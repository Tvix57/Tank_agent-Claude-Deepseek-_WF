---
name: server-assembly-architecture
description: "Архитектура компонента сборки на сервере: AssemblyUserComponent, механика покупки и сборки танков из частей схемы, паттерны персистентности и балансовые таблицы."
metadata: 
  node_type: memory
  type: reference
  category: Сборка
  originSessionId: server-analyst-lead
  modified: 2026-09-28T00:00:00.000Z
---

# Документ: Сборка — механика сборки танков (AssemblyUserComponent)

**Путь:** `/workspace/server/.claude/docs/assembly-architecture.md`

**Статус:** auto-create — составлено `server-analyst-lead` по существующему коду (код в рамках задачи не менялся), 2026-09-28. Статус: auto-create — всё подтверждено чтением кода, содержимое удалённых балансовых таблиц (`Balance`: шансы поезда, списки танков) не проверялось. Документ готов к использованию, при возникновении несоответствий между документом и фактическим поведением — сверяться с актуальным кодом.

## Содержание

Документ содержит 10 основных разделов:

1. **Назначение и бизнес-логика** (#purpose) — игровой цикл сборки танка: покупка частей схемы за серебро, накопление до 30 частей, выдача/отклонение награды, генерация новой награды
2. **Референсы** (#references) — связи с TrainUserComponent, tank-airplane-data-architecture.md, балансовые таблицы поезда
3. **Паттерны** (#patterns) — UserChildComponent, персистентность "1a + 1b", статические балансовые таблицы, взвешенный случайный выбор, APIResponseStd
4. **Список классов** (#class-list) — основные классы области (AssemblyUserComponent, AssemblyNeedSchemePartsData, AssemblySchemeParts, AssemblySchemePartsType, AssemblyPage)
5. **Навигация по классам** (#class-nav) — указатели на методы основных классов
6. **Классы** (раздел 6) — подробная документация:
   - `AssemblyUserComponent` (#class-assemblyusercomponent) — поля, методы генерации, покупки, выдачи/отклонения, персистентности
   - `AssemblyNeedSchemePartsData` (#class-assemblyneedschemepartsdata) — захардкоженные таблицы цен и пачек
   - `AssemblySchemeParts` (#class-assemblyschemeparts) — описание пачки (тип, цвет, количество частей)
   - `AssemblySchemePartsType` (#class-assemblyschemepartstype) — enum цветов пачек
   - `AssemblyPage` (#class-assemblypage) — маршруты API (/buySchemeParts, /take, /reject, /compare)
7. **Жизненный цикл награды** (#lifecycle) — диаграмма состояний и переходов
8. **Персистентность** (#persistence) — хранение в документе User под ключом "Assembly"
9. **Связи с другими компонентами** (#relations) — Bag (ресурсы), Train (уровень), Hangar/Aerodrome (выдача), Codex (добавление записей), Balance/TankData
10. **Принятые уязвимости, компромиссы и подозрительные места** (#tradeoffs) — 12 известных особенностей и потенциальных проблем

## Смежная документация

- **Балансовые данные** — `/workspace/server/.claude/docs/tank-airplane-data-architecture.md` (иерархия TankData/AirplaneData, фильтр `dropType == TRAIN` для отбора кандидатов)
- **Поезд** — `/workspace/server/.claude/docs/train-architecture.md` (шансы звёзд, уровень для проверки доступности ранга)
- **Коллекции** — `/workspace/server/.claude/docs/collections-architecture.md` (прямых связей с сборкой нет)
