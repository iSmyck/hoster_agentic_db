"""Batch reader and tree/link proposer for converted Markdown."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from ..schemas.structure import (
    BatchReadDocument,
    BatchReadExcluded,
    BatchReadMissing,
    BatchReadReport,
    BatchReadRequest,
    ProposedLink,
    StructureNode,
    StructureProposalReport,
)
from .converted_corpus import ConvertedCorpus

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}")


class StructureError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class AgentStructurer:
    def __init__(self, corpus: ConvertedCorpus) -> None:
        self._corpus = corpus

    def batch_read(self, request: BatchReadRequest) -> BatchReadReport:
        ids = request.markdown_object_ids
        if not ids:
            raise StructureError("EMPTY_BATCH", "markdown_object_ids must not be empty")
        if len(ids) > 256:
            raise StructureError("BATCH_TOO_LARGE", "markdown_object_ids must contain at most 256 items")
        seen: set[str] = set()
        unique_ids: list[str] = []
        for item in ids:
            if item in seen:
                continue
            seen.add(item)
            unique_ids.append(item)

        documents: list[BatchReadDocument] = []
        excluded: list[BatchReadExcluded] = []
        missing: list[BatchReadMissing] = []
        for markdown_object_id in unique_ids:
            record = self._corpus.get(request.space_id, request.client_id, markdown_object_id)
            if record is None:
                missing.append(BatchReadMissing(markdown_object_id=markdown_object_id))
                continue
            if record.status == "blocked":
                excluded.append(
                    BatchReadExcluded(
                        markdown_object_id=markdown_object_id,
                        status=record.status,
                        reason="blocked",
                    )
                )
                continue
            if record.status != "ready":
                excluded.append(
                    BatchReadExcluded(
                        markdown_object_id=markdown_object_id,
                        status=record.status,
                        reason="not_ready",
                    )
                )
                continue
            documents.append(
                BatchReadDocument(
                    markdown_object_id=record.markdown_object_id,
                    source_path=record.source_path,
                    status="ready",
                    markdown=record.markdown,
                    attachments=record.attachments,
                    front_matter_draft=record.front_matter_draft,
                )
            )
        return BatchReadReport(documents=documents, excluded=excluded, missing=missing)

    def propose_tree(self, request: BatchReadRequest) -> StructureProposalReport:
        batch = self.batch_read(request)
        nodes = _propose_nodes(batch.documents)
        low_ids = [node.document_id for node in nodes if node.confidence == "low"]
        return StructureProposalReport(
            nodes=nodes,
            excluded=batch.excluded,
            missing=batch.missing,
            low_confidence_document_ids=low_ids,
        )


def _document_id(document: BatchReadDocument) -> str:
    value = document.front_matter_draft.get("id")
    if not value:
        raise StructureError("FRONT_MATTER_INVALID", "front_matter_draft.id is required")
    return str(value)


def _display_title(document: BatchReadDocument) -> str:
    title = str(document.front_matter_draft.get("title") or "").strip()
    return title or Path(document.source_path).stem or "untitled"


def _propose_nodes(documents: list[BatchReadDocument]) -> list[StructureNode]:
    if not documents:
        return []
    groups: dict[str, list[BatchReadDocument]] = defaultdict(list)
    for document in documents:
        parent_dir = Path(document.source_path).parent.as_posix()
        groups[parent_dir].append(document)

    parent_by_mid: dict[str, str | None] = {}
    group_size_by_mid: dict[str, int] = {}
    group_key_by_mid: dict[str, str] = {}
    for key, members in groups.items():
        ordered = sorted(members, key=lambda item: item.source_path)
        root_id = _document_id(ordered[0])
        for index, member in enumerate(ordered):
            member_id = _document_id(member)
            if index == 0 or member_id == root_id:
                parent_by_mid[member.markdown_object_id] = None
            else:
                parent_by_mid[member.markdown_object_id] = root_id
            group_size_by_mid[member.markdown_object_id] = len(ordered)
            group_key_by_mid[member.markdown_object_id] = key

    links_by_mid = _propose_links(documents)
    group_has_links = {
        key: any(links_by_mid[member.markdown_object_id] for member in members)
        for key, members in groups.items()
    }
    nodes: list[StructureNode] = []
    for document in documents:
        document_id = _document_id(document)
        title = _display_title(document)
        links = links_by_mid.get(document.markdown_object_id, [])
        group_size = group_size_by_mid[document.markdown_object_id]
        parent_id = parent_by_mid[document.markdown_object_id]
        group_key = group_key_by_mid[document.markdown_object_id]
        confidence, needs_attention, reason = _confidence(
            group_size=group_size,
            is_group_root=parent_id is None,
            has_own_links=bool(links),
            group_has_links=group_has_links[group_key],
        )
        nodes.append(
            StructureNode(
                markdown_object_id=document.markdown_object_id,
                document_id=document_id,
                source_path=document.source_path,
                title=title,
                parent_id=parent_id,
                links=links,
                confidence=confidence,
                needs_attention=needs_attention,
                attention_reason=reason,
                front_matter_draft=document.front_matter_draft,
            )
        )
    return nodes


def _propose_links(documents: list[BatchReadDocument]) -> dict[str, list[ProposedLink]]:
    titles: dict[str, str] = {}
    tokens: dict[str, set[str]] = {}
    for document in documents:
        title = _display_title(document)
        titles[document.markdown_object_id] = title
        tokens[document.markdown_object_id] = set(_TOKEN_RE.findall(title.lower()))

    result: dict[str, list[ProposedLink]] = {document.markdown_object_id: [] for document in documents}
    seen: dict[str, set[str]] = {document.markdown_object_id: set() for document in documents}
    for source in documents:
        source_mid = source.markdown_object_id
        source_id = _document_id(source)
        body = source.markdown.lower()
        for target in documents:
            if target.markdown_object_id == source_mid:
                continue
            target_id = _document_id(target)
            if target_id == source_id or target_id in seen[source_mid]:
                continue
            target_title = titles[target.markdown_object_id]
            related = bool(tokens[source_mid] & tokens[target.markdown_object_id])
            if target_title and target_title.lower() in body:
                related = True
            if not related:
                continue
            result[source_mid].append(ProposedLink(target_document_id=target_id))
            seen[source_mid].add(target_id)
    return result


def _confidence(
    *,
    group_size: int,
    is_group_root: bool,
    has_own_links: bool,
    group_has_links: bool,
) -> tuple[str, bool, str | None]:
    if group_size == 1:
        return "low", True, "ambiguous isolation"
    if is_group_root:
        if group_has_links:
            return "medium", False, None
        return "low", True, "unlinked sibling"
    if not has_own_links:
        return "low", True, "unlinked sibling"
    return "high", False, None
