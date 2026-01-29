"""Households management page."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    apply_custom_css,
    format_currency,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Households")


@st.cache_data(ttl=30)
def get_households(include_inactive: bool = False) -> list[dict[str, Any]]:
    """Fetch households with caching."""
    try:
        return api_client.list_households(include_inactive=include_inactive)
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities for dropdowns."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


tab_list, tab_create = st.tabs(["All Households", "Create New"])

with tab_list:
    try:
        include_inactive = st.checkbox("Include inactive households", value=False)
        households = get_households(include_inactive=include_inactive)

        if households:
            section_header("Household List")

            df = pd.DataFrame(households)
            display_cols = ["name", "is_active", "primary_contact_entity_id", "id"]
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[available_cols] if available_cols else df,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("<br>", unsafe_allow_html=True)
            section_header("Household Details")

            household_options = {str(h["id"]): h["name"] for h in households}
            selected_household_id = st.selectbox(
                "Select Household",
                options=list(household_options.keys()),
                format_func=lambda x: household_options.get(x, x),
            )

            if selected_household_id:
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.subheader("Members")
                    as_of_date = st.date_input(
                        "As of date", value=date.today(), key="members_as_of"
                    )
                    members = api_client.list_household_members(
                        selected_household_id, as_of=as_of_date
                    )

                    if members:
                        entities = get_entities()
                        entity_names = {str(e["id"]): e["name"] for e in entities}

                        for m in members:
                            entity_name = entity_names.get(
                                str(m.get("entity_id")), "Unknown"
                            )
                            role = m.get("role") or "Member"
                            display = m.get("display_name") or entity_name

                            mcol1, mcol2 = st.columns([4, 1])
                            with mcol1:
                                st.write(f"**{display}** ({role})")
                                st.caption(f"Entity: {entity_name}")
                            with mcol2:
                                if st.button(
                                    "Remove",
                                    key=f"remove_{m['id']}",
                                    type="secondary",
                                ):
                                    try:
                                        api_client.remove_household_member(
                                            selected_household_id, m["id"]
                                        )
                                        st.success("Member removed")
                                        get_households.clear()
                                        st.rerun()
                                    except api_client.APIError as e:
                                        st.error(f"Failed: {e.detail}")
                            st.divider()
                    else:
                        st.info("No members in this household.")

                    # Add member form
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("Add Member"):
                        entities = get_entities()
                        if entities:
                            entity_options = {str(e["id"]): e["name"] for e in entities}
                            new_entity_id = st.selectbox(
                                "Entity",
                                options=list(entity_options.keys()),
                                format_func=lambda x: entity_options.get(x, x),
                                key="add_member_entity",
                            )
                            new_role = st.text_input(
                                "Role (optional)", placeholder="e.g., Head, Spouse"
                            )
                            new_display_name = st.text_input("Display Name (optional)")

                            if st.button("Add Member", type="primary"):
                                try:
                                    api_client.add_household_member(
                                        household_id=selected_household_id,
                                        entity_id=new_entity_id,
                                        role=new_role if new_role else None,
                                        display_name=new_display_name
                                        if new_display_name
                                        else None,
                                    )
                                    st.success("Member added!")
                                    get_households.clear()
                                    st.rerun()
                                except api_client.APIError as e:
                                    st.error(f"Failed: {e.detail}")
                        else:
                            st.warning("No entities available. Create an entity first.")

                with col2:
                    st.subheader("Actions")

                    # Net Worth button
                    if st.button("View Net Worth", type="primary"):
                        st.session_state.show_net_worth = selected_household_id

                    # Delete button
                    if st.button("Delete Household", type="secondary"):
                        try:
                            api_client.delete_household(selected_household_id)
                            st.success("Household deleted")
                            get_households.clear()
                            st.rerun()
                        except api_client.APIError as e:
                            st.error(f"Failed: {e.detail}")

                # Show net worth if requested
                if st.session_state.get("show_net_worth") == selected_household_id:
                    st.markdown("<br>", unsafe_allow_html=True)
                    section_header("Look-Through Net Worth")

                    nw_as_of = st.date_input(
                        "As of date", value=date.today(), key="nw_as_of"
                    )
                    show_detail = st.checkbox("Show detail breakdown", value=False)

                    try:
                        result = api_client.get_household_net_worth(
                            selected_household_id, as_of=nw_as_of
                        )

                        col_a, col_l, col_n = st.columns(3)
                        with col_a:
                            st.metric(
                                "Total Assets",
                                format_currency(result.get("total_assets", 0)),
                            )
                        with col_l:
                            st.metric(
                                "Total Liabilities",
                                format_currency(result.get("total_liabilities", 0)),
                            )
                        with col_n:
                            st.metric(
                                "Net Worth",
                                format_currency(result.get("net_worth", 0)),
                            )

                        if show_detail and result.get("detail"):
                            st.markdown("<br>", unsafe_allow_html=True)
                            detail_df = pd.DataFrame(result["detail"])
                            st.dataframe(
                                detail_df,
                                use_container_width=True,
                                hide_index=True,
                            )
                    except api_client.APIError as e:
                        st.error(f"Failed to load net worth: {e.detail}")

        else:
            st.info("No households found. Create one in the 'Create New' tab.")
    except api_client.APIError as e:
        st.error(f"API Error: {e.detail}")
    except Exception as e:
        st.error(f"Error loading households: {e}")

with tab_create:
    section_header("Create New Household")

    with st.form("create_household_form"):
        name = st.text_input("Household Name", placeholder="e.g., Smith Family")

        entities = get_entities()
        primary_contact_id = None
        if entities:
            entity_options = {"": "-- None --"}
            entity_options.update({str(e["id"]): e["name"] for e in entities})
            primary_contact_id = st.selectbox(
                "Primary Contact (optional)",
                options=list(entity_options.keys()),
                format_func=lambda x: entity_options.get(x, x),
            )

        submitted = st.form_submit_button("Create Household", type="primary")

        if submitted:
            if not name.strip():
                st.error("Household name is required.")
            else:
                try:
                    result = api_client.create_household(
                        name=name.strip(),
                        primary_contact_entity_id=primary_contact_id
                        if primary_contact_id
                        else None,
                    )
                    st.success(f"Created household: {result.get('name')}")
                    get_households.clear()
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Failed to create household: {e.detail}")
                except Exception as e:
                    st.error(f"Error: {e}")
