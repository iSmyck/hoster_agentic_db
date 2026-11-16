"""In-memory StructureProposal persistence, review, and GO submit."""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..adapters.go_client import GOClient, GOClientError, StubGOClient
from ..schemas.structure import (
    BatchReadExcluded,
    BatchReadMissing,
    BatchReadRequest,
    LinkEdge,
    StructureNode,
    StructureProposalEdit,
    StructureProposalReport,
    StructureProposalView,
    StructureSubmission,
    StructureSubmitReport,
    StructureSubmitRequest,
    TreePreviewNode,
)
from ..validators.front_matter import FrontMatterError, validate_front_matter_draft
from .agent_structurer import AgentStructurer, StructureError


@dataclass
class StructureProposalRecord:
    proposal_id: str
    space_id: str
    client_id: str
    status: str
    version: int
    nodes: list[StructureNode]
    excluded: list[BatchReadExcluded]
    missing: list[BatchReadMissing]
    versions: list[list[StructureNode]] = field(default_factory=list)


class StructureProposalStore:
    def __init__(self) -> None:
        self._items: dict[str, StructureProposalRecord] = {}

    def put(self, record: StructureProposalRecord) -> None:
        self._items[record.proposal_id] = record

    def get(self, proposal_id: str) -> StructureProposalRecord | None:
        return self._items.get(proposal_id)


class StructureReviewService:
    def __init__(
        self,
        structurer: AgentStructurer,
        store: StructureProposalStore,
        go_client: GOClient | None = None,
    ) -> None:
        self._structurer = structurer
        self._store = store
        self._go_client = go_client or StubGOClient()

    def create(self, request: BatchReadRequest) -> StructureProposalView:
        generated = self._structurer.propose_tree(request)
        proposal_id = uuid.uuid4().hex
        nodes = [node.model_copy(deep=True) for node in generated.nodes]
        if nodes:
            _validate_structure(nodes)
        record = StructureProposalRecord(
            proposal_id=proposal_id,
            space_id=request.space_id,
            client_id=request.client_id,
            status="in_review",
            version=1,
            nodes=nodes,
            excluded=list(generated.excluded),
            missing=list(generated.missing),
            versions=[copy.deepcopy(nodes)],
        )
        self._store.put(record)
        return _view(record, generated)

    def get(self, proposal_id: str) -> StructureProposalView:
        return _view(self._require(proposal_id))

    def patch(self, proposal_id: str, edit: StructureProposalEdit) -> StructureProposalView:
        record = self._require(proposal_id)
        seen_edits: set[str] = set()
        by_id = {node.document_id: node.model_copy(deep=True) for node in record.nodes}
        applied = False
        for change in edit.nodes:
            if change.document_id in seen_edits:
                raise StructureError("STRUCTURE_INVALID", "duplicate document_id in patch")
            seen_edits.add(change.document_id)
            current = by_id.get(change.document_id)
            if current is None:
                raise StructureError("STRUCTURE_INVALID", f"unknown document_id {change.document_id}")
            fields = change.model_fields_set
            if not ({"parent_id", "links"} & fields):
                continue
            applied = True
            if "parent_id" in fields:
                current.parent_id = change.parent_id
            if "links" in fields:
                current.links = list(change.links or [])
            by_id[change.document_id] = current
        if not applied:
            raise StructureError("STRUCTURE_INVALID", "patch must set parent_id or links")
        updated = [by_id[node.document_id] for node in record.nodes]
        _validate_structure(updated)
        record.nodes = updated
        record.version += 1
        record.status = "in_review"
        record.versions.append(copy.deepcopy(updated))
        return _view(record)

    def approve(self, proposal_id: str) -> StructureProposalView:
        record = self._require(proposal_id)
        if not record.nodes:
            raise StructureError("EMPTY_PROPOSAL", "cannot approve a proposal with no documents")
        record.status = "approved"
        return _view(record)

    def submit(self, proposal_id: str, request: StructureSubmitRequest) -> StructureSubmitReport:
        record = self._require(proposal_id)
        if record.status != "approved":
            raise StructureError("NOT_APPROVED", "structure proposal is not approved")
        if not record.nodes:
            raise StructureError("EMPTY_PROPOSAL", "cannot submit a proposal with no documents")
        merged: list[tuple[StructureNode, dict[str, Any]]] = []
        for node in record.nodes:
            draft = _merged_front_matter(node)
            try:
                validate_front_matter_draft(draft)
            except FrontMatterError as exc:
                raise StructureError(exc.code, exc.message) from exc
            merged.append((node, draft))
        submissions: list[StructureSubmission] = []
        for node, draft in merged:
            go_payload = _go_payload(record, node, draft, request)
            try:
                created = self._go_client.submit_proposal(go_payload)
            except GOClientError as exc:
                raise StructureError("GO_SUBMIT_FAILED", exc.message, http_status=502) from exc
            go_id = created.get("id") if isinstance(created, dict) else None
            if not go_id:
                raise StructureError("GO_SUBMIT_FAILED", "GO proposal response missing id", http_status=502)
            submissions.append(
                StructureSubmission(
                    document_id=node.document_id,
                    go_proposal_id=str(go_id),
                    proposal_sha=go_payload["proposal_sha"],
                    base_sha=request.base_sha,
                    author_stable_id=request.author_stable_id,
                    requester_stable_id=request.requester_stable_id,
                )
            )
        return StructureSubmitReport(proposal_id=record.proposal_id, submissions=submissions)

    def _require(self, proposal_id: str) -> StructureProposalRecord:
        record = self._store.get(proposal_id)
        if record is None:
            raise StructureError("NOT_FOUND", "structure proposal not found", http_status=404)
        return record


def _view(
    record: StructureProposalRecord, generated: StructureProposalReport | None = None
) -> StructureProposalView:
    low_ids = [node.document_id for node in record.nodes if node.confidence == "low"]
    if generated is not None and record.version == 1:
        low_ids = list(generated.low_confidence_document_ids)
    return StructureProposalView(
        proposal_id=record.proposal_id,
        space_id=record.space_id,
        client_id=record.client_id,
        status=record.status,  # type: ignore[arg-type]
        version=record.version,
        tree=_tree_preview(record.nodes),
        links_graph=_links_graph(record.nodes),
        nodes=record.nodes,
        excluded=record.excluded,
        missing=record.missing,
        low_confidence_document_ids=low_ids,
    )


def _tree_preview(nodes: list[StructureNode]) -> list[TreePreviewNode]:
    children: dict[str, list[str]] = {node.document_id: [] for node in nodes}
    for node in nodes:
        if node.parent_id and node.parent_id in children:
            children[node.parent_id].append(node.document_id)
    return [
        TreePreviewNode(
            document_id=node.document_id,
            title=node.title,
            parent_id=node.parent_id,
            children=children[node.document_id],
            needs_attention=node.needs_attention,
        )
        for node in nodes
    ]


def _links_graph(nodes: list[StructureNode]) -> list[LinkEdge]:
    edges: list[LinkEdge] = []
    for node in nodes:
        for link in node.links:
            edges.append(
                LinkEdge(
                    source_document_id=node.document_id,
                    target_document_id=link.target_document_id,
                    relation=link.relation,
                )
            )
    return edges


def _validate_structure(nodes: list[StructureNode]) -> None:
    by_id = {node.document_id: node for node in nodes}
    if len(by_id) != len(nodes):
        raise StructureError("STRUCTURE_INVALID", "duplicate document_id in proposal")
    for node in nodes:
        if node.parent_id == node.document_id:
            raise StructureError("STRUCTURE_INVALID", "self-parent is not allowed")
        if node.parent_id is not None and node.parent_id not in by_id:
            raise StructureError("STRUCTURE_INVALID", "parent_id is outside the proposal")
        seen_targets: set[str] = set()
        for link in node.links:
            if link.target_document_id == node.document_id:
                raise StructureError("STRUCTURE_INVALID", "self-link is not allowed")
            if link.target_document_id not in by_id:
                raise StructureError("STRUCTURE_INVALID", "link target is outside the proposal")
            if link.target_document_id in seen_targets:
                raise StructureError("STRUCTURE_INVALID", "duplicate link target")
            seen_targets.add(link.target_document_id)
    visiting: set[str] = set()
    seen: set[str] = set()

    def walk(document_id: str) -> None:
        if document_id in visiting:
            raise StructureError("STRUCTURE_INVALID", "parent cycle is not allowed")
        if document_id in seen:
            return
        visiting.add(document_id)
        parent_id = by_id[document_id].parent_id
        if parent_id is not None:
            walk(parent_id)
        visiting.remove(document_id)
        seen.add(document_id)

    for node in nodes:
        walk(node.document_id)


def _merged_front_matter(node: StructureNode) -> dict[str, Any]:
    draft = copy.deepcopy(dict(node.front_matter_draft))
    draft["parent_id"] = node.parent_id
    draft["links"] = [link.model_dump() for link in node.links]
    return draft


def _go_payload(
    record: StructureProposalRecord,
    node: StructureNode,
    front_matter: dict[str, Any],
    request: StructureSubmitRequest,
) -> dict[str, Any]:
    proposal_data = {
        "author_stable_id": request.author_stable_id,
        "requester_stable_id": request.requester_stable_id,
        "actor_type": "human",
        "document_id": node.document_id,
        "markdown_object_id": node.markdown_object_id,
        "front_matter": front_matter,
        "rationale": "Approved structure proposal",
    }
    canonical = json.dumps(
        {
            "space_id": record.space_id,
            "document_id": node.document_id,
            "markdown_object_id": node.markdown_object_id,
            "base_sha": request.base_sha,
            "author_stable_id": request.author_stable_id,
            "requester_stable_id": request.requester_stable_id,
            "front_matter": front_matter,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    proposal_sha = hashlib.sha1(canonical.encode("utf-8"), usedforsecurity=False).hexdigest()
    return {
        "space_id": record.space_id,
        "proposal_sha": proposal_sha,
        "base_sha": request.base_sha,
        "target_branch": request.target_branch,
        "idempotency_key": f"{record.proposal_id}:{node.document_id}",
        "proposal_data": proposal_data,
    }
