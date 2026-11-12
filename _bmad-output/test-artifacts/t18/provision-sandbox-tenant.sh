#!/usr/bin/env bash
# Provisioning skeleton/checklist for the internal sandbox tenant.
# All values are parameterized via environment variables; no secrets are hard-coded.
# This script does not create real production resources. Inspect each step before running.

set -euo pipefail

: "${TENANT_ID:=tenant-sandbox-01}"
: "${TENANT_SLUG:=sandbox-01}"
: "${TENANT_LABEL:=Internal Sandbox 01}"
: "${BASE_DOMAIN:=sandbox-01.example.local}"
: "${PRIMARY_TENANT_ID:=tenant-primary}"

: "${KEYCLOAK_URL:=https://keycloak.example.local}"
: "${KEYCLOAK_ADMIN_USER:=admin}"
: "${KEYCLOAK_ADMIN_PASSWORD:?KEYCLOAK_ADMIN_PASSWORD is required}"
: "${KEYCLOAK_REALM:=corp-kb-sandbox-01}"

: "${GITLAB_URL:=https://gitlab.example.local}"
: "${GITLAB_ADMIN_TOKEN:?GITLAB_ADMIN_TOKEN is required}"
: "${GITLAB_TENANT_GROUP:=corp-kb-sandbox-01}"

: "${POSTGRES_HOST:=postgres.example.local}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_SUPERUSER:?POSTGRES_SUPERUSER is required}"
: "${POSTGRES_SUPERUSER_PASSWORD:?POSTGRES_SUPERUSER_PASSWORD is required}"
: "${POSTGRES_DATABASE:=corp_kb}"
: "${KB_AUTHZ_SCHEMA:=kb_authz_sandbox_01}"
: "${KB_OPS_SCHEMA:=kb_ops_sandbox_01}"
: "${KB_INDEX_SCHEMA:=kb_index_sandbox_01}"

: "${MINIO_URL:=https://minio.example.local}"
: "${MINIO_ROOT_USER:=minioadmin}"
: "${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}"
: "${MINIO_BUCKET:=corp-kb-sandbox-01}"

echo "=== Provisioning sandbox tenant: ${TENANT_ID} ==="

# 1. Keycloak realm and OIDC clients
# TODO: create realm ${KEYCLOAK_REALM}
# TODO: create client openwebui-${TENANT_SLUG}
# TODO: create client identity-service-${TENANT_SLUG}
# TODO: create tenant-scoped groups under /${TENANT_SLUG}
# TODO: verify no group or client name collides with ${PRIMARY_TENANT_ID}
echo "[ ] Keycloak realm ${KEYCLOAK_REALM} configured"

# 2. PostgreSQL schemas and roles
# TODO: connect to ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DATABASE}
# TODO: create schemas ${KB_AUTHZ_SCHEMA}, ${KB_OPS_SCHEMA}, ${KB_INDEX_SCHEMA}
# TODO: create roles *_writer / *_reader with least privilege
# TODO: grant usage on schema, revoke cross-schema writes
# TODO: run component migrations with schema-qualified alembic environment
echo "[ ] PostgreSQL schemas and roles created"

# 3. MinIO bucket and policies
# TODO: create bucket ${MINIO_BUCKET}
# TODO: create read/write policies scoped to arn:aws:s3:::${MINIO_BUCKET}/*
# TODO: create service credentials for GO, index worker and retrieval service
# TODO: verify primary-tenant credentials cannot access ${MINIO_BUCKET}
echo "[ ] MinIO bucket ${MINIO_BUCKET} provisioned"

# 4. GitLab tenant group and Space repositories
# TODO: create group ${GITLAB_TENANT_GROUP} with visibility private
# TODO: create at least one Space repository, e.g. ${GITLAB_TENANT_GROUP}/sales
# TODO: configure protected target branch and merge-only settings
# TODO: issue scoped group access tokens for Git Orchestrator
echo "[ ] GitLab group ${GITLAB_TENANT_GROUP} ready"

# 5. Service configuration placeholders
# TODO: set X-Tenant-ID header in inter-service calls
# TODO: point Open WebUI OIDC to openwebui-${TENANT_SLUG} client
# TODO: point identity/GO/retrieval services to schema and bucket names above
# TODO: store all secrets in deployment secret mechanism, never in Git
echo "[ ] Service configuration placeholders documented"

echo "=== Provisioning checklist complete for ${TENANT_ID} ==="
echo "WARNING: this script is a skeleton. No real resources were created."
