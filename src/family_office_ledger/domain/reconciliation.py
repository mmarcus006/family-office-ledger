"""Reconciliation session and match domain models."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class ReconciliationSessionStatus(str, Enum):
    """Status of a reconciliation session."""

    PENDING = "pending"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ReconciliationMatchStatus(str, Enum):
    """Status of a reconciliation match."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclass
class ReconciliationMatch:
    """A match between an imported transaction and a ledger transaction.

    Represents a proposed match between a bank/brokerage import and an
    existing ledger transaction, with confidence scoring and status tracking.
    """

    session_id: UUID
    imported_id: str
    imported_date: date
    imported_amount: Decimal
    id: UUID = field(default_factory=uuid4)
    imported_description: str = ""
    suggested_ledger_txn_id: UUID | None = None
    confidence_score: int = 0
    status: ReconciliationMatchStatus = ReconciliationMatchStatus.PENDING
    actioned_at: datetime | None = None
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class ReconciliationSession:
    """A reconciliation session for an account.

    Represents a single reconciliation workflow where a user imports
    transactions from a file and matches them against ledger entries.
    """

    account_id: UUID
    file_name: str
    file_format: str
    id: UUID = field(default_factory=uuid4)
    status: ReconciliationSessionStatus = ReconciliationSessionStatus.PENDING
    matches: list[ReconciliationMatch] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    closed_at: datetime | None = None

    @property
    def pending_count(self) -> int:
        """Count of matches with PENDING status."""
        return sum(
            1 for m in self.matches if m.status == ReconciliationMatchStatus.PENDING
        )

    @property
    def confirmed_count(self) -> int:
        """Count of matches with CONFIRMED status."""
        return sum(
            1 for m in self.matches if m.status == ReconciliationMatchStatus.CONFIRMED
        )

    @property
    def rejected_count(self) -> int:
        """Count of matches with REJECTED status."""
        return sum(
            1 for m in self.matches if m.status == ReconciliationMatchStatus.REJECTED
        )

    @property
    def skipped_count(self) -> int:
        """Count of matches with SKIPPED status."""
        return sum(
            1 for m in self.matches if m.status == ReconciliationMatchStatus.SKIPPED
        )

    @property
    def match_rate(self) -> float:
        """Ratio of confirmed matches to total matches (0.0-1.0)."""
        if not self.matches:
            return 0.0
        return self.confirmed_count / len(self.matches)
