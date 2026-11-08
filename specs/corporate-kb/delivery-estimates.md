# T00 delivery estimation assumptions and first two delivery-sprint scenarios

Status: **LOW-CONFIDENCE planning input, not a commitment**. Ranges are derived from the baseline evidence and adapter scope, not from a calendar target.

## 1. Estimation model

Assumed cross-functional capacity for planning only:

| Role | Capacity per two-week sprint |
|---|---:|
| Backend engineer | 10 person-days |
| Frontend engineer | 5 person-days |
| QA / test engineer | 5 person-days |
| DevOps / security | 2 person-days |
| Product owner / domain review | 2 person-days |
| **Total gross capacity** | **24 person-days** |
| **Commitment capacity after 15–20% reserve** | **19.2–20.4 person-days** |

A different real team composition changes the plan; no velocity is inferred from the withdrawn v1.1 estimates.

## 2. Delivery Sprint 1 — contracts, document/Space skeleton and identity seam

Scope: T01 contract harness, initial T02 repository/Space/document mapping, initial T03 identity/AuthZ adapter seam, synthetic CI/evidence setup.

| Work item | Range, person-days |
|---|---:|
| T01 projection/contract validation and fault fixtures | 5–8 |
| T02 Space/document/front-matter/read mapping | 4–7 |
| T03 initial identity and policy adapter seam | 6–9 |
| Sandbox/CI/evidence integration and review | 3–5 |
| **Total** | **18–29** |

Capacity-based plan:

- Commit only T01 and T02 read-side slice plus identity spike up to **19.2–20.4 person-days** after the reserve.
- Keep 15–20% unallocated for upstream and fixture surprises.
- Do not start T04 editor or full merge implementation in this sprint.
- Exit evidence: reproducible synthetic environments, T01 negative vectors, two-Space read model and a completed T03 identity/AuthZ adapter baseline suitable for T04 entry.

Confidence: **LOW**. Main risks: upstream schema/identity differences, missing local backend tests, LDAP/OIDC adapter behavior and frontend quality debt.

## 3. Delivery Sprint 2 — draft/proposal/DecisionRecord and minimal merge path

Scope: initial T04 draft/save, T05 ProposalRecord/DecisionRecord/merge/recovery, T06 bypass enforcement; only the minimal T07 review surface that fits remaining capacity. **Entry dependency:** T03 must be complete before T04 starts; if it is incomplete, this sprint first finishes T03 and T04–T07 shift right.

| Work item | Range, person-days |
|---|---:|
| T04 draft/save/conflict/revision integration | 4–8 |
| T05 ProposalRecord/DecisionRecord/GO merge/recovery | 8–14 |
| T06 protected branch/credential/bypass checks | 4–7 |
| T07 minimal review/approve/reject UX | 4–8 |
| Security/concurrency evidence and review | 4–6 |
| **Total** | **24–43** |

Capacity-based plan:

- Commit only the single-page draft → proposal → DecisionRecord → merge path with T06 negative tests up to **19.2–20.4 person-days** after the reserve.
- Defer full editor WYSIWYG adapter and non-critical T07 UX polish if the range exceeds capacity.
- Exit evidence: exact base/proposal SHA, canonical DecisionRecord note+tag, parent/trailer validation, no direct merge/push and crash/quarantine checks.

Confidence: **VERY LOW**. Main risks: editor adapter, target-race/recovery semantics, privileged admin bypass and browser accessibility/XSS checks.

## 4. Estimation consequences from T00

| Finding | Planning effect |
|---|---|
| Stock identity and tool approval need adapters | Increase T03/T09 uncertainty; no configuration-only estimate |
| External migration owner is required | Include DevOps/migration rehearsal in every deployment increment |
| GitLab has no target-branch CAS and shows nonconforming race | Keep dedicated concurrency/recovery QA in T05/T06 |
| TipTap current path loses canonical constructs | Do not promise WYSIWYG in Sprint 1; editor direction is G0-D8 |
| Frontend typecheck/ESLint/build-script debt | Reserve explicit stabilization time; do not hide it in feature estimates |
| GitLab privileged Owner bypass | Add admin governance and out-of-band reconciliation acceptance |
| Object store and production AD/IdP remain unverified | Keep later integration work out of the first two sprint commitments |

## 5. Owner decisions that can change these ranges

- TipTap adapter vs CodeMirror vs hybrid editor direction.
- OIDC-only baseline vs additional LDAP/LDAPS adapter.
- Preserving Open WebUI branding vs obtaining enterprise/white-label rights.
- Actual team size and QA/DevOps availability.
- Whether the first slice requires browser accessibility/XSS and personal Notes/chats regression before implementation.
