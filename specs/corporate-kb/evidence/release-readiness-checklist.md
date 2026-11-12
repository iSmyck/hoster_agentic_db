# Release Readiness Checklist

**Project:** corp_ai_db  
**Date:** 2026-11-12  
**Overall readiness:** 90 %  
**Target:** Minimal production launch under hoster.by white-label

## Executive summary

All in-progress action items are closed. The remaining 10 % is blocked on external owner/hoster inputs and production environment gates that cannot be resolved from the codebase alone. This checklist records what is ready, what is blocked, and the go/no-go criteria for launch.

## Phase status

| Phase | Status | Notes |
|-------|--------|-------|
| A — G1 vertical slice | DONE | T00–T09, T04a/T04b synthetic closures, A05–A10/A27–A30 fault matrix closed synthetically. Live destructive acceptance optional. |
| B — Identity/Retrieval live integration | DONE | ACT-006 live pgvector benchmark PASS (KIMI, 1024d, synthetic Russian corpus). |
| C — Ingestion/source connectors | backlog | Git-only source approved; external connectors deferred. C.1.1 MinIO staging done. |
| D — Backup/restore and DR | verified | D.1.1, D.1.2, D.2, D.4.1 done; HA/cross-site DR deferred. |
| E — Production hardening | done (minimal target) | ACT-008/009/010/011/012 closed. Full HA/AD/SLO/deep pen-test deferred. |

## Action items

| ID | Title | Status |
|----|-------|--------|
| ACT-001 | T04a live browser acceptance | done |
| ACT-002 | T04b lossless TipTap adapter | done |
| ACT-003 | Local stack smoke execution | done |
| ACT-004 | Full G1 live acceptance A01–A36 subset | done (synthetic) |
| ACT-005 | Identity service Keycloak/OpenLDAP live integration | done (sandbox) |
| ACT-006 | Retrieval service live pgvector benchmark | done |
| ACT-007 | Owner source/connector selection | done (Git-only) |
| ACT-008 | Backup encryption, retention and runbook decisions | done |
| ACT-009 | hoster.ai endpoint and model inputs | done (KIMI retained) |
| ACT-010 | Second-client deployment resources | done (sandbox spec) |
| ACT-011 | Production readiness decisions | done (minimal target) |
| ACT-012 | Open WebUI white-label logo/favicon decision | done (build config ready) |

## Pre-launch checks

### Engineering

- [x] `uv run pytest src/git-orchestrator/tests -q` — 73 passed.
- [x] `uv run pytest src/identity/tests -q` — passed (baseline).
- [x] `uv run pytest src/session/tests -q` — passed (baseline).
- [x] `uv run pytest src/retrieval/tests -q` — 43 passed, 4 skipped.
- [x] `cd src/open-webui && npm run kb:test` — 40 passed.
- [x] `cd src/open-webui && npm run kb:build` — succeeded.
- [x] `cd src/open-webui && WHITE_LABEL_LEGAL_CLEARANCE=1 npm run kb:build:white-label` — succeeded.
- [x] ACT-006 live pgvector benchmark PASS.
- [x] Runbooks created and reviewed.

### Security

- [x] XSS sanitization via DOMPurify in editor preview and document read view.
- [x] Actor mismatch / self-approval / idempotency guards in GO.
- [x] ACL-aware retrieval filtering.
- [x] Security review checklist created.
- [ ] External penetration test — deferred.
- [ ] Production object-store ACL engine recheck (T13/T16) — blocked.

### Operations

- [x] Backup and retention runbook created.
- [x] Incident response runbook created.
- [x] Rollback and recovery runbook created.
- [x] Monitoring/alerting checklist created.
- [x] Privileged bypass governance documented.
- [x] Internal sandbox tenant spec created.
- [ ] Production AD / live-SLO integration — blocked.
- [ ] HA PostgreSQL / cross-site DR — deferred.

## Go / no-go criteria

| Criterion | Status |
|-----------|--------|
| All in-progress action items closed | GO |
| G1 vertical slice complete | GO |
| Phase B live benchmark passed | GO |
| Minimal production runbooks in place | GO |
| White-label build configuration ready | GO |
| External pen-test completed | NO-GO until performed |
| Production object-store ACL recheck passed | NO-GO until T13/T16 unblocked |
| Production IdP / live SLO validated | NO-GO until AD integration unblocked |
| HA / cross-site DR ready | NO-GO (deferred) |

## Known risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Live destructive G1 acceptance not run | Medium | Synthetic fault matrix + happy-path live subset passed; full A01–A36 deferred to Phase E. |
| Object-store ACL production engine not rechecked | High | T13/T16 tracked as blocked; do not launch production multi-tenant until resolved. |
| Production AD / live SLO not integrated | High | Sandbox Keycloak is validated; production AD deferred. |
| HA / cross-site DR not implemented | High | Explicitly deferred by owner decision; single-node launch accepted. |
| hoster.ai integration deferred | Medium | KIMI retained as production provider; hoster.ai adapter future work. |
| Real white-label assets pending | Low | Build config ready; default Open WebUI branding fallback works. |

## Recommended next actions before launch

1. Resolve T13/T16 object-store ACL production engine recheck.
2. Complete production AD / live-SLO integration and validate Keycloak ↔ AD trust.
3. Perform external penetration test or accept documented risk.
4. Provision real logo/favicon assets and run `kb:build:white-label` with legal clearance.
5. Execute T18a/T18b multi-tenant validation against the internal sandbox tenant once resources are provisioned.

## Sign-off

This checklist is a machine-generated readiness snapshot. Owner sign-off is required on the blocked gates before launch.
