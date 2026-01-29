"""Audit trail page for viewing system audit entries."""

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
    apply_custom_css,
    get_plotly_layout,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Audit Trail")


@st.cache_data(ttl=30)
def get_audit_entries(
    entity_type: str | None,
    action: str | None,
    start_date: date | None,
    end_date: date | None,
    limit: int = 100,
) -> dict[str, Any]:
    """Fetch audit entries with caching."""
    try:
        return api_client.list_audit_entries(
            entity_type=entity_type,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    except Exception:
        return {}


@st.cache_data(ttl=30)
def get_audit_summary(
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    """Fetch audit summary with caching."""
    try:
        return api_client.get_audit_summary(start_date=start_date, end_date=end_date)
    except Exception:
        return {}


# ============================================
# SIDEBAR FILTERS
# ============================================
with st.sidebar:
    st.subheader("Filters")

    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30),
            key="audit_start_date",
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            key="audit_end_date",
        )

    # Ensure valid date types
    if not isinstance(start_date, date):
        start_date = date.today() - timedelta(days=30)
    if not isinstance(end_date, date):
        end_date = date.today()

    # Entity type filter
    entity_type_options = ["All", "entity", "account", "transaction", "reconciliation"]
    entity_type = st.selectbox(
        "Entity Type",
        options=entity_type_options,
        index=0,
    )
    entity_type_filter = None if entity_type == "All" else entity_type

    # Action filter
    action_options = ["All", "create", "update", "delete", "confirm", "reject"]
    action = st.selectbox(
        "Action",
        options=action_options,
        index=0,
    )
    action_filter = None if action == "All" else action

    # Result limit
    limit = st.number_input(
        "Max Results",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
    )

try:
    # ============================================
    # SUMMARY STATISTICS
    # ============================================
    section_header("Audit Summary")

    summary = get_audit_summary(start_date, end_date)

    if summary:
        summary_data = summary.get("data", summary)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_entries = summary_data.get("total_entries", 0)
            st.metric(label="Total Entries", value=str(total_entries), border=True)

        with col2:
            creates = summary_data.get("creates", 0)
            st.metric(label="Creates", value=str(creates), border=True)

        with col3:
            updates = summary_data.get("updates", 0)
            st.metric(label="Updates", value=str(updates), border=True)

        with col4:
            deletes = summary_data.get("deletes", 0)
            st.metric(label="Deletes", value=str(deletes), border=True)

        # Action breakdown chart
        st.markdown("<br>", unsafe_allow_html=True)

        by_action = summary_data.get("by_action", {})
        if by_action:
            fig_action = go.Figure(
                data=[
                    go.Pie(
                        labels=list(by_action.keys()),
                        values=list(by_action.values()),
                        hole=0.4,
                        marker={"colors": CHART_COLORS[: len(by_action)]},
                        textinfo="label+value",
                        textposition="outside",
                    )
                ]
            )
            fig_action.update_layout(
                **get_plotly_layout("Actions by Type"),
                showlegend=False,
                height=300,
            )
            st.plotly_chart(fig_action, use_container_width=True)
    else:
        st.info("No audit summary data available.")

    # ============================================
    # AUDIT ENTRIES LIST
    # ============================================
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Audit Entries")

    entries = get_audit_entries(
        entity_type=entity_type_filter,
        action=action_filter,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    if entries:
        entries_list = entries.get("entries", entries.get("data", []))
        if isinstance(entries_list, list) and entries_list:
            display_data = []
            for entry in entries_list:
                display_data.append(
                    {
                        "Timestamp": entry.get("timestamp", "")[:19],
                        "Entity Type": entry.get("entity_type", "-"),
                        "Action": entry.get("action", "-"),
                        "Entity ID": str(entry.get("entity_id", "-"))[:8] + "...",
                        "User": entry.get("user", "system"),
                        "Changes": str(entry.get("changes", {}))[:50] + "...",
                    }
                )

            df = pd.DataFrame(display_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=400,
            )

            # Entry detail expander
            st.markdown("<br>", unsafe_allow_html=True)
            section_header("Entry Details")

            entry_ids = [str(e.get("id", "")) for e in entries_list if e.get("id")]
            if entry_ids:
                selected_id = st.selectbox(
                    "Select entry to view details",
                    options=entry_ids,
                    format_func=lambda x: f"Entry {x[:8]}...",
                )

                if selected_id:
                    selected_entry = next(
                        (
                            e
                            for e in entries_list
                            if str(e.get("id", "")) == selected_id
                        ),
                        None,
                    )
                    if selected_entry:
                        with st.expander("View Full Entry", expanded=True):
                            st.json(selected_entry)
        else:
            st.info("No audit entries found for the selected filters.")
    else:
        st.info("No audit entries available.")

except api_client.APIError as e:
    st.error(f"API Error: {e.detail}")
except Exception as e:
    st.error(f"Error loading audit data: {e}")
    st.info("Make sure the backend API is running.")
