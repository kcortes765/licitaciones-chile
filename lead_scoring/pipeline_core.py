"""
Core compartido del pipeline.

Centraliza:
  - priorizacion de datasets de leads
  - recomputo consistente de score_total y score_combined
  - ranking y perfiles
  - resumenes de cobertura
  - export CRM interno
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from config import FILTERED_DIR, OUTPUT_DIR, SCORING_WEIGHTS

LEAD_SOURCE_PRIORITY = (
    "leads_enriched.parquet",
    "leads_ml_ranked.parquet",
    "leads_ranked.parquet",
)

COMBINED_SCORE_WEIGHTS = {
    "score_total": 0.70,
    "km_score": 0.15,
    "xgb_score": 0.15,
}

CLIENT_FORBIDDEN_COLUMNS = {
    "score_total",
    "score_combined",
    "cluster",
    "cluster_perfil",
    "km_score",
    "xgb_score",
    "xgb_predicted_wr",
    "score_digital",
}


def find_best_leads_path(
    filtered_dir: Path = FILTERED_DIR,
    *,
    priority: tuple[str, ...] = LEAD_SOURCE_PRIORITY,
) -> Path | None:
    """Retorna el mejor dataset de leads disponible, con prioridad fija."""
    for name in priority:
        candidate = filtered_dir / name
        if candidate.exists():
            return candidate
    return None


def load_best_leads_dataframe(
    filtered_dir: Path = FILTERED_DIR,
    *,
    priority: tuple[str, ...] = LEAD_SOURCE_PRIORITY,
) -> tuple[pd.DataFrame, Path]:
    """Carga el mejor dataset de leads disponible."""
    path = find_best_leads_path(filtered_dir, priority=priority)
    if path is None:
        raise FileNotFoundError(
            "No se encontro un dataset de leads. Esperado uno de: "
            + ", ".join(priority)
        )
    return pd.read_parquet(path), path


def _missing_score_columns(df: pd.DataFrame) -> list[str]:
    return [f"score_{dim}" for dim in SCORING_WEIGHTS if f"score_{dim}" not in df.columns]


def recompute_score_total(df: pd.DataFrame) -> pd.DataFrame:
    """Recalcula score_total usando una unica fuente de verdad."""
    missing = _missing_score_columns(df)
    if missing:
        raise ValueError(f"No se puede recalcular score_total. Faltan columnas: {missing}")

    df = df.copy()
    df["score_total"] = sum(
        df[f"score_{dim}"] * weight
        for dim, weight in SCORING_WEIGHTS.items()
    ).clip(0, 100).round(1)
    return df


def recompute_score_combined(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalcula score_combined con pesos estables.

    Si faltan km_score o xgb_score, su contribucion cae a un baseline neutral
    igual a score_total. Asi los datasets pre-ML no se castigan artificialmente,
    pero cuando existen señales ML siguen entrando con los pesos congelados.
    """
    df = df.copy()
    if "score_total" not in df.columns:
        raise ValueError("No se puede recalcular score_combined sin score_total")

    score_total = pd.to_numeric(df["score_total"], errors="coerce").fillna(0)
    total = score_total * COMBINED_SCORE_WEIGHTS["score_total"]

    for col in ("km_score", "xgb_score"):
        signal = score_total
        if col in df.columns:
            signal = pd.to_numeric(df[col], errors="coerce").fillna(score_total)
        total = total + signal * COMBINED_SCORE_WEIGHTS[col]
    df["score_combined"] = total.clip(0, 100).round(1)
    return df


def assign_cluster_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna cluster_perfil con base en score_combined."""
    df = df.copy()
    if "score_combined" not in df.columns:
        raise ValueError("No se puede asignar cluster_perfil sin score_combined")

    sc_pct = df["score_combined"].rank(pct=True)
    df["cluster_perfil"] = pd.cut(
        sc_pct,
        bins=[0, 0.40, 0.70, 0.90, 1.01],
        labels=["LEAD BAJO", "LEAD REGULAR", "LEAD BUENO", "LEAD IDEAL"],
    ).astype(str)
    return df


def assign_rank(df: pd.DataFrame, score_col: str, rank_col: str) -> pd.DataFrame:
    """Ordena por score y asigna ranking secuencial."""
    df = df.sort_values(score_col, ascending=False).reset_index(drop=True).copy()
    df[rank_col] = range(1, len(df) + 1)
    return df


def resolve_score_column(df: pd.DataFrame) -> str:
    if "score_combined" in df.columns:
        return "score_combined"
    if "score_total" in df.columns:
        return "score_total"
    raise ValueError("No existe score_total ni score_combined")


def resolve_rank_column(df: pd.DataFrame) -> str:
    if "rank_ml" in df.columns:
        return "rank_ml"
    if "rank" in df.columns:
        return "rank"
    raise ValueError("No existe rank ni rank_ml")


def contact_coverage_summary(df: pd.DataFrame) -> dict[str, int]:
    """Resumen compacto de cobertura comercial."""
    summary = {
        "total_leads": len(df),
        "con_telefono": 0,
        "con_email": 0,
        "con_web": 0,
        "con_rival": 0,
        "pdf_listo": 0,
        "outreach_listo": 0,
    }
    if "telefono" in df.columns:
        summary["con_telefono"] = int(df["telefono"].notna().sum())
    if "email" in df.columns:
        summary["con_email"] = int(df["email"].notna().sum())
    if "web" in df.columns:
        summary["con_web"] = int(df["web"].notna().sum())
    if "top_rival_1_name" in df.columns:
        summary["con_rival"] = int(df["top_rival_1_name"].notna().sum())
    return summary


def _series_or_default(df: pd.DataFrame, col: str, default):
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def build_crm_dataframe(
    df: pd.DataFrame,
    *,
    tender_codigo: str = "",
    tender_nombre: str = "",
    default_channel: str = "WhatsApp",
) -> pd.DataFrame:
    """Crea un CRM minimo y Google Sheets-friendly."""
    crm = pd.DataFrame({
        "empresa": _series_or_default(df, "nombre", "").fillna(_series_or_default(df, "rut", "")),
        "rut": _series_or_default(df, "rut", ""),
        "contacto": _series_or_default(df, "contacto_nombre", ""),
        "telefono": _series_or_default(df, "telefono", ""),
        "email": _series_or_default(df, "email", ""),
        "licitacion_codigo": tender_codigo,
        "licitacion_nombre": tender_nombre,
        "fecha_contacto": "",
        "canal": default_channel,
        "estado": "Pendiente",
        "proximo_follow_up": "",
        "notas": "",
        "resultado": "",
    })
    if "rank_ml" in df.columns:
        crm["prioridad"] = df["rank_ml"]
    elif "rank" in df.columns:
        crm["prioridad"] = df["rank"]
    else:
        crm["prioridad"] = range(1, len(df) + 1)
    return crm


def list_existing_outputs(paths: Iterable[Path]) -> list[str]:
    return [str(path) for path in paths if path.exists()]


def coverage_report_path(output_dir: Path = OUTPUT_DIR) -> Path:
    return output_dir / "coverage_report.json"
