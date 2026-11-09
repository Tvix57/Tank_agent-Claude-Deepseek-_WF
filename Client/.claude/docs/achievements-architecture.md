# Документация компонента "Достижения" (Profile → Achievements)

ГДД: [achievements-gdd.md](/workspace/client/.claude/docs/game-design/achievements-gdd.md)

Сверено с кодом после merge `origin/amnesia/fix` 2026-10-19.

**auto-create** — составлено `client-analyst-lead` путём анализа существующего кода (не по итогам
разработки), доверие ниже, чем к документации по факту реализации.

Объём сокращён по запросу пользователя: вёрстка и стили не описываются. Документ фиксирует (1) какие
данные приходят с сервера и какими методами попадают в компоненты, (2) какие элементы обновляются по
имени метода/поля, (3) механизм показа `AchievementCompletePopup`.

## 1. Назначение и бизнес-логика {#s1-purpose}

Раздел профиля "Достижения": достижения по типам (`AchievementType`: `airplaneHunt`, `tanksHunt`) с
прогрессом, рангами (`AchievementRank`: 0..X + MAX) и наградой за ранг. Отдельно — тост
`AchievementCompletePopup` при выполнении достижения (push от сервера) и пресет шапки
`HeaderAchievementsBar`, который этот тост создаёт.

Правила ГДД: [#gdd-purpose](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-purpose), [#gdd-hunt-types](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-hunt-types), [#gdd-task](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-task) (задание и награда за него клиентом не вычисляются, приходят от сервера).

## 2. Референсы

Не использовались.

## 3. Использованные паттерны {#s3-patterns}

- `PreloadableLayout` (`onPreload`/`onCreate`/`onDestroy`) — секции, которым нужны данные до показа.
- `LayoutSlot` для переключения вложенных секций в `AchievementsSection` (как `CollectionsSection`,
  см. `collections-architecture.md`).
- Push-события — подход описан в `server-push-events-subscription.md`. Здесь одно сырое событие
  `g/ws/events/achievements/update` слушается двумя независимыми способами (#s8-tradeoffs).

## 4. Список классов {#s4-classes}

- `AchievementRank` (enum) — реализует качества, [#gdd-quality](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-quality).
- `AchievementsSection`, `AchievementsListSection`, `AchievementLine`, `AchievementRank` (enum) — в
  `src/views/home_screen/popups/profile/achievements/`
- `AchievementsTypeSection` (абстрактный), `AchievementsAirplanesHuntSection`,
  `AchievementsTanksHuntSection`, `AchievementType` (enum, файл `AchievemetType.ts`) — в
  `achievements/achievements_type/`
- `HeaderAchievementsBar` (`src/shared/header/presets/`), `AchievementCompletePopup`
  (`src/views/popups/`)
- Domain-типы `AchievementsJSON`, `AchievementJSON`, `AchievementDoneJSON` (`achievement.d.ts`)

## 5. Якоря

`#s1-purpose` `#s3-patterns` `#s4-classes` `#s6-toc` `#s7-data-flow` `#s7-1-domain-types`
`#s7-2-achievementssection` `#s7-3-achievementslistsection` `#s7-4-achievementstypesection`
`#s7-5-achievementline` `#s7-6-headerachievementsbar` `#s7-7-achievementcompletepopup`
`#s8-tradeoffs` `#s10-file-map`

## 6. Оглавление {#s6-toc}

- [1. Назначение и бизнес-логика](#s1-purpose)
- [3. Использованные паттерны](#s3-patterns)
- [4. Список классов](#s4-classes)
- [7. Классы и методы](#s7-data-flow)
  - [7.1 Domain-типы](#s7-1-domain-types)
  - [7.2 `AchievementsSection`](#s7-2-achievementssection)
  - [7.3 `AchievementsListSection`](#s7-3-achievementslistsection)
  - [7.4 `AchievementsTypeSection` + наследники](#s7-4-achievementstypesection)
  - [7.5 `AchievementLine`](#s7-5-achievementline)
  - [7.6 `HeaderAchievementsBar`](#s7-6-headerachievementsbar)
  - [7.7 `AchievementCompletePopup`](#s7-7-achievementcompletepopup)
- [8. Компромиссы](#s8-tradeoffs)
- [9. Связь с ГДД](#s9-gdd-link)
- [10. Карта файлов компонента](#s10-file-map)

## 7. Классы и методы {#s7-data-flow}

### 7.1 Domain-типы (`achievement.d.ts`) {#s7-1-domain-types}

ГДД: [#gdd-task](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-task), [#gdd-quality](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-quality) (`nextRank`, `currentRank`), [#gdd-progress](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-progress) (`currentProgress`/`maxProgress`).

```ts
interface AchievementsJSON { inProgress: AchievementJSON[]; }   // ответ /getSection

interface AchievementJSON {          // состояние одного достижения
    id: number;
    type: string;                    // значение AchievementType
    currentProgress: number;
    maxProgress: number;
    currentRank: number;
    nextRank: number;                // AchievementRank, включая MAX
    reward?: BagItemJSON;
    image?: { country?: number };
}

interface AchievementDoneJSON {      // payload push-события, без прогресса и награды
    id: number;
    section: string;                 // значение AchievementType
    nextRank: number;
    isDone: boolean;
}
```

Серверный контракт (только факты): запросы `/ingame/achievements/getSection`, `/update`, `/getReward`
(описаны в 7.4, 7.5), push `g/ws/events/achievements/update` с `AchievementDoneJSON`. Серверная
сторона — `/workspace/server/.claude/docs/achievements-architecture.md`.

### 7.2 `AchievementsSection` {#s7-2-achievementssection}

Корневой контейнер вкладки профиля, данных не грузит: маршрутизация между тремя секциями через
`LayoutSlot`.
ГДД: [#gdd-hunt-types](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-hunt-types) (две кнопки-раздела), переход по нажатию на оповещение — [#gdd-complete-popup](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-complete-popup).

- `showList()` / `showTanksHunt()` / `showAirplanesHunt()` — кладут секцию в `slot` и вызывают
  `section.start()`.
- `focus()` — вызывается из конструктора при `config.focus` (`IAchievementSectionConfig`); при
  заданном `focus.id` открывает секцию по `focus.type`, иначе список. Используется при переходе из
  `AchievementCompletePopup` (7.7).

### 7.3 `AchievementsListSection` {#s7-3-achievementslistsection}

Список двух категорий с бейджами "есть невостребованные достижения". Данные не запрашивает, читает
уже загруженный `Globals.account.notifications`.
ГДД: [#gdd-hunt-types](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-hunt-types), [#gdd-notifiers](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-notifiers).

- `onCreate()` — подписка `Globals.account.onNotificationChangeCall(handleUserNotifications, this)` (общий
  механизм аккаунта, не push достижений) и первый вызов `handleUserNotifications()`; приватный
  `focus()` — пустая заглушка (TODO).
- `handleUserNotifications()` — берёт `Notifications.getNotificationObject(Notifications.ACHIEVEMENT_ID)?.doneSections`
  и для каждого пункта (имена `tanksHunt`/`airplaneHunt`) переключает `visible` спрайта `notify`.
- `onDestroy()` — `offNotificationChange`.

### 7.4 `AchievementsTypeSection` + `AchievementsAirplanesHuntSection` / `AchievementsTanksHuntSection` {#s7-4-achievementstypesection}

Одна категория: скроллируемый список `AchievementLine`. Наследники только возвращают тип через
абстрактный `getAchievementType()`.
ГДД: [#gdd-hunt-types](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-hunt-types); порядок списка — [#gdd-list-order](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-list-order), расхождения Р1–Р3 в [#s8-tradeoffs](#s8-tradeoffs).

- `onPreload()` — `Globals.ws.sendRequest("/ingame/achievements/getSection", { section })`; ответ
  `AchievementsJSON` в `this.data`, затем `preloadCompleted()` / `preloadFailed()`.
- `onCreate()` — `showAll()`, при `config.focus` ещё `focus()`.
- `showAll()` — по `data.inProgress` создаёт `AchievementLine` в собственном `Layout`-контейнере
  (`lineContainers`), добавляет в `scroll.content`, затем `sortAchievements()`.
- `sortAchievements()` — публичный, вызывается и из `AchievementLine.updateUI()`. Переставляет
  существующие строки между зафиксированными контейнерами (`shiftChildren()` + `add`), строки не
  пересоздаются; `data.inProgress` переписывается в новом порядке. Корзины: 0 — выполнено, ранг не
  MAX (сверху, по рангу убыв., затем id); 1 — в процессе (по рангу убыв., затем id); 2 — MAX (внизу, по id). Правило: #gdd-list-order; расхождения Р1–Р3 (#s8-tradeoffs).
- `focus()` — прокрутка к `config.focus.id`: смещение — сумма высот `lineContainers` выше найденного +
  `scroll.content.spacing.y`, зажато снизу `scroll.getMinBounds()`; при ненайденном id — выход. Тот же
  приём — `collections-architecture.md#cls-collectionsexperimentaltankssection`.

### 7.5 `AchievementLine` {#s7-5-achievementline}

Пункт списка, хранит `data: AchievementJSON`; сам запрашивает обновления и обновляет свой UI частично.
ГДД: карточка — [#gdd-card](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-card) (расхождение Р4 в #s8-tradeoffs), награда — [#gdd-reward](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-reward), прогресс — [#gdd-progress](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-progress), звезда качества и ряд звёзд — [#gdd-quality](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-quality) (`AchievementRank`, 4).

- `onCreate()` — строит UI, `refreshVisualState()`, подписка `App.events.on("g/ws/events/achievements/update", onEventUpdate)`;
  `onDestroy()` — отписка.
- `onEventUpdate(data)` — при `data.id == this.data.id` вызывает `updateData()`. Из payload берётся
  только `id`, событие — триггер перезапроса.
- `updateData()` — `/ingame/achievements/update { section: data.type, id }`; ответ заменяет `this.data`;
  при `currentProgress >= maxProgress` — `updateUI()`, иначе `updateProgress()`.
- `getReward()` — `/ingame/achievements/getReward`. Если в ещё не заменённом `this.data` есть
  `reward` — сначала `animationReward()` (hold золота + `FlyIconsAnimation`), затем ответ заменяет
  `this.data`, затем `updateUI()`.
- `updateUI()` — `refreshVisualState()` + `list.sortAchievements()`.
- `refreshVisualState()` — полное обновление по `this.data`: `visible` у `ready`; `replaceByName("reward", UIReward())`
  или `destroyChildByName("reward")` (если нет награды или `nextRank === MAX`); `setNextRank()`;
  `replaceByName("description", UIDescription())`; `setRankProgress()`.
- `updateProgress()` — без пересоздания: `text` у `textProgress` и `progressBar.set(0, currentProgress, maxProgress)`.
- `setNextRank(rank)` — `replaceByName("currentRank", ...)`, при MAX скрывает его.
  `setRankProgress()` — `visible` звёзд `rankProgress` по `currentRank`.
- Dev-tools (видны при `Globals.isDevTools()`), запросы `/ingame/devTools/achievement*`:
  `onMaxRankBtn`, `onDropRankBtn`, `onMaxProgressBtn` заменяют `this.data` ответом и вызывают
  `updateUI()`; `onDropProgressBtn` правит только `data.currentProgress` и вызывает `updateProgress()`.

### 7.6 `HeaderAchievementsBar` {#s7-6-headerachievementsbar}

Пресет шапки (`IHeaderPreset`) с `ScrollableArea` для тостов. Тот же пресет обрабатывает
`COLLECTION_SET_COMPLETED`: `collections-architecture.md#cls-headerachievementsbar-set-completed`.
ГДД: [#gdd-complete-popup](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-complete-popup) (показ один раз в момент выполнения, тосты столбиком).

- Конструктор → `onCreate()`: `GameEvents.emitter.on(GameEvents.ACHIEVEMENTS_EVENT, onAchievementDone)`.
  `GameEvents.listenServerEvents()` ре-эмитит в него payload сырого события `achievements/update` без
  преобразования. Отписка — приватный `onDestroy()` по `Layout.EVENT_DESTROYED`.
- `onAchievementDone(data: AchievementDoneJSON)` — при `data.isDone && data.nextRank != AchievementRank.MAX`:
  `AchievementCompletePopup.create(data, header.scene)` → `scrollContent.content.add(..., { px: 200 })` →
  `refreshForce()` контента и скролла → `show()`. Иначе попап не создаётся.

### 7.7 `AchievementCompletePopup` {#s7-7-achievementcompletepopup}

Тост (`extends Layout`); данные — параметр конструктора, тот же `AchievementDoneJSON`.
ГДД: [#gdd-complete-popup](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-complete-popup).

- `static create(data, scene)` — единственная точка создания; вызывается только из
  `HeaderAchievementsBar.onAchievementDone`.
- `show()` — твин появления, по завершении `hide(500, 5000)`: автоскрытие через 5 с.
- `hide(time, timeDelay)` — твин скрытия; по завершении `destroy()` и `refreshForce()` у родителя и
  родителя родителя. Других путей закрытия нет.
- `onBtnClick()` — клик по всему попапу: `ProfilePopup.publish` с `openTab: AchievementsSection.TAB_NAME`
  и `achievementSection: { focus: { type: data.section, id: data.id } }`; цепочка
  `AchievementsSection.focus()` → `showTanksHunt()/showAirplanesHunt()` → `AchievementsTypeSection.focus()`
  (7.2, 7.4). Сам тост по клику не закрывается, только по автоскрытию.
- Очереди нет (в отличие от `popup-queue-pattern.md`): тосты накапливаются в скролле шапки
  одновременно.

## 8. Компромиссы {#s8-tradeoffs}

- Сырой push `g/ws/events/achievements/update` слушается дважды: `AchievementLine` напрямую через
  `App.events` (нужен только `id`) и `HeaderAchievementsBar` через `GameEvents.ACHIEVEMENTS_EVENT`
  (нужен весь `AchievementDoneJSON`). Дублирование подписки не переработано.
- `AchievementLine.onEventUpdate` всегда делает перезапрос `updateData()`: payload (`AchievementDoneJSON`)
  не несёт прогресса и награды.
- Р1 (ГДД, отложено 2026-10-14): `AchievementsTypeSection.ts:111-117` (`sortAchievements`) — группы качеств
  отсортированы от большего к меньшему (`b.currentRank - a.currentRank`, :115); по [#gdd-list-order](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-list-order) — от меньшего к большему.
- Р2 (ГДД, отложено 2026-10-14): там же — внутри группы качества нет сортировки по прогрессу (порядок по
  `id`); по #gdd-list-order — по прогрессу от большего к меньшему.
- Р3 (ГДД, отложено 2026-10-14): там же (корзина 0, :115) — блок «ждут награды» отсортирован от большего
  качества к меньшему; по #gdd-list-order — от меньшего к большему.
- Р4 (ГДД, отложено 2026-10-14): `AchievementLine.ts:150-158` (`UIAddDescription`) — нет иконки класса перед
  названием класса в тексте задания; по [#gdd-card](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-card) она нужна.

## 9. Связь с ГДД {#s9-gdd-link}

ГДД области — [achievements-gdd.md](/workspace/client/.claude/docs/game-design/achievements-gdd.md). Правило → клиентская реализация:

| Правило ГДД | Где на клиенте |
|---|---|
| [#gdd-purpose](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-purpose) — список заданий на технику, награда | вкладка `AchievementsSection` (7.2) |
| [#gdd-hunt-types](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-hunt-types) — две кнопки: танки, самолёты | `AchievementsListSection`, `AchievementsSection.showTanksHunt/showAirplanesHunt` (7.2, 7.3) |
| [#gdd-task](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-task) — задание, страна × класс, N единиц | не вычисляется; приходит `AchievementJSON` из `/getSection` и `/update` (7.1, 7.4) |
| [#gdd-quality](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-quality) — качества, звезда и ряд звёзд | `AchievementRank`, `AchievementLine.setNextRank/setRankProgress` (7.5) |
| [#gdd-progress](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-progress) — накопительный прогресс | считает сервер; клиент: `AchievementLine.updateProgress` (7.5) |
| [#gdd-reward](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-reward) — награда золотом, кнопка «Забрать награду» | `AchievementLine.getReward`, `animationReward`, `UIReward` в `refreshVisualState` (7.5) |
| [#gdd-card](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-card) — карточка (подложка, прогресс, «Выполнено») | `AchievementLine.refreshVisualState`; иконки класса в тексте задания нет, Р4 ([#s8-tradeoffs](#s8-tradeoffs)) |
| [#gdd-list-order](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-list-order) — порядок списка | `AchievementsTypeSection.sortAchievements`; Р1–Р3 ([#s8-tradeoffs](#s8-tradeoffs)) |
| [#gdd-complete-popup](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-complete-popup) — оповещение один раз, столбиком, клик открывает профиль | `HeaderAchievementsBar.onAchievementDone`, `AchievementCompletePopup.create/show/hide/onBtnClick` (7.6, 7.7) |
| [#gdd-notifiers](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-notifiers) — лампочки на аватарке, вкладке, кнопках разделов | `AchievementsListSection.handleUserNotifications` (7.3); `HeaderProfile`, `ProfilePopup` (10) |

## 10. Карта файлов компонента {#s10-file-map}

### Файлы прямого влияния

- `src/views/home_screen/popups/profile/achievements/achievement.d.ts` — типы данных с сервера.
- `src/views/home_screen/popups/profile/achievements/AchievementsSection.ts` — вкладка профиля «Достижения», точка входа.
- `src/views/home_screen/popups/profile/achievements/AchievementsListSection.ts` — список разделов достижений по типам.
- `src/views/home_screen/popups/profile/achievements/AchievementLine.ts` — строка достижения: прогресс, ранги, рефетч по push.
- `src/views/home_screen/popups/profile/achievements/AchievementRank.ts` — enum рангов (0..X + MAX).
- `src/views/home_screen/popups/profile/achievements/achievements_type/AchievemetType.ts` — enum типов достижений.
- `src/views/home_screen/popups/profile/achievements/achievements_type/AchievementsTypeSection.ts` — абстрактная секция типа, загрузка данных.
- `src/views/home_screen/popups/profile/achievements/achievements_type/AchievementsAirplanesHuntSection.ts` — секция типа `airplaneHunt`.
- `src/views/home_screen/popups/profile/achievements/achievements_type/AchievementsTanksHuntSection.ts` — секция типа `tanksHunt`.
- `src/shared/header/presets/HeaderAchievementsBar.ts` — индикатор в шапке, запуск тостов.
- `src/views/popups/AchievementCompletePopup.ts` — тост «достижение выполнено».
- `assets-src/atlas/achievements_screen/` — атлас графики экрана (пакет `AchievementsScreen`).

### Файлы косвенного влияния

- `src/plain/GameEvents.ts` — пробрасывает push `g/ws/events/achievements/update` в `ACHIEVEMENTS_EVENT`.
- `src/shared/header/Header.ts` — добавляет `HeaderAchievementsBar` в шапку (пресет `achievementsBar`, `py: 150`, справа снизу; блок валют `layout.resources` и методы шапки к достижениям не относятся).
- `src/shared/header/HeaderPresets.ts` — фабрика `achievementsBar`.
- `src/shared/header/presets/HeaderProfile.ts` — отметка непросмотренных достижений на кнопке профиля (лампочка на аватарке, [#gdd-notifiers](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-notifiers)).
- `src/shared/notifications/Notifications.ts` — константа `ACHIEVEMENT_ID` объекта уведомлений.
- `src/views/home_screen/popups/profile/ProfilePopup.ts` — вкладка, подгрузка пакета `AchievementsScreen`, отметка `notified` (лампочка на вкладке, [#gdd-notifiers](/workspace/client/.claude/docs/game-design/achievements-gdd.md#gdd-notifiers)).
- `src/views/home_screen/popups/profile/ProfileSection.ts` — зависимость: базовый класс секций профиля.
- `assets-src/raw/lang/ru/ru.json` — общий файл переводов: ключи `achievementsScreen.*` и `profileScreen.tabs.achievements`.
- `tools/src/config.yaml` — общий конфиг паковки: строка регистрации атласа `achievements_screen` как пакета `AchievementsScreen`.

Полнота проверена `grep` по `Achievement`/`ACHIEVEMENT`/`achievements` в `src`, `assets-src`, `tools`.
