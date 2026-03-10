"""
03 - Filtra bulk CSV: solo licitaciones de construcción (UNSPSC 72*).
Lee los CSVs grandes en chunks de 50K filas para no reventar la RAM.

Resultado:
  data/filtered/tenders_construction.parquet   — licitaciones de construcción
  data/filtered/tenderers_construction.parquet  — oferentes en esas licitaciones
  data/filtered/awards_construction.parquet     — adjudicaciones
  data/filtered/suppliers_construction.parquet  — ganadores
  data/filtered/parties_construction.parquet    — detalle de empresas (RUT, nombre)

Uso:
  python 03_filter_construction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from config import RAW_DIR, FILTERED_DIR, BULK_YEARS, BULK_CSV_FILES, CONSTRUCTION_UNSPSC_PREFIX
from utils import print_header

CHUNK_SIZE = 50_000


def _prefix_links(chunk: pd.DataFrame, year: int) -> pd.DataFrame:
    """Prefija columnas _link* con el año para hacerlas únicas entre años.

    Sin esto, _link='id-0.1' en 2022 colisiona con _link='id-0.1' en 2025
    (son tenders completamente distintos).
    """
    prefix = f"{year}/"
    for col in chunk.columns:
        if col == "_link" or col.startswith("_link_"):
            mask = chunk[col].notna()
            chunk.loc[mask, col] = prefix + chunk.loc[mask, col].astype(str)
    return chunk


def find_csv(year: int, key: str) -> Path | None:
    """Busca un CSV en las carpetas de datos raw."""
    expected_name = BULK_CSV_FILES[key]
    year_dir = RAW_DIR / str(year)

    # Buscar exacto
    exact = year_dir / expected_name
    if exact.exists():
        return exact

    # Buscar variantes (a veces tienen prefijo o sufijo)
    if year_dir.exists():
        key_prefix = key.split("_")[0]
        for f in year_dir.glob("*.csv"):
            fname = f.name.lower()
            # Evitar que "tenders" matchee "tenderers" (substring)
            if fname.startswith(key_prefix) and not fname.startswith(key_prefix + "er"):
                return f
            if key_prefix in fname and f"_{key_prefix}" in fname:
                return f

    return None


def get_construction_tender_ids(years: list[int]) -> set:
    """
    Paso 1: Identificar _link_main de licitaciones de construcción.
    Usa tender_items.csv filtrando por classification_id que empiece con 72.
    Retorna set de _link_main values (join key para todos los CSVs).
    """
    print("\n--- Paso 1: Identificar licitaciones de construcción ---")
    construction_ids = set()

    for year in years:
        items_path = find_csv(year, "items")
        if not items_path:
            print(f"  AVISO: No se encontró items CSV para {year}")
            continue

        print(f"  Procesando items {year}: {items_path.name}")
        size_mb = items_path.stat().st_size / (1024 * 1024)
        print(f"  Tamaño: {size_mb:.0f} MB")

        count = 0
        for chunk in tqdm(pd.read_csv(items_path, chunksize=CHUNK_SIZE,
                                       low_memory=False, dtype=str),
                          desc=f"  Items {year}"):
            # classification_id contiene códigos UNSPSC
            if "classification_id" not in chunk.columns:
                print(f"  ERROR: No existe columna classification_id. Cols: {list(chunk.columns)}")
                break

            # _link_main es el join key hacia main.csv (_link)
            if "_link_main" not in chunk.columns:
                print(f"  ERROR: No existe columna _link_main. Cols: {list(chunk.columns)}")
                break

            chunk = _prefix_links(chunk, year)

            mask = chunk["classification_id"].astype(str).str.startswith(CONSTRUCTION_UNSPSC_PREFIX)
            matching = chunk.loc[mask]

            if len(matching) > 0:
                ids = matching["_link_main"].dropna().unique()
                construction_ids.update(ids)
                count += len(ids)

        print(f"  {year}: {count} items de construcción encontrados")

    print(f"\nTotal IDs de licitaciones de construcción: {len(construction_ids)}")
    return construction_ids


def filter_csv_by_ids(years: list[int], key: str, match_ids: set,
                      output_name: str, id_col_override: str | None = None) -> pd.DataFrame | None:
    """Filtra un CSV manteniendo solo filas cuyo join key está en match_ids.

    Para main.csv (tenders): join key = _link
    Para todos los demás: join key = _link_main
    id_col_override permite especificar una columna distinta (ej. para parties por id).
    """
    print(f"\n--- Filtrando {key} ---")
    out_path = FILTERED_DIR / f"{output_name}.parquet"

    all_batches = []

    for year in years:
        csv_path = find_csv(year, key)
        if not csv_path:
            print(f"  AVISO: No se encontró {key} CSV para {year}")
            continue

        print(f"  Procesando {key} {year}: {csv_path.name}")

        id_col = id_col_override
        first_chunk_key = True
        for chunk in tqdm(pd.read_csv(csv_path, chunksize=CHUNK_SIZE,
                                       low_memory=False, dtype=str),
                          desc=f"  {key} {year}"):
            if first_chunk_key:
                first_chunk_key = False
                if id_col is None:
                    # main.csv usa _link; el resto usa _link_main
                    if "_link_main" in chunk.columns:
                        id_col = "_link_main"
                    elif "_link" in chunk.columns:
                        id_col = "_link"
                    else:
                        print(f"  WARNING: No se encontró _link/_link_main en {key} {year}. "
                              f"Cols: {list(chunk.columns)}")
                        break
                print(f"  Join key: {id_col}")

            if id_col not in chunk.columns:
                break

            chunk = _prefix_links(chunk, year)

            mask = chunk[id_col].isin(match_ids)
            matching = chunk.loc[mask]
            if len(matching) > 0:
                all_batches.append(matching)

    if not all_batches:
        print(f"  Sin resultados para {key}")
        return None

    df = pd.concat(all_batches, ignore_index=True)
    df.to_parquet(out_path, index=False)
    print(f"  Guardado: {out_path} ({len(df)} filas, {out_path.stat().st_size/(1024*1024):.1f} MB)")
    return df


def main():
    print_header("03 — Filtrar Construcción del Bulk CSV")

    years = BULK_YEARS

    # Verificar que existen datos raw
    has_data = False
    for year in years:
        year_dir = RAW_DIR / str(year)
        if year_dir.exists() and list(year_dir.glob("*.csv")):
            has_data = True
            csvs = list(year_dir.glob("*.csv"))
            print(f"  {year}: {len(csvs)} archivos CSV")
            for csv in csvs:
                print(f"    - {csv.name} ({csv.stat().st_size/(1024*1024):.0f} MB)")

    if not has_data:
        print("\nERROR: No hay datos raw descargados.")
        print("Ejecuta primero: python 01_download_bulk.py")
        sys.exit(1)

    # Paso 1: IDs de construcción
    construction_ids = get_construction_tender_ids(years)

    if not construction_ids:
        print("\nERROR: No se encontraron licitaciones de construcción.")
        print("Verificar que los CSV tienen la estructura esperada.")
        sys.exit(1)

    # Paso 2: Filtrar cada CSV relevante
    # main.csv usa _link como join key (no tiene _link_main)
    filter_csv_by_ids(years, "tenders", construction_ids, "tenders_construction",
                      id_col_override="_link")
    # Los demás usan _link_main automáticamente
    filter_csv_by_ids(years, "tenderers", construction_ids, "tenderers_construction")
    filter_csv_by_ids(years, "awards", construction_ids, "awards_construction")
    filter_csv_by_ids(years, "suppliers", construction_ids, "suppliers_construction")

    # Paso 3: Parties — filtrar por _link_main (mismos IDs de tender)
    print("\n--- Extrayendo parties (empresas) ---")
    filter_csv_by_ids(years, "parties", construction_ids, "parties_construction")

    # Resumen
    print("\n--- Resumen ---")
    for pq in FILTERED_DIR.glob("*_construction.parquet"):
        df = pd.read_parquet(pq)
        print(f"  {pq.name}: {len(df)} filas, {pq.stat().st_size/(1024*1024):.1f} MB")

    print("\nSiguiente paso: python 04_build_company_db.py")


if __name__ == "__main__":
    main()
