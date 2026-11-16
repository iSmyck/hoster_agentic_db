"""KBI.1.3 media extraction, classification, and convert/run matrix."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.object_store import InMemoryObjectStore
from kb_ingestion.app.parsers import extraction_router, pdf_parser, pptx_parser
from kb_ingestion.app.services.media_processor import classify_image, requires_verification

from .test_convert import (
    _minimal_docx,
    _minimal_pptx,
    _run,
    _upload,
)

_DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PPTX_CT = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_PDF_CT = "application/pdf"


def _bytes_len(n: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * max(0, n - 8)


def _pdf_with_embedded_image(
    xobject_name: str = "Im0",
    *,
    payload: bytes | None = None,
    dct_decode: bool = False,
) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    img = DecodedStreamObject()
    img[NameObject("/Type")] = NameObject("/XObject")
    img[NameObject("/Subtype")] = NameObject("/Image")
    img[NameObject("/Width")] = NumberObject(1)
    img[NameObject("/Height")] = NumberObject(1)
    img[NameObject("/ColorSpace")] = NameObject("/DeviceRGB")
    img[NameObject("/BitsPerComponent")] = NumberObject(8)
    if dct_decode:
        img[NameObject("/Filter")] = NameObject("/DCTDecode")
    img.set_data(payload if payload is not None else bytes([10, 20, 30]))
    img_ref = writer._add_object(img)

    page_obj = page.get_object()
    resources = page_obj.get("/Resources")
    if resources is None:
        resources = DictionaryObject()
        page_obj[NameObject("/Resources")] = resources
    xobj = resources.get("/XObject")
    if xobj is None:
        xobj = DictionaryObject()
        resources[NameObject("/XObject")] = xobj
    xobj[NameObject(f"/{xobject_name}")] = img_ref

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _pptx_multi_slide(slides: dict[int, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for num, text in slides.items():
            slide_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                f'<p:cSld><p:spTree><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:spTree></p:cSld></p:sld>'
            )
            zf.writestr(f"ppt/slides/slide{num}.xml", slide_xml)
    return buffer.getvalue()


# --- Rule-based classifier (five classes) ---


@pytest.mark.parametrize(
    ("filename", "size", "expected"),
    [
        ("watermark.png", 60_000, "decorative"),
        ("brand-logo.png", 60_000, "decorative"),
        ("ui-icon.svg", 10_000, "decorative"),
        ("tiny.bin", 100, "decorative"),
        ("figure.png", 1024, "illustrative"),
        ("generic-photo.jpg", 51_000, "substantive"),
        ("chart-critical.png", 67, "critical"),
        ("wiring-schematic.png", 200, "critical"),
        ("signature-scan.png", 67, "handwritten"),
        ("handwriting-sample.png", 67, "handwritten"),
    ],
)
def test_classify_image_matrix(filename: str, size: int, expected: str) -> None:
    result = classify_image(filename, _bytes_len(size), "image/png")
    assert result.media_class == expected
    assert requires_verification(expected) == (expected in {"critical", "handwritten"})


def test_classify_primary_asset_skips_tiny_decorative() -> None:
    result = classify_image("scan.png", _bytes_len(100), "image/png", primary_asset=True)
    assert result.media_class == "illustrative"


# --- Parser / matrix rows ---


def test_matrix_docx_media_illustrative(client: TestClient, object_store: InMemoryObjectStore) -> None:
    figure = _bytes_len(600)
    docx = _minimal_docx("Policy body", {"figure.png": figure})
    object_id = _upload(client, filename="policy.docx", content=docx, content_type=_DOCX_CT)
    before = object_store.count()
    report = _run(client, object_id, "docs/policy.docx")["body"]
    assert object_store.count() > before
    media_att = [a for a in report["attachments"] if a["source_ref"].startswith("embedded:")]
    assert len(media_att) == 1
    assert media_att[0]["sha256"]
    assert media_att[0]["media_type"] == "image/png"
    assert media_att[0]["media_class"] == "illustrative"
    assert media_att[0]["verification_status"] == "not_required"
    assert report["status"] == "ready"


def test_matrix_pptx_media_staged_count(client: TestClient, object_store: InMemoryObjectStore) -> None:
    photo = _bytes_len(600)
    pptx = _minimal_pptx("Deck narrative", {"photo.png": photo})
    object_id = _upload(client, filename="deck.pptx", content=pptx, content_type=_PPTX_CT)
    before = object_store.count()
    report = _run(client, object_id, "decks/deck.pptx")["body"]
    assert object_store.count() == before + 1
    assert report["attachments"]
    assert report["attachments"][-1]["sha256"]


def test_matrix_pdf_xobject_extraction(client: TestClient) -> None:
    pdf_bytes = _pdf_with_embedded_image("diagram.png")
    parsed = pdf_parser.extract("diagram.pdf", pdf_bytes)
    assert len(parsed.embedded_media) >= 1
    assert parsed.embedded_media[0].data
    object_id = _upload(client, filename="diagram.pdf", content=pdf_bytes, content_type=_PDF_CT)
    report = _run(client, object_id, "drawings/diagram.pdf")["body"]
    embedded = [a for a in report["attachments"] if "diagram.png" in a["source_ref"]]
    assert embedded
    assert embedded[0]["sha256"]
    assert embedded[0]["media_type"] == "image/png"


def test_matrix_decorative_watermark_not_blocked(client: TestClient) -> None:
    docx = _minimal_docx("Visible text", {"header-watermark.png": _bytes_len(20_000)})
    object_id = _upload(client, filename="memo.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "memo.docx")["body"]
    wm = next(a for a in report["attachments"] if "watermark" in a["source_ref"])
    assert wm["media_class"] == "decorative"
    assert report["status"] == "ready"
    assert report["blockers"] == []
    assert "watermark" not in report["markdown"].lower()


def test_matrix_handwritten_blocked_pending(client: TestClient) -> None:
    tiny = _bytes_len(67)
    docx = _minimal_docx("Form", {"signature-scan.png": tiny})
    object_id = _upload(client, filename="form.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "forms/form.docx")["body"]
    assert report["status"] == "blocked"
    att = next(a for a in report["attachments"] if "signature" in a["source_ref"])
    assert att["media_class"] == "handwritten"
    assert att["verification_status"] == "pending"
    assert any(b["code"] == "MEDIA_VERIFICATION_PENDING" for b in report["blockers"])


def test_matrix_critical_tiny_blocked_pending(client: TestClient) -> None:
    docx = _minimal_docx("Report", {"chart-critical.png": _bytes_len(67)})
    object_id = _upload(client, filename="report.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "reports/report.docx")["body"]
    assert report["status"] == "blocked"
    att = next(a for a in report["attachments"] if "critical" in a["source_ref"])
    assert att["media_class"] == "critical"
    assert att["verification_status"] == "pending"


def test_matrix_substantive_large_generic(client: TestClient) -> None:
    docx = _minimal_docx("Manual", {"appendix.dat": _bytes_len(50_001)})
    object_id = _upload(client, filename="manual.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "manual.docx")["body"]
    att = next(a for a in report["attachments"] if "appendix" in a["source_ref"])
    assert att["media_class"] == "substantive"
    assert att["verification_status"] == "not_required"
    assert report["status"] == "ready"


def test_matrix_logo_large_decorative(client: TestClient) -> None:
    docx = _minimal_docx("Letter", {"corp-logo.png": _bytes_len(60_000)})
    object_id = _upload(client, filename="letter.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "letter.docx")["body"]
    att = next(a for a in report["attachments"] if "logo" in a["source_ref"])
    assert att["media_class"] == "decorative"
    assert report["status"] == "ready"


def test_pptx_slide_numeric_order() -> None:
    pptx = _pptx_multi_slide({10: "Tenth slide", 2: "Second slide"})
    result = pptx_parser.extract("order.pptx", pptx)
    pos_second = result.markdown_body.find("Second slide")
    pos_tenth = result.markdown_body.find("Tenth slide")
    assert pos_second != -1 and pos_tenth != -1
    assert pos_second < pos_tenth
    assert "## Slide 2" in result.markdown_body
    assert "## Slide 10" in result.markdown_body


def test_pdf_xobject_router_without_pillow() -> None:
    pdf_bytes = _pdf_with_embedded_image("Im0")
    result = extraction_router.extract("embed.pdf", _PDF_CT, pdf_bytes)
    assert result.embedded_media
    assert len(result.embedded_media[0].data) == 3


def test_pdf_dctdecode_media_type_jpeg() -> None:
    pdf_bytes = _pdf_with_embedded_image("photo.png", dct_decode=True, payload=b"\xff\xd8\xff")
    parsed = pdf_parser.extract("photo.pdf", pdf_bytes)
    assert parsed.embedded_media[0].media_type == "image/jpeg"


def test_http_pdf_critical_xobject_blocked(client: TestClient) -> None:
    pdf_bytes = _pdf_with_embedded_image("chart-critical.png")
    object_id = _upload(client, filename="chart.pdf", content=pdf_bytes, content_type=_PDF_CT)
    report = _run(client, object_id, "charts/chart.pdf")["body"]
    assert report["status"] == "blocked"
    att = report["attachments"][0]
    assert att["media_class"] == "critical"
    assert att["verification_status"] == "pending"
    assert any(b["code"] == "MEDIA_VERIFICATION_PENDING" for b in report["blockers"])