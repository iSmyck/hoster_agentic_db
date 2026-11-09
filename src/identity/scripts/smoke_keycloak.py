"""Smoke test for Keycloak -> identity service token resolution.

Fetches an access token for the configured test user from a local Keycloak
instance and exercises the identity service ``/resolve-token`` endpoint.

No client secrets or access tokens are printed.
"""

from __future__ import annotations

import os
import sys

import httpx

DEFAULT_KEYCLOAK_URL = "http://localhost:8082"
DEFAULT_REALM = "corp-kb"
DEFAULT_CLIENT_ID = "identity-service"
DEFAULT_IDENTITY_SERVICE_URL = "http://localhost:8001"


def _get_token(
    keycloak_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> str:
    token_url = (
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
    )
    response = httpx.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("Keycloak response did not contain an access_token")
    return access_token


def _resolve_identity(identity_service_url: str, access_token: str) -> dict:
    resolve_url = f"{identity_service_url}/api/kb/v1/identity/resolve-token"
    response = httpx.post(
        resolve_url,
        json={"access_token": access_token},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    keycloak_url = os.environ.get("KEYCLOAK_URL", DEFAULT_KEYCLOAK_URL)
    realm = os.environ.get("KEYCLOAK_REALM", DEFAULT_REALM)
    client_id = os.environ.get("KEYCLOAK_CLIENT_ID", DEFAULT_CLIENT_ID)
    client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
    identity_service_url = os.environ.get(
        "IDENTITY_SERVICE_URL",
        DEFAULT_IDENTITY_SERVICE_URL,
    )
    username = os.environ.get("KEYCLOAK_TEST_USERNAME", "testuser")
    password = os.environ.get("KEYCLOAK_TEST_PASSWORD", "testpass")

    if not client_secret:
        print("KEYCLOAK_CLIENT_SECRET is not set", file=sys.stderr)
        return 1

    print(f"Keycloak: {keycloak_url}")
    print(f"Realm: {realm}")
    print(f"Identity service: {identity_service_url}")

    try:
        access_token = _get_token(
            keycloak_url,
            realm,
            client_id,
            client_secret,
            username,
            password,
        )
        identity = _resolve_identity(identity_service_url, access_token)
    except httpx.HTTPStatusError as exc:
        print(
            f"HTTP error from {exc.request.url}: {exc.response.status_code}",
            file=sys.stderr,
        )
        return 1
    except httpx.RequestError as exc:
        print(f"Request error: {exc}", file=sys.stderr)
        return 1

    print("Resolved identity:")
    print(f"  id: {identity.get('id')}")
    print(f"  external_refs: {identity.get('external_refs')}")
    print(f"  created_at: {identity.get('created_at')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
