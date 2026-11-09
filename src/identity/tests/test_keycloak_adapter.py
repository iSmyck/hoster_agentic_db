"""Tests for the Keycloak identity adapter.

All network calls are mocked so these tests run without a running Keycloak
server and never exercise real credentials.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from identity.app.adapters.keycloak import IdentityAdapterError, KeycloakIdentityAdapter
from identity.app.services import identity_service


@pytest.fixture
def adapter() -> KeycloakIdentityAdapter:
    return KeycloakIdentityAdapter(
        keycloak_url="http://localhost:8082",
        realm="corp-kb",
        client_id="identity-service",
        client_secret="dummy-secret",
    )


def _mock_httpx_client(
    post_response: dict[str, Any] | Exception | None = None,
    get_response: dict[str, Any] | Exception | None = None,
) -> Mock:
    """Return a mock httpx.Client class configured for the adapter tests."""
    mock_client = Mock()

    if isinstance(post_response, Exception):
        mock_client.post.side_effect = post_response
    elif post_response is not None:
        post_resp = Mock()
        post_resp.json.return_value = post_response
        post_resp.raise_for_status.return_value = None
        mock_client.post.return_value = post_resp

    if isinstance(get_response, Exception):
        mock_client.get.side_effect = get_response
    elif get_response is not None:
        get_resp = Mock()
        get_resp.json.return_value = get_response
        get_resp.raise_for_status.return_value = None
        mock_client.get.return_value = get_resp

    mock_client_cls = Mock()
    mock_client_cls.return_value.__enter__ = Mock(return_value=mock_client)
    mock_client_cls.return_value.__exit__ = Mock(return_value=False)
    return mock_client_cls


class TestKeycloakAdapter:
    def test_resolve_external_refs_success(self, adapter: KeycloakIdentityAdapter) -> None:
        introspection = {
            "active": True,
            "sub": "a1b2c3",
            "email": "test@example.com",
            "preferred_username": "testuser",
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
        }

        with patch(
            "identity.app.adapters.keycloak.httpx.Client",
            _mock_httpx_client(introspection),
        ):
            refs = adapter.resolve_external_refs("dummy-token")

        assert refs["issuer"] == "http://localhost:8082/realms/corp-kb"
        assert refs["sub"] == "a1b2c3"
        assert refs["email"] == "test@example.com"
        assert refs["preferred_username"] == "testuser"
        assert refs["name"] == "Test User"
        assert refs["given_name"] == "Test"
        assert refs["family_name"] == "User"

    def test_inactive_token_raises(self, adapter: KeycloakIdentityAdapter) -> None:
        introspection = {"active": False}

        with patch(
            "identity.app.adapters.keycloak.httpx.Client",
            _mock_httpx_client(introspection),
        ), pytest.raises(IdentityAdapterError) as exc_info:
            adapter.resolve_external_refs("expired-token")

        assert exc_info.value.code == "TOKEN_INVALID"

    def test_introspection_http_error(self, adapter: KeycloakIdentityAdapter) -> None:
        import httpx

        error_response = Mock()
        error_response.status_code = 401
        exc = httpx.HTTPStatusError(
            "Unauthorized",
            request=Mock(),
            response=error_response,
        )

        with patch(
            "identity.app.adapters.keycloak.httpx.Client",
            _mock_httpx_client(post_response=exc),
        ), pytest.raises(IdentityAdapterError) as exc_info:
            adapter.introspect_token("dummy-token")

        assert exc_info.value.code == "INTROSPECTION_HTTP_ERROR"

    def test_resolve_external_refs_uses_introspection_only(self, adapter: KeycloakIdentityAdapter) -> None:
        introspection = {
            "active": True,
            "sub": "a1b2c3",
            "email": "test@example.com",
            "name": "Test User",
        }

        with patch(
            "identity.app.adapters.keycloak.httpx.Client",
            _mock_httpx_client(introspection),
        ) as mock_client_cls:
            refs = adapter.resolve_external_refs("dummy-token")

        assert refs["sub"] == "a1b2c3"
        assert mock_client_cls.return_value.__enter__.return_value.get.call_count == 0


class TestResolveIdentityFromToken:
    def test_service_resolves_identity_from_token(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_adapter = Mock(spec=KeycloakIdentityAdapter)
        mock_adapter.resolve_external_refs.return_value = {
            "issuer": "http://localhost:8082/realms/corp-kb",
            "sub": "token-user-1",
            "email": "token@example.com",
        }

        monkeypatch.setattr(
            identity_service,
            "_get_identity_adapter",
            lambda: mock_adapter,
        )

        identity = identity_service.resolve_identity_from_token(db_session, "dummy-token")

        assert identity is not None
        refs = identity.external_refs[0]
        assert refs["issuer"] == "http://localhost:8082/realms/corp-kb"
        assert refs["sub"] == "token-user-1"
        mock_adapter.resolve_external_refs.assert_called_once_with("dummy-token")

    def test_service_maps_adapter_error(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_adapter = Mock(spec=KeycloakIdentityAdapter)
        mock_adapter.resolve_external_refs.side_effect = IdentityAdapterError(
            "TOKEN_INVALID",
            "Access token is not active",
        )

        monkeypatch.setattr(
            identity_service,
            "_get_identity_adapter",
            lambda: mock_adapter,
        )

        with pytest.raises(identity_service.IdentityServiceError) as exc_info:
            identity_service.resolve_identity_from_token(db_session, "bad-token")

        assert exc_info.value.code == "IDENTITY_ADAPTER_ERROR:TOKEN_INVALID"


class TestResolveTokenEndpoint:
    def test_resolve_token_endpoint_success(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_adapter = Mock(spec=KeycloakIdentityAdapter)
        mock_adapter.resolve_external_refs.return_value = {
            "issuer": "http://localhost:8082/realms/corp-kb",
            "sub": "endpoint-user-1",
            "email": "endpoint@example.com",
        }

        monkeypatch.setattr(
            identity_service,
            "_get_identity_adapter",
            lambda: mock_adapter,
        )

        resp = client.post(
            "/api/kb/v1/identity/resolve-token",
            json={"access_token": "dummy-token"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["external_refs"][0]["sub"] == "endpoint-user-1"
        assert body["external_refs"][0]["email"] == "endpoint@example.com"

    def test_resolve_token_endpoint_invalid_token(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_adapter = Mock(spec=KeycloakIdentityAdapter)
        mock_adapter.resolve_external_refs.side_effect = IdentityAdapterError(
            "TOKEN_INVALID",
            "Access token is not active",
        )

        monkeypatch.setattr(
            identity_service,
            "_get_identity_adapter",
            lambda: mock_adapter,
        )

        resp = client.post(
            "/api/kb/v1/identity/resolve-token",
            json={"access_token": "expired-token"},
        )
        assert resp.status_code == 401, resp.text
        assert resp.json()["detail"]["code"] == "IDENTITY_ADAPTER_ERROR:TOKEN_INVALID"
