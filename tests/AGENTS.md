# TEST SUITE

## OVERVIEW
Pytest suite: 1145 tests across 54 modules covering domain, services, repositories, parsers, API, CLI, and UI.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Shared fixtures | conftest.py | 10 domain fixtures (sample_entity, sample_account, etc.) |
| Domain tests | test_entities.py, test_value_objects.py, test_transactions.py | |
| Service tests | test_*_service.py | ingestion, ledger, reporting, reconciliation, lot_matching, corporate_action, budget |
| Repository tests | test_repositories_sqlite.py, test_repositories_postgres.py, test_budget_repository.py | |
| Parser tests | test_parsers.py, test_bank_parsers.py | |
| API tests | test_api.py, test_reconciliation_api.py, test_currency_api.py, test_budget_api.py | FastAPI TestClient |
| CLI tests | test_cli.py, test_reconciliation_cli.py, test_currency_cli.py, test_budget_cli.py | |
| UI tests | ui/test_*.py | async tests with ASGITransport |
| Streamlit tests | streamlit_app/test_*.py | mock-based tests |

## CONVENTIONS
- Files: `test_*.py`; classes: `Test*`; methods: `test_*`
- Fixtures centralized in conftest.py; UI fixtures in ui/conftest.py
- Async tests: `asyncio_mode = "auto"` (no decorator needed)
- In-memory SQLite for all repo tests (`:memory:`)
- API tests use dependency overrides for DB injection
- Streamlit tests use MagicMock for st module

## TEST COUNTS
| Category | Tests |
|----------|-------|
| Reconciliation | ~150 |
| Repositories | ~180 |
| Services | ~280 |
| Domain | ~120 |
| API | ~120 |
| CLI | ~120 |
| UI/Streamlit | ~60 |
| Currency/Exchange | ~132 |
| Expense | ~102 |
| Budget | ~91 |

## FIXTURE PATTERNS
```python
# Domain fixtures (conftest.py)
@pytest.fixture
def sample_entity() -> Entity: ...

# Chained fixtures
@pytest.fixture
def sample_account(sample_entity: Entity) -> Account: ...

# In-memory DB (conftest.py or test files)
@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database

# API client (ui/conftest.py)
@pytest.fixture
async def api_client(api_app):
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as c:
        yield LedgerAPIClient(base_url="http://test", client=c)
```

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- Large test files: test_ingestion_service.py (1913 lines), test_repositories_postgres.py (2165 lines)
- Mypy relaxed for tests: `disallow_untyped_defs = false`
- Coverage configured in pyproject.toml with branch coverage
- Postgres tests skipped if psycopg2 not installed (94 tests)
- Streamlit tests use mock httpx.Client that routes to TestClient
