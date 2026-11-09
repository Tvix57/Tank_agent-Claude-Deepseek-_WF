# Сборка (Assembly) — `AssemblyUserComponent`

ГДД: [/workspace/client/.claude/docs/game-design/assembly-gdd.md](/workspace/client/.claude/docs/game-design/assembly-gdd.md)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-09-28;
> актуализирован 2026-10-19 после merge `origin/amnesia/fix` (диф `AssemblyUserComponent` и сверка
> зависимостей). Содержимое балансовых таблиц (`Balance`: шансы призыва, списки танков) не проверялось.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация по классам](#class-nav)
6. Классы
   - [`AssemblyUserComponent`](#class-assemblyusercomponent)
   - [`AssemblyNeedSchemePartsData`](#class-assemblyneedschemepartsdata)
   - [`AssemblySchemeParts`](#class-assemblyschemeparts)
   - [`AssemblySchemePartsType`](#class-assemblyschemepartstype)
   - [`AssemblyPage`](#class-assemblypage)
7. [Жизненный цикл награды](#lifecycle)
8. [Персистентность](#persistence)
9. [Связи с другими компонентами](#relations)
10. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
11. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

"Сборка" — механика, в которой игрок собирает танк из частей схемы. У игрока в каждый момент есть
ровно одна **заранее сгенерированная награда** (`reward` — сейчас на практике всегда `Tank`), и
известны две цены:

- `needSchemeParts` — сколько частей схемы нужно, чтобы забрать или отклонить награду (после
  генерации всегда `30`, см. [`MAX_SCHEME_PARTS_COUNT`](#class-assemblyneedschemepartsdata));
- `needSilverCoins` — сколько серебра стоит одна покупка пачки частей схемы.

Бизнес-логика — в ГДД [`assembly-gdd.md`](/workspace/client/.claude/docs/game-design/assembly-gdd.md).

Игровой цикл:

1. Игрок покупает части схемы за серебро (`buySchemeParts`) — получает случайную пачку от 1 до 10
   частей танковой схемы (цвет пачки выпадает по весам; ГДД [#gdd-blueprint-quality](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-blueprint-quality)).
2. Накопив `needSchemeParts` частей, игрок либо **забирает** награду (`takeReward`: танк уходит в
   ангар/сумку), либо **отклоняет** её (`rejectReward`: части всё равно списываются). В обоих случаях
   сразу генерируется новая награда (ГДД [#gdd-take](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-take), [#gdd-build-points](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-build-points)).
3. Генерация выбирает танк на ранг выше самого слабого танка игрока (с ограничением по прокачке
   поезда), того же `TankType`, что у самого слабого танка, и только с `dropType == TRAIN`. Уровень
   танка — по уровню игрока, звёзды — по таблицам шансов поезда (ГДД [#gdd-reward-choice](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-reward-choice)).
4. Цена пачки частей (`needSilverCoins`) растёт с каждой генерацией награды того же ранга (5 ступеней,
   каждая ×2, дальше — потолок; ГДД [#gdd-blueprint-price](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-blueprint-price)).

Сгенерированный танк сразу попадает в кодекс (ещё до того, как игрок его забрал).

<a id="references"></a>
## 2. Референсы

- `TrainUserComponent.receiveTank` — та же схема выбора звёзд (`Balance.getSummonStarsRankChance`
  + `DropUtils.RollDrop` + `TrainSummonData.getRandomStars`) и та же таблица шансов рангов
  (`Balance.getSummonRankChance`), на которую опирается [`tankRankIsAvailable`](#m-tankrankisavailable).
  После merge листы баланса поезда/аэродрома заменены общими `SummonRankChances`/`SummonStarsRankChances`
  (`Balance` ключует по уровню поезда); сама область Summon здесь не описывается.
- Фильтр `type`/`dropType == TRAIN` описан со стороны данных в
  [`tank-airplane-data-architecture.md#consumers`](tank-airplane-data-architecture.md#consumers) —
  здесь не дублируется.

<a id="patterns"></a>
## 3. Паттерны

- **`UserChildComponent`** — компонент хранится полями внутри общего документа `User` (ключ
  `"Assembly"`), ленивый геттер `User.getAssemblyUserComponent()`.
- **Персистентность "1a + 1b"** по классификации `server-developer-db-persistence`
  (`.claude/agents/developers/server-developer-db-persistence.md`): примитивы и вручную сплющенная карта
  `tankBuildCounter` (1a) + вложенный `Item` через `dbToData()`/`ItemFactory.newFromDocument` (1b).
  Подробно — [Персистентность](#persistence).
- **Статические балансовые таблицы в коде** (`AssemblyNeedSchemePartsData`) — не из `Balance`/Google
  Sheets, а захардкожены.
- **Взвешенный случайный выбор** — два варианта: через проценты с вычитанием
  (`AssemblyNeedSchemePartsData.getSchemeParts`) и через общий `DropUtils.RollDrop` (звёзды).
- **`APIResponseStd`** — сериализация в JSON для клиента (`apiResponse()`).

<a id="class-list"></a>
## 4. Список классов

Код задачи не менялся; ниже — все классы области (существующие).

| Класс | Путь |
|---|---|
| `AssemblyUserComponent` | `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` |
| `AssemblyNeedSchemePartsData` | `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblyNeedSchemePartsData.java` |
| `AssemblySchemeParts` | `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblySchemeParts.java` |
| `AssemblySchemePartsType` | `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblySchemePartsType.java` |
| `AssemblyPage` | `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AssemblyPage.java` |

Точки подключения вне пакета (не часть области, только вызывают её): `User` (поле `assembly`, геттер,
загрузка, `modifyReceiver`), `WSRouter` (маршрут `/ingame/assembly`), `HomePage` (кладёт
`assembly.apiResponse()` в payload главного экрана).

<a id="class-nav"></a>
## 5. Навигация по классам

- [`AssemblyUserComponent`](#class-assemblyusercomponent): [поля](#assembly-fields) ·
  [`generateReward`](#m-generatereward) · [`tankRankIsAvailable`](#m-tankrankisavailable) ·
  [`rejectReward`](#m-rejectreward) · [`buySchemeParts`](#m-buyschemeparts) ·
  [`takeReward`](#m-takereward) · [`afterDBMappingBuild`](#m-afterdbmappingbuild) ·
  [`dbMappingBuild`](#m-dbmappingbuild) · [`apiResponse`](#m-apiresponse) · [прочие](#assembly-trivial)
- [`AssemblyNeedSchemePartsData`](#class-assemblyneedschemepartsdata): [`getSchemeParts`](#m-getschemeparts) ·
  [`getTankSchemePartsPrice`](#m-gettankschemepartsprice)
- [`AssemblySchemeParts`](#class-assemblyschemeparts)
- [`AssemblySchemePartsType`](#class-assemblyschemepartstype)
- [`AssemblyPage`](#class-assemblypage): [маршруты](#page-routes)

---

<a id="class-assemblyusercomponent"></a>
## 6.1. `AssemblyUserComponent`

`extends UserChildComponent implements APIResponseStd`. Состояние сборки одного игрока и вся
бизнес-логика: генерация награды, покупка частей схемы, выдача/отклонение награды.

<a id="assembly-fields"></a>
### Поля

| Поле | Тип | Смысл |
|---|---|---|
| `TANK_NEED_SILVER_COINS_INCREASE_LIMIT` | `static final int = 5` | Сколько раз максимум растёт цена пачки частей для одного ранга (= длина списка цен в `AssemblyNeedSchemePartsData`). |
| `reward` | `Item` | Текущая награда. Генерируется только `Tank`; ветки `Airplane` в коде есть, но генерации самолёта нет. |
| `needSilverCoins` | `int` | Цена одной покупки пачки частей схемы. |
| `needSchemeParts` | `int` | Сколько частей схемы нужно для `take`/`reject`. |
| `tankBuildCounter` | `Map<Integer, Integer>` | Ключ — `Rank.ordinal()` целевого ранга, значение — сколько раз генерировалась награда этого ранга (с потолком 5). |

<a id="m-generatereward"></a>
### `private void generateReward()`

Генерирует новую награду-танк и пересчитывает цены. Шаги:

1. **Самый слабый танк игрока.** Стартовое значение — последний ранг `Rank.TANKS` (`XX`; после merge список идёт до `XX`) и тип
   `TankType.LIGHT`. Если в сумке нет танков — ранг `I`. Иначе перебирает `bag.getTanks()` и при
   строго меньшем ранге запоминает ранг и `type` этого танка.
2. **Целевой ранг** = индекс минимального в `Rank.TANKS` + 1; если выходит за список — остаётся
   последний. Если [`tankRankIsAvailable`](#m-tankrankisavailable) для него `false` — индекс
   уменьшается на 1 (один раз, без повторной проверки).
3. **Кандидаты** — `Balance.getTanks(targetRank)`, отфильтрованные по `type == minTankType` и
   `dropType == TRAIN` (фильтр `dropType` стоит в самой сборке, `AssemblyUserComponent`; см. [`tank-airplane-data-architecture.md#consumers`](tank-airplane-data-architecture.md#consumers)).
   Пустой список — **выход без изменений** (старая `reward` остаётся, см. [компромиссы](#tradeoffs)).
4. Случайный кандидат (`RandomJdk.nextInt(0, size)`, равномерно).
5. **Звёзды:** ранг звёзд — `DropUtils.RollDrop` по `Rank.TANK_STARS` с весами
   `Balance.getSummonStarsRankChance(trainLevel, starsRank.ordinal())`; количество —
   `TrainSummonData.getRandomStars()`.
6. `Tank.createNew(id, false)`, уровень = уровень игрока, зажатый в `[TankData.MIN_LEVEL,
   TankData.MAX_LEVEL]`, `setStars`, `recalculateParams`.
7. `reward = tank`, `changedField(REWARD_FIELD, reward.dbToData())`.
8. `codex.add(tank.createCodexEntry())` — танк попадает в кодекс сразу при генерации (ГДД [#gdd-reward-choice](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-reward-choice)).
9. **Цена:** `buildCount = min(tankBuildCounter[targetRank], 4)`;
   `needSilverCoins = AssemblyNeedSchemePartsData.getTankSchemePartsPrice(targetRank, buildCount)`;
   `needSchemeParts = 30`; `tankBuildCounter[targetRank] = buildCount + 1`. Все три поля сохраняются
   `changedField`. ГДД [#gdd-blueprint-price](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-blueprint-price), [#gdd-build-points](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-build-points).

Вызывается из `rejectReward`, `takeReward` (при успехе) и `afterDBMappingBuild` (если награды нет).

<a id="m-tankrankisavailable"></a>
### `public boolean tankRankIsAvailable(Rank rank)`

Правило "прокачка поезда +1 ранг": ранг доступен, если у него ненулевой шанс выпадения в поезде на
текущем уровне поезда (`Balance.getSummonRankChance(trainLevel, rank.ordinal())`), ЛИБО
ненулевой шанс у предыдущего ранга (`rank.ordinal() - 1`). Для `Rank.I` предыдущий — `NONE` (ordinal 0). ГДД [#gdd-reward-choice](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-reward-choice).

<a id="m-rejectreward"></a>
### `public boolean rejectReward()`

Количество частей в сумке читается как `long` (`getResourceCount`), сравнивается с `needSchemeParts`.
Определяет ресурс частей по типу `reward` (`Tank` → `RESOURCE_TANK_SCHEME_PARTS`, `Airplane` →
`RESOURCE_AIRPLANE_SCHEME_PARTS`); награды нет — `false`. Частей меньше `needSchemeParts` — `false`.
Иначе списывает `needSchemeParts`, вызывает `generateReward()`, `true`. Отклонение стоит столько же
частей, сколько получение. ГДД [#gdd-take](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-take).

<a id="m-buyschemeparts"></a>
### `public JSONObject buySchemeParts()`

Роллит пачку ([`getSchemeParts`](#m-getschemeparts)); серебра меньше `needSilverCoins` — `null`.
Иначе списывает `needSilverCoins` серебра и начисляет `parts.count` частей **всегда танковой** схемы
(`RESOURCE_TANK_SCHEME_PARTS`, независимо от типа награды). Возвращает `parts.apiResponse()`
(`{type, count}`). Цена после покупки не меняется — она пересчитывается только в `generateReward`. ГДД [#gdd-blueprint-quality](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-blueprint-quality).

<a id="m-takereward"></a>
### `public JSONObject takeReward()`

Диспетчер по типу `reward`:
- `takeTankReward()` — проверяет и списывает `needSchemeParts` танковых частей,
  `hangar.addTank((Tank) reward)` (танк добавляется в сумку, ставится в ангар, при наличии
  заменяемого танка того же типа тот теряет 1 `count` — логика `HangarUserComponent.addTank`),
  возвращает `reward.apiResponse()`;
- `takeAirplaneReward()` — то же с самолётными частями и `aerodrome.addAirplane`.

Если результат не `null` — `generateReward()`. Иначе `null` (не хватает частей или нет награды). ГДД [#gdd-take](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-take).

<a id="m-afterdbmappingbuild"></a>
### `public void afterDBMappingBuild()`

Если после загрузки `reward == null` — `generateReward()`. Вызывается `User.dbMappingBuild` **всегда**
(и когда поля `"Assembly"` в документе нет), сразу после `assembly.dbMappingBuild`. Важно: это
происходит до загрузки сумки и кодекса (см. [компромиссы](#tradeoffs), п.1).

<a id="m-dbmappingbuild"></a>
### `public void dbMappingBuild(Document document)`

Читает `nsc`, `needSchemeParts` (по умолчанию 0), `rw` (если не пустой — `ItemFactory.newFromDocument`;
при `null` от фабрики награда не присваивается, иначе `item.dbMappingBuild`), `tbco` (ключи-строки → `Integer.parseInt`, значения кастуются в `Integer`).

<a id="m-apiresponse"></a>
### `public JSONObject apiResponse()`

`{ silverCoins, needSilverCoins, schemeParts, schemePartsId, needSchemeParts, reward? }`:
`schemePartsId` — `5` (танк) / `6` (самолёт) / `0` (награды нет), `schemeParts` — количество этого
ресурса в сумке; `reward` — только если не `null`.

<a id="assembly-trivial"></a>
### Прочие методы (тривиальные)

- `AssemblyUserComponent(User, String)` — конструктор, имя компонента `"Assembly"` задаёт `User`.
- `modifyReceiver(UnitPFBuilder<Object>)` — пустой (сообщений актора компонент не обрабатывает).
- `canCreatePlane()` / `canCreateTank()` — хватает ли самолётных/танковых частей на `needSchemeParts`;
  в коде нигде не вызываются.
- `getTank()` — `reward`, если это `Tank`, иначе `null` (используется `AssemblyPage /compare`).
- `private dbTankBuildCounterChanged()` — сплющивает `tankBuildCounter` в `Document` (ключ —
  `String`) и пишет одним `changedField(TBCO)`.
- `DBFields` — `static class` с приватными константами ключей (см. [Персистентность](#persistence)).

---

<a id="class-assemblyneedschemepartsdata"></a>
## 6.2. `AssemblyNeedSchemePartsData`

Захардкоженные балансовые таблицы сборки + экземпляр-запись `(rank, value)`.

- `MAX_SCHEME_PARTS_COUNT = 30` — `needSchemeParts` после каждой генерации.
- `LIST` — пачки частей схемы: `RED` 5% ×10, `YELLOW` 10% ×7, `PURPLE` 15% ×5, `BLUE` 20% ×3,
  `GREEN` 50% ×1 (сумма шансов 100). `public static`, мутабельный `ArrayList`.
- `TANK_PARTS` (private) — `Rank.I..X` → 5 цен (серебро) за пачку; каждая следующая ×2.
  Базовые: I 10, II 25, III 75, IV 150, V 400, VI 1000, VII 2000, VIII 5000, IX 10000, X 20000.
- `rank`, `value` — `public final` поля записи; конструктор тривиален.

<a id="m-getschemeparts"></a>
### `public static AssemblySchemeParts getSchemeParts()`

`RandomJdk.nextPercents()` (∈ [0, 100)) и последовательное вычитание `dropChance` по `LIST`; первая
пачка, на которой остаток `<= 0`, — результат. Страховочный возврат — последний элемент (`GREEN`).

<a id="m-gettankschemepartsprice"></a>
### `public static int getTankSchemePartsPrice(Rank rank, int num)`

Цена пачки для ранга `rank` на `num`-й генерации. Ранга нет в таблице — берётся таблица `X` (ранги `XI..XX` в `TANK_PARTS` не заведены, цены для них = `X`).
`num` вне `[0, 5)` — максимальная (последняя) цена. ГДД [#gdd-blueprint-price](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-blueprint-price).

<a id="class-assemblyschemeparts"></a>
## 6.3. `AssemblySchemeParts`

`implements APIResponseStd`. Неизменяемое описание пачки: `type` (`AssemblySchemePartsType`),
`dropChance` (`Double`, проценты), `count` (сколько частей даёт). `apiResponse()` →
`{ type: type.getType(), count }`.

<a id="class-assemblyschemepartstype"></a>
## 6.4. `AssemblySchemePartsType`

Enum цвета пачки: `NONE("")`, `GREEN`, `BLUE`, `PURPLE`, `YELLOW`, `RED` (строки в нижнем регистре).
- `getType()` — строковое значение для клиента.
- `fromString(String)` — поиск по строке, иначе `NONE`; объявлен **нестатическим** (`public final`),
  в коде не вызывается.

<a id="class-assemblypage"></a>
## 6.5. `AssemblyPage`

`extends AuthorizedUserPage`, маршрут `/ingame/assembly` (`WSRouter`). Тонкий слой: вызывает методы
компонента и формирует ответ.

<a id="page-routes"></a>
### Маршруты

| Маршрут | Метод компонента | Успех (payload) | Ошибка |
|---|---|---|---|
| `""` | `apiResponse()` | `assembly` | — |
| `/buySchemeParts` | `buySchemeParts()` | `reward` (пачка `{type,count}`), `assembly` | `null` → ошибка `"Buy scheme parts err" / "Not enougth money"` |
| `/compare` | `getTank()` + `hangar.getReplaceableTank(tank)` | `receivedTank`, `replaceableTank` (или `JSONObject.NULL`) | награда не танк → пустая ошибка |
| `/take` | `takeReward()` | `reward` (танк), `assembly` (уже с новой наградой) | `null` → пустая ошибка |
| `/reject` | `rejectReward()` | `assembly` | `false` → пустая ошибка |

Push-событий область не шлёт. `HangarUserComponent.addTank` эмитит `UserEmitterId.HANGAR_UPDATE` — внутреннее событие `UserEmitter` (слушает `BattlefieldUserComponent`), клиенту оно не приходит; клиентский `HANGAR_UPDATE` после `/take` шлёт само окно сборки.

---

<a id="lifecycle"></a>
## 7. Жизненный цикл награды

```
загрузка User ──► dbMappingBuild("Assembly") ──► afterDBMappingBuild: reward == null? ──► generateReward
                                                                                              │
/buySchemeParts: −needSilverCoins серебра, +1..10 танковых частей (цена не меняется)          │
/take:   −30 частей, танк → hangar/bag ──────────────────────────────────────────────► generateReward
/reject: −30 частей ──────────────────────────────────────────────────────────────────► generateReward
```

Каждая генерация увеличивает `tankBuildCounter[targetRank]` (до 5) и тем самым цену следующей пачки
для этого ранга — независимо от того, забрал игрок награду или отклонил.

<a id="persistence"></a>
## 8. Персистентность

Всё хранится в документе `User` под ключом `"Assembly"` (`User.DBFields.P_ASSEMBLY_FIELD`), через
унаследованный `changedField`:

| Ключ | Поле | Вид |
|---|---|---|
| `rw` | `reward` | вложенный документ `Item.dbToData()` (1b) |
| `nsc` | `needSilverCoins` | `int` (1a) |
| `needSchemeParts` | `needSchemeParts` | `int` (1a) |
| `tbco` | `tankBuildCounter` | `Document { "<rankOrdinal>": count }` (1a, ручное сплющивание) |

Пишутся только в `generateReward`. Ресурсы (серебро, части схемы) хранятся в сумке
(`BagUserComponent`), не здесь. Порядок загрузки — [компромиссы](#tradeoffs), п.1.

<a id="relations"></a>
## 9. Связи с другими компонентами

- **Bag** — чтение танков (`getTanks`), чтение/изменение ресурсов `RESOURCE_SILVER_COINS` (1),
  `RESOURCE_TANK_SCHEME_PARTS` (5), `RESOURCE_AIRPLANE_SCHEME_PARTS` (6). В Java-коде вне области эти
  ресурсы частей схемы никто не начисляет — единственный источник в коде `buySchemeParts` (только
  танковые); выдача через балансовые данные/дроп не проверялась.
- **Train** — `getLevel()` для `tankRankIsAvailable` и шансов звёзд; таблицы поезда из `Balance`;
  `TrainSummonData.getRandomStars()`.
- **Hangar / Aerodrome** — выдача награды (`addTank`, `addAirplane`), `/compare` через
  `getReplaceableTank`.
- **Codex** — `add(tank.createCodexEntry())` при каждой генерации. `CodexUserComponent.add` сам
  решает, заменить ли запись (по `power`).
- **Balance / TankData** — `getTanks(rank)`, фильтр `type`/`dropType` (см.
  [`tank-airplane-data-architecture.md#consumers`](tank-airplane-data-architecture.md#consumers)).
- **User** — `getLevel()` для уровня танка; `User.dbMappingBuild` вызывает `dbMappingBuild`/
  `afterDBMappingBuild`; `HomePage` отдаёт `assembly.apiResponse()`.
- **Коллекции, военная база, кланы** — прямых связей нет. После merge `ActorInitializationTask` грузит
  ещё и коллекции (до кодекса), а при пустой сумке — `MilitaryBaseUserComponent.initStarter`; `User`
  получил компоненты коллекций/кланов/военной базы; на сборку это не влияет.

<a id="tradeoffs"></a>
## 10. Принятые уязвимости, компромиссы и подозрительные места

Причины решений в коде не зафиксированы; ниже — наблюдения по коду, без оценки "баг/задумано"
(решение — за пользователем).

> **Отложено (решение пользователя, 2026-09-28):** пункты ниже сейчас не исправляются. При любой новой
> задаче, затрагивающей `AssemblyUserComponent`/`AssemblyPage`, — предложить пользователю включить их
> исправление в задачу (приоритет: п.2, затем п.1), предварительно сверив с актуальным кодом.

1. **Генерация при загрузке видит пустую сумку и незагруженный кодекс.** `afterDBMappingBuild`
   вызывается внутри `User.dbMappingBuild`, а сумка и кодекс грузятся позже
   (`ActorInitializationTask`, шаг `buildComponents`: сумка → ... → коллекции → кодекс). Если `reward == null` (новый игрок или пустой
   `rw`), `generateReward` считает, что танков нет (→ целевой ранг `II`/`I`, тип `LIGHT`), а запись
   кодекса добавляется до `codex.dbMappingChildBuild`.
   по ГДД (#gdd-reward-choice, решение пользователя 2026-10-15) — расхождение, исправление отложено.
2. **Пустой список кандидатов → старая награда остаётся.** После `take` уже выданный `Tank`-объект
   остаётся в `reward` и может быть выдан повторно следующим `/take`; после `reject` части списаны, а
   награда не сменилась.
   по ГДД (#gdd-take, решение пользователя 2026-10-15) — расхождение, исправление отложено.
3. **`minTankType` при всех танках ранга `X`** остаётся `LIGHT` (обновляется только при строго
   меньшем ранге), т.е. тип не берётся из реального танка.
   по ГДД (#gdd-reward-choice, решение пользователя 2026-10-15) — расхождение, исправление отложено.
4. **Одна попытка понижения ранга** в шаге 2 `generateReward` — после декремента доступность не
   перепроверяется. Проверка `targetTankRank == null` недостижима (`ImmutableList` не содержит `null`).
5. **`Balance.getTanks(rank)` может вернуть `null`** (прямой `map.get`) — NPE в цикле; при нулевой сумме
   шансов звёзд для уровня поезда `DropUtils.RollDrop` вызывает `nextIntInclusive(1, 0)` / может вернуть
   `null` (→ NPE на `.getItem()`).
6. **Кодекс пополняется при генерации**, а не при получении — отклонённые танки тоже попадают в кодекс.
   по ГДД (#gdd-reward-choice, 2026-10-15) это правило, не дефект.
7. **`buySchemeParts` всегда даёт танковые части**, даже если награда — самолёт; самолётная награда
   не генерируется вовсе (ветки `Airplane` — фактически мёртвый код, как и `canCreatePlane/Tank`,
   `AssemblySchemePartsType.fromString`, `NONE`).
8. **Счётчик цены растёт при каждой генерации**, включая первую при загрузке и отклонения; при
   `needSilverCoins == 0` покупка бесплатна — возможно, если успешной генерации ещё не было (все
   попытки вышли по пустому списку кандидатов, п.2).
   по ГДД (#gdd-blueprint-price, решение пользователя 2026-10-15) — расхождение, исправление отложено.
9. **Комментарий у `TANK_NEED_SILVER_COINS_INCREASE_LIMIT`** ссылается на несуществующий
   `AssemblyNeedSilverCoinsData`; фактическая таблица — `AssemblyNeedSchemePartsData.TANK_PARTS`
   (и названия "SchemeParts price" описывают цену в серебре).
10. **`AssemblyNeedSchemePartsData.LIST`** — `public static` мутабельный `ArrayList` (может быть
    изменён извне).
11. **`/compare`** возвращает пустую ошибку, если награда — не танк; тексты ошибок есть только у
    `/buySchemeParts` (с опечаткой "enougth").
    по ГДД (#gdd-take, решение пользователя 2026-10-15) — расхождение, исправление отложено.
12. **Нет синхронизации балансов с Google-таблицами** — цены и пачки захардкожены (`AssemblyNeedSchemePartsData`).
13. **`buySchemeParts` не запрещает покупку при 30+ очках** (ГДД #gdd-build-points) — ГДД, отложено 2026-10-15.
14. **Нет компенсации 10 серебра за заменённый танк** — когда новый танк забран «ПРОДАЖЕЙ» и заменённый уходит из команды (`/take`, `HangarUserComponent.addTank`) (ГДД #gdd-take; решение пользователя: как в поезде) — ГДД, отложено 2026-10-15.

<a id="file-map"></a>
## 11. Карта файлов компонента

Миграций, ресурсных файлов и клиентских файлов у области нет (проверено `grep` по репозиторию).

### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` | компонент: награда, покупка частей, выдача/отклонение, персистентность |
| `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblyNeedSchemePartsData.java` | захардкоженные таблицы цен и количества частей схемы |
| `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblySchemeParts.java` | пачка частей схемы: цвет-тип, шанс выпадения, количество |
| `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblySchemePartsType.java` | цвет (тип) пачки частей схемы: green/blue/purple/yellow/red |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AssemblyPage.java` | WS-страница `/ingame/assembly` |

### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | поле `assembly`, геттер, `dbMappingBuild`/`afterDBMappingBuild`, `modifyReceiver`, ключ `P_ASSEMBLY_FIELD` |
| `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` | регистрация маршрута `/ingame/assembly` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/HomePage.java` | кладёт `assembly.apiResponse()` в payload главного экрана |
| `game/src/main/java/com/linkedgames/game/model/bag/BagUserComponent.java` | ресурсы 1/5/6 (серебро, части схемы), список танков |
| `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` | уровень поезда для доступности ранга и шансов |
| `game/src/main/java/com/linkedgames/game/model/Rank.java` | `Rank.TANKS` (до `XX`), `Rank.TANK_STARS` |
| `game/src/main/java/com/linkedgames/game/model/item/ItemFactory.java` | `newFromDocument` для `rw` (может вернуть `null`) |
| `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorInitializationTask.java` | порядок загрузки сумки/коллекций/кодекса относительно `afterDBMappingBuild` |
| `game/src/main/java/com/linkedgames/game/model/hangar/HangarUserComponent.java` | `addTank` при выдаче награды |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/AerodromeUserComponent.java` | выдача самолёта-награды |
| `game/src/main/java/com/linkedgames/game/model/codex/CodexUserComponent.java` | `add` записи кодекса при генерации награды |
| `game/src/main/java/com/linkedgames/game/model/codex/entries/CodexTankEntry.java` | зависимость: запись кодекса, создаваемая из танка-награды |
| `game/src/main/java/com/linkedgames/game/balance/Balance.java` | общая таблица балансовых данных, часть области: шансы призыва (общий лист Summon, по уровню поезда) по рангу и звёздам (`getSummonRankChance`, `getSummonStarsRankChance`) |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/data/TankData.java` | зависимость: справочник танков; фильтр `type`/`dropType` при выборе награды |
| `game/src/main/java/com/linkedgames/game/model/train/data/TrainSummonData.java` | зависимость: `getRandomStars()` для звёздности награды |
| `game/src/main/java/com/linkedgames/game/service/drop/DropUtils.java` | зависимость: розыгрыш по шансам при генерации |
| `game/src/main/java/com/linkedgames/game/service/drop/DroppedItem.java` | зависимость: результат розыгрыша |
