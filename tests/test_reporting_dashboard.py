"""Tests for reporting dashboard methods."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    Money,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.reporting import ReportingServiceImpl


@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def entity_repo(db: SQLiteDatabase) -> SQLiteEntityRepository:
    return SQLiteEntityRepository(db)


@pytest.fixture
def account_repo(db: SQLiteDatabase) -> SQLiteAccountRepository:
    return SQLiteAccountRepository(db)


@pytest.fixture
def transaction_repo(db: SQLiteDatabase) -> SQLiteTransactionRepository:
    return SQLiteTransactionRepository(db)


@pytest.fixture
def position_repo(db: SQLiteDatabase) -> SQLitePositionRepository:
    return SQLitePositionRepository(db)


@pytest.fixture
def tax_lot_repo(db: SQLiteDatabase) -> SQLiteTaxLotRepository:
    return SQLiteTaxLotRepository(db)


@pytest.fixture
def security_repo(db: SQLiteDatabase) -> SQLiteSecurityRepository:
    return SQLiteSecurityRepository(db)


@pytest.fixture
def entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Test LLC",
        entity_type=EntityType.LLC,
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def second_entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Test Trust",
        entity_type=EntityType.TRUST,
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def account(account_repo: SQLiteAccountRepository, entity: Entity) -> Account:
    account = Account(
        name="Operating",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def second_account(
    account_repo: SQLiteAccountRepository, second_entity: Entity
) -> Account:
    account = Account(
        name="Trust Account",
        entity_id=second_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.SAVINGS,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def service(
    entity_repo: SQLiteEntityRepository,
    account_repo: SQLiteAccountRepository,
    transaction_repo: SQLiteTransactionRepository,
    position_repo: SQLitePositionRepository,
    tax_lot_repo: SQLiteTaxLotRepository,
    security_repo: SQLiteSecurityRepository,
) -> ReportingServiceImpl:
    return ReportingServiceImpl(
        entity_repo=entity_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        security_repo=security_repo,
    )


class TestTransactionSummaryByType:
    def test_empty_returns_empty_data(
        self,
        service: ReportingServiceImpl,
    ):
        result = service.transaction_summary_by_type(
            entity_ids=None,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert result["report_name"] == "Transaction Summary by Type"
        assert result["data"] == []
        assert result["totals"]["total_transactions"] == 0

    def test_groups_by_reference_type(
        self,
        service: ReportingServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        account: Account,
    ):
        txn1 = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[Entry(account_id=account.id, debit_amount=Money(Decimal("100")))],
            reference="interest",
        )
        transaction_repo.add(txn1)

        txn2 = Transaction(
            transaction_date=date(2024, 6, 20),
            entries=[Entry(account_id=account.id, debit_amount=Money(Decimal("200")))],
            reference="interest",
        )
        transaction_repo.add(txn2)

        txn3 = Transaction(
            transaction_date=date(2024, 6, 25),
            entries=[Entry(account_id=account.id, debit_amount=Money(Decimal("50")))],
            reference="transfer",
        )
        transaction_repo.add(txn3)

        result = service.transaction_summary_by_type(
            entity_ids=None,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(result["data"]) == 2
        assert result["totals"]["total_transactions"] == 3
        assert result["totals"]["total_amount"] == Decimal("350")


class TestTransactionSummaryByEntity:
    def test_empty_returns_empty_data(
        self,
        service: ReportingServiceImpl,
    ):
        result = service.transaction_summary_by_entity(
            entity_ids=None,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert result["report_name"] == "Transaction Summary by Entity"
        assert result["data"] == []
        assert result["totals"]["total_transactions"] == 0

    def test_groups_by_entity(
        self,
        service: ReportingServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        account: Account,
        second_account: Account,
        entity: Entity,
        second_entity: Entity,
    ):
        txn1 = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[Entry(account_id=account.id, debit_amount=Money(Decimal("100")))],
        )
        transaction_repo.add(txn1)

        txn2 = Transaction(
            transaction_date=date(2024, 6, 20),
            entries=[
                Entry(account_id=second_account.id, debit_amount=Money(Decimal("200")))
            ],
        )
        transaction_repo.add(txn2)

        result = service.transaction_summary_by_entity(
            entity_ids=None,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(result["data"]) == 2
        assert result["totals"]["total_transactions"] == 2

        entity_names = {item["entity_name"] for item in result["data"]}
        assert "Test LLC" in entity_names
        assert "Test Trust" in entity_names


class TestDashboardSummary:
    def test_returns_overview_stats(
        self,
        service: ReportingServiceImpl,
        entity: Entity,
        account: Account,
    ):
        result = service.dashboard_summary(
            entity_ids=None,
            as_of_date=date(2024, 12, 31),
        )

        assert result["report_name"] == "Dashboard Summary"
        assert result["data"]["total_entities"] >= 1
        assert result["data"]["total_accounts"] >= 1
        assert "net_worth" in result["data"]
        assert "total_assets" in result["data"]
        assert "total_liabilities" in result["data"]

    def test_includes_transaction_count(
        self,
        service: ReportingServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        account: Account,
    ):
        txn = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[Entry(account_id=account.id, debit_amount=Money(Decimal("100")))],
        )
        transaction_repo.add(txn)

        result = service.dashboard_summary(
            entity_ids=None,
            as_of_date=date(2024, 12, 31),
        )

        assert result["data"]["total_transactions"] >= 1
