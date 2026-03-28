"""
Charts nivel museo para IngenIA Licitaciones.

Filosofia: "Engineered Clarity" — cada grafico es una pieza visual,
no un default de matplotlib. Fondo blanco puro, sin grid visible,
sin bordes de axes, paleta reducida, tipografia thin, DPI 200.

Referencia: autonomo/DESIGN_PHILOSOPHY_INGENIA.md

Funciones (todas reciben data dict + path str):
    gen_win_rate_gauge       - Semicirculo limpio con zonas sutiles
    gen_radar_premium        - Radar 8 ejes, relleno navy alpha=0.12
    gen_competitor_bars      - Barras horizontales finas
    gen_timeline             - Linea temporal participaciones
    gen_market_position      - Scatter WR vs bids, empresa destacada
    gen_opportunity_waterfall - Waterfall ingresos -> potencial
    gen_tipo_donut           - Donut LP/LE/L1 limpio
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Arc, Wedge, FancyArrowPatch

from pdf_design import MCOLORS, _name

warnings.filterwarnings("ignore", category=UserWarning)


# ═══════════════════════════════════════════════════════════════
# MUSEO PALETTE — matplotlib 0-1 range, solo 6 colores
# ═══════════════════════════════════════════════════════════════

DPI = 200

_NAVY   = MCOLORS["navy"]          # #0F1B2D — territorio
_DGRAY  = MCOLORS["dark_gray"]     # #2D3748 — texto body
_MGRAY  = MCOLORS["medium_gray"]   # #6B7B8D — captions, secundario
_LBGRAY = MCOLORS["light_bg"]      # #E8ECF0 — fondos sutiles
_GOLD   = MCOLORS["gold_accent"]   # #B8860B — hallazgos clave
_WHITE  = (1.0, 1.0, 1.0)


def _rgba(color, alpha):
    """Crea tupla RGBA desde color RGB + alpha."""
    return (color[0], color[1], color[2], alpha)


def _rc_museo():
    """Aplica rcParams museo globales — sans-serif, sin spines, blanco."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "axes.facecolor": "white",
        "figure.facecolor": "white",
        "axes.grid": False,
        "axes.labelcolor": _MGRAY,
        "xtick.color": _MGRAY,
        "ytick.color": _MGRAY,
    })


def _save(fig, path):
    """Guarda con config museo: DPI 200, fondo blanco, tight layout."""
    fig.savefig(str(path), dpi=DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none", pad_inches=0.08)
    plt.close(fig)


def _empty_chart(figsize, msg, path):
    """Chart vacio con mensaje centrado — fallback elegante."""
    _rc_museo()
    fig, ax = plt.subplots(figsize=figsize)
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            fontsize=9, color=_MGRAY, transform=ax.transAxes,
            fontweight="light")
    ax.axis("off")
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 1. WIN RATE GAUGE — semicirculo limpio
# ═══════════════════════════════════════════════════════════════

def gen_win_rate_gauge(data, path):
    """
    Semicirculo con 3 zonas MUY sutiles (alpha=0.15).
    Needle apuntando al WR. Numero grande (24pt) DEBAJO.
    Label 'Tasa de adjudicacion' arriba en gris small.
    Promedio con linea punteada fina.
    """
    _rc_museo()

    company = data.get("company", {})
    industry = data.get("industry", {})
    wr = float(company.get("win_rate", 0))
    wr_pct = wr * 100
    avg_wr = float(industry.get("avg_win_rate", 0.15)) * 100

    fig, ax = plt.subplots(figsize=(3.2, 2.0))
    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-0.45, 1.15)
    ax.axis("off")

    max_wr_display = 60.0

    # --- Zonas de color MUY sutiles — tonos del sistema, no semaforo ---
    zones = [
        (0, 15,             _rgba(_MGRAY, 0.15)),   # baja: gris medio
        (15, 25,            _rgba(_LBGRAY, 0.40)),   # media: gris claro
        (25, max_wr_display, _rgba(_NAVY, 0.15)),    # alta: navy sutil
    ]

    for start_wr, end_wr, color in zones:
        theta1 = 180 - (end_wr / max_wr_display) * 180
        theta2 = 180 - (start_wr / max_wr_display) * 180
        wedge = Wedge((0, 0), 1.0, theta1, theta2, width=0.28,
                      fc=color, ec="none")
        ax.add_patch(wedge)

    # --- Arcos delimitadores sutiles ---
    arc_outer = Arc((0, 0), 2.0, 2.0, angle=0, theta1=0, theta2=180,
                    color=_rgba(_LBGRAY, 0.6), linewidth=0.8)
    ax.add_patch(arc_outer)
    arc_inner = Arc((0, 0), 1.44, 1.44, angle=0, theta1=0, theta2=180,
                    color=_rgba(_LBGRAY, 0.4), linewidth=0.5)
    ax.add_patch(arc_inner)

    # --- Needle — navy, limpia ---
    needle_wr = min(wr_pct, max_wr_display)
    needle_angle = np.radians(180 - (needle_wr / max_wr_display) * 180)
    needle_len = 0.85
    nx = needle_len * np.cos(needle_angle)
    ny = needle_len * np.sin(needle_angle)
    ax.plot([0, nx], [0, ny], color=_NAVY, linewidth=2.0,
            solid_capstyle="round")
    ax.plot(0, 0, "o", color=_NAVY, markersize=5, zorder=5)

    # --- Marker promedio — linea punteada fina ---
    avg_clamped = min(avg_wr, max_wr_display)
    avg_angle = np.radians(180 - (avg_clamped / max_wr_display) * 180)
    r_in, r_out = 0.74, 1.04
    ax.plot(
        [r_in * np.cos(avg_angle), r_out * np.cos(avg_angle)],
        [r_in * np.sin(avg_angle), r_out * np.sin(avg_angle)],
        color=_MGRAY, linewidth=1.0, linestyle="--", alpha=0.7,
    )
    ax.annotate(
        "Prom. {:.0f}%".format(avg_wr),
        xy=(r_out * 1.08 * np.cos(avg_angle),
            r_out * 1.08 * np.sin(avg_angle)),
        fontsize=6, color=_MGRAY, ha="center", va="bottom",
        fontweight="light",
    )

    # --- Labels de escala — sutiles ---
    for wr_val in [0, 15, 30, 45, max_wr_display]:
        angle = np.radians(180 - (wr_val / max_wr_display) * 180)
        lx = 1.14 * np.cos(angle)
        ly = 1.14 * np.sin(angle)
        ax.text(lx, ly, "{}%".format(int(wr_val)), fontsize=5.5,
                color=_MGRAY, ha="center", va="center", fontweight="light")

    # --- Label arriba ---
    ax.text(0, 1.08, "Tasa de adjudicacion", fontsize=7, color=_MGRAY,
            ha="center", va="bottom", fontweight="light")

    # --- Numero grande (24pt) DEBAJO del gauge ---
    ax.text(0, -0.18, "{:.1f}%".format(wr_pct), fontsize=24,
            fontweight="bold", color=_NAVY, ha="center", va="top")

    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 2. RADAR PREMIUM — 8 ejes, relleno navy
# ═══════════════════════════════════════════════════════════════

def gen_radar_premium(data, path):
    """
    8 ejes. Labels CORTOS (max 12 chars). Font 7pt.
    Relleno navy alpha=0.12. Linea punteada gris P50.
    Valores numericos FUERA del poligono.
    """
    _rc_museo()

    percentiles = data.get("client_percentiles", {})
    if not percentiles:
        _empty_chart((3.5, 3.0), "Sin datos de perfil", path)
        return

    # Orden fijo + labels cortos (max 12 chars)
    label_map = {
        "Win Rate":                "Win Rate",
        "Volumen":                 "Volumen",
        "Adjudicaciones":          "Adjudic.",
        "Monto":                   "Monto",
        "Diversificacion":         "Diversif.",
        "Competidores\nenfrentados": "Competid.",
        "Resiliencia":             "Resiliencia",
        "Actividad\nreciente":     "Actividad",
    }
    order = list(label_map.keys())
    labels_raw = [k for k in order if k in percentiles]
    labels = [label_map[k] for k in labels_raw]
    values = [percentiles[k] for k in labels_raw]

    n = len(labels)
    if n < 3:
        _empty_chart((3.5, 3.0), "Datos insuficientes", path)
        return

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values_closed = values + [values[0]]
    angles_closed = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(3.5, 3.0),
                           subplot_kw={"polar": True})
    fig.patch.set_facecolor("white")

    # --- Linea P50 referencia — gris punteada ---
    p50 = [50] * (n + 1)
    ax.plot(angles_closed, p50, color=_MGRAY, linewidth=0.7,
            linestyle="--", alpha=0.5)

    # --- Relleno navy alpha=0.12 + linea ---
    ax.fill(angles_closed, values_closed, color=_rgba(_NAVY, 0.12))
    ax.plot(angles_closed, values_closed, color=_NAVY, linewidth=1.5)
    ax.scatter(angles, values, color=_NAVY, s=20, zorder=5,
               edgecolors="white", linewidths=0.6)

    # --- Valores numericos FUERA del poligono ---
    for angle, val in zip(angles, values):
        offset_r = 12 if val > 60 else 10
        ax.annotate(
            "{:.0f}".format(val), xy=(angle, val),
            xytext=(angle, val + offset_r),
            fontsize=7, fontweight="bold", color=_NAVY,
            ha="center", va="center",
        )

    # --- Config ejes ---
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=7, color=_DGRAY, fontweight="light")
    ax.set_ylim(0, 105)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=5, color=_MGRAY)
    ax.set_rlabel_position(0)

    # --- Grilla circular muy sutil ---
    ax.grid(True, color=_rgba(_LBGRAY, 0.8), linewidth=0.3)
    ax.spines["polar"].set_color(_rgba(_LBGRAY, 0.5))
    ax.spines["polar"].set_linewidth(0.4)

    plt.tight_layout(pad=0.5)
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 3. RIVAL BARS — barras horizontales finas
# ═══════════════════════════════════════════════════════════════

def gen_competitor_bars(data, path):
    """
    Barras horizontales finas (height=0.25).
    Navy para rival 1, gray para resto.
    Conteo a la derecha. '1 vez' no '1 veces'.
    """
    _rc_museo()

    loss = data.get("loss", {})
    company = data.get("company", {})
    total_lost = int(loss.get("total_lost",
                              company.get("total_lost", 0)) or 0)

    rivals = []
    for i in range(1, 6):
        name = loss.get("top_rival_{}_name".format(i))
        count = loss.get("top_rival_{}_count".format(i), 0)
        if pd.notna(name) and count and int(count) > 0:
            rivals.append((_name(name), int(count)))
    rivals = rivals[:5]

    n = len(rivals)
    fig_h = max(1.4, n * 0.45 + 0.5)
    fig, ax = plt.subplots(figsize=(7.0, fig_h))
    fig.patch.set_facecolor("white")

    if not rivals:
        ax.text(0.5, 0.5, "Sin rivales recurrentes identificados",
                ha="center", va="center", fontsize=9, color=_MGRAY,
                transform=ax.transAxes, fontweight="light")
        ax.axis("off")
        _save(fig, path)
        return

    names = [r[0][:28] for r in rivals]
    counts = [r[1] for r in rivals]
    max_count = max(counts)
    y_pos = np.arange(n)

    # Colores: navy para #1, gris para resto
    colors = [_NAVY if i == 0 else _rgba(_MGRAY, 0.6) for i in range(n)]

    bars = ax.barh(y_pos, counts, height=0.25, color=colors,
                   edgecolor="none")

    # Labels a la derecha con conteo + porcentaje
    for bar, count in zip(bars, counts):
        vez = "vez" if count == 1 else "veces"
        pct_text = ""
        if total_lost > 0:
            pct = count / total_lost * 100
            pct_text = " ({:.0f}%)".format(pct)
        label = "{} {}{}".format(count, vez, pct_text)
        ax.text(bar.get_width() + max_count * 0.04,
                bar.get_y() + bar.get_height() / 2,
                label, ha="left", va="center",
                fontsize=7.5, color=_DGRAY, fontweight="light")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=7.5, color=_DGRAY)
    ax.invert_yaxis()
    ax.set_xlim(0, max_count * 1.45)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.set_xticks([])

    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 4. TIMELINE — participaciones en el tiempo
# ═══════════════════════════════════════════════════════════════

def gen_timeline(data, path):
    """
    Scatter temporal: x=fecha, y=monto. Navy=ganada, gris=perdida.
    Linea de tendencia sutil. Sin grid. Tipografia thin.
    """
    _rc_museo()

    bids = data.get("bid_history", [])
    company = data.get("company", {})

    fig, ax = plt.subplots(figsize=(7.0, 2.5))
    fig.patch.set_facecolor("white")

    if not bids:
        total_bids = int(company.get("total_bids", 0))
        total_wins = int(company.get("total_wins", 0))
        dias = int(company.get("dias_desde_ultima", 0) or 0)

        msg = "Historial detallado no disponible"
        if total_bids > 0:
            msg += "\n{} participaciones | {} adjudicadas".format(
                total_bids, total_wins)
            if dias > 0:
                msg += "\nUltima actividad hace {} dias".format(dias)

        ax.text(0.5, 0.5, msg, ha="center", va="center",
                fontsize=8, color=_MGRAY, transform=ax.transAxes,
                linespacing=1.6, fontweight="light")
        ax.axis("off")
        _save(fig, path)
        return

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

    # --- Perdidas: gris sutil ---
    if dates_lost:
        ax.scatter(dates_lost, [m / 1e6 for m in montos_lost],
                   color=_rgba(_MGRAY, 0.3), s=18, marker="o",
                   edgecolors="none", zorder=3)

    # --- Ganadas: navy con borde blanco ---
    if dates_won:
        ax.scatter(dates_won, [m / 1e6 for m in montos_won],
                   color=_rgba(_NAVY, 0.8), s=28, marker="o",
                   edgecolors="white", linewidths=0.5, zorder=4)

    # --- Trend line sutil ---
    all_dates = dates_won + dates_lost
    all_montos = montos_won + montos_lost
    if len(all_dates) >= 4:
        sorted_idx = np.argsort([d.timestamp() for d in all_dates])
        sorted_dates = [all_dates[i] for i in sorted_idx]
        sorted_montos = [all_montos[i] / 1e6 for i in sorted_idx]
        window = max(3, len(sorted_montos) // 4)
        if len(sorted_montos) >= window:
            ma = pd.Series(sorted_montos).rolling(
                window, min_periods=1).mean()
            ax.plot(sorted_dates, ma, color=_rgba(_NAVY, 0.3),
                    linewidth=1.2, linestyle="-")

    # --- Eje Y en millones ---
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: "${:,.0f}M".format(x).replace(",", ".")))
    ax.tick_params(axis="both", labelsize=7)

    # --- Grid Y minimo ---
    ax.grid(True, axis="y", alpha=0.05, color=_MGRAY, linewidth=0.4)

    plt.tight_layout(pad=0.4)
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 5. MARKET POSITION — scatter WR vs bids
# ═══════════════════════════════════════════════════════════════

def gen_market_position(data, path):
    """
    Points en gris alpha=0.15. Company point en navy grande.
    Cuadrantes como texto MUY sutil (alpha=0.08).
    Lineas de promedios punteadas finas.
    """
    _rc_museo()

    company = data.get("company", {})
    industry = data.get("industry", {})

    comp_wr = float(company.get("win_rate", 0)) * 100
    comp_bids = int(company.get("total_bids", 0))
    avg_wr = float(industry.get("avg_win_rate", 0.15)) * 100
    avg_bids = float(industry.get("avg_bids", 10))

    fig, ax = plt.subplots(figsize=(7.0, 2.5))
    fig.patch.set_facecolor("white")

    # --- Scatter mercado: gris alpha=0.15 ---
    market = data.get("market_scatter", [])
    wr_dist = data.get("wr_distribution", [])
    if market:
        m_bids = [m.get("total_bids", 0) for m in market]
        m_wr = [m.get("win_rate", 0) * 100 for m in market]
        ax.scatter(m_bids, m_wr, color=_rgba(_MGRAY, 0.15), s=10,
                   edgecolors="none", zorder=2)
    elif wr_dist:
        rng = np.random.RandomState(42)
        n_pts = min(len(wr_dist), 300)
        sample_wr = np.array(wr_dist[:n_pts]) * 100
        sample_bids = rng.lognormal(
            mean=np.log(max(avg_bids, 5)), sigma=0.8, size=n_pts)
        sample_bids = np.clip(sample_bids, 1, 200)
        ax.scatter(sample_bids, sample_wr, color=_rgba(_MGRAY, 0.15),
                   s=8, edgecolors="none", zorder=2)

    # --- Lineas de promedio punteadas finas ---
    ax.axhline(avg_wr, color=_MGRAY, linewidth=0.6, linestyle="--",
               alpha=0.4)
    ax.axvline(avg_bids, color=_MGRAY, linewidth=0.6, linestyle="--",
               alpha=0.4)

    # --- Labels de cuadrantes MUY sutiles (alpha=0.08) ---
    quad_labels = [
        (0.22, 0.90, "Bajo vol. / Alta efect."),
        (0.80, 0.90, "Alto vol. / Alta efect."),
        (0.22, 0.08, "Bajo vol. / Baja efect."),
        (0.80, 0.08, "Alto vol. / Baja efect."),
    ]
    for qx, qy, qtxt in quad_labels:
        ax.text(qx, qy, qtxt, transform=ax.transAxes, fontsize=5.5,
                color=_rgba(_MGRAY, 0.35), ha="center", va="center",
                fontweight="light")

    # --- Company point — navy grande con borde gold ---
    ax.plot(comp_bids, comp_wr, "o", color=_NAVY, markersize=10,
            markeredgecolor=_GOLD, markeredgewidth=1.5, zorder=6)

    # --- Label empresa con flecha ---
    offset_x = max(avg_bids * 0.15, 3)
    if comp_bids >= avg_bids:
        offset_x = -offset_x
    ha = "left" if comp_bids < avg_bids else "right"
    ax.annotate(
        "{:.1f}% WR | {} lic.".format(comp_wr, comp_bids),
        xy=(comp_bids, comp_wr),
        xytext=(comp_bids + offset_x, comp_wr + 3),
        fontsize=7, fontweight="bold", color=_NAVY, ha=ha,
        arrowprops={"arrowstyle": "->", "color": _NAVY, "lw": 0.6},
    )

    ax.tick_params(axis="both", labelsize=7)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

    # --- Grid minimo ---
    ax.grid(True, alpha=0.05, color=_MGRAY, linewidth=0.3)

    plt.tight_layout(pad=0.4)
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 6. OPPORTUNITY WATERFALL
# ═══════════════════════════════════════════════════════════════

def gen_opportunity_waterfall(data, path):
    """
    Barras verticales. Actual=navy, increments=gold, total=navy.
    Labels ARRIBA. Lineas conectoras finas.
    """
    _rc_museo()

    company = data.get("company", {})
    industry = data.get("industry", {})

    wr = float(company.get("win_rate", 0))
    total_bids = int(company.get("total_bids", 0))
    monto_prom = float(company.get("monto_promedio", 0) or 0)
    avg_wr = float(industry.get("avg_win_rate", 0.22))
    top10_wr = float(industry.get("top10_win_rate", 0.40))

    wins_actual = int(company.get("total_wins", 0))
    ingreso_actual = wins_actual * monto_prom

    # --- Escenarios incrementales ---
    wr_plus5 = wr + 0.05
    wins_plus5 = total_bids * wr_plus5
    extra_plus5 = max(0, (wins_plus5 - wins_actual)) * monto_prom

    wins_avg = total_bids * avg_wr
    extra_avg = max(0, (wins_avg - wins_actual) * monto_prom - extra_plus5)

    wins_top = total_bids * top10_wr
    extra_top = max(0, (wins_top - wins_actual) * monto_prom
                    - extra_plus5 - max(0, extra_avg))

    potencial_total = (ingreso_actual + extra_plus5
                       + max(0, extra_avg) + max(0, extra_top))

    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    fig.patch.set_facecolor("white")

    labels = ["Actual", "+5pp WR", "Prom. rubro", "Top 10%", "Potencial"]
    bottoms = [
        0,
        ingreso_actual,
        ingreso_actual + extra_plus5,
        ingreso_actual + extra_plus5 + max(0, extra_avg),
        0,
    ]
    heights = [
        ingreso_actual,
        extra_plus5,
        max(0, extra_avg),
        max(0, extra_top),
        potencial_total,
    ]

    # Colores: navy para actual y total, gold para incrementos
    colors = [_NAVY, _GOLD, _GOLD, _GOLD, _NAVY]
    alphas = [0.85, 0.70, 0.55, 0.70, 0.85]

    x = np.arange(len(labels))
    bar_w = 0.50

    for i in range(len(labels)):
        ax.bar(x[i], heights[i], bottom=bottoms[i], width=bar_w,
               color=_rgba(colors[i], alphas[i]), edgecolor="white",
               linewidth=0.5)

        # Labels ARRIBA de cada barra
        total_top = bottoms[i] + heights[i]
        if heights[i] > 0:
            val_mm = heights[i] / 1e6
            prefix = "+" if 0 < i < len(labels) - 1 else ""
            label_text = "{}${:,.0f}MM".format(prefix, val_mm).replace(
                ",", ".")
            ax.text(x[i], total_top + potencial_total * 0.025,
                    label_text, ha="center", va="bottom",
                    fontsize=7.5, fontweight="bold", color=_NAVY)

    # --- Lineas conectoras finas entre barras ---
    for i in range(len(labels) - 2):
        top_i = bottoms[i] + heights[i]
        ax.plot([x[i] + bar_w / 2, x[i + 1] - bar_w / 2],
                [top_i, top_i], color=_MGRAY, linewidth=0.5,
                linestyle="--", alpha=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5, color=_DGRAY,
                       fontweight="light")
    ax.set_ylim(0, potencial_total * 1.18 if potencial_total > 0 else 100)
    ax.set_yticks([])
    ax.tick_params(axis="x", length=0)

    plt.tight_layout(pad=0.4)
    _save(fig, path)


# ═══════════════════════════════════════════════════════════════
# 7. TIPO DONUT — LP/LE/L1
# ═══════════════════════════════════════════════════════════════

def gen_tipo_donut(data, path):
    """
    Centro con total. Colores: navy, medium_gray, light_gray.
    Max 3 slices visibles.
    """
    _rc_museo()

    company = data.get("company", {})
    tipos = {
        "LP": int(company.get("n_LP", 0) or 0),
        "LE": int(company.get("n_LE", 0) or 0),
        "L1": int(company.get("n_L1", 0) or 0),
    }
    total = sum(tipos.values())

    fig, ax = plt.subplots(figsize=(2.8, 2.8))
    fig.patch.set_facecolor("white")

    if total == 0:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center",
                fontsize=9, color=_MGRAY, transform=ax.transAxes,
                fontweight="light")
        ax.axis("off")
        _save(fig, path)
        return

    # Filtrar tipos con 0, max 3 slices
    labels, sizes, donut_colors = [], [], []
    palette = [
        _rgba(_NAVY, 0.85),
        _rgba(_MGRAY, 0.65),
        _rgba(_LBGRAY, 0.80),
    ]
    for i, (label, val) in enumerate(tipos.items()):
        if val > 0:
            labels.append(label)
            sizes.append(val)
            donut_colors.append(palette[i])

    wedges, _ = ax.pie(
        sizes, labels=None, colors=donut_colors,
        startangle=90, counterclock=False,
        wedgeprops={"width": 0.32, "edgecolor": "white", "linewidth": 2},
    )

    # Labels con % sobre cada slice
    for wedge, label, size, dc in zip(wedges, labels, sizes, donut_colors):
        angle = (wedge.theta2 + wedge.theta1) / 2
        x_pos = 0.82 * np.cos(np.radians(angle))
        y_pos = 0.82 * np.sin(np.radians(angle))
        pct = size / total * 100
        # Blanco sobre slices oscuros (navy), gris oscuro en claros
        txt_color = "white" if dc[0] < 0.3 else _DGRAY
        ax.text(x_pos, y_pos,
                "{}\n{:.0f}%".format(label, pct),
                ha="center", va="center",
                fontsize=7, fontweight="bold", color=txt_color)

    # --- Centro: total ---
    ax.text(0, 0.04, str(total), ha="center", va="center",
            fontsize=18, fontweight="bold", color=_NAVY)
    ax.text(0, -0.10, "licitaciones", ha="center", va="center",
            fontsize=6, color=_MGRAY, fontweight="light")

    plt.tight_layout(pad=0.3)
    _save(fig, path)
