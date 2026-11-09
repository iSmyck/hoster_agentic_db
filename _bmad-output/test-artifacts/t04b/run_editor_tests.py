# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T04b lossless TipTap adapter and browser editor gate harness.

Validates canonical Markdown/front-matter round-trip fidelity and synthetic
browser editor gate vectors (IME ordering, accessibility exposure, XSS/MDX
rejection) on synthetic fixtures. Real browser automation remains BLOCKED.
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
    AccessibilityValidator,
    FrontMatterBoundaryValidator,
    IMEValidator,
    RoundTripValidator,
    SchemaValidator,
    XSSValidator,
)

CONTRACTS_DIR = Path("specs/corporate-kb/contracts")
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t04b")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t04b")
SPEC_BASELINE_COMMIT = "d2c0d072a757808ea891fbf6414f00147679f7a7"
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py",
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py",
        details=details or {},
    )


def _blocked(
    check_id: str,
    scenario_id: str,
    reason: str,
    expected: str = "live browser/sandbox integration evidence",
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py",
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py",
        details=validator_check.details,
    )


def _load_fixtures() -> dict[str, Path]:
    fixture_root = ROOT / "fixtures"
    return {
        "roundtrip": fixture_root / "roundtrip.yaml",
        "front_matter_boundary": fixture_root / "front_matter_boundary.yaml",
        "ime": fixture_root / "ime.yaml",
        "accessibility": fixture_root / "accessibility.yaml",
        "xss": fixture_root / "xss.yaml",
    }


def _build_sample_front_matter() -> dict[str, Any]:
    """Return a schema-valid document-front-matter-v2 sample with full constructs."""
    return {
        "schema_version": "document-front-matter-v2",
        "id": "11111111-1111-4111-8111-111111111111",
        "title": "Pricing Playbook",
        "parent_id": None,
        "ownership_mode": "migrated",
        "origin": {
            "schema_version": "source-origin-v1",
            "source_id": "legacy-doc-42",
            "source_binding_id": "legacy-binding",
            "source_object_id": "doc-42",
            "source_version": "1.0",
            "source_content_sha256": "0" * 64,
            "source_ref": "source://legacy/doc-42",
            "observed_at": "2026-11-01T00:00:00Z",
            "ownership_mode": "migrated",
        },
        "links": [
            {
                "target_document_id": "22222222-2222-4222-8222-222222222222",
                "relation": "references",
            }
        ],
        "valid_until": "2026-12-31",
        "archived": True,
        "archive": {
            "archived_at": "2026-11-01T00:00:00Z",
            "reason": "Superseded",
            "replacement_document_id": "33333333-3333-4333-8333-333333333333",
        },
        "attachments": [
            {
                "object_id": "att-1",
                "version": "1",
                "sha256": "0" * 64,
                "size": 1234,
                "media_type": "application/pdf",
                "source_ref": "source://sales/att-1",
                "media_class": "substantive",
                "verification_status": "verified",
            }
        ],
    }


def run_schema_checks(schema_validator: SchemaValidator) -> list[Check]:
    """Validate representative front matter against the v2 schema and schema integrity."""
    checks: list[Check] = []

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


def run_roundtrip_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = RoundTripValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "round_trip", fixture_path))
    return checks


def run_front_matter_boundary_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = FrontMatterBoundaryValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(
            _validator_check_to_check(check, "front_matter_boundary", fixture_path)
        )
    return checks


def run_ime_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = IMEValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "ime", fixture_path))
    return checks


def run_accessibility_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = AccessibilityValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "accessibility", fixture_path))
    return checks


def run_xss_checks(fixture_path: Path) -> list[Check]:
    data = load_yaml(fixture_path)
    validator = XSSValidator(data.get("fixtures", []))
    checks: list[Check] = []
    for check in validator.validate():
        checks.append(_validator_check_to_check(check, "xss", fixture_path))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T04b lossless TipTap adapter and browser editor gate harness"
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
            contracts_version="document-front-matter-v2",
            output_dir=OUTPUT_DIR,
        )
        for path in missing_fixtures:
            builder.add(
                _blocked(
                    f"harness.fixture_missing.{Path(path).name}",
                    "harness",
                    f"fixture not found: {path}",
                    expected="valid round-trip/front-matter/IME/accessibility/XSS fixtures",
                )
            )
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=SPEC_BASELINE_COMMIT,
        contracts_version="document-front-matter-v2",
        output_dir=OUTPUT_DIR,
    )

    builder.add(
        _pass(
            "harness.fixtures_loaded",
            "harness",
            "synthetic editor fixtures load",
            f"loaded {len(fixtures)} fixture files",
            details={"fixtures": sorted(fixtures.keys())},
        )
    )

    for check in run_schema_checks(schema_validator):
        builder.add(check)
    for check in run_roundtrip_checks(fixtures["roundtrip"]):
        builder.add(check)
    for check in run_front_matter_boundary_checks(fixtures["front_matter_boundary"]):
        builder.add(check)
    for check in run_ime_checks(fixtures["ime"]):
        builder.add(check)
    for check in run_accessibility_checks(fixtures["accessibility"]):
        builder.add(check)
    for check in run_xss_checks(fixtures["xss"]):
        builder.add(check)

    # Real browser automation remains BLOCKED.
    for sub in (
        "live_browser_ime_composition",
        "live_screen_reader_labels",
        "live_keyboard_focus_navigation",
        "live_xss_render_exposure",
        "live_managed_preview_save",
    ):
        builder.add(
            _blocked(
                f"runtime.{sub}",
                "runtime",
                "requires sandboxed browser automation and credentials",
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
    raw_path = OUTPUT_DIR / "editor-results.json"
    builder.write_json(raw_path)

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(render_summary(raw_report), encoding="utf-8")

    sanitized = sanitize_for_evidence(raw_report)
    if _contains_repo_absolute(sanitized):
        raise AssertionError(
            "sanitized evidence still contains absolute paths under the repo root"
        )
    sanitized_path = EVIDENCE_DIR / "editor-results.json"
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
