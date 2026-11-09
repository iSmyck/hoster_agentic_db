# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T18a repeatable config-only dedicated deployment harness."""

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

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t18a")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t18a")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t18a/run_t18a_tests.py"
BLOCKED_NOTE = (
    "Real second-client environment, object store, CI and network perimeter remain BLOCKED pending owner authorization. "
    "This report contains only synthetic config/isolation evidence; it does not claim production dedicated deployment PASS."
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


def check_resource_isolation(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        resources = inp.get("resources", {})
        required = ["repositories", "config", "postgresql", "index", "objects", "secrets", "backups", "mirrors", "network_perimeter", "egress_allowlist"]
        all_separate = all(bool(resources.get(k, {}).get("separate")) for k in required)
        cross_read = bool(inp.get("cross_client_read_attempt"))
        cross_write = bool(inp.get("cross_client_write_attempt"))
        blocked = bool(inp.get("cross_client_blocked"))
        ok = all_separate and not (cross_read and not blocked) and not (cross_write and not blocked)
        details = {
            "resources_separate": {k: bool(resources.get(k, {}).get("separate")) for k in required},
            "cross_client_read_attempt": cross_read,
            "cross_client_write_attempt": cross_write,
            "cross_client_blocked": blocked,
        }
        if exp_status == "PASS":
            checks.append(_check(f"resource_isolation.{name}.valid", "resource_isolation", "PASS" if ok else "FAIL",
                "second client has separate repositories, config, DB, index, objects, secrets, backups, mirrors, perimeter and egress",
                "resource isolation valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"resource_isolation.{name}.rejected", "resource_isolation", "FAIL" if not ok else "PASS",
                f"shared resource or cross-client access rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "resource isolation problem detected" if not ok else "resource isolation unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_config_only_delivery(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        same_core = bool(inp.get("same_pinned_core"))
        client_config = bool(inp.get("client_config_adapters"))
        code_edit = bool(inp.get("code_edit_required"))
        client_branch = bool(inp.get("client_branch_created"))
        ok = same_core and client_config and not code_edit and not client_branch
        details = {
            "same_pinned_core": same_core,
            "client_config_adapters": client_config,
            "code_edit_required": code_edit,
            "client_branch_created": client_branch,
        }
        if exp_status == "PASS":
            checks.append(_check(f"config_only_delivery.{name}.valid", "config_only_delivery", "PASS" if ok else "FAIL",
                "second client deployed from same pinned core plus config/adapters without code edits or client branch",
                "config-only delivery valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"config_only_delivery.{name}.rejected", "config_only_delivery", "FAIL" if not ok else "PASS",
                f"code edit or client branch rejected with {exp.get('error', 'INVALID_CONFIG')}",
                "config-only delivery problem detected" if not ok else "config-only delivery unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_migration_ownership(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        migrations_disabled = bool(inp.get("enable_db_migrations_false"))
        non_ddl_role = bool(inp.get("runtime_non_ddl_role"))
        authorized_migrator = bool(inp.get("authorized_external_migrator"))
        head_verified = bool(inp.get("expected_head_verified_before_traffic"))
        cross_schema = bool(inp.get("cross_schema_write"))
        runtime_ddl = bool(inp.get("runtime_ddl"))
        empty_db_proof = bool(inp.get("empty_db_treated_as_proof"))
        ok = migrations_disabled and non_ddl_role and authorized_migrator and head_verified and not cross_schema and not runtime_ddl and not empty_db_proof
        details = {
            "enable_db_migrations_false": migrations_disabled,
            "runtime_non_ddl_role": non_ddl_role,
            "authorized_external_migrator": authorized_migrator,
            "expected_head_verified_before_traffic": head_verified,
            "cross_schema_write": cross_schema,
            "runtime_ddl": runtime_ddl,
            "empty_db_treated_as_proof": empty_db_proof,
        }
        if exp_status == "PASS":
            checks.append(_check(f"migration_ownership.{name}.valid", "migration_ownership", "PASS" if ok else "FAIL",
                "runtime workers have migrations disabled and non-DDL roles; only authorized migrator verifies heads before traffic",
                "migration ownership valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"migration_ownership.{name}.rejected", "migration_ownership", "FAIL" if not ok else "PASS",
                f"migration ownership violation rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "migration ownership problem detected" if not ok else "migration ownership unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_cold_startup(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        offline_assets = bool(inp.get("offline_assets_ready"))
        sbom_ok = bool(inp.get("sbom_verified"))
        config_ok = bool(inp.get("config_verified"))
        unapproved_download = bool(inp.get("unapproved_download_attempted"))
        fallback = bool(inp.get("unapproved_fallback"))
        ok = offline_assets and sbom_ok and config_ok and not unapproved_download and not fallback
        details = {
            "offline_assets_ready": offline_assets,
            "sbom_verified": sbom_ok,
            "config_verified": config_ok,
            "unapproved_download_attempted": unapproved_download,
            "unapproved_fallback": fallback,
        }
        if exp_status == "PASS":
            checks.append(_check(f"cold_startup.{name}.valid", "cold_startup", "PASS" if ok else "FAIL",
                "cold startup verifies offline assets, SBOM and config; no unapproved download or fallback",
                "cold startup valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"cold_startup.{name}.rejected", "cold_startup", "FAIL" if not ok else "PASS",
                f"unapproved download/fallback rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "cold startup problem detected" if not ok else "cold startup unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
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
        creds = inp.get("credential_separation", {})
        required = ["proposal_merge", "connector", "ci_index", "retrieval"]
        separated = all(bool(creds.get(k, {}).get("separate_identity")) for k in required)
        merge_leaked = bool(creds.get("proposal_merge", {}).get("leaked_to_ui_or_agent"))
        egress_default_deny = bool(inp.get("default_egress_closed"))
        approved_routes = bool(inp.get("approved_egress_routes_only"))
        ok = separated and not merge_leaked and egress_default_deny and approved_routes
        details = {
            "credential_separation": {k: bool(creds.get(k, {}).get("separate_identity")) for k in required},
            "merge_credential_leaked": merge_leaked,
            "default_egress_closed": egress_default_deny,
            "approved_egress_routes_only": approved_routes,
        }
        if exp_status == "PASS":
            checks.append(_check(f"credential_egress_separation.{name}.valid", "credential_egress_separation", "PASS" if ok else "FAIL",
                "proposal/merge, connector, CI/index and retrieval credentials separated; default egress closed except approved routes",
                "credential/egress separation valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"credential_egress_separation.{name}.rejected", "credential_egress_separation", "FAIL" if not ok else "PASS",
                f"credential leak or open egress rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "credential/egress problem detected" if not ok else "credential/egress separation unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_readiness_states(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        state = inp.get("readiness_state", "")
        published = bool(inp.get("published"))
        indexed = bool(inp.get("indexed"))
        unavailable = bool(inp.get("unavailable"))
        masked = bool(inp.get("inactive_preflight_reported_as_published"))
        if state == "published":
            ok = published and not indexed and not unavailable and not masked
        elif state == "indexed":
            ok = indexed and not unavailable and not masked
        elif state == "unavailable":
            ok = unavailable and not published and not indexed and not masked
        else:
            ok = False
        details = {
            "readiness_state": state,
            "published": published,
            "indexed": indexed,
            "unavailable": unavailable,
            "inactive_preflight_reported_as_published": masked,
        }
        if exp_status == "PASS":
            checks.append(_check(f"readiness_states.{name}.valid", "readiness_states", "PASS" if ok else "FAIL",
                "readiness distinguishes published, indexed and unavailable; inactive preflight not masked",
                "readiness states valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"readiness_states.{name}.rejected", "readiness_states", "FAIL" if not ok else "PASS",
                f"readiness state lie rejected with {exp.get('error', 'INVALID_STATE')}",
                "readiness state problem detected" if not ok else "readiness states unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: hc.SchemaValidator) -> list[hc.Check]:
    checks: list[hc.Check] = []
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
    parser = argparse.ArgumentParser(description="T18a Repeatable Config-Only Dedicated Deployment")
    parser.add_argument("--dry-run", action="store_true", help="list checks without writing reports")
    args = parser.parse_args()

    if not hc.CONTRACTS_DIR.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t18a-deployment-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.contracts_dir", "harness", "BLOCKED", "contracts directory present", f"missing {hc.CONTRACTS_DIR}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="deployment-results.json", title="T18a Repeatable Config-Only Dedicated Deployment Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t18a-deployment-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(_check(f"harness.schema_load.{name}", "harness", "BLOCKED", "schema loads", f"load error: {exc}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="deployment-results.json", title="T18a Repeatable Config-Only Dedicated Deployment Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="dedicated-deployment-v1",
            schema_version="t18a-deployment-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="deployment-results.json", title="T18a Repeatable Config-Only Dedicated Deployment Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="dedicated-deployment-v1",
        schema_version="t18a-deployment-results-v1",
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

    for sub in ["live_second_client_environment", "live_object_store", "live_ci_runner", "live_network_perimeter"]:
        builder.add(_check(f"runtime.{sub}", "runtime", "BLOCKED", "live integration evidence", "requires owner-authorized second-client infrastructure"))

    return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
        raw_filename="deployment-results.json", title="T18a Repeatable Config-Only Dedicated Deployment Evidence Summary",
        blocked_note=BLOCKED_NOTE)


if __name__ == "__main__":
    sys.exit(main())
