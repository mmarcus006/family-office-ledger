"""PostgreSQL implementations of repository interfaces."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg2
import psycopg2.extras

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.exchange_rates import ExchangeRate, ExchangeRateSource
from family_office_ledger.domain.reconciliation import (
    ReconciliationMatch,
    ReconciliationMatchStatus,
    ReconciliationSession,
    ReconciliationSessionStatus,
)
from family_office_ledger.domain.transactions import Entry, TaxLot, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AcquisitionType,
    AssetClass,
    EntityType,
    Money,
    Quantity,
)
from family_office_ledger.domain.vendors import Vendor
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    ExchangeRateRepository,
    PositionRepository,
    ReconciliationSessionRepository,
    SecurityRepository,
    TaxLotRepository,
    TransactionRepository,
    VendorRepository,
)


class PostgresDatabase:
    """PostgreSQL database connection manager."""

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._connection: psycopg2.extensions.connection | None = None

    def get_connection(self) -> psycopg2.extensions.connection:
        """Get or create the database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                self._connection_string,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
        return self._connection

    def initialize(self) -> None:
        """Create all database tables."""
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                -- Entities table
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    entity_type TEXT NOT NULL,
                    fiscal_year_end TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Accounts table
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    sub_type TEXT NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    is_investment_account BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    UNIQUE(name, entity_id),
                    FOREIGN KEY (entity_id) REFERENCES entities(id)
                );

                -- Securities table
                CREATE TABLE IF NOT EXISTS securities (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    cusip TEXT,
                    isin TEXT,
                    asset_class TEXT NOT NULL,
                    is_qsbs_eligible BOOLEAN NOT NULL DEFAULT FALSE,
                    qsbs_qualification_date TEXT,
                    issuer TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                );

                -- Positions table
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    security_id TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    cost_basis_amount TEXT NOT NULL,
                    cost_basis_currency TEXT NOT NULL,
                    market_value_amount TEXT NOT NULL,
                    market_value_currency TEXT NOT NULL,
                    UNIQUE(account_id, security_id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (security_id) REFERENCES securities(id)
                );

                -- Transactions table
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    transaction_date TEXT NOT NULL,
                    posted_date TEXT,
                    memo TEXT NOT NULL DEFAULT '',
                    reference TEXT NOT NULL DEFAULT '',
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    is_reversed BOOLEAN NOT NULL DEFAULT FALSE,
                    reverses_transaction_id TEXT,
                    FOREIGN KEY (reverses_transaction_id) REFERENCES transactions(id)
                );

                -- Tax lots table (must be before entries due to FK)
                CREATE TABLE IF NOT EXISTS tax_lots (
                    id TEXT PRIMARY KEY,
                    position_id TEXT NOT NULL,
                    acquisition_date TEXT NOT NULL,
                    cost_per_share_amount TEXT NOT NULL,
                    cost_per_share_currency TEXT NOT NULL,
                    original_quantity TEXT NOT NULL,
                    remaining_quantity TEXT NOT NULL,
                    acquisition_type TEXT NOT NULL,
                    disposition_date TEXT,
                    is_covered BOOLEAN NOT NULL DEFAULT TRUE,
                    wash_sale_disallowed BOOLEAN NOT NULL DEFAULT FALSE,
                    wash_sale_adjustment_amount TEXT NOT NULL,
                    wash_sale_adjustment_currency TEXT NOT NULL,
                    reference TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (position_id) REFERENCES positions(id)
                );

                -- Entries table (for transaction entries)
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    debit_amount TEXT NOT NULL,
                    debit_currency TEXT NOT NULL,
                    credit_amount TEXT NOT NULL,
                    credit_currency TEXT NOT NULL,
                    memo TEXT NOT NULL DEFAULT '',
                    tax_lot_id TEXT,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (tax_lot_id) REFERENCES tax_lots(id)
                );

                -- Reconciliation sessions table
                CREATE TABLE IF NOT EXISTS reconciliation_sessions (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_format TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    closed_at TEXT
                );

                -- Reconciliation matches table
                CREATE TABLE IF NOT EXISTS reconciliation_matches (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    imported_id TEXT NOT NULL,
                    imported_date TEXT NOT NULL,
                    imported_amount TEXT NOT NULL,
                    imported_description TEXT NOT NULL DEFAULT '',
                    suggested_ledger_txn_id TEXT,
                    confidence_score INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    actioned_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES reconciliation_sessions(id) ON DELETE CASCADE
                );

                -- Exchange rates table
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id TEXT PRIMARY KEY,
                    from_currency TEXT NOT NULL,
                    to_currency TEXT NOT NULL,
                    rate TEXT NOT NULL,
                    effective_date TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                -- Vendors table
                CREATE TABLE IF NOT EXISTS vendors (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    tax_id TEXT,
                    is_1099_eligible BOOLEAN NOT NULL DEFAULT FALSE,
                    default_account_id TEXT,
                    default_category TEXT,
                    contact_email TEXT,
                    contact_phone TEXT,
                    notes TEXT DEFAULT '',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_accounts_entity_id ON accounts(entity_id);
                CREATE INDEX IF NOT EXISTS idx_positions_account_id ON positions(account_id);
                CREATE INDEX IF NOT EXISTS idx_positions_security_id ON positions(security_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
                CREATE INDEX IF NOT EXISTS idx_entries_transaction_id ON entries(transaction_id);
                CREATE INDEX IF NOT EXISTS idx_entries_account_id ON entries(account_id);
                CREATE INDEX IF NOT EXISTS idx_tax_lots_position_id ON tax_lots(position_id);
                CREATE INDEX IF NOT EXISTS idx_tax_lots_acquisition_date ON tax_lots(acquisition_date);
                CREATE INDEX IF NOT EXISTS idx_reconciliation_sessions_account_id ON reconciliation_sessions(account_id);
                CREATE INDEX IF NOT EXISTS idx_reconciliation_matches_session_id ON reconciliation_matches(session_id);
                CREATE INDEX IF NOT EXISTS idx_exchange_rates_pair_date ON exchange_rates(from_currency, to_currency, effective_date);
                CREATE INDEX IF NOT EXISTS idx_exchange_rates_date ON exchange_rates(effective_date);
                CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(name);
                CREATE INDEX IF NOT EXISTS idx_vendors_category ON vendors(category);
                CREATE INDEX IF NOT EXISTS idx_vendors_tax_id ON vendors(tax_id);
                """
            )

            # Add expense columns to transactions and entries tables
            # Postgres supports ADD COLUMN IF NOT EXISTS
            cur.execute(
                """
                ALTER TABLE transactions ADD COLUMN IF NOT EXISTS category TEXT;
                ALTER TABLE transactions ADD COLUMN IF NOT EXISTS tags TEXT;
                ALTER TABLE transactions ADD COLUMN IF NOT EXISTS vendor_id TEXT;
                ALTER TABLE transactions ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE;
                ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurring_frequency TEXT;

                ALTER TABLE entries ADD COLUMN IF NOT EXISTS category TEXT;
                """
            )
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


class PostgresEntityRepository(EntityRepository):
    """PostgreSQL implementation of EntityRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, entity: Entity) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO entities (id, name, entity_type, fiscal_year_end, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(entity.id),
                    entity.name,
                    entity.entity_type.value,
                    entity.fiscal_year_end.isoformat(),
                    entity.is_active,
                    entity.created_at.isoformat(),
                    entity.updated_at.isoformat(),
                ),
            )
        conn.commit()

    def get(self, entity_id: UUID) -> Entity | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM entities WHERE id = %s", (str(entity_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def get_by_name(self, name: str) -> Entity | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM entities WHERE name = %s", (name,))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def list_all(self) -> Iterable[Entity]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM entities")
            rows = cur.fetchall()
        return [self._row_to_entity(row) for row in rows]

    def list_active(self) -> Iterable[Entity]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM entities WHERE is_active = TRUE")
            rows = cur.fetchall()
        return [self._row_to_entity(row) for row in rows]

    def update(self, entity: Entity) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE entities SET
                    name = %s,
                    entity_type = %s,
                    fiscal_year_end = %s,
                    is_active = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    entity.name,
                    entity.entity_type.value,
                    entity.fiscal_year_end.isoformat(),
                    entity.is_active,
                    entity.updated_at.isoformat(),
                    str(entity.id),
                ),
            )
        conn.commit()

    def delete(self, entity_id: UUID) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM entities WHERE id = %s", (str(entity_id),))
        conn.commit()

    def _row_to_entity(self, row: Any) -> Entity:
        entity = Entity(
            name=row["name"],
            entity_type=EntityType(row["entity_type"]),
            id=UUID(row["id"]),
            fiscal_year_end=date.fromisoformat(row["fiscal_year_end"]),
            is_active=bool(row["is_active"]),
        )
        # Set created_at and updated_at directly to avoid triggering defaults
        object.__setattr__(
            entity, "created_at", datetime.fromisoformat(row["created_at"])
        )
        object.__setattr__(
            entity, "updated_at", datetime.fromisoformat(row["updated_at"])
        )
        return entity


class PostgresAccountRepository(AccountRepository):
    """PostgreSQL implementation of AccountRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, account: Account) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, name, entity_id, account_type, sub_type, currency,
                                      is_investment_account, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(account.id),
                    account.name,
                    str(account.entity_id),
                    account.account_type.value,
                    account.sub_type.value,
                    account.currency,
                    account.is_investment_account,
                    account.is_active,
                    account.created_at.isoformat(),
                ),
            )
        conn.commit()

    def get(self, account_id: UUID) -> Account | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM accounts WHERE id = %s", (str(account_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_account(row)

    def get_by_name(self, name: str, entity_id: UUID) -> Account | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM accounts WHERE name = %s AND entity_id = %s",
                (name, str(entity_id)),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_account(row)

    def list_by_entity(self, entity_id: UUID) -> Iterable[Account]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM accounts WHERE entity_id = %s", (str(entity_id),)
            )
            rows = cur.fetchall()
        return [self._row_to_account(row) for row in rows]

    def list_investment_accounts(
        self, entity_id: UUID | None = None
    ) -> Iterable[Account]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            if entity_id is None:
                cur.execute("SELECT * FROM accounts WHERE is_investment_account = TRUE")
            else:
                cur.execute(
                    "SELECT * FROM accounts WHERE is_investment_account = TRUE AND entity_id = %s",
                    (str(entity_id),),
                )
            rows = cur.fetchall()
        return [self._row_to_account(row) for row in rows]

    def update(self, account: Account) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE accounts SET
                    name = %s,
                    entity_id = %s,
                    account_type = %s,
                    sub_type = %s,
                    currency = %s,
                    is_investment_account = %s,
                    is_active = %s
                WHERE id = %s
                """,
                (
                    account.name,
                    str(account.entity_id),
                    account.account_type.value,
                    account.sub_type.value,
                    account.currency,
                    account.is_investment_account,
                    account.is_active,
                    str(account.id),
                ),
            )
        conn.commit()

    def delete(self, account_id: UUID) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE id = %s", (str(account_id),))
        conn.commit()

    def _row_to_account(self, row: Any) -> Account:
        account = Account(
            name=row["name"],
            entity_id=UUID(row["entity_id"]),
            account_type=AccountType(row["account_type"]),
            id=UUID(row["id"]),
            sub_type=AccountSubType(row["sub_type"]),
            currency=row["currency"],
            is_active=bool(row["is_active"]),
        )
        # Override is_investment_account to match stored value
        account.is_investment_account = bool(row["is_investment_account"])
        # Set created_at directly
        object.__setattr__(
            account, "created_at", datetime.fromisoformat(row["created_at"])
        )
        return account


class PostgresSecurityRepository(SecurityRepository):
    """PostgreSQL implementation of SecurityRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, security: Security) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO securities (id, symbol, name, cusip, isin, asset_class,
                                        is_qsbs_eligible, qsbs_qualification_date, issuer, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(security.id),
                    security.symbol,
                    security.name,
                    security.cusip,
                    security.isin,
                    security.asset_class.value,
                    security.is_qsbs_eligible,
                    security.qsbs_qualification_date.isoformat()
                    if security.qsbs_qualification_date
                    else None,
                    security.issuer,
                    security.is_active,
                ),
            )
        conn.commit()

    def get(self, security_id: UUID) -> Security | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM securities WHERE id = %s", (str(security_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_security(row)

    def get_by_symbol(self, symbol: str) -> Security | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM securities WHERE symbol = %s", (symbol,))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_security(row)

    def get_by_cusip(self, cusip: str) -> Security | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM securities WHERE cusip = %s", (cusip,))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_security(row)

    def list_all(self) -> Iterable[Security]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM securities")
            rows = cur.fetchall()
        return [self._row_to_security(row) for row in rows]

    def list_qsbs_eligible(self) -> Iterable[Security]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM securities WHERE is_qsbs_eligible = TRUE")
            rows = cur.fetchall()
        return [self._row_to_security(row) for row in rows]

    def update(self, security: Security) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE securities SET
                    symbol = %s,
                    name = %s,
                    cusip = %s,
                    isin = %s,
                    asset_class = %s,
                    is_qsbs_eligible = %s,
                    qsbs_qualification_date = %s,
                    issuer = %s,
                    is_active = %s
                WHERE id = %s
                """,
                (
                    security.symbol,
                    security.name,
                    security.cusip,
                    security.isin,
                    security.asset_class.value,
                    security.is_qsbs_eligible,
                    security.qsbs_qualification_date.isoformat()
                    if security.qsbs_qualification_date
                    else None,
                    security.issuer,
                    security.is_active,
                    str(security.id),
                ),
            )
        conn.commit()

    def _row_to_security(self, row: Any) -> Security:
        return Security(
            symbol=row["symbol"],
            name=row["name"],
            id=UUID(row["id"]),
            cusip=row["cusip"],
            isin=row["isin"],
            asset_class=AssetClass(row["asset_class"]),
            is_qsbs_eligible=bool(row["is_qsbs_eligible"]),
            qsbs_qualification_date=date.fromisoformat(row["qsbs_qualification_date"])
            if row["qsbs_qualification_date"]
            else None,
            issuer=row["issuer"],
            is_active=bool(row["is_active"]),
        )


class PostgresPositionRepository(PositionRepository):
    """PostgreSQL implementation of PositionRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, position: Position) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO positions (id, account_id, security_id, quantity,
                                       cost_basis_amount, cost_basis_currency,
                                       market_value_amount, market_value_currency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(position.id),
                    str(position.account_id),
                    str(position.security_id),
                    str(position.quantity.value),
                    str(position.cost_basis.amount),
                    position.cost_basis.currency,
                    str(position.market_value.amount),
                    position.market_value.currency,
                ),
            )
        conn.commit()

    def get(self, position_id: UUID) -> Position | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM positions WHERE id = %s", (str(position_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_position(row)

    def get_by_account_and_security(
        self, account_id: UUID, security_id: UUID
    ) -> Position | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM positions WHERE account_id = %s AND security_id = %s",
                (str(account_id), str(security_id)),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_position(row)

    def list_by_account(self, account_id: UUID) -> Iterable[Position]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM positions WHERE account_id = %s", (str(account_id),)
            )
            rows = cur.fetchall()
        return [self._row_to_position(row) for row in rows]

    def list_by_security(self, security_id: UUID) -> Iterable[Position]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM positions WHERE security_id = %s", (str(security_id),)
            )
            rows = cur.fetchall()
        return [self._row_to_position(row) for row in rows]

    def list_by_entity(self, entity_id: UUID) -> Iterable[Position]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.* FROM positions p
                JOIN accounts a ON p.account_id = a.id
                WHERE a.entity_id = %s
                """,
                (str(entity_id),),
            )
            rows = cur.fetchall()
        return [self._row_to_position(row) for row in rows]

    def update(self, position: Position) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE positions SET
                    account_id = %s,
                    security_id = %s,
                    quantity = %s,
                    cost_basis_amount = %s,
                    cost_basis_currency = %s,
                    market_value_amount = %s,
                    market_value_currency = %s
                WHERE id = %s
                """,
                (
                    str(position.account_id),
                    str(position.security_id),
                    str(position.quantity.value),
                    str(position.cost_basis.amount),
                    position.cost_basis.currency,
                    str(position.market_value.amount),
                    position.market_value.currency,
                    str(position.id),
                ),
            )
        conn.commit()

    def _row_to_position(self, row: Any) -> Position:
        position = Position(
            account_id=UUID(row["account_id"]),
            security_id=UUID(row["security_id"]),
            id=UUID(row["id"]),
        )
        # Update internal state
        position.update_from_lots(
            total_quantity=Quantity(Decimal(row["quantity"])),
            total_cost=Money(
                Decimal(row["cost_basis_amount"]), row["cost_basis_currency"]
            ),
        )
        # Set market value directly using internal attribute
        position._market_value = Money(
            Decimal(row["market_value_amount"]), row["market_value_currency"]
        )
        return position


class PostgresTransactionRepository(TransactionRepository):
    """PostgreSQL implementation of TransactionRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, txn: Transaction) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (id, transaction_date, posted_date, memo, reference,
                                          created_by, created_at, is_reversed, reverses_transaction_id,
                                          category, tags, vendor_id, is_recurring, recurring_frequency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(txn.id),
                    txn.transaction_date.isoformat(),
                    txn.posted_date.isoformat() if txn.posted_date else None,
                    txn.memo,
                    txn.reference,
                    str(txn.created_by) if txn.created_by else None,
                    txn.created_at.isoformat(),
                    txn.is_reversed,
                    str(txn.reverses_transaction_id)
                    if txn.reverses_transaction_id
                    else None,
                    txn.category,
                    json.dumps(txn.tags) if txn.tags else None,
                    str(txn.vendor_id) if txn.vendor_id else None,
                    txn.is_recurring,
                    txn.recurring_frequency,
                ),
            )
            for entry in txn.entries:
                cur.execute(
                    """
                    INSERT INTO entries (id, transaction_id, account_id, debit_amount, debit_currency,
                                         credit_amount, credit_currency, memo, tax_lot_id, category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(entry.id),
                        str(txn.id),
                        str(entry.account_id),
                        str(entry.debit_amount.amount),
                        entry.debit_amount.currency,
                        str(entry.credit_amount.amount),
                        entry.credit_amount.currency,
                        entry.memo,
                        str(entry.tax_lot_id) if entry.tax_lot_id else None,
                        entry.category,
                    ),
                )
        conn.commit()

    def get(self, txn_id: UUID) -> Transaction | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM transactions WHERE id = %s", (str(txn_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_transaction(row)

    def list_by_account(
        self,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[Transaction]:
        conn = self._db.get_connection()
        query = """
            SELECT DISTINCT t.* FROM transactions t
            JOIN entries e ON t.id = e.transaction_id
            WHERE e.account_id = %s
        """
        params: list[str] = [str(account_id)]

        if start_date is not None:
            query += " AND t.transaction_date >= %s"
            params.append(start_date.isoformat())
        if end_date is not None:
            query += " AND t.transaction_date <= %s"
            params.append(end_date.isoformat())

        query += " ORDER BY t.transaction_date"
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def list_by_entity(
        self,
        entity_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[Transaction]:
        conn = self._db.get_connection()
        query = """
            SELECT DISTINCT t.* FROM transactions t
            JOIN entries e ON t.id = e.transaction_id
            JOIN accounts a ON e.account_id = a.id
            WHERE a.entity_id = %s
        """
        params: list[str] = [str(entity_id)]

        if start_date is not None:
            query += " AND t.transaction_date >= %s"
            params.append(start_date.isoformat())
        if end_date is not None:
            query += " AND t.transaction_date <= %s"
            params.append(end_date.isoformat())

        query += " ORDER BY t.transaction_date"
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def list_by_date_range(
        self, start_date: date, end_date: date
    ) -> Iterable[Transaction]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM transactions
                WHERE transaction_date >= %s AND transaction_date <= %s
                ORDER BY transaction_date
                """,
                (start_date.isoformat(), end_date.isoformat()),
            )
            rows = cur.fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def get_reversals(self, txn_id: UUID) -> Iterable[Transaction]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM transactions WHERE reverses_transaction_id = %s",
                (str(txn_id),),
            )
            rows = cur.fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def update(self, txn: Transaction) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE transactions SET
                    transaction_date = %s,
                    posted_date = %s,
                    memo = %s,
                    reference = %s,
                    created_by = %s,
                    is_reversed = %s,
                    reverses_transaction_id = %s,
                    category = %s,
                    tags = %s,
                    vendor_id = %s,
                    is_recurring = %s,
                    recurring_frequency = %s
                WHERE id = %s
                """,
                (
                    txn.transaction_date.isoformat(),
                    txn.posted_date.isoformat() if txn.posted_date else None,
                    txn.memo,
                    txn.reference,
                    str(txn.created_by) if txn.created_by else None,
                    txn.is_reversed,
                    str(txn.reverses_transaction_id)
                    if txn.reverses_transaction_id
                    else None,
                    txn.category,
                    json.dumps(txn.tags) if txn.tags else None,
                    str(txn.vendor_id) if txn.vendor_id else None,
                    txn.is_recurring,
                    txn.recurring_frequency,
                    str(txn.id),
                ),
            )
        conn.commit()

    def _row_to_transaction(self, row: Any) -> Transaction:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM entries WHERE transaction_id = %s", (row["id"],))
            entry_rows = cur.fetchall()
        entries = [self._row_to_entry(entry_row) for entry_row in entry_rows]

        tags_raw = row.get("tags")
        tags: list[str] = json.loads(tags_raw) if tags_raw else []

        txn = Transaction(
            transaction_date=date.fromisoformat(row["transaction_date"]),
            entries=entries,
            id=UUID(row["id"]),
            posted_date=date.fromisoformat(row["posted_date"])
            if row["posted_date"]
            else None,
            memo=row["memo"],
            reference=row["reference"],
            created_by=UUID(row["created_by"]) if row["created_by"] else None,
            is_reversed=bool(row["is_reversed"]),
            reverses_transaction_id=UUID(row["reverses_transaction_id"])
            if row["reverses_transaction_id"]
            else None,
            category=row.get("category"),
            tags=tags,
            vendor_id=UUID(row["vendor_id"]) if row.get("vendor_id") else None,
            is_recurring=bool(row.get("is_recurring", False)),
            recurring_frequency=row.get("recurring_frequency"),
        )
        object.__setattr__(txn, "created_at", datetime.fromisoformat(row["created_at"]))
        return txn

    def _row_to_entry(self, row: Any) -> Entry:
        return Entry(
            account_id=UUID(row["account_id"]),
            id=UUID(row["id"]),
            debit_amount=Money(Decimal(row["debit_amount"]), row["debit_currency"]),
            credit_amount=Money(Decimal(row["credit_amount"]), row["credit_currency"]),
            memo=row["memo"],
            tax_lot_id=UUID(row["tax_lot_id"]) if row["tax_lot_id"] else None,
            category=row.get("category"),
        )


class PostgresTaxLotRepository(TaxLotRepository):
    """PostgreSQL implementation of TaxLotRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, lot: TaxLot) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tax_lots (id, position_id, acquisition_date, cost_per_share_amount,
                                      cost_per_share_currency, original_quantity, remaining_quantity,
                                      acquisition_type, disposition_date, is_covered,
                                      wash_sale_disallowed, wash_sale_adjustment_amount,
                                      wash_sale_adjustment_currency, reference, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(lot.id),
                    str(lot.position_id),
                    lot.acquisition_date.isoformat(),
                    str(lot.cost_per_share.amount),
                    lot.cost_per_share.currency,
                    str(lot.original_quantity.value),
                    str(lot.remaining_quantity.value),
                    lot.acquisition_type.value,
                    lot.disposition_date.isoformat() if lot.disposition_date else None,
                    lot.is_covered,
                    lot.wash_sale_disallowed,
                    str(lot.wash_sale_adjustment.amount),
                    lot.wash_sale_adjustment.currency,
                    lot.reference,
                    lot.created_at.isoformat(),
                ),
            )
        conn.commit()

    def get(self, lot_id: UUID) -> TaxLot | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tax_lots WHERE id = %s", (str(lot_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_tax_lot(row)

    def list_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM tax_lots WHERE position_id = %s ORDER BY acquisition_date",
                (str(position_id),),
            )
            rows = cur.fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def list_open_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM tax_lots
                WHERE position_id = %s AND CAST(remaining_quantity AS DECIMAL) > 0
                ORDER BY acquisition_date
                """,
                (str(position_id),),
            )
            rows = cur.fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def list_by_acquisition_date_range(
        self, position_id: UUID, start_date: date, end_date: date
    ) -> Iterable[TaxLot]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM tax_lots
                WHERE position_id = %s AND acquisition_date >= %s AND acquisition_date <= %s
                ORDER BY acquisition_date
                """,
                (str(position_id), start_date.isoformat(), end_date.isoformat()),
            )
            rows = cur.fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def list_wash_sale_candidates(
        self, position_id: UUID, sale_date: date
    ) -> Iterable[TaxLot]:
        """List lots acquired within 30 days before or after sale date."""
        conn = self._db.get_connection()
        # Wash sale rule: 30 days before and after the sale
        start_date = sale_date - timedelta(days=30)
        end_date = sale_date + timedelta(days=30)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM tax_lots
                WHERE position_id = %s AND acquisition_date >= %s AND acquisition_date <= %s
                ORDER BY acquisition_date
                """,
                (str(position_id), start_date.isoformat(), end_date.isoformat()),
            )
            rows = cur.fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def update(self, lot: TaxLot) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tax_lots SET
                    position_id = %s,
                    acquisition_date = %s,
                    cost_per_share_amount = %s,
                    cost_per_share_currency = %s,
                    original_quantity = %s,
                    remaining_quantity = %s,
                    acquisition_type = %s,
                    disposition_date = %s,
                    is_covered = %s,
                    wash_sale_disallowed = %s,
                    wash_sale_adjustment_amount = %s,
                    wash_sale_adjustment_currency = %s,
                    reference = %s
                WHERE id = %s
                """,
                (
                    str(lot.position_id),
                    lot.acquisition_date.isoformat(),
                    str(lot.cost_per_share.amount),
                    lot.cost_per_share.currency,
                    str(lot.original_quantity.value),
                    str(lot.remaining_quantity.value),
                    lot.acquisition_type.value,
                    lot.disposition_date.isoformat() if lot.disposition_date else None,
                    lot.is_covered,
                    lot.wash_sale_disallowed,
                    str(lot.wash_sale_adjustment.amount),
                    lot.wash_sale_adjustment.currency,
                    lot.reference,
                    str(lot.id),
                ),
            )
        conn.commit()

    def _row_to_tax_lot(self, row: Any) -> TaxLot:
        lot = TaxLot(
            position_id=UUID(row["position_id"]),
            acquisition_date=date.fromisoformat(row["acquisition_date"]),
            cost_per_share=Money(
                Decimal(row["cost_per_share_amount"]), row["cost_per_share_currency"]
            ),
            original_quantity=Quantity(Decimal(row["original_quantity"])),
            id=UUID(row["id"]),
            acquisition_type=AcquisitionType(row["acquisition_type"]),
            disposition_date=date.fromisoformat(row["disposition_date"])
            if row["disposition_date"]
            else None,
            is_covered=bool(row["is_covered"]),
            wash_sale_disallowed=bool(row["wash_sale_disallowed"]),
            wash_sale_adjustment=Money(
                Decimal(row["wash_sale_adjustment_amount"]),
                row["wash_sale_adjustment_currency"],
            ),
            reference=row["reference"],
        )
        # Set remaining_quantity (it's set in __post_init__ to original_quantity)
        lot.remaining_quantity = Quantity(Decimal(row["remaining_quantity"]))
        # Set created_at directly
        object.__setattr__(lot, "created_at", datetime.fromisoformat(row["created_at"]))
        return lot


class PostgresReconciliationSessionRepository(ReconciliationSessionRepository):
    """PostgreSQL implementation of ReconciliationSessionRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, session: ReconciliationSession) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reconciliation_sessions (id, account_id, file_name, file_format,
                                                      status, created_at, closed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(session.id),
                    str(session.account_id),
                    session.file_name,
                    session.file_format,
                    session.status.value,
                    session.created_at.isoformat(),
                    session.closed_at.isoformat() if session.closed_at else None,
                ),
            )
            for match in session.matches:
                cur.execute(
                    """
                    INSERT INTO reconciliation_matches (id, session_id, imported_id, imported_date,
                                                         imported_amount, imported_description,
                                                         suggested_ledger_txn_id, confidence_score,
                                                         status, actioned_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(match.id),
                        str(session.id),
                        match.imported_id,
                        match.imported_date.isoformat(),
                        str(match.imported_amount),
                        match.imported_description,
                        str(match.suggested_ledger_txn_id)
                        if match.suggested_ledger_txn_id
                        else None,
                        match.confidence_score,
                        match.status.value,
                        match.actioned_at.isoformat() if match.actioned_at else None,
                        match.created_at.isoformat(),
                    ),
                )
        conn.commit()

    def get(self, session_id: UUID) -> ReconciliationSession | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reconciliation_sessions WHERE id = %s",
                (str(session_id),),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def get_pending_for_account(self, account_id: UUID) -> ReconciliationSession | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reconciliation_sessions WHERE account_id = %s AND status = %s",
                (str(account_id), ReconciliationSessionStatus.PENDING.value),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def update(self, session: ReconciliationSession) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE reconciliation_sessions SET
                    account_id = %s,
                    file_name = %s,
                    file_format = %s,
                    status = %s,
                    closed_at = %s
                WHERE id = %s
                """,
                (
                    str(session.account_id),
                    session.file_name,
                    session.file_format,
                    session.status.value,
                    session.closed_at.isoformat() if session.closed_at else None,
                    str(session.id),
                ),
            )
            cur.execute(
                "DELETE FROM reconciliation_matches WHERE session_id = %s",
                (str(session.id),),
            )
            for match in session.matches:
                cur.execute(
                    """
                    INSERT INTO reconciliation_matches (id, session_id, imported_id, imported_date,
                                                         imported_amount, imported_description,
                                                         suggested_ledger_txn_id, confidence_score,
                                                         status, actioned_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(match.id),
                        str(session.id),
                        match.imported_id,
                        match.imported_date.isoformat(),
                        str(match.imported_amount),
                        match.imported_description,
                        str(match.suggested_ledger_txn_id)
                        if match.suggested_ledger_txn_id
                        else None,
                        match.confidence_score,
                        match.status.value,
                        match.actioned_at.isoformat() if match.actioned_at else None,
                        match.created_at.isoformat(),
                    ),
                )
        conn.commit()

    def delete(self, session_id: UUID) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM reconciliation_sessions WHERE id = %s", (str(session_id),)
            )
        conn.commit()

    def list_by_account(self, account_id: UUID) -> list[ReconciliationSession]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reconciliation_sessions WHERE account_id = %s",
                (str(account_id),),
            )
            rows = cur.fetchall()
        return [self._row_to_session(row) for row in rows]

    def _row_to_session(self, row: Any) -> ReconciliationSession:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reconciliation_matches WHERE session_id = %s ORDER BY created_at ASC",
                (row["id"],),
            )
            match_rows = cur.fetchall()
        matches = [self._row_to_match(match_row) for match_row in match_rows]

        session = ReconciliationSession(
            account_id=UUID(row["account_id"]),
            file_name=row["file_name"],
            file_format=row["file_format"],
            id=UUID(row["id"]),
            status=ReconciliationSessionStatus(row["status"]),
            matches=matches,
            closed_at=datetime.fromisoformat(row["closed_at"])
            if row["closed_at"]
            else None,
        )
        object.__setattr__(
            session, "created_at", datetime.fromisoformat(row["created_at"])
        )
        return session

    def _row_to_match(self, row: Any) -> ReconciliationMatch:
        match = ReconciliationMatch(
            session_id=UUID(row["session_id"]),
            imported_id=row["imported_id"],
            imported_date=date.fromisoformat(row["imported_date"]),
            imported_amount=Decimal(row["imported_amount"]),
            id=UUID(row["id"]),
            imported_description=row["imported_description"],
            suggested_ledger_txn_id=UUID(row["suggested_ledger_txn_id"])
            if row["suggested_ledger_txn_id"]
            else None,
            confidence_score=row["confidence_score"],
            status=ReconciliationMatchStatus(row["status"]),
            actioned_at=datetime.fromisoformat(row["actioned_at"])
            if row["actioned_at"]
            else None,
        )
        object.__setattr__(
            match, "created_at", datetime.fromisoformat(row["created_at"])
        )
        return match


class PostgresExchangeRateRepository(ExchangeRateRepository):
    """PostgreSQL implementation of ExchangeRateRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, rate: ExchangeRate) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exchange_rates (id, from_currency, to_currency, rate,
                                            effective_date, source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(rate.id),
                    rate.from_currency,
                    rate.to_currency,
                    str(rate.rate),
                    rate.effective_date.isoformat(),
                    rate.source.value,
                    rate.created_at.isoformat(),
                ),
            )
        conn.commit()

    def get(self, rate_id: UUID) -> ExchangeRate | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM exchange_rates WHERE id = %s", (str(rate_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_exchange_rate(row)

    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: date,
    ) -> ExchangeRate | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM exchange_rates
                WHERE from_currency = %s AND to_currency = %s AND effective_date = %s
                """,
                (from_currency, to_currency, effective_date.isoformat()),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_exchange_rate(row)

    def get_latest_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM exchange_rates
                WHERE from_currency = %s AND to_currency = %s
                ORDER BY effective_date DESC
                LIMIT 1
                """,
                (from_currency, to_currency),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_exchange_rate(row)

    def list_by_currency_pair(
        self,
        from_currency: str,
        to_currency: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Iterable[ExchangeRate]:
        conn = self._db.get_connection()
        query = """
            SELECT * FROM exchange_rates
            WHERE from_currency = %s AND to_currency = %s
        """
        params: list[str] = [from_currency, to_currency]

        if start_date is not None:
            query += " AND effective_date >= %s"
            params.append(start_date.isoformat())
        if end_date is not None:
            query += " AND effective_date <= %s"
            params.append(end_date.isoformat())

        query += " ORDER BY effective_date"
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [self._row_to_exchange_rate(row) for row in rows]

    def list_by_date(self, effective_date: date) -> Iterable[ExchangeRate]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM exchange_rates WHERE effective_date = %s",
                (effective_date.isoformat(),),
            )
            rows = cur.fetchall()
        return [self._row_to_exchange_rate(row) for row in rows]

    def delete(self, rate_id: UUID) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM exchange_rates WHERE id = %s", (str(rate_id),))
        conn.commit()

    def _row_to_exchange_rate(self, row: Any) -> ExchangeRate:
        rate = ExchangeRate(
            from_currency=row["from_currency"],
            to_currency=row["to_currency"],
            rate=Decimal(row["rate"]),
            effective_date=date.fromisoformat(row["effective_date"]),
            id=UUID(row["id"]),
            source=ExchangeRateSource(row["source"]),
        )
        # Set created_at directly to preserve stored value
        object.__setattr__(
            rate, "created_at", datetime.fromisoformat(row["created_at"])
        )
        return rate


class PostgresVendorRepository(VendorRepository):
    """PostgreSQL implementation of VendorRepository."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._db = database

    def add(self, vendor: Vendor) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vendors (id, name, category, tax_id, is_1099_eligible,
                                     default_account_id, default_category, contact_email,
                                     contact_phone, notes, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(vendor.id),
                    vendor.name,
                    vendor.category,
                    vendor.tax_id,
                    vendor.is_1099_eligible,
                    str(vendor.default_account_id)
                    if vendor.default_account_id
                    else None,
                    vendor.default_category,
                    vendor.contact_email,
                    vendor.contact_phone,
                    vendor.notes,
                    vendor.is_active,
                    vendor.created_at.isoformat(),
                    vendor.updated_at.isoformat(),
                ),
            )
        conn.commit()

    def get(self, vendor_id: UUID) -> Vendor | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vendors WHERE id = %s", (str(vendor_id),))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_vendor(row)

    def update(self, vendor: Vendor) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE vendors SET
                    name = %s,
                    category = %s,
                    tax_id = %s,
                    is_1099_eligible = %s,
                    default_account_id = %s,
                    default_category = %s,
                    contact_email = %s,
                    contact_phone = %s,
                    notes = %s,
                    is_active = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    vendor.name,
                    vendor.category,
                    vendor.tax_id,
                    vendor.is_1099_eligible,
                    str(vendor.default_account_id)
                    if vendor.default_account_id
                    else None,
                    vendor.default_category,
                    vendor.contact_email,
                    vendor.contact_phone,
                    vendor.notes,
                    vendor.is_active,
                    vendor.updated_at.isoformat(),
                    str(vendor.id),
                ),
            )
        conn.commit()

    def delete(self, vendor_id: UUID) -> None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM vendors WHERE id = %s", (str(vendor_id),))
        conn.commit()

    def list_all(self, include_inactive: bool = False) -> Iterable[Vendor]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            if include_inactive:
                cur.execute("SELECT * FROM vendors ORDER BY name")
            else:
                cur.execute(
                    "SELECT * FROM vendors WHERE is_active = TRUE ORDER BY name"
                )
            rows = cur.fetchall()
        return [self._row_to_vendor(row) for row in rows]

    def list_by_category(self, category: str) -> Iterable[Vendor]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM vendors WHERE category = %s AND is_active = TRUE ORDER BY name",
                (category,),
            )
            rows = cur.fetchall()
        return [self._row_to_vendor(row) for row in rows]

    def search_by_name(self, name_pattern: str) -> Iterable[Vendor]:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM vendors WHERE name ILIKE %s AND is_active = TRUE ORDER BY name",
                (f"%{name_pattern}%",),
            )
            rows = cur.fetchall()
        return [self._row_to_vendor(row) for row in rows]

    def get_by_tax_id(self, tax_id: str) -> Vendor | None:
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vendors WHERE tax_id = %s", (tax_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_vendor(row)

    def _row_to_vendor(self, row: Any) -> Vendor:
        vendor = Vendor(
            name=row["name"],
            id=UUID(row["id"]),
            category=row["category"],
            tax_id=row["tax_id"],
            is_1099_eligible=bool(row["is_1099_eligible"]),
            default_account_id=UUID(row["default_account_id"])
            if row["default_account_id"]
            else None,
            default_category=row["default_category"],
            contact_email=row["contact_email"],
            contact_phone=row["contact_phone"],
            notes=row["notes"] or "",
            is_active=bool(row["is_active"]),
        )
        object.__setattr__(
            vendor, "created_at", datetime.fromisoformat(row["created_at"])
        )
        object.__setattr__(
            vendor, "updated_at", datetime.fromisoformat(row["updated_at"])
        )
        return vendor
