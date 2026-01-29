"""Tests for currency CLI commands."""

from decimal import Decimal

from family_office_ledger.cli import main
from family_office_ledger.domain.exchange_rates import ExchangeRate, ExchangeRateSource
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLiteExchangeRateRepository,
)


class TestCurrencyHelp:
    def test_currency_no_subcommand_prints_help(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(["--database", str(db_path), "currency"])

        assert result == 0
        captured = capsys.readouterr()
        assert "rates-add" in captured.out or "currency" in captured.out.lower()


class TestCurrencyRatesAdd:
    def test_adds_exchange_rate(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--rate",
                "0.92",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Added rate" in captured.out
        assert "USD/EUR" in captured.out
        assert "0.92" in captured.out

    def test_adds_rate_with_custom_source(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "GBP",
                "--to",
                "USD",
                "--rate",
                "1.27",
                "--date",
                "2024-01-15",
                "--source",
                "ecb",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Added rate" in captured.out
        assert "GBP/USD" in captured.out

    def test_rate_stored_in_database(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--rate",
                "0.92",
                "--date",
                "2024-01-15",
            ]
        )

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        rate = repo.get_rate("USD", "EUR", date(2024, 1, 15))

        assert rate is not None
        assert rate.from_currency == "USD"
        assert rate.to_currency == "EUR"
        assert rate.rate == Decimal("0.92")

    def test_uppercase_normalization(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "usd",
                "--to",
                "eur",
                "--rate",
                "0.92",
                "--date",
                "2024-01-15",
            ]
        )

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        rate = repo.get_rate("USD", "EUR", date(2024, 1, 15))

        assert rate is not None
        assert rate.from_currency == "USD"
        assert rate.to_currency == "EUR"

    def test_fails_with_nonexistent_database(self, tmp_path, capsys):
        db_path = tmp_path / "nonexistent.db"

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--rate",
                "0.92",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Database not found" in captured.out


class TestCurrencyRatesList:
    def test_lists_rates(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.92"),
                effective_date=date(2024, 1, 15),
                source=ExchangeRateSource.MANUAL,
            )
        )
        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.93"),
                effective_date=date(2024, 1, 16),
                source=ExchangeRateSource.ECB,
            )
        )

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-list",
                "--from",
                "USD",
                "--to",
                "EUR",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "USD/EUR" in captured.out
        assert "0.92" in captured.out
        assert "0.93" in captured.out
        assert "manual" in captured.out
        assert "ecb" in captured.out

    def test_filters_by_date_range(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.90"),
                effective_date=date(2024, 1, 10),
                source=ExchangeRateSource.MANUAL,
            )
        )
        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.92"),
                effective_date=date(2024, 1, 15),
                source=ExchangeRateSource.MANUAL,
            )
        )
        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.94"),
                effective_date=date(2024, 1, 20),
                source=ExchangeRateSource.MANUAL,
            )
        )

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-list",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--start-date",
                "2024-01-14",
                "--end-date",
                "2024-01-16",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "0.92" in captured.out
        assert "0.90" not in captured.out
        assert "0.94" not in captured.out

    def test_no_rates_found(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-list",
                "--from",
                "USD",
                "--to",
                "EUR",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "No rates found" in captured.out


class TestCurrencyRatesLatest:
    def test_gets_latest_rate(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.90"),
                effective_date=date(2024, 1, 10),
                source=ExchangeRateSource.MANUAL,
            )
        )
        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.93"),
                effective_date=date(2024, 1, 20),
                source=ExchangeRateSource.ECB,
            )
        )

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-latest",
                "--from",
                "USD",
                "--to",
                "EUR",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Latest USD/EUR" in captured.out
        assert "0.93" in captured.out
        assert "ecb" in captured.out

    def test_no_rate_found(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-latest",
                "--from",
                "USD",
                "--to",
                "EUR",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "No rate found" in captured.out


class TestCurrencyConvert:
    def test_converts_amount(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.92"),
                effective_date=date(2024, 1, 15),
                source=ExchangeRateSource.MANUAL,
            )
        )

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "convert",
                "--amount",
                "100",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "100 USD" in captured.out
        assert "EUR" in captured.out
        assert "92" in captured.out

    def test_converts_with_inverse_rate(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.92"),
                effective_date=date(2024, 1, 15),
                source=ExchangeRateSource.MANUAL,
            )
        )

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "convert",
                "--amount",
                "92",
                "--from",
                "EUR",
                "--to",
                "USD",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "92 EUR" in captured.out
        assert "USD" in captured.out

    def test_conversion_fails_without_rate(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "convert",
                "--amount",
                "100",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "No exchange rate found" in captured.out

    def test_conversion_with_decimal_amount(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        repo = SQLiteExchangeRateRepository(db)
        from datetime import date

        repo.add(
            ExchangeRate(
                from_currency="USD",
                to_currency="GBP",
                rate=Decimal("0.79"),
                effective_date=date(2024, 1, 15),
                source=ExchangeRateSource.MANUAL,
            )
        )

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "convert",
                "--amount",
                "123.45",
                "--from",
                "USD",
                "--to",
                "GBP",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "123.45 USD" in captured.out
        assert "GBP" in captured.out


class TestCurrencyErrorHandling:
    def test_invalid_date_format(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--rate",
                "0.92",
                "--date",
                "2024/01/15",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_invalid_rate_value(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--rate",
                "not_a_number",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_negative_rate_value(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "currency",
                "rates-add",
                "--from",
                "USD",
                "--to",
                "EUR",
                "--rate",
                "-0.92",
                "--date",
                "2024-01-15",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out
