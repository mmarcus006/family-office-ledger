"""FastAPI application factory and dependency injection setup."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from family_office_ledger.api.routes import (
    account_router,
    audit_router,
    budget_router,
    currency_router,
    entity_router,
    expense_router,
    health_router,
    household_router,
    ownership_router,
    portfolio_router,
    qsbs_router,
    reconciliation_router,
    report_router,
    tax_router,
    transaction_router,
    transfer_router,
    vendor_router,
)
from family_office_ledger.config import get_settings
from family_office_ledger.container import get_container, get_database, reset_container
from family_office_ledger.exceptions import FamilyOfficeLedgerError
from family_office_ledger.logging_config import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
)
from family_office_ledger.repositories.sqlite import SQLiteDatabase

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown.

    Initializes logging and the DI container on startup,
    cleans up resources on shutdown.
    """
    settings = get_settings()
    configure_logging(settings)

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment.value,
    )

    # Initialize the container (and database)
    container = get_container()
    _ = container.database  # Force database initialization

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("application_stopping")
    reset_container()
    logger.info("application_stopped")


def get_db() -> SQLiteDatabase:
    """Get the database instance (legacy compatibility).

    This function is used as a FastAPI dependency and can be overridden
    in tests using app.dependency_overrides.

    Prefer using get_database() from container module for new code.
    """
    db = get_database()
    # Type narrowing for backward compatibility
    if isinstance(db, SQLiteDatabase):
        return db
    # For Postgres, this would need different handling
    # For now, assume SQLite for backward compatibility
    return db  # type: ignore


async def log_request_middleware(request: Request, call_next):
    """Middleware to add request context to logs."""
    request_id = str(uuid.uuid4())[:8]
    bind_context(request_id=request_id, path=request.url.path, method=request.method)

    try:
        response = await call_next(request)
        logger.debug(
            "request_completed",
            status_code=response.status_code,
        )
        return response
    finally:
        clear_context()


async def exception_handler(
    request: Request, exc: FamilyOfficeLedgerError
) -> JSONResponse:
    """Handle domain exceptions and return appropriate JSON responses."""
    logger.warning(
        "domain_exception",
        error_code=exc.error_code,
        message=exc.message,
        context=exc.context,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Double-entry, multi-entity accounting and investment ledger for family offices",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Add middleware
    app.middleware("http")(log_request_middleware)

    # Add exception handlers
    app.add_exception_handler(FamilyOfficeLedgerError, exception_handler)

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
    app.include_router(budget_router)
    app.include_router(household_router)
    app.include_router(ownership_router)

    return app


# Create app instance for uvicorn
app = create_app()
