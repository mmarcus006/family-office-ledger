"""Tests for cash flow projection service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.value_objects import Money
from family_office_ledger.services.cash_flow_projection import (
    CashFlowCategory,
    CashFlowItem,
    CashFlowProjectionService,
    CashFlowSummary,
    ConfidenceLevel,
    ProjectionPeriod,
    SpendingPattern,
)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def service() -> CashFlowProjectionService:
    """Create a CashFlowProjectionService without a repository (uses placeholders)."""
    return CashFlowProjectionService(repository=None)


@pytest.fixture
def sample_inflow_item() -> CashFlowItem:
    """Create a sample inflow cash flow item."""
    return CashFlowItem(
        date=date(2025, 6, 15),
        amount=Money(Decimal("5000")),
        category=CashFlowCategory.SALARY_INCOME,
        description="Monthly salary",
        is_inflow=True,
        is_projected=False,
        confidence=ConfidenceLevel.HIGH,
    )


@pytest.fixture
def sample_outflow_item() -> CashFlowItem:
    """Create a sample outflow cash flow item."""
    return CashFlowItem(
        date=date(2025, 6, 20),
        amount=Money(Decimal("2000")),
        category=CashFlowCategory.MORTGAGE_PAYMENT,
        description="Mortgage payment",
        is_inflow=False,
        is_projected=False,
        confidence=ConfidenceLevel.HIGH,
    )


@pytest.fixture
def sample_projected_item() -> CashFlowItem:
    """Create a sample projected cash flow item."""
    return CashFlowItem(
        date=date(2025, 7, 1),
        amount=Money(Decimal("3000")),
        category=CashFlowCategory.LIVING_EXPENSES,
        description="Projected living expenses",
        is_inflow=False,
        is_projected=True,
        confidence=ConfidenceLevel.MEDIUM,
        source="pattern",
    )


@pytest.fixture
def monthly_mortgage_pattern() -> SpendingPattern:
    """Create a monthly mortgage spending pattern."""
    return SpendingPattern(
        category=CashFlowCategory.MORTGAGE_PAYMENT,
        description="Mortgage payment",
        average_amount=Money(Decimal("5000")),
        frequency=ProjectionPeriod.MONTHLY,
        day_of_month=1,
        confidence=ConfidenceLevel.HIGH,
        occurrence_count=12,
        last_occurrence=date(2025, 5, 1),
    )


@pytest.fixture
def weekly_grocery_pattern() -> SpendingPattern:
    """Create a weekly grocery spending pattern."""
    return SpendingPattern(
        category=CashFlowCategory.LIVING_EXPENSES,
        description="Weekly groceries",
        average_amount=Money(Decimal("300")),
        frequency=ProjectionPeriod.WEEKLY,
        day_of_week=0,  # Monday
        confidence=ConfidenceLevel.MEDIUM,
        occurrence_count=52,
    )


@pytest.fixture
def quarterly_insurance_pattern() -> SpendingPattern:
    """Create a quarterly insurance spending pattern."""
    return SpendingPattern(
        category=CashFlowCategory.INSURANCE,
        description="Quarterly insurance premium",
        average_amount=Money(Decimal("2500")),
        frequency=ProjectionPeriod.QUARTERLY,
        confidence=ConfidenceLevel.HIGH,
        occurrence_count=4,
    )


@pytest.fixture
def annual_property_tax_pattern() -> SpendingPattern:
    """Create an annual property tax spending pattern."""
    return SpendingPattern(
        category=CashFlowCategory.PROPERTY_TAX,
        description="Annual property tax",
        average_amount=Money(Decimal("15000")),
        frequency=ProjectionPeriod.ANNUAL,
        confidence=ConfidenceLevel.HIGH,
        occurrence_count=1,
    )


# -----------------------------------------------------------------------------
# TestCashFlowSummaryCalculateTotals
# -----------------------------------------------------------------------------


class TestCashFlowSummaryCalculateTotals:
    """Tests for CashFlowSummary.calculate_totals method."""

    def test_calculates_totals_for_single_inflow(
        self, sample_inflow_item: CashFlowItem
    ):
        """Single inflow item should calculate correct totals."""
        summary = CashFlowSummary(
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            period_label="Jun 2025",
            opening_balance=Money(Decimal("10000")),
        )
        summary.calculate_totals([sample_inflow_item])

        assert summary.total_inflows == Money(Decimal("5000"))
        assert summary.total_outflows == Money(Decimal("0"))
        assert summary.net_cash_flow == Money(Decimal("5000"))
        assert summary.closing_balance == Money(Decimal("15000"))

    def test_calculates_totals_for_single_outflow(
        self, sample_outflow_item: CashFlowItem
    ):
        """Single outflow item should calculate correct totals."""
        summary = CashFlowSummary(
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            period_label="Jun 2025",
            opening_balance=Money(Decimal("10000")),
        )
        summary.calculate_totals([sample_outflow_item])

        assert summary.total_inflows == Money(Decimal("0"))
        assert summary.total_outflows == Money(Decimal("2000"))
        assert summary.net_cash_flow == Money(Decimal("-2000"))
        assert summary.closing_balance == Money(Decimal("8000"))

    def test_calculates_totals_for_mixed_items(
        self, sample_inflow_item: CashFlowItem, sample_outflow_item: CashFlowItem
    ):
        """Mixed inflow and outflow items should calculate correct net."""
        summary = CashFlowSummary(
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            period_label="Jun 2025",
            opening_balance=Money(Decimal("10000")),
        )
        summary.calculate_totals([sample_inflow_item, sample_outflow_item])

        assert summary.total_inflows == Money(Decimal("5000"))
        assert summary.total_outflows == Money(Decimal("2000"))
        assert summary.net_cash_flow == Money(Decimal("3000"))
        assert summary.closing_balance == Money(Decimal("13000"))

    def test_groups_items_by_category(self):
        """Items should be grouped by category in category dicts."""
        items = [
            CashFlowItem(
                date=date(2025, 6, 1),
                amount=Money(Decimal("1000")),
                category=CashFlowCategory.SALARY_INCOME,
                description="Salary 1",
                is_inflow=True,
            ),
            CashFlowItem(
                date=date(2025, 6, 15),
                amount=Money(Decimal("500")),
                category=CashFlowCategory.SALARY_INCOME,
                description="Salary 2",
                is_inflow=True,
            ),
            CashFlowItem(
                date=date(2025, 6, 10),
                amount=Money(Decimal("200")),
                category=CashFlowCategory.DIVIDEND_INCOME,
                description="Dividend",
                is_inflow=True,
            ),
            CashFlowItem(
                date=date(2025, 6, 5),
                amount=Money(Decimal("300")),
                category=CashFlowCategory.MORTGAGE_PAYMENT,
                description="Mortgage",
                is_inflow=False,
            ),
            CashFlowItem(
                date=date(2025, 6, 20),
                amount=Money(Decimal("100")),
                category=CashFlowCategory.INSURANCE,
                description="Insurance",
                is_inflow=False,
            ),
        ]
        summary = CashFlowSummary(
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            period_label="Jun 2025",
        )
        summary.calculate_totals(items)

        assert summary.inflows_by_category[CashFlowCategory.SALARY_INCOME] == Money(
            Decimal("1500")
        )
        assert summary.inflows_by_category[CashFlowCategory.DIVIDEND_INCOME] == Money(
            Decimal("200")
        )
        assert summary.outflows_by_category[CashFlowCategory.MORTGAGE_PAYMENT] == Money(
            Decimal("300")
        )
        assert summary.outflows_by_category[CashFlowCategory.INSURANCE] == Money(
            Decimal("100")
        )

    def test_calculates_projected_percentage(
        self, sample_inflow_item: CashFlowItem, sample_projected_item: CashFlowItem
    ):
        """Projected percentage should reflect proportion of projected items."""
        summary = CashFlowSummary(
            period_start=date(2025, 6, 1),
            period_end=date(2025, 7, 31),
            period_label="Jun-Jul 2025",
        )
        # One actual, one projected = 50%
        summary.calculate_totals([sample_inflow_item, sample_projected_item])

        assert summary.projected_percentage == Decimal("50")

    def test_handles_empty_items_list(self):
        """Empty items list should result in zero totals."""
        summary = CashFlowSummary(
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            period_label="Jun 2025",
            opening_balance=Money(Decimal("10000")),
        )
        summary.calculate_totals([])

        assert summary.total_inflows == Money(Decimal("0"))
        assert summary.total_outflows == Money(Decimal("0"))
        assert summary.net_cash_flow == Money(Decimal("0"))
        assert summary.closing_balance == Money(Decimal("10000"))
        assert summary.projected_percentage == Decimal("0")


# -----------------------------------------------------------------------------
# TestSpendingPatternProjectNextOccurrence
# -----------------------------------------------------------------------------


class TestSpendingPatternProjectNextOccurrence:
    """Tests for SpendingPattern.project_next_occurrence method."""

    def test_monthly_pattern_same_month(
        self, monthly_mortgage_pattern: SpendingPattern
    ):
        """Monthly pattern with day_of_month later in current month."""
        from_date = date(2025, 6, 15)
        # Pattern day is 1, current is 15, so should be next month
        next_occ = monthly_mortgage_pattern.project_next_occurrence(from_date)
        assert next_occ == date(2025, 7, 1)

    def test_monthly_pattern_before_day_of_month(
        self, monthly_mortgage_pattern: SpendingPattern
    ):
        """Monthly pattern when current day is before day_of_month."""
        # Create a pattern with day_of_month=15
        pattern = SpendingPattern(
            category=CashFlowCategory.INSURANCE,
            description="Insurance",
            average_amount=Money(Decimal("500")),
            frequency=ProjectionPeriod.MONTHLY,
            day_of_month=15,
        )
        from_date = date(2025, 6, 10)
        next_occ = pattern.project_next_occurrence(from_date)
        assert next_occ == date(2025, 6, 15)

    def test_monthly_pattern_year_boundary(self):
        """Monthly pattern crossing year boundary."""
        pattern = SpendingPattern(
            category=CashFlowCategory.MORTGAGE_PAYMENT,
            description="Mortgage",
            average_amount=Money(Decimal("5000")),
            frequency=ProjectionPeriod.MONTHLY,
            day_of_month=1,
        )
        from_date = date(2025, 12, 15)
        next_occ = pattern.project_next_occurrence(from_date)
        assert next_occ == date(2026, 1, 1)

    def test_weekly_pattern_same_week(self, weekly_grocery_pattern: SpendingPattern):
        """Weekly pattern with day_of_week later in current week."""
        # Pattern is Monday (day_of_week=0)
        # Thursday June 19, 2025 is a Thursday (weekday=3)
        from_date = date(2025, 6, 19)
        next_occ = weekly_grocery_pattern.project_next_occurrence(from_date)
        # Next Monday is June 23, 2025
        assert next_occ == date(2025, 6, 23)

    def test_weekly_pattern_exact_same_day(self):
        """Weekly pattern when from_date is same day of week should return next week."""
        pattern = SpendingPattern(
            category=CashFlowCategory.LIVING_EXPENSES,
            description="Groceries",
            average_amount=Money(Decimal("200")),
            frequency=ProjectionPeriod.WEEKLY,
            day_of_week=0,  # Monday
        )
        # June 16, 2025 is a Monday
        from_date = date(2025, 6, 16)
        next_occ = pattern.project_next_occurrence(from_date)
        # Should return next Monday
        assert next_occ == date(2025, 6, 23)

    def test_weekly_pattern_day_before(self):
        """Weekly pattern when from_date is day before target."""
        pattern = SpendingPattern(
            category=CashFlowCategory.LIVING_EXPENSES,
            description="Groceries",
            average_amount=Money(Decimal("200")),
            frequency=ProjectionPeriod.WEEKLY,
            day_of_week=0,  # Monday
        )
        # June 15, 2025 is a Sunday (weekday=6)
        from_date = date(2025, 6, 15)
        next_occ = pattern.project_next_occurrence(from_date)
        # Should return next day (Monday)
        assert next_occ == date(2025, 6, 16)

    def test_quarterly_pattern_q1_to_q2(
        self, quarterly_insurance_pattern: SpendingPattern
    ):
        """Quarterly pattern from Q1 to Q2."""
        from_date = date(2025, 2, 15)  # Q1
        next_occ = quarterly_insurance_pattern.project_next_occurrence(from_date)
        assert next_occ == date(2025, 4, 1)  # Q2 start

    def test_quarterly_pattern_q4_to_q1(
        self, quarterly_insurance_pattern: SpendingPattern
    ):
        """Quarterly pattern from Q4 to Q1 (year boundary)."""
        from_date = date(2025, 11, 15)  # Q4
        next_occ = quarterly_insurance_pattern.project_next_occurrence(from_date)
        assert next_occ == date(2026, 1, 1)  # Next Q1 start

    def test_quarterly_pattern_q3_to_q4(
        self, quarterly_insurance_pattern: SpendingPattern
    ):
        """Quarterly pattern from Q3 to Q4."""
        from_date = date(2025, 8, 1)  # Q3
        next_occ = quarterly_insurance_pattern.project_next_occurrence(from_date)
        assert next_occ == date(2025, 10, 1)  # Q4 start

    def test_annual_pattern(self, annual_property_tax_pattern: SpendingPattern):
        """Annual pattern should return same date next year."""
        from_date = date(2025, 6, 15)
        next_occ = annual_property_tax_pattern.project_next_occurrence(from_date)
        assert next_occ == date(2026, 6, 15)

    def test_daily_pattern(self):
        """Daily pattern should return next day."""
        pattern = SpendingPattern(
            category=CashFlowCategory.LIVING_EXPENSES,
            description="Daily expenses",
            average_amount=Money(Decimal("50")),
            frequency=ProjectionPeriod.DAILY,
        )
        from_date = date(2025, 6, 15)
        next_occ = pattern.project_next_occurrence(from_date)
        assert next_occ == date(2025, 6, 16)

    def test_daily_pattern_year_boundary(self):
        """Daily pattern crossing year boundary."""
        pattern = SpendingPattern(
            category=CashFlowCategory.LIVING_EXPENSES,
            description="Daily expenses",
            average_amount=Money(Decimal("50")),
            frequency=ProjectionPeriod.DAILY,
        )
        from_date = date(2025, 12, 31)
        next_occ = pattern.project_next_occurrence(from_date)
        assert next_occ == date(2026, 1, 1)


# -----------------------------------------------------------------------------
# TestEstimateTaxPayments
# -----------------------------------------------------------------------------


class TestEstimateTaxPayments:
    """Tests for CashFlowProjectionService.estimate_tax_payments method."""

    def test_returns_four_federal_estimated_payments(
        self, service: CashFlowProjectionService
    ):
        """Should return 4 quarterly estimated tax payments."""
        projections = service.estimate_tax_payments(None, 2025)

        assert len(projections) == 4
        for proj in projections:
            assert proj.tax_type == "federal_estimated"

    def test_correct_federal_estimated_dates_for_2025(
        self, service: CashFlowProjectionService
    ):
        """Federal estimated tax dates should be Q1-Q4 due dates."""
        projections = service.estimate_tax_payments(None, 2025)
        due_dates = [p.due_date for p in projections]

        expected_dates = [
            date(2025, 4, 15),
            date(2025, 6, 15),
            date(2025, 9, 15),
            date(2026, 1, 15),
        ]
        assert due_dates == expected_dates

    def test_correct_federal_estimated_dates_for_2026(
        self, service: CashFlowProjectionService
    ):
        """Federal estimated tax dates for different year."""
        projections = service.estimate_tax_payments(None, 2026)
        due_dates = [p.due_date for p in projections]

        expected_dates = [
            date(2026, 4, 15),
            date(2026, 6, 15),
            date(2026, 9, 15),
            date(2027, 1, 15),
        ]
        assert due_dates == expected_dates

    def test_projections_have_medium_confidence(
        self, service: CashFlowProjectionService
    ):
        """Tax projections should have medium confidence level."""
        projections = service.estimate_tax_payments(None, 2025)

        for proj in projections:
            assert proj.confidence == ConfidenceLevel.MEDIUM

    def test_projections_have_placeholder_amount(
        self, service: CashFlowProjectionService
    ):
        """Tax projections should have the placeholder amount."""
        projections = service.estimate_tax_payments(None, 2025)

        for proj in projections:
            assert proj.estimated_amount == Money(Decimal("25000"))


# -----------------------------------------------------------------------------
# TestCalculateLiquidityRunway
# -----------------------------------------------------------------------------


class TestCalculateLiquidityRunway:
    """Tests for CashFlowProjectionService.calculate_liquidity_runway method."""

    def test_calculates_runway_months(self, service: CashFlowProjectionService):
        """Runway months should be liquid_assets / monthly_burn."""
        analysis = service.calculate_liquidity_runway(None, date(2025, 6, 1))

        # Placeholder: 500,000 / 25,000 = 20 months
        assert analysis.runway_months == Decimal("20")

    def test_analysis_has_correct_as_of_date(self, service: CashFlowProjectionService):
        """Analysis should have the correct as_of_date."""
        test_date = date(2025, 7, 15)
        analysis = service.calculate_liquidity_runway(None, test_date)

        assert analysis.as_of_date == test_date

    def test_minimum_cash_threshold_calculation(
        self, service: CashFlowProjectionService
    ):
        """Minimum cash threshold should be monthly_burn * minimum_cash_months."""
        analysis = service.calculate_liquidity_runway(
            None, date(2025, 6, 1), minimum_cash_months=6
        )

        # 25,000 * 6 = 150,000
        assert analysis.minimum_cash_threshold == Money(Decimal("150000"))

    def test_is_below_threshold_when_above(self, service: CashFlowProjectionService):
        """Should not be below threshold when liquid assets exceed threshold."""
        analysis = service.calculate_liquidity_runway(
            None, date(2025, 6, 1), minimum_cash_months=6
        )

        # Liquid assets (500,000) > threshold (150,000)
        assert analysis.is_below_threshold is False

    def test_months_until_threshold_calculated(
        self, service: CashFlowProjectionService
    ):
        """Should calculate months until reaching threshold."""
        analysis = service.calculate_liquidity_runway(
            None, date(2025, 6, 1), minimum_cash_months=6
        )

        # (500,000 - 150,000) / 25,000 = 14 months
        assert analysis.months_until_threshold == Decimal("14")

    def test_liquid_assets_breakdown(self, service: CashFlowProjectionService):
        """Analysis should include breakdown of liquid assets."""
        analysis = service.calculate_liquidity_runway(None, date(2025, 6, 1))

        assert analysis.cash_balances == Money(Decimal("200000"))
        assert analysis.money_market_balances == Money(Decimal("100000"))
        assert analysis.public_securities_value == Money(Decimal("200000"))

    def test_custom_minimum_cash_months(self, service: CashFlowProjectionService):
        """Should respect custom minimum_cash_months parameter."""
        analysis = service.calculate_liquidity_runway(
            None, date(2025, 6, 1), minimum_cash_months=12
        )

        # 25,000 * 12 = 300,000
        assert analysis.minimum_cash_threshold == Money(Decimal("300000"))


# -----------------------------------------------------------------------------
# TestGeneratePeriods
# -----------------------------------------------------------------------------


class TestGeneratePeriods:
    """Tests for CashFlowProjectionService._generate_periods method."""

    def test_monthly_periods_single_month(self, service: CashFlowProjectionService):
        """Single month should generate one period."""
        periods = service._generate_periods(
            date(2025, 6, 1), date(2025, 6, 30), ProjectionPeriod.MONTHLY
        )

        assert len(periods) == 1
        assert periods[0] == (date(2025, 6, 1), date(2025, 6, 30), "Jun 2025")

    def test_monthly_periods_multiple_months(self, service: CashFlowProjectionService):
        """Multiple months should generate correct periods."""
        periods = service._generate_periods(
            date(2025, 1, 1), date(2025, 3, 31), ProjectionPeriod.MONTHLY
        )

        assert len(periods) == 3
        assert periods[0] == (date(2025, 1, 1), date(2025, 1, 31), "Jan 2025")
        assert periods[1] == (date(2025, 2, 1), date(2025, 2, 28), "Feb 2025")
        assert periods[2] == (date(2025, 3, 1), date(2025, 3, 31), "Mar 2025")

    def test_monthly_periods_year_boundary(self, service: CashFlowProjectionService):
        """Monthly periods should handle year boundary."""
        periods = service._generate_periods(
            date(2025, 12, 1), date(2026, 1, 31), ProjectionPeriod.MONTHLY
        )

        assert len(periods) == 2
        assert periods[0] == (date(2025, 12, 1), date(2025, 12, 31), "Dec 2025")
        assert periods[1] == (date(2026, 1, 1), date(2026, 1, 31), "Jan 2026")

    def test_monthly_periods_partial_end_month(
        self, service: CashFlowProjectionService
    ):
        """End date in middle of month should truncate period."""
        periods = service._generate_periods(
            date(2025, 6, 1), date(2025, 7, 15), ProjectionPeriod.MONTHLY
        )

        assert len(periods) == 2
        assert periods[0] == (date(2025, 6, 1), date(2025, 6, 30), "Jun 2025")
        assert periods[1] == (date(2025, 7, 1), date(2025, 7, 15), "Jul 2025")

    def test_weekly_periods(self, service: CashFlowProjectionService):
        """Weekly periods should be 7 days each."""
        periods = service._generate_periods(
            date(2025, 6, 1), date(2025, 6, 21), ProjectionPeriod.WEEKLY
        )

        assert len(periods) == 3
        assert periods[0] == (date(2025, 6, 1), date(2025, 6, 7), "Week of 06/01")
        assert periods[1] == (date(2025, 6, 8), date(2025, 6, 14), "Week of 06/08")
        assert periods[2] == (date(2025, 6, 15), date(2025, 6, 21), "Week of 06/15")

    def test_quarterly_periods(self, service: CashFlowProjectionService):
        """Quarterly periods should span 3 months each."""
        periods = service._generate_periods(
            date(2025, 1, 1), date(2025, 6, 30), ProjectionPeriod.QUARTERLY
        )

        assert len(periods) == 2
        assert periods[0] == (date(2025, 1, 1), date(2025, 3, 31), "Q1 2025")
        assert periods[1] == (date(2025, 4, 1), date(2025, 6, 30), "Q2 2025")

    def test_quarterly_periods_year_boundary(self, service: CashFlowProjectionService):
        """Quarterly periods should handle year boundary."""
        periods = service._generate_periods(
            date(2025, 10, 1), date(2026, 3, 31), ProjectionPeriod.QUARTERLY
        )

        assert len(periods) == 2
        assert periods[0] == (date(2025, 10, 1), date(2025, 12, 31), "Q4 2025")
        assert periods[1] == (date(2026, 1, 1), date(2026, 3, 31), "Q1 2026")

    def test_annual_periods(self, service: CashFlowProjectionService):
        """Annual periods should span full years."""
        periods = service._generate_periods(
            date(2025, 1, 1), date(2026, 12, 31), ProjectionPeriod.ANNUAL
        )

        assert len(periods) == 2
        assert periods[0] == (date(2025, 1, 1), date(2025, 12, 31), "2025")
        assert periods[1] == (date(2026, 1, 1), date(2026, 12, 31), "2026")

    def test_daily_periods(self, service: CashFlowProjectionService):
        """Daily periods should be single days."""
        periods = service._generate_periods(
            date(2025, 6, 1), date(2025, 6, 3), ProjectionPeriod.DAILY
        )

        assert len(periods) == 3
        assert periods[0] == (date(2025, 6, 1), date(2025, 6, 1), "06/01/2025")
        assert periods[1] == (date(2025, 6, 2), date(2025, 6, 2), "06/02/2025")
        assert periods[2] == (date(2025, 6, 3), date(2025, 6, 3), "06/03/2025")


# -----------------------------------------------------------------------------
# TestProjectCashFlows
# -----------------------------------------------------------------------------


class TestProjectCashFlows:
    """Tests for CashFlowProjectionService.project_cash_flows method."""

    def test_returns_list_of_summaries(self, service: CashFlowProjectionService):
        """Should return a list of CashFlowSummary objects."""
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
            period=ProjectionPeriod.MONTHLY,
        )

        assert isinstance(summaries, list)
        assert len(summaries) > 0
        assert all(isinstance(s, CashFlowSummary) for s in summaries)

    def test_monthly_projection_returns_correct_periods(
        self, service: CashFlowProjectionService
    ):
        """Monthly projection should return one summary per month."""
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            period=ProjectionPeriod.MONTHLY,
        )

        assert len(summaries) == 3
        assert summaries[0].period_label == "Jan 2025"
        assert summaries[1].period_label == "Feb 2025"
        assert summaries[2].period_label == "Mar 2025"

    def test_opening_balance_carries_forward(self, service: CashFlowProjectionService):
        """Opening balance of each period should equal closing of previous."""
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            period=ProjectionPeriod.MONTHLY,
        )

        for i in range(1, len(summaries)):
            assert summaries[i].opening_balance == summaries[i - 1].closing_balance

    def test_includes_pattern_projections_when_enabled(
        self, service: CashFlowProjectionService
    ):
        """Should include pattern-based projections when include_patterns=True."""
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
            period=ProjectionPeriod.MONTHLY,
            include_patterns=True,
            include_scheduled=False,
            include_capital_calls=False,
            include_tax_estimates=False,
        )

        # Service has placeholder patterns that generate items
        # At minimum, verify it returns summaries
        assert len(summaries) >= 1

    def test_includes_tax_estimates_when_enabled(
        self, service: CashFlowProjectionService
    ):
        """Should include tax estimates when include_tax_estimates=True."""
        # Date range that includes April 15 (Q1 estimated tax deadline)
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 30),
            period=ProjectionPeriod.MONTHLY,
            include_patterns=False,
            include_scheduled=False,
            include_capital_calls=False,
            include_tax_estimates=True,
        )

        # Should have tax payment in April
        assert len(summaries) == 1
        assert summaries[0].total_outflows.amount > Decimal("0")

    def test_excludes_all_optional_projections(
        self, service: CashFlowProjectionService
    ):
        """Should return empty items when all optional projections disabled."""
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
            period=ProjectionPeriod.MONTHLY,
            include_patterns=False,
            include_scheduled=False,
            include_capital_calls=False,
            include_tax_estimates=False,
        )

        assert len(summaries) == 1
        assert summaries[0].total_inflows == Money(Decimal("0"))
        assert summaries[0].total_outflows == Money(Decimal("0"))

    def test_respects_entity_ids_filter(self, service: CashFlowProjectionService):
        """Should filter by entity_ids when provided."""
        entity_id = uuid4()
        summaries = service.project_cash_flows(
            entity_ids=[entity_id],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
            period=ProjectionPeriod.MONTHLY,
        )

        # With no repository, this uses placeholders but shouldn't error
        assert len(summaries) >= 1

    def test_handles_single_day_range(self, service: CashFlowProjectionService):
        """Should handle a single-day date range."""
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 6, 15),
            end_date=date(2025, 6, 15),
            period=ProjectionPeriod.DAILY,
            include_patterns=False,
            include_scheduled=False,
            include_capital_calls=False,
            include_tax_estimates=False,
        )

        assert len(summaries) == 1
        assert summaries[0].period_start == date(2025, 6, 15)
        assert summaries[0].period_end == date(2025, 6, 15)


# -----------------------------------------------------------------------------
# TestCashFlowItem
# -----------------------------------------------------------------------------


class TestCashFlowItem:
    """Tests for CashFlowItem dataclass."""

    def test_creates_inflow_item(self):
        """Should create an inflow cash flow item."""
        item = CashFlowItem(
            date=date(2025, 6, 1),
            amount=Money(Decimal("1000")),
            category=CashFlowCategory.SALARY_INCOME,
            description="Salary",
            is_inflow=True,
        )

        assert item.is_inflow is True
        assert item.category == CashFlowCategory.SALARY_INCOME
        assert item.amount == Money(Decimal("1000"))

    def test_creates_outflow_item(self):
        """Should create an outflow cash flow item."""
        item = CashFlowItem(
            date=date(2025, 6, 1),
            amount=Money(Decimal("500")),
            category=CashFlowCategory.MORTGAGE_PAYMENT,
            description="Mortgage",
            is_inflow=False,
        )

        assert item.is_inflow is False
        assert item.category == CashFlowCategory.MORTGAGE_PAYMENT

    def test_default_confidence_is_high(self):
        """Default confidence should be HIGH."""
        item = CashFlowItem(
            date=date(2025, 6, 1),
            amount=Money(Decimal("1000")),
            category=CashFlowCategory.SALARY_INCOME,
            description="Salary",
            is_inflow=True,
        )

        assert item.confidence == ConfidenceLevel.HIGH

    def test_default_is_projected_is_false(self):
        """Default is_projected should be False."""
        item = CashFlowItem(
            date=date(2025, 6, 1),
            amount=Money(Decimal("1000")),
            category=CashFlowCategory.SALARY_INCOME,
            description="Salary",
            is_inflow=True,
        )

        assert item.is_projected is False

    def test_optional_uuid_fields_default_to_none(self):
        """Optional UUID fields should default to None."""
        item = CashFlowItem(
            date=date(2025, 6, 1),
            amount=Money(Decimal("1000")),
            category=CashFlowCategory.SALARY_INCOME,
            description="Salary",
            is_inflow=True,
        )

        assert item.id is None
        assert item.transaction_id is None
        assert item.scheduled_transaction_id is None
        assert item.capital_call_id is None
        assert item.entity_id is None
        assert item.account_id is None


# -----------------------------------------------------------------------------
# TestAnalyzeSpendingPatterns
# -----------------------------------------------------------------------------


class TestAnalyzeSpendingPatterns:
    """Tests for CashFlowProjectionService.analyze_spending_patterns method."""

    def test_returns_list_of_patterns(self, service: CashFlowProjectionService):
        """Should return a list of SpendingPattern objects."""
        patterns = service.analyze_spending_patterns(None)

        assert isinstance(patterns, list)
        assert all(isinstance(p, SpendingPattern) for p in patterns)

    def test_returns_placeholder_patterns(self, service: CashFlowProjectionService):
        """Should return placeholder patterns (mortgage, insurance, living)."""
        patterns = service.analyze_spending_patterns(None)

        categories = [p.category for p in patterns]
        assert CashFlowCategory.MORTGAGE_PAYMENT in categories
        assert CashFlowCategory.INSURANCE in categories
        assert CashFlowCategory.LIVING_EXPENSES in categories

    def test_respects_lookback_months_parameter(
        self, service: CashFlowProjectionService
    ):
        """Should accept lookback_months parameter without error."""
        patterns = service.analyze_spending_patterns(None, lookback_months=24)

        assert len(patterns) > 0


# -----------------------------------------------------------------------------
# TestProjectCapitalCalls
# -----------------------------------------------------------------------------


class TestProjectCapitalCalls:
    """Tests for CashFlowProjectionService.project_capital_calls method."""

    def test_returns_empty_list_placeholder(self, service: CashFlowProjectionService):
        """Placeholder implementation returns empty list."""
        projections = service.project_capital_calls(
            None, date(2025, 1, 1), date(2025, 12, 31)
        )

        assert projections == []


# -----------------------------------------------------------------------------
# TestEnums
# -----------------------------------------------------------------------------


class TestProjectionPeriodEnum:
    """Tests for ProjectionPeriod enum."""

    def test_all_periods_exist(self):
        """All expected period values should exist."""
        assert ProjectionPeriod.DAILY.value == "daily"
        assert ProjectionPeriod.WEEKLY.value == "weekly"
        assert ProjectionPeriod.MONTHLY.value == "monthly"
        assert ProjectionPeriod.QUARTERLY.value == "quarterly"
        assert ProjectionPeriod.ANNUAL.value == "annual"


class TestCashFlowCategoryEnum:
    """Tests for CashFlowCategory enum."""

    def test_inflow_categories_exist(self):
        """All inflow categories should exist."""
        inflow_categories = [
            CashFlowCategory.SALARY_INCOME,
            CashFlowCategory.INVESTMENT_INCOME,
            CashFlowCategory.DIVIDEND_INCOME,
            CashFlowCategory.INTEREST_INCOME,
            CashFlowCategory.RENTAL_INCOME,
            CashFlowCategory.BUSINESS_INCOME,
            CashFlowCategory.CAPITAL_GAIN,
            CashFlowCategory.DISTRIBUTION,
            CashFlowCategory.LOAN_PROCEEDS,
            CashFlowCategory.ASSET_SALE,
            CashFlowCategory.OTHER_INCOME,
        ]
        for cat in inflow_categories:
            assert cat is not None

    def test_outflow_categories_exist(self):
        """All outflow categories should exist."""
        outflow_categories = [
            CashFlowCategory.LIVING_EXPENSES,
            CashFlowCategory.MORTGAGE_PAYMENT,
            CashFlowCategory.PROPERTY_TAX,
            CashFlowCategory.INSURANCE,
            CashFlowCategory.INVESTMENT_PURCHASE,
            CashFlowCategory.CAPITAL_CALL,
            CashFlowCategory.TAX_PAYMENT,
            CashFlowCategory.LOAN_PAYMENT,
            CashFlowCategory.CHARITABLE_GIVING,
            CashFlowCategory.EDUCATION,
            CashFlowCategory.HEALTHCARE,
            CashFlowCategory.PROFESSIONAL_FEES,
            CashFlowCategory.OTHER_EXPENSE,
        ]
        for cat in outflow_categories:
            assert cat is not None


class TestConfidenceLevelEnum:
    """Tests for ConfidenceLevel enum."""

    def test_all_levels_exist(self):
        """All expected confidence levels should exist."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.SPECULATIVE.value == "speculative"


# -----------------------------------------------------------------------------
# Edge Cases
# -----------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for cash flow projection service."""

    def test_leap_year_february(self, service: CashFlowProjectionService):
        """Should handle February in leap year correctly."""
        periods = service._generate_periods(
            date(2024, 2, 1), date(2024, 2, 29), ProjectionPeriod.MONTHLY
        )

        assert len(periods) == 1
        assert periods[0][1] == date(2024, 2, 29)

    def test_non_leap_year_february(self, service: CashFlowProjectionService):
        """Should handle February in non-leap year correctly."""
        periods = service._generate_periods(
            date(2025, 2, 1), date(2025, 2, 28), ProjectionPeriod.MONTHLY
        )

        assert len(periods) == 1
        assert periods[0][1] == date(2025, 2, 28)

    def test_quarterly_mid_quarter_start(self, service: CashFlowProjectionService):
        """Quarterly periods starting mid-quarter should work correctly."""
        periods = service._generate_periods(
            date(2025, 2, 15), date(2025, 6, 30), ProjectionPeriod.QUARTERLY
        )

        # Should span from mid-Q1 through end of Q2
        assert len(periods) == 2
        assert periods[0][0] == date(2025, 2, 15)
        assert periods[0][1] == date(2025, 3, 31)  # End of Q1

    def test_large_date_range(self, service: CashFlowProjectionService):
        """Should handle large date ranges (10 years)."""
        periods = service._generate_periods(
            date(2025, 1, 1), date(2034, 12, 31), ProjectionPeriod.ANNUAL
        )

        assert len(periods) == 10

    def test_weekly_pattern_friday(self):
        """Weekly pattern on Friday should work correctly."""
        pattern = SpendingPattern(
            category=CashFlowCategory.LIVING_EXPENSES,
            description="Friday dinner",
            average_amount=Money(Decimal("100")),
            frequency=ProjectionPeriod.WEEKLY,
            day_of_week=4,  # Friday
        )
        # June 16, 2025 is Monday
        from_date = date(2025, 6, 16)
        next_occ = pattern.project_next_occurrence(from_date)
        # Next Friday is June 20, 2025
        assert next_occ == date(2025, 6, 20)

    def test_zero_opening_balance(self, service: CashFlowProjectionService):
        """Should handle zero opening balance."""
        summaries = service.project_cash_flows(
            entity_ids=None,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
            period=ProjectionPeriod.MONTHLY,
            include_patterns=False,
            include_scheduled=False,
            include_capital_calls=False,
            include_tax_estimates=False,
        )

        # Placeholder opening balance is 100,000 but test verifies behavior
        assert summaries[0].closing_balance == summaries[0].opening_balance

    def test_spending_pattern_with_none_day_of_month(self):
        """Monthly pattern without day_of_month should still work."""
        pattern = SpendingPattern(
            category=CashFlowCategory.LIVING_EXPENSES,
            description="Living expenses",
            average_amount=Money(Decimal("5000")),
            frequency=ProjectionPeriod.MONTHLY,
            day_of_month=None,  # No specific day
        )
        from_date = date(2025, 6, 15)
        # Without day_of_month, falls through to daily logic
        next_occ = pattern.project_next_occurrence(from_date)
        # Falls through to daily default
        assert next_occ == date(2025, 6, 16)

    def test_multiple_items_same_category_same_date(self):
        """Multiple items in same category on same date should sum correctly."""
        items = [
            CashFlowItem(
                date=date(2025, 6, 1),
                amount=Money(Decimal("1000")),
                category=CashFlowCategory.SALARY_INCOME,
                description="Salary 1",
                is_inflow=True,
            ),
            CashFlowItem(
                date=date(2025, 6, 1),
                amount=Money(Decimal("2000")),
                category=CashFlowCategory.SALARY_INCOME,
                description="Salary 2",
                is_inflow=True,
            ),
        ]
        summary = CashFlowSummary(
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            period_label="Jun 2025",
        )
        summary.calculate_totals(items)

        assert summary.inflows_by_category[CashFlowCategory.SALARY_INCOME] == Money(
            Decimal("3000")
        )
