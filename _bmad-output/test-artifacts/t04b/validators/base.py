"""Shared validator types and helpers for T04b."""

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
