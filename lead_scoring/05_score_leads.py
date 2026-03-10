"""
05 - Scoring de leads: 9 dimensiones, score 0-100.
Lee company_database.parquet, aplica fórmula, genera ranking.

Resultado: data/filtered/leads_ranked.parquet

Uso:
  python 05_score_leads.py
"""
from __future__ import annotations

import sys

import pandas as pd
import numpy as np

from config import FILTERED_DIR, SCORING_WEIGHTS, IDEAL_RANGES, REGIONES_TOP, RECENCIA_MAX_DAYS
from pipeline_validation import assert_dataframe_contract
from utils import print_header, formato_clp


def score_in_range(value: float, ideal_min: float, ideal_max: float,
                   lower_bound: float = 0, upper_bound: float = None,
                   optimal: float = None) -> float:
    """
    Score 0-100 basado en proximidad a un rango ideal.

    Sin optimal: flat 100 dentro del rango (backward compatible).
    Con optimal: gradiente 85-100 dentro del rango, pico en optimal.
                 Fuera del rango: decae desde el score del borde hasta 0.
                 Continuo en todos los puntos.
    """
    if pd.isna(value):
        return 0

    INNER_MIN = 85  # score mínimo dentro del rango ideal (cuando optimal dado)

    if optimal is None:
        # Comportamiento original
        if ideal_min <= value <= ideal_max:
            return 100
        if value < ideal_min:
            if lower_bound is not None and ideal_min > lower_bound:
                return max(0, 100 * (value - lower_bound) / (ideal_min - lower_bound))
            return max(0, 100 * value / ideal_min) if ideal_min > 0 else 0
        if upper_bound is not None and upper_bound > ideal_max:
            return max(0, 100 * (1 - (value - ideal_max) / (upper_bound - ideal_max)))
        return max(0, 100 * ideal_max / value) if value > 0 else 0

    # Con optimal: gradiente continuo
    optimal = max(ideal_min, min(ideal_max, optimal))
    max_dist = max(abs(optimal - ideal_min), abs(optimal - ideal_max))
    if max_dist == 0:
        max_dist = 1  # evitar div/0

    def _edge_score(edge_val):
        """Score en un borde del rango ideal."""
        d = abs(edge_val - optimal)
        return INNER_MIN + (100 - INNER_MIN) * (1 - d / max_dist)

    if ideal_min <= value <= ideal_max:
        return _edge_score(value)

    if value < ideal_min:
        es = _edge_score(ideal_min)
        if lower_bound is not None and ideal_min > lower_bound:
            return max(0, es * (value - lower_bound) / (ideal_min - lower_bound))
        return max(0, es * value / ideal_min) if ideal_min > 0 else 0

    # value > ideal_max
    es = _edge_score(ideal_max)
    if upper_bound is not None and upper_bound > ideal_max:
        return max(0, es * (1 - (value - ideal_max) / (upper_bound - ideal_max)))
    return max(0, es * ideal_max / value) if value > 0 else 0


def score_actividad(row: pd.Series) -> float:
    """Score de actividad: 5-15 bids/año es ideal, más activo = mejor."""
    bids = row.get("total_bids", 0)
    return score_in_range(bids, *IDEAL_RANGES["actividad"],
                          lower_bound=0, upper_bound=50, optimal=15)


def score_tamano(row: pd.Series) -> float:
    """Score de tamaño: basado en categoría MOP y volumen."""
    cat = str(row.get("categoria_mop", "")).lower()
    tipo_mop = row.get("tipo_mop")

    # Con categoría MOP
    if pd.notna(tipo_mop):
        if "mayor" in str(tipo_mop).lower():
            # 2da categoría = ideal, 1ra = muy grande, 3ra = chica
            if "2" in cat or "segunda" in cat:
                return 100
            if "3" in cat or "tercera" in cat:
                return 80
            if "1" in cat or "primera" in cat:
                return 60
            return 70  # Categoría desconocida pero está en MOP mayor
        else:
            return 50  # MOP menor

    # Sin categoría MOP: usar monto_promedio como proxy
    monto = row.get("monto_promedio", 0)
    if pd.notna(monto) and monto > 0:
        return score_in_range(monto, 66_000_000, 500_000_000,
                              lower_bound=1_000_000, upper_bound=5_000_000_000,
                              optimal=500_000_000)

    # Fallback: usar monto_adjudicado (acumulado) como proxy de tamaño
    monto_adj = row.get("monto_adjudicado", 0)
    if pd.notna(monto_adj) and monto_adj > 0:
        return score_in_range(monto_adj, 300_000_000, 5_000_000_000,
                              lower_bound=10_000_000, upper_bound=50_000_000_000,
                              optimal=5_000_000_000)

    return 20  # Sin datos = penalización


def score_win_rate(row: pd.Series) -> float:
    """Score de win rate: 15-35% es ideal, 25% es óptimo."""
    wr = row.get("win_rate", 0)
    if row.get("total_bids", 0) < 2:
        return 30  # Muy pocos datos
    return score_in_range(wr, *IDEAL_RANGES["win_rate"],
                          lower_bound=0, upper_bound=0.8, optimal=0.25)


def score_recencia(row: pd.Series) -> float:
    """Score de recencia: <365 días es ideal, más reciente = mejor."""
    dias = row.get("dias_desde_ultima", 9999)
    if pd.isna(dias) or dias > RECENCIA_MAX_DAYS:
        return 0  # Más de 4 años = inactivo
    return score_in_range(
        -dias, -IDEAL_RANGES["recencia_dias"][1], -IDEAL_RANGES["recencia_dias"][0],
        lower_bound=-RECENCIA_MAX_DAYS, upper_bound=0, optimal=0
    )


def score_valor(row: pd.Series) -> float:
    """Score de valor: monto promedio en rango LP, mayor = mejor."""
    monto = row.get("monto_promedio", 0)
    if pd.isna(monto) or monto == 0:
        return 20
    return score_in_range(monto, *IDEAL_RANGES["valor_clp"],
                          lower_bound=1_000_000, upper_bound=5_000_000_000,
                          optimal=500_000_000)


def score_competencia(row: pd.Series) -> float:
    """Score de competencia: 5-10 competidores, más competencia = más oportunidad."""
    comp = row.get("competidores_promedio", 0)
    if pd.isna(comp) or comp == 0:
        return 30
    return score_in_range(comp, *IDEAL_RANGES["competencia"],
                          lower_bound=1, upper_bound=30, optimal=10)


def score_digital(row: pd.Series) -> float:
    """
    Score de presencia digital: menos digital = más probable que necesite ayuda.
    Invertido: sin web/email = score alto (oportunidad de venderles servicio).
    """
    has_web = pd.notna(row.get("web")) or pd.notna(row.get("gm_web"))
    has_email = pd.notna(row.get("email")) or pd.notna(row.get("ocds_email"))
    has_phone = pd.notna(row.get("telefono")) or pd.notna(row.get("gm_telefono"))

    if has_web and has_email:
        return 30   # Buena presencia digital = menos oportunidad
    elif has_web or has_email:
        return 50   # Presencia parcial
    elif has_phone:
        return 60   # Teléfono pero sin web/email
    else:
        return 70   # Sin presencia digital = oportunidad


def score_oportunidad(row: pd.Series) -> float:
    """Score de oportunidad: más derrotas y rivales = más necesitan ayuda = mejor lead."""
    total_lost = row.get("total_lost", 0)
    total_lost = 0 if pd.isna(total_lost) else int(total_lost)
    n_rivals = row.get("n_distinct_rivals", 0)
    n_rivals = 0 if pd.isna(n_rivals) else int(n_rivals)
    total_bids = row.get("total_bids", 1)
    total_bids = max(1, total_bids if pd.notna(total_bids) else 1)

    if total_lost == 0 and n_rivals == 0:
        return 30  # Sin datos de derrotas

    loss_rate = total_lost / total_bids
    # loss_rate aporta hasta 70 puntos, n_rivals hasta 30
    score = min(70, loss_rate * 140)
    rival_bonus = min(30, n_rivals * 5)
    return min(100, score + rival_bonus)


def score_especializacion(row: pd.Series) -> float:
    """Score basado en tipo de obras (LP = más valor = mejor lead)."""
    n_lp = row.get("n_LP", 0)
    n_lp = 0 if pd.isna(n_lp) else n_lp
    n_le = row.get("n_LE", 0)
    n_le = 0 if pd.isna(n_le) else n_le
    n_l1 = row.get("n_L1", 0)
    n_l1 = 0 if pd.isna(n_l1) else n_l1
    total = n_lp + n_le + n_l1

    if total == 0:
        return 30

    # Mayor proporción de LP = mejor
    ratio_lp = n_lp / total
    ratio_le = n_le / total

    return min(100, ratio_lp * 100 + ratio_le * 50 + 20)


def score_region(row: pd.Series) -> float:
    """Score por región: regiones con más actividad."""
    region = row.get("region", "")
    if pd.isna(region) or not region:
        return 50  # Sin dato = neutro

    for i, r in enumerate(REGIONES_TOP):
        if r.lower() in str(region).lower() or str(region).lower() in r.lower():
            return 100 - i * 10  # 100, 90, 80, 70, 60
    return 40  # Región con menos actividad


def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula score total para cada empresa."""
    print("\n--- Calculando scores ---")

    scorers = {
        "actividad": score_actividad,
        "tamano": score_tamano,
        "win_rate": score_win_rate,
        "recencia": score_recencia,
        "valor": score_valor,
        "competencia": score_competencia,
        "oportunidad": score_oportunidad,
        "especializacion": score_especializacion,
        "region": score_region,
    }
    # score_digital se calcula aparte (solo discrimina post-enrichment)

    for dim, func in scorers.items():
        col_name = f"score_{dim}"
        df[col_name] = df.apply(func, axis=1)
        peso = SCORING_WEIGHTS[dim]
        print(f"  {dim} (peso {peso:.0%}): "
              f"min={df[col_name].min():.0f}, "
              f"media={df[col_name].mean():.0f}, "
              f"max={df[col_name].max():.0f}")

    # Score total ponderado
    df["score_total"] = sum(
        df[f"score_{dim}"] * peso
        for dim, peso in SCORING_WEIGHTS.items()
    )

    # Score ya está en escala 0-100 (pesos suman 1.0, cada dimensión 0-100)
    # Solo clipear por seguridad, no normalizar al max observado
    df["score_total"] = df["score_total"].clip(0, 100).round(1)

    return df


def main():
    print_header("05 — Scoring de Leads (9 dimensiones)")

    db_path = FILTERED_DIR / "company_database.parquet"
    if not db_path.exists():
        print("ERROR: No existe company_database.parquet")
        print("Ejecuta primero: python 04_build_company_db.py")
        sys.exit(1)

    df = pd.read_parquet(db_path)
    print(f"Empresas cargadas: {len(df)}")

    # Filtrar empresas con mínima actividad
    min_bids = 2
    active = df[df["total_bids"] >= min_bids].copy()
    print(f"Empresas con >= {min_bids} bids: {len(active)}")

    # Excluir personas naturales del ranking
    if "es_persona_natural" in active.columns:
        n_personas = active["es_persona_natural"].sum()
        if n_personas > 0:
            active = active[~active["es_persona_natural"]].copy()
            print(f"Excluidas {n_personas} personas naturales: {len(active)} empresas")

    # Calcular scores
    active = calculate_scores(active)

    # Rankear
    active = active.sort_values("score_total", ascending=False).reset_index(drop=True)
    active["rank"] = range(1, len(active) + 1)

    # Guardar
    out_path = FILTERED_DIR / "leads_ranked.parquet"
    assert_dataframe_contract(active, "leads_ranked")
    active.to_parquet(out_path, index=False)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  RANKING DE LEADS")
    print(f"{'='*60}")
    print(f"  Total rankeados: {len(active)}")
    print(f"  Score promedio: {active['score_total'].mean():.1f}")
    print(f"  Score mediana: {active['score_total'].median():.1f}")

    print(f"\n  Top 20 leads:")
    print(f"  {'#':>3} {'Score':>5} {'Bids':>5} {'Wins':>5} {'WR':>5} "
          f"{'Monto Prom':>12} {'Empresa'}")
    print(f"  {'-'*70}")

    for _, row in active.head(20).iterrows():
        nombre = row.get("nombre", row["rut"])
        if pd.isna(nombre):
            nombre = row["rut"]
        nombre = str(nombre)[:30]
        monto = formato_clp(row["monto_promedio"]) if pd.notna(row["monto_promedio"]) else "N/A"
        wr = f"{row['win_rate']:.0%}" if pd.notna(row["win_rate"]) else "N/A"

        print(f"  {row['rank']:>3} {row['score_total']:>5.1f} "
              f"{row['total_bids']:>5.0f} {row['total_wins']:>5.0f} {wr:>5} "
              f"{monto:>12} {nombre}")

    # Distribución de scores
    print(f"\n  Distribución de scores:")
    bins = [(80, 101), (60, 80), (40, 60), (20, 40), (0, 20)]
    for lo, hi in bins:
        count = ((active["score_total"] >= lo) & (active["score_total"] < hi)).sum()
        bar = "#" * (count // max(1, len(active) // 50))
        print(f"    {lo:>3}-{hi:>3}: {count:>5} {bar}")

    print(f"\n  Guardado: {out_path}")
    print(f"\nSiguiente paso: python 06_enrich_contacts.py")


if __name__ == "__main__":
    main()
