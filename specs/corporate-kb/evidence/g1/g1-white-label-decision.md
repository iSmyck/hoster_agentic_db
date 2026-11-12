# G1 White-label build configuration — decision record

## Decision

Owner approved a license-compliant white-label build step for the Open WebUI KB
overlay (ACT-012 / G1-D8). The implementation accepts brand asset paths via
environment variables, copies them into the build, generates a CSS override for
the splash screen, and injects the override at build time. Open WebUI copyright,
attribution, and LICENSE notices remain intact.

## Status

- **Owner approval:** accepted.
- **Actual logo/favicon assets:** pending. The build script does not commit or
  ship any real brand assets.
- **Final legal clearance:** required at build time via
  `WHITE_LABEL_LEGAL_CLEARANCE=1`; remains the owner's responsibility.

## Build configuration

- Script: `src/open-webui/scripts/white-label-build.js`
- Example environment file: `src/open-webui/.white-label-env.example`
- NPM script: `npm run kb:build:white-label` (defined in
  `src/open-webui/package.json`)
- Generated CSS: `upstream/static/kb-brand/white-label.css`
- Asset output directory: `upstream/static/kb-brand/`
- Operator documentation: `src/open-webui/README.md`

## Constraints preserved

- The default `npm run kb:build` is unchanged and continues to use upstream
  branding.
- The white-label step is opt-in and guarded by `WHITE_LABEL_LEGAL_CLEARANCE=1`.
- No brand assets are tracked in the repository.
- `upstream/src/app.html` is restored after the white-label build so tracked
  source remains unmodified.

## Evidence

- Implementation completed and verified: see
  `src/open-webui/scripts/white-label-build.js` and the verification logs for
  `npm run kb:build` and `npm run kb:build:white-label`.
