"""Command-line interface package for Family Office Ledger.

This package provides CLI commands organized into domain-specific submodules:
- reconciliation_commands: Bank reconciliation
- currency_commands: Currency and exchange rates
- budget_commands: Budget management
- qsbs_commands: QSBS tax tracking
- household_commands: Household management

For backward compatibility, all command functions are re-exported here.
"""

# Re-export main entry points and all command functions for backward compatibility
from family_office_ledger.cli._main import (
    cmd_budget_add_line,
    cmd_budget_alerts,
    cmd_budget_create,
    cmd_budget_list,
    cmd_budget_variance,
    cmd_currency_convert,
    cmd_currency_rates_add,
    cmd_currency_rates_latest,
    cmd_currency_rates_list,
    cmd_expense_by_category,
    cmd_expense_by_vendor,
    cmd_expense_categorize,
    cmd_expense_recurring,
    cmd_expense_summary,
    cmd_household_add_member,
    cmd_household_create,
    cmd_household_list,
    cmd_household_members,
    cmd_household_net_worth,
    cmd_ingest,
    cmd_init,
    cmd_ownership_create,
    cmd_ownership_delete,
    cmd_ownership_list,
    cmd_ownership_look_through,
    cmd_ownership_tree,
    cmd_portfolio_allocation,
    cmd_portfolio_concentration,
    cmd_portfolio_summary,
    cmd_qsbs_list,
    cmd_qsbs_mark,
    cmd_qsbs_remove,
    cmd_qsbs_summary,
    cmd_reconcile_close,
    cmd_reconcile_confirm,
    cmd_reconcile_create,
    cmd_reconcile_list,
    cmd_reconcile_reject,
    cmd_reconcile_skip,
    cmd_reconcile_summary,
    cmd_status,
    cmd_tax_export,
    cmd_tax_generate,
    cmd_tax_summary,
    cmd_transfer_close,
    cmd_transfer_confirm,
    cmd_transfer_create,
    cmd_transfer_list,
    cmd_transfer_reject,
    cmd_transfer_summary,
    cmd_ui,
    cmd_vendor_add,
    cmd_vendor_get,
    cmd_vendor_list,
    cmd_vendor_search,
    cmd_vendor_update,
    cmd_version,
    create_app,
    get_default_db_path,
    main,
)

__all__ = [
    # Main entry points
    "main",
    "create_app",
    "get_default_db_path",
    # Init/status/version commands
    "cmd_init",
    "cmd_status",
    "cmd_version",
    "cmd_ingest",
    "cmd_ui",
    # Reconciliation commands
    "cmd_reconcile_create",
    "cmd_reconcile_list",
    "cmd_reconcile_confirm",
    "cmd_reconcile_reject",
    "cmd_reconcile_skip",
    "cmd_reconcile_close",
    "cmd_reconcile_summary",
    # Transfer commands
    "cmd_transfer_create",
    "cmd_transfer_list",
    "cmd_transfer_confirm",
    "cmd_transfer_reject",
    "cmd_transfer_close",
    "cmd_transfer_summary",
    # QSBS commands
    "cmd_qsbs_list",
    "cmd_qsbs_mark",
    "cmd_qsbs_remove",
    "cmd_qsbs_summary",
    # Tax commands
    "cmd_tax_generate",
    "cmd_tax_summary",
    "cmd_tax_export",
    # Portfolio commands
    "cmd_portfolio_allocation",
    "cmd_portfolio_concentration",
    "cmd_portfolio_summary",
    # Currency commands
    "cmd_currency_rates_add",
    "cmd_currency_rates_list",
    "cmd_currency_rates_latest",
    "cmd_currency_convert",
    # Expense commands
    "cmd_expense_categorize",
    "cmd_expense_summary",
    "cmd_expense_by_category",
    "cmd_expense_by_vendor",
    "cmd_expense_recurring",
    # Vendor commands
    "cmd_vendor_add",
    "cmd_vendor_list",
    "cmd_vendor_get",
    "cmd_vendor_update",
    "cmd_vendor_search",
    # Budget commands
    "cmd_budget_create",
    "cmd_budget_list",
    "cmd_budget_add_line",
    "cmd_budget_variance",
    "cmd_budget_alerts",
    # Household commands
    "cmd_household_list",
    "cmd_household_create",
    "cmd_household_add_member",
    "cmd_household_members",
    "cmd_household_net_worth",
    # Ownership commands
    "cmd_ownership_list",
    "cmd_ownership_create",
    "cmd_ownership_delete",
    "cmd_ownership_tree",
    "cmd_ownership_look_through",
]
