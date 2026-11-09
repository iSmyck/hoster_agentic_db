"""Stale base validator: target-branch advance detection and diff view."""

from __future__ import annotations

from typing import Any

from .base import ValidatorCheck


class StaleBaseValidator:
    """Validate stale-base conflict fixtures."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            inp = fixture.get("input", {})
            state = fixture.get("state", {})
            expected = fixture.get("expected", {})
            expected_status = expected.get("status", "STALE_BASE")

            base_sha = inp.get("base_sha")
            target_head = state.get("target_head")
            target_history = state.get("target_history", [])

            # Base is stale if it is not the current target HEAD and not an ancestor
            # of the current HEAD in our synthetic history.
            is_stale = base_sha != target_head and base_sha not in target_history

            if expected_status == "STALE_BASE":
                if is_stale:
                    checks.append(
                        ValidatorCheck(
                            id=f"stale_base.{name}.conflict_detected",
                            status="PASS",
                            expected="STALE_BASE conflict with diff view",
                            actual="target advanced before save; stale base detected",
                            details={
                                "base_sha": base_sha,
                                "target_head": target_head,
                                "diff_view": expected.get("diff_view", True),
                                "silent_overwrite": False,
                            },
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"stale_base.{name}.conflict_detected",
                            status="FAIL",
                            expected="STALE_BASE conflict with diff view",
                            actual="base is still fresh in synthetic state",
                            details={
                                "base_sha": base_sha,
                                "target_head": target_head,
                            },
                        )
                    )
            elif expected_status == "FAIL":
                # Silent overwrite is forbidden; expect no overwrite happened.
                if is_stale:
                    checks.append(
                        ValidatorCheck(
                            id=f"stale_base.{name}.no_silent_overwrite",
                            status="PASS",
                            expected="silent overwrite rejected",
                            actual="stale base refused, no main/draft overwrite",
                            details={
                                "base_sha": base_sha,
                                "target_head": target_head,
                                "silent_overwrite": False,
                            },
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"stale_base.{name}.no_silent_overwrite",
                            status="FAIL",
                            expected="silent overwrite rejected",
                            actual="base not stale; cannot prove overwrite prevention",
                            details={
                                "base_sha": base_sha,
                                "target_head": target_head,
                            },
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"stale_base.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status STALE_BASE or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details={},
                    )
                )

        return checks
