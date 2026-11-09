# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T18 necessary pilot part: pilot hardening and protected deployment harness."""

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

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t18")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t18")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t18/run_t18_tests.py"
BLOCKED_NOTE = (
    "Live pilot environment, protected deployment, real corpus and second-client acceptance remain BLOCKED. "
    "This report contains only synthetic structural evidence; it does not claim production pilot PASS or full T18/G3 readiness."
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


def check_pilot_isolation(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        components = inp.get("components", {})
        required = {
            "repositories_spaces",
            "config_adapters",
            "postgresql_index",
            "object_storage",
            "secrets",
            "backups",
            "egress",
        }
        all_separated = required.issubset(set(components.keys())) and all(
            components.get(k) for k in required
        )
        runtime_ok = bool(inp.get("runtime_migrations_disabled")) and bool(
            inp.get("runtime_non_ddl_role")
        )
        migrator_ok = bool(inp.get("migrators_only_rehearsed_upgrades"))
        ok = all_separated and runtime_ok and migrator_ok
        details = {
            "all_components_separated": all_separated,
            "runtime_migrations_disabled": bool(inp.get("runtime_migrations_disabled")),
            "runtime_non_ddl_role": bool(inp.get("runtime_non_ddl_role")),
            "migrators_only_rehearsed_upgrades": migrator_ok,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"pilot_isolation.{name}.isolated",
                    "pilot_isolation",
                    "PASS" if ok else "FAIL",
                    "pilot environment isolates Spaces, config, PostgreSQL/index, object storage, secrets, backups and egress; runtime is non-DDL; migrators only rehearsed upgrades",
                    "pilot isolation valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"pilot_isolation.{name}.rejected",
                    "pilot_isolation",
                    "FAIL" if not ok else "PASS",
                    f"insufficient isolation rejected with {exp.get('error', 'INVALID_STATE')}",
                    "isolation problem detected" if not ok else "isolation unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_credential_egress_separation(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        creds = inp.get("credentials_separated", {})
        required = {"proposal_merge", "connector", "ci_index", "retrieval"}
        separated = required.issubset(set(creds.keys())) and all(
            creds.get(k) for k in required
        )
        egress_closed = bool(inp.get("default_egress_closed"))
        approved_only = bool(inp.get("approved_routes_only"))
        no_branch = not bool(inp.get("client_code_branch"))
        no_prod = not bool(inp.get("production_resource_created_without_authorization"))
        ok = separated and egress_closed and approved_only and no_branch and no_prod
        details = {
            "credentials_separated": separated,
            "default_egress_closed": egress_closed,
            "approved_routes_only": approved_only,
            "no_client_code_branch": no_branch,
            "no_unauthorized_production_resource": no_prod,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"credential_egress_separation.{name}.separated",
                    "credential_egress_separation",
                    "PASS" if ok else "FAIL",
                    "proposal/merge, connector, CI/index and retrieval credentials are separated; default egress closed; approved routes only; no client code branch; no unauthorized production resource",
                    "credential/egress separation valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"credential_egress_separation.{name}.rejected",
                    "credential_egress_separation",
                    "FAIL" if not ok else "PASS",
                    f"credential/egress leak rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                    "separation problem detected" if not ok else "separation unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_runbook_rehearsal(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    required = {
        "startup",
        "cutover",
        "merge_recovery_quarantine",
        "export",
        "backup",
        "restore",
        "upgrade",
        "rollback",
    }
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        runbooks = inp.get("runbooks", {})
        all_present = required.issubset(set(runbooks.keys()))
        complete = all(
            bool(rb.get("exact_versions_refs"))
            and bool(rb.get("commands"))
            and bool(rb.get("sanitized_outputs"))
            and bool(rb.get("failure_handling"))
            and bool(rb.get("blocked_items_recorded"))
            and bool(rb.get("independently_reviewed"))
            for rb in runbooks.values()
        )
        ok = all_present and complete
        details = {
            "all_runbooks_present": all_present,
            "all_runbooks_complete": complete,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"runbook_rehearsal.{name}.complete",
                    "runbook_rehearsal",
                    "PASS" if ok else "FAIL",
                    "startup/cutover/recovery/export/backup/restore/upgrade/rollback runbooks rehearsed with versions/refs, commands, sanitized outputs, failure handling, BLOCKED items and independent review",
                    "runbooks complete" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"runbook_rehearsal.{name}.rejected",
                    "runbook_rehearsal",
                    "FAIL" if not ok else "PASS",
                    f"incomplete runbook rejected with {exp.get('error', 'INVALID_STATE')}",
                    "runbook problem detected" if not ok else "runbooks unexpectedly complete",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_backup_restore_drill(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        closure = bool(inp.get("decisions_assets_authorization_closure"))
        authz = bool(inp.get("kb_authz_rebuilt"))
        freeze = bool(inp.get("kb_ops_global_merge_freeze"))
        barriers = bool(inp.get("per_target_barriers"))
        new_snapshot = bool(inp.get("kb_index_new_validated_snapshot"))
        before_activation = bool(inp.get("activation_after_snapshot_pointer"))
        ok = closure and authz and freeze and barriers and new_snapshot and before_activation
        details = {
            "closure_validated": closure,
            "kb_authz_rebuilt": authz,
            "kb_ops_global_merge_freeze": freeze,
            "per_target_barriers": barriers,
            "kb_index_new_validated_snapshot": new_snapshot,
            "activation_after_snapshot_pointer": before_activation,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"backup_restore_drill.{name}.valid",
                    "backup_restore_drill",
                    "PASS" if ok else "FAIL",
                    "backup/restore drill validates closure, rebuilds kb_authz, starts kb_ops under global freeze with barriers, and points kb_index to new validated snapshot before activation",
                    "backup/restore drill valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"backup_restore_drill.{name}.rejected",
                    "backup_restore_drill",
                    "FAIL" if not ok else "PASS",
                    f"invalid restore drill rejected with {exp.get('error', 'INVALID_STATE')}",
                    "restore drill problem detected" if not ok else "drill unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_security_regression(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        denials = inp.get("non_privileged_write_denials", {})
        required_identities = {
            "business",
            "engineering",
            "bot",
            "connector",
            "ci",
            "source_managed",
        }
        denials_ok = required_identities.issubset(set(denials.keys())) and all(
            denials.get(k, {}).get("direct_push") is True
            and denials.get(k, {}).get("direct_merge") is True
            and denials.get(k, {}).get("auto_merge") is True
            for k in required_identities
        )
        schema_iso = bool(inp.get("component_schema_isolation"))
        ddl_denied = bool(inp.get("runtime_ddl_denied"))
        cross_client_denied = bool(inp.get("cross_client_resource_access_denied"))
        canary_clean = bool(inp.get("secret_redaction_canary_clean"))
        ok = denials_ok and schema_iso and ddl_denied and cross_client_denied and canary_clean
        details = {
            "non_privileged_denials_complete": denials_ok,
            "component_schema_isolation": schema_iso,
            "runtime_ddl_denied": ddl_denied,
            "cross_client_access_denied": cross_client_denied,
            "secret_canary_clean": canary_clean,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"security_regression.{name}.hardened",
                    "security_regression",
                    "PASS" if ok else "FAIL",
                    "direct push/merge/auto-merge denied for non-privileged identities; component schema isolation; runtime DDL and cross-client access denied; secret canaries clean",
                    "security/regression valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"security_regression.{name}.rejected",
                    "security_regression",
                    "FAIL" if not ok else "PASS",
                    f"bypass or disclosure rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                    "security/regression problem detected" if not ok else "security unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_privileged_bypass_governance(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        attempted = bool(inp.get("owner_bypass_attempted"))
        detected = bool(inp.get("detected"))
        quarantined = bool(inp.get("quarantined"))
        runbook = bool(inp.get("g0_d3_runbook_invoked"))
        not_managed = not bool(inp.get("treated_as_managed_path"))
        ok = attempted and detected and quarantined and runbook and not_managed
        details = {
            "owner_bypass_attempted": attempted,
            "detected": detected,
            "quarantined": quarantined,
            "g0_d3_runbook_invoked": runbook,
            "not_treated_as_managed_path": not_managed,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"privileged_bypass_governance.{name}.governed",
                    "privileged_bypass_governance",
                    "PASS" if ok else "FAIL",
                    "privileged Owner bypass is detected, quarantined and handled via G0-D3 emergency runbook, not as a managed path",
                    "bypass governance valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"privileged_bypass_governance.{name}.rejected",
                    "privileged_bypass_governance",
                    "FAIL" if not ok else "PASS",
                    f"bypass treated as managed path rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                    "bypass governance problem detected" if not ok else "bypass governance unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_business_user_acceptance(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    required_steps = {
        "pending_queue",
        "read_edit",
        "diff_rationale_evidence",
        "accept_reject_cancel",
        "history_restore",
    }
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        users = inp.get("users", [])
        two_independent = len(users) >= 2 and all(
            not bool(u.get("engineering")) for u in users
        )
        steps = set(inp.get("completed_steps", []))
        steps_ok = required_steps.issubset(steps)
        no_git = not bool(inp.get("used_git_cli"))
        canonical = bool(inp.get("canonical_decisions"))
        history = bool(inp.get("history_cursor"))
        revert = bool(inp.get("reviewed_revert_mr"))
        no_self_approval = not bool(inp.get("self_approval"))
        ok = (
            two_independent
            and steps_ok
            and no_git
            and canonical
            and history
            and revert
            and no_self_approval
        )
        details = {
            "two_independent_non_engineering_users": two_independent,
            "all_steps_completed": steps_ok,
            "no_git_cli": no_git,
            "canonical_decisions": canonical,
            "history_cursor": history,
            "reviewed_revert_mr": revert,
            "no_self_approval": no_self_approval,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"business_user_acceptance.{name}.accepted",
                    "business_user_acceptance",
                    "PASS" if ok else "FAIL",
                    "two independent non-engineering users complete the full review/decision/restore scenario without Git/CLI",
                    "business-user acceptance valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"business_user_acceptance.{name}.rejected",
                    "business_user_acceptance",
                    "FAIL" if not ok else "PASS",
                    f"invalid acceptance scenario rejected with {exp.get('error', 'APPROVER_CONFLICT')}",
                    "acceptance problem detected" if not ok else "acceptance unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def run_schema_checks(schema_validator: hc.SchemaValidator) -> list[hc.Check]:
    checks: list[hc.Check] = []
    decision = {
        "schema_version": "decision-record-v1",
        "decision_id": hc.uuid_str(1),
        "proposal_id": "prop-pilot-001",
        "repository_id": "repo-sales",
        "space_id": "sales",
        "target_branch": "main",
        "proposal_sha": "a" * 40,
        "base_sha": "f" * 40,
        "action": "accepted",
        "actor_stable_id": "approver-sales-1",
        "actor_type": "human",
        "timestamp": "2026-11-09T12:00:00Z",
        "rationale": "Pilot acceptance decision.",
        "evidence": [],
        "policy_bundle_id": "sales-policy-bundle",
        "access_policy_revision": "d" * 40,
        "approval_policy_revision": "e" * 40,
        "payload_hash": "1" * 64,
        "record_sha256": "2" * 64,
    }
    err = schema_validator.validate_or_error("decision-record.schema.json", decision)
    checks.append(
        _check(
            "schema.decision_record.valid",
            "schema",
            "PASS" if err is None else "FAIL",
            "sample decision record is schema valid",
            "schema valid" if err is None else err,
            details={"decision_id": decision["decision_id"], "error": err},
        )
    )
    regex = schema_validator.compile_regexes()
    bad = [r for r in regex if r[2] is not None]
    checks.append(
        _check(
            "schema.regex_compile",
            "schema",
            "FAIL" if bad else "PASS",
            "all schema regex patterns compile",
            f"bad regex: {bad[:3]}" if bad else f"{len(regex)} patterns compiled",
            details={"bad_regex_count": len(bad)},
        )
    )
    refs = schema_validator.resolve_refs()
    unresolved = [r for r in refs if r[2] is not None]
    checks.append(
        _check(
            "schema.refs_resolve",
            "schema",
            "FAIL" if unresolved else "PASS",
            "all schema $ref resolve",
            f"unresolved: {unresolved[:3]}" if unresolved else f"{len(refs)} refs resolved",
            details={"unresolved_count": len(unresolved)},
        )
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T18 Necessary Pilot Part: Pilot Hardening and Protected Deployment"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="list checks without writing reports"
    )
    args = parser.parse_args()

    if not hc.CONTRACTS_DIR.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t18-pilot-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(
            _check(
                "harness.contracts_dir",
                "harness",
                "BLOCKED",
                "contracts directory present",
                f"missing {hc.CONTRACTS_DIR}",
            )
        )
        return hc.write_reports(
            builder,
            dry_run=args.dry_run,
            output_dir=OUTPUT_DIR,
            evidence_dir=EVIDENCE_DIR,
            raw_filename="pilot-results.json",
            title="T18 Necessary Pilot Part: Pilot Hardening and Protected Deployment Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t18-pilot-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(
                _check(
                    f"harness.schema_load.{name}",
                    "harness",
                    "BLOCKED",
                    "schema loads",
                    f"load error: {exc}",
                )
            )
        return hc.write_reports(
            builder,
            dry_run=args.dry_run,
            output_dir=OUTPUT_DIR,
            evidence_dir=EVIDENCE_DIR,
            raw_filename="pilot-results.json",
            title="T18 Necessary Pilot Part: Pilot Hardening and Protected Deployment Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="pilot-harness-v1",
            schema_version="t18-pilot-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(
            _check(
                "harness.fixture_missing",
                "harness",
                "BLOCKED",
                "fixture present",
                f"missing {fixture_path}",
            )
        )
        return hc.write_reports(
            builder,
            dry_run=args.dry_run,
            output_dir=OUTPUT_DIR,
            evidence_dir=EVIDENCE_DIR,
            raw_filename="pilot-results.json",
            title="T18 Necessary Pilot Part: Pilot Hardening and Protected Deployment Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="pilot-harness-v1",
        schema_version="t18-pilot-results-v1",
        command=RERUN_CMD,
        rerun_cmd=RERUN_CMD,
    )
    builder.add(
        _check(
            "harness.fixture_loaded",
            "harness",
            "PASS",
            "synthetic fixtures load",
            "scenarios.yaml loaded",
            details={"fixture": hc._fixture_path(fixture_path)},
        )
    )

    for check in run_schema_checks(schema_validator):
        builder.add(check)

    data = hc.load_yaml(fixture_path)
    scenarios = data.get("scenarios", {})
    for scenario_id, scenario_data in scenarios.items():
        handler = globals().get(f"check_{scenario_id}")
        if handler is None:
            builder.add(
                _check(
                    f"harness.no_handler.{scenario_id}",
                    scenario_id,
                    "BLOCKED",
                    "scenario handler exists",
                    "no handler implemented",
                )
            )
            continue
        try:
            fixtures = scenario_data.get("fixtures", [])
            for c in handler(fixtures, fixture_path):
                builder.add(c)
        except Exception as exc:
            builder.add(
                _check(
                    f"harness.scenario_error.{scenario_id}",
                    scenario_id,
                    "BLOCKED",
                    "scenario executes",
                    str(exc),
                )
            )

    for sub in [
        "live_pilot_environment_isolation",
        "live_backup_restore_drill",
        "live_business_user_acceptance",
        "live_runbook_rehearsal",
        "live_second_client_preparation",
    ]:
        builder.add(
            _check(
                f"runtime.{sub}",
                "runtime",
                "BLOCKED",
                "live integration evidence",
                "requires owner-authorized pilot environment, corpus and credentials",
            )
        )

    return hc.write_reports(
        builder,
        dry_run=args.dry_run,
        output_dir=OUTPUT_DIR,
        evidence_dir=EVIDENCE_DIR,
        raw_filename="pilot-results.json",
        title="T18 Necessary Pilot Part: Pilot Hardening and Protected Deployment Evidence Summary",
        blocked_note=BLOCKED_NOTE,
    )


if __name__ == "__main__":
    sys.exit(main())
