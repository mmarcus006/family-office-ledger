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
    EntityCreate,
    EntityResponse,
    EntryResponse,
    HealthResponse,
    ReportResponse,
    TransactionCreate,
    TransactionResponse,
)
from family_office_ledger.domain.entities import Account, Entity
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
    TransactionRepository,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.interfaces import LedgerService, ReportingService
from family_office_ledger.services.ledger import (
    LedgerServiceImpl,
    UnbalancedTransactionError,
)
from family_office_ledger.services.reporting import ReportingServiceImpl

# Create routers
health_router = APIRouter(tags=["health"])
entity_router = APIRouter(prefix="/entities", tags=["entities"])
account_router = APIRouter(prefix="/accounts", tags=["accounts"])
transaction_router = APIRouter(prefix="/transactions", tags=["transactions"])
report_router = APIRouter(prefix="/reports", tags=["reports"])


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
