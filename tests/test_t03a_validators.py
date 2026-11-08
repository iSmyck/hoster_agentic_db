"""Unit tests for T03a group snapshot validator."""

from __future__ import annotations

from typing import Any


def test_group_nested_resolution(t03a_modules: Any) -> None:
    fixture = {
        "name": "nested",
        "groups": [
            {
                "group_id": "g1",
                "members": [
                    {"id": "u1", "type": "user"},
                    {"id": "g2", "type": "group"},
                ],
            },
            {
                "group_id": "g2",
                "members": [{"id": "u2", "type": "user"}],
            },
        ],
        "expected": {
            "snapshots": {
                "g1": [
                    {
                        "group_id": "g1",
                        "member_id": "u1",
                        "membership_source": "direct",
                    },
                    {
                        "group_id": "g1",
                        "member_id": "u2",
                        "membership_source": "nested",
                    },
                ],
                "g2": [
                    {
                        "group_id": "g2",
                        "member_id": "u2",
                        "membership_source": "direct",
                    },
                ],
            }
        },
    }
    checks = t03a_modules.groups.GroupSnapshotValidator([fixture]).validate()

    assert any(
        c.id == "groups.snapshot.nested.g1" and c.status == "PASS" for c in checks
    )
    assert any(
        c.id == "groups.snapshot.nested.g2" and c.status == "PASS" for c in checks
    )


def test_group_cycle_detection(t03a_modules: Any) -> None:
    fixture = {
        "name": "cycle",
        "groups": [
            {
                "group_id": "a",
                "members": [{"id": "b", "type": "group"}],
            },
            {
                "group_id": "b",
                "members": [{"id": "a", "type": "group"}],
            },
        ],
        "expected": {"cycles": [["a", "b", "a"]]},
    }
    checks = t03a_modules.groups.GroupSnapshotValidator([fixture]).validate()

    cycle_check = next(c for c in checks if c.id == "groups.cycle.cycle")
    assert cycle_check.status == "PASS"


def test_group_missing_group(t03a_modules: Any) -> None:
    fixture = {
        "name": "missing",
        "groups": [
            {"group_id": "present", "members": []},
        ],
        "expected_missing_groups": ["ghost"],
    }
    checks = t03a_modules.groups.GroupSnapshotValidator([fixture]).validate()

    missing_check = next(c for c in checks if c.id == "groups.missing.missing.ghost")
    assert missing_check.status == "PASS"
