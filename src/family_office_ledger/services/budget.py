from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from family_office_ledger.domain.budgets import (
    Budget,
    BudgetLineItem,
    BudgetPeriodType,
    BudgetVariance,
)
from family_office_ledger.domain.value_objects import Money
from family_office_ledger.repositories.interfaces import BudgetRepository
from family_office_ledger.services.interfaces import BudgetService, ExpenseService


class BudgetServiceImpl(BudgetService):
    def __init__(
        self,
        budget_repo: BudgetRepository,
        expense_service: ExpenseService,
    ) -> None:
        self._budget_repo = budget_repo
        self._expense_service = expense_service

    def create_budget(
        self,
        name: str,
        entity_id: UUID,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> Budget:
        budget = Budget(
            name=name,
            entity_id=entity_id,
            period_type=BudgetPeriodType(period_type),
            start_date=start_date,
            end_date=end_date,
            id=uuid4(),
        )
        self._budget_repo.add(budget)
        return budget

    def get_budget(self, budget_id: UUID) -> Budget | None:
        return self._budget_repo.get(budget_id)

    def update_budget(self, budget: Budget) -> None:
        self._budget_repo.update(budget)

    def delete_budget(self, budget_id: UUID) -> None:
        self._budget_repo.delete(budget_id)

    def add_line_item(
        self,
        budget_id: UUID,
        category: str,
        budgeted_amount: Money,
        account_id: UUID | None = None,
        notes: str = "",
    ) -> BudgetLineItem:
        line_item = BudgetLineItem(
            budget_id=budget_id,
            category=category,
            budgeted_amount=budgeted_amount,
            id=uuid4(),
            account_id=account_id,
            notes=notes,
        )
        self._budget_repo.add_line_item(line_item)
        return line_item

    def get_line_items(self, budget_id: UUID) -> list[BudgetLineItem]:
        return list(self._budget_repo.get_line_items(budget_id))

    def calculate_variance(
        self,
        budget_id: UUID,
        actual_expenses: dict[str, Money],
    ) -> list[BudgetVariance]:
        line_items = self._budget_repo.get_line_items(budget_id)
        variances: list[BudgetVariance] = []

        for item in line_items:
            actual = actual_expenses.get(item.category, Money(Decimal("0")))
            variance = BudgetVariance(
                category=item.category,
                budgeted=item.budgeted_amount,
                actual=actual,
            )
            variances.append(variance)

        return variances

    def get_budget_vs_actual(
        self,
        entity_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        budget = self._budget_repo.get_active_for_date(entity_id, start_date)
        if budget is None:
            return {
                "budget": None,
                "line_items": [],
                "actual_expenses": {},
                "variances": [],
            }

        line_items = list(self._budget_repo.get_line_items(budget.id))
        actual_expenses = self._expense_service.get_expenses_by_category(
            entity_ids=[entity_id],
            start_date=start_date,
            end_date=end_date,
        )

        variances = self.calculate_variance(budget.id, actual_expenses)

        return {
            "budget": budget,
            "line_items": line_items,
            "actual_expenses": actual_expenses,
            "variances": variances,
        }

    def check_alerts(
        self,
        budget_id: UUID,
        actual_expenses: dict[str, Money],
        thresholds: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        if thresholds is None:
            thresholds = [80, 90, 100, 110]

        alerts: list[dict[str, Any]] = []
        line_items = self._budget_repo.get_line_items(budget_id)

        for item in line_items:
            actual = actual_expenses.get(item.category, Money(Decimal("0")))
            if item.budgeted_amount.amount == 0:
                continue

            percent_used = (actual.amount / item.budgeted_amount.amount) * 100

            for threshold in sorted(thresholds, reverse=True):
                if percent_used >= threshold:
                    alerts.append(
                        {
                            "category": item.category,
                            "threshold": threshold,
                            "percent_used": float(percent_used),
                            "budgeted": item.budgeted_amount,
                            "actual": actual,
                            "status": "over_budget" if threshold >= 100 else "warning",
                        }
                    )
                    break

        return alerts
