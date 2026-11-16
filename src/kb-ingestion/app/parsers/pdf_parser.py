"""PDF text extractor using pypdf."""

from __future__ import annotations

import io

from .base import ParserError, ParseResult


def extract(filename: str, data: bytes) -> ParseResult:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "pdf extractor unavailable") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "pdf is not readable") from exc
    parts: list[str] = []
    losses: list[dict[str, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(f"## Page {index}\n\n{text}")
        else:
            losses.append({"kind": "empty_page", "detail": f"page {index} had no extractable text"})
    body = "\n\n".join(parts) if parts else "(empty pdf)"
    return ParseResult(markdown_body=body, losses=losses)