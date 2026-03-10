"""
Humanizador de nombres de empresa.

Regla: usar el nombre comercial (post-pipe) y eliminar SOLO formas legales.
Conservar todo lo demás: Constructora, Inmobiliaria, Comercial, Rental, etc.
Title case. Sin nombres personales.

Ej: "CONSTRUCTORA MONTE VIVO LIMITADA | CONSTRUCTORA MONTE VIVO LIMITADA"
  → "Constructora Monte Vivo"

Ej: "ONLY-WORK COMERCIALIZADORA SPA | CONSTRUCTORA SYNEL SPA"
  → "Constructora Synel"  (usa post-pipe, no toca pre-pipe)
"""

import re
import unicodedata
import pandas as pd
from pathlib import Path


def _normalizar(s: str) -> str:
    s = s.replace('\ufffd', '')
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('ascii')


FORMAS_LEGALES = [
    r'EMPRESA\s+INDIVIDUAL\s+DE\s+RESPONSABILIDAD\s+LIMITADA',
    r'S\.?P\.?A\.?',
    r'E\.?I\.?R\.?L\.?',
    r'S\.?R\.?L\.?',
    r'LTDA\.?',
    r'LIMITADA',
    r'S\s+A\b',
]

CONECTORES = {'y', 'de', 'del', 'la', 'el', 'los', 'las', 'e', 'a', 'en', 'con', 'por', '&'}
VOCALES = set('AEIOU')
NO_ACRONIMO = {
    'RIO', 'SUR', 'SOL', 'MAR', 'SAN', 'DEL', 'LOS', 'LAS',
    'VIA', 'EL', 'LA', 'LUZ', 'PAZ', 'RED',
}


def _title_case(s: str) -> str:
    words = s.split()
    result = []
    for i, w in enumerate(words):
        wu = w.upper()
        if i > 0 and w.lower() in CONECTORES:
            result.append(w.lower())
        elif not any(c in VOCALES for c in wu):
            result.append(wu)
        elif len(w) <= 3 and wu not in NO_ACRONIMO:
            result.append(wu)
        else:
            result.append(w.capitalize())
    out = ' '.join(result)
    # Capitalizar después de guión: "Only-work" → "Only-Work"
    out = re.sub(r'(-[a-z])', lambda m: m.group(0).upper(), out)
    return out


def humanizar(nombre_raw: str) -> str:
    if not isinstance(nombre_raw, str) or not nombre_raw.strip():
        return ""

    # POST-PIPE: nombre comercial ya simplificado (evita introducir nombres personales)
    base = nombre_raw.split('|')[1].strip() if '|' in nombre_raw else nombre_raw.strip()
    base = base.strip('.,;: ')

    # Normalizar a ASCII
    n = _normalizar(base).upper()
    n = re.sub(r'\s{2,}', ' ', n).strip()

    # Siglas con puntos: C.F.C. → CFC
    n = re.sub(r'\b([A-Z])\.([A-Z])\.([A-Z])\.?\b', r'\1\2\3', n)
    n = re.sub(r'\b([A-Z])\.([A-Z])\.?\b', r'\1\2', n)
    n = re.sub(r'\b([A-Z]{2,5})\.(?=\s|$)', r'\1', n)

    # Eliminar formas legales (varias pasadas, al final y globalmente)
    for _ in range(3):
        for forma in FORMAS_LEGALES:
            n = re.sub(r'\s*\b' + forma + r'\b\s*$', '', n, flags=re.IGNORECASE).strip()
    for forma in FORMAS_LEGALES:
        cleaned = re.sub(r'\s*\b' + forma + r'\b\s*', ' ', n, flags=re.IGNORECASE).strip()
        if cleaned:
            n = cleaned

    n = re.sub(r'\s{2,}', ' ', n).strip()

    return _title_case(n)


def agregar_columna_humanizado(xlsx_path: str):
    xl = pd.ExcelFile(xlsx_path)
    hojas = {}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        if 'nombre' in df.columns:
            col_hum = df['nombre'].apply(humanizar)
            if 'nombre_humanizado' in df.columns:
                df['nombre_humanizado'] = col_hum
            else:
                idx = df.columns.get_loc('nombre') + 1
                df.insert(idx, 'nombre_humanizado', col_hum)
        hojas[sheet] = df
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        for sheet, df in hojas.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"Guardado: {xlsx_path}")


def actualizar_mensajes_wsp(xlsx_path: str):
    """Reemplaza el nombre de empresa en wsp_mensaje con nombre_humanizado."""
    xl = pd.ExcelFile(xlsx_path)
    hojas = {}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        if 'wsp_mensaje' in df.columns and 'nombre_humanizado' in df.columns:
            def reemplazar(row):
                msg = str(row['wsp_mensaje'])
                hum = str(row['nombre_humanizado'])
                # Reemplazar todo lo que hay entre "Vi que " y " ha participado"
                return re.sub(
                    r'(Vi que )(.+?)( ha participado)',
                    lambda m: m.group(1) + hum + m.group(3),
                    msg
                )
            df['wsp_mensaje'] = df.apply(reemplazar, axis=1)
        hojas[sheet] = df
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        for sheet, df in hojas.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"Mensajes actualizados: {xlsx_path}")
