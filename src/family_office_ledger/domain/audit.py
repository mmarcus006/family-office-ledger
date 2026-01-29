"""Audit trail domain models for tracking changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class AuditEntityType(str, Enum):
    ENTITY = "entity"
    ACCOUNT = "account"
    TRANSACTION = "transaction"
    POSITION = "position"
    SECURITY = "security"
    TAX_LOT = "tax_lot"
    RECONCILIATION_SESSION = "reconciliation_session"
    RECONCILIATION_MATCH = "reconciliation_match"
    TRANSFER_SESSION = "transfer_session"
    TRANSFER_MATCH = "transfer_match"


@dataclass
class AuditEntry:
    entity_type: AuditEntityType
    entity_id: UUID
    action: AuditAction
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    timestamp: datetime = field(default_factory=_utc_now)
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    change_summary: str = ""
    ip_address: str | None = None
    user_agent: str | None = None

    @property
    def has_changes(self) -> bool:
        return self.old_values is not None or self.new_values is not None

    @property
    def changed_fields(self) -> list[str]:
        if self.old_values is None or self.new_values is None:
            return []
        old_keys = set(self.old_values.keys())
        new_keys = set(self.new_values.keys())
        all_keys = old_keys | new_keys
        changed = []
        for key in all_keys:
            old_val = self.old_values.get(key)
            new_val = self.new_values.get(key)
            if old_val != new_val:
                changed.append(key)
        return sorted(changed)


@dataclass
class AuditLogSummary:
    total_entries: int
    entries_by_action: dict[AuditAction, int]
    entries_by_entity_type: dict[AuditEntityType, int]
    oldest_entry: datetime | None
    newest_entry: datetime | None
