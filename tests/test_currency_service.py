"""Tests for CurrencyService."""

from datetime import date
from decimal import Decimal

import pytest

from family_office_ledger.domain.exchange_rates import ExchangeRate
from family_office_ledger.domain.value_objects import Money
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLiteExchangeRateRepository,
)
from family_office_ledger.services.currency import (
    CurrencyServiceImpl,
    ExchangeRateNotFoundError,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def currency_service(db: SQLiteDatabase) -> CurrencyServiceImpl:
    """Create a currency service with a repository."""
    repo = SQLiteExchangeRateRepository(db)
    return CurrencyServiceImpl(repo)


class TestCurrencyServiceAddRate:
    """Tests for add_rate method."""

    def test_add_rate_persists_rate(self, currency_service: CurrencyServiceImpl):
        """add_rate persists the exchange rate to repository."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )

        currency_service.add_rate(rate)

        # Verify we can retrieve it
        retrieved = currency_service.get_rate("USD", "EUR", date(2026, 1, 15))
        assert retrieved is not None
        assert retrieved.id == rate.id
        assert retrieved.rate == Decimal("0.92")


class TestCurrencyServiceGetRate:
    """Tests for get_rate method."""

    def test_get_rate_returns_rate_for_pair_on_date(
        self, currency_service: CurrencyServiceImpl
    ):
        """get_rate returns rate for currency pair on specific date."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate)

        result = currency_service.get_rate("USD", "EUR", date(2026, 1, 15))

        assert result is not None
        assert result.rate == Decimal("0.92")

    def test_get_rate_returns_none_for_missing_rate(
        self, currency_service: CurrencyServiceImpl
    ):
        """get_rate returns None when no rate exists."""
        result = currency_service.get_rate("USD", "EUR", date(2026, 1, 15))
        assert result is None

    def test_get_rate_returns_none_for_wrong_date(
        self, currency_service: CurrencyServiceImpl
    ):
        """get_rate returns None for different date."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate)

        result = currency_service.get_rate("USD", "EUR", date(2026, 1, 16))
        assert result is None


class TestCurrencyServiceGetLatestRate:
    """Tests for get_latest_rate method."""

    def test_get_latest_rate_returns_most_recent(
        self, currency_service: CurrencyServiceImpl
    ):
        """get_latest_rate returns the most recent rate."""
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.90"),
            effective_date=date(2026, 1, 10),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        rate3 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.91"),
            effective_date=date(2026, 1, 12),
        )
        currency_service.add_rate(rate1)
        currency_service.add_rate(rate2)
        currency_service.add_rate(rate3)

        result = currency_service.get_latest_rate("USD", "EUR")

        assert result is not None
        assert result.id == rate2.id
        assert result.rate == Decimal("0.92")

    def test_get_latest_rate_returns_none_for_unknown_pair(
        self, currency_service: CurrencyServiceImpl
    ):
        """get_latest_rate returns None for unknown currency pair."""
        result = currency_service.get_latest_rate("USD", "JPY")
        assert result is None


class TestCurrencyServiceConvert:
    """Tests for convert method."""

    def test_convert_same_currency_returns_same_money(
        self, currency_service: CurrencyServiceImpl
    ):
        """Convert same currency returns same Money object."""
        amount = Money(Decimal("100"), "USD")

        result = currency_service.convert(amount, "USD", date(2026, 1, 15))

        assert result == amount

    def test_convert_uses_direct_rate(self, currency_service: CurrencyServiceImpl):
        """Convert uses direct rate when available."""
        # Add USD -> EUR rate
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate)

        amount = Money(Decimal("100"), "USD")
        result = currency_service.convert(amount, "EUR", date(2026, 1, 15))

        assert result.currency.value == "EUR"
        assert result.amount == Decimal("92")  # 100 * 0.92

    def test_convert_uses_inverse_rate_if_direct_not_found(
        self, currency_service: CurrencyServiceImpl
    ):
        """Convert uses inverse rate when direct rate not found."""
        # Add EUR -> USD rate (we want USD -> EUR)
        rate = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.10"),  # 1 EUR = 1.10 USD
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate)

        amount = Money(Decimal("110"), "USD")
        result = currency_service.convert(amount, "EUR", date(2026, 1, 15))

        assert result.currency.value == "EUR"
        assert result.amount == Decimal("100")  # 110 / 1.10

    def test_convert_raises_error_when_no_rate_found(
        self, currency_service: CurrencyServiceImpl
    ):
        """Convert raises ExchangeRateNotFoundError when no rate exists."""
        amount = Money(Decimal("100"), "USD")

        with pytest.raises(ExchangeRateNotFoundError) as exc_info:
            currency_service.convert(amount, "EUR", date(2026, 1, 15))

        assert "USD/EUR" in str(exc_info.value)
        assert "2026-01-15" in str(exc_info.value)

    def test_convert_with_decimal_precision(
        self, currency_service: CurrencyServiceImpl
    ):
        """Convert preserves decimal precision."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.923456"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate)

        amount = Money(Decimal("1000.50"), "USD")
        result = currency_service.convert(amount, "EUR", date(2026, 1, 15))

        expected = Decimal("1000.50") * Decimal("0.923456")
        assert result.amount == expected


class TestCurrencyServiceCalculateFxGainLoss:
    """Tests for calculate_fx_gain_loss method."""

    def test_calculate_fx_gain_positive(self, currency_service: CurrencyServiceImpl):
        """Calculate FX gain when currency strengthens."""
        # EUR received when EUR/USD = 1.10
        # Now EUR/USD = 1.15 (EUR strengthened against USD)
        rate_original = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.10"),
            effective_date=date(2026, 1, 1),
        )
        rate_current = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.15"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate_original)
        currency_service.add_rate(rate_current)

        amount = Money(Decimal("1000"), "EUR")
        result = currency_service.calculate_fx_gain_loss(
            original_amount=amount,
            original_date=date(2026, 1, 1),
            current_date=date(2026, 1, 15),
            base_currency="USD",
        )

        # Original: 1000 EUR * 1.10 = 1100 USD
        # Current: 1000 EUR * 1.15 = 1150 USD
        # Gain: 1150 - 1100 = 50 USD
        assert result.currency.value == "USD"
        assert result.amount == Decimal("50")

    def test_calculate_fx_loss_negative(self, currency_service: CurrencyServiceImpl):
        """Calculate FX loss when currency weakens."""
        # EUR received when EUR/USD = 1.10
        # Now EUR/USD = 1.05 (EUR weakened against USD)
        rate_original = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.10"),
            effective_date=date(2026, 1, 1),
        )
        rate_current = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.05"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate_original)
        currency_service.add_rate(rate_current)

        amount = Money(Decimal("1000"), "EUR")
        result = currency_service.calculate_fx_gain_loss(
            original_amount=amount,
            original_date=date(2026, 1, 1),
            current_date=date(2026, 1, 15),
            base_currency="USD",
        )

        # Original: 1000 EUR * 1.10 = 1100 USD
        # Current: 1000 EUR * 1.05 = 1050 USD
        # Loss: 1050 - 1100 = -50 USD
        assert result.currency.value == "USD"
        assert result.amount == Decimal("-50")

    def test_calculate_fx_gain_loss_zero_for_base_currency(
        self, currency_service: CurrencyServiceImpl
    ):
        """Calculate FX gain/loss returns zero when amount is in base currency."""
        amount = Money(Decimal("1000"), "USD")

        result = currency_service.calculate_fx_gain_loss(
            original_amount=amount,
            original_date=date(2026, 1, 1),
            current_date=date(2026, 1, 15),
            base_currency="USD",
        )

        assert result.currency.value == "USD"
        assert result.amount == Decimal("0")
        assert result.is_zero

    def test_calculate_fx_gain_loss_raises_when_original_rate_missing(
        self, currency_service: CurrencyServiceImpl
    ):
        """Calculate FX gain/loss raises when original date rate missing."""
        rate_current = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.15"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate_current)

        amount = Money(Decimal("1000"), "EUR")

        with pytest.raises(ExchangeRateNotFoundError):
            currency_service.calculate_fx_gain_loss(
                original_amount=amount,
                original_date=date(2026, 1, 1),  # No rate for this date
                current_date=date(2026, 1, 15),
                base_currency="USD",
            )

    def test_calculate_fx_gain_loss_raises_when_current_rate_missing(
        self, currency_service: CurrencyServiceImpl
    ):
        """Calculate FX gain/loss raises when current date rate missing."""
        rate_original = ExchangeRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("1.10"),
            effective_date=date(2026, 1, 1),
        )
        currency_service.add_rate(rate_original)

        amount = Money(Decimal("1000"), "EUR")

        with pytest.raises(ExchangeRateNotFoundError):
            currency_service.calculate_fx_gain_loss(
                original_amount=amount,
                original_date=date(2026, 1, 1),
                current_date=date(2026, 1, 15),  # No rate for this date
                base_currency="USD",
            )


class TestCurrencyServiceEdgeCases:
    """Edge case tests for CurrencyService."""

    def test_convert_handles_very_small_amounts(
        self, currency_service: CurrencyServiceImpl
    ):
        """Convert handles very small amounts correctly."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate)

        amount = Money(Decimal("0.01"), "USD")
        result = currency_service.convert(amount, "EUR", date(2026, 1, 15))

        assert result.currency.value == "EUR"
        assert result.amount == Decimal("0.0092")

    def test_convert_handles_very_large_amounts(
        self, currency_service: CurrencyServiceImpl
    ):
        """Convert handles very large amounts correctly."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate)

        amount = Money(Decimal("1000000000"), "USD")
        result = currency_service.convert(amount, "EUR", date(2026, 1, 15))

        assert result.currency.value == "EUR"
        assert result.amount == Decimal("920000000")

    def test_multiple_currency_conversions(self, currency_service: CurrencyServiceImpl):
        """Service handles multiple currency pairs."""
        rate_usd_eur = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        rate_usd_gbp = ExchangeRate(
            from_currency="USD",
            to_currency="GBP",
            rate=Decimal("0.79"),
            effective_date=date(2026, 1, 15),
        )
        rate_eur_gbp = ExchangeRate(
            from_currency="EUR",
            to_currency="GBP",
            rate=Decimal("0.86"),
            effective_date=date(2026, 1, 15),
        )
        currency_service.add_rate(rate_usd_eur)
        currency_service.add_rate(rate_usd_gbp)
        currency_service.add_rate(rate_eur_gbp)

        # Convert USD -> EUR
        usd_amount = Money(Decimal("100"), "USD")
        eur_result = currency_service.convert(usd_amount, "EUR", date(2026, 1, 15))
        assert eur_result.amount == Decimal("92")

        # Convert USD -> GBP
        gbp_result = currency_service.convert(usd_amount, "GBP", date(2026, 1, 15))
        assert gbp_result.amount == Decimal("79")

        # Convert EUR -> GBP
        eur_amount = Money(Decimal("100"), "EUR")
        gbp_result2 = currency_service.convert(eur_amount, "GBP", date(2026, 1, 15))
        assert gbp_result2.amount == Decimal("86")
