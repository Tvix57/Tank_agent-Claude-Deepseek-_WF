---
schema: 1
name: server_achievements_architecture_draft.md
type: project
title: Назначение, архитектура и реализация серверной части Достижений
source: .claude/memory/server_achievements_architecture_draft.md
claude: |
  name: server-achievementusercomponent
  description: "Назначение, архитектура и реализация серверной части Достижений"
  metadata:
    node_type: memory
    type: reference
    status: auto-create
    date: 2026-09-28
    originSessionId: 6dd5d0e9-e340-48f7-a193-067cf524609e
    modified: 2026-09-28T04:22:28.281Z
---

# Server: Достижения (AchievementUserComponent)

**Статус: auto-create** — документ составлен аналитиками по результатам сканирования кода (2026-09-28). Доверять с осторожностью, перепроверять по актуальному коду при использовании.

## Краткое резюме

Серверная часть Достижений — компонент `AchievementUserComponent`, управляющий набором из **72 фиксированных достижений** на игрока (прогресс-счётчики уничтожений вражеской техники):

- 32 достижения танков (8 стран × 4 класса): `DestroyTankAchievement`
- 40 достижений самолётов (8 стран × 5 классов): `DestroyAirplaneAchievement`

Каждое достижение имеет ранги `NONE → I → … → X → MAX`, пороги и награды из баланса (`balance.json`, таблица `Achievements`).

Жизненный цикл:
1. Клиент сообщает об уничтожении техники в кампании → `trigger()` прибавляет прогресс
2. При достижении порога (`isDone`) сервер шлёт push `/events/achievements/update`
3. Игрок запрашивает `/ingame/achievements/getReward` → получает награду (GOLD_COIN), ранг повышается
4. Прогресс при смене ранга **не сбрасывается** (пороги накопительные)

## Основные классы

Пакет `game/src/main/java/com/linkedgames/game/model/achievements/`:

| Класс | Назначение |
|-------|-----------|
| `AchievementUserComponent` | Главный компонент, владеет всеми достижениями |
| `Achievement` (abstract) | Базовый жизненный цикл (прогресс/ранги/награда) |
| `DestroyTankAchievement` | Стратегия для танков |
| `DestroyAirplaneAchievement` | Стратегия для самолётов |
| `AchievementFactory` | Создаёт полный набор из 72 достижений |
| `AchievementData` | Строка баланса (пороги/награды) |
| `AchievementsPage` | WS-роуты `/ingame/achievements/*` |
| `AchievementsDao` | Коллекция Mongo `achievements` |

## Персистентность

Отдельная коллекция Mongo (`achievements`), один документ на **изменённое** достижение: `{ _id, ownerId, id, progress, currentRank, nextRank }`.

Неизменённые достижения в БД не хранятся (состояние берётся из фабрики).

## Важные моменты (подозрительные места)

- **Нет проверки**: прогресс начисляется по `tankId`/`airplaneId` от клиента без валидации (`if (true) // TODO`)
- **Самолётный роут не лимитирован**: серебро не проверяется, прогресс можно накручивать
- Неправильно сравниваются уведомления (`JSONObject` не переопределяет `equals`)
- Опасный cast в `trigger` наследников (полагается только на фильтр по `AchievementType`)
- Линейный поиск по 720 строкам баланса в `refreshMaxProgress`

## Ссылка на полный документ

`/workspace/server/.claude/docs/achievements-architecture.md`

Разделы: 1 (назначение), 2 (референсы), 3 (паттерны), 4–5 (список/навигация классов), 6 (классы подробно), 7 (начисление прогресса), 8 (push-события), 9 (персистентность), 10 (контракт с клиентом), 11 (компромиссы).
