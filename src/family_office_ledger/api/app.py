"""FastAPI application factory and dependency injection setup."""

from fastapi import FastAPI

from family_office_ledger.api.routes import (
    account_router,
    audit_router,
    currency_router,
    entity_router,
    expense_router,
    health_router,
    portfolio_router,
    qsbs_router,
    reconciliation_router,
    report_router,
    tax_router,
    transaction_router,
    transfer_router,
    vendor_router,
)
from family_office_ledger.repositories.sqlite import SQLiteDatabase

# Global database instance (can be overridden for testing)
_database: SQLiteDatabase | None = None


def get_db() -> SQLiteDatabase:
    """Get the database instance.

    This function is used as a FastAPI dependency and can be overridden
    in tests using app.dependency_overrides.
    """
    global _database
    if _database is None:
        _database = SQLiteDatabase("family_office_ledger.db")
        _database.initialize()
    return _database


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Family Office Ledger API",
        description="Double-entry, multi-entity accounting and investment ledger for family offices",
        version="0.1.0",
    )

    # Add dependency override mechanism for get_db
    # Routes will use Depends() to get the database
    app.dependency_overrides[SQLiteDatabase] = get_db

    # Include routers
    app.include_router(health_router)
    app.include_router(entity_router)
    app.include_router(account_router)
    app.include_router(transaction_router)
    app.include_router(report_router)
    app.include_router(reconciliation_router)
    app.include_router(transfer_router)
    app.include_router(qsbs_router)
    app.include_router(tax_router)
    app.include_router(portfolio_router)
    app.include_router(audit_router)
    app.include_router(currency_router)
    app.include_router(expense_router)
    app.include_router(vendor_router)

    return app


# Create app instance for uvicorn
app = create_app()
