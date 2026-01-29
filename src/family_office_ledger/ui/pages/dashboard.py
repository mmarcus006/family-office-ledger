# pyright: reportMissingImports=false

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.api_client import api
from family_office_ledger.ui.constants import CARD, CARD_PAD


def render() -> None:
    ui.label("Dashboard").classes("text-xl font-semibold text-slate-900")

    if api is None:
        ui.label("Frontend dependencies are missing.").classes("text-rose-700")
        return

    asof_in = ui.input("As of").props("dense outlined")
    asof_in.value = date.today().isoformat()

    cards = ui.row().classes("w-full gap-3")
    charts_row = ui.row().classes("w-full gap-3")
    recent_card = ui.card().classes(f"{CARD} {CARD_PAD} w-full")

    async def refresh() -> None:
        try:
            as_of = date.fromisoformat(str(asof_in.value))
        except Exception:
            as_of = date.today()

        report = await api.net_worth_report(as_of_date=as_of)
        totals = report.get("totals", {})

        cards.clear()
        with cards:
            for label, key in [
                ("Net Worth", "net_worth"),
                ("Total Assets", "total_assets"),
                ("Liabilities", "total_liabilities"),
            ]:
                with ui.card().classes(f"{CARD} {CARD_PAD} w-64"):
                    ui.label(label).classes(
                        "text-xs uppercase tracking-wide text-slate-500"
                    )
                    ui.label(str(totals.get(key, "0"))).classes(
                        "text-2xl font-semibold text-slate-900"
                    )

        start = as_of - timedelta(days=90)
        type_summary = await api.transaction_summary_by_type(
            start_date=start, end_date=as_of
        )
        entity_summary = await api.transaction_summary_by_entity(
            start_date=start, end_date=as_of
        )

        charts_row.clear()
        with charts_row:
            with ui.card().classes(f"{CARD} {CARD_PAD} flex-1"):
                ui.label("Transactions by Type (90 days)").classes(
                    "text-sm font-semibold mb-2"
                )
                type_data = type_summary.get("data", [])
                if type_data:
                    type_rows = [
                        {
                            "type": item.get("transaction_type", ""),
                            "count": item.get("count", 0),
                            "amount": item.get("total_amount", "0"),
                        }
                        for item in type_data
                    ]
                    ui.table(
                        columns=[
                            {"name": "type", "label": "Type", "field": "type"},
                            {"name": "count", "label": "Count", "field": "count"},
                            {"name": "amount", "label": "Amount", "field": "amount"},
                        ],
                        rows=type_rows,
                        row_key="type",
                    ).classes("w-full")
                else:
                    ui.label("No transactions in period").classes("text-slate-500")

            with ui.card().classes(f"{CARD} {CARD_PAD} flex-1"):
                ui.label("Transactions by Entity (90 days)").classes(
                    "text-sm font-semibold mb-2"
                )
                entity_data = entity_summary.get("data", [])
                if entity_data:
                    entity_rows = [
                        {
                            "entity": item.get("entity_name", ""),
                            "count": item.get("transaction_count", 0),
                            "amount": item.get("total_amount", "0"),
                        }
                        for item in entity_data
                    ]
                    ui.table(
                        columns=[
                            {"name": "entity", "label": "Entity", "field": "entity"},
                            {"name": "count", "label": "Count", "field": "count"},
                            {"name": "amount", "label": "Amount", "field": "amount"},
                        ],
                        rows=entity_rows,
                        row_key="entity",
                    ).classes("w-full")
                else:
                    ui.label("No transactions in period").classes("text-slate-500")

        recent_card.clear()
        with recent_card:
            ui.label("Recent Transactions").classes("text-sm font-semibold")
            txns = await api.list_transactions(start_date=start, end_date=as_of)
            txns = list(reversed(txns))[:10]
            rows: list[dict[str, Any]] = []
            for t in txns:
                rows.append(
                    {
                        "id": t.get("id"),
                        "transaction_date": t.get("transaction_date"),
                        "memo": t.get("memo"),
                        "reference": t.get("reference"),
                    }
                )
            ui.table(
                columns=[
                    {
                        "name": "transaction_date",
                        "label": "Date",
                        "field": "transaction_date",
                    },
                    {"name": "reference", "label": "Ref", "field": "reference"},
                    {"name": "memo", "label": "Memo", "field": "memo"},
                ],
                rows=rows,
                row_key="id",
                pagination=10,
            ).classes("w-full")

    with ui.row().classes("w-full items-end gap-2"):
        asof_in  # noqa: B018 - NiceGUI element placement
        ui.button("Refresh", on_click=refresh).props("dense")

    with ui.column().classes("w-full gap-3 pt-3"):
        cards  # noqa: B018 - NiceGUI element placement
        charts_row  # noqa: B018 - NiceGUI element placement
        recent_card  # noqa: B018 - NiceGUI element placement

    ui.timer(0.05, refresh, once=True)
