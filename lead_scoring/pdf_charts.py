"""
Graficos premium para PDFs de IngenIA Licitaciones.

7 funciones de charts publicacion-ready que usan la paleta de pdf_design.py.
Cada grafico: DPI 200, fondo blanco, sin bordes innecesarios, tipografia consistente.

Funciones:
    gen_win_rate_gauge    - Gauge semicircular con zonas de color
    gen_radar_premium     - Radar 8 ejes con relleno semi-transparente + P50
    gen_competitor_bars   - Barras horizontales con degradado + contexto
    gen_timeline          - Linea temporal participaciones (fecha vs monto)
    gen_market_position   - Scatter WR vs total_bids, empresa destacada
    gen_opportunity_waterfall - Waterfall ingresos actuales -> potencial
    gen_tipo_donut        - Donut LP/LE/L1 con % en centro

Uso:
    from pdf_charts import gen_win_rate_gauge, gen_radar_premium, ...
    gen_win_rate_gauge(data, "/tmp/gauge.png")
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch, Arc, Wedge
from matplotlib.collections import PatchCollection

from pdf_design import COLORS, MCOLORS, _s, _name, _money, _pct

warnings.filterwarnings("ignore", category=UserWarning)

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

DPI = 200
FONT_FAMILY = "sans-serif"

# Colores rapidos
_NAVY = MCOLORS["navy"]
_BLUE = MCOLORS["blue"]
_BLUE_L = MCOLORS["blue_light"]
_GOLD = MCOLORS["gold"]
_GREEN = MCOLORS["green"]
_RED = MCOLORS["red"]
_AMBER = MCOLORS["amber"]
_TEXT = MCOLORS["text_primary"]
_TEXT2 = MCOLORS["text_secondary"]
_MUTED = MCOLORS["text_muted"]
_BORDER = MCOLORS["border"]
_BG = MCOLORS["bg_light"]
_WHITE = (1.0, 1.0, 1.0)


def _style_ax(ax, title="", xlabel="", ylabel="", grid=True):
    """Estilo base consistente para todos los charts."""
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_BORDER)
    ax.spines["bottom"].set_color(_BORDER)
    ax.spines["left"].set_linewidth(0.6)
    ax.spines["bottom"].set_linewidth(0.6)
    if grid:
        ax.grid(True, alpha=0.12, color="#cccccc", linewidth=0.5)
    ax.tick_params(colors=_TEXT2, labelsize=8)
    if title:
        ax.set_title(title, fontweight="bold", color=_NAVY, fontsize=11, pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8, color=_TEXT2)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8, color=_TEXT2)


def _save(fig, path):
    """Guarda figura con configuracion premium."""
    fig.savefig(str(path), dpi=DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none", pad_inches=0.15)
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# 1. WIN RATE GAUGE (semicircular)
# ═══════════════════════════════════════════════════════════════

def gen_win_rate_gauge(data, path):
    """
    Gauge semicircular mostrando Win Rate con zonas de color:
    rojo <15%, amarillo 15-25%, verde >25%. Marker de la empresa.
    """
    company = data.get("company", {})
    industry = data.get("industry", {})
    wr = float(company.get("win_rate", 0))
    wr_pct = wr * 100
    avg_wr = float(industry.get("avg_win_rate", 0.15)) * 100

    fig, ax = plt.subplots(figsize=(4.0, 2.6))
    ax.set_aspect("equal")
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.25, 1.15)
    ax.axis("off")

    # Zonas de color del gauge (0-60% range mapped to 180 degrees)
    max_wr_display = 60.0  # Max WR shown on gauge
    zones = [
        (0, 15, _RED + (0.25,)),
        (15, 25, _AMBER + (0.25,)),
        (25, max_wr_display, _GREEN + (0.25,)),
    ]

    for start_wr, end_wr, color in zones:
        theta1 = 180 - (end_wr / max_wr_display) * 180
        theta2 = 180 - (start_wr / max_wr_display) * 180
        wedge = Wedge((0, 0), 1.0, theta1, theta2, width=0.30, fc=color, ec="none")
        ax.add_patch(wedge)

    # Arco exterior (borde sutil)
    arc = Arc((0, 0), 2.0, 2.0, angle=0, theta1=0, theta2=180,
              color=_BORDER, linewidth=1.0)
    ax.add_patch(arc)
    arc_inner = Arc((0, 0), 1.4, 1.4, angle=0, theta1=0, theta2=180,
                    color=_BORDER, linewidth=0.5)
    ax.add_patch(arc_inner)

    # Needle (aguja) para la empresa
    needle_wr = min(wr_pct, max_wr_display)
    needle_angle = np.radians(180 - (needle_wr / max_wr_display) * 180)
    needle_len = 0.88
    nx = needle_len * np.cos(needle_angle)
    ny = needle_len * np.sin(needle_angle)
    ax.plot([0, nx], [0, ny], color=_NAVY, linewidth=2.5, solid_capstyle="round")
    ax.plot(0, 0, "o", color=_NAVY, markersize=6, zorder=5)

    # Marker promedio rubro (linea punteada)
    avg_angle = np.radians(180 - (min(avg_wr, max_wr_display) / max_wr_display) * 180)
    avg_x_inner = 0.72 * np.cos(avg_angle)
    avg_y_inner = 0.72 * np.sin(avg_angle)
    avg_x_outer = 1.02 * np.cos(avg_angle)
    avg_y_outer = 1.02 * np.sin(avg_angle)
    ax.plot([avg_x_inner, avg_x_outer], [avg_y_inner, avg_y_outer],
            color=_MUTED, linewidth=1.5, linestyle="--")
    ax.annotate("Prom.\n{:.0f}%".format(avg_wr),
                xy=(avg_x_outer, avg_y_outer),
                fontsize=6.5, color=_MUTED, ha="center", va="bottom")

    # Labels de escala
    for wr_val in [0, 15, 25, 40, max_wr_display]:
        angle = np.radians(180 - (wr_val / max_wr_display) * 180)
        lx = 1.12 * np.cos(angle)
        ly = 1.12 * np.sin(angle)
        ax.text(lx, ly, "{}%".format(int(wr_val)), fontsize=6,
                color=_MUTED, ha="center", va="center")

    # Valor central grande
    if wr_pct >= 25:
        val_color = _GREEN
    elif wr_pct >= 15:
        val_color = _AMBER
    else:
        val_color = _RED

    ax.text(0, -0.08, "{:.1f}%".format(wr_pct), fontsize=22,
            fontweight="bold", color=val_color, ha="center", va="top")
    ax.text(0, -0.22, "Win Rate", fontsize=8, color=_TEXT2,
            ha="center", va="top")

    fig.patch.set_facecolor("white")
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 2. RADAR PREMIUM (8 ejes + P50)
# ═══════════════════════════════════════════════════════════════

def gen_radar_premium(data, path):
    """
    Radar chart con 8 ejes, relleno semi-transparente,
    linea de percentil 50% como referencia, labels legibles.
    """
    percentiles = data.get("client_percentiles", {})
    if not percentiles:
        fig, ax = plt.subplots(figsize=(4.0, 3.8))
        ax.text(0.5, 0.5, "Sin datos de perfil", ha="center", va="center",
                fontsize=12, color=_MUTED, transform=ax.transAxes)
        ax.axis("off")
        _save(fig, path)
        return

    # Orden fijo para visual balance
    order = [
        "Win Rate", "Volumen", "Adjudicaciones", "Monto",
        "Diversificacion", "Competidores\nenfrentados",
        "Resiliencia", "Actividad\nreciente",
    ]
    labels = [k for k in order if k in percentiles]
    values = [percentiles[k] for k in labels]

    # Limpiar labels multilinea para matplotlib
    clean_labels = [l.replace("\n", " ") for l in labels]

    N = len(labels)
    if N < 3:
        fig, ax = plt.subplots(figsize=(4.0, 3.8))
        ax.text(0.5, 0.5, "Datos insuficientes", ha="center", va="center",
                fontsize=12, color=_MUTED, transform=ax.transAxes)
        ax.axis("off")
        _save(fig, path)
        return

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(4.0, 3.8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")

    # Linea P50 referencia
    p50_vals = [50] * (N + 1)
    ax.plot(angles_plot, p50_vals, color=_MUTED, linewidth=0.8,
            linestyle="--", alpha=0.6, label="Percentil 50 (mediana)")

    # Relleno de la empresa
    ax.fill(angles_plot, values_plot, color=_BLUE + (0.15,))
    ax.plot(angles_plot, values_plot, color=_BLUE, linewidth=2.0)
    ax.scatter(angles, values, color=_BLUE, s=30, zorder=5, edgecolors="white",
               linewidths=0.8)

    # Valores en cada punto
    for angle, val, label in zip(angles, values, clean_labels):
        offset_r = 8
        ax.annotate("{:.0f}".format(val),
                    xy=(angle, val),
                    xytext=(angle, val + offset_r),
                    fontsize=7, fontweight="bold", color=_NAVY,
                    ha="center", va="center")

    # Config ejes
    ax.set_xticks(angles)
    ax.set_xticklabels(clean_labels, fontsize=7, color=_TEXT)
    ax.set_ylim(0, 105)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=5.5, color=_MUTED)
    ax.set_rlabel_position(0)

    # Grilla circular
    ax.grid(True, color=_BORDER, linewidth=0.4, alpha=0.5)
    ax.spines["polar"].set_color(_BORDER)
    ax.spines["polar"].set_linewidth(0.5)

    # Leyenda
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12),
              fontsize=6, frameon=False, labelcolor=_MUTED)

    ax.set_title("Perfil Competitivo vs. Mercado", fontweight="bold",
                 color=_NAVY, fontsize=11, pad=20)

    plt.tight_layout()
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 3. COMPETITOR BARS (horizontales + contexto)
# ═══════════════════════════════════════════════════════════════

def gen_competitor_bars(data, path):
    """
    Barras horizontales de rivales: degradado rojo->naranja,
    nombre a la izquierda, conteo y % a la derecha.
    Mini-barra gris de contexto (total licitaciones perdidas).
    """
    loss = data.get("loss", {})
    company = data.get("company", {})
    total_lost = int(loss.get("total_lost", company.get("total_lost", 0)) or 0)

    rivals = []
    for i in range(1, 6):
        name = loss.get("top_rival_{}_name".format(i))
        count = loss.get("top_rival_{}_count".format(i), 0)
        if pd.notna(name) and count and int(count) > 0:
            rivals.append((_name(name), int(count)))

    # Limitar a 5 rivales max
    rivals = rivals[:5]

    n_rivals = len(rivals)
    fig_h = max(1.8, n_rivals * 0.65 + 0.8)
    fig, ax = plt.subplots(figsize=(5.5, fig_h))
    fig.patch.set_facecolor("white")

    if not rivals:
        ax.text(0.5, 0.5, "Sin rivales recurrentes identificados",
                ha="center", va="center", fontsize=10, color=_MUTED,
                transform=ax.transAxes)
        ax.axis("off")
        _save(fig, path)
        return

    names = [r[0][:30] for r in rivals]
    counts = [r[1] for r in rivals]
    max_count = max(counts)
    ctx_max = max(total_lost, max_count) if total_lost > 0 else max_count * 1.5

    # Degradado rojo -> naranja
    n = len(rivals)
    gradient_colors = []
    for i in range(n):
        t = i / max(n - 1, 1)
        r = _RED[0] + (_AMBER[0] - _RED[0]) * t
        g = _RED[1] + (_AMBER[1] - _RED[1]) * t
        b = _RED[2] + (_AMBER[2] - _RED[2]) * t
        gradient_colors.append((r, g, b))

    y_pos = np.arange(n)

    # Mini-barras de contexto (total perdidas)
    if total_lost > 0:
        ax.barh(y_pos, [total_lost] * n, height=0.45,
                color=_BG, edgecolor="none", label="Total perdidas")

    # Barras de rivales
    bars = ax.barh(y_pos, counts, height=0.45,
                   color=gradient_colors, edgecolor="none")

    # Labels
    for i, (bar, count) in enumerate(zip(bars, counts)):
        pct = (count / total_lost * 100) if total_lost > 0 else 0
        label = "{} veces".format(count)
        if total_lost > 0:
            label += " ({:.0f}%)".format(pct)
        ax.text(bar.get_width() + ctx_max * 0.02,
                bar.get_y() + bar.get_height() / 2,
                label, ha="left", va="center",
                fontweight="bold", fontsize=8, color=_NAVY)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=8, color=_TEXT)
    ax.invert_yaxis()
    ax.set_xlim(0, ctx_max * 1.35)

    _style_ax(ax, title="Rivales que Mas Te Ganan", xlabel="Adjudicaciones ganadas vs tu empresa")

    # Remover Y-axis spine
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    plt.tight_layout()
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 4. TIMELINE (participaciones en el tiempo)
# ═══════════════════════════════════════════════════════════════

def gen_timeline(data, path):
    """
    Linea temporal de participaciones: x=fecha, y=monto, color=gano/perdio.
    Muestra tendencia con linea suavizada.
    NUEVO: el PDF actual no tiene este grafico.
    """
    bids = data.get("bid_history", [])
    company = data.get("company", {})

    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    fig.patch.set_facecolor("white")

    if not bids:
        # Fallback: mostrar resumen basico con datos de company
        total_bids = int(company.get("total_bids", 0))
        total_wins = int(company.get("total_wins", 0))
        dias = int(company.get("dias_desde_ultima", 0) or 0)

        msg = "Historial detallado no disponible"
        if total_bids > 0:
            msg += "\n{} participaciones | {} adjudicadas".format(total_bids, total_wins)
            if dias > 0:
                msg += "\nUltima actividad hace {} dias".format(dias)

        ax.text(0.5, 0.5, msg, ha="center", va="center",
                fontsize=9, color=_MUTED, transform=ax.transAxes,
                linespacing=1.6)
        ax.axis("off")
        _save(fig, path)
        return

    # Si hay datos de bid_history (list of dicts con fecha, monto, ganado)
    dates_won, montos_won = [], []
    dates_lost, montos_lost = [], []

    for bid in bids:
        fecha = pd.to_datetime(bid.get("fecha"), errors="coerce")
        monto = float(bid.get("monto", 0) or 0)
        ganado = bid.get("ganado", False)
        if pd.isna(fecha):
            continue
        if ganado:
            dates_won.append(fecha)
            montos_won.append(monto)
        else:
            dates_lost.append(fecha)
            montos_lost.append(monto)

    # Plot perdidas primero (fondo)
    if dates_lost:
        ax.scatter(dates_lost, [m / 1e6 for m in montos_lost],
                   color=_RED + (0.4,), s=25, marker="x",
                   label="No adjudicada", zorder=3)
    # Plot ganadas encima
    if dates_won:
        ax.scatter(dates_won, [m / 1e6 for m in montos_won],
                   color=_GREEN + (0.7,), s=35, marker="o",
                   edgecolors=_GREEN, linewidths=0.8,
                   label="Adjudicada", zorder=4)

    # Trend line (si hay suficientes puntos)
    all_dates = dates_won + dates_lost
    all_montos = montos_won + montos_lost
    if len(all_dates) >= 4:
        sorted_idx = np.argsort([d.timestamp() for d in all_dates])
        sorted_dates = [all_dates[i] for i in sorted_idx]
        sorted_montos = [all_montos[i] / 1e6 for i in sorted_idx]

        # Moving average simple
        window = max(3, len(sorted_montos) // 4)
        if len(sorted_montos) >= window:
            ma = pd.Series(sorted_montos).rolling(window, min_periods=1).mean()
            ax.plot(sorted_dates, ma, color=_BLUE + (0.5,), linewidth=1.5,
                    linestyle="-", label="Tendencia")

    _style_ax(ax, title="Historial de Participaciones",
              xlabel="", ylabel="Monto ($MM)")

    ax.legend(fontsize=6.5, loc="upper left", frameon=True,
              facecolor="white", edgecolor=_BORDER, framealpha=0.9)

    # Formato eje Y en millones
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: "${:,.0f}".format(x).replace(",", ".")))

    plt.tight_layout()
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 5. MARKET POSITION (scatter WR vs bids)
# ═══════════════════════════════════════════════════════════════

def gen_market_position(data, path):
    """
    Scatter plot WR vs total_bids. Empresa como punto grande destacado.
    Promedio marcado. Muestra donde esta vs el mercado.
    """
    company = data.get("company", {})
    industry = data.get("industry", {})
    wr_dist = data.get("wr_distribution", [])

    comp_wr = float(company.get("win_rate", 0)) * 100
    comp_bids = int(company.get("total_bids", 0))
    avg_wr = float(industry.get("avg_win_rate", 0.15)) * 100
    avg_bids = float(industry.get("avg_bids", 10))

    fig, ax = plt.subplots(figsize=(5.0, 3.5))
    fig.patch.set_facecolor("white")

    # Scatter de todas las empresas (si hay datos de market_scatter)
    market = data.get("market_scatter", [])
    if market:
        m_bids = [m.get("total_bids", 0) for m in market]
        m_wr = [m.get("win_rate", 0) * 100 for m in market]
        ax.scatter(m_bids, m_wr, color=_BORDER, s=12, alpha=0.35,
                   edgecolors="none", zorder=2)
    elif wr_dist:
        # Simular scatter con distribucion WR + ruido en bids
        rng = np.random.RandomState(42)
        n = min(len(wr_dist), 300)
        sample_wr = np.array(wr_dist[:n]) * 100
        sample_bids = rng.lognormal(mean=np.log(max(avg_bids, 5)), sigma=0.8, size=n)
        sample_bids = np.clip(sample_bids, 1, 200)
        ax.scatter(sample_bids, sample_wr, color=_BORDER, s=10, alpha=0.3,
                   edgecolors="none", zorder=2)

    # Lineas de promedio
    ax.axhline(avg_wr, color=_MUTED, linewidth=0.8, linestyle="--", alpha=0.5)
    ax.axvline(avg_bids, color=_MUTED, linewidth=0.8, linestyle="--", alpha=0.5)

    # Labels de cuadrantes
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    quad_labels = [
        (0.25, 0.92, "Bajo volumen\nAlta efectividad", _GREEN),
        (0.82, 0.92, "Alto volumen\nAlta efectividad", _GREEN),
        (0.25, 0.06, "Bajo volumen\nBaja efectividad", _RED),
        (0.82, 0.06, "Alto volumen\nBaja efectividad", _AMBER),
    ]
    for qx, qy, qtxt, qcolor in quad_labels:
        ax.text(qx, qy, qtxt, transform=ax.transAxes, fontsize=5.5,
                color=qcolor + (0.5,), ha="center", va="center",
                style="italic")

    # Promedio marcado
    ax.plot(avg_bids, avg_wr, "D", color=_MUTED, markersize=7, zorder=4)
    ax.annotate("Promedio\nmercado", xy=(avg_bids, avg_wr),
                xytext=(avg_bids + 5, avg_wr + 4),
                fontsize=6, color=_MUTED, ha="left",
                arrowprops=dict(arrowstyle="->", color=_MUTED, lw=0.6))

    # Empresa (punto grande destacado)
    ax.plot(comp_bids, comp_wr, "o", color=_NAVY, markersize=12,
            markeredgecolor=_GOLD, markeredgewidth=2.0, zorder=6)
    # Label empresa
    offset_x = 5 if comp_bids < avg_bids else -5
    ha = "left" if comp_bids < avg_bids else "right"
    ax.annotate("Tu empresa\n{:.1f}% WR | {} lic.".format(comp_wr, comp_bids),
                xy=(comp_bids, comp_wr),
                xytext=(comp_bids + offset_x, comp_wr + 3),
                fontsize=7, fontweight="bold", color=_NAVY, ha=ha,
                arrowprops=dict(arrowstyle="->", color=_NAVY, lw=0.8))

    _style_ax(ax, title="Posicion en el Mercado",
              xlabel="Total licitaciones", ylabel="Win Rate (%)")

    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

    plt.tight_layout()
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 6. OPPORTUNITY WATERFALL
# ═══════════════════════════════════════════════════════════════

def gen_opportunity_waterfall(data, path):
    """
    Waterfall chart: ingresos actuales -> gap vs promedio -> gap vs top10% -> potencial.
    NO usa barh simple. Cada bloque se apila visualmente.
    """
    company = data.get("company", {})
    industry = data.get("industry", {})
    loss = data.get("loss", {})

    wr = float(company.get("win_rate", 0))
    total_bids = int(company.get("total_bids", 0))
    monto_prom = float(company.get("monto_promedio", 0) or 0)
    avg_wr = float(industry.get("avg_win_rate", 0.22))
    top10_wr = float(industry.get("top10_win_rate", 0.40))

    # Calcular escenarios
    wins_actual = int(company.get("total_wins", 0))
    ingreso_actual = wins_actual * monto_prom

    # +5pp WR
    wr_plus5 = wr + 0.05
    wins_plus5 = total_bids * wr_plus5
    extra_plus5 = max(0, (wins_plus5 - wins_actual)) * monto_prom

    # Promedio rubro
    wins_avg = total_bids * avg_wr
    extra_avg = max(0, (wins_avg - wins_actual)) * monto_prom - extra_plus5

    # Top 10%
    wins_top = total_bids * top10_wr
    extra_top = max(0, (wins_top - wins_actual)) * monto_prom - extra_plus5 - max(0, extra_avg)

    potencial_total = ingreso_actual + extra_plus5 + max(0, extra_avg) + max(0, extra_top)

    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    fig.patch.set_facecolor("white")

    # Datos del waterfall
    labels = ["Actual", "+5pp WR", "Prom. rubro", "Top 10%", "Potencial"]
    values_raw = [ingreso_actual, extra_plus5, max(0, extra_avg), max(0, extra_top), potencial_total]

    # Posiciones
    x = np.arange(len(labels))
    bar_width = 0.55

    # Calcular bottoms para waterfall
    bottoms = [0, ingreso_actual, ingreso_actual + extra_plus5,
               ingreso_actual + extra_plus5 + max(0, extra_avg), 0]
    heights = [ingreso_actual, extra_plus5, max(0, extra_avg), max(0, extra_top), potencial_total]

    colors = [_BLUE, _GREEN, _GREEN, _GOLD, _NAVY]
    alphas = [0.8, 0.7, 0.6, 0.7, 0.9]

    for i in range(len(labels)):
        ax.bar(x[i], heights[i], bottom=bottoms[i], width=bar_width,
               color=colors[i] + (alphas[i],), edgecolor="white", linewidth=0.5)

        # Valor encima
        total_top = bottoms[i] + heights[i]
        if heights[i] > 0:
            val_mm = heights[i] / 1e6
            if i == 0 or i == len(labels) - 1:
                label_text = "${:,.0f}MM".format(val_mm).replace(",", ".")
            else:
                label_text = "+${:,.0f}MM".format(val_mm).replace(",", ".")

            ax.text(x[i], total_top + potencial_total * 0.02,
                    label_text, ha="center", va="bottom",
                    fontsize=8, fontweight="bold", color=_NAVY)

    # Lineas conectoras entre barras
    for i in range(len(labels) - 2):
        top_i = bottoms[i] + heights[i]
        ax.plot([x[i] + bar_width / 2, x[i + 1] - bar_width / 2],
                [top_i, top_i], color=_MUTED, linewidth=0.6,
                linestyle="--")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, color=_TEXT)
    ax.set_ylim(0, potencial_total * 1.2 if potencial_total > 0 else 100)

    _style_ax(ax, title="Oportunidad de Ingresos Adicionales", ylabel="$MM CLP")

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda val, _: "${:,.0f}MM".format(val / 1e6).replace(",", ".")))

    # Remover spine inferior para look cleaner
    ax.spines["bottom"].set_visible(True)

    plt.tight_layout()
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 7. TIPO DONUT (LP/LE/L1)
# ═══════════════════════════════════════════════════════════════

def gen_tipo_donut(data, path):
    """
    Donut chart de distribucion LP/LE/L1 con % en el centro.
    NO barras — donut elegante.
    """
    company = data.get("company", {})

    tipos = {
        "LP (Mayor cuantia)": int(company.get("n_LP", 0) or 0),
        "LE (Media cuantia)": int(company.get("n_LE", 0) or 0),
        "L1 (Menor cuantia)": int(company.get("n_L1", 0) or 0),
    }
    total = sum(tipos.values())

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    fig.patch.set_facecolor("white")

    if total == 0:
        ax.text(0.5, 0.5, "Sin datos\nde tipo", ha="center", va="center",
                fontsize=11, color=_MUTED, transform=ax.transAxes)
        ax.axis("off")
        _save(fig, path)
        return

    # Filtrar tipos con 0
    labels = []
    sizes = []
    colors_list = [_NAVY + (0.85,), _BLUE + (0.75,), _BLUE_L + (0.65,)]
    final_colors = []
    for i, (label, val) in enumerate(tipos.items()):
        if val > 0:
            labels.append(label)
            sizes.append(val)
            final_colors.append(colors_list[i])

    # Donut
    wedges, texts = ax.pie(
        sizes, labels=None, colors=final_colors,
        startangle=90, counterclock=False,
        wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
    )

    # Labels con porcentaje
    for i, (wedge, label, size) in enumerate(zip(wedges, labels, sizes)):
        angle = (wedge.theta2 + wedge.theta1) / 2
        x_pos = 0.78 * np.cos(np.radians(angle))
        y_pos = 0.78 * np.sin(np.radians(angle))
        pct = size / total * 100
        ax.text(x_pos, y_pos, "{:.0f}%".format(pct),
                ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")

    # Centro: total
    ax.text(0, 0.04, str(total), ha="center", va="center",
            fontsize=20, fontweight="bold", color=_NAVY)
    ax.text(0, -0.12, "licitaciones", ha="center", va="center",
            fontsize=7, color=_TEXT2)

    # Leyenda debajo
    legend_labels = ["{}: {} ({:.0f}%)".format(l, s, s / total * 100)
                     for l, s in zip(labels, sizes)]
    ax.legend(wedges, legend_labels, loc="lower center",
              bbox_to_anchor=(0.5, -0.12), fontsize=6.5,
              frameon=False, ncol=1, labelcolor=_TEXT)

    ax.set_title("Distribucion por Tipo", fontweight="bold",
                 color=_NAVY, fontsize=11, pad=12)

    plt.tight_layout()
    _save(fig, path)
