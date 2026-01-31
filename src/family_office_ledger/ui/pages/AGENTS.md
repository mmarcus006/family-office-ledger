<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# pages

## Purpose
NiceGUI page layouts for the alternative frontend. Each file represents a full page view that composes components.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Page exports |
| `accounts.py` | Account management page (4.9KB) |
| `dashboard.py` | Main dashboard with net worth and KPIs (6KB) |
| `entities.py` | Entity management page (3.3KB) |
| `reports.py` | Report generation page (5.2KB) |
| `transactions.py` | Transaction entry and list page (11KB) |

## For AI Agents

### Working In This Directory
- **NiceGUI frontend is experimental** - Streamlit is production
- Pages compose components from `../components/`
- Follow NiceGUI routing patterns

### Page Pattern
```python
from nicegui import ui
from family_office_ledger.ui.components import nav, forms

def show() -> None:
    """Page entry point."""
    nav.sidebar()
    with ui.column():
        # ... page content
```

### Testing Requirements
- Tests in `tests/ui/test_pages.py`
- Currently minimal - expand with NiceGUI development

## Dependencies

### Internal
- `../components/` - Reusable UI components
- `../api_client.py` - API communication

### External
- `nicegui` - UI framework

<!-- MANUAL: -->
