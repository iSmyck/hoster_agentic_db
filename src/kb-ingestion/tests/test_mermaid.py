"""KBI.5 diagram detection, Mermaid generation, Kroki, evidence gate."""

from __future__ import annotations

from fastapi.testclient import TestClient
from kb_ingestion.app.services.media_processor import classify_image

from .test_convert import _minimal_docx, _run, _upload
from .test_media import _bytes_len

_DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_ACTIVATE = "/api/kb/v1/ingest/mermaid/activate"
_STATUS = "/api/kb/v1/ingest/mermaid/status"


def _enable_mermaid(client: TestClient) -> None:
    route = client.app.state.mermaid_route
    route.vision.configured = True
    route.kroki.available = True
    outcome = client.post(_ACTIVATE, json={"human_spot_check": True, "license_ok": True})
    assert outcome.status_code == 200
    assert outcome.json()["enabled"] is True


def test_diagram_candidate_from_heuristics() -> None:
    diagram = classify_image("wiring-schematic.png", _bytes_len(200), "image/png")
    assert diagram.diagram_candidate is True
    assert diagram.media_class == "critical"
    figure = classify_image("figure.png", _bytes_len(1024), "image/png")
    assert figure.diagram_candidate is False
    assert figure.media_class == "illustrative"
    critical = classify_image("chart-critical.png", _bytes_len(67), "image/png")
    assert critical.diagram_candidate is False
    assert critical.media_class == "critical"


def test_disabled_route_keeps_image_and_alt(client: TestClient) -> None:
    status = client.get(_STATUS).json()
    assert status["enabled"] is False
    assert "VISION_PROVIDER_MISSING" in status["reasons"]
    docx = _minimal_docx("Body", {"wiring-schematic.png": _bytes_len(800)})
    object_id = _upload(client, filename="d.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "docs/d.docx")["body"]
    att = next(a for a in report["attachments"] if "schematic" in a["source_ref"])
    assert att["diagram_candidate"] is True
    assert att["mermaid_status"] == "skipped"
    assert att["mermaid_source"] is None
    assert "attachment://" in report["markdown"]
    assert "```mermaid" not in report["markdown"]


def test_activate_requires_all_gates(client: TestClient) -> None:
    missing = client.post(_ACTIVATE, json={"human_spot_check": True, "license_ok": True}).json()
    assert missing["enabled"] is False
    assert "VISION_PROVIDER_MISSING" in missing["reasons"]
    client.app.state.mermaid_route.vision.configured = True
    client.app.state.mermaid_route.kroki.available = True
    no_spot = client.post(_ACTIVATE, json={"human_spot_check": False, "license_ok": True}).json()
    assert no_spot["enabled"] is False
    assert "HUMAN_SPOT_CHECK_REQUIRED" in no_spot["reasons"]
    no_license = client.post(_ACTIVATE, json={"human_spot_check": True, "license_ok": False}).json()
    assert no_license["enabled"] is False
    assert "LICENSE_CHECK_FAILED" in no_license["reasons"]


def test_enabled_route_generates_mermaid_linked_to_image(client: TestClient) -> None:
    _enable_mermaid(client)
    docx = _minimal_docx("Body", {"wiring-schematic.png": _bytes_len(800)})
    object_id = _upload(client, filename="d.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "docs/d.docx")["body"]
    att = next(a for a in report["attachments"] if "schematic" in a["source_ref"])
    assert att["automatic"] is True
    assert att["diagram_candidate"] is True
    assert att["mermaid_status"] == "validated"
    assert att["mermaid_source"] == "flowchart LR\n  X-->Y"
    assert att["object_id"]
    assert "```mermaid" in report["markdown"]
    assert "flowchart LR" in report["markdown"]
    assert report["status"] == "ready"
    assert report["errors"] == []


def test_kroki_failure_preserves_image(client: TestClient) -> None:
    _enable_mermaid(client)
    client.app.state.mermaid_route.kroki.fail_next = True
    docx = _minimal_docx("Body", {"wiring-schematic.png": _bytes_len(800)})
    object_id = _upload(client, filename="d.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "docs/d.docx")["body"]
    att = next(a for a in report["attachments"] if "schematic" in a["source_ref"])
    assert att["mermaid_status"] == "invalid"
    assert att["mermaid_source"] is None
    assert "attachment://" in report["markdown"]
    assert "```mermaid" not in report["markdown"]
    assert {item["code"] for item in report["errors"]} == {"MERMAID_INVALID"}
    assert att["object_id"]


def test_invalid_vision_output_discarded(client: TestClient) -> None:
    _enable_mermaid(client)
    client.app.state.mermaid_route.vision.invalid_next = True
    docx = _minimal_docx("Body", {"flowchart-diagram.png": _bytes_len(800)})
    object_id = _upload(client, filename="d.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "docs/d.docx")["body"]
    att = next(a for a in report["attachments"] if "diagram" in a["source_ref"])
    assert att["mermaid_status"] == "invalid"
    assert att["mermaid_source"] is None
    assert "attachment://" in report["markdown"]


def test_non_diagram_does_not_call_vision(client: TestClient) -> None:
    _enable_mermaid(client)
    client.app.state.mermaid_route.vision.calls.clear()
    docx = _minimal_docx("Body", {"figure.png": _bytes_len(800)})
    object_id = _upload(client, filename="d.docx", content=docx, content_type=_DOCX_CT)
    report = _run(client, object_id, "docs/d.docx")["body"]
    att = next(a for a in report["attachments"] if "figure" in a["source_ref"])
    assert att["diagram_candidate"] is False
    assert att["mermaid_status"] == "none"
    assert client.app.state.mermaid_route.vision.calls == []


def test_golden_failure_blocks_activation(client: TestClient) -> None:
    route = client.app.state.mermaid_route
    route.vision.configured = True
    route.kroki.available = True
    route.vision.invalid_next = True
    outcome = client.post(_ACTIVATE, json={"human_spot_check": True, "license_ok": True}).json()
    assert outcome["enabled"] is False
    assert "GOLDEN_FIXTURES_FAILED" in outcome["reasons"]
