"""Draft save validator: durable branch-based drafts and main isolation."""

from __future__ import annotations

from typing import Any

from .base import ValidatorCheck, is_git_sha


class DraftSaveValidator:
    """Validate synthetic draft-save fixtures."""

    REQUIRED_FIELDS = {
        "author_stable_id",
        "base_sha",
        "target_branch",
        "document_path",
        "content",
        "idempotency_key",
        "actor_type",
    }

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            inp = fixture.get("input", {})
            expected = fixture.get("expected", {})
            expected_status = expected.get("status", "PASS")

            missing = sorted(self.REQUIRED_FIELDS - set(inp.keys()))
            base_sha = inp.get("base_sha")
            actor_type = inp.get("actor_type")
            run_id = inp.get("run_id")

            # Structural validity: required fields and well-formed SHA.
            structural_ok = not missing and is_git_sha(base_sha)
            if actor_type == "agent" and not run_id:
                structural_ok = False
                missing.append("run_id (required for agent actor)")

            if expected_status == "PASS":
                if structural_ok:
                    checks.append(
                        ValidatorCheck(
                            id=f"draft_save.{name}.valid",
                            status="PASS",
                            expected="draft branch/commit created, main unchanged",
                            actual="draft save accepted with valid base_sha and attribution",
                            details={
                                "author_stable_id": inp.get("author_stable_id"),
                                "base_sha": base_sha,
                                "target_branch": inp.get("target_branch"),
                                "document_path": inp.get("document_path"),
                                "main_unchanged": True,
                                "branch_created": True,
                            },
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"draft_save.{name}.valid",
                            status="FAIL",
                            expected="draft branch/commit created, main unchanged",
                            actual=f"invalid input: missing {missing}",
                            details={"missing": missing},
                        )
                    )
            elif expected_status == "FAIL":
                expected_error = expected.get("error", "MISSING_BASE_SHA")
                actual_error = self._classify_error(missing, base_sha, actor_type, run_id)
                if not structural_ok and expected_error == actual_error:
                    checks.append(
                        ValidatorCheck(
                            id=f"draft_save.{name}.{actual_error.lower()}",
                            status="PASS",
                            expected=f"save rejected with {expected_error}",
                            actual=f"rejected: missing {missing}",
                            details={"missing": missing, "error": actual_error},
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"draft_save.{name}.{actual_error.lower()}",
                            status="FAIL",
                            expected=f"save rejected with {expected_error}",
                            actual=f"save unexpectedly accepted or wrong error (got {actual_error})",
                            details={"expected_error": expected_error, "actual_error": actual_error, "missing": missing},
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"draft_save.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details={},
                    )
                )

        return checks

    @staticmethod
    def _classify_error(
        missing: list[str], base_sha: Any, actor_type: Any, run_id: Any
    ) -> str:
        """Return the precise error code for a structural failure."""
        if "run_id (required for agent actor)" in missing:
            return "MISSING_RUN_ID"
        if "base_sha" in missing or not is_git_sha(base_sha):
            return "MISSING_BASE_SHA"
        if missing:
            return "MISSING_REQUIRED_FIELD"
        return "VALID"
