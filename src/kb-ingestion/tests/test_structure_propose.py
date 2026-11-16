"""KBI.2.2 tree and link proposal generation."""

from __future__ import annotations

from fastapi.testclient import TestClient
from kb_ingestion.app.services.converted_corpus import ConvertedDocument

from .test_convert import _minimal_docx, _run, _upload
from .test_media import _bytes_len
from .test_structure import _batch

_PROPOSE = "/api/kb/v1/ingest/structure/propose"
_DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _propose(client: TestClient, ids: list[str], *, space_id: str = "sales", client_id: str = "n8n-1"):
    response = client.post(
        _PROPOSE,
        json={"space_id": space_id, "client_id": client_id, "markdown_object_ids": ids},
    )
    return {"status": response.status_code, "body": response.json()}


def _convert_md(client: TestClient, filename: str, source_path: str, body: bytes) -> dict:
    object_id = _upload(client, filename=filename, content=body, content_type="text/markdown")
    report = _run(client, object_id, source_path)["body"]
    return report


def test_same_dir_related_proposes_parent_and_links(client: TestClient) -> None:
    first = _convert_md(client, "policy.md", "docs/policy.md", b"# Policy handbook\n\nRules")
    second = _convert_md(client, "annex.md", "docs/policy-annex.md", b"# Policy annex\n\nSee handbook")
    outcome = _propose(
        client, [first["markdown_object_id"], second["markdown_object_id"]]
    )
    assert outcome["status"] == 200
    nodes = outcome["body"]["nodes"]
    assert [n["markdown_object_id"] for n in nodes] == [
        first["markdown_object_id"],
        second["markdown_object_id"],
    ]
    by_path = {node["source_path"]: node for node in nodes}
    root = by_path["docs/policy-annex.md"]
    child = by_path["docs/policy.md"]
    assert root["parent_id"] is None
    assert child["parent_id"] == root["document_id"]
    assert child["parent_id"] != child["document_id"]
    linked = child["links"] + root["links"]
    assert any(link["target_document_id"] in {root["document_id"], child["document_id"]} for link in linked)
    assert all(link["relation"] == "references" for link in linked)
    assert child["confidence"] == "high"
    assert child["needs_attention"] is False
    assert root["confidence"] == "medium"
    assert root["needs_attention"] is False
    assert outcome["body"]["low_confidence_document_ids"] == []


def test_same_dir_unlinked_marks_attention(client: TestClient) -> None:
    first = _convert_md(client, "alpha.md", "kb/alpha.md", b"# Alpha\n\nOne")
    second = _convert_md(client, "zeta.md", "kb/zeta.md", b"# Zeta\n\nTwo")
    nodes = _propose(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]["nodes"]
    by_path = {node["source_path"]: node for node in nodes}
    root = by_path["kb/alpha.md"]
    child = by_path["kb/zeta.md"]
    assert root["parent_id"] is None
    assert child["parent_id"] == root["document_id"]
    nodes = [root, child]
    assert nodes[0]["links"] == []
    assert nodes[1]["links"] == []
    assert all(node["needs_attention"] for node in nodes)
    assert all(node["attention_reason"] == "unlinked sibling" for node in nodes)
    low_ids = [node["document_id"] for node in nodes if node["confidence"] == "low"]
    assert set(low_ids) == {nodes[0]["document_id"], nodes[1]["document_id"]}
    body = _propose(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]
    assert set(body["low_confidence_document_ids"]) == set(low_ids)


def test_singleton_ambiguous_isolation(client: TestClient) -> None:
    report = _convert_md(client, "solo.md", "notes/solo.md", b"# Solo\n\nOnly")
    body = _propose(client, [report["markdown_object_id"]])["body"]
    node = body["nodes"][0]
    assert node["parent_id"] is None
    assert node["confidence"] == "low"
    assert node["needs_attention"] is True
    assert node["attention_reason"] == "ambiguous isolation"
    assert body["low_confidence_document_ids"] == [node["document_id"]]


def test_blocked_excluded_from_nodes(client: TestClient) -> None:
    ready = _convert_md(client, "ok.md", "ok.md", b"# Ok")
    docx = _minimal_docx("Form", {"signature-scan.png": _bytes_len(67)})
    blocked_raw = _upload(client, filename="form.docx", content=docx, content_type=_DOCX_CT)
    blocked_md = _run(client, blocked_raw, "form.docx")["body"]["markdown_object_id"]
    body = _propose(client, [ready["markdown_object_id"], blocked_md])["body"]
    assert [n["markdown_object_id"] for n in body["nodes"]] == [ready["markdown_object_id"]]
    assert body["excluded"][0]["markdown_object_id"] == blocked_md
    assert body["excluded"][0]["reason"] == "blocked"


def test_missing_id_not_in_nodes(client: TestClient) -> None:
    unknown = "0" * 32
    body = _propose(client, [unknown])["body"]
    assert body["nodes"] == []
    assert body["missing"][0]["code"] == "OBJECT_NOT_FOUND"


def test_empty_propose_rejected(client: TestClient) -> None:
    outcome = _propose(client, [])
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "EMPTY_BATCH"


def test_no_self_parent_or_cycle(client: TestClient) -> None:
    first = _convert_md(client, "a.md", "tree/a.md", b"# Tree alpha")
    second = _convert_md(client, "b.md", "tree/b.md", b"# Tree beta")
    nodes = _propose(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]["nodes"]
    ids = {n["document_id"] for n in nodes}
    for node in nodes:
        assert node["parent_id"] != node["document_id"]
        if node["parent_id"] is not None:
            assert node["parent_id"] in ids
        for link in node["links"]:
            assert link["target_document_id"] != node["document_id"]
            assert link["target_document_id"] in ids


def test_title_in_body_link_without_token_overlap(client: TestClient) -> None:
    root = _convert_md(client, "guide.md", "dir/aaa.md", b"# Quartz manual\n\nIntro")
    child = _convert_md(
        client,
        "note.md",
        "dir/zzz.md",
        b"# Ember notes\n\nSee Quartz manual for setup",
    )
    body = _propose(client, [root["markdown_object_id"], child["markdown_object_id"]])["body"]
    by_path = {node["source_path"]: node for node in body["nodes"]}
    lex_root = by_path["dir/aaa.md"]
    lex_child = by_path["dir/zzz.md"]
    assert lex_root["parent_id"] is None
    assert lex_child["parent_id"] == lex_root["document_id"]
    assert lex_child["links"] == [
        {"target_document_id": lex_root["document_id"], "relation": "references"}
    ]
    assert lex_root["confidence"] == "medium"
    assert lex_child["confidence"] == "high"
    assert body["low_confidence_document_ids"] == []


def test_two_directories_have_independent_roots(client: TestClient) -> None:
    docs_a = _convert_md(client, "a.md", "docs/a.md", b"# Docs alpha")
    docs_b = _convert_md(client, "b.md", "docs/b.md", b"# Docs beta")
    notes = _convert_md(client, "n.md", "notes/n.md", b"# Notes solo")
    body = _propose(
        client,
        [docs_a["markdown_object_id"], docs_b["markdown_object_id"], notes["markdown_object_id"]],
    )["body"]
    by_path = {node["source_path"]: node for node in body["nodes"]}
    assert by_path["docs/a.md"]["parent_id"] is None
    assert by_path["docs/b.md"]["parent_id"] == by_path["docs/a.md"]["document_id"]
    assert by_path["notes/n.md"]["parent_id"] is None
    assert by_path["notes/n.md"]["confidence"] == "low"
    assert by_path["notes/n.md"]["attention_reason"] == "ambiguous isolation"


def test_not_ready_excluded_from_propose(client: TestClient) -> None:
    mid = "b" * 32
    client.app.state.converted_corpus.put(
        ConvertedDocument(
            markdown_object_id=mid,
            source_object_id="src",
            space_id="sales",
            client_id="n8n-1",
            source_path="pending.md",
            status="pending",
            markdown="pending",
            attachments=[],
            front_matter_draft={"id": "11111111-1111-1111-1111-111111111111", "title": "P"},
        )
    )
    body = _propose(client, [mid])["body"]
    assert body["nodes"] == []
    assert body["excluded"][0]["reason"] == "not_ready"


def test_propose_batch_too_large(client: TestClient) -> None:
    ids = [f"{index:032x}" for index in range(257)]
    outcome = _propose(client, ids)
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "BATCH_TOO_LARGE"


def test_propose_missing_front_matter_id(client: TestClient) -> None:
    mid = "c" * 32
    client.app.state.converted_corpus.put(
        ConvertedDocument(
            markdown_object_id=mid,
            source_object_id="src",
            space_id="sales",
            client_id="n8n-1",
            source_path="broken.md",
            status="ready",
            markdown="x",
            attachments=[],
            front_matter_draft={"title": "Broken"},
        )
    )
    outcome = _propose(client, [mid])
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "FRONT_MATTER_INVALID"


def test_propose_is_deterministic(client: TestClient) -> None:
    first = _convert_md(client, "p.md", "docs/p.md", b"# Policy one")
    second = _convert_md(client, "q.md", "docs/q.md", b"# Policy two")
    ids = [first["markdown_object_id"], second["markdown_object_id"]]
    first_body = _propose(client, ids)["body"]
    second_body = _propose(client, ids)["body"]
    assert first_body == second_body


def test_propose_does_not_mutate_corpus(client: TestClient) -> None:
    report = _convert_md(client, "keep.md", "keep.md", b"# Keep\n\nBody")
    _propose(client, [report["markdown_object_id"]])
    original = _batch(client, [report["markdown_object_id"]])["body"]["documents"][0]
    assert original["front_matter_draft"]["parent_id"] is None
    assert original["front_matter_draft"]["links"] == []
