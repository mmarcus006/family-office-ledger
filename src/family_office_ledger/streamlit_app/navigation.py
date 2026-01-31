"""Shared navigation component for Atlas Ledger.

Provides:
- Top bar with entity/household filtering
- Consistent sidebar that doesn't collapse
- Page initialization helpers
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from family_office_ledger.streamlit_app import api_client


def init_page(title: str = "", wide: bool = True) -> None:
    """Initialize a page with proper configuration.

    Args:
        title: Page title to display
        wide: Use wide layout (default True)
    """
    # Import and apply styles
    from family_office_ledger.streamlit_app.app import init_session_state
    from family_office_ledger.streamlit_app.styles import apply_custom_css

    init_session_state()
    apply_custom_css()

    # Render top navigation bar with entity filter
    render_top_nav()

    # Display page title if provided
    if title:
        st.title(title)


def render_top_nav() -> None:
    """Render the top navigation bar with entity and household filters."""

    # Create a container for the top nav
    with st.container():
        cols = st.columns([3, 2, 2, 1])

        with cols[0]:
            # Entity filter
            try:
                entities = get_cached_entities()
                if entities:
                    entity_options = {"": "All Entities"}
                    entity_options.update({str(e["id"]): e["name"] for e in entities})

                    current_entity = st.session_state.get("selected_entity_id", "")

                    selected = st.selectbox(
                        "Entity",
                        options=list(entity_options.keys()),
                        format_func=lambda x: entity_options.get(x, "All Entities"),
                        index=list(entity_options.keys()).index(str(current_entity))
                              if str(current_entity) in entity_options else 0,
                        key="top_nav_entity",
                        label_visibility="collapsed",
                    )

                    if selected != st.session_state.get("selected_entity_id"):
                        st.session_state.selected_entity_id = selected if selected else None
                        st.rerun()
            except Exception:
                pass  # Silently fail if API not available

        with cols[1]:
            # Household filter
            try:
                households = get_cached_households()
                if households:
                    household_options = {"": "All Households"}
                    household_options.update({str(h["id"]): h["name"] for h in households})

                    current_household = st.session_state.get("selected_household_id", "")

                    selected_hh = st.selectbox(
                        "Household",
                        options=list(household_options.keys()),
                        format_func=lambda x: household_options.get(x, "All Households"),
                        index=list(household_options.keys()).index(str(current_household))
                              if str(current_household) in household_options else 0,
                        key="top_nav_household",
                        label_visibility="collapsed",
                    )

                    if selected_hh != st.session_state.get("selected_household_id"):
                        st.session_state.selected_household_id = selected_hh if selected_hh else None
                        st.rerun()
            except Exception:
                pass

        with cols[2]:
            # Quick date filter
            date_options = {
                "today": "Today",
                "mtd": "Month to Date",
                "qtd": "Quarter to Date",
                "ytd": "Year to Date",
            }
            st.selectbox(
                "Period",
                options=list(date_options.keys()),
                format_func=lambda x: date_options[x],
                key="top_nav_period",
                label_visibility="collapsed",
            )

        with cols[3]:
            # API status indicator
            try:
                api_client.health_check()
                st.markdown(
                    '<span style="color: #059669; font-size: 0.75rem;">● Connected</span>',
                    unsafe_allow_html=True
                )
            except Exception:
                st.markdown(
                    '<span style="color: #e11d48; font-size: 0.75rem;">● Disconnected</span>',
                    unsafe_allow_html=True
                )

    # Add separator
    st.markdown("---")


@st.cache_data(ttl=60)
def get_cached_entities() -> list[dict[str, Any]]:
    """Get cached list of entities."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


@st.cache_data(ttl=60)
def get_cached_households() -> list[dict[str, Any]]:
    """Get cached list of households."""
    try:
        return api_client.list_households()
    except Exception:
        return []


def get_selected_entity_id() -> str | None:
    """Get the currently selected entity ID."""
    return st.session_state.get("selected_entity_id")


def get_selected_household_id() -> str | None:
    """Get the currently selected household ID."""
    return st.session_state.get("selected_household_id")


def get_selected_period() -> str:
    """Get the currently selected time period."""
    return st.session_state.get("top_nav_period", "ytd")
