"""End-to-end MVP tests for the Identity + AuthZ adapter."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from identity.app.models.authz import GroupSnapshot, PolicyBundle, Revocation
from identity.app.services import identity_service


@pytest.fixture
def space_id() -> str:
    return "demo-space"


@pytest.fixture
def external_ref() -> dict[str, str]:
    return {"issuer": "test", "sub": "alice"}


@pytest.fixture
def identity_id(client: TestClient, external_ref: dict[str, str]) -> str:
    resp = client.post("/api/kb/v1/identity/resolve", json={"external_ref": external_ref})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


@pytest.fixture
def policy_bundle(space_id: str) -> dict[str, Any]:
    return {
        "space_id": space_id,
        "bundle_id": "bundle-1",
        "repository_id": f"repo-{space_id}",
        "access_policy_revision": "a" * 40,
        "approval_policy_revision": "b" * 40,
        "group_capabilities": {
            "readers": ["read", "search"],
            "authors": ["read", "search", "propose"],
            "approvers": ["read", "search", "propose", "review", "merge"],
        },
        "path_approvers": {
            "approvers": ["/docs", "/docs/pricing"],
        },
    }


@pytest.fixture
def group_snapshot(space_id: str, external_ref: dict[str, str]) -> dict[str, Any]:
    return {
        "space_id": space_id,
        "snapshot_id": str(uuid.uuid4()),
        "groups": [
            {
                "group_name": "readers",
                "member_refs": [external_ref],
                "parent_groups": [],
            },
            {
                "group_name": "authors",
                "member_refs": [],
                "parent_groups": ["readers"],
            },
            {
                "group_name": "approvers",
                "member_refs": [external_ref],
                "parent_groups": [],
            },
        ],
    }


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestIdentityResolve:
    def test_resolve_creates_identity(self, client: TestClient, external_ref: dict[str, str]) -> None:
        resp = client.post("/api/kb/v1/identity/resolve", json={"external_ref": external_ref})
        assert resp.status_code == 200
        body = resp.json()
        assert body["external_refs"] == [external_ref]
        assert "id" in body

    def test_resolve_is_idempotent(self, client: TestClient, external_ref: dict[str, str]) -> None:
        r1 = client.post("/api/kb/v1/identity/resolve", json={"external_ref": external_ref})
        r2 = client.post("/api/kb/v1/identity/resolve", json={"external_ref": external_ref})
        assert r1.json()["id"] == r2.json()["id"]


class TestGroupSnapshot:
    def test_ingest_group_snapshot(
        self,
        client: TestClient,
        space_id: str,
        group_snapshot: dict[str, Any],
    ) -> None:
        resp = client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["space_id"] == space_id
        assert body["groups_ingested"] == 3
        assert body["epoch"] == 1

    def test_ingest_bumps_epoch(
        self,
        client: TestClient,
        space_id: str,
        group_snapshot: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        resp = client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        assert resp.json()["epoch"] == 2


class TestPolicyActivation:
    def test_activate_policy_bundle(
        self,
        client: TestClient,
        space_id: str,
        policy_bundle: dict[str, Any],
    ) -> None:
        resp = client.post("/api/kb/v1/policies/activate", json=policy_bundle)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["space_id"] == space_id
        assert body["bundle_id"] == "bundle-1"
        assert body["activation_epoch"] == 1

    def test_activate_requires_revisions(
        self,
        client: TestClient,
        space_id: str,
        policy_bundle: dict[str, Any],
    ) -> None:
        bad = {k: v for k, v in policy_bundle.items() if k not in ("access_policy_revision",)}
        resp = client.post("/api/kb/v1/policies/activate", json=bad)
        assert resp.status_code == 422


class TestAuthzContext:
    def test_compute_context(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
        group_snapshot: dict[str, Any],
        policy_bundle: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        client.post("/api/kb/v1/policies/activate", json=policy_bundle)

        resp = client.post(
            "/api/kb/v1/authz/context",
            json={"space_id": space_id, "actor_id": identity_id, "actor_type": "human"},
        )
        assert resp.status_code == 200, resp.text
        ctx = resp.json()
        assert ctx["schema_version"] == "authz-context-v2"
        assert ctx["issuer"] == "corp-ai-db-identity"
        assert ctx["actor_type"] == "human"
        assert len(ctx["space_scopes"]) == 1

        scope = ctx["space_scopes"][0]
        assert scope["space_id"] == space_id
        assert set(scope["capabilities"]) == {
            "read",
            "search",
            "propose",
            "review",
            "merge",
        }
        assert scope["policy_bundle_id"] == "bundle-1"
        assert scope["group_snapshot"]["membership_sha256"]
        assert scope["revocation_epoch"] == 2

    def test_agent_capability_guard(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
        group_snapshot: dict[str, Any],
        policy_bundle: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        client.post("/api/kb/v1/policies/activate", json=policy_bundle)

        resp = client.post(
            "/api/kb/v1/authz/context",
            json={"space_id": space_id, "actor_id": identity_id, "actor_type": "agent"},
        )
        capabilities = resp.json()["space_scopes"][0]["capabilities"]
        assert set(capabilities) <= {"read", "search", "propose", "source_read"}
        assert "merge" not in capabilities
        assert "review" not in capabilities

    def test_context_missing_policy(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
        group_snapshot: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        resp = client.post(
            "/api/kb/v1/authz/context",
            json={"space_id": space_id, "actor_id": identity_id},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "POLICY_REVISION_MISMATCH"


class TestPathApproval:
    def test_longest_prefix_approval(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
        group_snapshot: dict[str, Any],
        policy_bundle: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        client.post("/api/kb/v1/policies/activate", json=policy_bundle)

        resp = client.post(
            "/api/kb/v1/authz/check",
            json={"space_id": space_id, "actor_id": identity_id, "path": "/docs/pricing/page.md"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["approved"] is True
        assert body["matched_prefix"] == "/docs/pricing"

    def test_no_match_denies(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
        group_snapshot: dict[str, Any],
        policy_bundle: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        client.post("/api/kb/v1/policies/activate", json=policy_bundle)

        resp = client.post(
            "/api/kb/v1/authz/check",
            json={"space_id": space_id, "actor_id": identity_id, "path": "/unrelated"},
        )
        assert resp.json()["approved"] is False

    def test_path_traversal_rejected(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/authz/check",
            json={"space_id": space_id, "actor_id": identity_id, "path": "/etc/../secret"},
        )
        assert resp.status_code == 422


class TestServiceLayer:
    def test_nested_group_resolution(
        self,
        db_session: Session,
        space_id: str,
        external_ref: dict[str, str],
    ) -> None:
        identity_service.resolve_identity(db_session, external_ref)
        snapshot = {
            "space_id": space_id,
            "groups": [
                {"group_name": "g1", "member_refs": [external_ref], "parent_groups": []},
                {"group_name": "g2", "member_refs": [], "parent_groups": ["g1"]},
                {"group_name": "g3", "member_refs": [], "parent_groups": ["g2"]},
            ],
        }
        identity_service.ingest_group_snapshot(db_session, space_id, snapshot)
        snapshots = [
            s for s in identity_service._active_group_snapshots(db_session, space_id)
        ]
        groups = identity_service._resolve_groups_for_actor(snapshots, external_ref)
        assert groups == {"g1", "g2", "g3"}

    def test_revocation_epoch_after_activation(
        self,
        db_session: Session,
        space_id: str,
        external_ref: dict[str, str],
        policy_bundle: dict[str, Any],
    ) -> None:
        identity_service.resolve_identity(db_session, external_ref)
        identity_service.activate_policy_bundle(db_session, space_id, policy_bundle)
        assert identity_service._latest_revocation_epoch(db_session, space_id) == 1


class TestContractShape:
    def test_authz_context_matches_contract_keys(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
        group_snapshot: dict[str, Any],
        policy_bundle: dict[str, Any],
    ) -> None:
        client.post("/api/kb/v1/groups/snapshot", json=group_snapshot)
        client.post("/api/kb/v1/policies/activate", json=policy_bundle)

        resp = client.post(
            "/api/kb/v1/authz/context",
            json={"space_id": space_id, "actor_id": identity_id, "actor_type": "human"},
        )
        ctx = resp.json()
        required = {
            "schema_version",
            "context_id",
            "issuer",
            "stable_id",
            "actor_type",
            "space_scopes",
            "path_scopes",
            "evaluated_at",
            "expires_at",
            "revocation_epoch",
        }
        assert required.issubset(ctx.keys())
        scope = ctx["space_scopes"][0]
        assert {
            "space_id",
            "repository_id",
            "capabilities",
            "policy_bundle_id",
            "access_policy_revision",
            "approval_policy_revision",
            "group_snapshot",
            "revocation_epoch",
        }.issubset(scope.keys())


class TestSnapshotAndPolicySupersede:
    def test_prior_group_snapshots_get_valid_until(
        self,
        db_session: Session,
        space_id: str,
        external_ref: dict[str, str],
        group_snapshot: dict[str, Any],
    ) -> None:
        identity_service.resolve_identity(db_session, external_ref)
        identity_service.ingest_group_snapshot(db_session, space_id, group_snapshot)
        identity_service.ingest_group_snapshot(db_session, space_id, group_snapshot)

        prior = (
            db_session.query(GroupSnapshot)
            .filter(GroupSnapshot.space_id == space_id, GroupSnapshot.epoch == 1)
            .all()
        )
        assert len(prior) == 3
        assert all(row.valid_until is not None for row in prior)

    def test_prior_policy_bundles_get_valid_until(
        self,
        db_session: Session,
        space_id: str,
        external_ref: dict[str, str],
        policy_bundle: dict[str, Any],
    ) -> None:
        identity_service.resolve_identity(db_session, external_ref)
        identity_service.activate_policy_bundle(db_session, space_id, policy_bundle)
        identity_service.activate_policy_bundle(db_session, space_id, policy_bundle)

        prior = (
            db_session.query(PolicyBundle)
            .filter(
                PolicyBundle.space_id == space_id,
                PolicyBundle.activation_epoch == 1,
            )
            .all()
        )
        assert len(prior) == 1
        assert prior[0].valid_until is not None


class TestEpochOrdering:
    def test_snapshot_epoch_after_policy_revocation(
        self,
        db_session: Session,
        space_id: str,
        external_ref: dict[str, str],
        group_snapshot: dict[str, Any],
        policy_bundle: dict[str, Any],
    ) -> None:
        identity_service.resolve_identity(db_session, external_ref)
        identity_service.activate_policy_bundle(db_session, space_id, policy_bundle)
        revocation = (
            db_session.query(Revocation)
            .filter(Revocation.space_id == space_id)
            .one()
        )
        rows = identity_service.ingest_group_snapshot(db_session, space_id, group_snapshot)
        assert rows[0].epoch > revocation.revoked_at_epoch


class TestRouteErrorMapping:
    def test_not_found_for_unknown_actor(
        self,
        client: TestClient,
        space_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/authz/context",
            json={"space_id": space_id, "actor_id": str(uuid.uuid4()), "actor_type": "human"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_group_snapshot_stale(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/authz/context",
            json={"space_id": space_id, "actor_id": identity_id, "actor_type": "human"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "GROUP_SNAPSHOT_STALE"

    def test_invalid_snapshot(
        self,
        client: TestClient,
        space_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/groups/snapshot",
            json={"space_id": space_id, "groups": []},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_SNAPSHOT"

    def test_invalid_path_returns_422(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/authz/check",
            json={"space_id": space_id, "actor_id": identity_id, "path": "/etc/../secret"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_PATH"

    def test_invalid_actor_type_returns_422(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/authz/context",
            json={"space_id": space_id, "actor_id": identity_id, "actor_type": "robot"},
        )
        assert resp.status_code == 422


class TestPathApprovalDeniedResponses:
    def test_unknown_actor_denied(
        self,
        client: TestClient,
        space_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/authz/check",
            json={"space_id": space_id, "actor_id": str(uuid.uuid4()), "path": "/docs"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["approved"] is False
        assert "actor identity not found" in body["reason"]

    def test_no_active_policy_denied(
        self,
        client: TestClient,
        space_id: str,
        identity_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/authz/check",
            json={"space_id": space_id, "actor_id": identity_id, "path": "/docs"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["approved"] is False
        assert "no active policy bundle" in body["reason"]


class TestRefMatching:
    def test_empty_actor_ref_is_no_match(
        self,
        db_session: Session,
        space_id: str,
    ) -> None:
        ref = {"issuer": "test", "sub": "bob"}
        identity_service.resolve_identity(db_session, ref)
        snapshot = {
            "space_id": space_id,
            "groups": [
                {"group_name": "g1", "member_refs": [ref], "parent_groups": []},
            ],
        }
        identity_service.ingest_group_snapshot(db_session, space_id, snapshot)
        snapshots = identity_service._active_group_snapshots(db_session, space_id)
        groups = identity_service._resolve_groups_for_actor(snapshots, {})
        assert groups == set()
