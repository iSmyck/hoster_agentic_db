# T00 evidence — personal Notes and ordinary chats regression

## Scope

Stock Open WebUI `v0.13.0`, synthetic PostgreSQL runtime and two non-admin users. The check used only synthetic notes/chats and API calls; no browser JavaScript or real user data.

Raw result: `_bmad-output/test-artifacts/t00/backend/notes-chats-results.json`

SHA-256 raw result: `713da7e509eb2e0aa874273f3dffdbd751f430c48c1aa66a13767babf926d43d`

## Result

**8 PASS / 0 FAIL**

| Check | Result |
|---|---|
| Note owner can read private note | PASS |
| Other user cannot read private note | PASS |
| Other user's note list excludes it | PASS |
| Chat owner can read private chat | PASS |
| Other user receives authorization denial for private chat | PASS |
| Other user's chat list excludes it | PASS |
| Note owner can create a note chat | PASS |
| Other user is denied for note chat | PASS |

The private chat endpoint returned HTTP 401 for the other user, which is an authorization denial in this context. Both users had already authenticated successfully, so it was not treated as token failure.

## Consequence

The pinned upstream personal Notes and ordinary chats baseline is compatible with the feature-flag boundary: personal content is private and other users cannot read or enumerate it. No migration of personal Notes/chats is required for the managed KB.

## Limitations

- This was an API/schema regression, not a browser E2E test.
- Collaborative editor behavior, IME, accessibility, XSS and browser diff are outside this check.
- Only non-admin users were used; no admin bypass semantics were evaluated.
