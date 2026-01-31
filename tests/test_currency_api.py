"""Tests for currency API endpoints."""


import pytest
from httpx import Client

from family_office_ledger.api.app import create_app, get_db
from family_office_ledger.repositories.sqlite import SQLiteDatabase


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


class TestExchangeRateEndpoints:
    def test_add_exchange_rate_returns_201(self, test_client: Client) -> None:
        payload = {
            "from_currency": "USD",
            "to_currency": "EUR",
            "rate": "0.92",
            "effective_date": "2025-01-15",
            "source": "manual",
        }
        response = test_client.post("/currency/rates", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "EUR"
        assert data["rate"] == "0.92"
        assert data["effective_date"] == "2025-01-15"
        assert data["source"] == "manual"
        assert "id" in data
        assert "created_at" in data

    def test_add_exchange_rate_with_default_source(self, test_client: Client) -> None:
        payload = {
            "from_currency": "GBP",
            "to_currency": "USD",
            "rate": "1.25",
            "effective_date": "2025-01-15",
        }
        response = test_client.post("/currency/rates", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == "manual"

    def test_add_exchange_rate_invalid_currency_length(
        self, test_client: Client
    ) -> None:
        payload = {
            "from_currency": "US",
            "to_currency": "EUR",
            "rate": "0.92",
            "effective_date": "2025-01-15",
        }
        response = test_client.post("/currency/rates", json=payload)
        assert response.status_code == 422

    def test_get_exchange_rate_by_id(self, test_client: Client) -> None:
        payload = {
            "from_currency": "USD",
            "to_currency": "JPY",
            "rate": "150.5",
            "effective_date": "2025-01-15",
        }
        create_response = test_client.post("/currency/rates", json=payload)
        rate_id = create_response.json()["id"]

        response = test_client.get(f"/currency/rates/{rate_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rate_id
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "JPY"

    def test_get_exchange_rate_not_found(self, test_client: Client) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/currency/rates/{fake_id}")
        assert response.status_code == 404

    def test_list_exchange_rates_by_currency_pair(self, test_client: Client) -> None:
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": "0.91",
                "effective_date": "2025-01-14",
            },
        )
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": "0.92",
                "effective_date": "2025-01-15",
            },
        )
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "GBP",
                "rate": "0.80",
                "effective_date": "2025-01-15",
            },
        )

        response = test_client.get(
            "/currency/rates",
            params={"from_currency": "USD", "to_currency": "EUR"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["rates"]) == 2

    def test_list_exchange_rates_with_date_filter(self, test_client: Client) -> None:
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": "0.91",
                "effective_date": "2025-01-14",
            },
        )
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": "0.92",
                "effective_date": "2025-01-15",
            },
        )

        response = test_client.get(
            "/currency/rates",
            params={
                "from_currency": "USD",
                "to_currency": "EUR",
                "start_date": "2025-01-15",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["rates"][0]["rate"] == "0.92"

    def test_get_latest_exchange_rate(self, test_client: Client) -> None:
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "CHF",
                "rate": "0.88",
                "effective_date": "2025-01-14",
            },
        )
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "CHF",
                "rate": "0.89",
                "effective_date": "2025-01-15",
            },
        )

        response = test_client.get(
            "/currency/rates/latest",
            params={"from_currency": "USD", "to_currency": "CHF"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rate"] == "0.89"
        assert data["effective_date"] == "2025-01-15"

    def test_get_latest_exchange_rate_not_found(self, test_client: Client) -> None:
        response = test_client.get(
            "/currency/rates/latest",
            params={"from_currency": "USD", "to_currency": "XYZ"},
        )
        assert response.status_code == 404

    def test_delete_exchange_rate(self, test_client: Client) -> None:
        create_response = test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "CAD",
                "rate": "1.35",
                "effective_date": "2025-01-15",
            },
        )
        rate_id = create_response.json()["id"]

        delete_response = test_client.delete(f"/currency/rates/{rate_id}")
        assert delete_response.status_code == 204

        get_response = test_client.get(f"/currency/rates/{rate_id}")
        assert get_response.status_code == 404

    def test_delete_exchange_rate_not_found(self, test_client: Client) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.delete(f"/currency/rates/{fake_id}")
        assert response.status_code == 404


class TestCurrencyConversionEndpoints:
    def test_convert_currency(self, test_client: Client) -> None:
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": "0.92",
                "effective_date": "2025-01-15",
            },
        )

        payload = {
            "amount": "100.00",
            "from_currency": "USD",
            "to_currency": "EUR",
            "as_of_date": "2025-01-15",
        }
        response = test_client.post("/currency/convert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["original_amount"] == "100.00"
        assert data["original_currency"] == "USD"
        assert data["converted_amount"] == "92.0000"
        assert data["converted_currency"] == "EUR"
        assert data["rate_used"] == "0.92"
        assert data["as_of_date"] == "2025-01-15"

    def test_convert_currency_with_inverse_rate(self, test_client: Client) -> None:
        test_client.post(
            "/currency/rates",
            json={
                "from_currency": "EUR",
                "to_currency": "USD",
                "rate": "1.09",
                "effective_date": "2025-01-15",
            },
        )

        payload = {
            "amount": "100.00",
            "from_currency": "USD",
            "to_currency": "EUR",
            "as_of_date": "2025-01-15",
        }
        response = test_client.post("/currency/convert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["rate_used"] == "inverse"

    def test_convert_currency_rate_not_found(self, test_client: Client) -> None:
        payload = {
            "amount": "100.00",
            "from_currency": "USD",
            "to_currency": "XYZ",
            "as_of_date": "2025-01-15",
        }
        response = test_client.post("/currency/convert", json=payload)
        assert response.status_code == 404

    def test_convert_same_currency(self, test_client: Client) -> None:
        payload = {
            "amount": "100.00",
            "from_currency": "USD",
            "to_currency": "USD",
            "as_of_date": "2025-01-15",
        }
        response = test_client.post("/currency/convert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["converted_amount"] == "100.00"


class TestEntryWithCurrencyFields:
    def test_create_transaction_with_default_currency(
        self, test_client: Client
    ) -> None:
        entity_response = test_client.post(
            "/entities",
            json={"name": "Test Entity", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        asset_response = test_client.post(
            "/accounts",
            json={
                "name": "Cash",
                "entity_id": entity_id,
                "account_type": "asset",
            },
        )
        asset_id = asset_response.json()["id"]

        equity_response = test_client.post(
            "/accounts",
            json={
                "name": "Equity",
                "entity_id": entity_id,
                "account_type": "equity",
            },
        )
        equity_id = equity_response.json()["id"]

        txn_payload = {
            "transaction_date": "2025-01-15",
            "entries": [
                {
                    "account_id": asset_id,
                    "debit_amount": "1000.00",
                    "credit_amount": "0",
                },
                {
                    "account_id": equity_id,
                    "debit_amount": "0",
                    "credit_amount": "1000.00",
                },
            ],
            "memo": "Initial contribution",
        }
        response = test_client.post("/transactions", json=txn_payload)
        assert response.status_code == 201
        data = response.json()

        assert data["entries"][0]["debit_currency"] == "USD"
        assert data["entries"][0]["credit_currency"] == "USD"
        assert data["entries"][1]["debit_currency"] == "USD"
        assert data["entries"][1]["credit_currency"] == "USD"

    def test_create_transaction_with_explicit_currency(
        self, test_client: Client
    ) -> None:
        entity_response = test_client.post(
            "/entities",
            json={"name": "Test Entity", "entity_type": "llc"},
        )
        entity_id = entity_response.json()["id"]

        asset_response = test_client.post(
            "/accounts",
            json={
                "name": "Cash EUR",
                "entity_id": entity_id,
                "account_type": "asset",
                "currency": "EUR",
            },
        )
        asset_id = asset_response.json()["id"]

        equity_response = test_client.post(
            "/accounts",
            json={
                "name": "Equity EUR",
                "entity_id": entity_id,
                "account_type": "equity",
                "currency": "EUR",
            },
        )
        equity_id = equity_response.json()["id"]

        txn_payload = {
            "transaction_date": "2025-01-15",
            "entries": [
                {
                    "account_id": asset_id,
                    "debit_amount": "1000.00",
                    "debit_currency": "EUR",
                    "credit_amount": "0",
                    "credit_currency": "EUR",
                },
                {
                    "account_id": equity_id,
                    "debit_amount": "0",
                    "debit_currency": "EUR",
                    "credit_amount": "1000.00",
                    "credit_currency": "EUR",
                },
            ],
            "memo": "EUR contribution",
        }
        response = test_client.post("/transactions", json=txn_payload)
        assert response.status_code == 201
        data = response.json()

        assert data["entries"][0]["debit_currency"] == "EUR"
        assert data["entries"][0]["credit_currency"] == "EUR"
