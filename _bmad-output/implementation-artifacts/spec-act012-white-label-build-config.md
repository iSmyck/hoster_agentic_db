---
title: 'ACT-012 — License-compliant white-label build configuration'
type: 'feature'
created: '2026-11-12'
status: 'done'
baseline_revision: 'a5c2c06c4873817e153f53812eb36d1e4ff400c6'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Owner approved a license-compliant white-label build step with asset paths via environment variables (G1-D8 / ACT-012). Actual logo/favicon assets and final legal clearance remain pending, but the build configuration must be ready so assets can be swapped without code changes once they arrive.

**Approach:** Add an optional white-label build script to the Open WebUI overlay that accepts asset paths via environment variables, copies them into the build, generates a CSS override, and injects it at build time. Keep Open WebUI attribution intact and document the legal clearance requirement.

## Boundaries & Constraints

**Always:**
- Accept asset paths via environment variables; never hard-code brand assets.
- Keep Open WebUI copyright / attribution notices intact.
- Make white-label build opt-in (`npm run kb:build:white-label`); default build remains unchanged.
- Document that final legal clearance and asset ownership are the owner's responsibility.
- Verify the default build still passes.

**Never:**
- Commit real logo/favicon assets.
- Remove or hide Open WebUI attribution without explicit owner legal clearance.
- Break the existing default `npm run kb:build`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| White-label build with assets | Env vars point to valid logo/favicon/splash files | Build succeeds with custom assets in `/static/kb-brand/` and CSS override injected | Clear error if asset missing |
| White-label build without assets | Env vars unset | Build uses default Open WebUI branding; only CSS shell created | Warning logged |
| Default build | `npm run kb:build` | No white-label changes; upstream assets remain | No error |
| Missing legal clearance | — | Script refuses to run unless `WHITE_LABEL_LEGAL_CLEARANCE=1` is set | Error with explanation |

</intent-contract>

## Code Map

- `src/open-webui/scripts/white-label-build.js` -- new build script.
- `src/open-webui/.white-label-env.example` -- example environment variables.
- `src/open-webui/package.json` -- add `kb:build:white-label` script.
- `src/open-webui/README.md` -- document white-label usage and legal clearance requirement.
- `specs/corporate-kb/evidence/g1/g1-white-label-decision.md` -- evidence / decision record (update or create).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- ACT-012 to done.

## Tasks & Acceptance

**Execution:**
- `src/open-webui/scripts/white-label-build.js` -- create Node.js script that:
  - Validates `WHITE_LABEL_LEGAL_CLEARANCE=1`.
  - Runs `kb:merge`.
  - Copies assets from `WEBUI_LOGO_PATH`, `WEBUI_FAVICON_PATH`, `WEBUI_SPLASH_LIGHT_PATH`, `WEBUI_SPLASH_DARK_PATH` into `upstream/static/kb-brand/` if set.
  - Generates `upstream/static/kb-brand/white-label.css` that overrides splash/logo CSS without removing attribution.
  - Injects the CSS link into `upstream/src/app.html` at build time via string replacement (preserving LICENSE comments).
  - Runs the upstream Vite build.
  RATIONALE: implements license-compliant white-label build step.
- `src/open-webui/.white-label-env.example` -- example env file with placeholders. RATIONALE: discoverability.
- `src/open-webui/package.json` -- add `kb:build:white-label` script. RATIONALE: easy invocation.
- `src/open-webui/README.md` -- document white-label build, env vars, legal clearance requirement, and default fallback. RATIONALE: operator guidance.
- `specs/corporate-kb/evidence/g1/g1-white-label-decision.md` -- decision record noting owner approval, pending assets, and build config. RATIONALE: reviewable evidence.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- set ACT-012 to `done`, update overall_percent to 85. RATIONALE: reflect closure.

**Acceptance Criteria:**
- Given the overlay, when `npm run kb:build` is executed, then it succeeds without white-label modifications.
- Given `WHITE_LABEL_LEGAL_CLEARANCE=1` and valid asset paths, when `npm run kb:build:white-label` is executed, then it succeeds and the build contains `/static/kb-brand/` assets.
- Given the evidence report, when reviewed, then it states owner approval, pending assets, and build configuration location.
- Given the sprint status file, when updated, then ACT-012 is `done` and overall_percent is 85.

## Spec Change Log

## Review Triage Log

### 2026-11-12 — Review pass (self-review)
- verdicts: 2 findings — high 0, medium 0, low 0, false 0, maybe-false 2
- findings:
  - `[maybe-false]` `[defer]` CSS override targets only splash/logo selectors; other in-app brand surfaces may need additional selectors once real assets and full brand requirements are known.
  - `[maybe-false]` `[defer]` Favicon mime-type detection is heuristic based on file extension; exotic formats may need manual adjustment.

## Design Notes

The script uses build-time string replacement in `app.html` rather than committing a modified upstream file. This keeps the LICENSE-covered source surface intact in the repository and makes the white-label step an explicit, auditable build operation. The CSS override targets only the splash/logo elements and leaves attribution/footer text untouched.

## Verification

**Commands:**
- `cd src/open-webui && npm run kb:build` -- expected: succeeds (no white-label changes).
- `cd src/open-webui && WHITE_LABEL_LEGAL_CLEARANCE=1 npm run kb:build:white-label` -- expected: succeeds; check `upstream/static/kb-brand/` exists.
- `python -c "import yaml; yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status.yaml'))"` -- expected: no parse errors.

**Manual checks (if no CLI):**
- Inspect `src/open-webui/scripts/white-label-build.js` for legal-clearance guard and env var handling.
- Inspect `specs/corporate-kb/evidence/g1/g1-white-label-decision.md` for closure summary.
- Inspect `sprint-status.yaml` action_items for ACT-012 status.

## Auto Run Result

- Summary: ACT-012 closed by creating a license-compliant white-label build configuration. The opt-in `kb:build:white-label` script validates legal clearance, accepts asset paths via env vars, copies assets into the build, generates a CSS override, and injects it at build time. Default `kb:build` remains unchanged. Sprint status updated; overall_percent raised to 85.
- Files changed:
  - `src/open-webui/scripts/white-label-build.js` — new white-label build script.
  - `src/open-webui/.white-label-env.example` — example env file.
  - `src/open-webui/package.json` — added `kb:build:white-label` script.
  - `src/open-webui/.gitignore` — ignored local `.white-label-env`.
  - `src/open-webui/README.md` — documented white-label usage and legal clearance.
  - `specs/corporate-kb/evidence/g1/g1-white-label-decision.md` — decision/closure evidence.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — ACT-012 done, overall_percent 85.
- Review findings: 2 maybe-false deferred (additional brand surfaces, exotic favicon formats).
- Follow-up review recommended: false.
- Verification performed:
  - `node --check scripts/white-label-build.js` → passed.
  - `npm run kb:build` → passed (default build unchanged).
  - `WHITE_LABEL_LEGAL_CLEARANCE=1 npm run kb:build:white-label` → passed.
  - `npm run kb:build:white-label` without clearance → refused with clear message.
  - YAML parse check → OK.
- Residual risks:
  - Real logo/favicon/splash assets and final legal clearance are still pending.
  - CSS override is scoped to splash/logo; additional selectors may be needed.
