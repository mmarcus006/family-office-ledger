<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# pages

## Purpose
Streamlit multi-page application pages. Each file represents a page in the Streamlit sidebar navigation. Files are numbered to control display order.

## Key Files

| File | Description |
|------|-------------|
| `1_Dashboard.py` | Net worth overview, KPIs, charts (11KB) |
| `2_Entities.py` | Entity management - LLCs, trusts, individuals (4KB) |
| `3_Accounts.py` | Account management by entity (4.7KB) |
| `4_Transactions.py` | Journal entry recording (10KB) |
| `5_Reports.py` | Financial report generation (13KB) |
| `6_Reconciliation.py` | Bank statement matching workflow (11KB) |
| `7_Transfers.py` | Inter-account transfer matching (12KB) |
| `8_Audit.py` | Audit trail viewer (7.3KB) |
| `9_Currency.py` | Exchange rate management (11KB) |
| `10_Portfolio.py` | Asset allocation and performance (14KB) |
| `11_QSBS.py` | Qualified Small Business Stock tracking (13KB) |
| `12_Tax.py` | Tax document generation - Form 8949, Schedule D (17KB) |
| `13_Households.py` | Household grouping management (11KB) |
| `14_Ownership.py` | Entity ownership structure visualization (11KB) |

## For AI Agents

### Working In This Directory
- **File naming convention**: `N_PageName.py` where N is display order
- Each page is a standalone Streamlit script
- Pages communicate with API via `api_client.py` in parent directory
- Use design system from `family_office_ledger.design_system`

### Page Structure Pattern
```python
import streamlit as st
from family_office_ledger.streamlit_app.api_client import get_api_client
from family_office_ledger.streamlit_app.styles import apply_page_config

apply_page_config()
st.title("Page Title")

client = get_api_client()
# ... page content
```

### Testing Requirements
- Page tests in `tests/streamlit_app/test_streamlit_pages.py`
- Mock API client responses
- Test error handling for API failures

### Common Patterns
- Use `st.columns()` for layouts
- Use `st.tabs()` for sub-sections
- Use `st.form()` for data entry
- Display monetary values with `format_currency()`
- Color code values with `get_value_color()`

## Dependencies

### Internal
- `../api_client.py` - API communication
- `../styles.py` - Streamlit styling helpers
- `family_office_ledger.design_system` - Design tokens and formatters

### External
- `streamlit` - UI framework
- `plotly` - Charts and visualizations
- `pandas` - Data manipulation

<!-- MANUAL: -->
