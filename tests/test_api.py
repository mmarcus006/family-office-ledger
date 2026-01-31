"""Tests for FastAPI endpoints."""


import pytest
from httpx import Client

from family_office_ledger.api.app import create_app, get_db
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
)


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

    # Override the database dependency (both get_db function and SQLiteDatabase class)
    def override_get_db() -> SQLiteDatabase:
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[SQLiteDatabase] = override_get_db

    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_returns_ok(self, test_client: Client) -> None:
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestEntityEndpoints:
    """Tests for /entities endpoints."""

    def test_create_entity_returns_201(self, test_client: Client) -> None:
        payload = {
            "name": "Test LLC",
            "entity_type": "llc",
            "fiscal_year_end": "2025-12-31",
        }
        response = test_client.post("/entities", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test LLC"
        assert data["entity_type"] == "llc"
        assert "id" in data

    def test_create_entity_with_minimal_fields(self, test_client: Client) -> None:
        payload = {
            "name": "Minimal Entity",
            "entity_type": "individual",
        }
        response = test_client.post("/entities", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Entity"
        assert data["entity_type"] == "individual"

    def test_create_entity_invalid_type_returns_422(self, test_client: Client) -> None:
        payload = {
            "name": "Invalid Entity",
            "entity_type": "invalid_type",
        }
        response = test_client.post("/entities", json=payload)
        assert response.status_code == 422

    def test_list_entities_returns_empty_list(self, test_client: Client) -> None:
        response = test_client.get("/entities")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_entities_returns_created_entities(self, test_client: Client) -> None:
        # Create two entities
        test_client.post(
            "/entities",
            json={"name": "Entity 1", "entity_type": "llc"},
        )
        test_client.post(
            "/entities",
            json={"name": "Entity 2", "entity_type": "trust"},
        )

        response = test_client.get("/entities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [e["name"] for e in data]
        assert "Entity 1" in names
        assert "Entity 2" in names

    def test_get_entity_by_id(self, test_client: Client) -> None:
        # Create entity
        create_response = test_client.post(
            "/entities",
            json={"name": "Get Test", "entity_type": "partnership"},
        )
        entity_id = create_response.json()["id"]

        # Get entity by ID
        response = test_client.get(f"/entities/{entity_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test"
        assert data["id"] == entity_id

    def test_get_entity_not_found_returns_404(self, test_client: Client) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/entities/{fake_id}")
        assert response.status_code == 404


class TestAccountEndpoints:
    """Tests for /accounts endpoints."""

    def test_create_account_returns_201(self, test_client: Client) -> None:
        # First create an entity
        entity_response = test_client.post(
            "/entities",
            json={"name": "Account Test Entity", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        # Create account
        payload = {
            "name": "Checking Account",
            "entity_id": entity_id,
            "account_type": "asset",
            "sub_type": "checking",
            "currency": "USD",
        }
        response = test_client.post("/accounts", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Checking Account"
        assert data["entity_id"] == entity_id
        assert data["account_type"] == "asset"
        assert data["sub_type"] == "checking"

    def test_create_account_with_minimal_fields(self, test_client: Client) -> None:
        entity_response = test_client.post(
            "/entities",
            json={"name": "Minimal Account Entity", "entity_type": "individual"},
        )
        entity_id = entity_response.json()["id"]

        payload = {
            "name": "Simple Account",
            "entity_id": entity_id,
            "account_type": "asset",
        }
        response = test_client.post("/accounts", json=payload)
        assert response.status_code == 201

    def test_create_account_invalid_entity_returns_404(
        self, test_client: Client
    ) -> None:
        fake_entity_id = "00000000-0000-0000-0000-000000000000"
        payload = {
            "name": "Orphan Account",
            "entity_id": fake_entity_id,
            "account_type": "asset",
        }
        response = test_client.post("/accounts", json=payload)
        assert response.status_code == 404

    def test_list_accounts_returns_empty(self, test_client: Client) -> None:
        response = test_client.get("/accounts")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_accounts_filter_by_entity_id(self, test_client: Client) -> None:
        # Create two entities
        entity1_response = test_client.post(
            "/entities",
            json={"name": "Entity 1", "entity_type": "llc"},
        )
        entity1_id = entity1_response.json()["id"]

        entity2_response = test_client.post(
            "/entities",
            json={"name": "Entity 2", "entity_type": "trust"},
        )
        entity2_id = entity2_response.json()["id"]

        # Create accounts for each entity
        test_client.post(
            "/accounts",
            json={
                "name": "Account E1",
                "entity_id": entity1_id,
                "account_type": "asset",
            },
        )
        test_client.post(
            "/accounts",
            json={
                "name": "Account E2",
                "entity_id": entity2_id,
                "account_type": "liability",
            },
        )

        # List accounts for entity 1 only
        response = test_client.get(f"/accounts?entity_id={entity1_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Account E1"


class TestTransactionEndpoints:
    """Tests for /transactions endpoints."""

    def test_post_transaction_returns_201(self, test_client: Client) -> None:
        # Create entity and accounts
        entity_response = test_client.post(
            "/entities",
            json={"name": "Txn Test Entity", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        cash_response = test_client.post(
            "/accounts",
            json={
                "name": "Cash",
                "entity_id": entity_id,
                "account_type": "asset",
                "sub_type": "cash",
            },
        )
        cash_id = cash_response.json()["id"]

        income_response = test_client.post(
            "/accounts",
            json={
                "name": "Revenue",
                "entity_id": entity_id,
                "account_type": "income",
            },
        )
        income_id = income_response.json()["id"]

        # Post transaction
        payload = {
            "transaction_date": "2025-01-15",
            "memo": "Test transaction",
            "entries": [
                {
                    "account_id": cash_id,
                    "debit_amount": "1000.00",
                    "credit_amount": "0",
                },
                {
                    "account_id": income_id,
                    "debit_amount": "0",
                    "credit_amount": "1000.00",
                },
            ],
        }
        response = test_client.post("/transactions", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["memo"] == "Test transaction"
        assert len(data["entries"]) == 2

    def test_post_unbalanced_transaction_returns_422(self, test_client: Client) -> None:
        # Create entity and accounts
        entity_response = test_client.post(
            "/entities",
            json={"name": "Unbalanced Test", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        cash_response = test_client.post(
            "/accounts",
            json={
                "name": "Cash Unbalanced",
                "entity_id": entity_id,
                "account_type": "asset",
            },
        )
        cash_id = cash_response.json()["id"]

        income_response = test_client.post(
            "/accounts",
            json={
                "name": "Revenue Unbalanced",
                "entity_id": entity_id,
                "account_type": "income",
            },
        )
        income_id = income_response.json()["id"]

        # Post unbalanced transaction (debits != credits)
        payload = {
            "transaction_date": "2025-01-15",
            "memo": "Unbalanced",
            "entries": [
                {
                    "account_id": cash_id,
                    "debit_amount": "1000.00",
                    "credit_amount": "0",
                },
                {
                    "account_id": income_id,
                    "debit_amount": "0",
                    "credit_amount": "500.00",  # Not balanced!
                },
            ],
        }
        response = test_client.post("/transactions", json=payload)
        assert response.status_code == 422

    def test_list_transactions_returns_empty(self, test_client: Client) -> None:
        response = test_client.get("/transactions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_transactions_filter_by_account_id(self, test_client: Client) -> None:
        # Create entity and accounts
        entity_response = test_client.post(
            "/entities",
            json={"name": "Filter Test", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        account1_response = test_client.post(
            "/accounts",
            json={
                "name": "Account 1",
                "entity_id": entity_id,
                "account_type": "asset",
            },
        )
        account1_id = account1_response.json()["id"]

        account2_response = test_client.post(
            "/accounts",
            json={
                "name": "Account 2",
                "entity_id": entity_id,
                "account_type": "equity",
            },
        )
        account2_id = account2_response.json()["id"]

        # Post transaction
        test_client.post(
            "/transactions",
            json={
                "transaction_date": "2025-01-20",
                "memo": "Test txn",
                "entries": [
                    {
                        "account_id": account1_id,
                        "debit_amount": "500.00",
                        "credit_amount": "0",
                    },
                    {
                        "account_id": account2_id,
                        "debit_amount": "0",
                        "credit_amount": "500.00",
                    },
                ],
            },
        )

        # Filter by account_id
        response = test_client.get(f"/transactions?account_id={account1_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_transactions_filter_by_date_range(self, test_client: Client) -> None:
        # Create entity and accounts
        entity_response = test_client.post(
            "/entities",
            json={"name": "Date Range Test", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        cash_response = test_client.post(
            "/accounts",
            json={
                "name": "Cash DR",
                "entity_id": entity_id,
                "account_type": "asset",
            },
        )
        cash_id = cash_response.json()["id"]

        equity_response = test_client.post(
            "/accounts",
            json={
                "name": "Equity DR",
                "entity_id": entity_id,
                "account_type": "equity",
            },
        )
        equity_id = equity_response.json()["id"]

        # Post transactions on different dates
        test_client.post(
            "/transactions",
            json={
                "transaction_date": "2025-01-01",
                "memo": "Jan 1",
                "entries": [
                    {
                        "account_id": cash_id,
                        "debit_amount": "100.00",
                        "credit_amount": "0",
                    },
                    {
                        "account_id": equity_id,
                        "debit_amount": "0",
                        "credit_amount": "100.00",
                    },
                ],
            },
        )
        test_client.post(
            "/transactions",
            json={
                "transaction_date": "2025-02-15",
                "memo": "Feb 15",
                "entries": [
                    {
                        "account_id": cash_id,
                        "debit_amount": "200.00",
                        "credit_amount": "0",
                    },
                    {
                        "account_id": equity_id,
                        "debit_amount": "0",
                        "credit_amount": "200.00",
                    },
                ],
            },
        )

        # Filter by date range
        response = test_client.get(
            "/transactions?start_date=2025-01-01&end_date=2025-01-31"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["memo"] == "Jan 1"


class TestReportEndpoints:
    """Tests for /reports endpoints."""

    def test_net_worth_report_empty(self, test_client: Client) -> None:
        response = test_client.get("/reports/net-worth?as_of_date=2025-01-28")
        assert response.status_code == 200
        data = response.json()
        assert data["report_name"] == "Net Worth Report"
        assert "totals" in data

    def test_net_worth_report_with_data(self, test_client: Client) -> None:
        # Create entity with accounts and transactions
        entity_response = test_client.post(
            "/entities",
            json={"name": "Net Worth Entity", "entity_type": "individual"},
        )
        entity_id = entity_response.json()["id"]

        # Create asset and liability accounts
        asset_response = test_client.post(
            "/accounts",
            json={
                "name": "Bank Account",
                "entity_id": entity_id,
                "account_type": "asset",
            },
        )
        asset_id = asset_response.json()["id"]

        liability_response = test_client.post(
            "/accounts",
            json={
                "name": "Credit Card",
                "entity_id": entity_id,
                "account_type": "liability",
            },
        )
        liability_id = liability_response.json()["id"]

        equity_response = test_client.post(
            "/accounts",
            json={
                "name": "Equity",
                "entity_id": entity_id,
                "account_type": "equity",
            },
        )
        equity_id = equity_response.json()["id"]

        # Post opening balance transaction
        test_client.post(
            "/transactions",
            json={
                "transaction_date": "2025-01-01",
                "memo": "Opening balance",
                "entries": [
                    {
                        "account_id": asset_id,
                        "debit_amount": "10000.00",
                        "credit_amount": "0",
                    },
                    {
                        "account_id": liability_id,
                        "debit_amount": "0",
                        "credit_amount": "2000.00",
                    },
                    {
                        "account_id": equity_id,
                        "debit_amount": "0",
                        "credit_amount": "8000.00",
                    },
                ],
            },
        )

        # Get net worth report
        response = test_client.get("/reports/net-worth?as_of_date=2025-01-28")
        assert response.status_code == 200
        data = response.json()
        assert data["report_name"] == "Net Worth Report"
        # Check the entity is in the report
        assert len(data["data"]) >= 1

    def test_balance_sheet_report(self, test_client: Client) -> None:
        # Create entity
        entity_response = test_client.post(
            "/entities",
            json={"name": "Balance Sheet Entity", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        response = test_client.get(
            f"/reports/balance-sheet/{entity_id}?as_of_date=2025-01-28"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["report_name"] == "Balance Sheet"
        assert "data" in data
        assert "assets" in data["data"]
        assert "liabilities" in data["data"]
        assert "equity" in data["data"]

    def test_balance_sheet_invalid_entity_returns_404(
        self, test_client: Client
    ) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(
            f"/reports/balance-sheet/{fake_id}?as_of_date=2025-01-28"
        )
        assert response.status_code == 404
