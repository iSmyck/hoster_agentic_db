"""PDF text and embedded image extractor."""

from __future__ import annotations

import io

from .base import ExtractedMedia, ParserError, ParseResult


def _filter_names(image_obj) -> list[str]:
    filt = image_obj.get("/Filter")
    if filt is None:
        return []
    if isinstance(filt, list):
        return [str(item) for item in filt]
    return [str(filt)]


def _image_media_type(name: str, image_obj, data: bytes = b"") -> str:
    if any("DCTDecode" in token for token in _filter_names(image_obj)):
        return "image/jpeg"
    if name.lower().endswith(".png") or data.startswith(b"\x89PNG"):
        return "image/png"
    return "image/jpeg"


def _xobject_name(key) -> str:
    name = str(key)
    return name.removeprefix("/")


def _page_image_xobjects(page) -> list[tuple[str, object]]:
    resources = page.get("/Resources")
    if resources is None:
        return []
    resources = resources.get_object()
    xobjects = resources.get("/XObject")
    if xobjects is None:
        return []
    xobjects = xobjects.get_object()
    found: list[tuple[str, object]] = []
    for key, ref in xobjects.items():
        try:
            obj = ref.get_object()
        except Exception:  # noqa: BLE001, S112
            continue
        if obj.get("/Subtype") == "/Image":
            found.append((_xobject_name(key), obj))
    return found


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
    errors: list[dict[str, str]] = []
    embedded: list[ExtractedMedia] = []
    try:
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                parts.append(f"## Page {index}\n\n{text}")
            else:
                losses.append({"kind": "empty_page", "detail": f"page {index} had no extractable text"})
            for name, image_obj in _page_image_xobjects(page):
                try:
                    payload = image_obj.get_data()
                except Exception:  # noqa: BLE001
                    errors.append(
                        {
                            "code": "PDF_IMAGE_UNREADABLE",
                            "detail": f"pdf image stream unreadable: {name}",
                        }
                    )
                    continue
                media_type = _image_media_type(name, image_obj, payload)
                embedded.append(ExtractedMedia(filename=name, data=payload, media_type=media_type))
    except ParserError:
        raise
    except Exception as exc:
        raise ParserError("UNSUPPORTED_FORMAT", "pdf extraction failed") from exc
    body = "\n\n".join(parts) if parts else "(empty pdf)"
    return ParseResult(
        markdown_body=body,
        embedded_media=embedded,
        losses=losses,
        errors=errors,
    )