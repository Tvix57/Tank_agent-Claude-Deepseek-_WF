---
name: server-airdrop-component
description: "Назначение, архитектура и реализация серверной части AirDrop (ящики с золотом в кампании)"
metadata:
  node_type: memory
  type: reference
  status: auto-create
  date: 2026-09-28
  originSessionId: 6dd5d0e9-e340-48f7-a193-067cf524609e
  modified: 2026-09-28T04:34:13.828Z
---

# Server: AirDrop (ящики с золотом в кампании)

**Статус: auto-create** — документ составлен аналитиками по результатам сканирования кода (2026-09-28). Доверять с осторожностью, перепроверять по актуальному коду при использовании.

## Краткое резюме

Серверная часть AirDrop — случайные "ящики с неба" в кампании: клиент раз в минуту просит бросок
(`/sendAirDrop`), сервер с шансом 10/5/2,5/1 % (по номеру награды за день) выбирает цвет ящика и даёт
5 мин + 5,5 с на сбор (`/getAirDrop`) — награда: золотые монеты (`RESOURCE_GOLDEN_COINS`), диапазон
по цвету. Лимит — 4 награды в сутки. Весь баланс захардкожен в `AirDropData` (не в `Balance`/`balance.json`).
Сервер авторитетен: тип, срок жизни и награда определяются только на сервере.

## Основные классы

| Класс | Назначение |
|-------|-----------|
| `model/campaign/data/AirDropBoxType` | Enum цветов: NONE, GREY, GREEN, BLUE, PURPLE, YELLOW (строка "orange"), RED |
| `model/campaign/data/AirDropBox` | Строка баланса: тип, шанс цвета, диапазон награды в золоте |
| `model/campaign/data/AirDropData` | Захардкоженные константы баланса (кулдаун, срок жизни, шансы) и рандом |
| `model/campaign/CampaignUserComponent` (airDrop-часть) | Состояние игрока, выдача, ленивые таймеры, персистентность |
| `pages/ws/ingame/CampaignPage` (airDrop-роуты) | WS-роуты броска и сбора |
| `pages/ws/ingame/dev/DevToolsPage` (airDrop dev-роуты) | Отладочные роуты (при `app.devTools=true`) |

## Роуты (WS)

| Маршрут | Назначение |
|---------|-----------|
| `/ingame/campaign/sendAirDrop` | Бросок / возврат уже активного ящика (`payload.airDrop`) |
| `/ingame/campaign/getAirDrop` | Забрать ящик, получить золото (`payload.airDropReward`) |
| `/ingame/devTools/airDropChance`, `/airDropForce`, `/airDropReset` | Отладка: бросок без кулдауна, гарантированный ящик, сброс суточного счётчика |

## Ссылка на полный документ

`/workspace/server/.claude/docs/airdrop-architecture.md`

Разделы: 1 (назначение, контекст CampaignUserComponent, жизненный цикл, баланс), 2 (референсы), 3 (паттерны), 4 (список классов), 5 (навигация), 6 (таблица классов), 7 (классы подробно + персистентность + контракт с клиентом), 8 (компромиссы и подозрительные места).
