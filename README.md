# Atlas Family Office Ledger

A double-entry, multi-entity accounting and investment ledger for family offices. Built with Python 3.12+, FastAPI, and Streamlit.

## Features

### Core Accounting
- **Multi-entity structure** - LLCs, trusts, partnerships, individuals, holding companies
- **Double-entry journal** - Immutable transaction history with balanced debits/credits
- **Multi-currency support** - 15+ currencies with exchange rate management
- **Household groupings** - Aggregate entities into households for consolidated reporting

### Investment Management
- **Investment position tracking** - Tax lot management with cost basis
- **Cost basis methods** - FIFO, LIFO, Specific ID, Average Cost, Min/Max Gain
- **Portfolio analytics** - Asset allocation, concentration reports, performance tracking
- **QSBS tracking** - Qualified Small Business Stock (IRC Section 1202) eligibility

### Reconciliation & Transfers
- **Bank statement reconciliation** - Match imported statements with ledger transactions
- **Transfer matching** - Identify and link inter-account transfers
- **Parser support** - CSV, OFX, QFX formats; CITI, UBS, Morgan Stanley parsers

### Reporting & Tax
- **Financial reports** - Net worth, balance sheet, P&L by entity or consolidated
- **Tax documents** - Form 8949, Schedule D generation
- **Audit trail** - Complete history of all changes with filtering

### Ownership Structure
- **Ownership graph** - Track entity ownership relationships (beneficial, legal)
- **Look-through net worth** - Calculate effective ownership across entity chains

## Installation

```bash
# Install dependencies
uv sync --dev

# Initialize the database
uv run fol init
```

## Usage

### Command Line Interface

```bash
# Show all commands
uv run fol --help

# Check system status
uv run fol status

# Core operations
uv run fol ingest <file>           # Import transactions
uv run fol reconcile <subcommand>  # Bank reconciliation
uv run fol transfer <subcommand>   # Transfer matching
uv run fol portfolio <subcommand>  # Portfolio reports

# Tax & compliance
uv run fol qsbs <subcommand>       # QSBS tracking
uv run fol tax <subcommand>        # Tax document generation
uv run fol audit <subcommand>      # Audit trail

# Other
uv run fol currency <subcommand>   # Exchange rates
uv run fol expense <subcommand>    # Expense tracking
uv run fol budget <subcommand>     # Budgeting
```

### Web Interface (Streamlit)

```bash
# Launch the Streamlit UI (requires API server)
uv run fol ui
```

The UI provides 14 pages:
- **Dashboard** - Net worth overview, KPIs, charts
- **Entities** - Create and manage entities
- **Accounts** - Manage accounts by entity
- **Transactions** - Record journal entries
- **Reports** - Generate financial reports
- **Reconciliation** - Bank statement matching
- **Transfers** - Inter-account transfer matching
- **Audit** - View audit trail
- **Currency** - Exchange rate management
- **Portfolio** - Asset allocation and performance
- **QSBS** - Qualified small business stock tracking
- **Tax** - Tax document generation
- **Households** - Household management
- **Ownership** - Entity ownership structure

### REST API

```bash
# Start the API server
uv run uvicorn family_office_ledger.api.app:app --reload

# API documentation available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

## Architecture

```
src/family_office_ledger/
├── domain/          # Entities, transactions, value objects
├── services/        # Business logic (17 services)
├── repositories/    # SQLite + Postgres persistence
├── parsers/         # CSV/OFX/bank statement parsing
├── api/             # FastAPI REST endpoints (80+ routes)
├── streamlit_app/   # Streamlit UI (14 pages)
└── cli.py           # CLI entry point
```

### Layered Architecture
- **Domain** - Core business entities and value objects (frozen dataclasses)
- **Repositories** - Data persistence interfaces with SQLite/Postgres implementations
- **Services** - Business logic with `*Impl` suffix naming convention
- **API/CLI/UI** - Presentation layers

## Development

```bash
# Run tests (1145 tests)
uv run pytest

# Type checking (strict mode)
uv run mypy src/

# Linting
uv run ruff check .

# Format code
uv run ruff format .
```

### Database
- **Default**: SQLite at `~/.family_office_ledger/ledger.db`
- **Optional**: PostgreSQL (requires `psycopg2`)

## License

MIT
