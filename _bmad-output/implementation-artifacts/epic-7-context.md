# Epic 7 context: Internal pilot acceptance

**Goal.** Execute the internal sales-corpus pilot end-to-end through owner-approved hoster.ai inference, independent quality/safety/operational evaluation, and hardened protected-deployment rehearsal, producing reviewable evidence for a G2 decision without claiming second-client or full G3 scope.

**Current state.** All three stories are **TODO / BLOCKED** pending real external inputs and upstream implementation dependencies. No execution evidence exists.

---

## Story 7.1 — T11: Approved hoster.ai studio inference lifecycle

**Scope.** Configure and exercise all chat, tool and auxiliary inference routes through an owner-approved hoster.ai studio endpoint. Verify streaming, bounded tools, retries/cancellation, egress/secrets controls, and cold-start asset behavior on the *real* approved connection.

**Mapped requirements.** R15, R16, R18; I03, I04, I09, I12, I13.

**Acceptance ownership.** Full/direct: A16. Supporting: A18, A20.

**Key acceptance criteria (summary).**
- Every inference route (chat/answer, task/title/summarization, extraction, embeddings, reranking, OCR/vision) records approved connection/model/version, data profile, capabilities and required dimension/index-profile linkage.
- Streaming sequential/parallel tool calls preserve request/run correlation and citations, assemble typed arguments without executing partial content, and validate authorization before dispatch.
- Malformed JSON, unknown fields, unsupported operations, oversized payloads and prompt-injection instructions fail safely without shell/SQL/arbitrary execution, unauthorized model payload, merge or privilege expansion.
- Retry/cancel/disconnect/4xx/5xx behavior is observable; mutation retries preserve the same idempotency identity and exact payload. No silent provider/model/perimeter fallback.
- Egress is limited to approved endpoints; `pii_permitted` content stays inside the agreed perimeter; revocation closes live streams; offline startup uses only preapproved assets.
- Lifecycle measurements report TTFT and full-response latency separately, with retry/cancel/malformed-call rates, route inventory and fallback attempts; costs are attributable to the run.

**Dependencies.** T09 bounded tools and trusted execution context; real hoster.ai inputs and separate approval for external/paid calls are mandatory.

**Blockers.** Real hoster.ai endpoint, model inventory, credentials and egress policy are **UNKNOWN / BLOCKED**. Without them, T11 evidence must say BLOCKED and no integration PASS is claimed.

---

## Story 7.2 — T14: Reproducible quality, safety and operational evaluation

**Scope.** Build/run an expert Russian golden dataset and deterministic adversarial/regression/operational suites against the actual deployed application pipeline, producing independent reviewable evidence for pilot acceptance.

**Mapped requirements.** R01, R03, R04, R05, R11, R15, R18; I01–I14 in an explicitly chosen regression scope.

**Acceptance ownership.** Full/direct: A03, A18, A20, A21. Supporting: applicable A01–A36 in the chosen regression scope (no automatic VERIFIED).

**Key acceptance criteria (summary).**
- Evaluation cases record corpus snapshot SHA, code/config/model/tool-schema versions, dataset version, scope and expected evidence; use approved/local grader configuration and the same data barrier as production.
- Quality metrics cover exact/semantic recall, factual support, citation correctness and abstention/no-answer behavior separately for page/section reads, long/repeated-heading content and stale/private/conflict cases.
- Citation revision/section are checked against canonical evidence; unsupported answers and silent stale substitution fail visibly; owner-approved thresholds are recorded before release claims; an LLM judge is never the sole arbiter.
- Deterministic adversarial/regression suites (merge/push boundaries, ACL isolation, prompt injection, schema ownership, concurrency, crash/recovery) remain separate from probabilistic quality scores and require zero unauthorized disclosures.
- Operational measurements separate TTFT/full response, Git read/merge latency, merge→index freshness and CI queue lag; record retrieval/patch/conflict/restore outcomes plus cost drivers.
- Observability evidence covers tree/read latency/errors, truncation/cursor continuation, durable draft/proposal outcomes, review SHA mismatch/conflict rates, preview reliability and UI retry/idempotency with request/run/proposal correlation.
- Machine output retained in `_bmad-output/test-artifacts/t14`; sanitized review evidence stored in `specs/corporate-kb/evidence/t14`.

**Dependencies.** T01 contract harness, T09 agent tools, T10 indexing/retrieval, **T11 real approved inference**.

**Blockers.** Requires T11 inputs and an owner-reviewed expert golden set. Mocked application/hoster results are not accepted as real evidence.

---

## Story 7.3 — necessary T18 pilot part: Pilot hardening, protected deployment and operational acceptance

**Scope.** Harden a protected pilot deployment, rehearse startup/cutover/recovery/export/backup/restore/upgrade/rollback runbooks, and perform pre-G2 acceptance with two independent non-engineering business users. This covers only the **internal pilot** slice; full T18/G3 and second-client acceptance remain in Epic 8.

**Mapped requirements.** R01, R05, R14, R15, R17, R18; I01–I14 by operational-hardening scope.

**Acceptance ownership.** No full/direct owners assigned. Supporting: A01, A06, A07, A08, A09, A10, A15, A20, A22, A23, A28, A33. **A19 is explicitly out of scope here** (belongs to E08.4/E08.5).

**Key acceptance criteria (summary).**
- Pilot environment is isolated: repositories=Spaces, config/adapters, PostgreSQL/index/object storage, secrets, backups and egress separated; runtime workers have migrations disabled and non-DDL roles; only owning external migrators perform rehearsed schema upgrades before traffic.
- Proposal/merge, connector, CI/index and retrieval credentials remain separated; default egress is closed except approved routes; no client code branch introduced; no production resource/corpus created without separate authorization.
- Startup, cutover, merge recovery/quarantine, export, backup, restore, upgrade and rollback runbooks are rehearsed with exact versions/refs, commands, sanitized outputs, failure handling, residual BLOCKED items and independently reviewed results.
- Backup/restore drill validates decisions/assets/authorization closure, freshly rebuilds `kb_authz`, starts `kb_ops` under global merge freeze with conservative target barriers, and points `kb_index` to a new full validated snapshot before activation.
- Security/regression checks deny direct push/merge/auto-merge for every non-privileged business/engineering/bot/connector/CI/source-managed identity; each owning component writes only its schema; runtime DDL and cross-client resource access fail; secret/log redaction canaries disclose nothing.
- Privileged GitLab Owner bypass is treated as an out-of-band integrity incident: detection, immediate quarantine and G0-D3 emergency runbook — not as absolute technical prevention or a normal managed path.
- Two independent non-engineering business users complete the full **pending queue → read/edit → diff/rationale/evidence → accept/reject/cancel → history/restore** scenario without Git/CLI, exercising accept/reject/cancel on exact proposal fixtures and verifying canonical decisions, history cursor and reviewed revert-MR.

**Dependencies.** T13 portability/restore, applicable P0 safety gates, T11/T14 real pilot inference/evaluation evidence; protected deployment and pilot corpus require separate owner authorization.

**Blockers.** Requires real approved inference/evaluation, owner-authorized pilot environment and corpus, and completed runbook rehearsals. No second-client/A19 completion claim is made.

---

## Cross-story risks and constraints

1. **Real hoster.ai inputs are the critical path.** T11 cannot start without them; T14 and T18 necessary depend on T11 evidence.
2. **No mocks as PASS.** Absent real endpoint/configuration/credentials leaves affected integration BLOCKED, not passing with mocks or guessed model IDs.
3. **No invented thresholds.** Quality, latency, freshness, capacity, RPO/RTO, budget and retention values require owner decisions; unapproved values must not be invented as results.
4. **No G2 self-approval.** G2 is recorded only by the owner after reviewing evidence; completing this necessary pilot part does not mark full T18 or second-client/G3 scope complete.
5. **Sanitization required.** Prompts, raw documents/chunks/queries/rationale/evidence, provider payloads, tokens, signed URLs, bind secrets and PII snippets must be absent from ordinary logs, traces, metrics and evidence.
