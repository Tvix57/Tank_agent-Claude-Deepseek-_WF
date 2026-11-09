---
name: server-codex-architecture-docs
description: "Server — документация компонента \"Кодекс\" (CodexUserComponent)"
metadata:
  node_type: memory
  type: reference
  originSessionId: 2897f0c4-93d9-401e-88da-b2089f805a8f
  modified: 2026-10-13T13:24:50.135Z
---

**Путь:** `/workspace/server/.claude/docs/codex-architecture.md`

**Статус:** auto-create (составлено `server-analyst-lead` по существующему коду 2026-10-13; всё подтверждено чтением кода, запуском не проверялось).

**Реестр:** зарегистрирован в `/workspace/server/.claude/docs/component-docs-registry.md` строка 29.

**Содержимое:** 9 пунктов по стандарту (назначение, референсы, паттерны, класс-лист, навигация, оглавление по классам, классы и методы, трейдоффы и известные проблемы, связь с ГДД).

**Якоря:**
- `#bug-duplicates` — дубли записей из-за `map.remove(id)` в `onClean` (баг в master с d3d31c4, найден 2026-10-05, попадёт в `CodexPage.collected`). Связь с [[server-codex-deferred-fixes]].
- `#tradeoffs` — 8 компромиссов и уязвимостей (п. 1 — основной баг дубликатов, п. 2-8 — проблемы с дизайном и загрузкой).

**Примечание:** ГДД для кодекса отсутствует. 2026-10-13 пользователь решил пока не создавать — запросить файл/описание при следующей задаче по кодексу.

Аналитик области — `server-analyst-codex` (создан 2026-10-13). ГДД кодекса пока нет: что в него внести — раздел 9 дока. Баг дублей — `#bug-duplicates`, см. [[server-codex-deferred-fixes]].
