# Военная база — `MilitaryBaseUserComponent` (сервер)

> **auto-create.** Документ составлен `server-analyst-lead` по коду 2026-10-22 (ветка `koba/collection`).
> Подтверждено чтением кода, запуском не проверялось. Клиентскую сторону разбирает
> `client-analyst-lead`, контракт client↔server сверяет `integration-lead`.

ГДД: [military-base-gdd.md](/workspace/client/.claude/docs/game-design/military-base-gdd.md). Правки пользователя (документ «Правки») внесены в его разделы;
противоречия источника, которые пользователь отложил, собраны в [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open).

Смежные документы: [aerodrome-architecture.md](aerodrome-architecture.md) (расстановка самолётов по
позициям), [train-architecture.md](train-architecture.md) (общий Summon: лист `SummonUpgrade`, шансы
рангов и звёзд), [bag-architecture.md](bag-architecture.md) (`BagItem`, сумка),
[codex-architecture.md#producers](codex-architecture.md#producers),
[quests-architecture.md](quests-architecture.md).

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

Военная база даёт игроку самолёты и способ их прокачки ([gdd-purpose](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-purpose)). Цепочка: ресурсные здания добывают
сырьё, игрок переносит его на склад, отправляет конвоем на продажу и получает доллары
(`ItemId.RESOURCE_MILITARY_BASE_DOLLARS`), а за доллары запускает производство самолёта на
авиационном заводе. В штабе игрок призывает бустеры, которые усиливают здания, склад и слоты завода.
Готовый самолёт игрок принимает (он встаёт на позицию аэродрома) или продаёт за серебро.

Состояние хранится в двух местах:

- **Компонент** `MilitaryBaseUserComponent` (поле `MilitaryBase` документа пользователя): уровень
  склада, уровень/опыт/счётчик производств авиазавода, бесплатные призывы штаба и выпавший, но не
  принятый бустер, шаг туториала базы.
- **Сумка**: здания (`MilitaryBaseBuilding`, `ItemType.MILITARY_BASE_BUILDING` = 3, id 1–10), слоты
  авиазавода (`MilitaryBaseAviationFactorySlot`, `ItemType` = 4, id 1–10, внутри — произведённый
  самолёт) и бустеры (`MilitaryBaseBoost`, `ItemType` = 5, id 1–50). Один предмет на id, не стакаются.

Правила по коду:

- **Старт.** Новому игроку (пустая сумка) `initStarter` даёт 1000 долларов, 10 бустеров-транспортов
  ранга I с одной звездой I и ставит туториал на шаг 0.
- **Покупка здания** `/buyBuilding`: цена и время стройки — `MilitaryBaseData.BUILDING_BUY_DATA`
  (уголь — 0 долларов и 10 с, уран — 25 млн и 1 ч). Порядок покупки сервер не проверяет
  ([#tradeoffs](#tradeoffs) п.3). Ускорение стройки `/skipBuilding`: уголь бесплатно, остальные — 100 золота.
- **Добыча** (`MilitaryBaseBuilding.productionTick`): раз в 10 с здание добавляет
  `round((production(уровень) + бустер добычи) / 6)` единиц во внутренний буфер, пока буфер не
  заполнен (ёмкость — `capacity(уровень ёмкости) + бустер логистики`). Тик считается только при
  вызове `""` или `/tick`; пропущенное время навёрстывается целым числом интервалов.
- **Сбор** `/collectResource`: игрок переносит буфер здания (или всех зданий при `buildingId = 0`) на
  склад ресурса этого здания; ёмкость склада ресурса — `capacity(уровень склада) + бустер склада`.
- **Продажа** `/sellResource`: одна отправка на здание за раз; количество не больше вместимости
  транспорта (бустер-транспорт, без него 10 000). Прибыль — 5 долларов за единицу, время в пути —
  5–10 минут в зависимости от загрузки транспорта. Прибыль забирается `/takeProfit` после прибытия.
- **Оплата долларами.** Покупка и улучшения здания, улучшение склада и запуск производства
  списывают доллары; если долларов не хватает и клиент прислал `useGoldenCoins`, недостающая часть
  оплачивается золотом по курсу 100 золота за час дохода базы (`getGoldenCoinsCostForDollarsCost`).
  Без флага сервер возвращает ошибку с `missingDollars` и `goldenCoinsCost`.
- **Улучшения** мгновенные: уровень добычи и уровень ёмкости здания — по листу `MBBuildingData`
  (100 уровней), уровень склада — по `MBStorageData` (100 уровней).
- **Авиазавод.** 10 слотов работают параллельно. `/runFactory` списывает цену, сразу генерирует
  самолёт (ранг и звёзды по уровню завода, листы `SummonRankChances`/`SummonStarsRankChances`),
  кладёт его в слот и запускает таймер. Первое производство бесплатно, со 2-го по 20-е — 100 долларов
  и 30 с, дальше — цена и время из `MBAviationFactory` по уровню завода. Бустер слота сокращает время
  на фиксированное число секунд, минимум 1 с. Готовый самолёт: `/checkFactory` показывает его и
  самолёт, которого он заменит; `/acceptAirplane` ставит его на аэродром, `/refuseAirplane` продаёт за
  серебро. В обоих случаях завод получает +1 опыт ([gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory), правка 1.5); при наборе порога листа
  `SummonUpgrade` (общий с поездом) уровень растёт, опыт обнуляется.
- **Штаб.** 1 бесплатный призыв, после траты — следующий через 24 часа; без бесплатного призыв стоит
  250 золота. Выпадает один из 50 бустеров с рангом (I–X), рангом звёзд (I–X) и числом звёзд (1–5) по
  фиксированным таблицам `BoostSummonData`. Выпавший бустер хранится в штабе, пока игрок не примет
  (`/summonAccept`: заменяет параметры имеющегося бустера того же id или кладёт новый) или не продаст
  (`/summonRefuse`: 125 серебра). Повторный `/summon` при непринятом бустере возвращает тот же бустер
  без оплаты.
- **Бонус бустера** = `base` по рангу + значение по рангу звёзд и числу звёзд из листа бустера
  (`MB*BoostData[...]`). Бонус абсолютный: единицы добычи, ёмкости, вместимости или секунды.
- **Туториал базы**: 0 — купить уголь, 1 — собрать ресурсы, 2 — продать; после шага 2 — `-1`.
- **Уведомление** `militaryBase` горит, если есть бесплатный призыв, готовый самолёт, прибыль к
  получению, здание с буфером от 50% или доступное по деньгам улучшение.

<a id="references"></a>
## 2. Референсы

- ГДД [gdd-purpose](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-purpose) и его исходники `incoming/military-base-gdd.txt`, `incoming/military-base-fixes.txt`; таблица баланса — лист Google, загружается в
  `balance.json` (листы `MB*`).
- Производство самолёта повторяет призыв танка в поезде (`TrainUserComponent.receiveTank`,
  `getUpgradeDataJSON`) — [train-architecture.md](train-architecture.md).

<a id="patterns"></a>
## 3. Паттерны

- `UserChildComponent` с вложенными POJO (`MilitaryBaseStorage`, `MilitaryBaseAviationFactory`,
  `MilitaryBaseHeadquarters`): POJO отдают `dbToData`, компонент пишет их целиком через
  `changedField` (`dbStorageChanged` и т.п.) — граница персистентности как в
  `feedback_server_db_persistence_boundary`.
- Наследники `BagItem` с `onChangeField` по полям; регистрация в `ItemType`/`ItemFactory` (черновик
  `server_new_bagitem_component_page_draft`).
- Вычисляемые значения (`MilitaryBaseBuildingRate`, `MilitaryBaseBuildingCapacity`,
  `productionDuration` слота) в БД не хранятся и пересчитываются `recalculate*` после загрузки и после
  изменения уровней/бустеров.
- Табличные данные баланса — `KeyModel` + `Balance.mapping`; константы, не вынесенные в баланс, — в
  `MilitaryBaseData`, `BoostSummonData`, `BoostRouter`.

<a id="class-list"></a>
## 4. Список классов

Компонент и его части (`model/military_base/`): `MilitaryBaseUserComponent`,
`MilitaryBaseStorage`, `MilitaryBaseAviationFactory`, `MilitaryBaseHeadquarters`,
`MilitaryBaseBuildingRate`, `MilitaryBaseBuildingCapacity`.
Данные (`model/military_base/data/`): `MilitaryBaseData`, `BoostRouter`, `BoostSummonData`,
`MilitaryBaseBuildingData`, `MilitaryBaseStorageData`, `MilitaryBaseAviationFactoryData`,
`MilitaryBaseBoostData`.
Предметы сумки (`model/bag/military_base/`): `MilitaryBaseBuilding`,
`MilitaryBaseAviationFactorySlot`, `MilitaryBaseBoost`.
Страница: `MilitaryBasePage`.

В этой задаче классы не создавались и не менялись (первичный анализ).

<a id="anchors"></a>
## 5. Навигация (якоря)

| Якорь | Что там |
|---|---|
| [#cls-component](#cls-component) | `MilitaryBaseUserComponent` |
| [#m-payment](#m-payment) | доллары и доплата золотом |
| [#m-factory-exp](#m-factory-exp) | опыт и уровень авиазавода |
| [#m-hq](#m-hq) | призыв бустера в штабе |
| [#m-notification](#m-notification) | уведомление `militaryBase` |
| [#cls-storage](#cls-storage) | `MilitaryBaseStorage` |
| [#cls-factory](#cls-factory) | `MilitaryBaseAviationFactory` |
| [#cls-headquarters](#cls-headquarters) | `MilitaryBaseHeadquarters` |
| [#cls-rate](#cls-rate) | `MilitaryBaseBuildingRate`, `MilitaryBaseBuildingCapacity` |
| [#cls-data](#cls-data) | `MilitaryBaseData`, `BoostRouter`, `BoostSummonData`, листы `MB*` |
| [#cls-building](#cls-building) | `MilitaryBaseBuilding` |
| [#cls-slot](#cls-slot) | `MilitaryBaseAviationFactorySlot` |
| [#cls-boost](#cls-boost) | `MilitaryBaseBoost` |
| [#cls-page](#cls-page) | `MilitaryBasePage`, роуты |
| [#persistence](#persistence) | регистрация и персистентность |
| [#contract](#contract) | контракт с клиентом |
| [#tradeoffs](#tradeoffs) | уязвимости и проблемы |
| [#function-mapping](#function-mapping) | дубли функций (одно правило — одна функция) |
| [#implicit-order](#implicit-order) | переходы состояния у вызывающего |
| [#edge-cases](#edge-cases) | нестандартные действия игрока |
| [#fixes-status](#fixes-status) | статус документа «Правки» |

<a id="class-nav"></a>
## 6. Оглавление по классам

- [`MilitaryBaseUserComponent`](#cls-component)
- [`MilitaryBaseStorage`](#cls-storage)
- [`MilitaryBaseAviationFactory`](#cls-factory)
- [`MilitaryBaseHeadquarters`](#cls-headquarters)
- [`MilitaryBaseBuildingRate`, `MilitaryBaseBuildingCapacity`](#cls-rate)
- [`MilitaryBaseData`, `BoostRouter`, `BoostSummonData`, `*Data` листов](#cls-data)
- [`MilitaryBaseBuilding`](#cls-building)
- [`MilitaryBaseAviationFactorySlot`](#cls-slot)
- [`MilitaryBaseBoost`](#cls-boost)
- [`MilitaryBasePage`](#cls-page)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-component"></a>
### `MilitaryBaseUserComponent`

`model/military_base/MilitaryBaseUserComponent.java`. Поля: `storage`, `aviationFactory`,
`headquarters`, `tutorialProgress` (по умолчанию `-1`; `initStarter` ставит 0). Константы туториала
`TUTORIAL_BUY_COAL = 0`, `TUTORIAL_COLLECT_RESOURCES = 1`, `TUTORIAL_SELL_RESOURCES = 2`,
`TUTORIAL_FINISHED = -1`.

- `initStarter()` — стартовый набор: 1000 долларов, 10 бустеров-транспортов, туториал = 0. Зовёт
  `ActorInitializationTask`, когда сумка пустая. Правило ГДД: нет (как в коде).
- `recalculateBuildings()` — `recalculate` для зданий 1–10 и `onItemChanged` (клиент получает новые
  вычисляемые значения). Зовут `User.onInitialized`, `/upgradeStorage`, `/summonAccept`.
- `getDollarsPerHour(fallback)` — доход базы в час: сумма по построенным зданиям
  `amount × (час / interval) × price`; при нуле и `fallback` — 30600. Отдаётся клиенту
  (`dollarsPerHour`) и служит курсом доплаты золотом.
- <a id="m-payment"></a>`getGoldenCoinsCostForDollarsCost(cost)` — сколько золота стоит недостающая
  часть цены: `ceil(нехватка × 100 / getDollarsPerHour(true))`. Сам ничего не списывает; списание
  долларов и золота делает каждый роут `MilitaryBasePage` своей копией кода ([#function-mapping](#function-mapping) п.1).
- `completeTutorial(step)` — продвигает шаг, если текущий равен `step`; после шага 2 ставит `-1`.
- `recalculateAviationFactorySlots(applyActiveProductionDiff)` — пересчёт `productionDuration` слотов
  1–10 по времени производства завода и бустерам; с `true` сокращает и идущее производство (при
  принятии бустера). Ранний выход, если нет строки `MBAviationFactory` для уровня.
- `createAviationFactorySlotForBoost(boostId)` — для бустера слота создаёт слот в сумке, если его нет.
- `setStorageLevel(level)` — уровень склада + запись. Пересчёт зданий вызывающий делает отдельно
  ([#implicit-order](#implicit-order)).
- <a id="m-factory-exp"></a>`increaseAirplaneFactoryExp()` — +1 опыт; при `exp >= summonRequire`
  следующего уровня листа `SummonUpgrade` — уровень +1, опыт 0; на максимальном уровне ничего не
  делает; затем пересчёт слотов. Правило: [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) (правка 1.5); растёт ли уровень ещё и за доллары — [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open).
- `generateAirplane()`, `getAirplaneProductionCost()`, `getAirplaneProductionTime()`,
  `getAviationFactoryLevel()` — делегаты `MilitaryBaseAviationFactory`.
- `onAirplaneProductionStarted()` — счётчик производств +1, запись, пересчёт слотов.
- <a id="m-hq"></a>`hasHeadquartersSummons()`, `decreaseHeadquartersSummons()` — бесплатные призывы.
  `hasSummonedBoost()` — есть ли непринятый бустер. `summonBoost()` — возвращает непринятый бустер, а
  если его нет, генерирует новый и сохраняет в штабе (оплату не проверяет — [#tradeoffs](#tradeoffs) п.1).
  `clearBoost()` — убирает непринятый бустер.
- `tick()` — `productionTick` всех зданий и `headquarters.tick()` (возврат бесплатного призыва).
- <a id="m-notification"></a>`sendNotification()` — ставит или снимает уведомление
  `NotificationId.MILITARY_BASE` (условия — в [#purpose](#purpose)). Зовут `User` после загрузки и
  `User.onAuthorizedActive` на каждом авторизованном запросе.
- `getAviationFactoryInfoJSON()` — шансы рангов и звёзд на текущем и следующем уровне завода и
  «важные уровни», на которых откроется ближайший закрытый ранг/звёзды. Копия
  `TrainUserComponent.getUpgradeDataJSON` ([#function-mapping](#function-mapping) п.3).
- `apiResponse()` — `storage`, `aviationFactory` (+ `productionDurations` по слотам 1–10, считаются на
  шаблонных слотах), `headquarters`, `tutorialProgress`, `dollarsPerHour`.
- Тривиальные: `modifyReceiver` (пустой), `getStorageBaseCapacity`, `getStorageLevel`,
  `getTutorialProgress`, `dbMappingBuild` (ключи `st`, `af`, `hqrs`, `tpg`), приватные `db*Changed`,
  `has*Notification`.

<a id="cls-storage"></a>
### `MilitaryBaseStorage`

Уровень склада (`l`, по умолчанию 1). `getBaseCapacity()` — `capacity` строки `MBStorageData` уровня:
вместимость склада каждого ресурса до бустера. Остальное — геттер/сеттер, `apiResponse` (`level`),
`dbMappingBuild`/`dbToData`.

<a id="cls-factory"></a>
### `MilitaryBaseAviationFactory`

Уровень (`l`), опыт (`exp`), счётчик запусков (`productionCount`).

- `getProductionCost()` — 0 для первого производства, 100 до 20-го, дальше `productionCost` строки
  `MBAviationFactory` уровня. `getProductionTime()` — 30 с до 20-го, дальше `productionTime` строки.
  Строка берётся без проверки на `null` ([#tradeoffs](#tradeoffs) п.9).
- `generateAirplane()` — ранг по `SummonRankChances` уровня, случайная модель ранга из
  `Balance.getAirplanes(rank)` (без проверки на `null`/пустоту), ранг звёзд по
  `SummonStarsRankChances`, число звёзд — `AerodromeSummonData.getRandomStars()`; затем
  `recalculateParams`. Правило: [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) «та же механика призыва авиации». Копия
  `TrainUserComponent.receiveTank` ([#function-mapping](#function-mapping) п.3).
- Тривиальные: геттеры/сеттеры уровня и опыта, `increaseProductionCount`, `apiResponse`
  (`level`, `exp`, `productionCost`, `productionTime`), `dbMappingBuild`/`dbToData`.

<a id="cls-headquarters"></a>
### `MilitaryBaseHeadquarters`

Бесплатные призывы (`sm`, максимум `MAX_FREE_SUMMONS = 1`), время возврата (`st`), непринятый бустер
(`rcb`, документ предмета; пустой документ — нет бустера).

- `setSummons(n)` — при `n <= 0` ставит время возврата через `FREE_SUMMONS_TIME` (24 ч).
- `tick()` — по наступлении времени возвращает призывы до максимума и сбрасывает таймер; `true` —
  нужно записать.
- `generateBoost()` — случайный id из `BoostSummonData.BOOSTS` (равновероятно), ранг, ранг звёзд,
  число звёзд и вариант по таблицам `BoostSummonData`.
- `hasAvailableSummonNotification()` — есть призыв или таймер уже истёк.
- Тривиальные: `hasSummons`, `getSummons`, `receiveBoost`, `getReceivedBoost`, `clearReceivedBoost`,
  `apiResponse` (`summons`, `summonsTime`), `dbMappingBuild` (через `ItemFactory.newFromDocument` и
  приведение к `MilitaryBaseBoost`), `dbToData`.

<a id="cls-rate"></a>
### `MilitaryBaseBuildingRate`, `MilitaryBaseBuildingCapacity`

Пары «текущее/следующее» значение для клиента: скорость (`amount` за `interval`) и ёмкость
(`amount`). Только сеттеры, геттеры текущего значения и `apiResponse`
(`{current, next}`). В БД не пишутся.

<a id="cls-data"></a>
### `MilitaryBaseData`, `BoostRouter`, `BoostSummonData`, `*Data` листов

- `MilitaryBaseData` — константы: `BOOST_SUMMON_COST = 250` (золото), `BOOST_SELL_COST = 125`
  (серебро), `BUILDING_BUY_DATA` (цена/время стройки по зданию), `BUILDING_SELL_DATA` (цена ресурса,
  у всех 5; читает только `getDollarsPerHour`), `AVIATION_FACTORY_SLOTS` (1–10),
  `getSkipBuildingCost` (уголь 0, остальные 100), `getSkipAviationFactoryCost` (всегда 0),
  неиспользуемый `AviationFactorySlotData`. `apiResponse()` — справочник для `/balance`:
  `buildingBuyData`, `buildingSellData`, `storageData`, `aviationFactoryData` (лист `SummonUpgrade`),
  `aviationFactorySlotData` (лист `MBAviationFactory`), `buildingUpgradeData`.
- `BoostRouter` — связь «здание → бустер» для четырёх типов (добыча, логистика, склад, транспорт) и
  «слот завода → бустер»; `getAviationFactorySlotId(boostId)` — обратный поиск слота.
- `BoostSummonData` — список 50 бустеров призыва, веса рангов (`RANK_CHANCES`, сумма 100 000), веса
  рангов звёзд, веса числа звёзд (30/25/20/15/10), варианты внешнего вида для транспорта
  (`getVariantForRank` — вариант = индекс ранга). `getInfoJSON()` — шансы для `/headquartersInfo`.
  `getRandomBoostRank`, `getRandomBoostStarsRank`, `getRandomBoostStarsCount` — взвешенный выбор.
- `MilitaryBaseBuildingData` (`MBBuildingData`: уровень, добыча, ёмкость, цена),
  `MilitaryBaseStorageData` (`MBStorageData`: уровень, вместимость, цена),
  `MilitaryBaseAviationFactoryData` (`MBAviationFactory`: уровень, цена, время в секундах → мс),
  `MilitaryBaseBoostData` (5 листов бустеров: ранг, `base`, значения для 1–5 звёзд;
  `getStarValue(count)`; `apiResponse` пустой).

<a id="cls-building"></a>
### `MilitaryBaseBuilding`

Предмет сумки, id = ресурс (1 уголь … 10 уран). Хранимые поля: `bt` время окончания стройки, `pl`
уровень добычи, `ll` уровень ёмкости буфера, `pr` ресурсы в буфере, `sr` ресурсы на складе, `pt` время
следующего тика добычи, `sp` прибыль в пути, `st` время прибытия. Вычисляемые: `productionRate`,
`productionCapacity`, `storageCapacity`, `transportCapacity`.

- `isBuilt()` — стройка завершена (`bt == 0` или в прошлом).
- `recalculate(user)` — пересчёт вычисляемых полей по уровням, уровню склада и четырём бустерам здания
  (`getBoostAmount`). Скорость: `round((production + бустер)/6)` за 10 с; транспорт без бустера —
  10 000. Правила: [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings), [gdd-boosts](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-boosts), [gdd-storage](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-storage).
- `productionTick()` — накопление в буфер до ёмкости, навёрстывает пропущенные интервалы.
- `collectResources()` — перенос буфера на склад ресурса в пределах свободного места; если буфер был
  полон, таймер добычи стартует заново. `canCollectResources()` — буфер заполнен на 50% и есть место
  (для уведомления). Правило: ручного сбора в ГДД нет — механика отклонена ([gdd-rejected](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-rejected), [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings))
  ([#tradeoffs](#tradeoffs) п.12).
- `sellResources(amount)` — списывает со склада, ставит прибыль `amount × 5` и время прибытия
  `getSaleDuration`; отказ при `amount <= 0`, нехватке или идущей продаже. Правило:
  [gdd-storage](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-storage).
- `getSaleDuration(amount)` — 10 мин при полной загрузке транспорта, иначе 300–570 с шагом 30 с.
- `saleTick()` — по прибытии возвращает прибыль и обнуляет продажу. `hasSaleProfit()` — прибыль ждёт.
- Тривиальные: `createNew`, геттеры/сеттеры полей с `onChangeField`, `getProductionRate`,
  `getStorageResources`, `getTransportCapacityAmount`, `copy`, `apiResponse` (все поля и
  вычисляемые пары; `buildingTime` — только пока идёт стройка), `isStackable = false`,
  `onBagInsert` (только `super`), `dbMappingBuild`/`dbToData`, `getItemType`.

<a id="cls-slot"></a>
### `MilitaryBaseAviationFactorySlot`

Предмет сумки, id = номер слота 1–10. Хранимые поля: `pt` время готовности, `apd`/`abpd` длительность
и базовая длительность идущего производства, `rca` произведённый самолёт (документ `Airplane`).
Вычисляемые: `productionDuration`, `baseProductionDuration`.

- `isWorks()` — производство идёт (`pt` в будущем).
- `startProduction(time)` — запоминает длительности и ставит время готовности.
- `recalculateProductionDuration(user, baseDuration, applyActiveProductionDiff)` — длительность =
  база − бонус бустера слота в секундах, минимум 1 с; при `true` и идущем производстве сокращает
  оставшееся время на разницу. Правило: [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory), [gdd-boosts](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-boosts).
- `receiveAirplane(airplane)`, `getReceivedAirplane()`, `canReceiveAirplane()`,
  `clearReceivedAirplane()` (заодно обнуляет `apd`/`abpd`).
- Тривиальные: `createNew`, `getProductionTime`, `setProductionTime`, `getProductionDuration`, `copy`,
  `apiResponse` (`productionTime`, `productionDuration`, `airplane` или `null`),
  `dbMappingBuild` (самолёт через `ItemFactory` с приведением к `Airplane`), `dbToData`, `getItemType`.

<a id="cls-boost"></a>
### `MilitaryBaseBoost`

Предмет сумки, id 1–50 (`ItemId.MILITARY_BASE_BOOST_*`). Поля: `rank`, `stars` (ранг + число),
`variant` (внешний вид транспорта). `createNew` даёт ранг I и одну звезду I.

- `apiResponse()` — `rank`, `stars`, `variant` и `bonus {type, amount}`; тип — по `BoostRouter`:
  `production`, `logistics`, `storage`, `transport`, `aviationFactory`.
- Тривиальные: геттеры/сеттеры, `copy`, `isStackable = false`, `onBagInsert`, `dbMappingBuild`/
  `dbToData`, `getItemType`.

<a id="cls-page"></a>
### `MilitaryBasePage` (`/ingame/militaryBase`, `/ingame/military_base`)

Страница зарегистрирована в `WSRouter` под двумя путями. Все роуты работают в акторе игрока, то есть
последовательно. Ошибки отдаются без кода причины, кроме нехватки долларов.

| Роут | Вход | Что делает | Ответ |
|---|---|---|---|
| `""` | — | `tick`, состояние | `militaryBase` |
| `/balance` | — | справочник | `balance` |
| `/buyBuilding` | `buildingId`, `useGoldenCoins` | оплата, новое здание со стройкой; туториал 0 | `building`; `tutorial` — если пройден шаг 0 |
| `/skipBuilding` | `buildingId` | золото, конец стройки | `building` |
| `/upgradeProduction` | `buildingId`, `useGoldenCoins` | оплата, уровень добычи +1 | `building` |
| `/upgradeProductionCapacity` | `buildingId`, `useGoldenCoins` | оплата, уровень ёмкости +1 | `building` |
| `/sellResource` | `buildingId`, `amount` | отправка на продажу; туториал 2 | `tutorial` — если пройден шаг 2 |
| `/collectResource` | `buildingId` (0 — все) | сбор буферов; туториал 1 | `resources` (id зданий); `tutorial` — если пройден шаг 1 |
| `/takeProfit` | `buildingId` | доллары за прибывшую продажу | `rewards` |
| `/runFactory` | `slotId`, `useGoldenCoins` | оплата, самолёт в слот, таймер, квест `AERODROME_SUMMON`, запись в кодекс | `militaryBase` |
| `/skipFactory` | — | отключён: `slotId = -1`, всегда ошибка | — |
| `/checkFactory` | `slotId` | самолёт слота и заменяемый | `receivedAirplane`, `replaceableAirplane` |
| `/acceptAirplane` | `slotId` | серебро за заменяемый, `addAirplane`, очистка слота, опыт завода, квест `BETTER_AIRPLANE` | `rewards`, `militaryBase` |
| `/refuseAirplane` | `slotId` | серебро за самолёт, очистка слота, опыт завода | `rewards`, `militaryBase` |
| `/upgradeStorage` | `useGoldenCoins` | оплата, уровень склада +1, пересчёт зданий | `militaryBase` |
| `/summon` | — | бесплатный призыв, иначе 250 золота; бустер в штаб | `boost`, `current`, `militaryBase` |
| `/summonAccept` | — | бустер в сумку (или параметры в имеющийся), слот для бустера слота, пересчёт | — |
| `/summonRefuse` | — | бустер из штаба за 125 серебра | — |
| `/aviationFactoryInfo` | — | шансы завода | payload `getAviationFactoryInfoJSON` |
| `/headquartersInfo` | — | шансы штаба | payload `BoostSummonData.getInfoJSON` |
| `/tick` | — | `tick` | `militaryBase` |

Строки: `""` 54, `/balance` 63, `/buyBuilding` 70–148, `/skipBuilding` 150–182, `/upgradeProduction`
184–247, `/upgradeProductionCapacity` 249–313, `/sellResource` 315–355, `/collectResource` 357–392,
`/takeProfit` 394–426, `/runFactory` 428–516, `/skipFactory` 518–561, `/checkFactory` 563–598,
`/acceptAirplane` 600–657, `/refuseAirplane` 659–707, `/upgradeStorage` 709–763, `/summon` 765–807,
`/summonAccept` 809–830, `/summonRefuse` 832–846.

Изменения предметов сумки (здания, слоты, бустеры, доллары, серебро, золото) клиент получает обычным
путём сумки ([bag-architecture.md](bag-architecture.md)).

<a id="persistence"></a>
### Регистрация и персистентность

- `User`: поле и ленивый геттер `getMilitaryBaseUserComponent` (имя компонента `MilitaryBase`),
  загрузка из поля `MilitaryBase`, `modifyReceiver`, `sendNotification` после загрузки и на каждом
  авторизованном запросе, `onInitialized` — `recalculateBuildings` и `recalculateAviationFactorySlots`.
- `ActorInitializationTask` — `initStarter` при пустой сумке.
- `ItemType` (3, 4, 5) и `ItemFactory` — создание предметов базы из документов сумки.
- `Balance`/`BalanceImporter` — листы `MBBuildingData`, `MBStorageData`, `MBAviationFactory`,
  `MBBuildingBoostData[Production]`, `MBBuildingBoostData[Capacity]`, `MBStorageBoostData[Capacity]`,
  `MBStorageBoostData[Transport]`, `MBAviationFactoryBoostData[Production]`; общие листы `SummonUpgrade`,
  `SummonRankChances`, `SummonStarsRankChances`.

<a id="contract"></a>
### Контракт с клиентом

Роуты и ключи — в таблице [#cls-page](#cls-page); уведомление `militaryBase` — через
`NotificationComponent`. Сверка с клиентом — `integration-lead`, 2026-10-22:

- Совпадают: ответы `""`, `/tick`, `/balance`, `/summon`, `/checkFactory`, `/collectResource`; ошибка
  нехватки долларов с `missingDollars`/`goldenCoinsCost` и повтор с `useGoldenCoins`; поля здания и
  бустера; 50 id бустеров (`ItemId` 51/52 нет ни на одной стороне).
- Константы штаба и ускорения (250 золота за призыв, 125 серебра за продажу бустера, ускорение
  стройки 0 или 100 золота) совпадают, но в `/balance` не приходят: клиент держит свои копии.
- `/ingame/military_base` (`WSRouter.java:83-84`) — мёртвый алиас, клиент шлёт только `/ingame/militaryBase`.
- `MilitaryBaseStorageJSON.exp` клиент объявляет, сервер его не отдаёт (`MilitaryBaseStorage.apiResponse`
  отдаёт только `level`).
- `bonus` у бустера необязателен (`MilitaryBaseBoost.apiResponse`), сейчас заполнен у всех 50.
- Если игрок закрыл окно призыва, бустер остаётся в штабе до `/summonAccept` или `/summonRefuse`;
  повторный `/summon` возвращает его же.
- `productionTick` сдвигает `productionTime` на каждом прошедшем интервале, даже если буфер полон:
  таймер у клиента идёт и при остановленной добыче.
- Состояния завода для аэродрома ([gdd-aerodrome-view](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aerodrome-view), правка 1.6)
  клиент берёт из слотов в сумке, отдельного роута нет.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Статусы: баг — исправить; как в коде — ГДД молчит или расходится, решение за пользователем; открыто —
ждёт ответа пользователя. Приоритет — предложение аналитика.

Решение пользователя 2026-10-22: все баги и расхождения ГДД↔код ниже отложены, сейчас не чинятся
(список — `/workspace/client/.claude/memory/server_military_base_deferred_fixes.md`).

1. **Бесплатный бустер через `/summonAccept` без `/summon`.** Статус: баг, приоритет высокий.
   `actionSummonAccept` (`MilitaryBasePage.java:809-830`) не проверяет `hasSummonedBoost()`, а
   `summonBoost()` при пустом штабе генерирует новый бустер. Поддельный запрос `/summonAccept` в цикле
   даёт бустеры без оплаты, каждый раз новый; принятый бустер заменяет имеющийся без сравнения
   (сравнение — решение игрока на клиенте). Подтверждено `integration-lead`. Отложено пользователем
   2026-10-22.
2. **ГДД штаба расходится с кодом.** Статус: открыто. [gdd-headquarters](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-headquarters): цена призыва в долларах
   и растёт с уровнем штаба. В [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open): 3 бесплатных призыва каждые 12 ч и выбор 1 или
   10 призывов (не утверждены), способ роста уровня штаба. Код: 1 призыв раз в 24 ч, 250 золота, уровня штаба нет, призыв по одному.
3. **Покупка зданий в любом порядке.** Статус: открыто, приоритет средний. [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings): следующее место
   под здание появляется после покупки предыдущего. `/buyBuilding` проверяет только, что здания с
   таким id нет; поддельный запрос купит уран раньше угля.
4. **Состав бустеров.** Статус: открыто. [gdd-boosts](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-boosts): 52 бустера, включая общий бустер
   склада («Подземное хранилище») и общий бустер завода («Отдел ревизии»; снижает он цену или время —
   [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open)). В коде 50: общих бустеров нет,
   цену производства ничто не снижает.
5. **Бонусы бустеров абсолютные.** Статус: открыто. [gdd-boosts](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-boosts): бустеры зданий и хранения — «+N%»,
   фуры — «+N единиц» (единица общего бустера склада — [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open)). Код прибавляет
   фиксированные единицы и секунды из листов `MB*BoostData`.
6. **Улучшения мгновенные.** Статус: открыто. [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings), [gdd-storage](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-storage): каждое
   улучшение занимает N времени.
7. **Склад.** Статус: открыто. [gdd-storage](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-storage): что прокачивает уровень склада
   (общую вместимость или вместимость каждого ресурса) — [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open). В коде
   один уровень склада на все ресурсы, вместимость считается для каждого ресурса отдельно.
8. **Авиазавод: автозаполнение и ускорение.** Статус: открыто. [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory): кнопка автозаполнения
   всех слотов и ускорение сборки за доплату. Роута автозаполнения нет, `/skipFactory` отключён
   (`slotId = -1`), `getSkipAviationFactoryCost` возвращает 0.
9. **Строка баланса без проверки на `null`.** Статус: баг-риск, приоритет средний.
   `getProductionCost`/`getProductionTime` берут строку `MBAviationFactory` по уровню без проверки, а
   уровень завода идёт по другому листу (`SummonUpgrade`). Сейчас в обоих 20 уровней; если листы
   разойдутся, `apiResponse` и `/runFactory` упадут с NPE. То же у `generateAirplane`:
   `getAirplanes(rank)` без проверки (сейчас у всех 20 рангов есть самолёты). Отложено 2026-10-22.
10. **Кодекс пишется до решения игрока.** Статус: как в коде, приоритет низкий. `/runFactory` пишет
    самолёт в кодекс при запуске; проданный самолёт тоже там
    ([codex-architecture.md#producers](codex-architecture.md#producers)).
11. **Квест «призыв самолёта» засчитывается при запуске производства** (`AERODROME_SUMMON` в
    `/runFactory`); получение и продажа самолёта его не двигают. Статус: как в коде.
12. **Ручной сбор ресурсов и буфер здания.** Статус: открыто. [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings), [gdd-rejected](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-rejected): сбор
    автоматический, отдельного хранилища в здании нет, ручной сбор отклонён. В коде есть буфер здания, `/collectResource`,
    уведомление о сборе и шаг туториала «собрать ресурсы». Бустер логистики увеличивает ёмкость
    буфера; в ГДД второй бустер здания — «увеличение транспортировки».
13. **Первые 20 производств** — бесплатное первое, затем 100 долларов и 30 с (жёстко в коде). Статус:
    как в коде, в ГДД нет.
14. **Доплата золотом за нехватку долларов.** Статус: как в коде. [gdd-headquarters](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-headquarters), [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings),
    [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory): при нехватке долларов — окно покупки валюты (окна нет, [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open)); код позволяет докупить недостающие доллары золотом по
    курсу 100 золота за час дохода, при нулевом доходе — по запасному доходу 30 600 в час.
15. **Цена продажи ресурса задана дважды**: `sellResources` умножает на 5, `BUILDING_SELL_DATA.price`
    (тоже 5) читает только расчёт дохода. Статус: как в коде, приоритет средний: изменение таблицы не
    изменит реальную прибыль.
16. **Опыт завода и за продажу самолёта.** Статус: открыто. [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) (правка 1.5): опыт —
    «когда игрок забирает готовый самолёт». Код начисляет опыт и в `/acceptAirplane`, и в `/refuseAirplane`.
17. **`/skipBuilding` без проверки состояния стройки**: платит 100 золота и для уже построенного
    здания. Статус: баг, приоритет низкий; подтверждено `integration-lead`, отложено 2026-10-22. Ускорения стройки в ГДД нет (ускорение есть только у завода).
18. **`ItemType` 3/4/5 и старые документы сумки.** Статус: открыто (общий с коллекциями,
    `server_collections_deferred_fixes`). Коллекционные документы с `t=3` до merge amnesia/fix теперь
    читаются как `MilitaryBaseBuilding`; при id 1–10 такой документ станет «построенным» зданием.
    Числа `ItemType` на клиенте и сервере совпадают, конфликт возможен только в данных БД (тип берётся
    из `ordinal`, `ItemFactory` создаёт предмет по нему). Проверка — документы сумки с `t=3` без полей
    `bt`/`pl`.
19. **Туториал базы** (купить уголь, собрать, продать) в ГДД не описан. Статус: как в коде.
20. **Уведомление считается на каждом авторизованном запросе** (`User.onAuthorizedActive`): обход
    10 зданий и 10 слотов на любой запрос. Статус: как в коде, приоритет низкий.
21. **Добыча и возврат бесплатного призыва считаются только в `""` и `/tick`.** Уведомление при этом
    смотрит сохранённые значения: буфер, накопленный офлайн, не зажжёт уведомление до открытия базы.
    Статус: как в коде, приоритет низкий.
22. **Кандидаты на удаление**: `ItemId.RESOURCE_MILITARY_BASE_TOKENS` (не используется),
    `MilitaryBaseData.AviationFactorySlotData`, `MilitaryBaseBoostData.apiResponse` (пустой),
    `modifyReceiver` (пустой), переопределения `onBagInsert` (только `super`), `next` у
    `storageCapacity`/`transportCapacity` (всегда 0), второй путь страницы `/ingame/military_base`
    (клиент его не использует, [#contract](#contract)). Статус: как в коде, приоритет низкий.
23. **`AerodromeSummonData.getRandomStars` лежит в пакете аэродрома**, хотя после merge его зовёт только
    военная база ([#function-mapping](#function-mapping) п.2).

<a id="function-mapping"></a>
### Одно правило — одна функция (находки)

1. **Оплата долларами с доплатой золотом** скопирована в пять роутов (`/buyBuilding`,
   `/upgradeProduction`, `/upgradeProductionCapacity`, `/runFactory`, `/upgradeStorage`, по ~25 строк).
   Одно правило — одна функция у владельца долларов базы, например метод компонента «списать цену
   с доплатой золотом», возвращающий результат для ответа.
2. **Число звёзд 1–5 с весами 30/25/20/15/10** — четыре реализации: `AerodromeSummonData.getRandomStars`,
   `TrainSummonData.getRandomStars`, `BoostSummonData.getRandomBoostStarsCount`,
   `AlbumsSectionType.getRandomStars` (коллекции, своя реализация на процентах). Предложение: одна
   функция в общем Summon. Совпадает ли правило у всех источников — решает ГДД.
3. **Производство самолёта = призыв танка поезда**: `MilitaryBaseAviationFactory.generateAirplane` ≈
   `TrainUserComponent.receiveTank`, `getAviationFactoryInfoJSON` ≈ `TrainUserComponent.getUpgradeDataJSON`.
   [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) прямо называет это «той же механикой призыва». Предложение: общий Summon, параметризованный
   списком рангов и источником моделей.
4. **Бонус бустера** (база по рангу + значение звёзд) — три копии: `MilitaryBaseBuilding.getBoostAmount`,
   `MilitaryBaseAviationFactorySlot.getProductionBoostAmount`, `MilitaryBaseBoost.getBonusAmount`.
   Предложение: оставить одну функцию у `MilitaryBaseBoost`.
5. **Обход зданий 1–10** повторён в компоненте шесть раз и в `/collectResource`. Константа диапазона
   задана литералом `10`, хотя список зданий уже есть в `BUILDING_BUY_DATA`.

<a id="implicit-order"></a>
### Переходы состояния у вызывающего (WF `#no-implicit-order`)

Предложение для всех пунктов — метод-переход у владельца (`MilitaryBaseUserComponent` или предмет).

1. **Принять самолёт** (`MilitaryBasePage.java:600-657`): серебро за заменяемый + квест
   `SILVER_COINS_GAINED` + `addAirplane` + `clearReceivedAirplane` + `increaseAirplaneFactoryExp` +
   квест `BETTER_AIRPLANE` + `onBasicInfoUpdate`.
2. **Продать самолёт** (`:659-707`): серебро + квест + `clearReceivedAirplane` + опыт завода.
3. **Запустить производство** (`:428-516`): оплата + `generateAirplane` +
   `recalculateProductionDuration` + `startProduction` + `receiveAirplane` + `onAirplaneProductionStarted`
   + квест + кодекс; слот при отсутствии создаётся прямо в странице.
4. **Принять бустер** (`:809-830`): копирование ранга/звёзд/варианта или `add` +
   `createAviationFactorySlotForBoost` + `clearBoost` + `recalculateBuildings` +
   `recalculateAviationFactorySlots(true)`; проверка «бустер есть» отсутствует (п.1 [#tradeoffs](#tradeoffs)).
5. **Призыв** (`:765-807`): выбор способа оплаты + `decreaseHeadquartersSummons` + `summonBoost`.
6. **Покупка и ускорение здания** (`:70-182`): `createNew` + `setBuildingTime` + `setProductionTime` +
   `recalculate` + `addItem`; ускорение — `setBuildingTime(0)` + `setProductionTime`.
7. **Улучшения** (`:184-313`, `:709-763`): сеттер уровня + обязательный `recalculate`/
   `recalculateBuildings`; без пересчёта клиент и добыча получат старые значения.
8. **Шаги туториала** проверяются и продвигаются в трёх роутах страницы.

<a id="edge-cases"></a>
### Нестандартные действия игрока

| Действие | Поведение сервера |
|---|---|
| Двойное нажатие | запросы идут последовательно в акторе: второй `/runFactory` получает ошибку (слот занят), второй `/acceptAirplane`/`/refuseAirplane` — ошибку (слот пуст), второй `/summon` возвращает тот же бустер без оплаты, второй `/summonAccept` выдаёт ещё один бустер (п.1) |
| Закрытие окна до ответа | состояние сохранено: самолёт остаётся в слоте, бустер — в штабе до решения |
| Обрыв сети, две вкладки | один актор на игрока, гонок нет; вторая вкладка видит состояние после `""`/`/tick` |
| Фон | время идёт по часам сервера, добыча и продажа навёрстываются при следующем `/tick` |
| Подделка запроса | `/summonAccept` без призыва (п.1), покупка зданий вне порядка (п.3), `/skipBuilding` построенного здания (п.17); `amount` и `slotId` проверяются |

Поведение при двойном нажатии и закрытии окна ГДД не описывает — вопрос к ГДД.

<a id="fixes-status"></a>
### Статус документа «Правки»

| Правка | Сервер |
|---|---|
| §1.5 опыт завода за сбор самолёта | применена: опыт в `/acceptAirplane` и `/refuseAirplane`, в `/runFactory` нет (о продаже — п.16) |
| §1.6 состояния завода на аэродроме | серверной правки не требуется: состояние слотов (`productionTime`, `airplane`) клиент получает из сумки и `militaryBase`; отдельного роута нет — проверит `integration-lead` |
| §1.1–1.4, §2.1–2.16, §3.1 | только клиент |

Серверных правок, не найденных в коде, нет.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [military-base-gdd.md](/workspace/client/.claude/docs/game-design/military-base-gdd.md).

| Правило ГДД | Где реализовано |
|---|---|
| [gdd-purpose](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-purpose) цепочка ресурсы → продажа → доллары → самолёт | весь компонент |
| [gdd-headquarters](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-headquarters) штаб: бесплатные призывы, цена в долларах, уровень; 3 призыва/12 ч и 1/10 — [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open) | `MilitaryBaseHeadquarters`, `/summon*`; расходится (п.2) |
| [gdd-boosts](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-boosts) призы: качество, звёзды, качество звёзд; 52 бустера | `BoostSummonData`, `MilitaryBaseBoost`; 50 бустеров (п.4) |
| [gdd-boosts](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-boosts) назначение бустеров | `BoostRouter`, `MilitaryBaseBuilding.recalculate`, `MilitaryBaseAviationFactorySlot.recalculateProductionDuration`; проценты — п.5 |
| [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings) покупка здания, стройка с таймером, порядок мест | `/buyBuilding`, `isBuilt`; порядок не проверяется (п.3) |
| [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings) добыча раз в N секунд, прокачка добычи | `productionTick`, `/upgradeProduction` |
| [gdd-resource-buildings](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-resource-buildings), [gdd-rejected](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-rejected) сбор автоматический | расходится: ручной `/collectResource` (п.12) |
| [gdd-storage](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-storage) склад, продажа конвоем, один рейс на ресурс | `sellResources`, `saleTick`, `/takeProfit` |
| [gdd-open](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-open) прокачка склада: общая или по ресурсам | общий уровень (п.7) |
| [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) 10 слотов параллельно, время по уровню и бустерам | `MilitaryBaseAviationFactorySlot`, `getProductionTime` |
| [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) опыт завода при получении самолёта (правка 1.5) | `increaseAirplaneFactoryExp` |
| [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) автозаполнение, ускорение за доплату | не реализовано (п.8) |
| [gdd-aviation-factory](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aviation-factory) получение самолёта: выбор или продажа | `/checkFactory`, `/acceptAirplane`, `/refuseAirplane`; позиции — [aerodrome-architecture.md](aerodrome-architecture.md) |
| [gdd-aerodrome-view](/workspace/client/.claude/docs/game-design/military-base-gdd.md#gdd-aerodrome-view) аэродром без призыва, состояния завода (правка 1.6) | призыв удалён из аэродрома ([aerodrome-architecture.md](aerodrome-architecture.md)) |
| нет в ГДД | туториал базы (п.19), стартовый набор, первые 20 производств (п.13), доплата золотом (п.14) |

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от `game/src/main/java/com/linkedgames/game/`, кроме ресурсов.

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `model/military_base/MilitaryBaseUserComponent.java` | компонент: склад, завод, штаб, туториал, уведомление |
| `model/military_base/MilitaryBaseStorage.java` | уровень склада |
| `model/military_base/MilitaryBaseAviationFactory.java` | уровень/опыт завода, цена и время, генерация самолёта |
| `model/military_base/MilitaryBaseHeadquarters.java` | бесплатные призывы, непринятый бустер, генерация бустера |
| `model/military_base/MilitaryBaseBuildingRate.java` | вычисляемая скорость добычи |
| `model/military_base/MilitaryBaseBuildingCapacity.java` | вычисляемые ёмкости |
| `model/military_base/data/MilitaryBaseData.java` | константы цен, времени, справочник `/balance` |
| `model/military_base/data/BoostRouter.java` | связь зданий и слотов с бустерами |
| `model/military_base/data/BoostSummonData.java` | список бустеров и шансы призыва |
| `model/military_base/data/MilitaryBaseBuildingData.java` | строка `MBBuildingData` |
| `model/military_base/data/MilitaryBaseStorageData.java` | строка `MBStorageData` |
| `model/military_base/data/MilitaryBaseAviationFactoryData.java` | строка `MBAviationFactory` |
| `model/military_base/data/MilitaryBaseBoostData.java` | строка листов бустеров |
| `model/bag/military_base/MilitaryBaseBuilding.java` | здание в сумке |
| `model/bag/military_base/MilitaryBaseAviationFactorySlot.java` | слот завода в сумке |
| `model/bag/military_base/MilitaryBaseBoost.java` | бустер в сумке |
| `pages/ws/ingame/MilitaryBasePage.java` | роуты `/ingame/militaryBase` |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `model/user/User.java` | поле и геттер компонента, загрузка `MilitaryBase`, `sendNotification`, `onInitialized` |
| `model/user/tasks/ActorInitializationTask.java` | `initStarter` новому игроку |
| `pages/WSRouter.java` | регистрация `/ingame/military_base` и `/ingame/militaryBase` |
| `balance/Balance.java` | загрузка и геттеры листов `MB*` |
| `balance/BalanceImporter.java` | список листов `MB*` для импорта |
| `game/src/main/resources/balance.json` | листы `MBBuildingData`, `MBStorageData`, `MBAviationFactory`, `MB*BoostData[...]` |
| `model/item/ItemFactory.java` | создание предметов базы из документов |
| `model/notifications/NotificationId.java` | `MILITARY_BASE` |
| `pages/ws/ingame/dev/DevToolsPage.java` | dev-роут `/userDollars` |
| `model/aerodrome/AerodromeUserComponent.java` | `addAirplane`, `getReplaceableAirplane`, `getSilverCoinsReward` для принятия/продажи самолёта |
| `model/aerodrome/data/AerodromeSummonData.java` | `getRandomStars` для самолёта |
| `model/codex/CodexUserComponent.java` | запись произведённого самолёта |
| `model/quests/QuestEvent.java` | `AERODROME_SUMMON`, `BETTER_AIRPLANE`, `SILVER_COINS_GAINED` |
| `model/item/ItemType.java` | зависимость: `MILITARY_BASE_BUILDING`/`_AVIATION_FACTORY_SLOT`/`_BOOST` (3/4/5) |
| `model/item/ItemId.java` | зависимость: доллары, id зданий и бустеров |
| `model/Rank.java` | зависимость: `AIRPLANES`, `AIRPLANE_STARS`, `MILITARY_BASE_BOOSTS`, `MILITARY_BASE_BOOSTS_STARS` |
| `model/summon/data/SummonUpgradeData.java` | зависимость: порог уровня завода (общий Summon) |
| `model/bag/airplane/Airplane.java` | зависимость: самолёт в слоте, `createCodexEntry`, `getPower` |
| `model/bag/BagUserComponent.java` | зависимость: хранение предметов базы, `onItemChanged`, ресурсы |
| `model/train/TrainUserComponent.java` | образец призыва (копии логики, [#function-mapping](#function-mapping) п.3) |
