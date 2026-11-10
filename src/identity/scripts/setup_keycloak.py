"""Bootstrap a local Keycloak realm and client for identity-service testing.

This script is idempotent: it creates the ``corp-kb`` realm and
``identity-service`` client only if they do not already exist, then adds the
audience mapper required for token introspection and the groups mapper required
for group membership claims with direct-access grants.

The script prints the generated client secret so it can be copied into ``.env``.
It does not write secrets to any file.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

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
    mapper_name = f"{client_id}-audience"
    mappers_url = f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/protocol-mappers/models"
    if _mapper_exists(keycloak_url, token, realm, client_uuid, mapper_name):
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


def _create_test_user(
    keycloak_url: str,
    token: str,
    realm: str,
    username: str,
    password: str,
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
        print(f"Test user '{username}' already exists")
        return _get_user_id(keycloak_url, token, realm, username)

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
) -> None:
    resp = httpx.put(
        f"{keycloak_url}/admin/realms/{realm}/users/{user_id}/groups/{group_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if resp.status_code == 204:
        print("Added test user to 'sales' group")
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
    if resp.status_code == 200:
        return resp.json().get("value")
    return None


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
    _add_groups_mapper(keycloak_url, token, realm, client_uuid)
    user_id = _create_test_user(keycloak_url, token, realm, test_username, test_password)
    sales_group_id = _create_group(keycloak_url, token, realm, "sales")
    if user_id and sales_group_id:
        _add_user_to_group(keycloak_url, token, realm, user_id, sales_group_id)

    secret = _get_client_secret(keycloak_url, token, realm, client_uuid)
    if secret:
        print("\n# Client secret (copy to .env as KEYCLOAK_CLIENT_SECRET):")
        print(secret)
    else:
        print("\n# No client secret returned; Keycloak may require re-reading the client.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
