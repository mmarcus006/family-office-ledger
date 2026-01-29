"""Global UI state.

NiceGUI apps are typically single-process; state here is process-global.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class AppState:
    """Global application state."""

    selected_entity_id: UUID | None = None
    selected_account_id: UUID | None = None

    # Simple caches (refreshed on navigation / page load)
    entities: list[dict[str, Any]] = field(default_factory=list)
    accounts: list[dict[str, Any]] = field(default_factory=list)

    sidebar_collapsed: bool = False

    def clear_selections(self) -> None:
        self.selected_entity_id = None
        self.selected_account_id = None


state = AppState()
