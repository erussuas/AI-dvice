"""
Pacific Gas & Electric Company — Billing Engine
Rates effective March 1, 2026 (Advice 7846-E)
Schedules: B-1, B-6, B-10, B-19, B-20
"""

from dataclasses import dataclass, field
from billing_menasha import BillLine, BillResult

# ── Rate definitions ──────────────────────────────────────────────────────────
# All rates are TOTAL BUNDLED rates (generation + delivery + surcharges)
# Source: PG&E tariff book, Advice 7846-E, effective March 1, 2026

PGE_RATES = {
    "B-1": {
        "name": "B-1 – Small General Service (<75 kW)",
        "eligibility": "Max demand <75 kW for 3+ consecutive months",
        "has_demand": False,
        "voltages": ["secondary"],
        "cust_per_day": {"single": 0.32854, "poly": 0.82136},
        "energy": {
            "summer": {"peak": 0.47087, "part_peak": 0.42164, "off_peak": 0.40083},
            "winter": {"peak": 0.39545, "off_peak": 0.37933, "super_off_peak": 0.36291},
        },
        "demand": None,
        "notes": "Energy-only TOU. No demand charge. Transition from A-1 mandatory March 2021.",
    },
    "B-6": {
        "name": "B-6 – Small General TOU Demand (75–499 kW)",
        "eligibility": "Max demand 75–499 kW for 3+ consecutive months",
        "has_demand": True,
        "voltages": ["secondary", "primary"],
        "cust_per_day": {"secondary": 13.00, "primary": 13.00},
        "energy": {
            "summer": {
                "secondary": {"peak": 0.18648, "part_peak": 0.14775, "off_peak": 0.12037},
                "primary":   {"peak": 0.16454, "part_peak": 0.13500, "off_peak": 0.10931},
            },
            "winter": {
                "secondary": {"peak": 0.16188, "off_peak": 0.12026, "super_off_peak": 0.06442},
                "primary":   {"peak": 0.14737, "off_peak": 0.10963, "super_off_peak": 0.05594},
            },
        },
        "demand": {
            "summer": {
                "secondary": {"max_peak": 20.00, "max_demand": 15.00},
                "primary":   {"max_peak": 16.00, "max_demand": 12.00},
            },
            "winter": {
                "secondary": {"max_peak": 2.00, "max_demand": 15.00},
                "primary":   {"max_peak": 1.50, "max_demand": 12.00},
            },
        },
        "notes": "Approximate demand charges — verify with current tariff. Transition from A-6.",
    },
    "B-10": {
        "name": "B-10 – Medium General Demand-Metered (75–499 kW)",
        "eligibility": "Max demand 75–499 kW; alternative to B-6 without full TOU differentiation",
        "has_demand": True,
        "voltages": ["secondary", "primary"],
        "cust_per_day": {"secondary": 20.00, "primary": 20.00},
        "energy": {
            "summer": {
                "secondary": {"peak": 0.17500, "part_peak": 0.14000, "off_peak": 0.11500},
                "primary":   {"peak": 0.15500, "part_peak": 0.12500, "off_peak": 0.10000},
            },
            "winter": {
                "secondary": {"peak": 0.15500, "off_peak": 0.11500, "super_off_peak": 0.06000},
                "primary":   {"peak": 0.13500, "off_peak": 0.10000, "super_off_peak": 0.05000},
            },
        },
        "demand": {
            "summer": {
                "secondary": {"max_peak": 25.00, "max_demand": 18.00},
                "primary":   {"max_peak": 20.00, "max_demand": 14.00},
            },
            "winter": {
                "secondary": {"max_peak": 2.00, "max_demand": 18.00},
                "primary":   {"max_peak": 2.00, "max_demand": 14.00},
            },
        },
        "notes": "Approximate rates — verify with current tariff. Transition from A-10.",
    },
    "B-19": {
        "name": "B-19 – Medium General Demand TOU (500–999 kW)",
        "eligibility": "Max demand 500–999 kW for 3+ consecutive months. Mandatory above 499 kW. Voluntary below 500 kW.",
        "has_demand": True,
        "voltages": ["secondary", "primary", "transmission"],
        "cust_per_day": {
            "mandatory": {"secondary": 58.62824, "primary": 87.34546, "transmission": 117.10726},
            "voluntary": {"secondary": 11.36882, "primary": 11.36882, "transmission": 11.36882},
        },
        "energy": {
            "summer": {
                "secondary":    {"peak": 0.18648, "part_peak": 0.14775, "off_peak": 0.12037},
                "primary":      {"peak": 0.16454, "part_peak": 0.13500, "off_peak": 0.10931},
                "transmission": {"peak": 0.14803, "part_peak": 0.13556, "off_peak": 0.10902},
            },
            "winter": {
                "secondary":    {"peak": 0.16188, "off_peak": 0.12026, "super_off_peak": 0.06442},
                "primary":      {"peak": 0.14737, "off_peak": 0.10963, "super_off_peak": 0.05594},
                "transmission": {"peak": 0.14719, "off_peak": 0.10961, "super_off_peak": 0.05433},
            },
        },
        "demand": {
            "summer": {
                "secondary":    {"max_peak": 46.16, "max_part_peak": 10.52, "max_demand": 37.37},
                "primary":      {"max_peak": 37.89, "max_part_peak": 8.54,  "max_demand": 29.11},
                "transmission": {"max_peak": 14.67, "max_part_peak": 3.67,  "max_demand": 16.94},
            },
            "winter": {
                "secondary":    {"max_peak": 2.31, "max_demand": 37.37},
                "primary":      {"max_peak": 1.69, "max_demand": 29.11},
                "transmission": {"max_peak": 1.41, "max_demand": 16.94},
            },
        },
        "notes": "Effective March 1, 2026 (Advice 7846-E). Replaced legacy E-19. Power factor adjustment at $0.00005/kWh/%. PDP available.",
    },
    "B-20": {
        "name": "B-20 – Large General Service (≥1,000 kW)",
        "eligibility": "Max demand >999 kW for 3+ consecutive months. Must maintain >999 kW for 5 of prev 12 months or 3 consecutive of prev 14 months.",
        "has_demand": True,
        "voltages": ["secondary", "primary", "transmission"],
        "cust_per_day": {
            "secondary":    107.36636,
            "primary":      110.32836,
            "transmission": 331.86645,
        },
        "energy": {
            "summer": {
                "secondary":    {"peak": 0.17702, "part_peak": 0.14227, "off_peak": 0.11482},
                "primary":      {"peak": 0.17322, "part_peak": 0.13597, "off_peak": 0.10998},
                "transmission": {"peak": 0.15702, "part_peak": 0.13245, "off_peak": 0.10504},
            },
            "winter": {
                "secondary":    {"peak": 0.15632, "off_peak": 0.11460, "super_off_peak": 0.05872},
                "primary":      {"peak": 0.14951, "off_peak": 0.11005, "super_off_peak": 0.05406},
                "transmission": {"peak": 0.15043, "off_peak": 0.10085, "super_off_peak": 0.05134},
            },
        },
        "demand": {
            "summer": {
                "secondary":    {"max_peak": 41.35, "max_part_peak": 9.27, "max_demand": 39.08},
                "primary":      {"max_peak": 43.88, "max_part_peak": 9.45, "max_demand": 34.28},
                "transmission": {"max_peak": 22.28, "max_part_peak": 5.31, "max_demand": 17.19},
            },
            "winter": {
                "secondary":    {"max_peak": 2.32, "max_demand": 39.08},
                "primary":      {"max_peak": 2.34, "max_demand": 34.28},
                "transmission": {"max_peak": 2.97, "max_demand": 17.19},
            },
        },
        "notes": "Effective March 1, 2026 (Advice 7846-E). Replaced legacy E-20. 15-minute interval metering required. Power factor adjustment at $0.00005/kWh/%. PDP available.",
    },
}

BILLING_DAYS_PER_MONTH = 30  # average used for customer charge conversion


@dataclass
class PGEInputs:
    # Energy
    peak_kwh: float
    part_peak_kwh: float
    off_peak_kwh: float
    super_off_peak_kwh: float
    # Demand
    max_peak_demand_kw: float
    max_part_peak_demand_kw: float
    max_demand_kw: float
    # Config
    season: str           # "summer" | "winter"
    voltage: str          # "secondary" | "primary" | "transmission"
    phase: str            # "single" | "poly" (B-1 only)
    is_mandatory: bool    # B-19 only: mandatory vs voluntary
    billing_days: int     # typically 30
    power_factor_pct: float  # e.g. 85.0

    @property
    def total_kwh(self):
        return self.peak_kwh + self.part_peak_kwh + self.off_peak_kwh + self.super_off_peak_kwh


def calc_pge_bill(rate_key: str, inp: PGEInputs) -> BillResult:
    r = PGE_RATES[rate_key]
    lines = []
    total = 0.0
    season = inp.season
    voltage = inp.voltage

    # ── Customer charge ──────────────────────────────────────────────────────
    if rate_key == "B-1":
        key = "single" if inp.phase == "single" else "poly"
        daily_rate = r["cust_per_day"][key]
    elif rate_key == "B-19":
        cust_dict = r["cust_per_day"]["mandatory" if inp.is_mandatory else "voluntary"]
        daily_rate = cust_dict.get(voltage, cust_dict.get("secondary", 0))
    elif rate_key == "B-20":
        daily_rate = r["cust_per_day"].get(voltage, r["cust_per_day"]["secondary"])
    else:
        daily_rate = r["cust_per_day"].get(voltage, r["cust_per_day"].get("secondary", 0))

    cust_charge = daily_rate * inp.billing_days
    lines.append(BillLine(
        f"Customer charge (${daily_rate:.5f}/day × {inp.billing_days} days)", cust_charge))
    total += cust_charge

    # ── Energy charges ───────────────────────────────────────────────────────
    energy_rates = r["energy"][season]
    # For B-1: no voltage split
    if rate_key == "B-1":
        er = energy_rates
    else:
        er = energy_rates.get(voltage, energy_rates.get("secondary", {}))

    e_peak = inp.peak_kwh * er.get("peak", 0)
    e_pp   = inp.part_peak_kwh * er.get("part_peak", 0)
    e_off  = inp.off_peak_kwh * er.get("off_peak", 0)
    e_sop  = inp.super_off_peak_kwh * er.get("super_off_peak", 0)

    lines.append(BillLine(
        f"Peak energy ({inp.peak_kwh:,.0f} kWh × ${er.get('peak',0):.5f})", e_peak))
    if inp.part_peak_kwh > 0 and season == "summer":
        lines.append(BillLine(
            f"Part-peak energy ({inp.part_peak_kwh:,.0f} kWh × ${er.get('part_peak',0):.5f})", e_pp))
    lines.append(BillLine(
        f"Off-peak energy ({inp.off_peak_kwh:,.0f} kWh × ${er.get('off_peak',0):.5f})", e_off))
    if inp.super_off_peak_kwh > 0 and season == "winter":
        lines.append(BillLine(
            f"Super off-peak energy ({inp.super_off_peak_kwh:,.0f} kWh × ${er.get('super_off_peak',0):.5f})", e_sop))

    energy_total = e_peak + e_pp + e_off + e_sop
    total += energy_total

    # ── Demand charges ───────────────────────────────────────────────────────
    if r["has_demand"] and r["demand"]:
        dr = r["demand"][season]
        if isinstance(dr, dict) and voltage in dr:
            drates = dr[voltage]
        elif isinstance(dr, dict) and "secondary" in dr:
            drates = dr.get(voltage, dr["secondary"])
        else:
            drates = dr

        d_peak = inp.max_peak_demand_kw * drates.get("max_peak", 0)
        d_pp   = inp.max_part_peak_demand_kw * drates.get("max_part_peak", 0) if season == "summer" else 0
        d_max  = inp.max_demand_kw * drates.get("max_demand", 0)

        lines.append(BillLine(
            f"Max peak demand ({inp.max_peak_demand_kw:,.1f} kW × ${drates.get('max_peak',0):.2f}/kW)",
            d_peak))
        if season == "summer" and drates.get("max_part_peak", 0) > 0:
            lines.append(BillLine(
                f"Max part-peak demand ({inp.max_part_peak_demand_kw:,.1f} kW × ${drates.get('max_part_peak',0):.2f}/kW)",
                d_pp))
        lines.append(BillLine(
            f"Max demand ({inp.max_demand_kw:,.1f} kW × ${drates.get('max_demand',0):.2f}/kW)",
            d_max))

        demand_total = d_peak + d_pp + d_max
        total += demand_total

    # ── Power factor adjustment ──────────────────────────────────────────────
    pf_adj = 0.0
    if inp.power_factor_pct != 85.0 and inp.total_kwh > 0:
        pf_diff = abs(inp.power_factor_pct - 85.0)
        pf_adj = 0.00005 * pf_diff * inp.total_kwh
        if inp.power_factor_pct < 85.0:
            pf_adj = pf_adj  # surcharge
        else:
            pf_adj = -pf_adj  # credit
        lines.append(BillLine(
            f"Power factor adjustment (PF={inp.power_factor_pct:.0f}% vs 85% base, "
            f"{inp.total_kwh:,.0f} kWh × $0.00005 × {pf_diff:.0f}%)",
            pf_adj, is_credit=(pf_adj < 0)))
        total += pf_adj

    eff_rate = total / inp.total_kwh if inp.total_kwh > 0 else 0.0

    return BillResult(
        rate_key=rate_key,
        rate_name=r["name"],
        lines=lines,
        total=total,
        effective_rate=eff_rate,
        load_factor=0.0,
        is_cp4=False,
    )
