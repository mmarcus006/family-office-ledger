"""Tests for SQLite ExchangeRate repository."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.exchange_rates import ExchangeRate, ExchangeRateSource
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLiteExchangeRateRepository,
)


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def repo(db: SQLiteDatabase) -> SQLiteExchangeRateRepository:
    """Create an exchange rate repository."""
    return SQLiteExchangeRateRepository(db)


class TestSQLiteExchangeRateRepository:
    """Tests for SQLiteExchangeRateRepository."""

    def test_add_and_get_rate(self, repo: SQLiteExchangeRateRepository):
        """Can add and retrieve an exchange rate."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
            source=ExchangeRateSource.ECB,
        )

        repo.add(rate)
        retrieved = repo.get(rate.id)

        assert retrieved is not None
        assert retrieved.id == rate.id
        assert retrieved.from_currency == "USD"
        assert retrieved.to_currency == "EUR"
        assert retrieved.rate == Decimal("0.92")
        assert retrieved.effective_date == date(2026, 1, 15)
        assert retrieved.source == ExchangeRateSource.ECB

    def test_get_nonexistent_rate_returns_none(
        self, repo: SQLiteExchangeRateRepository
    ):
        """Getting a nonexistent rate returns None."""
        result = repo.get(uuid4())
        assert result is None

    def test_get_rate_by_pair_and_date(self, repo: SQLiteExchangeRateRepository):
        """Can get exchange rate for currency pair on specific date."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        repo.add(rate)

        retrieved = repo.get_rate("USD", "EUR", date(2026, 1, 15))

        assert retrieved is not None
        assert retrieved.id == rate.id
        assert retrieved.rate == Decimal("0.92")

    def test_get_rate_returns_none_for_wrong_date(
        self, repo: SQLiteExchangeRateRepository
    ):
        """get_rate returns None if no rate for that date."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        repo.add(rate)

        # Different date
        result = repo.get_rate("USD", "EUR", date(2026, 1, 16))
        assert result is None

    def test_get_rate_returns_none_for_wrong_pair(
        self, repo: SQLiteExchangeRateRepository
    ):
        """get_rate returns None if no rate for that currency pair."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        repo.add(rate)

        # Different currency pair
        result = repo.get_rate("USD", "GBP", date(2026, 1, 15))
        assert result is None

    def test_get_latest_rate(self, repo: SQLiteExchangeRateRepository):
        """Can get the most recent exchange rate for currency pair."""
        # Add rates for different dates
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
        repo.add(rate1)
        repo.add(rate2)
        repo.add(rate3)

        latest = repo.get_latest_rate("USD", "EUR")

        assert latest is not None
        assert latest.id == rate2.id
        assert latest.effective_date == date(2026, 1, 15)
        assert latest.rate == Decimal("0.92")

    def test_get_latest_rate_returns_none_for_unknown_pair(
        self, repo: SQLiteExchangeRateRepository
    ):
        """get_latest_rate returns None for unknown currency pair."""
        result = repo.get_latest_rate("USD", "JPY")
        assert result is None

    def test_list_by_currency_pair(self, repo: SQLiteExchangeRateRepository):
        """Can list all rates for a currency pair."""
        # Add rates for USD/EUR
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
        # Add rate for different pair
        rate3 = ExchangeRate(
            from_currency="USD",
            to_currency="GBP",
            rate=Decimal("0.78"),
            effective_date=date(2026, 1, 10),
        )

        repo.add(rate1)
        repo.add(rate2)
        repo.add(rate3)

        rates = list(repo.list_by_currency_pair("USD", "EUR"))

        assert len(rates) == 2
        rate_ids = {r.id for r in rates}
        assert rate1.id in rate_ids
        assert rate2.id in rate_ids
        assert rate3.id not in rate_ids

    def test_list_by_currency_pair_with_date_range(
        self, repo: SQLiteExchangeRateRepository
    ):
        """Can filter rates by date range."""
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.90"),
            effective_date=date(2026, 1, 5),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.91"),
            effective_date=date(2026, 1, 10),
        )
        rate3 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        rate4 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.93"),
            effective_date=date(2026, 1, 20),
        )

        repo.add(rate1)
        repo.add(rate2)
        repo.add(rate3)
        repo.add(rate4)

        # Filter with date range
        rates = list(
            repo.list_by_currency_pair(
                "USD", "EUR", start_date=date(2026, 1, 10), end_date=date(2026, 1, 15)
            )
        )

        assert len(rates) == 2
        rate_ids = {r.id for r in rates}
        assert rate2.id in rate_ids
        assert rate3.id in rate_ids

    def test_list_by_currency_pair_with_start_date_only(
        self, repo: SQLiteExchangeRateRepository
    ):
        """Can filter rates with only start date."""
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.90"),
            effective_date=date(2026, 1, 5),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )

        repo.add(rate1)
        repo.add(rate2)

        rates = list(
            repo.list_by_currency_pair("USD", "EUR", start_date=date(2026, 1, 10))
        )

        assert len(rates) == 1
        assert rates[0].id == rate2.id

    def test_list_by_currency_pair_with_end_date_only(
        self, repo: SQLiteExchangeRateRepository
    ):
        """Can filter rates with only end date."""
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.90"),
            effective_date=date(2026, 1, 5),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )

        repo.add(rate1)
        repo.add(rate2)

        rates = list(
            repo.list_by_currency_pair("USD", "EUR", end_date=date(2026, 1, 10))
        )

        assert len(rates) == 1
        assert rates[0].id == rate1.id

    def test_list_by_currency_pair_empty_for_unknown_pair(
        self, repo: SQLiteExchangeRateRepository
    ):
        """list_by_currency_pair returns empty for unknown pair."""
        rates = list(repo.list_by_currency_pair("USD", "JPY"))
        assert rates == []

    def test_list_by_date(self, repo: SQLiteExchangeRateRepository):
        """Can list all rates for a specific date."""
        # Add rates for same date, different pairs
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="GBP",
            rate=Decimal("0.78"),
            effective_date=date(2026, 1, 15),
        )
        # Add rate for different date
        rate3 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.90"),
            effective_date=date(2026, 1, 10),
        )

        repo.add(rate1)
        repo.add(rate2)
        repo.add(rate3)

        rates = list(repo.list_by_date(date(2026, 1, 15)))

        assert len(rates) == 2
        rate_ids = {r.id for r in rates}
        assert rate1.id in rate_ids
        assert rate2.id in rate_ids
        assert rate3.id not in rate_ids

    def test_list_by_date_empty_for_unknown_date(
        self, repo: SQLiteExchangeRateRepository
    ):
        """list_by_date returns empty for date with no rates."""
        rates = list(repo.list_by_date(date(2026, 1, 15)))
        assert rates == []

    def test_delete_rate(self, repo: SQLiteExchangeRateRepository):
        """Can delete an exchange rate."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        repo.add(rate)

        repo.delete(rate.id)

        assert repo.get(rate.id) is None

    def test_delete_nonexistent_rate_is_silent(
        self, repo: SQLiteExchangeRateRepository
    ):
        """Deleting a nonexistent rate does not raise error."""
        repo.delete(uuid4())  # Should not raise

    def test_rate_timestamp_preserved(self, repo: SQLiteExchangeRateRepository):
        """Exchange rate created_at timestamp is preserved."""
        created_at = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
        )
        # Override created_at
        object.__setattr__(rate, "created_at", created_at)

        repo.add(rate)
        retrieved = repo.get(rate.id)

        assert retrieved is not None
        assert retrieved.created_at == created_at

    def test_all_sources_stored_correctly(self, repo: SQLiteExchangeRateRepository):
        """All exchange rate sources are stored and retrieved correctly."""
        for source in ExchangeRateSource:
            rate = ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.92"),
                effective_date=date(2026, 1, 15),
                source=source,
            )
            repo.add(rate)
            retrieved = repo.get(rate.id)
            assert retrieved is not None
            assert retrieved.source == source

    def test_decimal_precision_preserved(self, repo: SQLiteExchangeRateRepository):
        """High precision decimal rates are preserved."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.9234567890123456"),
            effective_date=date(2026, 1, 15),
        )
        repo.add(rate)
        retrieved = repo.get(rate.id)

        assert retrieved is not None
        assert retrieved.rate == Decimal("0.9234567890123456")

    def test_multiple_rates_same_pair_same_date(
        self, repo: SQLiteExchangeRateRepository
    ):
        """Can store multiple rates for same pair and date (different IDs)."""
        rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.92"),
            effective_date=date(2026, 1, 15),
            source=ExchangeRateSource.ECB,
        )
        rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.921"),
            effective_date=date(2026, 1, 15),
            source=ExchangeRateSource.FED,
        )

        repo.add(rate1)
        repo.add(rate2)

        # Both should be retrievable by ID
        assert repo.get(rate1.id) is not None
        assert repo.get(rate2.id) is not None

        # get_rate returns one (whichever matches first)
        result = repo.get_rate("USD", "EUR", date(2026, 1, 15))
        assert result is not None
        assert result.id in {rate1.id, rate2.id}
