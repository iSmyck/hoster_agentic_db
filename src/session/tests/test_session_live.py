"""Live integration tests for the Session service HTTP API."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def stable_id() -> str:
    return "test:alice"


class TestCreateAndValidate:
    def test_create_with_external_ref(self, client: TestClient) -> None:
        resp = client.post(
            "/api/kb/v1/session/create",
            json={"external_ref": {"issuer": "test", "sub": "bob"}},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["stable_id"] == "test:bob"
        assert body["access_token"]
        assert body["refresh_token"]

    def test_create_with_stable_id(self, client: TestClient) -> None:
        resp = client.post(
            "/api/kb/v1/session/create",
            json={"stable_id": "test:carol"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["stable_id"] == "test:carol"

    def test_validate_returns_revisions(self, client: TestClient) -> None:
        create = client.post(
            "/api/kb/v1/session/create",
            json={
                "stable_id": "test:alice",
                "access_policy_revision": "a" * 40,
                "approval_policy_revision": "b" * 40,
            },
        )
        access_token = create.json()["access_token"]

        validate = client.get(
            "/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert validate.status_code == 200, validate.text
        body = validate.json()
        assert body["stable_id"] == "test:alice"
        assert body["access_policy_revision"] == "a" * 40
        assert body["approval_policy_revision"] == "b" * 40

    def test_missing_bearer_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/kb/v1/session/validate")
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_empty_bearer_rejected(self, client: TestClient) -> None:
        resp = client.get(
            "/api/kb/v1/session/validate",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_non_bearer_scheme_rejected(self, client: TestClient) -> None:
        resp = client.get(
            "/api/kb/v1/session/validate",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_create_missing_identity_returns_401(self, client: TestClient) -> None:
        resp = client.post("/api/kb/v1/session/create", json={})
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "INVALID_REF"

    def test_create_invalid_external_ref_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/kb/v1/session/create",
            json={"external_ref": {"sub": "only-sub"}},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "INVALID_REF"


class TestRefreshAndRevoke:
    def test_refresh_rotates_access_token(self, client: TestClient) -> None:
        create = client.post(
            "/api/kb/v1/session/create",
            json={"stable_id": "test:alice"},
        )
        body = create.json()
        time.sleep(0.01)

        refresh = client.post(
            "/api/kb/v1/session/refresh",
            json={"refresh_token": body["refresh_token"]},
        )
        assert refresh.status_code == 200, refresh.text
        new_access = refresh.json()["access_token"]
        assert new_access != body["access_token"]

        old_invalid = client.get(
            "/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert old_invalid.status_code == 401

        new_valid = client.get(
            "/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert new_valid.status_code == 200

    def test_logout_revokes_token(self, client: TestClient) -> None:
        create = client.post(
            "/api/kb/v1/session/create",
            json={"stable_id": "test:alice"},
        )
        access_token = create.json()["access_token"]

        logout = client.post(
            "/api/kb/v1/session/logout",
            json={"access_token": access_token},
        )
        assert logout.status_code == 204

        validate = client.get(
            "/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert validate.status_code == 401

    def test_logout_with_refresh_token_rejected(self, client: TestClient) -> None:
        create = client.post(
            "/api/kb/v1/session/create",
            json={"stable_id": "test:alice"},
        )
        refresh_token = create.json()["refresh_token"]

        logout = client.post(
            "/api/kb/v1/session/logout",
            json={"access_token": refresh_token},
        )
        assert logout.status_code == 401
        assert logout.json()["detail"]["code"] == "TOKEN_INVALID"

    def test_revoke_all_for_user(self, client: TestClient) -> None:
        c1 = client.post("/api/kb/v1/session/create", json={"stable_id": "test:alice"})
        c2 = client.post("/api/kb/v1/session/create", json={"stable_id": "test:alice"})
        c3 = client.post("/api/kb/v1/session/create", json={"stable_id": "test:bob"})

        revoke = client.post(
            "/api/kb/v1/session/revoke-all",
            json={"stable_id": "test:alice"},
        )
        assert revoke.status_code == 200
        assert revoke.json()["revoked_count"] == 2

        for token in (c1.json()["access_token"], c2.json()["access_token"]):
            resp = client.get(
                "/api/kb/v1/session/validate",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 401

        bob_valid = client.get(
            "/api/kb/v1/session/validate",
            headers={"Authorization": f"Bearer {c3.json()['access_token']}"},
        )
        assert bob_valid.status_code == 200

    def test_revoke_all_global(self, client: TestClient) -> None:
        c1 = client.post("/api/kb/v1/session/create", json={"stable_id": "test:alice"})
        c2 = client.post("/api/kb/v1/session/create", json={"stable_id": "test:bob"})

        revoke = client.post("/api/kb/v1/session/revoke-all/global")
        assert revoke.status_code == 200
        assert revoke.json()["revoked_count"] == 2

        for token in (c1.json()["access_token"], c2.json()["access_token"]):
            resp = client.get(
                "/api/kb/v1/session/validate",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 401
