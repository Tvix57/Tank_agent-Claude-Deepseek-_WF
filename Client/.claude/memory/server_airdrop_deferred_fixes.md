---
name: server-airdrop-deferred-fixes
description: Отложенные исправления серверного airDrop — поднять при любой новой задаче, затрагивающей airDrop
metadata:
  type: project
---

Подозрительные места серверного airDrop (`/workspace/server/.claude/docs/airdrop-architecture.md#tradeoffs`)
пользователь решил 2026-09-28 НЕ чинить сейчас.

**Why:** отдельной задачи на исправление не было; чинить — вместе с ближайшей задачей по этой области.

**How to apply:** при любой новой задаче, которая затрагивает `AirDropData`/`AirDropBox`/`AirDropBoxType` или
airDrop-часть `CampaignUserComponent`/`CampaignPage`/`DevToolsPage`, в начале напомнить пользователю про список и
предложить включить исправления в задачу. Заметные пункты: кулдаун `airDropTime` не персистентен,
`getAirDropBox` бросает IndexOutOfBounds при `dropCount >= 4`, суточный лимит по часовому поясу JVM, `YELLOW`
сериализуется как "orange", баланс захардкожен; ящик, выпавший до полуночи и собранный после, теряется из суточного счёта, а по ГДД
(`/workspace/client/.claude/docs/game-design/airdrop-gdd.md`, решение 2026-10-14) он должен идти в новые сутки. Стык с клиентом (там же): `/sendAirDrop` не проверяет туториал,
заложенные 5,5 с анимации не совпадают с клиентскими 7 с, минутная проверка рассинхронизирована с клиентской. Перед исправлением сверить с актуальным кодом.
Клиентская пара — [[client-airdrop-deferred-fixes]]. Аналогично: [[server-assembly-deferred-fixes]], [[server-achievements-deferred-fixes]]. См. [[server-airdrop-component]].
