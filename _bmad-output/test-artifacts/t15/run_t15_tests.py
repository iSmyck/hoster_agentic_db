# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T15 safe source registry, three-way updates and durable cursors harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
COMMON_ROOT = ROOT.parent
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

import harness_common as hc

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t15")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t15")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t15/run_t15_tests.py"
BLOCKED_NOTE = (
    "Real source connector integration remains BLOCKED pending owner selection, sandbox and credentials. "
    "This report contains only synthetic structural evidence; it does not claim production source integration PASS."
)


def _check(
    check_id: str,
    scenario_id: str,
    status: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
    expected_negative: bool = False,
) -> hc.Check:
    return hc.make_check(
        check_id,
        scenario_id,
        status,
        expected,
        actual,
        rerun_cmd=RERUN_CMD,
        fixture=fixture,
        details=details,
        expected_negative=expected_negative,
    )


def check_source_registry(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        has_space = bool(inp.get("space_id"))
        has_source = bool(inp.get("source_id"))
        has_repo = bool(inp.get("repository_id"))
        mode = inp.get("ownership_mode", "")
        origin = inp.get("origin", {})
        origin_mode_matches = origin.get("ownership_mode") == mode
        required_origin = mode in {"migrated", "source_managed"}
        origin_ok = (not required_origin) or (required_origin and origin_mode_matches and bool(origin.get("source_id")))
        ok = has_space and has_source and has_repo and mode in {"migrated", "source_managed", "curated", "live_operational"} and origin_ok
        details = {
            "space_id": inp.get("space_id"),
            "source_id": inp.get("source_id"),
            "repository_id": inp.get("repository_id"),
            "ownership_mode": mode,
            "origin_mode_matches": origin_mode_matches,
            "origin_present": bool(origin),
        }
        if exp_status == "PASS":
            checks.append(_check(f"source_registry.{name}.valid", "source_registry", "PASS" if ok else "FAIL",
                "source registry records stable binding with mode-appropriate origin",
                "registry entry valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"source_registry.{name}.rejected", "source_registry", "FAIL" if not ok else "PASS",
                f"invalid registry entry rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                "registry entry problem detected" if not ok else "registry entry unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_cursor_durability(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        seen = inp.get("seen", {})
        proposed = inp.get("proposed", {})
        merged = inp.get("merged", {})
        seen_durable = bool(seen.get("metadata_durable"))
        proposed_durable = bool(proposed.get("mr_durable")) and bool(proposed.get("proposal_record_durable"))
        merged_verified = bool(merged.get("git_merge_verified")) and bool(merged.get("source_mapping_reconciled"))
        cursor_ok = (
            (seen.get("cursor") == "seen" and seen_durable)
            and (proposed.get("cursor") in {"seen", "proposed"} and (proposed.get("cursor") != "proposed" or proposed_durable))
            and (merged.get("cursor") in {"seen", "proposed", "merged"} and (merged.get("cursor") != "merged" or (proposed_durable and merged_verified)))
        )
        details = {
            "seen_durable": seen_durable,
            "proposed_durable": proposed_durable,
            "merged_verified": merged_verified,
            "cursor_sequence": f"{seen.get('cursor')}->{proposed.get('cursor')}->{merged.get('cursor')}",
        }
        if exp_status == "PASS":
            checks.append(_check(f"cursor_durability.{name}.valid", "cursor_durability", "PASS" if cursor_ok else "FAIL",
                "cursor advances only after durable evidence",
                "cursor durable" if cursor_ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"cursor_durability.{name}.rejected", "cursor_durability", "FAIL" if not cursor_ok else "PASS",
                f"cursor advance without durable evidence rejected with {exp.get('error', 'INVALID_STATE')}",
                "cursor durability problem detected" if not cursor_ok else "cursor unexpectedly durable",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_same_hash_noop(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        same_hash = bool(inp.get("same_source_hash"))
        existing_open = bool(inp.get("existing_proposal_open"))
        created_new = bool(inp.get("created_new_proposal"))
        ok = same_hash and not created_new
        details = {
            "same_source_hash": same_hash,
            "existing_proposal_open": existing_open,
            "created_new_proposal": created_new,
        }
        if exp_status == "PASS":
            checks.append(_check(f"same_hash_noop.{name}.noop", "same_hash_noop", "PASS" if ok else "FAIL",
                "same source hash is a no-op or returns existing proposal",
                "same-hash no-op honored" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"same_hash_noop.{name}.rejected", "same_hash_noop", "FAIL" if not ok else "PASS",
                f"duplicate proposal rejected with {exp.get('error', 'INVALID_STATE')}",
                "duplicate proposal detected" if not ok else "no-op unexpectedly honored",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_one_outstanding_proposal(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        open_count = inp.get("outstanding_proposal_count", 0)
        new_observation = bool(inp.get("new_observation"))
        updated_seen_only = bool(inp.get("updated_seen_only"))
        ok = open_count <= 1 and (not new_observation or updated_seen_only or open_count == 0)
        details = {
            "outstanding_proposal_count": open_count,
            "new_observation": new_observation,
            "updated_seen_only": updated_seen_only,
        }
        if exp_status == "PASS":
            checks.append(_check(f"one_outstanding_proposal.{name}.valid", "one_outstanding_proposal", "PASS" if ok else "FAIL",
                "at most one outstanding proposal per source object; new observations update seen only",
                "one-proposal rule honored" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"one_outstanding_proposal.{name}.rejected", "one_outstanding_proposal", "FAIL" if not ok else "PASS",
                f"second outstanding proposal rejected with {exp.get('error', 'INVALID_STATE')}",
                "multiple outstanding proposals detected" if not ok else "one-proposal rule unexpectedly honored",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_ownership_modes(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        mode = inp.get("ownership_mode", "")
        local_edit = bool(inp.get("local_edit_attempted"))
        three_way = bool(inp.get("three_way_proposal_created"))
        write_attempt = bool(inp.get("write_attempted"))
        if mode == "migrated":
            ok = not bool(inp.get("old_source_still_writer"))
        elif mode == "source_managed":
            ok = not local_edit
        elif mode == "curated":
            ok = three_way and not write_attempt
        elif mode == "live_operational":
            ok = not write_attempt
        else:
            ok = False
        details = {
            "ownership_mode": mode,
            "local_edit_attempted": local_edit,
            "three_way_proposal_created": three_way,
            "write_attempted": write_attempt,
        }
        if exp_status == "PASS":
            checks.append(_check(f"ownership_modes.{name}.valid", "ownership_modes", "PASS" if ok else "FAIL",
                "ownership mode rules enforced",
                "ownership mode valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"ownership_modes.{name}.rejected", "ownership_modes", "FAIL" if not ok else "PASS",
                f"ownership mode violation rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "ownership mode violation detected" if not ok else "ownership mode unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_source_deletion_tombstone(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        deleted = bool(inp.get("source_deleted")) or bool(inp.get("source_inaccessible"))
        tombstone_mr = bool(inp.get("tombstone_mr_created"))
        silent_delete = bool(inp.get("silent_delete"))
        ok = deleted and tombstone_mr and not silent_delete
        details = {
            "source_deleted": inp.get("source_deleted"),
            "source_inaccessible": inp.get("source_inaccessible"),
            "tombstone_mr_created": tombstone_mr,
            "silent_delete": silent_delete,
        }
        if exp_status == "PASS":
            checks.append(_check(f"source_deletion_tombstone.{name}.tombstone", "source_deletion_tombstone", "PASS" if ok else "FAIL",
                "source deletion creates tombstone/obsolete review MR; silent delete forbidden",
                "tombstone created" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"source_deletion_tombstone.{name}.rejected", "source_deletion_tombstone", "FAIL" if not ok else "PASS",
                f"silent deletion rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "silent deletion detected" if not ok else "tombstone unexpectedly created",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_crash_replay(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        durable = inp.get("durable_evidence", {})
        reconstructed = inp.get("reconstructed_state", {})
        fabricated = bool(inp.get("fabricated_state"))
        seen_match = durable.get("seen") == reconstructed.get("seen")
        proposed_match = durable.get("proposed") == reconstructed.get("proposed")
        merged_match = durable.get("merged") == reconstructed.get("merged")
        ok = seen_match and proposed_match and merged_match and not fabricated
        details = {
            "durable_evidence": durable,
            "reconstructed_state": reconstructed,
            "fabricated_state": fabricated,
        }
        if exp_status == "PASS":
            checks.append(_check(f"crash_replay.{name}.reconstructs", "crash_replay", "PASS" if ok else "FAIL",
                "crash replay reconstructs cursor from durable evidence without fabrication",
                "replay reconstructs" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"crash_replay.{name}.rejected", "crash_replay", "FAIL" if not ok else "PASS",
                f"fabricated or unrecoverable cursor rejected with {exp.get('error', 'INVALID_STATE')}",
                "replay problem detected" if not ok else "replay unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: hc.SchemaValidator) -> list[hc.Check]:
    checks: list[hc.Check] = []
    proposal = {
        "schema_version": "proposal-record-v1",
        "proposal_id": "prop-source-001",
        "proposal_version_id": hc.uuid_str(1),
        "repository_id": "repo-sales",
        "space_id": "sales",
        "target_branch": "main",
        "proposal_sha": "a" * 40,
        "base_sha": "f" * 40,
        "author_stable_id": "connector-1",
        "version_author_stable_id": "connector-1",
        "requester_stable_id": "source-system-1",
        "actor_type": "connector",
        "run_id": "run-source-001",
        "rationale": "Source update proposal.",
        "evidence": [],
        "idempotency_key": "prop-source-001-v1",
        "payload_hash": "1" * 64,
        "created_at": "2026-11-09T12:00:00Z",
    }
    err = schema_validator.validate_or_error("proposal-record.schema.json", proposal)
    checks.append(_check("schema.proposal_record.valid", "schema", "PASS" if err is None else "FAIL",
        "sample source proposal record is schema valid",
        "schema valid" if err is None else err,
        details={"proposal_id": proposal["proposal_id"], "error": err}))

    regex = schema_validator.compile_regexes()
    bad = [r for r in regex if r[2] is not None]
    checks.append(_check("schema.regex_compile", "schema", "FAIL" if bad else "PASS",
        "all schema regex patterns compile",
        f"bad regex: {bad[:3]}" if bad else f"{len(regex)} patterns compiled",
        details={"bad_regex_count": len(bad)}))

    refs = schema_validator.resolve_refs()
    unresolved = [r for r in refs if r[2] is not None]
    checks.append(_check("schema.refs_resolve", "schema", "FAIL" if unresolved else "PASS",
        "all schema $ref resolve",
        f"unresolved: {unresolved[:3]}" if unresolved else f"{len(refs)} refs resolved",
        details={"unresolved_count": len(unresolved)}))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="T15 Safe Source Registry, Three-Way Updates and Durable Cursors")
    parser.add_argument("--dry-run", action="store_true", help="list checks without writing reports")
    args = parser.parse_args()

    if not hc.CONTRACTS_DIR.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t15-source-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.contracts_dir", "harness", "BLOCKED", "contracts directory present", f"missing {hc.CONTRACTS_DIR}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="source-results.json", title="T15 Safe Source Registry, Three-Way Updates and Durable Cursors Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t15-source-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(_check(f"harness.schema_load.{name}", "harness", "BLOCKED", "schema loads", f"load error: {exc}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="source-results.json", title="T15 Safe Source Registry, Three-Way Updates and Durable Cursors Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="source-registry-v1",
            schema_version="t15-source-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="source-results.json", title="T15 Safe Source Registry, Three-Way Updates and Durable Cursors Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="source-registry-v1",
        schema_version="t15-source-results-v1",
        command=RERUN_CMD,
        rerun_cmd=RERUN_CMD,
    )
    builder.add(_check("harness.fixture_loaded", "harness", "PASS", "synthetic fixtures load", "scenarios.yaml loaded",
        details={"fixture": hc._fixture_path(fixture_path)}))

    for check in run_schema_checks(schema_validator):
        builder.add(check)

    data = hc.load_yaml(fixture_path)
    scenarios = data.get("scenarios", {})
    for scenario_id, scenario_data in scenarios.items():
        handler = globals().get(f"check_{scenario_id}")
        if handler is None:
            builder.add(_check(f"harness.no_handler.{scenario_id}", scenario_id, "BLOCKED", "scenario handler exists", "no handler implemented"))
            continue
        try:
            fixtures = scenario_data.get("fixtures", [])
            for c in handler(fixtures, fixture_path):
                builder.add(c)
        except Exception as exc:
            builder.add(_check(f"harness.scenario_error.{scenario_id}", scenario_id, "BLOCKED", "scenario executes", str(exc)))

    for sub in ["live_source_connector", "live_gitlab_merge", "live_object_store_cursor"]:
        builder.add(_check(f"runtime.{sub}", "runtime", "BLOCKED", "live integration evidence", "requires live source sandbox and credentials"))

    return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
        raw_filename="source-results.json", title="T15 Safe Source Registry, Three-Way Updates and Durable Cursors Evidence Summary",
        blocked_note=BLOCKED_NOTE)


if __name__ == "__main__":
    sys.exit(main())
