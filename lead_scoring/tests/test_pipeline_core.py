"""
Tests exhaustivos para pipeline_core.py.

Cubre:
  - Constantes (COMBINED_SCORE_WEIGHTS, LEAD_SOURCE_PRIORITY, CLIENT_FORBIDDEN_COLUMNS)
  - find_best_leads_path / load_best_leads_dataframe
  - recompute_score_total / recompute_score_combined
  - assign_cluster_profile / assign_rank
  - resolve_score_column / resolve_rank_column
  - build_crm_dataframe
  - contact_coverage_summary
  - _series_or_default
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline_core import (
    COMBINED_SCORE_WEIGHTS,
    CLIENT_FORBIDDEN_COLUMNS,
    LEAD_SOURCE_PRIORITY,
    assign_cluster_profile,
    assign_rank,
    build_crm_dataframe,
    contact_coverage_summary,
    find_best_leads_path,
    load_best_leads_dataframe,
    recompute_score_combined,
    recompute_score_total,
    resolve_rank_column,
    resolve_score_column,
    _series_or_default,
)
from config import SCORING_WEIGHTS


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _make_scored_df(n: int = 5, *, include_ml: bool = False) -> pd.DataFrame:
    """DataFrame con todas las columnas score_{dim} + score_total."""
    rng = np.random.RandomState(42)
    data: dict = {
        "rut": [f"765432{i:02d}-K" for i in range(n)],
        "nombre": [f"EMPRESA {i} LTDA" for i in range(n)],
    }
    for dim in SCORING_WEIGHTS:
        data[f"score_{dim}"] = rng.uniform(30, 100, n).round(1)
    # score_total calculado con pesos reales
    total = np.zeros(n)
    for dim, w in SCORING_WEIGHTS.items():
        total += data[f"score_{dim}"] * w
    data["score_total"] = np.clip(total, 0, 100).round(1)
    if include_ml:
        data["km_score"] = rng.uniform(30, 90, n).round(1)
        data["xgb_score"] = rng.uniform(30, 90, n).round(1)
    return pd.DataFrame(data)


def _write_dummy_parquet(directory: Path, name: str) -> Path:
    """Escribe un parquet mínimo y retorna el path."""
    p = directory / name
    pd.DataFrame({"rut": ["1-9"]}).to_parquet(p)
    return p


# ══════════════════════════════════════════════════════════════════════
# 1) Constantes — COMBINED_SCORE_WEIGHTS
# ══════════════════════════════════════════════════════════════════════

class TestCombinedScoreWeights:
    def test_sum_is_one(self):
        assert abs(sum(COMBINED_SCORE_WEIGHTS.values()) - 1.0) < 1e-9

    def test_has_score_total(self):
        assert "score_total" in COMBINED_SCORE_WEIGHTS

    def test_has_km_score(self):
        assert "km_score" in COMBINED_SCORE_WEIGHTS

    def test_has_xgb_score(self):
        assert "xgb_score" in COMBINED_SCORE_WEIGHTS

    def test_all_positive(self):
        for k, v in COMBINED_SCORE_WEIGHTS.items():
            assert v > 0, f"{k} debería ser positivo"

    def test_score_total_dominant(self):
        assert COMBINED_SCORE_WEIGHTS["score_total"] > 0.5


# ══════════════════════════════════════════════════════════════════════
# 2) LEAD_SOURCE_PRIORITY
# ══════════════════════════════════════════════════════════════════════

class TestLeadSourcePriority:
    def test_has_three_entries(self):
        assert len(LEAD_SOURCE_PRIORITY) == 3

    def test_enriched_first(self):
        assert LEAD_SOURCE_PRIORITY[0] == "leads_enriched.parquet"

    def test_ml_ranked_second(self):
        assert LEAD_SOURCE_PRIORITY[1] == "leads_ml_ranked.parquet"

    def test_ranked_third(self):
        assert LEAD_SOURCE_PRIORITY[2] == "leads_ranked.parquet"


# ══════════════════════════════════════════════════════════════════════
# 3) CLIENT_FORBIDDEN_COLUMNS
# ══════════════════════════════════════════════════════════════════════

class TestClientForbiddenColumns:
    def test_not_empty(self):
        assert len(CLIENT_FORBIDDEN_COLUMNS) > 0

    def test_has_eight_columns(self):
        assert len(CLIENT_FORBIDDEN_COLUMNS) == 8

    @pytest.mark.parametrize("col", [
        "score_total", "score_combined", "cluster", "cluster_perfil",
        "km_score", "xgb_score", "xgb_predicted_wr", "score_digital",
    ])
    def test_expected_column_present(self, col):
        assert col in CLIENT_FORBIDDEN_COLUMNS


# ══════════════════════════════════════════════════════════════════════
# 4) find_best_leads_path
# ══════════════════════════════════════════════════════════════════════

class TestFindBestLeadsPath:
    def test_returns_enriched_when_all_exist(self, tmp_path):
        for name in LEAD_SOURCE_PRIORITY:
            _write_dummy_parquet(tmp_path, name)
        result = find_best_leads_path(tmp_path)
        assert result is not None
        assert result.name == "leads_enriched.parquet"

    def test_returns_ml_ranked_when_no_enriched(self, tmp_path):
        _write_dummy_parquet(tmp_path, "leads_ml_ranked.parquet")
        _write_dummy_parquet(tmp_path, "leads_ranked.parquet")
        result = find_best_leads_path(tmp_path)
        assert result is not None
        assert result.name == "leads_ml_ranked.parquet"

    def test_returns_ranked_when_only_ranked(self, tmp_path):
        _write_dummy_parquet(tmp_path, "leads_ranked.parquet")
        result = find_best_leads_path(tmp_path)
        assert result is not None
        assert result.name == "leads_ranked.parquet"

    def test_returns_none_when_empty_dir(self, tmp_path):
        result = find_best_leads_path(tmp_path)
        assert result is None

    def test_custom_priority(self, tmp_path):
        _write_dummy_parquet(tmp_path, "custom.parquet")
        result = find_best_leads_path(tmp_path, priority=("custom.parquet",))
        assert result is not None
        assert result.name == "custom.parquet"


# ══════════════════════════════════════════════════════════════════════
# 5) load_best_leads_dataframe
# ══════════════════════════════════════════════════════════════════════

class TestLoadBestLeadsDataframe:
    def test_raises_when_no_files(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_best_leads_dataframe(tmp_path)

    def test_loads_dataframe_when_exists(self, tmp_path):
        _write_dummy_parquet(tmp_path, "leads_ranked.parquet")
        df, path = load_best_leads_dataframe(tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert path.name == "leads_ranked.parquet"

    def test_loads_highest_priority(self, tmp_path):
        for name in LEAD_SOURCE_PRIORITY:
            _write_dummy_parquet(tmp_path, name)
        df, path = load_best_leads_dataframe(tmp_path)
        assert path.name == "leads_enriched.parquet"


# ══════════════════════════════════════════════════════════════════════
# 6) recompute_score_total
# ══════════════════════════════════════════════════════════════════════

class TestRecomputeScoreTotal:
    def test_produces_score_total(self):
        df = _make_scored_df()
        result = recompute_score_total(df)
        assert "score_total" in result.columns

    def test_result_in_range(self):
        df = _make_scored_df(20)
        result = recompute_score_total(df)
        assert (result["score_total"] >= 0).all()
        assert (result["score_total"] <= 100).all()

    def test_consistent_with_weights(self):
        df = _make_scored_df()
        result = recompute_score_total(df)
        for idx in range(len(result)):
            expected = sum(
                result.iloc[idx][f"score_{dim}"] * w
                for dim, w in SCORING_WEIGHTS.items()
            )
            expected = max(0, min(100, round(expected, 1)))
            assert abs(result.iloc[idx]["score_total"] - expected) < 0.2

    def test_missing_column_raises_valueerror(self):
        df = _make_scored_df()
        df = df.drop(columns=["score_actividad"])
        with pytest.raises(ValueError, match="Faltan columnas"):
            recompute_score_total(df)

    def test_does_not_modify_original(self):
        df = _make_scored_df()
        original_scores = df["score_total"].copy()
        _ = recompute_score_total(df)
        pd.testing.assert_series_equal(df["score_total"], original_scores)

    def test_single_row(self):
        df = _make_scored_df(1)
        result = recompute_score_total(df)
        assert len(result) == 1
        assert 0 <= result["score_total"].iloc[0] <= 100

    def test_all_zeros(self):
        df = _make_scored_df()
        for dim in SCORING_WEIGHTS:
            df[f"score_{dim}"] = 0.0
        result = recompute_score_total(df)
        assert (result["score_total"] == 0).all()

    def test_all_hundreds(self):
        df = _make_scored_df()
        for dim in SCORING_WEIGHTS:
            df[f"score_{dim}"] = 100.0
        result = recompute_score_total(df)
        assert (result["score_total"] == 100.0).all()


# ══════════════════════════════════════════════════════════════════════
# 7) recompute_score_combined
# ══════════════════════════════════════════════════════════════════════

class TestRecomputeScoreCombined:
    def test_with_ml_signals(self):
        df = _make_scored_df(include_ml=True)
        result = recompute_score_combined(df)
        assert "score_combined" in result.columns
        assert (result["score_combined"] >= 0).all()
        assert (result["score_combined"] <= 100).all()

    def test_without_ml_signals_uses_baseline(self):
        df = _make_scored_df(include_ml=False)
        result = recompute_score_combined(df)
        # Sin ML signals, score_combined = score_total * (0.70 + 0.15 + 0.15) = score_total
        pd.testing.assert_series_equal(
            result["score_combined"],
            result["score_total"],
            check_names=False,
        )

    def test_missing_score_total_raises(self):
        df = pd.DataFrame({"rut": ["1-9"], "km_score": [50]})
        with pytest.raises(ValueError, match="score_total"):
            recompute_score_combined(df)

    def test_does_not_modify_original(self):
        df = _make_scored_df(include_ml=True)
        original_cols = set(df.columns)
        _ = recompute_score_combined(df)
        assert set(df.columns) == original_cols

    def test_nan_ml_falls_back_to_score_total(self):
        df = _make_scored_df()
        df["km_score"] = np.nan
        df["xgb_score"] = np.nan
        result = recompute_score_combined(df)
        pd.testing.assert_series_equal(
            result["score_combined"],
            result["score_total"],
            check_names=False,
        )

    def test_partial_ml_signals(self):
        df = _make_scored_df()
        df["km_score"] = 80.0
        # xgb_score no existe -> fallback a score_total
        result = recompute_score_combined(df)
        assert "score_combined" in result.columns
        assert (result["score_combined"] >= 0).all()
        assert (result["score_combined"] <= 100).all()

    def test_weights_applied_correctly(self):
        df = pd.DataFrame({
            "rut": ["1-9"],
            "score_total": [80.0],
            "km_score": [60.0],
            "xgb_score": [40.0],
        })
        result = recompute_score_combined(df)
        expected = 80 * 0.70 + 60 * 0.15 + 40 * 0.15
        assert abs(result["score_combined"].iloc[0] - round(expected, 1)) < 0.2


# ══════════════════════════════════════════════════════════════════════
# 8) assign_cluster_profile
# ══════════════════════════════════════════════════════════════════════

class TestAssignClusterProfile:
    def test_four_categories(self):
        df = _make_scored_df(100)
        df = recompute_score_combined(df)
        result = assign_cluster_profile(df)
        categories = set(result["cluster_perfil"].unique())
        expected = {"LEAD BAJO", "LEAD REGULAR", "LEAD BUENO", "LEAD IDEAL"}
        assert categories == expected

    def test_column_exists(self):
        df = _make_scored_df(20)
        df = recompute_score_combined(df)
        result = assign_cluster_profile(df)
        assert "cluster_perfil" in result.columns

    def test_raises_without_score_combined(self):
        df = _make_scored_df()
        with pytest.raises(ValueError, match="score_combined"):
            assign_cluster_profile(df)

    def test_does_not_modify_original(self):
        df = _make_scored_df(20)
        df = recompute_score_combined(df)
        original_cols = set(df.columns)
        _ = assign_cluster_profile(df)
        assert "cluster_perfil" not in df.columns

    def test_percentile_distribution(self):
        # Con 100 filas, ~40% BAJO, ~30% REGULAR, ~20% BUENO, ~10% IDEAL
        df = _make_scored_df(100)
        df = recompute_score_combined(df)
        result = assign_cluster_profile(df)
        counts = result["cluster_perfil"].value_counts()
        assert counts.get("LEAD BAJO", 0) >= 30  # ~40% ± tolerancia
        assert counts.get("LEAD IDEAL", 0) >= 5   # ~10% ± tolerancia


# ══════════════════════════════════════════════════════════════════════
# 9) assign_rank
# ══════════════════════════════════════════════════════════════════════

class TestAssignRank:
    def test_starts_at_one(self, sample_leads_df):
        result = assign_rank(sample_leads_df, "score_total", "rank")
        assert result["rank"].min() == 1

    def test_sequential(self, sample_leads_df):
        result = assign_rank(sample_leads_df, "score_total", "rank")
        expected = list(range(1, len(result) + 1))
        assert list(result["rank"]) == expected

    def test_descending_order(self, sample_leads_df):
        result = assign_rank(sample_leads_df, "score_total", "rank")
        scores = result["score_total"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_custom_column_names(self):
        df = pd.DataFrame({"my_score": [10, 50, 30], "rut": ["a", "b", "c"]})
        result = assign_rank(df, "my_score", "my_rank")
        assert "my_rank" in result.columns
        assert list(result["my_rank"]) == [1, 2, 3]
        assert result.iloc[0]["my_score"] == 50

    def test_does_not_modify_original(self, sample_leads_df):
        original_index = sample_leads_df.index.tolist()
        _ = assign_rank(sample_leads_df, "score_total", "rank")
        assert sample_leads_df.index.tolist() == original_index


# ══════════════════════════════════════════════════════════════════════
# 10) resolve_score_column
# ══════════════════════════════════════════════════════════════════════

class TestResolveScoreColumn:
    def test_prefers_combined(self):
        df = pd.DataFrame({"score_combined": [1], "score_total": [1]})
        assert resolve_score_column(df) == "score_combined"

    def test_falls_back_to_total(self):
        df = pd.DataFrame({"score_total": [1]})
        assert resolve_score_column(df) == "score_total"

    def test_raises_when_neither(self):
        df = pd.DataFrame({"rut": ["1-9"]})
        with pytest.raises(ValueError):
            resolve_score_column(df)


# ══════════════════════════════════════════════════════════════════════
# 11) resolve_rank_column
# ══════════════════════════════════════════════════════════════════════

class TestResolveRankColumn:
    def test_prefers_rank_ml(self):
        df = pd.DataFrame({"rank_ml": [1], "rank": [1]})
        assert resolve_rank_column(df) == "rank_ml"

    def test_falls_back_to_rank(self):
        df = pd.DataFrame({"rank": [1]})
        assert resolve_rank_column(df) == "rank"

    def test_raises_when_neither(self):
        df = pd.DataFrame({"rut": ["1-9"]})
        with pytest.raises(ValueError):
            resolve_rank_column(df)


# ══════════════════════════════════════════════════════════════════════
# 12) build_crm_dataframe
# ══════════════════════════════════════════════════════════════════════

class TestBuildCrmDataframe:
    def test_expected_columns(self, sample_leads_df):
        crm = build_crm_dataframe(sample_leads_df)
        for col in ("empresa", "rut", "estado", "canal", "contacto",
                     "telefono", "email", "prioridad"):
            assert col in crm.columns, f"Falta columna {col}"

    def test_no_forbidden_columns(self, sample_enriched_df):
        crm = build_crm_dataframe(sample_enriched_df)
        for col in CLIENT_FORBIDDEN_COLUMNS:
            assert col not in crm.columns, f"Columna prohibida {col} en CRM"

    def test_uses_rank_ml_for_prioridad(self, sample_enriched_df):
        crm = build_crm_dataframe(sample_enriched_df)
        assert "prioridad" in crm.columns
        pd.testing.assert_series_equal(
            crm["prioridad"],
            sample_enriched_df["rank_ml"],
            check_names=False,
        )

    def test_uses_rank_when_no_rank_ml(self, sample_leads_df):
        crm = build_crm_dataframe(sample_leads_df)
        assert "prioridad" in crm.columns
        pd.testing.assert_series_equal(
            crm["prioridad"],
            sample_leads_df["rank"],
            check_names=False,
        )

    def test_generates_prioridad_when_no_rank(self):
        df = pd.DataFrame({"rut": ["1-9", "2-8"], "nombre": ["A", "B"]})
        crm = build_crm_dataframe(df)
        assert list(crm["prioridad"]) == [1, 2]

    def test_default_channel_whatsapp(self, sample_leads_df):
        crm = build_crm_dataframe(sample_leads_df)
        assert (crm["canal"] == "WhatsApp").all()

    def test_custom_channel(self, sample_leads_df):
        crm = build_crm_dataframe(sample_leads_df, default_channel="Email")
        assert (crm["canal"] == "Email").all()

    def test_estado_pendiente(self, sample_leads_df):
        crm = build_crm_dataframe(sample_leads_df)
        assert (crm["estado"] == "Pendiente").all()

    def test_tender_info_propagated(self, sample_leads_df):
        crm = build_crm_dataframe(
            sample_leads_df,
            tender_codigo="4000-1-LP26",
            tender_nombre="Obra Vial",
        )
        assert (crm["licitacion_codigo"] == "4000-1-LP26").all()
        assert (crm["licitacion_nombre"] == "Obra Vial").all()

    def test_row_count_matches(self, sample_leads_df):
        crm = build_crm_dataframe(sample_leads_df)
        assert len(crm) == len(sample_leads_df)


# ══════════════════════════════════════════════════════════════════════
# 13) contact_coverage_summary
# ══════════════════════════════════════════════════════════════════════

class TestContactCoverageSummary:
    def test_total_leads(self, sample_enriched_df):
        summary = contact_coverage_summary(sample_enriched_df)
        assert summary["total_leads"] == len(sample_enriched_df)

    def test_phone_count(self, sample_enriched_df):
        summary = contact_coverage_summary(sample_enriched_df)
        expected = int(sample_enriched_df["telefono"].notna().sum())
        assert summary["con_telefono"] == expected

    def test_email_count(self, sample_enriched_df):
        summary = contact_coverage_summary(sample_enriched_df)
        expected = int(sample_enriched_df["email"].notna().sum())
        assert summary["con_email"] == expected

    def test_web_count(self, sample_enriched_df):
        summary = contact_coverage_summary(sample_enriched_df)
        expected = int(sample_enriched_df["web"].notna().sum())
        assert summary["con_web"] == expected

    def test_missing_columns_no_crash(self):
        df = pd.DataFrame({"rut": ["1-9", "2-8"]})
        summary = contact_coverage_summary(df)
        assert summary["total_leads"] == 2
        assert summary["con_telefono"] == 0
        assert summary["con_email"] == 0
        assert summary["con_web"] == 0
        assert summary["con_rival"] == 0

    def test_empty_dataframe(self):
        df = pd.DataFrame({"rut": []})
        summary = contact_coverage_summary(df)
        assert summary["total_leads"] == 0

    def test_all_keys_present(self, sample_enriched_df):
        summary = contact_coverage_summary(sample_enriched_df)
        for key in ("total_leads", "con_telefono", "con_email",
                     "con_web", "con_rival", "pdf_listo", "outreach_listo"):
            assert key in summary


# ══════════════════════════════════════════════════════════════════════
# 14) _series_or_default
# ══════════════════════════════════════════════════════════════════════

class TestSeriesOrDefault:
    def test_existing_column(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = _series_or_default(df, "a", 0)
        pd.testing.assert_series_equal(result, df["a"])

    def test_missing_column(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = _series_or_default(df, "b", "default")
        assert len(result) == 3
        assert (result == "default").all()

    def test_default_preserves_index(self):
        df = pd.DataFrame({"a": [1, 2]}, index=[10, 20])
        result = _series_or_default(df, "b", 0)
        assert list(result.index) == [10, 20]

    def test_empty_dataframe(self):
        df = pd.DataFrame({"a": []})
        result = _series_or_default(df, "b", 99)
        assert len(result) == 0
