"""
14 - Preflight operativo y de seguridad.

Valida:
  - runtime soportado
  - repo y .gitignore
  - secretos requeridos/placeholder
  - scripts y documentos operativos/comerciales
  - dataset de leads disponible

Uso:
  python 14_operational_preflight.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import (
    BASE_DIR,
    ENV_PATH,
    FILTERED_DIR,
    OUTPUT_DIR,
    env_var_report,
    python_runtime_label,
    runtime_support_status,
)
from pipeline_core import find_best_leads_path
from utils import print_header

REPO_ROOT = BASE_DIR.parent
ROOT_ENV_PATH = REPO_ROOT / ".env"
ROOT_GITIGNORE = REPO_ROOT / ".gitignore"

REQUIRED_SCRIPTS = [
    BASE_DIR / "run_smoke_pipeline.py",
    BASE_DIR / "validate_outputs.py",
    BASE_DIR / "12_monitor_api.py",
    BASE_DIR / "11_generate_diagnostic_pdf.py",
]

REQUIRED_DOCS = [
    REPO_ROOT / "README.md",
    BASE_DIR / "OPERATIONS.md",
    BASE_DIR / "COMMERCIAL_PLAYBOOK.md",
    REPO_ROOT / "commercial" / "OFERTA_SERVICIO.md",
    REPO_ROOT / "commercial" / "NDA_SIMPLE.md",
    REPO_ROOT / "commercial" / "PROPUESTA_BASE.md",
    REPO_ROOT / "commercial" / "FOLLOWUP_SEQUENCE.md",
]

REQUIRED_GITIGNORE_PATTERNS = [
    ".env",
    "lead_scoring/.env",
    "lead_scoring/data/raw/",
    "lead_scoring/data/filtered/",
    "lead_scoring/data/output/",
]


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _check_git() -> dict:
    result = {"name": "git_repo", "status": "ok", "details": {}}
    probe = _run_git(["rev-parse", "--is-inside-work-tree"])
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        result["status"] = "blocker"
        result["details"] = {"error": probe.stderr.strip() or probe.stdout.strip()}
        return result

    result["details"]["repo_root"] = str(REPO_ROOT)
    ignored = {}
    for path in [ROOT_ENV_PATH, ENV_PATH]:
        check_ignore = _run_git(["check-ignore", str(path)])
        ignored[str(path)] = check_ignore.returncode == 0
    result["details"]["env_ignored"] = ignored
    if not all(ignored.values()):
        result["status"] = "blocker"
    return result


def _check_gitignore() -> dict:
    result = {"name": "gitignore", "status": "ok", "details": {}}
    if not ROOT_GITIGNORE.exists():
        result["status"] = "blocker"
        result["details"]["missing_file"] = str(ROOT_GITIGNORE)
        return result

    text = ROOT_GITIGNORE.read_text(encoding="utf-8")
    missing = [pattern for pattern in REQUIRED_GITIGNORE_PATTERNS if pattern not in text]
    result["details"]["missing_patterns"] = missing
    if missing:
        result["status"] = "blocker"
    return result


def _check_runtime() -> dict:
    status = runtime_support_status()
    result = {
        "name": "runtime",
        "status": "ok" if status in {"baseline", "target"} else "warning",
        "details": {
            "python": python_runtime_label(),
            "support_status": status,
        },
    }
    return result


def _check_env() -> dict:
    result = {"name": "env", "status": "ok", "details": {}}
    result["details"]["env_path"] = str(ENV_PATH)
    result["details"]["env_exists"] = ENV_PATH.exists()
    result["details"]["root_env_exists"] = ROOT_ENV_PATH.exists()
    result["details"]["required"] = env_var_report([
        "GOOGLE_MAPS_API_KEY",
        "MERCADO_PUBLICO_TICKET",
    ])
    result["details"]["optional"] = env_var_report(["APIFY_TOKEN"])

    blocker_statuses = {
        item["name"]: item["status"]
        for item in result["details"]["required"]
        if item["status"] != "ok"
    }
    warning_statuses = {
        item["name"]: item["status"]
        for item in result["details"]["optional"]
        if item["status"] != "ok"
    }

    if not ENV_PATH.exists() or blocker_statuses:
        result["status"] = "blocker"
    elif warning_statuses:
        result["status"] = "warning"

    result["details"]["blockers"] = blocker_statuses
    result["details"]["warnings"] = warning_statuses
    return result


def _check_paths(name: str, paths: list[Path], *, blocker: bool) -> dict:
    missing = [str(path) for path in paths if not path.exists()]
    status = "ok"
    if missing:
        status = "blocker" if blocker else "warning"
    return {
        "name": name,
        "status": status,
        "details": {
            "missing": missing,
            "checked": [str(path) for path in paths],
        },
    }


def _check_dataset() -> dict:
    best_path = find_best_leads_path(FILTERED_DIR)
    return {
        "name": "best_leads_dataset",
        "status": "ok" if best_path else "warning",
        "details": {
            "path": str(best_path) if best_path else None,
        },
    }


def build_report() -> dict:
    checks = [
        _check_runtime(),
        _check_git(),
        _check_gitignore(),
        _check_env(),
        _check_paths("required_scripts", REQUIRED_SCRIPTS, blocker=True),
        _check_paths("required_docs", REQUIRED_DOCS, blocker=True),
        _check_dataset(),
    ]

    blockers = [check["name"] for check in checks if check["status"] == "blocker"]
    warnings = [check["name"] for check in checks if check["status"] == "warning"]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "fail" if blockers else "ok",
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
    }


def main() -> None:
    print_header("Preflight operativo")
    report = build_report()
    out_path = OUTPUT_DIR / "preflight_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Status: {report['status']}")
    print(f"Blockers: {len(report['blockers'])}")
    print(f"Warnings: {len(report['warnings'])}")
    print(f"Reporte: {out_path}")

    if report["blockers"]:
        for item in report["blockers"]:
            print(f"  BLOCKER: {item}")
        sys.exit(1)


if __name__ == "__main__":
    main()
