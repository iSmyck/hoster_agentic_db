"""PPTX text and embedded media extractor."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

from .base import ExtractedMedia, ParserError, ParseResult
from .ooxml import ooxml_security_check

_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
_SLIDE_PATH = re.compile(r"ppt/slides/slide(\d+)\.xml$")


def _slide_number(path: str) -> int:
    match = _SLIDE_PATH.match(path)
    return int(match.group(1)) if match else 0


def extract(filename: str, data: bytes) -> ParseResult:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "pptx is not a valid zip archive") from exc
    with zf:
        ooxml_security_check(zf)
        media: list[ExtractedMedia] = []
        for name in zf.namelist():
            if name.startswith("ppt/media/"):
                base = name.rsplit("/", 1)[-1]
                payload = zf.read(name)
                lower = base.lower()
                if lower.endswith(".png"):
                    media_type = "image/png"
                elif lower.endswith((".jpg", ".jpeg")):
                    media_type = "image/jpeg"
                else:
                    media_type = "application/octet-stream"
                media.append(ExtractedMedia(filename=base, data=payload, media_type=media_type))
        slides_xml = [n for n in zf.namelist() if _SLIDE_PATH.match(n)]
        parts: list[str] = []
        for slide_path in sorted(slides_xml, key=_slide_number):
            try:
                root = ET.fromstring(zf.read(slide_path))
            except ET.ParseError as exc:
                raise ParserError("UNSUPPORTED_FORMAT", "pptx slide xml is not valid") from exc
            slide_texts: list[str] = []
            for node in root.findall(".//a:t", _NS):
                if node.text and node.text.strip():
                    slide_texts.append(node.text.strip())
            if slide_texts:
                slide_num = _slide_number(slide_path)
                text = " ".join(slide_texts)
                parts.append(f"## Slide {slide_num}\n\n{text}")
        body = "\n\n".join(parts) if parts else "(empty pptx)"
        return ParseResult(markdown_body=body, embedded_media=media)