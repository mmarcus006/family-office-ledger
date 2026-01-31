"""Domain models for private equity, venture capital, and alternative investments.

Provides comprehensive tracking for:
- Private fund investments with capital calls and distributions
- Cap table management with share classes and vesting
- Waterfall calculations for carried interest
- IRR and MOIC performance metrics
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Self
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import Money


def _utc_now() -> datetime:
    return datetime.now(UTC)


class FundType(str, Enum):
    """Type of private investment fund."""

    VENTURE_CAPITAL = "venture_capital"
    PRIVATE_EQUITY = "private_equity"
    GROWTH_EQUITY = "growth_equity"
    BUYOUT = "buyout"
    MEZZANINE = "mezzanine"
    REAL_ESTATE = "real_estate"
    HEDGE_FUND = "hedge_fund"
    FUND_OF_FUNDS = "fund_of_funds"
    DIRECT_INVESTMENT = "direct_investment"
    SPV = "spv"  # Special Purpose Vehicle


class FundStatus(str, Enum):
    """Status of a private fund investment."""

    COMMITTED = "committed"
    INVESTING = "investing"
    HARVESTING = "harvesting"
    LIQUIDATING = "liquidating"
    FULLY_LIQUIDATED = "fully_liquidated"


class CallType(str, Enum):
    """Type of capital call."""

    INVESTMENT = "investment"
    MANAGEMENT_FEE = "management_fee"
    FUND_EXPENSES = "fund_expenses"
    ORGANIZATIONAL = "organizational"


class DistributionType(str, Enum):
    """Type of distribution."""

    RETURN_OF_CAPITAL = "return_of_capital"
    REALIZED_GAIN = "realized_gain"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    RECALLABLE = "recallable"


class ShareClassType(str, Enum):
    """Type of share class in cap table."""

    COMMON = "common"
    PREFERRED = "preferred"
    PREFERRED_SERIES_A = "preferred_series_a"
    PREFERRED_SERIES_B = "preferred_series_b"
    PREFERRED_SERIES_C = "preferred_series_c"
    CONVERTIBLE_NOTE = "convertible_note"
    SAFE = "safe"  # Simple Agreement for Future Equity
    WARRANT = "warrant"
    OPTION = "option"


class VestingScheduleType(str, Enum):
    """Type of vesting schedule."""

    NONE = "none"
    CLIFF = "cliff"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class PrivateFund:
    """A private investment fund (PE, VC, etc.).

    Tracks commitments, calls, distributions, and calculates performance.
    """

    name: str
    fund_type: FundType
    entity_id: UUID  # The entity making the investment
    commitment: Money  # Total committed capital
    id: UUID = field(default_factory=uuid4)
    status: FundStatus = FundStatus.COMMITTED
    vintage_year: int | None = None
    fund_term_years: int = 10
    investment_period_years: int = 5
    management_fee_rate: Decimal = Decimal("0.02")  # 2% typical
    carried_interest_rate: Decimal = Decimal("0.20")  # 20% typical
    preferred_return_rate: Decimal = Decimal("0.08")  # 8% hurdle
    gp_name: str | None = None
    fund_manager: str | None = None
    investment_date: date | None = None
    expected_close_date: date | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    # Calculated/cached values (updated by service)
    total_called: Money = field(default_factory=lambda: Money(Decimal("0")))
    total_distributed: Money = field(default_factory=lambda: Money(Decimal("0")))
    current_nav: Money = field(default_factory=lambda: Money(Decimal("0")))

    @property
    def unfunded_commitment(self) -> Money:
        """Remaining capital that can be called (dry powder)."""
        return Money(self.commitment.amount - self.total_called.amount)

    @property
    def paid_in_capital(self) -> Money:
        """Total capital contributed (called minus recallable distributions)."""
        return self.total_called

    @property
    def total_value(self) -> Money:
        """Total value = NAV + Distributions."""
        return Money(self.current_nav.amount + self.total_distributed.amount)

    @property
    def tvpi(self) -> Decimal:
        """Total Value to Paid-In multiple (TVPI).

        TVPI = (NAV + Distributions) / Paid-In Capital
        """
        if self.total_called.amount == 0:
            return Decimal("0")
        return self.total_value.amount / self.total_called.amount

    @property
    def dpi(self) -> Decimal:
        """Distributions to Paid-In multiple (DPI).

        DPI = Distributions / Paid-In Capital
        """
        if self.total_called.amount == 0:
            return Decimal("0")
        return self.total_distributed.amount / self.total_called.amount

    @property
    def rvpi(self) -> Decimal:
        """Residual Value to Paid-In multiple (RVPI).

        RVPI = NAV / Paid-In Capital
        """
        if self.total_called.amount == 0:
            return Decimal("0")
        return self.current_nav.amount / self.total_called.amount

    @property
    def moic(self) -> Decimal:
        """Multiple on Invested Capital (same as TVPI)."""
        return self.tvpi


@dataclass
class CapitalCall:
    """A capital call from a private fund.

    Represents a request for the investor to contribute committed capital.
    """

    fund_id: UUID
    call_date: date
    due_date: date
    amount: Money
    id: UUID = field(default_factory=uuid4)
    call_type: CallType = CallType.INVESTMENT
    call_number: int | None = None  # Sequential call number
    purpose: str | None = None
    is_paid: bool = False
    paid_date: date | None = None
    transaction_id: UUID | None = None  # Link to journal entry
    created_at: datetime = field(default_factory=_utc_now)

    def mark_paid(self, paid_date: date, transaction_id: UUID | None = None) -> None:
        """Mark the capital call as paid."""
        self.is_paid = True
        self.paid_date = paid_date
        self.transaction_id = transaction_id


@dataclass
class Distribution:
    """A distribution from a private fund.

    Represents a return of capital or gains to the investor.
    """

    fund_id: UUID
    distribution_date: date
    amount: Money
    id: UUID = field(default_factory=uuid4)
    distribution_type: DistributionType = DistributionType.RETURN_OF_CAPITAL
    is_recallable: bool = False
    recallable_until: date | None = None
    source_company: str | None = None  # Company that generated the return
    realized_gain: Money | None = None
    cost_basis_returned: Money | None = None
    is_received: bool = False
    received_date: date | None = None
    transaction_id: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class ShareClass:
    """A share class definition for a cap table."""

    name: str
    share_type: ShareClassType
    id: UUID = field(default_factory=uuid4)
    authorized_shares: int = 0
    par_value: Decimal = Decimal("0.0001")
    liquidation_preference: Decimal = Decimal("1.0")  # 1x preference
    participation_cap: Decimal | None = None  # e.g., 3x cap
    is_participating: bool = False
    conversion_ratio: Decimal = Decimal("1.0")
    anti_dilution_type: str | None = None  # "broad_based", "narrow_based", "full_ratchet"
    dividend_rate: Decimal | None = None
    is_voting: bool = True
    votes_per_share: int = 1
    seniority: int = 0  # Higher = more senior in liquidation


@dataclass
class CapTableEntry:
    """An entry in a cap table representing ownership."""

    company_name: str
    entity_id: UUID  # The entity that owns the shares
    share_class_id: UUID
    shares: int
    id: UUID = field(default_factory=uuid4)
    cost_basis: Money = field(default_factory=lambda: Money(Decimal("0")))
    acquisition_date: date | None = None
    certificate_number: str | None = None
    is_qsbs_eligible: bool = False
    qsbs_qualification_date: date | None = None
    vesting_schedule: VestingScheduleType = VestingScheduleType.NONE
    vesting_start_date: date | None = None
    cliff_months: int = 0
    vesting_months: int = 0
    shares_vested: int = 0
    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def shares_unvested(self) -> int:
        """Number of unvested shares."""
        return self.shares - self.shares_vested

    @property
    def cost_per_share(self) -> Decimal:
        """Cost basis per share."""
        if self.shares == 0:
            return Decimal("0")
        return self.cost_basis.amount / self.shares

    def calculate_vested_shares(self, as_of_date: date) -> int:
        """Calculate vested shares as of a given date."""
        if self.vesting_schedule == VestingScheduleType.NONE:
            return self.shares

        if self.vesting_start_date is None:
            return 0

        months_elapsed = (
            (as_of_date.year - self.vesting_start_date.year) * 12
            + (as_of_date.month - self.vesting_start_date.month)
        )

        if months_elapsed < 0:
            return 0

        # Check cliff
        if months_elapsed < self.cliff_months:
            return 0

        if self.vesting_months == 0:
            return self.shares

        # Calculate vested portion
        vesting_fraction = min(months_elapsed / self.vesting_months, Decimal("1.0"))
        return int(self.shares * vesting_fraction)


@dataclass
class CapTable:
    """A complete cap table for a company."""

    company_name: str
    id: UUID = field(default_factory=uuid4)
    share_classes: list[ShareClass] = field(default_factory=list)
    entries: list[CapTableEntry] = field(default_factory=list)
    fully_diluted_shares: int = 0
    last_valuation: Money | None = None
    last_valuation_date: date | None = None
    option_pool_size: int = 0
    option_pool_available: int = 0
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def get_ownership_percentage(self, entity_id: UUID) -> Decimal:
        """Get ownership percentage for an entity."""
        if self.fully_diluted_shares == 0:
            return Decimal("0")

        entity_shares = sum(
            entry.shares for entry in self.entries if entry.entity_id == entity_id
        )
        return Decimal(entity_shares) / Decimal(self.fully_diluted_shares)

    def get_entity_value(self, entity_id: UUID) -> Money | None:
        """Get the value of an entity's holdings based on last valuation."""
        if self.last_valuation is None:
            return None

        ownership = self.get_ownership_percentage(entity_id)
        return Money(self.last_valuation.amount * ownership)


@dataclass
class WaterfallTier:
    """A tier in a waterfall distribution calculation."""

    name: str
    threshold: Money | None  # None for final tier
    lp_share: Decimal  # LP percentage (e.g., 0.80 for 80%)
    gp_share: Decimal  # GP percentage (e.g., 0.20 for 20%)


@dataclass
class WaterfallResult:
    """Result of a waterfall distribution calculation."""

    total_distributed: Money
    return_of_capital: Money
    preferred_return: Money
    gp_catchup: Money
    carried_interest: Money
    lp_proceeds: Money
    gp_proceeds: Money
    irr: Decimal | None = None
    moic: Decimal | None = None


def calculate_irr(
    cash_flows: list[tuple[date, Decimal]],
    guess: Decimal = Decimal("0.1"),
    max_iterations: int = 100,
    tolerance: Decimal = Decimal("0.0001"),
) -> Decimal | None:
    """Calculate Internal Rate of Return using Newton-Raphson method.

    Args:
        cash_flows: List of (date, amount) tuples. Negative = outflow, positive = inflow.
        guess: Initial IRR guess (default 10%)
        max_iterations: Maximum iterations for convergence
        tolerance: Convergence tolerance

    Returns:
        Annualized IRR as a decimal (0.15 = 15%), or None if doesn't converge
    """
    if not cash_flows or len(cash_flows) < 2:
        return None

    # Sort by date
    sorted_flows = sorted(cash_flows, key=lambda x: x[0])
    base_date = sorted_flows[0][0]

    # Convert dates to years from base
    flows_years = [
        ((d - base_date).days / 365.25, amount) for d, amount in sorted_flows
    ]

    rate = guess

    for _ in range(max_iterations):
        npv = Decimal("0")
        npv_derivative = Decimal("0")

        for years, amount in flows_years:
            if years == 0:
                npv += amount
            else:
                discount = (1 + rate) ** Decimal(str(-years))
                npv += amount * discount
                npv_derivative -= Decimal(str(years)) * amount * discount / (1 + rate)

        if abs(npv_derivative) < Decimal("0.0000001"):
            return None

        new_rate = rate - npv / npv_derivative

        if abs(new_rate - rate) < tolerance:
            return new_rate

        rate = new_rate

    return None  # Didn't converge


def calculate_moic(
    total_invested: Decimal, total_value: Decimal
) -> Decimal:
    """Calculate Multiple on Invested Capital.

    Args:
        total_invested: Total capital invested
        total_value: Current value + distributions

    Returns:
        MOIC multiple (e.g., 2.5 = 2.5x return)
    """
    if total_invested == 0:
        return Decimal("0")
    return total_value / total_invested


def calculate_waterfall(
    total_proceeds: Money,
    total_contributed: Money,
    preferred_return_rate: Decimal,
    carried_interest_rate: Decimal,
    investment_start_date: date,
    distribution_date: date,
    gp_catchup_rate: Decimal = Decimal("1.0"),  # 100% to GP until caught up
) -> WaterfallResult:
    """Calculate waterfall distribution for carried interest.

    Standard waterfall:
    1. Return of Capital - 100% to LPs until contributed capital returned
    2. Preferred Return - 100% to LPs until hurdle rate achieved
    3. GP Catch-up - 100% to GP until GP has received carried interest on all profits
    4. Carried Interest Split - Typically 80/20 LP/GP

    Args:
        total_proceeds: Total amount to distribute
        total_contributed: Total capital contributed by LPs
        preferred_return_rate: Annual hurdle rate (e.g., 0.08 for 8%)
        carried_interest_rate: GP carry percentage (e.g., 0.20 for 20%)
        investment_start_date: When capital was contributed
        distribution_date: When distribution occurs
        gp_catchup_rate: Percentage of profits to GP during catchup (typically 100%)

    Returns:
        WaterfallResult with breakdown of distribution
    """
    proceeds = total_proceeds.amount
    contributed = total_contributed.amount

    # Calculate years for preferred return
    years = Decimal(str((distribution_date - investment_start_date).days / 365.25))

    # Calculate preferred return amount (compound)
    pref_return_amount = contributed * ((1 + preferred_return_rate) ** years - 1)

    # Initialize tracking
    remaining = proceeds
    return_of_capital = Decimal("0")
    preferred_return = Decimal("0")
    gp_catchup = Decimal("0")
    carried_interest = Decimal("0")

    # Step 1: Return of Capital
    if remaining > 0:
        roc = min(remaining, contributed)
        return_of_capital = roc
        remaining -= roc

    # Step 2: Preferred Return
    if remaining > 0:
        pref = min(remaining, pref_return_amount)
        preferred_return = pref
        remaining -= pref

    # Step 3: GP Catch-up (GP gets 100% until they have their share of all profits so far)
    if remaining > 0:
        total_profit_so_far = return_of_capital + preferred_return + remaining - contributed
        if total_profit_so_far > 0:
            gp_target = total_profit_so_far * carried_interest_rate
            catchup_needed = gp_target  # GP needs to catch up to their share
            catchup = min(remaining, catchup_needed)
            gp_catchup = catchup
            remaining -= catchup

    # Step 4: Carried Interest Split (remaining split according to carry)
    if remaining > 0:
        carried_interest = remaining * carried_interest_rate
        remaining -= carried_interest

    # Calculate LP and GP totals
    lp_proceeds = return_of_capital + preferred_return + (proceeds - return_of_capital - preferred_return - gp_catchup - carried_interest)
    gp_proceeds = gp_catchup + carried_interest

    return WaterfallResult(
        total_distributed=total_proceeds,
        return_of_capital=Money(return_of_capital),
        preferred_return=Money(preferred_return),
        gp_catchup=Money(gp_catchup),
        carried_interest=Money(carried_interest),
        lp_proceeds=Money(lp_proceeds),
        gp_proceeds=Money(gp_proceeds),
    )
