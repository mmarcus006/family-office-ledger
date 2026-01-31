"""Tests for session-based reconciliation workflow."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.reconciliation import (
    ReconciliationMatchStatus,
    ReconciliationSession,
    ReconciliationSessionStatus,
)
from family_office_ledger.domain.transactions import Entry, Transaction
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
    SQLiteReconciliationSessionRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.reconciliation import (
    MatchNotFoundError,
    ReconciliationServiceImpl,
    SessionExistsError,
    SessionNotFoundError,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
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
def session_repo(db: SQLiteDatabase) -> SQLiteReconciliationSessionRepository:
    return SQLiteReconciliationSessionRepository(db)


@pytest.fixture
def entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Test Entity",
        entity_type=EntityType.INDIVIDUAL,
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def account(account_repo: SQLiteAccountRepository, entity: Entity) -> Account:
    account = Account(
        name="Test Checking",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )
    account_repo.add(account)
    return account


@pytest.fixture
def service(
    transaction_repo: SQLiteTransactionRepository,
    account_repo: SQLiteAccountRepository,
    session_repo: SQLiteReconciliationSessionRepository,
) -> ReconciliationServiceImpl:
    return ReconciliationServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        session_repo=session_repo,
    )


class TestSessionExceptions:
    """Test custom exceptions exist and work correctly."""

    def test_session_exists_error(self):
        """SessionExistsError is raised for duplicate sessions."""
        with pytest.raises(SessionExistsError):
            raise SessionExistsError("Session already exists")

    def test_session_not_found_error(self):
        """SessionNotFoundError is raised for missing sessions."""
        with pytest.raises(SessionNotFoundError):
            raise SessionNotFoundError("Session not found")

    def test_match_not_found_error(self):
        """MatchNotFoundError is raised for missing matches."""
        with pytest.raises(MatchNotFoundError):
            raise MatchNotFoundError("Match not found")


class TestCreateSession:
    """Tests for create_session method."""

    def test_create_session_returns_session(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Can create a reconciliation session."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test payment\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        assert session is not None
        assert isinstance(session, ReconciliationSession)
        assert session.account_id == account.id
        assert session.status == ReconciliationSessionStatus.PENDING

    def test_create_session_parses_and_creates_matches(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Session contains matches for each imported transaction."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n"
            "2026-01-15,100.00,Payment one\n"
            "2026-01-16,200.00,Payment two\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        assert len(session.matches) == 2
        assert session.matches[0].imported_amount == Decimal("100.00")
        assert session.matches[1].imported_amount == Decimal("200.00")

    def test_create_session_raises_if_pending_exists(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Raises SessionExistsError if pending session exists for account."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        with pytest.raises(SessionExistsError):
            service.create_session(
                account_id=account.id,
                file_path=str(csv_file),
                file_format="csv",
            )


class TestGetSession:
    """Tests for get_session method."""

    def test_get_session_returns_session(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Can retrieve a session by ID."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        created = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        retrieved = service.get_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_session_returns_none_for_unknown(
        self, service: ReconciliationServiceImpl
    ):
        """Returns None for unknown session ID."""
        result = service.get_session(uuid4())
        assert result is None


class TestListMatches:
    """Tests for list_matches method."""

    def test_list_matches_returns_all_matches(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Returns all matches for a session."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n"
            "2026-01-15,100.00,One\n"
            "2026-01-16,200.00,Two\n"
            "2026-01-17,300.00,Three\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        matches, total = service.list_matches(session.id)

        assert len(matches) == 3
        assert total == 3

    def test_list_matches_with_pagination(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Supports offset and limit for pagination."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n"
            "2026-01-15,100.00,One\n"
            "2026-01-16,200.00,Two\n"
            "2026-01-17,300.00,Three\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        matches, total = service.list_matches(session.id, limit=2, offset=0)
        assert len(matches) == 2
        assert total == 3

        matches2, total2 = service.list_matches(session.id, limit=2, offset=2)
        assert len(matches2) == 1
        assert total2 == 3

    def test_list_matches_filter_by_status(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Can filter matches by status."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n2026-01-15,100.00,One\n2026-01-16,200.00,Two\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        # Confirm one match
        service.skip_session_match(session.id, session.matches[0].id)

        pending_matches, pending_total = service.list_matches(
            session.id, status=ReconciliationMatchStatus.PENDING
        )
        skipped_matches, skipped_total = service.list_matches(
            session.id, status=ReconciliationMatchStatus.SKIPPED
        )

        assert pending_total == 1
        assert skipped_total == 1

    def test_list_matches_raises_for_unknown_session(
        self, service: ReconciliationServiceImpl
    ):
        """Raises SessionNotFoundError for unknown session."""
        with pytest.raises(SessionNotFoundError):
            service.list_matches(uuid4())


class TestConfirmSessionMatch:
    """Tests for confirm_session_match method."""

    def test_confirm_match_updates_status(
        self,
        service: ReconciliationServiceImpl,
        account: Account,
        transaction_repo: SQLiteTransactionRepository,
        tmp_path,
    ):
        """Confirming a match updates its status to CONFIRMED."""
        # Create a ledger transaction
        txn = Transaction(
            transaction_date=date(2026, 1, 15),
            entries=[
                Entry(
                    account_id=account.id,
                    debit_amount=Money(Decimal("100.00"), "USD"),
                ),
                Entry(
                    account_id=account.id,
                    credit_amount=Money(Decimal("100.00"), "USD"),
                ),
            ],
        )
        transaction_repo.add(txn)

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        match = session.matches[0]
        assert match.suggested_ledger_txn_id is not None

        confirmed = service.confirm_session_match(session.id, match.id)

        assert confirmed.status == ReconciliationMatchStatus.CONFIRMED
        assert confirmed.actioned_at is not None

    def test_confirm_match_without_suggestion_raises(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Cannot confirm a match without a suggested ledger transaction."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        match = session.matches[0]
        # No ledger transactions exist, so no suggestion

        with pytest.raises(MatchNotFoundError) as exc_info:
            service.confirm_session_match(session.id, match.id)

        assert "no suggested ledger transaction" in str(exc_info.value).lower()

    def test_confirm_match_raises_for_unknown_session(
        self, service: ReconciliationServiceImpl
    ):
        """Raises SessionNotFoundError for unknown session."""
        with pytest.raises(SessionNotFoundError):
            service.confirm_session_match(uuid4(), uuid4())

    def test_confirm_match_raises_for_unknown_match(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Raises MatchNotFoundError for unknown match ID."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        with pytest.raises(MatchNotFoundError):
            service.confirm_session_match(session.id, uuid4())


class TestRejectSessionMatch:
    """Tests for reject_session_match method."""

    def test_reject_match_updates_status(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Rejecting a match updates its status to REJECTED."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        match = session.matches[0]
        rejected = service.reject_session_match(session.id, match.id)

        assert rejected.status == ReconciliationMatchStatus.REJECTED
        assert rejected.actioned_at is not None

    def test_reject_match_raises_for_unknown_session(
        self, service: ReconciliationServiceImpl
    ):
        """Raises SessionNotFoundError for unknown session."""
        with pytest.raises(SessionNotFoundError):
            service.reject_session_match(uuid4(), uuid4())


class TestSkipSessionMatch:
    """Tests for skip_session_match method."""

    def test_skip_match_updates_status(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Skipping a match updates its status to SKIPPED."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        match = session.matches[0]
        skipped = service.skip_session_match(session.id, match.id)

        assert skipped.status == ReconciliationMatchStatus.SKIPPED
        assert skipped.actioned_at is not None


class TestAutoCloseSession:
    """Tests for auto-close behavior."""

    def test_auto_close_when_all_confirmed_or_rejected(
        self,
        service: ReconciliationServiceImpl,
        account: Account,
        transaction_repo: SQLiteTransactionRepository,
        tmp_path,
    ):
        """Session auto-closes when all matches are CONFIRMED or REJECTED."""
        txn = Transaction(
            transaction_date=date(2026, 1, 15),
            entries=[
                Entry(
                    account_id=account.id,
                    debit_amount=Money(Decimal("100.00"), "USD"),
                ),
                Entry(
                    account_id=account.id,
                    credit_amount=Money(Decimal("100.00"), "USD"),
                ),
            ],
        )
        transaction_repo.add(txn)

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n"
            "2026-01-15,100.00,Match\n"
            "2026-01-16,999.00,NoMatch\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        # Confirm the matched one
        matched = next(
            m for m in session.matches if m.suggested_ledger_txn_id is not None
        )
        service.confirm_session_match(session.id, matched.id)

        # Reject the unmatched one - this should trigger auto-close
        unmatched = next(
            m for m in session.matches if m.suggested_ledger_txn_id is None
        )
        service.reject_session_match(session.id, unmatched.id)

        updated = service.get_session(session.id)
        assert updated.status == ReconciliationSessionStatus.COMPLETED
        assert updated.closed_at is not None

    def test_no_auto_close_when_skipped_exists(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Session does NOT auto-close if any matches are SKIPPED."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n2026-01-15,100.00,One\n2026-01-16,200.00,Two\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        # Skip one, reject the other
        service.skip_session_match(session.id, session.matches[0].id)
        service.reject_session_match(session.id, session.matches[1].id)

        updated = service.get_session(session.id)
        assert updated.status == ReconciliationSessionStatus.PENDING


class TestCloseSession:
    """Tests for close_session method."""

    def test_close_session_sets_completed_when_all_resolved(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Manual close sets COMPLETED if no pending/skipped."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )
        service.reject_session_match(session.id, session.matches[0].id)

        closed = service.close_session(session.id)

        assert closed.status == ReconciliationSessionStatus.COMPLETED
        assert closed.closed_at is not None

    def test_close_session_sets_abandoned_when_pending_remain(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Manual close sets ABANDONED if pending or skipped remain."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n2026-01-15,100.00,One\n2026-01-16,200.00,Two\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )
        # Only reject one, leave the other pending
        service.reject_session_match(session.id, session.matches[0].id)

        closed = service.close_session(session.id)

        assert closed.status == ReconciliationSessionStatus.ABANDONED
        assert closed.closed_at is not None

    def test_close_session_raises_for_unknown_session(
        self, service: ReconciliationServiceImpl
    ):
        """Raises SessionNotFoundError for unknown session."""
        with pytest.raises(SessionNotFoundError):
            service.close_session(uuid4())


class TestGetSessionSummary:
    """Tests for get_session_summary method."""

    def test_get_session_summary_returns_counts(
        self, service: ReconciliationServiceImpl, account: Account, tmp_path
    ):
        """Returns summary with counts for each status."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Date,Amount,Description\n"
            "2026-01-15,100.00,One\n"
            "2026-01-16,200.00,Two\n"
            "2026-01-17,300.00,Three\n"
            "2026-01-18,400.00,Four\n"
        )

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        service.reject_session_match(session.id, session.matches[0].id)
        service.skip_session_match(session.id, session.matches[1].id)

        summary = service.get_session_summary(session.id)

        assert summary.total_imported == 4
        assert summary.pending == 2
        assert summary.rejected == 1
        assert summary.skipped == 1
        assert summary.confirmed == 0

    def test_get_session_summary_raises_for_unknown(
        self, service: ReconciliationServiceImpl
    ):
        """Raises SessionNotFoundError for unknown session."""
        with pytest.raises(SessionNotFoundError):
            service.get_session_summary(uuid4())


class TestRevisitSkippedMatch:
    """Tests for re-actioning skipped matches."""

    def test_can_confirm_previously_skipped_match(
        self,
        service: ReconciliationServiceImpl,
        account: Account,
        transaction_repo: SQLiteTransactionRepository,
        tmp_path,
    ):
        """Can change SKIPPED match to CONFIRMED."""
        txn = Transaction(
            transaction_date=date(2026, 1, 15),
            entries=[
                Entry(
                    account_id=account.id,
                    debit_amount=Money(Decimal("100.00"), "USD"),
                ),
                Entry(
                    account_id=account.id,
                    credit_amount=Money(Decimal("100.00"), "USD"),
                ),
            ],
        )
        transaction_repo.add(txn)

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Amount,Description\n2026-01-15,100.00,Test\n")

        session = service.create_session(
            account_id=account.id,
            file_path=str(csv_file),
            file_format="csv",
        )

        match = session.matches[0]
        service.skip_session_match(session.id, match.id)

        # Now confirm it
        confirmed = service.confirm_session_match(session.id, match.id)

        assert confirmed.status == ReconciliationMatchStatus.CONFIRMED
