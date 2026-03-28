"""
07 - Exporta resultados finales: Excel + CSV + mensajes WhatsApp.

Resultado:
  data/output/leads_final.xlsx       — Excel con formato, listo para revisar
  data/output/leads_final.csv        — CSV para importar
  data/output/mensajes_whatsapp.txt  — Mensajes listos para copiar y pegar

Uso:
  python 07_export_output.py
"""
from __future__ import annotations

import sys
from datetime import datetime

import pandas as pd

from config import FILTERED_DIR, OUTPUT_DIR
from pipeline_core import build_crm_dataframe, contact_coverage_summary, load_best_leads_dataframe
from pipeline_validation import (
    assert_client_safe_text,
    assert_dataframe_contract,
    write_run_manifest,
    write_validation_report,
)
from utils import print_header, formato_clp


WHATSAPP_TEMPLATE = """Hola {contacto}, soy Sebastián Cortés de IngenIA Licitaciones.

Vi que {empresa} ha participado en {n_bids} licitaciones de construcción recientes{detalle_licitacion}. Ofrezco un servicio de análisis estratégico con IA que ayuda a constructoras como la suya a:

- Detectar requisitos críticos en las bases (multas, garantías, plazos)
- Identificar riesgos ocultos antes de ofertar
- Optimizar la estrategia de precios

¿Les interesaría una demo gratuita con una licitación real suya? Solo necesito el código de la licitación.

Sebastián Cortés
Ing. Civil UCN | IngenIA Licitaciones
"""


def generate_whatsapp_message(row: pd.Series) -> str:
    """Genera mensaje WhatsApp personalizado para un lead."""
    contacto = row.get("contacto_nombre", "")
    if pd.isna(contacto) or not contacto:
        contacto = "estimado/a"

    empresa = row.get("nombre", "")
    if pd.isna(empresa) or not empresa:
        empresa = "su empresa"

    n_bids_raw = row.get("total_bids", 0)
    n_bids = int(n_bids_raw) if pd.notna(n_bids_raw) else 0
    win_rate = row.get("win_rate", 0)
    win_rate = win_rate if pd.notna(win_rate) else 0

    # Detalle personalizado según datos
    detalle = ""
    n_lp = row.get("n_LP", 0)
    if pd.notna(n_lp) and n_lp > 0:
        detalle = f", incluyendo {int(n_lp)} de tipo LP (>$66M)"

    if pd.notna(win_rate) and win_rate > 0:
        pct = f"{win_rate:.0%}"
        if win_rate < 0.25:
            detalle += f". Noté que su tasa de adjudicación es {pct} — justamente ahí es donde más impacto tiene nuestro análisis"
        elif win_rate < 0.40:
            detalle += f", con una tasa de adjudicación de {pct}"

    msg = WHATSAPP_TEMPLATE.format(
        contacto=contacto,
        empresa=empresa,
        n_bids=n_bids,
        detalle_licitacion=detalle,
    )

    return msg.strip()


def export_excel(df: pd.DataFrame, path):
    """Exporta Excel con formato profesional."""
    # Seleccionar y ordenar columnas para el Excel
    # Elegir columna de rank y score (preferir ML si existe)
    rank_col = "rank_ml" if "rank_ml" in df.columns else "rank"
    score_col_name = "score_combined" if "score_combined" in df.columns else "score_total"

    excel_cols = {
        rank_col: "#",
        score_col_name: "Score",
        "nombre": "Empresa",
        "rut": "RUT",
        "region": "Región",
        "total_bids": "Licitaciones",
        "total_wins": "Adjudicadas",
        "win_rate": "Win Rate",
        "monto_promedio": "Monto Prom.",
        "n_LP": "# LP",
        "n_LE": "# LE",
        "dias_desde_ultima": "Días Inactivo",
        "competidores_promedio": "Competidores Prom.",
        "tipo_mop": "Tipo MOP",
        "categoria_mop": "Categoría MOP",
        "telefono": "Teléfono",
        "email": "Email",
        "web": "Web",
        "contacto_nombre": "Contacto",
        "direccion": "Dirección",
    }

    # Solo incluir columnas que existen
    cols_exist = {k: v for k, v in excel_cols.items() if k in df.columns}
    export_df = df[list(cols_exist.keys())].rename(columns=cols_exist)

    # Formatear
    if "Win Rate" in export_df.columns:
        export_df["Win Rate"] = export_df["Win Rate"].apply(
            lambda x: f"{x:.0%}" if pd.notna(x) else ""
        )
    if "Monto Prom." in export_df.columns:
        export_df["Monto Prom."] = export_df["Monto Prom."].apply(
            lambda x: formato_clp(x) if pd.notna(x) else ""
        )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        export_df.to_excel(writer, sheet_name="Leads", index=False)

        # Ajustar ancho de columnas
        from openpyxl.utils import get_column_letter
        ws = writer.sheets["Leads"]
        for i, col in enumerate(export_df.columns, 1):
            col_max = export_df[col].astype(str).str.len().max()
            max_len = max(col_max if pd.notna(col_max) else 0, len(col)) + 2
            max_len = min(max_len, 40)
            ws.column_dimensions[get_column_letter(i)].width = max_len

        # Agregar hoja de resumen
        score_col = "score_combined" if "score_combined" in df.columns else "score_total"
        summary_data = {
            "Métrica": [
                "Total leads",
                "Score promedio",
                "Con teléfono",
                "Con email",
                "Con web",
                "En registro MOP",
                "Fecha generación",
            ],
            "Valor": [
                len(df),
                f"{df[score_col].mean():.1f}" if score_col in df.columns and pd.notna(df[score_col].mean()) else "N/A",
                df["telefono"].notna().sum() if "telefono" in df.columns else "N/A",
                df["email"].notna().sum() if "email" in df.columns else "N/A",
                df["web"].notna().sum() if "web" in df.columns else "N/A",
                df["tipo_mop"].notna().sum() if "tipo_mop" in df.columns else "N/A",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Resumen", index=False)

    print(f"  Excel guardado: {path}")


def export_whatsapp(df: pd.DataFrame, path):
    """Genera archivo con mensajes WhatsApp listos."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Mensajes WhatsApp — Generado {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# Total leads: {len(df)}\n")
        f.write(f"# Copiar y pegar cada mensaje en WhatsApp\n")
        f.write("=" * 60 + "\n\n")

        for _, row in df.iterrows():
            rank = row.get("rank_ml", row.get("rank", "?"))
            rank = rank if pd.notna(rank) else "?"
            nombre = row.get("nombre")
            if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
                nombre = row.get("rut")
            if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
                nombre = "?"
            telefono = row.get("telefono", "Sin teléfono")

            f.write(f"--- Lead #{rank} | {nombre} ---\n")
            if pd.notna(telefono) and telefono:
                f.write(f"Teléfono: {telefono}\n")
            else:
                f.write(f"Teléfono: Sin teléfono\n")
            if pd.notna(row.get("email")):
                f.write(f"Email: {row['email']}\n")
            f.write(f"\n")

            msg = generate_whatsapp_message(row)
            f.write(msg + "\n\n")
            f.write("=" * 60 + "\n\n")

    print(f"  WhatsApp guardado: {path}")


def main():
    print_header("07 — Exportar Resultados Finales")

    # Buscar mejor fuente disponible (preferir enriquecido > ML > heurístico)
    try:
        df, source_path = load_best_leads_dataframe()
    except FileNotFoundError:
        print("ERROR: No hay leads para exportar")
        print("Ejecuta primero: python 05_score_leads.py")
        sys.exit(1)

    print(f"Cargando {source_path.name}: {len(df)} leads")
    if "score_combined" in df.columns:
        assert_dataframe_contract(df, "leads_enriched" if "telefono" in df.columns else "leads_ml_ranked")
    else:
        assert_dataframe_contract(df, "leads_ranked")

    # Exportar Excel
    excel_path = OUTPUT_DIR / "leads_final.xlsx"
    export_excel(df, excel_path)

    # Exportar CSV (solo columnas cliente-safe, sin scores internos)
    csv_path = OUTPUT_DIR / "leads_final.csv"
    csv_safe_cols = [
        "nombre", "rut", "region", "total_bids", "total_wins", "win_rate",
        "monto_promedio", "n_LP", "n_LE", "dias_desde_ultima",
        "competidores_promedio", "tipo_mop", "categoria_mop",
        "telefono", "email", "web", "contacto_nombre", "direccion",
    ]
    csv_cols = [c for c in csv_safe_cols if c in df.columns]
    df[csv_cols].to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  CSV guardado: {csv_path}")

    # Exportar mensajes WhatsApp (top 50 con teléfono o todos los top 50)
    whatsapp_df = df.head(50)
    wa_path = OUTPUT_DIR / "mensajes_whatsapp.txt"
    export_whatsapp(whatsapp_df, wa_path)
    assert_client_safe_text(wa_path.read_text(encoding="utf-8"), wa_path.name)

    crm_df = build_crm_dataframe(df.head(100))
    crm_xlsx = OUTPUT_DIR / "crm_leads.xlsx"
    crm_csv = OUTPUT_DIR / "crm_leads.csv"
    crm_df.to_excel(crm_xlsx, index=False)
    crm_df.to_csv(crm_csv, index=False, encoding="utf-8-sig")
    print(f"  CRM guardado: {crm_xlsx}")

    coverage = contact_coverage_summary(df)
    write_validation_report(OUTPUT_DIR / "coverage_report.json", coverage)
    write_run_manifest(
        OUTPUT_DIR / "export_manifest.json",
        command="python 07_export_output.py",
        source=source_path.name,
        outputs=[str(excel_path), str(csv_path), str(wa_path), str(crm_xlsx), str(crm_csv)],
        details={"coverage": coverage, "rows": len(df)},
    )

    # Resumen final
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETADO")
    print(f"{'='*60}")
    print(f"  Archivos generados:")
    print(f"    {excel_path}")
    print(f"    {csv_path}")
    print(f"    {wa_path}")
    print(f"    {crm_xlsx}")
    print(f"\n  Total leads: {len(df)}")
    score_col = "score_combined" if "score_combined" in df.columns else "score_total"
    if score_col in df.columns:
        sc_min = df[score_col].min()
        sc_max = df[score_col].max()
        if pd.notna(sc_min) and pd.notna(sc_max):
            print(f"  Score rango: {sc_min:.1f} - {sc_max:.1f}")

    if "telefono" in df.columns:
        con_tel = df["telefono"].notna().sum()
        print(f"  Con teléfono: {con_tel}")

    print(f"\n  Próximos pasos:")
    print(f"  1. Revisar leads_final.xlsx — validar top 20 manualmente")
    print(f"  2. Buscar top 5 en Google para confirmar que son constructoras reales")
    print(f"  3. Copiar mensajes de mensajes_whatsapp.txt y enviar")


if __name__ == "__main__":
    main()
