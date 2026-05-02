"""
Utility Rate Comparison & Bill Audit Tool
Menasha Electric & Water Utilities (WI) | Pacific Gas & Electric (CA)
Run locally:  streamlit run app.py
Deploy:       push to GitHub → share.streamlit.io → main file = app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Utility Rate & Bill Audit Tool",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main .block-container { padding-top: 1.2rem; }
  div[data-testid="metric-container"] {
    background:#f8f9fa; border-radius:8px;
    padding:.5rem .8rem; border:1px solid #e5e7eb;
  }
  .stRadio > div { gap: .5rem; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Rate & Bill Audit Tool")
    st.divider()
    utility = st.radio(
        "Select Utility",
        ["Menasha Electric & Water (WI)", "Pacific Gas & Electric (CA)"],
        index=0,
    )
    st.divider()
    if "Menasha" in utility:
        st.caption("**Menasha Electric & Water Utilities**")
        st.caption("Amendment No. 87 · Effective June 1, 2025")
        st.caption("PSCW Docket 3560-ER-108")
        st.caption("Schedules: Rg-1/2, Gs-1/2, Cp-1 through Cp-4")
    else:
        st.caption("**Pacific Gas & Electric Company**")
        st.caption("Advice 7846-E · Effective March 1, 2026")
        st.caption("CPUC Authorized · Bundled & CCA accounts")
        st.caption("Schedules: B-1, B-10/B-10S, B-19/B-19S, B-20/B-20S")
    st.divider()
    st.caption("**Modes available**")
    if "Menasha" in utility:
        st.caption("📊 Single Bill — comparison calculator")
        st.caption("📂 Historical Series — upload CSV/Excel, re-engineer & audit")
    else:
        st.caption("📊 Rate Comparison Calculator")
        st.caption("🔍 Single Bill Re-engineering / Audit")
        st.caption("📂 Historical Series — upload CSV/Excel, re-engineer & audit")
    st.divider()
    st.caption("⚠️ For informational and comparison purposes only. "
               "Always verify with current utility tariff filings.")

# ── Route ─────────────────────────────────────────────────────────────────────
if "Menasha" in utility:
    from ui_menasha import render_menasha
    render_menasha()
else:
    from ui_pge import render_pge
    render_pge()
