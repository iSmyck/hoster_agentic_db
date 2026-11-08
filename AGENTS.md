# Workspace instructions

## Current phase

- T00 baseline audit is DONE and the owner G0 design review is APPROVED: `specs/corporate-kb/g0-review.md`.
- Pinned baseline: Open WebUI `v0.13.0` (commit `c38885a1a737da4968f157092f304f3b5481d0bf`), checkout at `_bmad-output/test-artifacts/t00/upstream/open-webui`. Versions, code refs, and toolchain: `specs/corporate-kb/baseline.md`.
- Sprint development is in progress per `_bmad-output/implementation-artifacts/sprint-status.yaml`; work only on the active story scope.
- Do not change pinned versions, upgrade dependencies, run product migrations, or perform mass formatting outside an approved story/ADR.
- Do not create the production knowledge-base corpus before its repository perimeter and source corpus are agreed.

## Normative documents

- Platform requirements and backlog: `specs/corporate-kb/spec.md`.
- Content pipeline standard: `specs/corporate-kb/content-standard.md`.
- Task state and evidence index: `specs/corporate-kb/tasks.md`.
- R01–R18 and I01–I14 take precedence over planning details.
- Distinguish REQUIREMENT, DESIGN, UNKNOWN, and DEFERRED. Record owner decisions in ADR files instead of silently merging contradictory rules.
- When `baseline.md`, `architecture.md`, and ADR files appear, read them before implementation work. Deeper repository instructions take precedence within an upstream checkout.
## Workflow

- Follow task dependencies and gates in the specification. Do not mark owner security/design approvals complete on the owner's behalf.
- Reuse verified upstream and GitLab capabilities before adding a service or library.
- Use the task states TODO, IN_PROGRESS, VERIFIED, DONE, and BLOCKED exactly as defined in the specification.
- Record commands, environment, results, blocked checks, upgrade impact, and sanitized evidence for each completed task.
- Keep machine-generated test output in `_bmad-output/test-artifacts`; place only sanitized reviewable evidence in `specs/corporate-kb/evidence`.

## Safety

- Use synthetic fixtures. Do not add real client documents, secrets, tokens, private endpoints, or unredacted personal data to the workspace or reports.
- Do not present mocked integration as a successful GitLab or hoster.ai studio check. Mark unavailable integrations BLOCKED.
- Production migration, destructive cleanup, push/deploy, paid external calls, and enabling egress require separate owner authorization.
- Do not commit or push changes unless the user explicitly requests it.

## Validation

- Lint/test/typecheck commands are recorded in `specs/corporate-kb/baseline.md` §3/§5, derived from the pinned upstream checkout.
- Upstream svelte-check, ESLint, and `npm run build` are known-FAIL approved debt (G0-D9), not releasable gates; use Vitest and the direct Vite build instead. Do not hide this debt.
- Sprint harness runners live in `_bmad-output/test-artifacts/<task>/` (e.g. `run_contract_tests.py`, `run_document_tests.py`); validate only the artifacts changed by the active story.
