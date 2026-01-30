# Project Structure

```
./
├── src/
│   └── family_office_ledger/           # Main package
│       ├── __init__.py                 # Public exports, version
│       ├── cli.py                      # CLI entry point (fol command)
│       │
│       ├── domain/                     # Domain models (13 files)
│       │   ├── __init__.py
│       │   ├── entities.py             # Entity, Account, Security, Position
│       │   ├── transactions.py         # Transaction, Entry, TaxLot
│       │   ├── value_objects.py        # Money, Quantity, 11 enums
│       │   ├── reconciliation.py       # ReconciliationSession, Match
│       │   ├── transfer_matching.py    # TransferMatchingSession, Match
│       │   ├── corporate_actions.py    # CorporateAction, Price
│       │   ├── documents.py            # Document, TaxDocLine
│       │   ├── audit.py                # AuditEntry, AuditAction
│       │   ├── exchange_rates.py       # ExchangeRate
│       │   ├── vendors.py              # Vendor
│       │   ├── budgets.py              # Budget, BudgetLineItem, BudgetVariance
│       │   ├── households.py           # Household, HouseholdMember
│       │   └── ownership.py            # EntityOwnership
│       │
│       ├── repositories/               # Persistence layer (4 files)
│       │   ├── __init__.py             # Optional Postgres export
│       │   ├── interfaces.py           # 11 repository ABCs
│       │   ├── sqlite.py               # SQLite implementations
│       │   └── postgres.py             # PostgreSQL implementations
│       │
│       ├── services/                   # Business logic (17 files)
│       │   ├── __init__.py
│       │   ├── interfaces.py           # Service ABCs
│       │   ├── ledger.py               # Core ledger operations
│       │   ├── ingestion.py            # Transaction import
│       │   ├── reconciliation.py       # Bank reconciliation
│       │   ├── transfer_matching.py    # Inter-entity transfers
│       │   ├── reporting.py            # Financial reports
│       │   ├── lot_matching.py         # Tax lot selection
│       │   ├── corporate_actions.py    # Stock splits, etc.
│       │   ├── qsbs.py                 # QSBS tracking
│       │   ├── tax_documents.py        # Tax form generation
│       │   ├── portfolio_analytics.py  # Portfolio analysis
│       │   ├── currency.py             # Exchange rates
│       │   ├── expense.py              # Expense categorization
│       │   ├── audit.py                # Audit trail
│       │   ├── budget.py               # Budgeting
│       │   ├── ownership_graph.py      # Ownership traversal
│       │   └── transaction_classifier.py # ML-style classification
│       │
│       ├── parsers/                    # File parsing (4 files)
│       │   ├── __init__.py
│       │   ├── csv_parser.py           # Generic CSV
│       │   ├── ofx_parser.py           # OFX/QFX format
│       │   └── bank_parsers.py         # CITI, UBS, Morgan Stanley
│       │
│       ├── api/                        # REST API (4 files)
│       │   ├── __init__.py
│       │   ├── app.py                  # FastAPI app factory
│       │   ├── routes.py               # 15 routers, 80+ endpoints
│       │   └── schemas.py              # Pydantic request/response models
│       │
│       ├── streamlit_app/              # Streamlit UI
│       │   ├── __init__.py
│       │   ├── app.py                  # Main Streamlit entry
│       │   ├── api_client.py           # HTTP client for API
│       │   ├── styles.py               # Quicken-style CSS
│       │   ├── .streamlit/
│       │   │   └── config.toml         # Streamlit configuration
│       │   └── pages/                  # 14 Streamlit pages
│       │       ├── 1_Dashboard.py
│       │       ├── 2_Entities.py
│       │       ├── 3_Accounts.py
│       │       ├── 4_Transactions.py
│       │       ├── 5_Reports.py
│       │       ├── 6_Reconciliation.py
│       │       ├── 7_Transfers.py
│       │       ├── 8_Audit.py
│       │       ├── 9_Currency.py
│       │       ├── 10_Portfolio.py
│       │       ├── 11_QSBS.py
│       │       ├── 12_Tax.py
│       │       ├── 13_Households.py
│       │       └── 14_Ownership.py
│       │
│       └── ui/                         # NiceGUI UI (optional, dev)
│           ├── __init__.py
│           ├── main.py
│           ├── api_client.py
│           ├── state.py
│           ├── constants.py
│           ├── components/
│           │   ├── __init__.py
│           │   ├── nav.py
│           │   ├── modals.py
│           │   ├── forms.py
│           │   ├── tables.py
│           │   └── charts.py
│           └── pages/
│               ├── __init__.py
│               ├── dashboard.py
│               ├── entities.py
│               ├── accounts.py
│               ├── transactions.py
│               └── reports.py
│
├── tests/                              # Test suite (61 modules)
│   ├── conftest.py                     # Shared fixtures
│   ├── test_entities.py
│   ├── test_transactions.py
│   ├── test_value_objects.py
│   ├── test_tax_lots.py
│   ├── test_repositories_sqlite.py
│   ├── test_repositories_postgres.py
│   ├── test_ledger_service.py
│   ├── test_lot_matching_service.py
│   ├── test_corporate_action_service.py
│   ├── test_reconciliation_*.py        # 6 reconciliation tests
│   ├── test_currency_*.py              # 6 currency tests
│   ├── test_expense_*.py               # 4 expense tests
│   ├── test_budget_*.py                # 5 budget tests
│   ├── test_ownership_graph.py
│   ├── test_households_repository.py
│   ├── test_api.py
│   ├── test_cli.py
│   ├── streamlit_app/                  # Streamlit UI tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_streamlit_api_client.py
│   │   └── test_streamlit_pages.py
│   └── ui/                             # NiceGUI tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_api_client.py
│       ├── test_components.py
│       ├── test_pages.py
│       └── test_workflows.py
│
├── docs/                               # Documentation
│   └── architecture-diagrams.md        # Mermaid diagrams
│
├── specs/                              # Project specifications
│   └── (this directory)
│
├── .sisyphus/                          # AI planning artifacts
│   ├── boulder.json
│   ├── plans/
│   ├── notepads/
│   └── drafts/
│
├── pyproject.toml                      # Project configuration
├── README.md                           # Project readme
├── AGENTS.md                           # AI agent context
└── .gitignore                          # Git ignore patterns
```

## File Counts by Layer

| Layer | Files | Lines (approx) |
|-------|-------|----------------|
| Domain | 13 | ~2,000 |
| Repositories | 4 | ~4,000 |
| Services | 17 | ~5,000 |
| API | 4 | ~3,500 |
| Parsers | 4 | ~800 |
| CLI | 1 | ~2,700 |
| Streamlit UI | 17 | ~4,000 |
| NiceGUI UI | 14 | ~2,000 |
| Tests | 61 | ~15,000 |
| **Total** | **135** | **~39,000** |
