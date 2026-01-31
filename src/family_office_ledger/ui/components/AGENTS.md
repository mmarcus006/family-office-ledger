<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# components

## Purpose
Reusable NiceGUI UI components for the alternative frontend. Contains building blocks for forms, tables, charts, navigation, and modals.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Component exports |
| `charts.py` | Chart components (placeholder) |
| `forms.py` | Form input components (1.5KB) |
| `modals.py` | Modal dialog components (1.4KB) |
| `nav.py` | Navigation components - sidebar, menu (2.5KB) |
| `tables.py` | Data table components (770B) |

## For AI Agents

### Working In This Directory
- **NiceGUI frontend is experimental** - Streamlit is production
- Components should be composable and reusable
- Follow NiceGUI patterns for state management

### Component Pattern
```python
from nicegui import ui

def my_component(data: dict) -> None:
    """Reusable component docstring."""
    with ui.card():
        ui.label(data["title"])
        # ... component content
```

### Testing Requirements
- Tests in `tests/ui/test_components.py`
- Components are currently minimal - expand as needed

## Dependencies

### Internal
- Uses domain models from `family_office_ledger.domain`

### External
- `nicegui` - UI framework

<!-- MANUAL: -->
