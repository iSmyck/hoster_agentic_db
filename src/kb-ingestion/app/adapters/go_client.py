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

    @abstractmethod
    def auto_merge(self, proposal_id: str, *, decision_data: dict[str, Any]) -> dict[str, Any]:
        """Record a source_sync DecisionRecord and merge without a human actor."""


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

    def auto_merge(self, proposal_id: str, *, decision_data: dict[str, Any]) -> dict[str, Any]:
        decision_url = f"{self.base_url}/api/kb/v1/decisions"
        merge_url = f"{self.base_url}/api/kb/v1/proposals/{proposal_id}/merge"
        try:
            decision = self._client.post(
                decision_url,
                json={
                    "proposal_id": proposal_id,
                    "action": "accepted",
                    "actor_id": "source-sync-bot",
                    "idempotency_key": f"source-sync:{proposal_id}",
                    "decision_data": decision_data,
                },
                timeout=30,
            )
            decision.raise_for_status()
            merged = self._client.post(merge_url, timeout=30)
            merged.raise_for_status()
        except httpx.HTTPError as exc:
            raise GOClientError(f"GO auto-merge failed: {exc}") from exc
        try:
            data = merged.json()
        except ValueError as exc:
            raise GOClientError("GO merge response is not valid JSON") from exc
        if not isinstance(data, dict):
            raise GOClientError("GO merge response is not an object")
        return data


class StubGOClient(GOClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []
        self.merges: list[str] = []
        self.fail_message: str | None = None
        self.return_empty_id: bool = False
        self.proposals: dict[str, dict[str, Any]] = {}

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.fail_message:
            raise GOClientError(self.fail_message)
        if self.return_empty_id:
            return {}
        required = ("space_id", "proposal_sha", "base_sha", "idempotency_key")
        missing = [key for key in required if key not in payload]
        if missing:
            raise GOClientError(f"GO payload missing {', '.join(missing)}")
        self.calls.append(payload)
        index = len(self.calls)
        record = {
            "id": f"00000000-0000-0000-0000-{index:012d}",
            "space_id": payload["space_id"],
            "proposal_sha": payload["proposal_sha"],
            "base_sha": payload["base_sha"],
            "status": "in_review",
            "idempotency_key": payload["idempotency_key"],
            "proposal_data": payload.get("proposal_data", {}),
        }
        self.proposals[record["id"]] = record
        return record

    def auto_merge(self, proposal_id: str, *, decision_data: dict[str, Any]) -> dict[str, Any]:
        if self.fail_message:
            raise GOClientError(self.fail_message)
        existing = self.proposals.get(proposal_id)
        if existing is None:
            raise GOClientError(f"proposal {proposal_id} not found")
        existing["status"] = "merged"
        self.merges.append(proposal_id)
        decision = {
            "proposal_id": proposal_id,
            "actor_id": "source-sync-bot",
            "outcome": "accepted",
            "decision_data": decision_data,
        }
        self.decisions.append(decision)
        return {"proposal_id": proposal_id, "status": "merged", "decision": decision}
