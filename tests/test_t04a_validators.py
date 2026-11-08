"""Unit tests for T04a idempotency and stale-base validators."""

from __future__ import annotations

from typing import Any


def test_idempotency_same_payload_replay(t04a_modules: Any) -> None:
    fixture = {
        "name": "replay",
        "input": {
            "idempotency_key": "key1",
            "payload_hash": "abc123",
        },
        "state": {
            "existing_drafts": [
                {
                    "idempotency_key": "key1",
                    "payload_hash": "abc123",
                    "proposal_sha": "sha1",
                }
            ]
        },
        "expected": {"status": "PASS"},
    }
    checks = t04a_modules.idempotency.IdempotencyValidator([fixture]).validate()

    assert len(checks) == 1
    assert checks[0].status == "PASS"
    assert checks[0].details["duplicate_commit"] is False


def test_idempotency_key_reused(t04a_modules: Any) -> None:
    fixture = {
        "name": "reused",
        "input": {
            "idempotency_key": "key1",
            "payload_hash": "different-hash",
        },
        "state": {
            "existing_drafts": [
                {
                    "idempotency_key": "key1",
                    "payload_hash": "original-hash",
                }
            ]
        },
        "expected": {"status": "IDEMPOTENCY_KEY_REUSED"},
    }
    checks = t04a_modules.idempotency.IdempotencyValidator([fixture]).validate()

    assert len(checks) == 1
    assert checks[0].status == "PASS"


def test_stale_base_conflict_detected(t04a_modules: Any) -> None:
    fixture = {
        "name": "stale",
        "input": {"base_sha": "oldsha"},
        "state": {
            "target_head": "newsha",
            "target_history": ["newsha"],
        },
        "expected": {"status": "STALE_BASE", "diff_view": True},
    }
    checks = t04a_modules.stale_base.StaleBaseValidator([fixture]).validate()

    conflict = next(c for c in checks if c.id == "stale_base.stale.conflict_detected")
    assert conflict.status == "PASS"
    assert conflict.details["silent_overwrite"] is False
    assert conflict.details["diff_view"] is True


def test_stale_base_no_silent_overwrite(t04a_modules: Any) -> None:
    fixture = {
        "name": "no_overwrite",
        "input": {"base_sha": "oldsha"},
        "state": {
            "target_head": "newsha",
            "target_history": ["newsha"],
        },
        "expected": {"status": "FAIL"},
    }
    checks = t04a_modules.stale_base.StaleBaseValidator([fixture]).validate()

    no_overwrite = next(
        c for c in checks if c.id == "stale_base.no_overwrite.no_silent_overwrite"
    )
    assert no_overwrite.status == "PASS"
    assert no_overwrite.details["silent_overwrite"] is False


def test_stale_base_fresh_base(t04a_modules: Any) -> None:
    fixture = {
        "name": "fresh",
        "input": {"base_sha": "currentsha"},
        "state": {
            "target_head": "currentsha",
            "target_history": ["currentsha"],
        },
        "expected": {"status": "STALE_BASE"},
    }
    checks = t04a_modules.stale_base.StaleBaseValidator([fixture]).validate()

    conflict = next(c for c in checks if c.id == "stale_base.fresh.conflict_detected")
    assert conflict.status == "FAIL"
