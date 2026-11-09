"""Group snapshot validator: nested closure, cycles, empty groups, ordering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GroupCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class GroupSnapshotValidator:
    """Validate nested group membership snapshots against the groupSnapshot contract."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    @staticmethod
    def _build_index(groups: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {g["group_id"]: g for g in groups}

    @staticmethod
    def _resolve_group(
        group_id: str,
        context_id: str,
        index: dict[str, dict[str, Any]],
        path: list[str],
        visited: set[str],
    ) -> tuple[list[dict[str, Any]], list[str] | None]:
        """Return membership entries for *context_id* by resolving *group_id*.

        Direct members of *group_id* are recorded as "direct" only when
        *group_id* equals *context_id*; inherited members are "nested".
        """
        if group_id in visited:
            cycle_start = path.index(group_id)
            return [], path[cycle_start:] + [group_id]
        group = index.get(group_id)
        if group is None:
            return [], None
        visited.add(group_id)
        results: list[dict[str, Any]] = []
        is_direct_context = group_id == context_id
        for member in group.get("members", []):
            member_id = member["id"]
            member_type = member.get("type", "user")
            if member_type == "user":
                results.append(
                    {
                        "group_id": context_id,
                        "member_id": member_id,
                        "membership_source": "direct"
                        if is_direct_context
                        else "nested",
                    }
                )
            elif member_type == "group":
                nested, cycle = GroupSnapshotValidator._resolve_group(
                    member_id, context_id, index, path + [group_id], visited.copy()
                )
                if cycle:
                    return [], cycle
                results.extend(nested)
        return results, None

    @staticmethod
    def _normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
        """Return a canonical representation for an undirected cycle path.

        Removes the repeated last node and treats reverse cycles as identical.
        """
        if len(cycle) >= 2 and cycle[0] == cycle[-1]:
            nodes = cycle[:-1]
        else:
            nodes = list(cycle)
        if not nodes:
            return tuple(cycle)
        rotations = [nodes[i:] + nodes[:i] for i in range(len(nodes))]
        forward = min(rotations)
        reverse_nodes = list(reversed(nodes))
        reverse_rotations = [reverse_nodes[i:] + reverse_nodes[:i] for i in range(len(reverse_nodes))]
        reverse = min(reverse_rotations)
        return tuple(min(forward, reverse))

    def _snapshot(
        self, groups: list[dict[str, Any]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[list[str]]]:
        """Build a per-group membership snapshot with transitive closure."""
        index = self._build_index(groups)
        snapshots: dict[str, list[dict[str, Any]]] = {}
        seen_cycles: set[tuple[str, ...]] = set()
        cycles: list[list[str]] = []
        for group in groups:
            gid = group["group_id"]
            members, cycle = self._resolve_group(gid, gid, index, [], set())
            if cycle:
                normalized = self._normalize_cycle(cycle)
                if normalized not in seen_cycles:
                    seen_cycles.add(normalized)
                    cycles.append(cycle)
            snapshots[gid] = members
        return snapshots, cycles

    def validate(self) -> list[GroupCheck]:
        checks: list[GroupCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            groups = fixture.get("groups", [])
            expected = fixture.get("expected", {})
            expected_cycles = expected.get("cycles", [])
            expected_snapshots = expected.get("snapshots", {})

            snapshots, cycles = self._snapshot(groups)

            # Cycle detection: compare canonical cycle sets.
            normalized_actual = sorted({self._normalize_cycle(c) for c in cycles})
            normalized_expected = sorted({self._normalize_cycle(c) for c in expected_cycles})
            if normalized_actual == normalized_expected:
                checks.append(
                    GroupCheck(
                        id=f"groups.cycle.{name}",
                        status="PASS",
                        expected=f"cycle(s) detected: {normalized_expected}",
                        actual=f"cycle(s) detected: {normalized_actual}",
                        details={"cycles": cycles},
                    )
                )
            else:
                checks.append(
                    GroupCheck(
                        id=f"groups.cycle.{name}",
                        status="FAIL",
                        expected=f"cycle(s) detected: {normalized_expected}",
                        actual=f"cycle(s) detected: {normalized_actual}",
                        details={
                            "expected_cycles": expected_cycles,
                            "actual_cycles": cycles,
                        },
                    )
                )

            # Snapshot correctness: transitive closure and empty groups explicit.
            for gid, expected_members in expected_snapshots.items():
                actual_members = snapshots.get(gid, [])
                # Compare full member entries preserving order.
                if actual_members == expected_members:
                    checks.append(
                        GroupCheck(
                            id=f"groups.snapshot.{name}.{gid}",
                            status="PASS",
                            expected=f"group {gid} resolves to expected members",
                            actual=f"resolved to {len(actual_members)} members",
                            details={
                                "group_id": gid,
                                "members": actual_members,
                            },
                        )
                    )
                else:
                    checks.append(
                        GroupCheck(
                            id=f"groups.snapshot.{name}.{gid}",
                            status="FAIL",
                            expected=f"group {gid} resolves to expected members",
                            actual=f"resolved to {len(actual_members)} members",
                            details={
                                "group_id": gid,
                                "expected": expected_members,
                                "actual": actual_members,
                            },
                        )
                    )

            # Missing group check.
            missing_groups = fixture.get("expected_missing_groups", [])
            index = self._build_index(groups)
            for gid in missing_groups:
                if gid in index:
                    checks.append(
                        GroupCheck(
                            id=f"groups.missing.{name}.{gid}",
                            status="FAIL",
                            expected=f"group {gid} is missing",
                            actual=f"group {gid} is present",
                            details={"group_id": gid},
                        )
                    )
                else:
                    checks.append(
                        GroupCheck(
                            id=f"groups.missing.{name}.{gid}",
                            status="PASS",
                            expected=f"group {gid} is missing",
                            actual=f"group {gid} is missing",
                            details={"group_id": gid},
                        )
                    )

        return checks
