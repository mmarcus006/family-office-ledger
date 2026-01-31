"""Cash flow projection service (Addepar Navigator-inspired).

Provides:
- Historical spending pattern analysis
- Scheduled transaction incorporation
- Capital call commitment tracking
- Tax payment estimation
- Liquidity runway calculation
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from family_office_ledger.domain.value_objects import Money
from family_office_ledger.logging_config import get_logger

logger = get_logger(__name__)


class ProjectionPeriod(str, Enum):
    """Projection time period."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class CashFlowCategory(str, Enum):
    """Categories for cash flow items."""

    # Inflows
    SALARY_INCOME = "salary_income"
    INVESTMENT_INCOME = "investment_income"
    DIVIDEND_INCOME = "dividend_income"
    INTEREST_INCOME = "interest_income"
    RENTAL_INCOME = "rental_income"
    BUSINESS_INCOME = "business_income"
    CAPITAL_GAIN = "capital_gain"
    DISTRIBUTION = "distribution"
    LOAN_PROCEEDS = "loan_proceeds"
    ASSET_SALE = "asset_sale"
    OTHER_INCOME = "other_income"

    # Outflows
    LIVING_EXPENSES = "living_expenses"
    MORTGAGE_PAYMENT = "mortgage_payment"
    PROPERTY_TAX = "property_tax"
    INSURANCE = "insurance"
    INVESTMENT_PURCHASE = "investment_purchase"
    CAPITAL_CALL = "capital_call"
    TAX_PAYMENT = "tax_payment"
    LOAN_PAYMENT = "loan_payment"
    CHARITABLE_GIVING = "charitable_giving"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    PROFESSIONAL_FEES = "professional_fees"
    OTHER_EXPENSE = "other_expense"


class ConfidenceLevel(str, Enum):
    """Confidence level for projections."""

    HIGH = "high"  # Scheduled/recurring
    MEDIUM = "medium"  # Based on patterns
    LOW = "low"  # Estimated
    SPECULATIVE = "speculative"


@dataclass
class CashFlowItem:
    """A single cash flow item (actual or projected)."""

    date: date
    amount: Money
    category: CashFlowCategory
    description: str
    is_inflow: bool
    id: UUID | None = None

    # Projection metadata
    is_projected: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    source: str | None = None  # "scheduled", "pattern", "manual"

    # Linking
    transaction_id: UUID | None = None
    scheduled_transaction_id: UUID | None = None
    capital_call_id: UUID | None = None

    # Entity/account
    entity_id: UUID | None = None
    account_id: UUID | None = None

    notes: str | None = None


@dataclass
class CashFlowSummary:
    """Summary of cash flows for a period."""

    period_start: date
    period_end: date
    period_label: str

    # Inflows
    total_inflows: Money = field(default_factory=lambda: Money(Decimal("0")))
    inflows_by_category: dict[CashFlowCategory, Money] = field(default_factory=dict)

    # Outflows
    total_outflows: Money = field(default_factory=lambda: Money(Decimal("0")))
    outflows_by_category: dict[CashFlowCategory, Money] = field(default_factory=dict)

    # Net
    net_cash_flow: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Balances
    opening_balance: Money = field(default_factory=lambda: Money(Decimal("0")))
    closing_balance: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Confidence
    projected_percentage: Decimal = Decimal("0")  # % of items that are projected

    def calculate_totals(self, items: list[CashFlowItem]) -> None:
        """Calculate totals from cash flow items."""
        inflows_by_cat: dict[CashFlowCategory, Decimal] = {}
        outflows_by_cat: dict[CashFlowCategory, Decimal] = {}
        total_inflows = Decimal("0")
        total_outflows = Decimal("0")
        projected_count = 0

        for item in items:
            if item.is_inflow:
                total_inflows += item.amount.amount
                inflows_by_cat[item.category] = (
                    inflows_by_cat.get(item.category, Decimal("0")) + item.amount.amount
                )
            else:
                total_outflows += item.amount.amount
                outflows_by_cat[item.category] = (
                    outflows_by_cat.get(item.category, Decimal("0")) + item.amount.amount
                )

            if item.is_projected:
                projected_count += 1

        self.total_inflows = Money(total_inflows)
        self.total_outflows = Money(total_outflows)
        self.net_cash_flow = Money(total_inflows - total_outflows)
        self.closing_balance = Money(self.opening_balance.amount + self.net_cash_flow.amount)

        self.inflows_by_category = {k: Money(v) for k, v in inflows_by_cat.items()}
        self.outflows_by_category = {k: Money(v) for k, v in outflows_by_cat.items()}

        if items:
            self.projected_percentage = Decimal(projected_count) / Decimal(len(items)) * 100


@dataclass
class SpendingPattern:
    """Detected spending pattern for projection."""

    category: CashFlowCategory
    description: str
    average_amount: Money
    frequency: ProjectionPeriod
    day_of_month: int | None = None  # For monthly patterns
    day_of_week: int | None = None  # For weekly patterns (0=Monday)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Pattern statistics
    occurrence_count: int = 0
    std_deviation: Decimal = Decimal("0")
    last_occurrence: date | None = None

    def project_next_occurrence(self, from_date: date) -> date:
        """Calculate the next expected occurrence."""
        if self.frequency == ProjectionPeriod.MONTHLY and self.day_of_month:
            # Next month on the same day
            if from_date.day >= self.day_of_month:
                # Move to next month
                if from_date.month == 12:
                    return date(from_date.year + 1, 1, self.day_of_month)
                else:
                    return date(from_date.year, from_date.month + 1, self.day_of_month)
            else:
                return date(from_date.year, from_date.month, self.day_of_month)

        elif self.frequency == ProjectionPeriod.WEEKLY and self.day_of_week is not None:
            days_ahead = self.day_of_week - from_date.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return from_date + timedelta(days=days_ahead)

        elif self.frequency == ProjectionPeriod.QUARTERLY:
            # Next quarter start
            quarter = (from_date.month - 1) // 3 + 1
            next_quarter = quarter + 1 if quarter < 4 else 1
            next_year = from_date.year if next_quarter > quarter else from_date.year + 1
            return date(next_year, (next_quarter - 1) * 3 + 1, 1)

        elif self.frequency == ProjectionPeriod.ANNUAL:
            return date(from_date.year + 1, from_date.month, from_date.day)

        else:
            # Daily - next day
            return from_date + timedelta(days=1)


@dataclass
class CapitalCallProjection:
    """Projected capital call for private investments."""

    fund_id: UUID
    fund_name: str
    expected_date: date
    expected_amount: Money
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    unfunded_commitment: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Based on fund stage/vintage
    probability: Decimal = Decimal("0.5")  # 50% default

    notes: str | None = None


@dataclass
class TaxPaymentProjection:
    """Projected tax payment."""

    due_date: date
    estimated_amount: Money
    tax_type: str  # "federal_estimated", "state_estimated", "property", etc.
    entity_id: UUID | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Calculation basis
    based_on_ytd_income: Money | None = None
    effective_rate: Decimal | None = None

    notes: str | None = None


@dataclass
class LiquidityAnalysis:
    """Liquidity runway analysis."""

    as_of_date: date
    current_liquid_assets: Money
    projected_monthly_burn: Money
    runway_months: Decimal

    # Breakdown
    cash_balances: Money = field(default_factory=lambda: Money(Decimal("0")))
    money_market_balances: Money = field(default_factory=lambda: Money(Decimal("0")))
    public_securities_value: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Upcoming obligations
    upcoming_capital_calls: Money = field(default_factory=lambda: Money(Decimal("0")))
    upcoming_tax_payments: Money = field(default_factory=lambda: Money(Decimal("0")))
    upcoming_loan_payments: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Risk levels
    minimum_cash_threshold: Money = field(default_factory=lambda: Money(Decimal("0")))
    is_below_threshold: bool = False
    months_until_threshold: Decimal | None = None


class CashFlowProjectionService:
    """Service for projecting future cash flows."""

    def __init__(
        self,
        repository: Any = None,
    ) -> None:
        self.repository = repository

    def project_cash_flows(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
        period: ProjectionPeriod = ProjectionPeriod.MONTHLY,
        include_patterns: bool = True,
        include_scheduled: bool = True,
        include_capital_calls: bool = True,
        include_tax_estimates: bool = True,
    ) -> list[CashFlowSummary]:
        """Project cash flows for a date range.

        Args:
            entity_ids: Entities to include (None for all)
            start_date: Projection start date
            end_date: Projection end date
            period: Aggregation period
            include_patterns: Include pattern-based projections
            include_scheduled: Include scheduled transactions
            include_capital_calls: Include capital call projections
            include_tax_estimates: Include tax payment estimates

        Returns:
            List of CashFlowSummary for each period
        """
        summaries: list[CashFlowSummary] = []
        items: list[CashFlowItem] = []

        # Get scheduled transactions
        if include_scheduled:
            scheduled_items = self._get_scheduled_transactions(
                entity_ids, start_date, end_date
            )
            items.extend(scheduled_items)

        # Get pattern-based projections
        if include_patterns:
            pattern_items = self._project_from_patterns(
                entity_ids, start_date, end_date
            )
            items.extend(pattern_items)

        # Get capital call projections
        if include_capital_calls:
            call_items = self._project_capital_calls(entity_ids, start_date, end_date)
            items.extend(call_items)

        # Get tax payment projections
        if include_tax_estimates:
            tax_items = self._project_tax_payments(entity_ids, start_date, end_date)
            items.extend(tax_items)

        # Group items by period
        periods = self._generate_periods(start_date, end_date, period)
        current_balance = self._get_current_cash_balance(entity_ids)

        for period_start, period_end, label in periods:
            period_items = [
                item for item in items if period_start <= item.date <= period_end
            ]

            summary = CashFlowSummary(
                period_start=period_start,
                period_end=period_end,
                period_label=label,
                opening_balance=current_balance,
            )
            summary.calculate_totals(period_items)
            current_balance = summary.closing_balance

            summaries.append(summary)

        logger.info(
            "cash_flow_projection_complete",
            periods=len(summaries),
            total_items=len(items),
        )

        return summaries

    def analyze_spending_patterns(
        self,
        entity_ids: list[UUID] | None,
        lookback_months: int = 12,
    ) -> list[SpendingPattern]:
        """Analyze historical transactions for spending patterns.

        Args:
            entity_ids: Entities to analyze
            lookback_months: Months of history to analyze

        Returns:
            List of detected spending patterns
        """
        patterns: list[SpendingPattern] = []

        # In full implementation, would:
        # 1. Fetch historical transactions
        # 2. Group by category and description
        # 3. Detect recurring patterns (same amount, regular timing)
        # 4. Calculate statistics (mean, std dev, frequency)

        # Placeholder patterns for illustration
        common_patterns = [
            SpendingPattern(
                category=CashFlowCategory.MORTGAGE_PAYMENT,
                description="Mortgage payment",
                average_amount=Money(Decimal("5000")),
                frequency=ProjectionPeriod.MONTHLY,
                day_of_month=1,
                confidence=ConfidenceLevel.HIGH,
            ),
            SpendingPattern(
                category=CashFlowCategory.INSURANCE,
                description="Insurance premiums",
                average_amount=Money(Decimal("2000")),
                frequency=ProjectionPeriod.MONTHLY,
                day_of_month=15,
                confidence=ConfidenceLevel.HIGH,
            ),
            SpendingPattern(
                category=CashFlowCategory.LIVING_EXPENSES,
                description="General living expenses",
                average_amount=Money(Decimal("8000")),
                frequency=ProjectionPeriod.MONTHLY,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]
        patterns.extend(common_patterns)

        logger.info(
            "spending_patterns_analyzed",
            patterns_detected=len(patterns),
            lookback_months=lookback_months,
        )

        return patterns

    def project_capital_calls(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> list[CapitalCallProjection]:
        """Project expected capital calls from private investments.

        Args:
            entity_ids: Entities to include
            start_date: Projection start
            end_date: Projection end

        Returns:
            List of capital call projections
        """
        projections: list[CapitalCallProjection] = []

        # In full implementation, would:
        # 1. Get all active private fund investments
        # 2. Calculate unfunded commitments
        # 3. Estimate call timing based on:
        #    - Fund vintage/stage
        #    - Historical call patterns
        #    - Investment period remaining

        logger.info(
            "capital_calls_projected",
            projections=len(projections),
            start_date=str(start_date),
            end_date=str(end_date),
        )

        return projections

    def estimate_tax_payments(
        self,
        entity_ids: list[UUID] | None,
        tax_year: int,
    ) -> list[TaxPaymentProjection]:
        """Estimate tax payments for the year.

        Args:
            entity_ids: Entities to include
            tax_year: Tax year to estimate

        Returns:
            List of tax payment projections
        """
        projections: list[TaxPaymentProjection] = []

        # Federal estimated tax payment dates
        federal_dates = [
            date(tax_year, 4, 15),
            date(tax_year, 6, 15),
            date(tax_year, 9, 15),
            date(tax_year + 1, 1, 15),
        ]

        # In full implementation, would:
        # 1. Calculate YTD taxable income
        # 2. Apply safe harbor rules (100% prior year or 110% if high income)
        # 3. Factor in withholding, credits
        # 4. Project by quarter

        for due_date in federal_dates:
            projections.append(
                TaxPaymentProjection(
                    due_date=due_date,
                    estimated_amount=Money(Decimal("25000")),  # Placeholder
                    tax_type="federal_estimated",
                    confidence=ConfidenceLevel.MEDIUM,
                )
            )

        logger.info(
            "tax_payments_estimated",
            projections=len(projections),
            tax_year=tax_year,
        )

        return projections

    def calculate_liquidity_runway(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
        minimum_cash_months: int = 6,
    ) -> LiquidityAnalysis:
        """Calculate liquidity runway analysis.

        Args:
            entity_ids: Entities to include
            as_of_date: Analysis date
            minimum_cash_months: Minimum months of cash to maintain

        Returns:
            LiquidityAnalysis with runway calculations
        """
        # In full implementation, would:
        # 1. Get current liquid asset balances
        # 2. Calculate average monthly burn rate
        # 3. Factor in upcoming obligations (capital calls, taxes)
        # 4. Calculate runway in months

        # Placeholder values
        liquid_assets = Money(Decimal("500000"))
        monthly_burn = Money(Decimal("25000"))
        runway = liquid_assets.amount / monthly_burn.amount if monthly_burn.amount > 0 else Decimal("999")

        analysis = LiquidityAnalysis(
            as_of_date=as_of_date,
            current_liquid_assets=liquid_assets,
            projected_monthly_burn=monthly_burn,
            runway_months=runway,
            cash_balances=Money(Decimal("200000")),
            money_market_balances=Money(Decimal("100000")),
            public_securities_value=Money(Decimal("200000")),
            minimum_cash_threshold=Money(monthly_burn.amount * minimum_cash_months),
        )

        analysis.is_below_threshold = (
            liquid_assets.amount < analysis.minimum_cash_threshold.amount
        )
        if not analysis.is_below_threshold and monthly_burn.amount > 0:
            excess = liquid_assets.amount - analysis.minimum_cash_threshold.amount
            analysis.months_until_threshold = excess / monthly_burn.amount

        logger.info(
            "liquidity_runway_calculated",
            liquid_assets=str(liquid_assets.amount),
            runway_months=str(runway),
        )

        return analysis

    def _get_scheduled_transactions(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> list[CashFlowItem]:
        """Get scheduled/recurring transactions as cash flow items."""
        items: list[CashFlowItem] = []
        # Would fetch from scheduled transactions repository
        return items

    def _project_from_patterns(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> list[CashFlowItem]:
        """Project cash flows from detected patterns."""
        items: list[CashFlowItem] = []

        patterns = self.analyze_spending_patterns(entity_ids)

        for pattern in patterns:
            current_date = pattern.project_next_occurrence(start_date)

            while current_date <= end_date:
                items.append(
                    CashFlowItem(
                        date=current_date,
                        amount=pattern.average_amount,
                        category=pattern.category,
                        description=pattern.description,
                        is_inflow=pattern.category in {
                            CashFlowCategory.SALARY_INCOME,
                            CashFlowCategory.INVESTMENT_INCOME,
                            CashFlowCategory.DIVIDEND_INCOME,
                            CashFlowCategory.INTEREST_INCOME,
                            CashFlowCategory.RENTAL_INCOME,
                            CashFlowCategory.BUSINESS_INCOME,
                            CashFlowCategory.DISTRIBUTION,
                            CashFlowCategory.OTHER_INCOME,
                        },
                        is_projected=True,
                        confidence=pattern.confidence,
                        source="pattern",
                    )
                )
                current_date = pattern.project_next_occurrence(
                    current_date + timedelta(days=1)
                )

        return items

    def _project_capital_calls(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> list[CashFlowItem]:
        """Convert capital call projections to cash flow items."""
        items: list[CashFlowItem] = []

        projections = self.project_capital_calls(entity_ids, start_date, end_date)

        for proj in projections:
            items.append(
                CashFlowItem(
                    date=proj.expected_date,
                    amount=proj.expected_amount,
                    category=CashFlowCategory.CAPITAL_CALL,
                    description=f"Capital call: {proj.fund_name}",
                    is_inflow=False,
                    is_projected=True,
                    confidence=proj.confidence,
                    source="capital_call",
                )
            )

        return items

    def _project_tax_payments(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> list[CashFlowItem]:
        """Convert tax payment projections to cash flow items."""
        items: list[CashFlowItem] = []

        # Get projections for relevant years
        years = set()
        current = start_date
        while current <= end_date:
            years.add(current.year)
            current = date(current.year + 1, 1, 1)

        for year in years:
            projections = self.estimate_tax_payments(entity_ids, year)
            for proj in projections:
                if start_date <= proj.due_date <= end_date:
                    items.append(
                        CashFlowItem(
                            date=proj.due_date,
                            amount=proj.estimated_amount,
                            category=CashFlowCategory.TAX_PAYMENT,
                            description=f"Tax payment: {proj.tax_type}",
                            is_inflow=False,
                            is_projected=True,
                            confidence=proj.confidence,
                            source="tax_estimate",
                            entity_id=proj.entity_id,
                        )
                    )

        return items

    def _generate_periods(
        self,
        start_date: date,
        end_date: date,
        period: ProjectionPeriod,
    ) -> list[tuple[date, date, str]]:
        """Generate period boundaries for aggregation."""
        periods: list[tuple[date, date, str]] = []
        current = start_date

        while current <= end_date:
            if period == ProjectionPeriod.MONTHLY:
                # End of month
                if current.month == 12:
                    period_end = date(current.year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(current.year, current.month + 1, 1) - timedelta(days=1)
                period_end = min(period_end, end_date)
                label = current.strftime("%b %Y")
                periods.append((current, period_end, label))
                current = period_end + timedelta(days=1)

            elif period == ProjectionPeriod.WEEKLY:
                period_end = min(current + timedelta(days=6), end_date)
                label = f"Week of {current.strftime('%m/%d')}"
                periods.append((current, period_end, label))
                current = period_end + timedelta(days=1)

            elif period == ProjectionPeriod.QUARTERLY:
                quarter = (current.month - 1) // 3 + 1
                if quarter == 4:
                    period_end = date(current.year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(current.year, quarter * 3 + 1, 1) - timedelta(days=1)
                period_end = min(period_end, end_date)
                label = f"Q{quarter} {current.year}"
                periods.append((current, period_end, label))
                current = period_end + timedelta(days=1)

            else:  # DAILY or ANNUAL
                if period == ProjectionPeriod.ANNUAL:
                    period_end = min(date(current.year, 12, 31), end_date)
                    label = str(current.year)
                else:
                    period_end = current
                    label = current.strftime("%m/%d/%Y")
                periods.append((current, period_end, label))
                current = period_end + timedelta(days=1)

        return periods

    def _get_current_cash_balance(self, entity_ids: list[UUID] | None) -> Money:
        """Get current total cash balance."""
        # Would fetch from accounts repository
        return Money(Decimal("100000"))  # Placeholder
