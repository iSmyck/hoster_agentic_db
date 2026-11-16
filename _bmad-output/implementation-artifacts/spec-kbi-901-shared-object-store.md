---
title: 'KBI-901 Shared object-store module'
type: 'feature'
created: '2026-11-17'
status: 'done'
---

## Intent

**Problem:** Ingestion staging and backup both need object-store primitives; backup still hashes locally and ingestion has no MinIO path.

**Approach:** Keep the shared `ObjectStore` put/get protocol for ingestion, add an injectable MinIO adapter and quoted keys, and reuse `sha256_hex` from backup. Do not collapse backup's versioned MinIO API onto the ingestion port.

## Boundaries & Constraints

**Always:**
- Shared module owns `ObjectStore`, `InMemoryObjectStore`, `MinioObjectStore`, `object_key`, `sha256_hex`.
- Keys are `{quote(space)}/{quote(client)}/{quote(object)}` so slash ids do not collide.
- Backup continues to own versioned buckets/manifests; it only imports the hash helper.
- Empty MinIO endpoint → in-memory store.

**Never:**
- Do not rewrite backup `put_object` / version listing onto ingestion `put`/`get`.
- Do not claim live MinIO ACL PASS.
- Do not add a product schema.

## Code Map

- `src/shared/object_store/hashing.py` — `sha256_hex`, `object_key`
- `src/shared/object_store/store.py` — in-memory protocol
- `src/shared/object_store/minio_store.py` — injectable MinIO adapter
- `src/shared/object_store/factory.py` — `build_object_store`
- `src/backup/app/adapters/object_store.py` — hashes via `sha256_hex`
- `src/kb-ingestion/tests/test_cross_cutting.py` — collision, factory, round-trip

## Tasks & Acceptance

**Acceptance Criteria:**
- Given two different (space, client) pairs that would collide on raw `/` join, when both are stored, then get returns the matching payload.
- Given `KB_INGEST_MINIO_ENDPOINT` empty, when the app starts, then staging uses `InMemoryObjectStore`.
- Given an injected MinIO-like client, when put/get run, then bytes and sha256 round-trip.
- Given backup adapter put, when hashing, then it uses `shared.object_store.hashing.sha256_hex`.

## Spec Change Log

- 2026-11-17: quoted keys, MinIO adapter, backup hash helper.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- `[medium]` `[defer]` MinIO `version_id` is in-process `vN`, not bucket versioning — backup API stays separate
- `[low]` `[patch]` slash identity collision — `object_key` percent-encodes parts
- `[low]` `[reject]` fold backup `put_object` into shared `put` — different port (versions/manifests)

## Auto Run Result

- Shared protocol + injectable MinIO; backup 60 passed / 1 skipped after hash helper.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 211 passed; ruff clean.
- Live MinIO ACL not claimed.
