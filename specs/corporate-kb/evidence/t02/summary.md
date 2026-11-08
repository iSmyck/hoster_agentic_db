# T02 Document Tree and Direct Read Evidence Summary

- **Generated:** 2026-11-08T21:55:51.753670+00:00
- **Contracts version:** document-front-matter-v2
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** 788e299a5316c7d5df685a8f11b043ff36135a10
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 104
- FAIL: 5
- BLOCKED: 4
- **Total:** 113

## Top findings

### FAIL
- `front_matter.sales.bad-archived-no-archive.md.schema` (front_matter): 'archive' is a required property at []; fixture `_bmad-output<absolute-path-redacted>`
- `front_matter.sales.bad-unarchived-with-archive.md.schema` (front_matter): True was expected at ['archived']; fixture `_bmad-output<absolute-path-redacted>`
- `read.sales.malformed-heading.md.malformed_headings` (read): malformed headings at lines [(14, '####### This heading has too many hashes'), (16, '#This heading lacks a space')]; fixture `None`
- `archive.sales.bad-archived-no-archive.md.invariant` (archive): archived=True, has_archive=False; fixture `None`
- `archive.sales.bad-unarchived-with-archive.md.invariant` (archive): archived=False, has_archive=True; fixture `None`

### BLOCKED
- `runtime.live_gitlab_tree_read` (runtime): requires live GitLab/GO sandbox and ACL service
- `runtime.exact_revision_git_blob` (runtime): requires live GitLab/GO sandbox and ACL service
- `runtime.authz_read_rejection` (runtime): requires live GitLab/GO sandbox and ACL service
- `runtime.cross_space_link_resolution` (runtime): requires live GitLab/GO sandbox and ACL service

### PASS (sample)
- `harness.fixtures_loaded` (harness): two synthetic Space fixtures load
- `front_matter.sales.archived/obsolete.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales.index.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales.malformed-heading.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales.playbook.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales.products.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales-pricing.attachment/price-list.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales-pricing.discount.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales-pricing.index.md.schema` (front_matter): document front matter is schema valid
- `front_matter.sales-pricing.pricing.md.schema` (front_matter): document front matter is schema valid

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t02/run_document_tests.py
```

Real GitLab/IdP/CI/hoster.ai integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural/document evidence; it does not claim production integration PASS.
