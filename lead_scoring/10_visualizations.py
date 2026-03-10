"""
10 - Visualizaciones nivel tesis del pipeline Lead Scoring.
Genera 27 graficos de alta calidad academica en data/output/graficos/

Fuentes:
  - data/filtered/company_database.parquet
  - data/filtered/leads_ranked.parquet
  - data/filtered/leads_ml_ranked.parquet
  - data/filtered/clusters.parquet
  - data/output/loss_analysis.parquet
  - data/output/matches.csv

Resultado:
  data/output/graficos/*.png  (300 DPI)

Uso:
  python 10_visualizations.py
  python 10_visualizations.py --only 1 5 12   # solo ciertos graficos
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import seaborn as sns

from config import FILTERED_DIR, OUTPUT_DIR, SCORING_WEIGHTS
from utils import print_header, formato_clp

# ---------------------------------------------------------------------------
# STYLE CONFIG
# ---------------------------------------------------------------------------
GRAFICOS_DIR = OUTPUT_DIR / "graficos"
GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)

DPI = 300
FIGSIZE_WIDE = (14, 7)
FIGSIZE_SQUARE = (10, 10)
FIGSIZE_TALL = (10, 12)
FIGSIZE_STD = (12, 7)

# Paleta profesional consistente
PALETTE_MAIN = [
    "#2C3E50", "#E74C3C", "#3498DB", "#2ECC71", "#F39C12",
    "#9B59B6", "#1ABC9C", "#E67E22", "#34495E", "#16A085",
]
PALETTE_SEQ = "YlOrRd"
PALETTE_DIV = "RdYlGn"
CLUSTER_COLORS = ["#3498DB", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6",
                  "#1ABC9C", "#E67E22", "#34495E", "#C0392B", "#27AE60"]

# Score dimension labels (Spanish)
SCORE_DIMS = {
    "score_actividad": "Actividad",
    "score_tamano": "Tamano",
    "score_win_rate": "Win Rate",
    "score_recencia": "Recencia",
    "score_valor": "Valor",
    "score_competencia": "Competencia",
    "score_digital": "Digital",
    "score_especializacion": "Especializacion",
    "score_region": "Region",
}

SCORE_COLS = list(SCORE_DIMS.keys())
WEIGHT_LABELS = {
    "score_actividad": "20%",
    "score_tamano": "15%",
    "score_win_rate": "12%",
    "score_recencia": "12%",
    "score_valor": "12%",
    "score_competencia": "10%",
    "score_digital": "7%",
    "score_especializacion": "7%",
    "score_region": "5%",
}


def _apply_style():
    """Estilo academico global."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "#FAFAFA",
        "axes.edgecolor": "#CCCCCC",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.color": "#CCCCCC",
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 16,
        "figure.titleweight": "bold",
    })
    sns.set_palette(PALETTE_MAIN)


def _save(fig, name: str):
    """Guarda figura y libera memoria."""
    path = GRAFICOS_DIR / f"{name}.png"
    fig.savefig(str(path), dpi=DPI, bbox_inches="tight", facecolor="white",
                edgecolor="none")
    plt.close("all")
    return path


def _short_region(name: str) -> str:
    """Acorta nombres de region para etiquetas."""
    if not isinstance(name, str):
        return str(name)
    return (name
            .replace("Region ", "")
            .replace("Region de ", "")
            .replace("Region del ", "")
            .replace("Metropolitana de Santiago", "RM Santiago")
            .replace("Libertador General Bernardo O'Higgins", "O'Higgins")
            .replace("Arica y Parinacota", "Arica-Parinac.")
            .replace("Nuble", "Nuble")
            .strip())


def _fmt_millions(x, _pos):
    """Formatter para ejes en millones CLP."""
    if x >= 1e9:
        return f"${x/1e9:.1f}B"
    if x >= 1e6:
        return f"${x/1e6:.0f}M"
    if x >= 1e3:
        return f"${x/1e3:.0f}K"
    return f"${x:.0f}"


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------
def load_data() -> Dict[str, Optional[pd.DataFrame]]:
    """Carga todos los DataFrames necesarios. Retorna None si no existe."""
    sources = {
        "company":   (FILTERED_DIR / "company_database.parquet", "parquet"),
        "ranked":    (FILTERED_DIR / "leads_ranked.parquet",     "parquet"),
        "ml":        (FILTERED_DIR / "leads_ml_ranked.parquet",  "parquet"),
        "clusters":  (FILTERED_DIR / "clusters.parquet",         "parquet"),
        "loss":      (OUTPUT_DIR / "loss_analysis.parquet",      "parquet"),
        "matches":   (OUTPUT_DIR / "matches.csv",                "csv"),
    }

    data = {}  # type: Dict[str, Optional[pd.DataFrame]]
    for key, (path, fmt) in sources.items():
        if path.exists():
            try:
                if fmt == "parquet":
                    data[key] = pd.read_parquet(str(path))
                else:
                    data[key] = pd.read_csv(str(path))
                print(f"  [OK] {key}: {len(data[key]):,} filas  ({path.name})")
            except Exception as e:
                print(f"  [WARN] Error leyendo {path.name}: {e}")
                data[key] = None
        else:
            print(f"  [--] {key}: no encontrado ({path.name})")
            data[key] = None

    return data


def _best_leads(data: Dict) -> Optional[pd.DataFrame]:
    """Retorna el mejor DataFrame de leads disponible (ml > ranked > company)."""
    for key in ("ml", "ranked", "company"):
        if data.get(key) is not None and len(data[key]) > 0:
            return data[key]
    return None


# ---------------------------------------------------------------------------
# 1. MERCADO OVERVIEW
# ---------------------------------------------------------------------------
def fig01_empresas_por_region(data: Dict) -> Optional[str]:
    """01 - Distribucion de empresas por region (horizontal bar, top 15)."""
    df = _best_leads(data)
    if df is None or "region" not in df.columns:
        return None

    counts = df["region"].value_counts().head(15).sort_values()
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    colors = sns.color_palette(PALETTE_SEQ, len(counts))
    bars = ax.barh(range(len(counts)), counts.values, color=colors)
    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels([_short_region(r) for r in counts.index])
    ax.set_xlabel("Numero de empresas")
    ax.set_title("Distribucion de Empresas Constructoras por Region\n(Top 15 regiones)")

    # Anotaciones
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_width() + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=9, fontweight="bold")

    ax.set_xlim(0, max(counts) * 1.12)
    fig.tight_layout()
    return str(_save(fig, "01_empresas_por_region"))


def fig02_evolucion_temporal(data: Dict) -> Optional[str]:
    """02 - Evolucion temporal de licitaciones por ano."""
    df = _best_leads(data)
    if df is None:
        return None

    # Intentar extraer anio de ultima_oferta o primera_oferta
    date_col = None
    for col in ("ultima_oferta", "primera_oferta"):
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        return None

    dfc = df.copy()
    dfc["_date"] = pd.to_datetime(dfc[date_col], errors="coerce")
    dfc = dfc.dropna(subset=["_date"])
    if dfc.empty:
        return None

    dfc["_year"] = dfc["_date"].dt.year
    yearly = dfc.groupby("_year").agg(
        empresas=("rut", "nunique") if "rut" in dfc.columns else ("nombre", "count"),
        total_bids=("total_bids", "sum") if "total_bids" in dfc.columns else ("_year", "count"),
    ).reset_index()

    fig, ax1 = plt.subplots(figsize=FIGSIZE_STD)
    color_bar = PALETTE_MAIN[2]
    color_line = PALETTE_MAIN[1]

    ax1.bar(yearly["_year"], yearly["empresas"], color=color_bar, alpha=0.7,
            label="Empresas activas", width=0.6)
    ax1.set_xlabel("Ano")
    ax1.set_ylabel("Empresas activas", color=color_bar)
    ax1.tick_params(axis="y", labelcolor=color_bar)

    if "total_bids" in yearly.columns:
        ax2 = ax1.twinx()
        ax2.plot(yearly["_year"], yearly["total_bids"], color=color_line, marker="o",
                 linewidth=2.5, markersize=8, label="Total ofertas")
        ax2.set_ylabel("Total ofertas acumuladas", color=color_line)
        ax2.tick_params(axis="y", labelcolor=color_line)

    ax1.set_title("Evolucion Temporal: Empresas Activas y Ofertas por Ano")
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    lines1, labels1 = ax1.get_legend_handles_labels()
    if "total_bids" in yearly.columns:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    else:
        ax1.legend(loc="upper left")

    fig.tight_layout()
    return str(_save(fig, "02_evolucion_temporal"))


def fig03_distribucion_montos(data: Dict) -> Optional[str]:
    """03 - Distribucion de montos de licitacion (histogram + KDE, log scale)."""
    df = _best_leads(data)
    if df is None or "monto_promedio" not in df.columns:
        return None

    montos = df["monto_promedio"].dropna()
    montos = montos[montos > 0]
    if len(montos) < 10:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)
    log_montos = np.log10(montos)

    ax.hist(log_montos, bins=50, color=PALETTE_MAIN[2], alpha=0.7, edgecolor="white",
            density=True, label="Histograma")
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(log_montos)
        x_range = np.linspace(log_montos.min(), log_montos.max(), 200)
        ax.plot(x_range, kde(x_range), color=PALETTE_MAIN[1], linewidth=2.5,
                label="KDE")
    except ImportError:
        pass

    # Percentiles
    for pct, style in [(25, "--"), (50, "-"), (75, "--"), (90, ":")]:
        val = np.percentile(log_montos, pct)
        ax.axvline(val, color=PALETTE_MAIN[4], linestyle=style, alpha=0.8, linewidth=1.5)
        ax.text(val, ax.get_ylim()[1] * 0.95, f"P{pct}\n{formato_clp(10**val)}",
                ha="center", fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    # Custom x-tick labels in CLP
    ticks = ax.get_xticks()
    ax.set_xticklabels([formato_clp(10**t) for t in ticks], rotation=30, ha="right")

    ax.set_xlabel("Monto promedio por licitacion (escala logaritmica)")
    ax.set_ylabel("Densidad")
    ax.set_title("Distribucion de Montos Promedio de Licitacion\n(Escala logaritmica)")
    ax.legend()
    fig.tight_layout()
    return str(_save(fig, "03_distribucion_montos"))


def fig04_tipos_licitacion_region(data: Dict) -> Optional[str]:
    """04 - Proporcion de tipos LP/LE/L1 (stacked bar by region, top 10)."""
    df = _best_leads(data)
    if df is None:
        return None
    needed = {"region", "n_LP", "n_LE", "n_L1"}
    if not needed.issubset(df.columns):
        return None

    dfc = df.copy()
    dfc["region_short"] = dfc["region"].apply(_short_region)
    top_regions = dfc["region_short"].value_counts().head(10).index.tolist()
    dfc = dfc[dfc["region_short"].isin(top_regions)]

    grouped = dfc.groupby("region_short")[["n_LP", "n_LE", "n_L1"]].sum()
    grouped = grouped.loc[top_regions]  # mantener orden

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)
    colors_tipo = {"n_LP": PALETTE_MAIN[1], "n_LE": PALETTE_MAIN[2], "n_L1": PALETTE_MAIN[3]}
    labels_tipo = {"n_LP": "Licitacion Publica (>1000 UTM)",
                   "n_LE": "Licitacion entre (100-1000 UTM)",
                   "n_L1": "Trato Directo (<100 UTM)"}

    bottom = np.zeros(len(grouped))
    for col in ["n_LP", "n_LE", "n_L1"]:
        vals = grouped[col].values
        ax.barh(range(len(grouped)), vals, left=bottom, color=colors_tipo[col],
                label=labels_tipo[col], edgecolor="white", linewidth=0.5)
        bottom += vals

    ax.set_yticks(range(len(grouped)))
    ax.set_yticklabels(grouped.index)
    ax.set_xlabel("Numero total de licitaciones")
    ax.set_title("Tipos de Licitacion por Region\n(Top 10 regiones por actividad)")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    return str(_save(fig, "04_tipos_licitacion_region"))


def fig05_heatmap_region_tipo(data: Dict) -> Optional[str]:
    """05 - Mapa de calor: actividad por region y tipo de licitacion."""
    df = _best_leads(data)
    if df is None:
        return None
    needed = {"region", "n_LP", "n_LE", "n_L1"}
    if not needed.issubset(df.columns):
        return None

    dfc = df.copy()
    dfc["region_short"] = dfc["region"].apply(_short_region)
    top_regions = dfc["region_short"].value_counts().head(12).index.tolist()
    dfc = dfc[dfc["region_short"].isin(top_regions)]

    pivot = dfc.groupby("region_short")[["n_LP", "n_LE", "n_L1"]].sum()
    pivot.columns = ["LP (>1000 UTM)", "LE (100-1000)", "L1 (<100)"]
    pivot = pivot.loc[top_regions]

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(pivot, annot=True, fmt=",.0f", cmap=PALETTE_SEQ, linewidths=0.5,
                linecolor="white", ax=ax, cbar_kws={"label": "Cantidad de licitaciones"})
    ax.set_title("Mapa de Calor: Actividad por Region y Tipo de Licitacion")
    ax.set_ylabel("")
    ax.set_xlabel("")
    fig.tight_layout()
    return str(_save(fig, "05_heatmap_region_tipo"))


# ---------------------------------------------------------------------------
# 2. SCORING ANALYSIS
# ---------------------------------------------------------------------------
def fig06_distribucion_score(data: Dict) -> Optional[str]:
    """06 - Distribucion del score total (histogram + KDE con percentiles)."""
    df = _best_leads(data)
    if df is None or "score_total" not in df.columns:
        return None

    scores = df["score_total"].dropna()
    if len(scores) < 10:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)
    ax.hist(scores, bins=40, color=PALETTE_MAIN[2], alpha=0.7, edgecolor="white",
            density=True, label="Histograma")
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(scores)
        x_range = np.linspace(scores.min(), scores.max(), 200)
        ax.plot(x_range, kde(x_range), color=PALETTE_MAIN[0], linewidth=2.5, label="KDE")
    except ImportError:
        pass

    # Percentiles
    for pct, color, style in [
        (25, PALETTE_MAIN[3], "--"),
        (50, PALETTE_MAIN[4], "-"),
        (75, PALETTE_MAIN[1], "--"),
        (90, PALETTE_MAIN[5], ":"),
        (95, PALETTE_MAIN[6], ":"),
    ]:
        val = np.percentile(scores, pct)
        ax.axvline(val, color=color, linestyle=style, linewidth=1.8, alpha=0.9)
        ax.text(val, ax.get_ylim()[1] * (0.85 - pct * 0.002),
                f"P{pct}: {val:.1f}", ha="center", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85))

    ax.set_xlabel("Score Total (0-100)")
    ax.set_ylabel("Densidad")
    ax.set_title("Distribucion del Score Total de Leads\n"
                 f"(N={len(scores):,} | Media={scores.mean():.1f} | Mediana={scores.median():.1f})")
    ax.legend()
    fig.tight_layout()
    return str(_save(fig, "06_distribucion_score"))


def fig07_radar_top20_vs_resto(data: Dict) -> Optional[str]:
    """07 - Radar/spider: promedio de 9 dimensiones del top 20 vs resto."""
    df = _best_leads(data)
    if df is None or "score_total" not in df.columns:
        return None
    available = [c for c in SCORE_COLS if c in df.columns]
    if len(available) < 4:
        return None

    df_sorted = df.sort_values("score_total", ascending=False)
    top20 = df_sorted.head(20)
    rest = df_sorted.iloc[20:]

    labels = [SCORE_DIMS.get(c, c) for c in available]
    top_vals = top20[available].mean().values
    rest_vals = rest[available].mean().values if len(rest) > 0 else np.zeros(len(available))

    # Cerrar el poligono
    angles = np.linspace(0, 2 * np.pi, len(available), endpoint=False).tolist()
    angles += angles[:1]
    top_vals = list(top_vals) + [top_vals[0]]
    rest_vals = list(rest_vals) + [rest_vals[0]]

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE, subplot_kw=dict(polar=True))
    ax.plot(angles, top_vals, "o-", linewidth=2.5, color=PALETTE_MAIN[1],
            label="Top 20 leads", markersize=7)
    ax.fill(angles, top_vals, alpha=0.15, color=PALETTE_MAIN[1])
    ax.plot(angles, rest_vals, "s-", linewidth=2, color=PALETTE_MAIN[2],
            label="Resto", markersize=5)
    ax.fill(angles, rest_vals, alpha=0.1, color=PALETTE_MAIN[2])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_title("Perfil de Scoring: Top 20 Leads vs Resto\n(Promedio de 9 dimensiones)",
                 pad=30, fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))
    fig.tight_layout()
    return str(_save(fig, "07_radar_top20_vs_resto"))


def fig08_correlacion_subscores(data: Dict) -> Optional[str]:
    """08 - Heatmap de correlacion entre los 9 sub-scores."""
    df = _best_leads(data)
    if df is None:
        return None
    available = [c for c in SCORE_COLS if c in df.columns]
    if len(available) < 4:
        return None

    corr = df[available].corr()
    labels = [SCORE_DIMS.get(c, c) for c in available]
    corr.index = labels
    corr.columns = labels

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, vmin=-1, vmax=1, linewidths=0.5, linecolor="white",
                ax=ax, cbar_kws={"label": "Correlacion de Pearson"})
    ax.set_title("Correlacion entre las 9 Dimensiones de Scoring")
    fig.tight_layout()
    return str(_save(fig, "08_correlacion_subscores"))


def fig09_score_vs_ml(data: Dict) -> Optional[str]:
    """09 - Score total heuristico vs score ML combinado (scatter + linea 45)."""
    df = data.get("ml")
    if df is None or "score_total" not in df.columns or "score_combined" not in df.columns:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    scatter = ax.scatter(df["score_total"], df["score_combined"], alpha=0.4,
                         s=20, c=PALETTE_MAIN[2], edgecolors="white", linewidth=0.3)

    # Linea 45 grados
    lims = [
        min(df["score_total"].min(), df["score_combined"].min()),
        max(df["score_total"].max(), df["score_combined"].max()),
    ]
    ax.plot(lims, lims, "--", color=PALETTE_MAIN[1], linewidth=2, alpha=0.7,
            label="Linea 45 (coincidencia perfecta)")

    # Correlacion
    corr_val = df["score_total"].corr(df["score_combined"])
    ax.text(0.05, 0.95, f"r = {corr_val:.3f}", transform=ax.transAxes,
            fontsize=13, fontweight="bold", va="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.9))

    ax.set_xlabel("Score Heuristico (0-100)")
    ax.set_ylabel("Score ML Combinado (0-100)")
    ax.set_title("Comparacion: Score Heuristico vs Score ML\n"
                 "(50% K-Means + 30% XGBoost + 20% Heuristico)")
    ax.legend(loc="lower right")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return str(_save(fig, "09_score_vs_ml"))


def fig10_violin_subscores(data: Dict) -> Optional[str]:
    """10 - Violin plots de cada sub-score."""
    df = _best_leads(data)
    if df is None:
        return None
    available = [c for c in SCORE_COLS if c in df.columns]
    if len(available) < 4:
        return None

    melted = df[available].melt(var_name="Dimension", value_name="Score")
    melted["Dimension"] = melted["Dimension"].map(SCORE_DIMS)

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    sns.violinplot(x="Dimension", y="Score", data=melted, ax=ax,
                   palette=PALETTE_MAIN[:len(available)], inner="quartile",
                   cut=0, linewidth=1.2)

    ax.set_xlabel("")
    ax.set_ylabel("Score (0-100)")
    ax.set_title("Distribucion de las 9 Dimensiones de Scoring\n(Violin plots con cuartiles)")
    ax.tick_params(axis="x", rotation=35)

    # Pesos en la parte superior
    for i, col in enumerate(available):
        weight = WEIGHT_LABELS.get(col, "")
        ax.text(i, 105, weight, ha="center", fontsize=9, fontweight="bold",
                color=PALETTE_MAIN[4])
    ax.set_ylim(-5, 115)

    fig.tight_layout()
    return str(_save(fig, "10_violin_subscores"))


def fig11_contribucion_top10(data: Dict) -> Optional[str]:
    """11 - Contribucion de cada dimension al score final (stacked bar, top 10 leads)."""
    df = _best_leads(data)
    if df is None or "score_total" not in df.columns:
        return None
    available = [c for c in SCORE_COLS if c in df.columns]
    if len(available) < 4:
        return None

    # Weighted contributions
    weights = {c: SCORING_WEIGHTS.get(c.replace("score_", ""), 0.1) for c in available}
    top10 = df.nlargest(10, "score_total").copy()

    name_col = "nombre" if "nombre" in top10.columns else "rut"
    names = top10[name_col].astype(str).str[:30].tolist()

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    left = np.zeros(len(top10))
    colors_dim = PALETTE_MAIN[:len(available)]

    for i, col in enumerate(available):
        weighted_vals = top10[col].fillna(0).values * weights[col]
        ax.barh(range(len(top10)), weighted_vals, left=left, color=colors_dim[i],
                label=f"{SCORE_DIMS.get(col, col)} ({WEIGHT_LABELS.get(col, '')})",
                edgecolor="white", linewidth=0.5)
        left += weighted_vals

    # Score total annotation
    for j, (score, name) in enumerate(zip(top10["score_total"], names)):
        ax.text(left[j] + 0.5, j, f"  {score:.1f}", va="center", fontsize=9,
                fontweight="bold")

    ax.set_yticks(range(len(top10)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Contribucion ponderada al Score Total")
    ax.set_title("Desglose de Score: Top 10 Leads\n(Contribucion de cada dimension)")
    ax.legend(loc="lower right", fontsize=8, ncol=2)
    fig.tight_layout()
    return str(_save(fig, "11_contribucion_top10"))


# ---------------------------------------------------------------------------
# 3. ML & CLUSTERING
# ---------------------------------------------------------------------------
def fig12_clusters_pca(data: Dict) -> Optional[str]:
    """12 - Scatter 2D: clusters K-Means (PCA coloreado por cluster)."""
    df = data.get("ml")
    if df is None or "cluster" not in df.columns:
        return None

    # Features para PCA
    feature_candidates = [
        "total_bids", "win_rate", "monto_promedio", "dias_desde_ultima",
        "n_LP", "n_LE", "n_L1", "competidores_promedio",
    ]
    features = [c for c in feature_candidates if c in df.columns]
    if len(features) < 3:
        return None

    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA

    X = df[features].fillna(0).values
    X_scaled = StandardScaler().fit_transform(X)
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X_scaled)

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    clusters = df["cluster"].values
    unique_clusters = sorted(df["cluster"].dropna().unique())

    for cl in unique_clusters:
        mask = clusters == cl
        label_name = cl
        if "cluster_perfil" in df.columns:
            perfil = df.loc[mask, "cluster_perfil"].mode()
            if len(perfil) > 0:
                label_name = f"C{cl}: {perfil.iloc[0]}"
        color = CLUSTER_COLORS[int(cl) % len(CLUSTER_COLORS)]
        ax.scatter(coords[mask, 0], coords[mask, 1], c=color, label=label_name,
                   alpha=0.6, s=30, edgecolors="white", linewidth=0.3)

    var_explained = pca.explained_variance_ratio_
    ax.set_xlabel(f"PC1 ({var_explained[0]:.1%} varianza)")
    ax.set_ylabel(f"PC2 ({var_explained[1]:.1%} varianza)")
    ax.set_title("Segmentacion de Empresas (K-Means)\n"
                 f"Proyeccion PCA - {len(unique_clusters)} clusters")
    ax.legend(loc="best", fontsize=9, markerscale=1.5)
    fig.tight_layout()
    return str(_save(fig, "12_clusters_pca"))


def fig13_radar_clusters(data: Dict) -> Optional[str]:
    """13 - Perfil de cada cluster: radar chart con medias de features."""
    cl_df = data.get("clusters")
    ml_df = data.get("ml")
    df = ml_df if ml_df is not None else cl_df
    if df is None or "cluster" not in df.columns:
        return None

    feature_candidates = [
        "total_bids", "win_rate", "monto_promedio", "dias_desde_ultima",
        "competidores_promedio", "score_total",
    ]
    features = [c for c in feature_candidates if c in df.columns]
    if len(features) < 3:
        return None

    unique_clusters = sorted(df["cluster"].dropna().unique())
    if len(unique_clusters) < 2:
        return None

    # Normalizar 0-100 para radar
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler(feature_range=(0, 100))
    df_norm = pd.DataFrame(scaler.fit_transform(df[features].fillna(0)),
                           columns=features, index=df.index)
    df_norm["cluster"] = df["cluster"].values

    angles = np.linspace(0, 2 * np.pi, len(features), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE, subplot_kw=dict(polar=True))

    for cl in unique_clusters:
        vals = df_norm[df_norm["cluster"] == cl][features].mean().values
        vals = list(vals) + [vals[0]]
        color = CLUSTER_COLORS[int(cl) % len(CLUSTER_COLORS)]
        label = f"Cluster {cl}"
        if "cluster_perfil" in df.columns:
            perfil = df[df["cluster"] == cl]["cluster_perfil"].mode()
            if len(perfil) > 0:
                label = f"C{cl}: {perfil.iloc[0]}"
        ax.plot(angles, vals, "o-", linewidth=2, color=color, label=label, markersize=5)
        ax.fill(angles, vals, alpha=0.08, color=color)

    feat_labels = [f.replace("_", " ").title() for f in features]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(feat_labels, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_title("Perfil de Clusters: Medias Normalizadas\n"
                 "(Cada eje = feature normalizada 0-100)", pad=30)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=9)
    fig.tight_layout()
    return str(_save(fig, "13_radar_clusters"))


def fig14_feature_importance(data: Dict) -> Optional[str]:
    """14 - Feature importance de XGBoost (horizontal bar)."""
    # Intentar cargar modelo guardado
    model_path = FILTERED_DIR / "ml_model.joblib"
    if not model_path.exists():
        return None

    try:
        import joblib
        model_data = joblib.load(str(model_path))
        if isinstance(model_data, dict):
            model = model_data.get("xgb_model") or model_data.get("model")
            feat_names = model_data.get("feature_names") or model_data.get("features")
        else:
            model = model_data
            feat_names = None
    except Exception:
        return None

    if model is None:
        return None

    try:
        importance = model.feature_importances_
    except AttributeError:
        return None

    if feat_names is None:
        feat_names = [f"Feature {i}" for i in range(len(importance))]

    # Sort
    idx = np.argsort(importance)
    feat_names = np.array(feat_names)[idx]
    importance = importance[idx]

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)
    colors = sns.color_palette(PALETTE_SEQ, len(importance))
    bars = ax.barh(range(len(importance)), importance, color=colors)

    ax.set_yticks(range(len(importance)))
    ax.set_yticklabels([f.replace("_", " ").title() for f in feat_names])
    ax.set_xlabel("Importancia relativa")
    ax.set_title("Feature Importance - Modelo XGBoost\n(Prediccion de Win Rate)")

    for bar, val in zip(bars, importance):
        ax.text(bar.get_width() + max(importance) * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

    fig.tight_layout()
    return str(_save(fig, "14_feature_importance"))


def fig15_winrate_real_vs_pred(data: Dict) -> Optional[str]:
    """15 - Win rate real vs predicho por XGBoost (scatter + R2)."""
    df = data.get("ml")
    if df is None or "win_rate" not in df.columns or "xgb_predicted_wr" not in df.columns:
        return None

    dfc = df.dropna(subset=["win_rate", "xgb_predicted_wr"])
    if len(dfc) < 10:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    ax.scatter(dfc["win_rate"], dfc["xgb_predicted_wr"], alpha=0.4, s=20,
               c=PALETTE_MAIN[2], edgecolors="white", linewidth=0.3)

    # Linea 45
    lims = [0, max(dfc["win_rate"].max(), dfc["xgb_predicted_wr"].max()) * 1.05]
    ax.plot(lims, lims, "--", color=PALETTE_MAIN[1], linewidth=2, alpha=0.7)

    # R2
    from sklearn.metrics import r2_score
    r2 = r2_score(dfc["win_rate"], dfc["xgb_predicted_wr"])
    mae = np.mean(np.abs(dfc["win_rate"] - dfc["xgb_predicted_wr"]))
    ax.text(0.05, 0.95, f"R$^2$ = {r2:.3f}\nMAE = {mae:.3f}",
            transform=ax.transAxes, fontsize=13, fontweight="bold", va="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.9))

    ax.set_xlabel("Win Rate Real")
    ax.set_ylabel("Win Rate Predicho (XGBoost)")
    ax.set_title("Win Rate Real vs Predicho por XGBoost")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return str(_save(fig, "15_winrate_real_vs_pred"))


def fig16_scores_por_cluster(data: Dict) -> Optional[str]:
    """16 - Distribucion de scores por perfil de lead (violin plot)."""
    df = data.get("ml") if data.get("ml") is not None else data.get("clusters")
    if df is None or "cluster_perfil" not in df.columns:
        return None

    score_col = "score_combined" if "score_combined" in df.columns else "score_total"
    if score_col not in df.columns:
        score_col = "km_score" if "km_score" in df.columns else None
    if score_col is None:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)

    # Ordenar perfiles de mejor a peor
    order = ["LEAD IDEAL", "LEAD BUENO", "LEAD REGULAR", "LEAD BAJO"]
    order = [o for o in order if o in df["cluster_perfil"].unique()]

    dfc = df[["cluster_perfil", score_col]].dropna().copy()
    dfc = dfc[dfc["cluster_perfil"].isin(order)]

    sns.violinplot(x="cluster_perfil", y=score_col, data=dfc, ax=ax,
                   order=order, palette=CLUSTER_COLORS[:len(order)],
                   inner="quartile", cut=0, linewidth=1.2)

    # Medias
    means = dfc.groupby("cluster_perfil")[score_col].mean()
    counts = dfc.groupby("cluster_perfil")[score_col].count()
    for i, label in enumerate(order):
        if label in means.index:
            ax.text(i, means[label] + 2, f"{means[label]:.1f}\n(n={counts[label]})",
                    ha="center", fontsize=9, fontweight="bold", color=PALETTE_MAIN[0])

    ax.set_xlabel("")
    ax.set_ylabel(f"Score ({score_col.replace('_', ' ').title()})")
    ax.set_title("Distribucion de Scores por Perfil\n(Violin plot con cuartiles y media)")
    ax.tick_params(axis="x", rotation=10)
    fig.tight_layout()
    return str(_save(fig, "16_scores_por_cluster"))


# ---------------------------------------------------------------------------
# 4. COMPETENCIA & RIVALIDADES
# ---------------------------------------------------------------------------
def fig17_top20_activas(data: Dict) -> Optional[str]:
    """17 - Top 20 empresas mas activas (horizontal bar, color por win_rate)."""
    df = _best_leads(data)
    if df is None or "total_bids" not in df.columns:
        return None

    top20 = df.nlargest(20, "total_bids").sort_values("total_bids")
    name_col = "nombre" if "nombre" in top20.columns else "rut"
    names = top20[name_col].astype(str).str[:35].tolist()

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)

    wr = top20["win_rate"].fillna(0).values if "win_rate" in top20.columns else np.zeros(len(top20))
    norm = plt.Normalize(vmin=0, vmax=max(wr.max(), 0.5))
    cmap = plt.cm.RdYlGn
    colors = cmap(norm(wr))

    bars = ax.barh(range(len(top20)), top20["total_bids"].values, color=colors,
                   edgecolor="white", linewidth=0.5)

    ax.set_yticks(range(len(top20)))
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Total de ofertas presentadas")
    ax.set_title("Top 20 Empresas Mas Activas\n(Color = tasa de adjudicacion)")

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Win Rate")

    # Annotations
    for bar, wr_val in zip(bars, wr):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"WR: {wr_val:.0%}", va="center", fontsize=8)

    fig.tight_layout()
    return str(_save(fig, "17_top20_activas"))


def fig18_winrate_vs_bids(data: Dict) -> Optional[str]:
    """18 - Win rate vs numero de licitaciones (scatter, tamano=monto)."""
    df = _best_leads(data)
    if df is None or "win_rate" not in df.columns or "total_bids" not in df.columns:
        return None

    dfc = df.dropna(subset=["win_rate", "total_bids"]).copy()
    dfc = dfc[dfc["total_bids"] > 0]
    if len(dfc) < 10:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)

    sizes = np.ones(len(dfc)) * 30
    if "monto_total" in dfc.columns:
        montos = dfc["monto_total"].fillna(0)
        sizes = 20 + 200 * (montos / montos.max()).fillna(0)

    color_arr = dfc["win_rate"].values
    scatter = ax.scatter(dfc["total_bids"], dfc["win_rate"], s=sizes, c=color_arr,
                         cmap="RdYlGn", alpha=0.6, edgecolors="white", linewidth=0.3)

    # Reference lines
    median_wr = dfc["win_rate"].median()
    median_bids = dfc["total_bids"].median()
    ax.axhline(median_wr, color="gray", linestyle="--", alpha=0.5, linewidth=1)
    ax.axvline(median_bids, color="gray", linestyle="--", alpha=0.5, linewidth=1)

    # Quadrant labels
    ax.text(0.95, 0.95, "Alta actividad\nAlto exito", transform=ax.transAxes,
            ha="right", va="top", fontsize=9, style="italic", alpha=0.5)
    ax.text(0.05, 0.95, "Baja actividad\nAlto exito", transform=ax.transAxes,
            ha="left", va="top", fontsize=9, style="italic", alpha=0.5)
    ax.text(0.95, 0.05, "Alta actividad\nBajo exito", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9, style="italic", alpha=0.5)
    ax.text(0.05, 0.05, "Baja actividad\nBajo exito", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=9, style="italic", alpha=0.5)

    cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Win Rate")
    ax.set_xlabel("Numero de licitaciones presentadas")
    ax.set_ylabel("Tasa de adjudicacion (Win Rate)")
    ax.set_title("Win Rate vs Actividad\n(Tamano = monto total adjudicado)")
    fig.tight_layout()
    return str(_save(fig, "18_winrate_vs_bids"))


def fig19_red_rivalidades(data: Dict) -> Optional[str]:
    """19 - Red de rivalidades top 10 leads (network graph con networkx)."""
    loss_df = data.get("loss")
    leads_df = _best_leads(data)
    if loss_df is None or leads_df is None:
        return None

    try:
        import networkx as nx
    except ImportError:
        print("    [SKIP] networkx no instalado, saltando grafo de rivalidades")
        return None

    # Merge nombres
    if "nombre" not in loss_df.columns and "rut" in loss_df.columns and "nombre" in leads_df.columns:
        name_map = leads_df.set_index("rut")["nombre"].to_dict() if "rut" in leads_df.columns else {}
        loss_df = loss_df.copy()
        loss_df["nombre"] = loss_df["rut"].map(name_map)

    # Top 10 leads con mas participaciones
    sort_col = "total_participated" if "total_participated" in loss_df.columns else "total_lost"
    if sort_col not in loss_df.columns:
        return None

    top10 = loss_df.nlargest(10, sort_col)
    name_col = "nombre" if "nombre" in top10.columns else "rut"

    G = nx.Graph()
    # Nodos: top 10 leads
    for _, row in top10.iterrows():
        name = str(row.get(name_col, ""))[:25]
        G.add_node(name, node_type="lead",
                   losses=row.get("total_lost", 0))

    # Edges: rivalidades
    for _, row in top10.iterrows():
        lead_name = str(row.get(name_col, ""))[:25]
        for rival_col, count_col in [("top_rival_1_name", "top_rival_1_count"),
                                      ("top_rival_2_name", "top_rival_2_count")]:
            rival = row.get(rival_col)
            count = row.get(count_col, 1)
            if pd.notna(rival) and str(rival).strip():
                rival_short = str(rival)[:25]
                if rival_short not in G.nodes:
                    G.add_node(rival_short, node_type="rival")
                G.add_edge(lead_name, rival_short, weight=count if pd.notna(count) else 1)

    if len(G.nodes) < 3:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    pos = nx.spring_layout(G, k=2.5, seed=42, iterations=50)

    # Color by type
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        if G.nodes[node].get("node_type") == "lead":
            node_colors.append(PALETTE_MAIN[1])
            node_sizes.append(800)
        else:
            node_colors.append(PALETTE_MAIN[2])
            node_sizes.append(400)

    weights = [G[u][v].get("weight", 1) for u, v in G.edges()]
    max_w = max(weights) if weights else 1
    edge_widths = [1 + 4 * (w / max_w) for w in weights]

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=node_sizes,
                           alpha=0.8, edgecolors="white", linewidths=1.5)
    nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths, alpha=0.4,
                           edge_color="#888888")
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_weight="bold")

    # Edge labels (counts)
    edge_labels = {(u, v): str(int(d["weight"])) for u, v, d in G.edges(data=True)
                   if d.get("weight", 0) > 1}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_size=7)

    # Legend
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE_MAIN[1],
               markersize=12, label="Leads (top 10)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE_MAIN[2],
               markersize=10, label="Rivales recurrentes"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=10)

    ax.set_title("Red de Rivalidades: Top 10 Leads\n"
                 "(Grosor de linea = frecuencia de enfrentamiento)")
    ax.axis("off")
    fig.tight_layout()
    return str(_save(fig, "19_red_rivalidades"))


def fig20_loss_rate_dist(data: Dict) -> Optional[str]:
    """20 - Loss rate distribution (histogram)."""
    loss_df = data.get("loss")
    if loss_df is None or "loss_rate" not in loss_df.columns:
        return None

    rates = loss_df["loss_rate"].dropna()
    if len(rates) < 10:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)
    ax.hist(rates, bins=30, color=PALETTE_MAIN[1], alpha=0.7, edgecolor="white",
            density=True)
    try:
        from scipy.stats import gaussian_kde
        if len(set(rates)) > 3:  # KDE needs variance
            kde = gaussian_kde(rates)
            x_range = np.linspace(0, 1, 200)
            ax.plot(x_range, kde(x_range), color=PALETTE_MAIN[0], linewidth=2.5)
    except (ImportError, np.linalg.LinAlgError):
        pass

    mean_lr = rates.mean()
    median_lr = rates.median()
    ax.axvline(mean_lr, color=PALETTE_MAIN[4], linestyle="-", linewidth=2,
               label=f"Media: {mean_lr:.1%}")
    ax.axvline(median_lr, color=PALETTE_MAIN[3], linestyle="--", linewidth=2,
               label=f"Mediana: {median_lr:.1%}")

    ax.set_xlabel("Tasa de Derrota (Loss Rate)")
    ax.set_ylabel("Densidad")
    ax.set_title(f"Distribucion de Loss Rate\n(N={len(rates):,} empresas)")
    ax.legend(fontsize=11)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    fig.tight_layout()
    return str(_save(fig, "20_loss_rate_dist"))


# ---------------------------------------------------------------------------
# 5. LEADS & OPORTUNIDADES
# ---------------------------------------------------------------------------
def fig21_top20_desglosado(data: Dict) -> Optional[str]:
    """21 - Top 20 leads: score desglosado (stacked horizontal bar)."""
    df = _best_leads(data)
    if df is None or "score_total" not in df.columns:
        return None
    available = [c for c in SCORE_COLS if c in df.columns]
    if len(available) < 4:
        return None

    weights = {c: SCORING_WEIGHTS.get(c.replace("score_", ""), 0.1) for c in available}
    top20 = df.nlargest(20, "score_total").copy()
    name_col = "nombre" if "nombre" in top20.columns else "rut"
    names = top20[name_col].astype(str).str[:30].tolist()

    fig, ax = plt.subplots(figsize=(14, 10))
    left = np.zeros(len(top20))
    colors_dim = PALETTE_MAIN[:len(available)]

    for i, col in enumerate(available):
        weighted_vals = top20[col].fillna(0).values * weights[col]
        ax.barh(range(len(top20)), weighted_vals, left=left, color=colors_dim[i],
                label=f"{SCORE_DIMS.get(col, col)} ({WEIGHT_LABELS.get(col, '')})",
                edgecolor="white", linewidth=0.5)
        left += weighted_vals

    for j, score in enumerate(top20["score_total"]):
        ax.text(left[j] + 0.3, j, f"{score:.1f}", va="center", fontsize=9,
                fontweight="bold")

    ax.set_yticks(range(len(top20)))
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Score Total Ponderado")
    ax.set_title("Top 20 Leads: Desglose Completo del Score\n"
                 "(9 dimensiones ponderadas)")

    # Rank and ML score annotation
    if "rank_ml" in top20.columns:
        ax2 = ax.twinx()
        ax2.set_yticks(range(len(top20)))
        ax2.set_yticklabels([f"#{int(r)}" if pd.notna(r) else "" for r in top20["rank_ml"]],
                            fontsize=8, color=PALETTE_MAIN[5])
        ax2.set_ylabel("Rank ML", color=PALETTE_MAIN[5])
        ax2.invert_yaxis()

    ax.legend(loc="lower right", fontsize=7, ncol=3)
    fig.tight_layout()
    return str(_save(fig, "21_top20_desglosado"))


def fig22_funnel(data: Dict) -> Optional[str]:
    """22 - Funnel: total empresas -> activas -> score alto -> contactables."""
    df = _best_leads(data)
    if df is None:
        return None

    total = len(df)
    activas = len(df[df["total_bids"] > 0]) if "total_bids" in df.columns else total
    score_alto = len(df[df["score_total"] > df["score_total"].quantile(0.75)]) if "score_total" in df.columns else 0

    # Contactables: con telefono o algun dato de contacto
    contactable = 0
    enriched_path = FILTERED_DIR / "leads_enriched.parquet"
    if enriched_path.exists():
        try:
            enriched = pd.read_parquet(str(enriched_path))
            contactable = len(enriched.dropna(subset=["telefono"])) if "telefono" in enriched.columns else 0
        except Exception:
            pass
    if contactable == 0 and data.get("matches") is not None:
        matches = data["matches"]
        if "lead_telefono" in matches.columns:
            contactable = matches["lead_telefono"].dropna().nunique()

    stages = ["Total empresas", "Con actividad", "Score alto (P75+)", "Contactables"]
    values = [total, activas, score_alto, max(contactable, 1)]

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)

    max_width = 1.0
    for i, (stage, val) in enumerate(zip(stages, values)):
        width = max_width * (val / max(values[0], 1))
        width = max(width, 0.08)  # minimo visible
        left = (max_width - width) / 2
        color = PALETTE_MAIN[i % len(PALETTE_MAIN)]
        rect = plt.Rectangle((left, len(stages) - i - 1), width, 0.7,
                              facecolor=color, alpha=0.8, edgecolor="white", linewidth=2)
        ax.add_patch(rect)
        ax.text(0.5, len(stages) - i - 1 + 0.35, f"{stage}\n{val:,}",
                ha="center", va="center", fontsize=12, fontweight="bold", color="white")

        # Conversion rate
        if i > 0:
            rate = val / values[i - 1] if values[i - 1] > 0 else 0
            ax.text(left + width + 0.03, len(stages) - i - 1 + 0.35,
                    f"{rate:.0%}", fontsize=10, va="center", color=PALETTE_MAIN[0],
                    fontweight="bold")

    ax.set_xlim(-0.1, 1.25)
    ax.set_ylim(-0.3, len(stages) + 0.3)
    ax.set_title("Funnel de Conversion de Leads\n"
                 "(Total -> Activas -> Score alto -> Contactables)")
    ax.axis("off")
    fig.tight_layout()
    return str(_save(fig, "22_funnel"))


def fig23_inactivo_vs_score(data: Dict) -> Optional[str]:
    """23 - Dias inactivo vs score (scatter, highlight leads dormidos con potencial)."""
    df = _best_leads(data)
    if df is None or "dias_desde_ultima" not in df.columns or "score_total" not in df.columns:
        return None

    dfc = df.dropna(subset=["dias_desde_ultima", "score_total"]).copy()
    if len(dfc) < 10:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)

    # Dormidos con potencial: inactivos >180 dias pero score > P75
    p75 = dfc["score_total"].quantile(0.75)
    dormidos = (dfc["dias_desde_ultima"] > 180) & (dfc["score_total"] > p75)
    normales = ~dormidos

    ax.scatter(dfc.loc[normales, "dias_desde_ultima"],
               dfc.loc[normales, "score_total"],
               alpha=0.3, s=20, c=PALETTE_MAIN[2], label="Normales",
               edgecolors="white", linewidth=0.2)
    ax.scatter(dfc.loc[dormidos, "dias_desde_ultima"],
               dfc.loc[dormidos, "score_total"],
               alpha=0.8, s=60, c=PALETTE_MAIN[1], marker="*",
               label=f"Dormidos con potencial ({dormidos.sum()})",
               edgecolors="white", linewidth=0.5)

    # Reference lines
    ax.axhline(p75, color=PALETTE_MAIN[3], linestyle="--", alpha=0.7,
               label=f"P75 Score = {p75:.1f}")
    ax.axvline(180, color=PALETTE_MAIN[4], linestyle="--", alpha=0.7,
               label="180 dias inactividad")

    # Highlight zone
    ax.axvspan(180, dfc["dias_desde_ultima"].max() * 1.05, ymin=p75 / 110,
               ymax=1, alpha=0.05, color=PALETTE_MAIN[1])
    ax.text(0.95, 0.95, "ZONA DE\nOPORTUNIDAD", transform=ax.transAxes,
            ha="right", va="top", fontsize=11, fontweight="bold",
            color=PALETTE_MAIN[1], alpha=0.4)

    ax.set_xlabel("Dias desde ultima oferta")
    ax.set_ylabel("Score Total")
    ax.set_title("Leads Dormidos con Potencial\n"
                 "(Inactivos >180 dias pero score alto)")
    ax.legend(loc="center right", fontsize=9)
    fig.tight_layout()
    return str(_save(fig, "23_inactivo_vs_score"))


def fig24_match_score_dist(data: Dict) -> Optional[str]:
    """24 - Match score distribution para alertas."""
    matches = data.get("matches")
    if matches is None or "match_score" not in matches.columns:
        return None

    scores = matches["match_score"].dropna()
    if len(scores) < 5:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)
    ax.hist(scores, bins=25, color=PALETTE_MAIN[3], alpha=0.7, edgecolor="white")

    # Thresholds de alerta
    thresholds = [
        (0.8, "Alta prioridad", PALETTE_MAIN[1]),
        (0.6, "Media", PALETTE_MAIN[4]),
        (0.4, "Baja", PALETTE_MAIN[2]),
    ]
    for thresh, label, color in thresholds:
        ax.axvline(thresh, color=color, linestyle="--", linewidth=2, alpha=0.8,
                   label=f"{label} (>{thresh:.0%})")

    ax.set_xlabel("Match Score (Lead-Licitacion)")
    ax.set_ylabel("Cantidad de matches")
    ax.set_title(f"Distribucion de Match Scores (Lead-Licitacion)\n"
                 f"(N={len(scores):,} matches)")
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()
    return str(_save(fig, "24_match_score_dist"))


def fig25_estacionalidad(data: Dict) -> Optional[str]:
    """25 - Heatmap: mes de cierre de licitaciones vs region (estacionalidad)."""
    matches = data.get("matches")
    if matches is None or "tender_cierre" not in matches.columns:
        return None

    dfc = matches.copy()
    dfc["_date"] = pd.to_datetime(dfc["tender_cierre"], errors="coerce")
    dfc = dfc.dropna(subset=["_date"])
    if len(dfc) < 20:
        return None

    dfc["mes"] = dfc["_date"].dt.month

    # Si hay region disponible, cruzar
    leads_df = _best_leads(data)
    if leads_df is not None and "region" in leads_df.columns and "lead_rut" in dfc.columns:
        rut_region = leads_df.set_index("rut")["region"].to_dict() if "rut" in leads_df.columns else {}
        dfc["region"] = dfc["lead_rut"].map(rut_region).apply(_short_region)
        dfc = dfc.dropna(subset=["region"])
        top_regions = dfc["region"].value_counts().head(10).index.tolist()
        dfc = dfc[dfc["region"].isin(top_regions)]
        pivot = dfc.groupby(["region", "mes"]).size().unstack(fill_value=0)
    else:
        # Solo por mes si no hay region
        dfc["region"] = "Total"
        pivot = dfc.groupby(["region", "mes"]).size().unstack(fill_value=0)

    meses = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
             7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
    pivot.columns = [meses.get(m, str(m)) for m in pivot.columns]

    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(pivot, annot=True, fmt="d", cmap=PALETTE_SEQ, linewidths=0.5,
                linecolor="white", ax=ax, cbar_kws={"label": "Licitaciones"})
    ax.set_title("Estacionalidad: Licitaciones por Mes y Region\n"
                 "(Mapa de calor)")
    ax.set_ylabel("")
    ax.set_xlabel("Mes de cierre")
    fig.tight_layout()
    return str(_save(fig, "25_estacionalidad"))


# ---------------------------------------------------------------------------
# 6. EXTRAS
# ---------------------------------------------------------------------------
def fig26_pareto(data: Dict) -> Optional[str]:
    """26 - Pareto: % de empresas que concentran % de adjudicaciones."""
    df = _best_leads(data)
    if df is None or "monto_adjudicado" not in df.columns:
        return None

    dfc = df[df["monto_adjudicado"] > 0].sort_values("monto_adjudicado", ascending=False).copy()
    if len(dfc) < 10:
        return None

    total = dfc["monto_adjudicado"].sum()
    dfc["pct_acumulado"] = dfc["monto_adjudicado"].cumsum() / total * 100
    dfc["pct_empresas"] = np.arange(1, len(dfc) + 1) / len(dfc) * 100

    fig, ax1 = plt.subplots(figsize=FIGSIZE_STD)

    # Barras individuales (solo top 30 para legibilidad)
    n_bars = min(30, len(dfc))
    ax1.bar(range(n_bars), dfc["monto_adjudicado"].values[:n_bars] / 1e6,
            color=PALETTE_MAIN[2], alpha=0.7, label="Monto adjudicado")
    ax1.set_ylabel("Monto adjudicado (M CLP)", color=PALETTE_MAIN[2])
    ax1.tick_params(axis="y", labelcolor=PALETTE_MAIN[2])

    # Curva acumulada
    ax2 = ax1.twinx()
    ax2.plot(range(n_bars), dfc["pct_acumulado"].values[:n_bars], color=PALETTE_MAIN[1],
             linewidth=2.5, marker=".", markersize=4, label="% acumulado")
    ax2.set_ylabel("% acumulado de adjudicaciones", color=PALETTE_MAIN[1])
    ax2.tick_params(axis="y", labelcolor=PALETTE_MAIN[1])
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter())

    # Lineas de referencia 80/20
    ax2.axhline(80, color="gray", linestyle="--", alpha=0.6)
    # Encontrar el indice donde se alcanza el 80%
    idx_80 = (dfc["pct_acumulado"] >= 80).idxmax()
    pos_80 = dfc.index.get_loc(idx_80)
    pct_empresas_80 = (pos_80 + 1) / len(dfc) * 100
    if pos_80 < n_bars:
        ax1.axvline(pos_80, color="gray", linestyle="--", alpha=0.6)
        ax1.text(pos_80 + 0.5, ax1.get_ylim()[1] * 0.95,
                 f"{pct_empresas_80:.0f}% de empresas\nconcentra 80%",
                 fontsize=10, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="yellow", alpha=0.3))

    ax1.set_xlabel("Empresas (ordenadas por monto adjudicado)")
    ax1.set_title("Analisis de Pareto: Concentracion de Adjudicaciones\n"
                  f"(Top {n_bars} de {len(dfc):,} empresas)")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right")

    fig.tight_layout()
    return str(_save(fig, "26_pareto"))


def fig27_monto_por_categoria(data: Dict) -> Optional[str]:
    """27 - Boxplot de monto promedio por categoria MOP."""
    df = _best_leads(data)
    if df is None or "categoria_mop" not in df.columns or "monto_promedio" not in df.columns:
        return None

    dfc = df.dropna(subset=["categoria_mop", "monto_promedio"]).copy()
    dfc = dfc[dfc["monto_promedio"] > 0]
    if len(dfc) < 10:
        return None

    # Orden logico de categorias
    cat_order = sorted(dfc["categoria_mop"].unique())

    fig, ax = plt.subplots(figsize=FIGSIZE_STD)
    sns.boxplot(x="categoria_mop", y="monto_promedio", data=dfc, ax=ax,
                order=cat_order, palette=PALETTE_MAIN[:len(cat_order)],
                showfliers=False, linewidth=1.2)

    # Overlay strip
    sns.stripplot(x="categoria_mop", y="monto_promedio", data=dfc, ax=ax,
                  order=cat_order, color=PALETTE_MAIN[0], alpha=0.2, size=3, jitter=True)

    # Medias
    means = dfc.groupby("categoria_mop")["monto_promedio"].mean()
    for i, cat in enumerate(cat_order):
        if cat in means.index:
            ax.text(i, means[cat] * 1.02, formato_clp(means[cat]),
                    ha="center", fontsize=8, fontweight="bold", color=PALETTE_MAIN[1])

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_millions))
    ax.set_xlabel("Categoria MOP")
    ax.set_ylabel("Monto promedio por licitacion (CLP)")
    ax.set_title("Monto Promedio por Categoria MOP\n(Boxplot + distribucion individual)")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return str(_save(fig, "27_monto_por_categoria"))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

# Registro de todos los graficos
ALL_CHARTS = [
    (1,  "Empresas por region",             fig01_empresas_por_region),
    (2,  "Evolucion temporal",              fig02_evolucion_temporal),
    (3,  "Distribucion de montos",          fig03_distribucion_montos),
    (4,  "Tipos de licitacion por region",  fig04_tipos_licitacion_region),
    (5,  "Heatmap region x tipo",           fig05_heatmap_region_tipo),
    (6,  "Distribucion del score total",    fig06_distribucion_score),
    (7,  "Radar top 20 vs resto",           fig07_radar_top20_vs_resto),
    (8,  "Correlacion sub-scores",          fig08_correlacion_subscores),
    (9,  "Score heuristico vs ML",          fig09_score_vs_ml),
    (10, "Violin sub-scores",               fig10_violin_subscores),
    (11, "Contribucion top 10",             fig11_contribucion_top10),
    (12, "Clusters PCA",                    fig12_clusters_pca),
    (13, "Radar clusters",                  fig13_radar_clusters),
    (14, "Feature importance XGBoost",      fig14_feature_importance),
    (15, "Win rate real vs predicho",       fig15_winrate_real_vs_pred),
    (16, "Scores por cluster",              fig16_scores_por_cluster),
    (17, "Top 20 empresas activas",         fig17_top20_activas),
    (18, "Win rate vs actividad",           fig18_winrate_vs_bids),
    (19, "Red de rivalidades",              fig19_red_rivalidades),
    (20, "Loss rate distribution",          fig20_loss_rate_dist),
    (21, "Top 20 leads desglosado",         fig21_top20_desglosado),
    (22, "Funnel de conversion",            fig22_funnel),
    (23, "Leads dormidos con potencial",    fig23_inactivo_vs_score),
    (24, "Match score distribution",        fig24_match_score_dist),
    (25, "Estacionalidad",                  fig25_estacionalidad),
    (26, "Pareto adjudicaciones",           fig26_pareto),
    (27, "Monto por categoria MOP",         fig27_monto_por_categoria),
]


def main():
    print_header("10 - Visualizaciones Lead Scoring")
    _apply_style()

    # Parse --only argument
    only_ids = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        only_ids = set()
        for arg in sys.argv[idx + 1:]:
            try:
                only_ids.add(int(arg))
            except ValueError:
                break
        if not only_ids:
            only_ids = None

    print(f"\nCargando datos...")
    data = load_data()

    n_ok = 0
    n_skip = 0
    n_fail = 0

    selected = ALL_CHARTS if only_ids is None else [c for c in ALL_CHARTS if c[0] in only_ids]

    print(f"\nGenerando {len(selected)} graficos en {GRAFICOS_DIR}/\n")

    for num, desc, func in selected:
        try:
            result = func(data)
            if result:
                print(f"  [{num:02d}/27] OK  {desc}  -> {Path(result).name}")
                n_ok += 1
            else:
                print(f"  [{num:02d}/27] --  {desc}  (datos insuficientes)")
                n_skip += 1
        except Exception as e:
            print(f"  [{num:02d}/27] ERR {desc}  ({e})")
            n_fail += 1
        finally:
            plt.close("all")

    print(f"\n{'='*60}")
    print(f"  Resultados: {n_ok} OK | {n_skip} saltados | {n_fail} errores")
    print(f"  Directorio: {GRAFICOS_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
