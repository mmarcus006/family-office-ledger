from datetime import date
from decimal import Decimal

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


@pytest.fixture
def sample_entity() -> Entity:
    return Entity(
        name="Smith Family Trust",
        entity_type=EntityType.TRUST,
        fiscal_year_end=date(2025, 12, 31),
    )


@pytest.fixture
def sample_llc_entity() -> Entity:
    return Entity(
        name="Smith Holdings LLC",
        entity_type=EntityType.LLC,
    )


@pytest.fixture
def sample_account(sample_entity: Entity) -> Account:
    return Account(
        name="Main Checking",
        entity_id=sample_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )


@pytest.fixture
def sample_brokerage_account(sample_entity: Entity) -> Account:
    return Account(
        name="Schwab Brokerage",
        entity_id=sample_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.BROKERAGE,
    )


@pytest.fixture
def sample_security() -> Security:
    return Security(
        symbol="AAPL",
        name="Apple Inc.",
        cusip="037833100",
        asset_class=AssetClass.EQUITY,
    )


@pytest.fixture
def sample_qsbs_security() -> Security:
    return Security(
        symbol="STARTUP",
        name="Startup Corp",
        asset_class=AssetClass.EQUITY,
        is_qsbs_eligible=True,
        qsbs_qualification_date=date(2020, 1, 15),
    )


@pytest.fixture
def sample_position(
    sample_brokerage_account: Account, sample_security: Security
) -> Position:
    return Position(
        account_id=sample_brokerage_account.id,
        security_id=sample_security.id,
    )


@pytest.fixture
def sample_tax_lot(sample_position: Position) -> TaxLot:
    return TaxLot(
        position_id=sample_position.id,
        acquisition_date=date(2023, 6, 15),
        cost_per_share=Money(Decimal("150.00")),
        original_quantity=Quantity(Decimal("100")),
    )


@pytest.fixture
def sample_money() -> Money:
    return Money(Decimal("1000.00"), "USD")


@pytest.fixture
def sample_quantity() -> Quantity:
    return Quantity(Decimal("100"))
