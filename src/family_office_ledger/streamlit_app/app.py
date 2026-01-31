"""Main Streamlit app entry point."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Atlas Ledger",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Atlas Family Office Ledger - Investment Accounting Platform"
    }
)


def init_session_state() -> None:
    """Initialize session state variables."""
    if "api_url" not in st.session_state:
        st.session_state.api_url = "http://localhost:8000"
    if "selected_entity_id" not in st.session_state:
        st.session_state.selected_entity_id = None


def main() -> None:
    """Main entry point for the Streamlit app."""
    init_session_state()

    # Apply custom styling
    from family_office_ledger.streamlit_app.styles import apply_custom_css

    apply_custom_css()

    # Sidebar
    st.sidebar.title("Atlas Ledger")
    st.sidebar.caption("Family Office Accounting")
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

    # Main content
    st.title("Welcome to Atlas Ledger")

    st.markdown(
        """
        <div style="
            background-color: #f7fafc;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #22324F;
            margin-bottom: 1.5rem;
        ">
            <p style="margin: 0; color: #2d3748; font-size: 1.1rem;">
                <strong>Atlas Family Office Ledger</strong> is a double-entry, multi-entity
                accounting system for managing family office finances.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navigation cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div style="
                background: white;
                padding: 1.25rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border: 1px solid #e2e8f0;
                height: 140px;
            ">
                <h4 style="margin: 0 0 0.5rem 0; color: #22324F;">Dashboard</h4>
                <p style="color: #718096; font-size: 0.875rem; margin: 0;">
                    Overview of net worth, assets, liabilities, and recent activity
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div style="
                background: white;
                padding: 1.25rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border: 1px solid #e2e8f0;
                height: 140px;
            ">
                <h4 style="margin: 0 0 0.5rem 0; color: #22324F;">Entities & Accounts</h4>
                <p style="color: #718096; font-size: 0.875rem; margin: 0;">
                    Manage LLCs, trusts, partnerships, and their accounts
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div style="
                background: white;
                padding: 1.25rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border: 1px solid #e2e8f0;
                height: 140px;
            ">
                <h4 style="margin: 0 0 0.5rem 0; color: #22324F;">Transactions & Reports</h4>
                <p style="color: #718096; font-size: 0.875rem; margin: 0;">
                    Record journal entries and generate financial reports
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # API Status
    from family_office_ledger.streamlit_app import api_client

    try:
        health = api_client.health_check()
        st.success(f"Connected to API (v{health.get('version', 'unknown')})")
    except Exception as e:
        st.error(f"Cannot connect to API at {st.session_state.api_url}: {e}")
        st.info(
            "Make sure the backend is running: "
            "`uv run uvicorn family_office_ledger.api.app:app`"
        )


if __name__ == "__main__":
    main()
