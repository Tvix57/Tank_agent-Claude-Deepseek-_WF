# TankData / AirplaneData — балансовые данные танков и самолётов

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду (код в рамках
> задачи не менялся), 2026-09-28; актуализирован после merge `amnesia/fix` 2026-10-19 (не закоммичен). Доверие пониженное: всё ниже подтверждено чтением кода, но
> фактическое содержимое удалённой Google-таблицы баланса не проверялось (см. [компромиссы](#tradeoffs)).

ГДД: отсутствует (создание отложено по решению пользователя 2026-10-13).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация по классам](#class-nav)
6. Классы
   - [`TankData`](#class-tankdata)
   - [`AirplaneData`](#class-airplanedata)
7. [Общее и различия TankData / AirplaneData](#diff)
8. [Кто использует данные](#consumers)
9. [Принятые уязвимости и компромиссы](#tradeoffs)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

`TankData` и `AirplaneData` — неизменяемые (все поля `public final`) описания **модели** танка и
самолёта из баланса игры: имя, ранг, тип, нация и базовые боевые характеристики. Это "справочник",
а не предмет игрока: у игрока в сумке лежат `Tank`/`Airplane` (наследники `BagItem`), которые хранят
только `id` модели плюс собственное состояние (уровень — только у танка, звёзды) и по `id` каждый раз
получают свою запись `TankData`/`AirplaneData` из `Balance`.

**Откуда заполняются.** Только из баланса, не из MongoDB:

1. При старте (`Globals` → `BalanceImporter.importFromRemote()`) импорт из Google-таблицы выполняется,
   только если `app.balanceShouldImport=true`. В закоммиченном `game/src/main/resources/app.properties`
   стоит `false` (дефолт в коде тоже `false`), поэтому по умолчанию импорт пропускается. Включить его
   можно своим файлом свойств через аргумент запуска `-appPropFile=<путь>`
   (`Environment.overrideApplicationProperties`). При включённом импорте листы, в т.ч. `Tanks` и
   `Airplanes`, скачиваются через Sheets API, из каждого листа удаляется первая строка (заголовки), и
   результат перезаписывает файл баланса (`app.balanceFilePath`; если пусто, как в закоммиченном
   файле, — `src/main/resources/balance.json` относительно каталога модуля).
2. `BalanceImporter.buildBalance()` читает файл (fallback — `/balance.json` из jar) и вызывает
   `Balance.INSTANCE.build(rawJson)`.
3. `Balance.build` через generic-метод `mapping(builder, jsonArray)` вызывает `TankData::build` /
   `AirplaneData::build` для каждой строки листов `"Tanks"` / `"Airplanes"` и кладёт результат в
   `Map<Integer, …>` по `key()` (= `id`); результат `null` пропускается (`mapping` делает `continue`). Затем строятся производные индексы: список id
   (`tanksId`/`airplanesId`) и группировка по рангу (`rankToTankData`/`rankToAirplaneData`).

Строка листа — это `JSONArray` строк; значения читаются по **жёстко заданным индексам колонок**,
enum-ы — через `EnumValues.valueOf(int)` (по ordinal).

В БД сохраняется только `id` модели (как `BagItem.id`), поэтому смена характеристик в таблице
применяется ко всем уже выданным танкам/самолётам после перезагрузки баланса.

<a id="references"></a>
## 2. Референсы

- `CollectionItem` (наследник `Item`, не `BagItem`) — `collections-architecture.md`
  ([референсы](collections-architecture.md#references),
  [структура пакетов](collections-architecture.md#package-structure),
  [`CollectionItem`](collections-architecture.md#class-collectionitem)); здесь не дублируется.
- Аналогичные балансовые классы с тем же контрактом `KeyModel` + `static build(JSONArray)`:
  `CollectionsData`, `CollectionItemData`, `AchievementData`, `SummonUpgradeData` (общий лист улучшений
  призыва вместо `TrainUpgradeData`/`AerodromeUpgradeData`), `UserLevelData`, `PercentValueData`,
  данные военной базы (`MilitaryBase*Data`, ссылкой); все грузятся в `Balance.build`.

<a id="patterns"></a>
## 3. Паттерны

- **Static factory из строки таблицы** — `build(JSONArray)` сопоставляет позиционные колонки полям.
- **`KeyModel<Integer>`** (`com.linkedgames.game.balance.KeyModel`, единственный метод `key()`) —
  контракт, по которому `Balance.mapping` строит `Map` по id.
- **Immutable value object** — все поля `public final`, без геттеров.
- **Flyweight / справочник + экземпляр** — `Tank`/`Airplane` хранят только id, характеристики берут
  из общего `TankData`/`AirplaneData` (`data()` → `Balance.INSTANCE.getXData(getId())`), а
  производные значения (с учётом уровня/звёзд) считают в `TankParams`/`AirplaneParams`.
- **Singleton-реестр** — `Balance.INSTANCE`.

<a id="class-list"></a>
## 4. Список классов

Документируемые (не изменялись):

| Класс | Путь |
|---|---|
| `TankData` | `game/src/main/java/com/linkedgames/game/model/bag/tank/data/TankData.java` |
| `AirplaneData` | `game/src/main/java/com/linkedgames/game/model/bag/airplane/data/AirplaneData.java` |

Смежные (упоминаются как контекст, отдельно не документируются): `Balance`, `BalanceImporter`,
`KeyModel` (пакет `game/balance`), `Tank`, `TankParams`, `Airplane`, `AirplaneParams`, enum-ы
`TankType`, `TankArmorType`, `TankAmmoType`, `TankDropType`, `TankTitleType`, `AirplaneType`,
`AirplaneArmorType`, `AirplaneGunType`, `AirplaneBombType`, `Rank`, `Country`.

<a id="class-nav"></a>
## 5. Навигация по классам

| Класс | Раздел |
|---|---|
| `TankData` | [ссылка](#class-tankdata) |
| `AirplaneData` | [ссылка](#class-airplanedata) |
| Сравнение | [ссылка](#diff) |

<a id="class-tankdata"></a>
## 6.1. `TankData`

Модель танка из листа `Tanks`. Реализует `KeyModel<Integer>`.

**Константы:** `MIN_LEVEL = 1`, `MAX_LEVEL = 100` — границы уровня танка. Используются как clamp
при выдаче/генерации танков (`TrainUserComponent.receiveTank`, `AssemblyUserComponent`,
`BattleDataFactory`) и как стартовый уровень туториальных танков. Уровень хранится в `Tank`, не
в `TankData`.

**Фильтр по `dropType`.** В ветке `amnesia/fix` `build` отбрасывал танки с `dropType != 1`; при merge фильтр
убран решением пользователя 2026-10-19. Грузятся все строки `Tanks`, включая `COLLECTION_REWARD`
(в `balance.json` 64 строки с `2`, id 286–349 — награды экспериментальных танков коллекций).

**Поля и колонки листа `Tanks`** (индекс = позиция в строке после удаления заголовка):

| Поле | Тип | Колонка | Примечание |
|---|---|---|---|
| `id` | `Integer` | 0 | ключ (`key()`) |
| `name` | `String` | 1 | |
| `rank` | `Rank` | 2 | ordinal |
| `type` | `TankType` | 3 | ordinal; определяет допустимые позиции (`TankType.TYPE_POSITION`) |
| `country` | `Country` | 5 | ordinal |
| `hp` | `int` | 7 | базовое, до уровня/звёзд |
| `damage` | `int` | 8 | базовое, до уровня/звёзд |
| `recharge` | `int` | 9 | |
| `penetration` | `int` | 10 | |
| `armor` | `int` | 11 | |
| `armorType` | `TankArmorType` | 12 | ordinal |
| `armorDurability` | `int` | 15 | строка вида `"10%"`, берётся часть до `%` |
| `armorLossDurability` | `int` | 16 | то же, часть до `%` |
| `ammoType` | `TankAmmoType` | 16 | ordinal — **та же колонка 16**, см. [компромиссы](#tradeoffs) |
| `dropType` | `TankDropType` | 18 | ordinal; источник танка — см. ниже |
| `titleType` | `TankTitleType` | 20 | в коде сервера нигде не читается (сохранён при merge) |

**`TankDropType`** (ordinal в колонке 18): `ANY` = 0, `TRAIN` = 1, `COLLECTION_REWARD` = 2
(закомментирован `FACTORY` — TODO). `ANY` добавлен первым, поэтому индексы `TRAIN`/`COLLECTION_REWARD`
сместились на +1 — значения колонки в таблице баланса должны быть обновлены под новые ordinal-ы
(делает пользователь). Читается в `TrainUserComponent.receiveTank` и `AssemblyUserComponent.generateReward`
(см. [потребители](#consumers)): в поезде и в награде сборки выпадают только танки строго с `TRAIN`;
`ANY` там **не** выпадает.

Колонки 4, 6, 13, 14, 17, 19 не читаются (в локальном `balance.json` на их местах — текстовые
подписи, например название типа или код нации `"FR"`).

**Методы:**

- `TankData(...)` — конструктор, присваивает все 16 полей.
- `static TankData build(JSONArray array)` — разбор строки таблицы: из колонок 15 и 16
  вырезается процент (`split("%")[0]` → `Integer.parseInt`), затем создаётся объект; enum-ы — через
  `X.VALUES.valueOf(array.getInt(i))`. Любой отсутствующий индекс или нечисловое значение бросает
  `JSONException` и валит сборку всего баланса.
- `key()` — возвращает `id`.

<a id="class-airplanedata"></a>
## 6.2. `AirplaneData`

Модель самолёта из листа `Airplanes`. Реализует `KeyModel<Integer>`. Констант уровня нет — у
самолёта нет уровня.

| Поле | Тип | Колонка | Примечание |
|---|---|---|---|
| `id` | `Integer` | 0 | ключ (`key()`) |
| `name` | `String` | 1 | |
| `rank` | `Rank` | 2 | ordinal |
| `type` | `AirplaneType` | 3 | ordinal; допустимые позиции — `AirplaneType.TYPE_POSITION` |
| `country` | `Country` | 5 | ordinal |
| `hp` | `int` | 7 | |
| `armorType` | `AirplaneArmorType` | 8 | ordinal |
| `gunDamage` | `int` | 10 | |
| `gunType` | `AirplaneGunType` | 11 | ordinal |
| `gunRecharge` | `int` | 13 | |
| `bombDamage` | `int` | 14 | |
| `bombType` | `AirplaneBombType` | 15 | ordinal |
| `bombRecharge` | `int` | 17 | |
| `bombDelay` | `int` | 18 | |

Колонки 4, 6, 9, 12, 16 не читаются. Локальный `balance.json` содержит в строках `Airplanes`
ровно 19 колонок (0–18) — совпадает с тем, что читает код.

**Методы:**

- `AirplaneData(...)` — конструктор, присваивает все 14 полей.
- `static AirplaneData build(JSONArray array)` — позиционный разбор без преобразований строк;
  enum-ы через `VALUES.valueOf(getInt(i))`.
- `key()` — возвращает `id`.

<a id="diff"></a>
## 7. Общее и различия TankData / AirplaneData

**Общее:** одинаковый контракт (`KeyModel<Integer>` + `static build(JSONArray)` + `key()`), одинаковые
первые колонки (`id`=0, `name`=1, `rank`=2, `type`=3, `country`=5, `hp`=7), одинаковый путь загрузки
и индексации в `Balance` (`getXData(id)`, `getXs(rank)`, `getXsId()`, `xIsAvailable(id)`),
одинаковая связь с `BagItem` (`createNew(data, isTemplate)` берёт только `data.id`; `data()` ищет
запись в `Balance` по id), одинаковые поля в `apiResponse()` предмета (`name`, `type`, `country`,
`rank` — ordinal-ы). Список допустимых рангов у обоих в коде задан одинаково (`Rank.TANKS` и
`Rank.AIRPLANES` — I…XX; звёзды `TANK_STARS`/`AIRPLANE_STARS` — I…X).

**Различия:**

| Аспект | `TankData` | `AirplaneData` |
|---|---|---|
| Уровень | `MIN_LEVEL`/`MAX_LEVEL`; `Tank.level` | нет уровня |
| Атака | одно орудие: `damage`, `recharge`, `penetration`, `ammoType` | пушка (`gunDamage`/`gunType`/`gunRecharge`) + бомбы (`bombDamage`/`bombType`/`bombRecharge`/`bombDelay`) |
| Броня | `armor`, `armorType`, `armorDurability`, `armorLossDurability` | только `armorType` |
| Парсинг | проценты из строк (кол. 15–16) | только `getInt`/`getString` |
| Неиспользуемые поля | `titleType` | нет |
| Пересчёт в Params | `hp`/`damage`: +1% за уровень выше 1, затем множитель звёзд | `hp`/`gunDamage`/`bombDamage`: только множитель звёзд |

<a id="consumers"></a>
## 8. Кто использует данные

Доступ всегда через `Balance.INSTANCE`:

- **`Tank` / `Airplane`** (`BagItem`) — `createNew(data|id, isTemplate)`, `data()`, `apiResponse()`
  (`name`, `type`, `country`, `rank`).
- **`TankParams.recalculate` / `AirplaneParams.recalculate`** — копируют боевые поля и применяют
  уровень/звёзды (`Balance.getStarsMultiplier`); это то, что реально уходит на клиент в `params` и
  в `power`.
- **Выдача новых юнитов по рангу** (`getTanks(rank)` / `getAirplanes(rank)` + случайный выбор):
  `TrainUserComponent.receiveTank` (шанс ранга — `Balance.getSummonRankChance(level, rank)` из общего листа
  `SummonRankChances`; туториальной ветки нет; после ролла ранга список `getTanks(droppedRank)` фильтруется циклом в новый `ArrayList` —
  только `dropType == TankDropType.TRAIN`, затем случайный выбор; `Balance` не менялся, отдельного
  индекса по `dropType` нет — решение пользователя),
  `AssemblyUserComponent.generateReward` (фильтр по `type` минимального ранга и `dropType == TRAIN`;
  пустой список — награда не генерируется, ранний `return`), `MilitaryBaseAviationFactory` (самолёт по рангу, ссылкой; `AerodromeUserComponent` по рангу больше не выдаёт).
- **Размещение по позициям** — `HangarUserComponent`, `AerodromeUserComponent`,
  `BattleDataFactory` берут `data.type` → `TankType/AirplaneType.TYPE_POSITION`.
- **Бот-команды** — `BattleDataFactory` (ранг/уровень/звёзды от уровня кампании; константы туториальных
  танков из `TutorialData` удалены).
- **Бой** — `UnitTank`/`UnitAirplane` сериализуют `data().id` и `data().rank`.
- **Достижения** — `CampaignPage` по `tankId`/`airplaneId` из запроса берёт `country` и `type` для
  `DestroyTankAchievement`/`DestroyAirplaneAchievement`.
- **Кодекс** — `CodexPage.actionTanks/actionAirplanes` перебирают все модели по рангам
  (`Rank.TANKS`/`Rank.AIRPLANES`) и отдают шаблонные предметы (`isTemplate=true`).
- **DevTools** — `DevToolsPage` перебирает `getTanksId()`.

<a id="tradeoffs"></a>
## 9. Принятые уязвимости и компромиссы

Ниже — наблюдения по коду; п. 1–6 — без принятых решений, п. 7 — принят пользователем осознанно.

1. **Колонка 16 в `TankData.build` читается дважды**: как `armorLossDurability` (строка, срез до
   `%`) и как `ammoType` (ordinal). Намеренно это или смещение индекса — из кода не определить.
   В локальном `balance.json` в колонке 16 лежит число без `%` (ordinal снаряда, рядом в колонке 17 —
   его текстовое название), а процент есть в колонке 14 (`"50%"`, `"150%"`), которую код не читает.
   Значит, `armorLossDurability` фактически получает ordinal снаряда — похоже на смещение индекса,
   но это не подтверждено (риск).
2. **Закоммиченный `balance.json` — фактический источник данных по умолчанию.** Импорт выключен
   (`app.balanceShouldImport=false`), поэтому на старте читается этот файл. Сверено 2026-10-13: все
   349 строк `Tanks` имеют 22 колонки (0–21), все 306 строк `Airplanes` — 19 (0–18), так что индексы
   `TankData`/`AirplaneData`, включая 18 и 20, на файле читаются. Колонка 18 у танков уже в новых
   ordinal-ах `TankDropType`: `1` всегда стоит рядом с подписью `TRAIN`, `2` — с `COLLECTION_REWARD`.
   Риск: соответствие Google-таблицы этому файлу не проверялось. Если импорт включить через
   `-appPropFile`, таблица перезапишет файл, и расхождение колонок там уронит сборку баланса.
3. **`titleType`** парсится, но нигде на сервере не используется. (`dropType` читается в
   `TrainUserComponent.receiveTank` и `AssemblyUserComponent.generateReward`, см. [потребители](#consumers).)
4. **Нет валидации строк**: одна битая строка любого из листов роняет сборку всего `Balance`.
5. **`getTanks(rank)`/`getAirplanes(rank)` возвращают `null`**, если в балансе нет моделей такого
   ранга (`Map.get` без default), а вызывающие (`TrainUserComponent`, `MilitaryBaseAviationFactory`,
   `CodexPage`, `BattleDataFactory`) проверку на `null` не делают.
6. **`CampaignPage` доверяет `tankId`/`airplaneId` клиента** (`if (true) // TODO` — нет проверки,
   что юнит был на поле боя); при неизвестном id `getTankData` вернёт `null` → NPE.
7. **Пустой список танков `TRAIN` для выпавшего ранга**: если в балансе для `droppedRank` нет ни
   одного танка с `dropType == TRAIN`, отфильтрованный `tanksList` в `TrainUserComponent.receiveTank`
   пуст и `RandomJdk.nextInt(0, 0)`/`get` упадёт. Намеренно не обрабатывается — баланс считается
   корректным (решение пользователя).

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от корня репозитория `server`. Полнота проверена `grep -w` по `TankData`/`AirplaneData` по всему
репозиторию (вне `game/src/main/java` вхождений нет); дополнительно учтены места, где данные читаются
через `Balance`/`data()` без упоминания имени класса.

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/bag/tank/data/TankData.java` | модель танка из листа `Tanks`, разбор строки, `MIN_LEVEL`/`MAX_LEVEL` |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/data/AirplaneData.java` | модель самолёта из листа `Airplanes`, разбор строки |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

Загрузка и общий реестр:

| Файл | Роль |
|---|---|
| `game/src/main/resources/balance.json` | файл баланса: таблицы `Tanks` и `Airplanes` (источник данных по умолчанию); листы теперь `UserLevel(new)`, `SummonUpgrade`, `SummonRankChances`, `SummonStarsRankChances`, `MB*` |
| `game/src/main/java/com/linkedgames/game/balance/Balance.java` | сборка `Map` по id (`null` пропускается, для `TankData` сейчас не возникает), индексы по рангу, `getTankData`/`getAirplaneData`/`getTanks(rank)`/`getTanksId` |
| `game/src/main/java/com/linkedgames/game/balance/BalanceImporter.java` | импорт листов `Tanks`/`Airplanes` из Google-таблицы и чтение файла баланса |
| `game/src/main/java/com/linkedgames/game/balance/KeyModel.java` | контракт `key()`, по которому `Balance.mapping` строит `Map` |
| `game/src/main/java/com/linkedgames/game/Globals.java` | запуск импорта и сборки баланса на старте |
| `game/src/main/resources/app.properties` | `app.balanceShouldImport`, `app.balanceFilePath` |

Зависимости — типы полей справочника из других областей:

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankType.java` | зависимость: тип танка, `TYPE_POSITION` |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankArmorType.java` | зависимость: тип брони танка |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankAmmoType.java` | зависимость: тип снаряда танка |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankDropType.java` | зависимость: источник выпадения танка (`ANY`/`TRAIN`/`COLLECTION_REWARD`) |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankTitleType.java` | зависимость: тип титула танка, на сервере не читается |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneType.java` | зависимость: тип самолёта, `TYPE_POSITION` |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneArmorType.java` | зависимость: тип брони самолёта |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneGunType.java` | зависимость: тип пушки самолёта |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneBombType.java` | зависимость: тип бомб самолёта |
| `game/src/main/java/com/linkedgames/game/model/Rank.java` | зависимость: ранг модели, списки `Rank.TANKS`/`Rank.AIRPLANES` |
| `game/src/main/java/com/linkedgames/game/model/Country.java` | зависимость: нация модели |

Потребители:

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/bag/tank/Tank.java` | предмет сумки, хранит id модели, `data()`, `apiResponse()` |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/Airplane.java` | то же для самолёта |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankParams.java` | пересчёт боевых полей с учётом уровня и звёзд |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneParams.java` | пересчёт боевых полей с учётом звёзд |
| `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` | выдача танка по рангу с фильтром `dropType == TRAIN`, clamp уровня |
| `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` | генерация награды сборки (`type`, `dropType`), clamp уровня |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/AerodromeUserComponent.java` | размещение самолёта по `type` |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseAviationFactory.java` | выдача самолёта по рангу (ссылкой, военная база) |
| `game/src/main/java/com/linkedgames/game/model/hangar/HangarUserComponent.java` | размещение танка по `data().type` |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleDataFactory.java` | бот-команды, позиции, clamp уровня |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitTank.java` | сериализация `data().id`/`rank` в бою |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitAirplane.java` | то же для самолёта |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleBalance.java` | боевые модификаторы по `TankArmorType`/`TankAmmoType` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` | `country`/`type` уничтоженного юнита для достижений |
| `game/src/main/java/com/linkedgames/game/model/achievements/AchievementFactory.java` | создание достижений с фильтром по `TankType`/`AirplaneType` |
| `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyTankAchievement.java` | прогресс по `type`/`country` уничтоженного танка |
| `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyAirplaneAchievement.java` | то же для самолёта |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CodexPage.java` | перечень всех моделей по рангам для кодекса |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` | dev-инструмент: перебор `getTanksId()` |
