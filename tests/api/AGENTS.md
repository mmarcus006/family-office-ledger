<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# api

## Purpose
Tests for the FastAPI REST API layer, focusing on route structure and module organization.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Test package marker |
| `test_routes_module_structure.py` | Tests verifying API route organization and structure (3.5KB) |

## For AI Agents

### Working In This Directory
- Tests focus on API structure rather than functionality
- Functional API tests are in parent `tests/test_api.py`
- Use `httpx.AsyncClient` with `TestClient` for API testing

### Testing Patterns
```python
from fastapi.testclient import TestClient
from family_office_ledger.api.app import create_app

def test_route_exists():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/endpoint")
    assert response.status_code != 404
```

## Dependencies

### Internal
- Tests `src/family_office_ledger/api/`

### External
- `pytest` - Test framework
- `httpx` - Async HTTP client

<!-- MANUAL: -->
