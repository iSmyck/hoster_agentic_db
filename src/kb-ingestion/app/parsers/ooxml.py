"""Shared OOXML zip archive security limits (docx, pptx, xlsx)."""

from __future__ import annotations

import zipfile

from .base import ParserError

_MAX_ZIP_MEMBERS = 256
_MAX_UNCOMPRESSED = 52_428_800


def ooxml_security_check(zf: zipfile.ZipFile) -> None:
    if len(zf.infolist()) > _MAX_ZIP_MEMBERS:
        raise ParserError("SECURITY_BLOCKER", "ooxml archive has too many entries")
    total = sum(info.file_size for info in zf.infolist())
    if total > _MAX_UNCOMPRESSED:
        raise ParserError("SECURITY_BLOCKER", "ooxml archive exceeds uncompressed limit")