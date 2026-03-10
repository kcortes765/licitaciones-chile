"""
Smoke pipeline determinista y liviano.

Valida:
  - scoring heuristico
  - score combinado consistente
  - exportes principales
  - validador cliente-safe
"""
from __future__ import annotations

import sys
import tempfile
from importlib import import_module
from pathlib import Path

import pandas as pd

from pipeline_core import (
    build_crm_dataframe,
    contact_coverage_summary,
    recompute_score_combined,
)
from pipeline_validation import (
    assert_client_safe_text,
    assert_dataframe_contract,
    write_run_manifest,
    write_validation_report,
)


def build_smoke_company_df() -> pd.DataFrame:
    return pd.DataFrame({
        "rut": ["76000000-1", "76000000-2", "76000000-3"],
        "nombre": ["Constructora Andina SpA", "Obras Norte Ltda", "Ingenieria Sur SpA"],
        "region": ["Región Metropolitana de Santiago", "Región de Valparaíso", "Región del Biobío"],
        "total_bids": [12, 6, 18],
        "total_wins": [3, 1, 5],
        "win_rate": [0.25, 0.17, 0.28],
        "monto_promedio": [180_000_000, 90_000_000, 350_000_000],
        "monto_total": [2_160_000_000, 540_000_000, 6_300_000_000],
        "monto_adjudicado": [600_000_000, 120_000_000, 1_800_000_000],
        "dias_desde_ultima": [20, 140, 8],
        "n_LP": [5, 1, 10],
        "n_LE": [4, 3, 4],
        "n_L1": [3, 2, 4],
        "competidores_promedio": [7, 9, 6],
        "total_lost": [5, 2, 6],
        "n_distinct_rivals": [3, 2, 4],
        "tipo_mop": ["mayor", None, "mayor"],
        "categoria_mop": ["2da", None, "3ra"],
        "es_persona_natural": [False, False, False],
    })


def main() -> None:
    score_mod = import_module("05_score_leads")
    export_mod = import_module("07_export_output")

    with tempfile.TemporaryDirectory(prefix="lead_smoke_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        output_dir = tmp_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        company_df = build_smoke_company_df()
        scored = score_mod.calculate_scores(company_df.copy())
        scored["km_score"] = [72.0, 45.0, 80.0]
        scored["xgb_score"] = [68.0, 40.0, 75.0]
        scored = recompute_score_combined(scored)
        scored = scored.sort_values("score_combined", ascending=False).reset_index(drop=True)
        scored["rank_ml"] = range(1, len(scored) + 1)
        scored["telefono"] = ["+56911111111", "", "+56933333333"]
        scored["email"] = ["contacto@andina.cl", "", "licitaciones@sur.cl"]
        scored["web"] = ["https://andina.cl", "", "https://sur.cl"]
        scored["contacto_nombre"] = ["Marcela", "", "Patricio"]
        scored["direccion"] = ["Santiago", "", "Concepcion"]

        assert_dataframe_contract(scored, "leads_ml_ranked")

        excel_path = output_dir / "leads_final.xlsx"
        txt_path = output_dir / "mensajes_whatsapp.txt"
        crm_path = output_dir / "crm_leads.xlsx"
        export_mod.export_excel(scored, excel_path)
        export_mod.export_whatsapp(scored, txt_path)
        build_crm_dataframe(scored).to_excel(crm_path, index=False)

        assert_client_safe_text(txt_path.read_text(encoding="utf-8"), txt_path.name)

        report = {
            "contract": "ok",
            "coverage": contact_coverage_summary(scored),
            "outputs": [str(excel_path), str(txt_path), str(crm_path)],
        }
        write_validation_report(output_dir / "smoke_report.json", report)
        write_run_manifest(
            output_dir / "smoke_manifest.json",
            command="python run_smoke_pipeline.py",
            source="deterministic_fixture",
            outputs=[str(excel_path), str(txt_path), str(crm_path)],
            details=report,
        )
        print("Smoke pipeline OK")
        print(report)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE FAILED: {exc}")
        sys.exit(1)

