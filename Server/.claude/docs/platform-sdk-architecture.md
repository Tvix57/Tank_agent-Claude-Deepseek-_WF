# Интеграции с площадками: награда за ярлык игры Яндекс Игр — `YandexUserComponent` (сервер)

Документ составлен `server-analyst-platform-sdk` по итогам разработки (саммари `server-developer-platform-sdk`), 2026-10-26;
пользователь одобрил изменения 2026-10-26. Описана только фича «ярлык»: остальной код `service/integration/**`
(`IntegrationUtil`, `SocialPortal`, `VKUtil`, `OdnoklassnikiUtil`, `OvermobileService`, `YookassaUtil`) и авторизация через
площадку в `GatewayPage` здесь не документируются. Платёжный конвейер — [offers-architecture.md](offers-architecture.md).
Клиентская сторона (диалог площадки, окно, «!») — зона client; контракт сверяет `integration-lead`.

ГДД: [platform-sdk-gdd.md](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md). Правила сервера: [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward), [#gdd-outcomes](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-outcomes).

ПРОСКАНИРОВАНО (прочитаны целиком):
- `game/src/main/java/com/linkedgames/game/service/integration/yandex/YandexUserComponent.java`
- `game/src/main/java/com/linkedgames/game/service/integration/yandex/ShortcutRewardStatus.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/YandexPage.java`
- `game/src/main/java/com/linkedgames/game/model/user/UserChildComponent.java`

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация](#anchors) (этот список и якоря разделов)
6. [Оглавление по классам](#class-nav)
7. Классы и методы: [`YandexUserComponent`](#cls-component) · [`ShortcutRewardStatus`](#cls-status) · [`YandexPage`](#cls-page) · [`User`](#cls-user) · [`DevToolsPage`](#cls-dev)
8. [Принятые риски и компромиссы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов](#file-map)
11. [Контракт client↔server](#contract) · [БД](#db) · [История решений](#history)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Разовая награда за ярлык игры, созданный через shortcut SDK Яндекс Игр. Диалог создания ярлыка показывает клиент; после
согласия игрока клиент просит награду у сервера. Подтвердить ярлык серверу нечем, поэтому сервер проверяет только свои
условия: награда ещё не выдана, игрок не забанен, состав награды не пуст.

Состав награды задан в коде компонента и в `balance.json` не хранится. Сейчас там заглушка (золото ×1, серебро ×1), числа
поправят перед релизом ([ГДД #gdd-open](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-open)). Отметка «награда выдана» лежит на аккаунте
и переносится и сбрасывается вместе с ним.

<a id="references"></a>
## 2. Референсы

Нет. Документация SDK (https://yandex.ru/dev/games/doc/ru/sdk/sdk-shortcut) относится к клиенту.

<a id="patterns"></a>
## 3. Паттерны

- Дочерний компонент пользователя: `UserChildComponent`, ленивое создание в `User.getYandexUserComponent()`, подгрузка
  через `dbMappingBuild`, запись плоским `changedField`.
- Boolean-флаг в поддокументе компонента хранится как `boolean` (`document.getBoolean(поле, false)`), а не как int 0/1, как
  `State.fl`.
- Переход состояния и его предусловия в одном методе владельца ([#no-implicit-order](/workspace/client/.claude/docs/agent-system-workflow.md#no-implicit-order)):
  `sendShortcutReward` сам проверяет «выдано», состав и бан, сам ставит отметку и выдаёт предметы.
- Выдача в `UserActor` синхронно: два запроса (две вкладки) выполняются по очереди, награда одна.

<a id="class-list"></a>
## 4. Список классов

Создано:
- `service/integration/yandex/YandexUserComponent` — компонент.
- `service/integration/yandex/ShortcutRewardStatus` — исход выдачи.
- `pages/ws/ingame/YandexPage` — роут `/ingame/yandex/sendShortcutReward`.

Изменено:
- `model/user/User` — поле, ленивый геттер, `account.yandexShortcut` в gateway, `dbMappingBuild`, `P_YANDEX_FIELD`, `isBanActive()`, `isNotBanned()`.
- `pages/WSRouter` — регистрация `/ingame/yandex`.
- `pages/ws/ingame/dev/DevToolsPage` — `/ingame/devTools/shortcutRewardReset`.

<a id="anchors"></a>
## 5. Навигация

Якоря: `#purpose`, `#references`, `#patterns`, `#class-list`, `#class-nav`, `#cls-component`, `#cls-status`, `#cls-page`,
`#cls-user`, `#cls-dev`, `#tradeoffs`, `#gdd-link`, `#file-map`, `#contract`, `#db`, `#history`.

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `YandexUserComponent` | [#cls-component](#cls-component) |
| `ShortcutRewardStatus` | [#cls-status](#cls-status) |
| `YandexPage` | [#cls-page](#cls-page) |
| `User` (изменения) | [#cls-user](#cls-user) |
| `DevToolsPage`, `WSRouter` (изменения) | [#cls-dev](#cls-dev) |

<a id="cls-component"></a>
## 7. `YandexUserComponent`

`extends UserChildComponent`, лежит в `service/integration/yandex/` по решению пользователя. Владеет и отметкой, и правилом
состава. Поля: `SHORTCUT_REWARD` (private static `ImmutableMap` resourceId→count: `RESOURCE_GOLDEN_COINS` ×1,
`RESOURCE_SILVER_COINS` ×1), `shortcutRewardTaken` (boolean). Конструктор `(User, componentName)` — тривиальный.

- `createShortcutReward()` (private static) — собирает состав: `Resource.createNew` + `setCount`, проверка `isAvailable()`.
  Хотя бы одна битая запись — весь состав пуст (чтобы gateway и выдача не расходились). Правило: состав награды, [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward).
- `sendShortcutReward()` → `ShortcutRewardStatus` — выдача. Порядок проверок:
  1. отметка стоит → `TAKEN` (в том числе забаненному);
  2. состав пуст или `user().isBanActive()` → `UNAVAILABLE`, отметка не ставится (после снятия бана награда доступна);
  3. иначе `markShortcutRewardTaken()` + `user().addItems(reward)` → `SEND`.
  Правило: выдача один раз на аккаунт, запрет забаненному, [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward); запрос после согласия, [#gdd-outcomes](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-outcomes).
- `shortcutRewardApiResponse()` → `JSONArray` — состав для клиента: при активном бане `[]`, иначе `Item.apiResponse` каждой записи.
  Единственный источник состава и для gateway, и для роута. Правило: забаненный видит пустой состав, [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward).
- `shortcutApiResponse()` → `{taken, reward}` — состояние для gateway и dev-роута. Правило: состояние награды известно с входа в игру, [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward).
- `DEV_resetShortcutReward()` — сброс отметки для разработки (`changeShortcutRewardTaken(false)`); бизнес-правила нет.
- `dbMappingBuild(Document)` — читает `shortcutReward`, по умолчанию `false`.
- Тривиальные private: `markShortcutRewardTaken()` и `changeShortcutRewardTaken(boolean)` (присвоение поля + `changedField`).
  Первый — именованный переход для `sendShortcutReward`; второй нужен ещё сбросу, поэтому обёртка над ним не дубль правила, а разные смыслы (выдача / сброс).
- `DBFields.SHORTCUT_REWARD_FIELD = "shortcutReward"` (private).

<a id="cls-status"></a>
## `ShortcutRewardStatus`

`enum`: `SEND` (выдано сейчас), `TAKEN` (уже выдано раньше), `UNAVAILABLE` (выдать нельзя: бан или пустой состав). Правило: исходы запроса награды, [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward).

<a id="cls-page"></a>
## `YandexPage`

`extends AuthorizedUserPage`, роут `/sendShortcutReward` без параметров (полный путь `/ingame/yandex/sendShortcutReward`,
регистрация `WSRouter.java:80`). Метод `actionSendShortcutReward` вызывает `sendShortcutReward()` и отвечает по статусу:

| Статус | Ответ |
|---|---|
| `SEND` | ok + `{send: true, reward: ItemJSON[]}` |
| `TAKEN` | ok + `{taken: true}` (не ошибка) |
| `UNAVAILABLE` | error |

Сами ресурсы клиент получает push-ем `/events/bag/update`. Правило: [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward) (ответ «уже выдано», ошибка запроса).

<a id="cls-user"></a>
## `User` (изменённые места)

- `:140` поле `yandex`; `:298-303` ленивый `getYandexUserComponent()` (имя компонента `"Yandex"`).
- `:594` `account.yandexShortcut = shortcutApiResponse()` в `PARAM_FULL` ответа `/pblc/gateway`.
- `:711-713` `dbMappingBuild`: если в документе есть `P_YANDEX_FIELD`, компонент подгружается; `:762` `P_YANDEX_FIELD = "Yandex"`.
- `~:1138` `isBanActive()` = `banType != NONE && !isBanExpired()`: чистая проверка без записи в БД. Нужна, потому что gateway
  не вызывает `banTick`, а `isBanActive` учитывает срок бана без смены состояния. `isNotBanned()` = `!isBanActive()`.
  Правило: бан с учётом срока, [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward).
  Изменение поведения: в `BanPanelPage:404` при истёкшем, но не снятом бане `isNotBanned()` теперь `true` (раньше `false` до `banTick`);
  пользователь это принял.

<a id="cls-dev"></a>
## `DevToolsPage` и `WSRouter`

- `DevToolsPage.java:290-296` `/ingame/devTools/shortcutRewardReset` → `DEV_resetShortcutReward()`, ответ `{yandexShortcut}`.
- `WSRouter.java:80` `addPageRoute("/ingame/yandex", new YandexPage())`.

<a id="tradeoffs"></a>
## 8. Принятые риски и компромиссы

- Сбой между `userToDb` и `bagToDb` оставляет отметку без предметов (решение пользователя 2026-10-26, ГДД #gdd-reward).
- Запрос можно подделать: подтвердить создание ярлыка серверу нечем (решение пользователя 2026-10-26).
- Смена состава требует релиза сервера (решение пользователя 2026-10-26).
- Состав с одной битой записью считается пустым целиком: награда пропадает, а не выдаётся частично.
- Остаток `State.sr` на dev не трогали, в прод он не попадал.
- Неописанные в ГДД случаи вроде «бан снят в сессии» — в [ГДД #gdd-open](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-open).

<a id="gdd-link"></a>
## 9. Связь с ГДД

| Место | Правило |
|---|---|
| `YandexUserComponent.sendShortcutReward`, `createShortcutReward`, `YandexPage` | [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward), [#gdd-outcomes](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-outcomes) |
| `shortcutRewardApiResponse`, `shortcutApiResponse`, `User` gateway | [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward) |
| `User.isBanActive` | [#gdd-reward](/workspace/client/.claude/docs/game-design/platform-sdk-gdd.md#gdd-reward) |

Функции с одним смыслом под разными именами не найдены: состав отдаёт только `shortcutRewardApiResponse`.

<a id="file-map"></a>
## 10. Карта файлов

**Файлы прямого влияния**
- `game/src/main/java/com/linkedgames/game/service/integration/yandex/YandexUserComponent.java` — компонент: отметка, состав, выдача.
- `game/src/main/java/com/linkedgames/game/service/integration/yandex/ShortcutRewardStatus.java` — исход выдачи.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/YandexPage.java` — роут `/ingame/yandex/sendShortcutReward`.

**Файлы косвенного влияния**
- `game/src/main/java/com/linkedgames/game/model/user/User.java` — поле, геттер, gateway `account.yandexShortcut`, БД, `isBanActive`.
- `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` — регистрация `/ingame/yandex`.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java` — dev-сброс отметки.
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BanPanelPage.java` — потребитель `isNotBanned` (`:404`), поведение изменилось.
- `game/src/main/java/com/linkedgames/game/model/user/UserChildComponent.java` — зависимость: база компонента.
- `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` — зависимость: создание и проверка ресурса награды.
- `game/src/main/java/com/linkedgames/game/model/item/ItemId.java` — зависимость: `RESOURCE_GOLDEN_COINS`, `RESOURCE_SILVER_COINS`.
- `game/src/main/java/com/linkedgames/game/model/item/Item.java` — зависимость: `apiResponse` (`{id, itemType, count}`).
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AuthorizedUserPage.java` — зависимость: база страницы.

<a id="contract"></a>
## Контракт client↔server

- Gateway: `account.yandexShortcut = {taken: boolean, reward: ItemJSON[]}`. Забаненному и при пустом составе `reward: []`.
- `/ingame/yandex/sendShortcutReward` — см. таблицу в [`YandexPage`](#cls-page).
- `ItemJSON` = `Item.apiResponse` = `{id, itemType, count}`.
- Пуш `/events/bag/update` — ресурсы в сумку.

<a id="db"></a>
## БД

Поддокумент `users."Yandex"` (`User.DBFields.P_YANDEX_FIELD`), ключ `shortcutReward` (boolean, по умолчанию `false`),
запись плоским `changedField`. Миграций и индексов нет: новых коллекций и фильтров нет.

<a id="history"></a>
## История решений

- Сначала отметка лежала в `StateUserComponent`, состав — в `IntegrationData`; пользователь перенёс всё в отдельный `YandexUserComponent`.
- Роут перенесён с `/ingame/state` на `/ingame/yandex`.
- Состав из баланса заменён кодом сервера (решение пользователя, ГДД #gdd-log).
