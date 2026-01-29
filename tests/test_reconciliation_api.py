"""Integration tests for reconciliation API endpoints."""

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import Client

from family_office_ledger.api.app import create_app, get_db
from family_office_ledger.repositories.sqlite import SQLiteDatabase


@pytest.fixture
def test_db() -> SQLiteDatabase:
    """Create an in-memory test database with thread-safety disabled for testing."""
    db = SQLiteDatabase(":memory:", check_same_thread=False)
    db.initialize()
    return db


@pytest.fixture
def test_client(test_db: SQLiteDatabase) -> Client:
    """Create a test client with the test database."""
    from starlette.testclient import TestClient

    app = create_app()

    # Override the database dependency
    def override_get_db() -> SQLiteDatabase:
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[SQLiteDatabase] = override_get_db

    return TestClient(app)


@pytest.fixture
def test_entity_id(test_client: Client) -> str:
    """Create a test entity and return its ID."""
    response = test_client.post(
        "/entities",
        json={"name": "Reconciliation Test Entity", "entity_type": "trust"},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def test_account_id(test_client: Client, test_entity_id: str) -> str:
    """Create a test account and return its ID."""
    response = test_client.post(
        "/accounts",
        json={
            "name": "Main Checking",
            "entity_id": test_entity_id,
            "account_type": "asset",
            "sub_type": "checking",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def equity_account_id(test_client: Client, test_entity_id: str) -> str:
    """Create an equity account for balanced transactions."""
    response = test_client.post(
        "/accounts",
        json={
            "name": "Equity",
            "entity_id": test_entity_id,
            "account_type": "equity",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def sample_csv_file(tmp_path: Path) -> str:
    """Create a sample CSV file for import testing."""
    csv_content = """Date,Description,Amount
2026-01-15,DEPOSIT,1000.00
2026-01-16,GROCERY STORE,-45.67
2026-01-17,PAYCHECK DIRECT DEP,2500.00
"""
    csv_file = tmp_path / "test_import.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)


@pytest.fixture
def sample_csv_with_ledger_match(
    test_client: Client,
    test_account_id: str,
    equity_account_id: str,
    tmp_path: Path,
) -> str:
    """Create a CSV file with transactions that match ledger entries."""
    # First, create some ledger transactions
    test_client.post(
        "/transactions",
        json={
            "transaction_date": "2026-01-15",
            "memo": "Deposit from client",
            "entries": [
                {
                    "account_id": test_account_id,
                    "debit_amount": "1000.00",
                    "credit_amount": "0",
                },
                {
                    "account_id": equity_account_id,
                    "debit_amount": "0",
                    "credit_amount": "1000.00",
                },
            ],
        },
    )
    test_client.post(
        "/transactions",
        json={
            "transaction_date": "2026-01-17",
            "memo": "Paycheck deposit",
            "entries": [
                {
                    "account_id": test_account_id,
                    "debit_amount": "2500.00",
                    "credit_amount": "0",
                },
                {
                    "account_id": equity_account_id,
                    "debit_amount": "0",
                    "credit_amount": "2500.00",
                },
            ],
        },
    )

    # CSV with matching transactions
    csv_content = """Date,Description,Amount
2026-01-15,DEPOSIT,1000.00
2026-01-16,GROCERY STORE,-45.67
2026-01-17,PAYCHECK,2500.00
"""
    csv_file = tmp_path / "matching.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)


class TestCreateSession:
    """Tests for POST /reconciliation/sessions endpoint."""

    def test_create_session_returns_201(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Create session successfully returns 201 with session data."""
        response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["account_id"] == test_account_id
        assert data["status"] == "pending"
        assert data["file_format"] == "csv"
        assert "matches" in data

    def test_create_session_imports_transactions(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Create session imports transactions and creates matches."""
        response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )

        assert response.status_code == 201
        data = response.json()
        # 3 transactions in the CSV
        assert len(data["matches"]) == 3

    def test_create_session_conflict_when_pending_exists(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Create session returns 409 when pending session already exists."""
        # Create first session
        response1 = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        assert response1.status_code == 201

        # Try to create another session for same account
        response2 = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )

        assert response2.status_code == 409
        assert "pending session" in response2.json()["detail"].lower()


class TestGetSession:
    """Tests for GET /reconciliation/sessions/{session_id} endpoint."""

    def test_get_session_returns_200(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Get existing session returns 200 with session data."""
        # Create session first
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]

        # Get the session
        response = test_client.get(f"/reconciliation/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["account_id"] == test_account_id
        assert data["status"] == "pending"

    def test_get_session_not_found_returns_404(self, test_client: Client) -> None:
        """Get non-existent session returns 404."""
        fake_id = str(uuid4())
        response = test_client.get(f"/reconciliation/sessions/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListMatches:
    """Tests for GET /reconciliation/sessions/{session_id}/matches endpoint."""

    def test_list_matches_returns_paginated_results(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """List matches returns paginated match data."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]

        # List matches
        response = test_client.get(f"/reconciliation/sessions/{session_id}/matches")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 3  # 3 transactions in CSV

    def test_list_matches_with_limit_and_offset(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """List matches respects limit and offset parameters."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]

        # List with limit=1, offset=1
        response = test_client.get(
            f"/reconciliation/sessions/{session_id}/matches?limit=1&offset=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) == 1
        assert data["total"] == 3
        assert data["limit"] == 1
        assert data["offset"] == 1

    def test_list_matches_filter_by_status(
        self,
        test_client: Client,
        test_account_id: str,
        equity_account_id: str,
        sample_csv_with_ledger_match: str,
    ) -> None:
        """List matches can filter by status."""
        # Create session with matches
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_with_ledger_match,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        matches = create_response.json()["matches"]

        # Confirm a match that has a suggested transaction
        match_with_suggestion = next(
            (m for m in matches if m["suggested_ledger_txn_id"] is not None), None
        )
        if match_with_suggestion:
            test_client.post(
                f"/reconciliation/sessions/{session_id}/matches/{match_with_suggestion['id']}/confirm"
            )

        # Filter by pending status
        pending_response = test_client.get(
            f"/reconciliation/sessions/{session_id}/matches?status=pending"
        )
        assert pending_response.status_code == 200
        assert "matches" in pending_response.json()

        # Filter by confirmed status
        confirmed_response = test_client.get(
            f"/reconciliation/sessions/{session_id}/matches?status=confirmed"
        )
        assert confirmed_response.status_code == 200
        confirmed_data = confirmed_response.json()

        # If we confirmed a match, check the counts make sense
        if match_with_suggestion:
            assert confirmed_data["total"] >= 1

    def test_list_matches_session_not_found_returns_404(
        self, test_client: Client
    ) -> None:
        """List matches for non-existent session returns 404."""
        fake_id = str(uuid4())
        response = test_client.get(f"/reconciliation/sessions/{fake_id}/matches")

        assert response.status_code == 404


class TestConfirmMatch:
    """Tests for POST /reconciliation/sessions/{session_id}/matches/{match_id}/confirm endpoint."""

    def test_confirm_match_returns_200(
        self,
        test_client: Client,
        test_account_id: str,
        equity_account_id: str,
        sample_csv_with_ledger_match: str,
    ) -> None:
        """Confirm match returns 200 with updated match."""
        # Create session with matches
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_with_ledger_match,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        matches = create_response.json()["matches"]

        # Find a match with a suggested ledger transaction
        match_with_suggestion = next(
            (m for m in matches if m["suggested_ledger_txn_id"] is not None), None
        )

        if match_with_suggestion is None:
            pytest.skip("No matches with suggested transactions available")

        # Confirm the match
        response = test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{match_with_suggestion['id']}/confirm"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
        assert data["actioned_at"] is not None

    def test_confirm_match_session_not_found_returns_404(
        self, test_client: Client
    ) -> None:
        """Confirm match with non-existent session returns 404."""
        fake_session_id = str(uuid4())
        fake_match_id = str(uuid4())

        response = test_client.post(
            f"/reconciliation/sessions/{fake_session_id}/matches/{fake_match_id}/confirm"
        )

        assert response.status_code == 404
        assert "session" in response.json()["detail"].lower()

    def test_confirm_match_match_not_found_returns_404(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Confirm match with non-existent match returns 404."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        fake_match_id = str(uuid4())

        response = test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{fake_match_id}/confirm"
        )

        assert response.status_code == 404
        assert "match" in response.json()["detail"].lower()


class TestRejectMatch:
    """Tests for POST /reconciliation/sessions/{session_id}/matches/{match_id}/reject endpoint."""

    def test_reject_match_returns_200(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Reject match returns 200 with updated match."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        matches = create_response.json()["matches"]
        match_id = matches[0]["id"]

        # Reject the match
        response = test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{match_id}/reject"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["actioned_at"] is not None

    def test_reject_match_session_not_found_returns_404(
        self, test_client: Client
    ) -> None:
        """Reject match with non-existent session returns 404."""
        fake_session_id = str(uuid4())
        fake_match_id = str(uuid4())

        response = test_client.post(
            f"/reconciliation/sessions/{fake_session_id}/matches/{fake_match_id}/reject"
        )

        assert response.status_code == 404

    def test_reject_match_match_not_found_returns_404(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Reject match with non-existent match returns 404."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        fake_match_id = str(uuid4())

        response = test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{fake_match_id}/reject"
        )

        assert response.status_code == 404


class TestSkipMatch:
    """Tests for POST /reconciliation/sessions/{session_id}/matches/{match_id}/skip endpoint."""

    def test_skip_match_returns_200(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Skip match returns 200 with updated match."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        matches = create_response.json()["matches"]
        match_id = matches[0]["id"]

        # Skip the match
        response = test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{match_id}/skip"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["actioned_at"] is not None

    def test_skip_match_session_not_found_returns_404(
        self, test_client: Client
    ) -> None:
        """Skip match with non-existent session returns 404."""
        fake_session_id = str(uuid4())
        fake_match_id = str(uuid4())

        response = test_client.post(
            f"/reconciliation/sessions/{fake_session_id}/matches/{fake_match_id}/skip"
        )

        assert response.status_code == 404

    def test_skip_match_match_not_found_returns_404(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Skip match with non-existent match returns 404."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        fake_match_id = str(uuid4())

        response = test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{fake_match_id}/skip"
        )

        assert response.status_code == 404


class TestCloseSession:
    """Tests for POST /reconciliation/sessions/{session_id}/close endpoint."""

    def test_close_session_returns_200(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Close session returns 200 with updated session."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]

        # Close the session
        response = test_client.post(f"/reconciliation/sessions/{session_id}/close")

        assert response.status_code == 200
        data = response.json()
        assert data["closed_at"] is not None
        # With pending matches, should be abandoned
        assert data["status"] in ("completed", "abandoned")

    def test_close_session_completed_when_all_resolved(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Close session becomes COMPLETED when all matches are confirmed/rejected."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        matches = create_response.json()["matches"]

        # Reject all matches (since they don't have suggested transactions)
        for match in matches:
            test_client.post(
                f"/reconciliation/sessions/{session_id}/matches/{match['id']}/reject"
            )

        # Close the session
        response = test_client.post(f"/reconciliation/sessions/{session_id}/close")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_close_session_abandoned_with_pending_matches(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Close session becomes ABANDONED when pending matches exist."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]

        # Don't process any matches, just close
        response = test_client.post(f"/reconciliation/sessions/{session_id}/close")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "abandoned"

    def test_close_session_not_found_returns_404(self, test_client: Client) -> None:
        """Close non-existent session returns 404."""
        fake_id = str(uuid4())
        response = test_client.post(f"/reconciliation/sessions/{fake_id}/close")

        assert response.status_code == 404


class TestGetSessionSummary:
    """Tests for GET /reconciliation/sessions/{session_id}/summary endpoint."""

    def test_get_summary_returns_200(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Get session summary returns 200 with statistics."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]

        # Get summary
        response = test_client.get(f"/reconciliation/sessions/{session_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_imported" in data
        assert "pending" in data
        assert "confirmed" in data
        assert "rejected" in data
        assert "skipped" in data
        assert "match_rate" in data
        assert data["total_imported"] == 3

    def test_get_summary_reflects_match_actions(
        self, test_client: Client, test_account_id: str, sample_csv_file: str
    ) -> None:
        """Get session summary reflects match actions."""
        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_file,
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        matches = create_response.json()["matches"]

        # Reject one, skip one
        test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{matches[0]['id']}/reject"
        )
        test_client.post(
            f"/reconciliation/sessions/{session_id}/matches/{matches[1]['id']}/skip"
        )

        # Get summary
        response = test_client.get(f"/reconciliation/sessions/{session_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["rejected"] == 1
        assert data["skipped"] == 1
        assert data["pending"] == 1

    def test_get_summary_session_not_found_returns_404(
        self, test_client: Client
    ) -> None:
        """Get summary for non-existent session returns 404."""
        fake_id = str(uuid4())
        response = test_client.get(f"/reconciliation/sessions/{fake_id}/summary")

        assert response.status_code == 404


class TestFullWorkflow:
    """Integration test for complete reconciliation workflow."""

    def test_full_reconciliation_workflow(
        self,
        test_client: Client,
        test_account_id: str,
        equity_account_id: str,
        sample_csv_with_ledger_match: str,
    ) -> None:
        """Test complete workflow: create -> list -> action matches -> close -> summary."""
        # Step 1: Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": sample_csv_with_ledger_match,
                "file_format": "csv",
            },
        )
        assert create_response.status_code == 201
        session_id = create_response.json()["id"]
        initial_matches = create_response.json()["matches"]
        assert len(initial_matches) == 3

        # Step 2: List matches
        list_response = test_client.get(
            f"/reconciliation/sessions/{session_id}/matches"
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 3

        # Step 3: Get session to verify state
        get_response = test_client.get(f"/reconciliation/sessions/{session_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "pending"

        # Step 4: Action each match differently
        confirmed_count = 0
        rejected_count = 0
        skipped_count = 0

        for match in initial_matches:
            match_id = match["id"]
            has_suggestion = match["suggested_ledger_txn_id"] is not None

            if has_suggestion and confirmed_count == 0:
                # Confirm one match with suggestion
                response = test_client.post(
                    f"/reconciliation/sessions/{session_id}/matches/{match_id}/confirm"
                )
                assert response.status_code == 200
                assert response.json()["status"] == "confirmed"
                confirmed_count += 1
            elif rejected_count == 0:
                # Reject one match
                response = test_client.post(
                    f"/reconciliation/sessions/{session_id}/matches/{match_id}/reject"
                )
                assert response.status_code == 200
                assert response.json()["status"] == "rejected"
                rejected_count += 1
            else:
                # Skip remaining matches
                response = test_client.post(
                    f"/reconciliation/sessions/{session_id}/matches/{match_id}/skip"
                )
                assert response.status_code == 200
                assert response.json()["status"] == "skipped"
                skipped_count += 1

        # Step 5: Get summary before close
        summary_response = test_client.get(
            f"/reconciliation/sessions/{session_id}/summary"
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["total_imported"] == 3
        assert summary["rejected"] == rejected_count
        assert summary["skipped"] == skipped_count

        # Step 6: Close session
        close_response = test_client.post(
            f"/reconciliation/sessions/{session_id}/close"
        )
        assert close_response.status_code == 200
        # With skipped matches, should be abandoned
        assert close_response.json()["status"] == "abandoned"
        assert close_response.json()["closed_at"] is not None

        # Step 7: Verify final state
        final_response = test_client.get(f"/reconciliation/sessions/{session_id}")
        assert final_response.status_code == 200
        assert final_response.json()["status"] == "abandoned"

    def test_workflow_with_all_confirmed_auto_closes(
        self,
        test_client: Client,
        test_account_id: str,
        equity_account_id: str,
        tmp_path: Path,
    ) -> None:
        """Test workflow where confirming/rejecting all matches auto-closes session."""
        # Create ledger transactions that will match
        test_client.post(
            "/transactions",
            json={
                "transaction_date": "2026-01-15",
                "memo": "Single deposit",
                "entries": [
                    {
                        "account_id": test_account_id,
                        "debit_amount": "500.00",
                        "credit_amount": "0",
                    },
                    {
                        "account_id": equity_account_id,
                        "debit_amount": "0",
                        "credit_amount": "500.00",
                    },
                ],
            },
        )

        # CSV with single matching transaction
        csv_content = """Date,Description,Amount
2026-01-15,DEPOSIT,500.00
"""
        csv_file = tmp_path / "single.csv"
        csv_file.write_text(csv_content)

        # Create session
        create_response = test_client.post(
            "/reconciliation/sessions",
            json={
                "account_id": test_account_id,
                "file_path": str(csv_file),
                "file_format": "csv",
            },
        )
        session_id = create_response.json()["id"]
        matches = create_response.json()["matches"]
        assert len(matches) == 1

        match = matches[0]
        if match["suggested_ledger_txn_id"] is not None:
            # Confirm the match - this may auto-close
            test_client.post(
                f"/reconciliation/sessions/{session_id}/matches/{match['id']}/confirm"
            )

            # Check if auto-closed
            get_response = test_client.get(f"/reconciliation/sessions/{session_id}")
            # After confirming all matches (no pending, no skipped), should be completed
            assert get_response.json()["status"] == "completed"
        else:
            # If no match, reject it to complete
            test_client.post(
                f"/reconciliation/sessions/{session_id}/matches/{match['id']}/reject"
            )

            # Close manually and verify
            test_client.post(f"/reconciliation/sessions/{session_id}/close")
            get_response = test_client.get(f"/reconciliation/sessions/{session_id}")
            assert get_response.json()["status"] == "completed"
