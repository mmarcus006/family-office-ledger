"""Dashboard page with overview metrics."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state

init_session_state()

st.title("📊 Dashboard")

as_of = st.date_input("As of Date", value=date.today())

try:
    dashboard_data = None
    net_worth_data = None

    try:
        dashboard_data = api_client.dashboard_summary(as_of_date=as_of)
    except Exception:
        net_worth_data = api_client.net_worth_report(as_of_date=as_of)

    if dashboard_data:
        data = dashboard_data.get("data", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            net_worth = data.get("net_worth", "0")
            st.metric("Net Worth", f"${float(net_worth):,.2f}")
        with col2:
            total_assets = data.get("total_assets", "0")
            st.metric("Total Assets", f"${float(total_assets):,.2f}")
        with col3:
            total_liabilities = data.get("total_liabilities", "0")
            st.metric("Total Liabilities", f"${float(total_liabilities):,.2f}")

        row2 = st.columns(3)
        with row2[0]:
            st.metric("Entities", data.get("entity_count", 0))
        with row2[1]:
            st.metric("Accounts", data.get("account_count", 0))
        with row2[2]:
            st.metric("Transactions", data.get("transaction_count", 0))
    else:
        totals = net_worth_data.get("totals", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Net Worth", f"${totals.get('net_worth', 0):,.2f}")
        with col2:
            st.metric("Total Assets", f"${totals.get('total_assets', 0):,.2f}")
        with col3:
            st.metric(
                "Total Liabilities", f"${totals.get('total_liabilities', 0):,.2f}"
            )

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Recent Transactions")
        start = as_of - timedelta(days=30)
        txns = api_client.list_transactions(start_date=start, end_date=as_of)
        if txns:
            txns_sorted = sorted(
                txns, key=lambda x: x.get("transaction_date", ""), reverse=True
            )[:10]
            df = pd.DataFrame(txns_sorted)
            display_cols = ["transaction_date", "reference", "memo"]
            available_cols = [c for c in display_cols if c in df.columns]
            if available_cols:
                st.dataframe(
                    df[available_cols], use_container_width=True, hide_index=True
                )
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions in the last 30 days.")

    with col_right:
        st.subheader("Entities Summary")
        entities = api_client.list_entities()
        if entities:
            df = pd.DataFrame(entities)
            display_cols = ["name", "entity_type", "is_active"]
            available_cols = [c for c in display_cols if c in df.columns]
            if available_cols:
                st.dataframe(
                    df[available_cols], use_container_width=True, hide_index=True
                )
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No entities created yet. Go to Entities page to create one.")

except api_client.APIError as e:
    st.error(f"API Error: {e.detail}")
except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Make sure the backend API is running.")
