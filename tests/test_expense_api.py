"""Tests for expense and vendor API endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from httpx import Client

from family_office_ledger.api.app import create_app, get_db
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    Money,
)
from family_office_ledger.domain.vendors import Vendor
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)


@pytest.fixture
def test_db() -> SQLiteDatabase:
    db = SQLiteDatabase(":memory:", check_same_thread=False)
    db.initialize()
    return db


@pytest.fixture
def test_client(test_db: SQLiteDatabase) -> Client:
    from starlette.testclient import TestClient

    app = create_app()

    def override_get_db() -> SQLiteDatabase:
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[SQLiteDatabase] = override_get_db

    return TestClient(app)


@pytest.fixture
def sample_entity(test_db: SQLiteDatabase) -> Entity:
    entity = Entity(name="Test LLC", entity_type=EntityType.LLC)
    SQLiteEntityRepository(test_db).add(entity)
    return entity


@pytest.fixture
def sample_expense_account(test_db: SQLiteDatabase, sample_entity: Entity) -> Account:
    account = Account(
        name="Office Supplies",
        entity_id=sample_entity.id,
        account_type=AccountType.EXPENSE,
        sub_type=AccountSubType.OTHER,
    )
    SQLiteAccountRepository(test_db).add(account)
    return account


@pytest.fixture
def sample_asset_account(test_db: SQLiteDatabase, sample_entity: Entity) -> Account:
    account = Account(
        name="Checking",
        entity_id=sample_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )
    SQLiteAccountRepository(test_db).add(account)
    return account


@pytest.fixture
def sample_vendor(test_db: SQLiteDatabase) -> Vendor:
    vendor = Vendor(
        name="Staples",
        category="office_supplies",
        tax_id="12-3456789",
        is_1099_eligible=True,
        contact_email="billing@staples.com",
    )
    SQLiteVendorRepository(test_db).add(vendor)
    return vendor


class TestVendorEndpoints:
    def test_create_vendor_returns_201(self, test_client: Client) -> None:
        payload = {
            "name": "ACME Corp",
            "category": "consulting",
            "is_1099_eligible": True,
        }
        response = test_client.post("/vendors", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "ACME Corp"
        assert data["category"] == "consulting"
        assert data["is_1099_eligible"] is True
        assert "id" in data

    def test_create_vendor_with_minimal_fields(self, test_client: Client) -> None:
        payload = {"name": "Simple Vendor"}
        response = test_client.post("/vendors", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Simple Vendor"
        assert data["is_1099_eligible"] is False

    def test_create_vendor_invalid_empty_name_returns_422(
        self, test_client: Client
    ) -> None:
        payload = {"name": ""}
        response = test_client.post("/vendors", json=payload)
        assert response.status_code == 422

    def test_list_vendors_returns_empty(self, test_client: Client) -> None:
        response = test_client.get("/vendors")
        assert response.status_code == 200
        data = response.json()
        assert data["vendors"] == []
        assert data["total"] == 0

    def test_list_vendors_returns_created_vendors(self, test_client: Client) -> None:
        test_client.post("/vendors", json={"name": "Vendor 1"})
        test_client.post("/vendors", json={"name": "Vendor 2"})

        response = test_client.get("/vendors")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        names = [v["name"] for v in data["vendors"]]
        assert "Vendor 1" in names
        assert "Vendor 2" in names

    def test_get_vendor_by_id(self, test_client: Client, sample_vendor: Vendor) -> None:
        response = test_client.get(f"/vendors/{sample_vendor.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Staples"
        assert data["id"] == str(sample_vendor.id)

    def test_get_vendor_not_found_returns_404(self, test_client: Client) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/vendors/{fake_id}")
        assert response.status_code == 404

    def test_update_vendor(self, test_client: Client, sample_vendor: Vendor) -> None:
        payload = {
            "name": "Staples Updated",
            "category": "supplies",
        }
        response = test_client.put(f"/vendors/{sample_vendor.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Staples Updated"
        assert data["category"] == "supplies"

    def test_update_vendor_partial(
        self, test_client: Client, sample_vendor: Vendor
    ) -> None:
        payload = {"notes": "Preferred vendor"}
        response = test_client.put(f"/vendors/{sample_vendor.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Preferred vendor"
        assert data["name"] == "Staples"

    def test_update_vendor_not_found_returns_404(self, test_client: Client) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.put(f"/vendors/{fake_id}", json={"name": "Test"})
        assert response.status_code == 404

    def test_delete_vendor(self, test_client: Client, sample_vendor: Vendor) -> None:
        response = test_client.delete(f"/vendors/{sample_vendor.id}")
        assert response.status_code == 204

        response = test_client.get(f"/vendors/{sample_vendor.id}")
        assert response.status_code == 404

    def test_delete_vendor_not_found_returns_404(self, test_client: Client) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.delete(f"/vendors/{fake_id}")
        assert response.status_code == 404

    def test_search_vendors_by_name(self, test_client: Client) -> None:
        test_client.post("/vendors", json={"name": "Office Depot"})
        test_client.post("/vendors", json={"name": "Staples Office"})
        test_client.post("/vendors", json={"name": "Amazon"})

        response = test_client.get("/vendors/search", params={"name": "Office"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        names = [v["name"] for v in data["vendors"]]
        assert "Office Depot" in names
        assert "Staples Office" in names
        assert "Amazon" not in names

    def test_search_vendors_no_results(self, test_client: Client) -> None:
        response = test_client.get("/vendors/search", params={"name": "NonExistent"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestExpenseEndpoints:
    def test_categorize_transaction(
        self,
        test_client: Client,
        test_db: SQLiteDatabase,
        sample_expense_account: Account,
        sample_asset_account: Account,
        sample_vendor: Vendor,
    ) -> None:
        txn = Transaction(
            transaction_date=date(2025, 1, 15),
            entries=[
                Entry(
                    account_id=sample_expense_account.id,
                    debit_amount=Money(Decimal("100.00")),
                    credit_amount=Money(Decimal("0")),
                ),
                Entry(
                    account_id=sample_asset_account.id,
                    debit_amount=Money(Decimal("0")),
                    credit_amount=Money(Decimal("100.00")),
                ),
            ],
            memo="Office supplies purchase",
        )
        SQLiteTransactionRepository(test_db).add(txn)

        payload = {
            "category": "office_supplies",
            "tags": ["2025", "Q1"],
            "vendor_id": str(sample_vendor.id),
        }
        response = test_client.post(
            f"/expenses/transactions/{txn.id}/categorize",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(txn.id)

    def test_categorize_transaction_not_found(self, test_client: Client) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        payload = {"category": "test"}
        response = test_client.post(
            f"/expenses/transactions/{fake_id}/categorize",
            json=payload,
        )
        assert response.status_code == 404

    def test_get_expense_summary(
        self,
        test_client: Client,
        test_db: SQLiteDatabase,
        sample_entity: Entity,
        sample_expense_account: Account,
        sample_asset_account: Account,
    ) -> None:
        for i in range(3):
            txn = Transaction(
                transaction_date=date(2025, 1, 10 + i),
                entries=[
                    Entry(
                        account_id=sample_expense_account.id,
                        debit_amount=Money(Decimal("50.00")),
                        credit_amount=Money(Decimal("0")),
                    ),
                    Entry(
                        account_id=sample_asset_account.id,
                        debit_amount=Money(Decimal("0")),
                        credit_amount=Money(Decimal("50.00")),
                    ),
                ],
                memo=f"Expense {i + 1}",
            )
            SQLiteTransactionRepository(test_db).add(txn)

        response = test_client.get(
            "/expenses/summary",
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "entity_ids": [str(sample_entity.id)],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["transaction_count"] == 3
        assert data["total_expenses"] == "150.00"
        assert data["start_date"] == "2025-01-01"
        assert data["end_date"] == "2025-01-31"

    def test_get_expense_summary_empty(
        self,
        test_client: Client,
        sample_entity: Entity,
    ) -> None:
        response = test_client.get(
            "/expenses/summary",
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "entity_ids": [str(sample_entity.id)],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["transaction_count"] == 0
        assert data["total_expenses"] == "0"

    def test_get_expenses_by_category(
        self,
        test_client: Client,
        test_db: SQLiteDatabase,
        sample_entity: Entity,
        sample_expense_account: Account,
        sample_asset_account: Account,
    ) -> None:
        txn = Transaction(
            transaction_date=date(2025, 1, 15),
            entries=[
                Entry(
                    account_id=sample_expense_account.id,
                    debit_amount=Money(Decimal("75.00")),
                    credit_amount=Money(Decimal("0")),
                ),
                Entry(
                    account_id=sample_asset_account.id,
                    debit_amount=Money(Decimal("0")),
                    credit_amount=Money(Decimal("75.00")),
                ),
            ],
            memo="Test expense",
            category="supplies",
        )
        SQLiteTransactionRepository(test_db).add(txn)

        response = test_client.get(
            "/expenses/by-category",
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "entity_ids": [str(sample_entity.id)],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "total" in data

    def test_get_expenses_by_vendor(
        self,
        test_client: Client,
        test_db: SQLiteDatabase,
        sample_entity: Entity,
        sample_expense_account: Account,
        sample_asset_account: Account,
        sample_vendor: Vendor,
    ) -> None:
        txn = Transaction(
            transaction_date=date(2025, 1, 15),
            entries=[
                Entry(
                    account_id=sample_expense_account.id,
                    debit_amount=Money(Decimal("100.00")),
                    credit_amount=Money(Decimal("0")),
                ),
                Entry(
                    account_id=sample_asset_account.id,
                    debit_amount=Money(Decimal("0")),
                    credit_amount=Money(Decimal("100.00")),
                ),
            ],
            memo="Vendor purchase",
            vendor_id=sample_vendor.id,
        )
        SQLiteTransactionRepository(test_db).add(txn)

        response = test_client.get(
            "/expenses/by-vendor",
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "entity_ids": [str(sample_entity.id)],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "vendors" in data
        assert "total" in data

    def test_get_recurring_expenses(
        self,
        test_client: Client,
        sample_entity: Entity,
    ) -> None:
        response = test_client.get(
            "/expenses/recurring",
            params={
                "entity_id": str(sample_entity.id),
                "lookback_months": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "recurring_expenses" in data
        assert "total" in data

    def test_get_recurring_expenses_requires_entity_id(
        self, test_client: Client
    ) -> None:
        response = test_client.get("/expenses/recurring")
        assert response.status_code == 422
