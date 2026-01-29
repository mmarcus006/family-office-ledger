# pyright: reportMissingImports=false

"""Navigation components."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.api_client import api
from family_office_ledger.ui.constants import NAV_LINK
from family_office_ledger.ui.state import state


def _entity_options(entities: list[dict[str, Any]]) -> dict[str, str]:
    options: dict[str, str] = {"": "All entities"}
    for e in entities:
        entity_id = str(e.get("id", ""))
        name = str(e.get("name", entity_id))
        if entity_id:
            options[entity_id] = name
    return options


def header() -> None:
    with ui.header(elevated=True).classes("bg-white border-b border-slate-200"):  # noqa: SIM117
        with ui.row().classes("w-full items-center justify-between px-4 py-2"):
            ui.label("Atlas Ledger").classes("text-lg font-semibold text-slate-900")

            selector = ui.select(
                options={"": "Loading..."},
                value=str(state.selected_entity_id) if state.selected_entity_id else "",
                label="Entity",
            ).props("dense outlined")

            async def load_entities() -> None:
                if api is None:
                    return
                entities = await api.list_entities()
                state.entities = entities
                selector.options = _entity_options(entities)
                selector.update()

            async def on_change(_: Any) -> None:
                raw = selector.value
                if not raw:
                    state.selected_entity_id = None
                else:
                    try:
                        state.selected_entity_id = UUID(str(raw))
                    except Exception:
                        state.selected_entity_id = None

            selector.on("update:model-value", on_change)
            ui.timer(0.05, load_entities, once=True)


def sidebar() -> None:
    with (
        ui.left_drawer(top_corner=True, bottom_corner=True).classes(
            "bg-white border-r border-slate-200"
        ),
        ui.column().classes("w-56 p-3 gap-1"),
    ):
        ui.link("Dashboard", "/").classes(NAV_LINK)
        ui.link("Entities", "/entities").classes(NAV_LINK)
        ui.link("Accounts", "/accounts").classes(NAV_LINK)
        ui.link("Transactions", "/transactions").classes(NAV_LINK)
        ui.link("Reports", "/reports").classes(NAV_LINK)
