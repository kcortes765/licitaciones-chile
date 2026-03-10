"""
Monitor diario formal.

Genera:
  - monitor_diario.md
  - matches.csv
  - alertas_contacto.txt
  - crm_leads.csv/xlsx actualizado desde los matches del dia
"""
from __future__ import annotations

from datetime import datetime
from importlib import import_module
from pathlib import Path

import pandas as pd

from config import OUTPUT_DIR
from pipeline_core import build_crm_dataframe, load_best_leads_dataframe
from pipeline_validation import write_run_manifest, write_validation_report
from utils import print_header


def main() -> None:
    print_header("12 - Monitor API Diario")

    matcher = import_module("09_tender_matcher")
    leads, source_path = load_best_leads_dataframe()
    leads = leads.head(200).copy()

    tenders = matcher.get_rss_tenders()
    tenders.extend([
        tender for tender in matcher.get_api_tenders(days=3)
        if tender.get("codigo") not in {rss.get("codigo") for rss in tenders}
    ])
    matches = matcher.match_tenders_to_leads(tenders, leads)

    md_path = OUTPUT_DIR / "monitor_diario.md"
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_dataset": source_path.name,
        "tenders": len(tenders),
        "matches": len(matches),
        "unique_leads": int(matches["lead_rut"].nunique()) if len(matches) else 0,
    }
    lines = [
        "# Monitor diario",
        "",
        f"- Dataset fuente: `{source_path.name}`",
        f"- Licitaciones analizadas: `{report['tenders']}`",
        f"- Matches encontrados: `{report['matches']}`",
        f"- Leads unicos: `{report['unique_leads']}`",
        "",
    ]

    outputs = [str(md_path)]
    if len(matches):
        matches_path = OUTPUT_DIR / "matches.csv"
        matches.to_csv(matches_path, index=False, encoding="utf-8-sig")
        outputs.append(str(matches_path))
        crm = build_crm_dataframe(
            matches.rename(columns={
                "lead_nombre": "nombre",
                "lead_rut": "rut",
                "lead_telefono": "telefono",
            }),
            default_channel="WhatsApp",
        )
        crm["licitacion_codigo"] = matches["tender_codigo"]
        crm["licitacion_nombre"] = matches["tender_nombre"]
        crm["estado"] = "Monitoreado"
        crm_csv = OUTPUT_DIR / "crm_leads.csv"
        crm_xlsx = OUTPUT_DIR / "crm_leads.xlsx"
        crm.to_csv(crm_csv, index=False, encoding="utf-8-sig")
        crm.to_excel(crm_xlsx, index=False)
        outputs.extend([str(crm_csv), str(crm_xlsx)])

        lines.extend(["## Top matches", ""])
        for _, row in matches.head(10).iterrows():
            lines.append(
                f"- `{row['tender_codigo']}` -> `{row['lead_nombre']}` "
                f"({int(row['match_score'])} pts, {row['match_reasons']})"
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_validation_report(OUTPUT_DIR / "monitor_report.json", report)
    write_run_manifest(
        OUTPUT_DIR / "monitor_manifest.json",
        command="python 12_monitor_api.py",
        source=source_path.name,
        outputs=outputs,
        details=report,
    )

    print(f"Monitor diario generado: {md_path}")


if __name__ == "__main__":
    main()

