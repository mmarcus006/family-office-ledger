from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Vendor:
    name: str
    id: UUID = field(default_factory=uuid4)
    category: str | None = None
    tax_id: str | None = None
    is_1099_eligible: bool = False
    default_account_id: UUID | None = None
    default_category: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _utc_now()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = _utc_now()
