"""KBI.4 front-matter enforce, data barrier, and job queue."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from .test_convert import _run, _upload
from .test_source_sync import _doc, _register, _sync

_FM = "/api/kb/v1/ingest/validate/front-matter"
_BARRIER = "/api/kb/v1/ingest/validate/data-barrier"
_JOBS = "/api/kb/v1/ingest/jobs"
_TICK = "/api/kb/v1/ingest/jobs/tick"
_METRICS = "/api/kb/v1/ingest/jobs/metrics"


def _valid_fm(**overrides):
    draft = {
        "schema_version": "document-front-matter-v2",
        "id": "11111111-1111-1111-1111-111111111111",
        "title": "Policy",
        "parent_id": None,
        "ownership_mode": "migrated",
        "links": [],
        "valid_until": None,
        "archived": False,
        "attachments": [],
        "origin": {
            "schema_version": "source-origin-v1",
            "source_id": "src-1",
            "source_binding_id": "bind-1",
            "source_object_id": "obj-1",
            "source_version": "v1",
            "source_content_sha256": "a" * 64,
            "source_ref": "docs/a.md",
            "observed_at": "2026-11-17T00:00:00+00:00",
            "ownership_mode": "migrated",
        },
    }
    draft.update(overrides)
    return draft


def test_front_matter_valid(client: TestClient) -> None:
    response = client.post(_FM, json={"front_matter": _valid_fm()})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_front_matter_access_key_rejected(client: TestClient) -> None:
    draft = _valid_fm()
    draft["access"] = "everyone"
    response = client.post(_FM, json={"front_matter": draft})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FRONT_MATTER_INVALID"


def test_front_matter_additional_property_rejected(client: TestClient) -> None:
    draft = _valid_fm()
    draft["owner"] = "sales"
    response = client.post(_FM, json={"front_matter": draft})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FRONT_MATTER_INVALID"


def test_front_matter_source_managed_requires_origin(client: TestClient) -> None:
    draft = _valid_fm(ownership_mode="source_managed")
    draft.pop("origin")
    response = client.post(_FM, json={"front_matter": draft})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ORIGIN_REQUIRED"


def test_front_matter_archived_with_archive_valid(client: TestClient) -> None:
    draft = _valid_fm(
        archived=True,
        archive={
            "archived_at": "2026-11-17T00:00:00+00:00",
            "reason": "replaced",
            "replacement_document_id": None,
        },
    )
    response = client.post(_FM, json={"front_matter": draft})
    assert response.status_code == 200


def test_convert_pii_permitted_without_basis_rejected(client: TestClient) -> None:
    object_id = _upload(
        client,
        filename="ok.md",
        content=b"# Note\n\nAll good.\n",
        content_type="text/markdown",
    )
    outcome = _run(client, object_id, "docs/ok.md", data_profile="pii_permitted")
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "LEGAL_BASIS_REQUIRED"


def test_source_sync_external_egress_forbidden(client: TestClient) -> None:
    source_id = _register(
        client, data_profile="pii_permitted", legal_basis="synthetic-basis-1"
    )["body"]["source_id"]
    outcome = _sync(
        client,
        source_id,
        [_doc("a", "hello", markdown="hello", inference_provider="openai")],
    )
    assert outcome["body"]["outcomes"][0]["code"] == "EGRESS_FORBIDDEN"
    assert client.app.state.go_client.calls == []


def test_front_matter_archived_without_archive(client: TestClient) -> None:
    response = client.post(_FM, json={"front_matter": _valid_fm(archived=True)})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ARCHIVE_INVARIANT_VIOLATION"


def test_front_matter_archive_without_flag(client: TestClient) -> None:
    draft = _valid_fm(
        archive={
            "archived_at": "2026-11-17T00:00:00+00:00",
            "reason": "replaced",
            "replacement_document_id": None,
        }
    )
    response = client.post(_FM, json={"front_matter": draft})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ARCHIVE_INVARIANT_VIOLATION"


def test_data_barrier_strict_pii_creates_correction_task(client: TestClient) -> None:
    response = client.post(
        _BARRIER,
        json={"data_profile": "strict", "text": "Note SYNTHETIC_PII in fixture."},
    )
    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["code"] == "PII_BLOCKED"
    assert body["hits"][0]["kind"] == "canary"
    assert "excerpt" not in body["hits"][0]
    assert body["correction_task"]["blocker_code"] == "PII_REVIEW_REQUIRED"


def test_data_barrier_pii_permitted_requires_legal_basis(client: TestClient) -> None:
    response = client.post(
        _BARRIER,
        json={"data_profile": "pii_permitted", "text": "hello", "legal_basis": ""},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "LEGAL_BASIS_REQUIRED"


def test_data_barrier_external_provider_forbidden(client: TestClient) -> None:
    response = client.post(
        _BARRIER,
        json={
            "data_profile": "pii_permitted",
            "text": "hello SYNTHETIC_PII",
            "legal_basis": "synthetic-basis-1",
            "inference_provider": "external",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "EGRESS_FORBIDDEN"


def test_data_barrier_strict_clean_passes(client: TestClient) -> None:
    response = client.post(_BARRIER, json={"data_profile": "strict", "text": "# Policy\n\nAll good."})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_convert_run_blocks_strict_pii(client: TestClient) -> None:
    object_id = _upload(
        client,
        filename="pii.md",
        content=b"# Note\n\nSYNTHETIC_PII\n",
        content_type="text/markdown",
    )
    outcome = _run(client, object_id, "docs/pii.md")
    assert outcome["status"] == 200
    assert outcome["body"]["status"] == "blocked"
    assert {item["code"] for item in outcome["body"]["blockers"]} == {"PII_REVIEW_REQUIRED"}
    assert outcome["body"]["correction_tasks"][0]["blocker_code"] == "PII_REVIEW_REQUIRED"


def test_source_pii_permitted_requires_legal_basis(client: TestClient) -> None:
    outcome = _register(client, data_profile="pii_permitted", legal_basis=None)
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "LEGAL_BASIS_REQUIRED"


def test_source_sync_refuses_invalid_front_matter(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    draft = _valid_fm()
    draft["access"] = "everyone"
    outcome = _sync(client, source_id, [_doc("a", "hello", front_matter=draft)])
    assert outcome["status"] == 200
    assert outcome["body"]["outcomes"][0]["disposition"] == "refused"
    assert outcome["body"]["outcomes"][0]["code"] == "FRONT_MATTER_INVALID"
    assert client.app.state.go_client.calls == []


def test_source_sync_refuses_strict_pii_markdown(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "hello", markdown="see SYNTHETIC_PII")])
    assert outcome["body"]["outcomes"][0]["disposition"] == "refused"
    assert outcome["body"]["outcomes"][0]["code"] == "PII_BLOCKED"
    assert client.app.state.go_client.calls == []


def test_job_retry_then_done(client: TestClient) -> None:
    start = datetime(2026, 11, 17, tzinfo=UTC)
    created = client.post(
        _JOBS,
        json={"kind": "convert", "payload": {"path": "a.md"}, "now": start.isoformat()},
    ).json()
    first = client.post(
        _TICK, json={"now": start.isoformat(), "inject": "transient"}
    ).json()
    assert first["job"]["status"] == "retry"
    assert first["job"]["attempts"] == 1
    retry_at = datetime.fromisoformat(first["job"]["next_run_at"])
    assert retry_at == start + timedelta(seconds=1)
    too_soon = client.post(
        _TICK, json={"now": (start + timedelta(milliseconds=500)).isoformat()}
    ).json()
    assert too_soon["processed"] == 0
    second = client.post(
        _TICK, json={"now": retry_at.isoformat(), "inject": "none"}
    ).json()
    assert second["job"]["status"] == "done"
    assert second["job"]["job_id"] == created["job_id"]


def test_job_exhausted_to_dlq_sanitizes_reason(client: TestClient) -> None:
    start = datetime(2026, 11, 17, tzinfo=UTC)
    client.post(_JOBS, json={"kind": "convert", "max_attempts": 2, "now": start.isoformat()})
    client.post(_TICK, json={"now": start.isoformat(), "inject": "transient"})
    later = start + timedelta(seconds=1)
    dead = client.post(_TICK, json={"now": later.isoformat(), "inject": "transient"}).json()
    assert dead["job"]["status"] == "dead"
    assert dead["job"]["attempts"] == 2
    assert "user@example.com" not in dead["job"]["last_error"]


def test_job_permanent_failure_dead_and_redacted(client: TestClient) -> None:
    start = datetime(2026, 11, 17, tzinfo=UTC)
    client.post(_JOBS, json={"kind": "convert", "now": start.isoformat()})
    outcome = client.post(
        _TICK, json={"now": start.isoformat(), "inject": "permanent"}
    ).json()
    assert outcome["job"]["status"] == "dead"
    assert outcome["job"]["attempts"] == 1
    assert "[redacted-token]" in outcome["job"]["last_error"]
    assert "[redacted-email]" in outcome["job"]["last_error"]
    assert "secret-token" not in outcome["job"]["last_error"]


def test_job_metrics_lag_attempts_outcomes(client: TestClient) -> None:
    start = datetime(2026, 11, 17, tzinfo=UTC)
    stamp = start.isoformat()
    client.post(_JOBS, json={"kind": "a", "now": stamp})
    client.post(_JOBS, json={"kind": "b", "now": stamp})
    client.post(_JOBS, json={"kind": "c", "now": stamp})
    client.post(_TICK, json={"now": start.isoformat(), "inject": "none"})
    client.post(_TICK, json={"now": start.isoformat(), "inject": "permanent"})
    later = start + timedelta(seconds=30)
    metrics = client.get(_METRICS, params={"now": later.isoformat()}).json()
    assert metrics["done"] == 1
    assert metrics["dead"] == 1
    assert metrics["queued"] == 1
    assert metrics["attempts_total"] == 1
    assert metrics["outcomes"]["done"] == 1
    assert metrics["outcomes"]["dead"] == 1
    assert metrics["lag_seconds"] == 30
