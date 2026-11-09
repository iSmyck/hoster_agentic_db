"""Identity + AuthZ client port, HTTP implementation, and test stub."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any


class IdentityClientError(Exception):
    """Raised when an identity client call fails."""


class IdentityClient(ABC):
    """Outbound port for Identity/AuthZ authorization checks."""

    @abstractmethod
    def check_path(
        self,
        space_id: str,
        actor_id: uuid.UUID,
        path: str,
    ) -> dict[str, Any]:
        """Return the identity service path-check response for ``path``."""


class HttpIdentityClient(IdentityClient):
    """Production client calling the Identity service over HTTP."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def check_path(
        self,
        space_id: str,
        actor_id: uuid.UUID,
        path: str,
    ) -> dict[str, Any]:
        import httpx

        url = f"{self.base_url}/api/kb/v1/authz/check"
        response = httpx.post(
            url,
            json={"space_id": space_id, "actor_id": str(actor_id), "path": path},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


class StubIdentityClient(IdentityClient):
    """In-memory stub for unit tests.

    ``state[("check", space_id, actor_id, path)]`` may be set to a dict that
    will be returned directly, or to a boolean that is wrapped as ``approved``.
    If no entry is present, the path is approved when it starts with an
    allowed prefix configured in ``allowed_prefixes``.
    """

    def __init__(
        self,
        state: dict[str, Any] | None = None,
        allowed_prefixes: list[str] | None = None,
    ) -> None:
        self.state = state or {}
        self.allowed_prefixes = allowed_prefixes or ["/docs"]

    def check_path(
        self,
        space_id: str,
        actor_id: uuid.UUID,
        path: str,
    ) -> dict[str, Any]:
        key = ("check", space_id, str(actor_id), path)
        if key in self.state:
            result = self.state[key]
            if isinstance(result, dict):
                return dict(result)
            return {
                "approved": bool(result),
                "space_id": space_id,
                "actor_id": str(actor_id),
                "path": path,
                "matched_prefix": None,
                "reason": "stub",
            }

        approved = any(path.startswith(p) for p in self.allowed_prefixes)
        return {
            "approved": approved,
            "space_id": space_id,
            "actor_id": str(actor_id),
            "path": path,
            "matched_prefix": self.allowed_prefixes[0] if approved else None,
            "reason": "stub-prefix-match",
        }
