# AirDrop — ящики с золотом в кампании (сервер)

ГДД: [/workspace/client/.claude/docs/game-design/airdrop-gdd.md](/workspace/client/.claude/docs/game-design/airdrop-gdd.md)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду (код в рамках
> задачи не менялся), 2026-09-28. Доверие пониженное: всё ниже подтверждено чтением кода, клиентская
> сторона (как клиент вызывает роуты и показывает ящик) не проверялась.
>
> Актуализация 2026-10-19 (merge `origin/amnesia/fix`, не закоммичен): код airDrop
> (`model/campaign/data/AirDrop*`, airDrop-методы и роуты) не менялся, проверено по diff. Обновлён
> только контекст компонента: рейтинговый бой, удалён туториал.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
   - [Контекст: CampaignUserComponent и CampaignPage](#campaign-context)
   - [Жизненный цикл ящика](#lifecycle)
   - [Баланс: откуда берутся числа](#balance)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`AirDropBoxType`](#cls-airdropboxtype)
   - [`AirDropBox`](#cls-airdropbox)
   - [`AirDropData`](#cls-airdropdata)
   - [`CampaignUserComponent` (airDrop-часть)](#cls-campaignusercomponent)
   - [`CampaignPage` (airDrop-роуты)](#cls-campaignpage)
   - [`DevToolsPage` (airDrop dev-роуты)](#cls-devtoolspage)
   - [Персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
9. [Карта файлов компонента](#file-map)
   - [Файлы прямого влияния](#file-map-direct)
   - [Файлы косвенного влияния](#file-map-indirect)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

AirDrop — случайный "ящик с неба" в кампании. Клиент периодически спрашивает сервер, не выпал ли
ящик; сервер с некоторой вероятностью выбирает цветной тип ящика и даёт на его сбор ограниченное
время. Если игрок успевает забрать ящик, ему начисляется случайное количество золотых монет
(`ItemId.RESOURCE_GOLDEN_COINS`), диапазон зависит от цвета. Число полученных наград в день ограничено
(сейчас 4), и с каждой полученной наградой шанс следующего выпадения падает.

Вся серверная логика сосредоточена в трёх классах пакета `model/campaign/data` (данные и рандом) и в
пяти полях/семи методах `CampaignUserComponent`. Сервер — авторитетный: тип ящика, срок жизни и
награда определяются только на сервере, клиент лишь передаёт команды "попробовать выбросить" и
"забрать".

<a id="campaign-context"></a>
### Контекст: CampaignUserComponent и CampaignPage

`CampaignUserComponent` (`game/.../model/campaign/CampaignUserComponent.java`, наследник
`UserChildComponent`, создаётся лениво в `User.getCampaignComponent()` с именем `"Campaign"`) хранит
прогресс кампании: `level` (из него вычисляются регион/глава/миссия), текущий бой `battleData` и признак рейтингового боя `rankedBattle`
(только в памяти) и минутный лимит серебра за уничтоженные танки (`lastRewardTime`/`currentRewardGiven`,
только в памяти). В MongoDB пишутся `level` и четыре airDrop-поля (см. [персистентность](#persistence)).
Его `apiResponse()` отдаёт только `level/region/chapter/mission` — **airDrop в нём не участвует**.

`CampaignPage` (`game/.../pages/ws/ingame/CampaignPage.java`, зарегистрирована в `WSRouter` как
`/ingame/campaign`) обслуживает бой кампании (`/battle`, `/battleResult`), награды за уничтожение
(`/battleTankReward`, `/battleAirplaneReward`, роуты рейтингового боя `/rankedRating`, `/rankedHistory*` — их проблемы с непроверенными `tankId`/`airplaneId`
описаны в [achievements-architecture.md#progress-sources](achievements-architecture.md#progress-sources)
и [#tradeoffs](achievements-architecture.md#tradeoffs); сами данные танков/самолётов — в
[tank-airplane-data-architecture.md](tank-airplane-data-architecture.md)), `/levelRewards` и два
airDrop-роута `/sendAirDrop`, `/getAirDrop`. Полное описание кампании без airDrop — [campaign-architecture.md](campaign-architecture.md).
AirDrop с боем никак не связан: он не зависит от уровня,
результата боя (в том числе рейтингового боя) и не зависит от `battleData`.

<a id="lifecycle"></a>
### Жизненный цикл ящика

Состояние игрока описывается пятью полями компонента:

| Поле | Смысл | В БД |
|---|---|---|
| `airDropRewardsGiven` | сколько наград получено за текущие сутки | да (`airDropRG`) |
| `airDropResetTime` | момент последнего суточного сброса счётчика | да (`airDropRT`) |
| `activeAirDrop` | тип ящика, "висящего" сейчас; `NONE` — ящика нет | да (`airDropAType`) |
| `airDropDeadTime` | момент (мс), после которого ящик сгорает; `0` — нет | да (`airDropDeadTime`) |
| `airDropTime` | момент (мс), раньше которого нельзя пробовать новый бросок (кулдаун) | **нет**, только в памяти |

Ящик считается активным, если `activeAirDrop != NONE` и текущее время строго меньше `airDropDeadTime`
(`hasActiveAirDrop()`).

1. **Бросок (`/sendAirDrop`).** Если активного ящика нет — проверяется кулдаун (`airDropTime`) и
   суточный лимит (с попутным сбросом счётчика при смене дня). Затем `sendAirDrop()`: если активный
   ящик есть — он возвращается повторно с `airDropInstant=true`; иначе выполняется `chanceAirDrop()`:
   кулдаун сдвигается на 1 минуту вперёд **при любом исходе**, делается бросок шанса по индексу
   `airDropRewardsGiven`; при успехе выбирается цвет и выставляется срок жизни 5 мин + 5,5 с.
2. **Сбор (`/getAirDrop`).** Если ящик активен — по его цвету находится `AirDropBox`, генерируется
   количество золота, предмет добавляется игроку, счётчик наград увеличивается, ящик сбрасывается в
   `NONE`/`0`, кулдаун снова ставится на 1 минуту.
3. **Сгорание.** Отдельного таймера/тика нет. Просроченный ящик просто перестаёт быть активным по
   `hasActiveAirDrop()`; поля в БД чистятся лениво — при следующем `sendAirDrop()`.
4. **Суточный сброс.** Тоже ленивый: в `isAirDropRewardAvailable()` через
   `resetAirDropByNextDay(false)`, когда `airDropResetTime` не "сегодня" по `DateUtil.isToday`
   (календарный день в часовом поясе JVM сервера).

<a id="balance"></a>
### Баланс: откуда берутся числа

Все числа **захардкожены** в `AirDropData`/`AirDropBoxType`; ни `Balance`, ни `balance.json`, ни
`app.properties` airDrop не содержат (проверено поиском).

- Кулдаун между бросками — `NEXT_DROP_AWAIT_TIME = 60 000 мс`.
- Срок жизни ящика — `DROP_LIFE_TIME = 300 000 + 5 500 мс` (5 мин + время анимации на клиенте, см. ГДД [#gdd-lifetime](/workspace/client/.claude/docs/game-design/airdrop-gdd.md#gdd-lifetime)).
- Шанс выпадения по номеру награды за день (`COUNT_DROP_CHANCES`): 1-я — 10 %, 2-я — 5 %,
  3-я — 2,5 %, 4-я — 1 % (см. ГДД [#gdd-spawn-chance](/workspace/client/.claude/docs/game-design/airdrop-gdd.md#gdd-spawn-chance)). Размер списка (4) и есть суточный лимит (`getMaxDropCount()`, см. ГДД [#gdd-daily-limit](/workspace/client/.claude/docs/game-design/airdrop-gdd.md#gdd-daily-limit)).
- Цвета (`LIST`, порядок важен для рулетки), шанс цвета и награда в золоте (включительно):

| Тип (enum) | Строка для клиента | Шанс цвета | Золото |
|---|---|---|---|
| `RED` | `red` | 1 % | 170–230 |
| `YELLOW` | `orange` | 3 % | 120–170 |
| `PURPLE` | `purple` | 6 % | 80–120 |
| `BLUE` | `blue` | 20 % | 50–80 |
| `GREEN` | `green` | 30 % | 30–50 |
| `GREY` | `grey` | 40 % | 10–20 |

Сумма шансов цветов — 100 % (см. ГДД [#gdd-box-quality](/workspace/client/.claude/docs/game-design/airdrop-gdd.md#gdd-box-quality) и [#gdd-reward](/workspace/client/.claude/docs/game-design/airdrop-gdd.md#gdd-reward)).

<a id="references"></a>
## 2. Референсы

Внешних референсов в коде нет. Структурно фича повторяет соседние механики `CampaignUserComponent`:
суточный сброс "по `DateUtil.isToday`" и отдача предмета-шаблона через `Resource.createNew(..., true)`
(так же, как `CHAPTER_GOLDEN_COINS_REWARD` в `levelCompeted`).

<a id="patterns"></a>
## 3. Паттерны

- **Персистентность через `changedField`** (поле-за-полем, `Component.changedField(name, value)`) и
  восстановление в `dbMappingBuild(Document)`; ключи — в вложенном `DBFields`. Подробно о подходе —
  агент `server-developer-db-persistence`.
- **Ленивые таймеры**: вместо планировщика хранятся абсолютные дедлайны (`airDropDeadTime`,
  `airDropTime`, `airDropResetTime`) и сравниваются с `System.currentTimeMillis()` при обращении.
- **Взвешенная рулетка** (`getRandomBox`): вычитание шансов из случайного процента по упорядоченному
  списку с fallback на последний элемент.
- **Enum со строковым ключом** (`AirDropBoxType.type` + `fromString` с fallback на `NONE`) — строка
  используется и в БД, и в ответе клиенту.
- **Шаблон предмета**: `Resource.createNew(id, true)` даёт предмет с `EMPTY_UID`; `BagUserComponent.add`
  при добавлении делает личную копию.

<a id="class-list"></a>
## 4. Список классов

Код не создавался и не менялся; перечислены классы, составляющие фичу:

- `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropBoxType.java`
- `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropBox.java`
- `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropData.java`
- `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` (airDrop-часть)
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` (`/sendAirDrop`, `/getAirDrop`)
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` (`/airDropChance`,
  `/airDropForce`, `/airDropReset`)

<a id="anchors"></a>
## 5. Навигация (якоря)

[`#purpose`](#purpose) · [`#campaign-context`](#campaign-context) · [`#lifecycle`](#lifecycle) ·
[`#balance`](#balance) · [`#references`](#references) · [`#patterns`](#patterns) ·
[`#class-list`](#class-list) · [`#cls-airdropboxtype`](#cls-airdropboxtype) ·
[`#cls-airdropbox`](#cls-airdropbox) · [`#cls-airdropdata`](#cls-airdropdata) ·
[`#cls-campaignusercomponent`](#cls-campaignusercomponent) · [`#cls-campaignpage`](#cls-campaignpage) ·
[`#cls-devtoolspage`](#cls-devtoolspage) · [`#persistence`](#persistence) ·
[`#client-contract`](#client-contract) · [`#tradeoffs`](#tradeoffs) · [`#file-map`](#file-map) ·
[`#file-map-direct`](#file-map-direct) · [`#file-map-indirect`](#file-map-indirect)

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Роль в фиче | Раздел |
|---|---|---|
| `AirDropBoxType` | цвета ящика + строковый ключ | [#cls-airdropboxtype](#cls-airdropboxtype) |
| `AirDropBox` | строка баланса: цвет, шанс, диапазон награды | [#cls-airdropbox](#cls-airdropbox) |
| `AirDropData` | константы баланса и рандом | [#cls-airdropdata](#cls-airdropdata) |
| `CampaignUserComponent` | состояние игрока, выдача, персистентность | [#cls-campaignusercomponent](#cls-campaignusercomponent) |
| `CampaignPage` | боевые WS-роуты | [#cls-campaignpage](#cls-campaignpage) |
| `DevToolsPage` | отладочные WS-роуты | [#cls-devtoolspage](#cls-devtoolspage) |

## 7. Классы и методы

<a id="cls-airdropboxtype"></a>
### `AirDropBoxType` (enum)

Значения `NONE("none")`, `GREY("grey")`, `GREEN("green")`, `BLUE("blue")`, `PURPLE("purple")`,
`YELLOW("orange")`, `RED("red")`. `NONE` означает "ящика нет".

- `getType()` — строковый ключ (он же в БД и в ответе клиенту).
- `fromString(String)` — линейный поиск по ключу; неизвестная строка или `null` → `NONE` (без
  исключения). Используется только при чтении из БД.

<a id="cls-airdropbox"></a>
### `AirDropBox`

Неизменяемая строка таблицы баланса: `public final type`, `public final dropChance` (процент для
рулетки цвета), приватные `minReward`/`maxReward`.

- `getReward()` — `RandomJdk.Instance.nextIntInclusive(minReward, maxReward)`, обе границы включены.
  Новый рандом при каждом вызове.

<a id="cls-airdropdata"></a>
### `AirDropData`

Статический "справочник" баланса (значения — в [#balance](#balance)).

- `NEXT_DROP_AWAIT_TIME`, `DROP_LIFE_TIME`, `LIST` — публичные константы (`LIST` — изменяемый
  `ArrayList`, но нигде не модифицируется).
- `getMaxDropCount()` — `COUNT_DROP_CHANCES.size()` (= 4), суточный лимит наград.
- `getAirDropBox(Integer dropCount)` — бросок "выпадет ли ящик вообще": `nextPercents()`
  (`100 * nextDouble()`, диапазон [0; 100)) сравнивается строго `<` с `COUNT_DROP_CHANCES.get(dropCount)`;
  успех → `getRandomBox()`, неуспех → `null`. При `dropCount >= 4` будет
  `IndexOutOfBoundsException` — вызывающие обязаны заранее проверить лимит
  (`isAirDropRewardAvailable()`).
- `getRandomBox()` — выбор цвета: из случайного процента по порядку `LIST` вычитаются `dropChance`,
  первый элемент, на котором остаток `<= 0`, — результат; если не нашли (теоретически невозможно при
  сумме 100) — последний элемент (`GREY`).

<a id="cls-campaignusercomponent"></a>
### `CampaignUserComponent` (airDrop-часть)

Поля — см. таблицу в [#lifecycle](#lifecycle).

- `isAirDropRewardAvailable()` — сначала `resetAirDropByNextDay(false)` (побочный эффект: может
  обнулить счётчик и записать в БД), затем `airDropRewardsGiven < getMaxDropCount()`.
- `resetAirDropByNextDay(boolean force)` — если `airDropResetTime` не сегодня или `force`: обнуляет
  `airDropRewardsGiven`, ставит `airDropResetTime = now`, оба поля через `changedField`. Кулдаун и
  активный ящик не трогает.
- `isAirDropTimeAvailable()` — `now >= airDropTime` (кулдаун прошёл).
- `hasActiveAirDrop()` — `activeAirDrop != NONE && now < airDropDeadTime`.
- `sendAirDrop()` — основной обработчик броска. (1) Если `airDropDeadTime != 0` и уже прошёл —
  сбрасывает `activeAirDrop = NONE`, `airDropDeadTime = 0` в памяти и БД (ленивая очистка сгоревшего
  ящика). (2) Если после этого ящик активен — возвращает `{airDropInstant: true, airDropType,
  airDropDeadTime}` без нового броска и без сдвига кулдауна. (3) Иначе — результат `chanceAirDrop()`
  (может быть `null`).
- `chanceAirDrop()` — ставит `airDropTime = now + 60 с` (только в памяти, до броска — т.е. и при
  неудаче), бросает `AirDropData.getAirDropBox(airDropRewardsGiven)`. Неудача → `null`. Успех →
  `activeAirDrop = тип`, `airDropDeadTime = now + DROP_LIFE_TIME`, оба в БД, возврат
  `{airDropInstant: false, airDropType, airDropDeadTime}`. Сам лимит не проверяет. Вызывается из
  `sendAirDrop()` и dev-роута `/airDropChance`.
- `sendForceAirDrop()` — dev-вариант без броска шанса: кулдаун +60 с, цвет через `getRandomBox()`,
  выставляет ящик и дедлайн так же, как `chanceAirDrop()`. Существующий активный ящик **перезаписывает**
  без проверки. Возвращает тот же JSON с `airDropInstant: false`.
- `getAirDrop()` — выдача награды. Нет активного ящика → `null`. Иначе: находит `AirDropBox` по
  `activeAirDrop` в `LIST` (`findFirst().get()`), создаёт шаблон `Resource.createNew(RESOURCE_GOLDEN_COINS,
  true).setCount(box.getReward())`, добавляет через `user().addItem(...)` (для `BagItem` →
  `BagUserComponent.add`, который копирует шаблон), кладёт в ответ `reward = airDropReward.apiResponse()`
  (ответ собран из шаблона, т.е. с пустым uid), затем `airDropRewardsGiven++`, ящик → `NONE`/`0` (всё
  в БД), кулдаун `now + 60 с` (в памяти). Квестовых/ачивочных событий не триггерит.
- `dbMappingBuild(Document)` (airDrop-часть) — `airDropRG` через `getInteger(..., 0)`, `airDropAType`
  через `AirDropBoxType.fromString` (отсутствие → `NONE`), `airDropDeadTime` и `airDropRT` через
  `getLong` только если ключ есть. `airDropTime` не читается — после загрузки компонента он `0`.
- `DBFields` — ключи Mongo (см. [#persistence](#persistence)).

Не связанные с airDrop методы (`getSilverCoinsReward`, `levelCompeted`, `createBattle`,
`completeBattle`, `apiResponse` и т.д.) — см. [#campaign-context](#campaign-context).

<a id="cls-campaignpage"></a>
### `CampaignPage` (airDrop-роуты)

Маршруты страницы `/ingame/campaign`; payload запроса не читают.

- `actionSendAirDrop` (`/sendAirDrop`) — если активного ящика нет: кулдаун не прошёл → ошибка
  `checkAvailable: "time"`; лимит исчерпан → `checkAvailable: "count"`. Затем `sendAirDrop()`;
  `null` → `checkAvailable: "bad luck"`; иначе `ok` с `airDrop`. При активном ящике обе проверки
  пропускаются и сразу возвращается существующий ящик.
- `actionGetAirDrop` (`/getAirDrop`) — нет активного ящика → `checkAvailable: "no air drop"`; затем
  `getAirDrop()`; `null` (дублирующая проверка) → та же ошибка; иначе `ok` с `airDropReward`.

<a id="cls-devtoolspage"></a>
### `DevToolsPage` (airDrop dev-роуты)

Страница `/ingame/devTools` регистрируется в `WSRouter` только при `app.devTools=true`.

- `actionAirDropChance` (`/airDropChance`) — проверяет только лимит (`"count"`), кулдаун и активный
  ящик **не** проверяет; вызывает `chanceAirDrop()` напрямую (может перезаписать активный ящик);
  `null` → `"bad luck"`, иначе `ok` с `airDrop`.
- `actionAirDropForce` (`/airDropForce`) — проверяет только лимит, затем гарантированный ящик через
  `sendForceAirDrop()`, `ok` с `airDrop`.
- `actionAirDropReset` (`/airDropReset`) — `resetAirDropByNextDay(true)`: обнуляет суточный счётчик
  (кулдаун и активный ящик не трогает), пустой `ok`.

<a id="persistence"></a>
### Персистентность

Секция компонента `"Campaign"`, запись по полям через `changedField` (без `changeThis`):

| Ключ Mongo | Поле | Тип |
|---|---|---|
| `airDropRG` | `airDropRewardsGiven` | int |
| `airDropAType` | `activeAirDrop` | string (`AirDropBoxType.getType()`) |
| `airDropDeadTime` | `airDropDeadTime` | long |
| `airDropRT` | `airDropResetTime` | long |

`airDropTime` (кулдаун) не сохраняется — живёт, пока жив объект компонента.

<a id="client-contract"></a>
### Контракт с клиентом

Клиент узнаёт об airDrop только из ответов на свои запросы; push-событий нет, в
`CampaignUserComponent.apiResponse()` (уходит в `HomePage` и ответы боя) airDrop-состояния нет.

- `/ingame/campaign/sendAirDrop` → `payload.airDrop = { airDropInstant: boolean, airDropType: string,
  airDropDeadTime: long (абсолютное серверное время, мс) }`. `airDropInstant = true` — это уже
  существовавший ящик (например, после перезахода), `false` — только что выпавший. Ошибки:
  `checkAvailable` = `"time"` | `"count"` | `"bad luck"`.
- `/ingame/campaign/getAirDrop` → `payload.airDropReward = { reward: <Resource.apiResponse()> }`
  (золото, `id = 2`, `count` = выпавшее количество). Ошибка: `checkAvailable = "no air drop"`.
- Dev: `/ingame/devTools/airDropChance`, `/airDropForce` → `payload.airDrop` того же формата;
  `/airDropReset` → пустой `ok`.
- Строка цвета для `YELLOW` — `"orange"`; клиент должен ориентироваться на строки из таблицы
  [#balance](#balance), а не на имена enum.

Как клиент потребляет эти данные — не проверялось (серверный анализ).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и подозрительные места

Явных комментариев о принятых компромиссах в коде нет; ниже — наблюдения по коду, требующие решения
владельца, а не утверждения о намерениях.

> **Отложено (решение пользователя, 2026-09-28):** пункты ниже сейчас не исправляются. При любой новой
> задаче, затрагивающей airDrop (`AirDropData`/`AirDropBox`/`AirDropBoxType`, airDrop-часть
> `CampaignUserComponent`/`CampaignPage`/`DevToolsPage`), — предложить пользователю включить их
> исправление в задачу, предварительно сверив с актуальным кодом.

1. **Кулдаун не персистентен.** `airDropTime` только в памяти: при пересоздании компонента (повторная
   загрузка пользователя) кулдаун обнуляется, и можно сразу бросать снова. Шанс при этом не растёт
   (индекс по `airDropRewardsGiven`), но число попыток в минуту ограничено только временем жизни
   объекта.
2. **Кулдаун ставится до броска.** Неудачный бросок тоже сдвигает `airDropTime` — это, видимо, и есть
   механизм "раз в минуту"; вероятность ящика за сутки определяется числом минут онлайна.
3. **Суточный сброс по часовому поясу JVM** (`DateUtil.isToday` через `GregorianCalendar` по
   умолчанию). Ящик, выпавший до полуночи и забранный после, увеличит счётчик "вчерашнего" дня,
   который затем обнулится при следующей проверке лимита. По ГДД ([#gdd-daily-limit](/workspace/client/.claude/docs/game-design/airdrop-gdd.md#gdd-daily-limit), решение пользователя 2026-10-14) такой ящик должен засчитываться в новые сутки; исправление отложено.
4. **`getAirDrop()` не проверяет лимит/день** — полагается на то, что лимит проверен при выбросе.
   Корректно, пока ящик нельзя создать в обход лимита.
5. **Dev-роуты перезаписывают активный ящик** (`/airDropChance`, `/airDropForce`) — только для dev.
6. **`getAirDropBox` бросает `IndexOutOfBoundsException` при `dropCount >= 4`** — защищено только
   порядком проверок в вызывающих.
7. **Несовпадение имени и строки: `YELLOW` ↔ `"orange"`.** Менять строку нельзя без миграции БД и
   клиента.
8. **Баланс захардкожен** в `AirDropData`, а не в `Balance`/Google-таблице — правка требует релиза
   сервера.
9. **Срок жизни включает клиентскую анимацию** (+5,5 с) — серверный дедлайн зависит от клиентского
   тайминга.
10. **Нет событий квестов/достижений** за полученное золото (в отличие от серебра в
    `/battleTankReward`); `QuestEvent` для золота в проекте нет вовсе.
11. **`reward` в ответе собран из шаблона** (`EMPTY_UID`), а не из реально добавленной копии —
    клиент не получит uid предмета из этого ответа.

<a id="file-map"></a>
## 9. Карта файлов компонента

Карта по фиче airDrop (не по всему `CampaignUserComponent`). Пути от корня репозитория `server`.
Миграций и ресурсов у фичи нет: баланс задан константами в `AirDropData`, поля лежат в документе `User`
(секция `Campaign`), индексов Mongo нет.

<a id="file-map-direct"></a>
### Файлы прямого влияния

- `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropBoxType.java` — цвета ящика и строковый ключ.
- `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropBox.java` — строка баланса: цвет, шанс, диапазон награды.
- `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropData.java` — константы баланса, рулетка `getRandomBox`.
- `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` — состояние игрока, выдача и сброс ящика, персистентность.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` — боевые роуты `/sendAirDrop`, `/getAirDrop`.

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` — dev-роуты `/airDropChance`, `/airDropForce`, `/airDropReset`.
- `game/src/main/java/com/linkedgames/game/model/user/User.java` — создание компонента `Campaign`, `dbMappingBuild`, `modifyReceiver`.
- `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` — регистрация `CampaignPage` (`/ingame/campaign`).
- `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` — зависимость: шаблон предмета-награды (`Resource.createNew`).
- `game/src/main/java/com/linkedgames/game/model/item/ItemId.java` — зависимость: идентификатор золота `RESOURCE_GOLDEN_COINS` для награды.
- `commons/src/main/java/com/linkedgames/commons/rnd/RandomJdk.java` — зависимость: генератор случайных чисел для рулетки и награды.
- `commons/src/main/java/com/linkedgames/commons/utils/DateUtil.java` — зависимость: `isToday` для суточного сброса счётчика.

Сверка полноты: `grep -rlE "AirDrop|airDrop"` по репозиторию даёт ровно шесть файлов (пять прямых и `DevToolsPage`);
`grep -rl CampaignUserComponent` добавляет `User.java` (прочие совпадения, например `BattleDataFactory`, `HomePage`, `RankedChallengeActor`, к airDrop не относятся); `CampaignPage` встречается ещё в `WSRouter.java`.
