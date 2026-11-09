# Сумка — клиентская модель `UserBag` и типы `bag.d.ts` (клиент)

> **auto-create** — документ составлен `client-analyst-lead` по существующему коду, 2026-10-13;
> сверен с кодом и сокращён 2026-10-14; актуализирован 2026-10-19 после merge `origin/amnesia/fix`
> (сокращённый формат). Запуском не проверялось.
> Серверная сторона: `/workspace/server/.claude/docs/bag-architecture.md` (`BagUserComponent`, тоже
> auto-create).

ГДД: [`game-design/bag-gdd.md`](game-design/bag-gdd.md) (черновик по примерному описанию,
2026-10-13). Ссылки `#gdd-…` ниже ведут в него.

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

Сумка на клиенте — кэш инвентаря игрока в памяти: ресурсы, танки, самолёты, а после merge — ещё и предметы военной базы
(здания, слоты авиазавода, бусты; сама область — не здесь) ([#gdd-purpose](game-design/bag-gdd.md#gdd-purpose)). Своего экрана нет: в
`src/views/home_screen/popups/bag/` лежат только типы `bag.d.ts`. Модель — `UserBag`, единственный
экземпляр — `Globals.bag`.

Жизненный цикл:

1. `InGameScene` вызывает `Globals.bag.requestData()` (`/ingame/bag/get`); экран загрузки скрывается
   и экран открывается только после ответа. До ответа `InGameScene.handleUserUpdate` не переключает
   экран: проверяет `Globals.bag.isInitialized()`.
2. Дальше сумка меняется только push `/events/bag/update` `{ items, del }` (подписка
   `App.events.on("g/ws/events/bag/update")`): `items` — новые и изменённые предметы целиком, `del` —
   `uid` удалённых.
3. Изменения идут экранам через `GameEvents`: `ITEM_NEW`, `ITEM_UPDATE`, `ITEM_NEW_OR_UPDATE`,
   `ITEM_DELETE` (по предмету), `BAG_UPDATE` (раз на пакет).
4. `Globals.logout()` заменяет `Globals.bag` новым пустым экземпляром (`#logout-leak`).

Клиент сумку не меняет: начисления и траты считает сервер
([#gdd-gain-spend](game-design/bag-gdd.md#gdd-gain-spend)); клиентские проверки «хватает ли ресурса»
только блокируют кнопки ([#dup-can-afford](#dup-can-afford)).

**Удержание ресурса** (`holdResource`/`releaseHold`) — клиентская механика без правила в ГДД, влияет
только на отображение: пока летит `FlyIconsAnimation`, значение ресурса в кэше занижено на размер
награды, чтобы счётчик в шапке вырос в момент прилёта иконок.

<a id="del-resource"></a>
**Ресурс в `del`** ([#gdd-open](game-design/bag-gdd.md#gdd-open)). Сервер присылает в `del` ресурс с
`count = 0` ([#client-contract](#client-contract)). Клиент обрабатывает его как любое удаление:
перед `ITEM_DELETE` пишет удаляемому предмету `count = 0` (после merge это делает любой `del`, для
техники тоже), затем удаляет из кэша. Подписчик `ITEM_DELETE` получает объект с нулевым `count`. Для игрока это ноль: `getResourceCount` отсутствующего ресурса
возвращает `0`, а подписчики `ITEM_DELETE` по ресурсу (шапка, счётчики схем, сборка) выставляют `0`
или пересчитывают по `getResourceCount`. Следующее начисление приходит в `items` и добавляется как
новое (`ITEM_NEW`). Отличить «ресурс с нулём» от «ресурса нет» клиент не может и не пытается. Побочный
эффект — висящий hold ([#userbag-hold-leak](#userbag-hold-leak)).

<a id="references"></a>
## 2. Референсы

Нет: документ описывает существующий код.

<a id="patterns"></a>
## 3. Паттерны

- **Кэш + push-синхронизация**: полная загрузка один раз, дальше дельты. Подписка у `UserBag` —
  первый, «сырой» подход из `server-push-events-subscription.md` (`App.events.on` без отписки).
- **Идентификатор предмета — пара `itemType` + `id`**: числа `id` у ресурсов, зданий и бустов военной
  базы пересекаются (`ItemId` — один enum с повторяющимися значениями), поэтому по одному `id`
  предмет не найти. Type-guard'ы `isResourceId` проверяют `itemType`; для остальных типов — `getItem`.
- **Событийная рассылка** через `GameEvents.emitter`: экран подписывается на `ITEM_*` в
  `onCreate`/конструкторе, отписывается в `onDestroy`/`Layout.EVENT_DESTROYED`, предмет фильтрует
  type-guard'ами `isResourceId`/`isTank`/`isAirplane`. Подписчику `ITEM_NEW_OR_UPDATE` по ресурсу или
  технике нужна пара `ITEM_DELETE` ([#del-resource](#del-resource)); либо подписка на `BAG_UPDATE` — пересчёт раз на пакет после удалений (так делает `HomeScreenAssembly.onBagUpdate`).
- **Удержание на время анимации**: `holdResource(tag, id, count)` в обработчике ответа →
  `FlyIconsAnimation.play(..., onEnd)` → `releaseHold(tag)` в `onEnd`. Ограничения — [#tradeoffs](#tradeoffs).

<a id="class-list"></a>
## 4. Список классов

- `src/plain/user/UserBag.ts` — `class UserBag` (default export).
- `src/views/home_screen/popups/bag/bag.d.ts` — глобальные интерфейсы `ItemJSON`, `BagItemJSON`,
  `ResourceJSON`, `TankJSON`, `TankParamsJSON`, `AirplaneJSON`, `AirplaneParamsJSON`, `StarsJSON`, `MilitaryBaseBuildingJSON`, `MilitaryBaseAviationFactorySlotJSON`, `MilitaryBaseBoostJSON`.
- Вне области, только используются: `ItemType` (`RESOURCE = 0`, `TANK = 1`, `AIRPLANE = 2`,
  `MILITARY_BASE_BUILDING = 3`, `MILITARY_BASE_AVIATION_FACTORY_SLOT = 4`, `MILITARY_BASE_BOOST = 5`,
  `COLLECTION_ITEM = 6`) и `ItemId` (ресурсы `1..8`, плюс id зданий и бустов военной базы) из `src/plain/items/`; события в `GameEvents`;
  `Globals.bag`/`logout`; `InGameScene`.

<a id="anchors"></a>
## 5. Навигация (якоря)

[#del-resource](#del-resource), [#client-contract](#client-contract), [#consumers](#consumers),
[#gdd-mapping](#gdd-mapping), [#dup-can-afford](#dup-can-afford), проблемы удержания
([#userbag-hold-order](#userbag-hold-order), [#userbag-hold-leak](#userbag-hold-leak),
[#userbag-hold-shared-tag](#userbag-hold-shared-tag)), [#file-map](#file-map).

<a id="class-nav"></a>
## 6. Оглавление по классам

- [`UserBag`](#cls-userbag): [`requestData`/`initialize`/`isInitialized`](#m-init), [`bagUpdate`](#m-bagupdate),
  [`holdResource`/`releaseHold`](#m-hold), [чтение, `getItem` и type-guard'ы](#m-getters)
- [Типы `bag.d.ts`](#cls-bag-dts)
- [Контракт с сервером](#client-contract), [потребители](#consumers), [карта файлов](#file-map)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-userbag"></a>
### `UserBag`

Поля: `bag: BagItemJSON[]` (плоский список, поиск линейный по `uid`), `initialized`,
`holdResourceList: { tag, id, count, applied }[]`.

<a id="m-init"></a>
#### `requestData()` и `initialize(items)`

`requestData` шлёт `/ingame/bag/get` и передаёт `response.items` в `initialize`. `initialize`
срабатывает один раз на экземпляр: вешает три логирующих слушателя `ITEM_NEW`/`ITEM_UPDATE`/
`ITEM_DELETE` (лог только при `Globals.isDevTools()`), кладёт предметы в кэш с `ITEM_NEW` +
`ITEM_NEW_OR_UPDATE` на каждый и подписывается на `g/ws/events/bag/update`. Отписки нет
([#logout-leak](#logout-leak)). `isInitialized()` возвращает флаг `initialized`.

<a id="m-bagupdate"></a>
#### `private bagUpdate(data: { items, del })`

1. Для каждого пришедшего предмета запоминает настоящее значение в недекларированном поле
   `items[i]["count_"]`; для ресурса вычитает из `count` все записи `holdResourceList` с тем же `id`
   (независимо от тега) и ставит им `applied = true`.
2. Известный `uid` заменяет целиком (`ITEM_UPDATE` + `ITEM_NEW_OR_UPDATE`), неизвестный добавляет
   (`ITEM_NEW` + `ITEM_NEW_OR_UPDATE`). Объект из пакета хранится как есть, без копии.
3. Для каждого `uid` из `del`: если предмет есть — `count = 0` у объекта, `ITEM_DELETE` с этим
   объектом и удаление из кэша. `i--` после удаления повторяет проверку того же `uid` (ничего не находит, на результат не
   влияет).
4. В конце — `BAG_UPDATE` без данных.

Правила ГДД: [#gdd-gain-spend](game-design/bag-gdd.md#gdd-gain-spend) (доставка учёта на клиент),
[#gdd-vehicles](game-design/bag-gdd.md#gdd-vehicles) (удаление техники при замене приходит тем же `del`).

<a id="m-hold"></a>
#### `holdResource(tag, id, count)` и `releaseHold(tag)`

- `holdResource` только добавляет `{ tag, id, count, applied: false }`; значение в кэше не меняет,
  вычитание произойдёт в следующем `bagUpdate`.
- `releaseHold` проходит по записям с этим тегом. `applied === false` или ресурса нет в кэше —
  пропускает, запись остаётся. Иначе восстанавливает `count = count_`, удаляет запись и прогоняет
  ресурс через `bagUpdate` (остальные удержания по `id` применяются заново, подписчики получают
  `ITEM_UPDATE`).
- Порядок вызовов лежит на вызывающем: `holdResource` синхронно до push, `releaseHold` ровно один раз
  после. Это нарушает [`#no-implicit-order`](agent-system-workflow.md#no-implicit-order); последствия —
  [#tradeoffs](#tradeoffs). Правил ГДД не реализует.

<a id="m-getters"></a>
#### Чтение и type-guard'ы

Тривиальные: `static isResource`, `isResourceId(item, id)`, `isTank`, `isAirplane` (по `itemType` и
`id`); `getResources()`, `getTanks()`, `getAirplanes()` (фильтр кэша, каждый раз новый массив);
`getResource(id)`, `getTank(uid)`, `getAirplane(uid)` (запись или `null`); `private get(uid)`
(предмет любого типа с индексом).

`getItem<T>(itemType, id)` — первая запись с этим `itemType` и `id` или `null`; в сумке по одному
предмету на пару, поэтому это поиск здания, слота или буста военной базы (потребители — только
`military_base`). Для ресурсов есть `getResource(id)`, `getItem(ItemType.RESOURCE, id)` даёт то же.

`getResourceCount(id)` — количество ресурса, `0`, если записи нет. Единственная точка, где клиент
отвечает «сколько у игрока ресурса» ([#gdd-resources](game-design/bag-gdd.md#gdd-resources)); именно
она делает удаление в `del` неотличимым от нуля. Пока действует удержание, возвращает заниженное
значение ([#hold-reads](#hold-reads)).

<a id="cls-bag-dts"></a>
### Типы `bag.d.ts`

Глобальные интерфейсы без `export`.

- `ItemJSON { id, itemType, count }` — предмет без `uid` (награды в ответах сервера).
- `BagItemJSON extends ItemJSON { uid }`; `ResourceJSON` — пустое расширение.
- `TankJSON` — `name`, `type`, `country`, `rank`, `level?`, `stars?`, `params`, `power`, `titleType`.
- `AirplaneJSON` — то же без `level` и `titleType`, `stars` обязателен.
- `StarsJSON { rank, count }`.
- `MilitaryBaseBuildingJSON`, `MilitaryBaseAviationFactorySlotJSON`, `MilitaryBaseBoostJSON` — три
  расширения `BagItemJSON` для предметов военной базы (`ItemType` 3, 4, 5). Поля и правила — область
  «Военная база», в этом документе не описываются.

`power` клиент не считает, только показывает; мощность игрока — `Globals.account.power`, не из сумки
([#gdd-power](game-design/bag-gdd.md#gdd-power)).

<a id="client-contract"></a>
### Контракт с сервером

Полный контракт — серверный `bag-architecture.md#client-contract`. Что важно клиенту:

- `/ingame/bag/get` → `{ items: BagItemJSON[] }`; push `/events/bag/update` → `{ items, del: string[] }`.
  Клиент ждёт оба поля всегда, без проверки на `undefined`.
- Push приходит сразу после обработки запроса (`UserActor.onAfterMessageReceive` →
  `User.processDelayedExecution`), практически вместе с ответом.
- В `del` попадает удалённая техника и ресурс с `count = 0`, хотя на сервере запись ресурса остаётся
  ([#del-resource](#del-resource)). Следующее начисление приходит в `items`; `uid` может совпасть или
  нет (серверный `#tradeoffs` п.2: дубль записи), клиент обрабатывает оба случая как `ITEM_NEW`.
- Награды в ответах других роутов — `ItemJSON` с `uid` шаблона, не записи сумки; клиент берёт из них
  только `id`/`count` (`RewardUtils.getResource`).

<a id="consumers"></a>
### Потребители

Файлы и их роли — [#file-map](#file-map). Здесь только теги удержания (`holdResource`/`releaseHold`)
и места, где они общие:

- `GoldenCoinsOffer::RESOURCE_GOLDEN_COINS` — `GoldenCoinsOfferPopup`, `AirDrop`, `AchievementLine`,
  `CollectionAlbumCard`, `CollectionsUSSROperationsSection` (один тег на пять экранов).
- `TrainCollectionItemPopup::RESOURCE_SILVER_COINS` — `HomeScreen` (два места),
  `TrainCollectionItemPopup` (только release), `CollectionExperimentalTank`.
- `HomeScreen::campaignChapterComplete::RESOURCE_GOLDEN_COINS` — hold в `CampaignBattleGround`, release
  в `HomeScreen` (разные классы).
- `CampaignGround::onTankDestroyedEvent::*` + `uid` — `CampaignBattleGround`, тег уникален на танк.
- Остальные теги уникальны для экрана: `HomeScreen::BtnTrainAccept/BtnTrainRefuse`,
  `HomeScreenQuest::*`, `IdlePopup::*`, `TrainBuySchemesPopup::*`, `CollectionExperimentalTank::*`,
  `MilitaryBaseStoragePopup::BtnTakeProfit::RESOURCE_MILITARY_BASE_DOLLARS` (новый потребитель, только
  упоминание). Аэродромные теги (`RadioTowerFrame::*`, `AerodromeBuySchemesPopup::*`) исчезли вместе с
  удалёнными классами.
- `CollectionExperimentalTank` единственный оборачивает вызовы в свои методы с набором
  `activeHoldTags` и снимает всё в `onDestroy` (`collections-architecture.md#s8` п.12).

<a id="gdd-mapping"></a>
### Сопоставление функций с ГДД ([`#gdd-function-mapping`](agent-system-workflow.md#gdd-function-mapping))

| Функция | Правило ГДД |
|---|---|
| `getResourceCount` | [#gdd-resources](game-design/bag-gdd.md#gdd-resources), граница — [#gdd-open](game-design/bag-gdd.md#gdd-open) (ноль/удаление) |
| `bagUpdate` | [#gdd-gain-spend](game-design/bag-gdd.md#gdd-gain-spend), [#gdd-vehicles](game-design/bag-gdd.md#gdd-vehicles) |
| `getTanks`/`getAirplanes`/`getTank`/`getAirplane` | [#gdd-vehicles](game-design/bag-gdd.md#gdd-vehicles) |
| `holdResource`/`releaseHold`, type-guard'ы | бизнес-правила нет |

<a id="dup-can-afford"></a>
Дубль по смыслу: условие «трата возможна только при достаточном количестве»
([#gdd-gain-spend](game-design/bag-gdd.md#gdd-gain-spend)) выражено не функцией, а одинаковым
выражением `Globals.bag.getResourceCount(id) >= price` в `TrainBuySchemesPopup`,
`ChangeNamePopup`, `ClanInfoPopup`, `ClanPopup` (цена 1000 зашита в код), `HomeScreenAssembly.checkNotification`
и в `military_base` (`MilitaryBaseMissingDollarsPopup`, `MilitaryBaseSelectableResource`,
`MilitaryBaseResource` — доллары базы, золото; только упоминание).
Возможное сведение — одна функция у `UserBag` (в вопросах, не решено).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

<a id="userbag-hold-order"></a>
### 1. Hold работает, только если поставлен до прихода push

`bagUpdate` вычитает удержание только из записей, уже лежащих в `holdResourceList`. Push приходит
практически вместе с ответом, поэтому `holdResource` вызывают синхронно в обработчике ответа, до любой
асинхронной паузы (загрузка ассетов, твины, задержки). Иначе push уже применён и удерживать нечего.
Исправлено в `TrainCollectionItemPopup`/`HomeScreen` (sellReward), `collections-architecture.md#s3`.

<a id="userbag-hold-leak"></a>
### 2. `releaseHold` не удаляет неприменённые записи — hold висит навсегда

Записи с `applied === false` и записи, ресурса которых нет в кэше, остаются в списке и вычитают свой
`count` из каждого следующего апдейта ресурса; баланс в шапке занижен до перезагрузки клиента. Пути:
- hold поставлен после push (п.1) или push по ресурсу не пришёл;
- экран уничтожен до `releaseHold` (остаточный риск: `HomeScreen` уничтожен во время
  `animationTrainCart` — hold sellReward повиснет);
- ресурс за время анимации ушёл в `del` (потрачен до нуля, [#del-resource](#del-resource)).

Решение пользователя 2026-09-30: `UserBag` не менять, закрывать на стороне экранов. Вариант на
будущее: в `releaseHold` удалять и записи с `applied=false` или без ресурса в кэше, без пересчёта.

<a id="userbag-hold-shared-tag"></a>
### 3. Тег hold общий для всех экземпляров одного экрана

`releaseHold(tag)` снимает все записи с тегом. Два одновременных попапа с одним тегом: первый release
снимет оба hold, шапка обновится раньше второго полёта иконок. Итоговый баланс верный, страдает только
визуальная синхронность. Реально общие теги — [#consumers](#consumers): пять экранов у золота
оффера, три класса у серебра поезда. Принято как есть (2026-09-30).

<a id="hold-reads"></a>
### 4. Во время удержания чтение возвращает заниженное значение

Удержание хранится прямо в кэше (`count` уменьшен), поэтому `getResourceCount` и все `ITEM_*` отдают
значение без удержанной награды. Проверки «хватает ли» (`canBuy` в `TrainBuySchemesPopup`,
`ChangeNamePopup`, `HomeScreenAssembly`) во время анимации видят меньше, чем на
сервере. Если удержание больше пришедшего значения, `count` уходит в минус: `HomeScreen`,
`HomeScreenAerodrome` защищаются `Math.max(count, 0)`, шапки (`HeaderGoldenCoinsBar`,
`HeaderSilverCoinsBar`) — нет. Решения нет.

<a id="logout-leak"></a>
### 5. Старый экземпляр после `logout` остаётся подписан

`Globals.logout()` (из `ExitPopup` без перезагрузки страницы и из `SceneImpl` при ошибке авторизации)
создаёт новый `UserBag`, но старый не отписан от `g/ws/events/bag/update` и логирующих `ITEM_*`. Push
обрабатывают оба экземпляра: старый со своим устаревшим кэшем тоже шлёт `ITEM_*`, подписчики получают
события дважды; оба мутируют один объект пакета (`count_`, вычитание hold). Найдено чтением кода,
запуском не проверялось; решения нет.

<a id="gdd-link"></a>
## 9. Связь с ГДД

| Раздел ГДД | Где на клиенте | Расхождение |
|---|---|---|
| [#gdd-purpose](game-design/bag-gdd.md#gdd-purpose) | [`UserBag`](#cls-userbag) | нет |
| [#gdd-resources](game-design/bag-gdd.md#gdd-resources) | [`getResourceCount`](#m-getters), `ItemId` (8 ресурсов: к шести добавлены доллары и жетоны военной базы) | нет: шесть базовых видов плюс ресурсы военной базы |
| [#gdd-purpose](game-design/bag-gdd.md#gdd-purpose) (состав сумки) | `ItemType` 3–5, `getItem`, типы `MilitaryBase*JSON` | ГДД знает только ресурсы и технику |
| [#gdd-vehicles](game-design/bag-gdd.md#gdd-vehicles) | [`bagUpdate`](#m-bagupdate) — удаление через `del` | нет |
| [#gdd-gain-spend](game-design/bag-gdd.md#gdd-gain-spend) | [`bagUpdate`](#m-bagupdate), [#dup-can-afford](#dup-can-afford) | удержание временно занижает значение, возможен минус ([#hold-reads](#hold-reads)) |
| [#gdd-starter](game-design/bag-gdd.md#gdd-starter) | на клиенте нет, стартовый набор серверный | нет |
| [#gdd-power](game-design/bag-gdd.md#gdd-power) | `power` только отображается; мощность игрока — `Globals.account.power` | нет |
| [#gdd-open](game-design/bag-gdd.md#gdd-open) | [#del-resource](#del-resource) | клиент считает ресурс в `del` удалённым и показывает 0; теперь `count = 0` пишется в объект до `ITEM_DELETE` |

<a id="file-map"></a>
## 10. Карта файлов компонента

Критерий полноты: `grep` по `UserBag`, `Globals.bag`, `BAG_UPDATE`, `ITEM_*`, `holdResource`,
`releaseHold`, `ItemJSON`, `BagItemJSON`, `ResourceJSON`, `TankJSON`, `AirplaneJSON`, `StarsJSON`,
`ItemType`, `ItemId` по `src`; каждый файл с вхождением стоит ниже. Сверено 2026-10-19.

### Файлы прямого влияния

- `src/plain/user/UserBag.ts` — кэш инвентаря, `bagUpdate`, удержание, геттеры.
- `src/views/home_screen/popups/bag/bag.d.ts` — типы `ItemJSON`, `BagItemJSON`, `ResourceJSON`, `TankJSON`, `AirplaneJSON`, `StarsJSON`.

### Файлы косвенного влияния

Зависимости, создание, события, сброс:
- `src/plain/items/ItemType.ts` — зависимость: тип предмета (0–6).
- `src/plain/items/ItemId.ts` — зависимость: ресурсы `1..8`, id зданий и бустов военной базы (значения пересекаются).
- `src/plain/Globals.ts` — поле `bag`, сброс в `logout()`.
- `src/plain/GameEvents.ts` — события `BAG_UPDATE`, `ITEM_*`.
- `src/scenes/InGameScene.ts` — первичная загрузка (`requestData`), проверка `isInitialized()`.

Подписчики, читатели ресурсов, удержание (`Globals.bag`, события, hold; теги — [#consumers](#consumers)):
- `src/shared/header/presets/HeaderGoldenCoinsBar.ts` — счётчик золота.
- `src/shared/header/presets/HeaderSilverCoinsBar.ts` — счётчик серебра.
- `src/views/home_screen/HomeScreen.ts` — схемы танков, ангар, hold.
- `src/views/home_screen/HomeScreenAerodrome.ts` — самолёты и ресурсы аэродрома.
- `src/views/home_screen/HomeScreenAssembly.ts` — ресурсы сборки, доступ по числу танков.
- `src/views/home_screen/HomeScreenQuest.ts` — hold награды квеста.
- `src/views/home_screen/campaign/AirDrop.ts` — hold золота ящика.
- `src/views/home_screen/campaign/CampaignBattleGround.ts` — hold наград кампании и танков.
- `src/views/home_screen/popups/battlefield/BattlefieldPopup.ts` — чтение техники.
- `src/views/home_screen/popups/idle/IdlePopup.ts` — hold награды.
- `src/views/home_screen/popups/profile/achievements/AchievementLine.ts` — hold золота награды.
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsUSSROperationsSection.ts` — hold золота.
- `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbumCard.ts` — hold золота.
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts` — hold с `activeHoldTags`.
- `src/views/home_screen/popups/settings/ChangeNamePopup.ts` — проверка цены смены имени.
- `src/views/home_screen/popups/clan/ClanInfoPopup.ts`, `src/views/home_screen/popups/clan/ClanPopup.ts` — проверка цены (кланы, новая область, только упоминание).
- `src/shared/header/presets/HeaderDollarsBar.ts`, `src/shared/header/presets/HeaderTokensBar.ts` — счётчики долларов и жетонов военной базы (подписка на `ITEM_*`).
- `src/views/home_screen/popups/shop/offers/GoldenCoinsOfferPopup.ts` — hold золота оффера.
- `src/views/home_screen/popups/train/TrainBuySchemesPopup.ts` — покупка схем, hold.
- `src/views/home_screen/popups/train/TrainCollectionItemPopup.ts` — release серебра.

Военная база (новая область, не документируется здесь; потребители `getItem`, `ITEM_*`, hold долларов):
- `src/plain/military_base/MilitaryBaseBoostRouter.ts`.
- `src/views/home_screen/popups/military_base/**` — окна и плашки базы (`MilitaryBasePopup`, `MilitaryBaseResourcesPopup`,
  `MilitaryBaseStoragePopup`, `MilitaryBaseStorageResource`, `MilitaryBaseAviationFactoryPopup`, `MilitaryBaseAviationFactorySlot`,
  `MilitaryBaseHeadquartersPopup`, `MilitaryBaseBoost*`, `MilitaryBaseBuyBuildingPopup`, `MilitaryBaseMissingDollarsPopup`,
  `MilitaryBaseSelectableResource`, `MilitaryBaseResource`, `MilitaryBaseSell*`/`MilitaryBaseSkip*`/`MilitaryBaseState`,
  `MilitaryBaseAerodromePopup`, `MilitaryBaseStoragePopup`, `base/MilitaryBaseAerodrome`, `base/MilitaryBaseAviationFactory`,
  `base/MilitaryBaseStorage`).

Типы и `ItemType`/`ItemId` без доступа к `Globals.bag`:
- `src/plain/RewardUtils.ts` — `getResource` из наград (`ItemJSON`).
- `src/plain/TutorialUtils.ts` — `TankJSON` в туториале.
- `src/presets/ItemsPresets.ts` — стандартная отрисовка предметов.
- `src/presets/TankPresets.ts` — отрисовка танка.
- `src/presets/AirplanePresets.ts` — отрисовка самолёта.
- `src/utils/CollectionUtils.ts` — предметы коллекций, награды.
- `src/battle/Battle.ts`, `src/battle/units/UnitTank.ts`, `src/battle/units/UnitAirplane.ts` — `TankJSON`/`AirplaneJSON` в данных боя и юнитах.
- `src/types/battle.d.ts` — типы данных боя на основе `TankJSON`/`AirplaneJSON`.
- `src/types/interfaces.d.ts` — общие интерфейсы с типами сумки.
- `src/views/home_screen/home.d.ts` — типы главного экрана.
- `src/views/home_screen/popups/airplane/AirplaneGetPopup.ts` — получение самолёта.
- `src/views/home_screen/popups/tank/TankGetPopup.ts` — получение танка.
- `src/views/home_screen/popups/assembly/AssemblyPopup.ts` — окно сборки.
- `src/views/home_screen/popups/assembly/assembly.d.ts` — типы сборки.
- `src/views/home_screen/popups/campaign/CampaignPopup.ts` — награды кампании.
- `src/views/home_screen/popups/idle/idle.d.ts` — типы наград idle.
- `src/views/home_screen/popups/shop/shop.d.ts` — типы магазина.
- `src/views/home_screen/popups/profile/profile.d.ts` — типы профиля.
- `src/views/home_screen/popups/profile/achievements/achievement.d.ts` — типы достижений.
- `src/views/home_screen/popups/profile/codex/CodexAirplanesSection.ts` — кодекс самолётов.
- `src/views/home_screen/popups/profile/codex/CodexTanksSection.ts` — кодекс танков.
- `src/views/home_screen/popups/profile/collections/collection.d.ts` — типы коллекций.
- `src/views/home_screen/popups/profile/collections/CollectionsListSection.ts`, `collection_type/CollectionAlbum.ts`, `collection_type/collection_album.d.ts` — предметы коллекций (`ItemJSON`/`ItemType`).
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsExperimentalTanksSection.ts` — секция экспериментальных танков.
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/collection_experimental_tank.d.ts` — типы экспериментального танка.
- `src/views/popups/AirplaneInfoPopup.ts` — информация о самолёте.
- `src/views/popups/TankInfoPopup.ts` — информация о танке.
