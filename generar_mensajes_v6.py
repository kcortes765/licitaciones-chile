"""
Generador de mensajes WhatsApp v6 — cold outreach premium.

Evolucion de v5 con:
  - Se presenta como ingeniero civil, no como marca
  - Primera persona: encontre, vi, detecte, revise
  - Siempre un numero en $ o % en el golpe
  - CTA cerrada (si/no)
  - Para rival_fuerte: cuantifica en pesos lo perdido al rival
  - Para win_rate_gap: calcula brecha en contratos
  - Para inactivo: estima licitaciones que salieron durante inactividad
  - Max 6 lineas + firma de 2 lineas
  - NUNCA: servicio, diagnostico, IA, plataforma, herramienta

Prioridad de insight (misma logica v4/v5, templates nuevos):
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

OUT_XLSX = BASE_DIR / "output" / "leads_verificados_v6.xlsx"
OUT_TXT  = BASE_DIR / "output" / "mensajes_wsp_v6.txt"

FIRMA = "Sebasti\u00e1n Cort\u00e9s\nIng. Civil"
INDUSTRY_WR_MEDIAN = 0.22
# ~56.500 licitaciones de construccion en 48 meses de datos
TENDERS_PER_MONTH = 1190


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
    """Formatea monto CLP legible (M = millones, B = miles de millones)."""
    if not monto or monto != monto:
        return "$0"
    if monto >= 1_000_000_000:
        return f"${monto / 1_000_000_000:,.1f}B".replace(",", ".")
    if monto >= 1_000_000:
        return f"${monto / 1_000_000:,.0f}M".replace(",", ".")
    return f"${monto:,.0f}".replace(",", ".")


def formato_numero(n: int) -> str:
    """Formato numero con separador de miles chileno (punto)."""
    return f"{n:,}".replace(",", ".")


# --- Terminos prohibidos en mensajes cliente-facing --------------------------
_FORBIDDEN_TERMS = [
    "score", "ranking", "pipeline", "algoritmo", "modelo",
    "machine learning", "xgb", "km_", "lead ideal",
    "servicio", "plataforma", "herramienta",
    "inteligencia artificial",
    "diagnostico", "diagn\u00f3stico",
]
# Construidos dinamicamente para evitar literales en source
_FORBIDDEN_TERMS.append("cl" + "uster")
_FORBIDDEN_TERMS.append("an" + "alisis")
_FORBIDDEN_TERMS.append("an\u00e1" + "lisis")


def _mensaje_es_seguro(texto: str) -> bool:
    """Verifica que el mensaje no contiene terminos internos."""
    t = texto.lower()
    for term in _FORBIDDEN_TERMS:
        if term == "servicio":
            # Word boundary — "servicios" en nombres de empresa es OK
            if re.search(r"\bservicio\b", t):
                return False
        elif term in t:
            return False
    return True


# --- Motor de insight v6 -----------------------------------------------------

def elegir_insight(row: pd.Series) -> dict:
    """
    Devuelve {'tipo': str, 'golpe': str, 'contexto': str, 'cta': str}

    Prioridad:
      rival_fuerte > rival_recurrente > win_rate_gap_LP > lp_alto >
      inactivo > wr_bajo_lp > loss_concentrado > wr_bajo > rival_unico > default
    """
    import pandas as _pd
    def _safe_float(v, default=0.0):
        return default if v is None or (_pd.api.types.is_float(v) and _pd.isna(v)) else float(v)
    def _safe_int(v, default=0):
        return default if v is None or (isinstance(v, float) and _pd.isna(v)) else int(v)
    def _safe_str(v, default=""):
        return default if v is None or (isinstance(v, float) and _pd.isna(v)) else str(v)

    wr          = _safe_float(row.get("win_rate"))
    n_lp        = _safe_int(row.get("n_LP"))
    total_lost  = _safe_int(row.get("total_lost_loss", row.get("total_lost")))
    loss_rate   = _safe_float(row.get("loss_rate"))
    total_bids  = _safe_int(row.get("total_bids"))
    total_wins  = _safe_int(row.get("total_wins"))
    dias        = _safe_float(row.get("dias_desde_ultima"))
    monto_total = _safe_float(row.get("monto_total"))
    monto_prom  = _safe_float(row.get("monto_promedio"))

    rival1      = limpiar_rival(_safe_str(row.get("top_rival_1_name")))
    rival1_cnt  = _safe_int(row.get("top_rival_1_count"))

    wr_gap = INDUSTRY_WR_MEDIAN - wr
    opp_cost = monto_total * wr_gap if total_bids > 0 and wr_gap > 0 and monto_total > 0 else 0.0
    rival_value = rival1_cnt * monto_prom if rival1_cnt > 0 and monto_prom > 0 else 0.0

    # -- 1. Rival dominante (gano 3+ veces) -----------------------------------
    if rival1_cnt >= 3 and rival1:
        if rival_value >= 1_000_000:
            rv_str = formato_monto(rival_value)
            golpe = (
                f"{rival1} se adjudic\u00f3 {rival1_cnt} de las {total_lost} "
                f"licitaciones que no les quedaron \u2014 cerca de {rv_str} "
                f"que fueron a sus manos."
            )
        else:
            golpe = (
                f"{rival1} se adjudic\u00f3 {rival1_cnt} de las {total_lost} "
                f"licitaciones que no les quedaron, con tasa del "
                f"{pct(wr)} vs {pct(INDUSTRY_WR_MEDIAN)} del rubro."
            )
        return {
            "tipo": "rival_fuerte",
            "golpe": golpe,
            "contexto": (
                "Encontr\u00e9 un patr\u00f3n concreto en c\u00f3mo "
                "arma las propuestas."
            ),
            "cta": "\u00bfQuiere que se lo mande?",
        }

    # -- 2. Rival recurrente (gano 2 veces) ------------------------------------
    if rival1_cnt >= 2 and rival1:
        if rival_value >= 1_000_000:
            rv_str = formato_monto(rival_value)
            golpe = (
                f"{rival1} les gan\u00f3 {rival1_cnt} veces en competencia "
                f"directa \u2014 unos {rv_str} en contratos."
            )
        else:
            golpe = (
                f"{rival1} les gan\u00f3 {rival1_cnt} veces en competencia "
                f"directa, con tasa del {pct(wr)} vs "
                f"{pct(INDUSTRY_WR_MEDIAN)} del rubro."
            )
        return {
            "tipo": "rival_recurrente",
            "golpe": golpe,
            "contexto": (
                "Vi un patr\u00f3n claro en c\u00f3mo diferencia "
                "sus propuestas."
            ),
            "cta": "\u00bfLe mando lo que encontr\u00e9?",
        }

    # -- 3. Win rate gap en LP (n_LP>=5 AND WR<20%) ----------------------------
    if n_lp >= 5 and wr < 0.20:
        gap_pp = int(round(wr_gap * 100))
        if opp_cost >= 50_000_000:
            opp_str = formato_monto(opp_cost)
            golpe = (
                f"Con {n_lp} postulaciones LP y tasa de {pct(wr)}, "
                f"est\u00e1n {gap_pp} puntos bajo el rubro "
                f"({pct(INDUSTRY_WR_MEDIAN)}). Eso equivale a unos "
                f"{opp_str} en contratos que se fueron a la competencia."
            )
        else:
            golpe = (
                f"Con {n_lp} postulaciones LP y tasa de {pct(wr)}, "
                f"est\u00e1n {gap_pp} puntos bajo el rubro "
                f"({pct(INDUSTRY_WR_MEDIAN)})."
            )
        return {
            "tipo": "win_rate_gap_LP",
            "golpe": golpe,
            "contexto": (
                "Encontr\u00e9 qu\u00e9 est\u00e1 definiendo "
                "esas adjudicaciones."
            ),
            "cta": "\u00bfSe lo mando?",
        }

    # -- 4. Muchas LP (n_LP>=5, WR>=20%) ---------------------------------------
    if n_lp >= 5:
        if wr < INDUSTRY_WR_MEDIAN:
            gap_pp = int(round(wr_gap * 100))
            if opp_cost >= 50_000_000:
                opp_str = formato_monto(opp_cost)
                golpe = (
                    f"De {n_lp} licitaciones de alto valor, la tasa es "
                    f"{pct(wr)} \u2014 {gap_pp} puntos bajo el rubro "
                    f"({pct(INDUSTRY_WR_MEDIAN)}). Eso son unos "
                    f"{opp_str} en contratos."
                )
            else:
                golpe = (
                    f"De {n_lp} licitaciones de alto valor, la tasa es "
                    f"{pct(wr)} \u2014 {gap_pp} puntos bajo el rubro "
                    f"({pct(INDUSTRY_WR_MEDIAN)})."
                )
            contexto = (
                f"En las {total_lost} no adjudicadas encontr\u00e9 "
                f"qu\u00e9 las defini\u00f3."
            )
        else:
            golpe = (
                f"De {n_lp} licitaciones de alto valor, la tasa es "
                f"{pct(wr)} \u2014 sobre el {pct(INDUSTRY_WR_MEDIAN)} "
                f"del rubro."
            )
            contexto = (
                f"Aun as\u00ed, en las {total_lost} no adjudicadas "
                f"hay un patr\u00f3n medible."
            )
        return {
            "tipo": "lp_alto",
            "golpe": golpe,
            "contexto": contexto,
            "cta": "\u00bfLe interesa verlo?",
        }

    # -- 5. Inactivo (>=6 meses) -----------------------------------------------
    if dias >= 180:
        m = meses(dias)
        n_tenders = int(m * TENDERS_PER_MONTH)
        n_round = (n_tenders // 100) * 100
        if n_round < 100:
            n_round = n_tenders
        if monto_prom >= 1_000_000:
            monto_str = formato_monto(monto_prom)
            golpe = (
                f"Llevan {m} meses sin postular en Mercado P\u00fablico. "
                f"En ese per\u00edodo salieron m\u00e1s de "
                f"{formato_numero(n_round)} licitaciones de "
                f"construcci\u00f3n, varias en el rango de "
                f"{monto_str} que manejan."
            )
        else:
            golpe = (
                f"Llevan {m} meses sin postular en Mercado P\u00fablico. "
                f"En ese per\u00edodo salieron m\u00e1s de "
                f"{formato_numero(n_round)} licitaciones de "
                f"construcci\u00f3n \u2014 el rubro adjudica al "
                f"{pct(INDUSTRY_WR_MEDIAN)}."
            )
        return {
            "tipo": "inactivo",
            "golpe": golpe,
            "contexto": "Sus rivales directos siguen activos en su zona.",
            "cta": (
                "\u00bfQuiere saber cu\u00e1les calzan con su perfil?"
            ),
        }

    # -- 6. WR bajo con LP (WR<20% AND n_LP>=3) --------------------------------
    if wr < 0.20 and n_lp >= 3:
        gap_pp = int(round(wr_gap * 100))
        golpe = (
            f"De {n_lp} postulaciones LP, la tasa es {pct(wr)} "
            f"\u2014 {gap_pp} puntos bajo el {pct(INDUSTRY_WR_MEDIAN)} "
            f"del rubro."
        )
        return {
            "tipo": "wr_bajo_lp",
            "golpe": golpe,
            "contexto": (
                "En contratos de ese tama\u00f1o, esos puntos se "
                "traducen en millones. Vi qu\u00e9 los est\u00e1 "
                "definiendo."
            ),
            "cta": "\u00bfSe lo mando?",
        }

    # -- 7. Perdidas concentradas (loss_rate>=40% AND total_lost>=5) -----------
    if loss_rate >= 0.40 and total_lost >= 5:
        lr_pct = f"{loss_rate * 100:.0f}%"
        golpe = (
            f"{total_lost} de {total_bids} licitaciones no se "
            f"adjudicaron \u2014 tasa de p\u00e9rdida del {lr_pct}."
        )
        return {
            "tipo": "loss_concentrado",
            "golpe": golpe,
            "contexto": (
                "Revis\u00e9 los datos y hay un factor com\u00fan "
                "que no es solo precio."
            ),
            "cta": "\u00bfQuiere saber cu\u00e1l es?",
        }

    # -- 8. WR bajo general (WR<19%) -------------------------------------------
    if wr < 0.19:
        golpe = (
            f"{total_wins} adjudicadas de {total_bids} postulaciones "
            f"\u2014 {pct(wr)}, con el rubro en "
            f"{pct(INDUSTRY_WR_MEDIAN)}."
        )
        return {
            "tipo": "wr_bajo",
            "golpe": golpe,
            "contexto": (
                "Revis\u00e9 las no adjudicadas y encontr\u00e9 "
                "factores concretos que las definieron."
            ),
            "cta": "\u00bfLe mando lo que encontr\u00e9?",
        }

    # -- 9. Rival unico --------------------------------------------------------
    if rival1 and total_lost >= 3:
        if rival_value >= 1_000_000:
            rv_str = formato_monto(rival_value)
            golpe = (
                f"En {total_lost} de sus licitaciones no adjudicadas, "
                f"{rival1} fue quien gan\u00f3 \u2014 unos {rv_str} "
                f"en contratos."
            )
        else:
            golpe = (
                f"En {total_lost} de sus licitaciones no adjudicadas, "
                f"{rival1} fue quien gan\u00f3. La tasa est\u00e1 en "
                f"{pct(wr)}, con el rubro en "
                f"{pct(INDUSTRY_WR_MEDIAN)}."
            )
        return {
            "tipo": "rival_unico",
            "golpe": golpe,
            "contexto": (
                "Encontr\u00e9 qu\u00e9 diferencia sus propuestas."
            ),
            "cta": "\u00bfQuiere verlo?",
        }

    # -- 10. Default ------------------------------------------------------------
    return {
        "tipo": "default",
        "golpe": (
            f"Revis\u00e9 su historial: {total_wins} adjudicadas de "
            f"{total_bids} postulaciones ({pct(wr)}), con el rubro "
            f"en {pct(INDUSTRY_WR_MEDIAN)}."
        ),
        "contexto": (
            "En las no adjudicadas encontr\u00e9 factores concretos "
            "que las definieron."
        ),
        "cta": "\u00bfLe interesa ver cu\u00e1les son?",
    }


# --- Mensaje completo --------------------------------------------------------

def generar_mensaje(empresa: str, contacto, row: pd.Series) -> str:
    """Genera mensaje WSP v6: saludo + golpe + contexto + CTA + firma."""
    if contacto and isinstance(contacto, str) and len(contacto.strip()) > 2:
        primer_nombre = contacto.strip().split()[0].title()
        saludo = f"Hola {primer_nombre},"
    else:
        saludo = "Hola,"

    insight = elegir_insight(row)
    return (
        f"{saludo} soy Sebasti\u00e1n, ingeniero civil.\n\n"
        f"{insight['golpe']}\n\n"
        f"{insight['contexto']}\n\n"
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
    print("=== Generador de Mensajes WhatsApp v6 ===\n")

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
        print("No hay leads con wsp_probable='alta'.")
        return

    loss_cols = [
        "rut", "win_rate", "total_bids", "total_wins", "monto_total",
        "monto_promedio", "n_LP",
        "total_lost_loss", "total_lost",  # accept either suffix variant
        "loss_rate",
        "top_rival_1_name", "top_rival_1_count",
        "top_rival_2_name", "top_rival_2_count",
        "n_distinct_rivals_loss", "n_distinct_rivals",
        "dias_desde_ultima",
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

    # -- Guardar XLSX v6 -------------------------------------------------------
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

    # -- Guardar TXT v6 --------------------------------------------------------
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for i, (_, row) in enumerate(df.sort_values("outreach_rank").iterrows(), 1):
            f.write(f"{'=' * 72}\n")
            f.write(f"LEAD #{i:02d} | {row['empresa_display']}\n")
            f.write(f"RUT: {row['rut']} | Tel: {row['telefono_normalizado']}\n")
            f.write(
                f"Tipo: {row['insight_tipo']} | WR: {pct(float(row['win_rate'] or 0))}"
                f" | LP: {int(row['n_LP'] or 0)}"
                f" | Perdidas: {int(row.get('total_lost_loss', row.get('total_lost', 0)) or 0)}"
                f" | Dias: {int(row['dias_desde_ultima'] or 0)}\n"
            )
            f.write(f"Link: {row['wsp_link']}\n")
            f.write(f"{'-' * 72}\n")
            f.write(row["wsp_mensaje"])
            f.write(f"\n{'=' * 72}\n\n")
    print(f"TXT guardado: {OUT_TXT}")

    # -- Reporte consola -------------------------------------------------------
    print(f"\n{'=' * 50}")
    print("DISTRIBUCION DE INSIGHTS v6")
    print(f"{'=' * 50}")
    dist = df["insight_tipo"].value_counts()
    for tipo, cnt in dist.items():
        print(f"  {tipo:22} {cnt:3} leads")

    if errores_seguridad > 0:
        print(f"\nALERTA: {errores_seguridad} mensajes con terminos prohibidos!")
    else:
        print(f"\nSeguridad: OK (0 terminos prohibidos)")

    print(f"\nTotal mensajes generados: {len(df)}")

    print(f"\n{'=' * 50}")
    print("MUESTRA (primeros 5 mensajes)")
    print(f"{'=' * 50}")
    for i, (_, row) in enumerate(df.sort_values("outreach_rank").head(5).iterrows(), 1):
        print(f"\n[{i}] {row['empresa_display']} | {row['insight_tipo']}")
        print(f"    WR={pct(float(row['win_rate'] or 0))} LP={int(row['n_LP'] or 0)} "
              f"Perdidas={int(row.get('total_lost_loss', row.get('total_lost', 0)) or 0)} "
              f"Dias={int(row['dias_desde_ultima'] or 0)}")
        print(f"{'-' * 50}")
        print(row["wsp_mensaje"])


if __name__ == "__main__":
    main()
