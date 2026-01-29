"""Household domain model for family office ownership grouping."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Household:
    name: str
    id: UUID = field(default_factory=uuid4)
    primary_contact_entity_id: UUID | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _utc_now()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = _utc_now()

    def set_primary_contact(self, entity_id: UUID | None) -> None:
        self.primary_contact_entity_id = entity_id
        self.updated_at = _utc_now()


@dataclass
class HouseholdMember:
    """Represents membership of an entity in a household.

    Enables the Household → Entity relationship with effective dating
    for historical queries ("who was a member on this date?").
    """

    household_id: UUID
    entity_id: UUID
    id: UUID = field(default_factory=uuid4)
    role: str | None = None  # 'client', 'entity', etc.
    display_name: str | None = None  # household-scoped label
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    created_at: datetime = field(default_factory=_utc_now)
