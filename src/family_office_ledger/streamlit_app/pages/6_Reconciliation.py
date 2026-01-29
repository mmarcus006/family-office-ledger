"""Reconciliation page for matching imported statements with ledger transactions."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import apply_custom_css, section_header

init_session_state()
apply_custom_css()

st.title("Reconciliation")

st.markdown(
    """
    <div style="
        background-color: #f7fafc;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        border-left: 4px solid #22324F;
    ">
        <p style="margin: 0; color: #2d3748;">
            Reconcile bank/broker statements against ledger transactions.
            Upload a statement file and match imported transactions with existing ledger entries.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def get_accounts() -> list[dict[str, Any]]:
    """Fetch accounts with caching."""
    try:
        return api_client.list_accounts()
    except Exception:
        return []


accounts = get_accounts()

if not accounts:
    st.warning("No accounts found. Create accounts first in the Accounts page.")
    st.stop()

tab_create, tab_manage = st.tabs(["Create Session", "Manage Sessions"])

with tab_create:
    section_header("Create Reconciliation Session")

    account_options = {
        str(a["id"]): f"{a['name']} ({a['account_type']})" for a in accounts
    }
    selected_account = st.selectbox(
        "Select Account",
        options=list(account_options.keys()),
        format_func=lambda x: account_options.get(x, str(x)),
        key="recon_account",
    )

    file_path = st.text_input(
        "Statement File Path",
        placeholder="/path/to/statement.csv",
        help="Path to the statement file on the server",
    )

    file_format = st.selectbox(
        "File Format",
        options=["csv", "ofx", "qfx"],
        index=0,
    )

    if st.button("Create Session", type="primary", key="create_recon_session"):
        if not file_path:
            st.error("Please enter a file path")
        else:
            try:
                session = api_client.create_reconciliation_session(
                    account_id=selected_account,
                    file_path=file_path,
                    file_format=file_format,
                )
                st.success(f"Session created: {session['id']}")
                st.session_state["active_recon_session"] = session["id"]
                st.rerun()
            except api_client.APIError as e:
                st.error(f"API Error: {e.detail}")
            except Exception as e:
                st.error(f"Error creating session: {e}")

with tab_manage:
    section_header("Manage Reconciliation Session")

    session_id = st.text_input(
        "Session ID",
        value=st.session_state.get("active_recon_session", ""),
        placeholder="Enter session UUID",
        key="recon_session_id",
    )

    if session_id:
        try:
            session = api_client.get_reconciliation_session(session_id)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", session.get("status", "unknown"), border=True)
            with col2:
                st.metric("File", session.get("file_name", "N/A"), border=True)
            with col3:
                st.metric("Format", session.get("file_format", "N/A"), border=True)

            try:
                summary = api_client.get_reconciliation_summary(session_id)
                st.markdown("<br>", unsafe_allow_html=True)
                section_header("Session Summary")
                cols = st.columns(5)
                with cols[0]:
                    st.metric(
                        "Total Imported", summary.get("total_imported", 0), border=True
                    )
                with cols[1]:
                    st.metric("Pending", summary.get("pending", 0), border=True)
                with cols[2]:
                    st.metric("Confirmed", summary.get("confirmed", 0), border=True)
                with cols[3]:
                    st.metric("Rejected", summary.get("rejected", 0), border=True)
                with cols[4]:
                    match_rate = summary.get("match_rate", 0)
                    st.metric(
                        "Match Rate",
                        f"{match_rate:.1%}" if match_rate else "0%",
                        border=True,
                    )
            except Exception:
                pass

            st.markdown("<br>", unsafe_allow_html=True)
            section_header("Matches")

            status_filter = st.selectbox(
                "Filter by Status",
                options=["All", "pending", "confirmed", "rejected", "skipped"],
                key="recon_status_filter",
            )

            filter_status = None if status_filter == "All" else status_filter

            matches_response = api_client.list_reconciliation_matches(
                session_id=session_id,
                status=filter_status,
                limit=100,
            )
            matches = matches_response.get("matches", [])

            if matches:
                for match in matches:
                    status = match.get("status", "unknown")
                    status_color = {
                        "pending": "#ff8700",
                        "confirmed": "#21c354",
                        "rejected": "#ff2b2b",
                        "skipped": "#718096",
                    }.get(status, "#718096")

                    with st.expander(
                        f"Match: {match.get('imported_description', 'N/A')[:50]}... "
                        f"| ${match.get('imported_amount', '0')} "
                        f"| {status.upper()}",
                        expanded=status == "pending",
                    ):
                        col_info, col_actions = st.columns([3, 1])

                        with col_info:
                            st.write(f"**Date:** {match.get('imported_date', 'N/A')}")
                            st.write(
                                f"**Amount:** ${match.get('imported_amount', '0')}"
                            )
                            st.write(
                                f"**Description:** {match.get('imported_description', 'N/A')}"
                            )
                            if match.get("suggested_ledger_txn_id"):
                                st.write(
                                    f"**Suggested Ledger Txn:** "
                                    f"{match['suggested_ledger_txn_id']}"
                                )
                            st.write(
                                f"**Confidence:** {match.get('confidence_score', 0):.0%}"
                            )

                        with col_actions:
                            match_id = match["id"]
                            current_status = match.get("status", "")

                            if current_status == "pending":
                                if st.button(
                                    "Confirm",
                                    key=f"confirm_{match_id}",
                                    use_container_width=True,
                                ):
                                    try:
                                        api_client.confirm_reconciliation_match(
                                            session_id, match_id
                                        )
                                        st.rerun()
                                    except api_client.APIError as e:
                                        st.error(e.detail)

                                if st.button(
                                    "Reject",
                                    key=f"reject_{match_id}",
                                    use_container_width=True,
                                ):
                                    try:
                                        api_client.reject_reconciliation_match(
                                            session_id, match_id
                                        )
                                        st.rerun()
                                    except api_client.APIError as e:
                                        st.error(e.detail)

                                if st.button(
                                    "Skip",
                                    key=f"skip_{match_id}",
                                    use_container_width=True,
                                ):
                                    try:
                                        api_client.skip_reconciliation_match(
                                            session_id, match_id
                                        )
                                        st.rerun()
                                    except api_client.APIError as e:
                                        st.error(e.detail)
                            else:
                                st.markdown(
                                    f"""
                                    <div style="
                                        background-color: {status_color}20;
                                        color: {status_color};
                                        padding: 0.5rem;
                                        border-radius: 4px;
                                        text-align: center;
                                        font-weight: 600;
                                    ">{current_status.upper()}</div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                df = pd.DataFrame(matches)
                display_cols = [
                    "imported_date",
                    "imported_amount",
                    "imported_description",
                    "confidence_score",
                    "status",
                ]
                available_cols = [c for c in display_cols if c in df.columns]
                if available_cols:
                    st.markdown("<br>", unsafe_allow_html=True)
                    section_header("All Matches Table")
                    st.dataframe(
                        df[available_cols], use_container_width=True, hide_index=True
                    )
            else:
                st.info("No matches found for this session.")

            st.markdown("---")
            if session.get("status") != "closed" and st.button(
                "Close Session", type="secondary"
            ):
                try:
                    api_client.close_reconciliation_session(session_id)
                    st.success("Session closed successfully")
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Error closing session: {e.detail}")

        except api_client.APIError as e:
            st.error(f"API Error: {e.detail}")
        except Exception as e:
            st.error(f"Error loading session: {e}")
    else:
        st.info("Enter a session ID to manage an existing reconciliation session.")
