---
schema: 1
name: server_achievements_deferred_fixes.md
type: project
title: Отложенные исправления серверных достижений — поднять при любой новой задаче, затрагивающей AchievementUserComponent
source: .claude/memory/server_achievements_deferred_fixes.md
claude: |
  name: server-achievements-deferred-fixes
  description: Отложенные исправления серверных достижений — поднять при любой новой задаче, затрагивающей AchievementUserComponent
  metadata:
    type: project
---

Подозрительные места серверных достижений (`/workspace/server/.claude/docs/achievements-architecture.md#tradeoffs`)
и расхождения контракта с клиентом (`#client-contract`) пользователь решил 2026-09-28 НЕ чинить сейчас.

**Why:** отдельной задачи на исправление не было; чинить — вместе с ближайшей задачей по этой области.

**How to apply:** при любой новой задаче, которая затрагивает `AchievementUserComponent`, `AchievementsPage`,
`AchievementsDao` или `model/achievements/**`, в начале напомнить пользователю про эти списки и предложить включить
исправления в задачу. Заметные пункты: накрутка прогресса через непроверенный `tankId`/`airplaneId` в `CampaignPage`
(общий с [[server-assembly-deferred-fixes]]-подобной практикой и с документацией TankData), неработающая дедупликация
уведомлений, потеря прогресса танков при исчерпанном лимите серебра, отсутствие push после `/getReward`.
2026-10-14 при создании ГДД (`/workspace/client/.claude/docs/game-design/achievements-gdd.md`) два пункта
подтверждены как расхождения с ГДД и снова отложены: танки при исчерпанном лимите серебра не засчитываются
(#gdd-progress: засчитывается каждая единица); нет оповещения, когда накопленный прогресс сразу перекрыл
следующий порог после «Забрать награду» (#gdd-complete-popup). Клиентская пара — [[client-achievements-deferred-fixes]].
Перед исправлением сверить с актуальным кодом. См. [[server-achievementusercomponent]].
