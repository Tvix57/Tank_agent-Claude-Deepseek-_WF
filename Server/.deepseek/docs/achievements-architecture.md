# Достижения (Achievements) — `AchievementUserComponent`

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-09-28;
> сверен с кодом и таблицей `Achievements` в `balance.json` 2026-10-14; после merge `amnesia/fix` перепроверен 2026-10-19, правок не потребовалось. Клиентская сторона —
> `/workspace/client/.claude/docs/achievements-architecture.md`, здесь не дублируется.

ГДД: [/workspace/client/.claude/docs/game-design/achievements-gdd.md](/workspace/client/.claude/docs/game-design/achievements-gdd.md)

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация по классам](#class-nav)
6. Классы
   - [`AchievementUserComponent`](#class-achievementusercomponent)
   - [`Achievement`](#class-achievement)
   - [`AchievementEntry`](#class-achievemententry)
   - [`AchievementData`](#class-achievementdata)
   - [`AchievementFactory`](#class-achievementfactory)
   - [`IAchievementContext`](#class-iachievementcontext)
   - [`DestroyTankAchievement` / `DestroyAirplaneAchievement`](#class-destroy-achievements)
   - [`AchievementRank`](#class-achievementrank)
   - [`AchievementType`](#class-achievementtype)
   - [`AchievementsPage`](#class-achievementspage)
   - [`AchievementsDao`](#class-achievementsdao)
7. [Начисление прогресса (точки вызова)](#progress-sources)
8. [Push-события и уведомления](#push-events)
9. [Персистентность](#persistence)
10. [Контракт с клиентом](#client-contract)
11. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
12. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

"Достижения" — **72 фиксированных достижения** на игрока, каждое — счётчик уничтожений вражеской
техники конкретной страны и класса:

- id 1–32 — `DestroyTankAchievement`: 8 стран × 4 класса танка (`LIGHT`/`TD`/`MEDIUM`/`HEAVY`),
  секция `tanksHunt`;
- id 33–72 — `DestroyAirplaneAchievement`: 8 стран × 5 классов самолёта (`FIGHTER`/`HEAVY_FIGHTER`/
  `STORMTROOPER`/`BOMBER`/`STRATEGIC_BOMBER`), секция `airplaneHunt`.

Ранги `NONE → I … X → MAX` (качества, [#gdd-quality](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-quality)). Состояние: `progress` (накопленный счётчик), `currentRank` (последний
полученный), `nextRank` (к которому идёт игрок). Порог `maxProgress` и награда ([#gdd-reward](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-reward)) берутся из баланса по
`(id, nextRank)`.

Жизненный цикл:

1. Клиент сообщает об уничтожении в кампании → `trigger` прибавляет `+1` к `progress` достижений с той
   же страной и классом ([точки вызова](#progress-sources)).
2. `progress >= maxProgress` — достижение выполнено (`isDone`): push и уведомление
   ([Push-события](#push-events), [#gdd-complete-popup](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-complete-popup)).
3. `/ingame/achievements/getReward` выдаёт награду за `nextRank` (в балансе всегда `GOLD_COIN`,
   ресурс id 2), `currentRank = nextRank`, `nextRank = next()`, `maxProgress` пересчитывается.
4. `progress` при повышении ранга **не сбрасывается**: пороги накопительные ([#gdd-progress](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-progress), id 1: 100, 500, 1000,
   3000, 15000, 30000, 60000, 120000, 300000, 500000; награды 10, 20, 40, 80, 160, 320, 640, 1500,
   3000, 6000).
5. При `nextRank == MAX` прогресс не копится (`addProgress` → `false`), награды нет, `maxProgress = 0`,
   `isDone == false`.

<a id="references"></a>
## 2. Референсы

Не использовались — задокументирована существующая реализация.

<a id="patterns"></a>
## 3. Паттерны

- **Strategy** — `Achievement` задаёт общий жизненный цикл, наследники в `list/` реализуют только
  `trigger(IAchievementContext)`.
- **Context object** — событие описывается `IAchievementContext` (вложенные `Context` наследников);
  компонент фильтрует по `AchievementType` контекста до вызова `trigger`.
- **Статическая фабрика** — `AchievementFactory` создаёт все 72 достижения при конструировании
  компонента; из БД накатывается только сохранённое состояние. ГДД: [#gdd-task](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-task).
- **Отдельная коллекция Mongo на сущность списка** (`dbFetchChanged`/`commitDbUpdates`, как у
  `bag`/`codex`/`collection`) — [Персистентность](#persistence),
  `.claude/agents/developers/server-developer-db-persistence.md`.
- **Dirty-флаг битовой маской** — `AchievementEntry.condition`, бит `INTERNAL_CONDITION_UPDATED`.

<a id="class-list"></a>
## 4. Список классов

Пакет `game/src/main/java/com/linkedgames/game/model/achievements/`: `AchievementUserComponent`,
`Achievement` (abstract), `AchievementEntry` (abstract), `AchievementData`, `AchievementFactory`,
`IAchievementContext`, `enums/AchievementRank`, `enums/AchievementType`,
`list/DestroyTankAchievement`, `list/DestroyAirplaneAchievement` (оба с вложенным `Context`).

Вне пакета (от `game/src/main/java/com/linkedgames/game/`): `pages/ws/ingame/AchievementsPage` (роуты),
`dao/AchievementsDao` (коллекция `achievements`). Подключение и интеграции — [карта файлов](#file-map).

<a id="class-nav"></a>
## 5. Навигация по классам

Якоря классов — в [оглавлении](#toc). Связи: `User.getAchievementsUserComponent()` (ленивое создание,
имя компонента `"Achievements"`) → `AchievementUserComponent` → `Map<Integer, Achievement> list` (из
`AchievementFactory`) → `Achievement extends AchievementEntry` → наследники из `list/`. Порог и
награда: `Balance` → `AchievementData`.

## 6. Классы

<a id="class-achievementusercomponent"></a>
### `AchievementUserComponent`

`extends UserChildComponent implements APIResponseStd`. Владеет `Map<Integer, Achievement> list`
(ключ — id) и кэшем `dbUpdateDocuments`.

- **Конструктор** — `list = AchievementFactory.createDefaultAchievements()`: все 72 в начальном
  состоянии независимо от БД.
- **`trigger(IAchievementContext)`** — для достижений с `getAchievementType() ==
  context.getAchievementType()` вызывает `item.trigger(context)`; если вернулось `true` И `isDone()`
  изменился — [push](#push-events) и `sendNotification()`.
- **`completeAchievement(int id)`** — `null`, если достижения нет, оно не выполнено или `MAX`. Иначе:
  `getReward()` → `user().addItem(item)` (в сумку: `Resource` — `BagItem`), `setNextRank()`,
  `sendNotification()`; возвращает `apiResponse()` уже НОВОГО состояния (выданная награда отдельно не
  возвращается). Push здесь не шлётся.
- **`sendNotification()`** — есть достижение `isDone && !isMaxRank` → `addNotification(ACHIEVEMENT_ID,
  { hasDone, doneSections })`, где `doneSections` — уникальные `AchievementType.getType()` таких
  достижений; иначе `deleteNotification`. Вызывается также из `User.onAuthorizedActiveOnce()`.
  ГДД: [#gdd-notifiers](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-notifiers).
- **`getSection(AchievementType)`** — `JSONArray` из `apiResponse()` достижений секции (порядок —
  обход `HashMap`, сортирует клиент).
- **Dev-операции** (только из `DevToolsPage`, без проверки `null`): `dropProgress` (`progress = 0`),
  `dropRank` (ранг `NONE`/`I` + `progress = 0`), `setMaxRank` (доводит до `MAX` без выдачи наград) —
  без push и `sendNotification`; `setMaxProgress` (`progress = maxProgress`) — всегда push и
  `sendNotification`.
- `apiResponse()` — `{ inProgress: [все 72] }`, не вызывается (см. [#tradeoffs](#tradeoffs)).
- Тривиальные: `getAchievement(id)`, пустой `modifyReceiver`.
- `dbFetchChanged` / `commitDbUpdates` / `dbMappingChildBuild` — [Персистентность](#persistence).

<a id="class-achievement"></a>
### `Achievement` (abstract)

`extends AchievementEntry implements APIResponseStd`. Поля: `public int id`, `progress`,
`maxProgress`, `currentRank`, `nextRank`, `protected AchievementType type`.

- **Конструктор `(id, type)`** — `currentRank = NONE`, `nextRank = I`, `refreshMaxProgress()`.
- **`addProgress(int)`** — при `isMaxRank()` → `false`; иначе `progress += value`, `markAsDirty()`,
  `true`. Верхней границы нет: `progress` растёт и после `isDone`.
- **`isDone()`** — `maxProgress > 0 && progress >= maxProgress`. **`isMaxRank()`** — `nextRank == MAX`.
- **`setNextRank()`** — только при `isDone()`: `currentRank = nextRank`, `nextRank = nextRank.next()`,
  пересчёт порога, `markAsDirty()`; `progress` не трогает.
- **`getReward(boolean template)`** — `null` при `MAX` или без строки баланса; иначе
  `Resource.createNew(data.rewardId, template)` с `count = data.reward`. `template = true` (для
  `apiResponse`) даёт uid `BagItem.EMPTY_UID`; `getReward()` = `getReward(false)`, реальный предмет.
- **`abstract trigger(IAchievementContext)`** — реализуют наследники.
- **`apiResponse()`** — `{ id, type, currentProgress, maxProgress, currentRank (ordinal), nextRank
  (ordinal), reward? }`; `reward` — шаблонная награда, нет при `MAX`.
- **`refreshMaxProgress()`** (private) — `maxProgress` из `Balance.getAchievementData(id, nextRank)`,
  `0` без строки (в т.ч. `MAX`); `afterDBMappingBuild()` вызывает его после загрузки из БД.
- **`dbMappingBuild` / `dbToData`** — `id`, `progress`, `currentRank`, `nextRank` (ordinal); невалидный
  ordinal при чтении заменяется на `NONE`/`I` через `AchievementRank.from`.
- Dev: `dropProgress`, `setMaxProgress`, `dropRank`, `setMaxRank` (цикл `setMaxProgress();
  setNextRank();` до `MAX`).
- Тривиальные: `getNextRang()` (опечатка в имени), `getAchievementType()`.

<a id="class-achievemententry"></a>
### `AchievementEntry` (abstract)

`implements IPersistentObject`. Persistable-запись: `ObjectId uid` и битовая маска `condition`.

- `getUid()` создаёт `ObjectId` лениво (при первом `getUid()`/`dbToData()`, далее uid читается из БД);
  `setUid` — только если не задан; `regenerateUid()` — новый uid.
- `addCondition`/`removeCondition`/`hasCondition` (protected), `markAsDirty()` ставит
  `INTERNAL_CONDITION_UPDATED`.
- `dbMappingBuild`/`dbToData` — только `_id`; `DBFields`: `UID_FIELD = "_id"`, `OWNER_ID_FIELD = "ownerId"`.
- `hashCode()` по uid.

<a id="class-achievementdata"></a>
### `AchievementData`

`implements KeyModel<Integer>` — строка таблицы баланса `Achievements`: `uid`, `achievementId`,
`rank`, `maxProgress`, `rewardId`, `reward` (количество). `build(JSONArray)` читает колонки
`[0]=uid`, `[1]=achievementId`, `[2]=rank` (индекс в `AchievementRank.ALL`), `[3]=maxProgress`,
`[5]=rewardId`, `[7]=reward`; `[4]` (описание) и `[6]` (имя награды) игнорируются. `key()` — `uid`.

В `balance.json` 720 строк: 72 достижения × ранги `I`–`X`; для `NONE`/`MAX` строк нет. Поиск по
`(achievementId, rank)` — `Balance.getAchievementData(int, AchievementRank)`, линейный проход.

<a id="class-achievementfactory"></a>
### `AchievementFactory`

`createDefaultAchievements()` — `HashMap` из 72 достижений с жёстко прописанными id, страной и
классом (порядок стран: `USSR`, `DE`, `US`, `JP`, `GB`, `IT`, `FR`, `CN`). Id совпадают с
`achievementId` в балансе (1–72) и должны совпадать при любом добавлении.

<a id="class-iachievementcontext"></a>
### `IAchievementContext`

Единственный метод `getAchievementType()` — по нему компонент выбирает, каким достижениям передать
контекст.

<a id="class-destroy-achievements"></a>
### `DestroyTankAchievement` / `DestroyAirplaneAchievement`

Одинаковы по устройству, различаются типом техники (`TankType`/`AirplaneType`) и секцией
(`TANKS_HUNT`/`AIRPLANES_HUNT`).

- Конструктор `(id, Country, TankType|AirplaneType)`.
- `trigger(context)` — приводит контекст к своему `Context` (прямой cast, без `instanceof`), при
  совпадении страны и класса — `addProgress(1)`.
- `apiResponse()` — базовый ответ + `image: { country: Country.ALL.indexOf(country) }`.
- Вложенный `Context(Country, TankType|AirplaneType)`; `getAchievementType()` — своя секция.

<a id="class-achievementrank"></a>
### `AchievementRank` (enum)

`NONE, I … X, MAX` (ordinal 0–11). `next()` — следующий по ordinal, для `MAX` — `MAX`.
`from(Integer ordinal, fallback)` — безопасное чтение из БД. `VALUES`/`ALL` — кэш значений.

<a id="class-achievementtype"></a>
### `AchievementType` (enum)

`TANKS_HUNT("tanksHunt")`, `AIRPLANES_HUNT("airplaneHunt")` (второе — в единственном числе, клиент на
это завязан). `getType()` — строка секции (JSON `type`/`section`); `fromString(str)` — `null` при
неизвестном.

<a id="class-achievementspage"></a>
### `AchievementsPage`

`extends AuthorizedUserPage`, регистрация в `WSRouter` как `/ingame/achievements`.

| Роут | Вход | Ответ |
|---|---|---|
| `""` | — | пустой `ok` |
| `/getSection` | `section: string` | `{ inProgress: [...] }`; неизвестная секция → ошибка `"invalid achievement section name"` |
| `/update` | `id: int` | `achievement.apiResponse()`; неизвестный id → `"invalid achievement Id"` |
| `/getReward` | `id: int` | новое состояние (`completeAchievement`); `null` → `"invalid achievement Id or not done"` |

<a id="class-achievementsdao"></a>
### `AchievementsDao`

Singleton `INSTANCE`, коллекция `achievements`. `findByOwnerId(ObjectId, Subscriber|TaskMailBox)` —
документы `{ ownerId }` (mailbox при ошибке получает `null`); `bulkUpdate(List<WriteModel>,
Subscriber|TaskMailBox)` — `bulkWrite` (mailbox получает `true`/`false`: успех/падение базы).

<a id="progress-sources"></a>
## 7. Начисление прогресса (точки вызова)

`trigger` вызывается **только** из `CampaignPage` (кампания, не PvP):

- `actionBattleTankReward` — по `tankId` из запроса: `Balance.getTankData(tankId)` →
  `DestroyTankAchievement.Context(country, type)`. Метод выходит раньше при
  `getSilverCoinsReward() == 0` (лимит серебра исчерпан) — тогда прогресс тоже не начисляется.
- `actionBattleAirplaneReward` — по `airplaneId`: `Balance.getAirplaneData(airplaneId)` →
  `DestroyAirplaneAchievement.Context`. Без проверки лимита.

Оба вызова под `if (true) { // TODO добавить проверку что такой танк/самолет есть на поле боя }`.
Других источников (квесты, PvP, покупки) нет; dev-роуты `/achievementDropProgress`,
`/achievementDropRank`, `/achievementMaxProgress`, `/achievementMaxRank` — в `DevToolsPage`.

<a id="push-events"></a>
## 8. Push-события и уведомления

1. **`/events/achievements/update`** (`JsonPacket`; клиент слушает `g/ws/events/achievements/update`) —
   `{ id, section, nextRank (ordinal), isDone }`. Шлётся из `trigger`, только когда `isDone` сменился
   (на практике `false → true`), и из dev `setMaxProgress` всегда. Не шлётся: при обычном приросте,
   после `getReward`, после dev `dropProgress`/`dropRank`/`setMaxRank`.
2. **Уведомление `achievement`** (`NotificationId.ACHIEVEMENT_ID`) через `NotificationUserComponent`
   → push `/events/userNotification` с `method: "UPDATE"` (`value = { hasDone, doneSections }`) или
   `"DELETE"`. Обновляется `sendNotification()`.

<a id="persistence"></a>
## 9. Персистентность

Отдельная коллекция Mongo `achievements`, документ на **изменённое** достижение:
`{ _id, ownerId, id, progress, currentRank, nextRank }`. В общий документ `User` не пишется
(`User.DBFields.P_ACHIEVEMENTS_FIELD` объявлен, не используется). Неизменённые достижения в БД не
хранятся — состояние берётся из фабрики. Индекс `ownerId` — миграция
`1785922748073_achievements.json`.

- **Загрузка** — `ActorInitializationTask`: `fetchUserAchievementsDb` → `findByOwnerId` →
  `dbMappingChildBuild`: достижение ищется по полю `id` в `list` фабрики; найдено — `dbMappingBuild` +
  `afterDBMappingBuild` (порог по текущему балансу), нет — документ молча игнорируется. `null`
  (ошибка запроса) → `fail("Init achievements failed")`.
- **Сохранение** — `ActorUpdateTask`, шаг `achievementsToDb`: `dbFetchChanged()` собирает
  `UpdateOneModel({_id: uid}, {$set: dbToData() + ownerId}, upsert)` для достижений с dirty-битом,
  **снимая бит при сборке**, и кэширует список в `dbUpdateDocuments` (повторный вызов до commit
  возвращает кэш). Пусто → `null`, шаг успешен без запроса.
- **Commit** — после успешного `bulkUpdate` всех компонентов `commitDbUpdates()` сбрасывает кэш и
  снова вызывает `dbFetchChanged()`; новые изменения за время записи → `false` →
  `persistFailed("User still has some data to save..")` (остаток сохранит следующая итерация). При
  ошибке базы commit не вызывается, кэш остаётся для повтора.

<a id="client-contract"></a>
## 10. Контракт с клиентом

Клиентская сторона — `/workspace/client/.claude/docs/achievements-architecture.md#s7-data-flow`
(типы `AchievementJSON`/`AchievementDoneJSON`, запросы, подписки). Серверная форма данных —
[`Achievement.apiResponse`](#class-achievement), [`AchievementsPage`](#class-achievementspage),
[Push-события](#push-events).

Совпадает: имена секций, ordinal-ранги (`MAX = 11`), необязательный `reward` (нет при `MAX`),
`image.country`, форма уведомления `{ hasDone, doneSections }`.

Расхождения (зафиксированы, не исправлялись):

1. Клиентский `AchievementLine.onEventUpdate` типизирует push как `AchievementJSON`, сервер шлёт
   `{ id, section, nextRank, isDone }` (`AchievementDoneJSON`). Клиент использует только `id` — не
   ломает.
2. Клиент по push перезапрашивает строку (`updateData()`), но push идёт только при переходе порога,
   не на каждое `+1`: промежуточный прогресс в открытом списке не обновляется.
3. Клиент передаёт в `/update` и `/getReward` `{ section, id }`, сервер читает только `id`.
4. После `/getReward` push нет — клиент обновляет строку по ответу. Если накопленный `progress` уже
   перекрывает следующий порог, ответ сразу с `currentProgress >= maxProgress`, а о новом выполнении
   сигналит только уведомление `achievement`.
5. Ответ `/getReward` — новое состояние, не выданный предмет; клиент анимирует награду по старым
   данным (согласовано с клиентским документом, но зависит от этого порядка).
6. Dev `dropProgress`/`dropRank`/`setMaxRank` не вызывают `sendNotification()` — бейдж `doneSections`
   (`AchievementsListSection`) может остаться устаревшим.

<a id="tradeoffs"></a>
## 11. Принятые уязвимости, компромиссы и подозрительные места

Намеренных компромиссов в коде не задокументировано; ниже факты кода (не исправлялись).

> **Отложено (решение пользователя, 2026-09-28):** пункты ниже и расхождения из
> [контракта с клиентом](#client-contract) не исправляются. При любой новой задаче, затрагивающей
> `AchievementUserComponent`/`AchievementsPage`/`model/achievements/**`, предложить пользователю
> включить их исправление, предварительно сверив с актуальным кодом.

- **Потеря прогресса при лимите серебра** (по ГДД [#gdd-progress](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-progress), решение пользователя 2026-10-14) — расхождение, исправление отложено: роут танков не засчитывает прогресс при `getSilverCoinsReward() == 0`, хотя по ГДД прогресс засчитывается каждая единица техники.
- **Нет push при перекрытии порога из /getReward** (по ГДД [#gdd-complete-popup](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-complete-popup), решение пользователя 2026-10-14) — расхождение, исправление отложено: после `/getReward` push `/events/achievements/update` не шлётся; если накопленный прогресс после выдачи награды перекрывает следующий порог, клиент узнаёт о новом выполнении только из уведомления, а не из отдельного события.
- **Античит**: прогресс начисляется по `tankId`/`airplaneId` от клиента без проверки (`if (true)
  // TODO`); самолётный роут не ограничен даже лимитом серебра — прогресс самолётов можно накручивать
  повторными запросами.
- **NPE**: неизвестный `tankId`/`airplaneId` → `getTankData`/`getAirplaneData` вернёт `null` →
  `NullPointerException` в `CampaignPage`.
- **Dedup уведомления не работает**: `NotificationUserComponent.addNotification` сравнивает значения
  через `Objects.equals`, а `JSONObject` не переопределяет `equals` → каждый `sendNotification()` с
  выполненными достижениями повторно шлёт `/events/userNotification`.
- **`setMaxRank`**: если в балансе нет строки промежуточного ранга (`maxProgress = 0` → `isDone`
  всегда `false`), цикл бесконечен. Сейчас строки для `I`–`X` есть у всех 72.
- **Небезопасный cast** в `trigger` наследников держится только на фильтре по `AchievementType`:
  второй тип контекста с тем же `AchievementType` даст `ClassCastException`.
- **Награда всегда `Resource`** по `rewardId`: не-ресурсный id (танк/самолёт) в балансе создастся как
  `Resource` с этим id.
- **Dev-методы компонента** не проверяют `null`; защита — только проверка в `DevToolsPage`.
- **Производительность**: `Balance.getAchievementData(id, rank)` — линейный поиск по 720 строкам;
  вызывается в `refreshMaxProgress` и в каждом `apiResponse` (через `getReward(true)`), `getSection`
  делает ~36–40 проходов.
- **Мёртвый код** (кандидат на удаление): `AchievementUserComponent.apiResponse()`,
  `User.DBFields.P_ACHIEVEMENTS_FIELD`, `AchievementEntry.regenerateUid()`, пустой `modifyReceiver`.
- **Мелочи**: `hashCode()` без `equals()` в `AchievementEntry`; опечатка `getNextRang()`.

<a id="file-map"></a>
## 12. Карта файлов компонента

Пути от корня репозитория `/workspace/server`.

### Файлы прямого влияния

- `game/src/main/java/com/linkedgames/game/model/achievements/AchievementUserComponent.java` — компонент игрока: список достижений, `trigger`, push, персистентность.
- `game/src/main/java/com/linkedgames/game/model/achievements/Achievement.java` — базовое достижение: прогресс, ранги, `isDone`.
- `game/src/main/java/com/linkedgames/game/model/achievements/AchievementEntry.java` — запись достижения для сохранения в БД.
- `game/src/main/java/com/linkedgames/game/model/achievements/AchievementData.java` — балансовая запись (порог, награда по `(id, rank)`).
- `game/src/main/java/com/linkedgames/game/model/achievements/AchievementFactory.java` — создание всех 72 достижений.
- `game/src/main/java/com/linkedgames/game/model/achievements/IAchievementContext.java` — интерфейс контекста события для `trigger`.
- `game/src/main/java/com/linkedgames/game/model/achievements/enums/AchievementRank.java` — ранги достижений.
- `game/src/main/java/com/linkedgames/game/model/achievements/enums/AchievementType.java` — типы достижений, фильтр cast в `trigger`.
- `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyTankAchievement.java` — достижение «уничтожить танки» и его `Context`.
- `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyAirplaneAchievement.java` — достижение «уничтожить самолёты» и его `Context`.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AchievementsPage.java` — WS-роуты `/ingame/achievements/*`.
- `game/src/main/java/com/linkedgames/game/dao/AchievementsDao.java` — доступ к Mongo-коллекции `achievements`.
- `game/src/main/resources/migrations/1785922748073_achievements.json` — миграция индекса коллекции `achievements`.

### Файлы косвенного влияния

- `game/src/main/java/com/linkedgames/game/model/user/User.java` — ленивое создание компонента `"Achievements"`, `modifyReceiver`, `sendNotification` в `onAuthorizedActiveOnce`.
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorInitializationTask.java` — загрузка достижений игрока из БД при входе.
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorUpdateTask.java` — сохранение изменений (`bulkUpdate`, `commitDbUpdates`).
- `game/src/main/java/com/linkedgames/game/balance/Balance.java` — загрузка таблицы `Achievements`, `getAchievementData`.
- `game/src/main/resources/balance.json` — общий баланс; компоненту принадлежит таблица `Achievements` (пороги и награды).
- `game/src/main/java/com/linkedgames/game/balance/BalanceImporter.java` — список импортируемых таблиц баланса, включает `Achievements`.
- `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` — регистрация роута `/ingame/achievements`.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` — источник прогресса: вызовы `trigger` при уничтожении танка и самолёта.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` — dev-роуты `achievement*`.
- `game/src/main/java/com/linkedgames/game/model/notifications/NotificationUserComponent.java` — зависимость: `addNotification`/`deleteNotification` для уведомления `achievement`.
- `game/src/main/java/com/linkedgames/game/model/notifications/NotificationId.java` — зависимость: идентификатор уведомления о достижении.
- `game/src/main/java/com/linkedgames/game/model/Country.java` — зависимость: страны, фильтр контекста достижений.
- `game/src/main/java/com/linkedgames/game/model/bag/tank/TankType.java` — зависимость: тип танка, фильтр контекста `DestroyTankAchievement`.
- `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneType.java` — зависимость: тип самолёта, фильтр контекста `DestroyAirplaneAchievement`.
- `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` — зависимость: ресурс, выдаваемый как награда.
- `game/src/main/java/com/linkedgames/game/model/item/Item.java` — зависимость: предмет награды.
- `game/src/main/java/com/linkedgames/game/balance/KeyModel.java` — зависимость: ключ записи баланса, база `AchievementData`.
- `game/src/main/java/com/linkedgames/game/model/user/UserChildComponent.java` — зависимость: базовый класс компонента игрока.
