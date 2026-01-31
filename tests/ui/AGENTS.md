<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# ui

## Purpose
Tests for the NiceGUI frontend components, pages, and workflows.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Test package marker with skip reason |
| `conftest.py` | Pytest fixtures for UI testing (954B) |
| `test_api_client.py` | Tests for NiceGUI API client (3KB) |
| `test_components.py` | Tests for UI components (394B) |
| `test_pages.py` | Tests for page layouts (554B) |
| `test_workflows.py` | Tests for user workflows (262B) |

## For AI Agents

### Working In This Directory
- **NiceGUI UI is experimental** - tests are minimal
- Expand tests as NiceGUI frontend develops
- Mock API responses for isolated testing

### Testing Patterns
```python
from family_office_ledger.ui.components import my_component

def test_component_renders():
    # NiceGUI testing patterns TBD
    pass
```

### Current State
- Tests are placeholder/minimal
- Focus on Streamlit tests for production frontend

## Dependencies

### Internal
- Tests `src/family_office_ledger/ui/`

### External
- `pytest` - Test framework
- `nicegui` - UI framework (test utilities TBD)

<!-- MANUAL: -->
