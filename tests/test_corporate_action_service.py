"""Tests for CorporateActionService implementation."""

from datetime import date
from decimal import Decimal

import pytest

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.transactions import TaxLot
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AcquisitionType,
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
from family_office_ledger.services.corporate_actions import CorporateActionServiceImpl


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
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
def service(
    tax_lot_repo: SQLiteTaxLotRepository,
    position_repo: SQLitePositionRepository,
    security_repo: SQLiteSecurityRepository,
) -> CorporateActionServiceImpl:
    return CorporateActionServiceImpl(tax_lot_repo, position_repo, security_repo)


@pytest.fixture
def test_entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(name="Test Family Trust", entity_type=EntityType.TRUST)
    entity_repo.add(entity)
    return entity


@pytest.fixture
def test_account(test_entity: Entity, account_repo: SQLiteAccountRepository) -> Account:
    account = Account(
        name="Brokerage Account",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.BROKERAGE,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def test_security(security_repo: SQLiteSecurityRepository) -> Security:
    security = Security(
        symbol="AAPL",
        name="Apple Inc.",
        asset_class=AssetClass.EQUITY,
    )
    security_repo.add(security)
    return security


@pytest.fixture
def test_position(
    test_account: Account,
    test_security: Security,
    position_repo: SQLitePositionRepository,
) -> Position:
    position = Position(account_id=test_account.id, security_id=test_security.id)
    position_repo.add(position)
    return position


class TestApplySplit:
    """Tests for the apply_split method."""

    def test_2_for_1_split_doubles_quantity_halves_cost(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        test_security: Security,
        test_position: Position,
    ) -> None:
        """A 2-for-1 split should double quantity and halve cost per share."""
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        updated_lot = tax_lot_repo.get(lot.id)
        assert updated_lot is not None
        assert updated_lot.original_quantity == Quantity(Decimal("100"))
        assert updated_lot.remaining_quantity == Quantity(Decimal("100"))
        assert updated_lot.cost_per_share == Money(Decimal("50.00"))

    def test_3_for_1_split(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_security: Security,
        test_position: Position,
    ) -> None:
        """A 3-for-1 split should triple quantity and divide cost by 3."""
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("150.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        tax_lot_repo.add(lot)

        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("3"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        updated_lot = tax_lot_repo.get(lot.id)
        assert updated_lot is not None
        assert updated_lot.original_quantity == Quantity(Decimal("90"))
        assert updated_lot.cost_per_share == Money(Decimal("50.00"))

    def test_reverse_split_1_for_4(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_security: Security,
        test_position: Position,
    ) -> None:
        """A 1-for-4 reverse split should quarter quantity and quadruple cost."""
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("10.00")),
            original_quantity=Quantity(Decimal("400")),
        )
        tax_lot_repo.add(lot)

        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("4"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        updated_lot = tax_lot_repo.get(lot.id)
        assert updated_lot is not None
        assert updated_lot.original_quantity == Quantity(Decimal("100"))
        assert updated_lot.cost_per_share == Money(Decimal("40.00"))

    def test_split_affects_multiple_lots(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_security: Security,
        test_position: Position,
    ) -> None:
        """A split should affect all open lots for the security."""
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

        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 2

        updated_lot1 = tax_lot_repo.get(lot1.id)
        updated_lot2 = tax_lot_repo.get(lot2.id)

        assert updated_lot1 is not None
        assert updated_lot1.original_quantity == Quantity(Decimal("100"))
        assert updated_lot1.cost_per_share == Money(Decimal("50.00"))

        assert updated_lot2 is not None
        assert updated_lot2.original_quantity == Quantity(Decimal("60"))
        assert updated_lot2.cost_per_share == Money(Decimal("60.00"))

    def test_split_ignores_closed_lots(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_security: Security,
        test_position: Position,
    ) -> None:
        """A split should not affect fully disposed lots."""
        open_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        closed_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 3, 15),
            cost_per_share=Money(Decimal("110.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        closed_lot.sell(Quantity(Decimal("30")), date(2024, 1, 15))

        tax_lot_repo.add(open_lot)
        tax_lot_repo.add(closed_lot)

        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        # Only the open lot should be affected
        assert count == 1

        updated_closed = tax_lot_repo.get(closed_lot.id)
        assert updated_closed is not None
        # Closed lot should remain unchanged
        assert updated_closed.original_quantity == Quantity(Decimal("30"))
        assert updated_closed.cost_per_share == Money(Decimal("110.00"))

    def test_split_preserves_total_cost_basis(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_security: Security,
        test_position: Position,
    ) -> None:
        """Total cost basis should remain unchanged after a split."""
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(lot)

        original_total_cost = lot.total_cost

        service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        updated_lot = tax_lot_repo.get(lot.id)
        assert updated_lot is not None
        assert updated_lot.total_cost == original_total_cost

    def test_split_with_no_lots_returns_zero(
        self,
        service: CorporateActionServiceImpl,
        test_security: Security,
    ) -> None:
        """Applying split with no lots should return 0."""
        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )
        assert count == 0

    def test_split_affects_partially_sold_lots(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        test_security: Security,
        test_position: Position,
    ) -> None:
        """A split should affect lots that are partially sold."""
        lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        lot.sell(Quantity(Decimal("40")), date(2024, 1, 15))
        tax_lot_repo.add(lot)

        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        updated_lot = tax_lot_repo.get(lot.id)
        assert updated_lot is not None
        # Original qty: 100 -> 200, remaining: 60 -> 120
        assert updated_lot.original_quantity == Quantity(Decimal("200"))
        assert updated_lot.remaining_quantity == Quantity(Decimal("120"))
        assert updated_lot.cost_per_share == Money(Decimal("50.00"))


class TestApplySpinoff:
    """Tests for the apply_spinoff method."""

    def test_spinoff_creates_new_lots_for_child_security(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Spinoff should create new lots for the child security."""
        # Create child security
        child_security = Security(
            symbol="CHILD",
            name="Child Corp",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(child_security)

        # Create position for child security
        child_position = Position(
            account_id=test_account.id, security_id=child_security.id
        )
        position_repo.add(child_position)

        # Create parent lot
        parent_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(parent_lot)

        count = service.apply_spinoff(
            parent_security_id=test_security.id,
            child_security_id=child_security.id,
            allocation_ratio=Decimal("0.20"),  # 20% of cost basis to child
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        # Verify parent lot cost basis reduced by 20%
        updated_parent = tax_lot_repo.get(parent_lot.id)
        assert updated_parent is not None
        # Original cost per share was 100, 20% allocated means 80 remains
        assert updated_parent.cost_per_share == Money(Decimal("80.00"))

        # Verify child lot created
        child_lots = list(tax_lot_repo.list_by_position(child_position.id))
        assert len(child_lots) == 1
        child_lot = child_lots[0]
        assert child_lot.acquisition_date == date(2023, 1, 15)  # Same as parent
        assert child_lot.original_quantity == Quantity(Decimal("100"))
        assert child_lot.cost_per_share == Money(Decimal("20.00"))  # 20% of 100
        assert child_lot.acquisition_type == AcquisitionType.SPINOFF

    def test_spinoff_with_multiple_parent_lots(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Spinoff should create child lots for each parent lot."""
        # Create child security
        child_security = Security(
            symbol="SPIN",
            name="Spinoff Corp",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(child_security)

        # Create position for child security
        child_position = Position(
            account_id=test_account.id, security_id=child_security.id
        )
        position_repo.add(child_position)

        # Create multiple parent lots
        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2022, 1, 15),
            cost_per_share=Money(Decimal("50.00")),
            original_quantity=Quantity(Decimal("200")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("80.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        count = service.apply_spinoff(
            parent_security_id=test_security.id,
            child_security_id=child_security.id,
            allocation_ratio=Decimal("0.25"),  # 25% to child
            effective_date=date(2024, 6, 15),
        )

        assert count == 2

        # Verify parent lots reduced
        updated_lot1 = tax_lot_repo.get(lot1.id)
        updated_lot2 = tax_lot_repo.get(lot2.id)

        assert updated_lot1 is not None
        assert updated_lot1.cost_per_share == Money(Decimal("37.50"))  # 75% of 50

        assert updated_lot2 is not None
        assert updated_lot2.cost_per_share == Money(Decimal("60.00"))  # 75% of 80

        # Verify child lots created
        child_lots = list(tax_lot_repo.list_by_position(child_position.id))
        assert len(child_lots) == 2

    def test_spinoff_preserves_acquisition_date(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Child lots should inherit acquisition date from parent."""
        child_security = Security(
            symbol="CHILD",
            name="Child Corp",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(child_security)

        child_position = Position(
            account_id=test_account.id, security_id=child_security.id
        )
        position_repo.add(child_position)

        parent_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2020, 3, 20),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        tax_lot_repo.add(parent_lot)

        service.apply_spinoff(
            parent_security_id=test_security.id,
            child_security_id=child_security.id,
            allocation_ratio=Decimal("0.15"),
            effective_date=date(2024, 6, 15),
        )

        child_lots = list(tax_lot_repo.list_by_position(child_position.id))
        assert len(child_lots) == 1
        assert child_lots[0].acquisition_date == date(2020, 3, 20)

    def test_spinoff_ignores_closed_lots(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Spinoff should only affect open lots."""
        child_security = Security(
            symbol="CHILD",
            name="Child Corp",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(child_security)

        child_position = Position(
            account_id=test_account.id, security_id=child_security.id
        )
        position_repo.add(child_position)

        open_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        closed_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 3, 15),
            cost_per_share=Money(Decimal("110.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        closed_lot.sell(Quantity(Decimal("30")), date(2024, 1, 15))

        tax_lot_repo.add(open_lot)
        tax_lot_repo.add(closed_lot)

        count = service.apply_spinoff(
            parent_security_id=test_security.id,
            child_security_id=child_security.id,
            allocation_ratio=Decimal("0.20"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        child_lots = list(tax_lot_repo.list_by_position(child_position.id))
        assert len(child_lots) == 1


class TestApplyMerger:
    """Tests for the apply_merger method."""

    def test_merger_creates_new_lots_for_new_security(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Merger should create new lots for the new security."""
        # Create new security (acquiring company)
        new_security = Security(
            symbol="NEWCO",
            name="NewCo Inc.",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(new_security)

        # Create position for new security
        new_position = Position(account_id=test_account.id, security_id=new_security.id)
        position_repo.add(new_position)

        # Create old lot
        old_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("50.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(old_lot)

        count = service.apply_merger(
            old_security_id=test_security.id,
            new_security_id=new_security.id,
            exchange_ratio=Decimal("0.5"),  # 2 old shares = 1 new share
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        # Verify old lot is closed
        updated_old = tax_lot_repo.get(old_lot.id)
        assert updated_old is not None
        assert updated_old.is_fully_disposed

        # Verify new lot created
        new_lots = list(tax_lot_repo.list_by_position(new_position.id))
        assert len(new_lots) == 1
        new_lot = new_lots[0]
        assert new_lot.original_quantity == Quantity(Decimal("50"))  # 100 * 0.5
        # Total cost basis preserved: 50 * 100 = 5000, new cost per share = 5000/50 = 100
        assert new_lot.cost_per_share == Money(Decimal("100.00"))
        assert new_lot.acquisition_date == date(2023, 1, 15)  # Same as old
        assert new_lot.acquisition_type == AcquisitionType.MERGER

    def test_merger_with_multiple_lots(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Merger should convert all open lots."""
        new_security = Security(
            symbol="MERGED",
            name="Merged Corp",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(new_security)

        new_position = Position(account_id=test_account.id, security_id=new_security.id)
        position_repo.add(new_position)

        lot1 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2022, 1, 15),
            cost_per_share=Money(Decimal("40.00")),
            original_quantity=Quantity(Decimal("200")),
        )
        lot2 = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("60.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        count = service.apply_merger(
            old_security_id=test_security.id,
            new_security_id=new_security.id,
            exchange_ratio=Decimal("1.5"),  # 1 old share = 1.5 new shares
            effective_date=date(2024, 6, 15),
        )

        assert count == 2

        new_lots = list(tax_lot_repo.list_by_position(new_position.id))
        assert len(new_lots) == 2

    def test_merger_with_cash_in_lieu(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Merger with cash in lieu should reduce cost basis."""
        new_security = Security(
            symbol="BUYER",
            name="Buyer Corp",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(new_security)

        new_position = Position(account_id=test_account.id, security_id=new_security.id)
        position_repo.add(new_position)

        old_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(old_lot)

        count = service.apply_merger(
            old_security_id=test_security.id,
            new_security_id=new_security.id,
            exchange_ratio=Decimal("0.8"),  # 1 old = 0.8 new
            effective_date=date(2024, 6, 15),
            cash_in_lieu_per_share=Money(Decimal("10.00")),  # $10 per old share
        )

        assert count == 1

        new_lots = list(tax_lot_repo.list_by_position(new_position.id))
        assert len(new_lots) == 1
        new_lot = new_lots[0]

        # Original cost: 100 * 100 = 10000
        # Cash received: 100 * 10 = 1000
        # Adjusted cost: 10000 - 1000 = 9000
        # New quantity: 100 * 0.8 = 80
        # New cost per share: 9000 / 80 = 112.50
        assert new_lot.original_quantity == Quantity(Decimal("80"))
        assert new_lot.cost_per_share == Money(Decimal("112.50"))

    def test_merger_ignores_closed_lots(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """Merger should only affect open lots."""
        new_security = Security(
            symbol="NEWCO",
            name="NewCo Inc.",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(new_security)

        new_position = Position(account_id=test_account.id, security_id=new_security.id)
        position_repo.add(new_position)

        open_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("50.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        closed_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2023, 3, 15),
            cost_per_share=Money(Decimal("60.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        closed_lot.sell(Quantity(Decimal("50")), date(2024, 1, 15))

        tax_lot_repo.add(open_lot)
        tax_lot_repo.add(closed_lot)

        count = service.apply_merger(
            old_security_id=test_security.id,
            new_security_id=new_security.id,
            exchange_ratio=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 1

        new_lots = list(tax_lot_repo.list_by_position(new_position.id))
        assert len(new_lots) == 1

    def test_merger_preserves_acquisition_date(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
        test_position: Position,
        test_account: Account,
    ) -> None:
        """New lots should preserve the original acquisition date."""
        new_security = Security(
            symbol="NEWCO",
            name="NewCo Inc.",
            asset_class=AssetClass.EQUITY,
        )
        security_repo.add(new_security)

        new_position = Position(account_id=test_account.id, security_id=new_security.id)
        position_repo.add(new_position)

        old_lot = TaxLot(
            position_id=test_position.id,
            acquisition_date=date(2019, 7, 20),
            cost_per_share=Money(Decimal("50.00")),
            original_quantity=Quantity(Decimal("100")),
        )
        tax_lot_repo.add(old_lot)

        service.apply_merger(
            old_security_id=test_security.id,
            new_security_id=new_security.id,
            exchange_ratio=Decimal("1.25"),
            effective_date=date(2024, 6, 15),
        )

        new_lots = list(tax_lot_repo.list_by_position(new_position.id))
        assert len(new_lots) == 1
        assert new_lots[0].acquisition_date == date(2019, 7, 20)


class TestApplySymbolChange:
    """Tests for the apply_symbol_change method."""

    def test_symbol_change_updates_security(
        self,
        service: CorporateActionServiceImpl,
        security_repo: SQLiteSecurityRepository,
        test_security: Security,
    ) -> None:
        """Symbol change should update the security's symbol."""
        original_id = test_security.id

        service.apply_symbol_change(
            security_id=test_security.id,
            new_symbol="NEWAAPL",
            effective_date=date(2024, 6, 15),
        )

        updated_security = security_repo.get(original_id)
        assert updated_security is not None
        assert updated_security.symbol == "NEWAAPL"
        assert updated_security.name == "Apple Inc."  # Name unchanged

    def test_symbol_change_preserves_other_fields(
        self,
        service: CorporateActionServiceImpl,
        security_repo: SQLiteSecurityRepository,
    ) -> None:
        """Symbol change should not affect other security fields."""
        security = Security(
            symbol="OLD",
            name="Old Corp",
            cusip="123456789",
            isin="US1234567890",
            asset_class=AssetClass.EQUITY,
            is_qsbs_eligible=True,
            qsbs_qualification_date=date(2020, 1, 1),
            issuer="Old Corp Inc.",
        )
        security_repo.add(security)

        service.apply_symbol_change(
            security_id=security.id,
            new_symbol="NEW",
            effective_date=date(2024, 6, 15),
        )

        updated = security_repo.get(security.id)
        assert updated is not None
        assert updated.symbol == "NEW"
        assert updated.name == "Old Corp"
        assert updated.cusip == "123456789"
        assert updated.isin == "US1234567890"
        assert updated.asset_class == AssetClass.EQUITY
        assert updated.is_qsbs_eligible is True
        assert updated.qsbs_qualification_date == date(2020, 1, 1)
        assert updated.issuer == "Old Corp Inc."


class TestMultiplePositions:
    """Tests for corporate actions affecting multiple positions."""

    def test_split_affects_all_positions_for_security(
        self,
        service: CorporateActionServiceImpl,
        tax_lot_repo: SQLiteTaxLotRepository,
        position_repo: SQLitePositionRepository,
        account_repo: SQLiteAccountRepository,
        security_repo: SQLiteSecurityRepository,
        test_entity: Entity,
        test_security: Security,
    ) -> None:
        """A split should affect lots across all positions holding the security."""
        # Create two accounts
        account1 = Account(
            name="Account 1",
            entity_id=test_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )
        account2 = Account(
            name="Account 2",
            entity_id=test_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.IRA,
        )
        account_repo.add(account1)
        account_repo.add(account2)

        # Create positions in both accounts
        pos1 = Position(account_id=account1.id, security_id=test_security.id)
        pos2 = Position(account_id=account2.id, security_id=test_security.id)
        position_repo.add(pos1)
        position_repo.add(pos2)

        # Create lots in both positions
        lot1 = TaxLot(
            position_id=pos1.id,
            acquisition_date=date(2023, 1, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
        )
        lot2 = TaxLot(
            position_id=pos2.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("120.00")),
            original_quantity=Quantity(Decimal("30")),
        )
        tax_lot_repo.add(lot1)
        tax_lot_repo.add(lot2)

        count = service.apply_split(
            security_id=test_security.id,
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
            effective_date=date(2024, 6, 15),
        )

        assert count == 2

        updated_lot1 = tax_lot_repo.get(lot1.id)
        updated_lot2 = tax_lot_repo.get(lot2.id)

        assert updated_lot1 is not None
        assert updated_lot1.original_quantity == Quantity(Decimal("100"))
        assert updated_lot1.cost_per_share == Money(Decimal("50.00"))

        assert updated_lot2 is not None
        assert updated_lot2.original_quantity == Quantity(Decimal("60"))
        assert updated_lot2.cost_per_share == Money(Decimal("60.00"))
