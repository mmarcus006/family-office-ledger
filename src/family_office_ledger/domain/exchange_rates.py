"""Exchange rate domain model for currency conversion."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class ExchangeRateSource(str, Enum):
    """Source of exchange rate data."""

    MANUAL = "manual"
    ECB = "ecb"
    FED = "fed"
    BANK = "bank"
    API = "api"


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """Immutable exchange rate value object.

    Represents a conversion rate between two currencies on a specific date.
    """

    from_currency: str
    to_currency: str
    rate: Decimal
    effective_date: date
    id: UUID = field(default_factory=uuid4)
    source: ExchangeRateSource = ExchangeRateSource.MANUAL
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        """Validate and coerce rate to Decimal."""
        if not isinstance(self.rate, Decimal):
            object.__setattr__(self, "rate", Decimal(str(self.rate)))
        if self.rate <= 0:
            raise ValueError(f"Exchange rate must be positive, got {self.rate}")

    @property
    def inverse(self) -> "ExchangeRate":
        """Return the inverse exchange rate (to -> from)."""
        return ExchangeRate(
            from_currency=self.to_currency,
            to_currency=self.from_currency,
            rate=Decimal("1") / self.rate,
            effective_date=self.effective_date,
            source=self.source,
        )

    @property
    def pair(self) -> str:
        """Return currency pair string like 'USD/EUR'."""
        return f"{self.from_currency}/{self.to_currency}"
