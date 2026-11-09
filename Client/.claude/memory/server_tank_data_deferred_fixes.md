---
name: server-tank-data-deferred-fixes
description: Отложенный возможный баг TankData — armorLossDurability читает ordinal снаряда (колонка 16) вместо процента (колонка 14)
metadata:
  type: project
---

Найдено 2026-10-13 при составлении карты файлов: в balance.json (таблица Tanks) колонка 16 — ordinal снаряда без `%`, процент лежит в колонке 14, которую TankData.build не читает → `armorLossDurability` получает ordinal. Похоже на смещение индекса, не подтверждено. Записано риском в /workspace/server/.claude/docs/tank-airplane-data-architecture.md (компромисс 9.1).

**Why:** код не меняли — задача была только документационная.
**How to apply:** при задаче по балансу танков/бою/прочности брони напомнить и предложить проверить через пайплайн. См. [[server-tank-airplane-data-architecture]].
