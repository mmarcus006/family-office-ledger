"""EntityOwnership domain model for Addepar-style ownership graph edges."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SelfOwnershipError(ValueError):
    def __init__(self, entity_id: UUID) -> None:
        self.entity_id = entity_id
        super().__init__(f"Entity {entity_id} cannot own itself")


@dataclass
class EntityOwnership:
    owner_entity_id: UUID
    owned_entity_id: UUID
    ownership_fraction: Decimal
    effective_start_date: date
    id: UUID = field(default_factory=uuid4)
    effective_end_date: date | None = None
    ownership_basis: str = "percent"
    ownership_type: str = "beneficial"
    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not isinstance(self.ownership_fraction, Decimal):
            object.__setattr__(
                self, "ownership_fraction", Decimal(str(self.ownership_fraction))
            )

        if self.owner_entity_id == self.owned_entity_id:
            raise SelfOwnershipError(self.owner_entity_id)

    def is_active_on(self, as_of_date: date) -> bool:
        if self.effective_start_date > as_of_date:
            return False
        if (
            self.effective_end_date is not None
            and as_of_date >= self.effective_end_date
        ):
            return False
        return True

    def end_ownership(self, end_date: date) -> None:
        self.effective_end_date = end_date
        self.updated_at = _utc_now()

    def update_fraction(self, new_fraction: Decimal) -> None:
        if not isinstance(new_fraction, Decimal):
            new_fraction = Decimal(str(new_fraction))
        self.ownership_fraction = new_fraction
        self.updated_at = _utc_now()


__all__ = ["EntityOwnership", "SelfOwnershipError"]
