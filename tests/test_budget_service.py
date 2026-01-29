"""Tests for BudgetService implementation."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.budgets import BudgetPeriodType
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    ExpenseCategory,
    Money,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteBudgetRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)
from family_office_ledger.services.budget import BudgetServiceImpl
from family_office_ledger.services.expense import ExpenseServiceImpl


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
def vendor_repo(db: SQLiteDatabase) -> SQLiteVendorRepository:
    return SQLiteVendorRepository(db)


@pytest.fixture
def budget_repo(db: SQLiteDatabase) -> SQLiteBudgetRepository:
    return SQLiteBudgetRepository(db)


@pytest.fixture
def expense_service(
    transaction_repo: SQLiteTransactionRepository,
    account_repo: SQLiteAccountRepository,
    vendor_repo: SQLiteVendorRepository,
) -> ExpenseServiceImpl:
    return ExpenseServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        vendor_repo=vendor_repo,
    )


@pytest.fixture
def budget_service(
    budget_repo: SQLiteBudgetRepository,
    expense_service: ExpenseServiceImpl,
) -> BudgetServiceImpl:
    return BudgetServiceImpl(
        budget_repo=budget_repo,
        expense_service=expense_service,
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
def test_accounts(
    account_repo: SQLiteAccountRepository,
    test_entity: Entity,
) -> dict[str, Account]:
    cash = Account(
        name="Cash",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
    )
    expense_account = Account(
        name="Expenses",
        entity_id=test_entity.id,
        account_type=AccountType.EXPENSE,
    )
    legal_expense = Account(
        name="Legal Expenses",
        entity_id=test_entity.id,
        account_type=AccountType.EXPENSE,
    )
    software_expense = Account(
        name="Software Expenses",
        entity_id=test_entity.id,
        account_type=AccountType.EXPENSE,
    )
    account_repo.add(cash)
    account_repo.add(expense_account)
    account_repo.add(legal_expense)
    account_repo.add(software_expense)
    return {
        "cash": cash,
        "expense": expense_account,
        "legal": legal_expense,
        "software": software_expense,
    }


class TestCreateBudget:
    def test_create_budget_basic(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Q1 2024 Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.QUARTERLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        assert budget.name == "Q1 2024 Budget"
        assert budget.entity_id == test_entity.id
        assert budget.period_type == BudgetPeriodType.QUARTERLY
        assert budget.start_date == date(2024, 1, 1)
        assert budget.end_date == date(2024, 3, 31)
        assert budget.is_active is True

    def test_create_budget_monthly(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="January 2024",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert budget.period_type == BudgetPeriodType.MONTHLY


class TestGetBudget:
    def test_get_budget_exists(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        created = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.ANNUAL.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        retrieved = budget_service.get_budget(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Budget"

    def test_get_budget_not_found(
        self,
        budget_service: BudgetServiceImpl,
    ):
        result = budget_service.get_budget(uuid4())
        assert result is None


class TestUpdateBudget:
    def test_update_budget_name(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Original Name",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.QUARTERLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        budget.name = "Updated Name"
        budget_service.update_budget(budget)

        retrieved = budget_service.get_budget(budget.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    def test_update_budget_deactivate(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.QUARTERLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        budget.deactivate()
        budget_service.update_budget(budget)

        retrieved = budget_service.get_budget(budget.id)
        assert retrieved is not None
        assert retrieved.is_active is False


class TestDeleteBudget:
    def test_delete_budget(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="To Delete",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.delete_budget(budget.id)

        result = budget_service.get_budget(budget.id)
        assert result is None


class TestAddLineItem:
    def test_add_line_item_basic(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        line_item = budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("5000.00")),
        )

        assert line_item.budget_id == budget.id
        assert line_item.category == ExpenseCategory.LEGAL.value
        assert line_item.budgeted_amount == Money(Decimal("5000.00"))

    def test_add_line_item_with_notes(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        line_item = budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.SOFTWARE.value,
            budgeted_amount=Money(Decimal("1000.00")),
            notes="SaaS subscriptions",
        )

        assert line_item.notes == "SaaS subscriptions"

    def test_add_line_item_with_account(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        line_item = budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("5000.00")),
            account_id=test_accounts["legal"].id,
        )

        assert line_item.account_id == test_accounts["legal"].id


class TestGetLineItems:
    def test_get_line_items(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("5000.00")),
        )
        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.SOFTWARE.value,
            budgeted_amount=Money(Decimal("1000.00")),
        )

        line_items = budget_service.get_line_items(budget.id)

        assert len(line_items) == 2
        categories = {item.category for item in line_items}
        assert ExpenseCategory.LEGAL.value in categories
        assert ExpenseCategory.SOFTWARE.value in categories


class TestCalculateVariance:
    def test_calculate_variance_under_budget(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("5000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("3000.00")),
        }

        variances = budget_service.calculate_variance(budget.id, actual_expenses)

        assert len(variances) == 1
        variance = variances[0]
        assert variance.category == ExpenseCategory.LEGAL.value
        assert variance.budgeted == Money(Decimal("5000.00"))
        assert variance.actual == Money(Decimal("3000.00"))
        assert variance.variance == Money(Decimal("2000.00"))
        assert variance.is_over_budget is False

    def test_calculate_variance_over_budget(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("5000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("7000.00")),
        }

        variances = budget_service.calculate_variance(budget.id, actual_expenses)

        assert len(variances) == 1
        variance = variances[0]
        assert variance.is_over_budget is True
        assert variance.variance == Money(Decimal("-2000.00"))

    def test_calculate_variance_no_actual_expenses(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("5000.00")),
        )

        variances = budget_service.calculate_variance(budget.id, {})

        assert len(variances) == 1
        variance = variances[0]
        assert variance.actual == Money(Decimal("0"))
        assert variance.is_over_budget is False


class TestGetBudgetVsActual:
    def test_get_budget_vs_actual_with_budget(
        self,
        budget_service: BudgetServiceImpl,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        budget = budget_service.create_budget(
            name="January 2024",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("5000.00")),
        )

        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            category=ExpenseCategory.LEGAL.value,
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["legal"].id,
                debit_amount=Money(Decimal("3000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("3000.00")),
            )
        )
        transaction_repo.add(txn)

        result = budget_service.get_budget_vs_actual(
            entity_id=test_entity.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert result["budget"] is not None
        assert result["budget"].id == budget.id
        assert len(result["line_items"]) == 1
        assert ExpenseCategory.LEGAL.value in result["actual_expenses"]
        assert len(result["variances"]) == 1

    def test_get_budget_vs_actual_no_budget(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        result = budget_service.get_budget_vs_actual(
            entity_id=test_entity.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert result["budget"] is None
        assert result["line_items"] == []
        assert result["actual_expenses"] == {}
        assert result["variances"] == []


class TestCheckAlerts:
    def test_check_alerts_80_percent_warning(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("1000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("850.00")),
        }

        alerts = budget_service.check_alerts(budget.id, actual_expenses)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["category"] == ExpenseCategory.LEGAL.value
        assert alert["threshold"] == 80
        assert alert["status"] == "warning"
        assert alert["percent_used"] == 85.0

    def test_check_alerts_90_percent_warning(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("1000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("950.00")),
        }

        alerts = budget_service.check_alerts(budget.id, actual_expenses)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["threshold"] == 90
        assert alert["status"] == "warning"

    def test_check_alerts_100_percent_over_budget(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("1000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("1050.00")),
        }

        alerts = budget_service.check_alerts(budget.id, actual_expenses)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["threshold"] == 100
        assert alert["status"] == "over_budget"

    def test_check_alerts_110_percent_severely_over(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("1000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("1200.00")),
        }

        alerts = budget_service.check_alerts(budget.id, actual_expenses)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["threshold"] == 110
        assert alert["status"] == "over_budget"
        assert alert["percent_used"] == 120.0

    def test_check_alerts_no_alert_under_threshold(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("1000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("500.00")),
        }

        alerts = budget_service.check_alerts(budget.id, actual_expenses)

        assert len(alerts) == 0

    def test_check_alerts_custom_thresholds(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("1000.00")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("550.00")),
        }

        alerts = budget_service.check_alerts(
            budget.id, actual_expenses, thresholds=[50, 75]
        )

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["threshold"] == 50
        assert alert["percent_used"] == 55.0

    def test_check_alerts_zero_budget_skipped(
        self,
        budget_service: BudgetServiceImpl,
        test_entity: Entity,
    ):
        budget = budget_service.create_budget(
            name="Test Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.MONTHLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("0")),
        )

        actual_expenses = {
            ExpenseCategory.LEGAL.value: Money(Decimal("500.00")),
        }

        alerts = budget_service.check_alerts(budget.id, actual_expenses)

        assert len(alerts) == 0


class TestBudgetServiceIntegration:
    def test_full_budget_workflow(
        self,
        budget_service: BudgetServiceImpl,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        budget = budget_service.create_budget(
            name="Q1 2024 Operating Budget",
            entity_id=test_entity.id,
            period_type=BudgetPeriodType.QUARTERLY.value,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.LEGAL.value,
            budgeted_amount=Money(Decimal("10000.00")),
        )
        budget_service.add_line_item(
            budget_id=budget.id,
            category=ExpenseCategory.SOFTWARE.value,
            budgeted_amount=Money(Decimal("3000.00")),
        )

        txn1 = Transaction(
            transaction_date=date(2024, 1, 15),
            category=ExpenseCategory.LEGAL.value,
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["legal"].id,
                debit_amount=Money(Decimal("8500.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("8500.00")),
            )
        )
        transaction_repo.add(txn1)

        txn2 = Transaction(
            transaction_date=date(2024, 2, 1),
            category=ExpenseCategory.SOFTWARE.value,
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["software"].id,
                debit_amount=Money(Decimal("2500.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("2500.00")),
            )
        )
        transaction_repo.add(txn2)

        result = budget_service.get_budget_vs_actual(
            entity_id=test_entity.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        assert result["budget"] is not None
        assert len(result["variances"]) == 2

        actual_expenses = result["actual_expenses"]
        alerts = budget_service.check_alerts(budget.id, actual_expenses)

        legal_alerts = [
            a for a in alerts if a["category"] == ExpenseCategory.LEGAL.value
        ]
        assert len(legal_alerts) == 1
        assert legal_alerts[0]["threshold"] == 80
        assert legal_alerts[0]["status"] == "warning"

        software_alerts = [
            a for a in alerts if a["category"] == ExpenseCategory.SOFTWARE.value
        ]
        assert len(software_alerts) == 1
        assert software_alerts[0]["threshold"] == 80
        assert software_alerts[0]["status"] == "warning"
