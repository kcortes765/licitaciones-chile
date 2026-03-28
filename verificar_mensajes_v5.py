"""
Verificador de mensajes WhatsApp v5 contra datos reales.

Verifica:
  1. Datos mencionados (rival, %, conteo, meses) vs loss_analysis.parquet
  2. Ausencia de terminos prohibidos (score, cluster, ML, pipeline, ranking, modelo, algoritmo)
  3. Longitud de mensaje (max ~500 chars antes de firma)
  4. CTA con signo de interrogacion
  5. Output: verificacion_v5_report.json
"""
import pandas as pd
import re
import json
from pathlib import Path

# --- Paths -------------------------------------------------------------------
BASE_DIR = Path(__file__).parent / "lead_scoring" / "data"
LOSS_PAR = BASE_DIR / "output" / "loss_analysis.parquet"
MSG_FILE = BASE_DIR / "output" / "mensajes_wsp_v5.txt"
REPORT_OUT = Path(__file__).parent / "verificacion_v5_report.json"

INDUSTRY_WR_MEDIAN = 0.22

# Firma para separar cuerpo de firma
FIRMA_MARKER = "IngenIA Licitaciones"

_FORBIDDEN_TERMS = [
    "score", "ranking", "pipeline", "algoritmo", "modelo",
    "machine learning", "xgb", "km_", "lead ideal", "cluster",
]

MAX_MSG_CHARS_BEFORE_FIRMA = 500


# --- Parsing -----------------------------------------------------------------

def parse_v5_blocks(content: str) -> list:
    """Parsea el archivo v5 txt en bloques de leads."""
    blocks = re.split(r"={60,}", content)
    blocks = [b.strip() for b in blocks if b.strip()]

    leads = []
    for block in blocks:
        lines = block.split("\n")
        header_line = rut_line = tipo_line = link_line = None
        msg_lines = []
        in_msg = False

        for line in lines:
            if re.match(r"LEAD #\d+", line):
                header_line = line
            elif line.startswith("RUT:"):
                rut_line = line
            elif line.startswith("Tipo:"):
                tipo_line = line
            elif line.startswith("Link:"):
                link_line = line
            elif re.match(r"-{40,}", line):
                in_msg = True
            elif in_msg:
                msg_lines.append(line)

        if not header_line:
            continue

        m_header = re.match(r"LEAD #(\d+) \| (.+)", header_line)
        if not m_header:
            continue
        lead_num = int(m_header.group(1))
        empresa = m_header.group(2).strip()

        m_rut = re.match(r"RUT: ([\w-]+)", rut_line) if rut_line else None
        rut = m_rut.group(1).strip() if m_rut else None
        if not rut:
            continue

        insight_type = wr_pct = n_lp = n_perdidas = dias_header = None
        if tipo_line:
            m_tipo = re.match(
                r"Tipo: (\w+) \| WR: (\d+)% \| LP: (\d+) \| Perdidas: (\d+) \| Dias: (\d+)",
                tipo_line,
            )
            if m_tipo:
                insight_type = m_tipo.group(1)
                wr_pct = int(m_tipo.group(2))
                n_lp = int(m_tipo.group(3))
                n_perdidas = int(m_tipo.group(4))
                dias_header = int(m_tipo.group(5))

        msg_text = "\n".join(msg_lines).strip()

        leads.append({
            "lead_num": lead_num,
            "empresa": empresa,
            "rut": rut,
            "insight_type": insight_type,
            "wr_pct_header": wr_pct,
            "n_lp_header": n_lp,
            "n_perdidas_header": n_perdidas,
            "dias_header": dias_header,
            "msg_text": msg_text,
        })

    return leads


# --- Helpers -----------------------------------------------------------------

def get_msg_before_firma(msg: str) -> str:
    """Retorna el texto del mensaje antes de la firma."""
    idx = msg.rfind(FIRMA_MARKER)
    if idx == -1:
        return msg
    # Go back to find the name line before "IngenIA Licitaciones"
    before = msg[:idx].strip()
    # Remove the name line (e.g. "Sebastián Cortés")
    lines = before.rsplit("\n", 1)
    if len(lines) > 1:
        return lines[0].strip()
    return before


def check_forbidden_terms(msg: str) -> list:
    """Retorna lista de terminos prohibidos encontrados."""
    t = msg.lower()
    found = []
    for term in _FORBIDDEN_TERMS:
        if term in t:
            found.append(term)
    return found


def get_rival_aliases(raw_name: str) -> list:
    """Variantes del nombre del rival para comparacion flexible."""
    if not raw_name or raw_name == "nan" or pd.isna(raw_name):
        return []
    aliases = []
    for part in str(raw_name).split("|"):
        part = part.strip()
        if part:
            aliases.append(part.lower())
            # Also add title-cased cleaned version (like humanizar does)
            cleaned = re.sub(
                r"\b(SPA|LTDA|LIMITADA|EIRL|E\.I\.R\.L\.|S\.A\.|SA)\.?$",
                "", part, flags=re.IGNORECASE
            ).strip(" .,")
            if cleaned:
                aliases.append(cleaned.lower())
                aliases.append(cleaned.title().lower())
    return list(set(aliases))


def name_matches(candidate: str, aliases: list) -> bool:
    """True si candidate aparece en algun alias o viceversa."""
    c = candidate.lower().strip()
    if not c:
        return False
    for alias in aliases:
        if c in alias or alias in c:
            return True
    return False


def meses_from_dias(dias: float) -> int:
    return int(round(float(dias) / 30))


# --- Main verification -------------------------------------------------------

def verify():
    print("=== Verificador de Mensajes v5 ===\n")

    if not MSG_FILE.exists():
        print(f"ERROR: No se encontro {MSG_FILE}")
        return False
    if not LOSS_PAR.exists():
        print(f"ERROR: No se encontro {LOSS_PAR}")
        return False

    content = MSG_FILE.read_text(encoding="utf-8")
    leads_parsed = parse_v5_blocks(content)
    print(f"Leads parseados: {len(leads_parsed)}")

    loss = pd.read_parquet(LOSS_PAR)
    loss["rut_norm"] = loss["rut"].astype(str).str.strip()
    rut_index = loss.set_index("rut_norm")

    errores = []
    advertencias = []
    ok_list = []
    forbidden_issues = []
    length_issues = []
    cta_issues = []

    def add_error(lead_num, rut, empresa, campo, val_msg, val_real, desc):
        errores.append({
            "lead": lead_num,
            "rut": rut,
            "empresa": empresa,
            "campo": campo,
            "valor_en_mensaje": val_msg,
            "valor_real": val_real,
            "descripcion": desc,
        })

    def add_advertencia(lead_num, desc):
        advertencias.append({"lead": lead_num, "descripcion": desc})

    for lead in leads_parsed:
        lnum = lead["lead_num"]
        rut = lead["rut"]
        empresa = lead["empresa"]
        insight = lead["insight_type"]
        msg = lead["msg_text"]
        has_error = False

        # --- 1. Terminos prohibidos ---
        forbidden = check_forbidden_terms(msg)
        if forbidden:
            forbidden_issues.append({
                "lead": lnum, "rut": rut, "empresa": empresa,
                "terminos": forbidden,
            })
            has_error = True

        # --- 2. Longitud del mensaje (antes de firma) ---
        msg_body = get_msg_before_firma(msg)
        if len(msg_body) > MAX_MSG_CHARS_BEFORE_FIRMA:
            length_issues.append({
                "lead": lnum, "rut": rut, "empresa": empresa,
                "chars": len(msg_body), "max": MAX_MSG_CHARS_BEFORE_FIRMA,
            })
            has_error = True

        # --- 3. CTA con signo de interrogacion ---
        if "?" not in msg:
            cta_issues.append({
                "lead": lnum, "rut": rut, "empresa": empresa,
                "descripcion": "Mensaje sin signo de interrogacion (CTA faltante)",
            })
            has_error = True

        # --- 4. Verificar datos contra parquet ---
        if rut not in rut_index.index:
            add_error(lnum, rut, empresa, "rut", rut, "NO_ENCONTRADO",
                      f"RUT {rut} no encontrado en loss_analysis.parquet")
            has_error = True
            if not has_error:
                ok_list.append(lnum)
            continue

        row = rut_index.loc[rut]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]

        # --- 4a. Verificar header metadata vs parquet ---
        wr_real = float(row.get("win_rate", 0) or 0)
        wr_real_pct = round(wr_real * 100)
        if lead["wr_pct_header"] is not None and abs(lead["wr_pct_header"] - wr_real_pct) > 1:
            add_error(lnum, rut, empresa, "win_rate_header",
                      f"{lead['wr_pct_header']}%", f"{wr_real_pct}%",
                      f"Header WR {lead['wr_pct_header']}% vs real {wr_real_pct}%")
            has_error = True

        n_lp_real = int(row.get("n_LP", 0) or 0)
        if lead["n_lp_header"] is not None and lead["n_lp_header"] != n_lp_real:
            add_error(lnum, rut, empresa, "n_LP_header",
                      lead["n_lp_header"], n_lp_real,
                      f"Header LP={lead['n_lp_header']} vs real {n_lp_real}")
            has_error = True

        n_perdidas_real = int(row.get("total_lost_loss", 0) or 0)
        if lead["n_perdidas_header"] is not None and lead["n_perdidas_header"] != n_perdidas_real:
            add_error(lnum, rut, empresa, "total_lost_loss_header",
                      lead["n_perdidas_header"], n_perdidas_real,
                      f"Header Perdidas={lead['n_perdidas_header']} vs real {n_perdidas_real}")
            has_error = True

        dias_real = float(row.get("dias_desde_ultima", 0) or 0)
        if lead["dias_header"] is not None and abs(lead["dias_header"] - dias_real) > 1:
            add_error(lnum, rut, empresa, "dias_header",
                      lead["dias_header"], int(dias_real),
                      f"Header Dias={lead['dias_header']} vs real {int(dias_real)}")
            has_error = True

        # --- 4b. Verificar contenido del mensaje segun tipo de insight ---
        total_lost = int(row.get("total_lost_loss", 0) or 0)
        total_bids = int(row.get("total_bids", 0) or 0)
        total_wins = int(row.get("total_wins", 0) or 0)
        loss_rate = float(row.get("loss_rate", 0) or 0)
        monto_total = float(row.get("monto_total", 0) or 0)
        rival1_raw = str(row.get("top_rival_1_name", "") or "")
        rival1_cnt = int(row.get("top_rival_1_count", 0) or 0)
        aliases_r1 = get_rival_aliases(rival1_raw)

        if insight == "rival_fuerte":
            # Expects: "{rival} les ha ganado {cnt} de las ultimas {total_lost}"
            m = re.search(r"les ha ganado (\d+) de las", msg)
            if m:
                cnt_msg = int(m.group(1))
                if cnt_msg != rival1_cnt:
                    add_error(lnum, rut, empresa, "rival1_count",
                              cnt_msg, rival1_cnt,
                              f"Msg dice rival gano {cnt_msg} vs real {rival1_cnt}")
                    has_error = True
            m_lost = re.search(r"(?:u|\u00fa)ltimas (\d+)", msg)
            if m_lost:
                lost_msg = int(m_lost.group(1))
                if lost_msg != total_lost:
                    add_error(lnum, rut, empresa, "total_lost",
                              lost_msg, total_lost,
                              f"Msg dice {lost_msg} perdidas vs real {total_lost}")
                    has_error = True
            # Verify rival name
            rival_in_msg = re.search(r"^[^,]+, soy .+\.\n\n(.+?) les ha ganado", msg, re.MULTILINE)
            if rival_in_msg:
                rival_name = rival_in_msg.group(1).strip()
                if not name_matches(rival_name, aliases_r1):
                    add_error(lnum, rut, empresa, "rival_name",
                              rival_name, rival1_raw,
                              f"Rival '{rival_name}' no coincide con '{rival1_raw}'")
                    has_error = True

        elif insight == "rival_recurrente":
            # Expects: "{rival} se les adelanto {cnt} veces"
            m = re.search(r"se les adelant(?:o|\u00f3) (\d+) veces", msg)
            if m:
                cnt_msg = int(m.group(1))
                if cnt_msg != rival1_cnt:
                    add_error(lnum, rut, empresa, "rival1_count",
                              cnt_msg, rival1_cnt,
                              f"Msg dice rival gano {cnt_msg} vs real {rival1_cnt}")
                    has_error = True
            rival_in_msg = re.search(r"compitieron, (.+?) se les adelant", msg)
            if rival_in_msg:
                rival_name = rival_in_msg.group(1).strip()
                if not name_matches(rival_name, aliases_r1):
                    add_error(lnum, rut, empresa, "rival_name",
                              rival_name, rival1_raw,
                              f"Rival '{rival_name}' no coincide con '{rival1_raw}'")
                    has_error = True

        elif insight == "win_rate_gap_LP":
            # Expects: "Con {n_lp} postulaciones LP y tasa de {wr}%"
            m_lp = re.search(r"Con (\d+) postulaciones LP", msg)
            if m_lp:
                lp_msg = int(m_lp.group(1))
                if lp_msg != n_lp_real:
                    add_error(lnum, rut, empresa, "n_LP",
                              lp_msg, n_lp_real,
                              f"Msg dice {lp_msg} LP vs real {n_lp_real}")
                    has_error = True
            m_wr = re.search(r"tasa de (\d+)%", msg)
            if m_wr:
                wr_msg = int(m_wr.group(1))
                if abs(wr_msg - wr_real_pct) > 1:
                    add_error(lnum, rut, empresa, "win_rate_msg",
                              f"{wr_msg}%", f"{wr_real_pct}%",
                              f"Msg dice WR {wr_msg}% vs real {wr_real_pct}%")
                    has_error = True
            m_gap = re.search(r"(\d+) puntos bajo el rubro", msg)
            if m_gap:
                gap_msg = int(m_gap.group(1))
                gap_real = int(round((INDUSTRY_WR_MEDIAN - wr_real) * 100))
                if abs(gap_msg - gap_real) > 1:
                    add_error(lnum, rut, empresa, "wr_gap",
                              f"{gap_msg}pp", f"{gap_real}pp",
                              f"Msg dice gap {gap_msg}pp vs real {gap_real}pp")
                    has_error = True
            # Verify opp cost if mentioned
            m_opp = re.search(r"cerca de \$([0-9,.]+[BM])", msg)
            if m_opp:
                opp_str = m_opp.group(1)
                wr_gap = INDUSTRY_WR_MEDIAN - wr_real
                opp_real = monto_total * wr_gap if wr_gap > 0 else 0
                # Parse opp_str to number for approximate comparison
                opp_parsed = 0
                if opp_str.endswith("B"):
                    opp_parsed = float(opp_str[:-1].replace(",", "")) * 1_000_000_000
                elif opp_str.endswith("M"):
                    opp_parsed = float(opp_str[:-1].replace(",", "")) * 1_000_000
                # Allow 20% tolerance for rounding
                if opp_real > 0 and abs(opp_parsed - opp_real) / opp_real > 0.20:
                    add_error(lnum, rut, empresa, "opp_cost",
                              opp_str, f"${opp_real:,.0f}",
                              f"Costo oportunidad ${opp_str} vs calculado ${opp_real:,.0f}")
                    has_error = True

        elif insight == "lp_alto":
            # Expects: "postulo a {n_lp} licitaciones de alto valor"
            m_lp = re.search(r"postul(?:o|\u00f3) a (\d+) licitaciones", msg)
            if m_lp:
                lp_msg = int(m_lp.group(1))
                if lp_msg != n_lp_real:
                    add_error(lnum, rut, empresa, "n_LP",
                              lp_msg, n_lp_real,
                              f"Msg dice {lp_msg} LP vs real {n_lp_real}")
                    has_error = True
            m_wr = re.search(r"tasa de (\d+)%", msg)
            if m_wr:
                wr_msg = int(m_wr.group(1))
                if abs(wr_msg - wr_real_pct) > 1:
                    add_error(lnum, rut, empresa, "win_rate_msg",
                              f"{wr_msg}%", f"{wr_real_pct}%",
                              f"Msg dice WR {wr_msg}% vs real {wr_real_pct}%")
                    has_error = True
            m_lost = re.search(r"las (\d+) no adjudicadas", msg)
            if m_lost:
                lost_msg = int(m_lost.group(1))
                if lost_msg != total_lost:
                    add_error(lnum, rut, empresa, "total_lost",
                              lost_msg, total_lost,
                              f"Msg dice {lost_msg} perdidas vs real {total_lost}")
                    has_error = True

        elif insight == "inactivo":
            # Expects: "Llevan {m} meses sin postular"
            m_meses = re.search(r"(\d+) meses sin postular", msg)
            if m_meses:
                meses_msg = int(m_meses.group(1))
                meses_real = meses_from_dias(dias_real)
                if abs(meses_msg - meses_real) > 1:
                    add_error(lnum, rut, empresa, "meses_inactivo",
                              meses_msg, f"{meses_real} ({int(dias_real)} dias)",
                              f"Msg dice {meses_msg} meses vs real {meses_real} ({int(dias_real)} dias)")
                    has_error = True
            else:
                add_advertencia(lnum, "No se encontro patron de meses en msg inactivo")

        elif insight == "wr_bajo_lp":
            # Expects: "De {n_lp} postulaciones LP, la tasa es {wr}%"
            m_lp = re.search(r"De (\d+) postulaciones LP", msg)
            if m_lp:
                lp_msg = int(m_lp.group(1))
                if lp_msg != n_lp_real:
                    add_error(lnum, rut, empresa, "n_LP",
                              lp_msg, n_lp_real,
                              f"Msg dice {lp_msg} LP vs real {n_lp_real}")
                    has_error = True
            m_wr = re.search(r"tasa.*?(?:es |de )(\d+)%", msg)
            if m_wr:
                wr_msg = int(m_wr.group(1))
                if abs(wr_msg - wr_real_pct) > 1:
                    add_error(lnum, rut, empresa, "win_rate_msg",
                              f"{wr_msg}%", f"{wr_real_pct}%",
                              f"Msg dice WR {wr_msg}% vs real {wr_real_pct}%")
                    has_error = True

        elif insight == "loss_concentrado":
            # Expects: "De las ultimas {total_bids} licitaciones, {total_lost} no se adjudicaron"
            m_total = re.search(
                r"(?:u|\u00fa)ltimas (\d+) licitaciones.*?(\d+) no se adjudicaron",
                msg, re.DOTALL,
            )
            if m_total:
                bids_msg = int(m_total.group(1))
                lost_msg = int(m_total.group(2))
                if bids_msg != total_bids:
                    add_error(lnum, rut, empresa, "total_bids",
                              bids_msg, total_bids,
                              f"Msg dice {bids_msg} bids vs real {total_bids}")
                    has_error = True
                if lost_msg != total_lost:
                    add_error(lnum, rut, empresa, "total_lost",
                              lost_msg, total_lost,
                              f"Msg dice {lost_msg} perdidas vs real {total_lost}")
                    has_error = True

        elif insight == "wr_bajo":
            # Expects: "{total_wins} adjudicadas de {total_bids} postulaciones — tasa de {wr}%"
            m = re.search(r"(\d+) adjudicadas de (\d+) postulaciones", msg)
            if m:
                wins_msg = int(m.group(1))
                bids_msg = int(m.group(2))
                if wins_msg != total_wins:
                    add_error(lnum, rut, empresa, "total_wins",
                              wins_msg, total_wins,
                              f"Msg dice {wins_msg} wins vs real {total_wins}")
                    has_error = True
                if bids_msg != total_bids:
                    add_error(lnum, rut, empresa, "total_bids",
                              bids_msg, total_bids,
                              f"Msg dice {bids_msg} bids vs real {total_bids}")
                    has_error = True
            m_wr = re.search(r"tasa de (\d+)%", msg)
            if m_wr:
                wr_msg = int(m_wr.group(1))
                if abs(wr_msg - wr_real_pct) > 1:
                    add_error(lnum, rut, empresa, "win_rate_msg",
                              f"{wr_msg}%", f"{wr_real_pct}%",
                              f"Msg dice WR {wr_msg}% vs real {wr_real_pct}%")
                    has_error = True

        elif insight == "rival_unico":
            # Expects: "En {total_lost} de sus licitaciones no adjudicadas, {rival} fue quien gano"
            m_lost = re.search(r"En (\d+) de sus licitaciones", msg)
            if m_lost:
                lost_msg = int(m_lost.group(1))
                if lost_msg != total_lost:
                    add_error(lnum, rut, empresa, "total_lost",
                              lost_msg, total_lost,
                              f"Msg dice {lost_msg} perdidas vs real {total_lost}")
                    has_error = True
            m_rival = re.search(r"adjudicadas, (.+?) fue quien", msg)
            if m_rival:
                rival_name = m_rival.group(1).strip()
                if not name_matches(rival_name, aliases_r1):
                    add_error(lnum, rut, empresa, "rival_name",
                              rival_name, rival1_raw,
                              f"Rival '{rival_name}' no coincide con '{rival1_raw}'")
                    has_error = True

        elif insight == "default":
            # Expects: "{total_wins} adjudicadas de {total_bids} postulaciones ({wr}%)"
            m = re.search(r"(\d+) adjudicadas de (\d+) postulaciones \((\d+)%\)", msg)
            if m:
                wins_msg = int(m.group(1))
                bids_msg = int(m.group(2))
                wr_msg = int(m.group(3))
                if wins_msg != total_wins:
                    add_error(lnum, rut, empresa, "total_wins",
                              wins_msg, total_wins,
                              f"Msg dice {wins_msg} wins vs real {total_wins}")
                    has_error = True
                if bids_msg != total_bids:
                    add_error(lnum, rut, empresa, "total_bids",
                              bids_msg, total_bids,
                              f"Msg dice {bids_msg} bids vs real {total_bids}")
                    has_error = True
                if abs(wr_msg - wr_real_pct) > 1:
                    add_error(lnum, rut, empresa, "win_rate_msg",
                              f"{wr_msg}%", f"{wr_real_pct}%",
                              f"Msg dice WR {wr_msg}% vs real {wr_real_pct}%")
                    has_error = True
            else:
                add_advertencia(lnum, "No se pudo parsear patron default")

        if not has_error:
            ok_list.append(lnum)

    # --- Build report ---
    from collections import Counter
    tipo_dist = Counter(l["insight_type"] for l in leads_parsed)

    report = {
        "total_leads": len(leads_parsed),
        "total_ok": len(ok_list),
        "total_con_errores_datos": len(errores),
        "total_forbidden_issues": len(forbidden_issues),
        "total_length_issues": len(length_issues),
        "total_cta_issues": len(cta_issues),
        "total_advertencias": len(advertencias),
        "distribucion_insights": dict(tipo_dist),
        "errores_datos": errores,
        "forbidden_issues": forbidden_issues,
        "length_issues": length_issues,
        "cta_issues": cta_issues,
        "advertencias": advertencias,
        "leads_ok": sorted(ok_list),
    }

    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # --- Console output ---
    print(f"\n{'='*50}")
    print("RESULTADO VERIFICACION v5")
    print(f"{'='*50}")
    print(f"  Total leads:            {report['total_leads']}")
    print(f"  Leads OK:               {report['total_ok']}")
    print(f"  Errores de datos:       {report['total_con_errores_datos']}")
    print(f"  Terminos prohibidos:    {report['total_forbidden_issues']}")
    print(f"  Longitud excedida:      {report['total_length_issues']}")
    print(f"  CTA faltante:           {report['total_cta_issues']}")
    print(f"  Advertencias:           {report['total_advertencias']}")

    print(f"\nDistribucion de insights:")
    for tipo, cnt in sorted(tipo_dist.items(), key=lambda x: -x[1]):
        print(f"  {tipo:22} {cnt:3}")

    if errores:
        print(f"\nERRORES DE DATOS ({len(errores)}):")
        for e in errores:
            print(f"  Lead #{e['lead']:02d} | {e['empresa']} | {e['campo']}: "
                  f"msg={e['valor_en_mensaje']} vs real={e['valor_real']}")

    if forbidden_issues:
        print(f"\nTERMINOS PROHIBIDOS ({len(forbidden_issues)}):")
        for fi in forbidden_issues:
            print(f"  Lead #{fi['lead']:02d} | {fi['empresa']} | {fi['terminos']}")

    if length_issues:
        print(f"\nLONGITUD EXCEDIDA ({len(length_issues)}):")
        for li in length_issues:
            print(f"  Lead #{li['lead']:02d} | {li['empresa']} | {li['chars']} chars (max {li['max']})")

    if cta_issues:
        print(f"\nCTA FALTANTE ({len(cta_issues)}):")
        for ci in cta_issues:
            print(f"  Lead #{ci['lead']:02d} | {ci['empresa']}")

    print(f"\nReporte guardado: {REPORT_OUT}")

    all_ok = (len(errores) == 0 and len(forbidden_issues) == 0
              and len(cta_issues) == 0)
    if all_ok:
        print("\nVerificacion OK — todos los mensajes son correctos")
    else:
        print(f"\nVerificacion con ERRORES — revisar reporte")

    return all_ok


if __name__ == "__main__":
    ok = verify()
    exit(0 if ok else 1)
