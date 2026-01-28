"""Tests for LotMatchingService implementation."""

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
    LotSelection,
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
from family_office_ledger.services.lot_matching import (
    InsufficientLotsError,
    InvalidLotSelectionError,
    LotMatchingServiceImpl,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def tax_lot_repo(db: SQLiteDatabase) -> SQLiteTaxLotRepository:
    return SQLiteTaxLotRepository(db)


@pytest.fixture
def position_repo(db: SQLiteDatabase) -> SQLitePositionRepository:
    return SQLitePositionRepository(db)


@pytest.fixture
def test_position(
    db: SQLiteDatabase,
    position_repo: SQLitePositionRepository,
) -> Position:
    """Create a test position with related entity, account, and security."""
    entity_repo = SQLiteEntityRepository(db)
    account_repo = SQLiteAccountRepository(db)
    security_repo = SQLiteSecurityRepository(db)

    entity = Entity(name="Test Entity", entity_type=EntityType.TRUST)
    entity_repo.add(entity)

    account = Account(
        name="Brokerage",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.BROKERAGE,
    )
    account_repo.add(account)

    security = Security(symbol="AAPL", name="Apple Inc.", asset_class=AssetClass.EQUITY)
    security_repo.add(security)

    position = Position(account_id=account.id, security_id=security.id)
    position_repo.add(position)
    return position


@pytest.fixture
def service(
    tax_lot_repo: SQLiteTaxLotRepository,
    position_repo: SQLitePositionRepository,
) -> LotMatchingServiceImpl:
    return LotMatchingServiceImpl(tax_lot_repo, position_repo)


class TestGetOpenLots:
    def test_returns_open_lots_only(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        # Create open lot
        open_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        # Create closed lot
        closed_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 2, 15),
            cost_per_share=Money(Decimal("110.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        closed_lot.sell(Quantity(Decimal("30")), date(2024, 1, 15))

        tax_lot_repo.add(open_lot)
        tax_lot_repo.add(closed_lot)

        open_lots = service.get_open_lots(test_position.id)

        assert len(open_lots) == 1
        assert open_lots[0].id == open_lot.id

    def test_returns_empty_list_when_no_lots(
        self,
        service: LotMatchingServiceImpl,
        test_position: Position,
    ) -> None:
        open_lots = service.get_open_lots(test_position.id)
        assert open_lots == []


class TestGetPositionCostBasis:
    def test_sums_remaining_cost_of_open_lots(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 2, 15),
            cost_per_share=Money(Decimal("110.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        cost_basis = service.get_position_cost_basis(test_position.id)

        # 50 * 100 + 30 * 110 = 5000 + 3300 = 8300
        assert cost_basis == Money(Decimal("8300.00"))

    def test_returns_zero_when_no_lots(
        self,
        service: LotMatchingServiceImpl,
        test_position: Position,
    ) -> None:
        cost_basis = service.get_position_cost_basis(test_position.id)
        assert cost_basis == Money.zero()

    def test_excludes_sold_portions(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        lot.sell(Quantity(Decimal("40")), date(2024, 1, 15))
        tax_lot_repo.add(lot)

        cost_basis = service.get_position_cost_basis(test_position.id)

        # 60 remaining * 100 = 6000
        assert cost_basis == Money(Decimal("6000.00"))


class TestMatchSaleFIFO:
    def test_selects_oldest_lots_first(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        oldest = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        middle = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        newest = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 12, 15),
            cost_per_share=Money(Decimal("140.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(oldest)
        tax_lot_repo.add(middle)
        tax_lot_repo.add(newest)

        matched = service.match_sale(
            test_position.id, Quantity(Decimal("75")), LotSelection.FIFO
        )

        assert len(matched) == 2
        assert matched[0].id == oldest.id
        assert matched[1].id == middle.id


class TestMatchSaleLIFO:
    def test_selects_newest_lots_first(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        oldest = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        newest = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 12, 15),
            cost_per_share=Money(Decimal("140.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(oldest)
        tax_lot_repo.add(newest)

        matched = service.match_sale(
            test_position.id, Quantity(Decimal("30")), LotSelection.LIFO
        )

        assert len(matched) == 1
        assert matched[0].id == newest.id


class TestMatchSaleHIFO:
    def test_selects_highest_cost_first(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        low_cost = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        high_cost = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(low_cost)
        tax_lot_repo.add(high_cost)

        matched = service.match_sale(
            test_position.id, Quantity(Decimal("30")), LotSelection.HIFO
        )

        assert len(matched) == 1
        assert matched[0].id == high_cost.id


class TestMatchSaleMinimizeGain:
    def test_selects_lots_with_lowest_gain(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        # At sale price of 120, gain = 120 - cost
        high_cost = TaxLot(  # gain = 120 - 110 = 10
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("110.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        low_cost = TaxLot(  # gain = 120 - 90 = 30
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("90.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(high_cost)
        tax_lot_repo.add(low_cost)

        # Minimize gain should pick high_cost lot first (lowest gain)
        matched = service.match_sale(
            test_position.id, Quantity(Decimal("30")), LotSelection.MINIMIZE_GAIN
        )

        assert len(matched) == 1
        assert matched[0].id == high_cost.id


class TestMatchSaleMaximizeGain:
    def test_selects_lots_with_highest_gain(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        high_cost = TaxLot(  # lower gain when sold
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("110.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        low_cost = TaxLot(  # higher gain when sold
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("90.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(high_cost)
        tax_lot_repo.add(low_cost)

        # Maximize gain should pick low_cost lot first (highest gain)
        matched = service.match_sale(
            test_position.id, Quantity(Decimal("30")), LotSelection.MAXIMIZE_GAIN
        )

        assert len(matched) == 1
        assert matched[0].id == low_cost.id


class TestMatchSaleSpecificId:
    def test_selects_only_specified_lots(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        matched = service.match_sale(
            test_position.id,
            Quantity(Decimal("30")),
            LotSelection.SPECIFIC_ID,
            specific_lot_ids=[lot2.id],
        )

        assert len(matched) == 1
        assert matched[0].id == lot2.id

    def test_raises_error_for_invalid_lot_id(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        invalid_id = uuid4()
        with pytest.raises(InvalidLotSelectionError):
            service.match_sale(
                test_position.id,
                Quantity(Decimal("30")),
                LotSelection.SPECIFIC_ID,
                specific_lot_ids=[invalid_id],
            )

    def test_raises_error_for_closed_lot(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot.sell(Quantity(Decimal("50")), date(2024, 1, 15))
        tax_lot_repo.add(lot)

        with pytest.raises(InvalidLotSelectionError):
            service.match_sale(
                test_position.id,
                Quantity(Decimal("30")),
                LotSelection.SPECIFIC_ID,
                specific_lot_ids=[lot.id],
            )


class TestMatchSaleAverageCost:
    def test_returns_all_open_lots_for_average_cost(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        matched = service.match_sale(
            test_position.id, Quantity(Decimal("30")), LotSelection.AVERAGE_COST
        )

        # For average cost, all open lots are returned for pro-rata allocation
        assert len(matched) == 2


class TestMatchSaleInsufficientLots:
    def test_raises_error_when_insufficient_quantity(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        with pytest.raises(InsufficientLotsError):
            service.match_sale(
                test_position.id, Quantity(Decimal("100")), LotSelection.FIFO
            )


class TestExecuteSale:
    def test_executes_fifo_sale(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("70")),
            proceeds=Money(Decimal("9800.00")),  # 70 shares @ $140
            sale_date=date(2024, 6, 15),
            method=LotSelection.FIFO,
        )

        assert len(dispositions) == 2

        # First disposition: all 50 shares from lot1
        d1 = dispositions[0]
        assert d1.lot_id == lot1.id
        assert d1.quantity_sold == Quantity(Decimal("50"))
        assert d1.cost_basis == Money(Decimal("5000.00"))  # 50 * 100
        assert d1.acquisition_date == date(2023, 1, 15)
        assert d1.disposition_date == date(2024, 6, 15)
        assert d1.is_long_term  # >365 days

        # Second disposition: 20 shares from lot2
        d2 = dispositions[1]
        assert d2.lot_id == lot2.id
        assert d2.quantity_sold == Quantity(Decimal("20"))
        assert d2.cost_basis == Money(Decimal("2400.00"))  # 20 * 120

        # Verify lots are updated in repository
        updated_lot1 = tax_lot_repo.get(lot1.id)
        updated_lot2 = tax_lot_repo.get(lot2.id)
        assert updated_lot1 is not None
        assert updated_lot1.remaining_quantity == Quantity(Decimal("0"))
        assert updated_lot2 is not None
        assert updated_lot2.remaining_quantity == Quantity(Decimal("30"))

    def test_executes_specific_id_sale(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("30")),
            proceeds=Money(Decimal("4200.00")),  # 30 shares @ $140
            sale_date=date(2024, 6, 15),
            method=LotSelection.SPECIFIC_ID,
            specific_lot_ids=[lot2.id],
        )

        assert len(dispositions) == 1
        assert dispositions[0].lot_id == lot2.id
        assert dispositions[0].quantity_sold == Quantity(Decimal("30"))

    def test_executes_average_cost_sale(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        # Total cost = 5000 + 6000 = 11000
        # Total shares = 100
        # Average cost = 110 per share
        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("40")),
            proceeds=Money(Decimal("5600.00")),  # 40 shares @ $140
            sale_date=date(2024, 6, 15),
            method=LotSelection.AVERAGE_COST,
        )

        # With average cost, sells pro-rata from all lots
        # 40 shares out of 100 total = 40%
        # From lot1: 50 * 0.4 = 20 shares
        # From lot2: 50 * 0.4 = 20 shares
        assert len(dispositions) == 2

        total_quantity = sum(d.quantity_sold.value for d in dispositions)
        assert total_quantity == Decimal("40")

        # Cost basis should be average: 40 * 110 = 4400
        total_cost = sum(d.cost_basis.amount for d in dispositions)
        assert total_cost == Decimal("4400.00")

    def test_proceeds_allocated_proportionally(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("60")),
            proceeds=Money(Decimal("9000.00")),  # 60 shares @ $150
            sale_date=date(2024, 6, 15),
            method=LotSelection.FIFO,
        )

        # 50 shares from lot1, 10 from lot2
        # Total proceeds = 9000
        total_proceeds = sum(d.proceeds.amount for d in dispositions)
        assert total_proceeds == Decimal("9000.00")


class TestDetectWashSales:
    def test_finds_lots_within_30_days_before(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        sale_date = date(2024, 2, 15)

        # Lot acquired 20 days before sale - should be detected
        recent_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=sale_date - timedelta(days=20),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        # Lot acquired 60 days before - should not be detected
        old_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=sale_date - timedelta(days=60),
            cost_per_share=Money(Decimal("90.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(recent_lot)
        tax_lot_repo.add(old_lot)

        wash_candidates = service.detect_wash_sales(
            test_position.id,
            sale_date,
            Money(Decimal("500.00")),  # loss amount
        )

        assert len(wash_candidates) == 1
        assert wash_candidates[0].id == recent_lot.id

    def test_finds_lots_within_30_days_after(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        sale_date = date(2024, 2, 15)

        # Lot acquired 15 days after sale - should be detected
        future_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=sale_date + timedelta(days=15),
            cost_per_share=Money(Decimal("105.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        tax_lot_repo.add(future_lot)

        wash_candidates = service.detect_wash_sales(
            test_position.id,
            sale_date,
            Money(Decimal("500.00")),
        )

        assert len(wash_candidates) == 1
        assert wash_candidates[0].id == future_lot.id

    def test_returns_empty_when_no_wash_sale_candidates(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        sale_date = date(2024, 2, 15)

        # Lot acquired well outside 30-day window
        old_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=sale_date - timedelta(days=90),
            cost_per_share=Money(Decimal("90.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(old_lot)

        wash_candidates = service.detect_wash_sales(
            test_position.id,
            sale_date,
            Money(Decimal("500.00")),
        )

        assert wash_candidates == []

    def test_ignores_gain_sales(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        """Wash sales only apply to losses, not gains."""
        sale_date = date(2024, 2, 15)

        recent_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=sale_date - timedelta(days=20),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(recent_lot)

        # Positive loss amount means a gain - no wash sale applies
        wash_candidates = service.detect_wash_sales(
            test_position.id,
            sale_date,
            Money(Decimal("-500.00")),  # This is actually a gain (negative loss)
        )

        assert wash_candidates == []


class TestRealizedGainCalculation:
    def test_calculates_realized_gain_correctly(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("50")),
            proceeds=Money(Decimal("7500.00")),  # 50 * 150
            sale_date=date(2024, 6, 15),
            method=LotSelection.FIFO,
        )

        d = dispositions[0]
        # Realized gain = proceeds - cost_basis = 7500 - 5000 = 2500
        assert d.realized_gain == Money(Decimal("2500.00"))

    def test_calculates_realized_loss_correctly(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("50")),
            proceeds=Money(Decimal("4000.00")),  # 50 * 80 (loss)
            sale_date=date(2024, 6, 15),
            method=LotSelection.FIFO,
        )

        d = dispositions[0]
        # Realized loss = proceeds - cost_basis = 4000 - 5000 = -1000
        assert d.realized_gain == Money(Decimal("-1000.00"))


class TestLongTermShortTermClassification:
    def test_short_term_classification(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        # Acquired recently - short term
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2024, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("50")),
            proceeds=Money(Decimal("5500.00")),
            sale_date=date(2024, 6, 15),  # Less than a year
            method=LotSelection.FIFO,
        )

        assert dispositions[0].is_long_term is False

    def test_long_term_classification(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        # Acquired over a year ago - long term
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2022, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("50")),
            proceeds=Money(Decimal("5500.00")),
            sale_date=date(2024, 6, 15),  # More than a year
            method=LotSelection.FIFO,
        )

        assert dispositions[0].is_long_term is True


class TestEdgeCases:
    def test_partial_lot_sale(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        """Test selling only part of a lot."""
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(lot)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("30")),
            proceeds=Money(Decimal("4500.00")),
            sale_date=date(2024, 6, 15),
            method=LotSelection.FIFO,
        )

        assert len(dispositions) == 1
        assert dispositions[0].quantity_sold == Quantity(Decimal("30"))
        assert dispositions[0].cost_basis == Money(Decimal("3000.00"))

        # Verify lot still has remaining shares
        updated_lot = tax_lot_repo.get(lot.id)
        assert updated_lot is not None
        assert updated_lot.remaining_quantity == Quantity(Decimal("70"))

    def test_exact_quantity_match(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        """Test selling exact quantity of a lot."""
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("50")),
            proceeds=Money(Decimal("7500.00")),
            sale_date=date(2024, 6, 15),
            method=LotSelection.FIFO,
        )

        assert len(dispositions) == 1
        assert dispositions[0].quantity_sold == Quantity(Decimal("50"))

        # Verify lot is fully disposed
        updated_lot = tax_lot_repo.get(lot.id)
        assert updated_lot is not None
        assert updated_lot.remaining_quantity == Quantity(Decimal("0"))
        assert updated_lot.is_fully_disposed

    def test_multiple_lots_partial_last(
        self,
        service: LotMatchingServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_position: Position,
    ) -> None:
        """Test selling from multiple lots with partial sale of last lot."""
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("110.00")),
            original_quantity=Quantity(Decimal("40")),
        )
        lot3 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 12, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)
        tax_lot_repo.add(lot3)

        dispositions = service.execute_sale(
            position_id=test_position.id,
            quantity=Quantity(Decimal("80")),
            proceeds=Money(Decimal("12000.00")),
            sale_date=date(2024, 6, 15),
            method=LotSelection.FIFO,
        )

        assert len(dispositions) == 3

        # lot1: all 30 shares
        assert dispositions[0].lot_id == lot1.id
        assert dispositions[0].quantity_sold == Quantity(Decimal("30"))

        # lot2: all 40 shares
        assert dispositions[1].lot_id == lot2.id
        assert dispositions[1].quantity_sold == Quantity(Decimal("40"))

        # lot3: only 10 shares
        assert dispositions[2].lot_id == lot3.id
        assert dispositions[2].quantity_sold == Quantity(Decimal("10"))

        # Verify remaining quantities
        assert tax_lot_repo.get(lot1.id).remaining_quantity == Quantity(Decimal("0"))
        assert tax_lot_repo.get(lot2.id).remaining_quantity == Quantity(Decimal("0"))
        assert tax_lot_repo.get(lot3.id).remaining_quantity == Quantity(Decimal("40"))
