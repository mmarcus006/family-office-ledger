"""Tax document generation page for Form 8949 and Schedule D."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    COLORS,
    apply_custom_css,
    format_currency,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Tax Documents")

st.markdown(
    f"""
    <div style="
        background-color: {COLORS["card_bg"]};
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid {COLORS["primary"]};
        margin-bottom: 1.5rem;
    ">
        Generate tax documents including <strong>Form 8949</strong> (Sales and Dispositions
        of Capital Assets) and <strong>Schedule D</strong> (Capital Gains and Losses) for your entities.
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities with caching."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_tax_summary(entity_id: str, tax_year: int) -> dict[str, Any]:
    """Fetch tax summary with caching."""
    try:
        return api_client.get_tax_summary(entity_id=entity_id, tax_year=tax_year)
    except Exception:
        return {}


@st.cache_data(ttl=30)
def get_schedule_d(entity_id: str, tax_year: int) -> dict[str, Any]:
    """Fetch Schedule D with caching."""
    try:
        return api_client.get_schedule_d(entity_id=entity_id, tax_year=tax_year)
    except Exception:
        return {}


# ============================================
# ENTITY AND YEAR SELECTION
# ============================================
entities = get_entities()

if not entities:
    st.warning("No entities found. Create an entity first to generate tax documents.")
    st.stop()

entity_options = {
    ent.get("name", "Unknown"): str(ent.get("id", "")) for ent in entities
}

col1, col2 = st.columns(2)

with col1:
    selected_entity_name = st.selectbox(
        "Select Entity",
        options=list(entity_options.keys()),
    )
    selected_entity_id = entity_options[selected_entity_name]

with col2:
    current_year = date.today().year
    tax_year = st.selectbox(
        "Tax Year",
        options=list(range(current_year, current_year - 10, -1)),
        index=1,  # Default to previous year
    )

st.markdown("<br>", unsafe_allow_html=True)

# ============================================
# TABS
# ============================================
tab_summary, tab_form8949, tab_scheduled = st.tabs(
    ["Tax Summary", "Form 8949", "Schedule D"]
)

try:
    # ============================================
    # TAB 1: TAX SUMMARY
    # ============================================
    with tab_summary:
        section_header(f"Tax Summary - {selected_entity_name} ({tax_year})")

        summary = get_tax_summary(selected_entity_id, tax_year)

        if summary:
            summary_data = summary.get("data", summary)

            # Key metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                short_term_gain = float(summary_data.get("short_term_gain", 0))
                st.metric(
                    label="Short-Term Gain/Loss",
                    value=format_currency(short_term_gain),
                    delta="< 1 year holding",
                    delta_color="off",
                    border=True,
                )

            with col2:
                long_term_gain = float(summary_data.get("long_term_gain", 0))
                st.metric(
                    label="Long-Term Gain/Loss",
                    value=format_currency(long_term_gain),
                    delta="> 1 year holding",
                    delta_color="off",
                    border=True,
                )

            with col3:
                total_gain = float(
                    summary_data.get("total_gain", short_term_gain + long_term_gain)
                )
                st.metric(
                    label="Total Net Gain/Loss",
                    value=format_currency(total_gain),
                    border=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Additional details
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(
                    f"""
                    <div style="
                        background-color: {COLORS["card_bg"]};
                        padding: 1.5rem;
                        border-radius: 8px;
                    ">
                        <h4 style="color: {COLORS["primary"]}; margin-top: 0;">Proceeds</h4>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 0.5rem 0;">Short-Term Proceeds</td>
                                <td style="text-align: right; font-weight: 600;">
                                    {format_currency(summary_data.get("short_term_proceeds", 0))}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 0.5rem 0;">Long-Term Proceeds</td>
                                <td style="text-align: right; font-weight: 600;">
                                    {format_currency(summary_data.get("long_term_proceeds", 0))}
                                </td>
                            </tr>
                            <tr style="border-top: 1px solid #e2e8f0;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Total Proceeds</td>
                                <td style="text-align: right; font-weight: 700;">
                                    {format_currency(summary_data.get("total_proceeds", 0))}
                                </td>
                            </tr>
                        </table>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f"""
                    <div style="
                        background-color: {COLORS["card_bg"]};
                        padding: 1.5rem;
                        border-radius: 8px;
                    ">
                        <h4 style="color: {COLORS["primary"]}; margin-top: 0;">Cost Basis</h4>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 0.5rem 0;">Short-Term Basis</td>
                                <td style="text-align: right; font-weight: 600;">
                                    {format_currency(summary_data.get("short_term_basis", 0))}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 0.5rem 0;">Long-Term Basis</td>
                                <td style="text-align: right; font-weight: 600;">
                                    {format_currency(summary_data.get("long_term_basis", 0))}
                                </td>
                            </tr>
                            <tr style="border-top: 1px solid #e2e8f0;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Total Basis</td>
                                <td style="text-align: right; font-weight: 700;">
                                    {format_currency(summary_data.get("total_basis", 0))}
                                </td>
                            </tr>
                        </table>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Transaction count
            st.markdown("<br>", unsafe_allow_html=True)
            txn_count = summary_data.get("transaction_count", 0)
            st.info(
                f"Total of {txn_count} reportable transactions for tax year {tax_year}."
            )
        else:
            st.info(f"No tax data available for {selected_entity_name} in {tax_year}.")

    # ============================================
    # TAB 2: FORM 8949
    # ============================================
    with tab_form8949:
        section_header(f"Form 8949 - {selected_entity_name} ({tax_year})")

        st.markdown(
            """
            Form 8949 reports sales and dispositions of capital assets.
            Download as CSV for import into tax software.
            """,
        )

        if st.button("Generate Form 8949 CSV", type="primary"):
            try:
                csv_data = api_client.get_form_8949_csv(
                    entity_id=selected_entity_id,
                    tax_year=tax_year,
                )

                if csv_data:
                    st.download_button(
                        label="Download Form 8949 CSV",
                        data=csv_data,
                        file_name=f"form_8949_{selected_entity_name.replace(' ', '_')}_{tax_year}.csv",
                        mime="text/csv",
                    )

                    # Preview the data
                    st.markdown("<br>", unsafe_allow_html=True)
                    section_header("Preview")

                    # Parse CSV for display
                    import io

                    df = pd.read_csv(io.StringIO(csv_data))
                    st.dataframe(
                        df, use_container_width=True, hide_index=True, height=400
                    )
                else:
                    st.warning("No Form 8949 data generated.")
            except api_client.APIError as e:
                st.error(f"Failed to generate Form 8949: {e.detail}")

        # Generate documents button
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="
                background-color: {COLORS["card_bg"]};
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            ">
                <strong>Form 8949 Categories:</strong>
                <ul style="margin-bottom: 0;">
                    <li><strong>Part I (Short-Term):</strong> Assets held 1 year or less</li>
                    <li><strong>Part II (Long-Term):</strong> Assets held more than 1 year</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ============================================
    # TAB 3: SCHEDULE D
    # ============================================
    with tab_scheduled:
        section_header(f"Schedule D - {selected_entity_name} ({tax_year})")

        st.markdown(
            """
            Schedule D summarizes capital gains and losses from Form 8949
            and calculates the net gain or loss.
            """,
        )

        schedule_d = get_schedule_d(selected_entity_id, tax_year)

        if schedule_d:
            sched_data = schedule_d.get("data", schedule_d)

            # Part I - Short-Term
            st.markdown(
                f"""
                <div style="
                    background-color: {COLORS["card_bg"]};
                    padding: 1.5rem;
                    border-radius: 8px;
                    margin-bottom: 1rem;
                ">
                    <h4 style="color: {COLORS["primary"]}; margin-top: 0;">
                        Part I - Short-Term Capital Gains and Losses
                    </h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background-color: #f1f5f9;">
                            <th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid #e2e8f0;">Description</th>
                            <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e2e8f0;">Proceeds</th>
                            <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e2e8f0;">Cost Basis</th>
                            <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e2e8f0;">Gain/Loss</th>
                        </tr>
                        <tr>
                            <td style="padding: 0.75rem;">Totals from Form 8949 Part I</td>
                            <td style="padding: 0.75rem; text-align: right;">{format_currency(sched_data.get("short_term_proceeds", 0))}</td>
                            <td style="padding: 0.75rem; text-align: right;">{format_currency(sched_data.get("short_term_basis", 0))}</td>
                            <td style="padding: 0.75rem; text-align: right; font-weight: 600;">{format_currency(sched_data.get("short_term_gain", 0))}</td>
                        </tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Part II - Long-Term
            st.markdown(
                f"""
                <div style="
                    background-color: {COLORS["card_bg"]};
                    padding: 1.5rem;
                    border-radius: 8px;
                    margin-bottom: 1rem;
                ">
                    <h4 style="color: {COLORS["primary"]}; margin-top: 0;">
                        Part II - Long-Term Capital Gains and Losses
                    </h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background-color: #f1f5f9;">
                            <th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid #e2e8f0;">Description</th>
                            <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e2e8f0;">Proceeds</th>
                            <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e2e8f0;">Cost Basis</th>
                            <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e2e8f0;">Gain/Loss</th>
                        </tr>
                        <tr>
                            <td style="padding: 0.75rem;">Totals from Form 8949 Part II</td>
                            <td style="padding: 0.75rem; text-align: right;">{format_currency(sched_data.get("long_term_proceeds", 0))}</td>
                            <td style="padding: 0.75rem; text-align: right;">{format_currency(sched_data.get("long_term_basis", 0))}</td>
                            <td style="padding: 0.75rem; text-align: right; font-weight: 600;">{format_currency(sched_data.get("long_term_gain", 0))}</td>
                        </tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Summary
            total_gain = float(sched_data.get("net_gain", 0))
            gain_color = COLORS["positive"] if total_gain >= 0 else COLORS["negative"]

            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, {gain_color} 0%, {"#1a9642" if total_gain >= 0 else "#c41e3a"} 100%);
                    padding: 1.5rem;
                    border-radius: 12px;
                    color: white;
                    text-align: center;
                ">
                    <div style="font-size: 0.9rem; text-transform: uppercase; opacity: 0.9;">
                        Net Capital Gain/Loss
                    </div>
                    <div style="font-size: 2.5rem; font-weight: 700;">
                        {format_currency(total_gain)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Carryover info if applicable
            carryover = sched_data.get("loss_carryover", 0)
            if carryover > 0:
                st.markdown("<br>", unsafe_allow_html=True)
                st.warning(
                    f"Capital loss carryover to next year: {format_currency(carryover)}"
                )
        else:
            st.info(
                f"No Schedule D data available for {selected_entity_name} in {tax_year}."
            )

        # Generate all documents
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Generate All Tax Documents")

        if st.button("Generate Tax Documents", type="primary", key="gen_all"):
            try:
                result = api_client.generate_tax_documents(
                    entity_id=selected_entity_id,
                    tax_year=tax_year,
                )
                st.success(
                    f"Tax documents generated for {selected_entity_name} ({tax_year})"
                )
                st.json(result)
            except api_client.APIError as e:
                st.error(f"Failed to generate documents: {e.detail}")

except api_client.APIError as e:
    st.error(f"API Error: {e.detail}")
except Exception as e:
    st.error(f"Error loading tax data: {e}")
    st.info("Make sure the backend API is running.")
