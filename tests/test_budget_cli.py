from datetime import date
from decimal import Decimal
from uuid import uuid4

from family_office_ledger.cli import main
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
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


class TestBudgetHelp:
    def test_budget_no_subcommand_prints_help(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(["--database", str(db_path), "budget"])

        assert result == 0
        captured = capsys.readouterr()
        assert "budget" in captured.out.lower()


class TestBudgetCreate:
    def test_create_budget_success(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "create",
                "--name",
                "Q1 2024 Budget",
                "--entity-id",
                str(entity.id),
                "--period-type",
                "quarterly",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-03-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Created budget" in captured.out
        assert "Q1 2024 Budget" in captured.out
        assert "quarterly" in captured.out

    def test_create_budget_invalid_date_format(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "create",
                "--name",
                "Bad Budget",
                "--entity-id",
                str(entity.id),
                "--period-type",
                "monthly",
                "--start-date",
                "01/01/2024",
                "--end-date",
                "01/31/2024",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_create_budget_missing_database(self, tmp_path, capsys):
        db_path = tmp_path / "nonexistent.db"

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "create",
                "--name",
                "Test Budget",
                "--entity-id",
                str(uuid4()),
                "--period-type",
                "annual",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-12-31",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Database not found" in captured.out


class TestBudgetList:
    def test_list_budgets_empty(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "list",
                "--entity-id",
                str(entity.id),
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "No budgets found" in captured.out

    def test_list_budgets_with_data(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        budget = service.create_budget(
            name="Q1 Budget",
            entity_id=entity.id,
            period_type="quarterly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "list",
                "--entity-id",
                str(entity.id),
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Q1 Budget" in captured.out
        assert "quarterly" in captured.out
        assert "Active" in captured.out


class TestBudgetAddLine:
    def test_add_line_item_success(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        budget = service.create_budget(
            name="Q1 Budget",
            entity_id=entity.id,
            period_type="quarterly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "add-line",
                "--budget-id",
                str(budget.id),
                "--category",
                "office supplies",
                "--amount",
                "5000.00",
                "--currency",
                "USD",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Added line item" in captured.out
        assert "office supplies" in captured.out

    def test_add_line_item_with_account(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        account_repo = SQLiteAccountRepository(db)
        account = Account(
            name="Checking",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
        )
        account_repo.add(account)

        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        budget = service.create_budget(
            name="Q1 Budget",
            entity_id=entity.id,
            period_type="quarterly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "add-line",
                "--budget-id",
                str(budget.id),
                "--category",
                "utilities",
                "--amount",
                "1000.00",
                "--currency",
                "USD",
                "--account-id",
                str(account.id),
                "--notes",
                "Quarterly utilities estimate",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Added line item" in captured.out
        assert "utilities" in captured.out


class TestBudgetVariance:
    def test_variance_no_budget(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "variance",
                "--entity-id",
                str(entity.id),
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-03-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "No active budget found" in captured.out

    def test_variance_with_budget(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        budget = service.create_budget(
            name="Q1 Budget",
            entity_id=entity.id,
            period_type="quarterly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        service.add_line_item(
            budget_id=budget.id,
            category="office supplies",
            budgeted_amount=Money(Decimal("5000.00"), "USD"),
        )

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "variance",
                "--entity-id",
                str(entity.id),
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-03-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Budget Variance Report" in captured.out
        assert "office supplies" in captured.out


class TestBudgetAlerts:
    def test_alerts_no_budget(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "alerts",
                "--entity-id",
                str(entity.id),
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-03-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "No active budget found" in captured.out

    def test_alerts_with_budget(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        budget = service.create_budget(
            name="Q1 Budget",
            entity_id=entity.id,
            period_type="quarterly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        service.add_line_item(
            budget_id=budget.id,
            category="office supplies",
            budgeted_amount=Money(Decimal("5000.00"), "USD"),
        )

        result = main(
            [
                "--database",
                str(db_path),
                "budget",
                "alerts",
                "--entity-id",
                str(entity.id),
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-03-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Budget Alerts" in captured.out or "No budget alerts" in captured.out
