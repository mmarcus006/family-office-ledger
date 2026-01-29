"""Tests for reconciliation CLI commands."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from family_office_ledger.cli import (
    cmd_reconcile_close,
    cmd_reconcile_confirm,
    cmd_reconcile_create,
    cmd_reconcile_list,
    cmd_reconcile_reject,
    cmd_reconcile_skip,
    cmd_reconcile_summary,
    main,
)
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.reconciliation import (
    ReconciliationMatch,
    ReconciliationMatchStatus,
    ReconciliationSession,
    ReconciliationSessionStatus,
)
from family_office_ledger.domain.value_objects import AccountType, EntityType
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteReconciliationSessionRepository,
)


@pytest.fixture
def db(tmp_path: Path) -> SQLiteDatabase:
    """Create a test database."""
    db_path = tmp_path / "test.db"
    db = SQLiteDatabase(str(db_path))
    db.initialize()
    return db


@pytest.fixture
def entity(db: SQLiteDatabase) -> Entity:
    """Create a test entity."""
    repo = SQLiteEntityRepository(db)
    entity = Entity(name="Test LLC", entity_type=EntityType.LLC)
    repo.add(entity)
    return entity


@pytest.fixture
def account(db: SQLiteDatabase, entity: Entity) -> Account:
    """Create a test account."""
    repo = SQLiteAccountRepository(db)
    account = Account(
        name="Checking",
        entity_id=entity.id,
        account_type=AccountType.ASSET,
    )
    repo.add(account)
    return account


@pytest.fixture
def session_repo(db: SQLiteDatabase) -> SQLiteReconciliationSessionRepository:
    """Create a session repository."""
    return SQLiteReconciliationSessionRepository(db)


@pytest.fixture
def session(
    account: Account, session_repo: SQLiteReconciliationSessionRepository
) -> ReconciliationSession:
    """Create a test reconciliation session."""
    session = ReconciliationSession(
        account_id=account.id,
        file_name="test.csv",
        file_format="csv",
    )
    # Add some test matches
    session.matches.append(
        ReconciliationMatch(
            session_id=session.id,
            imported_id="import_1",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.50"),
            imported_description="Payment to vendor",
            confidence_score=80,
        )
    )
    session.matches.append(
        ReconciliationMatch(
            session_id=session.id,
            imported_id="import_2",
            imported_date=date(2026, 1, 16),
            imported_amount=Decimal("250.00"),
            imported_description="Payroll deposit",
            confidence_score=90,
        )
    )
    session_repo.add(session)
    return session


class TestCmdReconcileCreate:
    """Tests for cmd_reconcile_create command."""

    def test_create_session_file_not_found(
        self, db: SQLiteDatabase, account: Account, capsys
    ):
        """Test create with nonexistent file."""

        class Args:
            database = str(db._path)
            account_id = str(account.id)
            file = "/nonexistent/file.csv"
            format = "csv"

        result = cmd_reconcile_create(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: File not found" in captured.out

    def test_create_session_nonexistent_account_still_creates(
        self, db: SQLiteDatabase, tmp_path: Path, capsys
    ):
        """Test create with nonexistent account still creates session (no validation)."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("date,amount,description\n2026-01-15,100.50,Test")

        class Args:
            database = str(db._path)
            account_id = str(uuid4())
            file = str(csv_file)
            format = "csv"

        result = cmd_reconcile_create(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Session created:" in captured.out

    def test_create_session_success(
        self, db: SQLiteDatabase, account: Account, tmp_path: Path, capsys
    ):
        """Test successful session creation."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("date,amount,description\n2026-01-15,100.50,Test payment")

        class Args:
            database = str(db._path)
            account_id = str(account.id)
            file = str(csv_file)
            format = "csv"

        result = cmd_reconcile_create(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Session created:" in captured.out
        assert "Account:" in captured.out
        assert "File:" in captured.out
        assert "Matches:" in captured.out

    def test_create_session_already_exists(
        self,
        db: SQLiteDatabase,
        account: Account,
        session: ReconciliationSession,
        tmp_path: Path,
        capsys,
    ):
        """Test create when pending session already exists."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("date,amount,description\n2026-01-15,100.50,Test")

        class Args:
            database = str(db._path)
            account_id = str(account.id)
            file = str(csv_file)
            format = "csv"

        result = cmd_reconcile_create(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out
        assert "pending session already exists" in captured.out.lower()


class TestCmdReconcileList:
    """Tests for cmd_reconcile_list command."""

    def test_list_session_not_found(self, db: SQLiteDatabase, capsys):
        """Test list with nonexistent session."""

        class Args:
            database = str(db._path)
            session_id = str(uuid4())
            status = None
            limit = 50
            offset = 0

        result = cmd_reconcile_list(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Session not found" in captured.out

    def test_list_matches_success(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test successful match listing."""

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            status = None
            limit = 50
            offset = 0

        result = cmd_reconcile_list(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Match ID" in captured.out
        assert "Status" in captured.out
        assert "Amount" in captured.out
        assert "Total:" in captured.out
        assert "2 matches" in captured.out

    def test_list_matches_with_status_filter(
        self,
        db: SQLiteDatabase,
        session: ReconciliationSession,
        session_repo: SQLiteReconciliationSessionRepository,
        capsys,
    ):
        """Test listing with status filter."""
        # Confirm one match
        session.matches[0].status = ReconciliationMatchStatus.CONFIRMED
        session_repo.update(session)

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            status = "pending"
            limit = 50
            offset = 0

        result = cmd_reconcile_list(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "1 matches" in captured.out

    def test_list_matches_with_pagination(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test listing with limit and offset."""

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            status = None
            limit = 1
            offset = 0

        result = cmd_reconcile_list(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "showing 1-1" in captured.out.lower()


class TestCmdReconcileConfirm:
    """Tests for cmd_reconcile_confirm command."""

    def test_confirm_session_not_found(self, db: SQLiteDatabase, capsys):
        """Test confirm with nonexistent session."""

        class Args:
            database = str(db._path)
            session_id = str(uuid4())
            match_id = str(uuid4())

        result = cmd_reconcile_confirm(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Session not found" in captured.out

    def test_confirm_match_not_found(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test confirm with nonexistent match."""

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            match_id = str(uuid4())

        result = cmd_reconcile_confirm(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Match not found" in captured.out

    def test_confirm_match_no_suggestion(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test confirm when match has no suggested transaction."""
        the_match_id = session.matches[0].id

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            match_id = str(the_match_id)

        result = cmd_reconcile_confirm(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert (
            "Error: Match not found" in captured.out
            or "no suggested" in captured.out.lower()
        )


class TestCmdReconcileReject:
    """Tests for cmd_reconcile_reject command."""

    def test_reject_session_not_found(self, db: SQLiteDatabase, capsys):
        """Test reject with nonexistent session."""

        class Args:
            database = str(db._path)
            session_id = str(uuid4())
            match_id = str(uuid4())

        result = cmd_reconcile_reject(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Session not found" in captured.out

    def test_reject_match_not_found(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test reject with nonexistent match."""

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            match_id = str(uuid4())

        result = cmd_reconcile_reject(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Match not found" in captured.out

    def test_reject_match_success(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test successful match rejection."""
        the_match_id = session.matches[0].id

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            match_id = str(the_match_id)

        result = cmd_reconcile_reject(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "rejected" in captured.out.lower()


class TestCmdReconcileSkip:
    """Tests for cmd_reconcile_skip command."""

    def test_skip_session_not_found(self, db: SQLiteDatabase, capsys):
        """Test skip with nonexistent session."""

        class Args:
            database = str(db._path)
            session_id = str(uuid4())
            match_id = str(uuid4())

        result = cmd_reconcile_skip(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Session not found" in captured.out

    def test_skip_match_not_found(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test skip with nonexistent match."""

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            match_id = str(uuid4())

        result = cmd_reconcile_skip(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Match not found" in captured.out

    def test_skip_match_success(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test successful match skip."""
        the_match_id = session.matches[0].id

        class Args:
            database = str(db._path)
            session_id = str(session.id)
            match_id = str(the_match_id)

        result = cmd_reconcile_skip(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "skipped" in captured.out.lower()


class TestCmdReconcileClose:
    """Tests for cmd_reconcile_close command."""

    def test_close_session_not_found(self, db: SQLiteDatabase, capsys):
        """Test close with nonexistent session."""

        class Args:
            database = str(db._path)
            session_id = str(uuid4())

        result = cmd_reconcile_close(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Session not found" in captured.out

    def test_close_session_success(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test successful session close."""

        class Args:
            database = str(db._path)
            session_id = str(session.id)

        result = cmd_reconcile_close(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "closed" in captured.out.lower()
        assert "status:" in captured.out.lower()


class TestCmdReconcileSummary:
    """Tests for cmd_reconcile_summary command."""

    def test_summary_session_not_found(self, db: SQLiteDatabase, capsys):
        """Test summary with nonexistent session."""

        class Args:
            database = str(db._path)
            session_id = str(uuid4())

        result = cmd_reconcile_summary(Args())

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Session not found" in captured.out

    def test_summary_success(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test successful summary display."""

        class Args:
            database = str(db._path)
            session_id = str(session.id)

        result = cmd_reconcile_summary(Args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Session Summary" in captured.out
        assert "Total:" in captured.out
        assert "Confirmed:" in captured.out
        assert "Rejected:" in captured.out
        assert "Skipped:" in captured.out
        assert "Pending:" in captured.out
        assert "Match Rate:" in captured.out


class TestReconcileMainIntegration:
    """Integration tests for reconcile commands via main()."""

    def test_reconcile_help(self, capsys):
        """Test reconcile --help displays subcommands."""
        with pytest.raises(SystemExit) as exc_info:
            main(["reconcile", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "create" in captured.out
        assert "list" in captured.out
        assert "confirm" in captured.out
        assert "reject" in captured.out
        assert "skip" in captured.out
        assert "close" in captured.out
        assert "summary" in captured.out

    def test_reconcile_create_via_main(
        self, db: SQLiteDatabase, account: Account, tmp_path: Path, capsys
    ):
        """Test create command via main."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("date,amount,description\n2026-01-15,100.50,Test")

        result = main(
            [
                "--database",
                str(db._path),
                "reconcile",
                "create",
                "--account-id",
                str(account.id),
                "--file",
                str(csv_file),
                "--format",
                "csv",
            ]
        )

        assert result == 0

    def test_reconcile_list_via_main(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test list command via main."""
        result = main(
            [
                "--database",
                str(db._path),
                "reconcile",
                "list",
                "--session-id",
                str(session.id),
            ]
        )

        assert result == 0

    def test_reconcile_summary_via_main(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test summary command via main."""
        result = main(
            [
                "--database",
                str(db._path),
                "reconcile",
                "summary",
                "--session-id",
                str(session.id),
            ]
        )

        assert result == 0

    def test_reconcile_close_via_main(
        self, db: SQLiteDatabase, session: ReconciliationSession, capsys
    ):
        """Test close command via main."""
        result = main(
            [
                "--database",
                str(db._path),
                "reconcile",
                "close",
                "--session-id",
                str(session.id),
            ]
        )

        assert result == 0
