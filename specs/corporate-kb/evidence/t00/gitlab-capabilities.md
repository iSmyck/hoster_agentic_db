# T00 evidence — GitLab CE capabilities

## Scope

Проверен реальный synthetic sandbox GitLab CE `19.5.3` (`revision 0d4c9a9a2fa`), ARM64 image digest `sha256:800f8ce577ac408d6810b9f09f2d5c8412c388b8dc7b77e3421d3c1b4641efd1`. Использовались только synthetic projects, users, tokens и documents.

Raw result: `_bmad-output/test-artifacts/t00/gitlab/capability-results.json`

SHA-256 raw result: `dc05904040a84f7e2024860961418c385555889e9ef5f98d947e2484ca8336a7`

## Result

**42 completed harness checks / 0 blocked after local webhook setup.** Raw aggregate нормализован как `COMPLETED_WITH_NONCONFORMING_EVIDENCE`, а не `PASS`: target-race показывает nonconforming merge без GO lock, а canonical tamper probe — policy-level invalid/no-merge до вызова GitLab merge.

| Capability | Result | Evidence |
|---|---|---|
| GitLab version, revision, API auth, local git | PASS | CE 19.5.3, API `/user`, `/version`, git rev-parse |
| Repository-per-Space isolation | PASS | Cross-Space file/history/export denied |
| Protected `main`, no direct push | PASS | `push_access_level=0`; business and engineering probes denied |
| Merge only through GO for non-admin roles | PASS | Developer/Reporter direct merge denied; only GO Maintainer merged |
| CE role-based protected branch profile | PASS | `merge_access_level=40`; per-user protected branch grants are Premium/Ultimate and unavailable in CE |
| Instance/project Owner boundary | **OBSERVED BYPASS / G0-DECISION** | GitLab root/Owner merged outside GO; absolute merge-only-GO is not guaranteed. Admin governance and reconciliation are required |
| Merge method and trailers | PASS | `merge_method=merge`, trailers `Decision-ID`, `Decision-Note-ID`, `Decision-Hash`, `Approved-by`; adversarial rebase and FF probes rejected HTTP 405 with no `main` write |
| Exact source SHA rejection | PASS | GitLab rejects stale source SHA with HTTP 405 and leaves `main`/MR unchanged |
| Target-branch CAS | NOT PROVIDED by GitLab | Target HEAD precondition is not an atomic GitLab compare-and-swap; GO serialization and durable recovery barrier are mandatory |
| GO lock and target-race protection | **NONCONFORMING MERGE OBSERVED** | GitLab merged against advanced target; first parent is advanced target, not reviewed base; no atomic target CAS. GO per-target lock is mandatory |
| Merge parentage | PASS | Accepted merge commit has first parent `base_sha` and second parent `proposal_sha` |
| Canonical DecisionRecord | PASS | Accept/reject/cancel JSON written to MR note and protected annotated tag `kb-decisions/<uuid>` |
| DecisionRecord after canonical note mutation | PASS as policy probe | Canonical note was actually mutated; recomputed hash and note/tag mismatch were detected, decision became `invalid`, `merge_attempted=false`, `main` unchanged. Product implementation remains pending |
| Decision export after source-branch deletion | PASS | MR notes and decision tags remain fetchable; tags are included in clone/fetch |
| Cutover | PASS | Controlled pre-cutover write, write freeze, exact `cutover_sha`, protected annotated tag and post-cutover no-direct-write matrix |
| Protected branch settle | PASS with operational rule | GitLab locally exhibited a brief propagation race; cutover must activate users/merges only after negative push proof |
| Webhook | PASS | Signed event delivered after enabling local webhook URLs only inside the sandbox; production requires allowlist, not local relaxation |
| Metadata export | PASS | MR notes/tags and repository refs fetched into export evidence |

## Required implementation consequences

1. GitLab CE is sufficient for the selected design without Premium CODEOWNERS approval gates; business approval is platform-side.
2. `merge_access_level=40` plus exclusive GO Maintainer membership is the CE-native enforcement profile.
3. GitLab root and project Owners remain privileged break-glass actors. GO reconciliation must detect out-of-band merges; owner must accept or restrict those accounts operationally.
4. GO must serialize every merge per repository/target branch and keep the durable `recovery_required` barrier. GitLab does not provide target-branch CAS.
5. Cutover runbooks must include a protection-settle proof before user/index activation.
6. Protected decision tags are required for clone/export durability; MR notes alone are GitLab metadata.
7. Local webhook relaxation is sandbox-only. Production webhook delivery must use reachable allowlisted endpoints and secret validation.

## Limitations

- No GitLab EE/Ultimate capabilities were purchased or tested.
- No GitLab HA, backup appliance or production network was tested.
- No real AD groups, users, documents or secrets were used.
- MR events exposed note creation but no distinct edit audit event for the canonical tamper; immutable audit therefore relies on the protected annotated tag and hash comparison, not on a mutable MR activity stream.
- Object-store/source credential matrix is not covered by the GitLab-only harness.
- This evidence does not approve G0 by itself; it is the GitLab capability input.
