# pyright: reportMissingImports=false

"""NiceGUI entry point and routing."""

from __future__ import annotations

from typing import Any


def _require_nicegui() -> Any:
    try:
        from nicegui import ui
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "NiceGUI is required for the frontend. Install with 'family-office-ledger[frontend]'."
        ) from e
    return ui


def add_global_styles() -> None:
    ui = _require_nicegui()
    ui.add_head_html(
        """
<style type="text/tailwindcss">
  @layer components {
    .atlas-page {
      @apply bg-slate-50 min-h-screen;
    }
  }
</style>
"""
    )


def create_ui() -> None:
    ui = _require_nicegui()

    from family_office_ledger.ui.components.nav import header, sidebar
    from family_office_ledger.ui.pages import (
        accounts,
        dashboard,
        entities,
        reports,
        transactions,
    )

    def shell(page_title: str, render_fn: Any) -> None:
        add_global_styles()
        header()
        sidebar()
        with ui.column().classes("atlas-page"):  # noqa: SIM117
            with ui.column().classes("max-w-[1200px] w-full mx-auto p-6 gap-4"):
                ui.label(page_title).classes("sr-only")
                render_fn()

    @ui.page("/")  # type: ignore[untyped-decorator]
    def index() -> None:
        shell("Dashboard", dashboard.render)

    @ui.page("/entities")  # type: ignore[untyped-decorator]
    def entities_page() -> None:
        shell("Entities", entities.render)

    @ui.page("/accounts")  # type: ignore[untyped-decorator]
    def accounts_page() -> None:
        shell("Accounts", accounts.render)

    @ui.page("/transactions")  # type: ignore[untyped-decorator]
    def transactions_page() -> None:
        shell("Transactions", transactions.render)

    @ui.page("/reports")  # type: ignore[untyped-decorator]
    def reports_page() -> None:
        shell("Reports", reports.render)


def run(
    *, port: int = 3000, api_url: str = "http://localhost:8000", reload: bool = True
) -> None:
    ui = _require_nicegui()

    from family_office_ledger.ui.api_client import api

    if api is not None:
        api.set_base_url(api_url)

    create_ui()
    ui.run(title="Atlas Ledger", port=port, reload=reload)
