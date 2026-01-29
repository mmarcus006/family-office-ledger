# pyright: reportMissingImports=false

"""Entities page."""

from __future__ import annotations

from datetime import date
from typing import Any

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.api_client import APIError, api
from family_office_ledger.ui.constants import BUTTON_PRIMARY, CARD, CARD_PAD
from family_office_ledger.ui.constants import ENTITY_TYPES
from family_office_ledger.ui.components.modals import form_dialog
from family_office_ledger.ui.components.tables import data_table
from family_office_ledger.ui.state import state


def render() -> None:
    ui.label("Entities").classes("text-xl font-semibold text-slate-900")

    rows: list[dict[str, Any]] = []

    columns: list[dict[str, Any]] = [
        {"name": "name", "label": "Name", "field": "name", "sortable": True},
        {"name": "entity_type", "label": "Type", "field": "entity_type"},
        {"name": "fiscal_year_end", "label": "Fiscal YE", "field": "fiscal_year_end"},
        {"name": "is_active", "label": "Active", "field": "is_active"},
    ]

    # Create dialog first so it can be referenced in button click handler
    dialog, card = form_dialog("New Entity")

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Manage entities").classes("text-slate-600")
        ui.button("+ New Entity", on_click=lambda: dialog.open()).classes(
            BUTTON_PRIMARY
        )

    with ui.card().classes(f"{CARD} {CARD_PAD} w-full"):
        table = data_table(columns=columns, rows=rows, row_key="id")

    async def refresh() -> None:
        if api is None:
            return
        state.entities = await api.list_entities()
        table.rows = state.entities
        table.update()

    with dialog:
        with card:
            name_in = ui.input("Name").props("autofocus").classes("w-full")
            etype = (
                ui.select(
                    options={o["value"]: o["label"] for o in ENTITY_TYPES},
                    label="Type",
                    value="llc",
                )
                .props("dense outlined")
                .classes("w-full")
            )
            fy_end = ui.date(
                value=date.today().replace(month=12, day=31).isoformat()
            ).props("minimal")

            error = ui.label("").classes("text-rose-700")

            async def submit() -> None:
                if api is None:
                    return
                name = str(name_in.value or "").strip()
                if not name:
                    error.text = "Name is required"
                    error.update()
                    return
                try:
                    fiscal = date.fromisoformat(str(fy_end.value))
                except Exception:
                    fiscal = None

                try:
                    await api.create_entity(
                        name=name,
                        entity_type=str(etype.value),
                        fiscal_year_end=fiscal,
                    )
                except APIError as e:
                    error.text = e.detail
                    error.update()
                    return

                dialog.close()
                await refresh()

            with ui.row().classes("w-full justify-end gap-2 pt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Create Entity", on_click=submit).classes(BUTTON_PRIMARY)

    ui.timer(0.05, refresh, once=True)
