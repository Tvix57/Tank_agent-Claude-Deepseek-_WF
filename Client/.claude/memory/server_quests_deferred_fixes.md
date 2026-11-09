---
name: server-quests-deferred-fixes
description: Отложенные исправления серверных квестов (в т.ч. повторная выдача награды) — поднять при любой новой задаче по квестам
metadata:
  type: project
---

Подозрительные места серверных квестов (`/workspace/server/.claude/docs/quests-architecture.md#tradeoffs`)
пользователь решил 2026-09-28 НЕ чинить сейчас — включая подтверждённую по коду уязвимость п.1.

**Why:** отдельной задачи на исправление не было; чинить — вместе с ближайшей задачей по этой области.

**How to apply:** при любой новой задаче, которая затрагивает `QuestsUserComponent`, `QuestEvent`, `QuestData`,
`UserResetQuests` или квестовые роуты `HomePage`/`DevToolsPage`, в начале напомнить пользователю и предложить
включить исправления. Приоритет — п.1: после конца цепочки `questId/progress/requiredProgress = 0`, но `reward`
не обнуляется, и `completeQuest` (проверяет только `progress < requiredProgress`) выдаёт награду повторно на
каждый вызов до сброса.
2026-10-15 создан ГДД (`/workspace/client/.claude/docs/game-design/quests-gdd.md`); при сверке пользователь снова отложил
все расхождения, ГДД под код не правился: п.1 повторная награда (#gdd-refresh, #gdd-reward); первое задание после
туториала (шаг 19) выдаётся как туториальное — 1 схема танка без 50/50, без таймера и замены, а первая обычная серия
даёт 2 вместо 3 (п.6, #gdd-tutorial, #gdd-reward; связано с [[server-tutorial-deferred-fixes]]); нет фильтра
невыполнимых — «Пройди N уровень» после последнего уровня (п.8 `canBeCompleted`, #gdd-unavailable); нет проверки,
что уничтоженная техника была в бою (п.5, чинить вместе с [[server-achievements-deferred-fixes]]). Клиентские
находки (прогресс 0/1 у задания кампании) — в `undocumented-areas-known-bugs.md`.
Перед исправлением сверить с актуальным кодом.
Аналогично: [[server-assembly-deferred-fixes]], [[server-achievements-deferred-fixes]], [[server-airdrop-deferred-fixes]].
