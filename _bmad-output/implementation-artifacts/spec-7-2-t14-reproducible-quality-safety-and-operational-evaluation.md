---
title: 'T14 Reproducible quality, safety and operational evaluation'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/t01-contract-tests.yaml
  - specs/corporate-kb/test-plan.md
  - specs/corporate-kb/baseline.md
  - specs/corporate-kb/components/retrieval-indexing.md
  - _bmad-output/implementation-artifacts/epic-7-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that the pilot can be evaluated against a reproducible Russian golden set, that quality/safety/operational metrics are separated, that refusal and groundedness are checked, and that an LLM judge is never the sole arbiter.

**Approach:** Create a T14 harness that exercises synthetic YAML fixtures for eval-case versioning, quality metrics, citation groundedness, deterministic adversarial/regression suites, operational measurements, observability correlation, Russian golden-set grading structure and human-in-the-loop disposition. Real model inference remains BLOCKED pending T11.

## Boundaries & Constraints

**Always:**
- Evaluation cases record corpus snapshot SHA, code/config/model/tool-schema versions, dataset version, scope and expected evidence; use approved/local grader configuration and the same data barrier as production.
- Quality metrics cover exact/semantic recall, factual support, citation correctness and abstention/no-answer behavior separately for page/section reads, long/repeated-heading content and stale/private/conflict cases.
- Citation revision/section are checked against canonical evidence; unsupported answers and silent stale substitution fail visibly; owner-approved thresholds are recorded before release claims; an LLM judge is never the sole arbiter.
- Deterministic adversarial/regression suites remain separate from probabilistic quality scores and require zero unauthorized disclosures.
- Operational measurements separate TTFT/full response, Git read/merge latency, merge→index freshness and CI queue lag.
- Observability evidence covers tree/read latency/errors, truncation/cursor continuation, durable draft/proposal outcomes, review SHA mismatch/conflict rates, preview reliability and UI retry/idempotency with request/run/proposal correlation.
- Machine output retained in `_bmad-output/test-artifacts/t14`; sanitized review evidence stored in `specs/corporate-kb/evidence/t14`.

**Never:**
- Do not use real hoster.ai inference, production corpus or owner-unapproved thresholds.
- Do not present mocked application/hoster results as real evidence.
- Do not let an LLM judge alone decide safety or groundedness.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Eval case versioning | Case with corpus/code/config/model/dataset/scope | All version fields recorded; local grader; production data barrier | Missing version / barrier mismatch → FAIL |
| Quality metrics | Russian golden answers with page/section/long/stale/private/conflict cases | Exact/semantic recall, factual support, citation correctness, abstention/no-answer reported separately | Undifferentiated score / missing abstention → FAIL |
| Citation groundedness | Answer with citations vs canonical evidence | Citations match revision/section; unsupported/stale answers fail visibly | Silent stale substitution / unsupported accepted → FAIL |
| Deterministic adversarial | Merge/push boundaries, ACL isolation, prompt injection, schema ownership, concurrency, crash/recovery | Deterministic PASS/FAIL; zero unauthorized disclosures | Probabilistic-only score / disclosure → FAIL |
| Operational measurements | Runtime/CI/Git telemetry | TTFT/full response, Git read/merge latency, merge→index freshness, CI queue lag separated | Missing separation → FAIL |
| Observability | Traces/metrics/logs | Tree/read errors, truncation/cursor, draft/proposal outcomes, SHA mismatch/conflict, preview, retry/idempotency correlated | Missing correlation → FAIL |
| Russian golden set | Expert Russian questions/answers | Local grader produces reproducible scores; human review for refusal/groundedness | Real inference without T11 → BLOCKED |
| Human-in-the-loop | Refusal/groundedness disposition | Expert human disposition recorded before release claim | Automated-only disposition → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t14/run_t14_tests.py` — main harness.
- `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml` — synthetic golden/adversarial/operational/observability fixtures.
- `specs/corporate-kb/test-plan.md` — A01–A36 catalog and fault matrix.
- `specs/corporate-kb/contracts/t01-contract-tests.yaml` — CF consumer vectors.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t14/run_t14_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t14/eval-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t14/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `7-2-t14-...` → `done`.

**Acceptance Criteria:**
- [x] Given eval-case fixtures, every case records corpus snapshot SHA, code/config/model/tool-schema versions, dataset version, scope and expected evidence using an approved/local grader and the production data barrier.
- [x] Given quality fixtures, metrics cover exact/semantic recall, factual support, citation correctness and abstention/no-answer separately for page/section reads, long/repeated-heading content and stale/private/conflict cases.
- [x] Given groundedness fixtures, citation revision/section are checked against canonical evidence; unsupported answers and silent stale substitution fail visibly.
- [x] Given adversarial fixtures, deterministic regression suites remain separate from probabilistic quality scores and require zero unauthorized disclosures.
- [x] Given operational fixtures, TTFT/full response, Git read/merge latency, merge→index freshness and CI queue lag are reported separately with retrieval/patch/conflict/restore outcomes and cost drivers.
- [x] Given observability fixtures, tree/read latency/errors, truncation/cursor continuation, durable draft/proposal outcomes, review SHA mismatch/conflict rates, preview reliability and UI retry/idempotency are correlated by request/run/proposal.
- [x] Given Russian golden-set fixtures, the local grader structure is reproducible and refusal/groundedness dispositions require human-in-the-loop review.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths and live inference/evaluation is recorded as BLOCKED.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Real hoster.ai inference and owner-reviewed expert golden set remain BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness validates the structure of a reproducible evaluation harness: versioning, separated quality/safety/operational/observability dimensions, citation groundedness checks, deterministic adversarial suites, Russian golden-set grading workflow and required human-in-the-loop disposition. It does not claim real model-output quality scores because live inference is BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t14/run_t14_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t14/run_t14_tests.py` -- expected: writes `eval-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t14/eval-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t14/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
