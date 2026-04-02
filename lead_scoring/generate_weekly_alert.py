"""
Generador de Alerta Semanal Premium -- IngenIA Licitaciones.

Genera alertas semanales para clientes del servicio mensual ($490K/mes).
Cada semana el cliente recibe:
  - PDF premium (2 paginas) con oportunidades, rivales, recomendaciones
  - Resumen WhatsApp texto plano (max 10 lineas)

Reutiliza logica de 09_tender_matcher.py (RSS/API) y pdf_design.py (diseno).

Uso:
    python generate_weekly_alert.py <RUT> [--days 7] [--output PATH]

    from generate_weekly_alert import *
"""
from __future__ import annotations

import sys
import tempfile
import warnings
from datetime import datetime, timedelta
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

from config import FILTERED_DIR, OUTPUT_DIR, MERCADO_PUBLICO_TICKET
from pdf_design import (
    PremiumPDF, COLORS, LAYOUT, _s, _name, _money, _pct,
)
from pipeline_core import load_best_leads_dataframe

warnings.filterwarnings("ignore", category=DeprecationWarning)

ALERT_DIR = OUTPUT_DIR / "alertas_semanales"
ALERT_DIR.mkdir(parents=True, exist_ok=True)

INDUSTRY_WR_MEDIAN = 0.22


# ===================================================================
# DATA LOADING
# ===================================================================

def load_client_profile(rut):
    """
    Carga perfil del cliente desde parquets del pipeline.
    Retorna dict con company data, loss analysis (rivales), industry stats.
    """
    profile = {"rut": rut, "found": False}

    # Buscar en datasets de leads (prioridad: enriched > ml > ranked > company_db)
    for parquet in [
        "leads_enriched.parquet",
        "leads_ml_ranked.parquet",
        "leads_ranked.parquet",
        "company_database.parquet",
    ]:
        path = FILTERED_DIR / parquet
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        match = df[df["rut"] == rut]
        if len(match) > 0:
            profile["company"] = match.iloc[0].to_dict()
            profile["found"] = True
            profile["source"] = parquet
            break

    if not profile["found"]:
        return profile

    company = profile["company"]

    # Loss analysis (rivales)
    loss_path = OUTPUT_DIR / "loss_analysis.parquet"
    if loss_path.exists():
        loss_df = pd.read_parquet(loss_path)
        loss_match = loss_df[loss_df["rut"] == rut]
        if len(loss_match) > 0:
            profile["loss"] = loss_match.iloc[0].to_dict()

    # Extraer perfil de filtrado
    profile["filter"] = {
        "region": str(company.get("region", "")),
        "monto_min": float(company.get("monto_promedio", 0)) * 0.3,
        "monto_max": float(company.get("monto_promedio", 0)) * 5.0,
        "tipos": _get_preferred_types(company),
    }

    # Rivales conocidos
    rivals = []
    loss = profile.get("loss", {})
    for i in range(1, 4):
        rival = loss.get(f"top_rival_{i}")
        if rival and pd.notna(rival):
            wins = loss.get(f"top_rival_{i}_wins", 0)
            rivals.append({"nombre": str(rival), "wins": int(wins) if pd.notna(wins) else 0})
    profile["rivals"] = rivals

    return profile


def _get_preferred_types(company):
    """Determina tipos de licitacion preferidos del cliente."""
    types = []
    n_lp = company.get("n_LP", 0)
    n_le = company.get("n_LE", 0)
    n_l1 = company.get("n_L1", 0)
    if pd.notna(n_lp) and n_lp > 0:
        types.append("LP")
    if pd.notna(n_le) and n_le > 0:
        types.append("LE")
    if pd.notna(n_l1) and n_l1 > 0:
        types.append("L1")
    return types if types else ["LP", "LE", "L1"]


# ===================================================================
# TENDER FETCHING (reutiliza 09_tender_matcher.py)
# ===================================================================

def fetch_recent_tenders(days=7):
    """
    Obtiene licitaciones de construccion recientes via RSS + API.
    Reutiliza get_rss_tenders() y get_api_tenders() de 09_tender_matcher.py.
    """
    matcher = import_module("09_tender_matcher")

    tenders = matcher.get_rss_tenders()

    api_tenders = matcher.get_api_tenders(days=days)
    seen = {t["codigo"] for t in tenders if t.get("codigo")}
    for t in api_tenders:
        if t.get("codigo") and t["codigo"] not in seen:
            tenders.append(t)
            seen.add(t["codigo"])

    return tenders


def _extract_tender_amount(tender):
    """Extrae monto estimado de la descripcion si esta disponible."""
    desc = str(tender.get("descripcion", ""))
    nombre = str(tender.get("nombre", ""))
    text = desc + " " + nombre

    import re
    # Buscar patrones de monto en CLP
    patterns = [
        r"\$\s*([\d.,]+)\s*(?:millones|MM)",
        r"([\d.,]+)\s*(?:millones|MM)\s*(?:de\s+)?(?:pesos)?",
        r"presupuesto[:\s]*([\d.,]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(".", "").replace(",", "."))
                if val < 100_000:
                    val *= 1_000_000
                return val
            except ValueError:
                continue
    return 0


def _extract_tender_type(tender):
    """Extrae tipo de licitacion del codigo."""
    codigo = str(tender.get("codigo", "")).upper()
    for tipo in ["LP", "LE", "LR", "L1", "LQ"]:
        if f"-{tipo}" in codigo:
            return tipo
    return "Otro"


# ===================================================================
# FILTERING & MATCHING
# ===================================================================

def filter_tenders_for_client(tenders, profile):
    """
    Filtra licitaciones segun perfil del cliente.
    Criterios: region, tipo, monto.
    Retorna lista de dicts con match_score y match_reasons.
    """
    client_filter = profile.get("filter", {})
    client_region = client_filter.get("region", "").lower()
    client_types = client_filter.get("tipos", [])
    monto_min = client_filter.get("monto_min", 0)
    monto_max = client_filter.get("monto_max", float("inf"))

    opportunities = []

    for tender in tenders:
        score = 0
        reasons = []

        # Region match
        tender_region = str(tender.get("region", "")).lower()
        if client_region and tender_region:
            if client_region in tender_region or tender_region in client_region:
                score += 30
                reasons.append("misma region")

        # Tipo match
        tipo = _extract_tender_type(tender)
        if tipo in client_types:
            score += 20
            reasons.append(f"tipo {tipo}")

        # Monto match
        monto = _extract_tender_amount(tender)
        if monto > 0:
            if monto_min <= monto <= monto_max:
                score += 25
                reasons.append("rango de monto")
            elif monto > monto_max * 0.5:
                score += 10
                reasons.append("monto cercano")

        # Keyword relevance (construccion ya filtrada por tender_matcher)
        score += 10
        reasons.append("construccion")

        # Minimo 20 puntos para incluir
        if score >= 20:
            opportunities.append({
                "codigo": tender.get("codigo", ""),
                "nombre": str(tender.get("nombre", ""))[:80],
                "descripcion": str(tender.get("descripcion", ""))[:150],
                "cierre": tender.get("cierre", ""),
                "organismo": tender.get("organismo", ""),
                "region": tender.get("region", ""),
                "tipo": tipo,
                "monto_estimado": monto,
                "match_score": score,
                "match_reasons": " | ".join(reasons),
            })

    # Ordenar por score desc, tomar top 5
    opportunities.sort(key=lambda x: x["match_score"], reverse=True)
    return opportunities[:5]


def check_rival_activity(tenders, profile):
    """
    Verifica si rivales conocidos participaron/ganaron en licitaciones recientes.
    Usa OCDS API via 09_tender_matcher.py.
    """
    rivals = profile.get("rivals", [])
    if not rivals:
        return []

    rival_ruts = {r["rut"]: r for r in rivals if r.get("rut")}
    rival_names = {r["nombre"].lower(): r for r in rivals}
    rival_moves = []

    matcher = import_module("09_tender_matcher")

    # Revisar primeras 10 licitaciones (limitar llamadas API)
    for tender in tenders[:10]:
        codigo = tender.get("codigo", "")
        if not codigo:
            continue

        participants = matcher.get_tender_participants_ocds(codigo)
        if not participants:
            continue

        # Comparar con rivales conocidos (por RUT primero, nombre como fallback)
        for rut_participant in participants:
            matched_rival = rival_ruts.get(str(rut_participant))
            if not matched_rival:
                # Fallback: match por nombre parcial
                for rival in rivals:
                    rival_name = rival["nombre"]
                    if (rival_name.lower() in str(rut_participant).lower() or
                            str(rut_participant) in rival_name):
                        matched_rival = rival
                        break
            if matched_rival:
                    rival_moves.append({
                        "rival": matched_rival["nombre"],
                        "rival_wins_historicas": matched_rival.get("wins", 0),
                        "tender_codigo": codigo,
                        "tender_nombre": str(tender.get("nombre", ""))[:70],
                        "tipo": "participando",
                    })

    return rival_moves


# ===================================================================
# RECOMMENDATIONS
# ===================================================================

def generate_recommendations(opportunities, rival_moves, profile):
    """
    Genera recomendaciones especificas basadas en oportunidades y rivales.
    Retorna lista de dicts con titulo + detalle.
    """
    company = profile.get("company", {})
    win_rate = float(company.get("win_rate", 0))
    recs = []

    # Recomendacion por oportunidades de alta afinidad
    high_match = [o for o in opportunities if o["match_score"] >= 40]
    if high_match:
        top = high_match[0]
        recs.append({
            "titulo": "Oportunidad prioritaria",
            "detalle": (
                f"La licitacion {top['codigo']} tiene alta afinidad con su perfil "
                f"({top['match_reasons']}). Recomendamos evaluar participacion."
            ),
        })

    # Recomendacion por movimiento de rivales
    if rival_moves:
        rival = rival_moves[0]
        recs.append({
            "titulo": "Alerta de rival",
            "detalle": (
                f"{rival['rival']} esta participando en {rival['tender_codigo']}. "
                f"Historicamente le ha ganado {rival['rival_wins_historicas']} veces. "
                f"Considere participar para disputar ese espacio."
            ),
        })

    # Recomendacion por win rate
    if win_rate < INDUSTRY_WR_MEDIAN:
        gap_pp = (INDUSTRY_WR_MEDIAN - win_rate) * 100
        recs.append({
            "titulo": "Estrategia de selectividad",
            "detalle": (
                f"Su tasa de adjudicacion esta {gap_pp:.0f} puntos bajo el promedio del rubro. "
                f"Recomendamos priorizar las {len(high_match)} oportunidades de mayor afinidad "
                f"en vez de postular a todas."
            ),
        })
    elif win_rate >= INDUSTRY_WR_MEDIAN and opportunities:
        recs.append({
            "titulo": "Mantener momentum",
            "detalle": (
                f"Su tasa de adjudicacion esta sobre el promedio del rubro ({_pct(INDUSTRY_WR_MEDIAN)}). "
                f"Aprovechar esta semana para ampliar volumen con las "
                f"{len(opportunities)} oportunidades identificadas."
            ),
        })

    # Recomendacion general si no hay suficientes
    if len(recs) < 2:
        recs.append({
            "titulo": "Monitoreo continuo",
            "detalle": (
                "Mantener seguimiento semanal de oportunidades en su region y "
                "segmento. Las licitaciones de mayor monto suelen publicarse "
                "a inicio y mitad de mes."
            ),
        })

    return recs[:3]


# ===================================================================
# PDF GENERATION
# ===================================================================

def generate_weekly_pdf(profile, opportunities, rival_moves, recommendations,
                        output_path=None, week_label=None):
    """
    Genera PDF de alerta semanal premium (2 paginas).
    Usa PremiumPDF de pdf_design.py para coherencia con diagnostico.
    """
    company = profile.get("company", {})
    nombre = _name(company.get("nombre", profile["rut"]))
    rut = profile["rut"]
    today = datetime.now()
    if not week_label:
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_label = f"Semana {week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"

    if not output_path:
        date_str = today.strftime("%Y%m%d")
        safe_name = _s(nombre).replace(" ", "_")[:30]
        output_path = ALERT_DIR / f"alerta_{safe_name}_{date_str}.pdf"

    pdf = PremiumPDF()
    pdf.set_context(company_name=nombre, report_title="Alerta Semanal")

    # ─── PAGINA 1: Header + Oportunidades + Rivales ───
    pdf.add_page()
    pdf.header_bar(
        f"Alerta Semanal — {nombre}",
        f"RUT: {rut} | {week_label}",
        today.strftime("%d/%m/%Y"),
    )

    # Metricas resumen rapidas (3 cards)
    y_cards = pdf.get_y() + 2
    card_w = 56
    card_gap = 6
    x = LAYOUT["margin_left"]

    n_opp = len(opportunities)
    n_rivals = len(rival_moves)
    n_recs = len(recommendations)

    pdf.metric_card(x, y_cards, str(n_opp), "Oportunidades", "esta semana", accent="green" if n_opp > 0 else "navy")
    pdf.metric_card(x + card_w + card_gap, y_cards, str(n_rivals), "Mov. Rivales",
                    "detectados" if n_rivals > 0 else "sin actividad",
                    accent="red" if n_rivals > 0 else "navy")
    pdf.metric_card(x + 2 * (card_w + card_gap), y_cards, str(n_recs), "Recomendaciones", "accionables", accent="gold")

    pdf.set_y(y_cards + LAYOUT["card_h"] + LAYOUT["sp_lg"])

    # SECCION 1: Oportunidades Esta Semana
    pdf.section_title(1, "Oportunidades Esta Semana",
                      f"{n_opp} licitaciones filtradas para su perfil")

    if opportunities:
        headers = ["Codigo", "Licitacion", "Tipo", "Cierre", "Afinidad"]
        rows = []
        for opp in opportunities:
            cierre = str(opp.get("cierre", ""))
            if len(cierre) > 10:
                cierre = cierre[:10]
            afinidad = "Alta" if opp["match_score"] >= 40 else "Media"
            rows.append([
                str(opp["codigo"])[:18],
                str(opp["nombre"])[:35],
                opp["tipo"],
                cierre if cierre else "—",
                afinidad,
            ])

        col_widths = [35, 65, 15, 25, 20]

        # Verificar espacio
        if pdf.get_y() + 8 + len(rows) * 7 > 260:
            pdf.add_page()
            pdf.set_y(LAYOUT["margin_top"] + 5)

        pdf.simple_table(headers, rows, col_widths=col_widths)
        pdf.spacer("sm")

        # Detalle de top oportunidad
        top = opportunities[0]
        desc = str(top.get("descripcion", ""))
        if desc and desc != "nan":
            pdf.insight_callout(
                f"Oportunidad destacada: {top['codigo']} — {desc}",
                style="success",
                icon_text="+",
            )
    else:
        pdf.text_block(
            "No se identificaron licitaciones de construccion con alta afinidad "
            "para su perfil esta semana. Continuaremos monitoreando.",
            style="body", color="text_secondary",
        )
        pdf.spacer("md")

    # SECCION 2: Movimiento de Rivales
    if pdf.get_y() > 220:
        pdf.add_page()
        pdf.set_y(LAYOUT["margin_top"] + 5)

    pdf.section_title(2, "Movimiento de Rivales",
                      "Actividad reciente de competidores conocidos")

    if rival_moves:
        for move in rival_moves[:3]:
            pdf.insight_callout(
                f"{_s(move['rival'])} esta {move['tipo']} en la licitacion "
                f"{move['tender_codigo']} ({_s(move['tender_nombre'])}). "
                f"Historial: le ha ganado {move['rival_wins_historicas']} veces.",
                style="danger",
                icon_text="!",
            )
    else:
        rivals_list = profile.get("rivals", [])
        if rivals_list:
            nombres = ", ".join(r["nombre"] for r in rivals_list[:3])
            pdf.text_block(
                f"Sus rivales principales ({_s(nombres)}) no registran "
                f"actividad publica en licitaciones esta semana.",
                style="body", color="text_secondary",
            )
        else:
            pdf.text_block(
                "Sin rivales identificados en su historial. "
                "El diagnostico competitivo completo identifica sus principales rivales.",
                style="body", color="text_secondary",
            )

    pdf.spacer("md")

    # SECCION 3: Recomendaciones
    if pdf.get_y() > 230:
        pdf.add_page()
        pdf.set_y(LAYOUT["margin_top"] + 5)

    pdf.section_title(3, "Recomendacion de la Semana",
                      "Acciones sugeridas basadas en su perfil")

    for rec in recommendations:
        pdf.spacer("xs")
        pdf._set_font("body_b")
        pdf._set_color("navy", "text")
        pdf.set_x(LAYOUT["margin_left"])
        pdf.cell(LAYOUT["content_w"], 5, _s(f">> {rec['titulo']}"), align="L")
        pdf.ln(6)
        pdf.text_block(rec["detalle"], style="body", color="text_primary")
        pdf.spacer("xs")

    # Footer con proxima entrega
    pdf.spacer("lg")
    pdf.divider("gold")
    next_week = today + timedelta(days=7)
    pdf.text_block(
        f"Proxima alerta: {next_week.strftime('%d/%m/%Y')} | "
        f"IngenIA Licitaciones — Servicio Mensual Premium",
        style="caption", color="text_muted",
    )

    # Footer profesional en todas las paginas
    for i in range(1, pdf.pages_count + 1):
        pdf.page = i
        pdf.professional_footer(page_num=i, total_pages=pdf.pages_count)

    pdf.output(str(output_path))
    return output_path


# ===================================================================
# WHATSAPP TEXT
# ===================================================================

def generate_whatsapp_text(profile, opportunities, rival_moves, recommendations):
    """
    Genera resumen texto plano para WhatsApp (max 10 lineas).
    Listo para copiar-pegar.
    """
    company = profile.get("company", {})
    nombre = _name(company.get("nombre", profile["rut"]))
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    lines = []
    lines.append(f"Alerta Semanal — {_s(nombre)}")
    lines.append(f"Semana {week_start.strftime('%d/%m')} al {week_end.strftime('%d/%m')}")
    lines.append("")

    if opportunities:
        lines.append(f"Oportunidades: {len(opportunities)} licitaciones para su perfil")
        for opp in opportunities[:3]:
            monto_str = _money(opp["monto_estimado"]) if opp["monto_estimado"] > 0 else ""
            cierre = str(opp.get("cierre", ""))[:10]
            line = f"- {opp['codigo']} | {opp['tipo']}"
            if monto_str:
                line += f" | {monto_str}"
            if cierre and cierre != "nan":
                line += f" | Cierre: {cierre}"
            lines.append(line)
    else:
        lines.append("Sin oportunidades de alta afinidad esta semana.")

    if rival_moves:
        lines.append("")
        move = rival_moves[0]
        lines.append(f"Rival: {_s(move['rival'])} participando en {move['tender_codigo']}")

    if recommendations:
        lines.append("")
        lines.append(f"Recomendacion: {_s(recommendations[0]['detalle'][:120])}")

    # Asegurar max 10 lineas
    lines = lines[:10]
    return "\n".join(lines)


# ===================================================================
# ORCHESTRATOR
# ===================================================================

def generate_weekly_alert(rut, days=7, output_dir=None):
    """
    Funcion principal: genera alerta semanal completa (PDF + WhatsApp).
    Retorna dict con paths y stats.
    """
    print(f"  Generando alerta semanal para {rut}...")

    # 1. Cargar perfil del cliente
    profile = load_client_profile(rut)
    if not profile["found"]:
        print(f"  ERROR: RUT {rut} no encontrado en los datasets")
        return {"error": f"RUT {rut} no encontrado"}

    company = profile["company"]
    nombre = _name(company.get("nombre", rut))
    print(f"  Cliente: {nombre}")

    # 2. Obtener licitaciones recientes
    print(f"  Consultando licitaciones (ultimos {days} dias)...")
    tenders = fetch_recent_tenders(days=days)
    print(f"  Licitaciones de construccion: {len(tenders)}")

    # 3. Filtrar para el cliente
    opportunities = filter_tenders_for_client(tenders, profile)
    print(f"  Oportunidades filtradas: {len(opportunities)}")

    # 4. Verificar actividad de rivales
    rival_moves = check_rival_activity(tenders, profile)
    print(f"  Movimientos de rivales: {len(rival_moves)}")

    # 5. Generar recomendaciones
    recommendations = generate_recommendations(opportunities, rival_moves, profile)

    # 6. Generar PDF
    out_dir = Path(output_dir) if output_dir else ALERT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = _s(nombre).replace(" ", "_")[:30]
    pdf_path = out_dir / f"alerta_{safe_name}_{date_str}.pdf"

    pdf_path = generate_weekly_pdf(
        profile, opportunities, rival_moves, recommendations,
        output_path=pdf_path,
    )
    print(f"  PDF generado: {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")

    # 7. Generar texto WhatsApp
    wsp_text = generate_whatsapp_text(profile, opportunities, rival_moves, recommendations)
    wsp_path = out_dir / f"alerta_wsp_{safe_name}_{date_str}.txt"
    wsp_path.write_text(wsp_text, encoding="utf-8")
    print(f"  WhatsApp: {wsp_path}")

    return {
        "rut": rut,
        "nombre": nombre,
        "pdf_path": str(pdf_path),
        "wsp_path": str(wsp_path),
        "opportunities": len(opportunities),
        "rival_moves": len(rival_moves),
        "recommendations": len(recommendations),
        "tenders_analyzed": len(tenders),
    }


# ===================================================================
# OFFLINE / DEMO MODE (sin acceso API)
# ===================================================================

def generate_weekly_alert_offline(rut, output_dir=None):
    """
    Genera alerta semanal usando datos historicos de los parquets.
    Para demos o cuando no hay acceso a RSS/API.
    Usa licitaciones recientes de tenders_construction.parquet en vez de API live.
    """
    print(f"  Generando alerta semanal (modo offline) para {rut}...")

    # 1. Cargar perfil del cliente
    profile = load_client_profile(rut)
    if not profile["found"]:
        print(f"  ERROR: RUT {rut} no encontrado")
        return {"error": f"RUT {rut} no encontrado"}

    company = profile["company"]
    nombre = _name(company.get("nombre", rut))
    print(f"  Cliente: {nombre}")

    # 2. Cargar licitaciones recientes de parquets
    tenders_path = FILTERED_DIR / "tenders_construction.parquet"
    if not tenders_path.exists():
        print("  AVISO: tenders_construction.parquet no encontrado")
        tenders_list = []
    else:
        tdf = pd.read_parquet(tenders_path)
        # Tomar las mas recientes
        if "date" in tdf.columns:
            tdf = tdf.sort_values("date", ascending=False)
        tenders_list = []
        for _, row in tdf.head(50).iterrows():
            tenders_list.append({
                "codigo": str(row.get("tender_id", row.get("id", ""))),
                "nombre": str(row.get("title", row.get("nombre", "")))[:80],
                "descripcion": str(row.get("description", ""))[:150],
                "cierre": str(row.get("tenderPeriod_endDate", row.get("cierre", "")))[:10],
                "organismo": str(row.get("procuringEntity_name", "")),
                "region": str(row.get("region", "")),
            })
    print(f"  Licitaciones historicas: {len(tenders_list)}")

    # 3. Filtrar
    opportunities = filter_tenders_for_client(tenders_list, profile)
    print(f"  Oportunidades filtradas: {len(opportunities)}")

    # 4. Rivales (sin API, usar datos historicos)
    rival_moves = _check_rivals_offline(profile)

    # 5. Recomendaciones
    recommendations = generate_recommendations(opportunities, rival_moves, profile)

    # 6. Generar PDF
    out_dir = Path(output_dir) if output_dir else ALERT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = _s(nombre).replace(" ", "_")[:30]
    pdf_path = out_dir / f"alerta_{safe_name}_{date_str}.pdf"

    pdf_path = generate_weekly_pdf(
        profile, opportunities, rival_moves, recommendations,
        output_path=pdf_path,
    )
    print(f"  PDF generado: {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")

    # 7. WhatsApp
    wsp_text = generate_whatsapp_text(profile, opportunities, rival_moves, recommendations)
    wsp_path = out_dir / f"alerta_wsp_{safe_name}_{date_str}.txt"
    wsp_path.write_text(wsp_text, encoding="utf-8")
    print(f"  WhatsApp: {wsp_path}")

    return {
        "rut": rut,
        "nombre": nombre,
        "pdf_path": str(pdf_path),
        "wsp_path": str(wsp_path),
        "opportunities": len(opportunities),
        "rival_moves": len(rival_moves),
        "recommendations": len(recommendations),
        "mode": "offline",
    }


def _check_rivals_offline(profile):
    """Genera movimientos de rivales desde datos historicos (sin API)."""
    rivals = profile.get("rivals", [])
    if not rivals:
        return []

    # Buscar en awards_construction si hay adjudicaciones recientes de rivales
    awards_path = FILTERED_DIR / "awards_construction.parquet"
    if not awards_path.exists():
        return []

    moves = []
    try:
        adf = pd.read_parquet(awards_path)
        if "date" in adf.columns:
            adf = adf.sort_values("date", ascending=False)

        for rival in rivals[:3]:
            rival_name = rival["nombre"].lower()
            # Buscar adjudicaciones del rival
            mask = adf.apply(
                lambda r: rival_name in str(r.get("suppliers_name", "")).lower()
                if pd.notna(r.get("suppliers_name")) else False,
                axis=1,
            )
            rival_awards = adf[mask].head(2)
            for _, award in rival_awards.iterrows():
                moves.append({
                    "rival": rival["nombre"],
                    "rival_wins_historicas": rival["wins"],
                    "tender_codigo": str(award.get("tender_id", ""))[:20],
                    "tender_nombre": str(award.get("title", ""))[:70],
                    "tipo": "adjudicado recientemente",
                })
    except Exception:
        pass

    return moves[:3]


# ===================================================================
# CLI
# ===================================================================

def main():
    """CLI: python generate_weekly_alert.py <RUT> [--days 7] [--offline] [--output PATH]"""
    if len(sys.argv) < 2:
        print("Uso: python generate_weekly_alert.py <RUT> [--days 7] [--offline] [--output PATH]")
        sys.exit(1)

    rut = sys.argv[1]
    days = 7
    offline = "--offline" in sys.argv
    output_dir = None

    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            try:
                days = int(sys.argv[idx + 1])
            except ValueError:
                pass

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    print("=" * 60)
    print("  ALERTA SEMANAL PREMIUM — IngenIA Licitaciones")
    print("=" * 60)

    if offline:
        result = generate_weekly_alert_offline(rut, output_dir=output_dir)
    else:
        result = generate_weekly_alert(rut, days=days, output_dir=output_dir)

    if "error" in result:
        print(f"\n  ERROR: {result['error']}")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"  Alerta generada para: {result['nombre']}")
    print(f"  Oportunidades: {result['opportunities']}")
    print(f"  Movimientos rivales: {result['rival_moves']}")
    print(f"  Recomendaciones: {result['recommendations']}")
    print(f"  PDF: {result['pdf_path']}")
    print(f"  WhatsApp: {result['wsp_path']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
