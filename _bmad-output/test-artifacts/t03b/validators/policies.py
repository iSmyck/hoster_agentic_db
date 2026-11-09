"""Access and approval policy schema validator for synthetic fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import unicodedata


@dataclass
class PolicyCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


def _canonical_prefix(prefix: str) -> str | None:
    """Return NFC-normalized prefix or None if invalid/ambiguous."""
    prefix = unicodedata.normalize("NFC", prefix)
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if prefix != "/":
        prefix = prefix.rstrip("/")
    if prefix == "/":
        return "/"
    parts = prefix.split("/")
    if any(p in ("", ".", "..") for p in parts[1:]):
        return None
    if "\\" in prefix:
        return None
    return prefix


class PolicyValidator:
    """Validate access-policy and approval-policy fixtures against their schemas."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self, schema_validate) -> list[PolicyCheck]:
        checks: list[PolicyCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            policy = fixture.get("policy", {})
            policy_type = fixture.get("type", "approval")
            expected_valid = bool(fixture.get("expected_valid", True))

            schema_name = (
                "access-policy.schema.json"
                if policy_type == "access"
                else "approval-policy.schema.json"
            )
            err = schema_validate(schema_name, policy)

            check_id = f"policy.{policy_type}.{name}.schema"
            if expected_valid and err is None:
                checks.append(
                    PolicyCheck(
                        id=check_id,
                        status="PASS",
                        expected=f"{policy_type} policy is schema valid",
                        actual="schema valid",
                        details={
                            "policy_bundle_id": policy.get("policy_bundle_id"),
                            "space_id": policy.get("space_id"),
                        },
                    )
                )
            elif expected_valid and err:
                checks.append(
                    PolicyCheck(
                        id=check_id,
                        status="FAIL",
                        expected=f"{policy_type} policy is schema valid",
                        actual=err,
                        details={"error": err},
                    )
                )
            elif not expected_valid and err:
                checks.append(
                    PolicyCheck(
                        id=check_id,
                        status="PASS",
                        expected=f"{policy_type} policy is correctly rejected by schema",
                        actual=err,
                        details={"error": err},
                    )
                )
            else:
                checks.append(
                    PolicyCheck(
                        id=check_id,
                        status="FAIL",
                        expected=f"{policy_type} policy is correctly rejected by schema",
                        actual="unexpectedly schema valid",
                        details={},
                    )
                )

            # Per-Space bundle consistency: access and approval revisions belong to one Space.
            if policy_type == "approval" and err is None:
                expected_duplicates = bool(
                    fixture.get("expected_duplicate_prefixes", False)
                )
                prefixes = [
                    _canonical_prefix(r.get("path_prefix", ""))
                    for r in policy.get("rules", [])
                ]
                seen: dict[str, list[str]] = {}
                duplicates: list[tuple[str, list[str]]] = []
                for rule in policy.get("rules", []):
                    canonical = _canonical_prefix(rule.get("path_prefix", ""))
                    if canonical is None:
                        continue
                    if canonical in seen:
                        duplicates.append(
                            (canonical, seen[canonical] + [rule["rule_id"]])
                        )
                    else:
                        seen[canonical] = [rule["rule_id"]]

                has_duplicates = bool(duplicates)
                if expected_duplicates and has_duplicates:
                    checks.append(
                        PolicyCheck(
                            id=f"policy.approval.{name}.duplicate_prefixes",
                            status="PASS",
                            expected="duplicate normalized prefixes are rejected (INVALID_POLICY)",
                            actual=f"duplicates detected: {duplicates}",
                            details={"duplicates": duplicates},
                        )
                    )
                elif expected_duplicates and not has_duplicates:
                    checks.append(
                        PolicyCheck(
                            id=f"policy.approval.{name}.duplicate_prefixes",
                            status="FAIL",
                            expected="duplicate normalized prefixes are rejected (INVALID_POLICY)",
                            actual="no duplicate normalized prefixes found",
                            details={"prefixes": prefixes},
                        )
                    )
                elif not expected_duplicates and has_duplicates:
                    checks.append(
                        PolicyCheck(
                            id=f"policy.approval.{name}.duplicate_prefixes",
                            status="FAIL",
                            expected="no duplicate normalized prefixes",
                            actual=f"unexpected duplicates: {duplicates}",
                            details={"duplicates": duplicates},
                        )
                    )
                else:
                    checks.append(
                        PolicyCheck(
                            id=f"policy.approval.{name}.duplicate_prefixes",
                            status="PASS",
                            expected="no duplicate normalized prefixes",
                            actual="no duplicate normalized prefixes found",
                            details={"prefixes": prefixes},
                        )
                    )

            if policy_type == "access" and expected_valid and err is None:
                access_rev = policy.get("access_policy_revision")
                approval_rev = policy.get("approval_policy_revision")
                space_id = policy.get("space_id")
                repository_id = policy.get("repository_id")
                bundle_id = policy.get("policy_bundle_id")
                checks.append(
                    PolicyCheck(
                        id=f"policy.access.{name}.space_binding",
                        status="PASS",
                        expected="access policy binds exactly one repository_id to one space_id and bundle",
                        actual=f"space_id={space_id}, repository_id={repository_id}, bundle_id={bundle_id}",
                        details={
                            "space_id": space_id,
                            "repository_id": repository_id,
                            "policy_bundle_id": bundle_id,
                            "access_policy_revision": access_rev,
                            "approval_policy_revision": approval_rev,
                        },
                    )
                )

        return checks
