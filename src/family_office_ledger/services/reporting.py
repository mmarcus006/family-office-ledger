"""Reporting service implementation for financial reports and exports."""

from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from family_office_ledger.domain.value_objects import AccountType, Money
from family_office_ledger.repositories.interfaces import (
    AccountRepository,
    EntityOwnershipRepository,
    EntityRepository,
    HouseholdRepository,
    PositionRepository,
    SecurityRepository,
    TaxLotRepository,
    TransactionRepository,
)
from family_office_ledger.services.currency import ExchangeRateNotFoundError
from family_office_ledger.services.interfaces import (
    BudgetService,
    CurrencyService,
    ReportingService,
)
from family_office_ledger.services.ownership_graph import OwnershipGraphService


class ReportingServiceImpl(ReportingService):
    """Implementation of ReportingService for generating financial reports."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        position_repo: PositionRepository,
        tax_lot_repo: TaxLotRepository,
        security_repo: SecurityRepository,
        currency_service: CurrencyService | None = None,
        budget_service: BudgetService | None = None,
        ownership_repo: EntityOwnershipRepository | None = None,
        household_repo: HouseholdRepository | None = None,
    ) -> None:
        self._entity_repo = entity_repo
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._position_repo = position_repo
        self._tax_lot_repo = tax_lot_repo
        self._security_repo = security_repo
        self._currency_service = currency_service
        self._budget_service = budget_service
        self._ownership_repo = ownership_repo
        self._household_repo = household_repo
        self._ownership_service: OwnershipGraphService | None = None
        if ownership_repo and household_repo:
            self._ownership_service = OwnershipGraphService(
                ownership_repo=ownership_repo,
                household_repo=household_repo,
                entity_repo=entity_repo,
                account_repo=account_repo,
                transaction_repo=transaction_repo,
                position_repo=position_repo,
            )

    def _convert_to_base(
        self,
        amount: Decimal,
        from_currency: str,
        base_currency: str,
        as_of_date: date,
    ) -> Decimal:
        """Convert amount to base currency. Returns original if no service or same currency."""
        if self._currency_service is None:
            return amount
        if from_currency == base_currency:
            return amount
        try:
            money = Money(amount, from_currency)
            converted = self._currency_service.convert(money, base_currency, as_of_date)
            return converted.amount
        except ExchangeRateNotFoundError:
            # If no rate, return original (log warning in production)
            return amount

    def net_worth_report(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
        base_currency: str | None = None,
    ) -> dict[str, Any]:
        """Generate net worth report showing total assets minus liabilities."""
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]
        elif len(entity_ids) == 0:
            result: dict[str, Any] = {
                "report_name": "Net Worth Report",
                "as_of_date": as_of_date,
                "data": [],
                "totals": {
                    "total_assets": Decimal("0"),
                    "total_liabilities": Decimal("0"),
                    "net_worth": Decimal("0"),
                },
            }
            if base_currency:
                result["base_currency"] = base_currency
            return result

        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        entity_data: list[dict[str, Any]] = []

        for entity_id in entity_ids:
            entity = self._entity_repo.get(entity_id)
            if entity is None:
                continue

            entity_assets = Decimal("0")
            entity_liabilities = Decimal("0")

            accounts = list(self._account_repo.list_by_entity(entity_id))

            for account in accounts:
                balance = self._calculate_account_balance(account.id, as_of_date)

                if base_currency and self._currency_service:
                    balance = self._convert_to_base(
                        balance, account.currency, base_currency, as_of_date
                    )

                if account.account_type == AccountType.ASSET:
                    entity_assets += balance
                elif account.account_type == AccountType.LIABILITY:
                    entity_liabilities += abs(balance)

            entity_data.append(
                {
                    "entity_id": str(entity_id),
                    "entity_name": entity.name,
                    "total_assets": entity_assets,
                    "total_liabilities": entity_liabilities,
                    "net_worth": entity_assets - entity_liabilities,
                }
            )

            total_assets += entity_assets
            total_liabilities += entity_liabilities

        result = {
            "report_name": "Net Worth Report",
            "as_of_date": as_of_date,
            "data": entity_data,
            "totals": {
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "net_worth": total_assets - total_liabilities,
            },
        }
        if base_currency:
            result["base_currency"] = base_currency
        return result

    def fx_gains_losses_report(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
        base_currency: str = "USD",
    ) -> dict[str, Any]:
        """Generate FX gains/losses report for foreign currency holdings."""
        if self._currency_service is None:
            return {
                "report_name": "FX Gains/Losses Report",
                "date_range": {"start_date": start_date, "end_date": end_date},
                "base_currency": base_currency,
                "data": [],
                "totals": {
                    "total_fx_gain_loss": Decimal("0"),
                },
                "error": "Currency service not available",
            }

        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]

        fx_data: list[dict[str, Any]] = []
        total_fx_gain_loss = Decimal("0")

        for entity_id in entity_ids:
            entity = self._entity_repo.get(entity_id)
            if entity is None:
                continue

            accounts = list(self._account_repo.list_by_entity(entity_id))

            for account in accounts:
                if account.currency == base_currency:
                    continue

                if account.account_type not in (
                    AccountType.ASSET,
                    AccountType.LIABILITY,
                ):
                    continue

                opening_balance = self._calculate_account_balance(
                    account.id, start_date
                )
                closing_balance = self._calculate_account_balance(account.id, end_date)

                if opening_balance == Decimal("0") and closing_balance == Decimal("0"):
                    continue

                try:
                    original_money = Money(opening_balance, account.currency)
                    fx_gain_loss = self._currency_service.calculate_fx_gain_loss(
                        original_money, start_date, end_date, base_currency
                    )

                    fx_data.append(
                        {
                            "entity_id": str(entity_id),
                            "entity_name": entity.name,
                            "account_id": str(account.id),
                            "account_name": account.name,
                            "currency": account.currency,
                            "opening_balance": opening_balance,
                            "closing_balance": closing_balance,
                            "fx_gain_loss": fx_gain_loss.amount,
                        }
                    )
                    total_fx_gain_loss += fx_gain_loss.amount
                except ExchangeRateNotFoundError:
                    fx_data.append(
                        {
                            "entity_id": str(entity_id),
                            "entity_name": entity.name,
                            "account_id": str(account.id),
                            "account_name": account.name,
                            "currency": account.currency,
                            "opening_balance": opening_balance,
                            "closing_balance": closing_balance,
                            "fx_gain_loss": None,
                            "error": "Exchange rate not found",
                        }
                    )

        return {
            "report_name": "FX Gains/Losses Report",
            "date_range": {"start_date": start_date, "end_date": end_date},
            "base_currency": base_currency,
            "data": fx_data,
            "totals": {
                "total_fx_gain_loss": total_fx_gain_loss,
            },
        }

    def balance_sheet_report(
        self,
        entity_id: UUID,
        as_of_date: date,
    ) -> dict[str, Any]:
        """Generate balance sheet showing assets, liabilities, and equity."""
        accounts = list(self._account_repo.list_by_entity(entity_id))

        assets: list[dict[str, Any]] = []
        liabilities: list[dict[str, Any]] = []
        equity_items: list[dict[str, Any]] = []

        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        total_equity = Decimal("0")

        for account in accounts:
            balance = self._calculate_account_balance(account.id, as_of_date)

            account_data = {
                "account_id": str(account.id),
                "account_name": account.name,
                "balance": balance,
            }

            if account.account_type == AccountType.ASSET:
                assets.append(account_data)
                total_assets += balance
            elif account.account_type == AccountType.LIABILITY:
                liabilities.append(account_data)
                # Liabilities are stored as negative (credit balance)
                total_liabilities += abs(balance)
            elif account.account_type == AccountType.EQUITY:
                equity_items.append(account_data)
                # Equity is stored as negative (credit balance)
                total_equity += abs(balance)

        return {
            "report_name": "Balance Sheet",
            "as_of_date": as_of_date,
            "data": {
                "assets": assets,
                "liabilities": liabilities,
                "equity": equity_items,
            },
            "totals": {
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
            },
        }

    def income_statement_report(
        self,
        entity_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Generate income statement showing income vs expenses for a period."""
        accounts = list(self._account_repo.list_by_entity(entity_id))

        income_items: list[dict[str, Any]] = []
        expense_items: list[dict[str, Any]] = []

        total_income = Decimal("0")
        total_expenses = Decimal("0")

        for account in accounts:
            # Calculate activity for the period only
            balance = self._calculate_account_balance_for_period(
                account.id, start_date, end_date
            )

            account_data = {
                "account_id": str(account.id),
                "account_name": account.name,
                "amount": abs(balance),
            }

            if account.account_type == AccountType.INCOME and balance != Decimal("0"):
                income_items.append(account_data)
                # Income has credit balance (negative in debit-credit terms)
                total_income += abs(balance)
            elif account.account_type == AccountType.EXPENSE and balance != Decimal(
                "0"
            ):
                expense_items.append(account_data)
                # Expenses have debit balance (positive)
                total_expenses += abs(balance)

        return {
            "report_name": "Income Statement",
            "date_range": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "data": {
                "income": income_items,
                "expenses": expense_items,
            },
            "totals": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net_income": total_income - total_expenses,
            },
        }

    def capital_gains_report(
        self,
        entity_ids: list[UUID] | None,
        tax_year: int,
    ) -> dict[str, Any]:
        """Generate capital gains report showing realized gains by lot."""
        # Get entities to include
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]

        gains_data: list[dict[str, Any]] = []
        short_term_gains = Decimal("0")
        long_term_gains = Decimal("0")

        year_start = date(tax_year, 1, 1)
        year_end = date(tax_year, 12, 31)

        for entity_id in entity_ids:
            # Get all investment accounts for this entity
            accounts = list(self._account_repo.list_by_entity(entity_id))
            investment_accounts = [a for a in accounts if a.is_investment_account]

            for account in investment_accounts:
                # Get positions for this account
                positions = list(self._position_repo.list_by_account(account.id))

                for position in positions:
                    # Get all tax lots for this position
                    lots = list(self._tax_lot_repo.list_by_position(position.id))

                    for lot in lots:
                        # Check if lot was disposed in this tax year
                        if lot.disposition_date is None:
                            continue

                        if not (year_start <= lot.disposition_date <= year_end):
                            continue

                        # Only include fully disposed lots
                        if not lot.is_fully_disposed:
                            continue

                        # Get security info
                        security = self._security_repo.get(position.security_id)
                        security_name = security.symbol if security else "Unknown"

                        # Calculate gain (we don't have proceeds stored, so we estimate)
                        cost_basis = lot.total_cost.amount

                        lot_data = {
                            "lot_id": str(lot.id),
                            "security": security_name,
                            "acquisition_date": lot.acquisition_date,
                            "disposition_date": lot.disposition_date,
                            "quantity": str(lot.original_quantity.value),
                            "cost_basis": cost_basis,
                            "is_long_term": lot.is_long_term,
                            "holding_period_days": lot.holding_period_days,
                        }

                        gains_data.append(lot_data)

                        # Track by holding period
                        # Note: Without actual sale proceeds, we can't calculate actual gain
                        # This is a simplified report showing disposed lots

        return {
            "report_name": "Capital Gains Report",
            "tax_year": tax_year,
            "data": gains_data,
            "totals": {
                "short_term_gains": short_term_gains,
                "long_term_gains": long_term_gains,
                "total_gains": short_term_gains + long_term_gains,
            },
        }

    def position_summary_report(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
    ) -> dict[str, Any]:
        """Generate position summary showing holdings by security."""
        # Get entities to include
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]

        position_data: list[dict[str, Any]] = []
        total_cost_basis = Decimal("0")
        total_market_value = Decimal("0")

        for entity_id in entity_ids:
            # Get all positions for this entity
            positions = list(self._position_repo.list_by_entity(entity_id))

            for position in positions:
                # Skip zero-quantity positions
                if position.quantity.is_zero:
                    continue

                # Get security info
                security = self._security_repo.get(position.security_id)
                security_symbol = security.symbol if security else "Unknown"
                security_name = security.name if security else "Unknown"

                # Get account info
                account = self._account_repo.get(position.account_id)
                account_name = account.name if account else "Unknown"

                cost_basis = position.cost_basis.amount
                market_value = position.market_value.amount
                unrealized_gain = market_value - cost_basis

                position_data.append(
                    {
                        "position_id": str(position.id),
                        "account_name": account_name,
                        "security_symbol": security_symbol,
                        "security_name": security_name,
                        "quantity": str(position.quantity.value),
                        "cost_basis": cost_basis,
                        "market_value": market_value,
                        "unrealized_gain": unrealized_gain,
                    }
                )

                total_cost_basis += cost_basis
                total_market_value += market_value

        return {
            "report_name": "Position Summary",
            "as_of_date": as_of_date,
            "data": position_data,
            "totals": {
                "total_cost_basis": total_cost_basis,
                "total_market_value": total_market_value,
                "total_unrealized_gain": total_market_value - total_cost_basis,
            },
        }

    def transaction_summary_by_type(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]

        type_counts: dict[str, int] = {}
        type_amounts: dict[str, Decimal] = {}

        for entity_id in entity_ids:
            transactions = list(
                self._transaction_repo.list_by_entity(
                    entity_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

            for txn in transactions:
                txn_type = txn.reference if txn.reference else "unclassified"
                type_counts[txn_type] = type_counts.get(txn_type, 0) + 1
                type_amounts[txn_type] = (
                    type_amounts.get(txn_type, Decimal("0")) + txn.total_debits.amount
                )

        data = [
            {
                "transaction_type": t,
                "count": type_counts[t],
                "total_amount": type_amounts[t],
            }
            for t in sorted(type_counts.keys())
        ]

        total_count = sum(type_counts.values())
        total_amount = sum(type_amounts.values())

        return {
            "report_name": "Transaction Summary by Type",
            "date_range": {"start_date": start_date, "end_date": end_date},
            "data": data,
            "totals": {
                "total_transactions": total_count,
                "total_amount": total_amount,
            },
        }

    def transaction_summary_by_entity(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
        else:
            entities = [e for e in self._entity_repo.list_all() if e.id in entity_ids]

        data: list[dict[str, Any]] = []
        total_count = 0
        total_amount = Decimal("0")

        for entity in entities:
            transactions = list(
                self._transaction_repo.list_by_entity(
                    entity.id,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

            entity_count = len(transactions)
            entity_amount = sum(
                (txn.total_debits.amount for txn in transactions), Decimal("0")
            )

            data.append(
                {
                    "entity_id": str(entity.id),
                    "entity_name": entity.name,
                    "entity_type": entity.entity_type.value,
                    "transaction_count": entity_count,
                    "total_amount": entity_amount,
                }
            )

            total_count += entity_count
            total_amount += entity_amount

        return {
            "report_name": "Transaction Summary by Entity",
            "date_range": {"start_date": start_date, "end_date": end_date},
            "data": data,
            "totals": {
                "total_transactions": total_count,
                "total_amount": total_amount,
            },
        }

    def dashboard_summary(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
    ) -> dict[str, Any]:
        net_worth = self.net_worth_report(entity_ids, as_of_date)

        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]

        total_accounts = 0
        total_transactions = 0
        for entity_id in entity_ids:
            accounts = list(self._account_repo.list_by_entity(entity_id))
            total_accounts += len(accounts)
            transactions = list(self._transaction_repo.list_by_entity(entity_id))
            total_transactions += len(transactions)

        return {
            "report_name": "Dashboard Summary",
            "as_of_date": as_of_date,
            "data": {
                "total_entities": len(entity_ids),
                "total_accounts": total_accounts,
                "total_transactions": total_transactions,
                "net_worth": net_worth["totals"]["net_worth"],
                "total_assets": net_worth["totals"]["total_assets"],
                "total_liabilities": net_worth["totals"]["total_liabilities"],
            },
        }

    def export_report(
        self,
        report_data: dict[str, Any],
        output_format: str,
        output_path: str,
    ) -> str:
        format_lower = output_format.lower()

        if format_lower == "json":
            self._export_to_json(report_data, output_path)
        elif format_lower == "csv":
            self._export_to_csv(report_data, output_path)
        else:
            raise ValueError(
                f"Unsupported format: {output_format}. Use 'json' or 'csv'."
            )

        return output_path

    def budget_report(
        self,
        entity_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Generate budget vs actual report for an entity."""
        if self._budget_service is None:
            return {
                "report_name": "Budget Report",
                "entity_id": entity_id,
                "start_date": start_date,
                "end_date": end_date,
                "data": [],
                "totals": {"error": "Budget service not configured"},
            }

        result = self._budget_service.get_budget_vs_actual(
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
        )

        if result["budget"] is None:
            return {
                "report_name": "Budget Report",
                "entity_id": entity_id,
                "start_date": start_date,
                "end_date": end_date,
                "data": [],
                "totals": {"message": "No active budget found for period"},
            }

        budget = result["budget"]
        variances = result["variances"]

        variance_data = []
        total_budgeted = Decimal("0")
        total_actual = Decimal("0")

        for v in variances:
            total_budgeted += v.budgeted.amount
            total_actual += v.actual.amount
            variance_data.append(
                {
                    "category": v.category,
                    "budgeted": str(v.budgeted.amount),
                    "actual": str(v.actual.amount),
                    "variance": str(v.variance.amount),
                    "variance_percent": str(v.variance_percent),
                    "is_over_budget": v.is_over_budget,
                }
            )

        total_variance = total_budgeted - total_actual
        total_variance_pct = (
            (total_variance / total_budgeted * 100).quantize(Decimal("0.01"))
            if total_budgeted > 0
            else Decimal("0")
        )

        return {
            "report_name": "Budget Report",
            "budget_id": budget.id,
            "budget_name": budget.name,
            "entity_id": entity_id,
            "period_type": budget.period_type.value,
            "start_date": start_date,
            "end_date": end_date,
            "data": variance_data,
            "totals": {
                "total_budgeted": str(total_budgeted),
                "total_actual": str(total_actual),
                "total_variance": str(total_variance),
                "total_variance_percent": str(total_variance_pct),
                "categories_over_budget": sum(1 for v in variances if v.is_over_budget),
                "categories_under_budget": sum(
                    1 for v in variances if not v.is_over_budget
                ),
            },
        }

    def _export_to_json(self, report_data: dict[str, Any], output_path: str) -> None:
        """Export report data to JSON file."""
        # Convert non-serializable types
        serializable_data = self._make_json_serializable(report_data)

        with open(output_path, "w") as f:
            json.dump(serializable_data, f, indent=2)

    def _export_to_csv(self, report_data: dict[str, Any], output_path: str) -> None:
        """Export report data to CSV file, flattening nested structures."""
        data = report_data.get("data", [])

        # Handle nested data structures (like balance sheet)
        if isinstance(data, dict):
            # Flatten nested structure
            rows = self._flatten_nested_data(data)
        elif isinstance(data, list):
            rows = data
        else:
            rows = []

        if not rows:
            # Write empty file with just report info
            with open(output_path, "w", newline="") as f:
                simple_writer = csv.writer(f)
                simple_writer.writerow(
                    ["report_name", report_data.get("report_name", "")]
                )
                if "as_of_date" in report_data:
                    simple_writer.writerow(
                        ["as_of_date", str(report_data["as_of_date"])]
                    )
            return

        # Get all unique keys from all rows for CSV header
        all_keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in all_keys:
                    all_keys.append(key)

        with open(output_path, "w", newline="") as f:
            dict_writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            dict_writer.writeheader()
            for row in rows:
                # Convert any non-string values
                serialized_row = {k: self._serialize_value(v) for k, v in row.items()}
                dict_writer.writerow(serialized_row)

    def _flatten_nested_data(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten nested data structure for CSV export."""
        rows: list[dict[str, Any]] = []

        for category, items in data.items():
            if isinstance(items, list):
                for item in items:
                    row = {"category": category}
                    if isinstance(item, dict):
                        row.update(item)
                    else:
                        row["value"] = item
                    rows.append(row)

        return rows

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        else:
            return obj

    def _serialize_value(self, value: Any) -> str:
        """Serialize a value to string for CSV output."""
        if isinstance(value, Decimal):
            return str(value)
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, UUID):
            return str(value)
        elif value is None:
            return ""
        else:
            return str(value)

    def _calculate_account_balance(self, account_id: UUID, as_of_date: date) -> Decimal:
        """Calculate account balance as of a specific date."""
        # Get all transactions up to as_of_date
        transactions = list(
            self._transaction_repo.list_by_account(
                account_id,
                start_date=None,
                end_date=as_of_date,
            )
        )

        balance = Decimal("0")
        for txn in transactions:
            for entry in txn.entries:
                if entry.account_id == account_id:
                    balance += entry.debit_amount.amount
                    balance -= entry.credit_amount.amount

        return balance

    def _calculate_account_balance_for_period(
        self, account_id: UUID, start_date: date, end_date: date
    ) -> Decimal:
        """Calculate account activity for a specific period."""
        transactions = list(
            self._transaction_repo.list_by_account(
                account_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

        balance = Decimal("0")
        for txn in transactions:
            for entry in txn.entries:
                if entry.account_id == account_id:
                    balance += entry.debit_amount.amount
                    balance -= entry.credit_amount.amount

        return balance

    def household_net_worth_report(
        self,
        household_id: UUID,
        as_of_date: date,
        base_currency: str | None = None,
    ) -> dict[str, Any]:
        """Generate look-through net worth report for a household."""
        if self._ownership_service is None or self._household_repo is None:
            return {
                "report_name": "Household Net Worth Report",
                "as_of_date": as_of_date,
                "error": "Ownership service not configured",
                "totals": {
                    "total_assets": Decimal("0"),
                    "total_liabilities": Decimal("0"),
                    "net_worth": Decimal("0"),
                },
            }

        household = self._household_repo.get(household_id)
        if household is None:
            return {
                "report_name": "Household Net Worth Report",
                "as_of_date": as_of_date,
                "error": f"Household {household_id} not found",
                "totals": {
                    "total_assets": Decimal("0"),
                    "total_liabilities": Decimal("0"),
                    "net_worth": Decimal("0"),
                },
            }

        look_through = self._ownership_service.household_look_through_net_worth(
            household_id, as_of_date
        )

        total_assets = Decimal(str(look_through.get("total_assets", 0)))
        total_liabilities = Decimal(str(look_through.get("total_liabilities", 0)))
        net_worth = Decimal(str(look_through.get("net_worth", 0)))

        if base_currency and self._currency_service:
            total_assets = self._convert_to_base(
                total_assets, "USD", base_currency, as_of_date
            )
            total_liabilities = self._convert_to_base(
                total_liabilities, "USD", base_currency, as_of_date
            )
            net_worth = self._convert_to_base(
                net_worth, "USD", base_currency, as_of_date
            )

        result: dict[str, Any] = {
            "report_name": "Household Net Worth Report",
            "household_id": str(household_id),
            "household_name": household.name,
            "as_of_date": as_of_date,
            "data": look_through.get("detail", []),
            "totals": {
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "net_worth": net_worth,
            },
        }
        if base_currency:
            result["base_currency"] = base_currency
        return result

    def ownership_weighted_net_worth_report(
        self,
        entity_id: UUID,
        as_of_date: date,
        base_currency: str | None = None,
    ) -> dict[str, Any]:
        """Generate look-through net worth report for a beneficial owner entity."""
        if self._ownership_service is None:
            return {
                "report_name": "Ownership Weighted Net Worth Report",
                "as_of_date": as_of_date,
                "error": "Ownership service not configured",
                "totals": {
                    "total_assets": Decimal("0"),
                    "total_liabilities": Decimal("0"),
                    "net_worth": Decimal("0"),
                },
            }

        entity = self._entity_repo.get(entity_id)
        if entity is None:
            return {
                "report_name": "Ownership Weighted Net Worth Report",
                "as_of_date": as_of_date,
                "error": f"Entity {entity_id} not found",
                "totals": {
                    "total_assets": Decimal("0"),
                    "total_liabilities": Decimal("0"),
                    "net_worth": Decimal("0"),
                },
            }

        look_through = self._ownership_service.beneficial_owner_look_through_net_worth(
            entity_id, as_of_date
        )

        total_assets = Decimal(str(look_through.get("total_assets", 0)))
        total_liabilities = Decimal(str(look_through.get("total_liabilities", 0)))
        net_worth = Decimal(str(look_through.get("net_worth", 0)))

        if base_currency and self._currency_service:
            total_assets = self._convert_to_base(
                total_assets, "USD", base_currency, as_of_date
            )
            total_liabilities = self._convert_to_base(
                total_liabilities, "USD", base_currency, as_of_date
            )
            net_worth = self._convert_to_base(
                net_worth, "USD", base_currency, as_of_date
            )

        result: dict[str, Any] = {
            "report_name": "Ownership Weighted Net Worth Report",
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "as_of_date": as_of_date,
            "data": look_through.get("detail", []),
            "totals": {
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "net_worth": net_worth,
            },
        }
        if base_currency:
            result["base_currency"] = base_currency
        return result
