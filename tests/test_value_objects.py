from decimal import Decimal

import pytest

from family_office_ledger.domain.value_objects import Money, Quantity


class TestMoney:
    def test_money_creation_with_decimal(self):
        money = Money(Decimal("100.50"), "USD")

        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"

    def test_money_creation_converts_float_to_decimal(self):
        money = Money(100.50, "USD")

        assert isinstance(money.amount, Decimal)
        assert money.amount == Decimal("100.5")

    def test_money_addition_same_currency(self):
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "USD")

        result = m1 + m2

        assert result == Money(Decimal("150.00"), "USD")

    def test_money_addition_different_currency_raises(self):
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("50.00"), "EUR")

        with pytest.raises(ValueError, match="Cannot add"):
            m1 + m2

    def test_money_subtraction_same_currency(self):
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("30.00"), "USD")

        result = m1 - m2

        assert result == Money(Decimal("70.00"), "USD")

    def test_money_subtraction_different_currency_raises(self):
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("30.00"), "EUR")

        with pytest.raises(ValueError, match="Cannot subtract"):
            m1 - m2

    def test_money_multiplication_by_decimal(self):
        money = Money(Decimal("100.00"), "USD")

        result = money * Decimal("1.5")

        assert result == Money(Decimal("150.00"), "USD")

    def test_money_multiplication_by_int(self):
        money = Money(Decimal("100.00"), "USD")

        result = money * 3

        assert result == Money(Decimal("300.00"), "USD")

    def test_money_negation(self):
        money = Money(Decimal("100.00"), "USD")

        result = -money

        assert result == Money(Decimal("-100.00"), "USD")

    def test_money_is_zero(self):
        zero = Money(Decimal("0"), "USD")
        non_zero = Money(Decimal("100.00"), "USD")

        assert zero.is_zero is True
        assert non_zero.is_zero is False

    def test_money_is_positive(self):
        positive = Money(Decimal("100.00"), "USD")
        negative = Money(Decimal("-100.00"), "USD")
        zero = Money(Decimal("0"), "USD")

        assert positive.is_positive is True
        assert negative.is_positive is False
        assert zero.is_positive is False

    def test_money_is_negative(self):
        negative = Money(Decimal("-100.00"), "USD")
        positive = Money(Decimal("100.00"), "USD")

        assert negative.is_negative is True
        assert positive.is_negative is False

    def test_money_comparison_less_than(self):
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")

        assert m1 < m2
        assert not m2 < m1

    def test_money_comparison_different_currency_raises(self):
        m1 = Money(Decimal("50.00"), "USD")
        m2 = Money(Decimal("100.00"), "EUR")

        with pytest.raises(ValueError, match="Cannot compare"):
            m1 < m2

    def test_money_zero_factory(self):
        zero_usd = Money.zero("USD")
        zero_eur = Money.zero("EUR")

        assert zero_usd == Money(Decimal("0"), "USD")
        assert zero_eur == Money(Decimal("0"), "EUR")

    def test_money_equality(self):
        m1 = Money(Decimal("100.00"), "USD")
        m2 = Money(Decimal("100.00"), "USD")
        m3 = Money(Decimal("100.00"), "EUR")
        m4 = Money(Decimal("50.00"), "USD")

        assert m1 == m2
        assert m1 != m3
        assert m1 != m4

    def test_money_immutability(self):
        money = Money(Decimal("100.00"), "USD")

        with pytest.raises(AttributeError):
            money.amount = Decimal("200.00")


class TestQuantity:
    def test_quantity_creation_with_decimal(self):
        qty = Quantity(Decimal("100.5"))

        assert qty.value == Decimal("100.5")

    def test_quantity_creation_converts_int(self):
        qty = Quantity(100)

        assert isinstance(qty.value, Decimal)
        assert qty.value == Decimal("100")

    def test_quantity_addition(self):
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("50"))

        result = q1 + q2

        assert result == Quantity(Decimal("150"))

    def test_quantity_subtraction(self):
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("30"))

        result = q1 - q2

        assert result == Quantity(Decimal("70"))

    def test_quantity_multiplication(self):
        qty = Quantity(Decimal("100"))

        result = qty * Decimal("2")

        assert result == Quantity(Decimal("200"))

    def test_quantity_negation(self):
        qty = Quantity(Decimal("100"))

        result = -qty

        assert result == Quantity(Decimal("-100"))

    def test_quantity_is_zero(self):
        zero = Quantity(Decimal("0"))
        non_zero = Quantity(Decimal("100"))

        assert zero.is_zero is True
        assert non_zero.is_zero is False

    def test_quantity_is_positive(self):
        positive = Quantity(Decimal("100"))
        negative = Quantity(Decimal("-100"))

        assert positive.is_positive is True
        assert negative.is_positive is False

    def test_quantity_is_negative(self):
        negative = Quantity(Decimal("-100"))
        positive = Quantity(Decimal("100"))

        assert negative.is_negative is True
        assert positive.is_negative is False

    def test_quantity_comparison(self):
        q1 = Quantity(Decimal("50"))
        q2 = Quantity(Decimal("100"))

        assert q1 < q2
        assert q1 <= q2
        assert q2 > q1

    def test_quantity_zero_factory(self):
        zero = Quantity.zero()

        assert zero == Quantity(Decimal("0"))

    def test_quantity_equality(self):
        q1 = Quantity(Decimal("100"))
        q2 = Quantity(Decimal("100"))
        q3 = Quantity(Decimal("50"))

        assert q1 == q2
        assert q1 != q3

    def test_quantity_immutability(self):
        qty = Quantity(Decimal("100"))

        with pytest.raises(AttributeError):
            qty.value = Decimal("200")

    def test_quantity_fractional_shares(self):
        qty = Quantity(Decimal("10.5"))

        assert qty.value == Decimal("10.5")
        assert qty.is_positive is True
