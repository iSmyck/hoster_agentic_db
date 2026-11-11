"""Synthetic API tests for T04a durable drafts and history."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def author_client(seeded_client: TestClient) -> TestClient:
    """Seeded client acting as the draft author."""
    return seeded_client


def test_save_draft_creates_or_updates(author_client: TestClient) -> None:
    payload = {
        "space_id": "corp-kb/sales",
        "path": "docs/new-draft.md",
        "content": "# New draft\n\nContent.\n",
        "target_branch": "main",
        "base_sha": "a" * 40,
    }
    r = author_client.post("/api/kb/v1/drafts/save", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["space_id"] == payload["space_id"]
    assert data["path"] == payload["path"]
    assert data["author_stable_id"] == "author-1"
    assert data["content"] == payload["content"]
    assert data["base_sha"] == payload["base_sha"]

    # Second save updates the same draft (idempotency by slot).
    payload["content"] = "# Updated\n"
    r2 = author_client.post("/api/kb/v1/drafts/save", json=payload)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["id"] == data["id"]
    assert data2["content"] == "# Updated\n"


def test_get_draft_returns_saved(author_client: TestClient) -> None:
    r = author_client.post(
        "/api/kb/v1/drafts/get",
        json={"space_id": "corp-kb/sales", "path": "docs/g1-proposal.md"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["path"] == "docs/g1-proposal.md"
    assert data["author_stable_id"] == "author-1"
    assert "content" in data


def test_get_missing_draft_404(author_client: TestClient) -> None:
    r = author_client.post(
        "/api/kb/v1/drafts/get",
        json={"space_id": "corp-kb/sales", "path": "docs/no-such-draft.md"},
    )
    assert r.status_code == 404


def test_list_drafts_paginated(author_client: TestClient) -> None:
    r = author_client.post(
        "/api/kb/v1/drafts/list",
        json={"space_id": "corp-kb/sales", "limit": 10},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["space_id"] == "corp-kb/sales"
    assert len(data["drafts"]) >= 2
    for draft in data["drafts"]:
        assert draft["author_stable_id"] == "author-1"


def test_discard_draft(author_client: TestClient) -> None:
    # Ensure a draft exists for the discard target.
    author_client.post(
        "/api/kb/v1/drafts/save",
        json={
            "space_id": "corp-kb/sales",
            "path": "docs/to-discard.md",
            "content": "# Discard me\n",
            "target_branch": "main",
        },
    )
    r = author_client.post(
        "/api/kb/v1/drafts/discard",
        json={"space_id": "corp-kb/sales", "path": "docs/to-discard.md"},
    )
    assert r.status_code == 200
    assert r.json()["discarded"] is True

    r2 = author_client.post(
        "/api/kb/v1/drafts/get",
        json={"space_id": "corp-kb/sales", "path": "docs/to-discard.md"},
    )
    assert r2.status_code == 404


def test_history_returns_commits(author_client: TestClient) -> None:
    r = author_client.post(
        "/api/kb/v1/documents/history",
        json={
            "space_id": "corp-kb/sales",
            "path": "docs/g1-proposal.md",
            "branch": "main",
            "limit": 10,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["space_id"] == "corp-kb/sales"
    assert data["path"] == "docs/g1-proposal.md"
    assert len(data["commits"]) >= 3
    for commit in data["commits"]:
        assert "sha" in commit
        assert "message" in commit
        assert "committed_date" in commit


def test_history_pagination_cursor(author_client: TestClient) -> None:
    first = author_client.post(
        "/api/kb/v1/documents/history",
        json={
            "space_id": "corp-kb/sales",
            "path": "docs/g1-proposal.md",
            "branch": "main",
            "limit": 2,
        },
    )
    assert first.status_code == 200
    data = first.json()
    assert len(data["commits"]) == 2
    assert data["next_cursor"] is not None

    second = author_client.post(
        "/api/kb/v1/documents/history",
        json={
            "space_id": "corp-kb/sales",
            "path": "docs/g1-proposal.md",
            "branch": "main",
            "limit": 2,
            "cursor": data["next_cursor"],
        },
    )
    assert second.status_code == 200
    data2 = second.json()
    assert len(data2["commits"]) >= 1
    assert all(c["committed_date"] < data["next_cursor"] for c in data2["commits"])


def test_draft_security_space_isolation(author_client: TestClient) -> None:
    r = author_client.post(
        "/api/kb/v1/drafts/save",
        json={
            "space_id": "unauthorized-space",
            "path": "docs/x.md",
            "content": "# x\n",
            "target_branch": "main",
        },
    )
    assert r.status_code == 404


def test_draft_security_path_validation(author_client: TestClient) -> None:
    r = author_client.post(
        "/api/kb/v1/drafts/save",
        json={
            "space_id": "corp-kb/sales",
            "path": "../etc/passwd",
            "content": "# x\n",
            "target_branch": "main",
        },
    )
    assert r.status_code in (400, 403)
