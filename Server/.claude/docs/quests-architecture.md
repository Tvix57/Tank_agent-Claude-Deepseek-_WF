# Квесты — `QuestsUserComponent` (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-09-28;
> актуализирован 2026-10-19 после merge `origin/amnesia/fix` (туториальные ветки и `isEndless` удалены,
> награда только танковые схемы, аэродромные источники прогресса переехали в `MilitaryBasePage`).
> Всё ниже подтверждено чтением кода; клиентская сторона (как клиент показывает квест и вызывает роуты)
> не проверялась, кроме факта подписки на push-событие.

ГДД: [/workspace/client/.claude/docs/game-design/quests-gdd.md](/workspace/client/.claude/docs/game-design/quests-gdd.md)

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
   - [Жизненный цикл квеста](#lifecycle)
   - [Окно 3 часа, цепочка, сутки](#windows)
   - [Туториал (удалён из квестов)](#tutorial)
2. [Референсы](#references)
3. [Паттерны](#patterns)
   - [Настраиваемая награда квеста](#pattern-configurable-reward)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`QuestsUserComponent`](#cls-questsusercomponent)
   - [`QuestsUserComponent.DBFields`](#cls-dbfields)
   - [`QuestEvent`](#cls-questevent)
   - [`QuestData`](#cls-questdata)
   - [`UserResetQuests` + миграция](#cls-userresetquests)
   - [`HomePage` (квестовые роуты)](#cls-homepage)
   - [`DevToolsPage` (квестовые dev-роуты)](#cls-devtoolspage)
   - [Источники прогресса (вызовы `triggerEvent`)](#progress-sources)
   - [Персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
9. [Карта файлов компонента](#file-map)
   - [Файлы прямого влияния](#file-map-direct)
   - [Файлы косвенного влияния](#file-map-indirect)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

У игрока в каждый момент **один** активный квест: "сделай N действий типа X" (призыв в поезде,
заработать серебро, уничтожить танки и т.п.). Прогресс начисляет сервер из игровых роутов
([источники](#progress-sources)); клиент только читает состояние и просит забрать награду.
Награда — схемы танка (`RESOURCE_TANK_SCHEME`), которые тратятся на призыв в поезде.

Состояние хранится во вложенном документе `Quests` пользователя
([персистентность](#persistence)), отдельного DAO нет.

<a id="lifecycle"></a>
### Жизненный цикл квеста

1. **Выдача.** При сбросе (см. ниже) или после завершения предыдущего квеста сервер выбирает квест из
   [`QuestData.LIST`](#cls-questdata) (см. ГДД [#gdd-quest-list](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-quest-list)), вычисляет стартовый `progress` и цель `requiredProgress`, и
   сразу фиксирует награду `reward` (тип и количество) — см. [`gainNewQuest(int)`](#m-gainnewquest-id) (выбор задания: ГДД [#gdd-quest-choice](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-quest-choice)).
2. **Прогресс.** Игровые роуты зовут [`triggerEvent(event, value)`](#m-triggerevent); засчитывается
   только событие того же типа, что у текущего квеста; прогресс ограничен сверху целью. Каждое
   засчитанное изменение шлёт клиенту push `/events/quest/update`. Что засчитывается — см. ГДД [#gdd-progress-sources](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-progress-sources).
3. **Завершение.** Клиент вызывает `/ingame/home/completeQuest` → [`completeQuest()`](#m-completequest):
   если `progress >= requiredProgress` — награда кладётся в сумку, счётчики растут, выдаётся следующий
   квест.

<a id="windows"></a>
### Окно 3 часа, цепочка, сутки

- **Окно** — `RESET_EVERY = 3 ч` (см. ГДД [#gdd-refresh](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-refresh)). Сброс ленивый: выполняется в [`apiResponse()`](#m-apiresponse), если
  с `resetTime` прошло больше 3 ч. Сброс обнуляет `completedQuests` и **заменяет
  текущий квест на квест id=1** (`TRAIN_SUMMON`), даже если прежний не завершён.
- **Цепочка** — `QUESTS_PER_CHAIN = 6` квестов за окно (см. ГДД [#gdd-refresh](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-refresh)). После 6-го завершения новый квест не
  выдаётся: `questId = 0`, `progress = requiredProgress = 0` до следующего сброса.
- **Сутки** — `completedChain` (сколько раз за сутки дошли до 6) обнуляется при первом сбросе в новые
  календарные сутки (`DateUtil.isToday` — по часовому поясу JVM). От него зависит количество схем в
  награде: `completedChain == 0` → 3, `== 1` → 2, дальше → 1.
- Тип схемы — всегда танковая (`RESOURCE_TANK_SCHEME`); бросок 50/50 на самолётную удалён merge'ем
  (по ГДД [#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward)).

<a id="tutorial"></a>
### Туториал (удалён из квестов)

После merge в `QuestsUserComponent` нет ни одной туториальной ветки: `TutorialSteps`, `TutorialData.TUTORIAL_QUESTS`
и `LAST_QUEST_*` удалены, квесты id 11–15 убраны из `QuestData.LIST`, поле `isEndless` (ключ `endless`) удалено
из компонента, `apiResponse()` и push `/events/quest/update` (поле `tutorial` в нём тоже убрано), `HomePage.completeQuest`
не добавляет `tutorial`. Шаги туториала квестами больше не двигаются. Старое значение `endless` в документах
пользователей осталось «сиротой» и не читается. Туториал — [tutorial-architecture.md](tutorial-architecture.md).

<a id="references"></a>
## 2. Референсы

Внешних референсов нет — документ описывает существующий код. Смежные серверные документы:

- [achievements-architecture.md#progress-sources](achievements-architecture.md#progress-sources) —
  те же боевые роуты `CampaignPage` начисляют прогресс достижений (та же оговорка про лимит серебра и
  отсутствие проверки, что техника была в бою).
- [airdrop-architecture.md](airdrop-architecture.md) — золото из ящиков квестовых событий не
  триггерит (там же п. про отсутствие `QuestEvent` для золота).
- [assembly-architecture.md](assembly-architecture.md) — "Сборка" работает с **частями** схем
  (`*_SCHEME_PARTS`), квесты выдают **целые** схемы (`*_SCHEME`) — разные ресурсы.
- [tank-airplane-data-architecture.md#consumers](tank-airplane-data-architecture.md#consumers) — откуда
  берётся `power` техники, по которому `TrainPage`/`MilitaryBasePage` решают, слать ли
  `BETTER_TANK`/`BETTER_AIRPLANE`.
- Правила персистентности (`changedField`, `dbMappingBuild`) — агент `server-developer-db-persistence`.

<a id="patterns"></a>
## 3. Паттерны

- **Авторитетный сервер.** Клиент не передаёт ни прогресс, ни награду: прогресс считается в
  серверных роутах, награда фиксируется при выдаче квеста.
- **Ленивый сброс по времени** в методе чтения (`apiResponse()` → `reset()`), без планировщика.
- **Справочник-константа** `ImmutableMap<Integer, QuestData>` в коде (не в `balance.json`).
- **Покомпонентная персистентность через `changedField`** в поддокумент `Quests` пользователя.
- **Разовый скрипт-миграция** (`AbstractScript` + JSON в `resources/migrations`) для массовой правки
  документов.

<a id="pattern-configurable-reward"></a>
### Настраиваемая награда квеста

Статус: **проект, не реализовано** (ветка `koba/lootbox`, 2026-10-27). Вариант устройства не выбран, см. вопросы ниже. ГДД: [#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward). ТЗ: `/workspace/client/.claude/docs/game-design/incoming/lootbox-source.md` («Задания поезда»).

**Что есть сейчас (по коду).**
- Награда квеста не лежит в `QuestData.LIST`. Она создаётся в `QuestsUserComponent.gainNewQuest(int)`: `Resource.createNew(ItemId.RESOURCE_TANK_SCHEME, true)` и количество 3/2/1 по `completedChain` (правило [#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward)).
- Поле `reward` уже имеет тип `Item`, а не «схема». Хранение (`rew`, `Item.dbToData`, чтение через `ItemFactory.newFromDocument`), выдача (`completeQuest` → `user().addItem(reward)`) и ответ клиенту (`reward.apiResponse()`) от конкретного типа предмета не зависят. Менять нужно только место создания награды.

**Что переиспользовать.**
- `Item` + `ItemType` + `ItemFactory` ([bag-architecture.md#cls-item](bag-architecture.md#cls-item)) как единый тип награды. Новый тип награды (лутбокс, позже генерал) = новый `ItemType` + регистрация в `ItemFactory`. Отдельный формат награды квеста не нужен.
- `OfferRewardData` ([offers-architecture.md#cls-small](offers-architecture.md#cls-small)) не подходит: фиксированный список `Item` плюс цена набора, без случайности и без зависимости от состояния игрока. Брать из него только идею «награда = `Item`».
- `CollectionUserComponent.grantReward` в коде не найден; `createSellCollectionItemReward` выдаёт награду за продажу предмета коллекции и к квестам отношения не имеет.
- Web-рекомендаций по теме нет (индекс пуст), `web-librarian` не вызывался.

**Требования, которые нужно учесть.**
1. `User.addItem(Item)` кладёт предмет только если он `BagItem`; для остальных типов ветка пустая и награда пропадёт без ошибки (так сейчас ведёт себя `COLLECTION_ITEM`, см. [bag-architecture.md#cls-item](bag-architecture.md#cls-item)). Новый тип награды должен быть `BagItem` либо `User.addItem` должен получить явную ветку; выбор зависит от того, где лежат лутбоксы (вопрос 2).
2. Правило «какая награда у этого квеста» одно ([#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward)) и должно жить в одной функции у владельца (`QuestsUserComponent`, либо у стратегии, если выберут вариант Б). Сейчас оно вшито в `gainNewQuest(int)`; второго места быть не должно.
3. Фиксация награды при выдаче квеста (а не при завершении) сохраняется: качество лутбокса определяется и пишется в `rew` в `gainNewQuest`, клиент видит его в слоте до выполнения. Старые документы с `rew` = схема остаются валидными.
4. Порядок вызовов у вызывающего не нужен: создание награды и запись `changedField(REWARD_FIELD, ...)` остаются в одном методе владельца.

**Варианты устройства (выбирает пользователь).**
- **А. Один метод создания награды в `QuestsUserComponent`.** `gainNewQuest(int)` вызывает `createReward()`; замена схем на лутбокс правит только этот метод. Новых классов нет. Минус: каждая новая награда снова правит компонент.
- **Б. Стратегия награды.** Интерфейс `QuestRewardStrategy` с методом `Item create(User user, int completedChain)` и `ImmutableMap`/поле с текущей стратегией (в стиле `ItemFactory`, без рефлексии). Реализации: схемы, лутбокс; генерал добавляется классом. Минус: один интерфейс с единственной живой реализацией, пока не появится вторая.
- **В. Награда как поле `QuestData`.** Поле `reward` в `QuestData` (по квесту) вместо вычисления по цепочке. Подходит, если награда должна зависеть от id квеста; для ТЗ (качество лутбокса, шансы по качеству) без такой зависимости не нужна. Награда по цепочке (3/2/1) в это поле не ложится.
- Конфиг в `balance.json` / `MongoDB` для таблицы шансов качеств возможен при любом варианте; сейчас баланс квестов в коде (п.11 [#tradeoffs](#tradeoffs)). Вопрос 4.

**Открытые вопросы.**
1. Противоречие ТЗ и ГДД: [#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward) говорит «награда только схемы танка, количество 3/2/1 по сериям», ТЗ заменяет её на лутбокс одного из 10 качеств, на макете без числа. Нужно решение: схемы убираются совсем или остаются в части заданий/серий; остаётся ли зависимость от серии за сутки (3/2/1) и как она отражается на качестве лутбокса. ГДД не правился.
2. Где хранится лутбокс: стакуемый `BagItem` (id = качество, `count`) в сумке или отдельный компонент со слотами и таймерами открытия. Влияет на пункт 1 требований; решается в области «Лутбоксы», не в квестах.
3. Как выбирается качество лутбокса за задание (таблица шансов в ТЗ пустая, ссылка «Расчеты» без данных) и от чего оно зависит.
4. Где хранить таблицу шансов и количества схем: в коде (как сейчас) или в `balance.json`.
5. Двойное нажатие «забрать», обрыв сети между `addItem` и ответом, две вкладки: уже описаны в [#tradeoffs](#tradeoffs) п.1 (повторная выдача после конца цепочки). С лутбоксами дефект даёт бесконечные сундуки вместо схем, поэтому его исправление стоит включить в задачу. В ГДД поведение не описано.

<a id="class-list"></a>
## 4. Список классов

Область (пакет `com.linkedgames.game`):

| Класс | Файл |
|-------|------|
| `QuestsUserComponent` (+ вложенный `DBFields`) | `game/src/main/java/com/linkedgames/game/model/quests/QuestsUserComponent.java` |
| `QuestEvent` | `.../model/quests/QuestEvent.java` |
| `QuestData` | `.../model/quests/data/QuestData.java` |
| `UserResetQuests` | `.../scripts/UserResetQuests.java` |
| миграция | `game/src/main/resources/migrations/1758700043392_reset_quests.json` |

Точки соприкосновения вне области (описаны только квестовые части):
`User`, `HomePage`, `DevToolsPage`, `TrainPage`, `MilitaryBasePage` (новая область «военная база»,
не документируется здесь), `CampaignPage`, `CampaignUserComponent`, `CollectionUserComponent`,
`AlbumsSectionType`, `ExperimentalTanksSectionType`.

<a id="anchors"></a>
## 5. Навигация (якоря)

Методы `QuestsUserComponent`: [`reset`](#m-reset) · [`triggerEvent`](#m-triggerevent) ·
[`completeQuest`](#m-completequest) · [`completeProgress`](#m-completeprogress) ·
[`gainNewQuest(int)`](#m-gainnewquest-id) · [`gainNewQuest()`](#m-gainnewquest) ·
[`onQuestUpdateNotification`](#m-onquestupdatenotification) · [`dbMappingBuild`](#m-dbmappingbuild) ·
[`apiResponse`](#m-apiresponse).
Сквозные разделы: [`#progress-sources`](#progress-sources) · [`#persistence`](#persistence) ·
[`#client-contract`](#client-contract) · [`#tradeoffs`](#tradeoffs).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Роль | Раздел |
|-------|------|--------|
| `QuestsUserComponent` | состояние, выдача, прогресс, награда, сброс, push | [#cls-questsusercomponent](#cls-questsusercomponent) |
| `QuestsUserComponent.DBFields` | ключи полей в Mongo | [#cls-dbfields](#cls-dbfields) |
| `QuestEvent` | типы событий, режим SET/ADD | [#cls-questevent](#cls-questevent) |
| `QuestData` | справочник квестов | [#cls-questdata](#cls-questdata) |
| `UserResetQuests` | миграция сброса счётчиков | [#cls-userresetquests](#cls-userresetquests) |
| `HomePage` | роуты чтения/завершения | [#cls-homepage](#cls-homepage) |
| `DevToolsPage` | отладочные роуты | [#cls-devtoolspage](#cls-devtoolspage) |
| Train/MilitaryBase/CampaignPage, CampaignUserComponent, CollectionUserComponent, Albums/ExperimentalTanksSectionType | источники прогресса | [#progress-sources](#progress-sources) |

## 7. Классы и методы

<a id="cls-questsusercomponent"></a>
### `QuestsUserComponent extends UserChildComponent implements APIResponseStd`

Создаётся лениво в `User.getQuestsUserComponent()` (имя компонента `"Quests"`). Поля: `questId`,
`progress`, `requiredProgress`, `resetTime`, `completedQuests`, `completedChain`, `reward` (`Item`).
Константы: `RESET_EVERY = 3 ч`, `QUESTS_PER_CHAIN = 6`.

Тривиальные: `modifyReceiver` — пустой; `reset()` = `reset(false)`.

<a id="m-afterdbmappingbuild"></a>
**`afterDBMappingBuild()`** — если `questId != 0` и его нет в `QuestData.LIST` (например, туториальные
11–15 у старых пользователей) → `reset(true)`: загрузка пользователя пишет в БД и выдаёт квест id=1.

<a id="m-reset"></a>
**`reset(boolean hard)`** — сброс окна.
- `hard == false` и с `resetTime` прошло ≤ 3 ч → выход.
- Новые сутки относительно `resetTime` → `completedChain = 0`.
- `completedQuests = 0`, `resetTime = now`.
- `gainNewQuest(1)`.

<a id="m-triggerevent"></a>
**`triggerEvent(QuestEvent event, int value)`** — начисление прогресса (см. ГДД [#gdd-progress-sources](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-progress-sources)).
- Выход, если квеста `questId` нет в `LIST` (в т.ч. `questId == 0`), тип события не совпадает
  (сравнение `ordinal()`), или цель уже достигнута.
- SET-событие (`CAMPAIGN_LEVEL_UP`) → `progress = value`; ADD → `progress += value`; затем
  ограничение `progress <= requiredProgress`.
- Сохранение `progress`, push [`onQuestUpdateNotification`](#m-onquestupdatenotification).

<a id="m-completequest"></a>
**`completeQuest()`** — завершение, возвращает JSON-массив наград или `null` (см. ГДД [#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward) и [#gdd-progress-start](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-progress-start)).
- `progress < requiredProgress` → `null` (роут отвечает ошибкой).
- `reward != null` → `user().addItem(reward)`; `reward` — шаблон (`Resource.createNew(..., true)`,
  пустой uid), сумка кладёт копию. В массив — `reward.apiResponse()`.
- `completedQuests++`; если стало `>= 6` → `completedChain++`.
- Следующий квест — всегда `gainNewQuest()` (случайный).

<a id="m-completeprogress"></a>
**`completeProgress()`** — dev: `progress = requiredProgress`, сохранение, push. Проверок нет.

<a id="m-gainnewquest-id"></a>
**`gainNewQuest(int id)`** (private) — выдача конкретного квеста (награда — см. ГДД [#gdd-reward](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-reward)).
- `questId = id`; `progress = QuestData.getCurrentValue(user)`;
  `requiredProgress = QuestData.getRequiredValue(user)`.
- Награда: танковые схемы, количество по `completedChain` (3/2/1, см. [окна](#windows)).
- Сохраняются все изменённые поля, `reward` — как `reward.dbToData()`. Push не шлёт.
- `id`, которого нет в `LIST`, даст NPE — вызывающие передают только существующие id.

<a id="m-gainnewquest"></a>
**`gainNewQuest()`** (private) — случайный квест (см. ГДД [#gdd-quest-choice](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-quest-choice)).
- Кандидаты: все `QuestData` с `canBeCompleted(user) == true` (всегда `true`) и `!disabled` —
  т.е. id 1–4, 8–10 (5–7 отключены), равновероятно.
- `completedQuests >= 6` или кандидатов нет → `questId = 0`, `progress = requiredProgress = 0`;
  **`reward` при этом не обнуляется** (см. [#tradeoffs](#tradeoffs) п.1).
- Иначе → `gainNewQuest(id)`.

<a id="m-onquestupdatenotification"></a>
**`onQuestUpdateNotification()`** (private) — WS-событие `/events/quest/update`, payload
`quest: {progress, requiredProgress}`. Вызывается из `triggerEvent` и `completeProgress`, не из
`completeQuest`/`reset` (там новое состояние уходит в ответе роута).

<a id="m-dbmappingbuild"></a>
**`dbMappingBuild(Document)`** — чтение полей с дефолтами (0 / `0L`); `reward`
восстанавливается через `ItemFactory.newFromDocument` + `dbMappingBuild`, только если поддокумент
`rew` есть, не пуст и фабрика вернула не `null`.

<a id="m-apiresponse"></a>
**`apiResponse()`** — **сначала вызывает `reset()`** (побочный эффект с записью в БД), затем JSON:
`id`, `type` (= `event.ordinal()`, только если квест есть в `LIST`), `progress`, `requiredProgress`,
`resetTime` (= момент **следующего** сброса: `resetTime + 3 ч`), `reward`
(`Item.apiResponse()`, если не `null`).

<a id="cls-dbfields"></a>
### `QuestsUserComponent.DBFields`

| Поле | Ключ |
|------|------|
| `questId` | `q` |
| `progress` | `pg` |
| `requiredProgress` | `rpg` |
| `resetTime` | `rt` |
| `completedQuests` | `coq` |
| `completedChain` | `coc` |
| `reward` | `rew` (поддокумент `Item.dbToData()`) |

<a id="cls-questevent"></a>
### `QuestEvent` (enum)

Что засчитывается (см. ГДД [#gdd-progress-sources](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-progress-sources)).

`TRAIN_SUMMON(0)`, `AERODROME_SUMMON(1)`, `CAMPAIGN_LEVEL_UP(2)`, `TANK_SELL(3)`,
`BATTLE_SILVER_COINS_GAINED(4)`, `BETTER_TANK(5)`, `BETTER_AIRPLANE(6)`, `TANK_DESTROY(7)`,
`AIRPLANE_DESTROY(8)`, `SILVER_COINS_GAINED(9)`. Поле `id` совпадает с `ordinal()`.

- `isSetValue()` — `id == CAMPAIGN_LEVEL_UP.ordinal()`: прогресс присваивается (значение — текущий
  уровень кампании).
- `isAddValue()` — `!isSetValue()`: прогресс прибавляется.

Клиенту уходит `ordinal()` как `type`.

<a id="cls-questdata"></a>
### `QuestData`

Поля: `id`, `event`, `minRequiredValue`, `maxRequiredValue`, `disabled` (по умолчанию `false`; бывшее `isTutorial`): отключённый квест остаётся в `LIST`
(прогресс по нему считается, если он уже выдан), но не выбирается случайной выдачей.

`LIST` (id → событие, диапазон цели; см. ГДД [#gdd-quest-list](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-quest-list)):

| id | Событие | Цель | Отключён |
|----|---------|------|----------|
| 1 | `TRAIN_SUMMON` | 10–20 | |
| 2 | `BATTLE_SILVER_COINS_GAINED` | 50–200 | |
| 3 | `AERODROME_SUMMON` | 5–10 | |
| 4 | `TANK_SELL` | 5–10 | |
| 5 | `CAMPAIGN_LEVEL_UP` | уровень + 1 | отключён |
| 6 | `BETTER_TANK` | 1 | отключён |
| 7 | `BETTER_AIRPLANE` | 1 | отключён |
| 8 | `TANK_DESTROY` | 20–40 | |
| 9 | `AIRPLANE_DESTROY` | 20–40 | |
| 10 | `SILVER_COINS_GAINED` | 100–400 | |

Отключены (`disabled = true`): 5 `CAMPAIGN_LEVEL_UP`, 6 `BETTER_TANK`, 7 `BETTER_AIRPLANE`. Квесты 11–15
(туториал) удалены.

- `getCurrentValue(user)` — `CAMPAIGN_LEVEL_UP` → текущий уровень кампании, остальные → 0.
- `getRequiredValue(user)` — `CAMPAIGN_LEVEL_UP` → уровень + 1, остальные →
  `nextIntInclusive(min, max)`.
- `canBeCompleted(user)` — всегда `true` (заглушка фильтра; см. ГДД [#gdd-unavailable](/workspace/client/.claude/docs/game-design/quests-gdd.md#gdd-unavailable)).

<a id="cls-userresetquests"></a>
### `UserResetQuests extends AbstractScript` + миграция

Запускается миграцией `1758700043392_reset_quests.json` (`type: script`). Для каждого
пользователя с поддокументом `Quests` выставляет `rt = 0`, `coq = 0`, `coc = 0` и перезаписывает
поддокумент через `$set`. `q`, `pg`, `rpg`, `rew` не трогает. Эффект наступает при
следующем `apiResponse()`: `resetTime = 0` → сброс окна. Поле `endless`, если есть в документах, скрипт не трогает и
компонент его не читает.

<a id="cls-homepage"></a>
### `HomePage` (`/ingame/home`, квестовые роуты)

- `""` (index) — payload включает `quest` (`apiResponse()`, т.е. с ленивым сбросом); остальные блоки (поезд, ангар, сборка и т.д.) — вне области.
- `/getQuest` — `quest`.
- `/completeQuest` — `completeQuest()`; `null` → ошибка; иначе `rewards`, `quest`.

<a id="cls-devtoolspage"></a>
### `DevToolsPage` (`/ingame/devTools`, только при `app.devTools=true`)

- `/completeQuest` — `completeProgress()` (довести прогресс до цели; награду не выдаёт). Аэродромные dev-роуты удалены, добавлен `/userDollars` (не квестовый).
- `/resetQuest` — `reset(true)` + `quest` в ответе.

<a id="progress-sources"></a>
### Источники прогресса (вызовы `triggerEvent`)

| Событие | Где | Значение / условие |
|---------|-----|--------------------|
| `TRAIN_SUMMON` | `TrainPage.actionSummon` | +1 и при выпадении предмета коллекции, и при выпадении танка |
| `AERODROME_SUMMON` | `MilitaryBasePage` (запуск производства самолёта, ~стр. 507) | +1 при запуске производства на фабрике, не при получении самолёта |
| `CAMPAIGN_LEVEL_UP` | `CampaignUserComponent.levelCompeted` (из `CampaignPage.actionBattleResult`) | SET = новый уровень, только при победе |
| `TANK_SELL` | `TrainPage.actionAccept` / `actionRefuse` | +1: при принятии — если был заменяемый танк; при отказе — всегда |
| `BETTER_TANK` | `TrainPage.actionAccept` | +1, если заменяемого нет или `power` нового больше |
| `BETTER_AIRPLANE` | `MilitaryBasePage` (принятие самолёта с фабрики) | +1, если заменяемого нет или `power` выше |
| `BATTLE_SILVER_COINS_GAINED` | `CampaignPage.actionBattleTankReward` | + серебро за танк, только если `getSilverCoinsReward() != 0` |
| `TANK_DESTROY` | `CampaignPage.actionBattleTankReward` | +1, **только если серебро не упёрлось в лимит** (иначе ранний выход) |
| `AIRPLANE_DESTROY` | `CampaignPage.actionBattleAirplaneReward` | +1 всегда, без лимита |
| `SILVER_COINS_GAINED` | `CampaignPage.actionBattleTankReward`; `TrainPage` `actionAccept`/`actionRefuse` и `MilitaryBasePage` принятие/отказ от самолёта (если серебро > 0); `CollectionUserComponent.grantReward` для любой награды-серебра (продажа дубля через `addDuplicateReward`, награды альбомов `AlbumsSectionType`, `ExperimentalTanksSectionType`) | + количество серебра (`(int) reward.getCount()`, `getCount()` стал `long`) |

Не триггерят квесты: золото (AirDrop, награды глав), PvP/battlefield, ранговые вызовы. Отказ от самолёта
на военной базе шлёт только `SILVER_COINS_GAINED`.

<a id="persistence"></a>
### Персистентность

- Поддокумент `User.DBFields.P_QUESTS_FIELD = "Quests"`; чтение в `User` —
  `getQuestsUserComponent().dbMappingBuild(...)`, если ключ есть, затем `afterDBMappingBuild()`.
- Запись — только точечные `changedField(DBFields.X, value)` (путь `Quests.<ключ>`); собственного
  `dbToData()` у компонента нет, начального документа не создаётся — поля появляются по мере первых
  изменений (обычно при первом `apiResponse()`: `resetTime = 0` → сброс → выдача квеста).
- Отдельного DAO нет.

<a id="client-contract"></a>
### Контракт с клиентом

- Состояние квеста — JSON [`apiResponse()`](#m-apiresponse) в `/ingame/home`, `/getQuest`,
  `/completeQuest`, dev `/resetQuest`.
- Push `/events/quest/update` — `{quest: {progress, requiredProgress}}`. На клиенте
  подписка есть в `src/plain/GameEvents.ts` (`g/ws/events/quest/update`); как клиент использует данные —
  не проверялось.
- Награда — `rewards` (массив `Item.apiResponse()`) в ответе `/completeQuest`.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и подозрительные места

Всё — по чтению кода, запуском не проверялось.

> **Отложено (решение пользователя, 2026-09-28):** пункты ниже сейчас не исправляются (п.1 подтверждён
> повторной сверкой с кодом — рабочая уязвимость). При любой новой задаче, затрагивающей квесты
> (`QuestsUserComponent`/`QuestEvent`/`QuestData`/`UserResetQuests`, квестовые роуты), — предложить
> пользователю включить их исправление в задачу (приоритет: п.1), предварительно сверив с актуальным кодом.

1. **Повторная выдача награды после конца цепочки.** После 6-го завершения `gainNewQuest()` ставит
   `questId = 0`, `progress = requiredProgress = 0`, но оставляет прежний `reward`. Проверка в
   `completeQuest` — только `progress < requiredProgress` (0 < 0 ложно), `questId` не проверяется.
   Значит, каждый повторный `/ingame/home/completeQuest` до сброса окна снова кладёт в сумку ту же
   награду (шаблон копируется сумкой) и растит `completedQuests`/`completedChain`. Защищает ли клиент
   — не проверено. Аналогично для нового пользователя до первого `apiResponse()` (там `reward == null`,
   поэтому награды нет, но счётчики растут и выдаётся квест).
   По ГДД (#gdd-refresh, решение пользователя 2026-10-15) — расхождение, исправление отложено.
2. **Сброс внутри чтения.** `apiResponse()` мутирует и сохраняет состояние; любой роут, отдающий
   `quest`, может сменить квест.
3. **Сброс окна заменяет незавершённый квест** и всегда на id=1 (`TRAIN_SUMMON`) —
   первый квест окна не случайный.
4. **`completedChain++` на каждом завершении при `completedQuests >= 6`**, а не один раз на цепочку
   (важно в связке с п.1).
5. **`TANK_DESTROY` зависит от лимита серебра**, `AIRPLANE_DESTROY` — нет; оба без проверки, что
   техника была в бою (`if (true) // TODO` в `CampaignPage`, см.
   [achievements-architecture.md#progress-sources](achievements-architecture.md#progress-sources)).
   По ГДД (#gdd-progress-sources, решение пользователя 2026-10-15) — расхождение, исправление отложено.
6. **Удалено merge'ем:** `isEndless` и туториальная выдача. Остаточный риск — старые `endless` и
   туториальные `questId` 11–15 в документах: `afterDBMappingBuild` сбрасывает такой квест на id=1.
7. **Хрупкость `QuestEvent`:** `isSetValue` сравнивает `id` с `ordinal()`, `triggerEvent` —
   `ordinal()` вместо сравнения enum; клиенту уходит `ordinal()`. Переупорядочивание enum сломает
   контракт и логику.
8. **Мёртвый код:** `canBeCompleted` всегда `true`, пустой `modifyReceiver`.
   По ГДД (#gdd-unavailable, решение пользователя 2026-10-15) — расхождение, исправление отложено.
9. **`gainNewQuest(int)` без проверки id** — NPE при отсутствующем id (сейчас не достижимо).
10. **Сутки по часовому поясу JVM** (`DateUtil.isToday` через `GregorianCalendar` по умолчанию).
11. **Баланс в коде**, не в `balance.json`: цели, количество схем (3/2/1), окно 3 ч, 6 квестов.
12. **`UserResetQuests`** перезаписывает весь поддокумент `Quests` значением, прочитанным в начале
    итерации (`$set` целиком) — при работе на живом сервере возможна потеря параллельных изменений
    онлайн-игрока.

<a id="file-map"></a>
## 9. Карта файлов компонента

Пути от корня репозитория `server`. Полнота проверена `grep` по `QuestsUserComponent`, `QuestEvent`,
`QuestData`, `UserResetQuests`, `getQuestsUserComponent`, `P_QUESTS_FIELD`, `triggerEvent` (2026-10-19).

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|------|------|
| `game/src/main/java/com/linkedgames/game/model/quests/QuestsUserComponent.java` | состояние квеста, выдача, прогресс, награда, сброс, push |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestEvent.java` | enum типов событий и режима SET/ADD |
| `game/src/main/java/com/linkedgames/game/model/quests/data/QuestData.java` | справочник квестов |
| `game/src/main/java/com/linkedgames/game/scripts/UserResetQuests.java` | скрипт сброса счётчиков квестов |
| `game/src/main/resources/migrations/1758700043392_reset_quests.json` | миграция, запускающая `UserResetQuests` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/HomePage.java` | роуты `/ingame/home`, `/getQuest`, `/completeQuest` |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|------|------|
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | геттер компонента, `modifyReceiver`, `P_QUESTS_FIELD`, `dbMappingBuild`/`afterDBMappingBuild` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` | dev-роуты `/completeQuest`, `/resetQuest` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/TrainPage.java` | источник прогресса: призыв, продажа, лучший танк, серебро |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/MilitaryBasePage.java` | источник прогресса: `AERODROME_SUMMON`, `BETTER_AIRPLANE`, серебро (область «военная база» не документируется здесь) |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` | источник прогресса: серебро и уничтожение техники в бою |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` | источник прогресса: `CAMPAIGN_LEVEL_UP` |
| `game/src/main/java/com/linkedgames/game/model/collections/CollectionUserComponent.java` | источник прогресса: `grantReward` → `SILVER_COINS_GAINED` (продажа дубля и др. награды-серебро) |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/AlbumsSectionType.java` | награды альбомов через `grantReward` (серебро засчитывается) |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/ExperimentalTanksSectionType.java` | источник прогресса: `TANK_SELL`, `BETTER_TANK` при принятии/продаже ожидающего танка |
