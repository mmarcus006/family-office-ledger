from uuid import uuid4

from family_office_ledger.cli import main
from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    Money,
)
from family_office_ledger.domain.vendors import Vendor
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)


class TestExpenseHelp:
    def test_expense_no_subcommand_prints_help(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(["--database", str(db_path), "expense"])

        assert result == 0
        captured = capsys.readouterr()
        assert "expense" in captured.out.lower()


class TestExpenseCategorize:
    def test_categorize_transaction(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        entity_repo = SQLiteEntityRepository(db)
        account_repo = SQLiteAccountRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)

        entity = Entity(name="Test Corp", entity_type=EntityType.LLC)
        entity_repo.add(entity)

        account = Account(
            name="Checking",
            entity_id=entity.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
        )
        account_repo.add(account)

        from datetime import date

        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Test transaction",
            entries=[
                Entry(
                    account_id=account.id,
                    debit_amount=Money("100.00"),
                    credit_amount=Money("0.00"),
                )
            ],
        )
        transaction_repo.add(txn)

        result = main(
            [
                "--database",
                str(db_path),
                "expense",
                "categorize",
                "--txn-id",
                str(txn.id),
                "--category",
                "legal",
                "--tags",
                "tax,q1",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "categorized" in captured.out
        assert "legal" in captured.out

    def test_categorize_invalid_txn_id(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "expense",
                "categorize",
                "--txn-id",
                "invalid-uuid",
                "--category",
                "legal",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid" in captured.out


class TestExpenseSummary:
    def test_expense_summary(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "expense",
                "summary",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Expense Summary" in captured.out
        assert "Total Expenses" in captured.out


class TestExpenseByCategory:
    def test_expense_by_category(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "expense",
                "by-category",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Expenses by Category" in captured.out


class TestExpenseByVendor:
    def test_expense_by_vendor(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "expense",
                "by-vendor",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Expenses by Vendor" in captured.out


class TestExpenseRecurring:
    def test_expense_recurring(self, tmp_path, capsys):
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
                "expense",
                "recurring",
                "--entity-id",
                str(entity.id),
                "--lookback-months",
                "3",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Recurring Expenses" in captured.out

    def test_expense_recurring_invalid_entity(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "expense",
                "recurring",
                "--entity-id",
                "invalid-uuid",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid entity ID" in captured.out


class TestVendorHelp:
    def test_vendor_no_subcommand_prints_help(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(["--database", str(db_path), "vendor"])

        assert result == 0
        captured = capsys.readouterr()
        assert "vendor" in captured.out.lower()


class TestVendorAdd:
    def test_vendor_add(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "vendor",
                "add",
                "--name",
                "Acme Corp",
                "--category",
                "consulting",
                "--tax-id",
                "12-3456789",
                "--1099",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Vendor created" in captured.out
        assert "Acme Corp" in captured.out
        assert "consulting" in captured.out
        assert "12-3456789" in captured.out
        assert "1099 Eligible" in captured.out

    def test_vendor_add_minimal(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "vendor",
                "add",
                "--name",
                "Simple Vendor",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Vendor created" in captured.out
        assert "Simple Vendor" in captured.out

    def test_vendor_stored_in_database(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        main(
            [
                "--database",
                str(db_path),
                "vendor",
                "add",
                "--name",
                "Test Vendor",
                "--category",
                "legal",
            ]
        )

        vendor_repo = SQLiteVendorRepository(db)
        vendors = list(vendor_repo.list_all())

        assert len(vendors) == 1
        assert vendors[0].name == "Test Vendor"
        assert vendors[0].category == "legal"


class TestVendorList:
    def test_vendor_list(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        vendor_repo = SQLiteVendorRepository(db)
        vendor_repo.add(Vendor(name="Vendor 1", category="legal"))
        vendor_repo.add(Vendor(name="Vendor 2", category="consulting"))

        result = main(["--database", str(db_path), "vendor", "list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "Vendor 1" in captured.out
        assert "Vendor 2" in captured.out
        assert "Total: 2" in captured.out

    def test_vendor_list_by_category(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        vendor_repo = SQLiteVendorRepository(db)
        vendor_repo.add(Vendor(name="Vendor 1", category="legal"))
        vendor_repo.add(Vendor(name="Vendor 2", category="consulting"))

        result = main(
            ["--database", str(db_path), "vendor", "list", "--category", "legal"]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Vendor 1" in captured.out
        assert "Vendor 2" not in captured.out

    def test_vendor_list_include_inactive(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        vendor_repo = SQLiteVendorRepository(db)
        active_vendor = Vendor(name="Active Vendor")
        inactive_vendor = Vendor(name="Inactive Vendor")
        inactive_vendor.deactivate()
        vendor_repo.add(active_vendor)
        vendor_repo.add(inactive_vendor)

        result = main(
            ["--database", str(db_path), "vendor", "list", "--include-inactive"]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Active Vendor" in captured.out
        assert "Inactive Vendor" in captured.out


class TestVendorGet:
    def test_vendor_get(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        vendor_repo = SQLiteVendorRepository(db)
        vendor = Vendor(name="Test Vendor", category="legal", tax_id="12-3456789")
        vendor_repo.add(vendor)

        result = main(
            ["--database", str(db_path), "vendor", "get", "--id", str(vendor.id)]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Vendor Details" in captured.out
        assert "Test Vendor" in captured.out
        assert "legal" in captured.out
        assert "12-3456789" in captured.out

    def test_vendor_get_not_found(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            ["--database", str(db_path), "vendor", "get", "--id", str(uuid4())]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Vendor not found" in captured.out

    def test_vendor_get_invalid_id(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            ["--database", str(db_path), "vendor", "get", "--id", "invalid-uuid"]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid vendor ID" in captured.out


class TestVendorUpdate:
    def test_vendor_update_name(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        vendor_repo = SQLiteVendorRepository(db)
        vendor = Vendor(name="Old Name")
        vendor_repo.add(vendor)

        result = main(
            [
                "--database",
                str(db_path),
                "vendor",
                "update",
                "--id",
                str(vendor.id),
                "--name",
                "New Name",
            ]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "updated" in captured.out

        updated = vendor_repo.get(vendor.id)
        assert updated is not None
        assert updated.name == "New Name"

    def test_vendor_update_deactivate(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        vendor_repo = SQLiteVendorRepository(db)
        vendor = Vendor(name="Test Vendor")
        vendor_repo.add(vendor)

        result = main(
            [
                "--database",
                str(db_path),
                "vendor",
                "update",
                "--id",
                str(vendor.id),
                "--deactivate",
            ]
        )

        assert result == 0

        updated = vendor_repo.get(vendor.id)
        assert updated is not None
        assert updated.is_active is False

    def test_vendor_update_not_found(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            [
                "--database",
                str(db_path),
                "vendor",
                "update",
                "--id",
                str(uuid4()),
                "--name",
                "New Name",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Vendor not found" in captured.out


class TestVendorSearch:
    def test_vendor_search(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        vendor_repo = SQLiteVendorRepository(db)
        vendor_repo.add(Vendor(name="Acme Corporation"))
        vendor_repo.add(Vendor(name="Acme LLC"))
        vendor_repo.add(Vendor(name="Other Company"))

        result = main(
            ["--database", str(db_path), "vendor", "search", "--name", "acme"]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Acme Corporation" in captured.out
        assert "Acme LLC" in captured.out
        assert "Other Company" not in captured.out
        assert "Found: 2" in captured.out

    def test_vendor_search_no_results(self, tmp_path, capsys):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(str(db_path))
        db.initialize()

        result = main(
            ["--database", str(db_path), "vendor", "search", "--name", "nonexistent"]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Found: 0" in captured.out


class TestDatabaseErrors:
    def test_expense_fails_with_nonexistent_database(self, tmp_path, capsys):
        db_path = tmp_path / "nonexistent.db"

        result = main(
            [
                "--database",
                str(db_path),
                "expense",
                "summary",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ]
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Database not found" in captured.out

    def test_vendor_fails_with_nonexistent_database(self, tmp_path, capsys):
        db_path = tmp_path / "nonexistent.db"

        result = main(["--database", str(db_path), "vendor", "list"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Database not found" in captured.out
