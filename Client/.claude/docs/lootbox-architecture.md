# Лутбоксы (client)

ГДД: [lootbox-gdd.md](game-design/lootbox-gdd.md). Серверная сторона и контракт маршрутов:
`/workspace/server/.claude/docs/lootbox-architecture.md` (здесь не дублируются).
Статус: обычный — разработка по ГДД, ветка koba/lootbox, правки ревью 2026-11-04 (не закоммичено).

**Содержание:** [Описание](#overview) · [Референсы и паттерны](#patterns) · [Классы](#classes) ·
[Потоки](#flows) · [Данные](#data) · [Компромиссы](#tradeoffs) · [Заглушки ассетов](#stubs) · [Карта файлов](#file-map)

## Описание {#overview}
Сундуки 10 качеств (ранги I–X) в окне «Трофеи» (`IdlePopup`): сетка сундуков из сумки, ячейка
открытия с таймером, подтверждение постановки, ускорение (серебро, нехватка — золото), показ награды
и её полёт в хедер; показ сундука, полученного за задание. Таймер и цену считает сервер, клиент
показывает остаток и цену по ответам. Лутбокс — стакуемый предмет сумки (`ItemType.LOOTBOX = 7`,
`id` = качество), счётчики берутся из кэша `UserBag`.

## Референсы и паттерны {#patterns}
- [client-ui-patterns.md#fly-to-target](client-ui-patterns.md#fly-to-target), [reward-flight-utils-architecture.md](reward-flight-utils-architecture.md) — `RewardFlightUtils`.
- [client-ui-patterns.md#reward-type-registry](client-ui-patterns.md#reward-type-registry) — `ItemsPresets.createImageLayout`.
- [client-ui-patterns.md#timer-speedup](client-ui-patterns.md#timer-speedup) — ячейка и попап ускорения.
- [popup-queue-pattern.md](popup-queue-pattern.md) — очередь `LootboxReceivedPopup`.
- Референс анимации: `TrainCollectionItemPopup` (ветка koba/collection).
- Сумка: [bag-architecture.md](bag-architecture.md); отрисовка `BagItem`: [items-presets-architecture.md](items-presets-architecture.md).

## Классы {#classes}
[LootboxState](#user-lootbox) · [LootboxIdleSection](#lootbox-idle-section) · [Попапы](#popups) ·
[LootboxReceivedPopup](#received-queue) · [LootboxUtils](#utils) · [RewardFlightUtils](#reward-flight) ·
[IdlePopup](#trophies-take) · [Остальные изменения](#other-changes)

### LootboxState {#user-lootbox}
`src/views/home_screen/popups/lootbox/LootboxState.ts`, модуль-синглтон `export default new class LootboxState` (как `MilitaryBaseState`, не поле `Globals`). Кэш `/info` на время жизни главного экрана, запросы маршрутов, таймер значка.
- `requestInfo()` — кэшированный `/info`: параллельные вызовы получают один и тот же промис (`infoRequest`), отказ снимает его в `finally`, кэш остаётся пустым и следующий вызов повторяет запрос. Ответ, пришедший после `reset()`, кэш не заполняет — защита счётчиком `infoVersion`. `getQuality(quality)`, `getBagCount(quality)` (из `Globals.bag`), `getQualitiesInBag()` — только качества с count > 0. ГДД: [#gdd-trophies-window](game-design/lootbox-gdd.md#gdd-trophies-window).
- <a id="state-reset"></a>`reset()` `#state-reset` — сброс при уничтожении главного экрана (`IdleBtn.onDestroy`), в т.ч. при logout и переходе на экран бана, одним методом владельца: `stopReadyTimer()`, `info = null`, `infoRequest = null`, `infoVersion++`, `LootboxReceivedPopup.clearQueue()`; идемпотентен. `LootboxState` импортирует `Globals` (сумка), обратного импорта из `Globals` нет. Цикл `LootboxState`↔`LootboxReceivedPopup` безопасен: при загрузке модулей стороны друг к другу не обращаются.
- `requestLootbox()`, `startOpen(quality)` (шлёт `{ quality }`), `open(slot)`, `speedup(slot, price)` (шлёт `{ slot, price }`, `price: LootboxPriceJSON`), `requestSpeedupPrice(slot)` (одна ячейка, для попапа ускорения), `requestSpeedupPrices()` (`{prices:[...]}` — снимок всех ячеек, для секции) — обёртки маршрутов `/ingame/lootbox/*`; `requestLootbox`/`startOpen` возвращают `LootboxResponseJSON`. Проверка `ResultUtils.isOk` — внутри обёрток `requestInfo`/`requestLootbox`/`requestSpeedupPrice`/`requestSpeedupPrices`: отказ отклоняет промис телом ответа. Вызывающий разбирает его в `catch` по признаку `lootbox` (отказ сервера несёт свежее состояние, сетевая ошибка — нет, у неё `errCode`). Ответы `/startOpen`/`/open`/`/speedup` переставляют таймер значка (`restartReadyTimer`). ГДД: [#gdd-open-slot](game-design/lootbox-gdd.md#gdd-open-slot), [#gdd-speedup](game-design/lootbox-gdd.md#gdd-speedup), [#gdd-claim](game-design/lootbox-gdd.md#gdd-claim).
- <a id="ready-timer"></a>**Таймер значка** `#ready-timer`: `checkReady()` запрашивает `/checkReady`, по `remaining > 0` ставит `setTimeout(remaining)`, по срабатыванию запрашивает снова. Отмена и устаревшие ответы — через счётчик версии `readyTimerVersion` (private `stopReadyTimer()` увеличивает его и гасит in-flight `/checkReady`). `remaining = 0` — значок уже выставил сервер, таймер не нужен. Сам значок — серверное уведомление `Notifications.LOOTBOX`, клиент его не считает. Владелец — `IdleBtn`: конструктор вызывает `checkReady()`, `onDestroy()` — `reset()`; `/checkReady` уходит при каждом создании главного экрана. ГДД: [#gdd-trophies-window](game-design/lootbox-gdd.md#gdd-trophies-window) (значок), [#gdd-open-slot](game-design/lootbox-gdd.md#gdd-open-slot) (таймер по серверному времени).

### LootboxIdleSection {#lootbox-idle-section}
`src/views/home_screen/popups/lootbox/LootboxIdleSection.ts` — секция сундуков внутри `IdlePopup`
(`#lootbox-idle-section`). Конфиг `LootboxIdleSectionConfig`. ГДД: [#gdd-trophies-window](game-design/lootbox-gdd.md#gdd-trophies-window).
- `showGrid()` / `UICell(quality)` — сетка 5×2, только качества с count > 0, все сразу без пагинации. Клетка кликабельна только при `hasFreeSlot()` ([#gdd-open-slot](game-design/lootbox-gdd.md#gdd-open-slot): занята — нажатие ничего не делает); нажатие открывает `LootboxStartOpenPopup`.
- `showSlots()` / `UISlot(slot)` — ячейка 290×50: иконка 46×42 при `x = 10`, текст при `x = 70`, справа кнопка шириной 90 (`x = -5`, `X_RIGHT_B`). При остатке 0 — зелёная «Открыть» → `onOpen`; иначе синяя с ценой → `showSpeedup`, и нажатие на иконку тоже `showSpeedup` (`Button.newSimpleButtonMode`). Надпись «Выберите сундук для открытия» при `slots.length < slotsCount`. Пересечения областей нажатия нет: иконка занимает 10–56 px, кнопка — 195–285 px. Каждый `Button` держит свой `_zone` с `hitArea` внутри своего `Layout` (`Layout.setInteractive`), поэтому PIXI выбирает верхний объект под курсором и порядок добавления детей на это не влияет — ветка «z-order не задан» из ревью 2026-11-04 отклонена. Возвращаемые `newSimpleButtonMode` объекты `Button` нигде не сохраняются — так во всём проекте (76 мест), включая `ListBox`; `_zone` умирает вместе с ячейкой при `showSlots()`.
- `updateTimers()` — тик раз в секунду через `App.tick`; конец = `TimeUtils.nowMls() + remaining` (`endTimeBySlot`), остаток из `getRemaining(slot)`.
- `requestPrices()` — `/speedupPrices` (пачка, один запрос) при показе и раз в минуту (`Every`); ответ `{prices:[{slot, quality, remaining, price}]}` обновляет `priceBySlot` и `endTimeBySlot` целиком, затем одна `showSlots()`. Пустой массив — норма: ускорять нечего. Ошибка — `console.warn`. ГДД: [#gdd-speedup](game-design/lootbox-gdd.md#gdd-speedup).
- `update(lootbox)` / `redraw(lootbox)` / `setLootbox` — перерисовка по данным сервера, в том числе при отказе любого маршрута. Частичная перерисовка через `replaceByName` (`Layout.clear()` меняет версию поколения). `onBagUpdate()` — перерисовка только сетки по `BAG_UPDATE`; слотам это не нужно, `UISlot` не читает сумку (иконка, название качества, таймер из `endTimeBySlot`, кнопка), количество из сумки есть только в `UICell`. `update` сразу вызывает `requestPrices()`, поэтому цена обновляется не только раз в минуту, но и после каждого действия. `setLootbox` переносит цену прошлого ответа (`priceBySlot`), только если в ячейке тот же сундук — смена видна по выросшему остатку (`now + remaining <= previousEndTime`), иначе цена сбрасывается.
- `onOpen(slot)` → `/open` → `showOpenResult(result)`: `LootboxRewardPopup` + `RewardFlightUtils` (`hold(rewards, layout)` до попапа, `fly` в `onExit`). Если окно закрыто до ответа — награда не показывается (она уже в сумке). ГДД: [#gdd-claim](game-design/lootbox-gdd.md#gdd-claim).
- Закрытие окна до ответа: `showOpenResult` проверяет `layout.objVersion() === 0` и выходит. Двойное нажатие в `onOpen`/`onStartOpen`/`onOpenNow` гасит `WSSocket.sendButtonRequest` (`LootboxState.startOpen`/`open`/`speedup`): пока запрос не вернулся, следующий отклоняется с `ERR_WS_BUTTON_ALREADY_PRESSED`; сервер повтор тоже отклоняет без списания.
- `devFinishOpen()` — только под `Globals.isDevTools()`, кнопка-иконка `atlas/ui/icons/right.png` в левом верхнем углу секции: `POST /ingame/devTools/lootboxFinishOpen`, сервер сдвигает окончание таймера в прошлое, ответ `{lootbox}` → `update(lootbox)`. Служит для проверки открытия без ожидания. Слот `devFinishOpen` добавлен в корень секции с `isAbsolute: true` (`x: 0, y: 0`, `X_LEFT_B | Y_TOP_B`): движок исключает абсолютного ребёнка из подсчёта высоты и из потока (`Layout` `_refresh`, ветки `isAbsolute`), поэтому кнопка не занимает строку и не растягивает окно «Трофеи». Содержимое перерисовывает `showDevFinishButton()` из `showSlots()`: кнопка есть, только когда в ячейке идёт таймер (`remaining > 0`), иначе слот пустой. В `TOP_TO_BOTTOM`-контейнере обычный ребёнок дал бы лишнюю строку с `spacing` — так окно и вылезало за границу раньше.

### Попапы {#popups}
`src/views/home_screen/popups/lootbox/`, оформление через `LootboxUtils.createWindow`.
- `LootboxStartOpenPopup` — подтверждение постановки: имя, иконка, «Награда в сундуке» (типы и диапазоны из `/info`), время открытия, зелёная кнопка «Начать открывать» (`onStartOpen` → `startOpen` → `LootboxIdleSection.update`). Попап закрывается в обеих ветках ответа. Отказ сервера приходит в `catch` (`WSSocket.sendRequest` отклоняет промис при `errCode`/`errSection`) и всегда несёт `lootbox` — `sendRefusal` на сервере собирает его через `createLootboxResponse`, поэтому `catch` перерисовывает секцию по свежему состоянию, как `LootboxSpeedupPopup`. Отказ без `lootbox` — только `ERR_WS_BUTTON_ALREADY_PRESSED` (двойное нажатие), состояние на сервере не изменилось, перерисовка не нужна; такие ошибки и сетевые идут в `console.warn`. ГДД: [#gdd-open-slot](game-design/lootbox-gdd.md#gdd-open-slot), [#gdd-contents](game-design/lootbox-gdd.md#gdd-contents).
- `LootboxSpeedupPopup` — «Открыть сейчас»: таймер, цена из конфига (`priceBySlot` секции); при `null` один `requestPrice()` при открытии, дальше раз в минуту (`Every`). До цены кнопка серая без обработчика (`createOpenButton(…, enabled)`), после ответа — зелёная. `onOpenNow` шлёт `{slot, price}`; нехватка золота → `Footer.openShop()`; `refuse(lootbox)` — закрытие и перерисовка секции при отказе. Истёк таймер на открытом попапе — `showReadyState()` (флаг `isReady`) убирает блок `cost` и меняет кнопку на «Открыть» → `onOpen()` шлёт `/open`; `requestPrice` после этого игнорируются. ГДД: [#gdd-speedup](game-design/lootbox-gdd.md#gdd-speedup).
- `LootboxRewardPopup` — награда сундука через `ItemsPresets.createRewardsLayout` (без жёсткого перечисления типов); в `showOpenResult` до показа попапа `let flyId = RewardFlightUtils.hold(result.rewards, this.layout)`, `onExit` вызывает `RewardFlightUtils.fly(flyId, центр экрана)`. При уничтожении сцены (`Scene.triggerDestroy`) `onExit` тоже срабатывает, но `fly` видит `isDestroyed` и снимает удержание без полёта — подписчики `FLY_ICONS` уже отписаны ([жизненный цикл](reward-flight-utils-architecture.md#lifecycle)). ГДД: [#gdd-claim](game-design/lootbox-gdd.md#gdd-claim).
- Все три: статический `publish(screen, config)`, `getAsGameFlash()`, `view()`.

### LootboxReceivedPopup {#received-queue}
Попап «Получен сундук» за задание, очередь `#received-queue`. ГДД: [#gdd-obtain](game-design/lootbox-gdd.md#gdd-obtain).
- `enqueue(screen, quality)` — в буфер; если ничего не показано, `showNext()`. `showNext()` берёт следующий, подгружает пакет глоу и публикует попап; освобождение — по `EVENT_DESTROYED` (в `onDestroy` показывается следующий). Счётчик `generation` отбрасывает отложенные показы после `clearQueue()`. В `onDestroy` снимаются твины только с самого `this.layout`: твин полёта сундука висит на `content.box`, а на момент `EVENT_DESTROYED` движок уже очистил `_children`/`_childNames` (`Layout.destroy`), поэтому `child("content.box")` там всегда `undefined` — отдельного снятия не требуется, и код его не делает.
- `clearQueue()` — вызывается из `LootboxState.reset()`.
- Анимация как у `TrainCollectionItemPopup`: появление 500 мс (alpha 0→1, scale 0.8→1, outQuad), пауза 500 мс, сундук летит к `HeaderProfile` и уменьшается за 500 мс (`playOutcomeAnimation`), попап гаснет через 100 мс; тапа нет. Счётчик количества сундуков в попапе не показывается (решение пользователя 2026-11-04), подписки на `BAG_UPDATE` у попапа нет.

### LootboxUtils {#utils}
`getName(quality)` — «Сундук: {0}» + `ranks.N`; `formatDuration(ms)` — «1ч 30м» (`timeDDHHMMSS_Mls`); `createWindow(title, content, width)` — общая рамка попапов. `getName` прогоняет название ранга через `StringUtils.capitalize(CAPITALIZE_FIRST_UPPER_OTHER_LOWER)` — для текущих десяти рангов (`ru.json`, одно слово, первая буква заглавная) результат не меняется; оставлено решением пользователя 2026-11-04. Оговорка: название из нескольких слов с заглавными внутри (аббревиатура, другая локаль) приведение опустит в нижний регистр — при появлении таких данных `capitalize` убрать.

`createPriceLayout(price, fontSize)` рисует цену ускорения по паре `{silver, gold}` от сервера (`speedupPriceEntry`). `null` — цены ещё нет, вместо неё «...». Комбинации: хватает серебра — `silver > 0, gold = 0`, показывается серебро; серебра не хватает — `silver = balance, gold > 0`, показываются обе валюты по ГДД ([#gdd-speedup](game-design/lootbox-gdd.md#gdd-speedup)); серебра нет вовсе — `silver = 0, gold > 0`, только золото; сундук готов (`speedupPrice` при `remainingMs <= 0` даёт 0) — `silver = 0, gold = 0`, рисуется «0 серебра». Проверка `price.silver > 0 || price.gold === 0` читается как «серебро участвует в цене»: без второй половины случай нулевой цены оставил бы блок стоимости пустым. На готовом сундуке эта надпись не показывается — секция перерисовывает ячейку в «Открыть», а попап ускорения уходит в `showReadyState()`, где блок `cost` убирается.

### RewardFlightUtils {#reward-flight}
Общая утилита полёта и удержания награды: API, жизненный цикл, цели — [reward-flight-utils-architecture.md](reward-flight-utils-architecture.md). ГДД: [#gdd-claim](game-design/lootbox-gdd.md#gdd-claim).
- Лутбоксы используют её в трёх местах: `LootboxIdleSection.showOpenResult` (`hold` после проверки «окно живо», `fly` в `onExit` `LootboxRewardPopup`, точка вылета — центр экрана), `IdlePopup` (`flyId`, `#trophies-take`), `HomeScreenQuest` (`hold` в переменную, затем `fly(id, точка)`).
- Награда лутбокса — любой тип предмета; удержание получают только ресурсы из таблицы целей утилиты, остальное в сумке появляется сразу.

### IdlePopup (изменения) {#trophies-take}
`src/views/home_screen/popups/idle/IdlePopup.ts`; idle-часть (таймер сбора, «НАГРАДА») не менялась. ГДД: [#gdd-trophies-window](game-design/lootbox-gdd.md#gdd-trophies-window).
- `requestData()` — параллельно `/ingame/home/idle` (трофеи начисляются при открытии; по ответу в поле `flyId: number | null` кладётся `RewardFlightUtils.hold(data.rewards, this.layout)`; закрытие окна до ответа удержание не ставит: owner уже мёртв) и `requestLootbox()` + `requestInfo()`. Ошибка лутбоксов окно не блокирует (только `console.warn`, секция не рисуется).
- `takeRewards(from)` (`#trophies-take`) — «ЗАБРАТЬ»: `isRewardsTaken = true`, `RewardFlightUtils.fly(flyId, from)` при `flyId !== null`, перерисовка контента; окно не закрывается, список трофеев остаётся, кнопка серая (`hasRewardsToTake()`). `isRewardsTaken` нужен только для серой кнопки. Отдельной проверки `objVersion()` нет, и она не нужна: `layout.child(...)` на уничтоженном `Layout` возвращает `undefined` (`destroy` чистит `_childNames`), поэтому перерисовка в этом случае не выполняется, а нажатие по уничтоженному лейауту невозможно — `destroy` снимает интерактив (`removeInteractive`).
- `releaseResources()` (`onDestroy`) — `RewardFlightUtils.fly(flyId, центр экрана)` при `flyId !== null`; после «ЗАБРАТЬ» второго полёта нет: однократность внутри `RewardFlightUtils`.
- Закрытие — тап по фону (`bgClick` → `layout.destroy()`); ключ `idleScreen.close` удалён, подсказка `idleScreen.closeHint`. Окно выше примерно на 200 px.

### Остальные изменения {#other-changes}
- `IdleBtn` — значок `AttentionAnimation` по `Notifications.LOOTBOX`: `handleLootboxNotifications`, подписка `onNotificationChangeCall`, отписка в `onDestroy`. Конструктор после подписки вызывает `LootboxState.checkReady()`, `onDestroy()` после отписки — `LootboxState.reset()`.
- `HomeScreenQuest` (`BtnQuest`) — иконка награды задания через `ItemsPresets.createImageLayout`; после `completeQuest`: `let flyId = RewardFlightUtils.hold(response.rewards, this.layout)`, `RewardFlightUtils.fly(flyId, Coord.getWorldPosition(this.layout.container))` и `LootboxReceivedPopup.enqueue` для каждого лутбокса в `rewards`. Рядом с иконкой печатается `reward.count` для любой награды, включая лутбокс: ГДД [#gdd-obtain](game-design/lootbox-gdd.md#gdd-obtain) требует, чтобы иконка сундука заменяла иконку схем, а про количество в слоте задания молчит (запрет счётчика там только для попапа «Получен сундук»). Повтор нажатия (`ERR_WS_BUTTON_ALREADY_PRESSED`) гасится защитой `sendButtonRequest` молча, остальные ошибки — `console.warn`.
- `ItemsPresets.createImageLootbox(quality, randomQuality, scale)` — иконка сундука (заглушка, тинт `Const.getTechColor(quality)`; случайный — без тинта, с «?»). Единственный диспетчер `createImageLayout` вызывает её для `ItemType.LOOTBOX`; `createRewardsLayout` вызывает `createImageLayout`. Один смысл — одна функция ([#gdd-function-mapping](agent-system-workflow.md#gdd-function-mapping)).
- `Footer.openShop()` — вынесенный метод открытия магазина (вкладка 3), используется при нехватке золота.
- `Globals` — поля `lootbox` нет, ссылок на лутбоксы нет.

## Потоки {#flows}
- Вход: `HomeScreen.onCreate` → `new IdleBtn` → `LootboxState.checkReady()`; выход: уничтожение `HomeScreen` → `IdleBtn.onDestroy` → `reset()`.
- Окно: `/idle` ∥ (`/lootbox` + `/info`) → `RewardFlightUtils.hold(rewards, layout)` для трофеев → секция.
- Постановка: сетка → `LootboxStartOpenPopup` → `/startOpen` → `update(lootbox)`.
- Открытие: ячейка на 0 → «Открыть» → `/open` → `showOpenResult`. Ускорение: `LootboxSpeedupPopup` → `/speedup` → `showOpenResult`.
- Отказ любого маршрута (ответ `LootboxResponseJSON`): попап закрыт, секция перерисована по `lootbox` из ответа, без сообщения ([#gdd-claim](game-design/lootbox-gdd.md#gdd-claim), «Нестандартные действия»).
- Окно закрыли до ответа `/open`/`/speedup`: награда не показывается, она уже в сумке.
- Вторая вкладка и возврат из фона: состояние берётся с сервера при открытии окна; тик ячейки считает конец от `remaining` последнего ответа.

## Данные {#data}
- `lootbox.d.ts`: `LootboxResponseJSON` (`{ lootbox }`), `LootboxSlotsJSON`, `LootboxSlotJSON` (`{ slot, quality, remaining }`), `LootboxInfoJSON`, `LootboxQualityJSON` (`{ quality, duration, rewards }`), `LootboxRewardRangeJSON`, `LootboxCheckReadyJSON`, `LootboxPriceJSON` (`{ silver, gold }`), `LootboxSpeedupPriceJSON` (`{ remaining, price, lootbox? }` — одна ячейка), `LootboxSpeedupPriceEntryJSON` (`+ slot, quality`) и `LootboxSpeedupPricesJSON` (`{ prices }` — пачка), `LootboxOpenResultJSON extends LootboxResponseJSON` (`+ rewards`). Контракт маршрутов — в серверном документе.
- `LootboxJSON extends BagItemJSON { randomQuality? }` в `popups/bag/bag.d.ts` — флаг предмета; `QuestJSON.reward` — `ItemJSON`.
- `ItemType.LOOTBOX = 7` (6 — `COLLECTION_ITEM`, на клиент не добавлен); `Notifications.LOOTBOX = "lootbox"`.
- `quality` во всех типах — это `Rank.ordinal()` с сервера, значения 1…10 (`Rank.I`…`Rank.X`), не произвольное число. Одна и та же величина служит тремя ролями: ключом локали `ranks.N`, аргументом `Const.getTechColor` и параметром `ItemsPresets.createImageLootbox`. `Rank.NONE = 0` в ответы не попадает — слоты с ним отсеивает `isValid()`, поэтому нумерация в `ranks` начинается с 1 и совпадает с ординалом. То же число лежит в `ItemType.LOOTBOX.id` в сумке, из-за чего `LootboxReceivedPopup` получает качество не из лутбокса, а из `reward.id` задания (`HomeScreenQuest` → `enqueue(screen, reward.id)`).
- i18n (`ru.json`): блок `lootboxScreen` (name, selectToOpen, rewards, rewardRange, openTime, startOpen, openCost, openNow, open, reward, received), `idleScreen.closeHint`.

## Принятые компромиссы {#tradeoffs}
- Схемы самолёта не летят: подписчик `HOME_AERODROME_AIRPLANE_SCHEMES` есть только в неподключённом `HomeScreenAerodrome`.
- `releaseHold` снимает удержание, только если bag-push пришёл раньше. Теги уникальны по id полёта ([reward-flight-utils-architecture.md](reward-flight-utils-architecture.md#api)). При уничтожении сцены `fly` не запускает полёт и снимает удержание сразу — подписчики `FLY_ICONS` уже отписаны.
- Окно «Трофеи» выше примерно на 200 px, на низких экранах не проверено.
- Нет блокировки кнопок постановки и «Открыть» на время запроса, защита серверная. В попапе ускорения кнопка серая до прихода цены.
- Нехватку золота клиент проверяет сам по кэшу `Globals.bag` и уводит в магазин; окончательное правило баланса — серверное `speedupAndOpen`. Дублирование осознанное: без него игрок не узнал бы путь к золоту. При устаревшем кэше возможен лишний переход в магазин или отказ.
- Перерисовка ячеек раз в минуту может съесть нажатие.
- В `createRewardsLayout` неизвестный `itemType` даёт пустой блок 25×25 перед числом.
- `reset()` при любом пересоздании `HomeScreen` (реконнект, бой, бан) сбрасывает кэш `/info` и очередь `LootboxReceivedPopup`.
- `LootboxReceivedPopup`: гонки `clearQueue()` с показом нет — `clearQueue()` снимает `isShown` и увеличивает `generation`, отложенный `onComplete` с прежней версией показ отменяет. Если `reset()` пришёл между `queue.shift()` и `onComplete`, сундук не показывается — попап не должен всплывать после ухода с экрана.
- Пустая сетка — штатное состояние по ГДД (в сетке только качества из сумки), поэтому «нет сундуков» и «`info` не загрузился» не различаются. Случай «`lootbox` есть, `info` нет» требует `reset()` посреди запроса и в игре не воспроизводится; при отказе `/info` секция не появляется — `IdlePopup` ждёт оба ответа через `Promise.all`.
- `IdlePopup.data` объявлен как `IdleJSON` без инициализации. Дыры нет: `publish` не показывает попап без `data`. При включении `strict` в `tsconfig` поле даст TS2564 — тогда инициализировать `null` и расширить тип.
- `requestPrices()` секции и `LootboxSpeedupPopup.requestPrice()` не дублируют друг друга: секция берёт снимок всех ячеек (`/speedupPrices`), попап — цену из конфига и зовёт `/speedupPrice` только когда её не было. Общего метода на `now + remaining` нет намеренно.
- Попап «Открыть сейчас» не открывается на готовом слоте: `updateTimers` перерисовывает ячейки при `remaining === 0`, а `UISlot` на готовый слот ставит зелёную «Открыть» вместо кнопки ускорения — это единственный вход в попап. Остаток считается от того же `endTimeBySlot`, что и `isReady` ячейки, поэтому «нулевой таймер и `price = null`» недостижим. Гонка «таймер истёк между перерисовкой и кликом» длится не больше тика и закрывается `showReadyState()` (P1-7): цена убирается, кнопка становится «Открыть» → бесплатный `/open`. Отдельная ветка для «уже готово» не нужна.
- Отложенное: `/workspace/client/.claude/memory/client_lootbox_deferred_fixes.md`.

## Заглушки ассетов {#stubs}
`ItemsPresets.createImageLootbox` (`atlas/home_screen/box.png` + тинт) — иконка сундука, заменить на арт по
качествам. Свечение попапа «Получен сундук» — `atlas/lootbox_screen/glow.png`, пакет `LootboxScreen` (спрайт
перенесён из ветки koba/collection, 2026-11-04).

## Карта файлов {#file-map}
### Файлы прямого влияния
- `src/views/home_screen/popups/lootbox/LootboxState.ts` — состояние, запросы, таймер значка, `reset()`.
- `src/plain/RewardFlightUtils.ts` — общий полёт наград ([reward-flight-utils-architecture.md](reward-flight-utils-architecture.md)).
- `src/views/home_screen/popups/lootbox/lootbox.d.ts` — типы.
- `src/views/home_screen/popups/lootbox/LootboxIdleSection.ts` — секция сундуков.
- `src/views/home_screen/popups/lootbox/LootboxStartOpenPopup.ts` — подтверждение постановки.
- `src/views/home_screen/popups/lootbox/LootboxSpeedupPopup.ts` — ускорение.
- `src/views/home_screen/popups/lootbox/LootboxRewardPopup.ts` — показ награды.
- `src/views/home_screen/popups/lootbox/LootboxReceivedPopup.ts` — «Получен сундук», очередь.
- `src/views/home_screen/popups/lootbox/LootboxUtils.ts` — имена, время, цена, рамка.

### Файлы косвенного влияния
- `src/plain/items/ItemType.ts` — зависимость: `LOOTBOX = 7`.
- `src/shared/notifications/Notifications.ts` — зависимость: `LOOTBOX`.
- `src/views/home_screen/IdleBtn.ts` — значок «ТРОФЕИ»; владелец таймера значка: `checkReady`/`reset`.
- `src/views/home_screen/popups/idle/IdlePopup.ts` — окно «Трофеи», хост секции, «ЗАБРАТЬ».
- `src/views/home_screen/HomeScreenQuest.ts` — награда-сундук задания, показ получения.
- `src/views/home_screen/popups/bag/bag.d.ts` — `LootboxJSON.randomQuality`.
- `src/presets/ItemsPresets.ts` — `createImageLootbox`, диспетчер `createImageLayout` (флаг читается как `(data as LootboxJSON).randomQuality`).
- `src/shared/footer/Footer.ts` — `openShop()`.
- `assets-src/raw/lang/ru/ru.json` — блок `lootboxScreen`, `idleScreen.closeHint`.
