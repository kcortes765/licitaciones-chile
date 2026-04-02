"""
pdf_charts.py — Charts limpios para IngenIA Licitaciones (v3).

Cada funcion recibe figsize_inches como parametro.
El caller calcula figsize basado en espacio disponible en mm:
    figsize = (w_mm / 25.4, h_mm / 25.4)

ZERO text overlap. Font sizes pequenos (7-9pt labels, 12pt max destacados).
Solo 3 colores: navy=#1B2A4A, gold=#B8860B, gray=#AAAAAA.
DPI 200 siempre.

Standalone test: python pdf_charts.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Arc

warnings.filterwarnings("ignore", category=UserWarning)

# ───────────────────────────────────────────────────────────
# Paleta — solo 3 colores (RGB 0-1 para matplotlib)
# ───────────────────────────────────────────────────────────
NAVY = (0x1B / 255, 0x2A / 255, 0x4A / 255)    # #1B2A4A
GOLD = (0xB8 / 255, 0x86 / 255, 0x0B / 255)    # #B8860B
GRAY = (0xAA / 255, 0xAA / 255, 0xAA / 255)    # #AAAAAA
WHITE = (1.0, 1.0, 1.0)

DPI = 200

DEFAULT_FIGSIZE = (3.0, 2.5)


def _rgba(color, alpha):
    """RGB tuple + alpha -> RGBA tuple."""
    return (color[0], color[1], color[2], alpha)


def _rc():
    """Aplica rcParams globales: sin spines, sin grid, fondo blanco."""
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
        "axes.labelcolor": GRAY,
        "xtick.color": GRAY,
        "ytick.color": GRAY,
    })


def _save(fig, path):
    """Guarda con DPI 200, fondo blanco, tight layout."""
    fig.savefig(str(path), dpi=DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none", pad_inches=0.06)
    plt.close(fig)


def _empty(figsize, msg, path):
    """Chart vacio con mensaje centrado — fallback elegante."""
    _rc()
    fig, ax = plt.subplots(figsize=figsize)
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            fontsize=8, color=GRAY, transform=ax.transAxes)
    ax.axis("off")
    _save(fig, path)


def _safe_float(val, default=0.0):
    """NaN-safe float conversion."""
    try:
        v = float(val)
        return default if np.isnan(v) or np.isinf(v) else v
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=0):
    """NaN-safe int conversion."""
    return int(_safe_float(val, default))


def _safe_str(val, default=""):
    """NaN-safe string conversion."""
    import pandas as pd
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    return str(val).strip() or default


def _name(raw):
    """Nombre limpio: titulo case, max 28 chars."""
    s = _safe_str(raw)
    if not s:
        return "N/D"
    s = s.strip().title()
    return s[:28] + "..." if len(s) > 28 else s


# ═══════════════════════════════════════════════════════════
# 1. GAUGE CHART — semicirculo simple
# ═══════════════════════════════════════════════════════════

def gauge_chart(wr, avg_wr, path, figsize=None):
    """Semicirculo con needle al WR. Promedio como linea punteada.

    Args:
        wr: Win rate de la empresa (0-1 o 0-100).
        avg_wr: Win rate promedio industria (0-1 o 0-100).
        path: Ruta de salida PNG.
        figsize: (w_inches, h_inches). Default (3.0, 1.8).
    """
    _rc()
    figsize = figsize or (3.0, 1.8)

    # Normalizar a porcentaje
    wr_pct = _safe_float(wr)
    if wr_pct <= 1.0:
        wr_pct *= 100
    avg_pct = _safe_float(avg_wr, 15.0)
    if avg_pct <= 1.0:
        avg_pct *= 100

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-0.35, 1.15)
    ax.axis("off")

    max_wr = 60.0

    # Zonas sutiles: baja (gray), media (gray claro), alta (navy)
    zones = [
        (0, 15,    _rgba(GRAY, 0.20)),
        (15, 25,   _rgba(GRAY, 0.10)),
        (25, max_wr, _rgba(NAVY, 0.15)),
    ]
    for s, e, color in zones:
        t1 = 180 - (e / max_wr) * 180
        t2 = 180 - (s / max_wr) * 180
        wedge = Wedge((0, 0), 1.0, t1, t2, width=0.28, fc=color, ec="none")
        ax.add_patch(wedge)

    # Arcos delimitadores
    arc_o = Arc((0, 0), 2.0, 2.0, theta1=0, theta2=180,
                color=_rgba(GRAY, 0.4), linewidth=0.7)
    arc_i = Arc((0, 0), 1.44, 1.44, theta1=0, theta2=180,
                color=_rgba(GRAY, 0.3), linewidth=0.4)
    ax.add_patch(arc_o)
    ax.add_patch(arc_i)

    # Needle
    needle_wr = min(wr_pct, max_wr)
    angle = np.radians(180 - (needle_wr / max_wr) * 180)
    nx = 0.85 * np.cos(angle)
    ny = 0.85 * np.sin(angle)
    ax.plot([0, nx], [0, ny], color=NAVY, linewidth=2.0, solid_capstyle="round")
    ax.plot(0, 0, "o", color=NAVY, markersize=5, zorder=5)

    # Marker promedio
    avg_c = min(avg_pct, max_wr)
    avg_a = np.radians(180 - (avg_c / max_wr) * 180)
    r_in, r_out = 0.74, 1.04
    ax.plot([r_in * np.cos(avg_a), r_out * np.cos(avg_a)],
            [r_in * np.sin(avg_a), r_out * np.sin(avg_a)],
            color=GRAY, linewidth=0.8, linestyle="--", alpha=0.7)
    ax.annotate("Prom. {:.0f}%".format(avg_pct),
                xy=(r_out * 1.08 * np.cos(avg_a), r_out * 1.08 * np.sin(avg_a)),
                fontsize=6, color=GRAY, ha="center", va="bottom")

    # Labels escala en extremos
    for val in [0, max_wr]:
        a = np.radians(180 - (val / max_wr) * 180)
        lx, ly = 1.14 * np.cos(a), 1.14 * np.sin(a)
        ax.text(lx, ly, "{}%".format(int(val)), fontsize=5.5,
                color=GRAY, ha="center", va="center")

    # Numero grande debajo
    ax.text(0, -0.15, "{:.1f}%".format(wr_pct), fontsize=12,
            fontweight="bold", color=NAVY, ha="center", va="top")

    _save(fig, path)


# ═══════════════════════════════════════════════════════════
# 2. RADAR CHART — 8 ejes, labels 1 palabra max
# ═══════════════════════════════════════════════════════════

def radar_chart(data_dict, path, figsize=None):
    """Radar de 8 ejes con relleno navy.

    Args:
        data_dict: {label: value(0-100), ...}. Max 8 ejes.
        path: Ruta de salida PNG.
        figsize: (w_inches, h_inches). Default (3.0, 2.8).
    """
    _rc()
    figsize = figsize or (3.0, 2.8)

    if not data_dict or len(data_dict) < 3:
        _empty(figsize, "Datos insuficientes", path)
        return

    # Abreviar labels a 1 palabra (max 10 chars)
    abbrev = {
        "Win Rate": "WinRate",
        "Volumen": "Volumen",
        "Adjudicaciones": "Adjudic.",
        "Monto": "Monto",
        "Diversificacion": "Diversif.",
        "Competidores\nenfrentados": "Compet.",
        "Resiliencia": "Resil.",
        "Actividad\nreciente": "Actividad",
    }

    labels_raw = list(data_dict.keys())[:8]
    labels = [abbrev.get(k, k[:10]) for k in labels_raw]
    values = [_safe_float(data_dict[k]) for k in labels_raw]
    n = len(labels)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values_c = values + [values[0]]
    angles_c = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"polar": True})
    fig.patch.set_facecolor("white")

    # P50 referencia
    p50 = [50] * (n + 1)
    ax.plot(angles_c, p50, color=GRAY, linewidth=0.6, linestyle="--", alpha=0.5)

    # Relleno navy
    ax.fill(angles_c, values_c, color=_rgba(NAVY, 0.12))
    ax.plot(angles_c, values_c, color=NAVY, linewidth=1.5)
    ax.scatter(angles, values, color=NAVY, s=18, zorder=5,
               edgecolors="white", linewidths=0.5)

    # Valores fuera del poligono
    for a, v in zip(angles, values):
        offset = 10 if v > 60 else 8
        ax.annotate("{:.0f}".format(v), xy=(a, v),
                    xytext=(a, v + offset),
                    fontsize=6, fontweight="bold", color=NAVY,
                    ha="center", va="center")

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=6, color=NAVY)
    ax.set_ylim(0, 105)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", ""], fontsize=5, color=GRAY)
    ax.set_rlabel_position(0)
    ax.grid(True, color=_rgba(GRAY, 0.3), linewidth=0.3)
    ax.spines["polar"].set_color(_rgba(GRAY, 0.3))
    ax.spines["polar"].set_linewidth(0.4)

    plt.tight_layout(pad=0.4)
    _save(fig, path)


# ═══════════════════════════════════════════════════════════
# 3. COMPETITOR CHART — barh simples
# ═══════════════════════════════════════════════════════════

def competitor_chart(rivals, path, figsize=None):
    """Barras horizontales: nombre left, count right.

    Args:
        rivals: [(nombre, count), ...] ordenado desc. Max 5.
        path: Ruta de salida PNG.
        figsize: (w_inches, h_inches). Default calculado por n.
    """
    _rc()

    rivals = [(n, c) for n, c in rivals if c and int(c) > 0][:5]
    n = len(rivals)

    if not rivals:
        figsize = figsize or DEFAULT_FIGSIZE
        _empty(figsize, "Sin rivales identificados", path)
        return

    fig_h = max(1.2, n * 0.4 + 0.4)
    figsize = figsize or (3.0, fig_h)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    names = [_name(r[0])[:25] for r in rivals]
    counts = [_safe_int(r[1]) for r in rivals]
    max_c = max(counts) if counts else 1
    y_pos = np.arange(n)

    colors = [NAVY if i == 0 else _rgba(GRAY, 0.6) for i in range(n)]
    bars = ax.barh(y_pos, counts, height=0.3, color=colors, edgecolor="none")

    for bar, count in zip(bars, counts):
        vez = "vez" if count == 1 else "veces"
        ax.text(bar.get_width() + max_c * 0.05,
                bar.get_y() + bar.get_height() / 2,
                "{} {}".format(count, vez),
                ha="left", va="center", fontsize=7, color=NAVY)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=7, color=NAVY)
    ax.invert_yaxis()
    ax.set_xlim(0, max_c * 1.4)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.set_xticks([])

    _save(fig, path)


# ═══════════════════════════════════════════════════════════
# 4. SCATTER CHART — posicion de mercado
# ═══════════════════════════════════════════════════════════

def scatter_chart(company_x, company_y, all_x, all_y, path, figsize=None):
    """Scatter: puntos grises (mercado), empresa navy grande.

    Args:
        company_x: Total bids de la empresa.
        company_y: Win rate de la empresa (0-100).
        all_x: Lista/array de total_bids del mercado.
        all_y: Lista/array de win_rates del mercado (0-100).
        path: Ruta de salida PNG.
        figsize: (w_inches, h_inches). Default (3.0, 2.2).
    """
    _rc()
    figsize = figsize or (3.0, 2.2)

    comp_x = _safe_float(company_x)
    comp_y = _safe_float(company_y)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    # Puntos mercado
    if all_x is not None and all_y is not None and len(all_x) > 0:
        ax.scatter(all_x, all_y, color=_rgba(GRAY, 0.20), s=8,
                   edgecolors="none", zorder=2)

    # Lineas promedio
    if all_x is not None and len(all_x) > 0:
        avg_x = np.nanmean(all_x)
        avg_y = np.nanmean(all_y)
        ax.axhline(avg_y, color=GRAY, linewidth=0.5, linestyle="--", alpha=0.4)
        ax.axvline(avg_x, color=GRAY, linewidth=0.5, linestyle="--", alpha=0.4)

    # Empresa: navy grande con borde gold
    ax.plot(comp_x, comp_y, "o", color=NAVY, markersize=9,
            markeredgecolor=GOLD, markeredgewidth=1.2, zorder=6)

    # Label empresa
    ax.annotate("{:.0f}% | {} lic.".format(comp_y, int(comp_x)),
                xy=(comp_x, comp_y),
                xytext=(8, 6), textcoords="offset points",
                fontsize=7, fontweight="bold", color=NAVY,
                arrowprops={"arrowstyle": "->", "color": NAVY, "lw": 0.5})

    ax.tick_params(axis="both", labelsize=6)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: "{:.0f}%".format(x)))

    _save(fig, path)


# ═══════════════════════════════════════════════════════════
# 5. DONUT CHART — max 3 slices, total en centro
# ═══════════════════════════════════════════════════════════

def donut_chart(data, path, figsize=None):
    """Donut con max 3 slices. Total en centro.

    Args:
        data: dict {label: count, ...}. Max 3 slices.
        path: Ruta de salida PNG.
        figsize: (w_inches, h_inches). Default (2.5, 2.5).
    """
    _rc()
    figsize = figsize or (2.5, 2.5)

    if not data:
        _empty(figsize, "Sin datos", path)
        return

    # Filtrar ceros y limitar a 3
    items = [(k, _safe_int(v)) for k, v in data.items() if _safe_int(v) > 0][:3]
    if not items:
        _empty(figsize, "Sin datos", path)
        return

    labels = [i[0] for i in items]
    sizes = [i[1] for i in items]
    total = sum(sizes)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    palette = [
        _rgba(NAVY, 0.85),
        _rgba(GRAY, 0.65),
        _rgba(GRAY, 0.35),
    ]
    colors = palette[:len(items)]

    wedges, _ = ax.pie(
        sizes, labels=None, colors=colors,
        startangle=90, counterclock=False,
        wedgeprops={"width": 0.32, "edgecolor": "white", "linewidth": 2},
    )

    # Labels sobre slices
    for wedge, label, size, dc in zip(wedges, labels, sizes, colors):
        angle = (wedge.theta2 + wedge.theta1) / 2
        x_pos = 0.82 * np.cos(np.radians(angle))
        y_pos = 0.82 * np.sin(np.radians(angle))
        pct = size / total * 100
        txt_color = "white" if dc[0] < 0.3 else NAVY
        ax.text(x_pos, y_pos,
                "{}\n{:.0f}%".format(label, pct),
                ha="center", va="center",
                fontsize=7, fontweight="bold", color=txt_color)

    # Centro
    ax.text(0, 0.04, str(total), ha="center", va="center",
            fontsize=16, fontweight="bold", color=NAVY)
    ax.text(0, -0.12, "total", ha="center", va="center",
            fontsize=6, color=GRAY)

    plt.tight_layout(pad=0.2)
    _save(fig, path)


# ═══════════════════════════════════════════════════════════
# 6. WATERFALL CHART — barras verticales con labels arriba
# ═══════════════════════════════════════════════════════════

def waterfall_chart(scenarios, path, figsize=None):
    """Waterfall: actual + incrementos (gold) + total (navy).

    Args:
        scenarios: list of (label, bottom, height).
            Primer elemento = actual (navy).
            Intermedios = incrementos (gold).
            Ultimo = total (navy).
        path: Ruta de salida PNG.
        figsize: (w_inches, h_inches). Default (3.5, 2.5).
    """
    _rc()
    figsize = figsize or (3.5, 2.5)

    if not scenarios:
        _empty(figsize, "Sin datos", path)
        return

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    n = len(scenarios)
    labels = [s[0] for s in scenarios]
    bottoms = [_safe_float(s[1]) for s in scenarios]
    heights = [_safe_float(s[2]) for s in scenarios]

    # Colores: primero y ultimo navy, intermedios gold
    colors = []
    for i in range(n):
        if i == 0 or i == n - 1:
            colors.append(_rgba(NAVY, 0.85))
        else:
            colors.append(_rgba(GOLD, 0.70))

    x = np.arange(n)
    bar_w = 0.50

    for i in range(n):
        ax.bar(x[i], heights[i], bottom=bottoms[i], width=bar_w,
               color=colors[i], edgecolor="white", linewidth=0.5)

        # Label arriba
        top = bottoms[i] + heights[i]
        max_top = max(b + h for b, h in zip(bottoms, heights))
        if heights[i] > 0:
            val_mm = heights[i] / 1e6
            prefix = "+" if 0 < i < n - 1 else ""
            label_text = "{}${:,.0f}M".format(prefix, val_mm).replace(",", ".")
            ax.text(x[i], top + max_top * 0.025,
                    label_text, ha="center", va="bottom",
                    fontsize=7, fontweight="bold", color=NAVY)

    # Lineas conectoras
    for i in range(n - 2):
        top_i = bottoms[i] + heights[i]
        ax.plot([x[i] + bar_w / 2, x[i + 1] - bar_w / 2],
                [top_i, top_i], color=GRAY, linewidth=0.4,
                linestyle="--", alpha=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7, color=NAVY)
    max_val = max(b + h for b, h in zip(bottoms, heights))
    ax.set_ylim(0, max_val * 1.15 if max_val > 0 else 100)
    ax.set_yticks([])
    ax.tick_params(axis="x", length=0)

    _save(fig, path)


# ═══════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════

def _test():
    """Genera 6 charts de prueba en /tmp/ con datos dummy."""
    out = Path(tempfile.gettempdir())
    print("Generando charts de prueba en:", out)

    # 1. Gauge
    p1 = out / "test_gauge.png"
    gauge_chart(wr=0.22, avg_wr=0.15, path=str(p1))
    print(f"  1/6 gauge_chart -> {p1} ({p1.stat().st_size:,} bytes)")

    # 2. Radar
    p2 = out / "test_radar.png"
    radar_chart({
        "Win Rate": 65, "Volumen": 40, "Adjudicaciones": 72,
        "Monto": 55, "Diversificacion": 30, "Resiliencia": 80,
        "Actividad\nreciente": 45, "Competidores\nenfrentados": 60,
    }, path=str(p2))
    print(f"  2/6 radar_chart -> {p2} ({p2.stat().st_size:,} bytes)")

    # 3. Competitor
    p3 = out / "test_competitor.png"
    competitor_chart([
        ("Constructora ABC Ltda", 8),
        ("Empresa XYZ S.A.", 5),
        ("Ingenieria Acme", 3),
        ("Obras del Sur", 2),
    ], path=str(p3))
    print(f"  3/6 competitor_chart -> {p3} ({p3.stat().st_size:,} bytes)")

    # 4. Scatter
    p4 = out / "test_scatter.png"
    rng = np.random.RandomState(42)
    all_x = rng.lognormal(mean=2.5, sigma=0.8, size=100).clip(1, 100)
    all_y = rng.uniform(5, 50, size=100)
    scatter_chart(company_x=25, company_y=22, all_x=all_x, all_y=all_y,
                  path=str(p4))
    print(f"  4/6 scatter_chart -> {p4} ({p4.stat().st_size:,} bytes)")

    # 5. Donut
    p5 = out / "test_donut.png"
    donut_chart({"LP": 35, "LE": 12, "L1": 5}, path=str(p5))
    print(f"  5/6 donut_chart -> {p5} ({p5.stat().st_size:,} bytes)")

    # 6. Waterfall
    p6 = out / "test_waterfall.png"
    actual = 500_000_000
    waterfall_chart([
        ("Actual", 0, actual),
        ("+5pp WR", actual, 120_000_000),
        ("Prom. rubro", actual + 120_000_000, 80_000_000),
        ("Top 10%", actual + 200_000_000, 150_000_000),
        ("Potencial", 0, actual + 350_000_000),
    ], path=str(p6))
    print(f"  6/6 waterfall_chart -> {p6} ({p6.stat().st_size:,} bytes)")

    # Verificar todos existen y tienen tamanio razonable
    all_ok = True
    for p in [p1, p2, p3, p4, p5, p6]:
        if not p.exists():
            print(f"  FALLO: {p.name} no existe")
            all_ok = False
        elif p.stat().st_size < 500:
            print(f"  FALLO: {p.name} muy pequeno ({p.stat().st_size} bytes)")
            all_ok = False

    if all_ok:
        print("\n=== 6/6 charts OK ===")
    else:
        print("\n=== ERRORES detectados ===")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════
# ALIASES — compatibilidad con generate_pdf_v2.py (legacy)
# Seran eliminados cuando feature 4 reemplace generate_pdf_v2.py
# ═══════════════════════════════════════════════════════════

def gen_win_rate_gauge(data, path):
    """Legacy wrapper: extrae wr/avg_wr de data dict."""
    company = data.get("company", {})
    industry = data.get("industry", {})
    wr = _safe_float(company.get("win_rate", 0))
    avg = _safe_float(industry.get("avg_win_rate", 0.15))
    gauge_chart(wr, avg, path)


def gen_radar_premium(data, path):
    """Legacy wrapper: extrae percentiles de data dict."""
    percentiles = data.get("client_percentiles", {})
    radar_chart(percentiles, path)


def gen_competitor_bars(data, path):
    """Legacy wrapper: extrae rivales de data dict."""
    import pandas as pd
    loss = data.get("loss", {})
    rivals = []
    for i in range(1, 6):
        name = loss.get("top_rival_{}_name".format(i))
        count = loss.get("top_rival_{}_count".format(i), 0)
        if name is not None and not (isinstance(name, float) and np.isnan(name)):
            c = _safe_int(count)
            if c > 0:
                rivals.append((_name(name), c))
    competitor_chart(rivals, path)


def gen_market_position(data, path):
    """Legacy wrapper: extrae company vs market de data dict."""
    company = data.get("company", {})
    industry = data.get("industry", {})
    comp_wr = _safe_float(company.get("win_rate", 0)) * 100
    comp_bids = _safe_int(company.get("total_bids", 0))
    avg_wr = _safe_float(industry.get("avg_win_rate", 0.15)) * 100
    avg_bids = _safe_float(industry.get("avg_bids", 10))
    # Generar scatter simulado si no hay datos de mercado
    market = data.get("market_scatter", [])
    wr_dist = data.get("wr_distribution", [])
    all_x, all_y = [], []
    if market:
        all_x = [m.get("total_bids", 0) for m in market]
        all_y = [m.get("win_rate", 0) * 100 for m in market]
    elif wr_dist:
        rng = np.random.RandomState(42)
        n_pts = min(len(wr_dist), 300)
        all_y = list(np.array(wr_dist[:n_pts]) * 100)
        all_x = list(np.clip(rng.lognormal(
            mean=np.log(max(avg_bids, 5)), sigma=0.8, size=n_pts), 1, 200))
    scatter_chart(comp_bids, comp_wr, all_x, all_y, path)


def gen_timeline(data, path):
    """Legacy wrapper: timeline no reimplementada en v3, genera chart vacio."""
    _empty((3.0, 2.0), "Timeline no disponible en v3", path)


def gen_tipo_donut(data, path):
    """Legacy wrapper: extrae LP/LE/L1 de data dict."""
    company = data.get("company", {})
    tipos = {
        "LP": _safe_int(company.get("n_LP", 0)),
        "LE": _safe_int(company.get("n_LE", 0)),
        "L1": _safe_int(company.get("n_L1", 0)),
    }
    donut_chart(tipos, path)


def gen_opportunity_waterfall(data, path):
    """Legacy wrapper: calcula escenarios de data dict."""
    company = data.get("company", {})
    industry = data.get("industry", {})

    wr = _safe_float(company.get("win_rate", 0))
    total_bids = _safe_int(company.get("total_bids", 0))
    monto_prom = _safe_float(company.get("monto_promedio", 0))
    avg_wr = _safe_float(industry.get("avg_win_rate", 0.22))
    top10_wr = _safe_float(industry.get("top10_win_rate", 0.40))

    wins_actual = _safe_int(company.get("total_wins", 0))
    ingreso_actual = wins_actual * monto_prom

    wr_plus5 = wr + 0.05
    wins_plus5 = total_bids * wr_plus5
    extra_plus5 = max(0, (wins_plus5 - wins_actual)) * monto_prom

    wins_avg = total_bids * avg_wr
    extra_avg = max(0, (wins_avg - wins_actual) * monto_prom - extra_plus5)

    wins_top = total_bids * top10_wr
    extra_top = max(0, (wins_top - wins_actual) * monto_prom
                    - extra_plus5 - max(0, extra_avg))

    potencial_total = ingreso_actual + extra_plus5 + max(0, extra_avg) + max(0, extra_top)

    scenarios = [
        ("Actual", 0, ingreso_actual),
        ("+5pp WR", ingreso_actual, extra_plus5),
        ("Prom. rubro", ingreso_actual + extra_plus5, max(0, extra_avg)),
        ("Top 10%", ingreso_actual + extra_plus5 + max(0, extra_avg), max(0, extra_top)),
        ("Potencial", 0, potencial_total),
    ]
    waterfall_chart(scenarios, path)


if __name__ == "__main__":
    _test()
