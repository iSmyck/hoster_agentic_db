# kb-ingestion live stack

Generated: 2026-11-16T22:29:46.212915+00:00
Claim: **VERIFIED(live-local-stack)**

| ID | Status | Expected | Actual |
|---|---|---|---|
| ingest.health | PASS | kb-ingestion /health 200 | status=200 |
| ingest.convert_upload | PASS | convert upload 201 | status=201 body={"object_id":"c07b42137e9645aea2c10ba206b45ca7","sha256":"7d9feda454ae2934e6adda9abb75bb2eff60fde4272b2af084337a6286380005","version_id":"v1","size":166,"media_type":"text/markdown"} |
| ingest.convert_run | PASS | convert/run ready | status=200 body={"path_map":{"docs/kbi-live-df2dfc905d.md":"c07b42137e9645aea2c10ba206b45ca7"},"markdown_object_id":"27ee120a755b4dc986dfdeeb5fd8281c","markdown":"---\nschema_version: document-front-matter-v2\ntitle: KBI live ingest\nowner: author-1\nstatus: draft\n---\n\n# KBI live ingest\n\nSynthetic page docs/kbi-live-df2dfc905d.md.","attachments":[],"blockers":[],"losses":[],"errors":[],"front_matter_draft":{ |
| ingest.source_register | PASS | register trusted auto_merge source | status=201 body={"source_id":"7a3fb4a42e5e456783ebc5fdf561f386","source_type":"n8n","source_ref":"live-stack://synthetic","credentials_ref":"ref:live-stack","poll_interval":3600,"space_id":"corp-kb/sales","data_profile":"strict","validation_required":false,"auto_merge":true,"trusted":true,"legal_basis":null,"max_files_per_sync":50,"max_lines_changed":2000} |
| ingest.source_sync_auto_merge | PASS | source-sync auto-merge against live GO/GitLab | status=200 body={"sync_run_id":"d18feeef076b477c8b69b37af99f5da6","source_id":"7a3fb4a42e5e456783ebc5fdf561f386","changes":[{"source_object_id":"live-1","path":"docs/kbi-live-df2dfc905d.md","kind":"created","source_version":"v1","sha256":"7d9feda454ae2934e6adda9abb75bb2eff60fde4272b2af084337a6286380005"}],"outcomes":[{"source_object_id":"live-1","path":"docs/kbi-live-df2dfc905d.md","disposition":"merged","code":null,"go_proposal_id":"c99d49de-cf6e-4d5e-ba55-893ba3a893e5","actor_type":"source_syn |
