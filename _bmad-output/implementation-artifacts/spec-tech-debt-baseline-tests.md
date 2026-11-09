---
title: 'Tech debt: pytest baseline and harness unit tests'
type: 'chore'
created: '2026-11-08'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '8f14e4b6232071c355d85bdcc0d1ee001f6d8cd1'
context:
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Накопленный tech debt: harness-исходники не покрыты unit tests, baseline test runner (pytest/pyproject.toml) не настроен, что блокирует уверенность в regressions перед продолжением эпиков.

**Approach:** Настроить минимальный pytest baseline в корне проекта и добавить unit tests для общих reporters/sanitize и key validators из t01-t04b.

## Boundaries & Constraints

**Always:**
- Использовать pinned T00 toolchain (Python 3.12, uv).
- Тесты должны запускаться через `uv run pytest -q` из корня проекта.
- Покрыть reporters (ReportBuilder, sanitize), sanitize (path/token/email redaction), и по крайней мере один validator из каждого harness.
- Не изменять product code / pinned versions.

**Never:**
- Не добавлять real credentials/endpoints.
- Не запускать integration tests без sandbox.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| pytest baseline | `uv run pytest -q` | Tests discovered and pass | Missing deps → FAIL |
| ReportBuilder | Add PASS/FAIL/BLOCKED checks | Deterministic JSON output | Missing fields → raises |
| sanitize | Absolute path / token / email | Redacted / relative output | — |
| SchemaValidator | Valid/invalid schema + payload | PASS/FAIL result | Missing schema → clear error |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t01/reporters/` — reference reporter/sanitize implementation.
- `_bmad-output/test-artifacts/t02/validators/` — document/read validators.
- `_bmad-output/test-artifacts/t03a/validators/` — identity/group validators.
- `_bmad-output/test-artifacts/t03b/validators/` — policy validators.
- `_bmad-output/test-artifacts/t04a/validators/` — draft/history validators.
- `_bmad-output/test-artifacts/t04b/validators/` — editor validators.

## Tasks & Acceptance

**Execution:**
- [ ] `pyproject.toml` — add `[project]` metadata, `[dependency-groups]` dev с `pytest`, `pyyaml`, `jsonschema`, `referencing`.
- [ ] `tests/__init__.py` — empty marker.
- [ ] `tests/test_reporters.py` — unit tests для ReportBuilder и sanitize.
- [ ] `tests/test_t02_validators.py` — tests для `_canonical_prefix`, path normalization, Git blob hash.
- [ ] `tests/test_t03a_validators.py` — tests для nested group resolution, cycle detection.
- [ ] `tests/test_t03b_validators.py` — tests для longest-prefix selection, duplicate-prefix detection.
- [ ] `tests/test_t04a_validators.py` — tests для idempotency replay и stale-base conflict.
- [ ] `tests/test_t04b_validators.py` — tests для front-matter boundary и XSS gate.
- [ ] `specs/corporate-kb/tasks.md` — обновить tech-debt статус / добавить запись.
- [ ] `_bmad-output/implementation-artifacts/sprint-status.yaml` — добавить tech-debt story `done` или запись в action items.

**Acceptance Criteria:**
- Given `uv run pytest -q`, when executed from project root, then all tests pass and no integration tests run without sandbox.
- Given ReportBuilder input, when serialized, then output is deterministic and includes required fields.
- Given absolute path/token/email, when sanitized, then output is relative/redacted.
- Given validators under test, when fed synthetic fixtures, then they produce expected PASS/FAIL/BLOCKED verdicts.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Tests import modules from `_bmad-output/test-artifacts/t0*/` via `sys.path` manipulation or by adding relative imports; since these directories are gitignored, tests must handle their absence gracefully or use import helpers.

## Verification

**Commands:**
- `uv run pytest -q` -- expected: all tests pass.
- `uv run ruff check tests --select=F` -- expected: clean.
- `uv run ruff format --check tests` -- expected: clean.
