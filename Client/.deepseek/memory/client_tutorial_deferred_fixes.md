---
schema: 1
name: client_tutorial_deferred_fixes.md
type: project
title: "Отложенное по клиентскому туториалу после merge amnesia/fix (2026-10-19): туториал сведён к двум шагам 0/1; напомнить при задаче по туториалу"
source: .claude/memory/client_tutorial_deferred_fixes.md
claude: |
  name: client-tutorial-deferred-fixes
  description: "Отложенное по клиентскому туториалу после merge amnesia/fix (2026-10-19): туториал сведён к двум шагам 0/1; напомнить при задаче по туториалу"
  metadata:
    node_type: memory
    type: project
    originSessionId: 6a977e76-69ca-4dd9-b65e-b16b39363d89
    modified: 2026-10-19T16:06:46.864Z
---

Док: `/workspace/client/.claude/docs/tutorial-architecture.md#tradeoffs` (статус «остатки»). После merge
`origin/amnesia/fix` 2026-10-19 туториал — шаги `0`/`1` (`TutorialUtils.FIRST_TRAIN`/`SECOND_TRAIN`), `-1` — выключен;
прежние находки про шаги 0..20, `STEP_20`, `aromorType`, подмену танков и паузу боёв удалены вместе с кодом.
Открыто (решения не было):
- контракт с сервером не сверен — поручено `integration-lead` 2026-10-19;
- имена `FIRST_TRAIN`/`SECOND_TRAIN` не отражают смысл шагов; ветка 0/1 в `AirplaneGetPopup` — копия из
  `TankGetPopup` (решение пользователя: наблюдение, переименование — отдельным этапом);
- «туториал включён» — сравнения `progress === -1` в пяти файлах; `HomeScreen` не подписан на
  `onTutorialChange` и вызывает `processTutorial` вручную — [[feedback-no-implicit-call-order]];
- слой туториала (z 999) над окнами: окно, открытое поверх указателя (например `TrainCollectionItemPopup`
  на шаге 0), может оказаться некликабельным;

Серверная пара — [[server-tutorial-deferred-fixes]].

**Why:** документация обновлялась без задачи на исправление.
**How to apply:** при задаче по туториалу напомнить; начать с результата сверки `integration-lead` и блокировки
окон слоем туториала. Перед исправлением сверить с актуальным кодом.
