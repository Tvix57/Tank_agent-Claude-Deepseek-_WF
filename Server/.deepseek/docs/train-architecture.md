# Поезд — `TrainUserComponent` (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-10-14;
> актуализирован после merge `origin/amnesia/fix` (2026-10-19). Всё ниже подтверждено чтением кода,
> запуском не проверялось.
> Клиентский код (`src/views/home_screen/HomeScreen.ts`, `src/views/home_screen/popups/train/`)
> просмотрен только для сверки контракта.

ГДД: [train-gdd.md](/workspace/client/.claude/docs/game-design/train-gdd.md) (черновик по примерному описанию). Ссылки на разделы — у классов и методов ниже и в [п.9](#gdd-link).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`TrainUserComponent`](#cls-trainusercomponent)
   - [`TrainSummonData`](#cls-trainsummondata)
   - [Таблицы баланса поезда (общий Summon)](#cls-balance)
   - [`TrainBuySchemesData`](#cls-trainbuyschemesdata)
   - [`TrainPage`](#cls-trainpage)
   - [Dev-роуты поезда](#dev-tools)
   - [Регистрация и персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Поезд пополняет инвентарь игрока за схемы танка (ресурс `ItemId.RESOURCE_TANK_SCHEME`, хранится в
сумке, см. [bag-architecture.md](bag-architecture.md)); пользователь называет их «жетонами призыва»,
канонический термин — [глоссарий](/workspace/client/.claude/docs/glossary.md).
Один призыв тратит одну схему танка и выдаёт либо предмет коллекции, либо танк. Характеристики танка
зависят от прогресса: ранг и качество звёзд — от уровня поезда, уровень танка — от уровня игрока.

Правила по коду:

- Призыв (`/ingame/train/summon`): сначала бросок предмета коллекции
  ([collections-architecture.md#roll-section](collections-architecture.md#roll-section)); выпал —
  предмет сразу уходит в коллекцию. Не выпал — танк: ранг по таблице `SummonRankChances` для уровня поезда,
  модель равновероятно среди танков ранга с `dropType == TRAIN`, уровень и звёзды —
  [`rollTankLevelAndStars`](#m-rolltanklevelandstars).
- Цена и эффекты призыва: схема танка −1, опыт поезда +1, квест `TRAIN_SUMMON` +1 — в обеих ветках.
  Опыт игрока +1 и опыт клана +1 (`ClanUserComponent.addExp`) — только в ветке танка.
- Решение по танку: выпавший танк хранится в компоненте (`receivedTank`) до решения игрока; пока
  решения нет, повторный призыв возвращает тот же танк без списания схемы. `/accept` ставит танк в
  ангар (самый слабый танк его типа заменяется, если все позиции типа заняты; за заменённый — 10
  серебра). `/refuse` — продажа выпавшего танка за 10 серебра.
- Уровень поезда: опыт поезда = число призывов. Для перехода на уровень `L+1` нужно
  `SummonUpgrade[L+1].summonRequire` опыта; избыток переносится, за одно начисление можно взять
  несколько уровней. На последнем уровне таблицы опыт не копится.
- Покупка схем танка (`/buySchemes`) — фиксированные наборы за золото
  ([`TrainBuySchemesData`](#cls-trainbuyschemesdata)).
- Стартовый набор — `initStarter`: 50 схем танка новому игроку (схемы самолёта поезд больше не выдаёт).
- Туториал: `/accept` двигает шаги `TutorialData.FIRST_TRAIN`/`SECOND_TRAIN`
  ([tutorial-architecture.md#effects](tutorial-architecture.md#effects),
  [#consumers](tutorial-architecture.md#consumers)); фиксированных танков и шагов на `/summon` в поезде
  больше нет.
- Запись в кодекс — в момент выпадения танка, до решения игрока
  ([codex-architecture.md#producers](codex-architecture.md#producers)).

Другие источники схем танка (правила — в документах этих областей): награды квестов
([quests-architecture.md](quests-architecture.md)), бой кампании (`CampaignPage
/battleTankReward`), награда за простой (`IdleUserComponent.takeRewards`), dev-роут
[`/trainAddSchemes`](#dev-tools).

Прокачка (пороги, шансы рангов и звёзд) идёт по общим листам Summon (`model.summon.data.SummonUpgradeData`,
`Balance.getSummon*`); их же читает `MilitaryBaseUserComponent`. Области Summon и военной базы здесь не
описаны. Уровень поезда читают и другие области: сборка — доступность ранга и звёзды награды
([assembly-architecture.md#m-tankrankisavailable](assembly-architecture.md#m-tankrankisavailable),
[#m-generatereward](assembly-architecture.md#m-generatereward)), экспериментальные танки — ранг
монеты при дропе ([collections-architecture.md#drop-item-generation](collections-architecture.md#drop-item-generation)).

<a id="references"></a>
## 2. Референсы

Нет. Компонент и `TrainPage` — из исходного коммита проекта; позже в них добавлены туториал, ветка
предмета коллекции и опыт клана. Компонент сам служит образцом: `ExperimentalTanksSectionType.takePendingTank`/
`sellPendingTank` — копии `/accept`/`/refuse`
([collections-architecture.md#pending-tank](collections-architecture.md#pending-tank)),
`AerodromeUserComponent` повторяет структуру компонента для самолётов
([aerodrome-architecture.md](aerodrome-architecture.md)).

<a id="patterns"></a>
## 3. Паттерны

- **`UserChildComponent` в документе игрока.** Состояние — поля в поддокументе `Train` документа
  `User`; запись — `changedField(<ключ>, <значение>)` при каждом изменении, загрузка —
  `dbMappingBuild`. Отдельной Mongo-коллекции и DAO нет.
- **Отложенная награда.** Выпавший танк сохраняется в БД (`rct`) до решения игрока, поэтому переживает
  перезаход; ответ `HomePage`/`TrainPage` возвращает его, пока он не принят или не продан. Тот же
  приём для предмета коллекции (`rci`), но там предмет забирается в том же запросе.
- **Взвешенный бросок** — `DropUtils.RollDrop` по списку `DroppedItem<Rank>`; шансы — из таблиц
  баланса через `PercentValueData` (проценты с 4 знаками, `100 % = 1 000 000`).
- **Статические данные в коде** — `ImmutableMap` в `TrainSummonData` и `TrainBuySchemesData`; в
  отличие от листов `SummonUpgrade`/`SummonRankChances`/`SummonStarsRankChances`, они не приходят из таблицы баланса.

<a id="class-list"></a>
## 4. Список классов

Пакет `com.linkedgames.game.model.train`: `TrainUserComponent` (с вложенным `DBFields`),
`data.TrainSummonData`, `data.TrainBuySchemesData`.
Страница: `com.linkedgames.game.pages.ws.ingame.TrainPage`.
Части чужих классов, принадлежащие поезду: summon-методы `Balance` (`model.summon.data.SummonUpgradeData`), train-роуты `DevToolsPage`.

<a id="anchors"></a>
## 5. Навигация (якоря)

| Якорь | Что там |
|---|---|
| `#cls-trainusercomponent` | поля, методы компонента |
| `#m-receivetank` | выдача танка |
| `#m-rolltanklevelandstars` | уровень и звёзды танка |
| `#m-addexp` | опыт и уровень поезда |
| `#m-getupgradedatajson` | данные окна прокачки |
| `#cls-trainsummondata` | шансы количества звёзд |
| `#cls-balance` | таблицы баланса поезда |
| `#cls-trainbuyschemesdata` | наборы схем танка за золото |
| `#cls-trainpage` | роуты `/ingame/train` |
| `#dev-tools` | dev-роуты поезда |
| `#persistence` | регистрация в `User`, ключи БД |
| `#client-contract` | JSON ответов, расхождения с клиентом |
| `#tradeoffs` | баги, дубли, компромиссы |

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `TrainUserComponent`, `TrainUserComponent.DBFields` | [#cls-trainusercomponent](#cls-trainusercomponent), [#persistence](#persistence) |
| `TrainSummonData` | [#cls-trainsummondata](#cls-trainsummondata) |
| summon-часть `Balance` | [#cls-balance](#cls-balance) |
| `TrainBuySchemesData` | [#cls-trainbuyschemesdata](#cls-trainbuyschemesdata) |
| `TrainPage` | [#cls-trainpage](#cls-trainpage) |
| train-роуты `DevToolsPage` | [#dev-tools](#dev-tools) |

## 7. Классы и методы

<a id="cls-trainusercomponent"></a>
### `TrainUserComponent`

`UserChildComponent`, `APIResponseStd`. Имя компонента `"Train"`, создаётся лениво в
`User.getTrainComponent()`.

Поля: `level` (уровень поезда, по умолчанию 1), `exp` (опыт до следующего уровня), `receivedTank`
(выпавший, ещё не принятый танк), `receivedCollectionItem` (выпавший предмет коллекции).

<a id="m-receivetank"></a>
**`receiveTank(): Tank`** — выдаёт танк призыва и сохраняет его в `receivedTank`.
- Есть непринятый танк — возвращает его, ничего не бросая.
- Ранг — `RollDrop` по `Balance.getSummonRankChance(level, rank)` для `Rank.TANKS` (I–XX);
  модель — случайная из `Balance.getTanks(rank)` с `dropType == TRAIN`; уровень и звёзды —
  `rollTankLevelAndStars`.
- Затем `changedField("rct")`, запись в кодекс (`createCodexEntry` + `CodexUserComponent.add`).
- Схему танка, опыт и квест не трогает — это делает [`TrainPage`](#cls-trainpage).
- ГДД: [gdd-tank-roll](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-tank-roll) (ранг, модель), [gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision) (возврат непринятого танка).

<a id="m-rolltanklevelandstars"></a>
**`rollTankLevelAndStars(Tank)`** — общий для поезда и награды экспериментальной коллекции
(`CollectionExperimentalTank`). Качество звёзд — `RollDrop` по
`getSummonStarsRankChance(level, rank)` для `Rank.TANK_STARS`; количество —
[`TrainSummonData.getRandomStars()`](#cls-trainsummondata); уровень — случайный в
`[user.level − 5; user.level + 5]`, обрезанный до `[TankData.MIN_LEVEL; TankData.MAX_LEVEL]`;
затем `recalculateParams()`. ГДД: [gdd-tank-roll](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-tank-roll).

**`receiveCollectionItemFromSection(CollectionSectionType)`** — предмет коллекции для призыва,
описан в [collections-architecture.md#roll-section](collections-architecture.md#roll-section).

<a id="m-addexp"></a>
**`addExp(int delta)`** — опыт поезда. `getNeedExp() == 0` (следующего уровня в `SummonUpgrade` нет) —
выход без изменений. Иначе `exp += delta`; при `delta > 0` цикл: пока `exp >= needExp` — уровень +1,
`exp -= needExp`, пересчёт `needExp`; достигнут последний уровень — `exp = 0`. Пишет `l` и `exp`. ГДД: [gdd-train-level](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-train-level).

**Уровень:**
- `getNeedExp()` — `SummonUpgrade[level + 1].summonRequire` или 0, если строки нет.
- `getNextLevel()` (private) — `level + 1`, если строка `SummonUpgrade[level + 1]` есть, иначе `level`.
- `addLevel()` — `level = getNextLevel()` (с потолком), используется dev-роутом.
- `addLevel(int delta)` — `level += delta` без потолка, используется только в `addExp`.
- `removeLevel()` — `level − 1`, не ниже 1; `exp` не меняет.

<a id="m-getupgradedatajson"></a>
**`getUpgradeDataJSON()`** — данные окна прокачки: `currentLevel`, `nextLevel`, `exp`, `expM`, массивы
`rank` и `stars` (`{rank, current, next}` — шанс на текущем и следующем уровне). «Важный уровень»:
первый ранг (и отдельно качество звёзд) с нулевым шансом после первого ненулевого; затем поиск от
`level` до `Balance.getMaxSummonLevel()` первого уровня, где его шанс ненулевой →
`importantRankLevel`/`importantStarsLevel` `{level, rank}`; не найден — ключ отсутствует. ГДД:
[gdd-train-level](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-train-level).

**`getSilverCoinsReward(Tank)`** — цена продажи танка: 10 при `tank != null`, иначе 0. Характеристики
танка не учитывает. Зовут `/accept` (за заменённый танк), `/refuse` (за выпавший) и
`ExperimentalTanksSectionType.addTankSaleReward`. ГДД: [gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision).

**`initStarter()`** — `addResource(RESOURCE_TANK_SCHEME, 50)`; вызывает `ActorInitializationTask`, когда сумка игрока
пуста (рядом `BagUserComponent.initStarter` и `MilitaryBaseUserComponent.initStarter`). Правило —
[bag-gdd.md#gdd-starter](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-starter).

**`apiResponse()`** — `{receivedTank?, receivedCollectionItem?, currentLevel, nextLevel, exp, expM}`.

**`dbMappingBuild(Document)`** — `l` (по умолчанию 1), `exp` (0); непустой `rct` → `Tank` через
`ItemFactory` (`null` от фабрики — поле остаётся пустым); непустой `rci` → `CollectionItem`, но только если его коллекция существует у игрока
(иначе отбрасывается в памяти, см.
[collections-architecture.md#no-section-type](collections-architecture.md#no-section-type)).

Тривиальные: `getLevel()`, `getReceivedTank()`, `getReceivedCollectionItem()`,
`canReceiveTank()`/`canReceiveCollectionItem()` (`поле == null`), `clearReceivedTank()`/
`clearReceivedCollectionItem()` (поле `null` + пустой `Document` в БД), `modifyReceiver` (пустой).

<a id="cls-trainsummondata"></a>
### `TrainSummonData`

Статический `getRandomStars()` — количество звёзд нового танка по весам `1→30, 2→25, 3→20, 4→15,
5→10` (из 100), от уровня не зависит. ГДД: [gdd-tank-roll](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-tank-roll). Зовут `rollTankLevelAndStars` и
`AssemblyUserComponent.generateReward`.

<a id="cls-balance"></a>
### Таблицы баланса поезда (общий Summon)

Листы `balance.json` общие для систем призыва (импорт — `BalanceImporter`, формат строк —
[tank-airplane-data-architecture.md](tank-airplane-data-architecture.md)). Отдельных листов и модели
`TrainUpgradeData` нет:

| Лист | Модель | Строка | Метод `Balance` |
|---|---|---|---|
| `SummonUpgrade` | `model.summon.data.SummonUpgradeData` (`level`, `summonRequire`) | опыт для перехода на уровень | `getSummonUpgradeData(level)` |
| `SummonRankChances` | `PercentValueData` | шансы рангов на уровне | `getSummonRankChance(level, rank)` |
| `SummonStarsRankChances` | `PercentValueData` | шансы качества звёзд на уровне | `getSummonStarsRankChance(level, rank)` |

- Колонка `i` строки `PercentValueData` соответствует `Rank.ordinal() == i`; уровня нет в таблице —
  все шансы 0 (`PercentValueData.EMPTY`).
- `getMaxSummonLevel()` — максимальный ключ `SummonUpgrade` (тот же источник, что и предел роста
  уровня в `getNextLevel`).

<a id="cls-trainbuyschemesdata"></a>
### `TrainBuySchemesData`

`LIST: ImmutableMap<id, data>` — наборы схем танка: `id`, `tankSchemes`, `bonus`, `priceGoldenCoins`;
`apiResponse()` → `{id, schemes, bonus, priceGoldenCoins}`. Значения — в самом классе; `bonus` у всех
наборов 0. ГДД: [gdd-buy-schemes](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-buy-schemes).

<a id="cls-trainpage"></a>
### `TrainPage` (`/ingame/train`)

`AuthorizedUserPage`, регистрация в `WSRouter`. Ошибки — `error()` без текста.

| Роут | Вход | Что делает | Ответ |
|---|---|---|---|
| `""` | — | состояние | `{train}` |
| `/summon` | — | призыв, порядок веток ниже | см. ниже |
| `/accept` | — | принять выпавший танк | `{rewards, train, tutorial?}` |
| `/refuse` | — | продать выпавший танк | `{rewards, train}` |
| `/autoData` | — | шансы рангов для автопризыва ([gdd-auto-summon](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-auto-summon)) | `{trainLevel, campaignLevel, list: [{rank, chance}]}` |
| `/upgradeData` | — | [`getUpgradeDataJSON`](#m-getupgradedatajson) | payload целиком |
| `/buySchemesData` | — | наборы схем танка | `{slots: [TrainBuySchemesData]}` |
| `/buySchemes` | `{id}` | купить набор | `{rewards}` |

**`/summon`** (ГДД: [gdd-summon](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-summon), [gdd-scheme](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-scheme)), ветки по порядку:
1. Есть `receivedCollectionItem` → `sendCollectionItemReply` (схема не списывается).
2. Есть `receivedTank` → `{receivedTank, replaceableTank}` (без `train`, `account`; схема не
   списывается).
3. Схем танка < 1 → `error()`.
4. `CollectionUserComponent.rollDropSectionType()` → секция → `receiveCollectionItemFromSection` →
   предмет есть: схема танка −1, `train.addExp(1)`, квест `TRAIN_SUMMON`, `sendCollectionItemReply`.
5. `receiveTank()`; `null` → `error()`. Схема танка −1, `user.addExp(1)`, `train.addExp(1)`, квест
   `TRAIN_SUMMON`, `ClanUserComponent.addExp(1)` →
   `{receivedTank, replaceableTank|null, train, account}`.

`sendCollectionItemReply` — `CollectionUserComponent.receiveSummonedItem`, затем
`clearReceivedCollectionItem()`; форма ответа —
[collections-architecture.md#summon-reply](collections-architecture.md#summon-reply).

**`/accept`**: нет `receivedTank` → `error()`. `replaceableTank = Hangar.getReplaceableTank`;
серебро `getSilverCoinsReward(replaceableTank)` → `BagUserComponent.add` + квест
`SILVER_COINS_GAINED`; `Hangar.addTank(receivedTank)`; `clearReceivedTank()`; квесты `TANK_SELL`
(если был заменяемый) и `BETTER_TANK` (заменяемого нет или мощность нового больше);
`user.onBasicInfoUpdate()`; шаги туториала `TutorialData.FIRST_TRAIN`/`SECOND_TRAIN` (`tutorial` в ответе). ГДД: [gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision). Правила квестов —
[quests-architecture.md#progress-sources](quests-architecture.md#progress-sources).

**`/refuse`**: нет `receivedTank` → `error()`. Серебро `getSilverCoinsReward(receivedTank)` + квест
`SILVER_COINS_GAINED`; `clearReceivedTank()`; квест `TANK_SELL`. Туториал не трогает. ГДД:
[gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision).

**`/buySchemes`**: неизвестный `id` или золота меньше цены → `error()`. Золото −цена,
`tankSchemes + bonus` схем танка через `BagUserComponent.add`. Квестов нет. ГДД: [gdd-buy-schemes](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-buy-schemes).

<a id="dev-tools"></a>
### Dev-роуты поезда (`DevToolsPage`, `/ingame/devTools`, только при `app.devTools=true`)

- `/trainAddSchemes` — +10 схем танка, пустой ответ.
- `/trainAddLevel` — `addLevel()`, ответ `{train, upgradeData}`.
- `/trainRemoveLevel` — `removeLevel()`, ответ `{train, upgradeData}`.
- `/collectionSummon` — выдача предмета коллекции через компонент поезда,
  [collections-architecture.md#roll-section](collections-architecture.md#roll-section).

<a id="persistence"></a>
### Регистрация и персистентность

- `User`: поле `train`, `getTrainComponent()`, `modifyReceiver`, загрузка поддокумента `Train`
  (`User.DBFields.P_TRAIN_FIELD`) в `dbMappingBuild`, если ключ есть.
- `TrainUserComponent.DBFields`: `l` — уровень, `exp` — опыт, `rct` — выпавший танк
  (`Tank.dbToData()`), `rci` — выпавший предмет коллекции. Очистка — пустой `Document`, ключ не
  удаляется.
- `ActorInitializationTask` (`buildComponents`): пустая сумка → `initStarter()` сумки и поезда.
- `HomePage /ingame/home` кладёт `train.apiResponse()` в payload главного экрана.

<a id="client-contract"></a>
### Контракт с клиентом

Push-событий у компонента нет; изменения сумки (схемы, золото, серебро) клиент получает push-ом
сумки ([bag-architecture.md#client-contract](bag-architecture.md#client-contract)). Ангар клиент
перезапрашивает сам (`/ingame/home/hangar` после локального `HANGAR_UPDATE` из `OnTrainAccept`);
серверный `UserEmitterId.HANGAR_UPDATE` из `HangarUserComponent` — внутреннее событие, клиенту не
приходит.

Клиент (`HomeScreen.ts`, `popups/train/*`, типы `TrainJSON`/`TrainUpgradeDataJSON`/
`TrainAutoSummonJSON` в `home.d.ts`, `TrainBuySchemesPopupJSON` в `train.d.ts`) использует роуты
`/summon`, `/accept`, `/refuse`, `/autoData`, `/upgradeData`, `/buySchemesData`, `/buySchemes`,
dev `/trainAddLevel`, `/trainRemoveLevel`, `/collectionSummon`; поля ответов совпадают с серверными.
Наблюдения:
- Роут `""` и dev `/trainAddSchemes` клиент не вызывает: состояние поезда приходит из `/ingame/home`.
- Любой `error()` на `/summon` клиент после туториала трактует как «нет схем» и открывает окно
  покупки.
- Автопризыв целиком на клиенте: сервер отдаёт только шансы (`/autoData`), отбор танка и `/refuse`
  неподходящих делает клиент.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Решений пользователя по пунктам нет, если не указано иное.

1. Ветка предмета коллекции не начисляет опыт игрока и опыт клана. В ветке танка `user.addExp(1)` и
   `clan.addExp(1)` есть, в ветке предмета — нет. Бросок предмета идёт и при включённом туториале
   (поезд туториал больше не подменяет). Вопросы про опыт игрока и туториал открыты в
   [gdd-open](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-open).
2. Переходы состояния собраны в `TrainPage` (без неявного порядка вызовов, WF
   `#no-implicit-order`): «принять» = `Hangar.addTank` + `clearReceivedTank` + серебро + квесты;
   «продать» = серебро + `clearReceivedTank` + квест; призыв = `receive*` + списание схемы + опыт +
   квест; предмет коллекции = `receiveCollectionItemFromSection` → `receiveSummonedItem` →
   `clearReceivedCollectionItem` (то же в `DevToolsPage`). Кандидаты в методы-переходы у
   `TrainUserComponent`: принять, продать, призвать.
3. Дубли одного правила (WF `#gdd-function-mapping`):
   - бросок звёзд по уровню поезда — `rollTankLevelAndStars` и копия в
     `AssemblyUserComponent.generateReward` (уровень там — ровно уровень игрока, без ±5);
   - «принять/продать танк» — `/accept`/`/refuse` и `ExperimentalTanksSectionType.takePendingTank`/
     `sellPendingTank` ([collections-architecture.md#tradeoffs-and-known-issues](collections-architecture.md#tradeoffs-and-known-issues) п.5, принято там без действий);
   - цена продажи 10 серебра — `getSilverCoinsReward` и `CollectionExperimentalTank.DUPLICATE_ITEM_PRICE`
     (там же, п.3, принято);
   - окно прокачки — `getUpgradeDataJSON` и аналог в `AerodromeUserComponent` и `MilitaryBaseUserComponent`;
   - защита «непринятый танк» — `canReceiveTank()` в странице и ранний `return receivedTank` в
     `receiveTank()`.
4. Имена расходятся со смыслом. `getSilverCoinsReward(Tank)` — цена продажи танка;
   `addLevel()` (с потолком) и `addLevel(int)` (без потолка) — одно имя, разное поведение.
5. Условие «важного уровня» `current == 0 && next != 0 || current == 0 && next == 0` равно
   `current == 0` (то же в аэродроме).
6. Максимальный уровень один — ключи `SummonUpgrade` (`getMaxSummonLevel`, `getNextLevel`). Если в
   `SummonRankChances` нет строки для уровня поезда, все шансы 0, и `DropUtils.RollDrop` вызовет
   `nextIntInclusive(1, 0)` → `IllegalArgumentException`. Покрытие листов одними уровнями держится
   вручную.
7. Листы `Summon*` общие с `MilitaryBaseUserComponent` (область не документирована): правка листов
   меняет прокачку и там.
8. Пустой список танков `TRAIN` для ранга — падение в `receiveTank`; намеренно не обрабатывается
   ([tank-airplane-data-architecture.md#tradeoffs](tank-airplane-data-architecture.md#tradeoffs) п.7,
   решение пользователя).
9. `/buySchemes` читает `id` через `getInt` — без ключа запрос падает исключением, а не
   `error()`.
10. `removeLevel()` не трогает `exp` — после понижения `exp` может быть ≥ порога; лишнее
    уйдёт в уровни при следующем `addExp`. Только dev-роут.
11. `/refuse` продаёт выпавший танк и при свободной позиции его типа в ангаре, хотя по
    [gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision) (решение
    пользователя 2026-10-14) продажа доступна только при замене. Клиент кнопку «Продать» в этом
    случае не показывает — расхождение только серверной проверки.
12. Кандидаты на удаление: пустой `modifyReceiver`; поле `bonus` в `TrainBuySchemesData` (у всех
    наборов 0) — если бонусы не планируются.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД области — [train-gdd.md](/workspace/client/.claude/docs/game-design/train-gdd.md). Правило → реализация:

| Правило ГДД | Где реализовано |
|---|---|
| [gdd-scheme](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-scheme) — 1 схема танка за призыв, без схем ошибка | `TrainPage /summon` ветка 3 и списание в ветках 4–5 |
| [gdd-summon](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-summon) — опыт поезда +1, квест `TRAIN_SUMMON` +1 за любой призыв | `TrainPage /summon` ветки 4–5 |
| [gdd-tank-roll](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-tank-roll) — ранг, модель | `TrainUserComponent.receiveTank` |
| [gdd-tank-roll](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-tank-roll) — качество, количество звёзд, уровень танка | `rollTankLevelAndStars`, `TrainSummonData.getRandomStars` (копия броска звёзд — `AssemblyUserComponent.generateReward`, [#tradeoffs](#tradeoffs) п.3) |
| [gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision) — непринятый танк возвращается без траты схемы | `TrainPage /summon` ветка 2, ранний `return` в `receiveTank` (дубль, [#tradeoffs](#tradeoffs) п.3) |
| [gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision) — «Взять»: замена слабейшего, 10 серебра | `TrainPage /accept`, `getSilverCoinsReward`, `HangarUserComponent.getReplaceableTank`/`addTank` |
| [gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision) — «Продать»: 10 серебра | `TrainPage /refuse`, `getSilverCoinsReward` |
| [gdd-train-level](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-train-level) — пороги, максимум, перенос опыта | `addExp`, `getNeedExp`, `getNextLevel`, лист `SummonUpgrade` |
| [gdd-train-level](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-train-level) — окно прокачки | `getUpgradeDataJSON`, `/upgradeData` |
| [gdd-buy-schemes](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-buy-schemes) — наборы за золото | `TrainBuySchemesData`, `/buySchemesData`, `/buySchemes` |
| [gdd-auto-summon](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-auto-summon) — автопризыв (выбор ранга на клиенте) | `/autoData` |
| [gdd-tutorial](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-tutorial) — два шага на «Взять», фиксированных танков нет | фиксированных танков в коде нет (удалено при merge) |
| [gdd-open](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-open) — опыт игрока и туториал при предмете коллекции, предмет коллекции в туториале | `TrainPage /summon` ветки 4–5, [#tradeoffs](#tradeoffs) п.1 |
| [collections-gdd.md#gdd-train-drop](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-train-drop) — один бросок на призыв, предмет коллекции вместо танка | `TrainPage /summon` ветка 4, `CollectionUserComponent.rollDropSectionType` |
| [bag-gdd.md#gdd-starter](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-starter) — 1 схема танка, 5 схем самолёта | `TrainUserComponent.initStarter` (в коде 50 схем танка, расходится) |
| [bag-gdd.md#gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend) — трата только при достаточном остатке | проверки схем в `/summon`, золота в `/buySchemes` |

<a id="file-map"></a>
## 10. Карта файлов компонента

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` | компонент: уровень, опыт, выдача танка, отложенный танк/предмет |
| `game/src/main/java/com/linkedgames/game/model/train/data/TrainSummonData.java` | шансы количества звёзд |
| `game/src/main/java/com/linkedgames/game/model/summon/data/SummonUpgradeData.java` | строка листа `SummonUpgrade` (общая модель) |
| `game/src/main/java/com/linkedgames/game/model/train/data/TrainBuySchemesData.java` | наборы схем танка за золото |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/TrainPage.java` | роуты `/ingame/train` |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | поле и геттер компонента, загрузка `Train`, `modifyReceiver`, `addExp` игрока |
| `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorInitializationTask.java` | `initStarter()` при пустой сумке |
| `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` | регистрация `/ingame/train` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/HomePage.java` | `train` в payload главного экрана |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` | dev-роуты поезда, `/collectionSummon` |
| `game/src/main/java/com/linkedgames/game/balance/Balance.java` | загрузка листов Summon, `getSummon*`, `getMaxSummonLevel` |
| `game/src/main/java/com/linkedgames/game/balance/BalanceImporter.java` | импорт листов `SummonUpgrade`, `SummonRankChances`, `SummonStarsRankChances` |
| `game/src/main/resources/balance.json` | листы `SummonUpgrade`, `SummonRankChances`, `SummonStarsRankChances` |
| `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` | читает уровень поезда и шансы, `TrainSummonData` (копия броска звёзд) |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseUserComponent.java` | `getMaxSummonLevel()` и листы Summon ([#tradeoffs](#tradeoffs) п.7), `initStarter` |
| `game/src/main/java/com/linkedgames/game/model/clan/ClanUserComponent.java` | `addExp(1)` при призыве танка |
| `game/src/main/java/com/linkedgames/game/model/collections/CollectionUserComponent.java` | бросок секции и приём предмета призыва |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionExperimentalTank.java` | `rollTankLevelAndStars` для танка-награды |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/ExperimentalTanksSectionType.java` | уровень поезда для ранга монеты, `getSilverCoinsReward`, копии `/accept`/`/refuse` |
| `game/src/main/java/com/linkedgames/game/model/hangar/HangarUserComponent.java` | `getReplaceableTank`, `addTank` при `/accept` |
| `game/src/main/java/com/linkedgames/game/model/codex/CodexUserComponent.java` | запись выпавшего танка в кодекс |
| `game/src/main/java/com/linkedgames/game/model/tutorial/TutorialUserComponent.java` | `increase` шагов на `/accept` |
| `game/src/main/java/com/linkedgames/game/model/tutorial/data/TutorialData.java` | `FIRST_TRAIN`/`SECOND_TRAIN` — шаги `/accept` |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestsUserComponent.java` | квесты `TRAIN_SUMMON`, `TANK_SELL`, `BETTER_TANK`, `SILVER_COINS_GAINED`; схемы танка в награду |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestEvent.java` | событие `TRAIN_SUMMON` |
| `game/src/main/java/com/linkedgames/game/model/quests/data/QuestData.java` | квест 1 — `TRAIN_SUMMON` |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` | `getLevel()` для `/autoData`; `SCHEMES_CHANCE` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` | схема танка в награду за уничтоженный танк |
| `game/src/main/java/com/linkedgames/game/model/idle/IdleUserComponent.java` | схемы танка в награду за простой |
| `game/src/main/java/com/linkedgames/game/model/bag/BagUserComponent.java` | зависимость: хранение схем танка, золота, серебра, список танков |
| `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` | зависимость: ресурсы в наградах |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/Tank.java` | зависимость: выпавший танк |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/data/TankData.java` | зависимость: модели, `MIN_LEVEL`/`MAX_LEVEL` |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankDropType.java` | зависимость: фильтр `TRAIN` |
| `game/src/main/java/com/linkedgames/game/model/item/ItemId.java` | зависимость: `RESOURCE_TANK_SCHEME`, `RESOURCE_GOLDEN_COINS`, `RESOURCE_SILVER_COINS` |
| `game/src/main/java/com/linkedgames/game/model/item/ItemFactory.java` | зависимость: восстановление `rct`/`rci` |
| `game/src/main/java/com/linkedgames/game/model/collections/itemList/CollectionItem.java` | зависимость: выпавший предмет коллекции |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/CollectionSectionType.java` | зависимость: `createRandomDropItem` |
| `game/src/main/java/com/linkedgames/game/model/Rank.java` | зависимость: `TANKS`, `TANK_STARS` |
| `game/src/main/java/com/linkedgames/game/service/drop/DropUtils.java` | зависимость: взвешенный бросок |
| `game/src/main/java/com/linkedgames/game/service/drop/DroppedItem.java` | зависимость: элемент броска |
| `game/src/main/java/com/linkedgames/game/balance/data/PercentValueData.java` | зависимость: строки `SummonRankChances`/`SummonStarsRankChances` |
| `game/src/main/java/com/linkedgames/game/balance/KeyModel.java` | зависимость: ключ `SummonUpgradeData` |
| `game/src/main/java/com/linkedgames/game/model/user/UserChildComponent.java` | зависимость: базовый класс компонента |
| `commons/src/main/java/com/linkedgames/commons/comp/Component.java` | зависимость: `changedField` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AuthorizedUserPage.java` | зависимость: базовый класс страницы |
| `commons/src/main/java/com/linkedgames/commons/rnd/RandomJdk.java` | зависимость: выбор модели, уровня, количества звёзд |
