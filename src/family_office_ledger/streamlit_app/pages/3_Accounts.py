"""Accounts management page."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import apply_custom_css, section_header

init_session_state()
apply_custom_css()

ACCOUNT_TYPES = ["asset", "liability", "equity", "income", "expense"]
ACCOUNT_SUB_TYPES = [
    "checking",
    "savings",
    "credit_card",
    "brokerage",
    "ira",
    "roth_ira",
    "401k",
    "529",
    "real_estate",
    "private_equity",
    "venture_capital",
    "crypto",
    "cash",
    "loan",
    "other",
]

st.title("Accounts")


@st.cache_data(ttl=30)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities with caching."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_accounts(entity_id: str | None = None) -> list[dict[str, Any]]:
    """Fetch accounts with caching."""
    try:
        return api_client.list_accounts(entity_id=entity_id)
    except Exception:
        return []


entities = get_entities()

if not entities:
    st.warning("No entities found. Create an entity first on the Entities page.")
    st.stop()

entity_options = {str(e["id"]): e["name"] for e in entities}
current_entity = st.session_state.get("selected_entity_id")

selected_entity = st.selectbox(
    "Select Entity",
    options=list(entity_options.keys()),
    format_func=lambda x: entity_options.get(x, x),
    index=list(entity_options.keys()).index(str(current_entity))
    if current_entity and str(current_entity) in entity_options
    else 0,
)

if selected_entity != st.session_state.get("selected_entity_id"):
    st.session_state.selected_entity_id = selected_entity
    st.rerun()

st.markdown("---")

tab_list, tab_create = st.tabs(["All Accounts", "Create New"])

with tab_list:
    try:
        accounts = get_accounts(entity_id=selected_entity)
        if accounts:
            for acct_type in ACCOUNT_TYPES:
                type_accounts = [
                    a for a in accounts if a.get("account_type") == acct_type
                ]
                if type_accounts:
                    section_header(acct_type.title())
                    df = pd.DataFrame(type_accounts)
                    display_cols = ["name", "sub_type", "currency", "id"]
                    available_cols = [c for c in display_cols if c in df.columns]
                    st.dataframe(
                        df[available_cols] if available_cols else df,
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info(
                "No accounts found for this entity. Create one in the 'Create New' tab."
            )
    except api_client.APIError as e:
        st.error(f"API Error: {e.detail}")
    except Exception as e:
        st.error(f"Error loading accounts: {e}")

with tab_create:
    section_header("Create New Account")

    with st.form("create_account_form"):
        name = st.text_input("Account Name", placeholder="e.g., Operating Checking")
        account_type = st.selectbox(
            "Account Type",
            options=ACCOUNT_TYPES,
            format_func=str.title,
        )
        sub_type = st.selectbox(
            "Sub-Type",
            options=ACCOUNT_SUB_TYPES,
            format_func=lambda x: x.replace("_", " ").title(),
        )
        currency = st.text_input("Currency", value="USD")

        submitted = st.form_submit_button("Create Account", type="primary")

        if submitted:
            if not name.strip():
                st.error("Account name is required.")
            elif not selected_entity:
                st.error("Select an entity first.")
            else:
                try:
                    result = api_client.create_account(
                        name=name.strip(),
                        entity_id=selected_entity,
                        account_type=account_type,
                        sub_type=sub_type,
                        currency=currency.upper(),
                    )
                    st.success(f"Created account: {result.get('name')}")
                    get_accounts.clear()
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Failed to create account: {e.detail}")
                except Exception as e:
                    st.error(f"Error: {e}")
