"""Tests for LedgerService implementation."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from family_office_ledger.domain.entities import Account, Entity
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
    SQLiteTransactionRepository,
)
from family_office_ledger.services.ledger import (
    AccountNotFoundError,
    LedgerServiceImpl,
    TransactionNotFoundError,
    UnbalancedTransactionError,
)


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
def test_entity(entity_repo: SQLiteEntityRepository) -> Entity:
    """Create and persist a test entity."""
    entity = Entity(name="Test Family Trust", entity_type=EntityType.TRUST)
    entity_repo.add(entity)
    return entity


@pytest.fixture
def test_accounts(
    account_repo: SQLiteAccountRepository, test_entity: Entity
) -> dict[str, Account]:
    """Create and persist test accounts."""
    cash = Account(
        name="Cash",
        entity_id=test_entity.id,
        account_type=AccountType.ASSET,
        sub_type=AccountSubType.CHECKING,
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
    account_repo.add(cash)
    account_repo.add(income)
    account_repo.add(expense)
    return {"cash": cash, "income": income, "expense": expense, "entity": test_entity}


@pytest.fixture
def ledger_service(
    transaction_repo: SQLiteTransactionRepository,
    account_repo: SQLiteAccountRepository,
    entity_repo: SQLiteEntityRepository,
) -> LedgerServiceImpl:
    """Create ledger service with real SQLite repositories."""
    return LedgerServiceImpl(
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        entity_repo=entity_repo,
    )


# ===== validate_transaction Tests =====


class TestValidateTransaction:
    def test_validate_balanced_transaction_passes(
        self, ledger_service: LedgerServiceImpl, test_accounts: dict[str, Account]
    ):
        """A balanced transaction with valid accounts should pass validation."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Valid transaction",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )

        # Should not raise
        ledger_service.validate_transaction(txn)

    def test_validate_unbalanced_transaction_raises(
        self, ledger_service: LedgerServiceImpl, test_accounts: dict[str, Account]
    ):
        """An unbalanced transaction should raise UnbalancedTransactionError."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Unbalanced",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("50.00")),  # Doesn't match debit
            )
        )

        with pytest.raises(UnbalancedTransactionError):
            ledger_service.validate_transaction(txn)

    def test_validate_transaction_with_nonexistent_account_raises(
        self, ledger_service: LedgerServiceImpl, test_accounts: dict[str, Account]
    ):
        """A transaction referencing a non-existent account should raise AccountNotFoundError."""
        nonexistent_account_id = uuid4()
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Invalid account",
        )
        txn.add_entry(
            Entry(
                account_id=nonexistent_account_id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )

        with pytest.raises(AccountNotFoundError):
            ledger_service.validate_transaction(txn)

    def test_validate_transaction_with_multiple_valid_entries(
        self, ledger_service: LedgerServiceImpl, test_accounts: dict[str, Account]
    ):
        """A transaction with multiple entries that balances should pass."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Multi-entry transaction",
        )
        # Split a payment across multiple expense accounts
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("60.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                debit_amount=Money(Decimal("40.00")),
            )
        )

        # Should not raise
        ledger_service.validate_transaction(txn)


# ===== post_transaction Tests =====


class TestPostTransaction:
    def test_post_valid_transaction_saves_to_repo(
        self,
        ledger_service: LedgerServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ):
        """A valid transaction should be saved to the repository."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Test deposit",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )

        ledger_service.post_transaction(txn)

        retrieved = transaction_repo.get(txn.id)
        assert retrieved is not None
        assert retrieved.memo == "Test deposit"
        assert len(retrieved.entries) == 2

    def test_post_unbalanced_transaction_raises_and_does_not_save(
        self,
        ledger_service: LedgerServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ):
        """An unbalanced transaction should not be saved."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Unbalanced",
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        # Intentionally unbalanced - no credit entry

        with pytest.raises(UnbalancedTransactionError):
            ledger_service.post_transaction(txn)

        # Verify not saved
        assert transaction_repo.get(txn.id) is None

    def test_post_transaction_with_invalid_account_raises(
        self,
        ledger_service: LedgerServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ):
        """A transaction with invalid account should not be saved."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Invalid account",
        )
        txn.add_entry(
            Entry(
                account_id=uuid4(),  # Non-existent
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )

        with pytest.raises(AccountNotFoundError):
            ledger_service.post_transaction(txn)

        # Verify not saved
        assert transaction_repo.get(txn.id) is None


# ===== reverse_transaction Tests =====


class TestReverseTransaction:
    def test_reverse_transaction_creates_reversing_entry(
        self,
        ledger_service: LedgerServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ):
        """Reversing a transaction should create a new transaction with swapped debits/credits."""
        # First post a transaction
        original = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Original payment",
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("250.00")),
            )
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("250.00")),
            )
        )
        ledger_service.post_transaction(original)

        # Reverse it
        reversal = ledger_service.reverse_transaction(
            txn_id=original.id,
            reversal_date=date(2024, 1, 20),
            memo="Reversal of payment",
        )

        # Verify reversal structure
        assert reversal.transaction_date == date(2024, 1, 20)
        assert reversal.memo == "Reversal of payment"
        assert reversal.reverses_transaction_id == original.id
        assert reversal.is_balanced

        # Check that debits and credits are swapped
        reversal_entries_by_account = {e.account_id: e for e in reversal.entries}
        cash_entry = reversal_entries_by_account[test_accounts["cash"].id]
        income_entry = reversal_entries_by_account[test_accounts["income"].id]

        # Original: cash debit 250, income credit 250
        # Reversal: cash credit 250, income debit 250
        assert cash_entry.credit_amount == Money(Decimal("250.00"))
        assert cash_entry.debit_amount == Money.zero()
        assert income_entry.debit_amount == Money(Decimal("250.00"))
        assert income_entry.credit_amount == Money.zero()

    def test_reverse_transaction_marks_original_as_reversed(
        self,
        ledger_service: LedgerServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ):
        """Reversing a transaction should mark the original as reversed."""
        original = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="To be reversed",
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        ledger_service.post_transaction(original)

        ledger_service.reverse_transaction(
            txn_id=original.id,
            reversal_date=date(2024, 1, 25),
            memo="Reversal",
        )

        # Reload original from repository
        updated_original = transaction_repo.get(original.id)
        assert updated_original is not None
        assert updated_original.is_reversed is True

    def test_reverse_transaction_saves_reversal_to_repo(
        self,
        ledger_service: LedgerServiceImpl,
        transaction_repo: SQLiteTransactionRepository,
        test_accounts: dict[str, Account],
    ):
        """The reversal transaction should be persisted."""
        original = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Original",
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        ledger_service.post_transaction(original)

        reversal = ledger_service.reverse_transaction(
            txn_id=original.id,
            reversal_date=date(2024, 1, 25),
            memo="Reversal",
        )

        # Verify reversal is saved
        retrieved = transaction_repo.get(reversal.id)
        assert retrieved is not None
        assert retrieved.reverses_transaction_id == original.id

        # Verify we can find it via get_reversals
        reversals = list(transaction_repo.get_reversals(original.id))
        assert len(reversals) == 1
        assert reversals[0].id == reversal.id

    def test_reverse_nonexistent_transaction_raises(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Trying to reverse a non-existent transaction should raise."""
        with pytest.raises(TransactionNotFoundError):
            ledger_service.reverse_transaction(
                txn_id=uuid4(),
                reversal_date=date(2024, 1, 25),
                memo="Reversal",
            )

    def test_reverse_transaction_preserves_entry_memos(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Entry memos should be preserved in the reversal."""
        original = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Original",
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
                memo="Cash deposit memo",
            )
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
                memo="Income memo",
            )
        )
        ledger_service.post_transaction(original)

        reversal = ledger_service.reverse_transaction(
            txn_id=original.id,
            reversal_date=date(2024, 1, 25),
            memo="Reversal",
        )

        reversal_entries_by_account = {e.account_id: e for e in reversal.entries}
        assert (
            reversal_entries_by_account[test_accounts["cash"].id].memo
            == "Cash deposit memo"
        )
        assert (
            reversal_entries_by_account[test_accounts["income"].id].memo
            == "Income memo"
        )


# ===== get_account_balance Tests =====


class TestGetAccountBalance:
    def test_get_account_balance_single_transaction(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Balance should reflect debits - credits for a single transaction."""
        txn = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Deposit",
        )
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
        ledger_service.post_transaction(txn)

        # Cash account: debit 1000 = positive 1000
        cash_balance = ledger_service.get_account_balance(test_accounts["cash"].id)
        assert cash_balance == Money(Decimal("1000.00"))

        # Income account: credit 1000 = negative 1000 (debit - credit)
        income_balance = ledger_service.get_account_balance(test_accounts["income"].id)
        assert income_balance == Money(Decimal("-1000.00"))

    def test_get_account_balance_multiple_transactions(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Balance should be sum of all debits minus all credits."""
        # First deposit
        txn1 = Transaction(transaction_date=date(2024, 1, 10))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        ledger_service.post_transaction(txn1)

        # Second deposit
        txn2 = Transaction(transaction_date=date(2024, 1, 15))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("300.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("300.00")),
            )
        )
        ledger_service.post_transaction(txn2)

        # Payment (expense)
        txn3 = Transaction(transaction_date=date(2024, 1, 20))
        txn3.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn3.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        ledger_service.post_transaction(txn3)

        # Cash: 500 + 300 - 200 = 600
        balance = ledger_service.get_account_balance(test_accounts["cash"].id)
        assert balance == Money(Decimal("600.00"))

    def test_get_account_balance_with_as_of_date(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Balance should only include transactions up to as_of_date."""
        # Transaction on Jan 10
        txn1 = Transaction(transaction_date=date(2024, 1, 10))
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        ledger_service.post_transaction(txn1)

        # Transaction on Jan 20
        txn2 = Transaction(transaction_date=date(2024, 1, 20))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("300.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("300.00")),
            )
        )
        ledger_service.post_transaction(txn2)

        # Transaction on Feb 5
        txn3 = Transaction(transaction_date=date(2024, 2, 5))
        txn3.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        txn3.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        ledger_service.post_transaction(txn3)

        # Balance as of Jan 15 should only include txn1
        balance_jan15 = ledger_service.get_account_balance(
            test_accounts["cash"].id, as_of_date=date(2024, 1, 15)
        )
        assert balance_jan15 == Money(Decimal("500.00"))

        # Balance as of Jan 31 should include txn1 and txn2
        balance_jan31 = ledger_service.get_account_balance(
            test_accounts["cash"].id, as_of_date=date(2024, 1, 31)
        )
        assert balance_jan31 == Money(Decimal("800.00"))

        # Balance with no as_of_date should include all
        balance_all = ledger_service.get_account_balance(test_accounts["cash"].id)
        assert balance_all == Money(Decimal("1800.00"))

    def test_get_account_balance_no_transactions(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """An account with no transactions should have zero balance."""
        balance = ledger_service.get_account_balance(test_accounts["cash"].id)
        assert balance == Money.zero()

    def test_get_account_balance_nonexistent_account(
        self,
        ledger_service: LedgerServiceImpl,
    ):
        """Getting balance for non-existent account should raise."""
        with pytest.raises(AccountNotFoundError):
            ledger_service.get_account_balance(uuid4())


# ===== get_entity_balance Tests =====


class TestGetEntityBalance:
    def test_get_entity_balance_sums_all_accounts(
        self,
        ledger_service: LedgerServiceImpl,
        account_repo: SQLiteAccountRepository,
        test_accounts: dict[str, Account],
    ):
        """Entity balance should sum all account balances."""
        entity = test_accounts["entity"]

        # Deposit to cash
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
        ledger_service.post_transaction(txn1)

        # Expense from cash
        txn2 = Transaction(transaction_date=date(2024, 1, 20))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("300.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("300.00")),
            )
        )
        ledger_service.post_transaction(txn2)

        # Entity balance should sum: cash(700) + income(-1000) + expense(300) = 0
        # (Double-entry accounting: debits always equal credits)
        entity_balance = ledger_service.get_entity_balance(entity.id)
        assert entity_balance == Money.zero()

    def test_get_entity_balance_with_as_of_date(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Entity balance should respect as_of_date."""
        entity = test_accounts["entity"]

        # Transaction on Jan 10
        txn1 = Transaction(transaction_date=date(2024, 1, 10))
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
        ledger_service.post_transaction(txn1)

        # Transaction on Feb 10
        txn2 = Transaction(transaction_date=date(2024, 2, 10))
        txn2.add_entry(
            Entry(
                account_id=test_accounts["expense"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        ledger_service.post_transaction(txn2)

        # As of Jan 31 - only first transaction
        balance_jan = ledger_service.get_entity_balance(
            entity.id, as_of_date=date(2024, 1, 31)
        )
        # cash(1000) + income(-1000) = 0
        assert balance_jan == Money.zero()

        # As of Feb 28 - both transactions
        balance_feb = ledger_service.get_entity_balance(
            entity.id, as_of_date=date(2024, 2, 28)
        )
        # cash(500) + income(-1000) + expense(500) = 0
        assert balance_feb == Money.zero()

    def test_get_entity_balance_no_accounts(
        self,
        ledger_service: LedgerServiceImpl,
        entity_repo: SQLiteEntityRepository,
    ):
        """Entity with no accounts should have zero balance."""
        # Create entity with no accounts
        empty_entity = Entity(name="Empty Entity", entity_type=EntityType.LLC)
        entity_repo.add(empty_entity)

        balance = ledger_service.get_entity_balance(empty_entity.id)
        assert balance == Money.zero()

    def test_get_entity_balance_isolates_by_entity(
        self,
        ledger_service: LedgerServiceImpl,
        entity_repo: SQLiteEntityRepository,
        account_repo: SQLiteAccountRepository,
        test_accounts: dict[str, Account],
    ):
        """Entity balance should only include accounts belonging to that entity."""
        # Create second entity with account
        entity2 = Entity(name="Other Entity", entity_type=EntityType.LLC)
        entity_repo.add(entity2)

        other_cash = Account(
            name="Other Cash",
            entity_id=entity2.id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CHECKING,
        )
        other_income = Account(
            name="Other Income",
            entity_id=entity2.id,
            account_type=AccountType.INCOME,
        )
        account_repo.add(other_cash)
        account_repo.add(other_income)

        # Transaction in original entity
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
        ledger_service.post_transaction(txn1)

        # Transaction in second entity
        txn2 = Transaction(transaction_date=date(2024, 1, 15))
        txn2.add_entry(
            Entry(
                account_id=other_cash.id,
                debit_amount=Money(Decimal("5000.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=other_income.id,
                credit_amount=Money(Decimal("5000.00")),
            )
        )
        ledger_service.post_transaction(txn2)

        # Original entity balance should not include entity2's transactions
        entity1_balance = ledger_service.get_entity_balance(test_accounts["entity"].id)
        # cash(1000) + income(-1000) = 0
        assert entity1_balance == Money.zero()

        # Entity2 balance
        entity2_balance = ledger_service.get_entity_balance(entity2.id)
        # other_cash(5000) + other_income(-5000) = 0
        assert entity2_balance == Money.zero()


# ===== Integration Tests =====


class TestLedgerServiceIntegration:
    def test_post_then_reverse_then_check_balance(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """A complete workflow: post, reverse, and verify balance reflects reversal."""
        # Post original transaction
        original = Transaction(
            transaction_date=date(2024, 1, 15),
            memo="Payment received",
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("1000.00")),
            )
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("1000.00")),
            )
        )
        ledger_service.post_transaction(original)

        # Check balance after posting
        balance_after_post = ledger_service.get_account_balance(
            test_accounts["cash"].id
        )
        assert balance_after_post == Money(Decimal("1000.00"))

        # Reverse the transaction
        ledger_service.reverse_transaction(
            txn_id=original.id,
            reversal_date=date(2024, 1, 20),
            memo="Reversal",
        )

        # Balance after reversal should be zero
        balance_after_reversal = ledger_service.get_account_balance(
            test_accounts["cash"].id
        )
        assert balance_after_reversal == Money.zero()

    def test_multiple_transactions_and_reversals(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Test complex scenario with multiple transactions and selective reversal."""
        # Post three transactions
        txn1 = Transaction(transaction_date=date(2024, 1, 10), memo="Deposit 1")
        txn1.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("100.00")),
            )
        )
        txn1.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("100.00")),
            )
        )
        ledger_service.post_transaction(txn1)

        txn2 = Transaction(transaction_date=date(2024, 1, 15), memo="Deposit 2")
        txn2.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("200.00")),
            )
        )
        txn2.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("200.00")),
            )
        )
        ledger_service.post_transaction(txn2)

        txn3 = Transaction(transaction_date=date(2024, 1, 20), memo="Deposit 3")
        txn3.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("300.00")),
            )
        )
        txn3.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("300.00")),
            )
        )
        ledger_service.post_transaction(txn3)

        # Balance: 100 + 200 + 300 = 600
        assert ledger_service.get_account_balance(test_accounts["cash"].id) == Money(
            Decimal("600.00")
        )

        # Reverse only the second transaction
        ledger_service.reverse_transaction(
            txn2.id, date(2024, 1, 25), "Reverse Deposit 2"
        )

        # Balance: 600 - 200 = 400
        assert ledger_service.get_account_balance(test_accounts["cash"].id) == Money(
            Decimal("400.00")
        )

    def test_balance_as_of_date_excludes_reversals_after_date(
        self,
        ledger_service: LedgerServiceImpl,
        test_accounts: dict[str, Account],
    ):
        """Balance as of date should exclude reversal entries that occurred after the date."""
        # Post transaction on Jan 10
        original = Transaction(transaction_date=date(2024, 1, 10))
        original.add_entry(
            Entry(
                account_id=test_accounts["cash"].id,
                debit_amount=Money(Decimal("500.00")),
            )
        )
        original.add_entry(
            Entry(
                account_id=test_accounts["income"].id,
                credit_amount=Money(Decimal("500.00")),
            )
        )
        ledger_service.post_transaction(original)

        # Reverse on Jan 20
        ledger_service.reverse_transaction(original.id, date(2024, 1, 20), "Reversal")

        # Balance as of Jan 15 (before reversal) should still show 500
        balance_jan15 = ledger_service.get_account_balance(
            test_accounts["cash"].id, as_of_date=date(2024, 1, 15)
        )
        assert balance_jan15 == Money(Decimal("500.00"))

        # Balance as of Jan 25 (after reversal) should be 0
        balance_jan25 = ledger_service.get_account_balance(
            test_accounts["cash"].id, as_of_date=date(2024, 1, 25)
        )
        assert balance_jan25 == Money.zero()
