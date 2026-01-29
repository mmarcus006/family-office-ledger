# pyright: reportMissingImports=false

"""Transactions page."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from nicegui import ui  # pyright: ignore[reportMissingImports]

from family_office_ledger.ui.api_client import APIError, api
from family_office_ledger.ui.constants import (
    BUTTON_PRIMARY,
    BUTTON_SECONDARY,
    CARD,
    CARD_PAD,
)
from family_office_ledger.ui.state import state


def _parse_money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")


@dataclass(slots=True)
class EntryRow:
    account_id: str = ""
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    memo: str = ""


def render() -> None:
    ui.label("Transactions").classes("text-xl font-semibold text-slate-900")

    tabs = ui.tabs().classes("w-full")
    entry_tab = ui.tab("Entry")
    history_tab = ui.tab("History")

    with ui.tab_panels(tabs, value=entry_tab).classes("w-full"):
        with ui.tab_panel(entry_tab):
            _render_entry()
        with ui.tab_panel(history_tab):
            _render_history()


def _render_entry() -> None:
    if api is None:
        ui.label("Frontend dependencies are missing.").classes("text-rose-700")
        return

    rows: list[EntryRow] = [EntryRow(), EntryRow()]

    account_select_options: dict[str, str] = {"": "Select account"}

    with ui.row().classes("w-full gap-3"):
        date_in = ui.input("Date").props("dense outlined")
        date_in.value = date.today().isoformat()
        ref_in = ui.input("Reference").props("dense outlined").classes("flex-1")

    memo_in = ui.input("Memo").props("dense outlined").classes("w-full")

    entries_container = ui.column().classes("w-full gap-2")

    with ui.row().classes("w-full items-center justify-between pt-3"):
        totals = ui.label("").classes("text-slate-700")
        with ui.row().classes("gap-2"):
            ui.button("Clear", on_click=lambda: clear()).classes(BUTTON_SECONDARY)
            post_btn = ui.button("Post Transaction").classes(BUTTON_PRIMARY)

    error = ui.label("").classes("text-rose-700")

    post_btn.disable()

    def recalc() -> None:
        total_debit = sum((r.debit for r in rows), start=Decimal("0"))
        total_credit = sum((r.credit for r in rows), start=Decimal("0"))
        diff = total_debit - total_credit

        balanced = diff == Decimal("0")
        totals.text = (
            f"Total Debits: ${total_debit:.2f}   "
            f"Total Credits: ${total_credit:.2f}   "
            f"Difference: ${diff:.2f}"
        )
        totals.update()

        valid_rows = [
            r for r in rows if r.account_id and (r.debit != 0 or r.credit != 0)
        ]
        min_entries_ok = len(valid_rows) >= 2
        has_debit = any(r.debit != 0 for r in valid_rows)
        has_credit = any(r.credit != 0 for r in valid_rows)

        can_post = balanced and min_entries_ok and has_debit and has_credit
        if can_post:
            post_btn.enable()
            error.text = ""
            error.update()
        else:
            post_btn.disable()
            error.text = "Transaction must balance" if not balanced else ""
            error.update()

    def add_row() -> None:
        rows.append(EntryRow())
        render_rows()
        recalc()

    def render_rows() -> None:
        entries_container.clear()
        with entries_container, ui.card().classes(f"{CARD} {CARD_PAD} w-full"):
            ui.label("Journal Entries").classes("text-sm font-semibold text-slate-700")
            with ui.column().classes("w-full gap-2 pt-2"):
                for idx, row in enumerate(rows):
                    with ui.row().classes("w-full gap-2 items-center"):
                        sel = (
                            ui.select(
                                options=account_select_options,
                                value=row.account_id,
                                label="Account",
                            )
                            .props("dense outlined")
                            .classes("w-80")
                        )

                        debit_in = (
                            ui.number(
                                label="Debit",
                                format="%.2f",
                                value=float(row.debit),
                            )
                            .props("dense outlined")
                            .classes("w-36")
                        )

                        credit_in = (
                            ui.number(
                                label="Credit",
                                format="%.2f",
                                value=float(row.credit),
                            )
                            .props("dense outlined")
                            .classes("w-36")
                        )

                        memo = (
                            ui.input("Memo").props("dense outlined").classes("flex-1")
                        )
                        memo.value = row.memo

                        def _on_account_change(e: Any, i: int = idx) -> None:
                            rows[i].account_id = str(e.value or "")
                            recalc()

                        def _on_debit_change(e: Any, i: int = idx) -> None:
                            rows[i].debit = _parse_money(e.value)
                            recalc()

                        def _on_credit_change(e: Any, i: int = idx) -> None:
                            rows[i].credit = _parse_money(e.value)
                            recalc()

                        def _on_memo_change(e: Any, i: int = idx) -> None:
                            rows[i].memo = str(e.value or "")

                        sel.on("update:model-value", _on_account_change)
                        debit_in.on("update:model-value", _on_debit_change)
                        credit_in.on("update:model-value", _on_credit_change)
                        memo.on("update:model-value", _on_memo_change)

                with ui.row().classes("w-full justify-end pt-2"):
                    ui.button("+ Add Row", on_click=add_row).classes(BUTTON_SECONDARY)

    async def load_accounts() -> None:
        entity_id = state.selected_entity_id
        accounts = await api.list_accounts(entity_id=entity_id) if entity_id else []
        state.accounts = accounts

        account_select_options.clear()
        account_select_options[""] = "Select account"
        for a in accounts:
            account_select_options[str(a["id"])] = str(a["name"])

        render_rows()
        recalc()

    async def post() -> None:
        try:
            txn_date = date.fromisoformat(str(date_in.value))
        except Exception:
            error.text = "Invalid date"
            error.update()
            return

        payload_entries: list[dict[str, Any]] = []
        for r in rows:
            if not r.account_id:
                continue
            if r.debit == 0 and r.credit == 0:
                continue
            payload_entries.append(
                {
                    "account_id": r.account_id,
                    "debit_amount": str(r.debit),
                    "credit_amount": str(r.credit),
                    "memo": r.memo,
                }
            )

        try:
            await api.post_transaction(
                transaction_date=txn_date,
                entries=payload_entries,
                memo=str(memo_in.value or ""),
                reference=str(ref_in.value or ""),
            )
        except APIError as e:
            error.text = e.detail
            error.update()
            return

        ui.notify("Transaction posted", type="positive", position="top")
        clear()

    def clear() -> None:
        memo_in.value = ""
        ref_in.value = ""
        rows[:] = [EntryRow(), EntryRow()]
        render_rows()
        recalc()

    post_btn.on("click", lambda _: post())

    ui.timer(0.05, load_accounts, once=True)


def _render_history() -> None:
    if api is None:
        ui.label("Frontend dependencies are missing.").classes("text-rose-700")
        return

    ui.label("History").classes("text-sm font-semibold text-slate-700")

    account_options: dict[str, str] = {"": "All accounts"}

    with ui.row().classes("w-full gap-2 items-end"):
        account_select = ui.select(
            options=account_options,
            label="Account",
            value="",
        ).props("dense outlined")

        start_in = ui.input("From").props("dense outlined")
        end_in = ui.input("To").props("dense outlined")
        start_in.value = (date.today() - timedelta(days=30)).isoformat()
        end_in.value = date.today().isoformat()

        apply_btn = ui.button("Apply").classes(BUTTON_SECONDARY)

    error = ui.label("").classes("text-rose-700")

    columns = [
        {"name": "transaction_date", "label": "Date", "field": "transaction_date"},
        {"name": "reference", "label": "Reference", "field": "reference"},
        {"name": "memo", "label": "Memo", "field": "memo"},
        {"name": "entries", "label": "Entries", "field": "entries"},
    ]
    table = ui.table(columns=columns, rows=[], row_key="id", pagination=25).classes(
        "w-full"
    )

    def _format_entries(txn: dict[str, Any]) -> str:
        parts: list[str] = []
        for e in txn.get("entries", []) or []:
            acc_id = str(e.get("account_id"))
            name = next(
                (a["name"] for a in state.accounts if str(a.get("id")) == acc_id),
                acc_id[:8],
            )
            debit = str(e.get("debit_amount", "0"))
            credit = str(e.get("credit_amount", "0"))
            if debit != "0" and debit != "0.00":
                parts.append(f"{name} +{debit}")
            if credit != "0" and credit != "0.00":
                parts.append(f"{name} -{credit}")
        return ", ".join(parts)

    async def load_accounts() -> None:
        entity_id = state.selected_entity_id
        accounts = await api.list_accounts(entity_id=entity_id) if entity_id else []
        state.accounts = accounts
        account_options.clear()
        account_options[""] = "All accounts"
        for a in accounts:
            account_options[str(a["id"])] = str(a["name"])
        account_select.update()

    async def apply_filters() -> None:
        error.text = ""
        error.update()

        try:
            start = date.fromisoformat(str(start_in.value))
            end = date.fromisoformat(str(end_in.value))
        except Exception:
            error.text = "Invalid date range"
            error.update()
            return

        account_id = str(account_select.value or "")
        kwargs: dict[str, Any] = {}
        if account_id:
            kwargs["account_id"] = account_id
        else:
            kwargs["start_date"] = start
            kwargs["end_date"] = end

        txns = await api.list_transactions(**kwargs)
        rows: list[dict[str, Any]] = []
        for t in txns:
            row = dict(t)
            row["entries"] = _format_entries(t)
            rows.append(row)
        table.rows = rows
        table.update()

    apply_btn.on("click", lambda _: apply_filters())

    ui.timer(0.05, load_accounts, once=True)
    ui.timer(0.1, apply_filters, once=True)
