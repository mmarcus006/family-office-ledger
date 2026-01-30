# Technology Stack

## Core Language

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.12+ | Primary language with type hints and modern features |

## Frameworks & Libraries

### Core Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| **FastAPI** | >=0.109.0 | REST API framework |
| **Pydantic** | >=2.5.0 | Data validation and serialization |
| **SQLAlchemy** | >=2.0.0 | SQL toolkit (raw SQL, not ORM) |
| **uvicorn** | >=0.27.0 | ASGI server for FastAPI |
| **psycopg2-binary** | >=2.9.11 | PostgreSQL driver |
| **openpyxl** | >=3.1.5 | Excel file parsing |

### Optional Frontend Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| **Streamlit** | >=1.40.0 | Web UI framework |
| **Plotly** | >=5.18 | Interactive charts |
| **Pandas** | >=2.0 | Data manipulation |
| **httpx** | >=0.27 | HTTP client for API calls |

### Development Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| **pytest** | >=8.0.0 | Testing framework |
| **pytest-cov** | >=4.1.0 | Coverage reporting |
| **pytest-asyncio** | >=0.23.0 | Async test support |
| **mypy** | >=1.8.0 | Static type checking |
| **ruff** | >=0.2.0 | Linting and formatting |
| **pre-commit** | >=3.6.0 | Git hooks |
| **httpx** | >=0.26.0 | HTTP client for testing |
| **types-psycopg2** | >=2.9.21 | Type stubs for psycopg2 |

## Database Support

| Database | Status | Usage |
|----------|--------|-------|
| **SQLite** | Primary | Default for CLI and development |
| **PostgreSQL** | Optional | Production deployments |

## Build & Package Management

| Tool | Purpose |
|------|---------|
| **uv** | Package manager (replaces pip) |
| **hatchling** | Build backend |

## Code Quality Configuration

### Mypy (Type Checking)
- `strict = true`
- `python_version = "3.12"`
- All strict checking options enabled
- Relaxed rules for tests and Streamlit modules

### Ruff (Linting)
- Line length: 88 characters
- Target: Python 3.12
- Rules: E, F, I, N, UP, B, C4, SIM
- isort integration for import sorting

### Coverage
- Branch coverage enabled
- Excludes: `__repr__`, `NotImplementedError`, `TYPE_CHECKING`, `@abstractmethod`

## Architecture Patterns

| Pattern | Implementation |
|---------|----------------|
| **Layered Architecture** | domain → repositories → services → api/cli |
| **Repository Pattern** | Abstract interfaces with SQLite/Postgres implementations |
| **Dependency Injection** | Interface-based with factory functions |
| **Value Objects** | Frozen dataclasses (Money, Quantity) |
| **Domain Events** | Audit trail via AuditEntry |
