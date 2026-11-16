"""Git Orchestrator client port for structure submit (KBI.2.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx


class GOClientError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GOClient(ABC):
    @abstractmethod
    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/kb/v1/proposals and return the created record."""


class HttpGOClient(GOClient):
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url)

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/kb/v1/proposals"
        try:
            response = self._client.post(url, json=payload, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GOClientError(f"GO proposal submission failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise GOClientError("GO proposal response is not valid JSON") from exc
        if not isinstance(data, dict) or "id" not in data:
            raise GOClientError("GO proposal response missing required field 'id'")
        return data


class StubGOClient(GOClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail_message: str | None = None

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.fail_message:
            raise GOClientError(self.fail_message)
        required = ("space_id", "proposal_sha", "base_sha", "idempotency_key")
        missing = [key for key in required if key not in payload]
        if missing:
            raise GOClientError(f"GO payload missing {', '.join(missing)}")
        self.calls.append(payload)
        index = len(self.calls)
        return {
            "id": f"00000000-0000-0000-0000-{index:012d}",
            "space_id": payload["space_id"],
            "proposal_sha": payload["proposal_sha"],
            "base_sha": payload["base_sha"],
            "status": "in_review",
            "idempotency_key": payload["idempotency_key"],
            "proposal_data": payload.get("proposal_data", {}),
        }
