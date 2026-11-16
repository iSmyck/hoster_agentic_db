"""Standalone image documents."""

from __future__ import annotations

import mimetypes

from .base import ExtractedMedia, ParseResult


def extract(filename: str, data: bytes) -> ParseResult:
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return ParseResult(
        markdown_body="",
        embedded_media=[ExtractedMedia(filename=filename, data=data, media_type=media_type)],
    )