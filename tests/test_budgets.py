"""Tests for budget domain models."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.budgets import (
    Budget,
    BudgetLineItem,
    BudgetPeriodType,
    BudgetVariance,
)
from family_office_ledger.domain.value_objects import Money


class TestBudgetPeriodType:
    """Tests for BudgetPeriodType enum."""

    def test_monthly_value(self) -> None:
        assert BudgetPeriodType.MONTHLY.value == "monthly"

    def test_quarterly_value(self) -> None:
        assert BudgetPeriodType.QUARTERLY.value == "quarterly"

    def test_annual_value(self) -> None:
        assert BudgetPeriodType.ANNUAL.value == "annual"

    def test_custom_value(self) -> None:
        assert BudgetPeriodType.CUSTOM.value == "custom"

    def test_string_serialization(self) -> None:
        """BudgetPeriodType should serialize as string for JSON."""
        assert BudgetPeriodType.MONTHLY.value == "monthly"
        assert isinstance(BudgetPeriodType.MONTHLY, str)


class TestBudget:
    """Tests for Budget dataclass."""

    def test_budget_creation_required_fields(self) -> None:
        entity_id = uuid4()
        budget = Budget(
            name="Q1 2026 Budget",
            entity_id=entity_id,
            period_type=BudgetPeriodType.QUARTERLY,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )

        assert budget.name == "Q1 2026 Budget"
        assert budget.entity_id == entity_id
        assert budget.period_type == BudgetPeriodType.QUARTERLY
        assert budget.start_date == date(2026, 1, 1)
        assert budget.end_date == date(2026, 3, 31)
        assert budget.id is not None
        assert budget.is_active is True
        assert budget.created_at is not None
        assert budget.updated_at is not None

    def test_budget_creation_with_all_fields(self) -> None:
        entity_id = uuid4()
        budget_id = uuid4()
        created = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

        budget = Budget(
            name="Annual Budget 2026",
            entity_id=entity_id,
            period_type=BudgetPeriodType.ANNUAL,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            id=budget_id,
            is_active=True,
            created_at=created,
            updated_at=created,
        )

        assert budget.id == budget_id
        assert budget.created_at == created

    def test_budget_is_active_by_default(self) -> None:
        budget = Budget(
            name="Test Budget",
            entity_id=uuid4(),
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        assert budget.is_active is True

    def test_budget_deactivate(self) -> None:
        budget = Budget(
            name="Test Budget",
            entity_id=uuid4(),
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        original_updated_at = budget.updated_at

        budget.deactivate()

        assert budget.is_active is False
        assert budget.updated_at >= original_updated_at


class TestBudgetLineItem:
    """Tests for BudgetLineItem dataclass."""

    def test_line_item_creation_required_fields(self) -> None:
        budget_id = uuid4()
        line_item = BudgetLineItem(
            budget_id=budget_id,
            category="payroll",
            budgeted_amount=Money(Decimal("5000.00")),
        )

        assert line_item.budget_id == budget_id
        assert line_item.category == "payroll"
        assert line_item.budgeted_amount == Money(Decimal("5000.00"))
        assert line_item.id is not None
        assert line_item.account_id is None
        assert line_item.notes == ""

    def test_line_item_creation_with_all_fields(self) -> None:
        budget_id = uuid4()
        line_item_id = uuid4()
        account_id = uuid4()

        line_item = BudgetLineItem(
            budget_id=budget_id,
            category="rent",
            budgeted_amount=Money(Decimal("3000.00")),
            id=line_item_id,
            account_id=account_id,
            notes="Monthly office rent",
        )

        assert line_item.id == line_item_id
        assert line_item.account_id == account_id
        assert line_item.notes == "Monthly office rent"

    def test_line_item_with_different_currencies(self) -> None:
        line_item = BudgetLineItem(
            budget_id=uuid4(),
            category="travel",
            budgeted_amount=Money(Decimal("1500.00"), "EUR"),
        )

        assert line_item.budgeted_amount.currency.value == "EUR"


class TestBudgetVariance:
    """Tests for BudgetVariance value object."""

    def test_variance_under_budget(self) -> None:
        variance = BudgetVariance(
            category="payroll",
            budgeted=Money(Decimal("5000.00")),
            actual=Money(Decimal("4500.00")),
        )

        assert variance.variance == Money(Decimal("500.00"))
        assert variance.variance_percent == Decimal("10.00")
        assert variance.is_over_budget is False

    def test_variance_over_budget(self) -> None:
        variance = BudgetVariance(
            category="travel",
            budgeted=Money(Decimal("1000.00")),
            actual=Money(Decimal("1200.00")),
        )

        assert variance.variance == Money(Decimal("-200.00"))
        assert variance.variance_percent == Decimal("-20.00")
        assert variance.is_over_budget is True

    def test_variance_exactly_on_budget(self) -> None:
        variance = BudgetVariance(
            category="rent",
            budgeted=Money(Decimal("3000.00")),
            actual=Money(Decimal("3000.00")),
        )

        assert variance.variance == Money(Decimal("0"))
        assert variance.variance_percent == Decimal("0.00")
        assert variance.is_over_budget is False

    def test_variance_zero_budget(self) -> None:
        """Zero budget should not cause division by zero."""
        variance = BudgetVariance(
            category="misc",
            budgeted=Money(Decimal("0")),
            actual=Money(Decimal("100.00")),
        )

        assert variance.variance_percent == Decimal("0")
        assert variance.is_over_budget is True

    def test_variance_is_frozen(self) -> None:
        """BudgetVariance should be immutable."""
        variance = BudgetVariance(
            category="payroll",
            budgeted=Money(Decimal("5000.00")),
            actual=Money(Decimal("4500.00")),
        )

        with pytest.raises(AttributeError):
            variance.category = "rent"  # type: ignore[misc]
