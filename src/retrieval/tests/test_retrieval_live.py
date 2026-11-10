"""Live integration tests for Retrieval + Identity on PostgreSQL.

These tests exercise the real services started on their configured ports.
They are skipped unless ``RUN_LIVE_RETRIEVAL_TESTS`` is set or both services
respond to health checks, so the suite remains safe in isolated unit-test runs.
"""

from __future__ import annotations

import os
import secrets
import uuid
from typing import Any

import httpx
import pytest

SPACE_ID = f"live-test-{secrets.token_hex(16)}"
SNAPSHOT_SHA = "a" * 40
STALE_SHA = "b" * 40

IDENTITY_URL = os.environ.get("IDENTITY_SERVICE_URL", "http://localhost:8001").rstrip("/")
RETRIEVAL_URL = os.environ.get("RETRIEVAL_SERVICE_URL", "http://localhost:8003").rstrip("/")


def _services_healthy(timeout: float = 5.0) -> bool:
    with httpx.Client() as client:
        for url in (IDENTITY_URL, RETRIEVAL_URL):
            try:
                resp = client.get(f"{url}/health", timeout=timeout)
                if resp.status_code != 200 or resp.json().get("status") != "ok":
                    return False
            except Exception:  # noqa: BLE001
                return False
    return True


_should_run_live = os.environ.get("RUN_LIVE_RETRIEVAL_TESTS") == "1" or _services_healthy()


pytestmark = pytest.mark.skipif(
    not _should_run_live,
    reason="Live services not healthy and RUN_LIVE_RETRIEVAL_TESTS not set",
)


@pytest.fixture(scope="module")
def http_client() -> Any:
    with httpx.Client() as client:
        yield client


@pytest.fixture(scope="module")
def reader_id(http_client: httpx.Client) -> uuid.UUID:
    resp = http_client.post(
        f"{IDENTITY_URL}/api/kb/v1/identity/resolve",
        json={"external_ref": {"issuer": "live-test", "sub": "reader-001"}},
        timeout=10.0,
    )
    resp.raise_for_status()
    return uuid.UUID(resp.json()["id"])


@pytest.fixture(scope="module")
def outsider_id(http_client: httpx.Client) -> uuid.UUID:
    resp = http_client.post(
        f"{IDENTITY_URL}/api/kb/v1/identity/resolve",
        json={"external_ref": {"issuer": "live-test", "sub": "outsider-001"}},
        timeout=10.0,
    )
    resp.raise_for_status()
    return uuid.UUID(resp.json()["id"])


@pytest.fixture(scope="module", autouse=True)
def _seed_identity(http_client: httpx.Client) -> None:
    """Seed group snapshot and policy bundle once per module."""
    group_resp = http_client.post(
        f"{IDENTITY_URL}/api/kb/v1/groups/snapshot",
        json={
            "space_id": SPACE_ID,
            "groups": [
                {
                    "group_name": "readers",
                    "member_refs": [{"issuer": "live-test", "sub": "reader-001"}],
                    "parent_groups": [],
                },
            ],
        },
        timeout=10.0,
    )
    group_resp.raise_for_status()

    policy_resp = http_client.post(
        f"{IDENTITY_URL}/api/kb/v1/policies/activate",
        json={
            "space_id": SPACE_ID,
            "bundle_id": "live-test-bundle",
            "repository_id": SPACE_ID,
            "access_policy_revision": "0" * 40,
            "approval_policy_revision": "0" * 40,
            "path_approvers": {"readers": ["/docs"]},
        },
        timeout=10.0,
    )
    policy_resp.raise_for_status()


@pytest.fixture(scope="module")
def active_generation_id(http_client: httpx.Client) -> uuid.UUID:
    """Build and activate an index generation for the live Space."""
    build_resp = http_client.post(
        f"{RETRIEVAL_URL}/api/kb/v1/index/build",
        json={"space_id": SPACE_ID, "snapshot_sha": SNAPSHOT_SHA},
        timeout=30.0,
    )
    build_resp.raise_for_status()
    generation_id = uuid.UUID(build_resp.json()["generation_id"])

    # Use the current active pointer's fence token (or 0 if none) so this
    # fixture composes with prior activations left by the smoke script.
    pointer_resp = http_client.get(
        f"{RETRIEVAL_URL}/api/kb/v1/index/pointer",
        params={"space_id": SPACE_ID, "profile": "default"},
        timeout=10.0,
    )
    if pointer_resp.status_code == 200:
        fence_token = pointer_resp.json()["fence_token"]
    else:
        fence_token = 0

    activate_resp = http_client.post(
        f"{RETRIEVAL_URL}/api/kb/v1/index/activate",
        json={
            "space_id": SPACE_ID,
            "profile": "default",
            "generation_id": str(generation_id),
            "fence_token": fence_token,
        },
        timeout=10.0,
    )
    activate_resp.raise_for_status()
    return generation_id


class TestRetrievalLiveIntegration:
    def test_services_healthy(self, http_client: httpx.Client) -> None:
        for url in (IDENTITY_URL, RETRIEVAL_URL):
            resp = http_client.get(f"{url}/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    def test_authorized_search_returns_allowed_chunks(
        self,
        http_client: httpx.Client,
        reader_id: uuid.UUID,
        active_generation_id: uuid.UUID,
    ) -> None:
        resp = http_client.post(
            f"{RETRIEVAL_URL}/api/kb/v1/search",
            json={
                "space_id": SPACE_ID,
                "query": "retrieval documentation",
                "actor_id": str(reader_id),
                "profile": "default",
                "mode": "hybrid",
                "top_k": 10,
            },
            timeout=30.0,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["space_id"] == SPACE_ID
        paths = {r["document_path"] for r in body["results"]}
        assert "docs/public.md" in paths
        assert "secret/internal.md" not in paths

    def test_unauthorized_search_returns_empty(
        self,
        http_client: httpx.Client,
        outsider_id: uuid.UUID,
        active_generation_id: uuid.UUID,
    ) -> None:
        resp = http_client.post(
            f"{RETRIEVAL_URL}/api/kb/v1/search",
            json={
                "space_id": SPACE_ID,
                "query": "retrieval documentation",
                "actor_id": str(outsider_id),
                "profile": "default",
                "mode": "hybrid",
                "top_k": 10,
            },
            timeout=30.0,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["results"] == []
        assert body["authorization_filtered_count"] > 0

    def test_stale_cursor_returns_conflict(
        self,
        http_client: httpx.Client,
        reader_id: uuid.UUID,
        active_generation_id: uuid.UUID,
    ) -> None:
        resp = http_client.post(
            f"{RETRIEVAL_URL}/api/kb/v1/search",
            json={
                "space_id": SPACE_ID,
                "query": "retrieval documentation",
                "actor_id": str(reader_id),
                "profile": "default",
                "mode": "hybrid",
                "top_k": 10,
                "cursor": STALE_SHA,
            },
            timeout=30.0,
        )
        assert resp.status_code == 409, resp.text
        detail = resp.json()["detail"]
        assert detail["code"] == "STALE_SNAPSHOT"
