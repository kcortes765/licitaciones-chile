"""
04 - Construye base de datos de empresas constructoras cruzando por RUT.
Merge: tenderers + suppliers + parties + MOP contratistas

Resultado: data/filtered/company_database.parquet
Columnas por empresa:
  - rut, nombre, region
  - total_bids, total_wins, win_rate
  - monto_promedio, monto_total
  - ultima_oferta, primera_oferta
  - competidores_promedio
  - tipos_licitacion (dict con conteo L1/LE/LP)
  - categoria_mop (si está en registro MOP)
  - especializaciones (tipos de obra)

Uso:
  python 04_build_company_db.py
"""
from __future__ import annotations

import sys
from datetime import datetime

import pandas as pd
import numpy as np

from config import FILTERED_DIR
from pipeline_validation import assert_dataframe_contract
from utils import normalizar_rut, extraer_rut_de_id, tipo_licitacion, print_header, is_persona_natural


def load_parquet_safe(name: str) -> pd.DataFrame | None:
    """Carga un parquet filtrado, retorna None si no existe."""
    path = FILTERED_DIR / f"{name}.parquet"
    if not path.exists():
        print(f"  AVISO: {path.name} no existe")
        return None
    df = pd.read_parquet(path)
    print(f"  Cargado {path.name}: {len(df)} filas, {len(df.columns)} cols")
    return df


def find_column(df: pd.DataFrame, keywords: list[str]) -> str | None:
    """Encuentra una columna por keywords parciales."""
    for col in df.columns:
        col_lower = col.lower()
        if any(k in col_lower for k in keywords):
            return col
    return None


def extract_ruts_from_df(df: pd.DataFrame) -> pd.Series:
    """Intenta extraer RUTs de cualquier columna que los contenga."""
    for col in df.columns:
        if any(k in col.lower() for k in ["rut", "party_id", "identifier", "id"]):
            ruts = df[col].apply(lambda x: extraer_rut_de_id(str(x)) if pd.notna(x) else None)
            if ruts.notna().sum() > 0:
                return ruts
    return pd.Series([None] * len(df), index=df.index)


def build_tenderer_stats(tenderers_df: pd.DataFrame,
                         tenders_df: pd.DataFrame | None) -> pd.DataFrame:
    """Calcula estadísticas de ofertas por empresa."""
    print("\n--- Calculando estadísticas de ofertas ---")

    # Extraer RUT de tenderers
    tenderers_df["rut"] = extract_ruts_from_df(tenderers_df)
    tenderers_df = tenderers_df[tenderers_df["rut"].notna()].copy()
    print(f"  Tenderers con RUT válido: {len(tenderers_df)}")

    # Si tenemos tenders, cruzar para obtener fechas y montos
    # Join key: tenderers._link_main ↔ tenders._link
    if tenders_df is not None:
        date_col = find_column(tenders_df, ["date", "fecha", "published"])
        amount_col = find_column(tenders_df, ["amount", "value", "monto", "estimat"])
        code_col = find_column(tenders_df, ["procurementmethoddetails", "code", "codigo"])

        merge_cols = ["_link"] + [c for c in [date_col, amount_col, code_col] if c]
        merge_cols = [c for c in merge_cols if c in tenders_df.columns]

        print(f"  Join: tenderers._link_main <-> tenders._link")
        print(f"  date_col={date_col}, amount_col={amount_col}, code_col={code_col}")

        merged = tenderers_df.merge(
            tenders_df[merge_cols].drop_duplicates(subset=["_link"]),
            left_on="_link_main",
            right_on="_link",
            how="left"
        )
        match_pct = merged["_link_y"].notna().sum() if "_link_y" in merged.columns else merged[date_col].notna().sum() if date_col else 0
        print(f"  Match: {match_pct}/{len(merged)} ({100*match_pct/len(merged):.0f}%)")
    else:
        merged = tenderers_df.copy()
        date_col = find_column(merged, ["date", "fecha"])
        amount_col = find_column(merged, ["amount", "value", "monto"])
        code_col = find_column(merged, ["procurementmethoddetails", "code", "codigo"])

    # Parsear fechas - usar la más reciente entre múltiples columnas
    if date_col and date_col in merged.columns:
        merged["_fecha"] = pd.to_datetime(merged[date_col], errors="coerce", utc=True).dt.tz_convert(None)
    else:
        merged["_fecha"] = pd.NaT

    # Suplementar con fechas de award/tender period (más recientes cuando existen)
    for alt_date_col in ["tender_awardPeriod_startDate", "tender_tenderPeriod_startDate"]:
        if alt_date_col in merged.columns:
            alt_dates = pd.to_datetime(merged[alt_date_col], errors="coerce", utc=True).dt.tz_convert(None)
            mask = alt_dates.notna() & (merged["_fecha"].isna() | (alt_dates > merged["_fecha"]))
            merged.loc[mask, "_fecha"] = alt_dates[mask]

    # Parsear montos
    if amount_col and amount_col in merged.columns:
        merged["_monto"] = pd.to_numeric(merged[amount_col], errors="coerce")
    else:
        merged["_monto"] = np.nan

    # Extraer tipo de licitación
    if code_col and code_col in merged.columns:
        merged["_tipo"] = merged[code_col].apply(
            lambda x: tipo_licitacion(str(x)) if pd.notna(x) else "Otro"
        )
    else:
        merged["_tipo"] = "Otro"

    # Agrupar por RUT
    now = pd.Timestamp.now()

    def agg_empresa(group):
        return pd.Series({
            "total_bids": len(group),
            "monto_promedio": group["_monto"].mean(),
            "monto_total": group["_monto"].sum(),
            "ultima_oferta": group["_fecha"].max(),
            "primera_oferta": group["_fecha"].min(),
            "dias_desde_ultima": (now - group["_fecha"].max()).days
                                 if pd.notna(group["_fecha"].max()) else 9999,
            "tipos_licitacion": group["_tipo"].value_counts().to_dict(),
            "n_LP": (group["_tipo"] == "LP").sum(),
            "n_LE": (group["_tipo"] == "LE").sum(),
            "n_L1": (group["_tipo"] == "L1").sum(),
        })

    if len(merged) == 0:
        print(f"  Empresas únicas (oferentes): 0")
        return pd.DataFrame(columns=["rut", "total_bids", "monto_promedio", "monto_total",
                                      "ultima_oferta", "primera_oferta", "dias_desde_ultima",
                                      "tipos_licitacion", "n_LP", "n_LE", "n_L1"])

    try:
        stats = merged.groupby("rut").apply(agg_empresa, include_groups=False).reset_index()
    except TypeError:
        result = merged.groupby("rut").apply(agg_empresa)
        if "rut" in result.columns:
            result = result.drop(columns=["rut"])
        stats = result.reset_index()
    print(f"  Empresas únicas (oferentes): {len(stats)}")
    return stats


def build_winner_stats(suppliers_df: pd.DataFrame) -> pd.DataFrame:
    """Calcula estadísticas de adjudicaciones por empresa."""
    print("\n--- Calculando estadísticas de adjudicaciones ---")

    suppliers_df["rut"] = extract_ruts_from_df(suppliers_df)
    suppliers_df = suppliers_df[suppliers_df["rut"].notna()].copy()

    amount_col = find_column(suppliers_df, ["amount", "value", "monto"])

    if amount_col:
        suppliers_df["_monto_adj"] = pd.to_numeric(suppliers_df[amount_col], errors="coerce")
    else:
        suppliers_df["_monto_adj"] = np.nan

    wins = suppliers_df.groupby("rut").agg(
        total_wins=("rut", "count"),
        monto_adjudicado=("_monto_adj", "sum"),
    ).reset_index()

    print(f"  Empresas con adjudicaciones: {len(wins)}")
    return wins


def build_names(parties_df: pd.DataFrame) -> pd.DataFrame:
    """Extrae nombres y regiones de parties."""
    print("\n--- Extrayendo nombres de empresas ---")

    parties_df["rut"] = extract_ruts_from_df(parties_df)
    parties_df = parties_df[parties_df["rut"].notna()].copy()

    name_col = find_column(parties_df, ["name", "nombre", "legal"])
    region_col = find_column(parties_df, ["region", "locality", "address", "country_name"])

    result = parties_df.groupby("rut").first().reset_index()
    cols = ["rut"]
    if name_col:
        result = result.rename(columns={name_col: "nombre"})
        cols.append("nombre")
    if region_col:
        result = result.rename(columns={region_col: "region"})
        cols.append("region")

    result = result[[c for c in cols if c in result.columns]]
    print(f"  Empresas con nombre: {len(result)}")
    return result


def calculate_competition(tenderers_df: pd.DataFrame) -> pd.DataFrame:
    """Calcula competidores promedio por empresa."""
    print("\n--- Calculando competencia promedio ---")

    tenderers_df["rut"] = extract_ruts_from_df(tenderers_df)

    # Usar _link_main como clave de tender (agrupa por licitación, no por row)
    tender_id_col = "_link_main"
    if tender_id_col not in tenderers_df.columns:
        tender_id_col = find_column(tenderers_df, ["tender_id", "ocid", "release"])
        if tender_id_col is None:
            tender_id_col = tenderers_df.columns[0]
        print(f"  AVISO: _link_main no encontrado, usando {tender_id_col}")

    # Contar oferentes por licitación
    offers_per_tender = tenderers_df.groupby(tender_id_col).size().rename("n_oferentes")

    # Merge back
    merged = tenderers_df.merge(offers_per_tender, on=tender_id_col, how="left")
    merged = merged[merged["rut"].notna()]

    competition = merged.groupby("rut")["n_oferentes"].mean().reset_index()
    competition.columns = ["rut", "competidores_promedio"]

    print(f"  Calculado para {len(competition)} empresas")
    print(f"  Competidores promedio: {competition['competidores_promedio'].mean():.1f} "
          f"(max: {competition['competidores_promedio'].max():.0f})")
    return competition


def compute_loss_stats(tenderers_df: pd.DataFrame,
                       suppliers_df: pd.DataFrame | None) -> pd.DataFrame:
    """Calcula derrotas y rivales por empresa para score_oportunidad."""
    print("\n--- Calculando estadísticas de derrotas ---")

    tdr = tenderers_df.copy()
    tdr["_rut"] = extract_ruts_from_df(tdr)
    tdr = tdr[tdr["_rut"].notna()][["_link_main", "_rut"]]

    if suppliers_df is None or len(tdr) == 0:
        print("  Sin datos de suppliers, saltando")
        return pd.DataFrame(columns=["rut", "total_lost", "n_distinct_rivals"])

    sup = suppliers_df.copy()
    sup["_winner_rut"] = extract_ruts_from_df(sup)
    sup = sup[sup["_winner_rut"].notna()][["_link_main", "_winner_rut"]]
    winner_map = sup.drop_duplicates(subset=["_link_main"]).set_index("_link_main")["_winner_rut"]

    tdr["_winner"] = tdr["_link_main"].map(winner_map)
    tdr["_lost"] = tdr["_winner"].notna() & (tdr["_winner"] != tdr["_rut"])

    loss_counts = tdr.groupby("_rut")["_lost"].sum().reset_index()
    loss_counts.columns = ["rut", "total_lost"]
    loss_counts["total_lost"] = loss_counts["total_lost"].astype(int)

    lost_rows = tdr[tdr["_lost"]]
    if len(lost_rows) > 0:
        rival_counts = lost_rows.groupby("_rut")["_winner"].nunique().reset_index()
        rival_counts.columns = ["rut", "n_distinct_rivals"]
    else:
        rival_counts = pd.DataFrame(columns=["rut", "n_distinct_rivals"])

    result = loss_counts.merge(rival_counts, on="rut", how="left")
    result["n_distinct_rivals"] = result["n_distinct_rivals"].fillna(0).astype(int)

    with_losses = (result["total_lost"] > 0).sum()
    print(f"  Empresas con derrotas: {with_losses}/{len(result)}")
    print(f"  Promedio derrotas: {result['total_lost'].mean():.1f}")
    print(f"  Promedio rivales distintos: {result['n_distinct_rivals'].mean():.1f}")
    return result


def main():
    print_header("04 — Construir Base de Datos de Empresas")

    # Cargar datos filtrados
    tenderers_df = load_parquet_safe("tenderers_construction")
    suppliers_df = load_parquet_safe("suppliers_construction")
    parties_df = load_parquet_safe("parties_construction")
    tenders_df = load_parquet_safe("tenders_construction")
    mop_df = load_parquet_safe("mop_contratistas")

    if tenderers_df is None:
        print("\nERROR: No hay datos de tenderers filtrados.")
        print("Ejecuta primero: python 03_filter_construction.py")
        sys.exit(1)

    # Construir cada componente
    bid_stats = build_tenderer_stats(tenderers_df.copy(), tenders_df)
    companies = bid_stats.copy()

    # Merge wins
    if suppliers_df is not None:
        win_stats = build_winner_stats(suppliers_df)
        companies = companies.merge(win_stats, on="rut", how="left")
        companies["total_wins"] = companies["total_wins"].fillna(0).astype(int)
    else:
        companies["total_wins"] = 0
        companies["monto_adjudicado"] = 0

    # Win rate (capped at 1.0 — wins puede exceder bids por fuentes distintas)
    companies["win_rate"] = (companies["total_wins"] / companies["total_bids"].clip(lower=1)).clip(upper=1.0)

    # Suplementar monto_promedio desde awards (89% cobertura vs 41%)
    awards_path = FILTERED_DIR / "awards_construction.parquet"
    if awards_path.exists() and suppliers_df is not None:
        print("\n--- Suplementando montos desde awards ---")
        awards_df = pd.read_parquet(awards_path)

        if "_link_awards" in suppliers_df.columns and "_link" in awards_df.columns:
            suppliers_copy = suppliers_df.copy()
            suppliers_copy["_rut"] = extract_ruts_from_df(suppliers_copy)
            award_amount_col = find_column(awards_df, ["value_amount", "amount"])

            if award_amount_col:
                suppliers_with_amount = suppliers_copy.merge(
                    awards_df[["_link", award_amount_col]].drop_duplicates(subset=["_link"]),
                    left_on="_link_awards",
                    right_on="_link",
                    how="left",
                    suffixes=("", "_award")
                )
                suppliers_with_amount["_amount"] = pd.to_numeric(
                    suppliers_with_amount[award_amount_col], errors="coerce"
                )

                award_montos = (suppliers_with_amount[suppliers_with_amount["_rut"].notna()]
                               .groupby("_rut")["_amount"]
                               .mean()
                               .reset_index()
                               .rename(columns={"_rut": "rut", "_amount": "monto_promedio_awards"}))

                companies = companies.merge(award_montos, on="rut", how="left")

                mask_no_monto = companies["monto_promedio"].isna() | (companies["monto_promedio"] == 0)
                filled = mask_no_monto & companies["monto_promedio_awards"].notna()
                companies.loc[filled, "monto_promedio"] = companies.loc[filled, "monto_promedio_awards"]
                companies.drop(columns=["monto_promedio_awards"], inplace=True)
                print(f"  Montos suplementados desde awards: {filled.sum()}")
                print(f"  monto_promedio cobertura: {companies['monto_promedio'].notna().sum()}/{len(companies)} "
                      f"({100*companies['monto_promedio'].notna().sum()/len(companies):.0f}%)")

    # Merge nombres
    if parties_df is not None:
        names = build_names(parties_df)
        companies = companies.merge(names, on="rut", how="left")

    # Competencia
    competition = calculate_competition(tenderers_df.copy())
    companies = companies.merge(competition, on="rut", how="left")

    # Derrotas y rivales (para score_oportunidad)
    loss_stats = compute_loss_stats(tenderers_df.copy(), suppliers_df)
    if len(loss_stats) > 0:
        companies = companies.merge(loss_stats, on="rut", how="left")
        companies["total_lost"] = companies["total_lost"].fillna(0).astype(int)
        companies["n_distinct_rivals"] = companies["n_distinct_rivals"].fillna(0).astype(int)
    else:
        companies["total_lost"] = 0
        companies["n_distinct_rivals"] = 0

    # MOP categoría
    if mop_df is not None and len(mop_df) > 0 and "rut" in mop_df.columns:
        mop_cols = [c for c in ["rut", "tipo_mop", "categoria_mop"] if c in mop_df.columns]
        if "rut" in mop_cols:
            mop_clean = mop_df[mop_df["rut"].notna()][mop_cols].drop_duplicates(subset=["rut"])
            companies = companies.merge(mop_clean, on="rut", how="left")
    else:
        companies["tipo_mop"] = None
        companies["categoria_mop"] = None

    # Ensure tipo_mop and categoria_mop always exist after MOP merge
    for col in ["tipo_mop", "categoria_mop"]:
        if col not in companies.columns:
            companies[col] = None

    # Detectar personas naturales
    if "nombre" in companies.columns:
        companies["es_persona_natural"] = companies["nombre"].apply(is_persona_natural)
        n_personas = companies["es_persona_natural"].sum()
        print(f"\n  Personas naturales detectadas: {n_personas}/{len(companies)}")
    else:
        companies["es_persona_natural"] = False

    # Reordenar columnas
    col_order = [
        "rut", "nombre", "region",
        "total_bids", "total_wins", "win_rate",
        "monto_promedio", "monto_total", "monto_adjudicado",
        "ultima_oferta", "primera_oferta", "dias_desde_ultima",
        "n_LP", "n_LE", "n_L1",
        "competidores_promedio",
        "total_lost", "n_distinct_rivals",
        "tipo_mop", "categoria_mop",
        "es_persona_natural",
    ]
    existing_cols = [c for c in col_order if c in companies.columns]
    extra_cols = [c for c in companies.columns if c not in col_order]
    companies = companies[existing_cols + extra_cols]

    # Guardar
    out_path = FILTERED_DIR / "company_database.parquet"
    assert_dataframe_contract(companies, "company_database")
    companies.to_parquet(out_path, index=False)

    print(f"\n{'='*60}")
    print(f"  COMPANY DATABASE")
    print(f"{'='*60}")
    print(f"  Archivo: {out_path}")
    print(f"  Total empresas: {len(companies)}")
    print(f"  Con nombre: {companies['nombre'].notna().sum() if 'nombre' in companies.columns else 'N/A'}")
    print(f"  Con adjudicaciones: {(companies['total_wins'] > 0).sum()}")
    print(f"  En registro MOP: {companies['tipo_mop'].notna().sum()}")
    print(f"  Win rate promedio: {companies['win_rate'].mean():.1%}")
    print(f"  Bids promedio: {companies['total_bids'].mean():.1f}")

    # Preview top empresas por actividad
    top = companies.nlargest(10, "total_bids")
    print(f"\n  Top 10 más activas:")
    for _, row in top.iterrows():
        nombre = row.get("nombre", row["rut"])
        if pd.isna(nombre):
            nombre = row["rut"]
        print(f"    {nombre}: {row['total_bids']} bids, "
              f"{row['total_wins']} wins ({row['win_rate']:.0%})")

    print(f"\nSiguiente paso: python 05_score_leads.py")


if __name__ == "__main__":
    main()
