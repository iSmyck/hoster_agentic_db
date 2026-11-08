# T00 evidence — environment and pinned versions

## Host and tools

- Host: macOS ARM64
- Docker Desktop: 8 CPUs, 12 GiB memory
- Git object format: SHA-1
- uv: 0.11.13
- Python host: 3.14.6; Open WebUI backend sandbox: Python 3.12.13
- Node frontend sandbox: 22.23.4
- pnpm host: 11.8.0
- Docker: 29.5.2
- Git: 2.47.0
- Ollama: 0.28.0

Raw environment manifest: `_bmad-output/test-artifacts/t00/environment.json`

SHA-256: `04942b06f8da466cb5d6141d2160e987db05b1bc732059dcbdabcbbc9bc1731f`

## Pinned components

| Component | Selected baseline | Evidence |
|---|---|---|
| Open WebUI | `v0.13.0`, commit `c38885a1a737da4968f157092f304f3b5481d0bf` | GitHub release and exact tag SHA |
| GitLab | CE `19.5.3-ce.0`, revision `0d4c9a9a2fa` | Docker image digest and API result |
| PostgreSQL / pgvector | PostgreSQL 18.6, pgvector 0.8.7, image `pgvector/pgvector:0.8.7-pg18-trixie` | Runtime and benchmark results |
| GitLab Runner | 19.5.3, git revision `33227fd4`, Go 1.26.10, darwin/arm64 | Official binary version check |
| Keycloak | 26.8.2 | Real OIDC/Admin API sandbox |
| Embedding benchmark model | Ollama `bge-m3:567m`, digest `sha256:7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`, 1024 dimensions | Synthetic retrieval benchmark only |
| Frontend runtime | Node 22.23.4 bookworm pinned image | npm/Vitest/Vite checks |

## Sandboxes

- GitLab: `localhost:8080`, synthetic service users and projects only.
- PostgreSQL: `localhost:55432`, synthetic databases only.
- Keycloak: `localhost:8443`, synthetic realms/users/groups only.
- Ollama: local `localhost:11434`, only the public embedding model.
- Open WebUI backend: `localhost:3100`, synthetic PostgreSQL database.

## Deliberately not included

- No hoster.ai endpoint or model ID.
- No real customer documents.
- No production secrets.
- No production AD/LDAP tenant.
- No GitLab EE/Ultimate entitlement.
