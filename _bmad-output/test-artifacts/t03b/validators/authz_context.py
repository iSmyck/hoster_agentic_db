"""AuthzContext per-Space isolation validator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AuthzContextCheck:
    id: str
    status: str
    expected: str
    actual: str
    details: dict[str, Any]


class AuthzContextValidator:
    """Validate that AuthzContext-v2 carries independent per-Space bindings."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    @staticmethod
    def _space_binding(scope: dict[str, Any]) -> dict[str, Any]:
        return {
            "space_id": scope.get("space_id"),
            "repository_id": scope.get("repository_id"),
            "policy_bundle_id": scope.get("policy_bundle_id"),
            "access_policy_revision": scope.get("access_policy_revision"),
            "approval_policy_revision": scope.get("approval_policy_revision"),
            "group_snapshot_id": scope.get("group_snapshot", {}).get("snapshot_id"),
            "revocation_epoch": scope.get("revocation_epoch"),
        }

    def validate(self, schema_validate) -> list[AuthzContextCheck]:
        checks: list[AuthzContextCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            context = fixture.get("context", {})
            expected_valid = bool(fixture.get("expected_valid", True))
            expected_isolated = bool(fixture.get("expected_isolated", True))

            err = schema_validate("authz-context.schema.json", context)
            if expected_valid and err is None:
                checks.append(
                    AuthzContextCheck(
                        id=f"authz_context.{name}.schema",
                        status="PASS",
                        expected="AuthzContext is schema valid",
                        actual="schema valid",
                        details={"stable_id": context.get("stable_id")},
                    )
                )
            elif expected_valid and err:
                checks.append(
                    AuthzContextCheck(
                        id=f"authz_context.{name}.schema",
                        status="FAIL",
                        expected="AuthzContext is schema valid",
                        actual=err,
                        details={"stable_id": context.get("stable_id"), "error": err},
                    )
                )
            elif not expected_valid and err:
                checks.append(
                    AuthzContextCheck(
                        id=f"authz_context.{name}.schema",
                        status="PASS",
                        expected="AuthzContext is correctly rejected by schema",
                        actual=err,
                        details={"error": err},
                    )
                )
            else:
                checks.append(
                    AuthzContextCheck(
                        id=f"authz_context.{name}.schema",
                        status="FAIL",
                        expected="AuthzContext is correctly rejected by schema",
                        actual="unexpectedly schema valid",
                        details={},
                    )
                )

            if expected_valid and err is None:
                space_scopes = context.get("space_scopes", [])
                path_scopes = context.get("path_scopes", [])

                # Every Space binding is independent.
                bindings = [self._space_binding(s) for s in space_scopes]

                def _shared_values(key: str) -> list[Any]:
                    values = [b[key] for b in bindings]
                    seen: set[Any] = set()
                    shared: list[Any] = []
                    for v in values:
                        if v in seen:
                            shared.append(v)
                        seen.add(v)
                    return shared

                shared_space_ids = _shared_values("space_id")
                shared_repository_ids = _shared_values("repository_id")
                shared_bundle_ids = _shared_values("policy_bundle_id")
                shared_group_snapshot_ids = _shared_values("group_snapshot_id")

                # Every path_scope.space_id has exactly one matching space_scope.
                path_space_ids = {p.get("space_id") for p in path_scopes}
                space_ids = {s.get("space_id") for s in space_scopes}
                orphan_paths = path_space_ids - space_ids

                isolated = (
                    not shared_space_ids
                    and not shared_repository_ids
                    and not shared_bundle_ids
                    and not shared_group_snapshot_ids
                    and not orphan_paths
                )
                if expected_isolated and isolated:
                    checks.append(
                        AuthzContextCheck(
                            id=f"authz_context.{name}.space_isolation",
                            status="PASS",
                            expected="each Space has independent repository/bundle/revisions/group/epoch bindings",
                            actual=f"{len(bindings)} independent Space binding(s), no orphan path scopes",
                            details={"bindings": bindings},
                        )
                    )
                elif expected_isolated and not isolated:
                    checks.append(
                        AuthzContextCheck(
                            id=f"authz_context.{name}.space_isolation",
                            status="FAIL",
                            expected="each Space has independent repository/bundle/revisions/group/epoch bindings",
                            actual=(
                                f"shared_space_ids={shared_space_ids}, "
                                f"shared_repository_ids={shared_repository_ids}, "
                                f"shared_bundle_ids={shared_bundle_ids}, "
                                f"shared_group_snapshot_ids={shared_group_snapshot_ids}, "
                                f"orphan_path_space_ids={sorted(orphan_paths)}"
                            ),
                            details={
                                "bindings": bindings,
                                "shared_space_ids": shared_space_ids,
                                "shared_repository_ids": shared_repository_ids,
                                "shared_bundle_ids": shared_bundle_ids,
                                "shared_group_snapshot_ids": shared_group_snapshot_ids,
                                "orphan_path_space_ids": sorted(orphan_paths),
                            },
                        )
                    )
                elif not expected_isolated and isolated:
                    checks.append(
                        AuthzContextCheck(
                            id=f"authz_context.{name}.space_isolation",
                            status="FAIL",
                            expected="fixture should exhibit shared or missing Space bindings",
                            actual="all Space bindings are independent",
                            details={"bindings": bindings},
                        )
                    )
                else:
                    checks.append(
                        AuthzContextCheck(
                            id=f"authz_context.{name}.space_isolation",
                            status="PASS",
                            expected="fixture should exhibit shared or missing Space bindings",
                            actual=(
                                f"shared_space_ids={shared_space_ids}, "
                                f"shared_repository_ids={shared_repository_ids}, "
                                f"shared_bundle_ids={shared_bundle_ids}, "
                                f"shared_group_snapshot_ids={shared_group_snapshot_ids}, "
                                f"orphan_path_space_ids={sorted(orphan_paths)}"
                            ),
                            details={
                                "shared_space_ids": shared_space_ids,
                                "shared_repository_ids": shared_repository_ids,
                                "shared_bundle_ids": shared_bundle_ids,
                                "shared_group_snapshot_ids": shared_group_snapshot_ids,
                                "orphan_path_space_ids": sorted(orphan_paths),
                            },
                        )
                    )

        return checks
