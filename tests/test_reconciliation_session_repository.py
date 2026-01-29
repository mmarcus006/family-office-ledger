"""Tests for SQLite ReconciliationSession repository."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.reconciliation import (
    ReconciliationMatch,
    ReconciliationMatchStatus,
    ReconciliationSession,
    ReconciliationSessionStatus,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLiteReconciliationSessionRepository,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def repo(db: SQLiteDatabase) -> SQLiteReconciliationSessionRepository:
    """Create a reconciliation session repository."""
    return SQLiteReconciliationSessionRepository(db)


class TestSQLiteReconciliationSessionRepository:
    """Tests for SQLiteReconciliationSessionRepository."""

    def test_add_and_get_session(self, repo: SQLiteReconciliationSessionRepository):
        """Can add and retrieve a session."""
        account_id = uuid4()
        session = ReconciliationSession(
            account_id=account_id,
            file_name="transactions.csv",
            file_format="csv",
        )

        repo.add(session)
        retrieved = repo.get(session.id)

        assert retrieved is not None
        assert retrieved.id == session.id
        assert retrieved.account_id == account_id
        assert retrieved.file_name == "transactions.csv"
        assert retrieved.file_format == "csv"
        assert retrieved.status == ReconciliationSessionStatus.PENDING

    def test_get_nonexistent_session_returns_none(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """Getting a nonexistent session returns None."""
        result = repo.get(uuid4())
        assert result is None

    def test_add_session_with_matches(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """Can add a session with matches and retrieve them."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )

        # Add matches
        ledger_txn_id = uuid4()
        match1 = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
            imported_description="Payment to vendor",
            suggested_ledger_txn_id=ledger_txn_id,
            confidence_score=85,
        )
        match2 = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_002",
            imported_date=date(2026, 1, 16),
            imported_amount=Decimal("200.00"),
        )
        session.matches.append(match1)
        session.matches.append(match2)

        repo.add(session)
        retrieved = repo.get(session.id)

        assert retrieved is not None
        assert len(retrieved.matches) == 2

        # Find match1 by imported_id
        retrieved_match1 = next(
            (m for m in retrieved.matches if m.imported_id == "txn_001"), None
        )
        assert retrieved_match1 is not None
        assert retrieved_match1.imported_amount == Decimal("100.00")
        assert retrieved_match1.imported_description == "Payment to vendor"
        assert retrieved_match1.suggested_ledger_txn_id == ledger_txn_id
        assert retrieved_match1.confidence_score == 85

    def test_get_pending_for_account(self, repo: SQLiteReconciliationSessionRepository):
        """Can get the pending session for an account."""
        account_id = uuid4()
        session = ReconciliationSession(
            account_id=account_id,
            file_name="test.csv",
            file_format="csv",
            status=ReconciliationSessionStatus.PENDING,
        )
        repo.add(session)

        pending = repo.get_pending_for_account(account_id)

        assert pending is not None
        assert pending.id == session.id

    def test_get_pending_for_account_ignores_completed(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """get_pending_for_account ignores completed sessions."""
        account_id = uuid4()

        # Create completed session
        completed = ReconciliationSession(
            account_id=account_id,
            file_name="old.csv",
            file_format="csv",
            status=ReconciliationSessionStatus.COMPLETED,
        )
        repo.add(completed)

        pending = repo.get_pending_for_account(account_id)
        assert pending is None

    def test_get_pending_for_account_returns_none_for_unknown_account(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """get_pending_for_account returns None for unknown account."""
        result = repo.get_pending_for_account(uuid4())
        assert result is None

    def test_update_session(self, repo: SQLiteReconciliationSessionRepository):
        """Can update session status and closed_at."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )
        repo.add(session)

        # Update session
        session.status = ReconciliationSessionStatus.COMPLETED
        session.closed_at = datetime.now(UTC)
        repo.update(session)

        # Retrieve and verify
        retrieved = repo.get(session.id)
        assert retrieved is not None
        assert retrieved.status == ReconciliationSessionStatus.COMPLETED
        assert retrieved.closed_at is not None

    def test_update_session_with_match_changes(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """Can update session with match status changes."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )
        match = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )
        session.matches.append(match)
        repo.add(session)

        # Update match status
        session.matches[0].status = ReconciliationMatchStatus.CONFIRMED
        session.matches[0].actioned_at = datetime.now(UTC)
        repo.update(session)

        # Retrieve and verify
        retrieved = repo.get(session.id)
        assert retrieved is not None
        assert len(retrieved.matches) == 1
        assert retrieved.matches[0].status == ReconciliationMatchStatus.CONFIRMED
        assert retrieved.matches[0].actioned_at is not None

    def test_delete_session(self, repo: SQLiteReconciliationSessionRepository):
        """Can delete a session."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )
        repo.add(session)

        repo.delete(session.id)

        assert repo.get(session.id) is None

    def test_delete_session_cascades_to_matches(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """Deleting a session also deletes its matches."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )
        match = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )
        session.matches.append(match)
        repo.add(session)

        repo.delete(session.id)

        # Session gone
        assert repo.get(session.id) is None

        # Matches should also be gone (verified by FK cascade)
        # We can verify by trying to add the same session back and checking it has no orphan matches
        session2 = ReconciliationSession(
            id=session.id,  # Same ID
            account_id=session.account_id,
            file_name="test2.csv",
            file_format="csv",
        )
        repo.add(session2)
        retrieved = repo.get(session.id)
        assert retrieved is not None
        assert len(retrieved.matches) == 0

    def test_list_by_account(self, repo: SQLiteReconciliationSessionRepository):
        """Can list all sessions for an account."""
        account_id = uuid4()
        other_account_id = uuid4()

        # Create sessions for our account
        session1 = ReconciliationSession(
            account_id=account_id,
            file_name="jan.csv",
            file_format="csv",
            status=ReconciliationSessionStatus.COMPLETED,
        )
        session2 = ReconciliationSession(
            account_id=account_id,
            file_name="feb.csv",
            file_format="csv",
            status=ReconciliationSessionStatus.PENDING,
        )
        # Create session for different account
        session3 = ReconciliationSession(
            account_id=other_account_id,
            file_name="other.csv",
            file_format="csv",
        )

        repo.add(session1)
        repo.add(session2)
        repo.add(session3)

        sessions = list(repo.list_by_account(account_id))

        assert len(sessions) == 2
        session_ids = {s.id for s in sessions}
        assert session1.id in session_ids
        assert session2.id in session_ids
        assert session3.id not in session_ids

    def test_list_by_account_empty_for_unknown_account(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """list_by_account returns empty for unknown account."""
        sessions = list(repo.list_by_account(uuid4()))
        assert sessions == []

    def test_session_timestamps_preserved(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """Session created_at and closed_at timestamps are preserved."""
        created_at = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        closed_at = datetime(2026, 1, 15, 11, 45, 0, tzinfo=UTC)

        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
            status=ReconciliationSessionStatus.COMPLETED,
            closed_at=closed_at,
        )
        # Override created_at
        object.__setattr__(session, "created_at", created_at)

        repo.add(session)
        retrieved = repo.get(session.id)

        assert retrieved is not None
        assert retrieved.created_at == created_at
        assert retrieved.closed_at == closed_at

    def test_match_timestamps_preserved(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """Match created_at and actioned_at timestamps are preserved."""
        created_at = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        actioned_at = datetime(2026, 1, 15, 10, 35, 0, tzinfo=UTC)

        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )
        match = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
            status=ReconciliationMatchStatus.CONFIRMED,
            actioned_at=actioned_at,
        )
        # Override created_at
        object.__setattr__(match, "created_at", created_at)
        session.matches.append(match)

        repo.add(session)
        retrieved = repo.get(session.id)

        assert retrieved is not None
        assert len(retrieved.matches) == 1
        assert retrieved.matches[0].created_at == created_at
        assert retrieved.matches[0].actioned_at == actioned_at

    def test_matches_ordered_by_created_at(
        self, repo: SQLiteReconciliationSessionRepository
    ):
        """Matches are returned ordered by created_at ASC."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )

        # Create matches with different created_at times
        match1 = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_003",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("300.00"),
        )
        object.__setattr__(
            match1, "created_at", datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        )

        match2 = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )
        object.__setattr__(
            match2, "created_at", datetime(2026, 1, 15, 10, 10, tzinfo=UTC)
        )

        match3 = ReconciliationMatch(
            session_id=session.id,
            imported_id="txn_002",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("200.00"),
        )
        object.__setattr__(
            match3, "created_at", datetime(2026, 1, 15, 10, 20, tzinfo=UTC)
        )

        session.matches.extend([match1, match2, match3])
        repo.add(session)

        retrieved = repo.get(session.id)
        assert retrieved is not None

        # Should be ordered by created_at ASC
        imported_ids = [m.imported_id for m in retrieved.matches]
        assert imported_ids == ["txn_001", "txn_002", "txn_003"]
