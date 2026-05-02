"""
Historical bill upload engine.
Handles CSV/Excel multi-month bill data for both Menasha and PG&E.
"""

import pandas as pd
import io
from dataclasses import dataclass, field
from typing import Optional

# ── Column definitions ────────────────────────────────────────────────────────

MENASHA_CSV_COLUMNS = {
    # Identification
    "billing_period":       "YYYY-MM (e.g. 2025-01)",
    "meter_id":             "Meter number or account ID",
    "site_name":            "Site / location name",
    "rate_schedule":        "Rg-1 | Rg-2 | Gs-1 | Gs-2 | Cp-1 | Cp-2 | Cp-3 | Cp-4",
    "billing_days":         "Number of billing days (e.g. 31)",
    "phase":                "single | three",
    "month_type":           "peak | shoulder | other",
    # Usage
    "on_peak_kwh":          "On-peak kWh consumed",
    "off_peak_kwh":         "Off-peak kWh consumed",
    "on_peak_demand_kw":    "On-peak maximum demand (kW)",
    "dist_demand_kw":       "Distribution demand — 12-month rolling peak (kW)",
    # Discounts
    "primary_metering":     "TRUE | FALSE — 2% discount on demand & energy",
    "xfmr_ownership":       "TRUE | FALSE — $0.25/kW transformer credit",
    # PCAC
    "pcac_rate":            "PCAC adjustment rate ($/kWh) — from utility monthly report",
    # PCAC2 (Cp-4 only)
    "eca_rate":             "Cp-4 only: ECA rate ($/kWh) from bill",
    "dca_rate":             "Cp-4 only: DCA rate ($/kW) from bill",
    # Tax
    "sales_tax_pct":        "Sales/use tax rate as decimal (e.g. 0.007 for 0.7%)",
    # Actuals for reconciliation
    "actual_total":         "Actual billed total ($) from invoice",
}

PGE_CSV_COLUMNS = {
    # Identification
    "billing_period":               "YYYY-MM (e.g. 2026-03)",
    "meter_id":                     "Meter serial number",
    "site_name":                    "Site name or address",
    "rate_schedule":                "B-1 | B-10 | B-19 | B-20",
    "billing_days":                 "Number of billing days",
    "season":                       "summer | winter",
    "voltage":                      "secondary | primary | transmission",
    "is_mandatory":                 "TRUE | FALSE (B-19 mandatory vs voluntary)",
    "is_cca":                       "TRUE | FALSE — CCA or Renewable100 account",
    "cca_provider":                 "CCA name (e.g. Ava Community Energy, MCE, Renewable100)",
    "city":                         "City for UUT lookup (e.g. Stockton, Hayward)",
    # PG&E Delivery — usage
    "peak_kwh":                     "Peak kWh (4–9 PM)",
    "part_peak_kwh":                "Part-peak kWh (summer only, 2–4 PM & 9–11 PM)",
    "off_peak_kwh":                 "Off-peak kWh",
    "super_off_peak_kwh":           "Super off-peak kWh (winter, 9 AM–2 PM, Mar–May)",
    # PG&E Delivery — demand
    "max_peak_demand_kw":           "Max peak demand (kW)",
    "max_part_peak_demand_kw":      "Max part-peak demand (kW, summer only)",
    "max_demand_kw":                "Max demand all-hours (kW)",
    # PG&E Delivery — rates from bill
    "peak_rate":                    "Peak energy rate ($/kWh) from bill",
    "part_peak_rate":               "Part-peak energy rate ($/kWh) from bill",
    "off_peak_rate":                "Off-peak energy rate ($/kWh) from bill",
    "super_off_peak_rate":          "Super off-peak rate ($/kWh) from bill",
    "max_peak_demand_rate":         "Max peak demand rate ($/kW) from bill",
    "max_part_peak_demand_rate":    "Max part-peak demand rate ($/kW) from bill",
    "max_demand_rate":              "Max demand rate ($/kW) from bill",
    "cust_charge_per_day":          "Customer charge ($/day) from bill",
    # Adjustments
    "generation_credit":            "Generation credit ($, enter as positive)",
    "pcia":                         "PCIA amount ($) from PG&E delivery side",
    "ffs":                          "Franchise Fee Surcharge ($) from PG&E delivery side",
    # CCA generation side
    "cca_peak_kwh":                 "CCA peak kWh (often same as peak_kwh)",
    "cca_off_peak_kwh":             "CCA off-peak kWh",
    "cca_super_off_peak_kwh":       "CCA super off-peak kWh",
    "cca_peak_rate":                "CCA peak generation rate ($/kWh)",
    "cca_off_peak_rate":            "CCA off-peak generation rate ($/kWh)",
    "cca_super_off_peak_rate":      "CCA super off-peak generation rate ($/kWh)",
    "cca_demand_kw":                "CCA demand (kW, if billed)",
    "cca_demand_rate":              "CCA demand rate ($/kW, if billed)",
    "cca_premium_kwh":              "CCA premium program kWh (e.g. Renewable100)",
    "cca_premium_rate":             "CCA premium rate ($/kWh adder)",
    "pcia_credit":                  "PCIA credit on CCA side ($, enter as positive)",
    "ffs_credit":                   "FFS credit on CCA side ($, enter as positive)",
    "cca_discount":                 "CCA discount (e.g. Bright Choice, enter as positive)",
    # Taxes
    "uut_pct_delivery":             "UUT rate on PG&E delivery side (decimal, e.g. 0.06)",
    "uut_pct_cca":                  "UUT rate on CCA generation side (decimal, e.g. 0.06)",
    "energy_commission_tax":        "Energy Commission Tax amount ($) from CCA bill",
    # Actuals
    "actual_pge_delivery_total":    "Actual PG&E delivery total ($) from invoice",
    "actual_cca_total":             "Actual CCA total ($) from invoice (0 if bundled)",
}


def generate_menasha_template() -> bytes:
    """Generate a downloadable CSV template for Menasha historical bills."""
    # Header row with column names, second row with descriptions
    cols = list(MENASHA_CSV_COLUMNS.keys())
    descriptions = list(MENASHA_CSV_COLUMNS.values())

    # Sample data row (Sonoco Jan 2026)
    sample = {
        "billing_period": "2026-01",
        "meter_id": "3017300007",
        "site_name": "69 Washington St",
        "rate_schedule": "Cp-4",
        "billing_days": "31",
        "phase": "three",
        "month_type": "other",
        "on_peak_kwh": "1983890",
        "off_peak_kwh": "3982720",
        "on_peak_demand_kw": "8732.92",
        "dist_demand_kw": "8987.90",
        "primary_metering": "TRUE",
        "xfmr_ownership": "TRUE",
        "pcac_rate": "0.0000",
        "eca_rate": "0.0003",
        "dca_rate": "-0.1170",
        "sales_tax_pct": "0.00700",
        "actual_total": "419902.71",
    }

    df = pd.DataFrame([
        {c: f"[{descriptions[i]}]" for i, c in enumerate(cols)},
        sample,
    ])
    df.columns = cols

    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def generate_pge_template() -> bytes:
    """Generate a downloadable CSV template for PG&E historical bills."""
    cols = list(PGE_CSV_COLUMNS.keys())
    descriptions = list(PGE_CSV_COLUMNS.values())

    # Sample row — Hayward B19S bill (March 2026)
    sample = {
        "billing_period": "2026-03",
        "meter_id": "1010095036",
        "site_name": "3466 Enterprise Ave Hayward",
        "rate_schedule": "B-19",
        "billing_days": "29",
        "season": "winter",
        "voltage": "secondary",
        "is_mandatory": "TRUE",
        "is_cca": "TRUE",
        "cca_provider": "Renewable100",
        "city": "Hayward",
        "peak_kwh": "9343.6",
        "part_peak_kwh": "0",
        "off_peak_kwh": "24852",
        "super_off_peak_kwh": "11534.4",
        "max_peak_demand_kw": "112",
        "max_part_peak_demand_kw": "0",
        "max_demand_kw": "171.2",
        "peak_rate": "0.16188",
        "part_peak_rate": "0",
        "off_peak_rate": "0.12026",
        "super_off_peak_rate": "0.06442",
        "max_peak_demand_rate": "2.310",
        "max_part_peak_demand_rate": "0",
        "max_demand_rate": "37.370",
        "cust_charge_per_day": "11.36882",
        "generation_credit": "3609.77",
        "pcia": "1634.39",
        "ffs": "26.07",
        "cca_peak_kwh": "9343.6",
        "cca_off_peak_kwh": "24852",
        "cca_super_off_peak_kwh": "11534.4",
        "cca_peak_rate": "0.12050",
        "cca_off_peak_rate": "0.07884",
        "cca_super_off_peak_rate": "0.02302",
        "cca_demand_kw": "112",
        "cca_demand_rate": "2.310",
        "cca_premium_kwh": "45730",
        "cca_premium_rate": "0.01750",
        "pcia_credit": "1634.39",
        "ffs_credit": "26.07",
        "cca_discount": "0",
        "uut_pct_delivery": "0.055",
        "uut_pct_cca": "0.055",
        "energy_commission_tax": "13.72",
        "actual_pge_delivery_total": "13759.73",
        "actual_cca_total": "0",
    }

    df = pd.DataFrame([
        {c: f"[{descriptions[i]}]" for i, c in enumerate(cols)},
        sample,
    ])
    df.columns = cols

    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def load_and_validate_csv(uploaded_file, utility: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Load uploaded CSV/Excel file, skip description row if present,
    return cleaned DataFrame and list of any warnings.
    """
    warnings = []
    try:
        if hasattr(uploaded_file, 'name') and uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file, dtype=str)
        else:
            df = pd.read_csv(uploaded_file, dtype=str)
    except Exception as e:
        return pd.DataFrame(), [f"Could not read file: {e}"]

    # Drop description row (first row if it contains bracket notation)
    if len(df) > 0 and any(str(v).startswith('[') for v in df.iloc[0].values):
        df = df.iloc[1:].reset_index(drop=True)

    if utility == "menasha":
        required = ["billing_period", "rate_schedule", "on_peak_kwh", "off_peak_kwh", "actual_total"]
    else:
        required = ["billing_period", "rate_schedule", "peak_kwh", "off_peak_kwh"]

    missing = [c for c in required if c not in df.columns]
    if missing:
        warnings.append(f"Missing required columns: {', '.join(missing)}")

    # Coerce numerics
    numeric_cols = [c for c in df.columns if c not in
                    ["billing_period", "meter_id", "site_name", "rate_schedule",
                     "phase", "month_type", "season", "voltage", "is_mandatory",
                     "is_cca", "cca_provider", "city", "primary_metering",
                     "xfmr_ownership"]]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    bool_cols = ["primary_metering", "xfmr_ownership", "is_mandatory", "is_cca"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().map(
                {"TRUE": True, "FALSE": False, "1": True, "0": False}).fillna(False)

    return df, warnings


def process_menasha_history(df: pd.DataFrame) -> pd.DataFrame:
    """Run billing engine across all rows, return results DataFrame."""
    from billing_menasha import calc_menasha_bill, MenashaInputs

    records = []
    for _, row in df.iterrows():
        # Determine rate period from billing_period column (YYYY-MM)
        billing_period_str = str(row.get("billing_period", ""))
        try:
            from datetime import date as _date
            yr, mo = int(billing_period_str[:4]), int(billing_period_str[5:7])
            bill_date = _date(yr, mo, 1)
        except Exception:
            bill_date = None

        inp = MenashaInputs(
            on_peak_kwh=float(row.get("on_peak_kwh", 0)),
            off_peak_kwh=float(row.get("off_peak_kwh", 0)),
            on_peak_demand_kw=float(row.get("on_peak_demand_kw", 0)),
            dist_demand_kw=float(row.get("dist_demand_kw", 0)),
            phase=str(row.get("phase", "three")),
            month_type=str(row.get("month_type", "other")),
            pcac=float(row.get("pcac_rate", 0)),
            primary_metering=bool(row.get("primary_metering", False)),
            xfmr_ownership=bool(row.get("xfmr_ownership", False)),
            sales_tax_pct=float(row.get("sales_tax_pct", 0)),
            eca_rate=float(row.get("eca_rate", 0)),
            dca_rate=float(row.get("dca_rate", 0)),
            pcac2_mode="direct",
            billing_date=bill_date,
        )
        rate_key = str(row.get("rate_schedule", "Cp-4"))
        try:
            result = calc_menasha_bill(rate_key, inp)
            computed = result.total
        except Exception as e:
            computed = 0.0

        actual = float(row.get("actual_total", 0))
        delta = computed - actual
        delta_pct = (delta / actual * 100) if actual != 0 else 0

        records.append({
            "Period": str(row.get("billing_period", "")),
            "Site": str(row.get("site_name", "")),
            "Rate": rate_key,
            "Total kWh": inp.total_kwh,
            "Computed ($)": round(computed, 2),
            "Actual ($)": actual,
            "Variance ($)": round(delta, 2),
            "Variance (%)": round(delta_pct, 2),
            "Flag": "⚠️" if abs(delta) > 50 else "✅",
        })

    return pd.DataFrame(records)


def process_pge_history(df: pd.DataFrame) -> pd.DataFrame:
    """Run PG&E audit engine across all rows."""
    from billing_pge import calc_pge_audit, PGEAuditInputs

    records = []
    for _, row in df.iterrows():
        inp = PGEAuditInputs(
            meter_id=str(row.get("meter_id", "")),
            site_name=str(row.get("site_name", "")),
            rate_schedule=str(row.get("rate_schedule", "B-19")),
            billing_days=int(row.get("billing_days", 29)),
            season=str(row.get("season", "winter")),
            voltage=str(row.get("voltage", "secondary")),
            is_mandatory=bool(row.get("is_mandatory", True)),
            is_cca=bool(row.get("is_cca", False)),
            cca_provider=str(row.get("cca_provider", "")),
            peak_kwh=float(row.get("peak_kwh", 0)),
            part_peak_kwh=float(row.get("part_peak_kwh", 0)),
            off_peak_kwh=float(row.get("off_peak_kwh", 0)),
            super_off_peak_kwh=float(row.get("super_off_peak_kwh", 0)),
            max_peak_demand_kw=float(row.get("max_peak_demand_kw", 0)),
            max_part_peak_demand_kw=float(row.get("max_part_peak_demand_kw", 0)),
            max_demand_kw=float(row.get("max_demand_kw", 0)),
            peak_rate=float(row.get("peak_rate", 0)),
            part_peak_rate=float(row.get("part_peak_rate", 0)),
            off_peak_rate=float(row.get("off_peak_rate", 0)),
            super_off_peak_rate=float(row.get("super_off_peak_rate", 0)),
            max_peak_demand_rate=float(row.get("max_peak_demand_rate", 0)),
            max_part_peak_demand_rate=float(row.get("max_part_peak_demand_rate", 0)),
            max_demand_rate=float(row.get("max_demand_rate", 0)),
            cust_charge_per_day=float(row.get("cust_charge_per_day", 0)),
            generation_credit=float(row.get("generation_credit", 0)),
            pcia=float(row.get("pcia", 0)),
            ffs=float(row.get("ffs", 0)),
            cca_peak_kwh=float(row.get("cca_peak_kwh", 0)),
            cca_off_peak_kwh=float(row.get("cca_off_peak_kwh", 0)),
            cca_super_off_peak_kwh=float(row.get("cca_super_off_peak_kwh", 0)),
            cca_peak_rate=float(row.get("cca_peak_rate", 0)),
            cca_off_peak_rate=float(row.get("cca_off_peak_rate", 0)),
            cca_super_off_peak_rate=float(row.get("cca_super_off_peak_rate", 0)),
            cca_demand_kw=float(row.get("cca_demand_kw", 0)),
            cca_demand_rate=float(row.get("cca_demand_rate", 0)),
            cca_premium_kwh=float(row.get("cca_premium_kwh", 0)),
            cca_premium_rate=float(row.get("cca_premium_rate", 0)),
            pcia_credit=float(row.get("pcia_credit", 0)),
            ffs_credit=float(row.get("ffs_credit", 0)),
            cca_discount=float(row.get("cca_discount", 0)),
            city=str(row.get("city", "Other / Unknown")),
            uut_pct_delivery=float(row.get("uut_pct_delivery", 0)),
            uut_pct_cca=float(row.get("uut_pct_cca", 0)),
            energy_commission_tax=float(row.get("energy_commission_tax", 0)),
            actual_pge_delivery_total=float(row.get("actual_pge_delivery_total", 0)),
            actual_cca_total=float(row.get("actual_cca_total", 0)),
        )
        try:
            result = calc_pge_audit(inp)
            computed = result.total_computed
        except Exception:
            computed = 0.0

        actual = inp.actual_total
        delta = computed - actual
        delta_pct = (delta / actual * 100) if actual != 0 else 0

        records.append({
            "Period": str(row.get("billing_period", "")),
            "Meter / Site": f"{inp.meter_id} — {inp.site_name}",
            "Rate": inp.rate_schedule,
            "Total kWh": inp.total_kwh,
            "Computed ($)": round(computed, 2),
            "Actual ($)": actual,
            "Variance ($)": round(delta, 2),
            "Variance (%)": round(delta_pct, 2),
            "Flag": "⚠️" if abs(delta) > 10 else "✅",
        })

    return pd.DataFrame(records)
