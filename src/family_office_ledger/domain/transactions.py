from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import AcquisitionType, Money, Quantity


def _utc_now() -> datetime:
    return datetime.now(UTC)


class UnbalancedTransactionError(Exception):
    pass


class InsufficientQuantityError(Exception):
    pass


class InvalidLotOperationError(Exception):
    pass


@dataclass
class Entry:
    account_id: UUID
    id: UUID = field(default_factory=uuid4)
    debit_amount: Money = field(default_factory=lambda: Money.zero())
    credit_amount: Money = field(default_factory=lambda: Money.zero())
    memo: str = ""
    tax_lot_id: UUID | None = None
    category: str | None = None

    @property
    def net_amount(self) -> Money:
        return self.debit_amount - self.credit_amount

    @property
    def is_debit(self) -> bool:
        return self.debit_amount.is_positive and self.credit_amount.is_zero

    @property
    def is_credit(self) -> bool:
        return self.credit_amount.is_positive and self.debit_amount.is_zero


@dataclass
class Transaction:
    transaction_date: date
    entries: list[Entry] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    posted_date: date | None = None
    memo: str = ""
    reference: str = ""
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)
    is_reversed: bool = False
    reverses_transaction_id: UUID | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    vendor_id: UUID | None = None
    is_recurring: bool = False
    recurring_frequency: str | None = None

    def __post_init__(self) -> None:
        if self.posted_date is None:
            self.posted_date = self.transaction_date

    @property
    def total_debits(self) -> Money:
        if not self.entries:
            return Money.zero()
        currency = self.entries[0].debit_amount.currency
        total = Decimal("0")
        for entry in self.entries:
            total += entry.debit_amount.amount
        return Money(total, currency)

    @property
    def total_credits(self) -> Money:
        if not self.entries:
            return Money.zero()
        currency = self.entries[0].credit_amount.currency
        total = Decimal("0")
        for entry in self.entries:
            total += entry.credit_amount.amount
        return Money(total, currency)

    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits

    def validate(self) -> None:
        if not self.is_balanced:
            raise UnbalancedTransactionError(
                f"Transaction {self.id} is unbalanced: "
                f"debits={self.total_debits.amount}, credits={self.total_credits.amount}"
            )

    def add_entry(self, entry: Entry) -> None:
        self.entries.append(entry)

    @property
    def is_reversal(self) -> bool:
        return self.reverses_transaction_id is not None

    @property
    def account_ids(self) -> set[UUID]:
        return {entry.account_id for entry in self.entries}


@dataclass
class TaxLot:
    position_id: UUID
    acquisition_date: date
    cost_per_share: Money
    original_quantity: Quantity
    id: UUID = field(default_factory=uuid4)
    remaining_quantity: Quantity = field(init=False)
    acquisition_type: AcquisitionType = AcquisitionType.PURCHASE
    disposition_date: date | None = None
    is_covered: bool = True
    wash_sale_disallowed: bool = False
    wash_sale_adjustment: Money = field(default_factory=lambda: Money.zero())
    reference: str = ""
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.remaining_quantity = self.original_quantity

    @property
    def total_cost(self) -> Money:
        return self.cost_per_share * self.original_quantity.value

    @property
    def remaining_cost(self) -> Money:
        return self.cost_per_share * self.remaining_quantity.value

    @property
    def adjusted_cost_per_share(self) -> Money:
        if self.wash_sale_disallowed and not self.wash_sale_adjustment.is_zero:
            adjustment_per_share = Money(
                self.wash_sale_adjustment.amount / self.original_quantity.value,
                self.cost_per_share.currency,
            )
            return self.cost_per_share + adjustment_per_share
        return self.cost_per_share

    @property
    def is_fully_disposed(self) -> bool:
        return self.remaining_quantity.is_zero

    @property
    def is_partially_disposed(self) -> bool:
        return (
            not self.remaining_quantity.is_zero
            and self.remaining_quantity < self.original_quantity
        )

    @property
    def is_open(self) -> bool:
        return not self.is_fully_disposed

    def sell(self, quantity: Quantity, disposition_date: date) -> Money:
        if quantity > self.remaining_quantity:
            raise InsufficientQuantityError(
                f"Cannot sell {quantity.value} shares from lot {self.id}: "
                f"only {self.remaining_quantity.value} remaining"
            )
        if disposition_date < self.acquisition_date:
            raise InvalidLotOperationError(
                f"Disposition date {disposition_date} cannot be before "
                f"acquisition date {self.acquisition_date}"
            )

        cost_basis_sold = self.adjusted_cost_per_share * quantity.value
        self.remaining_quantity = self.remaining_quantity - quantity

        if self.is_fully_disposed:
            self.disposition_date = disposition_date

        return cost_basis_sold

    def apply_split(self, ratio_numerator: Decimal, ratio_denominator: Decimal) -> None:
        ratio = ratio_numerator / ratio_denominator
        new_original = Quantity(self.original_quantity.value * ratio)
        new_remaining = Quantity(self.remaining_quantity.value * ratio)
        new_cost_per_share = Money(
            self.cost_per_share.amount / ratio, self.cost_per_share.currency
        )

        self.original_quantity = new_original
        self.remaining_quantity = new_remaining
        self.cost_per_share = new_cost_per_share

    @property
    def holding_period_days(self) -> int:
        end_date = self.disposition_date or date.today()
        return (end_date - self.acquisition_date).days

    @property
    def is_long_term(self) -> bool:
        return self.holding_period_days > 365

    @property
    def is_short_term(self) -> bool:
        return self.holding_period_days <= 365

    def mark_wash_sale(self, disallowed_amount: Money) -> None:
        self.wash_sale_disallowed = True
        self.wash_sale_adjustment = disallowed_amount
