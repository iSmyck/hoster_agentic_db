"""Rename survival validator: same stable_id, changed email/login must keep identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .identity import _identity_key


@dataclass
class RenameCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class RenameValidator:
    """Validate that renaming email/login preserves stable identity."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[RenameCheck]:
        checks: list[RenameCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            before = fixture.get("before", {})
            after = fixture.get("after", {})
            expected_stable = bool(fixture.get("expected_stable", True))

            before_type, before_key = _identity_key(before)
            after_type, after_key = _identity_key(after)

            if before_key is None:
                checks.append(
                    RenameCheck(
                        id=f"rename.{name}.before_key",
                        status="FAIL",
                        expected="before payload has stable identity key",
                        actual=f"before payload lacks stable key ({before_type})",
                        details={"before": before},
                    )
                )
                continue
            if after_key is None:
                checks.append(
                    RenameCheck(
                        id=f"rename.{name}.after_key",
                        status="FAIL",
                        expected="after payload has stable identity key",
                        actual=f"after payload lacks stable key ({after_type})",
                        details={"after": after},
                    )
                )
                continue

            stable = before_key == after_key

            if expected_stable and stable:
                checks.append(
                    RenameCheck(
                        id=f"rename.{name}.stable",
                        status="PASS",
                        expected="identity stable across email/login rename",
                        actual=f"stable key preserved {before_key}; email {before.get('email')} -> {after.get('email')}",
                        details={
                            "stable_key": before_key,
                            "email_before": before.get("email"),
                            "email_after": after.get("email"),
                            "login_before": before.get("login"),
                            "login_after": after.get("login"),
                        },
                    )
                )
            elif expected_stable and not stable:
                checks.append(
                    RenameCheck(
                        id=f"rename.{name}.stable",
                        status="FAIL",
                        expected="identity stable across email/login rename",
                        actual=f"stable key changed from {before_key} to {after_key}",
                        details={
                            "before_key": before_key,
                            "after_key": after_key,
                        },
                    )
                )
            elif not expected_stable and stable:
                checks.append(
                    RenameCheck(
                        id=f"rename.{name}.stable",
                        status="FAIL",
                        expected="identity should not be stable (new identity expected)",
                        actual=f"stable key unexpectedly preserved {before_key}",
                        details={
                            "stable_key": before_key,
                            "email_before": before.get("email"),
                            "email_after": after.get("email"),
                        },
                    )
                )
            else:
                checks.append(
                    RenameCheck(
                        id=f"rename.{name}.stable",
                        status="PASS",
                        expected="identity should not be stable (new identity expected)",
                        actual=f"stable key changed from {before_key} to {after_key}",
                        details={
                            "before_key": before_key,
                            "after_key": after_key,
                        },
                    )
                )
        return checks
