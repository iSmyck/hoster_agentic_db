"""KBI-901–906 cross-cutting: shared store, identity/GO, stack, evidence."""

from __future__ import annotations

import importlib.util
import inspect
import json
import uuid
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.go_client import HttpGOClient, StubGOClient
from kb_ingestion.app.adapters.identity_client import HttpIdentityClient, StubIdentityClient
from kb_ingestion.app.adapters.object_store import InMemoryObjectStore, build_object_store
from kb_ingestion.app.core.config import settings
from kb_ingestion.app.main import create_app

from shared.object_store import MinioObjectStore, object_key, sha256_hex
from shared.object_store.hashing import sha256_hex as hashing_sha256

REPO = Path(__file__).resolve().parents[3]
_CONVERT = "/api/kb/v1/ingest/convert"
_ACTOR = str(uuid.UUID(int=1))


class FakeMinio:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(self, bucket: str, key: str, data: BytesIO, length: int, content_type: str) -> None:
        self.objects[(bucket, key)] = data.read()

    def get_object(self, bucket: str, key: str) -> BytesIO:
        if (bucket, key) not in self.objects:
            raise KeyError(key)
        payload = self.objects[(bucket, key)]

        class _Resp:
            def read(self) -> bytes:
                return payload

            def close(self) -> None:
                return None

            def release_conn(self) -> None:
                return None

        return _Resp()


def _load_script(name: str, relative: str) -> object:
    path = REPO / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _upload(client: TestClient, *, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    response = client.post(
        _CONVERT,
        data={"space_id": "sales", "client_id": "n8n-1", "data_profile": "strict"},
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        headers=headers or {},
    )
    body = response.json() if response.content else {}
    return response.status_code, body


def test_quoted_keys_do_not_collide() -> None:
    store = InMemoryObjectStore()
    store.put("a/b", "c", "obj", b"one", "text/plain")
    store.put("a", "b/c", "obj", b"two", "text/plain")
    assert store.get("a/b", "c", "obj") == b"one"
    assert store.get("a", "b/c", "obj") == b"two"
    assert object_key("a/b", "c", "obj") != object_key("a", "b/c", "obj")


def test_empty_endpoint_uses_memory() -> None:
    store = build_object_store(endpoint="")
    assert isinstance(store, InMemoryObjectStore)


def test_minio_adapter_round_trip() -> None:
    fake = FakeMinio()
    store = build_object_store(client=fake, bucket="kb-ingest")
    assert isinstance(store, MinioObjectStore)
    staged = store.put("sales", "n8n-1", "abc", b"payload", "text/plain")
    assert staged.sha256 == sha256_hex(b"payload")
    assert store.get("sales", "n8n-1", "abc") == b"payload"
    assert store.count() == 1


def test_backup_hashes_via_shared_helper() -> None:
    from backup.app.adapters import object_store as backup_store

    source = inspect.getsource(backup_store)
    assert "from shared.object_store.hashing import sha256_hex" in source
    assert "hashlib.sha256" not in source
    assert hashing_sha256(b"abc") == sha256_hex(b"abc")


def test_scaffold_has_no_alembic_revisions() -> None:
    root = REPO / "src" / "kb-ingestion"
    assert (root / "app" / "main.py").is_file()
    versions = list((root / "migrations").rglob("versions/*.py"))
    assert versions == []
    deferred = (root / "migrations" / "deferred.py").read_text(encoding="utf-8")
    assert "PRODUCT_SCHEMA_OWNED_BY = \"kb_ops\"" in deferred
    assert "ALEMBIC_VERSIONS: tuple[str, ...] = ()" in deferred


def test_identity_optional_by_default(client: TestClient) -> None:
    status, _ = _upload(client)
    assert status == 201


def test_identity_required_without_actor(monkeypatch: pytest.MonkeyPatch, object_store: InMemoryObjectStore) -> None:
    monkeypatch.setattr(settings, "INGEST_REQUIRE_IDENTITY", True)
    app = create_app(object_store=object_store, identity_client=StubIdentityClient())
    status, body = _upload(TestClient(app))
    assert status == 401
    assert body["detail"]["code"] == "IDENTITY_REQUIRED"
    assert object_store.count() == 0


def test_identity_invalid_actor(monkeypatch: pytest.MonkeyPatch, object_store: InMemoryObjectStore) -> None:
    monkeypatch.setattr(settings, "INGEST_REQUIRE_IDENTITY", True)
    app = create_app(object_store=object_store, identity_client=StubIdentityClient())
    status, body = _upload(TestClient(app), headers={"X-Actor-Id": "not-a-uuid"})
    assert status == 400
    assert body["detail"]["code"] == "INVALID_ACTOR_ID"
    assert object_store.count() == 0


def test_identity_denied(monkeypatch: pytest.MonkeyPatch, object_store: InMemoryObjectStore) -> None:
    monkeypatch.setattr(settings, "INGEST_REQUIRE_IDENTITY", True)
    identity = StubIdentityClient(allowed_prefixes=["/docs"])
    app = create_app(object_store=object_store, identity_client=identity)
    status, body = _upload(TestClient(app), headers={"X-Actor-Id": _ACTOR})
    assert status == 403
    assert body["detail"]["code"] == "IDENTITY_DENIED"
    assert object_store.count() == 0


def test_identity_approved(monkeypatch: pytest.MonkeyPatch, object_store: InMemoryObjectStore) -> None:
    monkeypatch.setattr(settings, "INGEST_REQUIRE_IDENTITY", True)
    app = create_app(object_store=object_store, identity_client=StubIdentityClient())
    status, _ = _upload(TestClient(app), headers={"X-Actor-Id": _ACTOR})
    assert status == 201
    assert object_store.count() == 1


def test_http_clients_selected_from_settings(
    monkeypatch: pytest.MonkeyPatch, object_store: InMemoryObjectStore
) -> None:
    monkeypatch.setattr(settings, "INGEST_GO_BASE_URL", "http://go.test")
    monkeypatch.setattr(settings, "INGEST_IDENTITY_BASE_URL", "http://identity.test")
    app = create_app(object_store=object_store)
    assert isinstance(app.state.go_client, HttpGOClient)
    assert isinstance(app.state.identity_client, HttpIdentityClient)


def test_default_clients_are_stubs(object_store: InMemoryObjectStore) -> None:
    app = create_app(object_store=object_store)
    assert isinstance(app.state.go_client, StubGOClient)
    assert isinstance(app.state.identity_client, StubIdentityClient)


def test_adr_018_accepted() -> None:
    path = REPO / "specs" / "corporate-kb" / "adr" / "ADR-018-source-sync-auto-merge-policy.md"
    text = path.read_text(encoding="utf-8")
    assert "Accepted" in text
    assert "AUTO_MERGE_REQUIRES_TRUSTED" in text


def test_local_stack_registers_ingestion() -> None:
    stack = _load_script("local_stack", "scripts/local_stack.py")
    services = {svc["name"]: svc for svc in stack.SERVICES}
    ingest = services["kb-ingestion"]
    assert ingest["port"] == 8006
    assert ingest["migrations"] is None
    assert ingest["module"] == "kb_ingestion.app.main:app"


def test_smoke_registers_ingestion_health() -> None:
    smoke = _load_script("smoke_local_stack", "scripts/smoke_local_stack.py")
    assert smoke.SERVICES["kb-ingestion"] == "http://127.0.0.1:8006/health"


def test_run_service_aliases_ingestion() -> None:
    text = (REPO / "src" / "run_service.py").read_text(encoding="utf-8")
    assert "_alias_kb_ingestion" in text
    assert "kb-ingestion" in text


def test_evidence_pack_exists() -> None:
    index = REPO / "specs" / "corporate-kb" / "evidence" / "kb-ingestion" / "README.md"
    raw = REPO / "_bmad-output" / "test-artifacts" / "kb-ingestion" / "pytest-summary.json"
    assert index.is_file()
    text = index.read_text(encoding="utf-8")
    assert "VERIFIED(synthetic)" in text
    assert "BLOCKED" in text
    payload = json.loads(raw.read_text(encoding="utf-8"))
    assert payload["command"]
    assert payload["ruff"] in {"clean", "not-run"}
    assert "live_gates" in payload
