"""
05b - ML Scoring: XGBoost + K-Means sobre company_database.
Potencia el scoring heurístico con modelos entrenados en data real.

Modelos:
  1. XGBoost — predice win_rate REAL desde features de comportamiento
     (sin data leakage: target y features son independientes)
  2. K-Means — descubre segmentos naturales de empresas (primario)

Score final: 15% percentile quality (K-Means) + 15% XGBoost + 70% heurístico

Resultado:
  data/filtered/leads_ml_ranked.parquet  — ranking ML
  data/filtered/clusters.parquet         — empresas con cluster asignado
  data/filtered/ml_model.joblib          — modelo guardado para reusar

Uso:
  python 05b_ml_scoring.py
  python 05b_ml_scoring.py --clusters 6    # N clusters K-Means
  python 05b_ml_scoring.py --no-xgboost    # Solo clustering
"""
from __future__ import annotations

import sys
import warnings

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import joblib

from config import FILTERED_DIR, IDEAL_RANGES
from pipeline_core import (
    COMBINED_SCORE_WEIGHTS,
    assign_cluster_profile,
    assign_rank,
    recompute_score_combined,
)
from pipeline_validation import assert_dataframe_contract
from utils import print_header, formato_clp

warnings.filterwarnings("ignore", category=UserWarning)

# Features para XGBoost (predict win_rate) — NO incluye win_rate ni total_wins
XGBOOST_FEATURES = [
    "total_bids",
    "monto_promedio",
    "monto_total",
    "dias_desde_ultima",
    "n_LP",
    "n_LE",
    "n_L1",
    "competidores_promedio",
    "total_lost",
    "n_distinct_rivals",
]

# Features para K-Means (todas, incluyendo win_rate — clustering no supervisado)
KMEANS_FEATURES = [
    "total_bids",
    "total_wins",
    "win_rate",
    "monto_promedio",
    "monto_total",
    "dias_desde_ultima",
    "n_LP",
    "n_LE",
    "n_L1",
    "competidores_promedio",
    "total_lost",
    "n_distinct_rivals",
]


def prepare_features(df: pd.DataFrame, feature_list: list[str]
                     ) -> tuple[pd.DataFrame, list[str]]:
    """Prepara features numéricas, imputa NaN."""
    available = [f for f in feature_list if f in df.columns]
    X = df[available].copy().fillna(0)

    # Log-transform de montos (distribución muy sesgada)
    for col in ["monto_promedio", "monto_total"]:
        if col in X.columns:
            X[col] = np.log1p(X[col].clip(lower=0))

    return X, available


def train_xgboost(df: pd.DataFrame) -> pd.DataFrame:
    """
    XGBoost predice win_rate desde features de COMPORTAMIENTO.
    Sin data leakage: el target (win_rate) NO está en las features.
    Esto descubre qué patrones de comportamiento predicen éxito en licitaciones.
    """
    print("\n--- XGBoost: Predicción de Win Rate ---")

    if "win_rate" not in df.columns or df["win_rate"].isna().all():
        print("  AVISO: No hay win_rate para entrenar, saltando XGBoost")
        df["xgb_predicted_wr"] = 0
        return df

    try:
        from xgboost import XGBRegressor
    except ImportError:
        print("  AVISO: xgboost no instalado, usando GradientBoosting...")
        from sklearn.ensemble import GradientBoostingRegressor as XGBRegressor

    X, used_features = prepare_features(df, XGBOOST_FEATURES)

    if len(used_features) < 3:
        print(f"  Solo {len(used_features)} features, saltando XGBoost")
        df["xgb_predicted_wr"] = 0
        return df

    # Target: win_rate real
    y = df["win_rate"].fillna(0).clip(0, 1)

    # Filtrar empresas con suficientes datos para target confiable
    mask_reliable = (df["total_bids"] >= 3).values  # .values -> numpy array for safe indexing
    print(f"  Empresas con >= 3 bids (target confiable): {mask_reliable.sum()}")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    try:
        model = XGBRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            min_child_weight=5, subsample=0.8, random_state=42
        )
    except TypeError:
        # Fallback for sklearn GradientBoostingRegressor which doesn't support min_child_weight
        model = XGBRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            min_samples_leaf=5, subsample=0.8, random_state=42
        )

    # Entrenar solo con datos confiables, predecir para todos
    if mask_reliable.sum() >= 20:
        model.fit(X_scaled[mask_reliable], y.values[mask_reliable])
    else:
        model.fit(X_scaled, y.values)

    predicted_wr = model.predict(X_scaled)
    df["xgb_predicted_wr"] = np.clip(predicted_wr, 0, 1)

    # Feature importance — esto revela insights reales
    if hasattr(model, "feature_importances_"):
        importances = pd.Series(model.feature_importances_, index=used_features)
        importances = importances.sort_values(ascending=False)
        print("\n  Feature importance (¿qué predice ganar licitaciones?):")
        for feat, imp in importances.items():
            bar = "#" * int(imp * 50)
            print(f"    {feat:25s} {imp:.3f} {bar}")

    # Comparar predicción vs realidad (solo datos confiables)
    if mask_reliable.sum() >= 10:
        real = pd.Series(y.values[mask_reliable])
        pred = pd.Series(df["xgb_predicted_wr"].values[mask_reliable])
        mae = (real - pred).abs().mean()
        corr = real.corr(pred)
        print(f"\n  MAE (error promedio): {mae:.3f}")
        print(f"  Correlación pred vs real: {corr:.3f}")
        print("  NOTA: metricas son in-sample (sin train/test split)")

    # XGBoost score para lead scoring:
    # Empresas con predicted WR en rango ideal (15-35%) = mejor lead
    # Gradiente dentro del ideal: pico en 0.25 (midpoint), baja a 85 en bordes
    ideal_min, ideal_max = IDEAL_RANGES["win_rate"]
    optimal_wr = 0.25
    wr_pred = df["xgb_predicted_wr"]

    def _xgb_score(wr):
        if ideal_min <= wr <= ideal_max:
            dist = abs(wr - optimal_wr)
            max_dist = max(abs(optimal_wr - ideal_min), abs(optimal_wr - ideal_max))
            return 85 + 15 * (1 - dist / max_dist) if max_dist > 0 else 100
        if wr < ideal_min:
            return max(0, 85 * wr / ideal_min) if ideal_min > 0 else 0
        return max(0, 85 * (1 - (wr - ideal_max) / (1 - ideal_max)))

    df["xgb_score"] = wr_pred.apply(_xgb_score)

    # Guardar modelo
    model_path = FILTERED_DIR / "ml_model.joblib"
    joblib.dump({"model": model, "scaler": scaler, "features": used_features,
                 "target": "win_rate"}, model_path)
    print(f"\n  Modelo guardado: {model_path}")

    return df


def run_kmeans(df: pd.DataFrame, n_clusters: int = 5) -> pd.DataFrame:
    """K-Means clustering + distancia al centroide ideal para scoring."""
    print(f"\n--- K-Means: {n_clusters} clusters ---")

    X, used_features = prepare_features(df, KMEANS_FEATURES)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Auto-detección de K óptimo si se pide (--clusters 0)
    if n_clusters <= 0 and len(X_scaled) >= 6:
        print("  Buscando K óptimo (silhouette)...")
        best_k, best_score = 3, -1
        for k in range(3, min(9, len(X_scaled))):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X_scaled)
            sil = silhouette_score(X_scaled, labels)
            print(f"    K={k}: silhouette={sil:.3f}")
            if sil > best_score:
                best_k, best_score = k, sil
        n_clusters = best_k
        print(f"  K óptimo: {n_clusters} (silhouette={best_score:.3f})")

    # Validar que hay suficientes samples para el número de clusters
    n_clusters = min(n_clusters, len(X_scaled) - 1)
    if n_clusters < 2:
        print("  AVISO: Muy pocos datos para clustering, asignando score neutro")
        df["cluster"] = 0
        df["km_score"] = 50.0
        df["cluster_perfil"] = "insuficiente"
        return df

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X_scaled)

    n_unique = len(set(df["cluster"]))
    if n_unique >= 2 and len(df) > n_unique:
        sil = silhouette_score(X_scaled, df["cluster"])
        print(f"  Silhouette score: {sil:.3f}")

    # Scoring por percentile-rank ponderado (discrimina mejor que distancia-al-ideal)
    rank_df = pd.DataFrame(index=df.index)
    for feat in used_features:
        if feat == "dias_desde_ultima":
            # Menor es mejor → rank ascendente (el de menos días queda con rank alto)
            rank_df[feat] = X[feat].rank(ascending=False, pct=True) * 100
        else:
            # Mayor es mejor
            rank_df[feat] = X[feat].rank(ascending=True, pct=True) * 100

    # Pesos por feature alineados con ICP de constructora mediana
    quality_weights = {
        "total_bids": 0.15,
        "total_wins": 0.15,
        "win_rate": 0.20,
        "monto_promedio": 0.15,
        "monto_total": 0.05,
        "dias_desde_ultima": 0.10,
        "n_LP": 0.10,
        "n_LE": 0.03,
        "n_L1": 0.02,
        "competidores_promedio": 0.05,
        "total_lost": 0.05,
        "n_distinct_rivals": 0.05,
    }

    df["km_score"] = 0.0
    total_weight = 0
    for feat in used_features:
        w = quality_weights.get(feat, 0.05)
        df["km_score"] += rank_df[feat] * w
        total_weight += w

    if total_weight > 0:
        df["km_score"] = (df["km_score"] / total_weight).clip(0, 100)

    # Analizar cada cluster
    print(f"\n  Perfiles de clusters:")
    print(f"  {'Cluster':>8} {'N':>6} {'Bids':>6} {'WR':>6} {'Monto':>12} {'LP%':>5} {'Perfil'}")
    print(f"  {'-'*65}")

    # cluster_perfil se asigna después de score_combined (en compute_combined_score)
    df["cluster_perfil"] = "pendiente"

    # Resumen por cluster
    cluster_profiles = {}
    for c in sorted(df["cluster"].unique()):
        mask = df["cluster"] == c
        grp = df[mask]
        n = len(grp)
        avg_bids = grp["total_bids"].mean()
        avg_wr = grp["win_rate"].mean() if "win_rate" in grp.columns else 0
        avg_monto = grp["monto_promedio"].mean() if "monto_promedio" in grp.columns else 0
        n_lp = grp["n_LP"].sum() if "n_LP" in grp.columns else 0
        total_lic = grp[["n_LP", "n_LE", "n_L1"]].sum().sum() if "n_LP" in grp.columns else 1
        pct_lp = n_lp / max(total_lic, 1)

        cluster_profiles[c] = f"C{c}"
        monto_str = formato_clp(avg_monto) if avg_monto > 0 else "N/A"
        avg_km = grp["km_score"].mean()
        print(f"  {c:>8} {n:>6} {avg_bids:>6.1f} {avg_wr:>5.0%} "
              f"{monto_str:>12} {pct_lp:>4.0%} km={avg_km:.0f}")

    # Guardar scaler y modelo KMeans
    km_path = FILTERED_DIR / "kmeans_model.joblib"
    joblib.dump({"model": km, "scaler": scaler, "features": used_features}, km_path)

    return df


def compute_combined_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score combinado final:
      15% K-Means (percentile-rank quality scoring)
      15% XGBoost (win prediction confidence)
      70% Heurístico (reglas de negocio del ICP — el que más discrimina)

    Si falta una señal ML, se usa score_total como baseline neutral para no
    comprimir artificialmente el score combinado en corridas parciales.
    """
    print("\n--- Score combinado ---")

    components = {}

    if "km_score" in df.columns:
        components["K-Means (15%)"] = df["km_score"] * COMBINED_SCORE_WEIGHTS["km_score"]
    if "xgb_score" in df.columns:
        components["XGBoost (15%)"] = df["xgb_score"] * COMBINED_SCORE_WEIGHTS["xgb_score"]
    if "score_total" in df.columns:
        components["Heurístico (70%)"] = df["score_total"] * COMBINED_SCORE_WEIGHTS["score_total"]

    if not components:
        print("  AVISO: Sin scores para combinar")
        df["score_combined"] = 0
        return df

    df = recompute_score_combined(df)

    # NO normalizar a max observado — comprime el rango
    # El score ya está en escala 0-100 (pesos suman 1.0, cada input 0-100)
    df["score_combined"] = df["score_combined"].clip(0, 100).round(1)

    for name, vals in components.items():
        avg = vals.mean()
        print(f"  {name}: contribución promedio = {avg:.1f}")

    print(f"  Score combinado: min={df['score_combined'].min():.1f}, "
          f"mean={df['score_combined'].mean():.1f}, max={df['score_combined'].max():.1f}, "
          f"std={df['score_combined'].std():.1f}")

    # Asignar cluster_perfil basado en score_combined (no km_score)
    # Percentiles: top 10% → IDEAL, next 20% → BUENO, next 30% → REGULAR, bottom 40% → BAJO
    df = assign_cluster_profile(df)
    for label in ["LEAD IDEAL", "LEAD BUENO", "LEAD REGULAR", "LEAD BAJO"]:
        n = (df["cluster_perfil"] == label).sum()
        print(f"  {label}: {n} ({100*n/len(df):.0f}%)")

    return df


def main():
    print_header("05b — ML Scoring (XGBoost + K-Means)")

    # Preferir leads_ranked (tiene score_total del paso 05) sobre company_database
    ranked_path = FILTERED_DIR / "leads_ranked.parquet"
    db_path = FILTERED_DIR / "company_database.parquet"

    if ranked_path.exists():
        source_path = ranked_path
    elif db_path.exists():
        source_path = db_path
    else:
        print("ERROR: No existe company_database.parquet ni leads_ranked.parquet")
        print("Ejecuta primero: python 04_build_company_db.py y python 05_score_leads.py")
        sys.exit(1)

    n_clusters = 5
    skip_xgb = "--no-xgboost" in sys.argv

    if "--clusters" in sys.argv:
        idx = sys.argv.index("--clusters")
        if idx + 1 < len(sys.argv):
            try:
                n_clusters = int(sys.argv[idx + 1])
            except ValueError:
                print(f"AVISO: --clusters requiere un número, se recibió '{sys.argv[idx + 1]}'. Usando default (5)")
        else:
            print("AVISO: --clusters requiere un valor, usando default (5)")

    df = pd.read_parquet(source_path)
    print(f"Fuente: {source_path.name} — {len(df)} empresas")

    # Filtrar mínima actividad
    active = df[df["total_bids"] >= 2].copy()
    print(f"Empresas activas (>= 2 bids): {len(active)}")

    # 1. XGBoost — predice win_rate desde comportamiento (sin leakage)
    if not skip_xgb:
        active = train_xgboost(active)

    # 2. K-Means — clustering no supervisado + distancia a ICP ideal
    active = run_kmeans(active, n_clusters)

    # 3. Score combinado: 15% KMeans + 15% XGBoost + 70% heurístico
    active = compute_combined_score(active)

    # Ranking final
    active = assign_rank(active, "score_combined", "rank_ml")

    # Guardar
    ranked_path = FILTERED_DIR / "leads_ml_ranked.parquet"
    assert_dataframe_contract(active, "leads_ml_ranked")
    active.to_parquet(ranked_path, index=False)

    clusters_path = FILTERED_DIR / "clusters.parquet"
    cluster_cols = ["rut", "nombre", "cluster", "cluster_perfil",
                    "score_combined", "km_score", "xgb_score"]
    cluster_cols = [c for c in cluster_cols if c in active.columns]
    active[cluster_cols].to_parquet(clusters_path, index=False)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  RESULTADOS ML")
    print(f"{'='*60}")
    print(f"  Ranking ML: {ranked_path}")
    print(f"  Clusters: {clusters_path}")

    print(f"\n  Top 15 leads (ML):")
    print(f"  {'#':>3} {'Score':>6} {'KM':>5} {'XGB':>5} {'Cluster':>20} "
          f"{'Bids':>5} {'WR':>5} {'Empresa'}")
    print(f"  {'-'*85}")
    for _, row in active.head(15).iterrows():
        nombre = row.get("nombre", row["rut"])
        if pd.isna(nombre):
            nombre = row["rut"]
        nombre = str(nombre)[:28]
        perfil = row.get("cluster_perfil", "?")
        wr = f"{row['win_rate']:.0%}" if pd.notna(row.get("win_rate")) else "?"
        km = f"{row.get('km_score', 0):.0f}"
        xgb = f"{row.get('xgb_score', 0):.0f}"
        print(f"  {row.get('rank_ml', '?'):>3} {row['score_combined']:>6.1f} "
              f"{km:>5} {xgb:>5} {perfil:>20} "
              f"{row['total_bids']:>5.0f} {wr:>5} {nombre}")

    # Cluster "lead ideal"
    ideal_clusters = active[active["cluster_perfil"] == "LEAD IDEAL"]
    if len(ideal_clusters) > 0:
        print(f"\n  Empresas en cluster 'LEAD IDEAL': {len(ideal_clusters)}")

    # Distribución
    print(f"\n  Distribución de scores:")
    for lo, hi in [(80, 101), (60, 80), (40, 60), (20, 40), (0, 20)]:
        count = ((active["score_combined"] >= lo) & (active["score_combined"] < hi)).sum()
        bar = "#" * (count // max(1, len(active) // 50))
        print(f"    {lo:>3}-{hi-1:>3}: {count:>5} {bar}")

    print(f"\nSiguiente paso: python 06_enrich_contacts.py (usa leads_ml_ranked)")


if __name__ == "__main__":
    main()
