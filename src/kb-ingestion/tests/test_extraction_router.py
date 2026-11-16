"""KBI.1.2 format detection, routing, and security barrier matrix."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from kb_ingestion.app.core.config import settings
from kb_ingestion.app.parsers import docling_parser, extraction_router, markdown_parser
from kb_ingestion.app.parsers.base import ParserError
from kb_ingestion.app.parsers.ooxml import ooxml_security_check

from .test_convert import (
    _minimal_docx,
    _minimal_pdf,
    _minimal_pptx,
    _minimal_xlsx,
    _run,
    _tiny_png,
    _upload,
)


def _ooxml_zip_bomb(*, prefix: str, slide_or_doc: str, inner_xml: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(slide_or_doc, inner_xml)
        for index in range(260):
            zf.writestr(f"{prefix}/junk{index}.txt", "x")
    return buffer.getvalue()


def _bad_pptx_xml() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("ppt/slides/slide1.xml", "<broken")
    return buffer.getvalue()


def _bad_docx_xml() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("word/document.xml", "<broken")
    return buffer.getvalue()


def _xlsx_zip_bomb() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("xl/workbook.xml", "<?xml version='1.0'?><workbook/>")
        for index in range(260):
            zf.writestr(f"xl/junk{index}.xml", "<x/>")
    return buffer.getvalue()


# --- I/O matrix: direct router ---


def test_matrix_md_mime_and_extension() -> None:
    body = b"# Note\n\nSaved body."
    result = extraction_router.extract("note.md", "text/markdown", body)
    assert "Saved body" in result.markdown_body


def test_matrix_extension_wins_over_mime() -> None:
    result = extraction_router.extract("note.md", "application/pdf", b"# Title\n\nMarkdown wins")
    assert "Markdown wins" in result.markdown_body
    assert "Title" in result.markdown_body


def test_matrix_html_ok() -> None:
    result = extraction_router.extract("page.html", "text/html", b"<p>Hello HTML</p>")
    assert "Hello" in result.markdown_body


def test_matrix_html_script_blocker() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract("evil.html", "text/html", b"<script>alert(1)</script>")
    assert exc.value.code == "SECURITY_BLOCKER"


def test_matrix_html_javascript_url_blocker() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract(
            "evil.html",
            "text/html",
            b'<a href="javascript:alert(1)">click</a>',
        )
    assert exc.value.code == "SECURITY_BLOCKER"


def test_matrix_png_jpg_routed() -> None:
    png = extraction_router.extract("scan.png", "image/png", _tiny_png())
    assert png.embedded_media
    assert png.embedded_media[0].media_type == "image/png"
    jpg = extraction_router.extract(
        "photo.jpg",
        "image/jpeg",
        b"\xff\xd8\xff" + b"\x00" * 16,
    )
    assert jpg.embedded_media


def test_matrix_pdf_default_skips_docling() -> None:
    assert settings.DOCLING_EVIDENCE_GATE is False
    called: list[str] = []

    original_docling = docling_parser.extract

    def spy_docling(filename: str, data: bytes):
        called.append("docling")
        return original_docling(filename, data)

    with patch.object(docling_parser, "extract", side_effect=spy_docling):
        result = extraction_router.extract("blank.pdf", "application/pdf", _minimal_pdf())
    assert called == []
    assert result.markdown_body


def test_matrix_pdf_gated_docling_fallback() -> None:
    docling_calls = 0
    original_docling = docling_parser.extract

    def spy_docling(filename: str, data: bytes):
        nonlocal docling_calls
        docling_calls += 1
        return original_docling(filename, data)

    with (
        patch.object(settings, "DOCLING_EVIDENCE_GATE", True),
        patch.object(docling_parser, "extract", side_effect=spy_docling),
    ):
        result = extraction_router.extract("blank.pdf", "application/pdf", _minimal_pdf())
    assert docling_calls == 1
    assert result.markdown_body


def test_matrix_docx_xlsx_pptx_nonempty() -> None:
    docx = extraction_router.extract(
        "a.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        _minimal_docx("Docx text"),
    )
    assert "Docx" in docx.markdown_body
    xlsx = extraction_router.extract(
        "a.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _minimal_xlsx(),
    )
    assert "widget" in xlsx.markdown_body
    pptx = extraction_router.extract(
        "a.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        _minimal_pptx("Slide words"),
    )
    assert "Slide" in pptx.markdown_body


def test_matrix_unknown_format() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract("blob.bin", "application/octet-stream", b"\x00\x01")
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_matrix_mdx_blocked_by_extension() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract("page.mdx", "text/plain", b"export const x = 1")
    assert exc.value.code == "SECURITY_BLOCKER"


def test_matrix_mdx_blocked_by_mime() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract("page.txt", "text/mdx", b"content")
    assert exc.value.code == "SECURITY_BLOCKER"


def test_matrix_docx_zip_bomb() -> None:
    doc_xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body/></w:document>"
    )
    payload = _ooxml_zip_bomb(prefix="word", slide_or_doc="word/document.xml", inner_xml=doc_xml)
    with pytest.raises(ParserError) as exc:
        extraction_router.extract(
            "bomb.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            payload,
        )
    assert exc.value.code == "SECURITY_BLOCKER"


def test_matrix_xlsx_zip_bomb() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract(
            "bomb.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            _xlsx_zip_bomb(),
        )
    assert exc.value.code == "SECURITY_BLOCKER"


def test_ooxml_uncompressed_total_limit_without_huge_file() -> None:
    zf = MagicMock(spec=zipfile.ZipFile)
    first = zipfile.ZipInfo("a.bin")
    first.file_size = 30_000_000
    second = zipfile.ZipInfo("b.bin")
    second.file_size = 25_000_000
    zf.infolist.return_value = [first, second]
    with pytest.raises(ParserError) as exc:
        ooxml_security_check(zf)
    assert exc.value.code == "SECURITY_BLOCKER"


def test_matrix_pptx_zip_bomb() -> None:
    slide = (
        '<?xml version="1.0"?>'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        "<p:cSld/></p:sld>"
    )
    payload = _ooxml_zip_bomb(prefix="ppt", slide_or_doc="ppt/slides/slide1.xml", inner_xml=slide)
    with pytest.raises(ParserError) as exc:
        extraction_router.extract(
            "bomb.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            payload,
        )
    assert exc.value.code == "SECURITY_BLOCKER"


def test_matrix_bad_pptx_xml() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract(
            "bad.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            _bad_pptx_xml(),
        )
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_matrix_bad_docx_xml() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract(
            "bad.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _bad_docx_xml(),
        )
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_router_maps_unexpected_parser_exception() -> None:
    with (
        patch.object(markdown_parser, "extract", side_effect=RuntimeError("boom")),
        pytest.raises(ParserError) as exc,
    ):
        extraction_router.extract("note.md", "text/markdown", b"# hi")
    assert exc.value.code == "UNSUPPORTED_FORMAT"
    assert isinstance(exc.value.__cause__, RuntimeError)


# --- HTTP convert/run for selected barrier cases ---


def test_http_html_ok(client: TestClient) -> None:
    object_id = _upload(
        client,
        filename="ok.html",
        content=b"<p>Hello HTTP</p>",
        content_type="text/html",
    )
    outcome = _run(client, object_id, "docs/ok.html")
    assert outcome["status"] == 200
    assert "Hello" in outcome["body"]["markdown"]


def test_http_html_script_returns_400(client: TestClient) -> None:
    object_id = _upload(
        client,
        filename="evil.html",
        content=b"<script>alert(1)</script>",
        content_type="text/html",
    )
    outcome = _run(client, object_id, "docs/evil.html")
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "SECURITY_BLOCKER"


def test_http_mdx_returns_400(client: TestClient) -> None:
    object_id = _upload(
        client,
        filename="app.mdx",
        content=b"export default {}",
        content_type="text/mdx",
    )
    outcome = _run(client, object_id, "docs/app.mdx")
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "SECURITY_BLOCKER"


def test_http_zip_bomb_docx_returns_400(client: TestClient) -> None:
    doc_xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body/></w:document>"
    )
    bomb = _ooxml_zip_bomb(prefix="word", slide_or_doc="word/document.xml", inner_xml=doc_xml)
    object_id = _upload(
        client,
        filename="bomb.docx",
        content=bomb,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    outcome = _run(client, object_id, "docs/bomb.docx")
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "SECURITY_BLOCKER"


def test_http_bad_pptx_xml_returns_400(client: TestClient) -> None:
    object_id = _upload(
        client,
        filename="bad.pptx",
        content=_bad_pptx_xml(),
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    outcome = _run(client, object_id, "docs/bad.pptx")
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "UNSUPPORTED_FORMAT"


def test_http_unknown_format_returns_400(client: TestClient) -> None:
    object_id = _upload(
        client,
        filename="blob.bin",
        content=b"data",
        content_type="application/octet-stream",
    )
    outcome = _run(client, object_id, "blob.bin")
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "UNSUPPORTED_FORMAT"