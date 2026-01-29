# API LAYER

## OVERVIEW
FastAPI application with 6 routers and 50+ endpoints.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| App factory | app.py | `create_app()`, module-level `app` for uvicorn |
| Routes | routes.py | 745 lines, 6 routers |
| Schemas | schemas.py | Pydantic v2 request/response models |
| Public exports | __init__.py | `create_app` |

## ROUTERS
| Router | Prefix | Endpoints |
|--------|--------|-----------|
| health_router | /health | 1 |
| entity_router | /entities | 3 |
| account_router | /accounts | 2 |
| transaction_router | /transactions | 2 |
| report_router | /reports | 2 |
| reconciliation_router | /reconciliation | 10 |

## CONVENTIONS
- App via factory; module-level `app` for uvicorn
- Database dependency via `Depends(get_db)`
- Service instantiation via `get_*_service()` functions
- Response converters: `_*_to_response()` helpers
- Exception handling: domain exceptions → HTTP status codes

## ANTI-PATTERNS (THIS PROJECT)
- None documented.

## NOTES
- Default DB: `family_office_ledger.db` via SQLiteDatabase
- Reconciliation endpoints: create session, list matches, confirm/reject/skip, close, summary
- Amounts serialized as strings in JSON (Decimal precision)
