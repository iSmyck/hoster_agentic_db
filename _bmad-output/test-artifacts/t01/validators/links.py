"""Local Markdown link / anchor validation for integration protocols."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class MarkdownLinkChecker:
    """Check local relative links and heading anchors within a docs tree."""

    def __init__(self, contracts_dir: Path, specs_dir: Path) -> None:
        self.contracts_dir = contracts_dir
        self.specs_dir = specs_dir
        self._cache: dict[Path, tuple[str, set[str]]] = {}

    def _load(self, path: Path) -> tuple[str, set[str]]:
        if path not in self._cache:
            text = path.read_text(encoding="utf-8")
            headings = {
                self._anchor(line)
                for line in text.splitlines()
                if line.startswith("#")
            }
            self._cache[path] = (text, headings)
        return self._cache[path]

    @staticmethod
    def _anchor(line: str) -> str:
        """GitHub-style heading anchor from a Markdown heading line."""
        title = line.lstrip("#").strip()
        title = re.sub(r"<[^>]+>", "", title)
        title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
        title = re.sub(r"\s+", "-", title.strip())
        return title.lower()

    def check_file(self, path: Path) -> list[tuple[str, str, str | None]]:
        """Return [(link_text, target, error_or_None)] for local links in *path*."""
        text, _ = self._load(path)
        results: list[tuple[str, str, str | None]] = []
        # [text](target) or [text](target "title")
        for match in re.finditer(r"\[([^\]]+)\]\(([^)\"\s]+)(?:\s+[^)]*)?\)", text):
            link_text, target = match.group(1), match.group(2)
            error = self._resolve(path, target)
            results.append((link_text, target, error))
        # reference-style links: [text]: target
        for match in re.finditer(r"^\[([^\]]+)\]:\s+(\S+)", text, flags=re.MULTILINE):
            link_text, target = match.group(1), match.group(2)
            error = self._resolve(path, target)
            results.append((link_text, target, error))
        return results

    def _resolve(self, source: Path, target: str) -> str | None:
        if target.startswith(("http://", "https://", "mailto:")):
            return None  # external links are not verified here
        if target.startswith("#"):
            _, headings = self._load(source)
            anchor = target[1:]
            return None if anchor in headings else f"missing anchor #{anchor}"
        # Split file and anchor.
        if "#" in target:
            file_part, anchor = target.split("#", 1)
        else:
            file_part, anchor = target, None
        if not file_part:
            resolved = source
        else:
            resolved = (source.parent / file_part).resolve()
            if not str(resolved).startswith(str(self.contracts_dir.resolve())) and not str(
                resolved
            ).startswith(str(self.specs_dir.resolve())):
                return f"path outside docs tree: {file_part}"
        if not resolved.exists():
            return f"missing file: {file_part}"
        if anchor is not None:
            _, headings = self._load(resolved)
            if anchor not in headings:
                return f"missing anchor #{anchor} in {file_part}"
        return None
