"""
Shared UI rendering components
"""
import streamlit as st
from billing_menasha import BillResult


def fmt(amount: float) -> str:
    """Format a dollar amount with sign handling."""
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def render_bill_card(bill: BillResult, is_winner: bool = False,
                     actual_bill: float | None = None):
    """Render a single bill breakdown card."""
    card_class = "bill-card-winner" if is_winner else "bill-card"
    total_class = "bill-total-winner" if is_winner else "bill-total"

    badge = ' <span class="winner-badge">✓ Lower bill</span>' if is_winner else ""
    st.markdown(
        f'<div class="{card_class}">'
        f'<div style="font-size:0.9rem;font-weight:600;margin-bottom:4px;">'
        f'{bill.rate_name}{badge}</div>'
        f'<div class="{total_class}">{fmt(bill.total)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if bill.is_cp4:
        st.markdown(
            f'<div class="info-box">Cp-4 uses PCAC2 (separate demand & energy wholesale adjustments). '
            f'Load factor: <strong>{bill.load_factor:.1f}%</strong> '
            f'(eligibility requires ≥85%)</div>',
            unsafe_allow_html=True)

    st.markdown('<div class="section-label">Bill breakdown</div>', unsafe_allow_html=True)

    for line in bill.lines:
        color = "#dc2626" if line.amount < 0 else "#111827"
        st.markdown(
            f'<div class="line-item">'
            f'<span style="color:#6b7280;">{line.label}</span>'
            f'<span style="color:{color};font-weight:500;">{fmt(line.amount)}</span>'
            f'</div>',
            unsafe_allow_html=True)

    st.markdown(
        f'<div class="line-item" style="font-weight:700;border-top:2px solid #d1d5db;'
        f'margin-top:4px;padding-top:4px;">'
        f'<span>Total estimated bill</span>'
        f'<span>{fmt(bill.total)}</span>'
        f'</div>',
        unsafe_allow_html=True)

    # Effective rate
    st.markdown(
        f'<div style="font-size:0.78rem;color:#6b7280;margin-top:6px;">'
        f'Effective rate: <strong>${bill.effective_rate:.4f}/kWh</strong>'
        + (f' &nbsp;|&nbsp; Load factor: <strong>{bill.load_factor:.1f}%</strong>'
           if bill.load_factor > 0 else '') +
        f'</div>',
        unsafe_allow_html=True)

    # Reconciliation vs actual bill
    if actual_bill is not None:
        diff = bill.total - actual_bill
        pct = abs(diff) / actual_bill * 100
        if abs(diff) < 2.00:
            st.markdown(
                f'<div class="reconcile-ok">✅ Reconciles within {fmt(abs(diff))} of actual bill '
                f'({fmt(actual_bill)}) — rounding only.</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="reconcile-warn">⚠️ Difference of {fmt(diff)} ({pct:.2f}%) vs '
                f'actual bill of {fmt(actual_bill)}.</div>',
                unsafe_allow_html=True)


def render_summary_metrics(bill_a: BillResult, bill_b: BillResult):
    """Render the 4-metric summary row."""
    diff = bill_a.total - bill_b.total
    monthly_savings = abs(diff)
    annual_savings = monthly_savings * 12
    winner = bill_a.rate_name if diff <= 0 else bill_b.rate_name

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rate A — Total Bill", fmt(bill_a.total),
                  delta=None)
    with col2:
        st.metric("Rate B — Total Bill", fmt(bill_b.total),
                  delta=None)
    with col3:
        st.metric("Monthly Difference", fmt(monthly_savings),
                  delta=f"{winner} is lower")
    with col4:
        st.metric("Annualized Savings", fmt(annual_savings),
                  delta=f"if on {winner} all year")

    # Effective rate comparison bar
    er_a = bill_a.effective_rate
    er_b = bill_b.effective_rate
    st.markdown(
        f"**Effective rate:** {bill_a.rate_name} = **${er_a:.4f}/kWh** &nbsp;|&nbsp; "
        f"{bill_b.rate_name} = **${er_b:.4f}/kWh** &nbsp;|&nbsp; "
        f"Difference = **${abs(er_a - er_b):.4f}/kWh**"
    )

    # Progress bar showing relative bill sizes
    if bill_a.total + bill_b.total > 0:
        ratio_a = bill_a.total / (bill_a.total + bill_b.total)
        st.progress(ratio_a, text=f"← Rate A ({ratio_a*100:.0f}% of combined)   Rate B →")
