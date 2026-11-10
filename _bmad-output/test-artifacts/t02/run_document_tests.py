# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T02 document tree and canonical direct read harness.

Builds two synthetic repository-per-Space fixtures, validates front matter,
tree navigation, whole/section direct reads, attachment tuples, archive
invariants and path normalization, and writes deterministic reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
from validators import (  # noqa: E402
    ArchiveValidator,
    AttachmentValidator,
    PathValidator,
    ReadValidator,
    SchemaValidator,
    TreeValidator,
    load_space,
)

CONTRACTS_DIR = Path("specs/corporate-kb/contracts")
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t02")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t02")
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


def _check(
    check_id: str,
    scenario_id: str,
    status: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "scenario_id": scenario_id,
        "status": status,
        "expected": expected,
        "actual": actual,
        "input_sha256": _file_sha256(fixture) if fixture else None,
        "fixture_path": _fixture_path(fixture),
        "rerun_cmd": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
        "details": details or {},
    }


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
        return value.startswith(repo_abs) or bool(
            re.match(r"^[A-Za-z]:\\|^/Users/|^/home/|^/tmp/|^/var/", value)
        )
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
) -> dict[str, Any]:
    return _check(check_id, scenario_id, "PASS", expected, actual, fixture, details)


def _fail(
    check_id: str,
    scenario_id: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _check(check_id, scenario_id, "FAIL", expected, actual, fixture, details)


def _blocked(
    check_id: str,
    scenario_id: str,
    reason: str,
    expected: str = "live GitLab/GO integration evidence",
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _check(
        check_id,
        scenario_id,
        "BLOCKED",
        expected,
        reason,
        fixture,
        details or {"reason": reason},
    )


def _is_negative_check(check: dict[str, Any]) -> bool:
    """Return True for intentionally invalid fixtures (bad-/malformed-)."""
    name = check.get("id", "")
    fixture = check.get("fixture_path") or ""
    return ("bad-" in name or "malformed-" in name or
            "bad-" in fixture or "malformed-" in fixture)


def _add_check(builder: ReportBuilder, check: dict[str, Any]) -> None:
    from reporters.json_reporter import Check

    details = dict(check.get("details") or {})
    if check["status"] == "FAIL" and _is_negative_check(check):
        details["expected_negative"] = True

    builder.add(
        Check(
            id=check["id"],
            scenario_id=check["scenario_id"],
            status=check["status"],
            expected=check["expected"],
            actual=check["actual"],
            input_sha256=check["input_sha256"],
            fixture_path=check["fixture_path"],
            rerun_cmd=check["rerun_cmd"],
            details=details,
        )
    )


def validate_front_matters(
    spaces: dict[str, Any], schema_validator: SchemaValidator
) -> list[dict[str, Any]]:
    """Validate every document's front matter against front-matter.schema.json."""
    checks: list[dict[str, Any]] = []
    for space in spaces.values():
        for doc in space.documents:
            fixture = space.root / doc.path
            err = schema_validator.validate_or_error(
                "front-matter.schema.json", doc.front_matter
            )
            check_id = f"front_matter.{space.space_id}.{doc.path}.schema"
            if err:
                checks.append(
                    _fail(
                        check_id,
                        "front_matter",
                        "document front matter is schema valid",
                        err,
                        fixture=fixture,
                        details={"document_id": doc.document_id, "error": err},
                    )
                )
            else:
                checks.append(
                    _pass(
                        check_id,
                        "front_matter",
                        "document front matter is schema valid",
                        "schema valid",
                        fixture=fixture,
                        details={"document_id": doc.document_id},
                    )
                )
    return checks


def validate_source_origins(
    spaces: dict[str, Any], schema_validator: SchemaValidator
) -> list[dict[str, Any]]:
    """Validate origin sub-documents where present; add synthetic cases if none."""
    checks: list[dict[str, Any]] = []
    found = False
    for space in spaces.values():
        for doc in space.documents:
            origin = doc.front_matter.get("origin")
            if origin is None:
                continue
            found = True
            err = schema_validator.validate_or_error(
                "source-origin.schema.json", origin
            )
            check_id = f"source_origin.{space.space_id}.{doc.path}.schema"
            if err:
                checks.append(
                    _fail(
                        check_id,
                        "source_origin",
                        "origin is schema valid",
                        err,
                        details={"document_id": doc.document_id},
                    )
                )
            else:
                checks.append(
                    _pass(
                        check_id,
                        "source_origin",
                        "origin is schema valid",
                        "schema valid",
                        details={
                            "document_id": doc.document_id,
                            "source_id": origin.get("source_id"),
                        },
                    )
                )
    if not found:
        # Synthetic fixture covering valid and invalid source origins.
        synthetic_cases = [
            (
                "valid",
                {
                    "schema_version": "source-origin-v1",
                    "source_id": "DOC-0001",
                    "source_binding_id": "test-binding",
                    "source_object_id": "test-object",
                    "source_version": "test-version",
                    "source_content_sha256": "0" * 64,
                    "source_ref": "test-ref",
                    "observed_at": "2026-01-01T00:00:00Z",
                    "ownership_mode": "curated",
                },
            ),
            (
                "invalid_source_id",
                {
                    "schema_version": "source-origin-v1",
                    "source_id": "DOC-0001-invalid-case",
                    "source_binding_id": "test-binding",
                    "source_object_id": "test-object",
                    "source_version": "test-version",
                    "source_content_sha256": "0" * 64,
                    "source_ref": "test-ref",
                    "observed_at": "2026-01-01T00:00:00Z",
                    "ownership_mode": "curated",
                },
            ),
        ]
        for name, origin in synthetic_cases:
            err = schema_validator.validate_or_error(
                "source-origin.schema.json", origin
            )
            check_id = f"source_origin.synthetic.{name}.schema"
            if name.startswith("invalid"):
                if err:
                    checks.append(
                        _pass(
                            check_id,
                            "source_origin",
                            "invalid origin is rejected by schema",
                            err,
                            details={"source_id": origin.get("source_id"), "error": err},
                        )
                    )
                else:
                    checks.append(
                        _fail(
                            check_id,
                            "source_origin",
                            "invalid origin is rejected by schema",
                            "unexpectedly schema valid",
                            details={"source_id": origin.get("source_id")},
                        )
                    )
            else:
                if err:
                    checks.append(
                        _fail(
                            check_id,
                            "source_origin",
                            "valid origin is schema valid",
                            err,
                            details={"source_id": origin.get("source_id"), "error": err},
                        )
                    )
                else:
                    checks.append(
                        _pass(
                            check_id,
                            "source_origin",
                            "valid origin is schema valid",
                            "schema valid",
                            details={"source_id": origin.get("source_id")},
                        )
                    )
    return checks


def run_tree_checks(spaces: dict[str, Any]) -> list[dict[str, Any]]:
    rename_scenarios = {
        "sales-pricing": {
            "77777777-7777-4777-8777-777777777777": (
                "offers/discount.md",
                "discount.md",
            ),
        },
    }
    validator = TreeValidator(spaces)
    checks: list[dict[str, Any]] = []
    for check in validator.validate(rename_scenarios):
        checks.append(
            {
                "id": check.id,
                "scenario_id": "tree",
                "status": check.status,
                "expected": check.expected,
                "actual": check.actual,
                "input_sha256": None,
                "fixture_path": None,
                "rerun_cmd": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
                "details": check.details,
            }
        )
    return checks


def run_read_checks(spaces: dict[str, Any]) -> list[dict[str, Any]]:
    section_scenarios = [
        {
            "space_id": "sales",
            "path": "playbook.md",
            "heading": "Steps",
            "occurrence": 1,
            "expect_found": True,
            "expect_truncated": False,
        },
        {
            "space_id": "sales",
            "path": "playbook.md",
            "heading": "Steps",
            "occurrence": 2,
            "expect_found": True,
            "expect_truncated": False,
        },
        {
            "space_id": "sales",
            "path": "playbook.md",
            "heading": "Steps",
            "occurrence": 3,
            "expect_found": False,
        },
    ]
    validator = ReadValidator(spaces)
    checks: list[dict[str, Any]] = []
    for check in validator.validate(section_scenarios):
        checks.append(
            {
                "id": check.id,
                "scenario_id": "read",
                "status": check.status,
                "expected": check.expected,
                "actual": check.actual,
                "input_sha256": None,
                "fixture_path": None,
                "rerun_cmd": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
                "details": check.details,
            }
        )
    return checks


def run_attachment_checks(spaces: dict[str, Any]) -> list[dict[str, Any]]:
    validator = AttachmentValidator(spaces)
    checks: list[dict[str, Any]] = []
    for check in validator.validate():
        checks.append(
            {
                "id": check.id,
                "scenario_id": "attachments",
                "status": check.status,
                "expected": check.expected,
                "actual": check.actual,
                "input_sha256": None,
                "fixture_path": None,
                "rerun_cmd": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
                "details": check.details,
            }
        )
    return checks


def run_archive_checks(spaces: dict[str, Any]) -> list[dict[str, Any]]:
    validator = ArchiveValidator(spaces)
    checks: list[dict[str, Any]] = []
    for check in validator.validate():
        checks.append(
            {
                "id": check.id,
                "scenario_id": "archive",
                "status": check.status,
                "expected": check.expected,
                "actual": check.actual,
                "input_sha256": None,
                "fixture_path": None,
                "rerun_cmd": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
                "details": check.details,
            }
        )
    return checks


def run_path_checks(fixture_path: Path, schema_validator: SchemaValidator) -> list[dict[str, Any]]:
    data = load_yaml(fixture_path)
    validator = PathValidator(data, schema_validator.validate_or_error)
    checks: list[dict[str, Any]] = []
    for check in validator.validate():
        checks.append(
            {
                "id": check.id,
                "scenario_id": "paths",
                "status": check.status,
                "expected": check.expected,
                "actual": check.actual,
                "input_sha256": _file_sha256(fixture_path),
                "fixture_path": _fixture_path(fixture_path),
                "rerun_cmd": "uv run python _bmad-output/test-artifacts/t02/run_document_tests.py",
                "details": check.details,
            }
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T02 document tree and direct read harness"
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
        _add_check(
            builder,
            _blocked(
                "harness.contracts_dir",
                "harness",
                f"contracts directory not found: {CONTRACTS_DIR}",
                fixture=CONTRACTS_DIR,
            ),
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
            _add_check(
                builder,
                _blocked(
                    f"harness.schema_load.{name}",
                    "harness",
                    f"schema {name} failed to load: {exc}",
                ),
            )
        return _write_reports(builder, args.dry_run)

    fixture_root = ROOT / "fixtures"
    spaces = {
        "sales": load_space("sales", "repo-sales", fixture_root / "sales"),
        "sales-pricing": load_space(
            "sales-pricing", "repo-sales-pricing", fixture_root / "sales-pricing"
        ),
    }

    missing_fixtures = [name for name, space in spaces.items() if not space.documents]
    if missing_fixtures:
        builder = ReportBuilder(
            baseline_commit=T00_BASELINE_COMMIT,
            spec_baseline_commit=BASELINE_COMMIT,
            contracts_version="document-front-matter-v2",
            output_dir=OUTPUT_DIR,
        )
        for name in missing_fixtures:
            _add_check(
                builder,
                _blocked(
                    f"harness.fixture_missing.{name}",
                    "harness",
                    f"Space fixture {name} has no Markdown documents",
                    expected="valid two-Space fixture with Markdown documents",
                ),
            )
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=BASELINE_COMMIT,
        contracts_version="document-front-matter-v2",
        output_dir=OUTPUT_DIR,
    )

    _add_check(
        builder,
        _pass(
            "harness.fixtures_loaded",
            "harness",
            "two synthetic Space fixtures load",
            f"loaded {sum(len(s.documents) for s in spaces.values())} documents across {len(spaces)} Spaces",
            details={"spaces": {name: len(s.documents) for name, s in spaces.items()}},
        ),
    )

    for check in validate_front_matters(spaces, schema_validator):
        _add_check(builder, check)
    for check in validate_source_origins(spaces, schema_validator):
        _add_check(builder, check)
    for check in run_tree_checks(spaces):
        _add_check(builder, check)
    for check in run_read_checks(spaces):
        _add_check(builder, check)
    for check in run_attachment_checks(spaces):
        _add_check(builder, check)
    for check in run_archive_checks(spaces):
        _add_check(builder, check)
    for check in run_path_checks(fixture_root / "paths.yaml", schema_validator):
        _add_check(builder, check)

    # Runtime-only checks remain BLOCKED.
    for sub in (
        "live_gitlab_tree_read",
        "exact_revision_git_blob",
        "authz_read_rejection",
        "cross_space_link_resolution",
    ):
        _add_check(
            builder,
            _blocked(
                f"runtime.{sub}",
                "runtime",
                "requires live GitLab/GO sandbox and ACL service",
            ),
        )

    return _write_reports(builder, args.dry_run)


def _write_reports(builder: ReportBuilder, dry_run: bool) -> int:
    if dry_run:
        print(f"Dry run: {len(builder.checks)} checks prepared.")
        print(f"Counts: {builder._counts()}")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw_report = builder.build()
    raw_path = OUTPUT_DIR / "document-results.json"
    builder.write_json(raw_path)

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(render_summary(raw_report), encoding="utf-8")

    sanitized = sanitize_for_evidence(raw_report)
    if _contains_repo_absolute(sanitized):
        raise AssertionError(
            "sanitized evidence still contains absolute paths under the repo root"
        )
    sanitized_path = EVIDENCE_DIR / "document-results.json"
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
