# T00 evidence — S3-compatible object store

## Scope

S3-compatible sandbox: LocalStack `3.8.1-arm64`, image digest `sha256:bd3800b7f9da5903d052f109bb315a874f66c6d86d8615f67c2b6f0824f41b21`. MinIO binary download was unavailable, and LocalStack `2026.10.6` required a paid auth token and was not used.

Raw result: `_bmad-output/test-artifacts/t00/objectstore/capability-results.json`

## Result

**5 PASS / 1 FAIL in LocalStack; production-engine ACL NOT RUN.**

| Capability | Result |
|---|---|
| Versioned write produces distinct version IDs | PASS |
| Old object version remains immutable after overwrite | PASS |
| Version listing contains both versions | PASS |
| Delete marker does not remove old version | PASS |
| Allowed reader can read object from its Space bucket | PASS |
| Other-Space/bucket denial | **FAIL in LocalStack; NOT RUN on production engine** |

## Immutable version evidence

- Version 1 SHA-256: `737a4637537b39dfb93932b2884fae9867a8a0de0d5744bed9380a522f724513`
- Version 2 SHA-256: `e4448763c24e6532e11cdfd1abbbc27a66604f01118c2db9d097488d3805afb1`

Both versions remained readable after a delete marker was added. This supports the required immutable attachment model `{object_id, version, sha256}`.

## ACL finding

A synthetic reader with an inline policy limited to the Space bucket still received HTTP 200 for the other bucket. An explicit bucket `Deny` policy also did not make the sandbox deny the request. Therefore S3 ACL enforcement is **not claimed** by this probe. It must be re-run against the selected production S3 engine and scoped credentials before T13/T16 acceptance.

## Consequences

- Object-store immutable version/hash semantics are feasible.
- Object-store ACL, source credential matrix, production retention, backup and restore remain open.
- T00 should not claim full object-store readiness or full export/restore readiness.

Raw result contains no credentials or real customer data.
