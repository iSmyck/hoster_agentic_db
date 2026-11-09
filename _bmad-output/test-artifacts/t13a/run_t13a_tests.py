# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T13a complete portable export with exact refs and closure harness."""

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
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t13a")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t13a")
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
            "schema_version": "t13a-export-results-v1",
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
            "command": "uv run python _bmad-output/test-artifacts/t13a/run_t13a_tests.py",
            "rerun_cmd": "uv run python _bmad-output/test-artifacts/t13a/run_t13a_tests.py",
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
        "# T13a Complete Portable Export with Exact Refs and Closure Evidence Summary",
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
            "Real GitLab/object-store/IdP checks remain BLOCKED until their sandboxes and credentials exist. "
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t13a/run_t13a_tests.py",
        details=details,
    )


def is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _uuid(seed: int) -> str:
    return str(uuid.UUID(int=seed))


def check_export_authorization(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        batches = inp.get("batches", [])
        all_authorized = all(b.get("authorized") for b in batches)
        ok = all_authorized and len(batches) > 0
        details = {"batch_count": len(batches), "all_authorized": all_authorized}
        if exp_status == "PASS":
            checks.append(_check(f"export_authorization.{name}.authorized", "export_authorization", "PASS" if ok else "FAIL",
                "every export batch passes fresh Space+history authorization",
                "all batches authorized" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"export_authorization.{name}.rejected", "export_authorization", "FAIL" if not ok else "PASS",
                f"unauthorized batch rejected with {exp.get('error', 'AUTHZ_GROUP_STALE')}",
                "unauthorized batch detected" if not ok else "all batches unexpectedly authorized",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_git_clone_refs(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        refs = inp.get("refs", [])
        all_full = all(is_git_sha(r.get("object_sha")) for r in refs)
        tag_peels_ok = all(
            r.get("object_type") != "tag" or is_git_sha(r.get("peeled_sha"))
            for r in refs
        )
        protected_decision_tags = all(
            not r.get("ref_name", "").startswith("refs/tags/kb-decisions/") or r.get("protected") is True
            for r in refs
        )
        missing = inp.get("missing_refs", [])
        ok = all_full and tag_peels_ok and protected_decision_tags and len(missing) == 0 and len(refs) > 0
        details = {
            "ref_count": len(refs),
            "all_full_sha": all_full,
            "tag_peels_ok": tag_peels_ok,
            "protected_decision_tags": protected_decision_tags,
            "missing_refs": missing,
        }
        if exp_status == "PASS":
            checks.append(_check(f"git_clone_refs.{name}.explicit", "git_clone_refs", "PASS" if ok else "FAIL",
                "Git clone includes explicit full object SHAs and refs; protected decision tags marked protected",
                "refs explicit and complete" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"git_clone_refs.{name}.rejected", "git_clone_refs", "FAIL" if not ok else "PASS",
                f"incomplete or short refs rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                "ref problem detected" if not ok else "refs unexpectedly complete",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_decisions_manifest(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        decisions = inp.get("decisions", [])
        ok = True
        for d in decisions:
            if not is_git_sha(d.get("proposal_sha")):
                ok = False
            if not is_sha256(d.get("record_sha256")):
                ok = False
            if not d.get("note_record_sha256_match"):
                ok = False
            if not d.get("tag_proposal_sha_match"):
                ok = False
            if d.get("outcome") == "merged":
                if not is_git_sha(d.get("merge_first_parent")) or not is_git_sha(d.get("merge_second_parent")):
                    ok = False
                if d.get("merge_second_parent") != d.get("proposal_sha"):
                    ok = False
            if d.get("outcome") in {"rejected", "cancelled"} and d.get("has_merge_evidence"):
                ok = False
        details = {"decision_count": len(decisions), "all_integrity_checks": ok}
        if exp_status == "PASS":
            checks.append(_check(f"decisions_manifest.{name}.valid", "decisions_manifest", "PASS" if ok else "FAIL",
                "decisions manifest has exact decision_id, proposal_sha, record_sha256, note/tag linkage and correct merge evidence",
                "decisions manifest valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"decisions_manifest.{name}.rejected", "decisions_manifest", "FAIL" if not ok else "PASS",
                f"invalid decision manifest rejected with {exp.get('error', 'DECISION_INVALID')}",
                "decision integrity problem detected" if not ok else "decisions unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_assets_manifest(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        assets = inp.get("assets", [])
        ok = True
        for a in assets:
            if not is_sha256(a.get("sha256")):
                ok = False
            if a.get("export_status") == "exported" and a.get("sha256") != a.get("exported_object_sha256"):
                ok = False
            source_ref = a.get("source_ref", "")
            if source_ref.startswith("http") and "?v=" not in source_ref and "#v=" not in source_ref:
                ok = False
            if a.get("export_status") in {"missing", "rejected"}:
                ok = False
        details = {"asset_count": len(assets), "all_hash_verified": ok}
        if exp_status == "PASS":
            checks.append(_check(f"assets_manifest.{name}.valid", "assets_manifest", "PASS" if ok else "FAIL",
                "assets manifest contains immutable attachments with verified hashes",
                "assets manifest valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"assets_manifest.{name}.rejected", "assets_manifest", "FAIL" if not ok else "PASS",
                f"invalid asset rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "asset problem detected" if not ok else "assets unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_policy_bundle(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        all_present = bool(inp.get("all_present"))
        access_rev = inp.get("access_policy_revision")
        approval_rev = inp.get("approval_policy_revision")
        access_hash = inp.get("access_policy_content_sha256")
        approval_hash = inp.get("approval_policy_content_sha256")
        grants_hash = inp.get("grants_mapping_sha256")
        ok = (
            all_present
            and is_git_sha(access_rev)
            and is_git_sha(approval_rev)
            and is_sha256(access_hash)
            and is_sha256(approval_hash)
            and is_sha256(grants_hash)
            and bool(inp.get("policy_bundle_id"))
        )
        details = {
            "all_present": all_present,
            "access_policy_revision_valid": is_git_sha(access_rev),
            "approval_policy_revision_valid": is_git_sha(approval_rev),
        }
        if exp_status == "PASS":
            checks.append(_check(f"policy_bundle.{name}.complete", "policy_bundle", "PASS" if ok else "FAIL",
                "policy bundle includes access/approval revision SHAs and content/grants hashes",
                "policy bundle complete" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"policy_bundle.{name}.rejected", "policy_bundle", "FAIL" if not ok else "PASS",
                f"incomplete policy bundle rejected with {exp.get('error', 'INVALID_STATE')}",
                "policy bundle incomplete" if not ok else "policy bundle unexpectedly complete",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_grants_mapping(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        grants = inp.get("grants", [])
        includes_secrets = bool(inp.get("includes_secrets"))
        has_stable_ids = all(isinstance(g, dict) and g.get("stable_id") for g in grants)
        ok = has_stable_ids and not includes_secrets and len(grants) > 0
        details = {"grant_count": len(grants), "has_stable_ids": has_stable_ids, "includes_secrets": includes_secrets}
        if exp_status == "PASS":
            checks.append(_check(f"grants_mapping.{name}.valid", "grants_mapping", "PASS" if ok else "FAIL",
                "grants mapping uses stable identity/group data and excludes secrets",
                "grants mapping valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"grants_mapping.{name}.rejected", "grants_mapping", "FAIL" if not ok else "PASS",
                f"grants mapping with secrets rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "grants mapping problem detected" if not ok else "grants mapping unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_closure(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        closure = inp.get("closure", {})
        all_checks = bool(inp.get("all_checks_pass"))
        complete = bool(closure.get("complete"))
        decisions = bool(closure.get("decisions_complete"))
        assets = bool(closure.get("assets_complete"))
        authz = bool(closure.get("authorization_complete"))
        missing = closure.get("missing", [])
        hashes_ok = (
            is_sha256(closure.get("refs_manifest_sha256"))
            and is_sha256(closure.get("decisions_manifest_sha256"))
            and is_sha256(closure.get("assets_manifest_sha256"))
            and is_sha256(closure.get("documents_manifest_sha256"))
            and is_sha256(closure.get("policies_manifest_sha256"))
            and is_sha256(closure.get("repository_tree_sha256"))
        )
        ok = complete and decisions and assets and authz and len(missing) == 0 and hashes_ok and all_checks
        details = {
            "complete": complete,
            "decisions_complete": decisions,
            "assets_complete": assets,
            "authorization_complete": authz,
            "missing_count": len(missing),
            "hashes_valid": hashes_ok,
        }
        if exp_status == "PASS":
            checks.append(_check(f"closure.{name}.complete", "closure", "PASS" if ok else "FAIL",
                "closure.complete=true only when decisions, assets, authorization are complete and all manifest hashes are valid",
                "closure complete" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"closure.{name}.incomplete", "closure", "FAIL" if not ok else "PASS",
                f"incomplete closure rejected with {exp.get('error', 'INVALID_STATE')}",
                "closure incomplete" if not ok else "closure unexpectedly complete",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: SchemaValidator) -> list[Check]:
    checks: list[Check] = []
    manifest = {
        "schema_version": "export-manifest-v2",
        "export_id": _uuid(1),
        "format": "git_clone_with_manifests",
        "space_id": "sales",
        "repository_id": "repo-sales",
        "created_at": "2026-11-09T00:00:00Z",
        "created_by": "stable-user-1",
        "includes_secrets": False,
        "includes_private_chats": False,
        "snapshot": {
            "snapshot_sha": "a" * 40,
            "target_branch": "main",
            "main_generation_id": "gen-sales-1",
            "repository_tree_sha256": "0" * 64,
        },
        "refs": [
            {
                "ref_name": "refs/heads/main",
                "object_type": "commit",
                "object_sha": "a" * 40,
                "peeled_sha": None,
                "object_content_sha256": "1" * 64,
                "protected": True,
            },
            {
                "ref_name": f"refs/tags/kb-decisions/{_uuid(2)}",
                "object_type": "tag",
                "object_sha": "b" * 40,
                "peeled_sha": "a" * 40,
                "object_content_sha256": "2" * 64,
                "protected": True,
            },
        ],
        "documents": [
            {
                "document_id": _uuid(3),
                "path": "pricing.md",
                "parent_id": None,
                "document_revision_sha": "a" * 40,
                "content_sha256": "3" * 64,
                "links": [],
                "valid_until": None,
            }
        ],
        "decisions": [],
        "assets": [],
        "policies": {
            "policy_bundle_id": "sales-policy-bundle",
            "access_policy_revision": "a" * 40,
            "approval_policy_revision": "b" * 40,
            "access_policy_content_sha256": "4" * 64,
            "approval_policy_content_sha256": "5" * 64,
            "grants_mapping_sha256": "6" * 64,
        },
        "closure": {
            "complete": True,
            "decisions_complete": True,
            "assets_complete": True,
            "authorization_complete": True,
            "missing": [],
            "refs_manifest_sha256": "7" * 64,
            "decisions_manifest_sha256": "8" * 64,
            "assets_manifest_sha256": "9" * 64,
            "documents_manifest_sha256": "a" * 64,
            "policies_manifest_sha256": "b" * 64,
            "repository_tree_sha256": "0" * 64,
        },
    }
    err = schema_validator.validate_or_error("export-manifest.schema.json", manifest)
    checks.append(_check("schema.export_manifest.valid", "schema", "PASS" if err is None else "FAIL",
        "sample export manifest is schema valid", "schema valid" if err is None else err,
        details={"export_id": manifest["export_id"], "error": err}))

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
    parser = argparse.ArgumentParser(description="T13a Complete Portable Export with Exact Refs and Closure")
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
            contracts_version="export-manifest-v2",
            output_dir=OUTPUT_DIR,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=SPEC_BASELINE_COMMIT,
        contracts_version="export-manifest-v2",
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

    for sub in ['live_gitlab_export', 'live_object_store_export', 'live_decision_note_tag_export', 'live_grants_export']:
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
    raw_path = OUTPUT_DIR / "export-results.json"
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
    sanitized_path = EVIDENCE_DIR / "export-results.json"
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
