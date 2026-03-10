"""
16 - Verificación y scoring de contactabilidad de leads.

Limpia, normaliza y clasifica teléfonos. Cruza fuentes.
Genera lista priorizada para outreach por WhatsApp.

Resultado:
  data/output/leads_verificados.xlsx   — Lista priorizada con score de contactabilidad
  data/output/leads_verificados.csv    — CSV para importar
  data/output/verificacion_report.json — Estadísticas de verificación

Uso:
  python 16_verify_contacts.py              # Verificar top 100
  python 16_verify_contacts.py --top 200    # Verificar top 200
  python 16_verify_contacts.py --all        # Verificar todos los enriquecidos
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from config import FILTERED_DIR, OUTPUT_DIR
from pipeline_core import load_best_leads_dataframe
from pipeline_validation import write_run_manifest
from utils import print_header


# === Normalización de teléfonos chilenos ===

# Celular chileno: 9 XXXX XXXX, +56 9 XXXX XXXX, 9XXXXXXXX
_PREFIX = r"(?:\+?56)?"  # Prefijo país opcional
RE_MOBILE_CL = re.compile(rf"^\s*{_PREFIX}\s*9[\s.-]?(\d{{4}})[\s.-]?(\d{{4}})\s*$")
RE_MOBILE_SHORT = re.compile(r"^\s*9\s*(\d{4})[\s.-]?(\d{4})\s*$")
# Fijo chileno: (2) 2235 1639, (41) 213 9104, (63) 223 0504
RE_LANDLINE_CL = re.compile(rf"^\s*{_PREFIX}\s*\(?(\d{{1,2}})\)?\s+(\d{{3,4}})[\s.-]?(\d{{4}})\s*$")
# Formato atípico: 099 562 8466
RE_LANDLINE_ALT = re.compile(r"^\s*0?(\d{1,2})\s+(\d{3,4})[\s.-]?(\d{4})\s*$")


def normalize_phone_cl(raw: str) -> dict:
    """Normaliza un teléfono chileno y clasifica tipo."""
    if pd.isna(raw) or not str(raw).strip():
        return {"normalized": None, "type": "sin_telefono", "valid": False, "raw": raw}

    cleaned = str(raw).strip()
    # Limpiar caracteres URL-encoded
    cleaned = cleaned.replace("%20", " ").replace("%2B", "+")

    # Intentar celular
    m = RE_MOBILE_CL.match(cleaned) or RE_MOBILE_SHORT.match(cleaned)
    if m:
        digits = m.group(1) + m.group(2)
        return {
            "normalized": f"+569{digits}",
            "type": "celular",
            "valid": True,
            "raw": raw,
        }

    # Intentar fijo
    m = RE_LANDLINE_CL.match(cleaned) or RE_LANDLINE_ALT.match(cleaned)
    if m:
        area = m.group(1)
        part1 = m.group(2)
        part2 = m.group(3)
        return {
            "normalized": f"+56{area}{part1}{part2}",
            "type": "fijo",
            "valid": True,
            "raw": raw,
        }

    # Formato internacional no chileno
    if cleaned.startswith("+") and not cleaned.startswith("+56"):
        return {"normalized": cleaned, "type": "internacional", "valid": False, "raw": raw}

    return {"normalized": None, "type": "formato_invalido", "valid": False, "raw": raw}


def whatsapp_likely(phone_info: dict) -> str:
    """Estima probabilidad de WhatsApp basado en tipo de número."""
    if phone_info["type"] == "celular":
        return "alta"  # ~90% de celulares chilenos tienen WhatsApp
    if phone_info["type"] == "fijo":
        return "nula"  # fijos no tienen WhatsApp
    return "desconocida"


# === Scoring de contactabilidad ===

def score_contactability(row: pd.Series) -> dict:
    """Calcula score de contactabilidad y razones."""
    score = 0
    reasons = []

    # Teléfono celular verificado
    if row.get("phone_type") == "celular":
        score += 40
        reasons.append("celular_verificado")
    elif row.get("phone_type") == "fijo":
        score += 10
        reasons.append("solo_fijo")

    # WhatsApp probable
    if row.get("wsp_probable") == "alta":
        score += 20
        reasons.append("wsp_probable")

    # Email disponible
    if pd.notna(row.get("email")) and str(row.get("email", "")).strip():
        score += 15
        reasons.append("tiene_email")

    # Website disponible (respaldo para buscar más datos)
    if pd.notna(row.get("web")) and str(row.get("web", "")).strip():
        score += 10
        reasons.append("tiene_web")

    # Nombre de contacto disponible
    if pd.notna(row.get("contacto_nombre")) and str(row.get("contacto_nombre", "")).strip():
        score += 10
        reasons.append("tiene_nombre_contacto")

    # Dirección disponible
    if pd.notna(row.get("direccion")) and str(row.get("direccion", "")).strip():
        score += 5
        reasons.append("tiene_direccion")

    # Fuentes múltiples (mayor confianza)
    sources = 0
    if pd.notna(row.get("gm_telefono")):
        sources += 1
    if pd.notna(row.get("ocds_telefono")):
        sources += 1
    if sources >= 2:
        score += 10
        reasons.append("multiples_fuentes")

    return {"score": min(score, 100), "reasons": reasons}


# === Clasificación para outreach ===

def classify_outreach(row: pd.Series) -> str:
    """Clasifica la acción de outreach recomendada."""
    if row.get("phone_type") == "celular" and row.get("wsp_probable") == "alta":
        return "WSP_DIRECTO"
    if row.get("phone_type") == "fijo" and pd.notna(row.get("email")):
        return "EMAIL_PRIMERO"
    if row.get("phone_type") == "fijo":
        return "LLAMAR_FIJO"
    if pd.notna(row.get("email")):
        return "EMAIL_FRIO"
    if pd.notna(row.get("web")):
        return "BUSCAR_CONTACTO_WEB"
    return "SIN_CANAL"


# === Mensaje WhatsApp personalizado ===

def _clean_name(raw: str) -> str:
    """Extrae nombre comercial limpio de formatos como 'RAZÓN SOCIAL | Nombre Comercial'."""
    if pd.isna(raw) or not str(raw).strip():
        return "su empresa"
    name = str(raw).strip()
    if "|" in name:
        parts = [p.strip() for p in name.split("|")]
        # Preferir la parte que no es todo mayúsculas (nombre comercial)
        mixed = [p for p in parts if not p.isupper() and len(p) > 3]
        if mixed:
            return mixed[0]
        # Si todas son mayúsculas, la más corta
        return min(parts, key=len)
    return name


def generate_wsp_message(row: pd.Series) -> str:
    """Genera mensaje WhatsApp personalizado con tildes y ñ."""
    contacto = row.get("contacto_nombre", "")
    if pd.isna(contacto) or not str(contacto).strip():
        contacto = "estimado/a"

    empresa = _clean_name(row.get("nombre", ""))

    n_bids = int(row["total_bids"]) if pd.notna(row.get("total_bids")) else 0
    win_rate = float(row["win_rate"]) if pd.notna(row.get("win_rate")) else 0
    n_lp = int(row["n_LP"]) if pd.notna(row.get("n_LP")) else 0
    total_wins = int(row["total_wins"]) if pd.notna(row.get("total_wins")) else 0
    total_lost = int(row.get("total_lost", 0)) if pd.notna(row.get("total_lost")) else 0

    # Construir detalle personalizado según datos del lead
    detalles = []
    if n_lp > 0:
        detalles.append(f"incluyendo {n_lp} licitaciones LP (mayores a $66M)")
    if total_wins > 0 and total_lost > 0:
        detalles.append(f"con {total_wins} adjudicaciones y {total_lost} no adjudicadas")
    elif win_rate > 0:
        detalles.append(f"con una tasa de adjudicación de {win_rate:.0%}")

    # Gancho según situación
    gancho = ""
    if win_rate > 0 and win_rate < 0.25:
        gancho = (
            "\n\nNoté que la tasa de adjudicación está por debajo del promedio del rubro. "
            "Justamente ahí es donde más impacto tiene un análisis estratégico de las bases."
        )
    elif total_lost >= 5:
        gancho = (
            f"\n\nIdentifiqué {total_lost} licitaciones donde no se logró la adjudicación. "
            "Puedo mostrarle exactamente qué factores influyeron y cómo mejorar la próxima postulación."
        )

    detalle_str = ", ".join(detalles)
    if detalle_str:
        detalle_str = f", {detalle_str}"

    msg = (
        f"Hola {contacto}, soy Sebastián Cortés de IngenIA Licitaciones.\n"
        f"\n"
        f"Vi que {empresa} ha participado en {n_bids} licitaciones de construcción "
        f"en Mercado Público{detalle_str}.{gancho}\n"
        f"\n"
        f"Ofrezco un servicio de inteligencia de licitaciones con IA que ayuda "
        f"a constructoras como la suya a:\n"
        f"\n"
        f"• Detectar requisitos críticos en las bases (multas, garantías, plazos)\n"
        f"• Identificar quién les ha ganado y por qué\n"
        f"• Optimizar la estrategia para mejorar la tasa de adjudicación\n"
        f"\n"
        f"¿Les interesaría una demo gratuita con una licitación real suya? "
        f"Solo necesito el código de la licitación.\n"
        f"\n"
        f"Sebastián Cortés\n"
        f"Ing. Civil UCN · IngenIA Licitaciones"
    )
    return msg


def build_wsp_link(phone_normalized: str, message: str) -> str:
    """Genera link wa.me con mensaje pre-cargado y encoding correcto."""
    if pd.isna(phone_normalized) or not phone_normalized:
        return ""
    # wa.me necesita número sin + ni espacios
    number = phone_normalized.replace("+", "").replace(" ", "").replace("-", "")
    encoded_msg = quote(message, safe="")
    return f"https://wa.me/{number}?text={encoded_msg}"


def main():
    print_header("16 — Verificación de Contactos")

    # Parsear argumentos
    top_n = 100
    if "--all" in sys.argv:
        top_n = None
    elif "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 < len(sys.argv):
            top_n = int(sys.argv[idx + 1])

    # Cargar leads
    try:
        df, source_path = load_best_leads_dataframe()
    except FileNotFoundError:
        print("ERROR: No hay leads enriquecidos.")
        print("Ejecuta primero: python 06_enrich_contacts.py")
        sys.exit(1)

    if top_n:
        df = df.head(top_n).copy()
    print(f"Verificando {len(df)} leads desde {source_path.name}")

    # === Paso 1: Normalizar teléfonos ===
    print("\n--- Normalizando teléfonos ---")
    phone_results = df["telefono"].apply(normalize_phone_cl)
    df["telefono_normalizado"] = phone_results.apply(lambda x: x["normalized"]).astype("string")
    df["phone_type"] = phone_results.apply(lambda x: x["type"])
    df["phone_valid"] = phone_results.apply(lambda x: x["valid"])
    df["wsp_probable"] = phone_results.apply(lambda x: whatsapp_likely(x))

    type_counts = df["phone_type"].value_counts().to_dict()
    print(f"  Celular:    {type_counts.get('celular', 0)}")
    print(f"  Fijo:       {type_counts.get('fijo', 0)}")
    print(f"  Sin tel:    {type_counts.get('sin_telefono', 0)}")
    print(f"  Inválido:   {type_counts.get('formato_invalido', 0)}")
    print(f"  Internac:   {type_counts.get('internacional', 0)}")

    # === Paso 2: Score de contactabilidad ===
    print("\n--- Calculando contactabilidad ---")
    contact_scores = df.apply(score_contactability, axis=1)
    df["contact_score"] = contact_scores.apply(lambda x: x["score"])
    df["contact_reasons"] = contact_scores.apply(lambda x: ", ".join(x["reasons"]))

    # === Paso 3: Clasificar acción de outreach ===
    df["outreach_action"] = df.apply(classify_outreach, axis=1)

    # === Paso 3b: Generar mensajes y links WhatsApp ===
    print("\n--- Generando mensajes personalizados ---")
    df["wsp_mensaje"] = df.apply(generate_wsp_message, axis=1)
    df["wsp_link"] = df.apply(
        lambda row: build_wsp_link(row.get("telefono_normalizado", ""), row["wsp_mensaje"])
        if row.get("outreach_action") == "WSP_DIRECTO" else "",
        axis=1,
    )
    wsp_ready = (df["wsp_link"] != "").sum()
    print(f"  {wsp_ready} mensajes con link wa.me generados")

    action_counts = df["outreach_action"].value_counts().to_dict()
    print(f"\n  === ACCIONES DE OUTREACH ===")
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        print(f"  {action}: {count}")

    # === Paso 4: Ordenar por prioridad ===
    # Prioridad: score de negocio (rank_ml) + contactabilidad
    score_col = "score_combined" if "score_combined" in df.columns else "score_total"
    if score_col in df.columns:
        # Normalizar business score a 0-100
        biz_score = df[score_col].fillna(0)
        # Combinar: 60% negocio + 40% contactabilidad
        df["outreach_priority"] = (biz_score * 0.6 + df["contact_score"] * 0.4).round(1)
    else:
        df["outreach_priority"] = df["contact_score"]

    df = df.sort_values("outreach_priority", ascending=False).reset_index(drop=True)
    df["outreach_rank"] = range(1, len(df) + 1)

    # === Exportar ===
    print("\n--- Exportando resultados ---")

    # Columnas para el export
    export_cols = [
        "outreach_rank", "outreach_priority", "outreach_action",
        "nombre", "rut",
        "telefono_normalizado", "phone_type", "wsp_probable",
        "wsp_link", "wsp_mensaje",
        "email", "web", "contacto_nombre", "direccion",
        "contact_score", "contact_reasons",
    ]
    # Agregar score de negocio si existe
    if score_col in df.columns:
        export_cols.insert(3, score_col)
    if "rank_ml" in df.columns:
        export_cols.insert(4, "rank_ml")
    if "win_rate" in df.columns:
        export_cols.append("win_rate")
    if "total_bids" in df.columns:
        export_cols.append("total_bids")

    # Solo columnas que existen
    export_cols = [c for c in export_cols if c in df.columns]
    export_df = df[export_cols]

    # Excel
    xlsx_path = OUTPUT_DIR / "leads_verificados.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Hoja principal: todos
        export_df.to_excel(writer, sheet_name="Todos", index=False)

        # Hoja: listos para WhatsApp (columnas optimizadas para acción)
        wsp_mask = df["outreach_action"] == "WSP_DIRECTO"
        wsp_cols = [
            "outreach_rank", "nombre", "telefono_normalizado",
            "wsp_link", "wsp_mensaje",
            "email", "contacto_nombre",
        ]
        if "win_rate" in df.columns:
            wsp_cols.insert(3, "win_rate")
        if "total_bids" in df.columns:
            wsp_cols.insert(3, "total_bids")
        wsp_cols = [c for c in wsp_cols if c in df.columns]
        wsp_df = df.loc[wsp_mask, wsp_cols].copy()
        wsp_df.to_excel(writer, sheet_name="WhatsApp Listos", index=False)
        # Forzar columna teléfono como texto para preservar el +
        ws_wsp = writer.sheets["WhatsApp Listos"]
        from openpyxl.utils import get_column_letter
        if "telefono_normalizado" in wsp_cols:
            tel_col_idx = wsp_cols.index("telefono_normalizado") + 1
            for row_idx in range(2, len(wsp_df) + 2):
                cell = ws_wsp.cell(row=row_idx, column=tel_col_idx)
                cell.number_format = "@"  # formato texto

        # Hoja: necesitan otro canal
        other_df = export_df[df["outreach_action"] != "WSP_DIRECTO"]
        other_df.to_excel(writer, sheet_name="Otros Canales", index=False)

        # Hoja: resumen
        summary = pd.DataFrame({
            "Métrica": [
                "Total leads verificados",
                "Con celular verificado",
                "WhatsApp probable",
                "Solo fijo",
                "Sin teléfono",
                "Con email",
                "Con web",
                "Listos para WSP directo",
                "Contact score promedio",
                "Fecha verificación",
            ],
            "Valor": [
                len(df),
                type_counts.get("celular", 0),
                int((df["wsp_probable"] == "alta").sum()),
                type_counts.get("fijo", 0),
                type_counts.get("sin_telefono", 0),
                int(df["email"].notna().sum()),
                int(df["web"].notna().sum()),
                action_counts.get("WSP_DIRECTO", 0),
                f"{df['contact_score'].mean():.0f}/100",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ],
        })
        summary.to_excel(writer, sheet_name="Resumen", index=False)

    print(f"  Excel: {xlsx_path}")

    # CSV
    csv_path = OUTPUT_DIR / "leads_verificados.csv"
    export_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  CSV: {csv_path}")

    # Reporte JSON
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": source_path.name,
        "total_leads": len(df),
        "phone_types": type_counts,
        "outreach_actions": action_counts,
        "wsp_directo": action_counts.get("WSP_DIRECTO", 0),
        "contact_score_mean": round(df["contact_score"].mean(), 1),
        "contact_score_median": round(df["contact_score"].median(), 1),
    }
    report_path = OUTPUT_DIR / "verificacion_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Reporte: {report_path}")

    write_run_manifest(
        OUTPUT_DIR / "verificacion_manifest.json",
        command="python 16_verify_contacts.py",
        source=source_path.name,
        outputs=[str(xlsx_path), str(csv_path), str(report_path)],
        details=report,
    )

    # === Resumen final ===
    wsp_count = action_counts.get("WSP_DIRECTO", 0)
    print(f"\n{'='*60}")
    print(f"  VERIFICACIÓN COMPLETADA")
    print(f"{'='*60}")
    print(f"  {wsp_count} leads listos para WhatsApp directo")
    print(f"  {action_counts.get('EMAIL_PRIMERO', 0)} leads por email primero")
    print(f"  {action_counts.get('LLAMAR_FIJO', 0)} leads para llamar por fijo")
    print(f"  {action_counts.get('SIN_CANAL', 0)} leads sin canal disponible")
    print(f"\n  Top 5 para contactar:")
    top5 = df[df["outreach_action"] == "WSP_DIRECTO"].head(5)
    for _, row in top5.iterrows():
        print(f"    #{int(row['outreach_rank'])} {row['nombre'][:35]:35s} {row['telefono_normalizado']}  (score: {row['outreach_priority']})")


if __name__ == "__main__":
    main()
