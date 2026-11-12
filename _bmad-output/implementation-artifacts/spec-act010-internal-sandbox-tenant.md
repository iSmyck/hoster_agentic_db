---
title: 'ACT-010 — Internal sandbox tenant specification for multi-tenant validation'
type: 'chore'
created: '2026-11-12'
status: 'done'
baseline_revision: 'bd55bd82a65c210d3216313bac81f99d1db8bdce'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Owner approved an internal sandbox tenant for multi-tenant validation (ACT-010). We need a concrete tenant isolation specification and provisioning checklist so T18a/T18b can be validated without waiting for an external client.

**Approach:** Document tenant naming, isolation boundaries, and provisioning steps for GitLab, PostgreSQL, object store, and Keycloak. Create a reusable spec/checklist and a lightweight provisioning script skeleton. Update sprint status.

## Boundaries & Constraints

**Always:**
- Use synthetic tenant names (e.g., `tenant-sandbox-01`) and placeholder domains.
- Keep the spec aligned with the minimal production target (single-node PostgreSQL, daily backups, basic monitoring).
- Reference existing architecture decisions (G1-D6, D3-DEC1–4, ADR-019).
- Record evidence under `specs/corporate-kb/evidence/phase-e/`.

**Never:**
- Provision real production resources or commit credentials.
- Invent new multi-tenant authorization semantics beyond existing Space-scoped ACLs.
- Claim multi-tenant validation is complete from documentation alone.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tenant provisioning | Follow checklist | All isolation layers configured | Record deviations |
| Cross-tenant leak | User from tenant A queries tenant B | AuthZ rejects per Space/tenant ACL | Document in validation report |
| Shared infrastructure | Same PostgreSQL/MinIO/Keycloak instance | Tenant data isolated by schema/bucket/realm | Document shared-resource risks |

## Code Map

- `specs/corporate-kb/adr/` -- architecture decisions that constrain tenant isolation.
- `specs/corporate-kb/runbooks/` -- operational runbooks for provisioning.
- `src/identity/` -- identity service / Keycloak realm configuration.
- `src/git-orchestrator/` -- GitLab project path prefix and Space isolation.
- `src/retrieval/` -- PostgreSQL schema isolation for kb_index.
- `_bmad-output/test-artifacts/t18/` -- destination for T18 validation artifacts.
- `specs/corporate-kb/evidence/phase-e/act010-closure-evidence.md` -- evidence report.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- status updates.

## Tasks & Acceptance

**Execution:**
- `specs/corporate-kb/evidence/phase-e/internal-sandbox-tenant-spec.md` -- new tenant isolation specification: naming convention, GitLab group/project isolation, PostgreSQL schema isolation, object-store bucket isolation, Keycloak realm/client isolation, network/domain considerations, rollback steps. RATIONALE: closes ACT-010 with actionable spec.
- `_bmad-output/test-artifacts/t18/provision-sandbox-tenant.sh` -- shell script skeleton/checklist that operators can run to provision the tenant; all values parameterized via env vars. RATIONALE: reproducible provisioning.
- `_bmad-output/test-artifacts/t18/tenant-validation-checklist.md` -- checklist for validating isolation: identity, Git, KB Spaces, retrieval, object store. RATIONALE: guides T18a/T18b execution.
- `specs/corporate-kb/evidence/phase-e/act010-closure-evidence.md` -- closure evidence. RATIONALE: reviewable proof.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- set ACT-010 to done, update overall_percent to 90. RATIONALE: reflect closure.

**Acceptance Criteria:**
- Given the tenant spec, when reviewed, then it defines clear isolation boundaries for all four layers (GitLab, PostgreSQL, object store, Keycloak).
- Given the provisioning script, when inspected, then all values are parameterized and no secrets are hard-coded.
- Given the validation checklist, when reviewed, then it covers cross-tenant access denial and shared-resource risks.
- Given the sprint status file, when updated, then ACT-010 is `done` and overall_percent is 90.

## Spec Change Log

## Review Triage Log

### 2026-11-12 — Review pass (self-review)
- verdicts: 2 findings — high 0, medium 0, low 0, false 0, maybe-false 2
- findings:
  - `[maybe-false]` `[defer]` Real sandbox resources were not provisioned; the shell script is a parameterized skeleton. Live T18a/T18b validation remains environment-gated.
  - `[maybe-false]` `[defer]` Logical isolation (schema/bucket/realm/group) assumes the shared PostgreSQL/MinIO/Keycloak/GitLab instances are secure at the platform level; dedicated network/infrastructure isolation is out of scope.

## Design Notes

The sandbox tenant is intentionally minimal: it shares the same PostgreSQL/MinIO/Keycloak instance as the primary tenant but uses separate schemas/buckets/realms. This matches the owner-approved minimal production target. Full tenant-level network isolation and dedicated infrastructure are out of scope for launch.

## Verification

**Commands:**
- `ls specs/corporate-kb/evidence/phase-e/internal-sandbox-tenant-spec.md` -- expected: file exists.
- `bash -n _bmad-output/test-artifacts/t18/provision-sandbox-tenant.sh` -- expected: no syntax errors.
- `python -c "import yaml; yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status.yaml'))"` -- expected: no parse errors.

**Manual checks (if no CLI):**
- Inspect `specs/corporate-kb/evidence/phase-e/internal-sandbox-tenant-spec.md` for isolation boundaries.
- Inspect `specs/corporate-kb/evidence/phase-e/act010-closure-evidence.md` for closure summary.
- Inspect `sprint-status.yaml` action_items for ACT-010 status.

## Auto Run Result

- Summary: ACT-010 closed by creating an internal sandbox tenant specification, provisioning skeleton, and validation checklist. The spec defines logical isolation across Keycloak realms, GitLab groups, PostgreSQL schemas, and MinIO buckets. Sprint status updated; overall_percent raised to 90.
- Files changed:
  - `specs/corporate-kb/evidence/phase-e/internal-sandbox-tenant-spec.md` — tenant isolation specification.
  - `_bmad-output/test-artifacts/t18/provision-sandbox-tenant.sh` — parameterized provisioning skeleton.
  - `_bmad-output/test-artifacts/t18/tenant-validation-checklist.md` — validation checklist.
  - `specs/corporate-kb/evidence/phase-e/act010-closure-evidence.md` — closure evidence.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — ACT-010 done, overall_percent 90.
- Review findings: 2 maybe-false deferred (live provisioning not done, logical isolation assumptions).
- Follow-up review recommended: false.
- Verification performed:
  - `ls` confirmed all files exist.
  - `bash -n _bmad-output/test-artifacts/t18/provision-sandbox-tenant.sh` → no syntax errors.
  - YAML parse check → OK.
  - ACT-010 status check → done; overall_percent 90.
- Residual risks:
  - Real sandbox resources not provisioned; T18a/T18b runtime validation remains blocked until environment is available.
  - Object-store ACL production engine recheck remains blocked per T13/T16.
  - Production AD, live SLO, HA, and cross-client deployment remain deferred.
