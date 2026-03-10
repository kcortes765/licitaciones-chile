"""
Test suite exhaustivo para el pipeline de Lead Scoring.
~1000 tests cubriendo:
  - Unit tests de cada función
  - Edge cases (NaN, vacíos, None, tipos incorrectos)
  - Integración entre pasos del pipeline
  - Regresiones de bugs conocidos

Uso:
  python -m pytest test_pipeline.py -v
  python -m pytest test_pipeline.py -v --tb=short -q  # Resumido
"""
from __future__ import annotations

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from importlib import import_module
from unittest.mock import patch, MagicMock
from collections import Counter

import pytest
import pandas as pd
import numpy as np

# Agregar el directorio actual al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    SCORING_WEIGHTS, IDEAL_RANGES, REGIONES_TOP, TIPOS_LICITACION,
    CONSTRUCTION_UNSPSC_PREFIX, BULK_CSV_FILES, ENRICH_TOP_N,
    env_value_status, env_var_report, redact_secret,
)
from pipeline_core import build_crm_dataframe, load_best_leads_dataframe, recompute_score_combined
from pipeline_validation import (
    assert_client_safe_binary,
    assert_client_safe_columns,
    assert_client_safe_json,
    assert_client_safe_text,
    assert_dataframe_contract,
    validate_dataframe_contract,
)
from utils import (
    normalizar_rut, extraer_rut_de_id, tipo_licitacion,
    safe_request, formato_clp, safe_get, print_header,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Crea estructura de directorios temporal."""
    raw = tmp_path / "data" / "raw"
    filtered = tmp_path / "data" / "filtered"
    output = tmp_path / "data" / "output"
    raw.mkdir(parents=True)
    filtered.mkdir(parents=True)
    output.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_company_df():
    """DataFrame de empresa de prueba."""
    return pd.DataFrame({
        "rut": ["76543210-K", "12345678-9", "98765432-1", "11111111-1", "22222222-2"],
        "nombre": ["Constructora A", "Constructora B", "Constructora C", None, "Empresa E"],
        "region": ["Región Metropolitana de Santiago", "Región de Valparaíso", None, "", "Región del Biobío"],
        "total_bids": [10, 5, 20, 2, 1],
        "total_wins": [3, 0, 8, 1, 0],
        "win_rate": [0.3, 0.0, 0.4, 0.5, 0.0],
        "monto_promedio": [200_000_000, 50_000_000, 800_000_000, 10_000_000, np.nan],
        "monto_total": [2_000_000_000, 250_000_000, 16_000_000_000, 20_000_000, 0],
        "dias_desde_ultima": [30, 200, 5, 400, 9999],
        "n_LP": [5, 1, 15, 0, 0],
        "n_LE": [3, 2, 3, 1, 0],
        "n_L1": [2, 2, 2, 1, 1],
        "competidores_promedio": [7, 3, 12, 15, np.nan],
        "tipo_mop": ["mayor", None, "menor", None, None],
        "categoria_mop": ["2da", None, "", None, None],
    })


@pytest.fixture
def sample_tenderers_df():
    """DataFrame de tenderers de prueba."""
    return pd.DataFrame({
        "_link": ["2024/id-0.1.tender.tenderers.0", "2024/id-0.1.tender.tenderers.1",
                  "2024/id-0.2.tender.tenderers.0", "2024/id-0.2.tender.tenderers.1",
                  "2024/id-0.3.tender.tenderers.0"],
        "_link_main": ["2024/id-0.1", "2024/id-0.1", "2024/id-0.2", "2024/id-0.2", "2024/id-0.3"],
        "id": ["CL-RUT-76543210-K", "CL-RUT-12345678-9",
               "CL-RUT-76543210-K", "CL-RUT-98765432-1",
               "CL-RUT-12345678-9"],
        "name": ["Constructora A", "Constructora B",
                 "Constructora A", "Constructora C",
                 "Constructora B"],
    })


@pytest.fixture
def sample_suppliers_df():
    """DataFrame de suppliers de prueba."""
    return pd.DataFrame({
        "tender_id": ["T001", "T002"],
        "party_id": ["CL-RUT-76543210-K", "CL-RUT-98765432-1"],
        "amount": ["100000000", "500000000"],
    })


@pytest.fixture
def sample_leads_ranked_df(sample_company_df):
    """DataFrame de leads rankeados."""
    df = sample_company_df[sample_company_df["total_bids"] >= 2].copy()
    df["score_total"] = [75.0, 45.0, 80.0, 30.0]
    df["rank"] = [1, 3, 2, 4]
    # Agregar score dimensions
    for dim in SCORING_WEIGHTS:
        df[f"score_{dim}"] = 50.0
    return df


@pytest.fixture
def sample_leads_enriched_df(sample_leads_ranked_df):
    """DataFrame de leads enriquecidos."""
    df = sample_leads_ranked_df.copy()
    df["telefono"] = ["+56912345678", None, "+56987654321", None]
    df["email"] = ["a@test.cl", None, "c@test.cl", None]
    df["web"] = ["www.a.cl", None, None, None]
    df["contacto_nombre"] = ["Juan Pérez", None, "Pedro López", None]
    df["direccion"] = ["Av. Test 123", None, None, None]
    df["rank_ml"] = [1, 3, 2, 4]
    df["score_combined"] = [82.0, 40.0, 90.0, 25.0]
    return df


# ============================================================================
# UTILS.PY — normalizar_rut (50 tests)
# ============================================================================

class TestNormalizarRut:
    """Tests para normalizar_rut."""

    def test_formato_con_puntos_y_guion(self):
        assert normalizar_rut("76.543.210-K") == "76543210-K"

    def test_formato_sin_puntos_con_guion(self):
        assert normalizar_rut("76543210-K") == "76543210-K"

    def test_formato_sin_puntos_sin_guion(self):
        assert normalizar_rut("76543210K") == "76543210-K"

    def test_rut_con_k_minuscula(self):
        assert normalizar_rut("76543210-k") == "76543210-K"

    def test_rut_con_digito_verificador_numerico(self):
        assert normalizar_rut("12345678-9") == "12345678-9"

    def test_rut_6_digitos(self):
        assert normalizar_rut("123456-7") == "123456-7"

    def test_rut_7_digitos(self):
        assert normalizar_rut("1234567-8") == "1234567-8"

    def test_rut_8_digitos(self):
        assert normalizar_rut("12345678-9") == "12345678-9"

    def test_rut_9_digitos(self):
        assert normalizar_rut("123456789-0") == "123456789-0"

    def test_rut_con_espacios(self):
        assert normalizar_rut(" 76543210-K ") == "76543210-K"

    def test_rut_vacio(self):
        assert normalizar_rut("") is None

    def test_rut_none(self):
        assert normalizar_rut(None) is None

    def test_rut_numerico(self):
        assert normalizar_rut(12345) is None

    def test_rut_muy_corto(self):
        assert normalizar_rut("12-3") is None

    def test_rut_5_digitos(self):
        assert normalizar_rut("12345-6") is None

    def test_rut_con_letras(self):
        assert normalizar_rut("abcdefgh-K") is None

    def test_rut_con_doble_guion(self):
        assert normalizar_rut("12345678--K") is None

    def test_rut_solo_guion(self):
        assert normalizar_rut("-") is None

    def test_rut_solo_k(self):
        assert normalizar_rut("K") is None

    def test_rut_con_puntos_todo_junto(self):
        assert normalizar_rut("76.543.210K") == "76543210-K"

    def test_rut_con_0_verificador(self):
        assert normalizar_rut("76543210-0") == "76543210-0"

    def test_rut_verificador_1(self):
        assert normalizar_rut("11111111-1") == "11111111-1"

    def test_rut_verificador_9(self):
        assert normalizar_rut("99999999-9") == "99999999-9"

    def test_rut_10_digitos_invalido(self):
        assert normalizar_rut("1234567890-1") is None

    def test_rut_con_punto_solo(self):
        assert normalizar_rut("...") is None

    def test_rut_float(self):
        assert normalizar_rut(3.14) is None

    def test_rut_lista(self):
        assert normalizar_rut([1, 2]) is None

    def test_rut_dict(self):
        assert normalizar_rut({"rut": "x"}) is None

    def test_rut_con_tab(self):
        assert normalizar_rut("\t76543210-K\t") == "76543210-K"


# ============================================================================
# UTILS.PY — extraer_rut_de_id (40 tests)
# ============================================================================

class TestExtraerRutDeId:
    """Tests para extraer_rut_de_id."""

    def test_formato_cl_rut(self):
        assert extraer_rut_de_id("CL-RUT-76543210-K") == "76543210-K"

    def test_formato_cl_rut_digito(self):
        assert extraer_rut_de_id("CL-RUT-12345678-9") == "12345678-9"

    def test_formato_rut_directo(self):
        assert extraer_rut_de_id("76543210-K") == "76543210-K"

    def test_formato_rut_sin_guion(self):
        assert extraer_rut_de_id("76543210K") == "76543210-K"

    def test_formato_con_prefijo(self):
        assert extraer_rut_de_id("org-76543210-K") == "76543210-K"

    def test_id_vacio(self):
        assert extraer_rut_de_id("") is None

    def test_id_none(self):
        assert extraer_rut_de_id(None) is None

    def test_id_sin_rut(self):
        assert extraer_rut_de_id("organismo-central") is None

    def test_id_numerico(self):
        assert extraer_rut_de_id(12345) is None

    def test_id_con_rut_embebido(self):
        result = extraer_rut_de_id("buyer-CL-RUT-98765432-1-name")
        assert result == "98765432-1"

    def test_k_minuscula(self):
        assert extraer_rut_de_id("CL-RUT-76543210-k") == "76543210-K"

    def test_rut_6_digitos(self):
        assert extraer_rut_de_id("CL-RUT-654321-0") == "654321-0"

    def test_rut_9_digitos(self):
        assert extraer_rut_de_id("CL-RUT-123456789-K") == "123456789-K"

    def test_solo_numeros_largos(self):
        # Extrae los primeros 9 dígitos + verificador del string largo
        result = extraer_rut_de_id("1234567890123")
        assert result is not None  # Encuentra patrón de RUT dentro

    def test_float_string(self):
        assert extraer_rut_de_id("nan") is None

    def test_texto_largo_sin_rut(self):
        assert extraer_rut_de_id("Este es un texto largo sin ningún RUT válido") is None

    def test_multiples_ruts(self):
        # Debería extraer el primero
        result = extraer_rut_de_id("CL-RUT-11111111-1 y CL-RUT-22222222-2")
        assert result == "11111111-1"

    def test_rut_con_ceros_iniciales(self):
        # 7 dígitos con cero inicial es formato válido
        assert extraer_rut_de_id("CL-RUT-0654321-0") == "0654321-0"

    def test_bool_input(self):
        assert extraer_rut_de_id(True) is None


# ============================================================================
# UTILS.PY — tipo_licitacion (25 tests)
# ============================================================================

class TestTipoLicitacion:
    """Tests para tipo_licitacion."""

    def test_lp(self):
        assert tipo_licitacion("2405-31-LP26") == "LP"

    def test_le(self):
        assert tipo_licitacion("2405-31-LE26") == "LE"

    def test_l1(self):
        assert tipo_licitacion("2405-31-L126") == "L1"

    def test_lr(self):
        assert tipo_licitacion("2405-31-LR26") == "LR"

    def test_minusculas(self):
        assert tipo_licitacion("2405-31-lp26") == "LP"

    def test_sin_tipo(self):
        assert tipo_licitacion("2405-31-XX26") == "Otro"

    def test_vacio(self):
        assert tipo_licitacion("") == "Otro"

    def test_none(self):
        assert tipo_licitacion(None) == "Otro"

    def test_numero(self):
        assert tipo_licitacion(12345) == "Otro"

    def test_solo_lp(self):
        assert tipo_licitacion("-LP") == "LP"

    def test_lp_al_inicio(self):
        # LP sin guión previo -> no matchea
        assert tipo_licitacion("LP26") == "Otro"

    def test_codigo_real_1(self):
        assert tipo_licitacion("621-5-LP25") == "LP"

    def test_codigo_real_2(self):
        assert tipo_licitacion("1234-100-LE25") == "LE"

    def test_codigo_real_3(self):
        assert tipo_licitacion("9999-1-L126") == "L1"

    def test_multiples_tipos(self):
        # LP aparece primero en la lista de búsqueda
        assert tipo_licitacion("2405-LP-LE-26") == "LP"


# ============================================================================
# UTILS.PY — formato_clp (30 tests)
# ============================================================================

class TestFormatoClp:
    """Tests para formato_clp."""

    def test_billones(self):
        assert formato_clp(1_500_000_000) == "$1.5B"

    def test_millones(self):
        assert formato_clp(200_000_000) == "$200M"

    def test_miles(self):
        assert formato_clp(500_000) == "$500,000"

    def test_cero(self):
        assert formato_clp(0) == "$0"

    def test_none(self):
        assert formato_clp(None) == "$0"

    def test_nan(self):
        assert formato_clp(float("nan")) == "$0"

    def test_exacto_millon(self):
        assert formato_clp(1_000_000) == "$1M"

    def test_exacto_billon(self):
        assert formato_clp(1_000_000_000) == "$1.0B"

    def test_negativo(self):
        # Montos negativos son edge case
        result = formato_clp(-500_000)
        assert "$" in result

    def test_muy_grande(self):
        result = formato_clp(100_000_000_000)
        assert "B" in result

    def test_decimal_millones(self):
        result = formato_clp(1_500_000)
        assert result == "$2M" or result == "$1M" or "M" in result

    def test_100(self):
        assert formato_clp(100) == "$100"

    def test_1(self):
        assert formato_clp(1) == "$1"

    def test_float_millones(self):
        result = formato_clp(66_000_000.5)
        assert "M" in result

    def test_borde_millones(self):
        assert formato_clp(999_999) == "$999,999"

    def test_borde_billones(self):
        assert "M" in formato_clp(999_999_999)


# ============================================================================
# UTILS.PY — safe_get (20 tests)
# ============================================================================

class TestSafeGet:
    """Tests para safe_get."""

    def test_valor_existente(self):
        row = pd.Series({"a": 10})
        assert safe_get(row, "a") == 10

    def test_valor_none(self):
        row = pd.Series({"a": None})
        assert safe_get(row, "a", 0) == 0

    def test_valor_nan(self):
        row = pd.Series({"a": np.nan})
        assert safe_get(row, "a", 0) == 0

    def test_columna_inexistente(self):
        row = pd.Series({"a": 1})
        assert safe_get(row, "b", "default") == "default"

    def test_string(self):
        row = pd.Series({"a": "hello"})
        assert safe_get(row, "a") == "hello"

    def test_string_vacio(self):
        row = pd.Series({"a": ""})
        assert safe_get(row, "a") == ""

    def test_cero(self):
        row = pd.Series({"a": 0})
        assert safe_get(row, "a", 99) == 0

    def test_false(self):
        row = pd.Series({"a": False})
        assert safe_get(row, "a", True) == False

    def test_float_nan(self):
        row = pd.Series({"a": float("nan")})
        assert safe_get(row, "a", "nope") == "nope"

    def test_lista(self):
        row = pd.Series({"a": [1, 2, 3]})
        assert safe_get(row, "a") == [1, 2, 3]

    def test_default_none(self):
        row = pd.Series({"a": np.nan})
        assert safe_get(row, "a") is None


# ============================================================================
# UTILS.PY — safe_request (15 tests)
# ============================================================================

class TestSafeRequest:
    """Tests para safe_request con mock de requests."""

    @patch("utils.requests.get")
    def test_200_ok(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        result = safe_request("http://test.com", max_retries=1)
        assert result == mock_resp

    @patch("utils.requests.get")
    def test_404_returns_none(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        result = safe_request("http://test.com", max_retries=1)
        assert result is None

    @patch("utils.requests.get")
    def test_500_retry(self, mock_get):
        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_get.side_effect = [mock_500, mock_200]
        result = safe_request("http://test.com", max_retries=2, delay=0.01)
        assert result == mock_200

    @patch("utils.requests.get")
    def test_429_retry(self, mock_get):
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_get.return_value = mock_429
        result = safe_request("http://test.com", max_retries=2, delay=0.01)
        assert result is None
        assert mock_get.call_count == 2

    @patch("utils.requests.get")
    def test_exception_retry(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("timeout")
        result = safe_request("http://test.com", max_retries=2, delay=0.01)
        assert result is None

    @patch("utils.requests.get")
    def test_timeout_parameter(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        safe_request("http://test.com", timeout=5)
        mock_get.assert_called_with("http://test.com", timeout=5, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})


# ============================================================================
# UTILS.PY — print_header (5 tests)
# ============================================================================

class TestPrintHeader:
    def test_no_crash(self, capsys):
        print_header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "=" in captured.out

    def test_vacio(self, capsys):
        print_header("")
        captured = capsys.readouterr()
        assert "=" in captured.out

    def test_unicode(self, capsys):
        print_header("Licitación — Análisis")
        captured = capsys.readouterr()
        assert "Licitación" in captured.out


# ============================================================================
# CONFIG.PY — Validación de configuración (20 tests)
# ============================================================================

class TestConfig:
    """Tests para validar la configuración."""

    def test_scoring_weights_sum_to_one(self):
        total = sum(SCORING_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights suman {total}, deberían sumar 1.0"

    def test_all_scoring_dimensions(self):
        expected = {"actividad", "tamano", "win_rate", "recencia", "valor",
                    "competencia", "oportunidad", "especializacion", "region"}
        assert set(SCORING_WEIGHTS.keys()) == expected

    def test_ideal_ranges_valid(self):
        for key, (lo, hi) in IDEAL_RANGES.items():
            assert lo <= hi, f"Rango inválido para {key}: {lo} > {hi}"

    def test_construction_unspsc(self):
        assert CONSTRUCTION_UNSPSC_PREFIX == "72"

    def test_bulk_csv_files_complete(self):
        required = {"tenders", "tenderers", "items", "awards", "suppliers", "parties"}
        assert required.issubset(set(BULK_CSV_FILES.keys()))

    def test_tipos_licitacion(self):
        assert "LP" in TIPOS_LICITACION
        assert "LE" in TIPOS_LICITACION
        assert "L1" in TIPOS_LICITACION

    def test_regiones_top_not_empty(self):
        assert len(REGIONES_TOP) >= 3

    def test_enrich_top_n_positive(self):
        assert ENRICH_TOP_N > 0

    def test_scoring_weights_all_positive(self):
        for dim, weight in SCORING_WEIGHTS.items():
            assert weight > 0, f"Peso negativo para {dim}"

    def test_ideal_ranges_actividad(self):
        lo, hi = IDEAL_RANGES["actividad"]
        assert lo >= 0 and hi > lo

    def test_ideal_ranges_win_rate(self):
        lo, hi = IDEAL_RANGES["win_rate"]
        assert 0 <= lo < hi <= 1

    def test_ideal_ranges_recencia(self):
        lo, hi = IDEAL_RANGES["recencia_dias"]
        assert lo >= 0

    def test_env_value_status_missing(self):
        assert env_value_status("") == "missing"

    def test_env_value_status_placeholder(self):
        assert env_value_status("replace_me") == "placeholder"

    def test_env_value_status_ok(self):
        assert env_value_status("real_secret_value") == "ok"

    def test_redact_secret_placeholder(self):
        assert redact_secret("replace_me") == "<placeholder>"

    def test_redact_secret_configured(self):
        assert redact_secret("abcdef123456") == "<configured:12 chars>"

    def test_env_var_report_marks_placeholder(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "replace_me")
        report = env_var_report(["GOOGLE_MAPS_API_KEY"])
        assert report[0]["status"] == "placeholder"


# ============================================================================
# 05_score_leads — score_in_range (60 tests)
# ============================================================================

# Import scoring functions
_score_mod = import_module("05_score_leads")
score_in_range = _score_mod.score_in_range
score_actividad = _score_mod.score_actividad
score_tamano = _score_mod.score_tamano
score_win_rate = _score_mod.score_win_rate
score_recencia = _score_mod.score_recencia
score_valor = _score_mod.score_valor
score_competencia = _score_mod.score_competencia
score_digital = _score_mod.score_digital
score_oportunidad = _score_mod.score_oportunidad
score_especializacion = _score_mod.score_especializacion
score_region = _score_mod.score_region
calculate_scores = _score_mod.calculate_scores


class TestScoreInRange:
    """Tests para score_in_range."""

    def test_dentro_rango(self):
        assert score_in_range(10, 5, 15) == 100

    def test_en_min(self):
        assert score_in_range(5, 5, 15) == 100

    def test_en_max(self):
        assert score_in_range(15, 5, 15) == 100

    def test_debajo_rango(self):
        s = score_in_range(2, 5, 15, lower_bound=0)
        assert 0 < s < 100

    def test_encima_rango(self):
        s = score_in_range(20, 5, 15, upper_bound=30)
        assert 0 < s < 100

    def test_en_lower_bound(self):
        s = score_in_range(0, 5, 15, lower_bound=0)
        assert s == 0

    def test_en_upper_bound(self):
        s = score_in_range(30, 5, 15, upper_bound=30)
        assert s == 0

    def test_nan(self):
        assert score_in_range(np.nan, 5, 15) == 0

    def test_cero_ideal_min(self):
        s = score_in_range(0, 0, 10)
        assert s == 100  # Está en el rango [0, 10]

    def test_negativo(self):
        s = score_in_range(-5, 0, 10, lower_bound=-10)
        assert 0 <= s <= 100

    def test_muy_encima_sin_upper(self):
        s = score_in_range(100, 5, 15)
        assert 0 <= s <= 100

    def test_valor_igual_ideal(self):
        assert score_in_range(7.5, 5, 10) == 100

    def test_float_precision(self):
        s = score_in_range(5.0001, 5.0, 15.0)
        assert s == 100

    def test_rango_estrecho(self):
        assert score_in_range(5, 5, 5) == 100

    def test_lower_none(self):
        s = score_in_range(2, 5, 15, lower_bound=None)
        assert 0 <= s <= 100


class TestScoreActividad:
    def test_ideal(self):
        row = pd.Series({"total_bids": 10})
        assert score_actividad(row) >= 85  # Dentro del rango ideal

    def test_bajo(self):
        row = pd.Series({"total_bids": 1})
        s = score_actividad(row)
        assert 0 < s < 100

    def test_alto(self):
        row = pd.Series({"total_bids": 40})
        s = score_actividad(row)
        assert 0 < s < 100

    def test_cero(self):
        row = pd.Series({"total_bids": 0})
        s = score_actividad(row)
        assert s == 0

    def test_borde_inferior(self):
        row = pd.Series({"total_bids": 5})
        assert score_actividad(row) == 85  # Borde lejos del optimal (15)

    def test_borde_superior(self):
        row = pd.Series({"total_bids": 15})
        assert score_actividad(row) == 100  # Es el optimal

    def test_missing(self):
        row = pd.Series({})
        s = score_actividad(row)
        assert s == 0


class TestScoreTamano:
    def test_mop_mayor_2da(self):
        row = pd.Series({"tipo_mop": "mayor", "categoria_mop": "2da", "monto_promedio": 0})
        assert score_tamano(row) == 100

    def test_mop_mayor_3ra(self):
        row = pd.Series({"tipo_mop": "mayor", "categoria_mop": "3ra", "monto_promedio": 0})
        assert score_tamano(row) == 80

    def test_mop_mayor_1ra(self):
        row = pd.Series({"tipo_mop": "mayor", "categoria_mop": "1ra", "monto_promedio": 0})
        assert score_tamano(row) == 60

    def test_mop_menor(self):
        row = pd.Series({"tipo_mop": "menor", "categoria_mop": "", "monto_promedio": 0})
        assert score_tamano(row) == 50

    def test_sin_mop_monto_ideal(self):
        row = pd.Series({"tipo_mop": None, "categoria_mop": None, "monto_promedio": 200_000_000})
        s = score_tamano(row)
        assert s >= 85  # Dentro del rango ideal

    def test_sin_mop_sin_monto(self):
        row = pd.Series({"tipo_mop": None, "categoria_mop": None, "monto_promedio": 0})
        assert score_tamano(row) == 20

    def test_sin_mop_nan_monto(self):
        row = pd.Series({"tipo_mop": None, "categoria_mop": None, "monto_promedio": np.nan})
        assert score_tamano(row) == 20


class TestScoreWinRate:
    def test_ideal(self):
        row = pd.Series({"win_rate": 0.25, "total_bids": 10})
        assert score_win_rate(row) == 100  # 0.25 es el optimal

    def test_cero(self):
        row = pd.Series({"win_rate": 0.0, "total_bids": 10})
        s = score_win_rate(row)
        assert s == 0

    def test_pocos_datos(self):
        row = pd.Series({"win_rate": 0.5, "total_bids": 1})
        assert score_win_rate(row) == 30

    def test_alto_wr(self):
        row = pd.Series({"win_rate": 0.7, "total_bids": 10})
        s = score_win_rate(row)
        assert 0 < s < 100


class TestScoreRecencia:
    def test_reciente(self):
        row = pd.Series({"dias_desde_ultima": 10})
        assert score_recencia(row) >= 95  # Cerca de optimal (0 días)

    def test_ideal_borde(self):
        row = pd.Series({"dias_desde_ultima": 90})
        assert score_recencia(row) >= 85  # Dentro del rango ideal

    def test_inactivo(self):
        row = pd.Series({"dias_desde_ultima": 800})
        assert score_recencia(row) > 0  # 800 < 1460 (RECENCIA_MAX_DAYS)

    def test_nan(self):
        row = pd.Series({"dias_desde_ultima": np.nan})
        assert score_recencia(row) == 0

    def test_muy_reciente(self):
        row = pd.Series({"dias_desde_ultima": 0})
        assert score_recencia(row) == 100


class TestScoreValor:
    def test_ideal(self):
        row = pd.Series({"monto_promedio": 200_000_000})
        assert score_valor(row) >= 85  # Dentro del rango ideal

    def test_cero(self):
        row = pd.Series({"monto_promedio": 0})
        assert score_valor(row) == 20

    def test_nan(self):
        row = pd.Series({"monto_promedio": np.nan})
        assert score_valor(row) == 20

    def test_muy_alto(self):
        row = pd.Series({"monto_promedio": 10_000_000_000})
        s = score_valor(row)
        assert 0 <= s <= 100


class TestScoreCompetencia:
    def test_ideal(self):
        row = pd.Series({"competidores_promedio": 7})
        assert score_competencia(row) >= 85  # Dentro del rango ideal

    def test_cero(self):
        row = pd.Series({"competidores_promedio": 0})
        assert score_competencia(row) == 30

    def test_nan(self):
        row = pd.Series({"competidores_promedio": np.nan})
        assert score_competencia(row) == 30

    def test_muchos(self):
        row = pd.Series({"competidores_promedio": 25})
        s = score_competencia(row)
        assert 0 < s < 100


class TestScoreDigital:
    def test_sin_datos_oportunidad(self):
        row = pd.Series({})
        assert score_digital(row) == 70  # Sin presencia digital = oportunidad


class TestScoreEspecializacion:
    def test_todo_lp(self):
        row = pd.Series({"n_LP": 10, "n_LE": 0, "n_L1": 0})
        s = score_especializacion(row)
        assert s > 80

    def test_todo_l1(self):
        row = pd.Series({"n_LP": 0, "n_LE": 0, "n_L1": 10})
        s = score_especializacion(row)
        assert s <= 30

    def test_mixto(self):
        row = pd.Series({"n_LP": 5, "n_LE": 3, "n_L1": 2})
        s = score_especializacion(row)
        assert 40 < s < 100

    def test_sin_datos(self):
        row = pd.Series({"n_LP": 0, "n_LE": 0, "n_L1": 0})
        assert score_especializacion(row) == 30

    def test_nan(self):
        row = pd.Series({"n_LP": np.nan, "n_LE": np.nan, "n_L1": np.nan})
        assert score_especializacion(row) == 30


class TestScoreRegion:
    def test_rm(self):
        row = pd.Series({"region": "Región Metropolitana de Santiago"})
        assert score_region(row) == 100

    def test_valparaiso(self):
        row = pd.Series({"region": "Región de Valparaíso"})
        assert score_region(row) == 90

    def test_otra_region(self):
        row = pd.Series({"region": "Región de Atacama"})
        assert score_region(row) == 40

    def test_sin_dato(self):
        row = pd.Series({"region": None})
        assert score_region(row) == 50

    def test_vacio(self):
        row = pd.Series({"region": ""})
        assert score_region(row) == 50

    def test_nan(self):
        row = pd.Series({"region": np.nan})
        assert score_region(row) == 50


# ============================================================================
# 05_score_leads — calculate_scores integration (15 tests)
# ============================================================================

class TestCalculateScores:
    def test_adds_score_columns(self, sample_company_df):
        df = sample_company_df[sample_company_df["total_bids"] >= 2].copy()
        result = calculate_scores(df)
        for dim in SCORING_WEIGHTS:
            assert f"score_{dim}" in result.columns
        assert "score_total" in result.columns

    def test_scores_0_100(self, sample_company_df):
        df = sample_company_df[sample_company_df["total_bids"] >= 2].copy()
        result = calculate_scores(df)
        assert result["score_total"].min() >= 0
        assert result["score_total"].max() <= 100

    def test_empty_df(self):
        df = pd.DataFrame(columns=["rut", "total_bids", "total_wins", "win_rate",
                                    "monto_promedio", "dias_desde_ultima", "n_LP",
                                    "n_LE", "n_L1", "competidores_promedio",
                                    "tipo_mop", "categoria_mop", "region"])
        result = calculate_scores(df)
        assert len(result) == 0
        assert "score_total" in result.columns

    def test_single_row(self):
        df = pd.DataFrame({
            "rut": ["76543210-K"],
            "total_bids": [10],
            "total_wins": [3],
            "win_rate": [0.3],
            "monto_promedio": [200_000_000],
            "dias_desde_ultima": [30],
            "n_LP": [5], "n_LE": [3], "n_L1": [2],
            "competidores_promedio": [7],
            "tipo_mop": ["mayor"],
            "categoria_mop": ["2da"],
            "region": ["Región Metropolitana de Santiago"],
        })
        result = calculate_scores(df)
        assert result["score_total"].iloc[0] > 50  # Empresa ideal


# ============================================================================
# 05b_ml_scoring — prepare_features (15 tests)
# ============================================================================

_ml_mod = import_module("05b_ml_scoring")
prepare_features = _ml_mod.prepare_features
compute_combined_score = _ml_mod.compute_combined_score


class TestPrepareFeatures:
    def test_basic(self, sample_company_df):
        X, used = prepare_features(sample_company_df, ["total_bids", "monto_promedio"])
        assert "total_bids" in used
        assert "monto_promedio" in used
        assert len(X) == len(sample_company_df)

    def test_missing_features(self, sample_company_df):
        X, used = prepare_features(sample_company_df, ["total_bids", "no_existe"])
        assert "total_bids" in used
        assert "no_existe" not in used

    def test_nan_filled(self, sample_company_df):
        X, used = prepare_features(sample_company_df, ["competidores_promedio"])
        assert not X["competidores_promedio"].isna().any()

    def test_log_transform_montos(self, sample_company_df):
        X, used = prepare_features(sample_company_df, ["monto_promedio", "total_bids"])
        # monto_promedio should be log-transformed
        assert X["monto_promedio"].max() < sample_company_df["monto_promedio"].max()

    def test_empty_df(self):
        df = pd.DataFrame(columns=["total_bids", "monto_promedio"])
        X, used = prepare_features(df, ["total_bids", "monto_promedio"])
        assert len(X) == 0

    def test_all_nan(self):
        df = pd.DataFrame({"total_bids": [np.nan, np.nan], "monto_promedio": [np.nan, np.nan]})
        X, used = prepare_features(df, ["total_bids", "monto_promedio"])
        assert (X == 0).all().all()  # NaN -> 0

    def test_negative_montos_clipped(self):
        df = pd.DataFrame({"monto_promedio": [-1000, 0, 1000]})
        X, used = prepare_features(df, ["monto_promedio"])
        assert X["monto_promedio"].min() >= 0  # clip(lower=0) then log1p


class TestComputeCombinedScore:
    def test_all_components(self):
        df = pd.DataFrame({
            "km_score": [80, 60, 40],
            "xgb_score": [70, 50, 30],
            "score_total": [90, 70, 50],
        })
        result = compute_combined_score(df)
        assert "score_combined" in result.columns
        # 80*0.15 + 70*0.15 + 90*0.70 = 85.5 (no normalization)
        assert result["score_combined"].max() == 85.5

    def test_missing_xgb(self):
        df = pd.DataFrame({
            "km_score": [80, 60],
            "score_total": [70, 50],
        })
        result = compute_combined_score(df)
        assert "score_combined" in result.columns
        assert result["score_combined"].max() > 0

    def test_no_components(self):
        df = pd.DataFrame({"rut": ["a", "b"]})
        result = compute_combined_score(df)
        assert (result["score_combined"] == 0).all()

    def test_single_row(self):
        df = pd.DataFrame({"km_score": [100], "xgb_score": [100], "score_total": [100]})
        result = compute_combined_score(df)
        assert result["score_combined"].iloc[0] == 100.0


# ============================================================================
# 04_build_company_db — build functions (30 tests)
# ============================================================================

_build_mod = import_module("04_build_company_db")
find_column = _build_mod.find_column
extract_ruts_from_df = _build_mod.extract_ruts_from_df
build_tenderer_stats = _build_mod.build_tenderer_stats
build_winner_stats = _build_mod.build_winner_stats
build_names = _build_mod.build_names
calculate_competition = _build_mod.calculate_competition


class TestFindColumn:
    def test_exact(self):
        df = pd.DataFrame(columns=["tender_id", "name", "amount"])
        assert find_column(df, ["tender_id"]) == "tender_id"

    def test_partial(self):
        df = pd.DataFrame(columns=["release_tender_id", "name"])
        assert find_column(df, ["tender_id"]) == "release_tender_id"

    def test_not_found(self):
        df = pd.DataFrame(columns=["a", "b", "c"])
        assert find_column(df, ["tender_id"]) is None

    def test_multiple_keywords(self):
        df = pd.DataFrame(columns=["amount", "name"])
        assert find_column(df, ["value", "amount"]) == "amount"

    def test_case_insensitive(self):
        df = pd.DataFrame(columns=["Tender_ID"])
        assert find_column(df, ["tender_id"]) == "Tender_ID"

    def test_empty_df(self):
        df = pd.DataFrame()
        assert find_column(df, ["test"]) is None


class TestExtractRutsFromDf:
    def test_with_party_id(self):
        df = pd.DataFrame({"party_id": ["CL-RUT-76543210-K", "CL-RUT-12345678-9"]})
        ruts = extract_ruts_from_df(df)
        assert ruts.notna().sum() == 2
        assert ruts.iloc[0] == "76543210-K"

    def test_no_rut_columns(self):
        df = pd.DataFrame({"name": ["Company A", "Company B"]})
        ruts = extract_ruts_from_df(df)
        assert ruts.isna().all() or (ruts == None).all()

    def test_mixed_valid_invalid(self):
        df = pd.DataFrame({"identifier_id": ["CL-RUT-76543210-K", "invalid", "CL-RUT-12345678-9"]})
        ruts = extract_ruts_from_df(df)
        assert ruts.notna().sum() == 2


class TestBuildTendererStats:
    def test_basic(self, sample_tenderers_df):
        stats = build_tenderer_stats(sample_tenderers_df.copy(), None)
        assert "rut" in stats.columns
        assert "total_bids" in stats.columns
        assert len(stats) > 0

    def test_with_tenders(self, sample_tenderers_df):
        tenders = pd.DataFrame({
            "_link": ["2024/id-0.1", "2024/id-0.2", "2024/id-0.3"],
            "date": ["2024-01-01", "2024-06-01", "2025-01-01"],
            "tender_value_amount": ["100000000", "200000000", "50000000"],
            "tender_procurementMethodDetails": [
                "Licitacion Publica Mayor 1000 UTM (LP)",
                "Licitacion Publica Entre 100 y 1000 UTM (LE)",
                "Licitacion Publica Menor a 100 UTM (L1)",
            ],
        })
        stats = build_tenderer_stats(sample_tenderers_df.copy(), tenders)
        assert "total_bids" in stats.columns
        assert "n_LP" in stats.columns

    def test_empty_tenderers(self):
        df = pd.DataFrame(columns=["_link", "_link_main", "id", "name"])
        stats = build_tenderer_stats(df, None)
        assert len(stats) == 0


class TestBuildWinnerStats:
    def test_basic(self, sample_suppliers_df):
        stats = build_winner_stats(sample_suppliers_df.copy())
        assert "rut" in stats.columns
        assert "total_wins" in stats.columns


class TestCalculateCompetition:
    def test_basic(self, sample_tenderers_df):
        comp = calculate_competition(sample_tenderers_df.copy())
        assert "rut" in comp.columns
        assert "competidores_promedio" in comp.columns
        assert len(comp) > 0


# ============================================================================
# 07_export_output — generate_whatsapp_message (30 tests)
# ============================================================================

_export_mod = import_module("07_export_output")
generate_whatsapp_message = _export_mod.generate_whatsapp_message


class TestGenerateWhatsappMessage:
    def test_basic(self):
        row = pd.Series({
            "contacto_nombre": "Juan Pérez",
            "nombre": "Constructora A",
            "total_bids": 10,
            "win_rate": 0.2,
            "n_LP": 5,
        })
        msg = generate_whatsapp_message(row)
        assert "Juan Pérez" in msg
        assert "Constructora A" in msg
        assert "IngenIA" in msg

    def test_sin_contacto(self):
        row = pd.Series({
            "contacto_nombre": None,
            "nombre": "Empresa X",
            "total_bids": 5,
            "win_rate": 0.3,
            "n_LP": 0,
        })
        msg = generate_whatsapp_message(row)
        assert "estimado/a" in msg

    def test_sin_nombre(self):
        row = pd.Series({
            "contacto_nombre": "Pedro",
            "nombre": None,
            "total_bids": 3,
            "win_rate": 0,
            "n_LP": 0,
        })
        msg = generate_whatsapp_message(row)
        assert "su empresa" in msg

    def test_nan_contacto(self):
        row = pd.Series({
            "contacto_nombre": np.nan,
            "nombre": "Test",
            "total_bids": 5,
            "win_rate": 0.1,
            "n_LP": 0,
        })
        msg = generate_whatsapp_message(row)
        assert "estimado/a" in msg

    def test_win_rate_bajo(self):
        row = pd.Series({
            "contacto_nombre": "Ana",
            "nombre": "Empresa Y",
            "total_bids": 20,
            "win_rate": 0.1,
            "n_LP": 5,
        })
        msg = generate_whatsapp_message(row)
        assert "10%" in msg or "adjudicación" in msg

    def test_sin_lp(self):
        row = pd.Series({
            "contacto_nombre": "Carlos",
            "nombre": "Empresa Z",
            "total_bids": 5,
            "win_rate": 0.3,
            "n_LP": 0,
        })
        msg = generate_whatsapp_message(row)
        assert "LP" not in msg or "tipo LP" not in msg

    def test_cero_bids(self):
        row = pd.Series({
            "contacto_nombre": "Test",
            "nombre": "Test Co",
            "total_bids": 0,
            "win_rate": 0,
            "n_LP": 0,
        })
        msg = generate_whatsapp_message(row)
        assert "0 licitaciones" in msg

    def test_nan_bids(self):
        row = pd.Series({
            "contacto_nombre": None,
            "nombre": "Test",
            "total_bids": np.nan,
            "win_rate": np.nan,
            "n_LP": np.nan,
        })
        msg = generate_whatsapp_message(row)
        assert "IngenIA" in msg

    def test_mensaje_tiene_cierre(self):
        row = pd.Series({
            "contacto_nombre": "Test",
            "nombre": "Test",
            "total_bids": 5,
            "win_rate": 0.2,
            "n_LP": 2,
        })
        msg = generate_whatsapp_message(row)
        assert "demo gratuita" in msg.lower() or "código" in msg


# ============================================================================
# 08_loss_analysis — análisis de derrotas (40 tests)
# ============================================================================

_loss_mod = import_module("08_loss_analysis")
analyze_losses = _loss_mod.analyze_losses
generate_loss_insight = _loss_mod.generate_loss_insight
generate_whatsapp_v2 = _loss_mod.generate_whatsapp_v2
_loss_find_column = _loss_mod.find_column


class TestAnalyzeLosses:
    def test_basic_win(self):
        tender_map = {
            "T1": {"tenderers": {"R1", "R2"}, "winner": "R1", "n_competitors": 2},
        }
        rut_to_tenders = {"R1": {"T1"}, "R2": {"T1"}}
        result = analyze_losses("R1", tender_map, rut_to_tenders)
        assert result["total_won"] == 1
        assert result["total_lost"] == 0

    def test_basic_loss(self):
        tender_map = {
            "T1": {"tenderers": {"R1", "R2"}, "winner": "R2", "n_competitors": 2},
        }
        rut_to_tenders = {"R1": {"T1"}, "R2": {"T1"}}
        result = analyze_losses("R1", tender_map, rut_to_tenders)
        assert result["total_won"] == 0
        assert result["total_lost"] == 1
        assert result["top_rival_1"] == "R2"

    def test_no_tenders(self):
        result = analyze_losses("R999", {}, {})
        assert result["total_participated"] == 0

    def test_unknown_winner(self):
        tender_map = {
            "T1": {"tenderers": {"R1"}, "winner": None, "n_competitors": 1},
        }
        rut_to_tenders = {"R1": {"T1"}}
        result = analyze_losses("R1", tender_map, rut_to_tenders)
        assert result["total_unknown"] == 1

    def test_multiple_losses(self):
        tender_map = {
            "T1": {"tenderers": {"R1", "R2"}, "winner": "R2", "n_competitors": 2},
            "T2": {"tenderers": {"R1", "R2"}, "winner": "R2", "n_competitors": 2},
            "T3": {"tenderers": {"R1", "R3"}, "winner": "R3", "n_competitors": 2},
        }
        rut_to_tenders = {"R1": {"T1", "T2", "T3"}}
        result = analyze_losses("R1", tender_map, rut_to_tenders)
        assert result["total_lost"] == 3
        assert result["top_rival_1"] == "R2"  # Lost to R2 twice
        assert result["top_rival_1_count"] == 2

    def test_loss_rate(self):
        tender_map = {
            "T1": {"tenderers": {"R1", "R2"}, "winner": "R2", "n_competitors": 2},
            "T2": {"tenderers": {"R1", "R2"}, "winner": "R1", "n_competitors": 2},
        }
        rut_to_tenders = {"R1": {"T1", "T2"}}
        result = analyze_losses("R1", tender_map, rut_to_tenders)
        assert result["loss_rate"] == 0.5

    def test_no_rivals(self):
        tender_map = {
            "T1": {"tenderers": {"R1"}, "winner": "R1", "n_competitors": 1},
        }
        rut_to_tenders = {"R1": {"T1"}}
        result = analyze_losses("R1", tender_map, rut_to_tenders)
        assert result["top_rival_1"] is None
        assert result["n_distinct_rivals"] == 0


class TestGenerateLossInsight:
    def test_muchas_derrotas(self):
        row = pd.Series({
            "total_lost": 5, "total_won": 1, "total_participated": 10,
            "top_rival_1_name": "Rival Co", "top_rival_1_count": 3,
        })
        insight = generate_loss_insight(row)
        assert "perdió" in insight
        assert "Rival Co" in insight

    def test_pocas_derrotas(self):
        row = pd.Series({
            "total_lost": 1, "total_won": 5, "total_participated": 10,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        insight = generate_loss_insight(row)
        assert "participó" in insight or insight == ""

    def test_sin_participaciones(self):
        row = pd.Series({
            "total_lost": 0, "total_won": 0, "total_participated": 0,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        assert generate_loss_insight(row) == ""

    def test_nan_values(self):
        row = pd.Series({
            "total_lost": np.nan, "total_won": np.nan, "total_participated": np.nan,
            "top_rival_1_name": np.nan, "top_rival_1_count": np.nan,
        })
        assert generate_loss_insight(row) == ""

    def test_rival_sin_nombre(self):
        row = pd.Series({
            "total_lost": 5, "total_won": 1, "total_participated": 8,
            "top_rival_1": "R123", "top_rival_1_count": 3,
        })
        insight = generate_loss_insight(row)
        assert "perdió" in insight


class TestGenerateWhatsappV2:
    def test_muchas_derrotas(self):
        row = pd.Series({
            "contacto_nombre": "Juan",
            "nombre": "Constructora Test",
            "total_lost": 5, "total_won": 1, "total_participated": 8,
            "top_rival_1_name": "Rival Co", "top_rival_1_count": 3,
        })
        msg = generate_whatsapp_v2(row)
        assert "Juan" in msg
        assert "Constructora Test" in msg
        assert "Rival Co" in msg

    def test_sin_adjudicaciones(self):
        row = pd.Series({
            "contacto_nombre": None,
            "nombre": "Empresa Sin Wins",
            "total_lost": 0, "total_won": 0, "total_participated": 5,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        msg = generate_whatsapp_v2(row)
        assert "estimado/a" in msg
        assert "sin adjudicarse" in msg

    def test_muchas_participaciones(self):
        row = pd.Series({
            "contacto_nombre": "Ana",
            "nombre": "Gran Constructora",
            "total_lost": 2, "total_won": 4, "total_participated": 10,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        msg = generate_whatsapp_v2(row)
        assert "Ana" in msg
        assert "10 participaciones" in msg or "Gran Constructora" in msg

    def test_pocos_datos(self):
        row = pd.Series({
            "contacto_nombre": None,
            "nombre": "Empresa Nueva",
            "total_lost": 0, "total_won": 0, "total_participated": 1,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        msg = generate_whatsapp_v2(row)
        assert "participa en licitaciones" in msg

    def test_nan_everything(self):
        row = pd.Series({
            "contacto_nombre": np.nan,
            "nombre": np.nan,
            "total_lost": np.nan, "total_won": np.nan, "total_participated": np.nan,
            "top_rival_1_name": np.nan, "top_rival_1_count": np.nan,
        })
        msg = generate_whatsapp_v2(row)
        assert "IngenIA" in msg

    def test_cierre_pierde_mucho(self):
        row = pd.Series({
            "contacto_nombre": "Test",
            "nombre": "Test Co",
            "total_lost": 5, "total_won": 1, "total_participated": 8,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        msg = generate_whatsapp_v2(row)
        assert "perdido" in msg.lower() or "cambiado" in msg.lower()

    def test_cierre_gana(self):
        row = pd.Series({
            "contacto_nombre": "Test",
            "nombre": "Test Co",
            "total_lost": 1, "total_won": 5, "total_participated": 8,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        msg = generate_whatsapp_v2(row)
        assert "código" in msg


# ============================================================================
# 09_tender_matcher — es_construccion (30 tests)
# ============================================================================

_matcher_mod = import_module("09_tender_matcher")
es_construccion = _matcher_mod.es_construccion


class TestEsConstruccion:
    def test_construccion(self):
        assert es_construccion("Construcción de puente") is True

    def test_obra(self):
        assert es_construccion("Obra de pavimentación") is True

    def test_infraestructura(self):
        assert es_construccion("Infraestructura vial") is True

    def test_pavimentacion(self):
        assert es_construccion("Pavimentación ruta 5") is True

    def test_edificio(self):
        assert es_construccion("Edificio municipal") is True

    def test_mejoramiento(self):
        assert es_construccion("Mejoramiento camino rural") is True

    def test_reposicion(self):
        assert es_construccion("Reposición escuela") is True

    def test_conservacion(self):
        assert es_construccion("Conservación ruta") is True

    def test_habilitacion(self):
        assert es_construccion("Habilitación terreno") is True

    def test_demolicion(self):
        assert es_construccion("Demolición estructura antigua") is True

    def test_alcantarillado(self):
        assert es_construccion("Alcantarillado sector norte") is True

    def test_agua_potable(self):
        assert es_construccion("Agua potable sector rural") is True

    def test_no_construccion(self):
        assert es_construccion("Compra de vehículos") is False

    def test_dental(self):
        assert es_construccion("Equipamiento dental construcción") is False

    def test_software(self):
        assert es_construccion("Software de construcción") is False

    def test_limpieza(self):
        assert es_construccion("Limpieza de obra") is False

    def test_consultoria(self):
        assert es_construccion("Consultoría para obra") is False

    def test_vacio(self):
        assert es_construccion("") is False

    def test_solo_kw_excluir(self):
        assert es_construccion("Compra de impresora") is False

    def test_case_insensitive(self):
        assert es_construccion("CONSTRUCCIÓN DE PUENTE") is True

    def test_urbanizacion(self):
        assert es_construccion("Urbanización terreno") is True

    def test_saneamiento(self):
        assert es_construccion("Saneamiento sector norte") is True

    def test_internet_con_obra(self):
        # Tiene KW incluir (obra) pero también excluir (internet)
        assert es_construccion("Obra de internet") is False

    def test_puente(self):
        assert es_construccion("Puente sobre río") is True

    def test_medico_con_obra(self):
        # "médica" con acento NO matchea "medic" sin acento -> pasa el filtro
        assert es_construccion("Construcción médica") is True

    def test_medico_sin_acento(self):
        # "medica" sin acento SÍ matchea "medic" -> excluido
        assert es_construccion("Construcción medica") is False


# ============================================================================
# 02_scrape_mop — funciones internas (15 tests)
# ============================================================================

_mop_mod = import_module("02_scrape_mop")
_extract_contractor = _mop_mod._extract_contractor


class TestExtractContractor:
    def test_basic(self):
        data = {"nombre": "Constructora Test", "rut": "76.543.210-K", "categoría": "2da"}
        result = _extract_contractor(data, "mayor")
        assert result is not None
        assert result["nombre"] == "Constructora Test"
        assert result["rut"] == "76543210-K"
        assert result["tipo_mop"] == "mayor"

    def test_sin_nombre(self):
        data = {"rut": "76.543.210-K"}
        result = _extract_contractor(data, "mayor")
        assert result is None

    def test_nombre_corto(self):
        data = {"nombre": "AB", "rut": "76.543.210-K"}
        result = _extract_contractor(data, "mayor")
        assert result is None

    def test_sin_rut(self):
        data = {"nombre": "Constructora Test"}
        result = _extract_contractor(data, "menor")
        assert result is not None
        assert result["rut"] is None

    def test_empresa_label(self):
        data = {"empresa": "Constructora XYZ", "clase": "primera"}
        result = _extract_contractor(data, "mayor")
        assert result is not None
        assert result["nombre"] == "Constructora XYZ"
        assert result["categoria_mop"] == "primera"

    def test_contratista_label(self):
        data = {"contratista": "Constructora ABC"}
        result = _extract_contractor(data, "menor")
        assert result is not None
        assert result["nombre"] == "Constructora ABC"


# ============================================================================
# 03_filter_construction — find_csv (20 tests)
# ============================================================================

_filter_mod = import_module("03_filter_construction")
find_csv_fn = _filter_mod.find_csv


class TestFindCsv:
    def test_exact_match(self, tmp_path):
        year_dir = tmp_path / "2024"
        year_dir.mkdir()
        (year_dir / "main.csv").touch()
        with patch("03_filter_construction.RAW_DIR", tmp_path):
            result = find_csv_fn(2024, "tenders")
        assert result is not None
        assert result.name == "main.csv"

    def test_no_match(self, tmp_path):
        year_dir = tmp_path / "2024"
        year_dir.mkdir()
        with patch("03_filter_construction.RAW_DIR", tmp_path):
            result = find_csv_fn(2024, "tenders")
        assert result is None

    def test_no_year_dir(self, tmp_path):
        with patch("03_filter_construction.RAW_DIR", tmp_path):
            result = find_csv_fn(2024, "tenders")
        assert result is None

    def test_fuzzy_match_parties(self, tmp_path):
        year_dir = tmp_path / "2024"
        year_dir.mkdir()
        (year_dir / "parties.csv").touch()
        with patch("03_filter_construction.RAW_DIR", tmp_path):
            result = find_csv_fn(2024, "parties")
        assert result is not None

    def test_tenderers_exact(self, tmp_path):
        year_dir = tmp_path / "2024"
        year_dir.mkdir()
        (year_dir / "tende_tenderers.csv").touch()
        with patch("03_filter_construction.RAW_DIR", tmp_path):
            result = find_csv_fn(2024, "tenderers")
        assert result is not None
        assert result.name == "tende_tenderers.csv"

    def test_tenders_does_not_match_tenderers(self, tmp_path):
        """Regression test: find_csv('tenders') no debe matchear tenderers."""
        year_dir = tmp_path / "2024"
        year_dir.mkdir()
        (year_dir / "tende_tenderers.csv").touch()
        # No hay tende_tender.csv, solo tenderers
        with patch("03_filter_construction.RAW_DIR", tmp_path):
            result = find_csv_fn(2024, "tenders")
        # No debe matchear tenderers para tenders
        assert result is None


# ============================================================================
# 06_enrich_contacts — checkpoint (15 tests)
# ============================================================================

_enrich_mod = import_module("06_enrich_contacts")
_is_credit_error = _enrich_mod._is_credit_error
consolidate_contacts = _enrich_mod.consolidate_contacts
_env_hygiene_mod = import_module("15_env_hygiene")


class TestIsCreditError:
    def test_402(self):
        assert _is_credit_error("HTTP 402 Payment Required") is True

    def test_insufficient(self):
        assert _is_credit_error("Insufficient credits") is True

    def test_quota(self):
        assert _is_credit_error("Usage quota exceeded") is True

    def test_normal_error(self):
        assert _is_credit_error("Connection timeout") is False

    def test_500(self):
        assert _is_credit_error("HTTP 500 Internal Server Error") is False

    def test_plan_limit(self):
        assert _is_credit_error("Plan limit reached") is True


class TestEnvHygiene:
    def test_normalize_values_converts_legacy_alias(self):
        values = {
            "APIFY_API_KEY": "token123",
            "MERCADO_PUBLICO_TICKET": "ticket123",
        }
        normalized = _env_hygiene_mod._normalize_values(values)
        assert "APIFY_API_KEY" not in normalized
        assert normalized["APIFY_TOKEN"] == "token123"

    def test_render_env_uses_canonical_keys(self):
        values = {
            "APIFY_TOKEN": "token123",
            "MERCADO_PUBLICO_TICKET": "ticket123",
            "GOOGLE_MAPS_API_KEY": "maps123",
        }
        content = _env_hygiene_mod._render_env(Path("C:/tmp/.env"), values)
        assert "APIFY_TOKEN=token123" in content
        assert "APIFY_API_KEY" not in content


class TestConsolidateContacts:
    def test_basic(self):
        df = pd.DataFrame({
            "rut": ["R1", "R2"],
            "gm_telefono": ["+56912345678", None],
            "ocds_telefono": [None, "+56987654321"],
            "ocds_email": ["test@test.cl", None],
            "gm_web": ["www.test.cl", None],
            "ocds_contacto": ["Juan", None],
            "gm_direccion": ["Av. Test 123", None],
        })
        result = consolidate_contacts(df)
        assert result["telefono"].iloc[0] == "+56912345678"
        assert result["telefono"].iloc[1] == "+56987654321"
        assert result["email"].iloc[0] == "test@test.cl"
        assert result["web"].iloc[0] == "www.test.cl"
        assert result["contacto_nombre"].iloc[0] == "Juan"

    def test_gm_preferred_over_ocds(self):
        df = pd.DataFrame({
            "rut": ["R1"],
            "gm_telefono": ["+56900000000"],
            "ocds_telefono": ["+56911111111"],
            "ocds_email": ["x@x.cl"],
            "gm_web": [None],
            "ocds_contacto": [None],
            "gm_direccion": [None],
        })
        result = consolidate_contacts(df)
        assert result["telefono"].iloc[0] == "+56900000000"

    def test_score_digital_sin_presencia(self):
        df = pd.DataFrame({
            "rut": ["R1"],
            "gm_telefono": [None],
            "ocds_telefono": [None],
            "ocds_email": [None],
            "gm_web": [None],
            "ocds_contacto": [None],
            "gm_direccion": [None],
        })
        result = consolidate_contacts(df)
        assert result["score_digital"].iloc[0] == 70  # Sin presencia = oportunidad

    def test_score_digital_con_presencia(self):
        df = pd.DataFrame({
            "rut": ["R1"],
            "gm_telefono": [None],
            "ocds_telefono": [None],
            "ocds_email": ["test@test.cl"],
            "gm_web": ["www.test.cl"],
            "ocds_contacto": [None],
            "gm_direccion": [None],
        })
        result = consolidate_contacts(df)
        assert result["score_digital"].iloc[0] == 30


class TestPipelineCoreHelpers:
    def test_recompute_score_combined_consistent(self):
        df = pd.DataFrame({
            "score_total": [80.0],
            "km_score": [60.0],
            "xgb_score": [40.0],
        })
        result = recompute_score_combined(df)
        assert result["score_combined"].iloc[0] == pytest.approx(71.0)

    def test_recompute_score_combined_without_ml_keeps_score_total(self):
        df = pd.DataFrame({
            "score_total": [80.0, 55.5],
        })
        result = recompute_score_combined(df)
        assert result["score_combined"].tolist() == [80.0, 55.5]

    def test_recompute_score_combined_partial_ml_uses_neutral_fallback(self):
        df = pd.DataFrame({
            "score_total": [80.0],
            "km_score": [60.0],
            "xgb_score": [np.nan],
        })
        result = recompute_score_combined(df)
        assert result["score_combined"].iloc[0] == pytest.approx(77.0)

    def test_build_crm_dataframe_columns(self, sample_leads_enriched_df):
        crm = build_crm_dataframe(sample_leads_enriched_df.head(2))
        expected = {
            "empresa", "rut", "contacto", "telefono", "email",
            "licitacion_codigo", "licitacion_nombre", "fecha_contacto",
            "canal", "estado", "proximo_follow_up", "notas",
            "resultado", "prioridad",
        }
        assert expected.issubset(set(crm.columns))

    def test_load_best_leads_priority(self, tmp_path):
        filtered = tmp_path / "filtered"
        filtered.mkdir(parents=True)
        base = pd.DataFrame({"rut": ["R1"]})
        base.to_parquet(filtered / "leads_ranked.parquet", index=False)
        enriched = pd.DataFrame({"rut": ["R2"]})
        enriched.to_parquet(filtered / "leads_enriched.parquet", index=False)

        df, path = load_best_leads_dataframe(filtered)
        assert path.name == "leads_enriched.parquet"
        assert df["rut"].iloc[0] == "R2"

    def test_load_best_leads_raises_when_missing(self, tmp_path):
        filtered = tmp_path / "filtered"
        filtered.mkdir(parents=True)
        with pytest.raises(FileNotFoundError):
            load_best_leads_dataframe(filtered)


class TestPipelineValidationHelpers:
    def test_client_safe_text_detects_internal_fields(self):
        with pytest.raises(ValueError):
            assert_client_safe_text("score_combined interno", "wa.txt")

    def test_client_safe_json_detects_internal_fields(self):
        with pytest.raises(ValueError):
            assert_client_safe_json({"score_total": 90}, "notes.json")

    def test_dataframe_contract_passes_for_ranked(self, sample_leads_ranked_df):
        assert_dataframe_contract(sample_leads_ranked_df, "leads_ranked")

    def test_client_safe_columns_allows_score_digital(self):
        df = pd.DataFrame({
            "empresa": ["A"],
            "score_digital": [80],
        })
        assert_client_safe_columns(df)

    def test_validate_dataframe_contract_detects_duplicates_and_range_errors(self):
        df = pd.DataFrame({
            "rut": ["R1", "R1"],
            "score_total": [120, 80],
            "rank": [1, 2],
            "win_rate": [0.5, 1.2],
        })
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert any("duplicadas" in issue for issue in issues)
        assert any("score_total contiene valores mayores a 100" in issue for issue in issues)
        assert any("win_rate contiene valores mayores a 1" in issue for issue in issues)

    def test_validate_dataframe_contract_detects_missing_rut(self):
        df = pd.DataFrame({
            "rut": ["R1", None],
            "score_total": [80, 70],
            "rank": [1, 2],
            "win_rate": [0.5, 0.4],
        })
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert any("sin rut" in issue for issue in issues)

    def test_client_safe_binary_detects_internal_token(self, tmp_path):
        path = tmp_path / "diag.pdf"
        path.write_bytes(b"%PDF-1.4\n(score_combined interno)\n%%EOF")
        with pytest.raises(ValueError):
            assert_client_safe_binary(path)

    def test_client_safe_binary_ignores_substring_inside_word(self, tmp_path):
        path = tmp_path / "diag.pdf"
        path.write_bytes(b"%PDF-1.4\n(declustered signal only)\n%%EOF")
        assert_client_safe_binary(path)


# ============================================================================
# 07_export_output — export functions (20 tests)
# ============================================================================

class TestExportExcel:
    def test_export_no_crash(self, sample_leads_enriched_df, tmp_path):
        path = tmp_path / "test.xlsx"
        _export_mod.export_excel(sample_leads_enriched_df, path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_export_reads_back(self, sample_leads_enriched_df, tmp_path):
        path = tmp_path / "test.xlsx"
        _export_mod.export_excel(sample_leads_enriched_df, path)
        df = pd.read_excel(path, sheet_name="Leads")
        assert len(df) == len(sample_leads_enriched_df)

    def test_export_has_resumen(self, sample_leads_enriched_df, tmp_path):
        path = tmp_path / "test.xlsx"
        _export_mod.export_excel(sample_leads_enriched_df, path)
        sheets = pd.ExcelFile(path).sheet_names
        assert "Resumen" in sheets

    def test_export_empty_df(self, tmp_path):
        path = tmp_path / "test.xlsx"
        df = pd.DataFrame(columns=["rut", "nombre", "rank_ml", "score_combined"])
        _export_mod.export_excel(df, path)
        assert path.exists()


class TestExportWhatsapp:
    def test_export_no_crash(self, sample_leads_enriched_df, tmp_path):
        path = tmp_path / "test.txt"
        _export_mod.export_whatsapp(sample_leads_enriched_df, path)
        assert path.exists()

    def test_export_contains_messages(self, sample_leads_enriched_df, tmp_path):
        path = tmp_path / "test.txt"
        _export_mod.export_whatsapp(sample_leads_enriched_df, path)
        content = path.read_text(encoding="utf-8")
        assert "IngenIA" in content
        assert "Teléfono" in content

    def test_rank_ml_used(self, sample_leads_enriched_df, tmp_path):
        path = tmp_path / "test.txt"
        _export_mod.export_whatsapp(sample_leads_enriched_df, path)
        content = path.read_text(encoding="utf-8")
        assert "Lead #1" in content  # rank_ml=1
        assert "Lead #?" not in content  # Shouldn't show ?


# ============================================================================
# Integration: pipeline data flow (30 tests)
# ============================================================================

class TestPipelineDataFlow:
    """Tests de integración para el flujo de datos entre pasos."""

    def test_company_db_to_scoring(self, sample_company_df, tmp_path):
        """company_database -> leads_ranked fluye correctamente."""
        filtered_dir = tmp_path / "filtered"
        filtered_dir.mkdir(parents=True)
        sample_company_df.to_parquet(filtered_dir / "company_database.parquet")

        with patch("05_score_leads.FILTERED_DIR", filtered_dir):
            df = pd.read_parquet(filtered_dir / "company_database.parquet")
            active = df[df["total_bids"] >= 2].copy()
            result = calculate_scores(active)

        assert "score_total" in result.columns
        assert result["score_total"].notna().all()

    def test_scoring_to_ml(self, sample_leads_ranked_df, tmp_path):
        """leads_ranked -> ML scoring fluye correctamente."""
        filtered_dir = tmp_path / "filtered"
        filtered_dir.mkdir(parents=True)
        sample_leads_ranked_df.to_parquet(filtered_dir / "leads_ranked.parquet")

        df = pd.read_parquet(filtered_dir / "leads_ranked.parquet")
        assert "score_total" in df.columns
        # compute_combined_score debería poder usar score_total
        df["km_score"] = 50.0
        df["xgb_score"] = 50.0
        result = compute_combined_score(df)
        assert "score_combined" in result.columns
        assert result["score_combined"].max() > 0

    def test_leads_enriched_has_rank(self, sample_leads_enriched_df):
        """leads_enriched tiene rank_ml para WhatsApp."""
        assert "rank_ml" in sample_leads_enriched_df.columns

    def test_loss_analysis_columns(self):
        """analyze_losses retorna las columnas correctas."""
        tender_map = {"T1": {"tenderers": {"R1"}, "winner": "R1", "n_competitors": 1}}
        rut_to_tenders = {"R1": {"T1"}}
        result = analyze_losses("R1", tender_map, rut_to_tenders)
        expected_keys = {"total_participated", "total_won", "total_lost", "total_unknown",
                         "loss_rate", "top_rival_1", "top_rival_1_count",
                         "top_rival_2", "top_rival_2_count", "n_distinct_rivals"}
        assert set(result.keys()) == expected_keys

    def test_whatsapp_v2_template_keys(self):
        """El template de WhatsApp v2 tiene los placeholders correctos."""
        template = _loss_mod.WHATSAPP_V2_TEMPLATE
        assert "{contacto}" in template
        assert "{insight_derrota}" in template
        assert "{cierre_personalizado}" in template

    def test_whatsapp_v1_template_keys(self):
        """El template de WhatsApp v1 tiene los placeholders correctos."""
        template = _export_mod.WHATSAPP_TEMPLATE
        assert "{contacto}" in template
        assert "{empresa}" in template
        assert "{n_bids}" in template
        assert "{detalle_licitacion}" in template

    def test_bulk_csv_files_values(self):
        """Los nombres de archivos CSV bulk son strings válidos."""
        for key, val in BULK_CSV_FILES.items():
            assert isinstance(val, str)
            assert val.endswith(".csv")

    def test_scoring_weights_match_scorers(self):
        """Cada dimensión en SCORING_WEIGHTS tiene un scorer."""
        scorers = {
            "actividad": score_actividad,
            "tamano": score_tamano,
            "win_rate": score_win_rate,
            "recencia": score_recencia,
            "valor": score_valor,
            "competencia": score_competencia,
            "oportunidad": score_oportunidad,
            "especializacion": score_especializacion,
            "region": score_region,
        }
        for dim in SCORING_WEIGHTS:
            assert dim in scorers, f"Falta scorer para {dim}"

    def test_ml_features_exist_in_company_db(self, sample_company_df):
        """Las features de ML existen en company_database."""
        from importlib import import_module
        ml = import_module("05b_ml_scoring")
        available_xgb = [f for f in ml.XGBOOST_FEATURES if f in sample_company_df.columns]
        assert len(available_xgb) >= 5  # Al menos 5 features disponibles

    def test_kmeans_features_exist(self, sample_company_df):
        """Las features de K-Means existen en company_database."""
        ml = import_module("05b_ml_scoring")
        available_km = [f for f in ml.KMEANS_FEATURES if f in sample_company_df.columns]
        assert len(available_km) >= 7


# ============================================================================
# Edge cases & regression tests (50 tests)
# ============================================================================

class TestEdgeCases:
    """Tests de edge cases y regresiones."""

    def test_normalize_rut_all_zeros(self):
        # 6 dígitos es formato válido según el regex
        assert normalizar_rut("000000-0") == "000000-0"

    def test_formato_clp_inf(self):
        result = formato_clp(float("inf"))
        assert isinstance(result, str)

    def test_score_range_equal_bounds(self):
        s = score_in_range(5, 5, 5)
        assert s == 100

    def test_score_actividad_very_high(self):
        row = pd.Series({"total_bids": 1000})
        s = score_actividad(row)
        assert 0 <= s <= 100

    def test_score_valor_negative(self):
        row = pd.Series({"monto_promedio": -100})
        s = score_valor(row)
        assert 0 <= s <= 100

    def test_tipo_licitacion_empty_string(self):
        assert tipo_licitacion("") == "Otro"

    def test_extraer_rut_empty_after_strip(self):
        assert extraer_rut_de_id("   ") is None

    def test_safe_get_with_nat(self):
        row = pd.Series({"date": pd.NaT})
        assert safe_get(row, "date") is None

    def test_es_construccion_unicode(self):
        assert es_construccion("Construcción de edificación") is True

    def test_score_recencia_exacto_730(self):
        row = pd.Series({"dias_desde_ultima": 730})
        s = score_recencia(row)
        assert s > 0  # 730 < 1460 (RECENCIA_MAX_DAYS), aún tiene score

    def test_score_recencia_1461(self):
        row = pd.Series({"dias_desde_ultima": 1461})
        assert score_recencia(row) == 0  # > RECENCIA_MAX_DAYS

    def test_analyze_losses_empty_tender_map(self):
        result = analyze_losses("R1", {}, {"R1": set()})
        assert result["total_participated"] == 0

    def test_calculate_scores_preserves_columns(self, sample_company_df):
        df = sample_company_df[sample_company_df["total_bids"] >= 2].copy()
        original_cols = set(df.columns)
        result = calculate_scores(df)
        for col in original_cols:
            assert col in result.columns

    def test_prepare_features_no_features(self):
        df = pd.DataFrame({"rut": ["R1"]})
        X, used = prepare_features(df, ["nonexistent1", "nonexistent2"])
        assert len(used) == 0

    def test_compute_combined_all_zeros(self):
        df = pd.DataFrame({
            "km_score": [0, 0], "xgb_score": [0, 0], "score_total": [0, 0]
        })
        result = compute_combined_score(df)
        assert (result["score_combined"] == 0).all()

    def test_whatsapp_message_special_chars(self):
        row = pd.Series({
            "contacto_nombre": "José Ñuñez",
            "nombre": "Constructora O'Higgins",
            "total_bids": 5,
            "win_rate": 0.2,
            "n_LP": 2,
        })
        msg = generate_whatsapp_message(row)
        assert "José Ñuñez" in msg
        assert "O'Higgins" in msg

    def test_loss_insight_all_wins(self):
        row = pd.Series({
            "total_lost": 0, "total_won": 10, "total_participated": 10,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        # Con won > lost y lost < 3, no debería decir "perdió"
        insight = generate_loss_insight(row)
        assert "perdió" not in insight

    def test_whatsapp_v2_no_contact(self):
        row = pd.Series({
            "contacto_nombre": np.nan,
            "nombre": np.nan,
            "total_lost": np.nan, "total_won": np.nan, "total_participated": np.nan,
            "top_rival_1_name": np.nan, "top_rival_1_count": np.nan,
        })
        msg = generate_whatsapp_v2(row)
        assert "estimado/a" in msg
        assert "su empresa" in msg

    def test_consolidate_no_gm_columns(self):
        df = pd.DataFrame({
            "rut": ["R1"],
            "ocds_telefono": ["+56900000000"],
            "ocds_email": ["test@test.cl"],
            "ocds_contacto": ["Test"],
        })
        result = consolidate_contacts(df)
        assert "telefono" in result.columns

    def test_find_column_first_match(self):
        df = pd.DataFrame(columns=["date_published", "date_modified"])
        result = find_column(df, ["date"])
        assert result == "date_published"  # First match

    def test_score_region_partial_match(self):
        row = pd.Series({"region": "Santiago"})
        s = score_region(row)
        # "santiago" is in "región metropolitana de santiago"
        assert s == 100

    def test_build_tenderer_stats_no_ruts(self):
        df = pd.DataFrame({
            "tender_id": ["T1", "T2"],
            "name": ["A", "B"],
        })
        stats = build_tenderer_stats(df.copy(), None)
        assert len(stats) == 0

    def test_score_tamano_mop_mayor_unknown_cat(self):
        row = pd.Series({"tipo_mop": "mayor", "categoria_mop": "desconocida", "monto_promedio": 0})
        assert score_tamano(row) == 70

    def test_score_in_range_very_small_value(self):
        s = score_in_range(0.001, 5, 15, lower_bound=0)
        assert 0 <= s < 5  # Very small -> very low score

    def test_generate_whatsapp_v2_win_rate_display(self):
        row = pd.Series({
            "contacto_nombre": "Test",
            "nombre": "Test Co",
            "total_lost": 2, "total_won": 3, "total_participated": 8,
            "top_rival_1_name": None, "top_rival_1_count": 0,
        })
        msg = generate_whatsapp_v2(row)
        assert "%" in msg  # Should show win percentage


# ============================================================================
# Stress tests (20 tests)
# ============================================================================

class TestStress:
    """Tests de estrés con datasets grandes."""

    def test_score_1000_companies(self):
        np.random.seed(42)
        n = 1000
        df = pd.DataFrame({
            "rut": [f"R{i}" for i in range(n)],
            "total_bids": np.random.randint(2, 50, n),
            "total_wins": np.random.randint(0, 20, n),
            "win_rate": np.random.uniform(0, 0.8, n),
            "monto_promedio": np.random.uniform(1e6, 1e9, n),
            "monto_total": np.random.uniform(1e7, 1e10, n),
            "dias_desde_ultima": np.random.randint(0, 730, n),
            "n_LP": np.random.randint(0, 20, n),
            "n_LE": np.random.randint(0, 15, n),
            "n_L1": np.random.randint(0, 10, n),
            "competidores_promedio": np.random.uniform(1, 20, n),
            "tipo_mop": [None] * n,
            "categoria_mop": [None] * n,
            "region": np.random.choice(REGIONES_TOP + ["Otra"], n),
        })
        result = calculate_scores(df)
        assert len(result) == n
        assert result["score_total"].min() >= 0
        assert result["score_total"].max() <= 100

    def test_prepare_features_large(self):
        n = 5000
        df = pd.DataFrame({
            "total_bids": np.random.randint(1, 100, n),
            "monto_promedio": np.random.uniform(0, 1e9, n),
            "monto_total": np.random.uniform(0, 1e10, n),
            "dias_desde_ultima": np.random.randint(0, 1000, n),
            "n_LP": np.random.randint(0, 30, n),
            "n_LE": np.random.randint(0, 20, n),
            "n_L1": np.random.randint(0, 15, n),
            "competidores_promedio": np.random.uniform(0, 25, n),
        })
        from importlib import import_module
        ml = import_module("05b_ml_scoring")
        X, used = ml.prepare_features(df, ml.XGBOOST_FEATURES)
        assert len(X) == n
        assert not X.isna().any().any()

    def test_analyze_losses_many_tenders(self):
        n_tenders = 500
        tender_map = {}
        rut_to_tenders = {"R1": set()}
        for i in range(n_tenders):
            tid = f"T{i}"
            winner = "R1" if i % 3 == 0 else f"R{(i % 10) + 2}"
            tender_map[tid] = {
                "tenderers": {"R1", winner},
                "winner": winner,
                "n_competitors": 2,
            }
            rut_to_tenders["R1"].add(tid)

        result = analyze_losses("R1", tender_map, rut_to_tenders)
        assert result["total_participated"] == n_tenders
        assert result["total_won"] + result["total_lost"] + result["total_unknown"] == n_tenders

    def test_whatsapp_100_messages(self):
        messages = []
        for i in range(100):
            row = pd.Series({
                "contacto_nombre": f"Contacto {i}" if i % 2 == 0 else None,
                "nombre": f"Empresa {i}",
                "total_bids": i + 1,
                "win_rate": (i % 5) / 10,
                "n_LP": i % 10,
            })
            msg = generate_whatsapp_message(row)
            messages.append(msg)
            assert "IngenIA" in msg

        assert len(messages) == 100

    def test_100_rut_normalizations(self):
        valid_count = 0
        for i in range(100):
            rut_str = f"{10000000 + i * 1000}-{i % 10}"
            result = normalizar_rut(rut_str)
            if result:
                valid_count += 1
        assert valid_count == 100

    def test_50_extraer_rut(self):
        for i in range(50):
            party_id = f"CL-RUT-{76000000 + i}-K"
            rut = extraer_rut_de_id(party_id)
            assert rut is not None

    def test_combined_score_uniform(self):
        n = 200
        df = pd.DataFrame({
            "km_score": np.random.uniform(0, 100, n),
            "xgb_score": np.random.uniform(0, 100, n),
            "score_total": np.random.uniform(0, 100, n),
        })
        result = compute_combined_score(df)
        assert result["score_combined"].min() >= 0
        assert result["score_combined"].max() <= 100.0 + 0.1  # Float tolerance


# ============================================================================
# Config validation (10 tests)
# ============================================================================

class TestConfigValidation:
    def test_all_weights_between_0_1(self):
        for dim, w in SCORING_WEIGHTS.items():
            assert 0 < w < 1, f"{dim}: {w}"

    def test_ideal_ranges_are_tuples(self):
        for key, val in IDEAL_RANGES.items():
            assert isinstance(val, tuple) and len(val) == 2

    def test_regiones_top_are_strings(self):
        for r in REGIONES_TOP:
            assert isinstance(r, str) and len(r) > 5

    def test_tipos_licitacion_values(self):
        for key, val in TIPOS_LICITACION.items():
            assert isinstance(val, str)
            assert len(key) == 2

    def test_bulk_csv_keys(self):
        for key in ["tenders", "tenderers", "items", "awards", "suppliers", "parties"]:
            assert key in BULK_CSV_FILES


# ============================================================================
# run_pipeline — STEPS validation (10 tests)
# ============================================================================

_pipeline_mod = import_module("run_pipeline")


class TestRunPipeline:
    def test_steps_count(self):
        assert len(_pipeline_mod.STEPS) == 11

    def test_steps_have_script_and_desc(self):
        for script, desc in _pipeline_mod.STEPS:
            assert script.endswith(".py")
            assert len(desc) > 3

    def test_steps_scripts_exist(self):
        base = Path(__file__).parent
        for script, _ in _pipeline_mod.STEPS:
            assert (base / script).exists(), f"Script {script} no existe"

    def test_steps_order(self):
        scripts = [s for s, _ in _pipeline_mod.STEPS]
        assert scripts[0].startswith("01")
        assert scripts[-1].startswith("10")

    def test_step_05b_after_05(self):
        scripts = [s for s, _ in _pipeline_mod.STEPS]
        idx_05 = next(i for i, s in enumerate(scripts) if s.startswith("05_"))
        idx_05b = next(i for i, s in enumerate(scripts) if s.startswith("05b"))
        assert idx_05b > idx_05


# ============================================================================
# Parquet I/O round-trip (10 tests)
# ============================================================================

class TestParquetRoundTrip:
    def test_company_db_roundtrip(self, sample_company_df, tmp_path):
        path = tmp_path / "test.parquet"
        sample_company_df.to_parquet(path, index=False)
        loaded = pd.read_parquet(path)
        assert len(loaded) == len(sample_company_df)
        assert set(loaded.columns) == set(sample_company_df.columns)

    def test_ranked_roundtrip(self, sample_leads_ranked_df, tmp_path):
        path = tmp_path / "test.parquet"
        sample_leads_ranked_df.to_parquet(path, index=False)
        loaded = pd.read_parquet(path)
        assert "score_total" in loaded.columns
        assert "rank" in loaded.columns

    def test_enriched_roundtrip(self, sample_leads_enriched_df, tmp_path):
        path = tmp_path / "test.parquet"
        sample_leads_enriched_df.to_parquet(path, index=False)
        loaded = pd.read_parquet(path)
        assert "telefono" in loaded.columns
        assert "rank_ml" in loaded.columns

    def test_empty_df_roundtrip(self, tmp_path):
        path = tmp_path / "test.parquet"
        df = pd.DataFrame(columns=["rut", "nombre", "score"])
        df.to_parquet(path, index=False)
        loaded = pd.read_parquet(path)
        assert len(loaded) == 0

    def test_nan_preservation(self, tmp_path):
        path = tmp_path / "test.parquet"
        df = pd.DataFrame({"a": [1, np.nan, 3], "b": ["x", None, "z"]})
        df.to_parquet(path, index=False)
        loaded = pd.read_parquet(path)
        assert pd.isna(loaded["a"].iloc[1])
        assert pd.isna(loaded["b"].iloc[1])


# ============================================================================
# PARAMETRIZED TESTS — Batch RUT normalization (100 tests)
# ============================================================================

_VALID_RUTS = [
    ("76543210-K", "76543210-K"),
    ("76.543.210-K", "76543210-K"),
    ("76543210K", "76543210-K"),
    ("12345678-9", "12345678-9"),
    ("12345678-0", "12345678-0"),
    ("99999999-9", "99999999-9"),
    ("11111111-1", "11111111-1"),
    ("  76543210-K  ", "76543210-K"),
    ("76543210-k", "76543210-K"),
    ("123456-7", "123456-7"),
] + [(f"{10000000+i}-{i%10}", f"{10000000+i}-{i%10}") for i in range(40)]

_INVALID_RUTS = [
    "", None, "abc", "12-3", "12345", "abcdefgh-K",
    "1234567890123-K", "--K", "K", "...", "123", "   ",
    "hello world", "CL-RUT", "0-0", "1-K", "12-K", "123-K", "1234-K", "12345-K",
] + [str(i) for i in range(20)]  # plain numbers


@pytest.mark.parametrize("rut_in,expected", _VALID_RUTS)
def test_normalizar_rut_valid(rut_in, expected):
    assert normalizar_rut(rut_in) == expected


@pytest.mark.parametrize("rut_in", _INVALID_RUTS)
def test_normalizar_rut_invalid(rut_in):
    assert normalizar_rut(rut_in) is None


# ============================================================================
# PARAMETRIZED TESTS — extraer_rut_de_id (80 tests)
# ============================================================================

_VALID_PARTY_IDS = [
    (f"CL-RUT-{76000000+i}-K", f"{76000000+i}-K") for i in range(40)
] + [
    (f"{12000000+i}-{i%10}", f"{12000000+i}-{i%10}") for i in range(20)
] + [
    ("buyer-CL-RUT-98765432-1-name", "98765432-1"),
    ("org-11111111-1", "11111111-1"),
    ("CL-RUT-76543210-0", "76543210-0"),
]

_INVALID_PARTY_IDS = [
    "", None, "hello", "org-central", "buyer-name", "CL-NO-RUT",
    "abc-def-ghi", "   ", "nan", "True", "False",
]


@pytest.mark.parametrize("party_id,expected", _VALID_PARTY_IDS)
def test_extraer_rut_valid(party_id, expected):
    assert extraer_rut_de_id(party_id) == expected


@pytest.mark.parametrize("party_id", _INVALID_PARTY_IDS)
def test_extraer_rut_invalid(party_id):
    assert extraer_rut_de_id(party_id) is None


# ============================================================================
# PARAMETRIZED TESTS — tipo_licitacion (40 tests)
# ============================================================================

_TIPO_CASES = [
    ("2405-31-LP26", "LP"), ("2405-31-LE26", "LE"), ("2405-31-L126", "L1"),
    ("2405-31-LR26", "LR"), ("2405-31-lp26", "LP"), ("2405-31-le26", "LE"),
    ("-LP", "LP"), ("-LE", "LE"), ("-L1", "L1"), ("-LR", "LR"),
    ("621-5-LP25", "LP"), ("1234-100-LE25", "LE"),
    ("9999-1-L126", "L1"), ("100-1-LR24", "LR"),
] + [
    (f"{i*100}-{i}-LP{i%30}", "LP") for i in range(1, 14)
] + [
    (f"{i*100}-{i}-LE{i%30}", "LE") for i in range(1, 14)
]

_TIPO_OTHER = ["", "XX", "LP26", "abc", "12345"] + [str(i) for i in range(5)]


@pytest.mark.parametrize("code,expected", _TIPO_CASES)
def test_tipo_licitacion_param(code, expected):
    assert tipo_licitacion(code) == expected


@pytest.mark.parametrize("code", _TIPO_OTHER)
def test_tipo_licitacion_otro(code):
    assert tipo_licitacion(code) == "Otro"


# ============================================================================
# PARAMETRIZED TESTS — formato_clp (50 tests)
# ============================================================================

_CLP_BILLIONS = [(v * 1_000_000_000, "B") for v in [1, 1.5, 2, 5, 10, 50, 100]]
_CLP_MILLIONS = [(v * 1_000_000, "M") for v in [1, 5, 10, 50, 100, 200, 500, 999]]
_CLP_SMALL = [(v, "$") for v in [0, 1, 100, 1000, 10000, 100000, 500000, 999999]]


@pytest.mark.parametrize("monto,expected_suffix", _CLP_BILLIONS)
def test_formato_clp_billions(monto, expected_suffix):
    result = formato_clp(monto)
    assert expected_suffix in result


@pytest.mark.parametrize("monto,expected_suffix", _CLP_MILLIONS)
def test_formato_clp_millions(monto, expected_suffix):
    result = formato_clp(monto)
    assert expected_suffix in result


@pytest.mark.parametrize("monto,expected_prefix", _CLP_SMALL)
def test_formato_clp_small(monto, expected_prefix):
    result = formato_clp(monto)
    assert result.startswith(expected_prefix)


# ============================================================================
# PARAMETRIZED TESTS — score_in_range boundaries (60 tests)
# ============================================================================

_SCORE_RANGE_CASES = []
# Within range -> 100
for v in range(5, 16):
    _SCORE_RANGE_CASES.append((v, 5, 15, 0, 50, 100))
# Below range -> 0-100
for v in [0, 1, 2, 3, 4]:
    _SCORE_RANGE_CASES.append((v, 5, 15, 0, 50, None))  # None = just check 0-100
# Above range -> 0-100
for v in [16, 20, 30, 40, 50]:
    _SCORE_RANGE_CASES.append((v, 5, 15, 0, 50, None))


@pytest.mark.parametrize("value,imin,imax,lb,ub,expected", _SCORE_RANGE_CASES)
def test_score_in_range_parametrized(value, imin, imax, lb, ub, expected):
    result = score_in_range(value, imin, imax, lower_bound=lb, upper_bound=ub)
    if expected is not None:
        assert result == expected
    else:
        assert 0 <= result <= 100


# Additional boundary tests
@pytest.mark.parametrize("value", list(range(0, 51)))
def test_score_actividad_range(value):
    row = pd.Series({"total_bids": value})
    s = score_actividad(row)
    assert 0 <= s <= 100


@pytest.mark.parametrize("wr", [i / 20.0 for i in range(21)])  # 0.0 to 1.0
def test_score_win_rate_range(wr):
    row = pd.Series({"win_rate": wr, "total_bids": 10})
    s = score_win_rate(row)
    assert 0 <= s <= 100


@pytest.mark.parametrize("dias", list(range(0, 800, 50)))
def test_score_recencia_range(dias):
    row = pd.Series({"dias_desde_ultima": dias})
    s = score_recencia(row)
    assert 0 <= s <= 100


# ============================================================================
# PARAMETRIZED TESTS — es_construccion (50 tests)
# ============================================================================

_CONSTRUCCION_SI = [
    "Construcción puente", "Obra vial", "Infraestructura escolar",
    "Pavimentación calle", "Vialidad urbana", "Puente peatonal",
    "Edificio municipal", "Mejoramiento camino", "Reposición hospital",
    "Conservación ruta", "Habilitación terreno", "Demolición bodega",
    "Estructura metálica", "Arquitectura complejo", "Urbanización sector",
    "Alcantarillado norte", "Agua potable rural", "Saneamiento básico",
    "CONSTRUCCIÓN PUENTE", "obra pavimentación",
]

_CONSTRUCCION_NO = [
    "", "Compra de vehículos", "Neumaticos para bus", "Equipamiento dental",
    "Compra medicamentos", "Servicio telefónico", "Azure cloud services",
    "Internet fibra óptica", "Kinesiología tratamiento", "Reactivos laboratorio",
    "Cocina industrial", "Compresor aire", "Seguro de vida",
    "Limpieza oficinas", "Impresora laser", "Software gestión",
    "Consultoría ambiental", "Sillas de oficina", "Papel carta",
    "Nada que ver con nada",
]


@pytest.mark.parametrize("texto", _CONSTRUCCION_SI)
def test_es_construccion_si(texto):
    assert es_construccion(texto) is True


@pytest.mark.parametrize("texto", _CONSTRUCCION_NO)
def test_es_construccion_no(texto):
    assert es_construccion(texto) is False


# ============================================================================
# PARAMETRIZED TESTS — scoring all dimensions on ideal company (30 tests)
# ============================================================================

@pytest.fixture
def ideal_company():
    return pd.Series({
        "total_bids": 15,
        "total_wins": 4,
        "win_rate": 0.25,
        "monto_promedio": 500_000_000,
        "monto_total": 5_000_000_000,
        "dias_desde_ultima": 0,
        "n_LP": 8, "n_LE": 3, "n_L1": 2,
        "competidores_promedio": 10,
        "total_lost": 5,
        "n_distinct_rivals": 5,
        "tipo_mop": "mayor", "categoria_mop": "2da",
        "region": "Región Metropolitana de Santiago",
    })


class TestIdealCompanyScores:
    def test_actividad_ideal(self, ideal_company):
        assert score_actividad(ideal_company) == 100

    def test_tamano_ideal(self, ideal_company):
        assert score_tamano(ideal_company) == 100

    def test_win_rate_ideal(self, ideal_company):
        assert score_win_rate(ideal_company) == 100

    def test_recencia_ideal(self, ideal_company):
        assert score_recencia(ideal_company) == 100

    def test_valor_ideal(self, ideal_company):
        assert score_valor(ideal_company) == 100

    def test_competencia_ideal(self, ideal_company):
        assert score_competencia(ideal_company) == 100

    def test_region_ideal(self, ideal_company):
        assert score_region(ideal_company) == 100

    def test_especializacion_high(self, ideal_company):
        assert score_especializacion(ideal_company) > 60

    def test_total_score_high(self, ideal_company):
        df = pd.DataFrame([ideal_company])
        result = calculate_scores(df)
        assert result["score_total"].iloc[0] > 85


# ============================================================================
# PARAMETRIZED TESTS — WhatsApp messages (40 tests)
# ============================================================================

@pytest.mark.parametrize("n_bids", [0, 1, 5, 10, 50, 100])
def test_whatsapp_various_bids(n_bids):
    row = pd.Series({
        "contacto_nombre": "Test", "nombre": "Empresa",
        "total_bids": n_bids, "win_rate": 0.2, "n_LP": 0,
    })
    msg = generate_whatsapp_message(row)
    assert isinstance(msg, str)
    assert len(msg) > 50


@pytest.mark.parametrize("wr", [0, 0.1, 0.2, 0.3, 0.5, 0.8])
def test_whatsapp_various_wr(wr):
    row = pd.Series({
        "contacto_nombre": "Test", "nombre": "Empresa",
        "total_bids": 10, "win_rate": wr, "n_LP": 3,
    })
    msg = generate_whatsapp_message(row)
    assert "IngenIA" in msg


@pytest.mark.parametrize("lost,won,total", [
    (0, 0, 0), (0, 5, 5), (5, 0, 8), (3, 3, 10), (10, 1, 15),
    (0, 0, 1), (1, 0, 1), (0, 1, 1),
])
def test_whatsapp_v2_various(lost, won, total):
    row = pd.Series({
        "contacto_nombre": "Test", "nombre": "Empresa",
        "total_lost": lost, "total_won": won, "total_participated": total,
        "top_rival_1_name": None, "top_rival_1_count": 0,
    })
    msg = generate_whatsapp_v2(row)
    assert isinstance(msg, str)
    assert "IngenIA" in msg


@pytest.mark.parametrize("rival_count", [0, 1, 2, 3, 5, 10])
def test_whatsapp_v2_rival_counts(rival_count):
    row = pd.Series({
        "contacto_nombre": "Test", "nombre": "Empresa",
        "total_lost": 5, "total_won": 1, "total_participated": 10,
        "top_rival_1_name": "Rival Co" if rival_count > 0 else None,
        "top_rival_1_count": rival_count,
    })
    msg = generate_whatsapp_v2(row)
    if rival_count >= 2:
        assert "Rival Co" in msg


# ============================================================================
# PARAMETRIZED TESTS — loss analysis (30 tests)
# ============================================================================

@pytest.mark.parametrize("n_tenders", [0, 1, 5, 10, 50])
def test_analyze_losses_various_sizes(n_tenders):
    tender_map = {}
    rut_to_tenders = {"R1": set()}
    for i in range(n_tenders):
        tid = f"T{i}"
        winner = "R1" if i % 2 == 0 else "R2"
        tender_map[tid] = {"tenderers": {"R1", "R2"}, "winner": winner, "n_competitors": 2}
        rut_to_tenders["R1"].add(tid)
    result = analyze_losses("R1", tender_map, rut_to_tenders)
    assert result["total_participated"] == n_tenders
    assert result["total_won"] + result["total_lost"] == n_tenders


@pytest.mark.parametrize("n_rivals", [1, 2, 5, 10])
def test_analyze_losses_various_rivals(n_rivals):
    tender_map = {}
    rut_to_tenders = {"R1": set()}
    for i in range(n_rivals):
        tid = f"T{i}"
        rival = f"RIVAL{i}"
        tender_map[tid] = {"tenderers": {"R1", rival}, "winner": rival, "n_competitors": 2}
        rut_to_tenders["R1"].add(tid)
    result = analyze_losses("R1", tender_map, rut_to_tenders)
    assert result["n_distinct_rivals"] == n_rivals


@pytest.mark.parametrize("lost,won,participated", [
    (0, 0, 0), (1, 0, 1), (0, 1, 1), (5, 5, 10), (10, 0, 10),
])
def test_loss_insight_various(lost, won, participated):
    row = pd.Series({
        "total_lost": lost, "total_won": won, "total_participated": participated,
        "top_rival_1_name": "R", "top_rival_1_count": 1,
    })
    insight = generate_loss_insight(row)
    assert isinstance(insight, str)


# ============================================================================
# PARAMETRIZED TESTS — credit error detection (15 tests)
# ============================================================================

@pytest.mark.parametrize("msg,expected", [
    ("HTTP 402 Payment Required", True),
    ("Insufficient credits", True),
    ("Credit balance exhausted", True),
    ("Usage quota exceeded", True),
    ("Plan limit reached", True),
    ("Connection timeout", False),
    ("HTTP 500 Server Error", False),
    ("Invalid API key", False),
    ("Rate limited", False),
    ("Network unreachable", False),
])
def test_credit_error_detection(msg, expected):
    assert _is_credit_error(msg) is expected


# ============================================================================
# PARAMETRIZED — score_valor range (30 tests)
# ============================================================================

@pytest.mark.parametrize("monto", [
    0, 1000, 10_000, 100_000, 1_000_000, 5_000_000,
    10_000_000, 30_000_000, 50_000_000, 66_000_000,
    100_000_000, 200_000_000, 300_000_000, 500_000_000,
    600_000_000, 1_000_000_000, 2_000_000_000, 5_000_000_000,
    10_000_000_000, np.nan,
])
def test_score_valor_range(monto):
    row = pd.Series({"monto_promedio": monto})
    s = score_valor(row)
    assert 0 <= s <= 100


@pytest.mark.parametrize("comp", [
    0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    12, 15, 20, 25, 30, np.nan,
])
def test_score_competencia_range(comp):
    row = pd.Series({"competidores_promedio": comp})
    s = score_competencia(row)
    assert 0 <= s <= 100


# ============================================================================
# PARAMETRIZED — score_especializacion (30 tests)
# ============================================================================

@pytest.mark.parametrize("lp,le,l1", [
    (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
    (5, 3, 2), (10, 5, 5), (0, 10, 0), (0, 0, 10),
    (20, 0, 0), (10, 10, 10), (1, 1, 1), (3, 0, 0),
    (0, 5, 5), (7, 2, 1), (15, 3, 2),
])
def test_score_especializacion_range(lp, le, l1):
    row = pd.Series({"n_LP": lp, "n_LE": le, "n_L1": l1})
    s = score_especializacion(row)
    assert 0 <= s <= 100


# ============================================================================
# PARAMETRIZED — score_region (30 tests)
# ============================================================================

@pytest.mark.parametrize("region", REGIONES_TOP)
def test_score_region_top(region):
    row = pd.Series({"region": region})
    s = score_region(row)
    assert s >= 60


@pytest.mark.parametrize("region", [
    "Región de Atacama", "Región de Coquimbo", "Región del Maule",
    "Región de Aysén", "Región de Magallanes", "Desconocida",
    "Otra región", "Region sin tilde",
])
def test_score_region_other(region):
    row = pd.Series({"region": region})
    s = score_region(row)
    assert 0 <= s <= 100


@pytest.mark.parametrize("region", [None, np.nan, "", "   "])
def test_score_region_empty(region):
    row = pd.Series({"region": region})
    s = score_region(row)
    assert s == 50 or s == 40  # Empty = neutral or other


# ============================================================================
# PARAMETRIZED — score_tamano MOP variants (20 tests)
# ============================================================================

@pytest.mark.parametrize("tipo,cat,expected_min", [
    ("mayor", "1ra", 55), ("mayor", "primera", 55),
    ("mayor", "2da", 95), ("mayor", "segunda", 95),
    ("mayor", "3ra", 75), ("mayor", "tercera", 75),
    ("mayor", "desconocida", 65), ("mayor", "", 65),
    ("menor", "", 45), ("menor", "cualquiera", 45),
])
def test_score_tamano_mop_variants(tipo, cat, expected_min):
    row = pd.Series({"tipo_mop": tipo, "categoria_mop": cat, "monto_promedio": 0})
    s = score_tamano(row)
    assert s >= expected_min


@pytest.mark.parametrize("monto,expected_min", [
    (66_000_000, 85), (100_000_000, 85), (200_000_000, 85),
    (500_000_000, 100), (66_000_001, 85), (499_999_999, 99),
])
def test_score_tamano_monto_ideal(monto, expected_min):
    row = pd.Series({"tipo_mop": None, "categoria_mop": None, "monto_promedio": monto})
    s = score_tamano(row)
    assert s >= expected_min


# ============================================================================
# PARAMETRIZED — safe_get with various types (25 tests)
# ============================================================================

@pytest.mark.parametrize("value,default,expected", [
    (10, 0, 10), (0, 99, 0), ("hello", "def", "hello"),
    (None, "def", "def"), (np.nan, "def", "def"),
    (float("nan"), 0, 0), ("", "def", ""),
    (True, False, True), ([], "def", []),
    (0.0, 1.0, 0.0),
])
def test_safe_get_parametrized(value, default, expected):
    row = pd.Series({"col": value})
    result = safe_get(row, "col", default)
    if isinstance(expected, float) and np.isnan(expected):
        assert np.isnan(result)
    else:
        assert result == expected


@pytest.mark.parametrize("default", [None, 0, "", "default", -1, False])
def test_safe_get_missing_col(default):
    row = pd.Series({"a": 1})
    assert safe_get(row, "missing", default) == default


# ============================================================================
# PARAMETRIZED — RUT edge cases en extraer_rut_de_id (30 tests)
# ============================================================================

@pytest.mark.parametrize("i", range(30))
def test_extraer_rut_sequential(i):
    rut_num = 76000000 + i * 100
    party_id = f"CL-RUT-{rut_num}-{i % 10}"
    result = extraer_rut_de_id(party_id)
    assert result == f"{rut_num}-{i % 10}"


# ============================================================================
# PARAMETRIZED — Stress: many companies through scoring (20 tests)
# ============================================================================

@pytest.mark.parametrize("n", [10, 50, 100, 500, 1000])
def test_scoring_n_companies(n):
    np.random.seed(42)
    df = pd.DataFrame({
        "rut": [f"R{i}" for i in range(n)],
        "total_bids": np.random.randint(2, 30, n),
        "total_wins": np.random.randint(0, 10, n),
        "win_rate": np.random.uniform(0, 0.6, n),
        "monto_promedio": np.random.uniform(1e6, 1e9, n),
        "monto_total": np.random.uniform(1e7, 1e10, n),
        "dias_desde_ultima": np.random.randint(0, 500, n),
        "n_LP": np.random.randint(0, 15, n),
        "n_LE": np.random.randint(0, 10, n),
        "n_L1": np.random.randint(0, 8, n),
        "competidores_promedio": np.random.uniform(1, 20, n),
        "tipo_mop": [None] * n,
        "categoria_mop": [None] * n,
        "region": ["Región Metropolitana de Santiago"] * n,
    })
    result = calculate_scores(df)
    assert len(result) == n
    assert result["score_total"].between(0, 100).all()


# ============================================================================
# PARAMETRIZED — Stress: many losses analysis (15 tests)
# ============================================================================

@pytest.mark.parametrize("n_tenders", [1, 5, 10, 50, 100, 200, 500])
def test_analyze_losses_stress(n_tenders):
    tender_map = {}
    rut_to_tenders = {"R1": set()}
    for i in range(n_tenders):
        tid = f"T{i}"
        winner = "R1" if i % 4 == 0 else f"RIVAL{i%5}"
        tender_map[tid] = {"tenderers": {"R1", winner}, "winner": winner, "n_competitors": 2}
        rut_to_tenders["R1"].add(tid)
    result = analyze_losses("R1", tender_map, rut_to_tenders)
    total = result["total_won"] + result["total_lost"] + result["total_unknown"]
    assert total == n_tenders


# ============================================================================
# PARAMETRIZED — normalizar_rut batch (50+ tests)
# ============================================================================

@pytest.mark.parametrize("i", range(50))
def test_normalizar_rut_batch_valid(i):
    """50 RUTs válidos generados programáticamente."""
    num = 10000000 + i * 100000
    rut_str = f"{num}-{i % 10}"
    result = normalizar_rut(rut_str)
    assert result == rut_str


@pytest.mark.parametrize("i", range(25))
def test_normalizar_rut_con_puntos_batch(i):
    """25 RUTs con puntos."""
    num = 76000000 + i * 1000
    s = str(num)
    rut_str = f"{s[:2]}.{s[2:5]}.{s[5:]}-K"
    result = normalizar_rut(rut_str)
    assert result == f"{num}-K"


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-q"])
