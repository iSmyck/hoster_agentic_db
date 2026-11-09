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
