"""Tests for portfolio analytics service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity, Position, Security
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
)
from family_office_ledger.services.portfolio_analytics import (
    AssetAllocation,
    PortfolioAnalyticsService,
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
def service(
    entity_repo: SQLiteEntityRepository,
    position_repo: SQLitePositionRepository,
    security_repo: SQLiteSecurityRepository,
) -> PortfolioAnalyticsService:
    return PortfolioAnalyticsService(
        entity_repo=entity_repo,
        position_repo=position_repo,
        security_repo=security_repo,
    )


def create_security(
    security_repo: SQLiteSecurityRepository,
    symbol: str,
    name: str,
    asset_class: AssetClass = AssetClass.EQUITY,
) -> Security:
    security = Security(
        symbol=symbol,
        name=name,
        asset_class=asset_class,
    )
    security_repo.add(security)
    return security


def create_position(
    position_repo: SQLitePositionRepository,
    account: Account,
    security: Security,
    quantity: Decimal,
    cost_basis: Decimal,
    market_value: Decimal,
) -> Position:
    position = Position(
        account_id=account.id,
        security_id=security.id,
    )
    position._quantity = Quantity(quantity)
    position._cost_basis = Money(cost_basis, "USD")
    position._market_value = Money(market_value, "USD")
    position_repo.add(position)
    return position


class TestAssetAllocationReport:
    def test_empty_portfolio(self, service: PortfolioAnalyticsService, entity: Entity):
        report = service.asset_allocation_report([entity.id], date.today())

        assert report.total_market_value.amount == Decimal("0")
        assert report.total_cost_basis.amount == Decimal("0")
        assert len(report.allocations) == 0

    def test_single_asset_class(
        self,
        service: PortfolioAnalyticsService,
        entity: Entity,
        account: Account,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
    ):
        security = create_security(
            security_repo, "AAPL", "Apple Inc", AssetClass.EQUITY
        )
        create_position(
            position_repo,
            account,
            security,
            quantity=Decimal("100"),
            cost_basis=Decimal("10000"),
            market_value=Decimal("15000"),
        )

        report = service.asset_allocation_report([entity.id], date.today())

        assert report.total_market_value.amount == Decimal("15000")
        assert report.total_cost_basis.amount == Decimal("10000")
        assert report.total_unrealized_gain.amount == Decimal("5000")
        assert len(report.allocations) == 1
        assert report.allocations[0].asset_class == AssetClass.EQUITY
        assert report.allocations[0].allocation_percent == Decimal("100.00")

    def test_multiple_asset_classes(
        self,
        service: PortfolioAnalyticsService,
        entity: Entity,
        account: Account,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
    ):
        equity = create_security(security_repo, "AAPL", "Apple Inc", AssetClass.EQUITY)
        fixed_income = create_security(
            security_repo, "BND", "Bond Fund", AssetClass.FIXED_INCOME
        )
        crypto = create_security(security_repo, "BTC", "Bitcoin", AssetClass.CRYPTO)

        create_position(
            position_repo,
            account,
            equity,
            quantity=Decimal("100"),
            cost_basis=Decimal("5000"),
            market_value=Decimal("6000"),
        )
        create_position(
            position_repo,
            account,
            fixed_income,
            quantity=Decimal("50"),
            cost_basis=Decimal("2500"),
            market_value=Decimal("2500"),
        )
        create_position(
            position_repo,
            account,
            crypto,
            quantity=Decimal("1"),
            cost_basis=Decimal("500"),
            market_value=Decimal("1500"),
        )

        report = service.asset_allocation_report([entity.id], date.today())

        assert report.total_market_value.amount == Decimal("10000")
        assert len(report.allocations) == 3

        equity_alloc = next(
            a for a in report.allocations if a.asset_class == AssetClass.EQUITY
        )
        assert equity_alloc.allocation_percent == Decimal("60.00")

        fi_alloc = next(
            a for a in report.allocations if a.asset_class == AssetClass.FIXED_INCOME
        )
        assert fi_alloc.allocation_percent == Decimal("25.00")

        crypto_alloc = next(
            a for a in report.allocations if a.asset_class == AssetClass.CRYPTO
        )
        assert crypto_alloc.allocation_percent == Decimal("15.00")


class TestConcentrationReport:
    def test_empty_portfolio(self, service: PortfolioAnalyticsService, entity: Entity):
        report = service.concentration_report([entity.id], date.today())

        assert report.total_market_value.amount == Decimal("0")
        assert len(report.holdings) == 0
        assert report.largest_single_holding == Decimal("0")

    def test_single_holding(
        self,
        service: PortfolioAnalyticsService,
        entity: Entity,
        account: Account,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
    ):
        security = create_security(security_repo, "AAPL", "Apple Inc")
        create_position(
            position_repo,
            account,
            security,
            quantity=Decimal("100"),
            cost_basis=Decimal("10000"),
            market_value=Decimal("15000"),
        )

        report = service.concentration_report([entity.id], date.today())

        assert len(report.holdings) == 1
        assert report.holdings[0].security_symbol == "AAPL"
        assert report.holdings[0].concentration_percent == Decimal("100.00")
        assert report.top_5_concentration == Decimal("100.00")
        assert report.largest_single_holding == Decimal("100.00")

    def test_multiple_holdings_sorted_by_concentration(
        self,
        service: PortfolioAnalyticsService,
        entity: Entity,
        account: Account,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
    ):
        aapl = create_security(security_repo, "AAPL", "Apple Inc")
        msft = create_security(security_repo, "MSFT", "Microsoft")
        goog = create_security(security_repo, "GOOG", "Alphabet")

        create_position(
            position_repo,
            account,
            aapl,
            quantity=Decimal("10"),
            cost_basis=Decimal("1000"),
            market_value=Decimal("2000"),
        )
        create_position(
            position_repo,
            account,
            msft,
            quantity=Decimal("10"),
            cost_basis=Decimal("2000"),
            market_value=Decimal("5000"),
        )
        create_position(
            position_repo,
            account,
            goog,
            quantity=Decimal("10"),
            cost_basis=Decimal("1500"),
            market_value=Decimal("3000"),
        )

        report = service.concentration_report([entity.id], date.today())

        assert len(report.holdings) == 3
        assert report.holdings[0].security_symbol == "MSFT"
        assert report.holdings[1].security_symbol == "GOOG"
        assert report.holdings[2].security_symbol == "AAPL"

    def test_top_n_limit(
        self,
        service: PortfolioAnalyticsService,
        entity: Entity,
        account: Account,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
    ):
        for i in range(5):
            sec = create_security(security_repo, f"SEC{i}", f"Security {i}")
            create_position(
                position_repo,
                account,
                sec,
                quantity=Decimal("10"),
                cost_basis=Decimal("1000"),
                market_value=Decimal("1000"),
            )

        report = service.concentration_report([entity.id], date.today(), top_n=3)

        assert len(report.holdings) == 3


class TestPerformanceReport:
    def test_empty_portfolio(self, service: PortfolioAnalyticsService, entity: Entity):
        report = service.performance_report(
            [entity.id], date(2024, 1, 1), date(2024, 12, 31)
        )

        assert report.portfolio_total_return_amount.amount == Decimal("0")
        assert report.portfolio_total_return_percent == Decimal("0")

    def test_unrealized_gains(
        self,
        service: PortfolioAnalyticsService,
        entity: Entity,
        account: Account,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
    ):
        security = create_security(security_repo, "AAPL", "Apple Inc")
        create_position(
            position_repo,
            account,
            security,
            quantity=Decimal("100"),
            cost_basis=Decimal("10000"),
            market_value=Decimal("15000"),
        )

        report = service.performance_report(
            [entity.id], date(2024, 1, 1), date(2024, 12, 31)
        )

        assert report.portfolio_total_return_amount.amount == Decimal("5000")
        assert report.portfolio_total_return_percent == Decimal("50.00")


class TestPortfolioSummary:
    def test_summary_includes_all_metrics(
        self,
        service: PortfolioAnalyticsService,
        entity: Entity,
        account: Account,
        security_repo: SQLiteSecurityRepository,
        position_repo: SQLitePositionRepository,
    ):
        security = create_security(security_repo, "AAPL", "Apple Inc")
        create_position(
            position_repo,
            account,
            security,
            quantity=Decimal("100"),
            cost_basis=Decimal("10000"),
            market_value=Decimal("15000"),
        )

        summary = service.get_portfolio_summary([entity.id], date.today())

        assert "total_market_value" in summary
        assert "total_cost_basis" in summary
        assert "total_unrealized_gain" in summary
        assert "asset_allocation" in summary
        assert "top_holdings" in summary
        assert "concentration_metrics" in summary

        assert summary["total_market_value"] == "15000"
        assert summary["total_cost_basis"] == "10000"
        assert summary["total_unrealized_gain"] == "5000"
