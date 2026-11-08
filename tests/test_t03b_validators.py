"""Unit tests for T03b longest-prefix policy validator."""

from __future__ import annotations

from typing import Any


def test_canonical_prefix(t03b_modules: Any) -> None:
    cp = t03b_modules.longest_prefix._canonical_prefix

    assert cp("/sales") == "/sales"
    assert cp("/sales/") == "/sales"
    assert cp("/") == "/"
    assert cp("/sales/../foo") is None
    assert cp("/sales/./foo") is None
    assert cp("/sales\\foo") is None
    assert cp("") is None


def test_longest_prefix_selection(t03b_modules: Any) -> None:
    _select = t03b_modules.longest_prefix._select_rule
    rules = [
        {"rule_id": "r1", "path_prefix": "/", "external_group_ids": ["all"]},
        {"rule_id": "r2", "path_prefix": "/sales", "external_group_ids": ["sales"]},
        {
            "rule_id": "r3",
            "path_prefix": "/sales/pricing",
            "external_group_ids": ["pricing"],
        },
    ]

    selected = _select(rules, "/sales/pricing/discount.md")
    assert selected is not None
    assert selected["rule_id"] == "r3"

    selected_root_only = _select([rules[0]], "/anything.md")
    assert selected_root_only is not None
    assert selected_root_only["rule_id"] == "r1"

    # Root prefix matches every path, so use a rule list without root for no-match.
    selected_no_match = _select(rules[1:], "/engineering/runbook.md")
    assert selected_no_match is None


def test_no_parent_union_pass(t03b_modules: Any) -> None:
    fixture = {
        "name": "no_union",
        "path": "/sales/pricing/discount.md",
        "rules": [
            {
                "rule_id": "r1",
                "path_prefix": "/sales",
                "external_group_ids": ["sales"],
            },
            {
                "rule_id": "r2",
                "path_prefix": "/sales/pricing",
                "external_group_ids": ["pricing"],
            },
        ],
        "expected_rule_id": "r2",
    }
    checks = t03b_modules.longest_prefix.LongestPrefixValidator([fixture]).validate()

    selection = next(c for c in checks if c.id == "longest_prefix.no_union.selection")
    no_union = next(
        c for c in checks if c.id == "longest_prefix.no_union.no_parent_union"
    )
    assert selection.status == "PASS"
    assert no_union.status == "PASS"


def test_parent_prefix_union_detected(t03b_modules: Any) -> None:
    fixture = {
        "name": "parent_union",
        "path": "/sales/pricing/discount.md",
        "rules": [
            {
                "rule_id": "r1",
                "path_prefix": "/sales",
                "external_group_ids": ["sales"],
            },
            {
                "rule_id": "r2",
                "path_prefix": "/sales/pricing",
                "external_group_ids": ["pricing", "sales"],
            },
        ],
        "expected_rule_id": "r2",
    }
    checks = t03b_modules.longest_prefix.LongestPrefixValidator([fixture]).validate()

    selection = next(
        c for c in checks if c.id == "longest_prefix.parent_union.selection"
    )
    no_union = next(
        c for c in checks if c.id == "longest_prefix.parent_union.no_parent_union"
    )
    assert selection.status == "PASS"
    assert no_union.status == "FAIL"


def test_duplicate_prefix_selection(t03b_modules: Any) -> None:
    fixture = {
        "name": "dup_prefix",
        "path": "/sales/deal.md",
        "rules": [
            {
                "rule_id": "r1",
                "path_prefix": "/sales",
                "external_group_ids": ["sales"],
            },
            {
                "rule_id": "r2",
                "path_prefix": "/sales",
                "external_group_ids": ["pricing"],
            },
        ],
        "expected_rule_id": "r1",
    }
    checks = t03b_modules.longest_prefix.LongestPrefixValidator([fixture]).validate()

    selection = next(c for c in checks if c.id == "longest_prefix.dup_prefix.selection")
    # Selection is stable (first matching rule wins in this implementation).
    assert selection.status == "PASS"
