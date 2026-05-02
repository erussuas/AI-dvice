"""
Pacific Gas & Electric — UI
Mode 1a: Rate comparison calculator (original)
Mode 1b: Single bill re-engineering / audit
Mode 2:  Historical bill series upload & audit
"""
import streamlit as st
import pandas as pd
from billing_pge import (calc_pge_bill, calc_pge_audit,
                          PGEInputs, PGEAuditInputs,
                          PGE_RATES, CITY_UUT_RATES)
from bill_history import (generate_pge_template, load_and_validate_csv,
                           process_pge_history)
from ui_shared import (render_bill_card, render_comparison_summary,
                        render_audit_table, fmt)


def render_pge():
    st.markdown("## ⚡ Pacific Gas & Electric Company (PG&E)")
    st.caption("Rates effective March 1, 2026 · Advice 7846-E · CPUC Authorized")

    mode = st.radio(
        "Mode",
        ["📊 Rate Comparison Calculator",
         "🔍 Single Bill Re-engineering / Audit",
         "📂 Historical Bill Series — Upload & Audit"],
        horizontal=True)
    st.divider()

    if mode.startswith("📊"):
        _render_comparison()
    elif mode.startswith("🔍"):
        _render_single_audit()
    else:
        _render_history()


# ── MODE 1a: Rate comparison ──────────────────────────────────────────────────
def _render_comparison():
    st.markdown("### Rate Comparison Calculator")

    with st.expander("ℹ️ Rate Eligibility", expanded=False):
        st.markdown("""
| Schedule | Demand | Notes |
|---|---|---|
| **B-1** | <75 kW | Energy-only TOU, no demand charge |
| **B-10 / B-10S** | 75–499 kW | Standard business medium use |
| **B-19 / B-19S** | 500–999 kW | Mandatory above 499 kW |
| **B-20 / B-20S** | ≥1,000 kW | Mandatory above 999 kW |

**Peak:** 4–9 PM daily · **Summer:** Jun–Sep · **Winter:** Oct–May · **Super off-peak:** 9 AM–2 PM Mar–May
        """)

    with st.expander("📥 Usage Inputs", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            season   = st.selectbox("Season", ["winter","summer"],
                                    format_func=lambda x: "Winter (Oct–May)" if x=="winter" else "Summer (Jun–Sep)")
            voltage  = st.selectbox("Service voltage", ["secondary","primary","transmission"],
                                    format_func=lambda x: {"secondary":"Secondary (standard)","primary":"Primary (customer transformer)","transmission":"Transmission (>5 MW)"}[x])
            billing_days = st.number_input("Billing days", 28, 33, 29)
            phase    = st.selectbox("Phase (B-1 only)", ["poly","single"],
                                    format_func=lambda x: "Poly-phase" if x=="poly" else "Single-phase")
        with c2:
            peak_kwh       = st.number_input("Peak kWh (4–9 PM)", min_value=0.0, value=150_000.0, step=1000.0, format="%.0f")
            part_peak_kwh  = st.number_input("Part-peak kWh (summer 2–4 PM & 9–11 PM)", min_value=0.0,
                                             value=80_000.0 if season=="summer" else 0.0, step=1000.0, format="%.0f",
                                             disabled=(season=="winter"))
            off_peak_kwh   = st.number_input("Off-peak kWh", min_value=0.0, value=200_000.0, step=1000.0, format="%.0f")
            sop_kwh        = st.number_input("Super off-peak kWh (winter 9 AM–2 PM, Mar–May)", min_value=0.0,
                                             value=0.0, step=1000.0, format="%.0f",
                                             disabled=(season=="summer"))
            total_kwh = peak_kwh + (part_peak_kwh if season=="summer" else 0) + off_peak_kwh + (sop_kwh if season=="winter" else 0)
            st.metric("Total kWh", f"{total_kwh:,.0f}")
        with c3:
            max_peak_d     = st.number_input("Max peak demand (kW)", min_value=0.0, value=600.0, step=10.0, format="%.1f")
            max_pp_d       = st.number_input("Max part-peak demand (kW, summer)", min_value=0.0,
                                             value=550.0 if season=="summer" else 0.0, step=10.0, format="%.1f",
                                             disabled=(season=="winter"))
            max_demand     = st.number_input("Max demand all-hours (kW)", min_value=0.0, value=700.0, step=10.0, format="%.1f")
            pf             = st.number_input("Power factor (%)", 70.0, 100.0, 85.0, 0.5)
            is_mandatory   = st.checkbox("B-19 mandatory (demand >499 kW for 3+ months)", value=True)

    with st.expander("📊 Rate Schedules to Compare", expanded=True):
        all_keys   = list(PGE_RATES.keys())
        rate_names = {k: v["name"] for k, v in PGE_RATES.items()}
        ca, cb = st.columns(2)
        rate_a = ca.selectbox("Rate A", all_keys, format_func=lambda k: rate_names[k], index=all_keys.index("B-19"))
        rate_b = cb.selectbox("Rate B", all_keys, format_func=lambda k: rate_names[k], index=all_keys.index("B-20"))

    inp = PGEInputs(
        peak_kwh=peak_kwh,
        part_peak_kwh=part_peak_kwh if season=="summer" else 0.0,
        off_peak_kwh=off_peak_kwh,
        super_off_peak_kwh=sop_kwh if season=="winter" else 0.0,
        max_peak_demand_kw=max_peak_d,
        max_part_peak_demand_kw=max_pp_d if season=="summer" else 0.0,
        max_demand_kw=max_demand,
        season=season, voltage=voltage, phase=phase,
        is_mandatory=is_mandatory, billing_days=billing_days,
        power_factor_pct=pf,
    )

    bill_a = calc_pge_bill(rate_a, inp)
    bill_b = calc_pge_bill(rate_b, inp)
    winner_a = bill_a.total <= bill_b.total

    st.divider()
    render_comparison_summary(bill_a, bill_b)
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        render_bill_card(bill_a, is_winner=winner_a)
    with col_b:
        render_bill_card(bill_b, is_winner=not winner_a)

    st.divider()
    for rk in [rate_a, rate_b]:
        st.caption(f"**{rk}:** {PGE_RATES[rk]['eligibility']}  |  {PGE_RATES[rk].get('notes','')}")
    st.caption("Does not include PCIA, FFS, UUT, or CCA generation. Use Audit mode for full bill re-engineering.")


# ── MODE 1b: Single bill audit ────────────────────────────────────────────────
def _render_single_audit():
    st.markdown("### Single Bill Re-engineering — Audit Mode")
    st.info("Enter all line items **exactly as shown on the bill**. The tool re-engineers each line and reconciles against the actual billed total.")

    # Pre-populate from which sample bill?
    sample = st.selectbox("Pre-load sample bill",
                          ["— blank —",
                           "Stockton B10S — Suite K (Mar 2026)",
                           "Stockton B1 — Suite E (Mar 2026)",
                           "Hayward B19S — Renewable100 (Mar 2026)"])

    defaults = _get_sample_defaults(sample)

    with st.expander("📋 Bill Metadata", expanded=True):
        c1, c2, c3 = st.columns(3)
        meter_id       = c1.text_input("Meter ID",       value=defaults.get("meter_id",""))
        site_name      = c1.text_input("Site name",      value=defaults.get("site_name",""))
        rate_schedule  = c2.selectbox("Rate schedule",   list(PGE_RATES.keys()),
                                      index=list(PGE_RATES.keys()).index(defaults.get("rate_schedule","B-10")))
        billing_days   = c2.number_input("Billing days", 28, 33, defaults.get("billing_days", 29))
        season         = c2.selectbox("Season", ["winter","summer"],
                                      index=0 if defaults.get("season","winter")=="winter" else 1)
        voltage        = c3.selectbox("Voltage", ["secondary","primary","transmission"])
        is_mandatory   = c3.checkbox("B-19/B-20 mandatory", value=defaults.get("is_mandatory", True))
        is_cca         = c3.checkbox("CCA / Community Choice account", value=defaults.get("is_cca", False))
        cca_provider   = c3.text_input("CCA provider name", value=defaults.get("cca_provider",""))

    with st.expander("🔋 PG&E Delivery — Usage & Rates", expanded=True):
        st.markdown("**Energy**")
        e1, e2, e3, e4 = st.columns(4)
        peak_kwh  = e1.number_input("Peak kWh",          value=defaults.get("peak_kwh", 0.0), format="%.3f")
        peak_rate = e1.number_input("Peak rate ($/kWh)",  value=defaults.get("peak_rate", 0.0), step=0.00001, format="%.5f")
        pp_kwh    = e2.number_input("Part-peak kWh",      value=defaults.get("part_peak_kwh", 0.0), format="%.3f",
                                    disabled=(season=="winter"))
        pp_rate   = e2.number_input("Part-peak rate",     value=defaults.get("part_peak_rate", 0.0), step=0.00001, format="%.5f",
                                    disabled=(season=="winter"))
        off_kwh   = e3.number_input("Off-peak kWh",       value=defaults.get("off_peak_kwh", 0.0), format="%.3f")
        off_rate  = e3.number_input("Off-peak rate",      value=defaults.get("off_peak_rate", 0.0), step=0.00001, format="%.5f")
        sop_kwh   = e4.number_input("Super off-peak kWh", value=defaults.get("super_off_peak_kwh", 0.0), format="%.3f")
        sop_rate  = e4.number_input("Super off-peak rate",value=defaults.get("super_off_peak_rate", 0.0), step=0.00001, format="%.5f")

        st.markdown("**Demand**")
        d1, d2, d3 = st.columns(3)
        mpd_kw     = d1.number_input("Max peak demand (kW)",      value=defaults.get("max_peak_demand_kw", 0.0), format="%.3f")
        mpd_rate   = d1.number_input("Max peak demand ($/kW)",    value=defaults.get("max_peak_demand_rate", 0.0), step=0.001, format="%.3f")
        mppd_kw    = d2.number_input("Max part-peak demand (kW)", value=defaults.get("max_part_peak_demand_kw", 0.0), format="%.3f",
                                     disabled=(season=="winter"))
        mppd_rate  = d2.number_input("Max part-peak rate ($/kW)", value=defaults.get("max_part_peak_demand_rate", 0.0), step=0.001, format="%.3f",
                                     disabled=(season=="winter"))
        md_kw      = d3.number_input("Max demand (kW)",           value=defaults.get("max_demand_kw", 0.0), format="%.3f")
        md_rate    = d3.number_input("Max demand ($/kW)",         value=defaults.get("max_demand_rate", 0.0), step=0.001, format="%.3f")

        cust_daily = st.number_input("Customer charge ($/day)", value=defaults.get("cust_charge_per_day", 11.36882), step=0.00001, format="%.5f")

        st.markdown("**Adjustments**")
        a1, a2, a3 = st.columns(3)
        gen_credit = a1.number_input("Generation credit ($, enter as positive)", value=defaults.get("generation_credit", 0.0), format="%.2f")
        pcia       = a2.number_input("PCIA ($)",                                  value=defaults.get("pcia", 0.0), format="%.2f")
        ffs        = a3.number_input("Franchise Fee Surcharge ($)",               value=defaults.get("ffs", 0.0), format="%.2f")

        st.markdown("**Tax — PG&E Delivery Side**")
        t1, t2 = st.columns(2)
        city           = t1.selectbox("City (for UUT lookup)", list(CITY_UUT_RATES.keys()),
                                      index=list(CITY_UUT_RATES.keys()).index(defaults.get("city","Other / Unknown")))
        uut_delivery   = t2.number_input("UUT rate on delivery (%)", value=defaults.get("uut_pct_delivery", 0.0) * 100,
                                         step=0.1, format="%.2f") / 100
        if city != "Other / Unknown":
            st.caption(f"Standard {city} UUT rate: **{CITY_UUT_RATES[city]*100:.1f}%** — adjust if bill shows different amount")

    cca_lines = {}
    if is_cca:
        with st.expander("⚡ CCA Generation Side", expanded=True):
            st.markdown("**CCA energy generation rates**")
            g1, g2, g3 = st.columns(3)
            cca_pk_kwh  = g1.number_input("CCA peak kWh",           value=defaults.get("cca_peak_kwh", peak_kwh), format="%.3f")
            cca_pk_rate = g1.number_input("CCA peak rate ($/kWh)",  value=defaults.get("cca_peak_rate", 0.0), step=0.00001, format="%.5f")
            cca_off_kwh  = g2.number_input("CCA off-peak kWh",       value=defaults.get("cca_off_peak_kwh", off_kwh), format="%.3f")
            cca_off_rate = g2.number_input("CCA off-peak rate",      value=defaults.get("cca_off_peak_rate", 0.0), step=0.00001, format="%.5f")
            cca_sop_kwh  = g3.number_input("CCA super off-peak kWh", value=defaults.get("cca_super_off_peak_kwh", sop_kwh), format="%.3f")
            cca_sop_rate = g3.number_input("CCA super off-peak rate",value=defaults.get("cca_super_off_peak_rate", 0.0), step=0.00001, format="%.5f")

            st.markdown("**CCA demand & premium program**")
            h1, h2, h3, h4 = st.columns(4)
            cca_d_kw    = h1.number_input("CCA demand (kW)",        value=defaults.get("cca_demand_kw", 0.0), format="%.3f")
            cca_d_rate  = h1.number_input("CCA demand rate ($/kW)", value=defaults.get("cca_demand_rate", 0.0), step=0.001, format="%.3f")
            prem_kwh    = h2.number_input("Premium program kWh",    value=defaults.get("cca_premium_kwh", 0.0), format="%.0f")
            prem_rate   = h2.number_input("Premium rate ($/kWh)",   value=defaults.get("cca_premium_rate", 0.0), step=0.00001, format="%.5f")
            pcia_cr     = h3.number_input("PCIA Credit ($, positive)", value=defaults.get("pcia_credit", 0.0), format="%.2f")
            ffs_cr      = h3.number_input("FFS Credit ($, positive)",  value=defaults.get("ffs_credit", 0.0), format="%.2f")
            cca_disc    = h4.number_input("CCA discount ($, positive)", value=defaults.get("cca_discount", 0.0), format="%.2f")

            st.markdown("**Tax — CCA Generation Side**")
            tx1, tx2, tx3 = st.columns(3)
            uut_cca = tx1.number_input("UUT rate on CCA (%)", value=defaults.get("uut_pct_cca", 0.0) * 100,
                                       step=0.1, format="%.2f") / 100
            ect     = tx2.number_input("Energy Commission Tax ($)", value=defaults.get("energy_commission_tax", 0.0), format="%.2f")

            cca_lines = dict(
                cca_peak_kwh=cca_pk_kwh, cca_peak_rate=cca_pk_rate,
                cca_off_peak_kwh=cca_off_kwh, cca_off_peak_rate=cca_off_rate,
                cca_super_off_peak_kwh=cca_sop_kwh, cca_super_off_peak_rate=cca_sop_rate,
                cca_demand_kw=cca_d_kw, cca_demand_rate=cca_d_rate,
                cca_premium_kwh=prem_kwh, cca_premium_rate=prem_rate,
                pcia_credit=pcia_cr, ffs_credit=ffs_cr, cca_discount=cca_disc,
                uut_pct_cca=uut_cca, energy_commission_tax=ect,
            )
    else:
        cca_lines = dict(
            cca_peak_kwh=0, cca_peak_rate=0, cca_off_peak_kwh=0, cca_off_peak_rate=0,
            cca_super_off_peak_kwh=0, cca_super_off_peak_rate=0,
            cca_demand_kw=0, cca_demand_rate=0, cca_premium_kwh=0, cca_premium_rate=0,
            pcia_credit=0, ffs_credit=0, cca_discount=0, uut_pct_cca=0, energy_commission_tax=0,
        )

    with st.expander("✅ Actual Bill Totals (for reconciliation)", expanded=True):
        r1, r2 = st.columns(2)
        actual_pge = r1.number_input("Actual PG&E delivery total ($)", value=defaults.get("actual_pge_delivery_total", 0.0), format="%.2f")
        actual_cca = r2.number_input("Actual CCA total ($, 0 if bundled)", value=defaults.get("actual_cca_total", 0.0), format="%.2f")

    inp = PGEAuditInputs(
        meter_id=meter_id, site_name=site_name, rate_schedule=rate_schedule,
        billing_days=billing_days, season=season, voltage=voltage,
        is_mandatory=is_mandatory, is_cca=is_cca, cca_provider=cca_provider,
        peak_kwh=peak_kwh, part_peak_kwh=pp_kwh if season=="summer" else 0,
        off_peak_kwh=off_kwh, super_off_peak_kwh=sop_kwh if season=="winter" else 0,
        max_peak_demand_kw=mpd_kw, max_part_peak_demand_kw=mppd_kw if season=="summer" else 0,
        max_demand_kw=md_kw,
        peak_rate=peak_rate, part_peak_rate=pp_rate, off_peak_rate=off_rate,
        super_off_peak_rate=sop_rate, max_peak_demand_rate=mpd_rate,
        max_part_peak_demand_rate=mppd_rate, max_demand_rate=md_rate,
        cust_charge_per_day=cust_daily,
        generation_credit=gen_credit, pcia=pcia, ffs=ffs,
        city=city, uut_pct_delivery=uut_delivery,
        actual_pge_delivery_total=actual_pge, actual_cca_total=actual_cca,
        **cca_lines,
    )

    result = calc_pge_audit(inp)

    st.divider()
    st.markdown("### Audit Results")

    # Summary
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("PG&E Delivery — Computed", fmt(result.pge_computed))
    s2.metric("CCA Generation — Computed", fmt(result.cca_computed))
    s3.metric("Total Computed", fmt(result.total_computed))
    delta_pct = (result.total_delta / result.total_actual * 100) if result.total_actual > 0 else 0
    s4.metric("Variance vs Actual",
              fmt(result.total_delta),
              delta=f"{delta_pct:+.2f}%")

    if abs(result.total_delta) < 1.00:
        st.success(f"✅ Perfect reconciliation — computed matches actual within {fmt(abs(result.total_delta))}")
    elif abs(result.total_delta) < 50:
        st.warning(f"⚠️ Small variance of {fmt(result.total_delta)} — likely rounding")
    else:
        st.error(f"❌ Variance of {fmt(result.total_delta)} ({delta_pct:+.2f}%) — investigate")

    # PG&E delivery breakdown
    ca, cb = st.columns(2)
    with ca:
        st.markdown("**PG&E Electric Delivery**")
        for line in result.pge_lines:
            color = "#dc2626" if line.computed < 0 else "#111827"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:.82rem;"
                f"padding:2px 0;border-bottom:1px solid #f3f4f6'>"
                f"<span style='color:#6b7280'>{line.label}</span>"
                f"<span style='color:{color};font-weight:500'>{fmt(line.computed)}</span>"
                f"</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;font-weight:700;"
            f"font-size:.9rem;padding:5px 0;border-top:2px solid #d1d5db;margin-top:4px'>"
            f"<span>PG&E Delivery Total</span><span>{fmt(result.pge_computed)}</span></div>",
            unsafe_allow_html=True)
        if actual_pge > 0:
            d = result.pge_computed - actual_pge
            if abs(d) < 1:
                st.success(f"✅ Matches actual {fmt(actual_pge)} within {fmt(abs(d))}")
            else:
                st.warning(f"Δ {fmt(d)} vs actual {fmt(actual_pge)}")

    with cb:
        if is_cca and result.cca_lines:
            st.markdown("**CCA Generation**")
            for line in result.cca_lines:
                color = "#dc2626" if line.computed < 0 else "#111827"
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;font-size:.82rem;"
                    f"padding:2px 0;border-bottom:1px solid #f3f4f6'>"
                    f"<span style='color:#6b7280'>{line.label}</span>"
                    f"<span style='color:{color};font-weight:500'>{fmt(line.computed)}</span>"
                    f"</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-weight:700;"
                f"font-size:.9rem;padding:5px 0;border-top:2px solid #d1d5db;margin-top:4px'>"
                f"<span>CCA Total</span><span>{fmt(result.cca_computed)}</span></div>",
                unsafe_allow_html=True)
            if actual_cca > 0:
                d = result.cca_computed - actual_cca
                if abs(d) < 1:
                    st.success(f"✅ Matches actual {fmt(actual_cca)} within {fmt(abs(d))}")
                else:
                    st.warning(f"Δ {fmt(d)} vs actual {fmt(actual_cca)}")

    st.caption(f"Effective rate (computed): **${result.effective_rate_computed:.4f}/kWh**  |  "
               + (f"Effective rate (actual): **${result.effective_rate_actual:.4f}/kWh**" if result.total_actual > 0 else ""))


# ── MODE 2: Historical upload ─────────────────────────────────────────────────
def _render_history():
    st.markdown("### Historical Bill Series — Upload & Audit")
    st.markdown(
        "Upload a CSV or Excel file with one row per meter per billing period. "
        "The tool re-engineers each bill line by line and flags variances vs actual billed amounts.")

    col_dl, _ = st.columns([1, 3])
    with col_dl:
        tpl = generate_pge_template()
        st.download_button("⬇️ Download CSV template", tpl,
                           file_name="pge_bill_template.csv", mime="text/csv")

    st.markdown("**Key column groups:**")
    groups = {
        "Identification": "billing_period, meter_id, site_name, rate_schedule, billing_days, season, voltage, city",
        "PG&E Delivery Usage": "peak_kwh, off_peak_kwh, super_off_peak_kwh, part_peak_kwh",
        "PG&E Demand": "max_peak_demand_kw, max_demand_kw, max_part_peak_demand_kw",
        "PG&E Rates (from bill)": "peak_rate, off_peak_rate, super_off_peak_rate, max_demand_rate, cust_charge_per_day",
        "Adjustments": "generation_credit, pcia, ffs",
        "CCA Generation (if CCA)": "cca_peak_kwh, cca_peak_rate, cca_off_peak_kwh, cca_off_peak_rate, pcia_credit, ffs_credit",
        "Taxes": "uut_pct_delivery, uut_pct_cca, energy_commission_tax",
        "Actuals": "actual_pge_delivery_total, actual_cca_total",
    }
    for group, cols in groups.items():
        st.markdown(f"- **{group}:** `{cols}`")

    uploaded = st.file_uploader("Upload bill history (CSV or Excel)", type=["csv","xlsx","xls"])
    if uploaded:
        df, warnings = load_and_validate_csv(uploaded, "pge")
        if warnings:
            for w in warnings:
                st.warning(w)
        if not df.empty:
            st.success(f"Loaded {len(df)} billing record(s)")
            with st.spinner("Re-engineering bills…"):
                results = process_pge_history(df)
            render_audit_table(results, "PG&E — Bill Re-engineering Results")


# ── Sample bill pre-population ────────────────────────────────────────────────
def _get_sample_defaults(sample: str) -> dict:
    if "Stockton B10S" in sample and "K" in sample:
        return dict(
            meter_id="1004464911", site_name="1505 Tillie Lewis Dr Ste K",
            rate_schedule="B-10", billing_days=29, season="winter",
            voltage="secondary", is_mandatory=False, is_cca=True,
            cca_provider="Ava Community Energy",
            peak_kwh=2414.520, off_peak_kwh=5168.580, super_off_peak_kwh=2087.280,
            peak_rate=0.26321, off_peak_rate=0.22773, super_off_peak_rate=0.19139,
            max_peak_demand_kw=36.48, max_demand_rate=20.50,
            max_peak_demand_rate=0.0, max_demand_kw=36.48,
            cust_charge_per_day=11.36882,
            generation_credit=1057.21, pcia=505.95, ffs=4.84,
            city="Stockton", uut_pct_delivery=0.06,
            cca_peak_kwh=2414.520, cca_peak_rate=0.14379,
            cca_off_peak_kwh=5168.580, cca_off_peak_rate=0.10831,
            cca_super_off_peak_kwh=2087.280, cca_super_off_peak_rate=0.07197,
            pcia_credit=505.96, ffs_credit=4.83, cca_discount=5.29,
            uut_pct_cca=0.06, energy_commission_tax=2.90,
            actual_pge_delivery_total=2907.47, actual_cca_total=576.50,
        )
    elif "Stockton B1" in sample and "E" in sample:
        return dict(
            meter_id="1004561490", site_name="1505 Tillie Lewis Dr Ste E",
            rate_schedule="B-1", billing_days=29, season="winter",
            voltage="secondary", is_mandatory=False, is_cca=True,
            cca_provider="Ava Community Energy",
            peak_kwh=1907.759, off_peak_kwh=4140.345, super_off_peak_kwh=1828.047,
            peak_rate=0.39545, off_peak_rate=0.37933, super_off_peak_rate=0.36291,
            cust_charge_per_day=0.82136,
            generation_credit=827.81, pcia=390.42, ffs=3.70,
            city="Stockton", uut_pct_delivery=0.06,
            cca_peak_kwh=1907.759, cca_peak_rate=0.12113,
            cca_off_peak_kwh=4140.345, cca_off_peak_rate=0.10501,
            cca_super_off_peak_kwh=1828.047, cca_super_off_peak_rate=0.08859,
            pcia_credit=390.43, ffs_credit=3.71, cca_discount=4.14,
            uut_pct_cca=0.06, energy_commission_tax=2.36,
            actual_pge_delivery_total=2733.02, actual_cca_total=457.67,
        )
    elif "Hayward" in sample:
        return dict(
            meter_id="1010095036", site_name="3466 Enterprise Ave Hayward",
            rate_schedule="B-19", billing_days=29, season="winter",
            voltage="secondary", is_mandatory=False, is_cca=True,
            cca_provider="Renewable100",
            peak_kwh=9343.6, off_peak_kwh=24852.0, super_off_peak_kwh=11534.4,
            peak_rate=0.16188, off_peak_rate=0.12026, super_off_peak_rate=0.06442,
            max_peak_demand_kw=112.0, max_peak_demand_rate=2.310,
            max_demand_kw=171.2, max_demand_rate=37.370,
            cust_charge_per_day=11.36882,
            generation_credit=3609.77, pcia=1634.39, ffs=26.07,
            city="Hayward", uut_pct_delivery=0.055,
            cca_peak_kwh=9343.6, cca_peak_rate=0.12050,
            cca_off_peak_kwh=24852.0, cca_off_peak_rate=0.07884,
            cca_super_off_peak_kwh=11534.4, cca_super_off_peak_rate=0.02302,
            cca_demand_kw=112.0, cca_demand_rate=2.310,
            cca_premium_kwh=45730.0, cca_premium_rate=0.01750,
            pcia_credit=1634.39, ffs_credit=26.07, cca_discount=0.0,
            uut_pct_cca=0.055, energy_commission_tax=13.72,
            actual_pge_delivery_total=13759.73, actual_cca_total=0.0,
        )
    return {}
