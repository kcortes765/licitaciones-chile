"""
pdf_engine.py — Motor de layout MATEMÁTICO para fpdf2.

Cada elemento tiene altura pre-calculada. La suma de alturas por página
DEBE ser <= content_height (257mm para A4 con márgenes 20/20).
Si no cabe, se salta a nueva página. NUNCA se corta ni se solapa.

Parte del sistema Engineered Clarity — IngenIA Licitaciones.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from fpdf import FPDF

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de altura pre-calculadas (mm)
# ---------------------------------------------------------------------------
HEADER_H = 40
METRIC_ROW_H = 30
SECTION_HEADING_H = 15
BODY_LINE_H = 5
TABLE_ROW_H = 7
CHART_H = 65
CALLOUT_H = 20
SPACER_SM = 4
SPACER_MD = 8
SPACER_LG = 12
FOOTER_H = 10
PRICING_ROW_H = 55
CTA_H = 35

# Colores canónicos
COLOR_NAVY = (0x1B, 0x2A, 0x4A)   # #1B2A4A
COLOR_GOLD = (0xB8, 0x86, 0x0B)   # #B8860B
COLOR_GRAY = (0xAA, 0xAA, 0xAA)   # #AAAAAA
COLOR_WHITE = (0xFF, 0xFF, 0xFF)
COLOR_DARK_GRAY = (0x2D, 0x37, 0x48)
COLOR_MID_GRAY = (0x6B, 0x7B, 0x8D)
COLOR_LIGHT_GRAY = (0xE8, 0xEC, 0xF0)


# Tipo para funciones de renderizado: (pdf, x, y, w, h) -> None
RenderFn = Callable[[FPDF, float, float, float, float], None]


@dataclass
class _Element:
    """Elemento interno con altura y función de renderizado."""
    height_mm: float
    render_fn: RenderFn
    label: str = ""


@dataclass
class _ColumnSpec:
    """Especificación de una columna."""
    width_ratio: float
    render_fn: RenderFn
    height_mm: float


class LayoutOverflowError(Exception):
    """Raised when elements exceed available page height."""
    pass


class PageLayout:
    """Motor de layout matemático para A4 con fpdf2.

    Gestiona posicionamiento vertical de forma determinista.
    Cada elemento declara su altura. El motor verifica que cabe
    antes de renderizar. Si no cabe, salta a nueva página.
    """

    # Dimensiones A4 (mm)
    PAGE_W = 210.0
    PAGE_H = 297.0

    # Márgenes (mm)
    MARGIN_TOP = 20.0
    MARGIN_BOTTOM = 20.0
    MARGIN_LEFT = 20.0
    MARGIN_RIGHT = 15.0

    # Área útil calculada
    CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT   # 175mm
    CONTENT_H = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM    # 257mm

    # Gap default entre elementos (mm)
    DEFAULT_GAP = 0.0  # Gaps se agregan explícitamente como spacers

    def __init__(self, pdf: Optional[FPDF] = None):
        if pdf is None:
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.set_auto_page_break(auto=False)
            pdf.set_margins(self.MARGIN_LEFT, self.MARGIN_TOP, self.MARGIN_RIGHT)
        else:
            pdf.set_auto_page_break(auto=False)

        self.pdf = pdf
        self._current_y = self.MARGIN_TOP
        self._page_elements: List[_Element] = []
        self._page_count = 0
        self._footer_fn: Optional[RenderFn] = None
        self._footer_h: float = 0.0

    # -- Propiedades ---------------------------------------------------------

    @property
    def content_width(self) -> float:
        return self.CONTENT_W

    @property
    def content_height(self) -> float:
        return self.CONTENT_H

    @property
    def current_y(self) -> float:
        return self._current_y

    @property
    def remaining_height(self) -> float:
        """Espacio vertical disponible en la página actual."""
        footer_reserve = self._footer_h if self._footer_fn else 0.0
        return (self.PAGE_H - self.MARGIN_BOTTOM - footer_reserve) - self._current_y

    @property
    def page_count(self) -> int:
        return self._page_count

    # -- Control de páginas --------------------------------------------------

    def new_page(self) -> None:
        """Inicia una nueva página. Renderiza footer de la anterior si existe."""
        if self._page_count > 0 and self._footer_fn:
            footer_y = self.PAGE_H - self.MARGIN_BOTTOM - self._footer_h
            self._footer_fn(
                self.pdf,
                self.MARGIN_LEFT,
                footer_y,
                self.CONTENT_W,
                self._footer_h,
            )
        self.pdf.add_page()
        self._page_count += 1
        self._current_y = self.MARGIN_TOP
        self._page_elements = []

    def set_footer(self, render_fn: RenderFn, height_mm: float = FOOTER_H) -> None:
        """Registra una función de footer que se renderiza al final de cada página."""
        self._footer_fn = render_fn
        self._footer_h = height_mm

    def finalize(self) -> None:
        """Renderiza el footer de la última página."""
        if self._page_count > 0 and self._footer_fn:
            footer_y = self.PAGE_H - self.MARGIN_BOTTOM - self._footer_h
            self._footer_fn(
                self.pdf,
                self.MARGIN_LEFT,
                footer_y,
                self.CONTENT_W,
                self._footer_h,
            )

    # -- Agregar elementos ---------------------------------------------------

    def _fits(self, height_mm: float) -> bool:
        """Verifica si un elemento cabe en la página actual."""
        footer_reserve = self._footer_h if self._footer_fn else 0.0
        limit = self.PAGE_H - self.MARGIN_BOTTOM - footer_reserve
        return (self._current_y + height_mm) <= limit + 0.01  # tolerancia fp

    def add_element(
        self,
        height_mm: float,
        render_fn: RenderFn,
        label: str = "",
        allow_page_break: bool = True,
    ) -> bool:
        """Agrega un elemento al layout.

        Args:
            height_mm: Altura fija del elemento en mm.
            render_fn: Función (pdf, x, y, w, h) -> None que renderiza.
            label: Etiqueta para logging/debug.
            allow_page_break: Si True, salta a nueva página si no cabe.
                              Si False, omite el elemento si no cabe.

        Returns:
            True si el elemento se renderizó, False si se omitió.
        """
        if not self._fits(height_mm):
            if allow_page_break:
                self.new_page()
            else:
                logger.warning(
                    "Elemento '%s' (%.1fmm) omitido — no cabe (%.1fmm disponible)",
                    label, height_mm, self.remaining_height,
                )
                return False

        # Renderizar
        render_fn(
            self.pdf,
            self.MARGIN_LEFT,
            self._current_y,
            self.CONTENT_W,
            height_mm,
        )

        elem = _Element(height_mm=height_mm, render_fn=render_fn, label=label)
        self._page_elements.append(elem)
        self._current_y += height_mm

        return True

    def add_spacer(self, height_mm: float = SPACER_MD) -> bool:
        """Agrega un espaciador vacío."""
        return self.add_element(
            height_mm,
            lambda pdf, x, y, w, h: None,  # no-op
            label=f"spacer({height_mm})",
            allow_page_break=False,  # spacers se omiten si no caben
        )

    def add_columns(
        self,
        col_specs: List[Tuple[float, RenderFn, float]],
        gap_mm: float = 6.0,
        label: str = "",
        allow_page_break: bool = True,
    ) -> bool:
        """Renderiza columnas lado a lado.

        Args:
            col_specs: Lista de (width_ratio, render_fn, height_mm).
                       Los ratios deben sumar ~1.0.
            gap_mm: Espacio entre columnas en mm.
            label: Etiqueta para debug.
            allow_page_break: Si True, salta de página si no cabe.

        Returns:
            True si se renderizó, False si se omitió.
        """
        max_h = max(spec[2] for spec in col_specs)

        if not self._fits(max_h):
            if allow_page_break:
                self.new_page()
            else:
                logger.warning(
                    "Columnas '%s' (%.1fmm) omitidas — no cabe", label, max_h
                )
                return False

        total_gaps = gap_mm * (len(col_specs) - 1)
        usable_w = self.CONTENT_W - total_gaps
        current_x = self.MARGIN_LEFT

        for ratio, render_fn, col_h in col_specs:
            col_w = usable_w * ratio
            render_fn(self.pdf, current_x, self._current_y, col_w, col_h)
            current_x += col_w + gap_mm

        self._page_elements.append(
            _Element(height_mm=max_h, render_fn=lambda *a: None, label=label)
        )
        self._current_y += max_h
        return True

    # -- Validación ----------------------------------------------------------

    @staticmethod
    def validate_page(
        elements_with_heights: List[Tuple[str, float]],
        max_height: float = None,
    ) -> None:
        """Valida que una lista de elementos cabe en una página.

        Args:
            elements_with_heights: Lista de (label, height_mm).
            max_height: Altura máxima disponible. Default: CONTENT_H (257mm).

        Raises:
            LayoutOverflowError: Si la suma excede el máximo.
        """
        if max_height is None:
            max_height = PageLayout.CONTENT_H

        total = sum(h for _, h in elements_with_heights)

        if total > max_height:
            detail_lines = [f"  {label}: {h:.1f}mm" for label, h in elements_with_heights]
            detail = "\n".join(detail_lines)
            raise LayoutOverflowError(
                f"Overflow: {total:.1f}mm > {max_height:.1f}mm disponible.\n"
                f"Elementos:\n{detail}\n"
                f"Exceso: {total - max_height:.1f}mm"
            )

    @staticmethod
    def validate_page_with_footer(
        elements_with_heights: List[Tuple[str, float]],
        footer_h: float = FOOTER_H,
    ) -> None:
        """Valida incluyendo espacio reservado para footer."""
        max_h = PageLayout.CONTENT_H - footer_h
        PageLayout.validate_page(elements_with_heights, max_height=max_h)

    # -- Utilidades ----------------------------------------------------------

    def page_height_used(self) -> float:
        """Altura total usada por los elementos en la página actual."""
        return sum(e.height_mm for e in self._page_elements)

    def page_height_breakdown(self) -> str:
        """Retorna string con desglose de alturas para debug."""
        lines = []
        total = 0.0
        for e in self._page_elements:
            lines.append(f"  {e.label or '(unnamed)'}: {e.height_mm:.1f}mm")
            total += e.height_mm
        lines.append(f"  TOTAL: {total:.1f}mm / {self.content_height:.1f}mm")
        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Finaliza y guarda el PDF."""
        self.finalize()
        self.pdf.output(path)


# ---------------------------------------------------------------------------
# Test standalone
# ---------------------------------------------------------------------------
def _test():
    """Crea un PDF de prueba con 20 elementos para verificar el engine."""
    import os
    import tempfile

    layout = PageLayout()

    # Footer simple
    def render_footer(pdf, x, y, w, h):
        pdf.set_draw_color(*COLOR_GRAY)
        pdf.line(x, y, x + w, y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*COLOR_MID_GRAY)
        pdf.set_xy(x, y + 2)
        pdf.cell(w, 5, f"IngenIA Licitaciones - Pagina {pdf.page_no()}", align="C")

    layout.set_footer(render_footer, FOOTER_H)

    # Renderizadores de prueba
    def make_box(color, text):
        def _render(pdf, x, y, w, h):
            pdf.set_fill_color(*color)
            pdf.rect(x, y, w, h, "F")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*COLOR_WHITE)
            pdf.set_xy(x + 2, y + h / 2 - 3)
            pdf.cell(w - 4, 6, text, align="L")
        return _render

    # Página 1: elementos normales
    layout.new_page()

    layout.add_element(HEADER_H, make_box(COLOR_NAVY, "Header (40mm)"), "header")
    layout.add_spacer(SPACER_LG)
    layout.add_element(METRIC_ROW_H, make_box(COLOR_DARK_GRAY, "Metrics (30mm)"), "metrics")
    layout.add_spacer(SPACER_MD)
    layout.add_element(SECTION_HEADING_H, make_box(COLOR_MID_GRAY, "Section (15mm)"), "section")
    layout.add_spacer(SPACER_SM)
    layout.add_element(CHART_H, make_box(COLOR_GOLD, "Chart (65mm)"), "chart")
    layout.add_spacer(SPACER_MD)
    layout.add_element(CALLOUT_H, make_box(COLOR_NAVY, "Callout (20mm)"), "callout")

    print(f"Página 1 breakdown:\n{layout.page_height_breakdown()}")

    # Página 2: columns
    layout.new_page()
    layout.add_element(SECTION_HEADING_H, make_box(COLOR_NAVY, "Sección 2"), "section2")
    layout.add_spacer(SPACER_MD)

    layout.add_columns(
        [
            (0.55, make_box(COLOR_GOLD, "Col izq (55%)"), CHART_H),
            (0.45, make_box(COLOR_DARK_GRAY, "Col der (45%)"), CHART_H),
        ],
        label="columns_chart_text",
    )
    layout.add_spacer(SPACER_LG)
    layout.add_columns(
        [
            (0.60, make_box(COLOR_NAVY, "Col 60%"), 70),
            (0.40, make_box(COLOR_MID_GRAY, "Col 40%"), 70),
        ],
        label="columns_2",
    )

    print(f"\nPágina 2 breakdown:\n{layout.page_height_breakdown()}")

    # Página 3: llenar con muchos elementos hasta forzar auto-page
    layout.new_page()
    for i in range(20):
        added = layout.add_element(
            TABLE_ROW_H * 3,  # 21mm cada uno
            make_box(COLOR_DARK_GRAY if i % 2 == 0 else COLOR_MID_GRAY, f"Elem {i+1} (21mm)"),
            label=f"elem_{i+1}",
            allow_page_break=True,
        )
        if added:
            layout.add_spacer(SPACER_SM)

    print(f"\nPágina 3+ breakdown:\n{layout.page_height_breakdown()}")
    print(f"\nTotal páginas: {layout.page_count}")

    # Validar que los page layouts típicos caben
    print("\n--- Validación de layouts típicos ---")

    page_specs = {
        "P1 Portada": [
            ("header", HEADER_H), ("spacer", SPACER_LG), ("metrics", METRIC_ROW_H),
            ("spacer", SPACER_MD), ("body", 35), ("spacer", SPACER_MD),
            ("table", 40),
        ],
        "P2 Desempeño": [
            ("section", SECTION_HEADING_H), ("spacer", SPACER_MD),
            ("columns_gauge", 65), ("spacer", SPACER_MD),
            ("columns_radar", 70), ("spacer", SPACER_MD),
        ],
        "P3 Competitiva": [
            ("section", SECTION_HEADING_H), ("spacer", SPACER_MD),
            ("chart_rivales", 45), ("spacer", SPACER_SM),
            ("body_rival", 20), ("spacer", SPACER_SM),
            ("table_licit", 50), ("spacer", SPACER_SM),
            ("callout", 18), ("spacer", SPACER_SM),
            ("table_comp", 40),
        ],
        "P4 Temporal": [
            ("section", SECTION_HEADING_H), ("spacer", SPACER_MD),
            ("columns_donut", 65), ("spacer", SPACER_MD),
            ("body_regional", 20), ("spacer", SPACER_SM),
            ("body_escala", 15),
        ],
        "P5 Oportunidad": [
            ("section", SECTION_HEADING_H), ("spacer", SPACER_MD),
            ("chart_waterfall", 70), ("spacer", SPACER_MD),
            ("table_escenarios", 35), ("spacer", SPACER_MD),
            ("callout_costo", 18),
        ],
        "P6 Recomendaciones": [
            ("section", SECTION_HEADING_H), ("spacer", SPACER_MD),
            ("body_recs", 80), ("spacer", SPACER_MD),
            ("pricing", PRICING_ROW_H), ("spacer", SPACER_MD),
            ("cta", CTA_H), ("spacer", SPACER_SM),
            ("disclaimer", 10),
        ],
    }

    all_ok = True
    for page_name, elems in page_specs.items():
        total = sum(h for _, h in elems)
        max_avail = PageLayout.CONTENT_H - FOOTER_H  # reservar footer
        status = "OK" if total <= max_avail else "OVERFLOW"
        if status == "OVERFLOW":
            all_ok = False
        print(f"  {page_name}: {total:.0f}mm / {max_avail:.0f}mm [{status}]")

    # Guardar PDF de prueba
    test_dir = tempfile.gettempdir()
    test_path = os.path.join(test_dir, "pdf_engine_test.pdf")
    layout.save(test_path)
    file_size = os.path.getsize(test_path)
    print(f"\nPDF test guardado: {test_path} ({file_size:,} bytes)")
    print(f"Páginas totales: {layout.page_count}")

    assert layout.page_count >= 3, f"Expected >= 3 pages, got {layout.page_count}"
    assert file_size > 1000, f"PDF too small: {file_size} bytes"
    assert all_ok, "Some page layouts overflow!"

    # Validación con validate_page
    try:
        PageLayout.validate_page_with_footer(page_specs["P1 Portada"])
        print("\nvalidate_page: P1 OK")
    except LayoutOverflowError as e:
        print(f"\nvalidate_page: P1 FAILED — {e}")
        raise

    # Test overflow detection
    try:
        PageLayout.validate_page([("huge", 300)])
        print("validate_page: overflow NOT detected (BAD)")
        raise AssertionError("Should have raised LayoutOverflowError")
    except LayoutOverflowError:
        print("validate_page: overflow correctly detected")

    print("\n=== Engine OK ===")


if __name__ == "__main__":
    _test()
