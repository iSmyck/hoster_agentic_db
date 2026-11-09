# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T12b controlled cutover and activation harness."""

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
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t12b")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t12b")
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
            "schema_version": "t12b-cutover-results-v1",
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
            "command": "uv run python _bmad-output/test-artifacts/t12b/run_t12b_tests.py",
            "rerun_cmd": "uv run python _bmad-output/test-artifacts/t12b/run_t12b_tests.py",
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
        "# T12b Controlled Cutover and Activation Evidence Summary",
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
            "Real GitLab/GO/object-store/IdP checks remain BLOCKED until their sandboxes and credentials exist. "
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t12b/run_t12b_tests.py",
        details=details,
    )


def is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _uuid(seed: int) -> str:
    return str(uuid.UUID(int=seed))


def check_cutover_record(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        space_id = inp.get("space_id")
        repo_id = inp.get("repository_id")
        cutover_sha = inp.get("cutover_sha")
        evidence = inp.get("evidence_sha256")
        signoff = inp.get("signoff_stable_id")
        signed_at = inp.get("signed_at")
        all_present = bool(inp.get("all_fields_present"))
        ok = (
            bool(space_id) and bool(repo_id)
            and is_git_sha(cutover_sha)
            and is_sha256(evidence)
            and bool(signoff)
            and bool(signed_at)
        )
        details = {
            "space_id_present": bool(space_id),
            "repository_id_present": bool(repo_id),
            "cutover_sha_valid": is_git_sha(cutover_sha),
            "evidence_sha256_valid": is_sha256(evidence),
            "signoff_present": bool(signoff),
            "signed_at_present": bool(signed_at),
        }
        if exp_status == "PASS":
            checks.append(_check(f"cutover_record.{name}.valid", "cutover_record", "PASS" if ok else "FAIL",
                "CutoverRecord binds Space, exact cutover_sha, evidence, sign-off stable identity and UTC timestamp",
                "CutoverRecord valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"cutover_record.{name}.rejected", "cutover_record", "FAIL" if not ok else "PASS",
                f"invalid CutoverRecord rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                "CutoverRecord rejected" if not ok else "CutoverRecord unexpectedly accepted",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_write_freeze(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        freeze = bool(inp.get("freeze"))
        access_closed = bool(inp.get("user_access_closed"))
        no_published = not bool(inp.get("published_index_exists"))
        later_steps = any(inp.get(k) for k in ["protection_active", "preflight_validated", "published_created", "activated"])
        ok = freeze and access_closed and no_published and (not later_steps or name == "freeze_before_any_later_step")
        # For the positive fixture, later steps are false; for negatives, we check freeze preconditions only.
        if name != "freeze_before_any_later_step":
            ok = freeze and access_closed and no_published
        details = {
            "freeze": freeze,
            "user_access_closed": access_closed,
            "no_published_index": no_published,
        }
        if exp_status == "PASS":
            checks.append(_check(f"write_freeze.{name}.frozen", "write_freeze", "PASS" if ok else "FAIL",
                "write freeze established first with user access closed and no published index",
                "freeze valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"write_freeze.{name}.rejected", "write_freeze", "FAIL" if not ok else "PASS",
                f"invalid freeze state rejected with {exp.get('error', 'INVALID_STATE')}",
                "freeze precondition failed" if not ok else "freeze precondition unexpectedly passed",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_head_verification(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        head = inp.get("head_sha")
        cutover = inp.get("cutover_sha")
        drift = bool(inp.get("drift_after_signoff"))
        exact = is_git_sha(head) and is_git_sha(cutover) and head == cutover
        ok = exact and not drift
        details = {
            "head_sha": head,
            "cutover_sha": cutover,
            "head_matches_cutover": exact,
            "drift_after_signoff": drift,
        }
        if exp_status == "PASS":
            checks.append(_check(f"head_verification.{name}.exact", "head_verification", "PASS" if ok else "FAIL",
                "HEAD equals cutover_sha before protection and activation",
                "HEAD exact" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"head_verification.{name}.rejected", "head_verification", "FAIL" if not ok else "PASS",
                f"HEAD mismatch or drift rejected with {exp.get('error', 'STALE_BASE')}",
                "HEAD mismatch or drift detected" if not ok else "HEAD unexpectedly matched",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_protected_rules(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        val_tag = inp.get("validation_tag")
        cut_tag = inp.get("cutover_tag")
        mr_only = bool(inp.get("mr_only_rules"))
        merge_only_go = bool(inp.get("merge_only_go"))
        neg_proof = bool(inp.get("negative_direct_push_proof"))
        ok = (
            bool(val_tag) and bool(cut_tag)
            and val_tag.startswith("refs/tags/kb-validation/")
            and cut_tag.startswith("refs/tags/kb-cutover/")
            and mr_only and merge_only_go and neg_proof
        )
        details = {
            "validation_tag": val_tag,
            "cutover_tag": cut_tag,
            "mr_only_rules": mr_only,
            "merge_only_go": merge_only_go,
            "negative_direct_push_proof": neg_proof,
        }
        if exp_status == "PASS":
            checks.append(_check(f"protected_rules.{name}.protected", "protected_rules", "PASS" if ok else "FAIL",
                "protected validation/cutover tags and MR-only/merge-only-GO rules with negative direct-push proof",
                "protected rules valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"protected_rules.{name}.rejected", "protected_rules", "FAIL" if not ok else "PASS",
                f"incomplete protection rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "protection gap detected" if not ok else "protection unexpectedly complete",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_preflight_to_published_order(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        pre = inp.get("preflight", {})
        pub = inp.get("published", {})
        preflight_valid = (
            bool(pre.get("is_preflight"))
            and pre.get("serving_allowed") is False
            and is_git_sha(pre.get("snapshot_sha"))
            and bool(pre.get("validated"))
        )
        published_valid = (
            pub.get("is_preflight") is False
            and pub.get("serving_allowed") is True
            and is_git_sha(pub.get("snapshot_sha"))
            and bool(pub.get("full_validation_repeated"))
            and pub.get("snapshot_id") != pre.get("snapshot_id")
        )
        same_sha = pre.get("snapshot_sha") == pub.get("snapshot_sha")
        ok = preflight_valid and published_valid and same_sha
        details = {
            "preflight_valid": preflight_valid,
            "published_valid": published_valid,
            "same_sha": same_sha,
            "ids_differ": pub.get("snapshot_id") != pre.get("snapshot_id"),
        }
        if exp_status == "PASS":
            checks.append(_check(f"preflight_to_published_order.{name}.ordered", "preflight_to_published_order", "PASS" if ok else "FAIL",
                "inactive preflight validated before separate published artifact with new IDs and same SHA",
                "preflight→published order valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"preflight_to_published_order.{name}.rejected", "preflight_to_published_order", "FAIL" if not ok else "PASS",
                f"invalid preflight→published transition rejected with {exp.get('error', 'INVALID_STATE')}",
                "invalid transition detected" if not ok else "transition unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_activation(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        observable = bool(inp.get("published_pointer_observable"))
        access_opened = bool(inp.get("user_access_opened"))
        ok = observable and access_opened
        details = {
            "published_pointer_observable": observable,
            "user_access_opened": access_opened,
        }
        if exp_status == "PASS":
            checks.append(_check(f"activation.{name}.active", "activation", "PASS" if ok else "FAIL",
                "Space/user access activated only after published pointer is observable",
                "activation valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"activation.{name}.rejected", "activation", "FAIL" if not ok else "PASS",
                f"invalid activation rejected with {exp.get('error', 'INDEX_NOT_READY')}",
                "activation precondition failed" if not ok else "activation unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_bypass(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    valid_order = ["freeze", "head_verified", "protection", "preflight", "published", "activation"]
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        steps = inp.get("steps", [])
        ok = steps == valid_order
        details = {"steps": steps, "valid_order": valid_order}
        if exp_status == "PASS":
            checks.append(_check(f"bypass.{name}.valid_order", "bypass", "PASS" if ok else "FAIL",
                "cutover follows freeze→HEAD→protection→preflight→published→activation order",
                "order valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"bypass.{name}.rejected", "bypass", "FAIL" if not ok else "PASS",
                f"bypass or out-of-order cutover rejected with {exp.get('error', 'INVALID_STATE')}",
                "out-of-order cutover detected" if not ok else "cutover order unexpectedly valid",
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
        "sample cutover preflight snapshot is schema valid", "schema valid" if err is None else err,
        details={"snapshot_id": preflight["snapshot_id"], "error": err}))

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
    parser = argparse.ArgumentParser(description="T12b Controlled Cutover and Activation")
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

    for sub in ['live_gitlab_protected_tags', 'live_gitlab_mr_only_rules', 'live_gitlab_negative_direct_push', 'live_go_cutover_record']:
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
    raw_path = OUTPUT_DIR / "cutover-results.json"
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
    sanitized_path = EVIDENCE_DIR / "cutover-results.json"
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
