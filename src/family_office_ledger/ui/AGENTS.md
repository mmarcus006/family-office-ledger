# UI LAYER

## OVERVIEW
NiceGUI frontend with 5 pages, reusable components, and global state management.

## STRUCTURE
```
ui/
├── main.py           # entry point, routing (@ui.page decorators)
├── state.py          # AppState dataclass (global singleton)
├── api_client.py     # LedgerAPIClient (httpx async)
├── constants.py      # Tailwind CSS class constants
├── components/       # reusable UI components
│   ├── nav.py        # header, sidebar
│   ├── forms.py      # money_input, select_field, date_field
│   ├── tables.py     # data_table wrapper
│   ├── modals.py     # confirm_dialog, form_dialog
│   └── charts.py     # plotly_figure wrapper
└── pages/            # page components
    ├── dashboard.py  # net worth, recent transactions
    ├── entities.py   # entity management
    ├── accounts.py   # account management
    ├── transactions.py # journal entry form
    └── reports.py    # net worth, balance sheet
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Routing | main.py | `@ui.page()` decorators |
| State | state.py | AppState dataclass, global `state` singleton |
| API calls | api_client.py | LedgerAPIClient with async methods |
| Styling | constants.py | Tailwind CSS class constants |
| Navigation | components/nav.py | header, sidebar components |
| Forms | components/forms.py | money_input, select_field, date_field |
| Tables | components/tables.py | data_table with pagination |

## CONVENTIONS
- Functional components (functions returning None, render in-place)
- Composition via context managers (`with ui.column():`)
- Manual reactivity: `.update()` calls after state changes
- Async event handlers for API calls
- `ui.timer(0.05, callback, once=True)` for initial data loads

## STATE MANAGEMENT
```python
@dataclass
class AppState:
    selected_entity_id: UUID | None
    selected_account_id: UUID | None
    entities: list[dict]    # cached
    accounts: list[dict]    # cached
    sidebar_collapsed: bool
```

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- Framework: NiceGUI (Python, builds on Vue.js/Quasar)
- Optional dependency: `family-office-ledger[frontend]`
- API client uses httpx AsyncClient with ASGITransport for testing
- Shell layout applied to all pages via `shell()` function
