"""Unit tests for T10b published retrieval and monotonic lifecycle harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def _make_builder(t10b_modules: Any) -> Any:
    return t10b_modules.run_t10b_tests.ReportBuilder(
        baseline_commit="a" * 40,
        spec_baseline_commit="b" * 40,
        contracts_version="index-snapshot-v1",
        output_dir=Path("/tmp"),
    )


def test_report_builder_counts_empty(t10b_modules: Any) -> None:
    rb = _make_builder(t10b_modules)
    assert rb._counts() == {
        "PASS": 0,
        "FAIL": 0,
        "FAIL_EXPECTED": 0,
        "FAIL_UNEXPECTED": 0,
        "BLOCKED": 0,
    }


def test_report_builder_counts_expected_negative(t10b_modules: Any) -> None:
    rb = _make_builder(t10b_modules)
    Check = t10b_modules.run_t10b_tests.Check
    rb.add(Check("c1", "publication_lifecycle", "PASS", "p", "p"))
    rb.add(Check("c2", "publication_lifecycle", "FAIL", "f", "f", details={"expected_negative": True}))
    rb.add(Check("c3", "harness", "BLOCKED", "b", "b"))
    rb.add(Check("c4", "publication_lifecycle", "FAIL", "f", "f"))

    counts = rb._counts()
    assert counts["PASS"] == 1
    assert counts["FAIL"] == 2
    assert counts["FAIL_EXPECTED"] == 1
    assert counts["FAIL_UNEXPECTED"] == 1
    assert counts["BLOCKED"] == 1


def test_write_reports_pass_expected_fail_exits_zero(t10b_modules: Any, tmp_path: Path) -> None:
    rb = _make_builder(t10b_modules)
    rb.output_dir = tmp_path
    Check = t10b_modules.run_t10b_tests.Check
    rb.add(Check("c1", "publication_lifecycle", "PASS", "p", "p"))
    rb.add(Check("c2", "publication_lifecycle", "FAIL", "f", "f", details={"expected_negative": True}))
    code = t10b_modules.run_t10b_tests._write_reports(rb, dry_run=True)
    assert code == 0


def test_write_reports_only_blocked_exits_nonzero(t10b_modules: Any, tmp_path: Path) -> None:
    rb = _make_builder(t10b_modules)
    rb.output_dir = tmp_path
    Check = t10b_modules.run_t10b_tests.Check
    rb.add(Check("c1", "runtime", "BLOCKED", "b", "b"))
    rb.add(Check("c2", "harness", "BLOCKED", "b", "b"))
    code = t10b_modules.run_t10b_tests._write_reports(rb, dry_run=True)
    assert code == 1


def test_write_reports_unexpected_fail_exits_nonzero(t10b_modules: Any, tmp_path: Path) -> None:
    rb = _make_builder(t10b_modules)
    rb.output_dir = tmp_path
    Check = t10b_modules.run_t10b_tests.Check
    rb.add(Check("c1", "publication_lifecycle", "PASS", "p", "p"))
    rb.add(Check("c2", "publication_lifecycle", "FAIL", "f", "f"))
    code = t10b_modules.run_t10b_tests._write_reports(rb, dry_run=True)
    assert code == 1


def _pub_pair(
    t10b_modules: Any,
    *,
    preflight_id: str,
    published_id: str,
    full_validation_repeated: bool = True,
    preflight_serving: bool = False,
) -> dict[str, Any]:
    return {
        "preflight": {
            "snapshot_id": preflight_id,
            "snapshot_sha": "a" * 40,
            "closure_sha256": "c" * 64,
            "policy_bundle_id": "sales-policy-bundle",
            "access_policy_revision": "d" * 40,
            "approval_policy_revision": "f" * 40,
            "exact_projection_sha256": "e" * 64,
            "semantic_projection_sha256": "5" * 64,
            "is_preflight": True,
            "serving_allowed": preflight_serving,
        },
        "published": {
            "snapshot_id": published_id,
            "snapshot_sha": "a" * 40,
            "closure_sha256": "c" * 64,
            "policy_bundle_id": "sales-policy-bundle",
            "access_policy_revision": "d" * 40,
            "approval_policy_revision": "f" * 40,
            "exact_projection_sha256": "e" * 64,
            "semantic_projection_sha256": "5" * 64,
            "is_preflight": False,
            "serving_allowed": True,
            "full_validation_repeated": full_validation_repeated,
        },
    }


def test_check_publication_lifecycle_pass(t10b_modules: Any) -> None:
    fixture = {
        "name": "pass",
        "input": _pub_pair(
            t10b_modules,
            preflight_id="11111111-1111-4111-8111-111111111111",
            published_id="22222222-2222-4222-8222-222222222222",
        ),
        "expected": {"status": "PASS"},
    }
    checks = t10b_modules.run_t10b_tests.check_publication_lifecycle([fixture], None)
    assert checks[0].status == "PASS"


def test_check_publication_lifecycle_reused_id_rejected(t10b_modules: Any) -> None:
    fixture = {
        "name": "reused_id",
        "input": _pub_pair(
            t10b_modules,
            preflight_id="11111111-1111-4111-8111-111111111111",
            published_id="11111111-1111-4111-8111-111111111111",
        ),
        "expected": {"status": "FAIL", "error": "INVALID_STATE"},
    }
    checks = t10b_modules.run_t10b_tests.check_publication_lifecycle([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def _cas_fixture(
    *,
    same_fence: bool = True,
    latest_ancestry: bool = True,
    validated_snapshot: bool = True,
    single_writer: bool = True,
    rows_updated: int = 1,
    stale_marked: bool = False,
) -> dict[str, Any]:
    return {
        "current_pointer": {
            "fence": "00000000-0000-4000-8000-000000000000",
            "snapshot_sha": "a" * 40,
            "generation_id": "gen-sales-1",
            "profile_version": "pgvector-fts-v1",
        },
        "publisher": {
            "expected_fence": "00000000-0000-4000-8000-000000000000",
            "latest_ancestry": latest_ancestry,
            "validated_snapshot": validated_snapshot,
            "single_writer": single_writer,
        },
        "result": {
            "pointer_rows_updated": rows_updated,
            "stale_job_marked_superseded": stale_marked,
        },
    }


def test_check_pointer_cas_fencing_pass(t10b_modules: Any) -> None:
    fixture = {"name": "pass", "input": _cas_fixture(), "expected": {"status": "PASS"}}
    checks = t10b_modules.run_t10b_tests.check_pointer_cas_fencing([fixture], None)
    assert checks[0].status == "PASS"


def test_check_pointer_cas_fencing_stale_fence_expected_fail(t10b_modules: Any) -> None:
    fixture = {
        "name": "stale_fence",
        "input": {
            "current_pointer": {
                "fence": "11111111-1111-4111-8111-111111111111",
                "snapshot_sha": "b" * 40,
                "generation_id": "gen-sales-2",
                "profile_version": "pgvector-fts-v1",
            },
            "publisher": {
                "expected_fence": "00000000-0000-4000-8000-000000000000",
                "latest_ancestry": True,
                "validated_snapshot": True,
                "single_writer": True,
            },
            "result": {"pointer_rows_updated": 0, "stale_job_marked_superseded": True},
        },
        "expected": {"status": "PASS"},
    }
    checks = t10b_modules.run_t10b_tests.check_pointer_cas_fencing([fixture], None)
    assert checks[0].status == "PASS"


def test_check_pointer_cas_fencing_rows_zero_unexpected_fail(t10b_modules: Any) -> None:
    fixture = {
        "name": "rows_zero",
        "input": _cas_fixture(rows_updated=0, stale_marked=False),
        "expected": {"status": "FAIL", "error": "INDEX_GENERATION_CONFLICT"},
    }
    checks = t10b_modules.run_t10b_tests.check_pointer_cas_fencing([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_pointer_cas_fencing_error_mismatch_is_unexpected(t10b_modules: Any) -> None:
    fixture = {
        "name": "rows_zero_mismatch",
        "input": _cas_fixture(rows_updated=0, stale_marked=False),
        "expected": {"status": "FAIL", "error": "STALE_BASE"},
    }
    checks = t10b_modules.run_t10b_tests.check_pointer_cas_fencing([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is not True


def test_check_per_space_retrieval_pass(t10b_modules: Any) -> None:
    fixture = {
        "name": "pass",
        "input": {
            "snapshots": [{"state": "active", "serving_allowed": True, "included": True}],
            "candidates": [{"returned": True, "reauthorized": True}],
            "citations": [
                {
                    "space_id": "sales",
                    "document_id": "11111111-1111-4111-8111-111111111111",
                    "revision_sha": "a" * 40,
                    "range": "section-1",
                }
            ],
            "cross_space_leak": False,
        },
        "expected": {"status": "PASS"},
    }
    checks = t10b_modules.run_t10b_tests.check_per_space_retrieval([fixture], None)
    assert checks[0].status == "PASS"


def test_check_per_space_retrieval_empty_inactive_pass(t10b_modules: Any) -> None:
    fixture = {
        "name": "empty_inactive",
        "input": {
            "snapshots": [{"state": "ready", "serving_allowed": False, "inactive": True, "included": True}],
            "candidates": [],
            "citations": [],
            "cross_space_leak": False,
        },
        "expected": {"status": "PASS"},
    }
    checks = t10b_modules.run_t10b_tests.check_per_space_retrieval([fixture], None)
    assert checks[0].status == "PASS"


def test_check_per_space_retrieval_stale_snapshot_expected_fail(t10b_modules: Any) -> None:
    fixture = {
        "name": "stale",
        "input": {
            "snapshots": [{"state": "superseded", "serving_allowed": False, "included": True}],
            "candidates": [{"returned": True, "reauthorized": True}],
            "citations": [],
            "cross_space_leak": False,
        },
        "expected": {"status": "FAIL", "error": "STALE_INDEX_CANDIDATE"},
    }
    checks = t10b_modules.run_t10b_tests.check_per_space_retrieval([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_per_space_retrieval_unauthorized_expected_fail(t10b_modules: Any) -> None:
    fixture = {
        "name": "unauthorized",
        "input": {
            "snapshots": [{"state": "active", "serving_allowed": True, "included": True}],
            "candidates": [{"returned": True, "reauthorized": False}],
            "citations": [],
            "cross_space_leak": False,
        },
        "expected": {"status": "FAIL", "error": "AUTHZ_GROUP_STALE"},
    }
    checks = t10b_modules.run_t10b_tests.check_per_space_retrieval([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_per_space_retrieval_cross_space_expected_fail(t10b_modules: Any) -> None:
    fixture = {
        "name": "cross_space",
        "input": {
            "snapshots": [{"state": "active", "serving_allowed": True, "included": True}],
            "candidates": [{"returned": True, "reauthorized": True}],
            "citations": [
                {
                    "space_id": "hr",
                    "document_id": "11111111-1111-4111-8111-111111111111",
                    "revision_sha": "a" * 40,
                    "range": "section-1",
                }
            ],
            "cross_space_leak": True,
        },
        "expected": {"status": "FAIL", "error": "SECURITY_REJECTED"},
    }
    checks = t10b_modules.run_t10b_tests.check_per_space_retrieval([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_per_space_retrieval_error_mismatch_is_unexpected(t10b_modules: Any) -> None:
    fixture = {
        "name": "cross_space_mismatch",
        "input": {
            "snapshots": [{"state": "active", "serving_allowed": True, "included": True}],
            "candidates": [{"returned": True, "reauthorized": True}],
            "citations": [
                {
                    "space_id": "hr",
                    "document_id": "11111111-1111-4111-8111-111111111111",
                    "revision_sha": "a" * 40,
                    "range": "section-1",
                }
            ],
            "cross_space_leak": True,
        },
        "expected": {"status": "FAIL", "error": "STALE_INDEX_CANDIDATE"},
    }
    checks = t10b_modules.run_t10b_tests.check_per_space_retrieval([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is not True


def test_check_cursor_binding_pass(t10b_modules: Any) -> None:
    fixture = {
        "name": "pass",
        "input": {
            "cursor_binding": {
                "snapshot_ids": ["11111111-1111-4111-8111-111111111111"],
                "profile_version": "pgvector-fts-v1",
                "policy_bundle_id": "sales-policy-bundle",
                "access_policy_revision": "d" * 40,
                "approval_policy_revision": "f" * 40,
                "group_epoch": 7,
                "revocation_epoch": 42,
                "actor_epoch": 3,
            },
            "stale_binding": False,
            "continuation": {"limit_exceeded": True, "has_more": True, "next_cursor": "cursor-page-2"},
        },
        "expected": {"status": "PASS"},
    }
    checks = t10b_modules.run_t10b_tests.check_cursor_binding([fixture], None)
    assert checks[0].status == "PASS"


def test_check_cursor_binding_missing_actor_epoch_fail(t10b_modules: Any) -> None:
    fixture = {
        "name": "missing_actor",
        "input": {
            "cursor_binding": {
                "snapshot_ids": ["11111111-1111-4111-8111-111111111111"],
                "profile_version": "pgvector-fts-v1",
                "policy_bundle_id": "sales-policy-bundle",
                "access_policy_revision": "d" * 40,
                "approval_policy_revision": "f" * 40,
                "group_epoch": 7,
                "revocation_epoch": 42,
            },
            "stale_binding": False,
            "continuation": {},
        },
        "expected": {"status": "FAIL", "error": "STALE_INDEX_CANDIDATE"},
    }
    checks = t10b_modules.run_t10b_tests.check_cursor_binding([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_check_index_not_ready_pass(t10b_modules: Any) -> None:
    fixture = {
        "name": "no_active",
        "input": {
            "space_state": "no_active_snapshot",
            "result": {"code": "INDEX_NOT_READY", "retryable": True},
        },
        "expected": {"status": "PASS"},
    }
    checks = t10b_modules.run_t10b_tests.check_index_not_ready([fixture], None)
    assert checks[0].status == "PASS"


def test_check_index_not_ready_silent_truncation_fail(t10b_modules: Any) -> None:
    fixture = {
        "name": "silent",
        "input": {
            "space_state": "limit_exceeded",
            "result": {"code": "none", "retryable": False, "truncated": True, "next_cursor": None},
        },
        "expected": {"status": "FAIL", "error": "LIMIT_EXCEEDED"},
    }
    checks = t10b_modules.run_t10b_tests.check_index_not_ready([fixture], None)
    assert checks[0].status == "FAIL"
    assert checks[0].details.get("expected_negative") is True


def test_run_schema_checks_valid(t10b_modules: Any) -> None:
    sv = t10b_modules.run_t10b_tests.SchemaValidator(
        Path("specs/corporate-kb/contracts")
    )
    if sv.load_errors:
        pytest.skip(f"schema load errors: {sv.load_errors}")
    checks = t10b_modules.run_t10b_tests.run_schema_checks(sv)
    assert any(c.id == "schema.preflight.valid" and c.status == "PASS" for c in checks)
    assert any(c.id == "schema.published.valid" and c.status == "PASS" for c in checks)
