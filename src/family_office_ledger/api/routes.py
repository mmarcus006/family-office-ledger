"""API routes for Family Office Ledger."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from family_office_ledger.api.schemas import (
    AccountCreate,
    AccountResponse,
    AssetAllocationReportResponse,
    AssetAllocationResponse,
    AuditEntryResponse,
    AuditListResponse,
    AuditSummaryResponse,
    BalanceSheetResponse,
    CategorizeTransactionRequest,
    ConcentrationReportResponse,
    CreateSessionRequest,
    CreateTransferSessionRequest,
    CurrencyConvertRequest,
    CurrencyConvertResponse,
    EntityCreate,
    EntityResponse,
    EntryResponse,
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateResponse,
    ExpenseByCategoryResponse,
    ExpenseByVendorResponse,
    ExpenseSummaryResponse,
    Form8949EntryResponse,
    Form8949PartResponse,
    Form8949Response,
    GenerateTaxDocumentsRequest,
    HealthResponse,
    HoldingConcentrationResponse,
    MarkQSBSRequest,
    MatchListResponse,
    MatchResponse,
    PerformanceMetricsResponse,
    PerformanceReportResponse,
    PortfolioSummaryResponse,
    QSBSHoldingResponse,
    QSBSSummaryResponse,
    RecurringExpenseListResponse,
    RecurringExpenseResponse,
    ReportResponse,
    ScheduleDResponse,
    SecurityResponse,
    SessionResponse,
    SessionSummaryResponse,
    TaxDocumentsResponse,
    TaxDocumentSummaryResponse,
    TransactionCreate,
    TransactionResponse,
    TransferMatchListResponse,
    TransferMatchResponse,
    TransferSessionResponse,
    TransferSummaryResponse,
    VendorCreate,
    VendorListResponse,
    VendorResponse,
    VendorUpdate,
)
from family_office_ledger.domain.audit import AuditAction, AuditEntityType
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.exchange_rates import ExchangeRate, ExchangeRateSource
from family_office_ledger.domain.reconciliation import (
    ReconciliationMatch,
    ReconciliationMatchStatus,
    ReconciliationSession,
)
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.transfer_matching import (
    TransferMatch,
    TransferMatchingSession,
    TransferMatchStatus,
)
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    Currency,
    EntityType,
    Money,
)
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    TransactionRepository,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteExchangeRateRepository,
    SQLitePositionRepository,
    SQLiteReconciliationSessionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)
from family_office_ledger.domain.vendors import Vendor
from family_office_ledger.services.audit import AuditService
from family_office_ledger.services.currency import (
    CurrencyServiceImpl,
    ExchangeRateNotFoundError,
)
from family_office_ledger.services.expense import ExpenseServiceImpl
from family_office_ledger.services.interfaces import LedgerService, ReportingService
from family_office_ledger.services.ledger import (
    LedgerServiceImpl,
    UnbalancedTransactionError,
)
from family_office_ledger.services.portfolio_analytics import PortfolioAnalyticsService
from family_office_ledger.services.qsbs import (
    QSBSService,
    SecurityNotFoundError,
)
from family_office_ledger.services.reconciliation import (
    MatchNotFoundError,
    ReconciliationServiceImpl,
    SessionExistsError,
    SessionNotFoundError,
)
from family_office_ledger.services.reporting import ReportingServiceImpl
from family_office_ledger.services.tax_documents import TaxDocumentService
from family_office_ledger.services.transfer_matching import (
    TransferMatchingService,
    TransferMatchNotFoundError,
    TransferSessionNotFoundError,
)

# Create routers
health_router = APIRouter(tags=["health"])
entity_router = APIRouter(prefix="/entities", tags=["entities"])
account_router = APIRouter(prefix="/accounts", tags=["accounts"])
transaction_router = APIRouter(prefix="/transactions", tags=["transactions"])
report_router = APIRouter(prefix="/reports", tags=["reports"])
reconciliation_router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])
transfer_router = APIRouter(prefix="/transfers", tags=["transfers"])
qsbs_router = APIRouter(prefix="/qsbs", tags=["qsbs"])
tax_router = APIRouter(prefix="/tax", tags=["tax"])
portfolio_router = APIRouter(prefix="/portfolio", tags=["portfolio"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])
currency_router = APIRouter(prefix="/currency", tags=["currency"])
expense_router = APIRouter(prefix="/expenses", tags=["expenses"])
vendor_router = APIRouter(prefix="/vendors", tags=["vendors"])


# Dependency injection functions
def get_entity_repository(db: SQLiteDatabase) -> EntityRepository:
    """Get entity repository instance."""
    return SQLiteEntityRepository(db)


def get_account_repository(db: SQLiteDatabase) -> AccountRepository:
    """Get account repository instance."""
    return SQLiteAccountRepository(db)


def get_transaction_repository(db: SQLiteDatabase) -> TransactionRepository:
    """Get transaction repository instance."""
    return SQLiteTransactionRepository(db)


def get_ledger_service(
    db: SQLiteDatabase,
    entity_repo: EntityRepository,
    account_repo: AccountRepository,
    transaction_repo: TransactionRepository,
) -> LedgerService:
    """Get ledger service instance."""
    return LedgerServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        entity_repo=entity_repo,
    )


def get_reporting_service(db: SQLiteDatabase) -> ReportingService:
    """Get reporting service instance."""
    entity_repo = SQLiteEntityRepository(db)
    account_repo = SQLiteAccountRepository(db)
    transaction_repo = SQLiteTransactionRepository(db)
    position_repo = SQLitePositionRepository(db)
    tax_lot_repo = SQLiteTaxLotRepository(db)
    security_repo = SQLiteSecurityRepository(db)

    return ReportingServiceImpl(
        entity_repo=entity_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        security_repo=security_repo,
    )


def get_reconciliation_service(db: SQLiteDatabase) -> ReconciliationServiceImpl:
    """Get reconciliation service instance."""
    account_repo = SQLiteAccountRepository(db)
    transaction_repo = SQLiteTransactionRepository(db)
    session_repo = SQLiteReconciliationSessionRepository(db)

    return ReconciliationServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        session_repo=session_repo,
    )


# Helper functions
def _entity_to_response(entity: Entity) -> EntityResponse:
    """Convert Entity domain object to response schema."""
    return EntityResponse(
        id=entity.id,
        name=entity.name,
        entity_type=entity.entity_type.value,
        fiscal_year_end=entity.fiscal_year_end,
        is_active=entity.is_active,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _account_to_response(account: Account) -> AccountResponse:
    """Convert Account domain object to response schema."""
    return AccountResponse(
        id=account.id,
        name=account.name,
        entity_id=account.entity_id,
        account_type=account.account_type.value,
        sub_type=account.sub_type.value,
        currency=account.currency,
        is_investment_account=account.is_investment_account,
        is_active=account.is_active,
        created_at=account.created_at,
    )


def _get_currency_str(currency: Currency | str) -> str:
    if isinstance(currency, Currency):
        return currency.value
    return currency


def _entry_to_response(entry: Entry) -> EntryResponse:
    """Convert Entry domain object to response schema."""
    return EntryResponse(
        id=entry.id,
        account_id=entry.account_id,
        debit_amount=str(entry.debit_amount.amount),
        debit_currency=_get_currency_str(entry.debit_amount.currency),
        credit_amount=str(entry.credit_amount.amount),
        credit_currency=_get_currency_str(entry.credit_amount.currency),
        memo=entry.memo,
    )


def _transaction_to_response(txn: Transaction) -> TransactionResponse:
    """Convert Transaction domain object to response schema."""
    return TransactionResponse(
        id=txn.id,
        transaction_date=txn.transaction_date,
        posted_date=txn.posted_date,
        memo=txn.memo,
        reference=txn.reference,
        is_reversed=txn.is_reversed,
        created_at=txn.created_at,
        entries=[_entry_to_response(e) for e in txn.entries],
    )


# Health endpoint
@health_router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


# Entity endpoints
@entity_router.post(
    "",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity(
    payload: EntityCreate,
    db: Annotated[SQLiteDatabase, Depends()],
) -> EntityResponse:
    """Create a new entity."""
    entity_repo = get_entity_repository(db)

    # Parse entity type
    entity_type = EntityType(payload.entity_type)

    # Create entity
    entity = Entity(
        name=payload.name,
        entity_type=entity_type,
    )
    if payload.fiscal_year_end:
        entity.fiscal_year_end = payload.fiscal_year_end

    entity_repo.add(entity)
    return _entity_to_response(entity)


@entity_router.get("", response_model=list[EntityResponse])
def list_entities(
    db: Annotated[SQLiteDatabase, Depends()],
) -> list[EntityResponse]:
    """List all entities."""
    entity_repo = get_entity_repository(db)
    entities = list(entity_repo.list_all())
    return [_entity_to_response(e) for e in entities]


@entity_router.get("/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> EntityResponse:
    """Get entity by ID."""
    entity_repo = get_entity_repository(db)
    entity = entity_repo.get(entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {entity_id} not found",
        )
    return _entity_to_response(entity)


# Account endpoints
@account_router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    payload: AccountCreate,
    db: Annotated[SQLiteDatabase, Depends()],
) -> AccountResponse:
    """Create a new account."""
    entity_repo = get_entity_repository(db)
    account_repo = get_account_repository(db)

    # Verify entity exists
    entity = entity_repo.get(payload.entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {payload.entity_id} not found",
        )

    # Parse types
    account_type = AccountType(payload.account_type)
    sub_type = (
        AccountSubType(payload.sub_type) if payload.sub_type else AccountSubType.OTHER
    )

    # Create account
    account = Account(
        name=payload.name,
        entity_id=payload.entity_id,
        account_type=account_type,
        sub_type=sub_type,
        currency=payload.currency,
    )

    account_repo.add(account)
    return _account_to_response(account)


@account_router.get("", response_model=list[AccountResponse])
def list_accounts(
    db: Annotated[SQLiteDatabase, Depends()],
    entity_id: UUID | None = Query(default=None),
) -> list[AccountResponse]:
    """List accounts, optionally filtered by entity_id."""
    account_repo = get_account_repository(db)

    if entity_id:
        accounts = list(account_repo.list_by_entity(entity_id))
    else:
        # List all accounts by iterating entities
        entity_repo = get_entity_repository(db)
        accounts = []
        for entity in entity_repo.list_all():
            accounts.extend(account_repo.list_by_entity(entity.id))

    return [_account_to_response(a) for a in accounts]


# Transaction endpoints
@transaction_router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_transaction(
    payload: TransactionCreate,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransactionResponse:
    """Post a new transaction."""
    entity_repo = get_entity_repository(db)
    account_repo = get_account_repository(db)
    transaction_repo = get_transaction_repository(db)
    ledger_service = get_ledger_service(db, entity_repo, account_repo, transaction_repo)

    # Create entries
    entries: list[Entry] = []
    for entry_data in payload.entries:
        entry = Entry(
            account_id=entry_data.account_id,
            debit_amount=Money(
                Decimal(entry_data.debit_amount), entry_data.debit_currency
            ),
            credit_amount=Money(
                Decimal(entry_data.credit_amount), entry_data.credit_currency
            ),
            memo=entry_data.memo,
        )
        entries.append(entry)

    # Create transaction
    txn = Transaction(
        transaction_date=payload.transaction_date,
        entries=entries,
        memo=payload.memo,
        reference=payload.reference,
    )

    # Post via ledger service
    try:
        ledger_service.post_transaction(txn)
    except UnbalancedTransactionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    return _transaction_to_response(txn)


@transaction_router.get("", response_model=list[TransactionResponse])
def list_transactions(
    db: Annotated[SQLiteDatabase, Depends()],
    account_id: UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> list[TransactionResponse]:
    """List transactions with optional filters."""
    transaction_repo = get_transaction_repository(db)

    if account_id:
        transactions = list(
            transaction_repo.list_by_account(
                account_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
    elif start_date and end_date:
        transactions = list(transaction_repo.list_by_date_range(start_date, end_date))
    else:
        # Return empty list if no filter provided (for safety)
        transactions = []

    return [_transaction_to_response(t) for t in transactions]


# Report endpoints
@report_router.get("/net-worth", response_model=ReportResponse)
def net_worth_report(
    db: Annotated[SQLiteDatabase, Depends()],
    as_of_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> ReportResponse:
    """Generate net worth report."""
    reporting_service = get_reporting_service(db)

    report_data = reporting_service.net_worth_report(
        entity_ids=entity_ids,
        as_of_date=as_of_date,
    )

    return ReportResponse(
        report_name=report_data["report_name"],
        as_of_date=report_data["as_of_date"],
        data=_serialize_report_data(report_data["data"]),
        totals=_serialize_totals(report_data["totals"]),
    )


@report_router.get("/balance-sheet/{entity_id}", response_model=BalanceSheetResponse)
def balance_sheet_report(
    entity_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
    as_of_date: date = Query(...),
) -> BalanceSheetResponse:
    """Generate balance sheet for an entity."""
    entity_repo = get_entity_repository(db)
    entity = entity_repo.get(entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {entity_id} not found",
        )

    reporting_service = get_reporting_service(db)

    report_data = reporting_service.balance_sheet_report(
        entity_id=entity_id,
        as_of_date=as_of_date,
    )

    return BalanceSheetResponse(
        report_name=report_data["report_name"],
        as_of_date=report_data["as_of_date"],
        data=_serialize_nested_report_data(report_data["data"]),
        totals=_serialize_totals(report_data["totals"]),
    )


@report_router.get("/summary-by-type", response_model=ReportResponse)
def transaction_summary_by_type(
    db: Annotated[SQLiteDatabase, Depends()],
    start_date: date = Query(...),
    end_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> ReportResponse:
    reporting_service = get_reporting_service(db)

    report_data = reporting_service.transaction_summary_by_type(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
    )

    return ReportResponse(
        report_name=report_data["report_name"],
        data=_serialize_report_data(report_data["data"]),
        totals=_serialize_totals(report_data["totals"]),
    )


@report_router.get("/summary-by-entity", response_model=ReportResponse)
def transaction_summary_by_entity(
    db: Annotated[SQLiteDatabase, Depends()],
    start_date: date = Query(...),
    end_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> ReportResponse:
    reporting_service = get_reporting_service(db)

    report_data = reporting_service.transaction_summary_by_entity(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
    )

    return ReportResponse(
        report_name=report_data["report_name"],
        data=_serialize_report_data(report_data["data"]),
        totals=_serialize_totals(report_data["totals"]),
    )


@report_router.get("/dashboard", response_model=ReportResponse)
def dashboard_summary(
    db: Annotated[SQLiteDatabase, Depends()],
    as_of_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> ReportResponse:
    reporting_service = get_reporting_service(db)

    report_data = reporting_service.dashboard_summary(
        entity_ids=entity_ids,
        as_of_date=as_of_date,
    )

    return ReportResponse(
        report_name=report_data["report_name"],
        as_of_date=report_data["as_of_date"],
        data=_serialize_dashboard_data(report_data["data"]),
        totals={},
    )


def _serialize_dashboard_data(data: dict[str, Any]) -> dict[str, Any]:
    serialized = {}
    for key, value in data.items():
        if isinstance(value, Decimal) or isinstance(value, UUID):
            serialized[key] = str(value)
        else:
            serialized[key] = value
    return serialized


def _serialize_report_data(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize report data for JSON response."""
    serialized = []
    for item in data:
        serialized_item = {}
        for key, value in item.items():
            if isinstance(value, Decimal) or isinstance(value, UUID):
                serialized_item[key] = str(value)
            elif isinstance(value, date):
                serialized_item[key] = value.isoformat()
            else:
                serialized_item[key] = value
        serialized.append(serialized_item)
    return serialized


def _serialize_nested_report_data(
    data: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Serialize nested report data for JSON response."""
    return {key: _serialize_report_data(value) for key, value in data.items()}


def _serialize_totals(totals: dict[str, Any]) -> dict[str, Any]:
    """Serialize totals for JSON response."""
    serialized = {}
    for key, value in totals.items():
        if isinstance(value, Decimal):
            serialized[key] = str(value)
        else:
            serialized[key] = value
    return serialized


def _reconciliation_match_to_response(
    match: ReconciliationMatch,
) -> MatchResponse:
    """Convert ReconciliationMatch domain object to response schema."""
    return MatchResponse(
        id=match.id,
        session_id=match.session_id,
        imported_id=match.imported_id,
        imported_date=match.imported_date,
        imported_amount=str(match.imported_amount),
        imported_description=match.imported_description,
        suggested_ledger_txn_id=match.suggested_ledger_txn_id,
        confidence_score=match.confidence_score,
        status=match.status.value,
        actioned_at=match.actioned_at,
        created_at=match.created_at,
    )


def _reconciliation_session_to_response(
    session: ReconciliationSession,
) -> SessionResponse:
    """Convert ReconciliationSession domain object to response schema."""
    return SessionResponse(
        id=session.id,
        account_id=session.account_id,
        file_name=session.file_name,
        file_format=session.file_format,
        status=session.status.value,
        created_at=session.created_at,
        closed_at=session.closed_at,
        matches=[_reconciliation_match_to_response(m) for m in session.matches],
    )


# Reconciliation endpoints
@reconciliation_router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: CreateSessionRequest,
    db: Annotated[SQLiteDatabase, Depends()],
) -> SessionResponse:
    """Create a new reconciliation session."""
    reconciliation_service = get_reconciliation_service(db)

    try:
        session = reconciliation_service.create_session(
            account_id=payload.account_id,
            file_path=payload.file_path,
            file_format=payload.file_format,
        )
    except SessionExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    return _reconciliation_session_to_response(session)


@reconciliation_router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
)
def get_session(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> SessionResponse:
    """Get a reconciliation session by ID."""
    reconciliation_service = get_reconciliation_service(db)

    session = reconciliation_service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return _reconciliation_session_to_response(session)


@reconciliation_router.get(
    "/sessions/{session_id}/matches",
    response_model=MatchListResponse,
)
def list_matches(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
    match_status: ReconciliationMatchStatus | None = Query(
        default=None, alias="status"
    ),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> MatchListResponse:
    """List matches for a session with pagination."""
    reconciliation_service = get_reconciliation_service(db)

    try:
        matches, total = reconciliation_service.list_matches(
            session_id=session_id,
            status=match_status,
            limit=limit,
            offset=offset,
        )
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return MatchListResponse(
        matches=[_reconciliation_match_to_response(m) for m in matches],
        total=total,
        limit=limit,
        offset=offset,
    )

    return MatchListResponse(
        matches=[_reconciliation_match_to_response(m) for m in matches],
        total=total,
        limit=limit,
        offset=offset,
    )


@reconciliation_router.post(
    "/sessions/{session_id}/matches/{match_id}/confirm",
    response_model=MatchResponse,
)
def confirm_match(
    session_id: UUID,
    match_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> MatchResponse:
    """Confirm a match in a session."""
    reconciliation_service = get_reconciliation_service(db)

    try:
        match = reconciliation_service.confirm_session_match(session_id, match_id)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except MatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _reconciliation_match_to_response(match)


@reconciliation_router.post(
    "/sessions/{session_id}/matches/{match_id}/reject",
    response_model=MatchResponse,
)
def reject_match(
    session_id: UUID,
    match_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> MatchResponse:
    """Reject a match in a session."""
    reconciliation_service = get_reconciliation_service(db)

    try:
        match = reconciliation_service.reject_session_match(session_id, match_id)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except MatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _reconciliation_match_to_response(match)


@reconciliation_router.post(
    "/sessions/{session_id}/matches/{match_id}/skip",
    response_model=MatchResponse,
)
def skip_match(
    session_id: UUID,
    match_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> MatchResponse:
    """Skip a match in a session."""
    reconciliation_service = get_reconciliation_service(db)

    try:
        match = reconciliation_service.skip_session_match(session_id, match_id)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except MatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _reconciliation_match_to_response(match)


@reconciliation_router.post(
    "/sessions/{session_id}/close",
    response_model=SessionResponse,
)
def close_session(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> SessionResponse:
    """Manually close a session."""
    reconciliation_service = get_reconciliation_service(db)

    try:
        session = reconciliation_service.close_session(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _reconciliation_session_to_response(session)


@reconciliation_router.get(
    "/sessions/{session_id}/summary",
    response_model=SessionSummaryResponse,
)
def get_session_summary(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> SessionSummaryResponse:
    """Get session summary statistics."""
    reconciliation_service = get_reconciliation_service(db)

    try:
        summary = reconciliation_service.get_session_summary(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return SessionSummaryResponse(
        total_imported=summary.total_imported,
        pending=summary.pending,
        confirmed=summary.confirmed,
        rejected=summary.rejected,
        skipped=summary.skipped,
        match_rate=summary.match_rate,
    )


# Transfer Matching Endpoints
_transfer_service_cache: dict[int, TransferMatchingService] = {}


def get_transfer_matching_service(db: SQLiteDatabase) -> TransferMatchingService:
    db_id = id(db)
    if db_id not in _transfer_service_cache:
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        _transfer_service_cache[db_id] = TransferMatchingService(
            transaction_repo=transaction_repo,
            account_repo=account_repo,
        )
    return _transfer_service_cache[db_id]


def _transfer_match_to_response(match: TransferMatch) -> TransferMatchResponse:
    return TransferMatchResponse(
        id=match.id,
        source_transaction_id=match.source_transaction_id,
        target_transaction_id=match.target_transaction_id,
        source_account_id=match.source_account_id,
        target_account_id=match.target_account_id,
        amount=str(match.amount),
        transfer_date=match.transfer_date,
        confidence_score=match.confidence_score,
        status=match.status.value,
        memo=match.memo,
        confirmed_at=match.confirmed_at,
        created_at=match.created_at,
    )


def _transfer_session_to_response(
    session: TransferMatchingSession,
) -> TransferSessionResponse:
    return TransferSessionResponse(
        id=session.id,
        entity_ids=session.entity_ids,
        date_tolerance_days=session.date_tolerance_days,
        status=session.status,
        created_at=session.created_at,
        closed_at=session.closed_at,
        matches=[_transfer_match_to_response(m) for m in session.matches],
    )


@transfer_router.post(
    "/sessions",
    response_model=TransferSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer_session(
    payload: CreateTransferSessionRequest,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransferSessionResponse:
    transfer_service = get_transfer_matching_service(db)

    session = transfer_service.create_session(
        entity_ids=payload.entity_ids,
        start_date=payload.start_date,
        end_date=payload.end_date,
        date_tolerance_days=payload.date_tolerance_days,
    )

    return _transfer_session_to_response(session)


@transfer_router.get(
    "/sessions/{session_id}",
    response_model=TransferSessionResponse,
)
def get_transfer_session(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransferSessionResponse:
    transfer_service = get_transfer_matching_service(db)

    try:
        session = transfer_service.get_session(session_id)
    except TransferSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _transfer_session_to_response(session)


@transfer_router.get(
    "/sessions/{session_id}/matches",
    response_model=TransferMatchListResponse,
)
def list_transfer_matches(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
    match_status: TransferMatchStatus | None = Query(default=None, alias="status"),
) -> TransferMatchListResponse:
    transfer_service = get_transfer_matching_service(db)

    try:
        matches = transfer_service.list_matches(session_id, status=match_status)
    except TransferSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return TransferMatchListResponse(
        matches=[_transfer_match_to_response(m) for m in matches],
        total=len(matches),
    )


@transfer_router.post(
    "/sessions/{session_id}/matches/{match_id}/confirm",
    response_model=TransferMatchResponse,
)
def confirm_transfer_match(
    session_id: UUID,
    match_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransferMatchResponse:
    transfer_service = get_transfer_matching_service(db)

    try:
        match = transfer_service.confirm_match(session_id, match_id)
    except TransferSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except TransferMatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _transfer_match_to_response(match)


@transfer_router.post(
    "/sessions/{session_id}/matches/{match_id}/reject",
    response_model=TransferMatchResponse,
)
def reject_transfer_match(
    session_id: UUID,
    match_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransferMatchResponse:
    transfer_service = get_transfer_matching_service(db)

    try:
        match = transfer_service.reject_match(session_id, match_id)
    except TransferSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except TransferMatchNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _transfer_match_to_response(match)


@transfer_router.post(
    "/sessions/{session_id}/close",
    response_model=TransferSessionResponse,
)
def close_transfer_session(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransferSessionResponse:
    transfer_service = get_transfer_matching_service(db)

    try:
        session = transfer_service.close_session(session_id)
    except TransferSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _transfer_session_to_response(session)


@transfer_router.get(
    "/sessions/{session_id}/summary",
    response_model=TransferSummaryResponse,
)
def get_transfer_summary(
    session_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransferSummaryResponse:
    transfer_service = get_transfer_matching_service(db)

    try:
        summary = transfer_service.get_summary(session_id)
    except TransferSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return TransferSummaryResponse(
        total_matches=summary.total_matches,
        pending_count=summary.pending_count,
        confirmed_count=summary.confirmed_count,
        rejected_count=summary.rejected_count,
        total_confirmed_amount=str(summary.total_confirmed_amount),
    )


# QSBS Endpoints
def get_qsbs_service(db: SQLiteDatabase) -> QSBSService:
    security_repo = SQLiteSecurityRepository(db)
    position_repo = SQLitePositionRepository(db)
    tax_lot_repo = SQLiteTaxLotRepository(db)
    return QSBSService(
        security_repo=security_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
    )


def _security_to_response(security: Any) -> SecurityResponse:
    return SecurityResponse(
        id=security.id,
        symbol=security.symbol,
        name=security.name,
        cusip=security.cusip,
        isin=security.isin,
        asset_class=security.asset_class.value,
        is_qsbs_eligible=security.is_qsbs_eligible,
        qsbs_qualification_date=security.qsbs_qualification_date,
        issuer=security.issuer,
        is_active=security.is_active,
    )


@qsbs_router.get("/securities", response_model=list[SecurityResponse])
def list_qsbs_eligible_securities(
    db: Annotated[SQLiteDatabase, Depends()],
) -> list[SecurityResponse]:
    qsbs_service = get_qsbs_service(db)
    securities = qsbs_service.list_qsbs_eligible_securities()
    return [_security_to_response(s) for s in securities]


@qsbs_router.post(
    "/securities/{security_id}/mark-eligible",
    response_model=SecurityResponse,
)
def mark_security_qsbs_eligible(
    security_id: UUID,
    payload: MarkQSBSRequest,
    db: Annotated[SQLiteDatabase, Depends()],
) -> SecurityResponse:
    qsbs_service = get_qsbs_service(db)

    try:
        security = qsbs_service.mark_security_qsbs_eligible(
            security_id=security_id,
            qualification_date=payload.qualification_date,
        )
    except SecurityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _security_to_response(security)


@qsbs_router.post(
    "/securities/{security_id}/remove-eligible",
    response_model=SecurityResponse,
)
def remove_security_qsbs_eligibility(
    security_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> SecurityResponse:
    qsbs_service = get_qsbs_service(db)

    try:
        security = qsbs_service.remove_qsbs_eligibility(security_id)
    except SecurityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _security_to_response(security)


@qsbs_router.get("/summary", response_model=QSBSSummaryResponse)
def get_qsbs_summary(
    db: Annotated[SQLiteDatabase, Depends()],
    as_of_date: date | None = Query(default=None),
    entity_ids: list[UUID] | None = Query(default=None),
) -> QSBSSummaryResponse:
    qsbs_service = get_qsbs_service(db)

    summary = qsbs_service.get_qsbs_summary(
        entity_ids=entity_ids,
        as_of_date=as_of_date,
    )

    holdings = [
        QSBSHoldingResponse(
            security_id=h.security_id,
            security_symbol=h.security_symbol,
            security_name=h.security_name,
            position_id=h.position_id,
            acquisition_date=h.acquisition_date,
            quantity=str(h.quantity),
            cost_basis=str(h.cost_basis),
            holding_period_days=h.holding_period_days,
            is_qualified=h.is_qualified,
            days_until_qualified=h.days_until_qualified,
            potential_exclusion=str(h.potential_exclusion),
            issuer=h.issuer,
        )
        for h in summary.holdings
    ]

    return QSBSSummaryResponse(
        total_qsbs_holdings=summary.total_qsbs_holdings,
        qualified_holdings=summary.qualified_holdings,
        pending_holdings=summary.pending_holdings,
        total_cost_basis=str(summary.total_cost_basis),
        total_potential_exclusion=str(summary.total_potential_exclusion),
        holdings=holdings,
    )


def get_tax_document_service(db: SQLiteDatabase) -> TaxDocumentService:
    entity_repo = SQLiteEntityRepository(db)
    position_repo = SQLitePositionRepository(db)
    tax_lot_repo = SQLiteTaxLotRepository(db)
    security_repo = SQLiteSecurityRepository(db)
    return TaxDocumentService(
        entity_repo=entity_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        security_repo=security_repo,
    )


def _form8949_entry_to_response(entry: Any) -> Form8949EntryResponse:
    return Form8949EntryResponse(
        description=entry.description,
        date_acquired=entry.date_acquired,
        date_sold=entry.date_sold,
        proceeds=str(entry.proceeds.amount),
        cost_basis=str(entry.cost_basis.amount),
        adjustment_code=entry.adjustment_code.value if entry.adjustment_code else None,
        adjustment_amount=str(entry.adjustment_amount.amount)
        if entry.adjustment_amount
        else None,
        gain_or_loss=str(entry.gain_or_loss.amount),
        is_long_term=entry.is_long_term,
        box=entry.box.value,
    )


def _form8949_part_to_response(part: Any) -> Form8949PartResponse:
    return Form8949PartResponse(
        box=part.box.value,
        entries=[_form8949_entry_to_response(e) for e in part.entries],
        total_proceeds=str(part.total_proceeds.amount),
        total_cost_basis=str(part.total_cost_basis.amount),
        total_adjustments=str(part.total_adjustments.amount),
        total_gain_or_loss=str(part.total_gain_or_loss.amount),
    )


def _form8949_to_response(form: Any) -> Form8949Response:
    return Form8949Response(
        tax_year=form.tax_year,
        taxpayer_name=form.taxpayer_name,
        short_term_parts=[_form8949_part_to_response(p) for p in form.short_term_parts],
        long_term_parts=[_form8949_part_to_response(p) for p in form.long_term_parts],
        total_short_term_proceeds=str(form.total_short_term_proceeds.amount),
        total_short_term_cost_basis=str(form.total_short_term_cost_basis.amount),
        total_short_term_gain_or_loss=str(form.total_short_term_gain_or_loss.amount),
        total_long_term_proceeds=str(form.total_long_term_proceeds.amount),
        total_long_term_cost_basis=str(form.total_long_term_cost_basis.amount),
        total_long_term_gain_or_loss=str(form.total_long_term_gain_or_loss.amount),
    )


def _schedule_d_to_response(schedule: Any) -> ScheduleDResponse:
    return ScheduleDResponse(
        tax_year=schedule.tax_year,
        taxpayer_name=schedule.taxpayer_name,
        line_1a_box_a=str(schedule.line_1a.amount),
        line_1b_box_b=str(schedule.line_1b.amount),
        line_1c_box_c=str(schedule.line_1c.amount),
        line_7_net_short_term=str(schedule.line_7.amount),
        line_8a_box_d=str(schedule.line_8a.amount),
        line_8b_box_e=str(schedule.line_8b.amount),
        line_8c_box_f=str(schedule.line_8c.amount),
        line_15_net_long_term=str(schedule.line_15.amount),
        line_16_combined=str(schedule.line_16.amount),
    )


def _tax_summary_to_response(summary: Any) -> TaxDocumentSummaryResponse:
    return TaxDocumentSummaryResponse(
        tax_year=summary.tax_year,
        entity_name=summary.entity_name,
        short_term_transactions=summary.short_term_transactions,
        long_term_transactions=summary.long_term_transactions,
        total_short_term_proceeds=str(summary.total_short_term_proceeds.amount),
        total_short_term_cost_basis=str(summary.total_short_term_cost_basis.amount),
        total_short_term_gain=str(summary.total_short_term_gain.amount),
        total_long_term_proceeds=str(summary.total_long_term_proceeds.amount),
        total_long_term_cost_basis=str(summary.total_long_term_cost_basis.amount),
        total_long_term_gain=str(summary.total_long_term_gain.amount),
        wash_sale_adjustments=str(summary.wash_sale_adjustments.amount),
        net_capital_gain=str(summary.net_capital_gain.amount),
    )


@tax_router.post(
    "/entities/{entity_id}/documents",
    response_model=TaxDocumentsResponse,
)
def generate_tax_documents(
    entity_id: UUID,
    payload: GenerateTaxDocumentsRequest,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TaxDocumentsResponse:
    tax_service = get_tax_document_service(db)

    lot_proceeds: dict[UUID, Money] | None = None
    if payload.lot_proceeds:
        lot_proceeds = {
            UUID(lot_id): Money(Decimal(amount), "USD")
            for lot_id, amount in payload.lot_proceeds.items()
        }

    try:
        form_8949, schedule_d, summary = tax_service.generate_from_entity(
            entity_id=entity_id,
            tax_year=payload.tax_year,
            lot_proceeds=lot_proceeds,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return TaxDocumentsResponse(
        form_8949=_form8949_to_response(form_8949),
        schedule_d=_schedule_d_to_response(schedule_d),
        summary=_tax_summary_to_response(summary),
    )


@tax_router.get(
    "/entities/{entity_id}/summary",
    response_model=TaxDocumentSummaryResponse,
)
def get_tax_summary(
    entity_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
    tax_year: int = Query(..., ge=2000, le=2100),
) -> TaxDocumentSummaryResponse:
    tax_service = get_tax_document_service(db)

    try:
        summary = tax_service.get_tax_document_summary(
            entity_id=entity_id,
            tax_year=tax_year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _tax_summary_to_response(summary)


@tax_router.get(
    "/entities/{entity_id}/form-8949/csv",
)
def export_form_8949_csv(
    entity_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
    tax_year: int = Query(..., ge=2000, le=2100),
) -> Any:
    from fastapi.responses import Response

    tax_service = get_tax_document_service(db)

    try:
        form_8949, _, _ = tax_service.generate_from_entity(
            entity_id=entity_id,
            tax_year=tax_year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    csv_content = tax_service.export_form_8949_csv(form_8949)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=form_8949_{tax_year}.csv"
        },
    )


@tax_router.get(
    "/entities/{entity_id}/schedule-d",
    response_model=ScheduleDResponse,
)
def get_schedule_d(
    entity_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
    tax_year: int = Query(..., ge=2000, le=2100),
) -> ScheduleDResponse:
    tax_service = get_tax_document_service(db)

    try:
        form_8949, _, _ = tax_service.generate_from_entity(
            entity_id=entity_id,
            tax_year=tax_year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    schedule_d = tax_service.generate_schedule_d(form_8949)
    return _schedule_d_to_response(schedule_d)


def get_portfolio_analytics_service(db: SQLiteDatabase) -> PortfolioAnalyticsService:
    entity_repo = SQLiteEntityRepository(db)
    position_repo = SQLitePositionRepository(db)
    security_repo = SQLiteSecurityRepository(db)
    return PortfolioAnalyticsService(
        entity_repo=entity_repo,
        position_repo=position_repo,
        security_repo=security_repo,
    )


@portfolio_router.get(
    "/allocation",
    response_model=AssetAllocationReportResponse,
)
def get_asset_allocation(
    db: Annotated[SQLiteDatabase, Depends()],
    entity_ids: list[UUID] | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
) -> AssetAllocationReportResponse:
    from datetime import date as dt_date

    service = get_portfolio_analytics_service(db)
    effective_date = as_of_date or dt_date.today()

    report = service.asset_allocation_report(
        entity_ids=entity_ids,
        as_of_date=effective_date,
    )

    return AssetAllocationReportResponse(
        as_of_date=report.as_of_date,
        entity_names=report.entity_names,
        allocations=[
            AssetAllocationResponse(
                asset_class=a.asset_class.value,
                market_value=str(a.market_value.amount),
                cost_basis=str(a.cost_basis.amount),
                unrealized_gain=str(a.unrealized_gain.amount),
                allocation_percent=str(a.allocation_percent),
                position_count=a.position_count,
            )
            for a in report.allocations
        ],
        total_market_value=str(report.total_market_value.amount),
        total_cost_basis=str(report.total_cost_basis.amount),
        total_unrealized_gain=str(report.total_unrealized_gain.amount),
    )


@portfolio_router.get(
    "/concentration",
    response_model=ConcentrationReportResponse,
)
def get_concentration_report(
    db: Annotated[SQLiteDatabase, Depends()],
    entity_ids: list[UUID] | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    top_n: int = Query(default=20, ge=1, le=100),
) -> ConcentrationReportResponse:
    from datetime import date as dt_date

    service = get_portfolio_analytics_service(db)
    effective_date = as_of_date or dt_date.today()

    report = service.concentration_report(
        entity_ids=entity_ids,
        as_of_date=effective_date,
        top_n=top_n,
    )

    return ConcentrationReportResponse(
        as_of_date=report.as_of_date,
        entity_names=report.entity_names,
        holdings=[
            HoldingConcentrationResponse(
                security_id=h.security_id,
                security_symbol=h.security_symbol,
                security_name=h.security_name,
                asset_class=h.asset_class.value,
                market_value=str(h.market_value.amount),
                cost_basis=str(h.cost_basis.amount),
                unrealized_gain=str(h.unrealized_gain.amount),
                concentration_percent=str(h.concentration_percent),
                position_count=h.position_count,
            )
            for h in report.holdings
        ],
        total_market_value=str(report.total_market_value.amount),
        top_5_concentration=str(report.top_5_concentration),
        top_10_concentration=str(report.top_10_concentration),
        largest_single_holding=str(report.largest_single_holding),
    )


@portfolio_router.get(
    "/performance",
    response_model=PerformanceReportResponse,
)
def get_performance_report(
    db: Annotated[SQLiteDatabase, Depends()],
    start_date: date = Query(...),
    end_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> PerformanceReportResponse:
    service = get_portfolio_analytics_service(db)

    report = service.performance_report(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
    )

    return PerformanceReportResponse(
        start_date=report.start_date,
        end_date=report.end_date,
        entity_names=report.entity_names,
        metrics=[
            PerformanceMetricsResponse(
                entity_name=m.entity_name,
                start_value=str(m.start_value.amount),
                end_value=str(m.end_value.amount),
                net_contributions=str(m.net_contributions.amount),
                total_return_amount=str(m.total_return_amount.amount),
                total_return_percent=str(m.total_return_percent),
                unrealized_gain=str(m.unrealized_gain.amount),
                unrealized_gain_percent=str(m.unrealized_gain_percent),
            )
            for m in report.metrics
        ],
        portfolio_total_return_amount=str(report.portfolio_total_return_amount.amount),
        portfolio_total_return_percent=str(report.portfolio_total_return_percent),
    )


@portfolio_router.get(
    "/summary",
    response_model=PortfolioSummaryResponse,
)
def get_portfolio_summary(
    db: Annotated[SQLiteDatabase, Depends()],
    entity_ids: list[UUID] | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
) -> PortfolioSummaryResponse:
    from datetime import date as dt_date

    service = get_portfolio_analytics_service(db)
    effective_date = as_of_date or dt_date.today()

    summary = service.get_portfolio_summary(
        entity_ids=entity_ids,
        as_of_date=effective_date,
    )

    return PortfolioSummaryResponse(
        as_of_date=effective_date,
        total_market_value=summary["total_market_value"],
        total_cost_basis=summary["total_cost_basis"],
        total_unrealized_gain=summary["total_unrealized_gain"],
        asset_allocation=summary["asset_allocation"],
        top_holdings=summary["top_holdings"],
        concentration_metrics=summary["concentration_metrics"],
    )


def get_audit_service(db: SQLiteDatabase) -> AuditService:
    return AuditService(db)


def _audit_entry_to_response(entry: Any) -> AuditEntryResponse:
    return AuditEntryResponse(
        id=entry.id,
        entity_type=entry.entity_type.value,
        entity_id=entry.entity_id,
        action=entry.action.value,
        user_id=entry.user_id,
        timestamp=entry.timestamp,
        old_values=entry.old_values,
        new_values=entry.new_values,
        change_summary=entry.change_summary,
        ip_address=entry.ip_address,
        user_agent=entry.user_agent,
    )


@audit_router.get(
    "/entries",
    response_model=AuditListResponse,
)
def list_audit_entries(
    db: Annotated[SQLiteDatabase, Depends()],
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> AuditListResponse:
    service = get_audit_service(db)

    if entity_type:
        entries = service.list_by_entity_type(
            AuditEntityType(entity_type),
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
    elif action:
        entries = service.list_by_action(
            AuditAction(action),
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
    else:
        entries = service.list_recent(limit=limit, offset=offset)

    return AuditListResponse(
        entries=[_audit_entry_to_response(e) for e in entries],
        total=len(entries),
    )


@audit_router.get(
    "/entries/{entry_id}",
    response_model=AuditEntryResponse,
)
def get_audit_entry(
    entry_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> AuditEntryResponse:
    service = get_audit_service(db)

    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit entry not found",
        )

    return _audit_entry_to_response(entry)


@audit_router.get(
    "/entities/{entity_type}/{entity_id}",
    response_model=AuditListResponse,
)
def list_entity_audit_trail(
    entity_type: str,
    entity_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> AuditListResponse:
    service = get_audit_service(db)

    entries = service.list_by_entity(
        AuditEntityType(entity_type),
        entity_id,
        limit=limit,
        offset=offset,
    )

    return AuditListResponse(
        entries=[_audit_entry_to_response(e) for e in entries],
        total=len(entries),
    )


@audit_router.get(
    "/summary",
    response_model=AuditSummaryResponse,
)
def get_audit_summary(
    db: Annotated[SQLiteDatabase, Depends()],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> AuditSummaryResponse:
    service = get_audit_service(db)

    summary = service.get_summary(start_date=start_date, end_date=end_date)

    return AuditSummaryResponse(
        total_entries=summary.total_entries,
        entries_by_action={k.value: v for k, v in summary.entries_by_action.items()},
        entries_by_entity_type={
            k.value: v for k, v in summary.entries_by_entity_type.items()
        },
        oldest_entry=summary.oldest_entry,
        newest_entry=summary.newest_entry,
    )


def get_currency_service(db: SQLiteDatabase) -> CurrencyServiceImpl:
    repo = SQLiteExchangeRateRepository(db)
    return CurrencyServiceImpl(repo)


def _exchange_rate_to_response(rate: ExchangeRate) -> ExchangeRateResponse:
    return ExchangeRateResponse(
        id=rate.id,
        from_currency=rate.from_currency,
        to_currency=rate.to_currency,
        rate=str(rate.rate),
        effective_date=rate.effective_date,
        source=rate.source.value,
        created_at=rate.created_at,
    )


@currency_router.post(
    "/rates",
    response_model=ExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_exchange_rate(
    payload: ExchangeRateCreate,
    db: Annotated[SQLiteDatabase, Depends()],
) -> ExchangeRateResponse:
    currency_service = get_currency_service(db)

    rate = ExchangeRate(
        from_currency=payload.from_currency,
        to_currency=payload.to_currency,
        rate=Decimal(payload.rate),
        effective_date=payload.effective_date,
        source=ExchangeRateSource(payload.source),
    )

    currency_service.add_rate(rate)
    return _exchange_rate_to_response(rate)


@currency_router.get(
    "/rates",
    response_model=ExchangeRateListResponse,
)
def list_exchange_rates(
    db: Annotated[SQLiteDatabase, Depends()],
    from_currency: str | None = Query(default=None, min_length=3, max_length=3),
    to_currency: str | None = Query(default=None, min_length=3, max_length=3),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> ExchangeRateListResponse:
    repo = SQLiteExchangeRateRepository(db)

    if from_currency and to_currency:
        rates = list(
            repo.list_by_currency_pair(
                from_currency, to_currency, start_date=start_date, end_date=end_date
            )
        )
    elif start_date:
        rates = list(repo.list_by_date(start_date))
    else:
        rates = []

    return ExchangeRateListResponse(
        rates=[_exchange_rate_to_response(r) for r in rates],
        total=len(rates),
    )


@currency_router.get(
    "/rates/latest",
    response_model=ExchangeRateResponse,
)
def get_latest_exchange_rate(
    db: Annotated[SQLiteDatabase, Depends()],
    from_currency: str = Query(..., min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
) -> ExchangeRateResponse:
    currency_service = get_currency_service(db)

    rate = currency_service.get_latest_rate(from_currency, to_currency)
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exchange rate found for {from_currency}/{to_currency}",
        )

    return _exchange_rate_to_response(rate)


@currency_router.get(
    "/rates/{rate_id}",
    response_model=ExchangeRateResponse,
)
def get_exchange_rate(
    rate_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> ExchangeRateResponse:
    repo = SQLiteExchangeRateRepository(db)

    rate = repo.get(rate_id)
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exchange rate {rate_id} not found",
        )

    return _exchange_rate_to_response(rate)


@currency_router.delete(
    "/rates/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_exchange_rate(
    rate_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> None:
    repo = SQLiteExchangeRateRepository(db)

    rate = repo.get(rate_id)
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exchange rate {rate_id} not found",
        )

    repo.delete(rate_id)


@currency_router.post(
    "/convert",
    response_model=CurrencyConvertResponse,
)
def convert_currency(
    payload: CurrencyConvertRequest,
    db: Annotated[SQLiteDatabase, Depends()],
) -> CurrencyConvertResponse:
    currency_service = get_currency_service(db)

    original = Money(Decimal(payload.amount), payload.from_currency)

    try:
        converted = currency_service.convert(
            original, payload.to_currency, payload.as_of_date
        )
    except ExchangeRateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    rate = currency_service.get_rate(
        payload.from_currency, payload.to_currency, payload.as_of_date
    )
    rate_str = str(rate.rate) if rate else "inverse"

    return CurrencyConvertResponse(
        original_amount=payload.amount,
        original_currency=payload.from_currency,
        converted_amount=str(converted.amount),
        converted_currency=payload.to_currency,
        rate_used=rate_str,
        as_of_date=payload.as_of_date,
    )


def get_expense_service(db: SQLiteDatabase) -> ExpenseServiceImpl:
    transaction_repo = SQLiteTransactionRepository(db)
    account_repo = SQLiteAccountRepository(db)
    vendor_repo = SQLiteVendorRepository(db)
    return ExpenseServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        vendor_repo=vendor_repo,
    )


def get_vendor_repository(db: SQLiteDatabase) -> SQLiteVendorRepository:
    return SQLiteVendorRepository(db)


def _vendor_to_response(vendor: Vendor) -> VendorResponse:
    return VendorResponse(
        id=vendor.id,
        name=vendor.name,
        category=vendor.category,
        tax_id=vendor.tax_id,
        is_1099_eligible=vendor.is_1099_eligible,
        is_active=vendor.is_active,
        contact_email=vendor.contact_email,
        contact_phone=vendor.contact_phone,
        notes=vendor.notes,
        created_at=vendor.created_at,
    )


@vendor_router.post(
    "",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor(
    payload: VendorCreate,
    db: Annotated[SQLiteDatabase, Depends()],
) -> VendorResponse:
    vendor_repo = get_vendor_repository(db)

    vendor = Vendor(
        name=payload.name,
        category=payload.category,
        tax_id=payload.tax_id,
        is_1099_eligible=payload.is_1099_eligible,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        notes=payload.notes,
    )

    vendor_repo.add(vendor)
    return _vendor_to_response(vendor)


@vendor_router.get("", response_model=VendorListResponse)
def list_vendors(
    db: Annotated[SQLiteDatabase, Depends()],
    include_inactive: bool = Query(default=False),
) -> VendorListResponse:
    vendor_repo = get_vendor_repository(db)
    vendors = list(vendor_repo.list_all(include_inactive=include_inactive))
    return VendorListResponse(
        vendors=[_vendor_to_response(v) for v in vendors],
        total=len(vendors),
    )


@vendor_router.get("/search", response_model=VendorListResponse)
def search_vendors(
    db: Annotated[SQLiteDatabase, Depends()],
    name: str = Query(..., min_length=1),
) -> VendorListResponse:
    vendor_repo = get_vendor_repository(db)
    vendors = list(vendor_repo.search_by_name(name))
    return VendorListResponse(
        vendors=[_vendor_to_response(v) for v in vendors],
        total=len(vendors),
    )


@vendor_router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> VendorResponse:
    vendor_repo = get_vendor_repository(db)
    vendor = vendor_repo.get(vendor_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found",
        )
    return _vendor_to_response(vendor)


@vendor_router.put("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: UUID,
    payload: VendorUpdate,
    db: Annotated[SQLiteDatabase, Depends()],
) -> VendorResponse:
    vendor_repo = get_vendor_repository(db)
    vendor = vendor_repo.get(vendor_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found",
        )

    if payload.name is not None:
        vendor.name = payload.name
    if payload.category is not None:
        vendor.category = payload.category
    if payload.tax_id is not None:
        vendor.tax_id = payload.tax_id
    if payload.is_1099_eligible is not None:
        vendor.is_1099_eligible = payload.is_1099_eligible
    if payload.contact_email is not None:
        vendor.contact_email = payload.contact_email
    if payload.contact_phone is not None:
        vendor.contact_phone = payload.contact_phone
    if payload.notes is not None:
        vendor.notes = payload.notes

    vendor_repo.update(vendor)
    return _vendor_to_response(vendor)


@vendor_router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(
    vendor_id: UUID,
    db: Annotated[SQLiteDatabase, Depends()],
) -> None:
    vendor_repo = get_vendor_repository(db)
    vendor = vendor_repo.get(vendor_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found",
        )
    vendor_repo.delete(vendor_id)


@expense_router.post(
    "/transactions/{txn_id}/categorize",
    response_model=TransactionResponse,
)
def categorize_transaction(
    txn_id: UUID,
    payload: CategorizeTransactionRequest,
    db: Annotated[SQLiteDatabase, Depends()],
) -> TransactionResponse:
    expense_service = get_expense_service(db)

    try:
        txn = expense_service.categorize_transaction(
            transaction_id=txn_id,
            category=payload.category,
            tags=payload.tags,
            vendor_id=payload.vendor_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return _transaction_to_response(txn)


@expense_router.get("/summary", response_model=ExpenseSummaryResponse)
def get_expense_summary(
    db: Annotated[SQLiteDatabase, Depends()],
    start_date: date = Query(...),
    end_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> ExpenseSummaryResponse:
    expense_service = get_expense_service(db)

    summary = expense_service.get_expense_summary(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
    )

    by_category = expense_service.get_expenses_by_category(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
    )

    return ExpenseSummaryResponse(
        total_expenses=str(summary["total_expenses"]),
        transaction_count=summary["transaction_count"],
        category_breakdown={
            cat: str(amount.amount) for cat, amount in by_category.items()
        },
        start_date=start_date,
        end_date=end_date,
    )


@expense_router.get("/by-category", response_model=ExpenseByCategoryResponse)
def get_expenses_by_category(
    db: Annotated[SQLiteDatabase, Depends()],
    start_date: date = Query(...),
    end_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> ExpenseByCategoryResponse:
    expense_service = get_expense_service(db)

    by_category = expense_service.get_expenses_by_category(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
    )

    total = sum((m.amount for m in by_category.values()), Decimal("0"))

    return ExpenseByCategoryResponse(
        categories={cat: str(amount.amount) for cat, amount in by_category.items()},
        total=str(total),
    )


@expense_router.get("/by-vendor", response_model=ExpenseByVendorResponse)
def get_expenses_by_vendor(
    db: Annotated[SQLiteDatabase, Depends()],
    start_date: date = Query(...),
    end_date: date = Query(...),
    entity_ids: list[UUID] | None = Query(default=None),
) -> ExpenseByVendorResponse:
    expense_service = get_expense_service(db)

    by_vendor = expense_service.get_expenses_by_vendor(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
    )

    total = sum((m.amount for m in by_vendor.values()), Decimal("0"))

    return ExpenseByVendorResponse(
        vendors={str(vid): str(amount.amount) for vid, amount in by_vendor.items()},
        total=str(total),
    )


@expense_router.get("/recurring", response_model=RecurringExpenseListResponse)
def get_recurring_expenses(
    db: Annotated[SQLiteDatabase, Depends()],
    entity_id: UUID = Query(...),
    lookback_months: int = Query(default=3, ge=1, le=24),
) -> RecurringExpenseListResponse:
    expense_service = get_expense_service(db)

    recurring = expense_service.detect_recurring_expenses(
        entity_id=entity_id,
        lookback_months=lookback_months,
    )

    return RecurringExpenseListResponse(
        recurring_expenses=[
            RecurringExpenseResponse(
                vendor_id=r["vendor_id"],
                frequency=r["frequency"],
                amount=str(r["amount"].amount),
                occurrence_count=r["occurrence_count"],
                last_date=r["last_date"],
            )
            for r in recurring
        ],
        total=len(recurring),
    )
