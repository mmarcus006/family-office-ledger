# REPOSITORIES LAYER

## OVERVIEW
Persistence interfaces and implementations for SQLite and PostgreSQL. 11 repository interfaces.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Interfaces | interfaces.py | 11 ABCs (Entity, Account, Security, Position, Transaction, TaxLot, ReconciliationSession, ExchangeRate, Vendor, Budget) |
| SQLite | sqlite.py | 1799 lines, 11 repository classes |
| Postgres | postgres.py | 1885 lines, mirrors SQLite implementation |
| Public exports | __init__.py | optional Postgres via try/except |

## CONVENTIONS
- Interface names: `EntityRepository`, `AccountRepository`, etc.
- Implementations prefixed by backend: `SQLite*`, `Postgres*`
- Database wrappers: `SQLiteDatabase`, `PostgresDatabase`
- Each repository: 7-10 methods (CRUD + queries)
- Row mapping via `_row_to_*()` methods

## REPOSITORY INTERFACES
| Interface | Methods | Notes |
|-----------|---------|-------|
| EntityRepository | 7 | add, get, get_by_name, list_all, list_active, update, delete |
| AccountRepository | 7 | add, get, get_by_name, list_by_entity, list_investment_accounts, update, delete |
| SecurityRepository | 8 | includes list_qsbs_eligible |
| PositionRepository | 7 | list_by_account, list_by_security, list_by_entity |
| TransactionRepository | 7 | list_by_date_range, get_reversals |
| TaxLotRepository | 7 | list_wash_sale_candidates, list_open_by_position |
| ReconciliationSessionRepository | 6 | get_pending_for_account |
| ExchangeRateRepository | 7 | get_rate, get_latest_rate, list_by_currency_pair |
| VendorRepository | 8 | get_by_tax_id, search_by_name, list_by_category |
| BudgetRepository | 10 | add, get, update, delete, list_by_entity, get_active_for_date, add/get/update/delete_line_item |

## ANTI-PATTERNS (THIS PROJECT)
- **CRITICAL**: sqlite.py and postgres.py are 95% identical (~3700 lines total) - only SQL syntax differs (`?` vs `%s`). Consolidation candidate.

## NOTES
- Postgres optional: conditional import in __init__.py
- Schema in `initialize()` method (~250 lines CREATE TABLE)
- ReconciliationSession uses cascade delete for matches
- Budget uses cascade delete for line items
- Uses `object.__setattr__()` to bypass frozen dataclass constraints during row mapping
- Schema evolution via `_add_migration_columns()` with `ALTER TABLE ADD COLUMN IF NOT EXISTS`
