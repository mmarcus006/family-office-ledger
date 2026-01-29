"""Tests for Budget API endpoints."""

import pytest
from httpx import Client

from family_office_ledger.api.app import create_app, get_db
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
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

    def override_get_db() -> SQLiteDatabase:
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[SQLiteDatabase] = override_get_db

    return TestClient(app)


@pytest.fixture
def test_entity(test_db: SQLiteDatabase) -> Entity:
    """Create a test entity."""
    entity_repo = SQLiteEntityRepository(test_db)
    entity = Entity(
        name="Test Entity",
        entity_type=EntityType.LLC,
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def test_account(test_db: SQLiteDatabase, test_entity: Entity) -> Account:
    """Create a test account."""
    account_repo = SQLiteAccountRepository(test_db)
    account = Account(
        name="Test Account",
        entity_id=test_entity.id,
        account_type=AccountType.EXPENSE,
        sub_type=AccountSubType.OTHER,
        currency="USD",
    )
    account_repo.add(account)
    return account


class TestBudgetCreateEndpoint:
    """Tests for POST /budgets endpoint."""

    def test_create_budget_returns_201(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        response = test_client.post("/budgets", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Q1 Budget"
        assert data["entity_id"] == str(test_entity.id)
        assert data["period_type"] == "quarterly"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_budget_with_monthly_period(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        payload = {
            "name": "January Budget",
            "entity_id": str(test_entity.id),
            "period_type": "monthly",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        }
        response = test_client.post("/budgets", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["period_type"] == "monthly"

    def test_create_budget_invalid_entity_returns_404(
        self, test_client: Client
    ) -> None:
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        payload = {
            "name": "Invalid Budget",
            "entity_id": fake_uuid,
            "period_type": "annual",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        }
        response = test_client.post("/budgets", json=payload)
        assert response.status_code == 404

    def test_create_budget_invalid_period_type_returns_422(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        payload = {
            "name": "Invalid Budget",
            "entity_id": str(test_entity.id),
            "period_type": "invalid",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        }
        response = test_client.post("/budgets", json=payload)
        assert response.status_code == 422


class TestBudgetListEndpoint:
    """Tests for GET /budgets endpoint."""

    def test_list_budgets_returns_empty_list(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        response = test_client.get(f"/budgets?entity_id={test_entity.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["budgets"] == []
        assert data["total"] == 0

    def test_list_budgets_returns_created_budgets(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        test_client.post("/budgets", json=payload)

        response = test_client.get(f"/budgets?entity_id={test_entity.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["budgets"]) == 1
        assert data["budgets"][0]["name"] == "Q1 Budget"
        assert data["total"] == 1


class TestBudgetGetEndpoint:
    """Tests for GET /budgets/{budget_id} endpoint."""

    def test_get_budget_returns_200(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        create_response = test_client.post("/budgets", json=payload)
        budget_id = create_response.json()["id"]

        response = test_client.get(f"/budgets/{budget_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == budget_id
        assert data["name"] == "Q1 Budget"

    def test_get_budget_not_found_returns_404(self, test_client: Client) -> None:
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/budgets/{fake_uuid}")
        assert response.status_code == 404


class TestBudgetDeleteEndpoint:
    """Tests for DELETE /budgets/{budget_id} endpoint."""

    def test_delete_budget_returns_204(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        create_response = test_client.post("/budgets", json=payload)
        budget_id = create_response.json()["id"]

        response = test_client.delete(f"/budgets/{budget_id}")
        assert response.status_code == 204

    def test_delete_budget_not_found_returns_404(self, test_client: Client) -> None:
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = test_client.delete(f"/budgets/{fake_uuid}")
        assert response.status_code == 404


class TestBudgetLineItemEndpoint:
    """Tests for POST /budgets/{budget_id}/line-items endpoint."""

    def test_add_line_item_returns_201(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        budget_payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        budget_response = test_client.post("/budgets", json=budget_payload)
        budget_id = budget_response.json()["id"]

        line_item_payload = {
            "category": "Office Supplies",
            "budgeted_amount": "1000.00",
            "budgeted_currency": "USD",
            "notes": "Q1 office supplies",
        }
        response = test_client.post(
            f"/budgets/{budget_id}/line-items", json=line_item_payload
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "Office Supplies"
        assert data["budgeted_amount"] == "1000.00"
        assert data["budgeted_currency"] == "USD"
        assert "id" in data

    def test_add_line_item_to_nonexistent_budget_returns_404(
        self, test_client: Client
    ) -> None:
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        line_item_payload = {
            "category": "Office Supplies",
            "budgeted_amount": "1000.00",
            "budgeted_currency": "USD",
        }
        response = test_client.post(
            f"/budgets/{fake_uuid}/line-items", json=line_item_payload
        )
        assert response.status_code == 404


class TestBudgetLineItemListEndpoint:
    """Tests for GET /budgets/{budget_id}/line-items endpoint."""

    def test_list_line_items_returns_empty_list(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        budget_payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        budget_response = test_client.post("/budgets", json=budget_payload)
        budget_id = budget_response.json()["id"]

        response = test_client.get(f"/budgets/{budget_id}/line-items")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_line_items_returns_added_items(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        budget_payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        budget_response = test_client.post("/budgets", json=budget_payload)
        budget_id = budget_response.json()["id"]

        line_item_payload = {
            "category": "Office Supplies",
            "budgeted_amount": "1000.00",
            "budgeted_currency": "USD",
        }
        test_client.post(f"/budgets/{budget_id}/line-items", json=line_item_payload)

        response = test_client.get(f"/budgets/{budget_id}/line-items")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "Office Supplies"


class TestBudgetVarianceEndpoint:
    """Tests for GET /budgets/{budget_id}/variance endpoint."""

    def test_get_variance_returns_200(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        budget_payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        budget_response = test_client.post("/budgets", json=budget_payload)
        budget_id = budget_response.json()["id"]

        line_item_payload = {
            "category": "Office Supplies",
            "budgeted_amount": "1000.00",
            "budgeted_currency": "USD",
        }
        test_client.post(f"/budgets/{budget_id}/line-items", json=line_item_payload)

        response = test_client.get(
            f"/budgets/{budget_id}/variance?start_date=2025-01-01&end_date=2025-03-31"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "category" in data[0]
        assert "budgeted" in data[0]
        assert "actual" in data[0]

    def test_get_variance_nonexistent_budget_returns_404(
        self, test_client: Client
    ) -> None:
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(
            f"/budgets/{fake_uuid}/variance?start_date=2025-01-01&end_date=2025-03-31"
        )
        assert response.status_code == 404


class TestBudgetAlertsEndpoint:
    """Tests for GET /budgets/{budget_id}/alerts endpoint."""

    def test_get_alerts_returns_200(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        budget_payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        budget_response = test_client.post("/budgets", json=budget_payload)
        budget_id = budget_response.json()["id"]

        line_item_payload = {
            "category": "Office Supplies",
            "budgeted_amount": "1000.00",
            "budgeted_currency": "USD",
        }
        test_client.post(f"/budgets/{budget_id}/line-items", json=line_item_payload)

        response = test_client.get(f"/budgets/{budget_id}/alerts?threshold=80")
        assert response.status_code == 200
        data = response.json()
        assert "budget_id" in data
        assert "alerts" in data
        assert "total_alerts" in data
        assert data["budget_id"] == budget_id

    def test_get_alerts_nonexistent_budget_returns_404(
        self, test_client: Client
    ) -> None:
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/budgets/{fake_uuid}/alerts?threshold=80")
        assert response.status_code == 404

    def test_get_alerts_with_custom_threshold(
        self, test_client: Client, test_entity: Entity
    ) -> None:
        budget_payload = {
            "name": "Q1 Budget",
            "entity_id": str(test_entity.id),
            "period_type": "quarterly",
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
        }
        budget_response = test_client.post("/budgets", json=budget_payload)
        budget_id = budget_response.json()["id"]

        line_item_payload = {
            "category": "Office Supplies",
            "budgeted_amount": "1000.00",
            "budgeted_currency": "USD",
        }
        test_client.post(f"/budgets/{budget_id}/line-items", json=line_item_payload)

        response = test_client.get(f"/budgets/{budget_id}/alerts?threshold=50")
        assert response.status_code == 200
        data = response.json()
        assert data["budget_id"] == budget_id
