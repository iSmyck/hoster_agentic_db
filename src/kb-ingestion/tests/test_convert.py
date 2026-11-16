"""Conversion pipeline tests (KBI.1.2–KBI.1.6)."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.object_store import InMemoryObjectStore
from kb_ingestion.app.parsers import extraction_router
from kb_ingestion.app.parsers.base import ParserError

_RUN_URL = "/api/kb/v1/ingest/convert/run"
_UPLOAD_URL = "/api/kb/v1/ingest/convert"


def _upload(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> str:
    response = client.post(
        _UPLOAD_URL,
        data={
            "space_id": "sales",
            "client_id": "n8n-1",
            "data_profile": "strict",
        },
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
            "<w:body><w:p><w:r><w:t>"
            f"{text}"
            "</w:t></w:r></w:p></w:body></w:document>"
        )
        zf.writestr("word/document.xml", document_xml)
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        for name, data in images.items():
            zf.writestr(f"word/media/{name}", data)
    return buffer.getvalue()


def _minimal_pdf(text: str = "Sample PDF") -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    # pypdf blank page has no text; acceptable for format routing test
    return buf.getvalue()


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


def test_router_selects_markdown_by_extension() -> None:
    result = extraction_router.extract("note.md", "text/plain", b"# Title\n\nBody")
    assert "Title" in result.markdown_body


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
    assert "Policy" in report["markdown"]
    assert report["status"] == "ready"
    fm = report["front_matter_draft"]
    assert fm["schema_version"] == "document-front-matter-v2"
    assert fm["parent_id"] is None
    assert fm["ownership_mode"] == "migrated"
    assert fm["title"] == "Policy"


def test_docx_embedded_media_and_blocker(client: TestClient, object_store: InMemoryObjectStore) -> None:
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
    outcome = _run(client, object_id, "legal/contract.docx")
    assert outcome["status"] == 200
    report = outcome["body"]
    assert report["status"] == "blocked"
    assert report["blockers"]
    assert object_store.count() > before
    assert "attachment://" in report["markdown"]
    assert "watermark" not in report["markdown"]


def test_pdf_and_xlsx_routing(client: TestClient) -> None:
    pdf_id = _upload(client, filename="a.pdf", content=_minimal_pdf(), content_type="application/pdf")
    assert _run(client, pdf_id, "a.pdf")["status"] == 200
    xlsx_id = _upload(
        client,
        filename="sheet.xlsx",
        content=_minimal_xlsx(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    body = _run(client, xlsx_id, "sheet.xlsx")["body"]
    assert "widget" in body["markdown"]


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


def test_run_missing_object(client: TestClient) -> None:
    outcome = _run(client, "0" * 32, "missing.md")
    assert outcome["status"] == 404
    assert outcome["body"]["detail"]["code"] == "OBJECT_NOT_FOUND"