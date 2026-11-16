# Epic KBI.2 Context: Agent KB structuring

## Goal

Превратить пачку уже сконвертированных Markdown в предложение дерева KB. Агент только предлагает `parent_id` и `links`; человек правит; в GO уходит только одобренное. Canonical write здесь нет.

## Stories

- Story KBI.2.1: Batch read of converted Markdown
- Story KBI.2.2: Tree and link proposal generation
- Story KBI.2.3: Structure proposal review
- Story KBI.2.4: Submit proposals to GO

## Requirements & Constraints

Convert уже отдал Markdown, вложения и front-matter draft; `parent_id` и `links` пустые. Структуризация читает только `status=ready`. `status=blocked` исключается и сообщается, в дерево не входит.

Агент не пишет в Git. Human review обязателен до GO. Auto-merge для `structure` запрещён (ADR-018). Ключ `access` в шапке запрещён.

Batch read — поверхность агента: список `markdown_object_id` → документы с телом, attachments и front-matter draft, плюс отчёт excluded/missing.

## Technical Decisions

Конвертация должна сохранить Markdown как отдельный object-store объект (`markdown_object_id`) и реестр метаданных (status, FM, attachments). Batch-read не пересчитывает парсеры. Persistence для 2.1 — in-memory реестр + object store (как staging KBI.1); PostgreSQL queue — KBI.4.

GO client и StructureProposal persistence — стори 2.3–2.4, не 2.1. Синтетически закрыто: in-memory StructureProposal + StubGOClient; live GitLab/GO не заявлено.

## Cross-Story Dependencies

KBI.1 convert/run — источник документов. 2.2 читает только batch-read `documents[]`. 2.4 требует approved proposal и валидный FM.
