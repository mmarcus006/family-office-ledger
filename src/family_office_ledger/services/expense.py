from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

from family_office_ledger.domain.transactions import Transaction
from family_office_ledger.domain.value_objects import AccountType, Money
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    TransactionRepository,
    VendorRepository,
)
from family_office_ledger.services.interfaces import ExpenseService

CATEGORY_RULES: dict[str, list[str]] = {
    "legal": ["attorney", "lawyer", "legal", "law firm", "counsel"],
    "accounting": ["cpa", "accountant", "bookkeeper", "tax prep", "audit"],
    "software": ["software", "saas", "subscription", "license", "slack", "zoom"],
    "utilities": ["electric", "gas", "water", "utility", "power", "pg&e", "con ed"],
    "rent": ["rent", "lease", "landlord", "property management"],
    "payroll": ["payroll", "salary", "wages", "adp", "gusto", "paychex"],
    "travel": ["airline", "hotel", "airbnb", "uber", "lyft", "flight", "travel"],
    "meals": ["restaurant", "doordash", "grubhub", "cafe", "catering", "lunch"],
    "insurance": ["insurance", "premium", "policy", "coverage"],
    "hosting": ["hosting", "aws", "azure", "cloud", "server", "heroku"],
    "marketing": ["marketing", "advertising", "ads", "campaign", "promo"],
    "consulting": ["consultant", "consulting", "advisory", "advisor"],
    "bank_fees": ["bank fee", "wire fee", "transfer fee", "service charge"],
    "office_supplies": ["office supplies", "staples", "supplies"],
    "hardware": ["hardware", "computer", "laptop", "equipment"],
    "charitable": ["donation", "charitable", "nonprofit", "charity"],
}


class ExpenseServiceImpl(ExpenseService):
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        account_repo: AccountRepository,
        vendor_repo: VendorRepository,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._account_repo = account_repo
        self._vendor_repo = vendor_repo

    def categorize_transaction(
        self,
        transaction_id: UUID,
        category: str | None = None,
        tags: list[str] | None = None,
        vendor_id: UUID | None = None,
    ) -> Transaction:
        txn = self._transaction_repo.get(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction not found: {transaction_id}")

        if category is not None:
            txn.category = category
        if tags is not None:
            txn.tags = tags
        if vendor_id is not None:
            txn.vendor_id = vendor_id

        self._transaction_repo.update(txn)
        return txn

    def auto_categorize(self, transaction: Transaction) -> str | None:
        memo_lower = (transaction.memo or "").lower()
        reference_lower = (transaction.reference or "").lower()
        text_to_search = f"{memo_lower} {reference_lower}"

        for category, keywords in CATEGORY_RULES.items():
            for keyword in keywords:
                if keyword.lower() in text_to_search:
                    return category
        return None

    def get_expense_summary(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        expense_accounts = self._get_expense_accounts(entity_ids)
        expense_account_ids = {a.id for a in expense_accounts}

        total = Decimal("0")
        count = 0

        if entity_ids:
            for entity_id in entity_ids:
                txns = self._transaction_repo.list_by_entity(
                    entity_id, start_date, end_date
                )
                for txn in txns:
                    expense_amount = self._get_expense_amount(txn, expense_account_ids)
                    if expense_amount > Decimal("0"):
                        total += expense_amount
                        count += 1
        else:
            txns = self._transaction_repo.list_by_date_range(start_date, end_date)
            for txn in txns:
                expense_amount = self._get_expense_amount(txn, expense_account_ids)
                if expense_amount > Decimal("0"):
                    total += expense_amount
                    count += 1

        return {
            "total_expenses": total,
            "transaction_count": count,
            "date_range": {"start_date": start_date, "end_date": end_date},
        }

    def get_expenses_by_category(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Money]:
        expense_accounts = self._get_expense_accounts(entity_ids)
        expense_account_ids = {a.id for a in expense_accounts}

        by_category: dict[str, Decimal] = defaultdict(Decimal)

        transactions = self._get_transactions(entity_ids, start_date, end_date)
        for txn in transactions:
            expense_amount = self._get_expense_amount(txn, expense_account_ids)
            if expense_amount > Decimal("0"):
                cat = txn.category if txn.category else "uncategorized"
                by_category[cat] += expense_amount

        return {cat: Money(amount) for cat, amount in by_category.items()}

    def get_expenses_by_vendor(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[UUID, Money]:
        expense_accounts = self._get_expense_accounts(entity_ids)
        expense_account_ids = {a.id for a in expense_accounts}

        by_vendor: dict[UUID, Decimal] = defaultdict(Decimal)

        transactions = self._get_transactions(entity_ids, start_date, end_date)
        for txn in transactions:
            if txn.vendor_id is None:
                continue
            expense_amount = self._get_expense_amount(txn, expense_account_ids)
            if expense_amount > Decimal("0"):
                by_vendor[txn.vendor_id] += expense_amount

        return {vid: Money(amount) for vid, amount in by_vendor.items()}

    def detect_recurring_expenses(
        self,
        entity_id: UUID,
        lookback_months: int = 3,
    ) -> list[dict[str, Any]]:
        end_date = date.today()
        start_date = end_date - relativedelta(months=lookback_months)

        expense_accounts = self._get_expense_accounts([entity_id])
        expense_account_ids = {a.id for a in expense_accounts}

        transactions = list(
            self._transaction_repo.list_by_entity(entity_id, start_date, end_date)
        )

        vendor_transactions: dict[UUID, list[tuple[date, Decimal]]] = defaultdict(list)
        for txn in transactions:
            if txn.vendor_id is None:
                continue
            expense_amount = self._get_expense_amount(txn, expense_account_ids)
            if expense_amount > Decimal("0"):
                vendor_transactions[txn.vendor_id].append(
                    (txn.transaction_date, expense_amount)
                )

        recurring: list[dict[str, Any]] = []
        for vendor_id, txn_list in vendor_transactions.items():
            if len(txn_list) < 2:
                continue

            txn_list.sort(key=lambda x: x[0])
            dates = [t[0] for t in txn_list]
            amounts = [t[1] for t in txn_list]

            frequency = self._detect_frequency(dates)
            if frequency:
                total_amount = sum(amounts, Decimal("0"))
                avg_amount = total_amount / Decimal(len(amounts))
                recurring.append(
                    {
                        "vendor_id": vendor_id,
                        "frequency": frequency,
                        "amount": Money(avg_amount),
                        "occurrence_count": len(txn_list),
                        "last_date": dates[-1],
                    }
                )

        return recurring

    def _get_expense_accounts(self, entity_ids: list[UUID] | None) -> list[Any]:
        accounts = []
        if entity_ids:
            for entity_id in entity_ids:
                for acc in self._account_repo.list_by_entity(entity_id):
                    if acc.account_type == AccountType.EXPENSE:
                        accounts.append(acc)
        return accounts

    def _get_transactions(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> list[Transaction]:
        transactions: list[Transaction] = []
        if entity_ids:
            for entity_id in entity_ids:
                txns = self._transaction_repo.list_by_entity(
                    entity_id, start_date, end_date
                )
                transactions.extend(txns)
        else:
            transactions = list(
                self._transaction_repo.list_by_date_range(start_date, end_date)
            )
        return transactions

    def _get_expense_amount(
        self, txn: Transaction, expense_account_ids: set[UUID]
    ) -> Decimal:
        total = Decimal("0")
        for entry in txn.entries:
            if entry.account_id in expense_account_ids:
                total += entry.debit_amount.amount
        return total

    def _detect_frequency(self, dates: list[date]) -> str | None:
        if len(dates) < 2:
            return None

        intervals = []
        for i in range(1, len(dates)):
            intervals.append((dates[i] - dates[i - 1]).days)

        avg_interval = sum(intervals) / len(intervals)

        if 25 <= avg_interval <= 35:
            return "monthly"
        elif 12 <= avg_interval <= 16:
            return "bi-weekly"
        elif 5 <= avg_interval <= 9:
            return "weekly"
        elif 85 <= avg_interval <= 95:
            return "quarterly"
        elif 360 <= avg_interval <= 370:
            return "annual"

        return None
