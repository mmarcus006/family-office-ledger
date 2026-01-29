# API LAYER

## OVERVIEW
FastAPI application with 15 routers and 80+ endpoints.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| App factory | app.py | `create_app()`, module-level `app` for uvicorn |
| Routes | routes.py | 2489 lines, 15 routers |
| Schemas | schemas.py | 724 lines, Pydantic v2 request/response models |
| Public exports | __init__.py | `create_app` |

## ROUTERS
| Router | Prefix | Endpoints |
|--------|--------|-----------|
| health_router | /health | 1 |
| entity_router | /entities | 3 |
| account_router | /accounts | 2 |
| transaction_router | /transactions | 2 |
| report_router | /reports | 6 |
| reconciliation_router | /reconciliation | 10 |
| transfer_router | /transfers | 7 |
| qsbs_router | /qsbs | 4 |
| tax_router | /tax | 4 |
| portfolio_router | /portfolio | 4 |
| audit_router | /audit | 4 |
| currency_router | /currency | 6 |
| expense_router | /expenses | 5 |
| vendor_router | /vendors | 6 |
| budget_router | /budgets | 9 |

## CONVENTIONS
- App via factory; module-level `app` for uvicorn
- Database dependency via `Depends(get_db)`
- Service instantiation via `get_*_service()` functions
- Response converters: `_*_to_response()` helpers
- Exception handling: domain exceptions → HTTP status codes

## ANTI-PATTERNS (THIS PROJECT)
- **HIGH**: routes.py is 2489 lines with 80+ endpoints in single file - split into router modules candidate

## NOTES
- Default DB: `family_office_ledger.db` via SQLiteDatabase
- Amounts serialized as strings in JSON (Decimal precision)
- 15+ `get_*_service()` factory functions for DI
- 20+ `_*_to_response()` converter functions
- Budget endpoints: CRUD, line items, variance, alerts
