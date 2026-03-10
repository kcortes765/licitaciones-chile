"""
Generador de mensajes WhatsApp v4 — Implementación post-auditoría de 5 agentes.

Cambios respecto a v3:
  - Nuevo tipo win_rate_gap_LP: n_LP>=5 AND WR<20% (antes de lp_alto)
  - lp_alto siempre incluye benchmark de tasa (WR>=rubro o WR<rubro)
  - inactivo se evalúa ANTES de wr_bajo_lp cuando n_lp<5 (fix LEAD #24)
  - Todas las plantillas reescritas: GOLPE PRIMERO → método → CTA
  - Salida: mensajes_wsp_v4.txt + leads_verificados_v4.xlsx

Prioridad de insight por lead:
  1. rival_fuerte     — rival ganó 3+ veces (nombrado con conteo)
  2. rival_recurrente — rival ganó 2 veces (nombrado)
  3. win_rate_gap_LP  — n_LP>=5 AND WR<20% (ángulo del dolor en contratos grandes)
  4. lp_alto          — n_LP>=5 (con benchmark de tasa siempre)
  5. inactivo         — sin ofertar 6+ meses (ANTES de wr_bajo_lp cuando n_lp<5)
  6. wr_bajo_lp       — WR<20% con LP>=3
  7. loss_concentrado — loss_rate>=40% con 5+ pérdidas
  8. wr_bajo          — WR<19% cualquier perfil
  9. rival_unico      — rival ganó 1 vez
  10. default         — stats honestos
"""
import pandas as pd
import urllib.parse
import re

# ─── Configuración ────────────────────────────────────────────────────────────
BASE_DIR     = "C:/Seba/Nueva carpeta (2)/lead_scoring/data"
VERIFIED_CSV = f"{BASE_DIR}/output/leads_verificados.csv"
LOSS_PAR     = f"{BASE_DIR}/output/loss_analysis.parquet"
ENRICHED_PAR = f"{BASE_DIR}/filtered/leads_enriched.parquet"
COMPANYDB    = f"{BASE_DIR}/filtered/company_database.parquet"

# v4 outputs — NO sobreescribir v3
OUT_XLSX = f"{BASE_DIR}/output/leads_verificados_v4.xlsx"
OUT_TXT  = f"{BASE_DIR}/output/mensajes_wsp_v4.txt"

FIRMA = "Sebastián Cortés\nIngenIA Licitaciones"
INDUSTRY_WR_MEDIAN = 0.22   # calculado de empresas activas (total_bids>=5)


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

    Orden de prioridad v4:
      rival_fuerte → rival_recurrente → win_rate_gap_LP → lp_alto →
      inactivo → wr_bajo_lp → loss_concentrado → wr_bajo → rival_unico → default
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
                f"{rival1} les ganó en {rival1_cnt} de las licitaciones donde compitieron directamente. "
                f"Hay un patrón claro en cómo estructura sus propuestas — "
                f"y se puede comparar base por base antes de la próxima postulación."
            ),
            "cta": "¿Le interesa ver qué está haciendo distinto?",
        }

    # ── 3. Win rate gap en contratos LP (n_LP>=5 AND WR<20%) ─────────────────
    # Este tipo captura el ángulo más doloroso: muchas postulaciones grandes, baja tasa.
    # Va ANTES de lp_alto para los leads con WR<20% (Agent 3: 7 leads afectados).
    if n_lp >= 5 and wr < 0.20:
        gap_pp = int(round(wr_gap * 100))
        return {
            "tipo": "win_rate_gap_LP",
            "cuerpo": (
                f"Su empresa ha postulado a {n_lp} licitaciones de alto valor (LP, sobre $66 millones) "
                f"y la tasa de adjudicación es {pct(wr)} — {gap_pp} puntos por debajo del promedio del rubro ({pct(INDUSTRY_WR_MEDIAN)}).\n\n"
                f"En contratos de ese tamaño, esa brecha son varios contratos anuales que están quedando en otras manos. "
                f"Los factores que la explican son medibles con el historial de esas bases."
            ),
            "cta": "¿Le interesa ver dónde está la diferencia?",
        }

    # ── 4. Muchas licitaciones grandes (LP >= 5, WR >= 20%) ──────────────────
    if n_lp >= 5:
        tasa_str = pct(wr)
        prom_str = pct(INDUSTRY_WR_MEDIAN)
        if wr < INDUSTRY_WR_MEDIAN:
            # WR bajo pero no tanto como para win_rate_gap_LP — igual mostrar brecha
            gap_pp = int(round(wr_gap * 100))
            cuerpo = (
                f"Su empresa ha postulado a {n_lp} licitaciones de alto valor (LP, contratos sobre $66 millones) "
                f"y la tasa de adjudicación es {tasa_str}, con el rubro en {prom_str}. "
                f"En contratos de ese tamaño, esa diferencia equivale a varios contratos que están quedando en manos de la competencia.\n\n"
                f"Con los datos de esas {total_lost} bases no adjudicadas, los factores que explican esa brecha son identificables."
            )
        else:
            # WR >= rubro: ángulo positivo pero igual hay pérdidas que analizar
            cuerpo = (
                f"Su empresa ha postulado a {n_lp} licitaciones de alto valor (LP, contratos sobre $66 millones). "
                f"La tasa actual es {tasa_str}, por encima del promedio del rubro ({prom_str}). "
                f"Aun así, con {total_lost} licitaciones no adjudicadas en contratos de ese valor, "
                f"los factores que las explican son medibles."
            )
        return {
            "tipo": "lp_alto",
            "cuerpo": cuerpo,
            "cta": "¿Le interesa ver cuáles son en el caso de ustedes?",
        }

    # ── 5. Inactividad prolongada (>=6 meses) — ANTES de wr_bajo_lp ──────────
    # Fix Agent 3: LEAD #24 (Ambienta Diseño Y Obras) tenía wr_bajo_lp pero
    # corresponde a inactivo (n_LP=4, dias=259). Al mover inactivo aquí,
    # se evalúa correctamente cuando n_lp<5.
    if dias >= 180:
        m = meses(dias)
        return {
            "tipo": "inactivo",
            "cuerpo": (
                f"Su empresa lleva {m} meses sin postular en Mercado Público. "
                f"En ese período salieron licitaciones del rubro en su región "
                f"donde están compitiendo sus rivales directos."
            ),
            "cta": "¿Le interesa saber cuáles son y quiénes las están ganando?",
        }

    # ── 6. Win rate bajo con LP ───────────────────────────────────────────────
    if wr < 0.20 and n_lp >= 3:
        gap_pp = int(round(wr_gap * 100))
        return {
            "tipo": "wr_bajo_lp",
            "cuerpo": (
                f"Su empresa ha postulado a {n_lp} licitaciones LP (contratos sobre $66M) "
                f"y la tasa de adjudicación es {pct(wr)}, {gap_pp} puntos por debajo del promedio del rubro ({pct(INDUSTRY_WR_MEDIAN)}).\n\n"
                f"En contratos de ese tamaño, esa brecha son varios contratos anuales que están quedando en otras manos. "
                f"Los factores que la explican son medibles con el historial de esas bases."
            ),
            "cta": "¿Le interesa ver dónde está la diferencia?",
        }

    # ── 7. Tasa de pérdida alta ───────────────────────────────────────────────
    if loss_rate >= 0.40 and total_lost >= 5:
        return {
            "tipo": "loss_concentrado",
            "cuerpo": (
                f"Su empresa perdió {total_lost} licitaciones en el período analizado. "
                f"En ese tipo de concentración de pérdidas casi siempre hay un patrón en la propuesta "
                f"— no solo en precio — que se puede identificar comparando las bases ganadoras."
            ),
            "cta": "¿Le interesa ver qué está marcando la diferencia?",
        }

    # ── 8. Win rate bajo general ──────────────────────────────────────────────
    if wr < 0.19:
        gap_pp = int(round(wr_gap * 100))
        return {
            "tipo": "wr_bajo",
            "cuerpo": (
                f"Su empresa tiene {total_wins} adjudicadas de {total_bids} postulaciones "
                f"— tasa de {pct(wr)}, con el rubro en {pct(INDUSTRY_WR_MEDIAN)}.\n\n"
                f"En las licitaciones no adjudicadas hay factores concretos que se pueden identificar "
                f"cruzando esas bases con las de los ganadores."
            ),
            "cta": "¿Le interesa ver cuáles son?",
        }

    # ── 9. Rival único ────────────────────────────────────────────────────────
    if rival1 and total_lost >= 3:
        return {
            "tipo": "rival_unico",
            "cuerpo": (
                f"Revisé las bases de las licitaciones donde su empresa no se adjudicó. "
                f"En {total_lost} de ellas, {rival1} fue quien ganó.\n\n"
                f"Con esos datos se puede identificar exactamente qué diferenció esas propuestas."
            ),
            "cta": "¿Le interesa ver el análisis?",
        }

    # ── 10. Default ───────────────────────────────────────────────────────────
    return {
        "tipo": "default",
        "cuerpo": (
            f"Revisé el historial de su empresa en Mercado Público: "
            f"{total_wins} adjudicadas de {total_bids} postulaciones "
            f"— tasa de {pct(wr)}, con el rubro en {pct(INDUSTRY_WR_MEDIAN)}.\n\n"
            f"En las licitaciones no adjudicadas hay factores concretos que se pueden identificar "
            f"cruzando esas bases con las de los ganadores."
        ),
        "cta": "¿Le interesa ver cuáles son?",
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

    # Los 45 leads WSP
    wsp = verified[verified["wsp_probable"] == "alta"].copy()
    print(f"Leads WSP: {len(wsp)}")

    # Columnas de loss que necesitamos
    loss_cols = [
        "rut", "win_rate", "total_bids", "total_wins", "monto_total",
        "n_LP", "total_lost_loss", "loss_rate",
        "top_rival_1_name", "top_rival_1_count",
        "top_rival_2_name", "top_rival_2_count",
        "n_distinct_rivals_loss", "dias_desde_ultima",
        "xgb_predicted_wr",
    ]
    loss_sub  = loss[loss_cols].copy()
    wsp_clean = wsp.drop(columns=["win_rate", "total_bids"], errors="ignore")
    df = wsp_clean.merge(loss_sub, on="rut", how="left")

    # Nombre humanizado
    df["empresa_display"] = df["nombre"].apply(humanizar)

    # Generar mensajes
    mensajes  = []
    wsp_links = []
    tipos     = []

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

    # ── Guardar XLSX v4 ───────────────────────────────────────────────────────
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

        otros = verified[verified["wsp_probable"] != "alta"]
        otros.to_excel(writer, sheet_name="Otros Leads", index=False)
    print(f"XLSX: {OUT_XLSX}")

    # ── Guardar TXT v4 ────────────────────────────────────────────────────────
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for i, (_, row) in enumerate(df.sort_values("outreach_rank").iterrows(), 1):
            f.write(f"{'='*72}\n")
            f.write(f"LEAD #{i:02d} | Rank #{int(row['outreach_rank']):02d} | {row['empresa_display']}\n")
            f.write(f"RUT: {row['rut']} | Tel: {row['telefono_normalizado']}\n")
            f.write(
                f"Insight: {row['insight_tipo']} | WR: {pct(float(row['win_rate'] or 0))}"
                f" | LP: {int(row['n_LP'] or 0)} | Perdidas: {int(row['total_lost_loss'] or 0)}"
                f" | Dias: {int(row['dias_desde_ultima'] or 0)}\n"
            )
            f.write(f"Link: {row['wsp_link']}\n")
            f.write(f"{'─'*72}\n")
            f.write(row["wsp_mensaje"])
            f.write(f"\n{'='*72}\n\n")
    print(f"TXT: {OUT_TXT}")

    # ── Reporte consola ───────────────────────────────────────────────────────
    print("\n=== DISTRIBUCION DE INSIGHTS v4 ===")
    dist = df["insight_tipo"].value_counts()
    for tipo, cnt in dist.items():
        print(f"  {tipo:22} {cnt:3} leads")

    print("\n=== MUESTRA (primeros 8 mensajes por ranking) ===")
    for i, (_, row) in enumerate(df.sort_values("outreach_rank").head(8).iterrows(), 1):
        print(f"\n{'='*65}")
        print(f"[{i}] {row['empresa_display']} | Tipo: {row['insight_tipo']}")
        print(f"    WR={pct(float(row['win_rate'] or 0))} | LP={int(row['n_LP'] or 0)} | Perdidas={int(row['total_lost_loss'] or 0)} | Dias={int(row['dias_desde_ultima'] or 0)}")
        print(f"{'─'*65}")
        print(row["wsp_mensaje"])


if __name__ == "__main__":
    main()
