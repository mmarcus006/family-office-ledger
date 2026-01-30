# Setup Guide

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.12+ | Runtime |
| uv | latest | Package manager |
| Git | any | Version control |
| PostgreSQL | 13+ | Optional production database |

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd quicken
```

### 2. Install Dependencies

Using `uv` (recommended):

```bash
# Install all dependencies including dev tools
uv sync --dev

# Or install with optional frontend dependencies
uv sync --dev --extra frontend
```

Using pip (alternative):

```bash
pip install -e ".[dev,frontend]"
```

### 3. Initialize the Database

```bash
# Initialize SQLite database (default location: ~/.family_office_ledger/ledger.db)
uv run fol init

# Or specify a custom path
uv run fol --database /path/to/ledger.db init
```

### 4. Verify Installation

```bash
# Check CLI is working
uv run fol --help

# Check database status
uv run fol status
```

## Running the Application

### CLI Mode

```bash
# Show help
uv run fol --help

# Common commands
uv run fol status                    # Database status
uv run fol entity list               # List entities (if any)
uv run fol account list              # List accounts
```

### API Server

```bash
# Start the FastAPI server
uvicorn family_office_ledger.api.app:app --reload

# Or with custom host/port
uvicorn family_office_ledger.api.app:app --host 0.0.0.0 --port 8000
```

API will be available at:
- Endpoints: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Streamlit UI

```bash
# Launch via CLI (starts API server automatically)
uv run fol ui

# Or manually
streamlit run src/family_office_ledger/streamlit_app/app.py
```

UI will be available at http://localhost:8501

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | None | PostgreSQL connection string |
| `DATABASE_PATH` | `~/.family_office_ledger/ledger.db` | SQLite database path |
| `API_BASE_URL` | `http://localhost:8000` | API URL for Streamlit UI |

### PostgreSQL Configuration

To use PostgreSQL instead of SQLite:

```bash
# Set connection string
export DATABASE_URL="postgresql://user:pass@localhost:5432/ledger"

# Initialize PostgreSQL database
uv run fol --database $DATABASE_URL init
```

## Development Commands

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_entities.py

# Run tests matching pattern
uv run pytest -k "test_transaction"
```

### Type Checking

```bash
# Check all source files
uv run mypy src/

# Check specific module
uv run mypy src/family_office_ledger/services/
```

### Linting

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Project Structure After Setup

```
~/.family_office_ledger/
└── ledger.db              # Default SQLite database

./
├── .venv/                 # Virtual environment (created by uv)
├── src/                   # Source code
├── tests/                 # Test files
└── specs/                 # Documentation (this folder)
```

## Common Issues

### Import Errors for Streamlit/Pandas

These are optional dependencies. Install with:
```bash
uv sync --dev --extra frontend
```

### PostgreSQL Connection Errors

1. Verify PostgreSQL is running: `pg_isready`
2. Check connection string format
3. Ensure database exists: `createdb ledger`

### mypy Errors in Tests

Test files have relaxed typing. Errors in test files are expected and do not affect production code.

## Quick Start Workflow

```bash
# 1. Setup
uv sync --dev --extra frontend
uv run fol init

# 2. Create sample data
uv run fol entity create "Smith Family LLC" --type llc
uv run fol account create "Operating Account" \
    --entity-id <entity-id> \
    --type asset \
    --sub-type checking

# 3. Start UI
uv run fol ui
```
