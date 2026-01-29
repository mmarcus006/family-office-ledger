"""Transfer matching domain models for pairing inter-account transfers.

This module provides domain models for matching equal-opposite transactions
between accounts that represent the same underlying transfer.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class TransferMatchStatus(str, Enum):
    """Status of a transfer match."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass
class TransferMatch:
    """A matched pair of transactions representing an inter-account transfer.

    Represents a pairing between two transactions:
    - source_transaction: The outflow (debit from source account)
    - target_transaction: The inflow (credit to target account)

    These should have equal amounts (opposite signs) and be within a
    reasonable date range of each other.
    """

    source_transaction_id: UUID
    target_transaction_id: UUID
    source_account_id: UUID
    target_account_id: UUID
    amount: Decimal
    transfer_date: date
    id: UUID = field(default_factory=uuid4)
    confidence_score: int = 0
    status: TransferMatchStatus = TransferMatchStatus.PENDING
    memo: str = ""
    confirmed_at: datetime | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def is_pending(self) -> bool:
        """Check if match is pending review."""
        return self.status == TransferMatchStatus.PENDING

    @property
    def is_confirmed(self) -> bool:
        """Check if match has been confirmed."""
        return self.status == TransferMatchStatus.CONFIRMED

    @property
    def is_rejected(self) -> bool:
        """Check if match has been rejected."""
        return self.status == TransferMatchStatus.REJECTED


@dataclass
class TransferMatchingSession:
    """A session for matching transfers across accounts.

    Groups transfer matches for review and confirmation.
    """

    id: UUID = field(default_factory=uuid4)
    entity_ids: list[UUID] = field(default_factory=list)
    date_tolerance_days: int = 3
    matches: list[TransferMatch] = field(default_factory=list)
    status: str = "pending"
    created_at: datetime = field(default_factory=_utc_now)
    closed_at: datetime | None = None

    @property
    def pending_count(self) -> int:
        """Count of matches with PENDING status."""
        return sum(1 for m in self.matches if m.status == TransferMatchStatus.PENDING)

    @property
    def confirmed_count(self) -> int:
        """Count of matches with CONFIRMED status."""
        return sum(1 for m in self.matches if m.status == TransferMatchStatus.CONFIRMED)

    @property
    def rejected_count(self) -> int:
        """Count of matches with REJECTED status."""
        return sum(1 for m in self.matches if m.status == TransferMatchStatus.REJECTED)

    @property
    def total_matched_amount(self) -> Decimal:
        """Total amount of confirmed transfer matches."""
        return sum(
            (m.amount for m in self.matches if m.is_confirmed),
            Decimal("0"),
        )


__all__ = [
    "TransferMatchStatus",
    "TransferMatch",
    "TransferMatchingSession",
]
