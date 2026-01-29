"""Fixtures for Streamlit app tests."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

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
def test_client(api_app):
    """Synchronous test client for the API."""
    from starlette.testclient import TestClient

    with TestClient(api_app) as client:
        yield client


@pytest.fixture
def mock_streamlit() -> Iterator[MagicMock]:
    """Mock streamlit module for import tests."""
    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.cache_data = lambda ttl=None: lambda f: f  # No-op decorator

    with patch.dict("sys.modules", {"streamlit": mock_st}):
        yield mock_st


@pytest.fixture
def mock_httpx_client(test_client) -> Iterator[MagicMock]:
    """Mock httpx.Client that routes to test_client."""

    class MockResponse:
        def __init__(self, response):
            self.status_code = response.status_code
            self._response = response

        def json(self) -> Any:
            return self._response.json()

        @property
        def text(self) -> str:
            return self._response.text

    class MockClient:
        def __init__(self, base_url: str, timeout: float = 30.0):
            self.base_url = base_url
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url: str, params: dict | None = None) -> MockResponse:
            return MockResponse(test_client.get(url, params=params))

        def post(self, url: str, json: dict | None = None) -> MockResponse:
            return MockResponse(test_client.post(url, json=json))

        def delete(self, url: str) -> MockResponse:
            return MockResponse(test_client.delete(url))

    with patch(
        "family_office_ledger.streamlit_app.api_client.httpx.Client", MockClient
    ):
        yield MockClient
