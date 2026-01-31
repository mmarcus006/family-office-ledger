<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# cli

## Purpose
Command-line interface for the Family Office Ledger. Provides the `fol` command with 47+ subcommands organized by domain.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Package exports - re-exports all command functions for backward compatibility |
| `_main.py` | Main CLI implementation (113KB) - Typer app with all commands |
| `budget_commands.py` | Budget management commands (create, list, add-line, variance, alerts) |
| `currency_commands.py` | Currency and exchange rate commands |
| `household_commands.py` | Household management commands |
| `qsbs_commands.py` | QSBS (Qualified Small Business Stock) tracking commands |
| `reconciliation_commands.py` | Bank reconciliation workflow commands |

## For AI Agents

### Working In This Directory
- **`_main.py` is very large (113KB)** - command logic is being extracted to `*_commands.py` modules
- New commands should be added to appropriate `*_commands.py` file
- Commands are registered with Typer's `@app.command()` decorator
- All commands use dependency injection via `container.py`

### Command Structure
```python
@app.command()
def command_name(
    ctx: typer.Context,
    arg: str = typer.Argument(...),
    option: str = typer.Option(None),
) -> None:
    """Command docstring shown in --help."""
    container = ctx.obj["container"]
    service = container.some_service
    # ... implementation
```

### Testing Requirements
- CLI tests in `tests/cli/`
- Use `CliRunner` from Typer for testing
- Mock database connections in tests

### Common Patterns
- Use `structlog` for logging
- Exit codes: 0=success, 1=error
- Output format: tables for lists, JSON for exports
- Date format: ISO 8601 (YYYY-MM-DD)

## Dependencies

### Internal
- `family_office_ledger.container` - Dependency injection container
- `family_office_ledger.services.*` - Business logic services
- `family_office_ledger.config` - Configuration settings

### External
- `typer` - CLI framework
- `rich` - Terminal formatting

<!-- MANUAL: -->
