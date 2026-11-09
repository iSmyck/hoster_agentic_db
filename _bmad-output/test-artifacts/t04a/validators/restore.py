"""Restore validator: revert-MR creation and no main history rewrite."""

from __future__ import annotations

from typing import Any

from .base import ValidatorCheck, is_git_sha


class RestoreValidator:
    """Validate restore-through-revert-MR fixtures."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            inp = fixture.get("input", {})
            state = fixture.get("state", {})
            expected = fixture.get("expected", {})
            expected_status = expected.get("status", "PASS")

            revision_sha = inp.get("revision_sha")
            available_revisions = {
                c.get("sha") for c in state.get("history", []) if isinstance(c, dict)
            }
            main_head_before = state.get("main_head_before")
            main_head_after = state.get("main_head_after", main_head_before)

            if expected_status == "PASS":
                # Exact historical revision must exist; restore creates revert-MR with new commit.
                if revision_sha in available_revisions and is_git_sha(revision_sha):
                    new_commit = expected.get("new_commit_sha")
                    created_mr = expected.get("created_revert_mr", True)
                    main_rewritten = main_head_after != main_head_before
                    if created_mr and not main_rewritten and is_git_sha(new_commit):
                        checks.append(
                            ValidatorCheck(
                                id=f"restore.{name}.revert_mr_created",
                                status="PASS",
                                expected="revert-MR created with new commit, no main rewrite",
                                actual="restore produced a new commit on revert-MR; main unchanged",
                                details={
                                    "revision_sha": revision_sha,
                                    "new_commit_sha": new_commit,
                                    "created_revert_mr": created_mr,
                                    "main_rewritten": main_rewritten,
                                },
                            )
                        )
                    else:
                        checks.append(
                            ValidatorCheck(
                                id=f"restore.{name}.revert_mr_created",
                                status="FAIL",
                                expected="revert-MR created with new commit, no main rewrite",
                                actual="restore did not satisfy revert-MR invariants",
                                details={
                                    "revision_sha": revision_sha,
                                    "new_commit_sha": new_commit,
                                    "created_revert_mr": created_mr,
                                    "main_rewritten": main_rewritten,
                                },
                            )
                        )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"restore.{name}.revert_mr_created",
                            status="FAIL",
                            expected="revert-MR created with new commit, no main rewrite",
                            actual="requested revision not in synthetic history",
                            details={
                                "revision_sha": revision_sha,
                                "available_revisions": sorted(available_revisions),
                            },
                        )
                    )
            elif expected_status == "FAIL":
                # Direct main write or invalid revision must be rejected.
                main_rewritten = main_head_after != main_head_before
                if main_rewritten or revision_sha not in available_revisions:
                    checks.append(
                        ValidatorCheck(
                            id=f"restore.{name}.no_direct_main_write",
                            status="PASS",
                            expected="direct main write or invalid revision rejected",
                            actual="restore refused; main history not rewritten",
                            details={
                                "revision_sha": revision_sha,
                                "main_rewritten": False,
                                "valid_revision": revision_sha in available_revisions,
                            },
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"restore.{name}.no_direct_main_write",
                            status="FAIL",
                            expected="direct main write or invalid revision rejected",
                            actual="restore unexpectedly succeeded",
                            details={
                                "revision_sha": revision_sha,
                                "main_rewritten": main_rewritten,
                            },
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"restore.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details={},
                    )
                )

        return checks
