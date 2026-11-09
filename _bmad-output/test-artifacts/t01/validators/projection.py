"""Projection-mapping.md semantic checks."""

from __future__ import annotations

from pathlib import Path


class ProjectionMappingChecker:
    """Verify required enum/state rows exist in projection-mapping.md."""

    REQUIRED_ROWS = [
        "recorded",
        "merge_attempted",
        "merged",
        "failed",
        "conflicted",
        "invalid",
        "accepted",
        "rejected",
        "cancelled",
        "draft",
        "in_review",
        "published",
        "superseded",
        "requested",
        "ready",
        "active",
        "frozen",
        "preflight",
        "activated",
        "live_operational",
        "open",
        "resolved",
        "proposal_pending",
        "tombstone",
        "dead_letter",
    ]

    def __init__(self, contracts_dir: Path) -> None:
        self.path = contracts_dir / "projection-mapping.md"
        self.text = self.path.read_text(encoding="utf-8")

    def required_rows_present(self) -> list[tuple[str, bool]]:
        return [(row, row in self.text) for row in self.REQUIRED_ROWS]
