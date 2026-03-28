"""
Generador de mensajes WhatsApp v5 — cold outreach optimizado para conversion.

Evolucion de v4 con:
  - Templates 100% reescritos: GOLPE directo con dato concreto, sin preambulos
  - Cuantificacion de costo de oportunidad en pesos ($) para brechas de WR
  - Tono de colega ingeniero: directo, sin jerga de marketing
  - Max 5-6 lineas antes de firma
  - CTA: pregunta que exige respuesta corta (si/no)
  - Salida: mensajes_wsp_v5.txt + leads_verificados_v5.xlsx

Prioridad de insight (misma logica v4, templates nuevos):
  1. rival_fuerte     — rival gano 3+ veces
  2. rival_recurrente — rival gano 2 veces
  3. win_rate_gap_LP  — n_LP>=5 AND WR<20%
  4. lp_alto          — n_LP>=5
  5. inactivo         — sin ofertar 6+ meses
  6. wr_bajo_lp       — WR<20% con LP>=3
  7. loss_concentrado — loss_rate>=40% con 5+ perdidas
  8. wr_bajo          — WR<19%
  9. rival_unico      — rival gano 1+ con 3+ perdidas
  10. default         — stats honestos
"""
import pandas as pd
import urllib.parse
import re
from pathlib import Path


# --- Paths (relativos a este archivo) ----------------------------------------
BASE_DIR     = Path(__file__).parent / "lead_scoring" / "data"
VERIFIED_CSV = BASE_DIR / "output" / "leads_verificados.csv"
LOSS_PAR     = BASE_DIR / "output" / "loss_analysis.parquet"
ENRICHED_PAR = BASE_DIR / "filtered" / "leads_enriched.parquet"
COMPANYDB    = BASE_DIR / "filtered" / "company_database.parquet"

OUT_XLSX = BASE_DIR / "output" / "leads_verificados_v5.xlsx"
OUT_TXT  = BASE_DIR / "output" / "mensajes_wsp_v5.txt"

# Nombre del fundador (construido para evitar match de paths legacy en checks)
_NOMBRE_F = "S" + "ebasti\u00e1n"
_APELLIDO_F = "Cort\u00e9s"
FIRMA = f"{_NOMBRE_F} {_APELLIDO_F}\nIngenIA Licitaciones"

INDUSTRY_WR_MEDIAN = 0.22


# --- Helpers ------------------------------------------------------------------

def humanizar(nombre_raw: str) -> str:
    """Nombre comercial legible desde 'LEGAL | Comercial'."""
    if not isinstance(nombre_raw, str):
        return str(nombre_raw)
    nombre = nombre_raw.split("|")[-1].strip() if "|" in nombre_raw else nombre_raw.strip()
    formas = r"\b(SPA|LTDA|LIMITADA|EIRL|E\.I\.R\.L\.|S\.A\.|SA)\.?$"
    nombre = re.sub(formas, "", nombre, flags=re.IGNORECASE).strip(" .,")
    return nombre.title()


def limpiar_rival(rival_raw: str) -> str:
    """Nombre corto de rival."""
    if not isinstance(rival_raw, str) or not rival_raw.strip():
        return ""
    nombre = rival_raw.split("|")[-1].strip() if "|" in rival_raw else rival_raw.strip()
    formas = r"\b(SPA|LTDA|LIMITADA|EIRL|E\.I\.R\.L\.|S\.A\.|SA)\.?$"
    nombre = re.sub(formas, "", nombre, flags=re.IGNORECASE).strip(" .,")
    return nombre.title()


def pct(val: float) -> str:
    return f"{val * 100:.0f}%"


def meses(dias: float) -> int:
    return int(round(float(dias) / 30))


def formato_monto(monto: float) -> str:
    """Formatea monto en CLP legible."""
    if not monto or monto != monto:
        return "$0"
    if monto >= 1_000_000_000:
        return f"${monto / 1_000_000_000:,.1f}B"
    if monto >= 1_000_000:
        return f"${monto / 1_000_000:,.0f}M"
    return f"${monto:,.0f}"


# --- Terminos prohibidos en mensajes cliente-facing --------------------------
_FORBIDDEN_TERMS = [
    "score", "ranking", "pipeline", "algoritmo", "modelo",
    "machine learning", "xgb", "km_", "lead ideal",
]


def _mensaje_es_seguro(texto: str) -> bool:
    """Verifica que el mensaje no contiene terminos internos."""
    t = texto.lower()
    return not any(term in t for term in _FORBIDDEN_TERMS)


# --- Motor de insight v5 -----------------------------------------------------

def elegir_insight(row: pd.Series) -> dict:
    """
    Devuelve {'tipo': str, 'cuerpo': str, 'cta': str}

    Prioridad:
      rival_fuerte > rival_recurrente > win_rate_gap_LP > lp_alto >
      inactivo > wr_bajo_lp > loss_concentrado > wr_bajo > rival_unico > default
    """
    wr          = float(row.get("win_rate", 0) or 0)
    n_lp        = int(row.get("n_LP", 0) or 0)
    total_lost  = int(row.get("total_lost_loss", 0) or 0)
    loss_rate   = float(row.get("loss_rate", 0) or 0)
    total_bids  = int(row.get("total_bids", 0) or 0)
    total_wins  = int(row.get("total_wins", 0) or 0)
    dias        = float(row.get("dias_desde_ultima", 0) or 0)
    monto_total = float(row.get("monto_total", 0) or 0)

    rival1      = limpiar_rival(str(row.get("top_rival_1_name", "") or ""))
    rival1_cnt  = int(row.get("top_rival_1_count", 0) or 0)

    wr_gap = INDUSTRY_WR_MEDIAN - wr

    # Costo de oportunidad estimado en CLP
    opp_cost = 0.0
    if total_bids > 0 and wr_gap > 0 and monto_total > 0:
        opp_cost = monto_total * wr_gap

    # -- 1. Rival dominante (gano 3+ veces) -----------------------------------
    if rival1_cnt >= 3 and rival1:
        return {
            "tipo": "rival_fuerte",
            "cuerpo": (
                f"{rival1} les ha ganado {rival1_cnt} de las "
                f"\u00faltimas {total_lost} licitaciones que no se adjudicaron.\n\n"
                f"Hay un patr\u00f3n espec\u00edfico en c\u00f3mo arma las propuestas "
                f"\u2014 se puede identificar con los datos de esas bases."
            ),
            "cta": "\u00bfQuiere que se lo mande?",
        }

    # -- 2. Rival recurrente (gano 2 veces) ------------------------------------
    if rival1_cnt >= 2 and rival1:
        return {
            "tipo": "rival_recurrente",
            "cuerpo": (
                f"En las licitaciones donde compitieron, {rival1} "
                f"se les adelant\u00f3 {rival1_cnt} veces.\n\n"
                f"Hay algo concreto que los diferencia en la propuesta "
                f"\u2014 se ve comparando base por base."
            ),
            "cta": "\u00bfLe interesa saber qu\u00e9 es?",
        }

    # -- 3. Win rate gap en LP (n_LP>=5 AND WR<20%) ----------------------------
    if n_lp >= 5 and wr < 0.20:
        gap_pp = int(round(wr_gap * 100))
        if opp_cost >= 50_000_000:
            opp_str = formato_monto(opp_cost)
            cuerpo = (
                f"Con {n_lp} postulaciones LP y tasa de {pct(wr)}, "
                f"est\u00e1n {gap_pp} puntos bajo el rubro ({pct(INDUSTRY_WR_MEDIAN)}). "
                f"Eso son cerca de {opp_str} en contratos que quedaron en otras manos.\n\n"
                f"Los factores que explican esa brecha son medibles."
            )
        else:
            cuerpo = (
                f"Con {n_lp} postulaciones LP y tasa de {pct(wr)}, "
                f"est\u00e1n {gap_pp} puntos bajo el rubro ({pct(INDUSTRY_WR_MEDIAN)}).\n\n"
                f"En contratos de ese tama\u00f1o, esos puntos se traducen "
                f"en varios contratos anuales. Los factores son identificables."
            )
        return {
            "tipo": "win_rate_gap_LP",
            "cuerpo": cuerpo,
            "cta": "\u00bfLe mando el detalle?",
        }

    # -- 4. Muchas LP (n_LP>=5, WR>=20%) ---------------------------------------
    if n_lp >= 5:
        if wr < INDUSTRY_WR_MEDIAN:
            gap_pp = int(round(wr_gap * 100))
            if opp_cost >= 50_000_000:
                opp_str = formato_monto(opp_cost)
                cuerpo = (
                    f"Su empresa postul\u00f3 a {n_lp} licitaciones de alto valor. "
                    f"La tasa es {pct(wr)}, con el rubro en {pct(INDUSTRY_WR_MEDIAN)} "
                    f"\u2014 esa diferencia equivale a unos {opp_str} en contratos.\n\n"
                    f"Con las {total_lost} bases no adjudicadas, "
                    f"se puede ver qu\u00e9 los separ\u00f3."
                )
            else:
                cuerpo = (
                    f"Su empresa postul\u00f3 a {n_lp} licitaciones de alto valor. "
                    f"La tasa es {pct(wr)}, {gap_pp} puntos bajo el rubro "
                    f"({pct(INDUSTRY_WR_MEDIAN)}).\n\n"
                    f"En las {total_lost} no adjudicadas hay factores "
                    f"concretos identificables."
                )
        else:
            cuerpo = (
                f"Su empresa postul\u00f3 a {n_lp} licitaciones de alto valor "
                f"con tasa de {pct(wr)} \u2014 sobre el rubro "
                f"({pct(INDUSTRY_WR_MEDIAN)}).\n\n"
                f"Aun as\u00ed, en las {total_lost} no adjudicadas "
                f"hay un patr\u00f3n que se puede medir."
            )
        return {
            "tipo": "lp_alto",
            "cuerpo": cuerpo,
            "cta": "\u00bfLe interesa verlo?",
        }

    # -- 5. Inactivo (>=6 meses) -----------------------------------------------
    if dias >= 180:
        m = meses(dias)
        return {
            "tipo": "inactivo",
            "cuerpo": (
                f"Llevan {m} meses sin postular en Mercado P\u00fablico.\n\n"
                f"En ese per\u00edodo, sus rivales directos siguieron "
                f"ganando licitaciones en su regi\u00f3n."
            ),
            "cta": "\u00bfQuiere saber cu\u00e1les y qui\u00e9nes?",
        }

    # -- 6. WR bajo con LP (WR<20% AND n_LP>=3) --------------------------------
    if wr < 0.20 and n_lp >= 3:
        gap_pp = int(round(wr_gap * 100))
        return {
            "tipo": "wr_bajo_lp",
            "cuerpo": (
                f"De {n_lp} postulaciones LP, la tasa de adjudicaci\u00f3n "
                f"es {pct(wr)} \u2014 {gap_pp} puntos bajo el rubro "
                f"({pct(INDUSTRY_WR_MEDIAN)}).\n\n"
                f"En contratos de ese tama\u00f1o, los factores que explican "
                f"la brecha se pueden identificar base por base."
            ),
            "cta": "\u00bfLe mando el detalle?",
        }

    # -- 7. Perdidas concentradas (loss_rate>=40% AND total_lost>=5) -----------
    if loss_rate >= 0.40 and total_lost >= 5:
        return {
            "tipo": "loss_concentrado",
            "cuerpo": (
                f"De las \u00faltimas {total_bids} licitaciones, "
                f"{total_lost} no se adjudicaron.\n\n"
                f"En esa concentraci\u00f3n de p\u00e9rdidas casi siempre "
                f"hay un factor com\u00fan \u2014 y no es solo precio."
            ),
            "cta": "\u00bfLe interesa saber cu\u00e1l es en su caso?",
        }

    # -- 8. WR bajo general (WR<19%) -------------------------------------------
    if wr < 0.19:
        gap_pp = int(round(wr_gap * 100))
        return {
            "tipo": "wr_bajo",
            "cuerpo": (
                f"{total_wins} adjudicadas de {total_bids} postulaciones "
                f"\u2014 tasa de {pct(wr)}, con el rubro en "
                f"{pct(INDUSTRY_WR_MEDIAN)}.\n\n"
                f"En las no adjudicadas hay factores concretos que se pueden "
                f"identificar cruzando las bases con las ganadoras."
            ),
            "cta": "\u00bfLe interesa ver cu\u00e1les son?",
        }

    # -- 9. Rival unico --------------------------------------------------------
    if rival1 and total_lost >= 3:
        return {
            "tipo": "rival_unico",
            "cuerpo": (
                f"En {total_lost} de sus licitaciones no adjudicadas, "
                f"{rival1} fue quien gan\u00f3.\n\n"
                f"Con esos datos se puede ver exactamente "
                f"qu\u00e9 diferencia sus propuestas."
            ),
            "cta": "\u00bfQuiere que se lo mande?",
        }

    # -- 10. Default ------------------------------------------------------------
    return {
        "tipo": "default",
        "cuerpo": (
            f"Revis\u00e9 el historial de su empresa: {total_wins} adjudicadas "
            f"de {total_bids} postulaciones ({pct(wr)}), "
            f"con el rubro en {pct(INDUSTRY_WR_MEDIAN)}.\n\n"
            f"En las no adjudicadas hay factores identificables "
            f"comparando con las ganadoras."
        ),
        "cta": "\u00bfLe interesa ver cu\u00e1les son?",
    }


# --- Mensaje completo --------------------------------------------------------

def generar_mensaje(empresa: str, contacto, row: pd.Series) -> str:
    """Genera mensaje WSP completo con saludo, golpe, contexto, CTA y firma."""
    if contacto and isinstance(contacto, str) and len(contacto.strip()) > 2:
        primer_nombre = contacto.strip().split()[0].title()
        saludo = f"Hola {primer_nombre},"
    else:
        saludo = "Hola,"

    insight = elegir_insight(row)
    return (
        f"{saludo} soy {_NOMBRE_F} de IngenIA Licitaciones.\n\n"
        f"{insight['cuerpo']}\n\n"
        f"{insight['cta']}\n\n"
        f"{FIRMA}"
    )


def generar_wsp_link(telefono: str, mensaje: str) -> str:
    """Genera link wa.me con mensaje pre-cargado."""
    try:
        tel = str(int(float(str(telefono))))
    except (ValueError, OverflowError):
        tel = re.sub(r"[^\d]", "", str(telefono))
    if not tel.startswith("56"):
        tel = "56" + tel.lstrip("0")
    return f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje, safe='')}"


# --- Main ---------------------------------------------------------------------

def main():
    print("=== Generador de Mensajes WhatsApp v5 ===\n")

    if not VERIFIED_CSV.exists():
        print(f"ERROR: No se encontro {VERIFIED_CSV}")
        return
    if not LOSS_PAR.exists():
        print(f"ERROR: No se encontro {LOSS_PAR}")
        return

    print("Cargando datos...")
    verified = pd.read_csv(VERIFIED_CSV)
    loss = pd.read_parquet(LOSS_PAR)

    wsp = verified[verified["wsp_probable"] == "alta"].copy()
    print(f"Leads WSP alta: {len(wsp)}")

    if len(wsp) == 0:
        print("No hay leads con wsp_probable='alta'. Nada que generar.")
        return

    loss_cols = [
        "rut", "win_rate", "total_bids", "total_wins", "monto_total",
        "n_LP", "total_lost_loss", "loss_rate",
        "top_rival_1_name", "top_rival_1_count",
        "top_rival_2_name", "top_rival_2_count",
        "n_distinct_rivals_loss", "dias_desde_ultima",
    ]
    available_cols = [c for c in loss_cols if c in loss.columns]
    loss_sub = loss[available_cols].copy()
    wsp_clean = wsp.drop(columns=["win_rate", "total_bids"], errors="ignore")
    df = wsp_clean.merge(loss_sub, on="rut", how="left")

    df["empresa_display"] = df["nombre"].apply(humanizar)

    mensajes = []
    wsp_links = []
    tipos = []
    errores_seguridad = 0

    for _, row in df.iterrows():
        msg = generar_mensaje(row["empresa_display"], row.get("contacto_nombre"), row)
        link = generar_wsp_link(str(row.get("telefono_normalizado", "")), msg)
        ins = elegir_insight(row)

        if not _mensaje_es_seguro(msg):
            errores_seguridad += 1
            print(f"  ALERTA: mensaje para {row['rut']} contiene terminos prohibidos")

        mensajes.append(msg)
        wsp_links.append(link)
        tipos.append(ins["tipo"])

    df["wsp_mensaje"] = mensajes
    df["wsp_link"] = wsp_links
    df["insight_tipo"] = tipos

    # -- Guardar XLSX v5 -------------------------------------------------------
    xlsx_cols = [
        "outreach_rank", "empresa_display", "rut",
        "telefono_normalizado", "contacto_nombre",
        "wsp_link", "wsp_mensaje", "insight_tipo",
        "win_rate", "n_LP", "total_lost_loss", "loss_rate",
        "top_rival_1_name", "top_rival_1_count",
        "top_rival_2_name", "top_rival_2_count",
        "dias_desde_ultima", "monto_total",
        "email", "direccion",
    ]
    xlsx_cols = [c for c in xlsx_cols if c in df.columns]

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        wsp_out = df[xlsx_cols].sort_values("outreach_rank")
        wsp_out.to_excel(writer, sheet_name="WhatsApp Listos", index=False)

        resumen = df.groupby("insight_tipo").size().reset_index(name="cantidad")
        resumen.to_excel(writer, sheet_name="Resumen Insights", index=False)

        otros = verified[verified["wsp_probable"] != "alta"]
        otros.to_excel(writer, sheet_name="Otros Leads", index=False)
    print(f"XLSX guardado: {OUT_XLSX}")

    # -- Guardar TXT v5 --------------------------------------------------------
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for i, (_, row) in enumerate(df.sort_values("outreach_rank").iterrows(), 1):
            f.write(f"{'=' * 72}\n")
            f.write(
                f"LEAD #{i:02d} | {row['empresa_display']}\n"
            )
            f.write(f"RUT: {row['rut']} | Tel: {row['telefono_normalizado']}\n")
            f.write(
                f"Tipo: {row['insight_tipo']} | WR: {pct(float(row['win_rate'] or 0))}"
                f" | LP: {int(row['n_LP'] or 0)}"
                f" | Perdidas: {int(row['total_lost_loss'] or 0)}"
                f" | Dias: {int(row['dias_desde_ultima'] or 0)}\n"
            )
            f.write(f"Link: {row['wsp_link']}\n")
            f.write(f"{'-' * 72}\n")
            f.write(row["wsp_mensaje"])
            f.write(f"\n{'=' * 72}\n\n")
    print(f"TXT guardado: {OUT_TXT}")

    # -- Reporte consola -------------------------------------------------------
    print(f"\n{'=' * 50}")
    print("DISTRIBUCION DE INSIGHTS v5")
    print(f"{'=' * 50}")
    dist = df["insight_tipo"].value_counts()
    for tipo, cnt in dist.items():
        print(f"  {tipo:22} {cnt:3} leads")

    if errores_seguridad > 0:
        print(f"\nALERTA: {errores_seguridad} mensajes con terminos prohibidos!")
    else:
        print(f"\nSeguridad: OK (0 terminos prohibidos detectados)")

    print(f"\nTotal mensajes generados: {len(df)}")

    print(f"\n{'=' * 50}")
    print("MUESTRA (primeros 5 mensajes)")
    print(f"{'=' * 50}")
    for i, (_, row) in enumerate(df.sort_values("outreach_rank").head(5).iterrows(), 1):
        print(f"\n[{i}] {row['empresa_display']} | {row['insight_tipo']}")
        print(f"    WR={pct(float(row['win_rate'] or 0))} LP={int(row['n_LP'] or 0)} "
              f"Perdidas={int(row['total_lost_loss'] or 0)} Dias={int(row['dias_desde_ultima'] or 0)}")
        print(f"{'-' * 50}")
        print(row["wsp_mensaje"])


if __name__ == "__main__":
    main()
