# Сборка — сборочный цех на главном экране (клиент)

> **auto-create** — документ составлен по существующему коду (код в рамках задачи не менялся),
> 2026-10-14. Запуском не проверялось. Актуализирован 2026-10-19 после merge `origin/amnesia/fix`
> (подписка плашки на `BAG_UPDATE`, переписанная анимация покупки).
> Серверная сторона: `/workspace/server/.claude/docs/assembly-architecture.md` (тоже auto-create).

ГДД: `/workspace/client/.claude/docs/game-design/assembly-gdd.md`. В ГДД «чертёж» — купленная пачка
(в коде «часть схемы»), «очки строительства» — части схемы (`schemeParts`), порог в 30 очков приходит
как `needSchemeParts`.

<a id="toc"></a>
## Оглавление
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

Сборка — «СБОРОЧНЫЙ ЦЕХ» (`assemblyScreen.title`): игрок покупает за серебро части схемы и, накопив
нужное количество, забирает заранее сгенерированный сервером танк-награду или отказывается от него
(ГДД [#gdd-purpose](game-design/assembly-gdd.md#gdd-purpose)).
Генерация награды, цены и списания — на сервере
(`/workspace/server/.claude/docs/assembly-architecture.md#purpose`); клиент показывает состояние и
шлёт четыре действия.

Клиентская часть из двух мест:

- **Плашка на главном экране** (`HomeScreenAssembly`, футер `HomeScreen`, слот `assembly`). Показывает
  награду (фон по рангу, картинка, у танка — ранг, имя, тип) и два мини-прогресса: части схемы к
  `needSchemeParts` в процентах и серебро к `needSilverCoins` значением. Когда хватает серебра на
  покупку или частей на сборку, включаются бегущие огни и значок внимания. Клик открывает окно.
- **Окно сборки** (`AssemblyPopup`). Танк-награда с мощностью и параметрами, текст «Танк собран на N%»,
  прогресс частей, пять пластин-схем по цветам пачек. Нижняя кнопка выбирается так:
  1. частей `>= needSchemeParts` — «СОБРАТЬ»: открывает окно сравнения `TankGetPopup`;
  2. иначе серебра `>= needSilverCoins` — «Купить схему за N»: покупка пачки;
  3. иначе — прогресс серебра без кнопки.

  ГДД: `#gdd-window`, `#gdd-build-points`.

Правила, которые живут только на клиенте:

- **Доступ по размеру команды.** Пока танков в сумке меньше `Globals.vars.AssemblyAccessHangarSize`,
  плашка показывает замок и текст «Собери {0} танков в команду» (`homeScreen.assembly.access`), окно
  не открывается. На сервере такой проверки нет ([#tradeoffs](#tradeoffs), п.3). ГДД `#gdd-access`.
- **Анимация покупки** (ГДД `#gdd-buy-animation`). Сервер возвращает цвет выпавшей пачки (`reward.type`). Пластины других цветов
  «взрываются» по очереди в случайном порядке с шагом 50 мс (спайн `spine/battle/tank_destroy`,
  крестик) и сжимаются, выпавшая увеличивается и улетает вверх. Когда закончились все анимации,
  прогресс и кнопка перестраиваются по новым данным.
- **Окно сравнения** (ГДД `#gdd-take`). Без заменяемого танка в окне одна кнопка «ВЫБРАТЬ» → `/take`. С заменяемым:
  красная «ПРОДАЖА» и кнопка смены местами; «ПРОДАЖА» шлёт `/reject`, а после смены местами —
  `/take`. Отказ на сервере списывает части и ничего не даёт взамен. Закрытие окна сравнения по фону
  ничего не шлёт, награда остаётся.

<a id="references"></a>
## 2. Референсы

- Серверный контракт — `/workspace/server/.claude/docs/assembly-architecture.md#page-routes`,
  `#m-apiresponse`; жизненный цикл награды — `#lifecycle` там же.
- Окно сравнения `TankGetPopup` — общее с поездом и коллекциями; флаг `bgClose` описан в
  `collections-architecture.md#cls-tankgetpopup-bgclose` (сборка его не передаёт).
- Плашка повторяет устройство соседней `HomeScreenAerodrome` (тот же атлас `home_screen/support`).

<a id="patterns"></a>
## 3. Паттерны

- **Попап через `FlashPublisher`.** `AssemblyPopup.publish`: запрос `/ingame/assembly` → загрузка
  пакетов `AssemblyScreen` и `TechInfo` → `GameFlash` с `setParallel(true)`, закрытие по фону.
  Процедура ассетов — `asset-packaging.md` (`#regular-atlas`; картинки танков —
  `Creator.spriteAsync`, `#async-atlas`).
- **Подписка на события сумки.** `HomeScreenAssembly` подписывается на `GameEvents.BAG_UPDATE` (доступ
  по числу танков) и на `ITEM_NEW_OR_UPDATE`/`ITEM_DELETE` по ресурсам (`UserBag.isResourceId`) в
  `onCreate` и отписывается по `Layout.EVENT_DESTROYED`. Устройство событий — `bag-architecture.md#patterns`.
- **Локальное событие пересоздания.** После `/take` и `/reject` окно шлёт
  `GameEvents.ASSEMBLY_UPDATE(assembly)`; `HomeScreen.onAssemblyUpdate` сохраняет данные и
  пересоздаёт плашку целиком. Своих push-событий у сборки нет; ресурсы приходят push-ом сумки
  (`server-push-events-subscription.md`, `bag-architecture.md`).
- **Пресеты UI.** Окно — `PanelsPresets.PNL_WINDOW_STANDARD`/`HR`, кнопки — `ButtonPresets.BTN_GREEN`
  (`panels-buttons-presets-architecture.md`); карточка танка — `TankPresets.NameLayout`/`ParamsLayout`.

<a id="class-list"></a>
## 4. Список классов

- `src/views/home_screen/HomeScreenAssembly.ts` — `HomeScreenAssembly` (плашка).
- `src/views/home_screen/popups/assembly/AssemblyPopup.ts` — `AssemblyPopup` (+ интерфейс
  `AssemblyPopupConfig { onExit? }`).
- `src/views/home_screen/popups/assembly/assembly.d.ts` — глобальные типы `AssemblyJSON`,
  `AssemblyBuySchemeJSON`.

За пределами классов области: `HomeScreen` (создание плашки, `onAssemblyUpdate`), `home.d.ts`
(`HomeScreenJSON.assembly`), `GameEvents.ASSEMBLY_UPDATE`, `Vars.AssemblyAccessHangarSize`.

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#references`, `#patterns`, `#class-list`, `#class-nav`, `#classes`,
`#cls-homescreenassembly`, `#cls-assemblypopup`, `#types`, `#client-contract`, `#tradeoffs`,
`#gdd-link`, `#file-map`.

<a id="class-nav"></a>
## 6. Оглавление по классам

[`HomeScreenAssembly`](#cls-homescreenassembly) · [`AssemblyPopup`](#cls-assemblypopup) ·
[Типы `assembly.d.ts`](#types) · [Контракт с сервером](#client-contract)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-homescreenassembly"></a>
### `HomeScreenAssembly` (`implements IViewProvider`)

Плашка сборки на главном экране. Создаётся `HomeScreen.UIAssembly()` с `HomeScreenJSON.assembly`;
при `ASSEMBLY_UPDATE` пересоздаётся вместе со слотом. Из `AssemblyJSON` берёт только `reward`,
`needSchemeParts`, `needSilverCoins`, `schemePartsId`; текущие количества ресурсов читает из
`Globals.bag`, поэтому покупка частей в окне обновляет плашку без `ASSEMBLY_UPDATE`.

- `onCreate()` — строит слои `main` и `access`, видимость по правилу доступа (ГДД `#gdd-access`; танков в
  `Globals.bag.getTanks()` `>= AssemblyAccessHangarSize`), `checkNotification()`, подписки: `onBagUpdate`
  на `BAG_UPDATE` и шесть обработчиков ресурсов на `ITEM_*`. `onDestroy()` — отписка от них же.
- `UIMain()` — огни `LightRunAnimation` ×2, награда (`UIAirplane`/`UITank` по type-guard'у
  `UserBag.isAirplane`/`isTank`; нет награды — пусто), рамка, `AttentionAnimation`; клик —
  `AssemblyPopup.publish(screen, {})`.
- `UITank()` / `UIAirplane()` — фон по рангу, картинка из async-атласа `BTank_<id>`/`BAirplane_<id>`,
  маска; у танка ещё ранг, имя (обрезка до 20 символов), тип. Прогресс — `UIProgress` с
  `RESOURCE_TANK_SCHEME_PARTS` или `RESOURCE_AIRPLANE_SCHEME_PARTS`.
- `UIProgress(id)` → `UISchemesProgress(id)` (части к `needSchemeParts`, процент) +
  `UICoinsProgress()` (серебро к `needSilverCoins`, значение). ГДД `#gdd-home-card`.
- `UIAccess()` — затемнённая `home_screen/support/base.png`, замок и текст доступа.
- `checkNotification()` — огни и значок видны, если серебра `>= needSilverCoins` ИЛИ частей
  `schemePartsId` `>= needSchemeParts` (ГДД `#gdd-home-card`). То же условие, что выбор кнопки в
  [`AssemblyPopup.UIFooter`](#cls-assemblypopup), по другому источнику данных
  ([#tradeoffs](#tradeoffs), п.6).
- `replaceReward()` — пересоздаёт блок награды (вместе с прогрессами) и `refreshForce`.
- `onBagUpdate()` — на `BAG_UPDATE` (раз на пакет сумки, после добавлений и удалений) пересчитывает
  видимость `main`/`access`; удаление танка учитывается.
- `onSilverCoinsUpdate`/`onSilverCoinsDelete`, `onTankSchemePartsUpdate`/`onTankSchemePartsDelete`,
  `onAirplaneSchemePartsUpdate`/`onAirplaneSchemePartsDelete` — шесть одинаковых обработчиков:
  фильтр по `ItemId`, затем `replaceReward()` + `checkNotification()`.
- `view()` — корневой `Layout`.

<a id="cls-assemblypopup"></a>
### `AssemblyPopup` (`implements IViewProvider`)

Окно сборки. Держит снимок `data: AssemblyJSON` из последнего ответа сервера; на события сумки не
подписан.

Открытие и закрытие:

- `static publish(screen, config)` — `requestData()` (`/ingame/assembly` → `data`) → `loadAssets()`
  (пакеты `AssemblyScreen`, `TechInfo`, спиннер `FlashPublisher.showLoading`) →
  `FlashPublisher.publish(getAsGameFlash())`.
- `getAsGameFlash()` — `GameFlash` с закрытием по фону, `setParallel(true)`, фабрика `onCreate()`.
- `onCreate()` / `onDestroy()` — добавить `UIMain`; по `EVENT_DESTROYED` вызвать `config.onExit`
  (вызывающий сейчас его не передаёт). `view()` — `FlashLayout`.

Построение UI:

- `UIMain()` — окно 310 с заголовком и крестиком, появление твином; на время твина
  `screen.setBlockInteractive(true)`.
- `UIContent()` — фон `atlas/assembly_screen/bg.png`, колонка: `UITankInfo`,
  `TankPresets.ParamsLayout`, `UISchemesFooter`, `UIFooter`. `data.reward` приводится к `TankJSON`
  без проверки ([#tradeoffs](#tradeoffs), п.2).
- `UITankInfo(tank)` — картинка `BTank_<id>`, `TankPresets.NameLayout`, мощность.
- `UISchemesFooter()` (ГДД `#gdd-window`) — `UIBuildProgressText()` («Танк собран на N%», через `getPercent`),
  `UIBuildProgress()` (прогресс частей), `UITankSchemes()` (пять `UITankSchemeImg(color)`: пластина,
  схема, скрытый крестик `hit`; имя слоя — цвет). Слой `schemes` состоит из `list` (пять пластин),
  пустых `explosions` (родитель спайнов взрыва) и `animation` (копия улетающей пластины).
- `UIFooter()` — кнопка или прогресс серебра по правилу из [#purpose](#purpose).
- `getPercent(value, max)` — процент с ограничением `[0, 100]`; `max == 0` → 100.

Действия:

- `BtnBuySchemes()` (ГДД `#gdd-buy-animation`) — `hideAssemblyBtn()`, `/ingame/assembly/buySchemeParts`; при `result == "OK"` —
  `data = response.assembly`, `animationSchemes(response)`; при ошибке — `showAssemblyBtn()`.
- `animationSchemes(resp)` — делит слои `schemes.list` на отвергнутые (имя `!= resp.reward.type`) и
  выбранную, считает завершения; по последнему завершению пересоздаёт текст прогресса, `list`,
  ставит прогресс-бар на новые значения, пересоздаёт `footer`, `showAssemblyBtn()`.
- `animationHitAndHide(icon, effectsParent, delay, onComplete)` — отвергнутые, перемешанные
  `ArrayUtils.shuffle`, стартуют с задержкой `index * 50` мс; взрыв, крестик (250 мс), сжатие (250 мс).
- `animationSchemeExplosion(scheme, effectsParent, onComplete)` — создаёт спайн взрыва в `explosions`
  на позиции пластины и уничтожает его после затухания.
- `animationSelectScheme(icon, footer, onComplete)` — прячет оригинал, создаёт копию в `animation`,
  увеличение и улёт вверх (задержка 200 мс, 700 мс; затем 300 мс).
- `hideAssemblyBtn()` / `showAssemblyBtn()` — сжатие/разжатие кнопки `footer.assemblyBtn` с
  отключением/включением интерактивности; кнопки нет — выход.
- `BtnCompare()` (ГДД `#gdd-take`) — `/ingame/assembly/compare`; по ответу `TRAIN_STOP_AUTO_SUMMON` (останавливает
  автопризыв поезда) и `TankGetPopup.publish` с `onAccept: BtnTake`, `onRefuse: BtnReject`.
- `BtnTake()` — `/ingame/assembly/take` → `data = response.assembly`, пересоздание `UIContent`,
  `ASSEMBLY_UPDATE(assembly)`, `HANGAR_UPDATE` (главный экран перезапрашивает ангар).
- `BtnReject()` — `/ingame/assembly/reject` → то же, без `HANGAR_UPDATE`.

Ошибки `BtnCompare`/`BtnTake`/`BtnReject` глушатся пустым `catch`, `result` ответа не проверяется
([#tradeoffs](#tradeoffs), п.1).

<a id="types"></a>
### Типы `assembly.d.ts`

- `AssemblyJSON { silverCoins, needSilverCoins, schemeParts, schemePartsId, needSchemeParts,
  reward: BagItemJSON }` — состояние сборки; `reward` объявлен обязательным, сервер его опускает при
  `null` ([#tradeoffs](#tradeoffs), п.2).
- `AssemblyBuySchemeJSON { reward: { type, count }, assembly }` — ответ покупки: цвет и размер пачки.

<a id="client-contract"></a>
### Контракт с сервером

Маршруты `/ingame/assembly…` без параметров (сервер — `AssemblyPage`,
`/workspace/server/.claude/docs/assembly-architecture.md#page-routes`):

| Маршрут | Клиент | Ответ при успехе | Что клиент использует |
|---|---|---|---|
| `""` | `AssemblyPopup.requestData` | `{ assembly }` | всё |
| `/buySchemeParts` | `BtnBuySchemes` | `{ reward: {type, count}, assembly }` | `reward.type`, `assembly` |
| `/compare` | `BtnCompare` | `{ receivedTank, replaceableTank \| null }` | всё, в `TankGetPopup` |
| `/take` | `BtnTake` | `{ reward, assembly }` | `assembly` (`reward` не читается) |
| `/reject` | `BtnReject` | `{ assembly }` | `assembly` |

Первичное состояние — `HomeScreenJSON.assembly` из `/ingame/home`. `assembly.silverCoins` и
`schemeParts` сервер считает по сумке на момент ответа; `schemePartsId` — `5` (танк), `6` (самолёт)
или `0` (награды нет). Push-событий сборка не получает: ресурсы и танк после `/take` приходят
push-ом сумки (`bag-architecture.md#client-contract`).

Ошибки: `/buySchemeParts` возвращает `errSection`/`errCode`, `sendRequest` отклоняет промис.
`/compare`, `/take`, `/reject` отвечают только `result: "ERROR"` без кодов, и `sendRequest` считает
такой ответ успешным ([#tradeoffs](#tradeoffs), п.1).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Наблюдения по коду; баг это или задумано, решает пользователь.

1. **Ошибка `/compare`, `/take`, `/reject` обрабатывается как успех.** Сервер отвечает
   `{ result: "ERROR" }` без `errSection`/`errCode`, `WSSocket.sendRequest` резолвит промис, а
   обработчики не вызывают `ResultUtils.isOk`. `/take` или `/reject`: `data = undefined`,
   пересоздание `UIContent` падает на `data.reward`, `ASSEMBLY_UPDATE(undefined)` ломает плашку на
   главном экране. `/compare`: `TankGetPopup` получает `receivedTank: undefined`. Сервер отвечает
   ошибкой, если частей меньше `needSchemeParts` (окно показывает кнопку по устаревшему снимку) или
   награда не танк. Чинить на стыке: либо клиент проверяет `result`, либо сервер добавляет код
   ошибки (`integration-lead`). ГДД, отложено 2026-10-15: что видит игрок при ошибке, открыто в
   [#gdd-open](game-design/assembly-gdd.md#gdd-open).
2. **Окно не готово к отсутствию награды и к самолёту.** `UIContent` приводит `data.reward` к
   `TankJSON`; при `reward` отсутствующем (сервер опускает поле, если генерация не удалась,
   `/workspace/server/.claude/docs/assembly-architecture.md#tradeoffs`, п.2 и п.8) или самолётном окно
   упадёт. Плашка оба случая переживает. Самолётная награда на сервере не генерируется, ветки
   `UIAirplane`/`RESOURCE_AIRPLANE_SCHEME_PARTS` на клиенте пока не срабатывают. ГДД, отложено
   2026-10-15: [#gdd-take](game-design/assembly-gdd.md#gdd-take) требует новый танк сразу после
   «СОБРАТЬ»/отказа, а сервер при пустом списке кандидатов оставляет старую награду.
3. **Доступ по числу танков проверяет только клиент.** `Vars.AssemblyAccessHangarSize = 12` зашит в
   клиенте, сервер его не знает и не проверяет. Замок скрывает плашку, но маршруты доступны всегда.
   Пересчёт идёт по `BAG_UPDATE`, удаление танка учитывается. ГДД,
   отложено 2026-10-15: правило из [#gdd-access](game-design/assembly-gdd.md#gdd-access) (12 танков)
   проверяет только клиент.
4. **Снимок окна не обновляется.** `AssemblyPopup` не слушает `ITEM_*`: серебро или части, изменённые,
   пока окно открыто (другая награда, другой экран), не меняют кнопку и прогрессы до следующего
   ответа сервера. Отсюда и сценарий п.1.
5. **Шесть одинаковых обработчиков ресурсов** в `HomeScreenAssembly` (3 ресурса × `ITEM_NEW_OR_UPDATE`/
   `ITEM_DELETE`) с одним телом. Кандидат на один обработчик с фильтром по набору `ItemId`. Каждое
   изменение любого из трёх ресурсов пересоздаёт весь блок награды вместе с async-картинкой.
6. **Одно правило — три выражения.** «Хватает серебра на покупку / частей на сборку» записано в
   `HomeScreenAssembly.checkNotification` (по `Globals.bag`) и в `AssemblyPopup.UIFooter` (по снимку
   сервера); в `checkNotification` одно выражение повторено трижды. «Доступ по числу танков» — дважды
   (`onCreate`, `onBagUpdate`). Сводка похожих проверок по проекту —
   `bag-architecture.md#dup-can-afford`; во время удержания ресурсов плашка видит заниженные
   значения — `bag-architecture.md#hold-reads`.
7. **Ошибки глушатся.** `BtnCompare`/`BtnTake`/`BtnReject` с пустым `catch`, `BtnBuySchemes` только
   пишет в консоль; игрок сообщения не видит. ГДД, отложено 2026-10-15: что показывать, открыто в
   [#gdd-open](game-design/assembly-gdd.md#gdd-open).
8. **Неиспользуемое.** Ключи `assemblyScreen.info`, `assemblyScreen.complete`, `assemblyScreen.take`
   в `ru.json` нигде не читаются; `AssemblyPopupConfig.onExit` и `onExit` у `TankGetPopup` (пустой)
   не используются; ответ `/take.reward` не читается; `textArgs` у кнопки «СОБРАТЬ» передаётся, но в
   строке нет `{0}`. Кандидаты на удаление.
9. **Нет английской локализации.** В `en.json` нет `assemblyScreen.*` и `homeScreen.assembly.*`.
10. **Под чертежами нет подписи очков.** `UITankSchemeImg` рисует пластину и схему без подписи 1/3/5/7/10;
    ГДД [#gdd-window](game-design/assembly-gdd.md#gdd-window) её требует. ГДД, отложено 2026-10-15.
11. **Сервер разрешает `buySchemeParts` при 30 и более очках.** По ГДД
    [#gdd-build-points](game-design/assembly-gdd.md#gdd-build-points) покупка при 30+ запрещена. Клиент
    кнопку не показывает, но запрос возможен со снимка окна (п.4). Стык, чинить на сервере. ГДД,
    отложено 2026-10-15.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [assembly-gdd.md](game-design/assembly-gdd.md). Правило ГДД — класс или метод:

- [`#gdd-access`](game-design/assembly-gdd.md#gdd-access) — `HomeScreenAssembly.onCreate`/`onBagUpdate`/`UIAccess`
  ([`HomeScreenAssembly`](#cls-homescreenassembly));
- [`#gdd-build-points`](game-design/assembly-gdd.md#gdd-build-points) и
  [`#gdd-window`](game-design/assembly-gdd.md#gdd-window) — `AssemblyPopup.UIFooter`/`UISchemesFooter`
  ([`AssemblyPopup`](#cls-assemblypopup));
- [`#gdd-home-card`](game-design/assembly-gdd.md#gdd-home-card) — `HomeScreenAssembly.UIProgress`/`checkNotification`;
- [`#gdd-take`](game-design/assembly-gdd.md#gdd-take) — `BtnCompare`/`BtnTake`/`BtnReject` и `TankGetPopup`;
- [`#gdd-buy-animation`](game-design/assembly-gdd.md#gdd-buy-animation) — `BtnBuySchemes`, `animationSchemes`,
  `animationHitAndHide`, `animationSelectScheme`, `hideAssemblyBtn`;
- [`#gdd-blueprint-quality`](game-design/assembly-gdd.md#gdd-blueprint-quality),
  [`#gdd-blueprint-price`](game-design/assembly-gdd.md#gdd-blueprint-price),
  [`#gdd-reward-choice`](game-design/assembly-gdd.md#gdd-reward-choice) — серверные правила
  (`/workspace/server/.claude/docs/assembly-architecture.md#purpose`); на клиенте только отображение
  (`AssemblyBuySchemeJSON.reward.type`).

Расхождения кода с ГДД — [#tradeoffs](#tradeoffs), пп.1–3, 7, 10, 11. Анимация покупки с ГДД `#gdd-buy-animation` совпадает (решение 2026-10-19).

<a id="file-map"></a>
## 10. Карта файлов компонента

Полнота проверена `grep` по `HomeScreenAssembly|AssemblyPopup|AssemblyJSON|AssemblyBuySchemeJSON|assemblyScreen|AssemblyScreen|assembly_screen|AssemblyAccessHangarSize|ASSEMBLY_UPDATE|homeScreen.assembly|/ingame/assembly`.
Движок `src/ee/`, `Const`, `Globals` не перечислены.

### Файлы прямого влияния

- `src/views/home_screen/HomeScreenAssembly.ts` — плашка на главном экране, доступ, подписки на сумку.
- `src/views/home_screen/popups/assembly/AssemblyPopup.ts` — окно сборки, все запросы `/ingame/assembly…`.
- `src/views/home_screen/popups/assembly/assembly.d.ts` — типы `AssemblyJSON`, `AssemblyBuySchemeJSON`.
- `assets-src/atlas/assembly_screen/` (`bg.png`) — графика пакета `AssemblyScreen`.

### Файлы косвенного влияния

- `.claude/docs/game-design/assembly-gdd.md` — ГДД сборки (одна копия на client и server).
- `src/views/home_screen/HomeScreen.ts` — слот `assembly` в футере, `UIAssembly()`, `onAssemblyUpdate`, подписка на `ASSEMBLY_UPDATE`.
- `src/views/home_screen/home.d.ts` — поле `HomeScreenJSON.assembly`.
- `src/plain/GameEvents.ts` — событие `ASSEMBLY_UPDATE`; сборка также шлёт `HANGAR_UPDATE`, `TRAIN_STOP_AUTO_SUMMON`.
- `src/plain/Vars.ts` — `AssemblyAccessHangarSize`.
- `assets-src/raw/lang/ru/ru.json` — общий файл локализации; сборке принадлежат `assemblyScreen.*`, `homeScreen.assembly.access`.
- `tools/src/config.yaml` — общий конфиг паковки; сборке принадлежит запись пакета `AssemblyScreen` (путь `assembly_screen`).
- `assets-src/atlas/home_screen/support/` — общий атлас плашек главного экрана; сборка использует `frame.png`, `base.png` (в том числе затемнённым фоном замка).
- `assets-src/atlas/tech_info/tanks/schemes/` — часть атласа `TechInfo`: пластины и схемы пяти цветов, `X_Icon.png`.
- `src/views/home_screen/popups/tank/TankGetPopup.ts` — зависимость: окно сравнения танков, `onAccept`/`onRefuse`.
- `src/plain/user/UserBag.ts` — зависимость: `getTanks`, `getResourceCount`, type-guard'ы.
- `src/plain/items/ItemId.ts` — зависимость: ресурсы `RESOURCE_SILVER_COINS`, `RESOURCE_TANK_SCHEME_PARTS`, `RESOURCE_AIRPLANE_SCHEME_PARTS`.
- `src/views/home_screen/popups/bag/bag.d.ts` — зависимость: `BagItemJSON`, `TankJSON`, `AirplaneJSON`.
- `src/presets/TankPresets.ts` — зависимость: имя и параметры танка в окне.
- `src/presets/RankPresets.ts` — зависимость: значок ранга на плашке.
- `src/presets/PanelsPresets.ts`, `src/presets/ButtonPresets.ts` — зависимость: окно, разделители, кнопки.
- `src/shared/AnimatedProgressBar.ts` — зависимость: все прогресс-бары.
- `src/shared/animations/LightRunAnimation.ts`, `src/shared/animations/AttentionAnimation.ts` — зависимость: подсветка плашки.
- `src/shared/FlashPublisher.ts`, `src/shared/flash/GameFlash.ts` — зависимость: показ окна и спиннер загрузки.
- `src/utils/ArrayUtils.ts` — зависимость: `shuffle` порядка взрывов.
- `src/utils/ResultUtils.ts` — зависимость: проверка `result` у покупки.
- `src/utils/TankUtils.ts`, `src/utils/AirplaneUtils.ts`, `src/utils/StringUtils.ts` — зависимость: имена ассетов техники, обрезка имени.
- `src/plain/globals/WSSocket.ts` — зависимость: `sendRequest`/`sendButtonRequest`, правило «ошибка — только при `errCode`/`errSection`».
