"""
Utilidades compartidas del pipeline.
"""
from __future__ import annotations

import re
import time
import requests
import pandas as pd
from typing import Optional


def normalizar_rut(rut: str) -> Optional[str]:
    """
    Normaliza un RUT chileno a formato sin puntos con guión.
    Ej: '76.543.210-K' -> '76543210-K', '76543210K' -> '76543210-K'
    Retorna None si no es un RUT válido.
    """
    if not rut or not isinstance(rut, str):
        return None
    rut = rut.strip().upper().replace(".", "").replace(" ", "")
    # Si no tiene guión, insertar antes del último carácter (dígito verificador)
    if "-" not in rut and len(rut) > 1:
        rut = rut[:-1] + "-" + rut[-1]
    # Validar formato
    if not re.match(r"^\d{6,9}-[\dK]$", rut):
        return None
    return rut


def extraer_rut_de_id(party_id: str) -> Optional[str]:
    """
    Extrae RUT de un ID de party OCDS.
    Formatos comunes: 'CL-RUT-76543210-K', '76543210-K', etc.
    """
    if not party_id or not isinstance(party_id, str):
        return None
    # Intentar extraer patrón de RUT
    match = re.search(r"(\d{6,9})-?([\dkK])", party_id)
    if match:
        return f"{match.group(1)}-{match.group(2).upper()}"
    return None


def tipo_licitacion(codigo: str) -> str:
    """Extrae tipo de licitación del código (LP, LE, L1, LR, LQ)."""
    codigo = str(codigo).upper()
    for tipo in ["LP", "LE", "LR", "L1", "LQ"]:
        if f"-{tipo}" in codigo or f"({tipo})" in codigo:
            return tipo
    return "Otro"


def safe_request(url: str, max_retries: int = 3, delay: float = 2.0,
                 timeout: int = 30) -> Optional[requests.Response]:
    """Request HTTP con reintentos y backoff."""
    for i in range(max_retries):
        try:
            resp = requests.get(url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = delay * (i + 1)
                print(f"  HTTP {resp.status_code}, reintentando en {wait}s...")
                time.sleep(wait)
                continue
            print(f"  HTTP {resp.status_code} para {url}")
            return None
        except requests.RequestException as e:
            print(f"  Error request ({i+1}/{max_retries}): {e}")
            time.sleep(delay)
    return None


def formato_clp(monto: float) -> str:
    """Formatea un monto en pesos chilenos."""
    if monto is None or (isinstance(monto, float) and (monto != monto)):  # NaN check
        return "$0"
    if monto >= 1_000_000_000:
        return f"${monto/1_000_000_000:,.1f}B"
    if monto >= 1_000_000:
        return f"${monto/1_000_000:,.0f}M"
    return f"${monto:,.0f}"


def safe_get(row, col: str, default=None):
    """Like Series.get() but returns default for NaN values too."""
    val = row.get(col)
    if val is None or (isinstance(val, float) and val != val):
        return default
    try:
        if not isinstance(val, (list, dict, set)) and pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


import unicodedata as _ud

_COMPANY_KEYWORDS = {
    "SPA", "LTDA", "LIMITADA", "EIRL", "E.I.R.L", "S.A.", "S.A",
    "CONSTRUCTORA", "INGENIERIA", "SERVICIOS", "COMERCIAL",
    "INVERSIONES", "SOCIEDAD", "EMPRESA", "CONSULTORA",
    "IMPORTADORA", "INMOBILIARIA", "MAQUINARIAS", "TRANSPORTES",
    "PROYECTOS", "MANTENCION", "CONSTRUCCION", "CONSTRUCCIONES",
    "GRUPO", "GESTION", "CLIMATIZACION", "TECNOLOGIA", "SOLUCIONES",
    "ELECTRONICA", "MECANICA", "ASESORIA", "ASESORIAS", "INSTALACIONES",
    "DISTRIBUIDORA", "SUMINISTROS", "ARQUITECTOS", "OBRAS",
}


def _strip_accents(s: str) -> str:
    """Remueve acentos para comparación."""
    return "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn")


def is_persona_natural(nombre: str) -> bool:
    """Detecta si un nombre parece persona natural (no empresa).

    Retorna True solo cuando AMBAS partes (formal y trade name)
    carecen de keywords de empresa y son nombres cortos.
    Normaliza acentos para evitar falsos positivos.
    """
    if pd.isna(nombre) or not nombre:
        return False

    nombre_norm = _strip_accents(nombre.upper().strip())
    # Check full name for company keywords (accent-normalized)
    if any(kw in nombre_norm for kw in _COMPANY_KEYWORDS):
        return False

    # Split by | (format: "FORMAL_NAME | TRADE_NAME")
    parts = [p.strip() for p in nombre.split("|")]
    for part in parts:
        part_norm = _strip_accents(part.upper())
        if any(kw in part_norm for kw in _COMPANY_KEYWORDS):
            return False

    # If both parts are short (≤3 words), likely a person
    return all(len(p.split()) <= 4 for p in parts)


def print_header(texto: str):
    """Imprime header con formato."""
    print(f"\n{'='*60}")
    print(f"  {texto}")
    print(f"{'='*60}")
