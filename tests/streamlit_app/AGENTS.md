<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# streamlit_app

## Purpose
Tests for the Streamlit frontend application, including API client and page rendering.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Test package marker |
| `conftest.py` | Pytest fixtures for Streamlit testing (2.4KB) |
| `test_streamlit_api_client.py` | Tests for API client wrapper (9.8KB) |
| `test_streamlit_pages.py` | Tests for Streamlit page components (11KB) |

## For AI Agents

### Working In This Directory
- Streamlit testing requires mocking `st` module
- API client tests mock HTTP responses
- Page tests verify rendering and interactions

### Testing Patterns
```python
from unittest.mock import patch, MagicMock
import pytest

@pytest.fixture
def mock_api_client():
    with patch("family_office_ledger.streamlit_app.api_client.httpx") as mock:
        yield mock

def test_page_renders(mock_api_client):
    mock_api_client.get.return_value = MagicMock(json=lambda: {...})
    # ... test page
```

### Common Fixtures (conftest.py)
- Mock API responses
- Mock Streamlit session state
- Test database setup

## Dependencies

### Internal
- Tests `src/family_office_ledger/streamlit_app/`

### External
- `pytest` - Test framework
- `httpx` - HTTP client (mocked)

<!-- MANUAL: -->
