"""
Tests exhaustivos para funciones de scoring en 05_score_leads.py.

Cubre: score_in_range (con/sin optimal), 10 scoring functions individuales,
calculate_scores integración, bounds [0,100], y consistencia con SCORING_WEIGHTS.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from importlib import import_module

# ── Imports del pipeline ────────────────────────────────────────────
score_mod = import_module("05_score_leads")

score_in_range = score_mod.score_in_range
score_actividad = score_mod.score_actividad
score_tamano = score_mod.score_tamano
score_win_rate = score_mod.score_win_rate
score_recencia = score_mod.score_recencia
score_valor = score_mod.score_valor
score_competencia = score_mod.score_competencia
score_oportunidad = score_mod.score_oportunidad
score_especializacion = score_mod.score_especializacion
score_region = score_mod.score_region
score_digital = score_mod.score_digital
calculate_scores = score_mod.calculate_scores

from config import SCORING_WEIGHTS, IDEAL_RANGES, REGIONES_TOP, RECENCIA_MAX_DAYS


# ── Helpers ─────────────────────────────────────────────────────────

def _row(**kw) -> pd.Series:
    """pd.Series con defaults razonables para tests de scoring."""
    d = dict(
        total_bids=10, total_wins=3, win_rate=0.30,
        monto_promedio=150_000_000.0, monto_adjudicado=500_000_000.0,
        dias_desde_ultima=100, n_LP=4, n_LE=3, n_L1=2,
        competidores_promedio=7.0, total_lost=5, n_distinct_rivals=3,
        region="Región Metropolitana de Santiago",
        tipo_mop=None, categoria_mop="",
    )
    d.update(kw)
    return pd.Series(d)


def _drow(**kw) -> pd.Series:
    """pd.Series con campos digitales para score_digital."""
    d = dict(
        web=np.nan, gm_web=np.nan,
        email=np.nan, ocds_email=np.nan,
        telefono=np.nan, gm_telefono=np.nan,
    )
    d.update(kw)
    return pd.Series(d)


def _make_df(n: int = 5) -> pd.DataFrame:
    """DataFrame mínimo para calculate_scores."""
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "rut": [f"7654321{i}-K" for i in range(n)],
        "total_bids": rng.randint(3, 25, n),
        "total_wins": rng.randint(0, 10, n),
        "win_rate": rng.uniform(0.05, 0.5, n).round(3),
        "monto_promedio": rng.uniform(10e6, 500e6, n),
        "monto_adjudicado": rng.uniform(100e6, 2e9, n),
        "dias_desde_ultima": rng.randint(30, 800, n),
        "n_LP": rng.randint(0, 10, n),
        "n_LE": rng.randint(0, 8, n),
        "n_L1": rng.randint(0, 6, n),
        "competidores_promedio": rng.uniform(2, 15, n).round(1),
        "total_lost": rng.randint(0, 12, n),
        "n_distinct_rivals": rng.randint(0, 8, n),
        "region": ["Región Metropolitana de Santiago"] * n,
        "tipo_mop": [None] * n,
        "categoria_mop": [""] * n,
    })


# ═══════════════════════════════════════════════════════════════════
# A) score_in_range — SIN optimal
# ═══════════════════════════════════════════════════════════════════

class TestScoreInRangeNoOptimal:
    """Flat 100 dentro del rango, gradientes fuera."""

    def test_inside_range(self):
        assert score_in_range(10, 5, 15) == 100

    def test_exact_min(self):
        assert score_in_range(5, 5, 15) == 100

    def test_exact_max(self):
        assert score_in_range(15, 5, 15) == 100

    def test_below_gradient(self):
        # 100*(3-0)/(5-0) = 60
        assert score_in_range(3, 5, 15, lower_bound=0) == pytest.approx(60, abs=0.1)

    def test_above_gradient(self):
        # 100*(1-(20-15)/(25-15)) = 50
        assert score_in_range(20, 5, 15, upper_bound=25) == pytest.approx(50, abs=0.1)

    def test_at_lower_bound_zero(self):
        assert score_in_range(0, 5, 15, lower_bound=0) == pytest.approx(0, abs=0.1)

    def test_at_upper_bound_zero(self):
        assert score_in_range(25, 5, 15, upper_bound=25) == pytest.approx(0, abs=0.1)

    def test_nan_returns_zero(self):
        assert score_in_range(np.nan, 5, 15) == 0

    def test_none_returns_zero(self):
        assert score_in_range(None, 5, 15) == 0

    def test_lower_bound_none(self):
        # 100*value/ideal_min = 100*2/5 = 40
        assert score_in_range(2, 5, 15, lower_bound=None) == pytest.approx(40, abs=0.1)

    def test_upper_bound_none(self):
        # 100*ideal_max/value = 100*15/30 = 50
        assert score_in_range(30, 5, 15, upper_bound=None) == pytest.approx(50, abs=0.1)

    def test_negative_below_clipped(self):
        assert score_in_range(-5, 5, 15, lower_bound=0) == 0

    def test_far_above_clipped(self):
        assert score_in_range(100, 5, 15, upper_bound=25) == 0

    def test_zero_width_range(self):
        assert score_in_range(5, 5, 5) == 100


# ═══════════════════════════════════════════════════════════════════
# A) score_in_range — CON optimal
# ═══════════════════════════════════════════════════════════════════

class TestScoreInRangeWithOptimal:
    """Gradiente 85-100, pico en optimal."""

    def test_at_optimal_100(self):
        assert score_in_range(10, 5, 15, 0, 50, optimal=10) == pytest.approx(100, abs=0.1)

    def test_min_edge_85(self):
        # optimal=10, max_dist=5, edge(5)=85+15*(1-5/5)=85
        assert score_in_range(5, 5, 15, 0, 50, optimal=10) == pytest.approx(85, abs=0.1)

    def test_max_edge_85(self):
        assert score_in_range(15, 5, 15, 0, 50, optimal=10) == pytest.approx(85, abs=0.1)

    def test_midway_gradient(self):
        # 85+15*(1-2.5/5)=92.5
        assert score_in_range(7.5, 5, 15, 0, 50, optimal=10) == pytest.approx(92.5, abs=0.1)

    def test_below_range_decays(self):
        # es=edge(5)=85, 85*(3-0)/(5-0)=51
        assert score_in_range(3, 5, 15, 0, 50, optimal=10) == pytest.approx(51, abs=0.1)

    def test_above_range_decays(self):
        # es=edge(15)=85, 85*(1-10/35)≈60.71
        result = score_in_range(25, 5, 15, 0, 50, optimal=10)
        assert result == pytest.approx(60.71, abs=0.5)

    def test_optimal_clipped_below_to_min(self):
        # optimal=0 → clipped to 5, max_dist=max(0,10)=10
        # edge(10) = 85+15*(1-5/10)=92.5
        assert score_in_range(10, 5, 15, 0, 50, optimal=0) == pytest.approx(92.5, abs=0.1)

    def test_optimal_clipped_above_to_max(self):
        # optimal=20 → clipped to 15, max_dist=10, at 15: 100
        assert score_in_range(15, 5, 15, 0, 50, optimal=20) == pytest.approx(100, abs=0.1)

    def test_div_zero_same_range(self):
        result = score_in_range(5, 5, 5, 0, 10, optimal=5)
        assert 0 <= result <= 100

    def test_nan_returns_zero(self):
        assert score_in_range(np.nan, 5, 15, 0, 50, optimal=10) == 0

    def test_asymmetric_optimal_near_max(self):
        # optimal=15, max_dist=max(10,0)=10
        # at value=5 (min): 85+15*(1-10/10)=85
        # at value=15 (optimal): 100
        assert score_in_range(15, 5, 15, 0, 50, optimal=15) == pytest.approx(100, abs=0.1)
        assert score_in_range(5, 5, 15, 0, 50, optimal=15) == pytest.approx(85, abs=0.1)

    @pytest.mark.parametrize("v", [-100, -1, 0, 0.001, 50, 1000])
    def test_always_non_negative(self, v):
        assert score_in_range(v, 5, 15, 0, 50, optimal=10) >= 0

    @pytest.mark.parametrize("v", list(range(0, 55, 5)))
    def test_never_exceeds_100(self, v):
        assert score_in_range(v, 5, 15, 0, 50, optimal=10) <= 100


# ═══════════════════════════════════════════════════════════════════
# B) Funciones de scoring individuales
# ═══════════════════════════════════════════════════════════════════

class TestScoreActividad:
    def test_zero_bids_near_zero(self):
        assert score_actividad(_row(total_bids=0)) == pytest.approx(0, abs=0.5)

    def test_1_bid_low(self):
        r = score_actividad(_row(total_bids=1))
        assert 0 < r < 85

    def test_5_bids_lower_ideal(self):
        assert score_actividad(_row(total_bids=5)) >= 85

    def test_10_bids_mid_range(self):
        r = score_actividad(_row(total_bids=10))
        assert 85 <= r <= 100

    def test_15_bids_optimal(self):
        assert score_actividad(_row(total_bids=15)) == pytest.approx(100, abs=0.5)

    def test_25_bids_above(self):
        r = score_actividad(_row(total_bids=25))
        assert 0 < r < 100

    def test_50_bids_at_upper_bound(self):
        assert score_actividad(_row(total_bids=50)) == pytest.approx(0, abs=0.5)

    def test_nan_zero(self):
        assert score_actividad(_row(total_bids=np.nan)) == 0


class TestScoreTamano:
    def test_mop_mayor_2da(self):
        assert score_tamano(_row(tipo_mop="Mayor", categoria_mop="2da categoría")) == 100

    def test_mop_mayor_segunda(self):
        assert score_tamano(_row(tipo_mop="Mayor", categoria_mop="segunda")) == 100

    def test_mop_mayor_3ra(self):
        assert score_tamano(_row(tipo_mop="Mayor", categoria_mop="3ra categoría")) == 80

    def test_mop_mayor_tercera(self):
        assert score_tamano(_row(tipo_mop="Mayor", categoria_mop="tercera")) == 80

    def test_mop_mayor_1ra(self):
        assert score_tamano(_row(tipo_mop="Mayor", categoria_mop="1ra categoría")) == 60

    def test_mop_mayor_primera(self):
        assert score_tamano(_row(tipo_mop="Mayor", categoria_mop="primera")) == 60

    def test_mop_mayor_unknown_cat(self):
        assert score_tamano(_row(tipo_mop="Mayor", categoria_mop="especial")) == 70

    def test_mop_menor(self):
        assert score_tamano(_row(tipo_mop="Menor", categoria_mop="1ra")) == 50

    def test_no_mop_monto_in_range(self):
        r = score_tamano(_row(tipo_mop=None, monto_promedio=150_000_000))
        assert 85 <= r <= 100

    def test_no_mop_monto_optimal(self):
        r = score_tamano(_row(tipo_mop=None, monto_promedio=500_000_000))
        assert r == pytest.approx(100, abs=1)

    def test_no_mop_adjudicado_fallback(self):
        r = score_tamano(_row(tipo_mop=None, monto_promedio=0,
                              monto_adjudicado=1_000_000_000))
        assert 0 < r <= 100

    def test_no_data_fallback_20(self):
        assert score_tamano(_row(tipo_mop=None, monto_promedio=0,
                                 monto_adjudicado=0)) == 20

    def test_nan_everything_fallback_20(self):
        assert score_tamano(_row(tipo_mop=None, monto_promedio=np.nan,
                                 monto_adjudicado=np.nan)) == 20

    def test_case_insensitive_mayor(self):
        assert score_tamano(_row(tipo_mop="MAYOR", categoria_mop="2da")) == 100


class TestScoreWinRate:
    def test_less_than_2_bids_returns_30(self):
        assert score_win_rate(_row(total_bids=1, win_rate=0.5)) == 30

    def test_zero_bids_returns_30(self):
        assert score_win_rate(_row(total_bids=0, win_rate=0)) == 30

    def test_optimal_25pct(self):
        assert score_win_rate(_row(total_bids=10, win_rate=0.25)) == pytest.approx(100, abs=0.5)

    def test_zero_wr(self):
        assert score_win_rate(_row(total_bids=10, win_rate=0)) == pytest.approx(0, abs=0.5)

    def test_50pct_above_ideal(self):
        r = score_win_rate(_row(total_bids=10, win_rate=0.5))
        assert 0 < r < 85

    def test_80pct_at_upper_bound(self):
        assert score_win_rate(_row(total_bids=10, win_rate=0.8)) == pytest.approx(0, abs=0.5)

    def test_15pct_lower_ideal(self):
        assert score_win_rate(_row(total_bids=10, win_rate=0.15)) >= 85

    def test_35pct_upper_ideal(self):
        assert score_win_rate(_row(total_bids=10, win_rate=0.35)) >= 85

    def test_nan_wr(self):
        assert score_win_rate(_row(total_bids=10, win_rate=np.nan)) == 0


class TestScoreRecencia:
    def test_zero_days_optimal(self):
        assert score_recencia(_row(dias_desde_ultima=0)) == pytest.approx(100, abs=0.5)

    def test_100_days_high(self):
        assert score_recencia(_row(dias_desde_ultima=100)) > 90

    def test_365_days_edge(self):
        assert score_recencia(_row(dias_desde_ultima=365)) >= 85

    def test_730_days_mid(self):
        r = score_recencia(_row(dias_desde_ultima=730))
        assert 0 < r < 85

    def test_1460_days_max(self):
        assert score_recencia(_row(dias_desde_ultima=1460)) == pytest.approx(0, abs=0.5)

    def test_over_max_zero(self):
        assert score_recencia(_row(dias_desde_ultima=9999)) == 0

    def test_nan_zero(self):
        assert score_recencia(_row(dias_desde_ultima=np.nan)) == 0

    def test_missing_column_defaults_high(self):
        # row.get("dias_desde_ultima", 9999) → 9999 > 1460 → 0
        assert score_recencia(pd.Series({"total_bids": 10})) == 0


class TestScoreValor:
    def test_zero_returns_20(self):
        assert score_valor(_row(monto_promedio=0)) == 20

    def test_nan_returns_20(self):
        assert score_valor(_row(monto_promedio=np.nan)) == 20

    def test_66m_lower_ideal(self):
        assert score_valor(_row(monto_promedio=66_000_000)) >= 85

    def test_500m_optimal(self):
        assert score_valor(_row(monto_promedio=500_000_000)) == pytest.approx(100, abs=0.5)

    def test_5b_upper_bound(self):
        assert score_valor(_row(monto_promedio=5_000_000_000)) == pytest.approx(0, abs=0.5)

    def test_200m_mid_range(self):
        r = score_valor(_row(monto_promedio=200_000_000))
        assert 85 <= r <= 100

    def test_1m_lower_bound(self):
        assert score_valor(_row(monto_promedio=1_000_000)) == pytest.approx(0, abs=0.5)


class TestScoreCompetencia:
    def test_zero_returns_30(self):
        assert score_competencia(_row(competidores_promedio=0)) == 30

    def test_nan_returns_30(self):
        assert score_competencia(_row(competidores_promedio=np.nan)) == 30

    def test_5_lower_ideal(self):
        assert score_competencia(_row(competidores_promedio=5)) >= 85

    def test_10_optimal(self):
        assert score_competencia(_row(competidores_promedio=10)) == pytest.approx(100, abs=0.5)

    def test_30_upper_bound(self):
        assert score_competencia(_row(competidores_promedio=30)) == pytest.approx(0, abs=0.5)

    def test_7_mid_range(self):
        r = score_competencia(_row(competidores_promedio=7))
        assert 85 <= r <= 100

    def test_1_at_lower_bound(self):
        # comp=1 es exactamente lower_bound → score 0
        assert score_competencia(_row(competidores_promedio=1)) == pytest.approx(0, abs=0.5)


class TestScoreOportunidad:
    def test_no_data_returns_30(self):
        assert score_oportunidad(_row(total_lost=0, n_distinct_rivals=0)) == 30

    def test_high_loss_high_rivals_100(self):
        # loss_rate=10/20=0.5→min(70,70)=70, bonus=min(30,30)=30→100
        r = score_oportunidad(_row(total_lost=10, total_bids=20, n_distinct_rivals=6))
        assert r == pytest.approx(100, abs=0.5)

    def test_moderate(self):
        # loss_rate=5/20=0.25→min(70,35)=35, bonus=min(30,15)=15→50
        r = score_oportunidad(_row(total_lost=5, total_bids=20, n_distinct_rivals=3))
        assert r == pytest.approx(50, abs=0.5)

    def test_zero_bids_no_div_error(self):
        # total_bids=max(1,0)=1 → loss_rate=1/1=1→70, bonus=5→75
        r = score_oportunidad(_row(total_lost=1, total_bids=0, n_distinct_rivals=1))
        assert r > 30

    def test_nan_lost_treated_as_zero(self):
        assert score_oportunidad(_row(total_lost=np.nan, n_distinct_rivals=0)) == 30

    def test_nan_rivals(self):
        # n_rivals=0, loss_rate=5/10=0.5→70, bonus=0→70
        r = score_oportunidad(_row(total_lost=5, total_bids=10, n_distinct_rivals=np.nan))
        assert r == pytest.approx(70, abs=0.5)

    def test_only_rivals_no_losses(self):
        # loss_rate=0→score=0, bonus=min(30,25)=25→25
        r = score_oportunidad(_row(total_lost=0, n_distinct_rivals=5, total_bids=10))
        assert r == pytest.approx(25, abs=0.5)

    def test_capped_at_100(self):
        r = score_oportunidad(_row(total_lost=100, total_bids=100, n_distinct_rivals=100))
        assert r <= 100


class TestScoreEspecializacion:
    def test_all_lp_max(self):
        # ratio_lp=1→min(100, 100+0+20)=100
        assert score_especializacion(_row(n_LP=10, n_LE=0, n_L1=0)) == 100

    def test_all_l1_low(self):
        # ratio_lp=0, ratio_le=0→min(100, 0+0+20)=20
        assert score_especializacion(_row(n_LP=0, n_LE=0, n_L1=10)) == pytest.approx(20, abs=0.5)

    def test_all_le_mid(self):
        # ratio_le=1→min(100, 0+50+20)=70
        assert score_especializacion(_row(n_LP=0, n_LE=10, n_L1=0)) == pytest.approx(70, abs=0.5)

    def test_mix(self):
        # ratio_lp=5/10=0.5, ratio_le=3/10=0.3→min(100, 50+15+20)=85
        assert score_especializacion(_row(n_LP=5, n_LE=3, n_L1=2)) == pytest.approx(85, abs=0.5)

    def test_zero_total_returns_30(self):
        assert score_especializacion(_row(n_LP=0, n_LE=0, n_L1=0)) == 30

    def test_nan_all_returns_30(self):
        assert score_especializacion(_row(n_LP=np.nan, n_LE=np.nan, n_L1=np.nan)) == 30

    def test_high_lp_le_capped_100(self):
        # ratio_lp=0.7, ratio_le=0.3→min(100, 70+15+20)=100
        assert score_especializacion(_row(n_LP=7, n_LE=3, n_L1=0)) == 100


class TestScoreRegion:
    def test_metropolitana_100(self):
        assert score_region(_row(region="Región Metropolitana de Santiago")) == 100

    def test_valparaiso_90(self):
        assert score_region(_row(region="Región de Valparaíso")) == 90

    def test_biobio_80(self):
        assert score_region(_row(region="Región del Biobío")) == 80

    def test_araucania_70(self):
        assert score_region(_row(region="Región de La Araucanía")) == 70

    def test_los_lagos_60(self):
        assert score_region(_row(region="Región de Los Lagos")) == 60

    def test_other_region_40(self):
        assert score_region(_row(region="Región de Atacama")) == 40

    def test_empty_50(self):
        assert score_region(_row(region="")) == 50

    def test_nan_50(self):
        assert score_region(_row(region=np.nan)) == 50

    def test_none_50(self):
        assert score_region(_row(region=None)) == 50

    def test_partial_match_santiago(self):
        assert score_region(_row(region="Santiago")) == 100

    def test_case_insensitive(self):
        assert score_region(_row(region="región metropolitana de santiago")) == 100


class TestScoreDigital:
    def test_web_and_email_30(self):
        assert score_digital(_drow(web="www.test.cl", email="a@b.cl")) == 30

    def test_web_only_50(self):
        assert score_digital(_drow(web="www.test.cl")) == 50

    def test_email_only_50(self):
        assert score_digital(_drow(email="a@b.cl")) == 50

    def test_phone_only_60(self):
        assert score_digital(_drow(telefono="+56912345678")) == 60

    def test_nothing_70(self):
        assert score_digital(_drow()) == 70

    def test_gm_web_counts_as_web(self):
        assert score_digital(_drow(gm_web="www.test.cl")) == 50

    def test_ocds_email_counts_as_email(self):
        assert score_digital(_drow(ocds_email="a@b.cl")) == 50

    def test_gm_telefono_counts_as_phone(self):
        assert score_digital(_drow(gm_telefono="+56922222222")) == 60

    def test_gm_web_plus_ocds_email_30(self):
        assert score_digital(_drow(gm_web="www.test.cl", ocds_email="a@b.cl")) == 30

    def test_web_phone_no_email_50(self):
        assert score_digital(_drow(web="www.test.cl", telefono="+56912345678")) == 50

    def test_missing_all_fields_70(self):
        # row sin campos digitales → .get() retorna None → 70
        assert score_digital(pd.Series({"total_bids": 10})) == 70


# ═══════════════════════════════════════════════════════════════════
# C) calculate_scores — integración
# ═══════════════════════════════════════════════════════════════════

class TestCalculateScores:
    def test_produces_score_total(self):
        assert "score_total" in calculate_scores(_make_df()).columns

    def test_score_total_range(self):
        df = calculate_scores(_make_df(10))
        assert (df["score_total"] >= 0).all()
        assert (df["score_total"] <= 100).all()

    def test_all_dim_columns_exist(self):
        df = calculate_scores(_make_df())
        for dim in SCORING_WEIGHTS:
            assert f"score_{dim}" in df.columns

    def test_dim_scores_in_range(self):
        df = calculate_scores(_make_df(10))
        for dim in SCORING_WEIGHTS:
            col = f"score_{dim}"
            assert (df[col] >= 0).all(), f"{col} tiene valores negativos"
            assert (df[col] <= 100).all(), f"{col} excede 100"

    def test_score_total_is_weighted_sum(self):
        df = calculate_scores(_make_df(5))
        for _, r in df.iterrows():
            expected = sum(r[f"score_{d}"] * w for d, w in SCORING_WEIGHTS.items())
            expected = max(0, min(100, round(expected, 1)))
            assert abs(r["score_total"] - expected) < 0.5

    def test_preserves_existing_columns(self):
        orig = set(_make_df().columns)
        assert orig.issubset(set(calculate_scores(_make_df()).columns))

    def test_row_count_preserved(self):
        assert len(calculate_scores(_make_df(7))) == 7

    def test_single_row(self):
        df = calculate_scores(_make_df(1))
        assert len(df) == 1
        assert 0 <= df.iloc[0]["score_total"] <= 100

    def test_dims_match_config(self):
        df = calculate_scores(_make_df())
        dims = {c for c in df.columns if c.startswith("score_") and c != "score_total"}
        assert dims == {f"score_{d}" for d in SCORING_WEIGHTS}


# ═══════════════════════════════════════════════════════════════════
# D) Bounds paramétricos — todos los scores en [0, 100]
# ═══════════════════════════════════════════════════════════════════

class TestAllScoresBounded:
    """Barrido paramétrico: ninguna función devuelve valores fuera de [0, 100]."""

    @pytest.mark.parametrize("bids", [0, 1, 5, 10, 15, 25, 50, 100, np.nan])
    def test_actividad(self, bids):
        assert 0 <= score_actividad(_row(total_bids=bids)) <= 100

    @pytest.mark.parametrize("wr", [0, 0.1, 0.15, 0.25, 0.35, 0.5, 0.8, 1.0, np.nan])
    def test_win_rate(self, wr):
        assert 0 <= score_win_rate(_row(total_bids=10, win_rate=wr)) <= 100

    @pytest.mark.parametrize("d", [0, 100, 365, 730, 1460, 5000, np.nan])
    def test_recencia(self, d):
        assert 0 <= score_recencia(_row(dias_desde_ultima=d)) <= 100

    @pytest.mark.parametrize("m", [0, 1e6, 66e6, 200e6, 500e6, 5e9, np.nan])
    def test_valor(self, m):
        assert 0 <= score_valor(_row(monto_promedio=m)) <= 100

    @pytest.mark.parametrize("c", [0, 1, 5, 7, 10, 20, 30, np.nan])
    def test_competencia(self, c):
        assert 0 <= score_competencia(_row(competidores_promedio=c)) <= 100

    @pytest.mark.parametrize("lost,rivals", [
        (0, 0), (5, 3), (10, 6), (0, 5), (100, 100),
    ])
    def test_oportunidad(self, lost, rivals):
        assert 0 <= score_oportunidad(_row(
            total_lost=lost, n_distinct_rivals=rivals, total_bids=20
        )) <= 100

    @pytest.mark.parametrize("lp,le,l1", [
        (0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10), (5, 3, 2),
    ])
    def test_especializacion(self, lp, le, l1):
        assert 0 <= score_especializacion(_row(n_LP=lp, n_LE=le, n_L1=l1)) <= 100

    @pytest.mark.parametrize("reg", [
        "Región Metropolitana de Santiago", "Región de Atacama", "", np.nan, None,
    ])
    def test_region(self, reg):
        assert 0 <= score_region(_row(region=reg)) <= 100


# ═══════════════════════════════════════════════════════════════════
# E) Consistencia de weights
# ═══════════════════════════════════════════════════════════════════

class TestWeightsConsistency:
    def test_weights_sum_to_1(self):
        assert sum(SCORING_WEIGHTS.values()) == pytest.approx(1.0)

    def test_nine_dimensions(self):
        assert len(SCORING_WEIGHTS) == 9

    def test_all_dims_have_scorer_function(self):
        for dim in SCORING_WEIGHTS:
            assert hasattr(score_mod, f"score_{dim}"), f"Falta score_{dim}"

    def test_ideal_ranges_consistent(self):
        for key, (lo, hi) in IDEAL_RANGES.items():
            assert lo < hi, f"IDEAL_RANGES[{key}]: min({lo}) >= max({hi})"

    def test_recencia_max_gt_365(self):
        assert RECENCIA_MAX_DAYS > 365

    def test_regiones_top_not_empty(self):
        assert len(REGIONES_TOP) >= 5
