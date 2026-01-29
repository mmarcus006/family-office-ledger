"""API routes for Family Office Ledger."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from family_office_ledger.api.schemas import (
    AccountCreate,
    AccountResponse,
    BalanceSheetResponse,
    CreateSessionRequest,
    CreateTransferSessionRequest,
    EntityCreate,
    EntityResponse,
    EntryResponse,
    HealthResponse,
    MatchListResponse,
    MatchResponse,
    ReportResponse,
    SessionResponse,
    SessionSummaryResponse,
    TransactionCreate,
    TransactionResponse,
    TransferMatchListResponse,
    TransferMatchResponse,
    TransferSessionResponse,
    TransferSummaryResponse,
)
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.reconciliation import (
    ReconciliationMatch,
    ReconciliationMatchStatus,
    ReconciliationSession,
)
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    Money,
)
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    ReconciliationSessionRepository,
    TransactionRepository,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteReconciliationSessionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.interfaces import LedgerService, ReportingService
from family_office_ledger.services.ledger import (
    LedgerServiceImpl,
    UnbalancedTransactionError,
)
from family_office_ledger.services.reconciliation import (
    MatchNotFoundError,
    ReconciliationServiceImpl,
    SessionExistsError,
    SessionNotFoundError,
)
from family_office_ledger.services.reporting import ReportingServiceImpl
from family_office_ledger.services.transfer_matching import (
    TransferMatchingService,
    TransferMatchNotFoundError,
    TransferSessionNotFoundError,
)
from family_office_ledger.domain.transfer_matching import (
    TransferMatch,
    TransferMatchingSession,
    TransferMatchStatus,
)

# Create routers
health_router = APIRouter(tags=["health"])
entity_router = APIRouter(prefix="/entities", tags=["entities"])
account_router = APIRouter(prefix="/accounts", tags=["accounts"])
transaction_router = APIRouter(prefix="/transactions", tags=["transactions"])
report_router = APIRouter(prefix="/reports", tags=["reports"])
reconciliation_router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])
transfer_router = APIRouter(prefix="/transfers", tags=["transfers"])


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


def _entry_to_response(entry: Entry) -> EntryResponse:
    """Convert Entry domain object to response schema."""
    return EntryResponse(
        id=entry.id,
        account_id=entry.account_id,
        debit_amount=str(entry.debit_amount.amount),
        credit_amount=str(entry.credit_amount.amount),
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
            debit_amount=Money(Decimal(entry_data.debit_amount)),
            credit_amount=Money(Decimal(entry_data.credit_amount)),
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
        if isinstance(value, Decimal):
            serialized[key] = str(value)
        elif isinstance(value, UUID):
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
            if isinstance(value, Decimal):
                serialized_item[key] = str(value)
            elif isinstance(value, UUID):
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
