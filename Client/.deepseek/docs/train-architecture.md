# Поезд — призыв танков на главном экране (клиент)

> **смешанный** — разделы 1–7 и 9–10 в основе **auto-create** (составлены `client-analyst-lead` по существующему
> коду, 2026-10-14; запуском не проверялось); по итогам разработки и сверены с кодом: п.1, `#m-ontrainsummon`,
> `#m-ontraincollectionitemreceived`, `#m-cleartraincart`, `#m-auto-summon`, `#m-train-animation`, `OnTrainRefuse`,
> `#cls-traincollectionitempopup`, `#tradeoffs` п.2/п.4/п.7 (2026-10-23, автопризыв не останавливается на предмете
> коллекции — решение пользователя). 2026-10-15 — п.9 дополнен по ГДД (ТЗ «Механика кора»). 2026-10-19 — сверено
> с кодом после merge `origin/amnesia/fix` (удалён аэродромный код радиовышки, туториал переведён на
> `TutorialUtils.FIRST_TRAIN`/`SECOND_TRAIN`, правки окон поезда). 2026-10-23 — `animationTrainDestroyTank`
> переименован в `animationTrainClearCart` (решение пользователя).
> Серверная сторона: `/workspace/server/.claude/docs/train-architecture.md` (тоже auto-create).

ГДД: [train-gdd.md](game-design/train-gdd.md) (черновик по примерному описанию, дополнен по ТЗ «Механика кора» 2026-10-15). Ссылки на разделы —
у классов и методов ниже и в [п.9](#gdd-link). Термин ГДД — «схема танка» (в коде `RESOURCE_TANK_SCHEME`,
`tankSchemes`).

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

Поезд — правая часть футера главного экрана. Игрок кликает по поезду, тратит одну схему танка и
получает танк или предмет коллекции. Бросок, списание, опыт поезда и туториальные подмены делает
сервер ([серверный #purpose](/workspace/server/.claude/docs/train-architecture.md#purpose)); клиент
показывает результат, отправляет решение игрока и ведёт автопризыв.

Из чего состоит клиент:

- **Плашка поезда** (часть `HomeScreen`): локомотив с вагоном, клик — призыв. Пока выпавший танк не
  взят и не продан, он стоит в вагоне, повторный клик показывает его снова (сервер отвечает тем же
  танком без списания, [gdd-decision](game-design/train-gdd.md#gdd-decision)).
- **Счётчик схем танка** над поездом: число из сумки, клик открывает окно покупки схем.
- **Полоса уровня поезда** (`TrainUpgradeProgressBar`) и две кнопки над поездом: «АВТО»
  (`TrainAutoSummonBtn`) и «ИНФО» (`TrainUpgradeBtn`).
- **Окна:** решение по танку — общий `TankGetPopup`; предмет коллекции — `TrainCollectionItemPopup`;
  прокачка — `TrainUpgradePopup`; покупка схем — `TrainBuySchemesPopup`; настройка автопризыва —
  `TrainAutoSummonPopup`.

Призыв по шагам ([`OnTrainSummon`](#m-ontrainsummon)):
1. Ответ с танком — вагон с танком въезжает, затем открывается `TankGetPopup`. «Выбрать» ставит
   танк в ангар (`/accept`), «Продажа» продаёт его за серебро (`/refuse`). Закрытие окна по фону
   оставляет танк в вагоне.
2. Ответ с предметом коллекции — вагон с иконкой предмета приезжает и остаётся на вагоне, пока открыто
   `TrainCollectionItemPopup` (подробно — [collections-architecture.md#cls-traincollectionitempopup-changes](collections-architecture.md#cls-traincollectionitempopup-changes)).
   После закрытия окна груз гаснет, дальше — следующий призыв автопризыва или возврат локомотива.
3. Ошибка — вне туториала открывается окно покупки схем.

Кнопка «Продажа» в `TankGetPopup` есть только когда выпавший танк заменяет другой
(`replaceableTank !== null`); при свободной позиции окно показывает одну кнопку «Выбрать». Это
соответствует [gdd-decision](game-design/train-gdd.md#gdd-decision). Автопризыв это правило нарушает,
см. [#tradeoffs](#tradeoffs) п.1.

**Автопризыв** реализован только на клиенте, на сервере есть лишь роут шансов `/autoData`. Правила —
[gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon); реализация:
- доступ — с уровня кампании `Vars.AutoSummonAccessLevel` (10), иначе окно показывает условие;
- игрок выбирает ранг из рангов с ненулевым шансом на текущем уровне поезда, выбор хранится в
  `localStorage` (`autoTrain`) и стирается при `Globals.logout()`;
- клиент призывает цепочкой; неподходящий танк ([`isTrainAutoSummonTargetTank`](#m-auto-summon))
  сразу продаётся через `/refuse` (в том числе при свободной позиции, [#tradeoffs](#tradeoffs) п.1),
  подходящий показывается в `TankGetPopup` и ждёт решения игрока; новый предмет коллекции
  показывается в `TrainCollectionItemPopup`, призыв продолжается после закрытия окна; дубликат
  (`sellReward` есть) окна не получает, призыв идёт сразу ([`onTrainCollectionItemReceived`](#m-ontraincollectionitemreceived));
- остановка: клик по поезду или по «АВТО», закрытие `TankGetPopup` по фону, ошибка призыва,
  событие `TRAIN_STOP_AUTO_SUMMON` (шлёт `AssemblyPopup.BtnCompare`).

Туториальные ветки поезда (указатель на поезд на шагах `TutorialUtils.FIRST_TRAIN`/`SECOND_TRAIN`
(0 и 1), на «Выбрать» на тех же шагах, запрет окна покупки при ошибке) — [tutorial-architecture.md#integration](tutorial-architecture.md#integration).

<a id="references"></a>
## 2. Референсы

Нет: код поезда — из исходного коммита проекта. Прежние копии поезда в аэродроме (автопризыв
радиовышки, `AerodromeBuySchemesPopup`) удалены merge `origin/amnesia/fix`; вместо них военная база
(`src/views/home_screen/popups/military_base/`, не документируется здесь). Окно сравнения
`TankGetPopup` переиспользуют сборка ([assembly-architecture.md](assembly-architecture.md)) и
коллекции ([collections-architecture.md#cls-tankgetpopup-bgclose](collections-architecture.md#cls-tankgetpopup-bgclose)).

<a id="patterns"></a>
## 3. Паттерны

- **Окно с предзагрузкой данных.** `static publish` → `requestData()` (запрос роута) → при
  необходимости `loadAssets()` → `FlashPublisher.publish(GameFlash)`; окно строится в `onCreate` из
  уже полученных данных. Так устроены `TrainAutoSummonPopup`, `TrainUpgradePopup`,
  `TrainBuySchemesPopup`. Окна поверх друг друга не выстраиваются в очередь
  ([popup-queue-pattern.md#problem](popup-queue-pattern.md#problem)).
- **Удержание награды под анимацию.** Серебро и схемы приходят push-ом сумки почти одновременно с
  ответом; `Globals.bag.holdResource` ставится синхронно в обработчике ответа, `releaseHold` — в конце
  полёта иконок ([bag-architecture.md#m-hold](bag-architecture.md#m-hold),
  [#userbag-hold-order](bag-architecture.md#userbag-hold-order)).
- **Полёт иконок через событие.** `FlyIconsAnimation.play(TRAIN_TANK_SCHEMES, …)` шлёт `FLY_ICONS`;
  `HomeScreen.onFlyIcons` знает позицию счётчика схем и запускает анимацию. Так в счётчик летят схемы
  из квестов, наград за простой, боя кампании и покупки.
- **Состояние поезда — в данных экрана.** Отдельной модели нет: `HomeScreen.data.train` (`TrainJSON`)
  приходит в `/ingame/home` и заменяется ответами `/summon`/`/accept`/`/refuse`; плашка
  пересобирается из него (`replaceByName("train", UITrain())`).
- **Окно с колбэком выхода.** Окно, после которого поезд должен продолжить работу
  (`TrainCollectionItemPopup`), получает `onExit` и вызывает его ровно один раз при любом исходе. После
  окна содержимое вагона снимается той же анимацией, что и при продаже танка
  ([`clearTrainCart`](#m-cleartraincart)).
- **Стандартные панели и кнопки** — `PanelsPresets.PNL_WINDOW_STANDARD`, `HR`, `ButtonPresets.BTN_*`
  ([panels-buttons-presets-architecture.md](panels-buttons-presets-architecture.md)).

<a id="class-list"></a>
## 4. Список классов

Папка `src/views/home_screen/popups/train/`: `TrainAutoSummonPopup`, `TrainBuySchemesPopup`,
`TrainCollectionItemPopup`, `TrainUpgradePopup`, типы `train.d.ts`.
Папка `src/views/home_screen/`: `TrainAutoSummonBtn`, `TrainUpgradeBtn`, `TrainUpgradeProgressBar`.
Части чужих классов, принадлежащие поезду: train-методы `HomeScreen`, типы `TrainJSON`/
`TrainUpgradeDataJSON`/`TrainAutoSummonJSON` в `home.d.ts`, события `TRAIN_*` в `GameEvents`,
использование `TankGetPopup`.

<a id="anchors"></a>
## 5. Навигация (якоря)

| Якорь | Что там |
|---|---|
| `#cls-homescreen-train` | плашка, счётчик схем, обработчики роутов в `HomeScreen` |
| `#m-ontrainsummon` | обработка ответа `/summon` |
| `#m-ontraincollectionitemreceived` | предмет коллекции из призыва, продолжение автопризыва |
| `#m-cleartraincart` | снятие содержимого вагона: продолжение автопризыва или возврат локомотива |
| `#m-ontrainaccept` | «Выбрать» (`/accept`) и «Продажа» (`/refuse`) |
| `#m-auto-summon` | запуск, остановка и фильтр автопризыва |
| `#m-train-animation` | анимации локомотива и вагона |
| `#cls-tankgetpopup-train` | `TankGetPopup` в поезде: кнопки, продажа |
| `#client-contract` | роуты, поля ответов, события |
| `#tradeoffs` | баги, расхождения, дубли |

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `HomeScreen` (train-часть) | [#cls-homescreen-train](#cls-homescreen-train) |
| `TrainAutoSummonBtn`, `TrainUpgradeBtn` | [#cls-buttons](#cls-buttons) |
| `TrainUpgradeProgressBar` | [#cls-trainupgradeprogressbar](#cls-trainupgradeprogressbar) |
| `TrainAutoSummonPopup` | [#cls-trainautosummonpopup](#cls-trainautosummonpopup) |
| `TrainUpgradePopup` | [#cls-trainupgradepopup](#cls-trainupgradepopup) |
| `TrainBuySchemesPopup` | [#cls-trainbuyschemespopup](#cls-trainbuyschemespopup) |
| `TrainCollectionItemPopup` | [#cls-traincollectionitempopup](#cls-traincollectionitempopup) |
| `TankGetPopup` (в поезде) | [#cls-tankgetpopup-train](#cls-tankgetpopup-train) |
| `train.d.ts`, типы в `home.d.ts`, `GameEvents` | [#types](#types) |

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-homescreen-train"></a>
### `HomeScreen` — train-часть

`src/views/home_screen/HomeScreen.ts`. Поля: `data.train: TrainJSON`, `autoTrainParams?: { rank }`
(задан — автопризыв включён), dev `devSummonSection`.

**Плашка и счётчик:**
- `UIFooter()` — кладёт плашку (`train`), полосу уровня (`progressBar`), кнопки `icons.auto`/
  `icons.info` и счётчик схем (`tankSchemes`; клик → `TrainBuySchemesPopup`).
- `UITrain()` — слои плашки: кнопка призыва `btn` (клик → `Tutorial.hide()` + `OnTrainSummon(true)`),
  вагоны `cart0`/`cart1`, локомотив из четырёх спрайтов, поверх — `btnStopAuto` (клик →
  `stopTrainAutoSummon`, интерактивна только при включённом автопризыве, поэтому клик по поезду в
  этом режиме останавливает автопризыв). Если в `data.train` есть `receivedTank` или
  `receivedCollectionItem`, локомотив скрыт и вагон стоит с содержимым.
- `onTankSchemesUpdate`/`onTankSchemesDelete` — `ITEM_NEW_OR_UPDATE`/`ITEM_DELETE` по
  `RESOURCE_TANK_SCHEME` → текст счётчика (`Math.max(count, 0)`, при удалении `0`) и
  `resizeTankSchemes()` (ширина подложки по тексту).
- `onFlyIcons(data)` — `FLY_ICONS` с именем `TRAIN_TANK_SCHEMES` → полёт иконки схемы в счётчик,
  `data.onEnd` в конце.
- `onTrainLevelUpdate(train)` — `TRAIN_LEVEL_UPDATE` (шлют dev-кнопки `TrainUpgradePopup`) →
  `data.train` и полоса уровня.
- `processTutorial()` — указатель на `content.footer.train` на шагах `TutorialUtils.FIRST_TRAIN`/
  `SECOND_TRAIN` (0 и 1), при открытых окнах не показывается; пересчёт по `FlashOverlay.EVENT_ON_CHANGED`
  ([tutorial-architecture.md#integration](tutorial-architecture.md#integration)).

<a id="m-ontrainsummon"></a>
**`OnTrainSummon(btn?)`** — призыв `/ingame/train/summon`; `btn = true` (клик игрока) —
`sendButtonRequest` (блокирует параллельные кнопочные запросы), иначе (автопризыв) — `sendRequest`.
ГДД: [gdd-summon](game-design/train-gdd.md#gdd-summon), [gdd-decision](game-design/train-gdd.md#gdd-decision).
Ответ `ResultUtils.isOk`:
1. `train` есть — `currentLevel`/`nextLevel`/`exp`/`expM` в `data.train` и `progressBar.update`.
2. `account` есть — `Globals.account.build` (так приходит новый шаг туториала).
3. `collectionItem.sellReward` есть — синхронный hold серебра с тегом
   `TrainCollectionItemPopup::RESOURCE_SILVER_COINS`.
4. Окно (`popup`): предмет коллекции — [`onTrainCollectionItemReceived`](#m-ontraincollectionitemreceived).
   Танк — при автопризыве сначала фильтр, неподходящий →
   `OnTrainRefuse`; иначе `TankGetPopup` с `onAccept: OnTrainAccept`, `onRefuse: OnTrainRefuse`,
   `onClose: stopTrainAutoSummon`.
5. `train` есть — окно открывается из конца `animationTrainCart`; нет (сервер вернул непринятый танк,
   [серверный /summon](/workspace/server/.claude/docs/train-architecture.md#cls-trainpage) ветка 2) — сразу.

Ответ не OK: при автопризыве — `stopTrainAutoSummon` и возврат локомотива; вне туториала —
`TrainBuySchemesPopup` при любой ошибке ([#tradeoffs](#tradeoffs) п.3). Ключ `tutorial` ответа не
читается.

<a id="m-ontraincollectionitemreceived"></a>
**`onTrainCollectionItemReceived(item: CollectionTrainJSON)`** — предмет коллекции из ответа призыва;
общий для `OnTrainSummon` и `DevOnTrainCollect`. ГДД:
[gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon),
[collections-gdd.md#gdd-train-drop](game-design/collections-gdd.md#gdd-train-drop). Запоминает снимок
`autoParams = this.autoTrainParams`.
- Автопризыв и дубликат (`sellReward` есть; монета-дубликат или фото, которое разбирается на
  серебро) — `releaseHold` тега `TrainCollectionItemPopup::RESOURCE_SILVER_COINS`, окна нет,
  [`clearTrainCart(autoParams)`](#m-cleartraincart).
- Иначе `TrainCollectionItemPopup.publish` с `onExit: () => clearTrainCart(autoParams)`. `onExit`
  вызывается и при закрытии окна, и при провале загрузки его ассетов
  ([#cls-traincollectionitempopup](#cls-traincollectionitempopup)). Закрытие окна автопризыв не
  останавливает.
- Вне автопризыва окно показывается и для дубликата; после окна груз гаснет и возвращается локомотив.

Вызывается из `onEnd` `animationTrainCart`. Визуал тот же, что у танка: `finalizeTrainCart` оставляет
груз коллекции на вагоне (локомотив скрыт, кнопка поезда выключена), пока окно открыто; снимает груз
`clearTrainCart`.

<a id="m-cleartraincart"></a>
**`clearTrainCart(autoParams: TrainAutoSummonParams | undefined)`** — снятие содержимого вагона после
решения по призыву; общий хвост `OnTrainRefuse` и `onTrainCollectionItemReceived`. ГДД:
[gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon),
[gdd-decision](game-design/train-gdd.md#gdd-decision).
- Запущен другой автопризыв (`this.autoTrainParams !== undefined && !== autoParams`) — ничего не
  делает: поездом уже управляет новый запуск.
- Иначе `animationTrainClearCart` (груз гаснет, 300 мс) → если `autoParams !== undefined &&
  this.autoTrainParams === autoParams` — `OnTrainSummon()` (следующий вагон въезжает без локомотива,
  ветка «локомотив скрыт» в `animationTrainCart`); иначе `animationTrainLocomotive` → пересборка
  `UITrain` (дважды, [#tradeoffs](#tradeoffs) п.7).

Снимок `autoParams` сравнивается по ссылке: игрок остановил автопризыв, пока шли окно или анимация, —
возврат локомотива; остановил и запустил заново (новый объект `autoTrainParams`, цепочку ведёт
`runTrainAutoSummon`) — второго `OnTrainSummon` нет.

<a id="m-ontrainaccept"></a>
**`OnTrainAccept()`** — «Выбрать», `/ingame/train/accept`. `data.train = response.train`; `tutorial` →
`Globals.account.setTutorial` + `processTutorial()`; серебро за заменённый танк из `rewards` → hold
`HomeScreen::BtnTrainAccept::RESOURCE_SILVER_COINS` и полёт монет от поезда в шапку; локальное
событие `HANGAR_UPDATE` (экран перезапрашивает `/ingame/home/hangar`). Дальше: автопризыв —
следующий `OnTrainSummon()`, иначе возврат локомотива, пересборка плашки и ещё один `processTutorial()`
(указатель следующего шага появляется после анимации). ГДД:
[gdd-decision](game-design/train-gdd.md#gdd-decision).

**`OnTrainRefuse()`** — «Продажа», `/ingame/train/refuse`. `data.train = response.train`; если окон нет
(`flashOverlay.count() === 0`) — hold `HomeScreen::BtnTrainRefuse::RESOURCE_SILVER_COINS` и полёт
монет; затем [`clearTrainCart(this.autoTrainParams)`](#m-cleartraincart) — снимок берётся в момент
ответа `/refuse`. ГДД: [gdd-decision](game-design/train-gdd.md#gdd-decision).

Ответы `/accept` и `/refuse` на `isOk` не проверяются ([#tradeoffs](#tradeoffs) п.5).

<a id="m-auto-summon"></a>
**Автопризыв** (ГДД: [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon)):
- `runTrainAutoSummon(rank)` — вызывает `TrainAutoSummonPopup` по «СТАРТ»: включает `btnStopAuto`,
  запускает вращение `TrainAutoSummonBtn`, ставит `autoTrainParams`, `OnTrainSummon()`. Переход «выкл →
  вкл».
- `stopTrainAutoSummon(): boolean` — переход «вкл → выкл»: сброс `autoTrainParams`, выключение
  `btnStopAuto`, остановка вращения; `false`, если автопризыв не был включён. Вызывают
  `TrainAutoSummonBtn`, `btnStopAuto`, `onClose` у `TankGetPopup`, ошибка призыва,
  `onTrainStopAutoSummon` (`TRAIN_STOP_AUTO_SUMMON`). Закрытие `TrainCollectionItemPopup` его не
  вызывает.
- Продолжение после предмета коллекции —
  [`onTrainCollectionItemReceived`](#m-ontraincollectionitemreceived).
- `isTrainAutoSummonTargetTank(received, replaceable)` — подходит ли танк: ранг ниже выбранного → нет;
  ранг равен выбранному, есть заменяемый и мощность выпавшего `<=` его мощности → нет; иначе да (ранг
  выше выбранного — да при любой мощности). Наличие свободной позиции не учитывает
  ([#tradeoffs](#tradeoffs) п.1).
- `disableTrainBtn(value)`/`enableTrainStopAutoSummonBtn(value)` — интерактивность `btn`/`btnStopAuto`.

<a id="m-train-animation"></a>
**Анимации плашки:**
- `animationTrainCart(train, item, onEnd)` — приезд вагона с содержимым (`UITrainCartContent`). Без
  `item` — сразу `data.train`, пересборка, `onEnd`. Локомотив виден — он уезжает влево (800 мс, звук
  `raw/audio/effects/train.mp3`), вагон `cart0` въезжает; иначе новый `cart0` сменяет старый (1100 мс).
  Конец — `finalizeTrainCart`.
- `finalizeTrainCart(item, train, onEnd)` — `data.train = train`; танк: включение кнопки поезда и
  пересборка `UITrain` (вагон с танком остаётся, `train.receivedTank` есть); предмет коллекции:
  пересборки нет, груз остаётся на вагоне, локомотив скрыт, кнопка выключена. Затем `onEnd`.
  Пересобирать для предмета нельзя: сервер очищает `receivedCollectionItem` до ответа `/summon`, и
  `UITrain` показал бы локомотив.
- `animationTrainLocomotive(onEnd)` — локомотив уже виден → `onEnd` сразу; иначе локомотив и пустой
  вагон въезжают (800 мс), `onEnd` вызывается из конца обоих твинов, то есть дважды
  ([#tradeoffs](#tradeoffs) п.7).
- `animationTrainClearCart(onEnd)` — содержимое вагона (танк или груз коллекции) гаснет (300 мс);
  кнопка поезда выключена на время анимации. Вызывается только из
  [`clearTrainCart`](#m-cleartraincart). Переименован из `animationTrainDestroyTank`
  (решение пользователя 2026-10-23).
- `UITrainCartContent(item)` — танк: `Creator.spriteAsync` большого спрайта (`BTank_<asset>`), иначе
  спрайт вагона коллекции `collection_wagon.png`.

**Dev:** `DevOnTrainCollect()` — `/ingame/devTools/collectionSummon { section }`, обработчик ответа —
копия `OnTrainSummon` ([#tradeoffs](#tradeoffs) п.4); выбор секции —
[collections-architecture.md#cls-homescreen-dev-summon-section](collections-architecture.md#cls-homescreen-dev-summon-section).

<a id="cls-buttons"></a>
### `TrainAutoSummonBtn`, `TrainUpgradeBtn` (`implements IViewProvider`)

- `TrainAutoSummonBtn` — кнопка «АВТО». Клик: `screen.stopTrainAutoSummon()` вернул `true` — только
  остановка; иначе `TrainAutoSummonPopup.publish`. `runAnimation()`/`stopAnimation()` — бесконечное
  вращение шестерёнки, пока автопризыв включён.
- `TrainUpgradeBtn` — кнопка «ИНФО», клик → `TrainUpgradePopup.publish`.

<a id="cls-trainupgradeprogressbar"></a>
### `TrainUpgradeProgressBar` (`implements IViewProvider`)

Текст «Уровень N», полоса `exp`/`expM` (`AnimatedProgressBar`). При `currentLevel === nextLevel`
(максимальный уровень) — дописывает `global.levelMax` и скрывает полосу. `update(train)` пересобирает
содержимое. ГДД: [gdd-train-level](game-design/train-gdd.md#gdd-train-level).

<a id="cls-trainautosummonpopup"></a>
### `TrainAutoSummonPopup` (`implements IViewProvider`)

Окно «АВТОАКТИВАЦИЯ». `LOCAL_STORAGE_KEY = "autoTrain"`; конструктор читает сохранённый ранг
(по умолчанию 1); размер заголовка 17. `requestData()` — `/ingame/train/autoData`.
- `UIContent()` — `Vars.AutoSummonAccessLevel > campaignLevel` → `UIAccess()` (текст «Пройди N ур.
  кампании»), иначе `UIRank()` + `UIStart()`.
- `UIRank()` — `ListBox` рангов из `list`: перебор идёт до первого ранга с `chance === 0` включительно
  (он показан с замком, остальные выше не показываются), затем остаются не более 10 последних доступных
  рангов (`slice(max(0, availableCount - 10))`). Если сохранённого ранга нет в списке, выбирается первый
  элемент списка. Выбор сохраняется в `localStorage` при выборе в `ListBox`; автоподстановка первого
  ранга в `localStorage` не пишется. Замок на ранге с нулевым шансом выбор не запрещает
  ([#tradeoffs](#tradeoffs) п.6).
- `UIStart()` — текст `sellInfo` («Более слабые танки будут проданы за серебро»), кнопка «СТАРТ» →
  `screen.runTrainAutoSummon(selectedRank)` и закрытие окна.
- Закрытие — крестик или клик по фону; `onExit` из конфига вызывается при уничтожении (поездом не
  передаётся).

<a id="cls-trainupgradepopup"></a>
### `TrainUpgradePopup` (`implements IViewProvider`)

Окно «УЛУЧШЕНИЕ ПОЕЗДА», данные — `/ingame/train/upgradeData`
([серверный #m-getupgradedatajson](/workspace/server/.claude/docs/train-architecture.md#m-getupgradedatajson)).
ГДД: [gdd-train-level](game-design/train-gdd.md#gdd-train-level).
- `UILevel()` — «Текущий уровень → Следующий уровень», на максимуме вместо следующего `-`.
- `UIChances()` — `ScrollableArea` (вертикальная прокрутка) с `UIRanks()`, разделителем и `UIStars()`;
  высота `min(высота содержимого, MAX_CHANCES_HEIGHT = 385)`.
- `UIRanks()`/`UIStars()` — строки рангов и качества звёзд: шанс на текущем уровне (если `> 0`),
  справа — шанс на следующем (`-` на максимуме) либо «Новое на N ур.» для `importantRankLevel`/
  `importantStarsLevel`. Строка с нулевым текущим шансом выводится, только если это «важный» ранг.
  Проценты — `NumberUtils.intToPercent(value, 1000000)`.
- `UIContent()` — уровни, `UIChances()`, подпись (`maxLevel` на максимуме, иначе `info`), полоса опыта.
- Dev (`Globals.isDevTools()`): кнопки `-`/`+` → `/ingame/devTools/trainRemoveLevel`/`trainAddLevel`,
  перерисовка и `TRAIN_LEVEL_UPDATE`.

<a id="cls-trainbuyschemespopup"></a>
### `TrainBuySchemesPopup` (`implements IViewProvider`)

Окно покупки схем танка. `requestData()` — `/ingame/train/buySchemesData`; `loadAssets()` — пакет
`ShopScreen` (фоны лотов). ГДД: [gdd-buy-schemes](game-design/train-gdd.md#gdd-buy-schemes).
- `UILots()` — три лота из `slots[0..2]`.
- `UILot(slot)` — фон по `id` (1 синий, 2 фиолетовый, 3 золотой), число схем, бонус (если `> 0`),
  цена. `canBuy` — золота в сумке `>=` цены (иначе цена красная, лот не кликается; та же проверка есть
  на сервере, [bag-architecture.md#dup-can-afford](bag-architecture.md#dup-can-afford)). Клик →
  `sendButtonRequest /buySchemes { id }`; OK → hold `TrainBuySchemesPopup::RESOURCE_TANK_SCHEME`,
  полёт `TRAIN_TANK_SCHEMES` с числом иконок по `id` (`[0, 3, 10, 20]`), закрытие окна.
- `UICurrency()` — «Золота в наличии» (иконка `atlas/ui/header/golden_coins_icon.png`, как и в цене лота). Кнопка «КУПИТЬ ЗОЛОТО» без обработчика
  ([#tradeoffs](#tradeoffs) п.8).

<a id="cls-traincollectionitempopup"></a>
### `TrainCollectionItemPopup`

Окно «найден предмет коллекции» после призыва и после клейма комплекта танков. Полное описание —
[collections-architecture.md#cls-traincollectionitempopup-changes](collections-architecture.md#cls-traincollectionitempopup-changes).
Для поезда важно: окно закрывается само после анимации, hold серебра за повтор ставит вызывающий
(`OnTrainSummon`), окно его снимает. `onExit` передаёт
[`onTrainCollectionItemReceived`](#m-ontraincollectionitemreceived) — он ведёт в
[`clearTrainCart`](#m-cleartraincart) (груз гаснет, затем следующий призыв или локомотив); окно
вызывает его из `onDestroy` и из `catch` загрузки ассетов (после `releaseHold`), так что вагон не
остаётся с грузом и цепочка не встаёт и при ошибке загрузки. ГДД:
[collections-gdd.md#gdd-train-drop](game-design/collections-gdd.md#gdd-train-drop).

<a id="cls-tankgetpopup-train"></a>
### `TankGetPopup` в поезде

`src/views/home_screen/popups/tank/TankGetPopup.ts` — общее окно сравнения (поезд, сборка,
коллекции); здесь — поведение для поезда. ГДД: [gdd-decision](game-design/train-gdd.md#gdd-decision).
- `UIButtons(up, down)`: `replaceableTank === null` → одна кнопка «ВЫБРАТЬ» (`onAccept`). Есть
  заменяемый → «ПРОДАЖА» и «ВЫБРАТЬ». Сверху текущий танк, снизу выпавший; «ВЫБРАТЬ» меняет их местами
  (`BtnSwap`, анимация разницы мощности), «ПРОДАЖА» продаёт нижний танк: без обмена — выпавший
  (`onRefuse`), после обмена — заменяемый (`onAccept`). Цвет и порядок кнопок зависят от того, чья
  мощность больше.
- Закрытие по фону (`bgClose` по умолчанию `true`, поезд флаг не передаёт) → `onClose` → остановка
  автопризыва; танк остаётся непринятым. Флаг `bgClose` —
  [collections-architecture.md#cls-tankgetpopup-bgclose](collections-architecture.md#cls-tankgetpopup-bgclose).
- `processTutorial()` — указатель на «ВЫБРАТЬ» на шагах `TutorialUtils.FIRST_TRAIN`/`SECOND_TRAIN`.

<a id="types"></a>
### Типы и события

- `train.d.ts`: `TrainBuySchemesPopupJSON { slots }`, `TankSchemesSlotJSON { id, schemes, bonus,
  priceGoldenCoins }`.
- `home.d.ts`: `TrainJSON { receivedTank?, receivedCollectionItem?, currentLevel, nextLevel, exp, expM }`,
  `TrainUpgradeDataJSON`, `TrainAutoSummonJSON { trainLevel, campaignLevel, list: {rank, chance}[] }`.
- `collection.d.ts`: `CollectionTrainJSON` — часть ответа `/summon` с предметом коллекции
  ([collections-architecture.md#cls-collectiondts](collections-architecture.md#cls-collectiondts)).
- `home.d.ts`: после merge из `HomeScreenJSON` убрано `radioTower`, поле `train` без изменений.
- `GameEvents.TRAIN_LEVEL_UPDATE: TrainJSON`, `GameEvents.TRAIN_STOP_AUTO_SUMMON` — клиентские
  события, слушает `HomeScreen`.

<a id="client-contract"></a>
### Контракт с сервером

Роуты сервера — [серверный #cls-trainpage](/workspace/server/.claude/docs/train-architecture.md#cls-trainpage);
сверено по коду обеих сторон 2026-10-14.

| Роут | Кто вызывает | Что читает клиент |
|---|---|---|
| `/ingame/home` | `HomeScreen.onPreload` | `train` (`TrainJSON`) |
| `/ingame/train/summon` | `OnTrainSummon` | `receivedTank`, `replaceableTank`, `train`, `account`, `collectionItem`; `tutorial` не читает |
| `/ingame/train/accept` | `OnTrainAccept` | `train`, `rewards`, `tutorial` |
| `/ingame/train/refuse` | `OnTrainRefuse` | `train`, `rewards` |
| `/ingame/train/autoData` | `TrainAutoSummonPopup` | `campaignLevel`, `list`; `trainLevel` не читает |
| `/ingame/train/upgradeData` | `TrainUpgradePopup` | всё |
| `/ingame/train/buySchemesData` | `TrainBuySchemesPopup` | `slots[0..2]` |
| `/ingame/train/buySchemes { id }` | `TrainBuySchemesPopup` | `rewards` |
| dev `/ingame/devTools/trainAddLevel`, `/trainRemoveLevel` | `TrainUpgradePopup` | `train`, `upgradeData` |
| dev `/ingame/devTools/collectionSummon { section }` | `DevOnTrainCollect` | как `/summon` |

- Роут `/ingame/train` (index) и dev `/trainAddSchemes` клиент не вызывает.
- Любой `error()` на `/summon` клиент считает «нет схем» ([#tradeoffs](#tradeoffs) п.3). У сервера две
  ошибки: схем меньше одной и `receiveTank() == null`.
- Push-событий у поезда нет. Схемы, золото и серебро обновляются push-ом сумки
  ([bag-architecture.md#client-contract](bag-architecture.md#client-contract),
  [server-push-events-subscription.md](server-push-events-subscription.md)). `HANGAR_UPDATE` на
  клиенте — локальное событие, его шлёт `OnTrainAccept`; серверный `HANGAR_UPDATE` до клиента не
  доходит.
- Автопризыв целиком клиентский: сервер отдаёт шансы, клиент выбирает и продаёт неподходящие танки
  обычным `/refuse`. Порог доступа по уровню кампании сервер не проверяет.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Наблюдения по коду, запуском не проверялись; решения пользователя указаны у пунктов, где они есть. В реестре
`undocumented-areas-known-bugs.md` записей о поезде не было, переносить нечего.

1. **Расхождение с ГДД: автопризыв продаёт танк при свободной позиции.** `isTrainAutoSummonTargetTank`
   не смотрит на `replaceableTank === null`: танк ранга ниже выбранного уходит в `/refuse`, даже если
   встал бы в свободную позицию. По [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon) и
   [gdd-decision](game-design/train-gdd.md#gdd-decision) продажа — только при замене; сервер `/refuse`
   такую продажу принимает
   ([серверный #tradeoffs](/workspace/server/.claude/docs/train-architecture.md#tradeoffs) п.11).
   Решение пользователя 2026-10-14: баг клиента, правка через пайплайн; что делать при свободной
   позиции (взять танк или показать окно) — решается при правке кода.
2. **Продолжение после окна предмета при уходе с экрана.** Если `HomeScreen` уходит с экрана, пока
   `TrainCollectionItemPopup` открыт, `onExit` вызовет `clearTrainCart` (анимации плашки и, в
   автопризыве, `OnTrainSummon`) у ушедшего экрана. Тот же риск есть у `TankGetPopup` (`onAccept`/`onRefuse`). Не
   чинилось, в рантайме не проверено.
3. **Любая ошибка `/summon` — окно покупки.** Клиент не различает «нет схем» и прочие ошибки; вопрос
   «что показывать при ошибке, если схемы есть» открыт в [gdd-open](game-design/train-gdd.md#gdd-open).
   В туториале при ошибке игрок не видит ничего.
4. **Обработчик ответа призыва скопирован.** `DevOnTrainCollect` повторяет колбэк `OnTrainSummon`
   почти дословно (WF `#gdd-function-mapping`); ветка предмета коллекции вынесена в общий
   `onTrainCollectionItemReceived`, остальное ветвление по-прежнему в двух местах. Кандидат — один
   обработчик ответа с параметром роута.
5. **`/accept` и `/refuse` без проверки `isOk`.** Ошибочный ответ (например, двойной клик, когда
   непринятого танка уже нет) записывает `data.train = undefined`, следующая пересборка `UITrain`
   падает на `this.data.train.receivedTank`; при автопризыве цепочка обрывается.
6. **Порог автопризыва только на клиенте.** `Vars.AutoSummonAccessLevel` (10; в коде читается как `Globals.vars.AutoSummonAccessLevel`) —
   после удаления автопризыва радиовышки используется только поездом; сервер его не проверяет. Сохранённый ранг берётся из `localStorage`: если его нет в показанном списке, подставляется первый
   элемент списка, но если это ранг с нулевым шансом (первый «замок» списка, например уровень поезда
   понижен dev-кнопкой), окно показывает его с замком, а «СТАРТ» запускает автопризыв с ним, как описано в [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon). В игре уровень поезда не
   понижается.
7. **`animationTrainLocomotive` зовёт `onEnd` дважды** (конец твина локомотива и вагона; в коде
   `todo: не уверен`). Вне автопризыва `OnTrainAccept` и `clearTrainCart` (после продажи и после окна
   предмета коллекции) пересобирают плашку дважды. Не чинилось.
8. **`TrainBuySchemesPopup`:** кнопка «КУПИТЬ ЗОЛОТО» без `onClick` (переход в магазин закомментирован);
   число лотов, цвета фонов и число летящих иконок зашиты по `id`; при ошибке покупки окно молчит;
   `canBuy` во время удержания золота видит меньше реального
   ([bag-architecture.md#hold-reads](bag-architecture.md#hold-reads)). Копия
   в аэродроме (`AerodromeBuySchemesPopup`) удалена merge `origin/amnesia/fix`.
9. **Hold повисает при уходе с экрана во время анимации** — `animationTrainCart` с `sellReward`, полёты
   монет `/accept`/`/refuse` и схем: `onFlyIcons` слушает только `HomeScreen`
   ([bag-architecture.md#userbag-hold-leak](bag-architecture.md#userbag-hold-leak)).
10. **Правило «максимальный уровень поезда» записано выражением `currentLevel === nextLevel`** в
    `TrainUpgradeProgressBar` и в каждом блоке `TrainUpgradePopup`
    ([gdd-train-level](game-design/train-gdd.md#gdd-train-level)). Кандидат на одну функцию.
11. **Дубли с аэродромом сняты.** Копии `RadioTowerAutoSummonPopup`, `AerodromeBuySchemesPopup`,
    `isRadioTowerAutoSummonTargetAirplane` и события `RADIO_TOWER_*AUTO_SUMMON` удалены merge
    `origin/amnesia/fix`. В `HomeScreen` остался неиспользуемый `interface RadioTowerAutoSummonParams`;
    `HomeScreenAerodrome.ts` и `GameEvents.RADIO_TOWER_UPDATE` ссылаются на удалённый
    `AerodromeRadioTowerJSON` (ошибки `tsc` от автора fix, не чинились).
12. **Состояние поезда меняется в нескольких местах `HomeScreen`** (`OnTrainSummon` по полям,
    `animationTrainCart`, `finalizeTrainCart`, `OnTrainAccept`, `OnTrainRefuse`, `onTrainLevelUpdate`),
    после каждого вручную идёт пересборка плашки или полосы (WF `#no-implicit-order`). Кандидат —
    один метод «применить `TrainJSON`», который сам обновляет плашку и полосу.
13. **Мелочи:** `GameFlash` у `TrainCollectionItemPopup` назван `"TankGetPopup"` (копия);
    `TrainAutoSummonJSON.trainLevel` не читается; ключи окон поезда есть только в `ru.json`.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД области — [train-gdd.md](game-design/train-gdd.md). Правило → клиентская реализация:

| Правило ГДД | Где на клиенте |
|---|---|
| [gdd-scheme](game-design/train-gdd.md#gdd-scheme) — без схем ошибка | `OnTrainSummon`, ветка не OK → `TrainBuySchemesPopup` |
| [gdd-summon](game-design/train-gdd.md#gdd-summon) — один призыв, танк или предмет, опыт поезда +1 | `OnTrainSummon`, полоса `TrainUpgradeProgressBar` |
| [gdd-decision](game-design/train-gdd.md#gdd-decision) — непринятый танк возвращается | вагон в `UITrain`, закрытие `TankGetPopup` по фону |
| [gdd-decision](game-design/train-gdd.md#gdd-decision) — «Взять» с заменой и серебром | `TankGetPopup` «ВЫБРАТЬ», `OnTrainAccept` |
| [gdd-decision](game-design/train-gdd.md#gdd-decision) — «Продать» только при замене | `TankGetPopup.UIButtons`; нарушено автопризывом ([#tradeoffs](#tradeoffs) п.1) |
| [gdd-summon](game-design/train-gdd.md#gdd-summon) — анимация повышения уровня игрока в шапке | `Header.onAccountUpdate` → `LevelUpAnimation.publish` (`src/shared/header/Header.ts`) |
| [gdd-decision](game-design/train-gdd.md#gdd-decision) — класс = тип, замена самого слабого танка класса; окно сравнения: «текущий» сверху, перестановка, «Продажа» продаёт нетекущий, без подтверждения | `TankGetPopup.UITankGet`/`UIButtons`/`BtnSwap` ([#cls-tankgetpopup-train](#cls-tankgetpopup-train)); выбор заменяемого — сервер `HangarUserComponent.getReplaceableTank` |
| [gdd-decision](game-design/train-gdd.md#gdd-decision) — серебро от поезда летит в шапку; при продаже только без открытых окон | `OnTrainAccept`, `OnTrainRefuse` (проверка `flashOverlay.count() === 0` только в refuse), `FlyIconsAnimation.HEADER_SILVER_COINS` |
| [gdd-train-level](game-design/train-gdd.md#gdd-train-level) — уровень, окно прокачки | `TrainUpgradeProgressBar`, `TrainUpgradePopup` |
| [gdd-train-level](game-design/train-gdd.md#gdd-train-level) — максимальный уровень: «(макс ур)», «Поезд полностью улучшен», «-» | `TrainUpgradeProgressBar.UIMain`, `TrainUpgradePopup.UILevel`/`UIRanks`/`UIStars`/`UIContent` |
| [gdd-buy-schemes](game-design/train-gdd.md#gdd-buy-schemes) — наборы за золото | `TrainBuySchemesPopup` |
| [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon) — доступ с 10-го уровня кампании, список до 10 рангов, ранг с замком виден, сохранённый ранг с шансом 0 запускается, ранг на устройстве | `TrainAutoSummonPopup`, `Vars.AutoSummonAccessLevel`, `Globals.logout` |
| [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon) — продажа неподходящего танка только при замене, подходящий ждёт решения | `isTrainAutoSummonTargetTank`, `OnTrainSummon`; продажа при свободной позиции — баг ([#tradeoffs](#tradeoffs) п.1) |
| [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon) — остановка | `stopTrainAutoSummon` и его вызывающие ([#m-auto-summon](#m-auto-summon)) |
| [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon) — настройки «остановка при окончании схем» нет, остановка на ошибке призыва | ветка не OK в `OnTrainSummon` → `stopTrainAutoSummon` |
| [gdd-auto-summon](game-design/train-gdd.md#gdd-auto-summon) — предмет коллекции не останавливает автопризыв: новый — окно, призыв после закрытия (остановлен, пока окно открыто, — не продолжается); дубликат — без окна, призыв дальше | `onTrainCollectionItemReceived` ([#m-ontraincollectionitemreceived](#m-ontraincollectionitemreceived)), `onExit` у `TrainCollectionItemPopup`, [`clearTrainCart`](#m-cleartraincart) |
| [gdd-tutorial](game-design/train-gdd.md#gdd-tutorial) — два шага на «Взять», фиксированных танков нет | клиентские указатели — `tutorial-architecture.md` |
| [collections-gdd.md#gdd-train-drop](game-design/collections-gdd.md#gdd-train-drop) — предмет коллекции вместо танка | `OnTrainSummon`/`DevOnTrainCollect` → `onTrainCollectionItemReceived`, `TrainCollectionItemPopup` |
| [collections-gdd.md#gdd-train-drop](game-design/collections-gdd.md#gdd-train-drop) — визуал призыва с предметом как с танком: груз стоит на вагоне, пока открыто окно, затем гаснет | `finalizeTrainCart` (без пересборки для предмета), [`clearTrainCart`](#m-cleartraincart) |

<a id="file-map"></a>
## 10. Карта файлов компонента

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `src/views/home_screen/popups/train/TrainAutoSummonPopup.ts` | окно настройки автопризыва |
| `src/views/home_screen/popups/train/TrainBuySchemesPopup.ts` | окно покупки схем танка |
| `src/views/home_screen/popups/train/TrainCollectionItemPopup.ts` | окно предмета коллекции после призыва |
| `src/views/home_screen/popups/train/TrainUpgradePopup.ts` | окно прокачки поезда, dev-уровни |
| `src/views/home_screen/popups/train/train.d.ts` | типы наборов схем |
| `src/views/home_screen/TrainAutoSummonBtn.ts` | кнопка «АВТО» |
| `src/views/home_screen/TrainUpgradeBtn.ts` | кнопка «ИНФО» |
| `src/views/home_screen/TrainUpgradeProgressBar.ts` | полоса уровня поезда |
| `assets-src/atlas/home_screen/train/` | спрайты локомотива, вагона, подложки счётчика (пакет `HomeScreen`) |
| `assets-src/raw/audio/effects/train.mp3` | звук отъезда локомотива |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `src/views/home_screen/HomeScreen.ts` | плашка, счётчик схем, обработка `/summon`/`/accept`/`/refuse`, автопризыв, анимации, указатель туториала |
| `src/views/home_screen/home.d.ts` | `TrainJSON`, `TrainUpgradeDataJSON`, `TrainAutoSummonJSON` |
| `src/views/home_screen/popups/tank/TankGetPopup.ts` | зависимость: окно решения по танку |
| `src/views/home_screen/popups/assembly/AssemblyPopup.ts` | `TRAIN_STOP_AUTO_SUMMON` перед своим `TankGetPopup` |
| `src/views/home_screen/popups/profile/collections/collection.d.ts` | `CollectionTrainJSON` — ответ `/summon` с предметом |
| `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts` | открывает `TrainCollectionItemPopup` для монеты следующего ранга |
| `src/plain/GameEvents.ts` | `TRAIN_LEVEL_UPDATE`, `TRAIN_STOP_AUTO_SUMMON` |
| `src/plain/Globals.ts` | `logout()` стирает `autoTrain` из `localStorage` |
| `src/plain/Vars.ts` | `AutoSummonAccessLevel` — порог автопризыва |
| `src/shared/animations/FlyIconsAnimation.ts` | `TRAIN_TANK_SCHEMES` — полёт схем в счётчик |
| `src/views/home_screen/HomeScreenQuest.ts` | полёт схем из награды квеста |
| `src/views/home_screen/popups/idle/IdlePopup.ts` | полёт схем из награды за простой |
| `src/views/home_screen/campaign/CampaignBattleGround.ts` | полёт схем из боя кампании |
| `src/presets/ItemsPresets.ts` | иконка ресурса «схема танка» |
| `src/plain/TutorialUtils.ts` | зависимость: `FIRST_TRAIN`/`SECOND_TRAIN` в указателях поезда (`HomeScreen`, `TankGetPopup`) |
| `src/plain/user/User.ts` | `setTutorial` — вызывает `OnTrainAccept` |
| `src/views/tutorial/Tutorial.ts` | зависимость: `hide()` по клику на поезд |
| `src/plain/user/UserBag.ts` | зависимость: число схем и золота, hold/release |
| `src/plain/items/ItemId.ts` | зависимость: `RESOURCE_TANK_SCHEME`, `RESOURCE_SILVER_COINS`, `RESOURCE_GOLDEN_COINS` |
| `src/plain/RewardUtils.ts` | зависимость: ресурс из `rewards` |
| `src/utils/ResultUtils.ts` | зависимость: `isOk` |
| `src/plain/globals/WSSocket.ts` | зависимость: `sendRequest`/`sendButtonRequest` |
| `src/shared/FlashPublisher.ts` | зависимость: публикация окон |
| `src/shared/flash/GameFlash.ts` | зависимость: обёртка окна, клик по фону |
| `src/shared/ListBox.ts` | зависимость: выбор ранга автопризыва |
| `src/shared/AnimatedProgressBar.ts` | зависимость: полосы опыта |
| `src/presets/RankPresets.ts` | зависимость: значки рангов |
| `src/presets/PanelsPresets.ts`, `src/presets/ButtonPresets.ts` | зависимость: панели и кнопки окон |
| `assets-src/atlas/ui/icons/train.png` | иконка схемы танка (общий атлас UI) |
| `assets-src/atlas/shop_screen/` | фоны лотов покупки (пакет `ShopScreen`) |
| `assets-src/atlas/tech_info/chance/`, `assets-src/atlas/tech_info/stars/` | полосы шансов и звёзды в окнах прокачки и автопризыва |
| `assets-src/raw/lang/ru/ru.json` | ключи `homeScreen.tankPopup`, `upgradeTrainPopup`, `autoTrainPopup`, `trainCollectionPopup`, `shopScreen.train` |
| `tools/src/config.yaml` | пакеты `HomeScreen`, `ShopScreen` ([asset-packaging.md#regular-atlas](asset-packaging.md#regular-atlas)) |
