"""Git Orchestrator client port, HTTP implementation, and test stub."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class GOClientError(Exception):
    """Raised when a Git Orchestrator client call fails."""


class GOClient(ABC):
    """Outbound port for canonical Git read operations."""

    @abstractmethod
    def get_tree(self, space_id: str, sha: str) -> list[dict[str, Any]]:
        """Return tree entries for ``space_id`` at exact ``sha``."""

    @abstractmethod
    def read_document(self, space_id: str, path: str, sha: str) -> str:
        """Return decoded text content of ``path`` at exact ``sha``."""

    @abstractmethod
    def get_branch_head(self, space_id: str, branch: str = "main") -> str:
        """Return the HEAD commit SHA of a branch for reconciliation."""


class HttpGOClient(GOClient):
    """Production client calling the Git Orchestrator service over HTTP."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_tree(self, space_id: str, sha: str) -> list[dict[str, Any]]:
        import httpx

        url = f"{self.base_url}/api/kb/v1/documents/tree"
        response = httpx.post(
            url,
            json={"space_id": space_id, "sha": sha},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["entries"]

    def read_document(self, space_id: str, path: str, sha: str) -> str:
        import httpx

        url = f"{self.base_url}/api/kb/v1/documents/read"
        response = httpx.post(
            url,
            json={"space_id": space_id, "path": path, "sha": sha},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["content"]

    def get_branch_head(self, space_id: str, branch: str = "main") -> str:
        import httpx

        url = f"{self.base_url}/api/kb/v1/spaces/{space_id}/branches/{branch}"
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        return response.json()["commit"]["id"]


class StubGOClient(GOClient):
    """In-memory stub for unit tests."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = state or {}

    def _get(self, key: tuple[Any, ...], default: Any) -> Any:
        return self.state.get(key, default)

    def get_tree(self, space_id: str, sha: str) -> list[dict[str, Any]]:
        return list(self._get(("tree", space_id, sha), []))

    def read_document(self, space_id: str, path: str, sha: str) -> str:
        return str(self._get(("doc", space_id, path, sha), ""))

    def get_branch_head(self, space_id: str, branch: str = "main") -> str:
        branch_data = self._get(
            ("branch", space_id, branch),
            {"commit": {"id": ""}},
        )
        return branch_data["commit"]["id"]
