from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    PositionRepository,
    ReconciliationSessionRepository,
    SecurityRepository,
    TaxLotRepository,
    TransactionRepository,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteReconciliationSessionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)

__all__ = [
    "AccountRepository",
    "EntityRepository",
    "PositionRepository",
    "ReconciliationSessionRepository",
    "SecurityRepository",
    "TaxLotRepository",
    "TransactionRepository",
    "SQLiteAccountRepository",
    "SQLiteDatabase",
    "SQLiteEntityRepository",
    "SQLitePositionRepository",
    "SQLiteReconciliationSessionRepository",
    "SQLiteSecurityRepository",
    "SQLiteTaxLotRepository",
    "SQLiteTransactionRepository",
]

# PostgreSQL support is optional - only available if psycopg2 is installed
try:
    from family_office_ledger.repositories.postgres import (
        PostgresAccountRepository,
        PostgresDatabase,
        PostgresEntityRepository,
        PostgresPositionRepository,
        PostgresReconciliationSessionRepository,
        PostgresSecurityRepository,
        PostgresTaxLotRepository,
        PostgresTransactionRepository,
    )

    __all__ += [
        "PostgresAccountRepository",
        "PostgresDatabase",
        "PostgresEntityRepository",
        "PostgresPositionRepository",
        "PostgresReconciliationSessionRepository",
        "PostgresSecurityRepository",
        "PostgresTaxLotRepository",
        "PostgresTransactionRepository",
    ]
except ImportError:
    # psycopg2 not installed, PostgreSQL repositories not available
    pass
