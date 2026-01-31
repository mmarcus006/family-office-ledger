"""LedgerService implementation for double-entry accounting operations."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from family_office_ledger.domain.transactions import (
    Entry,
    Transaction,
    UnbalancedTransactionError,
)
from family_office_ledger.domain.value_objects import Money
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityRepository,
    TransactionRepository,
)
from family_office_ledger.services.interfaces import LedgerService


class AccountNotFoundError(Exception):
    """Raised when an account cannot be found."""

    def __init__(self, account_id: UUID) -> None:
        self.account_id = account_id
        super().__init__(f"Account not found: {account_id}")


class TransactionNotFoundError(Exception):
    """Raised when a transaction cannot be found."""

    def __init__(self, txn_id: UUID) -> None:
        self.txn_id = txn_id
        super().__init__(f"Transaction not found: {txn_id}")


class LedgerServiceImpl(LedgerService):
    """Implementation of LedgerService for double-entry accounting."""

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        account_repo: AccountRepository,
        entity_repo: EntityRepository,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._account_repo = account_repo
        self._entity_repo = entity_repo

    def post_transaction(self, txn: Transaction) -> None:
        """Validate and save a transaction to the ledger.

        Args:
            txn: The transaction to post

        Raises:
            UnbalancedTransactionError: If debits don't equal credits
            AccountNotFoundError: If any account in the transaction doesn't exist
        """
        self.validate_transaction(txn)
        self._transaction_repo.add(txn)

    def validate_transaction(self, txn: Transaction) -> None:
        """Validate that a transaction is balanced and all accounts exist.

        Args:
            txn: The transaction to validate

        Raises:
            UnbalancedTransactionError: If debits don't equal credits
            AccountNotFoundError: If any account in the transaction doesn't exist
        """
        # Check all accounts exist
        for entry in txn.entries:
            account = self._account_repo.get(entry.account_id)
            if account is None:
                raise AccountNotFoundError(entry.account_id)

        # Check transaction is balanced
        if not txn.is_balanced:
            raise UnbalancedTransactionError(
                txn_id=txn.id, debits=txn.total_debits, credits=txn.total_credits
            )

    def reverse_transaction(
        self, txn_id: UUID, reversal_date: date, memo: str
    ) -> Transaction:
        """Create a reversing entry for an existing transaction.

        Creates a new transaction with debits and credits swapped,
        links it to the original via reverses_transaction_id,
        and marks the original as reversed.

        Args:
            txn_id: ID of the transaction to reverse
            reversal_date: Date for the reversal transaction
            memo: Memo for the reversal transaction

        Returns:
            The newly created reversal transaction

        Raises:
            TransactionNotFoundError: If the original transaction doesn't exist
        """
        # Get the original transaction
        original = self._transaction_repo.get(txn_id)
        if original is None:
            raise TransactionNotFoundError(txn_id)

        # Create reversal entries with swapped debits/credits
        reversal_entries: list[Entry] = []
        for orig_entry in original.entries:
            reversal_entry = Entry(
                account_id=orig_entry.account_id,
                debit_amount=orig_entry.credit_amount,
                credit_amount=orig_entry.debit_amount,
                memo=orig_entry.memo,
                tax_lot_id=orig_entry.tax_lot_id,
            )
            reversal_entries.append(reversal_entry)

        # Create the reversal transaction
        reversal = Transaction(
            transaction_date=reversal_date,
            entries=reversal_entries,
            memo=memo,
            reverses_transaction_id=txn_id,
        )

        # Save the reversal
        self._transaction_repo.add(reversal)

        # Mark original as reversed
        original.is_reversed = True
        self._transaction_repo.update(original)

        return reversal

    def get_account_balance(
        self, account_id: UUID, as_of_date: date | None = None
    ) -> Money:
        """Calculate the running balance for an account.

        Balance is calculated as sum of debits minus sum of credits
        for all entries touching the account up to the as_of_date.

        Args:
            account_id: ID of the account
            as_of_date: Optional date to calculate balance as of (inclusive).
                        If None, includes all transactions.

        Returns:
            The account balance (debits - credits)

        Raises:
            AccountNotFoundError: If the account doesn't exist
        """
        # Verify account exists
        account = self._account_repo.get(account_id)
        if account is None:
            raise AccountNotFoundError(account_id)

        # Get all transactions for this account
        transactions = self._transaction_repo.list_by_account(
            account_id, end_date=as_of_date
        )

        # Sum up debits and credits for entries in this account
        total_debits = Decimal("0")
        total_credits = Decimal("0")
        currency = "USD"

        for txn in transactions:
            for entry in txn.entries:
                if entry.account_id == account_id:
                    total_debits += entry.debit_amount.amount
                    total_credits += entry.credit_amount.amount
                    currency = (
                        entry.debit_amount.currency or entry.credit_amount.currency
                    )

        return Money(total_debits - total_credits, currency)

    def get_entity_balance(
        self, entity_id: UUID, as_of_date: date | None = None
    ) -> Money:
        """Calculate the sum of all account balances for an entity.

        Args:
            entity_id: ID of the entity
            as_of_date: Optional date to calculate balance as of (inclusive).
                        If None, includes all transactions.

        Returns:
            The sum of all account balances for the entity
        """
        # Get all accounts for this entity
        accounts = self._account_repo.list_by_entity(entity_id)

        # Sum all account balances
        total = Decimal("0")
        currency = "USD"

        for account in accounts:
            balance = self.get_account_balance(account.id, as_of_date)
            total += balance.amount
            currency = balance.currency

        return Money(total, currency)
