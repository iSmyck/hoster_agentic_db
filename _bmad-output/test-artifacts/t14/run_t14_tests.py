# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T14 reproducible quality, safety and operational evaluation harness."""

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

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t14")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t14")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t14/run_t14_tests.py"
BLOCKED_NOTE = (
    "Real hoster.ai inference and owner-reviewed expert Russian golden set remain BLOCKED. "
    "This report contains only synthetic structural evidence; it does not claim production evaluation PASS."
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


def check_eval_case_versioning(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        corpus_sha = inp.get("corpus_snapshot_sha")
        code_v = inp.get("code_version")
        config_v = inp.get("config_version")
        model_v = inp.get("model_version")
        tool_v = inp.get("tool_schema_version")
        dataset_v = inp.get("dataset_version")
        scope = inp.get("scope")
        expected_evidence = inp.get("expected_evidence")
        grader = inp.get("grader_config_approved")
        barrier = inp.get("same_data_barrier_as_production")
        ok = (
            hc.is_git_sha(corpus_sha)
            and bool(code_v)
            and bool(config_v)
            and bool(model_v)
            and bool(tool_v)
            and bool(dataset_v)
            and bool(scope)
            and bool(expected_evidence)
            and bool(grader)
            and bool(barrier)
        )
        details = {
            "corpus_sha_valid": hc.is_git_sha(corpus_sha),
            "code_version": code_v,
            "config_version": config_v,
            "model_version": model_v,
            "tool_schema_version": tool_v,
            "dataset_version": dataset_v,
            "scope": scope,
            "expected_evidence": expected_evidence,
            "grader_config_approved": grader,
            "same_data_barrier": barrier,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"eval_case_versioning.{name}.complete",
                    "eval_case_versioning",
                    "PASS" if ok else "FAIL",
                    "eval case records corpus/code/config/model/tool-schema/dataset versions, scope and expected evidence with approved local grader and production data barrier",
                    "versioning complete" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"eval_case_versioning.{name}.rejected",
                    "eval_case_versioning",
                    "FAIL" if not ok else "PASS",
                    f"incomplete eval case rejected with {exp.get('error', 'INVALID_STATE')}",
                    "versioning problem detected" if not ok else "versioning unexpectedly complete",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_quality_metrics(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    required_categories = {
        "page_read",
        "section_read",
        "long_heading",
        "repeated_heading",
        "stale",
        "private",
        "conflict",
    }
    required_metrics = {
        "exact_recall",
        "semantic_recall",
        "factual_support",
        "citation_correctness",
        "abstention_no_answer",
    }
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        metrics = inp.get("metrics", {})
        categories = set(metrics.keys())
        has_all_categories = required_categories.issubset(categories)
        separated = all(
            required_metrics.issubset(set(metrics.get(cat, {}).keys()))
            for cat in categories
        )
        undifferentiated = bool(inp.get("undifferentiated_score"))
        ok = has_all_categories and separated and not undifferentiated
        details = {
            "required_categories_present": has_all_categories,
            "metrics_separated_by_category": separated,
            "undifferentiated_score": undifferentiated,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"quality_metrics.{name}.complete",
                    "quality_metrics",
                    "PASS" if ok else "FAIL",
                    "quality metrics cover exact/semantic recall, factual support, citation correctness and abstention/no-answer per category",
                    "quality metrics valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"quality_metrics.{name}.rejected",
                    "quality_metrics",
                    "FAIL" if not ok else "PASS",
                    f"incomplete or undifferentiated metrics rejected with {exp.get('error', 'INVALID_STATE')}",
                    "quality metrics problem detected" if not ok else "metrics unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_citation_groundedness(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        citations = inp.get("citations", [])
        evidence = inp.get("canonical_evidence", {})
        unsupported = bool(inp.get("unsupported_answer"))
        silent_stale = bool(inp.get("silent_stale_substitution"))
        threshold_recorded = bool(inp.get("threshold_recorded"))
        llm_judge_sole = bool(inp.get("llm_judge_sole_arbiter"))
        citation_ok = all(
            evidence.get(c.get("revision_sha")) == c.get("section") for c in citations
        )
        ok = (
            citation_ok
            and not unsupported
            and not silent_stale
            and threshold_recorded
            and not llm_judge_sole
        )
        details = {
            "citations_match_evidence": citation_ok,
            "unsupported_answer": unsupported,
            "silent_stale_substitution": silent_stale,
            "threshold_recorded": threshold_recorded,
            "llm_judge_sole_arbiter": llm_judge_sole,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"citation_groundedness.{name}.grounded",
                    "citation_groundedness",
                    "PASS" if ok else "FAIL",
                    "citations checked against canonical evidence; unsupported/stale answers fail visibly; thresholds recorded; LLM judge not sole arbiter",
                    "groundedness valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"citation_groundedness.{name}.rejected",
                    "citation_groundedness",
                    "FAIL" if not ok else "PASS",
                    f"ungrounded answer rejected with {exp.get('error', 'CITATION_MISMATCH')}",
                    "groundedness problem detected" if not ok else "groundedness unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_deterministic_adversarial(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        suite = inp.get("suite_type")
        deterministic = bool(inp.get("deterministic_result"))
        zero_disclosure = bool(inp.get("zero_unauthorized_disclosure"))
        probabilistic_only = bool(inp.get("probabilistic_score_only"))
        ok = deterministic and zero_disclosure and not probabilistic_only
        details = {
            "suite_type": suite,
            "deterministic_result": deterministic,
            "zero_unauthorized_disclosure": zero_disclosure,
            "probabilistic_score_only": probabilistic_only,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"deterministic_adversarial.{name}.safe",
                    "deterministic_adversarial",
                    "PASS" if ok else "FAIL",
                    "adversarial/regression suite is deterministic and requires zero unauthorized disclosures",
                    "deterministic adversarial valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"deterministic_adversarial.{name}.rejected",
                    "deterministic_adversarial",
                    "FAIL" if not ok else "PASS",
                    f"non-deterministic or disclosing suite rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                    "adversarial suite problem detected" if not ok else "suite unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_operational_measurements(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    required = {
        "ttft_ms",
        "full_response_ms",
        "git_read_latency_ms",
        "git_merge_latency_ms",
        "merge_to_index_freshness_s",
        "ci_queue_lag_s",
    }
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        metrics = inp.get("metrics", {})
        has_required = required.issubset(set(metrics.keys()))
        outcomes = inp.get("outcomes", {})
        has_outcomes = all(
            k in outcomes for k in ("retrieval", "patch", "conflict", "restore")
        )
        cost = bool(inp.get("cost_drivers"))
        ok = has_required and has_outcomes and cost
        details = {
            "required_latency_metrics_present": has_required,
            "outcomes_present": has_outcomes,
            "cost_drivers_present": cost,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"operational_measurements.{name}.complete",
                    "operational_measurements",
                    "PASS" if ok else "FAIL",
                    "operational metrics separate TTFT/full response, Git read/merge latency, merge→index freshness, CI queue lag with outcomes and cost drivers",
                    "operational metrics valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"operational_measurements.{name}.rejected",
                    "operational_measurements",
                    "FAIL" if not ok else "PASS",
                    f"incomplete operational metrics rejected with {exp.get('error', 'INVALID_STATE')}",
                    "operational metrics problem detected" if not ok else "metrics unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_observability(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    required = {
        "tree_read_latency_errors",
        "truncation_cursor_continuation",
        "durable_draft_proposal_outcomes",
        "review_sha_mismatch_conflict_rates",
        "preview_reliability",
        "ui_retry_idempotency_correlation",
    }
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        telemetry = set(inp.get("telemetry", []))
        correlated = bool(inp.get("request_run_proposal_correlation"))
        ok = required.issubset(telemetry) and correlated
        details = {
            "required_telemetry_present": required.issubset(telemetry),
            "correlation_present": correlated,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"observability.{name}.complete",
                    "observability",
                    "PASS" if ok else "FAIL",
                    "observability covers required dimensions with request/run/proposal correlation",
                    "observability valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"observability.{name}.rejected",
                    "observability",
                    "FAIL" if not ok else "PASS",
                    f"incomplete observability rejected with {exp.get('error', 'INVALID_STATE')}",
                    "observability problem detected" if not ok else "observability unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_russian_golden_set(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        cases = inp.get("cases", [])
        has_russian = any("а" <= c.get("question", "")[0:1].lower() <= "я" or c.get("language") == "ru" for c in cases)
        golden_complete = all(bool(c.get("golden_answer")) for c in cases)
        local_grader = bool(inp.get("local_grader"))
        no_live_claim = not bool(inp.get("claims_live_inference_pass"))
        ok = has_russian and golden_complete and local_grader and no_live_claim
        details = {
            "has_russian_cases": has_russian,
            "golden_answers_complete": golden_complete,
            "local_grader": local_grader,
            "no_live_inference_claim": no_live_claim,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"russian_golden_set.{name}.ready",
                    "russian_golden_set",
                    "PASS" if ok else "FAIL",
                    "Russian golden set has complete golden answers, local grader and does not claim live inference PASS",
                    "golden set structure valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"russian_golden_set.{name}.rejected",
                    "russian_golden_set",
                    "FAIL" if not ok else "PASS",
                    f"invalid golden set rejected with {exp.get('error', 'INVALID_STATE')}",
                    "golden set problem detected" if not ok else "golden set unexpectedly valid",
                    fixture=fixture_path,
                    details=details,
                    expected_negative=expected_negative,
                )
            )
    return checks


def check_human_in_the_loop(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        human = bool(inp.get("human_disposition_recorded"))
        automated_only = bool(inp.get("automated_only_disposition"))
        ok = human and not automated_only
        details = {
            "human_disposition_recorded": human,
            "automated_only_disposition": automated_only,
        }
        if exp_status == "PASS":
            checks.append(
                _check(
                    f"human_in_the_loop.{name}.reviewed",
                    "human_in_the_loop",
                    "PASS" if ok else "FAIL",
                    "refusal/groundedness disposition requires human-in-the-loop review",
                    "human-in-the-loop valid" if ok else f"details={details}",
                    fixture=fixture_path,
                    details=details,
                )
            )
        else:
            checks.append(
                _check(
                    f"human_in_the_loop.{name}.rejected",
                    "human_in_the_loop",
                    "FAIL" if not ok else "PASS",
                    f"automated-only disposition rejected with {exp.get('error', 'APPROVER_CONFLICT')}",
                    "human review missing" if not ok else "human review unexpectedly present",
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
        "proposal_id": "prop-eval-001",
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
        "rationale": "Evaluation harness proposal.",
        "evidence": [],
        "idempotency_key": "prop-eval-001-v1",
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
        description="T14 Reproducible Quality, Safety and Operational Evaluation"
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
            schema_version="t14-eval-results-v1",
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
            raw_filename="eval-results.json",
            title="T14 Reproducible Quality, Safety and Operational Evaluation Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t14-eval-results-v1",
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
            raw_filename="eval-results.json",
            title="T14 Reproducible Quality, Safety and Operational Evaluation Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="eval-harness-v1",
            schema_version="t14-eval-results-v1",
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
            raw_filename="eval-results.json",
            title="T14 Reproducible Quality, Safety and Operational Evaluation Evidence Summary",
            blocked_note=BLOCKED_NOTE,
        )

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="eval-harness-v1",
        schema_version="t14-eval-results-v1",
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
        "live_hoster_quality_inference",
        "live_russian_golden_set_grading",
        "live_human_expert_review",
        "live_operational_measurement_collection",
    ]:
        builder.add(
            _check(
                f"runtime.{sub}",
                "runtime",
                "BLOCKED",
                "live integration evidence",
                "requires live hoster.ai sandbox, model outputs and credentials",
            )
        )

    return hc.write_reports(
        builder,
        dry_run=args.dry_run,
        output_dir=OUTPUT_DIR,
        evidence_dir=EVIDENCE_DIR,
        raw_filename="eval-results.json",
        title="T14 Reproducible Quality, Safety and Operational Evaluation Evidence Summary",
        blocked_note=BLOCKED_NOTE,
    )


if __name__ == "__main__":
    sys.exit(main())
