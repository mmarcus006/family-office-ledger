"""Entities management page."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state

init_session_state()

ENTITY_TYPES = ["llc", "trust", "partnership", "individual", "holding_co"]

st.title("🏢 Entities")

tab_list, tab_create = st.tabs(["All Entities", "Create New"])

with tab_list:
    try:
        entities = api_client.list_entities()
        if entities:
            df = pd.DataFrame(entities)
            display_cols = ["name", "entity_type", "fiscal_year_end", "is_active", "id"]
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[available_cols] if available_cols else df,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.subheader("Select Entity for Other Pages")
            entity_options = {str(e["id"]): e["name"] for e in entities}
            entity_options[""] = "-- Select Entity --"

            current = st.session_state.get("selected_entity_id", "")
            selected = st.selectbox(
                "Active Entity",
                options=[""] + list(entity_options.keys())[:-1],
                format_func=lambda x: entity_options.get(x, x)
                if x
                else "-- Select Entity --",
                index=0
                if not current
                else (
                    list(entity_options.keys()).index(str(current))
                    if str(current) in entity_options
                    else 0
                ),
            )
            if selected != st.session_state.get("selected_entity_id"):
                st.session_state.selected_entity_id = selected if selected else None
                st.rerun()
        else:
            st.info("No entities found. Create one in the 'Create New' tab.")
    except api_client.APIError as e:
        st.error(f"API Error: {e.detail}")
    except Exception as e:
        st.error(f"Error loading entities: {e}")

with tab_create:
    st.subheader("Create New Entity")

    with st.form("create_entity_form"):
        name = st.text_input("Entity Name", placeholder="e.g., Miller Family LLC")
        entity_type = st.selectbox(
            "Entity Type",
            options=ENTITY_TYPES,
            format_func=lambda x: x.replace("_", " ").title(),
        )
        fiscal_year_end = st.date_input(
            "Fiscal Year End",
            value=date.today().replace(month=12, day=31),
        )

        submitted = st.form_submit_button("Create Entity", type="primary")

        if submitted:
            if not name.strip():
                st.error("Entity name is required.")
            else:
                try:
                    result = api_client.create_entity(
                        name=name.strip(),
                        entity_type=entity_type,
                        fiscal_year_end=fiscal_year_end,
                    )
                    st.success(f"✅ Created entity: {result.get('name')}")
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Failed to create entity: {e.detail}")
                except Exception as e:
                    st.error(f"Error: {e}")
