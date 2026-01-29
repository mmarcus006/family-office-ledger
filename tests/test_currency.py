from decimal import Decimal

import pytest

from family_office_ledger.domain.value_objects import Currency, Money


class TestCurrencyEnum:
    """Test Currency enum values and behavior."""

    def test_currency_enum_has_expected_values(self):
        """Verify all expected ISO 4217 currency codes exist."""
        expected_currencies = {
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "CHF",
            "CAD",
            "AUD",
            "CNY",
            "HKD",
            "SGD",
            "NZD",
            "SEK",
            "NOK",
            "DKK",
            "MXN",
            "BRL",
            "INR",
            "KRW",
            "ZAR",
        }
        actual_currencies = {c.value for c in Currency}
        assert actual_currencies == expected_currencies

    def test_currency_enum_members_exist(self):
        """Verify specific currency enum members."""
        assert Currency.USD.value == "USD"
        assert Currency.EUR.value == "EUR"
        assert Currency.GBP.value == "GBP"
        assert Currency.JPY.value == "JPY"
        assert Currency.CHF.value == "CHF"
        assert Currency.CAD.value == "CAD"
        assert Currency.AUD.value == "AUD"
        assert Currency.CNY.value == "CNY"
        assert Currency.HKD.value == "HKD"
        assert Currency.SGD.value == "SGD"
        assert Currency.NZD.value == "NZD"
        assert Currency.SEK.value == "SEK"
        assert Currency.NOK.value == "NOK"
        assert Currency.DKK.value == "DKK"
        assert Currency.MXN.value == "MXN"
        assert Currency.BRL.value == "BRL"
        assert Currency.INR.value == "INR"
        assert Currency.KRW.value == "KRW"
        assert Currency.ZAR.value == "ZAR"

    def test_currency_enum_is_string_enum(self):
        """Verify Currency inherits from str for JSON serialization."""
        assert isinstance(Currency.USD, str)
        assert Currency.USD == "USD"


class TestMoneyWithCurrency:
    """Test Money class with Currency enum validation."""

    def test_money_accepts_currency_enum(self):
        """Money should accept Currency enum directly."""
        money = Money(Decimal("100.00"), Currency.USD)
        assert money.amount == Decimal("100.00")
        assert money.currency == Currency.USD

    def test_money_accepts_string_currency_backward_compatible(self):
        """Money should accept string currency for backward compatibility."""
        money = Money(Decimal("100.00"), "USD")
        assert money.amount == Decimal("100.00")
        assert money.currency == Currency.USD

    def test_money_converts_string_to_currency_enum(self):
        """Money should convert valid string to Currency enum."""
        money = Money(Decimal("100.00"), "EUR")
        assert isinstance(money.currency, Currency)
        assert money.currency == Currency.EUR

    def test_money_rejects_invalid_currency_string(self):
        """Money should raise ValueError for invalid currency string."""
        with pytest.raises(ValueError, match="Invalid currency"):
            Money(Decimal("100.00"), "INVALID")

    def test_money_currency_returns_enum_type(self):
        """Money.currency property should return Currency enum."""
        money = Money(Decimal("100.00"), Currency.GBP)
        assert isinstance(money.currency, Currency)
        assert money.currency == Currency.GBP

    def test_money_default_currency_is_usd_enum(self):
        """Money default currency should be Currency.USD."""
        money = Money(Decimal("100.00"))
        assert money.currency == Currency.USD
        assert isinstance(money.currency, Currency)

    def test_money_arithmetic_with_enum_currencies(self):
        """Money arithmetic should work with Currency enum."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("50.00"), Currency.USD)
        result = m1 + m2
        assert result == Money(Decimal("150.00"), Currency.USD)

    def test_money_arithmetic_different_currencies_raises(self):
        """Money arithmetic with different currencies should raise ValueError."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("50.00"), Currency.EUR)
        with pytest.raises(ValueError, match="Cannot add"):
            m1 + m2

    def test_money_subtraction_with_enum_currencies(self):
        """Money subtraction should work with Currency enum."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("30.00"), Currency.USD)
        result = m1 - m2
        assert result == Money(Decimal("70.00"), Currency.USD)

    def test_money_subtraction_different_currencies_raises(self):
        """Money subtraction with different currencies should raise ValueError."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("30.00"), Currency.EUR)
        with pytest.raises(ValueError, match="Cannot subtract"):
            m1 - m2

    def test_money_comparison_with_enum_currencies(self):
        """Money comparison should work with Currency enum."""
        m1 = Money(Decimal("50.00"), Currency.USD)
        m2 = Money(Decimal("100.00"), Currency.USD)
        assert m1 < m2

    def test_money_comparison_different_currencies_raises(self):
        """Money comparison with different currencies should raise ValueError."""
        m1 = Money(Decimal("50.00"), Currency.USD)
        m2 = Money(Decimal("100.00"), Currency.EUR)
        with pytest.raises(ValueError, match="Cannot compare"):
            m1 < m2

    def test_money_equality_with_enum_currencies(self):
        """Money equality should work with Currency enum."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("100.00"), Currency.USD)
        assert m1 == m2

    def test_money_equality_different_currencies(self):
        """Money equality should be false for different currencies."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("100.00"), Currency.EUR)
        assert m1 != m2

    def test_money_zero_with_currency_enum(self):
        """Money.zero() should accept Currency enum."""
        zero = Money.zero(Currency.EUR)
        assert zero == Money(Decimal("0"), Currency.EUR)
        assert zero.currency == Currency.EUR

    def test_money_zero_with_string_currency(self):
        """Money.zero() should accept string currency for backward compatibility."""
        zero = Money.zero("GBP")
        assert zero == Money(Decimal("0"), Currency.GBP)
        assert zero.currency == Currency.GBP

    def test_money_zero_default_is_usd(self):
        """Money.zero() default should be USD."""
        zero = Money.zero()
        assert zero == Money(Decimal("0"), Currency.USD)
        assert zero.currency == Currency.USD

    def test_money_multiplication_preserves_currency_enum(self):
        """Money multiplication should preserve Currency enum."""
        money = Money(Decimal("100.00"), Currency.EUR)
        result = money * 2
        assert result.currency == Currency.EUR
        assert isinstance(result.currency, Currency)

    def test_money_negation_preserves_currency_enum(self):
        """Money negation should preserve Currency enum."""
        money = Money(Decimal("100.00"), Currency.GBP)
        result = -money
        assert result.currency == Currency.GBP
        assert isinstance(result.currency, Currency)

    def test_money_mixed_enum_and_string_comparison(self):
        """Money created with enum and string should be equal if same currency."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("100.00"), "USD")
        assert m1 == m2

    def test_money_mixed_enum_and_string_arithmetic(self):
        """Money arithmetic should work with mixed enum and string creation."""
        m1 = Money(Decimal("100.00"), Currency.USD)
        m2 = Money(Decimal("50.00"), "USD")
        result = m1 + m2
        assert result == Money(Decimal("150.00"), Currency.USD)

    def test_money_case_sensitive_currency_validation(self):
        """Currency validation should be case-sensitive."""
        with pytest.raises(ValueError, match="Invalid currency"):
            Money(Decimal("100.00"), "usd")

    def test_money_all_supported_currencies(self):
        """Money should accept all Currency enum values."""
        for currency in Currency:
            money = Money(Decimal("100.00"), currency)
            assert money.currency == currency
            assert isinstance(money.currency, Currency)

    def test_money_all_supported_currencies_as_string(self):
        """Money should accept all Currency enum values as strings."""
        for currency in Currency:
            money = Money(Decimal("100.00"), currency.value)
            assert money.currency == currency
            assert isinstance(money.currency, Currency)
