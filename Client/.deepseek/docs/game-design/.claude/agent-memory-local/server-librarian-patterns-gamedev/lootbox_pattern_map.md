Карта серверных геймдев-паттернов для лутбоксов (поиск 2026-10-27, ветка koba/lootbox).

- Ленивые таймеры (абсолютный дедлайн, без планировщика): `/workspace/server/.claude/docs/airdrop-architecture.md#patterns`.
- Взвешенная рулетка (вычитание шансов из случайного процента, страховка последним элементом): там же, `AirDropData.getRandomBox`; `assembly-architecture.md#m-takereward` (`DropUtils.RollDrop`, веса по листам Balance).
- Ускорение стройки/производства за золото и расчёт доплаты недостающего: `/workspace/server/.claude/docs/military-base-architecture.md` (`/skipBuilding`, `getGoldenCoinsCostForDollarsCost`, §3 и §8 п.17).
- Авторитетная выдача и сериализация запросов игрока в акторе: `platform-sdk-architecture.md#patterns` (п. про `UserActor`), `platform-sdk-architecture.md` §7 (`sendShortcutReward`, проверка «выдано» внутри владельца).
- Антидубль при выдаче: `bag-architecture.md#m-add` (повторный add уже лежащего uid запрещён); антипример — `quests` п.1 и `assembly` п.2 (награда выдаётся повторно), см. memory `server_quests_deferred_fixes`.
- Детерминированный RNG на сервере: `battle-architecture.md#determinism` (`BattleRandom`, seed), догон реального времени — `#realtime`.

Ловушка: в `platform-sdk-architecture.md` раздел §7 не имеет якоря — ссылаться по заголовку.
Ловушка: `/workspace/server/.claude/docs/web-recommendations/README.md` — индекс пуст; web-рекомендаций по геймдев-задачам нет.
