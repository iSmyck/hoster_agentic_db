## Deferred from: code review of spec-1-1-t01-reproducible-two-space-sandbox-and-executable-defect-evi.md (2026-11-08)

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-t01-reproducible-two-space-sandbox-and-executable-defect-evi.md`
  summary: Dynamic catalog-driven execution for T01 contract vectors.
  evidence: Harness currently maps CF vectors to hardcoded functions instead of interpreting `t01-contract-tests.yaml` at runtime. Requires stable runner contract and GO backend availability.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-t01-reproducible-two-space-sandbox-and-executable-defect-evi.md`
  summary: Live GitLab API provisioning of two-Space fixtures.
  evidence: `sandbox.py` is a stub returning BLOCKED. Requires live GitLab/IdP/CI sandbox and credentials.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-t01-reproducible-two-space-sandbox-and-executable-defect-evi.md`
  summary: CF-20 idempotency collision runtime checks.
  evidence: No synthetic collision test implemented. Requires GO backend and idempotency registry.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-t01-reproducible-two-space-sandbox-and-executable-defect-evi.md`
  summary: CF-01 cross-Space reuse/fan-out runtime checks.
  evidence: Only structural distinctness verified. Requires live GitLab/AuthZ sandbox.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-t01-reproducible-two-space-sandbox-and-executable-defect-evi.md`
  summary: Full CF-06/CF-07/CF-10/CF-12–CF-24 runtime lifecycle checks.
  evidence: Currently marked BLOCKED/NOT_EXECUTED. Requires GO backend and canonical store.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-t01-reproducible-two-space-sandbox-and-executable-defect-evi.md`
  summary: Unit tests for T01 validators, reporters, and sandbox modules.
  evidence: Deferred until baseline test runner (pytest/pyproject.toml) is configured in T00/T01.

## Deferred from: code review of spec-b1-identity-service-live-integration.md (2026-11-10)

- source_spec: `_bmad-output/implementation-artifacts/spec-b1-identity-service-live-integration.md`
  summary: Race window between SELECT and UPDATE in `recheck_group_membership`.
  evidence: A concurrent insert of a matching snapshot between read and expire would remain valid. Requires `SELECT ... FOR UPDATE` or atomic DB-level operation.

- source_spec: `_bmad-output/implementation-artifacts/spec-b1-identity-service-live-integration.md`
  summary: `setup_keycloak.py` re-fetches IDs with a second GET after POST instead of using the `Location` header.
  evidence: Current approach is idempotent and works; optimization is low value.

- source_spec: `_bmad-output/implementation-artifacts/spec-b1-identity-service-live-integration.md`
  summary: `test_keycloak_live.py` falls back to hardcoded `admin`/`admin` Keycloak admin credentials.
  evidence: Sandbox-only test fixture; acceptable for local smoke but should be removed before production test hardening.

## Deferred from: code review of spec-b2-session-service.md (2026-11-10)

- source_spec: `_bmad-output/implementation-artifacts/spec-b2-session-service.md`
  summary: Refresh tokens are not rotated on refresh.
  evidence: Current design invalidates old access token via JTI rotation; refresh-token rotation is future hardening.

- source_spec: `_bmad-output/implementation-artifacts/spec-b2-session-service.md`
  summary: No rate limiting, brute-force protection, or structured audit logging on session endpoints.
  evidence: Out of scope for initial Session service; add when auth hardening phase begins.

- source_spec: `_bmad-output/implementation-artifacts/spec-b2-session-service.md`
  summary: No automated cleanup of expired sessions.
  evidence: Requires background job design; table will grow until cleanup is implemented.

- source_spec: `_bmad-output/implementation-artifacts/spec-b2-session-service.md`
  summary: `revoke_all_for_user` loads matching rows into memory before updating.
  evidence: Acceptable for expected scale; switch to bulk UPDATE if scale grows.

## Deferred from: code review of spec-b3-retrieval-live-integration.md (2026-11-10)

- source_spec: `_bmad-output/implementation-artifacts/spec-b3-retrieval-live-integration.md`
  summary: `SearchLog` writes into `kb_index` schema, violating ADR-015 single-writer matrix.
  evidence: Pre-existing issue in `src/retrieval/app/services/search.py`; requires separate refactoring to move audit logs out of `kb_index`.

- source_spec: `_bmad-output/implementation-artifacts/spec-b3-retrieval-live-integration.md`
  summary: Retrieval AuthZ only exercises path-approver check, not full `AuthzContext` epoch/policy contract.
  evidence: `src/retrieval/app/services/search.py` calls `identity_client.check_path` and only checks `approved`; depends on hardened AuthZ contract.

- source_spec: `_bmad-output/implementation-artifacts/spec-b3-retrieval-live-integration.md`
  summary: Smoke/live tests do not fully verify ACL matrix (approver access to `/secret`, reader access to `docs/restricted.md`).
  evidence: Coverage gap in `src/retrieval/scripts/smoke_retrieval.py` and `src/retrieval/tests/test_retrieval_live.py`; not a functional defect.
