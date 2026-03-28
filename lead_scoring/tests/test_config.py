"""
Tests exhaustivos para config.py — configuración central del pipeline.

Cubre: pesos de scoring, rangos ideales, paths, constantes, funciones de
env vars, runtime labels, y constantes de pipeline_core relacionadas.
"""
from __future__ import annotations

import os
import sys
from collections import namedtuple
from unittest.mock import patch

import pytest

from config import (
    BASE_DIR,
    BULK_YEARS,
    CONSTRUCTION_UNSPSC_PREFIX,
    DATA_DIR,
    ENRICH_TOP_N,
    FILTERED_DIR,
    IDEAL_RANGES,
    OUTPUT_DIR,
    PLACEHOLDER_SECRET_VALUES,
    PYTHON_BASELINE,
    PYTHON_TARGET,
    RAW_DIR,
    RECENCIA_MAX_DAYS,
    REGIONES_TOP,
    SCORING_WEIGHTS,
    TIPOS_LICITACION,
    env_value_status,
    missing_env_vars,
    python_runtime_label,
    redact_secret,
    runtime_support_status,
)
from pipeline_core import CLIENT_FORBIDDEN_COLUMNS, COMBINED_SCORE_WEIGHTS


# ====================================================================
# SCORING_WEIGHTS
# ====================================================================


class TestScoringWeights:
    """Verifica integridad de los pesos de scoring (9 dimensiones)."""

    EXPECTED_DIMENSIONS = {
        "actividad",
        "tamano",
        "win_rate",
        "recencia",
        "valor",
        "competencia",
        "oportunidad",
        "especializacion",
        "region",
    }

    def test_weights_sum_to_one(self):
        total = sum(SCORING_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Suma = {total}, esperado 1.0"

    def test_all_nine_dimensions_present(self):
        assert set(SCORING_WEIGHTS.keys()) == self.EXPECTED_DIMENSIONS

    def test_exactly_nine_dimensions(self):
        assert len(SCORING_WEIGHTS) == 9

    @pytest.mark.parametrize("dim", [
        "actividad", "tamano", "win_rate", "recencia", "valor",
        "competencia", "oportunidad", "especializacion", "region",
    ])
    def test_each_weight_positive_and_less_than_one(self, dim):
        w = SCORING_WEIGHTS[dim]
        assert 0 < w < 1, f"{dim} peso={w}, debe ser (0,1)"

    def test_no_extra_dimensions(self):
        extras = set(SCORING_WEIGHTS.keys()) - self.EXPECTED_DIMENSIONS
        assert not extras, f"Dimensiones extra: {extras}"

    def test_weights_are_floats(self):
        for dim, w in SCORING_WEIGHTS.items():
            assert isinstance(w, float), f"{dim} tipo={type(w)}, esperado float"


# ====================================================================
# IDEAL_RANGES
# ====================================================================


class TestIdealRanges:
    """Verifica coherencia de los rangos ideales de scoring."""

    def test_all_ranges_have_min_less_than_max(self):
        for key, (lo, hi) in IDEAL_RANGES.items():
            assert lo < hi, f"{key}: min={lo} >= max={hi}"

    def test_actividad_min_non_negative(self):
        lo, _ = IDEAL_RANGES["actividad"]
        assert lo >= 0, f"actividad min={lo}, no puede ser negativo"

    def test_win_rate_range_within_zero_one(self):
        lo, hi = IDEAL_RANGES["win_rate"]
        assert 0 <= lo <= 1, f"win_rate lo={lo} fuera de [0,1]"
        assert 0 <= hi <= 1, f"win_rate hi={hi} fuera de [0,1]"

    def test_valor_clp_positive(self):
        lo, hi = IDEAL_RANGES["valor_clp"]
        assert lo > 0, "valor_clp min debe ser positivo"
        assert hi > lo, "valor_clp max debe ser mayor que min"

    def test_competencia_positive_range(self):
        lo, hi = IDEAL_RANGES["competencia"]
        assert lo > 0, "competencia min debe ser > 0"
        assert hi > lo

    def test_recencia_dias_starts_at_zero(self):
        lo, _ = IDEAL_RANGES["recencia_dias"]
        assert lo == 0, "recencia_dias min debe ser 0 (hoy)"


# ====================================================================
# Constantes simples
# ====================================================================


class TestConstants:
    """Verifica constantes clave del pipeline."""

    def test_recencia_max_days_greater_than_365(self):
        assert RECENCIA_MAX_DAYS > 365

    def test_regiones_top_not_empty(self):
        assert len(REGIONES_TOP) > 0

    def test_regiones_top_no_duplicates(self):
        assert len(REGIONES_TOP) == len(set(REGIONES_TOP))

    def test_tipos_licitacion_has_required_keys(self):
        for key in ("L1", "LE", "LP", "LR"):
            assert key in TIPOS_LICITACION, f"Falta tipo {key}"

    def test_tipos_licitacion_values_non_empty(self):
        for key, desc in TIPOS_LICITACION.items():
            assert desc, f"{key} descripción vacía"

    def test_construction_unspsc_prefix(self):
        assert CONSTRUCTION_UNSPSC_PREFIX == "72"

    def test_bulk_years_has_four_or_more(self):
        assert len(BULK_YEARS) >= 4

    def test_bulk_years_are_ints(self):
        for y in BULK_YEARS:
            assert isinstance(y, int), f"Año {y} no es int"

    def test_bulk_years_reasonable_range(self):
        for y in BULK_YEARS:
            assert 2020 <= y <= 2030, f"Año {y} fuera de rango razonable"

    def test_enrich_top_n_positive(self):
        assert ENRICH_TOP_N > 0

    def test_placeholder_secret_values_not_empty(self):
        assert len(PLACEHOLDER_SECRET_VALUES) > 0

    def test_placeholder_values_are_lowercase(self):
        for v in PLACEHOLDER_SECRET_VALUES:
            assert v == v.lower(), f"Placeholder '{v}' debe ser lowercase"


# ====================================================================
# Paths
# ====================================================================


class TestPaths:
    """Verifica que los directorios del pipeline existen."""

    def test_base_dir_exists(self):
        assert BASE_DIR.exists(), f"BASE_DIR no existe: {BASE_DIR}"

    def test_data_dir_exists(self):
        assert DATA_DIR.exists(), f"DATA_DIR no existe: {DATA_DIR}"

    def test_raw_dir_exists(self):
        assert RAW_DIR.exists(), f"RAW_DIR no existe: {RAW_DIR}"

    def test_filtered_dir_exists(self):
        assert FILTERED_DIR.exists(), f"FILTERED_DIR no existe: {FILTERED_DIR}"

    def test_output_dir_exists(self):
        assert OUTPUT_DIR.exists(), f"OUTPUT_DIR no existe: {OUTPUT_DIR}"

    def test_base_dir_is_directory(self):
        assert BASE_DIR.is_dir()

    def test_config_py_inside_base_dir(self):
        assert (BASE_DIR / "config.py").exists()


# ====================================================================
# Python version tuples
# ====================================================================


class TestPythonVersion:
    """Verifica constantes y funciones de versión Python."""

    def test_baseline_is_tuple(self):
        assert isinstance(PYTHON_BASELINE, tuple)

    def test_target_is_tuple(self):
        assert isinstance(PYTHON_TARGET, tuple)

    def test_baseline_has_two_elements(self):
        assert len(PYTHON_BASELINE) == 2

    def test_target_has_two_elements(self):
        assert len(PYTHON_TARGET) == 2

    def test_baseline_major_is_3(self):
        assert PYTHON_BASELINE[0] == 3

    def test_target_major_is_3(self):
        assert PYTHON_TARGET[0] == 3

    def test_target_minor_gte_baseline_minor(self):
        assert PYTHON_TARGET[1] >= PYTHON_BASELINE[1]


# ====================================================================
# python_runtime_label
# ====================================================================


class TestPythonRuntimeLabel:

    def test_format_matches_major_dot_minor(self):
        label = python_runtime_label()
        parts = label.split(".")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_current_runtime_label(self):
        expected = f"{sys.version_info.major}.{sys.version_info.minor}"
        assert python_runtime_label() == expected

    def test_custom_version_info(self):
        FakeVer = namedtuple("FakeVer", ["major", "minor"])
        assert python_runtime_label(FakeVer(3, 12)) == "3.12"


# ====================================================================
# runtime_support_status
# ====================================================================


class TestRuntimeSupportStatus:

    def test_baseline_returns_baseline(self):
        FakeVer = namedtuple("FakeVer", ["major", "minor"])
        ver = FakeVer(*PYTHON_BASELINE)
        assert runtime_support_status(ver) == "baseline"

    def test_target_returns_target(self):
        FakeVer = namedtuple("FakeVer", ["major", "minor"])
        ver = FakeVer(*PYTHON_TARGET)
        assert runtime_support_status(ver) == "target"

    def test_other_returns_unverified(self):
        FakeVer = namedtuple("FakeVer", ["major", "minor"])
        ver = FakeVer(3, 99)
        assert runtime_support_status(ver) == "unverified"

    def test_default_uses_sys_version(self):
        result = runtime_support_status()
        assert result in ("baseline", "target", "unverified")


# ====================================================================
# env_value_status
# ====================================================================


class TestEnvValueStatus:

    def test_empty_string_is_missing(self):
        assert env_value_status("") == "missing"

    def test_none_is_missing(self):
        assert env_value_status(None) == "missing"

    def test_whitespace_only_is_missing(self):
        assert env_value_status("   ") == "missing"

    def test_replace_me_is_placeholder(self):
        assert env_value_status("replace_me") == "placeholder"

    def test_placeholder_case_insensitive(self):
        assert env_value_status("REPLACE_ME") == "placeholder"
        assert env_value_status("Replace_Me") == "placeholder"

    def test_todo_is_placeholder(self):
        assert env_value_status("todo") == "placeholder"

    def test_real_value_is_ok(self):
        assert env_value_status("abc123xyz") == "ok"

    def test_long_real_value_is_ok(self):
        assert env_value_status("real_token_AbCdEf1234567890") == "ok"


# ====================================================================
# redact_secret
# ====================================================================


class TestRedactSecret:

    def test_missing_returns_tag(self):
        assert redact_secret("") == "<missing>"

    def test_placeholder_returns_tag(self):
        assert redact_secret("replace_me") == "<placeholder>"

    def test_configured_shows_length(self):
        result = redact_secret("my_secret_key_123")
        assert result.startswith("<configured:")
        assert "17 chars" in result

    def test_configured_does_not_leak_value(self):
        result = redact_secret("super_secret_api_key")
        assert "super_secret" not in result

    def test_none_is_missing(self):
        assert redact_secret(None) == "<missing>"


# ====================================================================
# missing_env_vars
# ====================================================================


class TestMissingEnvVars:

    def test_set_vars_not_missing(self):
        with patch.dict(os.environ, {"TEST_VAR_A": "real_value"}):
            result = missing_env_vars(["TEST_VAR_A"])
            assert result == []

    def test_unset_vars_are_missing(self):
        env_clean = {k: v for k, v in os.environ.items() if k != "NONEXISTENT_VAR_XYZ"}
        with patch.dict(os.environ, env_clean, clear=True):
            result = missing_env_vars(["NONEXISTENT_VAR_XYZ"])
            assert "NONEXISTENT_VAR_XYZ" in result

    def test_placeholder_vars_are_missing(self):
        with patch.dict(os.environ, {"TEST_PLACEHOLDER": "replace_me"}):
            result = missing_env_vars(["TEST_PLACEHOLDER"])
            assert "TEST_PLACEHOLDER" in result

    def test_empty_list_returns_empty(self):
        assert missing_env_vars([]) == []

    def test_mix_of_set_and_unset(self):
        env = {"PRESENT_VAR": "good_value"}
        with patch.dict(os.environ, env, clear=True):
            result = missing_env_vars(["PRESENT_VAR", "ABSENT_VAR"])
            assert "PRESENT_VAR" not in result
            assert "ABSENT_VAR" in result


# ====================================================================
# pipeline_core: COMBINED_SCORE_WEIGHTS y CLIENT_FORBIDDEN_COLUMNS
# ====================================================================


class TestPipelineCoreConstants:
    """Verifica constantes de pipeline_core.py importadas desde config tests."""

    def test_combined_score_weights_sum_to_one(self):
        total = sum(COMBINED_SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Suma = {total}, esperado 1.0"

    def test_combined_score_weights_has_expected_keys(self):
        assert "score_total" in COMBINED_SCORE_WEIGHTS
        assert "km_score" in COMBINED_SCORE_WEIGHTS
        assert "xgb_score" in COMBINED_SCORE_WEIGHTS

    def test_combined_score_weights_all_positive(self):
        for key, w in COMBINED_SCORE_WEIGHTS.items():
            assert w > 0, f"{key} peso={w}, debe ser positivo"

    def test_client_forbidden_columns_not_empty(self):
        assert len(CLIENT_FORBIDDEN_COLUMNS) > 0

    def test_client_forbidden_has_score_total(self):
        assert "score_total" in CLIENT_FORBIDDEN_COLUMNS

    def test_client_forbidden_has_score_combined(self):
        assert "score_combined" in CLIENT_FORBIDDEN_COLUMNS

    def test_client_forbidden_has_cluster(self):
        assert "cluster" in CLIENT_FORBIDDEN_COLUMNS

    def test_client_forbidden_has_ml_scores(self):
        assert "km_score" in CLIENT_FORBIDDEN_COLUMNS
        assert "xgb_score" in CLIENT_FORBIDDEN_COLUMNS
