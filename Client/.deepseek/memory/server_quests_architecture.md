---
schema: 1
name: server_quests_architecture.md
type: project
title: Назначение, архитектура и реализация серверного компонента Квесты (QuestsUserComponent)
source: .claude/memory/server_quests_architecture.md
claude: |
  name: server-quests-component
  description: "Назначение, архитектура и реализация серверного компонента Квесты (QuestsUserComponent)"
  metadata:
    node_type: memory
    type: reference
    status: auto-create
    date: 2026-09-28
    originSessionId: 6dd5d0e9-e340-48f7-a193-067cf524609e
    modified: 2026-09-28T05:50:40.380Z
---

# Server: Квесты (QuestsUserComponent)

**Статус: auto-create** — документ составлен server-analyst-lead по существующему коду (2026-09-28), каждое утверждение сверено с кодом; прежняя версия документа от библиотекаря заменена целиком. Перепроверять по актуальному коду при использовании.

## Краткое резюме

У игрока один активный квест "сделай N действий типа X" (10 обычных + 5 туториальных в `QuestData.LIST`).
Прогресс начисляет сервер из игровых роутов через `triggerEvent(QuestEvent, value)`; клиент только
читает состояние и забирает награду (`/ingame/home/completeQuest`). Награда — схемы танка/самолёта
(`RESOURCE_TANK_SCHEME`/`RESOURCE_AIRPLANE_SCHEME`), тип и количество фиксируются при выдаче квеста
(3/2/1 по числу цепочек за сутки, 50 за последний квест туториала). Окно 3 ч (ленивый сброс в
`apiResponse()`), 6 квестов за окно, `completedChain` обнуляется в новые сутки. `isEndless` (туториал)
= квест не заменяется при сбросе окна.

## Основные классы

| Класс | Назначение |
|-------|-----------|
| `model/quests/QuestsUserComponent` | Состояние, выдача, прогресс, награда, сброс, push `/events/quest/update` |
| `model/quests/QuestEvent` | 10 типов событий; `CAMPAIGN_LEVEL_UP` — SET, остальные — ADD |
| `model/quests/data/QuestData` | Справочник квестов (событие, диапазон цели, isTutorial) |
| `scripts/UserResetQuests` | Миграция `1758700043392_reset_quests.json`: обнуляет `rt`/`coq`/`coc` |

## Роуты (WS)

| Маршрут | Назначение |
|---------|-----------|
| `/ingame/home` (index), `/ingame/home/getQuest` | Состояние квеста (`payload.quest`, с ленивым сбросом) |
| `/ingame/home/completeQuest` | Забрать награду (`payload.rewards`, `quest`, `tutorial?`) |
| `/ingame/devTools/completeQuest`, `/resetQuest` | Отладка: довести прогресс до цели / жёсткий сброс |

## Главное подозрительное место

После 6-го квеста окна `questId = 0`, `progress = requiredProgress = 0`, а `reward` не обнуляется —
повторный `/completeQuest` снова выдаёт награду (по чтению кода, не проверено). Полный список — `#tradeoffs`.

## Ссылка на полный документ

`/workspace/server/.claude/docs/quests-architecture.md`

Разделы: 1 (назначение, жизненный цикл, окна/цепочки/сутки, туториал и isEndless), 2 (референсы и смежные документы), 3 (паттерны), 4 (список классов), 5 (навигация), 6 (таблица классов), 7 (классы подробно + источники прогресса `#progress-sources` + персистентность + контракт с клиентом), 8 (компромиссы и подозрительные места).
