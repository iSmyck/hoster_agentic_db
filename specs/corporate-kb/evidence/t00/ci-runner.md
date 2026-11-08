# T00 evidence — GitLab Runner exact-SHA CI

## Scope

GitLab Runner `19.5.3`, git revision `33227fd4`, darwin/arm64, shell executor; GitLab CE `19.5.3`. Synthetic CI project `root/t00-runner-ci-dba72ce3d4dc` (id 21), protected `main`, pipeline 3 / job 2.

Raw result: `_bmad-output/test-artifacts/t00/runner/capability-results.json`

SHA-256 raw result: `3670b1bb4d8bd39085cff0920b110aee41ed5b03ce3a48a9f9b3bc1801d483c3`

## Result

**7 PASS / 0 FAIL / 0 BLOCKED**

| Capability | Result |
|---|---|
| Runner authentication via `POST /user/runners` and project runner registration | PASS |
| Runner received the job | PASS |
| `git rev-parse HEAD == CI_COMMIT_SHA` | PASS |
| `CI_COMMIT_REF_PROTECTED=true` and protected branch API confirmation | PASS |
| `git cat-file` reads commit and file content at exact SHA | PASS |
| Downloaded job artifact `sha-report.json` has expected and actual SHA matching `7e52c02a56f8bfcc703fbbde78fc96f1e7d3c8e7` | PASS |
| `main` SHA unchanged before and after the job; no push steps | PASS |

Pipeline 3 and job 2 completed with `success`. Runner was stopped, registration deleted, token-bearing config removed.

## Artifacts

- `evidence/sha-report.json`, SHA-256 `48cf9b8aaf37161807a5dfcf0184a379d7beabd185f30e7d0f185afc4b58afe0`;
- `evidence/job-2-trace.sanitized.txt`, SHA-256 `834756c1f936b58b1e0ab59cdeaf5ed6ba14b2afd9cf4e35d1f67eb7a84dca11`;
- `gitlab-ci.synthetic.yml` and `synthetic-payload.txt` — exact CI fixture.

## Consequences

CI can read an exact protected Git SHA without write-back, which is the required indexing seam. This is not evidence of a complete index worker, object-store, rollback or production CI queue. Artifact `ref` was empty because the job used `CI_COMMIT_REF` instead of `CI_COMMIT_REF_NAME`; `main` was confirmed via the job API.

## Limitations

- Shell executor on a single local runner, not HA/production autoscaling.
- No Docker executor, secret masking, cache policy, queue lag SLO or CI failure/retry matrix was tested.
- The synthetic CI project remains for evidence and is not a production repository.
