# Бан-панель и модерация — `BanPanelPage`, `model.ban`, модераторский чат (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду (код в рамках
> задачи не менялся), 2026-10-18; связан с ГДД 2026-10-18. Всё ниже подтверждено чтением кода, запуском не проверялось.
> Сверка с ТЗ «Бан панель» (с «Правками №1» и «Правками №2» тестировщика) — в [#tradeoffs](#tradeoffs)
> как находки; решений по ним нет. Клиентская сторона здесь упомянута только как потребитель
> роутов; контракт client↔server сверяет `integration-lead`.

ГДД: [ban-gdd.md](/workspace/client/.claude/docs/game-design/ban-gdd.md) (статус «как в коде», 2026-10-18). Ссылки на разделы — у методов ниже и в
[п.9](#gdd-link); расхождения кода с ГДД — [#tradeoffs](#tradeoffs) п.17. Открытые вопросы ГДД,
которые касаются сервера: [О2](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) («Найти IP»), [О3](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) (кто накладывает «Тишину» и «Блок»),
[О4](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) (срок), [О5](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) (запрет в чате модераторов), [О6](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) (права должностных лиц).

Терминология: в коде тип `BanType.BAN` означает запрет на общение в общем чате (кнопки ТЗ
«10 минут» и «Забанить»), `MUTE` — «Тишина» (чат и личные сообщения), `BLOCK` — «Блок» (запрет на
все действия), `BAD_NAME` — блокировка никнейма. Поле БД `User.banStart` хранит время **окончания**
наказания (`DBFields.BAN_END_FIELD = "banStart"`).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`BanPanelPage`](#cls-banpanelpage)
   - [`BanActions` и `UserRights`](#cls-banactions)
   - [Модели `model.ban`](#cls-models)
   - [`BanPanelDao`](#cls-banpaneldao)
   - [Состояние наказания в `User`](#cls-user)
   - [`AccountPage` `/banInfo`](#cls-accountpage)
   - [Проверки при отправке сообщений и удаление сообщений](#cls-chat-checks)
   - [Модераторский чат](#cls-moderators-chat)
   - [Назначение модератора](#cls-admin)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Модератор или админ открывает бан-панель другого игрока и накладывает наказание с причиной и сроком.
Наказание пишется в поля игрока (`User.banType`, `User.endBanTime`, `User.isNameBanned`) и отдельной
записью в коллекцию `ban_history`. Игроку уходят уведомление `accountRefresh` и системное письмо
(письмо сейчас теряется — [mailbox-architecture.md#tradeoffs](mailbox-architecture.md#tradeoffs) п.3).

Правила по коду:

- Должностные лица — `UserRights.MODERATOR` (100) и `ADMIN` (200); «суперпользователь» — любой из
  них. Модератора назначает и снимает админ в веб-админке ([#cls-admin](#cls-admin)).
- Одновременно у игрока может быть одно наказание из `BAN`/`MUTE`/`BLOCK` (поле `banType`) и,
  независимо от него, блокировка ника (`isNameBanned`).
- `BAN` и `MUTE` истекают сами: `User.banTick` сбрасывает `banType` в `NONE` после `endBanTime`.
  `BLOCK` и блокировка ника бессрочны, снимаются только вручную.
- Права по видам: бан чата и блокировка ника — модератор и админ; тишина, блок и поиск по IP —
  только админ; отмену модератор может сделать только для бана чата и блокировки ника
  ([#cls-banactions](#cls-banactions)).
- Заблокированный ник показывается как `app.noviceName` (`Fighter`) — `User.getDisplayName`.
- Применение наказания на сервере ограничено возвратом `banType`/`endBanTime` клиенту: при отправке
  в общий чат и почту и при прочих действиях сервер наказание не проверяет; единственное исключение —
  чат клана, где `ClanChatPage /send` отказывает при `MUTE` ([#tradeoffs](#tradeoffs) п.1).
- Модераторский чат — отдельный канал сообщений для должностных лиц, хранится в коллекции `chat`
  документом `_id: 1`.

<a id="references"></a>
## 2. Референсы

ТЗ «Бан панель» (PDF пользователя, 2026-10-18) с «Правками №1» и «Правками №2»; сверка — в
[#tradeoffs](#tradeoffs) и [#gdd-link](#gdd-link). Пример пагинации из Правок №2 — «магический мир»
(внешний скриншот, в коде не используется).

<a id="patterns"></a>
## 3. Паттерны

- Цепочки `user.createTask(...)` с `actionExecuteWait` в актор целевого игрока (`UserStore`) —
  изменение чужого `User` идёт внутри его актора; запись истории — после.
- Вложенные таски `taskLatestBanHistory` / `taskLatestBadNameHistory` + `UserSignatureCollectorTask`
  для подписей «кто наложил / кто снял».
- Method reference `BanActions.ICanPunish` для проверки прав в общем `punishUser`.
- Чаты — akka-актор с кешем последних 50 сообщений по языку, сохранение в БД только в `postStop`
  (остановка сервера).

<a id="class-list"></a>
## 4. Список классов

Код в задаче не создавался и не менялся. Классы области:
`BanPanelPage`, `BanPanelDao`, `BanType`, `BanActions`, `BanHistoryEntry`, `BanCancelInfo`,
`BanGeneralInfo`, `UserRights`, ban-часть `User`, `AccountPage`, `ChatPage` (`/deleteMessage`),
`ModeratorsChatPage`, `ModeratorsChatService`, `ModeratorsChatMessage`, `ChatDao` (модераторская
часть), `AdminUserInfoPage` (`/moderatorToggle`), `UserDao` (`countIp`, `findByIp`).

<a id="anchors"></a>
## 5. Навигация (якоря)

`#cls-banpanelpage`, `#m-index`, `#m-punish`, `#m-cancel`, `#m-dropname`, `#m-history`, `#m-findip`,
`#cls-banactions`, `#cls-models`, `#cls-banpaneldao`, `#cls-user`, `#cls-accountpage`,
`#cls-chat-checks`, `#cls-moderators-chat`, `#cls-admin`, `#client-contract`, `#tradeoffs`,
`#gdd-link`, `#file-map`.

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `BanPanelPage` | [#cls-banpanelpage](#cls-banpanelpage) |
| `BanActions`, `UserRights` | [#cls-banactions](#cls-banactions) |
| `BanType`, `BanHistoryEntry`, `BanCancelInfo`, `BanGeneralInfo` | [#cls-models](#cls-models) |
| `BanPanelDao` | [#cls-banpaneldao](#cls-banpaneldao) |
| `User` (ban-поля) | [#cls-user](#cls-user) |
| `AccountPage` | [#cls-accountpage](#cls-accountpage) |
| `ChatPage`, `ChatService.deleteMessage` | [#cls-chat-checks](#cls-chat-checks) |
| `ModeratorsChatPage`, `ModeratorsChatService`, `ModeratorsChatMessage`, `ChatDao` | [#cls-moderators-chat](#cls-moderators-chat) |
| `AdminUserInfoPage`, `AdminDao` | [#cls-admin](#cls-admin) |
| `UserDao.countIp/findByIp` | [#m-findip](#m-findip) |

## 7. Классы и методы

<a id="cls-banpanelpage"></a>
### `BanPanelPage` (`/ingame/banPanel`)

`pages/ws/ingame/BanPanelPage.java`. Каждый роут начинается с проверки «запрашивающий —
суперпользователь и цель — не он сам» (у `/mute`, `/block`, `/findIp` — «запрашивающий — админ»).
Права цели не проверяются нигде ([#tradeoffs](#tradeoffs) п.4). Размер страницы истории и поиска по
IP — `PAGE_HISTORY_ELEMENTS = 10`.

<a id="m-index"></a>
#### `actionIndex` — `""` (`:48–129`)

Payload `targetUserId`. В акторе цели вызывает `banTick` и собирает `BanGeneralInfo`; если
`banType != NONE`, достаёт последнюю запись истории (без `BAD_NAME`). Ответ: `info`
(`BanGeneralInfo`), `canBlock`, `canBan`, `canMute` — право по `BanActions` и `banType` цели в
`NONE`/`BAD_NAME`; `canCancel` — по типу последней записи. ГДД: [#gdd-player-info](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-player-info), [#gdd-ban-panel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-ban-panel),
замена санкционных кнопок на «Снять наказание» — [#gdd-cancel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-cancel). Флаг блокировки ника — `info.isBadName`; отдельного `canDropName` нет.

<a id="m-punish"></a>
#### `actionBan` / `actionMute` / `actionBlock` → `punishUser` (`:215–269`, `:366–456`)

- `/ban` (`BAN`) и `/mute` (`MUTE`): payload `userId`, `hours` (double), `reason`;
  `endTime = now + round(hours·3600000)`. `/block` (`BLOCK`): `userId`, `reason`, `endTime = 0`.
- `punishUser`: причина длиннее 500 символов — ошибка. В акторе цели — отказ, если нет права, если
  у цели уже есть наказание (кроме случая `BAD_NAME`) или ник уже заблокирован (для `BAD_NAME`).
  Иначе: для `BLOCK` — `onBlockOnlineUpdate` (пустой, TODO) и `onBasicInfoUpdate`; для `BAD_NAME` —
  `blockName(true)`, для остальных — `changeBanType` + `changeBanTime`. Затем системное письмо
  `MessageEncoder.banMessage(type, endTime−startTime, bannerName, reason)` и уведомление
  `ACCOUNT_REFRESH_ID`. После актора — `insertHistory`. Ответ `ok`/`error` без кода причины.
- ГДД [#gdd-punishments](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-punishments): кнопки «10 минут» и «Забанить» (оба — `/ban`, время задаёт клиент),
  «Тишина» (`/mute`), «Блок» (`/block`); «новое нельзя, пока есть активное» — проверка
  `isNotBanned` в акторе цели.
- Шаги «тип + время» у вызывающего: `changeBanType` и `changeBanTime` идут двумя сеттерами
  ([#tradeoffs](#tradeoffs) п.12).

<a id="m-cancel"></a>
#### `actionCancelBan` — `/cancel` (`:271–339`)

Payload `userId`. Берёт последнюю запись истории без `BAD_NAME`; отказ, если `canCancel` ложно или
запись уже отменена. В акторе цели: `banType → NONE`, `endBanTime → now`, `accountRefresh`; если цель
не наказана — отказ «user is not banned». Затем `updateCancelInfo` (кто и когда снял). И успех, и
отказ отвечают `ok` ([#tradeoffs](#tradeoffs) п.8). ГДД: [#gdd-cancel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-cancel), «кто снял» —
[#gdd-history](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-history).

<a id="m-dropname"></a>
#### `actionDropName` / `actionUnDropName` — `/dropName`, `/undropName` (`:458–530`)

- `/dropName`: payload `userId`, `reason`; запись `BAD_NAME` с `endTime = 0` через `punishUser`
  (право `canDropName`). Причину сервер берёт из запроса как есть, сам текст «Блокировка ника (ник)»
  не формирует ([#tradeoffs](#tradeoffs) п.6). Проверка прав в начале метода продублирована
  (`:512–526`).
- `/undropName`: последняя запись `BAD_NAME`, в акторе `blockName(false)` + `accountRefresh`, затем
  `updateCancelInfo`. Права на отмену не проверяются через `canCancel` — достаточно быть
  суперпользователем. Ответ всегда `ok`.
- ГДД [#gdd-name-block](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-name-block): ник «Fighter», кнопка меняется на «Разблокировать имя»; причина
  «Блокировка ника "<прежний ник>"» сервером не формируется ([#tradeoffs](#tradeoffs) п.6, п.17).

<a id="m-history"></a>
#### `actionHistory` — `/history` (`:131–213`)

Payload `userId`, `page` (по умолчанию 1). Считает записи, зажимает `page` в `[1, maxPage]`, отдаёт
до 10 записей по убыванию `_id` (новые первыми) с подписями `banner` и `cancel.user`. Пустая история
— `ok` с пустым массивом. Пагинация по 10 на странице, новые первыми — совпадает с
[#gdd-history](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-history) (Правки №2).

<a id="m-findip"></a>
#### `actionFindIp` — `/findIp` (`:532–602`) и `UserDao.countIp/findByIp`

Только админ. Payload `ip`, `page`. `countIp` считает игроков с полем `ip`, `findByIp` должен отдать
страницу `id`/`login`/`online`. Реализация `findByIp` не работает ([#tradeoffs](#tradeoffs) п.5).
В `users` хранится только последний IP и последний user-agent (`User.onAuthorizedActiveOnce`).
Назначение кнопки в ГДД не определено — [О2](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open).

<a id="cls-banactions"></a>
### `BanActions` и `UserRights`

`model/ban/BanActions.java`, `model/user/UserRights.java`.

- `UserRights`: `NONE(0)`, `MODERATOR(100)`, `ADMIN(200)`; `isSuperUser` (≥100), `isModerator`
  (100–199), `isAdmin` (≥200), `getById`.
- `BanActions.canBan` — суперпользователь; `canMute`, `canBlock` — админ; `canDropName` —
  суперпользователь; `canCancel(rights, type)` — админ любой тип, модератор только `BAN` и
  `BAD_NAME`. Параметр `targetRights` во всех `can*` не используется. `ICanPunish` — интерфейс для
  method reference.
- ГДД: доступность кнопок — [#gdd-ban-panel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-ban-panel), права по видам — [О3](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open), права на цель и
  видимость IP/почты/UA — [О6](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open); отмена — [#gdd-cancel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-cancel).
- Проверка прав продублирована: в начале каждого роута `BanPanelPage` и повторно в `can*` внутри
  `punishUser` ([#tradeoffs](#tradeoffs) п.11).

<a id="cls-models"></a>
### Модели `model.ban`

- `BanType`: `NONE`, `BAN`, `MUTE`, `BLOCK`, `BAD_NAME`, `ALL` (`ALL` нигде не используется —
  кандидат на удаление).
- `BanHistoryEntry` — запись `ban_history`: `_id`, `ownerId` (наказанный), `bannerId`, `type`,
  `startTime`, `endTime` (0 у бессрочных), `reason`, `cancel`. `apiResponse`: `banner` (подпись или
  `Unknown`), `type`, `startTime`, `endTime` (только если ≠ 0), `reason`, `cancel`. Признак
  «наказание активно» сервер не отдаёт — клиент выводит его сам.
- `BanCancelInfo` — `cancelUserId`, `cancelTime`; `apiResponse`: `user`, `time`.
- `BanGeneralInfo` — снимок цели для панели: подпись, `creationTime`, `lastOnlineTime`, `banType`,
  `banTime` (абсолютное время окончания), `isBadName`; `ip`, `email`, `userAgent` — только админу,
  модератору `"--"`.

<a id="cls-banpaneldao"></a>
### `BanPanelDao`

`dao/BanPanelDao.java`, коллекция `ban_history`. `countHistory`, `fetchHistory` (сортировка
`_id` desc, skip/limit), `insertHistory`, `updateCancelInfo` (`$set cancel`),
`fetchLatestBanHistory` (`type != BAD_NAME`), `fetchLatestBadNameHistory` (`type == BAD_NAME`).
`HistoryDocuments` копит документы и id для подписей. Индексов на `ownerId`/`type` нет — JSON-миграции
нет ([#tradeoffs](#tradeoffs) п.10).

<a id="cls-user"></a>
### Состояние наказания в `User`

`model/user/User.java`: поля `banType`, `endBanTime`, `isNameBanned` (`:118–120`), поля БД
`banType`, `banStart`, `isNameBanned` (`:744–746`).

- `banTick` (`:1135`) — сбрасывает истёкший `BAN`/`MUTE` в `NONE`; вызывается в
  `AuthorizedUserPage.onRouteCallStart` на каждом роуте игрока и перед чтением в бан-панели и
  `/banInfo`. Запись истории при истечении не меняется. ГДД [#gdd-mute-player](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-mute-player) (срок истёк —
  запрет снят).
- `changeBanType`, `changeBanTime`, `blockName`, `getBanType`, `getBanTime`, `isBadName`,
  `isNotBanned` — тривиальные поля.
- `getDisplayName` (`:818`) — `Fighter` для незарегистрированного или с заблокированным ником
  ([#gdd-name-block](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-name-block)).
- `apiResponse` (`:623–624`) отдаёт `banType` и `endBanTime` — по ним клиент показывает плашку
  запрета и экран блокировки.
- `onBlockOnlineUpdate` — пустой TODO.

<a id="cls-accountpage"></a>
### `AccountPage` `/banInfo`

`pages/ws/ingame/AccountPage.java:36–75`. Игрок запрашивает своё наказание: `banTick`, затем
последняя запись истории без `BAD_NAME` — ответ `info` (`BanHistoryEntry.apiResponse`, в т.ч.
`reason`). Источник текста «Причина» на экране блокировки ([#gdd-block-screen](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-block-screen)). Без активного наказания
вложенный таск не создаётся, а `actionRun` читает его результат — вероятен `NullPointerException`
([#tradeoffs](#tradeoffs) п.9). `taskLatestBanHistory` — копия метода `BanPanelPage`
([#tradeoffs](#tradeoffs) п.11).

<a id="cls-chat-checks"></a>
### Проверки при отправке сообщений и удаление сообщений

- `ChatPage /send` (`:34–54`) проверяет только сигнатуру энкодера и регистрацию; `banType` не
  проверяется. Отправка личных сообщений — [mailbox-architecture.md](mailbox-architecture.md), там
  проверки наказания тоже нет ([#tradeoffs](#tradeoffs) п.1; ГДД [#gdd-mute-player](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-mute-player)).
- `ChatPage /deleteMessage` (`:56–65`) — суперпользователь удаляет сообщение по `id` и `lang`:
  `ChatService.deleteMessage` убирает его из кеша и рассылает `{delId}` ([#gdd-message-delete](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-message-delete)). Не суперпользователю
  тоже отвечает `ok`. Если у языка нет подписчиков, `chatSubscriptions.get` вернёт `null`
  ([#tradeoffs](#tradeoffs) п.13).
- Чат клана (`ClanChatPage`, `/ingame/clanChat`, зона кланов, здесь только ссылкой): `/send` отвечает
  `error` при `banType == MUTE` (`BAN` и `BLOCK` не проверяет); `/deleteMessage` доступен лидеру клана,
  а не модератору.
- Подпись автора (`UserSignature` с `rights`) сохраняется в сообщении в момент отправки; по `rights`
  клиент может красить ник должностного лица ([#gdd-staff-nick-color](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-staff-nick-color)). После блокировки ника старые сообщения
  показывают старое имя.

<a id="cls-moderators-chat"></a>
### Модераторский чат (`/ingame/moderator/chat`)

- ГДД [#gdd-moderator-chat](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-moderator-chat); запрет на общение в нём не действует — [О5](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open).
- `ModeratorsChatPage`: `""`, `/subscribe`, `/unsubscribe`, `/send`, `/deleteMessage`. Права
  (суперпользователь) проверяются только в `/send` и `/deleteMessage`; подписка и чтение истории —
  без проверки ([#tradeoffs](#tradeoffs) п.3).
- `ModeratorsChatService` — копия `ChatService`: актор `ModeratorsChatActor`, кеш 50 сообщений на
  язык, длина до 256, каталог сессий `moderator/chat`, `retryMS` 1000. Загрузка при старте
  (`Globals.postLoad`, прод), сохранение в `postStop`.
- `ModeratorsChatMessage` — копия `ChatMessage`.
- `ChatDao.loadModeratorMessages` / `saveModeratorsMessagesAWAIT` — документ `_id: 1` коллекции
  `chat`.
- Дублирование `ChatService`/`ModeratorsChatService` и `ChatMessage`/`ModeratorsChatMessage` —
  [#tradeoffs](#tradeoffs) п.11.

<a id="cls-admin"></a>
### Назначение модератора

`AdminUserInfoPage /moderatorToggle` (веб-админка, доступ — `AbstractAdminPage`, только `ADMIN`)
переключает `NONE ↔ MODERATOR`. Админ назначается вне кода (поле `rights` в БД).
`AdminDao` считает и выводит список модераторов.
ГДД: назначение должностных лиц — вне игры, в отдельном сервисе ([#gdd-purpose](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-purpose), решение пользователя 2026-10-18); в коде это `/moderatorToggle` веб-админки игрового сервера, админ задаётся только в БД.

<a id="client-contract"></a>
### Контракт с клиентом

| Роут | Запрос | Ответ |
|---|---|---|
| `/ingame/banPanel` | `targetUserId` | `info`, `canBlock`, `canBan`, `canMute`, `canCancel` |
| `/ingame/banPanel/history` | `userId`, `page` | `history[]`, `page`, `maxPage` |
| `/ingame/banPanel/ban`, `/mute` | `userId`, `hours`, `reason` | ok / error |
| `/ingame/banPanel/block` | `userId`, `reason` | ok / error |
| `/ingame/banPanel/cancel` | `userId` | всегда ok |
| `/ingame/banPanel/dropName` | `userId`, `reason` | ok / error |
| `/ingame/banPanel/undropName` | `userId` | всегда ok |
| `/ingame/banPanel/findIp` | `ip`, `page` | `list[{id, login, online}]`, `page`, `maxPage` |
| `/ingame/account/banInfo` | — | `info` (запись истории) |
| `/ingame/moderator/chat/*` | как `/ingame/chat/*` | как `/ingame/chat/*` |

Время везде — абсолютные миллисекунды (`startTime`, `endTime`, `banTime`, `endBanTime`); длительность
наказания клиент считает сам как `endTime − startTime`. Сверку полей и расхождение «41 день» из
Правок №1 разбирает `integration-lead` ([#tradeoffs](#tradeoffs) п.7).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Находки анализа, решений по ним нет. Пункты, которые касаются ТЗ и Правок, отмечены.

1. **Сервер не применяет наказания (ТЗ «10 минут», «Забанить», «Тишина», «Блок»).** `ChatPage /send`
   и отправка личных сообщений не проверяют `banType`; заблокированный (`BLOCK`) игрок может вызывать
   любые роуты. Запрет держится только на клиенте, который читает `banType`/`endBanTime`. Единственная
   серверная проверка — `ClanChatPage /send` (`:129`), только для `MUTE`; для общего чата и почты правило
   не распространено. Статус: отложено 2026-10-18 (решение пользователя).
2. **«Блок» и «Тишина» не работают у модератора (Правки №1, №2).** `/mute` и `/block` требуют
   `ADMIN` (`BanPanelPage:238`, `:257`; `BanActions.canMute/canBlock`), модератору сервер отвечает
   `error` без кода. В Правках действия выполняет «Модератор Один», в консоли — `Uncaught (in promise)
   Object`, что совпадает с отказом по правам. Какие права нужны для каждого вида наказания, ТЗ не
   определяет. Показывает ли клиент кнопки при `canMute/canBlock = false` — вопрос к клиенту. Статус: отложено 2026-10-18 (решение пользователя).
   **Сверка integration-lead 2026-10-18:** `/ingame/banPanel` (`BanPanelPage:95-106`) считает `canBlock`/`canMute` через `BanActions.canBlock/canMute` = `isAdmin(requester)` и `banType ∈ {NONE, BAD_NAME}` — та же проверка, что в роутах (`:238`, `:257`). Модератору сервер отдаёт `false`; расхождения флагов с роутами нет. Клиент (`BanPanelPopup:206-211`) показывает кнопки строго по флагам.
3. **Модераторский чат читает любой игрок.** `ModeratorsChatPage /subscribe` без проверки прав
   (ТЗ Правки №1: вкладку видят модераторы и админы). Статус: отложено 2026-10-18 (решение пользователя).
4. **Права цели не учитываются.** Модератор может забанить чат или заблокировать ник админа и
   другого модератора; `targetRights` в `BanActions` не используется.
5. **«Найти IP» не работает.** `UserDao.findByIp` вызывает `.first()` (не больше одного документа),
   затем `subList(begin, limit)` — при `limit = 10` и одном документе `IndexOutOfBoundsException`, на
   второй странице `subList(10, 10)`; проекция только `_id`, а страница читает `login` и `online`.
   Индекса на `users.ip` нет. Хранится только последний IP/UA, ТЗ говорит об «устройствах, с которых
   он совершал вход».
6. **Причина блокировки ника (Правки №1, №2).** Сервер сохраняет `reason` из запроса как есть; в
   истории пустая причина и ключ `ban.reasonNameBlock` пришли от клиента. ТЗ требует текст
   «Блокировка ника (ник)» — где его формировать (сервер с ником на момент блокировки или клиент),
   не решено. Статус: отложено 2026-10-18 (решение пользователя).
7. **«Время бана 41 день» при бане на час (Правки №1).** Сервер пишет `startTime` и `endTime`
   корректно; у игрока таймер верный (по `endBanTime`). Расхождение — в расчёте на стороне панели,
   передано `integration-lead`.
   **Сверка integration-lead 2026-10-18:** единицы совпадают — `BanPanelPage:230` пишет `endTime = now + round(hours·3600000)` (мс), `BanHistoryEntry:113-116` отдаёт `startTime`/`endTime` в мс как есть, клиент `BanHistoryPanel:159` делит разность на 1000 (`TimeUtils.timeDDHHMMSS_Mls`). ×1000 по коду не воспроизводится; первопричина по коду не найдена ни на одной стороне.
8. **Отмена молча «успешна».** `/cancel` и `/undropName` отвечают `ok` и при отказе (нет прав, нечего
   снимать, нет истории). После естественного истечения `BAN`/`MUTE` запись истории остаётся без
   `cancel`, а `/cancel` отвечает отказом «user is not banned» под видом `ok`.
9. **`/banInfo` без наказания.** Без активного наказания вложенный таск не создаётся, а `actionRun`
   читает `taskStore("latestBanHistory")` — вероятен NPE и ответ `error` (не проверено запуском). Если
   нет записи истории при `banType != NONE`, `/cancel` и `/undropName` тоже упадут на
   `latestHistory.getId()`.
10. **Нет индексов `ban_history`.** Фильтры по `ownerId` (+ `type`) и сортировка по `_id` без
    JSON-миграции индекса (правило проекта: индекс — в том же изменении).
11. **Дубли (одно правило — одна функция).** `taskLatestBanHistory` в `BanPanelPage` и `AccountPage`,
    `taskLatestBadNameHistory` отличается только DAO-методом; `ModeratorsChatService` и
    `ModeratorsChatMessage` — копии `ChatService`/`ChatMessage`; проверка прав в роутах повторяет
    `BanActions.can*`; двойная проверка в `actionDropName`. Предложение — оставить по одной функции;
    вариант выбирает пользователь при задаче на область.
12. **Неявный порядок вызовов.** Наложение и снятие наказания у вызывающего собраны из
    `changeBanType` + `changeBanTime` (`BanPanelPage:423–425`, `:311–312`); блокировка ника —
    `blockName(true/false)` отдельно. Кандидат — методы-переходы у `User` (наложить/снять).
13. **Удаление сообщения при отсутствии подписчиков языка.** `ChatService.deleteMessage`
    (`:212–217`, так же в `ModeratorsChatService`) вызывает `broadcast` у `null` — исключение в акторе
    чата и его перезапуск с пустым кешем. Срабатывает, только если удаляющий не подписан на язык.
14. **Валидация ввода.** `hours` не проверяется (отрицательное, ноль, очень большое); пустая причина
    разрешена; при ошибке клиенту не уходит код причины.
15. **Мёртвый код.** `BanType.ALL`, `User.onBlockOnlineUpdate` (пустой TODO),
    `UserSignature.fromUserDocument` (не вызывается, к тому же не учитывает блокировку ника).
16. **Письмо о бане теряется** — [mailbox-architecture.md#tradeoffs](mailbox-architecture.md#tradeoffs)
    п.3 (отложенный кросс-репо баг, здесь не дублируется).
17. **Расхождения кода с ГДД** (ГДД записан «как в коде»; ниже — места, где серверный код
    правилу не соответствует или не поддерживает его):
    - [#gdd-punishments](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-punishments), [#gdd-mute-player](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-mute-player), [#gdd-block-screen](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-block-screen) — сервер запрет не
      применяет (п.1).
    - [#gdd-ban-panel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-ban-panel) — «причина обязательна, до 255 символов»: сервер принимает пустую причину
      и до 500 символов; срок принимает дробный и отрицательный (п.14, [О4](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open)).
    - [#gdd-name-block](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-name-block) — причину «Блокировка ника "<прежний ник>"» сервер не формирует, пишет
      `reason` из запроса (п.6).
    - [#gdd-moderator-chat](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-moderator-chat) — «только для должностных лиц»: подписка без проверки прав (п.3).
    - [#gdd-player-info](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-player-info) — «кнопки нет у профиля админа»: сервер права цели не проверяет (п.4,
      [О6](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open)); почту модератору сервер отдаёт как `"--"` (`BanGeneralInfo`), что не совпадает с
      «почта выводится как есть» для должностного лица ([О6](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open)).
    - [#gdd-cancel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-cancel) — «СНЯТЬ НАКАЗАНИЕ» при наказании любого вида: модератору `canCancel`
      разрешает только бан и блокировку ника; «Тишину» и «Блок» модератор снять не может
      (связано с [О3](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open)).

Пункты ТЗ, которые сервер уже выполняет: история по 10 записей на страницу, новые первыми (Правки
№2); «кто снял» и время снятия; замена ника на `Fighter`; IP/почта/UA — только админу. Цвет ника
должностного лица (Правки №1) и раскладка панели — клиентская сторона; сервер отдаёт `rights` в
подписи.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [ban-gdd.md](/workspace/client/.claude/docs/game-design/ban-gdd.md). Соответствие правил ГДД коду:

| Правило ГДД | Код |
|---|---|
| [#gdd-purpose](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-purpose) | [#purpose](#purpose); назначение должностных лиц — [#cls-admin](#cls-admin) (по ГДД назначение вне игры) |
| [#gdd-player-info](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-player-info) | [#m-index](#m-index), `BanGeneralInfo` ([#cls-models](#cls-models)); почта — только админу (п.17) |
| [#gdd-ban-panel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-ban-panel) | [#m-index](#m-index), [#cls-banactions](#cls-banactions); «Найти IP» — [#m-findip](#m-findip), [О2](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) |
| [#gdd-name-block](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-name-block) | [#m-dropname](#m-dropname), `User.getDisplayName` ([#cls-user](#cls-user)) |
| [#gdd-punishments](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-punishments) | [#m-punish](#m-punish), `BanType` ([#cls-models](#cls-models)); права — [О3](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) |
| [#gdd-cancel](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-cancel) | [#m-cancel](#m-cancel), `BanActions.canCancel` |
| [#gdd-history](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-history) | [#m-history](#m-history), `BanHistoryEntry`, `BanCancelInfo` |
| [#gdd-mute-player](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-mute-player) | `User.banTick`, `apiResponse.banType/endBanTime` ([#cls-user](#cls-user)); серверной проверки нет (п.1) |
| [#gdd-block-screen](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-block-screen) | [#cls-accountpage](#cls-accountpage); серверного ограничения нет (п.1) |
| [#gdd-moderator-chat](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-moderator-chat) | [#cls-moderators-chat](#cls-moderators-chat); [О5](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) |
| [#gdd-message-delete](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-message-delete) | [#cls-chat-checks](#cls-chat-checks) |
| [#gdd-staff-nick-color](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-staff-nick-color) | `UserSignature.rights` ([#cls-chat-checks](#cls-chat-checks)); цвет — клиент, [О1](/workspace/client/.claude/docs/game-design/ban-gdd.md#gdd-open) |

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от `game/src/main/java/com/linkedgames/game/`, если не указано иное.

### Файлы прямого влияния

- `pages/ws/ingame/BanPanelPage.java` — роуты бан-панели.
- `dao/BanPanelDao.java` — коллекция `ban_history`.
- `model/ban/BanType.java` — виды наказаний.
- `model/ban/BanActions.java` — права на наказание и отмену.
- `model/ban/BanHistoryEntry.java` — запись истории.
- `model/ban/BanCancelInfo.java` — кто и когда снял.
- `model/ban/BanGeneralInfo.java` — снимок цели для панели.
- `model/user/UserRights.java` — уровни прав должностных лиц.
- `pages/ws/ingame/ModeratorsChatPage.java` — роуты модераторского чата.
- `service/chat/ModeratorsChatService.java` — актор модераторского чата.
- `service/chat/ModeratorsChatMessage.java` — сообщение модераторского чата.

### Файлы косвенного влияния

- `model/user/User.java` — поля и методы наказания, `getDisplayName` (`Fighter`), `banType` в
  `apiResponse`, последние IP/UA.
- `pages/ws/ingame/AuthorizedUserPage.java` — `banTick` на каждом роуте игрока.
- `pages/ws/ingame/AccountPage.java` — `/banInfo`, сброс `accountRefresh`.
- `pages/ws/ingame/ChatPage.java` — отправка без проверки наказания, `/deleteMessage`.
- `pages/ws/ingame/ClanChatPage.java` — зависимость: единственная серверная проверка `MUTE` при отправке (зона кланов).
- `service/chat/ChatService.java` — `deleteMessage`, образец модераторского чата.
- `dao/ChatDao.java` — хранение модераторского чата (`_id: 1` коллекции `chat`).
- `dao/UserDao.java` — `countIp`, `findByIp`.
- `pages/WSRouter.java` — регистрация `/ingame/banPanel`, `/ingame/moderator/chat`, `/ingame/account` (рядом появился `/ingame/clanChat`).
- `Globals.java` — загрузка модераторского чата при старте (`:76`; рядом добавлены загрузки новых областей).
- `model/messages/MessageEncoder.java` — `banMessage` (письмо о бане, см. почту; индекс `EncoderId.BAN` изменился — [mailbox-architecture.md#tradeoffs](mailbox-architecture.md#tradeoffs)).
- `model/messages/Messengers.java` — зависимость: отправитель `POSTMAN` письма о бане.
- `model/mailbox/MailboxUserComponent.java` — `receiveSystemMessage` (пустой, см. почту).
- `model/notifications/NotificationId.java` — зависимость: `ACCOUNT_REFRESH_ID`.
- `model/user/UserSignature.java` — зависимость: подпись с `rights` в истории и чатах.
- `model/user/tasks/UserSignatureCollectorTask.java` — зависимость: подписи «кто наложил/снял».
- `utils/Names.java` и `game/src/main/resources/app.properties` (`app.noviceName=Fighter`) — имя
  заблокированного ника.
- `pages/web/admin/AdminUserInfoPage.java` — `/moderatorToggle`.
- `pages/web/admin/extend/AbstractAdminPage.java` — зависимость: доступ к веб-админке только `ADMIN`.
- `dao/AdminDao.java` — счёт и список модераторов.
- `service/battlefield/BattlefieldActor.java` — зависимость: подпись бота с `UserRights.NONE`.
