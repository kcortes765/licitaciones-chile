import pandas as pd
import re
import json

# Cargar parquet
loss = pd.read_parquet('C:/Seba/Nueva carpeta (2)/lead_scoring/data/output/loss_analysis.parquet')
loss['rut_norm'] = loss['rut'].astype(str).apply(lambda r: str(r).strip())
rut_index = loss.set_index('rut_norm')

INDUSTRY_WR_MEDIAN = 0.22

# Leer archivo de mensajes
with open('C:/Seba/Nueva carpeta (2)/lead_scoring/data/output/mensajes_wsp_v3.txt', 'r', encoding='utf-8') as f:
    content = f.read()

lead_blocks = re.split(r'={40,}', content)
lead_blocks = [b.strip() for b in lead_blocks if b.strip()]

leads_parsed = []
for block in lead_blocks:
    lines = block.split('\n')
    header_line = rut_line = insight_line = None
    msg_lines = []
    in_msg = False
    for line in lines:
        if re.match(r'LEAD #\d+', line):
            header_line = line
        elif line.startswith('RUT:'):
            rut_line = line
        elif line.startswith('Insight:'):
            insight_line = line
        elif re.match(r'─+', line):
            in_msg = True
        elif in_msg:
            msg_lines.append(line)
    if not header_line:
        continue
    m_header = re.match(r'(LEAD #\d+) \| Rank #(\d+) \| (.+)', header_line)
    if not m_header:
        continue
    lead_id = m_header.group(1)
    empresa_humanizada = m_header.group(3).strip()
    m_rut = re.match(r'RUT: ([\d\w-]+)', rut_line) if rut_line else None
    if not m_rut:
        continue
    rut = m_rut.group(1).strip()
    insight_type = wr_pct = n_lp = n_perdidas = None
    if insight_line:
        m_ins = re.match(r'Insight: (\w+) \| WR: (\d+)% \| LP: (\d+) \| Perdidas: (\d+)', insight_line)
        if m_ins:
            insight_type = m_ins.group(1)
            wr_pct = int(m_ins.group(2))
            n_lp = int(m_ins.group(3))
            n_perdidas = int(m_ins.group(4))
    msg_text = '\n'.join(msg_lines).strip()
    leads_parsed.append({
        'lead_id': lead_id, 'empresa': empresa_humanizada, 'rut': rut,
        'insight_type': insight_type, 'wr_pct_header': wr_pct,
        'n_lp_header': n_lp, 'n_perdidas_header': n_perdidas, 'msg_text': msg_text
    })

# ==== Helper: normalizar nombres de rival ====
def get_rival_aliases(raw_name):
    """Devuelve lista de variantes del nombre del rival para comparación flexible."""
    if not raw_name or raw_name == 'nan':
        return []
    aliases = []
    for part in raw_name.split('|'):
        part = part.strip()
        if part:
            aliases.append(part.lower())
    return aliases

def name_matches(candidate, aliases):
    """True si candidate (lower) aparece en algún alias o viceversa."""
    c = candidate.lower().strip()
    for alias in aliases:
        if c in alias or alias in c:
            return True
    return False

# ==== VERIFICACIÓN ====
errores = []
advertencias = []
ok_list = []
sin_datos = []
leads_con_error = set()

def add_error(lead_id, rut, empresa, campo, val_msg, val_real, desc):
    errores.append({
        'lead': lead_id, 'rut': rut, 'empresa': empresa,
        'campo': campo, 'valor_en_mensaje': val_msg,
        'valor_real': val_real, 'descripcion': desc
    })

def add_advertencia(lead_id, desc):
    advertencias.append({'lead': lead_id, 'descripcion': desc})

for lead in leads_parsed:
    lid = lead['lead_id']
    rut = lead['rut']
    empresa = lead['empresa']
    insight = lead['insight_type']
    msg = lead['msg_text']
    has_error = False

    # Buscar en parquet
    if rut not in rut_index.index:
        add_error(lid, rut, empresa, 'rut', rut, 'NO_ENCONTRADO',
                  f'RUT {rut} no encontrado en parquet')
        leads_con_error.add(lid)
        continue

    row = rut_index.loc[rut]

    # ---- Verificar header metadata vs parquet ----

    # WR: round(win_rate * 100)
    wr_real_raw = float(row['win_rate'])
    wr_real_pct = round(wr_real_raw * 100)
    if lead['wr_pct_header'] is not None and abs(lead['wr_pct_header'] - wr_real_pct) > 1:
        add_error(lid, rut, empresa, 'win_rate_header',
                  f"{lead['wr_pct_header']}%", f"{wr_real_pct}% (raw={wr_real_raw:.4f})",
                  f"Header dice WR {lead['wr_pct_header']}% pero real es {wr_real_pct}%")
        has_error = True

    # n_LP
    n_lp_real = int(row['n_LP'])
    if lead['n_lp_header'] is not None and lead['n_lp_header'] != n_lp_real:
        add_error(lid, rut, empresa, 'n_LP_header',
                  lead['n_lp_header'], n_lp_real,
                  f"Header dice LP={lead['n_lp_header']} pero real es {n_lp_real}")
        has_error = True

    # n_perdidas vs total_lost_loss
    n_perdidas_real = int(row['total_lost_loss'])
    if lead['n_perdidas_header'] is not None and lead['n_perdidas_header'] != n_perdidas_real:
        add_error(lid, rut, empresa, 'total_lost_loss_header',
                  lead['n_perdidas_header'], n_perdidas_real,
                  f"Header dice Perdidas={lead['n_perdidas_header']} pero real es {n_perdidas_real}")
        has_error = True

    # ---- Verificar MENSAJE según tipo de insight ----
    msg_verified = False

    if insight in ('rival_unico', 'rival_recurrente', 'rival_fuerte'):
        rival_raw_1 = str(row['top_rival_1_name']) if pd.notna(row['top_rival_1_name']) else ''
        rival_raw_2 = str(row['top_rival_2_name']) if pd.notna(row['top_rival_2_name']) else ''
        aliases_r1 = get_rival_aliases(rival_raw_1)
        aliases_r2 = get_rival_aliases(rival_raw_2)
        count_r1 = int(row['top_rival_1_count']) if pd.notna(row['top_rival_1_count']) else 0
        count_r2 = int(row['top_rival_2_count']) if pd.notna(row['top_rival_2_count']) else 0

        # Patrón 1: "aparece NombreRival." (rival_unico)
        # Punto final de la frase anterior + espacio + Nombre
        appear_match = re.search(r'aparece ([^\n.]+)', msg)

        # Patrón 2: ". NombreRival les ganó en N ocasiones" (rival_recurrente/fuerte)
        # El punto pertenece a la frase anterior, luego el nombre empieza con mayúscula
        gano_match = re.search(r'\.\s+([A-ZÁÉÍÓÚÑ][^\n.]+?) les gan[oó] en (\d+) ocasion', msg)
        if not gano_match:
            # Fallback sin punto previo (para casos donde el rival está en inicio de frase)
            gano_match = re.search(r'(?:^|\n)([A-ZÁÉÍÓÚÑ][^\n.]+?) les gan[oó] en (\d+) ocasion', msg)

        if appear_match:
            rival_en_msg = appear_match.group(1).strip().rstrip('.')
            msg_verified = True
            if not name_matches(rival_en_msg, aliases_r1) and not name_matches(rival_en_msg, aliases_r2):
                add_error(lid, rut, empresa, 'top_rival_name', rival_en_msg,
                          f"r1='{rival_raw_1}'",
                          f"Rival '{rival_en_msg}' no coincide con top_rival_1='{rival_raw_1}'")
                has_error = True
            else:
                # Es correcto, advertir si es abreviatura
                display_name_r1 = rival_raw_1.split('|')[0].strip()
                if rival_en_msg.lower() != display_name_r1.lower():
                    add_advertencia(lid, f"Rival '{rival_en_msg}' es abreviatura/alias de '{display_name_r1}'")

        if gano_match:
            rival_en_msg = gano_match.group(1).strip()
            count_en_msg = int(gano_match.group(2))
            msg_verified = True

            # Verificar count (debe coincidir con r1 o r2 según qué rival es)
            matches_r1 = name_matches(rival_en_msg, aliases_r1)
            matches_r2 = name_matches(rival_en_msg, aliases_r2)

            if matches_r1:
                if count_en_msg != count_r1:
                    add_error(lid, rut, empresa, 'top_rival_1_count', count_en_msg, count_r1,
                              f"Mensaje dice rival r1 ganó {count_en_msg} veces pero real es {count_r1}")
                    has_error = True
                else:
                    display_name = rival_raw_1.split('|')[0].strip()
                    if rival_en_msg.lower() != display_name.lower():
                        add_advertencia(lid, f"Rival '{rival_en_msg}' es abreviatura/alias de '{display_name}'")
            elif matches_r2:
                if count_en_msg != count_r2:
                    add_error(lid, rut, empresa, 'top_rival_2_count', count_en_msg, count_r2,
                              f"Mensaje dice rival r2 ganó {count_en_msg} veces pero real es {count_r2}")
                    has_error = True
                else:
                    display_name = rival_raw_2.split('|')[0].strip()
                    if rival_en_msg.lower() != display_name.lower():
                        add_advertencia(lid, f"Rival '{rival_en_msg}' es abreviatura/alias de '{display_name}'")
            else:
                # No coincide con ningún rival conocido
                add_error(lid, rut, empresa, 'top_rival_name', rival_en_msg,
                          f"r1='{rival_raw_1.split('|')[0].strip()}' | r2='{rival_raw_2.split('|')[0].strip()}'",
                          f"Rival '{rival_en_msg}' en mensaje no coincide con r1='{rival_raw_1.split('|')[0].strip()}' ni r2='{rival_raw_2.split('|')[0].strip()}'")
                has_error = True

        if not msg_verified:
            add_advertencia(lid, "No se encontró patrón de rival en el texto del mensaje")

    elif insight in ('lp_alto', 'wr_bajo_lp'):
        n_lp_real = int(row['n_LP'])
        n_perd_real = int(row['total_lost_loss'])

        lp_match = re.search(r'postulado a (\d+) licitaciones de alto valor', msg)
        perdidas_match = re.search(r'historial de esas (\d+) licitaciones no adjudicadas', msg)

        if lp_match:
            lp_msg = int(lp_match.group(1))
            msg_verified = True
            if lp_msg != n_lp_real:
                add_error(lid, rut, empresa, 'n_LP', lp_msg, n_lp_real,
                          f"Mensaje dice {lp_msg} LP pero real es {n_lp_real}")
                has_error = True

        if perdidas_match:
            perd_msg = int(perdidas_match.group(1))
            msg_verified = True
            if perd_msg != n_perd_real:
                add_error(lid, rut, empresa, 'total_lost_loss', perd_msg, n_perd_real,
                          f"Mensaje dice {perd_msg} pérdidas LP pero real es {n_perd_real}")
                has_error = True

        if not msg_verified:
            sin_datos.append(lid)
            continue

    elif insight == 'inactivo':
        meses_match = re.search(r'(\d+)\s+meses sin postular', msg)
        if meses_match:
            meses_msg = int(meses_match.group(1))
            dias_real = float(row['dias_desde_ultima'])
            meses_real = dias_real / 30
            meses_real_round = round(meses_real)
            msg_verified = True
            if abs(meses_msg - meses_real_round) > 1:
                add_error(lid, rut, empresa, 'dias_desde_ultima_meses',
                          meses_msg, f'{meses_real_round} ({dias_real:.0f} dias)',
                          f"Mensaje dice {meses_msg} meses pero real es {meses_real:.1f} meses ({dias_real:.0f} días)")
                has_error = True
        else:
            sin_datos.append(lid)
            continue

    elif insight == 'loss_concentrado':
        n_perd_real = int(row['total_lost_loss'])
        lr_real = round(row['loss_rate'] * 100)
        total_participated = int(row['total_participated']) if pd.notna(row['total_participated']) else int(row['total_bids'])

        # Patrón: "perdió N de M licitaciones (X%)"
        lr_match = re.search(r'perdi[oó] (\d+) de (\d+) licitaciones', msg)
        pct_match = re.search(r'\((\d+)%\)', msg)

        if lr_match:
            perd_msg = int(lr_match.group(1))
            total_msg = int(lr_match.group(2))
            msg_verified = True
            if perd_msg != n_perd_real:
                add_error(lid, rut, empresa, 'total_lost_loss', perd_msg, n_perd_real,
                          f"Mensaje dice perdió {perd_msg} pero real es {n_perd_real}")
                has_error = True
            if total_msg != total_participated:
                add_error(lid, rut, empresa, 'total_participated', total_msg, total_participated,
                          f"Mensaje dice total={total_msg} pero real es {total_participated}")
                has_error = True
            if pct_match:
                pct_msg = int(pct_match.group(1))
                expected_pct = round(perd_msg / total_msg * 100) if total_msg > 0 else 0
                if abs(pct_msg - expected_pct) > 1:
                    add_error(lid, rut, empresa, 'loss_rate_pct', f'{pct_msg}%', f'{expected_pct}%',
                              f"Porcentaje en mensaje {pct_msg}% no corresponde a {perd_msg}/{total_msg}={expected_pct}%")
                    has_error = True
        elif pct_match:
            pct_msg = int(pct_match.group(1))
            msg_verified = True
            if abs(pct_msg - lr_real) > 2:
                add_error(lid, rut, empresa, 'loss_rate', f'{pct_msg}%', f'{lr_real}%',
                          f"Mensaje dice {pct_msg}% pero real es {lr_real}%")
                has_error = True

        if not msg_verified:
            sin_datos.append(lid)
            continue

    elif insight == 'wr_bajo':
        wr_real_pct = round(float(row['win_rate']) * 100)
        # Buscar porcentaje mencionado en el mensaje
        wr_match = re.search(r'tasa.*?(\d+)%', msg, re.IGNORECASE)
        if not wr_match:
            wr_match = re.search(r'(\d+)%.*?adjudicaci', msg, re.IGNORECASE)
        if wr_match:
            wr_msg = int(wr_match.group(1))
            msg_verified = True
            if abs(wr_msg - wr_real_pct) > 1:
                add_error(lid, rut, empresa, 'win_rate', f'{wr_msg}%', f'{wr_real_pct}%',
                          f"Mensaje dice WR {wr_msg}% pero real es {wr_real_pct}%")
                has_error = True
        else:
            sin_datos.append(lid)
            continue

    else:
        sin_datos.append(lid)
        continue

    if has_error:
        leads_con_error.add(lid)
    else:
        ok_list.append(lid)

# Asegurarse de que todos los leads aparezcan en alguna categoría
all_lids = {l['lead_id'] for l in leads_parsed}
classified = set(ok_list) | set(sin_datos) | leads_con_error
unclassified = all_lids - classified
for lid in sorted(unclassified):
    ok_list.append(lid)

resultado = {
    'total_verificados': len(leads_parsed),
    'total_con_errores': len(leads_con_error),
    'total_ok': len(ok_list),
    'total_sin_datos_verificables': len(sin_datos),
    'errores': errores,
    'advertencias': advertencias,
    'ok': sorted(ok_list),
    'sin_datos_verificables': sorted(sin_datos)
}

print(json.dumps(resultado, ensure_ascii=False, indent=2))
