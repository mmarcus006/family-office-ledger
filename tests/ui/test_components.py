from __future__ import annotations

import pytest


class TestComponents:
    def test_can_import_components_when_installed(self) -> None:
        pytest.importorskip("nicegui")

        from family_office_ledger.ui.components import forms, modals, nav, tables

        assert forms is not None
        assert modals is not None
        assert nav is not None
        assert tables is not None
