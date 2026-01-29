"""Tests for ExpenseService implementation."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from dateutil.relativedelta import relativedelta

import pytest

from family_office_ledger.domain.entities import Account, Entity
from family_office_ledger.domain.transactions import Entry, Transaction
from family_office_ledger.domain.vendors import Vendor
from family_office_ledger.domain.value_objects import (
    AccountSubType,
    AccountType,
    EntityType,
    ExpenseCategory,
    Money,
)
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityRepository,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)
from family_office_ledger.services.expense import ExpenseServiceImpl


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
def vendor_repo(db: SQLiteDatabase) -> SQLiteVendorRepository:
    return SQLiteVendorRepository(db)


@pytest.fixture
def expense_service(
    transaction_repo: SQLiteTransactionRepository,
    account_repo: SQLiteAccountRepository,
    vendor_repo: SQLiteVendorRepository,
) -> ExpenseServiceImpl:
    """Create ExpenseService with all repositories."""
    return ExpenseServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        vendor_repo=vendor_repo,
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


@pytest.fixture
def test_vendor(vendor_repo: SQLiteVendorRepository) -> Vendor:
    """Create and persist a test vendor."""
    vendor = Vendor(
        name="Acme Legal Services",
        category=ExpenseCategory.LEGAL.value,
        is_1099_eligible=True,
    )
    vendor_repo.add(vendor)
    return vendor


@pytest.fixture
def test_vendor_2(vendor_repo: SQLiteVendorRepository) -> Vendor:
    """Create and persist a second test vendor."""
    vendor = Vendor(
        name="CloudSoft Inc",
        category=ExpenseCategory.SOFTWARE.value,
    )
    vendor_repo.add(vendor)
    return vendor


# ===== categorize_transaction Tests =====


class TestCategorizeTransaction:
    def test_categorize_transaction_basic(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_vendor: Vendor,
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should assign category, tags, and vendor to a transaction."""
        # Create expense transaction
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Legal consultation",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["legal"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        transaction_repo.add(txn)

        updated = expense_service.categorize_transaction(
            transaction_id=txn.id,
            category=ExpenseCategory.LEGAL.value,
            tags=["professional", "recurring"],
            vendor_id=test_vendor.id,
        )

        assert updated.category == ExpenseCategory.LEGAL.value
        assert "professional" in updated.tags
        assert "recurring" in updated.tags
        assert updated.vendor_id == test_vendor.id

    def test_categorize_transaction_partial_update(
        self,
        expense_service: ExpenseServiceImpl,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should only update provided fields."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Office supplies",
            category="other",
            tags=["existing"],
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(txn)

        # Only update category
        updated = expense_service.categorize_transaction(
            transaction_id=txn.id,
            category=ExpenseCategory.OFFICE_SUPPLIES.value,
        )

        assert updated.category == ExpenseCategory.OFFICE_SUPPLIES.value
        assert "existing" in updated.tags  # Tags unchanged
        assert updated.vendor_id is None  # Vendor unchanged

    def test_categorize_transaction_not_found(
        self,
        expense_service: ExpenseServiceImpl,
    ):
        """Should raise error for non-existent transaction."""
        with pytest.raises(ValueError, match="Transaction not found"):
            expense_service.categorize_transaction(
                transaction_id=uuid4(),
                category=ExpenseCategory.LEGAL.value,
            )


# ===== auto_categorize Tests =====


class TestAutoCategorize:
    def test_auto_categorize_legal_keywords(
        self,
        expense_service: ExpenseServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Should detect legal category from keywords."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Payment to Smith & Associates Law Firm",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )

        category = expense_service.auto_categorize(txn)
        assert category == ExpenseCategory.LEGAL.value

    def test_auto_categorize_software_keywords(
        self,
        expense_service: ExpenseServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Should detect software category from keywords."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Monthly SaaS subscription - Slack",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("50.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("50.00")),
            )
        )

        category = expense_service.auto_categorize(txn)
        assert category == ExpenseCategory.SOFTWARE.value

    def test_auto_categorize_utilities_keywords(
        self,
        expense_service: ExpenseServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Should detect utilities category from keywords."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Electric bill payment - PG&E",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )

        category = expense_service.auto_categorize(txn)
        assert category == ExpenseCategory.UTILITIES.value

    def test_auto_categorize_no_match(
        self,
        expense_service: ExpenseServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Should return None when no keywords match."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Random payment XYZ123",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("75.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("75.00")),
            )
        )

        category = expense_service.auto_categorize(txn)
        assert category is None

    def test_auto_categorize_case_insensitive(
        self,
        expense_service: ExpenseServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Should match keywords regardless of case."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="LAWYER RETAINER FEE",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("2000.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("2000.00")),
            )
        )

        category = expense_service.auto_categorize(txn)
        assert category == ExpenseCategory.LEGAL.value


# ===== get_expense_summary Tests =====


class TestGetExpenseSummary:
    def test_get_expense_summary_basic(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should return total expenses for period."""
        # Create expense transactions
        txn1 = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Legal fees",
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["legal"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn1)

        txn2 = Transaction(
            transaction_date=date(2024, 1, 20),
            memo="Software subscription",
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["software"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        transaction_repo.add(txn2)

        summary = expense_service.get_expense_summary(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert summary["total_expenses"] == Decimal("1500.00")
        assert summary["transaction_count"] == 2
        assert "date_range" in summary

    def test_get_expense_summary_date_filter(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should filter by date range."""
        # January expense
        txn1 = Transaction(transaction_date=date(2024, 1, 15))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        transaction_repo.add(txn1)

        # February expense
        txn2 = Transaction(transaction_date=date(2024, 2, 15))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        transaction_repo.add(txn2)

        # Get January only
        summary = expense_service.get_expense_summary(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert summary["total_expenses"] == Decimal("100.00")

    def test_get_expense_summary_no_expenses(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
    ):
        """Should return zeros when no expenses."""
        summary = expense_service.get_expense_summary(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert summary["total_expenses"] == Decimal("0")
        assert summary["transaction_count"] == 0


# ===== get_expenses_by_category Tests =====


class TestGetExpensesByCategory:
    def test_get_expenses_by_category_basic(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should group expenses by category."""
        # Legal expense
        txn1 = Transaction(
            transaction_date=date(2024, 1, 15),
            category=ExpenseCategory.LEGAL.value,
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["legal"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn1)

        # Software expenses (two transactions)
        txn2 = Transaction(
            transaction_date=date(2024, 1, 20),
            category=ExpenseCategory.SOFTWARE.value,
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["software"].id,
                debit_amount=Money(Decimal("300.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("300.00")),
            )
        )
        transaction_repo.add(txn2)

        txn3 = Transaction(
            transaction_date=date(2024, 1, 25),
            category=ExpenseCategory.SOFTWARE.value,
        )
        txn3.add_entry(
            Entry(
                account_id=test_accounts["software"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn3.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        transaction_repo.add(txn3)

        by_category = expense_service.get_expenses_by_category(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert ExpenseCategory.LEGAL.value in by_category
        assert by_category[ExpenseCategory.LEGAL.value] == Money(Decimal("1000.00"))
        assert ExpenseCategory.SOFTWARE.value in by_category
        assert by_category[ExpenseCategory.SOFTWARE.value] == Money(Decimal("500.00"))

    def test_get_expenses_by_category_no_category(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should group uncategorized expenses."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            category=None,
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("150.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("150.00")),
            )
        )
        transaction_repo.add(txn)

        by_category = expense_service.get_expenses_by_category(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert "uncategorized" in by_category
        assert by_category["uncategorized"] == Money(Decimal("150.00"))


# ===== get_expenses_by_vendor Tests =====


class TestGetExpensesByVendor:
    def test_get_expenses_by_vendor_basic(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_vendor: Vendor,
        test_vendor_2: Vendor,
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should group expenses by vendor."""
        # Vendor 1 expenses
        txn1 = Transaction(
            transaction_date=date(2024, 1, 15),
            vendor_id=test_vendor.id,
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["legal"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        transaction_repo.add(txn1)

        # Vendor 2 expenses
        txn2 = Transaction(
            transaction_date=date(2024, 1, 20),
            vendor_id=test_vendor_2.id,
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["software"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        transaction_repo.add(txn2)

        by_vendor = expense_service.get_expenses_by_vendor(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert test_vendor.id in by_vendor
        assert by_vendor[test_vendor.id] == Money(Decimal("1000.00"))
        assert test_vendor_2.id in by_vendor
        assert by_vendor[test_vendor_2.id] == Money(Decimal("500.00"))

    def test_get_expenses_by_vendor_no_vendor(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should include expenses without vendor."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            vendor_id=None,
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("75.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("75.00")),
            )
        )
        transaction_repo.add(txn)

        by_vendor = expense_service.get_expenses_by_vendor(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # No vendor should not appear in results (only vendor-linked expenses)
        assert len(by_vendor) == 0


# ===== detect_recurring_expenses Tests =====


class TestDetectRecurringExpenses:
    def test_detect_recurring_expenses_monthly(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_vendor: Vendor,
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should detect monthly recurring expenses."""
        today = date.today()
        for months_ago in [2, 1, 0]:
            txn_date = today - relativedelta(months=months_ago)
            txn = Transaction(
                transaction_date=txn_date,
                memo="Monthly retainer",
                vendor_id=test_vendor.id,
            )
            txn.add_entry(
                Entry(
                    account_id=test_accounts["legal"].id,
                    debit_amount=Money(Decimal("500.00")),
                )
            )
            txn.add_entry(
                Entry(
                    account_id=test_accounts["cash"].id,
                    credit_amount=Money(Decimal("500.00")),
                )
            )
            transaction_repo.add(txn)

        recurring = expense_service.detect_recurring_expenses(
            entity_id=test_entity.id,
            lookback_months=3,
        )

        assert len(recurring) >= 1
        found = False
        for pattern in recurring:
            if pattern["vendor_id"] == test_vendor.id:
                found = True
                assert pattern["frequency"] == "monthly"
                assert pattern["amount"] == Money(Decimal("500.00"))
                assert pattern["occurrence_count"] == 3
        assert found, "Expected recurring pattern not detected"

    def test_detect_recurring_expenses_no_pattern(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should return empty when no recurring pattern."""
        today = date.today()
        txn = Transaction(
            transaction_date=today - relativedelta(months=1),
            memo="One-time purchase",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("999.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("999.00")),
            )
        )
        transaction_repo.add(txn)

        recurring = expense_service.detect_recurring_expenses(
            entity_id=test_entity.id,
            lookback_months=3,
        )

        for pattern in recurring:
            assert pattern["occurrence_count"] >= 2

    def test_detect_recurring_expenses_varying_amounts(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_vendor_2: Vendor,
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Should detect recurring expenses with similar amounts."""
        today = date.today()
        amounts = [Decimal("150.00"), Decimal("155.00"), Decimal("148.00")]
        for months_ago, amount in zip([2, 1, 0], amounts):
            txn_date = today - relativedelta(months=months_ago)
            txn = Transaction(
                transaction_date=txn_date,
                vendor_id=test_vendor_2.id,
            )
            txn.add_entry(
                Entry(
                    account_id=test_accounts["software"].id,
                    debit_amount=Money(amount),
                )
            )
            txn.add_entry(
                Entry(
                    account_id=test_accounts["cash"].id,
                    credit_amount=Money(amount),
                )
            )
            transaction_repo.add(txn)

        recurring = expense_service.detect_recurring_expenses(
            entity_id=test_entity.id,
            lookback_months=3,
        )

        found = False
        for pattern in recurring:
            if pattern["vendor_id"] == test_vendor_2.id:
                found = True
                assert pattern["occurrence_count"] == 3
        assert found, "Expected recurring pattern with varying amounts not detected"


# ===== Integration Tests =====


class TestExpenseServiceIntegration:
    def test_full_expense_workflow(
        self,
        expense_service: ExpenseServiceImpl,
        test_entity: Entity,
        test_accounts: dict[str, Account],
        test_vendor: Vendor,
        test_vendor_2: Vendor,
        transaction_repo: SQLiteTransactionRepository,
    ):
        """Test complete workflow: create, categorize, and report expenses."""
        # Create uncategorized expense
        txn1 = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Payment to Attorney John Smith",
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["legal"].id,
                debit_amount=Money(Decimal("2500.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("2500.00")),
            )
        )
        transaction_repo.add(txn1)

        # Auto-categorize
        suggested = expense_service.auto_categorize(txn1)
        assert suggested == ExpenseCategory.LEGAL.value

        # Apply categorization with vendor
        expense_service.categorize_transaction(
            transaction_id=txn1.id,
            category=suggested,
            tags=["professional-fees"],
            vendor_id=test_vendor.id,
        )

        # Create another expense
        txn2 = Transaction(
            transaction_date=date(2024, 1, 20),
            memo="Cloud hosting - AWS",
            category=ExpenseCategory.HOSTING.value,
            vendor_id=test_vendor_2.id,
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["software"].id,
                debit_amount=Money(Decimal("350.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("350.00")),
            )
        )
        transaction_repo.add(txn2)

        # Get summary
        summary = expense_service.get_expense_summary(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert summary["total_expenses"] == Decimal("2850.00")

        # Get by category
        by_cat = expense_service.get_expenses_by_category(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert ExpenseCategory.LEGAL.value in by_cat
        assert ExpenseCategory.HOSTING.value in by_cat

        # Get by vendor
        by_vendor = expense_service.get_expenses_by_vendor(
            entity_ids=[test_entity.id],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert test_vendor.id in by_vendor
        assert test_vendor_2.id in by_vendor
