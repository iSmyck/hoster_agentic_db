"""Idempotency validator: replay semantics and duplicate commit prevention."""

from __future__ import annotations

from typing import Any

from .base import ValidatorCheck


class IdempotencyValidator:
    """Validate idempotent save/replay fixtures."""

    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def validate(self) -> list[ValidatorCheck]:
        checks: list[ValidatorCheck] = []
        for fixture in self.fixtures:
            name = fixture.get("name", "unnamed")
            inp = fixture.get("input", {})
            state = fixture.get("state", {})
            expected = fixture.get("expected", {})
            expected_status = expected.get("status", "PASS")

            key = inp.get("idempotency_key")
            payload_hash = inp.get("payload_hash")
            existing = {
                d["idempotency_key"]: d
                for d in state.get("existing_drafts", [])
                if isinstance(d, dict) and "idempotency_key" in d
            }
            existing_draft = existing.get(key)

            if expected_status == "PASS":
                # Same key + same payload must return existing draft, no duplicate commit.
                if (
                    existing_draft
                    and existing_draft.get("payload_hash") == payload_hash
                ):
                    checks.append(
                        ValidatorCheck(
                            id=f"idempotency.{name}.same_payload_replay",
                            status="PASS",
                            expected="existing draft returned, no duplicate commit",
                            actual="idempotency key matches existing draft with identical payload",
                            details={
                                "idempotency_key": key,
                                "existing_proposal_sha": existing_draft.get("proposal_sha"),
                                "duplicate_commit": False,
                            },
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"idempotency.{name}.same_payload_replay",
                            status="FAIL",
                            expected="existing draft returned, no duplicate commit",
                            actual="no matching existing draft with identical payload",
                            details={
                                "idempotency_key": key,
                                "existing_payload_hash": existing_draft.get("payload_hash")
                                if existing_draft
                                else None,
                                "input_payload_hash": payload_hash,
                            },
                        )
                    )
            elif expected_status == "IDEMPOTENCY_KEY_REUSED":
                # Same key + different payload must be rejected.
                if existing_draft and existing_draft.get("payload_hash") != payload_hash:
                    checks.append(
                        ValidatorCheck(
                            id=f"idempotency.{name}.different_payload_rejected",
                            status="PASS",
                            expected="IDEMPOTENCY_KEY_REUSED when payload differs",
                            actual="idempotency key reused with different payload",
                            details={
                                "idempotency_key": key,
                                "existing_payload_hash": existing_draft.get("payload_hash"),
                                "input_payload_hash": payload_hash,
                            },
                        )
                    )
                else:
                    checks.append(
                        ValidatorCheck(
                            id=f"idempotency.{name}.different_payload_rejected",
                            status="FAIL",
                            expected="IDEMPOTENCY_KEY_REUSED when payload differs",
                            actual="key not reused or payload hashes match",
                            details={
                                "idempotency_key": key,
                                "existing_payload_hash": existing_draft.get("payload_hash")
                                if existing_draft
                                else None,
                                "input_payload_hash": payload_hash,
                            },
                        )
                    )
            else:
                checks.append(
                    ValidatorCheck(
                        id=f"idempotency.{name}.unexpected_expected_status",
                        status="FAIL",
                        expected="expected status PASS or IDEMPOTENCY_KEY_REUSED",
                        actual=f"unexpected expected status {expected_status}",
                        details={},
                    )
                )

        return checks
