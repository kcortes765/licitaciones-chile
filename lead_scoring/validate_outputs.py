"""
Valida entorno y artefactos cliente-safe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from config import OUTPUT_DIR, env_var_report
from pipeline_validation import (
    assert_client_safe_binary,
    assert_client_safe_json,
    assert_client_safe_text,
    write_validation_report,
)
from utils import print_header


def _check_env() -> dict:
    report = {"env": "ok", "checks": []}
    for context, vars_ in [
        ("Google Places", ["GOOGLE_MAPS_API_KEY"]),
        ("Mercado Publico", ["MERCADO_PUBLICO_TICKET"]),
        ("Apify fallback", ["APIFY_TOKEN"]),
    ]:
        vars_report = env_var_report(vars_)
        statuses = {item["status"] for item in vars_report}
        if "missing" in statuses or "placeholder" in statuses:
            report["env"] = "warning"
        report["checks"].append({"context": context, "vars": vars_report})
    return report


def main() -> None:
    print_header("Validacion de outputs")
    report = {"checks": []}

    if "--check-env" in sys.argv:
        env_report = _check_env()
        write_validation_report(OUTPUT_DIR / "env_validation.json", env_report)
        print(json.dumps(env_report, indent=2, ensure_ascii=False))
        return

    text_candidates = [
        OUTPUT_DIR / "mensajes_whatsapp.txt",
        OUTPUT_DIR / "mensajes_whatsapp_v2.txt",
        OUTPUT_DIR / "alertas_contacto.txt",
    ]
    for path in text_candidates:
        if path.exists():
            assert_client_safe_text(path.read_text(encoding="utf-8"), path.name)
            report["checks"].append({"artifact": path.name, "status": "ok"})

    for path in sorted((OUTPUT_DIR / "diagnosticos").glob("*_notas.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert_client_safe_json(payload, path.name)
        report["checks"].append({"artifact": path.name, "status": "ok"})

    for path in sorted((OUTPUT_DIR / "diagnosticos").glob("*.pdf")):
        assert_client_safe_binary(path)
        report["checks"].append({"artifact": path.name, "status": "ok"})

    out_path = OUTPUT_DIR / "validation_report.json"
    write_validation_report(out_path, report)
    print(f"Validacion completada: {out_path}")


if __name__ == "__main__":
    main()
