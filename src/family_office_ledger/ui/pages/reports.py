# pyright: reportMissingImports=false

"""Reports page."""

from __future__ import annotations

from datetime import date

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.api_client import APIError, api
from family_office_ledger.ui.constants import BUTTON_SECONDARY, CARD, CARD_PAD
from family_office_ledger.ui.state import state


def render() -> None:
    ui.label("Reports").classes("text-xl font-semibold text-slate-900")

    if api is None:
        ui.label("Frontend dependencies are missing.").classes("text-rose-700")
        return

    report_type = ui.select(
        options={"net_worth": "Net Worth", "balance_sheet": "Balance Sheet"},
        value="net_worth",
        label="Report",
    ).props("dense outlined")
    asof_in = ui.input("As of").props("dense outlined")
    asof_in.value = date.today().isoformat()

    entity_multi = ui.select(options={}, label="Entities").props(
        "dense outlined multiple use-chips"
    )

    error = ui.label("").classes("text-rose-700")

    output = ui.column().classes("w-full gap-3")

    async def load_entities() -> None:
        entities = await api.list_entities()
        state.entities = entities
        entity_multi.options = {str(e["id"]): str(e["name"]) for e in entities}
        entity_multi.update()

    async def generate() -> None:
        error.text = ""
        error.update()
        output.clear()

        try:
            as_of = date.fromisoformat(str(asof_in.value))
        except Exception:
            error.text = "Invalid as-of date"
            error.update()
            return

        selected_ids: list[str] | None
        if entity_multi.value:
            selected_ids = [str(v) for v in entity_multi.value]
        else:
            selected_ids = None

        try:
            if str(report_type.value) == "net_worth":
                report = await api.net_worth_report(
                    as_of_date=as_of, entity_ids=selected_ids
                )
            else:
                if state.selected_entity_id is None:
                    error.text = "Select an entity in the header for Balance Sheet"
                    error.update()
                    return
                report = await api.balance_sheet(
                    entity_id=state.selected_entity_id,
                    as_of_date=as_of,
                )
        except APIError as e:
            error.text = e.detail
            error.update()
            return

        with output:
            with ui.card().classes(f"{CARD} {CARD_PAD} w-full"):
                ui.label(str(report.get("report_name", "Report"))).classes(
                    "text-sm font-semibold text-slate-700"
                )

                totals = report.get("totals", {})
                if isinstance(totals, dict):
                    with ui.row().classes("w-full gap-6 pt-2"):
                        for k, v in totals.items():
                            with ui.column().classes("gap-0"):
                                ui.label(str(k).replace("_", " ").title()).classes(
                                    "text-xs uppercase tracking-wide text-slate-500"
                                )
                                ui.label(str(v)).classes("text-base font-semibold")

            data = report.get("data")
            if isinstance(data, list):
                if data:
                    columns = [
                        {"name": k, "label": k.replace("_", " ").title(), "field": k}
                        for k in data[0]
                    ]
                else:
                    columns = []
                ui.table(columns=columns, rows=data, row_key="entity_id").classes(
                    "w-full"
                )
            elif isinstance(data, dict):
                # Balance sheet: categories -> rows
                for section in ["assets", "liabilities", "equity"]:
                    rows = data.get(section)
                    if not isinstance(rows, list) or not rows:
                        continue
                    with ui.card().classes(f"{CARD} {CARD_PAD} w-full"):
                        ui.label(section.title()).classes("text-sm font-semibold")
                        cols = [
                            {
                                "name": "account_name",
                                "label": "Account",
                                "field": "account_name",
                            },
                            {"name": "balance", "label": "Balance", "field": "balance"},
                        ]
                        ui.table(columns=cols, rows=rows, row_key="account_id").classes(
                            "w-full"
                        )

    ui.timer(0.05, load_entities, once=True)

    with ui.row().classes("w-full gap-2 items-end"):
        report_type  # noqa: B018 - NiceGUI element placement
        asof_in  # noqa: B018 - NiceGUI element placement
        entity_multi  # noqa: B018 - NiceGUI element placement
        ui.button("Generate", on_click=generate).classes(BUTTON_SECONDARY)

    error  # noqa: B018 - NiceGUI element placement
    output  # noqa: B018 - NiceGUI element placement
