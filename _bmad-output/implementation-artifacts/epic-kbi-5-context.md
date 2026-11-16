# Epic KBI.5 Context: Diagram→Mermaid

## Goal

Определять diagram-кандидаты и, только после evidence gate, генерировать Mermaid через vision stub и проверять синтаксис Kroki. По умолчанию маршрут выключен: остаётся image + alt.

## Stories

- Story KBI.5.1: Diagram detection
- Story KBI.5.2: Mermaid generation
- Story KBI.5.3: Kroki validation gate
- Story KBI.5.4: Evidence gate and activation

## Requirements & Constraints

Route disabled until: vision provider configured, golden fixtures pass, human spot-check, license OK, Kroki available. Live vision LLM и live Kroki не заявляются (stubs; paid/egress требуют owner). Не Pillow. Не менять пять media_class. `diagram_candidate` — отдельный флаг. Invalid Mermaid → image preserved.

## Technical Decisions

Heuristics по имени: diagram/schematic/flowchart/architecture/uml/mermaid. StubVisionLLM + StubKrokiClient. `POST /mermaid/activate`, `GET /mermaid/status`. Convert/run читает `app.state.mermaid_route`.

## Implementation result (2026-11-17)

Synthetic VERIFIED: specs `spec-kbi-5-1`…`5-4` done; pytest 194 passed; ruff clean. Live vision/Kroki not claimed.
