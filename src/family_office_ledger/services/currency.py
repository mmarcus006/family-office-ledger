from datetime import date

from family_office_ledger.domain.exchange_rates import ExchangeRate
from family_office_ledger.domain.value_objects import Currency, Money
from family_office_ledger.repositories.interfaces import ExchangeRateRepository
from family_office_ledger.services.interfaces import CurrencyService


def _get_currency_str(currency: Currency | str) -> str:
    if isinstance(currency, Currency):
        return currency.value
    return currency


class ExchangeRateNotFoundError(Exception):
    pass


class CurrencyServiceImpl(CurrencyService):
    def __init__(self, exchange_rate_repo: ExchangeRateRepository) -> None:
        self._repo = exchange_rate_repo

    def add_rate(self, rate: ExchangeRate) -> None:
        self._repo.add(rate)

    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: date,
    ) -> ExchangeRate | None:
        return self._repo.get_rate(from_currency, to_currency, effective_date)

    def get_latest_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate | None:
        return self._repo.get_latest_rate(from_currency, to_currency)

    def convert(
        self,
        amount: Money,
        to_currency: str,
        as_of_date: date,
    ) -> Money:
        from_currency = _get_currency_str(amount.currency)
        if from_currency == to_currency:
            return amount

        rate = self._repo.get_rate(from_currency, to_currency, as_of_date)
        if rate is not None:
            converted = amount.amount * rate.rate
            return Money(converted, to_currency)

        inverse = self._repo.get_rate(to_currency, from_currency, as_of_date)
        if inverse is not None:
            converted = amount.amount / inverse.rate
            return Money(converted, to_currency)

        raise ExchangeRateNotFoundError(
            f"No exchange rate found for {from_currency}/{to_currency} on {as_of_date}"
        )

    def calculate_fx_gain_loss(
        self,
        original_amount: Money,
        original_date: date,
        current_date: date,
        base_currency: str,
    ) -> Money:
        from_currency = _get_currency_str(original_amount.currency)

        if from_currency == base_currency:
            return Money.zero(base_currency)

        original_in_base = self.convert(original_amount, base_currency, original_date)
        current_in_base = self.convert(original_amount, base_currency, current_date)

        return current_in_base - original_in_base
