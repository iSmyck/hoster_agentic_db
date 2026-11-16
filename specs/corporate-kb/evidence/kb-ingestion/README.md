# kb-ingestion evidence (KBI-906)

Status: **VERIFIED(synthetic)** plus **live-local-stack** convert/source-sync auto-merge (2026-11-17). Production AD/MinIO ACL/TipTap/A01–A36 remain **BLOCKED**.

Machine-generated pytest JSON lives in `_bmad-output/test-artifacts/kb-ingestion/` and is not a live GO/GitLab/MinIO claim.

| Document | Result |
|---|---|
| `pytest.md` | Sanitized pytest/ruff summary for KBI.1–KBI.5 and KBI-901–906 |
| `_bmad-output/test-artifacts/kb-ingestion/pytest-summary.json` | Machine-readable command, pass count, ruff, live_gates |

## Live gates (not claimed)

- Live Identity HTTP, Git Orchestrator, GitLab, MinIO ACL, vision/Kroki, and hoster studio: **BLOCKED**
- Product PostgreSQL schema for ingestion: not created (ADR-015; durable jobs stay in GO `kb_ops`)
- Owner live DONE: not marked
