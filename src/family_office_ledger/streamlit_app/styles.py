"""Shared styles and CSS for the Streamlit app.

Uses the Atlas Design System for consistent styling across all pages.
"""

from __future__ import annotations

import streamlit as st

from family_office_ledger.design_system import (
    COLORS,
    DARK_THEME,
    LIGHT_THEME,
    Theme,
    get_theme,
)
from family_office_ledger.design_system.components import (
    CHART_COLORS,
    format_currency,
    format_percentage,
    get_plotly_theme,
    get_value_color,
)
from family_office_ledger.design_system.tokens import (
    BORDER_RADIUS,
    FONT_SIZES,
    FONT_WEIGHTS,
    SHADOWS,
    SPACING,
    TYPOGRAPHY,
)

# Re-export for backward compatibility
__all__ = [
    "COLORS",
    "CHART_COLORS",
    "apply_custom_css",
    "metric_card",
    "section_header",
    "format_currency",
    "get_amount_color",
    "get_plotly_layout",
]


def apply_custom_css(theme: Theme | None = None) -> None:
    """Inject custom CSS for professional financial dashboard styling.

    Args:
        theme: Theme to apply. Defaults to light theme.
    """
    if theme is None:
        theme = LIGHT_THEME

    colors = theme.colors

    st.markdown(
        f"""
<style>
    /* =================================================================
       Atlas Design System - Streamlit Integration
       ================================================================= */

    /* Import Inter font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Root variables */
    :root {{
        --font-sans: {TYPOGRAPHY['font_sans']};
        --font-mono: {TYPOGRAPHY['font_mono']};
        --color-background: {colors.background};
        --color-surface: {colors.surface};
        --color-text: {colors.text};
        --color-text-secondary: {colors.text_secondary};
        --color-text-muted: {colors.text_muted};
        --color-border: {colors.border};
        --color-primary: {colors.primary};
        --color-success: {colors.success};
        --color-warning: {colors.warning};
        --color-error: {colors.error};
        --color-gain: {colors.gain};
        --color-loss: {colors.loss};
    }}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Base typography */
    html, body, [class*="st-"] {{
        font-family: var(--font-sans);
    }}

    /* Reduce top padding */
    .block-container {{
        padding-top: {SPACING['6']};
        padding-bottom: {SPACING['6']};
        max-width: 1400px;
    }}

    /* =================================================================
       Metric Cards
       ================================================================= */

    [data-testid="stMetricValue"] {{
        font-size: {FONT_SIZES['2xl']};
        font-weight: {FONT_WEIGHTS['semibold']};
        color: {colors.text};
        font-family: var(--font-mono);
    }}

    [data-testid="stMetricLabel"] {{
        font-size: {FONT_SIZES['sm']};
        color: {colors.text_muted};
        font-weight: {FONT_WEIGHTS['medium']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* Positive delta (green) */
    [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Up"] {{
        color: {colors.gain};
    }}
    [data-testid="stMetricDelta"][data-testid="stMetricDeltaIcon-Up"] {{
        color: {colors.gain};
    }}

    /* Negative delta (red) */
    [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Down"] {{
        color: {colors.loss};
    }}

    /* =================================================================
       Custom Card Component
       ================================================================= */

    .atlas-card {{
        background-color: {colors.surface};
        padding: {SPACING['5']};
        border-radius: {BORDER_RADIUS['lg']};
        box-shadow: {SHADOWS['md']};
        border: 1px solid {colors.border_subtle};
        margin-bottom: {SPACING['4']};
    }}

    .atlas-card-header {{
        font-size: {FONT_SIZES['sm']};
        color: {colors.text_muted};
        font-weight: {FONT_WEIGHTS['medium']};
        margin-bottom: {SPACING['2']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .atlas-card-value {{
        font-size: {FONT_SIZES['3xl']};
        font-weight: {FONT_WEIGHTS['bold']};
        color: {colors.text};
        margin: 0;
        font-family: var(--font-mono);
    }}

    .atlas-card-value.positive {{
        color: {colors.gain};
    }}

    .atlas-card-value.negative {{
        color: {colors.loss};
    }}

    .atlas-card-subtitle {{
        color: {colors.text_muted};
        font-size: {FONT_SIZES['sm']};
        margin-top: {SPACING['1']};
    }}

    /* =================================================================
       Glass Card (AtlasFive inspired)
       ================================================================= */

    .atlas-glass-card {{
        background: {colors.glass_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: {colors.glass_border};
        border-radius: {BORDER_RADIUS['xl']};
        padding: {SPACING['6']};
        box-shadow: {SHADOWS['glass']};
    }}

    /* =================================================================
       Section Headers
       ================================================================= */

    .atlas-section-header {{
        font-size: {FONT_SIZES['lg']};
        font-weight: {FONT_WEIGHTS['semibold']};
        color: {colors.text};
        margin-bottom: {SPACING['4']};
        padding-bottom: {SPACING['2']};
        border-bottom: 2px solid {colors.border};
    }}

    /* =================================================================
       Data Tables
       ================================================================= */

    .stDataFrame {{
        border-radius: {BORDER_RADIUS['lg']};
        overflow: hidden;
    }}

    .stDataFrame thead tr th {{
        background-color: {colors.background_subtle} !important;
        color: {colors.text} !important;
        font-weight: {FONT_WEIGHTS['semibold']};
        text-transform: uppercase;
        font-size: {FONT_SIZES['xs']};
        letter-spacing: 0.05em;
        padding: {SPACING['3']} {SPACING['4']} !important;
    }}

    .stDataFrame tbody tr td {{
        font-family: var(--font-mono);
        font-size: {FONT_SIZES['sm']};
    }}

    /* =================================================================
       Sidebar
       ================================================================= */

    [data-testid="stSidebar"] {{
        background-color: {colors.background_subtle};
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {{
        color: {colors.text};
        font-weight: {FONT_WEIGHTS['bold']};
    }}

    /* =================================================================
       Buttons
       ================================================================= */

    .stButton > button {{
        background-color: {colors.primary};
        color: {colors.primary_text};
        border-radius: {BORDER_RADIUS['md']};
        padding: {SPACING['2']} {SPACING['4']};
        font-weight: {FONT_WEIGHTS['medium']};
        border: none;
        transition: all 150ms ease;
        font-family: var(--font-sans);
    }}

    .stButton > button:hover {{
        background-color: {colors.primary_hover};
        border: none;
        transform: translateY(-1px);
        box-shadow: {SHADOWS['md']};
    }}

    .stButton > button:active {{
        background-color: {colors.primary_active};
        transform: translateY(0);
    }}

    /* Secondary button */
    .stButton > button[kind="secondary"] {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
    }}

    .stButton > button[kind="secondary"]:hover {{
        background-color: {colors.background_subtle};
    }}

    /* =================================================================
       Tabs
       ================================================================= */

    .stTabs [data-baseweb="tab-list"] {{
        gap: {SPACING['1']};
        background-color: transparent;
        border-bottom: 1px solid {colors.border};
    }}

    .stTabs [data-baseweb="tab"] {{
        padding: {SPACING['3']} {SPACING['5']};
        font-weight: {FONT_WEIGHTS['medium']};
        color: {colors.text_muted};
        background-color: transparent;
        border-radius: {BORDER_RADIUS['md']} {BORDER_RADIUS['md']} 0 0;
        border: none;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        color: {colors.text};
        background-color: {colors.background_subtle};
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: {colors.primary};
        background-color: {colors.surface};
        border-bottom: 2px solid {colors.primary};
    }}

    /* =================================================================
       Form Inputs
       ================================================================= */

    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stDateInput > div > div > input,
    .stNumberInput > div > div > input {{
        border-radius: {BORDER_RADIUS['md']};
        border-color: {colors.border};
        font-family: var(--font-sans);
    }}

    .stSelectbox > div > div:focus-within,
    .stTextInput > div > div > input:focus,
    .stDateInput > div > div > input:focus {{
        border-color: {colors.border_focus};
        box-shadow: 0 0 0 2px {COLORS['primary']['100']};
    }}

    /* =================================================================
       Expander
       ================================================================= */

    .streamlit-expanderHeader {{
        font-weight: {FONT_WEIGHTS['semibold']};
        color: {colors.text};
        background-color: {colors.background_subtle};
        border-radius: {BORDER_RADIUS['md']};
    }}

    /* =================================================================
       Alerts
       ================================================================= */

    .stAlert {{
        border-radius: {BORDER_RADIUS['lg']};
    }}

    /* Success alert */
    .stAlert[data-baseweb="notification"][kind="positive"] {{
        background-color: {colors.success_subtle};
        border-left: 4px solid {colors.success};
    }}

    /* Warning alert */
    .stAlert[data-baseweb="notification"][kind="warning"] {{
        background-color: {colors.warning_subtle};
        border-left: 4px solid {colors.warning};
    }}

    /* Error alert */
    .stAlert[data-baseweb="notification"][kind="negative"] {{
        background-color: {colors.error_subtle};
        border-left: 4px solid {colors.error};
    }}

    /* =================================================================
       Progress Bar
       ================================================================= */

    .stProgress > div > div > div > div {{
        background-color: {colors.primary};
        border-radius: {BORDER_RADIUS['full']};
    }}

    /* =================================================================
       Status Badges
       ================================================================= */

    .atlas-badge {{
        display: inline-flex;
        align-items: center;
        padding: {SPACING['0.5']} {SPACING['2']};
        font-size: {FONT_SIZES['xs']};
        font-weight: {FONT_WEIGHTS['medium']};
        border-radius: {BORDER_RADIUS['full']};
    }}

    .atlas-badge-success {{
        background-color: {colors.success_subtle};
        color: {colors.success_text};
    }}

    .atlas-badge-warning {{
        background-color: {colors.warning_subtle};
        color: {colors.warning_text};
    }}

    .atlas-badge-error {{
        background-color: {colors.error_subtle};
        color: {colors.error_text};
    }}

    .atlas-badge-info {{
        background-color: {colors.info_subtle};
        color: {colors.info_text};
    }}

    .atlas-badge-neutral {{
        background-color: {colors.background_muted};
        color: {colors.text_secondary};
    }}

    /* =================================================================
       Financial Values
       ================================================================= */

    .atlas-value-positive {{
        color: {colors.gain};
        font-family: var(--font-mono);
    }}

    .atlas-value-negative {{
        color: {colors.loss};
        font-family: var(--font-mono);
    }}

    .atlas-value-neutral {{
        color: {colors.text};
        font-family: var(--font-mono);
    }}

    /* =================================================================
       QSBS Specific Styles
       ================================================================= */

    .atlas-qsbs-eligible {{
        background-color: {COLORS['purple']['50']};
        border-left: 4px solid {COLORS['purple']['600']};
        padding: {SPACING['4']};
        border-radius: {BORDER_RADIUS['md']};
    }}

    .atlas-qsbs-qualified {{
        background-color: {colors.success_subtle};
        border-left: 4px solid {colors.success};
        padding: {SPACING['4']};
        border-radius: {BORDER_RADIUS['md']};
    }}

</style>
""",
        unsafe_allow_html=True,
    )


def metric_card(
    title: str, value: str, subtitle: str = "", positive: bool | None = None
) -> None:
    """Render a styled metric card.

    Args:
        title: Card title/label
        value: Main value to display
        subtitle: Optional subtitle or change indicator
        positive: True for green, False for red, None for neutral
    """
    value_class = ""
    if positive is True:
        value_class = "positive"
    elif positive is False:
        value_class = "negative"

    st.markdown(
        f"""
        <div class="atlas-card">
            <div class="atlas-card-header">{title}</div>
            <p class="atlas-card-value {value_class}">{value}</p>
            {f'<div class="atlas-card-subtitle">{subtitle}</div>' if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def glass_card(content: str, title: str | None = None) -> None:
    """Render a glass morphism card (AtlasFive inspired).

    Args:
        content: HTML content for the card
        title: Optional card title
    """
    title_html = f'<div class="atlas-card-header">{title}</div>' if title else ""
    st.markdown(
        f"""
        <div class="atlas-glass-card">
            {title_html}
            {content}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    """Render a styled section header."""
    st.markdown(
        f'<div class="atlas-section-header">{title}</div>', unsafe_allow_html=True
    )


def status_badge(status: str, variant: str = "neutral") -> str:
    """Generate HTML for a status badge.

    Args:
        status: Status text to display
        variant: Badge variant (success, warning, error, info, neutral)

    Returns:
        HTML string for the badge
    """
    return f'<span class="atlas-badge atlas-badge-{variant}">{status}</span>'


def get_amount_color(value: float | int | str) -> str:
    """Get the appropriate color for a monetary value.

    Args:
        value: Numeric value

    Returns:
        Color hex code
    """
    return get_value_color(value)


def get_plotly_layout(title: str = "") -> dict[str, object]:
    """Get a clean Plotly layout configuration.

    Args:
        title: Optional chart title

    Returns:
        Plotly layout dictionary
    """
    theme = get_theme()
    layout = get_plotly_theme()

    if title:
        layout["title"] = {
            "text": title,
            "font": {"size": 16, "color": theme.colors.text},
            "x": 0,
            "xanchor": "left",
        }

    layout["margin"] = {"l": 40, "r": 20, "t": 40 if title else 20, "b": 40}

    return layout
