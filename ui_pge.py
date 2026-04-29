"""
Pacific Gas & Electric Company — Streamlit UI
"""
import streamlit as st
from billing_pge import calc_pge_bill, PGEInputs, PGE_RATES
from ui_shared import render_bill_card, render_summary_metrics


def render_pge():
    st.markdown("## ⚡ Pacific Gas & Electric Company (PG&E)")
    st.markdown(
        '<div class="info-box">Rates effective March 1, 2026 · Advice 7846-E · '
        'CPUC Authorized · Bundled Service (Generation + Delivery)</div>',
        unsafe_allow_html=True)

    # ── Rate eligibility helper ───────────────────────────────────────────────
    with st.expander("ℹ️ Rate Eligibility by Demand Level", expanded=False):
        st.markdown("""
| Schedule | Demand Threshold | Service Voltage | Notes |
|----------|-----------------|-----------------|-------|
| **B-1** | < 75 kW | Secondary | Energy-only TOU, no demand charge |
| **B-6** | 75 – 499 kW | Secondary / Primary | TOU demand metered |
| **B-10** | 75 – 499 kW | Secondary / Primary | Alternative to B-6 |
| **B-19** | 500 – 999 kW | Secondary / Primary / Transmission | Mandatory above 499 kW |
| **B-20** | ≥ 1,000 kW | Secondary / Primary / Transmission | Mandatory above 999 kW |

**Peak hours (all seasons):** 4:00 PM – 9:00 PM every day including weekends  
**Summer:** June 1 – September 30 · **Winter:** October 1 – May 31  
**Super off-peak (winter only):** 9:00 AM – 2:00 PM in March, April, May
        """)

    # ── Usage Inputs ─────────────────────────────────────────────────────────
    with st.expander("📥 Monthly Usage Inputs", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            season = st.selectbox(
                "Season",
                options=["summer", "winter"],
                format_func=lambda x: "Summer (Jun–Sep)" if x == "summer" else "Winter (Oct–May)")
            billing_days = st.number_input("Billing days", min_value=28, max_value=33,
                                           value=30, step=1)
            voltage = st.selectbox(
                "Service voltage",
                options=["secondary", "primary", "transmission"],
                format_func=lambda x: {
                    "secondary": "Secondary (standard, most C&I)",
                    "primary": "Primary (customer-owned transformer)",
                    "transmission": "Transmission (very large industrial)",
                }[x])

        with col2:
            peak_kwh = st.number_input("Peak kWh (4–9 PM daily)", min_value=0.0,
                                       value=150_000.0, step=1000.0, format="%.0f")
            if season == "summer":
                part_peak_kwh = st.number_input("Part-peak kWh (2–4 PM & 9–11 PM, summer only)",
                                                min_value=0.0, value=80_000.0,
                                                step=1000.0, format="%.0f")
            else:
                part_peak_kwh = 0.0
                st.info("No part-peak period in winter.")
            off_peak_kwh = st.number_input("Off-peak kWh", min_value=0.0,
                                           value=200_000.0, step=1000.0, format="%.0f")
            if season == "winter":
                super_off_peak_kwh = st.number_input(
                    "Super off-peak kWh (9 AM–2 PM, Mar–May only)",
                    min_value=0.0, value=0.0, step=1000.0, format="%.0f")
            else:
                super_off_peak_kwh = 0.0

            total_kwh = peak_kwh + part_peak_kwh + off_peak_kwh + super_off_peak_kwh
            st.metric("Total kWh", f"{total_kwh:,.0f}")

        with col3:
            max_peak_demand = st.number_input("Max peak demand (kW, 4–9 PM)", min_value=0.0,
                                              value=600.0, step=10.0, format="%.1f")
            if season == "summer":
                max_part_peak_demand = st.number_input("Max part-peak demand (kW, summer)",
                                                       min_value=0.0, value=550.0,
                                                       step=10.0, format="%.1f")
            else:
                max_part_peak_demand = 0.0
            max_demand = st.number_input("Max demand — all hours (kW)", min_value=0.0,
                                         value=700.0, step=10.0, format="%.1f")
            power_factor = st.number_input("Power factor (%)", min_value=70.0,
                                           max_value=100.0, value=85.0, step=0.5, format="%.1f")
            phase = st.selectbox("Phase (B-1 only)", options=["poly", "single"],
                                 format_func=lambda x: "Poly-phase" if x == "poly" else "Single-phase")

        # B-19 mandatory vs voluntary
        is_mandatory = st.checkbox("B-19: Mandatory service (demand >499 kW for 3+ months)?",
                                   value=True,
                                   help="Affects customer charge — mandatory customers pay ~$58/day vs ~$11/day for voluntary")

    # ── Rate selector ─────────────────────────────────────────────────────────
    with st.expander("📊 Rate Schedules to Compare", expanded=True):
        all_rates = list(PGE_RATES.keys())
        rate_labels = {k: v["name"] for k, v in PGE_RATES.items()}
        col_a, col_b = st.columns(2)
        with col_a:
            rate_a_key = st.selectbox("Rate A", options=all_rates,
                                      format_func=lambda k: rate_labels[k],
                                      index=all_rates.index("B-19"))
        with col_b:
            rate_b_key = st.selectbox("Rate B", options=all_rates,
                                      format_func=lambda k: rate_labels[k],
                                      index=all_rates.index("B-20"))

    # ── Build inputs & calculate ──────────────────────────────────────────────
    inp = PGEInputs(
        peak_kwh=peak_kwh,
        part_peak_kwh=part_peak_kwh,
        off_peak_kwh=off_peak_kwh,
        super_off_peak_kwh=super_off_peak_kwh,
        max_peak_demand_kw=max_peak_demand,
        max_part_peak_demand_kw=max_part_peak_demand if season == "summer" else 0.0,
        max_demand_kw=max_demand,
        season=season,
        voltage=voltage,
        phase=phase,
        is_mandatory=is_mandatory,
        billing_days=billing_days,
        power_factor_pct=power_factor,
    )

    bill_a = calc_pge_bill(rate_a_key, inp)
    bill_b = calc_pge_bill(rate_b_key, inp)

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.divider()
    render_summary_metrics(bill_a, bill_b)

    # ── Bill cards ─────────────────────────────────────────────────────────────
    st.divider()
    col_a, col_b = st.columns(2)
    winner_a = bill_a.total <= bill_b.total
    with col_a:
        render_bill_card(bill_a, is_winner=winner_a)
    with col_b:
        render_bill_card(bill_b, is_winner=not winner_a)

    # ── Demand eligibility warnings ────────────────────────────────────────────
    st.divider()
    st.markdown("**📋 Eligibility notes for selected rates:**")
    for rk in [rate_a_key, rate_b_key]:
        st.caption(f"**{rk}:** {PGE_RATES[rk]['eligibility']}  |  {PGE_RATES[rk]['notes']}")

    st.caption(
        "Note: Estimated bills for informational comparison only. "
        "B-6 and B-10 demand charges are approximate — verify with current PG&E tariff sheets. "
        "Does not include PDP event charges/credits, Option R/S adjustments, or CCA/DA components."
    )
