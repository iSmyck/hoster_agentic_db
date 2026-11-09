# T14 Reproducible Quality, Safety and Operational Evaluation Evidence Summary

- **Generated:** 2026-11-08T23:50:40.937735+00:00
- **Contracts version:** eval-harness-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 15
- FAIL (expected): 14
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 33

## Top findings

### FAIL (expected)
- `eval_case_versioning.missing_corpus_sha_rejected.rejected` (eval_case_versioning): versioning problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `eval_case_versioning.unapproved_grader_rejected.rejected` (eval_case_versioning): versioning problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `quality_metrics.undifferentiated_score_rejected.rejected` (quality_metrics): quality metrics problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `quality_metrics.missing_abstention_rejected.rejected` (quality_metrics): quality metrics problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `citation_groundedness.unsupported_answer_rejected.rejected` (citation_groundedness): groundedness problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `citation_groundedness.silent_stale_substitution_rejected.rejected` (citation_groundedness): groundedness problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `citation_groundedness.llm_judge_sole_arbiter_rejected.rejected` (citation_groundedness): groundedness problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `deterministic_adversarial.probabilistic_only_rejected.rejected` (deterministic_adversarial): adversarial suite problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `deterministic_adversarial.unauthorized_disclosure_rejected.rejected` (deterministic_adversarial): adversarial suite problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `operational_measurements.missing_git_merge_latency_rejected.rejected` (operational_measurements): operational metrics problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `observability.missing_correlation_rejected.rejected` (observability): observability problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `russian_golden_set.missing_golden_answer_rejected.rejected` (russian_golden_set): golden set problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `russian_golden_set.live_inference_claim_rejected.rejected` (russian_golden_set): golden set problem detected; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`
- `human_in_the_loop.automated_only_disposition_rejected.rejected` (human_in_the_loop): human review missing; fixture `_bmad-output/test-artifacts/t14/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_hoster_quality_inference` (runtime): requires live hoster.ai sandbox, model outputs and credentials
- `runtime.live_russian_golden_set_grading` (runtime): requires live hoster.ai sandbox, model outputs and credentials
- `runtime.live_human_expert_review` (runtime): requires live hoster.ai sandbox, model outputs and credentials
- `runtime.live_operational_measurement_collection` (runtime): requires live hoster.ai sandbox, model outputs and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.proposal_record.valid` (schema): sample proposal record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `eval_case_versioning.complete_eval_case.complete` (eval_case_versioning): eval case records corpus/code/config/model/tool-schema/dataset versions, scope and expected evidence with approved local grader and production data barrier
- `quality_metrics.all_categories_separated.complete` (quality_metrics): quality metrics cover exact/semantic recall, factual support, citation correctness and abstention/no-answer per category
- `citation_groundedness.citations_match_canonical_evidence.grounded` (citation_groundedness): citations checked against canonical evidence; unsupported/stale answers fail visibly; thresholds recorded; LLM judge not sole arbiter
- `deterministic_adversarial.merge_boundary_suite.safe` (deterministic_adversarial): adversarial/regression suite is deterministic and requires zero unauthorized disclosures
- `deterministic_adversarial.acl_isolation_suite.safe` (deterministic_adversarial): adversarial/regression suite is deterministic and requires zero unauthorized disclosures
- `deterministic_adversarial.prompt_injection_suite.safe` (deterministic_adversarial): adversarial/regression suite is deterministic and requires zero unauthorized disclosures

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t14/run_t14_tests.py
```

Real hoster.ai inference and owner-reviewed expert Russian golden set remain BLOCKED. This report contains only synthetic structural evidence; it does not claim production evaluation PASS.
