# Клиентские паттерны наград, таймеров, сеток и полёта иконок

Раздел заведён по WF `#pattern-gap` при подготовке фичи «Лутбоксы» (2026-10-27,
`client-analyst-lead`, по коду ветки `koba/lootbox` = `master` 5ede1134). Описано то, что есть в
коде. Где общего решения в коде нет, сказано прямо и перечислены ближайшие приёмы; выбор решения
для лутбоксов не принят и идёт пользователю.

ГДД: [game-design/lootbox-gdd.md](game-design/lootbox-gdd.md).

Классы и оглавление по классам (п.4, п.6 стандарта): новых и изменённых классов нет, документ
описывает существующий код; классы перечислены в [карте файлов](#files).

**Разделы:** [Реестр типов наград](#reward-type-registry) ·
[Таймер с ускорением и доплатой](#timer-speedup) · [Сетка с пагинацией](#paged-grid) ·
[Награда по данным сервера](#server-reward-config) · [Полёт иконок к цели](#fly-to-target) ·
[Расхождения доков с кодом](#doc-drift) · [Карта файлов](#files)

## Реестр типов наград {#reward-type-registry}

**Отрисовка — один диспетчер, таблицы выдачи нет.** Таблицы `itemType → обработчик выдачи` в клиенте
нет; для отрисовки есть один диспетчер.

Что есть:
- Диспетчер `ItemsPresets.createImageLayout` (`src/presets/ItemsPresets.ts:13`) — `switch (itemType)` по
  `RESOURCE`/`TANK`/`AIRPLANE`/`LOOTBOX`; неизвестный тип даёт пустой `Layout` 25×25. Ветки `TANK`/`AIRPLANE`
  пустые. `createRewardsLayout` (`:115`) своего свитча не имеет: вызывает `this.createImageLayout(data[i])`
  (`:119`) и добавляет число. Подробно — [items-presets-architecture.md#s8](items-presets-architecture.md#s8).
  Состояние: в ветке `koba/lootbox` второй свитч в `createRewardsLayout` снят, файл не закоммичен.
- Пример — ветка `LOOTBOX` (`:24-26`) → `createImageLootbox(data.id, (data as LootboxJSON).randomQuality === true, 0.3)`
  (`:32`). `id` награды трактуется как качество сундука; флаг `randomQuality` (поле
  `LootboxJSON`, `src/views/home_screen/popups/bag/bag.d.ts:60`) переключает показ: случайное качество — без
  тинта, со знаком «?»; иначе тинт `Const.getTechColor(quality)`. Масштаб задаёт вызывающий: 0.3 в
  наградах, 0.55 в списке и слотах лутбокса (`LootboxIdleSection`), 0.8 в `LootboxSpeedupPopup` и
  `LootboxStartOpenPopup`, 1 в `LootboxReceivedPopup`. Попапы лутбокса вызывают `createImageLootbox`
  напрямую, минуя диспетчер; диспетчер используется для наград (`LootboxRewardPopup` через
  `createRewardsLayout`).
- Внутри `RESOURCE` второй уровень выбора — цепочка `if` по `ItemId` в `createImageResource` (золото,
  серебро, схема танка, схема самолёта).
- Выдача награды (удержание + полёт) — общий `RewardFlightUtils` ([#fly-to-target](#fly-to-target)) у
  `HomeScreenQuest`, `IdlePopup`, `LootboxIdleSection`. Остальные места пишут удержание вручную по жёстко
  заданным `ItemId`: `HomeScreen` (`/ingame/train/accept|refuse`), `GoldenCoinsOfferPopup`,
  `MilitaryBaseStoragePopup`, `TrainBuySchemesPopup`, `CampaignBattleGround`, `AirDrop`. Ищет ресурс
  `RewardUtils.getResource` (`src/plain/RewardUtils.ts`, складывает дубли ресурса в списке).
- Единственные таблицы-соответствия в клиенте — статические `Map<number, number>` в
  `src/plain/military_base/MilitaryBaseBoostRouter.ts` (id здания → id бустера). Это данные, а не
  обработчики, но форма «статическая таблица в `src/plain/`» в проекте уже принята.

Чего не хватает для лутбокса (ТЗ: «лутбокс должен расширяться под любой ресурс или предмет»):
отрисовка уже в одном месте (`createImageLayout`, ветка `LOOTBOX` есть), но для типа награды всё ещё
нет единого места с целью полёта: `RewardFlightUtils` держит таблицу только для ресурсов, а `ItemType`
(генерал) потребует правки свитча и таблицы полёта отдельно. Правило `#gdd-function-mapping`: два
свитча выражали одно правило («как нарисовать предмет»); в ветке сведено к одному, второй свитч не
восстанавливать.

## Таймер с ускорением и доплатой {#timer-speedup}

**Общего компонента нет.** Есть общий механизм тика и две игровые реализации.

Механизм:
- Время — `TimeUtils.nowMls()` (`src/utils/TimeUtils.ts`): серверное время из
  `Globals.serverInfo.time` (`TimeUtils.updateS`, `Globals.ts:84`) плюс локальный `Date.now()`;
  пересчёт на каждый кадр (`App.pixiApp.ticker.add(() => TimeUtils.update())`, `Globals.ts:55`).
  Остаток считается как `deadline − nowMls()`, поэтому после фона таймер верный.
- Секундный тик — `App.tick.add(layout, { isValid, onTickSecond(e), onRequest(e, done) })`; по
  `e.toRequest()` вызывается `onRequest` (обычно запрос или закрытие окна). Тик живёт, пока жив
  `layout`: валидность по умолчанию — `generationObject.objVersion() != 0` (`src/ee/tick/TickElement.ts`),
  поэтому `isValid: () => true` в лутбоксе равнозначен умолчанию.
- Обёртка `Every` (`src/plain/Every.ts`) — «вызывать callback раз в N мс» поверх того же тика,
  с `remove()`. Так сделан AirDrop ([airdrop-architecture.md](airdrop-architecture.md)).
- Формат — `TimeUtils.timeDDHHMMSS_Mls(left)`.

Реализации:
- Ускорение стройки, `MilitaryBaseSkipBuildingPopup` — тик раз в секунду обновляет текст таймера
  и вызывает `updateCost()`: цена из баланса на клиенте (`MilitaryBaseData.getSkipBuildingCost`,
  постоянная, от остатка не зависит), кнопка гаснет при нехватке золота. `left <= 0` или пропал
  `buildingTime` → окно закрывается. Запрос `/ingame/militaryBase/skipBuilding`. Подробно —
  [military-base-architecture.md#cls-buy-skip](military-base-architecture.md#cls-buy-skip).
- Доплата недостающей валюты, `MilitaryBaseMissingDollarsPopup` — сервер на неуспешный запрос
  возвращает `missingDollars` и `goldenCoinsCost`, клиент их только показывает и повторяет тот же
  запрос (`handlerUrl` + `payload`) с `useGoldenCoins: true`; при OK вызывает `onSuccess(response)`.
  Используется в четырёх окнах базы. Цену доплаты клиент не считает.
- Срок жизни ящика AirDrop — `Every` раз в секунду, сравнение `airDropDeadTime` с `nowMls()`,
  без ускорения.
- Лутбокс, пример — `LootboxIdleSection` (секция слотов и сетки, `src/views/home_screen/popups/lootbox/LootboxIdleSection.ts`)
  и `LootboxSpeedupPopup` (тот же каталог):
  - Конец отсчёта — абсолютное время: `endTimeBySlot.set(slot, nowMls() + slot.remaining)` (`LootboxIdleSection.setLootbox`,
    `:91`), в попапе `endTime = nowMls() + config.slot.remaining` (конструктор, `:40`). Остаток —
    `Math.max(0, end − nowMls())` (`getRemaining`, `:101`; в попапе `getTimerText`, `:78`).
  - Секундный тик — `App.tick.add(layout, { isValid: () => true, onTickSecond })`: в `LootboxIdleSection`
    (`:58`) `onTickSecond` вызывает `updateTimers()` — пишет текст в `info.timer`, при остатке 0
    перерисовывает слоты (`showSlots`); в попапе (`:53`) — `updateTimer()`, обновляет `content.window…timer`.
  - Цена — не на тике, а `new Every(layout, 60000, …)` (`LootboxIdleSection:55`,
    попап `:57`): `LootboxState.requestSpeedupPrice(slot)` (`/ingame/lootbox/speedupPrice`). Ответ несёт
    `price` и `remaining`; по нему заново `end = nowMls() + response.remaining` (`LootboxIdleSection:216`,
    попап `:98`). Пока цены нет (`null`), кнопка открытия в попапе не работает (`onOpenNow`, `:111`).
  - Клиент цену не вычисляет: `LootboxState.speedup(slot, price)` (`LootboxState.ts`) шлёт
    `{ slot, silver, gold }` из последнего ответа сервера. Если золота не хватает (`price.gold` больше
    остатка в сумке) — попап закрывается и открывает магазин (`footer.openShop()`, `:116`).

Чего не хватает для лутбокса (ТЗ: 0,1 серебра за секунду оставшегося времени, недостающее серебро
докупается золотом, ГДД: [game-design/lootbox-gdd.md](game-design/lootbox-gdd.md)): на клиенте цена
обновляется раз в минуту, а не каждую секунду, и между запросами показ может отставать от серверной
цены. Клиент отправляет в `speedup` цену из последнего ответа, значит сервер должен пересчитать и
сверить её при списании. У стройки цена постоянная, у доплаты её считает сервер после отказа.
Формула и место расчёта (клиент для показа, сервер для списания, одна формула на обеих сторонах или
цена из ответа) — вопрос контракта, решать через `integration-lead`.

## Сетка с пагинацией {#paged-grid}

**Общая сетка с пагинацией в коде не собрана.** Сетка и пагинатор есть по отдельности, вместе нигде не
соединены: в лутбоксах сетка показывается целиком и пагинатора нет (убрали 2026-11-04).

- Сетка — `new Layout({ direction: Layout.Direction.GRID, gridColumns: N, spacing: [x, y] })`;
  так сделаны ангар (4 колонки, `HomeScreen.ts:424`), `BattlefieldPopup`, аэродром базы, магазин, ресурсы
  базы (5), профиль, бан-панель (3), сетка лутбоксов (5). Серверной пагинации ни в одной сетке нет.
  Кодекс — своя таблица ранг × страна × тип ([codex-architecture.md](codex-architecture.md)), тоже без страниц.
- Пагинатор — `AdvancedPaginator` (`src/shared/paginators/AdvancedPaginator.ts`): кнопки «<<», «<»,
  до 5 номеров, «>», «>>»; колбэки `firstButton/prevButton/nextButton/lastButton/numberedButton`
  задаёт владелец; `updatePageNav(curPage, maxPage)` перерисовывает номера.
  «В конец» — запрос страницы `AdvancedPaginator.MAX_PAGE_TEMPLATE`, настоящий номер возвращает
  сервер. Используется в восьми местах с одной схемой: семь секций рейтинга
  (`src/views/home_screen/popups/rating/Rating{Power,Tanks,Airplanes,Campaign,CampaignRanking,Clan,Battlefield}Section.ts`,
  запросы `/ingame/rating/*` и `/ingame/campaign/rankedRating` с `{ page }`) и `BanHistoryPanel`
  (`/ingame/banPanel/history { userId, page }`): запрос → сохранить ответ → пересоздать список →
  `updatePageNav(data.page, data.maxPage)`. Во всех секциях рейтинга список вертикальный
  (`Layout.Direction.TOP_TO_BOTTOM`), не сетка. Секции рейтинга почти дословно повторяют друг друга
  (разные маршрут и тип строки) — находка `#gdd-function-mapping`, для лутбоксов не трогается.
- `PaginatorConfig` в `src/types/interfaces.d.ts:60` (поле `GameFlashConfig.paginator`) в коде
  клиента никем не заполняется.

Варианта с локальной пагинацией в коде больше нет: в `LootboxIdleSection` (лутбоксы) пагинатор убран
2026-11-04 по решению пользователя, сетка строится целиком из всех качеств в сумке
(`LootboxState.getQualitiesInBag()`, `new Layout({ direction: Layout.Direction.GRID, gridColumns: 5 })`).
Это рабочий пример «данные уже на клиенте, сервер страниц не знает» без самого пагинатора — если пагинация
понадобится заново, сочетание «GRID-`Layout` + `AdvancedPaginator`» по-прежнему надо собирать с нуля.

Для серверной пагинации сочетание «GRID-`Layout` + `AdvancedPaginator` + `{ page }` → `page/maxPage`»
повторяет схему рейтинга.

## Награда по данным сервера {#server-reward-config}

**В коде нет** описания награды, которое клиент рисует, не зная её тип заранее, кроме минимального
`ItemJSON { id, itemType, count }` (`popups/bag/bag.d.ts`). Ответы с наградами (`rewards: ItemJSON[]`:
квест, поезд, idle, магазин, склад базы) клиент рисует через `ItemsPresets.createRewardsLayout`, а
выдаёт по жёстко заданным `ItemId` ([#reward-type-registry](#reward-type-registry)).

Чего нет для лутбокса (изображение 5 ТЗ: «Золото 20 - 500», «схемы поезда 3 - 15», «Умение», «Генерал»
без числа): диапазона количества, награды без количества и состава возможных наград, пришедшего с
сервера. `CampaignLevelRewardsJSON` (`popups/campaign/campaign.d.ts`) держит награды как `any[]` и
образцом не служит. Формат — серверный контракт, через `integration-lead`.

## Полёт иконок к цели {#fly-to-target}

Есть в `src/shared`, на уровне `Creator`/`Layout` (`src/ee/`) нет и не будет: `src/ee/` не меняется
(CLAUDE.md).

- Отправитель — `FlyIconsAnimation.play(name, count, from, onEnd, { scale })`: только эмитит
  `GameEvents.FLY_ICONS` с именем цели и мировой точкой вылета (`Coord.getWorldPosition(...)`).
- Получатель — виджет-цель подписан на `FLY_ICONS`, сравнивает `data.name` со своей константой и
  сам вызывает `FlyIconsAnimation.publish(scene, { asset, count, from, to, scale, type, onEnd })`,
  считая `to` по своему контейнеру. Цели: `HEADER_SILVER_COINS`, `HEADER_GOLDEN_COINS`,
  `HEADER_DOLLARS`, `HEADER_TOKENS` (бары хедера), `TRAIN_TANK_SCHEMES` (`HomeScreen.onFlyIcons`),
  `HOME_AERODROME_AIRPLANE_SCHEMES` (только в неподключённом `HomeScreenAerodrome`).
- Анимация — спрайты по дуге Безье (`ANIMATION_ARC`, по умолчанию) или по прямой (`ANIMATION_LINE`),
  с разбросом старта ±15 px, появлением и исчезновением масштабом; `onEnd` после последней иконки,
  `cancel()` — без `onEnd`.
- Связка с сумкой: удержание `Globals.bag.holdResource(key, id, count)` ставится до полёта, в `onEnd` —
  `releaseHold(key)`, чтобы счётчик в хедере вырос при прилёте
  ([bag-architecture.md](bag-architecture.md)).
- Если у имени нет подписчика, `onEnd` не вызывается и удержание не снимается (случай
  `HOME_AERODROME_AIRPLANE_SCHEMES`, [aerodrome-architecture.md](aerodrome-architecture.md)).

**Общий помощник награды — `RewardFlightUtils`**: удержание ресурсов награды, полёт и снятие удержания, привязка к жизни окна. API, жизненный цикл, таблица целей и места вызова — [reward-flight-utils-architecture.md](reward-flight-utils-architecture.md). Для паттерна важно: цель полёта добавляется только вместе с подписчиком, который вызывает `onEnd`; `HEADER_TOKENS` подписан, но иконок не рисует (сразу `onEnd`).

Чего нет для лутбокса: полёта произвольного `Layout` (карточки генерала с уменьшением) — `publish`
летает только спрайтом по `asset`; цели «призывы» нет (есть схемы поезда). Новая цель — новая
константа и подписчик в виджете-цели, по образцу `HeaderSilverCoinsBar.onFlyIcons`.

## Расхождения доков с кодом {#doc-drift}

Найдено при сверке, на 2026-10-27, ветка `koba/lootbox`:
- [items-presets-architecture.md](items-presets-architecture.md) описывает `ItemType.COLLECTION_ITEM`,
  `createImageCollectionItem` и `createRewardsCustomLayout`, вызов из `CollectionExperimentalTank`.
  В коде этого нет: `ItemType` — 0–5 (`RESOURCE`…`MILITARY_BASE_BOOST`), папки
  `profile/collections/` нет, вызовов `ItemsPresets` 11 в 6 файлах.

## Карта файлов {#files}

**Файлы прямого влияния**

- `src/presets/ItemsPresets.ts` — отрисовка иконок и списков наград, два свитча по `itemType`.
- `src/shared/animations/FlyIconsAnimation.ts` — полёт иконок: `play` (событие) и `publish` (анимация).
- `src/shared/paginators/AdvancedPaginator.ts` — общий пагинатор страниц по ответу сервера.
- `src/plain/Every.ts` — периодический вызов поверх `App.tick`.
- `src/views/home_screen/popups/military_base/MilitaryBaseSkipBuildingPopup.ts` — таймер с ценой ускорения.
- `src/views/home_screen/popups/military_base/MilitaryBaseMissingDollarsPopup.ts` — доплата золотом по ответу сервера.

**Файлы косвенного влияния**

- `src/plain/items/ItemType.ts` — типы предметов 0–5, по ним свитчи `ItemsPresets`.
- `src/utils/TimeUtils.ts` — зависимость: серверное время `nowMls()` и формат остатка.
- `src/plain/RewardUtils.ts` — зависимость: поиск ресурса в списке наград.
- `src/plain/GameEvents.ts` — событие `FLY_ICONS`.
- `src/plain/Globals.ts` — синхронизация `TimeUtils` с сервером и обновление каждый кадр.
- `src/types/interfaces.d.ts` — неиспользуемый `PaginatorConfig`.
- `src/views/home_screen/popups/bag/bag.d.ts` — `ItemJSON`.
- `src/views/home_screen/popups/campaign/campaign.d.ts` — `CampaignLevelRewardsJSON` с `any[]`.
- `src/shared/header/presets/HeaderSilverCoinsBar.ts`, `HeaderGoldenCoinsBar.ts`, `HeaderDollarsBar.ts`,
  `HeaderTokensBar.ts` — цели полёта иконок в хедере.
- `src/views/home_screen/HomeScreen.ts` — цель `TRAIN_TANK_SCHEMES`, выдача наград поезда, сетка ангара.
- `src/views/home_screen/HomeScreenAerodrome.ts` — цель `HOME_AERODROME_AIRPLANE_SCHEMES` (не подключён).
- `src/views/home_screen/HomeScreenQuest.ts` — выдача награды квеста с полётом.
- `src/views/home_screen/popups/idle/IdlePopup.ts` — удержание и полёт idle-наград.
- `src/views/home_screen/popups/shop/offers/GoldenCoinsOfferPopup.ts` — полёт золота после оффера.
- `src/views/home_screen/popups/military_base/MilitaryBaseBuyBuildingPopup.ts` — вызов доплаты после отказа.
- `src/views/home_screen/campaign/AirDrop.ts` — таймер ящика на `Every`; вызывает `FlyIconsAnimation`, `RewardUtils`.
- `src/views/home_screen/campaign/CampaignBattleGround.ts` — вызывает `FlyIconsAnimation`, `RewardUtils` (награды боя кампании).
- `src/views/home_screen/popups/military_base/MilitaryBasePopup.ts` — вызывает `FlyIconsAnimation`, `MilitaryBaseSkipBuildingPopup`.
- `src/views/home_screen/popups/military_base/MilitaryBaseResourcesPopup.ts` — вызывает `FlyIconsAnimation`, `MilitaryBaseSkipBuildingPopup`, `MilitaryBaseMissingDollarsPopup`.
- `src/views/home_screen/popups/military_base/MilitaryBaseStoragePopup.ts` — вызывает `FlyIconsAnimation`, `RewardUtils`, `MilitaryBaseSkipBuildingPopup`, `MilitaryBaseMissingDollarsPopup`.
- `src/views/home_screen/popups/military_base/MilitaryBaseAviationFactoryPopup.ts` — вызывает `MilitaryBaseMissingDollarsPopup`.
- `src/views/home_screen/popups/profile/achievements/AchievementLine.ts` — вызывает `FlyIconsAnimation`, `RewardUtils` (награда достижения).
- `src/views/home_screen/popups/train/TrainBuySchemesPopup.ts` — вызывает `FlyIconsAnimation`, `RewardUtils` (покупка схем).
- `src/views/home_screen/popups/profile/ProfileSection.ts` — вызывает `ItemsPresets` (карточки техники).
- `src/views/home_screen/popups/profile/codex/CodexTanksSection.ts` — вызывает `ItemsPresets` (карточки танков).
- `src/views/home_screen/popups/profile/codex/CodexAirplanesSection.ts` — вызывает `ItemsPresets` (карточки самолётов).
- `src/views/battlefield_screen/BattlefieldScreen.ts` — вызывает `ItemsPresets.createRewardsLayout` (награды боя).
- `src/views/home_screen/popups/rating/*Section.ts` (7 файлов) — пагинатор рейтингов.
- `src/views/home_screen/popups/banPanel/BanHistoryPanel.ts` — пагинатор истории банов.
