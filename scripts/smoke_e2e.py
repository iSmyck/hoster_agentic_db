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
from urllib.parse import quote

import httpx
from sqlalchemy import create_engine, text

IDENTITY_URL = os.environ.get("IDENTITY_SERVICE_URL", "http://localhost:8001")
GO_URL = os.environ.get("GO_SERVICE_URL", "http://localhost:8002")
RETRIEVAL_URL = os.environ.get("RETRIEVAL_SERVICE_URL", "http://localhost:8003")
INGESTION_URL = os.environ.get("INGESTION_SERVICE_URL", "http://localhost:8004")

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
    resp = httpx.post(
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
    resp = httpx.post(
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

    resp = httpx.post(
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

    resp = httpx.post(
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
    resp = httpx.get(
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


def _ensure_test_document(project_id: str) -> str:
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
    resp = httpx.post(
        f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/files/{quote(path, safe='')}",
        headers={"Authorization": f"Bearer {GITLAB_TOKEN}"},
        json={
            "branch": "main",
            "content": encoded,
            "encoding": "base64",
            "commit_message": f"E2E smoke test document {timestamp}",
        },
        timeout=30.0,
    )
    if resp.status_code not in (200, 201):
        _fail(f"GitLab document creation failed: {resp.status_code}")
    return path


def _get_head_sha(project_id: str) -> str:
    resp = httpx.get(
        f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits/main",
        headers={"Authorization": f"Bearer {GITLAB_TOKEN}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _build_index(sha: str) -> dict:
    resp = httpx.post(
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
    db_url = os.environ.get("RETRIEVAL_DATABASE_URL", os.environ.get("DATABASE_URL", ""))
    if not db_url:
        _fail("RETRIEVAL_DATABASE_URL or DATABASE_URL required for fence token lookup")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT fence_token FROM kb_index.index_pointers "
                "WHERE space_id = :space_id AND profile = :profile AND active"
            ),
            {"space_id": SPACE_ID, "profile": "default"},
        ).fetchone()
    return row[0] if row else 0


def _activate_index(generation_id: str) -> dict:
    fence_token = _current_fence_token()
    resp = httpx.post(
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
    resp = httpx.post(
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
    doc_path = _ensure_test_document(project_id)
    print(f"   created {doc_path}")

    print("5. Reading GitLab HEAD...")
    head_sha = _get_head_sha(project_id)
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
