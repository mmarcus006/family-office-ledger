from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    HouseholdRepository,
    PositionRepository,
    ReconciliationSessionRepository,
    SecurityRepository,
    TaxLotRepository,
    TransactionRepository,
    VendorRepository,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteHouseholdRepository,
    SQLitePositionRepository,
    SQLiteReconciliationSessionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)

__all__ = [
    "AccountRepository",
    "EntityRepository",
    "HouseholdRepository",
    "PositionRepository",
    "ReconciliationSessionRepository",
    "SecurityRepository",
    "TaxLotRepository",
    "TransactionRepository",
    "VendorRepository",
    "SQLiteAccountRepository",
    "SQLiteDatabase",
    "SQLiteEntityRepository",
    "SQLiteHouseholdRepository",
    "SQLitePositionRepository",
    "SQLiteReconciliationSessionRepository",
    "SQLiteSecurityRepository",
    "SQLiteTaxLotRepository",
    "SQLiteTransactionRepository",
    "SQLiteVendorRepository",
]

# PostgreSQL support is optional - only available if psycopg2 is installed
try:
    from family_office_ledger.repositories.postgres import (
        PostgresAccountRepository,
        PostgresDatabase,
        PostgresEntityRepository,
        PostgresHouseholdRepository,
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
        "PostgresHouseholdRepository",
        "PostgresPositionRepository",
        "PostgresReconciliationSessionRepository",
        "PostgresSecurityRepository",
        "PostgresTaxLotRepository",
        "PostgresTransactionRepository",
    ]
except ImportError:
    pass
