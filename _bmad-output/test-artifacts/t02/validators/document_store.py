"""In-memory Git-like document tree loader for T02 synthetic fixtures."""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Document:
    """One Markdown document inside a synthetic Space."""

    space_id: str
    repository_id: str
    path: str  # repository-relative, NFC-normalized
    content: str  # full Markdown bytes as UTF-8 string
    front_matter: dict[str, Any]
    body: str
    revision_sha: str  # synthetic full Git SHA-1 of canonical content bytes
    content_sha256: str

    @property
    def document_id(self) -> str | None:
        return self.front_matter.get("id")

    @property
    def parent_id(self) -> str | None:
        return self.front_matter.get("parent_id")

    @property
    def title(self) -> str | None:
        return self.front_matter.get("title")

    @property
    def archived(self) -> bool:
        return bool(self.front_matter.get("archived", False))

    @property
    def archive(self) -> dict[str, Any] | None:
        return self.front_matter.get("archive")

    @property
    def attachments(self) -> list[dict[str, Any]]:
        return self.front_matter.get("attachments", []) or []


@dataclass
class Space:
    """Synthetic repository-per-Space fixture."""

    space_id: str
    repository_id: str
    root: Path
    documents: list[Document] = field(default_factory=list)

    def by_id(self) -> dict[str, Document]:
        result: dict[str, Document] = {}
        for doc in self.documents:
            doc_id = doc.document_id
            if doc_id is not None:
                result[doc_id] = doc
        return result

    def by_path(self) -> dict[str, Document]:
        return {doc.path: doc for doc in self.documents}


def _canonical_path(path: Path) -> str:
    """Return repository-relative NFC path string using forward slashes."""
    rel = path.as_posix()
    rel = unicodedata.normalize("NFC", rel)
    # Strip any leading ./
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def _split_front_matter(text: str) -> tuple[str | None, str]:
    """Split YAML front matter from Markdown body.

    Supports the standard `---` fence. Returns (yaml_text_or_None, body).
    """
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines(keepends=True)
    if not lines:
        return None, text
    if lines[0].rstrip("\r\n") != "---":
        return None, text
    end = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            end = i
            break
    if end == -1:
        return None, text
    yaml_text = "".join(lines[1:end])
    body = "".join(lines[end + 1 :])
    # Normalize body start: ensure single leading newline max.
    body = body.lstrip("\r\n")
    return yaml_text, body


def load_space(space_id: str, repository_id: str, root: Path) -> Space:
    """Load every *.md file under *root* as a Document."""
    docs: list[Document] = []
    if not root.exists():
        return Space(
            space_id=space_id, repository_id=repository_id, root=root, documents=docs
        )
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        yaml_text, body = _split_front_matter(text)
        front_matter = yaml.safe_load(yaml_text) if yaml_text is not None else {}
        if front_matter is None:
            front_matter = {}
        content_bytes = text.encode("utf-8")
        revision_sha = hashlib.sha1(
            b"blob " + str(len(content_bytes)).encode("ascii") + b"\0" + content_bytes
        ).hexdigest()
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()
        rel = _canonical_path(path.relative_to(root))
        docs.append(
            Document(
                space_id=space_id,
                repository_id=repository_id,
                path=rel,
                content=text,
                front_matter=front_matter,
                body=body,
                revision_sha=revision_sha,
                content_sha256=content_sha256,
            )
        )
    return Space(
        space_id=space_id, repository_id=repository_id, root=root, documents=docs
    )
