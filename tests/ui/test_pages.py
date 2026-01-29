from __future__ import annotations

import pytest


class TestPages:
    def test_can_import_pages_when_installed(self) -> None:
        pytest.importorskip("nicegui")
        from family_office_ledger.ui.pages import (
            accounts,
            dashboard,
            entities,
            reports,
            transactions,
        )

        assert callable(accounts.render)
        assert callable(dashboard.render)
        assert callable(entities.render)
        assert callable(reports.render)
        assert callable(transactions.render)
