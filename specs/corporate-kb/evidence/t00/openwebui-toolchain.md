# T00 evidence — Open WebUI frontend and backend toolchain

## Scope

Pinned checkout: Open WebUI `v0.13.0`, commit `c38885a1a737da4968f157092f304f3b5481d0bf`.

Raw artifacts:

- `_bmad-output/test-artifacts/t00/backend/ruff-format.txt`
- `_bmad-output/test-artifacts/t00/backend/ruff-ci.txt`
- `_bmad-output/test-artifacts/t00/backend/pytest.txt`
- `_bmad-output/test-artifacts/t00/backend/runtime-results.json`
- `_bmad-output/test-artifacts/t00/frontend/svelte-check.txt`
- `_bmad-output/test-artifacts/t00/frontend/eslint.txt`
- `_bmad-output/test-artifacts/t00/frontend/vitest.txt`
- `_bmad-output/test-artifacts/t00/frontend/results.json`
- `_bmad-output/test-artifacts/t00/frontend/build-results.json`

## Backend result

| Check | Result | Evidence |
|---|---|---|
| Python range | PASS | Upstream supports Python `>=3.11,<3.13`; sandbox used 3.12.13 |
| `uv sync --frozen --group dev` | PASS | Dependencies installed from `uv.lock` |
| `uv sync --frozen --group dev --extra postgres` | PASS | `pgvector==0.4.2`, `psycopg2-binary==2.9.12` installed |
| Ruff format check | PASS | Exit 0 |
| Upstream CI Ruff command | PASS | Exit 0 with upstream-selected F rules/ignores |
| Pytest | NO LOCAL SUITE | Exit 5; no backend tests were collected |
| External Alembic migrator | PASS | 51 upstream tables, head `e42c8f710a36` |
| Runtime API on PostgreSQL/pgvector | PASS | `/api/config` returned Open WebUI `0.13.0` |
| Runtime DDL denial | PASS | Runtime role could read but could not create tables in `openwebui` schema |
| pgvector extension/table ownership | PASS with operational requirement | Extension and schema must be pre-provisioned by a privileged migrator |

## Frontend result

| Check | Result | Evidence |
|---|---|---|
| Node engine | PASS | Node 22.23.4 satisfies upstream `<=22.x.x`; host Node 26 was not used |
| `npm ci` | PASS | Completed with `CYPRESS_INSTALL_BINARY=0` |
| Vitest | PASS | 1 test file, 4 tests passed |
| Direct Vite build | PASS | 5706 files, 246,018,942 bytes, `build/index.html` present |
| Upstream `npm run build` | FAIL | Exit 137; hardcoded 12 GiB Node heap exceeded the 12 GiB Docker allocation |
| `npm run check` / svelte-check | FAIL | 5722 errors and 191 warnings |
| Non-mutating ESLint | FAIL | `@typescript-eslint/no-unused-vars` crashed on `ModelDefaultsPanel.svelte` |
| Browser/E2E | NOT RUN | Cypress binary was intentionally not installed; no browser evidence |

## Baseline consequences

1. The reproducible backend profile is `uv sync --frozen --group dev --extra postgres`; a bare dev profile is insufficient for pgvector runtime.
2. Runtime migrations are disabled; a separate migrator role performs Alembic upgrades and verifies head `e42c8f710a36` before application startup.
3. Upstream frontend build is possible with a 6 GiB direct Vite invocation, but the stock `npm run build` script needs either more Docker memory or a build-profile adjustment.
4. The upstream typecheck and ESLint gates are not currently releasable baseline gates; build and existing Vitest pass, but code-quality debt must be tracked explicitly.
5. The external regression workflow points to a moving `@main` reusable workflow and cannot be treated as a pinned reproducible test baseline without pinning that repository separately.
