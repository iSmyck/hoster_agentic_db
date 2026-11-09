# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T11 approved hoster.ai studio inference lifecycle harness."""

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

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t11")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t11")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t11/run_t11_tests.py"
BLOCKED_NOTE = (
    "Real hoster.ai studio endpoint, model inventory, credentials and egress remain BLOCKED. "
    "This report contains only synthetic structural evidence; it does not claim production inference PASS."
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


def check_route_inventory(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        connection = inp.get("connection", "")
        model = inp.get("model", "")
        version = inp.get("model_version")
        data_profile = inp.get("data_profile", "")
        capabilities = inp.get("capabilities", [])
        dimension = inp.get("dimension")
        index_link = inp.get("index_profile_link", "")
        approved = bool(inp.get("approved_connection", connection.endswith("-approved")))
        has_version = version is not None and str(version) != ""
        has_profile = data_profile in {"strict", "pii_permitted"}
        has_link = bool(index_link)
        has_dim = dimension is not None and isinstance(dimension, int) and dimension > 0
        ok = approved and has_version and has_profile and has_link and has_dim
        details = {
            "route": inp.get("route"),
            "connection": connection,
            "model": model,
            "approved": approved,
            "has_version": has_version,
            "has_data_profile": has_profile,
            "has_index_profile_link": has_link,
            "has_dimension": has_dim,
            "capabilities": capabilities,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"route_inventory.{name}.complete",
                    "route_inventory",
                    "PASS" if ok else "FAIL",
                    "route records approved connection, model/version, data profile, capabilities and index-profile linkage",
                    "route inventory complete" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"route_inventory.{name}.rejected",
                    "route_inventory",
                    "FAIL" if not ok else "PASS",
                    f"incomplete or unapproved route rejected with {exp.get('error', 'INVALID_CONFIG')}",
                    "route inventory problem detected" if not ok else "route unexpectedly complete",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_streaming_tool_calls(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        request_id = inp.get("request_id")
        run_id = inp.get("run_id")
        chunks = inp.get("chunks", [])
        authorized = bool(inp.get("authorized", True))
        assembled_valid = bool(inp.get("assembled_args_valid"))
        executed_partial = bool(inp.get("executed_partial_content"))
        has_request_id = bool(request_id)
        has_run_id = bool(run_id)
        all_citations = all(bool(c.get("citation_refs")) for c in chunks)
        all_correlated = len({c.get("tool_call_id") for c in chunks}) >= 1
        ok = (
            has_request_id
            and has_run_id
            and all_correlated
            and all_citations
            and authorized
            and assembled_valid
            and not executed_partial
        )
        details = {
            "has_request_id": has_request_id,
            "has_run_id": has_run_id,
            "all_correlated": all_correlated,
            "all_citations": all_citations,
            "authorized": authorized,
            "assembled_args_valid": assembled_valid,
            "executed_partial_content": executed_partial,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"streaming_tool_calls.{name}.safe",
                    "streaming_tool_calls",
                    "PASS" if ok else "FAIL",
                    "streaming tool calls preserve correlation/citations, assemble typed args and validate authz before dispatch",
                    "streaming/tool-call handling valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"streaming_tool_calls.{name}.rejected",
                    "streaming_tool_calls",
                    "FAIL" if not ok else "PASS",
                    f"unsafe streaming/tool-call handling rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                    "streaming/tool-call problem detected" if not ok else "handling unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_malformed_unsafe_inputs(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        unsafe = (
            bool(inp.get("attempted_shell"))
            or bool(inp.get("attempted_sql"))
            or bool(inp.get("attempted_merge"))
            or bool(inp.get("attempted_privilege"))
        )
        malformed = inp.get("payload_type") in {
            "malformed_json",
            "unknown_fields",
            "oversized",
            "prompt_injection",
        }
        rejected = bool(inp.get("rejected", malformed or unsafe))
        ok = malformed and rejected and not unsafe
        details = {
            "payload_type": inp.get("payload_type"),
            "malformed_or_injection": malformed,
            "rejected": rejected,
            "unsafe_side_effects": unsafe,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"malformed_unsafe_inputs.{name}.safe",
                    "malformed_unsafe_inputs",
                    "PASS" if ok else "FAIL",
                    "malformed/unsafe input fails safely without shell/SQL/arbitrary execution or privilege expansion",
                    "input handled safely" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"malformed_unsafe_inputs.{name}.rejected",
                    "malformed_unsafe_inputs",
                    "FAIL" if not ok else "PASS",
                    f"unsafe input rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                    "unsafe input detected" if not ok else "input unexpectedly safe",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_retry_cancel_disconnect(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        event = inp.get("event")
        observable = bool(inp.get("observable"))
        same_key = bool(inp.get("same_idempotency_key", True))
        same_payload = bool(inp.get("same_payload_hash", True))
        stream_closed = bool(inp.get("stream_closed", True))
        retry_counted = bool(inp.get("retry_counted", True))
        if event == "retry":
            ok = observable and same_key and same_payload and retry_counted
        elif event in {"cancel", "disconnect"}:
            ok = observable and stream_closed
        elif event in {"4xx", "5xx"}:
            ok = observable and retry_counted
        else:
            ok = observable
        details = {
            "event": event,
            "observable": observable,
            "same_idempotency_key": same_key,
            "same_payload_hash": same_payload,
            "stream_closed": stream_closed,
            "retry_counted": retry_counted,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"retry_cancel_disconnect.{name}.observable",
                    "retry_cancel_disconnect",
                    "PASS" if ok else "FAIL",
                    "retry/cancel/disconnect/4xx/5xx behavior is observable and preserves idempotency/payload",
                    "event handling observable" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"retry_cancel_disconnect.{name}.rejected",
                    "retry_cancel_disconnect",
                    "FAIL" if not ok else "PASS",
                    f"broken idempotency or unobservable event rejected with {exp.get('error', 'INVALID_STATE')}",
                    "retry/event problem detected" if not ok else "event handling unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_egress_perimeter(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        approved = bool(inp.get("approved"))
        pii = bool(inp.get("pii_permitted"))
        leaves = bool(inp.get("leaves_perimeter"))
        revocation_closes = bool(inp.get("revocation_closes_stream"))
        offline_preapproved = bool(inp.get("offline_asset_preapproved"))
        ok = approved and not (pii and leaves) and revocation_closes and offline_preapproved
        details = {
            "approved_endpoint": approved,
            "pii_permitted": pii,
            "leaves_perimeter": leaves,
            "revocation_closes_stream": revocation_closes,
            "offline_asset_preapproved": offline_preapproved,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"egress_perimeter.{name}.contained",
                    "egress_perimeter",
                    "PASS" if ok else "FAIL",
                    "egress limited to approved endpoints; PII stays inside perimeter; revocation closes streams; offline assets preapproved",
                    "egress/perimeter valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"egress_perimeter.{name}.rejected",
                    "egress_perimeter",
                    "FAIL" if not ok else "PASS",
                    f"unauthorized egress or leak rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                    "egress/perimeter problem detected" if not ok else "egress unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_lifecycle_metrics(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        ttft = inp.get("ttft_ms")
        full = inp.get("full_response_ms")
        has_latency = isinstance(ttft, (int, float)) and isinstance(full, (int, float))
        has_rates = all(
            isinstance(inp.get(k), (int, float))
            for k in ("retry_rate", "cancel_rate", "malformed_rate")
        )
        route_inventory = bool(inp.get("route_inventory_recorded"))
        fallback = inp.get("fallback_attempts", 0)
        fallback_ok = fallback == 0 or bool(inp.get("fallback_approved"))
        cost_ok = bool(inp.get("cost_attributed_to_run"))
        ok = has_latency and has_rates and route_inventory and fallback_ok and cost_ok
        details = {
            "has_latency": has_latency,
            "has_rates": has_rates,
            "route_inventory_recorded": route_inventory,
            "fallback_attempts": fallback,
            "fallback_approved": bool(inp.get("fallback_approved")),
            "cost_attributed_to_run": cost_ok,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"lifecycle_metrics.{name}.complete",
                    "lifecycle_metrics",
                    "PASS" if ok else "FAIL",
                    "lifecycle metrics report TTFT/full-response latency, rates, route inventory, fallback and cost attribution",
                    "metrics complete" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"lifecycle_metrics.{name}.rejected",
                    "lifecycle_metrics",
                    "FAIL" if not ok else "PASS",
                    f"incomplete or hidden-fallback metrics rejected with {exp.get('error', 'INVALID_STATE')}",
                    "metrics problem detected" if not ok else "metrics unexpectedly complete",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def run_schema_checks(schema_validator: hc.SchemaValidator) -> list[hc.Check]:
    checks: list[hc.Check] = []
    proposal = {
        "schema_version": "proposal-record-v1",
        "proposal_id": "prop-inference-001",
        "proposal_version_id": hc.uuid_str(1),
        "repository_id": "repo-sales",
        "space_id": "sales",
        "target_branch": "main",
        "proposal_sha": "a" * 40,
        "base_sha": "f" * 40,
        "author_stable_id": "agent-1",
        "version_author_stable_id": "agent-1",
        "requester_stable_id": "user-sales-1",
        "actor_type": "agent",
        "run_id": "run-2026-001",
        "rationale": "Approved inference test.",
        "evidence": [],
        "idempotency_key": "prop-inference-001-v1",
        "payload_hash": "1" * 64,
        "created_at": "2026-11-09T12:00:00Z",
    }
    err = schema_validator.validate_or_error("proposal-record.schema.json", proposal)
    checks.append(
        _check(
            "schema.proposal_record.valid",
            "schema",
            "PASS" if err is None else "FAIL",
            "sample proposal record is schema valid",
            "schema valid" if err is None else err,
            details={"proposal_id": proposal["proposal_id"], "error": err},
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
        description="T11 Approved hoster.ai Studio Inference Lifecycle"
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
            schema_version="t11-inference-results-v1",
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
            raw_filename="inference-results.json",
            title="T11 Approved hoster.ai Studio Inference Lifecycle Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t11-inference-results-v1",
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
            raw_filename="inference-results.json",
            title="T11 Approved hoster.ai Studio Inference Lifecycle Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="hoster-inference-lifecycle-v1",
            schema_version="t11-inference-results-v1",
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
            raw_filename="inference-results.json",
            title="T11 Approved hoster.ai Studio Inference Lifecycle Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="hoster-inference-lifecycle-v1",
        schema_version="t11-inference-results-v1",
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
        "live_hoster_chat_inference",
        "live_hoster_embeddings_inference",
        "live_hoster_vision_inference",
        "live_streaming_tool_call",
        "live_revocation_closes_stream",
    ]:
        builder.add(
            _check(
                f"runtime.{sub}",
                "runtime",
                "BLOCKED",
                "live integration evidence",
                "requires live hoster.ai sandbox and credentials",
            )
        )

    return hc.write_reports(
        builder,
        dry_run=args.dry_run,
        output_dir=OUTPUT_DIR,
        evidence_dir=EVIDENCE_DIR,
        raw_filename="inference-results.json",
        title="T11 Approved hoster.ai Studio Inference Lifecycle Evidence Summary",
        blocked_note=BLOCKED_NOTE,
    )


if __name__ == "__main__":
    sys.exit(main())
