"""Component utilities for the Atlas Design System.

Provides reusable component patterns and CSS generation utilities
for building consistent UI components across different frontends.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from family_office_ledger.design_system.themes import Theme, get_theme
from family_office_ledger.design_system.tokens import (
    BORDER_RADIUS,
    CHART_COLORS,
    COLORS,
    FONT_SIZES,
    FONT_WEIGHTS,
    SEMANTIC_COLORS,
    SHADOWS,
    SPACING,
    TYPOGRAPHY,
)


class Size(str, Enum):
    """Component size variants."""

    XS = "xs"
    SM = "sm"
    MD = "md"
    LG = "lg"
    XL = "xl"


class Variant(str, Enum):
    """Component style variants."""

    DEFAULT = "default"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    GHOST = "ghost"


# =============================================================================
# CSS Generation Utilities
# =============================================================================


def get_card_css(
    elevated: bool = True,
    glass: bool = False,
    padding: str = "md",
    radius: str = "lg",
) -> str:
    """Generate CSS for a card component.

    Args:
        elevated: Whether card has shadow elevation
        glass: Whether to use glass morphism effect
        padding: Padding size (xs, sm, md, lg, xl)
        radius: Border radius (sm, md, lg, xl)

    Returns:
        CSS string for the card
    """
    theme = get_theme()
    styles = [
        f"background-color: {theme.colors.surface};",
        f"border-radius: {BORDER_RADIUS.get(radius, BORDER_RADIUS['lg'])};",
        f"padding: {SPACING.get(padding, SPACING['4'])};",
        f"border: 1px solid {theme.colors.border_subtle};",
    ]

    if elevated:
        styles.append(f"box-shadow: {SHADOWS['md']};")

    if glass:
        styles.extend([
            f"background: {theme.colors.glass_bg};",
            "backdrop-filter: blur(10px);",
            "-webkit-backdrop-filter: blur(10px);",
            f"border: {theme.colors.glass_border};",
        ])

    return " ".join(styles)


def get_button_css(
    variant: Variant = Variant.PRIMARY,
    size: Size = Size.MD,
    full_width: bool = False,
) -> str:
    """Generate CSS for a button component.

    Args:
        variant: Button style variant
        size: Button size
        full_width: Whether button takes full width

    Returns:
        CSS string for the button
    """
    theme = get_theme()

    # Size mappings
    size_styles = {
        Size.XS: f"padding: {SPACING['1']} {SPACING['2']}; font-size: {FONT_SIZES['xs']};",
        Size.SM: f"padding: {SPACING['1.5']} {SPACING['3']}; font-size: {FONT_SIZES['sm']};",
        Size.MD: f"padding: {SPACING['2']} {SPACING['4']}; font-size: {FONT_SIZES['base']};",
        Size.LG: f"padding: {SPACING['2.5']} {SPACING['5']}; font-size: {FONT_SIZES['lg']};",
        Size.XL: f"padding: {SPACING['3']} {SPACING['6']}; font-size: {FONT_SIZES['xl']};",
    }

    # Variant colors
    variant_styles = {
        Variant.PRIMARY: f"background-color: {theme.colors.primary}; color: {theme.colors.primary_text};",
        Variant.SECONDARY: f"background-color: {theme.colors.background_muted}; color: {theme.colors.text};",
        Variant.SUCCESS: f"background-color: {theme.colors.success}; color: white;",
        Variant.WARNING: f"background-color: {theme.colors.warning}; color: white;",
        Variant.ERROR: f"background-color: {theme.colors.error}; color: white;",
        Variant.INFO: f"background-color: {theme.colors.info}; color: white;",
        Variant.GHOST: f"background-color: transparent; color: {theme.colors.text};",
        Variant.DEFAULT: f"background-color: {theme.colors.surface}; color: {theme.colors.text}; border: 1px solid {theme.colors.border};",
    }

    styles = [
        f"font-family: {TYPOGRAPHY['font_sans']};",
        f"font-weight: {FONT_WEIGHTS['medium']};",
        f"border-radius: {BORDER_RADIUS['md']};",
        "border: none;",
        "cursor: pointer;",
        "transition: all 150ms ease;",
        size_styles.get(size, size_styles[Size.MD]),
        variant_styles.get(variant, variant_styles[Variant.PRIMARY]),
    ]

    if full_width:
        styles.append("width: 100%;")

    return " ".join(styles)


def get_badge_css(variant: Variant = Variant.DEFAULT) -> str:
    """Generate CSS for a badge/tag component.

    Args:
        variant: Badge style variant

    Returns:
        CSS string for the badge
    """
    theme = get_theme()

    variant_styles = {
        Variant.DEFAULT: f"background-color: {theme.colors.background_muted}; color: {theme.colors.text_secondary};",
        Variant.PRIMARY: f"background-color: {COLORS['primary']['100']}; color: {COLORS['primary']['700']};",
        Variant.SUCCESS: f"background-color: {theme.colors.success_subtle}; color: {theme.colors.success_text};",
        Variant.WARNING: f"background-color: {theme.colors.warning_subtle}; color: {theme.colors.warning_text};",
        Variant.ERROR: f"background-color: {theme.colors.error_subtle}; color: {theme.colors.error_text};",
        Variant.INFO: f"background-color: {theme.colors.info_subtle}; color: {theme.colors.info_text};",
    }

    styles = [
        f"font-size: {FONT_SIZES['xs']};",
        f"font-weight: {FONT_WEIGHTS['medium']};",
        f"padding: {SPACING['0.5']} {SPACING['2']};",
        f"border-radius: {BORDER_RADIUS['full']};",
        "display: inline-flex;",
        "align-items: center;",
        variant_styles.get(variant, variant_styles[Variant.DEFAULT]),
    ]

    return " ".join(styles)


# =============================================================================
# Financial Formatting Utilities
# =============================================================================


def format_currency(
    value: float | int | str,
    currency: str = "USD",
    show_sign: bool = False,
    compact: bool = False,
) -> str:
    """Format a value as currency.

    Args:
        value: Numeric value to format
        currency: Currency code (USD, EUR, etc.)
        show_sign: Whether to show +/- sign
        compact: Use compact notation (1.5M instead of 1,500,000)

    Returns:
        Formatted currency string
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    # Currency symbols
    symbols = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "JPY": "\u00a5"}
    symbol = symbols.get(currency, currency + " ")

    if compact and abs(num) >= 1_000_000_000:
        formatted = f"{num / 1_000_000_000:.1f}B"
    elif compact and abs(num) >= 1_000_000:
        formatted = f"{num / 1_000_000:.1f}M"
    elif compact and abs(num) >= 1_000:
        formatted = f"{num / 1_000:.1f}K"
    else:
        formatted = f"{abs(num):,.2f}"

    if show_sign and num > 0:
        return f"+{symbol}{formatted}"
    elif num < 0:
        return f"-{symbol}{formatted}"
    else:
        return f"{symbol}{formatted}"


def format_percentage(
    value: float | int | str,
    decimals: int = 2,
    show_sign: bool = False,
) -> str:
    """Format a value as percentage.

    Args:
        value: Numeric value (0.15 = 15%)
        decimals: Number of decimal places
        show_sign: Whether to show +/- sign

    Returns:
        Formatted percentage string
    """
    try:
        num = float(value) * 100
    except (ValueError, TypeError):
        return str(value)

    formatted = f"{num:.{decimals}f}%"

    if show_sign and num > 0:
        return f"+{formatted}"
    return formatted


def get_value_color(value: float | int | str) -> str:
    """Get the appropriate color for a monetary value.

    Args:
        value: Numeric value

    Returns:
        Color hex code (gain, loss, or neutral)
    """
    theme = get_theme()
    try:
        num = float(value)
        if num > 0:
            return theme.colors.gain
        elif num < 0:
            return theme.colors.loss
        else:
            return theme.colors.neutral
    except (ValueError, TypeError):
        return theme.colors.text


def get_status_color(status: str) -> str:
    """Get color for a status value.

    Args:
        status: Status string (active, inactive, pending, error, etc.)

    Returns:
        Color hex code
    """
    status_lower = status.lower()
    return SEMANTIC_COLORS.get(status_lower, SEMANTIC_COLORS["neutral"])


# =============================================================================
# Chart Configuration
# =============================================================================


def get_plotly_theme() -> dict[str, Any]:
    """Get Plotly chart theme configuration.

    Returns:
        Plotly layout configuration dictionary
    """
    theme = get_theme()

    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": TYPOGRAPHY["font_sans"],
            "size": 12,
            "color": theme.colors.text_secondary,
        },
        "colorway": CHART_COLORS,
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
            "bgcolor": "rgba(0,0,0,0)",
        },
        "xaxis": {
            "gridcolor": theme.colors.border_subtle,
            "linecolor": theme.colors.border,
            "tickfont": {"color": theme.colors.text_muted},
        },
        "yaxis": {
            "gridcolor": theme.colors.border_subtle,
            "linecolor": theme.colors.border,
            "tickfont": {"color": theme.colors.text_muted},
        },
    }


def get_echarts_theme() -> dict[str, Any]:
    """Get ECharts theme configuration.

    Returns:
        ECharts option configuration
    """
    theme = get_theme()

    return {
        "backgroundColor": "transparent",
        "textStyle": {
            "fontFamily": TYPOGRAPHY["font_sans"],
            "color": theme.colors.text_secondary,
        },
        "color": CHART_COLORS,
        "legend": {
            "textStyle": {"color": theme.colors.text_secondary},
        },
        "tooltip": {
            "backgroundColor": theme.colors.surface,
            "borderColor": theme.colors.border,
            "textStyle": {"color": theme.colors.text},
        },
    }


# =============================================================================
# Account Type Colors
# =============================================================================


def get_account_type_color(account_type: str) -> str:
    """Get color for an account type.

    Args:
        account_type: Account type (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE)

    Returns:
        Color hex code
    """
    type_lower = account_type.lower()
    return SEMANTIC_COLORS.get(type_lower, COLORS["slate"]["500"])


def get_qsbs_status_color(status: str) -> str:
    """Get color for QSBS status.

    Args:
        status: QSBS status (eligible, qualified, pending, not_eligible)

    Returns:
        Color hex code
    """
    status_map = {
        "eligible": SEMANTIC_COLORS["qsbs_eligible"],
        "qualified": SEMANTIC_COLORS["qsbs_qualified"],
        "pending": SEMANTIC_COLORS["qsbs_pending"],
        "not_eligible": COLORS["slate"]["400"],
    }
    return status_map.get(status.lower(), COLORS["slate"]["500"])
