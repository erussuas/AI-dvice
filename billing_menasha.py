"""
Menasha Electric & Water Utilities — Billing Engine
Amendment No. 87, effective June 1, 2025
Docket 3560-ER-108
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Rate definitions ──────────────────────────────────────────────────────────
MENASHA_RATES = {
    "Rg-1":  {"name": "Rg-1 – Residential",
               "cust": {"single": 12.00, "three": 21.00},
               "energy": {"flat": 0.1140}, "dc": None, "dd": None,
               "tou": False, "lim": None, "ctc": {"pct": 0.03, "cap": 0.97}, "pcac2": False},

    "Rg-2":  {"name": "Rg-2 – Residential TOD",
               "cust": {"single": 12.00, "three": 21.00},
               "energy": {"on": 0.1999, "off": 0.0617}, "dc": None, "dd": None,
               "tou": True, "lim": None, "ctc": {"pct": 0.03, "cap": 0.97}, "pcac2": False},

    "Gs-1":  {"name": "Gs-1 – General Service",
               "cust": {"single": 13.00, "three": 22.00},
               "energy": {"flat": 0.1164}, "dc": None, "dd": None,
               "tou": False, "lim": None, "ctc": {"pct": 0.03, "cap": 1.95}, "pcac2": False},

    "Gs-2":  {"name": "Gs-2 – General Service TOD",
               "cust": {"single": 13.00, "three": 22.00},
               "energy": {"on": 0.1967, "off": 0.0607}, "dc": None, "dd": None,
               "tou": True, "lim": None, "ctc": {"pct": 0.03, "cap": 1.95}, "pcac2": False},

    "Cp-1":  {"name": "Cp-1 – Small Power (50–200 kW)",
               "cust": {"single": 50.00, "three": 50.00},
               "energy": {"on": 0.0862, "off": 0.0544},
               "dc": {"peak": 8.50, "shoulder": 8.50, "other": 8.50},
               "dd": 2.50, "tou": True, "lim": 0.1418,
               "ctc": {"pct": 0.03, "cap": 16.35}, "pcac2": False},

    "Cp-2":  {"name": "Cp-2 – Large Power TOD (200–1,000 kW)",
               "cust": {"single": 200.00, "three": 200.00},
               "energy": {"on": 0.0620, "off": 0.0484},
               "dc": {"peak": 12.50, "shoulder": 12.50, "other": 12.50},
               "dd": 2.50, "tou": True, "lim": None,
               "ctc": {"pct": 0.03, "cap": 49.85}, "pcac2": False},

    "Cp-3":  {"name": "Cp-3 – Industrial TOD (1,000–5,000 kW)",
               "cust": {"single": 300.00, "three": 300.00},
               "energy": {"on": 0.0587, "off": 0.0400},
               "dc": {"peak": 14.00, "shoulder": 14.00, "other": 14.00},
               "dd": 2.50, "tou": True, "lim": None,
               "ctc": {"pct": 0.03, "cap": 82.50}, "pcac2": False},

    "Cp-4":  {"name": "Cp-4 – Large Industrial TOD (5,000+ kW, LF ≥85%)",
               "cust": {"single": 500.00, "three": 500.00},
               "energy": {"on": 0.0573, "off": 0.0356},
               "dc": {"peak": 21.853, "shoulder": 17.962, "other": 16.497},
               "dd": 3.00, "tou": True, "lim": None,
               "ctc": {"pct": 0.03, "cap": 225.00}, "pcac2": True},
}

BDCF = {"peak": 21.853, "shoulder": 17.962, "other": 16.497}
BECF = 0.0432


@dataclass
class MenashaInputs:
    on_peak_kwh: float
    off_peak_kwh: float
    on_peak_demand_kw: float
    dist_demand_kw: float
    phase: str            # "single" | "three"
    month_type: str       # "peak" | "shoulder" | "other"
    pcac: float           # $/kWh, PCAC rate (non-Cp4)
    primary_metering: bool
    xfmr_ownership: bool
    sales_tax_pct: float  # e.g. 0.007 for 0.7%
    # Cp-4 PCAC2 — direct rate entry
    eca_rate: float = 0.0   # $/kWh
    dca_rate: float = 0.0   # $/kW
    # Cp-4 PCAC2 — formula mode
    pcac2_mode: str = "direct"  # "direct" | "formula"
    wdc: float = 0.0
    rbd: float = 0.0
    wec: float = 0.0

    @property
    def total_kwh(self):
        return self.on_peak_kwh + self.off_peak_kwh


@dataclass
class BillLine:
    label: str
    amount: float
    is_credit: bool = False
    is_subtotal: bool = False


@dataclass
class BillResult:
    rate_key: str
    rate_name: str
    lines: list = field(default_factory=list)
    total: float = 0.0
    effective_rate: float = 0.0
    load_factor: float = 0.0
    is_cp4: bool = False


def calc_menasha_bill(rate_key: str, inp: MenashaInputs) -> BillResult:
    r = MENASHA_RATES[rate_key]
    pm = inp.primary_metering
    lines = []
    total = 0.0

    # Customer charge
    cust = r["cust"][inp.phase]
    lines.append(BillLine(f"Customer charge ({inp.phase}-phase)", cust))
    total += cust

    # Distribution demand (demand schedules only)
    dist_cost = 0.0
    if r["dd"]:
        dist_cost = inp.dist_demand_kw * r["dd"]
        if pm:
            dist_cost *= 0.98
        if inp.xfmr_ownership:
            dist_cost -= inp.dist_demand_kw * 0.25
        label = f"Distribution demand ({inp.dist_demand_kw:,.2f} kW × ${r['dd']:.2f}/kW"
        if pm:
            label += " ×0.98"
        if inp.xfmr_ownership:
            label += " − $0.25/kW xfmr"
        label += ")"
        lines.append(BillLine(label, dist_cost))
        total += dist_cost

    # Energy charges
    energy_cost = 0.0
    if r["tou"] and "on" in r["energy"]:
        e_on = inp.on_peak_kwh * r["energy"]["on"]
        e_off = inp.off_peak_kwh * r["energy"]["off"]
        if pm:
            e_on *= 0.98
            e_off *= 0.98
        energy_cost = e_on + e_off
        lines.append(BillLine(
            f"On-peak energy ({inp.on_peak_kwh:,.0f} kWh × ${r['energy']['on']:.4f}{' ×0.98' if pm else ''})",
            e_on))
        lines.append(BillLine(
            f"Off-peak energy ({inp.off_peak_kwh:,.0f} kWh × ${r['energy']['off']:.4f}{' ×0.98' if pm else ''})",
            e_off))
    else:
        energy_cost = inp.total_kwh * r["energy"]["flat"]
        if pm:
            energy_cost *= 0.98
        lines.append(BillLine(
            f"Energy ({inp.total_kwh:,.0f} kWh × ${r['energy']['flat']:.4f}{' ×0.98' if pm else ''})",
            energy_cost))

    # Demand charge
    demand_cost = 0.0
    if r["dc"]:
        dc_rate = r["dc"][inp.month_type]
        demand_cost = inp.on_peak_demand_kw * dc_rate
        if pm:
            demand_cost *= 0.98
        lines.append(BillLine(
            f"On-peak demand ({inp.on_peak_demand_kw:,.2f} kW × ${dc_rate:.3f}/kW{' ×0.98' if pm else ''})",
            demand_cost))

    # Energy limiter (Cp-1 only)
    if r["lim"]:
        limiter_total = inp.total_kwh * r["lim"]
        combo = energy_cost + demand_cost
        if limiter_total < combo:
            lines.append(BillLine(
                f"Energy limiter applied ({inp.total_kwh:,.0f} kWh × ${r['lim']:.4f}) — less than demand+energy",
                limiter_total))
            total += limiter_total
        else:
            lines.append(BillLine("Demand + energy (limiter not triggered)", combo))
            total += combo
    else:
        total += energy_cost + demand_cost

    # PCAC / PCAC2
    if r["pcac2"]:
        # Resolve ECA/DCA
        if inp.pcac2_mode == "formula" and inp.rbd > 0:
            bdcf = BDCF[inp.month_type]
            dca = (inp.wdc / inp.rbd) - bdcf
            eca = (inp.wec / inp.total_kwh) - BECF if inp.total_kwh > 0 else 0.0
        else:
            dca = inp.dca_rate
            eca = inp.eca_rate
        eca_charge = eca * inp.total_kwh
        dca_charge = dca * inp.on_peak_demand_kw
        lines.append(BillLine(
            f"PCAC2 – ECA (${eca:.4f}/kWh × {inp.total_kwh:,.0f} kWh)", eca_charge,
            is_credit=(eca_charge < 0)))
        lines.append(BillLine(
            f"PCAC2 – DCA (${dca:.4f}/kW × {inp.on_peak_demand_kw:,.2f} kW)", dca_charge,
            is_credit=(dca_charge < 0)))
        total += eca_charge + dca_charge
    else:
        pcac_charge = inp.total_kwh * inp.pcac
        lines.append(BillLine(
            f"PCAC ({inp.total_kwh:,.0f} kWh × ${inp.pcac:.4f}/kWh)", pcac_charge,
            is_credit=(pcac_charge < 0)))
        total += pcac_charge

    # CTC-1 rider
    ctc = min(total * r["ctc"]["pct"], r["ctc"]["cap"])
    lines.append(BillLine(
        f"CTC-1 rider (3.0% of bill, cap ${r['ctc']['cap']:.2f})", ctc))
    total += ctc

    # Sales tax
    tax_amount = 0.0
    if inp.sales_tax_pct > 0:
        tax_amount = total * inp.sales_tax_pct
        lines.append(BillLine(
            f"Sales/use tax ({inp.sales_tax_pct*100:.3f}%)", tax_amount))
        total += tax_amount

    # Minimum bill check
    min_bill = cust + dist_cost if r["dd"] else cust
    if total < min_bill:
        adj = min_bill - total
        lines.append(BillLine("Minimum bill adjustment", adj))
        total = min_bill

    # Load factor
    lf = 0.0
    if inp.on_peak_demand_kw > 0 and inp.total_kwh > 0:
        lf = (inp.total_kwh / (inp.on_peak_demand_kw * 730)) * 100

    eff_rate = total / inp.total_kwh if inp.total_kwh > 0 else 0.0

    return BillResult(
        rate_key=rate_key,
        rate_name=r["name"],
        lines=lines,
        total=total,
        effective_rate=eff_rate,
        load_factor=lf,
        is_cp4=r["pcac2"],
    )
