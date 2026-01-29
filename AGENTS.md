# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-29
**Commit:** 115c72f
**Branch:** main

## OVERVIEW
Python 3.12+ family office ledger with FastAPI API, SQLite/Postgres repositories, double-entry accounting domain, NiceGUI + Streamlit frontends. Features: multi-currency, expense tracking, budgeting.

## STRUCTURE
```
./
├── src/family_office_ledger/    # package root (layered architecture)
│   ├── domain/                  # entities, transactions, value objects (13 files)
│   ├── services/                # business logic (17 services)
│   ├── repositories/            # SQLite + Postgres persistence (11 repos)
│   ├── parsers/                 # CSV/OFX/bank statement parsing
│   ├── api/                     # FastAPI REST endpoints (15 routers)
│   ├── ui/                      # NiceGUI frontend (optional)
│   ├── streamlit_app/           # Streamlit frontend (12 pages)
│   └── cli.py                   # `fol` CLI entry point
├── tests/                       # pytest suite (1145 tests)
├── pyproject.toml               # tooling config (ruff, mypy, pytest)
└── .sisyphus/                   # planning artifacts
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| CLI commands | cli.py | `fol init/status/ingest/reconcile/transfer/qsbs/tax/portfolio/currency/expense/vendor/budget/audit/ui` |
| FastAPI app | api/app.py | `create_app()` factory |
| API routes | api/routes.py | 15 routers, 80+ endpoints |
| Domain models | domain/ | dataclasses + value objects |
| Business logic | services/ | 17 services (ingestion, reconciliation, reporting, budgeting, etc.) |
| Persistence | repositories/ | SQLite/Postgres implementations (11 repos each) |
| Bank parsing | parsers/ | CITI/UBS/MorganStanley parsers |
| NiceGUI UI | ui/ | NiceGUI pages/components (dev) |
| Streamlit UI | streamlit_app/ | 12 pages, Quicken-style theme (production) |
| Tests | tests/ | 54 modules, fixtures in conftest.py |

## CODE MAP
- CLI: `fol = family_office_ledger.cli:main`
- API: `family_office_ledger.api.app:app` (uvicorn entry)
- NiceGUI: `family_office_ledger.ui.main:run` (not wired to CLI)
- Streamlit: `fol ui` launches streamlit_app/app.py
- Public exports: `family_office_ledger.__init__` (Account, Entity, Transaction, Money, Budget, etc.)

## CONVENTIONS
- Strict mypy (`strict = true`); tests relax typing rules
- Ruff linting: E/F/I/N/UP/B/C4/SIM, 88-char lines
- `src/` layout; absolute imports from `family_office_ledger`
- Layered architecture: domain → repositories → services → api/cli
- Service classes use `*Impl` suffix
- Enums inherit from `str, Enum` for JSON serialization
- Value objects are `frozen=True` dataclasses
- Repository interfaces in `interfaces.py`; implementations in `sqlite.py`/`postgres.py`

## ANTI-PATTERNS (THIS PROJECT)
- **sqlite.py/postgres.py**: 95% code duplication (~3700 lines total) - only SQL placeholders differ
- **routes.py**: 2489 lines, 80+ endpoints in single file - split into router modules candidate
- **cli.py**: 2714 lines, 47 subcommands in single file - split into command modules candidate

## UNIQUE STYLES
- `__init__.py` files curate public exports via `__all__`
- Postgres support is optional (conditional import)
- Uses `uv` package manager
- Dual frontend: NiceGUI (dev, incomplete) + Streamlit (production-ready)
- No `__main__.py` - only `fol` CLI entry point

## COMMANDS
```bash
uv sync --dev                    # install dependencies
uv run pytest                    # run tests (1145 passing)
uv run mypy src/                 # type checking
uv run ruff check .              # linting
uv run fol --help                # CLI help
uv run fol ui                    # launch Streamlit UI
uvicorn family_office_ledger.api.app:app  # start API server
```

## NOTES
- Default SQLite DB: `~/.family_office_ledger/ledger.db` (CLI) or `family_office_ledger.db` (API)
- Reconciliation workflow: create session → list matches → confirm/reject/skip → close
- Large files (>500 lines): cli.py, routes.py, sqlite.py, postgres.py, ingestion.py, reconciliation.py, reporting.py
- Test count: 1145 tests (94 Postgres tests skipped if psycopg2 not installed)
- Financial features: multi-currency (132 tests), expense tracking (102 tests), budgeting (91 tests)
