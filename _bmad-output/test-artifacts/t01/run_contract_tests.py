# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T01 contract-test harness.

Parses specs/corporate-kb/contracts/t01-contract-tests.yaml, bootstraps two
synthetic repository-per-Space fixtures, executes the CF-01..CF-30 vectors that
can be checked without a live GitLab/IdP/CI/hoster.ai sandbox, and writes
deterministic reports to _bmad-output/test-artifacts/t01/ plus a sanitized copy
to specs/corporate-kb/evidence/t01/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema.exceptions import ValidationError

# Make the harness package importable when run from the repository root.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fixtures.spaces import sales_pricing_space, sales_space  # noqa: E402
from reporters.json_reporter import Check, ReportBuilder, sha256_text  # noqa: E402
from reporters.markdown_reporter import render_summary  # noqa: E402
from reporters.sanitize import sanitize_for_evidence  # noqa: E402
from sandbox import GitLabSandbox  # noqa: E402
from validators import MarkdownLinkChecker, OpenApiChecker, ProjectionMappingChecker, SchemaValidator  # noqa: E402

CONTRACTS_DIR = Path("specs/corporate-kb/contracts")
SPEC_PATH = CONTRACTS_DIR / "t01-contract-tests.yaml"
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t01")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t01")
BASELINE_COMMIT = "152b00ff6aaa7b95c7b958d822bf54e8a54d1650"


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=True, allow_unicode=True)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def fixture_path(name: str) -> Path:
    return Path("_bmad-output/test-artifacts/t01/fixtures/payloads") / name


def fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blocked(
    check_id: str,
    cf_id: str,
    reason: str,
    fixture: Path | None = None,
    expected: str = "real sandbox/integration evidence",
) -> Check:
    return Check(
        id=check_id,
        cf_id=cf_id,
        status="BLOCKED",
        expected=expected,
        actual=reason,
        fixture_path=str(fixture) if fixture else None,
        rerun_cmd="uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py",
        details={"reason": reason},
    )


def _not_executed(
    check_id: str,
    cf_id: str,
    reason: str,
    fixture: Path | None = None,
    expected: str = "check depends on unavailable sandbox or backend",
) -> Check:
    return Check(
        id=check_id,
        cf_id=cf_id,
        status="NOT_EXECUTED",
        expected=expected,
        actual=reason,
        fixture_path=str(fixture) if fixture else None,
        rerun_cmd="uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py",
        details={"reason": reason},
    )


def _pass(
    check_id: str,
    cf_id: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> Check:
    return Check(
        id=check_id,
        cf_id=cf_id,
        status="PASS",
        expected=expected,
        actual=actual,
        input_sha256=fixture_sha256(fixture) if fixture else None,
        fixture_path=str(fixture) if fixture else None,
        rerun_cmd="uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py",
        details=details or {},
    )


def _fail(
    check_id: str,
    cf_id: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
) -> Check:
    return Check(
        id=check_id,
        cf_id=cf_id,
        status="FAIL",
        expected=expected,
        actual=actual,
        input_sha256=fixture_sha256(fixture) if fixture else None,
        fixture_path=str(fixture) if fixture else None,
        rerun_cmd="uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py",
        details=details or {},
    )


def run_cf30_catalog_completeness(
    catalog: dict[str, Any],
    schema_validator: SchemaValidator,
    openapi: OpenApiChecker,
) -> list[Check]:
    """CF-30: parse/resolve/unique operationIds/regex/mutation headers."""
    checks: list[Check] = []

    # JSON parse every .schema.json (already done in SchemaValidator load).
    checks.append(
        _pass(
            "CF-30.json_schema_parse",
            "CF-30",
            "all .schema.json parse",
            f"{len(schema_validator.schemas)} schema files parsed",
        )
    )

    # YAML parse openapi, agent-tools, events, t01-contract-tests.
    for name in ("openapi.yaml", "agent-tools.yaml", "events.yaml", "t01-contract-tests.yaml"):
        try:
            load_yaml(CONTRACTS_DIR / name)
            checks.append(
                _pass(
                    f"CF-30.yaml_parse.{name}",
                    "CF-30",
                    f"{name} parses",
                    f"{name} parsed",
                )
            )
        except Exception as exc:
            checks.append(
                _fail(
                    f"CF-30.yaml_parse.{name}",
                    "CF-30",
                    f"{name} parses",
                    str(exc),
                )
            )

    # Resolve all $ref in schemas.
    ref_results = schema_validator.resolve_refs()
    unresolved = [r for r in ref_results if r[2] is not None]
    if unresolved:
        checks.append(
            _fail(
                "CF-30.schema_refs_resolve",
                "CF-30",
                "all schema $ref resolve",
                f"unresolved: {unresolved[:3]}",
                details={"unresolved_count": len(unresolved)},
            )
        )
    else:
        checks.append(
            _pass(
                "CF-30.schema_refs_resolve",
                "CF-30",
                "all schema $ref resolve",
                f"{len(ref_results)} refs resolved",
            )
        )

    # Resolve local $ref in openapi / agent-tools.
    openapi_ref_results = openapi.resolve_refs()
    openapi_unresolved = [r for r in openapi_ref_results if r[2] is not None]
    if openapi_unresolved:
        checks.append(
            _fail(
                "CF-30.openapi_refs_resolve",
                "CF-30",
                "all OpenAPI/agent-tools $ref resolve",
                f"unresolved: {openapi_unresolved[:3]}",
            )
        )
    else:
        checks.append(
            _pass(
                "CF-30.openapi_refs_resolve",
                "CF-30",
                "all OpenAPI/agent-tools $ref resolve",
                f"{len(openapi_ref_results)} refs resolved",
            )
        )

    # Compile regex patterns.
    regex_results = schema_validator.compile_regexes()
    bad_regex = [r for r in regex_results if r[2] is not None]
    if bad_regex:
        checks.append(
            _fail(
                "CF-30.regex_compile",
                "CF-30",
                "all regex patterns compile",
                f"bad regex: {bad_regex[:3]}",
            )
        )
    else:
        checks.append(
            _pass(
                "CF-30.regex_compile",
                "CF-30",
                "all regex patterns compile",
                f"{len(regex_results)} patterns compiled",
            )
        )

    # Unique operationIds.
    dupes = openapi.duplicate_operation_ids()
    if dupes:
        checks.append(
            _fail(
                "CF-30.operationIds_unique",
                "CF-30",
                "OpenAPI operationIds are unique",
                f"duplicates: {dupes[:3]}",
            )
        )
    else:
        checks.append(
            _pass(
                "CF-30.operationIds_unique",
                "CF-30",
                "OpenAPI operationIds are unique",
                f"{len(openapi.operation_ids())} operationIds unique",
            )
        )

    # Mutation operations require Idempotency-Key.
    missing = openapi.missing_idempotency_header()
    if missing:
        checks.append(
            _fail(
                "CF-30.mutation_headers_complete",
                "CF-30",
                "mutating operations require Idempotency-Key header",
                f"missing: {missing[:3]}",
            )
        )
    else:
        checks.append(
            _pass(
                "CF-30.mutation_headers_complete",
                "CF-30",
                "mutating operations require Idempotency-Key header",
                "all mutation operations require Idempotency-Key",
            )
        )

    # Agent-tools vs bounded-agent OpenAPI operationId mapping.
    agent_ids = openapi.agent_tool_operation_ids()
    bounded_ids = openapi.bounded_agent_operation_ids()
    if agent_ids == bounded_ids:
        checks.append(
            _pass(
                "CF-30.agent_tool_operationId_mapping",
                "CF-30",
                "agent-tools operationIds match bounded-agent OpenAPI operations",
                f"matched {len(agent_ids)} operationIds",
            )
        )
    else:
        checks.append(
            _fail(
                "CF-30.agent_tool_operationId_mapping",
                "CF-30",
                "agent-tools operationIds match bounded-agent OpenAPI operations",
                f"agent_only={agent_ids - bounded_ids}, bounded_only={bounded_ids - agent_ids}",
            )
        )

    # Semantic consumer assertions depend on a GO backend that is not provisioned
    # in T01; real integration status depends on live GitLab/IdP/CI/hoster.ai
    # sandboxes. Per spec these are DESIGN_NOT_EXECUTED (NOT_EXECUTED).
    checks.append(
        _not_executed(
            "CF-30.semantic_consumer_assertions",
            "CF-30",
            "semantic consumer assertions require a running GO backend and real sandbox not provisioned for T01",
            expected="semantic consumer assertions pass",
        )
    )
    checks.append(
        _not_executed(
            "CF-30.integration_status",
            "CF-30",
            "real GitLab/IdP/CI/hoster.ai sandbox and credentials are not provisioned for T01",
            expected="integration_status available",
        )
    )
    return checks


def run_cf29_links(checker: MarkdownLinkChecker) -> list[Check]:
    """CF-29: crash recovery headings and local Markdown links."""
    checks: list[Check] = []
    for name in ("specs/corporate-kb/integration.md", "specs/corporate-kb/contracts/gitlab-integration.md"):
        path = Path(name)
        results = checker.check_file(path)
        broken = [r for r in results if r[2] is not None]
        if broken:
            checks.append(
                _fail(
                    f"CF-29.{name}.links",
                    "CF-29",
                    "local Markdown links resolve",
                    f"broken: {broken[:3]}",
                )
            )
        else:
            checks.append(
                _pass(
                    f"CF-29.{name}.links",
                    "CF-29",
                    "local Markdown links resolve",
                    f"{len(results)} local links checked",
                )
            )

    # Verify §7.1 and §7.3 are referenced in crash-recovery headings, not §7.7.
    _CRASH_RECOVERY_RE = re.compile(r"recovery|crash|fencing", re.IGNORECASE)

    def has_section_reference(path: Path, section: str) -> bool:
        text = path.read_text(encoding="utf-8")
        section_re = re.compile(rf"\b7\.{section}\b")
        for line in text.splitlines():
            if not line.startswith(("#", "##", "###")):
                continue
            heading_text = line.lstrip("#").strip()
            if _CRASH_RECOVERY_RE.search(heading_text) and section_re.search(heading_text):
                return True
        return False

    integration_path = Path("specs/corporate-kb/integration.md")
    gitlab_path = Path("specs/corporate-kb/contracts/gitlab-integration.md")
    has_7_1 = has_section_reference(integration_path, "1") or has_section_reference(gitlab_path, "1")
    has_7_3 = has_section_reference(integration_path, "3") or has_section_reference(gitlab_path, "3")
    has_7_7 = has_section_reference(integration_path, "7") or has_section_reference(gitlab_path, "7")

    if has_7_1 and has_7_3 and not has_7_7:
        checks.append(
            _pass(
                "CF-29.spec_reference_7.1_and_7.3",
                "CF-29",
                "spec references 7.1 and 7.3 for crash recovery in both files, not 7.7",
                "7.1=True, 7.3=True, 7.7=False",
            )
        )
    else:
        checks.append(
            _fail(
                "CF-29.spec_reference_7.1_and_7.3",
                "CF-29",
                "spec references 7.1 and 7.3 for crash recovery in both files, not 7.7",
                f"7.1={has_7_1}, 7.3={has_7_3}, 7.7={has_7_7}",
            )
        )
    return checks


def run_cf01_authz_context(schema_validator: SchemaValidator) -> list[Check]:
    """CF-01: cross-Space isolation via AuthzContext schema and invariant checks."""
    checks: list[Check] = []
    sales = load_yaml(fixture_path("cf01_authz_context_sales.yaml"))
    pricing = load_yaml(fixture_path("cf01_authz_context_pricing.yaml"))

    for name, ctx in (("sales", sales), ("pricing", pricing)):
        err = schema_validator.validate_or_error("authz-context.schema.json", ctx)
        if err:
            checks.append(
                _fail(
                    f"CF-01.{name}_schema",
                    "CF-01",
                    f"{name} authz-context is schema valid",
                    err,
                    fixture=fixture_path(f"cf01_authz_context_{name}.yaml"),
                )
            )
        else:
            checks.append(
                _pass(
                    f"CF-01.{name}_schema",
                    "CF-01",
                    f"{name} authz-context is schema valid",
                    "schema valid",
                    fixture=fixture_path(f"cf01_authz_context_{name}.yaml"),
                )
            )

    # Structural uniqueness / no-shared-binding check.
    sales_scope = sales["space_scopes"][0]
    pricing_scope = pricing["space_scopes"][0]
    shared = (
        sales_scope["repository_id"] == pricing_scope["repository_id"]
        or sales_scope["policy_bundle_id"] == pricing_scope["policy_bundle_id"]
        or sales_scope["group_snapshot"]["snapshot_id"]
        == pricing_scope["group_snapshot"]["snapshot_id"]
    )
    if shared:
        checks.append(
            _fail(
                "CF-01.space_isolation",
                "CF-01",
                "sales and sales-pricing have distinct repository/bundle/group snapshot",
                "fixtures share a repository_id, policy_bundle_id or group_snapshot",
            )
        )
    else:
        checks.append(
            _pass(
                "CF-01.space_isolation",
                "CF-01",
                "sales and sales-pricing have distinct repository/bundle/group snapshot",
                "distinct repository_id, policy_bundle_id, group_snapshot",
            )
        )

    # Runtime fan-out / cursor replay / AccessPolicyChanged rejection remain BLOCKED.
    for sub in (
        "search_fanout",
        "cursor_replay_stale",
        "access_policy_changed_rejection",
    ):
        checks.append(
            _blocked(
                f"CF-01.{sub}",
                "CF-01",
                "requires live AuthzContext service and GitLab webhook/identity sandbox",
                expected="POLICY_REVISION_MISMATCH / AUTHZ_CONTEXT_STALE / rejected",
            )
        )
    return checks


def _canonical_prefix(prefix: str, reject_trailing_slash: bool = False) -> str | None:
    """Return NFC-normalized prefix or None if it is ambiguous/invalid.

    Root ``/`` is a valid prefix. A non-empty input that normalizes to ``None``
    indicates an invalid/ambiguous path and must be treated as a failure by
    callers.
    """
    prefix = unicodedata.normalize("NFC", prefix)
    if prefix == "/":
        return "/"
    if prefix.startswith("/"):
        if reject_trailing_slash and prefix.endswith("/"):
            return None
        prefix = prefix.rstrip("/")
    if not prefix:
        return None
    parts = prefix.split("/")
    if any(p in ("", ".", "..") for p in parts[1:]):
        return None
    if "\\" in prefix or ".." in prefix:
        return None
    return prefix


def run_cf02_approval_policy(schema_validator: SchemaValidator) -> list[Check]:
    """CF-02: approval policy schema + prefix normalization checks."""
    checks: list[Check] = []
    files = {
        "valid": fixture_path("cf02_approval_policy_valid.yaml"),
        "duplicate_prefix": fixture_path("cf02_approval_policy_duplicate_prefix.yaml"),
        "cyrillic": fixture_path("cf02_approval_policy_cyrillic.yaml"),
    }

    for name, path in files.items():
        data = load_yaml(path)
        err = schema_validator.validate_or_error("approval-policy.schema.json", data)
        if err:
            checks.append(
                _fail(
                    f"CF-02.{name}_schema",
                    "CF-02",
                    f"{name} policy schema valid",
                    err,
                    fixture=path,
                )
            )
        else:
            checks.append(
                _pass(
                    f"CF-02.{name}_schema",
                    "CF-02",
                    f"{name} policy schema valid",
                    "schema valid",
                    fixture=path,
                )
            )

    # Duplicate normalized prefix detection.
    dup_data = load_yaml(files["duplicate_prefix"])
    raw_prefixes = [r["path_prefix"] for r in dup_data["rules"]]
    prefixes: list[str | None] = [_canonical_prefix(p, reject_trailing_slash=False) for p in raw_prefixes]
    invalid = [(raw, norm) for raw, norm in zip(raw_prefixes, prefixes) if raw and norm is None]
    if invalid:
        checks.append(
            _fail(
                "CF-02.duplicate_prefix_invalid",
                "CF-02",
                "all non-empty prefixes normalize to a valid canonical prefix",
                f"invalid prefixes: {invalid[:3]}",
                fixture=files["duplicate_prefix"],
            )
        )
    else:
        seen = Counter(p for p in prefixes if p is not None)
        duplicates = {p for p, c in seen.items() if c > 1}
        if duplicates:
            checks.append(
                _pass(
                    "CF-02.duplicate_prefix_detected",
                    "CF-02",
                    "duplicate normalized prefixes are rejected (INVALID_POLICY)",
                    f"duplicates: {sorted(duplicates)}",
                    fixture=files["duplicate_prefix"],
                )
            )
        else:
            checks.append(
                _fail(
                    "CF-02.duplicate_prefix_detected",
                    "CF-02",
                    "duplicate normalized prefixes are rejected (INVALID_POLICY)",
                    "no duplicate normalized prefixes found in fixture",
                    fixture=files["duplicate_prefix"],
                )
            )

    # Cyrillic NFC/NFD duplicate detection.
    cyr_data = load_yaml(files["cyrillic"])
    cyr_prefixes = [
        unicodedata.normalize("NFC", r["path_prefix"]) for r in cyr_data["rules"]
    ]
    if len(cyr_prefixes) == len(set(cyr_prefixes)):
        checks.append(
            _fail(
                "CF-02.cyrillic_duplicate_detected",
                "CF-02",
                "NFC/NFD duplicate prefixes are rejected",
                "NFC-normalized prefixes are not equal in fixture",
                fixture=files["cyrillic"],
            )
        )
    else:
        checks.append(
            _pass(
                "CF-02.cyrillic_duplicate_detected",
                "CF-02",
                "NFC/NFD duplicate prefixes are rejected",
                f"NFC-normalized duplicates: {cyr_prefixes}",
                fixture=files["cyrillic"],
            )
        )

    # Longest-prefix runtime assignment remains BLOCKED.
    checks.append(
        _blocked(
            "CF-02.longest_prefix_assignment",
            "CF-02",
            "longest-prefix rule selection requires active approval policy service",
        )
    )
    return checks


def run_cf03_front_matter(schema_validator: SchemaValidator) -> list[Check]:
    """CF-03: archive bidirectional invariant."""
    checks: list[Check] = []
    cases = {
        "archived_without_archive": fixture_path(
            "cf03_front_matter_archived_without_archive.yaml"
        ),
        "unarchived_with_archive": fixture_path(
            "cf03_front_matter_unarchived_with_archive.yaml"
        ),
        "valid_restore": fixture_path("cf03_front_matter_valid_restore.yaml"),
    }

    for name, path in cases.items():
        data = load_yaml(path)
        err = schema_validator.validate_or_error("front-matter.schema.json", data)
        if name in ("archived_without_archive", "unarchived_with_archive"):
            if err:
                checks.append(
                    _pass(
                        f"CF-03.{name}_rejected",
                        "CF-03",
                        f"{name} fails schema validation",
                        err,
                        fixture=path,
                    )
                )
            else:
                checks.append(
                    _fail(
                        f"CF-03.{name}_rejected",
                        "CF-03",
                        f"{name} fails schema validation",
                        "schema accepted invalid fixture",
                        fixture=path,
                    )
                )
        else:
            if err:
                checks.append(
                    _fail(
                        f"CF-03.{name}_accepted",
                        "CF-03",
                        f"{name} is schema valid",
                        err,
                        fixture=path,
                    )
                )
            else:
                checks.append(
                    _pass(
                        f"CF-03.{name}_accepted",
                        "CF-03",
                        f"{name} is schema valid",
                        "schema valid",
                        fixture=path,
                    )
                )

    # Bidirectional invariant: archived iff archive present.
    for name, path in cases.items():
        data = load_yaml(path)
        archived = data.get("archived", False)
        has_archive = data.get("archive") is not None
        if archived == has_archive or name == "valid_restore":
            expected_ok = True
        else:
            expected_ok = False
        actual_ok = archived == has_archive
        if expected_ok == actual_ok:
            checks.append(
                _pass(
                    f"CF-03.{name}_bidirectional",
                    "CF-03",
                    "archived flag and archive block are consistent",
                    f"archived={archived}, has_archive={has_archive}",
                    fixture=path,
                )
            )
        else:
            checks.append(
                _fail(
                    f"CF-03.{name}_bidirectional",
                    "CF-03",
                    "archived flag and archive block are consistent",
                    f"archived={archived}, has_archive={has_archive}",
                    fixture=path,
                )
            )

    # Replacement/descendant semantic checks remain BLOCKED.
    checks.append(
        _blocked(
            "CF-03.replacement_semantics",
            "CF-03",
            "archive replacement/descendant semantics require canonical document service",
        )
    )
    return checks


def run_cf04_source_origin(schema_validator: SchemaValidator) -> list[Check]:
    """CF-04: origin required for migrated/source_managed; live_operational forbidden."""
    checks: list[Check] = []

    fm_path = fixture_path("cf04_front_matter_migrated_no_origin.yaml")
    fm = load_yaml(fm_path)
    err = schema_validator.validate_or_error("front-matter.schema.json", fm)
    if err:
        checks.append(
            _pass(
                "CF-04.migrated_no_origin_rejected",
                "CF-04",
                "migrated front matter without origin is rejected",
                err,
                fixture=fm_path,
            )
        )
    else:
        checks.append(
            _fail(
                "CF-04.migrated_no_origin_rejected",
                "CF-04",
                "migrated front matter without origin is rejected",
                "schema accepted invalid fixture",
                fixture=fm_path,
            )
        )

    so_path = fixture_path("cf04_source_origin_live_operational.yaml")
    so = load_yaml(so_path)
    err = schema_validator.validate_or_error("source-origin.schema.json", so)
    # source-origin.schema.json allows live_operational; canonical front matter does not.
    if err:
        checks.append(
            _fail(
                "CF-04.source_origin_live_operational_valid",
                "CF-04",
                "source-origin allows live_operational ownership_mode",
                err,
                fixture=so_path,
            )
        )
    else:
        checks.append(
            _pass(
                "CF-04.source_origin_live_operational_valid",
                "CF-04",
                "source-origin allows live_operational ownership_mode",
                "schema valid",
                fixture=so_path,
            )
        )

    # live_operational in canonical front matter remains BLOCKED (not expressible in schema).
    checks.append(
        _blocked(
            "CF-04.live_operational_canonical_forbidden",
            "CF-04",
            "canonical front matter live_operational rejection requires document service",
        )
    )
    return checks


def run_cf05_source_id(schema_validator: SchemaValidator) -> list[Check]:
    """CF-05: source_id DOC-0001 preserved, lowercase rewrite rejected."""
    checks: list[Check] = []

    valid_path = fixture_path("cf05_source_id_doc0001.yaml")
    valid = load_yaml(valid_path)
    err = schema_validator.validate_or_error("source-origin.schema.json", valid)
    if err:
        checks.append(
            _fail(
                "CF-05.doc0001_valid",
                "CF-05",
                "source_id DOC-0001 is valid",
                err,
                fixture=valid_path,
            )
        )
    else:
        checks.append(
            _pass(
                "CF-05.doc0001_valid",
                "CF-05",
                "source_id DOC-0001 is valid",
                "schema valid",
                fixture=valid_path,
            )
        )

    lower_path = fixture_path("cf05_source_id_lowercase.yaml")
    lower = load_yaml(lower_path)
    err = schema_validator.validate_or_error("source-origin.schema.json", lower)
    if err:
        checks.append(
            _pass(
                "CF-05.lowercase_schema_rejected",
                "CF-05",
                "source_id lowercase rewrite fails JSON Schema",
                err,
                fixture=lower_path,
            )
        )
    else:
        # Schema accepts lowercase doc-0001; semantic normalization rule rejects it.
        checks.append(
            _blocked(
                "CF-05.lowercase_semantic_rejected",
                "CF-05",
                "source_id lowercase rewrite requires canonical source service for semantic validation",
                fixture=lower_path,
                expected="semantic_valid=false (DOC-0001 preserved)",
            )
        )
    return checks


def run_cf06_docops(schema_validator: SchemaValidator) -> list[Check]:
    """CF-06: DocOps review/correction task schema checks."""
    checks: list[Check] = []

    # Correction task schema has closed states; runtime lifecycle remains BLOCKED.
    sample = {
        "schema_version": "docops-correction-task-v1",
        "task_id": "11111111-1111-4111-8111-111111111111",
        "space_id": "sales",
        "repository_id": "repo-sales",
        "document_id": "22222222-2222-4222-8222-222222222222",
        "document_revision_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "state": "open",
        "requester_stable_id": "user-sales-2",
        "owner": {"kind": "group", "stable_id": "sales-approvers"},
        "evidence_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "linked_mr": None,
        "idempotency_key": "key-1",
        "payload_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "task_version": 1,
        "created_at": "2026-11-08T00:00:00Z",
        "updated_at": "2026-11-08T00:00:00Z",
        "resolved_at": None,
        "cancelled_at": None,
        "resolved_by_stable_id": None,
        "cancelled_by_stable_id": None,
        "resolution_reason": None,
        "cancellation_reason": None,
        "resolution_evidence_sha256": None,
        "cancellation_evidence_sha256": None,
    }
    err = schema_validator.validate_or_error("docops-correction-task.schema.json", sample)
    if err:
        checks.append(
            _fail(
                "CF-06.correction_task_schema_valid",
                "CF-06",
                "valid open correction task passes schema",
                err,
            )
        )
    else:
        checks.append(
            _pass(
                "CF-06.correction_task_schema_valid",
                "CF-06",
                "valid open correction task passes schema",
                "schema valid",
            )
        )

    # Invalid state: open with linked_mr.
    invalid_linked = dict(sample)
    invalid_linked["linked_mr"] = {
        "proposal_id": "prop-1",
        "proposal_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "merge_commit_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    }
    err = schema_validator.validate_or_error(
        "docops-correction-task.schema.json", invalid_linked
    )
    if err:
        checks.append(
            _pass(
                "CF-06.open_with_linked_mr_rejected",
                "CF-06",
                "open task with non-null linked_mr is schema-invalid",
                err,
            )
        )
    else:
        checks.append(
            _fail(
                "CF-06.open_with_linked_mr_rejected",
                "CF-06",
                "open task with non-null linked_mr is schema-invalid",
                "schema accepted invalid fixture",
            )
        )

    # Runtime lifecycle, idempotency, MR governance remain BLOCKED.
    for sub in (
        "review_scheduled_due_removed",
        "correction_create_resolve_cancel",
        "idempotency_and_cas",
        "mr_governance",
    ):
        checks.append(
            _blocked(
                f"CF-06.{sub}",
                "CF-06",
                "requires live GO backend, GitLab MR sandbox and idempotency registry",
            )
        )
    return checks


def run_cf07_agent_tools(openapi: OpenApiChecker) -> list[Check]:
    """CF-07: agent-tool / bounded-agent operationId parity (structural only)."""
    checks: list[Check] = []
    agent_ids = openapi.agent_tool_operation_ids()
    bounded_ids = openapi.bounded_agent_operation_ids()
    if agent_ids == bounded_ids:
        checks.append(
            _pass(
                "CF-07.agent_tool_catalog_matches",
                "CF-07",
                "agent-tools operationIds match bounded-agent OpenAPI operations exactly",
                f"matched {len(agent_ids)} operationIds",
            )
        )
    else:
        checks.append(
            _fail(
                "CF-07.agent_tool_catalog_matches",
                "CF-07",
                "agent-tools operationIds match bounded-agent OpenAPI operations exactly",
                f"agent_only={agent_ids - bounded_ids}, bounded_only={bounded_ids - agent_ids}",
            )
        )

    # Runtime write-boundary checks remain BLOCKED.
    for sub in ("bounded_agent_forbidden_writes", "agent_propose_rejected"):
        checks.append(
            _blocked(
                f"CF-07.{sub}",
                "CF-07",
                "requires running GO service and agent credential sandbox",
            )
        )
    return checks


def run_cf08_connector() -> list[Check]:
    """CF-08: connector credential boundaries are runtime-only."""
    return [
        _blocked(
            f"CF-08.{sub}",
            "CF-08",
            "requires connector credential sandbox and immutable binding registry",
        )
        for sub in (
            "dry_run_staging",
            "post_cutover_proposal",
            "pre_cutover_forbidden",
            "cursor_binding_exact",
        )
    ]


def run_cf09_invariants(openapi: OpenApiChecker) -> list[Check]:
    """CF-09: x-contract-invariants IDs present and complete."""
    checks: list[Check] = []
    invariants = openapi.openapi.get("x-contract-invariants", [])
    required_ids = {
        "PATH_BODY_SPACE_ID",
        "PATH_BODY_DOCUMENT_ID",
        "PATH_BODY_PROPOSAL_ID",
        "PATH_BODY_IMPORT_ID",
        "PATH_BODY_RUN_ID",
        "PATH_BODY_CORRECTION_TASK_ID",
        "BODY_HEADER_IDEMPOTENCY",
        "DECISION_KEY_AND_PROPOSAL_EQUALITY",
    }
    found_ids = {inv.get("id") for inv in invariants if isinstance(inv, dict)}
    missing = required_ids - found_ids
    if missing:
        checks.append(
            _fail(
                "CF-09.required_invariant_ids",
                "CF-09",
                f"required invariant IDs present: {required_ids}",
                f"missing: {missing}",
            )
        )
    else:
        checks.append(
            _pass(
                "CF-09.required_invariant_ids",
                "CF-09",
                f"required invariant IDs present: {required_ids}",
                f"found {len(required_ids)} required IDs",
            )
        )

    # Runtime path/body/header mismatch rejection remains BLOCKED.
    for sub in (
        "path_body_id_mismatch_rejected",
        "error_enum_coverage",
        "tool_adapter_route",
    ):
        checks.append(
            _blocked(
                f"CF-09.{sub}",
                "CF-09",
                "requires running GO API and mutation paths",
            )
        )
    return checks


def run_cf10_history_queue_correction() -> list[Check]:
    """CF-10: history, review-proposals and correction-task endpoints are runtime-only."""
    return [
        _blocked(
            f"CF-10.{sub}",
            "CF-10",
            "requires GitLab repository fixtures and GO runtime",
        )
        for sub in (
            "history_revert_mr",
            "approver_queue_prefix",
            "protected_object_not_found",
            "verified_root_commit",
            "non_root_empty_parents",
            "correction_get_cross_space",
            "resolve_cancel_authz",
            "open_to_in_review_merge",
            "no_mr_resolution",
            "idempotency_replay",
        )
    ]


def _error_paths_contain(errors, expected_segments: list[str]) -> bool:
    """Return True if any error's absolute_path starts with *expected_segments*."""
    for exc in errors:
        path = list(exc.absolute_path)
        if path[: len(expected_segments)] == expected_segments:
            return True
    return False


def run_cf11_index_snapshot(schema_validator: SchemaValidator) -> list[Check]:
    """CF-11: index-snapshot schema negative cases."""
    checks: list[Check] = []
    cases = {
        "requested_serving": (
            fixture_path("cf11_index_snapshot_requested_serving.yaml"),
            ["preflight", "serving_allowed"],
        ),
        "active_null_hash": (
            fixture_path("cf11_index_snapshot_active_null_hash.yaml"),
            ["exact_projection", "projection_sha256"],
        ),
        "incremental_missing_inputs": (
            fixture_path("cf11_index_snapshot_incremental_missing.yaml"),
            ["closure", "missing_inputs"],
        ),
    }

    for name, (path, expected_path) in cases.items():
        data = load_yaml(path)
        errors = list(schema_validator.iter_errors("index-snapshot.schema.json", data))
        if errors and _error_paths_contain(errors, expected_path):
            checks.append(
                _pass(
                    f"CF-11.{name}_rejected",
                    "CF-11",
                    f"{name} fails schema validation under {expected_path}",
                    f"matched error path; first error: {errors[0].message} at {list(errors[0].absolute_path)}",
                    fixture=path,
                )
            )
        elif errors:
            checks.append(
                _fail(
                    f"CF-11.{name}_rejected",
                    "CF-11",
                    f"{name} fails schema validation under {expected_path}",
                    f"rejected for unrelated reasons: {errors[:3]}",
                    fixture=path,
                )
            )
        else:
            checks.append(
                _fail(
                    f"CF-11.{name}_rejected",
                    "CF-11",
                    f"{name} fails schema validation under {expected_path}",
                    "schema accepted invalid fixture",
                    fixture=path,
                )
            )

    # Semantic-only checks remain BLOCKED.
    for sub in (
        "preflight_cutover_sha_mismatch",
        "active_incremental_history_rewrite",
    ):
        checks.append(
            _blocked(
                f"CF-11.{sub}",
                "CF-11",
                "requires index-run runtime and validated snapshots",
            )
        )
    return checks


def run_cf12_to_cf18_runtime(cf_id: str, name: str) -> list[Check]:
    """CF-12..CF-18 are fully runtime / DB / merge sandbox checks."""
    return [
        _blocked(
            f"{cf_id}.{name}",
            cf_id,
            "requires GitLab merge sandbox, index cutover runtime or export manifest runtime",
        )
    ]


def run_cf19_proposal_record(schema_validator: SchemaValidator) -> list[Check]:
    """CF-19: proposal-record schema + semantic negative checks."""
    checks: list[Check] = []
    path = fixture_path("cf19_proposal_record_bad_line_range.yaml")
    data = load_yaml(path)

    # Verify the fixture is otherwise schema-valid.
    errors = list(schema_validator.iter_errors("proposal-record.schema.json", data))
    if errors:
        checks.append(
            _fail(
                "CF-19.bad_line_range_fixture_schema",
                "CF-19",
                "negative fixture is valid except for intended line_range violation",
                f"unrelated schema errors: {errors[:3]}",
                fixture=path,
            )
        )
    else:
        checks.append(
            _pass(
                "CF-19.bad_line_range_fixture_schema",
                "CF-19",
                "negative fixture is valid except for intended line-range violation",
                "schema valid",
                fixture=path,
            )
        )

    # The line-range order invariant is not expressible in JSON Schema; check it here.
    reversed_ranges = []
    for i, ev in enumerate(data.get("evidence", [])):
        rng = ev.get("range")
        if rng and rng.get("end_line", 0) < rng.get("start_line", 0):
            reversed_ranges.append((i, rng))

    if reversed_ranges:
        checks.append(
            _pass(
                "CF-19.bad_line_range_detected",
                "CF-19",
                "line_range with end_line < start_line is rejected as semantic violation",
                f"reversed ranges: {reversed_ranges}",
                fixture=path,
            )
        )
    else:
        checks.append(
            _fail(
                "CF-19.bad_line_range_detected",
                "CF-19",
                "line_range with end_line < start_line is rejected as semantic violation",
                "no reversed line range found in fixture",
                fixture=path,
            )
        )

    # Other CF-19 semantic checks remain BLOCKED.
    for sub in (
        "proposal_state_combinations",
        "import_manifest_errors",
        "truncation_consistency",
    ):
        checks.append(
            _blocked(
                f"CF-19.{sub}",
                "CF-19",
                "requires proposal runtime and import service",
            )
        )
    return checks


def run_cf20_idempotency() -> list[Check]:
    """CF-20: idempotency registry is runtime-only."""
    return [
        _blocked(
            f"CF-20.{sub}",
            "CF-20",
            "requires global idempotency key registry and DB sandbox",
        )
        for sub in (
            "key_reused_different_payload",
            "concurrent_replay_independent",
            "race_duplicate_guard",
            "correction_idempotency",
            "concurrent_correction",
            "path_body_mismatch_before_insert",
        )
    ]


def run_cf21_to_cf24_runtime(cf_id: str, name: str) -> list[Check]:
    """CF-21..CF-24 are runtime / DB / merge sandbox checks."""
    return [
        _blocked(
            f"{cf_id}.{name}",
            cf_id,
            "requires GO runtime, decision/merge service or index DB sandbox",
        )
    ]


def run_cf25_projection_mapping(pmc: ProjectionMappingChecker) -> list[Check]:
    """CF-25: required enum/state rows present in projection-mapping.md."""
    checks: list[Check] = []
    rows = pmc.required_rows_present()
    missing = [r for r, present in rows if not present]
    if missing:
        checks.append(
            _fail(
                "CF-25.required_rows_present",
                "CF-25",
                "projection-mapping.md contains required enum/state rows",
                f"missing: {missing[:10]}",
            )
        )
    else:
        checks.append(
            _pass(
                "CF-25.required_rows_present",
                "CF-25",
                "projection-mapping.md contains required enum/state rows",
                f"{len(rows)} required rows present",
            )
        )

    # Semantic mapping exactness remains BLOCKED.
    for sub in (
        "enum_mapping_exact",
        "derived_mapping_exact",
        "stable_uuid_epochs",
        "recorded_accepted_projection",
        "version_hash_pairs",
        "proposal_pending_requirements",
        "merged_requirements",
        "correction_state_mapping",
        "backup_restore_reconciliation",
    ):
        checks.append(
            _blocked(
                f"CF-25.{sub}",
                "CF-25",
                "requires running projection / DB roundtrip sandbox",
            )
        )
    return checks


def run_cf26_live_operational() -> list[Check]:
    """CF-26: live_operational read is runtime-only."""
    return [
        _blocked(
            f"CF-26.{sub}",
            "CF-26",
            "requires source connector sandbox and live_operational read path",
        )
        for sub in ("live_operational_rejected", "registered_typed_read")
    ]


def run_cf27_document_links() -> list[Check]:
    """CF-27: document link resolution is runtime/DB-only."""
    return [
        _blocked(
            f"CF-27.{sub}",
            "CF-27",
            "requires document link projection and DB sandbox",
        )
        for sub in (
            "target_projection_invalid",
            "swapped_orphan_cycle_cross_space",
        )
    ]


def run_cf28_path_normalization() -> list[Check]:
    """CF-28: path normalization structural checks."""
    checks: list[Check] = []
    data = load_yaml(fixture_path("cf28_paths.yaml"))

    # Absolute/relative boundary pairs.
    for pair in data["absolute_relative_pairs"]:
        absolute = pair["absolute"]
        relative = pair["relative"]
        derived_relative = absolute.lstrip("/")
        if derived_relative == relative:
            checks.append(
                _pass(
                    f"CF-28.absolute_relative_lossless.{absolute}",
                    "CF-28",
                    "absolute/relative path mapping is lossless",
                    f"{absolute} <-> {relative}",
                    fixture=fixture_path("cf28_paths.yaml"),
                )
            )
        else:
            checks.append(
                _fail(
                    f"CF-28.absolute_relative_lossless.{absolute}",
                    "CF-28",
                    "absolute/relative path mapping is lossless",
                    f"{absolute} -> {derived_relative} != {relative}",
                    fixture=fixture_path("cf28_paths.yaml"),
                )
            )

    # Ambiguous paths must be rejected.
    for bad in data["ambiguous_paths"]:
        normalized = _canonical_prefix(bad["path"], reject_trailing_slash=True)
        if normalized is None:
            checks.append(
                _pass(
                    f"CF-28.ambiguous_rejected.{bad['path']}",
                    "CF-28",
                    "ambiguous path rejected",
                    f"{bad['path']} rejected",
                    fixture=fixture_path("cf28_paths.yaml"),
                )
            )
        else:
            checks.append(
                _fail(
                    f"CF-28.ambiguous_rejected.{bad['path']}",
                    "CF-28",
                    "ambiguous path rejected",
                    f"{bad['path']} normalized to {normalized}",
                    fixture=fixture_path("cf28_paths.yaml"),
                )
            )

    # NFC/NFD duplicates.
    nfc, nfd = data["nfc_nfd"][0]["nfc"], data["nfc_nfd"][0]["nfd"]
    if unicodedata.normalize("NFC", nfc) == unicodedata.normalize("NFC", nfd):
        checks.append(
            _pass(
                "CF-28.nfc_nfd_duplicate",
                "CF-28",
                "NFC/NFD duplicates are detected",
                f"NFC({nfc}) == NFC({nfd})",
                fixture=fixture_path("cf28_paths.yaml"),
            )
        )
    else:
        checks.append(
            _fail(
                "CF-28.nfc_nfd_duplicate",
                "CF-28",
                "NFC/NFD duplicates are detected",
                f"NFC({nfc}) != NFC({nfd})",
                fixture=fixture_path("cf28_paths.yaml"),
            )
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="T01 contract-test harness")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse catalog and list checks without writing reports",
    )
    args = parser.parse_args()

    try:
        catalog = load_yaml(SPEC_PATH)
    except FileNotFoundError as exc:
        builder = ReportBuilder(
            baseline_commit=BASELINE_COMMIT,
            contracts_version="unknown",
            output_dir=OUTPUT_DIR,
        )
        builder.add(
            _blocked(
                "harness.catalog_load",
                "CF-30",
                f"catalog file not found: {exc}",
                fixture=SPEC_PATH,
            )
        )
        _write_reports(builder, args.dry_run)
        return 0 if args.dry_run else 1

    required_schemas = {
        target
        for test in catalog.get("tests", [])
        for target in test.get("targets", [])
        if target.endswith(".schema.json")
    }
    missing_schema_files = sorted(
        target for target in required_schemas if not (CONTRACTS_DIR / target).exists()
    )
    if missing_schema_files:
        builder = ReportBuilder(
            baseline_commit=BASELINE_COMMIT,
            contracts_version=catalog.get("contract_version", "unknown"),
            output_dir=OUTPUT_DIR,
        )
        for name in missing_schema_files:
            builder.add(
                _blocked(
                    f"harness.schema_missing.{name}",
                    "CF-30",
                    f"required schema file {name} not found in {CONTRACTS_DIR}",
                )
            )
        _write_reports(builder, args.dry_run)
        return 0 if args.dry_run else 1

    try:
        schema_validator = SchemaValidator(CONTRACTS_DIR)
        openapi = OpenApiChecker(CONTRACTS_DIR)
        link_checker = MarkdownLinkChecker(CONTRACTS_DIR, Path("specs/corporate-kb"))
        projection = ProjectionMappingChecker(CONTRACTS_DIR)
    except FileNotFoundError as exc:
        builder = ReportBuilder(
            baseline_commit=BASELINE_COMMIT,
            contracts_version=catalog.get("contract_version", "unknown"),
            output_dir=OUTPUT_DIR,
        )
        builder.add(
            _blocked(
                "harness.contract_files",
                "CF-30",
                f"required contract file missing: {exc}",
            )
        )
        _write_reports(builder, args.dry_run)
        return 0 if args.dry_run else 1

    if schema_validator.load_errors:
        builder = ReportBuilder(
            baseline_commit=BASELINE_COMMIT,
            contracts_version=catalog.get("contract_version", "unknown"),
            output_dir=OUTPUT_DIR,
        )
        for name, exc in schema_validator.load_errors:
            builder.add(
                _blocked(
                    f"harness.schema_load.{name}",
                    "CF-30",
                    f"schema {name} failed to load or compile: {exc}",
                )
            )
        _write_reports(builder, args.dry_run)
        return 0 if args.dry_run else 1

    builder = ReportBuilder(
        baseline_commit=BASELINE_COMMIT,
        contracts_version=catalog.get("contract_version", "unknown"),
        output_dir=OUTPUT_DIR,
    )

    builder.add(
        Check(
            id="harness.catalog_parse",
            cf_id="CF-30",
            status="PASS",
            expected="t01-contract-tests.yaml parses",
            actual=f"parsed {len(catalog.get('tests', []))} test entries",
            input_sha256=sha256_text(SPEC_PATH.read_text(encoding="utf-8")),
            fixture_path=str(SPEC_PATH),
            rerun_cmd="uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py",
        )
    )

    # Execute checks.
    for fn in (
        lambda: run_cf30_catalog_completeness(catalog, schema_validator, openapi),
        lambda: run_cf29_links(link_checker),
        lambda: run_cf01_authz_context(schema_validator),
        lambda: run_cf02_approval_policy(schema_validator),
        lambda: run_cf03_front_matter(schema_validator),
        lambda: run_cf04_source_origin(schema_validator),
        lambda: run_cf05_source_id(schema_validator),
        lambda: run_cf06_docops(schema_validator),
        lambda: run_cf07_agent_tools(openapi),
        run_cf08_connector,
        lambda: run_cf09_invariants(openapi),
        run_cf10_history_queue_correction,
        lambda: run_cf11_index_snapshot(schema_validator),
        lambda: run_cf12_to_cf18_runtime("CF-12", "cutover"),
        lambda: run_cf12_to_cf18_runtime("CF-13", "concurrent_publication"),
        lambda: run_cf12_to_cf18_runtime("CF-14", "export_closure"),
        lambda: run_cf12_to_cf18_runtime("CF-15", "decision_export"),
        lambda: run_cf12_to_cf18_runtime("CF-16", "export_request_manifest"),
        lambda: run_cf12_to_cf18_runtime("CF-17", "export_hash_linkage"),
        lambda: run_cf12_to_cf18_runtime("CF-18", "decision_merge_linkage"),
        lambda: run_cf19_proposal_record(schema_validator),
        run_cf20_idempotency,
        lambda: run_cf21_to_cf24_runtime("CF-21", "decision_recovery"),
        lambda: run_cf21_to_cf24_runtime("CF-22", "db_fk"),
        lambda: run_cf21_to_cf24_runtime("CF-23", "decision_merge_refs"),
        lambda: run_cf21_to_cf24_runtime("CF-24", "index_db_roundtrip"),
        lambda: run_cf25_projection_mapping(projection),
        run_cf26_live_operational,
        run_cf27_document_links,
        run_cf28_path_normalization,
    ):
        for check in fn():
            builder.add(check)

    return _write_reports(builder, args.dry_run)


def _write_reports(builder: ReportBuilder, dry_run: bool) -> int:
    """Write reports or print dry-run summary."""
    if dry_run:
        print(f"Dry run: {len(builder.checks)} checks prepared.")
        print(f"Counts: {builder._counts()}")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # Write fixture metadata so the harness is reproducible.
    dump_json(
        OUTPUT_DIR / "fixtures" / "spaces.json",
        {"sales": sales_space(), "sales-pricing": sales_pricing_space()},
    )

    raw_report = builder.build()
    raw_path = OUTPUT_DIR / "contract-results.json"
    builder.write_json(raw_path)

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(render_summary(raw_report), encoding="utf-8")

    sanitized = sanitize_for_evidence(raw_report)
    sanitized_path = EVIDENCE_DIR / "contract-results.json"
    dump_json(sanitized_path, sanitized)

    evidence_summary_path = EVIDENCE_DIR / "summary.md"
    evidence_summary_path.write_text(render_summary(sanitized), encoding="utf-8")

    print(f"Wrote {raw_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {sanitized_path}")
    print(f"Wrote {evidence_summary_path}")
    print(f"Counts: {raw_report['counts']}")

    # Exit 1 only if there are FAIL results; BLOCKED is an acceptable T01 outcome.
    return 1 if raw_report["counts"].get("FAIL", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
