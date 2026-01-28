# Atlas Family Office Ledger

A double-entry, multi-entity accounting and investment ledger for family offices.

## Features

- Multi-entity structure (LLCs, trusts, partnerships, holding companies)
- Double-entry journal with immutable transaction history
- Investment position and tax lot tracking
- Cost basis methods: FIFO, LIFO, Specific ID, Average Cost, Min/Max Gain
- Corporate action processing (splits, spinoffs, mergers)
- Reconciliation with imported bank/broker statements
- Consolidated reporting across entities

## Installation

```bash
uv sync --dev
```

## Usage

```bash
uv run fol --help
```

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check .
```

## License

MIT
