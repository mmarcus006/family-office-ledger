"""SQLite implementations of repository interfaces."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from family_office_ledger.domain.entities import Account, Entity, Position, Security
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
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    PositionRepository,
    SecurityRepository,
    TaxLotRepository,
    TransactionRepository,
)


class SQLiteDatabase:
    """SQLite database connection manager."""

    def __init__(
        self, path: str | Path = ":memory:", check_same_thread: bool = True
    ) -> None:
        self._path = str(path)
        self._check_same_thread = check_same_thread
        self._connection: sqlite3.Connection | None = None

    def get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self._path, check_same_thread=self._check_same_thread
            )
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def initialize(self) -> None:
        """Create all database tables."""
        conn = self.get_connection()
        conn.executescript(
            """
            -- Entities table
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                entity_type TEXT NOT NULL,
                fiscal_year_end TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
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
                is_investment_account INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
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
                is_qsbs_eligible INTEGER NOT NULL DEFAULT 0,
                qsbs_qualification_date TEXT,
                issuer TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
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
                is_reversed INTEGER NOT NULL DEFAULT 0,
                reverses_transaction_id TEXT,
                FOREIGN KEY (reverses_transaction_id) REFERENCES transactions(id)
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

            -- Tax lots table
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
                is_covered INTEGER NOT NULL DEFAULT 1,
                wash_sale_disallowed INTEGER NOT NULL DEFAULT 0,
                wash_sale_adjustment_amount TEXT NOT NULL,
                wash_sale_adjustment_currency TEXT NOT NULL,
                reference TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (position_id) REFERENCES positions(id)
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
            """
        )
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


class SQLiteEntityRepository(EntityRepository):
    """SQLite implementation of EntityRepository."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._db = database

    def add(self, entity: Entity) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO entities (id, name, entity_type, fiscal_year_end, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(entity.id),
                entity.name,
                entity.entity_type.value,
                entity.fiscal_year_end.isoformat(),
                1 if entity.is_active else 0,
                entity.created_at.isoformat(),
                entity.updated_at.isoformat(),
            ),
        )
        conn.commit()

    def get(self, entity_id: UUID) -> Entity | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM entities WHERE id = ?", (str(entity_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def get_by_name(self, name: str) -> Entity | None:
        conn = self._db.get_connection()
        row = conn.execute("SELECT * FROM entities WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def list_all(self) -> Iterable[Entity]:
        conn = self._db.get_connection()
        rows = conn.execute("SELECT * FROM entities").fetchall()
        return [self._row_to_entity(row) for row in rows]

    def list_active(self) -> Iterable[Entity]:
        conn = self._db.get_connection()
        rows = conn.execute("SELECT * FROM entities WHERE is_active = 1").fetchall()
        return [self._row_to_entity(row) for row in rows]

    def update(self, entity: Entity) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE entities SET
                name = ?,
                entity_type = ?,
                fiscal_year_end = ?,
                is_active = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                entity.name,
                entity.entity_type.value,
                entity.fiscal_year_end.isoformat(),
                1 if entity.is_active else 0,
                entity.updated_at.isoformat(),
                str(entity.id),
            ),
        )
        conn.commit()

    def delete(self, entity_id: UUID) -> None:
        conn = self._db.get_connection()
        conn.execute("DELETE FROM entities WHERE id = ?", (str(entity_id),))
        conn.commit()

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
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


class SQLiteAccountRepository(AccountRepository):
    """SQLite implementation of AccountRepository."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._db = database

    def add(self, account: Account) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO accounts (id, name, entity_id, account_type, sub_type, currency,
                                  is_investment_account, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(account.id),
                account.name,
                str(account.entity_id),
                account.account_type.value,
                account.sub_type.value,
                account.currency,
                1 if account.is_investment_account else 0,
                1 if account.is_active else 0,
                account.created_at.isoformat(),
            ),
        )
        conn.commit()

    def get(self, account_id: UUID) -> Account | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (str(account_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_account(row)

    def get_by_name(self, name: str, entity_id: UUID) -> Account | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM accounts WHERE name = ? AND entity_id = ?",
            (name, str(entity_id)),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_account(row)

    def list_by_entity(self, entity_id: UUID) -> Iterable[Account]:
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT * FROM accounts WHERE entity_id = ?", (str(entity_id),)
        ).fetchall()
        return [self._row_to_account(row) for row in rows]

    def list_investment_accounts(
        self, entity_id: UUID | None = None
    ) -> Iterable[Account]:
        conn = self._db.get_connection()
        if entity_id is None:
            rows = conn.execute(
                "SELECT * FROM accounts WHERE is_investment_account = 1"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM accounts WHERE is_investment_account = 1 AND entity_id = ?",
                (str(entity_id),),
            ).fetchall()
        return [self._row_to_account(row) for row in rows]

    def update(self, account: Account) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE accounts SET
                name = ?,
                entity_id = ?,
                account_type = ?,
                sub_type = ?,
                currency = ?,
                is_investment_account = ?,
                is_active = ?
            WHERE id = ?
            """,
            (
                account.name,
                str(account.entity_id),
                account.account_type.value,
                account.sub_type.value,
                account.currency,
                1 if account.is_investment_account else 0,
                1 if account.is_active else 0,
                str(account.id),
            ),
        )
        conn.commit()

    def delete(self, account_id: UUID) -> None:
        conn = self._db.get_connection()
        conn.execute("DELETE FROM accounts WHERE id = ?", (str(account_id),))
        conn.commit()

    def _row_to_account(self, row: sqlite3.Row) -> Account:
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


class SQLiteSecurityRepository(SecurityRepository):
    """SQLite implementation of SecurityRepository."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._db = database

    def add(self, security: Security) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO securities (id, symbol, name, cusip, isin, asset_class,
                                    is_qsbs_eligible, qsbs_qualification_date, issuer, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(security.id),
                security.symbol,
                security.name,
                security.cusip,
                security.isin,
                security.asset_class.value,
                1 if security.is_qsbs_eligible else 0,
                security.qsbs_qualification_date.isoformat()
                if security.qsbs_qualification_date
                else None,
                security.issuer,
                1 if security.is_active else 0,
            ),
        )
        conn.commit()

    def get(self, security_id: UUID) -> Security | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM securities WHERE id = ?", (str(security_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_security(row)

    def get_by_symbol(self, symbol: str) -> Security | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM securities WHERE symbol = ?", (symbol,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_security(row)

    def get_by_cusip(self, cusip: str) -> Security | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM securities WHERE cusip = ?", (cusip,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_security(row)

    def list_all(self) -> Iterable[Security]:
        conn = self._db.get_connection()
        rows = conn.execute("SELECT * FROM securities").fetchall()
        return [self._row_to_security(row) for row in rows]

    def list_qsbs_eligible(self) -> Iterable[Security]:
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT * FROM securities WHERE is_qsbs_eligible = 1"
        ).fetchall()
        return [self._row_to_security(row) for row in rows]

    def update(self, security: Security) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE securities SET
                symbol = ?,
                name = ?,
                cusip = ?,
                isin = ?,
                asset_class = ?,
                is_qsbs_eligible = ?,
                qsbs_qualification_date = ?,
                issuer = ?,
                is_active = ?
            WHERE id = ?
            """,
            (
                security.symbol,
                security.name,
                security.cusip,
                security.isin,
                security.asset_class.value,
                1 if security.is_qsbs_eligible else 0,
                security.qsbs_qualification_date.isoformat()
                if security.qsbs_qualification_date
                else None,
                security.issuer,
                1 if security.is_active else 0,
                str(security.id),
            ),
        )
        conn.commit()

    def _row_to_security(self, row: sqlite3.Row) -> Security:
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


class SQLitePositionRepository(PositionRepository):
    """SQLite implementation of PositionRepository."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._db = database

    def add(self, position: Position) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO positions (id, account_id, security_id, quantity,
                                   cost_basis_amount, cost_basis_currency,
                                   market_value_amount, market_value_currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        row = conn.execute(
            "SELECT * FROM positions WHERE id = ?", (str(position_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_position(row)

    def get_by_account_and_security(
        self, account_id: UUID, security_id: UUID
    ) -> Position | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM positions WHERE account_id = ? AND security_id = ?",
            (str(account_id), str(security_id)),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_position(row)

    def list_by_account(self, account_id: UUID) -> Iterable[Position]:
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT * FROM positions WHERE account_id = ?", (str(account_id),)
        ).fetchall()
        return [self._row_to_position(row) for row in rows]

    def list_by_security(self, security_id: UUID) -> Iterable[Position]:
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT * FROM positions WHERE security_id = ?", (str(security_id),)
        ).fetchall()
        return [self._row_to_position(row) for row in rows]

    def list_by_entity(self, entity_id: UUID) -> Iterable[Position]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """
            SELECT p.* FROM positions p
            JOIN accounts a ON p.account_id = a.id
            WHERE a.entity_id = ?
            """,
            (str(entity_id),),
        ).fetchall()
        return [self._row_to_position(row) for row in rows]

    def update(self, position: Position) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE positions SET
                account_id = ?,
                security_id = ?,
                quantity = ?,
                cost_basis_amount = ?,
                cost_basis_currency = ?,
                market_value_amount = ?,
                market_value_currency = ?
            WHERE id = ?
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

    def _row_to_position(self, row: sqlite3.Row) -> Position:
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


class SQLiteTransactionRepository(TransactionRepository):
    """SQLite implementation of TransactionRepository."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._db = database

    def add(self, txn: Transaction) -> None:
        conn = self._db.get_connection()
        # Insert transaction
        conn.execute(
            """
            INSERT INTO transactions (id, transaction_date, posted_date, memo, reference,
                                      created_by, created_at, is_reversed, reverses_transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(txn.id),
                txn.transaction_date.isoformat(),
                txn.posted_date.isoformat() if txn.posted_date else None,
                txn.memo,
                txn.reference,
                str(txn.created_by) if txn.created_by else None,
                txn.created_at.isoformat(),
                1 if txn.is_reversed else 0,
                str(txn.reverses_transaction_id)
                if txn.reverses_transaction_id
                else None,
            ),
        )
        # Insert entries
        for entry in txn.entries:
            conn.execute(
                """
                INSERT INTO entries (id, transaction_id, account_id, debit_amount, debit_currency,
                                     credit_amount, credit_currency, memo, tax_lot_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
        conn.commit()

    def get(self, txn_id: UUID) -> Transaction | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (str(txn_id),)
        ).fetchone()
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
            WHERE e.account_id = ?
        """
        params: list[str] = [str(account_id)]

        if start_date is not None:
            query += " AND t.transaction_date >= ?"
            params.append(start_date.isoformat())
        if end_date is not None:
            query += " AND t.transaction_date <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY t.transaction_date"
        rows = conn.execute(query, params).fetchall()
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
            WHERE a.entity_id = ?
        """
        params: list[str] = [str(entity_id)]

        if start_date is not None:
            query += " AND t.transaction_date >= ?"
            params.append(start_date.isoformat())
        if end_date is not None:
            query += " AND t.transaction_date <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY t.transaction_date"
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def list_by_date_range(
        self, start_date: date, end_date: date
    ) -> Iterable[Transaction]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM transactions
            WHERE transaction_date >= ? AND transaction_date <= ?
            ORDER BY transaction_date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def get_reversals(self, txn_id: UUID) -> Iterable[Transaction]:
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT * FROM transactions WHERE reverses_transaction_id = ?",
            (str(txn_id),),
        ).fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def update(self, txn: Transaction) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE transactions SET
                transaction_date = ?,
                posted_date = ?,
                memo = ?,
                reference = ?,
                created_by = ?,
                is_reversed = ?,
                reverses_transaction_id = ?
            WHERE id = ?
            """,
            (
                txn.transaction_date.isoformat(),
                txn.posted_date.isoformat() if txn.posted_date else None,
                txn.memo,
                txn.reference,
                str(txn.created_by) if txn.created_by else None,
                1 if txn.is_reversed else 0,
                str(txn.reverses_transaction_id)
                if txn.reverses_transaction_id
                else None,
                str(txn.id),
            ),
        )
        conn.commit()

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        conn = self._db.get_connection()
        # Get entries for this transaction
        entry_rows = conn.execute(
            "SELECT * FROM entries WHERE transaction_id = ?", (row["id"],)
        ).fetchall()
        entries = [self._row_to_entry(entry_row) for entry_row in entry_rows]

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
        )
        # Set created_at directly
        object.__setattr__(txn, "created_at", datetime.fromisoformat(row["created_at"]))
        return txn

    def _row_to_entry(self, row: sqlite3.Row) -> Entry:
        return Entry(
            account_id=UUID(row["account_id"]),
            id=UUID(row["id"]),
            debit_amount=Money(Decimal(row["debit_amount"]), row["debit_currency"]),
            credit_amount=Money(Decimal(row["credit_amount"]), row["credit_currency"]),
            memo=row["memo"],
            tax_lot_id=UUID(row["tax_lot_id"]) if row["tax_lot_id"] else None,
        )


class SQLiteTaxLotRepository(TaxLotRepository):
    """SQLite implementation of TaxLotRepository."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._db = database

    def add(self, lot: TaxLot) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO tax_lots (id, position_id, acquisition_date, cost_per_share_amount,
                                  cost_per_share_currency, original_quantity, remaining_quantity,
                                  acquisition_type, disposition_date, is_covered,
                                  wash_sale_disallowed, wash_sale_adjustment_amount,
                                  wash_sale_adjustment_currency, reference, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                1 if lot.is_covered else 0,
                1 if lot.wash_sale_disallowed else 0,
                str(lot.wash_sale_adjustment.amount),
                lot.wash_sale_adjustment.currency,
                lot.reference,
                lot.created_at.isoformat(),
            ),
        )
        conn.commit()

    def get(self, lot_id: UUID) -> TaxLot | None:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM tax_lots WHERE id = ?", (str(lot_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_tax_lot(row)

    def list_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT * FROM tax_lots WHERE position_id = ? ORDER BY acquisition_date",
            (str(position_id),),
        ).fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def list_open_by_position(self, position_id: UUID) -> Iterable[TaxLot]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM tax_lots
            WHERE position_id = ? AND CAST(remaining_quantity AS REAL) > 0
            ORDER BY acquisition_date
            """,
            (str(position_id),),
        ).fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def list_by_acquisition_date_range(
        self, position_id: UUID, start_date: date, end_date: date
    ) -> Iterable[TaxLot]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM tax_lots
            WHERE position_id = ? AND acquisition_date >= ? AND acquisition_date <= ?
            ORDER BY acquisition_date
            """,
            (str(position_id), start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def list_wash_sale_candidates(
        self, position_id: UUID, sale_date: date
    ) -> Iterable[TaxLot]:
        """List lots acquired within 30 days before or after sale date."""
        conn = self._db.get_connection()
        # Wash sale rule: 30 days before and after the sale
        from datetime import timedelta

        start_date = sale_date - timedelta(days=30)
        end_date = sale_date + timedelta(days=30)
        rows = conn.execute(
            """
            SELECT * FROM tax_lots
            WHERE position_id = ? AND acquisition_date >= ? AND acquisition_date <= ?
            ORDER BY acquisition_date
            """,
            (str(position_id), start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        return [self._row_to_tax_lot(row) for row in rows]

    def update(self, lot: TaxLot) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE tax_lots SET
                position_id = ?,
                acquisition_date = ?,
                cost_per_share_amount = ?,
                cost_per_share_currency = ?,
                original_quantity = ?,
                remaining_quantity = ?,
                acquisition_type = ?,
                disposition_date = ?,
                is_covered = ?,
                wash_sale_disallowed = ?,
                wash_sale_adjustment_amount = ?,
                wash_sale_adjustment_currency = ?,
                reference = ?
            WHERE id = ?
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
                1 if lot.is_covered else 0,
                1 if lot.wash_sale_disallowed else 0,
                str(lot.wash_sale_adjustment.amount),
                lot.wash_sale_adjustment.currency,
                lot.reference,
                str(lot.id),
            ),
        )
        conn.commit()

    def _row_to_tax_lot(self, row: sqlite3.Row) -> TaxLot:
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
