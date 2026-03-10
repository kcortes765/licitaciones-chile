"""
08 - Análisis de derrotas por empresa.
Para cada top lead, analiza:
  - Cuántas licitaciones perdió vs ganó
  - Contra quién perdió (competidores recurrentes)
  - Patrones de derrota (tipo de licitación, monto, región)
  - Genera insight personalizado para mensaje de venta

Resultado:
  data/output/loss_analysis.parquet  — análisis por empresa
  data/output/mensajes_whatsapp_v2.txt — mensajes con insights de derrotas

Uso:
  python 08_loss_analysis.py             # Top 100
  python 08_loss_analysis.py --top 50    # Top 50
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd

from config import FILTERED_DIR, OUTPUT_DIR
from pipeline_validation import assert_client_safe_text, assert_dataframe_contract, write_run_manifest
from utils import print_header, extraer_rut_de_id


def find_column(df: pd.DataFrame, keywords: list[str]) -> str | None:
    for col in df.columns:
        if any(k in col.lower() for k in keywords):
            return col
    return None


def build_tender_participants(tenderers_df: pd.DataFrame,
                               suppliers_df: pd.DataFrame) -> dict:
    """
    Construye mapa: tender_id -> {tenderers: [ruts], winner: rut}
    Usa _link_main como clave de tender (OCDS tender key).
    """
    print("  Construyendo mapa de participantes por licitación...")

    # Usar _link_main para agrupar por tender
    tender_id_col_t = "_link_main"
    if tender_id_col_t not in tenderers_df.columns:
        tender_id_col_t = find_column(tenderers_df, ["tender_id", "ocid", "release"])
        if tender_id_col_t is None:
            tender_id_col_t = tenderers_df.columns[0]
        print(f"  AVISO: _link_main no encontrado en tenderers, usando {tender_id_col_t}")

    str_cols_t = tenderers_df.select_dtypes(include="object").columns
    tenderers_df["_rut"] = tenderers_df[str_cols_t].apply(
        lambda row: next((r for v in row if (r := extraer_rut_de_id(str(v)))), None),
        axis=1
    )

    # Mapa: tender_id -> lista de oferentes
    tender_map = {}
    for tid, group in tenderers_df[tenderers_df["_rut"].notna()].groupby(tender_id_col_t):
        tender_map[tid] = {
            "tenderers": set(group["_rut"].unique()),
            "winner": None,
            "n_competitors": len(group["_rut"].unique()),
        }

    # Agregar ganadores desde suppliers
    if suppliers_df is not None:
        tender_id_col_s = "_link_main"
        if tender_id_col_s not in suppliers_df.columns:
            tender_id_col_s = find_column(suppliers_df, ["tender_id", "ocid", "release"])
            if tender_id_col_s is None:
                tender_id_col_s = suppliers_df.columns[0]
            print(f"  AVISO: _link_main no encontrado en suppliers, usando {tender_id_col_s}")

        str_cols_s = suppliers_df.select_dtypes(include="object").columns
        suppliers_df["_rut"] = suppliers_df[str_cols_s].apply(
            lambda row: next((r for v in row if (r := extraer_rut_de_id(str(v)))), None),
            axis=1
        )

        for _, row in suppliers_df[suppliers_df["_rut"].notna()].iterrows():
            tid = row[tender_id_col_s]
            if tid in tender_map:
                tender_map[tid]["winner"] = row["_rut"]

    n_with_winner = sum(1 for v in tender_map.values() if v["winner"])
    n_with_losses = sum(1 for v in tender_map.values()
                        if v["winner"] and len(v["tenderers"]) > 1)
    print(f"  Licitaciones mapeadas: {len(tender_map)}")
    print(f"  Con ganador identificado: {n_with_winner}")
    print(f"  Con perdedores identificables: {n_with_losses}")
    return tender_map


def analyze_losses(rut: str, tender_map: dict, rut_to_tenders: dict) -> dict:
    """Analiza derrotas de una empresa específica."""
    participated = []
    won = []
    lost = []
    lost_to = Counter()  # Contra quién perdió

    for tid in rut_to_tenders.get(rut, set()):
        info = tender_map[tid]
        participated.append(tid)
        if info["winner"] == rut:
            won.append(tid)
        elif info["winner"] is not None:
            lost.append(tid)
            lost_to[info["winner"]] += 1

    # Top competidores que le ganan
    top_rivals = lost_to.most_common(5)

    return {
        "total_participated": len(participated),
        "total_won": len(won),
        "total_lost": len(lost),
        "total_unknown": len(participated) - len(won) - len(lost),
        "loss_rate": len(lost) / max(len(participated), 1),
        "top_rival_1": top_rivals[0][0] if len(top_rivals) > 0 else None,
        "top_rival_1_count": top_rivals[0][1] if len(top_rivals) > 0 else 0,
        "top_rival_2": top_rivals[1][0] if len(top_rivals) > 1 else None,
        "top_rival_2_count": top_rivals[1][1] if len(top_rivals) > 1 else 0,
        "n_distinct_rivals": len(lost_to),
    }


def generate_loss_insight(row: pd.Series) -> str:
    """Genera insight de texto basado en análisis de derrotas."""
    lost = row.get("total_lost", 0)
    lost = int(lost) if pd.notna(lost) else 0
    won = row.get("total_won", 0)
    won = int(won) if pd.notna(won) else 0
    total = row.get("total_participated", 0)
    total = int(total) if pd.notna(total) else 0
    rival = row.get("top_rival_1_name", row.get("top_rival_1", ""))
    rival_count = row.get("top_rival_1_count", 0)
    rival_count = int(rival_count) if pd.notna(rival_count) else 0

    if total == 0:
        return ""

    loss_pct = lost / total * 100

    parts = []
    if lost > won and lost >= 3:
        parts.append(f"perdió {lost} de {total} licitaciones ({loss_pct:.0f}%)")
    elif lost > 0:
        parts.append(f"participó en {total} licitaciones, ganó {won}")

    if rival and rival_count >= 2:
        parts.append(f"su competidor más frecuente ({rival}) le ganó {rival_count} veces")

    return ". ".join(parts)


WHATSAPP_V2_TEMPLATE = """Hola {contacto}, soy Sebastián Cortés de IngenIA Licitaciones.

{insight_derrota}

Ofrezco análisis estratégico con IA para licitaciones de construcción:
- Detección de requisitos críticos ocultos en las bases
- Análisis de competidores y estrategia de precios
- Evaluación de riesgos antes de ofertar

{cierre_personalizado}

Sebastián Cortés
Ing. Civil UCN | IngenIA Licitaciones
"""


def generate_whatsapp_v2(row: pd.Series) -> str:
    """Genera mensaje WhatsApp potenciado con insights de derrotas."""
    contacto = row.get("contacto_nombre", "")
    if pd.isna(contacto) or not contacto:
        contacto = "estimado/a"

    empresa = row.get("nombre", "")
    if pd.isna(empresa) or not empresa:
        empresa = "su empresa"

    lost = row.get("total_lost", 0)
    lost = int(lost) if pd.notna(lost) else 0
    won = row.get("total_won", 0)
    won = int(won) if pd.notna(won) else 0
    total = row.get("total_participated", 0)
    total = int(total) if pd.notna(total) else 0
    rival_name = row.get("top_rival_1_name", "")
    rival_count = row.get("top_rival_1_count", 0)
    rival_count = int(rival_count) if pd.notna(rival_count) else 0

    # Insight personalizado según el caso
    if lost >= 3 and lost > won:
        insight = (f"Analicé los datos públicos de licitaciones y vi que {empresa} "
                   f"participó en {total} licitaciones recientes de construcción, "
                   f"adjudicándose {won}.")
        if pd.notna(rival_name) and rival_count >= 2:
            insight += (f" Noté que {rival_name} les ha ganado en {rival_count} ocasiones"
                        f" — justo ese tipo de patrón es lo que nuestro análisis ayuda a revertir.")
    elif won == 0 and total >= 2:
        insight = (f"Vi que {empresa} ha postulado a {total} licitaciones de construcción "
                   f"recientemente sin adjudicarse aún. Nuestro servicio está diseñado "
                   f"exactamente para eso — identificar por qué se pierde y cómo ganar.")
    elif total >= 5:
        win_pct = won / total * 100
        insight = (f"Analicé los datos de {empresa} en licitaciones de construcción: "
                   f"{total} participaciones, {won} adjudicaciones ({win_pct:.0f}%). "
                   f"Nuestro análisis con IA puede ayudar a subir esa tasa.")
    else:
        insight = (f"Vi que {empresa} participa en licitaciones de construcción. "
                   f"Ofrezco un servicio de análisis estratégico con IA que ayuda "
                   f"a constructoras a ganar más licitaciones.")

    # Cierre
    if lost > won:
        cierre = "¿Les interesaría una demo gratuita? Puedo analizar una licitación que hayan perdido y mostrarles qué habría cambiado."
    else:
        cierre = "¿Les interesaría una demo gratuita con una licitación actual suya? Solo necesito el código."

    return WHATSAPP_V2_TEMPLATE.format(
        contacto=contacto,
        insight_derrota=insight,
        cierre_personalizado=cierre,
    ).strip()


def main():
    print_header("08 — Análisis de Derrotas por Empresa")

    top_n = 100
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 >= len(sys.argv):
            print("ERROR: --top requiere un valor numérico")
            sys.exit(1)
        try:
            top_n = int(sys.argv[idx + 1])
        except ValueError:
            print(f"ERROR: --top requiere un número, se recibió '{sys.argv[idx + 1]}'")
            sys.exit(1)

    # Cargar datos
    tenderers_path = FILTERED_DIR / "tenderers_construction.parquet"
    suppliers_path = FILTERED_DIR / "suppliers_construction.parquet"

    # Cargar leads (preferir enriched > ML ranked > heurístico)
    leads_path = FILTERED_DIR / "leads_enriched.parquet"
    if not leads_path.exists():
        leads_path = FILTERED_DIR / "leads_ml_ranked.parquet"
    if not leads_path.exists():
        leads_path = FILTERED_DIR / "leads_ranked.parquet"
    if not leads_path.exists():
        print("ERROR: No hay leads rankeados")
        print("Ejecuta primero: python 05_score_leads.py")
        sys.exit(1)

    if not tenderers_path.exists():
        print("ERROR: No hay tenderers filtrados")
        sys.exit(1)

    leads = pd.read_parquet(leads_path).head(top_n)
    tenderers = pd.read_parquet(tenderers_path)
    suppliers = pd.read_parquet(suppliers_path) if suppliers_path.exists() else None

    print(f"Leads a analizar: {len(leads)}")

    # Construir mapa de participantes
    tender_map = build_tender_participants(tenderers, suppliers)

    # Pre-construir índice inverso rut -> tenders para O(1) lookup
    rut_to_tenders = defaultdict(set)
    for tid, info in tender_map.items():
        for rut in info.get("tenderers", set()):
            rut_to_tenders[rut].add(tid)

    # Analizar cada lead
    print(f"\n--- Analizando derrotas ---")
    analyses = []
    for _, row in leads.iterrows():
        rut = row["rut"]
        analysis = analyze_losses(rut, tender_map, rut_to_tenders)
        analysis["rut"] = rut
        analyses.append(analysis)

    analysis_df = pd.DataFrame(analyses)

    # Merge con leads
    leads = leads.merge(analysis_df, on="rut", how="left", suffixes=("", "_loss"))

    # Rellenar NaN en columnas numéricas del merge
    numeric_fill_cols = ["total_participated", "total_won", "total_lost", "total_unknown",
                         "loss_rate", "top_rival_1_count", "top_rival_2_count", "n_distinct_rivals"]
    for col in numeric_fill_cols:
        if col in leads.columns:
            leads[col] = leads[col].fillna(0)

    # Resolver nombres de rivales
    # Buscar nombres en parties o company_database
    parties_path = FILTERED_DIR / "parties_construction.parquet"
    rut_to_name = {}
    if parties_path.exists():
        parties = pd.read_parquet(parties_path)
        name_col = find_column(parties, ["name", "nombre"])
        if name_col:
            str_cols_p = parties.select_dtypes(include="object").columns
            parties["_rut"] = parties[str_cols_p].apply(
                lambda row: next((r for v in row if (r := extraer_rut_de_id(str(v)))), None),
                axis=1
            )
            for _, p in parties[parties["_rut"].notna()].iterrows():
                rut_to_name[p["_rut"]] = p[name_col]

    leads["top_rival_1_name"] = leads["top_rival_1"].map(rut_to_name)
    leads["top_rival_2_name"] = leads["top_rival_2"].map(rut_to_name)
    leads["loss_insight"] = leads.apply(generate_loss_insight, axis=1)

    # Guardar análisis
    out_path = OUTPUT_DIR / "loss_analysis.parquet"
    assert_dataframe_contract(leads, "loss_analysis")
    leads.to_parquet(out_path, index=False)

    # Generar mensajes WhatsApp v2
    wa_path = OUTPUT_DIR / "mensajes_whatsapp_v2.txt"
    with open(wa_path, "w", encoding="utf-8") as f:
        f.write(f"# Mensajes WhatsApp V2 (con análisis de derrotas)\n")
        f.write(f"# Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# Total: {len(leads)} leads\n")
        f.write("=" * 60 + "\n\n")

        for _, row in leads.iterrows():
            rank = row.get("rank", row.get("rank_ml", "?"))
            rank = rank if pd.notna(rank) else "?"
            nombre = row.get("nombre")
            if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
                nombre = row.get("rut")
            if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
                nombre = "?"
            telefono = row.get("telefono", "Sin teléfono")
            lost = row.get("total_lost", 0)
            lost = lost if pd.notna(lost) else 0
            won = row.get("total_won", 0)
            won = won if pd.notna(won) else 0

            f.write(f"--- Lead #{rank} | "
                    f"Won: {int(won)} Lost: {int(lost)} | {nombre} ---\n")
            if pd.notna(telefono) and telefono:
                f.write(f"Teléfono: {telefono}\n")
            else:
                f.write(f"Teléfono: Sin teléfono\n")
            if pd.notna(row.get("email")):
                f.write(f"Email: {row['email']}\n")
            if pd.notna(row.get("loss_insight")) and row.get("loss_insight"):
                f.write(f"Insight: {row['loss_insight']}\n")
            f.write(f"\n")

            msg = generate_whatsapp_v2(row)
            f.write(msg + "\n\n")
            f.write("=" * 60 + "\n\n")
    assert_client_safe_text(wa_path.read_text(encoding="utf-8"), wa_path.name)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  ANÁLISIS DE DERROTAS")
    print(f"{'='*60}")
    print(f"  Leads analizados: {len(leads)}")
    print(f"  Con derrotas identificadas: {(leads['total_lost'] > 0).sum()}")
    print(f"  Con rival recurrente: {(leads['top_rival_1_count'] >= 2).sum()}")

    # Top leads por oportunidad (muchas derrotas = más necesitan ayuda)
    high_loss = leads[leads["total_lost"] >= 3].sort_values("total_lost", ascending=False)
    if len(high_loss) > 0:
        print(f"\n  Top leads por oportunidad (más derrotas):")
        print(f"  {'Empresa':30s} {'Perdió':>7} {'Ganó':>5} {'Rival principal'}")
        print(f"  {'-'*70}")
        for _, row in high_loss.head(10).iterrows():
            nombre_val = row.get("nombre")
            nombre = str(nombre_val if pd.notna(nombre_val) else row.get("rut", "?"))[:28]
            rival_val = row.get("top_rival_1_name")
            if not pd.notna(rival_val):
                rival_val = row.get("top_rival_1")
            rival = str(rival_val if pd.notna(rival_val) else "?")[:20]
            t_lost = row['total_lost'] if pd.notna(row['total_lost']) else 0
            t_won = row['total_won'] if pd.notna(row['total_won']) else 0
            print(f"  {nombre:30s} {t_lost:>7.0f} "
                  f"{t_won:>5.0f} {rival}")

    print(f"\n  Archivos generados:")
    print(f"    {out_path}")
    print(f"    {wa_path}")
    write_run_manifest(
        OUTPUT_DIR / "loss_analysis_manifest.json",
        command="python 08_loss_analysis.py",
        source=leads_path.name,
        outputs=[str(out_path), str(wa_path)],
        details={"top_n": top_n, "rows": len(leads)},
    )


if __name__ == "__main__":
    main()
