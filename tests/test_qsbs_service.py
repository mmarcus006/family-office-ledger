"""Tests for QSBS service."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.transactions import TaxLot
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AssetClass,
    EntityType,
    Money,
    Quantity,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
)
from family_office_ledger.services.qsbs import (
    QSBS_HOLDING_PERIOD_DAYS,
    QSBSService,
    SecurityNotFoundError,
)


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
def security_repo(db: SQLiteDatabase) -> SQLiteSecurityRepository:
    return SQLiteSecurityRepository(db)


@pytest.fixture
def position_repo(db: SQLiteDatabase) -> SQLitePositionRepository:
    return SQLitePositionRepository(db)


@pytest.fixture
def tax_lot_repo(db: SQLiteDatabase) -> SQLiteTaxLotRepository:
    return SQLiteTaxLotRepository(db)


@pytest.fixture
def entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Test LLC",
        entity_type=EntityType.LLC,
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def account(account_repo: SQLiteAccountRepository, entity: Entity) -> Account:
    account = Account(
        name="Brokerage",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.BROKERAGE,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def security(security_repo: SQLiteSecurityRepository) -> Security:
    security = Security(
        symbol="STARTUP",
        name="Startup Inc",
        asset_class=AssetClass.EQUITY,
        issuer="Startup Inc",
    )
    security_repo.add(security)
    return security


@pytest.fixture
def service(
    security_repo: SQLiteSecurityRepository,
    position_repo: SQLitePositionRepository,
    tax_lot_repo: SQLiteTaxLotRepository,
) -> QSBSService:
    return QSBSService(
        security_repo=security_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
    )


class TestMarkQSBSEligible:
    def test_marks_security_as_qsbs_eligible(
        self,
        service: QSBSService,
        security: Security,
    ):
        qual_date = date(2020, 1, 1)
        result = service.mark_security_qsbs_eligible(security.id, qual_date)

        assert result.is_qsbs_eligible is True
        assert result.qsbs_qualification_date == qual_date

    def test_raises_error_for_nonexistent_security(
        self,
        service: QSBSService,
    ):
        with pytest.raises(SecurityNotFoundError):
            service.mark_security_qsbs_eligible(uuid4(), date(2020, 1, 1))


class TestRemoveQSBSEligibility:
    def test_removes_qsbs_eligibility(
        self,
        service: QSBSService,
        security: Security,
    ):
        service.mark_security_qsbs_eligible(security.id, date(2020, 1, 1))
        result = service.remove_qsbs_eligibility(security.id)

        assert result.is_qsbs_eligible is False
        assert result.qsbs_qualification_date is None

    def test_raises_error_for_nonexistent_security(
        self,
        service: QSBSService,
    ):
        with pytest.raises(SecurityNotFoundError):
            service.remove_qsbs_eligibility(uuid4())


class TestListQSBSEligibleSecurities:
    def test_returns_empty_list_when_none_eligible(
        self,
        service: QSBSService,
        security: Security,
    ):
        result = service.list_qsbs_eligible_securities()
        assert result == []

    def test_returns_only_eligible_securities(
        self,
        service: QSBSService,
        security_repo: SQLiteSecurityRepository,
    ):
        qsbs_security = Security(
            symbol="QSBS1",
            name="QSBS Company",
            is_qsbs_eligible=True,
            qsbs_qualification_date=date(2020, 1, 1),
        )
        security_repo.add(qsbs_security)

        non_qsbs = Security(
            symbol="NONQ",
            name="Non-QSBS Company",
        )
        security_repo.add(non_qsbs)

        result = service.list_qsbs_eligible_securities()

        assert len(result) == 1
        assert result[0].symbol == "QSBS1"


class TestGetQSBSSummary:
    def test_returns_empty_summary_when_no_qsbs_securities(
        self,
        service: QSBSService,
    ):
        summary = service.get_qsbs_summary()

        assert summary.total_qsbs_holdings == 0
        assert summary.qualified_holdings == 0
        assert summary.pending_holdings == 0
        assert summary.total_cost_basis == Decimal("0")
        assert summary.total_potential_exclusion == Decimal("0")
        assert summary.holdings == []

    def test_calculates_holding_periods(
        self,
        service: QSBSService,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
        tax_lot_repo: SQLiteTaxLotRepository,
        account: Account,
    ):
        qsbs_security = Security(
            symbol="QSBS1",
            name="QSBS Company",
            is_qsbs_eligible=True,
            qsbs_qualification_date=date(2018, 1, 1),
        )
        security_repo.add(qsbs_security)

        position = Position(
            account_id=account.id,
            security_id=qsbs_security.id,
        )
        position.update_from_lots(Quantity(Decimal("100")), Money(Decimal("10000")))
        position_repo.add(position)

        lot = TaxLot(
            position_id=position.id,
            acquisition_date=date.today() - timedelta(days=1000),
            original_quantity=Quantity(Decimal("100")),
            cost_per_share=Money(Decimal("100")),
        )
        tax_lot_repo.add(lot)

        summary = service.get_qsbs_summary()

        assert summary.total_qsbs_holdings == 1
        assert summary.holdings[0].holding_period_days == 1000

    def test_identifies_qualified_holdings(
        self,
        service: QSBSService,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
        tax_lot_repo: SQLiteTaxLotRepository,
        account: Account,
    ):
        qsbs_security = Security(
            symbol="QSBS1",
            name="QSBS Company",
            is_qsbs_eligible=True,
            qsbs_qualification_date=date(2015, 1, 1),
        )
        security_repo.add(qsbs_security)

        position = Position(
            account_id=account.id,
            security_id=qsbs_security.id,
        )
        position.update_from_lots(Quantity(Decimal("100")), Money(Decimal("10000")))
        position_repo.add(position)

        qualified_lot = TaxLot(
            position_id=position.id,
            acquisition_date=date.today()
            - timedelta(days=QSBS_HOLDING_PERIOD_DAYS + 100),
            original_quantity=Quantity(Decimal("100")),
            cost_per_share=Money(Decimal("100")),
        )
        tax_lot_repo.add(qualified_lot)

        summary = service.get_qsbs_summary()

        assert summary.qualified_holdings == 1
        assert summary.pending_holdings == 0
        assert summary.holdings[0].is_qualified is True

    def test_calculates_potential_exclusion(
        self,
        service: QSBSService,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
        tax_lot_repo: SQLiteTaxLotRepository,
        account: Account,
    ):
        qsbs_security = Security(
            symbol="QSBS1",
            name="QSBS Company",
            is_qsbs_eligible=True,
            qsbs_qualification_date=date(2015, 1, 1),
        )
        security_repo.add(qsbs_security)

        position = Position(
            account_id=account.id,
            security_id=qsbs_security.id,
        )
        position.update_from_lots(Quantity(Decimal("100")), Money(Decimal("50000")))
        position_repo.add(position)

        lot = TaxLot(
            position_id=position.id,
            acquisition_date=date.today() - timedelta(days=100),
            original_quantity=Quantity(Decimal("100")),
            cost_per_share=Money(Decimal("500")),
        )
        tax_lot_repo.add(lot)

        summary = service.get_qsbs_summary()

        assert summary.holdings[0].cost_basis == Decimal("50000")
        assert summary.holdings[0].potential_exclusion == Decimal("500000")


class TestCalculateExclusionAvailable:
    def test_returns_zero_for_non_qsbs_security(
        self,
        service: QSBSService,
        security: Security,
    ):
        result = service.calculate_exclusion_available(security.id)
        assert result == Decimal("0")

    def test_returns_zero_when_security_not_found(
        self,
        service: QSBSService,
    ):
        result = service.calculate_exclusion_available(uuid4())
        assert result == Decimal("0")
