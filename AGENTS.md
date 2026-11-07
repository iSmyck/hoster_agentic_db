# Workspace instructions

## Current phase

- Only T00 baseline audit and G0 design review are currently authorized.
- Do not change product code, run product migrations, upgrade dependencies, or perform mass formatting before baseline/design approval.
- No Open WebUI commit, GitLab version/edition, upstream checkout, or repository-perimeter layout has been selected yet. Do not guess them.
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

- Project lint and test commands are not configured yet. Derive them from the pinned upstream repositories during T00 and record them in `baseline.md`.
- Until then, validate only the artifacts changed during workspace setup; do not invent a product stack or test command.
