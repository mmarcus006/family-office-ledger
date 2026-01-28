from datetime import date
from decimal import Decimal

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


class TestEntity:
    def test_entity_creation_with_required_fields(self):
        entity = Entity(name="Smith Family Trust", entity_type=EntityType.TRUST)

        assert entity.name == "Smith Family Trust"
        assert entity.entity_type == EntityType.TRUST
        assert entity.is_active is True
        assert entity.id is not None

    def test_entity_creation_with_all_fields(self):
        entity = Entity(
            name="Holdings LLC",
            entity_type=EntityType.LLC,
            fiscal_year_end=date(2025, 3, 31),
            is_active=True,
        )

        assert entity.name == "Holdings LLC"
        assert entity.entity_type == EntityType.LLC
        assert entity.fiscal_year_end == date(2025, 3, 31)

    def test_entity_deactivate(self, sample_entity: Entity):
        original_updated_at = sample_entity.updated_at

        sample_entity.deactivate()

        assert sample_entity.is_active is False
        assert sample_entity.updated_at >= original_updated_at

    def test_entity_activate(self, sample_entity: Entity):
        sample_entity.is_active = False

        sample_entity.activate()

        assert sample_entity.is_active is True

    def test_entity_types_cover_family_office_structures(self):
        assert EntityType.LLC.value == "llc"
        assert EntityType.TRUST.value == "trust"
        assert EntityType.PARTNERSHIP.value == "partnership"
        assert EntityType.INDIVIDUAL.value == "individual"
        assert EntityType.HOLDING_CO.value == "holding_co"


class TestAccount:
    def test_account_creation_requires_entity_id(self, sample_entity: Entity):
        account = Account(
            name="Main Checking",
            entity_id=sample_entity.id,
            account_type=AccountType.ASSET,
        )

        assert account.entity_id == sample_entity.id
        assert account.name == "Main Checking"
        assert account.account_type == AccountType.ASSET

    def test_account_with_investment_subtype_sets_investment_flag(
        self, sample_entity: Entity
    ):
        account = Account(
            name="Brokerage",
            entity_id=sample_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.BROKERAGE,
        )

        assert account.is_investment_account is True

    def test_account_with_checking_subtype_not_investment(self, sample_entity: Entity):
        account = Account(
            name="Checking",
            entity_id=sample_entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
        )

        assert account.is_investment_account is False

    def test_account_types_cover_double_entry_categories(self):
        assert AccountType.ASSET.value == "asset"
        assert AccountType.LIABILITY.value == "liability"
        assert AccountType.EQUITY.value == "equity"
        assert AccountType.INCOME.value == "income"
        assert AccountType.EXPENSE.value == "expense"

    def test_account_subtypes_cover_family_office_needs(self):
        investment_types = [
            AccountSubType.BROKERAGE,
            AccountSubType.IRA,
            AccountSubType.ROTH_IRA,
            AccountSubType.K401,
            AccountSubType.K529,
            AccountSubType.PRIVATE_EQUITY,
            AccountSubType.VENTURE_CAPITAL,
            AccountSubType.CRYPTO,
        ]
        for sub_type in investment_types:
            assert sub_type is not None


class TestSecurity:
    def test_security_creation_with_symbol_and_name(self):
        security = Security(symbol="AAPL", name="Apple Inc.")

        assert security.symbol == "AAPL"
        assert security.name == "Apple Inc."
        assert security.is_active is True

    def test_security_with_cusip_and_isin(self):
        security = Security(
            symbol="MSFT",
            name="Microsoft Corp",
            cusip="594918104",
            isin="US5949181045",
        )

        assert security.cusip == "594918104"
        assert security.isin == "US5949181045"

    def test_security_qsbs_eligibility_tracking(self):
        security = Security(
            symbol="STARTUP",
            name="Startup Corp",
            is_qsbs_eligible=True,
            qsbs_qualification_date=date(2020, 1, 15),
        )

        assert security.is_qsbs_eligible is True
        assert security.qsbs_qualification_date == date(2020, 1, 15)
        assert security.has_qsbs_status is True

    def test_security_mark_qsbs_eligible(self):
        security = Security(symbol="NEWCO", name="New Company")
        assert security.has_qsbs_status is False

        security.mark_qsbs_eligible(date(2024, 6, 1))

        assert security.is_qsbs_eligible is True
        assert security.qsbs_qualification_date == date(2024, 6, 1)
        assert security.has_qsbs_status is True

    def test_asset_classes_cover_family_office_investments(self):
        assert AssetClass.EQUITY.value == "equity"
        assert AssetClass.FIXED_INCOME.value == "fixed_income"
        assert AssetClass.ALTERNATIVE.value == "alternative"
        assert AssetClass.REAL_ESTATE.value == "real_estate"
        assert AssetClass.CRYPTO.value == "crypto"
        assert AssetClass.PRIVATE_EQUITY.value == "private_equity"
        assert AssetClass.VENTURE_CAPITAL.value == "venture_capital"


class TestPosition:
    def test_position_creation_links_account_and_security(
        self, sample_brokerage_account: Account, sample_security: Security
    ):
        position = Position(
            account_id=sample_brokerage_account.id,
            security_id=sample_security.id,
        )

        assert position.account_id == sample_brokerage_account.id
        assert position.security_id == sample_security.id

    def test_position_starts_with_zero_quantity(self, sample_position: Position):
        assert sample_position.quantity.is_zero
        assert sample_position.cost_basis.is_zero
        assert sample_position.market_value.is_zero

    def test_position_update_from_lots(self, sample_position: Position):
        sample_position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )

        assert sample_position.quantity == Quantity(Decimal("100"))
        assert sample_position.cost_basis == Money(Decimal("15000.00"))

    def test_position_update_market_value(self, sample_position: Position):
        sample_position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )

        sample_position.update_market_value(Decimal("175.00"))

        assert sample_position.market_value == Money(Decimal("17500.00"))

    def test_position_unrealized_gain_calculation(self, sample_position: Position):
        sample_position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )
        sample_position.update_market_value(Decimal("175.00"))

        unrealized = sample_position.unrealized_gain

        assert unrealized == Money(Decimal("2500.00"))

    def test_position_average_cost_per_share(self, sample_position: Position):
        sample_position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )

        avg_cost = sample_position.average_cost_per_share

        assert avg_cost == Decimal("150.00")

    def test_position_is_long_when_positive_quantity(self, sample_position: Position):
        sample_position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )

        assert sample_position.is_long is True
        assert sample_position.is_short is False
        assert sample_position.is_flat is False

    def test_position_is_flat_when_zero_quantity(self, sample_position: Position):
        assert sample_position.is_flat is True
        assert sample_position.is_long is False
        assert sample_position.is_short is False
