"""Git Orchestrator client port and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx


class GOClientError(Exception):
    """Raised when a Git Orchestrator client call fails."""

    def __init__(self, message: str, response: httpx.Response | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.response = response


class GOClient(ABC):
    """Outbound port for submitting import proposals to GO."""

    @abstractmethod
    def get_current_head(self, space_id: str) -> str:
        """Return the current HEAD SHA of the Space target branch."""

    @abstractmethod
    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit a proposal to GO and return the created proposal record."""


class HttpGOClient(GOClient):
    """Production client calling the Git Orchestrator service over HTTP."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url)

    def get_current_head(self, space_id: str) -> str:
        url = f"{self.base_url}/api/kb/v1/spaces/{space_id}/merge-rules"
        try:
            response = self._client.get(url, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GOClientError(f"GO merge-rules request failed: {exc}") from exc

        data = response.json()
        if not isinstance(data, dict) or "head_sha" not in data:
            raise GOClientError(
                "GO merge-rules response missing required field 'head_sha'",
                response=response,
            )
        return str(data["head_sha"])

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/kb/v1/proposals"
        try:
            response = self._client.post(url, json=payload, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GOClientError(f"GO proposal submission failed: {exc}") from exc

        data = response.json()
        if not isinstance(data, dict) or "id" not in data:
            raise GOClientError(
                "GO proposal response missing required field 'id'",
                response=response,
            )
        return data


class StubGOClient(GOClient):
    """In-memory stub for unit tests."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = state or {}
        self.calls: list[dict[str, Any]] = []

    def get_current_head(self, space_id: str) -> str:
        return str(self.state.get("head_sha", "0" * 40))

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"submit_proposal": payload})
        return {
            "id": self.state.get("proposal_id", "00000000-0000-0000-0000-000000000001"),
            "space_id": payload["space_id"],
            "proposal_sha": payload["proposal_sha"],
            "base_sha": payload["base_sha"],
            "status": "in_review",
            "idempotency_key": payload["idempotency_key"],
        }
