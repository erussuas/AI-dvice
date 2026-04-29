# ⚡ Utility Rate Comparison Tool

A Streamlit web app for comparing commercial and industrial electric rate schedules across multiple utilities.

## Supported Utilities

| Utility | State | Schedules | Effective Date |
|---------|-------|-----------|----------------|
| **Menasha Electric & Water Utilities** | Wisconsin | Rg-1, Rg-2, Gs-1, Gs-2, Cp-1, Cp-2, Cp-3, Cp-4 | June 1, 2025 (Amendment 87) |
| **Pacific Gas & Electric (PG&E)** | California | B-1, B-6, B-10, B-19, B-20 | March 1, 2026 (Advice 7846-E) |

## Features

- **Side-by-side bill comparison** for any two eligible rate schedules
- **Full billing engine** including customer charges, TOU energy, demand charges, distribution demand, energy limiters, PCAC/PCAC2 adjustments, CTC-1 rider, and sales tax
- **Cp-4 PCAC2 support** with both direct rate entry (from bill) and formula mode (from wholesale cost inputs)
- **Load factor calculation** for Cp-4 eligibility verification (≥85% required)
- **Bill reconciliation** against actual bills
- **Power factor adjustment** for PG&E schedules
- **Annualized savings** comparison

## Project Structure

```
utility_rate_app/
├── app.py               # Main Streamlit entry point + utility selector
├── billing_menasha.py   # Menasha billing engine
├── billing_pge.py       # PG&E billing engine
├── ui_menasha.py        # Menasha UI module
├── ui_pge.py            # PG&E UI module
├── ui_shared.py         # Shared rendering components
├── rates_menasha.json   # Menasha rate data (reference)
├── rates_pge.json       # PG&E rate data (reference)
└── requirements.txt
```

## Running Locally

```bash
pip install streamlit
streamlit run app.py
```

## Deploying to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Deploy

## Data Sources

- **Menasha**: PSCW Docket 3560-ER-108, Amendment No. 87, effective June 1, 2025
- **PG&E**: CPUC Advice Letter 7846-E, effective March 1, 2026. Tariff book at [pge.com/tariffs](https://www.pge.com/tariffs)

## Disclaimer

This tool is for informational and comparison purposes only. Estimated bills may differ from actual utility bills due to rounding, reactive charges, interim rate adjustments, and other factors. Always verify rates with current utility tariff filings before making business decisions.

## Adding More Utilities

To add a new utility:
1. Create `billing_<utility>.py` with rate constants and a `calc_<utility>_bill()` function
2. Create `ui_<utility>.py` with a `render_<utility>()` function
3. Add the utility to the sidebar radio selector in `app.py`
4. Add a corresponding `rates_<utility>.json` for reference

## License

MIT
