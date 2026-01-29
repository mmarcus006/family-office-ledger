"""QSBS (Qualified Small Business Stock) tracking page."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    COLORS,
    apply_custom_css,
    format_currency,
    get_plotly_layout,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("QSBS Tracking")

st.markdown(
    f"""
    <div style="
        background-color: {COLORS["card_bg"]};
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid {COLORS["accent"]};
        margin-bottom: 1.5rem;
    ">
        <strong>Qualified Small Business Stock (QSBS)</strong> can qualify for
        significant tax exclusions under IRC Section 1202. Track your eligible
        securities and potential tax benefits here.
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
def get_qsbs_securities() -> list[dict[str, Any]]:
    """Fetch QSBS securities with caching."""
    try:
        return api_client.list_qsbs_securities()
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_qsbs_summary(
    entity_ids: list[str] | None,
    as_of_date: date | None,
) -> dict[str, Any]:
    """Fetch QSBS summary with caching."""
    try:
        return api_client.get_qsbs_summary(entity_ids=entity_ids, as_of_date=as_of_date)
    except Exception:
        return {}


def clear_qsbs_cache() -> None:
    """Clear QSBS caches."""
    get_qsbs_securities.clear()
    get_qsbs_summary.clear()


# ============================================
# SIDEBAR FILTERS
# ============================================
with st.sidebar:
    st.subheader("Filters")

    as_of = st.date_input("As of Date", value=date.today())
    if not isinstance(as_of, date):
        as_of = date.today()

    entities = get_entities()
    entity_options = {
        ent.get("name", "Unknown"): str(ent.get("id", "")) for ent in entities
    }

    selected_entities = st.multiselect(
        "Entities",
        options=list(entity_options.keys()),
        default=[],
        help="Leave empty to include all entities",
    )

    entity_ids = (
        [entity_options[name] for name in selected_entities]
        if selected_entities
        else None
    )

try:
    # ============================================
    # QSBS SUMMARY
    # ============================================
    summary = get_qsbs_summary(entity_ids, as_of)

    if summary:
        summary_data = summary.get("data", summary)

        qualified_value = float(summary_data.get("qualified_value", 0))
        pending_value = float(summary_data.get("pending_value", 0))
        total_value = float(
            summary_data.get("total_value", qualified_value + pending_value)
        )
        potential_exclusion = float(summary_data.get("potential_exclusion", 0))
        qualified_count = summary_data.get("qualified_count", 0)
        pending_count = summary_data.get("pending_count", 0)

        # Main summary card
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {COLORS["positive"]} 0%, #1a9642 100%);
                padding: 2rem;
                border-radius: 12px;
                color: white;
                margin-bottom: 1.5rem;
            ">
                <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.9;">
                    Potential Tax Exclusion
                </div>
                <div style="font-size: 3rem; font-weight: 700; margin: 0.5rem 0;">
                    {format_currency(potential_exclusion)}
                </div>
                <div style="font-size: 0.875rem; opacity: 0.8;">
                    Based on qualified QSBS holdings
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Qualified Value",
                value=format_currency(qualified_value),
                border=True,
            )

        with col2:
            st.metric(
                label="Pending Value", value=format_currency(pending_value), border=True
            )

        with col3:
            st.metric(
                label="Qualified Securities", value=str(qualified_count), border=True
            )

        with col4:
            st.metric(label="Pending Securities", value=str(pending_count), border=True)

        # Pie chart of qualified vs pending
        if total_value > 0:
            st.markdown("<br>", unsafe_allow_html=True)

            fig_pie = go.Figure(
                data=[
                    go.Pie(
                        labels=["Qualified QSBS", "Pending Qualification"],
                        values=[qualified_value, pending_value],
                        hole=0.4,
                        marker={"colors": [COLORS["positive"], COLORS["warning"]]},
                        textinfo="label+percent",
                        textposition="outside",
                    )
                ]
            )
            fig_pie.update_layout(
                **get_plotly_layout("QSBS Status Breakdown"),
                showlegend=False,
                height=300,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================
    # TABS
    # ============================================
    tab_securities, tab_manage = st.tabs(["Securities List", "Manage Eligibility"])

    # ============================================
    # TAB 1: SECURITIES LIST
    # ============================================
    with tab_securities:
        section_header("QSBS-Eligible Securities")

        securities = get_qsbs_securities()

        if securities:
            securities_list = (
                securities
                if isinstance(securities, list)
                else securities.get("data", [])
            )

            if securities_list:
                display_data = []
                for sec in securities_list:
                    qual_date = sec.get("qualification_date", "")
                    if qual_date:
                        qual_date_str = str(qual_date)[:10]
                        # Calculate holding period
                        try:
                            qual_dt = date.fromisoformat(qual_date_str)
                            holding_days = (as_of - qual_dt).days
                            holding_years = holding_days / 365.25
                            holding_str = f"{holding_years:.1f} years"
                            # 5 years required for full QSBS exclusion
                            status = "Qualified" if holding_years >= 5 else "Pending"
                        except Exception:
                            holding_str = "N/A"
                            status = "Unknown"
                    else:
                        qual_date_str = "-"
                        holding_str = "N/A"
                        status = "Unknown"

                    display_data.append(
                        {
                            "Security": sec.get("name", "Unknown"),
                            "Symbol": sec.get("symbol", "-"),
                            "Qualification Date": qual_date_str,
                            "Holding Period": holding_str,
                            "Status": status,
                            "Value": format_currency(sec.get("value", 0)),
                        }
                    )

                df = pd.DataFrame(display_data)

                # Color code status
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    height=400,
                    column_config={
                        "Status": st.column_config.TextColumn(
                            "Status",
                            help="Qualified = 5+ years holding period",
                        ),
                    },
                )
            else:
                st.info("No QSBS-eligible securities found.")
        else:
            st.info("No QSBS securities data available.")

    # ============================================
    # TAB 2: MANAGE ELIGIBILITY
    # ============================================
    with tab_manage:
        section_header("Mark Security as QSBS-Eligible")

        st.markdown(
            """
            Mark a security as QSBS-eligible by providing its ID and the date
            when it qualified (typically the acquisition date for original issue stock).
            """,
        )

        with st.form("mark_eligible_form"):
            security_id = st.text_input(
                "Security ID",
                help="Enter the UUID of the security",
            )

            qual_date = st.date_input(
                "Qualification Date",
                value=date.today(),
                help="Date when the security became QSBS-eligible (usually acquisition date)",
            )

            if not isinstance(qual_date, date):
                qual_date = date.today()

            submitted = st.form_submit_button("Mark as QSBS-Eligible", type="primary")

            if submitted:
                if not security_id:
                    st.error("Please enter a Security ID.")
                else:
                    try:
                        result = api_client.mark_security_qsbs_eligible(
                            security_id=security_id,
                            qualification_date=qual_date,
                        )
                        st.success(
                            f"Security marked as QSBS-eligible as of {qual_date}"
                        )
                        clear_qsbs_cache()
                    except api_client.APIError as e:
                        st.error(f"Failed: {e.detail}")

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Remove QSBS Eligibility")

        with st.form("remove_eligible_form"):
            remove_security_id = st.text_input(
                "Security ID",
                key="remove_security_id",
                help="Enter the UUID of the security to remove eligibility",
            )

            remove_submitted = st.form_submit_button(
                "Remove QSBS Eligibility",
                type="secondary",
            )

            if remove_submitted:
                if not remove_security_id:
                    st.error("Please enter a Security ID.")
                else:
                    try:
                        api_client.remove_security_qsbs_eligibility(remove_security_id)
                        st.success("QSBS eligibility removed.")
                        clear_qsbs_cache()
                    except api_client.APIError as e:
                        st.error(f"Failed: {e.detail}")

        # Info box about QSBS rules
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="
                background-color: {COLORS["card_bg"]};
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            ">
                <h4 style="color: {COLORS["primary"]}; margin-top: 0;">QSBS Quick Reference</h4>
                <ul style="margin-bottom: 0; color: {COLORS["text"]};">
                    <li><strong>Section 1202 Exclusion:</strong> Up to 100% of gain excluded from federal tax</li>
                    <li><strong>Holding Period:</strong> Must hold for 5+ years</li>
                    <li><strong>Max Exclusion:</strong> Greater of $10M or 10x cost basis</li>
                    <li><strong>Requirements:</strong> C-corp, active business, gross assets &lt; $50M at issuance</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

except api_client.APIError as e:
    st.error(f"API Error: {e.detail}")
except Exception as e:
    st.error(f"Error loading QSBS data: {e}")
    st.info("Make sure the backend API is running.")
