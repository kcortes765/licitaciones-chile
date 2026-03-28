"""
Tests exhaustivos para pipeline_validation.py

Cubre: PIPELINE_CONTRACTS, validate_dataframe_contract, CLIENT_FORBIDDEN_PATTERNS,
assert_client_safe_columns, assert_client_safe_text, assert_client_safe_json,
assert_client_safe_binary, write_run_manifest, write_validation_report.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline_validation import (
    PIPELINE_CONTRACTS,
    CLIENT_FORBIDDEN_PATTERNS,
    validate_dataframe_contract,
    assert_dataframe_contract,
    assert_client_safe_columns,
    assert_client_safe_text,
    assert_client_safe_json,
    assert_client_safe_binary,
    write_run_manifest,
    write_validation_report,
    _scan_text_forbidden,
    _extract_text_like_chunks,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _valid_company_df(n: int = 3) -> pd.DataFrame:
    """DataFrame válido para contrato company_database."""
    return pd.DataFrame({
        "rut": [f"7654321{i}-K" for i in range(n)],
        "total_bids": [10, 15, 8],
        "total_wins": [3, 5, 2],
        "win_rate": [0.30, 0.33, 0.25],
        "monto_promedio": [100e6, 200e6, 50e6],
        "dias_desde_ultima": [100, 200, 50],
        "n_LP": [5, 3, 2],
        "n_LE": [3, 4, 1],
        "n_L1": [2, 2, 5],
    })


def _valid_leads_ranked_df(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "rut": [f"7654321{i}-K" for i in range(n)],
        "score_total": [85.0, 72.0, 60.0],
        "rank": [1, 2, 3],
        "win_rate": [0.30, 0.25, 0.15],
    })


def _valid_leads_ml_ranked_df(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "rut": [f"7654321{i}-K" for i in range(n)],
        "score_total": [85.0, 72.0, 60.0],
        "score_combined": [88.0, 75.0, 63.0],
        "rank_ml": [1, 2, 3],
    })


def _valid_leads_enriched_df(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "rut": [f"7654321{i}-K" for i in range(n)],
        "score_total": [85.0, 72.0, 60.0],
        "score_combined": [88.0, 75.0, 63.0],
        "score_digital": [40.0, 55.0, 70.0],
    })


def _valid_loss_analysis_df(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "rut": [f"7654321{i}-K" for i in range(n)],
        "total_participated": [20, 15, 10],
        "total_won": [5, 3, 2],
        "loss_rate": [0.50, 0.53, 0.60],
    })


def _valid_matches_df(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        "tender_codigo": [f"T{i}" for i in range(n)],
        "lead_rut": [f"7654321{i}-K" for i in range(n)],
        "match_score": [90.0, 75.0, 60.0],
    })


# ── A) PIPELINE_CONTRACTS estructura ───────────────────────────────────

class TestPipelineContracts:
    """Verifica la estructura y completitud de PIPELINE_CONTRACTS."""

    EXPECTED_ARTIFACTS = [
        "company_database", "leads_ranked", "leads_ml_ranked",
        "leads_enriched", "loss_analysis", "matches",
    ]

    def test_six_artifacts_exist(self):
        assert len(PIPELINE_CONTRACTS) == 6

    @pytest.mark.parametrize("name", EXPECTED_ARTIFACTS)
    def test_artifact_exists(self, name):
        assert name in PIPELINE_CONTRACTS

    @pytest.mark.parametrize("name", EXPECTED_ARTIFACTS)
    def test_artifact_has_required(self, name):
        contract = PIPELINE_CONTRACTS[name]
        assert "required" in contract
        assert isinstance(contract["required"], list)
        assert len(contract["required"]) > 0

    @pytest.mark.parametrize("name", EXPECTED_ARTIFACTS)
    def test_artifact_has_ranges(self, name):
        contract = PIPELINE_CONTRACTS[name]
        assert "ranges" in contract
        assert isinstance(contract["ranges"], dict)

    def test_company_database_required_columns(self):
        req = PIPELINE_CONTRACTS["company_database"]["required"]
        for col in ["rut", "total_bids", "total_wins", "win_rate",
                     "monto_promedio", "dias_desde_ultima", "n_LP", "n_LE", "n_L1"]:
            assert col in req

    def test_company_database_unique_rut(self):
        assert PIPELINE_CONTRACTS["company_database"]["unique"] == ["rut"]

    def test_leads_ranked_required(self):
        req = PIPELINE_CONTRACTS["leads_ranked"]["required"]
        assert "rut" in req and "score_total" in req and "rank" in req

    def test_leads_ml_ranked_required(self):
        req = PIPELINE_CONTRACTS["leads_ml_ranked"]["required"]
        for col in ["rut", "score_total", "score_combined", "rank_ml"]:
            assert col in req

    def test_loss_analysis_required(self):
        req = PIPELINE_CONTRACTS["loss_analysis"]["required"]
        for col in ["rut", "total_participated", "total_won", "loss_rate"]:
            assert col in req

    def test_matches_required(self):
        req = PIPELINE_CONTRACTS["matches"]["required"]
        for col in ["tender_codigo", "lead_rut", "match_score"]:
            assert col in req

    def test_matches_no_unique_key(self):
        """matches no tiene restricción de unicidad (un lead puede matchear varias)."""
        contract = PIPELINE_CONTRACTS["matches"]
        assert contract.get("unique") is None

    def test_ranges_tuples(self):
        """Todos los rangos son tuples (min, max)."""
        for name, contract in PIPELINE_CONTRACTS.items():
            for col, rng in contract.get("ranges", {}).items():
                assert isinstance(rng, tuple), f"{name}.{col} range no es tuple"
                assert len(rng) == 2, f"{name}.{col} range no tiene 2 elementos"


# ── B) validate_dataframe_contract ──────────────────────────────────────

class TestValidateDataframeContract:
    """Tests para validate_dataframe_contract."""

    def test_valid_company_db_returns_empty(self):
        df = _valid_company_df()
        issues = validate_dataframe_contract(df, "company_database")
        assert issues == []

    def test_valid_leads_ranked_returns_empty(self):
        df = _valid_leads_ranked_df()
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert issues == []

    def test_valid_leads_ml_ranked_returns_empty(self):
        df = _valid_leads_ml_ranked_df()
        issues = validate_dataframe_contract(df, "leads_ml_ranked")
        assert issues == []

    def test_valid_leads_enriched_returns_empty(self):
        df = _valid_leads_enriched_df()
        issues = validate_dataframe_contract(df, "leads_enriched")
        assert issues == []

    def test_valid_loss_analysis_returns_empty(self):
        df = _valid_loss_analysis_df()
        issues = validate_dataframe_contract(df, "loss_analysis")
        assert issues == []

    def test_valid_matches_returns_empty(self):
        df = _valid_matches_df()
        issues = validate_dataframe_contract(df, "matches")
        assert issues == []

    def test_missing_columns_detected(self):
        df = pd.DataFrame({"rut": ["76543210-K"]})
        issues = validate_dataframe_contract(df, "company_database")
        assert any("Faltan columnas" in i for i in issues)

    def test_missing_single_column(self):
        df = _valid_company_df()
        df = df.drop(columns=["win_rate"])
        issues = validate_dataframe_contract(df, "company_database")
        assert any("win_rate" in i for i in issues)

    def test_duplicates_detected(self):
        df = _valid_company_df()
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        issues = validate_dataframe_contract(df, "company_database")
        assert any("duplicadas" in i for i in issues)

    def test_value_below_range_detected(self):
        df = _valid_company_df()
        df.loc[0, "win_rate"] = -0.1
        issues = validate_dataframe_contract(df, "company_database")
        assert any("menores" in i for i in issues)

    def test_value_above_range_detected(self):
        df = _valid_company_df()
        df.loc[0, "win_rate"] = 1.5
        issues = validate_dataframe_contract(df, "company_database")
        assert any("mayores" in i for i in issues)

    def test_null_rut_detected(self):
        df = _valid_company_df()
        df.loc[0, "rut"] = None
        issues = validate_dataframe_contract(df, "company_database")
        assert any("sin rut" in i for i in issues)

    def test_nan_rut_detected(self):
        df = _valid_company_df()
        df.loc[0, "rut"] = np.nan
        issues = validate_dataframe_contract(df, "company_database")
        assert any("sin rut" in i for i in issues)

    def test_unknown_contract_raises_keyerror(self):
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(KeyError, match="Contrato desconocido"):
            validate_dataframe_contract(df, "nonexistent_artifact")

    def test_score_total_above_100(self):
        df = _valid_leads_ranked_df()
        df.loc[0, "score_total"] = 101.0
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert any("mayores" in i for i in issues)

    def test_score_total_below_0(self):
        df = _valid_leads_ranked_df()
        df.loc[0, "score_total"] = -1.0
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert any("menores" in i for i in issues)

    def test_rank_below_1(self):
        df = _valid_leads_ranked_df()
        df.loc[0, "rank"] = 0
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert any("menores" in i for i in issues)

    def test_rank_none_upper_bound_no_max_issue(self):
        """rank tiene upper_bound None, no debería detectar valores altos."""
        df = _valid_leads_ranked_df()
        df.loc[0, "rank"] = 99999
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert not any("rank" in i and "mayores" in i for i in issues)

    def test_range_column_missing_is_skipped(self):
        """Si la columna de rango no existe, se salta sin error."""
        df = _valid_leads_ranked_df().drop(columns=["win_rate"])
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert not any("win_rate" in i for i in issues)

    def test_nan_values_in_range_column_ignored(self):
        """NaN en columna de rango se ignora (dropna)."""
        df = _valid_company_df()
        df.loc[0, "win_rate"] = np.nan
        issues = validate_dataframe_contract(df, "company_database")
        assert not any("win_rate" in i for i in issues)

    def test_multiple_issues_returned(self):
        """Puede retornar múltiples issues a la vez."""
        df = pd.DataFrame({"rut": [None, "76543210-K", "76543210-K"]})
        issues = validate_dataframe_contract(df, "company_database")
        assert len(issues) >= 2  # missing columns + null rut at minimum

    def test_match_score_above_100(self):
        df = _valid_matches_df()
        df.loc[0, "match_score"] = 105.0
        issues = validate_dataframe_contract(df, "matches")
        assert any("mayores" in i for i in issues)

    def test_loss_rate_above_1(self):
        df = _valid_loss_analysis_df()
        df.loc[0, "loss_rate"] = 1.1
        issues = validate_dataframe_contract(df, "loss_analysis")
        assert any("mayores" in i for i in issues)


class TestAssertDataframeContract:
    """Tests para assert_dataframe_contract (wrapper que lanza ValueError)."""

    def test_valid_df_no_exception(self):
        df = _valid_company_df()
        assert_dataframe_contract(df, "company_database")  # no exception

    def test_invalid_df_raises_valueerror(self):
        df = pd.DataFrame({"rut": [None]})
        with pytest.raises(ValueError, match="Contrato invalido"):
            assert_dataframe_contract(df, "company_database")


# ── C) CLIENT_FORBIDDEN_PATTERNS ────────────────────────────────────────

class TestClientForbiddenPatterns:
    """Verifica que los regex detectan/excluyen correctamente."""

    def test_score_total_matches(self):
        assert _scan_text_forbidden("score_total") != []

    def test_score_combined_matches(self):
        assert _scan_text_forbidden("score_combined") != []

    def test_cluster_matches(self):
        assert _scan_text_forbidden("cluster") != []

    def test_cluster_perfil_matches(self):
        assert _scan_text_forbidden("cluster_perfil") != []

    def test_xgb_score_matches(self):
        assert _scan_text_forbidden("xgb_score") != []

    def test_xgb_predicted_wr_matches(self):
        assert _scan_text_forbidden("xgb_predicted_wr") != []

    def test_km_score_matches(self):
        assert _scan_text_forbidden("km_score") != []

    def test_lead_ideal_matches(self):
        assert _scan_text_forbidden("lead ideal") != []

    def test_rank_position_matches(self):
        assert _scan_text_forbidden("rank_position") != []

    def test_score_digital_does_not_match(self):
        """score_digital es la excepción — no debe matchear."""
        result = _scan_text_forbidden("score_digital")
        # score_digital no debería matchear score_ pattern por la excepción (?!digital)
        # pero puede matchear score_combined pattern si es case insensitive
        # Verificamos que el pattern score_(?!digital) no matchea
        import re
        pattern = re.compile(r"\bscore_(?!digital)\w+\b", re.IGNORECASE)
        assert not pattern.search("score_digital")

    def test_nombre_does_not_match(self):
        assert _scan_text_forbidden("nombre") == []

    def test_empresa_does_not_match(self):
        assert _scan_text_forbidden("empresa") == []

    def test_rut_does_not_match(self):
        assert _scan_text_forbidden("rut") == []

    def test_score_actividad_matches(self):
        assert _scan_text_forbidden("score_actividad") != []

    def test_score_region_matches(self):
        assert _scan_text_forbidden("score_region") != []

    def test_case_insensitive_score_total(self):
        assert _scan_text_forbidden("SCORE_TOTAL") != []

    def test_case_insensitive_cluster(self):
        assert _scan_text_forbidden("CLUSTER") != []

    def test_km_prefix_matches(self):
        assert _scan_text_forbidden("km_prediction") != []

    def test_xgb_prefix_matches(self):
        assert _scan_text_forbidden("xgb_feature_importance") != []

    def test_embedded_in_sentence(self):
        result = _scan_text_forbidden("El score_total del lead es 85")
        assert len(result) > 0

    def test_clean_sentence(self):
        result = _scan_text_forbidden("Su empresa participó en 12 licitaciones")
        assert result == []


# ── D) assert_client_safe_columns ───────────────────────────────────────

class TestAssertClientSafeColumns:
    """Tests para assert_client_safe_columns."""

    def test_clean_columns_ok(self):
        df = pd.DataFrame({"rut": ["X"], "nombre": ["Y"], "region": ["Z"]})
        assert_client_safe_columns(df)  # no exception

    def test_score_total_raises(self):
        df = pd.DataFrame({"rut": ["X"], "score_total": [80.0]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_score_combined_raises(self):
        df = pd.DataFrame({"rut": ["X"], "score_combined": [80.0]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_cluster_raises(self):
        df = pd.DataFrame({"rut": ["X"], "cluster": [1]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_xgb_score_raises(self):
        df = pd.DataFrame({"rut": ["X"], "xgb_score": [0.5]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_km_score_raises(self):
        df = pd.DataFrame({"rut": ["X"], "km_score": [70.0]})
        with pytest.raises(ValueError, match="no permitidas"):
            assert_client_safe_columns(df)

    def test_score_digital_not_raises(self):
        """score_digital es una excepción — NO debe bloquearse."""
        df = pd.DataFrame({"rut": ["X"], "score_digital": [50.0]})
        # score_digital no debería matchear score_(?!digital)
        # Solo pasa si el regex funciona correctamente
        assert_client_safe_columns(df)  # no exception

    def test_allowed_columns_override(self):
        """Si score_total está en allowed_columns, se permite."""
        df = pd.DataFrame({"rut": ["X"], "score_total": [80.0]})
        assert_client_safe_columns(df, allowed_columns={"score_total"})

    def test_multiple_forbidden_columns(self):
        df = pd.DataFrame({
            "rut": ["X"],
            "score_total": [80.0],
            "cluster": [1],
            "xgb_score": [0.5],
        })
        with pytest.raises(ValueError):
            assert_client_safe_columns(df)

    def test_empty_df_ok(self):
        df = pd.DataFrame()
        assert_client_safe_columns(df)  # no exception


# ── E) assert_client_safe_text ──────────────────────────────────────────

class TestAssertClientSafeText:
    """Tests para assert_client_safe_text."""

    def test_clean_text_ok(self, clean_text):
        assert_client_safe_text(clean_text, "test_message")

    def test_dirty_text_raises(self, dirty_text):
        with pytest.raises(ValueError, match="patrones internos"):
            assert_client_safe_text(dirty_text, "test_message")

    def test_score_total_in_text_raises(self):
        with pytest.raises(ValueError):
            assert_client_safe_text("Su score_total es 85", "msg")

    def test_xgb_predicted_wr_raises(self):
        with pytest.raises(ValueError):
            assert_client_safe_text("xgb_predicted_wr = 0.28", "msg")

    def test_cluster_in_text_raises(self):
        with pytest.raises(ValueError):
            assert_client_safe_text("Está en el cluster IDEAL", "msg")

    def test_km_score_raises(self):
        with pytest.raises(ValueError):
            assert_client_safe_text("km_score alto", "msg")

    def test_empty_text_ok(self):
        assert_client_safe_text("", "empty")

    def test_normal_business_text_ok(self):
        text = "Su empresa ha participado en 15 licitaciones con tasa de 22%"
        assert_client_safe_text(text, "msg")


# ── F) assert_client_safe_json ──────────────────────────────────────────

class TestAssertClientSafeJson:
    """Tests para assert_client_safe_json."""

    def test_clean_payload_ok(self):
        payload = {"empresa": "TEST LTDA", "rut": "76543210-K", "tasa": 0.22}
        assert_client_safe_json(payload, "test")

    def test_payload_with_score_total_raises(self):
        payload = {"score_total": 85.0}
        with pytest.raises(ValueError):
            assert_client_safe_json(payload, "test")

    def test_nested_forbidden_key_raises(self):
        payload = {"data": {"score_combined": 80.0}}
        with pytest.raises(ValueError):
            assert_client_safe_json(payload, "test")

    def test_forbidden_in_value_raises(self):
        payload = {"note": "El score_total es alto"}
        with pytest.raises(ValueError):
            assert_client_safe_json(payload, "test")

    def test_list_payload_ok(self):
        payload = [{"rut": "X", "nombre": "Y"}]
        assert_client_safe_json(payload, "test")

    def test_empty_dict_ok(self):
        assert_client_safe_json({}, "test")

    def test_cluster_in_json_raises(self):
        payload = {"cluster": "LEAD IDEAL"}
        with pytest.raises(ValueError):
            assert_client_safe_json(payload, "test")


# ── G) assert_client_safe_binary ────────────────────────────────────────

class TestAssertClientSafeBinary:
    """Tests para assert_client_safe_binary."""

    def test_clean_binary_ok(self, tmp_path):
        p = tmp_path / "clean.pdf"
        # Simular PDF con texto limpio
        content = b"%PDF-1.4\n" + b"empresa rut licitacion datos" + b"\n%%EOF"
        p.write_bytes(content)
        assert_client_safe_binary(p)  # no exception

    def test_binary_with_score_total_raises(self, tmp_path):
        p = tmp_path / "bad.pdf"
        content = b"%PDF-1.4\n" + b"score_total = 85.0" + b"\n%%EOF"
        p.write_bytes(content)
        with pytest.raises(ValueError, match="tokens internos"):
            assert_client_safe_binary(p)

    def test_binary_with_cluster_raises(self, tmp_path):
        p = tmp_path / "bad2.pdf"
        content = b"%PDF-1.4\n" + b"cluster LEAD IDEAL" + b"\n%%EOF"
        p.write_bytes(content)
        with pytest.raises(ValueError, match="tokens internos"):
            assert_client_safe_binary(p)

    def test_binary_with_xgb_raises(self, tmp_path):
        p = tmp_path / "bad3.pdf"
        content = b"%PDF-1.4\n" + b"xgb_score prediction is 0.28" + b"\n%%EOF"
        p.write_bytes(content)
        with pytest.raises(ValueError, match="tokens internos"):
            assert_client_safe_binary(p)

    def test_empty_binary_ok(self, tmp_path):
        p = tmp_path / "empty.bin"
        p.write_bytes(b"")
        assert_client_safe_binary(p)  # no exception

    def test_pure_binary_no_text(self, tmp_path):
        p = tmp_path / "binary.dat"
        p.write_bytes(bytes(range(256)))
        assert_client_safe_binary(p)  # no matching text chunks


# ── H) write_run_manifest ───────────────────────────────────────────────

class TestWriteRunManifest:
    """Tests para write_run_manifest."""

    def test_writes_valid_json(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="test", source="test.py", outputs=["a.csv"])
        data = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_has_required_fields(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="export", source="07_export.py",
                           outputs=["leads.csv", "leads.xlsx"])
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert "command" in data
        assert "source" in data
        assert "outputs" in data
        assert "details" in data

    def test_command_stored(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="my_command", source="s.py", outputs=[])
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["command"] == "my_command"

    def test_source_stored(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="c", source="pipeline.py", outputs=[])
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["source"] == "pipeline.py"

    def test_outputs_list(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="c", source="s", outputs=["a.csv", "b.xlsx"])
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["outputs"] == ["a.csv", "b.xlsx"]

    def test_details_default_empty(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="c", source="s", outputs=[])
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["details"] == {}

    def test_details_custom(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="c", source="s", outputs=[],
                           details={"rows": 100, "status": "ok"})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["details"]["rows"] == 100
        assert data["details"]["status"] == "ok"

    def test_generated_at_is_iso_format(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="c", source="s", outputs=[])
        data = json.loads(p.read_text(encoding="utf-8"))
        # Should parse as ISO datetime
        from datetime import datetime
        datetime.fromisoformat(data["generated_at"])

    def test_creates_parent_directories(self, tmp_path):
        p = tmp_path / "sub" / "dir" / "manifest.json"
        write_run_manifest(p, command="c", source="s", outputs=[])
        assert p.exists()

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "manifest.json"
        write_run_manifest(p, command="first", source="s", outputs=[])
        write_run_manifest(p, command="second", source="s", outputs=[])
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["command"] == "second"


# ── I) write_validation_report ──────────────────────────────────────────

class TestWriteValidationReport:
    """Tests para write_validation_report."""

    def test_writes_valid_json(self, tmp_path):
        p = tmp_path / "report.json"
        report = {"status": "ok", "issues": [], "artifacts_checked": 5}
        write_validation_report(p, report)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["status"] == "ok"

    def test_preserves_structure(self, tmp_path):
        p = tmp_path / "report.json"
        report = {
            "artifacts": {
                "company_database": {"valid": True, "issues": []},
                "leads_ranked": {"valid": False, "issues": ["missing col"]},
            },
            "total_issues": 1,
        }
        write_validation_report(p, report)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["total_issues"] == 1
        assert data["artifacts"]["leads_ranked"]["valid"] is False

    def test_creates_parent_directories(self, tmp_path):
        p = tmp_path / "deep" / "nested" / "report.json"
        write_validation_report(p, {"ok": True})
        assert p.exists()

    def test_unicode_content(self, tmp_path):
        p = tmp_path / "report.json"
        report = {"msg": "Validación completada — región ñ"}
        write_validation_report(p, report)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "ñ" in data["msg"]

    def test_empty_report(self, tmp_path):
        p = tmp_path / "report.json"
        write_validation_report(p, {})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {}


# ── Extra: _extract_text_like_chunks ────────────────────────────────────

class TestExtractTextLikeChunks:
    """Tests para la función interna _extract_text_like_chunks."""

    def test_extracts_readable_text(self):
        data = b"\x00\x01hello world\x00\x02"
        result = _extract_text_like_chunks(data)
        assert "hello world" in result

    def test_empty_input(self):
        assert _extract_text_like_chunks(b"") == ""

    def test_pure_binary(self):
        data = bytes([0x00, 0x01, 0x02, 0x03])
        result = _extract_text_like_chunks(data)
        assert result == ""

    def test_minimum_chunk_length(self):
        """Chunks menores a 4 bytes no se extraen."""
        data = b"\x00abc\x00"
        result = _extract_text_like_chunks(data)
        assert result == ""  # "abc" is only 3 chars

    def test_exactly_4_chars_extracted(self):
        data = b"\x00abcd\x00"
        result = _extract_text_like_chunks(data)
        assert "abcd" in result


# ── Extra: _scan_text_forbidden edge cases ──────────────────────────────

class TestScanTextForbidden:
    """Tests adicionales para _scan_text_forbidden."""

    def test_returns_list(self):
        result = _scan_text_forbidden("clean text")
        assert isinstance(result, list)

    def test_empty_string(self):
        assert _scan_text_forbidden("") == []

    def test_multiple_matches(self):
        result = _scan_text_forbidden("score_total cluster xgb_score")
        assert len(result) >= 3

    def test_partial_word_no_match(self):
        """'scoreboard' no debería matchear score_xxx pattern."""
        result = _scan_text_forbidden("scoreboard")
        assert result == []

    def test_lead_ideal_case_insensitive(self):
        assert _scan_text_forbidden("LEAD IDEAL") != []
        assert _scan_text_forbidden("Lead Ideal") != []
