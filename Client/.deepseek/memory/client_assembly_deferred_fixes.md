---
schema: 1
name: client_assembly_deferred_fixes.md
type: project
title: Отложенные исправления клиентской сборки (AssemblyPopup, HomeScreenAssembly) — найдены при первичной документации 2026-10-14, напомнить при задаче по сборке
source: .claude/memory/client_assembly_deferred_fixes.md
claude: |
  name: client-assembly-deferred-fixes
  description: "Отложенные исправления клиентской сборки (AssemblyPopup, HomeScreenAssembly) — найдены при первичной документации 2026-10-14, напомнить при задаче по сборке"
  metadata:
    node_type: memory
    type: project
    originSessionId: 2c59b490-c034-488f-8e86-6a2aa77b2a46
    modified: 2026-10-14T04:09:38.895Z
---

Док: `/workspace/client/.claude/docs/assembly-architecture.md` (п.8, 11 проблем). Решение пользователя
2026-10-14: записать находками, чинить при задаче по области. Главное:
- п.1 (приоритет) — ошибка `/take`/`/reject`/`/compare`: сервер отвечает `.error()` без кода,
  `WSSocket.sendRequest` резолвит как успех, `AssemblyPopup` не проверяет `ResultUtils.isOk` →
  падение окна и `ASSEMBLY_UPDATE(undefined)` на плашке. Стык client↔server — через `integration-lead`;
- доступ (`AssemblyAccessHangarSize = 12`) проверяет только клиент, при удалении танка не
  пересчитывается (`bag-architecture.md#assembly-tank-delete`);
- окно падает без `reward` и на награде-самолёте (каст к `TankJSON`);
- мелочи: ошибки глушатся, дубль правила «хватает серебра/частей», спрайт `aerodrome.png` на замке,
  нет ключей в `en.json`, неиспользуемые ключи/`onExit`/`textArgs`.

ГДД сборки создан 2026-10-15 (`game-design/assembly-gdd.md`). Расхождения с ним, отложенные решением пользователя
2026-10-15 (пометка «ГДД, отложено 2026-10-15» в доке): под чертежами нет подписей очков (#gdd-window); доступ
и ошибки — см. выше. «ПРОДАЖА» без компенсации соответствует ГДД (#gdd-take) и из проблем убрана. Анимация
покупки ГДД приведена к коду, расхождения нет.

Серверная пара — [[server-assembly-deferred-fixes]].

**How to apply:** при задаче по сборке напомнить и предложить починить, начиная с п.1.
