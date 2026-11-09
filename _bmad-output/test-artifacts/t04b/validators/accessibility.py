"""Accessibility validator: focus, labels and screen-reader roles exposed."""

from __future__ import annotations

import re
from typing import Any

from .base import ValidatorCheck


class AccessibilityValidator:
    """Validate synthetic editor accessibility descriptors/HTML snippets."""

    FOCUSABLE_RE = re.compile(
        r"<(?:input|textarea|button|select|a\b|[^>\s]+\s+(?:contenteditable|tabindex))",
        re.IGNORECASE,
    )
    LABEL_RE = re.compile(
        r'(?:aria-label|aria-labelledby|title|label)\s*=\s*["\'][^"\']+["\']',
        re.IGNORECASE,
    )
    ROLE_RE = re.compile(r'role\s*=\s*["\'][^"\']+["\']', re.IGNORECASE)

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            expected_status = fixture.get("expected_status", "PASS")
            html = fixture.get("html", "")
            focusable_count = len(self.FOCUSABLE_RE.findall(html))
            labelled_count = len(self.LABEL_RE.findall(html))
            role_count = len(self.ROLE_RE.findall(html))
            focusable_expected = fixture.get("focusable_count", focusable_count)
            labels_required = fixture.get("labels_required", True)
            roles_required = fixture.get("roles_required", True)

            details: dict[str, Any] = {
                "focusable_count": focusable_count,
                "labelled_count": labelled_count,
                "role_count": role_count,
                "focusable_expected": focusable_expected,
            }

            ok = focusable_count == focusable_expected
            if labels_required:
                ok = ok and labelled_count >= focusable_count
            if roles_required:
                ok = ok and role_count >= 1

            if expected_status == "PASS":
                if ok:
                    checks.append(
                        ValidatorCheck(
                            id=f"accessibility.{name}.exposed",
                            status="PASS",
                            expected="focusable elements have labels and roles exposed",
                            actual=f"{focusable_count} focusable, {labelled_count} labelled, {role_count} roles",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"accessibility.{name}.exposed",
                            status="FAIL",
                            expected="focusable elements have labels and roles exposed",
                            actual="missing labels, roles or unexpected focusable count",
                            details=details,
                        )
                    )
            elif expected_status == "FAIL":
                if not ok:
                    checks.append(
                        ValidatorCheck(
                            id=f"accessibility.{name}.gap_detected",
                            status="PASS",
                            expected="accessibility gap detected",
                            actual="focus/labels/roles insufficient",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"accessibility.{name}.gap_detected",
                            status="FAIL",
                            expected="accessibility gap detected",
                            actual="accessibility unexpectedly complete",
                            details=details,
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"accessibility.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details=details,
                    )
                )

        return checks
