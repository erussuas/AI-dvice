"""
Menasha Electric & Water Utilities — UI
Mode 1: Single-bill demo / comparison calculator
Mode 2: Historical bill series upload & audit
"""
import streamlit as st
import pandas as pd
from billing_menasha import calc_menasha_bill, MenashaInputs, MENASHA_RATES
from bill_history import (generate_menasha_template, load_and_validate_csv,
                           process_menasha_history)
from ui_shared import render_bill_card, render_comparison_summary, render_audit_table, fmt


def render_menasha():
    st.markdown("## ⚡ Menasha Electric & Water Utilities")
    st.caption("Amendment No. 87 · Effective June 1, 2025 · PSCW Docket 3560-ER-108")

    mode = st.radio("Mode", ["📊 Single Bill — Demo / Comparison", "📂 Historical Bill Series — Upload & Audit"],
                    horizontal=True)
    st.divider()

    if mode.startswith("📊"):
        _render_single_bill()
    else:
        _render_history()


# ── MODE 1: Single bill ───────────────────────────────────────────────────────
def _render_single_bill():
    st.markdown("### Single Bill — Enter usage data and compare two rate schedules")
    st.caption("Pre-loaded with Sonoco U.S. Paper Mills — January 2026 (Cp-4). Edit any field to model scenarios.")

    # Rate period selector
    rate_period = st.radio(
        "Rate period",
        ["2025", "2021"],
        format_func=lambda x: {
            "2025": "📋 Current rates — Amendment No. 87 (June 1, 2025 – present, Docket 3560-ER-108)",
            "2021": "📋 Prior rates — Docket 3560-ER-107 (Dec 18, 2020 – May 31, 2025)",
        }[x],
        horizontal=True,
    )
    if rate_period == "2021":
        st.info("Using rates from Docket 3560-ER-107 (Final Decision Dec 17, 2020). "
                "PCAC base = $0.0727/kWh · BECF = $0.0328/kWh · "
                "Cp-4 BDCF: Jul/Aug $23.2413, Jun/Sep $19.4858, Other $18.0153")

    with st.expander("📥 Monthly Usage Inputs", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            on_peak_kwh  = st.number_input("On-peak kWh", min_value=0.0, value=1_983_890.0, step=1000.0, format="%.0f")
            off_peak_kwh = st.number_input("Off-peak kWh", min_value=0.0, value=3_982_720.0, step=1000.0, format="%.0f")
            st.metric("Total kWh", f"{on_peak_kwh + off_peak_kwh:,.0f}")
        with c2:
            on_peak_demand = st.number_input("On-peak max demand (kW)", min_value=0.0, value=8_732.92, step=10.0, format="%.2f")
            dist_demand    = st.number_input("Distribution demand — 12-mo peak (kW)", min_value=0.0, value=8_987.90, step=10.0, format="%.2f")
            month_type = st.selectbox("Billing month", ["other","shoulder","peak"],
                                      format_func=lambda x: {"peak":"July/August","shoulder":"June/September","other":"All other months"}[x])
        with c3:
            phase             = st.selectbox("Phase", ["three","single"], format_func=lambda x: "Three-phase" if x=="three" else "Single-phase")
            primary_metering  = st.checkbox("Primary metering discount (2%)", value=True)
            xfmr_ownership    = st.checkbox("Transformer ownership credit ($0.25/kW dist. demand)", value=True)
            sales_tax_pct     = st.number_input("Sales/use tax rate (%)", min_value=0.0, max_value=10.0, value=0.700, step=0.001, format="%.3f") / 100

    with st.expander("⚙️ PCAC / PCAC2 Adjustment Inputs", expanded=True):
        pcac = st.number_input("PCAC rate ($/kWh) — all schedules except Cp-4",
                               min_value=-0.05, max_value=0.20, value=0.0000, step=0.0001, format="%.4f")
        st.markdown("**PCAC2 — Cp-4 only**")
        pcac2_mode = st.radio("Entry mode", ["direct","formula"],
                              format_func=lambda x: "Enter ECA/DCA rates from bill" if x=="direct" else "Enter wholesale cost inputs (WDC/RBD/WEC)",
                              horizontal=True)
        if pcac2_mode == "direct":
            p1, p2 = st.columns(2)
            eca_rate = p1.number_input("ECA ($/kWh)", value=0.0003, step=0.0001, format="%.4f")
            dca_rate = p2.number_input("DCA ($/kW)",  value=-0.1170, step=0.0001, format="%.4f")
            wdc = wec = rbd = 0.0
        else:
            q1, q2, q3 = st.columns(3)
            wdc = q1.number_input("WDC ($)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
            rbd = q2.number_input("RBD (kW)", min_value=0.0, value=8_732.92, step=10.0, format="%.2f")
            wec = q3.number_input("WEC ($)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
            eca_rate = dca_rate = 0.0
        st.caption("BDCF: Jul/Aug $21.853 | Jun/Sep $17.962 | Other $16.497 | BECF: $0.0432/kWh")

    with st.expander("📊 Rate Schedules to Compare", expanded=True):
        all_keys   = list(MENASHA_RATES.keys())
        rate_names = {k: v["name"] for k, v in MENASHA_RATES.items()}
        ca, cb = st.columns(2)
        rate_a = ca.selectbox("Rate A", all_keys, format_func=lambda k: rate_names[k], index=all_keys.index("Cp-4"))
        rate_b = cb.selectbox("Rate B", all_keys, format_func=lambda k: rate_names[k], index=all_keys.index("Cp-3"))

    inp = MenashaInputs(
        on_peak_kwh=on_peak_kwh, off_peak_kwh=off_peak_kwh,
        on_peak_demand_kw=on_peak_demand, dist_demand_kw=dist_demand,
        phase=phase, month_type=month_type, pcac=pcac,
        primary_metering=primary_metering, xfmr_ownership=xfmr_ownership,
        sales_tax_pct=sales_tax_pct,
        eca_rate=eca_rate, dca_rate=dca_rate, pcac2_mode=pcac2_mode,
        wdc=wdc, rbd=rbd, wec=wec,
        rate_period=rate_period,
    )

    bill_a = calc_menasha_bill(rate_a, inp)
    bill_b = calc_menasha_bill(rate_b, inp)
    winner_a = bill_a.total <= bill_b.total

    st.divider()
    render_comparison_summary(bill_a, bill_b)
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        render_bill_card(bill_a, is_winner=winner_a,
                         actual_bill=419_902.71 if rate_a == "Cp-4" else None)
    with col_b:
        render_bill_card(bill_b, is_winner=not winner_a,
                         actual_bill=419_902.71 if rate_b == "Cp-4" else None)

    if rate_a == "Cp-4" or rate_b == "Cp-4":
        lf = bill_a.load_factor if rate_a == "Cp-4" else bill_b.load_factor
        if lf < 85.0:
            st.warning(f"⚠️ Load factor {lf:.1f}% is below the 85% Cp-4 eligibility threshold.")
        else:
            st.success(f"✅ Load factor {lf:.1f}% — meets Cp-4 ≥85% requirement.")

    st.caption("Estimated bills for comparison only. Verify with Menasha Utilities.")


# ── MODE 2: Historical upload ─────────────────────────────────────────────────
def _render_history():
    st.markdown("### Historical Bill Series — Upload & Audit")

    st.markdown(
        "Upload a CSV or Excel file with one row per billing period. "
        "The tool re-engineers each bill and flags any discrepancies vs actual billed amounts.")

    col_dl, _ = st.columns([1, 3])
    with col_dl:
        tpl = generate_menasha_template()
        st.download_button("⬇️ Download CSV template", tpl,
                           file_name="menasha_bill_template.csv", mime="text/csv")

    st.markdown("**Column guide (key fields):**")
    cols_guide = {
        "billing_period": "YYYY-MM",
        "rate_schedule": "Cp-1 | Cp-2 | Cp-3 | Cp-4 | Gs-1 | Gs-2 | Rg-1 | Rg-2",
        "on_peak_kwh / off_peak_kwh": "Usage split by TOU period",
        "on_peak_demand_kw": "Monthly on-peak max demand",
        "dist_demand_kw": "12-month rolling peak demand",
        "pcac_rate": "Monthly PCAC $/kWh from utility report",
        "eca_rate / dca_rate": "Cp-4 only — from bill",
        "sales_tax_pct": "e.g. 0.007 for 0.7%",
        "actual_total": "Billed total from invoice",
    }
    st.dataframe(pd.DataFrame(list(cols_guide.items()), columns=["Column", "Description"]),
                 use_container_width=True, hide_index=True, height=280)

    uploaded = st.file_uploader("Upload bill history (CSV or Excel)", type=["csv","xlsx","xls"])
    if uploaded:
        df, warnings = load_and_validate_csv(uploaded, "menasha")
        if warnings:
            for w in warnings:
                st.warning(w)
        if not df.empty:
            st.success(f"Loaded {len(df)} billing period(s)")
            with st.spinner("Re-engineering bills…"):
                results = process_menasha_history(df)
            render_audit_table(results, "Menasha — Bill Re-engineering Results")
