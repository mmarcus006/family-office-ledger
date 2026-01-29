from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AssetClass,
    EntityType,
    Money,
    Quantity,
    TaxTreatment,
)


@dataclass
class Entity:
    name: str
    entity_type: EntityType
    id: UUID = field(default_factory=uuid4)
    fiscal_year_end: date = field(
        default_factory=lambda: date(date.today().year, 12, 31)
    )
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    tax_treatment: TaxTreatment | None = None
    tax_id: str | None = None
    tax_id_type: str | None = None
    formation_date: date | None = None
    jurisdiction: str | None = None

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _utc_now()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = _utc_now()


@dataclass
class Account:
    name: str
    entity_id: UUID
    account_type: AccountType
    id: UUID = field(default_factory=uuid4)
    sub_type: AccountSubType = AccountSubType.OTHER
    currency: str = "USD"
    is_investment_account: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        investment_sub_types = {
            AccountSubType.BROKERAGE,
            AccountSubType.IRA,
            AccountSubType.ROTH_IRA,
            AccountSubType.K401,
            AccountSubType.K529,
            AccountSubType.PRIVATE_EQUITY,
            AccountSubType.VENTURE_CAPITAL,
            AccountSubType.CRYPTO,
        }
        if self.sub_type in investment_sub_types:
            self.is_investment_account = True


@dataclass
class Security:
    symbol: str
    name: str
    id: UUID = field(default_factory=uuid4)
    cusip: str | None = None
    isin: str | None = None
    asset_class: AssetClass = AssetClass.EQUITY
    is_qsbs_eligible: bool = False
    qsbs_qualification_date: date | None = None
    issuer: str | None = None
    is_active: bool = True

    @property
    def has_qsbs_status(self) -> bool:
        return self.is_qsbs_eligible and self.qsbs_qualification_date is not None

    def mark_qsbs_eligible(self, qualification_date: date) -> None:
        self.is_qsbs_eligible = True
        self.qsbs_qualification_date = qualification_date


@dataclass
class Position:
    account_id: UUID
    security_id: UUID
    id: UUID = field(default_factory=uuid4)
    _quantity: Quantity = field(default_factory=Quantity.zero)
    _cost_basis: Money = field(default_factory=lambda: Money.zero())
    _market_value: Money = field(default_factory=lambda: Money.zero())

    @property
    def quantity(self) -> Quantity:
        return self._quantity

    @property
    def cost_basis(self) -> Money:
        return self._cost_basis

    @property
    def market_value(self) -> Money:
        return self._market_value

    @property
    def unrealized_gain(self) -> Money:
        return self._market_value - self._cost_basis

    @property
    def is_long(self) -> bool:
        return self._quantity.is_positive

    @property
    def is_short(self) -> bool:
        return self._quantity.is_negative

    @property
    def is_flat(self) -> bool:
        return self._quantity.is_zero

    def update_from_lots(self, total_quantity: Quantity, total_cost: Money) -> None:
        self._quantity = total_quantity
        self._cost_basis = total_cost

    def update_market_value(self, price: Decimal) -> None:
        self._market_value = Money(
            self._quantity.value * price, self._cost_basis.currency
        )

    @property
    def average_cost_per_share(self) -> Decimal | None:
        if self._quantity.is_zero:
            return None
        return self._cost_basis.amount / self._quantity.value
