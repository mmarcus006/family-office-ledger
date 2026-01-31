"""Theme configurations for the Atlas Design System.

Provides light and dark themes with semantic color mappings.
Each theme defines colors for backgrounds, text, borders, and components.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Final

from family_office_ledger.design_system.tokens import (
    BORDER_RADIUS,
    COLORS,
    FONT_SIZES,
    GLASS,
    SHADOWS,
    SPACING,
    TYPOGRAPHY,
)


class ThemeMode(str, Enum):
    """Available theme modes."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass(frozen=True)
class ThemeColors:
    """Semantic color definitions for a theme."""

    # Backgrounds
    background: str
    background_subtle: str
    background_muted: str
    surface: str
    surface_raised: str
    surface_overlay: str

    # Text
    text: str
    text_secondary: str
    text_muted: str
    text_inverted: str

    # Borders
    border: str
    border_subtle: str
    border_focus: str

    # Primary actions
    primary: str
    primary_hover: str
    primary_active: str
    primary_text: str

    # Status colors
    success: str
    success_subtle: str
    success_text: str

    warning: str
    warning_subtle: str
    warning_text: str

    error: str
    error_subtle: str
    error_text: str

    info: str
    info_subtle: str
    info_text: str

    # Financial specific
    gain: str
    loss: str
    neutral: str

    # Glass effect
    glass_bg: str
    glass_border: str


@dataclass(frozen=True)
class Theme:
    """Complete theme configuration."""

    name: str
    mode: ThemeMode
    colors: ThemeColors

    # Typography
    font_family: str = TYPOGRAPHY["font_sans"]
    font_family_mono: str = TYPOGRAPHY["font_mono"]

    # Commonly used values (shortcuts)
    radius_sm: str = BORDER_RADIUS["sm"]
    radius_md: str = BORDER_RADIUS["md"]
    radius_lg: str = BORDER_RADIUS["lg"]

    shadow_sm: str = SHADOWS["sm"]
    shadow_md: str = SHADOWS["md"]
    shadow_lg: str = SHADOWS["lg"]

    spacing_xs: str = SPACING["1"]
    spacing_sm: str = SPACING["2"]
    spacing_md: str = SPACING["4"]
    spacing_lg: str = SPACING["6"]
    spacing_xl: str = SPACING["8"]

    def to_css_variables(self) -> str:
        """Generate CSS custom properties from theme."""
        css_vars = []

        # Colors
        css_vars.append(f"--color-background: {self.colors.background};")
        css_vars.append(f"--color-background-subtle: {self.colors.background_subtle};")
        css_vars.append(f"--color-background-muted: {self.colors.background_muted};")
        css_vars.append(f"--color-surface: {self.colors.surface};")
        css_vars.append(f"--color-surface-raised: {self.colors.surface_raised};")
        css_vars.append(f"--color-surface-overlay: {self.colors.surface_overlay};")

        css_vars.append(f"--color-text: {self.colors.text};")
        css_vars.append(f"--color-text-secondary: {self.colors.text_secondary};")
        css_vars.append(f"--color-text-muted: {self.colors.text_muted};")
        css_vars.append(f"--color-text-inverted: {self.colors.text_inverted};")

        css_vars.append(f"--color-border: {self.colors.border};")
        css_vars.append(f"--color-border-subtle: {self.colors.border_subtle};")
        css_vars.append(f"--color-border-focus: {self.colors.border_focus};")

        css_vars.append(f"--color-primary: {self.colors.primary};")
        css_vars.append(f"--color-primary-hover: {self.colors.primary_hover};")
        css_vars.append(f"--color-primary-active: {self.colors.primary_active};")
        css_vars.append(f"--color-primary-text: {self.colors.primary_text};")

        css_vars.append(f"--color-success: {self.colors.success};")
        css_vars.append(f"--color-success-subtle: {self.colors.success_subtle};")
        css_vars.append(f"--color-warning: {self.colors.warning};")
        css_vars.append(f"--color-warning-subtle: {self.colors.warning_subtle};")
        css_vars.append(f"--color-error: {self.colors.error};")
        css_vars.append(f"--color-error-subtle: {self.colors.error_subtle};")
        css_vars.append(f"--color-info: {self.colors.info};")
        css_vars.append(f"--color-info-subtle: {self.colors.info_subtle};")

        css_vars.append(f"--color-gain: {self.colors.gain};")
        css_vars.append(f"--color-loss: {self.colors.loss};")
        css_vars.append(f"--color-neutral: {self.colors.neutral};")

        css_vars.append(f"--color-glass-bg: {self.colors.glass_bg};")
        css_vars.append(f"--color-glass-border: {self.colors.glass_border};")

        # Typography
        css_vars.append(f"--font-family: {self.font_family};")
        css_vars.append(f"--font-family-mono: {self.font_family_mono};")

        # Radius
        css_vars.append(f"--radius-sm: {self.radius_sm};")
        css_vars.append(f"--radius-md: {self.radius_md};")
        css_vars.append(f"--radius-lg: {self.radius_lg};")

        # Shadows
        css_vars.append(f"--shadow-sm: {self.shadow_sm};")
        css_vars.append(f"--shadow-md: {self.shadow_md};")
        css_vars.append(f"--shadow-lg: {self.shadow_lg};")

        # Spacing
        css_vars.append(f"--spacing-xs: {self.spacing_xs};")
        css_vars.append(f"--spacing-sm: {self.spacing_sm};")
        css_vars.append(f"--spacing-md: {self.spacing_md};")
        css_vars.append(f"--spacing-lg: {self.spacing_lg};")
        css_vars.append(f"--spacing-xl: {self.spacing_xl};")

        return "\n    ".join(css_vars)


# =============================================================================
# Light Theme (Default)
# =============================================================================

LIGHT_THEME_COLORS = ThemeColors(
    # Backgrounds
    background=COLORS["slate"]["50"],
    background_subtle=COLORS["slate"]["100"],
    background_muted=COLORS["slate"]["200"],
    surface="#ffffff",
    surface_raised="#ffffff",
    surface_overlay="rgba(255, 255, 255, 0.9)",
    # Text
    text=COLORS["slate"]["900"],
    text_secondary=COLORS["slate"]["700"],
    text_muted=COLORS["slate"]["500"],
    text_inverted="#ffffff",
    # Borders
    border=COLORS["slate"]["200"],
    border_subtle=COLORS["slate"]["100"],
    border_focus=COLORS["primary"]["500"],
    # Primary
    primary=COLORS["primary"]["600"],
    primary_hover=COLORS["primary"]["700"],
    primary_active=COLORS["primary"]["800"],
    primary_text="#ffffff",
    # Status
    success=COLORS["success"]["600"],
    success_subtle=COLORS["success"]["50"],
    success_text=COLORS["success"]["700"],
    warning=COLORS["warning"]["600"],
    warning_subtle=COLORS["warning"]["50"],
    warning_text=COLORS["warning"]["700"],
    error=COLORS["error"]["600"],
    error_subtle=COLORS["error"]["50"],
    error_text=COLORS["error"]["700"],
    info=COLORS["info"]["600"],
    info_subtle=COLORS["info"]["50"],
    info_text=COLORS["info"]["700"],
    # Financial
    gain=COLORS["success"]["600"],
    loss=COLORS["error"]["600"],
    neutral=COLORS["slate"]["500"],
    # Glass
    glass_bg=GLASS["background"],
    glass_border=GLASS["border"],
)

LIGHT_THEME: Final[Theme] = Theme(
    name="Atlas Light",
    mode=ThemeMode.LIGHT,
    colors=LIGHT_THEME_COLORS,
)

# =============================================================================
# Dark Theme
# =============================================================================

DARK_THEME_COLORS = ThemeColors(
    # Backgrounds
    background=COLORS["slate"]["950"],
    background_subtle=COLORS["slate"]["900"],
    background_muted=COLORS["slate"]["800"],
    surface=COLORS["slate"]["900"],
    surface_raised=COLORS["slate"]["800"],
    surface_overlay="rgba(15, 23, 42, 0.9)",
    # Text
    text=COLORS["slate"]["50"],
    text_secondary=COLORS["slate"]["300"],
    text_muted=COLORS["slate"]["400"],
    text_inverted=COLORS["slate"]["900"],
    # Borders
    border=COLORS["slate"]["700"],
    border_subtle=COLORS["slate"]["800"],
    border_focus=COLORS["primary"]["400"],
    # Primary
    primary=COLORS["primary"]["500"],
    primary_hover=COLORS["primary"]["400"],
    primary_active=COLORS["primary"]["600"],
    primary_text="#ffffff",
    # Status
    success=COLORS["success"]["500"],
    success_subtle=COLORS["success"]["950"],
    success_text=COLORS["success"]["400"],
    warning=COLORS["warning"]["500"],
    warning_subtle=COLORS["warning"]["950"],
    warning_text=COLORS["warning"]["400"],
    error=COLORS["error"]["500"],
    error_subtle=COLORS["error"]["950"],
    error_text=COLORS["error"]["400"],
    info=COLORS["info"]["500"],
    info_subtle=COLORS["info"]["950"],
    info_text=COLORS["info"]["400"],
    # Financial
    gain=COLORS["success"]["500"],
    loss=COLORS["error"]["500"],
    neutral=COLORS["slate"]["400"],
    # Glass
    glass_bg=GLASS["background_dark"],
    glass_border=GLASS["border_dark"],
)

DARK_THEME: Final[Theme] = Theme(
    name="Atlas Dark",
    mode=ThemeMode.DARK,
    colors=DARK_THEME_COLORS,
)

# =============================================================================
# Theme Utilities
# =============================================================================

_current_theme: Theme = LIGHT_THEME


def get_theme(mode: ThemeMode | str | None = None) -> Theme:
    """Get a theme by mode.

    Args:
        mode: Theme mode (light, dark, system, or None for current)

    Returns:
        Theme configuration
    """
    if mode is None:
        return _current_theme

    if isinstance(mode, str):
        mode = ThemeMode(mode.lower())

    if mode == ThemeMode.DARK:
        return DARK_THEME
    elif mode == ThemeMode.LIGHT:
        return LIGHT_THEME
    else:
        # System mode - default to light (would need JS to detect)
        return LIGHT_THEME


def set_theme(theme: Theme) -> None:
    """Set the current theme.

    Args:
        theme: Theme to set as current
    """
    global _current_theme
    _current_theme = theme


def generate_css_root(theme: Theme | None = None) -> str:
    """Generate complete CSS :root block with theme variables.

    Args:
        theme: Theme to use (defaults to current theme)

    Returns:
        CSS string with :root variables
    """
    if theme is None:
        theme = _current_theme

    return f"""
:root {{
    {theme.to_css_variables()}
}}
"""


def generate_full_css(include_dark: bool = True) -> str:
    """Generate complete CSS with light and dark themes.

    Args:
        include_dark: Whether to include dark mode media query

    Returns:
        Complete CSS string
    """
    css_parts = [
        "/* Atlas Design System - Generated CSS Variables */",
        generate_css_root(LIGHT_THEME),
    ]

    if include_dark:
        css_parts.append(f"""
@media (prefers-color-scheme: dark) {{
    :root {{
        {DARK_THEME.to_css_variables()}
    }}
}}

[data-theme="dark"] {{
    {DARK_THEME.to_css_variables()}
}}
""")

    return "\n".join(css_parts)
