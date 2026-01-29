"""Currency management page for exchange rates and conversions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    COLORS,
    apply_custom_css,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Currency Management")

# Common currency codes
COMMON_CURRENCIES = [
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CHF",
    "CAD",
    "AUD",
    "CNY",
    "HKD",
    "SGD",
    "INR",
    "MXN",
    "BRL",
    "KRW",
    "NZD",
]


@st.cache_data(ttl=60)
def get_exchange_rates(
    from_currency: str | None = None,
    to_currency: str | None = None,
) -> dict[str, Any]:
    """Fetch exchange rates with caching."""
    try:
        return api_client.list_exchange_rates(
            from_currency=from_currency,
            to_currency=to_currency,
        )
    except Exception:
        return {}


def clear_rates_cache() -> None:
    """Clear the exchange rates cache."""
    get_exchange_rates.clear()


# ============================================
# TABS LAYOUT
# ============================================
tab_rates, tab_add, tab_convert = st.tabs(
    ["Exchange Rates", "Add Rate", "Currency Converter"]
)

# ============================================
# TAB 1: EXCHANGE RATES LIST
# ============================================
with tab_rates:
    section_header("Current Exchange Rates")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        from_filter = st.selectbox(
            "From Currency",
            options=["All"] + COMMON_CURRENCIES,
            index=0,
            key="rates_from_filter",
        )
    with col2:
        to_filter = st.selectbox(
            "To Currency",
            options=["All"] + COMMON_CURRENCIES,
            index=0,
            key="rates_to_filter",
        )

    from_currency = None if from_filter == "All" else from_filter
    to_currency = None if to_filter == "All" else to_filter

    try:
        rates = get_exchange_rates(from_currency=from_currency, to_currency=to_currency)

        if rates:
            rates_list = rates.get("rates", rates.get("data", []))
            if isinstance(rates_list, list) and rates_list:
                display_data = []
                for rate in rates_list:
                    display_data.append(
                        {
                            "ID": str(rate.get("id", ""))[:8] + "...",
                            "From": rate.get("from_currency", "-"),
                            "To": rate.get("to_currency", "-"),
                            "Rate": str(rate.get("rate", "-")),
                            "Date": str(rate.get("effective_date", "-"))[:10],
                            "Source": rate.get("source", "manual"),
                        }
                    )

                df = pd.DataFrame(display_data)
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    height=400,
                )

                # Delete rate section
                st.markdown("<br>", unsafe_allow_html=True)
                section_header("Delete Rate")

                rate_ids = [str(r.get("id", "")) for r in rates_list if r.get("id")]
                if rate_ids:
                    col_del1, col_del2 = st.columns([3, 1])
                    with col_del1:
                        delete_id = st.selectbox(
                            "Select rate to delete",
                            options=rate_ids,
                            format_func=lambda x: f"Rate {x[:8]}...",
                        )
                    with col_del2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Delete Rate", type="secondary"):
                            try:
                                api_client.delete_exchange_rate(delete_id)
                                st.success("Exchange rate deleted successfully!")
                                clear_rates_cache()
                                st.rerun()
                            except api_client.APIError as e:
                                st.error(f"Failed to delete: {e.detail}")
            else:
                st.info("No exchange rates found.")
        else:
            st.info("No exchange rates available. Add one using the 'Add Rate' tab.")

    except api_client.APIError as e:
        st.error(f"API Error: {e.detail}")
    except Exception as e:
        st.error(f"Error loading exchange rates: {e}")

# ============================================
# TAB 2: ADD EXCHANGE RATE
# ============================================
with tab_add:
    section_header("Add New Exchange Rate")

    with st.form("add_rate_form"):
        col1, col2 = st.columns(2)

        with col1:
            from_currency_input = st.selectbox(
                "From Currency",
                options=COMMON_CURRENCIES,
                index=0,
                key="add_from_currency",
            )

        with col2:
            to_currency_input = st.selectbox(
                "To Currency",
                options=COMMON_CURRENCIES,
                index=1,
                key="add_to_currency",
            )

        rate_value = st.text_input(
            "Exchange Rate",
            value="1.0000",
            help="Enter the exchange rate (e.g., 1.2345 means 1 FROM = 1.2345 TO)",
        )

        effective_date = st.date_input(
            "Effective Date",
            value=date.today(),
            key="add_effective_date",
        )

        source = st.selectbox(
            "Source",
            options=["manual", "api", "bank", "broker"],
            index=0,
        )

        submitted = st.form_submit_button("Add Exchange Rate", type="primary")

        if submitted:
            # Validate inputs
            if from_currency_input == to_currency_input:
                st.error("From and To currencies must be different.")
            else:
                try:
                    # Validate rate is a valid decimal
                    Decimal(rate_value)

                    if not isinstance(effective_date, date):
                        effective_date = date.today()

                    result = api_client.add_exchange_rate(
                        from_currency=from_currency_input,
                        to_currency=to_currency_input,
                        rate=rate_value,
                        effective_date=effective_date,
                        source=source,
                    )
                    st.success(
                        f"Exchange rate added: 1 {from_currency_input} = "
                        f"{rate_value} {to_currency_input}"
                    )
                    clear_rates_cache()
                except ValueError:
                    st.error("Please enter a valid numeric rate.")
                except api_client.APIError as e:
                    st.error(f"Failed to add rate: {e.detail}")

    # Quick rate display
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="
            background-color: {COLORS["card_bg"]};
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {COLORS["primary"]};
        ">
            <strong>Tip:</strong> Exchange rates are used for multi-currency
            portfolio valuations and currency conversions throughout the system.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================
# TAB 3: CURRENCY CONVERTER
# ============================================
with tab_convert:
    section_header("Currency Converter")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        amount_input = st.text_input(
            "Amount",
            value="100.00",
            key="convert_amount",
        )

    with col2:
        convert_from = st.selectbox(
            "From Currency",
            options=COMMON_CURRENCIES,
            index=0,
            key="convert_from",
        )

    with col3:
        convert_to = st.selectbox(
            "To Currency",
            options=COMMON_CURRENCIES,
            index=1,
            key="convert_to",
        )

    as_of_date = st.date_input(
        "As of Date",
        value=date.today(),
        key="convert_date",
    )

    if not isinstance(as_of_date, date):
        as_of_date = date.today()

    if st.button("Convert", type="primary", key="convert_btn"):
        if convert_from == convert_to:
            st.warning("From and To currencies are the same.")
            st.metric(label="Result", value=f"{amount_input} {convert_to}")
        else:
            try:
                result = api_client.convert_currency(
                    amount=amount_input,
                    from_currency=convert_from,
                    to_currency=convert_to,
                    as_of_date=as_of_date,
                )

                result_data = result.get("data", result)
                converted_amount = result_data.get("converted_amount", "N/A")
                rate_used = result_data.get("rate", "N/A")

                col_res1, col_res2 = st.columns(2)

                with col_res1:
                    st.markdown(
                        f"""
                        <div style="
                            background: linear-gradient(135deg, {COLORS["primary"]} 0%, #1a2744 100%);
                            padding: 1.5rem;
                            border-radius: 12px;
                            color: white;
                            text-align: center;
                        ">
                            <div style="font-size: 0.875rem; opacity: 0.9;">Converted Amount</div>
                            <div style="font-size: 2rem; font-weight: 700;">{converted_amount} {convert_to}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col_res2:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: {COLORS["card_bg"]};
                            padding: 1.5rem;
                            border-radius: 12px;
                            text-align: center;
                        ">
                            <div style="font-size: 0.875rem; color: {COLORS["text_muted"]};">Exchange Rate</div>
                            <div style="font-size: 1.5rem; font-weight: 600; color: {COLORS["text"]};">
                                1 {convert_from} = {rate_used} {convert_to}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            except api_client.APIError as e:
                st.error(f"Conversion failed: {e.detail}")
                st.info(
                    "Make sure an exchange rate exists for this currency pair "
                    "on or before the selected date."
                )
            except Exception as e:
                st.error(f"Error: {e}")
