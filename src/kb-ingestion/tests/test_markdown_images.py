"""KBI.1.4 Markdown attachment:// integration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .test_convert import _minimal_docx, _run, _tiny_png, _upload
from .test_media import _bytes_len

_DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_illustrative_embed_object_id_matches(client: TestClient) -> None:
    docx = _minimal_docx("Body", {"figure.png": _bytes_len(600)})
    object_id = _upload(client, filename="c.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "c.docx")["body"]
    att = report["attachments"][0]
    expected = f"![{att['alt_text']}](attachment://{att['object_id']})"
    assert expected in report["markdown"]


def test_decorative_excluded_from_markdown(client: TestClient) -> None:
    docx = _minimal_docx("Body", {"header-watermark.png": _bytes_len(800)})
    object_id = _upload(client, filename="c.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "c.docx")["body"]
    assert "attachment://" not in report["markdown"]
    assert "watermark" not in report["markdown"].lower()
    assert report["attachments"][0]["media_class"] == "decorative"


def test_generated_alt_marked_automatic(client: TestClient) -> None:
    docx = _minimal_docx("Body", {"figure.png": _bytes_len(600)})
    object_id = _upload(client, filename="c.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "c.docx")["body"]
    att = report["attachments"][0]
    assert att["automatic"] is True
    assert att["alt_text"]


def test_png_document_attachment_id(client: TestClient) -> None:
    object_id = _upload(client, filename="scan.png", content=_tiny_png(), content_type="image/png")
    report = _run(client, object_id, "media/scan.png")["body"]
    att = report["attachments"][0]
    assert f"attachment://{att['object_id']}" in report["markdown"]
