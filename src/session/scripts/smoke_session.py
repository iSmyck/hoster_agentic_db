"""Live smoke test for the Session service.

Requires the session service to be running on http://127.0.0.1:8004 and a
reachable PostgreSQL instance. The script exercises create, validate, refresh,
and revoke without touching the upstream IdP.
"""

from __future__ import annotations

import os
import sys

import httpx

BASE_URL = os.environ.get("SESSION_SERVICE_URL", "http://127.0.0.1:8004")


def _fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    health = httpx.get(f"{BASE_URL}/health", timeout=10)
    if health.status_code != 200:
        _fail(f"health check failed: {health.status_code} {health.text}")
    print("health ok")

    create_resp = httpx.post(
        f"{BASE_URL}/api/kb/v1/session/create",
        json={"stable_id": "test:alice"},
        timeout=10,
    )
    if create_resp.status_code != 200:
        _fail(f"create failed: {create_resp.status_code} {create_resp.text}")
    body = create_resp.json()
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]
    stable_id = body["stable_id"]
    if stable_id != "test:alice":
        _fail(f"unexpected stable_id: {stable_id}")
    print("create ok")

    validate_resp = httpx.get(
        f"{BASE_URL}/api/kb/v1/session/validate",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if validate_resp.status_code != 200:
        _fail(f"validate failed: {validate_resp.status_code} {validate_resp.text}")
    validated = validate_resp.json()
    if validated["stable_id"] != "test:alice":
        _fail(f"validate returned wrong stable_id: {validated}")
    print("validate ok")

    refresh_resp = httpx.post(
        f"{BASE_URL}/api/kb/v1/session/refresh",
        json={"refresh_token": refresh_token},
        timeout=10,
    )
    if refresh_resp.status_code != 200:
        _fail(f"refresh failed: {refresh_resp.status_code} {refresh_resp.text}")
    new_access = refresh_resp.json()["access_token"]
    if new_access == access_token:
        _fail("refresh returned the same access token")
    print("refresh ok")

    logout_resp = httpx.post(
        f"{BASE_URL}/api/kb/v1/session/logout",
        json={"access_token": new_access},
        timeout=10,
    )
    if logout_resp.status_code != 204:
        _fail(f"logout failed: {logout_resp.status_code} {logout_resp.text}")
    print("logout ok")

    after_logout = httpx.get(
        f"{BASE_URL}/api/kb/v1/session/validate",
        headers={"Authorization": f"Bearer {new_access}"},
        timeout=10,
    )
    if after_logout.status_code != 401:
        _fail(f"revoked token still valid: {after_logout.status_code}")
    print("revoked token rejected ok")

    print("smoke session passed")


if __name__ == "__main__":
    main()
