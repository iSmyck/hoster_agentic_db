"""Live integration tests against a real Keycloak sandbox.

These tests are skipped unless:
  - IDENTITY_ADAPTER is set to ``keycloak``
  - KEYCLOAK_CLIENT_SECRET is present
  - the configured Keycloak instance is reachable

They exercise the real token endpoint, adapter introspection, group fetch,
identity resolution, and revocation recheck paths.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
import pytest
from dotenv import load_dotenv
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv(".env")

from identity.app.adapters.keycloak import (
    IdentityAdapterError,
    KeycloakIdentityAdapter,
)
from identity.app.core.config import settings
from identity.app.models.authz import Base, GroupSnapshot, Identity, Revocation
from identity.app.services import identity_service

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("IDENTITY_ADAPTER", "stub") != "keycloak",
        reason="Live Keycloak tests require IDENTITY_ADAPTER=keycloak",
    ),
    pytest.mark.skipif(
        not os.environ.get("KEYCLOAK_CLIENT_SECRET", "").strip(),
        reason="Live Keycloak tests require KEYCLOAK_CLIENT_SECRET",
    ),
]


@pytest.fixture(scope="module")
def keycloak_urls() -> dict[str, str]:
    return {
        "url": settings.KEYCLOAK_URL,
        "realm": settings.KEYCLOAK_REALM,
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
        "username": os.environ.get("KEYCLOAK_TEST_USERNAME", "testuser"),
        "password": os.environ.get("KEYCLOAK_TEST_PASSWORD", "testpass"),
    }


@pytest.fixture(scope="module")
def live_adapter(keycloak_urls: dict[str, str]) -> KeycloakIdentityAdapter:
    return KeycloakIdentityAdapter(
        keycloak_url=keycloak_urls["url"],
        realm=keycloak_urls["realm"],
        client_id=keycloak_urls["client_id"],
        client_secret=keycloak_urls["client_secret"],
    )


@pytest.fixture(scope="module")
def access_token(keycloak_urls: dict[str, str]) -> str:
    try:
        resp = httpx.post(
            f"{keycloak_urls['url']}/realms/{keycloak_urls['realm']}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": keycloak_urls["client_id"],
                "client_secret": keycloak_urls["client_secret"],
                "username": keycloak_urls["username"],
                "password": keycloak_urls["password"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
        resp.raise_for_status()
    except httpx.RequestError as exc:
        pytest.skip(f"Keycloak not reachable: {exc}")
    token = resp.json().get("access_token")
    if not token:
        pytest.skip("Keycloak token response did not contain access_token")
    return token


@pytest.fixture
def live_db() -> Any:
    """Yield a committed session against the configured database."""
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    # Clean identity/authz tables so live tests are deterministic.
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_introspection_returns_active_token_with_groups(
    live_adapter: KeycloakIdentityAdapter,
    access_token: str,
) -> None:
    introspection = live_adapter.introspect_token(access_token)
    assert introspection.get("active") is True
    assert "sub" in introspection
    assert introspection.get("preferred_username") == "testuser"
    assert "sales" in introspection.get("groups", [])


def test_resolve_external_refs_normalizes_identity(
    live_adapter: KeycloakIdentityAdapter,
    access_token: str,
) -> None:
    refs = live_adapter.resolve_external_refs(access_token)
    assert refs["issuer"] == f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    assert refs["sub"]
    assert refs["preferred_username"] == "testuser"
    assert refs["email"].endswith("@example.com")


def test_fetch_groups_returns_sales(
    live_adapter: KeycloakIdentityAdapter,
    access_token: str,
) -> None:
    groups = live_adapter.fetch_groups(access_token)
    assert "sales" in groups


def test_resolve_identity_from_token_persists_in_kb_authz(
    live_db: Session,
    access_token: str,
) -> None:
    identity = identity_service.resolve_identity_from_token(live_db, access_token)
    assert isinstance(identity, Identity)
    assert identity.external_refs
    refs = identity.external_refs[0]
    assert refs["issuer"] == f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    assert refs["sub"]

    # Idempotent resolve returns the same stable identity.
    second = identity_service.resolve_identity_from_token(live_db, access_token)
    assert second.id == identity.id


def test_recheck_group_membership_advances_epoch_on_removal(
    live_db: Session,
    access_token: str,
    keycloak_urls: dict[str, str],
) -> None:
    space_id = f"live-space-{uuid.uuid4().hex[:8]}"

    # Seed an initial membership snapshot via recheck (user is in 'sales').
    result = identity_service.recheck_group_membership(live_db, space_id, access_token)
    assert result["space_id"] == space_id
    assert "sales" in result["groups"]
    first_epoch = result["epoch"]

    active = (
        live_db.query(GroupSnapshot)
        .filter(GroupSnapshot.space_id == space_id, GroupSnapshot.valid_until.is_(None))
        .all()
    )
    assert any(s.group_name == "sales" for s in active)

    # Remove the user from the 'sales' group using the admin API.
    _remove_user_from_group(keycloak_urls)

    try:
        result = identity_service.recheck_group_membership(live_db, space_id, access_token)
        assert result["epoch"] > first_epoch
        assert result["groups"] == []

        active = (
            live_db.query(GroupSnapshot)
            .filter(GroupSnapshot.space_id == space_id, GroupSnapshot.valid_until.is_(None))
            .all()
        )
        assert active == []

        revocation = (
            live_db.query(Revocation)
            .filter(Revocation.space_id == space_id)
            .order_by(Revocation.revoked_at_epoch.desc())
            .first()
        )
        assert revocation is not None
        assert revocation.revoked_at_epoch == result["epoch"]
    finally:
        # Restore membership so subsequent test runs remain deterministic.
        _add_user_to_group(keycloak_urls)


def _admin_token(keycloak_urls: dict[str, str]) -> str:
    resp = httpx.post(
        f"{keycloak_urls['url']}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "username": os.environ.get("KEYCLOAK_ADMIN_USER", "admin"),
            "password": os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin"),
            "client_id": "admin-cli",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _user_and_group_ids(keycloak_urls: dict[str, str]) -> tuple[str | None, str | None]:
    token = _admin_token(keycloak_urls)
    users_resp = httpx.get(
        f"{keycloak_urls['url']}/admin/realms/{keycloak_urls['realm']}/users",
        headers={"Authorization": f"Bearer {token}"},
        params={"username": keycloak_urls["username"], "exact": "true"},
        timeout=30.0,
    )
    users_resp.raise_for_status()
    users = users_resp.json()
    groups_resp = httpx.get(
        f"{keycloak_urls['url']}/admin/realms/{keycloak_urls['realm']}/groups",
        headers={"Authorization": f"Bearer {token}"},
        params={"search": "sales", "exact": "true"},
        timeout=30.0,
    )
    groups_resp.raise_for_status()
    groups = groups_resp.json()
    user_id = users[0]["id"] if users else None
    group_id = groups[0]["id"] if groups else None
    return user_id, group_id


def _remove_user_from_group(keycloak_urls: dict[str, str]) -> None:
    token = _admin_token(keycloak_urls)
    user_id, group_id = _user_and_group_ids(keycloak_urls)
    if not (user_id and group_id):
        pytest.fail("Could not locate test user or sales group")
    resp = httpx.delete(
        f"{keycloak_urls['url']}/admin/realms/{keycloak_urls['realm']}/users/{user_id}/groups/{group_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()


def _add_user_to_group(keycloak_urls: dict[str, str]) -> None:
    token = _admin_token(keycloak_urls)
    user_id, group_id = _user_and_group_ids(keycloak_urls)
    if not (user_id and group_id):
        return
    resp = httpx.put(
        f"{keycloak_urls['url']}/admin/realms/{keycloak_urls['realm']}/users/{user_id}/groups/{group_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()


def test_invalid_token_raises_adapter_error(live_adapter: KeycloakIdentityAdapter) -> None:
    with pytest.raises(IdentityAdapterError):
        live_adapter.resolve_external_refs("not-a-real-token")
