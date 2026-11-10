"""Fault-injection and recovery tests for the Git Orchestrator G1 slice.

These tests exercise durability barriers, crash recovery, and reconciliation
using the stub adapter so they run without a live GitLab instance.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from git_orchestrator.app.adapters.gitlab import StubGitLabAdapter


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
def accepted_proposal(
    client: TestClient,
    proposal_base: dict[str, Any],
) -> tuple[str, StubGitLabAdapter]:
    """Create an accepted proposal and return its id plus the stub adapter."""
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


class TestReconcileMerge:
    """Crash recovery: GitLab merged the MR but the GO process lost the result."""

    def _force_quarantine(
        self,
        client: TestClient,
        proposal_id: str,
        adapter: StubGitLabAdapter,
        proposal_base: dict[str, Any],
    ) -> None:
        adapter.state[("merge_fail", proposal_base["space_id"], 1)] = True
        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "MERGE_UNKNOWN_OUTCOME"

    def test_reconcile_finds_merge_commit(
        self,
        client: TestClient,
        accepted_proposal: tuple[str, StubGitLabAdapter],
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_id, adapter = accepted_proposal
        self._force_quarantine(client, proposal_id, adapter, proposal_base)

        # GitLab eventually reports a merge commit with correct parentage.
        merge_sha = "m" * 40
        adapter.state[("commit", proposal_base["space_id"], merge_sha)] = {
            "id": merge_sha,
            "parent_ids": [proposal_base["base_sha"], proposal_base["proposal_sha"]],
        }
        adapter.state[("branch", proposal_base["space_id"], "main")] = {
            "name": "main",
            "commit": {"id": merge_sha},
        }

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/reconcile")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "merged"
        assert body["merge_sha"] == merge_sha
        assert body["detail"] == "reconciled from Git: merge commit found with correct parentage"

        # Reconciled state is durable: replay returns the same Git-derived result.
        resp2 = client.post(f"/api/kb/v1/proposals/{proposal_id}/merge")
        assert resp2.status_code == 200
        assert resp2.json()["merge_sha"] == merge_sha
        assert resp2.json()["detail"] == "idempotent merge replay"

    def test_reconcile_conflicted_when_first_parent_changed(
        self,
        client: TestClient,
        accepted_proposal: tuple[str, StubGitLabAdapter],
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_id, adapter = accepted_proposal
        self._force_quarantine(client, proposal_id, adapter, proposal_base)

        # Someone merged something else first; the proposal's merge commit now
        # has a different first parent.
        merge_sha = "m" * 40
        adapter.state[("commit", proposal_base["space_id"], merge_sha)] = {
            "id": merge_sha,
            "parent_ids": ["z" * 40, proposal_base["proposal_sha"]],
        }
        adapter.state[("branch", proposal_base["space_id"], "main")] = {
            "name": "main",
            "commit": {"id": merge_sha},
        }

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/reconcile")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "conflicted"
        assert "first parent does not match base" in body["detail"]

    def test_reconcile_still_unknown_when_no_merge_commit_found(
        self,
        client: TestClient,
        accepted_proposal: tuple[str, StubGitLabAdapter],
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_id, adapter = accepted_proposal
        self._force_quarantine(client, proposal_id, adapter, proposal_base)

        # Target HEAD is some unrelated commit with no merge commit in history.
        adapter.state[("branch", proposal_base["space_id"], "main")] = {
            "name": "main",
            "commit": {"id": "z" * 40},
        }
        adapter.state[("commit", proposal_base["space_id"], "z" * 40)] = {
            "id": "z" * 40,
            "parent_ids": ["y" * 40],
        }
        adapter.state[("commit", proposal_base["space_id"], "y" * 40)] = {
            "id": "y" * 40,
            "parent_ids": [],
        }

        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/reconcile")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "quarantined"
        assert body["merge_sha"] is None
        assert "still unknown" in body["detail"]

    def test_reconcile_rejected_when_decision_not_quarantined(
        self,
        client: TestClient,
        accepted_proposal: tuple[str, StubGitLabAdapter],
        proposal_base: dict[str, Any],
    ) -> None:
        proposal_id, _adapter = accepted_proposal
        resp = client.post(f"/api/kb/v1/proposals/{proposal_id}/reconcile")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "INVALID_STATE"


class TestConcurrentMergeBarrier:
    """Durability barrier prevents a second merge on the same target."""

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

        # A brand new proposal can still be submitted (edits are not blocked).
        new_proposal = {
            **proposal_base,
            "proposal_sha": "d" * 40,
            "idempotency_key": "proposal-2",
        }
        source_branch = f"proposal/{new_proposal['proposal_sha'][:8]}"
        adapter.state[("branch", proposal_base["space_id"], source_branch)] = True
        resp2 = client.post("/api/kb/v1/proposals", json=new_proposal)
        assert resp2.status_code == 201, resp2.text
        new_proposal_id = resp2.json()["id"]

        # But merging it is blocked until recovery is cleared.
        client.post(
            "/api/kb/v1/decisions",
            json={
                "proposal_id": new_proposal_id,
                "action": "accepted",
                "actor_id": "approver-1",
                "idempotency_key": "decision-2",
            },
        )
        resp3 = client.post(f"/api/kb/v1/proposals/{new_proposal_id}/merge")
        assert resp3.status_code == 409
        assert resp3.json()["detail"]["code"] == "RECOVERY_REQUIRED"
