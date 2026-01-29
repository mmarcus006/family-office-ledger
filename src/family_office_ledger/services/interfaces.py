from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from family_office_ledger.domain.exchange_rates import ExchangeRate
from family_office_ledger.domain.transactions import TaxLot, Transaction
from family_office_ledger.domain.value_objects import LotSelection, Money, Quantity

if TYPE_CHECKING:
    from family_office_ledger.domain.budgets import (
        Budget,
        BudgetLineItem,
        BudgetVariance,
    )


@dataclass
class LotDisposition:
    lot_id: UUID
    quantity_sold: Quantity
    cost_basis: Money
    proceeds: Money
    acquisition_date: date
    disposition_date: date

    @property
    def realized_gain(self) -> Money:
        return self.proceeds - self.cost_basis

    @property
    def is_long_term(self) -> bool:
        return (self.disposition_date - self.acquisition_date).days > 365


@dataclass
class MatchResult:
    imported_id: str
    ledger_transaction_id: UUID | None
    confidence_score: int
    matched: bool
    reason: str


@dataclass
class ReconciliationSummary:
    total_imported: int
    matched_count: int
    unmatched_count: int
    duplicate_count: int
    exceptions: list[str]

    @property
    def match_rate(self) -> float:
        if self.total_imported == 0:
            return 0.0
        return self.matched_count / self.total_imported


class LedgerService(ABC):
    @abstractmethod
    def post_transaction(self, txn: Transaction) -> None:
        pass

    @abstractmethod
    def validate_transaction(self, txn: Transaction) -> None:
        pass

    @abstractmethod
    def reverse_transaction(
        self, txn_id: UUID, reversal_date: date, memo: str
    ) -> Transaction:
        pass

    @abstractmethod
    def get_account_balance(
        self, account_id: UUID, as_of_date: date | None = None
    ) -> Money:
        pass

    @abstractmethod
    def get_entity_balance(
        self, entity_id: UUID, as_of_date: date | None = None
    ) -> Money:
        pass


class LotMatchingService(ABC):
    @abstractmethod
    def match_sale(
        self,
        position_id: UUID,
        quantity: Quantity,
        method: LotSelection,
        specific_lot_ids: list[UUID] | None = None,
    ) -> list[TaxLot]:
        pass

    @abstractmethod
    def execute_sale(
        self,
        position_id: UUID,
        quantity: Quantity,
        proceeds: Money,
        sale_date: date,
        method: LotSelection,
        specific_lot_ids: list[UUID] | None = None,
    ) -> list[LotDisposition]:
        pass

    @abstractmethod
    def detect_wash_sales(
        self,
        position_id: UUID,
        sale_date: date,
        loss_amount: Money,
    ) -> list[TaxLot]:
        pass

    @abstractmethod
    def get_open_lots(self, position_id: UUID) -> list[TaxLot]:
        pass

    @abstractmethod
    def get_position_cost_basis(self, position_id: UUID) -> Money:
        pass


class CorporateActionService(ABC):
    @abstractmethod
    def apply_split(
        self,
        security_id: UUID,
        ratio_numerator: Decimal,
        ratio_denominator: Decimal,
        effective_date: date,
    ) -> int:
        pass

    @abstractmethod
    def apply_spinoff(
        self,
        parent_security_id: UUID,
        child_security_id: UUID,
        allocation_ratio: Decimal,
        effective_date: date,
    ) -> int:
        pass

    @abstractmethod
    def apply_merger(
        self,
        old_security_id: UUID,
        new_security_id: UUID,
        exchange_ratio: Decimal,
        effective_date: date,
        cash_in_lieu_per_share: Money | None = None,
    ) -> int:
        pass

    @abstractmethod
    def apply_symbol_change(
        self,
        security_id: UUID,
        new_symbol: str,
        effective_date: date,
    ) -> None:
        pass


class ReconciliationService(ABC):
    @abstractmethod
    def import_transactions(
        self,
        file_path: str,
        account_id: UUID,
        file_format: str,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def match_imported(
        self,
        imported_transactions: list[dict[str, Any]],
        account_id: UUID,
    ) -> list[MatchResult]:
        pass

    @abstractmethod
    def confirm_match(
        self,
        imported_id: str,
        ledger_transaction_id: UUID,
    ) -> None:
        pass

    @abstractmethod
    def create_from_import(
        self,
        imported_transaction: dict[str, Any],
        account_id: UUID,
    ) -> Transaction:
        pass

    @abstractmethod
    def get_reconciliation_summary(
        self,
        account_id: UUID,
        start_date: date,
        end_date: date,
    ) -> ReconciliationSummary:
        pass


class ReportingService(ABC):
    @abstractmethod
    def net_worth_report(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
        base_currency: str | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def fx_gains_losses_report(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
        base_currency: str = "USD",
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def balance_sheet_report(
        self,
        entity_id: UUID,
        as_of_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def income_statement_report(
        self,
        entity_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def capital_gains_report(
        self,
        entity_ids: list[UUID] | None,
        tax_year: int,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def position_summary_report(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def transaction_summary_by_type(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def transaction_summary_by_entity(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def dashboard_summary(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def export_report(
        self,
        report_data: dict[str, Any],
        output_format: str,
        output_path: str,
    ) -> str:
        pass

    @abstractmethod
    def budget_report(
        self,
        entity_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def household_net_worth_report(
        self,
        household_id: UUID,
        as_of_date: date,
        base_currency: str | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def ownership_weighted_net_worth_report(
        self,
        entity_id: UUID,
        as_of_date: date,
        base_currency: str | None = None,
    ) -> dict[str, Any]:
        pass


class CurrencyService(ABC):
    @abstractmethod
    def add_rate(self, rate: ExchangeRate) -> None:
        pass

    @abstractmethod
    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: date,
    ) -> ExchangeRate | None:
        pass

    @abstractmethod
    def get_latest_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate | None:
        pass

    @abstractmethod
    def convert(
        self,
        amount: Money,
        to_currency: str,
        as_of_date: date,
    ) -> Money:
        pass

    @abstractmethod
    def calculate_fx_gain_loss(
        self,
        original_amount: Money,
        original_date: date,
        current_date: date,
        base_currency: str,
    ) -> Money:
        pass


class ExpenseService(ABC):
    @abstractmethod
    def categorize_transaction(
        self,
        transaction_id: UUID,
        category: str | None = None,
        tags: list[str] | None = None,
        vendor_id: UUID | None = None,
    ) -> Transaction:
        pass

    @abstractmethod
    def auto_categorize(self, transaction: Transaction) -> str | None:
        pass

    @abstractmethod
    def get_expense_summary(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_expenses_by_category(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Money]:
        pass

    @abstractmethod
    def get_expenses_by_vendor(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[UUID, Money]:
        pass

    @abstractmethod
    def detect_recurring_expenses(
        self,
        entity_id: UUID,
        lookback_months: int = 3,
    ) -> list[dict[str, Any]]:
        pass


class BudgetService(ABC):
    @abstractmethod
    def create_budget(
        self,
        name: str,
        entity_id: UUID,
        period_type: str,  # BudgetPeriodType value
        start_date: date,
        end_date: date,
    ) -> Budget:
        pass

    @abstractmethod
    def get_budget(self, budget_id: UUID) -> Budget | None:
        pass

    @abstractmethod
    def update_budget(self, budget: Budget) -> None:
        pass

    @abstractmethod
    def delete_budget(self, budget_id: UUID) -> None:
        pass

    @abstractmethod
    def add_line_item(
        self,
        budget_id: UUID,
        category: str,
        budgeted_amount: Money,
        account_id: UUID | None = None,
        notes: str = "",
    ) -> BudgetLineItem:
        pass

    @abstractmethod
    def get_line_items(self, budget_id: UUID) -> list[BudgetLineItem]:
        pass

    @abstractmethod
    def calculate_variance(
        self,
        budget_id: UUID,
        actual_expenses: dict[str, Money],
    ) -> list[BudgetVariance]:
        pass

    @abstractmethod
    def get_budget_vs_actual(
        self,
        entity_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def check_alerts(
        self,
        budget_id: UUID,
        actual_expenses: dict[str, Money],
        thresholds: list[int] | None = None,  # default [80, 90, 100, 110]
    ) -> list[dict[str, Any]]:
        pass
