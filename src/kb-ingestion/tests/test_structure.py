"""KBI.2.1 batch-read of converted Markdown."""

from __future__ import annotations

from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.object_store import InMemoryObjectStore
from kb_ingestion.app.services.converted_corpus import ConvertedCorpus, ConvertedDocument

from .test_convert import _minimal_docx, _run, _upload
from .test_media import _bytes_len

_BATCH = "/api/kb/v1/ingest/structure/batch-read"
_DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _batch(client: TestClient, ids: list[str], *, space_id: str = "sales", client_id: str = "n8n-1"):
    response = client.post(
        _BATCH,
        json={"space_id": space_id, "client_id": client_id, "markdown_object_ids": ids},
    )
    return {"status": response.status_code, "body": response.json()}


def test_convert_persists_markdown_object(client: TestClient, object_store: InMemoryObjectStore) -> None:
    object_id = _upload(
        client, filename="policy.md", content=b"# Policy\n\nBody", content_type="text/markdown"
    )
    report = _run(client, object_id, "docs/policy.md")["body"]
    mid = report["markdown_object_id"]
    assert len(mid) == 32
    stored = object_store.get("sales", "n8n-1", mid)
    assert stored is not None
    assert b"Policy" in stored


def test_ready_batch_returns_content_attachments_front_matter(client: TestClient) -> None:
    first = _upload(
        client, filename="a.md", content=b"# Alpha\n\nOne", content_type="text/markdown"
    )
    second = _upload(
        client, filename="b.md", content=b"# Beta\n\nTwo", content_type="text/markdown"
    )
    id_a = _run(client, first, "a.md")["body"]["markdown_object_id"]
    id_b = _run(client, second, "b.md")["body"]["markdown_object_id"]
    outcome = _batch(client, [id_a, id_b])
    assert outcome["status"] == 200
    docs = outcome["body"]["documents"]
    assert [d["markdown_object_id"] for d in docs] == [id_a, id_b]
    assert "Alpha" in docs[0]["markdown"]
    assert docs[0]["front_matter_draft"]["title"] == "Alpha"
    assert docs[0]["status"] == "ready"
    assert "attachments" in docs[0]
    assert outcome["body"]["excluded"] == []
    assert outcome["body"]["missing"] == []


def test_blocked_excluded_and_reported(client: TestClient) -> None:
    ready_id = _upload(
        client, filename="ok.md", content=b"# Ok", content_type="text/markdown"
    )
    ready_md = _run(client, ready_id, "ok.md")["body"]["markdown_object_id"]
    docx = _minimal_docx("Form", {"signature-scan.png": _bytes_len(67)})
    blocked_raw = _upload(client, filename="form.docx", content=docx, content_type=_DOCX_CT)
    blocked_md = _run(client, blocked_raw, "form.docx")["body"]["markdown_object_id"]
    outcome = _batch(client, [ready_md, blocked_md])
    assert outcome["status"] == 200
    assert [d["markdown_object_id"] for d in outcome["body"]["documents"]] == [ready_md]
    excluded = outcome["body"]["excluded"]
    assert len(excluded) == 1
    assert excluded[0]["markdown_object_id"] == blocked_md
    assert excluded[0]["reason"] == "blocked"
    assert excluded[0]["status"] == "blocked"


def test_missing_id_reported(client: TestClient) -> None:
    unknown = "0" * 32
    outcome = _batch(client, [unknown])
    assert outcome["status"] == 200
    assert outcome["body"]["documents"] == []
    assert outcome["body"]["missing"][0]["markdown_object_id"] == unknown
    assert outcome["body"]["missing"][0]["code"] == "OBJECT_NOT_FOUND"


def test_other_space_not_leaked(client: TestClient) -> None:
    object_id = _upload(
        client, filename="a.md", content=b"# A", content_type="text/markdown"
    )
    mid = _run(client, object_id, "a.md")["body"]["markdown_object_id"]
    outcome = _batch(client, [mid], space_id="other")
    assert outcome["body"]["documents"] == []
    assert outcome["body"]["missing"][0]["markdown_object_id"] == mid
    assert outcome["body"]["missing"][0]["code"] == "OBJECT_NOT_FOUND"


def test_other_client_not_leaked(client: TestClient) -> None:
    object_id = _upload(
        client, filename="a.md", content=b"# A", content_type="text/markdown"
    )
    mid = _run(client, object_id, "a.md")["body"]["markdown_object_id"]
    outcome = _batch(client, [mid], client_id="other-client")
    assert outcome["status"] == 200
    assert outcome["body"]["documents"] == []
    assert outcome["body"]["missing"][0]["markdown_object_id"] == mid
    assert outcome["body"]["missing"][0]["code"] == "OBJECT_NOT_FOUND"


def test_empty_batch_rejected(client: TestClient) -> None:
    outcome = _batch(client, [])
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "EMPTY_BATCH"


def test_duplicate_ids_read_once(client: TestClient) -> None:
    object_id = _upload(
        client, filename="a.md", content=b"# Once", content_type="text/markdown"
    )
    mid = _run(client, object_id, "a.md")["body"]["markdown_object_id"]
    docs = _batch(client, [mid, mid])["body"]["documents"]
    assert len(docs) == 1
    assert docs[0]["markdown_object_id"] == mid


def test_batch_too_large_rejected(client: TestClient) -> None:
    ids = [f"{index:032x}" for index in range(257)]
    outcome = _batch(client, ids)
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "BATCH_TOO_LARGE"


def test_empty_tenant_ids_rejected(client: TestClient) -> None:
    response = client.post(
        _BATCH,
        json={"space_id": "", "client_id": "n8n-1", "markdown_object_ids": ["0" * 32]},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_non_ready_status_excluded(client: TestClient) -> None:
    mid = "a" * 32
    client.app.state.converted_corpus.put(
        ConvertedDocument(
            markdown_object_id=mid,
            source_object_id="src",
            space_id="sales",
            client_id="n8n-1",
            source_path="pending.md",
            status="pending",
            markdown="pending body",
            attachments=[],
            front_matter_draft={"title": "pending"},
        )
    )
    outcome = _batch(client, [mid])
    assert outcome["status"] == 200
    assert outcome["body"]["documents"] == []
    assert outcome["body"]["excluded"][0]["markdown_object_id"] == mid
    assert outcome["body"]["excluded"][0]["reason"] == "not_ready"


def test_corpus_slash_ids_do_not_collide() -> None:
    corpus = ConvertedCorpus()
    first = ConvertedDocument(
        markdown_object_id="id1",
        source_object_id="s1",
        space_id="a/b",
        client_id="c",
        source_path="one.md",
        status="ready",
        markdown="one",
        attachments=[],
        front_matter_draft={},
    )
    second = ConvertedDocument(
        markdown_object_id="id1",
        source_object_id="s2",
        space_id="a",
        client_id="b/c",
        source_path="two.md",
        status="ready",
        markdown="two",
        attachments=[],
        front_matter_draft={},
    )
    corpus.put(first)
    corpus.put(second)
    assert corpus.get("a/b", "c", "id1") is first
    assert corpus.get("a", "b/c", "id1") is second
    assert corpus.get("a/b", "c", "id1").markdown == "one"


def test_ready_docx_includes_attachments(client: TestClient) -> None:
    docx = _minimal_docx("Body", {"figure.png": _bytes_len(600)})
    raw_id = _upload(client, filename="c.docx", content=docx, content_type=_DOCX_CT)
    mid = _run(client, raw_id, "c.docx")["body"]["markdown_object_id"]
    docs = _batch(client, [mid])["body"]["documents"]
    assert docs[0]["attachments"]
    assert docs[0]["attachments"][0]["sha256"]
    assert "attachment://" in docs[0]["markdown"]
