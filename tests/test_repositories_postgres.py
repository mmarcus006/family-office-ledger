"""Tests for PostgreSQL repository implementations."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

# Check for PostgreSQL availability
POSTGRES_URL = os.environ.get("POSTGRES_URL")
SKIP_POSTGRES = POSTGRES_URL is None

pytestmark = pytest.mark.skipif(
    SKIP_POSTGRES, reason="PostgreSQL not available (POSTGRES_URL env var not set)"
)

if not SKIP_POSTGRES:
    from family_office_ledger.domain.budgets import (
        Budget,
        BudgetLineItem,
        BudgetPeriodType,
    )
    from family_office_ledger.domain.entities import (
        Account,
        Entity,
        Position,
        Security,
    )
    from family_office_ledger.domain.exchange_rates import (
        ExchangeRate,
        ExchangeRateSource,
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
    from family_office_ledger.repositories.postgres import (
        PostgresAccountRepository,
        PostgresBudgetRepository,
        PostgresDatabase,
        PostgresEntityRepository,
        PostgresExchangeRateRepository,
        PostgresPositionRepository,
        PostgresSecurityRepository,
        PostgresTaxLotRepository,
        PostgresTransactionRepository,
        PostgresVendorRepository,
    )


@pytest.fixture
def db() -> "PostgresDatabase":
    """Create a PostgreSQL database for testing."""
    assert POSTGRES_URL is not None
    database = PostgresDatabase(POSTGRES_URL)
    database.initialize()
    conn = database.get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM entries")
        cur.execute("DELETE FROM tax_lots")
        cur.execute("DELETE FROM transactions")
        cur.execute("DELETE FROM positions")
        cur.execute("DELETE FROM securities")
        cur.execute("DELETE FROM budget_line_items")
        cur.execute("DELETE FROM budgets")
        cur.execute("DELETE FROM accounts")
        cur.execute("DELETE FROM entities")
        cur.execute("DELETE FROM exchange_rates")
        cur.execute("DELETE FROM vendors")
    conn.commit()
    return database


@pytest.fixture
def entity_repo(db: "PostgresDatabase") -> "PostgresEntityRepository":
    return PostgresEntityRepository(db)


@pytest.fixture
def account_repo(db: "PostgresDatabase") -> "PostgresAccountRepository":
    return PostgresAccountRepository(db)


@pytest.fixture
def security_repo(db: "PostgresDatabase") -> "PostgresSecurityRepository":
    return PostgresSecurityRepository(db)


@pytest.fixture
def position_repo(db: "PostgresDatabase") -> "PostgresPositionRepository":
    return PostgresPositionRepository(db)


@pytest.fixture
def transaction_repo(db: "PostgresDatabase") -> "PostgresTransactionRepository":
    return PostgresTransactionRepository(db)


@pytest.fixture
def tax_lot_repo(db: "PostgresDatabase") -> "PostgresTaxLotRepository":
    return PostgresTaxLotRepository(db)


@pytest.fixture
def exchange_rate_repo(db: "PostgresDatabase") -> "PostgresExchangeRateRepository":
    return PostgresExchangeRateRepository(db)


@pytest.fixture
def vendor_repo(db: "PostgresDatabase") -> "PostgresVendorRepository":
    return PostgresVendorRepository(db)


@pytest.fixture
def budget_repo(db: "PostgresDatabase") -> "PostgresBudgetRepository":
    return PostgresBudgetRepository(db)


# ===== Entity Repository Tests =====


class TestPostgresEntityRepository:
    def test_add_and_get_entity(self, entity_repo: "PostgresEntityRepository") -> None:
        entity = Entity(
            name="Smith Family Trust",
            entity_type=EntityType.TRUST,
            fiscal_year_end=date(2025, 12, 31),
        )

        entity_repo.add(entity)
        retrieved = entity_repo.get(entity.id)

        assert retrieved is not None
        assert retrieved.id == entity.id
        assert retrieved.name == "Smith Family Trust"
        assert retrieved.entity_type == EntityType.TRUST
        assert retrieved.fiscal_year_end == date(2025, 12, 31)
        assert retrieved.is_active is True

    def test_get_nonexistent_entity_returns_none(
        self, entity_repo: "PostgresEntityRepository"
    ) -> None:
        result = entity_repo.get(uuid4())
        assert result is None

    def test_get_by_name(self, entity_repo: "PostgresEntityRepository") -> None:
        entity = Entity(name="Holdings LLC", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        retrieved = entity_repo.get_by_name("Holdings LLC")

        assert retrieved is not None
        assert retrieved.name == "Holdings LLC"

    def test_get_by_name_not_found(
        self, entity_repo: "PostgresEntityRepository"
    ) -> None:
        result = entity_repo.get_by_name("Nonexistent")
        assert result is None

    def test_list_all_entities(self, entity_repo: "PostgresEntityRepository") -> None:
        entity1 = Entity(name="Trust A", entity_type=EntityType.TRUST)
        entity2 = Entity(name="LLC B", entity_type=EntityType.LLC)
        entity_repo.add(entity1)
        entity_repo.add(entity2)

        entities = list(entity_repo.list_all())

        assert len(entities) == 2
        names = {e.name for e in entities}
        assert names == {"Trust A", "LLC B"}

    def test_list_active_entities(
        self, entity_repo: "PostgresEntityRepository"
    ) -> None:
        entity1 = Entity(name="Active Trust", entity_type=EntityType.TRUST)
        entity2 = Entity(
            name="Inactive LLC", entity_type=EntityType.LLC, is_active=False
        )
        entity_repo.add(entity1)
        entity_repo.add(entity2)

        active = list(entity_repo.list_active())

        assert len(active) == 1
        assert active[0].name == "Active Trust"

    def test_update_entity(self, entity_repo: "PostgresEntityRepository") -> None:
        entity = Entity(name="Old Name", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        updated = Entity(
            name="New Name",
            entity_type=EntityType.LLC,
            id=entity.id,
            fiscal_year_end=date(2026, 6, 30),
            is_active=False,
        )
        entity_repo.update(updated)

        retrieved = entity_repo.get(entity.id)
        assert retrieved is not None
        assert retrieved.name == "New Name"
        assert retrieved.entity_type == EntityType.LLC
        assert retrieved.fiscal_year_end == date(2026, 6, 30)
        assert retrieved.is_active is False

    def test_delete_entity(self, entity_repo: "PostgresEntityRepository") -> None:
        entity = Entity(name="To Delete", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        entity_repo.delete(entity.id)

        assert entity_repo.get(entity.id) is None

    def test_entity_preserves_timestamps(
        self, entity_repo: "PostgresEntityRepository"
    ) -> None:
        entity = Entity(name="Test", entity_type=EntityType.INDIVIDUAL)
        original_created = entity.created_at
        original_updated = entity.updated_at

        entity_repo.add(entity)
        retrieved = entity_repo.get(entity.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
        assert retrieved.updated_at == original_updated


# ===== Account Repository Tests =====


class TestPostgresAccountRepository:
    @pytest.fixture
    def persisted_entity(self, entity_repo: "PostgresEntityRepository") -> "Entity":
        entity = Entity(name="Test Entity", entity_type=EntityType.TRUST)
        entity_repo.add(entity)
        return entity

    def test_add_and_get_account(
        self, account_repo: "PostgresAccountRepository", persisted_entity: "Entity"
    ) -> None:
        account = Account(
            name="Main Checking",
            entity_id=persisted_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
            currency="USD",
        )

        account_repo.add(account)
        retrieved = account_repo.get(account.id)

        assert retrieved is not None
        assert retrieved.id == account.id
        assert retrieved.name == "Main Checking"
        assert retrieved.entity_id == persisted_entity.id
        assert retrieved.account_type == AccountType.ASSET
        assert retrieved.sub_type == AccountSubType.CHECKING
        assert retrieved.currency == "USD"

    def test_get_nonexistent_account_returns_none(
        self, account_repo: "PostgresAccountRepository"
    ) -> None:
        result = account_repo.get(uuid4())
        assert result is None

    def test_get_by_name(
        self, account_repo: "PostgresAccountRepository", persisted_entity: "Entity"
    ) -> None:
        account = Account(
            name="Brokerage",
            entity_id=persisted_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        account_repo.add(account)

        retrieved = account_repo.get_by_name("Brokerage", persisted_entity.id)

        assert retrieved is not None
        assert retrieved.name == "Brokerage"

    def test_get_by_name_not_found(
        self, account_repo: "PostgresAccountRepository", persisted_entity: "Entity"
    ) -> None:
        result = account_repo.get_by_name("Nonexistent", persisted_entity.id)
        assert result is None

    def test_list_by_entity(
        self,
        account_repo: "PostgresAccountRepository",
        entity_repo: "PostgresEntityRepository",
    ) -> None:
        entity1 = Entity(name="Entity 1", entity_type=EntityType.TRUST)
        entity2 = Entity(name="Entity 2", entity_type=EntityType.LLC)
        entity_repo.add(entity1)
        entity_repo.add(entity2)

        account1 = Account(
            name="Account 1",
            entity_id=entity1.id,
            account_type=AccountType.ASSET,
        )
        account2 = Account(
            name="Account 2",
            entity_id=entity1.id,
            account_type=AccountType.LIABILITY,
        )
        account3 = Account(
            name="Account 3",
            entity_id=entity2.id,
            account_type=AccountType.ASSET,
        )
        account_repo.add(account1)
        account_repo.add(account2)
        account_repo.add(account3)

        accounts = list(account_repo.list_by_entity(entity1.id))

        assert len(accounts) == 2
        names = {a.name for a in accounts}
        assert names == {"Account 1", "Account 2"}

    def test_list_investment_accounts_all(
        self, account_repo: "PostgresAccountRepository", persisted_entity: "Entity"
    ) -> None:
        brokerage = Account(
            name="Brokerage",
            entity_id=persisted_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        checking = Account(
            name="Checking",
            entity_id=persisted_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
        )
        ira = Account(
            name="IRA",
            entity_id=persisted_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.IRA,
        )
        account_repo.add(brokerage)
        account_repo.add(checking)
        account_repo.add(ira)

        investment_accounts = list(account_repo.list_investment_accounts())

        assert len(investment_accounts) == 2
        names = {a.name for a in investment_accounts}
        assert names == {"Brokerage", "IRA"}

    def test_list_investment_accounts_by_entity(
        self,
        account_repo: "PostgresAccountRepository",
        entity_repo: "PostgresEntityRepository",
    ) -> None:
        entity1 = Entity(name="Entity 1", entity_type=EntityType.TRUST)
        entity2 = Entity(name="Entity 2", entity_type=EntityType.LLC)
        entity_repo.add(entity1)
        entity_repo.add(entity2)

        brokerage1 = Account(
            name="Brokerage 1",
            entity_id=entity1.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        brokerage2 = Account(
            name="Brokerage 2",
            entity_id=entity2.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        account_repo.add(brokerage1)
        account_repo.add(brokerage2)

        accounts = list(account_repo.list_investment_accounts(entity1.id))

        assert len(accounts) == 1
        assert accounts[0].name == "Brokerage 1"

    def test_update_account(
        self, account_repo: "PostgresAccountRepository", persisted_entity: "Entity"
    ) -> None:
        account = Account(
            name="Old Name",
            entity_id=persisted_entity.id,
            account_type=AccountType.ASSET,
        )
        account_repo.add(account)

        account.name = "New Name"
        account.is_active = False
        account_repo.update(account)

        retrieved = account_repo.get(account.id)
        assert retrieved is not None
        assert retrieved.name == "New Name"
        assert retrieved.is_active is False

    def test_delete_account(
        self, account_repo: "PostgresAccountRepository", persisted_entity: "Entity"
    ) -> None:
        account = Account(
            name="To Delete",
            entity_id=persisted_entity.id,
            account_type=AccountType.ASSET,
        )
        account_repo.add(account)

        account_repo.delete(account.id)

        assert account_repo.get(account.id) is None


# ===== Security Repository Tests =====


class TestPostgresSecurityRepository:
    def test_add_and_get_security(
        self, security_repo: "PostgresSecurityRepository"
    ) -> None:
        security = Security(
            symbol="AAPL",
            name="Apple Inc.",
            cusip="037833100",
            isin="US0378331005",
            asset_class=AssetClass.EQUITY,
        )

        security_repo.add(security)
        retrieved = security_repo.get(security.id)

        assert retrieved is not None
        assert retrieved.id == security.id
        assert retrieved.symbol == "AAPL"
        assert retrieved.name == "Apple Inc."
        assert retrieved.cusip == "037833100"
        assert retrieved.isin == "US0378331005"
        assert retrieved.asset_class == AssetClass.EQUITY

    def test_get_nonexistent_security_returns_none(
        self, security_repo: "PostgresSecurityRepository"
    ) -> None:
        result = security_repo.get(uuid4())
        assert result is None

    def test_get_by_symbol(self, security_repo: "PostgresSecurityRepository") -> None:
        security = Security(symbol="MSFT", name="Microsoft Corp")
        security_repo.add(security)

        retrieved = security_repo.get_by_symbol("MSFT")

        assert retrieved is not None
        assert retrieved.symbol == "MSFT"

    def test_get_by_symbol_not_found(
        self, security_repo: "PostgresSecurityRepository"
    ) -> None:
        result = security_repo.get_by_symbol("NONEXISTENT")
        assert result is None

    def test_get_by_cusip(self, security_repo: "PostgresSecurityRepository") -> None:
        security = Security(symbol="GOOGL", name="Alphabet Inc.", cusip="02079K305")
        security_repo.add(security)

        retrieved = security_repo.get_by_cusip("02079K305")

        assert retrieved is not None
        assert retrieved.symbol == "GOOGL"

    def test_get_by_cusip_not_found(
        self, security_repo: "PostgresSecurityRepository"
    ) -> None:
        result = security_repo.get_by_cusip("000000000")
        assert result is None

    def test_list_all_securities(
        self, security_repo: "PostgresSecurityRepository"
    ) -> None:
        sec1 = Security(symbol="AAPL", name="Apple Inc.")
        sec2 = Security(symbol="GOOGL", name="Alphabet Inc.")
        security_repo.add(sec1)
        security_repo.add(sec2)

        securities = list(security_repo.list_all())

        assert len(securities) == 2
        symbols = {s.symbol for s in securities}
        assert symbols == {"AAPL", "GOOGL"}

    def test_list_qsbs_eligible(
        self, security_repo: "PostgresSecurityRepository"
    ) -> None:
        regular = Security(symbol="AAPL", name="Apple Inc.")
        qsbs = Security(
            symbol="STARTUP",
            name="Startup Corp",
            is_qsbs_eligible=True,
            qsbs_qualification_date=date(2020, 1, 15),
        )
        security_repo.add(regular)
        security_repo.add(qsbs)

        qsbs_securities = list(security_repo.list_qsbs_eligible())

        assert len(qsbs_securities) == 1
        assert qsbs_securities[0].symbol == "STARTUP"
        assert qsbs_securities[0].is_qsbs_eligible is True
        assert qsbs_securities[0].qsbs_qualification_date == date(2020, 1, 15)

    def test_update_security(self, security_repo: "PostgresSecurityRepository") -> None:
        security = Security(symbol="OLD", name="Old Name")
        security_repo.add(security)

        security.name = "New Name"
        security.is_qsbs_eligible = True
        security.qsbs_qualification_date = date(2024, 1, 1)
        security_repo.update(security)

        retrieved = security_repo.get(security.id)
        assert retrieved is not None
        assert retrieved.name == "New Name"
        assert retrieved.is_qsbs_eligible is True
        assert retrieved.qsbs_qualification_date == date(2024, 1, 1)


# ===== Position Repository Tests =====


class TestPostgresPositionRepository:
    @pytest.fixture
    def test_data(
        self,
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
        security_repo: "PostgresSecurityRepository",
    ) -> dict:
        entity = Entity(name="Test Entity", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        account = Account(
            name="Brokerage",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        account_repo.add(account)

        security = Security(symbol="AAPL", name="Apple Inc.")
        security_repo.add(security)

        return {"entity": entity, "account": account, "security": security}

    def test_add_and_get_position(
        self, position_repo: "PostgresPositionRepository", test_data: dict
    ) -> None:
        position = Position(
            account_id=test_data["account"].id,
            security_id=test_data["security"].id,
        )
        position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )
        position.update_market_value(Decimal("175.00"))

        position_repo.add(position)
        retrieved = position_repo.get(position.id)

        assert retrieved is not None
        assert retrieved.id == position.id
        assert retrieved.account_id == test_data["account"].id
        assert retrieved.security_id == test_data["security"].id
        assert retrieved.quantity == Quantity(Decimal("100"))
        assert retrieved.cost_basis == Money(Decimal("15000.00"))
        assert retrieved.market_value == Money(Decimal("17500.00"))

    def test_get_nonexistent_position_returns_none(
        self, position_repo: "PostgresPositionRepository"
    ) -> None:
        result = position_repo.get(uuid4())
        assert result is None

    def test_get_by_account_and_security(
        self, position_repo: "PostgresPositionRepository", test_data: dict
    ) -> None:
        position = Position(
            account_id=test_data["account"].id,
            security_id=test_data["security"].id,
        )
        position_repo.add(position)

        retrieved = position_repo.get_by_account_and_security(
            test_data["account"].id, test_data["security"].id
        )

        assert retrieved is not None
        assert retrieved.id == position.id

    def test_get_by_account_and_security_not_found(
        self, position_repo: "PostgresPositionRepository", test_data: dict
    ) -> None:
        result = position_repo.get_by_account_and_security(
            test_data["account"].id, uuid4()
        )
        assert result is None

    def test_list_by_account(
        self,
        position_repo: "PostgresPositionRepository",
        security_repo: "PostgresSecurityRepository",
        test_data: dict,
    ) -> None:
        sec2 = Security(symbol="GOOGL", name="Alphabet Inc.")
        security_repo.add(sec2)

        pos1 = Position(
            account_id=test_data["account"].id,
            security_id=test_data["security"].id,
        )
        pos2 = Position(
            account_id=test_data["account"].id,
            security_id=sec2.id,
        )
        position_repo.add(pos1)
        position_repo.add(pos2)

        positions = list(position_repo.list_by_account(test_data["account"].id))

        assert len(positions) == 2

    def test_list_by_security(
        self,
        position_repo: "PostgresPositionRepository",
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
        test_data: dict,
    ) -> None:
        entity2 = Entity(name="Entity 2", entity_type=EntityType.LLC)
        entity_repo.add(entity2)
        account2 = Account(
            name="Brokerage 2",
            entity_id=entity2.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        account_repo.add(account2)

        pos1 = Position(
            account_id=test_data["account"].id,
            security_id=test_data["security"].id,
        )
        pos2 = Position(
            account_id=account2.id,
            security_id=test_data["security"].id,
        )
        position_repo.add(pos1)
        position_repo.add(pos2)

        positions = list(position_repo.list_by_security(test_data["security"].id))

        assert len(positions) == 2

    def test_list_by_entity(
        self,
        position_repo: "PostgresPositionRepository",
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
        test_data: dict,
    ) -> None:
        # Create second entity with account
        entity2 = Entity(name="Entity 2", entity_type=EntityType.LLC)
        entity_repo.add(entity2)
        account2 = Account(
            name="Brokerage 2",
            entity_id=entity2.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        account_repo.add(account2)

        # Positions for entity 1
        pos1 = Position(
            account_id=test_data["account"].id,
            security_id=test_data["security"].id,
        )
        # Position for entity 2
        pos2 = Position(
            account_id=account2.id,
            security_id=test_data["security"].id,
        )
        position_repo.add(pos1)
        position_repo.add(pos2)

        positions = list(position_repo.list_by_entity(test_data["entity"].id))

        assert len(positions) == 1
        assert positions[0].account_id == test_data["account"].id

    def test_update_position(
        self, position_repo: "PostgresPositionRepository", test_data: dict
    ) -> None:
        position = Position(
            account_id=test_data["account"].id,
            security_id=test_data["security"].id,
        )
        position_repo.add(position)

        position.update_from_lots(
            total_quantity=Quantity(Decimal("200")),
            total_cost=Money(Decimal("30000.00")),
        )
        position.update_market_value(Decimal("180.00"))
        position_repo.update(position)

        retrieved = position_repo.get(position.id)
        assert retrieved is not None
        assert retrieved.quantity == Quantity(Decimal("200"))
        assert retrieved.cost_basis == Money(Decimal("30000.00"))
        assert retrieved.market_value == Money(Decimal("36000.00"))


# ===== Transaction Repository Tests =====


class TestPostgresTransactionRepository:
    @pytest.fixture
    def test_accounts(
        self,
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
    ) -> dict:
        entity = Entity(name="Test Entity", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        cash = Account(
            name="Cash",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
        )
        income = Account(
            name="Income",
            entity_id=entity.id,
            account_type=AccountType.INCOME,
        )
        account_repo.add(cash)
        account_repo.add(income)

        return {"entity": entity, "cash": cash, "income": income}

    def test_add_and_get_transaction(
        self, transaction_repo: "PostgresTransactionRepository", test_accounts: dict
    ) -> None:
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Interest payment",
            reference="REF-001",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )

        transaction_repo.add(txn)
        retrieved = transaction_repo.get(txn.id)

        assert retrieved is not None
        assert retrieved.id == txn.id
        assert retrieved.transaction_date == date(2024, 1, 15)
        assert retrieved.memo == "Interest payment"
        assert retrieved.reference == "REF-001"
        assert len(retrieved.entries) == 2
        assert retrieved.is_balanced

    def test_get_nonexistent_transaction_returns_none(
        self, transaction_repo: "PostgresTransactionRepository"
    ) -> None:
        result = transaction_repo.get(uuid4())
        assert result is None

    def test_transaction_with_reversal(
        self, transaction_repo: "PostgresTransactionRepository", test_accounts: dict
    ) -> None:
        original = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Original",
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(original)

        reversal = Transaction(
            transaction_date=date(2024, 1, 16),
            memo="Reversal",
            reverses_transaction_id=original.id,
        )
        reversal.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        reversal.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(reversal)

        reversals = list(transaction_repo.get_reversals(original.id))
        assert len(reversals) == 1
        assert reversals[0].reverses_transaction_id == original.id

    def test_list_by_account(
        self, transaction_repo: "PostgresTransactionRepository", test_accounts: dict
    ) -> None:
        txn1 = Transaction(transaction_date=date(2024, 1, 15))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )

        txn2 = Transaction(transaction_date=date(2024, 2, 15))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        transaction_repo.add(txn1)
        transaction_repo.add(txn2)

        # All transactions for cash account
        transactions = list(transaction_repo.list_by_account(test_accounts["cash"].id))
        assert len(transactions) == 2

        # With date filter
        filtered = list(
            transaction_repo.list_by_account(
                test_accounts["cash"].id,
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 28),
            )
        )
        assert len(filtered) == 1
        assert filtered[0].transaction_date == date(2024, 2, 15)

    def test_list_by_entity(
        self,
        transaction_repo: "PostgresTransactionRepository",
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
        test_accounts: dict,
    ) -> None:
        # Create second entity
        entity2 = Entity(name="Entity 2", entity_type=EntityType.LLC)
        entity_repo.add(entity2)
        cash2 = Account(
            name="Cash 2",
            entity_id=entity2.id,
            account_type=AccountType.ASSET,
        )
        income2 = Account(
            name="Income 2",
            entity_id=entity2.id,
            account_type=AccountType.INCOME,
        )
        account_repo.add(cash2)
        account_repo.add(income2)

        # Transaction for entity 1
        txn1 = Transaction(transaction_date=date(2024, 1, 15))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )

        # Transaction for entity 2
        txn2 = Transaction(transaction_date=date(2024, 1, 16))
        txn2.add_entry(
            Entry(
                account_id=cash2.id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=income2.id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        transaction_repo.add(txn1)
        transaction_repo.add(txn2)

        transactions = list(transaction_repo.list_by_entity(test_accounts["entity"].id))
        assert len(transactions) == 1
        assert transactions[0].id == txn1.id

    def test_list_by_date_range(
        self, transaction_repo: "PostgresTransactionRepository", test_accounts: dict
    ) -> None:
        txn1 = Transaction(transaction_date=date(2024, 1, 15))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )

        txn2 = Transaction(transaction_date=date(2024, 2, 15))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )

        txn3 = Transaction(transaction_date=date(2024, 3, 15))
        txn3.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("300.00")),
            )
        )
        txn3.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("300.00")),
            )
        )
        transaction_repo.add(txn1)
        transaction_repo.add(txn2)
        transaction_repo.add(txn3)

        transactions = list(
            transaction_repo.list_by_date_range(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 2, 28),
            )
        )

        assert len(transactions) == 2
        dates = [t.transaction_date for t in transactions]
        assert date(2024, 1, 15) in dates
        assert date(2024, 2, 15) in dates


# ===== Tax Lot Repository Tests =====


class TestPostgresTaxLotRepository:
    @pytest.fixture
    def test_position(
        self,
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
        security_repo: "PostgresSecurityRepository",
        position_repo: "PostgresPositionRepository",
    ) -> "Position":
        entity = Entity(name="Test Entity", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        account = Account(
            name="Brokerage",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        account_repo.add(account)

        security = Security(symbol="AAPL", name="Apple Inc.")
        security_repo.add(security)

        position = Position(
            account_id=account.id,
            security_id=security.id,
        )
        position_repo.add(position)
        return position

    def test_add_and_get_tax_lot(
        self, tax_lot_repo: "PostgresTaxLotRepository", test_position: "Position"
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("100")),
            acquisition_type=AcquisitionType.PURCHASE,
            is_covered=True,
            reference="BUY-001",
        )

        tax_lot_repo.add(lot)
        retrieved = tax_lot_repo.get(lot.id)

        assert retrieved is not None
        assert retrieved.id == lot.id
        assert retrieved.position_id == test_position.id
        assert retrieved.acquisition_date == date(2023, 6, 15)
        assert retrieved.cost_per_share == Money(Decimal("150.00"))
        assert retrieved.original_quantity == Quantity(Decimal("100"))
        assert retrieved.remaining_quantity == Quantity(Decimal("100"))
        assert retrieved.acquisition_type == AcquisitionType.PURCHASE
        assert retrieved.is_covered is True
        assert retrieved.reference == "BUY-001"

    def test_get_nonexistent_tax_lot_returns_none(
        self, tax_lot_repo: "PostgresTaxLotRepository"
    ) -> None:
        result = tax_lot_repo.get(uuid4())
        assert result is None

    def test_list_by_position(
        self, tax_lot_repo: "PostgresTaxLotRepository", test_position: "Position"
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("140.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        lots = list(tax_lot_repo.list_by_position(test_position.id))

        assert len(lots) == 2
        # Should be ordered by acquisition date
        assert lots[0].acquisition_date == date(2023, 1, 15)
        assert lots[1].acquisition_date == date(2023, 6, 15)

    def test_list_open_by_position(
        self, tax_lot_repo: "PostgresTaxLotRepository", test_position: "Position"
    ) -> None:
        open_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("140.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        closed_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        # Sell all shares from the second lot
        closed_lot.sell(Quantity(Decimal("50")), date(2024, 1, 15))

        tax_lot_repo.add(open_lot)
        tax_lot_repo.add(closed_lot)

        open_lots = list(tax_lot_repo.list_open_by_position(test_position.id))

        assert len(open_lots) == 1
        assert open_lots[0].id == open_lot.id

    def test_list_by_acquisition_date_range(
        self, tax_lot_repo: "PostgresTaxLotRepository", test_position: "Position"
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("140.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("40")),
        )
        lot3 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 12, 15),
            cost_per_share=Money(Decimal("160.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)
        tax_lot_repo.add(lot3)

        lots = list(
            tax_lot_repo.list_by_acquisition_date_range(
                test_position.id,
                start_date=date(2023, 4, 1),
                end_date=date(2023, 9, 30),
            )
        )

        assert len(lots) == 1
        assert lots[0].acquisition_date == date(2023, 6, 15)

    def test_list_wash_sale_candidates(
        self, tax_lot_repo: "PostgresTaxLotRepository", test_position: "Position"
    ) -> None:
        # Lot acquired 20 days before sale - should be included
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2024, 1, 1),
            cost_per_share=Money(Decimal("140.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        # Lot acquired 60 days before sale - should not be included
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 11, 1),
            cost_per_share=Money(Decimal("135.00")),
            original_quantity=Quantity(Decimal("20")),
        )
        # Lot acquired 15 days after sale - should be included
        lot3 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2024, 2, 5),
            cost_per_share=Money(Decimal("145.00")),
            original_quantity=Quantity(Decimal("25")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)
        tax_lot_repo.add(lot3)

        sale_date = date(2024, 1, 20)
        candidates = list(
            tax_lot_repo.list_wash_sale_candidates(test_position.id, sale_date)
        )

        assert len(candidates) == 2
        acquisition_dates = {lot.acquisition_date for lot in candidates}
        assert date(2024, 1, 1) in acquisition_dates
        assert date(2024, 2, 5) in acquisition_dates
        assert date(2023, 11, 1) not in acquisition_dates

    def test_update_tax_lot(
        self, tax_lot_repo: "PostgresTaxLotRepository", test_position: "Position"
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(lot)

        # Sell some shares
        lot.sell(Quantity(Decimal("30")), date(2024, 1, 15))
        lot.mark_wash_sale(Money(Decimal("50.00")))
        tax_lot_repo.update(lot)

        retrieved = tax_lot_repo.get(lot.id)
        assert retrieved is not None
        assert retrieved.remaining_quantity == Quantity(Decimal("70"))
        assert retrieved.wash_sale_disallowed is True
        assert retrieved.wash_sale_adjustment == Money(Decimal("50.00"))

    def test_tax_lot_preserves_all_fields(
        self, tax_lot_repo: "PostgresTaxLotRepository", test_position: "Position"
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00"), "USD"),
            original_quantity=Quantity(Decimal("100")),
            acquisition_type=AcquisitionType.GIFT,
            is_covered=False,
            wash_sale_disallowed=True,
            wash_sale_adjustment=Money(Decimal("25.00")),
            reference="GIFT-001",
        )
        original_created_at = lot.created_at

        tax_lot_repo.add(lot)
        retrieved = tax_lot_repo.get(lot.id)

        assert retrieved is not None
        assert retrieved.acquisition_type == AcquisitionType.GIFT
        assert retrieved.is_covered is False
        assert retrieved.wash_sale_disallowed is True
        assert retrieved.wash_sale_adjustment == Money(Decimal("25.00"))
        assert retrieved.reference == "GIFT-001"
        assert retrieved.created_at == original_created_at


# ===== Database Tests =====


class TestPostgresDatabase:
    def test_initialize_creates_tables(self, db: "PostgresDatabase") -> None:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            tables = cur.fetchall()
        table_names = {row["table_name"] for row in tables}

        assert "entities" in table_names
        assert "accounts" in table_names
        assert "securities" in table_names
        assert "positions" in table_names
        assert "transactions" in table_names
        assert "entries" in table_names
        assert "tax_lots" in table_names

    def test_get_connection_returns_same_connection(
        self, db: "PostgresDatabase"
    ) -> None:
        conn1 = db.get_connection()
        conn2 = db.get_connection()

        assert conn1 is conn2

    def test_close_releases_connection(self) -> None:
        assert POSTGRES_URL is not None
        db = PostgresDatabase(POSTGRES_URL)
        db.get_connection()
        db.close()

        # After close, get_connection should create a new connection
        assert db._connection is None

    def test_initialize_is_idempotent(self, db: "PostgresDatabase") -> None:
        db.initialize()  # Should not raise

        # Tables should still exist
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            tables = cur.fetchall()
        assert len(tables) > 0


# ===== Integration Tests =====


class TestPostgresRepositoryIntegration:
    def test_full_workflow(
        self,
        db: "PostgresDatabase",
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
        security_repo: "PostgresSecurityRepository",
        position_repo: "PostgresPositionRepository",
        transaction_repo: "PostgresTransactionRepository",
        tax_lot_repo: "PostgresTaxLotRepository",
    ) -> None:
        """Test a complete workflow: create entity, account, security, buy stock, record transaction."""
        # Create entity
        entity = Entity(name="Smith Family Trust", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        # Create accounts
        brokerage = Account(
            name="Schwab Brokerage",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        cash = Account(
            name="Cash",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CASH,
        )
        account_repo.add(brokerage)
        account_repo.add(cash)

        # Create security
        security = Security(
            symbol="AAPL",
            name="Apple Inc.",
            cusip="037833100",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(security)

        # Create position
        position = Position(
            account_id=brokerage.id,
            security_id=security.id,
        )
        position_repo.add(position)

        # Create tax lot for purchase
        lot = TaxLot(
            position_id=position.id,
            acquisition_date=date(2024, 1, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(lot)

        # Update position from lot
        position.update_from_lots(
            total_quantity=lot.original_quantity,
            total_cost=lot.total_cost,
        )
        position_repo.update(position)

        # Record purchase transaction
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Buy 100 AAPL @ $150",
            reference="TXN-001",
        )
        txn.add_entry(
            Entry(
                account_id=brokerage.id,
                debit_amount=Money(Decimal("15000.00")),
                memo="AAPL purchase",
                tax_lot_id=lot.id,
            )
        )
        txn.add_entry(
            Entry(
                account_id=cash.id,
                credit_amount=Money(Decimal("15000.00")),
                memo="Cash paid for AAPL",
            )
        )
        transaction_repo.add(txn)

        # Verify everything was persisted correctly
        retrieved_entity = entity_repo.get(entity.id)
        assert retrieved_entity is not None
        assert retrieved_entity.name == "Smith Family Trust"

        retrieved_accounts = list(account_repo.list_by_entity(entity.id))
        assert len(retrieved_accounts) == 2

        retrieved_security = security_repo.get_by_symbol("AAPL")
        assert retrieved_security is not None

        retrieved_position = position_repo.get_by_account_and_security(
            brokerage.id, security.id
        )
        assert retrieved_position is not None
        assert retrieved_position.quantity == Quantity(Decimal("100"))
        assert retrieved_position.cost_basis == Money(Decimal("15000.00"))

        retrieved_lots = list(tax_lot_repo.list_by_position(position.id))
        assert len(retrieved_lots) == 1
        assert retrieved_lots[0].cost_per_share == Money(Decimal("150.00"))

        retrieved_txn = transaction_repo.get(txn.id)
        assert retrieved_txn is not None
        assert retrieved_txn.is_balanced
        assert len(retrieved_txn.entries) == 2


# ===== Exchange Rate Repository Tests =====


class TestPostgresExchangeRateRepository:
    def test_add_and_get_exchange_rate(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 15),
            source=ExchangeRateSource.ECB,
        )

        exchange_rate_repo.add(rate)
        retrieved = exchange_rate_repo.get(rate.id)

        assert retrieved is not None
        assert retrieved.id == rate.id
        assert retrieved.from_currency == "USD"
        assert retrieved.to_currency == "EUR"
        assert retrieved.rate == Decimal("0.85")
        assert retrieved.effective_date == date(2024, 1, 15)
        assert retrieved.source == ExchangeRateSource.ECB

    def test_get_nonexistent_rate_returns_none(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        result = exchange_rate_repo.get(uuid4())
        assert result is None

    def test_get_rate_by_pair_and_date(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="GBP",
            rate=Decimal("0.79"),
            effective_date=date(2024, 1, 15),
        )
        exchange_rate_repo.add(rate)

        retrieved = exchange_rate_repo.get_rate("USD", "GBP", date(2024, 1, 15))

        assert retrieved is not None
        assert retrieved.rate == Decimal("0.79")

    def test_get_rate_not_found(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        result = exchange_rate_repo.get_rate("USD", "JPY", date(2024, 1, 15))
        assert result is None

    def test_get_latest_rate(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.84"),
            effective_date=date(2024, 1, 10),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 15),
        )
        rate3 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.86"),
            effective_date=date(2024, 1, 20),
        )
        exchange_rate_repo.add(rate1)
        exchange_rate_repo.add(rate2)
        exchange_rate_repo.add(rate3)

        latest = exchange_rate_repo.get_latest_rate("USD", "EUR")

        assert latest is not None
        assert latest.rate == Decimal("0.86")
        assert latest.effective_date == date(2024, 1, 20)

    def test_get_latest_rate_not_found(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        result = exchange_rate_repo.get_latest_rate("USD", "CHF")
        assert result is None

    def test_list_by_currency_pair(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.84"),
            effective_date=date(2024, 1, 10),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 15),
        )
        rate3 = ExchangeRate(
            from_currency="USD",
            to_currency="GBP",
            rate=Decimal("0.79"),
            effective_date=date(2024, 1, 15),
        )
        exchange_rate_repo.add(rate1)
        exchange_rate_repo.add(rate2)
        exchange_rate_repo.add(rate3)

        rates = list(exchange_rate_repo.list_by_currency_pair("USD", "EUR"))

        assert len(rates) == 2
        assert rates[0].effective_date == date(2024, 1, 10)
        assert rates[1].effective_date == date(2024, 1, 15)

    def test_list_by_currency_pair_with_date_filter(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.84"),
            effective_date=date(2024, 1, 5),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 15),
        )
        rate3 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.86"),
            effective_date=date(2024, 1, 25),
        )
        exchange_rate_repo.add(rate1)
        exchange_rate_repo.add(rate2)
        exchange_rate_repo.add(rate3)

        filtered = list(
            exchange_rate_repo.list_by_currency_pair(
                "USD",
                "EUR",
                start_date=date(2024, 1, 10),
                end_date=date(2024, 1, 20),
            )
        )

        assert len(filtered) == 1
        assert filtered[0].rate == Decimal("0.85")

    def test_list_by_date(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 15),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="GBP",
            rate=Decimal("0.79"),
            effective_date=date(2024, 1, 15),
        )
        rate3 = ExchangeRate(
            from_currency="EUR",
            to_currency="GBP",
            rate=Decimal("0.93"),
            effective_date=date(2024, 1, 16),
        )
        exchange_rate_repo.add(rate1)
        exchange_rate_repo.add(rate2)
        exchange_rate_repo.add(rate3)

        rates = list(exchange_rate_repo.list_by_date(date(2024, 1, 15)))

        assert len(rates) == 2
        pairs = {(r.from_currency, r.to_currency) for r in rates}
        assert ("USD", "EUR") in pairs
        assert ("USD", "GBP") in pairs

    def test_delete_exchange_rate(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 15),
        )
        exchange_rate_repo.add(rate)

        exchange_rate_repo.delete(rate.id)

        assert exchange_rate_repo.get(rate.id) is None

    def test_exchange_rate_preserves_timestamps(
        self, exchange_rate_repo: "PostgresExchangeRateRepository"
    ) -> None:
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 15),
        )
        original_created = rate.created_at

        exchange_rate_repo.add(rate)
        retrieved = exchange_rate_repo.get(rate.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created


# ===== Vendor Repository Tests =====


class TestPostgresVendorRepository:
    def test_add_and_get_vendor(self, vendor_repo: "PostgresVendorRepository") -> None:
        vendor = Vendor(
            name="Acme Corp",
            category="supplies",
            tax_id="12-3456789",
            is_1099_eligible=True,
            contact_email="billing@acme.com",
            contact_phone="555-1234",
            notes="Preferred vendor",
        )

        vendor_repo.add(vendor)
        retrieved = vendor_repo.get(vendor.id)

        assert retrieved is not None
        assert retrieved.id == vendor.id
        assert retrieved.name == "Acme Corp"
        assert retrieved.category == "supplies"
        assert retrieved.tax_id == "12-3456789"
        assert retrieved.is_1099_eligible is True
        assert retrieved.contact_email == "billing@acme.com"
        assert retrieved.contact_phone == "555-1234"
        assert retrieved.notes == "Preferred vendor"
        assert retrieved.is_active is True

    def test_get_nonexistent_vendor_returns_none(
        self, vendor_repo: "PostgresVendorRepository"
    ) -> None:
        result = vendor_repo.get(uuid4())
        assert result is None

    def test_update_vendor(self, vendor_repo: "PostgresVendorRepository") -> None:
        vendor = Vendor(name="Old Name", category="misc")
        vendor_repo.add(vendor)

        vendor.name = "New Name"
        vendor.category = "services"
        vendor.is_1099_eligible = True
        vendor_repo.update(vendor)

        retrieved = vendor_repo.get(vendor.id)
        assert retrieved is not None
        assert retrieved.name == "New Name"
        assert retrieved.category == "services"
        assert retrieved.is_1099_eligible is True

    def test_delete_vendor(self, vendor_repo: "PostgresVendorRepository") -> None:
        vendor = Vendor(name="To Delete")
        vendor_repo.add(vendor)

        vendor_repo.delete(vendor.id)

        assert vendor_repo.get(vendor.id) is None

    def test_list_all_active_only(
        self, vendor_repo: "PostgresVendorRepository"
    ) -> None:
        active = Vendor(name="Active Vendor")
        inactive = Vendor(name="Inactive Vendor", is_active=False)
        vendor_repo.add(active)
        vendor_repo.add(inactive)

        vendors = list(vendor_repo.list_all(include_inactive=False))

        assert len(vendors) == 1
        assert vendors[0].name == "Active Vendor"

    def test_list_all_including_inactive(
        self, vendor_repo: "PostgresVendorRepository"
    ) -> None:
        active = Vendor(name="Active Vendor")
        inactive = Vendor(name="Inactive Vendor", is_active=False)
        vendor_repo.add(active)
        vendor_repo.add(inactive)

        vendors = list(vendor_repo.list_all(include_inactive=True))

        assert len(vendors) == 2

    def test_list_by_category(self, vendor_repo: "PostgresVendorRepository") -> None:
        v1 = Vendor(name="Vendor A", category="supplies")
        v2 = Vendor(name="Vendor B", category="services")
        v3 = Vendor(name="Vendor C", category="supplies")
        vendor_repo.add(v1)
        vendor_repo.add(v2)
        vendor_repo.add(v3)

        vendors = list(vendor_repo.list_by_category("supplies"))

        assert len(vendors) == 2
        names = {v.name for v in vendors}
        assert names == {"Vendor A", "Vendor C"}

    def test_search_by_name(self, vendor_repo: "PostgresVendorRepository") -> None:
        v1 = Vendor(name="Acme Corporation")
        v2 = Vendor(name="Beta Inc")
        v3 = Vendor(name="Acme Supply Co")
        vendor_repo.add(v1)
        vendor_repo.add(v2)
        vendor_repo.add(v3)

        vendors = list(vendor_repo.search_by_name("Acme"))

        assert len(vendors) == 2
        names = {v.name for v in vendors}
        assert names == {"Acme Corporation", "Acme Supply Co"}

    def test_get_by_tax_id(self, vendor_repo: "PostgresVendorRepository") -> None:
        vendor = Vendor(name="Tax Vendor", tax_id="98-7654321")
        vendor_repo.add(vendor)

        retrieved = vendor_repo.get_by_tax_id("98-7654321")

        assert retrieved is not None
        assert retrieved.name == "Tax Vendor"

    def test_get_by_tax_id_not_found(
        self, vendor_repo: "PostgresVendorRepository"
    ) -> None:
        result = vendor_repo.get_by_tax_id("00-0000000")
        assert result is None

    def test_vendor_preserves_timestamps(
        self, vendor_repo: "PostgresVendorRepository"
    ) -> None:
        vendor = Vendor(name="Timestamp Test")
        original_created = vendor.created_at
        original_updated = vendor.updated_at

        vendor_repo.add(vendor)
        retrieved = vendor_repo.get(vendor.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
        assert retrieved.updated_at == original_updated

    def test_vendor_with_default_account(
        self,
        vendor_repo: "PostgresVendorRepository",
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
    ) -> None:
        entity = Entity(name="Test Entity", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        account = Account(
            name="Expense Account",
            entity_id=entity.id,
            account_type=AccountType.EXPENSE,
        )
        account_repo.add(account)

        vendor = Vendor(
            name="Vendor with Default",
            default_account_id=account.id,
            default_category="utilities",
        )
        vendor_repo.add(vendor)

        retrieved = vendor_repo.get(vendor.id)
        assert retrieved is not None
        assert retrieved.default_account_id == account.id
        assert retrieved.default_category == "utilities"


# ===== Budget Repository Tests =====


class TestPostgresBudgetRepository:
    @pytest.fixture
    def persisted_entity(self, entity_repo: "PostgresEntityRepository") -> "Entity":
        entity = Entity(name="Budget Test Entity", entity_type=EntityType.TRUST)
        entity_repo.add(entity)
        return entity

    def test_add_and_get_budget(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="2024 Annual Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        budget_repo.add(budget)
        retrieved = budget_repo.get(budget.id)

        assert retrieved is not None
        assert retrieved.id == budget.id
        assert retrieved.name == "2024 Annual Budget"
        assert retrieved.entity_id == persisted_entity.id
        assert retrieved.period_type == BudgetPeriodType.ANNUAL
        assert retrieved.start_date == date(2024, 1, 1)
        assert retrieved.end_date == date(2024, 12, 31)
        assert retrieved.is_active is True

    def test_get_nonexistent_budget_returns_none(
        self, budget_repo: "PostgresBudgetRepository"
    ) -> None:
        result = budget_repo.get(uuid4())
        assert result is None

    def test_update_budget(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="Old Name",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        budget_repo.add(budget)

        budget.name = "New Name"
        budget.period_type = BudgetPeriodType.QUARTERLY
        budget.end_date = date(2024, 3, 31)
        budget_repo.update(budget)

        retrieved = budget_repo.get(budget.id)
        assert retrieved is not None
        assert retrieved.name == "New Name"
        assert retrieved.period_type == BudgetPeriodType.QUARTERLY
        assert retrieved.end_date == date(2024, 3, 31)

    def test_delete_budget(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="To Delete",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        budget_repo.add(budget)

        budget_repo.delete(budget.id)

        assert budget_repo.get(budget.id) is None

    def test_list_by_entity_active_only(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        active = Budget(
            name="Active Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        inactive = Budget(
            name="Inactive Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            is_active=False,
        )
        budget_repo.add(active)
        budget_repo.add(inactive)

        budgets = list(budget_repo.list_by_entity(persisted_entity.id))

        assert len(budgets) == 1
        assert budgets[0].name == "Active Budget"

    def test_list_by_entity_including_inactive(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        active = Budget(
            name="Active Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        inactive = Budget(
            name="Inactive Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            is_active=False,
        )
        budget_repo.add(active)
        budget_repo.add(inactive)

        budgets = list(
            budget_repo.list_by_entity(persisted_entity.id, include_inactive=True)
        )

        assert len(budgets) == 2

    def test_get_active_for_date(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget_q1 = Budget(
            name="Q1 2024",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.QUARTERLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )
        budget_q2 = Budget(
            name="Q2 2024",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.QUARTERLY,
            start_date=date(2024, 4, 1),
            end_date=date(2024, 6, 30),
        )
        budget_repo.add(budget_q1)
        budget_repo.add(budget_q2)

        retrieved = budget_repo.get_active_for_date(
            persisted_entity.id, date(2024, 2, 15)
        )

        assert retrieved is not None
        assert retrieved.name == "Q1 2024"

    def test_get_active_for_date_returns_none_when_no_match(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="Q1 2024",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.QUARTERLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )
        budget_repo.add(budget)

        result = budget_repo.get_active_for_date(persisted_entity.id, date(2024, 7, 15))

        assert result is None

    def test_add_and_get_line_items(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="Test Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        budget_repo.add(budget)

        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Utilities",
            budgeted_amount=Money(Decimal("500.00")),
            notes="Electric and water",
        )
        budget_repo.add_line_item(line_item)

        line_items = list(budget_repo.get_line_items(budget.id))

        assert len(line_items) == 1
        assert line_items[0].id == line_item.id
        assert line_items[0].category == "Utilities"
        assert line_items[0].budgeted_amount == Money(Decimal("500.00"))
        assert line_items[0].notes == "Electric and water"

    def test_update_line_item(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="Test Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        budget_repo.add(budget)

        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Utilities",
            budgeted_amount=Money(Decimal("500.00")),
        )
        budget_repo.add_line_item(line_item)

        line_item.budgeted_amount = Money(Decimal("600.00"))
        line_item.notes = "Updated amount"
        budget_repo.update_line_item(line_item)

        line_items = list(budget_repo.get_line_items(budget.id))
        assert len(line_items) == 1
        assert line_items[0].budgeted_amount == Money(Decimal("600.00"))
        assert line_items[0].notes == "Updated amount"

    def test_delete_line_item(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="Test Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        budget_repo.add(budget)

        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Utilities",
            budgeted_amount=Money(Decimal("500.00")),
        )
        budget_repo.add_line_item(line_item)

        budget_repo.delete_line_item(line_item.id)

        line_items = list(budget_repo.get_line_items(budget.id))
        assert len(line_items) == 0

    def test_line_items_cascade_delete(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="Test Budget",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        budget_repo.add(budget)

        line_item1 = BudgetLineItem(
            budget_id=budget.id,
            category="Utilities",
            budgeted_amount=Money(Decimal("500.00")),
        )
        line_item2 = BudgetLineItem(
            budget_id=budget.id,
            category="Groceries",
            budgeted_amount=Money(Decimal("800.00")),
        )
        budget_repo.add_line_item(line_item1)
        budget_repo.add_line_item(line_item2)

        budget_repo.delete(budget.id)

        line_items = list(budget_repo.get_line_items(budget.id))
        assert len(line_items) == 0

    def test_budget_preserves_timestamps(
        self, budget_repo: "PostgresBudgetRepository", persisted_entity: "Entity"
    ) -> None:
        budget = Budget(
            name="Timestamp Test",
            entity_id=persisted_entity.id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        original_created = budget.created_at
        original_updated = budget.updated_at

        budget_repo.add(budget)
        retrieved = budget_repo.get(budget.id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
        assert retrieved.updated_at == original_updated

    def test_line_item_with_account_id(
        self,
        budget_repo: "PostgresBudgetRepository",
        entity_repo: "PostgresEntityRepository",
        account_repo: "PostgresAccountRepository",
    ) -> None:
        entity = Entity(name="Test Entity", entity_type=EntityType.TRUST)
        entity_repo.add(entity)

        account = Account(
            name="Utilities Expense",
            entity_id=entity.id,
            account_type=AccountType.EXPENSE,
        )
        account_repo.add(account)

        budget = Budget(
            name="Test Budget",
            entity_id=entity.id,
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        budget_repo.add(budget)

        line_item = BudgetLineItem(
            budget_id=budget.id,
            category="Utilities",
            budgeted_amount=Money(Decimal("500.00")),
            account_id=account.id,
        )
        budget_repo.add_line_item(line_item)

        line_items = list(budget_repo.get_line_items(budget.id))
        assert len(line_items) == 1
        assert line_items[0].account_id == account.id
