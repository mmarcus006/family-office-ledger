"""Transactions page with journal entry and history."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state

init_session_state()

st.title("📝 Transactions")

tab_entry, tab_history = st.tabs(["New Journal Entry", "Transaction History"])

entities = []
accounts = []
try:
    entities = api_client.list_entities()
    accounts = api_client.list_accounts()
except Exception:
    pass

if not entities:
    st.warning("No entities found. Create an entity first.")
    st.stop()

account_map = {
    str(a["id"]): f"{a['name']} ({a.get('account_type', '')})" for a in accounts
}

with tab_entry:
    st.subheader("Record Journal Entry")

    if not accounts:
        st.warning("No accounts found. Create accounts first on the Accounts page.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            txn_date = st.date_input("Transaction Date", value=date.today())
        with col2:
            reference = st.text_input("Reference", placeholder="e.g., INV-001")

        memo = st.text_input("Memo", placeholder="e.g., Monthly rent payment")

        st.markdown("### Journal Entries")
        st.caption("Debits must equal Credits for a balanced transaction.")

        if "entry_rows" not in st.session_state:
            st.session_state.entry_rows = 2

        entries = []
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
            if st.button("➕ Add Row"):
                st.session_state.entry_rows += 1
                st.rerun()
        with col_remove:
            if st.session_state.entry_rows > 2 and st.button("➖ Remove Row"):
                st.session_state.entry_rows -= 1
                st.rerun()

        st.markdown("---")

        diff = total_debits - total_credits
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        with col_summary1:
            st.metric("Total Debits", f"${total_debits:,.2f}")
        with col_summary2:
            st.metric("Total Credits", f"${total_credits:,.2f}")
        with col_summary3:
            if diff == 0 and total_debits > 0:
                st.success("✅ Balanced")
            elif diff != 0:
                st.error(f"❌ Difference: ${abs(diff):,.2f}")
            else:
                st.info("Enter amounts")

        if st.button(
            "Post Transaction",
            type="primary",
            disabled=(diff != 0 or total_debits == 0),
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
                    result = api_client.post_transaction(
                        transaction_date=txn_date,
                        entries=valid_entries,
                        memo=memo,
                        reference=reference,
                    )
                    st.success(
                        f"✅ Transaction posted! ID: {result.get('id', 'unknown')[:8]}..."
                    )
                    st.session_state.entry_rows = 2
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Failed to post: {e.detail}")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab_history:
    st.subheader("Transaction History")

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

    try:
        txns = api_client.list_transactions(
            account_id=filter_account if filter_account else None,
            start_date=filter_start,
            end_date=filter_end,
        )
        if txns:
            txns_sorted = sorted(
                txns, key=lambda x: x.get("transaction_date", ""), reverse=True
            )

            for txn in txns_sorted[:50]:
                with st.expander(
                    f"**{txn.get('transaction_date', 'N/A')}** - {txn.get('memo', 'No memo')} ({txn.get('reference', 'No ref')})"
                ):
                    entries = txn.get("entries", [])
                    if entries:
                        entry_data = []
                        for e in entries:
                            entry_data.append(
                                {
                                    "Account": account_map.get(
                                        str(e.get("account_id", "")),
                                        str(e.get("account_id", ""))[:8],
                                    ),
                                    "Debit": f"${Decimal(e.get('debit_amount', 0)):,.2f}"
                                    if Decimal(e.get("debit_amount", 0)) > 0
                                    else "",
                                    "Credit": f"${Decimal(e.get('credit_amount', 0)):,.2f}"
                                    if Decimal(e.get("credit_amount", 0)) > 0
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
