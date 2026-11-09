# Почта — `MailboxUserComponent` (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-10-17;
> актуализирован 2026-10-19 по коду после merge `origin/amnesia/fix` (не закоммичен). Всё ниже
> подтверждено чтением кода, запуском не проверялось.
> Клиентская сторона (`src/views/home_screen/popups/mailbox/**`, `mailbox.d.ts`) сверена только по
> вызываемым роутам и типам ответов, логика окон не анализировалась.

ГДД: [`mailbox-gdd.md`](/workspace/client/.claude/docs/game-design/mailbox-gdd.md) — черновик по коду. Почти все правила записаны в нём как открытые
вопросы ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open), О1–О12) и не подтверждены пользователем; подтверждено одно правило:
системные письма доходят до игрока ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О4). Ссылки ниже указывают на
раздел ГДД и на пункт [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open), где правило записано.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`MailboxUserComponent`](#cls-component)
   - [`MailboxMessage`](#cls-message)
   - [`MailboxDialog`](#cls-dialog)
   - [`MailboxDao` и миграция индексов](#cls-dao)
   - [Страницы `/ingame/mailbox/*`](#cls-pages)
   - [Системные отправители: `Messengers`, `MessageEncoder`](#cls-system)
   - [Персистентность и состояние в памяти](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Почта на сервере — личная переписка игроков один на один, со списком друзей и чёрным списком. Писем
с наградами и рассылок от игры ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О1, ждём ТЗ) в коде нет: роут `/ingame/mailbox/rewards` и корневой
`/ingame/mailbox` — заглушки, метод приёма системного письма от `POSTMAN` `receiveSystemMessage` пуст
(`// TODO`). Появился второй путь доставки без проверок — `addMessage` (письма-приглашения в клан из
`ClanPage`, см. [`#cls-component`](#cls-component)); сама функция клана здесь не описывается.
Dev-роутов почты в `DevToolsPage` (`pages/ws/ingame/dev/`) нет.

Правила по коду:

- **Кто может писать** ([#gdd-send-restrictions](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-send-restrictions), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О7). Только зарегистрированный игрок (`User.isRegistered`). Нельзя писать самому
  себе и системному отправителю (`Messengers.isSpecial`).
- **Текст** ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О6). Обрезаются пробелы по краям; пустой текст и текст длиннее 255 символов отклоняются; текст
  не может начинаться с `|s|` — это префикс системных сообщений `MessageEncoder`.
- **Чёрный список** ([#gdd-send-restrictions](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-send-restrictions), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О7; ошибка — О10). Если получатель внёс отправителя в чёрный список, сообщение не доставляется,
  отправитель получает ошибку `MAILBOX / ERR_BLACKLIST`. Свой чёрный список отправителю писать не
  мешает.
- **Хранение** ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), срок хранения — [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О11). Каждое сообщение пишется двумя копиями — у отправителя и у получателя; у каждого свой
  диалог (одна запись на пару «владелец–собеседник») с последним текстом и временем. У отправителя
  диалог помечается прочитанным, у получателя — непрочитанным.
- **Непрочитанные** ([#gdd-unread](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-unread), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О2, О3, О6). Игроку показывается число диалогов с непрочитанными сообщениями
  (`unreadDialogsCount`, уведомление `mailbox`). Диалог становится прочитанным при открытии переписки
  или по запросу `/read`.
- **Списки** ([#gdd-dialogs](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-dialogs), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О5, О6). Диалогов отдаётся не больше 50 (сначала непрочитанные, затем по убыванию времени),
  сообщений в переписке — последние 100. Диалоги с собеседником из своего чёрного списка в списке и в
  счётчике непрочитанных не показываются.
- **Друзья и чёрный список** ([#gdd-friends](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-friends), [#gdd-blacklist](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-blacklist), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О8, О9, О12). Списки односторонние, без подтверждения второй стороной. Лимит — 50 в
  каждом (`MAX_FRIENDS`, `MAX_BLACKLIST`). Человек не может быть одновременно другом и в чёрном
  списке: добавление в один список удаляет из другого. Системного отправителя добавить нельзя.

<a id="references"></a>
## 2. Референсы

Нет: модель, DAO и страницы почты пришли в исходном коммите `d3d31c4`; коммит `dc49854` («Ban panel»)
добавил вызов `receiveSystemMessage` из `BanPanelPage`; merge `origin/amnesia/fix` добавил `addMessage`
и `updateMessage` для приглашений в клан и вызов `init()` из `User`. Структура переписки близка к чату
(`ChatPage`) — та же защита префиксом `MessageEncoder`.

<a id="patterns"></a>
## 3. Паттерны

- **Ленивый компонент пользователя** — `User.getMailboxComponent()` создаёт компонент при первом
  обращении; в цепочку загрузки/сохранения `ActorInitializationTask`/`ActorUpdateTask` компонент не
  входит. `init()` вызывается из `User.onAuthorizedActiveOnce`.
- **Задачи с почтовыми ящиками (`user().createTask(...)`)** — асинхронные цепочки `actionRunWait` /
  `actionRun` + `actionWait` / `onSuccess` / `onFail`; ответ клиенту отправляется из задачи через
  сохранённый `PageProcessor`.
- **Прямая запись в MongoDB из DAO** — данные почты живут в четырёх собственных коллекциях, не в
  документе пользователя.
- **Доставка другому игроку через `UserStore.actionExecute` / `ExecuteInside`** — код выполняется в
  акторе получателя (уведомление, push).
- **Сбор подписей `UserSignatureCollectorTask`** — имена/аватары собеседников, друзей и чёрного
  списка подтягиваются из акторов этих игроков.

<a id="class-list"></a>
## 4. Список классов

Компонент целиком — см. [карту файлов](#file-map).

| Класс | Пакет | Роль |
|---|---|---|
| `MailboxUserComponent` | `model.mailbox` | логика почты игрока |
| `MailboxMessage` | `model.mailbox` | одно сообщение (копия владельца) |
| `MailboxDialog` | `model.mailbox` | диалог владельца с собеседником |
| `MailboxDao` | `dao` | доступ к коллекциям `mailbox_*` |
| `MailboxPage`, `DialogsPage`, `MessagesPage`, `FriendsPage`, `BlacklistPage`, `RewardsPage` | `pages.ws.ingame.mailbox` | WS-роуты |
| `Messengers`, `MessageEncoder` | `model.messages` | системные отправители и кодирование системных сообщений |

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#references`, `#patterns`, `#class-list`, `#class-nav`, `#cls-component`,
`#cls-message`, `#cls-dialog`, `#cls-dao`, `#cls-pages`, `#cls-system`, `#persistence`,
`#client-contract`, `#tradeoffs`, `#gdd-link`, `#file-map`.

<a id="class-nav"></a>
## 6. Оглавление по классам

- [`MailboxUserComponent`](#cls-component)
- [`MailboxMessage`](#cls-message)
- [`MailboxDialog`](#cls-dialog)
- [`MailboxDao`](#cls-dao)
- [`MailboxPage` / `DialogsPage` / `MessagesPage` / `FriendsPage` / `BlacklistPage` / `RewardsPage`](#cls-pages)
- [`Messengers`, `MessageEncoder`](#cls-system)

## 7. Классы и методы

<a id="cls-component"></a>
### `MailboxUserComponent`

`game/src/main/java/com/linkedgames/game/model/mailbox/MailboxUserComponent.java`. Наследует
`UserChildComponent`, реализует `APIResponseStd`. Поля в памяти: `unreadDialogs` (множество id
собеседников с непрочитанными диалогами), `dialogsSubscription` (открыт ли список диалогов),
`messagesSubscription` (id собеседника открытой переписки), `inited`. Правила ГДД класса целиком — [#gdd-purpose](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-purpose).

- `init()` — один раз (флаг `inited`) загружает из БД id собеседников с непрочитанными диалогами
  (`getUnreadDialogOpponentIds`) и, если список не пуст, шлёт уведомление `mailbox`. Правило:
  непрочитанное видно сразу после входа ([#gdd-unread](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-unread), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О3 — не подтверждено). Вызывается из
  `User.onAuthorizedActiveOnce` (после merge; раньше не вызывался) — см. [`#tradeoffs`](#tradeoffs), п.1.
- `sendMessage(opponentId, text, pageProcessor)` — отправка сообщения; правила: ограничения отправки
  ([#gdd-send-restrictions](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-send-restrictions), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О7), переписка ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages)). Отказ сразу, если адресат —
  сам игрок или системный отправитель. Затем: проверка, не в чёрном ли списке отправитель у
  получателя (`isBlacklisted`, при попадании задача падает с `ERROR_BLACKLISTED`); параллельно четыре
  записи — копия сообщения себе и получателю (`insertNewMessage`), диалог себе прочитанным и получателю
  непрочитанным (`insertNewDialog`); если хоть одна не прошла — ошибка. Отправителю в ответ
  `newMessage`; в актор получателя — `onMailMessageNotification` и `onUpdateDialogsNotification`.
  Перегрузка `sendMessage(opponentId, text)` — то же без ответа клиенту, вызовов нет.
- `addMessage(from, text)` — кладёт игроку входящее письмо от `from` без проверок `sendMessage`
  (чёрный список, регистрация, длина, префикс `|s|`): запись `mailbox_messages` (`ownerId` = игрок,
  `fromId` = `from`) и диалога с `read=false`, затем у самого игрока `onMailMessageNotification` и
  `onUpdateDialogsNotification`; обе записи не прошли — задача падает без ответа. Вызывается из
  `ClanPage` (приглашение в клан, текст `MessageEncoder.clanInviteMessage`); у отправителя копии нет.
  Правило ГДД: не описано (ГДД про клановые письма молчит — вопрос В1).
- `updateMessage(messageId, text)` — заменяет `text` своей копии письма по `_id` и `ownerId`
  (`MailboxDao.updateMessage`); диалог (`text` последнего сообщения) не обновляется, уведомлений и
  push нет, итог записи не проверяется (`actionRun` с пустым телом). Вызывается из `ClanPage` при
  принятии и отклонении приглашения (статус в тексте меняется на `STATUS_ACCEPT`/`STATUS_REJECT`).
- `dialogsSubscribe(pageProcessor)` — список диалогов ([#gdd-dialogs](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-dialogs), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О5); включает `dialogsSubscription`, отдаёт список диалогов с
  подписями собеседников. `dialogsUnSubscribe` — выключает флаг, отвечает `ok`.
- `messagesSubscribe(opponentId, pageProcessor)` — переписка ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О6); запоминает открытого собеседника, отдаёт
  переписку (`messages`) и флаги диалога (`friend`, `blacklisted`, `unread`), затем помечает диалог
  прочитанным. Диалога нет — `ok` с пустым списком и нулевыми флагами. `messagesUnsubscribe` —
  сбрасывает собеседника.
- `markMessagesRead(opponentId)` — прочтение ([#gdd-unread](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-unread), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О6); убирает собеседника из `unreadDialogs` и, только если он там был,
  пишет в БД `read=true, unread=0`.
- `getFriends` / `getBlacklist` — ([#gdd-friends](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-friends), [#gdd-blacklist](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-blacklist)) читают список id и отдают подписи игроков; документа нет — `ok` с
  пустым списком.
- `addToFriends(userId, …)` / `addToBlacklist(userId, …)` — правила: лимит и взаимоисключение
  ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О8), повтор ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О12); отказ для системного отправителя; проверка
  лимита 50; добавление в список и удаление из противоположного списка (с пометкой в диалоге).
- `deleteFromFriends` / `deleteFromBlacklist` — ([#gdd-friends](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-friends), [#gdd-blacklist](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-blacklist)) удаление из списка и снятие пометки в диалоге.
- `isFriend(opponentId, pageProcessor)` — проверка дружбы; роута нет, вызовов нет.
- `receiveSystemMessage(sender, msg)` — должна реализовывать правило «системные письма доходят до
  игрока» ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О4); пустая заглушка `// TODO`, вызывается из
  `BanPanelPage` при бане. Баг, отложен ([`#tradeoffs`](#tradeoffs), п.3).
- Приватные: `sendNotificationToUser` (уведомление `mailbox` с `apiResponse()`),
  `addToUnreadDialogs` / `removeFromUnreadDialogs` (меняют множество и шлют уведомление),
  `onMailMessageNotification` (push `/events/mailbox/messages`, если открыт диалог с этим отправителем,
  и всегда — в непрочитанные), `onUpdateDialogsNotification` (если открыт список диалогов —
  перечитывает его и шлёт push `/events/mailbox/dialogs`).
- `apiResponse()` — `{ unreadDialogsCount }`.

<a id="cls-message"></a>
### `MailboxMessage`

`model/mailbox/MailboxMessage.java`, `IPersistentObject`. Одно сообщение переписки ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages)). Поля: `id`, `ownerId` (чья копия),
`opponentId`, `fromId` (автор), `text`, `time`. Два конструктора: из документа БД и новый (с новым
`ObjectId`). `dbMappingBuild`/`dbToData` — прямое отображение полей. `apiResponse()` —
`{ id, userId: fromId, text, time(ms) }`. Остальное — геттеры. Для `addMessage` конструктор
вызывается как `(ownerId = id игрока, opponentId = from, fromId = from)`.

<a id="cls-dialog"></a>
### `MailboxDialog`

`model/mailbox/MailboxDialog.java`. Элемент списка диалогов ([#gdd-dialogs](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-dialogs), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О5). Поля: `id`, `opponentId`, `text`, `time`, `read` (по умолчанию
`true`), `unread` (по умолчанию 0), `friend`, `blacklisted`, `deleted`; транзиентное `opponent`
(`UserSignature`). `dbMappingBuild` читает документ (`dbToData` нет, хотя класс реализует
`IPersistentObject`). `apiResponse()` — `{ id, user, text, time, read, unread, friend, blacklisted,
deleted? }`; без подписи собеседника `user` = `UserSignature.createUnknown(opponentId)`. Конструктор
со всеми полями не используется. Поле `deleted` никто не записывает.

<a id="cls-dao"></a>
### `MailboxDao` и миграция индексов

`game/src/main/java/com/linkedgames/game/dao/MailboxDao.java`, синглтон `INSTANCE`. Лимиты 50 — [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О5, О8. Константы:
`MAX_FRIENDS = 50`, `MAX_BLACKLIST = 50`, ошибки `ERROR_UNEXPECTED`, `ERROR_BLACKLISTED`.

Коллекции:

| Коллекция | Документ |
|---|---|
| `mailbox_dialogs` | `{ ownerId, opponentId, text, time, read, unread, friend?, blacklisted?, deleted? }` |
| `mailbox_messages` | `{ _id, ownerId, opponentId, fromId, text, time }` |
| `mailbox_friends` | `{ _id: userId, friends: [ObjectId] }` |
| `mailbox_blacklist` | `{ _id: userId, blacklist: [ObjectId] }` |

Методы:

- `getUnreadDialogOpponentIds(ownerId, showDeleted, …)` — id собеседников из диалогов с `read=false`
  (без `showDeleted` — исключая `blacklisted` и `deleted`).
- `getDialogs(ownerId, showDeleted, …)` — диалоги, у которых есть `read` и `time` (так отсекаются
  записи, созданные только пометками друга/чёрного списка); сортировка `read` по возрастанию, `time`
  по убыванию; лимит 50. Возвращает `DialogDocuments` (документы + id собеседников).
- `getDialog` — один диалог пары. `getMessages` — копии сообщений владельца по паре, по убыванию
  времени, лимит 100.
- `setMessagesRead` — `read=true, unread=0` без ожидания результата.
- `updateMessage(ownerId, messageId, text, …)` — `$set text` по `{_id, ownerId}`; в задачу возвращается
  `true`, если ответ пришёл (совпадение документа не проверяется).
- `insertNewMessage` — вставка копии сообщения. `insertNewDialog(message, read, …)` — upsert диалога
  пары: `text`, `time`, `read`, `unread = read ? 0 : 1`.
- `getFriends`, `countFriends` (агрегация `$size`), `isFriends`, `addFriend` (`$addToSet` + upsert
  диалога `friend=true`), `deleteFriend` (`$pull` + `$unset friend`).
- `isBlacklisted(userId, opponentId)` — есть ли `opponentId` в чёрном списке `userId`; при попадании
  `sendFail(ERROR_BLACKLISTED)`. `getBlacklist`, `countBlacklist`, `addToBlacklist`,
  `deleteFromBlacklist` — как у друзей, с полем `blacklisted`.

В `addFriend`/`deleteFriend`/`addToBlacklist`/`deleteFromBlacklist` в задачу возвращается только
результат записи в список; запись в диалог идёт «выстрелил и забыл» (`NoJobSubscriber`).

Миграция `game/src/main/resources/migrations/1755491969919_mailbox.json`: уникальный
`mailbox_dialogs {ownerId, opponentId}`, составные `{ownerId, read, blacklisted, deleted}`,
`{ownerId, read, blacklisted, deleted, time:-1}`, `{ownerId, time}`; `mailbox_messages
{ownerId, opponentId, time:-1}`. Коллекции друзей и чёрного списка ищутся по `_id`, отдельных индексов
не требуют.

<a id="cls-pages"></a>
### Страницы `/ingame/mailbox/*`

Регистрация — `WSRouter.ingame`. Правила по роутам — в разделах ГДД: [#gdd-dialogs](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-dialogs), [#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), [#gdd-friends](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-friends), [#gdd-blacklist](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-blacklist). Все страницы — `AuthorizedUserPage`, делегируют в компонент.

| Роут | Класс | Запрос | Действие |
|---|---|---|---|
| `/ingame/mailbox` | `MailboxPage` | — | заглушка, `ok` |
| `/ingame/mailbox/rewards` | `RewardsPage` | — | заглушка, `ok` ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О1) |
| `/ingame/mailbox/dialogs/subscribe`, `/unsubscribe` | `DialogsPage` | — | `dialogsSubscribe` / `dialogsUnSubscribe` |
| `/ingame/mailbox/messages/subscribe` | `MessagesPage` | `opponent` | нет id или id = свой — `error` |
| `/ingame/mailbox/messages/unsubscribe` | `MessagesPage` | — | `messagesUnsubscribe`, `ok` |
| `/ingame/mailbox/messages/send` | `MessagesPage` | `opponent`, `text` | проверки регистрации и текста, `sendMessage` |
| `/ingame/mailbox/messages/read` | `MessagesPage` | `opponent` | `markMessagesRead`, сразу `ok` |
| `/ingame/mailbox/friends/get`, `/add`, `/delete` | `FriendsPage` | `id` (кроме `get`) | списки друзей |
| `/ingame/mailbox/blacklist/get`, `/add`, `/delete` | `BlacklistPage` | `id` (кроме `get`) | чёрный список |

<a id="cls-system"></a>
### Системные отправители: `Messengers`, `MessageEncoder`

- `model/messages/Messengers.java` — enum системных отправителей; сейчас один `POSTMAN`
  (`000000010000000000000001`, имя `game:postman`). `isSpecial(id)` — признак системного id:
  `id.getTimestamp() == 1`. `toSignature()` не вызывается.
- `model/messages/MessageEncoder.java` — кодирование системных сообщений для локализации на клиенте:
  префикс `|s|`, первое поле после префикса — `ordinal` внутреннего `EncoderId` (`CLAN_INVITE`, `BAN`).
  `banMessage(type, time, bannerName, reason)` → `|s|1|<type>|<time>|<banner>|<reason>`;
  `clanInviteMessage(clanId, clanName, status)` → `|s|0|<clanId>|<clanName>|<status>`
  (`status` — `ClanInvite.STATUS_SENT/REJECT/ACCEPT` = 0/1/2). Раньше `BAN` имел индекс 0; вставка
  `CLAN_INVITE` перед ним сдвинула индекс — вопрос В2. Используется также чатами (`ChatPage`,
  `ModeratorsChatPage`, `ClanChatPage`) и `MessagesPage` для отсечения префикса у игроков.
- Отправители системных писем: `BanPanelPage` (бан игрока: `POSTMAN` + `banMessage` через
  `receiveSystemMessage`) и `ClanPage` (приглашение в клан через `addMessage`, отправитель — игрок,
  пригласивший в клан). Письмо о бане теряется, потому что `receiveSystemMessage` пуст — нарушает правило «системные
  письма доходят до игрока» ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О4); баг, отложен.

<a id="persistence"></a>
### Персистентность и состояние в памяти

Компонент не сохраняется через `ActorUpdateTask` и не загружается в `ActorInitializationTask`: каждая
операция сразу пишет в коллекции `mailbox_*`. В памяти живут только `unreadDialogs`,
`dialogsSubscription`, `messagesSubscription`; `unreadDialogs` заново заполняется `init()` при входе,
подписки не восстанавливаются. Счётчик в уведомлении `mailbox` хранится в
`NotificationUserComponent` (`NotificationId.MAILBOX_ID`). Потеря счётчика после входа — [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О3.

<a id="client-contract"></a>
### Контракт с клиентом

Ответы (`payload`):

| Роут | Ответ | Тип клиента (`mailbox.d.ts`) |
|---|---|---|
| `/ingame/mailbox` | пусто | `MailboxPopupJSON {}` |
| `/dialogs/subscribe` | `{ dialogs: MailboxDialog[] }` | `MailboxDialogsJSON` |
| `/messages/subscribe` | `{ messages: MailboxMessage[], friend, blacklisted, unread }` | `MailboxMessagesJSON` |
| `/messages/send` | `{ newMessage: MailboxMessage }`; ошибка `MAILBOX/ERR_BLACKLIST` или общая | клиент проверяет `errCode === "ERR_BLACKLIST"` |
| `/messages/read`, `/unsubscribe`, `/friends/add|delete`, `/blacklist/add|delete` | пусто, `ok`/`error` | — |
| `/friends/get` | `{ friends: UserSignature[] }` | `MailboxFriendsJSON` |
| `/blacklist/get` | `{ blacklist: UserSignature[] }` | `MailboxBlacklistJSON` |
| `/rewards` | пусто | клиентом не вызывается (`MailboxRewardsSection` без запроса) |

Объекты: `MailboxDialog` → `{ id, user: UserSignature, text, time, read, unread, friend,
blacklisted, deleted? }`; `MailboxMessage` → `{ id, userId, text, time }`; `time` — миллисекунды.
Поля совпадают с `MailboxDialogJSON` / `MailboxMessageJSON`.

Push-события сервера:

| Событие | Когда | Payload | Слушает клиент |
|---|---|---|---|
| `/events/mailbox/messages` | получателю пришло сообщение, и у него открыта переписка с отправителем | `{ newMessage }` | `MailboxMessagesSection` (`g/ws/events/mailbox/messages`) |
| `/events/mailbox/dialogs` | получателю пришло сообщение, и у него открыт список диалогов | `{ dialogs }` | `MailboxDialogsSection` (`g/ws/events/mailbox/dialogs`) |
| `/events/userNotification`, `name: "mailbox"` | изменилось множество непрочитанных диалогов | `{ value: { unreadDialogsCount } }` | `Notifications.MAILBOX_ID` → `HeaderProfile`, `MailboxPopup`, `ProfilePopup` |

Обязанности сторон: при открытой переписке сервер всё равно добавляет отправителя в непрочитанные —
клиент сам вызывает `/messages/read` (`MailboxMessagesSection`, строка 82). Отправителю push о его
собственном сообщении не приходит, только ответ `newMessage`. Поведение клиента подробнее не
анализировалось — вопросы по нему через `client-analyst-lead`/`integration-lead`.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Номера строк — на дату документа. `MUC` = `model/mailbox/MailboxUserComponent.java`, `DAO` =
`dao/MailboxDao.java`.

1. **Закрыто merge: `init()` вызывается** ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О3; `MUC:41–60`; вызов — `User.onAuthorizedActiveOnce`).
   Счётчик непрочитанных после входа восстанавливается, `markMessagesRead` (`MUC:285–289`) видит
   старые непрочитанные диалоги. Остаток: уведомление шлётся только при непустом списке, а `init()`
   асинхронный — окно между входом и ответом БД; `markMessagesRead` по-прежнему зависит от
   множества в памяти.
2. **Счётчик `unread` диалога не накапливается** ([#gdd-dialogs](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-dialogs): ГДД называет «число непрочитанных в диалоге»; [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О2) — `MailboxDao.insertNewDialog` `set("unread", read ? 0 : 1)`: при любом
   числе непрочитанных сообщений у получателя `unread = 1`.
3. **Системные письма теряются — баг, отложен (решение пользователя 2026-10-17; приоритет высший, кросс-репо: на клиенте нет декодера `|s|`).** Нарушает подтверждённое правило «системные письма доходят до игрока» ([#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages), [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О4). `receiveSystemMessage` пуст (`MUC:454–456`), а `BanPanelPage:430–436`
   на него рассчитывает: игрок не получает письмо о бане.
4. **Награды и рассылки отсутствуют** ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О1, ждём ТЗ) — `RewardsPage:12–16`, `MailboxPage:12–16` отвечают пустым `ok`.
5. **Нет onFail у удаления** ([#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open) О10) — `deleteFromFriends` (`MUC:361–372`), `deleteFromBlacklist`
   (`MUC:441–452`): при сбое БД клиент не получает ответа.
6. **Нет проверки существования адресата и самого себя в списках.** `sendMessage` (`MUC:62–70`) не
   проверяет, что игрок с `opponentId` существует — в БД создаются диалоги с несуществующим id.
   `addToFriends`/`addToBlacklist` (`MUC:328–334`, `408–414`) не запрещают добавить самого себя или
   несуществующего игрока.
7. **Возможен второй ответ на один запрос** (предположительно, по устройству задач): `notifyOpponent`
   (`MUC:115–124`) идёт после успешного ответа клиенту; если актор получателя не загрузится, `onFail`
   (`MUC:125–138`) отправит ещё и `error` на тот же `PageProcessor`. Запуском не проверялось.
8. **Неатомарная отправка** — четыре независимые записи (`MUC:82–94`); при частичном сбое у одной
   стороны сообщение есть, у другой нет, а отправитель получает ошибку.
9. **Гонка лимита друзей/чёрного списка** — подсчёт и добавление разными запросами
   (`MUC:339–347`, `419–427`); два параллельных запроса могут превысить 50.
10. **Пометки в диалоге «выстрелил и забыл»** — `MailboxDao.addFriend`, `deleteFriend`, `addToBlacklist`, `deleteFromBlacklist`:
    результат не проверяется, флаги `friend`/`blacklisted` в диалоге могут разойтись со списками.
11. **Порядок друзей и чёрного списка не сохраняется**, недоступные игроки пропадают из ответа —
    `MUC:312`, `392` перебирают `HashMap` из `UserSignatureCollectorTask`.
12. **Дубли кода (правило «одно правило ГДД — одна функция»).** Сборка списка диалогов с подписями
    продублирована в `dialogsSubscribe` (`MUC:192–215`) и `onUpdateDialogsNotification`
    (`MUC:492–511`); `getFriends`/`getBlacklist` и пары add/delete у друзей и чёрного списка
    симметричны почти построчно.
13. **Неявный порядок вызовов.** Правило «друг и чёрный список взаимоисключающие» собирается у
    вызывающего из двух DAO-вызовов (`MUC:345–350`, `425–430`), а каждый DAO-метод сам пишет в две
    коллекции. Кандидат на один метод-переход у владельца.
14. **Мёртвый и незаконченный код** — кандидаты на удаление или доработку: `isFriend`
    (`MUC:227–237`, роута нет), `sendMessage(opponentId, text)` (`MUC:142–144`), параметр
    `showDeleted` (всегда `false`), поле `deleted` диалога (`MailboxDialog:21`, никто не пишет),
    конструктор `MailboxDialog:29–39`, `Messengers.toSignature` (`Messengers:36–38`).
15. **Свой чёрный список не мешает писать** (ГДД О7 этого случая не описывает) — `sendMessage` проверяет только чёрный список
    получателя (`MUC:78–80`); у отправителя диалог скрыт (`blacklisted=true`), но сообщение уходит.
    Правило это или упущение — вопрос к ГДД, см. [`#gdd-link`](#gdd-link).
16. **Приглашения в клан обходят правила отправки.** `addMessage` (`MUC:148–171`) не проверяет чёрный
    список получателя, длину и не требует отправителя в `mailbox_friends`; `updateMessage`
    (`MUC:173–187`) не проверяет результат и не обновляет `text` диалога, поэтому в списке диалогов
    остаётся текст `STATUS_SENT`; `messageId` приходит от клиента (`ClanPage`), чужое письмо не
    изменить только благодаря фильтру `ownerId`. Правила ГДД нет — вопрос В1.
17. **Уведомление шлётся всегда** — `NotificationUserComponent.addNotification` сравнивает значения
    через `Objects.equals`, а `apiResponse()` каждый раз создаёт новый `JSONObject`
    (`MUC:458–460`, `483–488`); дедупликация, скорее всего, не срабатывает.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`mailbox-gdd.md`](/workspace/client/.claude/docs/game-design/mailbox-gdd.md), черновик по коду. Правила почты записаны пунктами [#gdd-open](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-open)
(О1–О12) и ждут подтверждения; подтверждено только «системные письма доходят до игрока».

| Раздел ГДД | Пункт `#gdd-open` | Реализация |
|---|---|---|
| [#gdd-purpose](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-purpose) | О1 | заглушки `RewardsPage`, `MailboxPage` ([`#cls-pages`](#cls-pages)) |
| [#gdd-unread](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-unread) | О2, О3 | `unreadDialogs`, `init()` (не вызывается), `apiResponse()` компонента, `MailboxDao.getUnreadDialogOpponentIds` |
| [#gdd-dialogs](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-dialogs) | О5 | `dialogsSubscribe`, `MailboxDao.getDialogs`, `MailboxDialog` |
| [#gdd-messages](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-messages) | О4, О6, О11 | `messagesSubscribe`, `markMessagesRead`, `MailboxDao.getMessages`, `receiveSystemMessage` (заглушка, баг) |
| [#gdd-send-restrictions](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-send-restrictions) | О7, О10 | `sendMessage`, `MailboxDao.isBlacklisted`, `MessagesPage` |
| [#gdd-friends](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-friends) | О8, О10, О12 | `addToFriends`, `deleteFromFriends`, `getFriends`, `MailboxDao.*Friend*` |
| [#gdd-blacklist](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-blacklist) | О8, О9, О10, О12 | `addToBlacklist`, `deleteFromBlacklist`, `getBlacklist`, `MailboxDao.*Blacklist*` |

Расхождения и пробелы по сверке с ГДД (2026-10-17), решения пользователя не приняты:

- ГДД ([#gdd-dialogs](/workspace/client/.claude/docs/game-design/mailbox-gdd.md#gdd-dialogs)) описывает число непрочитанных в диалоге, сервер отдаёт 0 или 1 (п.2 `#tradeoffs`).
- Правило «свой чёрный список не мешает писать» (п.15) в ГДД не описано.
- Серверный счётчик `unreadDialogsCount` — число; ГДД О2 описывает индикатор без числа (показ — клиент).
- Диалоги с собеседником из своего чёрного списка скрыты в списке и счётчике — в ГДД не описано.
- В1: письма-приглашения в клан (`addMessage`, `updateMessage`) в ГДД почты не описаны; обходят чёрный список получателя, не обновляют текст диалога (п.16 `#tradeoffs`).
- В2: индекс `BAN` в `MessageEncoder` сменился с 0 на 1 из-за `CLAN_INVITE` в начале enum; клиентский декодер `|s|` по ранее зафиксированному не существует, но совместимость с будущим декодером не определена.
- Отказ добавить в список (лимит, служебный аккаунт) сервер возвращает как `error`; что видит игрок — О10.

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от `/workspace/server/`; `…/game` = `game/src/main/java/com/linkedgames/game`.

### Файлы прямого влияния

- `…/game/model/mailbox/MailboxUserComponent.java` — логика почты игрока.
- `…/game/model/mailbox/MailboxMessage.java` — модель сообщения.
- `…/game/model/mailbox/MailboxDialog.java` — модель диалога.
- `…/game/dao/MailboxDao.java` — коллекции `mailbox_*`, лимиты, `updateMessage`.
- `…/game/pages/ws/ingame/mailbox/MailboxPage.java` — `/ingame/mailbox`, заглушка.
- `…/game/pages/ws/ingame/mailbox/DialogsPage.java` — подписка на список диалогов.
- `…/game/pages/ws/ingame/mailbox/MessagesPage.java` — переписка, отправка, прочтение.
- `…/game/pages/ws/ingame/mailbox/FriendsPage.java` — друзья.
- `…/game/pages/ws/ingame/mailbox/BlacklistPage.java` — чёрный список.
- `…/game/pages/ws/ingame/mailbox/RewardsPage.java` — `/ingame/mailbox/rewards`, заглушка.
- `game/src/main/resources/migrations/1755491969919_mailbox.json` — индексы `mailbox_dialogs`,
  `mailbox_messages`.

### Файлы косвенного влияния

- `…/game/model/user/User.java` — поле `mailbox`, ленивый `getMailboxComponent()`, вызов `init()` в
  `onAuthorizedActiveOnce`.
- `…/game/pages/WSRouter.java` — регистрация шести страниц почты.
- `…/game/pages/ws/ingame/BanPanelPage.java` — отправка системного письма о бане через
  `receiveSystemMessage`.
- `…/game/model/messages/Messengers.java` — зависимость: системный отправитель `POSTMAN`,
  `isSpecial`.
- `…/game/model/messages/MessageEncoder.java` — зависимость: префикс `|s|`, `banMessage`,
  `clanInviteMessage`.
- `…/game/pages/ws/ingame/ClanPage.java` — косвенное влияние (область кланов, здесь только ссылкой):
  приглашения шлют `addMessage`, принятие и отклонение — `updateMessage`. `ClanChatPage` использует
  `MessageEncoder.hasEncoderSignaturePrefix`.
- `…/game/model/notifications/NotificationId.java` — зависимость: ключ уведомления `MAILBOX_ID`.
- `…/game/model/notifications/NotificationUserComponent.java` — зависимость: доставка уведомления
  `/events/userNotification`.
- `…/game/APICodeList.java` — зависимость: `ERR_SECTION_MAILBOX`, `ERR_BLACKLIST`.
- `…/game/model/user/tasks/UserSignatureCollectorTask.java` — зависимость: подписи собеседников.
- `…/game/service/user/UserStore.java` — зависимость: доставка в актор получателя.
- Клиент (контракт, не анализировался): `/workspace/client/src/views/home_screen/popups/mailbox/**`,
  `mailbox.d.ts`, `src/shared/notifications/Notifications.ts`, `src/shared/header/presets/HeaderProfile.ts`,
  `src/views/home_screen/popups/profile/ProfilePopup.ts`.
