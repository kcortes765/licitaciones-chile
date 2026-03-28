"""
Sistema de diseno visual nivel museo para IngenIA Licitaciones.

Filosofia: "Engineered Clarity" — cada pagina es un artefacto de
inteligencia competitiva, no un reporte con graficos pegados.

Clase principal: MuseumPDF(FPDF) con layout engine dinamico.
Cada metodo trackea current_y y retorna la nueva posicion.
NUNCA se hardcodean posiciones Y.

Referencia: autonomo/DESIGN_PHILOSOPHY_INGENIA.md
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
from fpdf import FPDF


# ═══════════════════════════════════════════════════════════════
# PALETA REDUCIDA — 6 colores, sin excepciones
# ═══════════════════════════════════════════════════════════════

PALETTE = {
    "navy":        (15, 27, 45),     # #0F1B2D — territorio, headers, peso visual
    "dark_gray":   (45, 55, 72),     # #2D3748 — texto body principal
    "medium_gray": (107, 123, 141),  # #6B7B8D — texto secundario, captions
    "light_bg":    (232, 236, 240),  # #E8ECF0 — fondos de cards, separadores
    "gold_accent": (184, 134, 11),   # #B8860B — hallazgos clave, max 1-2/pagina
    "white":       (255, 255, 255),  # #FFFFFF — fondo, aire
}

# Legacy COLORS dict — backward compat con pdf_charts.py y generate_pdf_v2.py
COLORS = {
    # Paleta museo (canonical)
    "navy":            PALETTE["navy"],
    "dark_gray":       PALETTE["dark_gray"],
    "medium_gray":     PALETTE["medium_gray"],
    "light_bg":        PALETTE["light_bg"],
    "gold_accent":     PALETTE["gold_accent"],
    "white":           PALETTE["white"],

    # Legacy aliases (usados por pdf_charts.py hasta rewrite feature 3)
    "navy_light":      (30, 48, 80),
    "blue":            (41, 98, 155),
    "blue_light":      (66, 133, 183),
    "gold":            PALETTE["gold_accent"],
    "gold_light":      (218, 190, 130),
    "copper":          (176, 124, 67),
    "green":           (39, 145, 76),
    "green_light":     (232, 245, 233),
    "red":             (192, 44, 56),
    "red_light":       (253, 237, 237),
    "amber":           (214, 158, 46),
    "amber_light":     (255, 248, 225),
    "text_primary":    PALETTE["dark_gray"],
    "text_secondary":  PALETTE["medium_gray"],
    "text_muted":      (153, 163, 173),
    "border":          (210, 215, 220),
    "border_light":    PALETTE["light_bg"],
    "bg_light":        PALETTE["light_bg"],
    "bg_card":         (250, 251, 252),
}

# Colores para matplotlib (0-1 range)
MCOLORS = {k: tuple(c / 255 for c in v) for k, v in COLORS.items()}


# ═══════════════════════════════════════════════════════════════
# LAYOUT CONSTANTS
# ═══════════════════════════════════════════════════════════════

LAYOUT = {
    # Pagina A4
    "page_w":        210,
    "page_h":        297,

    # Margenes museo (generosos)
    "margin_left":   25,
    "margin_right":  20,
    "margin_top":    25,
    "margin_bottom": 22,

    # Area util
    "content_w":     165,   # 210 - 25 - 20

    # Spacing vertical (museo)
    "section_gap":   12,
    "element_gap":   6,
    "text_gap":      3,

    # Header
    "header_h":      14,

    # Legacy keys (backward compat)
    "sp_xs":         2,
    "sp_sm":         4,
    "sp_md":         6,
    "sp_lg":         12,
    "sp_xl":         18,
    "sp_section":    12,
    "col_full":      165,
    "col_gutter":    6,
    "footer_y":      275,   # 297 - 22
}


# ═══════════════════════════════════════════════════════════════
# TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════

TYPOGRAPHY = {
    "h1":           {"family": "Helvetica", "style": "B",  "size": 20},
    "h2":           {"family": "Helvetica", "style": "B",  "size": 14},
    "h3":           {"family": "Helvetica", "style": "B",  "size": 12},
    "body":         {"family": "Helvetica", "style": "",   "size": 9},
    "body_b":       {"family": "Helvetica", "style": "B",  "size": 9},
    "small":        {"family": "Helvetica", "style": "",   "size": 8},
    "caption":      {"family": "Helvetica", "style": "",   "size": 7},
    "metric":       {"family": "Helvetica", "style": "B",  "size": 28},
    "metric_label": {"family": "Helvetica", "style": "",   "size": 8},
    "metric_sub":   {"family": "Helvetica", "style": "",   "size": 7},
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _s(text):
    """Sanitiza texto para fpdf2 (compatible Latin-1)."""
    if pd.isna(text) or text is None:
        return ""
    text = str(text)
    replacements = {
        "\u2013": "-",   "\u2014": "-",   "\u2018": "'",
        "\u2019": "'",   "\u201c": '"',   "\u201d": '"',
        "\u2026": "...", "\u2022": "-",   "\u00a0": " ",
        "\ufffd": "o",
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
    return "${:,.0f}".format(a).replace(",", ".")


def _pct(value):
    """Formatea como porcentaje."""
    if pd.isna(value):
        return "N/A"
    return "{:.1f}%".format(float(value) * 100)


# ═══════════════════════════════════════════════════════════════
# MUSEUM PDF — Layout Engine con Y dinamico
# ═══════════════════════════════════════════════════════════════

class MuseumPDF(FPDF):
    """
    PDF nivel museo con layout engine dinamico.

    Principios:
    - Cada metodo renderiza un componente y retorna la nueva Y.
    - self._y trackea la posicion vertical actual. NUNCA hardcodear.
    - needs_new_page(h) agrega pagina si el contenido no cabe.
    - Max 2 colores por componente. Max 4 por pagina.
    - 30% del espacio vertical = aire intencional.
    """

    # Dimensiones de pagina
    LEFT = 25
    RIGHT = 20
    TOP = 25
    BOTTOM = 22
    CONTENT_W = 165   # 210 - 25 - 20
    PAGE_W = 210
    PAGE_H = 297

    # Spacing
    SECTION_GAP = 12
    ELEMENT_GAP = 6
    TEXT_GAP = 3

    def __init__(self, orientation="P", unit="mm", format="A4"):
        super().__init__(orientation=orientation, unit=unit, format=format)
        self.set_auto_page_break(auto=False)
        self.set_margins(self.LEFT, 10, self.RIGHT)
        self._y = self.TOP
        self._page_count = 0
        self._company_name = ""
        self._report_title = ""

    # ─── Context ───

    def set_context(self, company_name="", report_title="Diagnostico Competitivo"):
        self._company_name = _s(company_name)
        self._report_title = _s(report_title)

    # ─── Layout engine ───

    @property
    def usable_bottom(self):
        """Y maxima antes del footer zone."""
        return self.PAGE_H - self.BOTTOM

    def needs_new_page(self, required_height):
        """Agrega pagina si el contenido no cabe. Retorna self._y."""
        if self._y + required_height > self.usable_bottom:
            self.add_page()
        return self._y

    def add_page(self, orientation="", format="", same=False):
        """Override: resetea _y al agregar pagina."""
        super().add_page(orientation, format, same)
        self._page_count += 1
        self._y = self.TOP

    def advance(self, mm):
        """Avanza _y por mm. Retorna nueva _y."""
        self._y += mm
        return self._y

    # ─── Internal helpers ───

    def _font(self, style_key):
        """Aplica estilo tipografico."""
        t = TYPOGRAPHY[style_key]
        self.set_font(t["family"], t["style"], t["size"])

    def _color(self, palette_key, kind="text"):
        """Aplica color de la paleta. kind: text/fill/draw."""
        r, g, b = PALETTE.get(palette_key, COLORS.get(palette_key, (0, 0, 0)))
        if kind == "text":
            self.set_text_color(r, g, b)
        elif kind == "fill":
            self.set_fill_color(r, g, b)
        elif kind == "draw":
            self.set_draw_color(r, g, b)

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: PAGE HEADER
    # Barra navy 14mm con titulo y subtitulo
    # Colores: navy + white (2)
    # ═══════════════════════════════════════════════════════════

    def page_header(self, title, subtitle=""):
        """Barra navy 14mm en top de pagina. Retorna nueva _y."""
        h = LAYOUT["header_h"]

        # Fondo navy full-width
        self._color("navy", "fill")
        self.rect(0, 0, self.PAGE_W, h, "F")

        # Titulo left-aligned
        self._font("h1")
        self._color("white", "text")
        self.set_xy(self.LEFT, 1.5)
        self.cell(self.CONTENT_W * 0.65, 6, _s(title), align="L")

        # Subtitulo right-aligned
        if subtitle:
            self._font("small")
            self.set_xy(self.LEFT, 1.5)
            self.cell(self.CONTENT_W, 6, _s(subtitle), align="R")

        # Branding
        self._font("caption")
        self.set_xy(self.LEFT, 7.5)
        self.cell(self.CONTENT_W, 5, "IngenIA Licitaciones", align="R")

        self._y = h + self.SECTION_GAP
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: METRIC ROW
    # Cards con numeros grandes, gap 4mm
    # Colores: navy + light_bg (2)
    # ═══════════════════════════════════════════════════════════

    def metric_row(self, metrics):
        """
        Fila de metric cards.
        metrics: lista de dicts {value, label, subtext?}
        Retorna nueva _y.
        """
        n = len(metrics)
        if n == 0:
            return self._y

        card_h = 25
        self.needs_new_page(card_h)
        gap = 4
        card_w = (self.CONTENT_W - gap * (n - 1)) / n
        x = self.LEFT

        for m in metrics:
            # Card background
            self._color("light_bg", "fill")
            self.rect(x, self._y, card_w, card_h, "F")

            # Borde superior navy fino
            self._color("navy", "draw")
            self.set_line_width(0.8)
            self.line(x + 1, self._y, x + card_w - 1, self._y)
            self.set_line_width(0.2)

            # Valor grande
            self._font("metric")
            self._color("navy", "text")
            self.set_xy(x, self._y + 2)
            self.cell(card_w, 10, _s(str(m["value"])), align="C")

            # Label
            self._font("metric_label")
            self._color("medium_gray", "text")
            self.set_xy(x, self._y + 13)
            self.cell(card_w, 4, _s(m["label"]), align="C")

            # Subtext
            if m.get("subtext"):
                self._font("metric_sub")
                self.set_xy(x, self._y + 18)
                self.cell(card_w, 4, _s(m["subtext"]), align="C")

            x += card_w + gap

        self._y += card_h + self.ELEMENT_GAP
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: SECTION HEADING
    # Numero en circulo + titulo. SIN linea decorativa.
    # Colores: navy + medium_gray (2)
    # ═══════════════════════════════════════════════════════════

    def section_heading(self, number, title, subtitle=""):
        """Titulo de seccion con numero en circulo. Retorna nueva _y."""
        heading_h = 12 if subtitle else 9
        self.needs_new_page(heading_h + 4)

        circle_d = 7
        # Circulo navy
        self._color("navy", "fill")
        self.ellipse(self.LEFT, self._y, circle_d, circle_d, "F")

        # Numero dentro del circulo
        self.set_font("Helvetica", "B", 9)
        self._color("white", "text")
        self.set_xy(self.LEFT, self._y + 0.5)
        self.cell(circle_d, circle_d - 1, str(number), align="C")

        # Titulo
        self._font("h2")
        self._color("navy", "text")
        self.set_xy(self.LEFT + circle_d + 3, self._y - 0.5)
        self.cell(self.CONTENT_W - circle_d - 3, 8, _s(title), align="L")

        # Subtitulo opcional
        if subtitle:
            self._font("small")
            self._color("medium_gray", "text")
            self.set_xy(self.LEFT + circle_d + 3, self._y + 7.5)
            self.cell(self.CONTENT_W - circle_d - 3, 5, _s(subtitle), align="L")

        self._y += heading_h + self.TEXT_GAP
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: BODY TEXT
    # Texto con line_height 5.5mm. Max 6 lineas por bloque.
    # Colores: dark_gray (1)
    # ═══════════════════════════════════════════════════════════

    def body_text(self, text, max_lines=6, width=None, style="body",
                  color="dark_gray", line_height=5.5):
        """Bloque de texto. Trunca a max_lines. Retorna nueva _y."""
        w = width or self.CONTENT_W
        safe = _s(text)

        # Truncar a max_lines
        lines = safe.split("\n")
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        safe = "\n".join(lines)

        # Estimar altura para needs_new_page
        self._font(style)
        char_per_line = max(1, int(w / (self.get_string_width("x") or 2)))
        estimated_lines = 0
        for line in lines:
            estimated_lines += max(1, -(-len(line) // char_per_line))  # ceil div
        estimated_lines = min(estimated_lines, max_lines)
        est_h = estimated_lines * line_height + 2

        self.needs_new_page(est_h)

        self._font(style)
        self._color(color, "text")
        self.set_xy(self.LEFT, self._y)
        y_before = self._y
        self.multi_cell(w, line_height, safe, align="L")
        rendered_h = self.get_y() - y_before

        self._y = y_before + rendered_h + self.TEXT_GAP
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: CHART BLOCK
    # Chart centrado con caption debajo. 6mm padding top/bottom.
    # Colores: medium_gray para caption (1)
    # ═══════════════════════════════════════════════════════════

    def chart_block(self, img_path, caption="", width_mm=None):
        """Inserta chart con caption. Retorna nueva _y."""
        w = width_mm or self.CONTENT_W
        padding = 6

        # Centrar si menor que content_w
        x = self.LEFT + (self.CONTENT_W - w) / 2

        self._y += padding
        self.needs_new_page(60)  # estimate min height

        self.image(img_path, x=x, y=self._y, w=w)
        # fpdf updates get_y after image
        img_bottom = self.get_y()
        self._y = img_bottom

        if caption:
            self._y += 2
            self._font("caption")
            self._color("medium_gray", "text")
            self.set_xy(self.LEFT, self._y)
            self.cell(self.CONTENT_W, 4, _s(caption), align="C")
            self._y += 4

        self._y += padding
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: CALLOUT
    # Borde izquierdo 3mm + texto. SIN fondo de color.
    # Colores: gold_accent border + dark_gray text (2)
    # ═══════════════════════════════════════════════════════════

    def callout(self, text, style="gold"):
        """Callout con borde izquierdo. Retorna nueva _y."""
        safe = _s(text)
        border_w = 3
        pad_left = 6
        text_w = self.CONTENT_W - border_w - pad_left

        # Estimar altura
        self._font("body")
        char_per_line = max(1, int(text_w / (self.get_string_width("x") or 2)))
        n_lines = max(1, -(-len(safe) // char_per_line))
        box_h = max(12, n_lines * 5.5 + 4)

        self.needs_new_page(box_h)

        # Borde izquierdo
        border_color = "gold_accent" if style == "gold" else "navy"
        self._color(border_color, "draw")
        self.set_line_width(border_w)
        self.line(
            self.LEFT + border_w / 2, self._y,
            self.LEFT + border_w / 2, self._y + box_h,
        )
        self.set_line_width(0.2)

        # Texto
        self._font("body")
        self._color("dark_gray", "text")
        self.set_xy(self.LEFT + border_w + pad_left, self._y + 2)
        self.multi_cell(text_w, 5.5, safe, align="L")
        actual_bottom = self.get_y() + 2

        self._y = max(self._y + box_h, actual_bottom) + self.ELEMENT_GAP
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: DATA TABLE
    # Tabla limpia. Solo header separator y bottom line.
    # Colores: navy header + dark_gray text (2)
    # ═══════════════════════════════════════════════════════════

    def data_table(self, headers, rows, col_widths=None, bold_col=None):
        """
        Tabla limpia sin bordes horizontales entre filas.
        bold_col: indice de columna a mostrar en bold (0-based).
        Retorna nueva _y.
        """
        n_cols = len(headers)
        if col_widths is None:
            col_widths = [self.CONTENT_W / n_cols] * n_cols

        header_h = 7
        row_h = 6.5
        total_h = header_h + row_h * len(rows) + 2
        self.needs_new_page(total_h)

        y = self._y

        # Header text (navy bold, no background fill)
        self._font("small")
        self._color("navy", "text")
        x = self.LEFT
        for hdr, w in zip(headers, col_widths):
            self.set_font("Helvetica", "B", 8)
            self.set_xy(x + 1, y + 1)
            self.cell(w - 2, header_h - 2, _s(hdr), align="C")
            x += w

        # Header separator line
        y += header_h
        self._color("navy", "draw")
        self.set_line_width(0.4)
        self.line(self.LEFT, y, self.LEFT + sum(col_widths), y)
        self.set_line_width(0.2)

        # Rows — no borders between rows
        for row in rows:
            x = self.LEFT
            for col_idx, (cell, w) in enumerate(zip(row, col_widths)):
                is_bold = (col_idx == bold_col) if bold_col is not None else False
                if is_bold:
                    self.set_font("Helvetica", "B", 8)
                else:
                    self._font("small")
                self._color("dark_gray", "text")
                self.set_xy(x + 1, y + 0.5)
                align = "L" if col_idx == 0 else "C"
                self.cell(w - 2, row_h, _s(str(cell)), align=align)
                x += w
            y += row_h

        # Bottom line
        self._color("light_bg", "draw")
        self.set_line_width(0.3)
        self.line(self.LEFT, y, self.LEFT + sum(col_widths), y)
        self.set_line_width(0.2)

        self._y = y + self.ELEMENT_GAP
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: PRICING CARDS
    # 3 cards lado a lado. Gap 4mm. Card central highlight.
    # Colores: navy + gold_accent (2)
    # ═══════════════════════════════════════════════════════════

    def pricing_cards(self, tiers):
        """
        Pricing cards en linea.
        tiers: lista de dicts {name, price, features:[], highlighted?}
        Retorna nueva _y.
        """
        n = len(tiers)
        if n == 0:
            return self._y

        gap = 4
        card_w = (self.CONTENT_W - gap * (n - 1)) / n
        max_features = max(len(t.get("features", [])) for t in tiers)
        card_h = min(55, 20 + max_features * 5)

        self.needs_new_page(card_h)

        x = self.LEFT
        for tier in tiers:
            highlighted = tier.get("highlighted", False)

            if highlighted:
                # Gold border, no fill
                self._color("white", "fill")
                self._color("gold_accent", "draw")
                self.set_line_width(1.0)
                self.rect(x, self._y, card_w, card_h, "DF")
                self.set_line_width(0.2)
            else:
                # Light bg, thin border
                self._color("light_bg", "fill")
                self._color("light_bg", "draw")
                self.set_line_width(0.3)
                self.rect(x, self._y, card_w, card_h, "DF")
                self.set_line_width(0.2)

            # Tier name
            self.set_font("Helvetica", "B", 10)
            self._color("navy", "text")
            self.set_xy(x + 2, self._y + 2)
            self.cell(card_w - 4, 5, _s(tier["name"]), align="C")

            # Price
            self.set_font("Helvetica", "B", 12)
            color = "gold_accent" if highlighted else "navy"
            self._color(color, "text")
            self.set_xy(x + 2, self._y + 8)
            self.cell(card_w - 4, 6, _s(tier["price"]), align="C")

            # Features
            self._font("small")
            self._color("dark_gray", "text")
            fy = self._y + 16
            for feat in tier.get("features", [])[:4]:
                self.set_xy(x + 3, fy)
                self.cell(card_w - 6, 4, _s("- " + feat), align="L")
                fy += 5

            x += card_w + gap

        self._y += card_h + self.ELEMENT_GAP
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: CTA BLOCK
    # Card navy con texto centrado.
    # Colores: navy + white (2)
    # ═══════════════════════════════════════════════════════════

    def cta_block(self, text, contact=""):
        """Card navy con CTA. Retorna nueva _y."""
        lines = [l for l in text.split("\n") if l.strip()]
        contact_lines = [l for l in contact.split("\n") if l.strip()] if contact else []
        box_h = 12 + len(lines) * 6 + len(contact_lines) * 5

        self.needs_new_page(box_h)

        # Fondo navy
        self._color("navy", "fill")
        self.rect(self.LEFT, self._y, self.CONTENT_W, box_h, "F")

        # Texto principal
        self.set_font("Helvetica", "B", 11)
        self._color("white", "text")
        ly = self._y + 5
        for line in lines:
            self.set_xy(self.LEFT, ly)
            self.cell(self.CONTENT_W, 5, _s(line), align="C")
            ly += 6

        # Contacto
        if contact_lines:
            ly += 2
            self._font("body")
            self._color("white", "text")
            for cl in contact_lines:
                self.set_xy(self.LEFT, ly)
                self.cell(self.CONTENT_W, 4, _s(cl), align="C")
                ly += 5

        self._y += box_h + self.ELEMENT_GAP
        self._color("dark_gray", "text")
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: FOOTER
    # Linea fina + 3 textos. Posicion fija en bottom zone.
    # Colores: medium_gray (1)
    # ═══════════════════════════════════════════════════════════

    def footer_block(self, page_num=None, total_pages=None):
        """Footer en bottom zone. No modifica _y."""
        y = self.PAGE_H - self.BOTTOM + 4

        # Linea fina
        self._color("light_bg", "draw")
        self.set_line_width(0.2)
        self.line(self.LEFT, y, self.LEFT + self.CONTENT_W, y)

        y += 2
        self._font("caption")
        self._color("medium_gray", "text")

        # Izquierda: marca
        self.set_xy(self.LEFT, y)
        self.cell(self.CONTENT_W / 3, 4, "IngenIA Licitaciones", align="L")

        # Centro: confidencial
        self.set_xy(self.LEFT + self.CONTENT_W / 3, y)
        self.cell(self.CONTENT_W / 3, 4, "Documento confidencial", align="C")

        # Derecha: pagina
        if page_num is not None:
            page_text = "Pag. {}".format(page_num)
            if total_pages:
                page_text += " de {}".format(total_pages)
            self.set_xy(self.LEFT + 2 * self.CONTENT_W / 3, y)
            self.cell(self.CONTENT_W / 3, 4, page_text, align="R")

        self._color("dark_gray", "text")

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: DIVIDER
    # Linea horizontal fina.
    # ═══════════════════════════════════════════════════════════

    def divider(self, style="light"):
        """Linea horizontal. Retorna nueva _y."""
        self._y += 2
        if style == "gold":
            self._color("gold_accent", "draw")
            self.set_line_width(0.3)
        elif style == "navy":
            self._color("navy", "draw")
            self.set_line_width(0.3)
        else:
            self._color("light_bg", "draw")
            self.set_line_width(0.2)

        self.line(self.LEFT, self._y, self.LEFT + self.CONTENT_W, self._y)
        self.set_line_width(0.2)
        self._y += 4
        return self._y

    # ═══════════════════════════════════════════════════════════
    # COMPONENTE: SPACER
    # Aire intencional.
    # ═══════════════════════════════════════════════════════════

    def spacer(self, mm=None, size="md"):
        """Espacio vertical. mm override o size preset. Retorna nueva _y."""
        if mm is not None:
            self._y += mm
        else:
            sizes = {"xs": 2, "sm": 4, "md": 6, "lg": 12, "xl": 18}
            self._y += sizes.get(size, 6)
        return self._y

    # ═══════════════════════════════════════════════════════════
    # LEGACY COMPAT — metodos usados por generate_pdf_v2.py
    # hasta rewrite de features 4-8
    # ═══════════════════════════════════════════════════════════

    def header_bar(self, title, subtitle="", detail=""):
        """Legacy compat: redirige a page_header."""
        return self.page_header(title, subtitle or detail)

    def section_title(self, number, title, subtitle=""):
        """Legacy compat: redirige a section_heading."""
        return self.section_heading(number, title, subtitle)

    def metric_card(self, x, y, value, label, subtext="", accent="navy"):
        """Legacy compat: single metric card at fixed position."""
        card_w = 33.6
        card_h = 25

        self._color("light_bg", "fill")
        self.rect(x, y, card_w, card_h, "F")

        self._color("navy", "draw")
        self.set_line_width(0.8)
        self.line(x + 1, y, x + card_w - 1, y)
        self.set_line_width(0.2)

        self._font("metric")
        self._color("navy", "text")
        self.set_xy(x, y + 2)
        self.cell(card_w, 10, _s(str(value)), align="C")

        self._font("metric_label")
        self._color("medium_gray", "text")
        self.set_xy(x, y + 13)
        self.cell(card_w, 4, _s(label), align="C")

        if subtext:
            self._font("metric_sub")
            self.set_xy(x, y + 18)
            self.cell(card_w, 4, _s(subtext), align="C")

        self._color("dark_gray", "text")

    def metric_cards_row(self, y, cards):
        """Legacy compat: metric cards at fixed y."""
        x = self.LEFT
        w = 33.6
        gap = 3
        for card in cards:
            self.metric_card(
                x, y,
                value=card["value"],
                label=card["label"],
                subtext=card.get("subtext", ""),
                accent=card.get("accent", "navy"),
            )
            x += w + gap

    def insight_callout(self, text, style="info", icon_text=None):
        """Legacy compat: redirige a callout."""
        return self.callout(text, style="gold")

    def comparison_table(self, headers, rows, col_widths=None, highlight_col=0):
        """Legacy compat: redirige a data_table."""
        bold_col = highlight_col - 1 if highlight_col > 0 else None
        return self.data_table(headers, rows, col_widths, bold_col)

    def simple_table(self, headers, rows, col_widths=None):
        """Legacy compat: redirige a data_table."""
        return self.data_table(headers, rows, col_widths)

    def professional_footer(self, page_num=None, total_pages=None):
        """Legacy compat: redirige a footer_block."""
        return self.footer_block(page_num, total_pages)

    def text_block(self, text, style="body", color="dark_gray",
                   width=None, align="L", line_height=5.5):
        """Legacy compat: redirige a body_text."""
        return self.body_text(text, width=width, style=style,
                              color=color, line_height=line_height)

    def embed_chart(self, img_path, x=None, y=None, w=None, h=None, caption=""):
        """Legacy compat: redirige a chart_block."""
        if y is not None:
            self._y = y
        return self.chart_block(img_path, caption, width_mm=w)

    def cta_card(self, title, lines, contact_lines=None):
        """Legacy compat: redirige a cta_block."""
        text = title + "\n" + "\n".join(lines)
        contact = "\n".join(contact_lines) if contact_lines else ""
        return self.cta_block(text, contact)

    def badge(self, x, y, text, style="navy"):
        """Legacy compat: badge at position."""
        self._font("caption")
        tw = self.get_string_width(_s(text)) + 5
        h = 5.5
        self._color("navy", "fill")
        self.rect(x, y, tw, h, "F")
        self._color("white", "text")
        self.set_xy(x + 1, y + 0.5)
        self.cell(tw - 2, h - 1, _s(text), align="C")
        self._color("dark_gray", "text")
        return tw

    def pricing_tier(self, x, y, w, name, price, features, highlighted=False):
        """Legacy compat: single pricing tier."""
        h = 12 + len(features) * 5
        if highlighted:
            self._color("navy", "fill")
            self._color("gold_accent", "draw")
            self.set_line_width(1.0)
        else:
            self._color("light_bg", "fill")
            self._color("light_bg", "draw")
            self.set_line_width(0.3)
        self.rect(x, y, w, h, "DF")
        self.set_line_width(0.2)

        self.set_font("Helvetica", "B", 10)
        tc = "gold_accent" if highlighted else "navy"
        self._color(tc, "text")
        self.set_xy(x + 2, y + 2)
        self.cell(w - 4, 5, _s(name), align="C")

        self._font("h3")
        self.set_xy(x + 2, y + 7)
        self.cell(w - 4, 6, _s(price), align="C")

        self._font("caption")
        fc = "white" if highlighted else "medium_gray"
        self._color(fc, "text")
        fy = y + 15
        for feat in features:
            self.set_xy(x + 3, fy)
            self.cell(w - 6, 4, _s("- " + feat), align="L")
            fy += 5

        self._color("dark_gray", "text")

    def add_premium_page(self, title="", subtitle="", detail=""):
        """Legacy compat: add page + header."""
        self.add_page()
        if title:
            self.page_header(title, subtitle or detail)

    def _set_font(self, style_key):
        """Legacy compat."""
        self._font(style_key)

    def _set_color(self, color_key, kind="text"):
        """Legacy compat."""
        self._color(color_key, kind)


# Backward compat alias
PremiumPDF = MuseumPDF
