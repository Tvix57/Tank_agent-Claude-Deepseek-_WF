# Кампания — уровни, бои с ботом, награды (сервер)

ГДД: [/workspace/client/.claude/docs/game-design/campaign-gdd.md](/workspace/client/.claude/docs/game-design/campaign-gdd.md)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду (код в рамках
> задачи не менялся), 2026-10-15. Всё ниже подтверждено чтением кода, запуском не проверялось.
> Клиентская сторона (как клиент проигрывает бой и вызывает роуты) не проверялась — её разбирает
> `client-analyst-lead`, сверка контракта будет через `integration-lead`.
>
> **Актуализация 2026-10-19** (merge `origin/amnesia/fix` в `koba/collection`, не закоммичен): добавлен
> рейтинговый бой (`/battle` теперь идёт через `RankedChallengeService`), `completeBattle()` возвращает
> `CampaignBattleResult`, удалены все туториальные ветки (`TutorialSteps` и бот туториала удалены),
> схемы за танк только танковые, добавлены роуты `/rankedRating`, `/rankedHistory*`. Подтверждено
> чтением кода, запуском не проверялось.
>
> Фича airDrop (ящики с золотом) живёт в том же `CampaignUserComponent`/`CampaignPage`, но описана
> отдельно: [airdrop-architecture.md](airdrop-architecture.md). Здесь airDrop не повторяется.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
   - [Модель прогресса: уровень, регион, глава, миссия](#progress-model)
   - [Жизненный цикл боя кампании](#battle-flow)
   - [Награды кампании](#rewards)
   - [Сложность бота](#bot-difficulty)
   - [Рейтинговый бой (только ссылка)](#ranked)
   - [Баланс: откуда берутся числа](#balance)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`CampaignUserComponent`](#cls-campaignusercomponent)
   - [`CampaignBattle`](#cls-campaignbattle)
   - [`CampaignFighter`](#cls-campaignfighter)
   - [`CampaignBattleResult`](#cls-campaignbattleresult)
   - [`CampaignPage`](#cls-campaignpage)
   - [`BattleDataFactory`, `BattleFighterData`, `BattleData` (бой кампании)](#cls-battledatafactory)
   - [`DevToolsPage` (dev-роуты уровня)](#cls-devtoolspage)
   - [Потребители уровня кампании](#consumers)
   - [Персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)
    - [Файлы прямого влияния](#file-map-direct)
    - [Файлы косвенного влияния](#file-map-indirect)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Кампания — PvE-режим: игрок последовательно проходит уровни, каждый уровень — бой его команды
(танки ангара и самолёты аэродрома) с ботом. Часть вызовов `/battle` заменяется рейтинговым боем с
другим игроком ([#ranked](#ranked)); уровень кампании он не меняет. Победа поднимает уровень на 1, каждые 5 уровней
(смена главы) дают 50 золотых монет. Во время боя за каждый уничтоженный вражеский танк начисляется
серебро (с минутным лимитом) и с шансом 10% схема танка; уничтоженные танки и самолёты
двигают квесты и достижения.

Сервер авторитетен в итоге боя: клиент проигрывает бой у себя и сообщает `win`, но при заявленной
победе сервер сам эмулирует тот же бой по тем же данным и seed и засчитывает уровень только при
своей победе. Награды за уничтожение отдельных юнитов при этом считаются по сообщениям клиента без
проверки (см. [#tradeoffs](#tradeoffs)).

<a id="progress-model"></a>
### Модель прогресса: уровень, регион, глава, миссия

ГДД: [#gdd-terms](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-terms), [#gdd-levels](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-levels).

Хранится одно число `level` (0..`TOTAL_LEVELS` = 10000, по умолчанию 0). Остальное вычисляется:

| Величина | Формула | Пример для `level = 57` |
|---|---|---|
| регион | `level / 50` | 1 |
| глава | `level / 5` (сквозная, не внутри региона) | 11 |
| миссия | `level - глава * 5` (0..4) | 2 |

Отдельных сущностей "регион"/"глава"/"миссия" на сервере нет: ни данных, ни разблокировок.

<a id="battle-flow"></a>
### Жизненный цикл боя кампании

ГДД: [#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield), [#gdd-level-transition](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-level-transition), [#gdd-defeat](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-defeat).

1. **`/battle`** — `RankedChallengeService.touch(user)`, затем: если у игрока уже есть незавершённый
   рейтинговый бой (`hasRankedBattle()`) — тот же `battleData` уходит клиенту повторно
   (`getCurrentBattle()`); иначе решение о виде боя принимает `RankedChallengeService.createBattle`
   (см. [#ranked](#ranked)). Обычный бой: `createBattle()` собирает `BattleData`: новый `uid`,
   случайный seed, боец-игрок (`createFighterFromUser`, текущая команда) и боец-бот
   (`createFighterBotFromUser`, команда по уровню кампании). Данные хранятся в `battleData` только в
   памяти и целиком уходят клиенту. Предыдущий незавершённый обычный бой молча перезаписывается.
2. **Во время боя** клиент шлёт `/battleTankReward` (уничтожен вражеский танк) и
   `/battleAirplaneReward` (уничтожен самолёт). Эти роуты с `battleData` не связаны, см.
   [#rewards](#rewards).
3. **`/battleResult`** с `win`:
   - `win: false` при отсутствии рейтингового боя — ответ с текущим `campaign`, бой не эмулируется,
     `battleData` остаётся в памяти до следующего `/battle`. При рейтинговом бое флаг `win`
     игнорируется, бой эмулируется всегда;
   - иначе — `completeBattle()`: эмуляция `CampaignBattle` тиками по 16 мс до конца боя;
     `battleData` и признак рейтингового боя сбрасываются в `finally`. Нет `battleData` (бой не
     создавался или компонент пересоздан) — ответ с текущим `campaign` без ошибки.
   - Рейтинговый результат (`CampaignBattleResult.isRanked()`) — передаётся в
     `RankedChallengeService.applyBattleResult`, уровень кампании не меняется
     ([#ranked](#ranked)).
   - Обычный результат: победа = игрок стал победителем эмуляции → `levelCompeted(true)`: уровень +1,
     квестовое событие `CAMPAIGN_LEVEL_UP`, при смене главы — награда (см. [#rewards](#rewards)).
     При включённом dev-режиме (`app.devTools`) в ответ добавляется полный лог эмуляции `battleResult`.

<a id="rewards"></a>
### Награды кампании

ГДД: [#gdd-kill-reward](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-kill-reward), [#gdd-chapter-reward](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-chapter-reward).

| Награда | Где | Условие |
|---|---|---|
| 5 серебра за танк | `CampaignPage.actionBattleTankReward` | лимит 300 серебра на серию, см. [`getSilverCoinsReward`](#m-getsilvercoinsreward); при лимите не выдаётся ничего, в том числе схемы и прогресс квестов/достижений |
| схема танка | там же | шанс 100 из 1000, только если серебро выдано; схемы самолёта кампания больше не выдаёт (расхождение с ГДД, см. [#tradeoffs](#tradeoffs) п.16) |
| 50 золотых монет за главу | `CampaignUserComponent.levelCompeted` | победа сменила главу, то есть каждые 5 уровней |
| награда за регион | `levelCompeted` | ключ `regionRewards` есть, но список всегда пуст |
| награды уровня (`/levelRewards`) | `CampaignUserComponent.levelRewards` | заглушка, всегда пустой список |
| золото airDrop | см. [airdrop-architecture.md](airdrop-architecture.md) | — |

Прогресс квестов (`TANK_DESTROY`, `AIRPLANE_DESTROY`, `SILVER_COINS_GAINED`,
`BATTLE_SILVER_COINS_GAINED`, `CAMPAIGN_LEVEL_UP`) описан в
[quests-architecture.md#progress-sources](quests-architecture.md#progress-sources), прогресс
достижений — в [achievements-architecture.md#progress-sources](achievements-architecture.md#progress-sources).
Как начисляются ресурсы в сумку — [bag-architecture.md#m-add](bag-architecture.md#m-add).

<a id="bot-difficulty"></a>
### Сложность бота

ГДД: [#gdd-enemy-tanks](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-enemy-tanks), [#gdd-enemy-airplanes](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-enemy-airplanes).

`BattleDataFactory.createBotTeam(campaignLevel)` строит команду бота детерминированно по уровню
(кроме выбора конкретной модели, она случайна среди подходящих по позиции):

- танков: `1 + level / 2` до уровня 22, дальше 12; самолётов: `1 + level / 4` до уровня 20,
  дальше 8;
- параметры растут "по очереди": каждые N уровней одна из 12 позиций получает +1 (`getParam`):
  уровень танка — каждые 8 уровней (в пределах `TankData.MIN_LEVEL..MAX_LEVEL`), звезда танка —
  каждые 17, ранг танка — каждые 84; звезда самолёта — каждые 25, ранг самолёта — каждые 125;
  ранг выше доступного для техники обрезается до последнего доступного;
- модель — случайная из `Balance.getTanks(rank)`/`getAirplanes(rank)`, тип которой допустим на
  позиции (`TankType.TYPE_POSITION`/`AirplaneType.TYPE_POSITION`). Данные техники —
  [tank-airplane-data-architecture.md](tank-airplane-data-architecture.md).

Бота туториала (`createTutorialBotTeam`) в коде больше нет: бот всегда строится по уровню кампании.

<a id="ranked"></a>
### Рейтинговый бой (только ссылка)

Область не документируется здесь. Связь с кампанией: `CampaignPage./battle` вызывает
`RankedChallengeService.createBattle`; актор (`service/campaign/RankedChallengeActor`) с шансом
`CHANCE` ищет соперника по рейтингу и, если находит, собирает бойцов (`BattleFighterData` с
`leagueId/rating/place`) и вызывает `CampaignUserComponent.createRankedBattle(a, b)`; иначе
`createBattle()` обычного боя. Результат `/battleResult` рейтингового боя применяет
`RankedChallengeService.applyBattleResult` (рейтинг, история, `LeagueMeta`). Роуты страницы
`/rankedRating`, `/rankedHistory`, `/rankedHistoryStatus`, `/rankedHistoryRead` — только маршрутизация
в `RankedChallengeService`/`RankedChallengeHistoryDao`.

<a id="balance"></a>
### Баланс: откуда берутся числа

Все числа захардкожены в коде, в `balance.json` кампании нет:

- `CampaignUserComponent`: `TOTAL_LEVELS = 10000`, `MISSIONS_PER_CHAPTER = 5`,
  `MISSIONS_PER_REGION = 50`, `CHAPTER_GOLDEN_COINS_REWARD` (50 золота), `SILVER_REWARD = 5`,
  `SILVER_LIMIT_PER_MINUTE = 300`, `SCHEMES_CHANCE = 100` (из 1000);
- `BattleDataFactory.createBotTeam`: пороги числа юнитов и шаги роста параметров (см.
  [#bot-difficulty](#bot-difficulty)).

<a id="references"></a>
## 2. Референсы

- [airdrop-architecture.md](airdrop-architecture.md) — вторая часть того же компонента; раздел
  `#campaign-context` там кратко описывает компонент, полное описание — этот документ.
- `RankedChallengeService` / `RankedChallengeActor` (`service/campaign`) — рейтинговый бой поверх того же
  `CampaignUserComponent.battleData`; в этом документе только граница, см. [#ranked](#ranked).
- `BattlefieldBattle` (`model/battlefield`) — другой наследник `Battle` (PvP в реальном времени);
  `CampaignBattle` устроен так же, но без реального времени и без ограничения длительности.

<a id="patterns"></a>
## 3. Паттерны

- **`UserChildComponent` с ленивым созданием** — `User.getCampaignComponent()`, персистентность в
  поддокументе `Campaign` пользователя через `changedField` + `dbMappingBuild` (подробно —
  агент `server-developer-db-persistence`).
- **Вычисляемые производные** — регион/глава/миссия не хранятся, считаются из `level`.
- **Детерминированная серверная эмуляция по seed** — клиент и сервер проигрывают один и тот же
  `BattleData` (комментарий в `BattleData`: "на одинаковом seed обе стороны должны показать
  одинаковый результат"); сервер эмулирует только заявленную победу.
- **Состояние только в памяти** — `battleData` и счётчики лимита серебра не сохраняются: бой и лимит
  живут, пока жив объект пользователя.
- **Шаблон награды** — `Resource.createNew(id, true)` с `EMPTY_UID`; сумка сама копирует шаблон при
  добавлении ([bag-architecture.md#m-add](bag-architecture.md#m-add)), поэтому статический
  `CHAPTER_GOLDEN_COINS_REWARD` безопасно переиспользуется.

<a id="class-list"></a>
## 4. Список классов

Ниже — все классы, составляющие компонент (без airDrop-классов).

Пакет `com.linkedgames.game.model.campaign`: `CampaignUserComponent`, `CampaignBattle`,
`CampaignFighter`, `CampaignBattleResult` (новый). Страница: `pages.ws.ingame.CampaignPage`. Части других классов, работающие на
кампанию: `BattleDataFactory` (боты), `BattleFighterData`/`BattleData` (рейтинг бойца, мощность, поиск
бойца), `Battle.getAnyOpponent`, `DevToolsPage` (dev-роуты уровня), `User` (создание,
загрузка, receiver).

<a id="anchors"></a>
## 5. Навигация (якоря)

Разделы: [#purpose](#purpose), [#progress-model](#progress-model), [#battle-flow](#battle-flow),
[#rewards](#rewards), [#bot-difficulty](#bot-difficulty), [#ranked](#ranked), [#balance](#balance),
[#consumers](#consumers), [#persistence](#persistence), [#client-contract](#client-contract),
[#tradeoffs](#tradeoffs), [#gdd-link](#gdd-link), [#file-map](#file-map).
Методы: [#m-getsilvercoinsreward](#m-getsilvercoinsreward), [#m-levelcompeted](#m-levelcompeted),
[#m-createbattle](#m-createbattle), [#m-completebattle](#m-completebattle),
[#m-levelrewards](#m-levelrewards), [#m-changelevel](#m-changelevel),
[#m-actionbattleresult](#m-actionbattleresult), [#m-actionbattletankreward](#m-actionbattletankreward).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `CampaignUserComponent` | [#cls-campaignusercomponent](#cls-campaignusercomponent) |
| `CampaignBattle` | [#cls-campaignbattle](#cls-campaignbattle) |
| `CampaignFighter` | [#cls-campaignfighter](#cls-campaignfighter) |
| `CampaignBattleResult` | [#cls-campaignbattleresult](#cls-campaignbattleresult) |
| `CampaignPage` | [#cls-campaignpage](#cls-campaignpage) |
| `BattleDataFactory`, `BattleFighterData`, `BattleData` | [#cls-battledatafactory](#cls-battledatafactory) |
| `DevToolsPage` | [#cls-devtoolspage](#cls-devtoolspage) |
| `User`, `HomePage`, `TrainPage`, `RatingCampaignService`, `PlayerListService`, `QuestData` | [#consumers](#consumers) |

## 7. Классы и методы

<a id="cls-campaignusercomponent"></a>
### `CampaignUserComponent`

`game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java`, наследник
`UserChildComponent`, `APIResponseStd`. Создаётся лениво в `User.getCampaignComponent()` с именем
`"Campaign"`. Поля кампании: `level` (в БД), `battleData`, `lastRewardTime`, `currentRewardGiven`,
`rankedBattle` (в памяти). Поля и методы airDrop — [airdrop-architecture.md#cls-campaignusercomponent](airdrop-architecture.md#cls-campaignusercomponent).

Тривиальные: `getLevel()`; `getRegion()`, `getChapter()`, `getMission()` — формулы из
[#progress-model](#progress-model); `getNextLevel()` (private) — `min(level + 1, TOTAL_LEVELS)`;
`addLevel()` — `level = getNextLevel()` + `changedField`; `removeLevel()` — `max(level - 1, 0)` + ГДД: [#gdd-levels](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-levels).
`changedField`, нигде не вызывается; `modifyReceiver` — пустой; `apiResponse()` —
`{level, region, chapter, mission}`.

<a id="m-getsilvercoinsreward"></a>
**`int getSilverCoinsReward()`** — выдаёт право на серебро за уничтоженный танк и сразу списывает его
из лимита. Если с `lastRewardTime` прошло больше 60 с — счётчик `currentRewardGiven` обнуляется.
Если `currentRewardGiven + 5 > 300` — возвращает 0 (лимит). Иначе `lastRewardTime = now`, счётчик
+5, возвращает 5. `lastRewardTime` обновляется при каждой выдаче, поэтому окно отсчитывается от
последней награды (см. [#tradeoffs](#tradeoffs) п.3). Геттер с побочным эффектом: повторный вызов
тратит лимит. ГДД: [#gdd-kill-reward](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-kill-reward).

<a id="m-levelcompeted"></a>
**`JSONObject levelCompeted(boolean isWin)`** — итог победы. При `isWin == false` — `null`. Иначе
запоминает регион и главу, `addLevel()`, `triggerEvent(CAMPAIGN_LEVEL_UP, level)`. Глава не
сменилась — `null`. Сменилась — кладёт в сумку `CHAPTER_GOLDEN_COINS_REWARD` (50 золота) и
возвращает `{chapterRewards: [награда]}`; если сменился и регион — дополнительно
`regionRewards: []`. ГДД: [#gdd-levels](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-levels), [#gdd-chapter-reward](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-chapter-reward).

<a id="m-levelrewards"></a>
**`JSONObject levelRewards(int level)`** — заглушка: параметр игнорируется, возвращает Правила в ГДД нет: награды за уровень по ГДД нет, метод — заготовка (решение пользователя 2026-10-15).
`{rewards: []}`, никогда `null`.

<a id="m-createbattle"></a>
**`JSONObject createBattle()`** — обычный бой: новый `BattleData` (`new ObjectId()`, `initSeed()`), боец-игрок ГДД: [#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield).
`createFighterFromUser`, боец-бот `createFighterBotFromUser`; сохраняет в `battleData`, возвращает
`battleData.apiResponse()`.

**`JSONObject createRankedBattle(BattleFighterData a, BattleFighterData b)`** — выставляет
`rankedBattle = true`, новый `BattleData` с seed и двумя готовыми бойцами, возвращает
`apiResponse()`. Вызывается из `RankedChallengeActor`, а не из страницы. Комментарий в коде:
пока рейтинговый бой не завершён, новый `battleData` не генерируется.
**`boolean hasRankedBattle()`** — `rankedBattle && battleData != null`.
**`JSONObject getCurrentBattle()`** — `battleData.apiResponse()` или `null`.

<a id="m-completebattle"></a>
**`CampaignBattleResult completeBattle()`** — нет `battleData` — `null`. Иначе создаёт
`CampaignBattle`, крутит `update(Battle.TICK_TIME)` пока `!isEnded()`. Обычный бой —
`CampaignBattleResult.regular(battle)`. Рейтинговый — `ranked(battle, user().id, ...)` с рейтингом и
мощностью (`BattleFighterData.getPower()`) победителя и проигравшего из `battleData`. В `finally`
всегда `battleData = null`, `rankedBattle = false` (ранние выходы не оставляют состояние). ГДД: [#gdd-defeat](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-defeat), [#gdd-levels](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-levels).

<a id="m-changelevel"></a>
**`void changeLevel(int deltaLevel)`** — сдвиг уровня на дельту с обрезкой в `0..TOTAL_LEVELS` +
`changedField`. Вызывается только из dev-роутов; квестовое событие и наград не даёт.

`DBFields`: `LEVEL_FIELD = "level"` (+ четыре airDrop-поля, см. airDrop-документ).

<a id="cls-campaignbattle"></a>
### `CampaignBattle`

`model/campaign/CampaignBattle.java`, наследник `Battle`. Переопределяет только
`initData(BattleData)`: для каждого бойца создаёт `CampaignFighter`, все танки и самолёты из данных
добавляет юнитами с `RechargeMode.AUTO` (автоматическая перезарядка, без действий игрока). Флаги
реального времени и длительность (`setDuration`) не задаются.

<a id="cls-campaignfighter"></a>
### `CampaignFighter`

`model/campaign/CampaignFighter.java` — пустой наследник `Fighter` (только конструктор `uid, name`).
Точка расширения, своей логики нет.

<a id="cls-campaignbattleresult"></a>
### `CampaignBattleResult`

`model/campaign/CampaignBattleResult.java`, неизменяемый результат эмулированного боя:
`battle`, `attacker` (`null` для обычного боя), `winner`, `loser`, рейтинг и мощность победителя и
проигравшего до боя. Фабрики `regular(battle)` (нули) и `ranked(...)`; `isRanked()` = `attacker != null`.
Пустой вложенный класс `Member` не используется (мёртвый код). `loser` — `getAnyOpponent` победителя.

<a id="cls-campaignpage"></a>
### `CampaignPage`

`pages/ws/ingame/CampaignPage.java`, наследник `AuthorizedUserPage`, зарегистрирована в `WSRouter`
как `/ingame/campaign`. Роуты кампании — ниже; `/sendAirDrop`, `/getAirDrop` —
[airdrop-architecture.md#cls-campaignpage](airdrop-architecture.md#cls-campaignpage).

- **`/battle` (`actionBattle`)** — `RankedChallengeService.touch`, повтор текущего рейтингового боя
  или `RankedChallengeService.createBattle`, см. [#battle-flow](#battle-flow); ответ `{battle}`
  уходит из страницы или из актора.
- **`/rankedRating`, `/rankedHistory`, `/rankedHistoryStatus`, `/rankedHistoryRead`** — рейтинговая
  таблица (`page`, по умолчанию 1), история боёв (сборка подписей через `UserSignatureCollectorTask`),
  флаг непрочитанного (`revision > readRevision`), отметка прочитанного (`revision`). Только
  маршрутизация, логика в рейтинговом сервисе и `RankedChallengeHistoryDao`.
- **`/battleAirplaneReward` (`actionBattleAirplaneReward`)** — `AIRPLANE_DESTROY` +1, достижение по ГДД: [#gdd-kill-reward](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-kill-reward).
  `airplaneId` из запроса без проверки; ответ пустой `ok`. Наград нет.
- **`/levelRewards` (`actionLevelRewards`)** — `levelRewards(level)`; ветка `error()` при `null`
  недостижима. Ответ `{rewards: {rewards: []}}` (вложенность двойная).

<a id="m-actionbattletankreward"></a>
**`/battleTankReward` (`actionBattleTankReward`)** — бизнес-логика награды за танк собрана в
странице: `getSilverCoinsReward()`; 0 — пустой `ok` и выход (ни квестов, ни достижений, ни схем).
Иначе серебро в сумку, квесты `BATTLE_SILVER_COINS_GAINED`, `SILVER_COINS_GAINED`, `TANK_DESTROY`,
достижение по `tankId` без проверки, затем ролл схемы (`1..1000 <= SCHEMES_CHANCE`), выдаётся только схема танка. Ответ `{rewards: [...]}`. ГДД: [#gdd-kill-reward](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-kill-reward).

<a id="m-actionbattleresult"></a>
**`/battleResult` (`actionBattleResult`)** — по [#battle-flow](#battle-flow) п.3: ранний выход при
`win: false` без рейтингового боя, иначе `completeBattle()`; рейтинговый результат уходит в
`RankedChallengeService.applyBattleResult(pageProcessor, result, campaign)` и страница на этом
заканчивает (ответ формирует актор, `campaign` берётся из `apiResponse()`); обычный — сравнение
`user.id` с победителем, `levelCompeted(isWin)`, ответ `{campaign, rewards?, battleResult?}`.

<a id="cls-battledatafactory"></a>
### `BattleDataFactory`, `BattleFighterData`, `BattleData` (бой кампании)

`model/battle/data/BattleDataFactory.java`. Для кампании важны `createFighterFromUser`,
`createFighterBotFromUser` (uid бота `new ObjectId(new Date(0))`, команда по
уровню), `createBotTeam(campaignLevel)` и `getParam` — см. [#bot-difficulty](#bot-difficulty).
`createTutorialBotTeam` удалён, `createFighterBotFromUser` больше не ветвится по туториалу.
`createFighterBot(UserSignature, campaignLevel)` вызывается вне кампании (тот же `createBotTeam`).
`BattleFighterData` получил `leagueId = -1`, `rating`, `place` (`setRanking`), `getPower()` (сумма
мощности танков и самолётов) и в `apiResponse()` поля `name` и, при `leagueId != -1`, `ranking
{leagueId, rating, place}`. `BattleData.getFighter(uid)` ищет бойца или `null`;
`Battle.getAnyOpponent(fighter)` — синоним `initOpponent` для 1 на 1. Используются рейтинговым боем.

<a id="cls-devtoolspage"></a>
### `DevToolsPage` (dev-роуты уровня)

`pages/ws/ingame/dev/DevToolsPage.java`: `/campaignAddLevel` и `/campaignRemoveLevel` —
`changeLevel(±value)`, ответ `{campaign}`. airDrop dev-роуты — в airDrop-документе.

<a id="consumers"></a>
### Потребители уровня кампании

- `User` — ленивое создание, `modifyReceiver`, загрузка поддокумента `Campaign`
  (`P_CAMPAIGN_FIELD`), `campaignLevel` в обзоре профиля (`profileOverview`).
- `HomePage` — `campaign` (`apiResponse()`) в `/ingame/home` и `/ingame/home/campaign`.
- `TrainPage` — `campaignLevel` в ответе с шансами рангов (только для показа). `AerodromePage` на
  уровень кампании больше не ссылается.
- `RatingCampaignService` (рейтинг по уровню, роут `RatingPage /campaign`), `PlayerListService`
  (список онлайна) — уровень берётся в `User.onBasicInfoUpdate()`, то есть при входе и
  периодическом обновлении онлайна (раз в 2 минуты), а не при повышении уровня.
- `QuestData` — квест `CAMPAIGN_LEVEL_UP`: текущее значение = `level`, цель = `level + 1`
  ([quests-architecture.md#cls-questdata](quests-architecture.md#cls-questdata)).
- `BattleDataFactory` — уровень определяет команду бота.
- `RankedChallengeActor` — вызывает `createBattle()`/`createRankedBattle()` в потоке пользователя
  (`UserStore.access`) ([#ranked](#ranked)).

<a id="persistence"></a>
### Персистентность

Поддокумент `Campaign` документа пользователя: `level` (int, по умолчанию 0) плюс airDrop-поля.
Отдельной коллекции и индексов нет. `battleData`, `rankedBattle`, `lastRewardTime`, `currentRewardGiven` не
сохраняются: перезагрузка пользователя теряет незавершённый бой (в том числе рейтинговый) и сбрасывает
лимит серебра.

<a id="client-contract"></a>
### Контракт с клиентом

WS-роуты `/ingame/campaign/*` (клиентская сторона не сверялась):

| Роут | Запрос | Ответ (payload) |
|---|---|---|
| `/battle` | — | `battle: {uid, seed, fighters[], type}`; у бойца добавлены `name` и (рейтинговый бой) `ranking {leagueId, rating, place}` |
| `/battleTankReward` | `tankId` | `rewards?: [item]` (нет ключа — ничего не выдано) |
| `/battleAirplaneReward` | `airplaneId` | пусто |
| `/battleResult` | `win` | обычный бой: `campaign: {level, region, chapter, mission}`, `rewards?: {chapterRewards, regionRewards?}`, `battleResult?` (dev); рейтинговый — ответ актора, см. [#ranked](#ranked) |
| `/rankedRating` | `page?` | таблица (формирует актор) |
| `/rankedHistory` | — | `history[{opponent, opponentRating, opponentPower, loser, win, rating, ratingDelta, time}]`, `revision` |
| `/rankedHistoryStatus` | — | `hasUnreadHistory` |
| `/rankedHistoryRead` | `revision` | пусто |
| `/levelRewards` | `level` | `rewards: {rewards: []}` |
| `/ingame/home`, `/ingame/home/campaign` | — | `campaign` |
| `/ingame/devTools/campaignAddLevel`, `/campaignRemoveLevel` | `value` | `campaign` |

Push-событий у кампании нет. Ресурсы-награды дополнительно приходят обычными событиями сумки.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и подозрительные места

Явных комментариев о принятых компромиссах в коде нет, кроме "защиты от накрутки" через лимит
серебра. Ниже наблюдения по коду, требующие решения владельца. Пункты, уже описанные в смежных
документах, только перечислены ссылками.

1. **Награды за юнитов не привязаны к бою.** `/battleTankReward` и `/battleAirplaneReward`
   (`CampaignPage.actionBattleTankReward`/`actionBattleAirplaneReward`) не проверяют, что идёт бой
   (`battleData`) и что юнит в нём есть. Серебро ограничено лимитом, но каждый успешный вызов ещё и
   роллит схему танка: до 60 роллов за серию лимита, в среднем около 6 схем без единого боя.
   по ГДД (#gdd-kill-reward, решение пользователя 2026-10-15) — расхождение, исправление отложено.
2. **Уже описано в смежных документах:** непроверенные `tankId`/`airplaneId` и NPE на неизвестном id
   (`actionBattleTankReward`, `actionBattleAirplaneReward`) — [achievements-architecture.md#tradeoffs](achievements-architecture.md#tradeoffs);
   прогресс квестов и достижений теряется при лимите серебра (ветка `silverCoinsAmount == 0` в `actionBattleTankReward`) —
   [quests-architecture.md#tradeoffs](quests-architecture.md#tradeoffs) п.5 и achievements;
   Туториальные ветки в `CampaignPage`/`BattleDataFactory` удалены (раньше: выход из туториала в
   `/battle`, победа без эмуляции) — пункты [tutorial-architecture.md#tradeoffs](tutorial-architecture.md#tradeoffs)
   п.1–2 про кампанию стали неактуальны, правка того документа — не здесь.
3. **Лимит серебра — не "300 в минуту".** `getSilverCoinsReward`
   (`CampaignUserComponent`) сдвигает `lastRewardTime` при каждой выдаче, поэтому
   счётчик сбрасывается только после 60 с без наград. Игрок, уничтожающий танк чаще раза в минуту,
   упрётся в 300 за любую длительность серии, а затем ждёт до минуты. Имя константы
   `SILVER_LIMIT_PER_MINUTE` и комментарий говорят о минутном окне.
4. **Эмуляция боя без ограничения времени.** `completeBattle` крутит `while (true)`
   (теперь `while (!battle.isEnded())` в `completeBattle`), а `CampaignBattle` не задаёт `setDuration`
   (у `BattlefieldBattle` — 10 минут, `BattlefieldBattle.java:44`). Если бой не может закончиться,
   поток пользователя зависает. Сейчас не воспроизводилось; эмуляция идёт синхронно в обработчике
   запроса.
5. **Ничья засчитывается игроку.** Если обе стороны уничтожены в одном тике, победитель —
   `fightersList.get(0)` (`Battle.java:346-348`), а игрок добавляется первым (`createBattle`). В рейтинговом бою порядок
   бойцов задаёт актор (`createRankedBattle(ownerFighter, opponentFighter)`, владелец первым), значит
   ничья засчитывается владельцу.
6. **Перебор боёв.** `/battle` можно вызывать сколько угодно: каждый раз новый seed и новая
   случайная команда бота, и всё это уходит клиенту до боя (`createBattle`).
   Клиент может заранее проиграть бой у себя и играть только выигрышные.
   по ГДД (#gdd-defeat, решение пользователя 2026-10-15) — расхождение, исправление отложено.
7. **Тихий отказ при потерянном бое.** Победа без `battleData` (после перезагрузки пользователя или
   без `/battle`) возвращает `ok` с прежним `campaign` без признака ошибки
   (ветка `campaignBattleResult == null` в `actionBattleResult`); клиент, показавший победу, не узнает, почему уровень не вырос.
8. **Максимальный уровень.** На `TOTAL_LEVELS` победа не меняет уровень, но всё равно шлёт
   `CAMPAIGN_LEVEL_UP` (`levelCompeted`); квест `CAMPAIGN_LEVEL_UP` с целью
   `level + 1` (`QuestData`) на этом уровне невыполним.
   по ГДД (#gdd-levels, решение пользователя 2026-10-15) — расхождение, исправление отложено.
9. **Заглушки наград.** `levelRewards` игнорирует `level` и всегда отдаёт пустой список
   (`levelRewards`), проверка на `null` в `actionLevelRewards` мёртвая, ответ вложен дважды
   (`rewards.rewards`); `regionRewards` всегда пуст (`levelCompeted`).
    по решению пользователя 2026-10-15 — заготовка под будущую линейку наград, не удалять.
10. **Логика наград в странице.** Серебро, схемы, квесты и достижения за танк считаются в
    `CampaignPage.actionBattleTankReward`, а не в компоненте; `SCHEMES_CHANCE` объявлен в компоненте
    (`CampaignUserComponent`), используется только страницей и продублирован в
    `IdleUserComponent` с тем же значением и смыслом (кандидат на одну константу).
11. **Мёртвый код и имена.** `removeLevel()` не вызывается
    (кандидат на удаление); пустые `modifyReceiver` и `CampaignFighter`; пустой вложенный класс
    `CampaignBattleResult.Member`; опечатка в имени
    `levelCompeted` (должно быть `levelCompleted`); `getSilverCoinsReward` — геттер с побочным
    эффектом.
12. **Рейтинг и список онлайна отстают.** Повышение уровня не вызывает `onBasicInfoUpdate()`, рейтинг
    кампании обновится при следующем периодическом обновлении онлайна (до 2 минут,
    `User.SHOULD_UPDATE_ONLINE_AFTER`, `User.onBasicInfoUpdate`). Dev-`changeLevel` тоже не обновляет рейтинг и не шлёт квестовое
    событие.
13. **Баланс в коде** — все числа кампании и рост сложности бота захардкожены
    ([#balance](#balance)); правка требует релиза сервера.
14. **`battleData` не очищается** при `win: false` без рейтингового боя (ранний выход в
    `actionBattleResult`); вреда нет, следующий `/battle` его перезапишет.
15. **Самолёты противника не совпадают с ГДД.** Количество совпадает: `1 + level / 4` до 20 уровня
    (то есть 1…6), далее 8 (`BattleDataFactory.createBotTeam`). Но улучшения
    по очереди на позициях 9–12 не применяются. По ГДД (#gdd-enemy-airplanes, решение пользователя
    2026-10-15) — расхождение, исправление отложено.
16. **Схемы самолёта убраны, ГДД не обновлён.** `actionBattleTankReward` выдаёт только
    `RESOURCE_TANK_SCHEME`; ГДД ([#gdd-kill-reward](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-kill-reward))
    описывает 50/50 схему танка или самолёта и отсутствие схем в туториале. Решение по расхождению —
    вопрос пользователю, ГДД в этой задаче не менялся.
17. **Рейтинговый бой залипает без `/battleResult`.** `hasRankedBattle()` истинен, пока не вызван
    `completeBattle()` (или не пересоздан компонент); все `/battle` возвращают тот же `battleData`, а
    новый обычный бой создать нельзя. Клиент, не приславший `/battleResult`, остаётся в этом бою.
    Флаг `rankedBattle` не персистентен, выход — перезагрузка пользователя.
18. **Рейтинговый бой принимает любой `win`.** Эмулируется всегда; результат применяет
    `RankedChallengeService` по эмуляции, а не по заявлению клиента (сверка с ГДД рейтингового боя
    не проводилась, ГДД нет).

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [campaign-gdd.md](/workspace/client/.claude/docs/game-design/campaign-gdd.md) (ссылка в шапке).
Ссылки `#gdd-*` стоят у [#progress-model](#progress-model), [#battle-flow](#battle-flow),
[#rewards](#rewards), [#bot-difficulty](#bot-difficulty), у методов `getSilverCoinsReward`,
`levelCompeted`, `completeBattle`, `actionBattleTankReward`. Без ссылки: `levelRewards` (в ГДД
награды за уровень нет), `changeLevel` (только dev-роут). Рейтинговый бой в ГДД кампании не описан. Пункты [#tradeoffs](#tradeoffs), не
совпадающие с ГДД, помечены строкой «по ГДД (#якорь, …)».

<a id="file-map"></a>
## 10. Карта файлов компонента

Без airDrop-файлов — они в [airdrop-architecture.md#file-map](airdrop-architecture.md#file-map).

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` | компонент: уровень, бой, награда за главу, лимит серебра |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignBattle.java` | серверная эмуляция боя кампании |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignFighter.java` | боец кампании (пустой наследник `Fighter`) |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignBattleResult.java` | результат эмуляции боя (обычный/рейтинговый) |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` | WS-роуты `/ingame/campaign/*`, награды за юнитов, рейтинговые роуты |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | создание и загрузка компонента, receiver, `campaignLevel` в профиле, `onBasicInfoUpdate` |
| `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` | регистрация `/ingame/campaign` |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleDataFactory.java` | команды игрока и бота, рост сложности бота по уровню |
| `game/src/main/java/com/linkedgames/game/model/battle/Battle.java` | зависимость: базовый бой, тики, определение победителя |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleData.java` | зависимость: данные боя и seed, формат `battle` в ответе, `getFighter(uid)` |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleFighterData.java` | зависимость: боец боя, рейтинг/место/мощность |
| `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeService.java` | рейтинговый бой: создание и применение результата (только ссылка, не документируется здесь) |
| `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeActor.java` | вызывает `createBattle()`/`createRankedBattle()` (только ссылка) |
| `game/src/main/java/com/linkedgames/game/dao/RankedChallengeHistoryDao.java` | история рейтинговых боёв для роутов страницы (только ссылка) |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/HomePage.java` | `campaign` в `/ingame/home` и `/ingame/home/campaign` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/TrainPage.java` | `campaignLevel` в ответе с шансами рангов |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` | dev-роуты `/campaignAddLevel`, `/campaignRemoveLevel` |
| `game/src/main/java/com/linkedgames/game/service/rating/RatingCampaignService.java` | рейтинг игроков по уровню кампании |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/RatingPage.java` | роут рейтинга кампании `/campaign` (добавленный `/clan` к кампании не относится) |
| `game/src/main/java/com/linkedgames/game/service/playerlist/PlayerListService.java` | уровень кампании в списке онлайна |
| `game/src/main/java/com/linkedgames/game/model/quests/data/QuestData.java` | квест `CAMPAIGN_LEVEL_UP`: текущее и требуемое значение по уровню |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestEvent.java` | зависимость: `CAMPAIGN_LEVEL_UP`, `TANK_DESTROY` и др. |
| `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyTankAchievement.java` | зависимость: контекст достижения за танк |
| `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyAirplaneAchievement.java` | зависимость: контекст достижения за самолёт |
| `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` | зависимость: ресурсы-награды (серебро, золото, схемы) |
| `game/src/main/java/com/linkedgames/game/model/idle/IdleUserComponent.java` | дубль константы `SCHEMES_CHANCE` (см. [#tradeoffs](#tradeoffs) п.10) |
