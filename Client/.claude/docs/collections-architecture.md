# Компонент "Коллекции" (Профиль → Коллекции) + событие "комплект собран"

> Сверено с кодом после merge `origin/amnesia/fix` 2026-10-19. (точки подключения и карта файлов).
> 2026-10-23 — `TrainCollectionItemPopup` и `onExit` (продолжение автопризыва поезда, решение пользователя).

> **Статус:** финальный, сверен с кодом клиента 2026-10-13 (после коммита `1272bc46`) и с серверным
> контрактом (`/workspace/server/.claude/docs/collections-architecture.md`). Базовая структура
> (список/секции/альбомы/`CollectionUtils`/`CollectionTabSelector`) описана по коду (`client-analyst-lead`);
> «комплект собран», окно сравнения награды-танка, нотификатор, события `COLLECTION_UPDATED`/
> `COLLECTION_SECTION_UPDATED`/`COLLECTION_SECTION_RESTARTED` — по итогам разработки.
> Ссылок «код → этот документ» в коде нет: ищи по имени класса или якорю `#cls-<Класс>`.

**Разделы:** [1. Описание](#s1) · [2. Референсы](#s2) · [3. Паттерны](#s3) ·
[4. Список классов](#s4) · [6. Оглавление по классам](#s6) · [7. Классы и методы](#s7) ·
[8. Компромиссы](#s8) · [9. Связь с ГДД](#s9) · [10. Карта файлов](#s10)

**ГДД (бизнес-логика):** [collections-gdd.md](/workspace/client/.claude/docs/game-design/collections-gdd.md) — правила обеих секций; ссылки на разделы — у классов ниже.

## 1. Краткое описание компонента: назначение и бизнес-логика {#s1}

"Коллекции" — вкладка `ProfilePopup` (`profileScreen.tabs.collections`). Три слоя:

1. **Список секций** — `/ingame/collections` → `CollectionListJSON`; плитка секции: иконка, название,
   (у альбомов) таймер до конца события.
2. **Секция** (`CollectionsTypeSection`) — модальный `CollectionSectionPopup`, данные запросом
   `/ingame/collections/getSection`.
3. **Коллекция** (`Collection`) — альбом фотографий (`CollectionAlbum`) у "Операций СССР" или
   карточка с рядом монет (`CollectionExperimentalTank`) у "Экспериментальной техники".

Типы секций (`CollectionsType`), реализованы два:

- **USSR_OPERATIONS** — альбомы. Общий звёздный прогресс секции (`sectionStars`/`sectionMaxStars`),
  пороговые награды по стадиям, кнопка "собрать всё", таймер. Альбом — набор фото-предметов
  (`CollectionItemJSON`); открытие — запрос `getCollection` → полноэкранная `CollectionAlbum`.
- **EXPERIMENTAL_TANKS** — карточки монет по нациям. **Звёздного прогресса нет ни у секции, ни у
  карточки** (решение пользователя). Вкладки-нации строятся из `countries` в данных секции; карточка
  сразу содержит весь набор монет (`items`, `null` = не собрана). Индикатор новой монеты —
  [#tanks-notify](#tanks-notify).
- **EXPERIMENTAL_AIRPLANES** — **не реализована и недоступна игроку**: сервер не отдаёт секцию 3
  (серверный `#no-section-type`), `CollectionsListSection.UIMain()` строит плитки только для 1 и 2.
  Класс секции — заглушка (`#s8` п.1).

Dev-tools-кнопки (при `Globals.isDevTools()`) — заполнение/сброс секции или коллекции для тестового стенда.

### Комплект коллекции собран (`collectionSetCompleted`) {#set-completed-feature}

> ГДД: [gdd-exp-set](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-set), [gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward)

Когда предмет (дроп поезда `/ingame/train/summon`, dev-выдачи) делает коллекцию полной, сервер только
уведомляет клиента push-ом. Монеты превращаются в монету следующего качества лишь при явном клейме
«Получить» (`#gdd-exp-set`).

> Не существуют (не возвращать): `burned`/`CollectionBurnedItemJSON` и `collectionSetCompleted` в ответе
> `/ingame/train/summon`, клиентский вызов `getCollectionReward` по push, `CollectionSetCompletedPopup`
> и очередь попапов в `HomeScreen`. Тост независим от `TrainCollectionItemPopup` (`#s8` п.7).

Контракт (по серверному документу):

1. **Push `/events/collections/setCompleted`** с `{collectionId, section}` — чистое уведомление, данных о
   награде нет. Клиент: `GameEvents.listenServerEvents()` → `COLLECTION_SET_COMPLETED`
   (`#cls-gameevents`); тип `CollectionSetCompletedJSON` (`#cls-collectiondts`).
2. **Клейм `getCollectionReward`** — только явный клик игрока (`CollectionExperimentalTank.claimReward`,
   `#cls-collectionexperimentaltank`). Роуты по типу секции: танки —
   `/ingame/collections/experimentalTank/getCollectionReward { collectionId }`, альбомы —
   `/ingame/collections/album/getCollectionReward { collectionId, stage }`; общие `/ingame/collections`,
   `/getSection`, `/getCollection` — отдельный общий пейдж. Награда-танк **всегда** откладывается
   сервером (`isRewardPending`, `hasPendingTank` у набора) до решения в окне сравнения
   (`.../experimentalTank/compareReward` → `takeReward`/`sellReward`); золото выдаётся сразу.
3. **Тост** создаёт `HeaderAchievementsBar` прямо из payload, без запросов
   (`#cls-headerachievementsbar-set-completed`).

**Тост `CollectionCompletePopup`**: `extends Layout` (образец — `AchievementCompletePopup`), без
затемнения и крестика, в области тостов шапки (общая `ScrollableArea` с достижениями), fade+slide,
скрывается по таймеру. Показывает баннер и приглашение «Получите награду»; награды в payload нет, **к
моменту показа она ещё не выдана**. Класс — `#cls-collectioncompletepopup`.

### Фокус при клике на тост {#collection-complete-focus-feature}

> ГДД: [gdd-navigation](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-navigation)

Клик открывает `ProfilePopup` на вкладке "Коллекции" с фокусом на секции/коллекции события — аналог
`IAchievementSectionConfig`/`AchievementsSection.focus()`, но секции открываются в СВОЁМ модальном
`CollectionSectionPopup`, поэтому конфиг идёт через два уровня (`ProfilePopup` → `CollectionsSection` →
`CollectionsTypeSection`). Фокус проходит весь путь (список → секция → коллекция), чтобы "назад"/закрытие
вели себя как при ручных кликах, без специального back-стека.

- `CollectionCompletePopup.onBtnClick()` → `ProfilePopup.publish` с `openTab:
  CollectionsSection.TAB_NAME`, `collectionSection: { focus: { type: data.section, id: data.collectionId } }`.
- `ProfilePopup` — `collectionSection?: ICollectionSectionConfig` передаётся в `showCollections(config)`
  при клике по табу и при открытии по `openTab` (как `achievementSection`).
- `CollectionsSection` — конфиг в `config`; `onPreload()` при `config.focus` вызывает `focus()` вместо
  `showList()`. `focus()` всегда сначала `showList()`, затем при `focus.id` — `showUSSROperations`/
  `showExperimentalTanks(undefined, { focus: { id } })`. Без `focus.id` или для `EXPERIMENTAL_AIRPLANES`
  остаётся список.
- `ICollectionsTypeSectionConfig { width?; height?; focus?: { id? } }` (все поля необязательны — решение
  пользователя вместо `Partial<...>`) — размер и фокус в одном конфиге. Наследники принимают `config?` и
  вызывают `super(section, data, { ...config, width, height })`; `focusId` = `config?.focus?.id`.
- Альбомы: `onCreate()` после `showAlbums()` вызывает `focusCollection(focusId)`; `showCollection` ставит
  `setBackAction(() => this.showAlbums())`. Танки: `focusCountry()` + `scrollToFocusCollection()`
  (`#cls-collectionsexperimentaltankssection`). Секция самолётов в фокусе не участвует.

### Нотификатор наград коллекций {#reward-notification}

Готовая к клейму награда подсвечивается на трёх уровнях — по образцу достижений
(`.claude/docs/achievements-architecture.md#s7-3-achievementslistsection`). Контракт:
`Notifications.COLLECTION_ID = "collection"`, объект `{hasReward: boolean, rewardSections: number[]}`
(`rewardSections` — значения `CollectionsType`); нет наград — сервер нотификацию удаляет. Пересчёт — на
сервере (вне этого документа).

- **Плитка секции** — `CollectionsListSection`, спрайт `notify` (`#cls-collectionslistsection`).
- **Вкладка "Коллекции"** — `ProfilePopup.handleUserNotifications`: `tabSelector.showNotifiedTab(
  CollectionsSection.TAB_NAME, hasReward)`.
- **Аватарка в шапке** — `HeaderProfile`: индикатор горит при `ACHIEVEMENT_ID.hasDone` ИЛИ
  `COLLECTION_ID.hasReward` (общий с достижениями).

## 2. Использованные референсы {#s2}

- Внешнего референса нет — бизнес-логика по ТЗ пользователя, сведённому в ГДД.
- `EXPERIMENTAL_TANKS` сделан по образцу `USSR_OPERATIONS`/`CollectionAlbum`: "Section → Collection" с
  тонкими абстрактными базами, специфика — в наследниках.
- `CollectionCompletePopup` — структура `AchievementCompletePopup`; дизайн — текстовое описание
  пользователя. Ассеты `collection_fill_icon.png`, `Vector_rigth_yellow.png` — в обычном атласе
  `collection/collections_screen` (пакет `CollectionsScreen`, правка `config.yaml` не нужна,
  `.claude/docs/asset-packaging.md#regular-atlas`).
- Загрузка фото предмета: `TrainCollectionItemPopup.UIItemPhoto`/`CollectionAlbum.UIItem`.
  `ItemsPresets.createImageCollectionItem` не используется — заглушка
  (`.claude/docs/items-presets-architecture.md#collection-item-todo`).

## 3. Использованные паттерны {#s3}

- **Preload → Build**: `CollectionsSection`, `CollectionsListSection`, `CollectionsTypeSection`,
  `Collection` — `PreloadableLayout`, UI строится после ответа сервера.
- **LayoutSlot для переключения "страниц"** (`put(view)`): `CollectionsSection.slot`,
  `CollectionSectionPopup.contentSlot`, `CollectionsUSSROperationsSection.slot`/`albumSlot`.
- **Абстрактная пара "Section vs Item"**: `CollectionsTypeSection.getSectionData()` и
  `Collection.getCollectionData()` — шаблонные хуки, логика в наследниках (Strategy).
- **Dev-tools**: спрайт-кнопка → `/ingame/devTools/...`; клиент после dev-запроса ничего не эмитит,
  обновление приходит push-ом (секция — `CollectionsTypeSection`, коллекция — `Collection`).
- **Получение награды**: запрос → `ResultUtils.isOk` + `RewardUtils.getResource` → `FlyIconsAnimation.play`
  + `Globals.bag.holdResource/releaseHold` → состояние обновляется push-ом (без патча). Правило:
  `holdResource` — всегда синхронно в обработчике ответа, до любой асинхронной паузы/анимации/загрузки
  (push `/events/bag/update` приходит сразу после ответа; поздний hold оставляет запись `UserBag` с
  `applied=false`, `releaseHold` её пропускает и она занижает последующие апдейты). Если визуал может не
  показаться — снимать hold явно (`#cls-traincollectionitempopup-changes`).
- **ScrollableArea с фиксированным вьюпортом**: `CollectionAlbum.UIScrollArea()`,
  `CollectionsExperimentalTanksSection.UICountryScroll()` — `fixedWidth`/`fixedHeight` +
  `calculateBounds: true` (`.claude/docs/asset-packaging.md`, "Частые причины ...").
- **Загрузка ассетов** (`.claude/docs/asset-packaging.md`): фото альбомов — async per-id
  `Creator.spriteAsync` (пакет `CollectionItem_<itemId>`, `config.yaml` + `LoadAssetPackage.ts`). Общие
  атласы (`CollectionsScreen`, `CollectionAlbums`, `CollectionAlbumsBackground`, `CollectionCoinIcon`,
  `CollectionItemTank_<min>_<max>`) — обычные, грузятся в `ProfilePopup.loadAssets()`, читаются `Creator.sprite`.
- **Push-события через `GameEvents`** (подписка — `.claude/docs/server-push-events-subscription.md`).
  Событие-триггер перезапроса без локальных патчей: `COLLECTION_UPDATED`/`COLLECTION_SECTION_UPDATED`/
  `COLLECTION_SECTION_RESTARTED` несут только id, клиент их не эмитит; подписчики перезапрашивают данные
  (`#cls-gameevents`). Порядок событий и ответов не гарантирован (`#s8` п.15).
- **Ручное дублирование серверного enum**: `enum Country` (`#s8` п.2).
- **Generic-свитч по `itemType`**: в `ItemsPresets.createImageLayout`/`createRewardsLayout` есть `case
  ItemType.COLLECTION_ITEM`.

## 4. Полный список созданных/затронутых классов {#s4}

Под `src/views/home_screen/popups/profile/collections/`, если не указано иное:

- `collection.d.ts`, `collection_type/collection_album.d.ts`,
  `collection_type/collection_experimental_tanks/collection_experimental_tank.d.ts` — JSON-контракты
  (`#cls-collectiondts`).
- `CollectionsType.ts`, `CollectionsSection.ts`, `CollectionsListSection.ts`, `CollectionSectionPopup.ts`.
- `collection_section_type/` — `CollectionsTypeSection` (abstract), `CollectionsUSSROperationsSection`,
  `CollectionsExperimentalTanksSection`, `CollectionsExperimentalAirplanesSection` (заглушка).
- `collection_type/` — `Collection` (abstract), `CollectionAlbum`, `CollectionAlbumCard`,
  `collection_experimental_tanks/CollectionExperimentalTank`.
- `src/utils/CollectionUtils.ts` — `CollectionUtils`, `enum Country`, `CollectionTabSelector` (фактически
  общий виджет вкладок профиля: Profile/Codex/Achievements/Collections).

Вне папки коллекций (изменения под коллекции): `CollectionCompletePopup`, `TrainCollectionItemPopup`,
`ItemsPresets`, `GameEvents`, `HeaderAchievementsBar`, `TankGetPopup`, `HomeScreen`, `Notifications`
(`COLLECTION_ID`), `ProfilePopup`, `HeaderProfile` — по разделам `#cls-*` и в карте файлов (`#s10`).

Ранг монеты — `item.stars.rank` (у собранной) и `CollectionExperimentalTankJSON.rank` (у карточки).

## 5. Использование ссылок (якорей) {#s5}

Навигация по разделу 7 — якоря `#cls-<ИмяКласса>` у каждого заголовка `###`.

## 6. Оглавление по классам {#s6}

- [collection.d.ts + collection_album.d.ts + collection_experimental_tank.d.ts (JSON-контракты)](#cls-collectiondts)
- [CollectionsType (enum)](#cls-collectionstype)
- [CollectionsSection](#cls-collectionssection)
- [CollectionsListSection](#cls-collectionslistsection)
- [CollectionSectionPopup](#cls-collectionsectionpopup)
- [CollectionsTypeSection (abstract)](#cls-collectionstypesection)
- [CollectionsUSSROperationsSection](#cls-collectionsussroperationssection)
- [CollectionsExperimentalTanksSection](#cls-collectionsexperimentaltankssection)
- [CollectionsExperimentalAirplanesSection (заглушка)](#cls-collectionsexperimentalairplanessection)
- [Collection (abstract)](#cls-collection)
- [CollectionAlbum](#cls-collectionalbum)
- [CollectionAlbumCard](#cls-collectionalbumcard)
- [CollectionExperimentalTank](#cls-collectionexperimentaltank)
- [CollectionUtils](#cls-collectionutils)
- [CollectionTabSelector](#cls-collectiontabselector)
- [CollectionCompletePopup](#cls-collectioncompletepopup)
- [TrainCollectionItemPopup (изменения)](#cls-traincollectionitempopup-changes)
- [ItemsPresets (изменения)](#cls-itemspresets-changes)
- [GameEvents (изменения)](#cls-gameevents)
- [TankGetPopup — флаг bgClose](#cls-tankgetpopup-bgclose)
- [HeaderAchievementsBar — обработка collectionSetCompleted](#cls-headerachievementsbar-set-completed)
- [HomeScreen — dev-кнопка DevOnCollectionComplete (временно)](#cls-homescreen-dev-collection-complete)
- [HomeScreen — dev-выбор секции для collectionSummon](#cls-homescreen-dev-summon-section)

## 7. Назначение каждого класса и его методов {#s7}

### collection.d.ts / collection_album.d.ts / collection_experimental_tank.d.ts {#cls-collectiondts}
Глобальные ambient-интерфейсы, по файлам (по типу секции, как серверные Page):
- `collection.d.ts` — общие: `CollectionListJSON`, `CollectionSectionListItemJSON`, `CollectionSectionJSON`,
  `CollectionJSON`, `CollectionItemJSON`, `CollectionSetCompletedJSON`, `CollectionUpdatedJSON`,
  `CollectionSectionEventJSON`, `CollectionTrainJSON`;
- `collection_album.d.ts` — `CollectionAlbumsSectionJSON`, `CollectionAlbumJSON`, `CollectionAlbumFullJSON`;
- `collection_experimental_tank.d.ts` — `CollectionExperimentalTanksSectionJSON`,
  `CollectionExperimentalTanksCountryJSON`, `CollectionExperimentalTankJSON`,
  `CollectionExperimentalTankRewardJSON`, `CollectionExperimentalTankCompareJSON`,
  `CollectionExperimentalTankResolveJSON`.

Общие:
- `CollectionListJSON`/`CollectionSectionListItemJSON` — ответ `/ingame/collections`: `section` +
  необязательный `sectionEndTime`, без содержимого коллекций.
- `CollectionSectionJSON` — `section`, `collections?` (необязателен: ответ `/getSectionProgress`
  содержимого коллекций не несёт).
- `CollectionJSON` — `id`, `name?` (нет в `collectionInfo` ответа summon у альбома), `hasAvailableReward`.
- `CollectionItemJSON extends ItemJSON` (без `uid`: сервер отдаёт `CollectionItem` как `Item`, не
  `BagItem`) — `name`/`collectionId`/`country`/`stars`.
- `CollectionUpdatedJSON` (`collectionId`) — push `collectionUpdated`; `CollectionSectionEventJSON`
  (`section`) — push `sectionUpdated` и `sectionRestarted` (`#cls-gameevents`).
- `CollectionSetCompletedJSON` — payload push `setCompleted`: `collectionId` (глобально уникален по всем
  секциям), `section`. Данных о награде нет.
- `CollectionTrainJSON` — коллекционная часть ответа `/ingame/train/summon` и
  `/ingame/devTools/collectionSummon` (сервер: `#summon-reply`); лежит под необязательным ключом
  `collectionItem` (корень: `{ collectionItem?, receivedTank?, replaceableTank?, train, account }`). Поля:
  `itemInfo`, `sellReward?` (`ResourceJSON`; **нет**, если предмет лучше имеющегося), `collectionInfo`
  (по факту `CollectionAlbumJSON` или `CollectionExperimentalTankJSON`), `sectionInfo`.
  `TrainJSON.receivedCollectionItem` (`home.d.ts`) — отдельный источник, с этим контрактом не связан;
  `HomeScreen` рисует вагон по `receivedTank ?? receivedCollectionItem`.

Альбомы:
- `CollectionAlbumsSectionJSON` — `sectionStars`/`sectionMaxStars`/`sectionRewardedStage`/`sectionStages`/
  `availableSectionStage: number | null` (индекс стадии, которую можно забрать)/`hasAvailableReward`/
  `sectionEndTime`.
- `CollectionAlbumJSON` (+ `stars`/`maxStars`/`rewardedStage`/`completed`), `CollectionAlbumFullJSON`
  (+ `stages`/`items`).

Эксп. танки:
- `CollectionExperimentalTanksSectionJSON` — `collections`, `hasAvailableReward`, `countries`; звёзд и
  `sectionEndTime` нет.
- `CollectionExperimentalTanksCountryJSON` — прогресс нации с сервера: `country`, `completed` (наборов с
  `everCompleted`), `total`, `notified`. Источник вкладок, прогресса и точки на вкладке (`#tanks-notify`).
- `CollectionExperimentalTankJSON extends CollectionJSON` — карточка: `country`, `rank`, `items:
  (CollectionItemJSON | null)[]`, `notified`, `hasPendingTank`, `everCompleted`, `reward`, `tank`.
  - `everCompleted` — набор хоть раз "получен" (с первого "Получить": танк взят/продан/ждёт решения);
    источник прогресса нации (ГДД `#gdd-exp-reward`).
  - `hasPendingTank` — есть выданный, но не сведённый игроком танк (решение не принято, напр. из-за
    переподключения); клик по "Получить" сразу открывает окно сравнения тем же танком, минуя повторный
    `getCollectionReward` (`#cls-collectionexperimentaltank`, ГДД `#gdd-exp-reward`).
  - `reward: ItemJSON` — превью награды за комплект: `TankJSON` за первый сбор, иначе `ResourceJSON`
    золота. При `hasPendingTank` — сам отложенный танк (с `level`/`stars`).
  - `tank: TankJSON` — сервер отдаёт всегда, без `level`/`stars`; превью полученного танка после первого
    сбора набора.
  - `rank` — ранг всей карточки (детерминирован по `id`); на уровне коллекции, т.к. `items[].stars.rank`
    есть только у собранных монет. Источник иконки ранга в `CollectionExperimentalTank.UIItem`.
  - `notified` — есть новая непросмотренная монета (`#tanks-notify`).
  - Монеты сервер строит вручную в `CollectionExperimentalTank.apiResponse()` (`id`/`name`/`stars`):
    `country`/`collectionId` в них **нет**, несмотря на тип; `stars` — собственный ранг монеты.
- `CollectionExperimentalTankRewardJSON` — ответ `getCollectionReward` для танков: `reward`,
  `nextRankItem` (`CollectionTrainJSON` монеты следующего ранга; `sellReward` = 10 серебра, если монета —
  дубликат, ГДД `#gdd-exp-duplicate`; `null` на последнем ранге), `isRewardPending` (награда — танк,
  выдача отложена до окна сравнения; `reward` при `true` информативен, на сумку/команду ещё не влияет).
- `CollectionExperimentalTankCompareJSON` — ответ `.../compareReward`: `collectionId`, `receivedTank`,
  `replaceableTank` (`null` при свободном слоте) — те же поля, что у конфига окна сравнения из поезда.
- `CollectionExperimentalTankResolveJSON` — общий ответ `.../takeReward` и `.../sellReward`: `collectionId`,
  `rewards: ItemJSON[]` (серебро за вытесненный/проданный танк — `RewardUtils.getResource(rewards,
  ItemId.RESOURCE_SILVER_COINS)`, может отсутствовать), `nextRankItem`. Самой карточки в ответе нет:
  клиент перезапрашивает её по `COLLECTION_UPDATED` (`#cls-collection`).

### CollectionsType {#cls-collectionstype}
`USSR_OPERATIONS = 1`, `EXPERIMENTAL_TANKS = 2`, `EXPERIMENTAL_AIRPLANES = 3` — значение `section` в JSON и
дискриминатор выбора класса секции.

### CollectionsSection {#cls-collectionssection}
Точка входа — вкладка "Коллекции" в `ProfilePopup`, `PreloadableLayout`. `TAB_NAME = "collections"`,
`data: CollectionListJSON`, `config: ICollectionSectionConfig` (`focus?: { type; id? }`).

- `onPreload()` — `/ingame/collections` → `data`; затем `focus()` при `config.focus`, иначе `showList()`.
- `showList()` — `CollectionsListSection` в `slot`.
- `showUSSROperations`/`showExperimentalTanks(previousSection?, config?)`/`showExperimentalAirplanes(
  previousSection?)` — через `openSection`. `showExperimentalAirplanes` ниоткуда не вызывается.
- `focus()` (private) — [#collection-complete-focus-feature](#collection-complete-focus-feature).
- `openSection(sectionType, build, previousSection?)` — `/ingame/collections/getSection` → `build` →
  `CollectionSectionPopup.publish(...)` с `previousSection` и `onClose` (закрыть `ProfilePopup`).

### CollectionsListSection {#cls-collectionslistsection}

> ГДД: [gdd-navigation](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-navigation)

Плитки секций, `PreloadableLayout` без `onPreload` (данные — `section.data`). Нотификатор —
[#reward-notification](#reward-notification).

- `UIMain()` — плитки только для `USSR_OPERATIONS` и `EXPERIMENTAL_TANKS`, прочие `section` пропускаются.
  Каждой плитке — спрайт `notify`; имя элемента `sectionItemName(section)` = `"section" + section`.
- `UIUSSROperations(sectionEndTime)` — плитка с таймером `TimeUtils.timeDDHHMMSS_Mls`, клик →
  `section.showUSSROperations()`. `UIExperimentalTanks()` — без таймера, клик → `showExperimentalTanks()`.
  `UIExperimentalAirplanes()` — **не вызывается** (мёртвый код).
- `onCreate()`/`onDestroy()` — подписка/отписка `Globals.account.onNotificationChangeCall`/
  `offNotificationChange(handleUserNotifications)`, плюс подписка на `COLLECTION_SECTION_RESTARTED`;
  конструктор тоже вызывает `handleUserNotifications()` (до первого события).
- `handleUserNotifications()` — `notify.visible` по `rewardSections.includes(section)`.
- `onSectionRestarted(section)` — свой `/getSectionProgress`, замена элемента `"timer"` через
  `UIUSSROperationsTimer` (ГДД `#gdd-ops-season`).

### CollectionSectionPopup {#cls-collectionsectionpopup}
Модальное окно (`IViewProvider`, `FlashPublisher`/`GameFlash`), хостит одну `CollectionsTypeSection`.

- `onCreate()` — рамка окна; при `previousSection` "назад" по умолчанию возвращает к нему.
- `showSection(section)` — `section.setPopup(this)`, сброс `backAction`, `contentSlot.put`, `start()`.
- `setBackAction(action?)` — переопределение "назад" секцией (без аргумента — дефолт: `previousSection`,
  иначе `destroy()`). `onBack()` — `backAction()`; `onClose()` — `config.onClose()` + `destroy()`.
- `setTitle(text)` — пишет в `layout.child("content.window.header.title", PIXI.Text)` (upper case).
  **Проверка на `undefined` обязательна**: `Layout.destroy()` уничтожает детей `window` по порядку
  (`panel` → `header` → `content`), к моменту `onDestroy()` → `onClose()` → `setDefaultTitle()` секции узел
  `header` уже уничтожен. Та же гонка у любого чтения `layout.child(...)` из `onClose()`/`onDestroy()` секции.
- `setDefaultTitle()` — `setTitle(defaultTitleText())` (`profileScreen.tabs.collections`).
- Остальное: `destroy()`, `UIMain()`/`UIHeader()`, `getAsGameFlash()` (клик по фону = закрытие),
  `publish(screen, config)` (static), `view()`.

### CollectionsTypeSection {#cls-collectionstypesection}
Абстрактная "секция целиком", `PreloadableLayout`. Поля: `section`, `private data`, `popup`, `tweenSystem`,
`private _config` (геттер `config`, `ICollectionsTypeSectionConfig` — в
[#collection-complete-focus-feature](#collection-complete-focus-feature)).

- `getSectionData()` (protected) — возвращает `data`; наследники сужают тип. Прямого доступа к `data` у
  наследников нет.
- `onCreate()`/`onDestroy()` — подписка/отписка `COLLECTION_SECTION_UPDATED` → `onSectionUpdated` и
  `COLLECTION_SECTION_RESTARTED` → `onSectionRestarted` (`#cls-gameevents`); `Layout.destroy` рекурсивен,
  отписка при закрытии попапа.
- `onSectionUpdated(section)` — чужая секция игнорируется; иначе `refreshSectionProgress(() =>
  onSectionDataUpdated())`. `onSectionRestarted(section)` — чужая игнорируется; иначе хук `onRestarted()`
  (в базе пустой; переопределяет `CollectionsUSSROperationsSection`; ГДД
  [gdd-ops-season](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-season)).
- `refreshSectionProgress(onRefreshed)` — `/ingame/collections/getSectionProgress { section }`; ответ после
  уничтожения (`isDestroyed`) или не `ok` отбрасывается; иначе вливается в `data` (`collections` остаются
  прежние) и вызывается `onRefreshed()`. Обновление точечное: только области, зависящие от прогресса
  (шапка, кнопки, вкладки).
- `reloadSection(data)` — полная замена `data` + `onSectionReloaded()` (полная перестройка, как при
  открытии из списка). Зовёт «Собрать всё» в альбомах.
- `onSectionDataUpdated()` / `onSectionReloaded()` (abstract) — точечное обновление после события / полная
  перестройка. Карточки коллекций обновляют себя сами (`#cls-collection`).
- `UIDevToolsSection()` / `UIDevFillSection()` / `UIDevResetSection()` — кнопки
  `collectionSectionFillMax`/`collectionSectionReset` → `devRequest(route)` (`{ section }`, событий не эмитит).

### CollectionsUSSROperationsSection {#cls-collectionsussroperationssection}

> ГДД: [gdd-ops-season](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-season), [gdd-ops-albums](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-albums), [gdd-ops-rewards](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-rewards)

Секция альбомов (`CollectionAlbumsSectionJSON`).

- `onCreate()` — слоты `slot` (`"content"`) и `albumSlot` (`"album"`), `rebuildAlbums()`, при `focusId` —
  `focusCollection(focusId)`.
- `rebuildAlbums()` — `slot.put(UIMain())` + `showAlbums()`: основной экран строится один раз; зовётся из
  `onCreate` и `onSectionReloaded`. Плитки живут и обновляются по push.
- `showAlbums()` — снимает «назад», `albumSlot.putEmpty()` (уничтожает открытый альбом), `content.visible = true`.
- `showCollection(data)` — `CollectionAlbum` в `albumSlot`, `content.visible = false`, «назад» →
  `showAlbums()`. Плитки под скрытым `content` не пересоздаются, после возврата показывают актуальную награду.
- `focusCollection(collectionId)` — `/ingame/collections/getCollection` → `showCollection`.
- `UIMain()`/`UIHeader()`/`UIHeaderTitle()`/`UIHeaderProgress()`/`UIHeaderStage*` — шапка: заголовок,
  таймер, прогресс `sectionStars`/`sectionMaxStars` с отметками стадий.
- `UIHeaderStageUnrewarded(...)` — кнопка клейма стадии при `availableSectionStage === stageIndex` (индекс
  отдаёт сервер, на клиенте не считается); клик → `/ingame/collections/album/getSectionReward { section,
  stage }`; после `ok` — анимация золота, обновление шапки — по push `sectionUpdated`.
- `onSectionDataUpdated()` — точечно заменяет `title`/`progress` в `content.header` и `collectAllBtn`
  (`replaceByName`) + `refreshForce()`; сетка альбомов не трогается.
- `onSectionReloaded()` — `rebuildAlbums()` (в т.ч. сетка из свежих `collections`).
- `onRestarted()` — `refreshSectionProgress(updateHeaderTitle)`: обновляет только таймер в заголовке
  (`replaceByName("title", UIHeaderTitle())`), остальное — по `sectionUpdated`.
- `UIAlbums()` — сетка `CollectionAlbumCard` (имя `"album" + id`, `openAlbum` → `focusCollection(id)`).
- `UICollectAllBtn()` — `/ingame/collections/album/getAllRewardInSection`, активна при `hasAvailableReward`;
  ответ `{rewards, data}` (типизирован `any`; решение пользователя — полная подмена) → `ResultUtils.isOk` →
  анимация золота → `reloadSection(response.data)`.
- `animationGetReward(layout, count)` — анимация золота (дубль `CollectionAlbumCard.UIReward`, `#s8` п.13).

### CollectionsExperimentalTanksSection {#cls-collectionsexperimentaltankssection}

> ГДД: [gdd-navigation](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-navigation), [gdd-exp-coins](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-coins), [gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward)

Секция монет по нациям (`CollectionExperimentalTanksSectionJSON`); коды наций — `enum Country`
(`#cls-collectionutils`). Вкладки, прогресс и индикатор нации берутся из серверного `countries`, не
считаются на клиенте. Поля: `slot` (`LayoutSlot` "content"), `tabSelector`, `currentCountry`. Слои наций
создаются один раз в `UIMain()` как дети слота (`"country" + id`); `showCountry` только переключает `visible`.

- `onCreate()` — `slot = addSlot({ name: "content" }, { y: 17 })`, `showTanks()`. Своих подписок нет
  (только базовая `COLLECTION_SECTION_UPDATED`).
- `showTanks()` — `currentCountry = focusCountry() ?? countries[0]?.country ?? 0` (ДО `slot.put(UIMain())`,
  чтобы активная вкладка совпала с нацией), `slot.put(UIMain())`, `showCountry`, `scrollToFocusCollection()`.
  Без `focusId`/при ненайденном id — нация первой коллекции.
- `focusCountry()` — `country` коллекции с `focusId` либо `undefined`.
- `scrollToFocusCollection()` — при `focusId` прокручивает `scroll` нации к карточке: смещение = сумма
  высот предыдущих карточек (`list.child("tank" + id)`) + `list.spacing.y`; `-offset` зажимается снизу
  `scroll.getMinBounds()` (тот же приём в `AchievementsTypeSection.focus()`).
- `onOpen()`/`onClose()` — `popup.setTitle(collectionScreen.sections.experimentalTanks.collectionName)` /
  `popup.setDefaultTitle()`.
- `UIMain()` — слои наций (`UICountryTanks`) + таб-бар снизу (`"tabs"`). `UICountryTanks(country)` =
  `UICountryHeader` (`"header"`) + `UICountryScroll` (`"scroll"`).
- `UITabSelector()` — `CollectionTabSelector` по `countries` (порядок сервера): имя `"tab" +
  Country[country]`, иконка `atlas/tech_info/flags/small/<code>.png`, `active` — `country == currentCountry`,
  `notified` — `hasCountryNotify`. Ширина вкладок пересчитывается на `EVENT_AFTER_REFRESH` (не более 86).
- `showCountry(country)` — `currentCountry`, `markCountryViewed(country)`, `visible` слоёв, `refreshForce()`.
  Сброс точки вкладки идёт через событие после ответа сервера, не здесь.
- `getCountryLayout(country)`, `getCountryProgress(country)` (элемент `countries`),
  `getCollectionsForCountry(country)` (фильтр `collections`).
- `UICountryHeader`/`UIProgressHeader` — флаг, `country.<code>`, `AnimatedProgressBar` "получено эксп.
  танков / наборов нации" (`getCountryProgress().completed`/`.total` с сервера; наборы с `everCompleted`
  считает сервер, в т.ч. ждущий решения танк; ГДД `#gdd-exp-reward`).
- `UICountryScroll(country)` — вертикальный `ScrollableArea` (fixed-вьюпорт) с карточками
  `CollectionExperimentalTank` (имя `"tank" + id`); список в `scroll.content` с именем `"tanks"`.
- `onSectionDataUpdated()` — точечно: `replaceByName("header", UICountryHeader(country))` у каждого слоя и
  `replaceByName("tabs", UITabSelector())`, `refreshForce()`. Нация, вкладка и карточки сохраняются.
- `onSectionReloaded()` — `showTanks()`.

#### Индикатор новой монеты на вкладке нации {#tanks-notify}
- `hasCountryNotify(country)` — `getCountryProgress(country)?.notified ?? false` (серверный флаг нации).
- `markCountryViewed(country)` — если флаг был: `/ingame/collections/experimentalTank/
  markCollectionItemViewed { country }`; событий не эмитит, локального патча `notified` нет: сервер шлёт
  push `sectionUpdated`, секция перезапрашивает `countries`, `onSectionDataUpdated()` пересобирает таб-бар.
- Сервер (серверный `#coin-new-flag`): `notified` ставится при получении **новой** (не дубликата и не
  улучшения) монеты — дроп поезда и dev-выдачи; не ставит монета следующего ранга при клейме. Сброс —
  клейм комплекта, `markCollectionItemViewed`, dev `collectionReset`.

### CollectionsExperimentalAirplanesSection {#cls-collectionsexperimentalairplanessection}
Заглушка: конструктор (`width: 350, height: 520`); `getSectionData()` не сужен, `onCreate` не
переопределён, хуки `onSectionDataUpdated()`/`onSectionReloaded()` пустые. Недостижима (`#s1`).

### Collection {#cls-collection}
Абстрактная "одна коллекция", `PreloadableLayout`; конструктор `(data, popup, size: CollectionSize)`.

- `getCollectionData()` / `onCollectionDataUpdated()` (abstract) — тип данных / перерисовка своей карточки.
- `onCreate()`/`onDestroy()` — подписка/отписка `COLLECTION_UPDATED` → `onCollectionUpdated(collectionId)`
  (чужой id игнорируется; свой → `refreshCollection()`).
- `refreshCollection()` (protected) — `/ingame/collections/getCollection { collectionId }`; ответ после
  уничтожения (`isDestroyed`) или не `ok` отбрасывается; иначе `this.data = response` →
  `onCollectionDataUpdated()`. Применяется и в ветке ошибки take/sell у танков.
- `setBackAction(action?)` — прокси к `popup`.
- `UIDevToolsCollection()` + `UIAddNewRandomItem()`/`UIAddNewBestItem()`/`UIAddAllBestItems()`/
  `UIResetCollection()` — dev-кнопки `collectionAddItem`/`collectionAddBestItem`/`collectionFillMax`/
  `collectionReset`; `devRequest(route)` — `{ collectionId }`, событий не эмитит.

### CollectionAlbum {#cls-collectionalbum}

> ГДД: [gdd-ops-albums](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-albums), [gdd-ops-rewards](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-rewards)

Полноэкранный альбом (`CollectionAlbumFullJSON`). `onCreate()`/`onCollectionDataUpdated()` — сборка/
пересборка `content`.

- `UIMain()`, `UIHeader()` (с dev-кнопками), `UIHeaderTitle()` (перевод
  `collectionScreen.sections.ussrOperations.collections.<id>.name`, не `name`), `UIHeaderProgress()`,
  `UIHeaderStage*` — прогресс `stars`/`maxStars` с отметками `stages`.
- `UIScrollArea()` — скролл с фоном и списком. `UIItems()` — предметы со смещением влево/вправо
  ("разворот"); `null` → `UIHideItem()` (пустой слот с "?").
- `UIItem(item)` — `spriteAsync` `.../collection_<albumId>/<itemId>/<itemId>_small.png` (пакет
  `CollectionItem_<itemId>`) + звёзды `item.stars.count`.

### CollectionAlbumCard {#cls-collectionalbumcard}

> ГДД: [gdd-ops-albums](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-albums), [gdd-ops-rewards](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-rewards)

Плитка альбома в сетке секции (`CollectionAlbumJSON`), 114×110; наследник `Collection`. Конструктор
`(data, popup, openAlbum: () => void)` (`openAlbum` задаёт секция).

- `onCreate()` — `super.onCreate()` + `add(UIMain(), { name: "content" })`; `onCollectionDataUpdated()` —
  `replaceByName("content", UIMain())`.
- `UIMain()` — обложка (палитра по серверному `completed`), `UITitle()`, `UIButton()`, `UIProgress()`, при
  `hasAvailableReward` — `UIReward()`; при `completed && !hasAvailableReward` — затемнение + `chekpoint.png`.
- `UITitle()` — перевод по `data.id`. `UIButton()` — альбом/фото (при `stars != 0`) с маской, клик →
  `openAlbum()`. `UIProgress()` — `AnimatedProgressBar` `stars`/`maxStars`.
- `UIReward()` — клейм `/ingame/collections/album/getCollectionReward { collectionId, stage: rewardedStage }`;
  после `ok` — анимация золота (hold `GoldenCoinsOffer::RESOURCE_GOLDEN_COINS` + `FlyIconsAnimation`);
  обновление — по push. Ответ `{reward}` — `any` (решение пользователя).

### CollectionExperimentalTank {#cls-collectionexperimentaltank}

> ГДД: [gdd-exp-set](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-set), [gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward)

Карточка монет внутри секции танков (`CollectionExperimentalTankJSON`), 360×90. Конструктор `(data, popup)`.
Новые данные — событие `COLLECTION_UPDATED` → базовый `refreshCollection()`; карточка событий не эмитит
(кроме `HANGAR_UPDATE` после take, `#cls-gameevents`). `onDestroy()` снимает оставшиеся hold-ы (`#s8` п.12).

- `UIMain()` — подложка, `UIHeader()`, `UIItems()`, `UIProgress()`, `UIReward()`.
- `UIHeader()` — плашка `header_pallet_complete`/`header_pallet_progress` по `hasAvailableReward`, перевод
  `collectionScreen.sections.experimentalTanks.collections.<id>.name` (поле `name` не используется); при
  `Globals.isDevTools()` — доп. `UIDevToolsCollection()` (масштаб 0.3).
- `UIItems()` — ряд из `items`; папка ассетов считается один раз `CollectionUtils.__assetGroupTank(id)`.
- `UIItem(item, index, folder)` — подложка ранга `atlas/collection/collection_coin_icon/<rank>.png` + иконка
  `atlas/collection/collection_items/<folder>/<index + 1>.png`:
  - ранг — из `getCollectionData().rank`, НЕ из `item.stars.rank` (`item` может быть `null`);
  - индекс 1-based (файлы `1.png`..`6.png`); папка — от id карточки, не от `item.country`;
  - несобранная монета — обе картинки с tint `Const.COLOR_TAUPE_GREY`.
- `UIProgress()` — `collectionScreen.progressComplete` при `hasAvailableReward`, иначе "собрано/всего".
- `UIReward()` — рамка (`reward_frame_done.png` при `hasAvailableReward`, иначе `reward_frame.png`) →
  `UIRewardItem()` → при `isTankReceived()` поверх `pallets/album_inactive_bg.png` (`setSize(90, 90)`,
  `alpha 0.5`) и `icons/chekpoint.png` (как у собранной `CollectionAlbumCard`) → `UIRewardCaption()`; при
  `hasAvailableReward` — кнопка, клик → `claimReward(layout)`. Золото в строке видно только при
  `hasAvailableReward` (ГДД `#gdd-exp-reward`).
- `isTankReceived()` — `!hasAvailableReward && everCompleted`: набор уже собирался, забрать нечего.
- `UIRewardCaption()` — `collectionScreen.getReward` (`COLOR_GOLD`) при `hasAvailableReward`; иначе
  `COLOR_SKY_BLUE`: `collectionScreen.tankReceived` при `isTankReceived()`, либо `collectionScreen.itemsLeft`
  + число пустых слотов.
- `UIRewardItem()` — при `isTankReceived()` → `ItemsPresets.createTankLayout(getCollectionData().tank)`;
  иначе по `reward.itemType`: `TANK` → `createTankLayout(reward)` (без уровня и звёзд — их разыгрывает
  сервер при выдаче), иначе `createRewardsCustomLayout([reward])`. При `hasPendingTank` `reward` — сам
  отложенный танк с уровнем и звёздами.
- `claimReward(layout)` — ГДД `#gdd-exp-reward` п. "если решение не принято". При `hasPendingTank` — сразу
  `compareReward(from)`. Иначе `/ingame/collections/experimentalTank/getCollectionReward { collectionId }`;
  при `ok` — `showReward(response, from)`. Событий нет. `from` — мировые координаты кнопки, источник для
  `FlyIconsAnimation`.
- `showReward(response, from)` — порядок зависит от типа награды (ГДД: золото — сначала монета, потом
  золото; танк — сначала сравнение, потом монета):
  - `isRewardPending` (танк) — `compareReward(from)` и выход; `nextRankItem` придёт в ответе take/sell;
  - иначе hold серебра под `nextRankItem.sellReward` синхронно (до любого попапа), тег
    `"TrainCollectionItemPopup::RESOURCE_SILVER_COINS"`;
  - золото (`RESOURCE_GOLDEN_COINS`) — hold `"CollectionExperimentalTank::RESOURCE_GOLDEN_COINS"`,
    `FlyIconsAnimation.HEADER_GOLDEN_COINS` от `from` (hold снимается в колбэке); монета следующего ранга
    показывается сразу, без ожидания полёта;
  - `nextRankItem` не `null` → `showNextRankItem`.
- `compareReward(from)` — `/ingame/collections/experimentalTank/compareReward { collectionId }`; при ошибке
  выход; при успехе `TankGetPopup.publish(screen, { receivedTank, replaceableTank, bgClose: false, onAccept:
  …takeReward, onRefuse: …sellReward })`. `bgClose: false` (`#cls-tankgetpopup-bgclose`): нештатный
  destroy окна = решение не принято, танк остаётся отложенным на сервере, у набора кнопка «Получить»
  (ГДД `#gdd-exp-reward`).
- `resolvePendingReward(route, isTake, from)` — общий обработчик `onAccept`/`onRefuse`: шлёт `route`
  (`.../takeReward` или `.../sellReward`) `{ collectionId }` → `CollectionExperimentalTankResolveJSON`; при
  ошибке (не `ok` или исключение) — `refreshCollection()`, чтобы строка не осталась неконсистентной. При
  успехе: если `isTake` — `GameEvents.emitter.emit(HANGAR_UPDATE)` (как `AssemblyPopup`/`OnTrainAccept`),
  hold серебра под `nextRankItem.sellReward`, `flySilver(response.rewards, from, …)` →
  `showNextRankItem(nextRankItem)` по окончании полёта.
- `showNextRankItem(nextRankItem)` — убирает тег серебра из `activeHoldTags` (дальше hold снимает
  `TrainCollectionItemPopup` с тем же тегом) и `TrainCollectionItemPopup.publish(screen, nextRankItem)`.
- `flySilver(rewards, from, onEnd)` — серебро из `rewards`; нет — сразу `onEnd()`. Есть — hold
  `"CollectionExperimentalTank::RESOURCE_SILVER_COINS"`, `FlyIconsAnimation.HEADER_SILVER_COINS` от `from`
  (масштаб 0.5, как `HomeScreen.OnTrainAccept`), по завершении `releaseHold` + `onEnd()`.
- Hold-ы (`#s8` п.12): `activeHoldTags: Set<string>`; приватные `holdResource(tag, id, count)` и
  `releaseHold(tag)` (снимает только если тег в наборе); `onDestroy` снимает все оставшиеся.

### CollectionUtils {#cls-collectionutils}
Статические UI-хелперы экранов коллекций (`src/utils/CollectionUtils.ts`).

- `TANK_CARD_ID_RANGES` (модульная константа) — 8 блоков id карточек по нациям (сервер —
  `ExperimentalTanksSectionType.EXPERIMENTAL_TANK_RANG_COLLECTION`); блок задаёт папку с 6 картинками
  монет. Каждый элемент хранит `load` со строковым литералом `addAssetPackage("CollectionItemTank_<min>_<max>")`:
  динамическое имя пакета webpack-плагин не подменяет (`.claude/docs/asset-packaging.md#troubleshooting`),
  а `LoadAssetPackage.ts` только для async per-id пакетов.
- `__assetGroupTank(collectionId)` — имя папки `"collection_<min>-<max>"` (только `EXPERIMENTAL_TANKS`);
  `__loadAssetGroupTank(collectionId)` — ставит в загрузку атлас `CollectionItemTank_<min>_<max>`
  (`TrainCollectionItemPopup.loadAssets()`; `ProfilePopup.loadAssets()` грузит все 8 пакетов сам).
- Для **альбомов** хелпера нет: путь и async-пакет строятся из данных (`.../collection_<collectionId>/
  <item.id>/<item.id>[_small].png`, пакет `CollectionItem_<item.id>`). Решение пользователя (2026-09-25):
  отрисовку коллекционных предметов вынести в статические функции `CollectionUtils` вместо
  `ItemsPresets.createImageCollectionItem` — перенос сделает пользователь
  (`.claude/docs/items-presets-architecture.md#collection-item-todo`).
- `button(config)`, `buttonStatus(layout, status)` (интерактивность при `status > 0`; `BUTTON_STATUS_BLUE`
  текстуру не меняет), `dollars(config)`, `panelPreset(type, config)` — аналоги `ButtonPresets`/
  `PanelsPresets` в стиле экрана коллекций, независимая реализация
  (`.claude/docs/panels-buttons-presets-architecture.md#collectionutils-analog`).
- `enum Country` — `FR=0, PL, DE, CZ, JP, IT, US, GB, USSR, CN=9`, вручную повторяет серверный (`#s8` п.2).

### CollectionTabSelector {#cls-collectiontabselector}
Горизонтальный таб-бар (коллекции и `ProfilePopup`). Поле `tabs: Layout[]`, конфиги `ICollectionTabConfig`.

- Конструктор — вкладки из конфигов, пересчёт шрифтов на `EVENT_AFTER_REFRESH`.
- `activateTab(tabName)` — `bg_on` только у этой вкладки; `showNotifiedTab(tabName, showNotified)` —
  индикатор уведомления.
- `UITab(config)`, `UIActiveTab`/`UIInActiveTab` — вкладка и визуал состояний; `fittedFontSize(text, base)`
  — шрифт под 80% ширины/высоты родителя; `recalculateTabTextFontSizes()` — общий минимум для всех; `view()`.

### CollectionCompletePopup {#cls-collectioncompletepopup}

> ГДД: [gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward)

Тост "комплект собран" (`src/views/popups/CollectionCompletePopup.ts`); логика —
[#set-completed-feature](#set-completed-feature). Отрисовки награды нет и быть не может (в payload её нет).

- `private constructor(data, config, screen: SceneImpl)` — поле `scene` (`SceneImpl`, не `HomeScreen`); слот
  `bg`, `UIMain()`, `refreshForce()`, затем в `bg` — `PanelsPresets.PNL_WINDOW_STANDARD_NO_HEADER({ width,
  height: boundsRect().height, alpha: 0.5 })`. `Button.newButton(this, onBtnClick)` на весь тост.
- `UIMain()` — строка `LEFT_TO_RIGHT`, `spacing: [5]`: `collection_fill_icon.png` → `UITitle()` →
  `Vector_rigth_yellow.png`. `UITitle()` — два `TextBuilder`: `collectionScreen.popup.collectionComplete`
  (`COLOR_LIGHT_SILVER`) и `collectionScreen.popup.getReward` (`COLOR_GOLD`).
- `show()` — fade+slide `Tweens.c` + `Easing.outQuad()`, по окончании `hide(500, 5000)`. `hide(time,
  timeDelay)` — fade+slide с задержкой; в `onEnd` сохраняет `parentLayout`, `destroy()`, `refreshForce()`
  родителя и его родителя (`ScrollContent` и `ScrollableArea` шапки). Вызывается только из `show()`,
  защита `isDestroyed` не нужна.
- `onBtnClick()` — `ProfilePopup.publish(scene.getOpenScreen() as HomeScreen, { userId, openTab,
  collectionSection: { focus } })` (`#collection-complete-focus-feature`). Тост при клике **не закрывается**.
- `static create(data, screen)` — `width: 150`, `resizable`, `calculateBounds`. Публикацию делает
  вызывающий (`HeaderAchievementsBar`).

### TrainCollectionItemPopup — изменения {#cls-traincollectionitempopup-changes}

> ГДД: [gdd-train-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-train-drop), [gdd-exp-duplicate](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-duplicate), [gdd-ops-upgrade](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-upgrade)

Попап "получен предмет коллекции" при summon и после клейма комплекта танков (монета следующего ранга,
`CollectionExperimentalTank.showNextRankItem`) (`FlashLayout`, `publish` → `loadAssets()` →
`FlashPublisher`). Изменения:

- `screen: ScreenImpl` (не `HomeScreen`) — нужны только `scene`/`getHeader()`, попап вызывается с любого экрана.
- `TrainCollectionItemPopupData extends CollectionTrainJSON` + `onExit?: () => void` — вызывается из
  `private onDestroy()` по `Layout.EVENT_DESTROYED` и из `.catch` загрузки ассетов в `publish` (после
  `releaseHold`), то есть ровно один раз при любом исходе. Передаёт его `HomeScreen`
  (`onTrainCollectionItemReceived`, `onExit` ведёт в `clearTrainCart`): снятие груза с вагона и
  продолжение автопризыва поезда
  ([train-architecture.md#m-ontraincollectionitemreceived](train-architecture.md#m-ontraincollectionitemreceived));
  `CollectionExperimentalTank.showNextRankItem` его не передаёт.
- `isCoin()` — `sectionInfo.section === EXPERIMENTAL_TANKS` (иначе альбом); `getSectionKey()` —
  `experimentalTanks`/`ussrOperations`; `isBetter()` — `sellReward === undefined`. Признак дубликата
  одинаков для монет и фото: сервер (`CollectionUserComponent.receiveSummonedItem`) кладёт `sellReward`
  при `!isBetter` для любой секции; для альбома это фото, которое разбирается на серебро
  ([gdd-train-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-train-drop)).
- `UIHeader()` — `homeScreen.trainCollectionPopup.newCoin`/`newPhoto`.
- `UIItemCoin()` — как `CollectionExperimentalTank.UIItem`, масштаб ×4: подложка по `collectionInfo.rank`
  (ранг карточки, не `itemInfo.stars`), иконка по `__assetGroupTank(collectionInfo.id)`, `index` — позиция
  `itemInfo.id` в `collectionInfo.items` (с учётом `null`). `UIItemPhoto()` — `spriteAsync`
  `.../collection_<itemInfo.collectionId>/<id>/<id>.png` + звёзды.
- `UIInfo()` — `collectionScreen.sections.<секция>.collectionName` + `.collections.<collectionInfo.id>.name`.
- `loadAssets()` — монета: `CollectionCoinIcon` + `CollectionUtils.__loadAssetGroupTank(collectionInfo.id)`;
  фото: async `CollectionItem_<itemInfo.id>` через `LoadAssetPackage`.
- Hold серебра за дубликат (`sellReward`) ставит НЕ попап, а вызывающий — синхронно в обработчике ответа
  (`#s3` "Получение награды"):
  - тег — строка `"TrainCollectionItemPopup::RESOURCE_SILVER_COINS"`, вызовы `Globals.bag.holdResource`/
    `releaseHold` пишутся напрямую в каждом месте (константы нет);
  - `sellRewardReleasePending` (true, если есть `sellReward`) — `onDestroy()` снимает hold, если полёт монет
    не стартовал; `publish` — `.catch` на `loadAssets()` снимает hold при ошибке загрузки;
  - `show()` → пауза 500 мс → `playOutcomeAnimation()` (попап закрывается сам): без `sellReward` — полёт
    предмета в шапку; с `sellReward` — сжатие, сброс флага, `HEADER_SILVER_COINS` → `releaseHold` в колбэке.
- `HomeScreen.OnTrainSummon`/`DevOnTrainCollect` — ветвление по `collectionItem !== undefined`
  (аналогично `receivedTank`). В колбэке ответа синхронно `holdResource` (если есть `sellReward`) до
  `animationTrainCart`, в неё передаётся `receivedTank ?? collectionItem?.itemInfo`; из `onEnd` анимации
  оба вызывают общий `onTrainCollectionItemReceived(collectionItem)`: при автопризыве и `sellReward` —
  `releaseHold` без попапа, иначе попап; в обоих случаях дальше `clearTrainCart` (сразу или из `onExit`):
  груз на вагоне гаснет, затем следующий призыв автопризыва или возврат локомотива
  ([train-architecture.md#m-cleartraincart](train-architecture.md#m-cleartraincart)). Пока попап
  открыт, груз стоит на вагоне, как танк при `TankGetPopup`.

### ItemsPresets — изменения {#cls-itemspresets-changes}
Полная документация — `.claude/docs/items-presets-architecture.md`. Для коллекций: `case
ItemType.COLLECTION_ITEM` в `createImageLayout`/`createRewardsLayout` → приватный
`createImageCollectionItem(data)` — заглушка (`Layout` 25×25 без спрайта); перенос отрисовки в
`CollectionUtils` — `#cls-collectionutils`.

### GameEvents — изменения {#cls-gameevents}
`src/plain/GameEvents.ts`:

- `COLLECTION_SET_COMPLETED: EventName<never>` — `never` намеренно, как `ACHIEVEMENTS_EVENT`/`TUTORIAL_EVENT`;
  форма данных фиксируется в подписчике.
- `COLLECTION_UPDATED: EventName<number>` (`collectionId`) — карточка с этим id перезапрашивает себя
  (`Collection.onCollectionUpdated`).
- `COLLECTION_SECTION_UPDATED: EventName<number>` (`section`) — секция перезапрашивает прогресс
  (`CollectionsTypeSection.onSectionUpdated`). Событие несёт только id: источник истины — сервер.
- `COLLECTION_SECTION_RESTARTED: EventName<number>` (`section`) — новый сезон (ГДД `#gdd-ops-season`);
  подписчики — `CollectionsTypeSection` (хук `onRestarted`) и `CollectionsListSection` (`onSectionRestarted`).
- `listenServerEvents()` — подписки `g/ws/events/collections/{setCompleted,collectionUpdated,sectionUpdated,
  sectionRestarted}` → соответствующее событие (`WSSocket.registerHandlers()` переизлучает серверный
  `json.type` как `"g/ws" + json.type`, см. `.claude/docs/server-push-events-subscription.md`).
- Клиентских эмитов этих событий нет нигде (клейм, take/sell, summon, `markCollectionItemViewed`, dev):
  единственные эмиты — в `listenServerEvents()`. Отписка подписчиков — в `onDestroy`.

### TankGetPopup — флаг bgClose {#cls-tankgetpopup-bgclose}
`src/views/home_screen/popups/tank/TankGetPopup.ts`: `HomeTankGetPopupConfig.bgClose?: boolean` (по
умолчанию `true`). При `false` `bgClick` ничего не делает и подпись `system.buttons.close` не рисуется.
Коллекции передают `false` (`CollectionExperimentalTank.compareReward`); остальные вызывающие не затронуты.

### HeaderAchievementsBar — обработка collectionSetCompleted {#cls-headerachievementsbar-set-completed}
`src/shared/header/presets/HeaderAchievementsBar.ts` (`IHeaderPreset`), реализует push-контракт из
`#set-completed-feature`:

- `onCreate()` — `GameEvents.emitter.on` для `ACHIEVEMENTS_EVENT` и `COLLECTION_SET_COMPLETED`, плюс
  `layout.on(Layout.EVENT_DESTROYED, this.onDestroy)`. Приватный `onDestroy()` снимает подписки: пресет не
  `Layout` и `Header.onDestroy()` его не вызывает (как у `HeaderGoldenCoinsBar`/`HeaderProfile`).
- `onCollectionSetCompleted(data)` — без условий и запросов: `CollectionCompletePopup.create(data,
  header.scene)` → `scrollContent.content.add(..., { px: 200 })` → `refreshForce` контента и скролла →
  `show()`. Тот же код, что `onAchievementDone`: тосты делят одну `ScrollableArea`.

Следствие: тост показывается на любом экране с `Header` (`#s8` п.6).

### HomeScreen — dev-кнопка DevOnCollectionComplete (временно) {#cls-homescreen-dev-collection-complete}
В блоке `Globals.isDevTools()` — кнопка `collectionComplete` → `DevOnCollectionComplete()`: эмитит
`COLLECTION_SET_COMPLETED` с `{ collectionId: 18, section: EXPERIMENTAL_TANKS }` (имитация push без
сервера). В коде помечена «ВРЕМЕННО»: убрать после ручной проверки.

### HomeScreen — dev-выбор секции для collectionSummon {#cls-homescreen-dev-summon-section}
Dev-UI (блок `Globals.isDevTools()`): `private devSummonSection: CollectionsType` (по умолчанию
`USSR_OPERATIONS`). Одна dev-кнопка `collectSummon` при каждом нажатии вызывает `DevOnTrainCollect()`
(`/ingame/devTools/collectionSummon { section }`) и переключает секцию по кругу `USSR_OPERATIONS →
EXPERIMENTAL_TANKS` (секция 3 исключена: у сервера нет её типа). Обработчики summon событий коллекций не
эмитят. Сервер: `section` необязателен (по умолчанию `USSR_OPERATIONS`), выдача в обход фильтров боевого
ролла, новая монета получает `notified` (`#tanks-notify`).

## 8. Принятые уязвимости/компромиссы {#s8}

1. **`CollectionsExperimentalAirplanesSection` — заглушка.** Недостижима (сервер не отдаёт секцию 3, плитка
   не строится); `UIExperimentalAirplanes()`/`showExperimentalAirplanes()` — мёртвый код. При возврате
   плитки без реализации секция откроется пустой, а `getSection` для секции 3 сервер вернёт ошибкой. Ждёт ТЗ.
2. **Ручное дублирование серверного enum `Country`** — при изменении порядка на сервере расхождение
   молчаливое (флаги наций перепутаются).
3. **Два пути обновления секции.** Клейм альбома/стадии/сбор ранга не патчат данные локально и ничего не
   эмитят: сервер шлёт push, клиент перезапрашивает (`getCollection`, `getSectionProgress`).
   `getAllRewardInSection` остаётся `{rewards, data}` с полной подменой через `reloadSection` (решение
   пользователя).
4. **Циклический импорт** `CollectionsSection.ts` ↔ `CollectionSectionPopup.ts` — работает (обе стороны
   используют только статическое поле и тип), но хрупко при добавлении top-level кода.
5. **Визуальная проверка тоста в браузере не выполнена** (проверен только `npx tsc --noEmit` и сборка
   ассетов). Перед мержем — вручную через `DevOnCollectionComplete`: анимация, клик → фокус, и что push
   `setCompleted` реально доходит с `{collectionId, section}` (`tsc` WS-пути не проверяет).
6. **Тост показывается на любом экране с `Header`.** Не проверено в рантайме: `onBtnClick()` приводит
   `scene.getOpenScreen()` к `HomeScreen` — на другом экране каст некорректен. Push сервером не
   переотправляется, пропущенные комплекты клиент не запрашивает.
7. **Тост и `TrainCollectionItemPopup` не синхронизированы** и могут быть на экране одновременно (решение
   пользователя). Визуальная приемлемость не проверена (п.5).
8. **`TrainCollectionItemPopupData.onExit`** использует только поезд (продолжение автопризыва,
   [train-architecture.md#m-ontraincollectionitemreceived](train-architecture.md#m-ontraincollectionitemreceived));
   окно монеты следующего ранга из `CollectionExperimentalTank` его не передаёт. Если `HomeScreen` ушёл
   с экрана, пока окно открыто, `onExit` вызовет `clearTrainCart` (в автопризыве — `OnTrainSummon`) ушедшего экрана
   (как `onAccept`/`onRefuse` у `TankGetPopup`); не чинилось
   ([train-architecture.md#tradeoffs](train-architecture.md#tradeoffs) п.2).
9. **Клейм комплекта танков — окно сравнения вместо прямой выдачи** (`#cls-collectionexperimentaltank`).
   Награда-танк всегда откладывается сервером до `takeReward`/`sellReward`, на момент показа `TankGetPopup`
   танк **ещё не выдан**. `TankGetPopup` типизирован `HomeScreen` (работает, т.к.
   `CollectionSectionPopup.screen` — `HomeScreen`).
10. **Hold `sellReward`** (`#cls-traincollectionitempopup-changes`). Решение пользователя —
    `UserBag.releaseHold` не менять (запись с `applied=false` пропускается, поэтому hold ставится
    синхронно, `#s3`). Остаточные риски: если `HomeScreen` уничтожен во время `animationTrainCart`, попап
    не публикуется и hold повисает; тег общий на все экземпляры попапа (два одновременных дубликата делят
    один тег).
11. **Окно сравнения при свободном слоте — одна кнопка "Выбрать"** (копия поведения поезда: `TankGetPopup.
    UIButtons` при `replaceableTank === null`; "Продажа" недоступна). Решение пользователя 2026-10-01:
    оставить как в поезде. Закрытия по фону нет (`#cls-tankgetpopup-bgclose`).
12. **Hold-ы награды эксп. танка снимаются при уничтожении карточки без решения** (`activeHoldTags`).
    Решение пользователя 2026-10-01: серебро в хедере важнее анимации — при `onDestroy` до показа
    монеты/окончания полёта оставшиеся hold-ы снимаются, анимация пропадает. Остаточный риск общий для
    `UserBag` (`bag-architecture.md#userbag-hold-leak`): hold с `applied=false` не снимается; здесь hold
    ставится синхронно, поэтому не применяется только если push по ресурсу не пришёл вовсе.
13. **Дубль анимации награды** `CollectionAlbumCard.UIReward` ↔ `CollectionsUSSROperationsSection.
    animationGetReward` (hold золота + `FlyIconsAnimation`) оставлен, как в `AchievementLine`/`AirDrop`
    (решение пользователя).
14. **Обновление по событию — лишний запрос.** Каждое `COLLECTION_UPDATED` вызывает `getCollection`, каждое
    `COLLECTION_SECTION_UPDATED` — `getSectionProgress`; взамен нет расхождения клиентского патча с
    сервером. Счётчика «побеждает последний запрос» нет, порядок ответов не защищён. Ответы наград
    альбомов (`{reward}`, `{rewards, data}`) типизированы `any`.
15. **Порядок событий и ответов не гарантирован.** Push приходит раньше ответа на запрос, push между собой
    не упорядочены. Принято пользователем: если секцию закрыть во время полёта серебра, карточка
    следующего ранга всё равно покажется, а общий тег `"TrainCollectionItemPopup::RESOURCE_SILVER_COINS"`
    может снять hold поезда раньше времени (`bag-architecture.md#userbag-hold-shared-tag`).

## 9. Связь с ГДД {#s9}

ГДД области — [collections-gdd.md](/workspace/client/.claude/docs/game-design/collections-gdd.md). Правило → клиентская реализация:

| Правило ГДД | Где на клиенте |
|---|---|
| [#gdd-purpose](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-purpose) — список секций: монеты, альбомы, самолёты-заглушка | `CollectionsListSection`, `CollectionsExperimentalAirplanesSection` ([CollectionsListSection](#cls-collectionslistsection)) |
| [#gdd-navigation](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-navigation) — вход в раздел, фокус с тоста | `CollectionsSection`, `CollectionSectionPopup`; фокус на тост — [#collection-complete-focus-feature](#collection-complete-focus-feature) |
| [#gdd-train-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-train-drop) — выпадение предмета из поезда | выбор шанса на сервере; клиент показывает `TrainCollectionItemPopup`, `HomeScreen.OnTrainSummon` ([#cls-traincollectionitempopup-changes](#cls-traincollectionitempopup-changes)) |
| [#gdd-exp-coins](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-coins) — монеты по нациям и качествам | `CollectionsExperimentalTanksSection`, `CollectionExperimentalTank.UIItem`, `CollectionUtils` ([#cls-collectionsexperimentaltankssection](#cls-collectionsexperimentaltankssection)) |
| [#gdd-exp-duplicate](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-duplicate) — дубликат монеты, продажа за серебро | `TrainCollectionItemPopup.isBetter`, `sellReward`, hold серебра; на ранге `null` в `CollectionExperimentalTank` ([#cls-collectionexperimentaltank](#cls-collectionexperimentaltank)) |
| [#gdd-exp-set](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-set) — набор из 6 монет, клейм «Получить» | `CollectionExperimentalTank.claimReward`, `hasAvailableReward`; `collectionSetCompleted` ([#set-completed-feature](#set-completed-feature)) |
| [#gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward) — награда за набор, монета следующего ранга или танк | `CollectionExperimentalTank.claimReward`, `showNextRankItem`, `isRewardPending`; `TankGetPopup` ([#cls-collectionexperimentaltank](#cls-collectionexperimentaltank)) |
| [#gdd-ops-season](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-season) — событие, таймер, новый сезон | `CollectionsUSSROperationsSection.UIHeaderTitle`, `onRestarted`; `COLLECTION_SECTION_RESTARTED` ([#cls-gameevents](#cls-gameevents)) |
| [#gdd-ops-albums](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-albums) — 9 альбомов, 9 фото, прогресс звёзд | `CollectionsUSSROperationsSection.UIAlbums`, `CollectionAlbumCard`, `CollectionAlbum` ([#cls-collectionalbum](#cls-collectionalbum)) |
| [#gdd-ops-upgrade](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-upgrade) — замена и разбор фото | решает сервер; клиент: `TrainCollectionItemPopup.isBetter`, `UIItemPhoto` |
| [#gdd-ops-rewards](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-rewards) — награды за звёзды, клейм стадии и «Забрать всё» | `UIHeaderStageUnrewarded`, `UICollectAllBtn`, `animationGetReward`; нотификатор — [#reward-notification](#reward-notification) |

Правила без клиентской реализации или без описания в этом документе: [#gdd-exp-quality](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-quality) (качества и шансы считает сервер, клиент получает готовый `rank`), [#gdd-exp-tank](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-tank) (метка «Прототип», уровень и звёзды танка), [#gdd-ops-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-ops-drop) (шансы и звёзды фото считает сервер).

## 10. Карта файлов компонента {#s10}

### Файлы прямого влияния

- `src/views/home_screen/popups/profile/collections/collection.d.ts` — ambient-интерфейсы JSON-контрактов (общие, `CollectionItemJSON`, `CollectionSetCompletedJSON`)
- `src/views/home_screen/popups/profile/collections/CollectionsType.ts` — `enum CollectionsType` (типы секций)
- `src/views/home_screen/popups/profile/collections/CollectionsSection.ts` — вкладка профиля «Коллекции», контейнер списка и секции
- `src/views/home_screen/popups/profile/collections/CollectionsListSection.ts` — список секций коллекций
- `src/views/home_screen/popups/profile/collections/CollectionSectionPopup.ts` — попап секции коллекций
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsTypeSection.ts` — базовая абстрактная секция (Strategy), общая логика секций
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsUSSROperationsSection.ts` — секция альбомов «Операции СССР»
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsExperimentalTanksSection.ts` — секция экспериментальных танков
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsExperimentalAirplanesSection.ts` — секция самолётов (заглушка)
- `src/views/home_screen/popups/profile/collections/collection_type/Collection.ts` — базовая абстрактная коллекция
- `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbum.ts` — коллекция-альбом
- `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbumCard.ts` — карточка альбома
- `src/views/home_screen/popups/profile/collections/collection_type/collection_album.d.ts` — типы JSON альбомов
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts` — коллекция эксп. танка (монеты, ранги)
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/collection_experimental_tank.d.ts` — типы JSON эксп. танков
- `src/utils/CollectionUtils.ts` — статические UI-хелперы, `enum Country`, `CollectionTabSelector`
- `src/views/popups/CollectionCompletePopup.ts` — тост «комплект собран»
- `src/views/home_screen/popups/train/TrainCollectionItemPopup.ts` — попап «получен предмет коллекции» (summon и монета следующего ранга после клейма)

### Файлы косвенного влияния

- `src/plain/GameEvents.ts` — события `COLLECTION_SET_COMPLETED`/`COLLECTION_UPDATED`/`COLLECTION_SECTION_UPDATED`/`COLLECTION_SECTION_RESTARTED`
- `src/plain/items/ItemType.ts` — зависимость: тип предмета `ItemType.COLLECTION_ITEM = 6` из другой области
- `src/plain/LoadAssetPackage.ts` — async per-id пакеты `CollectionItem_<id>` (фото альбомов)
- `src/presets/ItemsPresets.ts` — зависимость: стандартная отрисовка предметов `COLLECTION_ITEM` (другая область)
- `src/shared/notifications/Notifications.ts` — `COLLECTION_ID`, нотификатор наград коллекций
- `src/shared/header/presets/HeaderProfile.ts` — индикатор награды коллекций на кнопке профиля (после merge вёрстка перерисована, чтение `COLLECTION_ID.hasReward` сохранено)
- `src/shared/header/presets/HeaderAchievementsBar.ts` — обработка `COLLECTION_SET_COMPLETED`, показ `CollectionCompletePopup`
- `src/views/home_screen/popups/profile/ProfilePopup.ts` — подключает `CollectionsSection` и `CollectionTabSelector`, пакет `CollectionsScreen`; после merge в окне также `ClanEmblems`, запросы клана и `pushHeaderZIndex(false)` (область профиля/кланов, не коллекций)
- `src/views/home_screen/popups/tank/TankGetPopup.ts` — флаг `bgClose` для окна сравнения награды-танка
- `src/views/home_screen/HomeScreen.ts` — подгрузка пакета `CollectionsScreen`, dev-кнопки коллекций, обработка `collectionItem` в summon
- `tools/src/config.yaml` — общий файл: записи пакетов `CollectionsScreen` (`collection/collections_screen`) и `CollectionItem_*`
- `assets-src/raw/lang/ru/ru.json` — общий файл: блоки `collectionScreen.*` и `homeScreen.trainCollectionPopup`/`collectionCompletePopup`
