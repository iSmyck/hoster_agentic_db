# Epic KBI cross-cutting

## Goal

Связать kb-ingestion с shared object-store, Identity/GO клиентами, local stack и evidence. Product PostgreSQL schema не создаём (ADR-015). ADR-018 уже accepted.

## Tasks

- KBI-901 Shared object-store — done (synthetic)
- KBI-902 Scaffold (migrations deferred) — done (synthetic)
- KBI-903 Identity + GO clients — done (synthetic)
- KBI-904 ADR-018 (already on disk) — done
- KBI-905 Local stack + smoke health — done (registry only; live BLOCKED)
- KBI-906 Sanitized evidence — done (synthetic)

## Residual

Live Identity/GO/GitLab/MinIO ACL, vision/Kroki, and `local_stack` process start are BLOCKED. Durable jobs remain in-memory until GO `kb_ops` work is authorized.
