"""
Shared UI rendering components — used by both Menasha and PG&E modules.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from billing_menasha import BillResult


def fmt(amount: float) -> str:
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def fmt_delta(d: float) -> str:
    color = "green" if abs(d) < 1 else ("orange" if abs(d) < 50 else "red")
    sign = "+" if d > 0 else ""
    return f":{color}[{sign}{fmt(d)}]"


def render_bill_card(bill: BillResult, is_winner: bool = False,
                     actual_bill: float | None = None):
    card_bg = "#f0fdf4" if is_winner else "#f8f9fa"
    border  = "2px solid #16a34a" if is_winner else "1px solid #dee2e6"
    total_color = "#16a34a" if is_winner else "#111827"

    with st.container():
        st.markdown(
            f"""<div style="background:{card_bg};border:{border};border-radius:10px;
            padding:1rem 1.2rem;margin-bottom:0.5rem;">
            <div style="font-size:.85rem;font-weight:600;color:#374151">{bill.rate_name}
            {"&nbsp;<span style='background:#dcfce7;color:#16a34a;font-size:.7rem;"
             "padding:2px 9px;border-radius:999px;font-weight:700'>✓ Lower bill</span>" if is_winner else ""}
            </div>
            <div style="font-size:2rem;font-weight:700;color:{total_color};margin:.25rem 0">
            {fmt(bill.total)}</div></div>""",
            unsafe_allow_html=True)

        if bill.is_cp4:
            st.info(f"Cp-4 uses PCAC2. Load factor: **{bill.load_factor:.1f}%** "
                    f"(≥85% required for eligibility)")

        st.markdown("**Bill breakdown**")
        for line in bill.lines:
            color = "#dc2626" if line.amount < 0 else "#111827"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"font-size:.82rem;padding:2px 0;border-bottom:1px solid #f3f4f6'>"
                f"<span style='color:#6b7280'>{line.label}</span>"
                f"<span style='color:{color};font-weight:500'>{fmt(line.amount)}</span>"
                f"</div>", unsafe_allow_html=True)

        st.markdown(
            f"<div style='display:flex;justify-content:space-between;font-weight:700;"
            f"font-size:.9rem;padding:6px 0;border-top:2px solid #d1d5db;margin-top:4px'>"
            f"<span>Total estimated bill</span><span>{fmt(bill.total)}</span></div>",
            unsafe_allow_html=True)

        st.caption(f"Effective rate: **${bill.effective_rate:.4f}/kWh**"
                   + (f"  |  Load factor: **{bill.load_factor:.1f}%**" if bill.load_factor > 0 else ""))

        if actual_bill is not None and actual_bill > 0:
            diff = bill.total - actual_bill
            pct  = abs(diff) / actual_bill * 100
            if abs(diff) < 2.00:
                st.success(f"✅ Reconciles within {fmt(abs(diff))} of actual bill ({fmt(actual_bill)})")
            else:
                st.warning(f"⚠️ {fmt(diff)} difference ({pct:.2f}%) vs actual {fmt(actual_bill)}")


def render_comparison_summary(bill_a: BillResult, bill_b: BillResult):
    diff   = bill_a.total - bill_b.total
    winner = bill_a.rate_name if diff <= 0 else bill_b.rate_name
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rate A — Total", fmt(bill_a.total))
    c2.metric("Rate B — Total", fmt(bill_b.total))
    c3.metric("Monthly Difference", fmt(abs(diff)), delta=f"{winner} is lower")
    c4.metric("Annualized Savings", fmt(abs(diff) * 12))
    st.markdown(
        f"Effective rates: **{bill_a.rate_name}** = ${bill_a.effective_rate:.4f}/kWh  |  "
        f"**{bill_b.rate_name}** = ${bill_b.effective_rate:.4f}/kWh  |  "
        f"Δ = ${abs(bill_a.effective_rate - bill_b.effective_rate):.4f}/kWh")


def render_audit_table(df: pd.DataFrame, title: str = "Historical Bill Re-engineering"):
    """Render the multi-month audit results table with color coding and chart."""
    if df.empty:
        st.warning("No data to display.")
        return

    st.markdown(f"### {title}")

    # Summary metrics
    total_computed = df["Computed ($)"].sum()
    total_actual   = df["Actual ($)"].sum()
    total_delta    = total_computed - total_actual
    flagged        = (df["Flag"] == "⚠️").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Computed", fmt(total_computed))
    c2.metric("Total Actual",   fmt(total_actual))
    c3.metric("Total Variance", fmt(total_delta),
              delta="within tolerance" if abs(total_delta) < 100 else "investigate")
    c4.metric("Months Flagged ⚠️", f"{flagged} / {len(df)}")

    # Chart — computed vs actual over time
    if "Period" in df.columns and len(df) > 1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Actual ($)", x=df["Period"], y=df["Actual ($)"],
            marker_color="#3b82f6", opacity=0.85))
        fig.add_trace(go.Scatter(
            name="Computed ($)", x=df["Period"], y=df["Computed ($)"],
            mode="lines+markers", line=dict(color="#ef4444", width=2),
            marker=dict(size=7)))
        fig.add_trace(go.Bar(
            name="Variance ($)", x=df["Period"], y=df["Variance ($)"],
            marker_color=["#f97316" if abs(v) > 50 else "#86efac" for v in df["Variance ($)"]],
            opacity=0.7, yaxis="y2"))
        fig.update_layout(
            title="Bill History: Computed vs Actual",
            yaxis=dict(title="$ Amount", tickprefix="$"),
            yaxis2=dict(title="Variance ($)", overlaying="y", side="right",
                        tickprefix="$", zeroline=True),
            barmode="overlay", height=380, legend=dict(orientation="h", y=1.12),
            margin=dict(t=60, b=40))
        st.plotly_chart(fig, use_container_width=True)

    # Styled table
    def color_variance(val):
        if isinstance(val, float):
            if abs(val) < 1:
                return "color: green"
            elif abs(val) < 50:
                return "color: orange"
            else:
                return "color: red; font-weight: bold"
        return ""

    display_df = df.copy()
    for col in ["Computed ($)", "Actual ($)", "Variance ($)"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
    if "Variance (%)" in display_df.columns:
        display_df["Variance (%)"] = display_df["Variance (%)"].apply(
            lambda x: f"{x:+.2f}%" if pd.notnull(x) else "")
    if "Total kWh" in display_df.columns:
        display_df["Total kWh"] = display_df["Total kWh"].apply(
            lambda x: f"{x:,.0f}" if pd.notnull(x) else "")

    st.dataframe(display_df, use_container_width=True, height=min(400, 60 + 35 * len(df)))

    # Download results
    csv_out = df.to_csv(index=False).encode()
    st.download_button("⬇️ Download results as CSV", csv_out,
                       file_name="bill_audit_results.csv", mime="text/csv")
