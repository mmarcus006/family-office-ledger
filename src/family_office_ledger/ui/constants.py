"""UI constants for Atlas Ledger.

These are kept small and utility-oriented: the UI is data-dense, not decorative.
"""

from __future__ import annotations

from typing import Final


ENTITY_TYPES: Final[list[dict[str, str]]] = [
    {"value": "llc", "label": "LLC"},
    {"value": "trust", "label": "Trust"},
    {"value": "partnership", "label": "Partnership"},
    {"value": "individual", "label": "Individual"},
    {"value": "holding_co", "label": "Holding Company"},
]


ACCOUNT_TYPES: Final[list[dict[str, str]]] = [
    {"value": "asset", "label": "Asset"},
    {"value": "liability", "label": "Liability"},
    {"value": "equity", "label": "Equity"},
    {"value": "income", "label": "Income"},
    {"value": "expense", "label": "Expense"},
]


ACCOUNT_SUB_TYPES: Final[list[dict[str, str]]] = [
    {"value": "checking", "label": "Checking"},
    {"value": "savings", "label": "Savings"},
    {"value": "credit_card", "label": "Credit Card"},
    {"value": "brokerage", "label": "Brokerage"},
    {"value": "ira", "label": "IRA"},
    {"value": "roth_ira", "label": "Roth IRA"},
    {"value": "401k", "label": "401(k)"},
    {"value": "529", "label": "529 Plan"},
    {"value": "real_estate", "label": "Real Estate"},
    {"value": "private_equity", "label": "Private Equity"},
    {"value": "venture_capital", "label": "Venture Capital"},
    {"value": "crypto", "label": "Cryptocurrency"},
    {"value": "cash", "label": "Cash"},
    {"value": "loan", "label": "Loan"},
    {"value": "other", "label": "Other"},
]


# Tailwind class constants
APP_BG: Final[str] = "bg-slate-50"

CARD: Final[str] = "bg-white rounded-lg shadow-sm border border-slate-200"
CARD_PAD: Final[str] = "p-4"

TABLE: Final[str] = "w-full"

BUTTON_PRIMARY: Final[str] = (
    "bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-300"
)
BUTTON_SECONDARY: Final[str] = (
    "bg-slate-200 text-slate-900 hover:bg-slate-300 focus:ring-2 focus:ring-slate-300"
)
BUTTON_DANGER: Final[str] = (
    "bg-rose-600 text-white hover:bg-rose-700 focus:ring-2 focus:ring-rose-300"
)

INPUT: Final[str] = "border border-slate-300 rounded-md px-3 py-2"

NAV_LINK: Final[str] = "block px-3 py-2 rounded hover:bg-slate-100"
NAV_LINK_ACTIVE: Final[str] = "block px-3 py-2 rounded bg-blue-50 text-blue-700"
