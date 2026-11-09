"""Front-matter boundary validator: delimiter closed and intact through round-trip."""

from __future__ import annotations

from typing import Any

from .round_trip import RoundTripValidator
from .base import ValidatorCheck


class FrontMatterBoundaryValidator:
    """Validate that front-matter boundary is preserved and not merged into body."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            expected_status = fixture.get("expected_status", "PASS")
            markdown = fixture.get("markdown", "")
            details: dict[str, Any] = {"fixture": name}

            try:
                fm, body = RoundTripValidator._parse(markdown)
                serialized = RoundTripValidator._serialize(fm, body)
                boundary_closed = (
                    serialized.startswith("---\n") and "\n---\n" in serialized
                )
                body_unpolluted = all(f"{key}:" not in body for key in fm.keys())
                details.update(
                    {
                        "boundary_closed": boundary_closed,
                        "body_unpolluted": body_unpolluted,
                        "front_matter_keys": sorted(fm.keys()),
                    }
                )
            except Exception as exc:
                details["error"] = str(exc)
                boundary_closed = False
                body_unpolluted = False

            ok = boundary_closed and body_unpolluted

            if expected_status == "PASS":
                if ok:
                    checks.append(
                        ValidatorCheck(
                            id=f"front_matter_boundary.{name}.closed",
                            status="PASS",
                            expected="front-matter boundary remains closed and intact",
                            actual="front matter is closed; body does not contain front-matter keys",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"front_matter_boundary.{name}.closed",
                            status="FAIL",
                            expected="front-matter boundary remains closed and intact",
                            actual="front-matter boundary lost or body polluted",
                            details=details,
                        )
                    )
            elif expected_status == "FAIL":
                if not ok:
                    checks.append(
                        ValidatorCheck(
                            id=f"front_matter_boundary.{name}.boundary_lost_detected",
                            status="PASS",
                            expected="boundary loss detected",
                            actual="front-matter boundary is not closed",
                            details=details,
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"front_matter_boundary.{name}.boundary_lost_detected",
                            status="FAIL",
                            expected="boundary loss detected",
                            actual="front-matter boundary unexpectedly intact",
                            details=details,
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"front_matter_boundary.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details=details,
                    )
                )

        return checks
