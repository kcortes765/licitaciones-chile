"""
Prepara una muestra manual y determinista para revisar calidad de leads.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import OUTPUT_DIR
from pipeline_core import load_best_leads_dataframe, resolve_rank_column, resolve_score_column
from utils import print_header


def main() -> None:
    print_header("13 - Muestra Manual de Leads")
    leads, source_path = load_best_leads_dataframe()
    rank_col = resolve_rank_column(leads)
    score_col = resolve_score_column(leads)
    leads = leads.sort_values(rank_col).reset_index(drop=True)

    top = leads.head(25)
    middle_start = max(0, len(leads) // 2 - 12)
    middle = leads.iloc[middle_start:middle_start + 25]
    bottom = leads.tail(25)
    sample = pd.concat([top, middle, bottom], ignore_index=True).drop_duplicates(subset=["rut"])

    review = pd.DataFrame({
        "segmento_muestra": (["top"] * len(top)) + (["medio"] * len(middle)) + (["descarte"] * len(bottom)),
    }).iloc[:len(sample)].copy()
    review["rut"] = sample["rut"].values
    review["empresa"] = sample.get("nombre", sample["rut"]).values
    review["score"] = sample[score_col].values
    review["rank"] = sample[rank_col].values
    review["telefono"] = sample["telefono"].values if "telefono" in sample.columns else ""
    review["email"] = sample["email"].values if "email" in sample.columns else ""
    review["web"] = sample["web"].values if "web" in sample.columns else ""
    review["empresa_real"] = ""
    review["target_correcto"] = ""
    review["contactable"] = ""
    review["dolor_visible"] = ""
    review["observaciones"] = ""

    xlsx_path = OUTPUT_DIR / "lead_review_sample.xlsx"
    csv_path = OUTPUT_DIR / "lead_review_sample.csv"
    review.to_excel(xlsx_path, index=False)
    review.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"Muestra generada desde {source_path.name}: {xlsx_path}")


if __name__ == "__main__":
    main()

