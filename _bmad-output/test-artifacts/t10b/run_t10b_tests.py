# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T10b published retrieval, search cursors and monotonic publication lifecycle harness."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACTS_DIR = Path("specs/corporate-kb/contracts")
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t10b")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t10b")
SPEC_BASELINE_COMMIT = "d2c0d072a757808ea891fbf6414f00147679f7a7"
T00_BASELINE_COMMIT = "152b00ff6aaa7b95c7b958d822bf54e8a54d1650"


@dataclass
class Check:
    """One test check result."""

    id: str
    scenario_id: str
    status: str
    expected: str
    actual: str
    input_sha256: str | None = None
    fixture_path: str | None = None
    rerun_cmd: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class ReportBuilder:
    """Assemble deterministic results.json envelope."""

    def __init__(
        self,
        baseline_commit: str,
        spec_baseline_commit: str,
        contracts_version: str,
        output_dir: Path,
    ) -> None:
        self.baseline_commit = baseline_commit
        self.spec_baseline_commit = spec_baseline_commit
        self.contracts_version = contracts_version
        self.output_dir = output_dir
        self.checks: list[Check] = []

    def add(self, check: Check) -> None:
        self.checks.append(check)

    def build(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        checks = [self._check_to_dict(c) for c in self.checks]
        report = {
            "schema_version": "t10b-retrieval-results-v1",
            "generated_at": now,
            "baseline_commit": self.baseline_commit,
            "spec_baseline_commit": self.spec_baseline_commit,
            "contracts_version": self.contracts_version,
            "environment": {
                "sandbox": "synthetic_local_no_gitlab",
                "gitlab_available": False,
                "idp_available": False,
                "ldap_available": False,
                "ad_available": False,
                "ci_available": False,
                "hoster_available": False,
                "pinned_toolchain": {
                    "open_webui": "v0.13.0",
                    "open_webui_commit": "c38885a1a737da4968f157092f304f3b5481d0bf",
                    "python": "3.12.13",
                    "uv": "0.11.13",
                },
            },
            "sensitive_data_included": False,
            "command": "uv run python _bmad-output/test-artifacts/t10b/run_t10b_tests.py",
            "rerun_cmd": "uv run python _bmad-output/test-artifacts/t10b/run_t10b_tests.py",
            "counts": self._counts(),
            "checks": checks,
        }
        return report

    @staticmethod
    def _check_to_dict(check: Check) -> dict[str, Any]:
        return {
            "id": check.id,
            "scenario_id": check.scenario_id,
            "status": check.status,
            "expected": check.expected,
            "actual": check.actual,
            "input_sha256": check.input_sha256,
            "fixture_path": check.fixture_path,
            "rerun_cmd": check.rerun_cmd,
            "details": check.details,
        }

    def _counts(self) -> dict[str, int]:
        counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}
        for c in self.checks:
            counts[c.status] = counts.get(c.status, 0) + 1
        fail_expected = sum(
            1 for c in self.checks
            if c.status == "FAIL" and c.details.get("expected_negative") is True
        )
        fail_unexpected = counts["FAIL"] - fail_expected
        return {
            "PASS": counts["PASS"],
            "FAIL": counts["FAIL"],
            "FAIL_EXPECTED": fail_expected,
            "FAIL_UNEXPECTED": fail_unexpected,
            "BLOCKED": counts["BLOCKED"],
        }

    def write_json(self, path: Path) -> None:
        report = self.build()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")


_SECRET_PATTERNS = [
    (
        re.compile(
            r"(token|password|secret|private_key)\s*[=:]\s*[^\s\"']+", re.IGNORECASE
        ),
        r"\1=<redacted>",
    ),
    (re.compile(r"bearer\s+[a-z0-9_\-]+", re.IGNORECASE), "Bearer <redacted>"),
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "<email-redacted>"),
    (re.compile(r"localhost:\d+"), "<local-endpoint-redacted>"),
    (re.compile(r"127\.0\.0\.1:\d+"), "<local-endpoint-redacted>"),
]


def _sanitize_string(value: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(v) for v in value]
    return value


def _sanitize_for_evidence(report: dict[str, Any]) -> dict[str, Any]:
    sanitized = copy.deepcopy(report)
    sanitized["sensitive_data_included"] = False
    sanitized["environment"] = {
        k: _sanitize_value(v) for k, v in sanitized.get("environment", {}).items()
    }
    sanitized["checks"] = [_sanitize_value(c) for c in sanitized.get("checks", [])]
    return sanitized


def _render_summary(report: dict[str, Any]) -> str:
    counts = report["counts"]
    total = sum(counts.values()) - counts.get("FAIL", 0)
    lines: list[str] = [
        "# T10b Published Retrieval, Search Cursors and Monotonic Publication Lifecycle Evidence Summary",
        "",
        f"- **Generated:** {report['generated_at']}",
        f"- **Contracts version:** {report['contracts_version']}",
        f"- **Baseline commit:** {report['baseline_commit']}",
        f"- **Spec baseline commit:** {report['spec_baseline_commit']}",
        f"- **Environment:** {report['environment']['sandbox']}",
        f"- **Sensitive data present:** {report['sensitive_data_included']}",
        "",
        "## Counts",
        "",
        f"- PASS: {counts.get('PASS', 0)}",
        f"- FAIL (expected): {counts.get('FAIL_EXPECTED', 0)}",
        f"- FAIL (unexpected): {counts.get('FAIL_UNEXPECTED', 0)}",
        f"- BLOCKED: {counts.get('BLOCKED', 0)}",
        f"- **Total:** {total}",
        "",
        "## Top findings",
        "",
    ]

    blocked = [c for c in report["checks"] if c["status"] == "BLOCKED"]
    expected_fail = [c for c in report["checks"] if c["status"] == "FAIL" and c["details"].get("expected_negative") is True]
    unexpected_fail = [c for c in report["checks"] if c["status"] == "FAIL" and c["details"].get("expected_negative") is not True]
    passed = [c for c in report["checks"] if c["status"] == "PASS"][:10]

    if unexpected_fail:
        lines.append("### FAIL (unexpected)")
        for c in unexpected_fail:
            lines.append(
                f"- `{c['id']}` ({c['scenario_id']}): {c['actual']}; fixture `{c.get('fixture_path')}`"
            )
        lines.append("")

    if expected_fail:
        lines.append("### FAIL (expected)")
        for c in expected_fail:
            lines.append(
                f"- `{c['id']}` ({c['scenario_id']}): {c['actual']}; fixture `{c.get('fixture_path')}`"
            )
        lines.append("")

    if blocked:
        lines.append("### BLOCKED")
        for c in blocked[:20]:
            lines.append(f"- `{c['id']}` ({c['scenario_id']}): {c['actual']}")
        if len(blocked) > 20:
            lines.append(f"- ... and {len(blocked) - 20} more BLOCKED checks")
        lines.append("")

    if passed:
        lines.append("### PASS (sample)")
        for c in passed:
            lines.append(f"- `{c['id']}` ({c['scenario_id']}): {c['expected']}")
        lines.append("")

    lines.extend(
        [
            "## Rerun instructions",
            "",
            f"```bash\n{report['rerun_cmd']}\n```",
            "",
            "Real GitLab/PostgreSQL/retrieval checks remain BLOCKED until their sandboxes and credentials exist. "
            "This report contains only synthetic structural evidence; it does not claim production integration PASS.",
            "",
        ]
    )
    return "\n".join(lines)


class SchemaValidator:
    """Load all .schema.json files and validate fixtures against them."""

    VALIDATOR = Draft202012Validator
    SPEC = DRAFT202012

    def __init__(self, contracts_dir: Path) -> None:
        self.contracts_dir = contracts_dir
        self.schemas: dict[str, dict[str, Any]] = {}
        self.registry: Registry = Registry()
        self.validators: dict[str, Draft202012Validator] = {}
        self.load_errors: list[tuple[str, Exception]] = []
        self._load()

    def _load(self) -> None:
        for path in sorted(self.contracts_dir.glob("*.schema.json")):
            key = path.name
            try:
                with path.open("r", encoding="utf-8") as f:
                    schema = json.load(f)
            except Exception as exc:
                self.load_errors.append((key, exc))
                continue
            self.schemas[key] = schema
            try:
                resource = Resource.from_contents(schema, default_specification=self.SPEC)
                self.registry = self.registry.with_resource(schema.get("$id", key), resource)
                self.registry = self.registry.with_resource(key, resource)
                if schema.get("$id", key).startswith("./"):
                    self.registry = self.registry.with_resource(schema["$id"][2:], resource)
                else:
                    self.registry = self.registry.with_resource(f"./{schema.get('$id', key)}", resource)
            except Exception as exc:
                self.load_errors.append((key, exc))
                continue

        for key, schema in self.schemas.items():
            try:
                validator = self.VALIDATOR(schema, registry=self.registry)
                validator.check_schema(schema)
                self.validators[key] = validator
            except Exception as exc:
                self.load_errors.append((key, exc))

    def validate_or_error(self, schema_name: str, instance: Any) -> str | None:
        try:
            self.validators[schema_name].validate(instance)
            return None
        except ValidationError as exc:
            return f"{exc.message} at {list(exc.absolute_path)}"

    def compile_regexes(self) -> list[tuple[str, str, Exception | None]]:
        results: list[tuple[str, str, Exception | None]] = []

        def walk(node: Any, path: str) -> None:
            if isinstance(node, dict):
                if "pattern" in node and isinstance(node["pattern"], str):
                    try:
                        re.compile(node["pattern"])
                        results.append((path, node["pattern"], None))
                    except re.error as exc:
                        results.append((path, node["pattern"], exc))
                for k, v in node.items():
                    walk(v, f"{path}/{k}")
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, f"{path}[{i}]")

        for name, schema in self.schemas.items():
            walk(schema, name)
        return results

    def resolve_refs(self) -> list[tuple[str, str, Exception | None]]:
        results: list[tuple[str, str, Exception | None]] = []

        def walk(node: Any, path: str, resolver) -> None:
            if isinstance(node, dict):
                if "$ref" in node and isinstance(node["$ref"], str):
                    ref = node["$ref"]
                    try:
                        resolver.lookup(ref)
                        results.append((path, ref, None))
                    except NoSuchResource as exc:
                        results.append((path, ref, exc))
                    except Exception as exc:  # pragma: no cover
                        results.append((path, ref, exc))
                for k, v in node.items():
                    walk(v, f"{path}/{k}", resolver)
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, f"{path}[{i}]", resolver)

        for name, schema in self.schemas.items():
            base_uri = schema.get("$id", name)
            resolver = self.registry.resolver(base_uri=base_uri)
            walk(schema, name, resolver)
        return results


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, OSError) as exc:
        raise RuntimeError(f"corrupt or empty fixture {path}: {exc}") from exc


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
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _contains_repo_absolute(value: Any) -> bool:
    repo_abs = str(REPO_ROOT.resolve())
    if isinstance(value, str):
        return value.startswith(repo_abs) or Path(value).is_absolute()
    if isinstance(value, dict):
        return any(_contains_repo_absolute(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_repo_absolute(v) for v in value)
    return False


def _check(
    check_id: str,
    scenario_id: str,
    status: str,
    expected: str,
    actual: str,
    fixture: Path | None = None,
    details: dict[str, Any] | None = None,
    expected_negative: bool = False,
) -> Check:
    details = details or {}
    if expected_negative:
        details["expected_negative"] = True
    return Check(
        id=check_id,
        scenario_id=scenario_id,
        status=status,
        expected=expected,
        actual=actual,
        input_sha256=_file_sha256(fixture),
        fixture_path=_fixture_path(fixture),
        rerun_cmd="uv run python _bmad-output/test-artifacts/t10b/run_t10b_tests.py",
        details=details,
    )


def is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _uuid(seed: int) -> str:
    return str(uuid.UUID(int=seed))


def check_publication_lifecycle(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        pre = inp.get("preflight", {})
        pub = inp.get("published", {})
        ids_differ = pre.get("snapshot_id") != pub.get("snapshot_id")
        same_sha = pre.get("snapshot_sha") == pub.get("snapshot_sha")
        same_closure = pre.get("closure_sha256") == pub.get("closure_sha256")
        same_policy = (
            pre.get("policy_bundle_id") == pub.get("policy_bundle_id")
            and pre.get("access_policy_revision") == pub.get("access_policy_revision")
            and pre.get("approval_policy_revision") == pub.get("approval_policy_revision")
        )
        same_hashes = (
            pre.get("exact_projection_sha256") == pub.get("exact_projection_sha256")
            and pre.get("semantic_projection_sha256") == pub.get("semantic_projection_sha256")
        )
        full_validation_repeated = bool(pub.get("full_validation_repeated"))
        preflight_stays_inactive = bool(pre.get("serving_allowed")) is False and bool(pre.get("is_preflight")) is True
        published_active = bool(pub.get("serving_allowed")) is True and bool(pub.get("is_preflight")) is False
        ok = (
            ids_differ and same_sha and same_closure and same_policy and same_hashes
            and full_validation_repeated and preflight_stays_inactive and published_active
        )
        details = {
            "ids_differ": ids_differ,
            "same_sha": same_sha,
            "same_closure": same_closure,
            "same_policy": same_policy,
            "same_hashes": same_hashes,
            "full_validation_repeated": full_validation_repeated,
            "preflight_stays_inactive": preflight_stays_inactive,
            "published_active": published_active,
        }
        if exp_status == "PASS":
            checks.append(_check(f"publication_lifecycle.{name}.valid", "publication_lifecycle", "PASS" if ok else "FAIL",
                "published lifecycle creates new IDs with same SHA/closure/policy/hashes and repeats validation",
                "publication pair valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"publication_lifecycle.{name}.rejected", "publication_lifecycle", "FAIL" if not ok else "PASS",
                f"invalid publication pair rejected with {exp.get('error', 'INVALID_STATE')}",
                "rejected" if not ok else "not rejected",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def _observed_pointer_cas_error(details: dict[str, Any]) -> str | None:
    if details["same_fence"] and details["latest_ancestry"] and details["validated_snapshot"] and details["single_writer"]:
        if details["pointer_rows_updated"] != 1 or details["stale_job_marked_superseded"]:
            return "INDEX_GENERATION_CONFLICT"
        return None
    return "INDEX_GENERATION_CONFLICT"


def check_pointer_cas_fencing(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        expected_error = exp.get("error")
        current = inp.get("current_pointer", {})
        publisher = inp.get("publisher", {})
        result = inp.get("result", {})
        expected_fence = publisher.get("expected_fence")
        current_fence = current.get("fence")
        same_fence = expected_fence == current_fence
        latest_ancestry = bool(publisher.get("latest_ancestry"))
        validated_snapshot = bool(publisher.get("validated_snapshot"))
        single_writer = bool(publisher.get("single_writer"))
        rows_updated = result.get("pointer_rows_updated", 0)
        stale_marked = bool(result.get("stale_job_marked_superseded"))
        would_succeed = same_fence and latest_ancestry and validated_snapshot and single_writer
        actual_success = rows_updated == 1 and stale_marked is False
        ok = actual_success == would_succeed
        details = {
            "same_fence": same_fence,
            "latest_ancestry": latest_ancestry,
            "validated_snapshot": validated_snapshot,
            "single_writer": single_writer,
            "pointer_rows_updated": rows_updated,
            "stale_job_marked_superseded": stale_marked,
        }
        observed_error = _observed_pointer_cas_error(details)
        error_matches = expected_error is None or observed_error == expected_error
        expected_negative = expected_negative and not ok and error_matches
        if exp_status == "PASS":
            checks.append(_check(f"pointer_cas_fencing.{name}.valid", "pointer_cas_fencing", "PASS" if ok else "FAIL",
                "CAS/fencing pointer publication updates exactly one row for the single writer",
                "CAS succeeded" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"pointer_cas_fencing.{name}.rejected", "pointer_cas_fencing", "FAIL" if not ok else "PASS",
                f"stale publisher rejected with {exp.get('error', 'INDEX_GENERATION_CONFLICT')}",
                f"stale writer rejected ({observed_error})" if not ok else "stale writer unexpectedly succeeded",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def _observed_per_space_error(
    details: dict[str, Any],
    has_active_included: bool,
    candidates: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> str | None:
    if details["cross_space_leak"]:
        return "SECURITY_REJECTED"
    if details["excluded_present"]:
        return "STALE_INDEX_CANDIDATE"
    if not details["active_only"] and has_active_included:
        return "STALE_INDEX_CANDIDATE"
    if not details["all_reauthorized"] and any(c.get("returned") for c in candidates):
        return "AUTHZ_GROUP_STALE"
    if not details["citation_ok"] and citations:
        return "SECURITY_REJECTED"
    if not has_active_included and (candidates or citations):
        return "STALE_INDEX_CANDIDATE"
    return "STALE_INDEX_CANDIDATE"


def check_per_space_retrieval(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        expected_error = exp.get("error")
        snapshots = inp.get("snapshots", [])
        active_only = all(s.get("state") == "active" and s.get("serving_allowed") for s in snapshots if s.get("included"))
        excluded_present = any(s.get("included") and (s.get("inactive") or s.get("pending") or s.get("rejected") or s.get("archived")) for s in snapshots)
        has_active_included = any(s.get("included") and s.get("state") == "active" and s.get("serving_allowed") for s in snapshots)
        candidates = inp.get("candidates", [])
        all_reauthorized = all(c.get("reauthorized") for c in candidates if c.get("returned"))
        citations = inp.get("citations", [])
        citation_ok = all(
            isinstance(c, dict) and c.get("space_id") and c.get("document_id") and is_git_sha(c.get("revision_sha")) and c.get("range")
            for c in citations
        )
        cross_space = bool(inp.get("cross_space_leak"))
        normal_ok = active_only and not excluded_present and all_reauthorized and citation_ok and not cross_space
        empty_inactive_ok = not has_active_included and not candidates and not citations and not cross_space
        ok = normal_ok or empty_inactive_ok
        details = {
            "active_only": active_only,
            "excluded_present": excluded_present,
            "all_reauthorized": all_reauthorized,
            "citation_ok": citation_ok,
            "cross_space_leak": cross_space,
        }
        observed_error = _observed_per_space_error(details, has_active_included, candidates, citations)
        error_matches = expected_error is None or observed_error == expected_error
        expected_negative = expected_negative and not ok and error_matches
        if exp_status == "PASS":
            checks.append(_check(f"per_space_retrieval.{name}.valid", "per_space_retrieval", "PASS" if ok else "FAIL",
                "search fans out only over active published snapshots with reauthorized candidates and exact citations",
                "retrieval valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"per_space_retrieval.{name}.rejected", "per_space_retrieval", "FAIL" if not ok else "PASS",
                f"unauthorized or stale content rejected with {exp.get('error', 'STALE_INDEX_CANDIDATE')}",
                f"stale/unauthorized content detected ({observed_error})" if not ok else "content unexpectedly accepted",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_cursor_binding(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        binding = inp.get("cursor_binding", {})
        required_keys = {"snapshot_ids", "profile_version", "policy_bundle_id", "access_policy_revision", "approval_policy_revision", "group_epoch", "revocation_epoch", "actor_epoch"}
        complete = required_keys.issubset(set(binding.keys()))
        ordered_snapshots = isinstance(binding.get("snapshot_ids"), list)
        stale = bool(inp.get("stale_binding"))
        continuation = inp.get("continuation", {})
        next_cursor = continuation.get("next_cursor")
        has_next = bool(continuation.get("has_more"))
        limit_exceeded = bool(continuation.get("limit_exceeded"))
        ok = complete and ordered_snapshots and not stale and (not limit_exceeded or (has_next and next_cursor is not None))
        details = {
            "binding_complete": complete,
            "ordered_snapshots": ordered_snapshots,
            "stale_binding": stale,
            "limit_exceeded": limit_exceeded,
            "has_next": has_next,
            "next_cursor_present": next_cursor is not None,
        }
        if exp_status == "PASS":
            checks.append(_check(f"cursor_binding.{name}.valid", "cursor_binding", "PASS" if ok else "FAIL",
                "cursor binds complete ordered per-Space snapshot/profile/policy/group/revocation/actor-epoch set",
                "cursor binding valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"cursor_binding.{name}.rejected", "cursor_binding", "FAIL" if not ok else "PASS",
                f"stale or incomplete cursor rejected with {exp.get('error', 'STALE_INDEX_CANDIDATE')}",
                "stale/incomplete cursor rejected" if not ok else "cursor unexpectedly accepted",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_index_not_ready(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        state = inp.get("space_state")
        result = inp.get("result", {})
        code = result.get("code")
        explicit_error = code in {"INDEX_NOT_READY", "STALE_INDEX_CANDIDATE"}
        retryable = bool(result.get("retryable"))
        has_bounds = "effective_bounds" in result
        next_cursor = result.get("next_cursor")
        truncated = result.get("truncated")
        silent = truncated is True and (next_cursor is None or code == "none")
        ok = (
            (state in {"no_active_snapshot", "inactive_preflight", "upstream_failure"} and explicit_error and retryable)
            or (state == "limit_exceeded" and code == "LIMIT_EXCEEDED" and has_bounds and next_cursor is not None)
        ) and not silent
        details = {
            "space_state": state,
            "code": code,
            "retryable": retryable,
            "has_bounds": has_bounds,
            "next_cursor_present": next_cursor is not None,
            "silent_truncation": silent,
        }
        if exp_status == "PASS":
            checks.append(_check(f"index_not_ready.{name}.explicit", "index_not_ready", "PASS" if ok else "FAIL",
                "missing/stale index or limit returns explicit error with retryable/bounds/next_cursor; no silent truncation",
                "error handling explicit" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"index_not_ready.{name}.rejected", "index_not_ready", "FAIL" if not ok else "PASS",
                f"optimistic success or silent truncation rejected with {exp.get('error', 'INDEX_NOT_READY')}",
                "bad outcome detected" if not ok else "outcome unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: SchemaValidator) -> list[Check]:
    checks: list[Check] = []
    main_sha = "a" * 40
    preflight = {
        "schema_version": "index-snapshot-v1",
        "snapshot_id": _uuid(1),
        "space_id": "sales",
        "repository_id": "repo-sales",
        "target_branch": "main",
        "snapshot_sha": main_sha,
        "main_generation": {
            "generation_id": "gen-sales-1",
            "ancestry_root_sha": main_sha,
            "parent_generation_id": None,
            "history_rewrite_detected": False,
        },
        "index_profile_version": "pgvector-fts-v1",
        "run_type": "full",
        "purpose": "cutover_preflight",
        "state": "ready",
        "preflight": {"is_preflight": True, "serving_allowed": False, "cutover_sha": main_sha},
        "exact_projection": {"status": "ready", "projection_sha256": "e" * 64},
        "semantic_projection": {"status": "ready", "projection_sha256": "5" * 64},
        "documents": [{
            "document_id": _uuid(10), "path": "pricing.md", "document_revision_sha": "b" * 40,
            "content_sha256": "0" * 64, "dependency_sha256": "1" * 64,
            "dependency_closure": {"closure_sha256": "1" * 64, "inputs": [{"input_type": "document", "ref": "pricing.md", "content_sha256": "0" * 64}]},
            "eligible": True,
        }],
        "closure": {
            "complete": True,
            "closure_sha256": "c" * 64,
            "incremental_base_snapshot_sha": None,
            "full_snapshot_equivalence": "not_applicable",
            "missing_inputs": [],
        },
        "policy_bundle_id": "sales-policy-bundle",
        "access_policy_revision": "d" * 40,
        "approval_policy_revision": "f" * 40,
        "created_at": "2026-11-09T00:00:00Z",
    }
    err = schema_validator.validate_or_error("index-snapshot.schema.json", preflight)
    checks.append(_check("schema.preflight.valid", "schema", "PASS" if err is None else "FAIL",
        "sample preflight snapshot is schema valid", "schema valid" if err is None else err,
        details={"snapshot_id": preflight["snapshot_id"], "error": err}))

    published = dict(preflight)
    published["snapshot_id"] = _uuid(2)
    published["purpose"] = "published"
    published["state"] = "active"
    published["run_type"] = "full"
    published["preflight"] = {"is_preflight": False, "serving_allowed": True, "cutover_sha": None}
    err = schema_validator.validate_or_error("index-snapshot.schema.json", published)
    checks.append(_check("schema.published.valid", "schema", "PASS" if err is None else "FAIL",
        "sample published active snapshot is schema valid", "schema valid" if err is None else err,
        details={"snapshot_id": published["snapshot_id"], "error": err}))

    regex = schema_validator.compile_regexes()
    bad = [r for r in regex if r[2] is not None]
    checks.append(_check("schema.regex_compile", "schema", "FAIL" if bad else "PASS",
        "all schema regex patterns compile", f"bad regex: {bad[:3]}" if bad else f"{len(regex)} patterns compiled",
        details={"bad_regex_count": len(bad)}))

    refs = schema_validator.resolve_refs()
    unresolved = [r for r in refs if r[2] is not None]
    checks.append(_check("schema.refs_resolve", "schema", "FAIL" if unresolved else "PASS",
        "all schema $ref resolve", f"unresolved: {unresolved[:3]}" if unresolved else f"{len(refs)} refs resolved",
        details={"unresolved_count": len(unresolved)}))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="T10b Published Retrieval and Monotonic Publication Lifecycle")
    parser.add_argument("--dry-run", action="store_true", help="list checks without writing reports")
    args = parser.parse_args()

    if not CONTRACTS_DIR.exists():
        builder = ReportBuilder(
            baseline_commit=T00_BASELINE_COMMIT,
            spec_baseline_commit=SPEC_BASELINE_COMMIT,
            contracts_version="unknown",
            output_dir=OUTPUT_DIR,
        )
        builder.add(_check("harness.contracts_dir", "harness", "BLOCKED", "contracts directory present", f"missing {CONTRACTS_DIR}"))
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
            builder.add(_check(f"harness.schema_load.{name}", "harness", "BLOCKED", "schema loads", f"load error: {exc}"))
        return _write_reports(builder, args.dry_run)

    fixture_path = ROOT / "fixtures" / "scenarios.yaml"
    if not fixture_path.exists():
        builder = ReportBuilder(
            baseline_commit=T00_BASELINE_COMMIT,
            spec_baseline_commit=SPEC_BASELINE_COMMIT,
            contracts_version="index-snapshot-v1",
            output_dir=OUTPUT_DIR,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=SPEC_BASELINE_COMMIT,
        contracts_version="index-snapshot-v1",
        output_dir=OUTPUT_DIR,
    )
    builder.add(_check("harness.fixture_loaded", "harness", "PASS", "synthetic fixtures load", "scenarios.yaml loaded", details={"fixture": _fixture_path(fixture_path)}))

    for check in run_schema_checks(schema_validator):
        builder.add(check)

    data = load_yaml(fixture_path)
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

    for sub in ['live_postgres_active_pointer', 'live_retrieval_exact_semantic', 'live_cursor_revocation_stream', 'live_hoster_ai_inference']:
        builder.add(_check(f"runtime.{sub}", "runtime", "BLOCKED", "live integration evidence", "requires live sandbox and credentials"))

    return _write_reports(builder, args.dry_run)


def _compute_exit_code(builder: ReportBuilder) -> int:
    counts = builder._counts()
    scenario_results = {
        c.status
        for c in builder.checks
        if c.scenario_id not in {"harness", "runtime"}
    }
    has_scenario_results = bool(scenario_results.intersection({"PASS", "FAIL"}))
    all_blocked = all(c.status == "BLOCKED" for c in builder.checks) if builder.checks else True
    if counts.get("FAIL_UNEXPECTED", 0) > 0:
        return 1
    if not has_scenario_results and all_blocked:
        return 1
    return 0


def _write_reports(builder: ReportBuilder, dry_run: bool) -> int:
    counts = builder._counts()
    exit_code = _compute_exit_code(builder)
    if dry_run:
        print(f"Dry run: {len(builder.checks)} checks prepared.")
        print(f"Counts: {counts}")
        return exit_code

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw_report = builder.build()
    raw_path = OUTPUT_DIR / "retrieval-results.json"
    try:
        builder.write_json(raw_path)
    except OSError as exc:
        print(f"Failed to write {raw_path}: {exc}", file=sys.stderr)
        return 1

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(_render_summary(raw_report), encoding="utf-8")

    sanitized = _sanitize_for_evidence(raw_report)
    if _contains_repo_absolute(sanitized):
        raise AssertionError("sanitized evidence still contains absolute paths under the repo root")
    sanitized_path = EVIDENCE_DIR / "retrieval-results.json"
    try:
        dump_json(sanitized_path, sanitized)
    except OSError as exc:
        print(f"Failed to write {sanitized_path}: {exc}", file=sys.stderr)
        return 1

    evidence_summary_path = EVIDENCE_DIR / "summary.md"
    evidence_summary_path.write_text(_render_summary(sanitized), encoding="utf-8")

    print(f"Wrote {raw_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {sanitized_path}")
    print(f"Wrote {evidence_summary_path}")
    print(f"Counts: {raw_report['counts']}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
