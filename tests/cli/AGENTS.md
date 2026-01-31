<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# cli

## Purpose
Tests for the CLI module structure, verifying command organization and backward compatibility.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Test package marker |
| `test_cli_module_structure.py` | Tests verifying CLI module organization (5.8KB) |

## For AI Agents

### Working In This Directory
- Tests focus on module structure and exports
- Functional CLI tests are in parent `tests/test_cli.py`
- Verify backward compatibility when refactoring CLI

### Testing Patterns
```python
from typer.testing import CliRunner
from family_office_ledger.cli import main

runner = CliRunner()

def test_command_exists():
    result = runner.invoke(main, ["--help"])
    assert "command-name" in result.output
```

## Dependencies

### Internal
- Tests `src/family_office_ledger/cli/`

### External
- `pytest` - Test framework
- `typer` - CLI framework (includes testing utilities)

<!-- MANUAL: -->
