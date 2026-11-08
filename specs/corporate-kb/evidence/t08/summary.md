# T08 Scoped Working Context and Canonical Direct-Read Agent Tools Evidence Summary

- **Generated:** 2026-11-08T22:50:59.909873+00:00
- **Contracts version:** agent-tools-v2
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 10
- FAIL: 4
- BLOCKED: 4
- **Total:** 18

## Top findings

### FAIL
- `scope.scope_widening_rejected.widening_rejected` (scope): rejected; fixture `_bmad-output/test-artifacts/t08/fixtures/scenarios.yaml`
- `scope.missing_revision_sha.widening_rejected` (scope): rejected; fixture `_bmad-output/test-artifacts/t08/fixtures/scenarios.yaml`
- `direct_read.non_canonical_bypass.rejected` (direct_read): rejected; fixture `_bmad-output/test-artifacts/t08/fixtures/scenarios.yaml`
- `citation.revoked_cursor_rejected.revoked_cursor` (citation): revoked cursor rejected; fixture `_bmad-output/test-artifacts/t08/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_agent_scope_binding` (runtime): requires live sandbox and credentials
- `runtime.live_agent_canonical_read` (runtime): requires live sandbox and credentials
- `runtime.live_agent_citations` (runtime): requires live sandbox and credentials
- `runtime.live_agent_cursor_revocation` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.front_matter.valid` (schema): sample front matter is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `scope.page_scope_exact_sha.valid` (scope): model scope narrows server scope; exact revision SHA present
- `scope.subtree_scope_narrows.valid` (scope): model scope narrows server scope; exact revision SHA present
- `scope.space_scope_narrows_to_subtree.valid` (scope): model scope narrows server scope; exact revision SHA present
- `direct_read.canonical_read_with_bounds.canonical` (direct_read): direct read goes through GO at exact revision with bounds and cursor
- `citation.read_includes_citations.required` (citation): agent read/search results include citations with revision_sha and document_id
- `citation.search_includes_citations.required` (citation): agent read/search results include citations with revision_sha and document_id

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t08/run_t08_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
