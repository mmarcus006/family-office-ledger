# pyright: reportMissingImports=false

"""Accounts page."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.api_client import APIError, api
from family_office_ledger.ui.constants import (
    ACCOUNT_SUB_TYPES,
    ACCOUNT_TYPES,
    BUTTON_PRIMARY,
    CARD,
    CARD_PAD,
)
from family_office_ledger.ui.components.modals import form_dialog
from family_office_ledger.ui.components.tables import data_table
from family_office_ledger.ui.state import state


def _group_by_type(accounts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in accounts:
        grouped[str(a.get("account_type", "other"))].append(a)
    return dict(grouped)


def render() -> None:
    ui.label("Accounts").classes("text-xl font-semibold text-slate-900")

    help_text = ui.label(
        "Accounts are scoped to the selected entity in the header."
    ).classes("text-slate-600")

    columns: list[dict[str, Any]] = [
        {"name": "name", "label": "Name", "field": "name", "sortable": True},
        {"name": "sub_type", "label": "Sub-Type", "field": "sub_type"},
        {"name": "currency", "label": "Currency", "field": "currency"},
    ]

    # Create dialog first so it can be referenced in button click handler
    dialog, card = form_dialog("New Account")

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Manage accounts").classes("text-slate-600")
        new_btn = ui.button("+ New Account", on_click=lambda: dialog.open()).classes(
            BUTTON_PRIMARY
        )

    container = ui.column().classes("w-full gap-4")

    async def refresh() -> None:
        if api is None:
            return
        entity_id = state.selected_entity_id
        if entity_id is None:
            help_text.text = "Select an entity in the header to view accounts."
            help_text.update()
            new_btn.disable()
            container.clear()
            return

        new_btn.enable()
        help_text.text = ""
        help_text.update()

        accounts = await api.list_accounts(entity_id=entity_id)
        state.accounts = accounts
        grouped = _group_by_type(accounts)

        container.clear()
        for group_name in [
            "asset",
            "liability",
            "equity",
            "income",
            "expense",
            "other",
        ]:
            rows = grouped.get(group_name)
            if not rows:
                continue
            with container:
                with ui.card().classes(f"{CARD} {CARD_PAD} w-full"):
                    ui.label(group_name.capitalize()).classes(
                        "text-sm font-semibold text-slate-700"
                    )
                    data_table(columns=columns, rows=rows, row_key="id")

    with dialog:
        with card:
            name_in = ui.input("Name").props("autofocus").classes("w-full")
            atype = (
                ui.select(
                    options={o["value"]: o["label"] for o in ACCOUNT_TYPES},
                    label="Type",
                    value="asset",
                )
                .props("dense outlined")
                .classes("w-full")
            )
            sub_type = (
                ui.select(
                    options={o["value"]: o["label"] for o in ACCOUNT_SUB_TYPES},
                    label="Sub-Type",
                    value="checking",
                )
                .props("dense outlined")
                .classes("w-full")
            )
            currency = ui.input("Currency").props("dense").classes("w-full")
            currency.value = "USD"

            error = ui.label("").classes("text-rose-700")

            async def submit() -> None:
                if api is None:
                    return
                entity_id = state.selected_entity_id
                if entity_id is None:
                    error.text = "Select an entity in the header first"
                    error.update()
                    return
                name = str(name_in.value or "").strip()
                if not name:
                    error.text = "Name is required"
                    error.update()
                    return
                try:
                    await api.create_account(
                        name=name,
                        entity_id=entity_id,
                        account_type=str(atype.value),
                        sub_type=str(sub_type.value),
                        currency=str(currency.value or "USD").upper(),
                    )
                except APIError as e:
                    error.text = e.detail
                    error.update()
                    return
                dialog.close()
                await refresh()

            with ui.row().classes("w-full justify-end gap-2 pt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Create Account", on_click=submit).classes(BUTTON_PRIMARY)

    ui.timer(0.05, refresh, once=True)
