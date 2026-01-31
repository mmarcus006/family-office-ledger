"""Domain models for real estate investments.

Provides comprehensive tracking for:
- Property ownership and valuations
- Rental income and lease management
- Depreciation schedules (straight-line, MACRS)
- 1031 exchange tracking with deadline management
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import Money


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PropertyType(str, Enum):
    """Type of real estate property."""

    RESIDENTIAL_SINGLE_FAMILY = "residential_single_family"
    RESIDENTIAL_MULTI_FAMILY = "residential_multi_family"
    RESIDENTIAL_CONDO = "residential_condo"
    COMMERCIAL_OFFICE = "commercial_office"
    COMMERCIAL_RETAIL = "commercial_retail"
    COMMERCIAL_INDUSTRIAL = "commercial_industrial"
    COMMERCIAL_MIXED_USE = "commercial_mixed_use"
    LAND = "land"
    AGRICULTURAL = "agricultural"
    HOSPITALITY = "hospitality"
    SELF_STORAGE = "self_storage"
    MOBILE_HOME_PARK = "mobile_home_park"


class PropertyStatus(str, Enum):
    """Status of a property."""

    OWNED = "owned"
    UNDER_CONTRACT = "under_contract"
    LISTED_FOR_SALE = "listed_for_sale"
    SOLD = "sold"
    IN_1031_EXCHANGE = "in_1031_exchange"


class ValuationType(str, Enum):
    """Type of property valuation."""

    PURCHASE_PRICE = "purchase_price"
    APPRAISAL = "appraisal"
    BROKER_OPINION = "broker_opinion"
    TAX_ASSESSMENT = "tax_assessment"
    COMPARABLE_SALES = "comparable_sales"
    INCOME_APPROACH = "income_approach"
    OWNER_ESTIMATE = "owner_estimate"


class LeaseType(str, Enum):
    """Type of lease agreement."""

    GROSS = "gross"  # Landlord pays expenses
    NET = "net"  # Tenant pays some expenses
    DOUBLE_NET = "double_net"  # Tenant pays taxes and insurance
    TRIPLE_NET = "triple_net"  # Tenant pays all expenses (NNN)
    MODIFIED_GROSS = "modified_gross"
    PERCENTAGE = "percentage"  # Base rent + percentage of sales


class DepreciationMethod(str, Enum):
    """Depreciation calculation method."""

    STRAIGHT_LINE = "straight_line"
    MACRS_27_5 = "macrs_27_5"  # Residential rental (27.5 years)
    MACRS_39 = "macrs_39"  # Commercial (39 years)
    MACRS_15 = "macrs_15"  # Land improvements
    MACRS_5 = "macrs_5"  # Certain equipment
    MACRS_7 = "macrs_7"  # Furniture, fixtures


class Exchange1031Status(str, Enum):
    """Status of a 1031 exchange."""

    INITIATED = "initiated"
    PROPERTY_SOLD = "property_sold"
    IDENTIFICATION_PERIOD = "identification_period"
    PROPERTIES_IDENTIFIED = "properties_identified"
    EXCHANGE_PERIOD = "exchange_period"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class PropertyAddress:
    """Physical address of a property."""

    street_address: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    unit_number: str | None = None
    county: str | None = None

    def __str__(self) -> str:
        unit = f" {self.unit_number}" if self.unit_number else ""
        return f"{self.street_address}{unit}, {self.city}, {self.state} {self.zip_code}"


@dataclass
class PropertyValuation:
    """A valuation record for a property."""

    property_id: UUID
    valuation_date: date
    value: Money
    valuation_type: ValuationType
    id: UUID = field(default_factory=uuid4)
    appraiser: str | None = None
    notes: str | None = None
    supporting_document_id: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class Property:
    """A real estate property.

    Tracks ownership, valuations, income, and tax basis.
    """

    name: str
    entity_id: UUID
    property_type: PropertyType
    address: PropertyAddress
    id: UUID = field(default_factory=uuid4)
    status: PropertyStatus = PropertyStatus.OWNED

    # Acquisition info
    acquisition_date: date | None = None
    acquisition_price: Money = field(default_factory=lambda: Money(Decimal("0")))
    acquisition_costs: Money = field(default_factory=lambda: Money(Decimal("0")))  # Closing costs, etc.

    # Tax basis allocation
    land_value: Money = field(default_factory=lambda: Money(Decimal("0")))
    building_value: Money = field(default_factory=lambda: Money(Decimal("0")))
    improvements_value: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Physical characteristics
    square_feet: int | None = None
    lot_size_acres: Decimal | None = None
    year_built: int | None = None
    units: int = 1
    bedrooms: int | None = None
    bathrooms: Decimal | None = None

    # Financial tracking
    current_value: Money | None = None
    current_value_date: date | None = None
    annual_property_tax: Money | None = None
    annual_insurance: Money | None = None
    hoa_monthly: Money | None = None

    # Mortgage/financing
    mortgage_balance: Money | None = None
    mortgage_rate: Decimal | None = None
    mortgage_payment_monthly: Money | None = None

    # Disposition
    sale_date: date | None = None
    sale_price: Money | None = None
    sale_costs: Money | None = None

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @property
    def total_cost_basis(self) -> Money:
        """Total tax basis including acquisition costs."""
        return Money(
            self.acquisition_price.amount
            + self.acquisition_costs.amount
            + self.improvements_value.amount
        )

    @property
    def depreciable_basis(self) -> Money:
        """Basis available for depreciation (excludes land)."""
        return Money(self.building_value.amount + self.improvements_value.amount)

    @property
    def equity(self) -> Money | None:
        """Current equity (value - mortgage)."""
        if self.current_value is None:
            return None
        mortgage = self.mortgage_balance.amount if self.mortgage_balance else Decimal("0")
        return Money(self.current_value.amount - mortgage)

    @property
    def ltv(self) -> Decimal | None:
        """Loan-to-value ratio."""
        if self.current_value is None or self.mortgage_balance is None:
            return None
        if self.current_value.amount == 0:
            return None
        return self.mortgage_balance.amount / self.current_value.amount


@dataclass
class Lease:
    """A lease agreement for a property."""

    property_id: UUID
    tenant_name: str
    lease_type: LeaseType
    start_date: date
    end_date: date
    monthly_rent: Money
    id: UUID = field(default_factory=uuid4)
    unit_number: str | None = None
    security_deposit: Money | None = None

    # Rent escalation
    annual_increase_percent: Decimal | None = None
    annual_increase_fixed: Money | None = None

    # Expense pass-throughs (for NNN leases)
    tenant_pays_taxes: bool = False
    tenant_pays_insurance: bool = False
    tenant_pays_maintenance: bool = False
    cam_monthly: Money | None = None  # Common Area Maintenance

    # Percentage rent (for retail)
    percentage_rent_rate: Decimal | None = None
    percentage_rent_breakpoint: Money | None = None

    # Status
    is_active: bool = True
    is_month_to_month: bool = False
    notice_period_days: int = 30

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def annual_rent(self) -> Money:
        """Annual base rent."""
        return Money(self.monthly_rent.amount * 12)

    @property
    def days_remaining(self) -> int:
        """Days until lease expiration."""
        today = date.today()
        if today >= self.end_date:
            return 0
        return (self.end_date - today).days

    @property
    def is_expiring_soon(self) -> bool:
        """Whether lease expires within 90 days."""
        return 0 < self.days_remaining <= 90


@dataclass
class DepreciationSchedule:
    """Depreciation schedule for a property or improvement."""

    property_id: UUID
    asset_description: str
    method: DepreciationMethod
    depreciable_basis: Money
    placed_in_service_date: date
    id: UUID = field(default_factory=uuid4)
    useful_life_years: Decimal | None = None  # Auto-set based on method if None
    salvage_value: Money = field(default_factory=lambda: Money(Decimal("0")))
    accumulated_depreciation: Money = field(default_factory=lambda: Money(Decimal("0")))
    is_disposed: bool = False
    disposal_date: date | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        """Set useful life based on depreciation method if not specified."""
        if self.useful_life_years is None:
            method_lives = {
                DepreciationMethod.STRAIGHT_LINE: Decimal("27.5"),
                DepreciationMethod.MACRS_27_5: Decimal("27.5"),
                DepreciationMethod.MACRS_39: Decimal("39"),
                DepreciationMethod.MACRS_15: Decimal("15"),
                DepreciationMethod.MACRS_5: Decimal("5"),
                DepreciationMethod.MACRS_7: Decimal("7"),
            }
            self.useful_life_years = method_lives.get(self.method, Decimal("27.5"))

    @property
    def annual_depreciation(self) -> Money:
        """Annual depreciation amount (straight-line equivalent)."""
        if self.useful_life_years is None or self.useful_life_years == 0:
            return Money(Decimal("0"))
        depreciable = self.depreciable_basis.amount - self.salvage_value.amount
        return Money(depreciable / self.useful_life_years)

    @property
    def remaining_basis(self) -> Money:
        """Remaining depreciable basis."""
        return Money(self.depreciable_basis.amount - self.accumulated_depreciation.amount)

    def calculate_depreciation_for_year(self, tax_year: int) -> Money:
        """Calculate depreciation for a specific tax year.

        Uses mid-month convention for real property.
        """
        if self.is_disposed and self.disposal_date and self.disposal_date.year < tax_year:
            return Money(Decimal("0"))

        service_year = self.placed_in_service_date.year
        years_in_service = tax_year - service_year

        if years_in_service < 0:
            return Money(Decimal("0"))

        annual = self.annual_depreciation.amount

        # First year - mid-month convention
        if years_in_service == 0:
            months_in_service = 12 - self.placed_in_service_date.month + 1
            # Add 0.5 for mid-month convention
            fraction = (Decimal(months_in_service) - Decimal("0.5")) / 12
            return Money(annual * fraction)

        # Last year if disposed - mid-month convention
        if self.is_disposed and self.disposal_date and self.disposal_date.year == tax_year:
            months = self.disposal_date.month
            fraction = (Decimal(months) - Decimal("0.5")) / 12
            return Money(annual * fraction)

        # Check if fully depreciated
        years_elapsed = Decimal(years_in_service)
        if self.useful_life_years and years_elapsed >= self.useful_life_years:
            return Money(Decimal("0"))

        return Money(annual)


@dataclass
class Exchange1031:
    """A Section 1031 like-kind exchange.

    Tracks the exchange timeline and identified/acquired properties.
    Key deadlines:
    - 45 days: Identification period (must identify replacement properties)
    - 180 days: Exchange period (must close on replacement property)
    """

    relinquished_property_id: UUID
    entity_id: UUID
    sale_date: date
    sale_price: Money
    id: UUID = field(default_factory=uuid4)
    status: Exchange1031Status = Exchange1031Status.INITIATED

    # Qualified Intermediary
    qi_name: str | None = None
    qi_contact: str | None = None
    exchange_funds_held: Money | None = None

    # Identification (45-day rule)
    identification_deadline: date | None = None
    identified_property_ids: list[UUID] = field(default_factory=list)
    identified_property_descriptions: list[str] = field(default_factory=list)

    # Exchange completion (180-day rule)
    exchange_deadline: date | None = None
    replacement_property_id: UUID | None = None
    acquisition_date: date | None = None
    acquisition_price: Money | None = None

    # Basis tracking
    relinquished_basis: Money | None = None
    boot_received: Money | None = None  # Cash or non-like-kind property received
    deferred_gain: Money | None = None
    replacement_basis: Money | None = None  # Carryover basis

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        """Calculate deadlines from sale date."""
        if self.identification_deadline is None:
            self.identification_deadline = self.sale_date + timedelta(days=45)
        if self.exchange_deadline is None:
            self.exchange_deadline = self.sale_date + timedelta(days=180)

    @property
    def days_until_identification(self) -> int:
        """Days remaining in identification period."""
        if self.identification_deadline is None:
            return 0
        today = date.today()
        if today >= self.identification_deadline:
            return 0
        return (self.identification_deadline - today).days

    @property
    def days_until_exchange(self) -> int:
        """Days remaining in exchange period."""
        if self.exchange_deadline is None:
            return 0
        today = date.today()
        if today >= self.exchange_deadline:
            return 0
        return (self.exchange_deadline - today).days

    @property
    def is_identification_expired(self) -> bool:
        """Whether the 45-day identification period has expired."""
        if self.identification_deadline is None:
            return True
        return date.today() > self.identification_deadline

    @property
    def is_exchange_expired(self) -> bool:
        """Whether the 180-day exchange period has expired."""
        if self.exchange_deadline is None:
            return True
        return date.today() > self.exchange_deadline

    @property
    def properties_identified_count(self) -> int:
        """Number of properties identified."""
        return len(self.identified_property_ids) + len(self.identified_property_descriptions)

    def add_identified_property(
        self, property_id: UUID | None = None, description: str | None = None
    ) -> bool:
        """Add an identified replacement property.

        Three-property rule: Can identify up to 3 properties regardless of value.
        200% rule: Can identify more if total value <= 200% of relinquished.

        Returns:
            True if property was added, False if limit reached.
        """
        if self.is_identification_expired:
            return False

        current_count = self.properties_identified_count

        # Three-property rule (simplified - always allow up to 3)
        if current_count >= 3:
            return False

        if property_id:
            self.identified_property_ids.append(property_id)
        elif description:
            self.identified_property_descriptions.append(description)
        else:
            return False

        return True

    def calculate_deferred_gain(
        self,
        relinquished_basis: Money,
        selling_expenses: Money,
        boot_received: Money | None = None,
    ) -> Money:
        """Calculate gain deferred through the exchange.

        Deferred Gain = Realized Gain - Boot Received
        Realized Gain = Sale Price - Basis - Selling Expenses
        """
        self.relinquished_basis = relinquished_basis
        self.boot_received = boot_received or Money(Decimal("0"))

        realized_gain = (
            self.sale_price.amount
            - relinquished_basis.amount
            - selling_expenses.amount
        )

        # Recognized gain is limited to boot received
        recognized_gain = min(realized_gain, self.boot_received.amount)

        self.deferred_gain = Money(realized_gain - recognized_gain)

        # Replacement basis = Replacement price - Deferred gain
        if self.acquisition_price:
            self.replacement_basis = Money(
                self.acquisition_price.amount - self.deferred_gain.amount
            )

        return self.deferred_gain


@dataclass
class RentalIncome:
    """Monthly rental income record for tracking and reconciliation."""

    property_id: UUID
    lease_id: UUID | None
    period_start: date
    period_end: date
    base_rent: Money
    id: UUID = field(default_factory=uuid4)
    additional_rent: Money = field(default_factory=lambda: Money(Decimal("0")))  # CAM, utilities, etc.
    late_fees: Money = field(default_factory=lambda: Money(Decimal("0")))
    concessions: Money = field(default_factory=lambda: Money(Decimal("0")))  # Discounts
    is_received: bool = False
    received_date: date | None = None
    transaction_id: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def total_due(self) -> Money:
        """Total amount due for the period."""
        return Money(
            self.base_rent.amount
            + self.additional_rent.amount
            + self.late_fees.amount
            - self.concessions.amount
        )
