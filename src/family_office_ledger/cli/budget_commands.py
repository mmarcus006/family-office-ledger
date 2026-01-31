"""Budget management CLI commands for Family Office Ledger."""

import argparse
from datetime import datetime as dt
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from family_office_ledger.cli._main import get_default_db_path
from family_office_ledger.domain.value_objects import Money
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteBudgetRepository,
    SQLiteDatabase,
    SQLiteTransactionRepository,
    SQLiteVendorRepository,
)
from family_office_ledger.services.budget import BudgetServiceImpl
from family_office_ledger.services.expense import ExpenseServiceImpl


def cmd_budget_create(args: argparse.Namespace) -> int:
    """Create a new budget."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        start_date = dt.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = dt.strptime(args.end_date, "%Y-%m-%d").date()

        db = SQLiteDatabase(str(db_path))
        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        budget = service.create_budget(
            name=args.name,
            entity_id=UUID(args.entity_id),
            period_type=args.period_type,
            start_date=start_date,
            end_date=end_date,
        )

        print(f"Created budget: {budget.id}")
        print(f"  Name: {budget.name}")
        print(f"  Entity: {budget.entity_id}")
        print(f"  Period: {budget.period_type.value}")
        print(f"  Date Range: {budget.start_date} to {budget.end_date}")
        return 0

    except ValueError as e:
        print(f"Error: Invalid input: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_budget_list(args: argparse.Namespace) -> int:
    """List budgets for an entity."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        budget_repo = SQLiteBudgetRepository(db)

        include_inactive = (
            args.include_inactive if hasattr(args, "include_inactive") else False
        )
        budgets = list(
            budget_repo.list_by_entity(UUID(args.entity_id), include_inactive)
        )

        if not budgets:
            print("No budgets found.")
            return 0

        print(f"Budgets for entity {args.entity_id}:")
        print("=" * 70)
        for b in budgets:
            status = "Active" if b.is_active else "Inactive"
            print(f"  {b.id}")
            print(f"    Name: {b.name}")
            print(f"    Period: {b.period_type.value} ({b.start_date} to {b.end_date})")
            print(f"    Status: {status}")
            print()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_budget_add_line(args: argparse.Namespace) -> int:
    """Add a line item to a budget."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        amount = Money(Decimal(args.amount), args.currency)
        account_id = UUID(args.account_id) if args.account_id else None

        line_item = service.add_line_item(
            budget_id=UUID(args.budget_id),
            category=args.category,
            budgeted_amount=amount,
            account_id=account_id,
            notes=args.notes or "",
        )

        print(f"Added line item: {line_item.id}")
        print(f"  Category: {line_item.category}")
        print(f"  Amount: {line_item.budgeted_amount}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_budget_variance(args: argparse.Namespace) -> int:
    """Show budget variance report."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        start_date = dt.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = dt.strptime(args.end_date, "%Y-%m-%d").date()

        db = SQLiteDatabase(str(db_path))
        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        result = service.get_budget_vs_actual(
            entity_id=UUID(args.entity_id),
            start_date=start_date,
            end_date=end_date,
        )

        if result["budget"] is None:
            print("No active budget found for the specified entity and date range.")
            return 0

        budget = result["budget"]
        variances = result["variances"]

        print(f"Budget Variance Report: {budget.name}")
        print("=" * 70)
        print(f"Date Range: {start_date} to {end_date}")
        print(
            f"\n{'Category':<20} {'Budgeted':>12} {'Actual':>12} {'Variance':>12} {'%':>8}"
        )
        print("-" * 66)

        for v in variances:
            status = "OVER" if v.is_over_budget else ""
            print(
                f"{v.category:<20} ${v.budgeted.amount:>11,.2f} ${v.actual.amount:>11,.2f} ${v.variance.amount:>11,.2f} {v.variance_percent:>7}% {status}"
            )

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_budget_alerts(args: argparse.Namespace) -> int:
    """Show budget alerts."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        start_date = dt.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = dt.strptime(args.end_date, "%Y-%m-%d").date()

        db = SQLiteDatabase(str(db_path))
        budget_repo = SQLiteBudgetRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)
        account_repo = SQLiteAccountRepository(db)
        vendor_repo = SQLiteVendorRepository(db)
        expense_service = ExpenseServiceImpl(
            transaction_repo, account_repo, vendor_repo
        )
        service = BudgetServiceImpl(budget_repo, expense_service)

        # Get active budget
        budget = budget_repo.get_active_for_date(UUID(args.entity_id), start_date)
        if budget is None:
            print("No active budget found.")
            return 0

        # Get actual expenses
        actual = expense_service.get_expenses_by_category(
            entity_ids=[UUID(args.entity_id)],
            start_date=start_date,
            end_date=end_date,
        )

        # Check alerts
        thresholds = (
            [int(t) for t in args.thresholds.split(",")] if args.thresholds else None
        )
        alerts = service.check_alerts(budget.id, actual, thresholds)

        if not alerts:
            print("No budget alerts.")
            return 0

        print(f"Budget Alerts: {budget.name}")
        print("=" * 70)

        for alert in alerts:
            status_icon = "[!]" if alert["status"] == "warning" else "[X]"
            print(
                f"{status_icon} {alert['category']}: {alert['percent_used']:.1f}% of budget used"
            )
            print(f"     Budgeted: {alert['budgeted']} | Actual: {alert['actual']}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


__all__ = [
    "cmd_budget_create",
    "cmd_budget_list",
    "cmd_budget_add_line",
    "cmd_budget_variance",
    "cmd_budget_alerts",
]
