"""
09 - Tender Matcher: cruza licitaciones nuevas con top leads.
Cuando sale una licitación de construcción nueva, identifica cuáles
de tus top leads probablemente van a participar -> contactar AHORA.

Funciona de 2 formas:
  1. Batch: analiza licitaciones recientes vs top leads
  2. Monitor: revisa periódicamente y genera alertas

Resultado:
  data/output/matches.csv          — matches lead + licitación
  data/output/alertas_contacto.txt — alertas de "contacta ahora"

Uso:
  python 09_tender_matcher.py                    # Batch con RSS
  python 09_tender_matcher.py --days 7           # Últimos 7 días
  python 09_tender_matcher.py --tender 2405-31-LP26  # Match 1 licitación
"""
from __future__ import annotations

import sys
import re
import time
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pandas as pd
from config import (FILTERED_DIR, OUTPUT_DIR, OCDS_TENDER_URL,
                    MERCADO_PUBLICO_TICKET)
from pipeline_core import load_best_leads_dataframe
from pipeline_validation import assert_dataframe_contract, write_run_manifest
from utils import print_header, safe_request, extraer_rut_de_id

RSS_URL = "https://www.mercadopublico.cl/Portal/feedrelevant.aspx"

# Keywords de construcción (del monitor original)
KW_INCLUIR = [
    'construcci', 'obra', 'infraestructura', 'paviment', 'vialidad', 'puente',
    'edifici', 'mejoramiento', 'reposici', 'conservaci', 'habilitaci',
    'demolici', 'estructur', 'arquitect', 'urbanizaci', 'alcantarillado',
    'agua potable', 'saneamiento',
]
KW_EXCLUIR = [
    'vehicul', 'neumatic', 'dental', 'medic', 'telefon', 'azure', 'internet',
    'kinesiol', 'reactivo', 'cocina', 'compresor', 'seguro de', 'limpieza',
    'impresora', 'software', 'consultor',
]


def es_construccion(texto: str) -> bool:
    """Verifica si un texto corresponde a obra de construcción."""
    t = texto.lower()
    if not any(kw in t for kw in KW_INCLUIR):
        return False
    if any(ex in t for ex in KW_EXCLUIR):
        return False
    return True


def get_rss_tenders() -> list[dict]:
    """Obtiene licitaciones recientes del RSS feed (>1000 UTM)."""
    print("  Consultando RSS de licitaciones destacadas...")

    resp = safe_request(RSS_URL, max_retries=2)
    if not resp:
        print("  AVISO: No se pudo acceder al RSS")
        return []

    tenders = []
    try:
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        print(f"  RSS: {len(items)} licitaciones totales")

        for item in items:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")

            if es_construccion(title + " " + desc):
                # Extraer código de la URL o título
                code_match = re.search(r"(\d{2,6}-\d{1,3}-[A-Z]{2}\d{2})", title + " " + link)
                code = code_match.group(1) if code_match else ""

                tenders.append({
                    "codigo": code,
                    "nombre": title,
                    "descripcion": desc,
                    "url": link,
                })

        print(f"  Construcción: {len(tenders)} licitaciones")
    except ET.ParseError as e:
        print(f"  Error parsing RSS: {e}")

    return tenders


def get_api_tenders(days: int = 3) -> list[dict]:
    """Obtiene licitaciones recientes de la API clásica."""
    if not MERCADO_PUBLICO_TICKET:
        return []

    print(f"  Consultando API MercadoPublico (últimos {days} días)...")
    tenders = []
    base = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"

    for i in range(days):
        fecha = (datetime.now() - timedelta(days=i)).strftime("%d%m%Y")
        url = f"{base}?fecha={fecha}&ticket={MERCADO_PUBLICO_TICKET}"
        resp = safe_request(url, max_retries=2, delay=3)

        if not resp:
            continue

        try:
            data = resp.json()
            if "Codigo" in data and str(data["Codigo"]) == "10500":
                print(f"    Rate limit en fecha {fecha}")
                time.sleep(5)
                continue

            for lic in data.get("Listado", []):
                nombre = lic.get("Nombre", "")
                if es_construccion(nombre) and str(lic.get("CodigoEstado", "")) == "5":
                    tenders.append({
                        "codigo": lic.get("CodigoExterno", ""),
                        "nombre": nombre,
                        "descripcion": lic.get("Descripcion", "")[:200],
                        "cierre": lic.get("FechaCierre", ""),
                        "organismo": lic.get("Comprador", {}).get("NombreOrganismo", ""),
                        "region": lic.get("Comprador", {}).get("RegionUnidad", ""),
                    })
        except json.JSONDecodeError:
            pass

        time.sleep(2)

    print(f"  API: {len(tenders)} licitaciones de construcción abiertas")
    return tenders


def get_tender_participants_ocds(codigo: str) -> list[str]:
    """Obtiene participantes de una licitación via OCDS API."""
    url = OCDS_TENDER_URL.format(codigo=codigo)
    resp = safe_request(url, max_retries=2, delay=1)

    if not resp:
        return []

    try:
        data = resp.json()
        ruts = []
        releases = data.get("releases", [data]) if isinstance(data, dict) else []
        for release in releases:
            for party in release.get("parties", []):
                rut = extraer_rut_de_id(str(party.get("id", "")))
                if rut:
                    ruts.append(rut)
            # También en tender.tenderers
            for tenderer in release.get("tender", {}).get("tenderers", []):
                rut = extraer_rut_de_id(str(tenderer.get("id", "")))
                if rut:
                    ruts.append(rut)
        return list(set(ruts))
    except (json.JSONDecodeError, KeyError):
        return []


def match_tenders_to_leads(tenders: list[dict], leads_df: pd.DataFrame) -> pd.DataFrame:
    """
    Match: para cada licitación nueva, busca leads que probablemente participen.
    Criterios:
    1. Lead participó en licitaciones similares antes (misma región/tipo)
    2. Lead compite contra empresas que ya están en esta licitación
    3. Lead está activo recientemente
    """
    print(f"\n--- Matching {len(tenders)} licitaciones con {len(leads_df)} leads ---")

    matches = []

    for tender in tenders:
        codigo = tender.get("codigo", "")
        nombre = tender.get("nombre", "")
        region_tender = tender.get("region", "")

        # Obtener participantes actuales via OCDS (si la licitación ya tiene)
        if codigo:
            current_participants = get_tender_participants_ocds(codigo)
            time.sleep(0.5)
        else:
            current_participants = []

        for _, lead in leads_df.iterrows():
            rut = lead["rut"]
            score = 0
            reasons = []

            # 1. ¿Ya está participando?
            if rut in current_participants:
                score += 50
                reasons.append("ya participa")

            # 2. ¿Compite contra alguien que está participando?
            rival_1 = lead.get("top_rival_1")
            if pd.notna(rival_1) and rival_1 in current_participants:
                score += 30
                reasons.append(f"su rival {rival_1} ya participa")

            # 3. ¿Misma región?
            lead_region = str(lead.get("region", ""))
            if region_tender and lead_region and (
                region_tender.lower() in lead_region.lower() or
                lead_region.lower() in region_tender.lower()
            ):
                score += 15
                reasons.append("misma región")

            # 4. ¿Activo recientemente?
            dias = lead.get("dias_desde_ultima", 999)
            if pd.notna(dias) and dias < 90:
                score += 10
                reasons.append("activo reciente")

            # 5. ¿Licita en LP? (la mayoría del RSS son LP)
            n_lp = lead.get("n_LP", 0)
            if pd.notna(n_lp) and n_lp > 0:
                score += 5
                reasons.append("licita en LP")

            if score >= 15:  # Umbral mínimo
                nombre_val = lead.get("nombre")
                score_val = lead.get("score_combined")
                sc = score_val if pd.notna(score_val) else lead.get("score_total")
                matches.append({
                    "tender_codigo": codigo,
                    "tender_nombre": nombre[:60],
                    "tender_cierre": tender.get("cierre", ""),
                    "lead_rut": rut,
                    "lead_nombre": nombre_val if pd.notna(nombre_val) else rut,
                    "lead_score": sc if pd.notna(sc) else 0,
                    "match_score": score,
                    "match_reasons": " | ".join(reasons),
                    "lead_telefono": lead.get("telefono", ""),
                })

    matches_df = pd.DataFrame(matches)
    if len(matches_df) > 0:
        matches_df = matches_df.sort_values("match_score", ascending=False)

    print(f"  Matches encontrados: {len(matches_df)}")
    return matches_df


def main():
    print_header("09 — Tender Matcher (Licitación -> Lead)")

    days = 3
    specific_tender = None

    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 >= len(sys.argv):
            print("ERROR: --days requiere un valor numérico")
            sys.exit(1)
        try:
            days = int(sys.argv[idx + 1])
        except ValueError:
            print(f"ERROR: --days requiere un número, se recibió '{sys.argv[idx + 1]}'")
            sys.exit(1)

    if "--tender" in sys.argv:
        idx = sys.argv.index("--tender")
        if idx + 1 >= len(sys.argv):
            print("ERROR: --tender requiere un código de licitación")
            sys.exit(1)
        specific_tender = sys.argv[idx + 1]

    # Cargar leads
    try:
        leads, leads_path = load_best_leads_dataframe()
    except FileNotFoundError:
        print("ERROR: No hay leads rankeados")
        sys.exit(1)
    assert_dataframe_contract(leads, "leads_enriched" if "telefono" in leads.columns else
                              ("leads_ml_ranked" if "score_combined" in leads.columns else "leads_ranked"))
    leads = leads.head(200).copy()  # Top 200 para matching
    print(f"Leads cargados: {len(leads)}")

    # Cargar tender_map si existe loss_analysis
    loss_path = OUTPUT_DIR / "loss_analysis.parquet"
    if loss_path.exists():
        loss_df = pd.read_parquet(loss_path)
        # Merge rival info
        for col in ["top_rival_1", "top_rival_2"]:
            if col in loss_df.columns and col not in leads.columns:
                leads = leads.merge(loss_df[["rut", col]], on="rut", how="left")

    # Obtener licitaciones
    if specific_tender:
        tenders = [{
            "codigo": specific_tender,
            "nombre": f"Licitación {specific_tender}",
            "region": "",
        }]
    else:
        # Combinar RSS + API
        tenders = get_rss_tenders()
        api_tenders = get_api_tenders(days)

        # Dedup por código
        seen = {t["codigo"] for t in tenders if t["codigo"]}
        for t in api_tenders:
            if t["codigo"] not in seen:
                tenders.append(t)
                seen.add(t["codigo"])

        print(f"\nTotal licitaciones de construcción: {len(tenders)}")

    if not tenders:
        print("No se encontraron licitaciones de construcción recientes")
        sys.exit(0)

    # Match
    matches = match_tenders_to_leads(tenders, leads)

    if len(matches) == 0:
        print("\nNo se encontraron matches significativos")
        sys.exit(0)

    # Guardar matches
    csv_path = OUTPUT_DIR / "matches.csv"
    matches.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Generar alertas
    alerts_path = OUTPUT_DIR / "alertas_contacto.txt"
    with open(alerts_path, "w", encoding="utf-8") as f:
        f.write(f"# ALERTAS DE CONTACTO — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# Licitaciones de construcción activas × Top leads\n")
        f.write("=" * 60 + "\n\n")

        current_tender = None
        for _, m in matches.iterrows():
            if m["tender_codigo"] != current_tender:
                current_tender = m["tender_codigo"]
                f.write(f"\n{'='*60}\n")
                f.write(f"LICITACIÓN: {m['tender_nombre']}\n")
                f.write(f"Código: {m['tender_codigo']}\n")
                cierre = m.get("tender_cierre")
                if pd.notna(cierre) and cierre:
                    f.write(f"Cierre: {cierre}\n")
                f.write(f"\nLEADS A CONTACTAR:\n")

            lead_sc = m['lead_score'] if pd.notna(m['lead_score']) else 0
            f.write(f"\n  -> {m['lead_nombre']} (Score: {lead_sc:.0f})\n")
            f.write(f"    Match: {m['match_score']} pts — {m['match_reasons']}\n")
            tel = m.get("lead_telefono")
            if pd.notna(tel) and tel:
                f.write(f"    Tel: {tel}\n")

    # Resumen
    print(f"\n{'='*60}")
    print(f"  MATCHES LICITACIÓN -> LEAD")
    print(f"{'='*60}")
    print(f"  Licitaciones analizadas: {len(tenders)}")
    print(f"  Matches encontrados: {len(matches)}")
    print(f"  Leads con match: {matches['lead_rut'].nunique()}")

    # Top matches
    print(f"\n  Top 10 matches:")
    print(f"  {'Match':>5} {'Lead Score':>10} {'Empresa':25s} {'Licitación':30s} {'Razón'}")
    print(f"  {'-'*90}")
    for _, m in matches.head(10).iterrows():
        nombre = str(m["lead_nombre"]) if pd.notna(m["lead_nombre"]) else "?"
        nombre = nombre[:23]
        tender = str(m["tender_nombre"])[:28]
        lead_sc = m['lead_score'] if pd.notna(m['lead_score']) else 0
        print(f"  {m['match_score']:>5} {lead_sc:>10.0f} "
              f"{nombre:25s} {tender:30s} {m['match_reasons']}")

    print(f"\n  Archivos:")
    print(f"    {csv_path}")
    print(f"    {alerts_path}")
    write_run_manifest(
        OUTPUT_DIR / "matcher_manifest.json",
        command="python 09_tender_matcher.py",
        source=leads_path.name,
        outputs=[str(csv_path), str(alerts_path)],
        details={"tenders": len(tenders), "matches": len(matches)},
    )


if __name__ == "__main__":
    main()
