"""Unit tests for T10a exact-SHA CI index build harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def _make_builder(t10a_modules: Any) -> Any:
    return t10a_modules.run_t10a_tests.ReportBuilder(
        baseline_commit="a" * 40,
        spec_baseline_commit="b" * 40,
        contracts_version="index-snapshot-v1",
        output_dir=Path("/tmp"),
    )


def test_report_builder_counts_empty(t10a_modules: Any) -> None:
    rb = _make_builder(t10a_modules)
    assert rb._counts() == {
        "PASS": 0,
        "FAIL": 0,
        "FAIL_EXPECTED": 0,
        "FAIL_UNEXPECTED": 0,
        "BLOCKED": 0,
    }


def test_report_builder_counts_expected_negative(t10a_modules: Any) -> None:
    rb = _make_builder(t10a_modules)
    Check = t10a_modules.run_t10a_tests.Check
    rb.add(Check("c1", "exact_sha_build", "PASS", "p", "p"))
    rb.add(Check("c2", "exact_sha_build", "FAIL", "f", "f", details={"expected_negative": True}))
    rb.add(Check("c3", "harness", "BLOCKED", "b", "b"))
    rb.add(Check("c4", "exact_sha_build", "FAIL", "f", "f"))

    counts = rb._counts()
    assert counts["PASS"] == 1
    assert counts["FAIL"] == 2
    assert counts["FAIL_EXPECTED"] == 1
    assert counts["FAIL_UNEXPECTED"] == 1
    assert counts["BLOCKED"] == 1


def test_write_reports_pass_expected_fail_exits_zero(t10a_modules: Any, tmp_path: Path) -> None:
    rb = _make_builder(t10a_modules)
    rb.output_dir = tmp_path
    Check = t10a_modules.run_t10a_tests.Check
    rb.add(Check("c1", "exact_sha_build", "PASS", "p", "p"))
    rb.add(Check("c2", "exact_sha_build", "FAIL", "f", "f", details={"expected_negative": True}))
    code = t10a_modules.run_t10a_tests._write_reports(rb, dry_run=True)
    assert code == 0


def test_write_reports_only_blocked_exits_nonzero(t10a_modules: Any, tmp_path: Path) -> None:
    rb = _make_builder(t10a_modules)
    rb.output_dir = tmp_path
    Check = t10a_modules.run_t10a_tests.Check
    rb.add(Check("c1", "runtime", "BLOCKED", "b", "b"))
    rb.add(Check("c2", "harness", "BLOCKED", "b", "b"))
    code = t10a_modules.run_t10a_tests._write_reports(rb, dry_run=True)
    assert code == 1


def test_write_reports_unexpected_fail_exits_nonzero(t10a_modules: Any, tmp_path: Path) -> None:
    rb = _make_builder(t10a_modules)
    rb.output_dir = tmp_path
    Check = t10a_modules.run_t10a_tests.Check
    rb.add(Check("c1", "exact_sha_build", "PASS", "p", "p"))
    rb.add(Check("c2", "exact_sha_build", "FAIL", "f", "f"))
    code = t10a_modules.run_t10a_tests._write_reports(rb, dry_run=True)
    assert code == 1


def test_check_exact_sha_build_pass(t10a_modules: Any) -> None:
    fixture = {
        "name": "pass",
        "input": {
            "main_sha": "a" * 40,
            "resolved_sha": "a" * 40,
            "read_only": True,
            "webhook_hint_only": True,
            "git_write_capability": False,
        },
        "expected": {"status": "PASS"},
    }
    checks = t10a_modules.run_t10a_tests.check_exact_sha_build([fixture], None)
    assert len(checks) == 1
    assert checks[0].status == "PASS"


def test_check_exact_sha_build_expected_fail(t10a_modules: Any) -> None:
    fixture = {
        "name": "mismatch",
        "input": {
            "main_sha": "a" * 40,
            "resolved_sha": "b" * 40,
            "read_only": True,
            "webhook_hint_only": True,
            "git_write_capability": False,
        },
        "expected": {"status": "FAIL", "error": "STALE_BASE"},
    }
    checks = t10a_modules.run_t10a_tests.check_exact_sha_build([fixture], None)
    assert len(checks) == 1
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_preflight_artifact_pass(t10a_modules: Any) -> None:
    fixture = {
        "name": "pass",
        "input": {
            "snapshot_sha": "c" * 40,
            "cutover_sha": "c" * 40,
            "is_preflight": True,
            "serving_allowed": False,
            "purpose": "cutover_preflight",
            "run_type": "full",
            "state": "ready",
        },
        "expected": {"status": "PASS"},
    }
    checks = t10a_modules.run_t10a_tests.check_preflight_artifact([fixture], None)
    assert checks[0].status == "PASS"


def test_check_preflight_artifact_activated_rejected(t10a_modules: Any) -> None:
    fixture = {
        "name": "activated",
        "input": {
            "snapshot_sha": "c" * 40,
            "cutover_sha": "c" * 40,
            "is_preflight": False,
            "serving_allowed": True,
            "purpose": "published",
            "run_type": "full",
            "state": "active",
        },
        "expected": {"status": "FAIL", "error": "INVALID_STATE"},
    }
    checks = t10a_modules.run_t10a_tests.check_preflight_artifact([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_index_snapshot_contract_full_pass(t10a_modules: Any) -> None:
    fixture = {
        "name": "full",
        "input": {
            "snapshot": {
                "snapshot_sha": "a" * 40,
                "run_type": "full",
                "space_id": "sales",
                "index_profile_version": "pgvector-fts-v1",
                "policy_bundle_id": "sales-policy-bundle",
                "access_policy_revision": "d" * 40,
                "approval_policy_revision": "f" * 40,
                "exact_projection": {"projection_sha256": "e" * 64},
                "semantic_projection": {"projection_sha256": "5" * 64},
                "closure": {
                    "closure_sha256": "c" * 64,
                    "missing_inputs": [],
                    "full_snapshot_equivalence": "not_applicable",
                },
                "main_generation": {"ordering": "ancestry"},
            }
        },
        "expected": {"status": "PASS"},
    }
    checks = t10a_modules.run_t10a_tests.check_index_snapshot_contract([fixture], None)
    assert checks[0].status == "PASS"


def test_check_index_snapshot_contract_incremental_pass(t10a_modules: Any) -> None:
    fixture = {
        "name": "incremental",
        "input": {
            "snapshot": {
                "snapshot_sha": "a" * 40,
                "run_type": "incremental",
                "space_id": "sales",
                "index_profile_version": "pgvector-fts-v1",
                "policy_bundle_id": "sales-policy-bundle",
                "access_policy_revision": "d" * 40,
                "approval_policy_revision": "f" * 40,
                "exact_projection": {"projection_sha256": "e" * 64},
                "semantic_projection": {"projection_sha256": "5" * 64},
                "closure": {
                    "closure_sha256": "c" * 64,
                    "missing_inputs": [],
                    "full_snapshot_equivalence": "equivalent",
                    "equivalence_evidence": {
                        "full_run_id": "11111111-1111-4111-8111-111111111111",
                        "full_snapshot_id": "22222222-2222-4222-8222-222222222222",
                        "full_run_state": "ready",
                        "full_snapshot_state": "ready",
                        "validated_at": "2026-11-09T00:00:00Z",
                        "space_id": "sales",
                        "repository_id": "repo-sales",
                        "target_branch": "main",
                        "main_snapshot_sha": "a" * 40,
                        "main_generation_id": "gen-sales-1",
                        "index_profile_version": "pgvector-fts-v1",
                        "closure_complete": True,
                        "missing_inputs": [],
                        "closure_sha256": "c" * 64,
                        "exact_projection_sha256": "e" * 64,
                        "semantic_projection_sha256": "5" * 64,
                        "evidence_sha256": "7" * 64,
                    },
                },
                "main_generation": {"ordering": "ancestry"},
            }
        },
        "expected": {"status": "PASS"},
    }
    checks = t10a_modules.run_t10a_tests.check_index_snapshot_contract([fixture], None)
    assert checks[0].status == "PASS"


def test_check_index_snapshot_contract_lexicographic_fail(t10a_modules: Any) -> None:
    fixture = {
        "name": "lexicographic",
        "input": {
            "snapshot": {
                "snapshot_sha": "a" * 40,
                "run_type": "full",
                "space_id": "sales",
                "index_profile_version": "pgvector-fts-v1",
                "policy_bundle_id": "sales-policy-bundle",
                "access_policy_revision": "d" * 40,
                "approval_policy_revision": "f" * 40,
                "exact_projection": {"projection_sha256": "e" * 64},
                "semantic_projection": {"projection_sha256": "5" * 64},
                "closure": {
                    "closure_sha256": "c" * 64,
                    "missing_inputs": [],
                    "full_snapshot_equivalence": "not_applicable",
                },
                "main_generation": {"ordering": "lexicographic"},
            }
        },
        "expected": {"status": "FAIL", "error": "INDEX_GENERATION_CONFLICT"},
    }
    checks = t10a_modules.run_t10a_tests.check_index_snapshot_contract([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_index_snapshot_contract_incremental_missing_evidence(t10a_modules: Any) -> None:
    fixture = {
        "name": "missing_evidence",
        "input": {
            "snapshot": {
                "snapshot_sha": "a" * 40,
                "run_type": "incremental",
                "space_id": "sales",
                "index_profile_version": "pgvector-fts-v1",
                "policy_bundle_id": "sales-policy-bundle",
                "access_policy_revision": "d" * 40,
                "approval_policy_revision": "f" * 40,
                "exact_projection": {"projection_sha256": "e" * 64},
                "semantic_projection": {"projection_sha256": "5" * 64},
                "closure": {
                    "closure_sha256": "c" * 64,
                    "missing_inputs": [],
                    "full_snapshot_equivalence": "equivalent",
                },
                "main_generation": {"ordering": "ancestry"},
            }
        },
        "expected": {"status": "FAIL", "error": "DEPENDENCY_CLOSURE_MISMATCH"},
    }
    checks = t10a_modules.run_t10a_tests.check_index_snapshot_contract([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_eligible_content_exclusion_pass(t10a_modules: Any) -> None:
    fixture = {
        "name": "pass",
        "input": {"documents": [{"path": "pricing.md", "projected": True}]},
        "expected": {"status": "PASS"},
    }
    checks = t10a_modules.run_t10a_tests.check_eligible_content_exclusion([fixture], None)
    assert checks[0].status == "PASS"


def test_check_eligible_content_exclusion_inbox_rejected(t10a_modules: Any) -> None:
    fixture = {
        "name": "inbox",
        "input": {"documents": [{"path": "inbox/proposal.md", "projected": True, "ineligible_reason": "inbox"}]},
        "expected": {"status": "FAIL", "error": "SECURITY_REJECTED"},
    }
    checks = t10a_modules.run_t10a_tests.check_eligible_content_exclusion([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_idempotent_rebuild_pass(t10a_modules: Any) -> None:
    fixture = {
        "name": "pass",
        "input": {
            "duplicate_webhook": True,
            "kb_index_lost": False,
            "same_main_sha": True,
            "canonical_git_changed": False,
            "new_active_created": False,
        },
        "expected": {"status": "PASS"},
    }
    checks = t10a_modules.run_t10a_tests.check_idempotent_rebuild([fixture], None)
    assert checks[0].status == "PASS"


def test_check_idempotent_rebuild_changed_canonical_fail(t10a_modules: Any) -> None:
    fixture = {
        "name": "changed_git",
        "input": {
            "duplicate_webhook": False,
            "kb_index_lost": True,
            "same_main_sha": True,
            "canonical_git_changed": True,
            "new_active_created": False,
        },
        "expected": {"status": "FAIL", "error": "RECOVERY_REQUIRED"},
    }
    checks = t10a_modules.run_t10a_tests.check_idempotent_rebuild([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_run_schema_checks_preflight_published_valid(t10a_modules: Any) -> None:
    sv = t10a_modules.run_t10a_tests.SchemaValidator(
        Path("specs/corporate-kb/contracts")
    )
    if sv.load_errors:
        pytest.skip(f"schema load errors: {sv.load_errors}")
    checks = t10a_modules.run_t10a_tests.run_schema_checks(sv)
    assert any(c.id == "schema.preflight.valid" and c.status == "PASS" for c in checks)
    assert any(c.id == "schema.published.valid" and c.status == "PASS" for c in checks)


def test_run_schema_checks_negative_invalid_fixtures(t10a_modules: Any) -> None:
    sv = t10a_modules.run_t10a_tests.SchemaValidator(
        Path("specs/corporate-kb/contracts")
    )
    if sv.load_errors:
        pytest.skip(f"schema load errors: {sv.load_errors}")
    checks = t10a_modules.run_t10a_tests.run_schema_checks(sv)
    lex = next((c for c in checks if c.id == "schema.lexicographic_ordering.invalid"), None)
    inc = next((c for c in checks if c.id == "schema.incremental_no_evidence.invalid"), None)
    assert lex is not None
    assert inc is not None
    assert lex.status == "PASS"
    assert inc.status == "PASS"
