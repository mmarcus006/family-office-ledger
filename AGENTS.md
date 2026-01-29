# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-29
**Commit:** af61e5b
**Branch:** main

## OVERVIEW
Python 3.12+ family office ledger with FastAPI API, SQLite/Postgres repositories, double-entry accounting domain, NiceGUI + Streamlit frontends.

## STRUCTURE
```
./
├── src/family_office_ledger/    # package root (layered architecture)
│   ├── domain/                  # entities, transactions, value objects (12 files)
│   ├── services/                # business logic (16 services)
│   ├── repositories/            # SQLite + Postgres persistence
│   ├── parsers/                 # CSV/OFX/bank statement parsing
│   ├── api/                     # FastAPI REST endpoints (12 routers)
│   ├── ui/                      # NiceGUI frontend (optional)
│   ├── streamlit_app/           # Streamlit frontend (12 pages)
│   └── cli.py                   # `fol` CLI entry point
├── tests/                       # pytest suite (961 tests)
├── pyproject.toml               # tooling config (ruff, mypy, pytest)
└── .sisyphus/                   # planning artifacts
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| CLI commands | src/family_office_ledger/cli.py | `fol init/status/ingest/reconcile/transfer/qsbs/tax/portfolio/currency/audit/ui` |
| FastAPI app | src/family_office_ledger/api/app.py | `create_app()` factory |
| API routes | src/family_office_ledger/api/routes.py | 12 routers, 70+ endpoints |
| Domain models | src/family_office_ledger/domain/ | dataclasses + value objects |
| Business logic | src/family_office_ledger/services/ | 16 services (ingestion, reconciliation, reporting, etc.) |
| Persistence | src/family_office_ledger/repositories/ | SQLite/Postgres implementations |
| Bank parsing | src/family_office_ledger/parsers/ | CITI/UBS/MorganStanley parsers |
| NiceGUI UI | src/family_office_ledger/ui/ | NiceGUI pages/components |
| Streamlit UI | src/family_office_ledger/streamlit_app/ | 12 pages, Quicken-style theme |
| Tests | tests/ | 46 modules, fixtures in conftest.py |

## CODE MAP
- CLI: `fol = family_office_ledger.cli:main`
- API: `family_office_ledger.api.app:app` (uvicorn entry)
- NiceGUI: `family_office_ledger.ui.main:run`
- Streamlit: `fol ui` launches streamlit_app/app.py
- Public exports: `family_office_ledger.__init__` (Account, Entity, Transaction, Money, etc.)

## CONVENTIONS
- Strict mypy (`strict = true`); tests relax typing rules
- Ruff linting: E/F/I/N/UP/B/C4/SIM, 88-char lines
- `src/` layout; absolute imports from `family_office_ledger`
- Layered architecture: domain → repositories → services → api/cli
- Service classes use `*Impl` suffix
- Enums inherit from `str, Enum` for JSON serialization
- Value objects are `frozen=True` dataclasses

## ANTI-PATTERNS (THIS PROJECT)
- **sqlite.py/postgres.py**: 95% code duplication (SQL syntax only differs) - consolidation candidate
- **routes.py**: 1904 lines, 70+ endpoints in single file - split into router modules candidate
- **cli.py**: 1842 lines, 35 subcommands in single file - split into command modules candidate

## UNIQUE STYLES
- `__init__.py` files curate public exports via `__all__`
- Postgres support is optional (conditional import)
- Uses `uv` package manager
- Repository interfaces in `interfaces.py`; implementations in `sqlite.py`/`postgres.py`
- Dual frontend: NiceGUI (dev) + Streamlit (production-ready)

## COMMANDS
```bash
uv sync --dev                    # install dependencies
uv run pytest                    # run tests (961 passing)
uv run mypy src/                 # type checking
uv run ruff check .              # linting
uv run fol --help                # CLI help
uv run fol ui                    # launch Streamlit UI
uvicorn family_office_ledger.api.app:app  # start API server
```

## NOTES
- Default SQLite DB: `~/.family_office_ledger/ledger.db` (CLI) or `family_office_ledger.db` (API)
- Reconciliation workflow: create session → list matches → confirm/reject/skip → close
- Large files (>500 lines): ingestion.py, sqlite.py, postgres.py, reconciliation.py, routes.py, cli.py
- Test count: 961 tests (80 Postgres tests skipped if psycopg2 not installed)
