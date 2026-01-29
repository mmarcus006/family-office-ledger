"""Portfolio analytics page with allocation, concentration, and performance reports."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from family_office_ledger.streamlit_app import api_client
from family_office_ledger.streamlit_app.app import init_session_state
from family_office_ledger.streamlit_app.styles import (
    CHART_COLORS,
    COLORS,
    apply_custom_css,
    format_currency,
    get_plotly_layout,
    section_header,
)

init_session_state()
apply_custom_css()

st.title("Portfolio Analytics")


@st.cache_data(ttl=60)
def get_entities() -> list[dict[str, Any]]:
    """Fetch entities with caching."""
    try:
        return api_client.list_entities()
    except Exception:
        return []


@st.cache_data(ttl=60)
def get_portfolio_summary(
    entity_ids: list[str] | None,
    as_of_date: date | None,
) -> dict[str, Any]:
    """Fetch portfolio summary with caching."""
    try:
        return api_client.get_portfolio_summary(
            entity_ids=entity_ids, as_of_date=as_of_date
        )
    except Exception:
        return {}


@st.cache_data(ttl=60)
def get_allocation(
    entity_ids: list[str] | None,
    as_of_date: date | None,
) -> dict[str, Any]:
    """Fetch asset allocation with caching."""
    try:
        return api_client.get_asset_allocation(
            entity_ids=entity_ids, as_of_date=as_of_date
        )
    except Exception:
        return {}


@st.cache_data(ttl=60)
def get_concentration(
    entity_ids: list[str] | None,
    as_of_date: date | None,
    top_n: int = 20,
) -> dict[str, Any]:
    """Fetch concentration report with caching."""
    try:
        return api_client.get_concentration_report(
            entity_ids=entity_ids, as_of_date=as_of_date, top_n=top_n
        )
    except Exception:
        return {}


@st.cache_data(ttl=60)
def get_performance(
    start_date: date,
    end_date: date,
    entity_ids: list[str] | None,
) -> dict[str, Any]:
    """Fetch performance report with caching."""
    try:
        return api_client.get_performance_report(
            start_date=start_date, end_date=end_date, entity_ids=entity_ids
        )
    except Exception:
        return {}


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
    # PORTFOLIO SUMMARY
    # ============================================
    summary = get_portfolio_summary(entity_ids, as_of)

    if summary:
        summary_data = summary.get("data", summary)

        # Summary cards
        total_value = float(summary_data.get("total_value", 0))
        total_cost = float(summary_data.get("total_cost", 0))
        unrealized_gain = float(
            summary_data.get("unrealized_gain", total_value - total_cost)
        )
        positions_count = summary_data.get("positions_count", 0)

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {COLORS["primary"]} 0%, #1a2744 100%);
                padding: 2rem;
                border-radius: 12px;
                color: white;
                margin-bottom: 1.5rem;
            ">
                <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.9;">
                    Total Portfolio Value
                </div>
                <div style="font-size: 3rem; font-weight: 700; margin: 0.5rem 0;">
                    {format_currency(total_value)}
                </div>
                <div style="font-size: 0.875rem; opacity: 0.8;">
                    As of {as_of.strftime("%B %d, %Y")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Total Cost Basis", value=format_currency(total_cost), border=True
            )

        with col2:
            gain_delta = f"{'+' if unrealized_gain >= 0 else ''}{format_currency(unrealized_gain)}"
            st.metric(
                label="Unrealized Gain/Loss",
                value=format_currency(abs(unrealized_gain)),
                delta=gain_delta,
                delta_color="normal" if unrealized_gain >= 0 else "inverse",
                border=True,
            )

        with col3:
            if total_cost > 0:
                gain_pct = (unrealized_gain / total_cost) * 100
                pct_display = f"{gain_pct:+.2f}%"
            else:
                pct_display = "N/A"
            st.metric(label="Return %", value=pct_display, border=True)

        with col4:
            st.metric(label="Positions", value=str(positions_count), border=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================
    # TABS FOR DIFFERENT REPORTS
    # ============================================
    tab_alloc, tab_conc, tab_perf = st.tabs(
        ["Asset Allocation", "Concentration", "Performance"]
    )

    # ============================================
    # TAB 1: ASSET ALLOCATION
    # ============================================
    with tab_alloc:
        section_header("Asset Allocation")

        allocation = get_allocation(entity_ids, as_of)

        if allocation:
            alloc_data = allocation.get("data", allocation.get("allocation", {}))

            if isinstance(alloc_data, dict) and alloc_data:
                # Pie chart
                fig_alloc = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(alloc_data.keys()),
                            values=list(alloc_data.values()),
                            hole=0.4,
                            marker={"colors": CHART_COLORS[: len(alloc_data)]},
                            textinfo="label+percent",
                            textposition="outside",
                            textfont={"size": 11},
                        )
                    ]
                )
                fig_alloc.update_layout(
                    **get_plotly_layout(),
                    showlegend=False,
                    height=400,
                )
                st.plotly_chart(fig_alloc, use_container_width=True)

                # Data table
                alloc_df = pd.DataFrame(
                    [
                        {"Asset Class": k, "Value": format_currency(v), "Raw": float(v)}
                        for k, v in alloc_data.items()
                    ]
                )
                total = alloc_df["Raw"].sum()
                if total > 0:
                    alloc_df["% of Portfolio"] = alloc_df["Raw"].apply(
                        lambda x: f"{(x / total) * 100:.1f}%"
                    )
                alloc_df = alloc_df.drop(columns=["Raw"])
                st.dataframe(alloc_df, use_container_width=True, hide_index=True)
            else:
                st.info("No allocation data available.")
        else:
            st.info("No asset allocation data available.")

    # ============================================
    # TAB 2: CONCENTRATION
    # ============================================
    with tab_conc:
        section_header("Portfolio Concentration")

        top_n = st.slider("Top Holdings", min_value=5, max_value=50, value=20)

        concentration = get_concentration(entity_ids, as_of, top_n)

        if concentration:
            conc_data = concentration.get("data", concentration.get("holdings", []))

            if isinstance(conc_data, list) and conc_data:
                # Horizontal bar chart
                holdings_names = [h.get("name", "Unknown")[:20] for h in conc_data[:15]]
                holdings_values = [float(h.get("value", 0)) for h in conc_data[:15]]

                fig_conc = go.Figure(
                    data=[
                        go.Bar(
                            x=holdings_values,
                            y=holdings_names,
                            orientation="h",
                            marker_color=COLORS["primary"],
                            text=[format_currency(v) for v in holdings_values],
                            textposition="outside",
                        )
                    ]
                )
                fig_conc.update_layout(
                    **get_plotly_layout("Top Holdings by Value"),
                    showlegend=False,
                    height=max(300, len(holdings_names) * 25),
                    yaxis={"autorange": "reversed"},
                    xaxis={"showgrid": True, "gridcolor": "#e2e8f0"},
                )
                st.plotly_chart(fig_conc, use_container_width=True)

                # Data table
                display_data = []
                for h in conc_data:
                    display_data.append(
                        {
                            "Holding": h.get("name", "Unknown"),
                            "Symbol": h.get("symbol", "-"),
                            "Value": format_currency(h.get("value", 0)),
                            "% of Portfolio": f"{float(h.get('percentage', 0)):.2f}%",
                            "Shares": str(h.get("shares", "-")),
                        }
                    )

                df_conc = pd.DataFrame(display_data)
                st.dataframe(
                    df_conc, use_container_width=True, hide_index=True, height=400
                )
            else:
                st.info("No concentration data available.")
        else:
            st.info("No concentration data available.")

    # ============================================
    # TAB 3: PERFORMANCE
    # ============================================
    with tab_perf:
        section_header("Performance Report")

        col1, col2 = st.columns(2)
        with col1:
            perf_start = st.date_input(
                "Start Date",
                value=date.today() - timedelta(days=365),
                key="perf_start",
            )
        with col2:
            perf_end = st.date_input(
                "End Date",
                value=date.today(),
                key="perf_end",
            )

        if not isinstance(perf_start, date):
            perf_start = date.today() - timedelta(days=365)
        if not isinstance(perf_end, date):
            perf_end = date.today()

        performance = get_performance(perf_start, perf_end, entity_ids)

        if performance:
            perf_data = performance.get("data", performance)

            # Performance metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                total_return = float(perf_data.get("total_return", 0))
                st.metric(
                    label="Total Return",
                    value=f"{total_return:+.2f}%",
                    border=True,
                )

            with col2:
                realized = float(perf_data.get("realized_gain", 0))
                st.metric(
                    label="Realized Gains",
                    value=format_currency(realized),
                    border=True,
                )

            with col3:
                unrealized = float(perf_data.get("unrealized_gain", 0))
                st.metric(
                    label="Unrealized Gains",
                    value=format_currency(unrealized),
                    border=True,
                )

            # Performance chart if time series available
            time_series = perf_data.get("time_series", [])
            if time_series:
                dates = [p.get("date") for p in time_series]
                values = [float(p.get("value", 0)) for p in time_series]

                fig_perf = go.Figure(
                    data=[
                        go.Scatter(
                            x=dates,
                            y=values,
                            mode="lines",
                            fill="tozeroy",
                            line={"color": COLORS["primary"], "width": 2},
                            fillcolor="rgba(34, 50, 79, 0.1)",
                        )
                    ]
                )
                fig_perf.update_layout(
                    **get_plotly_layout("Portfolio Value Over Time"),
                    showlegend=False,
                    height=350,
                    xaxis={"showgrid": False},
                    yaxis={"showgrid": True, "gridcolor": "#e2e8f0"},
                )
                st.plotly_chart(fig_perf, use_container_width=True)
        else:
            st.info("No performance data available for the selected period.")

except api_client.APIError as e:
    st.error(f"API Error: {e.detail}")
except Exception as e:
    st.error(f"Error loading portfolio data: {e}")
    st.info("Make sure the backend API is running.")
