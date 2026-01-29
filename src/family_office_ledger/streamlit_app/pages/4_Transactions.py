"""Transactions page with journal entry and history."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    COLORS,
    apply_custom_css,
    format_currency,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Transactions")


@st.cache_data(ttl=30)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities with caching."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_accounts() -> list[dict[str, Any]]:
    """Fetch accounts with caching."""
    try:
        return api_client.list_accounts()
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_transactions(
    account_id: str | None, start: date, end: date
) -> list[dict[str, Any]]:
    """Fetch transactions with caching."""
    try:
        return api_client.list_transactions(
            account_id=account_id, start_date=start, end_date=end
        )
    except Exception:
        return []


tab_entry, tab_history = st.tabs(["New Journal Entry", "Transaction History"])

entities = get_entities()
accounts = get_accounts()

if not entities:
    st.warning("No entities found. Create an entity first.")
    st.stop()

account_map = {
    str(a["id"]): f"{a['name']} ({a.get('account_type', '')})" for a in accounts
}

with tab_entry:
    section_header("Record Journal Entry")

    if not accounts:
        st.warning("No accounts found. Create accounts first on the Accounts page.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            txn_date = st.date_input("Transaction Date", value=date.today())
        with col2:
            reference = st.text_input("Reference", placeholder="e.g., INV-001")

        memo = st.text_input("Memo", placeholder="e.g., Monthly rent payment")

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Journal Entries")
        st.caption("Debits must equal Credits for a balanced transaction.")

        if "entry_rows" not in st.session_state:
            st.session_state.entry_rows = 2

        entries: list[dict[str, str]] = []
        total_debits = Decimal("0")
        total_credits = Decimal("0")

        for i in range(st.session_state.entry_rows):
            col_acct, col_debit, col_credit = st.columns([3, 1, 1])
            with col_acct:
                acct = st.selectbox(
                    f"Account {i + 1}",
                    options=[""] + list(account_map.keys()),
                    format_func=lambda x: account_map.get(x, "-- Select --")
                    if x
                    else "-- Select --",
                    key=f"acct_{i}",
                )
            with col_debit:
                debit_str = st.text_input(
                    "Debit", value="", key=f"debit_{i}", placeholder="0.00"
                )
            with col_credit:
                credit_str = st.text_input(
                    "Credit", value="", key=f"credit_{i}", placeholder="0.00"
                )

            if acct:
                try:
                    debit = Decimal(debit_str) if debit_str.strip() else Decimal("0")
                    credit = Decimal(credit_str) if credit_str.strip() else Decimal("0")
                    entries.append(
                        {
                            "account_id": acct,
                            "debit_amount": str(debit),
                            "credit_amount": str(credit),
                        }
                    )
                    total_debits += debit
                    total_credits += credit
                except InvalidOperation:
                    st.error(f"Invalid amount in row {i + 1}")

        col_add, col_remove = st.columns(2)
        with col_add:
            if st.button("Add Row", key="add_row"):
                st.session_state.entry_rows += 1
                st.rerun()
        with col_remove:
            if st.session_state.entry_rows > 2 and st.button(
                "Remove Row", key="remove_row"
            ):
                st.session_state.entry_rows -= 1
                st.rerun()

        st.markdown("---")

        diff = total_debits - total_credits
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        with col_summary1:
            st.metric("Total Debits", format_currency(float(total_debits)))
        with col_summary2:
            st.metric("Total Credits", format_currency(float(total_credits)))
        with col_summary3:
            if diff == 0 and total_debits > 0:
                st.markdown(
                    f"""
                    <div style="
                        background-color: {COLORS["positive"]}20;
                        color: {COLORS["positive"]};
                        padding: 0.75rem;
                        border-radius: 6px;
                        text-align: center;
                        font-weight: 600;
                    ">Balanced</div>
                    """,
                    unsafe_allow_html=True,
                )
            elif diff != 0:
                st.markdown(
                    f"""
                    <div style="
                        background-color: {COLORS["negative"]}20;
                        color: {COLORS["negative"]};
                        padding: 0.75rem;
                        border-radius: 6px;
                        text-align: center;
                        font-weight: 600;
                    ">Difference: {format_currency(abs(float(diff)))}</div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("Enter amounts")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button(
            "Post Transaction",
            type="primary",
            disabled=(diff != 0 or total_debits == 0),
            use_container_width=True,
        ):
            valid_entries = [
                e
                for e in entries
                if e["account_id"]
                and (Decimal(e["debit_amount"]) > 0 or Decimal(e["credit_amount"]) > 0)
            ]
            if len(valid_entries) < 2:
                st.error("Need at least 2 entries with amounts.")
            else:
                try:
                    if not isinstance(txn_date, date):
                        txn_date = date.today()
                    result = api_client.post_transaction(
                        transaction_date=txn_date,
                        entries=valid_entries,
                        memo=memo,
                        reference=reference,
                    )
                    st.success(
                        f"Transaction posted! ID: {result.get('id', 'unknown')[:8]}..."
                    )
                    st.session_state.entry_rows = 2
                    get_transactions.clear()
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Failed to post: {e.detail}")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab_history:
    section_header("Transaction History")

    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        filter_account = st.selectbox(
            "Filter by Account",
            options=[""] + list(account_map.keys()),
            format_func=lambda x: account_map.get(x, "All Accounts")
            if x
            else "All Accounts",
        )
    with col_filter2:
        filter_start = st.date_input(
            "From Date", value=date.today() - timedelta(days=90)
        )
    with col_filter3:
        filter_end = st.date_input("To Date", value=date.today())

    if not isinstance(filter_start, date):
        filter_start = date.today() - timedelta(days=90)
    if not isinstance(filter_end, date):
        filter_end = date.today()

    try:
        txns = get_transactions(
            account_id=filter_account if filter_account else None,
            start=filter_start,
            end=filter_end,
        )
        if txns:
            txns_sorted = sorted(
                txns, key=lambda x: x.get("transaction_date", ""), reverse=True
            )

            for txn in txns_sorted[:50]:
                with st.expander(
                    f"**{txn.get('transaction_date', 'N/A')}** - "
                    f"{txn.get('memo', 'No memo')} ({txn.get('reference', 'No ref')})"
                ):
                    txn_entries = txn.get("entries", [])
                    if txn_entries:
                        entry_data = []
                        for entry in txn_entries:
                            debit_amt = Decimal(entry.get("debit_amount", 0) or 0)
                            credit_amt = Decimal(entry.get("credit_amount", 0) or 0)
                            entry_data.append(
                                {
                                    "Account": account_map.get(
                                        str(entry.get("account_id", "")),
                                        str(entry.get("account_id", ""))[:8],
                                    ),
                                    "Debit": format_currency(float(debit_amt))
                                    if debit_amt > 0
                                    else "",
                                    "Credit": format_currency(float(credit_amt))
                                    if credit_amt > 0
                                    else "",
                                }
                            )
                        st.dataframe(
                            pd.DataFrame(entry_data),
                            use_container_width=True,
                            hide_index=True,
                        )
                    st.caption(f"ID: {txn.get('id', 'N/A')}")

            if len(txns) > 50:
                st.info(f"Showing 50 of {len(txns)} transactions.")
        else:
            st.info("No transactions found for the selected filters.")
    except api_client.APIError as e:
        st.error(f"API Error: {e.detail}")
    except Exception as e:
        st.error(f"Error loading transactions: {e}")
