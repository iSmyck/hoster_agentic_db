# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T10a exact-SHA CI index build and validated preflight artifact harness."""

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
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t10a")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t10a")
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
            "schema_version": "t10a-index-build-results-v1",
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
            "command": "uv run python _bmad-output/test-artifacts/t10a/run_t10a_tests.py",
            "rerun_cmd": "uv run python _bmad-output/test-artifacts/t10a/run_t10a_tests.py",
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
        "# T10a Exact-SHA CI Index Build and Validated Preflight Artifact Evidence Summary",
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
            "Real GitLab/PostgreSQL/CI checks remain BLOCKED until their sandboxes and credentials exist. "
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t10a/run_t10a_tests.py",
        details=details,
    )


def is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _uuid(seed: int) -> str:
    return str(uuid.UUID(int=seed))


def make_snapshot(
    *,
    snapshot_id: str,
    space_id: str,
    repository_id: str,
    snapshot_sha: str,
    generation_id: str,
    profile_version: str,
    run_type: str,
    purpose: str,
    state: str,
    is_preflight: bool,
    serving_allowed: bool,
    cutover_sha: str | None,
    exact_sha256: str,
    semantic_sha256: str,
    closure_sha256: str,
    documents: list[dict[str, Any]],
    policy_bundle_id: str,
    access_policy_revision: str,
    approval_policy_revision: str,
    incremental_base_snapshot_sha: str | None = None,
    equivalence_evidence: dict[str, Any] | None = None,
    missing_inputs: list[str] | None = None,
    full_snapshot_equivalence: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic index-snapshot-v1 instance."""
    closure: dict[str, Any] = {
        "complete": missing_inputs is None or len(missing_inputs) == 0,
        "closure_sha256": closure_sha256,
        "incremental_base_snapshot_sha": incremental_base_snapshot_sha,
        "full_snapshot_equivalence": full_snapshot_equivalence or ("not_applicable" if run_type == "full" else "equivalent"),
        "missing_inputs": missing_inputs or [],
    }
    if equivalence_evidence is not None:
        closure["equivalence_evidence"] = equivalence_evidence
    snap: dict[str, Any] = {
        "schema_version": "index-snapshot-v1",
        "snapshot_id": snapshot_id,
        "space_id": space_id,
        "repository_id": repository_id,
        "target_branch": "main",
        "snapshot_sha": snapshot_sha,
        "main_generation": {
            "generation_id": generation_id,
            "ancestry_root_sha": snapshot_sha,
            "parent_generation_id": None,
            "history_rewrite_detected": False,
        },
        "index_profile_version": profile_version,
        "run_type": run_type,
        "purpose": purpose,
        "state": state,
        "preflight": {
            "is_preflight": is_preflight,
            "serving_allowed": serving_allowed,
            "cutover_sha": cutover_sha,
        },
        "exact_projection": {"status": "ready", "projection_sha256": exact_sha256},
        "semantic_projection": {"status": "ready", "projection_sha256": semantic_sha256},
        "documents": documents,
        "closure": closure,
        "policy_bundle_id": policy_bundle_id,
        "access_policy_revision": access_policy_revision,
        "approval_policy_revision": approval_policy_revision,
        "created_at": "2026-11-09T00:00:00Z",
    }
    return snap


def make_document(path: str, doc_id: str, revision_sha: str, eligible: bool = True) -> dict[str, Any]:
    content_sha = "0" * 64
    dep_sha = "1" * 64
    return {
        "document_id": doc_id,
        "path": path,
        "document_revision_sha": revision_sha,
        "content_sha256": content_sha,
        "dependency_sha256": dep_sha,
        "dependency_closure": {
            "closure_sha256": dep_sha,
            "inputs": [
                {"input_type": "document", "ref": path, "content_sha256": content_sha},
            ],
        },
        "eligible": eligible,
    }


def check_exact_sha_build(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        main_sha = inp.get("main_sha")
        resolved_sha = inp.get("resolved_sha")
        read_only = bool(inp.get("read_only"))
        webhook_hint_only = bool(inp.get("webhook_hint_only"))
        git_write = bool(inp.get("git_write_capability"))
        exact = is_git_sha(main_sha) and is_git_sha(resolved_sha) and main_sha == resolved_sha
        ok = exact and read_only and webhook_hint_only and not git_write
        details = {
            "main_sha": main_sha,
            "resolved_sha": resolved_sha,
            "read_only": read_only,
            "webhook_hint_only": webhook_hint_only,
            "git_write_capability": git_write,
        }
        if exp_status == "PASS":
            checks.append(_check(f"exact_sha_build.{name}.resolved", "exact_sha_build", "PASS" if ok else "FAIL",
                "CI resolves exact published main SHA via read-only credential",
                "exact SHA resolved" if ok else f"exact={exact}, read_only={read_only}, hint_only={webhook_hint_only}, git_write={git_write}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"exact_sha_build.{name}.rejected", "exact_sha_build", "FAIL" if not ok else "PASS",
                f"invalid build rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                "rejected" if not ok else "not rejected",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_preflight_artifact(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        snapshot_sha = inp.get("snapshot_sha")
        cutover_sha = inp.get("cutover_sha")
        is_preflight = bool(inp.get("is_preflight"))
        serving_allowed = bool(inp.get("serving_allowed"))
        purpose = inp.get("purpose")
        run_type = inp.get("run_type")
        state = inp.get("state")
        ok = (
            is_preflight
            and purpose == "cutover_preflight"
            and run_type == "full"
            and not serving_allowed
            and is_git_sha(snapshot_sha)
            and snapshot_sha == cutover_sha
            and state != "active"
        )
        details = {
            "snapshot_sha": snapshot_sha,
            "cutover_sha": cutover_sha,
            "is_preflight": is_preflight,
            "serving_allowed": serving_allowed,
            "purpose": purpose,
            "run_type": run_type,
            "state": state,
        }
        if exp_status == "PASS":
            checks.append(_check(f"preflight_artifact.{name}.inactive", "preflight_artifact", "PASS" if ok else "FAIL",
                "preflight artifact is inactive with snapshot_sha == cutover_sha and serving_allowed=false",
                "inactive preflight valid" if ok else f"ok={ok}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"preflight_artifact.{name}.rejected", "preflight_artifact", "FAIL" if not ok else "PASS",
                f"invalid preflight rejected with {exp.get('error', 'INVALID_STATE')}",
                "rejected" if not ok else "not rejected",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_index_snapshot_contract(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        snap = inp.get("snapshot", {})
        run_type = snap.get("run_type")
        closure = snap.get("closure", {})
        missing = closure.get("missing_inputs", [])
        equiv = closure.get("full_snapshot_equivalence")
        has_evidence = "equivalence_evidence" in closure
        gen = snap.get("main_generation", {})
        ordering = gen.get("ordering")
        perimeter = snap.get("space_id")
        profile = snap.get("index_profile_version")
        policy_bundle = snap.get("policy_bundle_id")
        access_rev = snap.get("access_policy_revision")
        approval_rev = snap.get("approval_policy_revision")
        exact = snap.get("exact_projection", {})
        semantic = snap.get("semantic_projection", {})
        ok = (
            is_git_sha(snap.get("snapshot_sha"))
            and is_git_sha(snap.get("snapshot_sha"))
            and is_sha256(exact.get("projection_sha256"))
            and is_sha256(semantic.get("projection_sha256"))
            and is_sha256(closure.get("closure_sha256"))
            and bool(perimeter)
            and bool(profile)
            and bool(policy_bundle)
            and is_git_sha(access_rev)
            and is_git_sha(approval_rev)
            and ordering != "lexicographic"
        )
        if run_type == "incremental":
            ok = ok and not missing and equiv == "equivalent" and has_evidence
        details = {
            "run_type": run_type,
            "missing_inputs": missing,
            "full_snapshot_equivalence": equiv,
            "has_equivalence_evidence": has_evidence,
            "ordering": ordering,
        }
        if exp_status == "PASS":
            checks.append(_check(f"index_snapshot_contract.{name}.valid", "index_snapshot_contract", "PASS" if ok else "FAIL",
                "snapshot contract has required SHAs, hashes, generation, profile and policy triple",
                "contract valid" if ok else f"contract invalid: {details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"index_snapshot_contract.{name}.rejected", "index_snapshot_contract", "FAIL" if not ok else "PASS",
                f"invalid contract rejected with {exp.get('error', 'DEPENDENCY_CLOSURE_MISMATCH')}",
                "rejected" if not ok else "not rejected",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_eligible_content_exclusion(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        docs = inp.get("documents", [])
        projected = [d for d in docs if d.get("projected")]
        ineligible_projected = [
            d for d in projected
            if d.get("ineligible_reason") or d.get("path", "").startswith(("inbox/", "templates/", "service/"))
            or d.get("archived") or d.get("deleted") or d.get("unverified_critical_media")
            or d.get("pending_branch") or d.get("rejected_branch")
        ]
        ok = not ineligible_projected
        details = {
            "total_documents": len(docs),
            "projected_count": len(projected),
            "ineligible_projected_count": len(ineligible_projected),
        }
        if exp_status == "PASS":
            checks.append(_check(f"eligible_content_exclusion.{name}.clean", "eligible_content_exclusion", "PASS" if ok else "FAIL",
                "only eligible canonical content enters projection",
                "exclusions clean" if ok else f"ineligible projected: {[d.get('path') for d in ineligible_projected]}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"eligible_content_exclusion.{name}.rejected", "eligible_content_exclusion", "FAIL" if not ok else "PASS",
                f"ineligible content rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "ineligible content detected" if not ok else "ineligible content not detected",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_idempotent_rebuild(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        duplicate = bool(inp.get("duplicate_webhook"))
        kb_index_lost = bool(inp.get("kb_index_lost"))
        same_sha = bool(inp.get("same_main_sha"))
        canonical_git_changed = bool(inp.get("canonical_git_changed"))
        new_active_created = bool(inp.get("new_active_created"))
        ok = (not canonical_git_changed) and (not new_active_created) and same_sha
        details = {
            "duplicate_webhook": duplicate,
            "kb_index_lost": kb_index_lost,
            "same_main_sha": same_sha,
            "canonical_git_changed": canonical_git_changed,
            "new_active_created": new_active_created,
        }
        if exp_status == "PASS":
            checks.append(_check(f"idempotent_rebuild.{name}.idempotent", "idempotent_rebuild", "PASS" if ok else "FAIL",
                "rebuild from Git + assets is idempotent and does not modify canonical Git or activate artifact",
                "idempotent" if ok else f"canonical_git_changed={canonical_git_changed}, new_active_created={new_active_created}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"idempotent_rebuild.{name}.rejected", "idempotent_rebuild", "FAIL" if not ok else "PASS",
                f"non-idempotent rebuild rejected with {exp.get('error', 'INVALID_STATE')}",
                "non-idempotent behavior detected" if not ok else "behavior was idempotent",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: SchemaValidator) -> list[Check]:
    checks: list[Check] = []
    main_sha = "a" * 40
    preflight = make_snapshot(
        snapshot_id=_uuid(1),
        space_id="sales",
        repository_id="repo-sales",
        snapshot_sha=main_sha,
        generation_id="gen-sales-1",
        profile_version="pgvector-fts-v1",
        run_type="full",
        purpose="cutover_preflight",
        state="ready",
        is_preflight=True,
        serving_allowed=False,
        cutover_sha=main_sha,
        exact_sha256="e" * 64,
        semantic_sha256="5" * 64,
        closure_sha256="c" * 64,
        documents=[make_document("pricing.md", _uuid(10), "b" * 40)],
        policy_bundle_id="sales-policy-bundle",
        access_policy_revision="d" * 40,
        approval_policy_revision="f" * 40,
    )
    err = schema_validator.validate_or_error("index-snapshot.schema.json", preflight)
    checks.append(_check("schema.preflight.valid", "schema", "PASS" if err is None else "FAIL",
        "sample preflight snapshot is schema valid", "schema valid" if err is None else err,
        details={"snapshot_id": preflight["snapshot_id"], "error": err}))

    published = make_snapshot(
        snapshot_id=_uuid(2),
        space_id="sales",
        repository_id="repo-sales",
        snapshot_sha=main_sha,
        generation_id="gen-sales-1",
        profile_version="pgvector-fts-v1",
        run_type="full",
        purpose="published",
        state="active",
        is_preflight=False,
        serving_allowed=True,
        cutover_sha=None,
        exact_sha256="e" * 64,
        semantic_sha256="5" * 64,
        closure_sha256="c" * 64,
        documents=[make_document("pricing.md", _uuid(10), "b" * 40)],
        policy_bundle_id="sales-policy-bundle",
        access_policy_revision="d" * 40,
        approval_policy_revision="f" * 40,
    )
    err = schema_validator.validate_or_error("index-snapshot.schema.json", published)
    checks.append(_check("schema.published.valid", "schema", "PASS" if err is None else "FAIL",
        "sample published active snapshot is schema valid", "schema valid" if err is None else err,
        details={"snapshot_id": published["snapshot_id"], "error": err}))

    lexicographic = copy.deepcopy(preflight)
    lexicographic["snapshot_id"] = _uuid(3)
    lexicographic["main_generation"] = {
        "generation_id": "gen-sales-1",
        "ancestry_root_sha": main_sha,
        "parent_generation_id": None,
        "history_rewrite_detected": False,
        "ordering": "lexicographic",
    }
    err = schema_validator.validate_or_error("index-snapshot.schema.json", lexicographic)
    checks.append(_check("schema.lexicographic_ordering.invalid", "schema", "PASS" if err is not None else "FAIL",
        "lexicographic generation ordering is rejected by schema", "schema rejected lexicographic ordering" if err is not None else "schema unexpectedly accepted lexicographic ordering",
        details={"snapshot_id": lexicographic["snapshot_id"], "error": err}))

    incremental_no_evidence = make_snapshot(
        snapshot_id=_uuid(4),
        space_id="sales",
        repository_id="repo-sales",
        snapshot_sha=main_sha,
        generation_id="gen-sales-1",
        profile_version="pgvector-fts-v1",
        run_type="incremental",
        purpose="published",
        state="active",
        is_preflight=False,
        serving_allowed=True,
        cutover_sha=None,
        exact_sha256="e" * 64,
        semantic_sha256="5" * 64,
        closure_sha256="c" * 64,
        documents=[make_document("pricing.md", _uuid(10), "b" * 40)],
        policy_bundle_id="sales-policy-bundle",
        access_policy_revision="d" * 40,
        approval_policy_revision="f" * 40,
        incremental_base_snapshot_sha="b" * 40,
        equivalence_evidence=None,
        full_snapshot_equivalence="equivalent",
    )
    err = schema_validator.validate_or_error("index-snapshot.schema.json", incremental_no_evidence)
    checks.append(_check("schema.incremental_no_evidence.invalid", "schema", "PASS" if err is not None else "FAIL",
        "incremental snapshot without equivalence_evidence is rejected by schema", "schema rejected incremental without evidence" if err is not None else "schema unexpectedly accepted incremental without evidence",
        details={"snapshot_id": incremental_no_evidence["snapshot_id"], "error": err}))

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
    parser = argparse.ArgumentParser(description="T10a Exact-SHA CI Index Build and Preflight Artifact")
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

    for sub in ['live_gitlab_exact_sha_build', 'live_gitlab_ci_no_write', 'live_postgres_kb_index_rebuild', 'live_object_store_acl']:
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
    raw_path = OUTPUT_DIR / "index-build-results.json"
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
    sanitized_path = EVIDENCE_DIR / "index-build-results.json"
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
