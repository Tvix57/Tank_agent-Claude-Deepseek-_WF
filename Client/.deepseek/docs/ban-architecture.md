# Бан-панель и модерация — окна бан-панели, экран блокировки, модерация чата (клиент)

> **auto-create** — документ составлен `client-analyst-lead` по существующему коду, 2026-10-18; актуализирован 2026-10-19
> после merge `origin/amnesia/fix` (см. [#merge-2026-10-19](#merge-2026-10-19)). Запуском не проверялось. Код в рамках задачи не менялся.
> Серверная сторона: `BanPanelPage` и связанные классы в `/workspace/server`, документ —
> `/workspace/server/.claude/docs/ban-architecture.md` (auto-create, 2026-10-18). Сервер упоминается только там, где без него непонятен контракт;
> сверку контракта делает `integration-lead`.

ГДД: [`game-design/ban-gdd.md`](game-design/ban-gdd.md) (из ТЗ «Бан панель.pdf», правила по коду, 2026-10-18). Ссылки `#gdd-…` ниже ведут в него.

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

Область объединяет инструменты модерации и то, что видит наказанный игрок.

Должностное лицо (права `rights >= 100`: модератор 100–199, админ от 200) открывает чужой профиль и
видит кнопку «i». Она запрашивает у сервера `/ingame/banPanel` данные модерации (`ModeratorJSON`) и
открывает окно `PlayerInfoPopup`: ID, последний вход, почта, кнопка «BAN». «BAN» открывает
`BanPanelPopup` — данные игрока, блокировку имени, санкционные кнопки, поля причины и срока, историю
банов (`BanHistoryPanel`). Какие кнопки показать, решает сервер флагами `canBan`/`canBlock`/`canMute`/
`canCancel` ([#gdd-ban-panel](game-design/ban-gdd.md#gdd-ban-panel)).

Наказания: бан (`BAN`, «10 МИНУТ» и «ЗАБАНИТЬ»), тишина (`MUTE`), блок (`BLOCK`), блокировка имени
(`BAD_NAME`, отдельный флаг `isBadName`) ([#gdd-punishments](game-design/ban-gdd.md#gdd-punishments)).
Наказанный игрок узнаёт о наказании из полей аккаунта `banType`/`endBanTime`:
- бан и тишина — поле ввода общего чата заменяется таймером (`GlobalChatSection.showBanData`);
  тишина — ещё и в почте ([mailbox-architecture.md#mute-input](mailbox-architecture.md#mute-input))
  ([#gdd-mute-player](game-design/ban-gdd.md#gdd-mute-player));
- блок — `InGameScene.currentScreenCheck` открывает `BanScreen` вместо главного экрана
  ([#gdd-block-screen](game-design/ban-gdd.md#gdd-block-screen)).

Письмо игроку о бане отправляет сервер; сейчас оно не доходит — отложенный кросс-репо баг,
[mailbox-architecture.md#system-letters](mailbox-architecture.md#system-letters).

Модерация чата: вкладка «МОДЕРАТОРЫ» (`ModeratorChatSection`) видна должностным лицам
([#gdd-moderator-chat](game-design/ban-gdd.md#gdd-moderator-chat)); они же видят крестик удаления у
каждого сообщения ([#gdd-message-delete](game-design/ban-gdd.md#gdd-message-delete)). Ник
должностного лица везде выделен цветом и обводкой
([#gdd-staff-nick-color](game-design/ban-gdd.md#gdd-staff-nick-color)).

<a id="references"></a>
## 2. Референсы

ТЗ «Бан панель.pdf» с «Правками №1» и «Правками №2» (расшифровка передана пользователем 2026-10-18,
содержание — в ГДД). В правках №2 упомянут референс пагинации истории из «Магического мира»
(ссылка на скриншот), в коде не использован.

<a id="patterns"></a>
## 3. Паттерны

- **Окно-флеш**: `FlashLayout` в `GameFlash` с `setParallel(true)`, закрытие по клику на фон
  (`bgClick`), появление `Tweens.c` с блокировкой ввода экрана — у всех трёх окон.
- **Пресеты**: панели `PanelsPresets.PNL_WINDOW_STANDARD`/`PNL_WINDOW_STANDARD_NO_HEADER`, кнопки
  `ButtonPresets.BTN_DEFAULT`/`BTN_GREEN`/`BTN_RED`, выделение кнопки `ButtonPresets.chanceTexture` и
  `updateInteractive`, поля `InputTextPresets.INPUTGenericAlpha`
  ([panels-buttons-presets-architecture.md](panels-buttons-presets-architecture.md)).
- **Подгружаемый блок**: `BanHistoryPanel` и `BanScreen` — `PreloadableLayout`/`ScreenImpl` с
  `onPreload` → запрос → `preloadCompleted`.
- **Секция чата через абстрактный класс**: `ModeratorChatSection` задаёт только маршруты, вся логика —
  в `AbstactChatSection`; push слушается напрямую `App.events.on(EVENT_ROUTE)` (подход 3 из
  [server-push-events-subscription.md](server-push-events-subscription.md#approach-3)).
- **Реакция на изменение аккаунта**: `Globals.account.onAccountUpdate`/`onAccountUpdateCall` —
  перерисовка запрета в чате и смена экрана при блоке.

<a id="class-list"></a>
## 4. Список классов

Задача — документирование, классы не создавались и не менялись. Состав области:

- `PlayerInfoPopup` — окно «i» с кнопкой «BAN».
- `BanPanelPopup` — бан-панель.
- `BanHistoryPanel` — история банов с пагинацией.
- `BanReaskPopup` — подтверждение блокировки имени.
- `BanType` — enum видов наказания.
- Типы `banPanel.d.ts`.
- `BanScreen` — экран заблокированного аккаунта.
- `ModeratorChatSection` — вкладка чата модераторов.
- Точки вне папок: `ProfilePopup` (кнопка «i»), `InGameScene` (переход на `BanScreen`),
  `ObjectCreator` (регистрация экрана), `User` (`banType`/`endBanTime`), `ChatPopup` (вкладка),
  `AbstactChatSection`/`ChatMessage` (удаление сообщений, цвет ника), `GlobalChatSection` (запрет),
  `Users` (права).

<a id="anchors"></a>
## 5. Навигация (якоря)

Классы: [`#cls-player-info`](#cls-player-info), [`#cls-ban-panel`](#cls-ban-panel),
[`#cls-history`](#cls-history), [`#cls-reask`](#cls-reask), [`#types`](#types),
[`#cls-ban-screen`](#cls-ban-screen), [`#cls-moderator-chat`](#cls-moderator-chat),
[`#external`](#external), [`#contract`](#contract), [`#gdd-mapping`](#gdd-mapping), [`#merge-2026-10-19`](#merge-2026-10-19).

Проблемы: [`#history-ban-time`](#history-ban-time), [`#block-mute-send`](#block-mute-send),
[`#locale-keys`](#locale-keys), [`#history-layout`](#history-layout), [`#active-dot`](#active-dot),
[`#find-ip`](#find-ip), [`#screen-check`](#screen-check), [`#nick-color-dup`](#nick-color-dup),
[`#punish-handlers`](#punish-handlers), [`#stale-moder-data`](#stale-moder-data),
[`#ban-screen-reason`](#ban-screen-reason), [`#client-reason`](#client-reason),
[`#server-deferred`](#server-deferred), [`#clan-chat-ban`](#clan-chat-ban), [`#minor`](#minor).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Файл | Раздел |
|---|---|---|
| `PlayerInfoPopup` | `home_screen/popups/banPanel/PlayerInfoPopup.ts` | [#cls-player-info](#cls-player-info) |
| `BanPanelPopup` | `home_screen/popups/banPanel/BanPanelPopup.ts` | [#cls-ban-panel](#cls-ban-panel) |
| `BanHistoryPanel` | `home_screen/popups/banPanel/BanHistoryPanel.ts` | [#cls-history](#cls-history) |
| `BanReaskPopup` | `home_screen/popups/banPanel/BanReaskPopup.ts` | [#cls-reask](#cls-reask) |
| `BanType`, типы | `home_screen/popups/banPanel/BanType.ts`, `banPanel.d.ts` | [#types](#types) |
| `BanScreen` | `ban_screen/BanScreen.ts` | [#cls-ban-screen](#cls-ban-screen) |
| `ModeratorChatSection` | `home_screen/popups/chat/ModeratorChatSection.ts` | [#cls-moderator-chat](#cls-moderator-chat) |
| Точки вне папок | см. раздел | [#external](#external) |

Пути ниже — от `src/views/`, если не указано иное.

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-player-info"></a>
### `PlayerInfoPopup`

Окно «i» ([#gdd-player-info](game-design/ban-gdd.md#gdd-player-info)). Конфиг: `data: UserFullJSON`
(профиль), `moderData: ModeratorJSON` (ответ `/ingame/banPanel`), `onExit`.

- `UIPlayerInfo()` — три строки: `ban.PlayerId` (ID из `data.id`), `ban.lastEnterence`
  (`moderData.info.lastOnlineTime`), `ban.email` (`moderData.info.email` как есть, без прочерка).
- `UIBanButton()` — кнопка «BAN» (спрайт `atlas/home_screen/btn/default_bg.png`, текст захардкожен) →
  `BanPanelPopup.publish` с теми же `data` и `moderData`. Окно «i» при этом не закрывается.
- `publish(screen, config)` — сразу публикует флеш.
- `onCreate`/`onDestroy`/`getAsGameFlash`/`view`/`getText` — каркас окна.

<a id="cls-ban-panel"></a>
### `BanPanelPopup`

Бан-панель ([#gdd-ban-panel](game-design/ban-gdd.md#gdd-ban-panel)). Состояние: `config.moderData`
(перезаписывается после каждого действия), поля `timeLayout`/`reasonLayout`, кнопка `sendButton`,
замыкание `sendRequest` — действие, которое выполнит «ОТПРАВИТЬ».

- `publish(screen, config)` — `loadAssets()` (пакет `RatingScreen` — фон истории, см.
  [#minor](#minor)), затем публикует флеш.
- `UIContent()` — сборка сверху вниз: `UITitle`, `UIPlayerName` (имя `playerName`),
  `UIBlockNameButton` (`blockNameBtn`), `UIPlayerInfoFull`, `UIButtons` (`buttons`), `UIDynamic`,
  `UIBanHistory`.
- `UITitle()` — заголовок `ban.blockNamePage.title` («БЛОКИРОВКА НИКНЕЙМА», шрифт 17); ключ
  `ban.controlPage.info` («Информация») не используется.
- `UIPlayerName()` — ник `moderData.info.user.name`; цвет и обводка по правам
  ([#gdd-staff-nick-color](game-design/ban-gdd.md#gdd-staff-nick-color), [#nick-color-dup](#nick-color-dup)).
- `UIBlockNameButton()` — [#gdd-name-block](game-design/ban-gdd.md#gdd-name-block). По `isBadName`
  выбирает маршрут `/ingame/banPanel/dropName` или `/undropName` и текст кнопки. Блокировка — через
  `BanReaskPopup`, разблокировка — сразу. Причину формирует сам клиент:
  `ban.blockNamePage.reasonNameBlock` с текущим ником ([#client-reason](#client-reason)). После ответа
  `updateModerData()` и замена `playerName`/`blockNameBtn`.
- `UIPlayerInfoFull()` — регистрация, последний вход, `IP:`, `UA:` (шрифт 8).
- `UIButtons()` — [#gdd-punishments](game-design/ban-gdd.md#gdd-punishments),
  [#gdd-cancel](game-design/ban-gdd.md#gdd-cancel). Сетка в 3 колонки. `canCancel` → только
  `UICancelButton`; иначе по флагам: `canBan` → «ЗАБАНИТЬ» и «10 МИНУТ», `canBlock` → «БЛОК»,
  `canMute` → «ТИШИНА». Всегда «НАЙТИ IP» и `sendButton`. Пересоздаётся после каждого действия.
- `UIDynamic()`, `UISetTime()`, `UISetReason()` — поля срока (фильтр «только цифры»,
  `maxLength: 255`) и причины (`maxLength: 255`); `onSubmit` обоих — `OnBtnSendMessage`.
- `UISendButton()` — зелёная «ОТПРАВИТЬ» → `OnBtnSendMessage`.
- `OnBtnSendMessage()` — проверка: видимое пустое поле — выход без сообщения; иначе `sendRequest()`.
- `Set10MinuteButton()` — `/ingame/banPanel/ban` с `hours: 0.16666666666`, поля: только причина.
- `SetBanButton()` — `/ingame/banPanel/ban` с `hours` из поля, поля: срок и причина.
- `SetBlockButton()` — `/ingame/banPanel/block`, поля: только причина.
- `SetMuteButton()` — `/ingame/banPanel/mute` с `hours`, поля: срок и причина.
  Четыре метода построены одинаково: `activeButtonsTextures` → `showEditRow` → новое `sendRequest`;
  после ответа `dropPanelState` → `updateModerData` → замена `buttons`
  ([#punish-handlers](#punish-handlers)). Ошибка запроса — только `console.warn`.
- `SetFindIpButton()` — [#find-ip](#find-ip).
- `UICancelButton()` — `/ingame/banPanel/cancel`, без полей и подтверждения, затем
  `updateModerData` и замена `buttons`.
- `showEditRow(showTime, showReason)` — видимость полей и `sendButton`.
- `activeButtonsTextures(btn)` — сбрасывает выделение у всех кнопок сетки, выделяет и блокирует
  нажатую.
- `dropPanelState()` — очищает поля, скрывает их, сбрасывает `sendRequest`.
- `updateModerData()` — сначала `history.updateCurrentPage()`, затем `/ingame/banPanel` →
  `config.moderData` ([#stale-moder-data](#stale-moder-data)). Ошибка проглатывается, промис всё равно
  разрешается.
- `getButtonPresetOption`, `getText`, `getAsGameFlash`, `view`, `onCreate`/`onDestroy` — каркас.

<a id="cls-history"></a>
### `BanHistoryPanel`

История банов ([#gdd-history](game-design/ban-gdd.md#gdd-history)). `PreloadableLayout` 350×325 с
фоном `atlas/rating_screen/tablet-ratings.png`. Получает тот же `BanPanelPopupConfig`, что и панель
(общая ссылка: `moderData` читается актуальная).

- `onPreload()` — `/ingame/banPanel/history` `{ userId, page }` → `data: BanJouranlJSON`.
- `onCreate()` — список и `AdvancedPaginator`: «в начало» — страница 1, «в конец» —
  `MAX_PAGE_TEMPLATE`, «вперёд»/«назад» — ±5 страниц, номер — эта страница.
- `updateCurrentPage()` — перезапрос текущей страницы через `numberedButton`.
- `BTNPaginator(page)` — запрос страницы и `updateData()`; ошибка — `console.warn`.
- `updateData()` — пересоздаёт список, берёт `page` из ответа, обновляет пагинатор по `maxPage`.
- `UIList()` — `ScrollableArea` со строками в порядке ответа сервера.
- `UILine(data)` — строка 325×60 (фон `bg-entry.png`): `UIBanLine`, при `cancel` — `UICancelLine`,
  причина `ban.reason` (шрифт 11) с переносом по 300 px; отступы 3 px сверху и снизу
  ([#history-layout](#history-layout)).
- `UIBanLine(data)` — заголовок по `type` (`ban.history.banner`/`mute`/`badName`/`block`), иконка
  уровня (`Layout` 15×15 со спрайтом и числом), ник наложившего (админ — зелёный, иначе жёлтый), дата `startTime`, срок
  `endTime - startTime` при наличии `endTime` ([#history-ban-time](#history-ban-time)), зелёная точка
  при `isPunishActive`.
- `UICancelLine(data)` — «Снял:», уровень, ник, дата `cancel.time`. Число в иконке уровня берётся из
  `data.banner.level`, а не `data.cancel.user.level` ([#minor](#minor)).
- `isPunishActive(data)` — нет `cancel` и (`endTime > now` или, без `endTime`, текущий
  `moderData.info.banType !== NONE`) ([#active-dot](#active-dot)).

<a id="cls-reask"></a>
### `BanReaskPopup`

Подтверждение блокировки имени ([#gdd-name-block](game-design/ban-gdd.md#gdd-name-block)).
`publish(screen, onConfirm)`. Заголовок `ban.blockNamePage.title`, вопрос `ban.blockNamePage.ask`,
кнопки `BTN_RED` «НЕТ, ОТМЕНА» (закрыть) и `BTN_GREEN` «ДА, ПРОДОЛЖИТЬ» (`onConfirm()` и закрыть).
Имя `FlashLayout` — `"PlayerInfoPopup"` (скопировано, [#minor](#minor)).

<a id="types"></a>
### `BanType` и `banPanel.d.ts`

- `BanType`: `NONE`, `BAN`, `MUTE`, `BLOCK`, `BAD_NAME`. `BAD_NAME` встречается только в записях
  истории; у аккаунта блокировка имени — флаг `isBadName`.
- `ModeratorJSON` — `canBan`, `canBlock`, `canCancel`, `canMute`, `info: ForModerInfoJSON`.
- `ForModerInfoJSON` — `user: UserSignatureJSON`, `banTime`, `banType`, `creationTime`, `ip`,
  `email`, `isBadName`, `lastOnlineTime`, `userAgent`. `banTime` клиентом не читается.
- `BanJouranlJSON` — `history: [BanHistoryJSON]` (записано как кортеж из одного элемента, по смыслу
  массив), `maxPage`, `page`.
- `BanHistoryJSON` — `banner: UserBasicJSON`, `cancel?: BanCancelJSON`, `startTime`, `endTime?`,
  `reason`, `type`.
- `BanCancelJSON` — `user: UserBasicJSON`, `time`.

<a id="cls-ban-screen"></a>
### `BanScreen`

Экран заблокированного аккаунта ([#gdd-block-screen](game-design/ban-gdd.md#gdd-block-screen)).
`ScreenImpl`, регистрируется в `ObjectCreator` под именем `"BanScreen"` (`ObjectCreator.banScreen()`).

- `onPreload()` — `/ingame/account/banInfo`; при `ResultUtils.isOk` берёт `response.info.reason`
  (ответ типизирован как `any`). Ошибка — экран всё равно открывается с пустой причиной
  ([#ban-screen-reason](#ban-screen-reason)).
- `onStart()` — `headerFooterShow = false`.
- `UIBanLayout()` — фон: чёрная заливка `Creator.spriteWhite().setTint(Const.COLOR_BLACK)` (раньше спрайт
  `atlas/home_screen/back.png`), тексты `ban.blockPage` и `ban.reason`.

<a id="cls-moderator-chat"></a>
### `ModeratorChatSection`

Вкладка чата модераторов ([#gdd-moderator-chat](game-design/ban-gdd.md#gdd-moderator-chat)).
`TAB_NAME = "moderator"`; маршруты `/ingame/moderator/chat/send`, `/deleteMessage`, `/subscribe`,
`/unsubscribe`; push `g/ws/events/moderator/chat`. Своей логики нет, всё — в `AbstactChatSection`.
Вкладку прячет только клиент, сервер подписку не проверяет ([#server-deferred](#server-deferred)).
Запрета на общение здесь нет: `showBanData` есть только в `GlobalChatSection`
([ban-gdd.md О5](game-design/ban-gdd.md#gdd-open)).

<a id="external"></a>
### Точки вне папок

- `home_screen/popups/profile/ProfilePopup.ts` — `UIMain` добавляет кнопку «i» (`UIInfoPanel`),
  если `Users.isSuperUser(Globals.account.rights) && !Users.isAdmin(this.data.user.rights)`; условие
  не исключает собственный профиль. `UIMain` профиля при открытии вызывает `screen.pushHeaderZIndex(false)`,
  `onDestroy` — `popHeaderZIndex()`; запросы клана и «пригласить в клан» в профиле — зона кланов, здесь не
  описаны. `UIInfoPanel()` — `/ingame/banPanel` `{ targetUserId }` →
  `PlayerInfoPopup.publish` ([#gdd-player-info](game-design/ban-gdd.md#gdd-player-info)).
- `src/scenes/InGameScene.ts` — `currentScreenCheck()`: при `banType === BLOCK` открывает
  `BanScreen`, иначе главный экран. Вызывается после загрузки сумки и на каждое `g/account/update`
  (`onAccountUpdateCall` — ещё и сразу при создании сцены); `handleUserUpdate` пропускает вызов, пока
  `Globals.bag.isInitialized()` ложно, поэтому до загрузки сумки экран не меняется ([#screen-check](#screen-check)).
  Данные аккаунта обновляются по уведомлению `accountRefresh` → `/ingame/account` →
  `Globals.account.refresh`.
- `src/plain/user/User.ts` — поля `banType: BanType` и `endBanTime` (мс), заполняются
  `ObjectUtils.classBuild` из данных аккаунта (в этом же классе появились `clanId` и событие
  `g/account/tutorial/update` — не область бана); `UserBasicJSON` в `src/types/interfaces.d.ts` несёт те
  же поля.
- `home_screen/popups/chat/GlobalChatSection.ts` — `showBanData()`: при `BAN` или `MUTE` скрывает
  поле, кнопку отправки и показывает `ban.forbidChat` с таймером `endBanTime - now`, по истечении
  возвращает поле. Перезапускается на `onAccountUpdate`
  ([#gdd-mute-player](game-design/ban-gdd.md#gdd-mute-player)). Почта — только при `MUTE`,
  [mailbox-architecture.md#mute-input](mailbox-architecture.md#mute-input).
- `home_screen/popups/chat/ChatPopup.ts` — вкладка `tab2` («МОДЕРАТОРЫ») при
  `Users.isSuperUser(Globals.account.rights)`; после неё вкладка клана `tab1` при `Globals.account.clanId !== ""`
  ([#clan-chat-ban](#clan-chat-ban)). Флеш окна получил имя `"ChatPopup"`.
- `home_screen/popups/chat/AbstractChatSection.ts` — `addMessage` передаёт в `ChatMessage`
  `canDelete: Users.isSuperUser(...)`; `BtnDeleteMessage(id)` шлёт `DELETE_MESSAGE_ROUTE`; удаление
  приходит push-сообщением с `delId` → `updateData` убирает сообщение
  ([#gdd-message-delete](game-design/ban-gdd.md#gdd-message-delete)). `ClanChatSection` (новая, не
  наследует `AbstactChatSection`) использует тот же `ChatMessage`, но `canDelete: isLeader()`
  ([#clan-chat-ban](#clan-chat-ban)).
- `home_screen/popups/chat/ChatMessage.ts` — крестик `atlas/ui/icons/close.png` в общем `Layout` `hl`
  (25 px, отступ 2) с иконкой ответа (она 25×25, только у чужих сообщений), в правом верхнем углу пузыря; цвет ника по правам, обводка 1 у должностных лиц.
- `src/shared/Users.ts` — `isAdmin` (`>= 200`), `isModerator` (`100..199`), `isSuperUser` (`>= 100`);
  `getDisplayName` показывает «Fighter» как `system.noviceName`.
- Цвет ника (`COLOR_YELLOW` `#ffd900` / `COLOR_GREEN` `#7CA431`) также в `HeaderProfile`,
  `ProfileSection`, пяти секциях рейтинга, `MailboxMessagesSection` и четырёх окнах почты
  ([#nick-color-dup](#nick-color-dup)).

<a id="contract"></a>
### Контракт с сервером

| Маршрут | Запрос | Ответ / использование |
|---|---|---|
| `/ingame/banPanel` | `{ targetUserId }` | `ModeratorJSON` |
| `/ingame/banPanel/ban` | `{ userId, hours, reason }` | только факт успеха |
| `/ingame/banPanel/mute` | `{ userId, hours, reason }` | только факт успеха |
| `/ingame/banPanel/block` | `{ userId, reason }` | только факт успеха |
| `/ingame/banPanel/cancel` | `{ userId }` | только факт успеха |
| `/ingame/banPanel/dropName`, `/undropName` | `{ userId, reason }` | только факт успеха |
| `/ingame/banPanel/findIp` | `{ ip, page: 0 }` | только `console.warn` |
| `/ingame/banPanel/history` | `{ userId, page }` | `BanJouranlJSON` |
| `/ingame/account/banInfo` | `{}` | `{ info: { reason } }` при OK |
| `/ingame/moderator/chat/*` | как у общего чата | `ChatMessagesJSON`, push `g/ws/events/moderator/chat` |
| поля аккаунта | — | `banType`, `endBanTime` (мс) |

`hours` — дробное число часов; `userId` — `moderData.info.user.id` (в `/ingame/banPanel` уходит
`data.id` профиля). Время — миллисекунды. Что сервер возвращает при отказе и как считает
`endTime` в истории — вопрос для `integration-lead` ([#history-ban-time](#history-ban-time),
[#block-mute-send](#block-mute-send)).

<a id="gdd-mapping"></a>
### Сопоставление функций с ГДД ([`#gdd-function-mapping`](agent-system-workflow.md#gdd-function-mapping))

| Правило ГДД | Функции | Находка |
|---|---|---|
| [#gdd-player-info](game-design/ban-gdd.md#gdd-player-info) | `ProfilePopup.UIInfoPanel`, `PlayerInfoPopup.UIPlayerInfo`/`UIBanButton` | — |
| [#gdd-ban-panel](game-design/ban-gdd.md#gdd-ban-panel) | `UIContent`, `UIButtons`, `showEditRow`, `OnBtnSendMessage` | — |
| [#gdd-name-block](game-design/ban-gdd.md#gdd-name-block) | `UIBlockNameButton`, `BanReaskPopup` | причина собирается на клиенте ([#client-reason](#client-reason)) |
| [#gdd-punishments](game-design/ban-gdd.md#gdd-punishments) | `Set10MinuteButton`, `SetBanButton`, `SetBlockButton`, `SetMuteButton` | четыре копии одного перехода ([#punish-handlers](#punish-handlers)); «10 минут» и «Забанить» — одно правило (бан), две функции, отличается только `hours` |
| [#gdd-cancel](game-design/ban-gdd.md#gdd-cancel) | `UICancelButton` | — |
| [#gdd-history](game-design/ban-gdd.md#gdd-history) | `BanHistoryPanel.*` | [#history-ban-time](#history-ban-time), [#active-dot](#active-dot), [#history-layout](#history-layout) |
| [#gdd-mute-player](game-design/ban-gdd.md#gdd-mute-player) | `GlobalChatSection.showBanData`, `MailboxMessagesSection.showBanData` | проверка «запрещено ли общение» записана в двух местах с разными условиями (по ГДД так и должно быть: бан — только чат) |
| [#gdd-block-screen](game-design/ban-gdd.md#gdd-block-screen) | `InGameScene.currentScreenCheck`, `BanScreen` | [#screen-check](#screen-check) |
| [#gdd-moderator-chat](game-design/ban-gdd.md#gdd-moderator-chat) | `ChatPopup.UIMain`, `ModeratorChatSection` | — |
| [#gdd-message-delete](game-design/ban-gdd.md#gdd-message-delete) | `AbstactChatSection.addMessage`/`BtnDeleteMessage`/`updateData`, `ChatMessage.UIMessage` | — |
| [#gdd-staff-nick-color](game-design/ban-gdd.md#gdd-staff-nick-color) | ~20 копий выбора цвета, `Users.getDisplayNameColor` | одно правило в 14 файлах, а функция `getDisplayNameColor` права не учитывает ([#nick-color-dup](#nick-color-dup)) |

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Пункты 1–4 — ошибки из «Правок №1/№2» тестировщика; их статус по текущему коду указан в каждом.

<a id="history-ban-time"></a>
### 1. Срок в истории в ~1000 раз больше настоящего

Правки №1: бан на 1 час в истории показан как «41д 15ч», у игрока таймер верный. 1 час × 1000 =
41 день 16 часов — разница ровно в тысячу раз. Клиент считает срок как `endTime - startTime` в мс
(`UIBanLine`), а таймер игрока — от `endBanTime` аккаунта. Серверный анализ считает `startTime`/
`endTime` истории корректными (`/workspace/server/.claude/docs/ban-architecture.md#tradeoffs` п.7), клиентский код тоже не умножает и не делит.
Обе стороны по коду выглядят верно — источник ищет `integration-lead` (единицы полей в ответе
`/history`, `timeDDHHMMSS_Mls`).

**Сверка integration-lead 2026-10-18:** обе стороны в миллисекундах: сервер `BanPanelPage:230` (`now + round(hours·3600000)`), `BanHistoryEntry:113-116`; клиент `BanHistoryPanel:159` → `timeDDHHMMSS_Mls` делит на 1000 (`TimeUtils:32`). ×1000 по коду не найден; первопричины на стороне client/server нет. Не проверено запуском: что именно лежит в БД у записи тестера и какое `hours` отправлено (`BanPanelPopup:356` — `Number(timeLayout.value)`, без ограничения единицы).

<a id="block-mute-send"></a>
### 2. «Блок» и «Тишина» не применяются

Правки №1 и №2: «ОТПРАВИТЬ» не реагирует, в консоли `Uncaught (in promise) Object`. Причина —
на сервере: `/mute` и `/block` требуют прав админа, модератору приходит `error`
(`/workspace/server/.claude/docs/ban-architecture.md#tradeoffs` п.2). Кто должен накладывать «ТИШИНУ» и «БЛОК», пользователь отложил
([ban-gdd.md О3](game-design/ban-gdd.md#gdd-open)).

Клиентская часть: кнопки «БЛОК»/«ТИШИНА» показываются только при `canBlock`/`canMute`, поэтому
модератор, у которого они видны, получил от `/ingame/banPanel` `true` при серверном отказе в самом
действии — расхождение флагов с проверкой роута проверяет `integration-lead`. Ошибка запроса
перехватывается (`.catch` → `console.warn`), модератор ничего не видит.

**Сверка integration-lead 2026-10-18:** сервер считает `canBlock`/`canMute` как `isAdmin(requester)` (`BanPanelPage:95-106`, `BanActions`), т.е. для модератора `false`, проверка роутов `/mute`, `/block` (`:238`, `:257`) та же. Расхождения флагов нет; клиент рисует кнопки по флагам (`BanPanelPopup:206-211`). Как модератор увидел кнопки — по коду не воспроизводится (кандидаты: учётка тестера была админом на момент открытия панели; сборка клиента/сервера старше текущего кода — единственный коммит `dc49854`).

<a id="locale-keys"></a>
### 3. Ключи локализации вместо текста

Правки №1/№2 показывали `ban.ForbidToCommicate` и `ban.reasonNameBlock`. В текущем коде их нет: чат
берёт `ban.forbidChat`, причина блокировки имени — `ban.blockNamePage.reasonNameBlock`, оба есть в
`ru.json`. Похоже, исправлено после правок; запуском не проверено. Остаётся: раздела `ban` нет в
`en.json`, английский клиент покажет ключи. В `ru.json` не используются `ban.controlPage.info` и
`ban.dialogPage`. Старые записи истории, сохранённые с причиной-ключом, так и останутся.

<a id="history-layout"></a>
### 4. Длинная причина ломает вёрстку истории

Правки №2. Строка `UILine` фиксированной высоты 60, причина переносится по 300 px и вылезает на
соседние строки. После merge шрифт причины уменьшен 13→11, добавлены отступы по 3 px — длинная причина
по-прежнему не помещается. Скролл (`ScrollableArea`) есть, но высота области не учитывает пагинатор, и он
ложится поверх нижних строк. Не исправлено.

<a id="active-dot"></a>
### 5. Зелёная точка у старых записей без срока

`isPunishActive`: запись без `endTime` (блок, блокировка имени) считается активной, если у игрока
сейчас любое наказание (`banType !== NONE`). Старый снятый блок без `cancel`, старая блокировка имени
или блок при активной тишине получат точку. Активность блокировки имени (`isBadName`) не проверяется.

<a id="find-ip"></a>
### 6. «НАЙТИ IP» ничего не делает

`SetFindIpButton` вызывает `showEditRow(false, false)` — «ОТПРАВИТЬ» скрывается, и назначенный
`sendRequest` запустить нечем. Даже при вызове ответ `/findIp` только пишется в консоль, а у промиса
нет `.catch`. Серверный `/findIp` тоже неисправен (`/workspace/server/.claude/docs/ban-architecture.md#tradeoffs` п.5). Что кнопка должна показывать, ГДД не описывает ([ban-gdd.md О2](game-design/ban-gdd.md#gdd-open)).

<a id="screen-check"></a>
### 7. Условие смены экрана в `InGameScene` всегда истинно

`if (currentScreen?.name ?? "" !== newScreen.name)` разбирается как
`currentScreen?.name ?? ("" !== newScreen.name)`: `??` слабее `!==`. При любом открытом экране
условие истинно, и на каждое `g/account/update` вызывается `openScreen` главного (или бан-) экрана.
Повтор того же экрана гасит `Scene.openScreen` (сравнение по имени). Но если открыт другой экран
(например, `BattlefieldScreen`), обновление аккаунта по коду переключит игрока на главный. Касается
не только бана — при правке сверить с владельцами экранов. После merge `handleUserUpdate`
дополнительно отсекает вызов до инициализации сумки; условие самого сравнения не менялось.

<a id="nick-color-dup"></a>
### 8. Правило цвета ника записано около 20 раз

Выбор «админ — `COLOR_GREEN`, модератор — `COLOR_YELLOW`, иначе свой цвет» и обводка
`isSuperUser ? 1 : 0` повторены в `ChatMessage`, `BanPanelPopup`, `BanHistoryPanel` (там «не админ —
жёлтый»), `HeaderProfile`, `ProfileSection`, пяти `Rating*Section` (по три места в каждой),
`MailboxMessagesSection` и четырёх окнах почты. `Users.getDisplayNameColor` существует, но возвращает
`config.color` или `#fff` без учёта прав. По [#gdd-function-mapping](agent-system-workflow.md#gdd-function-mapping) —
кандидат свести правило в `Users` (одна функция цвета и обводки по правам). Обводки нет только в
`HeaderProfile` — отражено в ГДД как решение «как в коде».

<a id="punish-handlers"></a>
### 9. Четыре копии перехода «выбрать наказание» с неявным порядком шагов

`Set10MinuteButton`/`SetBanButton`/`SetBlockButton`/`SetMuteButton` каждый сам выполняет
последовательность: `activeButtonsTextures` → `showEditRow` → присвоить `sendRequest` → после ответа
`dropPanelState` → `updateModerData` → `replaceByName("buttons")` через `btn.parentLayout.parentLayout`.
Порядок держится на вызывающем ([#no-implicit-order](agent-system-workflow.md#no-implicit-order)).
Кандидат: один метод-переход «выбрать наказание (вид, маршрут, поля)» и один «применить результат».

<a id="stale-moder-data"></a>
### 10. История обновляется по старым данным модерации

`updateModerData()` перезапрашивает историю до ответа `/ingame/banPanel`, а `isPunishActive` читает
`moderData.info.banType` — точки строятся по прежнему состоянию. Ошибка `/ingame/banPanel`
проглатывается, и вызывающий перерисовывает кнопки по старым данным.

<a id="ban-screen-reason"></a>
### 11. Экран блокировки без причины при ошибке

`BanScreen.onPreload` при ошибке или не-OK ответе открывает экран с «Причина: » без текста. Ответ
`/banInfo` типизирован как `any`.

<a id="client-reason"></a>
### 12. Причину блокировки имени формирует клиент модератора

Текст «Блокировка ника "<ник>"» переводится на языке модератора и уходит строкой `reason`. Игрок
другого языка увидит русскую причину; сервер принимает любую строку от клиента. Где формировать
причину (клиент или сервер), пользователь отложил — `/workspace/server/.claude/docs/ban-architecture.md#tradeoffs` п.6.

<a id="server-deferred"></a>
### 13. Отложенные серверные пункты, влияющие на клиент

Решение пользователя 2026-10-18 — отложено; подробности только в серверном документе
`/workspace/server/.claude/docs/ban-architecture.md#tradeoffs`:
- п.1 — наказания проверяет только клиент (`showBanData`, `currentScreenCheck`); сервер не
  запрещает отправку сообщений при бане/тишине и действия при блоке;
- п.3 — подписку на модераторский чат сервер не проверяет; клиент лишь прячет вкладку
  (`ChatPopup.UIMain`);
- п.6 — кто формирует причину блокировки ника ([#client-reason](#client-reason)).

<a id="clan-chat-ban"></a>
### 14. Запрет на общение не распространяется на чат клана

Новая вкладка «КЛАН» (`ClanChatSection`, `TAB_NAME = "clan"`, маршруты `/ingame/clanChat/*`, push
`g/ws/events/clanChat`) не вызывает `showBanData`: забаненный или «в тишине» игрок видит поле ввода и
может писать. Крестик удаления показывается при `isLeader()` (флаг из ответа `subscribe`), а не по
`isSuperUser`, — модератор сообщения клана не удаляет. ГДД про клановый чат ничего не говорит (аналог открытого вопроса
[ban-gdd.md О5](game-design/ban-gdd.md#gdd-open) для чата модераторов). Сам чат клана —
зона кланов, не документируется здесь.

<a id="minor"></a>
### 15. Мелочи

- `BanPanelPopup.loadAssets` грузит пакет `RatingScreen` ради фона истории; ошибка загрузки не
  обрабатывается. Иконки `atlas/profile_screen/level.png` и `atlas/ui/icons/dot_green.png` берутся из
  пакетов, загруженных другими экранами.
- `BanReaskPopup` назван `FlashLayout("PlayerInfoPopup")` — копия.
- Пагинатор истории: «вперёд»/«назад» — на 5 страниц, не на одну.
- Срок «0» часов проходит проверку `OnBtnSendMessage` ([ban-gdd.md О4](game-design/ban-gdd.md#gdd-open)).
- `ChatPopup.onCreate` с `tab: "moderator"` показал бы общую секцию при активной вкладке модераторов;
  сейчас окно открывается только с `global` (`HomeScreen`).
- `ForModerInfoJSON.banTime` не читается; `BanJouranlJSON` — опечатка в имени, `history` объявлен
  кортежем.
- Кнопка «i» видна и на собственном профиле должностного лица.
- `BanReaskPopup` получил `// @TODO: сделать более красивое окно` над классом.

<a id="merge-2026-10-19"></a>
## Изменения после merge origin/amnesia/fix (2026-10-19)

Логика бана не менялась. Правки визуальные: размеры шрифтов кнопок и текстов бан-панели и `BanReaskPopup`
12→9 без `setShrink`, заголовок бан-панели вручную (шрифт 17), иконка уровня в истории — `Layout` 15×15,
фон `BanScreen` — чёрная заливка, крестик и иконка ответа в `ChatMessage` в одном `Layout` `hl`.
Добавлена вкладка клана в `ChatPopup` ([#clan-chat-ban](#clan-chat-ban)); в `InGameScene.handleUserUpdate`
добавлена проверка инициализации сумки ([#screen-check](#screen-check)). Состояние tsc: ошибки автора fix
(`HomeScreenAerodrome.ts`, `battlefield.d.ts`, `GameEvents`) к области бана не относятся.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД — [`game-design/ban-gdd.md`](game-design/ban-gdd.md); соответствие разделов и функций — в
[#gdd-mapping](#gdd-mapping). Расхождения ТЗ с кодом, принятые «как в коде», — в
[журнале ГДД](game-design/ban-gdd.md#gdd-log). Письмо о бане — `mailbox-gdd.md#gdd-open` О4.

<a id="file-map"></a>
## 10. Карта файлов компонента

<a id="file-map-direct"></a>
### Файлы прямого влияния

- `src/views/home_screen/popups/banPanel/PlayerInfoPopup.ts` — окно «i».
- `src/views/home_screen/popups/banPanel/BanPanelPopup.ts` — бан-панель.
- `src/views/home_screen/popups/banPanel/BanHistoryPanel.ts` — история банов.
- `src/views/home_screen/popups/banPanel/BanReaskPopup.ts` — подтверждение блокировки имени.
- `src/views/home_screen/popups/banPanel/BanType.ts` — виды наказаний.
- `src/views/home_screen/popups/banPanel/banPanel.d.ts` — типы ответов бан-панели.
- `src/views/ban_screen/BanScreen.ts` — экран заблокированного аккаунта.
- `src/views/home_screen/popups/chat/ModeratorChatSection.ts` — чат модераторов.

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

- `src/views/home_screen/popups/profile/ProfilePopup.ts` — кнопка «i» и запрос `/ingame/banPanel`.
- `src/scenes/InGameScene.ts` — переход на `BanScreen` при блоке.
- `src/views/ObjectCreator.ts` — регистрация экрана `"BanScreen"`.
- `src/plain/user/User.ts` — поля аккаунта `banType`/`endBanTime`.
- `src/types/interfaces.d.ts` — `UserBasicJSON.banType`/`endBanTime`.
- `src/views/home_screen/popups/chat/ChatPopup.ts` — видимость вкладки «МОДЕРАТОРЫ».
- `src/views/home_screen/popups/chat/AbstractChatSection.ts` — право удаления, удаление по `delId`.
- `src/views/home_screen/popups/chat/ChatMessage.ts` — крестик удаления, цвет ника.
- `src/views/home_screen/popups/chat/GlobalChatSection.ts` — запрет на общение в общем чате.
- `src/views/home_screen/popups/chat/ClanChatSection.ts` — чат клана (без запрета на общение, права удаления у лидера; не область бана, [#clan-chat-ban](#clan-chat-ban)).
- `src/views/home_screen/popups/mailbox/MailboxMessagesSection.ts` — запрет на общение в почте и цвет
  ника (описано в `mailbox-architecture.md`).
- `src/shared/header/presets/HeaderProfile.ts` — цвет своего ника в шапке.
- `src/views/home_screen/popups/profile/ProfileSection.ts` — цвет ника в профиле.
- `src/views/home_screen/popups/rating/RatingPowerSection.ts`, `RatingCampaignSection.ts`,
  `RatingTanksSection.ts`, `RatingAirplanesSection.ts`, `RatingBattlefieldSection.ts` — цвет ника в
  рейтингах.
- `src/views/home_screen/popups/mailbox/popups/AddToFriendsPopup.ts`, `DeleteFromFriendsPopup.ts`,
  `AddToBlacklistPopup.ts`, `DeleteFromBlacklistPopup.ts` — цвет ника в окнах почты.
- `assets-src/raw/lang/ru/ru.json` — ключи `ban.*`, `chatScreen.tab2`.
- `src/shared/Users.ts` — зависимость: `isAdmin`/`isModerator`/`isSuperUser`, `getDisplayName`.
- `src/views/home_screen/popups/chat/chat.d.ts` — зависимость: `ChatMessageJSON`, `ChatMessagesJSON`.
- `src/shared/paginators/AdvancedPaginator.ts` — зависимость: пагинатор истории.
- `src/utils/TimeUtils.ts` — зависимость: `dateHMToString`, `timeDDHHMMSS_Mls`.
- `src/presets/ButtonPresets.ts`, `PanelsPresets.ts`, `InputTextPresets.ts` — зависимость: кнопки,
  панели, поля ввода.
