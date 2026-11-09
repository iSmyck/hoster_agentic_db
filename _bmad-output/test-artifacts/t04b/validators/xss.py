"""XSS/executable-content validator: reject dangerous HTML/MDX before exposure."""

from __future__ import annotations

import re
from typing import Any

from .base import ValidatorCheck


class XSSValidator:
    """Validate synthetic browser-gate vectors for executable content rejection."""

    DANGEROUS_RE = re.compile(
        r"<script|</script|javascript:|on\w+\s*=|<[A-Z][a-zA-Z0-9_]*[^>]*>|\{!|<!\[CDATA|<\s*(?:iframe|object|embed|form|input)\b|data:",
        re.IGNORECASE,
    )
    MDX_RE = re.compile(
        r"<[A-Z][a-zA-Z0-9_]*\b|import\s+.*\s+from\s+['\"]|export\s+default"
    )

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    @classmethod
    def gate(cls, payload: str) -> str | None:
        """Return None if safe, or a rejection reason string."""
        if cls.DANGEROUS_RE.search(payload):
            return "dangerous HTML or event handler detected"
        if cls.MDX_RE.search(payload):
            return "executable MDX/JSX detected"
        return None

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            payloads = fixture.get("payloads", [])
            for idx, entry in enumerate(payloads):
                if isinstance(entry, dict):
                    payload = entry.get("value", "")
                    expected = entry.get("expected", "reject")
                    label = entry.get("label", f"item-{idx}")
                else:
                    payload = str(entry)
                    expected = "reject"
                    label = f"item-{idx}"

                reason = self.gate(payload)
                rejected = reason is not None
                details: dict[str, Any] = {
                    "label": label,
                    "rejected": rejected,
                    "reason": reason,
                    "payload_length": len(payload),
                }

                if expected == "reject":
                    if rejected:
                        checks.append(
                            ValidatorCheck(
                                id=f"xss.{name}.{label}.rejected",
                                status="PASS",
                                expected="executable HTML/MDX/XSS payload rejected before exposure",
                                actual=f"rejected: {reason}",
                                details=details,
                            )
                        )
                    else:
                        checks.append(
                            ValidatorCheck(
                                id=f"xss.{name}.{label}.rejected",
                                status="FAIL",
                                expected="executable HTML/MDX/XSS payload rejected before exposure",
                                actual="payload allowed through gate",
                                details=details,
                            )
                        )
                elif expected == "allow":
                    if not rejected:
                        checks.append(
                            ValidatorCheck(
                                id=f"xss.{name}.{label}.allowed",
                                status="PASS",
                                expected="safe markdown allowed through gate",
                                actual="payload passed structural safety check",
                                details=details,
                            )
                        )
                    else:
                        checks.append(
                            ValidatorCheck(
                                id=f"xss.{name}.{label}.allowed",
                                status="FAIL",
                                expected="safe markdown allowed through gate",
                                actual=f"over-rejected: {reason}",
                                details=details,
                            )
                        )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"xss.{name}.{label}.unexpected_expected",
                            status="FAIL",
                            expected="expected 'reject' or 'allow'",
                            actual=f"unexpected expected {expected}",
                            details=details,
                        )
                    )

        return checks
