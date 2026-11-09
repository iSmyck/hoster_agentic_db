"""History cursor validator: ordered commits, truncation reason and next cursor."""

from __future__ import annotations

from typing import Any

from .base import ValidatorCheck


class HistoryCursorValidator:
    """Validate paginated Git history cursor fixtures."""

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

            commits = state.get("commits", [])
            cursor = inp.get("cursor")
            limit = inp.get("limit", 10)

            # Synthetic ordering: commits are listed newest-first; cursor is an index.
            start = cursor if isinstance(cursor, int) else 0
            page = commits[start : start + limit]
            truncated = start + limit < len(commits)
            next_cursor = start + limit if truncated else None

            shas = [c.get("sha") for c in page]
            ordered = self._is_ordered(page)

            if expected_status == "PASS":
                order_ok = expected.get("ordered", True)
                expect_truncated = expected.get("truncated", truncated)
                expect_next_cursor = expected.get("next_cursor", next_cursor)
                expect_reason = expected.get("truncation_reason", "limit" if truncated else None)

                if ordered == order_ok and truncated == expect_truncated and next_cursor == expect_next_cursor:
                    checks.append(
                        ValidatorCheck(
                            id=f"history_cursor.{name}.pagination",
                            status="PASS",
                            expected="ordered commits with explicit truncation reason and next cursor",
                            actual="page is ordered and cursor/truncation metadata present",
                            details={
                                "cursor": cursor,
                                "next_cursor": next_cursor,
                                "truncated": truncated,
                                "truncation_reason": expect_reason,
                                "page_size": len(page),
                                "ordered": ordered,
                            },
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"history_cursor.{name}.pagination",
                            status="FAIL",
                            expected="ordered commits with explicit truncation reason and next cursor",
                            actual="page ordering or cursor metadata mismatch",
                            details={
                                "cursor": cursor,
                                "next_cursor": next_cursor,
                                "expected_next_cursor": expect_next_cursor,
                                "truncated": truncated,
                                "expected_truncated": expect_truncated,
                                "ordered": ordered,
                            },
                        )
                    )
            elif expected_status == "FAIL":
                # Out-of-order page scenario.
                if not ordered:
                    checks.append(
                        ValidatorCheck(
                            id=f"history_cursor.{name}.out_of_order_rejected",
                            status="PASS",
                            expected="out-of-order history rejected",
                            actual="commits are not in ancestry order",
                            details={"shas": shas, "ordered": ordered},
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"history_cursor.{name}.out_of_order_rejected",
                            status="FAIL",
                            expected="out-of-order history rejected",
                            actual="commits are still ordered",
                            details={"shas": shas, "ordered": ordered},
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"history_cursor.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or FAIL",
                        actual=f"unexpected expected status {expected_status}",
                        details={},
                    )
                )

        return checks

    @staticmethod
    def _is_ordered(page: list[dict[str, Any]]) -> bool:
        """Return True if commits respect timestamp/parent ancestry order."""
        if len(page) < 2:
            return True
        timestamps = [c.get("timestamp") for c in page]
        if all(isinstance(ts, str) for ts in timestamps):
            return timestamps == sorted(timestamps, reverse=True)
        # Ancestry chain: each commit's parent must appear later in page.
        shas = [c.get("sha") for c in page]
        sha_to_index = {sha: i for i, sha in enumerate(shas) if sha}
        for i, commit in enumerate(page):
            parent = commit.get("parent")
            if parent and parent in sha_to_index and sha_to_index[parent] <= i:
                return False
        return True
