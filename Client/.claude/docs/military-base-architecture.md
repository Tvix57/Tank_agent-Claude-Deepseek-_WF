# Военная база — окна, здания, штаб, склад, авиазавод, бустеры (клиент)

> **auto-create** — документ составлен `client-analyst-military-base` по существующему коду, 2026-10-22.
> Запуском не проверялось. Код в рамках задачи не менялся.
> Серверная сторона: `MilitaryBasePage` и связанные классы в `/workspace/server`; здесь сервер упоминается
> только там, где без него непонятен контракт ([#contract](#contract)). Серверного документа нет.

ГДД: [`game-design/military-base-gdd.md`](game-design/military-base-gdd.md) (исходники —
`game-design/incoming/military-base-gdd.txt`, `military-base-fixes.txt`). Ссылки `#gdd-…` ниже ведут на
разделы ГДД: `#gdd-purpose`, `#gdd-access`, `#gdd-currencies`, `#gdd-base-map`, `#gdd-headquarters`, `#gdd-boosts`,
`#gdd-resource-buildings`, `#gdd-storage`, `#gdd-aviation-factory`, `#gdd-aerodrome-view`.

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

Военная база ([#gdd-purpose](game-design/military-base-gdd.md#gdd-purpose)) — способ получить самолёты. Цепочка игрока:
ресурсные здания добывают сырьё → оно вывозится на склад → склад отправляет сырьё на продажу «рейсом» за доллары →
доллары идут на запуск производства самолёта в авиазаводе → готовый самолёт забирается через окно `AirplaneGetPopup`
(другая область). Штаб выдаёт бустеры (улучшения зданий и транспорт), аэродром базы показывает самолёты игрока.
Клиент почти ничего не считает сам: состояние зданий приходит в сумке (`ItemType` 3/4/5) и в ответе `/ingame/militaryBase`,
деньги списывает сервер, клиент рисует состояние и шлёт команды ([#contract](#contract)).

Вход ([#gdd-access](game-design/military-base-gdd.md#gdd-access)): плашка «Военная база» на главном экране
(`HomeScreenMilitaryBase`, вместо старой плашки аэродрома) открывает `MilitaryBasePopup`. Из окна базы открываются
штаб, склад, авиазавод и аэродром базы; ресурсные здания (сетка 5×2 внизу) открывают окно здания или покупки.
Пока открыто окно базы, на кнопке «Главная» в `Footer` нет нажатого состояния ([#cls-external](#external)).
Ограничения по уровню кампании на клиенте нет ([#p-access](#p-access)).

Валюты ([#gdd-currencies](game-design/military-base-gdd.md#gdd-currencies)): ресурсы сумки — доллары
(`ItemId.RESOURCE_MILITARY_BASE_DOLLARS = 7`) и жетоны (`RESOURCE_MILITARY_BASE_TOKENS = 8`). В шапке на базе показаны
золото, серебро и доллары (`Header.SHOW_CURRENCY | SHOW_MILITARY_BASE_CURRENCY`); жетоны в шапке отключены
(`Header.ts:114` закомментировано), клиент их нигде не тратит и не начисляет. Золото (`RESOURCE_GOLDEN_COINS`) тратится на призыв
штаба, ускорение стройки и на «доплату» недостающих долларов.

Карта базы ([#gdd-base-map](game-design/military-base-gdd.md#gdd-base-map)): четыре здания на фоне (авиазавод, штаб,
аэродром, склад) и баблы над ними:

| Здание | Бабл / метка | Условие (где) |
|---|---|---|
| Штаб | значок лутбокса с числом | `headquarters.summons > 0` (`base/MilitaryBaseHeadquarters.bind`) |
| Склад | значок доллара | есть готовая прибыль `saleProfit > 0` и рейс не в пути (`MilitaryBaseState.hasProfit`, `base/MilitaryBaseStorage.checkProfit`) |
| Склад | значок «склад полон» | `used >= max` и нет прибыли (приоритет у доллара) |
| Склад | стрелка «можно прокачать» | доллары ≥ стоимость следующего уровня склада |
| Авиазавод | значок самолёта | есть слот с вышедшим временем и `airplane !== null` |
| Авиазавод | таймер | иначе — ближайший остаток времени среди слотов |
| Аэродром | сумма мощности | сумма `power` всех самолётов сумки |
| Ресурсное здание | рука «собрать» | см. [#cls-resource](#cls-resource) |
| Ресурсное здание | стрелка «можно прокачать/купить» | доллары ≥ стоимость покупки или следующего уровня добычи/транспорта |

Правила, которые видны только в коде и ещё не подтверждены ГДД, собраны в [#code-rules](#code-rules).

Границы области:
- входит: `src/views/home_screen/popups/military_base/**`, `HomeScreenMilitaryBase`, `MilitaryBaseBoostRouter`,
  `HeaderDollarsBar`, `HeaderTokensBar`, типы `MilitaryBase*JSON` в `bag.d.ts`, ключи `militaryBaseScreen.*` в `ru.json`;
- не входит: `AirplaneGetPopup` и слоты аэродрома (область «Аэродром», [aerodrome-architecture.md](aerodrome-architecture.md)),
  модель сумки `UserBag` ([bag-architecture.md](bag-architecture.md)), подписка плашки на бой
  ([air-battle-architecture.md](air-battle-architecture.md)), `HomeScreenAerodrome` (неподключённый остаток).

<a id="references"></a>
## 2. Референсы

Нет. Документ описывает существующий код.

<a id="patterns"></a>
## 3. Паттерны

- **Окно-`FlashLayout` + `GameFlash`**: у всех окон `publish(screen, config)` создаёт экземпляр, при необходимости грузит
  данные/ассеты и вызывает `FlashPublisher.publish`. Окна поверх окна базы идут с `setParallel(true)` и
  `screen.pushHeaderZIndex(...)`/`popHeaderZIndex()`; само окно базы и аэродром базы — нижний слой (`LOWER_FLASH_TAG`, `bgAlpha: -1`).
- **Состояние здания живёт в сумке** (`Globals.bag.getItem(ItemType.MILITARY_BASE_*, id)`), классы-«вьюшки» подписываются
  на `GameEvents.ITEM_NEW_OR_UPDATE/ITEM_DELETE` и перерисовываются в `bind(data)`. Состояние самой базы (`MilitaryBaseJSON`)
  лежит в синглтоне `MilitaryBaseState` и обновляется ответами команд.
- **Два клиентских события** (`GameEvents.MILITARY_BASE_UPDATED`, `MILITARY_BASE_BUILDING_UPDATED`) эмитит сам клиент после ответа
  команды или по таймеру; сервер их не шлёт. Подход «переизлучение» не используется
  ([server-push-events-subscription.md](server-push-events-subscription.md)): серверного push-события базы нет, обновление сумки
  идёт общим `g/ws/events/bag/update` ([bag-architecture.md](bag-architecture.md)).
- **Таймеры** — `App.tick.add(layout, { isValid, onTickSecond, onRequest })`; время — `TimeUtils.nowMls()` (серверное время на
  старте плюс локальное смещение), поэтому после ухода в фон таймеры пересчитываются правильно.
- **Очередь показа изменений** — `shared/PresentationFlow` в `MilitaryBaseResourcesPopup`: сохраняет актуальные данные сразу, а
  отрисовывает снимки после анимации полёта иконок ([#cls-resources-popup](#cls-resources-popup)).
- **Удержание ресурса на время анимации** — `Globals.bag.holdResource/releaseHold` при получении прибыли склада
  ([bag-architecture.md](bag-architecture.md)).
- **Кнопки и панели** — `Button.newButton`/`newSimpleButtonMode`, `Slice9`; свои кнопки `MilitaryBaseUtils.button`, а не `ButtonPresets`
  ([panels-buttons-presets-architecture.md](panels-buttons-presets-architecture.md)).
- **Золото вместо недостающих долларов** — один шаблон на пять команд ([#contract-gold](#contract-gold)).
- **Очередь попапов** ([popup-queue-pattern.md](popup-queue-pattern.md)) здесь не применяется: окна открываются параллельно.

<a id="class-list"></a>
## 4. Список классов

Задача — документирование, классы не создавались. Состав области (32 файла в папке, плашка, роутер, два бара шапки):

- Окно базы: `MilitaryBasePopup`, `MilitaryBaseBackground`, `base/MilitaryBaseHeadquarters`, `base/MilitaryBaseStorage`,
  `base/MilitaryBaseAviationFactory`, `base/MilitaryBaseAerodrome`.
- Состояние и утилиты: `MilitaryBaseState`, `MilitaryBaseData`, `MilitaryBaseUtils`, `MilitaryBaseNotification`, `militaryBase.d.ts`.
- Ресурсные здания: `MilitaryBaseResource`, `MilitaryBaseSelectableResource`, `MilitaryBaseResourcesPopup`,
  `MilitaryBaseBuyBuildingPopup`, `MilitaryBaseSkipBuildingPopup`, `MilitaryBaseMissingDollarsPopup`.
- Склад: `MilitaryBaseStoragePopup`, `MilitaryBaseStorageResource`, `MilitaryBaseSellResourcePopup`.
- Штаб: `MilitaryBaseHeadquartersPopup`, `MilitaryBaseHeadquartersSummonPopup`, `MilitaryBaseHeadquartersInfoPopup`.
- Бустеры: `MilitaryBaseBoostRouter` (`src/plain/military_base/`), `MilitaryBaseBoost`, `MilitaryBaseBoostSmall`,
  `MilitaryBaseBoostMedium`, `MilitaryBaseBoostPopup`.
- Авиазавод: `MilitaryBaseAviationFactoryPopup`, `MilitaryBaseAviationFactorySlot`, `MilitaryBaseAviationFactoryInfoPopup`,
  `MilitaryBaseSkipAviationFactoryPopup` (недостижим).
- Аэродром базы: `MilitaryBaseAerodromePopup`.
- Главный экран и шапка: `HomeScreenMilitaryBase`, `HeaderDollarsBar`, `HeaderTokensBar`.
- Точки вне папки: `HomeScreen`, `Header`, `HeaderPresets`, `Footer`, `Notifications`, `GameEvents`, `ItemType`, `ItemId`, `bag.d.ts`.

<a id="anchors"></a>
## 5. Навигация (якоря)

Классы: [`#cls-home-plate`](#cls-home-plate), [`#cls-popup`](#cls-popup), [`#cls-state`](#cls-state), [`#cls-map`](#cls-map),
[`#cls-resource`](#cls-resource), [`#cls-resources-popup`](#cls-resources-popup), [`#cls-buy-skip`](#cls-buy-skip),
[`#cls-storage`](#cls-storage), [`#cls-hq`](#cls-hq), [`#cls-boost`](#cls-boost), [`#cls-factory`](#cls-factory),
[`#cls-aerodrome`](#cls-aerodrome), [`#cls-header`](#cls-header), [`#types`](#types), [`#external`](#external),
[`#contract`](#contract), [`#gdd-mapping`](#gdd-mapping), [`#code-rules`](#code-rules).

Проблемы: [`#p-access`](#p-access), [`#p-skip-factory`](#p-skip-factory), [`#p-boost-plus`](#p-boost-plus),
[`#p-summon-close`](#p-summon-close), [`#p-fixes`](#p-fixes), [`#p-hardcode`](#p-hardcode), [`#p-booster-count`](#p-booster-count),
[`#p-silent-errors`](#p-silent-errors), [`#p-double-press`](#p-double-press), [`#p-nan`](#p-nan), [`#p-slot-delete`](#p-slot-delete),
[`#p-aerodrome-crash`](#p-aerodrome-crash), [`#p-take-profit`](#p-take-profit), [`#p-state-order`](#p-state-order),
[`#p-balance-cache`](#p-balance-cache), [`#p-tick-loop`](#p-tick-loop), [`#p-plate-timer`](#p-plate-timer),
[`#p-two-tabs`](#p-two-tabs), [`#p-duplicates`](#p-duplicates), [`#p-dead-code`](#p-dead-code), [`#p-misc`](#p-misc).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс / группа | Раздел | Правило ГДД |
|---|---|---|
| `HomeScreenMilitaryBase` | [#cls-home-plate](#cls-home-plate) | [#gdd-access](game-design/military-base-gdd.md#gdd-access) |
| `MilitaryBasePopup` | [#cls-popup](#cls-popup) | [#gdd-base-map](game-design/military-base-gdd.md#gdd-base-map) |
| `MilitaryBaseState`, `MilitaryBaseData`, `MilitaryBaseUtils`, `MilitaryBaseNotification` | [#cls-state](#cls-state) | несколько |
| `MilitaryBaseBackground`, `base/*` | [#cls-map](#cls-map) | [#gdd-base-map](game-design/military-base-gdd.md#gdd-base-map) |
| `MilitaryBaseResource`, `MilitaryBaseSelectableResource` | [#cls-resource](#cls-resource) | [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings) |
| `MilitaryBaseResourcesPopup` | [#cls-resources-popup](#cls-resources-popup) | [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings) |
| `BuyBuilding`, `SkipBuilding`, `MissingDollars` | [#cls-buy-skip](#cls-buy-skip) | [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings), [#gdd-currencies](game-design/military-base-gdd.md#gdd-currencies) |
| `StoragePopup`, `StorageResource`, `SellResourcePopup` | [#cls-storage](#cls-storage) | [#gdd-storage](game-design/military-base-gdd.md#gdd-storage) |
| `HeadquartersPopup`, `SummonPopup`, `InfoPopup` | [#cls-hq](#cls-hq) | [#gdd-headquarters](game-design/military-base-gdd.md#gdd-headquarters) |
| `BoostRouter`, `Boost`, `BoostSmall`, `BoostMedium`, `BoostPopup` | [#cls-boost](#cls-boost) | [#gdd-boosts](game-design/military-base-gdd.md#gdd-boosts) |
| `AviationFactoryPopup`, `AviationFactorySlot`, `AviationFactoryInfoPopup`, `SkipAviationFactoryPopup` | [#cls-factory](#cls-factory) | [#gdd-aviation-factory](game-design/military-base-gdd.md#gdd-aviation-factory) |
| `AerodromePopup` | [#cls-aerodrome](#cls-aerodrome) | [#gdd-aerodrome-view](game-design/military-base-gdd.md#gdd-aerodrome-view) |
| `HeaderDollarsBar`, `HeaderTokensBar` | [#cls-header](#cls-header) | [#gdd-currencies](game-design/military-base-gdd.md#gdd-currencies) |

<a id="classes"></a>
## 7. Классы и методы

Номера строк даны на 2026-10-22. Обработчики-прослойки вида `onMilitaryBaseUpdate(data) { this.bind(); }` перечислены одной строкой.

<a id="cls-home-plate"></a>
### `HomeScreenMilitaryBase` (`src/views/home_screen/`)

Плашка 113×94 в `HomeScreen.UIAerodrome` (`HomeScreen.ts:470`, справа внизу). ГДД: [#gdd-access](game-design/military-base-gdd.md#gdd-access).

- `UIMain` — картинка `atlas/home_screen/support/military_base.png`, рамка, затемнённая подпись «ВОЕННАЯ БАЗА» (y=35), слои двух
  самолётов `al0` (готовится к взлёту) и `al1` (взлетает), текст таймера `time` (y=30, скрыт), бабл `AttentionAnimation`.
  Клик → `MilitaryBasePopup.publish(screen, {})`. Самолёты добавлены после подписи, то есть рисуются над плашкой с надписью.
- `handleMilitaryBaseNotifications` — бабл виден, если `Notifications.getNotificationCount(Notifications.MILITARY_BASE) !== 0`
  (число приходит с сервера в `Globals.account.notifications.militaryBase`, режется до 99). Условие бабла считает сервер.
- `onAirplanePrepareTakeoff(event)` — только для своего игрока (`fighter.getUid() === Globals.account.id`): запоминает
  `takeoffTime`, показывает таймер «До взлёта: …» с подъёмом на y=18 (выше подписи), строит самолёт и тень (`atlas/airplanes/big/…`)
  с маской и анимацией въезда; сбрасывает `timerTween.target.elapsedTime`.
- `onAirplaneTakeoff(event)` — звук, скрывает таймер и `al0`, улетающая анимация `al1` влево.
- `onBattleBegin`/`onBattleEnded` — включают/выключают счёт таймера, на конец боя гасят текст и оба самолёта.
- Таймер — tween каждые 1000 мс, который вычитает 1000 из `takeoffTime`, а не считает по часам ([#p-plate-timer](#p-plate-timer)).
- `onDestroy` — снимает подписки на уведомления и четыре события боя (`GameEvents.BATTLE_*`).

<a id="cls-popup"></a>
### `MilitaryBasePopup`

Главное окно (нижний слой, на весь экран, `FlashLayout("MilitaryBasePopup")`). ГДД: [#gdd-base-map](game-design/military-base-gdd.md#gdd-base-map),
[#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings).

- `publish` — цепочка `requestData` → `loadAssets` → `FlashPublisher.publish`. Без `catch`: при ошибке запроса окно не откроется и
  ничего не скажет ([#p-silent-errors](#p-silent-errors)). Повторное нажатие на плашку запустит вторую цепочку ([#p-double-press](#p-double-press)).
- `requestData` — `/ingame/militaryBase` (кладёт в `MilitaryBaseState`) и один раз за сессию `/ingame/militaryBase/balance`
  (в статическое поле `MilitaryBaseData.balance`, [#p-balance-cache](#p-balance-cache)).
- `loadAssets` — пакеты `MilitaryBaseScreen`, `MilitaryBaseBackground`.
- `onCreate` — строит UI, включает в шапке `SHOW_CURRENCY | SHOW_MILITARY_BASE_CURRENCY`, подписывается на `MILITARY_BASE_UPDATED`
  (→ `bind`), `BAG_UPDATE` и `MILITARY_BASE_BUILDING_UPDATED` (→ `updateCollectNotifiers`), ставит тик.
- `onDestroy` — снимает подписки и жёстко возвращает в шапке только `SHOW_CURRENCY` (предыдущее состояние шапки не восстанавливается).
- `UIMain` — фон-карта 377 px (`MilitaryBaseBackground`, четыре здания `base/*` с координатами x/y), нижняя панель «ДОБЫЧА РЕСУРСОВ»
  с сеткой из десяти `MilitaryBaseResource`, тени сверху и снизу, кнопка «ВЕРНУТЬСЯ В БОЙ» (закрывает окно), плашка «Доход базы N / час»
  (`dollarsPerHour`), слой указателя туториала.
- `bind` — обновляет число дохода из `MilitaryBaseState.getMilitaryBaseData().dollarsPerHour` и пересчитывает баблы сбора.
- `updateCollectNotifiers` — правило «рука сбора»: если среди построенных зданий есть то, где `canCollectResource`, то руку показывают на
  каждом построенном здании с `productionResources > 0` и `storageResources < storageCapacity`. ГДД: [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings).
- `shouldRequestTick` / `getProductionSignature` / `onTick` — раз в секунду проверяет, не пора ли запросить `/ingame/militaryBase/tick`:
  сменилась подпись скорости добычи по зданиям (`id:amount:interval`, у строящихся `id:0`), вышло время `headquarters.summonsTime`,
  или у какого-то здания `productionTime <= now`. После ответа обновляет `MilitaryBaseState` и эмитит `MILITARY_BASE_UPDATED`
  ([#p-tick-loop](#p-tick-loop)).
- `BtnCollectResource` — `/ingame/militaryBase/collectResource {buildingId: 0}` (собрать со всех); при OK запускает `playResourcesAnimation`
  (полёт иконок `resources/<id>.png` со зданий на склад, `min(3, floor(10/число зданий))` штук от каждого).
- Кнопки зданий: авиазавод → `MilitaryBaseAviationFactoryPopup`, штаб → `MilitaryBaseHeadquartersPopup`, аэродром →
  `MilitaryBaseAerodromePopup`, склад → `MilitaryBaseStoragePopup`; ресурсное здание: открыто → `MilitaryBaseResourcesPopup`,
  не куплено → `MilitaryBaseBuyBuildingPopup`, строится → `MilitaryBaseSkipBuildingPopup`.
- `onPressBoost(boostId)` — ветка `boostId === 0 → штаб` недостижима (id бустеров начинаются с 1), всегда открывается
  `MilitaryBaseBoostPopup` ([#p-boost-plus](#p-boost-plus)).
- `processTutorial`/`hideTutorial` — при `tutorialProgress === 0` ставит палец на здание Уголь (+45 px), при `-1` или других значениях прячет.
  Покупка Угля прячет указатель и возвращает его в `onExit` окна покупки.

<a id="cls-state"></a>
### `MilitaryBaseState`, `MilitaryBaseData`, `MilitaryBaseUtils`, `MilitaryBaseNotification`

- `MilitaryBaseState` (синглтон) — `get/setMilitaryBaseData`, `getNotification` (пустой класс, [#p-dead-code](#p-dead-code)). Производные от сумки:
  `getActiveBuildings` (число построенных; id 1..10), `getMaxCapacity` (сумма `storageCapacity.current.amount` построенных),
  `getUsedCapacity` (сумма `storageResources` всех, включая строящиеся), `hasProfit` (есть здание с `saleProfit > 0` без идущего рейса),
  `hasAirplane` (есть слот с вышедшим временем и `airplane !== null`). ГДД: [#gdd-storage](game-design/military-base-gdd.md#gdd-storage),
  [#gdd-aviation-factory](game-design/military-base-gdd.md#gdd-aviation-factory). Ряд «построено» повторён в каждом методе ([#p-duplicates](#p-duplicates)).
- `MilitaryBaseData` — статический кэш баланса (`balance`) и геттеры: `getBuildingBuyData(id)` (`cost`, `time`), `getBuildingSellData(id)`
  (`price` за единицу), `getBuildingUpgradeData(id, level)` (параметр `id` игнорируется — одна таблица на добычу и транспорт),
  `getStorageData(level)`, `getAviationFactoryData(level)` (`needExp`), `getSkipBuildingCost` (0 для Угля, иначе 100 золота — константа в коде),
  `getSkipAviationFactoryCost` (всегда 0), `getAviationFactorySlotData` (не используется).
- `MilitaryBaseUtils` — `button` (кнопка: orange/blue/disable), `buttonStatus(layout, status)` (-1 полностью отключена, 0 серая но нажимаемая,
  1 оранжевая, 2 синяя; `setInteractive(status >= 0)`, поэтому серая кнопка всё равно нажимается — [#p-silent-errors](#p-silent-errors)),
  `dollars` (иконка + число, красное при нехватке), `compareBoost`/`isBoostBetter` (сравнение по `bonus.amount`, `null` всегда хуже),
  `getViewLevel` (1 + (productionLevel-1) + (productionCapacityLevel-1)), `canCollectResource` (правило «можно собрать»: `productionCapacity>0`,
  на складе есть место и `productionResources >= 10%` от `productionCapacity.current.amount`), `getBonusSprite`/`getBonusText`
  (тип бонуса → иконка и текст «+N», для `aviationFactory` — «-время»), `roundSmart`, `dotAnimation`, `UITutorial`.
  ГДД: [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings), [#gdd-boosts](game-design/military-base-gdd.md#gdd-boosts).
- `MilitaryBaseNotification` — пустой класс (5 строк).

<a id="cls-map"></a>
### `MilitaryBaseBackground` и здания карты `base/*`

ГДД: [#gdd-base-map](game-design/military-base-gdd.md#gdd-base-map).

- `MilitaryBaseBackground` — фон (`raw/backgrounds/military_base.png`, 517×516) и декоративные анимации: поезд, танк, самолёт, пыль и дым
  (`playNextAnimation` по кругу, `spawnDust/spawnFactoryPuff/spawnTrainPuff`). Логики игры нет. Боковые тени (±250) и верхняя/нижняя в
  `Background.ts:59-61`, ещё две в `MilitaryBasePopup.ts:296-297`.
- `base/MilitaryBaseHeadquarters` — подпись «ШТАБ», бабл с числом бесплатных призывов (`summons > 0`), пульсирует; подписка на
  `MILITARY_BASE_UPDATED`. Бабл без цифры («есть доллары, нет бесплатных») из ГДД не реализован.
- `base/MilitaryBaseStorage` — подпись, уровень склада, строка «used / max», бабл «доллар»/«склад полон» и стрелка прокачки. Подписки:
  `ITEM_*` (доллары, здания), оба события базы. Тикер раз в секунду `checkProfit` включает бабл доллара по времени выхода рейса.
- `base/MilitaryBaseAviationFactory` — подпись, уровень, бабл самолёта, таймер ближайшего слота. Тикер раз в секунду: `checkAirplanes`,
  `checkTime`. Подписки: `ITEM_*`, оба события.
- `base/MilitaryBaseAerodrome` — подпись и сумма `power` всех самолётов сумки (`Globals.bag.getAirplanes()`), подписка на `BAG_UPDATE`.
  Бабла нет (код закомментирован).

<a id="cls-resource"></a>
### `MilitaryBaseResource` и `MilitaryBaseSelectableResource`

ГДД: [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings).

- `MilitaryBaseResource` (77×114, по одному на `id` 1..10) — три взаимоисключающих состояния через `entity(...).setEnabled`: `inactive`
  (в сумке нет здания: затемнение, значок покупки, цена `buildingBuyData[id].cost`), `building` (`buildingTime > now`: молот, таймер,
  кнопка «Ускорить»), `active` (название, уровень, четыре панели: добыча, лимит, два слота бустера). `bind(data)` выбирает состояние,
  считает «стрелку прокачки» (доллары ≥ стоимость покупки или следующего уровня добычи/транспорта) и заполняет параметры.
- Тик здания: пока есть `buildingTime`, раз в секунду обновляет таймер; когда `left <= 0`, эмитит `MILITARY_BASE_BUILDING_UPDATED`
  и перерисовывается (завершение стройки обрабатывается только здесь, пока открыт экран базы).
- `bindBoostBonus` — под бустером: иконка и «+N» (`getBonusText`); если бустера нет, тот же вид серым с `amount: 0` (текст «+0»).
- `UIBoost` → `MilitaryBaseBoostSmall`, клик → `onPressBoost(id)`.
- Подписки: `ITEM_NEW_OR_UPDATE/DELETE` (доллары, нужные два бустера здания, само здание), `MILITARY_BASE_BUILDING_UPDATED`.
  `ITEM_DELETE` здания → `bind(null)`.
- `setCollectNotifierVisible` — рука сбора; скрывает стрелку прокачки, пока рука видна. Рука кликабельна → `onPressCollect` (сбор со всех).
- `MilitaryBaseSelectableResource` (50×50) — иконка в нижней полосе `MilitaryBaseResourcesPopup`; один из пяти бабликов: купить, ускорить,
  собрать, прокачать (условие прокачки скопировано из `MilitaryBaseResource`, [#p-duplicates](#p-duplicates)), `select(bool)` — рамка.

<a id="cls-resources-popup"></a>
### `MilitaryBaseResourcesPopup`

Окно ресурсного здания (310 px): склад здания сверху, ниже два блока улучшения (скорость добычи, объём транспорта/лимит) с бустерами.
ГДД: [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings).

- `render(data)` — вся отрисовка: имя, уровень, прогресс склада здания (красный при полном), счётчик «Добыто», кнопка «Отправить на склад»/«Освободить склад»,
  таймер добычи с прогрессом (`updateProductionProgress`, надпись «Добыча приостановлена» при полном лимите), текущее/следующее значение, кнопки улучшения
  (серые при нехватке долларов, но нажимаемые), «Макс. уровень», блоки бустеров.
- `bind(data, reset?)` + `PresentationFlow`: новые данные принимаются сразу, а `render` вызывается после анимации. Переходы:
  `production` (выросла добыча — иконка летит из блока добычи в лимит), `collect` (вырос склад — летит со счётчика в склад), `productionAndCollect`.
  Пока идёт анимация, кнопка сбора отключена (`setCollectBusy`).
- `onInventoryUpdate` — реагирует на доллары, два бустера здания, само здание. При росте `storageResources` сбрасывает `collectAwaitingBagUpdate`.
- `BtnStorageAction` — если склад здания полон, закрывает окно и открывает `MilitaryBaseStoragePopup`; иначе `BtnCollectResource`
  (`collectResource {buildingId}`), защищён флагами `collectRequestPending`/`collectAwaitingBagUpdate`/`presentation.isBusy`.
- `BtnUpgradeProduction` / `BtnUpgradeProductionCapacity` → `/ingame/militaryBase/upgradeProduction`, `/upgradeProductionCapacity`
  `{buildingId}`; при OK ничего не делают (результат придёт обновлением сумки), при нехватке — `MilitaryBaseMissingDollarsPopup`
  ([#contract-gold](#contract-gold)).
- `UISelectableResources` — нижняя полоса переключения между зданиями. Показывает только купленные здания (`getItem(..) === null → continue`),
  поэтому ветки «не куплено → окно покупки» в обработчике клика недостижимы; клик по строящемуся — окно ускорения; клик по другому — `config.id = i`, `bind(.., true)`.
- `UIBoost` — `MilitaryBaseBoostMedium`; если бустера нет, под ним кнопка «Подробнее» → `MilitaryBaseBoostPopup`; если есть — бонус под иконкой.
- `processTutorial` — шаг 1: палец на кнопку «Отправить на склад», пока `productionResources > 0`.

<a id="cls-buy-skip"></a>
### Покупка, ускорение, доплата золотом

ГДД: [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings), [#gdd-currencies](game-design/military-base-gdd.md#gdd-currencies).

- `MilitaryBaseBuyBuildingPopup` — карточка покупки: имя, цена и время из баланса, кнопка «КУПИТЬ» (всегда зелёная, проверка долларов закомментирована —
  решает сервер). `BtnBuyBuilding` → `/ingame/militaryBase/buyBuilding {buildingId}`; не OK и есть `missingDollars` → доплата золотом; OK → `onBuyBuildingSuccess`
  (сохраняет `tutorial`, эмитит `MILITARY_BASE_UPDATED` и `MILITARY_BASE_BUILDING_UPDATED`, закрывает окно). Внутреннее имя флеша скопировано
  от окна ускорения: `"MilitaryBaseSkipBuildingPopup"` ([#p-misc](#p-misc)).
- `MilitaryBaseSkipBuildingPopup` — «УСКОРЕНИЕ ПОСТРОЙКИ»: таймер, цена в золоте (`getSkipBuildingCost`: 0 для Угля, иначе 100), `BtnSkip` →
  `/ingame/militaryBase/skipBuilding {buildingId}` → эмит `MILITARY_BASE_BUILDING_UPDATED`, закрывает окно. Тик закрывает окно, когда время вышло или
  у здания пропал `buildingTime`.
- `MilitaryBaseMissingDollarsPopup` — «Купить доллары»: «Не хватает N долларов, доплатить M золота». Кнопка зелёная, если золота хватает; `BtnBuy` повторяет исходный
  запрос (`handlerUrl` + `payload`) с `useGoldenCoins: true`; при OK закрывается и вызывает `onSuccess(response)`.
- `MilitaryBaseSkipAviationFactoryPopup` — близнец окна ускорения здания для слота завода (`/ingame/militaryBase/skipFactory {slotId}`, цена 0 долларов).
  Недостижим ([#p-skip-factory](#p-skip-factory)).

<a id="cls-storage"></a>
### Склад: `MilitaryBaseStoragePopup`, `MilitaryBaseStorageResource`, `MilitaryBaseSellResourcePopup`

ГДД: [#gdd-storage](game-design/military-base-gdd.md#gdd-storage).

- `MilitaryBaseStoragePopup` — окно склада: общая заполненность (`used/max` через `MilitaryBaseState`), прогресс, блок «уровень → следующий» с прибавкой
  `(next.capacity - current.capacity) * число построенных зданий`, кнопка «Повысить» с ценой; на максимуме — «Максимальный уровень». Десять строк
  `MilitaryBaseStorageResource`. Шаг туториала 2: палец на «Отправить на продажу» первой строки с товаром.
  - `BtnUpgrade` → `/ingame/militaryBase/upgradeStorage` `{}`; доплата золотом по шаблону [#contract-gold](#contract-gold); OK → `setMilitaryBaseData` + `MILITARY_BASE_UPDATED`.
  - `BtnTakeProfit(id)` → `/ingame/militaryBase/takeProfit {buildingId}` → из `rewards` берёт доллары, `holdResource` на время полёта 5 иконок в шапку
    (`FlyIconsAnimation.HEADER_DOLLARS`) и `releaseHold` в конце ([#p-take-profit](#p-take-profit)).
- `MilitaryBaseStorageResource` (строка 330×44) — состояния: `inactive` (не куплено или строится, цена), `active` с тремя под-состояниями по рейсу:
  `sell` (нет рейса и нет прибыли — кнопка «Отправить на продажу»), `process` (рейс идёт, `saleTime > now`, таймер), `take` (прибыль `saleProfit > 0`,
  кнопка «Получить прибыль»). Значок «склад здания полон». Два бустера (хранилище и транспорт) и бонусы; анимация «бегущего света» на панели транспорта,
  пока рейс идёт и транспорт-бустер есть. Тик по `saleTime`: когда рейс закончился, эмитит `MILITARY_BASE_BUILDING_UPDATED` с данными из сумки.
  `getTutorialTarget` — первая активная строка с `storageResources > 0`.
- `MilitaryBaseSellResourcePopup` — «ОТПРАВКА ГРУЗА»: товар и цена за единицу (`buildingSellData[id].price`), блок транспорта (бустер и «N/вместимость»),
  ползунок `Slider`, кнопки `−`/`+`, итоговая прибыль и время в пути.
  - `bind` — максимум для отправки `selectedMaxValue = min(storageResources, transportCapacity.current.amount)`, начальное значение равно максимуму; шаг `−/+`:
    `max(1, roundSmart(5% от максимума))`. Ползунок настроен на диапазон `0..storageResources`, а не `0..selectedMaxValue`
    ([#p-misc](#p-misc)).
  - `updateSelectedValue` — прибыль `price * amount`; кнопка полностью отключена при прибыли ≤ 0.
  - `getSaleDuration` — только для показа: вместимость заполнена → 10 мин; иначе `270 + 30·ceil(доля·10)` секунд в пределах 300..570 ([#p-hardcode](#p-hardcode)).
  - `BtnSellResource` → `/ingame/militaryBase/sellResource {buildingId, amount}`; при OK сохраняет `tutorial` и закрывает окно.

<a id="cls-hq"></a>
### Штаб: `MilitaryBaseHeadquartersPopup`, `…SummonPopup`, `…InfoPopup`

ГДД: [#gdd-headquarters](game-design/military-base-gdd.md#gdd-headquarters).

- `MilitaryBaseHeadquartersPopup` — окно штаба: описание, цена призыва, кнопка «ВЫЗВАТЬ СНАБЖЕНИЕ», таймер «Бесплатное снабжение через».
  - `bind` — призыв стоит **250 золота** (константа в коде, `RESOURCE_GOLDEN_COINS`); если есть бесплатные (`summons > 0`), вместо цены показан текст «Бесплатное снабжение N»;
    кнопка серая при `gold < 250 && summons === 0`, но остаётся нажимаемой; таймер виден, пока `summonsTime - now >= 0`. Пересчитывается при изменении золота и долларов.
  - `BtnSummon` → `/ingame/militaryBase/summon {}` → `{militaryBase, boost, current}`; обновляет состояние, прячет нижний блок, открывает `SummonPopup`;
    по закрытию того окна нижний блок возвращается. Выбора «1 или 10» в клиенте нет.
  - Кнопка «i» → `MilitaryBaseHeadquartersInfoPopup`. Ассеты: пакет `MilitaryBaseHQ`.
- `MilitaryBaseHeadquartersSummonPopup` — результат призыва: «ПОЛУЧЕН НОВЫЙ БУСТЕР», анимации появления, новый бустер и (если есть) текущий, стрелка «ЛУЧШЕ/ХУЖЕ»
  с разницей бонуса (`getBonusDiff` — только при одинаковом `bonus.type`). `better = isBoostBetter(new, current)`: если лучше — доступна только кнопка «ВЫБРАТЬ»
  (`/summonAccept`); если нет — только «ПРОДАТЬ» (`/summonRefuse`) с ценой 125 серебра (число зашито в разметку, [#p-hardcode](#p-hardcode)). Закрытие по фону не вызывает ни одну команду
  ([#p-summon-close](#p-summon-close)).
- `MilitaryBaseHeadquartersInfoPopup` — «ШАНСЫ ПРИЗЫВА»: `/ingame/militaryBase/headquartersInfo`; два списка `rank[]` и `stars[]` с `chance` (делитель 100000, `NumberUtils.intToPercent`).

<a id="cls-boost"></a>
### Бустеры

ГДД: [#gdd-boosts](game-design/military-base-gdd.md#gdd-boosts).

- `MilitaryBaseBoostRouter` (`src/plain/military_base/`) — статические таблицы `ItemId`: здание → бустер добычи (`*_PRODUCTION`), вместимости/логистики (`*_LOGISTICS`),
  хранилища (`*_STORAGE`), транспорта (`*_TRANSPORT`), слот завода (1..10) → бустер слота (41..50). `VARIANT_GROUPS` — десять бустеров транспорта имеют варианты картинки и имени;
  `imagePath/imagePackage/nameKey(id, variant)` строят путь атласа (`military_base_boost/<id>/m.png` или `military_base_boost_variant/transport/<variant>/m.png`), имя пакета
  (`Boost_<id>`/`Boost_transport_<variant>`) и ключ перевода. `isAviationFactorySlotBoost`. Таблиц для id 51 и 52 нет ([#p-booster-count](#p-booster-count)).
- Данные бустера в сумке: `MilitaryBaseBoostJSON {rank, stars{rank,count}, variant, bonus{type,amount}}`; `bonus.type` — `production`, `logistics`, `storage`, `transport`, `aviationFactory`.
  Качество (`rank`) красит фон (`boost_bg/<size>/<rank>.png`) и название, звёзды рисуются по `stars.count` цветом `stars.rank`.
- `MilitaryBaseBoost` (106×130, «полная карточка») — фон по качеству, иконка (async-спрайт), название, бонус, 5 звёзд. Пустой бустер: серый фон, иконка типа
  (логистика/добыча или общий вид), плашка «ПУСТО» (флаг `FLAG_SHOW_EMPTY_TEXT`) или кнопка «Подробнее» (`FLAG_SHOW_EMPTY_BUTTON`, склад), бонус скрыт. Знака «?» и «0%» нет.
- `MilitaryBaseBoostSmall` (35×35) и `MilitaryBaseBoostMedium` (55×55) — те же поля в двух размерах (отличаются только размерами и ассетами; проверено `diff`). Пустой бустер:
  пустой слот, серая иконка типа бонуса, значок «+» (`add_booster_btn`, скрыт при `hidePlus`).
- `MilitaryBaseBoostPopup` — полноэкранная карточка бустера: название качества, `MilitaryBaseBoost`, «НАЗНАЧЕНИЕ» (`boostTarget.<id>`, `boostInfo.<id>`), подсказка «Перейдите в штаб, чтобы получить/улучшить бустер»
  и кнопка «Перейти в штаб» → закрывает карточку и открывает `MilitaryBaseHeadquartersPopup`. Точка входа для любого нажатия на бустер или «+».

<a id="cls-factory"></a>
### Авиазавод

ГДД: [#gdd-aviation-factory](game-design/military-base-gdd.md#gdd-aviation-factory).

- `MilitaryBaseAviationFactoryPopup` — окно завода: шапка с уровнем и прогрессом (`aviationFactory.exp / aviationFactoryData[level+1].needExp`, на максимуме «Макс. уровень»), кнопка «i», десять
  `MilitaryBaseAviationFactorySlot`.
  - `getSortedSlotIds` — порядок слотов: сначала с лучшим бонусом бустера слота (`compareBoost`), затем по номеру; пересортировка при каждой перестройке.
  - `updateSlots` — заменяет весь список слотов; вызывается при `MILITARY_BASE_UPDATED` и при изменении бустеров слотов. Слоты сами следят за своим предметом.
  - `BtnStartProduction(id)` → `/ingame/militaryBase/runFactory {slotId}`; нехватка → доплата золотом; OK → состояние и `MILITARY_BASE_UPDATED`.
  - `BtnGetAirplane(id)` → `/ingame/militaryBase/checkFactory {slotId}` → `{receivedAirplane, replaceableAirplane}` → `AirplaneGetPopup` ([aerodrome-architecture.md](aerodrome-architecture.md)).
    `onAccept` → `/acceptAirplane`, `onRefuse` → `/refuseAirplane` (оба возвращают `militaryBase`); `onClose` пустой.
  - Автозаполнения слотов в клиенте нет.
- `MilitaryBaseAviationFactorySlot` (330×44) — состояния: `inactive` (нет предмета слота, либо время вышло и самолёта нет: «Время сборки», «Цена», кнопка «Запустить производство»,
  кнопка полупрозрачная при нехватке долларов, но нажимаемая), `make` (время не вышло: шестерёнки, «Самолёт в производстве…» с точками, таймер), `ready` (время вышло и `airplane`: картинка,
  название, мощность, зелёная кнопка «Нажмите, чтобы забрать» с галочкой). Время запуска = `slot.productionDuration` либо `aviationFactory.productionDurations[slotId]`; цена одна для всех слотов —
  `aviationFactory.productionCost`. Справа бустер слота (`BoostSmall`, без «+»). Кнопка «ускорить» в состоянии `make` закомментирована.
- `MilitaryBaseAviationFactoryInfoPopup` — «ШАНСЫ ПРИЗЫВА» завода: `/ingame/militaryBase/aviationFactoryInfo` → `{level, rank[], stars[], importantRankLevel?, importantStarsLevel?}`;
  показывает строки с `current > 0` в процентах (делитель 1 000 000) и строки «Новое на N ур.» для важных уровней; прокрутка при высоте > 385.

<a id="cls-aerodrome"></a>
### `MilitaryBaseAerodromePopup`

Аэродром базы (нижний слой). ГДД: [#gdd-aerodrome-view](game-design/military-base-gdd.md#gdd-aerodrome-view). Слоты и порядок взлёта — [aerodrome-architecture.md](aerodrome-architecture.md).

- `publish` — `/ingame/aerodrome {}` → `{aerodrome: {airplanes: [{airplaneUid|null} × 8]}}`, пакет `AerodromeScreen`.
- `UIBase` — фон и 8 стоянок с индивидуальными размерами/позициями; по каждому самолёту `Globals.bag.getAirplane(uid)` и информация (флаг, тип, имя, ранг, звёзды, мощность);
  клик → `AirplaneInfoPopup`. `UIFooter` — сетка из 8 карточек и блок завода.
- Блок завода (кнопка перехода): три взаимоисключающих состояния, выбираются тикером раз в секунду (`checkAirplanes` → бабл самолёта; иначе `checkTime` → таймер ближайшего слота; иначе `checkIdle` →
  текст «Конвейер стоит! Назначьте производство»). Кнопка «ПЕРЕЙТИ НА ЗАВОД» закрывает аэродром и открывает `MilitaryBaseAviationFactoryPopup`. Кнопка назад — «ВЕРНУТЬСЯ НА БАЗУ».
- Падает, если `uid` есть, а самолёта в сумке нет ([#p-aerodrome-crash](#p-aerodrome-crash)).

<a id="cls-header"></a>
### `HeaderDollarsBar`, `HeaderTokensBar`

ГДД: [#gdd-currencies](game-design/military-base-gdd.md#gdd-currencies).

- Оба — пресеты шапки (`IHeaderPreset`), создаются в `Header` (`Header.ts:68-69`, `HeaderPresets.dollarsBar/tokensBar`), по умолчанию выключены; включаются `Header.showCurrency(flag)`.
  Показывают `Globals.bag.getResourceCount(...)` и подписаны на `ITEM_NEW_OR_UPDATE/ITEM_DELETE/FLY_ICONS`; значение меняется анимацией счёта (`animationValue`, ≥1000 без анимации у долларов).
- `HeaderDollarsBar.onFlyIcons` — принимает только `FlyIconsAnimation.HEADER_DOLLARS`, запускает полёт иконок доллара к себе и вызывает `data.onEnd()` по окончании.
  Источник — `MilitaryBaseStoragePopup.BtnTakeProfit`. `HeaderTokensBar.onFlyIcons` — сразу вызывает `onEnd`.
- В режиме разработчика (`Globals.isDevTools()`) клик по иконке шлёт `/ingame/devTools/userDollars` / `/userTokens`.
- `HeaderTokensBar` в шапке не включается ни при каком флаге ([#p-dead-code](#p-dead-code)).

<a id="types"></a>
### Типы

- `militaryBase.d.ts`: `MilitaryBaseJSON`, `MilitaryBaseStorageJSON`, `MilitaryBaseAviationFactoryJSON`, `MilitaryBaseHeadquartersFactoryJSON` (имя с лишним «Factory»), `AerodromePopupJSON {aerodrome: any}`,
  `AviationFactoryInfoJSON`, `HeadquartersInfoJSON`, `MilitaryBaseBalanceData` и таблицы баланса.
- `bag.d.ts`: `MilitaryBaseBuildingJSON` (поля `buildingTime?`, `productionLevel`, `productionCapacityLevel`, `productionRate{current,next}{amount,interval}`, `productionResources`, `productionCapacity`,
  `storageResources`, `storageCapacity`, `transportCapacity`, `productionTime`, `saleTime`, `saleProfit`), `MilitaryBaseAviationFactorySlotJSON {productionTime, productionDuration, airplane|null}`,
  `MilitaryBaseBoostJSON` (см. выше), `StarsJSON`.
- `ItemType`: `MILITARY_BASE_BUILDING = 3`, `MILITARY_BASE_AVIATION_FACTORY_SLOT = 4`, `MILITARY_BASE_BOOST = 5`. После слияния с `amnesia/fix` значение 3 занято
  военной базой, коллекции сдвинуты на 6 ([memory/server_collections_deferred_fixes.md](../memory/server_collections_deferred_fixes.md)). `ItemId`: ресурсы 7/8, здания 1..10
  (Уголь, Железо, Резина, Газ, Алюминий, Медь, Литий, Нефть, Вольфрам, Уран), бустеры 1..50.

<a id="external"></a>
### Точки вне папки

- `HomeScreen.ts:470` — создаёт `HomeScreenMilitaryBase` внутри `UIAerodrome` (уровень кампании не проверяется).
- `Header.ts:21,68-73,100-117` — флаг `SHOW_MILITARY_BASE_CURRENCY`, пресеты долларов и жетонов, ширина блока валют.
- `Footer.ts:123-133` — на `flashActivated` окна `MilitaryBasePopup` вызывает `switchTab(-1)` (кнопка «Главная» отжата), на `flashDeactivated` — `switchTab(0)`.
- `Notifications.MILITARY_BASE = "militaryBase"` (число) — бабл плашки.
- `GameEvents.MILITARY_BASE_UPDATED`, `MILITARY_BASE_BUILDING_UPDATED` (`GameEvents.ts:86-87`).
- `src/plain/Vars.ts:9` `AerodromeAccessCampaignLevel = 5` и ключ `homeScreen.militaryBase.access` («Пройди {0} ур. кампании») не используются базой.

<a id="contract"></a>
### Контракт с сервером (как его видит клиент)

Все команды — WebSocket-запросы `Globals.ws.sendRequest` / `sendButtonRequest`. `sendButtonRequest` держит один глобальный замок на все кнопки приложения: пока ответ не пришёл, любая другая
кнопочная команда отклоняется ошибкой `ERR_WS_BUTTON_ALREADY_PRESSED`. Ответ с полем `errCode/errSection` приходит как отказ промиса; ответ без них, но с `result !== "OK"`, приходит как успех, и клиент
сам проверяет `ResultUtils.isOk`. Если окно, в которое привязан запрос (`generationObject`), закрыто до ответа, ответ отбрасывается (`ERR_WS_GENERATION_ERROR`), побочные эффекты на клиенте не выполняются.

| Роут | Запрос | Ответ (поля, которые читает клиент) | Где |
|---|---|---|---|
| `/ingame/militaryBase` | `{}` | `{militaryBase}`: `dollarsPerHour`, `storage.level`, `aviationFactory{level, exp, productionCost, productionDurations{slot:ms}}`, `headquarters{summons, summonsTime}`, `tutorialProgress` (`storage.exp`, `aviationFactory.productionTime` не читаются) | `MilitaryBasePopup.requestData` |
| `/ingame/militaryBase/balance` | `{}` | `{balance}`: `buildingBuyData{id:{cost,time}}`, `buildingSellData{id:{price}}`, `storageData{lvl:{level,capacity,cost}}`, `aviationFactoryData{lvl:{level,needExp}}`, `buildingUpgradeData{lvl:{cost,…}}`, `aviationFactorySlotData` (не читается). Запрашивается один раз за сессию | то же |
| `/ingame/militaryBase/tick` | `{}` | `{result, militaryBase}` | `MilitaryBasePopup.onTick` |
| `/ingame/militaryBase/buyBuilding` | `{buildingId, useGoldenCoins?}` | OK: `{building, tutorial?}`; не OK: `{missingDollars, goldenCoinsCost}` | `BuyBuildingPopup` |
| `/ingame/militaryBase/skipBuilding` | `{buildingId}` | OK: `{building}` | `SkipBuildingPopup` |
| `/ingame/militaryBase/skipFactory` | `{slotId}` | OK: `{}` (недостижим) | `SkipAviationFactoryPopup` |
| `/ingame/militaryBase/upgradeProduction`, `/upgradeProductionCapacity` | `{buildingId, useGoldenCoins?}` | OK: тело не читается; не OK: `{missingDollars, goldenCoinsCost}` | `ResourcesPopup` |
| `/ingame/militaryBase/upgradeStorage` | `{useGoldenCoins?}` | OK: `{militaryBase}`; не OK: `{missingDollars, goldenCoinsCost}` | `StoragePopup` |
| `/ingame/militaryBase/collectResource` | `{buildingId}` (0 — со всех) | OK: `{resources: number[] (id собранных зданий), tutorial?}` | `MilitaryBasePopup`, `ResourcesPopup` |
| `/ingame/militaryBase/sellResource` | `{buildingId, amount}` | OK: `{tutorial?}` | `SellResourcePopup` |
| `/ingame/militaryBase/takeProfit` | `{buildingId}` | `{rewards: ItemJSON[]}` (наличие `result` не проверяется) | `StoragePopup` |
| `/ingame/militaryBase/summon` | `{}` | OK: `{militaryBase, boost, current|null}` | `HeadquartersPopup` |
| `/ingame/militaryBase/summonAccept`, `/summonRefuse` | `{}` | OK | `SummonPopup` |
| `/ingame/militaryBase/headquartersInfo` | `{}` | `{rank:[{rank,chance}], stars:[{rank,chance}]}` (делитель 100000) | `HeadquartersInfoPopup` |
| `/ingame/militaryBase/aviationFactoryInfo` | `{}` | `{level, rank:[{rank,current}], stars:[…], importantRankLevel?{level,rank}, importantStarsLevel?{level,rank}}` (делитель 1 000 000) | `AviationFactoryInfoPopup` |
| `/ingame/militaryBase/runFactory` | `{slotId, useGoldenCoins?}` | OK: `{militaryBase}`; не OK: `{missingDollars, goldenCoinsCost}` | `AviationFactoryPopup` |
| `/ingame/militaryBase/checkFactory` | `{slotId}` | OK: `{receivedAirplane, replaceableAirplane|null}` | то же |
| `/ingame/militaryBase/acceptAirplane`, `/refuseAirplane` | `{slotId}` | `{militaryBase}` (accept вызывается через `sendRequest`, без замка и без проверки `result`) | то же |
| `/ingame/aerodrome` | `{}` | `{aerodrome:{airplanes:[{airplaneUid}] ×8}}` | `AerodromePopup` |
| `/ingame/devTools/userDollars`, `/userTokens` | `{}` | не читается | шапка, только dev |

Серверный алиас `/ingame/military_base` мёртв, клиент его не вызывает. `MilitaryBaseStorageJSON.exp` объявлен в `militaryBase.d.ts:11`, сервер не отдаёт, клиент не читает. `bonus.amount` читается без проверки (`MilitaryBaseUtils.ts:45`); сервер заполняет его для всех 50 id.

Push-событий базы нет. Используются: `g/ws/events/bag/update` (`items`, `del`; предметы типов 3/4/5 и ресурсы 2/7/8) и уведомление аккаунта `militaryBase` (число) для плашки.

<a id="contract-gold"></a>
**Шаблон «доплата золотом».** Пять команд (покупка здания, прокачка добычи, прокачка транспорта/лимита, прокачка склада, запуск слота) при нехватке долларов отвечают не-OK с `missingDollars` и `goldenCoinsCost`.
Клиент открывает `MilitaryBaseMissingDollarsPopup`, который повторяет тот же роут с теми же полями и `useGoldenCoins: true`. Расчёт `goldenCoinsCost` делает сервер.

<a id="gdd-mapping"></a>
### Сопоставление функций с ГДД ([`#gdd-function-mapping`](agent-system-workflow.md#gdd-function-mapping))

| Функция | Правило ГДД | Замечание |
|---|---|---|
| `MilitaryBaseUtils.canCollectResource` | [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings) — сбор (порог 10% и место) | в ГДД порога нет ([#code-rules](#code-rules)) |
| `MilitaryBasePopup.updateCollectNotifiers` | [#gdd-base-map](game-design/military-base-gdd.md#gdd-base-map) — бабл сбора | условие свое для окна здания (`ResourcesPopup.setCollectBusy`) |
| `MilitaryBaseState.hasProfit` / `StorageResource.bind` (`take`) / `base/Storage.checkProfit` | [#gdd-storage](game-design/military-base-gdd.md#gdd-storage) — сбор долларов | дубль условия |
| `MilitaryBaseState.hasAirplane` / `base/AviationFactory.checkAirplanes` / `AerodromePopup.checkAirplanes` | [#gdd-aviation-factory](game-design/military-base-gdd.md#gdd-aviation-factory), [#gdd-aerodrome-view](game-design/military-base-gdd.md#gdd-aerodrome-view) | тройной дубль |
| `AerodromePopup.checkIdle/checkTime/checkAirplanes` | [#gdd-aerodrome-view](game-design/military-base-gdd.md#gdd-aerodrome-view) — три состояния кнопки завода | |
| `MilitaryBaseUtils.isBoostBetter` | [#gdd-headquarters](game-design/military-base-gdd.md#gdd-headquarters) — выбрать или продать | |
| `MilitaryBaseData.getSkipBuildingCost` | [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings) — ускорение стройки | число в коде |
| `SellResourcePopup.getSaleDuration`, `bind` (макс. отправки) | [#gdd-storage](game-design/military-base-gdd.md#gdd-storage) — продажа рейсом | считается и на клиенте, и на сервере ([#p-hardcode](#p-hardcode)) |
| `AviationFactoryPopup.getSortedSlotIds` | [#gdd-aviation-factory](game-design/military-base-gdd.md#gdd-aviation-factory) — порядок слотов | в ГДД не описан |
| `HeadquartersPopup.bind` | [#gdd-headquarters](game-design/military-base-gdd.md#gdd-headquarters) — цена и бесплатные призывы | цена в золоте, в ГДД — доллары |
| `MilitaryBaseUtils.getViewLevel` | [#gdd-resource-buildings](game-design/military-base-gdd.md#gdd-resource-buildings) — «каждое улучшение +1 к уровню» | |
| `Footer.onFlashActivated/Deactivated` | [#gdd-access](game-design/military-base-gdd.md#gdd-access) — кнопка «Главная» | |

<a id="code-rules"></a>
### Правила из кода, которых нет в исходниках ГДД

См. список в конце документа ([#code-rules-list](#code-rules-list)).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Статус: «баг» — вероятная ошибка; «риск» — зависит от сервера или не подтверждено запуском; «долг» — дубли, мёртвый код.

<a id="p-access"></a>
### 1. Доступа по уровню кампании на клиенте нет
Плашка и окно доступны сразу (`HomeScreen.ts:470`). Ключ `homeScreen.militaryBase.access` («Пройди {0} ур. кампании») есть в `ru.json`, но не используется; `Vars.AerodromeAccessCampaignLevel = 5` читает
только неподключённый `HomeScreenAerodrome`. Либо сервер сам не пускает (тогда клиент не покажет причину), либо доступа нет вовсе — решение пользователя ([#gdd-access](game-design/military-base-gdd.md#gdd-access)).

<a id="p-skip-factory"></a>
### 2. Ускорение производства самолёта недостижимо
Кнопка в слоте закомментирована (`AviationFactorySlot.ts:305-308`), `onSkip` передаётся, но не вызывается; `MilitaryBaseSkipAviationFactoryPopup` и `getSkipAviationFactoryCost` (всегда 0) — мёртвый код.
ГДД-источник: «Сборку можно ускорить за доплату» ([#gdd-aviation-factory](game-design/military-base-gdd.md#gdd-aviation-factory)). Не реализовано.

<a id="p-boost-plus"></a>
### 3. «+» на бустере не ведёт в штаб напрямую
Во всех обработчиках `onPressBoost` ветка `boostId === 0 → штаб` недостижима (`MilitaryBasePopup.ts:278`, `AviationFactoryPopup.ts:249`, `StoragePopup.ts:341`, три копии); на самом деле открывается
`MilitaryBaseBoostPopup`, откуда кнопка «Перейти в штаб». Правка 1.3 просит прямой переход.

<a id="p-summon-close"></a>
### 4. Закрытие окна призыва без решения (закрыто сверкой с сервером 2026-10-22)
`MilitaryBaseHeadquartersSummonPopup` закрывается по фону (`bgClick`, строка 471), не вызывая `/summonAccept` или `/summonRefuse`, запросов при закрытии не шлёт (`:52-59`). Бустер не теряется: сервер держит его в штабе
(`MilitaryBaseHeadquarters.java:21,111-119`), `clearBoost` вызывается только из accept/refuse, повторный `/summon` выдаёт тот же бустер без оплаты. Проблемы нет. Кнопка «ВЫБРАТЬ» недоступна, когда бустер хуже или равен; «ПРОДАТЬ» недоступна, когда лучше.

<a id="p-fixes"></a>
### 5. Состояние правок из `military-base-fixes.txt`
Построчная сверка — в отчёте аналитика (кратко): сделано 1.1, 1.2, 1.6, 2.5, 3.1; 2.1 похоже сделано (период 4000 мс и случайная задержка 0-200 мс, прежние значения неизвестны); не сделано 1.3 (прямой переход), 1.4 (частично), 2.3 («0%»), 2.9 (боковые тени остались); 1.5 и
остальное — на сервере или визуал, по коду клиента не проверить.

<a id="p-hardcode"></a>
### 6. Числа и формулы, зашитые в клиент
Цена призыва штаба 250 золота (`HeadquartersPopup.ts:108`; совпадает с сервером, `MilitaryBaseData.java:11-12`), цена продажи плохого бустера 125 серебра (`SummonPopup.ts:156`), ускорение стройки 100 золота и 0 для Угля (`MilitaryBaseData.ts:8-13`),
порог сбора 10% (`MilitaryBaseUtils.ts:161`), формула времени рейса (`SellResourcePopup.ts:161-174`), делители шансов 100000/1000000. Значения 250 золота, 125 серебра и ускорение стройки (0 для здания 1, иначе 100) совпадают с сервером (`MilitaryBaseData.java:11-12,69-74`), но в `/balance` не приходят и у клиента зашиты. Если сервер изменит числа, экран покажет старые.

<a id="p-booster-count"></a>
### 7. Бустеров 50 вместо 52
ГДД: 52 (20 для ресурсных зданий, 21 для склада, 11 для завода). В коде `ItemId` и `ru.json` — 50 (по 4 на здание и 10 слотов); нет общего бустера склада и «Отдела ревизии» (цена производства).
Атласы `military_base_boost/51`, `/52` и пакеты `Boost_51/52` в `LoadAssetPackage.ts` есть, а `ItemId`, `MilitaryBaseBoostRouter` и тексты — нет. Сверка с сервером: бустеры 51/52 существуют только как картинки (мёртвые ассеты), `ItemId.ts` совпадает с серверным (50 id).

<a id="p-silent-errors"></a>
### 8. Ошибки не показываются игроку
Почти все `.catch` пустые (19 `catch` в области, только два пишут в `Logger`), включая `ERR_WS_BUTTON_ALREADY_PRESSED`. «Серые» кнопки (`BUTTON_STATUS_DISABLE`) остаются нажимаемыми (`MilitaryBaseUtils.buttonStatus`: `setInteractive(status >= 0)`):
призыв штаба без золота, ускорение стройки без золота, прокачки без долларов. У прокачек нажимаемость нужна ради окна доплаты; у призыва и ускорения окна докупки золота нет, игрок
не получает объяснения.

<a id="p-double-press"></a>
### 9. Двойное нажатие
`FlashPublisher.publish` не отсекает повторные окна; окна, перед показом грузящие данные (`MilitaryBasePopup`, `AerodromePopup`, оба `…InfoPopup`), стартуют вторую цепочку при втором нажатии. У команд работает
замок `sendButtonRequest`. Не проверено запуском.

<a id="p-nan"></a>
### 10. Деление на ноль в окне склада
`MilitaryBaseStoragePopup.ts:112` — `120 * (1 / maxCapacity * usedCapacity)` при `maxCapacity = 0` (ни одного построенного здания) даёт `NaN` в ширине полоски.

<a id="p-slot-delete"></a>
### 11. Удаление предмета слота рисует старое состояние
`MilitaryBaseAviationFactorySlot` подписан на `ITEM_DELETE` тем же обработчиком, что и на обновление (`:62`), и вызывает `bind(item)` с удалённым предметом (в `UserBag` он приходит со старыми полями и `count = 0`).
Если сервер удаляет предмет слота, а не обнуляет его, слот останется в прежнем состоянии. Остальные классы (`MilitaryBaseResource`) обрабатывают удаление как `bind(null)`. Зависит от сервера.

<a id="p-aerodrome-crash"></a>
### 12. Аэродром базы падает без самолёта в сумке
`MilitaryBaseAerodromePopup.ts:120,150` — `getAirplane(uid)` может вернуть `null`, дальше `data.uid`, `data.power`. Известный отложенный баг ([memory/aerodrome_deferred_fixes.md](../memory/aerodrome_deferred_fixes.md)). Подпись «В БОЮ» тоже не вернули.

<a id="p-take-profit"></a>
### 13. Получение прибыли без проверки ответа
`MilitaryBaseStoragePopup.BtnTakeProfit` не проверяет `result` и берёт `RewardUtils.getResource(response.rewards, …).count`; если ответ без наград, выбрасывается исключение в `then` (проглатывается пустым `catch`).
`holdResource` вызывается после ответа, то есть если обновление сумки пришло раньше, ресурс уже виден в шапке. Строка-тег удержания написана дважды. Подтверждено сверкой: `/acceptAirplane` и `/refuseAirplane` тоже не проверяют `result` (`AviationFactoryPopup.ts:342-361`), при ответе без `militaryBase` в `setMilitaryBaseData` уходит `undefined`; `/takeProfit` — `StoragePopup.ts:391-398`.

<a id="p-state-order"></a>
### 14. Неявный порядок вызовов (`#no-implicit-order`)
- Пара «`MilitaryBaseState.setMilitaryBaseData(...)` + `GameEvents.emit(MILITARY_BASE_UPDATED, ...)`» повторена в `MilitaryBasePopup.onTick`, `HeadquartersPopup.BtnSummon`, `AviationFactoryPopup.onStartProductionSuccess/OnAirplaneAccept/OnAirplaneRefuse`,
  `StoragePopup.onUpgradeSuccess`. Предложение: один метод у `MilitaryBaseState`, который и обновляет, и эмитит.
- Вызывающий сам меняет поле чужого объекта: `MilitaryBaseState.getMilitaryBaseData().tutorialProgress = response.tutorial; emit(MILITARY_BASE_UPDATED)` в `BuyBuildingPopup.onBuyBuildingSuccess`,
  `SellResourcePopup.BtnSellResource`, `ResourcesPopup.BtnCollectResource`. Предложение: `MilitaryBaseState.setTutorialProgress(value)`.
- Дочерние классы в конструкторе читают `MilitaryBaseState.getMilitaryBaseData()` (`base/*`) и `MilitaryBaseData.balance` (все окна) — это работает только потому, что `MilitaryBasePopup.requestData` вызвана раньше.
  Попап любого здания, открытый в обход окна базы, получит `undefined`.

<a id="p-balance-cache"></a>
### 15. Баланс кэшируется навсегда
`MilitaryBaseData.balance` запрашивается один раз за жизнь страницы и не сбрасывается. Изменение баланса на сервере увидят только после перезагрузки.

<a id="p-tick-loop"></a>
### 16. Цикл запросов `/tick` при ошибке (переформулировано сверкой с сервером 2026-10-22)
`shouldRequestTick` возвращает `true`, пока у какого-то здания `productionTime - now <= 0`. Сервер `productionTick` всегда сдвигает `productionTime` (`MilitaryBaseBuilding.java:212-240`), полный склад цикла не даёт.
Цикл возможен при ошибке `/tick`: подпись обновляется только при OK (`MilitaryBasePopup.ts:128-129`), `catch` шлёт запрос заново каждый тик (`:137-160`). Остаточный риск — рассинхрон часов клиента и сервера (`src/utils/TimeUtils.ts:11-29`).

<a id="p-plate-timer"></a>
### 17. Таймер взлёта на плашке идёт по тикам, а не по часам
`HomeScreenMilitaryBase` вычитает по 1000 мс за каждый срабатывание tween. В фоновой вкладке с остановленным таймером браузера таймер отстанет от реального. Остальные таймеры базы считаются от `TimeUtils.nowMls()`.

<a id="p-two-tabs"></a>
### 18. Две вкладки / обрыв связи
Предметы базы обновляются общим push сумки, поэтому вторая вкладка увидит изменения зданий и слотов. `MilitaryBaseJSON` (уровни склада и завода, `exp`, бесплатные призывы, `tutorialProgress`) обновляется только ответами
собственных команд и `/tick`, поэтому в чужой вкладке он устареет до следующего открытия окна. При обрыве связи запросы ждут сокет бесконечно (повторы без лимита), все кнопки блокируются замком до ответа или таймаута.

<a id="p-duplicates"></a>
### 19. Дубли по смыслу (`#gdd-function-mapping`)
- «Есть готовый самолёт» — `MilitaryBaseState.hasAirplane`, `base/MilitaryBaseAviationFactory.checkAirplanes`, `MilitaryBaseAerodromePopup.checkAirplanes`; «ближайший остаток производства» — `base/…Factory.checkTime`, `AerodromePopup.checkTime`.
- «Есть прибыль на складе» — `MilitaryBaseState.hasProfit`, `base/MilitaryBaseStorage.checkProfit`.
- «Здание построено» (`buildingTime && buildingTime - now > 0`) — в `MilitaryBaseState` ×3, `MilitaryBasePopup` ×2 (в форме `<= now`), `MilitaryBaseResource`, `StorageResource`, `SelectableResource`, `ResourcesPopup`.
- «Можно прокачать» (доллары ≥ стоимости добычи/транспорта) — `MilitaryBaseResource.bind` и `MilitaryBaseSelectableResource.bind` дословно.
- «Можно собрать» — `MilitaryBasePopup.updateCollectNotifiers` (с поправкой на `productionResources > 0` и место) и `ResourcesPopup.setCollectBusy` (`canCollectResource`).
- `MilitaryBaseBoostSmall` / `Medium` / `Boost` — три копии одной карточки; `SkipBuildingPopup` / `SkipAviationFactoryPopup` — две копии окна.
- Цикл по `id 1..10` с `getItem` повторён десятки раз (`MilitaryBaseState`, `MilitaryBasePopup`, `base/*`, `AerodromePopup`).
- Прослойки без логики `onMilitaryBaseUpdate(data) { this.bind(); }` / `onBuildingUpdate`: `base/Headquarters`, `base/Storage`, `base/AviationFactory`, `StoragePopup`.
- Обработка `missingDollars` — четыре копии с одинаковой структурой (`BuyBuildingPopup`, `AviationFactoryPopup`, `StoragePopup`, `ResourcesPopup.onUpgradeResponse`).
- Указатель туториала (`processTutorial`/`hideTutorial`) — четыре копии.

<a id="p-dead-code"></a>
### 20. Мёртвый код — кандидаты на удаление
`MilitaryBaseNotification` и `MilitaryBaseState.getNotification`; `MilitaryBaseSkipAviationFactoryPopup` и `getSkipAviationFactoryCost`; `MilitaryBaseUtils.transport`, `i18nRateInterval`, `BUTTON_STATUS_BLUE`;
`MilitaryBaseData.getAviationFactorySlotData` и `balance.aviationFactorySlotData`; `MilitaryBaseBoostRouter.hasVariant`; `HeaderTokensBar` целиком (отключён, нет траты); недостижимые ветки `boostId === 0`;
ветка «не куплено» в `ResourcesPopup.UISelectableResources`; `AviationFactorySlot` — переменная `panelBtn` не добавляется на экран, в `UIReady` плейсхолдер `id = 40`; закомментированные блоки в `base/*`, `BuyBuildingPopup`,
`ResourcesPopup`; `homeScreen.militaryBase.access`; `AerodromePopupJSON.aerodrome: any`.

<a id="p-misc"></a>
### 21. Мелочи
- `BuyBuildingPopup` создаёт `FlashLayout("MilitaryBaseSkipBuildingPopup")` (копия имени; по имени флеша `Footer` различает только `MilitaryBasePopup`).
- `SellResourcePopup`: ползунок настроен на `0..storageResources`, а текущее значение ограничено `min(storageResources, transportCapacity)`; если транспорт меньше склада, ползунок при «максимуме» не у правого края (правка 1.4).
- Склад: прибавка вместимости при апгрейде умножается на число построенных зданий, а `used` считает и строящиеся.
- `HeaderDollarsBar.animationValue` берёт стартовое число из текста `parseInt(text.split(" ").join(""))`; при сокращённом формате («1.2K») старт будет искажён (не проверено).
- В `MilitaryBaseAviationFactory`/`Storage` бабл «не перебивается»: тикер включает бабл, но выключает его только `bind` по событию.
- `MilitaryBaseAviationFactoryPopup.OnAirplaneAccept` шлёт `sendRequest`, а `OnAirplaneRefuse` — `sendButtonRequest` (разный замок на двойное нажатие).
- Слот завода перерисовывается целиком (`replaceByName`) на каждое `MILITARY_BASE_UPDATED`, и порядок слотов может прыгнуть.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`game-design/military-base-gdd.md`](game-design/military-base-gdd.md); противоречия исходника и неутверждённые числа — в его [#gdd-open](game-design/military-base-gdd.md#gdd-open).
Сопоставление функций — в [#gdd-mapping](#gdd-mapping). Расхождения ГДД ↔ код — по решению пользователя 2026-10-22 все в [#gdd-open](game-design/military-base-gdd.md#gdd-open) (группа «Расхождения ГДД ↔ код»), решения нет; визуальные правки 2.9 и 2.4 — в отложенных исправлениях (`memory/military_base_deferred_fixes.md`); места в коде — в последнем столбце таблицы (в ГДД путей к коду нет):

| Тема | ГДД (исходник) | Код | Где в коде (от `C` = `src/views/home_screen/popups/military_base/`) |
|---|---|---|---|
| Цена призыва | за доллары | 250 золота (клиентская константа) | `MilitaryBaseHeadquartersPopup.ts:108` |
| Призыв 1 или 10 | да | один | `MilitaryBaseHeadquartersPopup.ts` |
| Бесплатные призывы | 3 каждые 12 ч (утвердить) | `summons` и `summonsTime` с сервера | `MilitaryBaseHeadquartersPopup.ts` |
| Бабл штаба | с числом; без числа, если есть доллары | только с числом | `base/MilitaryBaseHeadquarters.ts:51-58` |
| Бустеров | 52 | 50 | `src/plain/items/ItemId.ts:23+`, `src/plain/military_base/MilitaryBaseBoostRouter.ts` |
| Автозаполнение завода | есть | нет | `MilitaryBaseAviationFactoryPopup.ts` |
| Ускорение сборки | за доплату | недостижимо | `MilitaryBaseAviationFactoryPopup.ts:245-246`, `MilitaryBaseAviationFactorySlot.ts:305-308` |
| Клик по готовому слоту | в любое место | только зелёная кнопка | `MilitaryBaseAviationFactorySlot.ts:370+` |
| Прокачка зданий | занимает время | без таймера | `MilitaryBaseResourcesPopup.ts:834-871` |
| Прокачка склада | по типам ресурсов отдельно | один уровень склада | `MilitaryBaseStoragePopup.ts:408+` |
| Порядок покупки зданий | новый плейсмент после покупки предыдущего | любое из 10 сразу | `MilitaryBasePopup.ts:262-273`, `MilitaryBaseResource.ts:160,318` |
| Прокачка завода | за созданные самолёты | показывает `exp` с сервера (правка 1.5 — по серверу); `MilitaryBaseStorageJSON.exp` объявлен, но сервер не отдаёт и клиент не читает | `militaryBase.d.ts:11` |
| Не хватает валюты | попап «купить валюту» | доплата золотом | `MilitaryBaseMissingDollarsPopup.ts:166` |
| Рейсов на продажу | несколько, пока есть транспорт | один рейс на здание | `MilitaryBaseStorageResource.ts:130-143` |
| Сбор ресурсов в склад | автоматический, ручной сбор отменён | кнопка и бабл «собрать» (`/collectResource`), порог 10% лимита | `MilitaryBasePopup.ts:365`, `MilitaryBaseResourcesPopup.ts:893`, `MilitaryBaseUtils.ts:161` |
| Бустеры ресурсного здания | 2 (добыча, транспорт); хранение и фуры — у склада | 4 на здание (добыча, логистика, хранилище, транспорт) | `ItemId.ts` |
| «+» на пустом бустере | сразу в штаб (правка 1.3) | карточка бустера с кнопкой «Перейти в штаб» | `MilitaryBaseBoostPopup.ts:144`, `MilitaryBaseResource.ts:420-423`, `MilitaryBasePopup.ts:278`, `MilitaryBaseAviationFactoryPopup.ts:249`, `MilitaryBaseStoragePopup.ts:341` |
| Нет бустера | иконка влияния и «0%» (правка 2.3) | иконка и «+» / «+0» | `MilitaryBaseResource.ts:428-434` |
| Ползунок продажи | на максимуме (правка 1.4) | значение — максимум, шкала до запаса склада | `MilitaryBaseSellResourcePopup.ts:104-114` |
| Доступ | с 5-го уровня кампании (aerodrome-gdd, в #gdd-open) | без проверки | `HomeScreen.ts:470` |

<a id="file-map"></a>
## 10. Карта файлов компонента

### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `src/views/home_screen/HomeScreenMilitaryBase.ts` | плашка на главном экране, таймер и анимация взлёта |
| `src/plain/military_base/MilitaryBaseBoostRouter.ts` | таблицы бустеров, пути ассетов и ключи имён |
| `src/shared/header/presets/HeaderDollarsBar.ts` | счётчик долларов в шапке |
| `src/shared/header/presets/HeaderTokensBar.ts` | счётчик жетонов в шапке (отключён) |
| `src/views/home_screen/popups/military_base/MilitaryBasePopup.ts` | окно базы, тик, сбор со всех |
| `…/military_base/MilitaryBaseBackground.ts` | фон и декоративные анимации |
| `…/military_base/base/MilitaryBaseHeadquarters.ts`, `base/MilitaryBaseStorage.ts`, `base/MilitaryBaseAviationFactory.ts`, `base/MilitaryBaseAerodrome.ts` | здания на карте, баблы |
| `…/military_base/MilitaryBaseState.ts`, `MilitaryBaseData.ts`, `MilitaryBaseUtils.ts`, `MilitaryBaseNotification.ts`, `militaryBase.d.ts` | состояние, баланс, утилиты, типы |
| `…/military_base/MilitaryBaseResource.ts`, `MilitaryBaseSelectableResource.ts`, `MilitaryBaseResourcesPopup.ts` | ресурсные здания |
| `…/military_base/MilitaryBaseBuyBuildingPopup.ts`, `MilitaryBaseSkipBuildingPopup.ts`, `MilitaryBaseMissingDollarsPopup.ts` | покупка, ускорение, доплата |
| `…/military_base/MilitaryBaseStoragePopup.ts`, `MilitaryBaseStorageResource.ts`, `MilitaryBaseSellResourcePopup.ts` | склад и продажа |
| `…/military_base/MilitaryBaseHeadquartersPopup.ts`, `MilitaryBaseHeadquartersSummonPopup.ts`, `MilitaryBaseHeadquartersInfoPopup.ts` | штаб |
| `…/military_base/MilitaryBaseBoost.ts`, `MilitaryBaseBoostSmall.ts`, `MilitaryBaseBoostMedium.ts`, `MilitaryBaseBoostPopup.ts` | карточки бустеров |
| `…/military_base/MilitaryBaseAviationFactoryPopup.ts`, `MilitaryBaseAviationFactorySlot.ts`, `MilitaryBaseAviationFactoryInfoPopup.ts`, `MilitaryBaseSkipAviationFactoryPopup.ts` | авиазавод |
| `…/military_base/MilitaryBaseAerodromePopup.ts` | аэродром базы |
| `assets-src/atlas/military_base_screen/**`, `military_base_boost/**`, `military_base_boost_variant/transport/**` | атласы базы и бустеров |
| `assets-src/atlas/home_screen/support/military_base.png` | картинка плашки |
| `assets-src/raw/backgrounds/military_base.png`, `mb_hq.png` | фоны базы и штаба |

### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `src/views/home_screen/HomeScreen.ts` (`UIAerodrome`, строка 470) | подключает плашку |
| `src/shared/header/Header.ts`, `HeaderPresets.ts` | флаг `SHOW_MILITARY_BASE_CURRENCY`, создание пресетов |
| `src/shared/footer/Footer.ts` (`onFlashActivated/Deactivated`) | отжимает «Главная» на время окна базы |
| `src/shared/notifications/Notifications.ts` | ключ `MILITARY_BASE` |
| `src/plain/GameEvents.ts` | события `MILITARY_BASE_UPDATED`, `MILITARY_BASE_BUILDING_UPDATED` |
| `src/plain/items/ItemType.ts`, `ItemId.ts` | зависимость: типы 3/4/5, ресурсы 7/8, здания, бустеры 1..50 |
| `src/views/home_screen/popups/bag/bag.d.ts` | типы `MilitaryBaseBuildingJSON`, `…AviationFactorySlotJSON`, `…BoostJSON` |
| `assets-src/raw/lang/ru/ru.json` | ключи `militaryBaseScreen.*` (в т.ч. `boostName/boostTarget/boostInfo` ×50, `buildings`, `boostVariant.transport`), `homeScreen.militaryBase.*`, `homeScreen.takeoffTime` |
| `src/plain/LoadAssetPackage.ts`, `tools/src/config.yaml` | пакеты `MilitaryBaseScreen`, `MilitaryBaseBackground`, `MilitaryBaseHQ`, `AerodromeScreen`, `Boost_<id>`, `Boost_transport_<n>` |
| `src/plain/user/UserBag.ts` | зависимость: `getItem`, `getResourceCount`, `holdResource/releaseHold`, push `g/ws/events/bag/update` |
| `src/plain/globals/WSSocket.ts` | зависимость: `sendRequest/sendButtonRequest` |
| `src/shared/PresentationFlow.ts`, `src/shared/animations/FlyIconsAnimation.ts` | зависимость: очередь показа и полёт иконок |
| `src/views/home_screen/popups/airplane/AirplaneGetPopup.ts`, `…/AirplaneInfoPopup` | чужая область: окно получения самолёта и карточка самолёта |
| `src/views/home_screen/HomeScreenAerodrome.ts`, `src/plain/Vars.ts` | неподключённый остаток, `AerodromeAccessCampaignLevel` ([aerodrome-architecture.md](aerodrome-architecture.md)) |
| `assets-src/atlas/aerodrome_screen/**`, `airplanes/**` | атласы аэродрома и самолётов (пакет `AerodromeScreen`) |
| `src/battle/events/airplane/*` (`AirplanePrepareTakeoffEvent`, `AirplaneTakeoffEvent`) | зависимость плашки на главной |

<a id="code-rules-list"></a>
## Приложение. Правила из кода, которых нет в исходниках ГДД

В ГДД не внесены, пользователь не подтверждал.

1. Плашка и окно доступны без проверки уровня кампании; ключ «Пройди N ур. кампании» не используется ([#p-access](#p-access)).
2. Призыв штаба стоит 250 золота (клиент); при `summons > 0` призыв бесплатный, показывается «Бесплатное снабжение N»; таймер до начисления — `summonsTime`.
3. Результат призыва: сравнение по `bonus.amount` (null всегда хуже); лучше — только «ВЫБРАТЬ», хуже или равно — только «ПРОДАТЬ» за 125 серебра.
4. Доплата золотом работает для покупки здания, прокачки добычи/транспорта, прокачки склада и запуска слота; цену золота даёт сервер.
5. Ускорение стройки: 100 золота, первое здание (Уголь) бесплатно.
6. Здание «собрать ресурс»: порог 10% от лимита добычи и наличие места на складе; в окне здания при полном складе кнопка превращается в переход на склад.
7. Вместимость склада = сумма вместимости построенных зданий; уровень склада один; прирост при улучшении = разница вместимости × число построенных зданий.
8. Продажа: максимум = минимум из запасов здания и вместимости транспорта; шаг ± = 5% от максимума (не меньше 1, округляется вниз до разряда); один рейс на здание, три состояния строки склада (отправить, в пути, получить прибыль).
9. Время рейса для показа: полный транспорт — 10 минут, иначе от 5 до 9,5 минуты ступенями по 30 секунд.
10. Авиазавод: десять слотов, одна цена производства на все слоты, время — на слот; порядок слотов — по убыванию бонуса бустера слота, затем по номеру; ускорение недоступно, автозаполнения нет.
11. Уровень здания для показа: 1 плюс количество улучшений добычи и транспорта.
12. Бустеры: 50 штук (по 4 на здание — добыча, вместимость/логистика, хранилище, транспорт — и 10 слотов завода); у транспортных 10 вариантов картинки и названия; нет бустера — иконка типа и «+», на ресурсном здании «+0» серым.
13. Нажатие на любой бустер или «+» открывает карточку бустера с кнопкой «Перейти в штаб».
14. Туториал базы: `tutorialProgress` 0 (купить Уголь), 1 (собрать), 2 (продать), -1 (завершён); шаги двигает сервер через поле `tutorial` в ответах.
15. Баблы: штаб — число бесплатных призывов; склад — прибыль (приоритет) или «склад полон», плюс стрелка прокачки; завод — готовый самолёт, иначе таймер; плашка на главной — число из уведомления `militaryBase`.
16. Аэродром базы: сумма мощности в здании считается по всем самолётам сумки, а не только по стоянкам; кнопка перехода на завод — три состояния (простой, производство, готов самолёт).
17. Шапка на базе: золото, серебро и доллары; жетоны не показываются и нигде не используются.
18. Время взлёта самолёта игрока и анимация на плашке главной берутся из событий боя, не из состояния базы.
