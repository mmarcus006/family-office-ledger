"""Reports page with Net Worth and Balance Sheet."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    CHART_COLORS,
    apply_custom_css,
    format_currency,
    get_plotly_layout,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Reports")


@st.cache_data(ttl=30)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities with caching."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


entities = get_entities()

report_type = st.selectbox(
    "Report Type",
    options=["Net Worth", "Balance Sheet", "Summary by Type", "Summary by Entity"],
)

as_of = st.date_input("As of Date", value=date.today())
if not isinstance(as_of, date):
    as_of = date.today()

if report_type == "Net Worth":
    section_header("Net Worth Report")

    if entities:
        entity_options = {str(e["id"]): e["name"] for e in entities}
        selected_entities = st.multiselect(
            "Filter by Entities (leave empty for all)",
            options=list(entity_options.keys()),
            format_func=lambda x: entity_options.get(x, x),
        )
    else:
        selected_entities = []

    if st.button("Generate Report", type="primary"):
        try:
            report = api_client.net_worth_report(
                as_of_date=as_of,
                entity_ids=selected_entities if selected_entities else None,
            )

            totals = report.get("totals", {})

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Total Assets",
                    format_currency(float(totals.get("total_assets", 0))),
                    border=True,
                )
            with col2:
                st.metric(
                    "Total Liabilities",
                    format_currency(float(totals.get("total_liabilities", 0))),
                    border=True,
                )
            with col3:
                st.metric(
                    "Net Worth",
                    format_currency(float(totals.get("net_worth", 0))),
                    border=True,
                )

            data = report.get("data", [])
            if data:
                st.markdown("<br>", unsafe_allow_html=True)
                section_header("Details by Entity")
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                if "entity_name" in df.columns and "balance" in df.columns:
                    try:
                        df["balance_num"] = df["balance"].apply(
                            lambda x: float(Decimal(str(x))) if x else 0
                        )
                        assets = df[df["balance_num"] > 0]
                        if not assets.empty:
                            fig = go.Figure(
                                data=[
                                    go.Pie(
                                        labels=assets.get(
                                            "account_name", assets["entity_name"]
                                        ).tolist(),
                                        values=assets["balance_num"].tolist(),
                                        hole=0.4,
                                        marker={"colors": CHART_COLORS},
                                    )
                                ]
                            )
                            fig.update_layout(
                                **get_plotly_layout("Asset Allocation"), height=400
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        pass

            st.download_button(
                "Download CSV",
                data=pd.DataFrame(data).to_csv(index=False) if data else "",
                file_name=f"net_worth_{as_of.isoformat()}.csv",
                mime="text/csv",
            )

        except api_client.APIError as e:
            st.error(f"API Error: {e.detail}")
        except Exception as e:
            st.error(f"Error generating report: {e}")

elif report_type == "Balance Sheet":
    section_header("Balance Sheet Report")

    if not entities:
        st.warning("No entities found. Create an entity first.")
        st.stop()

    entity_options = {str(e["id"]): e["name"] for e in entities}
    selected_entity = st.selectbox(
        "Select Entity",
        options=list(entity_options.keys()),
        format_func=lambda x: entity_options.get(x, x),
    )

    if st.button("Generate Report", type="primary"):
        try:
            report = api_client.balance_sheet(
                entity_id=selected_entity,
                as_of_date=as_of,
            )

            st.markdown(f"### {report.get('report_name', 'Balance Sheet')}")
            st.caption(
                f"Entity: {entity_options.get(selected_entity)} | As of: {as_of}"
            )

            totals = report.get("totals", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Total Assets",
                    format_currency(float(totals.get("total_assets", 0))),
                    border=True,
                )
            with col2:
                st.metric(
                    "Total Liabilities",
                    format_currency(float(totals.get("total_liabilities", 0))),
                    border=True,
                )
            with col3:
                st.metric(
                    "Total Equity",
                    format_currency(float(totals.get("total_equity", 0))),
                    border=True,
                )

            data = report.get("data", {})

            for section in ["assets", "liabilities", "equity"]:
                rows = data.get(section, [])
                if rows:
                    st.markdown("<br>", unsafe_allow_html=True)
                    section_header(section.title())
                    df = pd.DataFrame(rows)
                    display_cols = ["account_name", "balance"]
                    available_cols = [c for c in display_cols if c in df.columns]
                    st.dataframe(
                        df[available_cols] if available_cols else df,
                        use_container_width=True,
                        hide_index=True,
                    )

        except api_client.APIError as e:
            st.error(f"API Error: {e.detail}")
        except Exception as e:
            st.error(f"Error generating report: {e}")

elif report_type == "Summary by Type":
    section_header("Transaction Summary by Account Type")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today().replace(day=1),
            key="summary_type_start",
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            key="summary_type_end",
        )

    if not isinstance(start_date, date):
        start_date = date.today().replace(day=1)
    if not isinstance(end_date, date):
        end_date = date.today()

    if entities:
        entity_options = {str(e["id"]): e["name"] for e in entities}
        selected_entities = st.multiselect(
            "Filter by Entities (leave empty for all)",
            options=list(entity_options.keys()),
            format_func=lambda x: entity_options.get(x, x),
            key="summary_type_entities",
        )
    else:
        selected_entities = []

    if st.button("Generate Report", type="primary", key="gen_summary_type"):
        try:
            report = api_client.transaction_summary_by_type(
                start_date=start_date,
                end_date=end_date,
                entity_ids=selected_entities if selected_entities else None,
            )

            st.markdown(
                f"### {report.get('report_name', 'Transaction Summary by Type')}"
            )

            totals = report.get("totals", {})
            if totals:
                cols = st.columns(len(totals))
                for i, (key, value) in enumerate(totals.items()):
                    with cols[i % len(cols)]:
                        st.metric(
                            key.replace("_", " ").title(),
                            format_currency(float(value)),
                            border=True,
                        )

            data = report.get("data", [])
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.download_button(
                    "Download CSV",
                    data=df.to_csv(index=False),
                    file_name=f"summary_by_type_{start_date}_{end_date}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No data found for the selected period.")

        except api_client.APIError as e:
            st.error(f"API Error: {e.detail}")
        except Exception as e:
            st.error(f"Error generating report: {e}")

elif report_type == "Summary by Entity":
    section_header("Transaction Summary by Entity")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today().replace(day=1),
            key="summary_entity_start",
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            key="summary_entity_end",
        )

    if not isinstance(start_date, date):
        start_date = date.today().replace(day=1)
    if not isinstance(end_date, date):
        end_date = date.today()

    if entities:
        entity_options = {str(e["id"]): e["name"] for e in entities}
        selected_entities = st.multiselect(
            "Filter by Entities (leave empty for all)",
            options=list(entity_options.keys()),
            format_func=lambda x: entity_options.get(x, x),
            key="summary_entity_entities",
        )
    else:
        selected_entities = []

    if st.button("Generate Report", type="primary", key="gen_summary_entity"):
        try:
            report = api_client.transaction_summary_by_entity(
                start_date=start_date,
                end_date=end_date,
                entity_ids=selected_entities if selected_entities else None,
            )

            st.markdown(
                f"### {report.get('report_name', 'Transaction Summary by Entity')}"
            )

            totals = report.get("totals", {})
            if totals:
                cols = st.columns(min(len(totals), 4))
                for i, (key, value) in enumerate(totals.items()):
                    with cols[i % len(cols)]:
                        st.metric(
                            key.replace("_", " ").title(),
                            format_currency(float(value)),
                            border=True,
                        )

            data = report.get("data", [])
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                if "entity_name" in df.columns and len(df) > 1:
                    numeric_cols = df.select_dtypes(include=["number"]).columns
                    if len(numeric_cols) > 0:
                        fig = px.bar(
                            df,
                            x="entity_name",
                            y=numeric_cols[0],
                            title="By Entity",
                            color_discrete_sequence=CHART_COLORS,
                        )
                        fig.update_layout(**get_plotly_layout())
                        st.plotly_chart(fig, use_container_width=True)

                st.download_button(
                    "Download CSV",
                    data=df.to_csv(index=False),
                    file_name=f"summary_by_entity_{start_date}_{end_date}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No data found for the selected period.")

        except api_client.APIError as e:
            st.error(f"API Error: {e.detail}")
        except Exception as e:
            st.error(f"Error generating report: {e}")
