# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T18b full G3 backup/restore/upgrade and full operational acceptance harness."""

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

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t18b")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t18b")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t18b/run_t18b_tests.py"
BLOCKED_NOTE = (
    "Full T18/G3 acceptance remains BLOCKED until E08.4 second-client deployment, E08.2 real connector evidence, "
    "completed runbooks and independent owner review exist. This report contains only synthetic structural evidence."
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


def check_clean_restore(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        refs = bool(inp.get("refs_validated"))
        metadata = bool(inp.get("mr_note_audit_metadata_validated"))
        decisions = bool(inp.get("decisions_validated"))
        assets = bool(inp.get("assets_closure_validated"))
        hashes = bool(inp.get("hashes_verified"))
        authz_rebuilt = bool(inp.get("kb_authz_rebuilt"))
        ops_freeze = bool(inp.get("kb_ops_global_merge_freeze"))
        ops_barriers = bool(inp.get("kb_ops_per_target_barriers"))
        index_snapshot = bool(inp.get("kb_index_new_validated_snapshot"))
        activation_before = bool(inp.get("activation_before_validation"))
        ok = refs and metadata and decisions and assets and hashes and authz_rebuilt and ops_freeze and ops_barriers and index_snapshot and not activation_before
        details = {
            "refs_validated": refs,
            "mr_note_audit_metadata_validated": metadata,
            "decisions_validated": decisions,
            "assets_closure_validated": assets,
            "hashes_verified": hashes,
            "kb_authz_rebuilt": authz_rebuilt,
            "kb_ops_global_merge_freeze": ops_freeze,
            "kb_ops_per_target_barriers": ops_barriers,
            "kb_index_new_validated_snapshot": index_snapshot,
            "activation_before_validation": activation_before,
        }
        if exp_status == "PASS":
            checks.append(_check(f"clean_restore.{name}.valid", "clean_restore", "PASS" if ok else "FAIL",
                "clean restore validates refs/metadata/decisions/assets/hashes, rebuilds kb_authz, kb_ops under freeze, kb_index snapshot before activation",
                "clean restore valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"clean_restore.{name}.rejected", "clean_restore", "FAIL" if not ok else "PASS",
                f"invalid restore rejected with {exp.get('error', 'INVALID_STATE')}",
                "clean restore problem detected" if not ok else "clean restore unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_correction_backup(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        backup = inp.get("backup", {})
        recon = inp.get("reconciliation", {})
        hash_ok = hc.is_sha256(backup.get("current_projection_hash"))
        sequence_ok = bool(backup.get("event_sequence_valid"))
        perimeter_ok = bool(backup.get("perimeter_check_passed"))
        mr_ok = bool(recon.get("linked_mr_verified"))
        no_fabricate = bool(recon.get("no_fabricated_decisions"))
        no_delete = bool(recon.get("no_deleted_canonical_writes"))
        no_resolve = bool(recon.get("no_resolved_or_cancelled_tasks"))
        no_second_path = bool(recon.get("no_second_canonical_write_path"))
        ok = hash_ok and sequence_ok and perimeter_ok and mr_ok and no_fabricate and no_delete and no_resolve and no_second_path
        details = {
            "projection_hash_valid": hash_ok,
            "event_sequence_valid": sequence_ok,
            "perimeter_check_passed": perimeter_ok,
            "linked_mr_verified": mr_ok,
            "no_fabricated_decisions": no_fabricate,
            "no_deleted_canonical_writes": no_delete,
            "no_resolved_or_cancelled_tasks": no_resolve,
            "no_second_canonical_write_path": no_second_path,
        }
        if exp_status == "PASS":
            checks.append(_check(f"correction_backup.{name}.valid", "correction_backup", "PASS" if ok else "FAIL",
                "correction backup validates hashes/event-sequence/perimeter and reconciles without fabricating/deleting/resolving tasks or creating second write path",
                "correction backup valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"correction_backup.{name}.rejected", "correction_backup", "FAIL" if not ok else "PASS",
                f"invalid correction backup reconciliation rejected with {exp.get('error', 'INVALID_STATE')}",
                "correction backup problem detected" if not ok else "correction backup unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_unknown_merge_quarantine(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        unknown = bool(inp.get("unknown_merge_outcome"))
        quarantined = bool(inp.get("quarantined"))
        auto_cleared = bool(inp.get("auto_cleared_by_terminal_or_ttl"))
        missing_assets = bool(inp.get("missing_assets"))
        incomplete_closure = bool(inp.get("incomplete_closure"))
        missing_correction = bool(inp.get("missing_correction_backup"))
        ready = bool(inp.get("ready_claimed"))
        ok = (not unknown or quarantined) and not auto_cleared and not (ready and (missing_assets or incomplete_closure or missing_correction))
        details = {
            "unknown_merge_outcome": unknown,
            "quarantined": quarantined,
            "auto_cleared_by_terminal_or_ttl": auto_cleared,
            "missing_assets": missing_assets,
            "incomplete_closure": incomplete_closure,
            "missing_correction_backup": missing_correction,
            "ready_claimed": ready,
        }
        if exp_status == "PASS":
            checks.append(_check(f"unknown_merge_quarantine.{name}.valid", "unknown_merge_quarantine", "PASS" if ok else "FAIL",
                "unknown merge outcomes quarantined; missing assets/closure/correction backup blocks READY",
                "quarantine valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"unknown_merge_quarantine.{name}.rejected", "unknown_merge_quarantine", "FAIL" if not ok else "PASS",
                f"optimistic quarantine handling rejected with {exp.get('error', 'INVALID_STATE')}",
                "quarantine problem detected" if not ok else "quarantine unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_metrics_alerts_runbooks(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    required = ["startup", "cutover", "merge_latency", "locks_fencing_recovery", "quarantine", "decision_mismatch", "ci_webhook_head_drift", "revocation", "source_cursors", "export_backup_closure", "source_sync", "ttft_full_response", "restore_upgrade"]
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        coverage = set(inp.get("runbook_coverage", []))
        metrics = set(inp.get("metric_coverage", []))
        alerts = set(inp.get("alert_coverage", []))
        secrets_in_telemetry = bool(inp.get("secrets_in_telemetry"))
        raw_in_telemetry = bool(inp.get("raw_content_in_telemetry"))
        rpo_rto = bool(inp.get("owner_approved_rpo_rto"))
        retention = bool(inp.get("owner_approved_retention"))
        cadence = bool(inp.get("owner_approved_backup_cadence"))
        ok = (
            all(r in coverage for r in required)
            and all(r in metrics for r in required)
            and all(r in alerts for r in ["locks_fencing_recovery", "quarantine", "decision_mismatch", "revocation", "source_cursors"])
            and not secrets_in_telemetry
            and not raw_in_telemetry
            and rpo_rto
            and retention
            and cadence
        )
        details = {
            "missing_runbooks": [r for r in required if r not in coverage],
            "missing_metrics": [r for r in required if r not in metrics],
            "secrets_in_telemetry": secrets_in_telemetry,
            "raw_content_in_telemetry": raw_in_telemetry,
            "owner_approved_rpo_rto": rpo_rto,
            "owner_approved_retention": retention,
            "owner_approved_backup_cadence": cadence,
        }
        if exp_status == "PASS":
            checks.append(_check(f"metrics_alerts_runbooks.{name}.valid", "metrics_alerts_runbooks", "PASS" if ok else "FAIL",
                "runbooks/metrics/alerts cover required areas; telemetry redacted; owner-approved RPO/RTO/retention/cadence recorded",
                "metrics/alerts/runbooks valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"metrics_alerts_runbooks.{name}.rejected", "metrics_alerts_runbooks", "FAIL" if not ok else "PASS",
                f"missing coverage or telemetry leak rejected with {exp.get('error', 'INVALID_STATE')}",
                "metrics/alerts/runbooks problem detected" if not ok else "metrics/alerts/runbooks unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_upgrade_rollback(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        pins = bool(inp.get("dependency_pins_checked"))
        sbom = bool(inp.get("sbom_license_diff_reviewed"))
        branding = bool(inp.get("branding_notices_preserved"))
        migration_order = bool(inp.get("external_migration_order_verified"))
        cold_start = bool(inp.get("cold_offline_startup_rehearsed"))
        seams = bool(inp.get("registered_seams_exercised"))
        failure_blocks = bool(inp.get("failure_blocks_upgrade"))
        rollback = bool(inp.get("rollback_path_preserved"))
        ok = pins and sbom and branding and migration_order and cold_start and seams and failure_blocks and rollback
        details = {
            "dependency_pins_checked": pins,
            "sbom_license_diff_reviewed": sbom,
            "branding_notices_preserved": branding,
            "external_migration_order_verified": migration_order,
            "cold_offline_startup_rehearsed": cold_start,
            "registered_seams_exercised": seams,
            "failure_blocks_upgrade": failure_blocks,
            "rollback_path_preserved": rollback,
        }
        if exp_status == "PASS":
            checks.append(_check(f"upgrade_rollback.{name}.valid", "upgrade_rollback", "PASS" if ok else "FAIL",
                "upgrade/rollback rehearsal checks pins, SBOM/license, branding, migration order, cold startup, seams and blocks upgrade on failure",
                "upgrade/rollback valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"upgrade_rollback.{name}.rejected", "upgrade_rollback", "FAIL" if not ok else "PASS",
                f"incomplete upgrade/rollback rehearsal rejected with {exp.get('error', 'INVALID_STATE')}",
                "upgrade/rollback problem detected" if not ok else "upgrade/rollback unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_cross_client_negative(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        read_attempt = bool(inp.get("second_client_reads_first_client"))
        write_attempt = bool(inp.get("second_client_writes_first_client"))
        blocked = bool(inp.get("blocked"))
        ok = (not read_attempt or blocked) and (not write_attempt or blocked)
        details = {
            "second_client_reads_first_client": read_attempt,
            "second_client_writes_first_client": write_attempt,
            "blocked": blocked,
        }
        if exp_status == "PASS":
            checks.append(_check(f"cross_client_negative.{name}.fail_closed", "cross_client_negative", "PASS" if ok else "FAIL",
                "cross-client negative controls fail closed",
                "cross-client controls valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"cross_client_negative.{name}.rejected", "cross_client_negative", "FAIL" if not ok else "PASS",
                f"cross-client access allowed rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "cross-client access detected" if not ok else "cross-client controls unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_full_g3_acceptance(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        second_client = bool(inp.get("e08_4_second_client_deployed"))
        real_connector = bool(inp.get("e08_2_real_connector_evidence"))
        clean_restore = bool(inp.get("clean_restore_evidence"))
        upgrade_ok = bool(inp.get("upgrade_rehearsal_evidence"))
        independent_review = bool(inp.get("independent_owner_review"))
        auto_merge = bool(inp.get("auto_merge_occurred"))
        human_decision = bool(inp.get("external_source_update_human_decision"))
        go_merge = bool(inp.get("external_source_update_go_merge"))
        ok = second_client and real_connector and clean_restore and upgrade_ok and independent_review and not auto_merge and human_decision and go_merge
        details = {
            "e08_4_second_client_deployed": second_client,
            "e08_2_real_connector_evidence": real_connector,
            "clean_restore_evidence": clean_restore,
            "upgrade_rehearsal_evidence": upgrade_ok,
            "independent_owner_review": independent_review,
            "auto_merge_occurred": auto_merge,
            "external_source_update_human_decision": human_decision,
            "external_source_update_go_merge": go_merge,
        }
        if exp_status == "PASS":
            checks.append(_check(f"full_g3_acceptance.{name}.valid", "full_g3_acceptance", "PASS" if ok else "FAIL",
                "full G3 acceptance requires E08.4, E08.2, clean restore, upgrade, independent review and external source update through human decision + GO merge",
                "G3 acceptance criteria valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"full_g3_acceptance.{name}.rejected", "full_g3_acceptance", "FAIL" if not ok else "PASS",
                f"G3 acceptance gap rejected with {exp.get('error', 'INVALID_STATE')}",
                "G3 acceptance gap detected" if not ok else "G3 acceptance unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: hc.SchemaValidator) -> list[hc.Check]:
    checks: list[hc.Check] = []
    task = {
        "schema_version": "docops-correction-task-v1",
        "task_id": hc.uuid_str(3),
        "space_id": "sales",
        "repository_id": "repo-sales",
        "document_id": hc.uuid_str(4),
        "document_revision_sha": "a" * 40,
        "state": "open",
        "requester_stable_id": "stable-user-1",
        "owner": {"kind": "group", "stable_id": "docops-owners"},
        "evidence_sha256": "e" * 64,
        "linked_mr": None,
        "idempotency_key": "idemp-g3-1",
        "payload_hash": "1" * 64,
        "task_version": 1,
        "created_at": "2026-11-09T00:00:00Z",
        "updated_at": "2026-11-09T00:00:00Z",
        "resolved_at": None,
        "cancelled_at": None,
        "resolved_by_stable_id": None,
        "cancelled_by_stable_id": None,
        "resolution_reason": None,
        "cancellation_reason": None,
        "resolution_evidence_sha256": None,
        "cancellation_evidence_sha256": None,
    }
    err = schema_validator.validate_or_error("docops-correction-task.schema.json", task)
    checks.append(_check("schema.correction_task_open.valid", "schema", "PASS" if err is None else "FAIL",
        "sample open correction task is schema valid",
        "schema valid" if err is None else err,
        details={"task_id": task["task_id"], "error": err}))

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
    parser = argparse.ArgumentParser(description="T18b Full G3 Backup/Restore/Upgrade and Full Operational Acceptance")
    parser.add_argument("--dry-run", action="store_true", help="list checks without writing reports")
    args = parser.parse_args()

    if not hc.CONTRACTS_DIR.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t18b-g3-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.contracts_dir", "harness", "BLOCKED", "contracts directory present", f"missing {hc.CONTRACTS_DIR}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="g3-results.json", title="T18b Full G3 Backup/Restore/Upgrade and Full Operational Acceptance Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t18b-g3-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(_check(f"harness.schema_load.{name}", "harness", "BLOCKED", "schema loads", f"load error: {exc}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="g3-results.json", title="T18b Full G3 Backup/Restore/Upgrade and Full Operational Acceptance Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="g3-acceptance-v1",
            schema_version="t18b-g3-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="g3-results.json", title="T18b Full G3 Backup/Restore/Upgrade and Full Operational Acceptance Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="g3-acceptance-v1",
        schema_version="t18b-g3-results-v1",
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

    for sub in ["live_second_client_restore", "live_correction_backup_restore", "live_upgrade_rehearsal", "live_independent_g3_review", "live_external_source_update"]:
        builder.add(_check(f"runtime.{sub}", "runtime", "BLOCKED", "live integration evidence", "requires E08.4 second client, E08.2 real connector and independent owner review"))

    return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
        raw_filename="g3-results.json", title="T18b Full G3 Backup/Restore/Upgrade and Full Operational Acceptance Evidence Summary",
        blocked_note=BLOCKED_NOTE)


if __name__ == "__main__":
    sys.exit(main())
