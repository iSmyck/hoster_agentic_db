# Open WebUI KB Overlay

This directory contains a **minimal overlay** for the corporate knowledge-base (KB) seams on top of the pinned Open WebUI `v0.13.0` upstream.

## Layout

```text
src/open-webui/
├── upstream/              # Pinned Open WebUI checkout (git-ignored, not tracked)
├── src/                   # Overlay TypeScript / Svelte source
│   ├── lib/api/kb.ts
│   ├── lib/components/KBTree.svelte
│   ├── lib/components/KBDocumentRead.svelte
│   └── lib/routes/kb/+page.svelte
├── tests/kb-client.test.ts
├── package.json           # Overlay dependencies and scripts
├── tsconfig.json          # TypeScript project spanning upstream + overlay
├── setup-openwebui.sh     # Clone / verify pinned upstream checkout
└── README.md              # This file
```

## One-time setup

Run the setup script to materialize the pinned upstream checkout under `upstream/`:

```bash
./setup-openwebui.sh
```

The script clones `https://github.com/open-webui/open-webui.git` and checks out commit `c38885a1a737da4968f157092f304f3b5481d0bf` if `upstream/` is missing or not at that commit. It is safe to run multiple times.

## How the overlay works

- Tracked files live in `src/open-webui/`. They add:
  - a typed KB API client (`src/lib/api/kb.ts`);
  - a document-tree component (`KBTree.svelte`);
  - a document-read component (`KBDocumentRead.svelte`);
  - a KB page combining both (`src/lib/routes/kb/+page.svelte`).
- The upstream checkout in `upstream/` is **not committed**; it is a build/runtime dependency.
- Build commands in `package.json` copy overlay files into the upstream tree and then invoke upstream tooling. This keeps the overlay small and avoids forking the entire 3.8 GB repository.

## Available scripts

Run from `src/open-webui/`:

```bash
# Install overlay dependencies (assumes upstream is already present)
npm install

# Run overlay unit tests for the KB API client
npm run kb:test

# Type-check upstream + overlay after merging overlay files
npm run kb:check

# Build production bundle using upstream Vite/SvelteKit
npm run kb:build
```

## Service wiring

The KB client talks to the existing backend adapters:

- `git-orchestrator` — `POST /api/kb/v1/documents/tree`, `POST /api/kb/v1/documents/read`
- `identity` — `POST /api/kb/v1/identity/resolve`, `POST /api/kb/v1/authz/context`, `POST /api/kb/v1/authz/check`

The client defaults to relative paths so Open WebUI's Vite dev proxy can forward them. Override the base URLs with the environment variables documented in `src/lib/api/kb.ts` if you run the client outside the Open WebUI dev server.

## Caveats

- `upstream/` is a large (≈3.8 GB) dependency. Do not commit it.
- Full build (`kb:build`) requires the upstream checkout to be present and its `node_modules` installed.
- Upstream `svelte-check`, ESLint, and `npm run build` are known baseline debt (G0-D9) and are not treated as release gates; use `kb:check` / direct Vite build for overlay validation.
