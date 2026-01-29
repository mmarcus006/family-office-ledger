from __future__ import annotations

import pytest


class TestWorkflows:
    def test_frontend_entrypoint_import(self) -> None:
        pytest.importorskip("nicegui")
        from family_office_ledger.ui.main import create_ui

        assert callable(create_ui)
