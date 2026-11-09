---
name: train-deferred-fixes
description: "Отложенные исправления поезда (client + server) — расхождения с train-gdd, найдены при первичной документации 2026-10-14, напомнить при задаче по поезду"
metadata:
  node_type: memory
  type: project
  originSessionId: 2c59b490-c034-488f-8e86-6a2aa77b2a46
  modified: 2026-10-23T05:52:52.546Z
---

Доки: client `/workspace/client/.claude/docs/train-architecture.md#tradeoffs`, server
`/workspace/server/.claude/docs/train-architecture.md#tradeoffs`; ГДД `train-gdd.md`.
Решения пользователя 2026-10-14 — баги, правка через пайплайн:
- client п.8 п.1 — автопризыв продаёт неподходящий танк и при свободной позиции (нарушает
  `#gdd-decision`/`#gdd-auto-summon`); при правке — взять или показать окно, иначе цикл на том же
  непринятом танке; серверный п.11 — `/refuse` не проверяет свободную позицию;
- client п.8 п.2 — на предмете коллекции автопризыв встаёт, режим остаётся включённым; по ГДД призыв
  продолжается (уточнено 2026-10-23: новый предмет — окно, призыв после закрытия; дубликат — без
  окна, призыв дальше);
- client: `/accept`/`/refuse` без `isOk` (падение пересборки), двойной `onEnd` анимации, «КУПИТЬ
  ЗОЛОТО» без обработчика;
- server: предмет коллекции без опыта игрока и в туториале (`#gdd-open`), `/buySchemes` без `id`
  падает, `getMaxTrainLevel` в аэродроме, переходы в `TrainPage`, дубли броска звёзд со сборкой.

**How to apply:** при задаче по поезду (или автопризыву, сборке, аэродрому) напомнить и предложить
починить, начиная с двух расхождений с ГДД. Стык client↔server по `/refuse` — через `integration-lead`.

## После merge amnesia/fix (2026-10-19)
- server: `TrainUserComponent.dbMappingBuild`, поле `rci` — нет проверки на `null` после `ItemFactory.newFromDocument` (для `receivedTank` есть) → NPE при неизвестном `t`.
