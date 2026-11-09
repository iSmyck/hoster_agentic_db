# Epic 8 context: Repeatable client delivery

**Goal.** Extend the internal pilot into a repeatable, isolated second-client delivery: one owner-selected real source connector, a safe three-way update protocol, evidence-gated extraction, config-only dedicated deployment, and full T18/G3 operational acceptance. The epic produces reviewable evidence for A14–A20, A28 and A33, and closes A19 only through the deployed second client.

**Current state.** All stories are **TODO / BLOCKED** pending owner selections, real external sandboxes and completed upstream dependencies. No execution evidence exists; `operations.md` remains DESIGN NOT EXECUTED until these rehearsals exist.

---

## Story 8.1 — T15: Safe source registry, three-way updates and durable cursors

**Scope.** Define the source-binding contract and Git Orchestrator (GO) cursor protocol so external source versions become at most one reviewable proposal at a time, with durable `seen`/`proposed`/`merged` transitions reconstructed from source and Git evidence after crashes.

**Mapped requirements.** R06–R10, R12, R13, R16, R18; I01–I07, I09, I10, I12–I14.

**Acceptance ownership.** Full/direct: A14. Supporting: A17, A32.

**Key acceptance criteria (summary).**
- Source observations advance `seen` only after durable metadata, `proposed` only after a durable MR plus ProposalRecord, and `merged` only after verified Git merge and source-mapping reconciliation. Crash replay reconstructs each transition from durable evidence; no fabricated cursor state.
- Same hash/version is a no-op or returns the existing proposal. At most one outstanding proposal exists per source object; newer observations update only `seen` until the current proposal terminates.
- `migrated`, `source_managed`, `curated` and `live_operational` bindings behave differently: migrated ignores the old source; GO denies local edits to source-managed content; curated updates produce a three-way reviewable proposal preserving independent source and human changes; live operational stays a typed read-only snapshot with no writes.
- Source deletion, stale ACL/owner or inaccessible object creates a tombstone/obsolete review through the normal MR path; silent deletion is forbidden.

**Dependencies.** E06.2 import/cutover, E04.2 proposal/decision/merge evidence, E05.2 indexing/reconciliation.

**Blockers.** None beyond upstream completion; this is the foundation for E08.2.

---

## Story 8.2 — T16: One owner-selected real source connector

**Scope.** Implement and validate exactly one real connector chosen by the owner from SharePoint, Bitrix24 or Kayako against its real sandbox, exercising updates, revocations, deletions, retries, attachments and bounded backoff.

**Mapped requirements.** R05, R06, R12–R16, R18; I01–I04, I06, I07, I09–I14.

**Acceptance ownership.** Full/direct: A14. Supporting: A16, A23, A25, A32.

**Key acceptance criteria (summary).**
- Feasibility inventory records the selected source's exact edition, API, authentication, sandbox, scopes, rate limits and observed behavior for list/changes/fetch/version/attachments/deletions/access-hints. The other two connectors are not claimed ready.
- The connector preserves stable remote ID, immutable version/hash, source owner and provenance; maps only to the configured repository=Space; and sends proposal-only requests to GO. Human DecisionRecord and GO merge remain mandatory; the connector has no push/merge/auto-merge/grants/export/index-pointer capability.
- Revoked credentials, changed ACL hints or revoked group membership fail closed; access hints are treated as hints only. Anti-enumeration behavior protects source metadata.
- Deletion produces the E08.1 tombstone/obsolete review; bounded retry preserves operation identity; duplicate webhooks/polling/concurrent workers yield at most one outstanding proposal; poison objects reach an observable dead-letter.
- Attachments are immutable/versioned with SHA-256, size, media type and source reference; scoped object credentials are used. Mutable URLs, missing/mismatched objects and failed object-store ACL checks block affected claims. Source secrets, raw payloads, signed URLs and tokens never enter documents, MR evidence, model arguments, logs or reports.

**Dependencies.** E08.1 safe update protocol and E02.3 authorization.

**Blockers.** Owner selection of exactly one source, real sandbox, edition/API details and credentials are **UNKNOWN / BLOCKED**. Without them T16 evidence must say BLOCKED; mocks do not count as integration PASS.

---

## Story 8.3 — T17 conditional: Evidence-gated extraction, media and OCR quality

**Scope.** Gate activation of any non-Markdown extraction route on owner-authorized real samples, golden/loss evidence, media/OCR classification and human verification. Markdown-only workloads are recorded N/A only through an explicit ADR/owner decision.

**Mapped requirements.** R02, R04, R12, R13, R15, R18; I01–I03, I08, I09, I12, I13.

**Acceptance ownership.** Full/direct: A16, A23 only if the conditional scope is activated. Supporting: A22.

**Key acceptance criteria (summary).**
- Activation requires owner-supplied authorized representative samples and agreement on formats, quality review and data/media profile. Only synthetic or sanitized derivative fixtures and hashes enter the workspace.
- The pinned Docling integration is assessed first; a second pipeline requires documented unmet need, approved design/ADR and separate compatibility, license and rollback assessment.
- Golden fixtures measure page/slide counts, encoding, reading order, table structure/numbers, links/anchors and omissions/duplications by format and risk. Empty/garbled output, unsupported formats, extraction loss and OCR disagreement are quarantined with the original recoverable.
- Decorative content is excluded; illustrative assets keep captions; substantive automatic descriptions are explicitly labelled and cite the original page/slide; critical/handwritten knowledge enters the index only after required human transcription/verification.
- Malicious or malformed samples are rejected before corpus/preview. Only approved providers, data profiles, pinned model/licenses/assets and egress routes are used. Unresolved PII/media hits, unplanned fallback or missing offline assets block the route. Failed extraction never advances source `merged` or publishes a partial index.

**Dependencies.** E06.1 dry-run/security/data barrier and owner-authorized real format samples.

**Blockers.** Real sample authorization and owner decision to activate non-Markdown scope. Without them the applicable extraction work is BLOCKED or recorded N/A by ADR only.

---

## Story 8.4 — T18a: Repeatable config-only dedicated deployment

**Scope.** Reproduce the complete platform for a second isolated client from the same pinned core and configuration, proving resource isolation and repeatable delivery without client code forks or shared security boundaries.

**Mapped requirements.** R05, R15, R17, R18; I04, I07, I09–I14.

**Acceptance ownership.** Full/direct: A19, A20, A33.

**Key acceptance criteria (summary).**
- Each client receives its own repositories=Spaces, Open WebUI/GO/Identity configuration and adapters, PostgreSQL/index/CI/object storage, immutable assets, secret references, backups, mirrors, network perimeter and egress allowlist, without code edits or a client branch.
- The second client cannot read or write the first client's repositories, history, grants, objects, caches, logs or backups. Personal Notes and ordinary chats retain upstream behavior; branding/notices remain preserved.
- Runtime workers use `ENABLE_DB_MIGRATIONS=False` and non-DDL roles; only the authorized external migrator for each owning component applies and verifies expected migration heads before traffic. Cross-schema writes and runtime DDL are denied; empty database is never treated as proof of no merge or external operation.
- Cold startup and isolation smoke checks separate proposal/merge, connector, CI/index and retrieval credentials; default egress is closed except approved routes; startup performs no unapproved download or provider fallback; readiness distinguishes published, indexed and unavailable states.

**Dependencies.** E06.4 portability/restore, applicable P0 safety gates, E07.3 pilot-hardening evidence.

**Blockers.** Second-client environment, object store, CI, secrets and network perimeter are **UNKNOWN / BLOCKED** until owner authorization and infrastructure are available.

---

## Story 8.5 — T18b full/G3: Backup, restore, upgrade and full operational acceptance

**Scope.** Demonstrate clean disaster-recovery and upgrade rehearsals for the second client, exercise observability and incident handling, and complete independent G3 review/owner acceptance for full T18.

**Mapped requirements.** R05, R06, R09, R10, R11, R13, R14, R15, R17, R18; I01–I14.

**Acceptance ownership.** Full/direct: A15, A19, A20, A33. Supporting: A14, A28.

**Key acceptance criteria (summary).**
- Clean restore validates refs, MR/note/audit metadata, decisions/assets/authorization closure and hashes; freshly rebuilds `kb_authz`; recovers Git-derived `kb_ops` projections under global merge freeze with conservative barriers; and points `kb_index` to a new full validated snapshot before activation.
- A separate durable non-Git-derived correction backup preserves correction-task current projections, append-only events, restricted evidence and idempotency records; restore validates hashes/event sequences/perimeter and performs linked-MR reconciliation without fabricating, deleting, resolving or cancelling tasks. Correction backup never creates a second canonical write path.
- Unknown merge outcomes remain quarantined; missing assets, incomplete closure or missing/corrupt correction backup block READY. Cross-client negative controls fail closed. Owner-approved RPO/RTO, retention, backup cadence and recovery evidence are recorded.
- Metrics/alerts/runbooks cover startup, cutover/activation, merge latency, locks/fencing/recovery age/quarantine, decision mismatch, CI/webhook/HEAD drift, revocation, source cursors, export/backup closure, source sync, TTFT/full response and restore/upgrade. Telemetry excludes secrets, raw documents/chunks/queries/rationale/evidence, provider payloads, signed URLs and PII snippets.
- Upgrade/rollback rehearsals evaluate dependency pins, SBOM/license diff, branding/notices, external migration order, cold offline startup and every registered auth/grant/tool/editor/retrieval/connector seam. Failures block the upgrade rather than being waived as upstream debt.
- Full T18/G3 acceptance demonstrates the E08.4 second-client deployment, E08.2 selected-connector evidence, clean backup/restore and upgrade results through independent review, with one external source update flowing through human decision and GO merge without auto-merge.

**Dependencies.** E08.4 repeatable dedicated deployment and E08.2/T16 selected real connector; E06.4 portability/restore including correction backup/restore is inherited.

**Blockers.** Requires E08.4 second client, E08.2 real connector evidence, completed runbooks and independent owner acceptance. Any unavailable required component remains BLOCKED.

---

## Cross-story risks and constraints

1. **Real source selection is the critical path.** T16 cannot start without an owner-chosen connector, real sandbox and credentials; full T18/G3 depends on T16 evidence.
2. **No mocks as PASS.** Absent real source, second-client environment or recovery infrastructure leaves affected integration BLOCKED, not passing with mocks or inferred values.
3. **A19 belongs only to Epic 8.** The internal pilot (E07.3) does not close A19; second-client resource isolation and final G3 acceptance close A19 here.
4. **No deterministic auto-merge.** Even trusted diffs from source-managed content require human DecisionRecord and GO merge.
5. **Conditional extraction must be explicitly gated.** T17 is BLOCKED or N/A by ADR until owner-authorized real samples and activation decision exist.
6. **Privileged Owner bypass is an incident, not a path.** Any out-of-band privileged GitLab Owner merge triggers reconciliation, quarantine and the G0-D3 emergency runbook; it is never treated as normal managed flow.
7. **T19/T20 remain deferred.** This epic creates no retrieval-evolution or fast/trust/scale commitments.
