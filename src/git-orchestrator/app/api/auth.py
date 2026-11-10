"""Session identity and authorization helpers for browser-facing GO routes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

import httpx
from fastapi import HTTPException, Request, status

from ..core.config import settings


@dataclass(frozen=True)
class AuthenticatedIdentity:
    stable_id: str
    role: str


def _extract_bearer(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Bearer session token required"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Bearer session token required"},
        )
    return token


def get_current_identity(request: Request) -> AuthenticatedIdentity:
    """Resolve the caller identity from a Session service access token."""
    token = _extract_bearer(request)
    try:
        response = httpx.get(
            f"{settings.SESSION_SERVICE_URL}/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SESSION_UNAVAILABLE", "message": "session service unavailable"},
        ) from exc
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SESSION", "message": "session token rejected"},
        )
    data = response.json()
    stable_id = str(data.get("stable_id") or "").strip()
    if not stable_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SESSION", "message": "session identity missing"},
        )
    return AuthenticatedIdentity(stable_id=stable_id, role="user")


def require_approver(identity: AuthenticatedIdentity) -> None:
    allowed = {item.strip() for item in settings.KB_APPROVER_IDS.split(",") if item.strip()}
    if identity.role != "admin" and identity.stable_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "APPROVER_REQUIRED",
                "message": "independent approver capability required",
            },
        )


def require_space_access(identity: AuthenticatedIdentity, space_id: str) -> None:
    allowed = {item.strip() for item in settings.KB_ALLOWED_SPACE_IDS.split(",") if item.strip()}
    if space_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "space not found"},
        )


def validate_target_branch(branch: str) -> None:
    allowed = {item.strip() for item in settings.KB_TARGET_BRANCHES.split(",") if item.strip()}
    if branch not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "TARGET_BRANCH_FORBIDDEN", "message": "target branch is not allowed"},
        )


def validate_markdown_path(path: str) -> None:
    """Allow only regular Markdown pages below approved KB roots."""
    if not path or "\\" in path or any(ord(char) < 32 for char in path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": "invalid KB page path"},
        )
    candidate = PurePosixPath(path)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or any(part.startswith(".") for part in candidate.parts)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": "invalid KB page path"},
        )
    if candidate.suffix.lower() not in {".md", ".markdown"} or candidate.parts[0] not in {
        "docs",
        "runbooks",
        "shared",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PATH_FORBIDDEN",
                "message": "only Markdown pages below approved KB roots are allowed",
            },
        )
