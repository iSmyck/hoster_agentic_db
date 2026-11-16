"""KBI.3 source-sync registry, delta, policy, notifications, scheduler."""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient
from kb_ingestion.app.adapters.go_client import StubGOClient

_SOURCES = "/api/kb/v1/ingest/sources"
_SUBS = "/api/kb/v1/ingest/notifications/subscriptions"
_TICK = "/api/kb/v1/ingest/scheduler/tick"


def _sha(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_body(**overrides):
    body = {
        "source_type": "n8n",
        "source_ref": "n8n:sales-wiki",
        "credentials_ref": "vault:n8n/sales-wiki",
        "poll_interval": 60,
        "space_id": "sales",
        "data_profile": "strict",
        "validation_required": False,
        "auto_merge": True,
        "trusted": True,
        "max_files_per_sync": 50,
        "max_lines_changed": 2000,
    }
    body.update(overrides)
    return body


def _register(client: TestClient, **overrides) -> dict:
    response = client.post(_SOURCES, json=_source_body(**overrides))
    return {"status": response.status_code, "body": response.json()}


def _doc(object_id: str, payload: str, **overrides) -> dict:
    item = {
        "source_object_id": object_id,
        "source_version": "v1",
        "sha256": _sha(payload),
        "path": f"docs/{object_id}.md",
        "action": "upsert",
        "ownership_mode": "source_managed",
        "lines_changed": 3,
        "tombstone": False,
    }
    item.update(overrides)
    return item


def _sync(client: TestClient, source_id: str, documents: list[dict]):
    response = client.post(f"{_SOURCES}/{source_id}/sync", json={"documents": documents})
    return {"status": response.status_code, "body": response.json()}


def test_register_trusted_auto_merge(client: TestClient) -> None:
    created = _register(client)
    assert created["status"] == 201
    body = created["body"]
    assert len(body["source_id"]) == 32
    assert body["auto_merge"] is True
    assert body["trusted"] is True
    fetched = client.get(f"{_SOURCES}/{body['source_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["credentials_ref"] == "vault:n8n/sales-wiki"


def test_auto_merge_requires_trusted(client: TestClient) -> None:
    outcome = _register(client, auto_merge=True, trusted=False)
    assert outcome["status"] == 400
    assert outcome["body"]["detail"]["code"] == "AUTO_MERGE_REQUIRES_TRUSTED"
    missing = client.get(f"{_SOURCES}/{'0' * 32}")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "SOURCE_NOT_FOUND"


def test_delta_created_noop_updated_deleted(client: TestClient) -> None:
    source_id = _register(client, auto_merge=False)["body"]["source_id"]
    first = _sync(client, source_id, [_doc("a", "hello")])
    assert first["status"] == 200
    assert first["body"]["changes"][0]["kind"] == "created"
    same = _sync(client, source_id, [_doc("a", "hello")])
    assert same["body"]["changes"][0]["kind"] == "noop"
    assert same["body"]["outcomes"][0]["disposition"] == "noop"
    changed = _sync(client, source_id, [_doc("a", "hello world", source_version="v2")])
    assert changed["body"]["changes"][0]["kind"] == "updated"
    deleted = _sync(
        client,
        source_id,
        [_doc("a", "hello world", action="delete", tombstone=True, source_version="v3")],
    )
    assert deleted["body"]["changes"][0]["kind"] == "deleted"
    assert deleted["body"]["outcomes"][0]["go_proposal_id"]


def test_version_change_same_hash_is_updated(client: TestClient) -> None:
    source_id = _register(client, auto_merge=False)["body"]["source_id"]
    _sync(client, source_id, [_doc("a", "hello", source_version="v1")])
    again = _sync(client, source_id, [_doc("a", "hello", source_version="v2")])
    assert again["body"]["changes"][0]["kind"] == "updated"


def test_path_change_same_hash_is_updated(client: TestClient) -> None:
    source_id = _register(client, auto_merge=False)["body"]["source_id"]
    _sync(client, source_id, [_doc("a", "hello", path="docs/a.md")])
    again = _sync(client, source_id, [_doc("a", "hello", path="docs/renamed.md")])
    assert again["body"]["changes"][0]["kind"] == "updated"


def test_register_callback_source(client: TestClient) -> None:
    created = _register(client, source_type="callback", source_ref="callback:sales")
    assert created["status"] == 201
    assert created["body"]["source_type"] == "callback"


def test_register_rejects_invalid_poll_interval(client: TestClient) -> None:
    outcome = _register(client, poll_interval=0)
    assert outcome["status"] == 422


def test_unknown_source_sync_not_found(client: TestClient) -> None:
    outcome = _sync(client, "0" * 32, [_doc("a", "x")])
    assert outcome["status"] == 404
    assert outcome["body"]["detail"]["code"] == "SOURCE_NOT_FOUND"


def test_auto_merge_records_source_sync_actor(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "policy")])
    result = outcome["body"]["outcomes"][0]
    assert result["disposition"] == "merged"
    assert result["actor_type"] == "source_sync"
    go_client = client.app.state.go_client
    assert isinstance(go_client, StubGOClient)
    assert go_client.calls[0]["proposal_data"]["actor_type"] == "source_sync"
    assert go_client.merges == [result["go_proposal_id"]]
    assert go_client.decisions[0]["decision_data"]["actor_type"] == "source_sync"
    assert go_client.decisions[0]["decision_data"]["rationale"] == "auto-merge per source policy"
    trailers = go_client.decisions[0]["decision_data"]["trailers"]
    assert trailers["Source-Sync-Id"] == source_id
    assert trailers["Source-Version"] == "v1"
    assert trailers["Sync-Run-Id"] == outcome["body"]["sync_run_id"]
    origin = go_client.calls[0]["proposal_data"]["origin"]
    assert origin["schema"] == "source-origin-v1"
    assert origin["source_id"] == source_id
    assert origin["source_content_sha256"] == _sha("policy")


def test_migrated_ownership_can_auto_merge(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "old", ownership_mode="migrated")])
    assert outcome["body"]["outcomes"][0]["disposition"] == "merged"
    assert client.app.state.go_client.merges


def test_validation_required_stays_human_review(client: TestClient) -> None:
    source_id = _register(client, validation_required=True)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "policy")])
    assert outcome["body"]["outcomes"][0]["disposition"] == "human_review"
    assert client.app.state.go_client.merges == []
    assert client.app.state.go_client.calls
    assert client.app.state.notifier.deliveries == []


def test_unknown_delete_is_noop(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    outcome = _sync(
        client,
        source_id,
        [_doc("missing", "gone", action="delete", tombstone=True)],
    )
    assert outcome["body"]["changes"][0]["kind"] == "noop"
    assert outcome["body"]["outcomes"][0]["disposition"] == "noop"
    assert client.app.state.go_client.calls == []


def test_line_bounds_exceeded_falls_back_to_review(client: TestClient) -> None:
    source_id = _register(client, max_lines_changed=5)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "one", lines_changed=9)])
    assert outcome["body"]["outcomes"][0]["code"] == "BOUND_EXCEEDED"
    assert outcome["body"]["outcomes"][0]["disposition"] == "human_review"


def test_bounds_exceeded_falls_back_to_review(client: TestClient) -> None:
    source_id = _register(client, max_files_per_sync=1)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "one"), _doc("b", "two")])
    assert {item["code"] for item in outcome["body"]["outcomes"]} == {"BOUND_EXCEEDED"}
    assert {item["disposition"] for item in outcome["body"]["outcomes"]} == {"human_review"}
    assert client.app.state.go_client.merges == []


def test_live_operational_forbidden(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "api", ownership_mode="live_operational")])
    result = outcome["body"]["outcomes"][0]
    assert result["disposition"] == "refused"
    assert result["code"] == "LIVE_OPERATIONAL_FORBIDDEN"
    assert client.app.state.go_client.calls == []


def test_sync_in_progress_conflict(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    client.app.state.source_sync._running.add(source_id)
    outcome = _sync(client, source_id, [_doc("a", "x")])
    assert outcome["status"] == 409
    assert outcome["body"]["detail"]["code"] == "SYNC_IN_PROGRESS"


def test_sync_go_failure(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    client.app.state.go_client.fail_message = "upstream down"
    outcome = _sync(client, source_id, [_doc("a", "x")])
    assert outcome["status"] == 502
    assert outcome["body"]["detail"]["code"] == "GO_SUBMIT_FAILED"


def test_sync_go_empty_id_fails(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    client.app.state.go_client.return_empty_id = True
    outcome = _sync(client, source_id, [_doc("a", "x")])
    assert outcome["status"] == 502
    assert outcome["body"]["detail"]["code"] == "GO_SUBMIT_FAILED"


def test_queued_job_marked_failed_on_go_error(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    client.post(_TICK, json={"now": "2026-11-17T00:00:00+00:00"})
    client.app.state.go_client.fail_message = "upstream down"
    outcome = _sync(client, source_id, [_doc("a", "x")])
    assert outcome["status"] == 502
    jobs = [
        job for job in client.app.state.source_sync._jobs.values() if job.source_id == source_id
    ]
    assert jobs[0].status == "failed"


def test_curated_document_protected(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    outcome = _sync(client, source_id, [_doc("a", "curated", ownership_mode="curated")])
    result = outcome["body"]["outcomes"][0]
    assert result["disposition"] == "refused"
    assert result["code"] == "CURATED_DOCUMENT_PROTECTED"
    assert client.app.state.go_client.calls == []


def test_delete_without_tombstone_refused(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    _sync(client, source_id, [_doc("a", "keep")])
    client.app.state.go_client.calls.clear()
    outcome = _sync(client, source_id, [_doc("a", "keep", action="delete", tombstone=False)])
    assert outcome["body"]["outcomes"][0]["code"] == "TOMBSTONE_REQUIRED"
    assert client.app.state.go_client.calls == []


def test_notification_on_proven_merge(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    client.post(
        _SUBS,
        json={
            "editor_stable_id": "editor-1",
            "space_id": "sales",
            "path": "docs",
            "channel": "log",
        },
    )
    _sync(client, source_id, [_doc("a", "policy")])
    deliveries = client.app.state.notifier.deliveries
    assert deliveries
    assert deliveries[0].status == "sent"
    assert deliveries[0].editor_stable_id == "editor-1"


def test_notification_failure_retries_without_rollback(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    client.post(
        _SUBS,
        json={
            "editor_stable_id": "editor-1",
            "space_id": "sales",
            "path": "docs/a.md",
            "channel": "webhook",
        },
    )
    client.app.state.notifier.fail_next = 2
    outcome = _sync(client, source_id, [_doc("a", "policy")])
    assert outcome["body"]["outcomes"][0]["disposition"] == "merged"
    assert client.app.state.go_client.merges
    delivery = client.app.state.notifier.deliveries[0]
    assert delivery.status == "sent"
    assert delivery.attempts == 3


def test_notification_exhausted_does_not_rollback_merge(client: TestClient) -> None:
    source_id = _register(client)["body"]["source_id"]
    client.post(
        _SUBS,
        json={
            "editor_stable_id": "editor-1",
            "space_id": "sales",
            "path": "docs/a.md",
            "channel": "webhook",
        },
    )
    client.app.state.notifier.fail_next = 5
    outcome = _sync(client, source_id, [_doc("a", "policy")])
    assert outcome["body"]["outcomes"][0]["disposition"] == "merged"
    assert client.app.state.go_client.merges
    assert client.app.state.notifier.failures
    assert client.app.state.notifier.failures[0].status == "failed"


def test_scheduler_queues_at_interval_and_dedupes_overlap(client: TestClient) -> None:
    source_id = _register(client, poll_interval=60)["body"]["source_id"]
    first = client.post(_TICK, json={"now": "2026-11-17T00:00:00+00:00"}).json()
    queued = [job for job in first["jobs"] if job["status"] == "queued"]
    assert len(queued) == 1
    assert queued[0]["source_id"] == source_id
    too_soon = client.post(_TICK, json={"now": "2026-11-17T00:00:30+00:00"}).json()
    assert too_soon["skipped_source_ids"] == [source_id]
    assert any(job["status"] == "skipped" for job in too_soon["jobs"])
    _sync(client, source_id, [_doc("a", "x")])
    not_due = client.post(_TICK, json={"now": "2026-11-17T00:00:45+00:00"}).json()
    assert not_due["jobs"] == []
    later = client.post(_TICK, json={"now": "2026-11-17T00:01:00+00:00"}).json()
    assert [job["source_id"] for job in later["jobs"] if job["status"] == "queued"] == [source_id]


def test_scheduler_skips_running_source(client: TestClient) -> None:
    source_id = _register(client, poll_interval=1)["body"]["source_id"]
    client.app.state.source_sync._running.add(source_id)
    tick = client.post(_TICK, json={"now": "2026-11-17T00:00:00+00:00"}).json()
    assert source_id in tick["skipped_source_ids"]
    assert any(job["status"] == "skipped" for job in tick["jobs"])


def test_scheduler_rejects_invalid_now(client: TestClient) -> None:
    _register(client)
    response = client.post(_TICK, json={"now": "not-a-timestamp"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
