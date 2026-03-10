"""
15 - Higiene y normalizacion de archivos .env.

Hace backup, normaliza nombres legacy y genera un reporte sin exponer secretos.

Uso:
  python 15_env_hygiene.py --write
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from config import BASE_DIR, OUTPUT_DIR, redact_secret
from utils import print_header

REPO_ROOT = BASE_DIR.parent
ENV_FILES = [
    REPO_ROOT / ".env",
    BASE_DIR / ".env",
]
CANONICAL_KEYS = [
    "APIFY_TOKEN",
    "MERCADO_PUBLICO_TICKET",
    "GOOGLE_MAPS_API_KEY",
]
LEGACY_ALIASES = {
    "APIFY_API_KEY": "APIFY_TOKEN",
}


def _parse_env(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return lines, values


def _normalize_values(values: dict[str, str]) -> dict[str, str]:
    normalized = dict(values)
    for legacy_key, canonical_key in LEGACY_ALIASES.items():
        if legacy_key in normalized and canonical_key not in normalized:
            normalized[canonical_key] = normalized[legacy_key]
        normalized.pop(legacy_key, None)
    return normalized


def _render_env(path: Path, values: dict[str, str]) -> str:
    header = "# Runtime secrets\n" if path.parent == BASE_DIR else "# Workspace secrets mirror\n"
    body = "\n".join(
        f"{key}={values[key]}"
        for key in CANONICAL_KEYS
        if values.get(key, "").strip()
    )
    return f"{header}{body}\n"


def _backup_path(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.name}.bak.{timestamp}")


def _mask_map(values: dict[str, str]) -> dict[str, str]:
    return {key: redact_secret(value) for key, value in values.items()}


def build_report(write: bool = False) -> dict:
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "write": write,
        "files": [],
    }

    parsed: dict[Path, dict[str, str]] = {}
    for path in ENV_FILES:
        file_report = {
            "path": str(path),
            "exists": path.exists(),
            "backup": None,
            "normalized_keys": [],
            "masked": {},
            "written": False,
        }
        if path.exists():
            _, values = _parse_env(path)
            normalized = _normalize_values(values)
            normalized_keys = sorted(set(values) - set(normalized))
            file_report["normalized_keys"] = normalized_keys
            file_report["masked"] = _mask_map(normalized)
            parsed[path] = normalized

            if write:
                backup = _backup_path(path)
                path.replace(backup)
                path.write_text(_render_env(path, normalized), encoding="utf-8")
                file_report["backup"] = str(backup)
                file_report["written"] = True
        report["files"].append(file_report)

    shared = {}
    existing = [path for path in ENV_FILES if path in parsed]
    if len(existing) == 2:
        left = parsed[existing[0]]
        right = parsed[existing[1]]
        for key in CANONICAL_KEYS:
            shared[key] = {
                "present_in_both": key in left and key in right,
                "same_value": (
                    key in left and key in right and left[key] == right[key]
                ),
            }
    report["shared_keys"] = shared
    return report


def main() -> None:
    print_header("Higiene .env")
    write = "--write" in sys.argv
    report = build_report(write=write)
    out_path = OUTPUT_DIR / "env_hygiene_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Reporte: {out_path}")
    for item in report["files"]:
        print(f"  {item['path']}: {'ok' if item['exists'] else 'missing'}")
        if item["normalized_keys"]:
            print(f"    aliases normalizados: {', '.join(item['normalized_keys'])}")
        if item["written"]:
            print(f"    backup: {item['backup']}")


if __name__ == "__main__":
    main()
