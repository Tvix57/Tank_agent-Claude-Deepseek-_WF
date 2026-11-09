# Ангар (танки) — `HangarUserComponent` (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду (код в рамках
> задачи не менялся), 2026-10-17; связан с ГДД ангара 2026-10-17. Актуализирован 2026-10-19 после
> merge `origin/amnesia/fix` (номера строк пересчитаны, добавлен `isEmpty`, убраны туториальные ветки).
> Всё ниже подтверждено чтением кода, запуском не проверялось.
> Клиентская сторона здесь упомянута только как список потребителей роутов; сверку полей делает
> `client-analyst-lead`.

ГДД: [hangar-gdd.md](/workspace/client/.claude/docs/game-design/hangar-gdd.md) — разделы
[#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots) (слоты и ряды),
[#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement) (новый танк, замена слабейшего, 10 серебра),
[#gdd-compare-window](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-compare-window), [#gdd-hangar-view](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-hangar-view),
[#gdd-tank-info](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-tank-info), [#gdd-battle-replace](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-battle-replace) (клиентские и
боевые правила; сервер их не реализует). Открытый вопрос —
[#gdd-open](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-open) (танк-награда через `User.addItem`). Смежные правила:
[campaign-gdd.md#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield) (слот N ангара — слот N поля боя),
[bag-gdd.md#gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles) (заменённый танк удаляется насовсем),
[bag-gdd.md#gdd-power](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-power) (мощность). Ссылки на них — у методов ниже и в
[п.9](#gdd-link).

Терминология: в тексте ГДД и этого документа место танка называется «слотом» (1–12); в коде это
`position` (0–11). Танк в слоте N хранится в `position` N−1
([glossary.md](/workspace/client/.claude/docs/glossary.md)). Имена в коде (`position`,
`TYPE_POSITION`, `getEmptyPosition`) остаются как есть.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`HangarUserComponent`](#cls-hangarusercomponent)
   - [`TankType.TYPE_POSITION`](#cls-tanktype)
   - [Роуты `HomePage`](#cls-homepage)
   - [Регистрация и персистентность](#persistence)
   - [Источники танков (кто ставит в ангар)](#producers)
   - [Потребители состояния ангара](#consumers)
   - [Dev-роуты](#dev-tools)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Ангар держит расстановку танков игрока по 12 слотам
([#gdd-purpose](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-purpose)). Сами танки лежат в сумке
([bag-architecture.md](bag-architecture.md)); ангар хранит только `uid` танка в каждом слоте. Танки
из слотов идут в команду боя (кампания, Battlefield) и показываются в профиле.

Правила по коду:

- Слоты по типу танка (`TankType.TYPE_POSITION`, [#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots)): слоты 1–4
  (`position` 0–3) — тяжёлые, 5–8 (4–7) — средние, 9–12 (8–11) — лёгкие и ПТ-САУ (общий ряд).
  Лёгкие и ПТ в одном ряду вытесняют друг друга — так задумано (решение пользователя 2026-10-17,
  [#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement)).
- Танк ставит в ангар игра, игрок слот не выбирает и танки не переставляет: роутов для этого нет.
- Новый танк встаёт в первый свободный слот своего ряда
  ([#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement)). Если весь ряд занят — заменяет самый слабый по `getPower()`
  танк ряда; при равной мощности — первый по порядку слотов. Заменённый танк уменьшается на 1 в
  сумке, то есть удаляется ([bag-gdd#gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles)).
- Серебро за заменённый танк, квесты `TANK_SELL`/`BETTER_TANK` и решение «взять или продать» ангар не
  обрабатывает — это делают вызывающие ([#producers](#producers)).
- Стартового состояния нет: слоты пусты, пока игрок не возьмёт первый танк через поезд. Фиксированных
  туториальных танков больше нет: `TrainPage /accept` лишь двигает шаги туториала `FIRST_TRAIN` и
  `SECOND_TRAIN` ([tutorial-architecture.md](tutorial-architecture.md)).
- Пустой ангар (`isEmpty`) закрывает вход в рейтинговый бой кампании (`RankedChallengeService.touch`);
  сама область боя здесь не описана ([#consumers](#consumers)).

<a id="references"></a>
## 2. Референсы

ГДД ангара — [hangar-gdd.md](/workspace/client/.claude/docs/game-design/hangar-gdd.md). Расстановка самолётов в
`AerodromeUserComponent` (`getReplaceableAirplane`, `addAirplane`, `getEmptyPosition`,
`getCurrentPosition`) — почти построчная копия ангара
([aerodrome-architecture.md#cls-aerodromeusercomponent](aerodrome-architecture.md#cls-aerodromeusercomponent)).
Решение пользователя 2026-10-17: копии не объединять, найденные баги исправлять в обеих.

<a id="patterns"></a>
## 3. Паттерны

- **Компонент пользователя** — `UserChildComponent` с `dbMappingBuild`/`changedField`, хранится
  поддокументом `Hangar` в документе пользователя.
- **Слоты по ссылке.** `Map<Integer, ObjectId>`: `position` слота → `uid` танка из сумки. Танк читается
  через `BagUserComponent.getTank(uid)`, который возвращает `null` для отсутствующего или
  недоступного танка.
- **Внутреннее событие** `UserEmitterId.HANGAR_UPDATE` после изменения расстановки.

<a id="class-list"></a>
## 4. Список классов

Задача — документирование существующего кода, классы не создавались и не менялись. Классы
компонента:

- `model/hangar/HangarUserComponent` — компонент ангара (единственный класс пакета); правила
  [#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots), [#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement).
- `pages/ws/ingame/HomePage` — роут `/ingame/home/hangar` и блок `hangar` в `/ingame/home`.
- `model/bag/tank/TankType` — таблица слотов по типу (класс области сумки, ангар — основной
  потребитель); правило [#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots).

<a id="anchors"></a>
## 5. Навигация (якоря)

| Якорь | Что там |
|---|---|
| `#m-getreplaceabletank` | выбор заменяемого танка |
| `#m-addtank` | постановка танка в слот, замена |
| `#m-json` | два формата ответа: `uid` и полный танк |
| `#persistence` | поле БД `tn`, регистрация в `User` |
| `#producers` | кто ставит танки в ангар |
| `#consumers` | кто читает слоты |
| `#client-contract` | роуты и поля для клиента |
| `#tradeoffs` | находки с номерами строк |

<a id="class-nav"></a>
## 6. Оглавление по классам

- [`HangarUserComponent`](#cls-hangarusercomponent): [`getReplaceableTank`](#m-getreplaceabletank),
  [`addTank`](#m-addtank), [JSON](#m-json), [прочие методы](#m-other)
- [`TankType.TYPE_POSITION`](#cls-tanktype)
- [`HomePage`](#cls-homepage)

## 7. Классы и методы

Пути ниже — от `game/src/main/java/com/linkedgames/game/`.

<a id="cls-hangarusercomponent"></a>
### `HangarUserComponent`

`model/hangar/HangarUserComponent.java`. Поля: `POSITIONS = 12` (private, `:22`), `tanks` — `position`
0–11 (слоты 1–12) → `uid` танка (`:24`). Класс выражает [#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots) и
[#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement).

<a id="m-getreplaceabletank"></a>
**`getReplaceableTank(Tank newTank): Tank`** (`:38-63`;
[#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement)) — самый слабый танк среди слотов ряда нового танка. Возвращает
`null`, если хотя бы один слот ряда пуст или его `uid` не найден в сумке (`:45-52`; для «потерянного»
`uid` это расходится с ГДД, [#tradeoffs](#tradeoffs) п.1). Сравнение строгое (`<`, `:58`): при
равной мощности остаётся первый по порядку слотов. Ряд общий для лёгких и ПТ-САУ, поэтому лёгкий
танк может заменить ПТ-САУ и наоборот — задумано ([#tradeoffs](#tradeoffs) п.4). Вызывается пятью вызывающими
([#producers](#producers)) для окна сравнения и расчёта серебра, затем повторно внутри `addTank`.

<a id="m-addtank"></a>
**`addTank(Tank tank)`** (`:65-83`;
[#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement),
[bag-gdd#gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles)) — ставит танк в слот:

1. Слот — первый пустой слот ряда (`getEmptyPosition`, `:69`).
2. Есть заменяемый — слот заменяемого (`getCurrentPosition`), ему `addCount(-1)` (`:70-74`).
3. Слот не найден (`-1`) — `position` 0, то есть слот 1 (`:75-77`, [#tradeoffs](#tradeoffs) п.1).
4. `BagUserComponent.add(tank)`, `uid` из `ItemAddInfo.item` пишется в слот (`:78-79`),
   `dbTanksChanged()`, событие `HANGAR_UPDATE` (`:80-82`).

<a id="m-json"></a>
**JSON** ([#gdd-hangar-view](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-hangar-view) — данные для блока ангара на главной;
[campaign-gdd#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield)):

- `apiResponse()` (`:156-161`) → `{tanks: [{position, tankUid | null}] ×12}`, через private
  `getTanksJSON()` (`:138-154`).
- `getFullTanksJSON()` (`:120-136`) → `[{position, tank: Tank.apiResponse() | null}] ×12`. Пишет
  `null` и для слота, `uid` которого нет в сумке. Используется только в профиле
  ([#consumers](#consumers)).

<a id="m-other"></a>
**Прочие методы** (тривиальные):

- `isEmpty()` (`:34-36`) — `true`, если ни в одном слоте нет `uid`; читает `RankedChallengeService.touch`.
- `getTankUid(int position)` (`:85-87`) — `uid` в слоте или `null`.
- `getCurrentPosition(Tank)` (`:89-103`, private) — `position` по `uid` или `−1`.
- `getEmptyPosition(Tank)` (`:105-112`, private) — первый слот ряда без `uid`; слот с
  «потерянным» `uid` считает занятым.
- `dbTanksChanged()` (`:114-118`, private) — пишет всю карту целиком в поле `tn`.
- `dbMappingBuild(Document)` (`:163-169`) — читает `tn`: ключ-строка → `Integer.parseInt`, значение
  → `ObjectId`; диапазон `position` не проверяется.
- `modifyReceiver` (`:30-32`) — пустой.

<a id="cls-tanktype"></a>
### `TankType.TYPE_POSITION`

`model/bag/tank/TankType.java:16-21` — тип → список `position` слотов
([#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots), слот N = `position` N−1): `HEAVY` 0–3, `MEDIUM` 4–7, `LIGHT`
8–11, `TD` 8–11. Обратная таблица `POSITION_TYPE` (`:23-36`) в коде сервера не используется. Тот же
`TYPE_POSITION` подбирает танки бота по слоту в `BattleDataFactory.java:121`
([battle-architecture.md](battle-architecture.md)).

<a id="cls-homepage"></a>
### Роуты `HomePage` (`/ingame/home`)

`pages/ws/ingame/HomePage.java`:

- `""` (`:19-28`) — в payload главного экрана среди прочего `hangar: apiResponse()`
  ([#gdd-hangar-view](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-hangar-view)).
- `/hangar` (`:37-42`) — только `hangar: apiResponse()`. Ошибок нет.

Своей страницы у ангара нет.

<a id="persistence"></a>
### Регистрация и персистентность

- `User.getHangarComponent()` (`model/user/User.java:208-212`) — ленивое создание с именем
  `"Hangar"`; `modifyReceiver` (`:424`); загрузка из поля `User.DBFields.P_HANGAR_FIELD = "Hangar"`
  (`:679-680`, `:753`).
- `HangarUserComponent.DBFields.TANKS_FIELD = "tn"` — `{"0": ObjectId, …}`; пустые слоты не
  пишутся.
- Ангар хранится в документе пользователя, танки — в отдельной коллекции сумки
  ([bag-architecture.md](bag-architecture.md)). Запись не атомарна: ангар и сумка сохраняются
  независимо.
- Индексов и миграций у ангара нет; скрипта чистки сирот в сумке, как `CleanupAerodrome` у
  аэродрома, тоже нет (запланирован, [#tradeoffs](#tradeoffs) п.1).

<a id="producers"></a>
### Источники танков (кто ставит в ангар)

ГДД: [#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement) (общее правило и что получает игрок от каждого источника),
[train-gdd#gdd-decision](/workspace/client/.claude/docs/game-design/train-gdd.md#gdd-decision),
[assembly-gdd#gdd-take](/workspace/client/.claude/docs/game-design/assembly-gdd.md#gdd-take),
[collections-gdd#gdd-exp-reward](/workspace/client/.claude/docs/game-design/collections-gdd.md#gdd-exp-reward).

| Вызывающий | `getReplaceableTank` | `addTank` | Серебро за заменённый | Квесты |
|---|---|---|---|---|
| `TrainPage /summon` (`pages/ws/ingame/TrainPage.java:46, :83`) | окно сравнения | — | — | — |
| `TrainPage /accept` (`:123, :137`) | да | да | 10 (`getSilverCoinsReward`) | `TANK_SELL`, `BETTER_TANK` |
| `AssemblyPage /compare` (`pages/ws/ingame/AssemblyPage.java:49`) | окно сравнения | — | — | — |
| `AssemblyUserComponent.takeTankReward` (`model/assembly/AssemblyUserComponent.java:226`) | — | да | нет ([assembly-architecture.md#tradeoffs](assembly-architecture.md#tradeoffs) п.14) | нет |
| `CollectionExperimentalTankPage /compareReward` (`pages/ws/ingame/CollectionExperimentalTankPage.java:109`) | окно сравнения | — | — | — |
| `ExperimentalTanksSectionType.takePendingTank` (`model/collections/sectionList/ExperimentalTanksSectionType.java:277, :282`) | да | да | да (`addTankSaleReward`) | `TANK_SELL`, `BETTER_TANK` |

Танк, выданный наградой через `User.addItem` (квесты, idle, офферы, достижения, Battlefield),
попадает только в сумку, не в ангар. Должен ли такой танк проходить постановку в ангар и бывают ли такие награды — открытый вопрос ГДД
([#gdd-open](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-open)); в данных не проверялось ([#tradeoffs](#tradeoffs) п.6).

<a id="consumers"></a>
### Потребители состояния ангара

ГДД: [campaign-gdd#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield) (слот N ангара — слот N
поля), [#gdd-battle-replace](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-battle-replace) (замена во время боя).

- `User.createTeam()` (`model/user/User.java:346-372`) — копии танков слотов 1–12 (`position` 0–11)
  в команду боя, слот танка в команде = слот в ангаре. Используют `BattleDataFactory` (бой кампании,
  `:29`), `BattlefieldPage /participate`, `/refuse`, `BattlefieldUserComponent` (`:97`).
  Бой кампании и рейтинговый бой кампании (`RankedChallengeService`, `CampaignPage`) — только
  потребители; их логика не здесь, рейтинговый бой читает ангар через `isEmpty` и `createUserSignature`.
- `BattlefieldUserComponent` (`model/battlefield/BattlefieldUserComponent.java:33-35`) — слушает
  `HANGAR_UPDATE` и обновляет команду в сервисе Battlefield. Серверный пересчёт боя кампании замену
  во время боя не учитывает: ГДД фиксирует расхождение как отложенное
  ([#gdd-battle-replace](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-battle-replace)).
- `BattlefieldPage ""` (`pages/ws/ingame/BattlefieldPage.java:19`) — `hangar: apiResponse()`.
- `User.profileOverview` (`User.java:543-556`, роут `/ingame/profile`) — `tanks: getFullTanksJSON()`
  и `tanksPower: TankUtils.getUserPower` — сумма мощности всех танков сумки, включая танки вне слотов
  ангара ([bag-gdd#gdd-power](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-power)).
- Сумка как замена ангара: `AssemblyUserComponent.generateReward` (`:68-80`, минимальный ранг среди
  танков сумки) считает, что в сумке лежат ровно танки ангара ([#tradeoffs](#tradeoffs) п.6).

<a id="dev-tools"></a>
### Dev-роуты

Dev-роутов ангара в `DevToolsPage` (`pages/ws/ingame/dev/DevToolsPage.java`) нет. Ангар меняется
только через реальные источники ([#producers](#producers)); `/trainAddSchemes` даёт схемы для
призыва. `/battleTestData` создаёт танки для теста боя, не трогая ни сумку, ни ангар.

<a id="client-contract"></a>
### Контракт с клиентом

**Роуты, где сервер отдаёт ангар:**

| Роут | Поле | Формат |
|---|---|---|
| `/ingame/home` | `hangar` | `{tanks: [{position: 0–11 (слот N = N−1), tankUid: string \| null}] ×12}` |
| `/ingame/home/hangar` | `hangar` | то же |
| `/ingame/battlefield` | `hangar` | то же |
| `/ingame/profile` | `tanks`, `tanksPower` | `[{position, tank: TankJSON \| null}] ×12`; число |
| `/ingame/train/summon`, `/ingame/assembly/compare`, `/ingame/collections/experimentalTank/compareReward` | `replaceableTank` | `TankJSON` или `null` |

**Push-событий у ангара нет.** `UserEmitterId.HANGAR_UPDATE` — внутреннее событие сервера, клиенту
не уходит. Клиент сам перезапрашивает `/ingame/home/hangar` по своему локальному событию
`GameEvents.HANGAR_UPDATE`, которое шлёт после «взять» в поезде, сборке и экспериментальных танках.
Танки по `tankUid` клиент берёт из своей копии сумки, которую обновляет push сумки
([bag-architecture.md#client-contract](bag-architecture.md#client-contract)).

Клиентские потребители (для сверки `client-analyst-lead`): `HangarJSON`/`TankPositionJSON` в
`src/views/home_screen/home.d.ts`, `HomeScreen.ts` (`onHangarUpdate`, запрос `/ingame/home/hangar`),
`BattlefieldPopup.ts`, `AssemblyPopup.ts`, `CollectionExperimentalTank.ts`, `profile.d.ts`.

Не проверено: сериализация `ObjectId` в `tankUid` строкой (клиентский тип — `string`).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Решения пользователя:

- 2026-10-17: расстановку в ангаре и на аэродроме не объединять; баг п.1 исправлять в обеих копиях.
- 2026-10-17: «потерянный» `uid` — слот считается свободным, серебро не платится
  ([#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement)); вместе с исправлением — разовый скрипт чистки сирот в
  сумке (п.1).
- 2026-10-17: лёгкие и ПТ-САУ в одном ряду вытесняют друг друга — задумано, как в коде (п.4).
- 2026-10-17: танк-награда через `User.addItem` — открытый вопрос ГДД
  ([#gdd-open](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-open), п.6).

Строки — `HangarUserComponent.java`, если не указано иное. Приоритеты — для отложенных исправлений.

1. **«Потерянный» `uid` отправляет танк в слот 1.** Статус: баг, приоритет высокий, исправление
   решено, не сделано. Если все слоты ряда заняты, но `uid` одного из них не найден в сумке:
   `getReplaceableTank` → `null` (`:45-52`), `getEmptyPosition` → `−1` (слот с `uid` считается
   занятым, `:107`), и `addTank` пишет танк в `position` 0, то есть в слот 1 (`:75-77`). Расходится с
   [#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement) («слот с отсутствующим в сумке танком считается свободным,
   серебро не начисляется»). Последствия:
   - лёгкий, средний или ПТ-танк встаёт в ряд тяжёлых, нарушая
     [#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots);
   - танк, стоявший в слоте 1, теряет слот, но остаётся в сумке: в бой не идёт, мощность
     игрока считает;
   - «потерянный» слот так и остаётся занятым, поэтому каждый следующий танк этого ряда снова
     уходит в слот 1;
   - вызывающие получают `replaceableTank = null`: окно сравнения показывает «свободное место»,
     серебро за замену не платится, `BETTER_TANK` засчитывается.
   Как `uid` теряется: ангар и сумка сохраняются раздельно ([#persistence](#persistence)), танк может
   стать недоступным (`isAvailable`). Тот же код — `AerodromeUserComponent.addAirplane`
   ([aerodrome-architecture.md#tradeoffs](aerodrome-architecture.md#tradeoffs) п.1).
   Исправление (решение 2026-10-17): `getEmptyPosition` считает свободным слот, чей `uid` не найден
   в сумке; серебро за такой слот не платится (заменяемого нет). Вместе с ним — разовый скрипт
   чистки сирот в сумке по образцу `CleanupAerodrome` (танки вне слотов ангара). Копии ангара и
   аэродрома остаются раздельными, правка — в обеих.
2. **Результат `BagUserComponent.add` не проверяется** (`:73`, `:78-79`). Заменяемый танк удаляется
   до `add`; если `add` откажет (повторная выдача объекта, уже лежащего в сумке), `itemAddInfo.item ==
   null` и `NullPointerException` на `:79` — заменённый танк потерян, новый не поставлен.
   Статус: баг-риск, приоритет низкий
   ([bag-architecture.md#tradeoffs](bag-architecture.md#tradeoffs) п.7).
3. **Переход «взять танк» собран у вызывающих** (WF `#no-implicit-order`, `#gdd-function-mapping`).
   Одно правило [#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement)
   («заменить слабейшего, 10 серебра», плюс квесты у источников) выражено тремя наборами шагов с разной полнотой:
   `TrainPage.actionAccept` (`TrainPage.java:115-157`), `ExperimentalTanksSectionType.takePendingTank`
   (`ExperimentalTanksSectionType.java:274-292`), `AssemblyUserComponent.takeTankReward` (`:226`, без серебра и квестов). Порядок
   «`getReplaceableTank` → серебро → `addTank`» держится на дисциплине вызывающих: заменяемый
   вычисляется дважды, и если между вызовами ангар изменится, серебро заплатят не за тот танк.
   Кандидат — метод-переход у ангара, который возвращает заменённый танк. Статус: как в коде,
   приоритет средний.
4. **Лёгкие и ПТ-САУ делят ряд 9–12 и заменяют друг друга.** Не проблема: задумано, ГДД
   фиксирует «лёгкие и ПТ вместе» ([#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots),
   [#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement)). `TYPE_POSITION` (`TankType.java:17,20`) даёт обоим типам
   одни слоты, `getReplaceableTank` ищет слабейшего по ряду без учёта типа. Статус: как в коде,
   исправлять не нужно.
5. **Число слотов задано дважды**: `POSITIONS = 12` (private, `:22`) и литерал `12` в
   `User.createTeam` (`User.java:348`). Статус: как в коде, приоритет низкий.
6. **Сумка считается равной ангару, но это не гарантировано.** `TankUtils.getUserPower`,
   `AssemblyUserComponent.generateReward` (`:68-80`) перебирают все танки сумки. Танки вне слотов
   появляются из-за п.1 и, возможно, из наград через `User.addItem` (открытый вопрос
   [#gdd-open](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-open)). Для самолётов эту же
   проблему закрыл разовый скрипт `CleanupAerodrome`; для танков аналога нет — его добавляют вместе
   с исправлением п.1 (решение 2026-10-17). Статус: баг-риск, приоритет средний.
7. **Кандидаты на удаление**: пустой `modifyReceiver` (`:30-32`); `TankType.POSITION_TYPE`
   (`TankType.java:23-36`) — в серверном коде не используется; ветка `-1` в `getCurrentPosition`
   (`:102`) для заменяемого танка недостижима, он всегда взят из слота. Статус: как в коде,
   приоритет низкий.
8. **Мелочи стиля**: `getOrDefault(position, null)` вместо `get` (`:44, :86, :94, :107, :126, :144`);
   `replaceableTank = null` перед `break` (`:46, :51`) — уже `null` по смыслу возврата. Статус: как в
   коде, приоритет низкий.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [hangar-gdd.md](/workspace/client/.claude/docs/game-design/hangar-gdd.md). Правила ГДД, которые реализует сервер, и где.

| Раздел ГДД | Реализация |
|---|---|
| [#gdd-slots](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-slots) — 12 слотов, 3 ряда, лёгкие и ПТ в одном ряду, слот N = `position` N−1, нельзя переставлять и снимать | `TankType.TYPE_POSITION`, `POSITIONS`; отсутствие роутов перестановки |
| [#gdd-placement](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-placement) — первый свободный слот или замена слабейшего ряда, удаление заменённого, 10 серебра | `getReplaceableTank`, `addTank`, `getEmptyPosition`; серебро и квесты у вызывающих ([#producers](#producers)); «потерянный» `uid` — расхождение, [#tradeoffs](#tradeoffs) п.1 |
| [#gdd-compare-window](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-compare-window) | сервер отдаёт только `replaceableTank` ([#client-contract](#client-contract)); окно — клиент |
| [#gdd-hangar-view](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-hangar-view) | `HomePage` `""` и `/hangar`, `apiResponse`, `getFullTanksJSON` |
| [#gdd-tank-info](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-tank-info) | клиентская часть; сервер отдаёт `Tank.apiResponse()` в профиле |
| [#gdd-battle-replace](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-battle-replace) | `HANGAR_UPDATE` → `BattlefieldUserComponent`; серверный пересчёт боя замену не учитывает (отложено в ГДД) |
| [#gdd-open](/workspace/client/.claude/docs/game-design/hangar-gdd.md#gdd-open) — танк-награда через `User.addItem` | не реализовано: танк идёт только в сумку ([#producers](#producers)) |
| [campaign-gdd#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield) — слот N ангара = слот N поля | `User.createTeam` |
| [bag-gdd#gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles) — заменённый удаляется насовсем | `addTank` → `addCount(-1)` |
| [bag-gdd#gdd-power](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-power) — мощность игрока по сумке | `TankUtils.getUserPower` в профиле |

Функции с одним смыслом под разными именами в области нет: правило замены выражено парой
`getReplaceableTank`/`addTank`; сборка перехода у трёх вызывающих — [#tradeoffs](#tradeoffs) п.3.

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути — от корня репозитория `/workspace/server`; `…/game/` = `game/src/main/java/com/linkedgames/game/`.

### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `…/game/model/hangar/HangarUserComponent.java` | компонент: слоты танков, замена, JSON, БД |
| `…/game/pages/ws/ingame/HomePage.java` | роут `/ingame/home/hangar`, блок `hangar` в `/ingame/home` |

### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `…/game/model/user/User.java` | регистрация, загрузка `Hangar`, `createTeam`, `profileOverview` |
| `…/game/model/user/UserEmitterId.java` | константа `HANGAR_UPDATE` |
| `…/game/model/bag/tank/TankType.java` | зависимость: `TYPE_POSITION` — слоты по типу |
| `…/game/model/bag/tank/Tank.java` | зависимость: `getPower`, `addCount`, `apiResponse` |
| `…/game/model/bag/tank/TankUtils.java` | `tanksPower` в профиле (по сумке) |
| `…/game/model/bag/BagUserComponent.java` | зависимость: `getTank(uid)`, `add` |
| `…/game/model/bag/utils/ItemAddInfo.java` | зависимость: `uid` добавленного танка |
| `…/game/pages/ws/ingame/TrainPage.java` | `/summon` (сравнение), `/accept` (постановка) |
| `…/game/pages/ws/ingame/AssemblyPage.java` | `/compare` — заменяемый танк |
| `…/game/model/assembly/AssemblyUserComponent.java` | `takeTankReward` → `addTank`; `generateReward` по танкам сумки |
| `…/game/pages/ws/ingame/CollectionExperimentalTankPage.java` | `/compareReward` — заменяемый танк |
| `…/game/model/collections/sectionList/ExperimentalTanksSectionType.java` | `takePendingTank` → `addTank` |
| `…/game/model/train/TrainUserComponent.java` | `getSilverCoinsReward` (10 серебра за заменённый танк) |
| `…/game/model/battlefield/BattlefieldUserComponent.java` | слушает `HANGAR_UPDATE`, команда в Battlefield |
| `…/game/pages/ws/ingame/BattlefieldPage.java` | `hangar` в ответе, `createTeam` |
| `…/game/service/campaign/RankedChallengeService.java` | рейтинговый бой кампании: `touch` проверяет `isEmpty` (область не документируется здесь) |
| `…/game/model/battle/data/BattleDataFactory.java` | `createTeam` для боя кампании; `TYPE_POSITION` для бота |
| `…/game/pages/ws/ingame/ProfilePage.java` | роут `/ingame/profile` → `profileOverview` |
| `…/game/pages/WSRouter.java` | монтирование `/ingame/home` |
| `…/game/model/aerodrome/AerodromeUserComponent.java` | копия логики расстановки (самолёты), правки — в обеих |
