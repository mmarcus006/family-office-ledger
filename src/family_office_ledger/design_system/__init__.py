"""Atlas Design System for Family Office Ledger.

A comprehensive design system inspired by:
- Addepar APL: Elevation-based hierarchy, data density
- Eton Solutions AtlasFive: Glass morphism, subtle depth
- Kubera: Dark mode first-class, modern aesthetic

This module provides design tokens, themes, and component utilities
that can be used across Streamlit, React, or any other frontend.

Usage:
    from family_office_ledger.design_system import (
        COLORS, LIGHT_THEME, DARK_THEME, get_theme,
        format_currency, format_percentage, get_value_color,
    )

    # Get current theme
    theme = get_theme()
    print(theme.colors.primary)

    # Format financial values
    print(format_currency(1234567.89))  # $1,234,567.89
    print(format_currency(1234567.89, compact=True))  # $1.2M
"""

from family_office_ledger.design_system.tokens import (
    BORDER_RADIUS,
    BREAKPOINTS,
    CHART_COLORS,
    COLORS,
    FONT_SIZES,
    FONT_WEIGHTS,
    SEMANTIC_COLORS,
    SHADOWS,
    SPACING,
    TYPOGRAPHY,
    Z_INDEX,
)
from family_office_ledger.design_system.themes import (
    DARK_THEME,
    LIGHT_THEME,
    Theme,
    ThemeMode,
    generate_css_root,
    generate_full_css,
    get_theme,
    set_theme,
)
from family_office_ledger.design_system.components import (
    Size,
    Variant,
    format_currency,
    format_percentage,
    get_account_type_color,
    get_badge_css,
    get_button_css,
    get_card_css,
    get_echarts_theme,
    get_plotly_theme,
    get_qsbs_status_color,
    get_status_color,
    get_value_color,
)

__all__ = [
    # Tokens
    "COLORS",
    "SEMANTIC_COLORS",
    "CHART_COLORS",
    "TYPOGRAPHY",
    "FONT_SIZES",
    "FONT_WEIGHTS",
    "SPACING",
    "BORDER_RADIUS",
    "SHADOWS",
    "BREAKPOINTS",
    "Z_INDEX",
    # Themes
    "Theme",
    "ThemeMode",
    "LIGHT_THEME",
    "DARK_THEME",
    "get_theme",
    "set_theme",
    "generate_css_root",
    "generate_full_css",
    # Components
    "Size",
    "Variant",
    "get_card_css",
    "get_button_css",
    "get_badge_css",
    "get_plotly_theme",
    "get_echarts_theme",
    # Utilities
    "format_currency",
    "format_percentage",
    "get_value_color",
    "get_status_color",
    "get_account_type_color",
    "get_qsbs_status_color",
]
