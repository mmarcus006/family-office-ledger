from __future__ import annotations

import pytest


@pytest.fixture
def api_app():
    """Create a test instance of the backend API with an in-memory DB."""

    from family_office_ledger.api.app import create_app
    from family_office_ledger.repositories.sqlite import SQLiteDatabase

    app = create_app()
    db = SQLiteDatabase(":memory:", check_same_thread=False)
    db.initialize()

    app.dependency_overrides[SQLiteDatabase] = lambda: db
    try:
        yield app
    finally:
        db.close()


@pytest.fixture
async def api_client(api_app):
    """LedgerAPIClient wired to the in-process FastAPI app."""

    httpx = pytest.importorskip("httpx")
    from httpx import ASGITransport, AsyncClient

    from family_office_ledger.ui.api_client import LedgerAPIClient

    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://test"
    ) as c:
        yield LedgerAPIClient(base_url="http://test", client=c)
