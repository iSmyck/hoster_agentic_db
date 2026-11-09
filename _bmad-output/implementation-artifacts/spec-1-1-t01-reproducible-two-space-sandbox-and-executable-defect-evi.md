---
title: 'T01 Reproducible two-Space sandbox and executable defect evidence'
type: 'feature'
created: '2026-11-08'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/t01-contract-tests.yaml
  - specs/corporate-kb/contracts/README.md
  - specs/corporate-kb/baseline.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В `t01-contract-tests.yaml` зафиксирован каталог из 30 контрактных векторов (CF-01..CF-30), но он имеет статус `DESIGN_NOT_EXECUTED`. QA не может получить воспроизводимый артефакт с executable validation reports до начала feature work.

**Approach:** Создать тонкий Python harness, который поднимает два синтетических repository-per-Space fixture (`sales`, `sales-pricing`) на закреплённом T00 toolchain, исполняет векторы из `t01-contract-tests.yaml` и записывает детерминированные отчёты с SHA-256, версиями, командами и rerun-инструкциями.

## Boundaries & Constraints

**Always:**
- Использовать только pinned T00 toolchain (Open WebUI v0.13.0, GitLab CE 19.5.3, PostgreSQL 18.6/pgvector 0.8.7, Python 3.12/uv).
- Хранить machine output в `_bmad-output/test-artifacts/t01/` и sanitized review evidence в `specs/corporate-kb/evidence/t01/`.
- Каждый check явно маркировать `PASS` / `FAIL` / `BLOCKED` / `NOT_EXECUTED`.
- Для FAIL предоставлять minimal reproduction fixture, stable IDs/SHAs, sanitized mismatch details и rerun instructions.
- Один GitLab repo = один Space; fixture-репозитории создавать через API, не коммитить статические bundles.

**Never:**
- Не создавать production corpus, не выполнять production migration, не использовать реальные credentials/endpoints.
- Не превращать harness в runtime service, canonical store или general-purpose testing platform.
- Не отмечать `BLOCKED` интеграции как `PASS`; CF-30 и real GitLab/IdP/hoster.ai проверки остаются `BLOCKED` / `DESIGN_NOT_EXECUTED`.
- Не изменять canonical или hash semantics существующих contracts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path — sandbox запущен | `uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py` | `contract-results.json` + `summary.md` с полным набором executed checks | Недоступные сервисы → `BLOCKED` с причиной |
| Schema validation negative | Invalid front matter / policy / record payload | Check `FAIL` с exact mismatch и SHA-256 входных данных | Ошибка парсинга JSON Schema → `BLOCKED` |
| Cross-Space isolation | Reuse sales bundle/group snapshot in sales-pricing | Check `FAIL` / `POLICY_REVISION_MISMATCH` | Fixture setup error → `BLOCKED` |
| Idempotency collision | Same Idempotency-Key, different payload | `IDEMPOTENCY_KEY_REUSED`, writes = 0 | Harness double-run должен давать deterministic результат |
| CF-30 catalog completeness | All schemas/OpenAPI/events/refs | `PASS` на parse/resolve/unique operationIds, `DESIGN_NOT_EXECUTED` для semantic assertions | Missing file → `BLOCKED` |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов: scope вытекает из `t01-contract-tests.yaml` и epic context, а технические детали (язык harness, формат отчёта) определяются существующими T00 паттернами._

## Code Map

- `specs/corporate-kb/contracts/t01-contract-tests.yaml` -- единственный источник CF-01..CF-30 векторов.
- `specs/corporate-kb/contracts/*.schema.json`, `*.yaml`, `*.md` -- целевые contracts для валидации.
- `specs/corporate-kb/baseline.md` -- pinned versions toolchain и reproducible commands.
- `_bmad/scripts/render_skill.py`, `config_utils.py` -- примеры deterministic render/config utilities, которые можно переиспользовать для snapshot-отчётов.
- `_bmad-output/test-artifacts/t00/gitlab/` -- reference-паттерн: synthetic GitLab projects, protected branches/tags, MR/DecisionRecord fixtures.
- `_bmad-output/test-artifacts/t00/checks.py` / `capability-results.json` -- reference-формат result envelope.

## Tasks & Acceptance

**Execution:**
- [ ] `_bmad-output/test-artifacts/t01/run_contract_tests.py` -- main harness: parse `t01-contract-tests.yaml`, bootstrap two Spaces, execute vectors, write `contract-results.json` и `summary.md`.
- [ ] `_bmad-output/test-artifacts/t01/fixtures/` -- synthetic YAML/JSON payloads для каждого CF vector, включая stable IDs/SHAs из `t01-contract-tests.yaml`.
- [ ] `_bmad-output/test-artifacts/t01/sandbox.py` -- provisioning двух GitLab repository-per-Space fixtures (`sales`, `sales-pricing`) с разными repository_id, policy_bundle_id, revisions, group snapshots, revocation epochs, readers/authors/approvers.
- [ ] `_bmad-output/test-artifacts/t01/validators/` -- пакет со schema validators (JSON Schema), OpenAPI/operationId checker, projection-mapping checker.
- [ ] `_bmad-output/test-artifacts/t01/reporters/` -- пакет для записи report с exact versions, environment, commands, expected/actual, raw SHA-256.
- [ ] `specs/corporate-kb/evidence/t01/summary.md` -- sanitized reviewable summary (pass/fail/blocked counts, top findings, rerun instructions).
- [ ] `specs/corporate-kb/evidence/t01/contract-results.json` -- sanitized копия machine output (secrets redacted).
- [ ] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- обновить `1-1-t01-...` из `backlog` → `done` после завершения и review.

**Acceptance Criteria:**
- Given `t01-contract-tests.yaml` и pinned T00 toolchain, when QA запускает `run_contract_tests.py`, then harness выполняет все CF-01..CF-29 vectors и CF-30 completeness check, и каждый результат явно помечен `PASS`/`FAIL`/`BLOCKED`/`NOT_EXECUTED`.
- Given любой `FAIL` result, when reviewer открывает report, then видит minimal reproduction fixture, stable IDs/SHAs, sanitized mismatch details и rerun instructions.
- Given passed, failed, BLOCKED и unexecuted checks, when report сгенерирован, then они остаются явно различимы, а `DESIGN_NOT_EXECUTED` / `BLOCKED` интеграции не отмечены как `PASS`.
- Given front matter, ProposalRecord, DecisionRecord, index snapshot, AuthzContext и policy schemas, when contract runners выполняют checks, then deterministic serialization, full-SHA и hash semantics verified against approved fixtures.
- Given completed run, when machine output сохранён в `_bmad-output/test-artifacts/t01/` и sanitized evidence в `specs/corporate-kb/evidence/t01/`, then ни в одном файле нет secrets/tokens/real endpoints.

## Implementation Notes


## Spec Change Log


## Review Triage Log

- `patch` — `run_cf29_links` unconditionally emitted PASS even when `has_7_1=False` and `has_7_3=False`. Fixed to assert all three booleans and check both `integration.md` and `gitlab-integration.md`. Re-ran harness: PASS 50 / FAIL 0 / BLOCKED 67.
- `patch` — Reports contained absolute filesystem paths (`/Users/antonsmychkin/...`), breaking reproducibility. Fixed to emit project-root-relative paths. Verified no absolute paths remain in reports.
- `patch` — Missing catalog/schema files and invalid JSON schemas caused traceback. Fixed to emit `BLOCKED` checks and exit cleanly.
- `patch` — JSON pointer escaping replaced `~1` before `~0`. Fixed order so `~0` → `~` first, then `~1` → `/`.
- `patch` — `agent-tools.yaml` cross-file `$ref` to `./openapi.yaml#...` could be unresolved. Fixed `resolve_refs` to handle cross-file refs.
- `patch` — Fixture getters returned mutable global dicts. Fixed to return `copy.deepcopy(...)`.
- `patch` — CF-11/CF-19 negative fixtures were rejected for `additionalProperties` rather than intended semantic condition. Fixed fixtures and added `iter_errors`/`_error_paths_contain` to verify errors land under expected properties.
- `patch` — `_canonical_prefix` rejected root `/` and silently skipped `None`. Fixed to treat `/` as valid root and fail explicitly when normalization returns `None` for non-empty input.
- `patch` — `sanitize.py` had duplicate case-insensitivity flags. Removed redundant inline `(?i)` while keeping `re.IGNORECASE`.
- `patch` — Deferred the following to later stories/epics because they require live GitLab/IdP/CI/hoster.ai sandboxes or a GO backend not yet available in T01: dynamic catalog-driven execution, live GitLab API provisioning of fixtures, CF-20 idempotency collision runtime checks, CF-01 cross-Space reuse/fan-out runtime checks, and full CF-06/CF-07/CF-10/CF-12–CF-24 runtime lifecycle checks.

## Design Notes

Harness остаётся thin QA adapter над существующими contracts и CI:
1. **Parse** — загружает `t01-contract-tests.yaml` и резолвит `$ref` в schemas/OpenAPI.
2. **Provision** — создаёт два disposable GitLab repo (`sales`, `sales-pricing`) с разными ACL/policy bundles.
3. **Execute** — для каждого vector вызывает соответствующий validator; negative vectors ожидают rejection, positive — successful roundtrip.
4. **Report** — для каждого check записывает `{id, status, expected, actual, input_sha256, fixture_path, rerun_cmd}`.
5. **Sanitize** — redact secrets/Tokens/emails перед копированием в `specs/corporate-kb/evidence/t01/`.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py --dry-run` -- expected: parse catalog, list checks, exit 0 без side effects.
- `uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py` -- expected: produce `_bmad-output/test-artifacts/t01/contract-results.json` and `summary.md` with deterministic stable IDs/SHAs.
- `python -m json.tool _bmad-output/test-artifacts/t01/contract-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t01/` -- expected: no matches.

**Manual checks:**
- `specs/corporate-kb/evidence/t01/summary.md` содержит pass/fail/blocked counts и top findings.
- `specs/corporate-kb/evidence/t01/contract-results.json` содержит `secrets_included: false`.

### Review Findings

- [x] [Review][Defer] Dynamic catalog-driven execution — harness maps CF vectors to hardcoded functions instead of interpreting `t01-contract-tests.yaml` at runtime. Deferred: requires stable runner contract and GO backend availability.
- [x] [Review][Defer] Live GitLab API provisioning of fixtures — `sandbox.py` is a stub returning `BLOCKED`. Deferred: requires live GitLab/IdP/CI sandbox and credentials.
- [x] [Review][Defer] CF-20 idempotency collision runtime checks — no synthetic collision test implemented. Deferred: requires GO backend and idempotency registry.
- [x] [Review][Defer] CF-01 cross-Space reuse/fan-out runtime checks — only structural distinctness verified. Deferred: requires live GitLab/AuthZ sandbox.
- [x] [Review][Defer] Full CF-06/CF-07/CF-10/CF-12–CF-24 runtime lifecycle checks — marked `BLOCKED`/`NOT_EXECUTED`. Deferred: requires GO backend and canonical store.
- [x] [Review][Defer] Unit tests for validators/reporters/sandbox — deferred until baseline test runner (`pytest`/`pyproject.toml`) is configured in T00/T01.
