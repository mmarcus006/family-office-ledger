"""HTTP client wrapper for the backend API.

This module is designed to be importable even when the optional `frontend`
dependencies are not installed.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class APIError(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return f"APIError({self.status_code}): {self.detail}"


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d is not None else None


class LedgerAPIClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        client: Any | None = None,
        timeout: float = 30.0,
    ) -> None:
        try:
            httpx = importlib.import_module("httpx")  # pyright: ignore[reportMissingImports]
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "httpx is required for the frontend. Install with 'family-office-ledger[frontend]'."
            ) from e

        self._httpx = httpx
        self._client = (
            client
            if client is not None
            else httpx.AsyncClient(base_url=base_url, timeout=timeout)
        )
        self._base_url = base_url

    @property
    def base_url(self) -> str:
        return self._base_url

    def set_base_url(self, base_url: str) -> None:
        """Update base_url for the internal client.

        If a client was injected, this only updates the stored base_url.
        """
        self._base_url = base_url
        if hasattr(self._client, "base_url"):
            # httpx exposes base_url as a property
            self._client.base_url = self._httpx.URL(base_url)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        r = await self._client.request(method, path, params=params, json=json)
        if 200 <= r.status_code < 300:
            if r.status_code == 204:
                return None
            return r.json()

        detail = ""
        try:
            payload = r.json()
            raw_detail = payload.get("detail")
            detail = raw_detail if isinstance(raw_detail, str) else str(raw_detail)
        except Exception:
            detail = r.text

        raise APIError(status_code=r.status_code, detail=detail)

    async def list_entities(self) -> list[dict[str, Any]]:
        data = await self._request_json("GET", "/entities")
        assert isinstance(data, list)
        return data

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        fiscal_year_end: date | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "entity_type": entity_type}
        if fiscal_year_end is not None:
            payload["fiscal_year_end"] = fiscal_year_end.isoformat()
        data = await self._request_json("POST", "/entities", json=payload)
        assert isinstance(data, dict)
        return data

    async def list_accounts(
        self, entity_id: UUID | str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if entity_id is not None:
            params["entity_id"] = str(entity_id)
        data = await self._request_json("GET", "/accounts", params=params)
        assert isinstance(data, list)
        return data

    async def create_account(
        self,
        name: str,
        entity_id: UUID | str,
        account_type: str,
        sub_type: str = "other",
        currency: str = "USD",
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "entity_id": str(entity_id),
            "account_type": account_type,
            "sub_type": sub_type,
            "currency": currency,
        }
        data = await self._request_json("POST", "/accounts", json=payload)
        assert isinstance(data, dict)
        return data

    async def post_transaction(
        self,
        transaction_date: date,
        entries: list[dict[str, Any]],
        memo: str = "",
        reference: str = "",
    ) -> dict[str, Any]:
        payload = {
            "transaction_date": transaction_date.isoformat(),
            "entries": entries,
            "memo": memo,
            "reference": reference,
        }
        data = await self._request_json("POST", "/transactions", json=payload)
        assert isinstance(data, dict)
        return data

    async def list_transactions(
        self,
        *,
        account_id: UUID | str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if account_id is not None:
            params["account_id"] = str(account_id)
        if start_date is not None:
            params["start_date"] = _iso(start_date)
        if end_date is not None:
            params["end_date"] = _iso(end_date)
        data = await self._request_json("GET", "/transactions", params=params)
        assert isinstance(data, list)
        return data

    async def net_worth_report(
        self,
        *,
        as_of_date: date,
        entity_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"as_of_date": as_of_date.isoformat()}
        if entity_ids is not None:
            params["entity_ids"] = entity_ids
        data = await self._request_json("GET", "/reports/net-worth", params=params)
        assert isinstance(data, dict)
        return data

    async def balance_sheet(
        self,
        *,
        entity_id: UUID | str,
        as_of_date: date,
    ) -> dict[str, Any]:
        data = await self._request_json(
            "GET",
            f"/reports/balance-sheet/{entity_id}",
            params={"as_of_date": as_of_date.isoformat()},
        )
        assert isinstance(data, dict)
        return data


try:  # pragma: no cover
    importlib.import_module("httpx")  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover
    api: LedgerAPIClient | None = None
else:  # pragma: no cover
    api = LedgerAPIClient()
