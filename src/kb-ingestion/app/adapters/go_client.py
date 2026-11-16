"""Git Orchestrator client port for structure submit and live source-sync."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote

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
    """Live GO client. Session bearer and GitLab proposal branches are optional."""

    def __init__(
        self,
        base_url: str,
        client: httpx.Client | None = None,
        *,
        session_url: str = "",
        author_id: str = "author-1",
        approver_id: str = "approver-1",
        gitlab_url: str = "",
        gitlab_token: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url)
        self._session_url = session_url.rstrip("/")
        self._author_id = author_id
        self._approver_id = approver_id
        self._gitlab_url = gitlab_url.rstrip("/")
        self._gitlab_token = gitlab_token

    def _mint_token(self, stable_id: str, role: str) -> str:
        if not self._session_url:
            return ""
        try:
            response = httpx.post(
                f"{self._session_url}/api/kb/v1/session/create",
                json={"stable_id": stable_id, "extra_claims": {"role": role}},
                timeout=15,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GOClientError(f"session mint failed: {exc}") from exc
        token = str(response.json().get("access_token") or "")
        if not token:
            raise GOClientError("session mint returned no access_token")
        return token

    def _headers(self, *, approver: bool = False) -> dict[str, str]:
        if not self._session_url:
            return {}
        if approver:
            token = self._mint_token(self._approver_id, "admin")
        else:
            token = self._mint_token(self._author_id, "user")
        return {"Authorization": f"Bearer {token}"}

    def _gitlab_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._gitlab_token}"}

    def _project_url(self, space_id: str) -> str:
        encoded = quote(space_id, safe="")
        return f"{self._gitlab_url}/api/v4/projects/{encoded}"

    def _ensure_proposal_branch(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Push markdown to GitLab so GO can find ``proposal/{sha[:8]}``."""
        if not self._gitlab_url or not self._gitlab_token:
            return payload
        data = dict(payload.get("proposal_data") or {})
        path = str(data.get("path") or "")
        markdown = str(data.get("markdown") or "")
        if not path or not markdown:
            return payload
        space_id = str(payload["space_id"])
        project = self._project_url(space_id)
        target = str(payload.get("target_branch") or "main")
        try:
            head = httpx.get(
                f"{project}/repository/branches/{quote(target, safe='')}",
                headers=self._gitlab_headers(),
                timeout=30,
            )
            head.raise_for_status()
            base_sha = str(head.json()["commit"]["id"])
            run_id = str(payload.get("idempotency_key") or "ingest").replace(":", "-")[:24]
            temp_branch = f"temp-ingest-{run_id}"
            branches = f"{project}/repository/branches"
            created = httpx.post(
                branches,
                headers=self._gitlab_headers(),
                json={"branch": temp_branch, "ref": base_sha},
                timeout=30,
            )
            created.raise_for_status()
            commit = httpx.post(
                f"{project}/repository/commits",
                headers=self._gitlab_headers(),
                json={
                    "branch": temp_branch,
                    "commit_message": f"ingest source-sync {run_id}",
                    "actions": [{"action": "create", "file_path": path, "content": markdown}],
                },
                timeout=30,
            )
            if commit.status_code == 400:
                commit = httpx.post(
                    f"{project}/repository/commits",
                    headers=self._gitlab_headers(),
                    json={
                        "branch": temp_branch,
                        "commit_message": f"ingest source-sync {run_id}",
                        "actions": [
                            {"action": "update", "file_path": path, "content": markdown}
                        ],
                    },
                    timeout=30,
                )
            commit.raise_for_status()
            proposal_sha = str(commit.json()["id"])
            proposal_branch = f"proposal/{proposal_sha[:8]}"
            branched = httpx.post(
                branches,
                headers=self._gitlab_headers(),
                json={"branch": proposal_branch, "ref": proposal_sha},
                timeout=30,
            )
            if branched.status_code not in {201, 400}:
                branched.raise_for_status()
            httpx.delete(
                f"{branches}/{quote(temp_branch, safe='')}",
                headers=self._gitlab_headers(),
                timeout=30,
            )
        except httpx.HTTPError as exc:
            raise GOClientError(f"GitLab proposal branch failed: {exc}") from exc
        updated = dict(payload)
        updated["proposal_sha"] = proposal_sha
        updated["base_sha"] = base_sha
        return updated

    def _wait_mergeable(self, space_id: str, mr_iid: int, timeout: float = 90.0) -> None:
        if not self._gitlab_url or not self._gitlab_token or not mr_iid:
            return
        url = f"{self._project_url(space_id)}/merge_requests/{mr_iid}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                response = httpx.get(url, headers=self._gitlab_headers(), timeout=15)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError:
                time.sleep(0.5)
                continue
            if data.get("detailed_merge_status") == "mergeable" or data.get("merge_status") == "can_be_merged":
                return
            time.sleep(0.5)

    def submit_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        live_payload = self._ensure_proposal_branch(payload)
        url = f"{self.base_url}/api/kb/v1/proposals"
        try:
            response = self._client.post(
                url, json=live_payload, headers=self._headers(), timeout=30
            )
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
        approver = self._headers(approver=True)
        try:
            lookup = self._client.get(
                f"{self.base_url}/api/kb/v1/proposals/{proposal_id}",
                headers=approver,
                timeout=30,
            )
            if lookup.status_code == 200:
                body = lookup.json()
                space_id = str(body.get("space_id") or "")
                mr_iid = int((body.get("proposal_data") or {}).get("mr_iid") or 0)
                self._wait_mergeable(space_id, mr_iid)
            decision = self._client.post(
                decision_url,
                json={
                    "proposal_id": proposal_id,
                    "action": "accepted",
                    "actor_id": self._approver_id,
                    "idempotency_key": f"source-sync:{proposal_id}",
                    "decision_data": decision_data,
                },
                headers=approver,
                timeout=30,
            )
            decision.raise_for_status()
            merged = self._client.post(merge_url, headers=approver, timeout=90)
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
