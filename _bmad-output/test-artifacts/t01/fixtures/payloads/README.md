# T01 synthetic fixtures

This directory contains static YAML/JSON payloads for the contract-test vectors
that can be checked without a live GitLab/IdP/CI/hoster.ai sandbox. Runtime-only
vectors (cross-Space API fan-out, MR lifecycle, idempotency registry, DB foreign
keys, source connector bindings, etc.) are exercised as `BLOCKED` checks in the
harness with synthetic in-memory state; they do not have static payloads because
they require a running GO backend and real sandboxes.

All stable IDs and synthetic hashes come from
`specs/corporate-kb/contracts/t01-contract-tests.yaml`.

| Fixture | CF vector | Purpose |
|---------|-----------|---------|
| `cf01_authz_context_*.yaml` | CF-01 | Two distinct per-Space AuthzContext fixtures |
| `cf02_approval_policy_*.yaml` | CF-02 | Valid, duplicate-prefix and Cyrillic-NFC/NFD policy bundles |
| `cf03_front_matter_*.yaml` | CF-03 | Archive bidirectional invariant cases |
| `cf04_*` | CF-04 | Migrated front matter without origin; live_operational source origin |
| `cf05_*` | CF-05 | DOC-0001 preserved vs lowercase rewrite |
| `cf11_index_snapshot_requested_serving.yaml` | CF-11 | Preflight `serving_allowed=true` while `state=requested` |
| `cf11_index_snapshot_active_null_hash.yaml` | CF-11 | Active descriptor with null `projection_sha256` |
| `cf11_index_snapshot_incremental_missing.yaml` | CF-11 | Active incremental with nonempty `missing_inputs` |
| `cf19_proposal_record_bad_line_range.yaml` | CF-19 | Invalid line range schema case |
| `cf28_paths.yaml` | CF-28 | Absolute/relative, ambiguous and NFC/NFD path vectors |
