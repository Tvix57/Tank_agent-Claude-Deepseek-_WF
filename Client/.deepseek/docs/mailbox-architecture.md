# Почта — окно `MailboxPopup`, личные сообщения, друзья, чёрный список (клиент)

> **auto-create** — документ составлен `client-analyst-lead` по существующему коду, 2026-10-17.
> Запуском не проверялось. Код в рамках задачи не менялся. Актуализировано 2026-10-19 после merge `origin/amnesia/fix` (сверено с кодом).
> Серверная сторона: `MailboxUserComponent`, `MailboxDao`, страницы `pages/ws/ingame/mailbox/*` в
> `/workspace/server`; серверного документа нет (в серверном реестре — строка `MailboxUserComponent`,
> статус «нет»). Сервер здесь упоминается только там, где без него непонятен контракт.

ГДД: [`game-design/mailbox-gdd.md`](game-design/mailbox-gdd.md) (черновик, по коду, 2026-10-17). Ссылки `#gdd-…` ниже ведут в него.
Почти все правила там пока в «Открытых вопросах» ([#gdd-open](game-design/mailbox-gdd.md#gdd-open)): так сделано в коде,
пользователь их не подтвердил.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. [Классы и методы](#classes)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Почта — личная переписка игроков один на один плюс списки друзей и чёрный список. Окно
`MailboxPopup` открывается только из профиля (`ProfilePopup`): из своего профиля — на списке
диалогов, из чужого — сразу на переписке с этим игроком.

В окне четыре вкладки (ключи `mailboxScreen.tab0..tab3`):

| Вкладка | Секция | Что делает |
|---|---|---|
| «НАГРАДЫ» | `MailboxRewardsSection` | пустая заглушка, только фон ([#rewards-stub](#rewards-stub)) |
| «СООБЩЕНИЯ» | `MailboxDialogsSection` → `MailboxMessagesSection` | список диалогов; по клику — переписка с собеседником |
| «ДРУЗЬЯ» | `MailboxFriendsSection` | список друзей: написать, удалить из друзей |
| «ЧС» | `MailboxBlacklistSection` | чёрный список: удалить из ЧС |

Правила, которые видны в клиентском коде (в ГДД записаны в [#gdd-open](game-design/mailbox-gdd.md#gdd-open) как требующие подтверждения):

- Непрочитанное — это число **диалогов** с непрочитанными сообщениями
  (`notifications.mailbox.unreadDialogsCount`), а не число сообщений. Оно приходит с сервера
  уведомлением `userNotification`. Клиент показывает только факт «есть непрочитанное»: иконку
  конверта в шапке, анимацию на кнопке почты в своём профиле и на вкладке «СООБЩЕНИЯ». Числа нигде
  нет, кроме «+N» у отдельного диалога в списке.
- Переписка открыта — входящие сообщения приходят push-событием и сразу помечаются прочитанными.
- Сообщение: не пустое после `trim`, до 255 символов (поле ввода `maxLength: 255`; сервер проверяет
  то же).
- Писать может только зарегистрированный игрок; незарегистрированному вместо поля ввода показан
  текст `chatScreen.registrationReq` и кнопка входа в `ConnectPopup`.
- Мут (`BanType.MUTE`) прячет поле ввода и показывает обратный отсчёт до конца запрета.
- Если отправитель в чёрном списке у собеседника, сервер отвечает `ERR_BLACKLIST`, и клиент прячет
  поле ввода с текстом «Вы находитесь у этого игрока в черном списке».
- Добавление в друзья/ЧС и удаление из них — через окно подтверждения.
- Добавление в ЧС из переписки возвращает на список диалогов.
- Служебные сообщения с префиксом `|s|` клиент декодирует (`MessageDecoder`): сейчас известен один вид —
  приглашение в дивизию (клан); в переписке оно рисуется отдельным блоком с кнопками «ПРИНЯТЬ»/
  «ОТКЛОНИТЬ» ([#cls-content](#cls-content)). Клан — отдельная область, здесь только точка стыка.

Ограничения, которые задаёт только сервер (клиент о них не знает): до 50 диалогов в списке, до 100
последних сообщений в переписке, до 50 друзей и до 50 записей в ЧС; добавление в друзья убирает
игрока из ЧС, добавление в ЧС убирает из друзей; служебным аккаунтам (`Messengers.isSpecial`) писать
и добавлять их нельзя.

**Награды из писем не реализованы** ни на клиенте, ни на сервере: вкладка есть, логики нет
([#rewards-stub](#rewards-stub)); по решению пользователя это планируемая функциональность, ждёт ТЗ.

Подтверждённое правило ГДД: системные письма (например, о бане) доходят до игрока
([#gdd-messages](game-design/mailbox-gdd.md#gdd-messages)). Сейчас не выполняется ([#system-letters](#system-letters)).

Границы области:
- входит: папка `src/views/home_screen/popups/mailbox/**`, индикатор почты в `HeaderProfile`,
  кнопка почты и её индикатор в `ProfilePopup`, ключ уведомления `Notifications.MAILBOX_ID`;
- не входит: общий чат (`popups/chat/**`; общий с почтой только атлас `atlas/community/` и ключ
  `chatScreen.registrationReq`), профиль целиком, система банов (почта лишь читает
  `Globals.account.banType`/`endBanTime`), механизм уведомлений `User.receiveNotifications`
  (общий для почты, достижений, коллекций).

<a id="references"></a>
## 2. Референсы

Нет. Документ описывает существующий код.

<a id="patterns"></a>
## 3. Паттерны

- **Окно с вкладками-секциями**: `FlashLayout` + `TabSelector` + `LayoutSlot`; секции — наследники
  `PreloadableLayout` (`onPreload` → запрос → `preloadCompleted` → `onCreate`), смена вкладки
  заменяет секцию через `LayoutSlot.put`.
- **Подписка на время жизни секции**: секция при открытии шлёт `.../subscribe`, при закрытии —
  `.../unsubscribe`; push-события слушает напрямую через `App.events.on("g/ws/events/mailbox/...")`
  (подход 3 из [server-push-events-subscription.md](server-push-events-subscription.md#approach-3)),
  без переизлучения через `GameEvents`.
- **Индикатор уведомления**: `Globals.account.onNotificationChangeCall` + чтение
  `Notifications.getNotificationObject(MAILBOX_ID)`; тот же приём у достижений и коллекций.
- **Окно подтверждения**: `GameFlash` с `setParallel(true)`, кнопки `ButtonPresets.BTN_DEFAULT`/
  `BTN_RED`, панель `PanelsPresets.PNL_WINDOW_STANDARD`
  ([panels-buttons-presets-architecture.md](panels-buttons-presets-architecture.md)).

<a id="class-list"></a>
## 4. Список классов

Задача — документирование, классы не создавались и не менялись. Состав области:

- `MailboxPopup` — окно почты, вкладки, индикатор на вкладке «СООБЩЕНИЯ».
- `MailboxDialogsSection` — список диалогов.
- `MailboxMessagesSection` — переписка с одним собеседником.
- `MailboxFriendsSection` — друзья.
- `MailboxBlacklistSection` — чёрный список.
- `MailboxRewardsSection` — заглушка вкладки наград.
- `MailboxUtils`, `content/MailboxMessage`, `content/MailboxClanInviteMessage` — содержимое «пузыря»
  сообщения; `MessageDecoder` (`src/plain/`) — разбор служебных сообщений.
- `AddToFriendsPopup`, `DeleteFromFriendsPopup`, `AddToBlacklistPopup`, `DeleteFromBlacklistPopup` —
  окна подтверждения.
- Типы `mailbox.d.ts`.
- Точки вне папки: `HeaderProfile` (индикатор), `ProfilePopup` (вход в почту и индикатор),
  `Notifications.MAILBOX_ID`.

<a id="anchors"></a>
## 5. Навигация (якоря)

Классы: [`#cls-popup`](#cls-popup), [`#cls-dialogs`](#cls-dialogs), [`#cls-messages`](#cls-messages),
[`#cls-friends-blacklist`](#cls-friends-blacklist), [`#cls-rewards`](#cls-rewards),
[`#cls-confirm`](#cls-confirm), [`#cls-content`](#cls-content), [`#types`](#types), [`#external`](#external),
[`#contract`](#contract), [`#gdd-mapping`](#gdd-mapping).

Проблемы: [`#rewards-stub`](#rewards-stub), [`#empty-index`](#empty-index),
[`#unread-dup`](#unread-dup), [`#header-icon`](#header-icon), [`#stale-flags`](#stale-flags),
[`#blacklisted-late`](#blacklisted-late), [`#mute-input`](#mute-input),
[`#subscription-overlap`](#subscription-overlap), [`#date-labels`](#date-labels),
[`#silent-errors`](#silent-errors), [`#copy-paste`](#copy-paste), [`#dead-code`](#dead-code),
[`#unread-flash`](#unread-flash), [`#system-letters`](#system-letters), [`#unread-login`](#unread-login).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Файл | Раздел |
|---|---|---|
| `MailboxPopup` | `mailbox/MailboxPopup.ts` | [#cls-popup](#cls-popup) |
| `MailboxDialogsSection` | `mailbox/MailboxDialogsSection.ts` | [#cls-dialogs](#cls-dialogs) |
| `MailboxMessagesSection` | `mailbox/MailboxMessagesSection.ts` | [#cls-messages](#cls-messages) |
| `MailboxFriendsSection`, `MailboxBlacklistSection` | `mailbox/MailboxFriendsSection.ts`, `mailbox/MailboxBlacklistSection.ts` | [#cls-friends-blacklist](#cls-friends-blacklist) |
| `MailboxRewardsSection` | `mailbox/MailboxRewardsSection.ts` | [#cls-rewards](#cls-rewards) |
| Окна подтверждения | `mailbox/popups/*.ts` | [#cls-confirm](#cls-confirm) |
| `MailboxUtils`, `MailboxMessage`, `MailboxClanInviteMessage`, `MessageDecoder` | `mailbox/MailboxUtils.ts`, `mailbox/content/*.ts`, `src/plain/MessageDecoder.ts` | [#cls-content](#cls-content) |
| Типы | `mailbox/mailbox.d.ts` | [#types](#types) |
| `HeaderProfile`, `ProfilePopup`, `Notifications` | вне папки | [#external](#external) |

Пути ниже — от `src/views/home_screen/popups/`.

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-popup"></a>
### `MailboxPopup`

Окно почты на весь экран (`FlashLayout`, тег `LOWER_FLASH_TAG`). Конфиг `MailboxPopupConfig`:
`tab` — имя стартовой вкладки (`TAB_NAME` одной из секций), `opponent` — собеседник для вкладки
переписки.

- `static publish(screen, config)` (строки 192–197) — запрашивает `/ingame/mailbox`, по ответу
  публикует окно. Ответ пустой, данные не используются ([#empty-index](#empty-index)).
- `onCreate()` (53–68) — строит интерфейс и открывает секцию по `config.tab`: `friends`,
  `blacklist`, `messages` (с `config.opponent`), иначе — диалоги. Вкладка `rewards` в эту развилку не
  попадает: откроются диалоги, а подсвечена будет вкладка «НАГРАДЫ» (строка 84). Подписывается на
  уведомления (`onNotificationChangeCall`, сразу вызывает обработчик).
- `onDestroy()` (70–72) — отписка от уведомлений.
- `UIMain()` — фон, `TabSelector` на четыре вкладки, анимация-индикатор `notificator` на вкладке
  «СООБЩЕНИЯ» (102–104), слот секции; ширина вкладок пересчитывается после каждого refresh (не шире
  150).
- `handleNotifications()` (126–129) — показывает индикатор вкладки, если `unreadDialogsCount > 0`.
  Правило «есть непрочитанное» — [#gdd-unread](game-design/mailbox-gdd.md#gdd-unread); то же выражение ещё в двух местах
  ([#unread-dup](#unread-dup)).
- `showDialogsSection()`, `showMessagesSection(opponent)` — публичные: их зовут секции (переход из
  диалогов/друзей в переписку, возврат из переписки после добавления в ЧС). Обе подсвечивают вкладку
  «СООБЩЕНИЯ». `showRewardsSection()`, `showFriendsSection()`, `showBlacklistSection()` — приватные,
  вызываются кликом по вкладке. Все пять одинаково: записать `config.tab`, создать секцию, положить в
  слот, `start()`.
- `view()`, `getAsGameFlash()` — служебные.

<a id="cls-dialogs"></a>
### `MailboxDialogsSection` (`TAB_NAME = "dialogs"`)

Список диалогов ([#gdd-dialogs](game-design/mailbox-gdd.md#gdd-dialogs)).

- `onPreload()` (31–38) — `/ingame/mailbox/dialogs/subscribe`; ответ `MailboxDialogsJSON`. Сервер
  отдаёт до 50 диалогов, сначала непрочитанные, затем по убыванию времени.
- `onCreate()` (40–46) — строит список, подписывается на push `g/ws/events/mailbox/dialogs`.
- `onDestroy()` (48–51) — `/ingame/mailbox/dialogs/unsubscribe`, отписка от push.
- `updateData(data)` (53–58) — push приносит полный список `dialogs`; секция перестраивает его
  целиком. Сервер шлёт этот push получателю каждого нового сообщения, если у того открыт список
  диалогов.
- `addDialogs()` (60–80) — очистить и заполнить скролл, разделители между строками; пустой список —
  текст `mailboxScreen.noDialogs`.
- `UIDialog(data)` (128–173) — строка: подпись собеседника (клик → `ProfilePopup` собеседника),
  последнее сообщение в одну строку (текст проходит `MessageDecoder.decode`: служебное сообщение
  показывается расшифрованным), время `dateHMToString`, зелёное «+N» при `unread > 0`. Клик по
  строке → `popup.showMessagesSection(data.user)`.

<a id="cls-messages"></a>
### `MailboxMessagesSection` (`TAB_NAME = "messages"`)

Переписка с одним собеседником ([#gdd-messages](game-design/mailbox-gdd.md#gdd-messages), [#gdd-send-restrictions](game-design/mailbox-gdd.md#gdd-send-restrictions)).
Собеседник задаётся `setOpponent(data)` до `start()`.

- `onPreload()` (51–58) — `/ingame/mailbox/messages/subscribe { opponent }`; ответ
  `MailboxMessagesJSON`: до 100 последних сообщений (новые первыми), флаги `friend`, `blacklisted`.
  Сервер в этом же запросе помечает диалог прочитанным. Нет диалога с этим игроком — сервер
  отвечает пустым списком и `false` во флагах.
- `onCreate()` (59–71) — строит интерфейс, добавляет сообщения в обратном порядке (старые сверху),
  вызывает `showBanData()`, подписывается на push `g/ws/events/mailbox/messages` и на обновление
  аккаунта (для мута).
- `onDestroy()` (73–77) — `/ingame/mailbox/messages/unsubscribe` и отписки.
- `updateData(data)` (83–88) — push `newMessage` (сервер шлёт его только для входящего сообщения от
  того, с кем открыта переписка): добавить сообщение и отправить `/ingame/mailbox/messages/read`.
- `addMessage(data, order)` (90–108) — перед сообщением вставляет разделитель даты, если дата
  сменилась (`lastDate`); своё сообщение выравнивается вправо, чужое влево; анимация появления с
  задержкой `100 * order` мс, не больше секунды.
- `UIMessage(data)` (251–288) — «пузырь» (`UIBubble`, `BorderPanel` из `atlas/community/bubble/*`),
  подпись автора, содержимое, время `timeHHMMToString`. Содержимое выбирает
  `MessageDecoder.decodeMessageId(data.text)`: `MailboxUtils.CLAN_INVITE` (0) → `MailboxClanInviteMessage`,
  иначе `MailboxMessage` (обычный текст); размер пузыря берётся из `content.width()/height()`
  ([#cls-content](#cls-content)).
- `UIDate(date)` (290–309) — подменяет дату на «СЕГОДНЯ»/«ВЧЕРА» ([#date-labels](#date-labels)).
- `UIHeader()` (311–419) — «Диалог с» + подпись собеседника (цвет по правам: админ — зелёный,
  модератор — жёлтый; клик → профиль), кнопка «в друзья»/«из друзей» по `data.friend`, кнопка ЧС:
  при `data.blacklisted = false` — добавить (после успеха — `popup.showDialogsSection()`), иначе —
  убрать. После каждого подтверждения меняет локальный флаг и перестраивает шапку
  ([#stale-flags](#stale-flags)). Правила — [#gdd-friends](game-design/mailbox-gdd.md#gdd-friends), [#gdd-blacklist](game-design/mailbox-gdd.md#gdd-blacklist).
- `UIMain()` (126–234) — шапка, скролл, поле ввода (`maxLength: 255`, отправка по Enter), кнопка
  отправки, скрытый текст «в ЧС у собеседника», текст мута `forbidText`; для незарегистрированного
  игрока поле и кнопка скрыты, вместо них — `registrationReq` с кнопкой `ConnectPopup` (успешный вход
  возвращает поле ввода).
- `showBanData()` (435–462) — при `BanType.MUTE` прячет поле ввода, показывает отсчёт до
  `endBanTime`, по окончании возвращает поле ([#mute-input](#mute-input)).
- `BtnSendMessage()` (464–484) — пустой после `trim` текст не отправляется;
  `/ingame/mailbox/messages/send { opponent, text }`; успех — очистить поле и добавить
  `response.newMessage`; ошибка `ERR_BLACKLIST` → `showBlacklist(true)`; другие ошибки молча
  ([#silent-errors](#silent-errors)).
- `showBlacklist(show)` (119–124) — переключает поле ввода и текст `mailboxScreen.blacklisted`.
- `UINoMessages()` — текст `mailboxScreen.noMessages`.

<a id="cls-friends-blacklist"></a>
### `MailboxFriendsSection` (`"friends"`) и `MailboxBlacklistSection` (`"blacklist"`)

Два почти одинаковых списка игроков ([#copy-paste](#copy-paste)). [#gdd-friends](game-design/mailbox-gdd.md#gdd-friends) и
[#gdd-blacklist](game-design/mailbox-gdd.md#gdd-blacklist).

- `onPreload()` (29–36) — `/ingame/mailbox/friends/get` → `MailboxFriendsJSON` либо
  `/ingame/mailbox/blacklist/get` → `MailboxBlacklistJSON`. Push-подписок нет: список обновляется
  только при повторном открытии вкладки.
- `addElements()` (44–65) — перестроить список; пусто — `mailboxScreen.noElements`.
- `UIElement(data)` — подпись (клик → профиль) и кнопки. У друзей — «написать»
  (`popup.showMessagesSection(data)`) и «удалить» (`DeleteFromFriendsPopup`); у ЧС — только
  «удалить» (`DeleteFromBlacklistPopup`). После подтверждения игрок убирается из локального массива,
  список перестраивается.

<a id="cls-rewards"></a>
### `MailboxRewardsSection` (`"rewards"`)

Только фон вкладки (строки 6–18): нет запроса, нет `onCreate`, поле `data: any` не используется.
На сервере роут `/ingame/mailbox/rewards` отвечает пустым `ok`, клиент его не вызывает. Награды
из писем в ГДД — открытый вопрос О1 ([#gdd-open](game-design/mailbox-gdd.md#gdd-open)), см. [#rewards-stub](#rewards-stub).

<a id="cls-confirm"></a>
### Окна подтверждения (`popups/*.ts`)

`AddToFriendsPopup`, `DeleteFromFriendsPopup`, `AddToBlacklistPopup`, `DeleteFromBlacklistPopup` —
четыре копии одного окна ([#copy-paste](#copy-paste)). Конфиг: `user`, `onYes`, `onNo`, `onExit`.

- `static publish(screen, config)` — параллельный `GameFlash` поверх почты.
- `UIMain()` — окно 310 px, заголовок (`mailboxScreen.friends` или `mailboxScreen.blacklist`, шрифт 17), крестик,
  блокирует экран на время анимации появления.
- `UIContent()` — вопрос (`addFriend`/`delFriend`/`addBlacklist`/`delBlacklist`) с именем (шрифт 14), окрашенным по
  правам; кнопки «Да, продолжить» и «Не уверен» (`onNo` и закрытие).
- `BtnAddToFriends()` / `BtnDeleteFromFriends()` / `BtnAddToBlacklist()` / `BtnDeleteFromBlacklist()`
  (строки 139–152) — `sendButtonRequest` на `/ingame/mailbox/friends/add|delete` или
  `/ingame/mailbox/blacklist/add|delete` с `{ id }`; при `ok` — `onYes` и закрытие; ошибка
  игнорируется, окно остаётся открытым ([#silent-errors](#silent-errors)).
- `onDestroy()` — `onExit` (секции возвращают интерактивность скролла).

<a id="cls-content"></a>
### Содержимое сообщения и `MessageDecoder`

Путь к файлам: `mailbox/MailboxUtils.ts`, `mailbox/content/*.ts` — от `popups/`; `MessageDecoder` —
`src/plain/MessageDecoder.ts`.

- `MessageDecoder` — служебное сообщение распознаётся по префиксу `|s|` (`hasSignaturePrefix`), поля
  разделены `|`: `|s|<id>|…`. `decodeMessageId(text)` отдаёт `id` или `-1` для обычного текста;
  `decode(text)` через `MESSAGE_ROUTER` (индекс = `id`) собирает читаемый текст; обычный текст и
  неизвестный `id` возвращает как есть. В роутере сейчас одна запись — `clanInviteMessage`
  (`|s|0|clanId|clanName|status`), ключ `messageDecoder.clanInvite.text`. Кодирует сервер
  (`MessageEncoder`), на сервере есть ещё `BAN` с `id = 1`, на клиенте его нет — письмо о бане
  показалось бы сырым текстом ([#system-letters](#system-letters)).
- `MailboxUtils` — константа `CLAN_INVITE = 0` (соответствует индексу в `MESSAGE_ROUTER`; связь
  держится только совпадением чисел). Метод `getSenderBodyText` возвращает `""` и нигде не вызывается
  ([#dead-code](#dead-code)).
- `MailboxMessage` (`IViewProvider`) — обычный текст сообщения (`RichTextBuilder`, шрифт 15, перенос
  300) через `MessageDecoder.decode`; даёт `width()`, `height()`, `view()`.
- `MailboxClanInviteMessage` (`IViewProvider`) — приглашение в клан: текст, затем по `status` из
  сообщения (`"1"` — отклонено, `"2"` — принято, иначе — ожидание). В ожидании запрашивает
  `/ingame/clan/inviteInfo { clanId }` и показывает кнопки «ПРИНЯТЬ» (`/ingame/clan/inviteAccept`,
  при успехе `Globals.account.clanId` и событие `GameEvents.CLAN_UPDATE`; `ERR_CLAN_IS_FULL` —
  «Максимум участников»), «ОТКЛОНИТЬ» (`/ingame/clan/inviteReject`) и «i» (открывает `ClanPopup`).
  Статус в тексте сообщения клиент локально не обновляет: после перезахода состояние берётся из
  сообщения, пришедшего с сервера. Логика кланов — отдельная область, здесь не описывается.
- `ConfirmPopup` (`src/views/popups/ConfirmPopup.ts`) в почте не используется: его вызывают только
  `ClanInfoPopup` и `ClanUserProfilePopup`. Почтовые окна подтверждения остались своими копиями
  ([#copy-paste](#copy-paste)).

<a id="types"></a>
### Типы `mailbox.d.ts`

- `MailboxPopupJSON` — пустой интерфейс, ответ `/ingame/mailbox`.
- `MailboxDialogsJSON { dialogs }`, `MailboxDialogJSON { id, user, text, time, read, unread, friend,
  blacklisted, deleted? }` — клиент читает `user`, `text`, `time`, `unread`; остальное не используется.
- `MailboxMessagesJSON { messages, friend, blacklisted, unread }` — `unread` не используется.
- `MailboxMessageJSON { id, userId, text, time }` — `userId` — автор; сравнение с
  `Globals.account.id` определяет сторону.
- `MailboxFriendsJSON { friends }`, `MailboxBlacklistJSON { blacklist }` — массивы
  `UserSignatureJSON` (общий тип из `src/types/interfaces.d.ts`).

Типы push-событий не объявлены: `updateData(data: any)` в обеих секциях.

<a id="external"></a>
### Точки вне папки

- `src/shared/header/presets/HeaderProfile.ts` — спрайт `mail` (`atlas/home_screen/btn/mailbox.png`,
  строка 50) виден, если `unreadDialogsCount > 0` (`handleUserNotifications`, 105–112). Иконка не
  кнопка: клик по этой области попадает в кнопку профиля (`profileBtn`, 85–89; шапка после merge перерисована: уровень и сила в одной строке, полоска опыта 2 px, на почту это не влияет) ([#header-icon](#header-icon)).
- `src/views/home_screen/popups/profile/ProfilePopup.ts` — `UIMailbox()` (261–281): кнопка почты в
  шапке профиля; в своём профиле открывает почту на диалогах, в чужом — на переписке с владельцем
  профиля. В своём профиле на кнопке есть `AttentionAnimation`, видимость — в
  `handleUserNotifications()` (350–360).
- `src/shared/notifications/Notifications.ts` — константа `MAILBOX_ID = "mailbox"`,
  `getNotificationObject`. Рядом после merge добавлен `MILITARY_BASE` (военная база, к почте не относится).
- Доставка уведомления: push `g/ws/events/userNotification` → `SceneImpl.onReceiveNotification` →
  `User.receiveNotifications` → событие `g/account/notifications`. Значение для почты —
  `{ unreadDialogsCount }`; сервер шлёт его при входе (если непрочитанное есть), при новом входящем
  сообщении и при прочтении диалога.

<a id="contract"></a>
### Контракт с сервером

| Запрос / событие | Кто вызывает | Ответ / данные |
|---|---|---|
| `/ingame/mailbox` | `MailboxPopup.publish` | пустой `ok` |
| `/ingame/mailbox/dialogs/subscribe`, `/unsubscribe` | `MailboxDialogsSection` | `{ dialogs }` / `ok` |
| push `/events/mailbox/dialogs` | сервер → `MailboxDialogsSection.updateData` | `{ dialogs }` |
| `/ingame/mailbox/messages/subscribe { opponent }`, `/unsubscribe` | `MailboxMessagesSection` | `{ messages, friend, blacklisted, unread }` / `ok` |
| `/ingame/mailbox/messages/send { opponent, text }` | `BtnSendMessage` | `{ newMessage }`; ошибка `MAILBOX/ERR_BLACKLIST` |
| `/ingame/mailbox/messages/read { opponent }` | `updateData` | `ok` |
| push `/events/mailbox/messages` | сервер → `MailboxMessagesSection.updateData` | `{ newMessage }` |
| `/ingame/mailbox/friends/get`, `/add {id}`, `/delete {id}` | `MailboxFriendsSection`, окна подтверждения | `{ friends }` / `ok` |
| `/ingame/mailbox/blacklist/get`, `/add {id}`, `/delete {id}` | `MailboxBlacklistSection`, окна подтверждения | `{ blacklist }` / `ok` |
| push `/events/userNotification` (`name: "mailbox"`) | сервер → `User.receiveNotifications` | `{ unreadDialogsCount }` |
| `/ingame/mailbox/rewards` | никто | пустой `ok` |
| `/ingame/clan/inviteInfo`, `/inviteAccept`, `/inviteReject` | `MailboxClanInviteMessage` | область кланов; см. [#cls-content](#cls-content) |

Подписки на сервере — одно поле на игрока: флаг `dialogsSubscription` и один `messagesSubscription`
(id собеседника). См. [#subscription-overlap](#subscription-overlap).

<a id="gdd-mapping"></a>
### Сопоставление функций с ГДД ([`#gdd-function-mapping`](agent-system-workflow.md#gdd-function-mapping))


| Правило ГДД | Функции | Дубли |
|---|---|---|
| [#gdd-unread](game-design/mailbox-gdd.md#gdd-unread) — есть непрочитанные диалоги | `MailboxPopup.handleNotifications`, `HeaderProfile.handleUserNotifications`, `ProfilePopup.handleUserNotifications` | одно выражение в трёх местах — [#unread-dup](#unread-dup) |
| [#gdd-dialogs](game-design/mailbox-gdd.md#gdd-dialogs) — список и порядок диалогов | `MailboxDialogsSection.onPreload/updateData/UIDialog` | нет |
| [#gdd-messages](game-design/mailbox-gdd.md#gdd-messages) — переписка, прочтение | `MailboxMessagesSection.onPreload/updateData/addMessage` | нет |
| [#gdd-send-restrictions](game-design/mailbox-gdd.md#gdd-send-restrictions) — кто и что может отправить | `UIMain` (регистрация), `showBanData` (мут), `BtnSendMessage` (пустой текст, ЧС), `maxLength: 255` | проверка «может ли игрок писать» разбросана по трём местам и не сведена в одну функцию — [#mute-input](#mute-input) |
| (в ГДД нет, см. вопрос в отчёте) — служебные сообщения | `MessageDecoder.decode/decodeMessageId`, `MailboxMessage`, `MailboxClanInviteMessage` | `MailboxUtils.CLAN_INVITE` и `MESSAGE_ROUTER[0]` дублируют один смысл (`id` = 0) числом в двух файлах |
| [#gdd-friends](game-design/mailbox-gdd.md#gdd-friends) | `AddToFriendsPopup.BtnAddToFriends`, `DeleteFromFriendsPopup.BtnDeleteFromFriends`, `MailboxFriendsSection` | копии окон — [#copy-paste](#copy-paste) |
| [#gdd-blacklist](game-design/mailbox-gdd.md#gdd-blacklist) | `AddToBlacklistPopup.BtnAddToBlacklist`, `DeleteFromBlacklistPopup.BtnDeleteFromBlacklist`, `MailboxBlacklistSection`, `showBlacklist` | копии окон и секций — [#copy-paste](#copy-paste) |

Неявный порядок вызовов ([`#no-implicit-order`](agent-system-workflow.md#no-implicit-order)):
`MailboxMessagesSection` после подтверждения сам меняет `data.friend`/`data.blacklisted` и
перестраивает шапку (строки 348–349, 368–369, 390–391, 406–407). Связь «друг ⇄ не в ЧС» живёт на
сервере, на клиенте её нет ([#stale-flags](#stale-flags)); кандидат — один метод-переход у секции
(«отношение к собеседнику изменилось»), который ставит оба флага по ответу сервера или
перезапрашивает их.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Решение пользователя есть только по п.14 (отложенный баг) и п.1 (ждёт ТЗ); остальное — находки анализа, не согласованные с пользователем. Номера строк — на 2026-10-17.

<a id="rewards-stub"></a>
### 1. Вкладка «НАГРАДЫ» пустая, награды из писем не реализованы

`mailbox/MailboxRewardsSection.ts:6-18` — только фон; `MailboxPopup.ts:80-85` — вкладка показана
всегда; сервер: `RewardsPage` отвечает пустым `ok`, `MailboxUserComponent.receiveSystemMessage` —
`// TODO`. Игрок видит вкладку, в которой ничего нет. Открыть окно сразу на этой вкладке нельзя:
`onCreate` (`MailboxPopup.ts:57-65`) уводит в диалоги, а подсвеченной остаётся «НАГРАДЫ» (строка 84).
По решению пользователя (2026-10-17) награды из писем и рассылки — «планируется, ждём ТЗ» ([#gdd-open](game-design/mailbox-gdd.md#gdd-open), О1); реализация — кросс-репо задача.

<a id="empty-index"></a>
### 2. Лишний запрос `/ingame/mailbox` перед открытием

`MailboxPopup.ts:47-51`, `192-197`: окно ждёт ответа на запрос, который ничего не возвращает
(`MailboxPopupJSON` пуст, поле `data` (строка 37) не читается). Лишний round-trip; при ошибке запроса
окно молча не откроется — у `then` нет `catch`.

<a id="unread-dup"></a>
### 3. Правило «есть непрочитанное» записано трижды

`HeaderProfile.ts:106`, `ProfilePopup.ts:351`, `MailboxPopup.ts:127` — одно и то же выражение
`getNotificationObject(MAILBOX_ID).unreadDialogsCount ? … : 0` с двойным вызовом. Кандидат — одна
функция рядом с `Notifications` (имя — через скилл `naming`). Ключ `unreadDialogsCount` не
типизирован.

<a id="header-icon"></a>
### 4. Иконка в шапке — только индикатор, без числа и без перехода

`HeaderProfile.ts:50`, `110`: спрайт виден при непрочитанном, но число не показывает и сам не
нажимается; поверх лежит кнопка профиля шириной 180 (строки 85–89), поэтому клик открывает профиль, а
не почту. До почты из шапки — два клика (профиль → кнопка почты). Если ТЗ предполагает «счётчик» в
шапке — это расхождение с кодом; в ГДД открытый вопрос О2 ([#gdd-open](game-design/mailbox-gdd.md#gdd-open)).

<a id="stale-flags"></a>
### 5. Флаги «друг» и «в ЧС» в переписке расходятся с сервером

`MailboxMessagesSection.ts:348-349`, `390-394`: после «добавить в друзья» клиент ставит
`friend = true`, но не сбрасывает `blacklisted`, хотя сервер при добавлении в друзья удаляет игрока
из ЧС (`MailboxUserComponent.addToFriends`). Сценарий: открыть переписку с игроком из ЧС (из
профиля), добавить в друзья — кнопка ЧС продолжит предлагать «удалить из ЧС». Обратный случай
(добавление в ЧС) маскируется переходом на диалоги (строка 394). Поля `friend`/`blacklisted` в
`MailboxDialogJSON` клиент не читает.

<a id="blacklisted-late"></a>
### 6. О том, что тебя внесли в ЧС, игрок узнаёт только после попытки отправить

`MailboxMessagesSection.ts:480-481`, `119-124`: поле ввода прячется только по ошибке `ERR_BLACKLIST`
на `send`. В ответе `subscribe` поле `blacklisted` означает «я внёс собеседника в ЧС» (так его
трактует кнопка в шапке), признака «собеседник внёс меня» нет. Игрок набирает сообщение и только
потом видит запрет. Для исправления нужен признак в ответе сервера — вопрос контракта
(`integration-lead`).

<a id="mute-input"></a>
### 7. Мут, регистрация и ЧС управляют одним полем ввода независимо

`MailboxMessagesSection.ts:196-225` (регистрация), `435-462` (мут), `119-124` (ЧС). Каждая ветка сама
прячет и показывает поле, кнопку и подложку. Последствия:
- по окончании мута `onInvalid` (452–458) показывает поле ввода даже незарегистрированному игроку и
  даже если до этого сработал `ERR_BLACKLIST`; у незарегистрированного поверх остаётся
  `registrationReq`;
- `showBanData` вызывается на каждое обновление аккаунта (строка 70) и при муте каждый раз заводит
  новый тикер (`App.tick.add`, 444) — тикеры копятся, пока идёт мут.
Кандидат — одна функция «может ли игрок писать сейчас» и одно место, которое по ней переключает
блок ввода.

<a id="subscription-overlap"></a>
### 8. Два окна почты делят одну серверную подписку

Сервер хранит одну подписку на переписку (`messagesSubscription`) и один флаг на диалоги. Цепочка
«переписка → клик по имени собеседника (строка 336) → профиль → кнопка почты» открывает второе окно
почты на той же переписке; при его закрытии `messages/unsubscribe` (строка 74) снимает подписку, и
первое окно перестаёт получать входящие. Как `FlashPublisher` складывает такие окна, запуском не
проверялось.

<a id="date-labels"></a>
### 9. «СЕГОДНЯ»/«ВЧЕРА» зависят от формата локали

`MailboxMessagesSection.ts:290-301`: «сегодня» собирается вручную как `dd.mm.yyyy` и сравнивается с
`TimeUtils.dateToStringShort` (`toLocaleDateString(system.dateLocale)`, `TimeUtils.ts:111-114`).
Совпадает только для локалей с таким форматом (`ru-RU`); при другой локали подписи не появятся.
Сейчас в проекте полноценная только `ru` (`en.json` — заготовка), поэтому проблема скрыта.

<a id="silent-errors"></a>
### 10. Ошибки действий не показываются игроку

`popups/AddToFriendsPopup.ts:148-150` и такие же `catch` в трёх других окнах; `BtnSendMessage`
(`MailboxMessagesSection.ts:480-484`) обрабатывает только `ERR_BLACKLIST`. При лимите 50 друзей/ЧС,
попытке добавить служебный аккаунт или ошибке отправки окно просто не реагирует. Есть ли общий показ
ошибок в `WSSocket.sendRequest`, не проверялось. Со стороны сервера: `deleteFromFriends`/
`deleteFromBlacklist` не имеют `onFail` — при ошибке БД ответа не будет совсем (серверная зона).

<a id="copy-paste"></a>
### 11. Копии кода

- Четыре окна подтверждения (`popups/*.ts`, ~170 строк каждое) отличаются роутом, ключами текста,
  заголовком и шириной переноса текста (350 у окон добавления, 300 у окон удаления).
- `MailboxFriendsSection` и `MailboxBlacklistSection` совпадают, кроме роута, поля массива и кнопки
  «написать».
- Разделитель строк (два `px.png`) скопирован в три секции.
Кандидат — одно параметризованное окно подтверждения и одна секция списка игроков.

<a id="dead-code"></a>
### 12. Неиспользуемый код — кандидаты на удаление

- `MailboxPopup.data` (строка 37) и тип `MailboxPopupJSON`;
- `MailboxRewardsSection.data` (строка 11);
- `private data: any` в окнах подтверждения (строка 32);
- закомментированный `onClick` подписи в `UIMessage` (`MailboxMessagesSection.ts:266-268`);
- `MailboxUtils.getSenderBodyText` — возвращает `""`, вызовов нет;
- неиспользуемые переменные разбора: `clanName` в `MailboxClanInviteMessage`, `clanId` и `status` в `MessageDecoder.clanInviteMessage`;
- поля типов, которые клиент не читает: `MailboxDialogJSON.read/friend/blacklisted/deleted`,
  `MailboxMessagesJSON.unread`.

<a id="unread-flash"></a>
### 13. Мигание индикатора при открытой переписке

Входящее сообщение в открытую переписку сервер сначала отмечает непрочитанным и шлёт уведомление,
затем клиент отвечает `/read` (`MailboxMessagesSection.ts:86`), и приходит второе уведомление. На
короткое время индикатор в шапке и на вкладке загорается. Исправляется на сервере: не считать
непрочитанным сообщение от собеседника, на переписку с которым игрок подписан.

<a id="system-letters"></a>
### 14. Системные письма (о бане) не доходят и не отображаются

Нарушает подтверждённое правило [#gdd-messages](game-design/mailbox-gdd.md#gdd-messages); отложено как баг (решение
пользователя 2026-10-17, [О4](game-design/mailbox-gdd.md#gdd-open)). Сервер: `BanPanelPage` при бане вызывает
`MailboxUserComponent.receiveSystemMessage(Messengers.POSTMAN.id, MessageEncoder.banMessage(...))`, а
метод пустой (`// TODO`), письмо теряется. Клиент: после merge декодер есть (`MessageDecoder`, [#cls-content](#cls-content)), но в нём только приглашение в клан (`id = 0`); для бана (`id = 1` на сервере) записи нет, и текст `|s|1|…` показался бы как есть: `decode` возвращает неизвестный `id` без изменений. Имя отправителя клиент уже
умеет показывать (`Users.isSpecial` → `system.messengers.*`). Исправление кросс-репо: сначала
доставка на сервере, затем запись для бана в `MESSAGE_ROUTER`.

<a id="unread-login"></a>
### 15. После входа в игру индикатор непрочитанного пуст

Серверная причина: `MailboxUserComponent.init()`, который загружает непрочитанные диалоги и шлёт
уведомление, нигде не вызывается. Клиент получает `unreadDialogsCount` только после первого нового
входящего, и счёт идёт лишь по диалогам, пришедшим с этого момента. В ГДД — открытый вопрос
[О3](game-design/mailbox-gdd.md#gdd-open). Клиентский код менять не нужно.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`game-design/mailbox-gdd.md`](game-design/mailbox-gdd.md), черновик по коду от 2026-10-17. Разделы описывают механику, а правила из кода
(лимиты, длина сообщения, ограничения отправки, связь друзей и ЧС) пока стоят в
[#gdd-open](game-design/mailbox-gdd.md#gdd-open) пунктами О5–О9 как «так в коде, требует подтверждения». Расхождением с ГДД
считается только нарушение подтверждённого правила: сейчас это системные письма
([#system-letters](#system-letters)).

| Раздел ГДД | Где на клиенте | Замечания по коду |
|---|---|---|
| [#gdd-purpose](game-design/mailbox-gdd.md#gdd-purpose) | [`MailboxPopup`](#cls-popup) | — |
| [#gdd-entry](game-design/mailbox-gdd.md#gdd-entry) (вход в почту) | [`ProfilePopup.UIMailbox`](#external) | из шапки не открывается ([#header-icon](#header-icon)) |
| [#gdd-unread](game-design/mailbox-gdd.md#gdd-unread) | [`#external`](#external), `MailboxPopup.handleNotifications` | считаются диалоги, числа нет ([#unread-dup](#unread-dup)); после входа пусто ([#unread-login](#unread-login)) |
| [#gdd-dialogs](game-design/mailbox-gdd.md#gdd-dialogs) | [`MailboxDialogsSection`](#cls-dialogs) | лимит 50 и порядок только на сервере |
| [#gdd-messages](game-design/mailbox-gdd.md#gdd-messages) | [`MailboxMessagesSection`](#cls-messages) | правило «системные письма доходят до игрока» не выполняется ([#system-letters](#system-letters)); 100 последних, без подгрузки старых; даты ([#date-labels](#date-labels)) |
| [#gdd-send-restrictions](game-design/mailbox-gdd.md#gdd-send-restrictions) | `UIMain`, `showBanData`, `BtnSendMessage` | [#mute-input](#mute-input), [#blacklisted-late](#blacklisted-late) |
| [#gdd-friends](game-design/mailbox-gdd.md#gdd-friends) | [`MailboxFriendsSection`](#cls-friends-blacklist), [окна](#cls-confirm) | лимит 50 только на сервере, ошибка молча |
| [#gdd-blacklist](game-design/mailbox-gdd.md#gdd-blacklist) | [`MailboxBlacklistSection`](#cls-friends-blacklist), [окна](#cls-confirm) | [#stale-flags](#stale-flags) |
| (нет раздела) служебные сообщения, приглашение в клан | [`#cls-content`](#cls-content) | в ГДД не описано |
| [#gdd-open](game-design/mailbox-gdd.md#gdd-open) (О1, награды) | [`MailboxRewardsSection`](#cls-rewards) | не реализовано ([#rewards-stub](#rewards-stub)) |

<a id="file-map"></a>
## 10. Карта файлов компонента

Критерий полноты: `grep` по `MailboxPopup`, `Mailbox*Section`, `Mailbox*JSON`, `AddToFriendsPopup`,
`DeleteFromFriendsPopup`, `AddToBlacklistPopup`, `DeleteFromBlacklistPopup`, `MAILBOX_ID`,
`unreadDialogsCount`, `/ingame/mailbox`, `events/mailbox`, `mailboxScreen.` по `src`; каждый файл с
вхождением стоит ниже; добавлены поиски по `MessageDecoder`, `MailboxUtils`, `content/`. Сверено 2026-10-19.

### Файлы прямого влияния

- `src/views/home_screen/popups/mailbox/MailboxPopup.ts` — окно почты, вкладки, индикатор вкладки.
- `src/views/home_screen/popups/mailbox/MailboxDialogsSection.ts` — список диалогов, подписка на диалоги.
- `src/views/home_screen/popups/mailbox/MailboxMessagesSection.ts` — переписка, отправка, прочтение, мут, ЧС.
- `src/views/home_screen/popups/mailbox/MailboxFriendsSection.ts` — список друзей.
- `src/views/home_screen/popups/mailbox/MailboxBlacklistSection.ts` — чёрный список.
- `src/views/home_screen/popups/mailbox/MailboxRewardsSection.ts` — заглушка вкладки наград.
- `src/views/home_screen/popups/mailbox/popups/AddToFriendsPopup.ts` — подтверждение «в друзья».
- `src/views/home_screen/popups/mailbox/popups/DeleteFromFriendsPopup.ts` — подтверждение «из друзей».
- `src/views/home_screen/popups/mailbox/popups/AddToBlacklistPopup.ts` — подтверждение «в ЧС».
- `src/views/home_screen/popups/mailbox/popups/DeleteFromBlacklistPopup.ts` — подтверждение «из ЧС».
- `src/views/home_screen/popups/mailbox/mailbox.d.ts` — типы ответов почты.
- `src/views/home_screen/popups/mailbox/MailboxUtils.ts` — константа вида служебного сообщения `CLAN_INVITE`.
- `src/views/home_screen/popups/mailbox/content/MailboxMessage.ts` — обычное сообщение в «пузыре».
- `src/views/home_screen/popups/mailbox/content/MailboxClanInviteMessage.ts` — приглашение в клан в «пузыре» (стык с областью кланов).

### Файлы косвенного влияния

- `src/views/home_screen/popups/profile/ProfilePopup.ts` — единственный вход в почту (`UIMailbox`),
  индикатор непрочитанного на кнопке в своём профиле.
- `src/shared/header/presets/HeaderProfile.ts` — иконка конверта в шапке при непрочитанном.
- `src/shared/notifications/Notifications.ts` — ключ `MAILBOX_ID`, чтение объекта уведомления.
- `src/plain/MessageDecoder.ts` — разбор служебных сообщений `|s|…`; читают `MailboxDialogsSection`, `MailboxMessage`, `MailboxClanInviteMessage`, `MailboxMessagesSection`.
- `src/views/popups/ConfirmPopup.ts` — общее окно подтверждения, почта не использует (упомянуто для сверки).
- `src/views/home_screen/popups/clan/ClanPopup.ts` — область кланов: кнопка «i» в приглашении.
- `src/plain/user/User.ts` — зависимость: `receiveNotifications`, `onNotificationChangeCall`,
  `onAccountUpdate`, поля `reg`, `banType`, `endBanTime`.
- `src/SceneImpl.ts` — зависимость: приём push `userNotification`.
- `src/types/interfaces.d.ts` — зависимость: `UserSignatureJSON`, `NotificationJSON`.
- `src/views/home_screen/popups/banPanel/BanType.ts` — зависимость: `BanType.MUTE`.
- `src/views/home_screen/popups/settings/ConnectPopup.ts` — вход/регистрация из переписки.
- `src/shared/Users.ts` — зависимость: подпись игрока, цвет по правам.
- `src/utils/TimeUtils.ts` — зависимость: форматы даты и времени сообщений.
- `assets-src/raw/lang/ru/ru.json` — ключи `mailboxScreen.*`; также `chatScreen.registrationReq`,
  `ban.forbidChat`, `common.dateTodayCaps`/`dateYesterdayCaps`, `system.messageInput`, `messageDecoder.clanInvite.*`.
- `assets-src/atlas/community/` — общий с чатом атлас: пузыри, кнопки друзей/ЧС, отправка, конверт.
- `assets-src/atlas/home_screen/btn/mailbox.png` — иконка почты в шапке и профиле.
