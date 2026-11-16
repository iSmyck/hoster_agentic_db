"""KBI.2.4 submit approved structure proposals to GO."""

from __future__ import annotations

from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.go_client import StubGOClient

from .test_structure_propose import _convert_md
from .test_structure_review import _create

_PROPOSALS = "/api/kb/v1/ingest/structure/proposals"
_SUBMIT_BODY = {
    "base_sha": "b" * 40,
    "author_stable_id": "author-1",
    "requester_stable_id": "requester-1",
}


def _approve(client: TestClient, proposal_id: str) -> dict:
    response = client.post(f"{_PROPOSALS}/{proposal_id}/approve")
    return response.json()


def _submit(client: TestClient, proposal_id: str, body: dict | None = None):
    response = client.post(f"{_PROPOSALS}/{proposal_id}/submit", json=body or _SUBMIT_BODY)
    return {"status": response.status_code, "body": response.json()}


def test_approved_submit_one_go_record_per_document(client: TestClient) -> None:
    first = _convert_md(client, "a.md", "docs/a.md", b"# Policy one\n\nA")
    second = _convert_md(client, "b.md", "docs/b.md", b"# Policy two\n\nB")
    created = _create(client, [first["markdown_object_id"], second["markdown_object_id"]])["body"]
    _approve(client, created["proposal_id"])
    outcome = _submit(client, created["proposal_id"])
    assert outcome["status"] == 200
    submissions = outcome["body"]["submissions"]
    assert len(submissions) == 2
    assert {item["document_id"] for item in submissions} == {node["document_id"] for node in created["nodes"]}
    for item in submissions:
        assert item["base_sha"] == "b" * 40
        assert item["author_stable_id"] == "author-1"
        assert item["requester_stable_id"] == "requester-1"
        assert len(item["proposal_sha"]) == 40
    go_client = client.app.state.go_client
    assert isinstance(go_client, StubGOClient)
    assert len(go_client.calls) == 2
    nodes_by_id = {node["document_id"]: node for node in created["nodes"]}
    for index, payload in enumerate(go_client.calls):
        document_id = payload["proposal_data"]["document_id"]
        node = nodes_by_id[document_id]
        assert payload["base_sha"] == "b" * 40
        assert payload["target_branch"] == "main"
        assert payload["idempotency_key"] == f"{created['proposal_id']}:{document_id}"
        assert payload["proposal_data"]["author_stable_id"] == "author-1"
        assert payload["proposal_data"]["requester_stable_id"] == "requester-1"
        assert payload["proposal_data"]["markdown_object_id"] == node["markdown_object_id"]
        assert payload["proposal_data"]["front_matter"]["schema_version"] == "document-front-matter-v2"
        assert payload["proposal_data"]["front_matter"]["parent_id"] == node["parent_id"]
        assert submissions[index]["proposal_sha"] == payload["proposal_sha"]
        assert submissions[index]["go_proposal_id"] == f"00000000-0000-0000-0000-{index + 1:012d}"
        assert submissions[index]["document_id"] == document_id


def test_submit_not_approved_rejected(client: TestClient) -> None:
    report = _convert_md(client, "a.md", "a.md", b"# Alpha")
    created = _create(client, [report["markdown_object_id"]])["body"]
    outcome = _submit(client, created["proposal_id"])
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "NOT_APPROVED"
    assert client.app.state.go_client.calls == []


def test_submit_invalid_front_matter_rejected(client: TestClient) -> None:
    report = _convert_md(client, "a.md", "a.md", b"# Alpha")
    created = _create(client, [report["markdown_object_id"]])["body"]
    _approve(client, created["proposal_id"])
    record = client.app.state.structure_proposals.get(created["proposal_id"])
    record.nodes[0].front_matter_draft["access"] = "everyone"
    outcome = _submit(client, created["proposal_id"])
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "FRONT_MATTER_INVALID"
    assert client.app.state.go_client.calls == []


def test_submit_missing_proposal(client: TestClient) -> None:
    outcome = _submit(client, "0" * 32)
    assert outcome["status"] == 404
    assert outcome["body"]["detail"]["code"] == "NOT_FOUND"


def test_submit_invalid_merged_parent_rejected(client: TestClient) -> None:
    report = _convert_md(client, "a.md", "a.md", b"# Alpha")
    created = _create(client, [report["markdown_object_id"]])["body"]
    _approve(client, created["proposal_id"])
    record = client.app.state.structure_proposals.get(created["proposal_id"])
    record.nodes[0].parent_id = "not-a-uuid"
    outcome = _submit(client, created["proposal_id"])
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "FRONT_MATTER_INVALID"
    assert client.app.state.go_client.calls == []


def test_submit_empty_nodes_rejected(client: TestClient) -> None:
    created = _create(client, ["0" * 32])["body"]
    record = client.app.state.structure_proposals.get(created["proposal_id"])
    record.status = "approved"
    outcome = _submit(client, created["proposal_id"])
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "EMPTY_PROPOSAL"
    assert client.app.state.go_client.calls == []


def test_submit_go_failure(client: TestClient) -> None:
    report = _convert_md(client, "a.md", "a.md", b"# Alpha")
    created = _create(client, [report["markdown_object_id"]])["body"]
    _approve(client, created["proposal_id"])
    client.app.state.go_client.fail_message = "upstream down"
    outcome = _submit(client, created["proposal_id"])
    assert outcome["status"] == 502
    assert outcome["body"]["detail"]["code"] == "GO_SUBMIT_FAILED"
