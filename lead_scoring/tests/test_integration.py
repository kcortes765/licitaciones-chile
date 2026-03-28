"""
Tests de integración end-to-end para el pipeline de lead scoring.

Verifican que la cadena completa funciona con datos reales:
company_db → calculate_scores → score_total → score_combined → rank → CRM export.

Todos los tests usan datos reales y se saltan si los parquets no existen.
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ── Setup paths ─────────────────────────────────────────────────────────
LEAD_SCORING_DIR = Path(__file__).resolve().parent.parent
if str(LEAD_SCORING_DIR) not in sys.path:
    sys.path.insert(0, str(LEAD_SCORING_DIR))

from config import SCORING_WEIGHTS, FILTERED_DIR, OUTPUT_DIR
from pipeline_core import (
    CLIENT_FORBIDDEN_COLUMNS,
    COMBINED_SCORE_WEIGHTS,
    assign_cluster_profile,
    assign_rank,
    build_crm_dataframe,
    contact_coverage_summary,
    recompute_score_combined,
    recompute_score_total,
    resolve_rank_column,
    resolve_score_column,
)
from pipeline_validation import (
    PIPELINE_CONTRACTS,
    assert_client_safe_columns,
    validate_dataframe_contract,
)

score_mod = import_module("05_score_leads")
calculate_scores = score_mod.calculate_scores

# ── Paths y skip markers ────────────────────────────────────────────────
COMPANY_DB_PATH = FILTERED_DIR / "company_database.parquet"
LEADS_RANKED_PATH = FILTERED_DIR / "leads_ranked.parquet"
LEADS_ML_RANKED_PATH = FILTERED_DIR / "leads_ml_ranked.parquet"
LEADS_ENRICHED_PATH = FILTERED_DIR / "leads_enriched.parquet"
LOSS_ANALYSIS_PATH = OUTPUT_DIR / "loss_analysis.parquet"

skip_no_company_db = pytest.mark.skipif(
    not COMPANY_DB_PATH.exists(), reason="company_database.parquet no disponible"
)
skip_no_leads_ranked = pytest.mark.skipif(
    not LEADS_RANKED_PATH.exists(), reason="leads_ranked.parquet no disponible"
)
skip_no_leads_ml_ranked = pytest.mark.skipif(
    not LEADS_ML_RANKED_PATH.exists(), reason="leads_ml_ranked.parquet no disponible"
)
skip_no_leads_enriched = pytest.mark.skipif(
    not LEADS_ENRICHED_PATH.exists(), reason="leads_enriched.parquet no disponible"
)
skip_no_loss_analysis = pytest.mark.skipif(
    not LOSS_ANALYSIS_PATH.exists(), reason="loss_analysis.parquet no disponible"
)


# =====================================================================
# 1. Score flow: company_db → calculate_scores → score_total [0,100]
# =====================================================================

class TestCalculateScoresOnRealData:
    """Correr calculate_scores sobre company_database real."""

    @skip_no_company_db
    def test_score_total_in_range(self):
        """score_total debe estar en [0, 100] para todas las filas."""
        df = pd.read_parquet(COMPANY_DB_PATH)
        # Filtrar empresas con mínima actividad (como hace el pipeline real)
        active = df[df["total_bids"] >= 2].copy()
        scored = calculate_scores(active)
        assert (scored["score_total"] >= 0).all(), "Hay scores < 0"
        assert (scored["score_total"] <= 100).all(), "Hay scores > 100"

    @skip_no_company_db
    def test_all_score_dimensions_created(self):
        """calculate_scores debe crear score_{dim} para las 9 dimensiones."""
        df = pd.read_parquet(COMPANY_DB_PATH)
        active = df[df["total_bids"] >= 2].head(50).copy()
        scored = calculate_scores(active)
        for dim in SCORING_WEIGHTS:
            col = f"score_{dim}"
            assert col in scored.columns, f"Falta columna {col}"
            assert (scored[col] >= 0).all(), f"{col} tiene valores < 0"
            assert (scored[col] <= 100).all(), f"{col} tiene valores > 100"

    @skip_no_company_db
    def test_score_total_is_weighted_sum(self):
        """score_total debe ser la suma ponderada de las 9 dimensiones."""
        df = pd.read_parquet(COMPANY_DB_PATH)
        active = df[df["total_bids"] >= 2].head(100).copy()
        scored = calculate_scores(active)
        recomputed = sum(
            scored[f"score_{dim}"] * weight
            for dim, weight in SCORING_WEIGHTS.items()
        ).clip(0, 100).round(1)
        diff = (scored["score_total"] - recomputed).abs()
        assert (diff < 0.2).all(), f"Diferencia máxima: {diff.max()}"

    @skip_no_company_db
    def test_row_count_preserved(self):
        """calculate_scores no debe agregar ni eliminar filas."""
        df = pd.read_parquet(COMPANY_DB_PATH)
        active = df[df["total_bids"] >= 2].head(50).copy()
        n_before = len(active)
        scored = calculate_scores(active)
        assert len(scored) == n_before


# =====================================================================
# 2. Recompute score_total desde leads_ranked
# =====================================================================

class TestRecomputeScoreTotalConsistency:
    """Verificar que score_total en leads_ranked es recomputable."""

    @skip_no_leads_ranked
    def test_recompute_matches_original(self):
        """Recomputar score_total debe dar resultado cercano al original."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        recomputed = recompute_score_total(df)
        diff = (df["score_total"] - recomputed["score_total"]).abs()
        # Al menos 99% de filas dentro de tolerancia 0.5
        pct_ok = (diff < 0.5).mean()
        assert pct_ok >= 0.99, (
            f"Solo {pct_ok:.1%} de filas consistentes (se requiere ≥99%). "
            f"Diff máx: {diff.max():.2f}"
        )

    @skip_no_leads_ranked
    def test_recomputed_in_range(self):
        """score_total recomputado debe estar en [0, 100]."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        recomputed = recompute_score_total(df)
        assert (recomputed["score_total"] >= 0).all()
        assert (recomputed["score_total"] <= 100).all()

    @skip_no_leads_ranked
    def test_score_dims_from_ranked_in_range(self):
        """Cada score_{dim} en leads_ranked debe estar en [0, 100]."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        for dim in SCORING_WEIGHTS:
            col = f"score_{dim}"
            if col in df.columns:
                series = df[col].dropna()
                assert (series >= 0).all(), f"{col} tiene valores < 0"
                assert (series <= 100).all(), f"{col} tiene valores > 100"


# =====================================================================
# 3. Recompute score_combined desde leads_ml_ranked
# =====================================================================

class TestRecomputeScoreCombinedConsistency:
    """Verificar que score_combined es recomputable."""

    @skip_no_leads_ml_ranked
    def test_recompute_combined_matches(self):
        """Recomputar score_combined debe dar resultado cercano al original."""
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        recomputed = recompute_score_combined(df)
        diff = (df["score_combined"] - recomputed["score_combined"]).abs()
        pct_ok = (diff < 0.5).mean()
        assert pct_ok >= 0.99, (
            f"Solo {pct_ok:.1%} de filas consistentes. Diff máx: {diff.max():.2f}"
        )

    @skip_no_leads_ml_ranked
    def test_recomputed_combined_in_range(self):
        """score_combined recomputado debe estar en [0, 100]."""
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        recomputed = recompute_score_combined(df)
        assert (recomputed["score_combined"] >= 0).all()
        assert (recomputed["score_combined"] <= 100).all()


# =====================================================================
# 4. Dataset sizes: ranked > enriched (enriched es top N)
# =====================================================================

class TestDatasetSizeRelationships:
    """Verificar relaciones de tamaño entre datasets."""

    @skip_no_leads_ranked
    @skip_no_leads_enriched
    def test_ranked_has_more_rows_than_enriched(self):
        """leads_ranked debe tener más filas que leads_enriched (top N)."""
        ranked = pd.read_parquet(LEADS_RANKED_PATH)
        enriched = pd.read_parquet(LEADS_ENRICHED_PATH)
        assert len(ranked) >= len(enriched), (
            f"ranked ({len(ranked)}) < enriched ({len(enriched)})"
        )

    @skip_no_leads_ranked
    @skip_no_leads_ml_ranked
    def test_ranked_same_size_as_ml_ranked(self):
        """leads_ranked y leads_ml_ranked deben tener el mismo número de filas."""
        ranked = pd.read_parquet(LEADS_RANKED_PATH)
        ml_ranked = pd.read_parquet(LEADS_ML_RANKED_PATH)
        assert len(ranked) == len(ml_ranked), (
            f"ranked ({len(ranked)}) != ml_ranked ({len(ml_ranked)})"
        )

    @skip_no_company_db
    @skip_no_leads_ranked
    def test_ranked_subset_of_company_db(self):
        """Todos los RUTs en leads_ranked deben existir en company_database."""
        company = pd.read_parquet(COMPANY_DB_PATH)
        ranked = pd.read_parquet(LEADS_RANKED_PATH)
        missing = set(ranked["rut"]) - set(company["rut"])
        assert len(missing) == 0, f"{len(missing)} RUTs en ranked no están en company_db"

    @skip_no_leads_ml_ranked
    @skip_no_leads_enriched
    def test_enriched_subset_of_ml_ranked(self):
        """Todos los RUTs en enriched deben existir en ml_ranked."""
        ml_ranked = pd.read_parquet(LEADS_ML_RANKED_PATH)
        enriched = pd.read_parquet(LEADS_ENRICHED_PATH)
        missing = set(enriched["rut"]) - set(ml_ranked["rut"])
        assert len(missing) == 0, f"{len(missing)} RUTs en enriched no están en ml_ranked"


# =====================================================================
# 5. Pipeline export: CRM DataFrame sin columnas prohibidas
# =====================================================================

class TestCrmExportSafety:
    """Verificar que el export CRM no contiene datos internos."""

    @skip_no_leads_enriched
    def test_crm_no_forbidden_columns(self):
        """CRM DataFrame no debe tener columnas prohibidas."""
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        crm = build_crm_dataframe(df)
        forbidden_in_crm = set(crm.columns) & CLIENT_FORBIDDEN_COLUMNS
        assert not forbidden_in_crm, f"Columnas prohibidas en CRM: {forbidden_in_crm}"

    @skip_no_leads_enriched
    def test_crm_has_expected_columns(self):
        """CRM DataFrame debe tener las columnas esperadas."""
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        crm = build_crm_dataframe(df)
        expected = {"empresa", "rut", "contacto", "telefono", "email", "canal", "estado"}
        missing = expected - set(crm.columns)
        assert not missing, f"Faltan columnas en CRM: {missing}"

    @skip_no_leads_enriched
    def test_crm_passes_client_safe_check(self):
        """CRM DataFrame debe pasar validación client-safe."""
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        crm = build_crm_dataframe(df)
        # No debe lanzar excepción
        assert_client_safe_columns(crm)

    @skip_no_leads_ml_ranked
    def test_crm_from_ml_ranked_no_forbidden(self):
        """CRM desde ml_ranked tampoco debe tener columnas prohibidas."""
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        crm = build_crm_dataframe(df)
        forbidden_in_crm = set(crm.columns) & CLIENT_FORBIDDEN_COLUMNS
        assert not forbidden_in_crm, f"Columnas prohibidas en CRM: {forbidden_in_crm}"


# =====================================================================
# 6. Score flow completo: company_db → score_total → combined → rank
# =====================================================================

class TestFullScoreFlow:
    """Cadena completa de scoring sobre datos reales."""

    @skip_no_company_db
    def test_full_pipeline_chain(self):
        """Ejecutar cadena completa: scores → combined → cluster → rank."""
        df = pd.read_parquet(COMPANY_DB_PATH)
        active = df[df["total_bids"] >= 2].head(100).copy()

        # Step 1: calculate_scores
        scored = calculate_scores(active)
        assert "score_total" in scored.columns
        assert (scored["score_total"] >= 0).all()
        assert (scored["score_total"] <= 100).all()

        # Step 2: recompute_score_combined (sin ML signals → usa score_total)
        combined = recompute_score_combined(scored)
        assert "score_combined" in combined.columns
        assert (combined["score_combined"] >= 0).all()
        assert (combined["score_combined"] <= 100).all()

        # Step 3: assign_cluster_profile
        clustered = assign_cluster_profile(combined)
        assert "cluster_perfil" in clustered.columns
        valid_profiles = {"LEAD BAJO", "LEAD REGULAR", "LEAD BUENO", "LEAD IDEAL"}
        actual = set(clustered["cluster_perfil"].unique())
        assert actual.issubset(valid_profiles), f"Perfiles inesperados: {actual - valid_profiles}"

        # Step 4: assign_rank
        ranked = assign_rank(clustered, "score_combined", "rank_ml")
        assert ranked["rank_ml"].min() == 1
        assert ranked["rank_ml"].max() == len(ranked)
        # Mayor score → menor rank
        top = ranked.iloc[0]
        bottom = ranked.iloc[-1]
        assert top["score_combined"] >= bottom["score_combined"]

    @skip_no_company_db
    def test_combined_without_ml_equals_score_total(self):
        """Sin ML signals, score_combined debe ser igual a score_total."""
        df = pd.read_parquet(COMPANY_DB_PATH)
        active = df[df["total_bids"] >= 2].head(50).copy()
        scored = calculate_scores(active)
        combined = recompute_score_combined(scored)
        diff = (scored["score_total"] - combined["score_combined"]).abs()
        assert (diff < 0.2).all(), (
            f"Sin ML, combined debería ≈ score_total. Diff máx: {diff.max():.2f}"
        )


# =====================================================================
# 7. score_total recalculable desde score_{dim} columns
# =====================================================================

class TestScoreTotalFromDims:
    """Verificar consistencia de score_total con dims individuales."""

    @skip_no_leads_ranked
    def test_weighted_sum_matches_stored(self):
        """score_total almacenado debe coincidir con suma ponderada de dims."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        recomputed = sum(
            df[f"score_{dim}"] * weight
            for dim, weight in SCORING_WEIGHTS.items()
        ).clip(0, 100).round(1)
        diff = (df["score_total"] - recomputed).abs()
        pct_ok = (diff < 0.5).mean()
        assert pct_ok >= 0.99, f"Solo {pct_ok:.1%} consistentes"


# =====================================================================
# 8. assign_rank produce ranking correcto
# =====================================================================

class TestAssignRankOnRealData:
    """Verificar ranking sobre datos reales."""

    @skip_no_leads_ranked
    def test_rank_starts_at_1(self):
        """El ranking debe empezar en 1."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        assert df["rank"].min() == 1

    @skip_no_leads_ranked
    def test_rank_is_sequential(self):
        """El ranking debe ser secuencial sin huecos."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        expected = set(range(1, len(df) + 1))
        actual = set(df["rank"])
        assert actual == expected, f"Huecos en ranking: {expected - actual}"

    @skip_no_leads_ranked
    def test_higher_score_lower_rank(self):
        """Mayor score_total debe tener menor número de rank."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        sorted_df = df.sort_values("rank")
        # Verificar que scores están en orden descendente (con tolerancia para empates)
        scores = sorted_df["score_total"].values
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1] - 0.1, (
                f"Rank {i+1} (score={scores[i]}) < Rank {i+2} (score={scores[i+1]})"
            )

    @skip_no_leads_ml_ranked
    def test_rank_ml_starts_at_1(self):
        """rank_ml debe empezar en 1."""
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        assert df["rank_ml"].min() == 1

    @skip_no_leads_ml_ranked
    def test_rank_ml_is_sequential(self):
        """rank_ml debe ser secuencial sin huecos."""
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        expected = set(range(1, len(df) + 1))
        actual = set(df["rank_ml"])
        assert actual == expected


# =====================================================================
# 9. Pipeline contracts: cada parquet pasa su contrato
# =====================================================================

class TestPipelineContracts:
    """Verificar que cada parquet pasa su contrato de datos."""

    @skip_no_company_db
    def test_company_db_passes_contract(self):
        df = pd.read_parquet(COMPANY_DB_PATH)
        issues = validate_dataframe_contract(df, "company_database")
        assert not issues, f"company_database falló contrato: {issues}"

    @skip_no_leads_ranked
    def test_leads_ranked_passes_contract(self):
        df = pd.read_parquet(LEADS_RANKED_PATH)
        issues = validate_dataframe_contract(df, "leads_ranked")
        assert not issues, f"leads_ranked falló contrato: {issues}"

    @skip_no_leads_ml_ranked
    def test_leads_ml_ranked_passes_contract(self):
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        issues = validate_dataframe_contract(df, "leads_ml_ranked")
        assert not issues, f"leads_ml_ranked falló contrato: {issues}"

    @skip_no_leads_enriched
    def test_leads_enriched_passes_contract(self):
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        issues = validate_dataframe_contract(df, "leads_enriched")
        assert not issues, f"leads_enriched falló contrato: {issues}"

    @skip_no_loss_analysis
    def test_loss_analysis_passes_contract(self):
        df = pd.read_parquet(LOSS_ANALYSIS_PATH)
        issues = validate_dataframe_contract(df, "loss_analysis")
        assert not issues, f"loss_analysis falló contrato: {issues}"


# =====================================================================
# 10. Coverage report: contact_coverage_summary produce datos sensatos
# =====================================================================

class TestCoverageReport:
    """Verificar que el reporte de cobertura es sensato."""

    @skip_no_leads_enriched
    def test_coverage_summary_keys(self):
        """contact_coverage_summary debe tener todas las keys esperadas."""
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        summary = contact_coverage_summary(df)
        expected_keys = {
            "total_leads", "con_telefono", "con_email", "con_web",
            "con_rival", "pdf_listo", "outreach_listo",
        }
        assert expected_keys.issubset(set(summary.keys()))

    @skip_no_leads_enriched
    def test_coverage_total_matches_rows(self):
        """total_leads debe coincidir con el número de filas."""
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        summary = contact_coverage_summary(df)
        assert summary["total_leads"] == len(df)

    @skip_no_leads_enriched
    def test_coverage_counts_non_negative(self):
        """Todos los conteos deben ser no negativos."""
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        summary = contact_coverage_summary(df)
        for key, value in summary.items():
            assert value >= 0, f"{key} es negativo: {value}"

    @skip_no_leads_enriched
    def test_coverage_counts_not_exceed_total(self):
        """Ningún conteo debe exceder total_leads."""
        df = pd.read_parquet(LEADS_ENRICHED_PATH)
        summary = contact_coverage_summary(df)
        total = summary["total_leads"]
        for key, value in summary.items():
            if key != "total_leads":
                assert value <= total, f"{key} ({value}) > total ({total})"

    @skip_no_leads_ranked
    def test_coverage_on_ranked_no_crash(self):
        """contact_coverage_summary no debe crashear con leads_ranked (sin contactos)."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        summary = contact_coverage_summary(df)
        assert summary["total_leads"] == len(df)
        # Sin columnas de contacto, los conteos deben ser 0
        assert summary["con_telefono"] >= 0


# =====================================================================
# 11. Resolve columns: score y rank columns
# =====================================================================

class TestResolveColumnsOnRealData:
    """Verificar resolve_score_column y resolve_rank_column."""

    @skip_no_leads_ml_ranked
    def test_resolve_score_on_ml_ranked(self):
        """ml_ranked tiene score_combined → debe resolverse."""
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        col = resolve_score_column(df)
        assert col == "score_combined"

    @skip_no_leads_ranked
    def test_resolve_score_on_ranked(self):
        """ranked tiene score_total → debe resolverse."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        col = resolve_score_column(df)
        assert col in ("score_combined", "score_total")

    @skip_no_leads_ml_ranked
    def test_resolve_rank_on_ml_ranked(self):
        """ml_ranked tiene rank_ml → debe resolverse."""
        df = pd.read_parquet(LEADS_ML_RANKED_PATH)
        col = resolve_rank_column(df)
        assert col == "rank_ml"

    @skip_no_leads_ranked
    def test_resolve_rank_on_ranked(self):
        """ranked tiene rank → debe resolverse."""
        df = pd.read_parquet(LEADS_RANKED_PATH)
        col = resolve_rank_column(df)
        assert col in ("rank_ml", "rank")
