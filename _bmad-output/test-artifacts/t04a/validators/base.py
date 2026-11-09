"""Shared validator types and helpers for T04a."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidatorCheck:
    """One validator result before conversion to the report Check."""

    id: str
    status: str  # PASS / FAIL / BLOCKED
    expected: str
    actual: str
    details: dict[str, Any]


_GIT_SHA_PATTERN = r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"


def is_git_sha(value: Any) -> bool:
    """Return True if *value* looks like a full Git object ID."""
    if not isinstance(value, str):
        return False
    return len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)
