"""Format detection and extractor selection (KBI-103)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from . import docx_parser, html_parser, image_parser, markdown_parser, pdf_parser, xlsx_parser
from .base import ParserError

_EXTRACTORS = {
    "markdown": markdown_parser.extract,
    "html": html_parser.extract,
    "pdf": pdf_parser.extract,
    "docx": docx_parser.extract,
    "xlsx": xlsx_parser.extract,
    "image": image_parser.extract,
}

_EXTENSION_MAP = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".pdf": "pdf",
    ".docx": "docx",
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
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "image/png": "image",
    "image/jpeg": "image",
}


def detect_format(filename: str, media_type: str | None) -> str:
    ext = Path(filename).suffix.lower()
    by_ext = _EXTENSION_MAP.get(ext)
    mime = media_type or mimetypes.guess_type(filename)[0] or ""
    by_mime = _MIME_MAP.get(mime)
    if by_ext and by_mime and by_ext != by_mime:
        return by_mime
    return by_ext or by_mime or ""


def extract(filename: str, media_type: str | None, data: bytes):
    kind = detect_format(filename, media_type)
    if not kind:
        raise ParserError("UNSUPPORTED_FORMAT", f"unsupported format for {filename}")
    if kind not in _EXTRACTORS:
        raise ParserError("UNSUPPORTED_FORMAT", f"no extractor for {kind}")
    handler = _EXTRACTORS[kind]
    return handler(filename, data)