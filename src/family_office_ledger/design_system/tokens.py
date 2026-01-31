"""Design tokens for the Atlas Design System.

Design tokens are the atomic values that define the visual design language.
They ensure consistency across all UI components and make it easy to
update the design system in one place.

Based on Tailwind CSS naming conventions for familiarity.
"""

from typing import Final

# =============================================================================
# Color Palette
# Using Tailwind CSS color naming for consistency
# =============================================================================

COLORS: Final[dict[str, dict[str, str]]] = {
    # Primary - Trust, professionalism (Blue)
    "primary": {
        "50": "#eff6ff",
        "100": "#dbeafe",
        "200": "#bfdbfe",
        "300": "#93c5fd",
        "400": "#60a5fa",
        "500": "#3b82f6",
        "600": "#2563eb",  # Main primary
        "700": "#1d4ed8",
        "800": "#1e40af",
        "900": "#1e3a8a",
        "950": "#172554",
    },
    # Slate - Neutral grays with slight blue tint
    "slate": {
        "50": "#f8fafc",
        "100": "#f1f5f9",
        "200": "#e2e8f0",
        "300": "#cbd5e1",
        "400": "#94a3b8",
        "500": "#64748b",
        "600": "#475569",
        "700": "#334155",
        "800": "#1e293b",
        "900": "#0f172a",
        "950": "#020617",
    },
    # Success - Gains, positive values (Emerald)
    "success": {
        "50": "#ecfdf5",
        "100": "#d1fae5",
        "200": "#a7f3d0",
        "300": "#6ee7b7",
        "400": "#34d399",
        "500": "#10b981",
        "600": "#059669",  # Main success
        "700": "#047857",
        "800": "#065f46",
        "900": "#064e3b",
        "950": "#022c22",
    },
    # Warning - Caution, alerts (Amber)
    "warning": {
        "50": "#fffbeb",
        "100": "#fef3c7",
        "200": "#fde68a",
        "300": "#fcd34d",
        "400": "#fbbf24",
        "500": "#f59e0b",
        "600": "#d97706",  # Main warning
        "700": "#b45309",
        "800": "#92400e",
        "900": "#78350f",
        "950": "#451a03",
    },
    # Error - Losses, negative values (Rose)
    "error": {
        "50": "#fff1f2",
        "100": "#ffe4e6",
        "200": "#fecdd3",
        "300": "#fda4af",
        "400": "#fb7185",
        "500": "#f43f5e",
        "600": "#e11d48",  # Main error
        "700": "#be123c",
        "800": "#9f1239",
        "900": "#881337",
        "950": "#4c0519",
    },
    # Info - Informational (Sky)
    "info": {
        "50": "#f0f9ff",
        "100": "#e0f2fe",
        "200": "#bae6fd",
        "300": "#7dd3fc",
        "400": "#38bdf8",
        "500": "#0ea5e9",
        "600": "#0284c7",  # Main info
        "700": "#0369a1",
        "800": "#075985",
        "900": "#0c4a6e",
        "950": "#082f49",
    },
    # Purple - Accent, special highlights
    "purple": {
        "50": "#faf5ff",
        "100": "#f3e8ff",
        "200": "#e9d5ff",
        "300": "#d8b4fe",
        "400": "#c084fc",
        "500": "#a855f7",
        "600": "#9333ea",  # Main purple
        "700": "#7c3aed",
        "800": "#6b21a8",
        "900": "#581c87",
        "950": "#3b0764",
    },
}

# Semantic color aliases for easier use
SEMANTIC_COLORS: Final[dict[str, str]] = {
    # Financial
    "gain": COLORS["success"]["600"],
    "loss": COLORS["error"]["600"],
    "neutral": COLORS["slate"]["500"],
    # Status
    "active": COLORS["success"]["600"],
    "inactive": COLORS["slate"]["400"],
    "pending": COLORS["warning"]["600"],
    "error": COLORS["error"]["600"],
    # QSBS specific
    "qsbs_eligible": COLORS["purple"]["600"],
    "qsbs_qualified": COLORS["success"]["600"],
    "qsbs_pending": COLORS["warning"]["600"],
    # Account types
    "asset": COLORS["primary"]["600"],
    "liability": COLORS["error"]["500"],
    "equity": COLORS["purple"]["600"],
    "income": COLORS["success"]["600"],
    "expense": COLORS["warning"]["600"],
}

# Chart colors (colorblind-friendly sequence)
CHART_COLORS: Final[list[str]] = [
    COLORS["primary"]["600"],  # Blue
    COLORS["success"]["600"],  # Emerald
    COLORS["warning"]["600"],  # Amber
    COLORS["purple"]["600"],  # Purple
    COLORS["info"]["600"],  # Sky
    COLORS["error"]["600"],  # Rose
    COLORS["primary"]["400"],  # Light blue
    COLORS["success"]["400"],  # Light emerald
]

# =============================================================================
# Typography
# =============================================================================

TYPOGRAPHY: Final[dict[str, str]] = {
    # Font families
    "font_sans": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_mono": "'JetBrains Mono', 'Fira Code', 'SF Mono', Monaco, monospace",
    "font_serif": "'Georgia', 'Times New Roman', serif",
    # Line heights
    "leading_none": "1",
    "leading_tight": "1.25",
    "leading_snug": "1.375",
    "leading_normal": "1.5",
    "leading_relaxed": "1.625",
    "leading_loose": "2",
    # Letter spacing
    "tracking_tighter": "-0.05em",
    "tracking_tight": "-0.025em",
    "tracking_normal": "0",
    "tracking_wide": "0.025em",
    "tracking_wider": "0.05em",
    "tracking_widest": "0.1em",
}

FONT_SIZES: Final[dict[str, str]] = {
    "xs": "0.75rem",  # 12px
    "sm": "0.875rem",  # 14px
    "base": "1rem",  # 16px
    "lg": "1.125rem",  # 18px
    "xl": "1.25rem",  # 20px
    "2xl": "1.5rem",  # 24px
    "3xl": "1.875rem",  # 30px
    "4xl": "2.25rem",  # 36px
    "5xl": "3rem",  # 48px
    "6xl": "3.75rem",  # 60px
}

FONT_WEIGHTS: Final[dict[str, int]] = {
    "thin": 100,
    "extralight": 200,
    "light": 300,
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    "extrabold": 800,
    "black": 900,
}

# =============================================================================
# Spacing Scale
# =============================================================================

SPACING: Final[dict[str, str]] = {
    "0": "0",
    "px": "1px",
    "0.5": "0.125rem",  # 2px
    "1": "0.25rem",  # 4px
    "1.5": "0.375rem",  # 6px
    "2": "0.5rem",  # 8px
    "2.5": "0.625rem",  # 10px
    "3": "0.75rem",  # 12px
    "3.5": "0.875rem",  # 14px
    "4": "1rem",  # 16px
    "5": "1.25rem",  # 20px
    "6": "1.5rem",  # 24px
    "7": "1.75rem",  # 28px
    "8": "2rem",  # 32px
    "9": "2.25rem",  # 36px
    "10": "2.5rem",  # 40px
    "11": "2.75rem",  # 44px
    "12": "3rem",  # 48px
    "14": "3.5rem",  # 56px
    "16": "4rem",  # 64px
    "20": "5rem",  # 80px
    "24": "6rem",  # 96px
    "28": "7rem",  # 112px
    "32": "8rem",  # 128px
}

# =============================================================================
# Border Radius
# =============================================================================

BORDER_RADIUS: Final[dict[str, str]] = {
    "none": "0",
    "sm": "0.125rem",  # 2px
    "DEFAULT": "0.25rem",  # 4px
    "md": "0.375rem",  # 6px
    "lg": "0.5rem",  # 8px
    "xl": "0.75rem",  # 12px
    "2xl": "1rem",  # 16px
    "3xl": "1.5rem",  # 24px
    "full": "9999px",
}

# =============================================================================
# Shadows (Elevation)
# Based on Addepar APL elevation system
# =============================================================================

SHADOWS: Final[dict[str, str]] = {
    "none": "none",
    # Subtle elevation for cards
    "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    # Default card shadow
    "DEFAULT": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    # Raised elements
    "md": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
    # Prominent cards
    "lg": "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
    # Modals, dropdowns
    "xl": "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
    # Full page overlays
    "2xl": "0 25px 50px -12px rgb(0 0 0 / 0.25)",
    # Inner shadow for inputs
    "inner": "inset 0 2px 4px 0 rgb(0 0 0 / 0.05)",
    # Glass morphism shadow (AtlasFive inspired)
    "glass": "0 8px 32px 0 rgba(31, 38, 135, 0.15)",
}

# =============================================================================
# Breakpoints (Responsive Design)
# =============================================================================

BREAKPOINTS: Final[dict[str, str]] = {
    "sm": "640px",
    "md": "768px",
    "lg": "1024px",
    "xl": "1280px",
    "2xl": "1536px",
}

# =============================================================================
# Z-Index Scale
# =============================================================================

Z_INDEX: Final[dict[str, int]] = {
    "auto": 0,
    "base": 0,
    "dropdown": 10,
    "sticky": 20,
    "fixed": 30,
    "modal-backdrop": 40,
    "modal": 50,
    "popover": 60,
    "tooltip": 70,
    "notification": 80,
    "max": 9999,
}

# =============================================================================
# Animation & Transitions
# =============================================================================

TRANSITIONS: Final[dict[str, str]] = {
    "none": "none",
    "all": "all 150ms cubic-bezier(0.4, 0, 0.2, 1)",
    "DEFAULT": "color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)",
    "colors": "color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1)",
    "opacity": "opacity 150ms cubic-bezier(0.4, 0, 0.2, 1)",
    "shadow": "box-shadow 150ms cubic-bezier(0.4, 0, 0.2, 1)",
    "transform": "transform 150ms cubic-bezier(0.4, 0, 0.2, 1)",
}

DURATIONS: Final[dict[str, str]] = {
    "75": "75ms",
    "100": "100ms",
    "150": "150ms",
    "200": "200ms",
    "300": "300ms",
    "500": "500ms",
    "700": "700ms",
    "1000": "1000ms",
}

# =============================================================================
# Glass Morphism (AtlasFive inspired)
# =============================================================================

GLASS: Final[dict[str, str]] = {
    "background": "rgba(255, 255, 255, 0.7)",
    "background_dark": "rgba(30, 41, 59, 0.8)",
    "blur": "blur(10px)",
    "border": "1px solid rgba(255, 255, 255, 0.2)",
    "border_dark": "1px solid rgba(255, 255, 255, 0.1)",
}
