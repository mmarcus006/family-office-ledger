"""Dependency injection container for Family Office Ledger.

Provides centralized dependency management using a simple container pattern.
This allows for:
- Easy testing through dependency replacement
- Configuration-driven service instantiation
- Lazy initialization of expensive resources
- Clean separation of concerns

Usage:
    from family_office_ledger.container import Container, get_container

    # Get container singleton
    container = get_container()

    # Access services
    db = container.database
    ledger = container.ledger_service
"""

from functools import cached_property, lru_cache
from typing import TYPE_CHECKING

from family_office_ledger.config import DatabaseType, Settings, get_settings
from family_office_ledger.logging_config import get_logger

if TYPE_CHECKING:
    from family_office_ledger.repositories.interfaces import LedgerRepository
    from family_office_ledger.services.audit import AuditService
    from family_office_ledger.services.ledger import LedgerService
    from family_office_ledger.services.lot_matching import LotMatchingService
    from family_office_ledger.services.qsbs import QSBSService
    from family_office_ledger.services.reconciliation import ReconciliationService
    from family_office_ledger.services.reporting import ReportingService

logger = get_logger(__name__)


class Container:
    """Dependency injection container.

    Provides lazy-loaded access to all application services and repositories.
    Services are instantiated on first access and cached for reuse.

    The container can be configured with custom settings for testing:

        test_settings = Settings(database_type=DatabaseType.SQLITE, sqlite_path=":memory:")
        container = Container(settings=test_settings)
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the container.

        Args:
            settings: Application settings. If None, loads from environment.
        """
        self._settings = settings or get_settings()
        self._database: LedgerRepository | None = None
        self._initialized = False
        logger.debug(
            "container_created",
            database_type=self._settings.database_type.value,
            environment=self._settings.environment.value,
        )

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings

    @cached_property
    def database(self) -> "LedgerRepository":
        """Get the database repository.

        Returns appropriate repository based on configuration:
        - SQLite for development/testing
        - PostgreSQL for production

        The database is initialized on first access.
        """
        if self._settings.database_type == DatabaseType.POSTGRES:
            return self._create_postgres_database()
        return self._create_sqlite_database()

    def _create_sqlite_database(self) -> "LedgerRepository":
        """Create and initialize SQLite database."""
        from family_office_ledger.repositories.sqlite import SQLiteDatabase

        db_path = str(self._settings.sqlite_path)
        logger.info("initializing_sqlite_database", path=db_path)

        db = SQLiteDatabase(db_path)
        db.initialize()
        return db

    def _create_postgres_database(self) -> "LedgerRepository":
        """Create and initialize PostgreSQL database."""
        from family_office_ledger.repositories.postgres import PostgresDatabase

        url = self._settings.database_url
        if not url:
            raise ValueError(
                "database_url must be set when database_type is postgres"
            )

        logger.info(
            "initializing_postgres_database",
            # Don't log the full URL as it may contain credentials
            host=url.split("@")[-1].split("/")[0] if "@" in url else "localhost",
        )

        db = PostgresDatabase(url)
        db.initialize()
        return db

    @cached_property
    def ledger_service(self) -> "LedgerService":
        """Get the ledger service for transaction management."""
        from family_office_ledger.services.ledger import LedgerService

        return LedgerService(self.database)

    @cached_property
    def lot_matching_service(self) -> "LotMatchingService":
        """Get the lot matching service for tax lot selection."""
        from family_office_ledger.services.lot_matching import LotMatchingService

        return LotMatchingService(self.database)

    @cached_property
    def qsbs_service(self) -> "QSBSService":
        """Get the QSBS service for Section 1202/1045 tracking."""
        from family_office_ledger.services.qsbs import QSBSService

        return QSBSService(self.database)

    @cached_property
    def reconciliation_service(self) -> "ReconciliationService":
        """Get the reconciliation service for bank statement matching."""
        from family_office_ledger.services.reconciliation import ReconciliationService

        return ReconciliationService(self.database)

    @cached_property
    def reporting_service(self) -> "ReportingService":
        """Get the reporting service for financial reports."""
        from family_office_ledger.services.reporting import ReportingService

        return ReportingService(self.database)

    @cached_property
    def audit_service(self) -> "AuditService":
        """Get the audit service for change tracking."""
        from family_office_ledger.services.audit import AuditService

        return AuditService(self.database)

    def close(self) -> None:
        """Close all resources held by the container.

        Should be called during application shutdown.
        """
        if self._database is not None:
            logger.info("closing_database_connection")
            # The database may have a close method
            if hasattr(self._database, "close"):
                self._database.close()  # type: ignore

    def __enter__(self) -> "Container":
        """Enter context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager, closing resources."""
        self.close()


# Module-level container instance
_container: Container | None = None


@lru_cache
def get_container() -> Container:
    """Get the global container singleton.

    The container is created lazily on first access using default settings.
    For testing, create a Container directly with custom settings instead
    of using this function.

    Returns:
        Global Container instance.
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Reset the global container.

    Used primarily for testing to ensure a fresh container state.
    """
    global _container
    if _container is not None:
        _container.close()
        _container = None
    get_container.cache_clear()


# FastAPI dependency functions
def get_database() -> "LedgerRepository":
    """FastAPI dependency for database access.

    Usage in routes:
        @router.get("/entities")
        def list_entities(db: LedgerRepository = Depends(get_database)):
            return db.get_entities()
    """
    return get_container().database


def get_ledger_service() -> "LedgerService":
    """FastAPI dependency for ledger service."""
    return get_container().ledger_service


def get_qsbs_service() -> "QSBSService":
    """FastAPI dependency for QSBS service."""
    return get_container().qsbs_service


def get_reconciliation_service() -> "ReconciliationService":
    """FastAPI dependency for reconciliation service."""
    return get_container().reconciliation_service


def get_reporting_service() -> "ReportingService":
    """FastAPI dependency for reporting service."""
    return get_container().reporting_service


def get_audit_service() -> "AuditService":
    """FastAPI dependency for audit service."""
    return get_container().audit_service
