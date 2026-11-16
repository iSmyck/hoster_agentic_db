"""In-memory registry of converted documents for structure batch-read."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from ..schemas.convert import AttachmentManifestEntry


@dataclass
class ConvertedDocument:
    markdown_object_id: str
    source_object_id: str
    space_id: str
    client_id: str
    source_path: str
    status: str
    markdown: str
    attachments: list[AttachmentManifestEntry]
    front_matter_draft: dict[str, Any]


class ConvertedCorpus:
    def __init__(self) -> None:
        self._docs: dict[str, ConvertedDocument] = {}

    def _key(self, space_id: str, client_id: str, markdown_object_id: str) -> str:
        return "/".join(
            quote(part, safe="") for part in (space_id, client_id, markdown_object_id)
        )

    def put(self, document: ConvertedDocument) -> None:
        key = self._key(document.space_id, document.client_id, document.markdown_object_id)
        self._docs[key] = document

    def get(
        self, space_id: str, client_id: str, markdown_object_id: str
    ) -> ConvertedDocument | None:
        return self._docs.get(self._key(space_id, client_id, markdown_object_id))
