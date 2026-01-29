# TEST SUITE

## OVERVIEW
Pytest suite: 660 tests across 30 modules covering domain, services, repositories, parsers, API, CLI, and UI.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Shared fixtures | conftest.py | 10 domain fixtures (sample_entity, sample_account, etc.) |
| Domain tests | test_entities.py, test_value_objects.py, test_transactions.py | |
| Service tests | test_*_service.py | ingestion, ledger, reporting, reconciliation |
| Repository tests | test_repositories_sqlite.py, test_repositories_postgres.py | |
| Parser tests | test_parsers.py, test_bank_parsers.py | |
| API tests | test_api.py, test_reconciliation_api.py | FastAPI TestClient |
| CLI tests | test_cli.py, test_reconciliation_cli.py | |
| UI tests | ui/test_*.py | async tests with ASGITransport |

## CONVENTIONS
- Files: `test_*.py`; classes: `Test*`; methods: `test_*`
- Fixtures centralized in conftest.py; UI fixtures in ui/conftest.py
- Async tests: `asyncio_mode = "auto"` (no decorator needed)
- In-memory SQLite for all repo tests (`:memory:`)
- API tests use dependency overrides for DB injection

## TEST COUNTS
| Category | Tests |
|----------|-------|
| Reconciliation | 139 (6 test files) |
| Repositories | ~100 |
| Services | ~200 |
| Domain | ~100 |
| API | ~50 |
| CLI | ~50 |
| UI | ~20 |

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- Large test files: test_ingestion_service.py (1913 lines), test_repositories_postgres.py (1399 lines)
- Mypy relaxed for tests: `disallow_untyped_defs = false`
- Coverage configured in pyproject.toml with branch coverage
- Postgres tests skipped if psycopg2 not installed
