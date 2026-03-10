"""
Configuración central del pipeline de Lead Scoring.
"""
from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import os
import sys

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# === Paths ===
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"          # CSVs bulk descargados
FILTERED_DIR = DATA_DIR / "filtered"  # Parquet filtrados
OUTPUT_DIR = DATA_DIR / "output"      # Excel/CSV finales
BACKUP_DIR = BASE_DIR.parent / "backups"

for d in [DATA_DIR, RAW_DIR, FILTERED_DIR, OUTPUT_DIR, BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === APIs ===
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
MERCADO_PUBLICO_TICKET = os.getenv("MERCADO_PUBLICO_TICKET", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

PLACEHOLDER_SECRET_VALUES = {
    "replace_me",
    "changeme",
    "change_me",
    "your_value_here",
    "todo",
    "set_me",
}

PYTHON_BASELINE = (3, 8)
PYTHON_TARGET = (3, 10)

OCDS_TENDER_URL = "https://apis.mercadopublico.cl/OCDS/data/tender/{codigo}"
OCDS_AWARD_URL = "https://apis.mercadopublico.cl/OCDS/data/award/{codigo}"

# Bulk data - descarga por año
BULK_BASE_URL = "https://data.open-contracting.org/en/publication/144/download"
BULK_YEARS = [2022, 2023, 2024, 2025]

# === MOP Contratistas ===
MOP_MAYORES_URL = "https://www.mop.gob.cl/serviciosmop/listado-contratistas-de-obras-mayores-mop/"
MOP_MENORES_URL = "https://www.mop.gob.cl/serviciosmop/listado-contratistas-de-obras-menores-mop/"

# === Filtrado ===
# UNSPSC códigos que empiezan con 72 = Servicios de edificación, construcción
CONSTRUCTION_UNSPSC_PREFIX = "72"

# === Scoring: 9 dimensiones ===
# Nota: "digital" se removió del heurístico porque pre-enrichment TODOS
# tienen score_digital=70 (sin datos de contacto), causando 0 varianza.
# Se aplica post-enrichment en 06_enrich_contacts.py solo para top 100.
SCORING_WEIGHTS = {
    "actividad":       0.20,  # Bids en últimos 12 meses
    "tamano":          0.14,  # Categoría MOP (proxy de tamaño)
    "win_rate":        0.12,  # Tasa de adjudicación
    "recencia":        0.12,  # Días desde última oferta
    "valor":           0.12,  # Monto promedio de licitaciones
    "competencia":     0.10,  # Promedio de competidores por licitación
    "oportunidad":     0.10,  # Derrotas y rivales (más derrotas = más oportunidad)
    "especializacion": 0.06,  # Tipo de obras
    "region":          0.04,  # Región con más licitaciones
}

# Rangos ideales para scoring (score máximo si cae en este rango)
IDEAL_RANGES = {
    "actividad": (5, 15),        # 5-15 licitaciones/año
    "win_rate": (0.15, 0.35),    # 15-35%
    "recencia_dias": (0, 365),   # Menos de 1 año (ciclos construcción largos)
    "valor_clp": (66_000_000, 500_000_000),  # $66M-$500M (LP)
    "competencia": (5, 10),      # 5-10 competidores
}

# Cota máxima para recencia (4 años de datos 2022-2025)
RECENCIA_MAX_DAYS = 1460

# Tipos de licitación
TIPOS_LICITACION = {
    "L1": "Menor (<100 UTM)",
    "LE": "Entre (100-1000 UTM)",
    "LP": "Mayor (>1000 UTM)",
    "LR": "Restringida",
}

# Regiones con más actividad de construcción (bonus scoring)
REGIONES_TOP = [
    "Región Metropolitana de Santiago",
    "Región de Valparaíso",
    "Región del Biobío",
    "Región de La Araucanía",
    "Región de Los Lagos",
]

# === Enriquecimiento ===
ENRICH_TOP_N = 100  # Enriquecer top N leads
APIFY_GOOGLE_MAPS_ACTOR = "nwua9Gu5YrADL7ZDj"  # compass/Google-Maps-Scraper

# === CSV Bulk: archivos clave ===
BULK_CSV_FILES = {
    "tenders":    "main.csv",
    "tenderers":  "tender_tenderers.csv",
    "items":      "tender_items.csv",
    "awards":     "awards.csv",
    "suppliers":  "awards_suppliers.csv",
    "parties":    "parties.csv",
    "documents":  "awards_documents.csv",
}


def python_runtime_label(version_info=None) -> str:
    version_info = version_info or sys.version_info
    return f"{version_info.major}.{version_info.minor}"


def runtime_support_status(version_info=None) -> str:
    version_info = version_info or sys.version_info
    current = (version_info.major, version_info.minor)
    if current == PYTHON_BASELINE:
        return "baseline"
    if current == PYTHON_TARGET:
        return "target"
    return "unverified"


def missing_env_vars(required_vars: list[str]) -> list[str]:
    """Retorna variables faltantes o vacias."""
    return [
        var for var in required_vars
        if env_value_status(os.getenv(var, "")) != "ok"
    ]


def env_value_status(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return "missing"
    if normalized.lower() in PLACEHOLDER_SECRET_VALUES:
        return "placeholder"
    return "ok"


def redact_secret(value: str) -> str:
    status = env_value_status(value)
    if status == "missing":
        return "<missing>"
    if status == "placeholder":
        return "<placeholder>"
    return f"<configured:{len(value.strip())} chars>"


def env_var_report(required_vars: list[str]) -> list[dict[str, str]]:
    report = []
    for var in required_vars:
        value = os.getenv(var, "")
        report.append({
            "name": var,
            "status": env_value_status(value),
            "value": redact_secret(value),
        })
    return report


def assert_env_vars(required_vars: list[str], *, context: str,
                    raise_on_missing: bool = True) -> list[str]:
    """Valida variables de entorno requeridas para un flujo concreto."""
    missing = missing_env_vars(required_vars)
    if missing and raise_on_missing:
        raise RuntimeError(
            f"Faltan variables de entorno para {context}: {', '.join(missing)}. "
            f"Completa {ENV_PATH} a partir de .env.example."
        )
    return missing
