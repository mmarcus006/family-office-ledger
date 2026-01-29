from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import Money


def _utc_now() -> datetime:
    return datetime.now(UTC)


class BudgetPeriodType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


@dataclass
class Budget:
    name: str
    entity_id: UUID
    period_type: BudgetPeriodType
    start_date: date
    end_date: date
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _utc_now()


@dataclass
class BudgetLineItem:
    budget_id: UUID
    category: str
    budgeted_amount: Money
    id: UUID = field(default_factory=uuid4)
    account_id: UUID | None = None
    notes: str = ""


@dataclass(frozen=True)
class BudgetVariance:
    category: str
    budgeted: Money
    actual: Money

    @property
    def variance(self) -> Money:
        return self.budgeted - self.actual

    @property
    def variance_percent(self) -> Decimal:
        if self.budgeted.amount == 0:
            return Decimal("0")
        return (
            (self.budgeted.amount - self.actual.amount) / self.budgeted.amount * 100
        ).quantize(Decimal("0.01"))

    @property
    def is_over_budget(self) -> bool:
        return self.actual.amount > self.budgeted.amount


__all__ = [
    "Budget",
    "BudgetLineItem",
    "BudgetPeriodType",
    "BudgetVariance",
]
