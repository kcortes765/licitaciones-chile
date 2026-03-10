"""
Runner del pipeline completo de lead scoring.
Ejecuta los 11 pasos batch en orden.

Uso:
  python run_pipeline.py           # Pipeline completo
  python run_pipeline.py --from 3  # Desde el paso 3
  python run_pipeline.py --only 5  # Solo un paso
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

STEPS = [
    ("01_download_bulk.py", "Descarga bulk CSV"),
    ("02_scrape_mop.py", "Scraping contratistas MOP"),
    ("03_filter_construction.py", "Filtrar construcción"),
    ("04_build_company_db.py", "Base de datos de empresas"),
    ("05_score_leads.py", "Scoring heurístico"),
    ("05b_ml_scoring.py", "ML Scoring (XGBoost + K-Means)"),
    ("06_enrich_contacts.py", "Enriquecimiento de contactos"),
    ("07_export_output.py", "Exportar resultados"),
    ("08_loss_analysis.py", "Análisis de derrotas"),
    ("09_tender_matcher.py", "Match licitaciones -> leads"),
    ("10_visualizations.py", "Visualizaciones (27 gráficos)"),
]


def main():
    start_from = 1
    only = None

    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        if idx + 1 >= len(sys.argv):
            print("Error: --from requiere un número de paso")
            sys.exit(1)
        try:
            start_from = int(sys.argv[idx + 1])
        except ValueError:
            print(f"Error: --from requiere un número, se recibió '{sys.argv[idx + 1]}'")
            sys.exit(1)

    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 >= len(sys.argv):
            print("Error: --only requiere un número de paso")
            sys.exit(1)
        try:
            only = int(sys.argv[idx + 1])
        except ValueError:
            print(f"Error: --only requiere un número, se recibió '{sys.argv[idx + 1]}'")
            sys.exit(1)

    if start_from > 1 and only:
        print("AVISO: --from y --only no se pueden usar juntos")
        sys.exit(1)

    if start_from < 1 or start_from > len(STEPS):
        print(f"Error: --from debe estar entre 1 y {len(STEPS)}")
        sys.exit(1)

    if only is not None and (only < 1 or only > len(STEPS)):
        print(f"Error: --only debe estar entre 1 y {len(STEPS)}")
        sys.exit(1)

    # Pasar args extra a los scripts
    extra_args = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--from", "--only"):
            i += 2  # skip these, they're for run_pipeline only
            continue
        if arg.startswith("--"):
            extra_args.append(arg)
            # If next arg exists and is not a flag, it's the value
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                extra_args.append(sys.argv[i + 1])
                i += 2
                continue
        i += 1

    print("=" * 60)
    print("  PIPELINE DE LEAD SCORING — LICITACIONES CHILE")
    print("=" * 60)

    for i, (script, desc) in enumerate(STEPS, 1):
        if only and i != only:
            continue
        if i < start_from:
            continue

        print(f"\n{'='*60}")
        print(f"  PASO {i}/{len(STEPS)}: {desc}")
        print(f"{'='*60}")

        t0 = time.time()
        result = subprocess.run(
            [sys.executable, script] + extra_args,
            cwd=str(Path(__file__).parent),
        )

        elapsed = time.time() - t0
        status = "OK" if result.returncode == 0 else "ERROR"
        print(f"\n  [{status}] Paso {i} completado en {elapsed:.0f}s")

        if result.returncode != 0:
            print(f"\n  Pipeline detenido en paso {i}.")
            print(f"  Corregir el error y reiniciar con: python run_pipeline.py --from {i}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETADO EXITOSAMENTE")
    print(f"{'='*60}")
    print(f"  Resultados en: lead_scoring/data/output/")
    print(f"  - leads_final.xlsx          (Excel con ranking)")
    print(f"  - leads_final.csv           (CSV importable)")
    print(f"  - crm_leads.xlsx            (CRM mÃ­nimo para seguimiento)")
    print(f"  - mensajes_whatsapp.txt     (mensajes básicos)")
    print(f"  - mensajes_whatsapp_v2.txt  (con análisis de derrotas)")
    print(f"  - matches.csv               (matches licitacion->lead)")
    print(f"  - coverage_report.json      (cobertura de contactos)")
    print(f"  - *_manifest.json           (trazabilidad por corrida)")
    print(f"  - alertas_contacto.txt      (a quién contactar ahora)")
    print(f"  - graficos/                 (27 gráficos nivel tesis)")


if __name__ == "__main__":
    main()
