---
name: client-bag-deferred-fixes
description: Отложенные исправления клиентской сумки (UserBag) — найдены при первичном анализе 2026-10-13, напомнить при задаче по сумке
metadata:
  type: project
---

Док: `/workspace/client/.claude/docs/bag-architecture.md#tradeoffs` (+ `#dup-can-afford`). Решение
пользователя 2026-10-13: оставить находками, чинить при задаче по области. Пункты:
- п.1–3 hold/releaseHold (перенесены из реестра багов недокументированных областей; висящий hold по
  ресурсу, ушедшему в del);
- п.4 при hold `getResourceCount` занижен, может уйти в минус, шапки не защищены;
- п.5 после logout старый UserBag подписан на push — ITEM_* дважды;
- п.6 HomeScreenAssembly не слушает ITEM_DELETE для танков (область «Сборка»);
- п.7 AerodromeBuySchemesPopup ищет RESOURCE_TANK_SCHEME вместо RESOURCE_AIRPLANE_SCHEME (область «Аэродром»);
- «хватает ресурса» (#gdd-gain-spend) — одно выражение в 4 местах.

Открытый вопрос ГДД «ресурс с нулём» пользователь оставил открытым; клиент по `del` удаляет ресурс
из кэша и показывает 0 (`#del-resource`). Серверная пара — [[server-bag-deferred-fixes]].

**How to apply:** при задаче по сумке, сборке (п.6) или аэродрому (п.7) напомнить и предложить починить.
