"""Request/response models for structure batch-read, propose, review, and submit."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .convert import AttachmentManifestEntry


class BatchReadRequest(BaseModel):
    space_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    markdown_object_ids: list[str]


class BatchReadDocument(BaseModel):
    markdown_object_id: str
    source_path: str
    status: Literal["ready"]
    markdown: str
    attachments: list[AttachmentManifestEntry]
    front_matter_draft: dict[str, Any]


class BatchReadExcluded(BaseModel):
    markdown_object_id: str
    status: str
    reason: Literal["blocked", "not_ready"]


class BatchReadMissing(BaseModel):
    markdown_object_id: str
    code: Literal["OBJECT_NOT_FOUND"] = "OBJECT_NOT_FOUND"


class BatchReadReport(BaseModel):
    documents: list[BatchReadDocument]
    excluded: list[BatchReadExcluded]
    missing: list[BatchReadMissing]


class ProposedLink(BaseModel):
    target_document_id: str
    relation: Literal["references"] = "references"


class StructureNode(BaseModel):
    markdown_object_id: str
    document_id: str
    source_path: str
    title: str
    parent_id: str | None
    links: list[ProposedLink]
    confidence: Literal["high", "medium", "low"]
    needs_attention: bool
    attention_reason: str | None = None
    front_matter_draft: dict[str, Any]


class StructureProposalReport(BaseModel):
    nodes: list[StructureNode]
    excluded: list[BatchReadExcluded]
    missing: list[BatchReadMissing]
    low_confidence_document_ids: list[str]


class TreePreviewNode(BaseModel):
    document_id: str
    title: str
    parent_id: str | None
    children: list[str]
    needs_attention: bool


class LinkEdge(BaseModel):
    source_document_id: str
    target_document_id: str
    relation: Literal["references"] = "references"


class StructureNodeEdit(BaseModel):
    document_id: str
    parent_id: str | None = None
    links: list[ProposedLink] | None = None


class StructureProposalEdit(BaseModel):
    nodes: list[StructureNodeEdit] = Field(min_length=1)


class StructureProposalView(BaseModel):
    proposal_id: str
    space_id: str
    client_id: str
    status: Literal["in_review", "approved"]
    version: int
    tree: list[TreePreviewNode]
    links_graph: list[LinkEdge]
    nodes: list[StructureNode]
    excluded: list[BatchReadExcluded]
    missing: list[BatchReadMissing]
    low_confidence_document_ids: list[str]


class StructureSubmitRequest(BaseModel):
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    author_stable_id: str = Field(min_length=1)
    requester_stable_id: str = Field(min_length=1)
    target_branch: str = "main"


class StructureSubmission(BaseModel):
    document_id: str
    go_proposal_id: str
    proposal_sha: str
    base_sha: str
    author_stable_id: str
    requester_stable_id: str


class StructureSubmitReport(BaseModel):
    proposal_id: str
    submissions: list[StructureSubmission]
