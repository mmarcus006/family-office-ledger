"""Currency and exchange rate CLI commands for Family Office Ledger."""

import argparse
from datetime import datetime as dt
from decimal import Decimal
from pathlib import Path

from family_office_ledger.cli._main import get_default_db_path
from family_office_ledger.domain.exchange_rates import ExchangeRate, ExchangeRateSource
from family_office_ledger.domain.value_objects import Money
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLiteExchangeRateRepository,
)
from family_office_ledger.services.currency import (
    CurrencyServiceImpl,
    ExchangeRateNotFoundError,
)


def cmd_currency_rates_add(args: argparse.Namespace) -> int:
    """Add an exchange rate."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        db.initialize()
        repo = SQLiteExchangeRateRepository(db)
        service = CurrencyServiceImpl(repo)

        effective_date = dt.strptime(args.date, "%Y-%m-%d").date()
        rate = ExchangeRate(
            from_currency=args.from_currency.upper(),
            to_currency=args.to_currency.upper(),
            rate=Decimal(args.rate),
            effective_date=effective_date,
            source=ExchangeRateSource(args.source),
        )
        service.add_rate(rate)
        print(
            f"Added rate: {args.from_currency.upper()}/{args.to_currency.upper()} "
            f"= {args.rate} (effective {args.date})"
        )
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_currency_rates_list(args: argparse.Namespace) -> int:
    """List exchange rates."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        repo = SQLiteExchangeRateRepository(db)

        start = (
            dt.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else None
        )
        end = dt.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else None

        rates = list(
            repo.list_by_currency_pair(
                args.from_currency.upper(),
                args.to_currency.upper(),
                start_date=start,
                end_date=end,
            )
        )

        if not rates:
            print(
                f"No rates found for {args.from_currency.upper()}/{args.to_currency.upper()}"
            )
            return 0

        print(
            f"Exchange rates for {args.from_currency.upper()}/{args.to_currency.upper()}:"
        )
        print("-" * 50)
        for rate in rates:
            print(f"  {rate.effective_date}: {rate.rate} (source: {rate.source.value})")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_currency_rates_latest(args: argparse.Namespace) -> int:
    """Get latest exchange rate."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        repo = SQLiteExchangeRateRepository(db)
        service = CurrencyServiceImpl(repo)

        rate = service.get_latest_rate(
            args.from_currency.upper(), args.to_currency.upper()
        )
        if rate is None:
            print(
                f"No rate found for {args.from_currency.upper()}/{args.to_currency.upper()}"
            )
            return 1
        print(
            f"Latest {args.from_currency.upper()}/{args.to_currency.upper()}: {rate.rate}"
        )
        print(f"  Effective: {rate.effective_date}")
        print(f"  Source: {rate.source.value}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_currency_convert(args: argparse.Namespace) -> int:
    """Convert amount between currencies."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        repo = SQLiteExchangeRateRepository(db)
        service = CurrencyServiceImpl(repo)

        as_of_date = dt.strptime(args.date, "%Y-%m-%d").date()
        amount = Money(Decimal(args.amount), args.from_currency.upper())

        converted = service.convert(amount, args.to_currency.upper(), as_of_date)
        print(
            f"{args.amount} {args.from_currency.upper()} = {converted.amount} {args.to_currency.upper()}"
        )
        print(f"  As of: {as_of_date}")
        return 0

    except ExchangeRateNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


__all__ = [
    "cmd_currency_rates_add",
    "cmd_currency_rates_list",
    "cmd_currency_rates_latest",
    "cmd_currency_convert",
]
