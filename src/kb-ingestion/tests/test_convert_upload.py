"""Tests for POST /api/kb/v1/ingest/convert (KBI.1.1)."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.object_store import InMemoryObjectStore

_CONVERT_URL = "/api/kb/v1/ingest/convert"
_MAX = 104_857_600


def _multipart(
    client: TestClient,
    *,
    space_id: str = "sales",
    client_id: str = "n8n-1",
    data_profile: str = "strict",
    legal_basis: str | None = None,
    file_content: bytes = b"%PDF-1.4 sample",
    file_name: str = "doc.pdf",
    content_type: str | None = "application/pdf",
    include_file: bool = True,
) -> tuple[int, dict]:
    data: dict[str, str] = {
        "space_id": space_id,
        "client_id": client_id,
        "data_profile": data_profile,
    }
    if legal_basis is not None:
        data["legal_basis"] = legal_basis
    files = None
    if include_file:
        if content_type is None:
            files = {"file": (file_name, file_content)}
        else:
            files = {"file": (file_name, file_content, content_type)}
    response = client.post(_CONVERT_URL, data=data, files=files)
    body = response.json() if response.content else {}
    return response.status_code, body


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_strict_upload_stages_bytes(client: TestClient, object_store: InMemoryObjectStore) -> None:
    content = b"hello-staging"
    status, body = _multipart(client, file_content=content, content_type="application/pdf")
    assert status == 201
    assert set(body) == {"object_id", "sha256", "version_id", "size", "media_type"}
    assert body["sha256"] == hashlib.sha256(content).hexdigest()
    assert body["size"] == len(content)
    assert body["media_type"] == "application/pdf"
    assert "-" not in body["object_id"]
    assert len(body["object_id"]) == 32
    stored = object_store.get("sales", "n8n-1", body["object_id"])
    assert stored == content
    assert object_store.count() == 1


def test_pii_permitted_with_legal_basis(client: TestClient, object_store: InMemoryObjectStore) -> None:
    status, _ = _multipart(
        client,
        data_profile="pii_permitted",
        legal_basis="contract-2026-001",
    )
    assert status == 201
    assert object_store.count() == 1


def test_pii_permitted_without_legal_basis_rejected(
    client: TestClient, object_store: InMemoryObjectStore
) -> None:
    status, body = _multipart(client, data_profile="pii_permitted", legal_basis="")
    assert status == 400
    assert body["detail"]["code"] == "LEGAL_BASIS_REQUIRED"
    assert object_store.count() == 0


def test_pii_permitted_whitespace_legal_basis_rejected(
    client: TestClient, object_store: InMemoryObjectStore
) -> None:
    status, body = _multipart(client, data_profile="pii_permitted", legal_basis="   ")
    assert status == 400
    assert body["detail"]["code"] == "LEGAL_BASIS_REQUIRED"
    assert object_store.count() == 0


def test_pii_permitted_omitted_legal_basis_rejected(
    client: TestClient, object_store: InMemoryObjectStore
) -> None:
    data = {
        "space_id": "sales",
        "client_id": "n8n-1",
        "data_profile": "pii_permitted",
    }
    response = client.post(
        _CONVERT_URL,
        data=data,
        files={"file": ("doc.pdf", b"content", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "LEGAL_BASIS_REQUIRED"
    assert object_store.count() == 0


def test_oversize_rejected(client: TestClient, object_store: InMemoryObjectStore) -> None:
    status, body = _multipart(client, file_content=b"x" * (_MAX + 1))
    assert status == 413
    assert body["detail"]["code"] == "SIZE_LIMIT_EXCEEDED"
    assert object_store.count() == 0


def test_exact_size_limit_allowed(client: TestClient, object_store: InMemoryObjectStore) -> None:
    status, _ = _multipart(client, file_content=b"a" * _MAX)
    assert status == 201
    assert object_store.count() == 1


def test_invalid_data_profile(client: TestClient, object_store: InMemoryObjectStore) -> None:
    status, body = _multipart(client, data_profile="open")
    assert status == 400
    assert body["detail"]["code"] == "INVALID_DATA_PROFILE"
    assert object_store.count() == 0


@pytest.mark.parametrize(
    ("space_id", "client_id", "expected_code"),
    [
        ("", "n8n-1", "INVALID_SPACE_ID"),
        ("../x", "n8n-1", "INVALID_SPACE_ID"),
        ("sales", "", "INVALID_CLIENT_ID"),
        ("sales", "../bad", "INVALID_CLIENT_ID"),
    ],
)
def test_invalid_identifiers(
    client: TestClient,
    object_store: InMemoryObjectStore,
    space_id: str,
    client_id: str,
    expected_code: str,
) -> None:
    status, body = _multipart(client, space_id=space_id, client_id=client_id)
    assert status == 400
    assert body["detail"]["code"] == expected_code
    assert object_store.count() == 0


def test_missing_file(client: TestClient, object_store: InMemoryObjectStore) -> None:
    status, body = _multipart(client, include_file=False)
    assert status == 422
    assert body["detail"]["code"] == "MISSING_FILE"
    assert object_store.count() == 0


def test_default_media_type_when_missing_content_type(
    client: TestClient,
) -> None:
    status, body = _multipart(client, content_type=None, file_name="payload.bin")
    assert status == 201
    assert body["media_type"] == "application/octet-stream"