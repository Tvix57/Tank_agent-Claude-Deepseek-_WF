---
schema: 1
name: server_military_base_deferred_fixes.md
type: project
title: Отложенные исправления серверной военной базы (дыра /summonAccept, /skipBuilding, мёртвый алиас роута, null-риски, t=3) — напомнить при задаче по военной базе, авиазаводу, штабу
source: .claude/memory/server_military_base_deferred_fixes.md
claude: |
  name: server-military-base-deferred-fixes
  description: "Отложенные исправления серверной военной базы (дыра /summonAccept, /skipBuilding, мёртвый алиас роута, null-риски, t=3) — напомнить при задаче по военной базе, авиазаводу, штабу"
  metadata:
    node_type: memory
    type: project
    originSessionId: fd6d858f-99c1-43c3-90d3-ec53e1b9dfc6
    modified: 2026-10-22T06:13:41.319Z
---

Док: `/workspace/server/.claude/docs/military-base-architecture.md#tradeoffs` (номера пунктов ниже — оттуда).
ГДД: `game-design/military-base-gdd.md`; расхождения ГДД↔код (#tradeoffs п.2–8, 12, 14, 16) сюда не
дублируются. Пути — от `/workspace/server/game/src/main/java/com/linkedgames/game/`.

Пользователь 2026-10-22 решил: все баги и расхождения ГДД↔код военной базы отложить, сейчас не чинить.

**Why:** задача была на первичную документацию и сверку контракта, без исправлений.

**How to apply:** при любой задаче, затрагивающей `MilitaryBaseUserComponent`, `model.military_base`,
`model.bag.military_base` или `MilitaryBasePage`, напомнить пользователю и предложить включить пункты.
Перед исправлением сверить с актуальным кодом.

- **Высокий приоритет: `/summonAccept` даёт бустер бесплатно** (п.1, `pages/ws/ingame/MilitaryBasePage.java:809-830`).
  Роут не проверяет `hasSummonedBoost()`, а `summonBoost()` при пустом штабе генерирует новый бустер;
  каждый повторный accept даёт новый. Подтверждено integration-lead.
- **`/skipBuilding` без проверки стройки** (п.17, `MilitaryBasePage.java:150-182`): 100 золота
  списываются и у уже построенного здания.
- **Мёртвый алиас** `/ingame/military_base` (`pages/WSRouter.java:83-84`): клиент шлёт только `/ingame/militaryBase`.
- **null-риски** (п.9): строка `MBAviationFactory` по уровню завода (`MilitaryBaseAviationFactory.getProductionCost`/
  `getProductionTime`) и `Balance.getAirplanes(rank)` в `generateAirplane` берутся без проверки.
  Сейчас данные согласованы (20 уровней, самолёты есть у всех рангов).
- **t=3** (п.18): в коде числа `ItemType` совпадают с клиентом, конфликт возможен только в данных БД.
  Проверка — документы сумки с `t=3` без полей `bt`/`pl`. Общий пункт с [[server-collections-deferred-fixes]].

Клиентские находки — [[military-base-deferred-fixes]].
