"""Conversion pipeline tests (KBI.1.2–KBI.1.6)."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.object_store import InMemoryObjectStore
from kb_ingestion.app.core.config import settings
from kb_ingestion.app.parsers import extraction_router
from kb_ingestion.app.parsers.base import ParserError

_RUN_URL = "/api/kb/v1/ingest/convert/run"
_UPLOAD_URL = "/api/kb/v1/ingest/convert"

_REQUIRED_FM_KEYS = {
    "schema_version",
    "id",
    "title",
    "parent_id",
    "ownership_mode",
    "links",
    "valid_until",
    "archived",
    "attachments",
    "origin",
}
_ATTACHMENT_KEYS = {
    "object_id",
    "version",
    "sha256",
    "size",
    "media_type",
    "source_ref",
    "media_class",
    "verification_status",
}


def _upload(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> str:
    response = client.post(
        _UPLOAD_URL,
        data={"space_id": "sales", "client_id": "n8n-1", "data_profile": "strict"},
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()["object_id"]


def _run(client: TestClient, object_id: str, source_path: str, **extra: object) -> dict:
    payload = {
        "space_id": "sales",
        "client_id": "n8n-1",
        "object_id": object_id,
        "source_path": source_path,
        "ownership_mode": "migrated",
        **extra,
    }
    response = client.post(_RUN_URL, json=payload)
    return {"status": response.status_code, "body": response.json()}


def _minimal_docx(text: str, images: dict[str, bytes] | None = None) -> bytes:
    images = images or {}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
        )
        zf.writestr("word/document.xml", document_xml)
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        for name, data in images.items():
            zf.writestr(f"word/media/{name}", data)
    return buffer.getvalue()


def _minimal_pptx(text: str, images: dict[str, bytes] | None = None) -> bytes:
    images = images or {}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        slide_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f'<p:cSld><p:spTree><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:spTree></p:cSld></p:sld>'
        )
        zf.writestr("ppt/slides/slide1.xml", slide_xml)
        for name, data in images.items():
            zf.writestr(f"ppt/media/{name}", data)
    return buffer.getvalue()


def _minimal_xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws["A1"] = "Name"
    ws["B1"] = "Value"
    ws.append(["widget", "42"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _minimal_pdf() -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _tiny_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_router_extension_wins_on_mime_conflict() -> None:
    result = extraction_router.extract("note.md", "application/pdf", b"# Title\n\nBody")
    assert "Title" in result.markdown_body


def test_router_pdf_uses_default_when_docling_gate_off() -> None:
    assert settings.DOCLING_EVIDENCE_GATE is False
    result = extraction_router.extract("a.pdf", "application/pdf", _minimal_pdf())
    assert result.markdown_body


def test_router_rejects_unknown_format() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract("data.bin", "application/octet-stream", b"\x00\x01")
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_html_security_blocker() -> None:
    with pytest.raises(ParserError) as exc:
        extraction_router.extract("evil.html", "text/html", b"<script>alert(1)</script>")
    assert exc.value.code == "SECURITY_BLOCKER"


def test_markdown_convert_dry_run(client: TestClient) -> None:
    content = b"# Policy\n\nAll good."
    object_id = _upload(client, filename="policy.md", content=content, content_type="text/markdown")
    outcome = _run(client, object_id, "docs/policy.md")
    assert outcome["status"] == 200
    report = outcome["body"]
    assert report["path_map"] == {"docs/policy.md": object_id}
    assert report["correction_tasks"] == []
    assert report["status"] == "ready"
    fm = report["front_matter_draft"]
    assert _REQUIRED_FM_KEYS <= set(fm.keys())
    assert fm["schema_version"] == "document-front-matter-v2"
    assert fm["parent_id"] is None
    assert fm["links"] == []
    assert fm["valid_until"] is None
    assert fm["archived"] is False
    assert fm["ownership_mode"] == "migrated"
    assert fm["origin"]["ownership_mode"] == "migrated"
    assert fm["title"] == "Policy"


def test_png_image_document(client: TestClient) -> None:
    object_id = _upload(client, filename="scan.png", content=_tiny_png(), content_type="image/png")
    report = _run(client, object_id, "media/scan.png")["body"]
    assert report["status"] == "ready"
    assert report["attachments"]
    att = report["attachments"][0]
    assert att["sha256"]
    assert att["automatic"] is True
    assert "attachment://" in report["markdown"]


def test_docx_media_classification_and_blockers(
    client: TestClient, object_store: InMemoryObjectStore
) -> None:
    tiny = b"\x89PNG\r\n\x1a\n" + b"\x00" * 400
    signature = b"\x89PNG\r\n\x1a\n" + b"\x01" * 800
    docx = _minimal_docx("Contract body", {"watermark.png": tiny, "signature-scan.png": signature})
    object_id = _upload(
        client,
        filename="contract.docx",
        content=docx,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    before = object_store.count()
    report = _run(client, object_id, "legal/contract.docx")["body"]
    assert report["status"] == "blocked"
    assert report["blockers"]
    assert report["correction_tasks"]
    assert report["correction_tasks"][0]["blocker_code"] == "MEDIA_VERIFICATION_PENDING"
    assert object_store.count() > before
    pending = [a for a in report["attachments"] if a["verification_status"] == "pending"]
    assert pending
    assert pending[0]["automatic"] is True
    fm_att = report["front_matter_draft"]["attachments"]
    assert _ATTACHMENT_KEYS <= set(fm_att[0].keys())
    assert "watermark" not in report["markdown"].lower()


def test_pptx_embedded_media(client: TestClient) -> None:
    pptx = _minimal_pptx("Quarter results", {"chart-critical.png": _tiny_png()})
    object_id = _upload(
        client,
        filename="deck.pptx",
        content=pptx,
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    report = _run(client, object_id, "decks/q1.pptx")["body"]
    assert "Quarter" in report["markdown"]
    assert report["attachments"]


def test_pdf_and_xlsx_routing(client: TestClient) -> None:
    pdf_id = _upload(client, filename="a.pdf", content=_minimal_pdf(), content_type="application/pdf")
    pdf_report = _run(client, pdf_id, "a.pdf")["body"]
    assert pdf_report["markdown"]
    assert isinstance(pdf_report["losses"], list)
    xlsx_id = _upload(
        client,
        filename="sheet.xlsx",
        content=_minimal_xlsx(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert "widget" in _run(client, xlsx_id, "sheet.xlsx")["body"]["markdown"]


def test_unsupported_after_upload(client: TestClient) -> None:
    object_id = _upload(client, filename="blob.bin", content=b"data", content_type="application/octet-stream")
    outcome = _run(client, object_id, "blob.bin")
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "UNSUPPORTED_FORMAT"


def test_source_managed_requires_origin(client: TestClient) -> None:
    object_id = _upload(client, filename="x.md", content=b"# X", content_type="text/markdown")
    outcome = _run(client, object_id, "x.md", ownership_mode="source_managed", origin=None)
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "ORIGIN_REQUIRED"


def test_source_managed_with_matching_origin(client: TestClient) -> None:
    object_id = _upload(client, filename="x.md", content=b"# Managed", content_type="text/markdown")
    sha = "a" * 64
    origin = {
        "schema_version": "source-origin-v1",
        "source_id": "src-1",
        "source_binding_id": "bind-1",
        "source_object_id": object_id,
        "source_version": "v1",
        "source_content_sha256": sha,
        "source_ref": "x.md",
        "observed_at": "2026-11-17T00:00:00+00:00",
        "ownership_mode": "source_managed",
    }
    report = _run(
        client,
        object_id,
        "x.md",
        ownership_mode="source_managed",
        origin=origin,
    )["body"]
    assert report["front_matter_draft"]["origin"]["ownership_mode"] == "source_managed"


def test_run_missing_object(client: TestClient) -> None:
    outcome = _run(client, "0" * 32, "missing.md")
    assert outcome["status"] == 404
    assert outcome["body"]["detail"]["code"] == "OBJECT_NOT_FOUND"