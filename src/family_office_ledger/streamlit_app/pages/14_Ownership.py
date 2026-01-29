"""Ownership graph management page."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
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

st.title("Ownership Graph")


@st.cache_data(ttl=30)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities for dropdowns."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_ownership_edges(as_of: date | None = None) -> list[dict[str, Any]]:
    """Fetch ownership edges."""
    try:
        return api_client.list_ownership_edges(as_of=as_of)
    except Exception:
        return []


tab_graph, tab_create, tab_look_through = st.tabs(
    ["Ownership Graph", "Create Edge", "Look-Through"]
)

with tab_graph:
    section_header("Ownership Edges")

    as_of_date = st.date_input("As of date", value=date.today(), key="graph_as_of")
    edges = get_ownership_edges(as_of=as_of_date)
    entities = get_entities()
    entity_names = {str(e["id"]): e["name"] for e in entities}

    if edges:
        st.markdown("**Current Ownership Structure:**")

        for edge in edges:
            owner_name = entity_names.get(
                str(edge.get("owner_entity_id")), str(edge.get("owner_entity_id"))
            )
            owned_name = entity_names.get(
                str(edge.get("owned_entity_id")), str(edge.get("owned_entity_id"))
            )
            fraction = edge.get("ownership_fraction", "0")
            try:
                pct = float(Decimal(fraction) * 100)
            except Exception:
                pct = 0.0

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{owner_name}** ──[{pct:.1f}%]──▶ **{owned_name}**")
                st.caption(
                    f"Type: {edge.get('ownership_type', 'beneficial')} | "
                    f"Effective: {edge.get('effective_start_date')} - "
                    f"{edge.get('effective_end_date') or 'present'}"
                )
            with col2:
                if st.button("Delete", key=f"del_{edge['id']}", type="secondary"):
                    try:
                        api_client.delete_ownership_edge(edge["id"])
                        st.success("Edge deleted")
                        get_ownership_edges.clear()
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Failed: {e.detail}")
            st.divider()

        # Show as table too
        with st.expander("View as Table"):
            df = pd.DataFrame(edges)
            df["owner"] = df["owner_entity_id"].apply(
                lambda x: entity_names.get(str(x), str(x))
            )
            df["owned"] = df["owned_entity_id"].apply(
                lambda x: entity_names.get(str(x), str(x))
            )
            display_cols = [
                "owner",
                "owned",
                "ownership_fraction",
                "ownership_type",
                "effective_start_date",
                "id",
            ]
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[available_cols] if available_cols else df,
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No ownership edges found. Create one in the 'Create Edge' tab.")

    # Ownership Tree section
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Ownership Tree")
    st.caption("View the effective ownership structure from a root entity")

    if entities:
        entity_options = {str(e["id"]): e["name"] for e in entities}
        selected_entity = st.selectbox(
            "Select Root Entity",
            options=list(entity_options.keys()),
            format_func=lambda x: entity_options.get(x, x),
            key="tree_entity",
        )

        if selected_entity:
            tree_as_of = st.date_input(
                "As of date", value=date.today(), key="tree_as_of"
            )

            if st.button("Show Tree", type="primary"):
                try:
                    tree = api_client.get_ownership_tree(
                        selected_entity, as_of=tree_as_of
                    )

                    if tree.get("effective_ownerships"):
                        st.markdown("**Effective Ownership Allocation:**")
                        for item in tree["effective_ownerships"]:
                            entity_name = entity_names.get(
                                str(item.get("entity_id")),
                                str(item.get("entity_id")),
                            )
                            path = item.get("path", [])
                            indent = "    " * (len(path) - 1) if path else ""
                            fraction = item.get("effective_fraction", "0")
                            try:
                                pct = float(Decimal(fraction) * 100)
                            except Exception:
                                pct = 0.0
                            st.text(f"{indent}{entity_name}: {pct:.1f}%")
                    else:
                        st.info("No downstream ownership found for this entity.")
                except api_client.APIError as e:
                    st.error(f"Failed to load tree: {e.detail}")
    else:
        st.warning("No entities available.")

with tab_create:
    section_header("Create Ownership Edge")

    entities = get_entities()
    if not entities:
        st.warning("No entities available. Create entities first.")
    else:
        with st.form("create_edge_form"):
            entity_options = {str(e["id"]): e["name"] for e in entities}

            owner_id = st.selectbox(
                "Owner Entity (the one that owns)",
                options=list(entity_options.keys()),
                format_func=lambda x: entity_options.get(x, x),
                key="owner_select",
            )

            owned_id = st.selectbox(
                "Owned Entity (the one being owned)",
                options=list(entity_options.keys()),
                format_func=lambda x: entity_options.get(x, x),
                key="owned_select",
            )

            col1, col2 = st.columns(2)
            with col1:
                fraction_pct = st.number_input(
                    "Ownership Percentage",
                    min_value=0.0,
                    max_value=100.0,
                    value=100.0,
                    step=0.1,
                    help="Enter as percentage (e.g., 50 for 50%)",
                )
            with col2:
                ownership_type = st.selectbox(
                    "Ownership Type",
                    options=["beneficial", "voting", "economic"],
                )

            start_date = st.date_input("Effective Start Date", value=date.today())

            submitted = st.form_submit_button("Create Edge", type="primary")

            if submitted:
                if owner_id == owned_id:
                    st.error("Owner and owned entity cannot be the same.")
                elif fraction_pct <= 0:
                    st.error("Ownership percentage must be greater than 0.")
                else:
                    try:
                        fraction_decimal = str(Decimal(str(fraction_pct)) / 100)
                        result = api_client.create_ownership_edge(
                            owner_id=owner_id,
                            owned_id=owned_id,
                            fraction=fraction_decimal,
                            start_date=start_date,
                            ownership_type=ownership_type,
                        )
                        owner_name = entity_options.get(owner_id, owner_id)
                        owned_name = entity_options.get(owned_id, owned_id)
                        st.success(
                            f"Created: {owner_name} --[{fraction_pct:.1f}%]--> {owned_name}"
                        )
                        get_ownership_edges.clear()
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Failed: {e.detail}")
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab_look_through:
    section_header("Look-Through Net Worth")
    st.caption(
        "Calculate an entity's net worth including weighted value of owned entities"
    )

    entities = get_entities()
    if not entities:
        st.warning("No entities available.")
    else:
        entity_options = {str(e["id"]): e["name"] for e in entities}
        selected_entity = st.selectbox(
            "Select Entity",
            options=list(entity_options.keys()),
            format_func=lambda x: entity_options.get(x, x),
            key="lt_entity",
        )

        lt_as_of = st.date_input("As of date", value=date.today(), key="lt_as_of")
        show_detail = st.checkbox("Show detail breakdown", value=False, key="lt_detail")

        if st.button("Calculate Look-Through Net Worth", type="primary"):
            try:
                result = api_client.get_entity_look_through_net_worth(
                    selected_entity, as_of=lt_as_of
                )

                st.markdown("<br>", unsafe_allow_html=True)

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
                    section_header("Detail Breakdown")
                    detail_df = pd.DataFrame(result["detail"])
                    st.dataframe(
                        detail_df,
                        use_container_width=True,
                        hide_index=True,
                    )

            except api_client.APIError as e:
                st.error(f"Failed: {e.detail}")
            except Exception as e:
                st.error(f"Error: {e}")
