---
title: 'KBI-903 Identity and GO clients'
type: 'feature'
created: '2026-11-17'
status: 'done'
---

## Intent

**Problem:** Convert and source-sync talk to GO via a stub and never check Identity/AuthZ.

**Approach:** Wire `StubIdentityClient` / `HttpIdentityClient` and existing GO clients on app state. Enforce identity only when `KB_INGEST_REQUIRE_IDENTITY` is true so the synthetic suite stays default-allow.

## Boundaries & Constraints

**Always:**
- Default: identity not required; GO is stub unless `KB_INGEST_GO_BASE_URL` is set.
- When required: missing `X-Actor-Id` → 401 `IDENTITY_REQUIRED`; unapproved path → 403 `IDENTITY_DENIED`.
- HTTP clients are selected from settings, not hardcoded production hosts.

**Never:**
- Do not fail existing tests that omit the actor header.
- Do not call live Identity/GO in unit tests.

## Code Map

- `src/kb-ingestion/app/adapters/identity_client.py`
- `src/kb-ingestion/app/main.py` — `_default_go_client` / `_default_identity_client`
- `src/kb-ingestion/app/api/router.py` — convert, convert/run, sources, sync
- `src/kb-ingestion/tests/conftest.py` — autouse stub isolation

## Tasks & Acceptance

**Acceptance Criteria:**
- Given require_identity false, when convert upload runs without `X-Actor-Id`, then 201.
- Given require_identity true and no actor, when convert upload runs, then 401 IDENTITY_REQUIRED.
- Given require_identity true and stub deny, when convert upload runs, then 403 IDENTITY_DENIED and store count stays 0.
- Given `KB_INGEST_GO_BASE_URL` set, when create_app runs, then `HttpGOClient` is installed.
- Given `KB_INGEST_IDENTITY_BASE_URL` set, when create_app runs, then `HttpIdentityClient` is installed.

## Spec Change Log

- 2026-11-17: identity gate default-off; HTTP clients from settings.

## Review Triage Log

### 2026-11-17 — Review pass
- `[low]` `[patch]` invalid actor UUID → 400 INVALID_ACTOR_ID
- `[low]` `[defer]` structure/proposal routes not identity-gated — out of AC
- `[medium]` `[defer]` live Identity/GO HTTP — BLOCKED

## Auto Run Result

- Default-allow preserved; require_identity matrix covered.
- Verification: 211 passed; ruff clean.
