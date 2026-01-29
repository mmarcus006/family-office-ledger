# STREAMLIT APP

## OVERVIEW
Streamlit frontend with 12 pages, Quicken-style professional theme, covering all API endpoints.

## STRUCTURE
```
streamlit_app/
├── app.py              # entry point, session state init
├── api_client.py       # synchronous HTTP client (681 lines, 40+ functions)
├── styles.py           # CSS theme, helpers (format_currency, section_header, get_plotly_layout)
├── .streamlit/
│   └── config.toml     # Quicken-style theme colors
└── pages/
    ├── 1_Dashboard.py      # net worth, KPIs, charts
    ├── 2_Entities.py       # entity CRUD
    ├── 3_Accounts.py       # account CRUD
    ├── 4_Transactions.py   # journal entry posting
    ├── 5_Reports.py        # net worth, balance sheet, PnL
    ├── 6_Reconciliation.py # bank statement matching
    ├── 7_Transfers.py      # inter-account transfer matching
    ├── 8_Audit.py          # audit trail viewer
    ├── 9_Currency.py       # exchange rate management
    ├── 10_Portfolio.py     # allocation, concentration, performance
    ├── 11_QSBS.py          # qualified small business stock tracking
    └── 12_Tax.py           # Form 8949, Schedule D generation
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Entry point | app.py | `main()`, `init_session_state()` |
| API calls | api_client.py | 40+ functions covering all API endpoints |
| Styling | styles.py | `apply_custom_css()`, `COLORS`, `CHART_COLORS`, `format_currency()` |
| Theme config | .streamlit/config.toml | primaryColor, backgroundColor, etc. |

## CONVENTIONS
- `from __future__ import annotations` in all files
- `apply_custom_css()` called at page start
- `@st.cache_data(ttl=60)` for API calls with caching
- `section_header(title)` for consistent section styling
- `format_currency(value)` for money display
- `get_plotly_layout(title)` for chart styling

## API CLIENT FUNCTIONS (api_client.py)
| Category | Functions |
|----------|-----------|
| Core | list_entities, create_entity, list_accounts, create_account, list_transactions, post_transaction |
| Reports | net_worth_report, balance_sheet, dashboard_summary, transaction_summary_by_type |
| Reconciliation | create_reconciliation_session, list_reconciliation_matches, confirm/reject/skip_match, close_session |
| Transfers | create_transfer_session, list_transfer_matches, confirm/reject_transfer_match |
| Audit | list_audit_entries, get_audit_entry, get_audit_summary |
| Currency | add_exchange_rate, list_exchange_rates, convert_currency, delete_exchange_rate |
| Portfolio | get_portfolio_summary, get_asset_allocation, get_concentration_report, get_performance_report |
| QSBS | list_qsbs_securities, get_qsbs_summary, mark/remove_security_qsbs_eligible |
| Tax | get_tax_summary, get_form_8949_csv, get_schedule_d, generate_tax_documents |

## THEME (styles.py)
```python
COLORS = {
    "primary": "#22324F",    # Deep blue
    "accent": "#471CFF",     # Purple
    "positive": "#21c354",   # Green (gains)
    "negative": "#ff2b2b",   # Red (losses)
    "warning": "#ff8700",    # Orange
}
```

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- Launched via `fol ui` CLI command
- Requires API server running on http://localhost:8000
- Uses httpx for synchronous HTTP requests
- Plotly for charts with consistent styling via `get_plotly_layout()`
- Page numbering (1_, 2_, etc.) controls sidebar order
