"""Tests for ReportingService implementation."""

import json
import os
import tempfile
from datetime import date
from decimal import Decimal

import pytest

from family_office_ledger.domain.entities import Account, Entity, Position, Security
from family_office_ledger.domain.transactions import Entry, TaxLot, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    AcquisitionType,
    AssetClass,
    EntityType,
    Money,
    Quantity,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.reporting import ReportingServiceImpl


@pytest.fixture
def db() -> SQLiteDatabase:
    """Create an in-memory SQLite database for testing."""
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
def reporting_service(
    entity_repo: SQLiteEntityRepository,
    account_repo: SQLiteAccountRepository,
    transaction_repo: SQLiteTransactionRepository,
    position_repo: SQLitePositionRepository,
    tax_lot_repo: SQLiteTaxLotRepository,
    security_repo: SQLiteSecurityRepository,
) -> ReportingServiceImpl:
    """Create ReportingService with all repositories."""
    return ReportingServiceImpl(
        entity_repo=entity_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        position_repo=position_repo,
        tax_lot_repo=tax_lot_repo,
        security_repo=security_repo,
    )


@pytest.fixture
def test_entity(entity_repo: SQLiteEntityRepository) -> Entity:
    """Create and persist a test entity."""
    entity = Entity(
        name="Smith Family Trust",
        entity_type=EntityType.TRUST,
        fiscal_year_end=date(2024, 12, 31),
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def test_entity_2(entity_repo: SQLiteEntityRepository) -> Entity:
    """Create and persist a second test entity."""
    entity = Entity(
        name="Smith Holdings LLC",
        entity_type=EntityType.LLC,
        fiscal_year_end=date(2024, 12, 31),
    )
    entity_repo.add(entity)
    return entity


@pytest.fixture
def test_accounts(
    account_repo: SQLiteAccountRepository,
    test_entity: Entity,
) -> dict[str, Account]:
    """Create and persist test accounts."""
    cash = Account(
        name="Cash",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )
    brokerage = Account(
        name="Brokerage",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.BROKERAGE,
    )
    income = Account(
        name="Income",
        entity_id=test_entity.id,
        account_type=AccountType.INCOME,
    )
    expense = Account(
        name="Expenses",
        entity_id=test_entity.id,
        account_type=AccountType.EXPENSE,
    )
    liability = Account(
        name="Credit Card",
        entity_id=test_entity.id,
        account_type=AccountType.LIABILITY,
        sub_type=AccountSubType.CREDIT_CARD,
    )
    equity = Account(
        name="Retained Earnings",
        entity_id=test_entity.id,
        account_type=AccountType.EQUITY,
    )
    account_repo.add(cash)
    account_repo.add(brokerage)
    account_repo.add(income)
    account_repo.add(expense)
    account_repo.add(liability)
    account_repo.add(equity)
    return {
        "cash": cash,
        "brokerage": brokerage,
        "income": income,
        "expense": expense,
        "liability": liability,
        "equity": equity,
    }


@pytest.fixture
def test_security(security_repo: SQLiteSecurityRepository) -> Security:
    """Create and persist a test security."""
    security = Security(
        symbol="AAPL",
        name="Apple Inc.",
        cusip="037833100",
        asset_class=AssetClass.EQUITY,
    )
    security_repo.add(security)
    return security


@pytest.fixture
def test_security_2(security_repo: SQLiteSecurityRepository) -> Security:
    """Create and persist a second test security."""
    security = Security(
        symbol="GOOGL",
        name="Alphabet Inc.",
        asset_class=AssetClass.EQUITY,
    )
    security_repo.add(security)
    return security


# ===== net_worth_report Tests =====


class TestNetWorthReport:
    def test_net_worth_report_basic(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Net worth report should calculate total assets minus liabilities."""
        # Create transaction: cash deposit
        txn = Transaction(transaction_date=date(2024, 1, 15), memo="Initial deposit")
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("10000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("10000.00")),
            )
        )
        transaction_repo.add(txn)

        # Add liability transaction
        txn2 = Transaction(
            transaction_date=date(2024, 1, 20), memo="Credit card charge"
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["liability"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        transaction_repo.add(txn2)

        report = reporting_service.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        assert report["report_name"] == "Net Worth Report"
        assert report["as_of_date"] == date(2024, 1, 31)
        assert "data" in report
        assert "totals" in report
        # Total assets = 10000 (cash), Total liabilities = 500
        assert report["totals"]["total_assets"] == Decimal("10000.00")
        assert report["totals"]["total_liabilities"] == Decimal("500.00")
        assert report["totals"]["net_worth"] == Decimal("9500.00")

    def test_net_worth_report_multiple_entities(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_entity_2: Entity,
        test_accounts: dict[str, Account],
        account_repo: SQLiteAccountRepository,
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Net worth report should aggregate across multiple entities."""
        # Create account for entity 2
        cash2 = Account(
            name="Cash",
            entity_id=test_entity_2.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
        )
        income2 = Account(
            name="Income",
            entity_id=test_entity_2.id,
            account_type=AccountType.INCOME,
        )
        account_repo.add(cash2)
        account_repo.add(income2)

        # Deposit to entity 1
        txn1 = Transaction(transaction_date=date(2024, 1, 15))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("5000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("5000.00")),
            )
        )
        transaction_repo.add(txn1)

        # Deposit to entity 2
        txn2 = Transaction(transaction_date=date(2024, 1, 15))
        txn2.add_entry(
            Entry(
                account_id=cash2.id,
                debit_amount=Money(Decimal("3000.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=income2.id,
                credit_amount=Money(Decimal("3000.00")),
            )
        )
        transaction_repo.add(txn2)

        report = reporting_service.net_worth_report(
            entity_ids=[test_entity.id, test_entity_2.id],
            as_of_date=date(2024, 1, 31),
        )

        assert report["totals"]["total_assets"] == Decimal("8000.00")
        assert report["totals"]["net_worth"] == Decimal("8000.00")

    def test_net_worth_report_all_entities_when_none_specified(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Net worth report with None entity_ids should include all entities."""
        txn = Transaction(transaction_date=date(2024, 1, 15))
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service.net_worth_report(
            entity_ids=None,
            as_of_date=date(2024, 1, 31),
        )

        assert report["totals"]["total_assets"] == Decimal("1000.00")

    def test_net_worth_report_empty_entities(
        self,
        reporting_service: ReportingServiceImpl,
    ):
        """Net worth report with no entities should return zeros."""
        report = reporting_service.net_worth_report(
            entity_ids=[],
            as_of_date=date(2024, 1, 31),
        )

        assert report["totals"]["total_assets"] == Decimal("0")
        assert report["totals"]["total_liabilities"] == Decimal("0")
        assert report["totals"]["net_worth"] == Decimal("0")


# ===== balance_sheet_report Tests =====


class TestBalanceSheetReport:
    def test_balance_sheet_report_basic(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Balance sheet should show assets, liabilities, and equity."""
        # Create transactions
        txn = Transaction(transaction_date=date(2024, 1, 15))
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("10000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["equity"].id,
                credit_amount=Money(Decimal("10000.00")),
            )
        )
        transaction_repo.add(txn)

        # Add liability
        txn2 = Transaction(transaction_date=date(2024, 1, 20))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["liability"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn2)

        report = reporting_service.balance_sheet_report(
            entity_id=test_entity.id,
            as_of_date=date(2024, 1, 31),
        )

        assert report["report_name"] == "Balance Sheet"
        assert report["as_of_date"] == date(2024, 1, 31)
        assert "data" in report
        assert "totals" in report
        assert "assets" in report["data"]
        assert "liabilities" in report["data"]
        assert "equity" in report["data"]
        assert report["totals"]["total_assets"] == Decimal("10000.00")
        assert report["totals"]["total_liabilities"] == Decimal("1000.00")
        assert report["totals"]["total_equity"] == Decimal("10000.00")

    def test_balance_sheet_report_no_transactions(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
    ):
        """Balance sheet with no transactions should show zeros."""
        report = reporting_service.balance_sheet_report(
            entity_id=test_entity.id,
            as_of_date=date(2024, 1, 31),
        )

        assert report["totals"]["total_assets"] == Decimal("0")
        assert report["totals"]["total_liabilities"] == Decimal("0")
        assert report["totals"]["total_equity"] == Decimal("0")


# ===== income_statement_report Tests =====


class TestIncomeStatementReport:
    def test_income_statement_report_basic(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Income statement should show income minus expenses."""
        # Add income transaction
        txn1 = Transaction(transaction_date=date(2024, 1, 15))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("5000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("5000.00")),
            )
        )
        transaction_repo.add(txn1)

        # Add expense transaction
        txn2 = Transaction(transaction_date=date(2024, 1, 20))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("1500.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("1500.00")),
            )
        )
        transaction_repo.add(txn2)

        report = reporting_service.income_statement_report(
            entity_id=test_entity.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert report["report_name"] == "Income Statement"
        assert report["date_range"]["start_date"] == date(2024, 1, 1)
        assert report["date_range"]["end_date"] == date(2024, 1, 31)
        assert "data" in report
        assert "totals" in report
        assert report["totals"]["total_income"] == Decimal("5000.00")
        assert report["totals"]["total_expenses"] == Decimal("1500.00")
        assert report["totals"]["net_income"] == Decimal("3500.00")

    def test_income_statement_report_date_range_filter(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Income statement should filter transactions by date range."""
        # Transaction in January
        txn1 = Transaction(transaction_date=date(2024, 1, 15))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn1)

        # Transaction in February
        txn2 = Transaction(transaction_date=date(2024, 2, 15))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("2000.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("2000.00")),
            )
        )
        transaction_repo.add(txn2)

        # Get January only
        report = reporting_service.income_statement_report(
            entity_id=test_entity.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert report["totals"]["total_income"] == Decimal("1000.00")

    def test_income_statement_report_no_transactions(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
    ):
        """Income statement with no transactions should show zeros."""
        report = reporting_service.income_statement_report(
            entity_id=test_entity.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert report["totals"]["total_income"] == Decimal("0")
        assert report["totals"]["total_expenses"] == Decimal("0")
        assert report["totals"]["net_income"] == Decimal("0")


# ===== capital_gains_report Tests =====


class TestCapitalGainsReport:
    def test_capital_gains_report_basic(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_security: Security,
        position_repo: SQLitePositionRepository,
        tax_lot_repo: SQLiteTaxLotRepository,
    ):
        """Capital gains report should show realized gains by lot."""
        # Create a position
        position = Position(
            account_id=test_accounts["brokerage"].id,
            security_id=test_security.id,
        )
        position_repo.add(position)

        # Create a tax lot that was sold (fully disposed)
        lot = TaxLot(
            position_id=position.id,
            acquisition_date=date(2023, 6, 15),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("50")),
            acquisition_type=AcquisitionType.PURCHASE,
            disposition_date=date(2024, 3, 15),
        )
        lot.remaining_quantity = Quantity(Decimal("0"))
        tax_lot_repo.add(lot)

        report = reporting_service.capital_gains_report(
            entity_ids=[test_entity.id],
            tax_year=2024,
        )

        assert report["report_name"] == "Capital Gains Report"
        assert report["tax_year"] == 2024
        assert "data" in report
        assert "totals" in report
        assert len(report["data"]) >= 1

    def test_capital_gains_report_long_term_vs_short_term(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_security: Security,
        position_repo: SQLitePositionRepository,
        tax_lot_repo: SQLiteTaxLotRepository,
    ):
        """Capital gains should distinguish long-term from short-term."""
        position = Position(
            account_id=test_accounts["brokerage"].id,
            security_id=test_security.id,
        )
        position_repo.add(position)

        # Short-term lot (held < 1 year)
        short_lot = TaxLot(
            position_id=position.id,
            acquisition_date=date(2024, 1, 1),
            cost_per_share=Money(Decimal("100.00")),
            original_quantity=Quantity(Decimal("10")),
            disposition_date=date(2024, 6, 1),
        )
        short_lot.remaining_quantity = Quantity(Decimal("0"))
        tax_lot_repo.add(short_lot)

        # Long-term lot (held > 1 year)
        long_lot = TaxLot(
            position_id=position.id,
            acquisition_date=date(2022, 1, 1),
            cost_per_share=Money(Decimal("50.00")),
            original_quantity=Quantity(Decimal("20")),
            disposition_date=date(2024, 6, 1),
        )
        long_lot.remaining_quantity = Quantity(Decimal("0"))
        tax_lot_repo.add(long_lot)

        report = reporting_service.capital_gains_report(
            entity_ids=[test_entity.id],
            tax_year=2024,
        )

        # Verify both lots are in the report
        assert len(report["data"]) >= 2
        # Check totals include both categories
        assert "short_term_gains" in report["totals"]
        assert "long_term_gains" in report["totals"]

    def test_capital_gains_report_no_dispositions(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
    ):
        """Capital gains report with no dispositions should show empty data."""
        report = reporting_service.capital_gains_report(
            entity_ids=[test_entity.id],
            tax_year=2024,
        )

        assert report["data"] == []
        assert report["totals"]["short_term_gains"] == Decimal("0")
        assert report["totals"]["long_term_gains"] == Decimal("0")
        assert report["totals"]["total_gains"] == Decimal("0")


# ===== position_summary_report Tests =====


class TestPositionSummaryReport:
    def test_position_summary_report_basic(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_security: Security,
        position_repo: SQLitePositionRepository,
    ):
        """Position summary should show holdings by security."""
        position = Position(
            account_id=test_accounts["brokerage"].id,
            security_id=test_security.id,
        )
        position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )
        position._market_value = Money(Decimal("17500.00"))
        position_repo.add(position)

        report = reporting_service.position_summary_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        assert report["report_name"] == "Position Summary"
        assert report["as_of_date"] == date(2024, 1, 31)
        assert len(report["data"]) >= 1
        assert report["totals"]["total_cost_basis"] == Decimal("15000.00")
        assert report["totals"]["total_market_value"] == Decimal("17500.00")
        assert report["totals"]["total_unrealized_gain"] == Decimal("2500.00")

    def test_position_summary_report_multiple_securities(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_security: Security,
        test_security_2: Security,
        position_repo: SQLitePositionRepository,
    ):
        """Position summary should aggregate multiple securities."""
        position1 = Position(
            account_id=test_accounts["brokerage"].id,
            security_id=test_security.id,
        )
        position1.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("10000.00")),
        )
        position1._market_value = Money(Decimal("12000.00"))
        position_repo.add(position1)

        position2 = Position(
            account_id=test_accounts["brokerage"].id,
            security_id=test_security_2.id,
        )
        position2.update_from_lots(
            total_quantity=Quantity(Decimal("50")),
            total_cost=Money(Decimal("5000.00")),
        )
        position2._market_value = Money(Decimal("6000.00"))
        position_repo.add(position2)

        report = reporting_service.position_summary_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        assert len(report["data"]) >= 2
        assert report["totals"]["total_cost_basis"] == Decimal("15000.00")
        assert report["totals"]["total_market_value"] == Decimal("18000.00")
        assert report["totals"]["total_unrealized_gain"] == Decimal("3000.00")

    def test_position_summary_report_no_positions(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
    ):
        """Position summary with no positions should show empty data."""
        report = reporting_service.position_summary_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        assert report["data"] == []
        assert report["totals"]["total_cost_basis"] == Decimal("0")
        assert report["totals"]["total_market_value"] == Decimal("0")
        assert report["totals"]["total_unrealized_gain"] == Decimal("0")


# ===== export_report Tests =====


class TestExportReport:
    def test_export_report_json(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Export report to JSON format."""
        # Create a simple transaction for the report
        txn = Transaction(transaction_date=date(2024, 1, 15))
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn)

        report = reporting_service.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result_path = reporting_service.export_report(
                report_data=report,
                output_format="json",
                output_path=output_path,
            )

            assert result_path == output_path
            assert os.path.exists(output_path)

            with open(output_path) as f:
                loaded = json.load(f)

            assert loaded["report_name"] == "Net Worth Report"
            assert "totals" in loaded
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_export_report_csv(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_security: Security,
        position_repo: SQLitePositionRepository,
    ):
        """Export report to CSV format."""
        position = Position(
            account_id=test_accounts["brokerage"].id,
            security_id=test_security.id,
        )
        position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )
        position._market_value = Money(Decimal("17500.00"))
        position_repo.add(position)

        report = reporting_service.position_summary_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            result_path = reporting_service.export_report(
                report_data=report,
                output_format="csv",
                output_path=output_path,
            )

            assert result_path == output_path
            assert os.path.exists(output_path)

            with open(output_path) as f:
                content = f.read()

            # CSV should have header row and data
            lines = content.strip().split("\n")
            assert len(lines) >= 2  # Header + at least one data row
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_export_report_invalid_format(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
    ):
        """Export with invalid format should raise ValueError."""
        report = reporting_service.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        with pytest.raises(ValueError, match="Unsupported format"):
            reporting_service.export_report(
                report_data=report,
                output_format="xml",
                output_path="/tmp/test.xml",
            )

    def test_export_report_csv_with_nested_data(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Export CSV should flatten nested report data."""
        txn = Transaction(transaction_date=date(2024, 1, 15))
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("5000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["equity"].id,
                credit_amount=Money(Decimal("5000.00")),
            )
        )
        transaction_repo.add(txn)

        # Balance sheet has nested data structure (assets, liabilities, equity)
        report = reporting_service.balance_sheet_report(
            entity_id=test_entity.id,
            as_of_date=date(2024, 1, 31),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            reporting_service.export_report(
                report_data=report,
                output_format="csv",
                output_path=output_path,
            )

            assert os.path.exists(output_path)

            with open(output_path) as f:
                content = f.read()

            # Should have content
            assert len(content) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


# ===== Integration Tests =====


class TestReportingServiceIntegration:
    def test_full_workflow_generate_and_export_reports(
        self,
        reporting_service: ReportingServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_security: Security,
        transaction_repo: SQLiteTransactionRepository,
        position_repo: SQLitePositionRepository,
    ):
        """Complete workflow: create data, generate reports, export."""
        # Create some transactions
        txn1 = Transaction(transaction_date=date(2024, 1, 15), memo="Initial capital")
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("50000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["equity"].id,
                credit_amount=Money(Decimal("50000.00")),
            )
        )
        transaction_repo.add(txn1)

        # Income transaction
        txn2 = Transaction(transaction_date=date(2024, 1, 20), memo="Consulting income")
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("10000.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("10000.00")),
            )
        )
        transaction_repo.add(txn2)

        # Expense transaction
        txn3 = Transaction(transaction_date=date(2024, 1, 25), memo="Office rent")
        txn3.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("2000.00")),
            )
        )
        txn3.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("2000.00")),
            )
        )
        transaction_repo.add(txn3)

        # Create investment position
        position = Position(
            account_id=test_accounts["brokerage"].id,
            security_id=test_security.id,
        )
        position.update_from_lots(
            total_quantity=Quantity(Decimal("100")),
            total_cost=Money(Decimal("15000.00")),
        )
        position._market_value = Money(Decimal("18000.00"))
        position_repo.add(position)

        # Generate all reports
        net_worth = reporting_service.net_worth_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )
        balance_sheet = reporting_service.balance_sheet_report(
            entity_id=test_entity.id,
            as_of_date=date(2024, 1, 31),
        )
        income_stmt = reporting_service.income_statement_report(
            entity_id=test_entity.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        positions = reporting_service.position_summary_report(
            entity_ids=[test_entity.id],
            as_of_date=date(2024, 1, 31),
        )

        # Verify reports have expected data
        # Cash: 50000 + 10000 - 2000 = 58000
        assert net_worth["totals"]["total_assets"] == Decimal("58000.00")
        assert balance_sheet["totals"]["total_assets"] == Decimal("58000.00")
        assert income_stmt["totals"]["total_income"] == Decimal("10000.00")
        assert income_stmt["totals"]["total_expenses"] == Decimal("2000.00")
        assert income_stmt["totals"]["net_income"] == Decimal("8000.00")
        assert positions["totals"]["total_unrealized_gain"] == Decimal("3000.00")

        # Export each report
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "net_worth.json")
            csv_path = os.path.join(tmpdir, "positions.csv")

            reporting_service.export_report(net_worth, "json", json_path)
            reporting_service.export_report(positions, "csv", csv_path)

            assert os.path.exists(json_path)
            assert os.path.exists(csv_path)

            with open(json_path) as f:
                loaded = json.load(f)
                assert loaded["report_name"] == "Net Worth Report"
