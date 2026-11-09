---
name: naming
description: |
  Конвенции именования для client (TypeScript/PIXI) и server (Java) этого проекта: классы, файлы,
  методы, поля, константы, JSON-ключи, роуты. Использовать ПЕРЕД тем, как придумывать имена для
  нового кода (классы, методы, переменные, интерфейсы, роуты, поля БД), при ревью имён в диффе и когда
  пользователь просит "переименовать", "назвать нормально", "улучшить нейминг".
---

# Нейминг в проекте

Цель: имя должно выглядеть так, будто его написал человек из этой команды, а не общий "стандарт".
Порядок приоритетов при выборе имени:

1. **Конвенция соседнего кода** (тот же файл → та же папка → та же область). Если рядом
   `showSection`, новый метод — `showTab`, а не `displayTab`/`renderTab`.
2. **Термины из глоссария** (`/workspace/client/.deepseek/docs/glossary.md`, ведёт скилл `glossary`),
   ГДД области (`.deepseek/docs/game-design/<область>-gdd.md`) и архитектурного дока.
   Одна сущность — одно слово во всём коде: если в ГДД и коде "section", не вводить "category"/"group".
3. Таблицы ниже (выведены из фактической статистики кода, 2026-10-06).
4. Только потом — общие правила хорошего нейминга (раздел "Человеческие имена").

## Что НЕ переименовывать без явной просьбы

- Публичный контракт client↔server: JSON-ключи, роуты (`"/takeReward"`), имена push-событий
  (`/events/X/Y`), поля и коллекции MongoDB. Переименование ломает другую сторону или данные.
- Код в `src/ee/` (запрет из CLAUDE.md).
- Существующие имена "заодно" в задаче, которая не про нейминг. Плохое имя рядом — упомянуть
  пользователю, не править молча.
- Исторические опечатки (`respone`, `resonse`, `resorces`, `IAbstraccteChatSection`) — не
  копировать в новый код, но и не чинить попутно; можно отметить пользователю.

## Client (TypeScript, `src/`)

### Файлы и папки
| Что | Конвенция | Примеры |
|---|---|---|
| Класс | PascalCase, один default-export класс на файл, имя файла = имя класса | `CollectionSectionPopup.ts` |
| Декларации типов области | `snake_case.d.ts` рядом с кодом | `collection.d.ts`, `collection_album.d.ts` |
| Папки | `snake_case` | `home_screen/popups/profile/collections/collection_type/` |

### Суффиксы классов (по роли)
`*Popup` (окно, `static publish(screen, config)` + `view()`), `*Section` / `*Sections` (вкладка/часть
окна), `*Screen`, `*Scene`, `*Flash`, `*Event` (боевые события `battle/events/`), `*Presets`
(фабрики стандартной отрисовки), `*Utils` (статические хелперы), `*Type` (enum-подобные/стратегии),
`*Bar`, `*Btn`, `*Selector`, `*Animation`. Новый класс — с суффиксом той роли, что уже есть, не
изобретать `*Manager`/`*Handler`/`*Controller`, если в области такого нет.

### Типы и интерфейсы
| Что | Конвенция | Примеры |
|---|---|---|
| Данные с сервера | `<Сущность>JSON` | `CollectionItemJSON`, `TankSpawnEventJSON` |
| Конфиг конструктора/`publish` | `<Класс>Config` | `CollectionSectionPopupConfig` |
| Прочее | `*Options`, `*Params` — редко, предпочитать `Config` | |
| enum | PascalCase имя, члены `UPPER_SNAKE` | `RechargeMode.MANUAL` |

### Методы
| Префикс | Смысл | Примеры |
|---|---|---|
| `on*` | обработчик события/жизненного цикла | `onCreate`, `onDestroy`, `onExit`, `onBack`, `onCollectionDataUpdated` |
| `UI*` | приватный построитель куска лейаута, возвращает `Layout` | `UIMain`, `UIHeader`, `UIContent`, `UIFooter` |
| `view()` | отдать корневой элемент (`IViewProvider`) | |
| `static publish(...)` | создать и показать попап | |
| `get*` / `set*` | доступ/изменение; `setDefault*` — сброс к дефолту | `setTitle`, `setDefaultTitle` |
| `show*` / `update*` / `add*` / `remove*` / `destroy` | действия над отображением | `showSection` |
| `is*` / `has*` / `need*` | булевы (поля и методы) | `isMe`, `hasAvailableReward`, `needCounter` |
| `create*` / `build*` / `calculate*` / `apply*` / `load*` | соответственно смыслу | |

Колбэк в конфиге — `onClose`, `onExit`, а не `closeCallback`/`handleClose`.
`handle*` — только для диспетчеров целого потока событий (`handleUserNotifications`,
`handleWsErrors`, `handleAppEvents`); обработчик одного события/кнопки — всегда `on*`.

### Переменные, поля, константы
- Поля без `_`-префикса, модификатор доступа явно: `private readonly layout: FlashLayout`.
- Локальные переменные — `let` (стиль кода: `let` ~2300 против `const` ~20); не переписывать на
  `const` чужие строки.
- Статические константы — `static readonly UPPER_SNAKE` (`COLOR_DARK_GREEN`).
- Сокращения слов в новом коде не используются — см. «Полные слова и длина имени» ниже.
- Однобуквенные — только счётчики циклов и координаты (`i`, `x`, `y`).

## Server (Java, `game/src/main/java/com/linkedgames/game`)

### Классы и пакеты
- Пакеты lowercase по области: `model/collections`, `model/quests`, `pages/ws/ingame`, `dao`.
- Суффиксы по роли: `*UserComponent` (состояние игрока), `*Page` (роуты), `*Data` (балансовый
  справочник), `*Event`, `*Service`, `*Entry` (запись в БД), `*Dao`, `*Message`, `*Type`
  (enum/стратегия), `*Utils`, `*Task`, `*Processor`, `*Policy`, `*Factory`.

### Методы
| Префикс | Смысл | Примеры |
|---|---|---|
| `action*` | обработчик роута в `*Page`, имя = роут | `"/takeReward"` → `actionTakeReward` |
| `apiResponse` / `*ApiResponse` | сериализация в JSON для клиента | `sectionInfoApiResponse` |
| `db*` | персистентность | `dbMappingBuild`, `dbToData`, `dbFetchChanged` |
| `on*` | реакция на событие | `onCollectionCompleted` |
| `mark*` | смена флага/статуса | `markDeleted`, `markAsDirty` |
| `is*` / `has*` / `can*` | булевы | `hasSectionType` |
| `get*` / `create*` / `add*` / `send*` / `find*` / `build*` | по смыслу | `rollDropSectionType` (доменный глагол — ок) |
| `DEV_*` | только для DevTools | `DEV_resetCollection` |

### Константы и данные
- `static final` — `UPPER_SNAKE` (`COLLECTION_NAME`, `ERROR_BLACKLISTED`).
- JSON-ключи — `camelCase` (`collectionId`, `hasAvailableReward`), совпадают с полями `*JSON` на клиенте.
- Имена Mongo-коллекций — `snake_case` строкой (`"mailbox_dialogs"`).
- Роуты — `/camelCaseГлагол` (`/getCollectionReward`, `/markCollectionItemViewed`).

## Общее для client и server

### Одна сущность — одно имя на обеих сторонах
Серверный `CollectionItem` ↔ клиентский `CollectionItemJSON`, ключ `collectionId` ↔ поле
`collectionId`. Новое поле придумывается один раз и копируется на другую сторону, а не "переводится".

### Регистр аббревиатур
| Аббревиатура | Как пишется | Примеры | Не так |
|---|---|---|---|
| JSON | всегда заглавными | `CollectionItemJSON`, `BattleResultJSON` | `CollectionItemJson` |
| Id | как слово | `collectionId`, `getId()`, `tanksById` | `collectionID`, `itemID` |
| UI | заглавными | `UIMain`, `IBattleUI` | `UiMain` |
| HTTP / WS | заглавными в именах классов | `HTTPRouter`, `WSRouter`, `WSSocket` | `HttpRouter` |
| api / db | строчными в начале camelCase-имени | `apiResponse`, `dbToData` | `APIResponse` |

Имена из внешних библиотек (`textureID`, `worldID` у PIXI) используются как есть, их регистр не
переносится на свой код.

### Булевы: `need*`, а не `should*`
Префиксы булевых — `is*`, `has*`, `can*` (server) и `need*` (`needCounter`, `needSilverCoins`).
`should*` в коде не встречается ни разу — не вводить его, даже если так советует общий стандарт.

## Полные слова и длина имени {#full-words}

Действует для нового кода: имён функций, методов, переменных, полей и параметров на client и server.

- **Полные слова.** Слово в имени не сокращается: `button`, `background`, `image`, `index`,
  `callback`, `config`, `count`, `temporary`, `value`, а не `btn`, `bg`, `img`, `idx`, `cb`, `cfg`,
  `cnt`, `tmp`, `val`. Аббревиатуры, которые читаются как слово, остаются: `JSON`, `Id`, `UI`,
  `HTTP`, `WS`, `api`, `db`, `url` (регистр — таблица «Регистр аббревиатур»). Однобуквенные — только
  счётчики циклов и координаты (`i`, `x`, `y`).
- **Старый код.** Имена `btn`, `bg`, `img`, `idx`, `cb` в существующем коде не переименовываются и в
  ревью вне задачи на нейминг не отмечаются. Новое имя рядом с ними всё равно пишется полностью.
- **Не больше 3 слов.** Слово — каждая часть camelCase/UPPER_SNAKE, включая префикс: `onSell` — 2,
  `hasAvailableReward` — 3, `onSellRewardButtonClick` — 5, длинно. Не считаются обязательные
  ролевые префиксы, повторяющие роут или окружение: `action` у обработчика роута, `DEV_`. Имя не
  укладывается — убрать то, что уже даёт класс или параметр (повтор контекста), назвать результат, а
  не реализацию, или разбить метод: длинное имя обычно значит, что метод делает несколько дел.
- **Простой английский.** Код читают русскоязычные программисты: слова — частые и устоявшиеся в
  программировании (`get`, `give`, `buy`, `count`, `remove`, `release`), а не редкие или книжные
  (`bestow`, `procure`, `tally`, `expunge`, `relinquish`). Идиомы и сленг (`nuke`, `yeet`,
  `kickOff`) не используются. Игровые термины — из глоссария (скилл `glossary`).

## Человеческие имена (общие правила, после конвенций выше)

Типичные "машинные" признаки, которых избегать:

- **Имя врёт о поведении** — самая серьёзная ошибка. `get*`, `is*`, `has*`, `can*`, `need*`,
  `find*` и `*ApiResponse` только читают: не меняют состояние, не пишут в БД, не шлют события.
  Если метод что-то меняет, глагол должен это показывать: не `getReward()`, который заодно выдаёт
  награду, а `takeReward()`; не `isCompleted()` с пометкой "просмотрено", а отдельный `markViewed()`.
  Так же и наоборот: `update*`/`refresh*` без побочного эффекта вводят в заблуждение.
- **Близнецы без реальной разницы**: `Reward` / `RewardInfo` / `RewardData`,
  `getSection()` / `getSectionInfo()`. Если отличие есть — назвать само отличие
  (`sectionPreview` vs `section`); если нет — оставить одно имя. Ролевые суффиксы проекта
  (`*Data` — балансовый справочник, `*JSON`, `*Entry`, `*Config`) — не шум, а роль; шум — это
  второй класс, отличающийся от первого только словом `Info`/`Data`/`Details` без иной роли.
- **Не ищется и не произносится**: имя должно находиться grep-ом и читаться вслух на ревью.
  `genymdhms`, `clsRwdTkn` → `generatedAt`, `rewardToken`.
- **Пустые слова**: `data`, `info`, `item`, `obj`, `result`, `value`, `manager`, `helper`, `handler`,
  `process*`, `do*`, `perform*` — если имя без них не теряет смысла, убрать; если теряет — заменить
  конкретикой (`rewardTank`, а не `rewardData`).
- **Пересказ реализации** вместо смысла: `filteredSortedListOfItems` → `visibleItems`.
- **Повтор контекста**: в `CollectionSectionPopup` поле `title`, а не `collectionSectionPopupTitle`;
  метод `Collection.getId()`, а не `getCollectionId()` (но в JSON и между сущностями — `collectionId`).
- **Слишком длинные** — больше 3 слов ([#full-words](#full-words)).
  `onSellRewardButtonClickCallback` → `onSell`.
- **Отрицания в булевых**: `isVisible`, а не `isNotHidden`; `hasReward`, а не `noReward`.
- **Тип в имени**: `rewardsList`, `tankArr`, `nameStr` → `rewards`, `tanks`, `name`.
- **Синонимы для одного действия** в одной области (`fetch`/`load`/`get`, `remove`/`delete`/`clear`)
  — взять тот, что уже в области.
- Коллекции — во множественном числе (`tanks`), мапы — `<значение>By<ключ>` (`tanksById`) или как
  у соседей.
- Не переводить русские игровые термины кальками: брать английский термин из глоссария, а если его
  там нет — из кода (набор — `set`, раздел — `section`, альбом — `album`). Нового термина нет нигде —
  выбрать с пользователем и записать в глоссарий (скилл `glossary`).

## Как работать

1. Перед тем как назвать новую сущность — открыть 1–2 соседних файла той же роли и повторить их
   схему. Таблицы выше — ориентир, соседний код важнее.
2. При ревью имён — без массовых правок, отчёт списком `файл:строка — старое → новое — почему`,
   сгруппированный по важности (сверху вниз):
   - **Критично** — имя врёт о поведении (побочный эффект в `get*`/`is*`, метод делает не то,
     что написано), расхождение имени сущности между client и server.
   - **Серьёзно** — расплывчатое имя (пустые слова, близнецы без разницы, сокращение слова или
     больше 3 слов в новом коде, редкое английское слово, однобуквенное вне цикла).
   - **Мелко** — нарушение конвенции проекта (префикс, суффикс роли, регистр аббревиатуры,
     `should*` вместо `need*`).
   Публичный контракт (JSON-ключи, роуты, поля БД) в отчёте помечать отдельно: переименование
   требует правки обеих сторон и миграции.
3. Если конвенции соседей противоречат друг другу — выбрать более частую в области и сказать об
   этом пользователю одной строкой.
