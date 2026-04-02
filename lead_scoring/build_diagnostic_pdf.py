"""
build_diagnostic_pdf.py — Generador de PDF Diagnostico v4.

Usa el motor de layout matematico (pdf_engine.py), componentes puros
(pdf_components.py) y charts limpios (pdf_charts.py).

Cada pagina es una lista de (height_mm, render_fn).
El layout engine las posiciona. Si algo no cabe, se omite.
NUNCA se corta ni se solapa.

6 paginas:
  P1: Portada — header + metricas + resumen ejecutivo + indice
  P2: Desempeno vs Mercado — gauge + radar en columnas
  P3: Inteligencia Competitiva — rivales, tabla detalle, hallazgo
  P4: Analisis Temporal — donut + regional + escala
  P5: Costo de Oportunidad — waterfall + escenarios
  P6: Recomendaciones — plan accion + pricing + CTA

Uso:
    python build_diagnostic_pdf.py 132385-4
    python build_diagnostic_pdf.py 132385-4 --output mi_diagnostico.pdf
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from config import OUTPUT_DIR
from pdf_engine import (
    PageLayout,
    HEADER_H, METRIC_ROW_H, SECTION_HEADING_H,
    CHART_H, CALLOUT_H, FOOTER_H, PRICING_ROW_H, CTA_H,
    SPACER_SM, SPACER_MD, SPACER_LG,
    COLOR_NAVY, COLOR_GOLD, COLOR_GRAY,
)
from pdf_components import (
    render_header, render_metrics, render_section_heading,
    render_body, render_chart, render_table, render_callout,
    render_pricing_row, render_cta, render_footer,
)
from pdf_charts import (
    gauge_chart, radar_chart, competitor_chart,
    scatter_chart, donut_chart, waterfall_chart,
    _safe_float, _safe_int, _safe_str,
)
from generate_pdf_v2 import load_data

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
DIAG_DIR = OUTPUT_DIR / "diagnosticos_v3"
DIAG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Text helpers (latin-1 safe for fpdf2 built-in fonts)
# ---------------------------------------------------------------------------

def _s(text):
    """Sanitize text for latin-1 (fpdf2 built-in fonts)."""
    if text is None:
        return ""
    if isinstance(text, float) and math.isnan(text):
        return ""
    text = str(text)
    replacements = {
        "\u2013": "-", "\u2014": "-", "\u2018": "'",
        "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return text.encode("latin-1", errors="replace").decode("latin-1")


def _name(raw):
    """Clean company name for display."""
    name = _s(raw)
    if not name or name == "-":
        return "Empresa"
    if "|" in name:
        parts = [p.strip() for p in name.split("|")]
        non_upper = [p for p in parts if not p.isupper() and len(p) > 3]
        if non_upper:
            return non_upper[0]
        return min(parts, key=len)
    return name


def _money(amount):
    """Format CLP amount."""
    a = _safe_float(amount)
    if a == 0:
        return "$0"
    if a >= 1e9:
        return "${:,.1f}B".format(a / 1e9).replace(",", ".")
    if a >= 1e6:
        return "${:,.0f}MM".format(a / 1e6).replace(",", ".")
    return "${:,.0f}".format(a).replace(",", ".")


def _pct(value):
    """Format as percentage (0-1 -> X.X%)."""
    v = _safe_float(value)
    return "{:.1f}%".format(v * 100)


def _fecha_es():
    """Current date in Spanish."""
    now = datetime.now()
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }
    return "{} de {} de {}".format(now.day, meses[now.month], now.year)


# ---------------------------------------------------------------------------
# Executive summary generator
# ---------------------------------------------------------------------------

def _generate_summary(data):
    """Generate personalized executive summary from real data."""
    company = data.get("company", {})
    loss = data.get("loss", {})
    industry = data.get("industry", {})

    nombre = _name(company.get("nombre", "la empresa"))
    wr = _safe_float(company.get("win_rate"))
    total_bids = _safe_int(company.get("total_bids"))
    total_wins = _safe_int(company.get("total_wins"))
    avg_wr = _safe_float(industry.get("avg_win_rate", 0.22))
    monto_prom = _safe_float(company.get("monto_promedio"))
    dias = _safe_int(company.get("dias_desde_ultima"))
    rival_name = _name(loss.get("top_rival_1_name", ""))
    rival_count = _safe_int(loss.get("top_rival_1_count"))
    loss_rate = _safe_float(loss.get("loss_rate"))
    total_lost = _safe_int(loss.get("total_lost"))

    lines = []

    # Line 1: market positioning
    if wr > avg_wr:
        diff_pp = (wr - avg_wr) * 100
        lines.append(
            "{} opera con una tasa de adjudicacion de {:.1f}%, "
            "superior al promedio del rubro ({:.1f}%) por {:.1f} puntos. "
            "Esto la posiciona en un segmento competitivo favorable.".format(
                nombre, wr * 100, avg_wr * 100, diff_pp
            )
        )
    elif wr > 0:
        diff_pp = (avg_wr - wr) * 100
        lines.append(
            "{} presenta una tasa de adjudicacion de {:.1f}%, "
            "{:.1f} puntos por debajo del promedio del rubro ({:.1f}%). "
            "Esto representa una oportunidad concreta de mejora.".format(
                nombre, wr * 100, diff_pp, avg_wr * 100
            )
        )
    else:
        lines.append(
            "{} ha participado en {} licitaciones registradas.".format(
                nombre, total_bids
            )
        )

    # Line 2: main finding
    if rival_count >= 3:
        lines.append(
            "El hallazgo mas relevante: {} ha ganado {} de las licitaciones "
            "no adjudicadas a {}, configurando un patron de competencia "
            "directa que merece atencion estrategica.".format(
                rival_name, rival_count, nombre
            )
        )
    elif dias > 365:
        lines.append(
            "Se detecta un periodo de inactividad de {} dias desde "
            "la ultima participacion, lo cual puede implicar perdida "
            "de posicionamiento frente a competidores activos.".format(dias)
        )
    elif loss_rate > 0.5 and total_lost >= 5:
        lines.append(
            "Con una tasa de no adjudicacion del {:.0f}% sobre {} "
            "licitaciones, existe un patron sistematico que puede "
            "revertirse con ajustes en la estrategia de postulacion.".format(
                loss_rate * 100, total_lost
            )
        )
    elif rival_count >= 1:
        lines.append(
            "Se identifico a {} como el competidor mas frecuente, "
            "habiendo ganado {} licitacion(es) en competencia directa.".format(
                rival_name, rival_count
            )
        )

    # Line 3: scale
    if monto_prom > 0:
        lines.append(
            "La empresa opera con un monto promedio por licitacion de {}, "
            "habiendo participado en {} procesos con {} adjudicaciones.".format(
                _money(monto_prom), total_bids, total_wins
            )
        )

    lines.append(
        "Este informe detalla su posicion competitiva, identifica "
        "los rivales clave y cuantifica la oportunidad de ingresos "
        "adicionales con mejoras especificas."
    )

    return " ".join(lines)


# ---------------------------------------------------------------------------
# Recommendations generator
# ---------------------------------------------------------------------------

def _generate_recommendations(data):
    """Generate actionable recommendations based on data patterns."""
    company = data.get("company", {})
    loss = data.get("loss", {})
    industry = data.get("industry", {})

    wr = _safe_float(company.get("win_rate"))
    avg_wr = _safe_float(industry.get("avg_win_rate", 0.22))
    total_bids = _safe_int(company.get("total_bids"))
    dias = _safe_int(company.get("dias_desde_ultima"))
    rival_name = _name(loss.get("top_rival_1_name", ""))
    rival_count = _safe_int(loss.get("top_rival_1_count"))
    n_lp = _safe_int(company.get("n_LP"))
    n_le = _safe_int(company.get("n_LE"))

    recs = []

    # WR-based recommendations
    if wr < avg_wr and wr > 0:
        gap = (avg_wr - wr) * 100
        recs.append(
            "1. CERRAR BRECHA DE WIN RATE: Su tasa actual ({:.1f}%) esta {:.0f} puntos "
            "bajo el promedio. Enfocarse en licitaciones donde tiene ventaja competitiva "
            "demostrada puede cerrar esta brecha en 6-12 meses.".format(wr * 100, gap)
        )
    elif wr >= avg_wr:
        recs.append(
            "1. PROTEGER VENTAJA: Su win rate ({:.1f}%) supera al mercado ({:.1f}%). "
            "Mantenga la disciplina en seleccion de licitaciones y monitoree "
            "movimientos de rivales para proteger esta posicion.".format(
                wr * 100, avg_wr * 100
            )
        )

    # Rival-based recommendations
    if rival_count >= 3:
        recs.append(
            "2. ESTRATEGIA ANTI-RIVAL: {} le ha ganado {} licitaciones. "
            "Analizar sus patrones de oferta (montos, tiempos, tipos) puede "
            "revelar vulnerabilidades explotables.".format(rival_name, rival_count)
        )
    elif rival_count >= 1:
        recs.append(
            "2. VIGILANCIA COMPETITIVA: {} es su rival mas frecuente. "
            "Monitorear sus movimientos permite anticipar y preparar "
            "mejores propuestas.".format(rival_name)
        )
    else:
        recs.append(
            "2. MAPEO COMPETITIVO: Sin un rival dominante identificado, "
            "el mercado esta fragmentado. Esto es una oportunidad para "
            "posicionarse como lider en su segmento."
        )

    # Activity-based
    if dias > 365:
        recs.append(
            "3. REACTIVACION URGENTE: {} dias sin postular significa perdida "
            "de visibilidad ante compradores. Retomar actividad con 2-3 "
            "licitaciones de bajo riesgo para reconstruir presencia.".format(dias)
        )
    elif n_lp > 0 and n_le > n_lp * 2:
        recs.append(
            "3. MIGRAR A LP: El {:.0f}% de sus postulaciones son LE. "
            "Las LP tienen mejor margen y menos competencia relativa. "
            "Gradualmente aumentar participacion en LP.".format(
                n_le / max(total_bids, 1) * 100
            )
        )
    else:
        recs.append(
            "3. DIVERSIFICACION: Evaluar expansion a nuevas regiones o "
            "tipos de licitacion para reducir concentracion de riesgo."
        )

    # Always add monitoring
    recs.append(
        "4. MONITOREO CONTINUO: Implementar alertas semanales de nuevas "
        "licitaciones en su rubro y region permite no perder oportunidades "
        "por falta de informacion oportuna."
    )

    return "\n\n".join(recs)


# ---------------------------------------------------------------------------
# Opportunity scenarios
# ---------------------------------------------------------------------------

def _calc_scenarios(data):
    """Calculate waterfall scenarios for opportunity cost page."""
    company = data.get("company", {})
    industry = data.get("industry", {})

    wr = _safe_float(company.get("win_rate"))
    total_bids = _safe_int(company.get("total_bids"))
    monto_prom = _safe_float(company.get("monto_promedio"))
    avg_wr = _safe_float(industry.get("avg_win_rate", 0.22))
    top10_wr = _safe_float(industry.get("top10_win_rate", 0.40))
    wins_actual = _safe_int(company.get("total_wins"))

    ingreso_actual = wins_actual * monto_prom

    wr_plus5 = wr + 0.05
    wins_plus5 = total_bids * wr_plus5
    extra_plus5 = max(0, (wins_plus5 - wins_actual)) * monto_prom

    wins_avg = total_bids * avg_wr
    extra_avg = max(0, (wins_avg - wins_actual) * monto_prom - extra_plus5)

    wins_top = total_bids * top10_wr
    extra_top = max(0, (wins_top - wins_actual) * monto_prom - extra_plus5 - max(0, extra_avg))

    potencial = ingreso_actual + extra_plus5 + max(0, extra_avg) + max(0, extra_top)

    waterfall = [
        ("Actual", 0, ingreso_actual),
        ("+5pp WR", ingreso_actual, extra_plus5),
        ("Prom. rubro", ingreso_actual + extra_plus5, max(0, extra_avg)),
        ("Top 10%", ingreso_actual + extra_plus5 + max(0, extra_avg), max(0, extra_top)),
        ("Potencial", 0, potencial),
    ]

    table_rows = [
        ["Actual", _pct(wr), str(wins_actual), _money(ingreso_actual)],
        ["+5pp", _pct(wr_plus5), str(int(wins_plus5)), _money(ingreso_actual + extra_plus5)],
        ["Prom. rubro", _pct(avg_wr), str(int(wins_avg)), _money(ingreso_actual + extra_plus5 + max(0, extra_avg))],
        ["Top 10%", _pct(top10_wr), str(int(wins_top)), _money(potencial)],
    ]

    return waterfall, table_rows, potencial, ingreso_actual


# ---------------------------------------------------------------------------
# PAGE BUILDERS
# ---------------------------------------------------------------------------

def _build_page_1(layout, data, tmp_dir):
    """P1: Portada — header + metrics + resumen + indice."""
    # Heights: 40 + 12 + 30 + 10 + 35 + 8 + 40 = 175mm (of 247 avail)
    company = data.get("company", {})
    loss = data.get("loss", {})
    industry = data.get("industry", {})

    nombre = _name(company.get("nombre", "Empresa"))
    rut = _safe_str(data.get("rut", ""))
    region = _s(str(company.get("region", "")) or "")
    fecha = _fecha_es()

    total_bids = _safe_int(company.get("total_bids"))
    total_wins = _safe_int(company.get("total_wins"))
    wr = _safe_float(company.get("win_rate"))
    monto_prom = _safe_float(company.get("monto_promedio"))
    n_rivals = _safe_int(company.get("n_distinct_rivals"))
    if n_rivals == 0:
        n_rivals = _safe_int(loss.get("n_distinct_rivals"))

    layout.new_page()

    # Header (40mm)
    layout.add_element(
        HEADER_H,
        lambda pdf, x, y, w, h: render_header(
            pdf, x, y, w, h,
            empresa=nombre, rut=rut, region=region, fecha=fecha,
        ),
        label="header",
    )

    layout.add_spacer(SPACER_LG)  # 12mm

    # Metrics row (30mm)
    avg_wr = _safe_float(industry.get("avg_win_rate", 0.22))
    wr_sub = "Sobre prom." if wr >= avg_wr else "Bajo prom."
    metrics_data = [
        (str(total_bids), "Licitaciones"),
        (str(total_wins), "Adjudicadas"),
        (_pct(wr), "Win Rate"),
        (_money(monto_prom), "Monto Prom."),
        (str(n_rivals), "Rivales"),
    ]

    layout.add_element(
        METRIC_ROW_H,
        lambda pdf, x, y, w, h, _m=metrics_data: render_metrics(
            pdf, x, y, w, h, metrics=_m,
        ),
        label="metrics",
    )

    layout.add_spacer(10)  # 10mm

    # Executive summary body (35mm)
    summary = _generate_summary(data)
    layout.add_element(
        35,
        lambda pdf, x, y, w, h, _t=summary: render_body(
            pdf, x, y, w, h, text=_t, font_size=9,
        ),
        label="body_resumen",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Table of contents (40mm)
    toc_rows = [
        ["1", "Desempeno vs Mercado", "Win rate, radar de capacidades, posicion"],
        ["2", "Inteligencia Competitiva", "Rivales directos, patrones, detalle"],
        ["3", "Analisis Temporal", "Composicion, presencia regional"],
        ["4", "Costo de Oportunidad", "Escenarios financieros, potencial"],
        ["5", "Recomendaciones", "Plan de accion y siguiente paso"],
    ]
    layout.add_element(
        40,
        lambda pdf, x, y, w, h, _r=toc_rows: render_table(
            pdf, x, y, w, h,
            headers=["#", "Seccion", "Contenido"],
            rows=_r,
            col_widths=[0.06, 0.30, 0.64],
            bold_col=1,
        ),
        label="table_contenido",
    )


def _build_page_2(layout, data, tmp_dir):
    """P2: Desempeno vs Mercado — gauge + radar in columns."""
    # Heights: 15 + 8 + 65 + 10 + 70 + 8 = 176mm (of 247 avail)
    company = data.get("company", {})
    industry = data.get("industry", {})
    percentiles = data.get("client_percentiles", {})

    wr = _safe_float(company.get("win_rate"))
    avg_wr = _safe_float(industry.get("avg_win_rate", 0.22))
    total_bids = _safe_int(company.get("total_bids"))
    total_wins = _safe_int(company.get("total_wins"))
    top10_wr = _safe_float(industry.get("top10_win_rate", 0.40))
    wr_rank = data.get("wr_rank", 0)
    total_active = data.get("total_active", 0)

    layout.new_page()

    # Section heading (15mm)
    layout.add_element(
        SECTION_HEADING_H,
        lambda pdf, x, y, w, h: render_section_heading(
            pdf, x, y, w, h,
            num=1, title="Desempeno vs Mercado",
            subtitle="Analisis comparativo de su posicion competitiva",
        ),
        label="section_desempeno",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Gauge column (60%) + text column (40%), height=65mm
    gauge_path = os.path.join(tmp_dir, "gauge.png")
    gauge_w_mm = layout.content_width * 0.60 - 3  # minus half gap
    gauge_h_mm = 65 - 8  # minus caption space
    gauge_chart(
        wr=wr, avg_wr=avg_wr, path=gauge_path,
        figsize=(gauge_w_mm / 25.4, gauge_h_mm / 25.4),
    )

    # Text for gauge column
    if wr >= avg_wr:
        gauge_text = (
            "Su tasa de adjudicacion ({:.1f}%) supera al promedio "
            "del rubro ({:.1f}%).".format(wr * 100, avg_wr * 100)
        )
        if wr_rank > 0 and total_active > 0:
            gauge_text += " Posicion #{} de {} empresas activas.".format(
                wr_rank, total_active
            )
        if wr < top10_wr:
            gap = (top10_wr - wr) * 100
            gauge_text += (
                " Para alcanzar el top 10% ({:.1f}%), necesita cerrar "
                "una brecha de {:.0f} puntos.".format(top10_wr * 100, gap)
            )
    else:
        gap = (avg_wr - wr) * 100
        gauge_text = (
            "Su win rate ({:.1f}%) esta {:.0f} puntos por debajo "
            "del promedio del rubro ({:.1f}%). Esto representa una "
            "oportunidad concreta de mejora que se cuantifica en la "
            "seccion de Costo de Oportunidad.".format(
                wr * 100, gap, avg_wr * 100
            )
        )

    def _render_gauge_col(pdf, x, y, w, h, _p=gauge_path):
        render_chart(pdf, x, y, w, h, img_path=_p,
                     caption="Tasa de adjudicacion vs promedio del sector")

    def _render_gauge_text(pdf, x, y, w, h, _t=gauge_text):
        render_body(pdf, x, y, w, h, text=_t, font_size=9)

    layout.add_columns(
        [
            (0.60, _render_gauge_col, 65),
            (0.40, _render_gauge_text, 65),
        ],
        label="columns_gauge",
    )

    layout.add_spacer(10)  # 10mm

    # Radar column (55%) + text column (45%), height=70mm
    radar_path = os.path.join(tmp_dir, "radar.png")
    radar_w_mm = layout.content_width * 0.55 - 3
    radar_h_mm = 70 - 8
    radar_data = percentiles if percentiles else {
        "Win Rate": 50, "Volumen": 50, "Monto": 50,
        "Adjudicaciones": 50, "Diversificacion": 50,
    }
    radar_chart(
        data_dict=radar_data, path=radar_path,
        figsize=(radar_w_mm / 25.4, radar_h_mm / 25.4),
    )

    # Text for radar: identify strengths and weaknesses
    sorted_dims = sorted(radar_data.items(), key=lambda x: x[1], reverse=True)
    strengths = [d for d, v in sorted_dims if v >= 60][:2]
    weaknesses = [d for d, v in sorted_dims if v < 40][:2]

    radar_text_parts = []
    if strengths:
        s_names = " y ".join(s.replace("\n", " ") for s in strengths)
        radar_text_parts.append("Fortalezas: {} (percentil alto).".format(s_names))
    if weaknesses:
        w_names = " y ".join(w.replace("\n", " ") for w in weaknesses)
        radar_text_parts.append("Areas de mejora: {}.".format(w_names))
    if not radar_text_parts:
        radar_text_parts.append("Perfil equilibrado sin debilidades criticas.")

    radar_text_parts.append(
        "El radar muestra su posicion relativa al mercado en 8 "
        "dimensiones clave. Percentil 50 = promedio del sector."
    )
    radar_text = " ".join(radar_text_parts)

    def _render_radar_col(pdf, x, y, w, h, _p=radar_path):
        render_chart(pdf, x, y, w, h, img_path=_p,
                     caption="Perfil competitivo (8 dimensiones)")

    def _render_radar_text(pdf, x, y, w, h, _t=radar_text):
        render_body(pdf, x, y, w, h, text=_t, font_size=9)

    layout.add_columns(
        [
            (0.55, _render_radar_col, 70),
            (0.45, _render_radar_text, 70),
        ],
        label="columns_radar",
    )

    layout.add_spacer(SPACER_MD)  # 8mm


def _build_page_3(layout, data, tmp_dir):
    """P3: Inteligencia Competitiva — rivals chart, detail, tables, callout."""
    # Heights: 15+8+45+6+20+6+50+6+18+6+40 = 220mm (of 247 avail)
    # If too tight, table_licitaciones (50) is omitted
    company = data.get("company", {})
    loss = data.get("loss", {})
    lost_details = data.get("lost_tender_details", [])

    layout.new_page()

    # Section heading (15mm)
    layout.add_element(
        SECTION_HEADING_H,
        lambda pdf, x, y, w, h: render_section_heading(
            pdf, x, y, w, h,
            num=2, title="Inteligencia Competitiva",
            subtitle="Rivales directos y patrones de competencia",
        ),
        label="section_competitiva",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Competitor chart (45mm)
    rivals_list = []
    for i in range(1, 6):
        rname = loss.get("top_rival_{}_name".format(i))
        rcount = loss.get("top_rival_{}_count".format(i), 0)
        if rname and not (isinstance(rname, float) and math.isnan(rname)):
            c = _safe_int(rcount)
            if c > 0:
                rivals_list.append((_name(rname), c))

    rival_chart_path = os.path.join(tmp_dir, "competitors.png")
    chart_h = 45
    chart_w_mm = layout.content_width
    chart_h_img = chart_h - 8  # caption space
    competitor_chart(
        rivals=rivals_list, path=rival_chart_path,
        figsize=(chart_w_mm / 25.4, chart_h_img / 25.4),
    )

    layout.add_element(
        chart_h,
        lambda pdf, x, y, w, h, _p=rival_chart_path: render_chart(
            pdf, x, y, w, h, img_path=_p,
            caption="Rivales directos: frecuencia de competencia",
        ),
        label="chart_rivales",
    )

    layout.add_spacer(6)  # 6mm

    # Rival detail body (20mm)
    rival_1_name = _name(loss.get("top_rival_1_name", ""))
    rival_1_count = _safe_int(loss.get("top_rival_1_count"))
    n_distinct = _safe_int(loss.get("n_distinct_rivals",
                                     company.get("n_distinct_rivals", 0)))

    if rival_1_count > 0:
        rival_body = (
            "Rival principal: {} ({} licitaciones en competencia directa). "
            "En total se identificaron {} rivales distintos en el periodo analizado.".format(
                rival_1_name, rival_1_count, n_distinct
            )
        )
    else:
        rival_body = (
            "Se identificaron {} competidores distintos en el periodo. "
            "No se detecto un rival dominante, lo que sugiere un "
            "mercado fragmentado.".format(n_distinct)
        )

    layout.add_element(
        20,
        lambda pdf, x, y, w, h, _t=rival_body: render_body(
            pdf, x, y, w, h, text=_t, font_size=9,
        ),
        label="body_rival_detail",
    )

    layout.add_spacer(6)  # 6mm

    # Lost tender detail table (50mm) — OPTIONAL (omit if no data or no space)
    if lost_details:
        tender_rows = []
        for d in lost_details[:6]:
            tender_rows.append([
                _s(str(d.get("fecha", ""))[:10]),
                _s(str(d.get("titulo", ""))[:45]),
                _money(d.get("monto", 0)),
            ])

        layout.add_element(
            50,
            lambda pdf, x, y, w, h, _r=tender_rows: render_table(
                pdf, x, y, w, h,
                headers=["Fecha", "Licitacion", "Monto"],
                rows=_r,
                col_widths=[0.15, 0.60, 0.25],
                bold_col=-1,
            ),
            label="table_licitaciones",
            allow_page_break=False,
        )

        layout.add_spacer(6)

    # Callout (18mm)
    if rival_1_count >= 3:
        callout_text = (
            "Hallazgo clave: {} ha ganado {} licitaciones donde usted "
            "participo. Existe un patron identificable en sus ofertas que "
            "puede analizarse para mejorar su posicion competitiva.".format(
                rival_1_name, rival_1_count
            )
        )
    elif n_distinct > 0:
        callout_text = (
            "Con {} rivales identificados en el periodo, el mercado "
            "presenta una competencia moderada. Monitorear los movimientos "
            "de los principales actores es clave.".format(n_distinct)
        )
    else:
        callout_text = (
            "No se identificaron rivales directos recurrentes. "
            "Esto puede indicar participacion en mercados de bajo "
            "volumen o alta fragmentacion competitiva."
        )

    layout.add_element(
        18,
        lambda pdf, x, y, w, h, _t=callout_text: render_callout(
            pdf, x, y, w, h, text=_t, color=COLOR_GOLD,
        ),
        label="callout_rival",
        allow_page_break=False,
    )

    layout.add_spacer(6)

    # Comparative table — top 5 rivals summary (40mm)
    if rivals_list:
        comp_rows = []
        for rname, rcount in rivals_list[:5]:
            comp_rows.append([
                _s(rname)[:30],
                str(rcount),
                "Alto" if rcount >= 5 else ("Medio" if rcount >= 3 else "Bajo"),
            ])

        layout.add_element(
            40,
            lambda pdf, x, y, w, h, _r=comp_rows: render_table(
                pdf, x, y, w, h,
                headers=["Rival", "Encuentros", "Nivel Amenaza"],
                rows=_r,
                col_widths=[0.50, 0.25, 0.25],
                bold_col=0,
            ),
            label="table_comparativa",
            allow_page_break=False,
        )


def _build_page_4(layout, data, tmp_dir):
    """P4: Analisis Temporal — donut + regional + scale."""
    # Heights: 15+8+65+10+20+6+15 = 139mm (of 247 avail)
    company = data.get("company", {})

    n_lp = _safe_int(company.get("n_LP"))
    n_le = _safe_int(company.get("n_LE"))
    n_l1 = _safe_int(company.get("n_L1"))
    total_bids = _safe_int(company.get("total_bids"))
    region = _s(str(company.get("region", "")) or "")
    monto_prom = _safe_float(company.get("monto_promedio"))
    dias = _safe_int(company.get("dias_desde_ultima"))

    layout.new_page()

    # Section heading (15mm)
    layout.add_element(
        SECTION_HEADING_H,
        lambda pdf, x, y, w, h: render_section_heading(
            pdf, x, y, w, h,
            num=3, title="Analisis Temporal y Sectorial",
            subtitle="Composicion de licitaciones y presencia regional",
        ),
        label="section_temporal",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Donut column (45%) + text column (55%), height=65mm
    donut_path = os.path.join(tmp_dir, "donut.png")
    donut_w_mm = layout.content_width * 0.45 - 3
    donut_h_mm = 65 - 8

    tipos = {}
    if n_lp > 0:
        tipos["LP"] = n_lp
    if n_le > 0:
        tipos["LE"] = n_le
    if n_l1 > 0:
        tipos["L1"] = n_l1

    donut_chart(
        data=tipos if tipos else {"Sin datos": 1},
        path=donut_path,
        figsize=(donut_w_mm / 25.4, donut_h_mm / 25.4),
    )

    # Text for donut
    donut_text_parts = ["Composicion por tipo de licitacion:"]
    if n_lp > 0:
        donut_text_parts.append(
            "- LP (>1000 UTM): {} ({:.0f}%)".format(
                n_lp, n_lp / max(total_bids, 1) * 100
            )
        )
    if n_le > 0:
        donut_text_parts.append(
            "- LE (100-1000 UTM): {} ({:.0f}%)".format(
                n_le, n_le / max(total_bids, 1) * 100
            )
        )
    if n_l1 > 0:
        donut_text_parts.append(
            "- L1 (<100 UTM): {} ({:.0f}%)".format(
                n_l1, n_l1 / max(total_bids, 1) * 100
            )
        )
    donut_text = "\n".join(donut_text_parts)

    def _render_donut_col(pdf, x, y, w, h, _p=donut_path):
        render_chart(pdf, x, y, w, h, img_path=_p,
                     caption="Distribucion por tipo de licitacion")

    def _render_donut_text(pdf, x, y, w, h, _t=donut_text):
        render_body(pdf, x, y, w, h, text=_t, font_size=9)

    layout.add_columns(
        [
            (0.45, _render_donut_col, 65),
            (0.55, _render_donut_text, 65),
        ],
        label="columns_donut",
    )

    layout.add_spacer(10)  # 10mm

    # Regional presence body (20mm)
    region_text = "Presencia regional: "
    if region:
        region_text += "operacion principal en {}. ".format(region)
    else:
        region_text += "sin region principal identificada. "

    region_text += (
        "Con un monto promedio de {}, la empresa se posiciona en el "
        "segmento de licitaciones de {} escala.".format(
            _money(monto_prom),
            "gran" if monto_prom > 500e6 else (
                "mediana" if monto_prom > 100e6 else "menor"
            ),
        )
    )

    layout.add_element(
        20,
        lambda pdf, x, y, w, h, _t=region_text: render_body(
            pdf, x, y, w, h, text=_t, font_size=9,
        ),
        label="body_regional",
    )

    layout.add_spacer(6)  # 6mm

    # Activity/scale body (15mm)
    if dias > 0:
        if dias > 365:
            scale_text = (
                "Ultima actividad detectada hace {} dias. "
                "Un periodo prolongado sin postulaciones puede afectar "
                "el posicionamiento ante compradores publicos.".format(dias)
            )
        else:
            scale_text = (
                "Actividad reciente: ultima postulacion hace {} dias. "
                "Nivel de actividad {}.".format(
                    dias,
                    "alto" if dias < 90 else ("moderado" if dias < 180 else "bajo"),
                )
            )
    else:
        scale_text = "Sin informacion de actividad reciente disponible."

    layout.add_element(
        15,
        lambda pdf, x, y, w, h, _t=scale_text: render_body(
            pdf, x, y, w, h, text=_t, font_size=9,
        ),
        label="body_escala",
        allow_page_break=False,
    )


def _build_page_5(layout, data, tmp_dir):
    """P5: Costo de Oportunidad — waterfall + scenarios table + callout."""
    # Heights: 15+8+70+8+35+8+18 = 162mm (of 247 avail)
    company = data.get("company", {})
    industry = data.get("industry", {})

    waterfall_data, table_rows, potencial, ingreso_actual = _calc_scenarios(data)

    layout.new_page()

    # Section heading (15mm)
    layout.add_element(
        SECTION_HEADING_H,
        lambda pdf, x, y, w, h: render_section_heading(
            pdf, x, y, w, h,
            num=4, title="Costo de Oportunidad",
            subtitle="Cuantificacion del potencial de mejora",
        ),
        label="section_oportunidad",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Waterfall chart (70mm)
    waterfall_path = os.path.join(tmp_dir, "waterfall.png")
    wf_w_mm = layout.content_width
    wf_h_mm = 70 - 8
    waterfall_chart(
        scenarios=waterfall_data, path=waterfall_path,
        figsize=(wf_w_mm / 25.4, wf_h_mm / 25.4),
    )

    layout.add_element(
        70,
        lambda pdf, x, y, w, h, _p=waterfall_path: render_chart(
            pdf, x, y, w, h, img_path=_p,
            caption="Escenarios de ingreso segun mejora en win rate",
        ),
        label="chart_waterfall",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Scenarios table (35mm)
    layout.add_element(
        35,
        lambda pdf, x, y, w, h, _r=table_rows: render_table(
            pdf, x, y, w, h,
            headers=["Escenario", "Win Rate", "Adjudic.", "Ingreso Acum."],
            rows=_r,
            col_widths=[0.25, 0.20, 0.20, 0.35],
            bold_col=0,
        ),
        label="table_escenarios",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Cost callout (18mm)
    delta = potencial - ingreso_actual
    if delta > 0:
        cost_text = (
            "Costo de oportunidad estimado: {}. "
            "Esta es la diferencia entre su ingreso actual ({}) "
            "y el potencial al alcanzar el top 10% del mercado.".format(
                _money(delta), _money(ingreso_actual),
            )
        )
    else:
        cost_text = (
            "Su nivel de ingreso actual ({}) refleja un desempeno "
            "solido. El foco debe estar en mantener y proteger "
            "esta posicion competitiva.".format(_money(ingreso_actual))
        )

    layout.add_element(
        18,
        lambda pdf, x, y, w, h, _t=cost_text: render_callout(
            pdf, x, y, w, h, text=_t, color=COLOR_NAVY,
        ),
        label="callout_costo",
    )


def _build_page_6(layout, data, tmp_dir):
    """P6: Recomendaciones — body + pricing + CTA + disclaimer."""
    # Heights: 15+8+80+10+55+8+35+4+10 = 225mm (of 247 avail)
    company = data.get("company", {})

    layout.new_page()

    # Section heading (15mm)
    layout.add_element(
        SECTION_HEADING_H,
        lambda pdf, x, y, w, h: render_section_heading(
            pdf, x, y, w, h,
            num=5, title="Recomendaciones",
            subtitle="Plan de accion basado en los hallazgos del diagnostico",
        ),
        label="section_recs",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # Recommendations body (80mm)
    recs_text = _generate_recommendations(data)
    layout.add_element(
        80,
        lambda pdf, x, y, w, h, _t=recs_text: render_body(
            pdf, x, y, w, h, text=_t, font_size=9,
        ),
        label="body_recs",
    )

    layout.add_spacer(10)  # 10mm

    # Pricing row (55mm)
    tiers = [
        {
            "title": "Monitoreo",
            "price": "$89.000/mes",
            "bullets": [
                "Alertas semanales",
                "1 region",
                "Dashboard basico",
            ],
        },
        {
            "title": "Profesional",
            "price": "$179.000/mes",
            "bullets": [
                "Diagnostico trimestral",
                "Alertas diarias",
                "3 regiones",
                "Soporte prioritario",
            ],
            "highlight": True,
        },
        {
            "title": "Enterprise",
            "price": "Consultar",
            "bullets": [
                "Todo incluido",
                "Cobertura nacional",
                "Consultor dedicado",
                "API de datos",
            ],
        },
    ]

    layout.add_element(
        PRICING_ROW_H,
        lambda pdf, x, y, w, h, _t=tiers: render_pricing_row(
            pdf, x, y, w, h, tiers=_t,
        ),
        label="pricing_row",
    )

    layout.add_spacer(SPACER_MD)  # 8mm

    # CTA (35mm)
    nombre = _name(company.get("nombre", ""))
    layout.add_element(
        CTA_H,
        lambda pdf, x, y, w, h: render_cta(
            pdf, x, y, w, h,
            text="Listo para mejorar sus resultados?",
            contact="Sebastian Cortes - scortes@ingenia.cl - +56 9 7625 7585",
        ),
        label="cta",
    )

    layout.add_spacer(SPACER_SM)  # 4mm

    # Disclaimer (10mm)
    disclaimer = (
        "Este diagnostico fue generado con datos de Mercado Publico (OCDS). "
        "Los datos reflejan el periodo 2022-2025. Documento confidencial."
    )
    layout.add_element(
        10,
        lambda pdf, x, y, w, h, _t=disclaimer: render_body(
            pdf, x, y, w, h, text=_t, font_size=7,
        ),
        label="body_disclaimer",
        allow_page_break=False,
    )


# ---------------------------------------------------------------------------
# MAIN BUILDER
# ---------------------------------------------------------------------------

def build_diagnostic(data, output_path=None):
    """Build the full 6-page diagnostic PDF.

    Args:
        data: Dict from load_data(rut).
        output_path: Optional output path. Default: diagnosticos_v3/<rut>.pdf.

    Returns:
        Path to generated PDF.
    """
    rut = data.get("rut", "unknown")
    if output_path is None:
        output_path = str(DIAG_DIR / "diagnostico_{}.pdf".format(rut.replace("-", "")))

    if not data.get("found"):
        print("ERROR: RUT {} no encontrado en los parquets.".format(rut))
        return None

    layout = PageLayout()

    # Page counter for footer
    _page_counter = [0]

    def _footer(pdf, x, y, w, h):
        _page_counter[0] += 1
        render_footer(pdf, x, y, w, h,
                      page_num=_page_counter[0], total_pages=6)

    layout.set_footer(_footer, FOOTER_H)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Build all 6 pages
        _build_page_1(layout, data, tmp_dir)
        print("  P1 Portada: {:.0f}mm used".format(layout.page_height_used()))

        _build_page_2(layout, data, tmp_dir)
        print("  P2 Desempeno: {:.0f}mm used".format(layout.page_height_used()))

        _build_page_3(layout, data, tmp_dir)
        print("  P3 Competitiva: {:.0f}mm used".format(layout.page_height_used()))

        _build_page_4(layout, data, tmp_dir)
        print("  P4 Temporal: {:.0f}mm used".format(layout.page_height_used()))

        _build_page_5(layout, data, tmp_dir)
        print("  P5 Oportunidad: {:.0f}mm used".format(layout.page_height_used()))

        _build_page_6(layout, data, tmp_dir)
        print("  P6 Recomendaciones: {:.0f}mm used".format(layout.page_height_used()))

        layout.save(output_path)

    file_size = os.path.getsize(output_path)
    print("PDF generado: {} ({:,} bytes, {} paginas)".format(
        output_path, file_size, layout.page_count,
    ))

    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python build_diagnostic_pdf.py <RUT> [--output path]")
        print("Ejemplo: python build_diagnostic_pdf.py 132385-4")
        sys.exit(1)

    rut = sys.argv[1]
    output = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    print("Cargando datos para RUT: {}...".format(rut))
    data = load_data(rut)

    if not data.get("found"):
        print("ERROR: RUT {} no encontrado.".format(rut))
        sys.exit(1)

    print("Datos cargados desde: {}".format(data.get("source", "?")))
    result = build_diagnostic(data, output)

    if result:
        print("\nDiagnostico v4 generado exitosamente: {}".format(result))
    else:
        print("\nError generando diagnostico.")
        sys.exit(1)
