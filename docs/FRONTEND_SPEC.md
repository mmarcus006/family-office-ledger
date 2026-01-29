# Frontend Specification: Atlas Family Office Ledger

**Version**: 1.0  
**Date**: 2026-01-28  
**Status**: Draft

---

## 1. Overview

A desktop-first web interface for managing multi-entity double-entry accounting. Built with NiceGUI for rapid Python development, consuming the existing FastAPI backend.

### Design Principles

1. **Data density over decoration** — Financial software shows numbers, not marketing fluff
2. **Keyboard-first** — Tab through forms, Enter to submit, Escape to cancel
3. **Immediate feedback** — Validation errors show inline, not in modals
4. **Predictable layout** — Same navigation, same patterns, every page

### Non-Goals

- Mobile optimization (desktop-first, responsive is a bonus)
- Offline support
- Real-time collaboration
- Fancy animations

---

## 2. Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Framework | NiceGUI 2.x | Python-native, FastAPI integration, WebSocket updates |
| Styling | Tailwind CSS (via Quasar) | Utility classes, consistent spacing |
| Charts | Plotly (via NiceGUI) | Interactive, good for financial data |
| Tables | AG Grid or NiceGUI tables | Sorting, filtering, pagination |
| HTTP Client | httpx | Async requests to backend API |
| Testing | pytest + pytest-asyncio + NiceGUI's testing utilities | TDD approach |
| Dev Server | uvicorn | Hot reload during development |

### Dependencies (additions to pyproject.toml)

```toml
[project.optional-dependencies]
frontend = [
    "nicegui>=2.0",
    "httpx>=0.27",
    "plotly>=5.18",
]

[project.optional-dependencies]
frontend-dev = [
    "pytest-asyncio>=0.23",
]
```

---

## 3. Architecture

```
src/family_office_ledger/
├── ui/                          # Frontend package
│   ├── __init__.py
│   ├── main.py                  # App entry point, routing
│   ├── state.py                 # Global UI state management
│   ├── api_client.py            # HTTP client wrapper for backend
│   ├── components/              # Reusable UI components
│   │   ├── __init__.py
│   │   ├── nav.py               # Navigation sidebar
│   │   ├── tables.py            # Data table wrappers
│   │   ├── forms.py             # Form field helpers
│   │   ├── modals.py            # Dialog/modal patterns
│   │   └── charts.py            # Chart wrappers
│   └── pages/                   # Page-level components
│       ├── __init__.py
│       ├── dashboard.py         # Home/overview
│       ├── entities.py          # Entity management
│       ├── accounts.py          # Account management
│       ├── transactions.py      # Transaction entry + history
│       └── reports.py           # Net worth, balance sheet
tests/
└── ui/                          # Frontend tests
    ├── conftest.py              # Fixtures, test client setup
    ├── test_api_client.py       # API client unit tests
    ├── test_pages.py            # Page rendering tests
    └── test_workflows.py        # End-to-end workflow tests
```

### State Management

NiceGUI uses a reactive model. State is stored in a singleton class:

```python
# ui/state.py
from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class AppState:
    """Global application state."""
    
    # Current selections
    selected_entity_id: Optional[uuid.UUID] = None
    selected_account_id: Optional[uuid.UUID] = None
    
    # Cached data (refreshed on navigation)
    entities: list[dict] = field(default_factory=list)
    accounts: list[dict] = field(default_factory=list)
    
    # UI state
    sidebar_collapsed: bool = False
    
    def clear_selections(self):
        self.selected_entity_id = None
        self.selected_account_id = None

state = AppState()
```

### API Client

Thin wrapper around httpx for backend communication:

```python
# ui/api_client.py
import httpx
from typing import Optional
from datetime import date

class LedgerAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    
    # Entities
    async def list_entities(self) -> list[dict]:
        r = await self._client.get("/entities")
        r.raise_for_status()
        return r.json()
    
    async def create_entity(self, name: str, entity_type: str, fiscal_year_end: Optional[date] = None) -> dict:
        payload = {"name": name, "entity_type": entity_type}
        if fiscal_year_end:
            payload["fiscal_year_end"] = fiscal_year_end.isoformat()
        r = await self._client.post("/entities", json=payload)
        r.raise_for_status()
        return r.json()
    
    # Accounts
    async def list_accounts(self, entity_id: Optional[str] = None) -> list[dict]:
        params = {}
        if entity_id:
            params["entity_id"] = entity_id
        r = await self._client.get("/accounts", params=params)
        r.raise_for_status()
        return r.json()
    
    async def create_account(self, name: str, entity_id: str, account_type: str, 
                            sub_type: str = "other", currency: str = "USD") -> dict:
        r = await self._client.post("/accounts", json={
            "name": name,
            "entity_id": entity_id,
            "account_type": account_type,
            "sub_type": sub_type,
            "currency": currency,
        })
        r.raise_for_status()
        return r.json()
    
    # Transactions
    async def post_transaction(self, transaction_date: date, entries: list[dict], 
                               memo: str = "", reference: str = "") -> dict:
        r = await self._client.post("/transactions", json={
            "transaction_date": transaction_date.isoformat(),
            "entries": entries,
            "memo": memo,
            "reference": reference,
        })
        r.raise_for_status()
        return r.json()
    
    async def list_transactions(self, account_id: Optional[str] = None,
                                start_date: Optional[date] = None,
                                end_date: Optional[date] = None) -> list[dict]:
        params = {}
        if account_id:
            params["account_id"] = account_id
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        r = await self._client.get("/transactions", params=params)
        r.raise_for_status()
        return r.json()
    
    # Reports
    async def net_worth_report(self, as_of_date: date, entity_ids: Optional[list[str]] = None) -> dict:
        params = {"as_of_date": as_of_date.isoformat()}
        if entity_ids:
            params["entity_ids"] = entity_ids
        r = await self._client.get("/reports/net-worth", params=params)
        r.raise_for_status()
        return r.json()
    
    async def balance_sheet(self, entity_id: str, as_of_date: date) -> dict:
        r = await self._client.get(f"/reports/balance-sheet/{entity_id}", 
                                   params={"as_of_date": as_of_date.isoformat()})
        r.raise_for_status()
        return r.json()

# Singleton instance
api = LedgerAPIClient()
```

---

## 4. Pages & Layouts

### 4.1 Shell Layout

Every page uses a consistent shell:

```
┌─────────────────────────────────────────────────────────────────┐
│  Atlas Ledger                                    [Entity: ▼]   │
├────────────┬────────────────────────────────────────────────────┤
│            │                                                    │
│  Dashboard │   Page Content                                     │
│  Entities  │                                                    │
│  Accounts  │                                                    │
│  Txns      │                                                    │
│  Reports   │                                                    │
│            │                                                    │
│            │                                                    │
│            │                                                    │
└────────────┴────────────────────────────────────────────────────┘
```

- **Header**: App name, global entity selector dropdown
- **Sidebar**: Navigation links, collapsible
- **Main**: Page-specific content

### 4.2 Dashboard (`/`)

Overview of the current entity or all entities.

```
┌─────────────────────────────────────────────────────────────────┐
│  Dashboard                                       as of: [date] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Net Worth      │  │  Total Assets   │  │  Liabilities    │ │
│  │  $1,234,567     │  │  $1,500,000     │  │  $265,433       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  Recent Transactions                              [View All →] │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Date       │ Memo              │ Amount      │ Account     ││
│  │ 2026-01-28 │ Payroll           │ -$5,000.00  │ Checking    ││
│  │ 2026-01-27 │ Client payment    │ +$12,500.00 │ Checking    ││
│  │ 2026-01-25 │ Office rent       │ -$2,000.00  │ Checking    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Account Balances                                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Account          │ Type     │ Balance                       ││
│  │ Operating Check  │ Asset    │ $45,230.00                    ││
│  │ Savings          │ Asset    │ $120,000.00                   ││
│  │ Brokerage        │ Asset    │ $890,000.00                   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Components:**
- Summary cards (net worth, assets, liabilities)
- Recent transactions table (last 10, link to full list)
- Account balances table (grouped by type)

### 4.3 Entities (`/entities`)

List and manage entities.

```
┌─────────────────────────────────────────────────────────────────┐
│  Entities                                      [+ New Entity]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Name              │ Type        │ Fiscal YE  │ Status      ││
│  │ Miller Family LLC │ LLC         │ Dec 31     │ Active      ││
│  │ Miller Trust      │ Trust       │ Dec 31     │ Active      ││
│  │ John Miller       │ Individual  │ Dec 31     │ Active      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**New Entity Modal:**
```
┌─────────────────────────────────────┐
│  New Entity                    [×]  │
├─────────────────────────────────────┤
│                                     │
│  Name:  [________________________]  │
│                                     │
│  Type:  [LLC              ▼]        │
│         • LLC                       │
│         • Trust                     │
│         • Partnership               │
│         • Individual                │
│         • Holding Company           │
│                                     │
│  Fiscal Year End: [Dec 31    ▼]     │
│                                     │
│         [Cancel]  [Create Entity]   │
└─────────────────────────────────────┘
```

### 4.4 Accounts (`/accounts`)

List and manage accounts. Filtered by selected entity.

```
┌─────────────────────────────────────────────────────────────────┐
│  Accounts                                      [+ New Account] │
│  Entity: [Miller Family LLC ▼]                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Assets                                                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Name              │ Sub-Type   │ Currency │ Balance        ││
│  │ Operating Check   │ Checking   │ USD      │ $45,230.00     ││
│  │ Savings           │ Savings    │ USD      │ $120,000.00    ││
│  │ Schwab Brokerage  │ Brokerage  │ USD      │ $890,000.00    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Liabilities                                                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Name              │ Sub-Type   │ Currency │ Balance        ││
│  │ Amex Card         │ Credit Card│ USD      │ $3,200.00      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Equity                                                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Name              │ Sub-Type   │ Currency │ Balance        ││
│  │ Owner's Equity    │ Other      │ USD      │ $1,052,030.00  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**New Account Modal:**
```
┌─────────────────────────────────────┐
│  New Account                   [×]  │
├─────────────────────────────────────┤
│                                     │
│  Entity: Miller Family LLC          │
│                                     │
│  Name:  [________________________]  │
│                                     │
│  Type:  [Asset            ▼]        │
│                                     │
│  Sub-Type: [Checking       ▼]       │
│                                     │
│  Currency: [USD            ▼]       │
│                                     │
│         [Cancel]  [Create Account]  │
└─────────────────────────────────────┘
```

### 4.5 Transactions (`/transactions`)

Two tabs: **Entry** and **History**.

#### Entry Tab

```
┌─────────────────────────────────────────────────────────────────┐
│  Transactions          [Entry]  [History]                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Date: [2026-01-28]    Reference: [______________]             │
│  Memo: [________________________________________________]      │
│                                                                 │
│  Journal Entries                                                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Account             │ Debit       │ Credit      │ Memo     ││
│  │ [Operating Check ▼] │ [_________] │ [_________] │ [______] ││
│  │ [Expense: Rent   ▼] │ [_________] │ [_________] │ [______] ││
│  │                                            [+ Add Row]      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌──────────────────────────────────────────┐                  │
│  │ Total Debits:   $2,000.00                │                  │
│  │ Total Credits:  $2,000.00                │                  │
│  │ Difference:     $0.00  ✓ Balanced        │                  │
│  └──────────────────────────────────────────┘                  │
│                                                                 │
│                                    [Clear]  [Post Transaction] │
└─────────────────────────────────────────────────────────────────┘
```

**Validation:**
- Real-time balance check (debits must equal credits)
- Minimum 2 entries required
- Account selection required for each row
- At least one debit and one credit must be non-zero

**Error States:**
- Unbalanced: "Difference: $500.00 — Transaction must balance"
- Missing account: Red border on account dropdown
- Invalid amount: Red border on input field

#### History Tab

```
┌─────────────────────────────────────────────────────────────────┐
│  Transactions          [Entry]  [History]                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Filters:                                                       │
│  Account: [All accounts     ▼]  From: [________]  To: [______] │
│                                                    [Apply]      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Date       │ Reference │ Memo           │ Entries          ││
│  │ 2026-01-28 │ INV-001   │ Client payment │ 2 entries [▼]    ││
│  │            │           │                │ Checking +$12,500││
│  │            │           │                │ Revenue  -$12,500││
│  │ 2026-01-27 │ RENT-01   │ Office rent    │ 2 entries [▼]    ││
│  │            │           │                │ Checking -$2,000 ││
│  │            │           │                │ Expense  +$2,000 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Showing 1-25 of 142                        [< Prev] [Next >]  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.6 Reports (`/reports`)

Report selection and display.

```
┌─────────────────────────────────────────────────────────────────┐
│  Reports                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Report: [Net Worth        ▼]   As of: [2026-01-28]            │
│  Entities: [☑ Miller LLC] [☑ Miller Trust] [☐ John Miller]    │
│                                                   [Generate]    │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  NET WORTH REPORT                                               │
│  As of January 28, 2026                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Entity            │ Account          │ Type    │ Balance   ││
│  │ Miller Family LLC │ Operating Check  │ Asset   │ $45,230   ││
│  │ Miller Family LLC │ Savings          │ Asset   │ $120,000  ││
│  │ Miller Family LLC │ Schwab Brokerage │ Asset   │ $890,000  ││
│  │ Miller Family LLC │ Amex Card        │ Liab.   │ ($3,200)  ││
│  │ Miller Trust      │ Trust Checking   │ Asset   │ $50,000   ││
│  │ Miller Trust      │ Trust Brokerage  │ Asset   │ $500,000  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌──────────────────────────────────────────┐                  │
│  │ Total Assets:       $1,605,230.00        │                  │
│  │ Total Liabilities:  $3,200.00            │                  │
│  │ ─────────────────────────────────────    │                  │
│  │ NET WORTH:          $1,602,030.00        │                  │
│  └──────────────────────────────────────────┘                  │
│                                                                 │
│                                              [Export CSV]       │
└─────────────────────────────────────────────────────────────────┘
```

**Available Reports:**
- Net Worth (multi-entity)
- Balance Sheet (single entity)

---

## 5. Component Specifications

### 5.1 Navigation Sidebar

```python
# ui/components/nav.py
from nicegui import ui
from ..state import state

def sidebar():
    with ui.column().classes('w-48 bg-gray-50 h-screen p-4'):
        ui.link('Dashboard', '/').classes('nav-link')
        ui.link('Entities', '/entities').classes('nav-link')
        ui.link('Accounts', '/accounts').classes('nav-link')
        ui.link('Transactions', '/transactions').classes('nav-link')
        ui.link('Reports', '/reports').classes('nav-link')
```

### 5.2 Data Tables

Wrapper for consistent table styling:

```python
# ui/components/tables.py
from nicegui import ui
from typing import Callable

def data_table(
    columns: list[dict],  # [{"name": "date", "label": "Date", "field": "date"}, ...]
    rows: list[dict],
    on_row_click: Callable[[dict], None] | None = None,
    pagination: int = 25,
):
    table = ui.table(
        columns=columns,
        rows=rows,
        row_key='id',
        pagination=pagination,
    ).classes('w-full')
    
    if on_row_click:
        table.on('rowClick', lambda e: on_row_click(e.args[1]))
    
    return table
```

### 5.3 Forms

Field helpers with validation:

```python
# ui/components/forms.py
from nicegui import ui
from decimal import Decimal
from typing import Callable

def money_input(label: str, on_change: Callable[[Decimal], None] | None = None):
    """Currency input with formatting."""
    inp = ui.number(label, format='%.2f', prefix='$')
    if on_change:
        inp.on('change', lambda e: on_change(Decimal(str(e.value or 0))))
    return inp

def select_field(label: str, options: list[dict], on_change: Callable | None = None):
    """Dropdown with label/value pairs."""
    sel = ui.select(
        options={o['value']: o['label'] for o in options},
        label=label,
    )
    if on_change:
        sel.on('change', on_change)
    return sel

def date_field(label: str, on_change: Callable | None = None):
    """Date picker."""
    with ui.input(label) as inp:
        with inp.add_slot('append'):
            ui.icon('edit_calendar').on('click', lambda: menu.open()).classes('cursor-pointer')
        with ui.menu() as menu:
            ui.date(on_change=lambda e: (inp.set_value(e.value), menu.close()))
    return inp
```

### 5.4 Modals

```python
# ui/components/modals.py
from nicegui import ui
from typing import Callable

def confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable,
    on_cancel: Callable | None = None,
):
    with ui.dialog() as dialog, ui.card():
        ui.label(title).classes('text-lg font-bold')
        ui.label(message)
        with ui.row():
            ui.button('Cancel', on_click=lambda: (on_cancel and on_cancel(), dialog.close()))
            ui.button('Confirm', on_click=lambda: (on_confirm(), dialog.close())).classes('bg-blue-500')
    return dialog

def form_dialog(title: str):
    """Base dialog for form modals. Returns (dialog, card) for content injection."""
    dialog = ui.dialog()
    with dialog:
        card = ui.card().classes('w-96')
        with card:
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(title).classes('text-lg font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
    return dialog, card
```

---

## 6. Routing

NiceGUI page routing:

```python
# ui/main.py
from nicegui import ui, app
from .components.nav import sidebar, header
from .pages import dashboard, entities, accounts, transactions, reports
from .api_client import api

def create_ui():
    """Initialize the NiceGUI application."""
    
    @ui.page('/')
    async def index():
        header()
        with ui.row().classes('w-full h-screen'):
            sidebar()
            with ui.column().classes('flex-1 p-6'):
                await dashboard.render()
    
    @ui.page('/entities')
    async def entities_page():
        header()
        with ui.row().classes('w-full h-screen'):
            sidebar()
            with ui.column().classes('flex-1 p-6'):
                await entities.render()
    
    @ui.page('/accounts')
    async def accounts_page():
        header()
        with ui.row().classes('w-full h-screen'):
            sidebar()
            with ui.column().classes('flex-1 p-6'):
                await accounts.render()
    
    @ui.page('/transactions')
    async def transactions_page():
        header()
        with ui.row().classes('w-full h-screen'):
            sidebar()
            with ui.column().classes('flex-1 p-6'):
                await transactions.render()
    
    @ui.page('/reports')
    async def reports_page():
        header()
        with ui.row().classes('w-full h-screen'):
            sidebar()
            with ui.column().classes('flex-1 p-6'):
                await reports.render()

def run():
    """Run the frontend server."""
    create_ui()
    ui.run(title='Atlas Ledger', port=3000, reload=True)
```

---

## 7. Testing Strategy

### Test Structure

```
tests/ui/
├── conftest.py              # Shared fixtures
├── test_api_client.py       # Unit tests for API client
├── test_components.py       # Component rendering tests
├── test_pages.py            # Page-level tests
└── test_workflows.py        # End-to-end workflow tests
```

### Fixtures

```python
# tests/ui/conftest.py
import pytest
from nicegui.testing import User
from httpx import ASGITransport, AsyncClient
from family_office_ledger.api.app import create_app
from family_office_ledger.ui.api_client import LedgerAPIClient

@pytest.fixture
def api_app():
    """Create a test instance of the backend API."""
    return create_app(database_url="sqlite:///:memory:")

@pytest.fixture
async def api_client(api_app):
    """Async HTTP client for testing API calls."""
    async with AsyncClient(
        transport=ASGITransport(app=api_app),
        base_url="http://test"
    ) as client:
        yield LedgerAPIClient.__new__(LedgerAPIClient)
        # Inject test client
        yield client

@pytest.fixture
def user(user: User) -> User:
    """NiceGUI test user for UI interactions."""
    return user
```

### Test Categories

#### 1. API Client Tests

```python
# tests/ui/test_api_client.py
import pytest
from family_office_ledger.ui.api_client import LedgerAPIClient

class TestAPIClient:
    async def test_create_entity(self, api_client):
        result = await api_client.create_entity(
            name="Test LLC",
            entity_type="llc"
        )
        assert result["name"] == "Test LLC"
        assert result["entity_type"] == "llc"
        assert "id" in result
    
    async def test_list_entities_empty(self, api_client):
        result = await api_client.list_entities()
        assert result == []
    
    async def test_create_account_requires_entity(self, api_client):
        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await api_client.create_account(
                name="Checking",
                entity_id="nonexistent-uuid",
                account_type="asset"
            )
    
    async def test_post_balanced_transaction(self, api_client):
        # Setup: create entity and accounts
        entity = await api_client.create_entity("Test", "llc")
        checking = await api_client.create_account("Checking", entity["id"], "asset")
        expense = await api_client.create_account("Rent", entity["id"], "expense")
        
        # Post balanced transaction
        from datetime import date
        result = await api_client.post_transaction(
            transaction_date=date(2026, 1, 28),
            entries=[
                {"account_id": expense["id"], "debit_amount": "1000.00", "credit_amount": "0"},
                {"account_id": checking["id"], "debit_amount": "0", "credit_amount": "1000.00"},
            ],
            memo="Rent payment"
        )
        assert len(result["entries"]) == 2
    
    async def test_post_unbalanced_transaction_fails(self, api_client):
        # Setup
        entity = await api_client.create_entity("Test", "llc")
        checking = await api_client.create_account("Checking", entity["id"], "asset")
        
        with pytest.raises(Exception):  # 422 error
            from datetime import date
            await api_client.post_transaction(
                transaction_date=date(2026, 1, 28),
                entries=[
                    {"account_id": checking["id"], "debit_amount": "1000.00", "credit_amount": "0"},
                ],
                memo="Unbalanced"
            )
```

#### 2. Component Tests

```python
# tests/ui/test_components.py
import pytest
from nicegui.testing import User

class TestDataTable:
    async def test_renders_rows(self, user: User):
        from family_office_ledger.ui.components.tables import data_table
        
        columns = [{"name": "name", "label": "Name", "field": "name"}]
        rows = [{"id": "1", "name": "Test Entity"}]
        
        data_table(columns, rows)
        
        await user.open('/')
        user.find('Test Entity').should_exist()
    
    async def test_row_click_callback(self, user: User):
        clicked = []
        
        from family_office_ledger.ui.components.tables import data_table
        columns = [{"name": "name", "label": "Name", "field": "name"}]
        rows = [{"id": "1", "name": "Clickable"}]
        
        data_table(columns, rows, on_row_click=lambda r: clicked.append(r))
        
        await user.open('/')
        await user.find('Clickable').click()
        assert len(clicked) == 1

class TestMoneyInput:
    async def test_formats_currency(self, user: User):
        from family_office_ledger.ui.components.forms import money_input
        
        money_input("Amount")
        
        await user.open('/')
        inp = user.find('Amount')
        await inp.type('1234.56')
        # Should display with $ prefix and 2 decimal places
```

#### 3. Page Tests

```python
# tests/ui/test_pages.py
import pytest
from nicegui.testing import User

class TestDashboardPage:
    async def test_shows_summary_cards(self, user: User, api_client):
        await user.open('/')
        
        user.find('Net Worth').should_exist()
        user.find('Total Assets').should_exist()
        user.find('Liabilities').should_exist()
    
    async def test_shows_recent_transactions(self, user: User):
        await user.open('/')
        user.find('Recent Transactions').should_exist()

class TestEntitiesPage:
    async def test_lists_entities(self, user: User, api_client):
        # Create test entity via API
        await api_client.create_entity("Test LLC", "llc")
        
        await user.open('/entities')
        user.find('Test LLC').should_exist()
    
    async def test_create_entity_modal(self, user: User):
        await user.open('/entities')
        
        await user.find('New Entity').click()
        user.find('Name').should_exist()
        user.find('Type').should_exist()
        user.find('Create Entity').should_exist()

class TestTransactionsPage:
    async def test_entry_form_validates_balance(self, user: User):
        await user.open('/transactions')
        
        # Add unbalanced entry
        # ... fill form with unbalanced amounts
        
        user.find('Transaction must balance').should_exist()
        user.find('Post Transaction').should_be_disabled()
```

#### 4. Workflow Tests

```python
# tests/ui/test_workflows.py
import pytest
from nicegui.testing import User

class TestEntityCreationWorkflow:
    async def test_create_entity_end_to_end(self, user: User):
        """Complete workflow: create entity, verify in list."""
        await user.open('/entities')
        
        # Click new entity button
        await user.find('New Entity').click()
        
        # Fill form
        await user.find('Name').type('Miller Family LLC')
        await user.find('Type').click()
        await user.find('LLC').click()
        
        # Submit
        await user.find('Create Entity').click()
        
        # Verify appears in list
        user.find('Miller Family LLC').should_exist()

class TestTransactionEntryWorkflow:
    async def test_post_transaction_end_to_end(self, user: User, api_client):
        """Complete workflow: post a balanced transaction."""
        # Setup: create entity and accounts via API
        entity = await api_client.create_entity("Test LLC", "llc")
        checking = await api_client.create_account("Checking", entity["id"], "asset")
        expense = await api_client.create_account("Rent Expense", entity["id"], "expense")
        
        await user.open('/transactions')
        
        # Fill transaction form
        await user.find('Date').type('2026-01-28')
        await user.find('Memo').type('Monthly rent')
        
        # First entry: debit expense
        # ... select account, enter debit amount
        
        # Second entry: credit checking
        # ... select account, enter credit amount
        
        # Verify balance indicator
        user.find('Balanced').should_exist()
        
        # Submit
        await user.find('Post Transaction').click()
        
        # Verify success (redirect to history or confirmation)
        user.find('Transaction posted').should_exist()
```

### Running Tests

```bash
# Run all frontend tests
uv run pytest tests/ui/ -v

# Run with coverage
uv run pytest tests/ui/ --cov=family_office_ledger.ui

# Run specific test file
uv run pytest tests/ui/test_workflows.py -v
```

---

## 8. Implementation Plan

### Phase 1: Foundation (3-4 days)

| Task | Description | Tests |
|------|-------------|-------|
| 1.1 | Set up `ui/` package structure | - |
| 1.2 | Implement `api_client.py` | `test_api_client.py` |
| 1.3 | Implement `state.py` | Unit tests |
| 1.4 | Create base components: `nav.py`, `tables.py`, `forms.py`, `modals.py` | `test_components.py` |
| 1.5 | Set up routing in `main.py` | - |
| 1.6 | Create shell layout (header, sidebar, main area) | Visual verification |

**Deliverable**: Empty but navigable app with working API client.

### Phase 2: Entity & Account Management (2-3 days)

| Task | Description | Tests |
|------|-------------|-------|
| 2.1 | Entities list page | `test_pages.py::TestEntitiesPage` |
| 2.2 | Create entity modal | Workflow test |
| 2.3 | Accounts list page (grouped by type) | `test_pages.py::TestAccountsPage` |
| 2.4 | Create account modal | Workflow test |
| 2.5 | Entity selector in header | - |

**Deliverable**: Full entity and account CRUD.

### Phase 3: Transaction Entry (3-4 days)

| Task | Description | Tests |
|------|-------------|-------|
| 3.1 | Transaction entry form (multi-row) | Unit tests |
| 3.2 | Real-time balance validation | `test_components.py` |
| 3.3 | Add/remove entry rows | - |
| 3.4 | Post transaction with error handling | `test_workflows.py` |
| 3.5 | Success/error feedback | - |

**Deliverable**: Working transaction entry with validation.

### Phase 4: Transaction History (2 days)

| Task | Description | Tests |
|------|-------------|-------|
| 4.1 | Transaction list with filters | `test_pages.py` |
| 4.2 | Date range picker | - |
| 4.3 | Account filter dropdown | - |
| 4.4 | Expandable row detail (show entries) | - |
| 4.5 | Pagination | - |

**Deliverable**: Searchable transaction history.

### Phase 5: Reports (2 days)

| Task | Description | Tests |
|------|-------------|-------|
| 5.1 | Report selector and date picker | - |
| 5.2 | Net worth report display | `test_pages.py::TestReportsPage` |
| 5.3 | Balance sheet report display | - |
| 5.4 | Multi-entity checkbox filter | - |
| 5.5 | CSV export | - |

**Deliverable**: Working reports with export.

### Phase 6: Dashboard (2 days)

| Task | Description | Tests |
|------|-------------|-------|
| 6.1 | Summary cards (net worth, assets, liabilities) | `test_pages.py::TestDashboardPage` |
| 6.2 | Recent transactions widget | - |
| 6.3 | Account balances table | - |
| 6.4 | Link to full pages | - |

**Deliverable**: Complete dashboard overview.

### Phase 7: Polish (1-2 days)

| Task | Description | Tests |
|------|-------------|-------|
| 7.1 | Keyboard navigation (Tab, Enter, Escape) | Manual testing |
| 7.2 | Loading states | - |
| 7.3 | Error handling improvements | - |
| 7.4 | Consistent styling pass | Visual review |

**Deliverable**: Production-ready frontend.

---

## 9. CLI Integration

Add frontend command to existing CLI:

```python
# cli.py addition
@cli.command()
@click.option('--port', default=3000, help='Port to run frontend')
@click.option('--api-url', default='http://localhost:8000', help='Backend API URL')
def ui(port: int, api_url: str):
    """Launch the web interface."""
    from family_office_ledger.ui.main import run
    from family_office_ledger.ui.api_client import api
    
    api.base_url = api_url
    run(port=port)
```

Usage:
```bash
# Start backend (in one terminal)
uv run uvicorn family_office_ledger.api.app:app --reload

# Start frontend (in another terminal)
uv run fol ui --port 3000
```

---

## 10. File Manifest

Files to create:

```
src/family_office_ledger/ui/
├── __init__.py
├── main.py
├── state.py
├── api_client.py
├── components/
│   ├── __init__.py
│   ├── nav.py
│   ├── tables.py
│   ├── forms.py
│   ├── modals.py
│   └── charts.py
└── pages/
    ├── __init__.py
    ├── dashboard.py
    ├── entities.py
    ├── accounts.py
    ├── transactions.py
    └── reports.py

tests/ui/
├── __init__.py
├── conftest.py
├── test_api_client.py
├── test_components.py
├── test_pages.py
└── test_workflows.py
```

Total: 18 new files

---

## Appendix A: Enums Reference

For dropdowns and validation:

```python
ENTITY_TYPES = [
    {"value": "llc", "label": "LLC"},
    {"value": "trust", "label": "Trust"},
    {"value": "partnership", "label": "Partnership"},
    {"value": "individual", "label": "Individual"},
    {"value": "holding_co", "label": "Holding Company"},
]

ACCOUNT_TYPES = [
    {"value": "asset", "label": "Asset"},
    {"value": "liability", "label": "Liability"},
    {"value": "equity", "label": "Equity"},
    {"value": "income", "label": "Income"},
    {"value": "expense", "label": "Expense"},
]

ACCOUNT_SUB_TYPES = [
    {"value": "checking", "label": "Checking"},
    {"value": "savings", "label": "Savings"},
    {"value": "credit_card", "label": "Credit Card"},
    {"value": "brokerage", "label": "Brokerage"},
    {"value": "ira", "label": "IRA"},
    {"value": "roth_ira", "label": "Roth IRA"},
    {"value": "401k", "label": "401(k)"},
    {"value": "529", "label": "529 Plan"},
    {"value": "real_estate", "label": "Real Estate"},
    {"value": "private_equity", "label": "Private Equity"},
    {"value": "venture_capital", "label": "Venture Capital"},
    {"value": "crypto", "label": "Cryptocurrency"},
    {"value": "cash", "label": "Cash"},
    {"value": "loan", "label": "Loan"},
    {"value": "other", "label": "Other"},
]
```

---

## Appendix B: Error Handling

Standard error patterns:

```python
# API errors
class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

# In api_client.py
async def _handle_response(self, response: httpx.Response) -> dict:
    if response.status_code == 422:
        detail = response.json().get("detail", "Validation error")
        raise APIError(422, detail)
    response.raise_for_status()
    return response.json()

# In UI components - show inline error
def show_error(message: str):
    ui.notify(message, type='negative', position='top')
```

---

## Appendix C: Styling Classes

Tailwind utilities for consistent styling:

```python
# Common class patterns
CARD = 'bg-white rounded-lg shadow p-4'
TABLE = 'w-full'
BUTTON_PRIMARY = 'bg-blue-600 text-white hover:bg-blue-700'
BUTTON_SECONDARY = 'bg-gray-200 text-gray-800 hover:bg-gray-300'
INPUT = 'border rounded px-3 py-2'
NAV_LINK = 'block px-4 py-2 hover:bg-gray-100 rounded'
NAV_LINK_ACTIVE = 'block px-4 py-2 bg-blue-100 text-blue-700 rounded'
```
