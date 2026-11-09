"""End-to-end smoke test for corp-ai-db backend services.

Exercises the full flow against real local infrastructure:

  Keycloak token -> identity resolution -> group snapshot / policy bundle
  -> GitLab HEAD -> index build -> index activate -> authorized search

Set all required environment variables in ``.env`` before running.
No secrets or tokens are printed.
"""

from __future__ import annotations

import base64
import os
import sys
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

IDENTITY_URL = os.environ.get("IDENTITY_SERVICE_URL", "http://localhost:8001")
GO_URL = os.environ.get("GO_SERVICE_URL", "http://localhost:8002")
RETRIEVAL_URL = os.environ.get("RETRIEVAL_SERVICE_URL", "http://localhost:8003")
INGESTION_URL = os.environ.get("INGESTION_SERVICE_URL", "http://localhost:8004")


def _http_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Execute an httpx request and convert transport errors to a clean failure."""
    try:
        return httpx.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        _fail(f"HTTP request failed for {exc.request.url}: {exc}")


def _http_get(url: str, **kwargs: Any) -> httpx.Response:
    return _http_request("GET", url, **kwargs)


def _http_post(url: str, **kwargs: Any) -> httpx.Response:
    return _http_request("POST", url, **kwargs)


KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8082")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "corp-kb")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "identity-service")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
KEYCLOAK_TEST_USERNAME = os.environ.get("KEYCLOAK_TEST_USERNAME", "testuser")
KEYCLOAK_TEST_PASSWORD = os.environ.get("KEYCLOAK_TEST_PASSWORD", "testpass")

GITLAB_URL = os.environ.get("GITLAB_URL", os.environ.get("GO_GITLAB_URL", "http://localhost:8081"))
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", os.environ.get("GO_GITLAB_TOKEN", ""))
SPACE_ID = os.environ.get("SMOKE_SPACE_ID", "corp-kb/sales")


def _fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def _get_keycloak_token() -> str:
    if not KEYCLOAK_CLIENT_SECRET:
        _fail("KEYCLOAK_CLIENT_SECRET is not set")
    resp = _http_post(
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "username": KEYCLOAK_TEST_USERNAME,
            "password": KEYCLOAK_TEST_PASSWORD,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30.0,
    )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _fail(f"Keycloak token request failed: {exc.response.status_code}")
    return resp.json()["access_token"]


def _resolve_identity(token: str) -> dict:
    resp = _http_post(
        f"{IDENTITY_URL}/api/kb/v1/identity/resolve-token",
        json={"access_token": token},
        timeout=30.0,
    )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _fail(f"Identity resolution failed: {exc.response.status_code}")
    return resp.json()


def _ensure_authz(actor_id: str, external_ref: dict) -> None:
    sub = external_ref.get("sub", "")
    issuer = external_ref.get("issuer", "")
    if not sub or not issuer:
        _fail("Identity external_ref missing sub/issuer")

    resp = _http_post(
        f"{IDENTITY_URL}/api/kb/v1/groups/snapshot",
        json={
            "space_id": SPACE_ID,
            "groups": [
                {
                    "group_name": "smoke-testers",
                    "member_refs": [{"issuer": issuer, "sub": sub}],
                    "parent_groups": [],
                },
            ],
        },
        timeout=30.0,
    )
    if resp.status_code not in (200, 201):
        _fail(f"Group snapshot failed: {resp.status_code}")

    resp = _http_post(
        f"{IDENTITY_URL}/api/kb/v1/policies/activate",
        json={
            "space_id": SPACE_ID,
            "bundle_id": "smoke-bundle",
            "repository_id": SPACE_ID,
            "access_policy_revision": "0" * 40,
            "approval_policy_revision": "1" * 40,
            "group_capabilities": {"smoke-testers": ["read", "search"]},
            "path_approvers": {"smoke-testers": ["/"]},
        },
        timeout=30.0,
    )
    if resp.status_code not in (200, 201):
        _fail(f"Policy activation failed: {resp.status_code}")


def _gitlab_project_id() -> str:
    resp = _http_get(
        f"{GITLAB_URL}/api/v4/projects",
        headers={"Authorization": f"Bearer {GITLAB_TOKEN}"},
        params={"search": SPACE_ID.split("/")[-1]},
        timeout=30.0,
    )
    resp.raise_for_status()
    projects = resp.json()
    for project in projects:
        if project.get("path_with_namespace") == SPACE_ID:
            return str(project["id"])
    _fail(f"GitLab project {SPACE_ID} not found")


def _default_branch(project_id: str) -> str:
    resp = _http_get(
        f"{GITLAB_URL}/api/v4/projects/{project_id}",
        headers={"Authorization": f"Bearer {GITLAB_TOKEN}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json().get("default_branch", "main")


def _ensure_test_document(project_id: str, branch: str) -> str:
    timestamp = datetime.now(UTC).isoformat()
    path = f"smoke-e2e-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.md"
    content = f"""# E2E Smoke Test Document

This document was created by the end-to-end smoke test at {timestamp}.

## Sales Process

1. Refine leads from marketing campaigns
2. Conduct discovery calls with prospects
3. Prepare proposals using approved templates
4. Submit proposals for business review
5. Close deals and onboard new customers

## Contact

For questions, contact the sales team at sales@example.com.
"""
    encoded = base64.b64encode(content.encode()).decode()
    resp = _http_post(
        f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/files/{quote(path, safe='')}",
        headers={"Authorization": f"Bearer {GITLAB_TOKEN}"},
        json={
            "branch": branch,
            "content": encoded,
            "encoding": "base64",
            "commit_message": f"E2E smoke test document {timestamp}",
        },
        timeout=30.0,
    )
    if resp.status_code not in (200, 201):
        _fail(f"GitLab document creation failed: {resp.status_code}")
    return path


def _get_head_sha(project_id: str, branch: str) -> str:
    resp = _http_get(
        f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits/{quote(branch, safe='')}",
        headers={"Authorization": f"Bearer {GITLAB_TOKEN}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _build_index(sha: str) -> dict:
    resp = _http_post(
        f"{RETRIEVAL_URL}/api/kb/v1/index/build",
        json={"space_id": SPACE_ID, "snapshot_sha": sha},
        timeout=120.0,
    )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _fail(f"Index build failed: {exc.response.status_code} {exc.response.text}")
    return resp.json()


def _current_fence_token() -> int:
    resp = _http_get(
        f"{RETRIEVAL_URL}/api/kb/v1/index/pointer",
        params={"space_id": SPACE_ID, "profile": "default"},
        timeout=30.0,
    )
    if resp.status_code == 404:
        return 0
    if resp.status_code != 200:
        _fail(f"Failed to read active pointer: {resp.status_code}")
    return resp.json()["fence_token"]


def _activate_index(generation_id: str) -> dict:
    fence_token = _current_fence_token()
    resp = _http_post(
        f"{RETRIEVAL_URL}/api/kb/v1/index/activate",
        json={
            "space_id": SPACE_ID,
            "profile": "default",
            "generation_id": generation_id,
            "fence_token": fence_token,
        },
        timeout=30.0,
    )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _fail(f"Index activation failed: {exc.response.status_code} {exc.response.text}")
    return resp.json()


def _search(actor_id: str, query: str) -> dict:
    resp = _http_post(
        f"{RETRIEVAL_URL}/api/kb/v1/search",
        json={
            "space_id": SPACE_ID,
            "query": query,
            "actor_id": actor_id,
            "top_k": 5,
        },
        timeout=60.0,
    )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _fail(f"Search failed: {exc.response.status_code} {exc.response.text}")
    return resp.json()


def main() -> int:
    print("1. Authenticating with Keycloak...")
    token = _get_keycloak_token()

    print("2. Resolving identity...")
    identity = _resolve_identity(token)
    actor_id = identity["id"]
    external_ref = identity["external_refs"][0]
    print(f"   actor_id: {actor_id}")

    print("3. Ensuring AuthZ snapshot/policy...")
    _ensure_authz(actor_id, external_ref)

    print("4. Preparing GitLab test document...")
    project_id = _gitlab_project_id()
    branch = _default_branch(project_id)
    doc_path = _ensure_test_document(project_id, branch)
    print(f"   created {doc_path} on branch {branch}")

    print("5. Reading GitLab HEAD...")
    head_sha = _get_head_sha(project_id, branch)
    print(f"   HEAD: {head_sha}")

    print("6. Building index...")
    build_result = _build_index(head_sha)
    print(f"   generation_id: {build_result['generation_id']}")
    print(f"   chunks_indexed: {build_result['chunks_indexed']}")

    print("7. Activating index...")
    activate_result = _activate_index(build_result["generation_id"])
    print(f"   pointer_id: {activate_result['pointer_id']}")

    print("8. Searching...")
    search_result = _search(actor_id, "discovery calls")
    print(f"   results: {len(search_result['results'])}")
    print(f"   filtered: {search_result['authorization_filtered_count']}")

    if not search_result["results"]:
        _fail("Search returned no authorized results")

    top_path = search_result["results"][0]["document_path"]
    print(f"   top result: {top_path}")

    if doc_path not in {r["document_path"] for r in search_result["results"]}:
        _fail(f"Newly created document {doc_path} not found in search results")

    print("\nE2E smoke test PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
