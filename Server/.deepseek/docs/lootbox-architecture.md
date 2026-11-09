# Лутбоксы — `LootboxUserComponent` (сервер)

> **Обычный** (по итогам разработки по ГДД). Документ составлен `server-analyst-lootbox` по одобренному пользователем коду ветки
> `koba/lootbox` (2026-10-28, обновлён 2026-11-04, не закоммичено). Подтверждено чтением кода и сборкой `mvn -pl game -am compile`, запуском не проверялось.
> Клиентскую сторону разбирает `client-analyst-lootbox`, контракт сверяет `integration-lead`.

ГДД: [lootbox-gdd.md](/workspace/client/.claude/docs/game-design/lootbox-gdd.md). Награда квеста —
[quests-gdd.md#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward).

Смежные документы: [bag-architecture.md](bag-architecture.md) (`BagItem`,
[идемпотентная выдача](bag-architecture.md#p-idempotent-reward)),
[quests-architecture.md](quests-architecture.md), [reward-roll-pattern.md](reward-roll-pattern.md),
[refusal-with-state-pattern.md](refusal-with-state-pattern.md),
[military-base-architecture.md](military-base-architecture.md) (образец оплаты с доплатой золотом и
уведомления), [agent-system-workflow.md#no-server-scheduler](agent-system-workflow.md#no-server-scheduler).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. [Классы и методы](#classes)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Лутбокс (сундук) — стакуемый предмет сумки с отложенным открытием ([#gdd-purpose](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-purpose)).
Сундук хранится в сумке, игрок ставит его в ячейку открытия, ждёт окончания таймера или ускоряет
открытие за серебро с доплатой золотом и получает одну награду.

Состояние хранится в двух местах:

- **Сумка**: предмет `Lootbox` (`ItemType.LOOTBOX` = 7). `id` предмета = номер качества, то есть
  `Rank.ordinal()` (I..X = 1..10), `count` — количество ([#gdd-storage](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-storage), [#gdd-qualities](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-qualities)).
- **Компонент** `LootboxUserComponent` (поле `Lootbox` документа пользователя): ячейки открытия.
  В БД лежит документ `slots` вида `{"<номер ячейки>": {quality, startTime}}`. Хранится только время
  постановки, окончание считается от него по текущим данным.

Правила по коду:

- **Качества и данные** — Java-класс `LootboxData` (не лист `balance.json`). Времена открытия из
  [#gdd-open-time](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open-time). Числа наград, шансов случайного качества, курса серебро/золото —
  заглушки до [#gdd-open](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open). Ячейка одна (`SLOTS_COUNT = 1`).
- **Постановка** `/startOpen`: сервер сам выбирает свободную ячейку, списывает один сундук из сумки и
  запоминает время постановки ([#gdd-open-slot](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open-slot)). Снять сундук нельзя.
- **Окончание** = `startTime + duration` текущих данных. При смене времени открытия таймер
  пересчитывается от момента постановки; прошедшее время даёт «Открыть» сразу.
- **Открытие** `/open` — только когда таймер истёк. **Ускорение** `/speedup` — оплата серебром и
  золотом, потом то же открытие ([#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup)). Цена: остаток вверх до целых минут, 0,1 серебра
  за секунду, вверх до целого. Серебра хватает — платится серебро; не хватает — всё серебро и золото
  `ceil(остаток / 100)`. Сервер принимает пару клиента, если она не ниже цены за `остаток − 60 с`;
  истёкший таймер — бесплатно.
- **Награда** ([#gdd-contents](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-contents), [#gdd-claim](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-claim)): один тип по весам качества (`DropUtils.RollDrop`, без промаха),
  количество — случайно из диапазона типа. Награда начисляется на сервере; `rewards` в ответе — только
  для показа и полёта.
- **Таймер на клиенте.** Серверного планировщика нет ([#no-server-scheduler](agent-system-workflow.md#no-server-scheduler)). Сервер отдаёт
  `remaining` (мс, ≥ 0) в ячейке, в `/speedupPrice` и в `/checkReady`; клиент ведёт таймер сам и по
  срабатыванию спрашивает сервер ([#gdd-trophies-window](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-trophies-window)).
- **Значок «ТРОФЕИ»** — уведомление `NotificationId.LOOTBOX` (`"lootbox"`): ставится, если есть
  готовая ячейка. Пересчитывается при входе, на каждом авторизованном запросе (`User.onAuthorizedActive*`),
  после постановки и открытия и в `/checkReady`.
- **Лутбокс как награда задания** ([quests-gdd.md#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward)): награда каждого задания — шаблон в
  `QuestData.reward`. Шаблон случайного лутбокса (`randomQuality`) превращается в конкретный при
  «забрать».
- **Убранное качество** (`removeInvalidLootboxes`, при загрузке игрока): ячейка и сундуки этого
  качества в сумке убираются; компенсация не реализована ([#gdd-storage](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-storage), [#gdd-open](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open)).

<a id="references"></a>
## 2. Референсы

- Военная база: оплата с доплатой золотом и аналитика траты золота, уведомление `militaryBase`.
- `AirDropData`: данные Java-классом и взвешенный розыгрыш ([airdrop-architecture.md](airdrop-architecture.md)).
- Квесты: хранение награды в `QuestsUserComponent` ([quests-architecture.md](quests-architecture.md)).

<a id="patterns"></a>
## 3. Паттерны

- [Отказ со свежим состоянием](refusal-with-state-pattern.md): `error()` + `lootbox` в одном пакете
  (`LootboxPage.sendRefusal`). Черновик, ожидает регистрации.
- [Реестр наград «один тип на выбор»](reward-roll-pattern.md): реестр — `LootboxQualityData.rewards`,
  вариант — `LootboxReward`, бросок — `DropUtils.RollDrop`.
- [Идемпотентная выдача награды](bag-architecture.md#p-idempotent-reward): повтор отсекается состоянием
  ячейки (порядок сообщений `UserActor`), ключа идемпотентности нет.
- Таймеры без серверного планировщика: [#no-server-scheduler](agent-system-workflow.md#no-server-scheduler).

<a id="class-list"></a>
## 4. Список классов

Созданные:

| Класс | Путь (от `game/src/main/java/com/linkedgames/game/`) |
|---|---|
| `Lootbox` | `model/bag/lootbox/Lootbox.java` |
| `LootboxUserComponent` | `model/lootbox/LootboxUserComponent.java` |
| `LootboxSlot` | `model/lootbox/LootboxSlot.java` |
| `LootboxData` | `model/lootbox/data/LootboxData.java` |
| `LootboxQualityData` | `model/lootbox/data/LootboxQualityData.java` |
| `LootboxReward` | `model/lootbox/data/LootboxReward.java` |
| `LootboxResourceReward` | `model/lootbox/data/LootboxResourceReward.java` |
| `LootboxPage` | `pages/ws/ingame/LootboxPage.java` |
| `QuestRewardData` | `model/quests/data/QuestRewardData.java` |

Изменённые: `ItemType`, `ItemFactory`, `User`, `WSRouter`, `Globals`, `NotificationId`,
`AnalyticsSubjectId`, `QuestsUserComponent`, `QuestData`.

<a id="anchors"></a>
## 5. Навигация (якоря)

Разделы документа: [#purpose](#purpose), [#classes](#classes), [#tradeoffs](#tradeoffs),
[#gdd-link](#gdd-link), [#file-map](#file-map).
Классы: [#cls-lootbox](#cls-lootbox), [#cls-component](#cls-component), [#cls-slot](#cls-slot),
[#cls-data](#cls-data), [#cls-quality](#cls-quality), [#cls-reward](#cls-reward),
[#cls-page](#cls-page), [#cls-quest](#cls-quest), [#cls-glue](#cls-glue).
Контракт: [#contract](#contract).

<a id="class-nav"></a>
## 6. Оглавление по классам

[Lootbox](#cls-lootbox) · [LootboxUserComponent](#cls-component) · [LootboxSlot](#cls-slot) ·
[LootboxData](#cls-data) · [LootboxQualityData](#cls-quality) · [LootboxReward и
LootboxResourceReward](#cls-reward) · [LootboxPage](#cls-page) · [Квесты](#cls-quest) ·
[Регистрация и стык](#cls-glue) · [Контракт](#contract)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-lootbox"></a>
### Lootbox (`BagItem`)

Стакуемый предмет сумки, `ItemType.LOOTBOX`, `id` = `Rank.ordinal()`. Порядок `Rank` хранится в БД
(`id` предмета и `quality` ячейки) и в контракте (`quality`): `Rank` расширять только добавлением в конец.

- `createNew(quality, isTemplate)` — сундук качества, количество 1; шаблон получает `BagItem.EMPTY_UID`.
- `createRandom(isTemplate)` — шаблон случайного сундука: `id = 0`, флаг `randomQuality`. [#gdd-obtain](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-obtain).
- `getQuality()` — качество; для случайного и неизвестного `id` — `Rank.NONE`.
- `rollQuality()` — разыгрывает качество по `LootboxData.rollRandomQuality`, снимает флаг, отмечает поля
  `id` и `randomQuality` изменёнными. Вызывать до добавления в сумку: стопка с разыгранным качеством
  там не объединяется. [#gdd-obtain](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-obtain) (качество разыгрывается в момент «забрать»).
- `isStackableVariant`, `copy` — случайный и конкретный сундуки не склеиваются, `copy` переносит флаг.
- `dbMappingBuild`/`dbToData`/`apiResponse` — поле `randomQuality` пишется и отдаётся только при `true`.

<a id="cls-component"></a>
### LootboxUserComponent (`UserChildComponent`)

Компонент `Lootbox`: карта `slots` (номер ячейки → `LootboxSlot`), запись в БД одним `changedField`
(`dbSlotsChanged`).

| Метод | Что делает | Правило ГДД |
|---|---|---|
| `startOpen(quality)` | проверяет качество в данных, свободную ячейку в `[0, SLOTS_COUNT)` и сундук в сумке; списывает 1, кладёт ячейку, пересчитывает значок | [#gdd-open-slot](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open-slot) |
| `open(slot)` | только готовая действительная ячейка; разыгрывает награду, `finishOpen` | [#gdd-claim](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-claim) |
| `speedupAndOpen(slot, silver, gold)` | действительная ячейка; разыгрывает награду до списания; истёк — бесплатно; иначе проверяет знак и балансы пары, `silver + gold×100 ≥ speedupPrice(остаток − 60 с)`, списывает ровно пару (золото — аналитика `LOOTBOX_SPEEDUP`), `finishOpen` | [#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup) |
| `finishOpen(slot, reward, item)` (private) | удаляет ячейку, пишет в БД, `reward.addTo(user, item)`, пересчитывает значок, возвращает `rewards` | [#gdd-claim](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-claim) |
| `speedupPrice(remainingMs)` (private static) | остаток вверх до минут, × 0,1 серебра в секунду (`SPEEDUP_SILVER` / `SPEEDUP_SECONDS`), вверх до целого; ≤ 0 — 0 | [#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup) |
| `speedupPriceApiResponse(slot)` | `{remaining, price:{silver, gold}}` для действительной ячейки, иначе `null` (отказ) | [#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup) |
| `speedupPricesApiResponse()` | `{prices:[{slot, quality, remaining, price}]}` — снимок всех действительных ячеек; недействительные пропускаются, пустой массив это успех; расчёт через общий `speedupPriceEntry` | [#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup) |
| `hasReadySlot()` / `sendNotification()` | есть готовая ячейка — ставит `NotificationId.LOOTBOX`, иначе снимает | [#gdd-trophies-window](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-trophies-window) |
| `checkReady()` | пересчитывает значок и отдаёт `{remaining}` до ближайшего окончания среди действительных ячеек (0 — готово, поля нет — пусто) | [#gdd-trophies-window](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-trophies-window) |
| `findFreeSlot()` (private) | первая свободная ячейка до `SLOTS_COUNT`; ячейки сверх числа остаются до открытия | [#gdd-open-slot](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open-slot) |
| `removeInvalidLootboxes()` | при `User.onInitialized` убирает недействительные ячейки и сундуки убранных качеств из сумки (случайные не трогает), зовёт `compensateRemovedLootbox` | [#gdd-storage](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-storage) |
| `compensateRemovedLootbox(quality, count)` | пустая точка расширения | [#gdd-open](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open) |
| `apiResponse()` | `{slotsCount, slots:[...]}`, недействительные ячейки пропускаются | — |
| `finishAllOpen()` | только dev: во всех действительных ячейках `finishImmediately()`, затем `dbSlotsChanged` и `sendNotification`; `false`, если менять нечего | — |
| `dbMappingBuild` | читает `slots`, пропускает ключи не числа и не документы | — |

Повтор: `open`/`speedupAndOpen` после успешного открытия не находят ячейку и отказывают, повторной
выдачи и списания нет. Награда разыгрывается до списания и удаления ячейки: ошибка розыгрыша не
теряет ни сундук, ни валюту.

<a id="cls-slot"></a>
### LootboxSlot (`IPersistentObject`)

Ячейка: `quality`, `startTime`. Mongo `{quality, startTime}`.

- `isValid()` — `startTime > 0` и качество есть в `LootboxData`; единственная проверка действительности.
- `getEndTime()` — `startTime + duration` текущего качества; у недействительной `Long.MAX_VALUE`
  ([#gdd-open-slot](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open-slot)).
- `isReady(now)` — действительна и `endTime ≤ now`.
- `getRemainingMs(now)` — `max(0, getEndTime() − now)`; остаток ячейки
  ([#gdd-trophies-window](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-trophies-window)).
- `apiResponse(slot)` — `{slot, quality, remaining}`, `remaining` из `getRemainingMs`.
- `finishImmediately()` — только для dev-инструментов: сдвигает `startTime` на `duration` в прошлое,
  качество не меняется; у недействительной ячейки ничего не делает.

<a id="cls-data"></a>
### LootboxData

Справочник в Java. Поля: `SLOTS_COUNT`, `SPEEDUP_SILVER`/`SPEEDUP_SECONDS` (ставка 1 серебро за 10 с),
`SILVER_PER_GOLD` = 100, `SPEEDUP_PRICE_TOLERANCE_MS` = 60 000, `QUALITIES` (Rank → `LootboxQualityData`),
`RANDOM_QUALITY_CHANCES`.

- `getQuality(rank)` — данные качества или `null`.
- `rollRandomQuality()` — случайное качество из `RANDOM_QUALITY_CHANCES` среди тех, что есть в `QUALITIES`,
  через `DropUtils.RollDrop` ([#gdd-obtain](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-obtain)).
- `validate()` — вызывается из `Globals.preload`: длительность > 0, у качества есть награды и сумма
  весов > 0, веса случайного качества ≥ 0 и сумма по `QUALITIES` > 0. Ошибка — `IllegalStateException`,
  старт останавливается. Вызов в `preload`, потому что `ExceptionInInitializerError` из static-блока не
  ловится `catch (Exception)` в `Globals.start()`.
- `apiResponse()` — `{qualities:[...]}` для `/info`.

<a id="cls-quality"></a>
### LootboxQualityData

Качество: `quality`, `duration` (мс), `rewards` (`DroppedItem<LootboxReward>`).

- `rollRewardType()` — `DropUtils.RollDrop(rewards)`, один тип за открытие ([#gdd-contents](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-contents)).
- `validate()` — проверки данных качества, делегирует `LootboxReward.validate(context)`.
- `apiResponse()` — `{quality, duration, rewards:[{itemType, id, min, max}]}`.

<a id="cls-reward"></a>
### LootboxReward и LootboxResourceReward

`LootboxReward` — точка расширения «тип награды»: `roll()` (разыграть `Item`), `addTo(user, item)`
(выдать своим путём и вернуть JSON для `rewards`), `apiResponse()` (описание для попапа),
`validate(context)`. Выдачу каждый тип делает сам, потому что `User.addItem` кладёт в сумку любой
`BagItem`, а танк или самолёт должны попасть в ангар или на аэродром.

`LootboxResourceReward(resourceId, min, max)` — ресурс в диапазоне: `roll()` создаёт ресурс-шаблон со
случайным количеством, `addTo` вызывает `user.addItem(item, AnalyticsSubjectId.LOOTBOX_OPEN)`,
`validate` требует `1 ≤ min ≤ max` (нулевое количество `BagUserComponent.add` отклонило бы уже после
траты сундука).

Не реализовано: награды-танки и награды-самолёты (ангар, аэродром, замена слабейшего), генералы —
отдельный ГДД ([#gdd-contents](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-contents)).

<a id="cls-page"></a>
### LootboxPage (`/ingame/lootbox`)

Маршруты и действия — в [#contract](#contract). Общие приватные помощники:

- `createLootboxResponse(pageProcessor, lootbox)` — `createResponse()` плюс `lootbox` в payload; статус
  `ok()`/`error()` задаёт вызывающий. Используют `actionIndex`, `actionStartOpen`, `sendOpenResult`
  (добавляет `rewards`) и `sendRefusal`.
- `readSlot(pageProcessor)` — `optInt("slot", -1)`; используют `actionSpeedupPrice`, `actionSpeedup`,
  `actionOpen`.
- `sendRefusal` — `error()` плюс `lootbox` в одном пакете ([паттерн](refusal-with-state-pattern.md)).
- Dev-маршрут вне этого страницы: `DevToolsPage` (`/ingame/devTools/lootboxFinishOpen`) зовёт
  `finishAllOpen()` и отдаёт `{lootbox}`; клиентская кнопка — в `LootboxIdleSection` под `Globals.isDevTools()`.
  Отключение: убрать роут и кнопку, `finishAllOpen`/`finishImmediately` остаются неиспользуемыми.

<a id="cls-quest"></a>
### Квесты: QuestRewardData, QuestData, QuestsUserComponent

- `QuestRewardData` — настройка награды задания: `of(item)` и `randomLootbox(count)`; `validate(context)` —
  награда это шаблон (`EMPTY_UID`) и `count > 0`.
- `QuestData.reward` — у каждого задания; сейчас у всех заглушка «случайный лутбокс ×1». `QuestData.validate()`
  вызывается из `Globals.preload`.
- `QuestsUserComponent.gainNewQuest` берёт награду из `QuestData`, градация 3/2/1 убрана
  ([#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward)); `createTakenReward()` при «забрать» разыгрывает качество у копии шаблона,
  остальные награды отдаёт как есть. Задания, выданные раньше, доделываются со старой наградой в `rew`.

<a id="cls-glue"></a>
### Регистрация и стык

- `ItemType`: `COLLECTION_ITEM` (6, заглушка под ветку коллекций, в `ItemFactory` нет) и `LOOTBOX` (7).
  Ordinal = поле `t` в БД: значения только в конец. `ItemFactory`: `LOOTBOX → Lootbox::new`.
- `User`: поле, `getLootboxUserComponent()`, `P_LOOTBOX_FIELD = "Lootbox"`, чтение в `dbMappingBuild`,
  `sendNotification()` в `onAuthorizedActiveOnce`/`onAuthorizedActive`, `removeInvalidLootboxes()` в `onInitialized`.
- `NotificationId.LOOTBOX = "lootbox"`; `AnalyticsSubjectId.LOOTBOX_OPEN`, `LOOTBOX_SPEEDUP` (в конец, в БД хранится ordinal).
- `WSRouter`: `/ingame/lootbox`. `Globals.preload`: `LootboxData.validate()`, `QuestData.validate()`.
- Idle-сбор (`IdleUserComponent`, `HomePage /idle`) не менялся: трофеи начисляются при открытии окна,
  окно запрашивает `/idle` и `/ingame/lootbox` параллельно.

<a id="contract"></a>
### Контракт `/ingame/lootbox/…`

Время в мс. Успех — `ok`; отказ — `error` без `reason` и свежий `{lootbox}` в payload.
`lootbox` = `{slotsCount, slots:[{slot, quality, remaining}]}`; свободной ячейки в `slots` нет.

| Маршрут | Запрос | Ответ ok | Отказ |
|---|---|---|---|
| `""` (`actionIndex`) | `{}` | `{lootbox}` | — |
| `/info` | `{}` | `{qualities:[{quality, duration, rewards:[{itemType, id, min, max}]}]}` | — |
| `/startOpen` | `{quality}` | `{lootbox}` | нет качества, ячейки или сундука |
| `/checkReady` | `{}` | `{remaining?}` | — |
| `/speedupPrice` | `{slot}` | `{remaining, price:{silver, gold}}` | нет действительной ячейки |
| `/speedupPrices` | `{}` | `{prices:[{slot, quality, remaining, price:{silver, gold}}]}` | отказа нет: недействительные ячейки пропускаются, пустой массив — успех |
| `/speedup` | `{slot, price:{silver, gold}}` | `{lootbox, rewards:[ItemJSON]}` | нет ячейки, цена ниже, не хватает баланса; нет price/полей или отрицательные — отказ на неготовую ячейку, на готовую цена игнорируется |
| `/open` | `{slot}` | `{lootbox, rewards:[ItemJSON]}` | нет ячейки или таймер не истёк |

Предмет сумки: `{id, itemType:7, count, uid}`; случайный: `{id:0, itemType:7, count, randomQuality:true}`.
`QuestJSON.reward` — любой предмет, случайный лутбокс — `reward.randomQuality: true`; `rewardRandom`
не существует. `/ingame/home/completeQuest` отдаёт в `rewards` уже конкретный сундук.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

1. **Компенсация за убранное качество пустая.** `compensateRemovedLootbox` ничего не выдаёт, сундуки
   и ячейка исчезают без возврата. Чем и сколько — открытый вопрос ГДД ([#gdd-open](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open)).
2. **Порядок `Rank` хранится в БД.** `quality` ячейки и `id` предмета — ordinal; вставка или
   перестановка значений `Rank` испортит данные.
3. **Запись сумки и документа не атомарна.** Ячейка (`userToDb`) и предметы (`bagToDb`) пишутся
   независимыми записями без общей транзакции ([bag p-idempotent-reward п.2](bag-architecture.md#p-idempotent-reward)). Сбой между ними даёт либо
   списанный сундук без ячейки, либо ячейку без списания, либо выданную награду при ещё стоящей ячейке.
   Принятый риск.
4. **Идемпотентность — только состоянием ячейки.** Повторный `/open`/`/speedup` отсекается отсутствием
   ячейки, `/startOpen` — отсутствием сундука или свободной ячейки. Ключа запроса нет.
5. **Допуск 60 с в цене ускорения.** В последнюю минуту таймера проходит пара `{0, 0}`: решение
   пользователя, [#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup).
6. **`rollQuality` только до добавления в сумку.** Порядок вызовов держит вызывающий
   (`createTakenReward`); сундук с разыгранным качеством, добавленный после, склеится с обычной
   стопкой, а добавленный до разыгрыша — нет. Кандидат на метод-переход у владельца
   ([#no-implicit-order](agent-system-workflow.md#no-implicit-order)).
7. **`checkReady` считает остаток отдельно.** `remaining` ячейки берут `LootboxSlot.getRemainingMs`
   (`apiResponse`, `speedupPriceApiResponse`, проверка цены в `speedupAndOpen`); `checkReady` ищет
   ближайшее `getEndTime()` среди действительных ячеек сам. Маршрут `/checkReady` и форма ответа
   `/speedupPrice` оставлены по решению пользователя (2026-10-30).
8. **Задание с фиксированным лутбоксом убранного качества** не обрабатывается: сундук попадёт в сумку и
   не откроется. Награда `Tank`/`Airplane` у `QuestRewardData.of` и у `LootboxReward` не поддержана.
9. **Числа баланса — заглушки**: награды, шансы качеств, курс, ставка ([#gdd-open](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open)). Повторная выдача награды
   квеста — вне области, см. [quests-architecture.md](quests-architecture.md).
10. **`finishOpen` удаляет ячейку до выдачи.** Исключение в `addTo` после удаления потеряет награду;
    данные проверяются при старте (`validate`), чтобы это не случалось.

<a id="gdd-link"></a>
## 9. Связь с ГДД

| Раздел ГДД | Где реализовано |
|---|---|
| [#gdd-qualities](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-qualities) | `Lootbox`, `LootboxData.QUALITIES`, `Rank` |
| [#gdd-storage](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-storage) | `Lootbox`, `removeInvalidLootboxes` |
| [#gdd-obtain](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-obtain) | `Lootbox.createRandom/rollQuality`, `QuestRewardData`, `createTakenReward` |
| [#gdd-trophies-window](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-trophies-window) | `sendNotification`, `checkReady`, `remaining`; `/idle` без изменений |
| [#gdd-open-slot](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open-slot), [#gdd-open-time](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open-time) | `startOpen`, `LootboxSlot`, `LootboxData` |
| [#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup) | `speedupAndOpen`, `speedupPrice`, `speedupPriceApiResponse`, `speedupPricesApiResponse` |
| [#gdd-contents](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-contents), [#gdd-claim](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-claim) | `LootboxQualityData.rollRewardType`, `LootboxReward`, `finishOpen`, `LootboxPage.sendRefusal` |
| [#gdd-open](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-open) | числа-заглушки в `LootboxData`, `compensateRemovedLootbox` |

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от `/workspace/server/game/src/main/java/com/linkedgames/game/`.

### Файлы прямого влияния

- `model/bag/lootbox/Lootbox.java` — предмет сумки.
- `model/lootbox/LootboxUserComponent.java` — компонент, ячейки, цена, открытие.
- `model/lootbox/LootboxSlot.java` — ячейка и её окончание.
- `model/lootbox/data/LootboxData.java` — качества, ставка, курс, случайное качество, проверка.
- `model/lootbox/data/LootboxQualityData.java` — длительность и награды качества.
- `model/lootbox/data/LootboxReward.java` — интерфейс типа награды.
- `model/lootbox/data/LootboxResourceReward.java` — награда-ресурс.
- `pages/ws/ingame/LootboxPage.java` — маршруты `/ingame/lootbox`.
- `model/quests/data/QuestRewardData.java` — настраиваемая награда задания (создан для лутбоксов).

### Файлы косвенного влияния

- `model/user/User.java` — поле компонента, `P_LOOTBOX_FIELD`, `dbMappingBuild`, хуки `onAuthorizedActive*`, `onInitialized`.
- `model/item/ItemType.java` — `LOOTBOX` = 7 (и заглушка `COLLECTION_ITEM` = 6).
- `model/item/ItemFactory.java` — `LOOTBOX → Lootbox::new`.
- `pages/WSRouter.java` — регистрация `/ingame/lootbox`.
- `Globals.java` — `LootboxData.validate()`, `QuestData.validate()` в `preload`.
- `model/notifications/NotificationId.java` — `LOOTBOX = "lootbox"`.
- `model/analytics/AnalyticsSubjectId.java` — `LOOTBOX_OPEN`, `LOOTBOX_SPEEDUP`.
- `model/quests/QuestsUserComponent.java` — награда из `QuestData`, `createTakenReward`.
- `model/quests/data/QuestData.java` — `reward` у заданий, `validate()`.
- `game/src/main/resources/balance.json` — не используется: данные лутбоксов в `LootboxData`.
- зависимость: `model/Rank.java` — качества, порядок хранится в БД.
- зависимость: `model/bag/BagUserComponent.java` — списание сундука и валюты, `getItem`.
- зависимость: `model/notifications/NotificationUserComponent.java` — уведомление `lootbox`, не сохраняется в БД.
- зависимость: `service/drop/DropUtils.java`, `DroppedItem.java` — взвешенный бросок.
- зависимость: `service/analytics/GameAnalytics.java` — аналитика траты золота.
