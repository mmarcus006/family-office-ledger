<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# alembic

## Purpose
Database migration management using Alembic. Handles schema versioning and upgrades for both SQLite and PostgreSQL databases.

## Key Files

| File | Description |
|------|-------------|
| `env.py` | Alembic environment configuration - connects to app settings |
| `script.py.mako` | Template for generating new migration scripts |
| `README` | Brief Alembic instructions |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `versions/` | Individual migration scripts (chronologically ordered) |

## For AI Agents

### Working In This Directory
- **Never modify `env.py`** unless changing database connection logic
- New migrations go in `versions/` with auto-generated revision IDs
- Use `uv run alembic revision -m "description"` to create new migrations
- Use `uv run alembic upgrade head` to apply migrations

### Migration Patterns
- Migrations use raw SQL (no ORM models defined yet)
- `render_as_batch=True` enabled for SQLite ALTER TABLE support
- Both offline and online migration modes supported

### Testing Requirements
- Test migrations on SQLite first (default)
- PostgreSQL migrations may need different syntax

## Dependencies

### Internal
- `family_office_ledger.config` - Database URL from settings

### External
- `alembic` - Migration framework
- `sqlalchemy` - Database engine

<!-- MANUAL: -->
