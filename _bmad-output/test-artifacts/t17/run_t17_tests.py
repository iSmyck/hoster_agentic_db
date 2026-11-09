# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T17 conditional evidence-gated extraction, media and OCR quality harness."""

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

OUTPUT_DIR = Path("_bmad-output/test-artifacts/t17")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t17")
RERUN_CMD = "uv run python _bmad-output/test-artifacts/t17/run_t17_tests.py"
BLOCKED_NOTE = (
    "Real non-Markdown extraction sample authorization, golden/loss evaluation and OCR quality evidence remain BLOCKED. "
    "This report contains only synthetic gating evidence; it does not claim production extraction PASS."
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


def check_route_activation_gate(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        owner_samples = bool(inp.get("owner_authorized_samples"))
        format_agreement = bool(inp.get("format_agreement"))
        quality_review = bool(inp.get("quality_review"))
        data_profile = bool(inp.get("data_media_profile"))
        markdown_only = bool(inp.get("markdown_only_workload"))
        ok = markdown_only or (owner_samples and format_agreement and quality_review and data_profile)
        details = {
            "owner_authorized_samples": owner_samples,
            "format_agreement": format_agreement,
            "quality_review": quality_review,
            "data_media_profile": data_profile,
            "markdown_only_workload": markdown_only,
        }
        if exp_status == "PASS":
            checks.append(_check(f"route_activation_gate.{name}.valid", "route_activation_gate", "PASS" if ok else "FAIL",
                "non-Markdown route activated only with owner samples, format agreement, quality review and data/media profile",
                "activation gate valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"route_activation_gate.{name}.rejected", "route_activation_gate", "FAIL" if not ok else "PASS",
                f"activation without required inputs rejected with {exp.get('error', 'INVALID_CONFIG')}",
                "activation gate problem detected" if not ok else "activation gate unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_docling_assessment(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        docling_assessed = bool(inp.get("docling_assessed"))
        second_pipeline = bool(inp.get("second_pipeline_considered"))
        documented_need = bool(inp.get("documented_unmet_need"))
        approved_adr = bool(inp.get("approved_adr"))
        compat_license_rollback = bool(inp.get("compatibility_license_rollback_assessed"))
        ok = docling_assessed and (not second_pipeline or (documented_need and approved_adr and compat_license_rollback))
        details = {
            "docling_assessed": docling_assessed,
            "second_pipeline_considered": second_pipeline,
            "documented_unmet_need": documented_need,
            "approved_adr": approved_adr,
            "compatibility_license_rollback_assessed": compat_license_rollback,
        }
        if exp_status == "PASS":
            checks.append(_check(f"docling_assessment.{name}.valid", "docling_assessment", "PASS" if ok else "FAIL",
                "Docling assessed first; second pipeline requires documented need, approved ADR and compatibility/license/rollback assessment",
                "Docling assessment valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"docling_assessment.{name}.rejected", "docling_assessment", "FAIL" if not ok else "PASS",
                f"undocumented second pipeline rejected with {exp.get('error', 'INVALID_CONFIG')}",
                "Docling assessment problem detected" if not ok else "Docling assessment unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_golden_fixtures(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        metrics = inp.get("metrics", {})
        supported = bool(inp.get("format_supported"))
        has_pages = isinstance(metrics.get("page_or_slide_count"), int) and metrics.get("page_or_slide_count", 0) > 0
        has_encoding = bool(metrics.get("encoding"))
        has_reading_order = bool(metrics.get("reading_order_valid"))
        has_tables = bool(metrics.get("table_structure_valid"))
        has_numbers = bool(metrics.get("numbers_preserved"))
        has_links = bool(metrics.get("links_anchors_preserved"))
        ok = supported and has_pages and has_encoding and has_reading_order and has_tables and has_numbers and has_links
        details = {
            "format_supported": supported,
            "metrics": metrics,
        }
        if exp_status == "PASS":
            checks.append(_check(f"golden_fixtures.{name}.valid", "golden_fixtures", "PASS" if ok else "FAIL",
                "golden fixtures measure page/slide counts, encoding, reading order, table/numbers, links/anchors",
                "golden fixtures valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"golden_fixtures.{name}.rejected", "golden_fixtures", "FAIL" if not ok else "PASS",
                f"unsupported or incomplete golden fixture rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                "golden fixture problem detected" if not ok else "golden fixtures unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_loss_quarantine(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        loss = bool(inp.get("extraction_loss")) or bool(inp.get("empty_or_garbled")) or bool(inp.get("unsupported_format")) or bool(inp.get("ocr_disagreement"))
        quarantined = bool(inp.get("quarantined"))
        original_recoverable = bool(inp.get("original_recoverable"))
        source_merged = bool(inp.get("source_merged"))
        partial_index = bool(inp.get("partial_index_published"))
        ok = (not loss) or (quarantined and original_recoverable and not source_merged and not partial_index)
        details = {
            "extraction_loss": inp.get("extraction_loss"),
            "empty_or_garbled": inp.get("empty_or_garbled"),
            "unsupported_format": inp.get("unsupported_format"),
            "ocr_disagreement": inp.get("ocr_disagreement"),
            "quarantined": quarantined,
            "original_recoverable": original_recoverable,
            "source_merged": source_merged,
            "partial_index_published": partial_index,
        }
        if exp_status == "PASS":
            checks.append(_check(f"loss_quarantine.{name}.valid", "loss_quarantine", "PASS" if ok else "FAIL",
                "loss/garbled/unsupported/OCR-disagreement quarantined with original recoverable; source not merged; no partial index",
                "loss/quarantine valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"loss_quarantine.{name}.rejected", "loss_quarantine", "FAIL" if not ok else "PASS",
                f"unquarantined loss or partial index rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "loss/quarantine problem detected" if not ok else "loss/quarantine unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_media_classes(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        media_class = inp.get("media_class", "")
        excluded = bool(inp.get("excluded"))
        kept_caption = bool(inp.get("kept_with_caption"))
        labelled = bool(inp.get("auto_description_labelled"))
        cites_original = bool(inp.get("cites_original_page"))
        human_verified = bool(inp.get("human_verified"))
        indexed = bool(inp.get("indexed"))
        if media_class == "decorative":
            ok = excluded and not indexed
        elif media_class == "illustrative":
            ok = kept_caption and indexed
        elif media_class == "substantive":
            ok = labelled and cites_original and indexed
        elif media_class == "critical":
            ok = human_verified and indexed
        elif media_class == "handwritten":
            ok = human_verified and indexed
        else:
            ok = False
        details = {
            "media_class": media_class,
            "excluded": excluded,
            "kept_with_caption": kept_caption,
            "auto_description_labelled": labelled,
            "cites_original_page": cites_original,
            "human_verified": human_verified,
            "indexed": indexed,
        }
        if exp_status == "PASS":
            checks.append(_check(f"media_classes.{name}.valid", "media_classes", "PASS" if ok else "FAIL",
                "decorative excluded; illustrative kept+caption; substantive labelled+cites original; critical/handwritten verified",
                "media class handling valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"media_classes.{name}.rejected", "media_classes", "FAIL" if not ok else "PASS",
                f"media class violation rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                "media class problem detected" if not ok else "media class handling unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_malicious_malformed(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        rejected = bool(inp.get("rejected_before_corpus"))
        corpus_preview = bool(inp.get("reached_corpus_or_preview"))
        ok = rejected and not corpus_preview
        details = {
            "sample_type": inp.get("sample_type"),
            "rejected_before_corpus": rejected,
            "reached_corpus_or_preview": corpus_preview,
        }
        if exp_status == "PASS":
            checks.append(_check(f"malicious_malformed.{name}.rejected", "malicious_malformed", "PASS" if ok else "FAIL",
                "malicious or malformed samples rejected before corpus/preview",
                "sample rejected" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"malicious_malformed.{name}.allowed", "malicious_malformed", "FAIL" if not ok else "PASS",
                f"malicious/malformed sample allowed into corpus rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "malicious/malformed sample allowed" if not ok else "sample unexpectedly rejected",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_provider_profile_egress(
    fixtures: list[dict[str, Any]], fixture_path: Path
) -> list[hc.Check]:
    checks: list[hc.Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        approved_provider = bool(inp.get("approved_provider"))
        approved_profile = bool(inp.get("approved_data_profile"))
        approved_egress = bool(inp.get("approved_egress_route"))
        unplanned_fallback = bool(inp.get("unplanned_fallback"))
        pii_egress = bool(inp.get("pii_egress"))
        ok = approved_provider and approved_profile and approved_egress and not unplanned_fallback and not pii_egress
        details = {
            "approved_provider": approved_provider,
            "approved_data_profile": approved_profile,
            "approved_egress_route": approved_egress,
            "unplanned_fallback": unplanned_fallback,
            "pii_egress": pii_egress,
        }
        if exp_status == "PASS":
            checks.append(_check(f"provider_profile_egress.{name}.valid", "provider_profile_egress", "PASS" if ok else "FAIL",
                "only approved provider/data profile/egress route used; unplanned fallback and PII egress blocked",
                "provider/profile/egress valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"provider_profile_egress.{name}.rejected", "provider_profile_egress", "FAIL" if not ok else "PASS",
                f"unapproved route/fallback/PII egress rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "provider/profile/egress problem detected" if not ok else "provider/profile/egress unexpectedly valid",
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
    parser = argparse.ArgumentParser(description="T17 Conditional Evidence-Gated Extraction, Media and OCR Quality")
    parser.add_argument("--dry-run", action="store_true", help="list checks without writing reports")
    args = parser.parse_args()

    if not hc.CONTRACTS_DIR.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t17-extraction-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.contracts_dir", "harness", "BLOCKED", "contracts directory present", f"missing {hc.CONTRACTS_DIR}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="extraction-results.json", title="T17 Conditional Evidence-Gated Extraction, Media and OCR Quality Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    schema_validator = hc.SchemaValidator(hc.CONTRACTS_DIR)
    if schema_validator.load_errors:
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            schema_version="t17-extraction-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(_check(f"harness.schema_load.{name}", "harness", "BLOCKED", "schema loads", f"load error: {exc}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="extraction-results.json", title="T17 Conditional Evidence-Gated Extraction, Media and OCR Quality Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = hc.ReportBuilder(
            baseline_commit=hc.T00_BASELINE_COMMIT,
            spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
            contracts_version="extraction-gating-v1",
            schema_version="t17-extraction-results-v1",
            command=RERUN_CMD,
            rerun_cmd=RERUN_CMD,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
            raw_filename="extraction-results.json", title="T17 Conditional Evidence-Gated Extraction, Media and OCR Quality Evidence Summary",
            blocked_note=BLOCKED_NOTE)

    builder = hc.ReportBuilder(
        baseline_commit=hc.T00_BASELINE_COMMIT,
        spec_baseline_commit=hc.SPEC_BASELINE_COMMIT,
        contracts_version="extraction-gating-v1",
        schema_version="t17-extraction-results-v1",
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

    for sub in ["live_docling_quality", "live_ocr_golden_set", "live_media_classification", "live_owner_authorized_samples"]:
        builder.add(_check(f"runtime.{sub}", "runtime", "BLOCKED", "live integration evidence", "requires owner-authorized real samples and extraction sandbox"))

    return hc.write_reports(builder, dry_run=args.dry_run, output_dir=OUTPUT_DIR, evidence_dir=EVIDENCE_DIR,
        raw_filename="extraction-results.json", title="T17 Conditional Evidence-Gated Extraction, Media and OCR Quality Evidence Summary",
        blocked_note=BLOCKED_NOTE)


if __name__ == "__main__":
    sys.exit(main())
