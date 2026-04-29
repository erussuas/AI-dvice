"""
Utility Rate Comparison Tool
Supports: Menasha Electric & Water Utilities (WI) | Pacific Gas & Electric (CA)
Built for Streamlit — deploy to streamlit.io or run locally with: streamlit run app.py
"""

import streamlit as st
import json
from pathlib import Path
from billing_menasha import calc_menasha_bill, MENASHA_RATES
from billing_pge import calc_pge_bill, PGE_RATES

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Utility Rate Comparison Tool",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; }
    .utility-header { font-size: 1.1rem; font-weight: 600; margin-bottom: 0; }
    .bill-card { background: #f8f9fa; border-radius: 8px; padding: 1.2rem; border: 1px solid #dee2e6; }
    .bill-card-winner { background: #f0fdf4; border-radius: 8px; padding: 1.2rem; border: 1.5px solid #16a34a; }
    .bill-total { font-size: 2rem; font-weight: 700; }
    .bill-total-winner { font-size: 2rem; font-weight: 700; color: #16a34a; }
    .line-item { display: flex; justify-content: space-between; font-size: 0.85rem; padding: 2px 0; border-bottom: 1px solid #f0f0f0; }
    .section-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600; margin: 0.5rem 0 0.2rem; }
    .winner-badge { background: #dcfce7; color: #16a34a; font-size: 0.75rem; padding: 2px 10px; border-radius: 999px; font-weight: 600; }
    .note-box { background: #fefce8; border: 1px solid #fde68a; border-radius: 6px; padding: 0.6rem 0.9rem; font-size: 0.82rem; color: #92400e; margin-top: 0.5rem; }
    .info-box { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 0.6rem 0.9rem; font-size: 0.82rem; color: #1e40af; margin-bottom: 0.5rem; }
    .reconcile-ok  { background: #f0fdf4; border: 1px solid #86efac; border-radius: 6px; padding: 0.5rem 0.8rem; font-size: 0.82rem; color: #166534; margin-top: 0.5rem; }
    .reconcile-warn { background: #fefce8; border: 1px solid #fde68a; border-radius: 6px; padding: 0.5rem 0.8rem; font-size: 0.82rem; color: #92400e; margin-top: 0.5rem; }
    div[data-testid="metric-container"] { background: #f8f9fa; border-radius: 8px; padding: 0.6rem; border: 1px solid #e5e7eb; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar — Utility selector ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/48/lightning-bolt.png", width=40)
    st.title("Rate Comparison Tool")
    st.divider()

    utility = st.radio(
        "Select Utility",
        options=["Menasha Electric & Water (WI)", "Pacific Gas & Electric (CA)"],
        index=0,
    )

    st.divider()
    st.caption("**Data sources**")
    if "Menasha" in utility:
        st.caption("Menasha Utilities — Amendment No. 87, effective June 1, 2025. Docket 3560-ER-108.")
    else:
        st.caption("PG&E — Advice 7846-E, effective March 1, 2026. CPUC authorized.")
    st.caption("⚠️ For informational purposes only. Always verify with current tariff filings.")

# ── Route to the correct UI ────────────────────────────────────────────────
if "Menasha" in utility:
    from ui_menasha import render_menasha
    render_menasha()
else:
    from ui_pge import render_pge
    render_pge()
