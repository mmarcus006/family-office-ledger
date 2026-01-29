# pyright: reportMissingImports=false

"""Table helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.constants import TABLE


def data_table(
    *,
    columns: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    row_key: str = "id",
    on_row_click: Callable[[dict[str, Any]], None] | None = None,
    pagination: int | dict[str, Any] = 25,
) -> Any:
    table = ui.table(
        columns=columns,
        rows=rows,
        row_key=row_key,
        pagination=pagination,
    ).classes(TABLE)

    if on_row_click is not None:
        table.on("rowClick", lambda e: on_row_click(e.args[1]))

    return table
