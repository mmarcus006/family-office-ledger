"""Transfer matching page for identifying inter-account transfers."""

from __future__ import annotations

import contextlib
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state

init_session_state()

st.title("💸 Transfer Matching")

st.markdown(
    """
Identify and match transfers between accounts across entities.
The system detects potential transfer pairs based on matching amounts and dates.
"""
)

entities: list[dict] = []
with contextlib.suppress(Exception):
    entities = api_client.list_entities()

if not entities:
    st.warning("No entities found. Create entities first in the Entities page.")
    st.stop()

tab_create, tab_manage = st.tabs(["Create Session", "Manage Sessions"])

with tab_create:
    st.subheader("Create Transfer Matching Session")

    entity_options = {str(e["id"]): e["name"] for e in entities}
    selected_entities = st.multiselect(
        "Select Entities (minimum 1)",
        options=list(entity_options.keys()),
        format_func=lambda x: entity_options.get(x, x),
        default=list(entity_options.keys())[:2]
        if len(entity_options) >= 2
        else list(entity_options.keys()),
        key="transfer_entities",
    )

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=90),
            key="transfer_start",
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            key="transfer_end",
        )

    date_tolerance = st.slider(
        "Date Tolerance (days)",
        min_value=0,
        max_value=14,
        value=3,
        help="Maximum days difference between transfer transactions",
    )

    if st.button("Create Session", type="primary", key="create_transfer_session"):
        if not selected_entities:
            st.error("Please select at least one entity")
        elif start_date > end_date:
            st.error("Start date must be before end date")
        else:
            try:
                session = api_client.create_transfer_session(
                    entity_ids=selected_entities,
                    start_date=start_date,
                    end_date=end_date,
                    date_tolerance_days=date_tolerance,
                )
                st.success(f"Session created: {session['id']}")
                st.session_state["active_transfer_session"] = session["id"]
                st.rerun()
            except api_client.APIError as e:
                st.error(f"API Error: {e.detail}")
            except Exception as e:
                st.error(f"Error creating session: {e}")

with tab_manage:
    st.subheader("Manage Transfer Session")

    session_id = st.text_input(
        "Session ID",
        value=st.session_state.get("active_transfer_session", ""),
        placeholder="Enter session UUID",
        key="transfer_session_id",
    )

    if session_id:
        try:
            session = api_client.get_transfer_session(session_id)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", session.get("status", "unknown"))
            with col2:
                st.metric(
                    "Date Tolerance", f"{session.get('date_tolerance_days', 0)} days"
                )
            with col3:
                entity_count = len(session.get("entity_ids", []))
                st.metric("Entities", entity_count)

            try:
                summary = api_client.get_transfer_summary(session_id)
                st.markdown("### Session Summary")
                cols = st.columns(5)
                with cols[0]:
                    st.metric("Total Matches", summary.get("total_matches", 0))
                with cols[1]:
                    st.metric("Pending", summary.get("pending_count", 0))
                with cols[2]:
                    st.metric("Confirmed", summary.get("confirmed_count", 0))
                with cols[3]:
                    st.metric("Rejected", summary.get("rejected_count", 0))
                with cols[4]:
                    st.metric(
                        "Confirmed Amount",
                        f"${summary.get('total_confirmed_amount', '0')}",
                    )
            except Exception:
                pass

            st.markdown("### Transfer Matches")

            status_filter = st.selectbox(
                "Filter by Status",
                options=["All", "pending", "confirmed", "rejected"],
                key="transfer_status_filter",
            )

            filter_status = None if status_filter == "All" else status_filter

            matches_response = api_client.list_transfer_matches(
                session_id=session_id,
                status=filter_status,
            )
            matches = matches_response.get("matches", [])

            if matches:
                accounts = {}
                try:
                    for acct in api_client.list_accounts():
                        accounts[acct["id"]] = acct["name"]
                except Exception:
                    pass

                for match in matches:
                    source_acct = accounts.get(
                        match.get("source_account_id"), "Unknown"
                    )
                    target_acct = accounts.get(
                        match.get("target_account_id"), "Unknown"
                    )

                    with st.expander(
                        f"${match.get('amount', '0')} | {source_acct} → {target_acct} "
                        f"| {match.get('status', 'unknown').upper()}",
                        expanded=match.get("status") == "pending",
                    ):
                        col_info, col_actions = st.columns([3, 1])

                        with col_info:
                            st.write(
                                f"**Transfer Date:** {match.get('transfer_date', 'N/A')}"
                            )
                            st.write(f"**Amount:** ${match.get('amount', '0')}")
                            st.write(f"**Source Account:** {source_acct}")
                            st.write(f"**Target Account:** {target_acct}")
                            st.write(
                                f"**Confidence:** {match.get('confidence_score', 0):.0%}"
                            )
                            if match.get("memo"):
                                st.write(f"**Memo:** {match['memo']}")

                        with col_actions:
                            match_id = match["id"]
                            current_status = match.get("status", "")

                            if current_status == "pending":
                                if st.button(
                                    "✅ Confirm",
                                    key=f"confirm_transfer_{match_id}",
                                    use_container_width=True,
                                ):
                                    try:
                                        api_client.confirm_transfer_match(
                                            session_id, match_id
                                        )
                                        st.rerun()
                                    except api_client.APIError as e:
                                        st.error(e.detail)

                                if st.button(
                                    "❌ Reject",
                                    key=f"reject_transfer_{match_id}",
                                    use_container_width=True,
                                ):
                                    try:
                                        api_client.reject_transfer_match(
                                            session_id, match_id
                                        )
                                        st.rerun()
                                    except api_client.APIError as e:
                                        st.error(e.detail)
                            else:
                                st.write(f"Status: **{current_status.upper()}**")

                df = pd.DataFrame(matches)
                display_cols = [
                    "transfer_date",
                    "amount",
                    "source_account_id",
                    "target_account_id",
                    "confidence_score",
                    "status",
                ]
                available_cols = [c for c in display_cols if c in df.columns]
                if available_cols:
                    st.markdown("### All Matches Table")
                    st.dataframe(
                        df[available_cols], use_container_width=True, hide_index=True
                    )
            else:
                st.info("No transfer matches found for this session.")

            st.markdown("---")
            if session.get("status") != "closed" and st.button(
                "🔒 Close Session", type="secondary"
            ):
                try:
                    api_client.close_transfer_session(session_id)
                    st.success("Session closed successfully")
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Error closing session: {e.detail}")

        except api_client.APIError as e:
            st.error(f"API Error: {e.detail}")
        except Exception as e:
            st.error(f"Error loading session: {e}")
    else:
        st.info("Enter a session ID to manage an existing transfer matching session.")
