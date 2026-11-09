"""Revocation epoch validator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RevocationCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class RevocationValidator:
    """Validate that stale revocation epochs are rejected."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[RevocationCheck]:
        checks: list[RevocationCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            context = fixture.get("context", {})
            policy_epoch = fixture.get("policy_epoch", 0)
            expected_stale = bool(fixture.get("expected_stale", False))

            # Per-Space revocation epoch from the context.
            space_scopes = context.get("space_scopes", [])
            stale_reasons: list[str] = []
            for scope in space_scopes:
                if scope.get("revocation_epoch", 0) < policy_epoch:
                    stale_reasons.append(
                        f"space {scope.get('space_id')} epoch {scope.get('revocation_epoch')} < policy_epoch {policy_epoch}"
                    )

            # Top-level revocation epoch also participates.
            if context.get("revocation_epoch", 0) < policy_epoch:
                stale_reasons.append(
                    f"top-level epoch {context.get('revocation_epoch')} < policy_epoch {policy_epoch}"
                )

            is_stale = bool(stale_reasons)

            if expected_stale and is_stale:
                checks.append(
                    RevocationCheck(
                        id=f"revocation.{name}.stale",
                        status="PASS",
                        expected="context with old revocation epoch is rejected/stale",
                        actual=f"stale: {stale_reasons}",
                        details={
                            "policy_epoch": policy_epoch,
                            "stale_reasons": stale_reasons,
                        },
                    )
                )
            elif expected_stale and not is_stale:
                checks.append(
                    RevocationCheck(
                        id=f"revocation.{name}.stale",
                        status="FAIL",
                        expected="context with old revocation epoch is rejected/stale",
                        actual="context epoch is not stale",
                        details={
                            "policy_epoch": policy_epoch,
                            "space_scopes": space_scopes,
                            "top_level_epoch": context.get("revocation_epoch"),
                        },
                    )
                )
            elif not expected_stale and is_stale:
                checks.append(
                    RevocationCheck(
                        id=f"revocation.{name}.stale",
                        status="FAIL",
                        expected="context epoch is fresh",
                        actual=f"unexpectedly stale: {stale_reasons}",
                        details={
                            "policy_epoch": policy_epoch,
                            "stale_reasons": stale_reasons,
                        },
                    )
                )
            else:
                checks.append(
                    RevocationCheck(
                        id=f"revocation.{name}.stale",
                        status="PASS",
                        expected="context epoch is fresh",
                        actual="context epoch is fresh",
                        details={
                            "policy_epoch": policy_epoch,
                            "top_level_epoch": context.get("revocation_epoch"),
                            "space_epochs": [
                                {
                                    "space_id": s.get("space_id"),
                                    "revocation_epoch": s.get("revocation_epoch"),
                                }
                                for s in space_scopes
                            ],
                        },
                    )
                )

        return checks
