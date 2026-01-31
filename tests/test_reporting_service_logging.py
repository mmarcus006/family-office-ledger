"""TDD Tests for structured logging in reporting service.

These tests verify that proper structlog warnings are logged when
exchange rate fallbacks occur in the reporting service.
"""

import logging
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest


class TestReportingServiceLogging:
    """Test that reporting service logs warnings for exchange rate fallbacks."""

    def test_exchange_rate_not_found_logs_warning(self, capsys, caplog) -> None:
        """Test that a warning is logged when exchange rate is not found."""
        from family_office_ledger.services.currency import ExchangeRateNotFoundError
        from family_office_ledger.services.reporting import ReportingServiceImpl

        # Create mock repositories
        entity_repo = MagicMock()
        account_repo = MagicMock()
        transaction_repo = MagicMock()
        position_repo = MagicMock()
        tax_lot_repo = MagicMock()
        security_repo = MagicMock()

        # Create a mock currency service that raises ExchangeRateNotFoundError
        mock_currency_service = MagicMock()
        mock_currency_service.convert.side_effect = ExchangeRateNotFoundError(
            "Exchange rate not found for EUR -> USD"
        )

        service = ReportingServiceImpl(
            entity_repo=entity_repo,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            position_repo=position_repo,
            tax_lot_repo=tax_lot_repo,
            security_repo=security_repo,
            currency_service=mock_currency_service,
        )

        # Capture logs at WARNING level for the reporting module
        with caplog.at_level(logging.WARNING, logger="family_office_ledger.services.reporting"):
            # Call the internal conversion method
            result = service._convert_to_base(
                amount=Decimal("100.00"),
                from_currency="EUR",
                base_currency="USD",
                as_of_date=date.today(),
            )

        # Result should be the original amount (fallback behavior)
        assert result == Decimal("100.00")

        # Structlog can output to stdout directly OR through Python's logging
        # depending on configuration. Check both to be robust.
        captured = capsys.readouterr()
        log_text = caplog.text

        # Combine both possible outputs
        all_output = captured.out + log_text

        # The log output should contain the event name
        assert "exchange_rate_not_found" in all_output, \
            f"Expected exchange_rate_not_found in log output. stdout: {captured.out!r}, caplog: {log_text!r}"


class TestLoggingConfiguration:
    """Test that logging is properly configured."""

    def test_structlog_logger_available_in_reporting(self) -> None:
        """Test that structlog logger is available in reporting module."""
        # Import should not fail
        from family_office_ledger.services import reporting

        # Check that the module has or can get a logger
        from family_office_ledger.logging_config import get_logger

        logger = get_logger("family_office_ledger.services.reporting")
        assert logger is not None
