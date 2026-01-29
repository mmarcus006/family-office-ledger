"""Pydantic v2 schemas for API request/response models."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Entity Schemas
class EntityCreate(BaseModel):
    """Schema for creating an entity."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(
        ..., pattern=r"^(llc|trust|partnership|individual|holding_co)$"
    )
    fiscal_year_end: date | None = None


class EntityResponse(BaseModel):
    """Schema for entity response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    entity_type: str
    fiscal_year_end: date
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Account Schemas
class AccountCreate(BaseModel):
    """Schema for creating an account."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=255)
    entity_id: UUID
    account_type: str = Field(..., pattern=r"^(asset|liability|equity|income|expense)$")
    sub_type: str | None = Field(
        default="other",
        pattern=r"^(checking|savings|credit_card|brokerage|ira|roth_ira|401k|529|real_estate|private_equity|venture_capital|crypto|cash|loan|other)$",
    )
    currency: str = Field(default="USD", min_length=3, max_length=3)


class AccountResponse(BaseModel):
    """Schema for account response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    entity_id: UUID
    account_type: str
    sub_type: str
    currency: str
    is_investment_account: bool
    is_active: bool
    created_at: datetime


# Transaction Entry Schemas
class EntryCreate(BaseModel):
    """Schema for creating a transaction entry."""

    account_id: UUID
    debit_amount: str = Field(default="0")
    debit_currency: str = Field(default="USD", min_length=3, max_length=3)
    credit_amount: str = Field(default="0")
    credit_currency: str = Field(default="USD", min_length=3, max_length=3)
    memo: str = ""


class EntryResponse(BaseModel):
    """Schema for entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    debit_amount: str
    debit_currency: str
    credit_amount: str
    credit_currency: str
    memo: str


# Transaction Schemas
class TransactionCreate(BaseModel):
    """Schema for creating a transaction."""

    transaction_date: date
    entries: list[EntryCreate] = Field(..., min_length=2)
    memo: str = ""
    reference: str = ""


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_date: date
    posted_date: date | None
    memo: str
    reference: str
    is_reversed: bool
    created_at: datetime
    entries: list[EntryResponse]


# Report Schemas
class ReportRequest(BaseModel):
    """Schema for report request parameters."""

    as_of_date: date
    entity_ids: list[UUID] | None = None


class ReportResponse(BaseModel):
    """Schema for report response."""

    report_name: str
    as_of_date: date | None = None
    data: Any
    totals: dict[str, Any]


class BalanceSheetResponse(BaseModel):
    """Schema for balance sheet report response."""

    report_name: str
    as_of_date: date
    data: dict[str, list[dict[str, Any]]]
    totals: dict[str, Any]


# Health check
class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str = "0.1.0"


# Reconciliation Schemas
class CreateSessionRequest(BaseModel):
    """Schema for creating a reconciliation session."""

    account_id: UUID
    file_path: str
    file_format: str


class MatchResponse(BaseModel):
    """Schema for reconciliation match response."""

    id: UUID
    session_id: UUID
    imported_id: str
    imported_date: date
    imported_amount: str
    imported_description: str
    suggested_ledger_txn_id: UUID | None
    confidence_score: int
    status: str
    actioned_at: datetime | None
    created_at: datetime


class SessionResponse(BaseModel):
    """Schema for reconciliation session response."""

    id: UUID
    account_id: UUID
    file_name: str
    file_format: str
    status: str
    created_at: datetime
    closed_at: datetime | None
    matches: list[MatchResponse]


class MatchListResponse(BaseModel):
    """Schema for paginated match list response."""

    matches: list[MatchResponse]
    total: int
    limit: int
    offset: int


class SessionSummaryResponse(BaseModel):
    """Schema for session summary response."""

    total_imported: int
    pending: int
    confirmed: int
    rejected: int
    skipped: int
    match_rate: float


# Transfer Matching Schemas
class CreateTransferSessionRequest(BaseModel):
    entity_ids: list[UUID] | None = None
    start_date: date | None = None
    end_date: date | None = None
    date_tolerance_days: int = Field(default=3, ge=1, le=30)


class TransferMatchResponse(BaseModel):
    id: UUID
    source_transaction_id: UUID
    target_transaction_id: UUID
    source_account_id: UUID
    target_account_id: UUID
    amount: str
    transfer_date: date
    confidence_score: int
    status: str
    memo: str
    confirmed_at: datetime | None
    created_at: datetime


class TransferSessionResponse(BaseModel):
    id: UUID
    entity_ids: list[UUID]
    date_tolerance_days: int
    status: str
    created_at: datetime
    closed_at: datetime | None
    matches: list[TransferMatchResponse]


class TransferMatchListResponse(BaseModel):
    matches: list[TransferMatchResponse]
    total: int


class TransferSummaryResponse(BaseModel):
    total_matches: int
    pending_count: int
    confirmed_count: int
    rejected_count: int
    total_confirmed_amount: str


# QSBS Schemas
class MarkQSBSRequest(BaseModel):
    qualification_date: date


class SecurityResponse(BaseModel):
    id: UUID
    symbol: str
    name: str
    cusip: str | None
    isin: str | None
    asset_class: str
    is_qsbs_eligible: bool
    qsbs_qualification_date: date | None
    issuer: str | None
    is_active: bool


class QSBSHoldingResponse(BaseModel):
    security_id: UUID
    security_symbol: str
    security_name: str
    position_id: UUID
    acquisition_date: date
    quantity: str
    cost_basis: str
    holding_period_days: int
    is_qualified: bool
    days_until_qualified: int
    potential_exclusion: str
    issuer: str | None


class QSBSSummaryResponse(BaseModel):
    total_qsbs_holdings: int
    qualified_holdings: int
    pending_holdings: int
    total_cost_basis: str
    total_potential_exclusion: str
    holdings: list[QSBSHoldingResponse]


# Tax Document Schemas
class Form8949EntryResponse(BaseModel):
    description: str
    date_acquired: date
    date_sold: date
    proceeds: str
    cost_basis: str
    adjustment_code: str | None
    adjustment_amount: str | None
    gain_or_loss: str
    is_long_term: bool
    box: str


class Form8949PartResponse(BaseModel):
    box: str
    entries: list[Form8949EntryResponse]
    total_proceeds: str
    total_cost_basis: str
    total_adjustments: str
    total_gain_or_loss: str


class Form8949Response(BaseModel):
    tax_year: int
    taxpayer_name: str
    short_term_parts: list[Form8949PartResponse]
    long_term_parts: list[Form8949PartResponse]
    total_short_term_proceeds: str
    total_short_term_cost_basis: str
    total_short_term_gain_or_loss: str
    total_long_term_proceeds: str
    total_long_term_cost_basis: str
    total_long_term_gain_or_loss: str


class ScheduleDResponse(BaseModel):
    tax_year: int
    taxpayer_name: str
    line_1a_box_a: str
    line_1b_box_b: str
    line_1c_box_c: str
    line_7_net_short_term: str
    line_8a_box_d: str
    line_8b_box_e: str
    line_8c_box_f: str
    line_15_net_long_term: str
    line_16_combined: str


class TaxDocumentSummaryResponse(BaseModel):
    tax_year: int
    entity_name: str
    short_term_transactions: int
    long_term_transactions: int
    total_short_term_proceeds: str
    total_short_term_cost_basis: str
    total_short_term_gain: str
    total_long_term_proceeds: str
    total_long_term_cost_basis: str
    total_long_term_gain: str
    wash_sale_adjustments: str
    net_capital_gain: str


class TaxDocumentsResponse(BaseModel):
    form_8949: Form8949Response
    schedule_d: ScheduleDResponse
    summary: TaxDocumentSummaryResponse


class GenerateTaxDocumentsRequest(BaseModel):
    tax_year: int = Field(..., ge=2000, le=2100)
    lot_proceeds: dict[str, str] | None = None


# Portfolio Analytics Schemas
class AssetAllocationResponse(BaseModel):
    asset_class: str
    market_value: str
    cost_basis: str
    unrealized_gain: str
    allocation_percent: str
    position_count: int


class AssetAllocationReportResponse(BaseModel):
    as_of_date: date
    entity_names: list[str]
    allocations: list[AssetAllocationResponse]
    total_market_value: str
    total_cost_basis: str
    total_unrealized_gain: str


class HoldingConcentrationResponse(BaseModel):
    security_id: UUID
    security_symbol: str
    security_name: str
    asset_class: str
    market_value: str
    cost_basis: str
    unrealized_gain: str
    concentration_percent: str
    position_count: int


class ConcentrationReportResponse(BaseModel):
    as_of_date: date
    entity_names: list[str]
    holdings: list[HoldingConcentrationResponse]
    total_market_value: str
    top_5_concentration: str
    top_10_concentration: str
    largest_single_holding: str


class PerformanceMetricsResponse(BaseModel):
    entity_name: str
    start_value: str
    end_value: str
    net_contributions: str
    total_return_amount: str
    total_return_percent: str
    unrealized_gain: str
    unrealized_gain_percent: str


class PerformanceReportResponse(BaseModel):
    start_date: date
    end_date: date
    entity_names: list[str]
    metrics: list[PerformanceMetricsResponse]
    portfolio_total_return_amount: str
    portfolio_total_return_percent: str


class PortfolioSummaryResponse(BaseModel):
    as_of_date: date
    total_market_value: str
    total_cost_basis: str
    total_unrealized_gain: str
    asset_allocation: list[dict[str, Any]]
    top_holdings: list[dict[str, Any]]
    concentration_metrics: dict[str, str]


# Audit Trail Schemas
class AuditEntryResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    user_id: UUID | None
    timestamp: datetime
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    change_summary: str
    ip_address: str | None
    user_agent: str | None


class AuditListResponse(BaseModel):
    entries: list[AuditEntryResponse]
    total: int


class AuditSummaryResponse(BaseModel):
    total_entries: int
    entries_by_action: dict[str, int]
    entries_by_entity_type: dict[str, int]
    oldest_entry: datetime | None
    newest_entry: datetime | None


# Exchange Rate Schemas
class ExchangeRateCreate(BaseModel):
    """Schema for creating an exchange rate."""

    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    rate: str  # Decimal as string
    effective_date: date
    source: str = Field(default="manual")


class ExchangeRateResponse(BaseModel):
    """Schema for exchange rate response."""

    id: UUID
    from_currency: str
    to_currency: str
    rate: str
    effective_date: date
    source: str
    created_at: datetime


class ExchangeRateListResponse(BaseModel):
    """Schema for paginated exchange rate list response."""

    rates: list[ExchangeRateResponse]
    total: int


class CurrencyConvertRequest(BaseModel):
    """Schema for currency conversion request."""

    amount: str
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    as_of_date: date


class CurrencyConvertResponse(BaseModel):
    """Schema for currency conversion response."""

    original_amount: str
    original_currency: str
    converted_amount: str
    converted_currency: str
    rate_used: str
    as_of_date: date


# Vendor Schemas
class VendorCreate(BaseModel):
    """Schema for creating a vendor."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    category: str | None = None
    tax_id: str | None = None
    is_1099_eligible: bool = False
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str = ""


class VendorUpdate(BaseModel):
    """Schema for updating a vendor."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None
    category: str | None = None
    tax_id: str | None = None
    is_1099_eligible: bool | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class VendorResponse(BaseModel):
    """Schema for vendor response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str | None
    tax_id: str | None
    is_1099_eligible: bool
    is_active: bool
    contact_email: str | None
    contact_phone: str | None
    notes: str
    created_at: datetime


class VendorListResponse(BaseModel):
    """Schema for paginated vendor list response."""

    vendors: list[VendorResponse]
    total: int


# Expense Schemas
class CategorizeTransactionRequest(BaseModel):
    """Schema for categorizing a transaction."""

    category: str | None = None
    tags: list[str] | None = None
    vendor_id: UUID | None = None


class ExpenseSummaryResponse(BaseModel):
    """Schema for expense summary response."""

    total_expenses: str
    transaction_count: int
    category_breakdown: dict[str, str]
    start_date: date
    end_date: date


class ExpenseByCategoryResponse(BaseModel):
    """Schema for expenses grouped by category."""

    categories: dict[str, str]
    total: str


class ExpenseByVendorResponse(BaseModel):
    """Schema for expenses grouped by vendor."""

    vendors: dict[str, str]  # vendor_id -> amount
    total: str


class RecurringExpenseResponse(BaseModel):
    """Schema for recurring expense detection response."""

    vendor_id: UUID
    frequency: str
    amount: str
    occurrence_count: int
    last_date: date


class RecurringExpenseListResponse(BaseModel):
    """Schema for list of recurring expenses."""

    recurring_expenses: list[RecurringExpenseResponse]
    total: int


# Budget Schemas
class BudgetCreate(BaseModel):
    """Schema for creating a budget."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    entity_id: UUID
    period_type: str = Field(..., pattern=r"^(monthly|quarterly|annual|custom)$")
    start_date: date
    end_date: date


class BudgetLineItemCreate(BaseModel):
    """Schema for creating a budget line item."""

    category: str = Field(..., min_length=1)
    budgeted_amount: str  # Decimal as string
    budgeted_currency: str = Field(default="USD", min_length=3, max_length=3)
    account_id: UUID | None = None
    notes: str = ""


class BudgetLineItemResponse(BaseModel):
    """Schema for budget line item response."""

    id: UUID
    budget_id: UUID
    category: str
    budgeted_amount: str
    budgeted_currency: str
    account_id: UUID | None
    notes: str


class BudgetResponse(BaseModel):
    """Schema for budget response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    entity_id: UUID
    period_type: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(BaseModel):
    """Schema for paginated budget list response."""

    budgets: list[BudgetResponse]
    total: int


class BudgetVarianceResponse(BaseModel):
    """Schema for budget variance response."""

    category: str
    budgeted: str
    actual: str
    variance: str
    variance_percent: str
    is_over_budget: bool


class BudgetVsActualResponse(BaseModel):
    """Schema for budget vs actual response."""

    budget: BudgetResponse | None
    line_items: list[BudgetLineItemResponse]
    variances: list[BudgetVarianceResponse]
    start_date: date
    end_date: date


class BudgetAlertResponse(BaseModel):
    """Schema for budget alert response."""

    category: str
    threshold: int
    percent_used: float
    budgeted: str
    actual: str
    status: str  # "warning" or "over_budget"


class BudgetAlertsResponse(BaseModel):
    """Schema for budget alerts list response."""

    budget_id: UUID
    alerts: list[BudgetAlertResponse]
    total_alerts: int
