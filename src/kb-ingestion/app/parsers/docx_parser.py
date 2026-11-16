"""DOCX text and embedded media extractor."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

from .base import ExtractedMedia, ParserError, ParseResult
from .ooxml import ooxml_security_check

_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract(filename: str, data: bytes) -> ParseResult:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "docx is not a valid zip archive") from exc
    with zf:
        ooxml_security_check(zf)
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
        try:
            root = ET.fromstring(document_xml)
        except ET.ParseError as exc:
            raise ParserError("UNSUPPORTED_FORMAT", "docx document.xml is not valid xml") from exc
        texts = [node.text for node in root.findall(".//w:t", _NS) if node.text]
        body = " ".join(texts).strip()
        body = re.sub(r"\s+", " ", body)
        if not body:
            body = "(empty docx)"
        return ParseResult(markdown_body=body, embedded_media=media)