"""Domain models for K-1 partnership tax documents and reconciliation.

Provides comprehensive tracking for:
- Schedule K-1 (Form 1065) data with all standard boxes
- Partnership tax capital accounts (704(b) and tax basis)
- K-1 to ledger reconciliation
- Section 754 step-up tracking
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import Money


def _utc_now() -> datetime:
    return datetime.now(UTC)


class K1Type(str, Enum):
    """Type of K-1 form."""

    FORM_1065 = "1065"  # Partnership
    FORM_1120S = "1120s"  # S-Corporation
    FORM_1041 = "1041"  # Estate/Trust


class ReconciliationStatus(str, Enum):
    """Status of K-1 reconciliation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RECONCILED = "reconciled"
    DISCREPANCY = "discrepancy"
    APPROVED = "approved"


class CapitalAccountMethod(str, Enum):
    """Method for capital account reporting."""

    TAX_BASIS = "tax_basis"
    GAAP = "gaap"
    SECTION_704B = "section_704b"
    OTHER = "other"


@dataclass
class K1Box:
    """A single box/line item from a K-1."""

    box_number: str
    description: str
    amount: Money
    code: str | None = None  # For boxes with multiple codes (e.g., Box 11)
    is_passive: bool | None = None  # For passive vs non-passive income
    is_portfolio: bool | None = None  # For portfolio income
    notes: str | None = None


@dataclass
class K1Document:
    """A Schedule K-1 tax document.

    Represents a complete K-1 with all standard boxes for Form 1065.
    """

    entity_id: UUID  # The entity that received the K-1
    partnership_name: str
    partnership_ein: str
    tax_year: int
    id: UUID = field(default_factory=uuid4)
    k1_type: K1Type = K1Type.FORM_1065

    # Partner information (Part II)
    partner_name: str | None = None
    partner_ssn_ein: str | None = None
    partner_type: str | None = None  # "individual", "corporation", etc.
    is_general_partner: bool = False
    is_domestic: bool = True
    partner_share_profit_beginning: Decimal | None = None  # %
    partner_share_profit_ending: Decimal | None = None
    partner_share_loss_beginning: Decimal | None = None
    partner_share_loss_ending: Decimal | None = None
    partner_share_capital_beginning: Decimal | None = None
    partner_share_capital_ending: Decimal | None = None

    # Part III - Partner's Share of Current Year Income, etc.
    # Box 1: Ordinary business income (loss)
    box_1_ordinary_income: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 2: Net rental real estate income (loss)
    box_2_rental_real_estate: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 3: Other net rental income (loss)
    box_3_other_rental: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 4: Guaranteed payments for services
    box_4a_guaranteed_services: Money = field(default_factory=lambda: Money(Decimal("0")))
    # Box 4b: Guaranteed payments for capital
    box_4b_guaranteed_capital: Money = field(default_factory=lambda: Money(Decimal("0")))
    # Box 4c: Total guaranteed payments
    box_4c_guaranteed_total: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 5: Interest income
    box_5_interest: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 6a: Ordinary dividends
    box_6a_ordinary_dividends: Money = field(default_factory=lambda: Money(Decimal("0")))
    # Box 6b: Qualified dividends
    box_6b_qualified_dividends: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 7: Royalties
    box_7_royalties: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 8: Net short-term capital gain (loss)
    box_8_short_term_gain: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 9a: Net long-term capital gain (loss)
    box_9a_long_term_gain: Money = field(default_factory=lambda: Money(Decimal("0")))
    # Box 9b: Collectibles (28%) gain
    box_9b_collectibles_gain: Money = field(default_factory=lambda: Money(Decimal("0")))
    # Box 9c: Unrecaptured Section 1250 gain
    box_9c_section_1250: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 10: Net Section 1231 gain (loss)
    box_10_section_1231: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 11: Other income (loss) - with codes
    box_11_other_income: list[K1Box] = field(default_factory=list)

    # Box 12: Section 179 deduction
    box_12_section_179: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 13: Other deductions - with codes
    box_13_other_deductions: list[K1Box] = field(default_factory=list)

    # Box 14: Self-employment earnings
    box_14a_net_se_earnings: Money = field(default_factory=lambda: Money(Decimal("0")))
    box_14b_gross_se_income: Money = field(default_factory=lambda: Money(Decimal("0")))
    box_14c_gross_se_income_fica: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 15: Credits - with codes
    box_15_credits: list[K1Box] = field(default_factory=list)

    # Box 16: Foreign transactions - with codes
    box_16_foreign: list[K1Box] = field(default_factory=list)

    # Box 17: Alternative minimum tax items
    box_17_amt: list[K1Box] = field(default_factory=list)

    # Box 18: Tax-exempt income and nondeductible expenses
    box_18a_tax_exempt_interest: Money = field(default_factory=lambda: Money(Decimal("0")))
    box_18b_other_tax_exempt: Money = field(default_factory=lambda: Money(Decimal("0")))
    box_18c_nondeductible_expenses: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 19: Distributions
    box_19a_cash_distributions: Money = field(default_factory=lambda: Money(Decimal("0")))
    box_19b_property_distributions: Money = field(default_factory=lambda: Money(Decimal("0")))
    box_19c_property_distributions_fmv: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Box 20: Other information - with codes
    box_20_other_info: list[K1Box] = field(default_factory=list)

    # Part II continued - Capital Account Analysis (L)
    capital_account_beginning: Money = field(default_factory=lambda: Money(Decimal("0")))
    capital_contributed_during_year: Money = field(default_factory=lambda: Money(Decimal("0")))
    current_year_increase: Money = field(default_factory=lambda: Money(Decimal("0")))
    withdrawals_distributions: Money = field(default_factory=lambda: Money(Decimal("0")))
    capital_account_ending: Money = field(default_factory=lambda: Money(Decimal("0")))
    capital_account_method: CapitalAccountMethod = CapitalAccountMethod.TAX_BASIS

    # Partner's share of liabilities
    share_nonrecourse: Money = field(default_factory=lambda: Money(Decimal("0")))
    share_qualified_nonrecourse: Money = field(default_factory=lambda: Money(Decimal("0")))
    share_recourse: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Reconciliation tracking
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.PENDING
    reconciled_by: UUID | None = None
    reconciled_at: datetime | None = None
    discrepancy_notes: str | None = None

    # Document metadata
    received_date: date | None = None
    document_url: str | None = None
    source_file_name: str | None = None

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @property
    def total_income(self) -> Money:
        """Total income from all sources."""
        total = (
            self.box_1_ordinary_income.amount
            + self.box_2_rental_real_estate.amount
            + self.box_3_other_rental.amount
            + self.box_4c_guaranteed_total.amount
            + self.box_5_interest.amount
            + self.box_6a_ordinary_dividends.amount
            + self.box_7_royalties.amount
            + self.box_8_short_term_gain.amount
            + self.box_9a_long_term_gain.amount
            + self.box_10_section_1231.amount
        )
        for item in self.box_11_other_income:
            total += item.amount.amount
        return Money(total)

    @property
    def total_deductions(self) -> Money:
        """Total deductions."""
        total = self.box_12_section_179.amount
        for item in self.box_13_other_deductions:
            total += item.amount.amount
        return Money(total)

    @property
    def total_distributions(self) -> Money:
        """Total distributions received."""
        return Money(
            self.box_19a_cash_distributions.amount
            + self.box_19b_property_distributions.amount
        )

    @property
    def total_liabilities(self) -> Money:
        """Total share of partnership liabilities."""
        return Money(
            self.share_nonrecourse.amount
            + self.share_qualified_nonrecourse.amount
            + self.share_recourse.amount
        )


@dataclass
class K1ReconciliationItem:
    """A single reconciliation item mapping K-1 box to ledger."""

    k1_document_id: UUID
    k1_box_number: str
    k1_box_description: str
    k1_amount: Money
    id: UUID = field(default_factory=uuid4)

    # Ledger mapping
    ledger_account_id: UUID | None = None
    ledger_account_name: str | None = None
    ledger_amount: Money | None = None
    transaction_ids: list[UUID] = field(default_factory=list)

    # Reconciliation result
    difference: Money | None = None
    is_reconciled: bool = False
    adjustment_required: bool = False
    adjustment_journal_id: UUID | None = None

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def calculate_difference(self) -> Money:
        """Calculate the difference between K-1 and ledger amounts."""
        if self.ledger_amount is None:
            self.difference = self.k1_amount
        else:
            self.difference = Money(self.k1_amount.amount - self.ledger_amount.amount)
        return self.difference


@dataclass
class K1Reconciliation:
    """A complete K-1 reconciliation record."""

    k1_document_id: UUID
    entity_id: UUID
    tax_year: int
    id: UUID = field(default_factory=uuid4)
    status: ReconciliationStatus = ReconciliationStatus.PENDING

    # Reconciliation items
    items: list[K1ReconciliationItem] = field(default_factory=list)

    # Summary
    total_k1_income: Money = field(default_factory=lambda: Money(Decimal("0")))
    total_ledger_income: Money = field(default_factory=lambda: Money(Decimal("0")))
    total_difference: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Capital account reconciliation
    k1_capital_beginning: Money | None = None
    ledger_capital_beginning: Money | None = None
    k1_capital_ending: Money | None = None
    ledger_capital_ending: Money | None = None
    capital_difference: Money | None = None

    # Workflow
    started_by: UUID | None = None
    started_at: datetime | None = None
    completed_by: UUID | None = None
    completed_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @property
    def items_reconciled_count(self) -> int:
        """Number of reconciled items."""
        return sum(1 for item in self.items if item.is_reconciled)

    @property
    def items_with_differences_count(self) -> int:
        """Number of items with differences."""
        return sum(
            1 for item in self.items
            if item.difference and item.difference.amount != 0
        )

    @property
    def is_fully_reconciled(self) -> bool:
        """Whether all items are reconciled with no differences."""
        return all(
            item.is_reconciled and
            (item.difference is None or item.difference.amount == 0)
            for item in self.items
        )


@dataclass
class Section754Election:
    """Section 754 election and step-up tracking.

    When a partnership makes a 754 election, it must adjust the
    basis of partnership property when there's a transfer of
    partnership interest or distribution.
    """

    partnership_name: str
    partnership_ein: str
    entity_id: UUID  # Partner entity
    id: UUID = field(default_factory=uuid4)
    election_date: date | None = None
    is_active: bool = True

    # Step-up/step-down amounts by asset class
    section_743b_adjustments: list["Section743bAdjustment"] = field(default_factory=list)

    # Amortization tracking
    total_step_up: Money = field(default_factory=lambda: Money(Decimal("0")))
    total_amortized: Money = field(default_factory=lambda: Money(Decimal("0")))
    annual_amortization: Money = field(default_factory=lambda: Money(Decimal("0")))

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @property
    def remaining_basis(self) -> Money:
        """Remaining unamortized basis adjustment."""
        return Money(self.total_step_up.amount - self.total_amortized.amount)


@dataclass
class Section743bAdjustment:
    """A Section 743(b) basis adjustment for a specific asset."""

    section_754_election_id: UUID
    asset_description: str
    adjustment_amount: Money  # Positive = step-up, negative = step-down
    id: UUID = field(default_factory=uuid4)
    asset_category: str | None = None  # "capital", "ordinary", etc.
    useful_life_years: Decimal | None = None
    annual_amortization: Money | None = None
    amortization_start_date: date | None = None
    total_amortized: Money = field(default_factory=lambda: Money(Decimal("0")))

    created_at: datetime = field(default_factory=_utc_now)

    @property
    def remaining_adjustment(self) -> Money:
        """Remaining unamortized adjustment."""
        return Money(self.adjustment_amount.amount - self.total_amortized.amount)


@dataclass
class PartnerCapitalAccount:
    """Partner's capital account tracking (704(b) book and tax basis).

    Tracks both Section 704(b) book capital and tax basis capital
    to support complex partnership allocations.
    """

    entity_id: UUID
    partnership_name: str
    partnership_ein: str
    tax_year: int
    id: UUID = field(default_factory=uuid4)

    # Section 704(b) Book Capital
    book_capital_beginning: Money = field(default_factory=lambda: Money(Decimal("0")))
    book_contributions: Money = field(default_factory=lambda: Money(Decimal("0")))
    book_income_allocation: Money = field(default_factory=lambda: Money(Decimal("0")))
    book_distributions: Money = field(default_factory=lambda: Money(Decimal("0")))
    book_capital_ending: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Tax Basis Capital
    tax_capital_beginning: Money = field(default_factory=lambda: Money(Decimal("0")))
    tax_contributions: Money = field(default_factory=lambda: Money(Decimal("0")))
    tax_income_allocation: Money = field(default_factory=lambda: Money(Decimal("0")))
    tax_distributions: Money = field(default_factory=lambda: Money(Decimal("0")))
    tax_capital_ending: Money = field(default_factory=lambda: Money(Decimal("0")))

    # 704(c) Layer tracking (for contributed property)
    section_704c_built_in_gain: Money = field(default_factory=lambda: Money(Decimal("0")))
    section_704c_built_in_loss: Money = field(default_factory=lambda: Money(Decimal("0")))
    section_704c_method: str | None = None  # "traditional", "curative", "remedial"

    # At-risk amount (Section 465)
    at_risk_beginning: Money = field(default_factory=lambda: Money(Decimal("0")))
    at_risk_ending: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Passive activity basis
    passive_basis_beginning: Money = field(default_factory=lambda: Money(Decimal("0")))
    passive_basis_ending: Money = field(default_factory=lambda: Money(Decimal("0")))

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @property
    def book_tax_difference(self) -> Money:
        """Difference between book and tax capital."""
        return Money(self.book_capital_ending.amount - self.tax_capital_ending.amount)

    def calculate_ending_balances(self) -> None:
        """Calculate ending balances from components."""
        self.book_capital_ending = Money(
            self.book_capital_beginning.amount
            + self.book_contributions.amount
            + self.book_income_allocation.amount
            - self.book_distributions.amount
        )
        self.tax_capital_ending = Money(
            self.tax_capital_beginning.amount
            + self.tax_contributions.amount
            + self.tax_income_allocation.amount
            - self.tax_distributions.amount
        )
