"""Source connector port and concrete adapters."""

from __future__ import annotations

import hashlib
import mimetypes
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SourceEntry:
    """Single scanned object from a source."""

    path: str
    content: bytes
    media_type: str
    size: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceScanResult:
    """Result of scanning a source connector."""

    entries: list[SourceEntry]
    cursor_value: str
    cursor_hash: str


class SourceConnector(ABC):
    """Inbound port for reading external source content."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the connector type identifier."""

    @abstractmethod
    def scan(self, cursor: str | None = None) -> SourceScanResult:
        """Scan the source and return entries plus a durable cursor/hash."""


class StubSourceConnector(SourceConnector):
    """In-memory source connector for tests."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._entries: list[SourceEntry] = []
        for item in config.get("entries", []):
            content = item.get("content", "")
            if isinstance(content, str):
                content = content.encode("utf-8")
            self._entries.append(
                SourceEntry(
                    path=item["path"],
                    content=content,
                    media_type=item.get("media_type", "text/markdown"),
                    size=len(content),
                    metadata=item.get("metadata", {}),
                )
            )

    @property
    def source_type(self) -> str:
        return "stub"

    def scan(self, cursor: str | None = None) -> SourceScanResult:
        entries = list(self._entries)
        cursor_value = self.config.get("cursor_value", "")
        cursor_hash = _hash_entries(entries)
        return SourceScanResult(
            entries=entries,
            cursor_value=cursor_value,
            cursor_hash=cursor_hash,
        )


class GitFolderConnector(SourceConnector):
    """Scan a local folder that represents a Git-managed source tree.

    Configuration keys:
        - path: root folder to scan (required)
        - include_patterns: list of glob patterns to include (default: ["*"])
        - exclude_patterns: list of glob patterns to exclude (default: [".git/**"])
        - max_file_size: maximum file size in bytes (default: 10 MiB)
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.root = Path(config["path"])
        self.include_patterns = config.get("include_patterns", ["*"])
        self.exclude_patterns = config.get("exclude_patterns", [".git/**"])
        self.max_file_size = config.get("max_file_size", 10 * 1024 * 1024)

    @property
    def source_type(self) -> str:
        return "git_folder"

    def scan(self, cursor: str | None = None) -> SourceScanResult:
        entries: list[SourceEntry] = []
        for file_path in sorted(self.root.rglob("*")):
            if not file_path.is_file() or file_path.is_symlink():
                continue
            rel_path = file_path.relative_to(self.root).as_posix()
            if not self._included(rel_path):
                continue
            try:
                stat = file_path.stat()
                if stat.st_size > self.max_file_size:
                    continue
                media_type, _ = mimetypes.guess_type(str(file_path))
                media_type = media_type or "application/octet-stream"
                content = file_path.read_bytes()
                if len(content) > self.max_file_size:
                    continue
            except OSError:
                continue
            entries.append(
                SourceEntry(
                    path=rel_path,
                    content=content,
                    media_type=media_type,
                    size=len(content),
                    metadata={
                        "mtime": stat.st_mtime,
                        "mode": oct(stat.st_mode),
                    },
                )
            )

        cursor_value = _folder_cursor(self.root, entries)
        cursor_hash = _hash_entries(entries)
        return SourceScanResult(
            entries=entries,
            cursor_value=cursor_value,
            cursor_hash=cursor_hash,
        )

    def _included(self, rel_path: str) -> bool:
        for pattern in self.exclude_patterns:
            if _glob_match(rel_path, pattern):
                return False
        return any(_glob_match(rel_path, pattern) for pattern in self.include_patterns)


def _hash_entries(entries: list[SourceEntry]) -> str:
    hasher = hashlib.sha256()
    for entry in entries:
        hasher.update(entry.path.encode("utf-8"))
        hasher.update(entry.content)
        hasher.update(entry.media_type.encode("utf-8"))
    return hasher.hexdigest()


def _folder_cursor(root: Path, entries: list[SourceEntry]) -> str:
    """Build a deterministic cursor from the newest mtime among scanned files."""
    max_mtime = 0.0
    for entry in entries:
        max_mtime = max(max_mtime, entry.metadata.get("mtime", 0.0))
    return f"{root.as_posix()}:{max_mtime:.6f}:{len(entries)}"


def _glob_match(path: str, pattern: str) -> bool:
    """Glob match supporting '*', '?' and '**' across path separators.

    Falls back to fnmatch for simple patterns. Literal regex metacharacters
    in the pattern are escaped so file names like 'report(1).md' match exactly.
    """
    import fnmatch

    if "**" not in pattern:
        return fnmatch.fnmatch(path, pattern)

    regex = re.escape(pattern)
    regex = regex.replace(re.escape("**/"), "(?:.*/)?")
    regex = regex.replace(re.escape("**"), ".*")
    regex = regex.replace(r"\*", "[^/]*").replace(r"\?", ".")
    return bool(re.fullmatch(regex, path))


SOURCE_CONNECTOR_REGISTRY: dict[str, type[SourceConnector]] = {
    "stub": StubSourceConnector,
    "git_folder": GitFolderConnector,
}


def build_source_connector(source_type: str, config: dict[str, Any]) -> SourceConnector:
    """Factory returning a configured source connector."""
    connector_cls = SOURCE_CONNECTOR_REGISTRY.get(source_type)
    if connector_cls is None:
        raise ValueError(f"unknown source_type: {source_type}")
    return connector_cls(config)
