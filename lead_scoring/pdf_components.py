"""
pdf_components.py -Componentes visuales para el PDF diagnóstico.

Cada función recibe (pdf, x, y, w, h, ...) y renderiza EXACTAMENTE
dentro de ese rectángulo. Son funciones puras: no modifican estado global,
no crean páginas, no cambian márgenes.

Forma parte del motor de layout matemático (pdf_engine.py).
Paleta: navy #1B2A4A, gold #B8860B, grises #2D3748/#6B7B8D/#E8ECF0/#AAAAAA.

IngenIA Licitaciones -Engineered Clarity.
"""

from __future__ import annotations

import math
import os
from typing import List, Optional, Tuple

from fpdf import FPDF

from pdf_engine import (
    COLOR_NAVY, COLOR_GOLD, COLOR_GRAY,
    COLOR_WHITE, COLOR_DARK_GRAY, COLOR_MID_GRAY, COLOR_LIGHT_GRAY,
    HEADER_H, METRIC_ROW_H, SECTION_HEADING_H, CALLOUT_H,
    FOOTER_H, PRICING_ROW_H, CTA_H,
)

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _set_font(pdf: FPDF, style: str = "", size: float = 9) -> None:
    """Set Helvetica font -built-in, no file needed."""
    pdf.set_font("Helvetica", style, size)


def _truncate(text: str, pdf: FPDF, max_w: float) -> str:
    """Trunca texto con '...' si excede max_w."""
    if pdf.get_string_width(text) <= max_w:
        return text
    while len(text) > 0 and pdf.get_string_width(text + "...") > max_w:
        text = text[:-1]
    return text + "..."


def _safe_str(val, default: str = "-") -> str:
    """NaN-safe string conversion with latin-1 sanitization for fpdf2."""
    if val is None:
        return default
    try:
        if isinstance(val, float) and math.isnan(val):
            return default
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return default
    return _latin1_safe(s)


def _latin1_safe(text: str) -> str:
    """Replace Unicode chars unsupported by Helvetica/latin-1."""
    replacements = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
        "\u2022": "-",   # bullet
        "\u00b7": "-",   # middle dot
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text


# ---------------------------------------------------------------------------
# 1. HEADER -Altura esperada: 40mm (HEADER_H)
# ---------------------------------------------------------------------------

def render_header(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    empresa: str = "", rut: str = "", region: str = "", fecha: str = "",
) -> None:
    """Barra navy con datos de la empresa.

    Altura esperada: 40mm (HEADER_H).
    Layout: empresa 18pt bold alineada a la izquierda,
    fecha 8pt alineada a la derecha, RUT+región en segunda línea.
    """
    # Fondo navy
    pdf.set_fill_color(*COLOR_NAVY)
    pdf.rect(x, y, w, h, "F")

    pad = 5  # padding interno
    inner_x = x + pad
    inner_w = w - 2 * pad

    # Empresa -bold 18pt, blanco, izquierda
    _set_font(pdf, "B", 18)
    pdf.set_text_color(*COLOR_WHITE)
    empresa_text = _safe_str(empresa, "Empresa")
    empresa_text = _truncate(empresa_text, pdf, inner_w * 0.7)
    pdf.set_xy(inner_x, y + 8)
    pdf.cell(inner_w * 0.7, 8, empresa_text, align="L")

    # Fecha -8pt, blanco, derecha, misma línea
    _set_font(pdf, "", 8)
    pdf.set_xy(inner_x + inner_w * 0.7, y + 10)
    pdf.cell(inner_w * 0.3, 5, _safe_str(fecha), align="R")

    # Segunda línea: RUT + Región
    _set_font(pdf, "", 9)
    pdf.set_text_color(*COLOR_LIGHT_GRAY)
    rut_region = f"RUT: {_safe_str(rut)}"
    if _safe_str(region) != "-":
        rut_region += f"  |  {_safe_str(region)}"
    pdf.set_xy(inner_x, y + 22)
    pdf.cell(inner_w, 5, rut_region, align="L")

    # Subtítulo
    _set_font(pdf, "", 7)
    pdf.set_text_color(180, 190, 210)
    pdf.set_xy(inner_x, y + 30)
    pdf.cell(inner_w, 4, "Diagnostico Competitivo - IngenIA Licitaciones", align="L")


# ---------------------------------------------------------------------------
# 2. METRICS -Altura esperada: 30mm (METRIC_ROW_H)
# ---------------------------------------------------------------------------

def render_metrics(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    metrics: List[Tuple[str, str]],
) -> None:
    """Fila de metric cards con número grande y label debajo.

    Altura esperada: 30mm (METRIC_ROW_H).
    metrics: lista de (valor, label), hasta 5 elementos.
    Cada card tiene border-top navy 1pt.
    """
    n = min(len(metrics), 5)
    if n == 0:
        return

    gap = 3
    card_w = (w - gap * (n - 1)) / n

    for i, (valor, label) in enumerate(metrics[:5]):
        cx = x + i * (card_w + gap)

        # Fondo card
        pdf.set_fill_color(*COLOR_LIGHT_GRAY)
        pdf.rect(cx, y, card_w, h, "F")

        # Border-top navy
        pdf.set_draw_color(*COLOR_NAVY)
        pdf.set_line_width(0.8)
        pdf.line(cx, y, cx + card_w, y)

        # Valor -20pt bold, navy, centrado
        _set_font(pdf, "B", 20)
        pdf.set_text_color(*COLOR_NAVY)
        val_text = _truncate(_safe_str(valor, "-"), pdf, card_w - 4)
        pdf.set_xy(cx, y + 4)
        pdf.cell(card_w, 10, val_text, align="C")

        # Label -7pt, gris medio, centrado
        _set_font(pdf, "", 7)
        pdf.set_text_color(*COLOR_MID_GRAY)
        label_text = _truncate(_safe_str(label, ""), pdf, card_w - 4)
        pdf.set_xy(cx, y + 18)
        pdf.cell(card_w, 5, label_text, align="C")

    pdf.set_line_width(0.2)  # reset


# ---------------------------------------------------------------------------
# 3. SECTION HEADING -Altura esperada: 15mm (SECTION_HEADING_H)
# ---------------------------------------------------------------------------

def render_section_heading(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    num: int = 1, title: str = "", subtitle: str = "",
) -> None:
    """Encabezado de sección con número en círculo, título bold, subtítulo gris.

    Altura esperada: 15mm (SECTION_HEADING_H).
    """
    circle_r = 5
    circle_cx = x + circle_r + 1
    circle_cy = y + h / 2

    # Círculo navy con número
    pdf.set_fill_color(*COLOR_NAVY)
    pdf.circle(circle_cx, circle_cy, circle_r, "F")
    _set_font(pdf, "B", 10)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_xy(circle_cx - circle_r, circle_cy - 3.5)
    pdf.cell(circle_r * 2, 7, str(num), align="C")

    text_x = x + circle_r * 2 + 5

    # Título -13pt bold, dark gray
    _set_font(pdf, "B", 13)
    pdf.set_text_color(*COLOR_DARK_GRAY)
    title_text = _truncate(_safe_str(title, "Sección"), pdf, w - text_x + x - 2)
    pdf.set_xy(text_x, y + 1)
    pdf.cell(w - (text_x - x), 7, title_text, align="L")

    # Subtítulo -8pt, gris medio
    if subtitle:
        _set_font(pdf, "", 8)
        pdf.set_text_color(*COLOR_MID_GRAY)
        sub_text = _truncate(_safe_str(subtitle), pdf, w - text_x + x - 2)
        pdf.set_xy(text_x, y + 8)
        pdf.cell(w - (text_x - x), 5, sub_text, align="L")


# ---------------------------------------------------------------------------
# 4. BODY -Altura variable (caller decides)
# ---------------------------------------------------------------------------

def render_body(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    text: str = "", font_size: float = 9,
) -> None:
    """Bloque de texto multi_cell dentro del box delimitado.

    Altura: la que el caller reserve. Si el texto no cabe, se trunca con '...'.
    """
    _set_font(pdf, "", font_size)
    pdf.set_text_color(*COLOR_DARK_GRAY)

    text = _safe_str(text, "")
    if not text:
        return

    # Estimar líneas que caben
    line_h = font_size * 0.4  # mm por línea aproximado
    max_lines = max(1, int(h / line_h))

    # Truncar por líneas
    lines = text.split("\n")
    output_lines = []
    for raw_line in lines:
        # Wrap manual: partir línea si excede w
        if pdf.get_string_width(raw_line) <= w - 2:
            output_lines.append(raw_line)
        else:
            words = raw_line.split()
            current = ""
            for word in words:
                test = f"{current} {word}".strip()
                if pdf.get_string_width(test) <= w - 4:
                    current = test
                else:
                    if current:
                        output_lines.append(current)
                    current = word
            if current:
                output_lines.append(current)

        if len(output_lines) >= max_lines:
            break

    # Truncar si excede
    if len(output_lines) > max_lines:
        output_lines = output_lines[:max_lines]
        if output_lines:
            output_lines[-1] = output_lines[-1].rstrip()
            if len(output_lines[-1]) > 3:
                output_lines[-1] = output_lines[-1][:-3] + "..."

    final_text = "\n".join(output_lines)
    pdf.set_xy(x + 1, y + 1)
    pdf.multi_cell(w - 2, line_h, final_text, align="L")


# ---------------------------------------------------------------------------
# 5. CHART -Altura esperada: 65mm (CHART_H) o variable
# ---------------------------------------------------------------------------

def render_chart(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    img_path: str = "", caption: str = "",
) -> None:
    """Imagen centrada con caption debajo.

    Altura esperada: variable (CHART_H=65mm por defecto).
    Imagen escalada para caber en w × (h - 8mm para caption).
    """
    caption_h = 8 if caption else 0
    img_h = h - caption_h
    img_w = w

    if img_path and os.path.isfile(img_path):
        # Centrar imagen horizontalmente
        pdf.image(img_path, x, y, img_w, img_h)
    else:
        # Placeholder si no hay imagen
        pdf.set_draw_color(*COLOR_LIGHT_GRAY)
        pdf.set_line_width(0.3)
        pdf.rect(x + 2, y + 2, w - 4, img_h - 4, "D")
        _set_font(pdf, "", 7)
        pdf.set_text_color(*COLOR_MID_GRAY)
        pdf.set_xy(x, y + img_h / 2 - 3)
        pdf.cell(w, 6, "[chart]", align="C")

    # Caption
    if caption:
        _set_font(pdf, "", 7)
        pdf.set_text_color(*COLOR_MID_GRAY)
        cap_text = _truncate(_safe_str(caption), pdf, w - 4)
        pdf.set_xy(x, y + img_h + 1)
        pdf.cell(w, 5, cap_text, align="C")

    pdf.set_line_width(0.2)


# ---------------------------------------------------------------------------
# 6. TABLE -Altura variable (caller calculates)
# ---------------------------------------------------------------------------

def render_table(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    headers: List[str] = None,
    rows: List[List[str]] = None,
    col_widths: List[float] = None,
    bold_col: int = -1,
) -> None:
    """Tabla limpia: header navy, filas alternas gris claro, sin bordes verticales.

    Altura: caller decide. Filas que no caben se truncan.
    col_widths: lista de ratios (deben sumar ~1.0). Si None, distribuye equitativamente.
    bold_col: índice de columna a renderizar en bold (-1 = ninguna).
    """
    if not headers or not rows:
        return

    n_cols = len(headers)
    if col_widths is None:
        col_widths = [1.0 / n_cols] * n_cols

    # Convertir ratios a mm
    widths = [r * w for r in col_widths]

    header_h = 7
    row_h = 6.5
    max_rows = max(0, int((h - header_h) / row_h))

    cy = y

    # Header
    pdf.set_fill_color(*COLOR_NAVY)
    pdf.rect(x, cy, w, header_h, "F")
    _set_font(pdf, "B", 7)
    pdf.set_text_color(*COLOR_WHITE)

    cx = x
    for i, hdr in enumerate(headers):
        hdr_text = _truncate(_safe_str(hdr, ""), pdf, widths[i] - 2)
        pdf.set_xy(cx + 1, cy + 1)
        pdf.cell(widths[i] - 2, header_h - 2, hdr_text, align="L")
        cx += widths[i]
    cy += header_h

    # Rows
    for r_idx, row in enumerate(rows[:max_rows]):
        # Fondo alterno
        if r_idx % 2 == 1:
            pdf.set_fill_color(*COLOR_LIGHT_GRAY)
            pdf.rect(x, cy, w, row_h, "F")

        cx = x
        for c_idx, cell_val in enumerate(row[:n_cols]):
            if c_idx == bold_col:
                _set_font(pdf, "B", 7)
                pdf.set_text_color(*COLOR_DARK_GRAY)
            else:
                _set_font(pdf, "", 7)
                pdf.set_text_color(*COLOR_DARK_GRAY)

            cell_text = _truncate(_safe_str(cell_val, "-"), pdf, widths[c_idx] - 3)
            pdf.set_xy(cx + 1, cy + 1)
            pdf.cell(widths[c_idx] - 2, row_h - 2, cell_text, align="L")
            cx += widths[c_idx]
        cy += row_h

    # Línea de cierre
    pdf.set_draw_color(*COLOR_GRAY)
    pdf.set_line_width(0.3)
    pdf.line(x, cy, x + w, cy)
    pdf.set_line_width(0.2)


# ---------------------------------------------------------------------------
# 7. CALLOUT -Altura esperada: 20mm (CALLOUT_H) o variable
# ---------------------------------------------------------------------------

def render_callout(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    text: str = "", color: Tuple[int, int, int] = COLOR_GOLD,
) -> None:
    """Bloque de texto con borde izquierdo de color.

    Altura esperada: 20mm (CALLOUT_H) o variable.
    Borde izquierdo 2mm del color indicado, texto 9pt dentro.
    """
    border_w = 2
    bg_pad = 0

    # Fondo sutil
    pdf.set_fill_color(250, 248, 240)
    pdf.rect(x, y, w, h, "F")

    # Borde izquierdo
    pdf.set_fill_color(*color)
    pdf.rect(x, y, border_w, h, "F")

    # Texto
    _set_font(pdf, "", 9)
    pdf.set_text_color(*COLOR_DARK_GRAY)
    text = _safe_str(text, "")
    if text:
        line_h = 4.2
        max_lines = max(1, int((h - 4) / line_h))

        lines = text.split("\n")
        output = []
        for line in lines:
            if pdf.get_string_width(line) <= w - border_w - 8:
                output.append(line)
            else:
                words = line.split()
                current = ""
                for word in words:
                    test = f"{current} {word}".strip()
                    if pdf.get_string_width(test) <= w - border_w - 8:
                        current = test
                    else:
                        if current:
                            output.append(current)
                        current = word
                if current:
                    output.append(current)
            if len(output) >= max_lines:
                break

        output = output[:max_lines]
        final = "\n".join(output)
        pdf.set_xy(x + border_w + 4, y + 3)
        pdf.multi_cell(w - border_w - 6, line_h, final, align="L")


# ---------------------------------------------------------------------------
# 8. PRICING ROW -Altura esperada: 55mm (PRICING_ROW_H)
# ---------------------------------------------------------------------------

def render_pricing_row(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    tiers: List[dict] = None,
) -> None:
    """3 cards de pricing lado a lado.

    Altura esperada: 55mm (PRICING_ROW_H).
    tiers: lista de dicts con keys: title, price, bullets (list[str]), highlight (bool).
    """
    if not tiers:
        return

    n = min(len(tiers), 3)
    gap = 4
    card_w = (w - gap * (n - 1)) / n

    for i, tier in enumerate(tiers[:3]):
        cx = x + i * (card_w + gap)
        is_highlight = tier.get("highlight", False)

        # Card background
        if is_highlight:
            pdf.set_fill_color(*COLOR_NAVY)
            text_color = COLOR_WHITE
            accent = COLOR_GOLD
        else:
            pdf.set_fill_color(*COLOR_LIGHT_GRAY)
            text_color = COLOR_DARK_GRAY
            accent = COLOR_NAVY

        pdf.rect(cx, y, card_w, h, "F")

        # Border-top accent
        pdf.set_fill_color(*accent)
        pdf.rect(cx, y, card_w, 1.5, "F")

        # Title
        _set_font(pdf, "B", 9)
        pdf.set_text_color(*text_color)
        title = _truncate(_safe_str(tier.get("title", ""), "Plan"), pdf, card_w - 6)
        pdf.set_xy(cx + 3, y + 5)
        pdf.cell(card_w - 6, 5, title, align="C")

        # Price
        _set_font(pdf, "B", 14)
        pdf.set_text_color(*accent if not is_highlight else COLOR_GOLD)
        price = _truncate(_safe_str(tier.get("price", ""), "-"), pdf, card_w - 6)
        pdf.set_xy(cx + 3, y + 13)
        pdf.cell(card_w - 6, 7, price, align="C")

        # Bullets
        _set_font(pdf, "", 7)
        pdf.set_text_color(*text_color)
        bullets = tier.get("bullets", [])
        bullet_y = y + 24
        for bi, bullet in enumerate(bullets[:4]):
            if bullet_y + 4 > y + h - 2:
                break
            btext = _truncate(f"- {_safe_str(bullet, '')}", pdf, card_w - 10)
            pdf.set_xy(cx + 5, bullet_y)
            pdf.cell(card_w - 10, 4, btext, align="L")
            bullet_y += 4.5


# ---------------------------------------------------------------------------
# 9. CTA -Altura esperada: 35mm (CTA_H)
# ---------------------------------------------------------------------------

def render_cta(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    text: str = "", contact: str = "",
) -> None:
    """Card navy con texto blanco centrado y datos de contacto.

    Altura esperada: 35mm (CTA_H).
    """
    # Fondo navy
    pdf.set_fill_color(*COLOR_NAVY)
    pdf.rect(x, y, w, h, "F")

    # Texto principal -12pt bold, gold
    _set_font(pdf, "B", 12)
    pdf.set_text_color(*COLOR_GOLD)
    cta_text = _safe_str(text, "¿Listo para mejorar sus resultados?")
    cta_text = _truncate(cta_text, pdf, w - 10)
    pdf.set_xy(x, y + 6)
    pdf.cell(w, 7, cta_text, align="C")

    # Contacto -9pt, blanco
    _set_font(pdf, "", 9)
    pdf.set_text_color(*COLOR_WHITE)
    contact_text = _safe_str(contact, "")
    if contact_text:
        pdf.set_xy(x, y + 17)
        pdf.cell(w, 5, contact_text, align="C")

    # Línea decorativa gold
    pdf.set_draw_color(*COLOR_GOLD)
    pdf.set_line_width(0.5)
    line_w = 30
    pdf.line(x + w / 2 - line_w / 2, y + h - 5, x + w / 2 + line_w / 2, y + h - 5)
    pdf.set_line_width(0.2)


# ---------------------------------------------------------------------------
# 10. FOOTER -Altura esperada: 10mm (FOOTER_H)
# ---------------------------------------------------------------------------

def render_footer(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    page_num: int = 0, total_pages: int = 0,
) -> None:
    """Línea fina + 3 textos al pie: marca izquierda, confidencial centro, página derecha.

    Altura esperada: 10mm (FOOTER_H).
    """
    # Línea separadora
    pdf.set_draw_color(*COLOR_GRAY)
    pdf.set_line_width(0.3)
    pdf.line(x, y + 1, x + w, y + 1)

    _set_font(pdf, "", 7)
    pdf.set_text_color(*COLOR_MID_GRAY)

    # Izquierda: marca
    pdf.set_xy(x, y + 3)
    pdf.cell(w / 3, 4, "IngenIA Licitaciones", align="L")

    # Centro: confidencial
    pdf.set_xy(x + w / 3, y + 3)
    pdf.cell(w / 3, 4, "Confidencial", align="C")

    # Derecha: página
    pdf.set_xy(x + 2 * w / 3, y + 3)
    if total_pages > 0:
        pdf.cell(w / 3, 4, f"Página {page_num} de {total_pages}", align="R")
    elif page_num > 0:
        pdf.cell(w / 3, 4, f"Página {page_num}", align="R")

    pdf.set_line_width(0.2)


# ---------------------------------------------------------------------------
# Test standalone -genera PDF de prueba con todos los componentes
# ---------------------------------------------------------------------------

def _test():
    """Genera un PDF de 1 página con header+metrics+section+body+table+callout.
    Verifica que nada se solapa usando alturas matemáticas.
    """
    import tempfile
    from pdf_engine import PageLayout, SPACER_MD, SPACER_SM, SPACER_LG

    layout = PageLayout()

    # Footer counter
    _page_count = [0]

    def _footer(pdf, x, y, w, h):
        _page_count[0] += 1
        render_footer(pdf, x, y, w, h, page_num=_page_count[0], total_pages=2)

    layout.set_footer(_footer, FOOTER_H)

    # --- Página 1: Portada ---
    layout.new_page()

    layout.add_element(
        HEADER_H,
        lambda pdf, x, y, w, h: render_header(
            pdf, x, y, w, h,
            empresa="Constructora Guerrero y Cutipa Ltda.",
            rut="132385-4",
            region="Región de Tarapacá",
            fecha="01/04/2026",
        ),
        label="header",
    )
    layout.add_spacer(SPACER_LG)

    layout.add_element(
        METRIC_ROW_H,
        lambda pdf, x, y, w, h: render_metrics(
            pdf, x, y, w, h,
            metrics=[
                ("23%", "Win Rate"),
                ("47", "Postulaciones"),
                ("$142M", "Monto Prom."),
                ("11", "Adjudicaciones"),
                ("5", "Rivales Directos"),
            ],
        ),
        label="metrics",
    )
    layout.add_spacer(SPACER_MD)

    layout.add_element(
        35,
        lambda pdf, x, y, w, h: render_body(
            pdf, x, y, w, h,
            text=(
                "Constructora Guerrero y Cutipa muestra un desempeño superior "
                "al promedio del sector en licitaciones públicas. Con una tasa de "
                "adjudicación del 23%, se ubica en el percentil 72 del mercado. "
                "Sin embargo, existe una oportunidad significativa de mejora en "
                "licitaciones de tipo LP, donde la brecha con los líderes del "
                "sector representa un costo de oportunidad estimado en $340M anuales."
            ),
            font_size=9,
        ),
        label="body_resumen",
    )
    layout.add_spacer(SPACER_MD)

    layout.add_element(
        50,
        lambda pdf, x, y, w, h: render_table(
            pdf, x, y, w, h,
            headers=["#", "Sección", "Descripción"],
            rows=[
                ["1", "Desempeño vs Mercado", "Win rate, radar de capacidades"],
                ["2", "Inteligencia Competitiva", "Rivales directos, patrones"],
                ["3", "Análisis Temporal", "Evolución y tendencias"],
                ["4", "Costo de Oportunidad", "Escenarios financieros"],
                ["5", "Recomendaciones", "Plan de acción y siguiente paso"],
            ],
            col_widths=[0.08, 0.30, 0.62],
            bold_col=1,
        ),
        label="table_contenido",
    )

    print(f"Página 1:\n{layout.page_height_breakdown()}")

    # --- Página 2: Componentes adicionales ---
    layout.new_page()

    layout.add_element(
        SECTION_HEADING_H,
        lambda pdf, x, y, w, h: render_section_heading(
            pdf, x, y, w, h,
            num=2, title="Desempeño vs Mercado",
            subtitle="Análisis comparativo de su posición competitiva",
        ),
        label="section_heading",
    )
    layout.add_spacer(SPACER_MD)

    # Chart placeholder (sin imagen real)
    layout.add_element(
        65,
        lambda pdf, x, y, w, h: render_chart(
            pdf, x, y, w, h,
            img_path="",  # no image -placeholder
            caption="Fig. 1 -Tasa de adjudicación vs promedio del sector",
        ),
        label="chart_gauge",
    )
    layout.add_spacer(SPACER_MD)

    layout.add_element(
        CALLOUT_H,
        lambda pdf, x, y, w, h: render_callout(
            pdf, x, y, w, h,
            text=(
                "Hallazgo clave: Su win rate del 23% supera al promedio del "
                "sector (18%), pero está 9 puntos por debajo del top 10%. "
                "Cerrar esa brecha podría significar ~$340M adicionales al año."
            ),
            color=COLOR_GOLD,
        ),
        label="callout",
    )
    layout.add_spacer(SPACER_MD)

    layout.add_element(
        PRICING_ROW_H,
        lambda pdf, x, y, w, h: render_pricing_row(
            pdf, x, y, w, h,
            tiers=[
                {
                    "title": "Esencial",
                    "price": "$89.000/mes",
                    "bullets": ["Monitoreo básico", "Alertas semanales", "1 región"],
                },
                {
                    "title": "Profesional",
                    "price": "$179.000/mes",
                    "bullets": ["Diagnóstico completo", "Alertas diarias", "3 regiones", "Soporte prioritario"],
                    "highlight": True,
                },
                {
                    "title": "Enterprise",
                    "price": "Consultar",
                    "bullets": ["Todo incluido", "API acceso", "Nacional", "Consultor dedicado"],
                },
            ],
        ),
        label="pricing_row",
    )
    layout.add_spacer(SPACER_SM)

    layout.add_element(
        CTA_H,
        lambda pdf, x, y, w, h: render_cta(
            pdf, x, y, w, h,
            text="¿Listo para ganar más licitaciones?",
            contact="Sebastián Cortés -scortes@ingenia.cl -+56 9 1234 5678",
        ),
        label="cta",
    )

    print(f"\nPágina 2:\n{layout.page_height_breakdown()}")

    # Guardar
    test_path = os.path.join(tempfile.gettempdir(), "pdf_components_test.pdf")
    layout.save(test_path)
    file_size = os.path.getsize(test_path)
    print(f"\nPDF test: {test_path} ({file_size:,} bytes)")
    print(f"Páginas: {layout.page_count}")

    assert layout.page_count == 2, f"Expected 2 pages, got {layout.page_count}"
    assert file_size > 2000, f"PDF too small: {file_size}"

    print("\n=== Components OK ===")


if __name__ == "__main__":
    _test()
