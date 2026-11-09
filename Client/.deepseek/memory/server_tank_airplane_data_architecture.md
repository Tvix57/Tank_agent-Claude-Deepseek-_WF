---
schema: 1
name: server_tank_airplane_data_architecture.md
type: project
title: "Архитектура балансовых классов TankData и AirplaneData на сервере: структура данных, паттерны загрузки из Google-таблицы, взаимодействие с иерархией BagItem."
source: .claude/memory/server_tank_airplane_data_architecture.md
claude: |
  name: server-tank-airplane-data-architecture
  description: "Архитектура балансовых классов TankData и AirplaneData на сервере: структура данных, паттерны загрузки из Google-таблицы, взаимодействие с иерархией BagItem."
  metadata:
    node_type: memory
    type: reference
    category: Балансовые данные
    originSessionId: server-analyst-lead
    modified: 2026-09-28T03:37:38.895Z
---

# Документ: TankData / AirplaneData — балансовые данные танков и самолётов

**Путь:** `/workspace/server/.claude/docs/tank-airplane-data-architecture.md`

**Статус:** auto-create — составлено `server-analyst-lead` по существующему коду (код в рамках задачи не менялся), 2026-09-28. Доверие пониженное: всё подтверждено чтением кода, но фактическое содержимое удалённой Google-таблицы баланса не проверялось. Документ готов к использованию, при возникновении несоответствий между документом и фактическим поведением — сверяться с актуальным кодом.

## Содержание

Документ содержит 9 основных разделов:

1. **Назначение и бизнес-логика** (#purpose) — назначение как "справочник" модели танка/самолёта, откуда заполняются (Google-таблица → BalanceImporter → Balance.INSTANCE)
2. **Референсы** (#references) — перекрёстные ссылки на `collections-architecture.md` (иерархия BagItem), аналогичные балансовые классы (`CollectionsData`, `AchievementData` и т.п.)
3. **Паттерны** (#patterns) — static factory `build(JSONArray)`, контракт `KeyModel<Integer>`, immutable value object, flyweight/справочник, singleton-реестр
4. **Список классов** (#class-list) — `TankData` и `AirplaneData` (неизменённые), смежные классы
5. **Навигация по классам** (#class-nav) — навигационная таблица к разделам с документацией классов
6. **Классы** (раздел 6) — подробная документация:
   - `TankData` (#class-tankdata)
   - `AirplaneData` (#class-airplanedata)
7. **Общее и различия TankData / AirplaneData** (#diff) — сравнительный анализ
8. **Кто использует данные** (#consumers) — точки обращения к данным
9. **Принятые уязвимости и компромиссы** (#tradeoffs) — ограничения и компромиссы дизайна

## Смежная документация

- **Коллекции** — `/workspace/client/.claude/docs/collections-architecture.md` / `/workspace/server/.claude/docs/collections-architecture.md` (иерархия BagItem, CollectionItem как наследник, взаимодействие с коллекциями)
- Другие балансовые классы с тем же паттерном (`CollectionsData`, `AchievementData`) документируются в своих файлах
