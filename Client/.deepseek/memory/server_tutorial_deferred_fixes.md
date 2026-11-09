---
schema: 1
name: server_tutorial_deferred_fixes.md
type: project
title: "Отложенное по серверному туториалу после merge amnesia/fix (2026-10-19): два шага на /accept, хрупкий переход через ||; поднять при задаче по туториалу"
source: .claude/memory/server_tutorial_deferred_fixes.md
claude: |
  name: server-tutorial-deferred-fixes
  description: "Отложенное по серверному туториалу после merge amnesia/fix (2026-10-19): два шага на /accept, хрупкий переход через ||; поднять при задаче по туториалу"
  metadata:
    node_type: memory
    type: project
    originSessionId: 6a977e76-69ca-4dd9-b65e-b16b39363d89
    modified: 2026-10-19T16:06:54.788Z
---

Док: `/workspace/server/.claude/docs/tutorial-architecture.md#tradeoffs`. После merge `origin/amnesia/fix`
2026-10-19 `TutorialSteps` и туториальные ветки квестов, кампании, боя и поезда удалены; сценарий — `TutorialData`
`FIRST_TRAIN=0`, `SECOND_TRAIN=1`, `MAX=1`, шаги двигает только `TrainPage /accept`. Прежние находки (шаг 20,
победа без эмуляции, квест 11) ушли вместе с кодом. Открыто (решения не было):
- переход шагов опирается на короткое замыкание `increase(FIRST_TRAIN) || increase(SECOND_TRAIN)` в `/accept`;
- шаг двигает принятие любого танка, `/refuse` не двигает;
- имена `FIRST_TRAIN`/`SECOND_TRAIN` не отражают смысл (решение пользователя: переименование — отдельным этапом);
- `UserGameVersion` при `gv < 1` всегда вызывает `skip()` — миграция `skip_tutorial` избыточна;
- контракт «выключен»: отсутствие ключа `tutorial` vs `progress: -1`; сверка с клиентом поручена `integration-lead`.

Клиентская пара — [[client-tutorial-deferred-fixes]].

**Why:** документация обновлялась без задачи на исправление.
**How to apply:** при задаче по туториалу напомнить и начать с перехода через `||` (свернуть в один метод-переход у
владельца — [[feedback-no-implicit-call-order]]). Перед исправлением сверить с актуальным кодом.
