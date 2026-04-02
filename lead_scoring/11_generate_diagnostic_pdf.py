"""
11 - Generador de PDF Diagnostico por RUT.

Genera un PDF profesional de 6 paginas ("Examen Medico Corporativo"):
  Pag 1: Portada + resumen ejecutivo + ranking statement
  Pag 2: Desempeno vs mercado (win rate + radar + histograma)
  Pag 3: Inteligencia competitiva (rivales + insight + tabla comparativa)
  Pag 4: Tendencias y sectores (tipo L1/LE/LP + region + montos)
  Pag 5: Costo de oportunidad (+5% WR = cuanto mas ingresos)
  Pag 6: CTA / servicios (cierre comercial)

Workflow con IA en el loop:
  1. python 11_generate_diagnostic_pdf.py <RUT>
     -> Genera PDF + notas JSON para personalizacion
  2. Claude/IA revisa notas JSON y mejora texto
  3. python 11_generate_diagnostic_pdf.py <RUT>
     -> Regenera PDF con texto personalizado

Uso:
  python 11_generate_diagnostic_pdf.py 137981-3
  python 11_generate_diagnostic_pdf.py 137981-3 --output custom.pdf
  python 11_generate_diagnostic_pdf.py --list-top 10
"""
from __future__ import annotations

import sys
import os
import re
import json
import tempfile
import shutil
import warnings
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from fpdf import FPDF

from config import FILTERED_DIR, OUTPUT_DIR
from pipeline_validation import (
    assert_client_safe_binary,
    assert_client_safe_json,
    write_run_manifest,
)
from utils import print_header

warnings.filterwarnings(
    "ignore",
    message='The parameter "ln" is deprecated*',
    category=DeprecationWarning,
)

# ── Directorio de salida ──
DIAG_DIR = OUTPUT_DIR / "diagnosticos"

# ── Paleta de colores ──
C_NAVY   = (27, 42, 74)
C_BLUE   = (46, 134, 171)
C_GREEN  = (40, 167, 69)
C_RED    = (220, 53, 69)
C_ORANGE = (230, 126, 34)
C_LIGHT  = (245, 247, 250)
C_WHITE  = (255, 255, 255)
C_TEXT   = (51, 51, 51)
C_GRAY   = (150, 150, 150)

# Matplotlib (0-1)
MC_NAVY  = tuple(c / 255 for c in C_NAVY)
MC_BLUE  = tuple(c / 255 for c in C_BLUE)
MC_GREEN = tuple(c / 255 for c in C_GREEN)
MC_RED   = tuple(c / 255 for c in C_RED)
MC_ORANGE = tuple(c / 255 for c in C_ORANGE)

# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════

def _s(text):
    """Safe text for fpdf2 (latin-1 compatible)."""
    if pd.isna(text) or text is None:
        return ""
    text = str(text).replace('\ufffd', 'o')  # Fix mojibake
    try:
        text.encode('latin-1')
        return text
    except UnicodeEncodeError:
        return text.encode('latin-1', errors='replace').decode('latin-1')


def _name(raw):
    """Clean company name for display."""
    name = _s(raw)
    if '|' in name:
        parts = [p.strip() for p in name.split('|')]
        non_upper = [p for p in parts if not p.isupper() and len(p) > 3]
        if non_upper:
            return non_upper[0]
        return min(parts, key=len)
    return name


def _money(amount):
    """Format CLP amount."""
    if pd.isna(amount) or amount == 0:
        return "$0"
    a = float(amount)
    if a >= 1e6:
        return ("$" + "{:,.0f}".format(a / 1e6) + "MM").replace(",", ".")
    if a >= 1e3:
        return ("$" + "{:,.0f}".format(a)).replace(",", ".")
    return "${:,.0f}".format(a).replace(",", ".")


def _pct(value):
    """Format as percentage."""
    if pd.isna(value):
        return "N/A"
    return "{:.1f}%".format(float(value) * 100)


# ═══════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════

def load_data(rut):
    """Load all data for a RUT from parquets."""
    data = {"rut": rut, "found": False}

    # Try sources in priority order
    for parquet in ["leads_enriched.parquet", "leads_ml_ranked.parquet",
                    "leads_ranked.parquet", "company_database.parquet"]:
        path = FILTERED_DIR / parquet
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        match = df[df["rut"] == rut]
        if len(match) > 0:
            data["company"] = match.iloc[0].to_dict()
            data["found"] = True
            data["source"] = parquet
            break

    if not data["found"]:
        return data

    # Loss analysis
    loss_path = OUTPUT_DIR / "loss_analysis.parquet"
    if loss_path.exists():
        loss_df = pd.read_parquet(loss_path)
        loss_match = loss_df[loss_df["rut"] == rut]
        if len(loss_match) > 0:
            data["loss"] = loss_match.iloc[0].to_dict()

    # Industry stats (all companies with 3+ bids)
    db_path = FILTERED_DIR / "company_database.parquet"
    if db_path.exists():
        db = pd.read_parquet(db_path)
        active = db[db["total_bids"] >= 3]
        data["industry"] = {
            "avg_win_rate": float(active["win_rate"].mean()),
            "median_win_rate": float(active["win_rate"].median()),
            "avg_bids": float(active["total_bids"].mean()),
            "total_companies": len(db),
            "active_companies": len(active),
            "avg_monto_promedio": float(active["monto_promedio"].mean()) if "monto_promedio" in active.columns else 0,
        }
        # Top 10% win rate threshold
        top10_wr = float(active["win_rate"].quantile(0.90))
        data["industry"]["top10_win_rate"] = top10_wr

    # Client-facing percentiles (position vs market, NOT internal scores)
    db_path2 = FILTERED_DIR / "company_database.parquet"
    if db_path2.exists():
        db2 = pd.read_parquet(db_path2)
        active2 = db2[db2["total_bids"] >= 3].copy()

        # Percentile radar: where does this company rank in each public metric?
        company = data["company"]
        radar_metrics = {
            "Win Rate":       ("win_rate",           float(company.get("win_rate", 0))),
            "Volumen":        ("total_bids",         float(company.get("total_bids", 0))),
            "Monto":          ("monto_promedio",     float(company.get("monto_promedio", 0))),
            "Adjudicaciones": ("total_wins",         float(company.get("total_wins", 0))),
            "Competidores\nenfrentados": ("n_distinct_rivals", float(company.get("n_distinct_rivals", 0))),
            "Actividad\nreciente": ("dias_desde_ultima", 0),  # special: lower is better
        }

        percentiles = {}
        for label, (col, val) in radar_metrics.items():
            if col in active2.columns:
                col_data = active2[col].dropna()
                if len(col_data) > 0:
                    if col == "dias_desde_ultima":
                        # Lower days = more recent = better, so invert
                        val = float(company.get(col, 9999))
                        pct = float((col_data >= val).sum() / len(col_data) * 100)
                    else:
                        pct = float((col_data <= val).sum() / len(col_data) * 100)
                    percentiles[label] = min(pct, 100)
                else:
                    percentiles[label] = 50
            else:
                percentiles[label] = 50

        # Diversificación: cuántos tipos de licitación usa (L1, LE, LP)
        n_tipos = sum(1 for t in ["n_L1", "n_LE", "n_LP"]
                      if int(company.get(t, 0) or 0) > 0)
        percentiles["Diversificacion"] = [0, 33, 66, 100][min(n_tipos, 3)]

        # Resiliencia: inversa de loss_rate (menos derrotas = mejor)
        loss = data.get("loss", {})
        _lr = loss.get("loss_rate")
        loss_rate = float(_lr) if _lr is not None and not (isinstance(_lr, float) and _lr != _lr) else 0.5
        loss_col = active2["total_lost"].dropna() / active2["total_bids"].clip(lower=1) if "total_lost" in active2.columns else None
        if loss_col is not None and len(loss_col) > 0:
            percentiles["Resiliencia"] = float((loss_col >= loss_rate).sum() / len(loss_col) * 100)
        else:
            percentiles["Resiliencia"] = max(0, (1 - loss_rate) * 100)

        data["client_percentiles"] = percentiles

        active2 = active2.sort_values("win_rate", ascending=False).reset_index(drop=True)
        data["total_active"] = len(active2)
        wr_match = active2[active2["rut"] == rut]
        if len(wr_match) > 0:
            data["wr_rank"] = int(wr_match.index[0]) + 1
        data["wr_distribution"] = active2["win_rate"].dropna().tolist()

    return data


# ═══════════════════════════════════════════════
# CHART GENERATION
# ═══════════════════════════════════════════════

def _apply_style():
    """Professional chart styling."""
    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'axes.grid': True,
        'grid.alpha': 0.15,
        'grid.color': '#cccccc',
        'font.family': 'sans-serif',
        'font.size': 10,
        'axes.spines.top': False,
        'axes.spines.right': False,
    })


def gen_win_rate_chart(data, path):
    """Bar chart: empresa vs promedio del rubro."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(3.4, 2.8))

    wr_empresa = float(data["company"].get("win_rate", 0)) * 100
    wr_rubro = float(data.get("industry", {}).get("avg_win_rate", 0.15)) * 100

    bars = ax.bar(
        ["Tu empresa", "Prom. rubro"],
        [wr_empresa, wr_rubro],
        color=[MC_BLUE, (0.78, 0.78, 0.78)],
        width=0.45, edgecolor='none'
    )
    for bar, val in zip(bars, [wr_empresa, wr_rubro]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                "{:.1f}%".format(val), ha='center', va='bottom',
                fontweight='bold', fontsize=12, color=MC_NAVY)

    ax.set_ylabel("Win Rate (%)", fontsize=9)
    ax.set_title("Tasa de Adjudicacion", fontweight='bold',
                 color=MC_NAVY, fontsize=12)
    ax.set_ylim(0, max(wr_empresa, wr_rubro, 5) * 1.35)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def gen_radar_chart(data, path):
    """Spider chart with client-facing percentiles vs market."""
    _apply_style()

    percentiles = data.get("client_percentiles", {})
    if not percentiles:
        # Fallback: empty chart
        fig, ax = plt.subplots(figsize=(3.4, 3.0))
        ax.text(0.5, 0.5, "Sin datos", ha='center', va='center')
        ax.axis('off')
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return

    # Order for visual balance
    order = [
        "Win Rate", "Volumen", "Adjudicaciones", "Monto",
        "Diversificacion", "Competidores\nenfrentados",
        "Resiliencia", "Actividad\nreciente",
    ]
    labels = [k for k in order if k in percentiles]
    values = [percentiles[k] for k in labels]

    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(3.4, 3.0), subplot_kw=dict(polar=True))
    ax.fill(angles_plot, values_plot, color=MC_BLUE, alpha=0.2)
    ax.plot(angles_plot, values_plot, color=MC_BLUE, linewidth=2)
    ax.scatter(angles, values, color=MC_BLUE, s=25, zorder=5)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=6, color='gray')
    ax.set_title("Tu Perfil vs. el Mercado", fontweight='bold',
                 color=MC_NAVY, fontsize=12, pad=15)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def gen_competitor_chart(data, path):
    """Horizontal bar chart of top rivals."""
    _apply_style()
    loss = data.get("loss", {})

    rivals = []
    for i in [1, 2]:
        name = loss.get("top_rival_{}_name".format(i))
        count = loss.get("top_rival_{}_count".format(i), 0)
        if pd.notna(name) and count and int(count) > 0:
            rivals.append((_name(name), int(count)))

    fig, ax = plt.subplots(figsize=(7.0, max(1.2, len(rivals) * 0.7 + 0.4)))

    if not rivals:
        ax.text(0.5, 0.5, "Sin datos de rivales recurrentes",
                ha='center', va='center', fontsize=12, color='gray',
                transform=ax.transAxes)
        ax.axis('off')
    else:
        names = [r[0][:35] for r in rivals]
        counts = [r[1] for r in rivals]
        colors = [MC_RED, MC_ORANGE][:len(rivals)]

        bars = ax.barh(names, counts, color=colors, height=0.4, edgecolor='none')
        for bar, val in zip(bars, counts):
            ax.text(bar.get_width() + 0.15,
                    bar.get_y() + bar.get_height() / 2,
                    "{} {}".format(val, "vez" if val == 1 else "veces"),
                    ha='left', va='center', fontweight='bold',
                    fontsize=11, color=MC_NAVY)

        ax.set_xlabel("Veces que te gano")
        ax.set_title("Rivales Principales", fontweight='bold',
                     color=MC_NAVY, fontsize=12)
        ax.set_xlim(0, max(counts) * 1.5)
        ax.invert_yaxis()

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def gen_ranking_chart(data, path):
    """Histogram showing win rate position among all companies."""
    _apply_style()
    wr_dist = data.get("wr_distribution", [])
    company_wr = float(data["company"].get("win_rate", 0))
    wr_rank = data.get("wr_rank", 0)
    total = data.get("total_active", len(wr_dist))

    fig, ax = plt.subplots(figsize=(7.0, 2.3))

    if wr_dist:
        # Convert to percentages for display
        wr_pct = [w * 100 for w in wr_dist]
        ax.hist(wr_pct, bins=40, color=(0.82, 0.82, 0.82),
                edgecolor='white', linewidth=0.5)
        ax.axvline(company_wr * 100, color=MC_BLUE, linewidth=2.5)

        yl = ax.get_ylim()
        ax.text(company_wr * 100 + 0.5, yl[1] * 0.8,
                "  Tu empresa\n  {:.1f}%".format(company_wr * 100),
                fontsize=10, fontweight='bold', color=MC_BLUE, va='top')

    ax.set_xlabel("Win Rate (%)")
    ax.set_ylabel("Empresas")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
    ax.set_title("Tu tasa de adjudicacion entre {:,} constructoras".format(total).replace(",", "."),
                 fontweight='bold', color=MC_NAVY, fontsize=12)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def gen_tipo_chart(data, path):
    """Stacked bar chart: bids by tender type (L1, LE, LP)."""
    _apply_style()
    company = data["company"]
    industry = data.get("industry", {})

    tipos = [
        ("L1 - Menor", "n_L1"),
        ("LE - Media", "n_LE"),
        ("LP - Mayor", "n_LP"),
    ]

    labels = [t[0] for t in tipos]
    values = [int(company.get(t[1], 0) or 0) for t in tipos]
    total = sum(values) or 1

    # Industry averages (percentage distribution)
    ind_dist = industry.get("tipo_distribution", {})

    fig, ax = plt.subplots(figsize=(7.0, 2.8))

    x = range(len(labels))
    bars = ax.bar(x, values, color=[MC_BLUE, MC_GREEN, MC_NAVY],
                  width=0.5, edgecolor='none')

    for bar, val in zip(bars, values):
        if val > 0:
            pct = val / total * 100
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    "{} ({:.0f}%)".format(val, pct),
                    ha='center', va='bottom', fontweight='bold',
                    fontsize=10, color=MC_NAVY)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Licitaciones")
    ax.set_title("Distribucion por Tipo de Licitacion", fontweight='bold',
                 color=MC_NAVY, fontsize=12)
    ax.set_ylim(0, max(values + [1]) * 1.35)

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def gen_opportunity_chart(data, path):
    """Visual: current revenue vs potential with +5% win rate."""
    _apply_style()
    company = data["company"]

    total_bids = int(company.get("total_bids", 0) or 0)
    total_wins = int(company.get("total_wins", 0) or 0)
    wr = float(company.get("win_rate", 0) or 0)
    monto_prom = float(company.get("monto_promedio", 0) or 0)

    # Current vs potential with +5% improvement
    current_revenue = total_wins * monto_prom
    improved_wr = min(wr + 0.05, 1.0)
    extra_wins = max(1, round(total_bids * 0.05))
    potential_wins = total_wins + extra_wins
    potential_revenue = potential_wins * monto_prom
    delta = potential_revenue - current_revenue

    fig, ax = plt.subplots(figsize=(7.0, 2.5))

    bars = ax.barh(
        ["Actual\n({})".format(_pct(wr)), "Con +5%\n({})".format(_pct(improved_wr))],
        [current_revenue, potential_revenue],
        color=[MC_BLUE, MC_GREEN],
        height=0.45, edgecolor='none'
    )

    for bar, val in zip(bars, [current_revenue, potential_revenue]):
        ax.text(bar.get_width() + max(current_revenue, potential_revenue) * 0.02,
                bar.get_y() + bar.get_height() / 2,
                _money(val),
                ha='left', va='center', fontweight='bold',
                fontsize=11, color=MC_NAVY)

    ax.set_xlabel("Monto Adjudicado Estimado (CLP)")
    ax.set_title("Costo de Oportunidad: +{} adjudicaciones = {}".format(
        potential_wins - total_wins, _money(delta)),
        fontweight='bold', color=MC_NAVY, fontsize=12)
    ax.set_xlim(0, max(current_revenue, potential_revenue) * 1.45)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, p: _money(x)))

    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)


# ═══════════════════════════════════════════════
# PDF BUILDER
# ═══════════════════════════════════════════════

class DiagnosticPDF(FPDF):
    """PDF con footer personalizado."""

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(*C_GRAY)
        self.cell(0, 10,
                  'Generado con IA | Sebastian Cortes - Inteligencia de Mercado | Pag. {}'.format(self.page_no()),
                  align='C')


def _mini_header(pdf, title):
    """Render mini header bar for inner pages."""
    pdf.set_fill_color(*C_NAVY)
    pdf.rect(0, 0, 210, 12, 'F')
    pdf.set_fill_color(*C_BLUE)
    pdf.rect(0, 12, 210, 1, 'F')
    pdf.set_xy(15, 2)
    pdf.set_text_color(*C_WHITE)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, _s(title))


def build_pdf(data, charts, output_path, notes=None):
    """Build the 6-page diagnostic PDF ('Examen Medico Corporativo')."""
    import re

    pdf = DiagnosticPDF()
    pdf.set_auto_page_break(auto=False)

    company = data["company"]
    loss = data.get("loss", {})
    industry = data.get("industry", {})

    empresa = _name(company.get("nombre", ""))
    rut = data["rut"]
    region = _s(company.get("region", ""))
    total_active = data.get("total_active", "N/A")

    wr = float(company.get("win_rate", 0))
    avg_wr = float(industry.get("avg_win_rate", 0.15))
    top10_wr = float(industry.get("top10_win_rate", 0.40))
    bids = int(company.get("total_bids", 0))
    wins = int(company.get("total_wins", 0))

    # Custom text
    texts = notes.get("texto_personalizado", {}) if notes else {}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE 1: PORTADA + RESUMEN EJECUTIVO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pdf.add_page()

    # ── Full-height header ──
    pdf.set_fill_color(*C_NAVY)
    pdf.rect(0, 0, 210, 55, 'F')
    pdf.set_fill_color(*C_BLUE)
    pdf.rect(0, 55, 210, 2, 'F')

    pdf.set_xy(15, 8)
    pdf.set_text_color(*C_WHITE)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 6, _s('ANALISIS ESTRATEGICO DE COMPETITIVIDAD'))

    pdf.set_xy(15, 17)
    pdf.set_font('Helvetica', 'B', 24)
    pdf.cell(0, 12, _s(empresa[:45]))

    pdf.set_xy(15, 33)
    pdf.set_font('Helvetica', '', 10)
    info = "RUT: {} | {} | {}".format(
        rut, region, datetime.now().strftime('%d/%m/%Y'))
    pdf.cell(0, 6, _s(info))

    # ── Ranking statement ──
    wr_rank = data.get("wr_rank", 0)
    if wr_rank and isinstance(total_active, int) and total_active > 0:
        pdf.set_xy(15, 43)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(140, 200, 255)
        pdf.cell(0, 8, _s("Empresa #{:,} de {:,} constructoras activas en Chile".format(
            wr_rank, total_active).replace(",", ".")))

    # ── Metric boxes ──
    metrics = [
        ("Licitaciones", str(bids)),
        ("Adjudicadas",  str(wins)),
        ("Win Rate",     _pct(wr)),
        ("Monto Total",  _money(company.get("monto_total", 0))),
        ("Competidores", str(int(company.get("n_distinct_rivals", 0)))),
    ]

    box_w = 34
    box_h = 22
    gap = 2
    start_x = 15
    start_y = 63

    for i, (label, value) in enumerate(metrics):
        x = start_x + i * (box_w + gap)
        pdf.set_fill_color(*C_LIGHT)
        pdf.rect(x, start_y, box_w, box_h, 'F')
        pdf.set_draw_color(*C_BLUE)
        pdf.set_line_width(0.8)
        pdf.line(x, start_y, x + box_w, start_y)

        pdf.set_xy(x, start_y + 3)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(box_w, 7, value, align='C')

        pdf.set_xy(x, start_y + 13)
        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(box_w, 5, label, align='C')

    # ── Resumen ejecutivo ──
    pdf.set_xy(15, start_y + box_h + 8)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, _s("Resumen Ejecutivo"), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    pdf.set_font('Helvetica', '', 9.5)
    pdf.set_text_color(*C_TEXT)

    if wr > avg_wr and avg_wr > 0:
        pct_diff = ((wr - avg_wr) / avg_wr) * 100
        comparison = "{:.0f}% superior al promedio del rubro ({})".format(pct_diff, _pct(avg_wr))
    elif avg_wr > 0:
        comparison = "por debajo del promedio del rubro ({})".format(_pct(avg_wr))
    else:
        comparison = ""

    narrative = texts.get("resumen_ejecutivo") or (
        "{empresa} ha participado en {bids} licitaciones de construccion "
        "entre 2022 y 2025, adjudicandose {wins} ({wr}){comp}. "
        "Se enfrentaron a {rivals} empresas distintas en procesos competitivos."
        "\n\n"
        "El Top 10% de constructoras del mercado tiene un Win Rate de {top10}. "
        "{posicion}".format(
            empresa=empresa, bids=bids, wins=wins, wr=_pct(wr),
            comp=(", " + comparison) if comparison else "",
            rivals=int(company.get("n_distinct_rivals", 0)),
            top10=_pct(top10_wr),
            posicion=(
                "Con tu tasa actual, estas en una posicion competitiva solida."
                if wr >= avg_wr else
                "Existe margen significativo de mejora para alcanzar ese nivel."
            ),
        )
    )
    pdf.multi_cell(180, 4.8, _s(narrative))

    # ── What this report contains ──
    pdf.ln(5)
    y = pdf.get_y()
    pdf.set_fill_color(*C_LIGHT)
    pdf.rect(15, y, 180, 42, 'F')
    pdf.set_draw_color(*C_BLUE)
    pdf.set_line_width(0.8)
    pdf.line(15, y, 15, y + 42)

    pdf.set_xy(20, y + 3)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 5, _s("En este informe encontraras:"))

    toc_items = [
        "Desempeno vs. el mercado (Win Rate, radar competitivo)",
        "Inteligencia de competidores (quienes te ganan y cuanto)",
        "Analisis por tipo de licitacion (donde rindes mejor)",
        "Costo de oportunidad (cuanto dejas en la mesa)",
    ]
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*C_TEXT)
    for j, item in enumerate(toc_items):
        pdf.set_xy(25, y + 11 + j * 7)
        pdf.cell(5, 5, _s(str(j + 1) + "."))
        pdf.cell(160, 5, _s(item))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE 2: DESEMPENO VS MERCADO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pdf.add_page()
    _mini_header(pdf, 'DESEMPENO VS. EL MERCADO')

    # Win Rate section
    pdf.set_y(18)
    pdf.set_text_color(*C_NAVY)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, _s('Tasa de Adjudicacion'), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*C_TEXT)

    wr_text = (
        "Tu Win Rate es de {wr}. El promedio del rubro es {avg} y "
        "el Top 10% del mercado alcanza {top10}. ".format(
            wr=_pct(wr), avg=_pct(avg_wr), top10=_pct(top10_wr)
        )
    )
    if wr >= top10_wr:
        wr_text += "Estas en el segmento de elite de constructoras."
    elif wr >= avg_wr:
        wr_text += "Estas sobre el promedio, pero hay espacio para llegar al Top 10%."
    else:
        wr_text += "Hay oportunidad significativa de mejora."
    pdf.multi_cell(180, 4.5, _s(wr_text))

    # Charts side by side
    chart_y = pdf.get_y() + 3
    if "win_rate" in charts:
        pdf.image(charts["win_rate"], x=15, y=chart_y, w=85)
    if "radar" in charts:
        pdf.image(charts["radar"], x=107, y=chart_y, w=85)

    # Ranking histogram below (radar chart ~80mm tall at w=85 with bbox_inches)
    pdf.set_y(chart_y + 85)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 10, _s('Tu Posicion en el Mercado'), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)

    if "ranking" in charts:
        pdf.image(charts["ranking"], x=15, y=pdf.get_y(), w=180)
        pdf.set_y(pdf.get_y() + 48)

    # Percentile box
    if wr_rank and isinstance(total_active, int) and total_active > 0:
        top_pct = (wr_rank / total_active) * 100
        y = pdf.get_y() + 2
        color = C_GREEN if top_pct <= 50 else C_ORANGE

        pdf.set_fill_color(*C_LIGHT)
        pdf.rect(15, y, 180, 14, 'F')
        pdf.set_draw_color(*color)
        pdf.set_line_width(1.2)
        pdf.line(15, y, 15, y + 14)

        pdf.set_xy(20, y + 2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*color)
        if top_pct < 1:
            pct_str = "Top {:.1f}%".format(top_pct)
        elif top_pct <= 50:
            pct_str = "Top {:.0f}%".format(top_pct)
        else:
            pct_str = "Percentil {:.0f}".format(100 - top_pct)
        pdf.cell(80, 5, _s("Win Rate: {} - {}".format(_pct(wr), pct_str)))

        pdf.set_xy(20, y + 8)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(160, 4, _s(
            "Entre {:,} constructoras activas (3+ licitaciones)".format(total_active).replace(",", ".")))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE 3: INTELIGENCIA COMPETITIVA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pdf.add_page()
    _mini_header(pdf, 'INTELIGENCIA COMPETITIVA')

    pdf.set_y(18)
    pdf.set_text_color(*C_NAVY)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, _s('Rivales Principales'), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    # Rival info boxes
    pdf.set_text_color(*C_TEXT)
    total_lost = int(loss.get("total_lost_loss", loss.get("total_lost", company.get("total_lost", 0))) or 0)
    has_rivals = False

    for i in [1, 2]:
        rival_name = loss.get("top_rival_{}_name".format(i))
        rival_count = loss.get("top_rival_{}_count".format(i), 0)

        if pd.isna(rival_name) or not rival_count or int(rival_count) == 0:
            continue
        has_rivals = True
        rival_count = int(rival_count)

        y = pdf.get_y()
        color = C_RED if i == 1 else C_ORANGE

        pdf.set_fill_color(*C_LIGHT)
        pdf.rect(15, y, 180, 16, 'F')
        pdf.set_draw_color(*color)
        pdf.set_line_width(1.2)
        pdf.line(15, y, 15, y + 16)

        pdf.set_xy(20, y + 2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*C_NAVY)
        rival_display = _name(rival_name)[:42]
        pdf.cell(120, 6, _s("Rival #{}: {}".format(i, rival_display)))

        pdf.set_xy(145, y + 2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*color)
        pdf.cell(45, 6, _s("Te gano {} {}".format(
            rival_count, "vez" if rival_count == 1 else "veces")), align='R')

        rival_rut = loss.get("top_rival_{}".format(i), "")
        if pd.notna(rival_rut):
            pdf.set_xy(20, y + 9)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(*C_GRAY)
            pdf.cell(120, 5, _s("RUT: {}".format(rival_rut)))

        pdf.set_y(y + 19)

    if not has_rivals:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(0, 8, _s("Sin rivales recurrentes identificados"), ln=True)

    pdf.set_text_color(*C_TEXT)
    pdf.ln(3)

    # Competitor chart
    if "competitors" in charts:
        chart_y2 = pdf.get_y()
        pdf.image(charts["competitors"], x=15, y=chart_y2, w=180)
        n_rivals = sum(1 for i in [1, 2]
                       if pd.notna(loss.get("top_rival_{}_name".format(i))))
        chart_h = max(30, n_rivals * 18 + 15)
        pdf.set_y(chart_y2 + chart_h)

    # Insight box
    pdf.ln(5)
    insight = loss.get("loss_insight", "")
    if pd.notna(insight) and insight:
        y = pdf.get_y()
        pdf.set_fill_color(255, 248, 225)
        pdf.rect(15, y, 180, 20, 'F')
        pdf.set_draw_color(255, 193, 7)
        pdf.set_line_width(0.4)
        pdf.rect(15, y, 180, 20, 'D')

        pdf.set_xy(20, y + 2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(133, 100, 4)
        pdf.cell(0, 5, _s("HALLAZGO CLAVE"))

        pdf.set_xy(20, y + 8)
        pdf.set_font('Helvetica', '', 9)
        insight_clean = _s(str(insight))
        insight_clean = re.sub(r'\([^)]*\|[^)]*\)', lambda m: '(' + _name(m.group(0)[1:-1]) + ')', insight_clean)
        if ' | ' in insight_clean:
            parts = insight_clean.split(' | ')
            insight_clean = parts[0]
        if insight_clean:
            insight_clean = insight_clean[0].upper() + insight_clean[1:]
        pdf.multi_cell(165, 4, insight_clean)
        pdf.set_y(y + 23)

    # AI custom insight
    comp_notes = texts.get("insight_competencia", "")
    if comp_notes:
        pdf.ln(3)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(*C_TEXT)
        pdf.multi_cell(180, 4.5, _s(comp_notes))

    # Summary stats
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*C_TEXT)

    loss_rate = loss.get("loss_rate", 0)
    n_rivals_total = loss.get("n_distinct_rivals_loss", company.get("n_distinct_rivals", 0))

    if total_lost > 0:
        bids_loss = int(loss.get("total_participated", company.get("total_bids", 0)))
        summary = (
            "En total, {} perdio {} de {} licitaciones contra "
            "{} rivales distintos (tasa de derrota: {}).".format(
                empresa[:30], total_lost, bids_loss,
                int(n_rivals_total) if pd.notna(n_rivals_total) else 0,
                _pct(loss_rate)
            )
        )
        pdf.multi_cell(180, 4.5, _s(summary))

    # Comparison table
    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 7, _s("Resumen Comparativo"), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    col_w = [75, 50, 50]
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(col_w[0], 7, _s("  Metrica"), fill=True)
    pdf.cell(col_w[1], 7, _s("Tu empresa"), fill=True, align='C')
    pdf.cell(col_w[2], 7, _s("Prom. rubro"), fill=True, align='C')
    pdf.ln()

    table_rows = [
        ("Win Rate", _pct(wr), _pct(industry.get("avg_win_rate", 0))),
        ("Licitaciones totales", str(bids),
         "{:.0f}".format(industry.get("avg_bids", 0))),
        ("Rivales enfrentados",
         str(int(n_rivals_total) if pd.notna(n_rivals_total) else 0), "-"),
    ]

    pdf.set_text_color(*C_TEXT)
    for idx, (label, val_emp, val_rub) in enumerate(table_rows):
        if idx % 2 == 0:
            pdf.set_fill_color(*C_LIGHT)
        else:
            pdf.set_fill_color(*C_WHITE)
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(col_w[0], 6, _s("  " + label), fill=True)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(col_w[1], 6, _s(val_emp), fill=True, align='C')
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(col_w[2], 6, _s(val_rub), fill=True, align='C')
        pdf.ln()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE 4: TENDENCIAS Y SECTORES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pdf.add_page()
    _mini_header(pdf, 'TENDENCIAS Y SECTORES')

    pdf.set_y(18)
    pdf.set_text_color(*C_NAVY)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, _s('Donde Compites'), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    # Tipo chart (figsize 7.0x2.8 → at w=180, h≈72 + labels ~8mm padding)
    if "tipos" in charts:
        pdf.image(charts["tipos"], x=15, y=pdf.get_y(), w=180)
        pdf.set_y(pdf.get_y() + 80)

    # Insight text about tipos
    n_l1 = int(company.get("n_L1", 0) or 0)
    n_le = int(company.get("n_LE", 0) or 0)
    n_lp = int(company.get("n_LP", 0) or 0)
    total_typed = n_l1 + n_le + n_lp

    if total_typed > 0:
        # Find dominant type
        tipo_map = {"L1 (Menor)": n_l1, "LE (Media)": n_le, "LP (Mayor)": n_lp}
        dominant = max(tipo_map, key=tipo_map.get)
        dominant_pct = tipo_map[dominant] / total_typed * 100

        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_text_color(*C_TEXT)

        tipo_text = texts.get("insight_sectores") or (
            "Tu actividad se concentra en licitaciones {dom} "
            "({pct:.0f}% de tus ofertas). ".format(dom=dominant, pct=dominant_pct)
        )

        if n_lp > 0 and n_lp / total_typed > 0.3:
            tipo_text += (
                "Tu participacion en licitaciones LP (mayores a 1000 UTM) "
                "indica capacidad para obras de envergadura."
            )
        elif n_lp == 0 or n_lp / total_typed < 0.1:
            tipo_text += (
                "Hay oportunidad de explorar licitaciones LP (>1000 UTM) "
                "donde los montos son significativamente mayores."
            )

        pdf.multi_cell(180, 4.8, _s(tipo_text))

    # Region info
    if region:
        pdf.ln(6)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(0, 7, _s("Presencia Regional"), ln=True)
        pdf.set_draw_color(*C_BLUE)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)

        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_text_color(*C_TEXT)
        pdf.multi_cell(180, 4.8, _s(
            "Region principal de operacion: {}. "
            "Tu perfil competitivo se compara contra todas las constructoras "
            "activas a nivel nacional.".format(region)
        ))

    # Monto promedio insight
    monto_prom = float(company.get("monto_promedio", 0) or 0)
    avg_monto = float(industry.get("avg_monto_promedio", 0) or 0)
    if monto_prom > 0:
        pdf.ln(6)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(0, 7, _s("Rango de Montos"), ln=True)
        pdf.set_draw_color(*C_BLUE)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)

        y = pdf.get_y()
        pdf.set_fill_color(*C_LIGHT)
        pdf.rect(15, y, 180, 18, 'F')
        pdf.set_draw_color(*C_BLUE)
        pdf.set_line_width(0.8)
        pdf.line(15, y, 15, y + 18)

        pdf.set_xy(20, y + 2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(80, 6, _s("Tu monto promedio: {}".format(_money(monto_prom))))

        pdf.set_xy(20, y + 10)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*C_GRAY)
        if avg_monto > 0:
            pdf.cell(160, 5, _s("Promedio del rubro: {}".format(_money(avg_monto))))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE 5: COSTO DE OPORTUNIDAD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pdf.add_page()
    _mini_header(pdf, 'COSTO DE OPORTUNIDAD')

    pdf.set_y(18)
    pdf.set_text_color(*C_NAVY)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, _s('Cuanto Dejas en la Mesa'), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    pdf.set_font('Helvetica', '', 9.5)
    pdf.set_text_color(*C_TEXT)

    improved_wr = min(wr + 0.05, 1.0)
    extra_wins = max(1, round(bids * 0.05))
    potential_wins = wins + extra_wins
    extra_revenue = extra_wins * monto_prom

    opp_text = (
        "Con {bids} licitaciones y un Win Rate de {wr}, te adjudicaste {wins}. "
        "Un aumento de solo 5 puntos porcentuales (a {new_wr}) habria significado "
        "{extra} adjudicacion{es} adicional{es2}, equivalente{es3} a aproximadamente "
        "{revenue} en ingresos.".format(
            bids=bids, wr=_pct(wr), wins=wins,
            new_wr=_pct(improved_wr), extra=extra_wins,
            es="es" if extra_wins > 1 else "",
            es2="es" if extra_wins > 1 else "",
            es3="s" if extra_wins > 1 else "",
            revenue=_money(extra_revenue)
        )
    )
    pdf.multi_cell(180, 4.8, _s(opp_text))

    # Opportunity chart
    pdf.ln(3)
    if "opportunity" in charts:
        pdf.image(charts["opportunity"], x=15, y=pdf.get_y(), w=180)
        pdf.set_y(pdf.get_y() + 58)

    # Key number box
    if extra_revenue > 0:
        y = pdf.get_y() + 3
        pdf.set_fill_color(232, 245, 233)
        pdf.rect(15, y, 180, 28, 'F')
        pdf.set_draw_color(*C_GREEN)
        pdf.set_line_width(1.2)
        pdf.line(15, y, 15, y + 28)

        pdf.set_xy(20, y + 3)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*C_GREEN)
        pdf.cell(0, 5, _s("OPORTUNIDAD ESTIMADA"))

        pdf.set_xy(20, y + 11)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(0, 8, _s("+{} = {} en ingresos potenciales".format(
            _money(extra_revenue), _pct(0.05) + " WR")))

        pdf.set_xy(20, y + 21)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(0, 5, _s("Basado en tu monto promedio de {} por adjudicacion".format(
            _money(monto_prom))))
        pdf.set_y(y + 32)

    # How to improve
    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, _s("Como mejorar tu Win Rate"), ln=True)
    pdf.set_draw_color(*C_BLUE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    tips = [
        ("Seleccionar mejor", "No ofertar a ciegas. Licitar donde tu perfil tiene ventaja."),
        ("Conocer rivales", "Saber contra quien compites permite ajustar la estrategia."),
        ("Monitorear temprano", "Las mejores oportunidades se preparan con anticipacion."),
        ("Analizar patrones", "Entender por que pierdes es tan valioso como ganar."),
    ]

    pdf.set_text_color(*C_TEXT)
    for j, (title, desc) in enumerate(tips):
        y = pdf.get_y()
        pdf.set_fill_color(*C_LIGHT)
        pdf.rect(15, y, 180, 11, 'F')
        pdf.set_draw_color(*C_BLUE)
        pdf.set_line_width(0.6)
        pdf.line(15, y, 15, y + 11)

        pdf.set_xy(20, y + 1)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(40, 5, _s(title))
        pdf.set_font('Helvetica', '', 8.5)
        pdf.cell(135, 5, _s(desc))
        pdf.set_y(y + 13)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE 6: SERVICIOS (CTA)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pdf.add_page()
    _mini_header(pdf, 'SIGUIENTE PASO')

    pdf.set_y(22)

    # Closing text
    closing = texts.get("cierre") or (
        "Este diagnostico fue generado analizando datos historicos de "
        "ChileCompra (2022-2025), procesando {:,} procesos de compra publica "
        "y {:,} constructoras activas.\n\n"
        "Este reporte analiza el pasado.\n"
        "Nuestro servicio monitorea el futuro.".format(
            industry.get("total_companies", 0),
            total_active if isinstance(total_active, int) else 0,
        ).replace(",", ".")
    )

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_TEXT)
    pdf.set_x(15)
    pdf.multi_cell(180, 6, _s(closing), align='C')

    # Service box
    pdf.ln(10)
    y_box = pdf.get_y()
    box_h = 100
    pdf.set_fill_color(*C_NAVY)
    pdf.rect(25, y_box, 160, box_h, 'F')
    pdf.set_fill_color(*C_BLUE)
    pdf.rect(25, y_box, 160, 2, 'F')

    pdf.set_text_color(*C_WHITE)

    pdf.set_xy(30, y_box + 8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(150, 8, _s("Inteligencia Competitiva B2B"), align='C')

    pdf.set_xy(30, y_box + 19)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(150, 5, _s("para Constructoras en Mercado Publico"), align='C')

    services = [
        ("Monitoreo de Oportunidades",
         "Filtro el 99% del ruido y te aviso cuando sale la licitacion ideal para tu perfil."),
        ("Inteligencia de Competidores",
         "Sabes contra quien vas a competir antes de ofertar."),
        ("Alertas Tempranas",
         "Las mejores licitaciones se preparan con tiempo, no el ultimo dia."),
    ]

    pdf.set_font('Helvetica', '', 9)
    for j, (svc_title, svc_desc) in enumerate(services):
        base_y = y_box + 32 + j * 16
        pdf.set_xy(40, base_y)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(130, 5, _s(svc_title))
        pdf.set_xy(40, base_y + 7)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(180, 200, 220)
        pdf.cell(130, 4, _s(svc_desc))
        pdf.set_text_color(*C_WHITE)

    # Contact
    pdf.set_xy(30, y_box + box_h - 18)
    pdf.set_draw_color(*C_BLUE)
    pdf.set_line_width(0.3)
    pdf.line(55, y_box + box_h - 20, 155, y_box + box_h - 20)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(150, 6, _s("Sebastian Cortes"), align='C')
    pdf.set_xy(30, y_box + box_h - 9)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(150, 5, _s("sebastian.cortes.ing@gmail.com"), align='C')

    # Bottom note
    pdf.set_y(y_box + box_h + 10)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(*C_GRAY)
    pdf.multi_cell(180, 4, _s(
        "Datos procesados con inteligencia artificial a partir de fuentes publicas "
        "(ChileCompra/Mercado Publico, 2022-2025). Este informe es de caracter informativo "
        "y no constituye asesoria legal ni financiera."
    ), align='C')

    # ── Save ──
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path


# ═══════════════════════════════════════════════
# AI NOTES (for personalization)
# ═══════════════════════════════════════════════

def generate_ai_notes(data, output_path):
    """Export JSON for AI review and personalization."""
    company = data["company"]
    loss = data.get("loss", {})
    industry = data.get("industry", {})

    notes = {
        "rut": data["rut"],
        "empresa": _name(company.get("nombre", "")),
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "instrucciones": (
            "Para personalizar el PDF: modifica los valores en "
            "'texto_personalizado' y re-ejecuta el script. "
            "Deja vacio '' para usar texto auto-generado."
        ),
        "datos_clave": {
            # Solo datos publicos derivados de ChileCompra
            "total_bids": int(company.get("total_bids", 0)),
            "total_wins": int(company.get("total_wins", 0)),
            "win_rate": round(float(company.get("win_rate", 0)), 4),
            "win_rate_rubro": round(float(industry.get("avg_win_rate", 0)), 4),
            "monto_total": float(company.get("monto_total", 0)),
            "region": _s(company.get("region", "")),
            "dias_desde_ultima": int(company.get("dias_desde_ultima", 0)),
            "total_lost": int(loss.get("total_lost_loss", loss.get("total_lost", 0)) or 0),
            "top_rival_1": _name(loss.get("top_rival_1_name", "")),
            "top_rival_1_count": int(loss.get("top_rival_1_count", 0)) if pd.notna(loss.get("top_rival_1_count")) else 0,
            "top_rival_2": _name(loss.get("top_rival_2_name", "")),
            "top_rival_2_count": int(loss.get("top_rival_2_count", 0)) if pd.notna(loss.get("top_rival_2_count")) else 0,
            "loss_insight": _s(loss.get("loss_insight", "")),
            # Contacto (uso interno del vendedor, NO incluir en PDF)
            "telefono": _s(company.get("telefono", "")),
            "email": _s(company.get("email", "")),
        },
        "texto_personalizado": {
            "resumen_ejecutivo": "",
            "insight_competencia": "",
            "insight_sectores": "",
            "cierre": "",
        },
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    assert_client_safe_json(notes, output_path.name)

    return notes


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

def main():
    print_header("11 -- Generador PDF Diagnostico")

    # ── List mode ──
    if "--list-top" in sys.argv:
        idx = sys.argv.index("--list-top")
        n = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 10

        enriched_path = FILTERED_DIR / "leads_enriched.parquet"
        if not enriched_path.exists():
            print("ERROR: No hay leads enriquecidos")
            sys.exit(1)

        enriched = pd.read_parquet(enriched_path)

        loss_path = OUTPUT_DIR / "loss_analysis.parquet"
        if loss_path.exists():
            loss = pd.read_parquet(loss_path)
            for col in ["top_rival_1_name", "top_rival_1_count", "loss_insight"]:
                if col in loss.columns and col not in enriched.columns:
                    enriched = enriched.merge(loss[["rut", col]], on="rut", how="left")

        print("\nTop {} leads para diagnostico:".format(n))
        print("{:>3} {:>10} {:>6} {:>6} {:>5} {:25} {:>15}".format(
            "#", "RUT", "Score", "WR", "Bids", "Rival", "Telefono"))
        print("-" * 80)

        for i, (_, row) in enumerate(enriched.head(n).iterrows()):
            rival = _name(row.get("top_rival_1_name", ""))[:24] if pd.notna(row.get("top_rival_1_name")) else "-"
            tel = str(row.get("telefono", ""))[:14] if pd.notna(row.get("telefono")) else "-"
            sc = float(row.get("score_combined", 0))
            wr_val = float(row.get("win_rate", 0)) * 100
            bd = int(row.get("total_bids", 0))
            print("{:>3} {:>10} {:>6.1f} {:>5.1f}% {:>5} {:25} {:>15}".format(
                i + 1, row["rut"], sc, wr_val, bd, rival, tel))

        return

    # ── Generate mode ──
    rut = None
    output_custom = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_custom = args[i + 1]
            i += 2
        elif not args[i].startswith("--"):
            rut = args[i]
            i += 1
        else:
            i += 1

    if not rut:
        print("Uso:")
        print("  python 11_generate_diagnostic_pdf.py <RUT>")
        print("  python 11_generate_diagnostic_pdf.py <RUT> --output nombre.pdf")
        print("  python 11_generate_diagnostic_pdf.py --list-top 10")
        sys.exit(1)

    print("Generando diagnostico para RUT: {}".format(rut))

    # Load
    data = load_data(rut)
    if not data["found"]:
        print("ERROR: RUT {} no encontrado en la base de datos".format(rut))
        sys.exit(1)

    empresa = _name(data["company"].get("nombre", ""))
    print("  Empresa: {}".format(empresa))
    print("  Win rate: {}".format(_pct(data["company"].get("win_rate", 0))))
    wr_rank = data.get("wr_rank", 0)
    total_act = data.get("total_active", 0)
    if wr_rank and total_act:
        print("  Win rate rank: #{} de {} (top {:.1f}%)".format(
            wr_rank, total_act, wr_rank / total_act * 100))

    if "loss" in data:
        r1 = _name(data["loss"].get("top_rival_1_name", ""))
        c1 = data["loss"].get("top_rival_1_count", 0)
        if r1:
            print("  Rival #1: {} ({} veces)".format(r1, int(c1) if pd.notna(c1) else 0))

    # Check for AI notes
    notes_path = DIAG_DIR / "diagnostico_{}_notas.json".format(rut)
    notes = None
    if notes_path.exists():
        with open(notes_path, encoding="utf-8") as f:
            notes = json.load(f)
        has_custom = any(v for v in notes.get("texto_personalizado", {}).values())
        if has_custom:
            print("  Usando texto personalizado de: {}".format(notes_path.name))
        else:
            notes = None

    # Generate charts
    tmp_dir = tempfile.mkdtemp(prefix="diag_")
    print("  Generando graficos...")
    charts = {}

    try:
        for name, func in [("win_rate", gen_win_rate_chart),
                           ("radar", gen_radar_chart),
                           ("competitors", gen_competitor_chart),
                           ("ranking", gen_ranking_chart),
                           ("tipos", gen_tipo_chart),
                           ("opportunity", gen_opportunity_chart)]:
            p = os.path.join(tmp_dir, name + ".png")
            func(data, p)
            charts[name] = p

        print("  {} graficos generados".format(len(charts)))

        # Build PDF
        if output_custom:
            pdf_path = Path(output_custom)
        else:
            pdf_path = DIAG_DIR / "diagnostico_{}.pdf".format(rut)

        build_pdf(data, charts, pdf_path, notes)
        assert_client_safe_binary(pdf_path)
        print("\n  PDF generado: {}".format(pdf_path))

        # AI notes
        ai_notes = generate_ai_notes(data, notes_path)
        print("  Notas IA: {}".format(notes_path))

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Summary
    print("\n" + "=" * 55)
    print("  DIAGNOSTICO GENERADO")
    print("=" * 55)
    print("  Empresa:  {}".format(empresa))
    print("  RUT:      {}".format(rut))
    print("  PDF:      {}".format(pdf_path))
    print("  Notas IA: {}".format(notes_path))
    write_run_manifest(
        DIAG_DIR / "diagnostico_{}_manifest.json".format(rut),
        command=f"python 11_generate_diagnostic_pdf.py {rut}",
        source=data.get("source", "unknown"),
        outputs=[str(pdf_path), str(notes_path)],
        details={"empresa": empresa},
    )
    print("\n  Para personalizar con IA:")
    print("    1. Abre {}".format(notes_path.name))
    print("    2. Modifica 'texto_personalizado'")
    print("    3. Re-ejecuta: python 11_generate_diagnostic_pdf.py {}".format(rut))


if __name__ == "__main__":
    main()
