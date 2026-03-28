"""
Generador de mensajes WhatsApp v3 — Insights reales y específicos.

Prioridad de insight por lead:
  1. rival_fuerte    — rival ganó 3+ veces (nombrado con conteo)
  2. rival_recurrente — rival ganó 2 veces (nombrado)
  3. lp_alto         — 5+ licitaciones grandes LP (>$66M)
  4. wr_bajo_lp      — win rate < 20% con LP >= 3
  5. loss_concentrado — loss_rate >= 40% con 5+ pérdidas
  6. inactivo        — sin ofertar 6+ meses
  7. wr_bajo         — win rate < 20% cualquier perfil
  8. rival_unico     — rival ganó 1 vez (phrasing honesto)
  9. default         — stats honestos con rival nombrado si lo hay
"""
import pandas as pd
import urllib.parse
import re
from pathlib import Path

# ─── Configuración ────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent / "lead_scoring" / "data"
VERIFIED_CSV = BASE_DIR / "output" / "leads_verificados.csv"
LOSS_PAR     = BASE_DIR / "output" / "loss_analysis.parquet"
ENRICHED_PAR = BASE_DIR / "filtered" / "leads_enriched.parquet"
COMPANYDB    = BASE_DIR / "filtered" / "company_database.parquet"
OUT_CSV      = BASE_DIR / "output" / "leads_verificados.csv"
OUT_XLSX     = BASE_DIR / "output" / "leads_verificados.xlsx"
OUT_TXT      = BASE_DIR / "output" / "mensajes_wsp_v3.txt"

FIRMA = "Sebastián Cortés\nIngenIA Licitaciones"
INDUSTRY_WR_MEDIAN = 0.22   # calculado de empresa activas (total_bids>=5)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def humanizar(nombre_raw: str) -> str:
    """Extrae nombre comercial del campo 'LEGAL | Comercial'."""
    if not isinstance(nombre_raw, str):
        return str(nombre_raw)
    nombre = nombre_raw.split("|")[-1].strip() if "|" in nombre_raw else nombre_raw.strip()
    formas = r"\b(SPA|LTDA|LIMITADA|EIRL|E\.I\.R\.L\.|S\.A\.|SA)\b\.?$"
    nombre = re.sub(formas, "", nombre, flags=re.IGNORECASE).strip(" .,")
    return nombre.title()


def limpiar_rival(rival_raw: str) -> str:
    """Extrae nombre comercial corto de un rival."""
    if not isinstance(rival_raw, str) or not rival_raw.strip():
        return ""
    nombre = rival_raw.split("|")[-1].strip() if "|" in rival_raw else rival_raw.strip()
    formas = r"\b(SPA|LTDA|LIMITADA|EIRL|E\.I\.R\.L\.|S\.A\.|SA)\b\.?$"
    nombre = re.sub(formas, "", nombre, flags=re.IGNORECASE).strip(" .,")
    return nombre.title()


def pct(val: float) -> str:
    return f"{val * 100:.0f}%"


def meses(dias: float) -> int:
    return int(round(float(dias) / 30))


# ─── Motor de insight ─────────────────────────────────────────────────────────

def elegir_insight(row: pd.Series) -> dict:
    """
    Devuelve {'tipo': str, 'cuerpo': str, 'cta': str}
    Orden de prioridad: rival fuerte → LP alto → win rate bajo → inactividad → default
    """
    wr          = float(row.get("win_rate", 0) or 0)
    n_lp        = int(row.get("n_LP", 0) or 0)
    total_lost  = int(row.get("total_lost_loss", 0) or 0)
    loss_rate   = float(row.get("loss_rate", 0) or 0)
    total_bids  = int(row.get("total_bids", 0) or 0)
    total_wins  = int(row.get("total_wins", 0) or 0)
    dias        = float(row.get("dias_desde_ultima", 0) or 0)

    rival1      = limpiar_rival(str(row.get("top_rival_1_name", "") or ""))
    rival1_cnt  = int(row.get("top_rival_1_count", 0) or 0)
    rival2      = limpiar_rival(str(row.get("top_rival_2_name", "") or ""))
    rival2_cnt  = int(row.get("top_rival_2_count", 0) or 0)

    wr_gap = INDUSTRY_WR_MEDIAN - wr   # positivo = están bajo el promedio

    # ── 1. Rival muy dominante (3+ veces) ────────────────────────────────────
    if rival1_cnt >= 3 and rival1:
        return {
            "tipo": "rival_fuerte",
            "cuerpo": (
                f"Revisé el historial de licitaciones de su empresa y encontré un patrón claro: "
                f"{rival1} les ha ganado en {rival1_cnt} de sus últimas {total_lost} licitaciones que no se adjudicaron.\n\n"
                f"No es casualidad — hay algo específico en cómo presentan sus propuestas que marca la diferencia, "
                f"y se puede identificar con los datos disponibles."
            ),
            "cta": "¿Le interesa saber exactamente qué es?",
        }

    # ── 2. Rival recurrente (2 veces) ────────────────────────────────────────
    if rival1_cnt >= 2 and rival1:
        return {
            "tipo": "rival_recurrente",
            "cuerpo": (
                f"Crucé el historial de su empresa con el de los ganadores en esas licitaciones. "
                f"{rival1} les ganó en {rival1_cnt} ocasiones — dentro de las mismas bases donde competían.\n\n"
                f"Hay un patrón en cómo se diferencian sus propuestas, y se puede analizar antes de la próxima postulación."
            ),
            "cta": "¿Le interesa ver el análisis de esas pérdidas?",
        }

    # ── 3. Muchas licitaciones grandes (LP ≥ 5) ──────────────────────────────
    if n_lp >= 5:
        tasa_str = pct(wr)
        prom_str = pct(INDUSTRY_WR_MEDIAN)
        return {
            "tipo": "lp_alto",
            "cuerpo": (
                f"Su empresa ha postulado a {n_lp} licitaciones de alto valor (LP, contratos sobre $66 millones). "
                f"En ese segmento la competencia es más dura y la diferencia entre adjudicar y no adjudicar "
                f"se juega en propuesta técnica y precio relativo.\n\n"
                + (
                    f"La tasa de adjudicación actual es {tasa_str}, con el rubro en {prom_str}. "
                    f"Con los datos de esas {total_lost} licitaciones no adjudicadas, se pueden identificar los patrones."
                    if wr < INDUSTRY_WR_MEDIAN else
                    f"Con el historial de esas {total_lost} licitaciones no adjudicadas, se pueden identificar los patrones específicos."
                )
            ),
            "cta": "¿Les interesa un análisis de esas licitaciones grandes?",
        }

    # ── 4. Win rate bajo con LP ───────────────────────────────────────────────
    if wr < 0.20 and n_lp >= 3:
        gap_pp = int(round(wr_gap * 100))
        return {
            "tipo": "wr_bajo_lp",
            "cuerpo": (
                f"Revisé el desempeño de su empresa en licitaciones LP (contratos sobre $66M): "
                f"de {n_lp} postulaciones, la tasa de adjudicación actual es {pct(wr)}, "
                f"mientras el promedio del rubro está en {pct(INDUSTRY_WR_MEDIAN)}.\n\n"
                f"Esa brecha de {gap_pp} puntos porcentuales equivale a contratos que están ganando los competidores. "
                f"Los factores que explican la diferencia se pueden identificar con los datos de esas bases."
            ),
            "cta": "¿Le interesa ver dónde está la brecha?",
        }

    # ── 5. Tasa de pérdida alta ───────────────────────────────────────────────
    if loss_rate >= 0.40 and total_lost >= 5:
        return {
            "tipo": "loss_concentrado",
            "cuerpo": (
                f"En el período analizado, {total_lost} de las licitaciones de su empresa no se adjudicaron "
                f"— una tasa de no adjudicación del {pct(loss_rate)}.\n\n"
                f"En ese tipo de perfil hay factores específicos y medibles que explican la diferencia "
                f"respecto a los ganadores. No son factores de precio únicamente."
            ),
            "cta": "¿Le interesa ver qué está marcando la diferencia en esas propuestas?",
        }

    # ── 6. Inactividad prolongada (≥ 6 meses) ────────────────────────────────
    if dias >= 180:
        m = meses(dias)
        return {
            "tipo": "inactivo",
            "cuerpo": (
                f"Su empresa lleva {m} meses sin presentar ofertas en Mercado Público. "
                f"En ese período han salido licitaciones del rubro constructivo en su región "
                f"donde han participado sus competidores directos.\n\n"
                f"Hay oportunidades activas ahora mismo que coinciden con el perfil de su empresa."
            ),
            "cta": (
                "¿Les interesa saber cuáles son esas licitaciones y quiénes están compitiendo en ellas?"
            ),
        }

    # ── 7. Win rate bajo general ──────────────────────────────────────────────
    if wr < 0.19:
        gap_pp = int(round(wr_gap * 100))
        return {
            "tipo": "wr_bajo",
            "cuerpo": (
                f"Revisé el historial de licitaciones de su empresa: {total_wins} adjudicaciones de {total_bids} postulaciones "
                f"— tasa de {pct(wr)}, con el promedio del rubro en {pct(INDUSTRY_WR_MEDIAN)}.\n\n"
                f"En ese tipo de perfil, la brecha de {gap_pp} puntos porcentuales casi siempre se explica "
                f"por factores específicos en la propuesta técnica o en el análisis de bases. Son factores medibles."
            ),
            "cta": "¿Le interesa identificar cuáles son en el caso de su empresa?",
        }

    # ── 8. Rival único — phrasing honesto ────────────────────────────────────
    if rival1 and total_lost >= 3:
        return {
            "tipo": "rival_unico",
            "cuerpo": (
                f"Crucé el historial de licitaciones de su empresa con los ganadores de las bases donde compitieron. "
                f"Entre las empresas que se adjudicaron esas licitaciones aparece {rival1}.\n\n"
                f"Con los datos de esas {total_lost} bases se pueden identificar los factores que marcaron la diferencia."
            ),
            "cta": "¿Le interesa ver el análisis de esas pérdidas?",
        }

    # ── 9. Default ────────────────────────────────────────────────────────────
    return {
        "tipo": "default",
        "cuerpo": (
            f"Revisé el historial de licitaciones de su empresa en Mercado Público: "
            f"{total_wins} adjudicadas de {total_bids} postulaciones.\n\n"
            f"En las licitaciones que no se adjudicaron hay patrones específicos que se pueden identificar "
            f"cruzando sus propuestas con las de los ganadores."
        ),
        "cta": "¿Le interesa ver el análisis?",
    }


# ─── Mensaje completo ─────────────────────────────────────────────────────────

def generar_mensaje(empresa: str, contacto, row: pd.Series) -> str:
    # Saludo con primer nombre si hay contacto
    if contacto and isinstance(contacto, str) and len(contacto.strip()) > 2:
        primer_nombre = contacto.strip().split()[0].title()
        saludo = f"Hola {primer_nombre},"
    else:
        saludo = "Hola,"

    insight = elegir_insight(row)
    return (
        f"{saludo} soy Sebastián de IngenIA Licitaciones.\n\n"
        f"{insight['cuerpo']}\n\n"
        f"{insight['cta']}\n\n"
        f"{FIRMA}"
    )


def generar_wsp_link(telefono: str, mensaje: str) -> str:
    # Convertir float → int antes de extraer dígitos (evita el ".0" extra)
    try:
        tel = str(int(float(str(telefono))))
    except (ValueError, OverflowError):
        tel = re.sub(r"[^\d]", "", str(telefono))
    if not tel.startswith("56"):
        tel = "56" + tel.lstrip("0")
    return f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje, safe='')}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Cargando datos...")
    verified = pd.read_csv(VERIFIED_CSV)
    loss     = pd.read_parquet(LOSS_PAR)
    # enriched no se necesita — loss ya contiene win_rate, bids, wins, monto_total

    # Los 45 leads WSP
    wsp = verified[verified["wsp_probable"] == "alta"].copy()
    print(f"Leads WSP: {len(wsp)}")

    # Columnas de loss que necesitamos (loss tiene todo: win_rate, bids, rivals, etc.)
    loss_cols = [
        "rut", "win_rate", "total_bids", "total_wins", "monto_total",
        "n_LP", "total_lost_loss", "loss_rate",
        "top_rival_1_name", "top_rival_1_count",
        "top_rival_2_name", "top_rival_2_count",
        "n_distinct_rivals_loss", "dias_desde_ultima",
        "xgb_predicted_wr",
    ]
    # Merge solo con loss (evita conflictos de columnas duplicadas)
    # Drop columnas que ya existen en verified para evitar sufijos
    loss_sub = loss[loss_cols].copy()
    wsp_clean = wsp.drop(columns=["win_rate", "total_bids"], errors="ignore")
    df = wsp_clean.merge(loss_sub, on="rut", how="left")

    # Nombre humanizado
    df["empresa_display"] = df["nombre"].apply(humanizar)

    # Generar mensajes
    mensajes   = []
    wsp_links  = []
    tipos      = []

    for _, row in df.iterrows():
        msg  = generar_mensaje(row["empresa_display"], row.get("contacto_nombre"), row)
        link = generar_wsp_link(str(row.get("telefono_normalizado", "")), msg)
        ins  = elegir_insight(row)

        mensajes.append(msg)
        wsp_links.append(link)
        tipos.append(ins["tipo"])

    df["wsp_mensaje"]  = mensajes
    df["wsp_link"]     = wsp_links
    df["insight_tipo"] = tipos

    # Actualizar df completo
    updated = verified.copy()
    mask = updated["wsp_probable"] == "alta"
    updated.loc[mask, "wsp_mensaje"] = df["wsp_mensaje"].values
    updated.loc[mask, "wsp_link"]    = df["wsp_link"].values

    # ── Guardar CSV ──────────────────────────────────────────────────────────
    updated.to_csv(OUT_CSV, index=False)
    print(f"CSV: {OUT_CSV}")

    # ── Guardar XLSX ─────────────────────────────────────────────────────────
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        wsp_out = df[[
            "outreach_rank", "empresa_display", "rut",
            "telefono_normalizado", "contacto_nombre",
            "wsp_link", "wsp_mensaje", "insight_tipo",
            "win_rate", "n_LP", "total_lost_loss", "loss_rate",
            "top_rival_1_name", "top_rival_1_count",
            "top_rival_2_name", "top_rival_2_count",
            "dias_desde_ultima", "monto_total",
            "email", "direccion",
        ]].sort_values("outreach_rank")
        wsp_out.to_excel(writer, sheet_name="WhatsApp Listos", index=False)

        resumen = df.groupby("insight_tipo").size().reset_index(name="cantidad")
        resumen.to_excel(writer, sheet_name="Resumen Insights", index=False)

        otros = updated[updated["wsp_probable"] != "alta"]
        otros.to_excel(writer, sheet_name="Otros Leads", index=False)
    print(f"XLSX: {OUT_XLSX}")

    # ── Guardar TXT ──────────────────────────────────────────────────────────
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for i, (_, row) in enumerate(df.sort_values("outreach_rank").iterrows(), 1):
            f.write(f"{'='*72}\n")
            f.write(f"LEAD #{i:02d} | Rank #{int(row['outreach_rank']):02d} | {row['empresa_display']}\n")
            f.write(f"RUT: {row['rut']} | Tel: {row['telefono_normalizado']}\n")
            f.write(f"Insight: {row['insight_tipo']} | WR: {pct(float(row['win_rate'] or 0))} | LP: {int(row['n_LP'] or 0)} | Perdidas: {int(row['total_lost_loss'] or 0)}\n")
            f.write(f"Link: {row['wsp_link']}\n")
            f.write(f"{'─'*72}\n")
            f.write(row["wsp_mensaje"])
            f.write(f"\n{'='*72}\n\n")
    print(f"TXT: {OUT_TXT}")

    # ── Reporte consola ───────────────────────────────────────────────────────
    print("\n=== DISTRIBUCION DE INSIGHTS ===")
    dist = df["insight_tipo"].value_counts()
    for tipo, cnt in dist.items():
        print(f"  {tipo:22} {cnt:3} leads")

    print("\n=== MUESTRA (primeros 8 mensajes por ranking) ===")
    for i, (_, row) in enumerate(df.sort_values("outreach_rank").head(8).iterrows(), 1):
        print(f"\n{'='*65}")
        print(f"[{i}] {row['empresa_display']} | Tipo: {row['insight_tipo']}")
        print(f"    WR={pct(float(row['win_rate'] or 0))} | LP={int(row['n_LP'] or 0)} | Perdidas={int(row['total_lost_loss'] or 0)}")
        print(f"{'─'*65}")
        print(row["wsp_mensaje"])


if __name__ == "__main__":
    main()
