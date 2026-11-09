"""End-to-end MVP tests for the Git Orchestrator adapter."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from git_orchestrator.app.adapters.gitlab import StubGitLabAdapter


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
            "requester_stable_id": "requester-1",
        },
    }


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDocumentRead:
    def test_read_document_exact_sha(
        self,
        client: TestClient,
        stub_adapter: StubGitLabAdapter,
        space_id: str,
    ) -> None:
        stub_adapter.state[("doc", space_id, "docs/page.md", "a" * 40)] = "hello"
        resp = client.post(
            "/api/kb/v1/documents/read",
            json={"space_id": space_id, "path": "docs/page.md", "sha": "a" * 40},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["content"] == "hello"
        assert body["sha"] == "a" * 40


class TestTree:
    def test_get_tree(
        self,
        client: TestClient,
        stub_adapter: StubGitLabAdapter,
        space_id: str,
    ) -> None:
        stub_adapter.state[("tree", space_id, "a" * 40)] = [
            {"path": "docs", "type": "tree", "sha": "d" * 40, "mode": "040000"},
            {"path": "docs/page.md", "type": "blob", "sha": "e" * 40, "mode": "100644"},
        ]
        resp = client.post(
            "/api/kb/v1/documents/tree",
            json={"space_id": space_id, "sha": "a" * 40},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["entries"]) == 2
        assert body["entries"][0]["path"] == "docs"


class TestProposals:
    def test_submit_proposal(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["space_id"] == proposal_base["space_id"]
        assert body["proposal_sha"] == proposal_base["proposal_sha"]
        assert body["status"] == "in_review"
        assert body["idempotency_key"] == proposal_base["idempotency_key"]

    def test_submit_proposal_is_idempotent(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        r1 = client.post("/api/kb/v1/proposals", json=proposal_base)
        r2 = client.post("/api/kb/v1/proposals", json=proposal_base)
        assert r1.json()["id"] == r2.json()["id"]

    def test_idempotency_key_reused_with_different_payload(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/proposals", json=proposal_base)
        conflict = {**proposal_base, "proposal_sha": "d" * 40}
        resp = client.post("/api/kb/v1/proposals", json=conflict)
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    def test_source_branch_not_found(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        source_branch = f"proposal/{proposal_base['proposal_sha'][:8]}"
        stub_adapter.state[("branch", proposal_base["space_id"], source_branch)] = False

        resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "SOURCE_BRANCH_NOT_FOUND"

    def test_mr_create_failure_rolls_back_db(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("mr_create_fail", proposal_base["space_id"])] = True

        resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "MR_CREATE_FAILED"

        # The idempotency key should be reusable because the transaction rolled back.
        del stub_adapter.state[("mr_create_fail", proposal_base["space_id"])]
        retry = client.post("/api/kb/v1/proposals", json=proposal_base)
        assert retry.status_code == 201


class TestDecisions:
    def test_record_accepted_decision(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-1",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["proposal_id"] == proposal_id
        assert body["outcome"] == "accepted"
        assert body["actor_id"] == "approver-1"

    def test_rejected_decision_closes_proposal(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "decision-2",
            },
        )
        assert resp.status_code == 201, resp.text

        # A rejected proposal no longer has an accepted decision, so merge
        # must refuse with INVALID_STATE.
        merge_resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert merge_resp.status_code == 409

    def test_decision_idempotency(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]
        decision = {
            "proposal_id": proposal_id,
            "action": "accepted",
            "actor_id": "approver-1",
            "idempotency_key": "decision-3",
        }
        r1 = client.post("/api/kb/v1/decisions", json=decision)
        r2 = client.post("/api/kb/v1/decisions", json=decision)
        assert r1.json()["id"] == r2.json()["id"]

    def test_decision_idempotency_conflict_different_proposal(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        p1 = client.post("/api/kb/v1/proposals", json=proposal_base)
        p2 = client.post(
            "/api/kb/v1/proposals",
            json={**proposal_base, "idempotency_key": "proposal-other"},
        )
        pid1 = p1.json()["id"]
        pid2 = p2.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": pid1,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "shared-key",
            },
        )

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": pid2,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "shared-key",
            },
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    def test_decision_idempotency_conflict_different_action(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "shared-action-key",
            },
        )

        resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "rejected",
                "actor_id": "approver-1",
                "idempotency_key": "shared-action-key",
            },
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"


class TestMerge:
    def test_merge_succeeds_with_accepted_decision(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        decision_resp = client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-merge-ok",
            },
        )
        assert decision_resp.status_code == 201
        decision_id = decision_resp.json()["id"]

        # Stub a verified merge commit with correct parentage.
        merge_sha = "m" * 40
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("commit", proposal_base["space_id"], merge_sha)] = {
            "id": merge_sha,
            "parent_ids": [proposal_base["base_sha"], proposal_base["proposal_sha"]],
        }
        # Make the stub return the verified merge SHA.
        original_merge = stub_adapter.merge_merge_request

        def _verified_merge(space_id: str, mr_iid: int, sha: str) -> dict[str, Any]:
            mr = original_merge(space_id, mr_iid, sha)
            mr["sha"] = merge_sha
            return mr

        stub_adapter.merge_merge_request = _verified_merge  # type: ignore[assignment]

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "merged"
        assert body["merge_sha"] == merge_sha
        assert body["recovery_required"] is False
        assert body["fence_token"] is not None

    def test_merge_fails_without_decision(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "INVALID_STATE"

    def test_self_approval_blocked(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": proposal_base["proposal_data"]["author_stable_id"],
                "idempotency_key": "decision-self",
            },
        )

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "SELF_APPROVAL"

    def test_self_approval_blocked_for_requester(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": proposal_base["proposal_data"]["requester_stable_id"],
                "idempotency_key": "decision-self-requester",
            },
        )

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "SELF_APPROVAL"

    def test_base_mismatch_blocks_merge(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-mismatch",
            },
        )

        # Stub MR base_sha defaults to empty, so simulate a stale base.
        # The first MR created by the stub always has iid == 1.
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("mr", proposal_base["space_id"], 1)] = {
            "iid": 1,
            "state": "opened",
            "base_sha": "z" * 40,
        }

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "BASE_MISMATCH"

    def test_merge_failed_returns_502(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-merge-fail",
            },
        )

        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("merge_fail", proposal_base["space_id"], 1)] = True

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "MERGE_UNKNOWN_OUTCOME"

    def test_merge_recovery_required_blocks_subsequent(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-recovery-1",
            },
        )

        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("merge_fail", proposal_base["space_id"], 1)] = True

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 502

        # Second merge attempt is blocked by recovery barrier.
        resp2 = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp2.status_code == 409
        assert resp2.json()["detail"]["code"] == "RECOVERY_REQUIRED"

    def test_remerge_rejected(
        self,
        client: TestClient,
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_resp = client.post("/api/kb/v1/proposals", json=proposal_base)
        proposal_id = proposal_resp.json()["id"]

        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-remerge",
            },
        )

        merge_sha = "m" * 40
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("commit", proposal_base["space_id"], merge_sha)] = {
            "id": merge_sha,
            "parent_ids": [proposal_base["base_sha"], proposal_base["proposal_sha"]],
        }
        original_merge = stub_adapter.merge_merge_request

        def _verified_merge(space_id: str, mr_iid: int, sha: str) -> dict[str, Any]:
            mr = original_merge(space_id, mr_iid, sha)
            mr["sha"] = merge_sha
            return mr

        stub_adapter.merge_merge_request = _verified_merge  # type: ignore[assignment]

        r1 = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert r1.status_code == 200

        r2 = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert r2.status_code == 409
        assert r2.json()["detail"]["code"] == "INVALID_STATE"


class TestMergeRules:
    def test_merge_rules_return_protected(
        self,
        client: TestClient,
        space_id: str,
    ) -> None:
        resp = client.get(f"/api/kb/v1/spaces/{space_id}/merge-rules")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["space_id"] == space_id
        assert body["protected"] is True
        assert body["merge_only"] is True

    def test_direct_push_blocked(
        self,
        client: TestClient,
        space_id: str,
    ) -> None:
        stub_adapter: StubGitLabAdapter = client.app.state.gitlab_adapter
        stub_adapter.state[("rules", space_id)] = {
            "protected": True,
            "merge_only": False,
            "push_access_levels": [{"access_level": 30}],
        }

        resp = client.get(f"/api/kb/v1/spaces/{space_id}/merge-rules")
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "DIRECT_PUSH_BLOCKED"


class TestUnknownProposal:
    def test_merge_unknown_proposal(self, client: TestClient) -> None:
        resp = client.post(f"/api/kb/v1/proposals/{uuid.uuid4()}/merge")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"
