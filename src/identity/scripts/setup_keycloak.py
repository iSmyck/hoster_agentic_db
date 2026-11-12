"""Bootstrap a local Keycloak realm and clients for corp-ai-db services.

This script is idempotent: it creates the ``corp-kb`` realm, the
``identity-service`` confidential client (used by the identity adapter) and the
``openwebui`` confidential client (used by Open WebUI OIDC) only if they do not
already exist. It seeds the audience mapper required for token introspection,
the groups mapper required for group membership claims, and the G1 test users
and groups.

The script persists generated client secrets to the workspace ``.env`` file
(via ``_update_env_file``) so that ``scripts/local_stack.py`` and the
acceptance harness can read them. It does not write secrets anywhere else.
"""

from __future__ import annotations

import os
import secrets
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_KEYCLOAK_URL = "http://localhost:8082"
DEFAULT_REALM = "corp-kb"
DEFAULT_IDENTITY_CLIENT_ID = "identity-service"
DEFAULT_OPENWEBUI_CLIENT_ID = "openwebui"

G1_GROUPS = ["sales", "kb-approvers"]


def _g1_user_password(username: str) -> str:
    """Return the sandbox password for a G1 test user from env, or fail closed."""
    env_var = f"KEYCLOAK_G1_{username.upper().replace('-', '_')}_PASSWORD"
    password = os.environ.get(env_var)
    if not password:
        raise RuntimeError(f"Set {env_var} for the local sandbox test user")
    return password


def _g1_users() -> dict[str, dict[str, Any]]:
    return {
        "g1-author": {
            "password": _g1_user_password("g1-author"),
            "email": "g1-author@hoster.test",
            "first_name": "G1",
            "last_name": "Author",
            "groups": ["sales"],
        },
        "g1-approver": {
            "password": _g1_user_password("g1-approver"),
            "email": "g1-approver@hoster.test",
            "first_name": "G1",
            "last_name": "Approver",
            "groups": ["sales", "kb-approvers"],
        },
    }


def _admin_token(keycloak_url: str, admin_user: str, admin_password: str) -> str:
    resp = httpx.post(
        f"{keycloak_url}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "username": admin_user,
            "password": admin_password,
            "client_id": "admin-cli",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _realm_exists(keycloak_url: str, token: str, realm: str) -> bool:
    resp = httpx.get(
        f"{keycloak_url}/admin/realms/{realm}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    return resp.status_code == 200


def _create_realm(keycloak_url: str, token: str, realm: str) -> None:
    resp = httpx.post(
        f"{keycloak_url}/admin/realms",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"realm": realm, "enabled": True},
        timeout=30.0,
    )
    if resp.status_code == 201:
        print(f"Created realm '{realm}'")
    elif resp.status_code == 409:
        print(f"Realm '{realm}' already exists")
    else:
        resp.raise_for_status()


def _get_client(keycloak_url: str, token: str, realm: str, client_id: str) -> dict | None:
    resp = httpx.get(
        f"{keycloak_url}/admin/realms/{realm}/clients",
        headers={"Authorization": f"Bearer {token}"},
        params={"clientId": client_id},
        timeout=30.0,
    )
    resp.raise_for_status()
    clients = resp.json()
    return clients[0] if clients else None


def _create_client(
    keycloak_url: str,
    token: str,
    realm: str,
    client_id: str,
    redirect_uris: list[str] | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "clientId": client_id,
        "name": client_id.replace("-", " ").title(),
        "enabled": True,
        "publicClient": False,
        "serviceAccountsEnabled": True,
        "directAccessGrantsEnabled": True,
        "standardFlowEnabled": True,
        "redirectUris": redirect_uris or ["http://localhost:*"],
    }
    resp = httpx.post(
        f"{keycloak_url}/admin/realms/{realm}/clients",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=30.0,
    )
    if resp.status_code == 409:
        print(f"Client '{client_id}' already exists")
        return _get_client(keycloak_url, token, realm, client_id) or {}
    resp.raise_for_status()
    print(f"Created client '{client_id}'")
    return _get_client(keycloak_url, token, realm, client_id) or {}


def _mapper_exists(
    keycloak_url: str,
    token: str,
    realm: str,
    client_uuid: str,
    mapper_name: str,
) -> bool:
    mappers_url = f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/protocol-mappers/models"
    resp = httpx.get(
        mappers_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return any(m.get("name") == mapper_name for m in resp.json())


def _add_audience_mapper(
    keycloak_url: str,
    token: str,
    realm: str,
    client_uuid: str,
    client_id: str,
) -> None:
    # The client itself needs to be in the audience for Open WebUI's OAuth
    # session handling; the identity-service client needs to be in the audience
    # so the identity adapter can introspect tokens issued to any client.
    for audience in {client_id, "identity-service"}:
        mapper_name = f"{client_id}-audience-{audience}"
        mappers_url = f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/protocol-mappers/models"
        if _mapper_exists(keycloak_url, token, realm, client_uuid, mapper_name):
            print(f"Audience mapper '{mapper_name}' already exists")
            continue

        resp = httpx.post(
            mappers_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "name": mapper_name,
                "protocol": "openid-connect",
                "protocolMapper": "oidc-audience-mapper",
                "consentRequired": False,
                "config": {
                    "included.client.audience": audience,
                    "id.token.claim": "false",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "false",
                },
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        print(f"Added audience mapper '{mapper_name}'")


def _add_groups_mapper(
    keycloak_url: str,
    token: str,
    realm: str,
    client_uuid: str,
) -> None:
    mapper_name = "groups"
    mappers_url = f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/protocol-mappers/models"
    if _mapper_exists(keycloak_url, token, realm, client_uuid, mapper_name):
        print(f"Groups mapper '{mapper_name}' already exists")
        return

    resp = httpx.post(
        mappers_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "name": mapper_name,
            "protocol": "openid-connect",
            "protocolMapper": "oidc-group-membership-mapper",
            "consentRequired": False,
            "config": {
                "claim.name": "groups",
                "full.path": "false",
                "id.token.claim": "false",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    print(f"Added groups mapper '{mapper_name}'")


def _get_user_id(keycloak_url: str, token: str, realm: str, username: str) -> str | None:
    resp = httpx.get(
        f"{keycloak_url}/admin/realms/{realm}/users",
        headers={"Authorization": f"Bearer {token}"},
        params={"username": username, "exact": "true"},
        timeout=30.0,
    )
    resp.raise_for_status()
    users = resp.json()
    return users[0]["id"] if users else None


def _create_user(
    keycloak_url: str,
    token: str,
    realm: str,
    username: str,
    spec: dict[str, Any],
) -> str | None:
    users_url = f"{keycloak_url}/admin/realms/{realm}/users"
    resp = httpx.get(
        users_url,
        headers={"Authorization": f"Bearer {token}"},
        params={"username": username, "exact": "true"},
        timeout=30.0,
    )
    resp.raise_for_status()
    if resp.json():
        print(f"User '{username}' already exists")
        return _get_user_id(keycloak_url, token, realm, username)

    resp = httpx.post(
        users_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "username": username,
            "enabled": True,
            "email": spec["email"],
            "firstName": spec["first_name"],
            "lastName": spec["last_name"],
            "credentials": [
                {"type": "password", "value": spec["password"], "temporary": False},
            ],
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    print(f"Created user '{username}'")
    return _get_user_id(keycloak_url, token, realm, username)


def _create_group(
    keycloak_url: str,
    token: str,
    realm: str,
    group_name: str,
) -> str | None:
    groups_url = f"{keycloak_url}/admin/realms/{realm}/groups"
    resp = httpx.get(
        groups_url,
        headers={"Authorization": f"Bearer {token}"},
        params={"search": group_name, "exact": "true"},
        timeout=30.0,
    )
    resp.raise_for_status()
    groups = resp.json()
    if groups:
        print(f"Group '{group_name}' already exists")
        return groups[0]["id"]

    resp = httpx.post(
        groups_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"name": group_name},
        timeout=30.0,
    )
    resp.raise_for_status()
    print(f"Created group '{group_name}'")

    resp = httpx.get(
        groups_url,
        headers={"Authorization": f"Bearer {token}"},
        params={"search": group_name, "exact": "true"},
        timeout=30.0,
    )
    resp.raise_for_status()
    groups = resp.json()
    return groups[0]["id"] if groups else None


def _add_user_to_group(
    keycloak_url: str,
    token: str,
    realm: str,
    user_id: str,
    group_id: str,
    username: str,
    group_name: str,
) -> None:
    resp = httpx.put(
        f"{keycloak_url}/admin/realms/{realm}/users/{user_id}/groups/{group_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if resp.status_code == 204:
        print(f"Added user '{username}' to group '{group_name}'")
    else:
        resp.raise_for_status()


def _get_client_secret(
    keycloak_url: str,
    token: str,
    realm: str,
    client_uuid: str,
) -> str | None:
    resp = httpx.get(
        f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json().get("value")


def _set_client_secret(
    keycloak_url: str,
    token: str,
    realm: str,
    client_uuid: str,
) -> None:
    resp = httpx.post(
        f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()


def _update_env_file(key: str, value: str) -> None:
    """Update a key in the workspace .env file without writing secrets elsewhere."""
    env_path = Path(".env").resolve()
    if not env_path.exists():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ensure_client(
    keycloak_url: str,
    token: str,
    realm: str,
    client_id: str,
    redirect_uris: list[str] | None = None,
    env_secret_key: str | None = None,
) -> tuple[str, str]:
    """Create or update a client and return (client_uuid, client_secret)."""
    client = _create_client(keycloak_url, token, realm, client_id, redirect_uris=redirect_uris)
    client_uuid = client.get("id")
    if not client_uuid:
        raise RuntimeError(f"Failed to obtain client UUID for {client_id}")

    _add_audience_mapper(keycloak_url, token, realm, client_uuid, client_id)
    _add_groups_mapper(keycloak_url, token, realm, client_uuid)

    # Use the secret requested by the environment if it is a real value; otherwise
    # regenerate and persist it back to .env so downstream tools see the same value.
    requested_secret = ""
    if env_secret_key:
        requested_secret = os.environ.get(env_secret_key, "").strip()
    if not requested_secret or requested_secret.startswith("CHANGE_ME"):
        requested_secret = secrets.token_urlsafe(48)
        if env_secret_key:
            _update_env_file(env_secret_key, requested_secret)
            os.environ[env_secret_key] = requested_secret

    _set_client_secret(keycloak_url, token, realm, client_uuid)
    secret = _get_client_secret(keycloak_url, token, realm, client_uuid)
    if not secret:
        raise RuntimeError(f"Failed to obtain client secret for {client_id}")
    if env_secret_key:
        _update_env_file(env_secret_key, secret)
        os.environ[env_secret_key] = secret
    return client_uuid, secret


def _ensure_test_user(
    keycloak_url: str,
    token: str,
    realm: str,
    username: str,
    spec: dict[str, Any],
    group_ids: dict[str, str],
) -> str | None:
    user_id = _create_user(keycloak_url, token, realm, username, spec)
    if not user_id:
        return None
    for group_name in spec.get("groups", []):
        group_id = group_ids.get(group_name)
        if group_id:
            _add_user_to_group(
                keycloak_url, token, realm, user_id, group_id, username, group_name
            )
    return user_id


def setup_keycloak(
    keycloak_url: str | None = None,
    realm: str | None = None,
    admin_user: str | None = None,
    admin_password: str | None = None,
    identity_client_id: str | None = None,
    openwebui_client_id: str | None = None,
    openwebui_redirect_uri: str = "http://localhost:3100/oauth/oidc/callback",
) -> dict[str, Any]:
    """Idempotently configure the corp-kb realm and return client secrets.

    Returns a dict with ``realm``, ``identity_client_secret``,
    ``openwebui_client_secret``, ``users`` (mapping username -> user_id) and
    ``groups``.
    """
    keycloak_url = (keycloak_url or os.environ.get("KEYCLOAK_URL", DEFAULT_KEYCLOAK_URL)).rstrip("/")
    realm = realm or os.environ.get("KEYCLOAK_REALM", DEFAULT_REALM)
    identity_client_id = identity_client_id or os.environ.get(
        "KEYCLOAK_CLIENT_ID", DEFAULT_IDENTITY_CLIENT_ID
    )
    openwebui_client_id = openwebui_client_id or os.environ.get(
        "OAUTH_CLIENT_ID", DEFAULT_OPENWEBUI_CLIENT_ID
    )
    admin_user = admin_user or os.environ.get("KEYCLOAK_ADMIN_USER", "")
    admin_password = admin_password or os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")

    if not admin_user or not admin_password:
        raise RuntimeError("KEYCLOAK_ADMIN_USER and KEYCLOAK_ADMIN_PASSWORD must be set")

    print(f"Keycloak admin: {keycloak_url}")
    token = _admin_token(keycloak_url, admin_user, admin_password)

    if not _realm_exists(keycloak_url, token, realm):
        _create_realm(keycloak_url, token, realm)
    else:
        print(f"Realm '{realm}' already exists")

    _, identity_secret = _ensure_client(
        keycloak_url,
        token,
        realm,
        identity_client_id,
        env_secret_key="KEYCLOAK_CLIENT_SECRET",
    )
    _, openwebui_secret = _ensure_client(
        keycloak_url,
        token,
        realm,
        openwebui_client_id,
        redirect_uris=[openwebui_redirect_uri, "http://127.0.0.1:3100/oauth/oidc/callback"],
        env_secret_key="OAUTH_CLIENT_SECRET",
    )

    group_ids: dict[str, str] = {}
    for group_name in G1_GROUPS:
        group_ids[group_name] = _create_group(keycloak_url, token, realm, group_name)

    users: dict[str, str | None] = {}
    for username, spec in _g1_users().items():
        users[username] = _ensure_test_user(
            keycloak_url, token, realm, username, spec, group_ids
        )

    return {
        "keycloak_url": keycloak_url,
        "realm": realm,
        "identity_client_id": identity_client_id,
        "identity_client_secret": identity_secret,
        "openwebui_client_id": openwebui_client_id,
        "openwebui_client_secret": openwebui_secret,
        "users": users,
        "groups": group_ids,
    }


def main() -> int:
    try:
        result = setup_keycloak()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("\n# Identity-service client secret (copy to .env as KEYCLOAK_CLIENT_SECRET):")
    print(result["identity_client_secret"])
    print("\n# Open WebUI OIDC client secret (copy to .env as OAUTH_CLIENT_SECRET):")
    print(result["openwebui_client_secret"])
    print("\n# Test users seeded:")
    for username, user_id in result["users"].items():
        print(f"  {username}: {user_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
