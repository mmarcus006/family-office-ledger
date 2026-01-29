"""Reports page with Net Worth and Balance Sheet."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import plotly.express as px
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state

init_session_state()

st.title("📈 Reports")

entities = []
try:
    entities = api_client.list_entities()
except Exception:
    pass

report_type = st.selectbox(
    "Report Type",
    options=["Net Worth", "Balance Sheet", "Summary by Type", "Summary by Entity"],
)

as_of = st.date_input("As of Date", value=date.today())

if report_type == "Net Worth":
    st.subheader("Net Worth Report")

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

            st.markdown("### Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Assets", f"${totals.get('total_assets', 0):,.2f}")
            with col2:
                st.metric(
                    "Total Liabilities", f"${totals.get('total_liabilities', 0):,.2f}"
                )
            with col3:
                st.metric("Net Worth", f"${totals.get('net_worth', 0):,.2f}")

            data = report.get("data", [])
            if data:
                st.markdown("### Details by Entity")
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                if "entity_name" in df.columns and "balance" in df.columns:
                    try:
                        df["balance_num"] = df["balance"].apply(
                            lambda x: float(Decimal(str(x))) if x else 0
                        )
                        assets = df[df["balance_num"] > 0]
                        if not assets.empty:
                            fig = px.pie(
                                assets,
                                values="balance_num",
                                names="account_name"
                                if "account_name" in assets.columns
                                else "entity_name",
                                title="Asset Allocation",
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        pass

            st.download_button(
                "📥 Download CSV",
                data=pd.DataFrame(data).to_csv(index=False) if data else "",
                file_name=f"net_worth_{as_of.isoformat()}.csv",
                mime="text/csv",
            )

        except api_client.APIError as e:
            st.error(f"API Error: {e.detail}")
        except Exception as e:
            st.error(f"Error generating report: {e}")

elif report_type == "Balance Sheet":
    st.subheader("Balance Sheet Report")

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
                st.metric("Total Assets", f"${totals.get('total_assets', 0):,.2f}")
            with col2:
                st.metric(
                    "Total Liabilities", f"${totals.get('total_liabilities', 0):,.2f}"
                )
            with col3:
                st.metric("Total Equity", f"${totals.get('total_equity', 0):,.2f}")

            data = report.get("data", {})

            for section in ["assets", "liabilities", "equity"]:
                rows = data.get(section, [])
                if rows:
                    st.markdown(f"#### {section.title()}")
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
    st.subheader("Transaction Summary by Account Type")

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
                            key.replace("_", " ").title(), f"${float(value):,.2f}"
                        )

            data = report.get("data", [])
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.download_button(
                    "📥 Download CSV",
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
    st.subheader("Transaction Summary by Entity")

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
                            key.replace("_", " ").title(), f"${float(value):,.2f}"
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
                        )
                        st.plotly_chart(fig, use_container_width=True)

                st.download_button(
                    "📥 Download CSV",
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
