# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-29
**Commit:** 7449801
**Branch:** main

## OVERVIEW
Python 3.12+ family office ledger with FastAPI API, SQLite/Postgres repositories, double-entry accounting domain, and NiceGUI frontend.

## STRUCTURE
```
./
├── src/family_office_ledger/    # package root (layered architecture)
│   ├── domain/                  # entities, transactions, value objects
│   ├── services/                # business logic (ingestion, reconciliation, reporting)
│   ├── repositories/            # SQLite + Postgres persistence
│   ├── parsers/                 # CSV/OFX/bank statement parsing
│   ├── api/                     # FastAPI REST endpoints
│   ├── ui/                      # NiceGUI frontend (optional)
│   └── cli.py                   # `fol` CLI entry point
├── tests/                       # pytest suite (660 tests)
├── pyproject.toml               # tooling config (ruff, mypy, pytest)
└── .sisyphus/                   # planning artifacts
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| CLI commands | src/family_office_ledger/cli.py | `fol init/status/ingest/reconcile/ui` |
| FastAPI app | src/family_office_ledger/api/app.py | `create_app()` factory |
| API routes | src/family_office_ledger/api/routes.py | 6 routers, 50+ endpoints |
| Domain models | src/family_office_ledger/domain/ | dataclasses + value objects |
| Business logic | src/family_office_ledger/services/ | ingestion, reconciliation, reporting |
| Persistence | src/family_office_ledger/repositories/ | SQLite/Postgres implementations |
| Bank parsing | src/family_office_ledger/parsers/ | CITI/UBS/MorganStanley parsers |
| Frontend | src/family_office_ledger/ui/ | NiceGUI pages/components |
| Tests | tests/ | 30 modules, fixtures in conftest.py |

## CODE MAP
- CLI: `fol = family_office_ledger.cli:main`
- API: `family_office_ledger.api.app:app` (uvicorn entry)
- UI: `family_office_ledger.ui.main:run` (NiceGUI entry)
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
- None documented.

## UNIQUE STYLES
- `__init__.py` files curate public exports via `__all__`
- Postgres support is optional (conditional import)
- Uses `uv` package manager
- Repository interfaces in `interfaces.py`; implementations in `sqlite.py`/`postgres.py`

## COMMANDS
```bash
uv sync --dev                    # install dependencies
uv run pytest                    # run tests (660 passing)
uv run mypy src/                 # type checking
uv run ruff check .              # linting
uv run fol --help                # CLI help
uv run fol reconcile --help      # reconciliation commands
uvicorn family_office_ledger.api.app:app  # start API server
```

## NOTES
- Default SQLite DB: `~/.family_office_ledger/ledger.db` (CLI) or `family_office_ledger.db` (API)
- Reconciliation workflow: create session → list matches → confirm/reject/skip → close
- Large files (>500 lines): ingestion.py, sqlite.py, postgres.py, reconciliation.py, routes.py
