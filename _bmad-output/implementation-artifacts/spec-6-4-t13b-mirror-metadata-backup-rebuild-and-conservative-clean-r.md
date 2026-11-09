---
title: 'T13b Mirror/metadata backup, rebuild and conservative clean restore'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/export-manifest.schema.json
  - specs/corporate-kb/contracts/docops-correction-task.schema.json
  - specs/corporate-kb/contracts/index-snapshot.schema.json
  - specs/corporate-kb/database.md
  - specs/corporate-kb/components/git-orchestrator.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-6-context.md
  - _bmad-output/implementation-artifacts/spec-4-7-t07b-docops-review-projections-correction-tasks-and-ux-telem.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that the Space can be mirrored, that GitLab MR/note/audit metadata and immutable objects are backed up separately from secrets, that a clean isolated instance can rebuild `kb_authz`, `kb_ops`, and `kb_index` from Git + approved config, and that correction-task state is restored and reconciled without fabricating or deleting canonical writes.

**Approach:** Create a T13b harness that exercises synthetic YAML fixtures for Git mirror completeness, protected tag preservation, metadata backup, immutable object backup, conservative rebuild semantics, clean-isolated restore, and correction-task backup reconciliation using the `docops-correction-task-v1` contract.

## Boundaries & Constraints

**Always:**
- Backup covers Git mirror of all refs/objects, protected decision/cutover tags, GitLab MR/note/audit metadata, immutable objects, nonsecret config and a separately controlled secrets recovery policy.
- Restore is proven on a clean isolated instance with no inherited active grants, pointer or operational rows.
- `kb_authz` is rebuilt from Git policy plus fresh IdP data; Git-derived `kb_ops` from MRs/notes/tags/history/source registry under a global merge freeze with conservative per-target barriers; `kb_index` from Git plus immutable assets and approved config.
- Correction tasks are restored separately with hash/event-sequence/perimeter checks and linked-MR reconciliation.
- Unknown merge outcomes remain quarantined; missing assets, grants or closure block READY.
- Rebuild semantics are conservative: unknown outcomes are not cleared by an empty database, terminal label, superseded decision or generic TTL; file/dump existence alone is not a restore PASS.

**Never:**
- Do not use real backups, credentials, or production instances.
- Do not restore active AuthzContext or active pointer as canonical truth from an unverified backup.
- Do not fabricate or delete canonical writes during correction-task reconciliation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Git mirror | All refs/objects and protected tags | Mirror contains exact full SHAs and protected tags | Missing ref/tag → FAIL |
| Metadata backup | MR/note/audit metadata captured | GitLab metadata present and consistent | Missing metadata → FAIL |
| Object backup | Immutable/versioned objects with hashes | Object versions/hashes match manifest | Mutable/missing object → FAIL |
| Secrets separation | Secrets recovery policy separately controlled | No secrets in ordinary backup/export | Secret leak → FAIL |
| kb_authz rebuild | Git policy + fresh IdP | Rebuilt from canonical policy and current IdP | Inherited grants used as truth → FAIL |
| kb_ops rebuild | MRs/notes/tags/history/source registry | Rebuilt under global merge freeze with per-target barriers | Unknown outcomes cleared automatically → FAIL |
| kb_index rebuild | Git + immutable assets + approved config | Index rebuilt without canonical Git mutation | Active pointer restored as truth → FAIL |
| Correction-task restore | Non-Git-derived operational backup | Hash/event-sequence/perimeter checks and linked-MR reconciliation | Fabrication/deletion of canonical writes → FAIL |
| Clean isolated instance | No inherited rows/grants/pointer | Restore proven from scratch | Inherited state used as truth → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t13b/run_t13b_tests.py` — main harness.
- `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml` — synthetic backup/restore/rebuild/fixture scenarios.
- `specs/corporate-kb/contracts/export-manifest.schema.json` — export/closure contract.
- `specs/corporate-kb/contracts/docops-correction-task.schema.json` — correction-task contract.
- `specs/corporate-kb/database.md` — schema ownership and rebuild semantics.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t13b/run_t13b_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t13b/restore-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t13b/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `6-4-t13b-...` → `done`.

**Acceptance Criteria:**
- [x] Given a backup, the Git mirror contains all refs/objects and protected decision/cutover tags with exact full SHAs.
- [x] Given metadata backup, GitLab MR/note/audit metadata is captured and consistent.
- [x] Given object backup, immutable/versioned objects match the assets manifest hashes; secrets are stored under a separately controlled recovery policy.
- [x] Given a clean isolated instance, `kb_authz` rebuilds from Git policy plus fresh IdP data with no inherited active grants.
- [x] Given a clean isolated instance, Git-derived `kb_ops` rebuilds from MRs/notes/tags/history/source registry under a global merge freeze with conservative per-target barriers.
- [x] Given a clean isolated instance, `kb_index` rebuilds from Git plus immutable assets and approved config without mutating canonical Git.
- [x] Given correction-task operational backup, restore uses hash/event-sequence/perimeter checks and linked-MR reconciliation without fabricating or deleting canonical writes.
- [x] Given unknown merge outcomes, empty database, terminal label, superseded decision or generic TTL, the outcome remains quarantined and is not auto-cleared.
- [x] Given missing assets, grants or closure, the restore state is not READY.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Live backup/restore/rebuild on real GitLab/PostgreSQL/object-store/IdP remains BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the backup set and restore procedure on a clean isolated instance, validating that each projection is rebuilt only from its owning source and that unknown outcomes remain quarantined. Correction-task reconciliation follows the `docops-correction-task-v1` contract without creating a second canonical write path. Real backup/restore drills remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t13b/run_t13b_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t13b/run_t13b_tests.py` -- expected: writes `restore-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t13b/restore-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t13b/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
