"""
Sistema de diseno premium para PDFs de IngenIA Licitaciones.

Capa de estilos reutilizable: paleta, tipografia, layout grid,
y componentes visuales fpdf2 (header_bar, section_title, metric_card,
insight_callout, comparison_table, footer).

Estilo referencia: reportes McKinsey/Bain — limpio, data-heavy,
jerarquia visual clara, documento ejecutivo.

Uso:
    from pdf_design import PremiumPDF, COLORS, TYPOGRAPHY, LAYOUT
    pdf = PremiumPDF()
    pdf.add_page()
    pdf.header_bar("Diagnostico Competitivo", "EMPRESA S.A.", "76.123.456-7")
    pdf.metric_card(x, y, "24.5%", "Win Rate", "Sobre promedio del rubro")
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
from fpdf import FPDF


# ═══════════════════════════════════════════════════════════════
# PALETA DE COLORES PREMIUM
# ═══════════════════════════════════════════════════════════════

COLORS = {
    # Primarios
    "navy":            (18, 32, 58),      # fondo header, titulos principales
    "navy_light":      (30, 48, 80),      # hover/variant navy
    "blue":            (41, 98, 155),      # acentos corporativos, links
    "blue_light":      (66, 133, 183),    # acentos secundarios

    # Acentos premium (dorado/cobrizo)
    "gold":            (191, 155, 81),     # highlights, metricas clave
    "gold_light":      (218, 190, 130),   # bordes dorados suaves
    "copper":          (176, 124, 67),     # acento calido alternativo

    # Positivo / Negativo / Neutro
    "green":           (39, 145, 76),      # bueno, sobre promedio
    "green_light":     (232, 245, 233),   # fondo positivo
    "red":             (192, 44, 56),      # alerta, bajo promedio
    "red_light":       (253, 237, 237),   # fondo negativo
    "amber":           (214, 158, 46),     # warning, zona media
    "amber_light":     (255, 248, 225),   # fondo warning

    # Grises elegantes
    "text_primary":    (33, 37, 41),       # texto principal
    "text_secondary":  (108, 117, 125),   # texto secundario, labels
    "text_muted":      (153, 163, 173),   # captions, notas al pie
    "border":          (210, 215, 220),   # bordes suaves
    "border_light":    (233, 236, 239),   # separadores
    "bg_light":        (245, 247, 250),   # fondo secciones alternas
    "bg_card":         (250, 251, 252),   # fondo cards
    "white":           (255, 255, 255),   # fondo principal
}

# Colores para matplotlib (0-1 range)
MCOLORS = {k: tuple(c / 255 for c in v) for k, v in COLORS.items()}


# ═══════════════════════════════════════════════════════════════
# TIPOGRAFIA
# ═══════════════════════════════════════════════════════════════

TYPOGRAPHY = {
    "h1":      {"family": "Helvetica", "style": "B", "size": 22},
    "h2":      {"family": "Helvetica", "style": "B", "size": 16},
    "h3":      {"family": "Helvetica", "style": "B", "size": 12},
    "body":    {"family": "Helvetica", "style": "",  "size": 10},
    "body_b":  {"family": "Helvetica", "style": "B", "size": 10},
    "small":   {"family": "Helvetica", "style": "",  "size": 9},
    "caption": {"family": "Helvetica", "style": "",  "size": 8},
    "metric":  {"family": "Helvetica", "style": "B", "size": 28},
    "metric_label": {"family": "Helvetica", "style": "",  "size": 9},
    "metric_sub":   {"family": "Helvetica", "style": "",  "size": 8},
}


# ═══════════════════════════════════════════════════════════════
# LAYOUT GRID
# ═══════════════════════════════════════════════════════════════

LAYOUT = {
    # Pagina A4 (210 x 297 mm)
    "page_w":        210,
    "page_h":        297,

    # Margenes
    "margin_left":   15,
    "margin_right":  15,
    "margin_top":    15,
    "margin_bottom": 20,

    # Area util
    "content_w":     180,   # 210 - 15 - 15

    # Columnas (sobre content_w = 180)
    "col_full":      180,
    "col_half":      87,    # (180 - 6) / 2
    "col_third":     56,    # (180 - 12) / 3
    "col_gutter":    6,     # espacio entre columnas

    # Spacing vertical
    "sp_xs":         2,
    "sp_sm":         4,
    "sp_md":         8,
    "sp_lg":         12,
    "sp_xl":         18,
    "sp_section":    14,    # entre secciones principales

    # Header bar
    "header_h":      38,

    # Metric cards
    "card_h":        32,
    "card_w_5":      33.6,  # 5 cards en fila: (180 - 4*3) / 5
    "card_gap":      3,

    # Footer
    "footer_h":      12,
    "footer_y":      282,   # 297 - 15
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _s(text):
    """Sanitiza texto para fpdf2 (compatible Latin-1)."""
    if pd.isna(text) or text is None:
        return ""
    text = str(text)
    # Reemplazos comunes Unicode -> Latin-1
    replacements = {
        "\u2013": "-",   # en-dash
        "\u2014": "-",   # em-dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
        "\u2022": "-",   # bullet
        "\u00a0": " ",   # non-breaking space
        "\ufffd": "o",   # replacement char
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return text.encode("latin-1", errors="replace").decode("latin-1")


def _name(raw):
    """Limpia nombre de empresa para mostrar."""
    name = _s(raw)
    if "|" in name:
        parts = [p.strip() for p in name.split("|")]
        non_upper = [p for p in parts if not p.isupper() and len(p) > 3]
        if non_upper:
            return non_upper[0]
        return min(parts, key=len)
    return name


def _money(amount):
    """Formatea monto CLP."""
    if pd.isna(amount) or amount == 0:
        return "$0"
    a = float(amount)
    if a >= 1e9:
        return "${:,.1f}B".format(a / 1e9).replace(",", ".")
    if a >= 1e6:
        return "${:,.0f}MM".format(a / 1e6).replace(",", ".")
    if a >= 1e3:
        return "${:,.0f}".format(a).replace(",", ".")
    return "${:,.0f}".format(a).replace(",", ".")


def _pct(value):
    """Formatea como porcentaje."""
    if pd.isna(value):
        return "N/A"
    return "{:.1f}%".format(float(value) * 100)


# ═══════════════════════════════════════════════════════════════
# PREMIUM PDF CLASS
# ═══════════════════════════════════════════════════════════════

class PremiumPDF(FPDF):
    """PDF premium con componentes reutilizables estilo McKinsey/Bain."""

    def __init__(self, orientation="P", unit="mm", format="A4"):
        super().__init__(orientation=orientation, unit=unit, format=format)
        self.set_auto_page_break(auto=False)
        self.set_margins(
            LAYOUT["margin_left"],
            LAYOUT["margin_top"],
            LAYOUT["margin_right"],
        )
        self._company_name = ""
        self._report_title = ""

    # ─── Setters para contexto ───

    def set_context(self, company_name="", report_title="Diagnostico Competitivo"):
        self._company_name = _s(company_name)
        self._report_title = _s(report_title)

    # ─── Font helpers ───

    def _set_font(self, style_key):
        """Aplica un estilo tipografico predefinido."""
        t = TYPOGRAPHY[style_key]
        self.set_font(t["family"], t["style"], t["size"])

    def _set_color(self, color_key, kind="text"):
        """Aplica un color predefinido. kind: 'text', 'fill', 'draw'."""
        r, g, b = COLORS[color_key]
        if kind == "text":
            self.set_text_color(r, g, b)
        elif kind == "fill":
            self.set_fill_color(r, g, b)
        elif kind == "draw":
            self.set_draw_color(r, g, b)

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: HEADER BAR
    # ═══════════════════════════════════════════════════════════

    def header_bar(self, title, subtitle="", detail=""):
        """
        Barra navy full-width en parte superior de la pagina.
        title: texto principal (ej: nombre empresa)
        subtitle: linea secundaria (ej: RUT, region)
        detail: linea terciaria (ej: fecha)
        """
        x0 = 0
        w = LAYOUT["page_w"]
        h = LAYOUT["header_h"]
        y0 = self.get_y() if self.get_y() > LAYOUT["margin_top"] else 0

        # Fondo navy
        self._set_color("navy", "fill")
        self.rect(x0, y0, w, h, "F")

        # Linea dorada inferior
        self._set_color("gold", "draw")
        self.set_line_width(0.6)
        self.line(x0, y0 + h, x0 + w, y0 + h)

        # Titulo
        self._set_font("h1")
        self._set_color("white", "text")
        self.set_xy(LAYOUT["margin_left"], y0 + 6)
        self.cell(LAYOUT["content_w"], 10, _s(title), align="L")

        # Subtitulo
        if subtitle:
            self._set_font("body")
            self._set_color("gold_light", "text")
            self.set_xy(LAYOUT["margin_left"], y0 + 17)
            self.cell(LAYOUT["content_w"], 6, _s(subtitle), align="L")

        # Detalle (alineado a la derecha)
        if detail:
            self._set_font("caption")
            self._set_color("text_muted", "text")
            self.set_xy(LAYOUT["margin_left"], y0 + 8)
            self.cell(LAYOUT["content_w"], 5, _s(detail), align="R")

        # Branding
        self._set_font("caption")
        self._set_color("gold_light", "text")
        self.set_xy(LAYOUT["margin_left"], y0 + 26)
        self.cell(LAYOUT["content_w"], 5, "IngenIA Licitaciones", align="R")

        # Restaurar posicion
        self.set_xy(LAYOUT["margin_left"], y0 + h + LAYOUT["sp_md"])
        self._set_color("text_primary", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: SECTION TITLE
    # ═══════════════════════════════════════════════════════════

    def section_title(self, number, title, subtitle=""):
        """
        Titulo de seccion con numero, linea decorativa.
        number: int o str (ej: 1, "01")
        title: titulo principal
        subtitle: descripcion breve
        """
        y = self.get_y()
        ml = LAYOUT["margin_left"]
        cw = LAYOUT["content_w"]

        # Numero en circulo navy
        num_w = 8
        self._set_color("navy", "fill")
        self.ellipse(ml, y, num_w, num_w, "F")
        self._set_font("body_b")
        self._set_color("white", "text")
        self.set_xy(ml, y + 0.8)
        self.cell(num_w, num_w - 1, str(number), align="C")

        # Titulo
        self._set_font("h2")
        self._set_color("navy", "text")
        self.set_xy(ml + num_w + 3, y)
        self.cell(cw - num_w - 3, 8, _s(title), align="L")

        # Subtitulo
        if subtitle:
            self._set_font("small")
            self._set_color("text_secondary", "text")
            self.set_xy(ml + num_w + 3, y + 8)
            self.cell(cw - num_w - 3, 5, _s(subtitle), align="L")
            y += 5

        # Linea decorativa
        y_line = y + 10
        self._set_color("gold", "draw")
        self.set_line_width(0.4)
        self.line(ml, y_line, ml + 40, y_line)
        self._set_color("border_light", "draw")
        self.set_line_width(0.2)
        self.line(ml + 40, y_line, ml + cw, y_line)

        self.set_xy(ml, y_line + LAYOUT["sp_md"])
        self._set_color("text_primary", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: METRIC CARD
    # ═══════════════════════════════════════════════════════════

    def metric_card(self, x, y, value, label, subtext="", accent="navy"):
        """
        Card compacta con numero grande + label + subtexto.
        x, y: posicion superior-izquierda
        value: numero/texto principal (ej: "24.5%")
        label: etiqueta (ej: "Win Rate")
        subtext: texto adicional (ej: "Sobre promedio")
        accent: color del borde superior ("navy", "gold", "green", "red")
        """
        w = LAYOUT["card_w_5"]
        h = LAYOUT["card_h"]

        # Fondo card
        self._set_color("bg_card", "fill")
        self._set_color("border", "draw")
        self.set_line_width(0.3)
        self.rect(x, y, w, h, "DF")

        # Borde superior con acento
        self._set_color(accent, "draw")
        self.set_line_width(1.0)
        self.line(x + 0.5, y, x + w - 0.5, y)

        # Valor principal
        self._set_font("h2")
        self._set_color("navy", "text")
        self.set_xy(x + 1.5, y + 3)
        self.cell(w - 3, 9, _s(str(value)), align="C")

        # Label
        self._set_font("metric_label")
        self._set_color("text_secondary", "text")
        self.set_xy(x + 1.5, y + 13)
        self.cell(w - 3, 5, _s(label), align="C")

        # Subtext
        if subtext:
            self._set_font("metric_sub")
            self._set_color("text_muted", "text")
            self.set_xy(x + 1.5, y + 19)
            self.cell(w - 3, 4, _s(subtext), align="C")

        # Restaurar
        self._set_color("text_primary", "text")
        self.set_line_width(0.2)

    def metric_cards_row(self, y, cards):
        """
        Fila de hasta 5 metric cards.
        cards: lista de dicts con keys: value, label, subtext (opt), accent (opt)
        """
        x = LAYOUT["margin_left"]
        w = LAYOUT["card_w_5"]
        gap = LAYOUT["card_gap"]
        for card in cards:
            self.metric_card(
                x, y,
                value=card["value"],
                label=card["label"],
                subtext=card.get("subtext", ""),
                accent=card.get("accent", "navy"),
            )
            x += w + gap

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: INSIGHT CALLOUT
    # ═══════════════════════════════════════════════════════════

    def insight_callout(self, text, style="info", icon_text=None):
        """
        Caja destacada con borde izquierdo grueso + icono textual.
        text: contenido del callout
        style: "info" (azul), "warning" (amber), "success" (verde), "danger" (rojo)
        icon_text: texto del icono (ej: "!", "i", ">"). Auto si None.
        """
        style_map = {
            "info":    {"border": "blue",  "bg": "bg_light",    "icon": "i"},
            "warning": {"border": "amber", "bg": "amber_light", "icon": "!"},
            "success": {"border": "green", "bg": "green_light", "icon": "+"},
            "danger":  {"border": "red",   "bg": "red_light",   "icon": "!"},
        }
        s = style_map.get(style, style_map["info"])
        icon = icon_text or s["icon"]

        ml = LAYOUT["margin_left"]
        cw = LAYOUT["content_w"]
        y = self.get_y()
        border_w = 3
        pad = 4

        # Calcular alto necesario
        self._set_font("body")
        safe_text = _s(text)
        text_w = cw - border_w - pad * 2 - 8
        # Estimar lineas
        n_lines = max(1, len(safe_text) / (text_w / 2.2))
        box_h = max(14, n_lines * 5 + 8)

        # Fondo
        self._set_color(s["bg"], "fill")
        self.rect(ml, y, cw, box_h, "F")

        # Borde izquierdo grueso
        self._set_color(s["border"], "draw")
        self.set_line_width(border_w)
        self.line(ml + border_w / 2, y, ml + border_w / 2, y + box_h)
        self.set_line_width(0.2)

        # Icono
        self._set_font("body_b")
        self._set_color(s["border"], "text")
        self.set_xy(ml + border_w + 2, y + 3)
        self.cell(6, 5, _s(icon), align="C")

        # Texto
        self._set_font("body")
        self._set_color("text_primary", "text")
        self.set_xy(ml + border_w + 8, y + 3)
        self.multi_cell(text_w, 5, safe_text, align="L")

        new_y = max(self.get_y() + 2, y + box_h)
        self.set_xy(ml, new_y + LAYOUT["sp_sm"])

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: COMPARISON TABLE
    # ═══════════════════════════════════════════════════════════

    def comparison_table(self, headers, rows, col_widths=None, highlight_col=0):
        """
        Tabla comparativa 'Tu empresa vs Mercado'.
        headers: lista de strings (ej: ["Metrica", "Tu empresa", "Promedio", "Top 10%"])
        rows: lista de listas de strings
        col_widths: lista de anchos (mm). Auto si None.
        highlight_col: columna a resaltar con color (1-based, 0=ninguna)
        """
        ml = LAYOUT["margin_left"]
        cw = LAYOUT["content_w"]
        n_cols = len(headers)

        if col_widths is None:
            col_widths = [cw / n_cols] * n_cols

        y = self.get_y()
        row_h = 7
        header_h = 8

        # Header de tabla
        self._set_color("navy", "fill")
        x = ml
        for i, (hdr, w) in enumerate(zip(headers, col_widths)):
            self.rect(x, y, w, header_h, "F")
            self._set_font("small")
            self._set_color("white", "text")
            self.set_xy(x, y + 1)
            self.cell(w, header_h - 2, _s(hdr), align="C")
            x += w

        y += header_h

        # Filas
        for row_idx, row in enumerate(rows):
            bg = "bg_light" if row_idx % 2 == 0 else "white"
            x = ml
            for col_idx, (cell, w) in enumerate(zip(row, col_widths)):
                self._set_color(bg, "fill")
                self.rect(x, y, w, row_h, "F")

                # Highlight column
                if col_idx + 1 == highlight_col:
                    self._set_color("navy", "fill")
                    self.rect(x, y, w, row_h, "F")
                    self._set_font("body_b")
                    self._set_color("white", "text")
                elif col_idx == 0:
                    self._set_font("body_b")
                    self._set_color("text_primary", "text")
                else:
                    self._set_font("body")
                    self._set_color("text_primary", "text")

                self.set_xy(x + 1, y)
                self.cell(w - 2, row_h, _s(str(cell)), align="C" if col_idx > 0 else "L")
                x += w
            y += row_h

        # Borde inferior
        self._set_color("border", "draw")
        self.set_line_width(0.3)
        self.line(ml, y, ml + sum(col_widths), y)
        self.set_line_width(0.2)

        self.set_xy(ml, y + LAYOUT["sp_sm"])
        self._set_color("text_primary", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: SIMPLE TABLE
    # ═══════════════════════════════════════════════════════════

    def simple_table(self, headers, rows, col_widths=None):
        """Tabla simple sin highlight, bordes suaves."""
        ml = LAYOUT["margin_left"]
        cw = LAYOUT["content_w"]
        n_cols = len(headers)

        if col_widths is None:
            col_widths = [cw / n_cols] * n_cols

        y = self.get_y()
        row_h = 6.5
        header_h = 7

        # Header
        self._set_color("bg_light", "fill")
        self._set_color("border", "draw")
        self.set_line_width(0.2)
        x = ml
        for hdr, w in zip(headers, col_widths):
            self.rect(x, y, w, header_h, "DF")
            self._set_font("small")
            self._set_color("text_secondary", "text")
            self.set_xy(x + 1, y + 0.5)
            self.cell(w - 2, header_h - 1, _s(hdr), align="C")
            x += w

        y += header_h

        # Rows
        for row_idx, row in enumerate(rows):
            x = ml
            for col_idx, (cell, w) in enumerate(zip(row, col_widths)):
                bg = "white" if row_idx % 2 == 0 else "bg_card"
                self._set_color(bg, "fill")
                self.rect(x, y, w, row_h, "F")
                self._set_font("body" if col_idx > 0 else "body_b")
                self._set_color("text_primary", "text")
                self.set_xy(x + 1, y)
                self.cell(w - 2, row_h, _s(str(cell)), align="C" if col_idx > 0 else "L")
                x += w
            y += row_h

        self.set_xy(ml, y + LAYOUT["sp_xs"])
        self._set_color("text_primary", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: FOOTER PROFESIONAL
    # ═══════════════════════════════════════════════════════════

    def professional_footer(self, page_num=None, total_pages=None):
        """
        Footer profesional con linea, branding, fecha, pagina.
        """
        y = LAYOUT["footer_y"]
        ml = LAYOUT["margin_left"]
        cw = LAYOUT["content_w"]

        # Linea separadora
        self._set_color("border_light", "draw")
        self.set_line_width(0.3)
        self.line(ml, y, ml + cw, y)

        y += 2

        # Izquierda: branding
        self._set_font("caption")
        self._set_color("text_muted", "text")
        self.set_xy(ml, y)
        self.cell(cw / 3, 4, "IngenIA Licitaciones", align="L")

        # Centro: confidencial
        self.set_xy(ml + cw / 3, y)
        self.cell(cw / 3, 4, "Documento confidencial", align="C")

        # Derecha: pagina
        if page_num is not None:
            page_text = "Pag. {}".format(page_num)
            if total_pages:
                page_text += " de {}".format(total_pages)
            self.set_xy(ml + 2 * cw / 3, y)
            self.cell(cw / 3, 4, page_text, align="R")

        self._set_color("text_primary", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: TEXT BLOCK
    # ═══════════════════════════════════════════════════════════

    def text_block(self, text, style="body", color="text_primary",
                   width=None, align="L", line_height=5):
        """Bloque de texto multi-linea con estilo."""
        ml = LAYOUT["margin_left"]
        w = width or LAYOUT["content_w"]
        self._set_font(style)
        self._set_color(color, "text")
        self.set_x(ml)
        self.multi_cell(w, line_height, _s(text), align=align)

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: DIVIDER
    # ═══════════════════════════════════════════════════════════

    def divider(self, style="light"):
        """Linea horizontal decorativa."""
        ml = LAYOUT["margin_left"]
        cw = LAYOUT["content_w"]
        y = self.get_y() + LAYOUT["sp_xs"]

        if style == "gold":
            self._set_color("gold", "draw")
            self.set_line_width(0.5)
        elif style == "navy":
            self._set_color("navy", "draw")
            self.set_line_width(0.3)
        else:
            self._set_color("border_light", "draw")
            self.set_line_width(0.2)

        self.line(ml, y, ml + cw, y)
        self.set_xy(ml, y + LAYOUT["sp_sm"])
        self.set_line_width(0.2)

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: SPACER
    # ═══════════════════════════════════════════════════════════

    def spacer(self, size="md"):
        """Espacio vertical."""
        sp = LAYOUT.get("sp_" + size, LAYOUT["sp_md"])
        self.set_y(self.get_y() + sp)

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: CTA CARD (Call to Action)
    # ═══════════════════════════════════════════════════════════

    def cta_card(self, title, lines, contact_lines=None):
        """
        Card premium para CTA / oferta de servicios.
        title: titulo del card
        lines: lista de strings (entregables / descripcion)
        contact_lines: lista de strings para firma/contacto
        """
        ml = LAYOUT["margin_left"]
        cw = LAYOUT["content_w"]
        y = self.get_y()

        # Estimar alto
        box_h = 16 + len(lines) * 5.5
        if contact_lines:
            box_h += 6 + len(contact_lines) * 4.5

        # Fondo navy
        self._set_color("navy", "fill")
        self.rect(ml, y, cw, box_h, "F")

        # Borde dorado
        self._set_color("gold", "draw")
        self.set_line_width(0.8)
        self.rect(ml, y, cw, box_h, "D")
        self.set_line_width(0.2)

        # Titulo
        self._set_font("h3")
        self._set_color("gold", "text")
        self.set_xy(ml + 8, y + 5)
        self.cell(cw - 16, 7, _s(title), align="C")

        # Lineas
        self._set_font("body")
        self._set_color("white", "text")
        ly = y + 14
        for line in lines:
            self.set_xy(ml + 10, ly)
            self.cell(cw - 20, 5, _s(line), align="L")
            ly += 5.5

        # Contacto
        if contact_lines:
            ly += 3
            self._set_color("gold", "draw")
            self.line(ml + 30, ly, ml + cw - 30, ly)
            ly += 3
            self._set_font("small")
            self._set_color("gold_light", "text")
            for cl in contact_lines:
                self.set_xy(ml + 8, ly)
                self.cell(cw - 16, 4, _s(cl), align="C")
                ly += 4.5

        self.set_xy(ml, y + box_h + LAYOUT["sp_md"])
        self._set_color("text_primary", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: IMAGE EMBED
    # ═══════════════════════════════════════════════════════════

    def embed_chart(self, img_path, x=None, y=None, w=None, h=None, caption=""):
        """
        Inserta un grafico generado por matplotlib.
        x, y: posicion (default: margen izq, posicion actual)
        w: ancho (default: content_w)
        caption: texto debajo del grafico
        """
        x = x or LAYOUT["margin_left"]
        y = y or self.get_y()
        w = w or LAYOUT["content_w"]

        self.image(img_path, x=x, y=y, w=w, h=h or 0)

        if h:
            self.set_y(y + h)
        else:
            self.set_y(self.get_y())

        if caption:
            self.spacer("xs")
            self._set_font("caption")
            self._set_color("text_muted", "text")
            self.set_x(LAYOUT["margin_left"])
            self.cell(LAYOUT["content_w"], 4, _s(caption), align="C")
            self._set_color("text_primary", "text")

        self.spacer("sm")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: PRICING TIER
    # ═══════════════════════════════════════════════════════════

    def pricing_tier(self, x, y, w, name, price, features, highlighted=False):
        """
        Card de tier de pricing.
        highlighted: si True, usa fondo navy + borde dorado.
        """
        h = 12 + len(features) * 5
        if highlighted:
            self._set_color("navy", "fill")
            self._set_color("gold", "draw")
            self.set_line_width(1.0)
        else:
            self._set_color("bg_card", "fill")
            self._set_color("border", "draw")
            self.set_line_width(0.3)

        self.rect(x, y, w, h, "DF")
        self.set_line_width(0.2)

        # Nombre tier
        self._set_font("body_b")
        tc = "gold" if highlighted else "navy"
        self._set_color(tc, "text")
        self.set_xy(x + 2, y + 2)
        self.cell(w - 4, 5, _s(name), align="C")

        # Precio
        self._set_font("h3")
        self.set_xy(x + 2, y + 7)
        self.cell(w - 4, 6, _s(price), align="C")

        # Features
        self._set_font("caption")
        fc = "white" if highlighted else "text_secondary"
        self._set_color(fc, "text")
        fy = y + 15
        for feat in features:
            self.set_xy(x + 3, fy)
            self.cell(w - 6, 4, _s("- " + feat), align="L")
            fy += 5

        self._set_color("text_primary", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: PAGE WITH HEADER
    # ═══════════════════════════════════════════════════════════

    def add_premium_page(self, title="", subtitle="", detail=""):
        """Agrega pagina con header_bar y footer."""
        self.add_page()
        if title:
            self.header_bar(title, subtitle, detail)

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: BADGE / TAG
    # ═══════════════════════════════════════════════════════════

    def badge(self, x, y, text, style="navy"):
        """Etiqueta pequena redondeada (badge)."""
        self._set_font("caption")
        tw = self.get_string_width(_s(text)) + 5
        h = 5.5

        self._set_color(style, "fill")
        # Rounded rect via lines (fpdf2 limitation)
        self.rect(x, y, tw, h, "F")

        tc = "white" if style in ("navy", "blue", "red", "green") else "text_primary"
        self._set_color(tc, "text")
        self.set_xy(x + 1, y + 0.5)
        self.cell(tw - 2, h - 1, _s(text), align="C")
        self._set_color("text_primary", "text")
        return tw
