# T17 Conditional Evidence-Gated Extraction, Media and OCR Quality Evidence Summary

- **Generated:** 2026-11-10T11:25:42.921876+00:00
- **Contracts version:** extraction-gating-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 21
- FAIL (expected): 14
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 39

## Top findings

### FAIL (expected)
- `route_activation_gate.missing_samples_blocked.rejected` (route_activation_gate): activation gate problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `route_activation_gate.missing_format_agreement_blocked.rejected` (route_activation_gate): activation gate problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `docling_assessment.second_pipeline_without_adr_rejected.rejected` (docling_assessment): Docling assessment problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `docling_assessment.docling_not_assessed_rejected.rejected` (docling_assessment): Docling assessment problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `golden_fixtures.unsupported_format_rejected.rejected` (golden_fixtures): golden fixture problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `golden_fixtures.missing_reading_order_rejected.rejected` (golden_fixtures): golden fixture problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `loss_quarantine.loss_partial_index_rejected.rejected` (loss_quarantine): loss/quarantine problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `loss_quarantine.loss_source_merged_rejected.rejected` (loss_quarantine): loss/quarantine problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `media_classes.critical_not_verified_rejected.rejected` (media_classes): media class problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `media_classes.substantive_missing_cite_rejected.rejected` (media_classes): media class problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `malicious_malformed.malicious_allowed_rejected.allowed` (malicious_malformed): malicious/malformed sample allowed; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `provider_profile_egress.unapproved_provider_rejected.rejected` (provider_profile_egress): provider/profile/egress problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `provider_profile_egress.unplanned_fallback_rejected.rejected` (provider_profile_egress): provider/profile/egress problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`
- `provider_profile_egress.pii_egress_rejected.rejected` (provider_profile_egress): provider/profile/egress problem detected; fixture `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_docling_quality` (runtime): requires owner-authorized real samples and extraction sandbox
- `runtime.live_ocr_golden_set` (runtime): requires owner-authorized real samples and extraction sandbox
- `runtime.live_media_classification` (runtime): requires owner-authorized real samples and extraction sandbox
- `runtime.live_owner_authorized_samples` (runtime): requires owner-authorized real samples and extraction sandbox

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `route_activation_gate.markdown_only_na.valid` (route_activation_gate): non-Markdown route activated only with owner samples, format agreement, quality review and data/media profile
- `route_activation_gate.non_markdown_activated.valid` (route_activation_gate): non-Markdown route activated only with owner samples, format agreement, quality review and data/media profile
- `docling_assessment.docling_only.valid` (docling_assessment): Docling assessed first; second pipeline requires documented need, approved ADR and compatibility/license/rollback assessment
- `docling_assessment.docling_plus_second_pipeline_with_adr.valid` (docling_assessment): Docling assessed first; second pipeline requires documented need, approved ADR and compatibility/license/rollback assessment
- `golden_fixtures.pdf_golden_complete.valid` (golden_fixtures): golden fixtures measure page/slide counts, encoding, reading order, table/numbers, links/anchors
- `golden_fixtures.pptx_golden_complete.valid` (golden_fixtures): golden fixtures measure page/slide counts, encoding, reading order, table/numbers, links/anchors
- `loss_quarantine.clean_extraction.valid` (loss_quarantine): loss/garbled/unsupported/OCR-disagreement quarantined with original recoverable; source not merged; no partial index

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t17/run_t17_tests.py
```

Real non-Markdown extraction sample authorization, golden/loss evaluation and OCR quality evidence remain BLOCKED. This report contains only synthetic gating evidence; it does not claim production extraction PASS.
