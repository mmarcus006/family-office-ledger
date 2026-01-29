"""Tests for transfer matching service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.transfer_matching import TransferMatchStatus
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    Money,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.transfer_matching import (
    TransferMatchingService,
    TransferMatchNotFoundError,
    TransferSessionNotFoundError,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def entity_repo(db: SQLiteDatabase) -> SQLiteEntityRepository:
    return SQLiteEntityRepository(db)


@pytest.fixture
def account_repo(db: SQLiteDatabase) -> SQLiteAccountRepository:
    return SQLiteAccountRepository(db)


@pytest.fixture
def transaction_repo(db: SQLiteDatabase) -> SQLiteTransactionRepository:
    return SQLiteTransactionRepository(db)


@pytest.fixture
def entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Test Entity",
        entity_type=EntityType.INDIVIDUAL,
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def checking_account(account_repo: SQLiteAccountRepository, entity: Entity) -> Account:
    account = Account(
        name="Checking",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def savings_account(account_repo: SQLiteAccountRepository, entity: Entity) -> Account:
    account = Account(
        name="Savings",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.SAVINGS,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def service(
    transaction_repo: SQLiteTransactionRepository,
    account_repo: SQLiteAccountRepository,
) -> TransferMatchingService:
    return TransferMatchingService(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
    )


class TestTransferMatchingSessionCreate:
    def test_create_session_returns_session_id(
        self,
        service: TransferMatchingService,
    ):
        session = service.create_session()
        assert session.id is not None

    def test_create_session_with_date_range(
        self,
        service: TransferMatchingService,
    ):
        session = service.create_session(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            date_tolerance_days=5,
        )
        assert session.date_tolerance_days == 5

    def test_create_session_with_entity_filter(
        self,
        service: TransferMatchingService,
        entity: Entity,
    ):
        session = service.create_session(entity_ids=[entity.id])
        assert entity.id in session.entity_ids


class TestTransferMatchingPairing:
    def test_matches_equal_opposite_transactions(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        outflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=checking_account.id,
                    debit_amount=Money(Decimal("1000")),
                )
            ],
            memo="Transfer to savings",
        )
        transaction_repo.add(outflow)

        inflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=savings_account.id,
                    credit_amount=Money(Decimal("1000")),
                )
            ],
            memo="Transfer from checking",
        )
        transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )

        assert len(session.matches) == 1
        match = session.matches[0]
        assert match.amount == Decimal("1000")
        assert match.source_account_id == checking_account.id
        assert match.target_account_id == savings_account.id

    def test_matches_within_date_tolerance(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        outflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=checking_account.id,
                    debit_amount=Money(Decimal("500")),
                )
            ],
        )
        transaction_repo.add(outflow)

        inflow = Transaction(
            transaction_date=date(2024, 6, 17),
            entries=[
                Entry(
                    account_id=savings_account.id,
                    credit_amount=Money(Decimal("500")),
                )
            ],
        )
        transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
            date_tolerance_days=3,
        )

        assert len(session.matches) == 1

    def test_no_match_outside_date_tolerance(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        outflow = Transaction(
            transaction_date=date(2024, 6, 1),
            entries=[
                Entry(
                    account_id=checking_account.id,
                    debit_amount=Money(Decimal("500")),
                )
            ],
        )
        transaction_repo.add(outflow)

        inflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=savings_account.id,
                    credit_amount=Money(Decimal("500")),
                )
            ],
        )
        transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
            date_tolerance_days=3,
        )

        assert len(session.matches) == 0

    def test_no_match_different_amounts(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        outflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=checking_account.id,
                    debit_amount=Money(Decimal("1000")),
                )
            ],
        )
        transaction_repo.add(outflow)

        inflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=savings_account.id,
                    credit_amount=Money(Decimal("999")),
                )
            ],
        )
        transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )

        assert len(session.matches) == 0


class TestTransferMatchActions:
    def test_confirm_match(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        outflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=checking_account.id,
                    debit_amount=Money(Decimal("1000")),
                )
            ],
        )
        transaction_repo.add(outflow)

        inflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=savings_account.id,
                    credit_amount=Money(Decimal("1000")),
                )
            ],
        )
        transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )
        match_id = session.matches[0].id

        confirmed = service.confirm_match(session.id, match_id)
        assert confirmed.status == TransferMatchStatus.CONFIRMED
        assert confirmed.confirmed_at is not None

    def test_reject_match(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        outflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=checking_account.id,
                    debit_amount=Money(Decimal("1000")),
                )
            ],
        )
        transaction_repo.add(outflow)

        inflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=savings_account.id,
                    credit_amount=Money(Decimal("1000")),
                )
            ],
        )
        transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )
        match_id = session.matches[0].id

        rejected = service.reject_match(session.id, match_id)
        assert rejected.status == TransferMatchStatus.REJECTED


class TestTransferMatchingSession:
    def test_get_session(
        self,
        service: TransferMatchingService,
    ):
        created = service.create_session()
        retrieved = service.get_session(created.id)
        assert retrieved.id == created.id

    def test_get_session_not_found(
        self,
        service: TransferMatchingService,
    ):
        with pytest.raises(TransferSessionNotFoundError):
            service.get_session(uuid4())

    def test_close_session(
        self,
        service: TransferMatchingService,
    ):
        session = service.create_session()
        closed = service.close_session(session.id)
        assert closed.status == "completed"
        assert closed.closed_at is not None


class TestTransferMatchingSummary:
    def test_summary_counts(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        for i in range(3):
            outflow = Transaction(
                transaction_date=date(2024, 6, 15 + i),
                entries=[
                    Entry(
                        account_id=checking_account.id,
                        debit_amount=Money(Decimal("100") * (i + 1)),
                    )
                ],
            )
            transaction_repo.add(outflow)

            inflow = Transaction(
                transaction_date=date(2024, 6, 15 + i),
                entries=[
                    Entry(
                        account_id=savings_account.id,
                        credit_amount=Money(Decimal("100") * (i + 1)),
                    )
                ],
            )
            transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )

        assert len(session.matches) == 3

        service.confirm_match(session.id, session.matches[0].id)
        service.reject_match(session.id, session.matches[1].id)

        summary = service.get_summary(session.id)
        assert summary.total_matches == 3
        assert summary.confirmed_count == 1
        assert summary.rejected_count == 1
        assert summary.pending_count == 1
        assert summary.total_confirmed_amount == Decimal("100")


class TestTransferMatchListFiltering:
    def test_list_matches_all(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        outflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=checking_account.id,
                    debit_amount=Money(Decimal("1000")),
                )
            ],
        )
        transaction_repo.add(outflow)

        inflow = Transaction(
            transaction_date=date(2024, 6, 15),
            entries=[
                Entry(
                    account_id=savings_account.id,
                    credit_amount=Money(Decimal("1000")),
                )
            ],
        )
        transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )

        matches = service.list_matches(session.id)
        assert len(matches) == 1

    def test_list_matches_by_status(
        self,
        service: TransferMatchingService,
        transaction_repo: SQLiteTransactionRepository,
        checking_account: Account,
        savings_account: Account,
    ):
        for i in range(2):
            outflow = Transaction(
                transaction_date=date(2024, 6, 15 + i),
                entries=[
                    Entry(
                        account_id=checking_account.id,
                        debit_amount=Money(Decimal("100") * (i + 1)),
                    )
                ],
            )
            transaction_repo.add(outflow)

            inflow = Transaction(
                transaction_date=date(2024, 6, 15 + i),
                entries=[
                    Entry(
                        account_id=savings_account.id,
                        credit_amount=Money(Decimal("100") * (i + 1)),
                    )
                ],
            )
            transaction_repo.add(inflow)

        session = service.create_session(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )

        service.confirm_match(session.id, session.matches[0].id)

        pending = service.list_matches(session.id, status=TransferMatchStatus.PENDING)
        assert len(pending) == 1

        confirmed = service.list_matches(
            session.id, status=TransferMatchStatus.CONFIRMED
        )
        assert len(confirmed) == 1


class TestTransferMatchErrors:
    def test_confirm_nonexistent_match(
        self,
        service: TransferMatchingService,
    ):
        session = service.create_session()

        with pytest.raises(TransferMatchNotFoundError):
            service.confirm_match(session.id, uuid4())

    def test_reject_nonexistent_match(
        self,
        service: TransferMatchingService,
    ):
        session = service.create_session()

        with pytest.raises(TransferMatchNotFoundError):
            service.reject_match(session.id, uuid4())
