"""
Fixtures reutilizables para la suite de tests del pipeline.

Provee datos sintéticos para tests unitarios y paths a datos reales
para tests de integración (saltados si no existen).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Asegurar que lead_scoring/ esté en sys.path para imports directos
LEAD_SCORING_DIR = Path(__file__).resolve().parent.parent
if str(LEAD_SCORING_DIR) not in sys.path:
    sys.path.insert(0, str(LEAD_SCORING_DIR))

# ── Paths a parquets reales ──────────────────────────────────────────

FILTERED_DIR = LEAD_SCORING_DIR / "data" / "filtered"
OUTPUT_DIR = LEAD_SCORING_DIR / "data" / "output"

COMPANY_DB_PATH = FILTERED_DIR / "company_database.parquet"
LEADS_RANKED_PATH = FILTERED_DIR / "leads_ranked.parquet"
LEADS_ML_RANKED_PATH = FILTERED_DIR / "leads_ml_ranked.parquet"
LEADS_ENRICHED_PATH = FILTERED_DIR / "leads_enriched.parquet"
LOSS_ANALYSIS_PATH = OUTPUT_DIR / "loss_analysis.parquet"


# ── Marcadores para saltar si faltan datos reales ────────────────────

skip_no_company_db = pytest.mark.skipif(
    not COMPANY_DB_PATH.exists(),
    reason="company_database.parquet no disponible",
)
skip_no_leads_ranked = pytest.mark.skipif(
    not LEADS_RANKED_PATH.exists(),
    reason="leads_ranked.parquet no disponible",
)
skip_no_leads_ml_ranked = pytest.mark.skipif(
    not LEADS_ML_RANKED_PATH.exists(),
    reason="leads_ml_ranked.parquet no disponible",
)
skip_no_leads_enriched = pytest.mark.skipif(
    not LEADS_ENRICHED_PATH.exists(),
    reason="leads_enriched.parquet no disponible",
)
skip_no_loss_analysis = pytest.mark.skipif(
    not LOSS_ANALYSIS_PATH.exists(),
    reason="loss_analysis.parquet no disponible",
)


# ── Fixtures: datos sintéticos ───────────────────────────────────────

@pytest.fixture
def sample_company_row() -> pd.Series:
    """Una fila representativa de company_database.parquet."""
    return pd.Series({
        "rut": "76543210-K",
        "nombre": "CONSTRUCTORA EXAMPLE LTDA | Example",
        "region": "Región Metropolitana de Santiago",
        "total_bids": 12,
        "total_wins": 4,
        "win_rate": 0.333,
        "monto_promedio": 150_000_000.0,
        "monto_total": 1_800_000_000.0,
        "monto_adjudicado": 600_000_000.0,
        "ultima_oferta": pd.Timestamp("2025-10-15"),
        "primera_oferta": pd.Timestamp("2022-06-01"),
        "dias_desde_ultima": 164,
        "n_LP": 5,
        "n_LE": 4,
        "n_L1": 3,
        "competidores_promedio": 7.5,
        "total_lost": 6,
        "n_distinct_rivals": 4,
        "tipo_mop": "Mayor",
        "categoria_mop": "2da categoría",
        "es_persona_natural": False,
        "tipos_licitacion": {"LP": 5, "LE": 4, "L1": 3},
    })


@pytest.fixture
def sample_leads_df() -> pd.DataFrame:
    """DataFrame pequeño con leads rankeados (5 filas)."""
    rng = np.random.RandomState(42)
    n = 5
    scores = rng.uniform(30, 90, n).round(1)
    data = {
        "rut": [f"7654321{i}-{chr(75-i)}" for i in range(n)],
        "nombre": [f"EMPRESA TEST {i} LTDA" for i in range(n)],
        "region": ["Región Metropolitana de Santiago"] * n,
        "total_bids": rng.randint(3, 25, n),
        "total_wins": rng.randint(0, 10, n),
        "win_rate": rng.uniform(0.05, 0.5, n).round(3),
        "monto_promedio": rng.uniform(10_000_000, 500_000_000, n),
        "dias_desde_ultima": rng.randint(30, 800, n),
        "n_LP": rng.randint(0, 10, n),
        "n_LE": rng.randint(0, 8, n),
        "n_L1": rng.randint(0, 6, n),
        "competidores_promedio": rng.uniform(2, 15, n).round(1),
        "total_lost": rng.randint(0, 12, n),
        "n_distinct_rivals": rng.randint(0, 8, n),
        "score_actividad": rng.uniform(40, 100, n).round(1),
        "score_tamano": rng.uniform(20, 100, n).round(1),
        "score_win_rate": rng.uniform(30, 100, n).round(1),
        "score_recencia": rng.uniform(0, 100, n).round(1),
        "score_valor": rng.uniform(20, 100, n).round(1),
        "score_competencia": rng.uniform(30, 100, n).round(1),
        "score_oportunidad": rng.uniform(30, 100, n).round(1),
        "score_especializacion": rng.uniform(20, 100, n).round(1),
        "score_region": rng.uniform(40, 100, n).round(1),
        "score_total": scores,
        "rank": list(range(1, n + 1)),
    }
    df = pd.DataFrame(data)
    # Asegurar win_rate consistente
    df["win_rate"] = (df["total_wins"] / df["total_bids"].clip(lower=1)).round(3)
    return df.sort_values("score_total", ascending=False).reset_index(drop=True)


@pytest.fixture
def sample_enriched_df(sample_leads_df) -> pd.DataFrame:
    """DataFrame con campos de enriquecimiento (contacto, teléfono, etc.)."""
    df = sample_leads_df.copy()
    df["score_combined"] = (df["score_total"] * 0.9 + 5).round(1).clip(0, 100)
    df["rank_ml"] = range(1, len(df) + 1)
    df["km_score"] = (df["score_total"] * 0.8 + 10).round(1).clip(0, 100)
    df["xgb_score"] = (df["score_total"] * 0.85 + 8).round(1).clip(0, 100)
    df["cluster"] = [0, 1, 2, 1, 0]
    df["cluster_perfil"] = ["LEAD IDEAL", "LEAD BUENO", "LEAD REGULAR",
                            "LEAD BUENO", "LEAD BAJO"]
    df["telefono"] = ["+56912345678", None, "+56987654321", None, "+56911111111"]
    df["email"] = ["test@empresa.cl", None, "info@otra.cl", None, None]
    df["web"] = ["www.empresa.cl", None, None, None, None]
    df["contacto_nombre"] = ["Juan Pérez", None, "María López", None, None]
    df["gm_telefono"] = [None, "+56922222222", None, None, None]
    df["gm_web"] = [None, "www.empresa2.cl", None, None, None]
    df["gm_email"] = [None, None, None, None, None]
    df["ocds_email"] = [None, None, None, "ocds@test.cl", None]
    df["ocds_telefono"] = [None, None, None, "+56933333333", None]
    df["ocds_contacto"] = [None, None, None, "Carlos Ruiz", None]
    df["score_digital"] = [30.0, 50.0, 60.0, 50.0, 70.0]
    df["xgb_predicted_wr"] = [0.28, 0.22, 0.15, 0.31, 0.10]
    return df


@pytest.fixture
def sample_loss_df() -> pd.DataFrame:
    """DataFrame sintético de loss_analysis."""
    return pd.DataFrame({
        "rut": ["76543210-K", "76543211-J", "76543212-I"],
        "total_participated": [20, 15, 8],
        "total_won": [5, 3, 0],
        "total_lost": [10, 8, 5],
        "loss_rate": [0.50, 0.533, 0.625],
        "rival1": ["RIVAL PRINCIPAL SPA", "OTRO RIVAL LTDA", ""],
        "rival1_cnt": [4, 2, 0],
    })


# ── Fixtures: textos para tests de seguridad ─────────────────────────

@pytest.fixture
def clean_text() -> str:
    """Texto seguro para enviar a clientes — sin términos internos."""
    return (
        "Hola Juan, soy Sebastián de IngenIA Licitaciones.\n\n"
        "Detecté que su empresa participó en 12 licitaciones LP el último año "
        "con una tasa de adjudicación del 18%, mientras que el promedio del rubro "
        "es 22%. Hay un patrón en las propuestas ganadoras que podría serle útil.\n\n"
        "¿Le interesa saber qué están haciendo diferente los que ganan?\n\n"
        "Sebastián Cortés\n"
        "IngenIA Licitaciones"
    )


@pytest.fixture
def dirty_text() -> str:
    """Texto con términos internos que NUNCA deberían llegar al cliente."""
    return (
        "Su score_total es 78.5 y está en el cluster LEAD IDEAL. "
        "El xgb_score predice un win rate de 0.28. "
        "Su km_score es 82 y el score_combined es 80.2. "
        "El ranking del pipeline lo ubica en posición 15."
    )


# ── Fixtures: parquets reales (se saltan si no existen) ──────────────

@pytest.fixture
def real_company_db():
    """Carga company_database.parquet real — se salta si no existe."""
    if not COMPANY_DB_PATH.exists():
        pytest.skip("company_database.parquet no disponible")
    return pd.read_parquet(COMPANY_DB_PATH)


@pytest.fixture
def real_leads_ranked():
    """Carga leads_ranked.parquet real — se salta si no existe."""
    if not LEADS_RANKED_PATH.exists():
        pytest.skip("leads_ranked.parquet no disponible")
    return pd.read_parquet(LEADS_RANKED_PATH)


@pytest.fixture
def real_leads_ml_ranked():
    """Carga leads_ml_ranked.parquet real — se salta si no existe."""
    if not LEADS_ML_RANKED_PATH.exists():
        pytest.skip("leads_ml_ranked.parquet no disponible")
    return pd.read_parquet(LEADS_ML_RANKED_PATH)


@pytest.fixture
def real_leads_enriched():
    """Carga leads_enriched.parquet real — se salta si no existe."""
    if not LEADS_ENRICHED_PATH.exists():
        pytest.skip("leads_enriched.parquet no disponible")
    return pd.read_parquet(LEADS_ENRICHED_PATH)


@pytest.fixture
def real_loss_analysis():
    """Carga loss_analysis.parquet real — se salta si no existe."""
    if not LOSS_ANALYSIS_PATH.exists():
        pytest.skip("loss_analysis.parquet no disponible")
    return pd.read_parquet(LOSS_ANALYSIS_PATH)
