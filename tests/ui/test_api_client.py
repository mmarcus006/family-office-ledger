from __future__ import annotations

from datetime import date

import pytest


class TestLedgerAPIClient:
    async def test_list_entities_empty(self, api_client) -> None:
        result = await api_client.list_entities()
        assert result == []

    async def test_create_entity(self, api_client) -> None:
        entity = await api_client.create_entity(name="Test LLC", entity_type="llc")
        assert entity["name"] == "Test LLC"
        assert entity["entity_type"] == "llc"
        assert "id" in entity

        entities = await api_client.list_entities()
        assert len(entities) == 1

    async def test_create_account_requires_entity(self, api_client) -> None:
        from family_office_ledger.ui.api_client import APIError

        with pytest.raises(APIError) as exc:
            await api_client.create_account(
                name="Checking",
                entity_id="00000000-0000-0000-0000-000000000000",
                account_type="asset",
            )

        assert exc.value.status_code == 404

    async def test_post_balanced_transaction(self, api_client) -> None:
        entity = await api_client.create_entity(name="Test", entity_type="llc")
        checking = await api_client.create_account(
            name="Checking", entity_id=entity["id"], account_type="asset"
        )
        expense = await api_client.create_account(
            name="Rent", entity_id=entity["id"], account_type="expense"
        )

        txn = await api_client.post_transaction(
            transaction_date=date(2026, 1, 28),
            entries=[
                {
                    "account_id": expense["id"],
                    "debit_amount": "1000.00",
                    "credit_amount": "0",
                    "memo": "",
                },
                {
                    "account_id": checking["id"],
                    "debit_amount": "0",
                    "credit_amount": "1000.00",
                    "memo": "",
                },
            ],
            memo="Rent payment",
        )

        assert "id" in txn
        assert len(txn["entries"]) == 2

    async def test_post_unbalanced_transaction_fails(self, api_client) -> None:
        from family_office_ledger.ui.api_client import APIError

        entity = await api_client.create_entity(name="Test", entity_type="llc")
        checking = await api_client.create_account(
            name="Checking", entity_id=entity["id"], account_type="asset"
        )

        with pytest.raises(APIError) as exc:
            await api_client.post_transaction(
                transaction_date=date(2026, 1, 28),
                entries=[
                    {
                        "account_id": checking["id"],
                        "debit_amount": "1000.00",
                        "credit_amount": "0",
                        "memo": "",
                    }
                ],
                memo="Unbalanced",
            )
        assert exc.value.status_code in {422, 400}
