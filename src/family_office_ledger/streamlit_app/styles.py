"""Shared styles and CSS for the Streamlit app."""

from __future__ import annotations

import streamlit as st

# Color palette based on Quicken's design
COLORS = {
    "primary": "#22324F",  # Deep blue - trust, stability
    "accent": "#471CFF",  # Vibrant purple - modern energy
    "positive": "#21c354",  # Green - gains, income
    "negative": "#ff2b2b",  # Red - losses, expenses
    "warning": "#ff8700",  # Orange - caution
    "neutral": "#718096",  # Gray - neutral data
    "background": "#ffffff",
    "card_bg": "#f7fafc",
    "text": "#2d3748",
    "text_muted": "#718096",
}

# Chart color sequence for Plotly
CHART_COLORS = [
    "#22324F",  # Deep blue
    "#471CFF",  # Purple
    "#21c354",  # Green
    "#ff8700",  # Orange
    "#ff2b2b",  # Red
    "#38b2ac",  # Teal
    "#805ad5",  # Violet
    "#d69e2e",  # Yellow
]


def apply_custom_css() -> None:
    """Inject custom CSS for professional financial dashboard styling."""
    st.markdown(
        """
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Reduce top padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Metric card styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
        color: #22324F;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #718096;
        font-weight: 500;
    }
    
    /* Positive delta (green) */
    [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Up"] {
        color: #21c354;
    }
    
    /* Negative delta (red) */
    [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Down"] {
        color: #ff2b2b;
    }
    
    /* Card container */
    .metric-card {
        background-color: #ffffff;
        padding: 1.25rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    
    .metric-card-header {
        font-size: 0.875rem;
        color: #718096;
        font-weight: 500;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-card-value {
        font-size: 2rem;
        font-weight: 700;
        color: #22324F;
        margin: 0;
    }
    
    .metric-card-value.positive {
        color: #21c354;
    }
    
    .metric-card-value.negative {
        color: #ff2b2b;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.125rem;
        font-weight: 600;
        color: #22324F;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e2e8f0;
    }
    
    /* Data table styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    
    .stDataFrame thead tr th {
        background-color: #f7fafc !important;
        color: #22324F !important;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f7fafc;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        color: #22324F;
        font-weight: 700;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #22324F;
        color: white;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        border: none;
        transition: background-color 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #1a2744;
        border: none;
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: #22324F;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        color: #718096;
        background-color: transparent;
        border-radius: 6px 6px 0 0;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #22324F;
        background-color: #f7fafc;
        border-bottom: 2px solid #22324F;
    }
    
    /* Form inputs */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stDateInput > div > div > input {
        border-radius: 6px;
        border-color: #e2e8f0;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #22324F;
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-color: #22324F;
    }
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
        <div class="metric-card">
            <div class="metric-card-header">{title}</div>
            <p class="metric-card-value {value_class}">{value}</p>
            {f'<div style="color: #718096; font-size: 0.875rem; margin-top: 0.25rem;">{subtitle}</div>' if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    """Render a styled section header."""
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def format_currency(value: float | int | str, show_sign: bool = False) -> str:
    """Format a value as currency.

    Args:
        value: Numeric value to format
        show_sign: Whether to show +/- sign

    Returns:
        Formatted currency string
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    if show_sign and num > 0:
        return f"+${num:,.2f}"
    elif num < 0:
        return f"-${abs(num):,.2f}"
    else:
        return f"${num:,.2f}"


def get_amount_color(value: float | int | str) -> str:
    """Get the appropriate color for a monetary value.

    Args:
        value: Numeric value

    Returns:
        Color hex code
    """
    try:
        num = float(value)
        if num > 0:
            return COLORS["positive"]
        elif num < 0:
            return COLORS["negative"]
        else:
            return COLORS["text"]
    except (ValueError, TypeError):
        return COLORS["text"]


def get_plotly_layout(title: str = "") -> dict[str, object]:
    """Get a clean Plotly layout configuration.

    Args:
        title: Optional chart title

    Returns:
        Plotly layout dictionary
    """
    layout: dict[str, object] = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "sans-serif", "size": 12, "color": COLORS["text"]},
        "margin": {"l": 40, "r": 20, "t": 40 if title else 20, "b": 40},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
    }
    if title:
        layout["title"] = {
            "text": title,
            "font": {"size": 16, "color": COLORS["primary"]},
            "x": 0,
            "xanchor": "left",
        }
    return layout
