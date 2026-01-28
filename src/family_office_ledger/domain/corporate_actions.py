"""Corporate action and price domain models."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import CorporateActionType


@dataclass
class Price:
    """Historical price for a security."""

    security_id: UUID
    price_date: date
    price: Decimal
    source: str = "manual"
    id: UUID = field(default_factory=uuid4)


@dataclass
class CorporateAction:
    """Corporate action affecting a security (split, merger, spinoff, etc.)."""

    security_id: UUID
    action_type: CorporateActionType
    effective_date: date
    ratio_numerator: Decimal
    ratio_denominator: Decimal
    resulting_security_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)

    @property
    def ratio(self) -> Decimal:
        """Calculate the conversion ratio (numerator / denominator)."""
        return self.ratio_numerator / self.ratio_denominator

    @property
    def is_split(self) -> bool:
        """Return True if this is a stock split or reverse split."""
        return self.action_type in (
            CorporateActionType.SPLIT,
            CorporateActionType.REVERSE_SPLIT,
        )

    @property
    def requires_resulting_security(self) -> bool:
        """Return True if this action type requires a resulting security ID."""
        return self.action_type in (
            CorporateActionType.SPINOFF,
            CorporateActionType.MERGER,
        )
