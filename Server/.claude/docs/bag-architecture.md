# Сумка — `BagUserComponent` (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-10-13, ветка
> `koba/collection`; сверен с кодом повторно 2026-10-14; актуализирован после merge `amnesia/fix` 2026-10-19 (не закоммичен). Запуском не проверялось. Клиентская сторона
> описана в `/workspace/client/.claude/docs/bag-architecture.md`.

ГДД: `/workspace/client/.claude/docs/game-design/bag-gdd.md` (черновик по описанию пользователя,
2026-10-13). Соответствие правил коду — [п.9](#gdd-link).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns) ([идемпотентная выдача награды](#p-idempotent-reward))
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`BagUserComponent`](#cls-bagusercomponent)
   - [`BagItem`](#cls-bagitem)
   - [`Resource` и `ItemId`](#cls-resource)
   - [`Tank`, `Airplane` и их утилиты](#cls-tank-airplane)
   - [`ItemAddInfo`, `ItemEmitInfo`](#cls-infos)
   - [`Item`, `ItemType`, `ItemFactory`](#cls-item)
   - [`BagDao` и миграция индекса](#cls-bagdao)
   - [`BagPage`](#cls-bagpage)
   - [Внешние точки: кто кладёт и списывает](#consumers)
   - [Персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Сумка — инвентарь игрока: ресурсы (`RESOURCE`), танки (`TANK`), самолёты (`AIRPLANE`) и предметы военной
базы (`MILITARY_BASE_BUILDING`, `MILITARY_BASE_AVIATION_FACTORY_SLOT`, `MILITARY_BASE_BOOST`, классы в
`model/bag/military_base/`, область военной базы здесь не описывается)
([gdd-purpose](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-purpose)). Каждый предмет —
отдельный документ коллекции `bag` с `ownerId`. Сумка держит предметы в памяти, отвечает другим
компонентам («сколько серебра», «танк по uid»), пушит клиенту изменения и раз в тик актора отдаёт
батч на запись в БД. Что считается правилом, смотри в ГДД; ниже — как это устроено в коде.

- **Ресурсы** ([gdd-resources](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-resources)).
  Восемь видов в `ItemId` (добавлены доллары и жетоны военной базы). Один `id` — один стек: поступление увеличивает `count` записи. Ресурс не
  удаляется при нуле (`canBeDeleted() == false`): запись с `count = 0` остаётся в сумке и в БД, но
  недоступна (`isAvailable() == false`). Последствия — [п.2](#tradeoffs).
- **Танки и самолёты** ([gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles)).
  Не стакаются: запись на экземпляр со своим `uid`, у танка `level`, у обоих `stars`. Параметры и
  мощность пересчитываются из баланса (`TankData`/`AirplaneData`) и в БД не хранятся. Экземпляр с
  `count <= 0` получает `DELETED` и удаляется из БД при ближайшем сохранении.
- **Шаблоны.** Предмет с `uid = EMPTY_UID` — глобальный шаблон (награды в статических полях, офферы).
  `add` кладёт в сумку личную копию, шаблон не меняется.
- **Списание.** Метода «потратить» нет: вызывающий проверяет `getResourceCount(id) >= цена`, затем
  `addResource(id, -цена)` ([gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend),
  [п.5–6](#tradeoffs)).
- **Мощность игрока** ([gdd-power](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-power)).
  `User.getPower()` = `TankUtils.getUserPower` + `AirplaneUtils.getUserPower` — сумма `power` доступных
  танков и самолётов сумки. `power` экземпляра хранится в поле и пересчитывается в
  `recalculateParams()` ([формулы](#cls-tank-airplane)). Клиент берёт `Globals.account.power` из поля
  `power` объекта `user` в `User.apiResponse` (параметр `FULL`, он же по умолчанию в `apiResponse()`).
  Отдельного push мощности нет, `/events/bag/update` несёт только `power` самих экземпляров. Те же
  суммы идут в рейтинги (`RatingPowerService`, `RatingTanksService`, `RatingAirplanesService`:
  `getPower`/`getTanksPower`/`getAirplanesPower`) и в `profileOverview` (`tanksPower`, `airplanesPower`).
- **Стартовый набор** ([gdd-starter](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-starter)).
  `BagUserComponent.initStarter()` пуст. Если при загрузке нет ни одного документа `bag`,
  `ActorInitializationTask` вызывает `TrainUserComponent.initStarter()`: `addResource` 50 схем танка;
  схем самолёта нет. Затем `MilitaryBaseUserComponent.initStarter()` (1000 долларов военной базы).

<a id="references"></a>
## 2. Референсы

- **`CodexUserComponent`, `AchievementUserComponent`, `CollectionUserComponent`** повторяют схему
  сумки: флаги `NEW`/`DELETED`, кэш `dbUpdateDocuments`, пара `dbFetchChanged`/`commitDbUpdates`,
  `dbMappingChildBuild`, `ownerId` + индекс миграцией. Баг дублей кодекса
  (`codex-architecture.md#bug-duplicates`) даёт тот же приём `map.remove(key)` в `onClean`
  ([п.4](#tradeoffs)).
- **`TankData`/`AirplaneData`** — балансовые справочники для `Tank`/`Airplane`:
  `tank-airplane-data-architecture.md`.

<a id="patterns"></a>
## 3. Паттерны

- **Битовые флаги** `BagItem`: `NEW` (не записан в БД), `DELETED` (удалить при сохранении), `IN_BAG`
  (уже в сумке, повторный `add` запрещён).
- **Запись батчем.** `FieldsChangerObserver` (`f()`) копит изменённые поля; раз в тик `dbFetchChanged`
  строит `WriteModel` (`$set` / upsert для новых / `DeleteOneModel`), `BagDao.bulkUpdate` пишет один
  `bulkWrite` ([детали](#m-dbfetchchanged)).
- **Индексы** поверх `items`: `resourceMap` (по `id`), `tanksList` + `tanksMap`, `airplanesList` +
  `airplanesMap` (по `uid`).
- **Дебаунс push** через `User.addDelayedExecution`: изменения за одно сообщение актора уходят одним
  пакетом ([`sendChangesToClient`](#m-sendchanges)).
- **Шаблон** (`EMPTY_UID` + `copy()`) — [п.1](#purpose). **Фабрика без рефлексии** — `ItemFactory`
  (`ImmutableMap<ItemType, Supplier<Item>>`). **Общие объекты-результаты** `ItemAddInfo`/`ItemEmitInfo`
  — [п.8](#tradeoffs).
- **Идемпотентная выдача награды** — как сейчас защищена выдача и чего в коде нет:
  [`#p-idempotent-reward`](#p-idempotent-reward).

<a id="p-idempotent-reward"></a>
### Идемпотентная выдача награды

Сокращённый формат, по коду на 2026-10-27 (**auto-create**, ветка `koba/lootbox`). Ключа
идемпотентности для выдачи в сумку в коде нет: повторный запрос защищён только состоянием
вызывающего компонента.

1. **Порядок запросов одного игрока.** Один `UserActor` на игрока (Akka `AbstractActor`), страницы
   доходят до него сообщением `PageProcessor` (`receivePageProcessor`) и обрабатываются по одному.
   Двойной клик, две вкладки и повтор после обрыва сети приходят в тот же почтовый ящик, поэтому
   синхронный обработчик не пересекается сам с собой: второй запрос видит состояние после первого.
   Это защищает, только если первый запрос изменил состояние, по которому второй отсекается
   (счётчик, флаг, очередь). Идентификатора запроса в игровом коде нет, одинаковый запрос второй раз
   не отличить от нового. Закрытое окно и обрыв сети не отменяют уже принятый запрос.
2. **Где живёт изменение.** Начисление меняет объекты в памяти актора. В БД оно уходит раз в
   `getTickInterval()` (10 минут, `UserActorPolicy`) и при остановке актора: `ActorUpdateTask` запускает
   `userToDb` и `bagToDb` (а также `codexToDb`, `achievementsToDb`) параллельно, затем `actionWait`.
   Это независимые записи (`UserDao.update` и `BagDao.bulkUpdate`), общей транзакции и порядка между
   ними нет. Отметка «выдано» в компоненте пользователя и предметы в `bag` могут сохраниться
   порознь: при сбое одной из записей или падении процесса между ними бывает отметка без предметов
   или предметы без отметки. Повтор записи есть только у сумки: `dbFetchChanged` держит
   `dbUpdateDocuments` до успешного `commitDbUpdates` (см. [п.12](#tradeoffs)). У документа
   пользователя такого кэша в коде проекта нет, `FieldsChangerObserver` читается с
   `CHANGED_WITH_FLUSH`; поведение при отказе записи в библиотеке не проверялось. Падение процесса до
   тика теряет обе стороны вместе, это согласованно.
3. **Защита в [`add`](#m-add).** Отказ даёт только флаг `IN_BAG`/`DELETED` на **том же объекте**:
   повторный `add` уже лежащей записи вернёт `success = false`. Проверки «такой `uid` уже есть»
   нет: если `uid` совпал с лежащим (`uniqueId`), `add0` не отказывает, а выпускает новый `uid`
   (`regenerateUid`) и добавляет запись. Объект с пустым `uid` копируется, и каждая копия получает
   новый `ObjectId` при первом `getUid`, поэтому вторая выдача того же шаблона не распознаётся как
   повтор. `Resource` стакуется с доступной записью по `id`, дельта прибавляется без учёта, была ли
   она выдана раньше; `addResource` вообще не смотрит на `uid`. Итого `add` защищает от повторной
   вставки одного и того же объекта (флаг `IN_BAG`), а не от повторной выдачи той же награды.
4. **Единственный ключ идемпотентности** в проекте: пара `provider + orderId` с уникальным индексом
   `payment_requests` для платежей. Описание и ограничения (проверка до начисления, запись после, ошибка
   индекса только в лог, начисление в памяти до сохранения профиля) —
   `offers-architecture.md#patterns`, `offers-architecture.md#tradeoffs` п.1–2; здесь не повторяются.
5. **Внешний API.** `OvermobileService` (YooKassa) шлёт `Idempotence-Key: UUID.randomUUID()` в запросе
   создания платежа. Это ключ для стороны ЮKassa, он новый на каждый вызов и состояния выдачи в игре не
   касается.
6. **Антипримеры (отложены, не пересказываются).** Квесты, повторная выдача награды без обнуления
   `reward`: `quests-architecture.md#tradeoffs` п.1, память `server_quests_deferred_fixes`. Сборка,
   повторная выдача танка при пустом списке кандидатов: `assembly-architecture.md#tradeoffs` п.2, память
   `server_assembly_deferred_fixes`. Магазин, двойное начисление набора и оплата без набора:
   `offers-architecture.md#tradeoffs` п.1–2, память `shop_deferred_fixes`.

<a id="class-list"></a>
## 4. Список классов

Корень путей — `game/src/main/java/com/linkedgames/game/`.

| Класс | Файл |
|---|---|
| `BagUserComponent`, `BagItem` | `model/bag/` |
| `Resource` | `model/bag/resource/Resource.java` |
| `Tank`, `TankParams`, `TankUtils` | `model/bag/tank/` |
| `Airplane`, `AirplaneParams`, `AirplaneUtils` | `model/bag/airplane/` |
| `ItemAddInfo`, `ItemEmitInfo` | `model/bag/utils/` |
| `Item`, `ItemType`, `ItemFactory`, `ItemId` | `model/item/` |
| `BagDao` | `dao/BagDao.java` |
| `BagPage` | `pages/ws/ingame/BagPage.java` (роут `/ingame/bag`) |
| Миграция индекса | `game/src/main/resources/migrations/1755491789292_bag.json` |
| Предметы военной базы (ссылкой) | `model/bag/military_base/` (`MilitaryBaseBuilding`, `MilitaryBaseAviationFactorySlot`, `MilitaryBaseBoost`) |
| Связанные (не часть сумки) | `User` (`getBagComponent`, `addItem`, `getPower`, `createTeam`), `UserEmitterId` (`BAG_ITEM_*`), `ActorInitializationTask`, `ActorUpdateTask` |

Enum-ы техники и `TankData`/`AirplaneData` лежат в пакете сумки, описаны в
`tank-airplane-data-architecture.md`.

<a id="anchors"></a>
## 5. Навигация (якоря)

Якоря разделов — в [оглавлении](#toc) и [таблице классов](#class-nav). Якоря методов: `#m-add`,
`#m-addresource`, `#p-idempotent-reward`, `#m-sendchanges`, `#m-dbfetchchanged`, `#m-dbmappingchildbuild`, `#m-setcount`.

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `BagUserComponent` | [#cls-bagusercomponent](#cls-bagusercomponent) |
| `BagItem` | [#cls-bagitem](#cls-bagitem) |
| `Resource`, `ItemId` | [#cls-resource](#cls-resource) |
| `Tank`, `Airplane`, `TankParams`, `AirplaneParams`, `TankUtils`, `AirplaneUtils` | [#cls-tank-airplane](#cls-tank-airplane) |
| `ItemAddInfo`, `ItemEmitInfo` | [#cls-infos](#cls-infos) |
| `Item`, `ItemType`, `ItemFactory` | [#cls-item](#cls-item) |
| `BagDao`, миграция | [#cls-bagdao](#cls-bagdao) |
| `BagPage` | [#cls-bagpage](#cls-bagpage) |

<a id="cls-bagusercomponent"></a>
## 7. Классы и методы

### `BagUserComponent extends UserChildComponent`

Создаётся лениво в `User.getBagComponent()` (имя `"Bag"`). В конструкторе подписывается на
`BAG_ITEM_NEW_ID`, `BAG_ITEM_CHANGE_ID`, `BAG_ITEM_DELETE_ID` — все три ведут в `onItemChanged(uid)`.
Поля: `items` (все предметы, включая недоступные и ждущие удаления), `uniqueId`, индексы
[паттернов](#patterns), `changedItems` (uid для push), `dbUpdateDocuments` (кэш батча).

<a id="m-add"></a>
#### `ItemAddInfo add(BagItem item)`

Положить предмет в сумку (правило: [gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend)).

1. `uid == EMPTY_UID` → работать с `item.copy()`.
2. Отказ (`success = false`): есть `IN_BAG` или `DELETED`, предмет недоступен, `count <= 0`.
3. Стакающийся (`Resource`): `getStackedItem` ищет **доступный** предмет того же типа и `id` с другим
   `uid` и `isStackableVariant`. Нашёлся — `addCount`, результат `update(true, countBefore, stackedItem)`,
   переданный объект в сумку не попадает.
4. Иначе `addNew`: `NEW` → `add0` → `onBagNew()` (`BAG_ITEM_NEW_ID`), результат `update(true, 0, item)`.

Возвращает общий `ItemAddInfo` — читать до следующего `add`. `add0` регистрирует без логики стека:
при коллизии `uid` (награды из почты с одинаковым `uid`) генерирует новый, ставит `IN_BAG`,
`onBagInsert(user)` (привязка к игроку, у техники пересчёт параметров), добавляет в `items`, `uniqueId`
и индекс типа. Его же использует загрузка.

<a id="m-addresource"></a>
#### `void addResource(Integer resourceId, long delta)`

Начислить или списать ресурс по `id` через `resourceMap`, минуя `add` (правило то же,
[п.3](#tradeoffs)). Записи нет — `Resource.createNew(id)` (`count = 1`), `add`, затем
`addCount(delta - 1)`. Видит и запись с `count = 0`: она получает `addCount` с тем же `uid`, а не
новую запись. Отрицательный итог не проверяется ([п.5](#tradeoffs)).

#### Прочие методы

- `getResourceCount(id)` (`long`, 0 если нет), `setResource(id, count)` (вызовов нет, [п.11](#tradeoffs)).
- `getItem(type, castTo)` (список доступных предметов типа) и `getItem(type, id, castTo)` (первый доступный
  по типу и `id` или `null`) — для предметов военной базы; `onItemChanged(uid)` стал `public`.
- `getItems()`, `getResources()`/`getResources(predicate)` — доступные предметы.
- `getTank(uid)`/`getAirplane(uid)` — `null`, если нет или недоступен; `getTanks()`/`getTanks(predicate)`/
  `forEachTanks`, то же для самолётов — по спискам, только доступные.
- `getItemEmitInfo()`, `getItemAddInfo()` — ленивые общие объекты.
- `initStarter()` — пуст ([п.10](#tradeoffs)).
- `onClean(item)` — снять с индексов и `uniqueId`; вызывается только из `dbFetchChanged`.
- `onItemChanged(uid)` — добавить `uid` в `changedItems`, один раз за сообщение актора поставить
  `sendChangesToClient` в отложенное выполнение.

<a id="m-sendchanges"></a>
#### `void sendChangesToClient()`

Изменённые доступные предметы уходят в `items` (полный `apiResponse()`), остальные `uid` из
`changedItems` (удалённые или с `count = 0`) — в `del`. Пакет `/events/bag/update` `{ items, del }`,
затем `changedItems.clear()`. `del` — ссылка на живое множество; безопасно, потому что
`SessionBox.sendEvent` сериализует синхронно до `clear()`.

<a id="m-dbfetchchanged"></a>
#### `List<WriteModel<Document>> dbFetchChanged()` и `boolean commitDbUpdates()`

`dbFetchChanged`: кэш `dbUpdateDocuments` не пуст — вернуть его (повтор после сбоя записи). Иначе по
`items`:

- `NEW` + `DELETED` — убрать из `items` и индексов, в БД ничего;
- `DELETED` — `DeleteOneModel` по `_id`, убрать из `items` и индексов;
- `NEW` — снять флаг, записать документ целиком (`dbToData()` + `ownerId`), `UpdateOneModel` с `upsert`;
- иначе — `$set` изменённых полей из `f().fetchChangedWithFlush()`.

Непустой результат кэшируется, пустой — `null`. `commitDbUpdates` (после успешной записи всех
компонентов) сбрасывает кэш, собирает изменения заново, `true` — новых нет.

<a id="m-dbmappingchildbuild"></a>
#### `void dbMappingChildBuild(List<Document> documents)`

Для каждого документа `ItemFactory.newFromDocument` (тип по `t`, по умолчанию `0`); `null` (неизвестный
ordinal) — документ пропускается; иначе `dbMappingBuild` → `add0((BagItem) item)`. `NEW` не ставится, событий нет (`user` ещё не привязан).
Приведение к `BagItem` без проверки — [п.1](#tradeoffs).

<a id="cls-bagitem"></a>
### `abstract BagItem extends Item`

База предмета: `uid` (`_id` в БД, `UID_FIELD`; `OWNER_ID_FIELD = "ownerId"`), флаги, привязанный
`User`, `FieldsChangerObserver` (создаётся в `assignUser`; до попадания в сумку изменения не
отслеживаются).

<a id="m-setcount"></a>
- `setCount(long count)` — при реальном изменении: `BAG_ITEM_CHANGE_COUNT_ID`, отметка поля `c` с
  `BAG_ITEM_CHANGE_ID`; при `count <= 0` и `canBeDeleted()` — `DELETED` и `BAG_ITEM_DELETE_ID`.
  `addCount(long delta)` — обёртка.
- `isAvailable()` — нет `DELETED` и `count > 0`.
- `getUid()` — ленивая генерация; `setUid` — только если ещё не задан; `regenerateUid()`.
- Переопределяемые: `isStackable()` (abstract), `isStackableVariant(src)` (`true`), `canBeDeleted()`
  (`true`), `onBagInsert`, `onBagNew`, `onDelete`, `copy()` (abstract), `copyFromInternal` (`id`,
  `count`).
- `apiResponse()` — поля `Item` + `uid`; `dbToData()` — поля `Item` + `_id`.
- `equals`/`hashCode` по `uid`; шаблон равен только себе (`!= EMPTY_UID` сравнивается по ссылке).

<a id="cls-resource"></a>
### `Resource extends BagItem` и `ItemId`

Один класс на все ресурсы, вид — `id` из `ItemId`: серебро 1, золото 2, схема танка 3, схема самолёта
4, части схемы танка 5, части схемы самолёта 6 (состав видов — открытый вопрос ГДД,
[gdd-open](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-open)). `createNew(id, isTemplate)`:
`count = 1`, шаблон получает `EMPTY_UID`. `isStackable() = true`, `canBeDeleted() = false`.

<a id="cls-tank-airplane"></a>
### `Tank`, `Airplane` (extends `BagItem`) и утилиты

- `Tank`: `level` (по умолчанию 1), `stars` (`Stars`: ранг + количество), вычисляемые `params`
  (`TankParams`) и `power`. `createNew(data|id, isTemplate)` — `count = 1`. `recalculateParams()` —
  `TankParams.recalculate` (база из `TankData`, +1 % hp и урона за уровень сверх первого, затем
  множитель звёзд из баланса) и `TankUtils.calculatePower` (`60000 / recharge * damage + hp`).
  Автоматически вызывается в `onBagInsert`, `dbMappingBuild`, `copy`, `createCodexEntry`; после
  `setLevel`/`setStars` вызывающие вызывают его сами (`TrainUserComponent`, `AssemblyUserComponent`,
  `BattleDataFactory`, `ExperimentalTanksSectionType`, `CodexPage`). В БД — `level`, `stars`.
- `Airplane`: то же без уровня; мощность `AirplaneUtils.calculatePower` (пушка + бомбы + hp, пополам).
  Звёзды пишутся под `Tank.DBFields.STARS_FIELD` (то же значение `"stars"`).
- `apiResponse` техники добавляет данные баланса (`name`, `type`, `country`, `rank`, `titleType`),
  `level`, `stars`, `params`, `power`. `createCodexEntry()` — снимок для кодекса
  (`codex-architecture.md`).
- `TankUtils.getUserPower(user)` / `AirplaneUtils.getUserPower(user)` — сумма `power` доступной техники
  ([gdd-power](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-power)).

<a id="cls-infos"></a>
### `ItemAddInfo`, `ItemEmitInfo`

Изменяемые контейнеры результата. `ItemAddInfo` — `success`, `countBefore` (`long`), `item` (итоговый предмет:
стек или новый). `ItemEmitInfo` — `item`; `BagItem` заполняет его перед `emit` и очищает сразу после,
слушатель читает `item` синхронно.

<a id="cls-item"></a>
### `Item`, `ItemType`, `ItemFactory`

- `Item` — `id`, `count` (`long`, по умолчанию 1); `apiResponse` `{id, itemType, count}`; БД: `id`, `t`
  (ordinal типа), `c` (только если `count != 1`). Чтение `c` принимает и старый `int`, и новый `long`
  (`Number.longValue()`); при отсутствии поля остаётся 1.
- `ItemType` (ordinal = `t`): `RESOURCE` 0, `TANK` 1, `AIRPLANE` 2, `MILITARY_BASE_BUILDING` 3,
  `MILITARY_BASE_AVIATION_FACTORY_SLOT` 4, `MILITARY_BASE_BOOST` 5, `COLLECTION_ITEM` 6. Типы 3–5 — `BagItem`
  из `model/bag/military_base/` (ссылкой). `COLLECTION_ITEM` — `CollectionItem extends Item`, не `BagItem`;
  в сумку не кладётся (`User.addItem` для него — пустая ветка).
- `ItemId`: ресурсы 1–8 (7 — доллары, 8 — жетоны военной базы); далее id зданий (1–10) и бустов (1–50)
  военной базы в тех же константах.
- `ItemFactory.newFromDocument(doc)` — экземпляр по `t`; регистрирует все шесть типов; неизвестный
  ordinal даёт `null` (проверка `hasValueOf`), исключения нет. Используется сумкой и `AssemblyUserComponent` (поле `rw`).

<a id="cls-bagdao"></a>
### `BagDao` и миграция индекса

Коллекция `bag`. `findByOwnerId(ownerId, mailbox)` — документы игрока (ошибка → `null` в mailbox →
`ActorInitializationTask` проваливает инициализацию). `bulkUpdate(models, mailbox)` — `bulkWrite`,
в mailbox `true/false`. Миграция `1755491789292_bag.json` — индекс `{ownerId: 1}`.

<a id="cls-bagpage"></a>
### `BagPage extends AuthorizedUserPage`

Роут `/ingame/bag/get`: `{ items: [apiResponse доступных предметов] }`.

<a id="consumers"></a>
### Внешние точки: кто кладёт и списывает

- **`add` / `User.addItem`** (шаблоны и новые объекты): `QuestsUserComponent`,
  `AchievementUserComponent`, `BattlefieldUserComponent`, `IdleUserComponent`, `GoldenCoinsOffer`,
  `CampaignUserComponent`, `CampaignPage`, `TrainPage`,
  `CollectionUserComponent.grantReward`, `HangarUserComponent.addTank`,
  `AerodromeUserComponent.addAirplane`.
- **`addResource`**: `AssemblyUserComponent`, `TrainPage`, `SettingsPage` (золото за
  смену логина), `ClanPage` (золото за создание и смену названия клана), `MilitaryBasePage`/
  `MilitaryBaseUserComponent` (доллары и золото, ссылкой), `TrainUserComponent.initStarter`, `DevToolsPage`.
- **Удаление техники**: `addTank`/`addAirplane` делают `addCount(-1)` заменяемому экземпляру.
- **Чтение**: `HangarUserComponent`, `AerodromeUserComponent`, `AssemblyUserComponent`,
  `User.createTeam` (копии техники в бой), `User.getPower`, `TrainUserComponent`, страницы с проверкой
  цены.

<a id="persistence"></a>
### Персистентность

- **Загрузка**: `ActorInitializationTask` → `fetchUserBagDb` (`BagDao.findByOwnerId`) → шаг
  `buildComponents`: `dbMappingChildBuild`; пустой список → `initStarter()` сумки и поезда. Сумка
  грузится после `User.dbMappingBuild`, поэтому `AssemblyUserComponent.afterDBMappingBuild` видит её
  пустой (`assembly-architecture.md#tradeoffs`, п.1).
- **Сохранение**: `UserActor.onTick` и завершение актора → `ActorUpdateTask`, шаг `bagToDb`
  (`dbFetchChanged` → `BagDao.bulkUpdate`), затем `commitDbUpdates` после успеха всех компонентов.
- **Документ**: `_id` (= `uid`), `ownerId`, `id`, `t`, `c` (если не 1); у танка `level`, `stars {r, c}`;
  у самолёта `stars`.

<a id="client-contract"></a>
### Контракт с клиентом

- `/ingame/bag/get` → `{ items }`; push `/events/bag/update` → `{ items, del }`, приходит после
  обработки сообщения актора (`UserActor.onAfterMessageReceive` → `processDelayedExecution`).
- Предмет: `{ id, itemType, count, uid }` + у техники поля [`Tank`/`Airplane`](#cls-tank-airplane).
- Ресурс, дошедший до `count = 0`, приходит в `del`, хотя запись на сервере остаётся. Дальше `uid`
  зависит от пути начисления: `addResource` — тот же `uid`, запись возвращается в `items`; `add` — новая
  запись с новым `uid` ([п.2](#tradeoffs)); старый `uid` в `del` уже был отправлен.
- Мощность игрока приходит не из сумки, а в `user.power` (см. [п.1](#purpose)).
- Ответы с наградой (`CampaignUserComponent.getAirDrop` и др.) отдают `apiResponse()` шаблона с
  `uid = 000000000000000000000000`, отличным от `uid` записи в сумке.

<a id="tradeoffs"></a>
## 8. Компромиссы и известные проблемы

Решений пользователя по пунктам нет, всё найдено чтением кода; отложены на задачу по сумке (память
`server_bag_deferred_fixes`). Исправленных к 2026-10-19 пунктов нет.

0. **`long` вместо `int`.** `count`, `addCount`, `getResourceCount`, `addResource`, `setResource`,
   `ItemAddInfo.countBefore` стали `long`; в `CollectionUserComponent.grantReward` усечение
   `(int) reward.getCount()` для квестового события — выбор пользователя.

1. **`dbMappingChildBuild` приводит к `BagItem` без проверки.** `COLLECTION_ITEM` (`t = 6`) создаёт
   `CollectionItem`, не наследника `BagItem`: документ сумки с `t = 6` уронит загрузку игрока
   `ClassCastException`. Неизвестный `t` больше не роняет: документ пропускается (`null` из
   `ItemFactory`) и остаётся в БД нетронутым. Старые документы `t = 3` с ветки `koba/collection`
   (коллекционные предметы в сумке) теперь читаются как `MILITARY_BASE_BUILDING`; решение открыто,
   описано в `collections-architecture.md:480`. Тот же пункт — `collections-architecture.md#todo`.
2. **Ресурс с `count = 0` и `add` создают дубль.** `getStackedItem` ищет только доступные стеки: нулевой
   ресурс, пришедший через `add` (серебро с поезда, золото с airDrop, награды квестов), получает
   вторую запись того же `id` **с новым `uid`**; `resourceMap` переключается на неё, старая с нулём
   остаётся в `items` и в БД. При загрузке в `resourceMap` попадает последний документ выборки
   (порядок не задан): если он нулевой, `getResourceCount` вернёт 0, а `BagPage` покажет клиенту
   положительную запись. Через `addResource` дубля нет (тот же `uid`). Наличие дублей в данных не
   проверялось. Способ починки зависит от [gdd-open](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-open):
   ресурс остаётся с нулём — `add` стакует и в нулевую запись; исчезает — ресурсу нужно удаление.
3. **Два пути начисления ресурса.** `add(Resource)` стакует только в доступную запись, `addResource`
   видит нулевую. Одно правило («начислить ресурс», [gdd-resources](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-resources))
   в двух функциях — кандидат свести к одной (`agent-system-workflow.md#gdd-function-mapping`).
4. **`onClean` снимает с индекса по ключу без сверки объекта.** `resourceMap.remove(id)` убрал бы
   актуальный ресурс при удалении дубля. Сейчас не срабатывает: ресурсы не удаляются. Для техники ключ
   `uid`, проблемы нет.
5. **`addResource` не защищён от минуса** (расходится с
   [gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend)). Вызывающие
   проверяют остаток заранее, но при отсутствии записи `addResource(id, 0)` создаёт ресурс с
   `count = 0`, отрицательная дельта — отрицательный `count`.
6. **Списание и удаление техники — неявный порядок у вызывающих** (`agent-system-workflow.md#no-implicit-order`):
   «проверить `getResourceCount` → `addResource(-цена)`» повторено в `TrainPage`, `SettingsPage`,
   `AssemblyUserComponent`, `ClanPage`, `MilitaryBasePage`; `addCount(-1)` заменяемой технике — в ангаре/аэродроме
   (удаление насовсем — по [gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles)).
   Метода-перехода у владельца («списать, если хватает») нет, правило минуса держится на дисциплине
   вызывающих.
7. **Результат `add` не проверяется в ангаре и аэродроме.** `HangarUserComponent.addTank` и
   `AerodromeUserComponent.addAirplane` уменьшают `count` заменяемой техники, потом берут
   `itemAddInfo.item.getUid()`. Отказ `add` (например, повторная выдача уже лежащего в сумке объекта,
   `assembly-architecture.md#tradeoffs` п.2) даёт `NullPointerException` после удаления заменяемой
   техники.
8. **Общие изменяемые `ItemAddInfo`/`ItemEmitInfo`.** Результат `add` перезаписывается следующим
   вызовом, `ItemEmitInfo` очищается после `emit`. Безопасно, пока все читают синхронно в потоке актора.
9. **`BAG_ITEM_CHANGE_COUNT_ID` никто не слушает.** Квестовые события о ресурсах (`SILVER_COINS_GAINED`)
   триггерят вызывающие после `add`, сумка их не шлёт.
10. **`initStarter` пуст**, комментарий обещает стартовые ресурсы; схемы начисляет
    `TrainUserComponent.initStarter` (50 схем танка; [gdd-starter](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-starter)
    расходится, ГДД обновляется). Срабатывает только при полностью пустой коллекции `bag` игрока.
11. **`setResource` не используется** (кандидат на удаление).
12. **Записи удаляются из памяти до подтверждения БД.** `dbFetchChanged` убирает `DELETED` из `items` и
    снимает `NEW` сразу; повтор при сбое держится только на кэше `dbUpdateDocuments`. Тот же приём у
    кодекса, коллекций и достижений.
13. **Индекс только `{ownerId: 1}`.** Уникальности `{ownerId, t, id}` для ресурсов нет; ставить её можно
    после очистки дублей из п.2.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: `/workspace/client/.claude/docs/game-design/bag-gdd.md` (черновик, 2026-10-13).

| Правило ГДД | Где в коде | Соответствие |
|---|---|---|
| [gdd-purpose](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-purpose) — инвентарь и учёт в БД | `BagUserComponent`, [персистентность](#persistence) | да |
| [gdd-resources](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-resources) — учёт ресурсов | `Resource`, `getResourceCount`, `add`, `addResource` | да; два пути — [п.3](#tradeoffs) |
| [gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles) — техника, замена удаляет насовсем | `Tank`, `Airplane`, `addCount(-1)` в ангаре/аэродроме | да; [п.6–7](#tradeoffs) |
| [gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend) — минус запрещён | проверки у вызывающих + `addResource(-цена)` | частично: [п.5–6](#tradeoffs) |
| [gdd-starter](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-starter) — 50 схем танка, 0 схем самолёта | `TrainUserComponent.initStarter` | нет (ГДД обновлён под код 2026-10-19) |
| [gdd-power](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-power) — мощность по технике сумки | `User.getPower`, `TankUtils`/`AirplaneUtils.getUserPower`, `recalculate` | да |
| [gdd-open](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-open) — ресурс с нулём | `canBeDeleted() == false`, `del` в push | вопрос открыт; от него зависит [п.2](#tradeoffs) |

Сверка с другими документами: `assembly-architecture.md` (`takeTankReward`: заменяемый танк теряет 1
`count`) сходится с кодом, но не упоминает NPE из п.7; `airdrop-architecture.md#patterns` и
`collections-architecture.md#todo` сходятся.

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от корня репозитория `server`. Классификация по `#doc-standard` п.10. Проверено `grep` по именам классов прямого влияния (2026-10-19); совпадения без отношения к сумке (`commons` `Resource`, `Migration`, `Assault Tank` в `balance.json`) не включены.

### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/bag/BagUserComponent.java` | компонент сумки пользователя: кэш предметов, начисление, push, персистентность |
| `game/src/main/java/com/linkedgames/game/model/bag/BagItem.java` | базовый предмет сумки: счётчик, флаги `NEW`/`DELETED`/`IN_BAG` |
| `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` | ресурс (все виды из `ItemId`), `canBeDeleted() == false` |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/Tank.java` | танк в сумке |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankParams.java` | расчётные параметры танка, `recalculate` |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankUtils.java` | мощность и утилиты по танкам пользователя |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/Airplane.java` | самолёт в сумке |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneParams.java` | расчётные параметры самолёта, `recalculate` |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneUtils.java` | мощность и утилиты по самолётам пользователя |
| `game/src/main/java/com/linkedgames/game/model/bag/utils/ItemAddInfo.java` | результат добавления предмета в сумку |
| `game/src/main/java/com/linkedgames/game/model/bag/utils/ItemEmitInfo.java` | данные события изменения предмета (`UserEmitterId.BAG_ITEM_*`) |
| `game/src/main/java/com/linkedgames/game/model/item/Item.java` | базовая сущность предмета, документная сериализация |
| `game/src/main/java/com/linkedgames/game/model/item/ItemType.java` | enum типа предмета (поле `t` в БД) |
| `game/src/main/java/com/linkedgames/game/model/item/ItemFactory.java` | создание предмета по документу БД, `null` для неизвестного типа |
| `game/src/main/java/com/linkedgames/game/model/bag/military_base/MilitaryBaseBuilding.java` | `BagItem` военной базы (ссылкой) |
| `game/src/main/java/com/linkedgames/game/model/bag/military_base/MilitaryBaseAviationFactorySlot.java` | то же: слот авиазавода |
| `game/src/main/java/com/linkedgames/game/model/bag/military_base/MilitaryBaseBoost.java` | то же: буст |
| `game/src/main/java/com/linkedgames/game/model/item/ItemId.java` | константы идентификаторов предметов (ресурсов) |
| `game/src/main/java/com/linkedgames/game/dao/BagDao.java` | чтение и `bulkWrite` коллекции `bag` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BagPage.java` | роут `/ingame/bag/get` |
| `game/src/main/resources/migrations/1755491789292_bag.json` | индекс `{ownerId: 1}` коллекции `bag` |

### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankType.java` | зависимость: enum типа танка (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankArmorType.java` | зависимость: enum типа брони танка (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankAmmoType.java` | зависимость: enum типа боеприпасов танка (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankDropType.java` | зависимость: enum типа выпадения танка (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankTitleType.java` | зависимость: enum титула танка (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/data/TankData.java` | зависимость: балансовый справочник танков (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneType.java` | зависимость: enum типа самолёта (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneGunType.java` | зависимость: enum типа вооружения самолёта (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneBombType.java` | зависимость: enum типа бомб самолёта (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneArmorType.java` | зависимость: enum типа брони самолёта (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/data/AirplaneData.java` | зависимость: балансовый справочник самолётов (`tank-airplane-data-architecture.md`) |
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | владелец компонента: `getBagComponent`, `addItem`, `getPower`, `createTeam` |
| `game/src/main/java/com/linkedgames/game/model/user/UserEmitterId.java` | идентификаторы эмиттера `BAG_ITEM_*` |
| `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorInitializationTask.java` | загрузка сумки из БД (`fetchUserBagDb`), стартовый набор |
| `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorUpdateTask.java` | периодическая запись сумки в БД (`bagToDb`) |
| `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` | регистрация роута `BagPage` |
| `game/src/main/java/com/linkedgames/game/model/hangar/HangarUserComponent.java` | добавление/замена танков, `addCount(-1)` |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/AerodromeUserComponent.java` | добавление/замена самолётов |
| `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` | сборка: списание ресурсов, выдача техники |
| `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` | поезд: стартовые схемы (`initStarter`), танки сумки для туториальной выдачи |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestsUserComponent.java` | награды квестов ресурсами |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` | награды кампании и airDrop ресурсами |
| `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldUserComponent.java` | ресурсные награды поля боя |
| `game/src/main/java/com/linkedgames/game/model/idle/IdleUserComponent.java` | начисление ресурсов простоя |
| `game/src/main/java/com/linkedgames/game/model/offers/list/GoldenCoinsOffer.java` | начисление золота по предложению |
| `game/src/main/java/com/linkedgames/game/model/achievements/Achievement.java` | награда достижения ресурсом |
| `game/src/main/java/com/linkedgames/game/model/team/Team.java` | команда из `Tank`/`Airplane` сумки |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleTankData.java` | данные танка боя из `Tank` |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleAirplaneData.java` | данные самолёта боя из `Airplane` |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleDataFactory.java` | сборка данных боя из техники сумки |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitTank.java` | боевая единица, использует `TankParams` |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitAirplane.java` | боевая единица, использует `AirplaneParams` |
| `game/src/main/java/com/linkedgames/game/model/collections/CollectionUserComponent.java` | награды коллекций как `BagItem`, начисление в сумку |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionList/Collection.java` | абстрактные награды коллекции (`BagItem`) |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionAlbum.java` | награда альбома ресурсом |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionExperimentalTank.java` | награда-танк коллекции |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionExperimentalTankEntry.java` | создание танка по записи коллекции |
| `game/src/main/java/com/linkedgames/game/model/collections/itemList/CollectionItem.java` | возвращает `ItemType.COLLECTION_ITEM` (источник риска [п.1](#tradeoffs)) |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/AlbumsSectionType.java` | выдача наград альбомов |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/ExperimentalTanksSectionType.java` | выдача танков экспериментальной секции |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/TrainPage.java` | поезд: списание схемы танка за призыв, серебро за продажу и замену танка, покупка схем за золото |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AssemblyPage.java` | замена танка при сборке |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` | награды кампании ресурсами |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/ClanPage.java` | списание золота (создание клана, смена названия) |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/MilitaryBasePage.java` | списание долларов и золота военной базы (ссылкой) |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseUserComponent.java` | военная база: `getItem` сумки, стартовые доллары (ссылкой) |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CodexPage.java` | создание `Tank`/`Airplane` для кодекса без сумки |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionAlbumPage.java` | выдача наград альбомов |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionExperimentalTankPage.java` | замена танка наградой коллекции |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/SettingsPage.java` | операции с ресурсами в настройках |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` | dev-начисление ресурсов и техники |
| `game/src/main/java/com/linkedgames/game/scripts/CleanupAerodrome.java` | скрипт чистки самолётов в коллекции `bag` |
