# Документация утилит "PanelsPresets" и "ButtonPresets" (стандартные фон-панель и кнопка UI)

Составлено по прямому запросу пользователя (не auto-create): "изучи и сделай документацию на
PanelsPresets и ButtonPresets с пометкой на то что в CollectionUtils есть функции button и
panelPreset для аналогичного использования но в новом графическом дизайне" (2026-09-25). Классы лежат
в `src/presets/PanelsPresets.ts` (82 строки) и `src/presets/ButtonPresets.ts` (315 строк).

Оба класса не принадлежат одной области (используются практически во всём проекте — welcome-экране,
попапах профиля/достижений/боя, экране боя и т.д.), своей подпапки в `src/views/...` и своего domain
`*.d.ts` у них нет — постоянный агент-аналитик под эту область не создавался (решение
`client-analyst-lead`, организационный вопрос, аналогично `ItemsPresets`, не требует подтверждения
пользователем).

**Важное отличие от объёма документации `ItemsPresets`:** `PanelsPresets`/`ButtonPresets` используются
в 139 местах в 38 файлах (`grep -rn "PanelsPresets\.\|ButtonPresets\." src`, 2026-09-25) — это
стандартный способ создать окно попапа/кнопку почти в любом UI-компоненте проекта. Полный построчный
список call sites сюда не включён (малополезен и дорог по контексту) — вместо него в разделе 3
описан паттерн использования и приведено несколько показательных примеров.

**Разделы:** [1. Описание](#s1) · [2. Референсы](#s2) · [3. Паттерны](#s3) ·
[4. Список классов](#s4) · [6. Оглавление по классам](#s6) · [7. Классы и методы](#s7) ·
[8. Компромиссы и открытые решения](#s8) · [10. Карта файлов](#s10)

## 1. Краткое описание: назначение и бизнес-логика {#s1}

`PanelsPresets` и `ButtonPresets` — два независимых статических класса-набора пресетов для отрисовки
двух самых частых UI-примитивов проекта: фон окна/панели/разделителя и кнопка с текстом. Оба
используют общий графический стиль `atlas/ui/panels/*` / `atlas/ui/buttons/*` (условно "стандартный"/
"общий" дизайн — в противовес дизайну экрана коллекций, см. ниже).

- **`PanelsPresets`** — три рабочих пресета фона: окно с рамкой и шапкой (`PNL_WINDOW_STANDARD`), то же без
  шапки (`PNL_WINDOW_STANDARD_NO_HEADER`), тонкая горизонтальная линия-разделитель (`HR`). Используется
  практически в каждом попапе проекта как источник фонового `BorderPanel`.
- **`ButtonPresets`** — четыре цветных варианта MLR-кнопки (`BTN_DEFAULT`/`BTN_GREEN`/`BTN_GREY`/
  `BTN_RED`) и отдельный пресет кнопки оплаты (`BTN_PAYMENT`), плюс публичные утилиты для изменения уже
  созданной кнопки (текст, цвет, текстура, интерактивность).

**Пометка про аналог в другом графическом дизайне (прямое требование задачи):** в
`src/utils/CollectionUtils.ts` (см. `.claude/docs/collections-architecture.md#cls-collectionutils`)
есть функции `CollectionUtils.button(config)` и `CollectionUtils.panelPreset(type, config)` —
функциональные аналоги `ButtonPresets.BTN_*` и `PanelsPresets.PNL_WINDOW_STANDARD*`/`HR` для
АНАЛОГИЧНОГО использования (кнопка с текстом; фон окна с шапкой/без шапки/разделитель — у
`panelPreset` даже есть свой `enum PanelPresetType` с теми же тремя именами `PNL_WINDOW_STANDARD`/
`PNL_WINDOW_STANDARD_NO_HEADER`/`HR`), но в НОВОМ графическом дизайне экрана коллекций: ассеты
`atlas/collection/collections_screen/pallets/btn_orange.png`/`btn_disable.png` (кнопка, через `Slice9`) и
`atlas/collection/collections_screen/pallets/popop_bg.png`/`popup_header.png` (панель, тоже через `Slice9`, а
не `BorderPanel`) вместо общих `atlas/ui/buttons/*`/`atlas/ui/panels/*`. Это две независимые
реализации одной и той же задачи — `CollectionUtils.button`/`panelPreset` НЕ наследуют и НЕ оборачивают
`ButtonPresets`/`PanelsPresets`, между классами нет ни вызовов друг друга, ни общего кода. Подробности
аналогов — раздел 8.

## 2. Использованные референсы {#s2}

Нет — документ составлен по существующему коду, без привязки к конкретной фиче/референсу.

## 3. Использованные паттерны {#s3}

- **Пресет-класс без состояния** — оба класса полностью `static`, не инстанцируются, поведение
  определяется входным конфигом (`PanelPresetsConfig`/`ButtonPresetsOptions`) и опциональными полями
  `LayoutConstructorConfig`.
- **`ObjectUtils.propMerge`** — стандартный способ слить дефолтные поля пресета (ассеты рамки/фона) с
  переданным конфигом, конфиг переопределяет дефолты. Используется и в `PanelsPresets`
  (`PNL_WINDOW_STANDARD`), и в приватном `btnBuilder` (`ButtonPresets`, ветка `borderPanel`).
- **`BorderPanel` как фон 9-slice через набор из 9 спрайтов** — `PanelsPresets` (оба `PNL_WINDOW_*`) и
  `ButtonPresets.btnBuilder` (ветка `options.borderPanel === true`, используется только у
  `BTN_PAYMENT`... фактически `BTN_PAYMENT` использует MLR, см. раздел 7) собирают фон из угловых/
  боковых/центрального спрайтов через общий класс `src/ee/display/BorderPanel`.
- **`MLRLayout` (Middle-Left-Right) для кнопок** — все `BTN_*`, кроме ветки `borderPanel`, собираются
  как растягиваемая по ширине кнопка из трёх спрайтов (левый край, растянутая середина, правый край) —
  паттерн для любой кнопки переменной ширины под текст произвольной длины.
- **Общий приватный билдер + публичные тонкие обёртки** — `ButtonPresets.btnBuilder` (private) содержит
  всю реальную логику сборки кнопки; `BTN_DEFAULT`/`BTN_GREEN`/`BTN_GREY`/`BTN_RED`/`BTN_PAYMENT` —
  тонкие публичные обёртки, отличающиеся только набором текстур и (у трёх из четырёх) добавлением
  запасной серой текстуры через `addTextures`. В отличие от `ItemsPresets`
  (`.claude/docs/items-presets-architecture.md#s3`), где диспетчер продублирован, здесь общая логика
  вынесена в один приватный метод — дублирования нет (см. раздел 8 про почти идентичные тела самих
  публичных методов).
- **Авто-resize кнопки по ширине текста** — если `options.width` не передан явно, `btnBuilder`
  подписывается на `Layout.EVENT_BEFORE_REFRESH` и выставляет `layout.width` по фактической ширине
  текста (`textContent.width + EMPTY_SPACE_CONTENT`, но не меньше дефолтной ширины и не больше
  `App.width`).
- **Доступ к уже созданной кнопке по имени child-а** — `updateText`/`updateColor`/`chanceTexture`/
  `updateInteractive`/`getText` не хранят ссылку на билдер, а находят нужный `child` в уже собранном
  `Layout` по строковому имени (`"btn._btnText_"`, `"btn"`, `"_btnText_"`) и переприменяют
  `refreshForce()`. Требует, чтобы имена не разъезжались с именами, заданными при сборке в
  `btnBuilder`/публичных `BTN_*`.
- **Стандартный способ использования (без перечисления всех call sites)** — почти любой попап
  собирает фон через `PanelsPresets.PNL_WINDOW_STANDARD`/`PNL_WINDOW_STANDARD_NO_HEADER` (пример:
  `src/views/welcome_screen/RecoveryPasswordPopup.ts:56`, `src/views/popups/
  AchievementCompletePopup.ts:31` — вариант с `NO_HEADER` и `alpha`), а кнопку — через
  `ButtonPresets.BTN_DEFAULT`/`BTN_GREEN` (пример: `src/views/welcome_screen/WelcomeScreen.ts:28,38` —
  кнопки логина/старта игры; `src/views/battlefield_screen/BattlefieldScreen.ts` — несколько
  `BTN_DEFAULT` плюс использование `chanceTexture`/`updateInteractive` для переключения состояния уже
  созданных кнопок). Итого 139 обращений в 38 файлах на 2026-09-25.

## 4. Полный список классов {#s4}

- `src/presets/PanelsPresets.ts` — `class PanelsPresets` (default export, единственный класс файла).
- `src/presets/ButtonPresets.ts` — `class ButtonPresets` (default export, единственный класс файла).

## 5. Ссылки для навигации {#s5}

См. якоря в оглавлении разделов выше и в п.6 ниже (`#cls-panelspresets`, `#cls-buttonpresets`,
`#collectionutils-analog`).

## 6. Оглавление по классам {#s6}

- [PanelsPresets](#cls-panelspresets)
- [ButtonPresets](#cls-buttonpresets)

## 7. Классы и методы {#s7}

### PanelsPresets {#cls-panelspresets}

- **`public static PNL_WINDOW_STANDARD(config: PanelPresetsConfig): BorderPanel`** — стандартное окно
  с рамкой и "шапкой" (визуально не отдельный слот, а часть общей 9-slice текстуры `atlas/ui/panels/0/
  *`: `lt`/`rt`/`lb`/`rb` — углы, `mt`/`lm`/`mb`/`rm` — стороны, `m` — центр, все `scale(0.5)`).
  Дефолт 370×200, высота не может быть меньше 200 (`Math.max`). Строка `config.width = Math.max(...)`
  для ширины закомментирована в коде — ширина сейчас ничем не ограничена снизу.
- **`public static PNL_WINDOW_STANDARD_NO_HEADER(config: PanelPresetsConfig): BorderPanel`** — то же
  самое, но ассеты `atlas/ui/panels/1/*` (вариант без шапки) и поддержка `config.alpha` (по умолчанию
  1, применяется к каждому из 9 спрайтов через `setAlpha`). Дефолт ширины/высоты применяется только
  если не заданы ни `width`/`pwidth`, ни `height`/`pheight` соответственно (в отличие от
  `PNL_WINDOW_STANDARD`, где проверяется только `width`/`height`, без `pwidth`/`pheight`).
- **`public static HR(config: PanelPresetsConfig): Layout`** — горизонтальный разделитель: `Layout` с
  одним `Creator.spriteWhite()`, растянутым до `config.width` по ширине и высотой 1px, тонированным в
  `Const.COLOR_WINDOW_HR`, с опциональной `config.alpha` (дефолт 1).
- **`public static PNL_TEST(config: LayoutConstructorConfig): Slice9`** — заготовка из merge
  `amnesia/fix`: `Slice9` с пустой `texture` и бордерами 26, дефолт 370×200. Вызовов в `src` нет —
  кандидат на удаление (см. [#s8](#s8)).

### ButtonPresets {#cls-buttonpresets}

- **`public static readonly Size = { BIG: "BIG" }`** / **`private static readonly Dimensions = { BIG:
  { width: 143, height: 44 } }`** — единственный именованный размер кнопки на 2026-09-25; передаётся
  через `options.size` вместо явных `width`/`height`.
- **`public static BTN_DEFAULT(options): Layout`** — синяя кнопка (`atlas/ui/buttons/blue/{m,l,r}
  .png`). Дополнительно добавляет в `addTextures` серый вариант (`atlas/ui/buttons/grey/*`) — запасная
  текстура с индексом 1 для последующего переключения через `chanceTexture(button, 1)` (используется
  как "визуально задизейбленное" состояние, см. пример `BattlefieldScreen.ts`).
  Оборачивает результат `btnBuilder` в дополнительный `Layout` и сдвигает на `y: 2` — комментарий в
  коде: "Кнопка имеет тень, поэтому её нужно выровнять по центру".
- **`public static BTN_GREEN(options): Layout`** — зелёная кнопка (`atlas/ui/buttons/green/*`),
  структурно идентична `BTN_DEFAULT` (тот же серый запасной вариант, тот же сдвиг `y: 2`).
- **`public static BTN_GREY(options): Layout`** — серая кнопка (`atlas/ui/buttons/grey/*`),
  структурно идентична, но БЕЗ добавления запасной серой текстуры (она и так серая) — единственное
  отличие от `BTN_DEFAULT`/`BTN_GREEN`/`BTN_RED`.
- **`public static BTN_RED(options): Layout`** — красная кнопка (`atlas/ui/buttons/red/*`), структурно
  идентична `BTN_DEFAULT`/`BTN_GREEN` (тот же серый запасной вариант, тот же сдвиг).
- **`public static BTN_PAYMENT(options): MLRLayout`** — отдельный пресет для кнопок оплаты
  (`atlas/ui/payment/btn-{m,l,r}.png`, дефолт 159×59). В отличие от `BTN_*` выше, возвращает результат
  `btnBuilder` НАПРЯМУЮ (без оборачивающего `Layout` и сдвига по тени) и без запасной текстуры.
- **`private static btnBuilder(sprites, options): MLRLayout | BorderPanel`** — общая сборка тела любой
  кнопки: `MLRLayout` из 3 спрайтов (обычный путь) либо `BorderPanel` из 9 спрайтов (если
  `options.borderPanel === true`; на 2026-09-25 ни один публичный `BTN_*` эту ветку не использует —
  все передают ровно 3 спрайта). Дальше: применение `addTextures` (запасные текстуры для
  `chanceTexture`), текст (см. ниже), авто-resize по ширине текста, `icon`, обёртка в `Button.newButton`
  при наличии `onClick`, звук клика через `setClickSound`.
  - Текст строится через `options.textBuilder` / `options.richTextBuilder` / `options.textKey`
    (взаимоисключающе, в этом порядке приоритета) — во всех трёх случаях текст приводится к
    верхнему регистру (`.toUpperCase()`/`rtf.toUpperCase()`) перед сборкой, добавляется в layout под
    именем `_btnText_`.
  - Если ни один из трёх вариантов текста не передан — кнопка собирается без текста (`textContent`
    остаётся `undefined`, ветка авто-resize пропускается).
- **`private static formatTextBuilder(textBuilder, size): TextBuilder`** — если `textBuilder` не
  передан, создаёт дефолтный (`Const.FONT_MEDIUM` = `Roboto-Medium`, `dropShadow`, `outlineColor #8f8989`, размер 25 — только
  для `Size.BIG`, единственного существующего размера). Если `textBuilder` уже передан — возвращает
  его без изменений (готовые кастомные стили не переопределяются).
- **`public static updateText(button: Layout, newText: string, images?: string[])`** — меняет текст уже
  созданной кнопки (ищет child `"btn._btnText_"`). Для `MultiStyleTextWithImages` дополнительно умеет
  подменять вложенные картинки-иконки по индексу (`images`). Не делает `refreshForce`, если новый текст
  совпадает со старым (оптимизация). Логирует ошибку и молча выходит, если child не найден.
- **`public static updateColor(button: Layout, color: string)`** — меняет `tint` текста кнопки
  (`Const.hexStrToNum`), затем `refreshForce`.
- **`public static chanceTexture(button: Layout, index: number)`** — переключает текстуру фона кнопки
  по индексу (через `child("btn").changeTexture(index)` — метод `MLRLayout`/`BorderPanel`, не
  документируется здесь как чужой API), затем `refreshForce`. Индекс 0 — исходная текстура, 1+ —
  текстуры, добавленные через `addTextures` при сборке (см. `BTN_DEFAULT`/`BTN_GREEN`/`BTN_RED`,
  запасная серая).
- **`public static updateInteractive(button: Layout, value: boolean)`** — включает/выключает
  интерактивность child-а `"btn"` (`setInteractive`).
- **`public static getText(button: Layout): PIXI.Text`** — возвращает текстовый child по имени
  `"_btnText_"` (без родительского `"btn."` в пути, в отличие от `updateText`/`updateColor` — расхождение
  в написании пути, но `Layout.child` ищет по имени рекурсивно, поэтому оба варианта попадают в один и
  тот же узел).

## 8. Принятые компромиссы и открытые решения {#s8}

- **`PanelsPresets.PNL_TEST` не используется** — пришёл с merge `amnesia/fix`, вызовов в `src` нет,
  `texture` пустая. Кандидат на удаление; решение — за автором ветки/пользователем.
- **Четыре `BTN_*`-метода почти дословно дублируют друг друга** — `BTN_DEFAULT`/`BTN_GREEN`/`BTN_GREY`/
  `BTN_RED` содержат идентичный код вычисления `width`/`height` по `options.size`/`Dimensions.BIG` и
  идентичную обёртку `Layout` со сдвигом `y: 2` — различается только выбор цветных текстур (и то, что
  `BTN_GREY` не добавляет запасную серую текстуру, а остальные три — добавляют). Общий приватный метод
  для этой части (в отличие от уже вынесенного `btnBuilder`) отсутствует. Наблюдение по коду, не оценка
  "хорошо/плохо".
- **`btnBuilder` поддерживает ветку `borderPanel`, но она не используется** — код сборки кнопки через
  `BorderPanel` (9 спрайтов) присутствует и рабочий, но ни один из существующих публичных `BTN_*`
  методов на 2026-09-25 её не вызывает (`options.borderPanel` нигде не передаётся `true` среди текущих
  пресетов). Мёртвая для текущих пресетов, но публично достижимая через прямой вызов `btnBuilder`
  извне невозможна — метод `private`.
- **`getText` и `updateText`/`updateColor` ищут child по разным путям** (`"_btnText_"` vs
  `"btn._btnText_"`) — работает одинаково благодаря рекурсивному поиску `Layout.child`, но
  несогласованность в написании может ввести в заблуждение при будущих правках.
- **Аналог в графическом дизайне экрана коллекций** {#collectionutils-analog} — `src/utils/
  CollectionUtils.ts` (см. `.claude/docs/collections-architecture.md#cls-collectionutils`) содержит
  `button(config: buttonConfig): Layout` и `panelPreset(type: PanelPresetType, config): Layout` —
  независимые, не связанные наследованием/делегированием аналоги `ButtonPresets.BTN_*` и
  `PanelsPresets.PNL_WINDOW_STANDARD`/`PNL_WINDOW_STANDARD_NO_HEADER`/`HR` для решения той же задачи
  (кнопка с текстом; фон окна с шапкой/без шапки/разделитель) в графическом стиле экрана коллекций:
  - `CollectionUtils.button` — через `Slice9` (не `MLRLayout`/`BorderPanel`), текстуры `atlas/
    collection/collections_screen/pallets/btn_orange.png` (активна) / `btn_disable.png` (задизейблена, порог
    задаётся отдельным параметром `config.type === "disable"`, а не запасной текстурой через
    `addTextures`, как у `ButtonPresets.chanceTexture`). Смена состояния — не аналог `chanceTexture`
    напрямую, а отдельный метод `CollectionUtils.buttonStatus(layout, status)`, переключающий и
    интерактивность, и текстуру фона одним вызовом (у `ButtonPresets` это два отдельных вызова:
    `updateInteractive` + `chanceTexture`).
  - `CollectionUtils.panelPreset` — тоже через `Slice9`, свой `enum PanelPresetType` с именами
    `PNL_WINDOW_STANDARD`/`PNL_WINDOW_STANDARD_NO_HEADER`/`HR`, повторяющими имена методов
    `PanelsPresets`; текстуры `atlas/collection/collections_screen/pallets/popop_bg.png` (фон) и
    `popup_header.png` (шапка, только у варианта с шапкой). Логика дефолтных `width`/`height` и
    `Math.max(height, 200)` в ветке `PNL_WINDOW_STANDARD` скопирована почти дословно из
    `PanelsPresets.PNL_WINDOW_STANDARD` (тот же дефолт 370×200), ветка `HR` — дословно идентична
    `PanelsPresets.HR` (тот же `Creator.spriteWhite()` + `Const.COLOR_WINDOW_HR`).

  Вызываются в области "Коллекции" (`CollectionSectionPopup` — `panelPreset`,
  `CollectionsUSSROperationsSection` — `button`) и в окне профиля `ProfilePopup` (`panelPreset`,
  фон окна `PNL_WINDOW_STANDARD`), которое содержит вкладку коллекций. Замены общих
  `ButtonPresets`/`PanelsPresets` в остальном проекте не предполагают.

## 10. Карта файлов компонента {#s10}

Полнота проверена 2026-10-19 (после merge `amnesia/fix`): `grep -rlE "\b(PanelsPresets|ButtonPresets)\b" src` — 46 файлов, каждый
ниже; в скобках — какие методы пресетов файл вызывает.

**Файлы прямого влияния**

- `src/presets/PanelsPresets.ts` — пресеты фона окна попапа и разделителя (`PNL_WINDOW_STANDARD`, `PNL_WINDOW_STANDARD_NO_HEADER`, `HR`).
- `src/presets/ButtonPresets.ts` — пресеты кнопок (`BTN_*`) и утилиты состояния кнопки (`updateInteractive`, `chanceTexture`, текст).

**Файлы косвенного влияния**

- `src/views/welcome_screen/WelcomeScreen.ts` — кнопки стартового экрана (`BTN_DEFAULT`/`BTN_GREEN`).
- `src/views/welcome_screen/LoginPopup.ts` — окно входа: фон окна и кнопка (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`).
- `src/views/welcome_screen/RecoveryPasswordPopup.ts` — окно восстановления пароля: фон окна и кнопка (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`).
- `src/views/battlefield_screen/BattlefieldScreen.ts` — кнопки экрана боя с переключением доступности (`BTN_DEFAULT`, `updateInteractive`, `chanceTexture`).
- `src/views/home_screen/popups/battlefield/BattlefieldPopup.ts` — попап боя: разделители и кнопки с переключением доступности (`HR`, `BTN_DEFAULT`/`BTN_GREEN`, `updateInteractive`, `chanceTexture`).
- `src/views/home_screen/popups/military_base/MilitaryBaseAviationFactoryInfoPopup.ts` — инфо авиазавода военной базы (область без дока): разделитель (`HR`).
- `src/views/home_screen/popups/military_base/MilitaryBaseHeadquartersInfoPopup.ts` — инфо штаба военной базы (область без дока): разделитель (`HR`).
- `src/views/home_screen/popups/clan/ClanPopup.ts` — окно кланов (область без дока): кнопки с переключением доступности (`BTN_DEFAULT`, `updateInteractive`, `chanceTexture`).
- `src/views/home_screen/popups/clan/ClanInfoPopup.ts` — информация о клане (область без дока): фон, разделитель, кнопки с переключением доступности (`PNL_WINDOW_STANDARD`, `HR`, `BTN_DEFAULT`, `updateInteractive`, `chanceTexture`).
- `src/views/home_screen/popups/clan/ClanUserProfilePopup.ts` — профиль участника клана (область без дока): фон и кнопка (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`).
- `src/views/home_screen/popups/campaign/CampaignRankedHistory.ts` — история рейтинговых боёв кампании (область без дока): фон окна (`PNL_WINDOW_STANDARD`).
- `src/views/home_screen/popups/mailbox/content/MailboxClanInviteMessage.ts` — письмо-приглашение в клан: кнопки (`BTN_DEFAULT`/`BTN_GREEN`).
- `src/views/home_screen/popups/profile/ProfileSection.ts` — вкладка профиля: кнопка (`BTN_DEFAULT`).
- `src/views/popups/ConfirmPopup.ts` — общее окно подтверждения: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`/`BTN_GREEN`).
- `src/views/home_screen/popups/train/TrainAutoSummonPopup.ts` — автопризыв поезда: фон и кнопка (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`).
- `src/views/home_screen/popups/train/TrainBuySchemesPopup.ts` — покупка схем поезда: фон, разделитель, кнопка (`PNL_WINDOW_STANDARD`, `HR`, `BTN_GREY`).
- `src/views/home_screen/popups/train/TrainUpgradePopup.ts` — улучшение поезда: фон и разделитель (`PNL_WINDOW_STANDARD`, `HR`).
- `src/views/home_screen/popups/assembly/AssemblyPopup.ts` — попап сборки: фон, разделители, кнопка (`PNL_WINDOW_STANDARD`, `HR`, `BTN_GREEN`).
- `src/views/home_screen/popups/airplane/AirplaneGetPopup.ts` — получение самолёта: кнопки (`BTN_DEFAULT`/`BTN_GREEN`/`BTN_RED`).
- `src/views/home_screen/popups/tank/TankGetPopup.ts` — получение танка: кнопки (`BTN_DEFAULT`/`BTN_GREEN`/`BTN_RED`).
- `src/views/home_screen/popups/idle/IdlePopup.ts` — idle-награды: фон, разделители, кнопка (`PNL_WINDOW_STANDARD`, `HR`, `BTN_GREEN`).
- `src/views/home_screen/popups/campaign/CampaignLevelRewardsPopup.ts` — награды уровня кампании: фон окна (`PNL_WINDOW_STANDARD`).
- `src/views/home_screen/popups/rating/RatingPopup.ts` — рейтинг: фон окна (`PNL_WINDOW_STANDARD`).
- `src/views/home_screen/popups/banPanel/BanPanelPopup.ts` — бан-панель: фон и кнопки с переключением доступности (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`/`BTN_GREEN`, `updateInteractive`, `chanceTexture`).
- `src/views/home_screen/popups/banPanel/BanReaskPopup.ts` — подтверждение бана: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_GREEN`/`BTN_RED`).
- `src/views/home_screen/popups/banPanel/PlayerInfoPopup.ts` — информация об игроке: фон без шапки (`PNL_WINDOW_STANDARD_NO_HEADER`).
- `src/views/home_screen/popups/mailbox/popups/AddToBlacklistPopup.ts` — подтверждение добавления в чёрный список: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`/`BTN_RED`).
- `src/views/home_screen/popups/mailbox/popups/AddToFriendsPopup.ts` — подтверждение добавления в друзья: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`/`BTN_RED`).
- `src/views/home_screen/popups/mailbox/popups/DeleteFromBlacklistPopup.ts` — подтверждение удаления из чёрного списка: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`/`BTN_RED`).
- `src/views/home_screen/popups/mailbox/popups/DeleteFromFriendsPopup.ts` — подтверждение удаления из друзей: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`/`BTN_RED`).
- `src/views/home_screen/popups/profile/SettingsSection.ts` — вкладка настроек профиля: кнопки (`BTN_DEFAULT`).
- `src/views/home_screen/popups/profile/achievements/AchievementLine.ts` — строка достижения: кнопка получения награды (`BTN_GREEN`).
- `src/views/home_screen/popups/settings/ChangeNamePopup.ts` — смена имени: фон и кнопка с переключением доступности (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`, `updateInteractive`, `chanceTexture`).
- `src/views/home_screen/popups/settings/ChangePasswordPopup.ts` — смена пароля: фон и кнопка (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`).
- `src/views/home_screen/popups/settings/ConnectPopup.ts` — привязка аккаунта с согласием на соглашения: фон и кнопки с переключением доступности (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`, `updateInteractive`, `chanceTexture`).
- `src/views/home_screen/popups/settings/ExitPopup.ts` — подтверждение выхода: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`/`BTN_RED`).
- `src/views/home_screen/popups/settings/HtmlViewPopup.ts` — просмотр HTML-страницы: фон окна (`PNL_WINDOW_STANDARD`).
- `src/views/home_screen/popups/settings/LanguagePopup.ts` — выбор языка: фон и кнопки (`PNL_WINDOW_STANDARD`, `BTN_DEFAULT`).
- `src/views/home_screen/popups/settings/NewsPopup.ts` — новости: фон окна (`PNL_WINDOW_STANDARD`).
- `src/views/home_screen/popups/shop/PaymentMethodsPopup.ts` — выбор способа оплаты: фон и кнопки платёжных систем (`PNL_WINDOW_STANDARD`, `BTN_PAYMENT`).
- `src/views/home_screen/popups/shop/PaymentPopup.ts` — оплата: фон окна (`PNL_WINDOW_STANDARD`).
- `src/views/home_screen/popups/shop/offers/GoldenCoinsOfferPopup.ts` — оффер золотых монет: фон и кнопка (`PNL_WINDOW_STANDARD`, `BTN_GREEN`).
- `src/views/popups/AchievementCompletePopup.ts` — попап «достижение выполнено»: фон без шапки (`PNL_WINDOW_STANDARD_NO_HEADER`).
- `src/views/popups/CollectionCompletePopup.ts` — тост «комплект собран»: фон без шапки (`PNL_WINDOW_STANDARD_NO_HEADER`).
- `src/utils/CollectionUtils.ts` — независимый аналог для графического стиля коллекций (`button`, `panelPreset`), логика панелей скопирована из `PanelsPresets`; пресеты не импортирует, при правке `PanelsPresets` сверять вручную (см. [#collectionutils-analog](#collectionutils-analog)).
