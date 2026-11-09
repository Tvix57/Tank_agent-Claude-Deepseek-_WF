---
schema: 1
name: server_assembly_deferred_fixes.md
type: project
title: Отложенные исправления AssemblyUserComponent — поднять при любой новой задаче, затрагивающей сборку на сервере
source: .claude/memory/server_assembly_deferred_fixes.md
claude: |
  name: server-assembly-deferred-fixes
  description: "Отложенные исправления AssemblyUserComponent — поднять при любой новой задаче, затрагивающей сборку на сервере"
  metadata:
    node_type: memory
    type: project
    originSessionId: 6dd5d0e9-e340-48f7-a193-067cf524609e
    modified: 2026-09-28T04:15:19.418Z
---

10 подозрительных мест в `AssemblyUserComponent`/`AssemblyPage` (перечислены в
`/workspace/server/.claude/docs/assembly-architecture.md#tradeoffs`) пользователь решил 2026-09-28 НЕ чинить сейчас.

**Why:** отдельной задачи на исправление не было; чинить — вместе с ближайшей задачей по этой области.

**How to apply:** при любой новой задаче, которая затрагивает `AssemblyUserComponent` (или `AssemblyPage`,
`model/assembly/**`), в начале напомнить пользователю про этот список и предложить включить исправления в
задачу. Приоритет: п.2 (после take/reject при пустом списке кандидатов `reward` не меняется — повторная выдача
танка; фильтр `dropType == TRAIN` от 2026-09-28 делает это чаще) и п.1 (генерация при загрузке до сумки/кодекса).
2026-10-15 при создании ГДД (`/workspace/client/.claude/docs/game-design/assembly-gdd.md`) п.1, п.2, п.3 (тип
LIGHT, когда все танки X ранга), п.8 (бесплатный чертёж при цене 0) и п.11 (ошибки без кода) подтверждены как
расхождения с ГДД и снова отложены. Новое расхождение: `buySchemeParts` не запрещает покупку при 30+ очках
(#gdd-build-points, server п.13); нет 10 серебра за заменённый танк, уходящий из команды при `/take` (#gdd-take, как в
поезде, server п.14). Кодекс при предложении танка (п.6) ГДД принял как правило — это не баг.
Клиентская пара — [[client-assembly-deferred-fixes]]. Перед исправлением сверить пункты с актуальным кодом. См. [[server-assembly-architecture]].

После merge amnesia/fix (2026-10-19): `Rank.TANKS` расширен до XX, а `TANK_PARTS` (цена частей схем) заведена только для I..X — ранги XI..XX берут цену X.
