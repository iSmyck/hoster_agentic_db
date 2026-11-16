"""KBI.2.3 StructureProposal review persistence and versioned edits."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .test_convert import _minimal_docx, _run, _upload
from .test_media import _bytes_len
from .test_structure_propose import _convert_md

_PROPOSALS = "/api/kb/v1/ingest/structure/proposals"


def _create(client: TestClient, ids: list[str]):
    response = client.post(
        _PROPOSALS,
        json={"space_id": "sales", "client_id": "n8n-1", "markdown_object_ids": ids},
    )
    return {"status": response.status_code, "body": response.json()}


def test_create_and_get_preview(client: TestClient) -> None:
    first = _convert_md(client, "policy.md", "docs/policy.md", b"# Policy handbook\n\nRules")
    second = _convert_md(client, "annex.md", "docs/policy-annex.md", b"# Policy annex\n\nSee handbook")
    created = _create(client, [first["markdown_object_id"], second["markdown_object_id"]])
    assert created["status"] == 201
    body = created["body"]
    assert len(body["proposal_id"]) == 32
    assert body["version"] == 1
    assert body["status"] == "in_review"
    assert body["tree"]
    assert body["links_graph"]
    assert all("front_matter_draft" in node for node in body["nodes"])
    fetched = client.get(f"{_PROPOSALS}/{body['proposal_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["proposal_id"] == body["proposal_id"]
    assert fetched.json()["tree"] == body["tree"]
    assert fetched.json()["links_graph"] == body["links_graph"]
    for node in body["nodes"]:
        assert node["front_matter_draft"]["parent_id"] is None
        preview = next(item for item in body["tree"] if item["document_id"] == node["document_id"])
        assert preview["parent_id"] == node["parent_id"]
        if node["parent_id"]:
            parent_preview = next(item for item in body["tree"] if item["document_id"] == node["parent_id"])
            assert node["document_id"] in parent_preview["children"]


def test_patch_parent_versions(client: TestClient) -> None:
    first = _convert_md(client, "a.md", "kb/a.md", b"# Alpha\n\nOne")
    second = _convert_md(client, "z.md", "kb/z.md", b"# Zeta\n\nTwo")
    created = _create(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]
    child = next(node for node in created["nodes"] if node["parent_id"] is not None)
    patched = client.patch(
        f"{_PROPOSALS}/{created['proposal_id']}",
        json={"nodes": [{"document_id": child["document_id"], "parent_id": None}]},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["version"] == 2
    updated = next(node for node in body["nodes"] if node["document_id"] == child["document_id"])
    assert updated["parent_id"] is None
    assert updated["front_matter_draft"]["parent_id"] is None
    tree_child = next(item for item in body["tree"] if item["document_id"] == child["document_id"])
    assert tree_child["parent_id"] is None
    parent_preview = next(item for item in body["tree"] if item["document_id"] == child["parent_id"])
    assert child["document_id"] not in parent_preview["children"]
    original = client.get(f"{_PROPOSALS}/{created['proposal_id']}").json()
    assert original["version"] == 2


def test_patch_cycle_rejected(client: TestClient) -> None:
    first = _convert_md(client, "a.md", "t/a.md", b"# Tree alpha")
    second = _convert_md(client, "b.md", "t/b.md", b"# Tree beta")
    created = _create(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]
    by_path = {node["source_path"]: node for node in created["nodes"]}
    root = by_path["t/a.md"]
    child = by_path["t/b.md"]
    response = client.patch(
        f"{_PROPOSALS}/{created['proposal_id']}",
        json={
            "nodes": [
                {"document_id": root["document_id"], "parent_id": child["document_id"]},
            ]
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "STRUCTURE_INVALID"
    assert client.get(f"{_PROPOSALS}/{created['proposal_id']}").json()["version"] == 1


def test_patch_unknown_document(client: TestClient) -> None:
    report = _convert_md(client, "solo.md", "notes/solo.md", b"# Solo")
    created = _create(client, [report["markdown_object_id"]])["body"]
    response = client.patch(
        f"{_PROPOSALS}/{created['proposal_id']}",
        json={"nodes": [{"document_id": "00000000-0000-0000-0000-000000000000", "parent_id": None}]},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "STRUCTURE_INVALID"


def test_get_missing_proposal(client: TestClient) -> None:
    response = client.get(f"{_PROPOSALS}/{'0' * 32}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


def test_approve_and_patch_reopens_review(client: TestClient) -> None:
    first = _convert_md(client, "a.md", "x/a.md", b"# Policy one")
    second = _convert_md(client, "b.md", "x/b.md", b"# Policy two")
    created = _create(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]
    approved = client.post(f"{_PROPOSALS}/{created['proposal_id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    again = client.post(f"{_PROPOSALS}/{created['proposal_id']}/approve")
    assert again.json()["status"] == "approved"
    child = next(node for node in created["nodes"] if node["parent_id"] is not None)
    prior_parent = child["parent_id"]
    patched = client.patch(
        f"{_PROPOSALS}/{created['proposal_id']}",
        json={
            "nodes": [
                {
                    "document_id": child["document_id"],
                    "links": [{"target_document_id": child["parent_id"], "relation": "references"}],
                }
            ]
        },
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["version"] == 2
    assert body["status"] == "in_review"
    updated = next(node for node in body["nodes"] if node["document_id"] == child["document_id"])
    assert updated["parent_id"] == prior_parent
    assert updated["front_matter_draft"]["links"] == []
    assert {
        "source_document_id": child["document_id"],
        "target_document_id": prior_parent,
        "relation": "references",
    } in body["links_graph"]


def test_approve_empty_nodes_rejected(client: TestClient) -> None:
    created = _create(client, ["0" * 32])["body"]
    assert created["nodes"] == []
    response = client.post(f"{_PROPOSALS}/{created['proposal_id']}/approve")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "EMPTY_PROPOSAL"


def test_patch_self_parent_rejected(client: TestClient) -> None:
    report = _convert_md(client, "solo.md", "notes/solo.md", b"# Solo")
    created = _create(client, [report["markdown_object_id"]])["body"]
    node = created["nodes"][0]
    response = client.patch(
        f"{_PROPOSALS}/{created['proposal_id']}",
        json={"nodes": [{"document_id": node["document_id"], "parent_id": node["document_id"]}]},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "STRUCTURE_INVALID"
    assert client.get(f"{_PROPOSALS}/{created['proposal_id']}").json()["version"] == 1


def test_patch_self_link_and_duplicate_rejected(client: TestClient) -> None:
    first = _convert_md(client, "a.md", "p/a.md", b"# Policy one")
    second = _convert_md(client, "b.md", "p/b.md", b"# Policy two")
    created = _create(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]
    child = next(node for node in created["nodes"] if node["parent_id"] is not None)
    self_link = client.patch(
        f"{_PROPOSALS}/{created['proposal_id']}",
        json={
            "nodes": [
                {
                    "document_id": child["document_id"],
                    "links": [{"target_document_id": child["document_id"], "relation": "references"}],
                }
            ]
        },
    )
    assert self_link.status_code == 400
    duplicate = client.patch(
        f"{_PROPOSALS}/{created['proposal_id']}",
        json={
            "nodes": [
                {
                    "document_id": child["document_id"],
                    "links": [
                        {"target_document_id": child["parent_id"], "relation": "references"},
                        {"target_document_id": child["parent_id"], "relation": "references"},
                    ],
                }
            ]
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"]["code"] == "STRUCTURE_INVALID"


def test_create_reports_excluded_and_missing(client: TestClient) -> None:
    ready = _convert_md(client, "ok.md", "ok.md", b"# Ok")
    docx = _minimal_docx("Form", {"signature-scan.png": _bytes_len(67)})
    blocked_raw = _upload(
        client,
        filename="form.docx",
        content=docx,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    blocked_md = _run(client, blocked_raw, "form.docx")["body"]["markdown_object_id"]
    unknown = "0" * 32
    created = _create(client, [ready["markdown_object_id"], blocked_md, unknown])["body"]
    assert [node["markdown_object_id"] for node in created["nodes"]] == [ready["markdown_object_id"]]
    assert created["excluded"][0]["markdown_object_id"] == blocked_md
    assert created["missing"][0]["markdown_object_id"] == unknown
    fetched = client.get(f"{_PROPOSALS}/{created['proposal_id']}").json()
    assert fetched["excluded"] == created["excluded"]
    assert fetched["missing"] == created["missing"]


def test_create_does_not_mutate_convert_front_matter(client: TestClient) -> None:
    report = _convert_md(client, "keep.md", "keep.md", b"# Keep\n\nBody")
    created = _create(client, [report["markdown_object_id"]])["body"]
    assert created["nodes"][0]["front_matter_draft"]["parent_id"] is None
    assert created["nodes"][0]["front_matter_draft"]["links"] == []
    assert created["nodes"][0]["parent_id"] is None
