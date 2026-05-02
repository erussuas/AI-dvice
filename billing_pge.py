"""
Pacific Gas & Electric — Billing Engine v2
Supports both bundled and CCA accounts.
Rates effective March 1, 2026 (Advice 7846-E).
Line-item audit mode: re-engineers bills from raw inputs.
"""

from dataclasses import dataclass, field
from billing_menasha import BillLine, BillResult

# ── Rate tables (March 1 2026, Advice 7846-E) ─────────────────────────────────
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
        "notes": "Energy-only TOU. No demand charge.",
    },
    "B-10": {
        "name": "B-10 / B-10S – Medium General Demand (75–499 kW)",
        "eligibility": "Max demand 75–499 kW; standard business medium use",
        "has_demand": True,
        "voltages": ["secondary", "primary"],
        "cust_per_day": {"secondary": 11.36882, "primary": 11.36882},
        "energy": {
            "summer": {
                "secondary": {"peak": 0.26321, "part_peak": 0.21000, "off_peak": 0.22773},
                "primary":   {"peak": 0.23000, "part_peak": 0.18500, "off_peak": 0.20000},
            },
            "winter": {
                "secondary": {"peak": 0.26321, "off_peak": 0.22773, "super_off_peak": 0.19139},
                "primary":   {"peak": 0.23000, "off_peak": 0.20000, "super_off_peak": 0.17000},
            },
        },
        "demand": {
            "summer": {
                "secondary": {"max_peak": 20.50, "max_demand": 20.50},
                "primary":   {"max_peak": 17.00, "max_demand": 17.00},
            },
            "winter": {
                "secondary": {"max_peak": 2.31, "max_demand": 20.50},
                "primary":   {"max_peak": 1.69, "max_demand": 17.00},
            },
        },
        "notes": "Confirmed from Stockton B10S bill (March 2026). Demand $20.50/kW.",
    },
    "B-19": {
        "name": "B-19 / B-19S – Medium General TOU (500–999 kW)",
        "eligibility": "Max demand 500–999 kW for 3+ consecutive months. Mandatory above 499 kW.",
        "has_demand": True,
        "voltages": ["secondary", "primary", "transmission"],
        "cust_per_day": {
            "mandatory": {"secondary": 58.62824, "primary": 87.34546, "transmission": 117.10726},
            "voluntary":  {"secondary": 11.36882, "primary": 11.36882, "transmission": 11.36882},
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
        "notes": "Effective March 1, 2026 (Advice 7846-E). Replaced E-19.",
    },
    "B-20": {
        "name": "B-20 / B-20S – Large General Service (≥1,000 kW)",
        "eligibility": "Max demand >999 kW for 3+ consecutive months.",
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
        "notes": "Effective March 1, 2026 (Advice 7846-E). Replaced E-20.",
    },
}

# California city UUT rates (electricity) — PG&E territory
CITY_UUT_RATES = {
    "Stockton":           0.060,
    "Hayward":            0.055,
    "Fresno":             0.072,
    "Oakland":            0.075,
    "San Francisco":      0.075,
    "San Jose":           0.000,
    "Sacramento":         0.000,
    "Modesto":            0.000,
    "Bakersfield":        0.000,
    "Concord":            0.000,
    "Berkeley":           0.075,
    "Richmond":           0.075,
    "Fremont":            0.000,
    "Santa Rosa":         0.000,
    "Sunnyvale":          0.000,
    "Livermore":          0.000,
    "San Leandro":        0.000,
    "Tracy":              0.000,
    "Other / Unknown":    0.000,
}

ENERGY_COMMISSION_TAX_RATE = 0.00030  # $/kWh


@dataclass
class PGEAuditInputs:
    """All inputs for single-bill re-engineering. Enter values FROM THE BILL."""
    meter_id: str = ""
    site_name: str = ""
    rate_schedule: str = "B-19"
    billing_days: int = 29
    season: str = "winter"
    voltage: str = "secondary"
    is_mandatory: bool = True
    is_cca: bool = False
    cca_provider: str = ""
    # Usage
    peak_kwh: float = 0.0
    part_peak_kwh: float = 0.0
    off_peak_kwh: float = 0.0
    super_off_peak_kwh: float = 0.0
    # Demand
    max_peak_demand_kw: float = 0.0
    max_part_peak_demand_kw: float = 0.0
    max_demand_kw: float = 0.0
    # Rates from bill
    peak_rate: float = 0.0
    part_peak_rate: float = 0.0
    off_peak_rate: float = 0.0
    super_off_peak_rate: float = 0.0
    max_peak_demand_rate: float = 0.0
    max_part_peak_demand_rate: float = 0.0
    max_demand_rate: float = 0.0
    cust_charge_per_day: float = 0.0
    # Adjustments from bill
    generation_credit: float = 0.0
    pcia: float = 0.0
    ffs: float = 0.0
    # CCA generation side
    cca_peak_kwh: float = 0.0
    cca_off_peak_kwh: float = 0.0
    cca_super_off_peak_kwh: float = 0.0
    cca_peak_rate: float = 0.0
    cca_off_peak_rate: float = 0.0
    cca_super_off_peak_rate: float = 0.0
    cca_demand_kw: float = 0.0
    cca_demand_rate: float = 0.0
    cca_premium_kwh: float = 0.0
    cca_premium_rate: float = 0.0
    pcia_credit: float = 0.0
    ffs_credit: float = 0.0
    cca_discount: float = 0.0
    # Taxes
    city: str = "Other / Unknown"
    uut_pct_delivery: float = 0.0
    uut_pct_cca: float = 0.0
    energy_commission_tax: float = 0.0
    # Actuals for reconciliation
    actual_pge_delivery_total: float = 0.0
    actual_cca_total: float = 0.0

    @property
    def total_kwh(self):
        return self.peak_kwh + self.part_peak_kwh + self.off_peak_kwh + self.super_off_peak_kwh

    @property
    def actual_total(self):
        return self.actual_pge_delivery_total + self.actual_cca_total


@dataclass
class AuditLineItem:
    label: str
    computed: float
    actual: float
    delta: float = 0.0
    note: str = ""
    def __post_init__(self):
        self.delta = round(self.computed - self.actual, 4)


@dataclass
class PGEAuditResult:
    pge_lines: list = field(default_factory=list)
    cca_lines: list = field(default_factory=list)
    pge_computed: float = 0.0
    cca_computed: float = 0.0
    pge_actual: float = 0.0
    cca_actual: float = 0.0
    total_computed: float = 0.0
    total_actual: float = 0.0
    total_delta: float = 0.0
    effective_rate_computed: float = 0.0
    effective_rate_actual: float = 0.0


def calc_pge_audit(inp: PGEAuditInputs) -> PGEAuditResult:
    """Re-engineers a PG&E bill line by line from bill inputs."""
    result = PGEAuditResult()
    pge_lines = []
    cca_lines = []
    pge_total = 0.0
    cca_total = 0.0

    def add(lines, label, amount):
        lines.append(AuditLineItem(label, amount, amount))
        return amount

    # ── PG&E Delivery ─────────────────────────────────────────────────────────
    pge_total += add(pge_lines, f"Customer charge ({inp.billing_days} days × ${inp.cust_charge_per_day:.5f}/day)",
                     inp.cust_charge_per_day * inp.billing_days)

    if inp.max_peak_demand_kw > 0 and inp.max_peak_demand_rate > 0:
        pge_total += add(pge_lines, f"Max peak demand ({inp.max_peak_demand_kw:,.3f} kW × ${inp.max_peak_demand_rate:.3f}/kW)",
                         inp.max_peak_demand_kw * inp.max_peak_demand_rate)

    if inp.max_part_peak_demand_kw > 0 and inp.max_part_peak_demand_rate > 0:
        pge_total += add(pge_lines, f"Max part-peak demand ({inp.max_part_peak_demand_kw:,.3f} kW × ${inp.max_part_peak_demand_rate:.3f}/kW)",
                         inp.max_part_peak_demand_kw * inp.max_part_peak_demand_rate)

    if inp.max_demand_kw > 0 and inp.max_demand_rate > 0:
        pge_total += add(pge_lines, f"Max demand ({inp.max_demand_kw:,.3f} kW × ${inp.max_demand_rate:.3f}/kW)",
                         inp.max_demand_kw * inp.max_demand_rate)

    if inp.peak_kwh > 0:
        pge_total += add(pge_lines, f"Peak energy ({inp.peak_kwh:,.3f} kWh × ${inp.peak_rate:.5f})",
                         inp.peak_kwh * inp.peak_rate)

    if inp.part_peak_kwh > 0:
        pge_total += add(pge_lines, f"Part-peak energy ({inp.part_peak_kwh:,.3f} kWh × ${inp.part_peak_rate:.5f})",
                         inp.part_peak_kwh * inp.part_peak_rate)

    if inp.off_peak_kwh > 0:
        pge_total += add(pge_lines, f"Off-peak energy ({inp.off_peak_kwh:,.3f} kWh × ${inp.off_peak_rate:.5f})",
                         inp.off_peak_kwh * inp.off_peak_rate)

    if inp.super_off_peak_kwh > 0:
        pge_total += add(pge_lines, f"Super off-peak ({inp.super_off_peak_kwh:,.3f} kWh × ${inp.super_off_peak_rate:.5f})",
                         inp.super_off_peak_kwh * inp.super_off_peak_rate)

    if inp.generation_credit != 0:
        gc = -abs(inp.generation_credit)
        pge_lines.append(AuditLineItem("Generation credit", gc, gc))
        pge_total += gc

    if inp.pcia != 0:
        pge_total += add(pge_lines, "Power Charge Indifference Adjustment (PCIA)", inp.pcia)

    if inp.ffs != 0:
        pge_total += add(pge_lines, "Franchise Fee Surcharge", inp.ffs)

    # UUT on delivery — applied to pre-tax subtotal
    if inp.uut_pct_delivery > 0:
        uut_d = pge_total * inp.uut_pct_delivery
        pge_total += add(pge_lines, f"{inp.city} Utility Users' Tax ({inp.uut_pct_delivery*100:.2f}%)", uut_d)

    result.pge_lines = pge_lines
    result.pge_computed = round(pge_total, 2)
    result.pge_actual = inp.actual_pge_delivery_total

    # ── CCA Generation ────────────────────────────────────────────────────────
    if inp.is_cca:
        if inp.cca_demand_kw > 0 and inp.cca_demand_rate > 0:
            cca_total += add(cca_lines, f"CCA demand ({inp.cca_demand_kw:,.3f} kW × ${inp.cca_demand_rate:.3f}/kW)",
                             inp.cca_demand_kw * inp.cca_demand_rate)

        if inp.cca_peak_kwh > 0:
            cca_total += add(cca_lines, f"CCA peak energy ({inp.cca_peak_kwh:,.3f} kWh × ${inp.cca_peak_rate:.5f})",
                             inp.cca_peak_kwh * inp.cca_peak_rate)

        if inp.cca_off_peak_kwh > 0:
            cca_total += add(cca_lines, f"CCA off-peak energy ({inp.cca_off_peak_kwh:,.3f} kWh × ${inp.cca_off_peak_rate:.5f})",
                             inp.cca_off_peak_kwh * inp.cca_off_peak_rate)

        if inp.cca_super_off_peak_kwh > 0:
            cca_total += add(cca_lines, f"CCA super off-peak ({inp.cca_super_off_peak_kwh:,.3f} kWh × ${inp.cca_super_off_peak_rate:.5f})",
                             inp.cca_super_off_peak_kwh * inp.cca_super_off_peak_rate)

        if inp.cca_premium_kwh > 0 and inp.cca_premium_rate > 0:
            cca_total += add(cca_lines, f"{inp.cca_provider} premium ({inp.cca_premium_kwh:,.0f} kWh × ${inp.cca_premium_rate:.5f})",
                             inp.cca_premium_kwh * inp.cca_premium_rate)

        if inp.pcia_credit > 0:
            cr = -abs(inp.pcia_credit)
            cca_lines.append(AuditLineItem("PCIA Credit", cr, cr))
            cca_total += cr

        if inp.ffs_credit > 0:
            cr = -abs(inp.ffs_credit)
            cca_lines.append(AuditLineItem("Franchise Fee Surcharge Credit", cr, cr))
            cca_total += cr

        if inp.cca_discount > 0:
            cr = -abs(inp.cca_discount)
            cca_lines.append(AuditLineItem(f"{inp.cca_provider} discount/credit", cr, cr))
            cca_total += cr

        if inp.uut_pct_cca > 0:
            uut_c = cca_total * inp.uut_pct_cca
            cca_total += add(cca_lines, f"Local Utility Users' Tax ({inp.uut_pct_cca*100:.2f}%)", uut_c)

        if inp.energy_commission_tax > 0:
            cca_total += add(cca_lines, "Energy Commission Tax", inp.energy_commission_tax)

    result.cca_lines = cca_lines
    result.cca_computed = round(cca_total, 2)
    result.cca_actual = inp.actual_cca_total
    result.total_computed = round(result.pge_computed + result.cca_computed, 2)
    result.total_actual = inp.actual_total
    result.total_delta = round(result.total_computed - result.total_actual, 2)
    kwh = inp.total_kwh or 1
    result.effective_rate_computed = result.total_computed / kwh
    result.effective_rate_actual = result.total_actual / kwh if result.total_actual > 0 else 0.0
    return result


# ── Simple comparison calculator (original Mode 1) ───────────────────────────
@dataclass
class PGEInputs:
    peak_kwh: float
    part_peak_kwh: float
    off_peak_kwh: float
    super_off_peak_kwh: float
    max_peak_demand_kw: float
    max_part_peak_demand_kw: float
    max_demand_kw: float
    season: str
    voltage: str
    phase: str
    is_mandatory: bool
    billing_days: int
    power_factor_pct: float

    @property
    def total_kwh(self):
        return self.peak_kwh + self.part_peak_kwh + self.off_peak_kwh + self.super_off_peak_kwh


def calc_pge_bill(rate_key: str, inp: PGEInputs) -> BillResult:
    r = PGE_RATES[rate_key]
    lines = []
    total = 0.0
    season = inp.season
    voltage = inp.voltage

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
    lines.append(BillLine(f"Customer charge (${daily_rate:.5f}/day × {inp.billing_days} days)", cust_charge))
    total += cust_charge

    energy_rates = r["energy"][season]
    er = energy_rates if rate_key == "B-1" else energy_rates.get(voltage, energy_rates.get("secondary", {}))

    e_peak = inp.peak_kwh * er.get("peak", 0)
    e_pp   = inp.part_peak_kwh * er.get("part_peak", 0)
    e_off  = inp.off_peak_kwh * er.get("off_peak", 0)
    e_sop  = inp.super_off_peak_kwh * er.get("super_off_peak", 0)

    lines.append(BillLine(f"Peak energy ({inp.peak_kwh:,.0f} kWh × ${er.get('peak',0):.5f})", e_peak))
    if inp.part_peak_kwh > 0 and season == "summer":
        lines.append(BillLine(f"Part-peak energy ({inp.part_peak_kwh:,.0f} kWh × ${er.get('part_peak',0):.5f})", e_pp))
    lines.append(BillLine(f"Off-peak energy ({inp.off_peak_kwh:,.0f} kWh × ${er.get('off_peak',0):.5f})", e_off))
    if inp.super_off_peak_kwh > 0 and season == "winter":
        lines.append(BillLine(f"Super off-peak ({inp.super_off_peak_kwh:,.0f} kWh × ${er.get('super_off_peak',0):.5f})", e_sop))

    total += e_peak + e_pp + e_off + e_sop

    if r["has_demand"] and r["demand"]:
        dr = r["demand"][season]
        drates = dr.get(voltage, dr.get("secondary", {}))
        d_peak = inp.max_peak_demand_kw * drates.get("max_peak", 0)
        d_pp   = inp.max_part_peak_demand_kw * drates.get("max_part_peak", 0) if season == "summer" else 0
        d_max  = inp.max_demand_kw * drates.get("max_demand", 0)
        lines.append(BillLine(f"Max peak demand ({inp.max_peak_demand_kw:,.1f} kW × ${drates.get('max_peak',0):.2f}/kW)", d_peak))
        if season == "summer" and drates.get("max_part_peak", 0) > 0:
            lines.append(BillLine(f"Max part-peak demand ({inp.max_part_peak_demand_kw:,.1f} kW × ${drates.get('max_part_peak',0):.2f}/kW)", d_pp))
        lines.append(BillLine(f"Max demand ({inp.max_demand_kw:,.1f} kW × ${drates.get('max_demand',0):.2f}/kW)", d_max))
        total += d_peak + d_pp + d_max

    if inp.power_factor_pct != 85.0 and inp.total_kwh > 0:
        pf_diff = abs(inp.power_factor_pct - 85.0)
        pf_adj = 0.00005 * pf_diff * inp.total_kwh
        if inp.power_factor_pct > 85.0:
            pf_adj = -pf_adj
        lines.append(BillLine(f"Power factor adjustment (PF={inp.power_factor_pct:.0f}%)", pf_adj, is_credit=(pf_adj < 0)))
        total += pf_adj

    eff_rate = total / inp.total_kwh if inp.total_kwh > 0 else 0.0
    return BillResult(rate_key=rate_key, rate_name=r["name"], lines=lines, total=total,
                      effective_rate=eff_rate, load_factor=0.0, is_cp4=False)
