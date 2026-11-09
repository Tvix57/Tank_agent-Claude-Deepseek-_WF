# Кодекс — `CodexUserComponent` (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-10-13;
> актуализирован 2026-10-19 после merge `origin/amnesia/fix` (не закоммичен). Всё ниже подтверждено
> чтением кода, запуском не проверялось.
> Клиентская сторона (`src/views/home_screen/popups/profile/codex/CodexTanksSection.ts`,
> `CodexAirplanesSection.ts`) не анализировалась.

ГДД: отсутствует (создание запрошено по `agent-system-workflow.md#gdd`; ссылки `#gdd-<раздел>` ниже
появятся после его создания).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`CodexUserComponent`](#cls-codexusercomponent)
   - [`CodexEntry`](#cls-codexentry)
   - [`CodexTankEntry`, `CodexAirplaneEntry`](#cls-entries)
   - [`CodexEntryType`, `CodexEntryFactory`](#cls-type-factory)
   - [`CodexDao` и миграция индекса](#cls-codexdao)
   - [`CodexPage`](#cls-codexpage)
   - [Точки записи в кодекс](#producers)
   - [Персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Кодекс — справочник техники игрока: какие танки и самолёты он уже получал. Для каждого `id` танка
(и отдельно самолёта) кодекс хранит одну запись — лучший полученный экземпляр по мощности (`power`).
Танковая запись хранит `id`, уровень, звёзды и мощность; самолётная — `id`, звёзды и мощность (уровня у
самолёта в кодексе нет).

Правила по коду:

- **Когда пишется запись.** В момент выпадения техники, до того как игрок её принял: призыв поезда
  (`TrainUserComponent.receiveTank`), награда сборки (`AssemblyUserComponent`, до `takeReward`/
  `rejectReward`), запуск производства самолёта на фабрике военной базы (`MilitaryBasePage.actionRunFactory`, роут
  `/runFactory`). Отказ от награды или
  продажа техники запись не убирает.
- **Что не пишется.** Экспериментальные танки из коллекций (`ExperimentalTanksSectionType`), боты боя,
  шаблоны `CodexPage`/`DevToolsPage`. Для коллекций это правило ГДД коллекций
  (`/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward`), решение 2026-10-05.
- **Сравнение.** Новая запись заменяет текущую, если её `power` не меньше (`>=`); при равной мощности
  тоже происходит замена. Если текущая сильнее — новая отбрасывается.
- **Прокачка не отражается.** Мощность фиксируется при выпадении; повышение уровня/звёзд танка в сумке
  кодекс не обновляет.
- **Показ.** `CodexPage` отдаёт весь каталог техники из баланса и отдельно список собранного игроком.

<a id="references"></a>
## 2. Референсы

Нет: компонент написан в исходном коммите `d3d31c4` и с тех пор не менялся. Ближайший аналог по
схеме хранения — записи коллекций (отдельная Mongo-коллекция с `ownerId`, bulk-запись), см.
[collections-architecture.md](collections-architecture.md).

<a id="patterns"></a>
## 3. Паттерны

- **Отдельная Mongo-коллекция на записи игрока** (`codex`, документ на запись, `ownerId`) вместо
  поддокумента `User`. Запись в БД — `bulkWrite` из `ActorUpdateTask`, загрузка — `findByOwnerId` в
  `ActorInitializationTask`.
- **Битовые флаги состояния записи** (`NEW`, `DELETED`, `ADDED`) с отложенной синхронизацией:
  изменения копятся в памяти и превращаются в `UpdateOneModel`/`DeleteOneModel` в `dbFetchChanged`.
- **Фабрика по типу** (`CodexEntryFactory`, `ImmutableMap<тип, Supplier>`) для полиморфной загрузки.
- **Индекс в памяти**: список (порядок, итерация) + `Map<id, запись>` (поиск текущей лучшей записи) на
  каждый тип техники.

<a id="class-list"></a>
## 4. Список классов

Пакет `game/src/main/java/com/linkedgames/game/`:

| Класс | Путь |
|---|---|
| `CodexUserComponent` | `model/codex/CodexUserComponent.java` |
| `CodexEntry` | `model/codex/CodexEntry.java` |
| `CodexEntryType` | `model/codex/CodexEntryType.java` |
| `CodexEntryFactory` | `model/codex/CodexEntryFactory.java` |
| `CodexTankEntry` | `model/codex/entries/CodexTankEntry.java` |
| `CodexAirplaneEntry` | `model/codex/entries/CodexAirplaneEntry.java` |
| `CodexDao` | `dao/CodexDao.java` |
| `CodexPage` | `pages/ws/ingame/CodexPage.java` (роут `/ingame/codex` в `WSRouter`) |

Смежные места (не часть пакета): `User.getCodexUserComponent`, `Tank.createCodexEntry`,
`Airplane.createCodexEntry`, `TrainUserComponent.receiveTank`, `AssemblyUserComponent` (создание награды),
`MilitaryBasePage.actionRunFactory`, `ActorUpdateTask` (`codexToDb`), `ActorInitializationTask`
(`fetchUserCodexDb`), миграция `game/src/main/resources/migrations/1757923635360_codex.json`.

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#references`, `#patterns`, `#class-list`, `#class-nav`, `#cls-codexusercomponent`,
`#m-add`, `#m-onclean`, `#m-dbfetchchanged`, `#cls-codexentry`, `#cls-entries`, `#cls-type-factory`,
`#cls-codexdao`, `#cls-codexpage`, `#producers`, `#persistence`, `#client-contract`, `#tradeoffs`,
`#bug-duplicates`, `#gdd-link`, `#file-map`.

<a id="class-nav"></a>
## 6. Оглавление по классам

- [`CodexUserComponent`](#cls-codexusercomponent): [`add`](#m-add), [`onClean`](#m-onclean),
  [`dbFetchChanged`](#m-dbfetchchanged)
- [`CodexEntry`](#cls-codexentry)
- [`CodexTankEntry` / `CodexAirplaneEntry`](#cls-entries)
- [`CodexEntryType` / `CodexEntryFactory`](#cls-type-factory)
- [`CodexDao`](#cls-codexdao)
- [`CodexPage`](#cls-codexpage)

## 7. Классы и методы

<a id="cls-codexusercomponent"></a>
### `CodexUserComponent`

`UserChildComponent` игрока, создаётся лениво в `User.getCodexUserComponent()` с именем `"Codex"`.
Поля: общий список `entries` (все записи, в том числе помеченные на удаление до ближайшей записи в БД),
`tanksList`/`tanksMap` и `airplanesList`/`airplanesMap` по типам, кэш `dbUpdateDocuments`.

- `modifyReceiver` — пустой, сообщений актора компонент не обрабатывает.
- `forEachTanks(Consumer)` / `forEachAirplanes(Consumer)` — обход списка типа с пропуском записей с
  флагом `DELETED`. Правило: показ собранной техники (`CodexPage`).

<a id="m-add"></a>
#### `add(CodexEntry)`

Правило: "одна запись на `id` техники — лучшая по мощности". Шаги:

1. Запись уже добавлена (`ADDED`) или удалена (`DELETED`) — выход. (Проверка `DELETED` продублирована
   вторым `if` — мёртвый код.)
2. Ищет текущую запись того же типа по `id` в `tanksMap`/`airplanesMap`. Если она есть и не удалена:
   `current.power > new.power` — новая отбрасывается; иначе текущей ставится `DELETED`.
3. Новой ставится `NEW`, затем `add0`.

Ветки танка и самолёта дословно повторяют друг друга (разные классы без общего интерфейса `getId`/
`getPower`).

- `add0(CodexEntry)` (private) — флаг `ADDED`, добавление в `entries`, в список и карту своего типа
  (`map.put(id, entry)` — перезаписывает прежнее значение). Используется и `add`, и загрузкой из БД.

<a id="m-onclean"></a>
#### `onClean(CodexEntry)` (private)

Убирает запись из списка и карты своего типа после того, как она выброшена из `entries`. Карты
(`tanksMap`/`airplanesMap`) не чистятся: после merge удалён безусловный `map.remove(id)`, а новая запись
сама перезаписывает ключ в `add0`. Вытесненная запись остаётся в карте с флагом `DELETED` до замены;
`add` такие записи пропускает. Источник бага [#bug-duplicates](#bug-duplicates) в `onClean` устранён.

<a id="m-dbfetchchanged"></a>
#### `dbFetchChanged()` и `commitDbUpdates()`

`dbFetchChanged` возвращает закэшированный `dbUpdateDocuments`, если он есть (повтор после неудачной
записи). Иначе проходит `entries`:

- `NEW` + `DELETED` (запись создана и вытеснена в одном цикле сохранения) — выбросить из памяти, в БД
  ничего;
- `DELETED` — `DeleteOneModel` по `_id`, выбросить из памяти;
- `NEW` — снять `NEW`, `UpdateOneModel` с `$set` всего документа + `ownerId`, `upsert: true`.

Записи выбрасываются из памяти и теряют `NEW` до подтверждения БД; повтор при ошибке держится на кэше
`dbUpdateDocuments`. Изменять существующую запись компонент не умеет — только добавлять и удалять.

`commitDbUpdates` сбрасывает кэш и пересобирает изменения; `true`, если пересобирать нечего (вызывается
из `ActorUpdateTask` после успешной записи всех компонентов).

- `dbMappingChildBuild(List<Document>)` — загрузка: для каждого документа фабрика → `dbMappingBuild` →
  `add0` без сравнения мощности. Дубли из БД не сводятся, в карте остаётся последний загруженный (не обязательно сильнейший).

<a id="cls-codexentry"></a>
### `CodexEntry`

Абстрактная запись (`IPersistentObject`). `uid` (`ObjectId`, создаётся лениво в `getUid`), битовое поле
`condition` с константами `INTERNAL_CONDITION_NEW`/`DELETED`/`ADDED` и protected-методами
`addCondition`/`removeCondition`/`hasCondition` (доступны компоненту, так как он в том же пакете).
`getType()` — абстрактный. `dbMappingBuild` читает `_id`, `dbToData` пишет `_id` и `t` (ordinal типа).
`DBFields`: `_id`, `t`, `ownerId`.

<a id="cls-entries"></a>
### `CodexTankEntry`, `CodexAirplaneEntry`

Данные записи с fluent-сеттерами; `setStars` копирует ранг и количество в собственный объект `Stars`.

- `CodexTankEntry`: `id` (`id`), `level` (`l`), `stars` (`s`), `power` (`p`); `getType() = TANK`.
- `CodexAirplaneEntry`: `id`, `stars` (`s`), `power` (`p`); `getType() = AIRPLANE`.

`dbMappingBuild` читает поля через `getInteger` с распаковкой в `int` — отсутствующее поле даст
`NullPointerException` при загрузке игрока.

<a id="cls-type-factory"></a>
### `CodexEntryType`, `CodexEntryFactory`

`CodexEntryType` — `TANK`, `AIRPLANE`; в БД хранится `ordinal` (порядок значений менять нельзя).
`CodexEntryFactory.newFromDocument(Document)` — тип по полю `t` (по умолчанию 0 = `TANK`) → новый пустой
объект; неизвестный ordinal проверяется `CodexEntryType.VALUES.hasValueOf` → `null`, такой документ при
загрузке пропускается (до merge неизвестный ordinal приводил к ошибке в `valueOf`).

<a id="cls-codexdao"></a>
### `CodexDao` и миграция индекса

Коллекция `codex`. `findByOwnerId(ownerId, mailbox)` — все записи игрока (ошибка → `null` в mailbox,
инициализация игрока падает с "Init codex failed"). `bulkUpdate(documents, mailbox)` — `bulkWrite`,
в mailbox `true`/`false` по успеху. Миграция `1757923635360_codex.json` создаёт неуникальный индекс
`{ownerId: 1}`.

<a id="cls-codexpage"></a>
### `CodexPage`

`AuthorizedUserPage`, роуты `/ingame/codex/tanks` и `/ingame/codex/airplanes`. Каждый собирает:

- каталог — все танки рангов `Rank.TANKS` (самолёты — `Rank.AIRPLANES`) из `Balance` как шаблоны
  (`createNew(data, true)` → `recalculateParams` → `apiResponse`);
- `collected` — по записи кодекса шаблон техники с её `id`, уровнем (только танк) и звёздами,
  `recalculateParams`, `apiResponse`. Мощность в ответе пересчитывается по текущему балансу; сохранённый
  `power` записи наружу не уходит и служит только для сравнения в [`add`](#m-add).

<a id="producers"></a>
### Точки записи в кодекс

Во всех точках вызывающий делает два шага: `X.createCodexEntry()` (у `Tank`/`Airplane`:
`recalculateParams` + снимок `id`/уровня/звёзд/мощности) и `user().getCodexUserComponent().add(entry)`.

| Источник | Метод | Момент |
|---|---|---|
| Поезд, туториальная ветка | `TrainUserComponent.receiveTank` | фиксированный танк туториала при выпадении |
| Поезд, обычный призыв | `TrainUserComponent.receiveTank` | при выпадении, до `/accept` |
| Сборка | `AssemblyUserComponent` (создание `reward`) | при создании награды, до `takeReward`/`rejectReward` |
| Военная база, фабрика авиации | `MilitaryBasePage.actionRunFactory` (`/runFactory`) | при запуске производства: `generateAirplane` → `createCodexEntry` + `add`, до приёма самолёта |

`AerodromeUserComponent` и `AerodromePage` в кодекс больше не пишут (призыв самолёта перенесён в
`MilitaryBasePage`). `MilitaryBaseAviationFactory` в кодекс не пишет. Повторный вызов `receiveTank`
при уже выпавшем танке возвращается раньше и запись не дублирует.

<a id="persistence"></a>
### Персистентность

Своя коллекция `codex` (документ на запись), поля `_id`, `t`, `ownerId`, `id`, `l` (танк), `s`, `p`.
Сохранение — шаг `codexToDb` в `ActorUpdateTask` (лог "has changed codexDocuments"), неуспех любого из
компонентов → `persistFailed("db error")`; после успеха — `commitDbUpdates`. Загрузка — шаг
`fetchUserCodexDb` в `ActorInitializationTask`, затем `dbMappingChildBuild`. `changedField` и поддокумент
`User` не используются.

<a id="client-contract"></a>
### Контракт с клиентом

Запрос без параметров. Ответ `/tanks`: `{ tanks: [Tank.apiResponse()...], collected: [Tank.apiResponse()...] }`;
`/airplanes`: `{ airplanes: [...], collected: [...] }`. Push-событий у кодекса нет. Повторы в
`collected` возможны из-за [#bug-duplicates](#bug-duplicates); как клиент их обрабатывает — не
проверялось.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

<a id="bug-duplicates"></a>
1. **Дубли записей (в проде с `d3d31c4`, найден 2026-10-05).** После merge `onClean` больше не чистит
   карты, поэтому новые дубли через `onClean` не возникают; осталось: дубли, уже лежащие в БД, и их
   загрузка без сведения (см. ниже). Исторический сценарий (до merge): в карте лежит запись A; `add(B)` с `power >= A` помечает A `DELETED` и кладёт B в карту.
   При ближайшем `dbFetchChanged` A удаляется из БД, а `onClean(A)` делает `tanksMap.remove(id)` и
   выкидывает из карты B (B остаётся в списке и пишется в БД). Следующий `add(C)` того же `id` не
   находит текущей записи и добавляется без сравнения — в списке и в БД две записи, `CodexPage` отдаёт
   обе в `collected`. Тот же эффект при цепочке A → B → C внутри одного цикла сохранения (ветка
   `NEW`+`DELETED` для B). Самолёты (`airplanesMap`) — аналогично. Загрузка
   ([`dbMappingChildBuild`](#m-dbfetchchanged)) дубли не сводит: в карте остаётся последний
   загруженный, остальные живут в списке и в БД бессрочно.
   Фикс `onClean` реализован (удаление `map.remove`). Не реализовано: при загрузке сводить дубли — оставлять запись с наибольшей `getPower()`,
   остальные помечать `DELETED` (удалятся при ближайшем сохранении). Уникальный индекс
   `{ownerId, t, id}` нельзя ставить, пока в проде есть дубли: сначала очистка данных, потом индекс
   (правило "миграция индекса сразу").
2. **Повторяющийся код по типам.** Ветки танка и самолёта в `add`/`add0`/`onClean`, классы записей и
   `forEach*` дублируют одно правило; общего интерфейса (`getId`, `getPower`) нет. Кандидат на
   сведение в одну функцию (правило "одно правило ГДД — одна функция").
3. **Двухшаговая запись у вызывающих.** Три точки делают `createCodexEntry()` + `add()`; правило
   "записать выпавшую технику" выражено у вызывающего, а не у владельца. Кандидат — один метод
   компонента, принимающий `Tank`/`Airplane`.
4. **Запись до получения.** Техника попадает в кодекс при выпадении, даже если игрок отказался от
   награды сборки. Нужна сверка с ГДД (его пока нет).
5. **Устаревшая мощность.** `power` записи фиксируется при выпадении и не пересчитывается при
   ребалансе; сравнение в `add` идёт по старым значениям, хотя `CodexPage` показывает пересчитанные.
6. **Равная мощность вызывает замену** (`>=`): лишняя пара delete + upsert в БД при выпадении
   равноценного экземпляра.
7. **Мёртвая проверка** `DELETED` в начале `add` (второй `if`).
8. **Хрупкая загрузка:** отсутствующее поле `id`/`l`/`p` в документе → NPE и сбой инициализации
   игрока.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: отсутствует. Правила, которые нужно в нём зафиксировать и затем связать с методами:
"одна запись на технику, лучшая по мощности" ([`add`](#m-add)), "когда техника попадает в кодекс"
([#producers](#producers)), "какие источники не пишут в кодекс" (экспериментальные танки — уже есть в
`/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward`), "что показывается в кодексе"
([`CodexPage`](#cls-codexpage)).

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от корня репозитория `/workspace/server`.

### Файлы прямого влияния

- `game/src/main/java/com/linkedgames/game/model/codex/CodexUserComponent.java` — компонент: карта записей, `add`, `onClean`, пакетная запись в БД.
- `game/src/main/java/com/linkedgames/game/model/codex/CodexEntry.java` — базовая запись кодекса, флаги состояния, сохранение документа.
- `game/src/main/java/com/linkedgames/game/model/codex/CodexEntryType.java` — тип записи (танк, самолёт).
- `game/src/main/java/com/linkedgames/game/model/codex/CodexEntryFactory.java` — создание записи нужного типа из документа БД.
- `game/src/main/java/com/linkedgames/game/model/codex/entries/CodexTankEntry.java` — запись танка.
- `game/src/main/java/com/linkedgames/game/model/codex/entries/CodexAirplaneEntry.java` — запись самолёта.
- `game/src/main/java/com/linkedgames/game/dao/CodexDao.java` — доступ к коллекции кодекса в MongoDB.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CodexPage.java` — роуты `/ingame/codex/tanks` и `/airplanes`.
- `game/src/main/resources/migrations/1757923635360_codex.json` — миграция индексов коллекции кодекса.

### Файлы косвенного влияния

- `game/src/main/java/com/linkedgames/game/model/user/User.java` — владеет компонентом, `getCodexUserComponent`, передача получателю изменений.
- `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` — регистрация роута `/ingame/codex`.
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorInitializationTask.java` — загрузка кодекса игрока из БД при входе (`fetchUserCodexDb`).
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorUpdateTask.java` — запись изменений кодекса в БД и подтверждение (`codexToDb`, `commitDbUpdates`).
- `game/src/main/java/com/linkedgames/game/model/bag/tank/Tank.java` — зависимость: тип другой области (сумка), создаёт запись кодекса в `createCodexEntry`.
- `game/src/main/java/com/linkedgames/game/model/bag/airplane/Airplane.java` — зависимость: тип другой области (сумка), создаёт запись кодекса в `createCodexEntry`.
- `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` — запись в кодекс при получении танка (`receiveTank`).
- `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` — запись в кодекс при выдаче награды сборки.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/MilitaryBasePage.java` — запись в кодекс при запуске производства самолёта (`actionRunFactory`); область военной базы здесь не описывается.

Итого: 9 файлов прямого влияния, 9 косвенного. Полнота проверена `grep -ri codex` по `game/src`.
