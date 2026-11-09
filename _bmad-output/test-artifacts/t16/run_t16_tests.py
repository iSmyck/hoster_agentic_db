# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T16 one owner-selected real source connector harness."""

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

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t16")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t16")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t16/run_t16_tests.py"
BLOCKED_NOTE = (
    "Real source connector integration remains BLOCKED pending owner selection of SharePoint/Bitrix24/Kayako, "
    "real sandbox and credentials. This report contains only synthetic design-readiness evidence; "
    "it does not claim production connector PASS."
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


def check_feasibility_inventory(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        selected = inp.get("selected_connector")
        inventory = inp.get("inventory", {})
        required = ["edition", "api", "authentication", "sandbox", "scopes", "rate_limits"]
        selected_complete = selected and all(bool(inventory.get(k)) for k in required)
        others = inp.get("other_connectors", [])
        others_not_ready = all(not bool(c.get("claimed_ready")) for c in others)
        ok = selected_complete and others_not_ready
        details = {
            "selected_connector": selected,
            "inventory_fields_present": {k: bool(inventory.get(k)) for k in required},
            "others_claimed_ready": [c.get("name") for c in others if c.get("claimed_ready")],
        }
        if exp_status == "PASS":
            checks.append(_check(f"feasibility_inventory.{name}.complete", "feasibility_inventory", "PASS" if ok else "FAIL",
                "selected source inventory complete; other connectors not claimed ready",
                "inventory complete" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"feasibility_inventory.{name}.rejected", "feasibility_inventory", "FAIL" if not ok else "PASS",
                f"incomplete inventory or unselected connector claim rejected with {exp.get('error', 'INVALID_CONFIG')}",
                "inventory problem detected" if not ok else "inventory unexpectedly complete",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_connector_identity_provenance(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        stable_remote = bool(inp.get("stable_remote_id"))
        immutable_version = bool(inp.get("immutable_version_or_hash"))
        source_owner = bool(inp.get("source_owner"))
        provenance = bool(inp.get("provenance"))
        correct_space = bool(inp.get("maps_to_configured_space"))
        ok = stable_remote and immutable_version and source_owner and provenance and correct_space
        details = {
            "stable_remote_id": stable_remote,
            "immutable_version_or_hash": immutable_version,
            "source_owner": source_owner,
            "provenance": provenance,
            "maps_to_configured_space": correct_space,
        }
        if exp_status == "PASS":
            checks.append(_check(f"connector_identity_provenance.{name}.valid", "connector_identity_provenance", "PASS" if ok else "FAIL",
                "connector preserves stable remote ID, immutable version/hash, source owner and provenance; maps to configured Space",
                "identity/provenance valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"connector_identity_provenance.{name}.rejected", "connector_identity_provenance", "FAIL" if not ok else "PASS",
                f"identity/provenance violation rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                "identity/provenance problem detected" if not ok else "identity/provenance unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_connector_capabilities(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    forbidden = {"push", "merge", "auto_merge", "grants", "export", "index_pointer"}
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        capabilities = set(inp.get("capabilities", []))
        proposal_only = bool(inp.get("proposal_only_to_go"))
        ok = proposal_only and not bool(capabilities.intersection(forbidden))
        details = {
            "capabilities": list(capabilities),
            "proposal_only_to_go": proposal_only,
            "forbidden_present": list(capabilities.intersection(forbidden)),
        }
        if exp_status == "PASS":
            checks.append(_check(f"connector_capabilities.{name}.valid", "connector_capabilities", "PASS" if ok else "FAIL",
                "connector sends proposal-only requests to GO and has no forbidden capabilities",
                "capabilities valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"connector_capabilities.{name}.rejected", "connector_capabilities", "FAIL" if not ok else "PASS",
                f"forbidden connector capability rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "forbidden capability detected" if not ok else "capabilities unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_access_revocation(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        revoked_creds = bool(inp.get("credentials_revoked"))
        changed_acl_hint = bool(inp.get("changed_acl_hint"))
        revoked_group = bool(inp.get("revoked_group_membership"))
        failed_closed = bool(inp.get("operation_failed_closed"))
        hint_only = bool(inp.get("access_hint_treated_as_hint_only"))
        ok = (not (revoked_creds or changed_acl_hint or revoked_group) or failed_closed) and hint_only
        details = {
            "credentials_revoked": revoked_creds,
            "changed_acl_hint": changed_acl_hint,
            "revoked_group_membership": revoked_group,
            "failed_closed": failed_closed,
            "hint_only": hint_only,
        }
        if exp_status == "PASS":
            checks.append(_check(f"access_revocation.{name}.fail_closed", "access_revocation", "PASS" if ok else "FAIL",
                "revoked credentials, changed ACL hints or revoked group membership fail closed; hints treated as hints only",
                "revocation handling valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"access_revocation.{name}.rejected", "access_revocation", "FAIL" if not ok else "PASS",
                f"revocation not fail-closed rejected with {exp.get('error', 'AUTHZ_GROUP_STALE')}",
                "revocation handling problem detected" if not ok else "revocation handling unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_deletion_retry_dedupe(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        deletion = bool(inp.get("source_deleted"))
        tombstone = bool(inp.get("tombstone_mr_created"))
        retry_identity = bool(inp.get("bounded_retry_preserves_identity"))
        duplicate = bool(inp.get("duplicate_event"))
        outstanding = inp.get("outstanding_proposal_count", 0)
        poison = bool(inp.get("poison_reached_dead_letter"))
        ok = (not deletion or tombstone) and retry_identity and (not duplicate or outstanding <= 1) and poison
        details = {
            "source_deleted": deletion,
            "tombstone_mr_created": tombstone,
            "bounded_retry_preserves_identity": retry_identity,
            "duplicate_event": duplicate,
            "outstanding_proposal_count": outstanding,
            "poison_reached_dead_letter": poison,
        }
        if exp_status == "PASS":
            checks.append(_check(f"deletion_retry_dedupe.{name}.valid", "deletion_retry_dedupe", "PASS" if ok else "FAIL",
                "deletion produces tombstone, retry preserves identity, duplicates dedupe and poison reaches dead-letter",
                "deletion/retry/dedupe valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"deletion_retry_dedupe.{name}.rejected", "deletion_retry_dedupe", "FAIL" if not ok else "PASS",
                f"deletion/retry/dedupe violation rejected with {exp.get('error', 'INVALID_STATE')}",
                "deletion/retry/dedupe problem detected" if not ok else "deletion/retry/dedupe unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_attachments_object_acl(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        attachments = inp.get("attachments", [])
        all_immutable = all(bool(a.get("immutable")) for a in attachments)
        all_sha256 = all(hc.is_sha256(a.get("sha256")) for a in attachments)
        all_size = all(isinstance(a.get("size"), int) and a.get("size", 0) > 0 for a in attachments)
        all_media = all(bool(a.get("media_type")) for a in attachments)
        all_source_ref = all(bool(a.get("source_ref")) for a in attachments)
        mutable_url = bool(inp.get("mutable_url_used"))
        missing = bool(inp.get("missing_object"))
        acl_fail = bool(inp.get("object_acl_failed"))
        ok = all_immutable and all_sha256 and all_size and all_media and all_source_ref and not mutable_url and not missing and not acl_fail
        details = {
            "attachment_count": len(attachments),
            "all_immutable": all_immutable,
            "all_sha256": all_sha256,
            "all_size": all_size,
            "all_media_type": all_media,
            "all_source_ref": all_source_ref,
            "mutable_url_used": mutable_url,
            "missing_object": missing,
            "object_acl_failed": acl_fail,
        }
        if exp_status == "PASS":
            checks.append(_check(f"attachments_object_acl.{name}.valid", "attachments_object_acl", "PASS" if ok else "FAIL",
                "attachments immutable/versioned with SHA-256, size, media type and source reference; mutable URL/missing/ACL-fail blocked",
                "attachments valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"attachments_object_acl.{name}.rejected", "attachments_object_acl", "FAIL" if not ok else "PASS",
                f"attachment/object problem rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "attachment/object problem detected" if not ok else "attachments unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_secrets_hygiene(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        leak_locations = set(inp.get("secret_leak_locations", []))
        ok = len(leak_locations) == 0
        details = {
            "secret_leak_locations": list(leak_locations),
        }
        if exp_status == "PASS":
            checks.append(_check(f"secrets_hygiene.{name}.clean", "secrets_hygiene", "PASS" if ok else "FAIL",
                "source secrets, raw payloads, signed URLs and tokens do not enter documents/MR evidence/model args/logs/reports",
                "secrets hygiene clean" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"secrets_hygiene.{name}.rejected", "secrets_hygiene", "FAIL" if not ok else "PASS",
                f"secret leak rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "secret leak detected" if not ok else "secrets hygiene unexpectedly clean",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: hc.SchemaValidator) -> list[hc.Check]:
    checks: list[hc.Check] = []
    proposal = {
        "schema_version": "proposal-record-v1",
        "proposal_id": "prop-connector-001",
        "proposal_version_id": hc.uuid_str(2),
        "repository_id": "repo-sales",
        "space_id": "sales",
        "target_branch": "main",
        "proposal_sha": "a" * 40,
        "base_sha": "f" * 40,
        "author_stable_id": "connector-sharepoint",
        "version_author_stable_id": "connector-sharepoint",
        "requester_stable_id": "source-sharepoint",
        "actor_type": "connector",
        "run_id": "run-connector-001",
        "rationale": "Source connector proposal.",
        "evidence": [],
        "idempotency_key": "prop-connector-001-v1",
        "payload_hash": "2" * 64,
        "created_at": "2026-11-09T12:00:00Z",
    }
    err = schema_validator.validate_or_error("proposal-record.schema.json", proposal)
    checks.append(_check("schema.proposal_record.valid", "schema", "PASS" if err is None else "FAIL",
        "sample connector proposal record is schema valid",
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
    parser = argparse.ArgumentParser(description="T16 One Owner-Selected Real Source Connector")
    parser.add_argument("--dry-run", action="store_true", help="list checks without writing reports")
    args = parser.parse_args()

    if not hc.CONTRACTS_DIR.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t16-connector-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.contracts_dir", "harness", "BLOCKED", "contracts directory present", f"missing {hc.CONTRACTS_DIR}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="connector-results.json", title="T16 One Owner-Selected Real Source Connector Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t16-connector-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(_check(f"harness.schema_load.{name}", "harness", "BLOCKED", "schema loads", f"load error: {exc}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="connector-results.json", title="T16 One Owner-Selected Real Source Connector Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="connector-design-v1",
            schema_version="t16-connector-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="connector-results.json", title="T16 One Owner-Selected Real Source Connector Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="connector-design-v1",
        schema_version="t16-connector-results-v1",
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

    for sub in ["live_sharepoint_connector", "live_bitrix_connector", "live_kayako_connector", "live_source_sandbox", "live_object_store_acl"]:
        builder.add(_check(f"runtime.{sub}", "runtime", "BLOCKED", "live integration evidence", "requires owner-selected source, sandbox and credentials"))

    return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
        raw_filename="connector-results.json", title="T16 One Owner-Selected Real Source Connector Evidence Summary",
        blocked_note=BLOCKED_NOTE)


if __name__ == "__main__":
    sys.exit(main())
