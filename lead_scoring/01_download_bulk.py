"""
01 - Descarga y descomprime bulk CSV de datos-abiertos ChileCompra.
Fuente: data.open-contracting.org (publicación 144 = Chile)

Descarga 2024 + 2025 (~1.4GB total), descomprime y extrae solo los CSV necesarios.

Uso:
  python 01_download_bulk.py              # Descarga 2024+2025
  python 01_download_bulk.py --year 2025  # Solo un año
"""
from __future__ import annotations

import sys
import tarfile
from pathlib import Path

import requests
from tqdm import tqdm

from config import RAW_DIR, BULK_YEARS, BULK_CSV_FILES
from utils import print_header

# URL de descarga del portal OCDS - formato CSV por año
DOWNLOAD_URL = "https://data.open-contracting.org/en/publication/144/download"


def download_year(year: int) -> Path | None:
    """Descarga el tar.gz de un año específico."""
    dest = RAW_DIR / f"chilecompra_{year}.tar.gz"

    if dest.exists():
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  Ya existe {dest.name} ({size_mb:.0f} MB) — saltando descarga")
        return dest

    print(f"  Descargando datos {year}...")

    # URL correcta: ?name=YEAR.csv.tar.gz
    url = f"{DOWNLOAD_URL}?name={year}.csv.tar.gz"
    resp = requests.get(url, stream=True, timeout=(30, 600),
                        headers={"User-Agent": "Mozilla/5.0"},
                        allow_redirects=True)

    if resp.status_code != 200:
        resp.close()
        # Fallback: intentar con parámetros separados
        print(f"  Código {resp.status_code}, intentando formato alternativo...")
        alt_url = f"{DOWNLOAD_URL}?name=full.csv.tar.gz"
        resp = requests.get(alt_url, stream=True, timeout=(30, 600),
                            headers={"User-Agent": "Mozilla/5.0"},
                            allow_redirects=True)

    if resp.status_code != 200:
        resp.close()
        print(f"  ERROR: No se pudo descargar ({resp.status_code})")
        print(f"  Descarga manual: {DOWNLOAD_URL}?name={year}.csv.tar.gz")
        print(f"  Guardar como: {dest}")
        return None

    total = int(resp.headers.get("content-length", 0))
    tmp_dest = dest.with_suffix(".tmp")
    try:
        with open(tmp_dest, "wb") as f:
            with tqdm(total=total, unit="B", unit_scale=True, desc=f"  {year}") as pbar:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    pbar.update(len(chunk))
        tmp_dest.replace(dest)
    except Exception:
        tmp_dest.unlink(missing_ok=True)
        raise
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  Descargado: {dest.name} ({size_mb:.0f} MB)")
    return dest


def extract_csvs(tar_path: Path, year: int):
    """Extrae solo los CSV necesarios del tar.gz."""
    year_dir = RAW_DIR / str(year)
    year_dir.mkdir(exist_ok=True)

    needed = set(BULK_CSV_FILES.values())
    already = {f.name for f in year_dir.glob("*.csv")}
    missing = needed - already

    if not missing:
        print(f"  Todos los CSV de {year} ya extraídos — saltando")
        return

    print(f"  Extrayendo {len(missing)} CSVs de {year}...")

    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            for member in tar.getmembers():
                fname = Path(member.name).name
                if fname in missing:
                    print(f"    {fname} ({member.size / (1024*1024):.0f} MB)")
                    member.name = fname  # Extraer sin subdirectorios
                    tar.extract(member, path=year_dir)
    except tarfile.TarError as e:
        print(f"  Error extrayendo: {e}")
        print(f"  Intenta descomprimir manualmente {tar_path} en {year_dir}/")
        return

    extracted = {f.name for f in year_dir.glob("*.csv")}
    print(f"  Extraídos: {len(extracted & needed)}/{len(needed)} archivos necesarios")

    still_missing = needed - extracted
    if still_missing:
        print(f"  AVISO: Faltan: {still_missing}")
        print(f"  Los nombres pueden variar. Archivos disponibles:")
        with tarfile.open(tar_path, "r:gz") as tar:
            csv_names = [Path(m.name).name for m in tar.getmembers()
                         if m.name.endswith(".csv")]
            for n in sorted(csv_names):
                print(f"    - {n}")


def main():
    print_header("01 — Descarga Bulk CSV ChileCompra")

    years = BULK_YEARS
    if "--year" in sys.argv:
        idx = sys.argv.index("--year")
        if idx + 1 >= len(sys.argv):
            print("Error: --year requiere un valor")
            sys.exit(1)
        try:
            years = [int(sys.argv[idx + 1])]
        except ValueError:
            print(f"Error: '{sys.argv[idx + 1]}' no es un año válido")
            sys.exit(1)

    for year in years:
        print(f"\n--- Año {year} ---")
        tar_path = download_year(year)
        if tar_path and tar_path.exists():
            extract_csvs(tar_path, year)

    # Verificar resultado
    print("\n--- Verificación ---")
    for year in years:
        year_dir = RAW_DIR / str(year)
        if year_dir.exists():
            csvs = list(year_dir.glob("*.csv"))
            total_mb = sum(f.stat().st_size for f in csvs) / (1024 * 1024)
            print(f"  {year}: {len(csvs)} archivos CSV ({total_mb:.0f} MB)")
        else:
            print(f"  {year}: No descargado")

    print("\nSiguiente paso: python 02_scrape_mop.py")


if __name__ == "__main__":
    main()
