#!/usr/bin/env python3
"""Live smoke test for the Retrieval + Identity integration.

Assumes:
  - PostgreSQL is running and kb_authz/kb_index schemas exist.
  - Identity service is running on IDENTITY_SERVICE_URL (default 8001).
  - Retrieval service is running on RETRIEVAL_SERVICE_URL (default 8003).

The script seeds a synthetic identity, group snapshot and policy bundle in the
Identity service, then builds and activates a stub index in the Retrieval
service and verifies authorized/unauthorized search plus stale-cursor behavior.

Run with stub embeddings and GO client for a self-contained local test:
    RETRIEVAL_EMBEDDING_MODEL=stub-deterministic \
    RETRIEVAL_EMBEDDING_DIMENSIONS=384 \
    RETRIEVAL_GO_CLIENT_MODE=stub \
    uv run python src/retrieval/scripts/smoke_retrieval.py

No real secrets are logged.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from typing import Any

import httpx

# Synthetic fixture identifiers. These are public test values, not secrets.
SPACE_ID = f"smoke-space-{uuid.uuid4().hex[:8]}"
SNAPSHOT_SHA = "a" * 40
STALE_SHA = "b" * 40


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


IDENTITY_URL = _env("IDENTITY_SERVICE_URL", "http://localhost:8001").rstrip("/")
RETRIEVAL_URL = _env("RETRIEVAL_SERVICE_URL", "http://localhost:8003").rstrip("/")


def _wait_for_health(client: httpx.Client, url: str, service: str, timeout: float = 30.0) -> None:
    """Wait until ``service`` health endpoint returns 200."""
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            resp = client.get(f"{url}/health", timeout=2.0)
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"{service} health check failed: {last_error}")


def _resolve_identity(client: httpx.Client, issuer: str, sub: str) -> uuid.UUID:
    """Create or resolve a stable identity and return its id."""
    resp = client.post(
        f"{IDENTITY_URL}/api/kb/v1/identity/resolve",
        json={"external_ref": {"issuer": issuer, "sub": sub}},
        timeout=10.0,
    )
    resp.raise_for_status()
    return uuid.UUID(resp.json()["id"])


def _ingest_group_snapshot(
    client: httpx.Client,
    space_id: str,
    groups: list[dict[str, Any]],
) -> None:
    resp = client.post(
        f"{IDENTITY_URL}/api/kb/v1/groups/snapshot",
        json={"space_id": space_id, "groups": groups},
        timeout=10.0,
    )
    resp.raise_for_status()


def _activate_policy_bundle(
    client: httpx.Client,
    space_id: str,
    path_approvers: dict[str, list[str]],
) -> None:
    resp = client.post(
        f"{IDENTITY_URL}/api/kb/v1/policies/activate",
        json={
            "space_id": space_id,
            "bundle_id": "smoke-bundle",
            "repository_id": space_id,
            "access_policy_revision": "0" * 40,
            "approval_policy_revision": "0" * 40,
            "path_approvers": path_approvers,
        },
        timeout=10.0,
    )
    resp.raise_for_status()


def _build_index(client: httpx.Client, space_id: str, snapshot_sha: str) -> uuid.UUID:
    resp = client.post(
        f"{RETRIEVAL_URL}/api/kb/v1/index/build",
        json={"space_id": space_id, "snapshot_sha": snapshot_sha},
        timeout=30.0,
    )
    resp.raise_for_status()
    body = resp.json()
    print(f"  index build: {body['chunks_indexed']} chunk(s) indexed")
    return uuid.UUID(body["generation_id"])


def _activate_pointer(
    client: httpx.Client,
    space_id: str,
    generation_id: uuid.UUID,
) -> int:
    # Compose with any previously activated pointer (e.g. from an earlier
    # smoke run or the live test suite).
    pointer_resp = client.get(
        f"{RETRIEVAL_URL}/api/kb/v1/index/pointer",
        params={"space_id": space_id, "profile": "default"},
        timeout=10.0,
    )
    if pointer_resp.status_code == 200:
        fence_token = pointer_resp.json()["fence_token"]
    else:
        fence_token = 0

    resp = client.post(
        f"{RETRIEVAL_URL}/api/kb/v1/index/activate",
        json={
            "space_id": space_id,
            "profile": "default",
            "generation_id": str(generation_id),
            "fence_token": fence_token,
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    body = resp.json()
    print(f"  pointer activated: fence_token={body['fence_token']}")
    return int(body["fence_token"])


def _search(
    client: httpx.Client,
    space_id: str,
    query: str,
    actor_id: uuid.UUID,
    cursor: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "space_id": space_id,
        "query": query,
        "actor_id": str(actor_id),
        "profile": "default",
        "mode": "hybrid",
        "top_k": 10,
    }
    if cursor is not None:
        payload["cursor"] = cursor
    resp = client.post(
        f"{RETRIEVAL_URL}/api/kb/v1/search",
        json=payload,
        timeout=30.0,
    )
    return {"status_code": resp.status_code, "body": resp.json()}


def main() -> int:
    print("B.3 Retrieval live integration smoke test")
    print(f"  identity: {IDENTITY_URL}")
    print(f"  retrieval: {RETRIEVAL_URL}")

    with httpx.Client() as client:
        print("\n1. Health checks")
        _wait_for_health(client, IDENTITY_URL, "identity")
        print("  identity: ok")
        _wait_for_health(client, RETRIEVAL_URL, "retrieval")
        print("  retrieval: ok")

        print("\n2. Seed Identity service")
        reader_issuer = "smoke-test"
        reader_sub = "reader-001"
        approver_sub = "approver-001"
        outsider_sub = "outsider-001"

        reader_id = _resolve_identity(client, reader_issuer, reader_sub)
        approver_id = _resolve_identity(client, reader_issuer, approver_sub)
        outsider_id = _resolve_identity(client, reader_issuer, outsider_sub)
        print(f"  reader_id={reader_id}")
        print(f"  approver_id={approver_id}")
        print(f"  outsider_id={outsider_id}")

        _ingest_group_snapshot(
            client,
            SPACE_ID,
            groups=[
                {
                    "group_name": "readers",
                    "member_refs": [{"issuer": reader_issuer, "sub": reader_sub}],
                    "parent_groups": [],
                },
                {
                    "group_name": "approvers",
                    "member_refs": [{"issuer": reader_issuer, "sub": approver_sub}],
                    "parent_groups": [],
                },
            ],
        )
        print("  group snapshot: ok")

        _activate_policy_bundle(
            client,
            SPACE_ID,
            path_approvers={
                "readers": ["/docs"],
                "approvers": ["/docs", "/secret"],
            },
        )
        print("  policy bundle: ok")

        print("\n3. Build and activate index")
        generation_id = _build_index(client, SPACE_ID, SNAPSHOT_SHA)
        _activate_pointer(client, SPACE_ID, generation_id)

        print("\n4. Authorized search (reader)")
        authorized = _search(client, SPACE_ID, "retrieval documentation", reader_id)
        if authorized["status_code"] != 200:
            print(f"  FAIL: expected 200, got {authorized['status_code']}: {authorized['body']}")
            return 1
        auth_paths = {r["document_path"] for r in authorized["body"]["results"]}
        print(f"  results: {auth_paths}")
        if "docs/public.md" not in auth_paths:
            print("  FAIL: docs/public.md missing for authorized reader")
            return 1
        if "secret/internal.md" in auth_paths:
            print("  FAIL: secret/internal.md leaked to reader")
            return 1
        print("  PASS")

        print("\n5. Unauthorized search (outsider)")
        unauthorized = _search(client, SPACE_ID, "retrieval documentation", outsider_id)
        if unauthorized["status_code"] != 200:
            print(
                f"  FAIL: expected 200, got {unauthorized['status_code']}: {unauthorized['body']}"
            )
            return 1
        if unauthorized["body"]["results"]:
            print(f"  FAIL: outsider got results: {unauthorized['body']['results']}")
            return 1
        print("  PASS")

        print("\n6. Stale cursor search")
        stale = _search(client, SPACE_ID, "retrieval documentation", reader_id, cursor=STALE_SHA)
        if stale["status_code"] != 409:
            print(f"  FAIL: expected 409, got {stale['status_code']}: {stale['body']}")
            return 1
        if stale["body"].get("detail", {}).get("code") != "STALE_SNAPSHOT":
            print(f"  FAIL: expected STALE_SNAPSHOT, got {stale['body']}")
            return 1
        print("  PASS")

    print("\nAll smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
