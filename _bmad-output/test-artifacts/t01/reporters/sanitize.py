"""Redact secrets / tokens / emails / local endpoints from evidence copies."""

from __future__ import annotations

import copy
import re
from typing import Any


_SECRET_PATTERNS = [
    (re.compile(r"(token|password|secret|private_key)\s*[=:]\s*[^\s\"']+", re.IGNORECASE), r"\1=<redacted>"),
    (re.compile(r"bearer\s+[a-z0-9_\-]+", re.IGNORECASE), "Bearer <redacted>"),
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "<email-redacted>"),
    (re.compile(r"localhost:\d+"), "<local-endpoint-redacted>"),
    (re.compile(r"127\.0\.0\.1:\d+"), "<local-endpoint-redacted>"),
]


def sanitize_string(value: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, dict):
        return {k: sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value(v) for v in value]
    return value


def sanitize_for_evidence(report: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of *report* with secrets and local endpoints redacted."""
    sanitized = copy.deepcopy(report)
    sanitized["secrets_included"] = False
    sanitized["environment"] = {
        k: sanitize_value(v) for k, v in sanitized.get("environment", {}).items()
    }
    sanitized["checks"] = [sanitize_value(c) for c in sanitized.get("checks", [])]
    return sanitized
