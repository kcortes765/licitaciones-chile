"""
Tests de seguridad de exportacion: verifican que NINGUN output
cliente-facing contiene datos internos (scores, clusters, ML signals).

Usa @pytest.mark.skipif para archivos que no existan localmente.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

LEAD_SCORING_DIR = Path(__file__).resolve().parent.parent
if str(LEAD_SCORING_DIR) not in sys.path:
    sys.path.insert(0, str(LEAD_SCORING_DIR))

from pipeline_core import CLIENT_FORBIDDEN_COLUMNS
from pipeline_validation import (
    CLIENT_FORBIDDEN_PATTERNS,
    _scan_text_forbidden,
    assert_client_safe_binary,
    assert_client_safe_columns,
    assert_client_safe_json,
    assert_client_safe_text,
)

# ── Paths ────────────────────────────────────────────────────────────

OUTPUT_DIR = LEAD_SCORING_DIR / "data" / "output"
DIAGNOSTICOS_DIR = OUTPUT_DIR / "diagnosticos"

LEADS_FINAL_CSV = OUTPUT_DIR / "leads_final.csv"
LEADS_FINAL_XLSX = OUTPUT_DIR / "leads_final.xlsx"
CRM_CSV = OUTPUT_DIR / "crm_leads.csv"
CRM_XLSX = OUTPUT_DIR / "crm_leads.xlsx"
LEADS_VERIF_CSV = OUTPUT_DIR / "leads_verificados.csv"
LEADS_VERIF_XLSX = OUTPUT_DIR / "leads_verificados.xlsx"
LEADS_VERIF_V4_XLSX = OUTPUT_DIR / "leads_verificados_v4.xlsx"
MSG_WSP = OUTPUT_DIR / "mensajes_whatsapp.txt"
MSG_WSP_V2 = OUTPUT_DIR / "mensajes_whatsapp_v2.txt"
MSG_WSP_V3 = OUTPUT_DIR / "mensajes_wsp_v3.txt"
MSG_WSP_V4 = OUTPUT_DIR / "mensajes_wsp_v4.txt"
EXPORT_MANIFEST = OUTPUT_DIR / "export_manifest.json"
VALIDATION_REPORT = OUTPUT_DIR / "validation_report.json"

# ── Skip markers ─────────────────────────────────────────────────────

skip_no_leads_csv = pytest.mark.skipif(
    not LEADS_FINAL_CSV.exists(), reason="leads_final.csv no disponible"
)
skip_no_leads_xlsx = pytest.mark.skipif(
    not LEADS_FINAL_XLSX.exists(), reason="leads_final.xlsx no disponible"
)
skip_no_crm_csv = pytest.mark.skipif(
    not CRM_CSV.exists(), reason="crm_leads.csv no disponible"
)
skip_no_crm_xlsx = pytest.mark.skipif(
    not CRM_XLSX.exists(), reason="crm_leads.xlsx no disponible"
)
skip_no_verif_csv = pytest.mark.skipif(
    not LEADS_VERIF_CSV.exists(), reason="leads_verificados.csv no disponible"
)
skip_no_verif_xlsx = pytest.mark.skipif(
    not LEADS_VERIF_XLSX.exists(), reason="leads_verificados.xlsx no disponible"
)
skip_no_verif_v4 = pytest.mark.skipif(
    not LEADS_VERIF_V4_XLSX.exists(), reason="leads_verificados_v4.xlsx no disponible"
)
skip_no_msg_wsp = pytest.mark.skipif(
    not MSG_WSP.exists(), reason="mensajes_whatsapp.txt no disponible"
)
skip_no_msg_v2 = pytest.mark.skipif(
    not MSG_WSP_V2.exists(), reason="mensajes_whatsapp_v2.txt no disponible"
)
skip_no_msg_v3 = pytest.mark.skipif(
    not MSG_WSP_V3.exists(), reason="mensajes_wsp_v3.txt no disponible"
)
skip_no_msg_v4 = pytest.mark.skipif(
    not MSG_WSP_V4.exists(), reason="mensajes_wsp_v4.txt no disponible"
)
skip_no_manifest = pytest.mark.skipif(
    not EXPORT_MANIFEST.exists(), reason="export_manifest.json no disponible"
)
skip_no_valreport = pytest.mark.skipif(
    not VALIDATION_REPORT.exists(), reason="validation_report.json no disponible"
)
skip_no_diagnosticos = pytest.mark.skipif(
    not DIAGNOSTICOS_DIR.exists(), reason="diagnosticos/ no disponible"
)


# ── Helpers ──────────────────────────────────────────────────────────

def _forbidden_cols_in_df(df: pd.DataFrame) -> list[str]:
    """Retorna columnas del DF que estan en CLIENT_FORBIDDEN_COLUMNS o matchean forbidden patterns."""
    bad = []
    for col in df.columns:
        if col in CLIENT_FORBIDDEN_COLUMNS:
            bad.append(col)
        elif _scan_text_forbidden(col):
            bad.append(col)
    return sorted(set(bad))


# ═══════════════════════════════════════════════════════════════════════
# TESTS: leads_final.csv
# ═══════════════════════════════════════════════════════════════════════

class TestLeadsFinalCsv:

    @skip_no_leads_csv
    def test_no_forbidden_columns(self):
        df = pd.read_csv(LEADS_FINAL_CSV, nrows=0)
        bad = _forbidden_cols_in_df(df)
        assert not bad, f"leads_final.csv contiene columnas prohibidas: {bad}"

    @skip_no_leads_csv
    def test_no_score_total(self):
        df = pd.read_csv(LEADS_FINAL_CSV, nrows=0)
        assert "score_total" not in df.columns

    @skip_no_leads_csv
    def test_no_score_combined(self):
        df = pd.read_csv(LEADS_FINAL_CSV, nrows=0)
        assert "score_combined" not in df.columns

    @skip_no_leads_csv
    def test_no_cluster(self):
        df = pd.read_csv(LEADS_FINAL_CSV, nrows=0)
        assert "cluster" not in df.columns
        assert "cluster_perfil" not in df.columns

    @skip_no_leads_csv
    def test_no_ml_scores(self):
        df = pd.read_csv(LEADS_FINAL_CSV, nrows=0)
        ml_cols = [c for c in df.columns if c.startswith(("xgb_", "km_"))]
        assert not ml_cols, f"leads_final.csv contiene columnas ML: {ml_cols}"

    @skip_no_leads_csv
    def test_assert_client_safe_columns(self):
        df = pd.read_csv(LEADS_FINAL_CSV, nrows=0)
        assert_client_safe_columns(df)


# ═══════════════════════════════════════════════════════════════════════
# TESTS: leads_final.xlsx
# ═══════════════════════════════════════════════════════════════════════

class TestLeadsFinalXlsx:

    @skip_no_leads_xlsx
    def test_no_forbidden_columns(self):
        df = pd.read_excel(LEADS_FINAL_XLSX, nrows=0)
        bad = _forbidden_cols_in_df(df)
        assert not bad, f"leads_final.xlsx contiene columnas prohibidas: {bad}"

    @skip_no_leads_xlsx
    def test_assert_client_safe_columns(self):
        df = pd.read_excel(LEADS_FINAL_XLSX, nrows=0)
        assert_client_safe_columns(df)


# ═══════════════════════════════════════════════════════════════════════
# TESTS: crm_leads.csv / .xlsx
# ═══════════════════════════════════════════════════════════════════════

class TestCrmLeadsCsv:

    @skip_no_crm_csv
    def test_no_forbidden_columns(self):
        df = pd.read_csv(CRM_CSV, nrows=0)
        bad = _forbidden_cols_in_df(df)
        assert not bad, f"crm_leads.csv contiene columnas prohibidas: {bad}"

    @skip_no_crm_csv
    def test_has_expected_columns(self):
        df = pd.read_csv(CRM_CSV, nrows=0)
        expected = {"empresa", "rut", "canal", "estado"}
        missing = expected - set(df.columns)
        assert not missing, f"crm_leads.csv falta columnas esperadas: {missing}"

    @skip_no_crm_csv
    def test_assert_client_safe_columns(self):
        df = pd.read_csv(CRM_CSV, nrows=0)
        assert_client_safe_columns(df)


class TestCrmLeadsXlsx:

    @skip_no_crm_xlsx
    def test_no_forbidden_columns(self):
        df = pd.read_excel(CRM_XLSX, nrows=0)
        bad = _forbidden_cols_in_df(df)
        assert not bad, f"crm_leads.xlsx contiene columnas prohibidas: {bad}"

    @skip_no_crm_xlsx
    def test_has_expected_columns(self):
        df = pd.read_excel(CRM_XLSX, nrows=0)
        expected = {"empresa", "rut", "canal", "estado"}
        missing = expected - set(df.columns)
        assert not missing, f"crm_leads.xlsx falta columnas esperadas: {missing}"

    @skip_no_crm_xlsx
    def test_assert_client_safe_columns(self):
        df = pd.read_excel(CRM_XLSX, nrows=0)
        assert_client_safe_columns(df)


# ═══════════════════════════════════════════════════════════════════════
# TESTS: mensajes WhatsApp (text files)
# ═══════════════════════════════════════════════════════════════════════

FORBIDDEN_TEXT_TERMS = [
    "score_total", "score_combined", "cluster", "xgb_",
    "km_score", "lead ideal",
]


class TestMensajesWhatsApp:

    @skip_no_msg_wsp
    def test_no_forbidden_terms(self):
        text = MSG_WSP.read_text(encoding="utf-8")
        matches = _scan_text_forbidden(text)
        assert not matches, f"mensajes_whatsapp.txt contiene patrones internos: {matches}"

    @skip_no_msg_wsp
    def test_assert_client_safe_text(self):
        text = MSG_WSP.read_text(encoding="utf-8")
        assert_client_safe_text(text, "mensajes_whatsapp.txt")

    @skip_no_msg_v2
    def test_v2_no_forbidden_terms(self):
        text = MSG_WSP_V2.read_text(encoding="utf-8")
        matches = _scan_text_forbidden(text)
        assert not matches, f"mensajes_whatsapp_v2.txt contiene patrones internos: {matches}"

    @skip_no_msg_v2
    def test_v2_assert_client_safe_text(self):
        text = MSG_WSP_V2.read_text(encoding="utf-8")
        assert_client_safe_text(text, "mensajes_whatsapp_v2.txt")


class TestMensajesWsp:

    @skip_no_msg_v3
    def test_v3_no_forbidden_terms(self):
        text = MSG_WSP_V3.read_text(encoding="utf-8")
        matches = _scan_text_forbidden(text)
        assert not matches, f"mensajes_wsp_v3.txt contiene patrones internos: {matches}"

    @skip_no_msg_v3
    def test_v3_assert_client_safe_text(self):
        text = MSG_WSP_V3.read_text(encoding="utf-8")
        assert_client_safe_text(text, "mensajes_wsp_v3.txt")

    @skip_no_msg_v4
    def test_v4_no_forbidden_terms(self):
        text = MSG_WSP_V4.read_text(encoding="utf-8")
        matches = _scan_text_forbidden(text)
        assert not matches, f"mensajes_wsp_v4.txt contiene patrones internos: {matches}"

    @skip_no_msg_v4
    def test_v4_assert_client_safe_text(self):
        text = MSG_WSP_V4.read_text(encoding="utf-8")
        assert_client_safe_text(text, "mensajes_wsp_v4.txt")


# ═══════════════════════════════════════════════════════════════════════
# TESTS: PDFs en diagnosticos/
# ═══════════════════════════════════════════════════════════════════════

def _collect_pdfs():
    if not DIAGNOSTICOS_DIR.exists():
        return []
    return sorted(DIAGNOSTICOS_DIR.glob("*.pdf"))


def _collect_notas_json():
    if not DIAGNOSTICOS_DIR.exists():
        return []
    return sorted(DIAGNOSTICOS_DIR.glob("*_notas.json"))


class TestDiagnosticoPdfs:

    @skip_no_diagnosticos
    @pytest.mark.parametrize("pdf_path", _collect_pdfs(), ids=lambda p: p.name)
    def test_pdf_client_safe(self, pdf_path):
        assert_client_safe_binary(pdf_path)


# ═══════════════════════════════════════════════════════════════════════
# TESTS: _notas.json en diagnosticos/
# ═══════════════════════════════════════════════════════════════════════

class TestDiagnosticoNotas:

    @skip_no_diagnosticos
    @pytest.mark.parametrize("json_path", _collect_notas_json(), ids=lambda p: p.name)
    def test_notas_json_client_safe(self, json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        assert_client_safe_json(payload, json_path.name)

    @skip_no_diagnosticos
    @pytest.mark.parametrize("json_path", _collect_notas_json(), ids=lambda p: p.name)
    def test_notas_json_valid(self, json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, (dict, list))


# ═══════════════════════════════════════════════════════════════════════
# TESTS: Scan parametrizado de TODOS los archivos de texto en output/
# ═══════════════════════════════════════════════════════════════════════

def _collect_text_files():
    if not OUTPUT_DIR.exists():
        return []
    text_files = []
    for ext in ("*.txt", "*.csv"):
        text_files.extend(OUTPUT_DIR.glob(ext))
    return sorted(text_files)


class TestAllOutputTextScan:

    @pytest.mark.parametrize("text_path", _collect_text_files(), ids=lambda p: p.name)
    def test_scan_text_no_forbidden_patterns(self, text_path):
        text = text_path.read_text(encoding="utf-8", errors="replace")
        if text_path.suffix == ".csv":
            header = text.split("\n", 1)[0]
            matches = _scan_text_forbidden(header)
        else:
            matches = _scan_text_forbidden(text)
        assert not matches, (
            f"{text_path.name} contiene patrones internos: {matches}"
        )


# ═══════════════════════════════════════════════════════════════════════
# TESTS: leads_verificados
# ═══════════════════════════════════════════════════════════════════════

class TestLeadsVerificados:

    @skip_no_verif_xlsx
    def test_xlsx_no_forbidden_columns(self):
        df = pd.read_excel(LEADS_VERIF_XLSX, nrows=0)
        bad = _forbidden_cols_in_df(df)
        assert not bad, f"leads_verificados.xlsx contiene columnas prohibidas: {bad}"

    @skip_no_verif_csv
    def test_csv_no_forbidden_columns(self):
        df = pd.read_csv(LEADS_VERIF_CSV, nrows=0)
        bad = _forbidden_cols_in_df(df)
        assert not bad, f"leads_verificados.csv contiene columnas prohibidas: {bad}"

    @skip_no_verif_v4
    def test_v4_xlsx_no_forbidden_columns(self):
        df = pd.read_excel(LEADS_VERIF_V4_XLSX, nrows=0)
        bad = _forbidden_cols_in_df(df)
        assert not bad, f"leads_verificados_v4.xlsx contiene columnas prohibidas: {bad}"

    @skip_no_verif_xlsx
    def test_xlsx_assert_client_safe(self):
        df = pd.read_excel(LEADS_VERIF_XLSX, nrows=0)
        assert_client_safe_columns(df)

    @skip_no_verif_csv
    def test_csv_assert_client_safe(self):
        df = pd.read_csv(LEADS_VERIF_CSV, nrows=0)
        assert_client_safe_columns(df)


# ═══════════════════════════════════════════════════════════════════════
# TESTS: JSON manifests
# ═══════════════════════════════════════════════════════════════════════

class TestJsonManifests:

    @skip_no_manifest
    def test_export_manifest_valid_json(self):
        with open(EXPORT_MANIFEST, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @skip_no_manifest
    def test_export_manifest_has_required_keys(self):
        with open(EXPORT_MANIFEST, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ("generated_at", "command", "source", "outputs"):
            assert key in data, f"export_manifest.json falta clave '{key}'"

    @skip_no_valreport
    def test_validation_report_valid_json(self):
        with open(VALIDATION_REPORT, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @skip_no_valreport
    def test_validation_report_has_checks(self):
        with open(VALIDATION_REPORT, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "checks" in data
        assert isinstance(data["checks"], list)


# ═══════════════════════════════════════════════════════════════════════
# TESTS: Seguridad sintetica (no depende de archivos reales)
# ═══════════════════════════════════════════════════════════════════════

class TestSyntheticExportSafety:
    """Tests con DataFrames sinteticos para verificar que las funciones de
    seguridad detectan correctamente columnas prohibidas."""

    def test_clean_df_passes(self):
        df = pd.DataFrame({"empresa": ["A"], "rut": ["12345678-9"], "telefono": ["+56912345678"]})
        assert_client_safe_columns(df)

    def test_df_with_score_total_fails(self):
        df = pd.DataFrame({"empresa": ["A"], "score_total": [85.0]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_df_with_cluster_fails(self):
        df = pd.DataFrame({"empresa": ["A"], "cluster": [1]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_df_with_xgb_score_fails(self):
        df = pd.DataFrame({"empresa": ["A"], "xgb_score": [0.8]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_df_with_km_score_fails(self):
        df = pd.DataFrame({"empresa": ["A"], "km_score": [70.0]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_score_digital_allowed_with_override(self):
        df = pd.DataFrame({"empresa": ["A"], "score_digital": [50.0]})
        assert_client_safe_columns(df, allowed_columns={"score_digital"})

    def test_clean_text_passes(self, clean_text):
        assert_client_safe_text(clean_text, "test_clean")

    def test_dirty_text_fails(self, dirty_text):
        with pytest.raises(ValueError, match="patrones internos"):
            assert_client_safe_text(dirty_text, "test_dirty")

    def test_clean_json_passes(self):
        payload = {"empresa": "Test", "rut": "12345678-9", "win_rate": 0.25}
        assert_client_safe_json(payload, "test_clean_json")

    def test_json_with_score_fails(self):
        payload = {"empresa": "Test", "score_total": 85.0}
        with pytest.raises(ValueError, match="patrones internos"):
            assert_client_safe_json(payload, "test_score_json")

    def test_forbidden_columns_set_not_empty(self):
        assert len(CLIENT_FORBIDDEN_COLUMNS) >= 7

    def test_forbidden_patterns_not_empty(self):
        assert len(CLIENT_FORBIDDEN_PATTERNS) >= 5
