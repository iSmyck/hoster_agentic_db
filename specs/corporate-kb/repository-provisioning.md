# Repository and Space provisioning proposal

Status: **APPROVED at G0-D13**. GitLab placement and Shared/Dedicated profiles are clarified by **ADR-17, accepted by the project owner on 2026-11-09**. This is a provisioning design, not a command to create production repositories or load a corpus.

## 1. Namespace and identity model

Each dedicated client deployment receives one GitLab group namespace. The group is hosted either on a shared hardened GitLab instance (`shared`) or on a separate client instance (`dedicated`) according to the tenant profile and [ADR-17](adr/ADR-017-gitlab-deployment-topology.md). GitLab itself remains outside the client application namespace and its release lifecycle; shared hosting never implies shared canonical repositories, managed credentials or client backup packages. Restricted platform-wide DR is governed separately by ADR-17.

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

Each Space is registered in a versioned deployment registry. `gitlab_mode`, `gitlab_instance_id` and the client group are client-level values inherited as read-only bindings by every Space of that client; mixed-mode or mixed-instance overrides within one client are invalid. Per-Space records contain:

| Field | Purpose |
|---|---|
| `space_id` | Stable Space identifier |
| `gitlab_mode` | `shared` or `dedicated` deployment profile from ADR-17 |
| `gitlab_instance_id` | Trusted logical GitLab instance binding; not a client-supplied agent argument |
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

1. Owner approves `space_id`, ACL policy bundle, data profile and the ADR-17 `shared`/`dedicated` tenant profile with a trusted GitLab instance binding.
2. Provision a private repository and stable GitLab project ID outside the client application namespace lifecycle.
3. Create only synthetic or explicitly approved unpublished initial content.
4. Register service identities with explicit `(tenant_id,space_id,repository_id,capability)` scope; client group membership alone is not sufficient:
   - GO: Maintainer, sole normal merge actor for this Space repository;
   - agent/proposal writer: Developer, cannot merge and cannot access another Space by default;
   - CI/indexer: Reporter/read-only Git access for this Space repository;
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

- Actual GitLab instance/profile assignment, group namespace and client repository list. The `shared`/`dedicated` decision mechanism is fixed by ADR-17; production placement remains an owner input.
- Initial Space IDs, business groups and path-scoped approval policies.
- Existing corpus mapping and whether any current repository must be split.
- Source connector, object-store layout and production cutover schedule.

This proposal closes the T00 design gap for repository-per-Space provisioning without creating production resources.
