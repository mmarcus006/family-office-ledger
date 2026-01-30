# Module Overview

This document outlines the purpose and responsibility of each major source code directory in the Atlas Family Office Ledger.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Interface Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    CLI      │  │  FastAPI    │  │  Streamlit / NiceGUI    │  │
│  │  (cli.py)   │  │  (api/)     │  │  (streamlit_app/, ui/)  │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          └────────────────┼─────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Service Layer                                │
│  ┌───────────┐ ┌─────────────┐ ┌───────────┐ ┌───────────────┐  │
│  │  Ledger   │ │Reconciliation│ │ Reporting │ │  Portfolio    │  │
│  │  Service  │ │   Service   │ │  Service  │ │  Analytics    │  │
│  └─────┬─────┘ └──────┬──────┘ └─────┬─────┘ └───────┬───────┘  │
│        │              │              │               │          │
│  ┌─────┴─────┐ ┌──────┴──────┐ ┌─────┴─────┐ ┌───────┴───────┐  │
│  │ Currency  │ │   Budget    │ │  Expense  │ │  Ownership    │  │
│  │  Service  │ │   Service   │ │  Service  │ │ Graph Service │  │
│  └───────────┘ └─────────────┘ └───────────┘ └───────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Repository Layer                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    interfaces.py                            │ │
│  │  EntityRepo, AccountRepo, TransactionRepo, TaxLotRepo...   │ │
│  └───────────────────────────┬─────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐   │
│  │  sqlite.py              │            postgres.py          │   │
│  │  SQLiteDatabase         │        PostgresDatabase         │   │
│  │  SQLite*Repository      │        Postgres*Repository      │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Domain Layer                                 │
│  ┌───────────┐ ┌─────────────┐ ┌───────────┐ ┌───────────────┐  │
│  │ Entity    │ │ Transaction │ │  Money    │ │  Household    │  │
│  │ Account   │ │   Entry     │ │ Quantity  │ │  Ownership    │  │
│  │ Security  │ │  TaxLot     │ │  Enums    │ │  Budget       │  │
│  │ Position  │ │             │ │           │ │               │  │
│  └───────────┘ └─────────────┘ └───────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Source Directories

### `/src/family_office_ledger/domain/`

**Responsibility:** Core domain models representing the accounting and investment domain. Contains pure business logic with no external dependencies.

| File | Purpose |
|------|---------|
| `entities.py` | Core structural models: Entity (LLC, trust, etc.), Account, Security, Position |
| `transactions.py` | Double-entry journal: Transaction, Entry, TaxLot with validation rules |
| `value_objects.py` | Immutable value types (Money, Quantity) and 11 domain enums |
| `reconciliation.py` | Bank reconciliation workflow: Session, Match, MatchStatus |
| `transfer_matching.py` | Inter-entity transfer matching: Session, Match |
| `corporate_actions.py` | Stock splits, spinoffs, mergers with adjustment logic |
| `households.py` | Family grouping: Household, HouseholdMember with time-bounded membership |
| `ownership.py` | Entity ownership graph: EntityOwnership with fractional ownership |
| `budgets.py` | Financial planning: Budget, BudgetLineItem, BudgetVariance |
| `vendors.py` | Payee/vendor management for expense tracking |
| `exchange_rates.py` | Currency exchange rates with source attribution |
| `audit.py` | Audit trail: AuditEntry, AuditAction for compliance |
| `documents.py` | Tax document generation: Document, TaxDocLine |

### `/src/family_office_ledger/repositories/`

**Responsibility:** Data persistence abstraction with SQLite and PostgreSQL implementations. Provides repository pattern for all domain aggregates.

| File | Purpose |
|------|---------|
| `interfaces.py` | 11 abstract repository interfaces (EntityRepository, AccountRepository, etc.) |
| `sqlite.py` | SQLite implementations (~1,800 lines) with schema initialization |
| `postgres.py` | PostgreSQL implementations (~1,900 lines) mirroring SQLite |

**Repository Interfaces:**
- EntityRepository, HouseholdRepository, AccountRepository
- SecurityRepository, PositionRepository
- TransactionRepository, TaxLotRepository
- ReconciliationSessionRepository, EntityOwnershipRepository
- ExchangeRateRepository, VendorRepository, BudgetRepository

### `/src/family_office_ledger/services/`

**Responsibility:** Business logic orchestration. Services coordinate between repositories and implement complex workflows like reconciliation, lot matching, and reporting.

| File | Purpose |
|------|---------|
| `interfaces.py` | Service interface definitions for dependency injection |
| `ledger.py` | Core accounting operations: journal entries, balances |
| `ingestion.py` | Transaction import from various sources |
| `reconciliation.py` | Bank statement reconciliation workflow |
| `transfer_matching.py` | Inter-entity transfer matching service |
| `lot_matching.py` | Tax lot selection strategies (FIFO, LIFO, SpecID, etc.) |
| `reporting.py` | Financial report generation (balance sheet, net worth) |
| `corporate_actions.py` | Corporate action processing (splits, dividends) |
| `qsbs.py` | Qualified Small Business Stock tracking |
| `tax_documents.py` | Schedule D, Form 8949 generation |
| `portfolio_analytics.py` | Asset allocation, concentration, performance |
| `currency.py` | Multi-currency support and conversion |
| `expense.py` | Expense categorization and analysis |
| `budget.py` | Budget creation, variance tracking, alerts |
| `audit.py` | Audit trail management |
| `ownership_graph.py` | Ownership traversal, cycle detection, look-through calculations |
| `transaction_classifier.py` | ML-style transaction categorization |

### `/src/family_office_ledger/parsers/`

**Responsibility:** File format parsing for transaction import. Supports CSV, OFX/QFX, and bank-specific formats.

| File | Purpose |
|------|---------|
| `csv_parser.py` | Generic CSV parsing with column mapping |
| `ofx_parser.py` | OFX/QFX (Quicken) format parsing |
| `bank_parsers.py` | Bank-specific parsers: Citi, UBS, Morgan Stanley |

### `/src/family_office_ledger/api/`

**Responsibility:** REST API layer built with FastAPI. Provides HTTP interface for all ledger operations.

| File | Purpose |
|------|---------|
| `app.py` | FastAPI application factory and configuration |
| `routes.py` | 15 routers with 80+ endpoints (entity, account, transaction, report, etc.) |
| `schemas.py` | Pydantic v2 request/response models (~700 lines) |

### `/src/family_office_ledger/streamlit_app/`

**Responsibility:** Production-ready web UI built with Streamlit. Provides a Quicken-style interface for all ledger operations.

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit entry point with navigation |
| `api_client.py` | HTTP client for FastAPI backend |
| `styles.py` | Custom CSS for Quicken-style theming |
| `pages/` | 14 Streamlit pages (Dashboard, Entities, Accounts, etc.) |

### `/src/family_office_ledger/ui/`

**Responsibility:** Alternative NiceGUI-based web UI (development/experimental). Not production-ready.

### `/src/family_office_ledger/cli.py`

**Responsibility:** Full-featured command-line interface. Single file (~2,700 lines) providing access to all ledger operations via the `fol` command.

**Command Groups:**
- `fol init/status` - Database initialization and status
- `fol ingest` - Transaction import
- `fol reconcile` - Bank reconciliation (7 subcommands)
- `fol transfer` - Transfer matching (6 subcommands)
- `fol qsbs` - QSBS management (2 subcommands)
- `fol tax` - Tax document generation
- `fol portfolio` - Portfolio analytics
- `fol currency` - Exchange rate management
- `fol expense` - Expense reports
- `fol vendor` - Vendor management
- `fol budget` - Budget management
- `fol household` - Household management
- `fol ownership` - Ownership graph
- `fol audit` - Audit trail
- `fol ui` - Launch Streamlit UI

## Data Flow Example: Create Transaction

```
1. CLI/API receives transaction request
2. Service layer validates business rules
3. Service calls TransactionRepository.add()
4. Repository executes SQL INSERT
5. Service creates AuditEntry via AuditService
6. Response returned to client
```

## Dependency Rules

1. **Domain** has no dependencies on other layers
2. **Repositories** depend only on Domain
3. **Services** depend on Domain and Repositories
4. **API/CLI/UI** depend on Services (never directly on Repositories)
