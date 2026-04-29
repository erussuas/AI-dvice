"""
Menasha Electric & Water Utilities — Streamlit UI
"""
import streamlit as st
from billing_menasha import calc_menasha_bill, MenashaInputs, MENASHA_RATES
from ui_shared import render_bill_card, render_summary_metrics


def render_menasha():
    st.markdown("## ⚡ Menasha Electric & Water Utilities")
    st.markdown(
        '<div class="info-box">Amendment No. 87 · Effective June 1, 2025 · '
        'PSCW Docket 3560-ER-108</div>', unsafe_allow_html=True)

    # ── Inputs ────────────────────────────────────────────────────────────────
    with st.expander("📥 Monthly Usage Inputs", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            on_peak_kwh = st.number_input("On-peak kWh", min_value=0.0,
                                          value=1_983_890.0, step=1000.0, format="%.0f")
            off_peak_kwh = st.number_input("Off-peak kWh", min_value=0.0,
                                           value=3_982_720.0, step=1000.0, format="%.0f")
            total_kwh = on_peak_kwh + off_peak_kwh
            st.metric("Total kWh", f"{total_kwh:,.0f}")
        with col2:
            on_peak_demand = st.number_input("On-peak max demand (kW)", min_value=0.0,
                                             value=8_732.92, step=10.0, format="%.2f")
            dist_demand = st.number_input("Distribution demand — 12-mo peak (kW)",
                                          min_value=0.0, value=8_987.90, step=10.0, format="%.2f")
            month_type = st.selectbox(
                "Billing month",
                options=["other", "shoulder", "peak"],
                format_func=lambda x: {
                    "peak": "July or August (summer peak)",
                    "shoulder": "June or September",
                    "other": "All other months",
                }[x],
                index=0,
            )
        with col3:
            phase = st.selectbox("Service phase",
                                 options=["three", "single"],
                                 format_func=lambda x: "Three-phase" if x == "three" else "Single-phase")
            primary_metering = st.checkbox("Primary metering discount (2%)", value=True)
            xfmr_ownership = st.checkbox("Transformer ownership credit ($0.25/kW)", value=True)
            sales_tax_pct = st.number_input("Sales/use tax rate (%)", min_value=0.0,
                                            max_value=10.0, value=0.700, step=0.001, format="%.3f") / 100

    with st.expander("⚙️ PCAC / PCAC2 Adjustment Inputs", expanded=True):
        pcac_col, _ = st.columns([1, 2])
        with pcac_col:
            pcac = st.number_input(
                "PCAC rate ($/kWh) — all schedules except Cp-4",
                min_value=-0.05, max_value=0.20, value=0.0000, step=0.0001, format="%.4f")

        st.markdown("**PCAC2 — Cp-4 only**")
        pcac2_mode = st.radio(
            "Entry mode",
            options=["direct", "formula"],
            format_func=lambda x: {
                "direct": "Enter ECA/DCA rates directly (from bill)",
                "formula": "Enter wholesale cost inputs (WDC / RBD / WEC)",
            }[x],
            horizontal=True,
        )

        if pcac2_mode == "direct":
            p1, p2 = st.columns(2)
            with p1:
                eca_rate = st.number_input("ECA — Energy Cost Adjustment ($/kWh)",
                                           value=0.0003, step=0.0001, format="%.4f")
            with p2:
                dca_rate = st.number_input("DCA — Demand Cost Adjustment ($/kW)",
                                           value=-0.1170, step=0.0001, format="%.4f")
            wdc = wec = rbd = 0.0
        else:
            q1, q2, q3 = st.columns(3)
            with q1:
                wdc = st.number_input("WDC — Wholesale demand-related cost ($)",
                                      min_value=0.0, value=0.0, step=1000.0, format="%.2f")
            with q2:
                rbd = st.number_input("RBD — Retail on-peak billing demand (kW)",
                                      min_value=0.0, value=8_732.92, step=10.0, format="%.2f")
            with q3:
                wec = st.number_input("WEC — Wholesale energy-related cost ($)",
                                      min_value=0.0, value=0.0, step=1000.0, format="%.2f")
            eca_rate = dca_rate = 0.0
        st.caption("BDCF: Jul/Aug $21.853 | Jun/Sep $17.962 | Other $16.497 | BECF: $0.0432/kWh")

    # ── Rate selector ─────────────────────────────────────────────────────────
    with st.expander("📊 Rate Schedules to Compare", expanded=True):
        all_rates = list(MENASHA_RATES.keys())
        rate_labels = {k: v["name"] for k, v in MENASHA_RATES.items()}
        col_a, col_b = st.columns(2)
        with col_a:
            rate_a_key = st.selectbox("Rate A", options=all_rates,
                                      format_func=lambda k: rate_labels[k],
                                      index=all_rates.index("Cp-4"))
        with col_b:
            rate_b_key = st.selectbox("Rate B", options=all_rates,
                                      format_func=lambda k: rate_labels[k],
                                      index=all_rates.index("Cp-3"))

    # ── Build inputs ──────────────────────────────────────────────────────────
    inp = MenashaInputs(
        on_peak_kwh=on_peak_kwh,
        off_peak_kwh=off_peak_kwh,
        on_peak_demand_kw=on_peak_demand,
        dist_demand_kw=dist_demand,
        phase=phase,
        month_type=month_type,
        pcac=pcac,
        primary_metering=primary_metering,
        xfmr_ownership=xfmr_ownership,
        sales_tax_pct=sales_tax_pct,
        eca_rate=eca_rate,
        dca_rate=dca_rate,
        pcac2_mode=pcac2_mode,
        wdc=wdc,
        rbd=rbd,
        wec=wec,
    )

    bill_a = calc_menasha_bill(rate_a_key, inp)
    bill_b = calc_menasha_bill(rate_b_key, inp)

    # ── Actual bill reconciliation (Sonoco Jan 2026) ──────────────────────────
    ACTUAL_BILL = 419_902.71
    reconcile_a = bill_a if rate_a_key == "Cp-4" else None
    reconcile_b = bill_b if rate_b_key == "Cp-4" else None

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.divider()
    render_summary_metrics(bill_a, bill_b)

    # ── Bill cards ────────────────────────────────────────────────────────────
    st.divider()
    col_a, col_b = st.columns(2)
    winner_a = bill_a.total <= bill_b.total
    with col_a:
        render_bill_card(bill_a, is_winner=winner_a,
                         actual_bill=ACTUAL_BILL if reconcile_a else None)
    with col_b:
        render_bill_card(bill_b, is_winner=not winner_a,
                         actual_bill=ACTUAL_BILL if reconcile_b else None)

    # ── Load factor warning for Cp-4 ─────────────────────────────────────────
    if rate_a_key == "Cp-4" or rate_b_key == "Cp-4":
        lf = bill_a.load_factor if rate_a_key == "Cp-4" else bill_b.load_factor
        if lf < 85.0:
            st.warning(
                f"⚠️ Computed load factor is {lf:.1f}% — below the 85% minimum required "
                f"for Cp-4 eligibility. Verify actual load factor with utility before modeling Cp-4."
            )
        else:
            st.success(f"✅ Load factor {lf:.1f}% — meets Cp-4 ≥85% eligibility requirement.")

    st.caption(
        "Note: Estimated bills for comparison purposes only. "
        "Actual bills may differ due to rounding, reactive charges, and other adjustments. "
        "Always verify with Menasha Utilities."
    )
