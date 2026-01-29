"""Tests for ReconciliationSession and ReconciliationMatch domain models."""

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


class TestReconciliationSessionStatus:
    """Tests for ReconciliationSessionStatus enum."""

    def test_session_status_values(self):
        """Session status enum has correct lowercase values."""
        assert ReconciliationSessionStatus.PENDING.value == "pending"
        assert ReconciliationSessionStatus.COMPLETED.value == "completed"
        assert ReconciliationSessionStatus.ABANDONED.value == "abandoned"

    def test_session_status_is_string_enum(self):
        """Session status inherits from str for serialization."""
        assert isinstance(ReconciliationSessionStatus.PENDING, str)
        assert ReconciliationSessionStatus.PENDING == "pending"


class TestReconciliationMatchStatus:
    """Tests for ReconciliationMatchStatus enum."""

    def test_match_status_values(self):
        """Match status enum has correct lowercase values."""
        assert ReconciliationMatchStatus.PENDING.value == "pending"
        assert ReconciliationMatchStatus.CONFIRMED.value == "confirmed"
        assert ReconciliationMatchStatus.REJECTED.value == "rejected"
        assert ReconciliationMatchStatus.SKIPPED.value == "skipped"

    def test_match_status_is_string_enum(self):
        """Match status inherits from str for serialization."""
        assert isinstance(ReconciliationMatchStatus.CONFIRMED, str)
        assert ReconciliationMatchStatus.CONFIRMED == "confirmed"


class TestReconciliationMatch:
    """Tests for ReconciliationMatch dataclass."""

    def test_match_creation_with_required_fields(self):
        """Match can be created with only required fields."""
        session_id = uuid4()
        match = ReconciliationMatch(
            session_id=session_id,
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )

        assert match.session_id == session_id
        assert match.imported_id == "txn_001"
        assert match.imported_date == date(2026, 1, 15)
        assert match.imported_amount == Decimal("100.00")

    def test_match_has_auto_generated_id(self):
        """Match gets auto-generated UUID id."""
        match = ReconciliationMatch(
            session_id=uuid4(),
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )

        assert match.id is not None

    def test_match_defaults_to_pending_status(self):
        """Match defaults to PENDING status."""
        match = ReconciliationMatch(
            session_id=uuid4(),
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )

        assert match.status == ReconciliationMatchStatus.PENDING

    def test_match_defaults_to_zero_confidence_score(self):
        """Match defaults to 0 confidence score."""
        match = ReconciliationMatch(
            session_id=uuid4(),
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )

        assert match.confidence_score == 0

    def test_match_defaults_to_empty_description(self):
        """Match defaults to empty description."""
        match = ReconciliationMatch(
            session_id=uuid4(),
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )

        assert match.imported_description == ""

    def test_match_defaults_to_none_suggested_ledger_txn(self):
        """Match defaults to None suggested_ledger_txn_id."""
        match = ReconciliationMatch(
            session_id=uuid4(),
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )

        assert match.suggested_ledger_txn_id is None

    def test_match_defaults_to_none_actioned_at(self):
        """Match defaults to None actioned_at."""
        match = ReconciliationMatch(
            session_id=uuid4(),
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )

        assert match.actioned_at is None

    def test_match_has_created_at_timestamp(self):
        """Match gets auto-generated created_at timestamp."""
        before = datetime.now(UTC)
        match = ReconciliationMatch(
            session_id=uuid4(),
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
        )
        after = datetime.now(UTC)

        assert before <= match.created_at <= after

    def test_match_creation_with_all_fields(self):
        """Match can be created with all fields specified."""
        session_id = uuid4()
        ledger_txn_id = uuid4()
        actioned_at = datetime.now(UTC)

        match = ReconciliationMatch(
            session_id=session_id,
            imported_id="txn_001",
            imported_date=date(2026, 1, 15),
            imported_amount=Decimal("100.00"),
            imported_description="Payment to vendor",
            suggested_ledger_txn_id=ledger_txn_id,
            confidence_score=85,
            status=ReconciliationMatchStatus.CONFIRMED,
            actioned_at=actioned_at,
        )

        assert match.imported_description == "Payment to vendor"
        assert match.suggested_ledger_txn_id == ledger_txn_id
        assert match.confidence_score == 85
        assert match.status == ReconciliationMatchStatus.CONFIRMED
        assert match.actioned_at == actioned_at


class TestReconciliationSession:
    """Tests for ReconciliationSession dataclass."""

    def test_session_creation_with_required_fields(self):
        """Session can be created with only required fields."""
        account_id = uuid4()
        session = ReconciliationSession(
            account_id=account_id,
            file_name="transactions.csv",
            file_format="csv",
        )

        assert session.account_id == account_id
        assert session.file_name == "transactions.csv"
        assert session.file_format == "csv"

    def test_session_has_auto_generated_id(self):
        """Session gets auto-generated UUID id."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="transactions.csv",
            file_format="csv",
        )

        assert session.id is not None

    def test_session_defaults_to_pending_status(self):
        """Session defaults to PENDING status."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="transactions.csv",
            file_format="csv",
        )

        assert session.status == ReconciliationSessionStatus.PENDING

    def test_session_defaults_to_empty_matches(self):
        """Session defaults to empty matches list."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="transactions.csv",
            file_format="csv",
        )

        assert session.matches == []

    def test_session_defaults_to_none_closed_at(self):
        """Session defaults to None closed_at."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="transactions.csv",
            file_format="csv",
        )

        assert session.closed_at is None

    def test_session_has_created_at_timestamp(self):
        """Session gets auto-generated created_at timestamp."""
        before = datetime.now(UTC)
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="transactions.csv",
            file_format="csv",
        )
        after = datetime.now(UTC)

        assert before <= session.created_at <= after


class TestReconciliationSessionProperties:
    """Tests for ReconciliationSession property methods."""

    @pytest.fixture
    def session_with_matches(self) -> ReconciliationSession:
        """Create a session with various match statuses."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )

        # Add 2 pending matches
        for i in range(2):
            session.matches.append(
                ReconciliationMatch(
                    session_id=session.id,
                    imported_id=f"pending_{i}",
                    imported_date=date(2026, 1, 15),
                    imported_amount=Decimal("100.00"),
                    status=ReconciliationMatchStatus.PENDING,
                )
            )

        # Add 3 confirmed matches
        for i in range(3):
            session.matches.append(
                ReconciliationMatch(
                    session_id=session.id,
                    imported_id=f"confirmed_{i}",
                    imported_date=date(2026, 1, 15),
                    imported_amount=Decimal("100.00"),
                    status=ReconciliationMatchStatus.CONFIRMED,
                )
            )

        # Add 1 rejected match
        session.matches.append(
            ReconciliationMatch(
                session_id=session.id,
                imported_id="rejected_0",
                imported_date=date(2026, 1, 15),
                imported_amount=Decimal("100.00"),
                status=ReconciliationMatchStatus.REJECTED,
            )
        )

        # Add 2 skipped matches
        for i in range(2):
            session.matches.append(
                ReconciliationMatch(
                    session_id=session.id,
                    imported_id=f"skipped_{i}",
                    imported_date=date(2026, 1, 15),
                    imported_amount=Decimal("100.00"),
                    status=ReconciliationMatchStatus.SKIPPED,
                )
            )

        return session

    def test_pending_count(self, session_with_matches: ReconciliationSession):
        """pending_count returns count of PENDING matches."""
        assert session_with_matches.pending_count == 2

    def test_confirmed_count(self, session_with_matches: ReconciliationSession):
        """confirmed_count returns count of CONFIRMED matches."""
        assert session_with_matches.confirmed_count == 3

    def test_rejected_count(self, session_with_matches: ReconciliationSession):
        """rejected_count returns count of REJECTED matches."""
        assert session_with_matches.rejected_count == 1

    def test_skipped_count(self, session_with_matches: ReconciliationSession):
        """skipped_count returns count of SKIPPED matches."""
        assert session_with_matches.skipped_count == 2

    def test_match_rate_calculation(self, session_with_matches: ReconciliationSession):
        """match_rate is confirmed_count / total_matches."""
        # 3 confirmed out of 8 total = 0.375
        assert session_with_matches.match_rate == pytest.approx(3 / 8)

    def test_match_rate_with_no_matches(self):
        """match_rate returns 0.0 when no matches exist."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )

        assert session.match_rate == 0.0

    def test_counts_with_empty_session(self):
        """All counts are 0 for session with no matches."""
        session = ReconciliationSession(
            account_id=uuid4(),
            file_name="test.csv",
            file_format="csv",
        )

        assert session.pending_count == 0
        assert session.confirmed_count == 0
        assert session.rejected_count == 0
        assert session.skipped_count == 0
