"""Policy path normalization validator."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass
class PathCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


def _canonical_policy_path(path: str) -> str | None:
    """Return canonical NFC absolute repository path or None if invalid."""
    path = unicodedata.normalize("NFC", path)
    if path == "/":
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    if path.endswith("/"):
        return None
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts[1:]):
        return None
    if "\\" in path:
        return None
    return path


def _to_relative(path: str) -> str | None:
    """Losslessly remove leading slash; root maps to empty prefix."""
    canonical = _canonical_policy_path(path)
    if canonical is None:
        return None
    if canonical == "/":
        return ""
    return canonical[1:]


class PathValidator:
    """Validate absolute/relative path round-trip and reject ambiguous variants."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[PathCheck]:
        checks: list[PathCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            absolute = fixture.get("absolute", "")
            relative = fixture.get("relative", "")
            expected_valid = bool(fixture.get("expected_valid", True))

            canonical = _canonical_policy_path(absolute)
            derived_relative = _to_relative(absolute)

            if expected_valid:
                if canonical is None:
                    checks.append(
                        PathCheck(
                            id=f"path.{name}.canonical",
                            status="FAIL",
                            expected=f"{absolute} normalizes to a canonical absolute path",
                            actual="normalization rejected the path",
                            details={"absolute": absolute, "relative": relative},
                        )
                    )
                elif derived_relative != relative:
                    checks.append(
                        PathCheck(
                            id=f"path.{name}.canonical",
                            status="FAIL",
                            expected=f"absolute {absolute} maps to relative {relative}",
                            actual=f"derived relative {derived_relative}",
                            details={
                                "absolute": absolute,
                                "expected_relative": relative,
                                "derived_relative": derived_relative,
                            },
                        )
                    )
                else:
                    checks.append(
                        PathCheck(
                            id=f"path.{name}.canonical",
                            status="PASS",
                            expected=f"absolute {absolute} maps losslessly to relative {relative}",
                            actual=f"canonical {canonical}, relative {derived_relative}",
                            details={
                                "absolute": absolute,
                                "canonical": canonical,
                                "relative": derived_relative,
                            },
                        )
                    )

                # Round-trip: adding leading slash to relative restores canonical.
                round_trip = "/" + relative if relative != "" else "/"
                if round_trip == canonical:
                    checks.append(
                        PathCheck(
                            id=f"path.{name}.round_trip",
                            status="PASS",
                            expected="relative -> absolute round-trip is lossless",
                            actual=f"/{relative if relative else ''} == {canonical}",
                            details={"round_trip": round_trip, "canonical": canonical},
                        )
                    )
                else:
                    checks.append(
                        PathCheck(
                            id=f"path.{name}.round_trip",
                            status="FAIL",
                            expected="relative -> absolute round-trip is lossless",
                            actual=f"round_trip {round_trip} != canonical {canonical}",
                            details={"round_trip": round_trip, "canonical": canonical},
                        )
                    )
            else:
                if canonical is None:
                    checks.append(
                        PathCheck(
                            id=f"path.{name}.rejected",
                            status="PASS",
                            expected=f"{absolute} is rejected as ambiguous/invalid",
                            actual="normalization rejected the path",
                            details={"absolute": absolute},
                        )
                    )
                else:
                    checks.append(
                        PathCheck(
                            id=f"path.{name}.rejected",
                            status="FAIL",
                            expected=f"{absolute} is rejected as ambiguous/invalid",
                            actual=f"normalized to {canonical}",
                            details={"absolute": absolute, "canonical": canonical},
                        )
                    )

        return checks
