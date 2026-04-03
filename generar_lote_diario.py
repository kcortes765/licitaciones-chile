"""
Generador de lotes diarios para outreach WhatsApp — Ola 1.

Lee leads_verificados_v7.xlsx y genera 9 CSVs (3 cuentas x 3 dias)
listos para envio manual. Cada CSV tiene 5 leads en orden de prioridad.

Asignacion de cuentas (segun OUTREACH_PLAYBOOK.md):
  Cuenta A (rivalry):    rival_fuerte + rival_recurrente + rival_unico + default(1)
  Cuenta B (performance): lp_alto + win_rate_gap_LP(5) + wr_bajo_lp
  Cuenta C (inactivity):  inactivo + win_rate_gap_LP(2) + wr_bajo + default(2)

Uso:
  python generar_lote_diario.py
"""
import pandas as pd
from pathlib import Path

# --- Paths -------------------------------------------------------------------
BASE_DIR = Path(__file__).parent / "lead_scoring" / "data"
INPUT_XLSX = BASE_DIR / "output" / "leads_verificados_v7.xlsx"
OUTPUT_DIR = BASE_DIR / "output" / "lotes"

# --- Capacidades por cuenta --------------------------------------------------
LEADS_PER_ACCOUNT = 15
LEADS_PER_DAY = 5
NUM_DAYS = 3

# Tipos primarios por cuenta (se asignan completos a esta cuenta)
ACCOUNT_PRIMARY = {
    "A": ["rival_fuerte", "rival_recurrente", "rival_unico"],
    "B": ["lp_alto", "wr_bajo_lp"],
    "C": ["inactivo", "wr_bajo"],
}

# Tipos compartidos: se reparten entre cuentas para balancear a 15
# Formato: tipo -> [(cuenta, cantidad), ...]
ACCOUNT_SHARED = {
    "win_rate_gap_LP": [("B", 5), ("C", 2)],
    "default": [("A", 1), ("C", 2)],
}


# --- Helpers NaN-safe --------------------------------------------------------

def _safe_str(v, default=""):
    if v is None:
        return default
    try:
        f = float(v)
        if f != f:
            return default
    except (ValueError, TypeError):
        pass
    return str(v)


def _safe_int(v, default=0):
    if v is None:
        return default
    try:
        f = float(v)
        if f != f:
            return default
        return int(f)
    except (ValueError, TypeError):
        return default


# --- Asignacion de cuentas ---------------------------------------------------

def assign_accounts(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna wsp_account (A/B/C) a cada lead segun insight_tipo y outreach_rank."""
    df = df.sort_values("outreach_rank").copy()
    df["wsp_account"] = ""

    # Paso 1: asignar tipos primarios (completos a su cuenta)
    for account, tipos in ACCOUNT_PRIMARY.items():
        mask = df["insight_tipo"].isin(tipos) & (df["wsp_account"] == "")
        df.loc[mask, "wsp_account"] = account

    # Paso 2: asignar tipos compartidos (repartir por outreach_rank)
    for tipo, distribuciones in ACCOUNT_SHARED.items():
        tipo_df = df[(df["insight_tipo"] == tipo) & (df["wsp_account"] == "")]
        tipo_indices = tipo_df.index.tolist()
        offset = 0
        for account, cantidad in distribuciones:
            batch = tipo_indices[offset:offset + cantidad]
            df.loc[batch, "wsp_account"] = account
            offset += cantidad

    # Verificar que no queden sin asignar
    sin_asignar = df[df["wsp_account"] == ""]
    if len(sin_asignar) > 0:
        # Asignar excedentes a la cuenta con menos leads
        for idx in sin_asignar.index:
            counts = df[df["wsp_account"] != ""]["wsp_account"].value_counts()
            for acc in ["A", "B", "C"]:
                if counts.get(acc, 0) < LEADS_PER_ACCOUNT:
                    df.loc[idx, "wsp_account"] = acc
                    break
            else:
                # Si todas estan llenas, asignar a C como overflow
                df.loc[idx, "wsp_account"] = "C"

    return df


def assign_days_and_order(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna send_day (1/2/3) y batch_order (1-5) dentro de cada cuenta."""
    df = df.copy()
    df["send_day"] = 0
    df["batch_order"] = 0

    for account in ["A", "B", "C"]:
        mask = df["wsp_account"] == account
        account_df = df.loc[mask].sort_values("outreach_rank")
        indices = account_df.index.tolist()

        for i, idx in enumerate(indices):
            day = (i // LEADS_PER_DAY) + 1
            order = (i % LEADS_PER_DAY) + 1
            df.loc[idx, "send_day"] = day
            df.loc[idx, "batch_order"] = order

    return df


def assign_template_variants(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna template_variant (A/B/C/D) con round-robin por cuenta."""
    df = df.copy()
    df["template_variant"] = "A"
    variants = ["A", "B", "C", "D"]

    for account in ["A", "B", "C"]:
        mask = df["wsp_account"] == account
        account_df = df.loc[mask].sort_values(["send_day", "batch_order"])
        indices = account_df.index.tolist()

        for i, idx in enumerate(indices):
            df.loc[idx, "template_variant"] = variants[i % len(variants)]

    return df


# --- Main --------------------------------------------------------------------

def main():
    print("=== Generador de Lotes Diarios — Ola 1 ===\n")

    if not INPUT_XLSX.exists():
        print(f"ERROR: No se encontro {INPUT_XLSX}")
        print("Ejecutar primero: python generar_mensajes_v7.py")
        return

    # Leer datos
    df = pd.read_excel(INPUT_XLSX, sheet_name="WhatsApp Listos")
    print(f"Leads cargados: {len(df)}")

    if len(df) == 0:
        print("No hay leads para procesar.")
        return

    # Asignar cuentas, dias y variantes
    df = assign_accounts(df)
    df = assign_days_and_order(df)
    df = assign_template_variants(df)

    # Verificar distribucion
    print(f"\nDistribucion por cuenta:")
    for acc in ["A", "B", "C"]:
        n = len(df[df["wsp_account"] == acc])
        tipos = df[df["wsp_account"] == acc]["insight_tipo"].value_counts()
        print(f"  Cuenta {acc}: {n} leads")
        for tipo, cnt in tipos.items():
            print(f"    {tipo}: {cnt}")

    # Crear directorio de salida
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Columnas de salida
    out_columns = [
        "empresa", "rut", "telefono", "wsp_link", "mensaje",
        "insight_tipo", "template_variant", "send_day", "batch_order",
    ]

    # Generar CSVs
    archivos_generados = []
    for account in ["A", "B", "C"]:
        for day in range(1, NUM_DAYS + 1):
            mask = (df["wsp_account"] == account) & (df["send_day"] == day)
            lote = df.loc[mask].sort_values("batch_order").copy()

            # Mapear columnas al formato de salida
            lote_out = pd.DataFrame()
            lote_out["empresa"] = lote["empresa_display"].apply(
                lambda x: _safe_str(x, "Sin nombre")
            )
            lote_out["rut"] = lote["rut"].apply(lambda x: _safe_str(x))
            lote_out["telefono"] = lote["telefono_normalizado"].apply(
                lambda x: _safe_str(x)
            )
            lote_out["wsp_link"] = lote["wsp_link"].apply(
                lambda x: _safe_str(x)
            )
            lote_out["mensaje"] = lote["wsp_mensaje"].apply(
                lambda x: _safe_str(x)
            )
            lote_out["insight_tipo"] = lote["insight_tipo"].values
            lote_out["template_variant"] = lote["template_variant"].values
            lote_out["send_day"] = lote["send_day"].values
            lote_out["batch_order"] = lote["batch_order"].values

            filename = f"lote_cuenta_{account}_dia{day}.csv"
            filepath = OUTPUT_DIR / filename
            lote_out.to_csv(filepath, index=False, encoding="utf-8-sig")
            archivos_generados.append(filename)
            print(f"  {filename}: {len(lote_out)} leads")

    print(f"\n{len(archivos_generados)} archivos generados en {OUTPUT_DIR}")

    # Resumen final
    print(f"\n{'=' * 50}")
    print("RESUMEN OLA 1")
    print(f"{'=' * 50}")
    total = len(df)
    print(f"Total leads: {total}")
    for day in range(1, NUM_DAYS + 1):
        n_day = len(df[df["send_day"] == day])
        print(f"  Dia {day}: {n_day} mensajes ({n_day // 3} por cuenta)")
    print(f"\nCuentas: A (rivalry), B (performance), C (inactivity)")
    print(f"Dias: 3 (lunes, martes, miercoles)")
    print(f"Mensajes por cuenta por dia: {LEADS_PER_DAY}")
    print(f"Total: {total} mensajes en 3 dias")


if __name__ == "__main__":
    main()
