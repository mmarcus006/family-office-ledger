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
    entity_ids: Sequence[str | UUID],
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


# ============================================
# Audit Endpoints
# ============================================
def list_audit_entries(
    entity_type: str | None = None,
    action: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List audit entries with optional filters."""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if entity_type:
        params["entity_type"] = entity_type
    if action:
        params["action"] = action
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    with _client() as client:
        r = client.get("/audit/entries", params=params)
        return _handle_response(r)


def get_audit_entry(entry_id: str | UUID) -> dict[str, Any]:
    """Get a specific audit entry."""
    with _client() as client:
        r = client.get(f"/audit/entries/{entry_id}")
        return _handle_response(r)


def list_entity_audit_trail(
    entity_type: str,
    entity_id: str | UUID,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Get audit trail for a specific entity."""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    with _client() as client:
        r = client.get(f"/audit/entities/{entity_type}/{entity_id}", params=params)
        return _handle_response(r)


def get_audit_summary(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Get audit summary statistics."""
    params: dict[str, Any] = {}
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    with _client() as client:
        r = client.get("/audit/summary", params=params)
        return _handle_response(r)


# ============================================
# Currency Endpoints
# ============================================
def add_exchange_rate(
    from_currency: str,
    to_currency: str,
    rate: str,
    effective_date: date,
    source: str = "manual",
) -> dict[str, Any]:
    """Add a new exchange rate."""
    with _client() as client:
        r = client.post(
            "/currency/rates",
            json={
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "effective_date": effective_date.isoformat(),
                "source": source,
            },
        )
        return _handle_response(r)


def list_exchange_rates(
    from_currency: str | None = None,
    to_currency: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """List exchange rates with optional filters."""
    params: dict[str, Any] = {}
    if from_currency:
        params["from_currency"] = from_currency
    if to_currency:
        params["to_currency"] = to_currency
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    with _client() as client:
        r = client.get("/currency/rates", params=params)
        return _handle_response(r)


def get_latest_exchange_rate(from_currency: str, to_currency: str) -> dict[str, Any]:
    """Get the latest exchange rate for a currency pair."""
    with _client() as client:
        r = client.get(
            "/currency/rates/latest",
            params={"from_currency": from_currency, "to_currency": to_currency},
        )
        return _handle_response(r)


def get_exchange_rate(rate_id: str | UUID) -> dict[str, Any]:
    """Get a specific exchange rate by ID."""
    with _client() as client:
        r = client.get(f"/currency/rates/{rate_id}")
        return _handle_response(r)


def delete_exchange_rate(rate_id: str | UUID) -> None:
    """Delete an exchange rate."""
    with _client() as client:
        r = client.delete(f"/currency/rates/{rate_id}")
        if r.status_code >= 400:
            _handle_response(r)


def convert_currency(
    amount: str,
    from_currency: str,
    to_currency: str,
    as_of_date: date,
) -> dict[str, Any]:
    """Convert an amount from one currency to another."""
    with _client() as client:
        r = client.post(
            "/currency/convert",
            json={
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "as_of_date": as_of_date.isoformat(),
            },
        )
        return _handle_response(r)


# ============================================
# Portfolio Endpoints
# ============================================
def get_asset_allocation(
    entity_ids: list[str] | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Get asset allocation report."""
    params: dict[str, Any] = {}
    if entity_ids:
        params["entity_ids"] = entity_ids
    if as_of_date:
        params["as_of_date"] = as_of_date.isoformat()
    with _client() as client:
        r = client.get("/portfolio/allocation", params=params)
        return _handle_response(r)


def get_concentration_report(
    entity_ids: list[str] | None = None,
    as_of_date: date | None = None,
    top_n: int = 20,
) -> dict[str, Any]:
    """Get portfolio concentration report."""
    params: dict[str, Any] = {"top_n": top_n}
    if entity_ids:
        params["entity_ids"] = entity_ids
    if as_of_date:
        params["as_of_date"] = as_of_date.isoformat()
    with _client() as client:
        r = client.get("/portfolio/concentration", params=params)
        return _handle_response(r)


def get_performance_report(
    start_date: date,
    end_date: date,
    entity_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Get portfolio performance report."""
    params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    if entity_ids:
        params["entity_ids"] = entity_ids
    with _client() as client:
        r = client.get("/portfolio/performance", params=params)
        return _handle_response(r)


def get_portfolio_summary(
    entity_ids: list[str] | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Get portfolio summary."""
    params: dict[str, Any] = {}
    if entity_ids:
        params["entity_ids"] = entity_ids
    if as_of_date:
        params["as_of_date"] = as_of_date.isoformat()
    with _client() as client:
        r = client.get("/portfolio/summary", params=params)
        return _handle_response(r)


# ============================================
# QSBS Endpoints
# ============================================
def list_qsbs_securities() -> list[dict[str, Any]]:
    """List QSBS-eligible securities."""
    with _client() as client:
        r = client.get("/qsbs/securities")
        return _handle_response(r)


def mark_security_qsbs_eligible(
    security_id: str | UUID,
    qualification_date: date,
) -> dict[str, Any]:
    """Mark a security as QSBS-eligible."""
    with _client() as client:
        r = client.post(
            f"/qsbs/securities/{security_id}/mark-eligible",
            json={"qualification_date": qualification_date.isoformat()},
        )
        return _handle_response(r)


def remove_security_qsbs_eligibility(security_id: str | UUID) -> dict[str, Any]:
    """Remove QSBS eligibility from a security."""
    with _client() as client:
        r = client.post(f"/qsbs/securities/{security_id}/remove-eligible")
        return _handle_response(r)


def get_qsbs_summary(
    entity_ids: list[str] | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Get QSBS summary."""
    params: dict[str, Any] = {}
    if entity_ids:
        params["entity_ids"] = entity_ids
    if as_of_date:
        params["as_of_date"] = as_of_date.isoformat()
    with _client() as client:
        r = client.get("/qsbs/summary", params=params)
        return _handle_response(r)


# ============================================
# Tax Endpoints
# ============================================
def generate_tax_documents(
    entity_id: str | UUID,
    tax_year: int,
    lot_proceeds: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate tax documents for an entity."""
    payload: dict[str, Any] = {"tax_year": tax_year}
    if lot_proceeds:
        payload["lot_proceeds"] = lot_proceeds
    with _client() as client:
        r = client.post(f"/tax/entities/{entity_id}/documents", json=payload)
        return _handle_response(r)


def get_tax_summary(entity_id: str | UUID, tax_year: int) -> dict[str, Any]:
    """Get tax summary for an entity."""
    with _client() as client:
        r = client.get(
            f"/tax/entities/{entity_id}/summary",
            params={"tax_year": tax_year},
        )
        return _handle_response(r)


def get_form_8949_csv(entity_id: str | UUID, tax_year: int) -> str:
    """Get Form 8949 as CSV."""
    with _client() as client:
        r = client.get(
            f"/tax/entities/{entity_id}/form-8949/csv",
            params={"tax_year": tax_year},
        )
        if r.status_code >= 400:
            _handle_response(r)
        return r.text


def get_schedule_d(entity_id: str | UUID, tax_year: int) -> dict[str, Any]:
    """Get Schedule D for an entity."""
    with _client() as client:
        r = client.get(
            f"/tax/entities/{entity_id}/schedule-d",
            params={"tax_year": tax_year},
        )
        return _handle_response(r)
