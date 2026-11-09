---
schema: 1
name: server_tutorial_architecture.md
type: project
title: Назначение, архитектура и реализация серверного компонента Туториал (TutorialUserComponent)
source: .claude/memory/server_tutorial_architecture.md
claude: |
  name: server-tutorial-component
  description: "Назначение, архитектура и реализация серверного компонента Туториал (TutorialUserComponent)"
  metadata:
    node_type: memory
    type: reference
    status: auto-create
    date: 2026-09-28
---

# Server: Туториал (TutorialUserComponent)

**Статус: auto-create** — документ составлен server-analyst-lead по существующему коду (2026-09-28), код не менялся. Перепроверять по актуальному коду при использовании.

## Краткое резюме

Одно поле `progress` в поддокументе `Tutorial.pg`: `0..20` — шаг (`TutorialSteps`), `-1` — выключен.
Пять циклов "призыв поезда → принять танк → прогресс туториального квеста (11–15, TANK_DESTROY 1..5) →
забрать награду", шаг 20 — финальный бой. Шаги двигают `TrainPage` (/summon, /accept),
`QuestsUserComponent` (triggerEvent, completeQuest) и `CampaignPage` (/battle, /battleResult) через
`increase(step)` (срабатывает только при совпадении шага). В туториале: фиксированные танки поезда,
бот-команда из `TutorialData`, бой всегда победа без эмуляции, без выпадения схем. Существующим
игрокам туториал выключен миграцией `1757495348631_skip_tutorial.json`.

## Основные классы

| Класс | Назначение |
|-------|-----------|
| `model/tutorial/TutorialUserComponent` | Шаг, `isEnabled`, `increase`, `apiResponse` `{progress}` |
| `model/tutorial/data/TutorialSteps` | Enum шагов 0..20, `MAX = 20` |
| `model/tutorial/data/TutorialData` | Танки игрока/врага, `ENEMY_COUNT`, `TUTORIAL_QUESTS`, награда 50 |

## Контракт

`tutorial: {progress}` — в `account` (apiResponseFull), ответах /ingame/train/summon|accept,
/ingame/home/completeQuest, /ingame/campaign/battle|battleResult и push `/events/quest/update`.
Выключен = нет ключа (кроме ответа кампании в момент завершения: `progress: -1`).

## Главное подозрительное место

Туториал выключается уже на `/battle` шага 20 (до `createBattle`), поэтому финальный бой — с обычным
ботом и реальной эмуляцией. Полный список — `#tradeoffs`.

## Ссылка на полный документ

`/workspace/server/.claude/docs/tutorial-architecture.md`

Разделы: 1 (назначение, сценарий `#flow`, эффекты `#effects`), 2–6 (референсы, паттерны, классы, якоря), 7 (классы, `#consumers`, `#migration`, `#persistence`, `#client-contract`), 8 (`#tradeoffs`). Квестовая часть — `quests-architecture.md#tutorial` (перекрёстные ссылки в обе стороны).
