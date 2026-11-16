"""KBI.1.6 dry-run report, blockers, and no canonical write."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient
from kb_ingestion.app.parsers import pdf_parser
from kb_ingestion.app.services import converter as converter_mod

from .test_convert import _minimal_docx, _minimal_pdf, _run, _upload
from .test_media import _bytes_len

_DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_CONVERT_DIR = Path(__file__).resolve().parents[1] / "app"


def test_ready_markdown_report_shape(client: TestClient) -> None:
    object_id = _upload(
        client, filename="policy.md", content=b"# Policy\n\nAll good.", content_type="text/markdown"
    )
    report = _run(client, object_id, "docs/policy.md")["body"]
    assert report["path_map"] == {"docs/policy.md": object_id}
    assert report["attachments"] == []
    assert report["blockers"] == []
    assert report["losses"] == []
    assert report["errors"] == []
    assert report["correction_tasks"] == []
    assert report["status"] == "ready"
    assert "front_matter_draft" in report
    assert len(report["markdown_object_id"]) == 32


def test_pdf_empty_page_loss(client: TestClient) -> None:
    object_id = _upload(client, filename="a.pdf", content=_minimal_pdf(), content_type="application/pdf")
    report = _run(client, object_id, "a.pdf")["body"]
    assert any(item["kind"] == "empty_page" for item in report["losses"])


def test_blocked_media_correction_task_one_to_one(client: TestClient) -> None:
    docx = _minimal_docx("Form", {"signature-scan.png": _bytes_len(67)})
    object_id = _upload(client, filename="form.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "forms/form.docx")["body"]
    assert report["status"] == "blocked"
    assert len(report["blockers"]) == 1
    assert len(report["correction_tasks"]) == 1
    task = report["correction_tasks"][0]
    assert task["blocker_code"] == report["blockers"][0]["code"]
    assert task["document_path"] == "forms/form.docx"
    assert task["document_id"] == report["front_matter_draft"]["id"]
    assert task["reason"] == report["blockers"][0]["detail"]
    assert task["schema_version"] == "docops-correction-task-v1"
    assert task["state"] == "proposed_draft"
    att = report["attachments"][0]
    assert f"attachment://{att['object_id']}" in report["markdown"]


def test_two_pending_media_two_correction_tasks(client: TestClient) -> None:
    docx = _minimal_docx(
        "Form",
        {
            "signature-scan.png": _bytes_len(67),
            "chart-critical.png": _bytes_len(80),
        },
    )
    object_id = _upload(client, filename="form.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "forms/form.docx")["body"]
    assert report["status"] == "blocked"
    assert len(report["blockers"]) == 2
    assert len(report["correction_tasks"]) == 2
    codes = {task["blocker_code"] for task in report["correction_tasks"]}
    assert codes == {"MEDIA_VERIFICATION_PENDING"}


def test_convert_modules_do_not_import_git() -> None:
    forbidden = {"git", "gitlab", "git_orchestrator"}
    for path in _CONVERT_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
                assert names.isdisjoint(forbidden), path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden, path


def test_unreadable_pdf_image_records_error_not_500() -> None:
    from unittest.mock import patch

    class Boom:
        def get_data(self) -> bytes:
            raise OSError("fail")

        def get(self, key: str):
            return None

    payload = _minimal_pdf()
    with patch.object(pdf_parser, "_page_image_xobjects", return_value=[("Im0", Boom())]):
        result = pdf_parser.extract("a.pdf", payload)
    assert result.errors
    assert result.errors[0]["code"] == "PDF_IMAGE_UNREADABLE"
    assert result.embedded_media == []


def test_http_unreadable_pdf_image_returns_200(client: TestClient) -> None:
    from unittest.mock import patch

    class Boom:
        def get_data(self) -> bytes:
            raise OSError("fail")

        def get(self, key: str):
            return None

    object_id = _upload(client, filename="a.pdf", content=_minimal_pdf(), content_type="application/pdf")
    with patch.object(pdf_parser, "_page_image_xobjects", return_value=[("Im0", Boom())]):
        outcome = _run(client, object_id, "a.pdf")
    assert outcome["status"] == 200
    assert outcome["body"]["errors"]
    assert outcome["body"]["errors"][0]["code"] == "PDF_IMAGE_UNREADABLE"


def test_converter_module_has_no_git_symbol() -> None:
    assert not hasattr(converter_mod, "git")
