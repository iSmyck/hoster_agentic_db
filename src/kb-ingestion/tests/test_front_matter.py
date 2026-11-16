"""KBI.1.5 front-matter-v2 draft schema matrix."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .test_convert import _minimal_docx, _run, _upload
from .test_media import _bytes_len

_DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_CONTRACTS = Path(__file__).resolve().parents[3] / "specs" / "corporate-kb" / "contracts"


def _validator() -> Draft202012Validator:
    fm_schema = json.loads((_CONTRACTS / "front-matter.schema.json").read_text())
    origin_schema = json.loads((_CONTRACTS / "source-origin.schema.json").read_text())
    registry = Registry().with_resources(
        [
            (
                "source-origin.schema.json",
                Resource.from_contents(origin_schema, default_specification=DRAFT202012),
            ),
            (
                "./source-origin.schema.json",
                Resource.from_contents(origin_schema, default_specification=DRAFT202012),
            ),
        ]
    )
    return Draft202012Validator(fm_schema, registry=registry)


def test_migrated_markdown_schema_valid(client: TestClient) -> None:
    object_id = _upload(
        client, filename="policy.md", content=b"# Policy\n\nAll good.", content_type="text/markdown"
    )
    report = _run(client, object_id, "docs/policy.md")["body"]
    draft = report["front_matter_draft"]
    _validator().validate(draft)
    assert draft["schema_version"] == "document-front-matter-v2"
    assert draft["parent_id"] is None
    assert draft["links"] == []
    assert draft["valid_until"] is None
    assert draft["archived"] is False
    assert draft["origin"]["ownership_mode"] == "migrated"


def test_attachments_schema_valid(client: TestClient) -> None:
    docx = _minimal_docx("Body", {"figure.png": _bytes_len(600)})
    object_id = _upload(client, filename="c.docx", content=docx, content_type=_DOCX_CT)
    draft = _run(client, object_id, "legal/c.docx")["body"]["front_matter_draft"]
    _validator().validate(draft)
    assert draft["attachments"]
    assert draft["attachments"][0]["description"]["automatic"] is True


def test_source_managed_requires_origin(client: TestClient) -> None:
    object_id = _upload(client, filename="x.md", content=b"# X", content_type="text/markdown")
    outcome = _run(client, object_id, "x.md", ownership_mode="source_managed", origin=None)
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "ORIGIN_REQUIRED"


def test_source_managed_mismatch_origin(client: TestClient) -> None:
    object_id = _upload(client, filename="x.md", content=b"# X", content_type="text/markdown")
    origin = {
        "schema_version": "source-origin-v1",
        "source_id": "src-1",
        "source_binding_id": "bind-1",
        "source_object_id": object_id,
        "source_version": "v1",
        "source_content_sha256": "a" * 64,
        "source_ref": "x.md",
        "observed_at": "2026-11-17T00:00:00+00:00",
        "ownership_mode": "migrated",
    }
    outcome = _run(client, object_id, "x.md", ownership_mode="source_managed", origin=origin)
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "FRONT_MATTER_INVALID"


def test_source_managed_matching_origin_schema_valid(client: TestClient) -> None:
    object_id = _upload(client, filename="x.md", content=b"# Managed", content_type="text/markdown")
    origin = {
        "schema_version": "source-origin-v1",
        "source_id": "src-1",
        "source_binding_id": "bind-1",
        "source_object_id": object_id,
        "source_version": "v1",
        "source_content_sha256": "a" * 64,
        "source_ref": "x.md",
        "observed_at": "2026-11-17T00:00:00+00:00",
        "ownership_mode": "source_managed",
    }
    report = _run(client, object_id, "x.md", ownership_mode="source_managed", origin=origin)["body"]
    draft = report["front_matter_draft"]
    assert draft["origin"]["ownership_mode"] == "source_managed"
    _validator().validate(draft)
