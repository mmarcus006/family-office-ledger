"""HTTP client for the FastAPI backend."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

import httpx
import streamlit as st


def get_api_url() -> str:
    return st.session_state.get("api_url", "http://localhost:8000")


def _client() -> httpx.Client:
    return httpx.Client(base_url=get_api_url(), timeout=30.0)


class APIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error {status_code}: {detail}")


def _handle_response(response: httpx.Response) -> Any:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise APIError(response.status_code, str(detail))
    return response.json()


def list_entities() -> list[dict[str, Any]]:
    with _client() as client:
        r = client.get("/entities")
        return _handle_response(r)


def get_entity(entity_id: str | UUID) -> dict[str, Any]:
    with _client() as client:
        r = client.get(f"/entities/{entity_id}")
        return _handle_response(r)


def create_entity(
    name: str,
    entity_type: str,
    fiscal_year_end: date | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "entity_type": entity_type}
    if fiscal_year_end:
        payload["fiscal_year_end"] = fiscal_year_end.isoformat()
    with _client() as client:
        r = client.post("/entities", json=payload)
        return _handle_response(r)


def list_accounts(entity_id: str | UUID | None = None) -> list[dict[str, Any]]:
    params = {}
    if entity_id:
        params["entity_id"] = str(entity_id)
    with _client() as client:
        r = client.get("/accounts", params=params)
        return _handle_response(r)


def create_account(
    name: str,
    entity_id: str | UUID,
    account_type: str,
    sub_type: str = "other",
    currency: str = "USD",
) -> dict[str, Any]:
    with _client() as client:
        r = client.post(
            "/accounts",
            json={
                "name": name,
                "entity_id": str(entity_id),
                "account_type": account_type,
                "sub_type": sub_type,
                "currency": currency,
            },
        )
        return _handle_response(r)


def list_transactions(
    account_id: str | UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, str] = {}
    if account_id:
        params["account_id"] = str(account_id)
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    with _client() as client:
        r = client.get("/transactions", params=params)
        return _handle_response(r)


def post_transaction(
    transaction_date: date,
    entries: list[dict[str, Any]],
    memo: str = "",
    reference: str = "",
) -> dict[str, Any]:
    with _client() as client:
        r = client.post(
            "/transactions",
            json={
                "transaction_date": transaction_date.isoformat(),
                "entries": entries,
                "memo": memo,
                "reference": reference,
            },
        )
        return _handle_response(r)


def net_worth_report(
    as_of_date: date,
    entity_ids: list[str] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"as_of_date": as_of_date.isoformat()}
    if entity_ids:
        params["entity_ids"] = entity_ids
    with _client() as client:
        r = client.get("/reports/net-worth", params=params)
        return _handle_response(r)


def balance_sheet(entity_id: str | UUID, as_of_date: date) -> dict[str, Any]:
    with _client() as client:
        r = client.get(
            f"/reports/balance-sheet/{entity_id}",
            params={"as_of_date": as_of_date.isoformat()},
        )
        return _handle_response(r)


def health_check() -> dict[str, Any]:
    with _client() as client:
        r = client.get("/health")
        return _handle_response(r)


# Additional Report Endpoints
def transaction_summary_by_type(
    start_date: date,
    end_date: date,
    entity_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Get transaction summary grouped by account type."""
    params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    if entity_ids:
        params["entity_ids"] = entity_ids
    with _client() as client:
        r = client.get("/reports/summary-by-type", params=params)
        return _handle_response(r)


def transaction_summary_by_entity(
    start_date: date,
    end_date: date,
    entity_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Get transaction summary grouped by entity."""
    params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    if entity_ids:
        params["entity_ids"] = entity_ids
    with _client() as client:
        r = client.get("/reports/summary-by-entity", params=params)
        return _handle_response(r)


def dashboard_summary(
    as_of_date: date,
    entity_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Get dashboard summary data."""
    params: dict[str, Any] = {"as_of_date": as_of_date.isoformat()}
    if entity_ids:
        params["entity_ids"] = entity_ids
    with _client() as client:
        r = client.get("/reports/dashboard", params=params)
        return _handle_response(r)


# Reconciliation Endpoints
def create_reconciliation_session(
    account_id: str | UUID,
    file_path: str,
    file_format: str,
) -> dict[str, Any]:
    """Create a new reconciliation session."""
    with _client() as client:
        r = client.post(
            "/reconciliation/sessions",
            json={
                "account_id": str(account_id),
                "file_path": file_path,
                "file_format": file_format,
            },
        )
        return _handle_response(r)


def get_reconciliation_session(session_id: str | UUID) -> dict[str, Any]:
    """Get a reconciliation session by ID."""
    with _client() as client:
        r = client.get(f"/reconciliation/sessions/{session_id}")
        return _handle_response(r)


def list_reconciliation_matches(
    session_id: str | UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List matches for a reconciliation session."""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    with _client() as client:
        r = client.get(f"/reconciliation/sessions/{session_id}/matches", params=params)
        return _handle_response(r)


def confirm_reconciliation_match(
    session_id: str | UUID,
    match_id: str | UUID,
) -> dict[str, Any]:
    """Confirm a reconciliation match."""
    with _client() as client:
        r = client.post(
            f"/reconciliation/sessions/{session_id}/matches/{match_id}/confirm"
        )
        return _handle_response(r)


def reject_reconciliation_match(
    session_id: str | UUID,
    match_id: str | UUID,
) -> dict[str, Any]:
    """Reject a reconciliation match."""
    with _client() as client:
        r = client.post(
            f"/reconciliation/sessions/{session_id}/matches/{match_id}/reject"
        )
        return _handle_response(r)


def skip_reconciliation_match(
    session_id: str | UUID,
    match_id: str | UUID,
) -> dict[str, Any]:
    """Skip a reconciliation match."""
    with _client() as client:
        r = client.post(
            f"/reconciliation/sessions/{session_id}/matches/{match_id}/skip"
        )
        return _handle_response(r)


def close_reconciliation_session(session_id: str | UUID) -> dict[str, Any]:
    """Close a reconciliation session."""
    with _client() as client:
        r = client.post(f"/reconciliation/sessions/{session_id}/close")
        return _handle_response(r)


def get_reconciliation_summary(session_id: str | UUID) -> dict[str, Any]:
    """Get reconciliation session summary statistics."""
    with _client() as client:
        r = client.get(f"/reconciliation/sessions/{session_id}/summary")
        return _handle_response(r)


# Transfer Matching Endpoints
def create_transfer_session(
    entity_ids: list[str | UUID],
    start_date: date,
    end_date: date,
    date_tolerance_days: int = 3,
) -> dict[str, Any]:
    """Create a new transfer matching session."""
    with _client() as client:
        r = client.post(
            "/transfers/sessions",
            json={
                "entity_ids": [str(eid) for eid in entity_ids],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "date_tolerance_days": date_tolerance_days,
            },
        )
        return _handle_response(r)


def get_transfer_session(session_id: str | UUID) -> dict[str, Any]:
    """Get a transfer matching session by ID."""
    with _client() as client:
        r = client.get(f"/transfers/sessions/{session_id}")
        return _handle_response(r)


def list_transfer_matches(
    session_id: str | UUID,
    status: str | None = None,
) -> dict[str, Any]:
    """List matches for a transfer session."""
    params: dict[str, Any] = {}
    if status:
        params["status"] = status
    with _client() as client:
        r = client.get(f"/transfers/sessions/{session_id}/matches", params=params)
        return _handle_response(r)


def confirm_transfer_match(
    session_id: str | UUID,
    match_id: str | UUID,
) -> dict[str, Any]:
    """Confirm a transfer match."""
    with _client() as client:
        r = client.post(f"/transfers/sessions/{session_id}/matches/{match_id}/confirm")
        return _handle_response(r)


def reject_transfer_match(
    session_id: str | UUID,
    match_id: str | UUID,
) -> dict[str, Any]:
    """Reject a transfer match."""
    with _client() as client:
        r = client.post(f"/transfers/sessions/{session_id}/matches/{match_id}/reject")
        return _handle_response(r)


def close_transfer_session(session_id: str | UUID) -> dict[str, Any]:
    """Close a transfer matching session."""
    with _client() as client:
        r = client.post(f"/transfers/sessions/{session_id}/close")
        return _handle_response(r)


def get_transfer_summary(session_id: str | UUID) -> dict[str, Any]:
    """Get transfer session summary statistics."""
    with _client() as client:
        r = client.get(f"/transfers/sessions/{session_id}/summary")
        return _handle_response(r)
