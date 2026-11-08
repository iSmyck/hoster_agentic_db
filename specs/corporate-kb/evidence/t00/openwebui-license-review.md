# T00 Evidence — Open WebUI license review (engineering evidence, sanitized)

**Дата:** 2026-11-07
**Статус:** engineering evidence для T00/G0. **Это НЕ юридическое заключение (not legal advice) и НЕ legal clearance.** Юридический статус по ADR-007 остаётся UNKNOWN/BLOCKED до формального legal/owner review (`specs/corporate-kb/adr/ADR-007-client-packaging-license.md:58,62`).
**Scope:** read-only анализ upstream checkout `_bmad-output/test-artifacts/t00/upstream/open-webui` (версия `0.13.0`, HEAD commit `c38885a1a737da4968f157092f304f3b5481d0bf`, дата коммита 2026-11-03). Файлы upstream и ADR не изменялись.

## 1. License modes (мульти-лицензионная модель)

Upstream использует три лицензионных режима по датам/коммитам вклада (`LICENSE_NOTICE:5-9`):

| Режим | Лицензия | Граница (коммиты) | Источник |
|---|---|---|---|
| 1 | MIT License (Timothy Jaeryang Baek, 2023) | до `a76068d69cd59568b920dfab85dc573dbbb8f131` | `LICENSE_HISTORY:31-53` |
| 2 | BSD 3-Clause (Timothy Jaeryang Baek, 2023–2025) | от `a76068d…` до `60d84a3aae9802339705826e9095e272e3c83623` включительно | `LICENSE_HISTORY:1-29` |
| 3 | «Open WebUI License» = BSD 3-Clause + branding-ограничение (п.4) | после `60d84a3…` | `LICENSE:1-51`, `LICENSE_NOTICE:9` |

Режим 3 является source-available, но НЕ OSI-approved open source: пункт 4 добавляет материальное условие на branding (`LICENSE:20-34`).

## 2. Текущий режим v0.13.0

- Текущий checkout: `package.json:2-3` (`name: open-webui`, `version: 0.13.0`, `private: true`); `pyproject.toml:2-7` (authors — Timothy Jaeryang Baek, `license = { file = "LICENSE" }`).
- HEAD `c38885a1a…` (2026-11-03) хронологически позже граничного коммита `60d84a3…` (смена лицензии ~2025), т.е. действует режим 3 с branding-ограничением. Точная принадлежность per-file к режимам 1–3 не подтверждена (git-инспекция истории в данном evidence не выполнялась); карта режимов задана только на уровне коммитов (`LICENSE_NOTICE:5-9`).
- Вывод для T00: baseline v0.13.0 подпадает под «Open WebUI License» с обязательством сохранения branding/notices.

## 3. Branding / notice obligations

**Notice-обязательства (BSD-клаузулы 1–3, `LICENSE:9-18`):**
- сохранять copyright notice (`LICENSE:3`, «Copyright (c) 2023- Open WebUI Inc.») и disclaimer в исходниках и бинарных дистрибутивах;
- запрет использования имён copyright holder/контрибьюторов для endorsement без письменного разрешения (`LICENSE:16-18`).

**Branding-ограничение (`LICENSE:20-34`):**
- запрещено «altering, removing, obscuring, or replacing» любого «Open WebUI» branding — имя, логотип, визуальные/текстовые/символьные идентификаторы — в любом deployment или distribution, кроме трёх исключений (см. раздел 4);
- нарушение = material breach лицензии (`LICENSE:33-34`).

**Branding surface в коде (upstream сам маркирует его как лицензионно-защищённый):**
- `backend/open_webui/env.py:959-965` — `WEBUI_NAME`; комментарий LICENSE:959-962; при задании env `WEBUI_NAME` upstream принудительно дописывает суффикс ` (Open WebUI)` (env.py:964-965);
- `backend/open_webui/env.py:967-971` — favicon как защищённый идентификатор (`WEBUI_FAVICON_URL`);
- `backend/open_webui/main.py:2374, 2982-2984, 3021-3022` — имя уходит в API config, PWA manifest и OpenSearch descriptor.

**README attribution:** `README.md:126-128` («requires preserving the Open WebUI branding», ссылки на LICENSE и LICENSE_HISTORY); Enterprise-контакт `README.md:130`. Контрибуции регулируются CLA (`LICENSE:39-40`).

## 4. Internal ≤50 rolling users vs managed/client deployment

Исключения из branding-запрета (`LICENSE:26-31`):
- (i) deployments/distributions, где число end users (физические лица с прямым доступом к приложению) **≤ 50 в rolling 30-дневном окне**;
- (ii) письменное разрешение copyright holder;
- (iii) enterprise license, явно разрешающая модификацию.

Инженерная интерпретация (не юридическая):
- **Internal ≤50 users:** изменение/удаление branding формально допустимо по исключению (i), но порог считается по rolling 30 дням; рост аудитории или суммирование нескольких deployment может вывести за пределы. BSD-нотификации (copyright/disclaimer) обязательны в любом случае.
- **Managed/client deployment (hoster.ai и внешние клиенты):** без письменного разрешения или enterprise license branding сохраняется полностью — имя, логотип, favicon, суффикс «(Open WebUI)». ADR-007 фиксирует это как design constraint: сохранение branding/notices выбранного baseline (ADR-007:20), запрет автоматического rebrand без license review (ADR-007:20,32), license/SBOM review до commercial distribution (ADR-007:21,61-62). Статус ADR — Proposed до юридической проверки (ADR-007:4).
- Не определено лицензией и требует решения владельца: считается ли порог per deployment или агрегированно по всем клиентским контурам hoster.ai; кто считается «end user» при SSO-группах и сервисных аккаунтах.

## 5. SBOM / fork риски

- **Минимальный fork + seam registry** (ADR-007:18) совместим с лицензией (модификация кода разрешена), но любой seam, затрагивающий branding surface (название в UI/метаданных, favicon, manifest, суффикс в env.py:964-965), для >50 users становится material breach (`LICENSE:33-34`).
- Формулировка «obscuring» (`LICENSE:22`) покрывает и косвенное сокрытие branding (например, переопределение имени через config так, чтобы вытеснить upstream-идентификаторы в managed-режиме).
- **Mixed-license repo:** перенос кода между файлами может смешивать режимы MIT/BSD/Open WebUI License; upstream не предоставляет per-file карту лицензий — это усложняет SBOM и license inventory (требования ADR-007:21,61).
- **Upgrade-риск:** новые upstream-релизы могут расширять branding surface (пример — маркировка в env.py:959-971); каждый upgrade требует повторного branding/notices diff и license/SBOM delta (ADR-007:23).
- Package metadata не содержит SPDX-идентификатора (`pyproject.toml:7` — ссылка на файл; `package.json` — поле license отсутствует, `private: true` в `package.json:4`); SBOM-инструменты не смогут автоматически классифицировать лицензию.

## 6. Точные ссылки file:line (upstream: `_bmad-output/test-artifacts/t00/upstream/open-webui/`)

- `LICENSE:3` — copyright 2023- Open WebUI Inc.
- `LICENSE:9-18` — BSD-нотификации 1–3
- `LICENSE:20-34` — branding-ограничение и три исключения (≤50 users / письменное разрешение / enterprise license)
- `LICENSE:33-34` — material breach
- `LICENSE:36-37` — prior licenses по LICENSE_HISTORY
- `LICENSE:39-40` — CLA
- `LICENSE_HISTORY:1-29` — BSD 3-Clause (до `60d84a3…`)
- `LICENSE_HISTORY:31-53` — MIT (до `a76068d…`)
- `LICENSE_NOTICE:5-9` — карта трёх режимов
- `README.md:126-128` — license/branding notice; `README.md:130` — Enterprise-контакт
- `package.json:2-4` — name/version/private; `pyproject.toml:2-7` — name/authors/license file
- `backend/open_webui/env.py:959-965` — WEBUI_NAME + принудительный суффикс; `env.py:967-971` — favicon
- `backend/open_webui/main.py:2374, 2982-2984, 3021-3022` — branding в API/manifest/OpenSearch
- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:4` (статус Proposed), `:12` (лицензия «не обычная MIT»), `:18` (seam registry), `:20` (сохранение branding/notices), `:21` (license/SBOM review), `:32` (запрет rebrand без legal review), `:58` (UNKNOWN/BLOCKED до проверки), `:62` (legal/owner review перед commercial distribution)

## 7. Вопросы юристу / владельцу для G0

1. Приемлема ли «Open WebUI License» (BSD + п.4) для internal deployment ≤50 users; как документировать rolling-30-day подсчёт end users?
2. Как считать «end users» при нескольких изолированных client deployments hoster.ai: per deployment или агрегированно по договору?
3. Достаточно ли исключения (i) для internal-режима при изменении WEBUI_NAME/favicon, или владелец требует сохранять суффикс «(Open WebUI)» как политику продукта независимо от лицензионного минимума?
4. Нужна ли enterprise license / письменное разрешение Open WebUI Inc. для managed/client поставки (white-label); кто инициирует контакт через `docs.openwebui.com/enterprise`?
5. Считается ли передача fork-пакета клиенту «distribution» в терминах п.4 (даже без rebrand)?
6. Как в SBOM/license inventory отражать три исторических режима без per-file карты от upstream?
7. Покрывает ли CLA (`LICENSE:39-40`) внутренние патчи; нужно ли подписывать его при upstream-контрибуциях?
8. Кто (owner/legal) утверждает финальный license/SBOM review до commercial distribution (ADR-007:21,62) и в какой срок до G0?
9. Распространяются ли notice-обязательства на многоязычные README и клиентские маркетинговые материалы?
10. Лицензии моделей, extraction/OCR assets и plugins (ADR-007:12,21) — часть того же review или отдельный трек?

## 8. Ограничения данного evidence

- Read-only анализ одного checkout v0.13.0; per-file принадлежность к режимам 1–3 не верифицирована по git-истории.
- Санитизировано: реальные клиентские данные, секреты и endpoint'ы отсутствуют.
- Выводы — engineering evidence для T00/G0, не legal clearance; формальное заключение остаётся за юристом/владельцем (ADR-007:58,62).
