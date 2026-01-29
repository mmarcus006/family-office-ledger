"""Main Streamlit app entry point."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Atlas Ledger",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    if "api_url" not in st.session_state:
        st.session_state.api_url = "http://localhost:8000"
    if "selected_entity_id" not in st.session_state:
        st.session_state.selected_entity_id = None


def main() -> None:
    init_session_state()

    st.sidebar.title("Atlas Ledger")
    st.sidebar.markdown("---")

    with st.sidebar.expander("Settings", expanded=False):
        api_url = st.text_input(
            "API URL",
            value=st.session_state.api_url,
            key="api_url_input",
        )
        if api_url != st.session_state.api_url:
            st.session_state.api_url = api_url
            st.rerun()

    st.title("Welcome to Atlas Ledger")
    st.markdown(
        """
        **Atlas Family Office Ledger** is a double-entry, multi-entity accounting
        system for managing family office finances.
        
        Use the sidebar to navigate:
        - **Dashboard** - Overview of net worth and recent activity
        - **Entities** - Manage LLCs, trusts, and other entities
        - **Accounts** - Manage accounts for each entity
        - **Transactions** - Record journal entries
        - **Reports** - Generate financial reports
        """
    )

    from family_office_ledger.streamlit_app import api_client

    try:
        health = api_client.health_check()
        st.success(f"✅ Connected to API (v{health.get('version', 'unknown')})")
    except Exception as e:
        st.error(f"❌ Cannot connect to API at {st.session_state.api_url}: {e}")
        st.info(
            "Make sure the backend is running: `uv run uvicorn family_office_ledger.api.app:app`"
        )


if __name__ == "__main__":
    main()
