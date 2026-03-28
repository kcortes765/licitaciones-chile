"""
Contratos y validaciones compartidas del pipeline.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

PIPELINE_CONTRACTS = {
    "company_database": {
        "required": [
            "rut", "total_bids", "total_wins", "win_rate", "monto_promedio",
            "dias_desde_ultima", "n_LP", "n_LE", "n_L1",
        ],
        "unique": ["rut"],
        "ranges": {"win_rate": (0, 1)},
    },
    "leads_ranked": {
        "required": ["rut", "score_total", "rank"],
        "unique": ["rut"],
        "ranges": {"score_total": (0, 100), "rank": (1, None), "win_rate": (0, 1)},
    },
    "leads_ml_ranked": {
        "required": ["rut", "score_total", "score_combined", "rank_ml"],
        "unique": ["rut"],
        "ranges": {"score_total": (0, 100), "score_combined": (0, 100), "rank_ml": (1, None)},
    },
    "leads_enriched": {
        "required": ["rut", "score_total", "score_combined"],
        "unique": ["rut"],
        "ranges": {"score_total": (0, 100), "score_combined": (0, 100), "score_digital": (0, 100)},
    },
    "loss_analysis": {
        "required": ["rut", "total_participated", "total_won", "loss_rate"],
        "unique": ["rut"],
        "ranges": {"loss_rate": (0, 1)},
    },
    "matches": {
        "required": ["tender_codigo", "lead_rut", "match_score"],
        "ranges": {"match_score": (0, 100)},
    },
}

CLIENT_FORBIDDEN_PATTERNS = (
    re.compile(r"\bscore_(?!digital)\w+\b", re.IGNORECASE),
    re.compile(r"\bscore_combined\b", re.IGNORECASE),
    re.compile(r"\bcluster(_perfil)?\b", re.IGNORECASE),
    re.compile(r"\bxgb_\w+\b", re.IGNORECASE),
    re.compile(r"\bkm_\w+\b", re.IGNORECASE),
    re.compile(r"\blead ideal\b", re.IGNORECASE),
    re.compile(r"\brank_position\b", re.IGNORECASE),
)

_BINARY_TEXT_CHUNK_PATTERN = re.compile(rb"[A-Za-z0-9_@:/\.\-\s]{4,}")


def validate_dataframe_contract(df: pd.DataFrame, artifact_name: str) -> list[str]:
    """Valida columnas, unicidad y rangos basicos de un artifacto."""
    contract = PIPELINE_CONTRACTS.get(artifact_name)
    if contract is None:
        raise KeyError(f"Contrato desconocido: {artifact_name}")

    issues: list[str] = []
    required = contract.get("required", [])
    missing = [col for col in required if col not in df.columns]
    if missing:
        issues.append(f"Faltan columnas requeridas: {missing}")

    unique_col = contract.get("unique")
    if unique_col and all(col in df.columns for col in unique_col):
        dupes = int(df.duplicated(subset=unique_col).sum())
        if dupes:
            issues.append(f"Hay {dupes} filas duplicadas en {unique_col}")

    for col, (min_value, max_value) in contract.get("ranges", {}).items():
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if min_value is not None and not series.empty and (series < min_value).any():
            issues.append(f"{col} contiene valores menores a {min_value}")
        if max_value is not None and not series.empty and (series > max_value).any():
            issues.append(f"{col} contiene valores mayores a {max_value}")

    if "rut" in df.columns and df["rut"].isna().any():
        issues.append("Existen filas sin rut")

    return issues


def assert_dataframe_contract(df: pd.DataFrame, artifact_name: str) -> None:
    issues = validate_dataframe_contract(df, artifact_name)
    if issues:
        raise ValueError(f"Contrato invalido para {artifact_name}: " + " | ".join(issues))


def _scan_text_forbidden(text: str) -> list[str]:
    matches = []
    for pattern in CLIENT_FORBIDDEN_PATTERNS:
        if pattern.search(text):
            matches.append(pattern.pattern)
    return matches


_STREAM_BLOCK_PATTERN = re.compile(rb"\bstream\b.*?\bendstream\b", re.DOTALL)


def _extract_text_like_chunks(data: bytes) -> str:
    """
    Extrae segmentos imprimibles desde binarios para evitar buscar substrings
    crudas dentro del stream completo del PDF.

    Excluye bloques stream...endstream que contienen datos comprimidos
    (imagenes, fonts) donde secuencias aleatorias pueden causar falsos positivos.
    """
    cleaned = _STREAM_BLOCK_PATTERN.sub(b" ", data)
    chunks = _BINARY_TEXT_CHUNK_PATTERN.findall(cleaned)
    if not chunks:
        return ""
    return "\n".join(
        chunk.decode("latin-1", errors="ignore")
        for chunk in chunks
    )


def assert_client_safe_columns(df: pd.DataFrame, allowed_columns: set[str] | None = None) -> None:
    """Bloquea columnas internas en artefactos cliente-facing."""
    offending = []
    for col in df.columns:
        if allowed_columns and col in allowed_columns:
            continue
        if _scan_text_forbidden(col):
            offending.append(col)
    if offending:
        raise ValueError(f"Columnas no permitidas en artefacto cliente-facing: {offending}")


def assert_client_safe_text(text: str, artifact_name: str) -> None:
    offending = _scan_text_forbidden(text)
    if offending:
        raise ValueError(
            f"Se detectaron patrones internos en {artifact_name}: {offending}"
        )


def assert_client_safe_json(payload: Any, artifact_name: str) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    assert_client_safe_text(serialized, artifact_name)


def assert_client_safe_binary(path: Path) -> None:
    """
    Chequeo ligero de PDF/binarios usando solo texto imprimible extraido.

    Esto evita falsos positivos por coincidencias accidentales dentro del stream
    binario completo y reutiliza las mismas reglas de texto cliente-safe.
    """
    data = path.read_bytes()
    extracted_text = _extract_text_like_chunks(data)
    offending = _scan_text_forbidden(extracted_text)
    if offending:
        raise ValueError(f"Artefacto binario contiene tokens internos: {offending}")


def write_run_manifest(
    path: Path,
    *,
    command: str,
    source: str,
    outputs: list[str],
    details: dict[str, Any] | None = None,
) -> None:
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "command": command,
        "source": source,
        "outputs": outputs,
        "details": details or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def write_validation_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
