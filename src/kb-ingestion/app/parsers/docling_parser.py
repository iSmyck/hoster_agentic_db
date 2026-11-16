"""Evidence-gated Docling route placeholder (disabled unless gate is on)."""

from __future__ import annotations

from .base import ParserError, ParseResult


def extract(filename: str, data: bytes) -> ParseResult:
    raise ParserError("UNSUPPORTED_FORMAT", "docling route is not activated")