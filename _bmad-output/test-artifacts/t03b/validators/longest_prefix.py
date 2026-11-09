"""Longest-normalized-prefix rule selection validator."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass
class LongestPrefixCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


def _canonical_prefix(prefix: str) -> str | None:
    """Return NFC-normalized prefix or None if invalid/ambiguous."""
    prefix = unicodedata.normalize("NFC", prefix)
    if prefix == "/":
        return "/"
    if prefix.startswith("/"):
        prefix = prefix.rstrip("/")
    if not prefix:
        return None
    parts = prefix.split("/")
    if any(p in ("", ".", "..") for p in parts[1:]):
        return None
    if "\\" in prefix:
        return None
    return prefix


def _matches(prefix: str, path: str) -> bool:
    """Return True if *prefix* selects *path* by longest-normalized-prefix rule."""
    canonical_prefix = _canonical_prefix(prefix)
    canonical_path = _canonical_prefix(path)
    if canonical_prefix is None or canonical_path is None:
        return False
    if canonical_prefix == "/":
        return True
    if canonical_path == canonical_prefix:
        return True
    if canonical_path.startswith(canonical_prefix + "/"):
        return True
    return False


def _select_rule(rules: list[dict[str, Any]], path: str) -> dict[str, Any] | None:
    """Select the rule with the longest matching normalized prefix."""
    candidates = [
        (rule, _canonical_prefix(rule["path_prefix"]))
        for rule in rules
        if _matches(rule["path_prefix"], path)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: len(item[1] or ""), reverse=True)
    return candidates[0][0]


class LongestPrefixValidator:
    """Validate longest-normalized-prefix selection and no parent-prefix union."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[LongestPrefixCheck]:
        checks: list[LongestPrefixCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            path = fixture.get("path", "")
            rules = fixture.get("rules", [])
            expected_rule_id = fixture.get("expected_rule_id")
            expect_no_match = bool(fixture.get("expect_no_match", False))

            selected = _select_rule(rules, path)

            if expect_no_match:
                if selected is None:
                    checks.append(
                        LongestPrefixCheck(
                            id=f"longest_prefix.{name}.no_match",
                            status="PASS",
                            expected="no rule matches the path",
                            actual="no rule matched",
                            details={"path": path, "rules": rules},
                        )
                    )
                else:
                    checks.append(
                        LongestPrefixCheck(
                            id=f"longest_prefix.{name}.no_match",
                            status="FAIL",
                            expected="no rule matches the path",
                            actual=f"rule {selected.get('rule_id')} matched",
                            details={"path": path, "selected": selected},
                        )
                    )
                continue

            if selected is None:
                checks.append(
                    LongestPrefixCheck(
                        id=f"longest_prefix.{name}.selection",
                        status="FAIL",
                        expected=f"rule {expected_rule_id} is selected",
                        actual="no rule matched",
                        details={"path": path, "rules": rules},
                    )
                )
                continue

            selected_id = selected.get("rule_id")
            if selected_id == expected_rule_id:
                checks.append(
                    LongestPrefixCheck(
                        id=f"longest_prefix.{name}.selection",
                        status="PASS",
                        expected=f"rule {expected_rule_id} is selected",
                        actual=f"rule {selected_id} selected",
                        details={
                            "path": path,
                            "selected_rule_id": selected_id,
                            "selected_groups": selected.get("external_group_ids"),
                        },
                    )
                )
            else:
                checks.append(
                    LongestPrefixCheck(
                        id=f"longest_prefix.{name}.selection",
                        status="FAIL",
                        expected=f"rule {expected_rule_id} is selected",
                        actual=f"rule {selected_id} selected",
                        details={
                            "path": path,
                            "expected_rule_id": expected_rule_id,
                            "selected_rule_id": selected_id,
                        },
                    )
                )

            # Verify parent-prefix groups are not unioned.
            parent_groups: set[str] = set()
            for rule in rules:
                if rule["rule_id"] == selected_id:
                    continue
                rule_prefix = _canonical_prefix(rule["path_prefix"])
                selected_prefix = _canonical_prefix(selected["path_prefix"])
                if rule_prefix is None or selected_prefix is None:
                    continue
                is_parent = rule_prefix == "/" or selected_prefix.startswith(
                    rule_prefix + "/"
                )
                if is_parent:
                    parent_groups.update(rule.get("external_group_ids", []))

            selected_groups = set(selected.get("external_group_ids", []))
            if parent_groups.isdisjoint(selected_groups):
                checks.append(
                    LongestPrefixCheck(
                        id=f"longest_prefix.{name}.no_parent_union",
                        status="PASS",
                        expected="parent-prefix groups are not unioned into selected rule",
                        actual=f"selected groups {sorted(selected_groups)} do not include parent groups {sorted(parent_groups)}",
                        details={
                            "selected_groups": sorted(selected_groups),
                            "parent_groups": sorted(parent_groups),
                        },
                    )
                )
            else:
                checks.append(
                    LongestPrefixCheck(
                        id=f"longest_prefix.{name}.no_parent_union",
                        status="FAIL",
                        expected="parent-prefix groups are not unioned into selected rule",
                        actual=f"selected groups overlap parent groups by {sorted(parent_groups & selected_groups)}",
                        details={
                            "selected_groups": sorted(selected_groups),
                            "parent_groups": sorted(parent_groups),
                            "overlap": sorted(parent_groups & selected_groups),
                        },
                    )
                )

        return checks
