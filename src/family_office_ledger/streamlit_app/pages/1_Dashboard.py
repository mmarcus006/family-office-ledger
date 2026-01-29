"""Dashboard page with Quicken-style overview metrics and charts."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    CHART_COLORS,
    COLORS,
    apply_custom_css,
    format_currency,
    get_plotly_layout,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Dashboard")


@st.cache_data(ttl=60)
def get_dashboard_data(as_of: date) -> dict[str, Any]:
    """Fetch dashboard summary data with caching."""
    try:
        return api_client.dashboard_summary(as_of_date=as_of)
    except Exception:
        return {}


@st.cache_data(ttl=60)
def get_net_worth_data(as_of: date) -> dict[str, Any]:
    """Fetch net worth report with caching."""
    try:
        return api_client.net_worth_report(as_of_date=as_of)
    except Exception:
        return {}


@st.cache_data(ttl=60)
def get_transactions(start: date, end: date) -> list[dict[str, Any]]:
    """Fetch transactions with caching."""
    try:
        return api_client.list_transactions(start_date=start, end_date=end)
    except Exception:
        return []


@st.cache_data(ttl=60)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities with caching."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


@st.cache_data(ttl=60)
def get_accounts() -> list[dict[str, Any]]:
    """Fetch accounts with caching."""
    try:
        return api_client.list_accounts()
    except Exception:
        return []


@st.cache_data(ttl=60)
def get_summary_by_type(start: date, end: date) -> dict[str, Any]:
    """Fetch transaction summary by account type with caching."""
    try:
        return api_client.transaction_summary_by_type(start_date=start, end_date=end)
    except Exception:
        return {}


# Date selector in sidebar
with st.sidebar:
    st.subheader("Filters")
    as_of = st.date_input("As of Date", value=date.today())
    if not isinstance(as_of, date):
        as_of = date.today()

try:
    # Fetch data
    dashboard_data = get_dashboard_data(as_of)
    net_worth_data = get_net_worth_data(as_of)
    entities = get_entities()
    accounts = get_accounts()

    # Extract values
    if dashboard_data and "data" in dashboard_data:
        data = dashboard_data.get("data", {})
        net_worth = float(data.get("net_worth", 0))
        total_assets = float(data.get("total_assets", 0))
        total_liabilities = float(data.get("total_liabilities", 0))
        entity_count = data.get("entity_count", len(entities))
        account_count = data.get("account_count", len(accounts))
        transaction_count = data.get("transaction_count", 0)
    elif net_worth_data and "totals" in net_worth_data:
        totals = net_worth_data.get("totals", {})
        net_worth = float(totals.get("net_worth", 0))
        total_assets = float(totals.get("total_assets", 0))
        total_liabilities = float(totals.get("total_liabilities", 0))
        entity_count = len(entities)
        account_count = len(accounts)
        transaction_count = 0
    else:
        net_worth = 0.0
        total_assets = 0.0
        total_liabilities = 0.0
        entity_count = len(entities)
        account_count = len(accounts)
        transaction_count = 0

    # ============================================
    # NET WORTH - Prominent Card
    # ============================================
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {COLORS["primary"]} 0%, #1a2744 100%);
            padding: 2rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 1.5rem;
        ">
            <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.9;">
                Net Worth
            </div>
            <div style="font-size: 3rem; font-weight: 700; margin: 0.5rem 0;">
                {format_currency(net_worth)}
            </div>
            <div style="font-size: 0.875rem; opacity: 0.8;">
                As of {as_of.strftime("%B %d, %Y")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ============================================
    # KPI ROW
    # ============================================
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.metric(
            label="Total Assets",
            value=format_currency(total_assets),
            border=True,
        )

    with kpi_col2:
        st.metric(
            label="Total Liabilities",
            value=format_currency(total_liabilities),
            border=True,
        )

    with kpi_col3:
        st.metric(
            label="Entities",
            value=str(entity_count),
            border=True,
        )

    with kpi_col4:
        st.metric(
            label="Accounts",
            value=str(account_count),
            border=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================
    # TWO COLUMN LAYOUT
    # ============================================
    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Account Breakdown by Type - Pie Chart
        section_header("Account Breakdown by Type")

        if accounts:
            # Group accounts by type
            account_types: dict[str, float] = {}
            for acc in accounts:
                acc_type = acc.get("account_type", "other")
                # Sum up balances if available, otherwise just count
                balance = float(acc.get("balance", 0) or 0)
                account_types[acc_type] = account_types.get(acc_type, 0) + abs(balance)

            if account_types and any(v > 0 for v in account_types.values()):
                fig_pie = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(account_types.keys()),
                            values=list(account_types.values()),
                            hole=0.4,
                            marker={"colors": CHART_COLORS[: len(account_types)]},
                            textinfo="label+percent",
                            textposition="outside",
                            textfont={"size": 11},
                        )
                    ]
                )
                fig_pie.update_layout(
                    **get_plotly_layout(),
                    showlegend=False,
                    height=300,
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                # Show placeholder chart with account type counts
                type_counts: dict[str, int] = {}
                for acc in accounts:
                    acc_type = acc.get("account_type", "other")
                    type_counts[acc_type] = type_counts.get(acc_type, 0) + 1

                fig_pie = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(type_counts.keys()),
                            values=list(type_counts.values()),
                            hole=0.4,
                            marker={"colors": CHART_COLORS[: len(type_counts)]},
                            textinfo="label+value",
                            textposition="outside",
                        )
                    ]
                )
                fig_pie.update_layout(
                    **get_plotly_layout(),
                    showlegend=False,
                    height=300,
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No accounts to display. Create accounts to see breakdown.")

        # Assets vs Liabilities Bar Chart
        section_header("Assets vs Liabilities")

        if total_assets > 0 or total_liabilities > 0:
            fig_bar = go.Figure(
                data=[
                    go.Bar(
                        x=["Assets", "Liabilities", "Net Worth"],
                        y=[total_assets, total_liabilities, net_worth],
                        marker_color=[
                            COLORS["positive"],
                            COLORS["negative"],
                            COLORS["primary"],
                        ],
                        text=[
                            format_currency(total_assets),
                            format_currency(total_liabilities),
                            format_currency(net_worth),
                        ],
                        textposition="outside",
                    )
                ]
            )
            fig_bar.update_layout(
                **get_plotly_layout(),
                showlegend=False,
                height=300,
                yaxis={"gridcolor": "#e2e8f0", "gridwidth": 1},
                xaxis={"showgrid": False},
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No financial data to display.")

    with col_right:
        # Recent Transactions
        section_header("Recent Transactions")

        start_date = as_of - timedelta(days=30)
        txns = get_transactions(start_date, as_of)

        if txns:
            txns_sorted = sorted(
                txns, key=lambda x: x.get("transaction_date", ""), reverse=True
            )[:10]

            # Create a clean dataframe
            display_data = []
            for txn in txns_sorted:
                display_data.append(
                    {
                        "Date": txn.get("transaction_date", "")[:10],
                        "Reference": txn.get("reference", "-")[:20],
                        "Memo": (txn.get("memo", "-") or "-")[:25],
                    }
                )

            df = pd.DataFrame(display_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=250,
            )
        else:
            st.info("No transactions in the last 30 days.")

        # Entities Summary
        section_header("Entities")

        if entities:
            entity_data = []
            for ent in entities[:5]:
                entity_data.append(
                    {
                        "Name": ent.get("name", ""),
                        "Type": ent.get("entity_type", ""),
                        "Active": "Yes" if ent.get("is_active", True) else "No",
                    }
                )

            df_entities = pd.DataFrame(entity_data)
            st.dataframe(
                df_entities,
                use_container_width=True,
                hide_index=True,
                height=200,
            )
        else:
            st.info("No entities. Go to Entities page to create one.")

except api_client.APIError as e:
    st.error(f"API Error: {e.detail}")
except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Make sure the backend API is running.")
