"""DOCX text and embedded media extractor."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

from .base import ExtractedMedia, ParserError, ParseResult

_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_MAX_ZIP_MEMBERS = 256
_MAX_UNCOMPRESSED = 52_428_800


def _docx_security_check(zf: zipfile.ZipFile) -> None:
    if len(zf.infolist()) > _MAX_ZIP_MEMBERS:
        raise ParserError("SECURITY_BLOCKER", "docx archive has too many entries")
    total = sum(info.file_size for info in zf.infolist())
    if total > _MAX_UNCOMPRESSED:
        raise ParserError("SECURITY_BLOCKER", "docx archive exceeds uncompressed limit")


def extract(filename: str, data: bytes) -> ParseResult:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "docx is not a valid zip archive") from exc
    with zf:
        _docx_security_check(zf)
        media: list[ExtractedMedia] = []
        for name in zf.namelist():
            if not name.startswith("word/media/"):
                continue
            base = name.rsplit("/", 1)[-1]
            payload = zf.read(name)
            media_type = "image/png" if base.lower().endswith(".png") else "image/jpeg"
            media.append(ExtractedMedia(filename=base, data=payload, media_type=media_type))
        try:
            document_xml = zf.read("word/document.xml")
        except KeyError as exc:
            raise ParserError("UNSUPPORTED_FORMAT", "docx missing document.xml") from exc
        root = ET.fromstring(document_xml)
        texts = [node.text for node in root.findall(".//w:t", _NS) if node.text]
        body = " ".join(texts).strip()
        body = re.sub(r"\s+", " ", body)
        if not body:
            body = "(empty docx)"
        return ParseResult(markdown_body=body, embedded_media=media)