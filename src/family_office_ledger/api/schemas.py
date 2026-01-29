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
    credit_amount: str = Field(default="0")
    memo: str = ""


class EntryResponse(BaseModel):
    """Schema for entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    debit_amount: str
    credit_amount: str
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
