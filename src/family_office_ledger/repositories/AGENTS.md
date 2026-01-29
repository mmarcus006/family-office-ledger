# REPOSITORIES LAYER

## OVERVIEW
Persistence interfaces and implementations for SQLite and PostgreSQL.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Interfaces | interfaces.py | 8 ABCs (Entity, Account, Security, Position, Transaction, TaxLot, ReconciliationSession) |
| SQLite | sqlite.py | 1232 lines, 8 repository classes |
| Postgres | postgres.py | 1285 lines, mirrors SQLite implementation |
| Public exports | __init__.py | optional Postgres via try/except |

## CONVENTIONS
- Interface names: `EntityRepository`, `AccountRepository`, etc.
- Implementations prefixed by backend: `SQLite*`, `Postgres*`
- Database wrappers: `SQLiteDatabase`, `PostgresDatabase`
- Each repository: 9-10 methods (CRUD + queries)
- Row mapping via `_row_to_*()` methods

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- sqlite.py and postgres.py are 95% identical (SQL syntax differs)
- Postgres optional: conditional import in __init__.py
- Schema in `initialize()` method (~150 lines CREATE TABLE)
- ReconciliationSession uses cascade delete for matches
