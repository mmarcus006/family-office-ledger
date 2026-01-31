<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-31 | Updated: 2026-01-31 -->

# design_system

## Purpose
Atlas Design System - a comprehensive design system for the Family Office Ledger inspired by Addepar APL, Eton Solutions AtlasFive, and Kubera. Provides design tokens, themes, and component utilities usable across Streamlit, React, or any frontend.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Public API - exports all tokens, themes, and utilities |
| `tokens.py` | Design tokens: colors, typography, spacing, shadows, breakpoints (10KB) |
| `themes.py` | Theme definitions: light/dark modes, CSS generation (11KB) |
| `components.py` | Component utilities: formatters, CSS generators, chart themes (11KB) |

## For AI Agents

### Working In This Directory
- This is a **cross-platform design system** - changes affect all frontends
- Tokens are the foundation - themes and components build on them
- Dark mode is first-class (not an afterthought)

### Design Token Categories
- `COLORS` - Brand and neutral color palette
- `SEMANTIC_COLORS` - Success, warning, error, info
- `CHART_COLORS` - Data visualization palette
- `TYPOGRAPHY` - Font families and scales
- `SPACING` - Consistent spacing scale
- `SHADOWS` - Elevation-based shadows
- `Z_INDEX` - Layer ordering

### Theme System
```python
from family_office_ledger.design_system import get_theme, LIGHT_THEME, DARK_THEME

theme = get_theme()  # Returns current theme
print(theme.colors.primary)
```

### Utility Functions
- `format_currency(amount, compact=False)` - Format money values
- `format_percentage(value)` - Format percentages
- `get_value_color(value)` - Green/red for positive/negative
- `get_plotly_theme()` / `get_echarts_theme()` - Chart library themes

### Testing Requirements
- Test both light and dark themes
- Verify CSS generation produces valid CSS
- Check formatters handle edge cases (negative, zero, large numbers)

## Dependencies

### External
- No external dependencies - pure Python

<!-- MANUAL: -->
