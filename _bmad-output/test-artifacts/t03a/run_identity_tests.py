# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T03a stable identity core and nested group snapshots harness.

Validates identity contracts on synthetic fixtures: stable ID schemas,
nested group membership, epoch ordering, rename survival and empty-group
handling. Writes deterministic reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Make the harness package importable when run from the repository root.
ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporters import ReportBuilder, render_summary, sanitize_for_evidence  # noqa: E402
from reporters.json_reporter import Check  # noqa: E402
from validators import (  # noqa: E402
    EpochValidator,
    GroupSnapshotValidator,
    IdentityValidator,
    RenameValidator,
    SchemaValidator,
)

CONTRACTS_DIR = Path("specs/corporate-kb/contracts")
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t03a")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t03a")
BASELINE_COMMIT = "788e299a5316c7d5df685a8f11b043ff36135a10"
T00_BASELINE_COMMIT = "152b00ff6aaa7b95c7b958d822bf54e8a54d1650"


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_path(path: Path | None) -> str | None:
    """Return project-root-relative path for evidence portability."""
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _pass(
    check_id: str,
    scenario_id: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> Check:
    return Check(
        id=check_id,
        scenario_id=scenario_id,
        status="PASS",
        expected=expected,
        actual=actual,
        input_sha256=_file_sha256(fixture),
        fixture_path=_fixture_path(fixture),
        rerun_cmd="uv run python _bmad-output/test-artifacts/t03a/run_identity_tests.py",
        details=details or {},
    )


def _fail(
    check_id: str,
    scenario_id: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> Check:
    return Check(
        id=check_id,
        scenario_id=scenario_id,
        status="FAIL",
        expected=expected,
        actual=actual,
        input_sha256=_file_sha256(fixture),
        fixture_path=_fixture_path(fixture),
        rerun_cmd="uv run python _bmad-output/test-artifacts/t03a/run_identity_tests.py",
        details=details or {},
    )


def _blocked(
    check_id: str,
    scenario_id: str,
    reason: str,
    expected: str = "live IdP/LDAP/AD/GO integration evidence",
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> Check:
    return Check(
        id=check_id,
        scenario_id=scenario_id,
        status="BLOCKED",
        expected=expected,
        actual=reason,
        input_sha256=_file_sha256(fixture),
        fixture_path=_fixture_path(fixture),
        rerun_cmd="uv run python _bmad-output/test-artifacts/t03a/run_identity_tests.py",
        details=details or {"reason": reason},
    )


def _identity_check_to_check(identity_check: Any, fixture: Path) -> Check:
    return Check(
        id=identity_check.id,
        scenario_id=identity_check.__class__.__name__.replace("Check", "").lower(),
        status=identity_check.status,
        expected=identity_check.expected,
        actual=identity_check.actual,
        input_sha256=_file_sha256(fixture),
        fixture_path=_fixture_path(fixture),
        rerun_cmd="uv run python _bmad-output/test-artifacts/t03a/run_identity_tests.py",
        details=identity_check.details,
    )


def run_identity_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = IdentityValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_identity_check_to_check(check, fixture_path))
    return checks


def run_group_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = GroupSnapshotValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_identity_check_to_check(check, fixture_path))
    return checks


def run_rename_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = RenameValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_identity_check_to_check(check, fixture_path))
    return checks


def run_epoch_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = EpochValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_identity_check_to_check(check, fixture_path))
    return checks


def run_authz_context_checks(
    fixture_path: Path, schema_validator: SchemaValidator
) -> list[Check]:
    data = load_yaml(fixture_path)
    checks: list[Check] = []
    for fixture in data.get("fixtures", []):
        name = fixture.get("name", "unnamed")
        payload = fixture.get("payload", {})
        expected_valid = bool(fixture.get("expected_valid", True))
        err = schema_validator.validate_or_error("authz-context.schema.json", payload)
        check_id = f"authz_context.{name}.schema"
        if expected_valid and err is None:
            checks.append(
                _pass(
                    check_id,
                    "authz_context",
                    "AuthzContext payload is schema valid",
                    "schema valid",
                    fixture=fixture_path,
                    details={"stable_id": payload.get("stable_id")},
                )
            )
        elif expected_valid and err:
            checks.append(
                _fail(
                    check_id,
                    "authz_context",
                    "AuthzContext payload is schema valid",
                    err,
                    fixture=fixture_path,
                    details={"stable_id": payload.get("stable_id"), "error": err},
                )
            )
        elif not expected_valid and err:
            checks.append(
                _pass(
                    check_id,
                    "authz_context",
                    "AuthzContext payload is correctly rejected by schema",
                    err,
                    fixture=fixture_path,
                    details={"error": err},
                )
            )
        else:
            checks.append(
                _fail(
                    check_id,
                    "authz_context",
                    "AuthzContext payload is correctly rejected by schema",
                    "unexpectedly schema valid",
                    fixture=fixture_path,
                    details={},
                )
            )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T03a stable identity core and nested group snapshots harness"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse fixtures and list checks without writing reports",
    )
    args = parser.parse_args()

    if not CONTRACTS_DIR.exists():
        builder = ReportBuilder(
            baseline_commit=T00_BASELINE_COMMIT,
            spec_baseline_commit=BASELINE_COMMIT,
            contracts_version="unknown",
            output_dir=OUTPUT_DIR,
        )
        builder.add(
            _blocked(
                "harness.contracts_dir",
                "harness",
                f"contracts directory not found: {CONTRACTS_DIR}",
                fixture=CONTRACTS_DIR,
            )
        )
        return _write_reports(builder, args.dry_run)

    schema_validator = SchemaValidator(CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = ReportBuilder(
            baseline_commit=T00_BASELINE_COMMIT,
            spec_baseline_commit=BASELINE_COMMIT,
            contracts_version="unknown",
            output_dir=OUTPUT_DIR,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(
                _blocked(
                    f"harness.schema_load.{name}",
                    "harness",
                    f"schema {name} failed to load: {exc}",
                )
            )
        return _write_reports(builder, args.dry_run)

    fixture_root = ROOT / "fixtures"
    identity_fixture = fixture_root / "identities.yaml"
    groups_fixture = fixture_root / "groups.yaml"
    renames_fixture = fixture_root / "renames.yaml"
    epochs_fixture = fixture_root / "epochs.yaml"
    authz_fixture = fixture_root / "authz_contexts.yaml"

    missing_fixtures = [
        str(p.relative_to(REPO_ROOT))
        for p in [
            identity_fixture,
            groups_fixture,
            renames_fixture,
            epochs_fixture,
            authz_fixture,
        ]
        if not p.exists()
    ]
    if missing_fixtures:
        builder = ReportBuilder(
            baseline_commit=T00_BASELINE_COMMIT,
            spec_baseline_commit=BASELINE_COMMIT,
            contracts_version="authz-context-v2",
            output_dir=OUTPUT_DIR,
        )
        for path in missing_fixtures:
            builder.add(
                _blocked(
                    f"harness.fixture_missing.{Path(path).name}",
                    "harness",
                    f"fixture not found: {path}",
                    expected="valid identity/group/rename/epoch fixtures",
                )
            )
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=BASELINE_COMMIT,
        contracts_version="authz-context-v2",
        output_dir=OUTPUT_DIR,
    )

    builder.add(
        _pass(
            "harness.fixtures_loaded",
            "harness",
            "synthetic identity and group fixtures load",
            "loaded identities, groups, renames, epochs and authz_context fixtures",
            details={
                "fixtures": [
                    "identities.yaml",
                    "groups.yaml",
                    "renames.yaml",
                    "epochs.yaml",
                    "authz_contexts.yaml",
                ]
            },
        )
    )

    for check in run_identity_checks(identity_fixture):
        builder.add(check)
    for check in run_group_checks(groups_fixture):
        builder.add(check)
    for check in run_rename_checks(renames_fixture):
        builder.add(check)
    for check in run_epoch_checks(epochs_fixture):
        builder.add(check)
    for check in run_authz_context_checks(authz_fixture, schema_validator):
        builder.add(check)

    # Runtime-only checks remain BLOCKED.
    for sub in (
        "live_ldap_nested_groups",
        "live_oidc_jit_provisioning",
        "live_ad_object_guid",
        "live_keycloak_rename",
        "live_empty_group_revocation",
        "live_policy_epoch_sync",
    ):
        builder.add(
            _blocked(
                f"runtime.{sub}",
                "runtime",
                "requires live IdP/LDAP/AD/GO sandbox and credentials",
            )
        )

    return _write_reports(builder, args.dry_run)


def _write_reports(builder: ReportBuilder, dry_run: bool) -> int:
    if dry_run:
        counts = builder._counts()
        print(f"Dry run: {len(builder.checks)} checks prepared.")
        print(f"Counts: {counts}")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw_report = builder.build()
    raw_path = OUTPUT_DIR / "identity-results.json"
    builder.write_json(raw_path)

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(render_summary(raw_report), encoding="utf-8")

    sanitized = sanitize_for_evidence(raw_report)
    sanitized_path = EVIDENCE_DIR / "identity-results.json"
    dump_json(sanitized_path, sanitized)

    evidence_summary_path = EVIDENCE_DIR / "summary.md"
    evidence_summary_path.write_text(render_summary(sanitized), encoding="utf-8")

    print(f"Wrote {raw_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {sanitized_path}")
    print(f"Wrote {evidence_summary_path}")
    print(f"Counts: {raw_report['counts']}")

    return 1 if raw_report["counts"].get("FAIL", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
