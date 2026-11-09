# Коллекции — архитектура (Collection / CollectionItem)

Пакет `com.linkedgames.game.model.collections`. Архитектурные пояснения живут здесь, не в javadoc
(см. [правило](#rule-no-reflection)); из кода на документ ссылок нет. Сверено с кодом 2026-10-19
(после слияния `origin/amnesia/fix` в `koba/collection`, не закоммичено; до слияния — 2026-10-13, `CollectionItem extends Item`).

**ГДД (общий с клиентом):** [collections-gdd.md](/workspace/client/.claude/docs/game-design/collections-gdd.md) —
правила не пересказываются, ссылки `ГДД: #gdd-…` у классов и механик.

Секции (`CollectionSection`):
- `USSR_OPERATIONS` (1) — альбомы: фото со звёздами, стадийные награды коллекции и секции, личный 90-дневный таймер.
- `EXPERIMENTAL_TANKS` (2) — монеты по нациям в тирах-коллекциях; сбор через дроп поезда, клейм комплекта по запросу клиента.
- `EXPERIMENTAL_AIRPLANES` (3) — есть в enum, типа секции НЕТ, см. [Секция без типа секции](#no-section-type).

Роуты разнесены по трём страницам, см. [Типы секций](#section-types). Принятые решения, которые не
пересматривать, — [TODO](#todo).

<a id="toc"></a>
## Оглавление

Разделы: [Референсы](#references) · [Паттерны](#patterns) · [Структура пакета](#package-structure) ·
[Persistence](#persistence-overview) ([сбор изменений](#persistence-fetch-changes), [загрузка](#persistence-loading)) ·
[Dev-tools](#dev-tools) · [Balance-модель монет](#balance-model-coins) · [Strategy](#strategy-sectionlist)
([синглтоны](#singletons), [секция без типа](#no-section-type), [типы секций](#section-types),
[порядок стадий](#reward-order), [таймер](#collection-timer)) · [Поток открытия поезда](#coin-accumulation-train-flow)
([ролл](#roll-section), [ответ summon](#summon-reply)) · [Клейм комплекта](#coin-set-conversion-economy)
([отложенный танк](#pending-tank)) · [События клиенту](#event-mechanism)
([нотификация](#reward-notification)) · [Принцип записи в БД](#db-write-principle-check) ·
[Компромиссы](#tradeoffs-and-known-issues) · [TODO](#todo) · [Карта файлов](#file-map) · [Смежная документация](#related-docs)

| Класс | Где описан |
|---|---|
| `CollectionUserComponent` | [ссылка](#class-collectionusercomponent) |
| `Collection` (abstract) | [ссылка](#class-collection) |
| `CollectionAlbum` | [ссылка](#class-collectionalbum) |
| `CollectionExperimentalTank` | [ссылка](#class-collectionexperimentaltank) |
| `CollectionItem` | [ссылка](#class-collectionitem) |
| `CollectionSectionType` (abstract) | [ссылка](#strategy-sectionlist) |
| `AlbumsSectionType` | [ссылка](#class-albumssectiontype) |
| `ExperimentalTanksSectionType` | [ссылка](#class-experimentaltankssectiontype) |
| `CollectionEntry` + `CollectionAlbumEntry`/`CollectionExperimentalTankEntry` | [ссылка](#class-collectionentry) |
| `CollectionSectionEntry` + `AlbumsSectionEntry`/`ExperimentalTanksSectionEntry` | [ссылка](#class-collectionsectionentry) |
| `CollectionItemEntry` | [ссылка](#class-collectionitementry) |
| `CollectionsData`/`CollectionItemData`, `CollectionSection` | [Balance-модель](#balance-model-coins), [структура](#package-structure) |
| Внешние точки: `CollectionPage`, `CollectionExperimentalTankPage`, `CollectionAlbumPage`, `TrainPage`, `DevToolsPage`, `TrainUserComponent` | [типы секций](#section-types), [поезд](#coin-accumulation-train-flow) |

<a id="references"></a>
## Референсы

Все внутрипроектные:
- **`CodexEntry`/`CodexTankEntry`** — наследование записей с типизированными полями поверх abstract-формы; образец для `CollectionEntry`/`CollectionSectionEntry`.
- **`BagItem`/`AchievementEntry`** — condition-флаги `NEW`/`DELETED`, `dbFetchChanged()` строит батч `WriteModel`; образец для `CollectionItemEntry`.
- **`Resource`** — один класс на все виды ресурсов (вид — в данных); образец для единого `CollectionItem`.
- **`ItemFactory`** — `ImmutableMap<Enum, Supplier<T>>` без рефлексии, см. [правило](#rule-no-reflection).
- **`TrainUserComponent.receiveTank()`** — пайплайн выдачи танка (ранг/уровень/звёзды + `recalculateParams()`).
- **`AchievementUserComponent.sendNotification()`** — образец [нотификации](#reward-notification).
- **`EventEmitter`/`UserEmitterId`** (`User.getEventEmitter()`) — событие "коллекция заполнена", см. [События](#event-mechanism).
- Клиентская сторона — [Смежная документация](#related-docs).

<a id="patterns"></a>
## Использованные паттерны

- **Strategy на двух уровнях**: `CollectionSectionType` (вся секция) и `Collection` (одна коллекция), у каждого по две реализации (альбомы/танки). Принцип выноса в абстрактный класс — в [Strategy](#strategy-sectionlist).
- **Ленивая фабрика + единственный ковариантный гетер записи** (`createEntry()`/`getTypedEntry()`), см. [Persistence](#persistence-overview).
- **Синглтоны на пользователя** через `ImmutableMap`, см. [Синглтоны](#singletons).
- **Полиморфизм без рефлексии**, см. [правило](#rule-no-reflection).
- **Маршрутизация по форме документа** (`cid`/`collectionId`/`sectionId`) вместо поля-дискриминатора, см. [Загрузка](#persistence-loading).
- **Один класс вместо иерархии**, когда поведение идентично, а различается контент — `CollectionItem`.
- **Publisher/Subscriber через `User.getEventEmitter()`** (решение пользователя): задел для будущих подписчиков (квесты/ачивки); bespoke `CollectionEventDispatcher` отклонён. Не пересматривать.

<a id="package-structure"></a>
## Структура пакета

```
model/collections/
├── CollectionUserComponent.java   — диспетчеризация + агрегация персистентности
├── data/                          — Balance-модель (не персистентная): CollectionsData (id/name/section),
│                                    CollectionItemData (id/name/collectionId/country)
├── enums/CollectionSection.java   — USSR_OPERATIONS(1)/EXPERIMENTAL_TANKS(2)/EXPERIMENTAL_AIRPLANES(3);
│                                    valueOf(int) — null для неизвестного значения
├── collectionsEntry/              — персистентные записи (collectionEntry/, sectionEntry/, collectionItemEntry/)
├── collectionList/                — Collection (abstract), CollectionAlbum, CollectionExperimentalTank
├── sectionList/                   — CollectionSectionType (abstract), AlbumsSectionType, ExperimentalTanksSectionType;
│                                    секционные константы и алгоритмы (стадии, шансы, награды) — здесь
└── itemList/CollectionItem.java   — один класс на фото и монеты (extends Item, не BagItem)
```

Отдельных классов событий нет (пустой каталог `event/`), см. [События клиенту](#event-mechanism).
`collectionList` и `sectionList` зеркалируют клиентские `Collection.ts`/`CollectionsTypeSection`.

<a id="class-collectionusercomponent"></a>
### `CollectionUserComponent`

`UserChildComponent`, один на пользователя, точка входа фичи. Бизнес-формул не содержит. Серверного
состояния "текущая открытая секция" нет (навигация — на клиенте).

- Конструктор — подписка на `COLLECTION_COMPLETED_ID` ([События](#event-mechanism)) и `buildSectionTypes()` ([Синглтоны](#singletons)).
- `hasSectionType`/`getSectionType` (`null` для секции без типа)/`getCollection(id)` (`null` для неизвестного id и коллекций секции без типа) — диспетчеризация.
- `getAlbumsSectionType(section)` — [Типы секций](#section-types); `rollDropSectionType()` — [Ролл секции](#roll-section); `receiveSummonedItem(item)` — [Ответ summon](#summon-reply); `refreshState()` — [Таймер](#collection-timer); `sendNotification()` — [Нотификация](#reward-notification).
- `grantReward(reward)` — единственная выдача награды коллекций: `BagComponent.add` + квест `SILVER_COINS_GAINED`, если серебро (`Item.getCount()` — `long`, в `triggerEvent(int)` идёт `(int) reward.getCount()`, решение пользователя; ГДД #gdd-ops-rewards, #gdd-exp-duplicate). Зовут дубликаты, альбомные награды, золото и серебро танков.
- `addDuplicateReward(item): BagItem` — `getCollection(item.data().collectionId).createDuplicateReward(item)` → `grantReward`.
- Добавления предмета на компоненте нет: `getSectionType(section).addItem(item)` (`true` = предмет новый/лучше).
- `sectionInfoApiResponse(section)` — `{section, sectionEndTime?}` (время только у `AlbumsSectionType`); `apiResponse()` — `{collectionsList: [...]}` по `sectionTypes.keySet()` (секции без типа нет); `sectionApiResponse(section)`/`sectionProgressApiResponse(section)` — делегаты к `apiResponse()`/`progressApiResponse()` секции (второй — роут `/getSectionProgress`).
- `DEV_*` — [Dev-tools](#dev-tools); `dbFetchChanged()`/`commitDbUpdates()` — [сбор изменений](#persistence-fetch-changes); `dbMappingChildBuild(documents)` — [Загрузка](#persistence-loading). `dbMappingBuild` не переопределён: собственных полей в документе пользователя нет (старое поле `"ss"` игнорируется).

<a id="persistence-overview"></a>
## Persistence: плоские списки записей в одной Mongo-коллекции

Три уровня иерархии — три вида записей, каждая — отдельный документ (`_id` = свой `ObjectId`, `ownerId`) в
Mongo-коллекции `collections` (`CollectionDao`). `changedField` не используется: `Collection`/
`CollectionSectionType` — не `Component`, у каждого локальный dirty-флаг.

<a id="class-collectionitementry"></a>
- **`CollectionItemEntry`** — владение одним предметом: `collectionItemId` (`cid`) + `stars`. Не abstract. Растущий/убывающий список → условия `NEW`/`DELETED`/`UPDATED` (`INTERNAL_CONDITION_UPDATED` = `1<<2`); `NEW+DELETED` выкидывается без записи. Инвариант: 1 `cid` = 1 запись = 1 документ.
  `updateState(Stars)` — единственный переход «принадлежит игроку с этими звёздами»: снимает `DELETED`, меняет звёзды, ставит `UPDATED`, если запись не `NEW`. `markDeleted()` — обратный переход, запись удаляется при сохранении. `Collection` флаги напрямую не ставит (`agent-system-workflow.md#no-implicit-order`). Переход на `BagItem` отклонён (решение пользователя). Индекс `{ownerId: 1}` (не уникальный) — `migrations/1791190438943_collections.json`.
<a id="class-collectionentry"></a>
- **`CollectionEntry`** — abstract `uid`/`collectionId`; наследники переопределяют `dbMappingBuild`/`dbToData` с `super` первой строкой: `CollectionAlbumEntry` (+`rewardedStage`), `CollectionExperimentalTankEntry` (+`everCompleted`, `notified` — `getBoolean(…, false)`; +`pendingTank` — вложенный документ, [Отложенный танк](#pending-tank)). Одна запись на коллекцию, только обновляется — dirty-флаг вместо `NEW`/`DELETED`.
<a id="class-collectionsectionentry"></a>
- **`CollectionSectionEntry`** — то же на уровне секции: abstract `uid`/`sectionId`/`selected` (ключ `"sel"`, дефолт `true` и в памяти, и для старых документов). `AlbumsSectionEntry` (+`sectionRewardedStage`/`sectionEndTime`), `ExperimentalTanksSectionEntry` (полей нет, никогда не dirty — [Принцип записи](#db-write-principle-check)).

В отличие от `CodexEntry`, `getType()` и фабрика записей не нужны: владелец записи известен при загрузке, тип создаёт он сам:
- `createEntry()` — `protected abstract` фабрика (только создаёт), у каждого из 4 наследников `Collection`/`CollectionSectionType` возвращает свой Entry.
- `entry` — `protected` поле, наследник кэширует без посредников.
- `getTypedEntry()` — `public abstract`, **единственный гетер записи** (правило проекта); наследники переопределяют с ковариантным типом и лениво создают через `createEntry()`. Entry — единственный источник истины для своих полей. У `ExperimentalTanksSectionType` гетер нужен только базовому `isSelected()`.
- `fetchOwnEntryChange()` читает `entry` напрямую: `markAsDirty()` всегда вызывается после записи через `getTypedEntry()`, так что `entry != null`.

<a id="persistence-fetch-changes"></a>
### Сбор изменений — каждый тип секции свою часть

`CollectionUserComponent.dbFetchChanged()` конкатенирует `fetchEntryChanges()` всех секций (пусто → `null`; результат кэшируется до `commitDbUpdates()`). `CollectionSectionType.fetchEntryChanges()` (`final`) собирает:
1. свою `CollectionSectionEntry`, если dirty (upsert);
2. `CollectionEntry` каждой коллекции секции (`Balance.getCollectionsDataList(section)`), если dirty (upsert);
3. предметы (`Collection.fetchItemEntryChanges()`): `DELETED` → `DeleteOneModel` (если не `NEW`) + удаление из списка и условный `itemsEntryMap.remove(cid, entry)`; `NEW`/`UPDATED` → upsert `$set`, флаги снимаются.

`markAsDirty()` (`protected final` на `Collection` и `CollectionSectionType`) ставит локальный флаг. Вызывают: `CollectionAlbum.takeReward()`/`DEV_reset()`, `CollectionExperimentalTank.markEverCompleted()`/`setNotified()`/`setPendingTank()`/`clearPendingTank()`/`DEV_reset()`, `AlbumsSectionType.takeSectionReward()`/`resetSectionState()`/`refreshSection()`, `CollectionSectionType.setSelected()`.

<a id="persistence-loading"></a>
### Загрузка: `dbMappingChildBuild` маршрутизирует по форме документа

`CollectionDao.findByOwnerId` отдаёт все документы пользователя плоским списком. Для каждого:
- есть `cid` → `Balance.getCollectionItemData(cid).collectionId` → `getCollection(...).addEntryFromDb(document)`;
- есть `collectionId` → `getSectionType(section).applyCollectionEntryFromDb(collectionId, document)` (кэш в `entry` коллекции и регистрация в `collectionsEntry`/`collectionsEntryMap` секции);
- есть `sectionId` → `getSectionType(...).applyOwnEntryFromDb(document)`.

Поля не пересекаются, `containsKey` однозначен. Документы с неизвестным id/секцией и все записи секции без типа пропускаются. Кэш в `entry` нужен, чтобы последующие записи обновляли тот же документ (тот же `uid`).
Дубли `cid` в БД (наследие прежней схемы) `Collection.addEntryFromDb` сводит: остаётся запись с большим `Stars.getId()`, остальные `markDeleted()` и удаляются обычным сохранением.

<a id="class-collection"></a>
## `Collection` (collectionList/)

Абстрактный родитель альбома и карточки монет. Поля `id`, `user` (`protected final User`, не компонент: всё нужное — уровня `User`: `getBagComponent()`, `getEventEmitter()`, `getTrainComponent()`, `id`); конструктор package-private, у наследников `public`. То же у `CollectionSectionType`.

- `data()` (protected) — `Balance.getCollectionsData(id)`; `isCompleted()`/`hasAvailableReward()` — `public abstract`, формула у наследника.
- `DEV_reset()`/`DEV_addRandom()`/`DEV_addBest()` (`null` = нечего выдать)/`DEV_fill()` — `public abstract`, только создают предметы; хелпер `pickRandomMissingItemData()` — [Dev-tools](#dev-tools).
- Владение (`itemsEntry`/`itemsEntryMap`): `hasItem`/`getOwnedStars(itemId)` (`DELETED` считаются отсутствующими; `null` если нет).
- `addItem(item): boolean` — текущие звёзды ≥ новых → `false` (дубликат, продажу делает вызывающий); иначе улучшение или восстановление `DELETED`-записи (`existing.updateState(stars)`); `NEW` создаётся, только если `cid` нет в карте; затем при `isCompleted()` — `emit(COLLECTION_COMPLETED_ID, id)`; возвращает `true`.
- `removeAllItems()` — `markDeleted()` у каждой записи (обмен комплекта, `DEV_reset`).
- `createDuplicateReward(item): BagItem` — `public abstract`, только создаёт награду (выдаёт `CollectionUserComponent.addDuplicateReward`). В абстрактный класс выносятся только методы с содержательным ответом у всех наследников.
- `takeReward(): BagItem` — `public abstract`: коллекция сама по сохранённым флагам определяет, положена ли награда, формирует её и ставит флаг/`markAsDirty()`; страница только валидирует, выдачу делает секция (`grantReward`). `null` — награды нет (`CollectionExperimentalTank` вызывается только после проверки `isCompleted()` страницей).
- Персистентность (`createEntry()`/`getTypedEntry()`/`markAsDirty()`/`applyOwnEntryFromDb()`/`fetchOwnEntryChange()`/`addEntryFromDb()`/`fetchItemEntryChanges()`) — [Persistence](#persistence-overview).
- `apiResponse()`/`fullApiResponse()` — abstract (клиентские типы в `collection.d.ts`).

<a id="class-collectionalbum"></a>
### `CollectionAlbum`

> ГДД: [gdd-ops-albums](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-albums), [gdd-ops-upgrade](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-upgrade), [gdd-ops-rewards](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-rewards)

- `getCollectionStars()` — сумма звёзд собранных; `getMaxStars()` — `кол-во предметов × Rank.COLLECTION_ITEM_STARS.size()`; `isCompleted()` — `stars >= maxStars`.
- `getRewardedStage()`; `isCollectionStageCompleted(stage)` — звёзды ≥ `AlbumsSectionType.COLLECTION_STAGE_STARS[stage]`; `isCollectionStageRewarded(stage)` — `rewardedStage > stage`; `isCollectionStageRewardAvailable(stage)` — пройдена и не выдана (единственное выражение правила #gdd-ops-rewards); `hasAvailableReward()` — есть такая стадия.
- `takeReward()` — стадия `getTypedEntry().getRewardedStage()`; не пройдена → `null`; иначе `rewardedStage = stage + 1`, `markAsDirty()`, возвращает `STAGE_REWARD_GOLD` (1 золото).
- `createDuplicateReward(item)` — серебро по звёздам из `DUPLICATE_ITEM_PRICE_FROM_STARS` (значения — ГДД #gdd-ops-upgrade).
- `resetRewardedStage()` (`private`) — `rewardedStage = 0` (dirty, если был ≠ 0); только из `DEV_reset()`. При перезапуске сезона награды НЕ сбрасываются ([Таймер](#collection-timer)).
- `apiResponse()` — `id/stars/maxStars/rewardedStage/hasAvailableReward/completed`; `fullApiResponse()` — плюс `name/stages/items` (`null` для несобранных).

<a id="class-collectionexperimentaltank"></a>
### `CollectionExperimentalTank`

> ГДД: [gdd-exp-coins](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-coins), [gdd-exp-duplicate](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-duplicate), [gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward), [gdd-exp-tank](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-tank)

Не копия альбома: звёзд коллекции и стадий нет.
- `isCompleted()` — владение каждым предметом (звёзды не важны); `hasAvailableReward()` = `isCompleted() || hasPendingTank()` (клейм — [отдельный запрос](#coin-set-conversion-economy)).
- `getCountry()` — нация первого предмета (все монеты тира одной нации).
- `isEverCompleted()` — «танк за комплект получен» (прогресс X/8); `markEverCompleted()` — `private`, снаружи только через `markRewardReceived()`.
- `isNotified()`/`setNotified(b)` — [Флаг](#coin-new-flag); `getPendingTank()`/`hasPendingTank()` — публичные; `setPendingTank`/`clearPendingTank` — `private`, снаружи только через `takeReward()`/`markRewardReceived()` ([Отложенный танк](#pending-tank)).
- `takeReward()` — `createCompletionReward(false)`; `Tank` кладёт в `pendingTank` (без `everCompleted`), золото возвращает без отложенного состояния. ГДД #gdd-exp-reward.
- `markRewardReceived()` — решение по танку принято: `clearPendingTank()` + `markEverCompleted()` (ранняя запись не нужна: повторный сбор до решения невозможен из-за `hasPendingTank()`).
- `createCompletionReward(isTemplate)` (`private`) — `isEverCompleted()` → `createExperimentalTankDefaultReward`, иначе `createExperimentalTankReward`; нужен и `takeReward()` (`false`), и превью `reward` (`true`).
- `createDuplicateReward(item)` — серебро `DUPLICATE_ITEM_PRICE = 10` независимо от звёзд (ГДД #gdd-exp-duplicate). Сумма продублирована константой, а не берётся из `TrainUserComponent.getSilverCoinsReward` (решение пользователя, [компромисс 3](#tradeoffs-and-known-issues)). Тот же метод даёт награду за дубликат при клейме.
- `DEV_*` — [Dev-tools](#dev-tools).
- `apiResponse()` = `fullApiResponse()`: `id/name/hasAvailableReward/country` (`ordinal`)/`rank`/`notified`/`hasPendingTank`/`everCompleted`/`reward`/`tank`/`items` (`null` = монета не собрана).
  - `everCompleted` клиент использует для прогресса нации (#gdd-exp-reward), не только для выбора шаблона награды.
  - `reward` (`rewardApiResponse()`): `hasPendingTank()` → `getPendingTank().apiResponse()` (реальный танк с `level`/`stars`); иначе `createCompletionReward(true)` — шаблон, у танка `level`/`stars` удалены через `tankTemplateApiResponse` (определяются при выдаче).
  - `tank` — отдаётся ВСЕГДА: шаблон танка-награды `createExperimentalTankReward(id, true)` без `level`/`stars`. Нужен, чтобы клиент рисовал превью танка в строке набора с отметкой «Танк получен», когда `reward` уже золото (`CollectionExperimentalTank.UIRewardItem`).
  - `rank` (1..8) — ранг тира коллекции целиком, не зависит от собранности (клиенту для `collection_coin_icon` пустых слотов); `findExperimentalTankRank(id)` с fallback `1`.

<a id="coin-new-flag"></a>
#### Флаг "новая монета" (`notified`)

Нотификатор вкладки нации на клиенте. Хранится в `CollectionExperimentalTankEntry.notified` (уровень одной коллекции), в JSON — ключ `"notified"`. `setNotified` пишет в БД только при реальном изменении.

- **Ставится** в `ExperimentalTanksSectionType.addItemToCollection(item)` (override): только если монеты не было (`!hasItem`) И `addItem` вернул `true` (улучшение звёзд не ставит). Входы — через `CollectionSectionType.addItem`: дроп поезда, `/collectionSummon` и все dev-выдачи (решение пользователя 2026-09-30).
- **Не ставится** (решение пользователя): монета следующего ранга в `convertSetCoins` (кладётся прямым `Collection.addItem`, мимо секции).
- **Сбрасывается**: `DEV_reset()`; `convertSetCoins` после `removeAllItems()`; роутом `/ingame/collections/experimentalTank/markCollectionItemViewed {country}` (специфичен для танков, `section` не передаётся — решение пользователя 2026-10-01). `country` — индекс в `Country.ALL`, иначе `error()`; вызывает `ExperimentalTanksSectionType.markCountryViewed(Country)` (`setNotified(false)` у всех коллекций нации, затем push `sectionUpdated` без нотификации), ответ — пустой `ok()`.

<a id="dev-tools"></a>
### Dev-tools коллекций (`DEV_*`)

> ГДД: [gdd-ops-upgrade](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-upgrade), [gdd-ops-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-drop), [gdd-exp-coins](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-coins)

Роуты `DevToolsPage` → `CollectionUserComponent.DEV_*` → базовый `CollectionSectionType.DEV_*` (`final`) → `Collection.DEV_*`: `/collectionAddItem` → `DEV_addRandom`; `/collectionAddBestItem` → `DEV_addBest`; `/collectionFillMax` → `DEV_fill`; `/collectionSectionFillMax` → `DEV_fill` каждой коллекции; `/collectionReset` → `DEV_reset`; `/collectionSectionReset` → `DEV_reset` каждой + `resetSectionState()`. Ответы всех dev-роутов коллекций — пустой ok; перерисовку клиент делает по push `collectionUpdated`/`sectionUpdated`. `/collectionSummon` — отдельный путь ([Ролл](#roll-section)), не `DEV_*`.

Правила (решение пользователя 2026-09-30):
- `Collection.DEV_*` только создают предметы; в игру их добавляет базовая секция через `addItem` полным игровым путём ([флаг `notified`](#coin-new-flag), `COLLECTION_COMPLETED_ID` → push `setCompleted`), как дроп с поезда. Квестов на добавление предмета нет, dev-выдача дубликатов не создаёт.
- Выдаётся только неполученное; нечего выдать — no-op.
- Танки: монета = ранг тира (`findExperimentalTankRank`, fallback 1), 1 звезда (`createCoin`); `DEV_addBest` = `DEV_addRandom`.
- Фото (`createPhoto`, `Rank.I`): `DEV_addRandom` — случайное недостающее со звёздами `getRandomStars()`; `DEV_addBest` — случайное среди недостающих и имеющихся ниже 5★, выдаётся 5★; `DEV_fill` — все ниже 5★ → 5★.
- `DEV_reset`: альбом — `removeAllItems()` + `resetRewardedStage()`; танки — `removeAllItems()`, `setNotified(false)`, `clearPendingTank()`, сброс `everCompleted` (dirty, только если был `true`).

<a id="balance-model-coins"></a>
## Balance-модель монет (`section = EXPERIMENTAL_TANKS`)

> ГДД: [gdd-exp-coins](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-coins), [gdd-exp-quality](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-quality)

Тир нации — строка `CollectionsData` с `section = EXPERIMENTAL_TANKS` и до 6 строк `CollectionItemData` одной нации. Данные: 8 наций × 8 тиров × 6 монет (id коллекций 10..73; альбомы — 9 × 9 фото). Ранг ↔ коллекции — `ExperimentalTanksSectionType.EXPERIMENTAL_TANK_RANG_COLLECTION` (ранг → id коллекций по нациям), обратный лукап `findExperimentalTankRank(id)`. Шансы ранга по уровню поезда — `EXPERIMENTAL_TANK_RANK_CHANCES` (таблица значений — ГДД #gdd-exp-quality): ключ — уровень поезда, С которого действует строка. `stars` монеты — ранг качества (1 звезда с рангом тира), суммарного показателя нет.

Доменные формулы живут в Strategy/`Collection` (макс. звёзд альбома — `CollectionAlbum.getMaxStars()`, нация — `CollectionExperimentalTank.getCountry()`); в `Balance` — только сырой лукап (`getCollectionsData`, `getCollectionsDataList`, `getCollectionItemData`, `getCollectionItems`, `getCollectionSectionItems`).

<a id="class-collectionitem"></a>
## `CollectionItem` (itemList/) — один коллекционный предмет

Фото и монеты — ОДИН класс (не abstract, без наследников), решение пользователя: поведение идентично, различие в данных (как `Resource`). **Принцип**: поведение, специфичное виду предметов (в т.ч. будущим самолётам), живёт в наследниках `Collection`, а не в подклассах `CollectionItem`.

- `stars: Stars` — у фото 1–5, у монет ранг качества; `setStars(rank, count)` только меняет `stars`, `onChangeField` не вызывает.
- `data()` — `Balance.getCollectionItemData(getId())`; `getItemType()` = `COLLECTION_ITEM` (ordinal 6, последний в `ItemType` после трёх `MILITARY_BASE_*`), `ItemFactory` — `CollectionItem::new`; `ItemFactory.newFromDocument` теперь возвращает `null` для неизвестного `t`.
- `createNew(CollectionItemData)` — единственная фабрика (без `isTemplate`); вид определяется переданными данными.
- `count` (поле `Item`) — `long` после слияния; у коллекционного предмета всегда 1, `Item.dbMappingBuild` читает и старый `int`, и `long`.
- `apiResponse()` — поля `Item` (`id`/`itemType`/`count`) + `stars/name/collectionId/country` (`ordinal`).
- Родитель — `Item`, не `BagItem`: нет `uid`, `isStackable`, `copy()`. `uid` в `apiResponse` не отдаётся; клиентский `CollectionItemJSON extends ItemJSON` его и не ждёт. `dbToData` без `_id`; старые документы `rci` с `_id` читаются (поле игнорируется).
- Экземпляры транзитны (дроп/показ игроку, построение `CollectionItemEntry`), в сумке не хранятся; владение — [`CollectionItemEntry`](#class-collectionitementry). Исключение — незабранный дроп в `TrainUserComponent.receivedCollectionItem` (поле `rci`).

<a id="strategy-sectionlist"></a>
## Strategy: `sectionList/` — диспетчеризация по типу секции

`CollectionSectionType` (abstract) — минимальный общий контракт:
- `progressApiResponse()` (abstract) — шапка секции без списка коллекций; `apiResponse()` — `final`: `progressApiResponse()` + `collections`. О перезапуске сезона сообщает `sectionRestarted {section}`.
- abstract: `getCollection(id)` (из собственной карты, [Синглтоны](#singletons)), `createRandomDropItem()`, `resetSectionState()` (`DEV_resetSection`, сброс стадий альбома), `getCollectionDropChance()` (альбомы `2`, танки `8`), `createEntry()`/`getTypedEntry()`.
- `isSectionActive()`/`refreshSection()` — абстрактные: идёт ли сезон и его актуализация; `isSectionActive()` — условие участия в ролле ([Таймер](#collection-timer), [Ролл](#roll-section)).
- **Слой операций секции** (ГДД #gdd-ops-rewards, #gdd-exp-reward): роуты и компонент коллекции не мутируют; мутирует и шлёт события секция. Базовый класс мутирует (`addItem(item)` `final`: `addItemToCollection` + при успехе `onCollectionUpdated(id)`; `DEV_*`) и вызывает абстрактные `onCollectionUpdated(int)`/`onCollectionsUpdated(List<Integer>)`; отправку решает наследник (сейчас оба → `sendUpdateEvents`). `addItemToCollection` (protected) — мутация без события; танки переопределяют ради [флага](#coin-new-flag).
- Хелперы отправки (protected final): `sendUpdateEvents(int)` = `sendCollectionUpdated(id)` + `sendSectionEvents()`; `sendUpdateEvents(List)` — для dev-секции; `sendSectionEvents()` = `sendSectionUpdated()` + `CollectionUserComponent.sendNotification()`; `sendSectionUpdated()` отдельно — без нотификации (`markCountryViewed`). Подробно — [События](#event-mechanism).
- `isFullyCollected()` — default `false` (для танков осознанно: экономика бесконечная); альбомы — все коллекции набрали максимум звёзд.
- `isSelected()`/`setSelected(b)` (`final`/`protected final`) — делегаты к `getTypedEntry()`, `markAsDirty()` только при изменении. Участие в ролле, [Ролл секции](#roll-section).
- `hasAvailableReward()` (не `final`) — есть коллекция секции с `hasAvailableReward()`; альбомы переопределяют ([Нотификация](#reward-notification)).
- Персистентность: `fetchEntryChanges()`/`applyOwnEntryFromDb()`/`applyCollectionEntryFromDb()` — `final`, [Persistence](#persistence-overview). `collectionsEntry`/`collectionsEntryMap` — зеркало `Collection.itemsEntry` ради единообразия формы (запись и так доступна через `getCollection(id).getTypedEntry()`); пополняются приватным `registerCollectionEntry` из `fetchEntryChanges()` и `applyCollectionEntryFromDb()`.
- `convertSetCoins(id)` — НЕ часть контракта, только у танков.

**Принцип** (для любых Strategy-задач проекта): функционал, нужный одному наследнику, в абстрактный класс не выносится даже default-заглушкой — только public-метод конкретного класса. Метод базового класса оправдан, пока есть генерик-вызывающий код (пример: `isEverCompleted()` только на `CollectionExperimentalTank`; `isSectionActive()` — не нарушение, его вызывает генерик-ролл). Специфичная операция — через однократное сужение `instanceof` ([Типы секций](#section-types)), а не `if (section == ...)`.

<a id="class-albumssectiontype"></a>
`AlbumsSectionType` — звёздно-стадийная бухгалтерия секции (у танков её нет вовсе):

> ГДД: [gdd-ops-rewards](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-rewards), [gdd-ops-season](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-season)

- `getSectionStars()`/`getSectionMaxStars()` — суммы по коллекциям; `getCollectionStars(id)`/`getCollectionMaxStars(id)` — делегаты к `CollectionAlbum`; `getSectionRewardedStage()`; `isSectionStageCompleted(stage)` (private, порог `SECTION_STAGE_STARS`).
- `findAvailableSectionStage(): Integer|null` — единственная функция правила #gdd-ops-rewards: ближайшая незабранная стадия (`sectionRewardedStage`), если звёзд хватает, иначе `null`. `hasAvailableSectionReward()` = `findAvailableSectionStage() != null`.
- `takeSectionReward()`/`takeCollectionReward(id)` (public) делегируют приватным перегрузкам с `boolean quiet` (`true` — без событий; роуты quiet не передают). `takeSectionReward(quiet)`: берёт доступную стадию (`null`, если нечего), `sectionRewardedStage = stage + 1`, `markAsDirty()`, `createSectionStageReward(false)`, `grantReward`; без quiet — `sendSectionEvents()`. `takeCollectionReward(id, quiet)`: `getCollection(id).takeReward()` + `grantReward`; без quiet — `sendUpdateEvents(id)`.
- `collectAllAvailableRewards()` — те же операции с `quiet = true` (`while (hasAvailableSectionReward())`, затем награды каждой коллекции) и одна `sendNotification()`, если что-то выдано; push коллекций и секции не шлёт — клиент перерисовывает по ответу (`data`).
- `getSectionEndTime(): long`, `isSectionActive()`, `refreshSection()` — [Таймер](#collection-timer).
- `progressApiResponse()` — `section/sectionStars/sectionMaxStars/sectionRewardedStage/sectionStages/availableSectionStage (int|null)/hasAvailableReward` (секционная ИЛИ любая коллекционная)`/sectionEndTime`.
- `createRandomDropItem()` — [Генерация предмета](#drop-item-generation).
- `resetSectionState()` — обнуляет `sectionRewardedStage` (dirty, если был ≠ 0); зовёт `DEV_resetSection`. При старте сезона НЕ вызывается (ГДД #gdd-ops-season).

Операции альбома уровня коллекции (`isCollectionStageCompleted`/`takeReward`/…) на секции не дублируются — вызывающий берёт `CollectionAlbum` через `getCollection(id)`.

<a id="class-experimentaltankssectiontype"></a>
`ExperimentalTanksSectionType`:
- `isSectionActive()` = `true`, `refreshSection()` и `resetSectionState()` пусты (сезона нет); `progressApiResponse()` — `{section, hasAvailableReward, countries}` (без `sectionEndTime`).
- `countriesApiResponse()` (private) — прогресс вкладок наций в порядке `Country.ALL`, нации без коллекций пропускаются; элемент `{country (ordinal), completed (число коллекций с isEverCompleted), total, notified (любая коллекция нации с флагом)}`.
- `addItemToCollection` (override), `markCountryViewed(Country)` — [Флаг](#coin-new-flag). `getCollectionCountry(id)` — private делегат `getCollection(id).getCountry()`.
- `takeCollectionReward(id)`, `takePendingTank(id)`, `sellPendingTank(id)` (public), `completePendingTank`, `convertSetCoins`, `findNextRankCollectionId` (private) — [Клейм](#coin-set-conversion-economy), [Отложенный танк](#pending-tank).
- `createRandomDropItem()` — [Генерация предмета](#drop-item-generation). Статический `findExperimentalTankRank(id)`; приватные `findRankCollectionId(rank, country)`, `createRandomCoinOfRank`, `rankToStarsRank(id)` (`Rank.VALUES.valueOf(rank ?: 1)`; работает, т.к. `Rank.I.ordinal() == 1`).

<a id="singletons"></a>
### Синглтоны: секции и коллекции не пересоздаются на каждый вызов

- `CollectionUserComponent.sectionTypes` — `ImmutableMap<CollectionSection, CollectionSectionType>`, строится один раз в `buildSectionTypes()` (единственное место `new AlbumsSectionType`/`new ExperimentalTanksSectionType`).
- Каждая секция в конструкторе строит `ImmutableMap<Integer, CollectionAlbum|CollectionExperimentalTank>` — по объекту на каждый `CollectionsData` секции.
- Безопасно: область — один пользователь, объекты хранят только его персистентное состояние.

<a id="no-section-type"></a>
### Секция без типа секции (`EXPERIMENTAL_AIRPLANES`)

Секция 3 — НЕ `AlbumsSectionType` (позже отдельная реализация по образцу танков); тип не создаётся (решение пользователя 2026-09-28). Следствия:
- `hasSectionType(3)` = `false`, `getSectionType(3)` → `null`, `getCollection(id)` → `null` для её коллекций; в ролл дропа не попадает.
- В `collectionsList` её нет; `dbMappingChildBuild` пропускает все её записи.
- `/ingame/collections/getSection`, dev `collectionSectionFillMax`/`collectionSectionReset`/`collectionSummon` с `section = 3` → ошибка как для невалидной секции; `getSectionReward` → "section does not support stage rewards", `getAllRewardInSection` → "no available reward"; роуты по `collectionId` → "invalid collections id".
- Незабранный `receivedCollectionItem` такой секции отбрасывается при загрузке в `TrainUserComponent.dbMappingBuild` (только в памяти; `rci` в БД не чистится — решение пользователя, перезапишется при следующем дропе/`clearReceivedCollectionItem`).

<a id="section-types"></a>
### Типы секций: доступ к специфичной для типа функциональности

- `CollectionUserComponent.getAlbumsSectionType(section)` — единственный геттер конкретного типа: `AlbumsSectionType` через `instanceof` или `null`. `CollectionPage` на `null` отдаёт ошибку — это же не даёт получить album-награду для танковой секции.
- Операции над коллекцией: `getCollection(id)` → явная проверка `null` ("invalid collections id") → однократное сужение `instanceof`. Отдельного типа секции под это нет и не должно быть.
- Танковая страница берёт секцию приватным `getTanksSectionType(user)` — прямой каст `(ExperimentalTanksSectionType) getSectionType(EXPERIMENTAL_TANKS)`, безопасно (lookup по константе). Отложенный рефактор каста и `getAlbumsSectionType` — `/workspace/client/.claude/memory/server_collections_deferred_fixes.md`.

**Маршруты разнесены по трём страницам-роутерам (2026-10-01)** — общего диспетчера по `instanceof` collection нет, каждая страница сужает тип своей коллекции и отвечает ошибкой на чужой (регистрация — `WSRouter`):
- **`CollectionPage`** (`/ingame/collections`) — общие для любых секций: `""` (index → `apiResponse()`), `/getSection`, `/getSectionProgress {section}` (`progressApiResponse()`; для секции без типа "invalid collections section"), `/getCollection` (`fullApiResponse()`).
- **`CollectionExperimentalTankPage`** (`/ingame/collections/experimentalTank`) — только `CollectionExperimentalTank`: `/getCollectionReward`, `/markCollectionItemViewed`, `/compareReward`, `/takeReward`, `/sellReward`.
- **`CollectionAlbumPage`** (`/ingame/collections/album`) — только `CollectionAlbum`/альбомная секция: `/getCollectionReward`, `/getSectionReward`, `/getAllRewardInSection`.

<a id="reward-order"></a>
### Получение наград ТОЛЬКО по порядку стадий

> ГДД: [gdd-ops-rewards](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-rewards)

Секция: `/getSectionReward` требует `findAvailableSectionStage() == stage`, иначе ошибка "section stage reward is not available"; других проверок нет, порядок гарантирован функцией. Коллекция альбома: проверки `isCollectionStageCompleted` и `stage == album.getRewardedStage()` ("collection stage rewards must be claimed in order"); альбомы-коллекции остаются на `hasAvailableReward` + `rewardedStage` (решение пользователя). `collectAllAvailableRewards()` идёт по порядку сам.

Награды этапов выдаёт `AlbumsSectionType` через `grantReward` (страницы только валидируют и вызывают `takeSectionReward()`/`takeCollectionReward(id)`); серебро засчитывается в квест `SILVER_COINS_GAINED`, как серебро с поезда и за дубликаты (решение пользователя 2026-09-29). Золото стадии в квест не засчитывается.

<a id="collection-timer"></a>
### Таймер коллекции — только у альбомов, не общий на пользователя

> ГДД: [gdd-ops-season](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-season)

`sectionEndTime` — только в `AlbumsSectionEntry`; у танков нет ни в записи, ни в API, в JSON — только у альбомных секций (`sectionInfoApiResponse`, `apiResponse`). Клиентский контракт: отсутствие = "таймера нет".

- Геттеры без побочных эффектов: `getSectionEndTime()`, `hasAvailableReward()`, `isSectionActive()`, `apiResponse()`.
- Альбомы: `isSectionActive()` = `endTime > now`; `refreshSection()` (public) безусловно ставит `endTime = now + COLLECTION_DURATION` (90 дн), `reselect()`, `markAsDirty()`. Фото/звёзды/награды не трогаются (ГДД #gdd-ops-season). Танки: `isSectionActive()` всегда `true`, `refreshSection()` пуст.
- `reselect()` — сейчас `setSelected(true)`. Точка расширения: при ротации наборов коллекций здесь решать, остаётся ли секция `selected`.
- `CollectionUserComponent.refreshState()` — по всем секциям: `!isSectionActive()` → `refreshSection()` + push `/events/collections/sectionRestarted {section}` (без `collectionIds`); при перезапуске любой секции `sendNotification()`. Вызывается из `AuthorizedUserPage.onRouteCallStart` после `resetOffers()` и из `User.onAuthorizedActiveOnce` перед `sendNotification()`; из роутов явных вызовов нет. Срабатывает и на первом старте (`endTime == 0`), фактически только у альбомов.

<a id="coin-accumulation-train-flow"></a>
## Накопление монет и поток открытия поезда

Дроп на `/ingame/train/summon` не зависит от секции, открытой на клиенте — секция выбирается взвешенным роллом.

<a id="roll-section"></a>
### Ролл секции: `CollectionUserComponent.rollDropSectionType()`

> ГДД: [gdd-train-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-train-drop), [gdd-ops-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-drop)

Возвращает `CollectionSectionType` или `null`, без кэша:
- Кандидаты — `sectionTypes.values()` с `isSectionActive() && isSelected() && !isFullyCollected()`; пусто → `null`. Отдельного флага «дроп разрешён» нет (танки всегда активны, альбомы — пока идёт сезон; сезон актуализирует `refreshState()`). Самолёты исключены отсутствием типа ([см.](#no-section-type)).
- `roll = nextIntInclusive(1, 100)`, накопительная сумма `getCollectionDropChance()` кандидатов по порядку; первая секция с суммой ≥ `roll` возвращается. Сумма < `roll` → `null` — ожидаемый промах. Общего `COLLECTION_DROP_CHANCE` нет.

**Боевой путь** (`TrainPage.actionSummon`): незабранный `receivedCollectionItem` → сразу `sendCollectionItemReply`; иначе проверки танка/схемы, `rollDropSectionType()` → `TrainUserComponent.receiveCollectionItemFromSection(section)`; предмет получен — списание схемы, опыт поезда, квест `TRAIN_SUMMON`, `sendCollectionItemReply`; иначе обычный `receiveTank()`.

**Dev `/ingame/devTools/collectionSummon`** — `{section?: int}` (дефолт `USSR_OPERATIONS`); невалидная секция или секция без типа → `error()`. Намеренно в обход фильтров ролла зовёт `receiveCollectionItemFromSection` (если есть незабранный предмет — вернётся он, независимо от секции), затем тот же `receiveSummonedItem`.

`TrainUserComponent.receiveCollectionItemFromSection(sectionType)` — есть незабранный `receivedCollectionItem` → он; `sectionType == null` → `null`; иначе `createRandomDropItem()` → `receivedCollectionItem` (`changedField("rci")`). `null` (нет предметов/ранга в Balance) вызывающие обрабатывают явно. После накопления страница зовёт `clearReceivedCollectionItem()`. `train.apiResponse()` содержит `receivedCollectionItem`, пока предмет не забран.

<a id="summon-reply"></a>
### Ответ summon с коллекционным предметом (контракт с клиентом)

`CollectionUserComponent.receiveSummonedItem(item): JSONObject` (вызывают `TrainPage.sendCollectionItemReply` и `DevToolsPage.actionCollectionSummon`): `getSectionType(section).addItem(item)`, при `!isBetter` — `addDuplicateReward`; возвращает объект для ключа `collectionItem`:
- `itemInfo` — `item.apiResponse()`; `sellReward` — только при `!isBetter`;
- `collectionInfo` — `Collection.apiResponse()` коллекции предмета ПОСЛЕ добавления;
- `sectionInfo` — `sectionInfoApiResponse(section)`, тот же элемент, что в `collectionsList`.

Форма ответа: `{collectionItem: {itemInfo, sellReward?, collectionInfo, sectionInfo}, train, account}`. `clearReceivedCollectionItem()` вызывает страница.

<a id="drop-item-generation"></a>
### Генерация предмета — `createRandomDropItem()` конкретной секции

> ГДД: [gdd-exp-quality](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-quality), [gdd-ops-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-drop)

- `AlbumsSectionType` — случайный предмет из `Balance.getCollectionSectionItems(section)`, звёзды `Rank.I` + `getRandomStars()` (шансы `STAR_COUNT_CHANCES` — ГДД #gdd-ops-drop); бросок дробный (`RandomJdk.nextPercents()`) и сумма весов дробная — иначе 0,2 % теряются при округлении.
- `ExperimentalTanksSectionType` — ранг: `getRandomExperimentalTankRank(trainLevel)` (`EXPERIMENTAL_TANK_RANK_CHANCES`: последняя строка с `key <= trainLevel`, уровень ниже 1 — первая строка; накопление веса, `rnd 1..100`). Нация — равновероятно среди коллекций ранга, без учёта прогресса. Монета — случайный предмет тира, `setStars(rankToStarsRank(tier), 1)`.

Фильтры (`isSelected`/`isFullyCollected`) проверяет ролл. Накопление делает вызывающий (`receiveSummonedItem`), чтобы предмет сначала можно было показать игроку. Отклонённые схемы выбора ранга — [TODO](#todo).

<a id="coin-set-conversion-economy"></a>
## Экономика монет: клейм комплекта

> ГДД: [gdd-exp-set](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-set), [gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward), [gdd-exp-duplicate](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-duplicate)

Комплект собирается обычным дропом, награда — по запросу `CollectionExperimentalTankPage.actionGetCollectionReward` (`/ingame/collections/experimentalTank/getCollectionReward`, [Типы секций](#section-types)):

1. `instanceof CollectionExperimentalTank` ("collection does not support stage rewards").
2. `hasPendingTank()` → ошибка "reward is pending": пока предыдущий танк не забран через take/sell, повторный клейм запрещён.
3. `isCompleted()` ("collection is not complete").
4. `ExperimentalTanksSectionType.takeCollectionReward(id)`: `collection.takeReward()`; танк → `pendingTank`, монеты НЕ конвертируются, `everCompleted` не ставится; золото (повторный сбор) → `grantReward` и сразу `convertSetCoins(id)`. Затем `sendUpdateEvents(id)`.
5. `convertSetCoins(id)` (private): `removeAllItems()`, `setNotified(false)`, случайная монета следующего ранга (`createRandomCoinOfRank`; `null` на последнем ранге). Монета уже есть → серебро как за дубликат (`addDuplicateReward`, #gdd-exp-duplicate); иначе `addItem` коллекции мимо секции (`notified` не ставится) и сама шлёт `collectionUpdated` соседней коллекции. Возвращает `{itemInfo, sellReward?, collectionInfo, sectionInfo}` (нужен `TrainCollectionItemPopup`).

Ответ `actionGetCollectionReward`: `reward` (`apiResponse()` отложенного танка или выданного золота), `isRewardPending`, `nextRankItem` (`null` при отложенном танке — монета придёт в ответе take/sell; для золота — payload конвертации или `null`). Танк: окно сравнения (`/compareReward`) → take/sell → монета; золото: монета → полёт золота.

<a id="pending-tank"></a>
### Отложенный танк (`pendingTank`) — take/sell вместо немедленной выдачи

> ГДД: [gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward)

Танк за первый сбор не кладётся в ангар внутри клейма — игрок выбирает "взять" или "продать", как при дропе танка с поезда (`TrainPage` `/accept`/`/refuse`).

- **Персистентность**: `CollectionExperimentalTankEntry.pendingTank` (`Tank`) — вложенный документ (`DBFields.PENDING_TANK_FIELD = "pendingTank"`; `dbToData()`: `pendingTank.dbToData()` или пустой `Document`; `dbMappingBuild`: `ItemFactory.newFromDocument(doc)` → если `Tank` (`null` для неизвестного `t` тоже отсекается `instanceof`) → `dbMappingBuild(doc)`). На уровне записи коллекции (тира), у каждого тира свой.
- **`CollectionExperimentalTank`**: `setPendingTank`/`clearPendingTank` — `private`, через `getTypedEntry()` + `markAsDirty()`; `clearPendingTank()` — no-op при `null`. Нештатное закрытие окна = решение не принято: при перезаходе `hasPendingTank()` остаётся, «Получить» не повторяется, окно открывает `/compareReward`. `DEV_reset()` чистит `pendingTank`.
- **`hasAvailableReward()`** = `isCompleted() || hasPendingTank()` — карточка остаётся "доступна действие", пока танк не забран/продан.
- **Превью `reward`** и поле `hasPendingTank` — [apiResponse](#class-collectionexperimentaltank); `hasPendingTank` позволяет клиенту различать "превью" и "ждёт take/sell" без парсинга `reward`.
- **Роуты `CollectionExperimentalTankPage`** (общий приватный `getPendingTankCollection` — валидирует `instanceof CollectionExperimentalTank` + `hasPendingTank()`, иначе `error()`):
  - `/compareReward` — окно сравнения (по образцу `AssemblyPage` `/compare`): `receivedTank` = отложенный танк, `replaceableTank` = `user.getHangarComponent().getReplaceableTank(receivedTank)` (или `null`).
  - `/takeReward` — `takePendingTank(id)`: копия `TrainPage.actionAccept` без туториальных шагов (серебро за заменяемый танк через `grantReward`, `addTank`, квесты `TANK_SELL`/`BETTER_TANK`, `onBasicInfoUpdate`), затем `completePendingTank`. В кодекс не пишется (ГДД; поезд пишет в `TrainUserComponent.receiveTank()`).
  - `/sellReward` — `sellPendingTank(id)`: копия `TrainPage.actionRefuse` (серебро за танк, квест `TANK_SELL`), затем `completePendingTank`.
  - `completePendingTank(id, rewards)` (private): `markRewardReceived()`, `convertSetCoins(id)` (монеты и прогресс X/8 — после решения), `sendUpdateEvents(id)`. Ответ take/sell: `{collectionId, rewards, nextRankItem}`. Дубль с `TrainPage` — [компромисс 5](#tradeoffs-and-known-issues).

Награды (`ExperimentalTanksSectionType`):
- `createExperimentalTankReward(collectionId, isTemplate)` — первый сбор: `Tank.createNew(tankId)`, `tankId` из `EXPERIMENTAL_TANK_REWARD` (ранг → id танков по нациям; позиция = позиция коллекции в `EXPERIMENTAL_TANK_RANG_COLLECTION`; сейчас id = 286 + 8·нация + (ранг − 1), все есть в `balance.json`; фильтр `dropType` из `TankData.build` убран при слиянии по решению пользователя, танки 286–349 грузятся). Id, которого нет в Balance, → NPE в `Tank.createNew` (и в превью `apiResponse()`) — при правке таблиц сверять с `Tanks`. Параметры считаются сразу (`recalculateParams()` — шаблон в сумку не попадает). Уровень/звёзды выдаваемого танка — `TrainUserComponent.rollTankLevelAndStars(tank)` в `createCompletionReward(false)`; у шаблона — уровень 1 без звёзд (ролл случаен и не совпал бы с выдачей).
- `createExperimentalTankDefaultReward(isTemplate)` — повторные сборы, 50 золота (#gdd-exp-reward).

<a id="event-mechanism"></a>
## События клиенту: push коллекций и секции, `setCompleted`, ответы операций

Источник событий обновления — сервер (решение 2026-10-07): клиентских эмитов после запросов нет, ответ запроса управляет только UI инициатора.

**0. Push обновления (слой операций секции)** — каждый запускает один точечный запрос клиента:
- `/events/collections/collectionUpdated {collectionId}` — на каждую затронутую коллекцию (`/getCollection`); `convertSetCoins` шлёт его соседней коллекции сам, если монета не дубликат.
- `/events/collections/sectionUpdated {section}` — шапка секции (`/getSectionProgress`); также из `markCountryViewed`.
- `/events/collections/sectionRestarted {section}` — из `refreshState()` при рестарте сезона; поведение решает клиентский наследник секции.
- Отправка — хелперы `CollectionSectionType` ([Strategy](#strategy-sectionlist)); `sendSectionEvents()` добавляет `sendNotification()`. Глушение (`quiet`) — только у операций альбома, «Собрать всё» шлёт одну нотификацию.
- Push уходят раньше ответа на запрос (принятый компромисс); клиент опирается на порядок сообщений по одному сокету.

**1. WS-push `/events/collections/setCompleted`** — без запроса, когда любая коллекция становится `isCompleted()` после добавления предмета:
- `Collection.addItem` → `emit(COLLECTION_COMPLETED_ID, id)` (`"collectionCompleted"` — служебное имя, не WS-путь); подписка в конструкторе компонента → `onCollectionCompleted(collectionId)` → `sendWSEvent(new JsonPacket(0L, "/events/collections/setCompleted"))` с `{collectionId: int, section: int}` (нет коллекции в Balance — не шлёт).
- Срабатывает при любом добавлении, после которого коллекция полна: дроп поезда, dev-выдачи. Деталей не несёт — клиент запрашивает сам (`/getCollection`). Клиент подписан в `GameEvents.ts`.
- **Push — чистое уведомление, награду не выдаёт**; награда — только по `getCollectionReward`.

**2. Синхронные ответы операций** (клиент различает по пути запроса и типу коллекции):
- `getCollectionReward` монет (`CollectionExperimentalTankPage`) — форма из [Клейма](#coin-set-conversion-economy); альбомных стадий (`CollectionAlbumPage`) — только `reward` (`hasAvailableReward`/`rewardedStage`/`sectionRewardedStage` убраны 2026-10-06; состояние клиент берёт из `/getCollection`/`/getSectionProgress`).
- `/takeReward`, `/sellReward` — `{collectionId, rewards, nextRankItem}`; `/album/getSectionReward` — `{reward}`; `/album/getAllRewardInSection` — `{rewards, data}` (подмена `data` сохранена осознанно, решение пользователя: отклонение от схемы событий).

События `"collectionSetCompleted"` сервер не шлёт — это имя клиентской фичи.

<a id="reward-notification"></a>
### Нотификация о доступной награде (`NotificationId.COLLECTION_ID = "collection"`)

`CollectionUserComponent.sendNotification()` обходит `sectionTypes` и собирает секции с `CollectionSectionType.hasAvailableReward()` (тот же метод даёт флаг `hasAvailableReward` в `apiResponse` секций):
- базовый (не `final`) — любая коллекция с `Collection.hasAvailableReward()` (у танков учитывает `pendingTank`);
- `AlbumsSectionType`: `hasAvailableSectionReward() || super.hasAvailableReward()`.

Есть секция → `NotificationUserComponent.addNotification("collection", {hasReward: true, rewardSections: [int CollectionSection.value]})` (push `/events/userNotification` `method=UPDATE`); нет → `deleteNotification("collection")` (`DELETE`, только если была).

Точки вызова:
- вход — `User.onAuthorizedActiveOnce()` (после достижений и `refreshState()`);
- `CollectionSectionType.addItem` (через `onCollectionUpdated` → `sendUpdateEvents` → `sendSectionEvents`) — только если предмет добавлен; дубликат/продажа не вызывают. Dev add/addBest идут через него;
- альбом: `takeSectionReward`/`takeCollectionReward` (без quiet), `collectAllAvailableRewards` — одна нотификация после выдачи;
- танки: `takeCollectionReward`, `takePendingTank`, `sellPendingTank` (через `sendUpdateEvents`);
- dev: `DEV_fillCollection`/`DEV_fillSection`/`DEV_resetCollection`/`DEV_resetSection` через `onCollection(s)Updated`;
- сезонный `refreshSection` нотификацию не шлёт — её шлёт `refreshState()`.

**Контракт с клиентом**: ключ `"collection"` в `/events/userNotification` и в начальном `NotificationUserComponent.apiResponse()`; клиентская обработка — `#reward-notification` клиентского документа.

<a id="db-write-principle-check"></a>
## Принцип "запись в БД только при новом элементе/награде"

У игрока, не получавшего предметов/наград, не должно быть ни одного документа `collections`. Подтверждено кодом:
- `Collection.addItem` создаёт `CollectionItemEntry` только для нового предмета (улучшение меняет существующую).
- `takeReward`/`takeSectionReward` — `markAsDirty()` только после проверок страницы.
- `markEverCompleted()`, `setNotified()`, `setSelected()`, dev `DEV_reset()`/`resetSectionState()` — пишут только при реальном изменении.
- `ExperimentalTanksSectionType` не вызывает `markAsDirty()` — `ExperimentalTanksSectionEntry` в Mongo не пишется.
- Все `Collection`/`CollectionSectionType` создаются заранее, но в памяти: `entry` = `null` до первого `getTypedEntry()`, который сам ничего не пишет.

**Единственное принятое исключение** — `AlbumsSectionEntry.sectionEndTime`: дефолт `0`, поэтому первый же `refreshSection()` (вход пользователя) пишет документ секции даже игроку без предметов. Решение пользователя (из трёх вариантов): оставить — служебное поле, стабильность личного 90-дневного окна важнее принципа. Не пересматривать, пока не изменится логика таймера.

<a id="tradeoffs-and-known-issues"></a>
## Компромиссы и уязвимости

Принятые решения, не требующие действий:
1. `sectionEndTime` пишется при старте сезона — [Принцип записи](#db-write-principle-check).
2. Дубликат монеты при клейме и с поезда → одинаково серебро (`addDuplicateReward` → `createDuplicateReward`, + квест `SILVER_COINS_GAINED`).
3. `CollectionExperimentalTank.DUPLICATE_ITEM_PRICE` дублирует сумму продажи танка из `TrainUserComponent.getSilverCoinsReward` — намеренно, без передачи танка (решение пользователя); при изменении формулы продажи синхронизировать вручную.
4. `takePendingTank` — копия `TrainPage.actionAccept` без туториальных шагов (то же `sellPendingTank` ↔ `actionRefuse`); при правке оригиналов синхронизировать вручную (принято 2026-10-07).
5. Уникальный индекс `{ownerId, cid}` не ставится (решение 2026-10-05) — инвариант «1 cid = 1 запись» держится кодом и сведением дублей при загрузке.
6. Поле `selected` секции — задел под ротацию наборов, не удалять (решение 2026-10-07).
7. Push `collectionUpdated`/`sectionUpdated` уходят раньше ответа — [События](#event-mechanism).
8. Отложены: `getAlbumsSectionType(section)` и каст `getTanksSectionType` — `/workspace/client/.claude/memory/server_collections_deferred_fixes.md`.
9. Кандидат на удаление: `TankDropType.COLLECTION_REWARD` (нигде не применяется).

<a id="todo"></a>
## TODO / незакрытые задачи

### Открытые

- **`BagUserComponent.dbMappingChildBuild`** делает `(BagItem) item`: документ сумки с `t = 6` (`COLLECTION_ITEM`; до слияния с amnesia/fix был `t = 3`, теперь это `MILITARY_BASE_BUILDING` — старые документы будут прочитаны как здание базы) уронит загрузку с `ClassCastException`, так как `CollectionItem` больше не `BagItem` (из `BagUserComponent` удалены список/карта коллекционных предметов и ветки `COLLECTION_ITEM` в `add0`/`onClean`). Решение уточняется у пользователя. Пустая ветка `instanceof CollectionItem` в `User.addItem` оставлена как есть (решение пользователя). Проверено 2026-10-19: `(BagItem) item` в `BagUserComponent` на месте, формулировка актуальна.
- **`TrainUserComponent.dbMappingBuild`, поле `rci`**: после слияния `ItemFactory.newFromDocument` может вернуть `null` (неизвестный `t`), а код сразу зовёт `dbMappingBuild` без проверки (для `receivedTank` проверка добавлена, для `rci` нет) — NPE при загрузке. Зона Поезда, здесь только фиксация.
- Самолёты (`EXPERIMENTAL_AIRPLANES`) — ждут ТЗ, см. [Секция без типа секции](#no-section-type).

### Принятые решения (не пересматривать)

- Ранг монеты при дропе — ролл по уровню поезда, нация равновероятно; схемы «только ранг 1» и «тир по прогрессу нации» отклонены пользователем. Звёзды монеты не случайные: 1 звезда с рангом тира.
- Шанс дропа задаёт каждая секция (`getCollectionDropChance()`); общего шанса нет. Серверного «текущей секции» и двухфазного дропа нет — секция выбирается роллом при каждом summon.
- `CollectionItem` — один класс, наследник `Item`; владение — `CollectionItemEntry` (вариант Б2), переход на `BagItem` отклонён.
- Танк коллекции в кодекс не пишется (ГДД). Сбор комплекта даёт и монету следующего ранга, и награду ([gdd-exp-set](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-set)).
- Dev-выдачи идут полным игровым путём, ставят `notified` ([Dev-tools](#dev-tools)).
- JSON-ключи `rewardedStage`, `sectionEndTime`, `sectionRewardedStage`, `notified`, `completed`, `nextRankItem`/`nextRankCollection`; поле записи `notified` (`DBFields.NOTIFIED_FIELD`) — для живой БД со старым `notyfied` нужен `$rename`.

<a id="rule-no-reflection"></a>
## Правило проекта: без рефлексии

Полиморфное создание при десериализации — без `Class.forName(...)`: явные `enum` + `ImmutableMap<Enum, Supplier<T>>` (`ItemFactory`/`CodexEntryFactory`). Для `CollectionItem` выбор класса не нужен — `CollectionItem::new`. Там же правило проекта: без развёрнутых javadoc, пояснения — в этом документе.

<a id="file-map"></a>
## Карта файлов компонента

Пути от корня репозитория `server`. Полнота проверена grep по именам классов прямого влияния.

### Файлы прямого влияния

- `game/src/main/java/com/linkedgames/game/model/collections/CollectionUserComponent.java` — компонент пользователя: состояние коллекций, операции секций, клейм, отложенный танк, персистентность
- `game/src/main/java/com/linkedgames/game/model/collections/collectionList/Collection.java` — базовая коллекция (Strategy нижнего уровня)
- `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionAlbum.java` — альбом операций СССР
- `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionExperimentalTank.java` — коллекция опытного танка (монеты, награды)
- `game/src/main/java/com/linkedgames/game/model/collections/itemList/CollectionItem.java` — коллекционный предмет (наследник Item)
- `game/src/main/java/com/linkedgames/game/model/collections/sectionList/CollectionSectionType.java` — базовый тип секции (Strategy верхнего уровня)
- `game/src/main/java/com/linkedgames/game/model/collections/sectionList/AlbumsSectionType.java` — секция альбомов
- `game/src/main/java/com/linkedgames/game/model/collections/sectionList/ExperimentalTanksSectionType.java` — секция опытных танков
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionEntry.java` — запись коллекции в Mongo (базовая)
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionAlbumEntry.java` — запись альбома
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionExperimentalTankEntry.java` — запись опытного танка
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/CollectionSectionEntry.java` — запись секции (базовая)
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/AlbumsSectionEntry.java` — запись секции альбомов
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/ExperimentalTanksSectionEntry.java` — запись секции опытных танков
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionItemEntry/CollectionItemEntry.java` — запись коллекционного предмета
- `game/src/main/java/com/linkedgames/game/model/collections/data/CollectionsData.java` — балансовая модель коллекции
- `game/src/main/java/com/linkedgames/game/model/collections/data/CollectionItemData.java` — балансовая модель предмета коллекции
- `game/src/main/java/com/linkedgames/game/model/collections/enums/CollectionSection.java` — enum секций
- `game/src/main/java/com/linkedgames/game/dao/CollectionDao.java` — DAO Mongo-коллекции collections
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionPage.java` — роуты /ingame/collections (общие операции)
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionAlbumPage.java` — роуты альбомов
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionExperimentalTankPage.java` — роуты опытных танков
- `game/src/main/resources/migrations/1791190438943_collections.json` — миграция индекса Mongo-коллекции collections

### Файлы косвенного влияния

- `game/src/main/java/com/linkedgames/game/model/user/User.java` — поле и геттер getCollectionUserComponent, регистрация компонента; refreshState/sendNotification коллекций рядом с кланом и военной базой (не область коллекций), пустая ветка CollectionItem в addItem
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorInitializationTask.java` — загрузка записей коллекций через CollectionDao при входе
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorUpdateTask.java` — bulkUpdate и commitDbUpdates коллекций при сохранении
- `game/src/main/java/com/linkedgames/game/model/user/UserEmitterId.java` — COLLECTION_COMPLETED_ID, эмиттер события комплекта
- `game/src/main/java/com/linkedgames/game/model/notifications/NotificationId.java` — COLLECTION_ID, нотификация о награде
- `game/src/main/java/com/linkedgames/game/model/item/Item.java` — родитель CollectionItem, count стал long
- `game/src/main/java/com/linkedgames/game/model/item/ItemFactory.java` — зависимость: фабрика предметов, ItemType.COLLECTION_ITEM -> CollectionItem::new; регистрирует и MILITARY_BASE_* (чужая область); newFromDocument возвращает null для неизвестного t
- `game/src/main/java/com/linkedgames/game/model/item/ItemType.java` — зависимость: enum типов предметов, значение COLLECTION_ITEM (ordinal 6, последний)
- `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` — receivedCollectionItem (поле rci), ролл секции, поток открытия поезда (баланс шансов теперь Summon*, туториал-ветка в receiveTank удалена — не влияет на коллекции)
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/TrainPage.java` — ответ summon с коллекционным предметом
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AuthorizedUserPage.java` — refreshState коллекций при авторизации (сезон)
- `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` — регистрация роутов трёх страниц коллекций
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` — dev-роуты коллекций (DEV_*, collectionSectionFillMax)
- `game/src/main/java/com/linkedgames/game/balance/Balance.java` — загрузка и доступ к Collections/CollectionItems, формулы
- `game/src/main/resources/balance.json` — таблицы Collections и CollectionItems (остальное — чужие области)
- `game/src/main/java/com/linkedgames/game/model/Rank.java` — зависимость: COLLECTION_ITEM_STARS, максимум звёзд альбома (`CollectionAlbum.getMaxStars`); сохранён при слиянии
- `game/src/main/java/com/linkedgames/game/balance/BalanceImporter.java` — листы Collections, CollectionItems при импорте баланса

<a id="related-docs"></a>
## Смежная документация

- Клиент: `/workspace/client/.claude/docs/collections-architecture.md` (экран коллекций, `collection.d.ts`, `CollectionCompletePopup`).
- Бизнес-логика: `/workspace/client/.claude/docs/game-design/collections-gdd.md`.
