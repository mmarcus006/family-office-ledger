# pyright: reportMissingImports=false

"""Form field helpers."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.constants import INPUT


def money_input(
    label: str,
    *,
    on_change: Callable[[Decimal], None] | None = None,
) -> Any:
    inp = ui.number(label=label, format="%.2f", prefix="$", value=0).classes(INPUT)
    if on_change is not None:
        inp.on(
            "update:model-value",
            lambda e: on_change(Decimal(str(e.value or 0))),
        )
    return inp


def select_field(
    label: str,
    *,
    options: dict[str, str],
    value: str | None = None,
    on_change: Callable[[Any], None] | None = None,
) -> Any:
    sel = ui.select(options=options, label=label, value=value).props("dense outlined")
    if on_change is not None:
        sel.on("update:model-value", on_change)
    return sel


def date_field(label: str) -> Any:
    with ui.input(label=label).classes(INPUT) as inp:
        with inp.add_slot("append"):
            ui.icon("edit_calendar").classes("cursor-pointer").on(
                "click", lambda: menu.open()
            )
        menu: Any
        with ui.menu() as menu:
            ui.date(on_change=lambda e: (inp.set_value(e.value), menu.close()))
    return inp
