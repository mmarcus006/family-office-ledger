"""TDD Tests for error class deduplication.

These tests verify that UnbalancedTransactionError is properly deduplicated:
- Canonical definition should be in domain/transactions.py
- services/ledger.py should import and re-export from domain
"""

import pytest


class TestUnbalancedTransactionErrorDeduplication:
    """Test that UnbalancedTransactionError is properly deduplicated."""

    def test_canonical_error_in_domain_transactions(self) -> None:
        """Test that UnbalancedTransactionError is defined in domain.transactions."""
        from family_office_ledger.domain.transactions import UnbalancedTransactionError

        assert UnbalancedTransactionError is not None
        assert issubclass(UnbalancedTransactionError, Exception)

    def test_ledger_service_imports_from_domain(self) -> None:
        """Test that ledger service uses the domain error class."""
        from family_office_ledger.domain.transactions import (
            UnbalancedTransactionError as DomainError,
        )
        from family_office_ledger.services.ledger import (
            UnbalancedTransactionError as LedgerError,
        )

        # Both should reference the same class (not duplicates)
        assert DomainError is LedgerError

    def test_api_routes_imports_from_domain(self) -> None:
        """Test that API routes use the domain error class."""
        from family_office_ledger.api.routes import UnbalancedTransactionError as APIError
        from family_office_ledger.domain.transactions import (
            UnbalancedTransactionError as DomainError,
        )

        # Should be the same class
        assert DomainError is APIError

    def test_error_can_be_raised_and_caught(self) -> None:
        """Test that the error works correctly across modules."""
        from family_office_ledger.domain.transactions import UnbalancedTransactionError

        with pytest.raises(UnbalancedTransactionError):
            raise UnbalancedTransactionError("Test error")

    def test_error_message_preserved(self) -> None:
        """Test that error message is preserved."""
        from family_office_ledger.domain.transactions import UnbalancedTransactionError

        msg = "Transaction is unbalanced: debits=100, credits=50"
        try:
            raise UnbalancedTransactionError(msg)
        except UnbalancedTransactionError as e:
            assert msg in str(e)
