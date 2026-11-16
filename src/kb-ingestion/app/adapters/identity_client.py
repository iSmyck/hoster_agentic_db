"""Identity + AuthZ client port for kb-ingestion (KBI-903)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from fastapi import HTTPException, Request, status


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
        try:
            response = httpx.post(
                url,
                json={"space_id": space_id, "actor_id": str(actor_id), "path": path},
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IdentityClientError(f"identity check failed: {exc}") from exc
        return response.json()


class StubIdentityClient(IdentityClient):
    """In-memory stub. Default prefixes ``/`` so unset tests stay allow-all."""

    def __init__(
        self,
        state: dict[str, Any] | None = None,
        allowed_prefixes: list[str] | None = None,
    ) -> None:
        self.state = state or {}
        self.allowed_prefixes = allowed_prefixes or ["/"]

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

        approved = any(path.startswith(prefix) for prefix in self.allowed_prefixes)
        return {
            "approved": approved,
            "space_id": space_id,
            "actor_id": str(actor_id),
            "path": path,
            "matched_prefix": self.allowed_prefixes[0] if approved else None,
            "reason": "stub-prefix-match",
        }


def enforce_identity(
    request: Request,
    *,
    space_id: str,
    path: str,
    actor_id: str | None,
) -> None:
    """No-op unless ``INGEST_REQUIRE_IDENTITY`` is enabled."""
    from ..core.config import settings

    if not settings.INGEST_REQUIRE_IDENTITY:
        return
    identity = getattr(request.app.state, "identity_client", None)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "IDENTITY_UNAVAILABLE", "message": "identity client is not configured"},
        )
    if not actor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "IDENTITY_REQUIRED", "message": "X-Actor-Id is required"},
        )
    try:
        actor = uuid.UUID(actor_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ACTOR_ID", "message": "X-Actor-Id must be a UUID"},
        ) from exc
    try:
        result = identity.check_path(space_id, actor, path)
    except IdentityClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "IDENTITY_UNAVAILABLE", "message": str(exc)},
        ) from exc
    if not result.get("approved"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "IDENTITY_DENIED", "message": "actor is not allowed for this path"},
        )
