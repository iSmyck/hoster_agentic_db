# Open WebUI integration patches

This directory contains patches applied to the pinned upstream Open WebUI checkout for the corp-ai-db G1 vertical slice.

The upstream checkout lives at `_bmad-output/test-artifacts/t00/upstream/open-webui` and is gitignored in this repo. Patches here record the exact modifications so they can be reapplied on a clean checkout.

## Patches

- `open-webui-t04b-wysiwyg.patch` — adds a WYSIWYG markdown editor (Source/Visual toggle) to Knowledge file viewer.

## Applying a patch

```bash
cd _bmad-output/test-artifacts/t00/upstream/open-webui
git apply ../../../../patches/open-webui-t04b-wysiwyg.patch
npm run build
```

After applying, the local stack orchestrator (`scripts/local_stack.py`) serves the built frontend via `FRONTEND_BUILD_DIR`.
