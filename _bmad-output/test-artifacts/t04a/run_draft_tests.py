# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T04a durable drafts, guarded navigation and cursor-based Git history harness.

Validates draft/branch contracts, idempotency, stale-base conflict detection,
history cursor/truncation and restore-through-revert-MR semantics on synthetic
YAML fixtures. Writes deterministic reports.
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
    DraftSaveValidator,
    HistoryCursorValidator,
    IdempotencyValidator,
    RestoreValidator,
    SchemaValidator,
    StaleBaseValidator,
)

CONTRACTS_DIR = Path("specs/corporate-kb/contracts")
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t04a")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t04a")
SPEC_BASELINE_COMMIT = "d2c0d072a757808ea891fbf6414f00147679f7a7"
T00_BASELINE_COMMIT = "152b00ff6aaa7b95c7b958d822bf54e8a54d1650"


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, OSError) as exc:
        raise RuntimeError(f"corrupt or empty fixture {path}: {exc}") from exc


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


def _contains_repo_absolute(value: Any) -> bool:
    """Return True if *value* contains an absolute filesystem path under the repo root."""
    repo_abs = str(REPO_ROOT.resolve())
    if isinstance(value, str):
        return value.startswith(repo_abs) or Path(value).is_absolute()
    if isinstance(value, dict):
        return any(_contains_repo_absolute(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_repo_absolute(v) for v in value)
    return False


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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py",
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py",
        details=details or {},
    )


def _blocked(
    check_id: str,
    scenario_id: str,
    reason: str,
    expected: str = "live GitLab/GO integration evidence",
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py",
        details=details or {"reason": reason},
    )


def _validator_check_to_check(
    validator_check: Any, scenario_id: str, fixture: Path | None
) -> Check:
    return Check(
        id=validator_check.id,
        scenario_id=scenario_id,
        status=validator_check.status,
        expected=validator_check.expected,
        actual=validator_check.actual,
        input_sha256=_file_sha256(fixture),
        fixture_path=_fixture_path(fixture),
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py",
        details=validator_check.details,
    )


def _load_fixtures() -> dict[str, Path]:
    fixture_root = ROOT / "fixtures"
    return {
        "drafts": fixture_root / "drafts.yaml",
        "idempotency": fixture_root / "idempotency.yaml",
        "stale_base": fixture_root / "stale_base.yaml",
        "history": fixture_root / "history.yaml",
        "restore": fixture_root / "restore.yaml",
    }


def run_draft_save_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = DraftSaveValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "draft_save", fixture_path))
    return checks


def run_idempotency_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = IdempotencyValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "idempotency", fixture_path))
    return checks


def run_stale_base_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = StaleBaseValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "stale_base", fixture_path))
    return checks


def run_history_cursor_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = HistoryCursorValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "history_cursor", fixture_path))
    return checks


def run_restore_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = RestoreValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "restore", fixture_path))
    return checks


def _build_sample_proposal_record() -> dict[str, Any]:
    """Return a schema-valid proposal-record sample referencing the draft contract."""
    return {
        "schema_version": "proposal-record-v1",
        "proposal_id": "prop-draft-1",
        "proposal_version_id": "33333333-3333-4333-8333-333333333333",
        "repository_id": "repo-sales",
        "space_id": "sales",
        "target_branch": "main",
        "proposal_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "base_sha": "ffffffffffffffffffffffffffffffffffffffff",
        "author_stable_id": "user-sales-1",
        "version_author_stable_id": "user-sales-1",
        "requester_stable_id": "user-sales-1",
        "actor_type": "human",
        "rationale": "Draft save for pricing playbook update.",
        "evidence": [
            {
                "kind": "document_revision",
                "ref": "repo-sales/playbook.md@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
                "document_id": "11111111-1111-4111-8111-111111111111",
                "revision_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            }
        ],
        "idempotency_key": "draft-sales-1",
        "payload_hash": "1111111111111111111111111111111111111111111111111111111111111111",
        "created_at": "2026-11-08T12:00:00Z",
    }


def _build_sample_decision_record() -> dict[str, Any]:
    """Return a schema-valid decision-record sample for the revert-MR approval path."""
    return {
        "schema_version": "decision-record-v1",
        "decision_id": "44444444-4444-4444-8444-444444444444",
        "proposal_id": "prop-revert-1",
        "repository_id": "repo-sales",
        "space_id": "sales",
        "target_branch": "main",
        "proposal_sha": "9999999999999999999999999999999999999999",
        "base_sha": "ffffffffffffffffffffffffffffffffffffffff",
        "action": "accepted",
        "actor_stable_id": "user-sales-approver-1",
        "actor_type": "human",
        "timestamp": "2026-11-08T13:00:00Z",
        "rationale": "Approved restore revert-MR.",
        "evidence": [],
        "policy_bundle_id": "sales-policy-bundle",
        "access_policy_revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "approval_policy_revision": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "payload_hash": "2222222222222222222222222222222222222222222222222222222222222222",
        "record_sha256": "3333333333333333333333333333333333333333333333333333333333333333",
    }


def _build_sample_front_matter() -> dict[str, Any]:
    """Return a schema-valid document-front-matter-v2 sample for a draft document."""
    return {
        "schema_version": "document-front-matter-v2",
        "id": "11111111-1111-4111-8111-111111111111",
        "title": "Pricing Playbook",
        "parent_id": None,
        "ownership_mode": "curated",
        "links": [],
        "valid_until": "2026-12-31",
        "archived": False,
        "attachments": [],
    }


def run_schema_checks(schema_validator: SchemaValidator) -> list[Check]:
    """Validate representative records against the three schemas from the spec context."""
    checks: list[Check] = []

    proposal = _build_sample_proposal_record()
    err = schema_validator.validate_or_error("proposal-record.schema.json", proposal)
    checks.append(
        _pass(
            "schema.proposal_record.valid",
            "schema",
            "sample proposal record is schema valid",
            "schema valid" if err is None else err,
            details={"proposal_id": proposal["proposal_id"], "error": err},
        )
        if err is None
        else _fail(
            "schema.proposal_record.valid",
            "schema",
            "sample proposal record is schema valid",
            err,
            details={"proposal_id": proposal["proposal_id"], "error": err},
        )
    )

    decision = _build_sample_decision_record()
    err = schema_validator.validate_or_error("decision-record.schema.json", decision)
    checks.append(
        _pass(
            "schema.decision_record.valid",
            "schema",
            "sample decision record is schema valid",
            "schema valid" if err is None else err,
            details={"decision_id": decision["decision_id"], "error": err},
        )
        if err is None
        else _fail(
            "schema.decision_record.valid",
            "schema",
            "sample decision record is schema valid",
            err,
            details={"decision_id": decision["decision_id"], "error": err},
        )
    )

    front_matter = _build_sample_front_matter()
    err = schema_validator.validate_or_error("front-matter.schema.json", front_matter)
    checks.append(
        _pass(
            "schema.front_matter.valid",
            "schema",
            "sample front matter is schema valid",
            "schema valid" if err is None else err,
            details={"document_id": front_matter["id"], "error": err},
        )
        if err is None
        else _fail(
            "schema.front_matter.valid",
            "schema",
            "sample front matter is schema valid",
            err,
            details={"document_id": front_matter["id"], "error": err},
        )
    )

    # Regex and ref integrity are useful structural checks reusing T03b patterns.
    regex_results = schema_validator.compile_regexes()
    bad_regex = [r for r in regex_results if r[2] is not None]
    if bad_regex:
        checks.append(
            _fail(
                "schema.regex_compile",
                "schema",
                "all schema regex patterns compile",
                f"bad regex: {bad_regex[:3]}",
                details={"bad_regex_count": len(bad_regex)},
            )
        )
    else:
        checks.append(
            _pass(
                "schema.regex_compile",
                "schema",
                "all schema regex patterns compile",
                f"{len(regex_results)} patterns compiled",
            )
        )

    ref_results = schema_validator.resolve_refs()
    unresolved = [r for r in ref_results if r[2] is not None]
    if unresolved:
        checks.append(
            _fail(
                "schema.refs_resolve",
                "schema",
                "all schema $ref resolve",
                f"unresolved: {unresolved[:3]}",
                details={"unresolved_count": len(unresolved)},
            )
        )
    else:
        checks.append(
            _pass(
                "schema.refs_resolve",
                "schema",
                "all schema $ref resolve",
                f"{len(ref_results)} refs resolved",
            )
        )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T04a durable drafts, guarded navigation and cursor-based Git history harness"
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
            spec_baseline_commit=SPEC_BASELINE_COMMIT,
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
            spec_baseline_commit=SPEC_BASELINE_COMMIT,
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

    fixtures = _load_fixtures()
    missing_fixtures = [
        str(p.relative_to(REPO_ROOT)) for p in fixtures.values() if not p.exists()
    ]
    if missing_fixtures:
        builder = ReportBuilder(
            baseline_commit=T00_BASELINE_COMMIT,
            spec_baseline_commit=SPEC_BASELINE_COMMIT,
            contracts_version="proposal-record-v1",
            output_dir=OUTPUT_DIR,
        )
        for path in missing_fixtures:
            builder.add(
                _blocked(
                    f"harness.fixture_missing.{Path(path).name}",
                    "harness",
                    f"fixture not found: {path}",
                    expected="valid draft/idempotency/stale-base/history/restore fixtures",
                )
            )
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=SPEC_BASELINE_COMMIT,
        contracts_version="proposal-record-v1",
        output_dir=OUTPUT_DIR,
    )

    builder.add(
        _pass(
            "harness.fixtures_loaded",
            "harness",
            "synthetic draft fixtures load",
            f"loaded {len(fixtures)} fixture files",
            details={"fixtures": sorted(fixtures.keys())},
        )
    )

    for check in run_schema_checks(schema_validator):
        builder.add(check)

    fixture_runs = [
        ("draft_save", run_draft_save_checks, fixtures["drafts"]),
        ("idempotency", run_idempotency_checks, fixtures["idempotency"]),
        ("stale_base", run_stale_base_checks, fixtures["stale_base"]),
        ("history_cursor", run_history_cursor_checks, fixtures["history"]),
        ("restore", run_restore_checks, fixtures["restore"]),
    ]
    for scenario, run_fn, fixture_path in fixture_runs:
        try:
            for check in run_fn(fixture_path):
                builder.add(check)
        except RuntimeError as exc:
            builder.add(
                _blocked(
                    f"harness.fixture_load.{scenario}",
                    "harness",
                    str(exc),
                    expected=f"valid {scenario} fixtures",
                )
            )

    # Runtime-only checks remain BLOCKED.
    for sub in (
        "live_gitlab_draft_branch",
        "live_gitlab_save_cas",
        "live_gitlab_idempotency_registry",
        "live_gitlab_stale_base_diff",
        "live_gitlab_history_cursor",
        "live_gitlab_restore_revert_mr",
    ):
        builder.add(
            _blocked(
                f"runtime.{sub}",
                "runtime",
                "requires live GitLab/GO sandbox and credentials",
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
    raw_path = OUTPUT_DIR / "draft-results.json"
    try:
        builder.write_json(raw_path)
    except OSError as exc:
        print(f"Failed to write {raw_path}: {exc}", file=sys.stderr)
        return 1

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(render_summary(raw_report), encoding="utf-8")

    sanitized = sanitize_for_evidence(raw_report)
    if _contains_repo_absolute(sanitized):
        raise AssertionError(
            "sanitized evidence still contains absolute paths under the repo root"
        )
    sanitized_path = EVIDENCE_DIR / "draft-results.json"
    try:
        dump_json(sanitized_path, sanitized)
    except OSError as exc:
        print(f"Failed to write {sanitized_path}: {exc}", file=sys.stderr)
        return 1

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
