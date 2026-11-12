"""G1 API fault-matrix tests (A05–A10 / A27–A30 + concurrency scenarios).

These tests provide deterministic synthetic closure of the deferred API lifecycle
fault matrix using the FastAPI TestClient and the in-memory stub GitLab adapter.
Live GitLab acceptance stays optional and gated by G1_ALLOW_DESTRUCTIVE_RESET.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from git_orchestrator.app.adapters.gitlab import StubGitLabAdapter
from git_orchestrator.app.api.auth import AuthenticatedIdentity, get_current_identity


@pytest.fixture
def space_id() -> str:
    return "demo-space"


@pytest.fixture
def proposal_base() -> dict[str, Any]:
    return {
        "space_id": "demo-space",
        "proposal_sha": "a" * 40,
        "base_sha": "b" * 40,
        "target_sha": "c" * 40,
        "target_branch": "main",
        "idempotency_key": "proposal-1",
        "proposal_data": {
            "author_stable_id": "author-1",
            "requester_stable_id": "author-1",
        },
    }


@pytest.fixture
def submitted_proposal(
    client: TestClient, proposal_base: dict[str, Any]
) -> dict[str, Any]:
    """Return a proposal that has been submitted via the API."""
    resp = client.post("/api/kb/v1/proposals", json=proposal_base)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def accepted_proposal(
    client: TestClient, proposal_base: dict[str, Any]
) -> tuple[str, StubGitLabAdapter]:
    """Return an accepted proposal id and the stub adapter."""
    proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
    assert proposal_resp.status_code == 201, proposal_resp.text
    proposal_id = proposal_resp.json()["id"]

    decision_resp = client.post(
        "/api/kb/v1/decisions",
        json={
            "proposal_id": proposal_id,
            "action": "accepted",
            "actor_id": "approver-1",
            "idempotency_key": "decision-1",
        },
    )
    assert decision_resp.status_code == 201, decision_resp.text
    return proposal_id, client.app.state.gitlab_adapter


class TestFaultMatrixInvalidStateTransitions:
    """A05: Merge requested before a decision exists."""

    def test_merge_before_decision_rejected(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")

        assert resp.status_code == 409, resp.text
        detail = resp.json()["detail"]
        assert detail["code"] == "INVALID_STATE"
        assert "request_id" in detail
        assert "retryable" in detail

    def test_merge_after_rejected_decision_rejected(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        reject_resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "decision-reject",
            },
        )
        assert reject_resp.status_code == 201, reject_resp.text

        merge_resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert merge_resp.status_code == 409
        assert merge_resp.json()["detail"]["code"] == "INVALID_STATE"


class TestFaultMatrixActorMismatch:
    """A06: Decision actor does not match the authenticated approver."""

    def test_decision_actor_spoofing_rejected(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "attacker-1",
                "idempotency_key": "decision-spoof",
            },
        )

        assert resp.status_code == 403, resp.text
        detail = resp.json()["detail"]
        assert detail["code"] == "ACTOR_MISMATCH"
        assert detail["retryable"] is False

    def test_proposal_author_binding_rejects_spoofed_author(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        spoofed = {
            **proposal_base,
            "proposal_data": {
                **proposal_base["proposal_data"],
                "author_stable_id": "attacker-1",
            },
        }

        resp = client.post("/api/kb/v1/proposals", json=spoofed)

        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"]["code"] == "ACTOR_MISMATCH"


class TestFaultMatrixSelfApproval:
    """A07: Author attempts to approve their own proposal."""

    def test_author_cannot_accept_own_proposal(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]
        author_id = submitted_proposal["proposal_data"]["author_stable_id"]

        client.app.dependency_overrides[get_current_identity] = (
            lambda: AuthenticatedIdentity(stable_id=author_id, role="admin")
        )

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": author_id,
                "idempotency_key": "decision-self",
            },
        )

        assert resp.status_code == 403, resp.text
        detail = resp.json()["detail"]
        assert detail["code"] == "SELF_APPROVAL"
        assert detail["retryable"] is False

        # No decision anchors should have been written.
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        assert not any(key[0] in {"note", "tag"} for key in stub_adapter.state)


class TestFaultMatrixIdempotency:
    """A08: Idempotency key reuse with a different payload."""

    def test_proposal_idempotency_key_reused_with_different_sha(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        r1 = client.post("/api/kb/v1/proposals", json=proposal_base)
        assert r1.status_code == 201, r1.text

        conflict = {**proposal_base, "proposal_sha": "d" * 40}
        r2 = client.post("/api/kb/v1/proposals", json=conflict)

        assert r2.status_code == 409, r2.text
        detail = r2.json()["detail"]
        assert detail["code"] == "IDEMPOTENCY_KEY_REUSED"
        assert detail["retryable"] is False

    def test_decision_idempotency_key_reused_with_different_action(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        r1 = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "shared-key",
            },
        )
        assert r1.status_code == 201, r1.text

        r2 = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "shared-key",
            },
        )

        assert r2.status_code == 409, r2.text
        assert r2.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"


class TestFaultMatrixConcurrentDecisions:
    """A09: Two decision requests for the same proposal without supersede."""

    def test_second_decision_for_same_proposal_rejected(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        r1 = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-first",
            },
        )
        assert r1.status_code == 201, r1.text

        r2 = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-second",
            },
        )

        assert r2.status_code == 409, r2.text
        assert r2.json()["detail"]["code"] == "INVALID_STATE"

    def test_second_decision_idempotent_when_identical_key(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]
        decision = {
            "proposal_id": proposal_id,
            "action": "accepted",
            "actor_id": "approver-1",
            "idempotency_key": "decision-idempotent",
        }

        r1 = client.post("/api/kb/v1/decisions", json=decision)
        r2 = client.post("/api/kb/v1/decisions", json=decision)

        assert r1.status_code == 201, r1.text
        assert r2.status_code == 201, r2.text
        assert r1.json()["id"] == r2.json()["id"]


class TestFaultMatrixMalformedPayload:
    """A10: Proposal SHA does not match the 40-hex contract."""

    def test_invalid_proposal_sha_returns_422(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        bad = {**proposal_base, "proposal_sha": "not-a-sha"}

        resp = client.post("/api/kb/v1/proposals", json=bad)

        assert resp.status_code == 422, resp.text

    def test_short_proposal_sha_returns_422(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        bad = {**proposal_base, "proposal_sha": "a" * 39}

        resp = client.post("/api/kb/v1/proposals", json=bad)

        assert resp.status_code == 422, resp.text


class TestFaultMatrixRejectDecision:
    """A27: Rejected decision persists and blocks merge."""

    def test_rejected_decision_persisted_and_blocks_merge(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "decision-reject-a27",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["outcome"] == "rejected"
        assert body["state"] == "recorded"

        get_resp = client.get(f"/api/kb/v1/proposals/{proposal_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "rejected"

        merge_resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert merge_resp.status_code == 409
        assert merge_resp.json()["detail"]["code"] == "INVALID_STATE"


class TestFaultMatrixCancelSupersede:
    """A28: A new decision can supersede a prior decision and govern the proposal."""

    def test_supersede_rejected_with_accepted_and_merge(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        assert proposal_resp.status_code == 201, proposal_resp.text
        proposal_id = proposal_resp.json()["id"]

        # First decision rejects the proposal.
        reject_resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "decision-reject-a28",
            },
        )
        assert reject_resp.status_code == 201, reject_resp.text
        prior_decision_id = reject_resp.json()["id"]

        # Merge is blocked while rejected.
        merge_resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert merge_resp.status_code == 409

        # A new accepted decision supersedes the rejection.
        supersede_resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-accept-a28",
                "supersedes_decision_id": str(prior_decision_id),
            },
        )
        assert supersede_resp.status_code == 201, supersede_resp.text
        new_decision = supersede_resp.json()
        assert new_decision["outcome"] == "accepted"
        assert str(new_decision["supersedes_decision_id"]) == str(prior_decision_id)

        # Proposal is back in_review and can merge.
        get_resp = client.get(f"/api/kb/v1/proposals/{proposal_id}")
        assert get_resp.json()["status"] == "in_review"

        merge_sha = "m" * 40
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("commit", proposal_base["space_id"], merge_sha)] = {
            "id": merge_sha,
            "parent_ids": [proposal_base["base_sha"], proposal_base["proposal_sha"]],
        }
        original_merge = stub_adapter.merge_merge_request

        def _verified_merge(
            space_id: str, mr_iid: int, sha: str, merge_commit_message: str | None = None
        ) -> dict[str, Any]:
            mr = original_merge(space_id, mr_iid, sha, merge_commit_message)
            mr["merge_commit_sha"] = merge_sha
            return mr

        stub_adapter.merge_merge_request = _verified_merge  # type: ignore[assignment]

        merge_resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert merge_resp.status_code == 200, merge_resp.text
        assert merge_resp.json()["status"] == "merged"

    def test_supersede_wrong_prior_decision_rejected(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        reject_resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "decision-reject-a28-wrong",
            },
        )
        assert reject_resp.status_code == 201, reject_resp.text

        fake_prior_id = uuid.uuid4()
        supersede_resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-accept-a28-wrong",
                "supersedes_decision_id": str(fake_prior_id),
            },
        )
        assert supersede_resp.status_code == 409
        assert supersede_resp.json()["detail"]["code"] == "INVALID_STATE"

    def test_supersede_without_prior_decision_rejected(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        proposal_id = submitted_proposal["id"]

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-supersede-no-prior",
                "supersedes_decision_id": str(uuid.uuid4()),
            },
        )

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_supersede_already_merged_proposal_rejected(
        self,
        client: TestClient,
        accepted_proposal: tuple[str, StubGitLabAdapter],
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_id, stub_adapter = accepted_proposal

        merge_sha = "m" * 40
        stub_adapter.state[("commit", proposal_base["space_id"], merge_sha)] = {
            "id": merge_sha,
            "parent_ids": [proposal_base["base_sha"], proposal_base["proposal_sha"]],
        }
        original_merge = stub_adapter.merge_merge_request

        def _verified_merge(
            space_id: str, mr_iid: int, sha: str, merge_commit_message: str | None = None
        ) -> dict[str, Any]:
            mr = original_merge(space_id, mr_iid, sha, merge_commit_message)
            mr["merge_commit_sha"] = merge_sha
            return mr

        stub_adapter.merge_merge_request = _verified_merge  # type: ignore[assignment]

        merge_resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert merge_resp.status_code == 200, merge_resp.text

        # We only need a stable uuid that is not the prior decision id.
        prior_id = uuid.uuid4()

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "decision-supersede-merged",
                "supersedes_decision_id": str(prior_id),
            },
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "INVALID_STATE"


class TestFaultMatrixConcurrentMergeBarrier:
    """A29/A30: Recovery barrier blocks merges after an unknown merge outcome."""

    def test_recovery_required_blocks_new_merge_on_same_target(
        self,
        client: TestClient,
        accepted_proposal: tuple[str, StubGitLabAdapter],
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_id, adapter = accepted_proposal
        adapter.state[("merge_fail", proposal_base["space_id"], 1)] = True

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "MERGE_UNKNOWN_OUTCOME"
        assert resp.json()["detail"]["retryable"] is True

        # A subsequent merge attempt is blocked by the recovery barrier.
        resp2 = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp2.status_code == 409
        assert resp2.json()["detail"]["code"] == "RECOVERY_REQUIRED"

    def test_base_mismatch_blocks_merge(
        self,
        client: TestClient,
        accepted_proposal: tuple[str, StubGitLabAdapter],
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_id, adapter = accepted_proposal
        adapter.state[("branch", proposal_base["space_id"], "main")] = {
            "name": "main",
            "commit": {"id": "z" * 40},
        }

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["code"] == "BASE_MISMATCH"
        assert detail["retryable"] is True


class TestFaultMatrixErrorShape:
    """All new fault cases return the unified error shape."""

    def test_domain_error_includes_code_message_request_id_retryable(
        self,
        client: TestClient,
        submitted_proposal: dict[str, Any],
    ) -> None:
        resp = client.post(f"/api/kb/v1/proposals/{submitted_proposal['id']}/merge")

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert set(detail.keys()) >= {"code", "message", "request_id", "retryable"}
        assert isinstance(detail["request_id"], str)
        assert len(detail["request_id"]) == 32
        assert isinstance(detail["retryable"], bool)

    def test_adapter_error_includes_unified_shape(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("mr_create_fail", proposal_base["space_id"])] = True

        resp = client.post("/api/kb/v1/proposals", json=proposal_base)

        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert set(detail.keys()) >= {"code", "message", "request_id", "retryable"}
