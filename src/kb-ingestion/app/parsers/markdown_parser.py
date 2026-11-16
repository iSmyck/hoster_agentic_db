"""Markdown pass-through extractor."""

from __future__ import annotations

from .base import ParserError, ParseResult


def extract(filename: str, data: bytes) -> ParseResult:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "markdown is not valid utf-8") from exc
    return ParseResult(markdown_body=text.strip())