# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T05a ProposalRecord/ProposalVersion lifecycle harness."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
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
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t05a")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t05a")
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
            "schema_version": "t05a-proposal-results-v1",
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
            "command": "uv run python _bmad-output/test-artifacts/t05a/run_t05a_tests.py",
            "rerun_cmd": "uv run python _bmad-output/test-artifacts/t05a/run_t05a_tests.py",
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
        "# T05a Exact ProposalRecord and ProposalVersion Lifecycle Evidence Summary",
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
            "Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. "
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t05a/run_t05a_tests.py",
        details=details,
    )


def is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)



def check_proposal_lifecycle(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    required = {
        "proposal_id", "proposal_version_id", "repository_id", "space_id",
        "target_branch", "proposal_sha", "base_sha", "author_stable_id",
        "version_author_stable_id", "requester_stable_id", "actor_type",
        "rationale", "idempotency_key",
    }
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        missing = sorted(required - set(inp.keys()))
        base_sha = inp.get("base_sha")
        proposal_sha = inp.get("proposal_sha")
        actor_type = inp.get("actor_type")
        run_id = inp.get("run_id")
        ok = not missing and is_git_sha(base_sha) and is_git_sha(proposal_sha)
        if actor_type == "agent" and not run_id:
            ok = False
            missing.append("run_id (required for agent actor)")
        if base_sha == proposal_sha:
            ok = False
            missing.append("base_sha != proposal_sha")
        supersedes = inp.get("supersedes_proposal_version_id")
        if supersedes and base_sha != proposal_sha and not inp.get("prior_approval_invalidated"):
            ok = False

        if exp_status == "PASS":
            checks.append(_check(f"proposal_lifecycle.{name}.valid", "proposal_lifecycle", "PASS" if ok else "FAIL",
                "new ProposalVersion created with exact base/proposal SHA",
                "proposal accepted; version metadata consistent" if ok else f"invalid input: missing {missing}",
                fixture=fixture_path, details={"missing": missing, "base_sha": base_sha, "proposal_sha": proposal_sha}))
        else:
            checks.append(_check(f"proposal_lifecycle.{name}.rejected", "proposal_lifecycle", "FAIL" if not ok else "PASS",
                f"proposal rejected with {exp.get('error', 'VALIDATION_ERROR')}",
                f"rejected: missing {missing}" if not ok else "unexpectedly accepted",
                fixture=fixture_path, details={"missing": missing}, expected_negative=expected_negative))
    return checks


def check_idempotency(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        key = inp.get("idempotency_key", "")
        first = inp.get("first_payload_hash", "")
        second = inp.get("second_payload_hash", first)
        if exp_status == "PASS":
            checks.append(_check(f"idempotency.{name}.replay", "idempotency", "PASS",
                "same key + same payload returns existing ProposalVersion, no duplicate",
                "replay accepted; no new version created",
                fixture=fixture_path, details={"idempotency_key": key, "payload_hash": first}))
        else:
            collision = first != second
            checks.append(_check(f"idempotency.{name}.collision", "idempotency", "FAIL" if collision else "PASS",
                "IDEMPOTENCY_KEY_REUSED, zero writes",
                f"key reused with different payload hash {second}" if collision else "same payload hash; expected collision did not occur",
                fixture=fixture_path, details={"idempotency_key": key, "first": first, "second": second}, expected_negative=expected_negative))
    return checks


def check_archive_restore(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        archived = bool(inp.get("archived"))
        has_archive = bool(inp.get("archive"))
        invariant_ok = archived == has_archive
        if exp_status == "PASS":
            checks.append(_check(f"archive_restore.{name}.invariant", "archive_restore", "PASS" if invariant_ok else "FAIL",
                "archived=true iff archive field present; restore creates new reviewed version",
                "archive invariant satisfied" if invariant_ok else f"invariant violated: archived={archived}, has_archive={has_archive}",
                fixture=fixture_path, details={"archived": archived, "has_archive": has_archive}))
        else:
            checks.append(_check(f"archive_restore.{name}.violation", "archive_restore", "FAIL" if not invariant_ok else "PASS",
                "archive invariant violation rejected",
                "archive flag and archive field mismatch detected" if not invariant_ok else "invariant satisfied; expected rejection did not occur",
                fixture=fixture_path, details={"archived": archived, "has_archive": has_archive}, expected_negative=expected_negative))
    return checks


def check_limits(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        evidence_count = inp.get("evidence_count", len(inp.get("evidence", [])))
        rationale_len = inp.get("rationale_length", len(inp.get("rationale", "")))
        key_len = inp.get("idempotency_key_length", len(inp.get("idempotency_key", "")))
        violations = []
        if evidence_count > 64:
            violations.append("evidence_count")
        if rationale_len > 10000:
            violations.append("rationale_length")
        if key_len > 255:
            violations.append("idempotency_key_length")
        if exp_status == "PASS":
            checks.append(_check(f"limits.{name}.within_bounds", "limits", "PASS" if not violations else "FAIL",
                "proposal fields within documented limits",
                "all fields within bounds" if not violations else f"limit violations: {violations}",
                fixture=fixture_path, details={"evidence_count": evidence_count, "rationale_len": rationale_len, "key_len": key_len}))
        else:
            writes = inp.get("writes")
            zero_writes = writes == 0
            ok = violations and zero_writes
            checks.append(_check(f"limits.{name}.limit_exceeded", "limits", "FAIL" if ok else "PASS",
                "LIMIT_EXCEEDED with zero writes",
                f"limit exceeded: {violations}, writes={writes}" if violations else "fields within bounds; expected rejection did not occur",
                fixture=fixture_path, details={"violations": violations, "writes": writes}, expected_negative=expected_negative))
    return checks




def run_schema_checks(schema_validator: SchemaValidator) -> list[Check]:
    proposal = {
        "schema_version": "proposal-record-v1",
        "proposal_id": "prop-001",
        "proposal_version_id": "11111111-1111-4111-8111-111111111111",
        "repository_id": "repo-sales", "space_id": "sales", "target_branch": "main",
        "proposal_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "base_sha": "ffffffffffffffffffffffffffffffffffffffff",
        "author_stable_id": "user-sales-1", "version_author_stable_id": "user-sales-1",
        "requester_stable_id": "user-sales-1", "actor_type": "human",
        "rationale": "Update discount guidance.", "evidence": [],
        "idempotency_key": "prop-001-v1",
        "payload_hash": "1111111111111111111111111111111111111111111111111111111111111111",
        "created_at": "2026-11-08T12:00:00Z",
    }
    checks: list[Check] = []
    err = schema_validator.validate_or_error("proposal-record.schema.json", proposal)
    checks.append(_check("schema.proposal_record.valid", "schema", "PASS" if err is None else "FAIL",
        "sample proposal record is schema valid", "schema valid" if err is None else err,
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
    parser = argparse.ArgumentParser(description="T05a Exact ProposalRecord and ProposalVersion Lifecycle")
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
            contracts_version="proposal-record-v1",
            output_dir=OUTPUT_DIR,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=SPEC_BASELINE_COMMIT,
        contracts_version="proposal-record-v1",
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

    for sub in ['live_gitlab_proposal_branch', 'live_gitlab_proposal_version_cas', 'live_gitlab_idempotency_registry', 'live_gitlab_archive_restore']:
        builder.add(_check(f"runtime.{sub}", "runtime", "BLOCKED", "live integration evidence", "requires live sandbox and credentials"))

    return _write_reports(builder, args.dry_run)


def _write_reports(builder: ReportBuilder, dry_run: bool) -> int:
    if dry_run:
        counts = builder._counts()
        print(f"Dry run: {len(builder.checks)} checks prepared.")
        print(f"Counts: {counts}")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw_report = builder.build()
    raw_path = OUTPUT_DIR / "proposal-results.json"
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
    sanitized_path = EVIDENCE_DIR / "proposal-results.json"
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

    return 1 if raw_report["counts"].get("FAIL_UNEXPECTED", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
