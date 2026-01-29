# PACKAGE KNOWLEDGE BASE

## OVERVIEW
Package root for family office ledger; layers: domain → repositories → services → api/cli/ui.

## STRUCTURE
```
src/family_office_ledger/
├── domain/         # entities, transactions, reconciliation, value objects (12 files)
├── services/       # business logic (16 services)
├── repositories/   # persistence interfaces + SQLite/Postgres implementations
├── parsers/        # CSV/OFX/bank statement parsing
├── api/            # FastAPI app + routes + schemas
├── ui/             # NiceGUI frontend (optional)
├── streamlit_app/  # Streamlit frontend (12 pages)
├── cli.py          # CLI entry point (`fol` command, 1842 lines)
└── __init__.py     # curated public exports
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Public exports | __init__.py | curated `__all__` (Account, Entity, Transaction, Money...) |
| CLI commands | cli.py | init, status, ingest, reconcile (7), transfer (6), qsbs (2), tax, portfolio, currency, audit, ui |
| Domain models | domain/ | dataclasses with UUID ids, UTC timestamps |
| Services | services/ | 16 services, *Impl suffix, interface-based DI |
| Repositories | repositories/ | interfaces.py + sqlite.py/postgres.py |
| API | api/ | FastAPI factory, 12 routers |
| NiceGUI | ui/ | NiceGUI pages/components/state |
| Streamlit | streamlit_app/ | 12 pages, Quicken-style CSS |

## CONVENTIONS
- Absolute imports from `family_office_ledger`
- Interfaces in `interfaces.py` within services/repositories
- Service implementations use `*Impl` suffix
- `__init__.py` curates exports; update `__all__` when adding public symbols
- Exceptions defined in module where raised, re-exported via `__init__.py`

## ANTI-PATTERNS (THIS PROJECT)
- cli.py is monolithic (1842 lines) - split candidate

## NOTES
- Optional Postgres: gated in repositories/__init__.py
- Optional NiceGUI: gated in ui/__init__.py
- Optional Streamlit: gated in cli.py cmd_ui()
- Version string in __init__.py: `__version__ = "0.1.0"`
