"""
02 - Scraping de contratistas MOP (Ministerio de Obras Públicas).
Extrae listas de contratistas de obras mayores y menores.
Resultado: data/filtered/mop_contratistas.parquet

Uso:
  python 02_scrape_mop.py
"""
from __future__ import annotations

import re

import pandas as pd
from bs4 import BeautifulSoup

from config import MOP_MAYORES_URL, MOP_MENORES_URL, FILTERED_DIR
from utils import normalizar_rut, print_header, safe_request


def scrape_mop_page(url: str, tipo: str) -> list[dict]:
    """Scrape una página de contratistas MOP."""
    print(f"  Scraping {tipo}: {url}")

    resp = safe_request(url, timeout=30)
    if resp is None:
        print(f"  ERROR: No se pudo obtener {url}")
        return []

    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        soup = BeautifulSoup(resp.text, "html.parser")
    contratistas = []

    # Buscar tablas con datos de contratistas
    tables = soup.find_all("table")
    if not tables:
        # Intentar con div/article content
        print(f"  No se encontraron tablas, buscando listas...")
        return _scrape_mop_list(soup, tipo)

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # Detectar headers
        headers = []
        header_row = rows[0]
        for th in header_row.find_all(["th", "td"]):
            headers.append(th.get_text(strip=True).lower())

        if not headers:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    data[headers[i]] = cell.get_text(strip=True)

            # Extraer campos relevantes
            contractor = _extract_contractor(data, tipo)
            if contractor:
                contratistas.append(contractor)

    print(f"  Encontrados: {len(contratistas)} contratistas {tipo}")
    return contratistas


def _scrape_mop_list(soup: BeautifulSoup, tipo: str) -> list[dict]:
    """Fallback: buscar contratistas en listas o texto."""
    contratistas = []
    # Buscar en el contenido principal
    content = soup.find("div", class_=re.compile(r"entry|content|article", re.I))
    if not content:
        content = soup.find("main") or soup.find("article") or soup

    # Patrón de RUT chileno
    rut_pattern = re.compile(r"(\d{1,2}\.\d{3}\.\d{3}-[\dkK])")

    # Buscar items de lista
    items = content.find_all("li")
    for item in items:
        text = item.get_text(strip=True)
        if len(text) > 5:
            rut_match = rut_pattern.search(text)
            rut = normalizar_rut(rut_match.group(1)) if rut_match else None
            nombre = rut_pattern.sub("", text).strip(" -–:,")
            if nombre:
                contratistas.append({
                    "nombre": nombre,
                    "rut": rut,
                    "tipo_mop": tipo,
                    "categoria_mop": "",
                })

    print(f"  Encontrados (lista): {len(contratistas)} contratistas {tipo}")
    return contratistas


def _extract_contractor(data: dict, tipo: str) -> dict | None:
    """Extrae datos normalizados de un dict de una fila."""
    nombre = ""
    rut = None
    categoria = ""

    for key, val in data.items():
        key_lower = key.lower()
        if any(k in key_lower for k in ["nombre", "razón", "empresa", "contratista"]):
            nombre = val
        elif "rut" in key_lower:
            rut = normalizar_rut(val)
        elif any(k in key_lower for k in ["categ", "clase", "registro"]):
            categoria = val

    if not nombre or len(nombre) < 3:
        return None

    return {
        "nombre": nombre,
        "rut": rut,
        "tipo_mop": tipo,
        "categoria_mop": categoria,
    }


def scrape_dgop_registro() -> list[dict]:
    """
    Intenta scrape del registro DGOP.
    URL: https://dgop.mop.gob.cl/contratistas-y-consultores/
    """
    url = "https://dgop.mop.gob.cl/contratistas-y-consultores/"
    print(f"  Intentando registro DGOP: {url}")

    try:
        resp = safe_request(url, timeout=30)
        if resp is None:
            print(f"  DGOP no accesible — no es crítico")
            return []

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception:
            soup = BeautifulSoup(resp.text, "html.parser")
        # Buscar enlaces a PDFs o listas
        links = soup.find_all("a", href=True)
        pdf_links = [a for a in links if ".pdf" in a["href"].lower()
                     and "contratista" in a.get_text(strip=True).lower()]

        if pdf_links:
            print(f"  Encontrados {len(pdf_links)} PDFs de contratistas (descarga manual)")
            for link in pdf_links[:5]:
                print(f"    - {link.get_text(strip=True)}: {link['href']}")

    except Exception as e:
        print(f"  Error DGOP: {e}")

    return []


def main():
    print_header("02 — Scraping Contratistas MOP")

    all_contractors = []

    # Scrape obras mayores
    mayores = scrape_mop_page(MOP_MAYORES_URL, "mayor")
    all_contractors.extend(mayores)

    # Scrape obras menores
    menores = scrape_mop_page(MOP_MENORES_URL, "menor")
    all_contractors.extend(menores)

    # Intentar DGOP
    dgop = scrape_dgop_registro()
    all_contractors.extend(dgop)

    if not all_contractors:
        print("\nAVISO: No se obtuvieron contratistas del scraping.")
        print("El pipeline puede continuar sin este dato (scoring parcial).")
        # Crear archivo vacío para no romper pasos siguientes
        df = pd.DataFrame(columns=["nombre", "rut", "tipo_mop", "categoria_mop"])
    else:
        df = pd.DataFrame(all_contractors)
        # Dedup: por RUT donde hay RUT, por nombre donde no
        has_rut = df[df["rut"].notna()]
        no_rut = df[df["rut"].isna()]
        has_rut = has_rut.drop_duplicates(subset=["rut"], keep="first")
        no_rut = no_rut.drop_duplicates(subset=["nombre"], keep="first")
        df = pd.concat([has_rut, no_rut], ignore_index=True)

    out_path = FILTERED_DIR / "mop_contratistas.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nGuardado: {out_path}")
    print(f"  Total contratistas: {len(df)}")
    print(f"  Con RUT: {df['rut'].notna().sum()}")
    print(f"  Mayores: {(df['tipo_mop'] == 'mayor').sum()}")
    print(f"  Menores: {(df['tipo_mop'] == 'menor').sum()}")

    print("\nSiguiente paso: python 03_filter_construction.py")


if __name__ == "__main__":
    main()
