# Financial Features: Multi-Currency, Expense Tracking, Budgeting

## TL;DR

> **Quick Summary**: Add three interconnected financial features to the family office ledger: (1) Multi-currency support with exchange rates and FX gains/losses, (2) Expense tracking with categories, vendors, and expense reports, (3) Budgeting with category-based budgets, spending tracking, and alerts.
> 
> **Deliverables**:
> - Multi-Currency: Currency enum, ExchangeRate value object, ExchangeRateService, currency conversion in reports
> - Expense Tracking: ExpenseCategory enum, category/tags on transactions, ExpenseService, expense reports
> - Budgeting: Budget domain model, BudgetService, budget vs actual reports, overage alerts
> 
> **Estimated Effort**: Large (5-7 days)
> **Parallel Execution**: YES - 3 phases with internal parallelization
> **Critical Path**: Multi-Currency → Expense Tracking → Budgeting

---

## Context

### Original Request
Implement three additional features for the family office ledger:
1. Multi-Currency Support (Priority 1 - foundational)
2. Expense Tracking (Priority 2 - builds categories)
3. Budgeting (Priority 3 - uses expense categories)

### Current State Analysis

**Multi-Currency**:
- Money value object EXISTS with `currency: str = "USD"` field
- Database ALREADY stores currency separately (debit_currency, credit_currency columns)
- Operations FAIL on currency mismatch (ValueError)
- NO exchange rate handling, NO conversion, NO FX gains/losses
- API schemas missing currency in EntryResponse

**Expense Tracking**:
- TransactionType enum has `EXPENSE` but no sub-categories
- All expenses routed to single "Legal & Professional Fees" account
- NO category/tag fields on Transaction or Entry models
- NO vendor, department, or cost center tracking
- Income statement groups all expenses together

**Budgeting**:
- NO budget definitions or thresholds exist
- NO spending limits or alerts
- NO variance analysis (actual vs budget)
- Reporting infrastructure exists but no budget-specific reports

### Dependencies
```
Multi-Currency (Phase 1)
    └── Expense Tracking (Phase 2)
            └── Budgeting (Phase 3)
```

---

## Phase 1: Multi-Currency Support

### Objective
Enable the ledger to handle multiple currencies with exchange rate tracking, conversion, and FX gains/losses reporting.

### Deliverables
- `Currency` enum with ISO 4217 codes
- `ExchangeRate` value object
- `ExchangeRateRepository` (SQLite + Postgres)
- `CurrencyService` with conversion methods
- Updated API schemas with currency fields
- Multi-currency reporting support
- FX gains/losses calculation

### Domain Models

#### Currency Enum
```python
class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    # ... extensible
```

#### ExchangeRate Value Object
```python
@dataclass(frozen=True)
class ExchangeRate:
    from_currency: Currency
    to_currency: Currency
    rate: Decimal
    effective_date: date
    source: str = "manual"  # "manual", "api", "bank"
```

### Tasks

#### Task 1.1: Currency Enum and Validation
- Add `Currency` enum to `domain/value_objects.py`
- Update `Money.__post_init__` to validate currency
- Maintain backward compatibility (accept string, convert to enum)
- Tests: `tests/test_currency.py`

#### Task 1.2: ExchangeRate Domain Model
- Create `domain/exchange_rates.py` with `ExchangeRate` dataclass
- Add `ExchangeRateRepository` interface to `repositories/interfaces.py`
- Tests: `tests/test_exchange_rates.py`

#### Task 1.3: Exchange Rate Repository (SQLite)
- Add `exchange_rates` table to SQLite schema
- Implement `SQLiteExchangeRateRepository`
- Methods: `add`, `get`, `get_rate_for_date`, `list_by_currency_pair`, `list_by_date_range`
- Tests: `tests/test_exchange_rate_repository.py`

#### Task 1.4: Exchange Rate Repository (Postgres)
- Mirror SQLite implementation for Postgres
- Tests in `tests/test_repositories_postgres.py`

#### Task 1.5: CurrencyService
- Create `services/currency.py` with `CurrencyService`
- Methods:
  - `convert(amount: Money, to_currency: Currency, as_of_date: date) -> Money`
  - `get_rate(from_currency, to_currency, as_of_date) -> ExchangeRate`
  - `add_rate(rate: ExchangeRate) -> None`
  - `calculate_fx_gain_loss(original: Money, current: Money, rate_then: ExchangeRate, rate_now: ExchangeRate) -> Money`
- Tests: `tests/test_currency_service.py`

#### Task 1.6: API Schema Updates
- Add `currency` field to `EntryCreate` and `EntryResponse`
- Add exchange rate endpoints to API
- Update existing endpoints to include currency info
- Tests: `tests/test_currency_api.py`

#### Task 1.7: Multi-Currency Reporting
- Update `ReportingServiceImpl` to handle multi-currency
- Add base currency parameter for consolidated reports
- FX gains/losses report
- Tests: `tests/test_multicurrency_reports.py`

#### Task 1.8: CLI Commands for Currency
- `fol currency rates add --from USD --to EUR --rate 0.92 --date 2026-01-29`
- `fol currency rates list --from USD --to EUR`
- `fol currency convert --amount 100 --from USD --to EUR --date 2026-01-29`
- Tests: `tests/test_currency_cli.py`

---

## Phase 2: Expense Tracking

### Objective
Enable categorization, tagging, and detailed tracking of expenses with vendor management and expense reporting.

### Deliverables
- `ExpenseCategory` enum (hierarchical)
- Category and tags fields on Transaction/Entry
- `Vendor` domain model
- `ExpenseService` with categorization and reporting
- Expense report endpoints
- Recurring expense detection

### Domain Models

#### ExpenseCategory Enum
```python
class ExpenseCategory(str, Enum):
    # Operations
    PAYROLL = "payroll"
    RENT = "rent"
    UTILITIES = "utilities"
    INSURANCE = "insurance"
    
    # Professional Services
    LEGAL = "legal"
    ACCOUNTING = "accounting"
    CONSULTING = "consulting"
    
    # Travel & Entertainment
    TRAVEL = "travel"
    MEALS = "meals"
    ENTERTAINMENT = "entertainment"
    
    # Technology
    SOFTWARE = "software"
    HARDWARE = "hardware"
    HOSTING = "hosting"
    
    # Financial
    BANK_FEES = "bank_fees"
    INTEREST_EXPENSE = "interest_expense"
    
    # Other
    OFFICE_SUPPLIES = "office_supplies"
    MARKETING = "marketing"
    OTHER = "other"
```

#### Vendor Model
```python
@dataclass
class Vendor:
    name: str
    id: UUID = field(default_factory=uuid4)
    category: ExpenseCategory | None = None
    tax_id: str | None = None
    is_1099_eligible: bool = False
    default_account_id: UUID | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
```

#### Transaction Extensions
```python
@dataclass
class Transaction:
    # ... existing fields ...
    category: ExpenseCategory | None = None
    tags: list[str] = field(default_factory=list)
    vendor_id: UUID | None = None
    is_recurring: bool = False
    recurring_frequency: str | None = None  # "monthly", "quarterly", "annual"
```

### Tasks

#### Task 2.1: ExpenseCategory Enum
- Add `ExpenseCategory` enum to `domain/value_objects.py`
- Hierarchical structure with parent categories
- Tests: `tests/test_expense_category.py`

#### Task 2.2: Transaction Model Extensions
- Add `category`, `tags`, `vendor_id`, `is_recurring`, `recurring_frequency` to Transaction
- Update Entry with optional `category` override
- Maintain backward compatibility (all new fields optional with defaults)
- Tests: `tests/test_transaction_extensions.py`

#### Task 2.3: Vendor Domain Model
- Create `domain/vendors.py` with `Vendor` dataclass
- Add `VendorRepository` interface
- Tests: `tests/test_vendors.py`

#### Task 2.4: Vendor Repository (SQLite)
- Add `vendors` table to SQLite schema
- Implement `SQLiteVendorRepository`
- Methods: `add`, `get`, `update`, `delete`, `list_all`, `list_by_category`, `search_by_name`
- Tests: `tests/test_vendor_repository.py`

#### Task 2.5: Vendor Repository (Postgres)
- Mirror SQLite implementation
- Tests in `tests/test_repositories_postgres.py`

#### Task 2.6: Database Schema Updates for Categories
- Add columns to `transactions` table: `category`, `tags` (JSON), `vendor_id`, `is_recurring`, `recurring_frequency`
- Add columns to `entries` table: `category` (optional override)
- Migration strategy: ALTER TABLE with defaults
- Tests: Verify existing data unaffected

#### Task 2.7: ExpenseService
- Create `services/expense.py` with `ExpenseService`
- Methods:
  - `categorize_transaction(txn_id, category, tags, vendor_id) -> Transaction`
  - `auto_categorize(transaction) -> ExpenseCategory | None` (rule-based)
  - `get_expense_summary(entity_ids, start_date, end_date) -> ExpenseSummary`
  - `get_expenses_by_category(entity_ids, start_date, end_date) -> dict[ExpenseCategory, Money]`
  - `get_expenses_by_vendor(entity_ids, start_date, end_date) -> dict[UUID, Money]`
  - `detect_recurring_expenses(entity_id, lookback_months) -> list[RecurringExpense]`
- Tests: `tests/test_expense_service.py`

#### Task 2.8: Expense API Endpoints
- `POST /expenses/transactions/{txn_id}/categorize` - Assign category/tags/vendor
- `GET /expenses/summary` - Expense summary by category
- `GET /expenses/by-category` - Detailed breakdown
- `GET /expenses/by-vendor` - Vendor spending analysis
- `GET /expenses/recurring` - Recurring expense detection
- CRUD for vendors: `POST/GET/PUT/DELETE /vendors`
- Tests: `tests/test_expense_api.py`

#### Task 2.9: Expense CLI Commands
- `fol expense categorize --txn-id UUID --category legal --tags "tax-deductible,q1"`
- `fol expense summary --start-date 2026-01-01 --end-date 2026-01-31`
- `fol expense by-category --start-date ... --end-date ...`
- `fol expense by-vendor --start-date ... --end-date ...`
- `fol vendor add --name "Acme Corp" --category consulting --tax-id "12-3456789"`
- `fol vendor list`
- Tests: `tests/test_expense_cli.py`

#### Task 2.10: Transaction Classifier Enhancement
- Update `TransactionClassifier` to infer `ExpenseCategory` from keywords
- Add vendor matching from memo/description
- Auto-tag based on patterns
- Tests: `tests/test_transaction_classifier.py` (extend existing)

---

## Phase 3: Budgeting

### Objective
Enable budget definition, tracking against actuals, variance analysis, and overage alerts.

### Deliverables
- `Budget` domain model with period and category support
- `BudgetRepository` (SQLite + Postgres)
- `BudgetService` with variance calculations
- Budget vs actual reports
- Overage alerts/notifications
- Budget API and CLI

### Domain Models

#### Budget Model
```python
@dataclass
class Budget:
    name: str
    entity_id: UUID
    period_type: BudgetPeriodType  # monthly, quarterly, annual
    start_date: date
    end_date: date
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)

class BudgetPeriodType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"
```

#### BudgetLineItem Model
```python
@dataclass
class BudgetLineItem:
    budget_id: UUID
    category: ExpenseCategory
    budgeted_amount: Money
    id: UUID = field(default_factory=uuid4)
    account_id: UUID | None = None  # Optional: specific account
    notes: str = ""
```

#### BudgetVariance (computed)
```python
@dataclass(frozen=True)
class BudgetVariance:
    category: ExpenseCategory
    budgeted: Money
    actual: Money
    variance: Money  # budgeted - actual (positive = under budget)
    variance_percent: Decimal
    is_over_budget: bool
```

### Tasks

#### Task 3.1: Budget Domain Models
- Create `domain/budgets.py` with `Budget`, `BudgetLineItem`, `BudgetPeriodType`, `BudgetVariance`
- Add `BudgetRepository` interface
- Tests: `tests/test_budgets.py`

#### Task 3.2: Budget Repository (SQLite)
- Add `budgets` and `budget_line_items` tables
- Implement `SQLiteBudgetRepository`
- Methods: `add`, `get`, `update`, `delete`, `list_by_entity`, `get_active_for_period`
- Tests: `tests/test_budget_repository.py`

#### Task 3.3: Budget Repository (Postgres)
- Mirror SQLite implementation
- Tests in `tests/test_repositories_postgres.py`

#### Task 3.4: BudgetService
- Create `services/budget.py` with `BudgetService`
- Methods:
  - `create_budget(entity_id, name, period_type, start_date, end_date, line_items) -> Budget`
  - `get_budget(budget_id) -> Budget | None`
  - `update_line_item(budget_id, category, amount) -> BudgetLineItem`
  - `get_variance_report(budget_id) -> list[BudgetVariance]`
  - `get_budget_vs_actual(entity_id, start_date, end_date) -> BudgetVsActualReport`
  - `check_budget_alerts(entity_id) -> list[BudgetAlert]`
  - `copy_budget(source_budget_id, new_start_date) -> Budget` (for recurring budgets)
- Tests: `tests/test_budget_service.py`

#### Task 3.5: Budget Alert System
- Create `BudgetAlert` dataclass with threshold levels (80%, 90%, 100%, 110%)
- Alert types: approaching, at_limit, over_budget
- Method: `get_active_alerts(entity_ids) -> list[BudgetAlert]`
- Tests: `tests/test_budget_alerts.py`

#### Task 3.6: Budget API Endpoints
- `POST /budgets` - Create budget with line items
- `GET /budgets/{budget_id}` - Get budget details
- `PUT /budgets/{budget_id}` - Update budget
- `DELETE /budgets/{budget_id}` - Delete budget
- `GET /budgets/{budget_id}/variance` - Variance report
- `GET /budgets/vs-actual` - Budget vs actual for period
- `GET /budgets/alerts` - Active budget alerts
- `POST /budgets/{budget_id}/copy` - Copy budget to new period
- Tests: `tests/test_budget_api.py`

#### Task 3.7: Budget CLI Commands
- `fol budget create --entity-id UUID --name "2026 Operating Budget" --period monthly --start-date 2026-01-01`
- `fol budget add-line --budget-id UUID --category legal --amount 5000`
- `fol budget list --entity-id UUID`
- `fol budget variance --budget-id UUID`
- `fol budget vs-actual --entity-id UUID --start-date ... --end-date ...`
- `fol budget alerts --entity-id UUID`
- Tests: `tests/test_budget_cli.py`

#### Task 3.8: Budget Reporting Integration
- Add budget comparison to existing reports
- Dashboard widget for budget status
- Export budget reports to CSV/JSON
- Tests: `tests/test_budget_reports.py`

---

## Execution Strategy

### Phase Dependencies
```
Phase 1 (Multi-Currency) ─────────────────────────────────────────┐
    Task 1.1 ──┬── Task 1.2 ──┬── Task 1.3 ──┬── Task 1.5 ──┬── Task 1.6 ──┬── Task 1.7 ──┬── Task 1.8
               │              │              │              │              │              │
               └── Task 1.4 ──┘              └──────────────┴──────────────┘              │
                                                                                          │
Phase 2 (Expense Tracking) ───────────────────────────────────────────────────────────────┤
    Task 2.1 ──┬── Task 2.2 ──┬── Task 2.3 ──┬── Task 2.4 ──┬── Task 2.6 ──┬── Task 2.7 ──┼── Task 2.8 ──┬── Task 2.9
               │              │              │              │              │              │              │
               │              └── Task 2.5 ──┘              │              │              │              └── Task 2.10
               │                                            └──────────────┘              │
               │                                                                          │
Phase 3 (Budgeting) ──────────────────────────────────────────────────────────────────────┘
    Task 3.1 ──┬── Task 3.2 ──┬── Task 3.4 ──┬── Task 3.5 ──┬── Task 3.6 ──┬── Task 3.7 ──┬── Task 3.8
               │              │              │              │              │              │
               └── Task 3.3 ──┘              └──────────────┘              └──────────────┘
```

### Parallel Execution Waves

**Phase 1 Waves:**
- Wave 1.1: Tasks 1.1, 1.2 (domain models)
- Wave 1.2: Tasks 1.3, 1.4 (repositories - parallel)
- Wave 1.3: Task 1.5 (service)
- Wave 1.4: Tasks 1.6, 1.7, 1.8 (API, reports, CLI - parallel)

**Phase 2 Waves:**
- Wave 2.1: Tasks 2.1, 2.2, 2.3 (domain models)
- Wave 2.2: Tasks 2.4, 2.5, 2.6 (repositories + schema - parallel)
- Wave 2.3: Task 2.7 (service)
- Wave 2.4: Tasks 2.8, 2.9, 2.10 (API, CLI, classifier - parallel)

**Phase 3 Waves:**
- Wave 3.1: Task 3.1 (domain models)
- Wave 3.2: Tasks 3.2, 3.3 (repositories - parallel)
- Wave 3.3: Tasks 3.4, 3.5 (service + alerts)
- Wave 3.4: Tasks 3.6, 3.7, 3.8 (API, CLI, reporting - parallel)

---

## Verification Strategy

### Per-Task Verification
Each task follows TDD: Write failing tests → Implement → Verify pass

### Phase Gates

**Phase 1 Complete When:**
- [ ] `uv run pytest tests/test_currency*.py tests/test_exchange*.py tests/test_multicurrency*.py -v` → All pass
- [ ] `uv run mypy src/` → No new errors
- [ ] Manual: Create exchange rate, convert amount, view multi-currency report

**Phase 2 Complete When:**
- [ ] `uv run pytest tests/test_expense*.py tests/test_vendor*.py -v` → All pass
- [ ] `uv run mypy src/` → No new errors
- [ ] Manual: Categorize transaction, view expense by category report

**Phase 3 Complete When:**
- [ ] `uv run pytest tests/test_budget*.py -v` → All pass
- [ ] `uv run mypy src/` → No new errors
- [ ] Manual: Create budget, view variance report, check alerts

### Final Verification
```bash
uv run pytest -v                    # All tests pass
uv run mypy src/                    # No type errors
uv run ruff check .                 # No lint errors
uv run fol --help                   # Shows all new commands
```

---

## Commit Strategy

| After | Message | Files |
|-------|---------|-------|
| Task 1.1-1.2 | `feat(domain): add Currency enum and ExchangeRate value object` | domain/ |
| Task 1.3-1.4 | `feat(repositories): add ExchangeRate repositories` | repositories/ |
| Task 1.5 | `feat(services): add CurrencyService with conversion` | services/ |
| Task 1.6-1.8 | `feat: multi-currency API, reporting, and CLI` | api/, services/, cli.py |
| Task 2.1-2.3 | `feat(domain): add ExpenseCategory, Vendor, Transaction extensions` | domain/ |
| Task 2.4-2.6 | `feat(repositories): add Vendor repositories and expense schema` | repositories/ |
| Task 2.7 | `feat(services): add ExpenseService` | services/ |
| Task 2.8-2.10 | `feat: expense tracking API, CLI, and classifier` | api/, cli.py, services/ |
| Task 3.1 | `feat(domain): add Budget and BudgetLineItem models` | domain/ |
| Task 3.2-3.3 | `feat(repositories): add Budget repositories` | repositories/ |
| Task 3.4-3.5 | `feat(services): add BudgetService with alerts` | services/ |
| Task 3.6-3.8 | `feat: budgeting API, CLI, and reporting` | api/, cli.py, services/ |

---

## Risk Mitigation

### Breaking Changes
- All new fields have defaults → backward compatible
- Currency validation accepts strings → gradual migration
- Existing reports unchanged; new multi-currency reports are separate endpoints

### Data Migration
- Exchange rates: New table, no migration needed
- Transaction extensions: ALTER TABLE with NULL defaults
- Vendor: New table, no migration needed
- Budget: New tables, no migration needed

### Performance
- Exchange rate lookups: Index on (from_currency, to_currency, effective_date)
- Expense queries: Index on category, vendor_id, is_recurring
- Budget queries: Index on entity_id, start_date, end_date

---

## Success Criteria

### Multi-Currency
- [ ] Can add/view exchange rates
- [ ] Can convert amounts between currencies
- [ ] Reports support base currency consolidation
- [ ] FX gains/losses calculated correctly

### Expense Tracking
- [ ] Transactions can be categorized
- [ ] Tags can be added to transactions
- [ ] Vendors can be managed
- [ ] Expense reports by category/vendor work
- [ ] Recurring expenses detected

### Budgeting
- [ ] Budgets can be created with line items
- [ ] Variance reports show budget vs actual
- [ ] Alerts trigger at thresholds
- [ ] Budgets can be copied to new periods
