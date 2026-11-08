# T04b Lossless TipTap Adapter and Browser Editor Gate Evidence Summary

- **Generated:** 2026-11-08T22:20:43.525067+00:00
- **Contracts version:** document-front-matter-v2
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_browser
- **Sensitive data present:** False

## Counts

- PASS: 24
- FAIL: 0
- BLOCKED: 5
- **Total:** 29

## Top findings

### BLOCKED
- `runtime.live_browser_ime_composition` (runtime): requires sandboxed browser automation and credentials
- `runtime.live_screen_reader_labels` (runtime): requires sandboxed browser automation and credentials
- `runtime.live_keyboard_focus_navigation` (runtime): requires sandboxed browser automation and credentials
- `runtime.live_xss_render_exposure` (runtime): requires sandboxed browser automation and credentials
- `runtime.live_managed_preview_save` (runtime): requires sandboxed browser automation and credentials

### PASS (sample)
- `harness.fixtures_loaded` (harness): synthetic editor fixtures load
- `schema.front_matter.valid` (schema): sample front matter is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `round_trip.canonical_full.lossless` (round_trip): canonical constructs preserved and only intended changes present
- `round_trip.canonical_minimal.lossless` (round_trip): canonical constructs preserved and only intended changes present
- `round_trip.cyrillic_body.lossless` (round_trip): canonical constructs preserved and only intended changes present
- `round_trip.stable_links_and_valid_until.lossless` (round_trip): canonical constructs preserved and only intended changes present
- `front_matter_boundary.closed_boundary.closed` (front_matter_boundary): front-matter boundary remains closed and intact
- `front_matter_boundary.archived_with_boundary.closed` (front_matter_boundary): front-matter boundary remains closed and intact

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py
```

Real browser automation/IME/accessibility/XSS rendering checks remain BLOCKED until a sandboxed browser environment exists. This report contains only synthetic structural editor evidence; it does not claim production browser PASS.
