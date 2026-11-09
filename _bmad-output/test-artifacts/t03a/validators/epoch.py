"""Epoch ordering validator: older syncs must not overwrite newer snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EpochCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class EpochValidator:
    """Validate that group/policy snapshots preserve monotonic epochs."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[EpochCheck]:
        checks: list[EpochCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            events = sorted(
                fixture.get("events", []), key=lambda e: e.get("received_at", "")
            )
            expected_final_epoch = fixture.get("expected_final_epoch")
            expected_rejected = set(fixture.get("expected_rejected_events", []))

            current_epoch: int | None = None
            current_snapshot: Any = None
            rejected: set[str] = set()

            for event in events:
                event_id = event.get("event_id", "unknown")
                epoch = event.get("epoch")
                snapshot = event.get("snapshot")

                if current_epoch is None:
                    current_epoch = epoch
                    current_snapshot = snapshot
                elif epoch >= current_epoch:
                    current_epoch = epoch
                    current_snapshot = snapshot
                else:
                    rejected.add(event_id)

            epoch_ok = current_epoch == expected_final_epoch
            rejected_ok = rejected == expected_rejected

            if epoch_ok and rejected_ok:
                checks.append(
                    EpochCheck(
                        id=f"epoch.ordering.{name}",
                        status="PASS",
                        expected=f"final epoch {expected_final_epoch}, rejected {sorted(expected_rejected)}",
                        actual=f"final epoch {current_epoch}, rejected {sorted(rejected)}",
                        details={
                            "final_epoch": current_epoch,
                            "rejected_events": sorted(rejected),
                            "snapshot_id": current_snapshot.get("snapshot_id")
                            if isinstance(current_snapshot, dict)
                            else None,
                        },
                    )
                )
            else:
                details: dict[str, Any] = {
                    "expected_final_epoch": expected_final_epoch,
                    "actual_final_epoch": current_epoch,
                    "expected_rejected": sorted(expected_rejected),
                    "actual_rejected": sorted(rejected),
                }
                if isinstance(current_snapshot, dict):
                    details["final_snapshot_id"] = current_snapshot.get("snapshot_id")
                checks.append(
                    EpochCheck(
                        id=f"epoch.ordering.{name}",
                        status="FAIL",
                        expected=f"final epoch {expected_final_epoch}, rejected {sorted(expected_rejected)}",
                        actual=f"final epoch {current_epoch}, rejected {sorted(rejected)}",
                        details=details,
                    )
                )

        return checks
