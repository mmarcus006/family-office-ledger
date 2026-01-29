"""Tests for ExchangeRate domain model."""

from datetime import date, datetime, UTC
from decimal import Decimal
from uuid import UUID

import pytest

from family_office_ledger.domain.exchange_rates import ExchangeRate, ExchangeRateSource


class TestExchangeRateCreation:
    """Test ExchangeRate creation with all fields."""

    def test_create_with_all_fields(self) -> None:
        """Create ExchangeRate with explicit values."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
            source=ExchangeRateSource.ECB,
        )
        assert rate.from_currency == "USD"
        assert rate.to_currency == "EUR"
        assert rate.rate == Decimal("0.92")
        assert rate.effective_date == date(2025, 1, 29)
        assert rate.source == ExchangeRateSource.ECB
        assert isinstance(rate.id, UUID)
        assert isinstance(rate.created_at, datetime)

    def test_create_with_defaults(self) -> None:
        """Create ExchangeRate with default source (MANUAL)."""
        rate = ExchangeRate(
            from_currency="GBP",
            to_currency="JPY",
            rate=Decimal("150.5"),
            effective_date=date(2025, 1, 29),
        )
        assert rate.source == ExchangeRateSource.MANUAL
        assert rate.created_at.tzinfo == UTC

    def test_rate_coerced_to_decimal(self) -> None:
        """Rate is coerced to Decimal from float/int."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=0.92,  # type: ignore
            effective_date=date(2025, 1, 29),
        )
        assert isinstance(rate.rate, Decimal)
        assert rate.rate == Decimal("0.92")

    def test_rate_coerced_from_string(self) -> None:
        """Rate is coerced to Decimal from string."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate="0.92",  # type: ignore[arg-type]
            effective_date=date(2025, 1, 29),
        )
        assert isinstance(rate.rate, Decimal)
        assert rate.rate == Decimal("0.92")


class TestExchangeRateFrozen:
    """Test that ExchangeRate is immutable."""

    def test_frozen_dataclass(self) -> None:
        """ExchangeRate is frozen (immutable)."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        with pytest.raises(AttributeError):
            rate.rate = Decimal("0.95")  # type: ignore[misc]

    def test_cannot_modify_currency(self) -> None:
        """Cannot modify currency fields."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        with pytest.raises(AttributeError):
            rate.from_currency = "GBP"  # type: ignore[misc]


class TestExchangeRateValidation:
    """Test ExchangeRate validation."""

    def test_rate_must_be_positive(self) -> None:
        """Exchange rate must be positive."""
        with pytest.raises(ValueError, match="Exchange rate must be positive"):
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0"),
                effective_date=date(2025, 1, 29),
            )

    def test_rate_cannot_be_negative(self) -> None:
        """Exchange rate cannot be negative."""
        with pytest.raises(ValueError, match="Exchange rate must be positive"):
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("-0.92"),
                effective_date=date(2025, 1, 29),
            )


class TestExchangeRateInverse:
    """Test ExchangeRate.inverse property."""

    def test_inverse_swaps_currencies(self) -> None:
        """Inverse swaps from/to currencies."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        inverse = rate.inverse
        assert inverse.from_currency == "EUR"
        assert inverse.to_currency == "USD"

    def test_inverse_reciprocal_rate(self) -> None:
        """Inverse has reciprocal rate."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        inverse = rate.inverse
        assert inverse.rate == Decimal("1") / Decimal("0.92")

    def test_inverse_preserves_date_and_source(self) -> None:
        """Inverse preserves effective_date and source."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
            source=ExchangeRateSource.ECB,
        )
        inverse = rate.inverse
        assert inverse.effective_date == date(2025, 1, 29)
        assert inverse.source == ExchangeRateSource.ECB

    def test_inverse_is_new_instance(self) -> None:
        """Inverse returns a new ExchangeRate instance."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        inverse = rate.inverse
        assert rate.id != inverse.id

    def test_double_inverse_equals_original(self) -> None:
        """Double inverse equals original (approximately)."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        double_inverse = rate.inverse.inverse
        # Due to Decimal precision, check currencies and approximate rate
        assert double_inverse.from_currency == rate.from_currency
        assert double_inverse.to_currency == rate.to_currency
        assert abs(double_inverse.rate - rate.rate) < Decimal("0.0001")


class TestExchangeRatePair:
    """Test ExchangeRate.pair property."""

    def test_pair_format(self) -> None:
        """Pair returns 'FROM/TO' format."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        assert rate.pair == "USD/EUR"

    def test_pair_different_currencies(self) -> None:
        """Pair works with different currency codes."""
        rate = ExchangeRate(
            from_currency="GBP",
            to_currency="JPY",
            rate=Decimal("150.5"),
            effective_date=date(2025, 1, 29),
        )
        assert rate.pair == "GBP/JPY"


class TestExchangeRateEquality:
    """Test ExchangeRate equality."""

    def test_equal_rates_with_same_id(self) -> None:
        """Rates with same ID are equal."""
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
            id=rate1.id,
            created_at=rate1.created_at,
        )
        assert rate1 == rate2

    def test_different_rates_not_equal(self) -> None:
        """Rates with different values are not equal."""
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2025, 1, 29),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.95"),
            effective_date=date(2025, 1, 29),
        )
        assert rate1 != rate2


class TestExchangeRateSource:
    """Test ExchangeRateSource enum."""

    def test_source_enum_values(self) -> None:
        """ExchangeRateSource has expected values."""
        assert ExchangeRateSource.MANUAL.value == "manual"
        assert ExchangeRateSource.ECB.value == "ecb"
        assert ExchangeRateSource.FED.value == "fed"
        assert ExchangeRateSource.BANK.value == "bank"
        assert ExchangeRateSource.API.value == "api"

    def test_source_is_string_enum(self) -> None:
        """ExchangeRateSource inherits from str."""
        assert isinstance(ExchangeRateSource.MANUAL, str)
        assert ExchangeRateSource.ECB == "ecb"
