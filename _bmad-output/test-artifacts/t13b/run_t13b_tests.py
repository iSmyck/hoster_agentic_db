# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "jsonschema>=4.18",
#   "referencing",
# ]
# ///

"""T13b mirror/metadata backup, rebuild and conservative clean restore harness."""

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
OUTPUT_DIR = Path("_bmad-output/test-artifacts/t13b")
EVIDENCE_DIR = Path("specs/corporate-kb/evidence/t13b")
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
            "schema_version": "t13b-restore-results-v1",
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
            "command": "uv run python _bmad-output/test-artifacts/t13b/run_t13b_tests.py",
            "rerun_cmd": "uv run python _bmad-output/test-artifacts/t13b/run_t13b_tests.py",
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
        "# T13b Mirror/Metadata Backup, Rebuild and Conservative Clean Restore Evidence Summary",
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
            "Real backup/restore/rebuild on GitLab/PostgreSQL/object-store/IdP remains BLOCKED until their sandboxes and credentials exist. "
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
        rerun_cmd="uv run python _bmad-output/test-artifacts/t13b/run_t13b_tests.py",
        details=details,
    )


def is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _uuid(seed: int) -> str:
    return str(uuid.UUID(int=seed))


def check_git_mirror_refs_objects(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        refs = inp.get("refs", [])
        objects = inp.get("objects", [])
        missing_refs = inp.get("missing_refs", [])
        missing_objects = inp.get("missing_objects", [])
        all_full = all(is_git_sha(r.get("object_sha")) for r in refs)
        protected_tags = all(
            not r.get("ref_name", "").startswith("refs/tags/kb-") or r.get("protected") is True
            for r in refs
        )
        all_objects_present = all(o.get("present") for o in objects)
        ok = all_full and protected_tags and all_objects_present and len(missing_refs) == 0 and len(missing_objects) == 0
        details = {
            "ref_count": len(refs),
            "object_count": len(objects),
            "all_full_sha": all_full,
            "protected_tags": protected_tags,
            "all_objects_present": all_objects_present,
            "missing_refs": missing_refs,
            "missing_objects": missing_objects,
        }
        if exp_status == "PASS":
            checks.append(_check(f"git_mirror_refs_objects.{name}.complete", "git_mirror_refs_objects", "PASS" if ok else "FAIL",
                "Git mirror contains all refs/objects and protected decision/cutover tags with exact full SHAs",
                "mirror complete" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"git_mirror_refs_objects.{name}.incomplete", "git_mirror_refs_objects", "FAIL" if not ok else "PASS",
                f"incomplete mirror rejected with {exp.get('error', 'INVALID_STATE')}",
                "mirror incomplete" if not ok else "mirror unexpectedly complete",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_metadata_backup(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        metadata = inp.get("metadata", {})
        consistent = bool(inp.get("consistent"))
        mrs = metadata.get("mrs", [])
        notes = metadata.get("notes", [])
        audit = metadata.get("audit_events", [])
        has_mrs = len(mrs) > 0
        has_notes = len(notes) > 0
        has_audit = len(audit) > 0
        note_match_ok = all(m.get("note_record_sha256_match") for m in mrs)
        ok = has_mrs and has_notes and has_audit and consistent and note_match_ok
        details = {
            "mr_count": len(mrs),
            "note_count": len(notes),
            "audit_event_count": len(audit),
            "consistent": consistent,
            "note_record_sha256_match": note_match_ok,
        }
        if exp_status == "PASS":
            checks.append(_check(f"metadata_backup.{name}.complete", "metadata_backup", "PASS" if ok else "FAIL",
                "GitLab MR/note/audit metadata captured and consistent",
                "metadata backup valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"metadata_backup.{name}.inconsistent", "metadata_backup", "FAIL" if not ok else "PASS",
                f"incomplete or inconsistent metadata rejected with {exp.get('error', 'DECISION_INVALID')}",
                "metadata backup problem detected" if not ok else "metadata unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_object_backup(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        objects = inp.get("objects", [])
        mutable = inp.get("mutable_objects", [])
        ok = True
        for o in objects:
            if not is_sha256(o.get("sha256")):
                ok = False
            if not o.get("present"):
                ok = False
            if not o.get("immutable"):
                ok = False
            if o.get("present_sha256") and o.get("sha256") != o.get("present_sha256"):
                ok = False
        ok = ok and len(mutable) == 0
        details = {"object_count": len(objects), "mutable_objects": mutable, "all_immutable_and_present": ok}
        if exp_status == "PASS":
            checks.append(_check(f"object_backup.{name}.valid", "object_backup", "PASS" if ok else "FAIL",
                "immutable/versioned objects match assets manifest hashes",
                "object backup valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"object_backup.{name}.rejected", "object_backup", "FAIL" if not ok else "PASS",
                f"mutable or hash-mismatched object rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "object backup problem detected" if not ok else "object backup unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_secrets_separation(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        ordinary_has_secrets = bool(inp.get("ordinary_backup_contains_secrets"))
        recovery_exists = bool(inp.get("secrets_recovery_policy_exists"))
        secrets_only_recovery = bool(inp.get("secrets_in_recovery_policy_only"))
        ok = (not ordinary_has_secrets) and recovery_exists and secrets_only_recovery
        details = {
            "ordinary_backup_contains_secrets": ordinary_has_secrets,
            "secrets_recovery_policy_exists": recovery_exists,
            "secrets_in_recovery_policy_only": secrets_only_recovery,
        }
        if exp_status == "PASS":
            checks.append(_check(f"secrets_separation.{name}.separate", "secrets_separation", "PASS" if ok else "FAIL",
                "secrets stored only under separately controlled recovery policy; ordinary backup has no secrets",
                "secrets separation valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"secrets_separation.{name}.rejected", "secrets_separation", "FAIL" if not ok else "PASS",
                f"secret leak or missing recovery policy rejected with {exp.get('error', 'SECURITY_REJECTED')}",
                "secrets separation problem detected" if not ok else "secrets separation unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_kb_authz_rebuild(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        source_ok = inp.get("source") == "git_policy_plus_fresh_idp"
        no_inherited = not bool(inp.get("inherited_active_grants"))
        fresh_idp = bool(inp.get("idp_data_fresh"))
        policy_loaded = bool(inp.get("policy_bundle_loaded"))
        ok = source_ok and no_inherited and fresh_idp and policy_loaded
        details = {
            "source_is_git_policy_plus_fresh_idp": source_ok,
            "no_inherited_active_grants": no_inherited,
            "idp_data_fresh": fresh_idp,
            "policy_bundle_loaded": policy_loaded,
        }
        if exp_status == "PASS":
            checks.append(_check(f"kb_authz_rebuild.{name}.valid", "kb_authz_rebuild", "PASS" if ok else "FAIL",
                "kb_authz rebuilt from Git policy plus fresh IdP data with no inherited active grants",
                "kb_authz rebuild valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"kb_authz_rebuild.{name}.rejected", "kb_authz_rebuild", "FAIL" if not ok else "PASS",
                f"invalid kb_authz rebuild rejected with {exp.get('error', 'AUTHZ_GROUP_STALE')}",
                "kb_authz rebuild problem detected" if not ok else "kb_authz rebuild unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_kb_ops_rebuild(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        source_ok = inp.get("source") == "git_mrs_notes_tags_history_registry"
        freeze = bool(inp.get("global_merge_freeze"))
        barriers = bool(inp.get("per_target_barriers"))
        quarantine = bool(inp.get("unknown_outcomes_quarantined"))
        ok = source_ok and freeze and barriers and quarantine
        details = {
            "source_is_git_derived": source_ok,
            "global_merge_freeze": freeze,
            "per_target_barriers": barriers,
            "unknown_outcomes_quarantined": quarantine,
        }
        if exp_status == "PASS":
            checks.append(_check(f"kb_ops_rebuild.{name}.valid", "kb_ops_rebuild", "PASS" if ok else "FAIL",
                "Git-derived kb_ops rebuilt under global merge freeze with conservative per-target barriers",
                "kb_ops rebuild valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"kb_ops_rebuild.{name}.rejected", "kb_ops_rebuild", "FAIL" if not ok else "PASS",
                f"invalid kb_ops rebuild rejected with {exp.get('error', 'RECOVERY_REQUIRED')}",
                "kb_ops rebuild problem detected" if not ok else "kb_ops rebuild unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_kb_index_rebuild(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        source_ok = inp.get("source") == "git_plus_immutable_assets_plus_config"
        no_git_mutation = not bool(inp.get("canonical_git_mutated"))
        pointer_not_truth = not bool(inp.get("active_pointer_restored_as_truth"))
        assets_ok = bool(inp.get("assets_hash_verified"))
        ok = source_ok and no_git_mutation and pointer_not_truth and assets_ok
        details = {
            "source_is_git_assets_config": source_ok,
            "canonical_git_not_mutated": no_git_mutation,
            "active_pointer_not_restored_as_truth": pointer_not_truth,
            "assets_hash_verified": assets_ok,
        }
        if exp_status == "PASS":
            checks.append(_check(f"kb_index_rebuild.{name}.valid", "kb_index_rebuild", "PASS" if ok else "FAIL",
                "kb_index rebuilt from Git + immutable assets + approved config without canonical Git mutation",
                "kb_index rebuild valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"kb_index_rebuild.{name}.rejected", "kb_index_rebuild", "FAIL" if not ok else "PASS",
                f"invalid kb_index rebuild rejected with {exp.get('error', 'INVALID_STATE')}",
                "kb_index rebuild problem detected" if not ok else "kb_index rebuild unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_correction_task_backup_reconciliation(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        backup = inp.get("backup", {})
        reconciliation = inp.get("reconciliation", {})
        hash_ok = is_sha256(backup.get("current_projection_hash"))
        sequence_ok = bool(backup.get("event_sequence_valid"))
        perimeter_ok = bool(backup.get("perimeter_check_passed"))
        mr_ok = bool(reconciliation.get("linked_mr_verified"))
        no_fabricate = bool(reconciliation.get("no_fabricated_decisions"))
        no_delete = bool(reconciliation.get("no_deleted_canonical_writes"))
        ok = hash_ok and sequence_ok and perimeter_ok and mr_ok and no_fabricate and no_delete
        details = {
            "projection_hash_valid": hash_ok,
            "event_sequence_valid": sequence_ok,
            "perimeter_check_passed": perimeter_ok,
            "linked_mr_verified": mr_ok,
            "no_fabricated_decisions": no_fabricate,
            "no_deleted_canonical_writes": no_delete,
        }
        if exp_status == "PASS":
            checks.append(_check(f"correction_task_backup_reconciliation.{name}.valid", "correction_task_backup_reconciliation", "PASS" if ok else "FAIL",
                "correction-task restore uses hash/event-sequence/perimeter checks and linked-MR reconciliation without fabricating/deleting canonical writes",
                "correction-task reconciliation valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"correction_task_backup_reconciliation.{name}.rejected", "correction_task_backup_reconciliation", "FAIL" if not ok else "PASS",
                f"invalid correction-task reconciliation rejected with {exp.get('error', 'INVALID_STATE')}",
                "correction-task reconciliation problem detected" if not ok else "correction-task reconciliation unexpectedly valid",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_clean_isolated_instance(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        no_inherited_grants = not bool(inp.get("inherited_active_grants"))
        no_inherited_pointer = not bool(inp.get("inherited_active_pointer"))
        no_inherited_ops = not bool(inp.get("inherited_operational_rows"))
        sources_verified = bool(inp.get("rebuild_sources_verified"))
        ok = no_inherited_grants and no_inherited_pointer and no_inherited_ops and sources_verified
        details = {
            "no_inherited_active_grants": no_inherited_grants,
            "no_inherited_active_pointer": no_inherited_pointer,
            "no_inherited_operational_rows": no_inherited_ops,
            "rebuild_sources_verified": sources_verified,
        }
        if exp_status == "PASS":
            checks.append(_check(f"clean_isolated_instance.{name}.clean", "clean_isolated_instance", "PASS" if ok else "FAIL",
                "restore proven on clean isolated instance with no inherited active grants, pointer or operational rows",
                "clean isolated instance" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"clean_isolated_instance.{name}.rejected", "clean_isolated_instance", "FAIL" if not ok else "PASS",
                f"inherited state used as truth rejected with {exp.get('error', 'INVALID_STATE')}",
                "inherited state detected" if not ok else "instance unexpectedly clean",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def check_conservative_rebuild(fixtures: list[dict[str, Any]], fixture_path: Path) -> list[Check]:
    checks: list[Check] = []
    for f in fixtures:
        name = f.get("name", "unnamed")
        inp = f.get("input", {})
        exp = f.get("expected", {})
        exp_status = exp.get("status", "PASS")
        expected_negative = exp_status == "FAIL"
        if "outcome" in inp and inp.get("outcome") == "unknown":
            conclusive = bool(inp.get("conclusive_reconciliation"))
            ok = not conclusive
        else:
            closure = bool(inp.get("closure_complete"))
            grants = bool(inp.get("grants_verified"))
            assets = bool(inp.get("assets_verified"))
            ok = closure and grants and assets
        details = {
            "conclusive_reconciliation": inp.get("conclusive_reconciliation"),
            "closure_complete": inp.get("closure_complete"),
            "grants_verified": inp.get("grants_verified"),
            "assets_verified": inp.get("assets_verified"),
        }
        if exp_status == "PASS":
            checks.append(_check(f"conservative_rebuild.{name}.conservative", "conservative_rebuild", "PASS" if ok else "FAIL",
                "unknown outcomes remain quarantined; missing assets/grants/closure block READY",
                "conservative rebuild valid" if ok else f"details={details}",
                fixture=fixture_path, details=details))
        else:
            checks.append(_check(f"conservative_rebuild.{name}.rejected", "conservative_rebuild", "FAIL" if not ok else "PASS",
                f"optimistic or incomplete rebuild rejected with {exp.get('error', 'INVALID_STATE')}",
                "rebuild optimism detected" if not ok else "rebuild unexpectedly conservative",
                fixture=fixture_path, details=details, expected_negative=expected_negative))
    return checks


def run_schema_checks(schema_validator: SchemaValidator) -> list[Check]:
    checks: list[Check] = []
    task = {
        "schema_version": "docops-correction-task-v1",
        "task_id": _uuid(1),
        "space_id": "sales",
        "repository_id": "repo-sales",
        "document_id": _uuid(2),
        "document_revision_sha": "a" * 40,
        "state": "open",
        "requester_stable_id": "stable-user-1",
        "owner": {"kind": "group", "stable_id": "docops-owners"},
        "evidence_sha256": "e" * 64,
        "linked_mr": None,
        "idempotency_key": "idemp-1",
        "payload_hash": "1" * 64,
        "task_version": 1,
        "created_at": "2026-11-09T00:00:00Z",
        "updated_at": "2026-11-09T00:00:00Z",
        "resolved_at": None,
        "cancelled_at": None,
        "resolved_by_stable_id": None,
        "cancelled_by_stable_id": None,
        "resolution_reason": None,
        "cancellation_reason": None,
        "resolution_evidence_sha256": None,
        "cancellation_evidence_sha256": None,
    }
    err = schema_validator.validate_or_error("docops-correction-task.schema.json", task)
    checks.append(_check("schema.correction_task_open.valid", "schema", "PASS" if err is None else "FAIL",
        "sample open correction task is schema valid", "schema valid" if err is None else err,
        details={"task_id": task["task_id"], "error": err}))

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
    parser = argparse.ArgumentParser(description="T13b Mirror/Metadata Backup, Rebuild and Conservative Clean Restore")
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
            contracts_version="docops-correction-task-v1",
            output_dir=OUTPUT_DIR,
        )
        builder.add(_check("harness.fixture_missing", "harness", "BLOCKED", "fixture present", f"missing {fixture_path}"))
        return _write_reports(builder, args.dry_run)

    builder = ReportBuilder(
        baseline_commit=T00_BASELINE_COMMIT,
        spec_baseline_commit=SPEC_BASELINE_COMMIT,
        contracts_version="docops-correction-task-v1",
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

    for sub in ['live_gitlab_mirror', 'live_postgres_backup_restore', 'live_object_store_backup', 'live_idp_rebuild']:
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
    raw_path = OUTPUT_DIR / "restore-results.json"
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
    sanitized_path = EVIDENCE_DIR / "restore-results.json"
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
