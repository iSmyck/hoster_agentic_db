"""Format detection and extractor selection (KBI-103)."""

from __future__ import annotations

import mimetypes
from collections.abc import Callable
from pathlib import Path

from ..core.config import settings
from . import (
    docling_parser,
    docx_parser,
    html_parser,
    image_parser,
    markdown_parser,
    pdf_parser,
    pptx_parser,
    xlsx_parser,
)
from .base import ParserError, ParseResult

ExtractFn = Callable[[str, bytes], ParseResult]

_EXTENSION_MAP = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}

_MIME_MAP = {
    "text/markdown": "markdown",
    "text/html": "html",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "image/png": "image",
    "image/jpeg": "image",
}

_ROUTES: dict[str, list[tuple[str, ExtractFn, bool]]] = {
    "markdown": [("default", lambda f, d: markdown_parser.extract(f, d), False)],
    "html": [("default", lambda f, d: html_parser.extract(f, d), False)],
    "pdf": [
        ("docling", lambda f, d: docling_parser.extract(f, d), True),
        ("default", lambda f, d: pdf_parser.extract(f, d), False),
    ],
    "docx": [("default", lambda f, d: docx_parser.extract(f, d), False)],
    "pptx": [("default", lambda f, d: pptx_parser.extract(f, d), False)],
    "xlsx": [("default", lambda f, d: xlsx_parser.extract(f, d), False)],
    "image": [("default", lambda f, d: image_parser.extract(f, d), False)],
}


def detect_format(filename: str, media_type: str | None) -> str:
    ext = Path(filename).suffix.lower()
    by_ext = _EXTENSION_MAP.get(ext)
    mime = media_type or mimetypes.guess_type(filename)[0] or ""
    by_mime = _MIME_MAP.get(mime)
    if by_ext and by_mime and by_ext != by_mime:
        return by_ext
    return by_ext or by_mime or ""


def _reject_mdx(filename: str, media_type: str | None) -> None:
    ext = Path(filename).suffix.lower()
    mime = media_type or mimetypes.guess_type(filename)[0] or ""
    if ext == ".mdx" or mime == "text/mdx":
        raise ParserError("SECURITY_BLOCKER", "mdx content is not allowed")


def extract(filename: str, media_type: str | None, data: bytes) -> ParseResult:
    _reject_mdx(filename, media_type)
    kind = detect_format(filename, media_type)
    if not kind:
        raise ParserError("UNSUPPORTED_FORMAT", f"unsupported format for {filename}")
    routes = _ROUTES.get(kind)
    if not routes:
        raise ParserError("UNSUPPORTED_FORMAT", f"no routes for {kind}")
    last_error: ParserError | None = None
    for _route_name, handler, evidence_gated in routes:
        if evidence_gated and not settings.DOCLING_EVIDENCE_GATE:
            continue
        try:
            return handler(filename, data)
        except ParserError as exc:
            last_error = exc
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = ParserError("UNSUPPORTED_FORMAT", f"extractor failed for {kind}")
            last_error.__cause__ = exc
            continue
    if last_error:
        raise last_error
    raise ParserError("UNSUPPORTED_FORMAT", f"no active extractor for {kind}")