"""Error envelope shape validator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ErrorShapeCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class ErrorShapeValidator:
    """Validate that denied requests return {code, message, request_id, retryable}."""

    REQUIRED_FIELDS = {"code", "message", "request_id", "retryable"}

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ErrorShapeCheck]:
        checks: list[ErrorShapeCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            error = fixture.get("error", {})
            expected_valid = bool(fixture.get("expected_valid", True))

            present = set(error.keys())
            missing = self.REQUIRED_FIELDS - present
            extra = present - self.REQUIRED_FIELDS

            # Details must be sanitized (no credentials/endpoints).
            details = error.get("details", {})
            has_sensitive = self._has_sensitive_pattern(str(details))

            is_valid = not missing and not has_sensitive

            if expected_valid and is_valid:
                checks.append(
                    ErrorShapeCheck(
                        id=f"error_shape.{name}.envelope",
                        status="PASS",
                        expected="error uses {code, message, request_id, retryable} with sanitized details",
                        actual="envelope valid and details sanitized",
                        details={
                            "fields": sorted(present),
                            "extra": sorted(extra),
                        },
                    )
                )
            elif expected_valid and not is_valid:
                checks.append(
                    ErrorShapeCheck(
                        id=f"error_shape.{name}.envelope",
                        status="FAIL",
                        expected="error uses {code, message, request_id, retryable} with sanitized details",
                        actual=f"missing={sorted(missing)}, has_sensitive_detail={has_sensitive}",
                        details={
                            "missing": sorted(missing),
                            "has_sensitive_detail": has_sensitive,
                        },
                    )
                )
            elif not expected_valid and not is_valid:
                checks.append(
                    ErrorShapeCheck(
                        id=f"error_shape.{name}.envelope",
                        status="PASS",
                        expected="error envelope is correctly rejected as malformed",
                        actual=f"missing={sorted(missing)}, has_sensitive_detail={has_sensitive}",
                        details={
                            "missing": sorted(missing),
                            "has_sensitive_detail": has_sensitive,
                        },
                    )
                )
            else:
                checks.append(
                    ErrorShapeCheck(
                        id=f"error_shape.{name}.envelope",
                        status="FAIL",
                        expected="error envelope is correctly rejected as malformed",
                        actual="envelope unexpectedly valid",
                        details={"fields": sorted(present)},
                    )
                )

        return checks

    @staticmethod
    def _has_sensitive_pattern(value: str) -> bool:
        lowered = value.lower()
        for token in (
            "token",
            "password",
            "secret",
            "bearer",
            "credential",
            "private",
            "localhost:",
            "127.0.0.1:",
        ):
            if token in lowered:
                return True
        return False
