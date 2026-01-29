# pyright: reportMissingImports=false

"""Dialog/modal helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui  # pyright: ignore[reportMissingImports]


def confirm_dialog(
    *,
    title: str,
    message: str,
    on_confirm: Callable[[], None],
    on_cancel: Callable[[], None] | None = None,
) -> Any:
    with ui.dialog() as dialog, ui.card().classes("w-[28rem]"):
        ui.label(title).classes("text-lg font-semibold")
        ui.label(message).classes("text-slate-700")
        with ui.row().classes("w-full justify-end gap-2"):

            def _cancel() -> None:
                if on_cancel:
                    on_cancel()
                dialog.close()

            def _confirm() -> None:
                on_confirm()
                dialog.close()

            ui.button("Cancel", on_click=_cancel).props("flat")
            ui.button("Confirm", on_click=_confirm).classes("bg-blue-600 text-white")
    return dialog


def form_dialog(title: str) -> tuple[Any, Any]:
    dialog = ui.dialog()
    with dialog:
        card = ui.card().classes("w-[32rem]")
        with card, ui.row().classes("w-full items-center justify-between"):
            ui.label(title).classes("text-lg font-semibold")
            ui.button(icon="close", on_click=dialog.close).props("flat round")
    return dialog, card
