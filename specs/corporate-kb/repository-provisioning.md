# Repository and Space provisioning proposal

Status: **APPROVED at G0-D13**. This is a provisioning design, not a command to create production repositories or load a corpus.

## 1. Namespace and identity model

Each dedicated client deployment receives one GitLab group namespace:

```text
kb-<client>/
  kb-space-<space_slug>
```

Rules:

- one GitLab repository = exactly one Space;
- repository `id` and `space_id` are the stable binding; repository name/path is not an identity key;
- `space_id` is a stable lowercase slug;
- a repository contains only one ACL perimeter, one canonical `main`, one cutover record and one index/export history;
- different ACL requirements are split into different repositories before cutover.

Example for a future client, not a production assignment:

```text
kb-client-a/
  kb-space-sales
  kb-space-hr
```

The actual client, group names and initial Spaces remain owner decisions.

## 2. Per-Space provisioning record

Each Space is registered in a versioned deployment registry with:

| Field | Purpose |
|---|---|
| `space_id` | Stable Space identifier |
| `gitlab_project_id` | Stable GitLab binding |
| `repository_path` | Provisioned namespace/path |
| `state` | `unpublished`, `cutover_ready`, `active`, `suspended` |
| `policy_bundle_id` | Access and approval policy binding |
| `go_service_identity` | Only normal merge actor |
| `index_profile_id` | Active index profile |
| `cutover_sha` | Exact initial published revision |
| `created_at`, `created_by` | Provisioning audit metadata |

Registry entries are configuration only; canonical document history remains in the Space repository.

## 3. Creation order

1. Owner approves `space_id`, ACL policy bundle and data profile.
2. Provision a private repository and stable GitLab project ID.
3. Create only synthetic or explicitly approved unpublished initial content.
4. Register service identities:
   - GO: Maintainer, sole normal merge actor;
   - agent/proposal writer: Developer, cannot merge;
   - CI/indexer: Reporter/read-only Git access;
   - connector/source: read-only source scope, no merge permission.
5. Configure `merge_method=merge` and protect `kb-decisions/*`; keep `main` unpublished with only the controlled import writer.
6. Execute unpublished import/dry-run and owner/data-barrier validation.
7. Freeze writes, require `HEAD == cutover_sha`, then enable protected `main` rules with no direct push and merge only through GO.
8. Create the protected annotated cutover tag and require a negative direct-push proof.
9. Build inactive preflight index and prove full dependency closure.
10. Create a separate same-SHA published request/run/snapshot, activate the pointer, then enable user access.
11. Register backup/export manifests and the first reconciliation schedule.

The Space is not publicly available before step 10.

## 4. Existing corpus migration

For an existing repository:

1. Inventory paths, owners, ACLs, links, assets and external originals.
2. Assign each document to exactly one target Space.
3. Split repositories before cutover if ACLs differ; do not place multiple ACL Spaces in one repository.
4. Preserve stable document IDs and provenance; record source path → target document ID mapping in the import manifest.
5. Use only the unpublished bulk-load exception.
6. Run link/asset/security/PII/data-barrier validation and expert sign-off before cutover.
7. If history rewrite is required, process it as a separate ADR with mirror/backup rotation and index-generation rebuild; do not silently rewrite published history.

## 5. Deletion and suspension

Space suspension disables user access and active index serving immediately, without deleting Git history. Repository deletion, privacy purge or filtered export requires a separate privileged ADR and is not part of normal provisioning.

## 6. Owner decisions still required

- Actual GitLab group namespace and client repository list.
- Initial Space IDs, business groups and path-scoped approval policies.
- Existing corpus mapping and whether any current repository must be split.
- Source connector, object-store layout and production cutover schedule.

This proposal closes the T00 design gap for repository-per-Space provisioning without creating production resources.
