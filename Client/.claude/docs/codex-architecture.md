# Кодекс — вкладка «База знаний» в профиле (клиент)

> **auto-create** — документ составлен по существующему коду (код в рамках задачи не менялся),
> 2026-10-13, сверен с кодом повторно 2026-10-14 и после merge origin/amnesia/fix 2026-10-19. Запуском не проверялось.
> Серверная сторона: `/workspace/server/.claude/docs/codex-architecture.md` (тоже auto-create).

ГДД: отсутствует (решение пользователя 2026-10-13: ГДД кодекса пока не создавать).

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

Кодекс — вкладка профиля `codex` («БАЗА ЗНАНИЙ», ключ `profileScreen.tabs.codex`): справочник всей
техники игры с отметкой, какую технику игрок уже получал. Вкладка видна только в своём профиле
(`ProfilePopup.UIContent`: `this.data.user.id === Globals.account.id`). Открыть можно кликом или через
`ProfilePopupConfig.openTab = "codex"`; таких вызовов в коде сейчас нет.

Экран в три уровня:

1. Список разделов: «ТАНКИ» и «САМОЛЕТЫ».
2. Раздел техники: кнопка «назад» и две вкладки — «ВСЕ ТАНКИ»/«ВСЕ САМОЛЕТЫ» и «В КОЛЛЕКЦИИ».
3. Сетка: блоки по рангам I–XX (`RANK = [1..20]`), в блоке строки по странам (флаг), в строке колонки по типам техники
   (танки: типы `0..3`, самолёты: `0..4`).

Правила отображения:

- **Сетка строится только по каталогу** (`data`, весь баланс). Собранное (`collectedData`) нужно лишь
  для поиска по `id`, своей сетки у него нет.
- **«ВСЕ»**: карточка-шаблон каждой техники каталога; клик открывает `TankInfoPopup`/`AirplaneInfoPopup`
  с данными шаблона.
- **«В КОЛЛЕКЦИИ»**: техника, найденная в `collected`, рисуется с её данными (уровень/звёзды), клик
  открывает инфо-попап с ними. Не найденная — шаблон под чёрным затемнением (`alpha 0.7`), не кликабельна.
- Строка страны пропускается, если в каталоге нет техники этой страны и ранга. Пустая ячейка типа —
  пустой `Layout` 64×50, чтобы колонки не съезжали.
- Порядок стран фиксирован: `COUNTRY = [8, 2, 6, 7, 4, 9, 0, 5, 3, 1]`, ранги `RANK = [1..20]` (после merge fix расширено с 1..10; спрайты шапки `tech_info/chance/1..20.png` есть).
- Счётчиков и процентов собранного нет. Push-событий кодекс не слушает: данные запрашиваются при
  каждом открытии раздела (при переключении вкладок «ВСЕ»/«В КОЛЛЕКЦИИ» — не повторяются).

<a id="references"></a>
## 2. Референсы

- Серверный контракт — `/workspace/server/.claude/docs/codex-architecture.md#client-contract`,
  `#cls-codexpage`.
- Карточки техники — `ItemsPresets.createTankLayout`/`createAirplaneLayout`
  (`items-presets-architecture.md`).
- `CodexTabSelector` — копия `src/views/home_screen/popups/rating/RatingTabSelector.ts` без текстур
  фона вкладки ([#tradeoffs](#tradeoffs), п.4).

<a id="patterns"></a>
## 3. Паттерны

- **Секция в слоте.** `ProfilePopup` → `CodexSection` → `CodexListSection` / `CodexTanksSection` /
  `CodexAirplanesSection`; каждая следующая кладётся в `LayoutSlot` родителя (`slot.put` +
  `refreshForce` + `start`), как в `CollectionsSection`/`AchievementsSection`.
- **`PreloadableLayout` с запросом в `onPreload`.** Запрос в `onPreload`, по ответу `preloadCompleted()`,
  при ошибке `preloadFailed()`; UI строится в `onCreate`.
- **Ассеты.** Атлас `codex_screen` (пакет `CodexScreen`) грузится в `ProfilePopup.loadAssets` вместе
  с остальными пакетами профиля; спрайты — `Creator.sprite("atlas/codex_screen/...")`. Процедура —
  `asset-packaging.md`.

<a id="class-list"></a>
## 4. Список классов

В `src/views/home_screen/popups/profile/codex/`: `CodexSection`, `CodexListSection`,
`CodexTanksSection` (+ внутренний `Tanks`), `CodexAirplanesSection` (+ внутренний `Airplanes`),
`CodexTabSelector` (+ интерфейс `CodexTabConfig`).

За пределами папки:

- `profile/ProfilePopup.ts` — вкладка, `showCodex()`, загрузка пакета `CodexScreen`, ветка `openTab`. После merge fix попап дополнительно грузит данные клана и пакет `ClanEmblems` и вызывает `pushHeaderZIndex(false)` (область кланов здесь не документируется).
- `profile/RewardsSection.ts` — берёт `CodexSection.TAB_NAME` для заголовка ([#tradeoffs](#tradeoffs), п.5).
- Типы — общие `TankJSON`/`AirplaneJSON` из `popups/bag/bag.d.ts`; своего domain `*.d.ts` нет.
- Локализация — `codexScreen.*` в `assets-src/raw/lang/<locale>/<locale>.json`.

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#references`, `#patterns`, `#class-list`, `#class-nav`, `#classes`, `#cls-codexsection`,
`#cls-codexlistsection`, `#cls-codextankssection`, `#cls-tanks`, `#cls-codexairplanessection`,
`#cls-codextabselector`, `#client-contract`, `#tradeoffs`, `#duplicates`, `#gdd-link`, `#file-map`.

<a id="class-nav"></a>
## 6. Оглавление по классам

[`CodexSection`](#cls-codexsection) · [`CodexListSection`](#cls-codexlistsection) ·
[`CodexTanksSection`](#cls-codextankssection) · [`Tanks`](#cls-tanks) ·
[`CodexAirplanesSection` и `Airplanes`](#cls-codexairplanessection) ·
[`CodexTabSelector`](#cls-codextabselector) · [Контракт с сервером](#client-contract)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-codexsection"></a>
### `CodexSection` (`extends PreloadableLayout`)

Корень вкладки. `static TAB_NAME = "codex"`; конструктор ставит заголовок попапа и открывает список.
`showList()`, `showTanks()`, `showAirplanes()` кладут в слот соответствующую секцию; назад из раздела
техники — `showList()`.

<a id="cls-codexlistsection"></a>
### `CodexListSection` (`extends PreloadableLayout`)

Две плитки-кнопки 355×85 (`tanks.png`/`airplanes.png`, тень, подпись `codexScreen.tanks`/`airplanes`);
клик вызывает `section.showTanks()`/`showAirplanes()`.

<a id="cls-codextankssection"></a>
### `CodexTanksSection` (`extends PreloadableLayout`)

Кнопка «назад», линия, `CodexTabSelector` с вкладками `tab0` («ВСЕ ТАНКИ», активна) и `tab1`
(«В КОЛЛЕКЦИИ»), слот под сетку. Публичные `data: TankJSON[]` (каталог) и `collectedData: TankJSON[]`
(собранное) читает внутренний `Tanks`.

- `onPreload()` — `/ingame/codex/tanks`, `data = response.tanks`, `collectedData = response.collected`
  если поле есть; ошибка → `preloadFailed()`.
- `onCreate()` → `showAll()`; `showAll()`/`showCollected()` (private) пересоздают `Tanks` с типом
  `"all"`/`"collected"` в слоте.
- Обработчик `Layout.EVENT_AFTER_REFRESH` в конструкторе раскладывает вкладки по ширине (две по 86).

<a id="cls-tanks"></a>
### `Tanks` (внутренний, `extends PreloadableLayout`)

Сетка в вертикальном `ScrollableArea`. `type: "all" | "collected"` (тип поля `string`).

- `onCreate()` — скролл и `UI()` внутри; `UI()` — блок на каждый ранг из `RANK`.
- `UIRank(rank)` — шапка (полоса `atlas/tech_info/chance/<rank>.png`, римская цифра, иконки и подписи
  четырёх типов), затем строки стран из `COUNTRY`; страна пропускается, если `getTanks(country, rank, -1)`
  пуст; линия ставится перед строкой с индексом в `COUNTRY` > 0.
- `UITanks(country, rank, type)` — колонка карточек ячейки; пустая — `Layout` 64×50.
- `UITank(tank)` — карточка, поведение по вкладкам описано в [#purpose](#purpose): при `"collected"`
  ищет `getCollectedTank(tank.id)`.
- `getTanks(country, rank, type)` — фильтр каталога, `type = -1` — любой тип.
- `getCollectedTank(id)` — первая запись `collectedData` с этим `id` или `null`
  ([#duplicates](#duplicates)).
- `UIRankLine`, `UIRankName`, `UIType` — элементы шапки ранга.

<a id="cls-codexairplanessection"></a>
### `CodexAirplanesSection` и внутренний `Airplanes`

Копия `CodexTanksSection`/`Tanks` с заменой танка на самолёт (методы `UIAirplanes`/`UIAirplane`/
`getAirplanes`/`getCollectedAirplane`). Отличия:

- роут `/ingame/codex/airplanes`, каталог из `response.airplanes`; вкладка `codexScreen.aAirplanes`;
- пять колонок типов (`0..4`, подписи `airplanes.typeS.<type>`, иконки `tech_info/airplanes/type`),
  колонка флага и ячейка типа 30 px вместо 64;
- карточки `ItemsPresets.createAirplaneLayout`, попап `AirplaneInfoPopup.publish(screen, data, {})`
  (у танков `TankInfoPopup.publish(screen, { data })`).

<a id="cls-codextabselector"></a>
### `CodexTabSelector`

Ряд текстовых вкладок без фона (`MLRLayout` 100×38, два текста: серый обычный и белый выбранный; размер шрифта по умолчанию 10).
`CodexTabConfig`: `textKey`, `selectedTextKey?`, `onClick`, `active?`, `name?`, `fontSize?`, свои
`RichTextBuilder`. Ширину и позиции вкладок задаёт вызывающий раздел (публичный `tabs`).

- `activateTab(tabName)` — выделяет вкладку по имени, снимает выделение с остальных.
- `UITab(config)` (private) — создаёт вкладку; клик переключает выделение и вызывает `config.onClick`.
- `selectTab`/`unselectTab` (private) — видимость текстов; `view()` — корневой `Layout`.

<a id="client-contract"></a>
### Контракт с сервером

Запросы без параметров:

- `/ingame/codex/tanks` → `{ tanks: TankJSON[], collected?: TankJSON[] }`;
- `/ingame/codex/airplanes` → `{ airplanes: AirplaneJSON[], collected?: AirplaneJSON[] }`.

Клиент использует `id`, `country`, `rank`, `type` для раскладки; остальное уходит в пресет карточки и
инфо-попап как есть. Ответ `sendRequest` типизирован `any`. Push-событий нет. Сервер:
`/workspace/server/.claude/docs/codex-architecture.md#client-contract`.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

<a id="duplicates"></a>
1. **Повторы в `collected` (серверный баг,
   `/workspace/server/.claude/docs/codex-architecture.md#bug-duplicates`).** Клиент дубли не рисует и
   не считает: сетка идёт по каталогу, `getCollectedTank`/`getCollectedAirplane` берёт первую запись с
   нужным `id`. Следствие одно: при дублях на карточке и в инфо-попапе показывается запись, идущая в
   ответе первой, а она не обязательно лучшая по мощности. Исправлять на сервере.
2. **Две копии одной логики.** `CodexTanksSection`+`Tanks` и `CodexAirplanesSection`+`Airplanes`
   почти построчно совпадают. Правила «сетка ранг × страна × тип», «вкладка собранного» и «поиск
   собранного по `id`» выражены дважды. Кандидат на один параметризованный класс.
3. **Без domain-типа ответа.** Форма `{ tanks, collected }` нигде не описана, ответ — `any`.
4. **Ещё одна копия селектора вкладок.** `CodexTabSelector` повторяет `RatingTabSelector` без
   текстур; рядом `src/shared/TabSelector.ts` и `CollectionTabSelector`; после merge fix у `CodexTabSelector`, `ProfileTabSelector` и `shared/TabSelector` размер шрифта по умолчанию 10 вместо 12.
5. **`RewardsSection` — неиспользуемый код с заголовком кодекса.** Класс нигде не создаётся
   (`TAB_NAME = "rewards"`, заглушка «скоро»), но ставит заголовок `profileScreen.tabs.codex`.
   Кандидат на удаление.
6. **Двойной перевод подписей вкладок.** Разделы передают в `textKey` уже переведённую строку, а
   `CodexTabSelector.UITab` переводит её ещё раз. Работает за счёт фолбэка `I18n.translate`, который
   возвращает ключ, если перевод не найден.
7. **Линия-разделитель по индексу константы.** Условие `i !== 0` проверяет индекс в `COUNTRY`, а не
   «уже нарисована строка»: если у ранга нет техники страны `8`, линия появится и над первой видимой
   строкой.
8. **Жёсткие списки.** Страны, ранги `1..20` и число типов зашиты константами. Техника вне списков в
   сетку не попадёт; при типе вне `0..3`/`0..4` строка страны может выйти пустой, потому что её
   наличие проверяется по любому типу.
9. **Ошибка запроса.** Раздел вызывает `preloadFailed()`; своего сообщения кодекс не показывает.
10. **Нет английской локализации.** В `assets-src/raw/lang/en/en.json` нет ключей `codexScreen.*` и
    `profileScreen` (только в `ru.json`), поэтому в английской локали заголовки вкладки и разделов
    кодекса не переведены. Решение пользователя 2026-10-13: только зафиксировать, код не менять.
    Повторно подтверждено 2026-10-14.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: отсутствует (решение пользователя 2026-10-13). Правила для будущей связи: «что показывает
каталог» ([`Tanks.UI`/`UIRank`](#cls-tanks)), «что считается собранным и как отображается»
([`UITank`](#cls-tanks)), «кодекс виден только в своём профиле» ([#purpose](#purpose)).

<a id="file-map"></a>
## 10. Карта файлов компонента

Полнота проверена `grep` по `CodexSection|CodexListSection|CodexTanksSection|CodexAirplanesSection|CodexTabSelector|codexScreen|CodexScreen|codex_screen`.

### Файлы прямого влияния

- `src/views/home_screen/popups/profile/codex/CodexSection.ts` — корень вкладки, `TAB_NAME`, переключение уровней.
- `src/views/home_screen/popups/profile/codex/CodexListSection.ts` — выбор раздела (танки/самолёты).
- `src/views/home_screen/popups/profile/codex/CodexTanksSection.ts` — раздел танков, внутренний `Tanks`, запрос `/ingame/codex/tanks`.
- `src/views/home_screen/popups/profile/codex/CodexAirplanesSection.ts` — раздел самолётов, внутренний `Airplanes`, запрос `/ingame/codex/airplanes`.
- `src/views/home_screen/popups/profile/codex/CodexTabSelector.ts` — вкладки «ВСЕ» / «В КОЛЛЕКЦИИ».
- `assets-src/atlas/codex_screen/` (`tanks.png`, `airplanes.png`, `section_tab_shadow.png`) — графика пакета `CodexScreen`.

### Файлы косвенного влияния

- `src/views/home_screen/popups/profile/ProfilePopup.ts` — вкладка, `showCodex()`, загрузка пакета `CodexScreen`, ветка `openTab`; `ProfileTabSelector.ts` — соседний селектор вкладок профиля.
- `src/views/home_screen/popups/profile/RewardsSection.ts` — берёт `CodexSection.TAB_NAME` для заголовка ([#tradeoffs](#tradeoffs), п.5).
- `assets-src/raw/lang/ru/ru.json` — общий файл локализации; кодексу принадлежат ключи `codexScreen.*`.
- `src/views/home_screen/popups/bag/bag.d.ts` — зависимость: общие типы `TankJSON`/`AirplaneJSON`.
- `tools/src/config.yaml` — общий конфиг паковки; кодексу принадлежит запись пакета `CodexScreen` (путь `codex_screen`).
