"""Bootstrap a local Keycloak realm and client for identity-service testing.

This script is idempotent: it creates the ``corp-kb`` realm and
``identity-service`` client only if they do not already exist, then adds the
audience mapper required for token introspection to work with direct-access
grants.

The script prints the generated client secret so it can be copied into ``.env``.
It does not write secrets to any file.
"""

from __future__ import annotations

import os
import sys

import httpx

DEFAULT_KEYCLOAK_URL = "http://localhost:8082"
DEFAULT_REALM = "corp-kb"
DEFAULT_CLIENT_ID = "identity-service"


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


def _create_client(keycloak_url: str, token: str, realm: str, client_id: str) -> dict:
    payload = {
        "clientId": client_id,
        "name": "Identity Service",
        "enabled": True,
        "publicClient": False,
        "serviceAccountsEnabled": True,
        "directAccessGrantsEnabled": True,
        "standardFlowEnabled": True,
        "redirectUris": ["http://localhost:*"],
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


def _add_audience_mapper(
    keycloak_url: str,
    token: str,
    realm: str,
    client_uuid: str,
    client_id: str,
) -> None:
    mapper_name = f"{client_id}-audience"
    mappers_url = f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/protocol-mappers/models"
    resp = httpx.get(
        mappers_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    existing = [m for m in resp.json() if m.get("name") == mapper_name]
    if existing:
        print(f"Audience mapper '{mapper_name}' already exists")
        return

    resp = httpx.post(
        mappers_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "name": mapper_name,
            "protocol": "openid-connect",
            "protocolMapper": "oidc-audience-mapper",
            "consentRequired": False,
            "config": {
                "included.client.audience": client_id,
                "id.token.claim": "false",
                "access.token.claim": "true",
                "userinfo.token.claim": "false",
            },
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    print(f"Added audience mapper '{mapper_name}'")


def _create_test_user(
    keycloak_url: str,
    token: str,
    realm: str,
    username: str,
    password: str,
) -> None:
    users_url = f"{keycloak_url}/admin/realms/{realm}/users"
    resp = httpx.get(
        users_url,
        headers={"Authorization": f"Bearer {token}"},
        params={"username": username, "exact": "true"},
        timeout=30.0,
    )
    resp.raise_for_status()
    if resp.json():
        print(f"Test user '{username}' already exists")
        return

    resp = httpx.post(
        users_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "username": username,
            "enabled": True,
            "email": f"{username}@example.com",
            "firstName": "Test",
            "lastName": "User",
            "credentials": [
                {"type": "password", "value": password, "temporary": False},
            ],
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    print(f"Created test user '{username}'")


def main() -> int:
    keycloak_url = os.environ.get("KEYCLOAK_URL", DEFAULT_KEYCLOAK_URL).rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", DEFAULT_REALM)
    client_id = os.environ.get("KEYCLOAK_CLIENT_ID", DEFAULT_CLIENT_ID)
    admin_user = os.environ.get("KEYCLOAK_ADMIN_USER", "")
    admin_password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")
    test_username = os.environ.get("KEYCLOAK_TEST_USERNAME", "testuser")
    test_password = os.environ.get("KEYCLOAK_TEST_PASSWORD", "testpass")

    if not admin_user or not admin_password:
        print(
            "KEYCLOAK_ADMIN_USER and KEYCLOAK_ADMIN_PASSWORD must be set",
            file=sys.stderr,
        )
        return 1

    print(f"Keycloak admin: {keycloak_url}")
    token = _admin_token(keycloak_url, admin_user, admin_password)

    if not _realm_exists(keycloak_url, token, realm):
        _create_realm(keycloak_url, token, realm)
    else:
        print(f"Realm '{realm}' already exists")

    client = _create_client(keycloak_url, token, realm, client_id)
    client_uuid = client.get("id")
    if not client_uuid:
        print("Failed to obtain client UUID", file=sys.stderr)
        return 1

    _add_audience_mapper(keycloak_url, token, realm, client_uuid, client_id)
    _create_test_user(keycloak_url, token, realm, test_username, test_password)

    secret = client.get("secret")
    if secret:
        print("\n# Client secret created.")
        print("# Retrieve it from the Keycloak admin console or read the client")
        print("# via the admin API; it is not printed here to avoid leaking it.")
    else:
        print("\n# No client secret returned; Keycloak may require re-reading the client.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
