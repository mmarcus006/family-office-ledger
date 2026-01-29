"""Chart wrappers.

Plotly is optional; charts are used sparingly.
"""

from __future__ import annotations

from typing import Any


def plotly_figure(data: Any) -> Any:
    """Return Plotly figure data unchanged.

    NiceGUI can render Plotly figures when Plotly is installed. This wrapper exists
    to keep imports optional.
    """

    return data
