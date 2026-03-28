"""
Tests de contratos de datos sobre parquets REALES.

Cada test usa fixtures de conftest.py que saltan si el archivo no existe.
Si un test falla, el bug está en el CÓDIGO del pipeline, NO en el test.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config import SCORING_WEIGHTS, FILTERED_DIR, OUTPUT_DIR
from pipeline_core import COMBINED_SCORE_WEIGHTS
from pipeline_validation import PIPELINE_CONTRACTS, validate_dataframe_contract

# ── Paths y skip markers (replicados de conftest para evitar import directo) ──
_COMPANY_DB_PATH = FILTERED_DIR / "company_database.parquet"
_LEADS_RANKED_PATH = FILTERED_DIR / "leads_ranked.parquet"
_LEADS_ML_RANKED_PATH = FILTERED_DIR / "leads_ml_ranked.parquet"
_LEADS_ENRICHED_PATH = FILTERED_DIR / "leads_enriched.parquet"
_LOSS_ANALYSIS_PATH = OUTPUT_DIR / "loss_analysis.parquet"

skip_no_company_db = pytest.mark.skipif(not _COMPANY_DB_PATH.exists(), reason="company_database.parquet no disponible")
skip_no_leads_ranked = pytest.mark.skipif(not _LEADS_RANKED_PATH.exists(), reason="leads_ranked.parquet no disponible")
skip_no_leads_ml_ranked = pytest.mark.skipif(not _LEADS_ML_RANKED_PATH.exists(), reason="leads_ml_ranked.parquet no disponible")
skip_no_leads_enriched = pytest.mark.skipif(not _LEADS_ENRICHED_PATH.exists(), reason="leads_enriched.parquet no disponible")
skip_no_loss_analysis = pytest.mark.skipif(not _LOSS_ANALYSIS_PATH.exists(), reason="loss_analysis.parquet no disponible")


# ════════════════════════════════════════════════════════════════════════
#  company_database.parquet
# ════════════════════════════════════════════════════════════════════════

class TestCompanyDatabase:
    """Verificaciones sobre company_database.parquet real."""

    @skip_no_company_db
    def test_has_required_columns(self, real_company_db):
        required = PIPELINE_CONTRACTS["company_database"]["required"]
        missing = [c for c in required if c not in real_company_db.columns]
        assert not missing, f"Faltan columnas requeridas: {missing}"

    @skip_no_company_db
    def test_ruts_are_unique(self, real_company_db):
        dupes = real_company_db.duplicated(subset=["rut"]).sum()
        assert dupes == 0, f"Hay {dupes} RUTs duplicados"

    @skip_no_company_db
    def test_no_null_ruts(self, real_company_db):
        null_ruts = real_company_db["rut"].isna().sum()
        assert null_ruts == 0, f"Hay {null_ruts} RUTs nulos"

    @skip_no_company_db
    def test_win_rate_in_range(self, real_company_db):
        wr = real_company_db["win_rate"].dropna()
        assert (wr >= 0).all(), "win_rate contiene valores negativos"
        assert (wr <= 1).all(), "win_rate contiene valores mayores a 1"

    @skip_no_company_db
    def test_total_bids_non_negative(self, real_company_db):
        assert (real_company_db["total_bids"] >= 0).all(), "total_bids tiene valores negativos"

    @skip_no_company_db
    def test_total_wins_non_negative(self, real_company_db):
        assert (real_company_db["total_wins"] >= 0).all(), "total_wins tiene valores negativos"

    @skip_no_company_db
    def test_total_wins_leq_total_bids(self, real_company_db):
        df = real_company_db
        violations = df[df["total_wins"] > df["total_bids"]]
        assert len(violations) == 0, (
            f"{len(violations)} filas tienen total_wins > total_bids. "
            f"Primeras 5: {violations[['rut', 'total_wins', 'total_bids']].head().to_dict('records')}"
        )

    @skip_no_company_db
    def test_monto_promedio_non_negative(self, real_company_db):
        mp = real_company_db["monto_promedio"].dropna()
        assert (mp >= 0).all(), "monto_promedio tiene valores negativos"

    @skip_no_company_db
    def test_dias_desde_ultima_non_negative(self, real_company_db):
        dias = real_company_db["dias_desde_ultima"]
        assert (dias >= 0).all(), "dias_desde_ultima tiene valores negativos"

    @skip_no_company_db
    def test_n_licitaciones_non_negative(self, real_company_db):
        for col in ["n_LP", "n_LE", "n_L1"]:
            assert (real_company_db[col] >= 0).all(), f"{col} tiene valores negativos"

    @skip_no_company_db
    def test_passes_pipeline_contract(self, real_company_db):
        issues = validate_dataframe_contract(real_company_db, "company_database")
        assert not issues, f"Contrato violado: {issues}"

    @skip_no_company_db
    def test_has_meaningful_row_count(self, real_company_db):
        assert len(real_company_db) > 100, (
            f"company_database tiene solo {len(real_company_db)} filas — esperado >100"
        )


# ════════════════════════════════════════════════════════════════════════
#  leads_ranked.parquet
# ════════════════════════════════════════════════════════════════════════

class TestLeadsRanked:
    """Verificaciones sobre leads_ranked.parquet real."""

    @skip_no_leads_ranked
    def test_has_required_columns(self, real_leads_ranked):
        required = PIPELINE_CONTRACTS["leads_ranked"]["required"]
        missing = [c for c in required if c not in real_leads_ranked.columns]
        assert not missing, f"Faltan columnas requeridas: {missing}"

    @skip_no_leads_ranked
    def test_ruts_are_unique(self, real_leads_ranked):
        dupes = real_leads_ranked.duplicated(subset=["rut"]).sum()
        assert dupes == 0, f"Hay {dupes} RUTs duplicados"

    @skip_no_leads_ranked
    def test_score_total_in_range(self, real_leads_ranked):
        st = real_leads_ranked["score_total"]
        assert (st >= 0).all(), "score_total contiene valores negativos"
        assert (st <= 100).all(), "score_total contiene valores mayores a 100"

    @skip_no_leads_ranked
    def test_rank_starts_at_one(self, real_leads_ranked):
        assert real_leads_ranked["rank"].min() == 1, "rank no empieza en 1"

    @skip_no_leads_ranked
    def test_rank_sequential_no_gaps(self, real_leads_ranked):
        ranks = sorted(real_leads_ranked["rank"].tolist())
        expected = list(range(1, len(real_leads_ranked) + 1))
        assert ranks == expected, "rank tiene huecos o valores no secuenciales"

    @skip_no_leads_ranked
    def test_has_all_nine_score_dimensions(self, real_leads_ranked):
        for dim in SCORING_WEIGHTS:
            col = f"score_{dim}"
            assert col in real_leads_ranked.columns, f"Falta columna {col}"

    @skip_no_leads_ranked
    def test_score_dimensions_in_range(self, real_leads_ranked):
        for dim in SCORING_WEIGHTS:
            col = f"score_{dim}"
            s = pd.to_numeric(real_leads_ranked[col], errors="coerce").dropna()
            assert (s >= 0).all(), f"{col} tiene valores negativos"
            assert (s <= 100).all(), f"{col} tiene valores mayores a 100"

    @skip_no_leads_ranked
    def test_win_rate_in_range(self, real_leads_ranked):
        if "win_rate" in real_leads_ranked.columns:
            wr = real_leads_ranked["win_rate"].dropna()
            assert (wr >= 0).all(), "win_rate negativo en leads_ranked"
            assert (wr <= 1).all(), "win_rate > 1 en leads_ranked"

    @skip_no_leads_ranked
    def test_passes_pipeline_contract(self, real_leads_ranked):
        issues = validate_dataframe_contract(real_leads_ranked, "leads_ranked")
        assert not issues, f"Contrato violado: {issues}"

    @skip_no_leads_ranked
    def test_score_total_recomputable(self, real_leads_ranked):
        """Verifica que score_total ≈ Σ(score_dim × peso) con tolerancia 0.5."""
        df = real_leads_ranked
        recomputed = sum(
            pd.to_numeric(df[f"score_{dim}"], errors="coerce").fillna(0) * weight
            for dim, weight in SCORING_WEIGHTS.items()
        ).clip(0, 100).round(1)

        diff = (df["score_total"] - recomputed).abs()
        bad = diff[diff > 0.5]
        assert len(bad) == 0, (
            f"{len(bad)} filas tienen score_total inconsistente (diff > 0.5). "
            f"Max diff: {diff.max():.2f}"
        )


# ════════════════════════════════════════════════════════════════════════
#  leads_ml_ranked.parquet
# ════════════════════════════════════════════════════════════════════════

class TestLeadsMlRanked:
    """Verificaciones sobre leads_ml_ranked.parquet real."""

    @skip_no_leads_ml_ranked
    def test_has_required_columns(self, real_leads_ml_ranked):
        required = PIPELINE_CONTRACTS["leads_ml_ranked"]["required"]
        missing = [c for c in required if c not in real_leads_ml_ranked.columns]
        assert not missing, f"Faltan columnas requeridas: {missing}"

    @skip_no_leads_ml_ranked
    def test_ruts_are_unique(self, real_leads_ml_ranked):
        dupes = real_leads_ml_ranked.duplicated(subset=["rut"]).sum()
        assert dupes == 0, f"Hay {dupes} RUTs duplicados"

    @skip_no_leads_ml_ranked
    def test_score_combined_in_range(self, real_leads_ml_ranked):
        sc = real_leads_ml_ranked["score_combined"]
        assert (sc >= 0).all(), "score_combined negativo"
        assert (sc <= 100).all(), "score_combined > 100"

    @skip_no_leads_ml_ranked
    def test_score_total_in_range(self, real_leads_ml_ranked):
        st = real_leads_ml_ranked["score_total"]
        assert (st >= 0).all(), "score_total negativo"
        assert (st <= 100).all(), "score_total > 100"

    @skip_no_leads_ml_ranked
    def test_rank_ml_starts_at_one(self, real_leads_ml_ranked):
        assert real_leads_ml_ranked["rank_ml"].min() == 1, "rank_ml no empieza en 1"

    @skip_no_leads_ml_ranked
    def test_rank_ml_sequential(self, real_leads_ml_ranked):
        ranks = sorted(real_leads_ml_ranked["rank_ml"].tolist())
        expected = list(range(1, len(real_leads_ml_ranked) + 1))
        assert ranks == expected, "rank_ml tiene huecos o no es secuencial"

    @skip_no_leads_ml_ranked
    def test_xgb_score_in_range(self, real_leads_ml_ranked):
        if "xgb_score" in real_leads_ml_ranked.columns:
            xs = pd.to_numeric(real_leads_ml_ranked["xgb_score"], errors="coerce").dropna()
            assert (xs >= 0).all(), "xgb_score negativo"
            assert (xs <= 100).all(), "xgb_score > 100"

    @skip_no_leads_ml_ranked
    def test_km_score_in_range(self, real_leads_ml_ranked):
        if "km_score" in real_leads_ml_ranked.columns:
            ks = pd.to_numeric(real_leads_ml_ranked["km_score"], errors="coerce").dropna()
            assert (ks >= 0).all(), "km_score negativo"
            assert (ks <= 100).all(), "km_score > 100"

    @skip_no_leads_ml_ranked
    def test_passes_pipeline_contract(self, real_leads_ml_ranked):
        issues = validate_dataframe_contract(real_leads_ml_ranked, "leads_ml_ranked")
        assert not issues, f"Contrato violado: {issues}"

    @skip_no_leads_ml_ranked
    def test_score_combined_recomputable(self, real_leads_ml_ranked):
        """Verifica que score_combined es consistente con los pesos definidos."""
        df = real_leads_ml_ranked
        score_total = pd.to_numeric(df["score_total"], errors="coerce").fillna(0)
        total = score_total * COMBINED_SCORE_WEIGHTS["score_total"]

        for col in ("km_score", "xgb_score"):
            if col in df.columns:
                signal = pd.to_numeric(df[col], errors="coerce").fillna(score_total)
            else:
                signal = score_total
            total = total + signal * COMBINED_SCORE_WEIGHTS[col]

        recomputed = total.clip(0, 100).round(1)
        diff = (df["score_combined"] - recomputed).abs()
        bad = diff[diff > 0.5]
        assert len(bad) == 0, (
            f"{len(bad)} filas tienen score_combined inconsistente (diff > 0.5). "
            f"Max diff: {diff.max():.2f}"
        )

    @skip_no_leads_ml_ranked
    def test_has_cluster_perfil(self, real_leads_ml_ranked):
        assert "cluster_perfil" in real_leads_ml_ranked.columns, "Falta cluster_perfil"
        valid_profiles = {"LEAD BAJO", "LEAD REGULAR", "LEAD BUENO", "LEAD IDEAL"}
        actual = set(real_leads_ml_ranked["cluster_perfil"].dropna().unique())
        unexpected = actual - valid_profiles
        assert not unexpected, f"Perfiles inesperados: {unexpected}"


# ════════════════════════════════════════════════════════════════════════
#  leads_enriched.parquet
# ════════════════════════════════════════════════════════════════════════

class TestLeadsEnriched:
    """Verificaciones sobre leads_enriched.parquet real."""

    @skip_no_leads_enriched
    def test_has_required_columns(self, real_leads_enriched):
        required = PIPELINE_CONTRACTS["leads_enriched"]["required"]
        missing = [c for c in required if c not in real_leads_enriched.columns]
        assert not missing, f"Faltan columnas requeridas: {missing}"

    @skip_no_leads_enriched
    def test_ruts_are_unique(self, real_leads_enriched):
        dupes = real_leads_enriched.duplicated(subset=["rut"]).sum()
        assert dupes == 0, f"Hay {dupes} RUTs duplicados"

    @skip_no_leads_enriched
    def test_score_digital_in_range(self, real_leads_enriched):
        if "score_digital" in real_leads_enriched.columns:
            sd = pd.to_numeric(real_leads_enriched["score_digital"], errors="coerce").dropna()
            assert (sd >= 0).all(), "score_digital negativo"
            assert (sd <= 100).all(), "score_digital > 100"

    @skip_no_leads_enriched
    def test_has_contact_columns(self, real_leads_enriched):
        for col in ["telefono", "email", "web"]:
            assert col in real_leads_enriched.columns, f"Falta columna de contacto: {col}"

    @skip_no_leads_enriched
    def test_score_total_in_range(self, real_leads_enriched):
        st = real_leads_enriched["score_total"]
        assert (st >= 0).all(), "score_total negativo"
        assert (st <= 100).all(), "score_total > 100"

    @skip_no_leads_enriched
    def test_score_combined_in_range(self, real_leads_enriched):
        sc = real_leads_enriched["score_combined"]
        assert (sc >= 0).all(), "score_combined negativo"
        assert (sc <= 100).all(), "score_combined > 100"

    @skip_no_leads_enriched
    def test_passes_pipeline_contract(self, real_leads_enriched):
        issues = validate_dataframe_contract(real_leads_enriched, "leads_enriched")
        assert not issues, f"Contrato violado: {issues}"

    @skip_no_leads_enriched
    def test_is_top_n_subset(self, real_leads_enriched):
        """leads_enriched debería ser un subconjunto (top N) de leads_ml_ranked."""
        if not _LEADS_ML_RANKED_PATH.exists():
            pytest.skip("leads_ml_ranked.parquet no disponible para comparar")
        ml = pd.read_parquet(_LEADS_ML_RANKED_PATH)
        assert len(real_leads_enriched) <= len(ml), (
            f"enriched ({len(real_leads_enriched)}) tiene más filas que ml_ranked ({len(ml)})"
        )

    @skip_no_leads_enriched
    def test_some_contacts_exist(self, real_leads_enriched):
        """Al menos algunos leads enriquecidos deben tener datos de contacto."""
        has_phone = real_leads_enriched["telefono"].notna().sum()
        has_email = real_leads_enriched["email"].notna().sum()
        has_web = real_leads_enriched["web"].notna().sum()
        total_contacts = has_phone + has_email + has_web
        assert total_contacts > 0, "Ningún lead enriquecido tiene datos de contacto"


# ════════════════════════════════════════════════════════════════════════
#  loss_analysis.parquet
# ════════════════════════════════════════════════════════════════════════

class TestLossAnalysis:
    """Verificaciones sobre loss_analysis.parquet real."""

    @skip_no_loss_analysis
    def test_has_required_columns(self, real_loss_analysis):
        required = PIPELINE_CONTRACTS["loss_analysis"]["required"]
        missing = [c for c in required if c not in real_loss_analysis.columns]
        assert not missing, f"Faltan columnas requeridas: {missing}"

    @skip_no_loss_analysis
    def test_ruts_are_unique(self, real_loss_analysis):
        dupes = real_loss_analysis.duplicated(subset=["rut"]).sum()
        assert dupes == 0, f"Hay {dupes} RUTs duplicados"

    @skip_no_loss_analysis
    def test_loss_rate_in_range(self, real_loss_analysis):
        lr = real_loss_analysis["loss_rate"].dropna()
        assert (lr >= 0).all(), "loss_rate negativo"
        assert (lr <= 1).all(), "loss_rate > 1"

    @skip_no_loss_analysis
    def test_total_participated_non_negative(self, real_loss_analysis):
        tp = real_loss_analysis["total_participated"]
        assert (tp >= 0).all(), "total_participated negativo"

    @skip_no_loss_analysis
    def test_total_won_non_negative(self, real_loss_analysis):
        tw = real_loss_analysis["total_won"]
        assert (tw >= 0).all(), "total_won negativo"

    @skip_no_loss_analysis
    def test_total_won_leq_participated(self, real_loss_analysis):
        df = real_loss_analysis
        violations = df[df["total_won"] > df["total_participated"]]
        assert len(violations) == 0, (
            f"{len(violations)} filas tienen total_won > total_participated"
        )

    @skip_no_loss_analysis
    def test_total_lost_non_negative(self, real_loss_analysis):
        """total_lost_loss es la columna de pérdidas en loss_analysis."""
        if "total_lost_loss" in real_loss_analysis.columns:
            tl = real_loss_analysis["total_lost_loss"]
            assert (tl >= 0).all(), "total_lost_loss negativo"

    @skip_no_loss_analysis
    def test_passes_pipeline_contract(self, real_loss_analysis):
        issues = validate_dataframe_contract(real_loss_analysis, "loss_analysis")
        assert not issues, f"Contrato violado: {issues}"

    @skip_no_loss_analysis
    def test_loss_rate_consistency(self, real_loss_analysis):
        """loss_rate debería ser cercano a total_lost_loss / total_participated."""
        df = real_loss_analysis
        if "total_lost_loss" not in df.columns:
            pytest.skip("total_lost_loss no disponible")
        mask = df["total_participated"] > 0
        subset = df[mask]
        if len(subset) == 0:
            pytest.skip("No hay filas con total_participated > 0")
        expected_lr = subset["total_lost_loss"] / subset["total_participated"]
        diff = (subset["loss_rate"] - expected_lr).abs()
        bad = diff[diff > 0.05]
        assert len(bad) == 0, (
            f"{len(bad)} filas tienen loss_rate inconsistente con total_lost_loss/total_participated. "
            f"Max diff: {diff.max():.3f}"
        )


# ════════════════════════════════════════════════════════════════════════
#  Cross-dataset consistency
# ════════════════════════════════════════════════════════════════════════

class TestCrossDatasetConsistency:
    """Verificaciones de consistencia entre datasets."""

    @skip_no_leads_ranked
    @skip_no_company_db
    def test_ranked_is_subset_of_company_db(self, real_leads_ranked, real_company_db):
        """Todos los RUTs en leads_ranked deben existir en company_database."""
        ranked_ruts = set(real_leads_ranked["rut"])
        company_ruts = set(real_company_db["rut"])
        missing = ranked_ruts - company_ruts
        assert not missing, (
            f"{len(missing)} RUTs en leads_ranked no están en company_database"
        )

    @skip_no_leads_ranked
    @skip_no_company_db
    def test_ranked_smaller_than_company_db(self, real_leads_ranked, real_company_db):
        """leads_ranked debería tener menos filas que company_database (filtro personas naturales)."""
        assert len(real_leads_ranked) <= len(real_company_db), (
            f"leads_ranked ({len(real_leads_ranked)}) > company_database ({len(real_company_db)})"
        )

    @skip_no_leads_ml_ranked
    @skip_no_leads_ranked
    def test_ml_ranked_same_size_as_ranked(self, real_leads_ml_ranked, real_leads_ranked):
        """leads_ml_ranked debería tener el mismo número de filas que leads_ranked."""
        assert len(real_leads_ml_ranked) == len(real_leads_ranked), (
            f"ml_ranked ({len(real_leads_ml_ranked)}) != ranked ({len(real_leads_ranked)})"
        )

    @skip_no_leads_enriched
    @skip_no_leads_ml_ranked
    def test_enriched_ruts_in_ml_ranked(self, real_leads_enriched, real_leads_ml_ranked):
        """Todos los RUTs enriquecidos deben estar en ml_ranked."""
        enriched_ruts = set(real_leads_enriched["rut"])
        ml_ruts = set(real_leads_ml_ranked["rut"])
        missing = enriched_ruts - ml_ruts
        assert not missing, (
            f"{len(missing)} RUTs enriquecidos no están en ml_ranked"
        )

    @skip_no_leads_ranked
    def test_score_total_matches_recomputed_from_dims(self, real_leads_ranked):
        """Recomputa score_total desde las 9 dimensiones y compara (tolerancia 0.5)."""
        df = real_leads_ranked
        recomputed = sum(
            pd.to_numeric(df[f"score_{dim}"], errors="coerce").fillna(0) * weight
            for dim, weight in SCORING_WEIGHTS.items()
        ).clip(0, 100).round(1)

        diff = (df["score_total"] - recomputed).abs()
        pct_ok = (diff <= 0.5).mean() * 100
        assert pct_ok >= 99.0, (
            f"Solo {pct_ok:.1f}% de filas tienen score_total consistente (esperado >=99%)"
        )

    @skip_no_leads_ml_ranked
    def test_score_combined_matches_recomputed(self, real_leads_ml_ranked):
        """Recomputa score_combined y compara (tolerancia 0.5)."""
        df = real_leads_ml_ranked
        score_total = pd.to_numeric(df["score_total"], errors="coerce").fillna(0)
        total = score_total * COMBINED_SCORE_WEIGHTS["score_total"]

        for col in ("km_score", "xgb_score"):
            if col in df.columns:
                signal = pd.to_numeric(df[col], errors="coerce").fillna(score_total)
            else:
                signal = score_total
            total = total + signal * COMBINED_SCORE_WEIGHTS[col]

        recomputed = total.clip(0, 100).round(1)
        diff = (df["score_combined"] - recomputed).abs()
        pct_ok = (diff <= 0.5).mean() * 100
        assert pct_ok >= 99.0, (
            f"Solo {pct_ok:.1f}% de filas tienen score_combined consistente (esperado >=99%)"
        )
