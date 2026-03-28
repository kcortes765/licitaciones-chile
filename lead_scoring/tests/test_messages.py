"""
Tests exhaustivos para generar_mensajes_v4.py y verificar_mensajes_v2.py.

Cubre: humanizar, limpiar_rival, pct, meses, elegir_insight (10 tipos),
generar_mensaje, generar_wsp_link, términos prohibidos, y verificación
con datos reales.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Agregar raíz del proyecto al path para importar scripts de la raíz
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generar_mensajes_v4 import (
    humanizar,
    limpiar_rival,
    pct,
    meses,
    elegir_insight,
    generar_mensaje,
    generar_wsp_link,
    INDUSTRY_WR_MEDIAN,
    FIRMA,
)

# Paths para tests con datos reales (definidos localmente para evitar import de conftest)
LEAD_SCORING_DIR = Path(__file__).resolve().parent.parent
FILTERED_DIR = LEAD_SCORING_DIR / "data" / "filtered"
OUTPUT_DIR = LEAD_SCORING_DIR / "data" / "output"
LOSS_ANALYSIS_PATH = OUTPUT_DIR / "loss_analysis.parquet"

# ── Funciones de verificar_mensajes_v2.py (copiadas para evitar ejecución
#    del módulo completo que carga datos y hace I/O a nivel de módulo) ───


def get_rival_aliases(raw_name):
    """Devuelve lista de variantes del nombre del rival para comparación flexible."""
    if not raw_name or raw_name == "nan":
        return []
    aliases = []
    for part in raw_name.split("|"):
        part = part.strip()
        if part:
            aliases.append(part.lower())
    return aliases


def name_matches(candidate, aliases):
    """True si candidate (lower) aparece en algún alias o viceversa."""
    c = candidate.lower().strip()
    for alias in aliases:
        if c in alias or alias in c:
            return True
    return False


# ── Términos prohibidos en mensajes cliente ────────────────────────────
FORBIDDEN_TERMS = [
    "score", "cluster", "ML", "modelo", "pipeline", "algoritmo",
    "ranking", "xgb", "km_score", "lead ideal", "score_total",
    "score_combined",
]


def _make_row(**overrides) -> pd.Series:
    """Crea una fila tipo loss_analysis con defaults sensatos."""
    defaults = {
        "nombre": "CONSTRUCTORA TEST LTDA",
        "win_rate": 0.25,
        "n_LP": 2,
        "total_lost_loss": 3,
        "loss_rate": 0.30,
        "total_bids": 10,
        "total_wins": 3,
        "dias_desde_ultima": 90,
        "top_rival_1_name": "",
        "top_rival_1_count": 0,
        "contacto_nombre": None,
        "telefono_normalizado": "+56912345678",
        "monto_total": 500_000_000,
    }
    defaults.update(overrides)
    return pd.Series(defaults)


# ══════════════════════════════════════════════════════════════════════════
# A. humanizar
# ══════════════════════════════════════════════════════════════════════════

class TestHumanizar:

    def test_title_case_simple(self):
        assert humanizar("CONSTRUCTORA MONTE VIVO") == "Constructora Monte Vivo"

    def test_removes_ltda(self):
        assert humanizar("CONSTRUCTORA MONTE VIVO LIMITADA") == "Constructora Monte Vivo"

    def test_removes_spa(self):
        assert humanizar("GUERCUT SPA") == "Guercut"

    def test_removes_eirl(self):
        assert humanizar("EMPRESA TEST EIRL") == "Empresa Test"

    def test_removes_eirl_dotted(self):
        assert humanizar("EMPRESA TEST E.I.R.L.") == "Empresa Test"

    def test_removes_sa(self):
        assert humanizar("CONSTRUCTORA GRANDE S.A.") == "Constructora Grande"

    def test_pipe_takes_commercial_name(self):
        assert humanizar("RAZÓN SOCIAL LTDA | Nombre Comercial") == "Nombre Comercial"

    def test_pipe_with_suffix_after(self):
        result = humanizar("LEGAL NAME | COMERCIAL SPA")
        assert "Spa" not in result
        assert result == "Comercial"

    def test_none_returns_string(self):
        result = humanizar(None)
        assert isinstance(result, str)
        assert result == "None"

    def test_nan_returns_string(self):
        result = humanizar(float("nan"))
        assert isinstance(result, str)

    def test_empty_string(self):
        result = humanizar("")
        assert isinstance(result, str)

    def test_numeric_input(self):
        result = humanizar(12345)
        assert isinstance(result, str)

    def test_preserves_words_without_suffix(self):
        assert humanizar("INGENIERÍA Y CONSTRUCCIÓN") == "Ingeniería Y Construcción"

    def test_strips_whitespace(self):
        assert humanizar("  EMPRESA TEST  ") == "Empresa Test"

    def test_ltda_lowercase(self):
        assert humanizar("Empresa Test ltda") == "Empresa Test"


# ══════════════════════════════════════════════════════════════════════════
# B. limpiar_rival
# ══════════════════════════════════════════════════════════════════════════

class TestLimpiarRival:

    def test_basic_cleaning(self):
        assert limpiar_rival("RIVAL CONSTRUCTOR SPA") == "Rival Constructor"

    def test_pipe_takes_last(self):
        assert limpiar_rival("LEGAL NAME | COMERCIAL") == "Comercial"

    def test_empty_returns_empty(self):
        assert limpiar_rival("") == ""

    def test_none_returns_empty(self):
        assert limpiar_rival(None) == ""

    def test_whitespace_only_returns_empty(self):
        assert limpiar_rival("   ") == ""

    def test_nan_string_returns_nan_title(self):
        # float NaN is not a str, so it returns ""
        assert limpiar_rival(float("nan")) == ""

    def test_removes_limitada(self):
        assert limpiar_rival("CONSTRUCTORA RIVAL LIMITADA") == "Constructora Rival"

    def test_title_case(self):
        result = limpiar_rival("EMPRESA RIVAL")
        assert result == "Empresa Rival"

    def test_removes_sa_dotted(self):
        assert limpiar_rival("CONSTRUCTORA BIG S.A.") == "Constructora Big"


# ══════════════════════════════════════════════════════════════════════════
# C. pct
# ══════════════════════════════════════════════════════════════════════════

class TestPct:

    def test_basic(self):
        assert pct(0.22) == "22%"

    def test_zero(self):
        assert pct(0) == "0%"

    def test_one(self):
        assert pct(1.0) == "100%"

    def test_rounding_up(self):
        assert pct(0.155) == "16%"  # 15.5 rounds to 16

    def test_rounding_down(self):
        assert pct(0.154) == "15%"  # 15.4 rounds to 15

    def test_small_value(self):
        assert pct(0.005) == "0%"  # 0.5 rounds to 0 with banker's rounding

    def test_large_value(self):
        assert pct(0.999) == "100%"

    def test_format_has_percent_sign(self):
        result = pct(0.33)
        assert result.endswith("%")


# ══════════════════════════════════════════════════════════════════════════
# D. meses
# ══════════════════════════════════════════════════════════════════════════

class TestMeses:

    def test_180_dias(self):
        assert meses(180) == 6

    def test_365_dias(self):
        assert meses(365) == 12

    def test_30_dias(self):
        assert meses(30) == 1

    def test_0_dias(self):
        assert meses(0) == 0

    def test_15_dias(self):
        # 15/30 = 0.5, round → 0
        assert meses(15) == 0

    def test_45_dias(self):
        # 45/30 = 1.5, round → 2
        assert meses(45) == 2

    def test_float_input(self):
        assert meses(180.5) == 6

    def test_string_numeric(self):
        assert meses("365") == 12

    def test_returns_int(self):
        result = meses(180)
        assert isinstance(result, int)


# ══════════════════════════════════════════════════════════════════════════
# E. elegir_insight — Prioridad de tipos
# ══════════════════════════════════════════════════════════════════════════

class TestElegirInsightRivalFuerte:
    """1. rival_fuerte: rival1_cnt >= 3 AND rival1 no vacío."""

    def test_rival_fuerte_basic(self):
        row = _make_row(top_rival_1_name="RIVAL SPA", top_rival_1_count=3)
        result = elegir_insight(row)
        assert result["tipo"] == "rival_fuerte"

    def test_rival_fuerte_high_count(self):
        row = _make_row(top_rival_1_name="RIVAL GRANDE LTDA", top_rival_1_count=7)
        result = elegir_insight(row)
        assert result["tipo"] == "rival_fuerte"

    def test_rival_fuerte_body_contains_rival(self):
        row = _make_row(top_rival_1_name="CONSTRUCTORA ABC SPA", top_rival_1_count=4)
        result = elegir_insight(row)
        # El nombre humanizado del rival debería estar en el cuerpo
        assert "Constructora Abc" in result["cuerpo"]

    def test_rival_fuerte_body_contains_count(self):
        row = _make_row(
            top_rival_1_name="RIVAL TEST",
            top_rival_1_count=5,
            total_lost_loss=10,
        )
        result = elegir_insight(row)
        assert "5" in result["cuerpo"]

    def test_rival_fuerte_has_cta(self):
        row = _make_row(top_rival_1_name="RIVAL", top_rival_1_count=3)
        result = elegir_insight(row)
        assert "?" in result["cta"]


class TestElegirInsightRivalRecurrente:
    """2. rival_recurrente: rival1_cnt >= 2 AND rival1 no vacío."""

    def test_rival_recurrente_basic(self):
        row = _make_row(top_rival_1_name="RIVAL SPA", top_rival_1_count=2)
        result = elegir_insight(row)
        assert result["tipo"] == "rival_recurrente"

    def test_rival_recurrente_not_fuerte(self):
        """cnt=2 debería ser recurrente, no fuerte."""
        row = _make_row(top_rival_1_name="RIVAL SPA", top_rival_1_count=2)
        result = elegir_insight(row)
        assert result["tipo"] != "rival_fuerte"

    def test_rival_recurrente_body_mentions_rival(self):
        row = _make_row(top_rival_1_name="CONSTRUCTORA RIVAL LTDA", top_rival_1_count=2)
        result = elegir_insight(row)
        assert "Constructora Rival" in result["cuerpo"]


class TestElegirInsightWinRateGapLP:
    """3. win_rate_gap_LP: n_LP >= 5 AND wr < 0.20."""

    def test_win_rate_gap_lp(self):
        row = _make_row(n_LP=5, win_rate=0.10)
        result = elegir_insight(row)
        assert result["tipo"] == "win_rate_gap_LP"

    def test_win_rate_gap_lp_at_boundary(self):
        row = _make_row(n_LP=5, win_rate=0.19)
        result = elegir_insight(row)
        assert result["tipo"] == "win_rate_gap_LP"

    def test_win_rate_gap_lp_not_if_wr_20(self):
        """wr=0.20 no debería activar win_rate_gap_LP."""
        row = _make_row(n_LP=5, win_rate=0.20)
        result = elegir_insight(row)
        assert result["tipo"] != "win_rate_gap_LP"

    def test_body_mentions_gap_points(self):
        row = _make_row(n_LP=6, win_rate=0.10)
        result = elegir_insight(row)
        # Gap = 22% - 10% = 12 puntos
        assert "12 puntos" in result["cuerpo"]

    def test_body_mentions_lp_count(self):
        row = _make_row(n_LP=8, win_rate=0.15)
        result = elegir_insight(row)
        assert "8 licitaciones" in result["cuerpo"]


class TestElegirInsightLpAlto:
    """4. lp_alto: n_LP >= 5 (con wr >= 0.20)."""

    def test_lp_alto_wr_above_industry(self):
        row = _make_row(n_LP=5, win_rate=0.30)
        result = elegir_insight(row)
        assert result["tipo"] == "lp_alto"

    def test_lp_alto_wr_at_industry(self):
        row = _make_row(n_LP=5, win_rate=0.22)
        result = elegir_insight(row)
        assert result["tipo"] == "lp_alto"

    def test_lp_alto_wr_below_industry_but_above_20(self):
        """wr=0.20 → lp_alto (no win_rate_gap_LP porque wr no es < 0.20)."""
        row = _make_row(n_LP=5, win_rate=0.20)
        result = elegir_insight(row)
        assert result["tipo"] == "lp_alto"

    def test_lp_alto_body_has_lp_count(self):
        row = _make_row(n_LP=7, win_rate=0.25)
        result = elegir_insight(row)
        assert "7 licitaciones" in result["cuerpo"]


class TestElegirInsightInactivo:
    """5. inactivo: dias >= 180."""

    def test_inactivo_basic(self):
        row = _make_row(dias_desde_ultima=200, n_LP=2)
        result = elegir_insight(row)
        assert result["tipo"] == "inactivo"

    def test_inactivo_at_boundary(self):
        row = _make_row(dias_desde_ultima=180, n_LP=2)
        result = elegir_insight(row)
        assert result["tipo"] == "inactivo"

    def test_inactivo_not_if_less(self):
        row = _make_row(dias_desde_ultima=179, n_LP=2)
        result = elegir_insight(row)
        assert result["tipo"] != "inactivo"

    def test_inactivo_body_has_meses(self):
        row = _make_row(dias_desde_ultima=270, n_LP=2)
        result = elegir_insight(row)
        assert "9 meses" in result["cuerpo"]

    def test_inactivo_over_rival_if_no_rival(self):
        """Sin rival, inactivo tiene prioridad sobre wr_bajo_lp."""
        row = _make_row(
            dias_desde_ultima=200,
            n_LP=4, win_rate=0.15,
            top_rival_1_name="", top_rival_1_count=0,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "inactivo"


class TestElegirInsightWrBajoLp:
    """6. wr_bajo_lp: wr < 0.20 AND n_LP >= 3."""

    def test_wr_bajo_lp_basic(self):
        row = _make_row(win_rate=0.15, n_LP=3, dias_desde_ultima=90)
        result = elegir_insight(row)
        assert result["tipo"] == "wr_bajo_lp"

    def test_wr_bajo_lp_high_lp(self):
        row = _make_row(win_rate=0.10, n_LP=4, dias_desde_ultima=90)
        result = elegir_insight(row)
        assert result["tipo"] == "wr_bajo_lp"

    def test_wr_bajo_lp_not_if_lp_lt_3(self):
        row = _make_row(win_rate=0.15, n_LP=2, dias_desde_ultima=90)
        result = elegir_insight(row)
        assert result["tipo"] != "wr_bajo_lp"


class TestElegirInsightLossConcentrado:
    """7. loss_concentrado: loss_rate >= 0.40 AND total_lost >= 5."""

    def test_loss_concentrado_basic(self):
        row = _make_row(
            loss_rate=0.50, total_lost_loss=6,
            win_rate=0.25, n_LP=2, dias_desde_ultima=90,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "loss_concentrado"

    def test_loss_concentrado_not_if_low_losses(self):
        row = _make_row(
            loss_rate=0.50, total_lost_loss=4,
            win_rate=0.25, n_LP=2, dias_desde_ultima=90,
        )
        result = elegir_insight(row)
        assert result["tipo"] != "loss_concentrado"

    def test_loss_concentrado_at_boundary(self):
        row = _make_row(
            loss_rate=0.40, total_lost_loss=5,
            win_rate=0.25, n_LP=2, dias_desde_ultima=90,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "loss_concentrado"


class TestElegirInsightWrBajo:
    """8. wr_bajo: wr < 0.19."""

    def test_wr_bajo_basic(self):
        row = _make_row(
            win_rate=0.15, n_LP=2, dias_desde_ultima=90,
            loss_rate=0.30, total_lost_loss=3,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "wr_bajo"

    def test_wr_bajo_at_boundary(self):
        """wr=0.19 no debería activar wr_bajo (condición es < 0.19)."""
        row = _make_row(
            win_rate=0.19, n_LP=2, dias_desde_ultima=90,
            loss_rate=0.30, total_lost_loss=3,
        )
        result = elegir_insight(row)
        assert result["tipo"] != "wr_bajo"

    def test_wr_bajo_body_has_stats(self):
        row = _make_row(
            win_rate=0.10, n_LP=2, total_bids=20, total_wins=2,
            dias_desde_ultima=90, loss_rate=0.30, total_lost_loss=3,
        )
        result = elegir_insight(row)
        assert "10%" in result["cuerpo"]
        assert "20 postulaciones" in result["cuerpo"]


class TestElegirInsightRivalUnico:
    """9. rival_unico: rival1 no vacío AND total_lost >= 3."""

    def test_rival_unico_basic(self):
        row = _make_row(
            top_rival_1_name="RIVAL UNO SPA", top_rival_1_count=1,
            total_lost_loss=3, win_rate=0.25, n_LP=2,
            dias_desde_ultima=90, loss_rate=0.30,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "rival_unico"

    def test_rival_unico_body_mentions_rival(self):
        row = _make_row(
            top_rival_1_name="CONSTRUCTORA ALFA LTDA", top_rival_1_count=1,
            total_lost_loss=5, win_rate=0.25, n_LP=2,
            dias_desde_ultima=90, loss_rate=0.30,
        )
        result = elegir_insight(row)
        assert "Constructora Alfa" in result["cuerpo"]

    def test_rival_unico_not_if_few_losses(self):
        row = _make_row(
            top_rival_1_name="RIVAL SPA", top_rival_1_count=1,
            total_lost_loss=2, win_rate=0.25, n_LP=2,
            dias_desde_ultima=90, loss_rate=0.20,
        )
        result = elegir_insight(row)
        assert result["tipo"] != "rival_unico"


class TestElegirInsightDefault:
    """10. default: todos los demás casos."""

    def test_default_basic(self):
        row = _make_row(
            win_rate=0.25, n_LP=2, dias_desde_ultima=90,
            loss_rate=0.20, total_lost_loss=2,
            top_rival_1_name="", top_rival_1_count=0,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "default"

    def test_default_has_stats(self):
        row = _make_row(
            win_rate=0.30, total_bids=15, total_wins=5,
            n_LP=2, dias_desde_ultima=90,
            loss_rate=0.20, total_lost_loss=2,
            top_rival_1_name="", top_rival_1_count=0,
        )
        result = elegir_insight(row)
        assert "15 postulaciones" in result["cuerpo"]
        assert "5 adjudicadas" in result["cuerpo"]

    def test_default_has_cta(self):
        row = _make_row(
            win_rate=0.25, n_LP=2, dias_desde_ultima=90,
            loss_rate=0.20, total_lost_loss=2,
            top_rival_1_name="", top_rival_1_count=0,
        )
        result = elegir_insight(row)
        assert "?" in result["cta"]


# ══════════════════════════════════════════════════════════════════════════
# E2. elegir_insight — Prioridad relativa
# ══════════════════════════════════════════════════════════════════════════

class TestInsightPriority:
    """Verificar que la prioridad de insights se respeta."""

    def test_rival_fuerte_over_everything(self):
        """rival_fuerte tiene máxima prioridad."""
        row = _make_row(
            top_rival_1_name="RIVAL SPA", top_rival_1_count=3,
            n_LP=6, win_rate=0.10,
            dias_desde_ultima=300, loss_rate=0.50, total_lost_loss=8,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "rival_fuerte"

    def test_rival_recurrente_over_lp(self):
        row = _make_row(
            top_rival_1_name="RIVAL SPA", top_rival_1_count=2,
            n_LP=6, win_rate=0.10,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "rival_recurrente"

    def test_win_rate_gap_over_lp_alto(self):
        """n_LP>=5, wr<20% → win_rate_gap_LP (no lp_alto)."""
        row = _make_row(n_LP=5, win_rate=0.10)
        result = elegir_insight(row)
        assert result["tipo"] == "win_rate_gap_LP"

    def test_inactivo_before_wr_bajo_lp(self):
        """dias>=180 con n_LP<5 → inactivo (no wr_bajo_lp)."""
        row = _make_row(
            dias_desde_ultima=200, win_rate=0.15, n_LP=4,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "inactivo"

    def test_all_zero_returns_default(self):
        row = _make_row(
            win_rate=0.25, n_LP=0, dias_desde_ultima=0,
            loss_rate=0, total_lost_loss=0, total_bids=1, total_wins=0,
            top_rival_1_name="", top_rival_1_count=0,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "default"


# ══════════════════════════════════════════════════════════════════════════
# E3. elegir_insight — NaN y valores faltantes
# ══════════════════════════════════════════════════════════════════════════

class TestInsightEdgeCases:

    def test_nan_win_rate(self):
        row = _make_row(win_rate=float("nan"))
        result = elegir_insight(row)
        assert result["tipo"] in (
            "rival_fuerte", "rival_recurrente", "win_rate_gap_LP",
            "lp_alto", "inactivo", "wr_bajo_lp", "loss_concentrado",
            "wr_bajo", "rival_unico", "default",
        )

    def test_none_rival(self):
        row = _make_row(top_rival_1_name=None, top_rival_1_count=5)
        result = elegir_insight(row)
        # rival limpiado será "", así que no debería ser rival_fuerte
        assert result["tipo"] != "rival_fuerte"

    def test_zero_everything(self):
        """wr=0 < 0.19 → wr_bajo (no default, porque la condición se cumple)."""
        row = _make_row(
            win_rate=0, n_LP=0, total_lost_loss=0, loss_rate=0,
            total_bids=0, total_wins=0, dias_desde_ultima=0,
            top_rival_1_name="", top_rival_1_count=0,
        )
        result = elegir_insight(row)
        assert result["tipo"] == "wr_bajo"

    def test_missing_fields_uses_defaults(self):
        """Row con solo algunos campos — no debería crashear."""
        row = pd.Series({"nombre": "TEST"})
        result = elegir_insight(row)
        assert "tipo" in result
        assert "cuerpo" in result
        assert "cta" in result

    def test_insight_always_has_required_keys(self):
        """Todos los insights deben tener tipo, cuerpo, cta."""
        rows = [
            _make_row(top_rival_1_name="R", top_rival_1_count=3),
            _make_row(top_rival_1_name="R", top_rival_1_count=2),
            _make_row(n_LP=5, win_rate=0.10),
            _make_row(n_LP=5, win_rate=0.25),
            _make_row(dias_desde_ultima=200, n_LP=2),
            _make_row(win_rate=0.15, n_LP=3, dias_desde_ultima=90),
            _make_row(loss_rate=0.50, total_lost_loss=6, win_rate=0.25, n_LP=2, dias_desde_ultima=90),
            _make_row(win_rate=0.15, n_LP=2, dias_desde_ultima=90, loss_rate=0.30, total_lost_loss=3),
            _make_row(top_rival_1_name="R", top_rival_1_count=1, total_lost_loss=3, win_rate=0.25, n_LP=2, dias_desde_ultima=90, loss_rate=0.30),
            _make_row(),
        ]
        for row in rows:
            result = elegir_insight(row)
            assert "tipo" in result
            assert "cuerpo" in result
            assert "cta" in result
            assert len(result["cuerpo"]) > 10
            assert "?" in result["cta"]


# ══════════════════════════════════════════════════════════════════════════
# F. Mensajes NO contienen términos prohibidos
# ══════════════════════════════════════════════════════════════════════════

class TestForbiddenTerms:

    @pytest.fixture
    def all_insight_rows(self):
        """Rows que generan cada tipo de insight."""
        return [
            _make_row(top_rival_1_name="RIVAL SPA", top_rival_1_count=3),
            _make_row(top_rival_1_name="RIVAL SPA", top_rival_1_count=2),
            _make_row(n_LP=5, win_rate=0.10),
            _make_row(n_LP=5, win_rate=0.25),
            _make_row(dias_desde_ultima=200, n_LP=2),
            _make_row(win_rate=0.15, n_LP=3, dias_desde_ultima=90),
            _make_row(loss_rate=0.50, total_lost_loss=6, win_rate=0.25, n_LP=2, dias_desde_ultima=90),
            _make_row(win_rate=0.15, n_LP=2, dias_desde_ultima=90, loss_rate=0.30, total_lost_loss=3),
            _make_row(top_rival_1_name="R SPA", top_rival_1_count=1, total_lost_loss=3, win_rate=0.25, n_LP=2, dias_desde_ultima=90, loss_rate=0.30),
            _make_row(win_rate=0.25, n_LP=2, dias_desde_ultima=90, loss_rate=0.20, total_lost_loss=2, top_rival_1_name="", top_rival_1_count=0),
        ]

    def test_no_forbidden_in_any_message(self, all_insight_rows):
        for row in all_insight_rows:
            msg = generar_mensaje("Empresa Test", "Juan", row)
            msg_lower = msg.lower()
            for term in FORBIDDEN_TERMS:
                assert term.lower() not in msg_lower, (
                    f"Término prohibido '{term}' encontrado en mensaje tipo "
                    f"{elegir_insight(row)['tipo']}: {msg[:100]}..."
                )

    def test_no_forbidden_in_cuerpo(self, all_insight_rows):
        for row in all_insight_rows:
            insight = elegir_insight(row)
            cuerpo_lower = insight["cuerpo"].lower()
            for term in FORBIDDEN_TERMS:
                assert term.lower() not in cuerpo_lower, (
                    f"Término prohibido '{term}' en cuerpo de {insight['tipo']}"
                )

    def test_no_forbidden_in_cta(self, all_insight_rows):
        for row in all_insight_rows:
            insight = elegir_insight(row)
            cta_lower = insight["cta"].lower()
            for term in FORBIDDEN_TERMS:
                assert term.lower() not in cta_lower, (
                    f"Término prohibido '{term}' en CTA de {insight['tipo']}"
                )


# ══════════════════════════════════════════════════════════════════════════
# G. generar_mensaje
# ══════════════════════════════════════════════════════════════════════════

class TestGenerarMensaje:

    def test_with_contact_name(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", "Juan Pérez", row)
        assert msg.startswith("Hola Juan,")

    def test_without_contact_name(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", None, row)
        assert msg.startswith("Hola,")

    def test_empty_contact_name(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", "", row)
        assert msg.startswith("Hola,")

    def test_short_contact_name(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", "AB", row)
        assert msg.startswith("Hola,")

    def test_contains_firma(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", "Juan", row)
        assert "Sebastián Cortés" in msg
        assert "IngenIA Licitaciones" in msg

    def test_contains_sebastian(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", "Juan", row)
        assert "soy Sebastián de IngenIA Licitaciones" in msg

    def test_contains_cta_question(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", "Juan", row)
        assert "?" in msg

    def test_multiword_contact_uses_first_name(self):
        row = _make_row()
        msg = generar_mensaje("Empresa", "María José López", row)
        assert "Hola María," in msg


# ══════════════════════════════════════════════════════════════════════════
# H. generar_wsp_link
# ══════════════════════════════════════════════════════════════════════════

class TestGenerarWspLink:

    def test_with_56_prefix(self):
        link = generar_wsp_link("+56912345678", "hola")
        assert "wa.me/56912345678" in link

    def test_without_56_prefix(self):
        link = generar_wsp_link("912345678", "hola")
        assert "wa.me/56912345678" in link

    def test_float_phone(self):
        link = generar_wsp_link("56912345678.0", "hola")
        assert "wa.me/56912345678" in link

    def test_url_encoded_message(self):
        link = generar_wsp_link("+56912345678", "hola mundo")
        assert "text=" in link
        # Spaces should be encoded
        assert "hola mundo" not in link.split("text=")[1]

    def test_starts_with_https(self):
        link = generar_wsp_link("+56912345678", "test")
        assert link.startswith("https://wa.me/")

    def test_strips_non_digits(self):
        link = generar_wsp_link("+56 9 1234 5678", "test")
        assert "wa.me/56912345678" in link

    def test_with_leading_zero(self):
        link = generar_wsp_link("0912345678", "test")
        assert "wa.me/56912345678" in link


# ══════════════════════════════════════════════════════════════════════════
# I. Verificar helpers de verificar_mensajes_v2.py
# ══════════════════════════════════════════════════════════════════════════

class TestGetRivalAliases:

    def test_basic(self):
        aliases = get_rival_aliases("CONSTRUCTORA ABC LTDA")
        assert len(aliases) >= 1
        assert aliases[0] == "constructora abc ltda"

    def test_with_pipe(self):
        aliases = get_rival_aliases("LEGAL NAME | COMERCIAL NAME")
        assert len(aliases) == 2
        assert "legal name" in aliases
        assert "comercial name" in aliases

    def test_empty(self):
        assert get_rival_aliases("") == []

    def test_none(self):
        assert get_rival_aliases(None) == []

    def test_nan_string(self):
        assert get_rival_aliases("nan") == []


class TestNameMatches:

    def test_exact_match(self):
        assert name_matches("constructora abc", ["constructora abc"]) is True

    def test_partial_match_candidate_in_alias(self):
        assert name_matches("ABC", ["constructora abc ltda"]) is True

    def test_partial_match_alias_in_candidate(self):
        assert name_matches("Constructora Abc Ltda Y Más", ["constructora abc"]) is True

    def test_no_match(self):
        assert name_matches("empresa xyz", ["constructora abc"]) is False

    def test_case_insensitive(self):
        assert name_matches("CONSTRUCTORA ABC", ["constructora abc"]) is True

    def test_empty_aliases(self):
        assert name_matches("anything", []) is False


# ══════════════════════════════════════════════════════════════════════════
# J. INDUSTRY_WR_MEDIAN y constantes
# ══════════════════════════════════════════════════════════════════════════

class TestConstants:

    def test_industry_wr_median_value(self):
        assert INDUSTRY_WR_MEDIAN == 0.22

    def test_industry_wr_median_type(self):
        assert isinstance(INDUSTRY_WR_MEDIAN, float)

    def test_firma_has_name(self):
        assert "Sebastián Cortés" in FIRMA

    def test_firma_has_company(self):
        assert "IngenIA Licitaciones" in FIRMA


# ══════════════════════════════════════════════════════════════════════════
# K. Integración con datos reales
# ══════════════════════════════════════════════════════════════════════════

skip_no_loss = pytest.mark.skipif(
    not LOSS_ANALYSIS_PATH.exists(),
    reason="loss_analysis.parquet no disponible",
)


@skip_no_loss
class TestIntegrationRealData:
    """Tests de integración con datos reales del parquet."""

    def test_first_10_leads_insight_consistent(self):
        """Para los primeros 10 leads, el insight_tipo es consistente con sus datos."""
        loss = pd.read_parquet(LOSS_ANALYSIS_PATH)
        for _, row in loss.head(10).iterrows():
            insight = elegir_insight(row)
            tipo = insight["tipo"]

            wr = float(row.get("win_rate", 0) or 0)
            n_lp = int(row.get("n_LP", 0) or 0)
            rival1 = str(row.get("top_rival_1_name", "") or "").strip()
            rival1_cnt = int(row.get("top_rival_1_count", 0) or 0)
            dias = float(row.get("dias_desde_ultima", 0) or 0)
            total_lost = int(row.get("total_lost_loss", 0) or 0)
            loss_rate = float(row.get("loss_rate", 0) or 0)

            # Verificar consistencia del tipo con datos
            if tipo == "rival_fuerte":
                assert rival1_cnt >= 3 and rival1 != ""
            elif tipo == "rival_recurrente":
                assert rival1_cnt >= 2 and rival1 != ""
            elif tipo == "win_rate_gap_LP":
                assert n_lp >= 5 and wr < 0.20
            elif tipo == "lp_alto":
                assert n_lp >= 5
            elif tipo == "inactivo":
                assert dias >= 180
            elif tipo == "wr_bajo_lp":
                assert wr < 0.20 and n_lp >= 3
            elif tipo == "loss_concentrado":
                assert loss_rate >= 0.40 and total_lost >= 5
            elif tipo == "wr_bajo":
                assert wr < 0.19

    def test_real_messages_no_forbidden_terms(self):
        """Ningún mensaje generado con datos reales contiene términos prohibidos."""
        loss = pd.read_parquet(LOSS_ANALYSIS_PATH)
        for _, row in loss.head(10).iterrows():
            nombre = str(row.get("nombre", "Empresa"))
            empresa = humanizar(nombre)
            msg = generar_mensaje(empresa, None, row)
            msg_lower = msg.lower()
            for term in FORBIDDEN_TERMS:
                assert term.lower() not in msg_lower, (
                    f"Término prohibido '{term}' en mensaje para RUT {row.get('rut')}"
                )

    def test_all_insights_have_cta_question(self):
        """Todos los mensajes tienen CTA con signo de interrogación."""
        loss = pd.read_parquet(LOSS_ANALYSIS_PATH)
        for _, row in loss.head(20).iterrows():
            insight = elegir_insight(row)
            assert "?" in insight["cta"], (
                f"CTA sin '?' para RUT {row.get('rut')}, tipo={insight['tipo']}"
            )

    def test_insight_distribution_covers_multiple_types(self):
        """Los datos reales producen al menos 3 tipos de insight diferentes."""
        loss = pd.read_parquet(LOSS_ANALYSIS_PATH)
        tipos = set()
        for _, row in loss.iterrows():
            insight = elegir_insight(row)
            tipos.add(insight["tipo"])
        assert len(tipos) >= 3, f"Solo {len(tipos)} tipos: {tipos}"
