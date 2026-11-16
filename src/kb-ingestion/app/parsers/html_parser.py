"""Simple HTML to text/markdown extractor."""

from __future__ import annotations

from html.parser import HTMLParser

from .base import ParserError, ParseResult

_BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(part for part in self._parts if part).strip()


def extract(filename: str, data: bytes) -> ParseResult:
    lowered = data.lower()
    if b"<script" in lowered or b"javascript:" in lowered:
        raise ParserError("SECURITY_BLOCKER", "executable html content is not allowed")
    try:
        raw = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "html is not valid utf-8") from exc
    parser = _TextExtractor()
    parser.feed(raw)
    body = parser.text()
    if not body:
        body = "(empty html document)"
    return ParseResult(markdown_body=body)