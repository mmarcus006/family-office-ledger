"""Tests for multi-currency reporting support in ReportingService."""

from datetime import date
from decimal import Decimal

import pytest

from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.exchange_rates import ExchangeRate
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    Money,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteExchangeRateRepository,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.currency import CurrencyServiceImpl
from family_office_ledger.services.reporting import ReportingServiceImpl


@pytest.fixture
def db() -> SQLiteDatabase:
    database = SQLiteDatabase(":memory:")
    database.initialize()
    return database


@pytest.fixture
def entity_repo(db: SQLiteDatabase) -> SQLiteEntityRepository:
    return SQLiteEntityRepository(db)


@pytest.fixture
def account_repo(db: SQLiteDatabase) -> SQLiteAccountRepository:
    return SQLiteAccountRepository(db)


@pytest.fixture
def transaction_repo(db: SQLiteDatabase) -> SQLiteTransactionRepository:
    return SQLiteTransactionRepository(db)


@pytest.fixture
def position_repo(db: SQLiteDatabase) -> SQLitePositionRepository:
    return SQLitePositionRepository(db)


@pytest.fixture
def tax_lot_repo(db: SQLiteDatabase) -> SQLiteTaxLotRepository:
    return SQLiteTaxLotRepository(db)


@pytest.fixture
def security_repo(db: SQLiteDatabase) -> SQLiteSecurityRepository:
    return SQLiteSecurityRepository(db)


@pytest.fixture
def exchange_rate_repo(db: SQLiteDatabase) -> SQLiteExchangeRateRepository:
    return SQLiteExchangeRateRepository(db)


@pytest.fixture
def currency_service(
    exchange_rate_repo: SQLiteExchangeRateRepository,
) -> CurrencyServiceImpl:
    return CurrencyServiceImpl(exchange_rate_repo)


@pytest.fixture
def reporting_service_no_currency(
    entity_repo: SQLiteEntityRepository,
    account_repo: SQLiteAccountRepository,
    transaction_repo: SQLiteTransactionRepository,
    position_repo: SQLitePositionRepository,
    tax_lot_repo: SQLiteTaxLotRepository,
    security_repo: SQLiteSecurityRepository,
) -> ReportingServiceImpl:
    return ReportingServiceImpl(
        entity_repo=entity_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        security_repo=security_repo,
    )


@pytest.fixture
def reporting_service_with_currency(
    entity_repo: SQLiteEntityRepository,
    account_repo: SQLiteAccountRepository,
    transaction_repo: SQLiteTransactionRepository,
    position_repo: SQLitePositionRepository,
    tax_lot_repo: SQLiteTaxLotRepository,
    security_repo: SQLiteSecurityRepository,
    currency_service: CurrencyServiceImpl,
) -> ReportingServiceImpl:
    return ReportingServiceImpl(
        entity_repo=entity_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        security_repo=security_repo,
        currency_service=currency_service,
    )


@pytest.fixture
def test_entity(entity_repo: SQLiteEntityRepository) -> Entity:
    entity = Entity(
        name="Smith Family Trust",
        entity_type=EntityType.TRUST,
        fiscal_year_end=date(2024, 12, 31),
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def usd_account(
    account_repo: SQLiteAccountRepository,
    test_entity: Entity,
) -> Account:
    account = Account(
        name="USD Cash",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
        currency="USD",
    )
    account_repo.add(account)
    return account


@pytest.fixture
def eur_account(
    account_repo: SQLiteAccountRepository,
    test_entity: Entity,
) -> Account:
    account = Account(
        name="EUR Cash",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
        currency="EUR",
    )
    account_repo.add(account)
    return account


@pytest.fixture
def income_account(
    account_repo: SQLiteAccountRepository,
    test_entity: Entity,
) -> Account:
    account = Account(
        name="Income",
        entity_id=test_entity.id,
        account_type=AccountType.INCOME,
        currency="USD",
    )
    account_repo.add(account)
    return account


class TestNetWorthReportWithBaseCurrency:
    def test_net_worth_without_base_currency_backward_compatible(
        self,
        reporting_service_no_currency: ReportingServiceImpl,
        test_entity: Entity,
        usd_account: Account,
        income_account: Account,
        transaction_repo: SQLiteTransactionRepository,
    ):
        txn = Transaction(transaction_date=date(2024, 1, 15), memo="Deposit")
        txn.add_entry(
            Entry(
                account_id=usd_account.id,
                debit_amount=Money(Decimal("10000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=income_account.id,
                credit_amount=Money(Decimal("10000.00")),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_no_currency.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        assert report["report_name"] == "Net Worth Report"
        assert report["totals"]["total_assets"] == Decimal("10000.00")
        assert "base_currency" not in report

    def test_net_worth_with_base_currency_same_currency(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
        test_entity: Entity,
        usd_account: Account,
        income_account: Account,
        transaction_repo: SQLiteTransactionRepository,
    ):
        txn = Transaction(transaction_date=date(2024, 1, 15), memo="Deposit")
        txn.add_entry(
            Entry(
                account_id=usd_account.id,
                debit_amount=Money(Decimal("10000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=income_account.id,
                credit_amount=Money(Decimal("10000.00")),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_with_currency.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
            base_currency="USD",
        )

        assert report["report_name"] == "Net Worth Report"
        assert report["totals"]["total_assets"] == Decimal("10000.00")
        assert report["base_currency"] == "USD"

    def test_net_worth_with_currency_conversion(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
        test_entity: Entity,
        usd_account: Account,
        eur_account: Account,
        income_account: Account,
        transaction_repo: SQLiteTransactionRepository,
        exchange_rate_repo: SQLiteExchangeRateRepository,
    ):
        eur_income = Account(
            name="EUR Income",
            entity_id=test_entity.id,
            account_type=AccountType.INCOME,
            currency="EUR",
        )
        from family_office_ledger.repositories.sqlite import SQLiteAccountRepository

        account_repo = SQLiteAccountRepository(exchange_rate_repo._db)
        account_repo.add(eur_income)

        exchange_rate_repo.add(
            ExchangeRate(
                from_currency="EUR",
                to_currency="USD",
                rate=Decimal("1.10"),
                effective_date=date(2024, 1, 31),
            )
        )

        txn1 = Transaction(transaction_date=date(2024, 1, 15), memo="USD Deposit")
        txn1.add_entry(
            Entry(
                account_id=usd_account.id,
                debit_amount=Money(Decimal("5000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=income_account.id,
                credit_amount=Money(Decimal("5000.00")),
            )
        )
        transaction_repo.add(txn1)

        txn2 = Transaction(transaction_date=date(2024, 1, 15), memo="EUR Deposit")
        txn2.add_entry(
            Entry(
                account_id=eur_account.id,
                debit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=eur_income.id,
                credit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        transaction_repo.add(txn2)

        report = reporting_service_with_currency.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
            base_currency="USD",
        )

        assert report["base_currency"] == "USD"
        assert report["totals"]["total_assets"] == Decimal("6100.00")

    def test_net_worth_graceful_fallback_when_no_exchange_rate(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
        test_entity: Entity,
        eur_account: Account,
        account_repo: SQLiteAccountRepository,
        transaction_repo: SQLiteTransactionRepository,
    ):
        eur_income = Account(
            name="EUR Income",
            entity_id=test_entity.id,
            account_type=AccountType.INCOME,
            currency="EUR",
        )
        account_repo.add(eur_income)

        txn = Transaction(transaction_date=date(2024, 1, 15), memo="EUR Deposit")
        txn.add_entry(
            Entry(
                account_id=eur_account.id,
                debit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        txn.add_entry(
            Entry(
                account_id=eur_income.id,
                credit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_with_currency.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
            base_currency="USD",
        )

        assert report["totals"]["total_assets"] == Decimal("1000.00")

    def test_net_worth_empty_entities_with_base_currency(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
    ):
        report = reporting_service_with_currency.net_worth_report(
            entity_ids=[],
            as_of_date=date(2024, 1, 31),
            base_currency="USD",
        )

        assert report["totals"]["total_assets"] == Decimal("0")
        assert report["base_currency"] == "USD"


class TestFxGainsLossesReport:
    def test_fx_report_without_currency_service(
        self,
        reporting_service_no_currency: ReportingServiceImpl,
        test_entity: Entity,
    ):
        report = reporting_service_no_currency.fx_gains_losses_report(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            base_currency="USD",
        )

        assert report["report_name"] == "FX Gains/Losses Report"
        assert report["error"] == "Currency service not available"
        assert report["data"] == []
        assert report["totals"]["total_fx_gain_loss"] == Decimal("0")

    def test_fx_report_basic(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
        test_entity: Entity,
        eur_account: Account,
        account_repo: SQLiteAccountRepository,
        transaction_repo: SQLiteTransactionRepository,
        exchange_rate_repo: SQLiteExchangeRateRepository,
    ):
        eur_income = Account(
            name="EUR Income",
            entity_id=test_entity.id,
            account_type=AccountType.INCOME,
            currency="EUR",
        )
        account_repo.add(eur_income)

        exchange_rate_repo.add(
            ExchangeRate(
                from_currency="EUR",
                to_currency="USD",
                rate=Decimal("1.10"),
                effective_date=date(2024, 1, 1),
            )
        )
        exchange_rate_repo.add(
            ExchangeRate(
                from_currency="EUR",
                to_currency="USD",
                rate=Decimal("1.15"),
                effective_date=date(2024, 12, 31),
            )
        )

        txn = Transaction(transaction_date=date(2024, 1, 1), memo="EUR Deposit")
        txn.add_entry(
            Entry(
                account_id=eur_account.id,
                debit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        txn.add_entry(
            Entry(
                account_id=eur_income.id,
                credit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_with_currency.fx_gains_losses_report(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            base_currency="USD",
        )

        assert report["report_name"] == "FX Gains/Losses Report"
        assert report["base_currency"] == "USD"
        assert len(report["data"]) >= 1

        eur_entry = next((d for d in report["data"] if d["currency"] == "EUR"), None)
        assert eur_entry is not None
        assert eur_entry["fx_gain_loss"] == Decimal("50.00")
        assert report["totals"]["total_fx_gain_loss"] == Decimal("50.00")

    def test_fx_report_skips_base_currency_accounts(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
        test_entity: Entity,
        usd_account: Account,
        income_account: Account,
        transaction_repo: SQLiteTransactionRepository,
    ):
        txn = Transaction(transaction_date=date(2024, 1, 1), memo="USD Deposit")
        txn.add_entry(
            Entry(
                account_id=usd_account.id,
                debit_amount=Money(Decimal("10000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=income_account.id,
                credit_amount=Money(Decimal("10000.00")),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_with_currency.fx_gains_losses_report(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            base_currency="USD",
        )

        assert report["data"] == []
        assert report["totals"]["total_fx_gain_loss"] == Decimal("0")

    def test_fx_report_handles_missing_exchange_rate(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
        test_entity: Entity,
        eur_account: Account,
        account_repo: SQLiteAccountRepository,
        transaction_repo: SQLiteTransactionRepository,
    ):
        eur_income = Account(
            name="EUR Income",
            entity_id=test_entity.id,
            account_type=AccountType.INCOME,
            currency="EUR",
        )
        account_repo.add(eur_income)

        txn = Transaction(transaction_date=date(2024, 1, 1), memo="EUR Deposit")
        txn.add_entry(
            Entry(
                account_id=eur_account.id,
                debit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        txn.add_entry(
            Entry(
                account_id=eur_income.id,
                credit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_with_currency.fx_gains_losses_report(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            base_currency="USD",
        )

        eur_entry = next((d for d in report["data"] if d["currency"] == "EUR"), None)
        assert eur_entry is not None
        assert eur_entry["fx_gain_loss"] is None
        assert eur_entry["error"] == "Exchange rate not found"

    def test_fx_report_with_none_entity_ids(
        self,
        reporting_service_with_currency: ReportingServiceImpl,
        test_entity: Entity,
    ):
        report = reporting_service_with_currency.fx_gains_losses_report(
            entity_ids=None,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            base_currency="USD",
        )

        assert report["report_name"] == "FX Gains/Losses Report"
        assert "error" not in report


class TestBackwardCompatibility:
    def test_reporting_service_works_without_currency_service(
        self,
        reporting_service_no_currency: ReportingServiceImpl,
        test_entity: Entity,
        usd_account: Account,
        income_account: Account,
        transaction_repo: SQLiteTransactionRepository,
    ):
        txn = Transaction(transaction_date=date(2024, 1, 15), memo="Deposit")
        txn.add_entry(
            Entry(
                account_id=usd_account.id,
                debit_amount=Money(Decimal("5000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=income_account.id,
                credit_amount=Money(Decimal("5000.00")),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_no_currency.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        assert report["totals"]["total_assets"] == Decimal("5000.00")

    def test_base_currency_ignored_without_currency_service(
        self,
        reporting_service_no_currency: ReportingServiceImpl,
        test_entity: Entity,
        eur_account: Account,
        account_repo: SQLiteAccountRepository,
        transaction_repo: SQLiteTransactionRepository,
    ):
        eur_income = Account(
            name="EUR Income",
            entity_id=test_entity.id,
            account_type=AccountType.INCOME,
            currency="EUR",
        )
        account_repo.add(eur_income)

        txn = Transaction(transaction_date=date(2024, 1, 15), memo="EUR Deposit")
        txn.add_entry(
            Entry(
                account_id=eur_account.id,
                debit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        txn.add_entry(
            Entry(
                account_id=eur_income.id,
                credit_amount=Money(Decimal("1000.00"), "EUR"),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service_no_currency.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
            base_currency="USD",
        )

        assert report["totals"]["total_assets"] == Decimal("1000.00")
        assert report["base_currency"] == "USD"
