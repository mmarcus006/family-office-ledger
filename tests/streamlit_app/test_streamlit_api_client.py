"""Tests for Streamlit API client functions."""

from __future__ import annotations

from datetime import date

import pytest


class TestAuditAPIClient:
    """Tests for audit API client functions."""

    def test_list_audit_entries(self, mock_httpx_client) -> None:
        """Test listing audit entries."""
        from family_office_ledger.streamlit_app import api_client

        # Call without filters
        result = api_client.list_audit_entries()
        # API returns empty list or dict for new DB
        assert isinstance(result, (list, dict))

    def test_list_audit_entries_with_filters(self, mock_httpx_client) -> None:
        """Test listing audit entries with filters."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.list_audit_entries(
            entity_type="entity",
            action="create",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            limit=50,
        )
        assert isinstance(result, (list, dict))

    def test_get_audit_summary(self, mock_httpx_client) -> None:
        """Test getting audit summary."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.get_audit_summary(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert isinstance(result, dict)


class TestCurrencyAPIClient:
    """Tests for currency API client functions."""

    def test_list_exchange_rates_empty(self, mock_httpx_client) -> None:
        """Test listing exchange rates when none exist."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.list_exchange_rates()
        assert isinstance(result, (list, dict))

    def test_add_and_list_exchange_rate(self, mock_httpx_client) -> None:
        """Test adding and listing exchange rates."""
        from family_office_ledger.streamlit_app import api_client

        # Add a rate
        result = api_client.add_exchange_rate(
            from_currency="USD",
            to_currency="EUR",
            rate="0.85",
            effective_date=date(2024, 1, 15),
            source="manual",
        )
        assert isinstance(result, dict)
        assert "id" in result or "data" in result

    def test_convert_currency(self, mock_httpx_client) -> None:
        """Test currency conversion."""
        from family_office_ledger.streamlit_app import api_client

        # First add an exchange rate
        api_client.add_exchange_rate(
            from_currency="USD",
            to_currency="EUR",
            rate="0.85",
            effective_date=date(2024, 1, 15),
        )

        # Then convert
        result = api_client.convert_currency(
            amount="100.00",
            from_currency="USD",
            to_currency="EUR",
            as_of_date=date(2024, 1, 15),
        )
        assert isinstance(result, dict)


class TestPortfolioAPIClient:
    """Tests for portfolio API client functions."""

    def test_get_portfolio_summary(self, mock_httpx_client) -> None:
        """Test getting portfolio summary."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.get_portfolio_summary(
            entity_ids=None,
            as_of_date=date.today(),
        )
        assert isinstance(result, dict)

    def test_get_asset_allocation(self, mock_httpx_client) -> None:
        """Test getting asset allocation."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.get_asset_allocation(
            entity_ids=None,
            as_of_date=date.today(),
        )
        assert isinstance(result, dict)

    def test_get_concentration_report(self, mock_httpx_client) -> None:
        """Test getting concentration report."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.get_concentration_report(
            entity_ids=None,
            as_of_date=date.today(),
            top_n=10,
        )
        assert isinstance(result, dict)

    def test_get_performance_report(self, mock_httpx_client) -> None:
        """Test getting performance report."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.get_performance_report(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            entity_ids=None,
        )
        assert isinstance(result, dict)


class TestQSBSAPIClient:
    """Tests for QSBS API client functions."""

    def test_list_qsbs_securities_empty(self, mock_httpx_client) -> None:
        """Test listing QSBS securities when none exist."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.list_qsbs_securities()
        assert isinstance(result, (list, dict))

    def test_get_qsbs_summary(self, mock_httpx_client) -> None:
        """Test getting QSBS summary."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.get_qsbs_summary(
            entity_ids=None,
            as_of_date=date.today(),
        )
        assert isinstance(result, dict)


class TestTaxAPIClient:
    """Tests for tax API client functions."""

    def test_get_tax_summary_no_entity(self, mock_httpx_client) -> None:
        """Test getting tax summary with invalid entity returns error."""
        from family_office_ledger.streamlit_app import api_client
        from family_office_ledger.streamlit_app.api_client import APIError

        with pytest.raises(APIError):
            api_client.get_tax_summary(
                entity_id="00000000-0000-0000-0000-000000000000",
                tax_year=2024,
            )

    def test_get_schedule_d_no_entity(self, mock_httpx_client) -> None:
        """Test getting Schedule D with invalid entity returns error."""
        from family_office_ledger.streamlit_app import api_client
        from family_office_ledger.streamlit_app.api_client import APIError

        with pytest.raises(APIError):
            api_client.get_schedule_d(
                entity_id="00000000-0000-0000-0000-000000000000",
                tax_year=2024,
            )

    def test_tax_workflow_with_entity(self, mock_httpx_client) -> None:
        """Test tax workflow with a valid entity."""
        from family_office_ledger.streamlit_app import api_client

        # Create an entity first
        entity = api_client.create_entity(
            name="Test Tax Entity",
            entity_type="llc",
        )
        entity_id = entity.get("id")

        # Get tax summary (may return empty data)
        summary = api_client.get_tax_summary(
            entity_id=entity_id,
            tax_year=2024,
        )
        assert isinstance(summary, dict)


class TestExistingAPIClientFunctions:
    """Tests for existing API client functions to ensure they still work."""

    def test_health_check(self, mock_httpx_client) -> None:
        """Test health check endpoint."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.health_check()
        assert result.get("status") == "healthy"

    def test_create_entity(self, mock_httpx_client) -> None:
        """Test creating an entity."""
        from family_office_ledger.streamlit_app import api_client

        result = api_client.create_entity(
            name="Test Entity",
            entity_type="llc",
        )
        assert result.get("name") == "Test Entity"
        assert result.get("entity_type") == "llc"
        assert "id" in result

    def test_list_entities(self, mock_httpx_client) -> None:
        """Test listing entities."""
        from family_office_ledger.streamlit_app import api_client

        # Create one first
        api_client.create_entity(name="Test", entity_type="llc")

        result = api_client.list_entities()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_create_account(self, mock_httpx_client) -> None:
        """Test creating an account."""
        from family_office_ledger.streamlit_app import api_client

        entity = api_client.create_entity(name="Test", entity_type="llc")
        result = api_client.create_account(
            name="Checking",
            entity_id=entity["id"],
            account_type="asset",
            sub_type="cash",
            currency="USD",
        )
        assert result.get("name") == "Checking"
        assert "id" in result

    def test_post_transaction(self, mock_httpx_client) -> None:
        """Test posting a transaction."""
        from family_office_ledger.streamlit_app import api_client

        entity = api_client.create_entity(name="Test", entity_type="llc")
        checking = api_client.create_account(
            name="Checking",
            entity_id=entity["id"],
            account_type="asset",
        )
        expense = api_client.create_account(
            name="Rent",
            entity_id=entity["id"],
            account_type="expense",
        )

        result = api_client.post_transaction(
            transaction_date=date(2024, 1, 15),
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
        assert "id" in result
        assert len(result.get("entries", [])) == 2
