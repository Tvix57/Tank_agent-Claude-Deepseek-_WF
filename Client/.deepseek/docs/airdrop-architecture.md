# AirDrop — ящики с золотом на поле боя кампании (клиент)

> **auto-create** — документ составлен по существующему коду (код в рамках задачи не менялся),
> 2026-10-14. Запуском не проверялось.
> Сверено с кодом после merge `origin/amnesia/fix` 2026-10-19.
> Серверная сторона: `/workspace/server/.claude/docs/airdrop-architecture.md` (тоже auto-create).

ГДД: [`game-design/airdrop-gdd.md`](game-design/airdrop-gdd.md) (одна копия на client и server).

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

AirDrop — случайное событие на поле боя кампании главного экрана. Над полем пролетает тень самолёта,
затем на парашюте опускается цветной ящик. Пока не истёк таймер под ящиком, игрок может нажать на
него и получить золото (`ItemId.RESOURCE_GOLDEN_COINS`). Цвет ящика, количество золота, шансы,
суточный лимит и срок жизни определяет сервер; клиент только спрашивает, не выпал ли ящик, показывает
его и отправляет запрос на сбор.

Вся клиентская логика — в одном классе `AirDrop`, который создаёт `CampaignBattleGround` и встраивает
в свой корневой `layout`. Отдельного экрана, событий `GameEvents` и push-подписок у области нет.

<a id="lifecycle"></a>
### Жизненный цикл на клиенте

1. **Опрос** ([#gdd-spawn-chance](game-design/airdrop-gdd.md#gdd-spawn-chance)). Конструктор `AirDrop` создаёт `Every` на 60 000 мс: первый вызов `onAirDropEvent()`
   идёт сразу, затем раз в минуту. Пока `airDropWait = true` (ящик летит или лежит), запрос не
   отправляется.
2. **Ответ `/ingame/campaign/sendAirDrop`.** Успех — `airDropWait = true`, спрайт ящика меняется на
   `box_<airDropType>.png`. Если `airDropInstant = true` (ящик уже был на сервере, например после
   перезагрузки) — ящик сразу показывается на земле (`showDropBox`). Иначе запускаются пролёт тени
   и падение ящика. Ошибки `count` / `bad luck` / `time` только пишутся в лог.
3. **Анимация** ([#gdd-plane-flight](game-design/airdrop-gdd.md#gdd-plane-flight), [#gdd-box-drop](game-design/airdrop-gdd.md#gdd-box-drop)). Все твины — на `tweenSystem` боя. Тень самолёта летит 4 с; тень ящика — 6 с с
   задержкой 1 с; ящик с парашютом — 5 с с задержкой 2 с, размер падает с ×4 до ×1. Падение и тень
   ящика заканчиваются через 7 с после ответа; затем парашют скрывается и вызывается `showDropBox`.
4. **На земле** ([#gdd-lifetime](game-design/airdrop-gdd.md#gdd-lifetime)). `showDropBox` показывает таймер, включает кнопку и раз в секунду обновляет остаток
   `airDropDeadTime − TimeUtils.nowMls()` в формате `TimeUtils.timeDDHHMMSS_Mls`. Когда срок
   прошёл — ящик, тень и таймер сжимаются до нуля (`animationHide`), `airDropWait = false`.
5. **Сбор** ([#gdd-collect](game-design/airdrop-gdd.md#gdd-collect)). Нажатие отключает кнопку и шлёт `/ingame/campaign/getAirDrop` через
   `sendButtonRequest`. При успехе и наличии золота в ответе: hold золота в сумке, скрытие ящика,
   над местом ящика появляется иконка золота с числом (увеличение 0,5 с, пауза, уменьшение 0,5 с),
   затем `FlyIconsAnimation.HEADER_GOLDEN_COINS` (5 иконок) из этой точки к счётчику в шапке;
   по окончании полёта hold снимается.

<a id="references"></a>
## 2. Референсы

- Тень самолёта сделана как тень взлетающих с аэродрома самолётов: спрайт, перекрашенный в чёрный
  через `PIXI.filters.ColorMatrixFilter.brightness(0)`, с прозрачностью. Спрайт — собственный
  `atlas/airDrop/plane.png`, не атлас самолёта.
- Выдача награды с hold-ом и `FlyIconsAnimation` повторяет `CampaignBattleGround.onTankDestroyedEvent`
  (серебро за танк) и экраны с золотом (`GoldenCoinsOfferPopup`, `AchievementLine`).

<a id="patterns"></a>
## 3. Паттерны

- **Сервер авторитетен**: клиент не хранит состояние airDrop между сессиями, после перезагрузки
  восстанавливает ящик по `airDropInstant = true` из первого опроса.
- **Периодический опрос** через `src/plain/Every` (тик привязан к `layout`, умирает вместе с ним).
- **Дерево `Layout` с именованными детьми** (`airDrop.plane`, `airDrop.box.boxImg.chute` и т.д.),
  доступ через `layout.child(path)`; смена цвета — `replaceByName("color", ...)`.
- **Удержание ресурса на время анимации**: `UserBag.holdResource` → `FlyIconsAnimation` →
  `UserBag.releaseHold` (подробно — `bag-architecture.md`).
- **Dev-инструменты** только при `Globals.isDevTools()`.

<a id="class-list"></a>
## 4. Список классов

Код в рамках задачи не создавался и не менялся; перечислены составляющие области:

- `src/views/home_screen/campaign/AirDrop.ts` — `AirDrop`.
- `src/types/interfaces.d.ts` — `AirDropSendJSON`, `AirDropGetJSON`.
- `src/views/home_screen/campaign/CampaignBattleGround.ts` — создание `AirDrop` (airDrop-часть).

<a id="anchors"></a>
## 5. Навигация (якоря)

[`#purpose`](#purpose) · [`#lifecycle`](#lifecycle) · [`#references`](#references) ·
[`#patterns`](#patterns) · [`#class-list`](#class-list) · [`#class-nav`](#class-nav) ·
[`#classes`](#classes) · [`#cls-airdrop`](#cls-airdrop) · [`#m-ui`](#m-ui) ·
[`#m-requests`](#m-requests) · [`#m-animations`](#m-animations) · [`#m-dev`](#m-dev) ·
[`#types`](#types) · [`#cls-campaignbattleground`](#cls-campaignbattleground) ·
[`#client-contract`](#client-contract) · [`#tradeoffs`](#tradeoffs) · [`#gdd-link`](#gdd-link) ·
[`#file-map`](#file-map) · [`#file-map-direct`](#file-map-direct) ·
[`#file-map-indirect`](#file-map-indirect)

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс / тип | Роль | Раздел |
|---|---|---|
| `AirDrop` | вся клиентская логика и вид airDrop | [#cls-airdrop](#cls-airdrop) |
| `AirDropSendJSON`, `AirDropGetJSON` | ответы сервера | [#types](#types) |
| `CampaignBattleGround` (airDrop-часть) | создание и встраивание | [#cls-campaignbattleground](#cls-campaignbattleground) |

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-airdrop"></a>
### `AirDrop` (`src/views/home_screen/campaign/AirDrop.ts`)

Поля:
- `airDropCheckTimer: Every` — минутный опрос сервера.
- `airDropLife: Every | undefined` — секундный таймер ящика на земле.
- `airDropWait: boolean` — ящик в полёте или на земле; блокирует опрос.
- `layout` — корневой `layout` `CampaignBattleGround`; `screen` — `HomeScreen` (generation-объект
  запросов); `tweenSystem` — твины боя.

`constructor(bg, layout)` — добавляет `UIAirDrop()` в `layout` под именем `airDrop`, создаёт
`airDropCheckTimer` (первый опрос — сразу).

<a id="m-ui"></a>
#### Построение вида

- `UIAirDrop()` — контейнер на весь `layout` с детьми `plane`, `box` (`x: -49, y: -122`) и, при
  dev-инструментах, колонкой кнопок `UIDev()` в левом нижнем углу.
- `UIPlane()` — спрайт `atlas/airDrop/plane.png`, `alpha 0.4`, масштаб 0,7, фильтр яркости 0 (чёрная
  тень); скрыт.
- `UIBox()` — контейнер масштаба 0,15 с детьми `shadow`, `boxImg`, `reward`, `btn`, `timer`
  (`y: 150`); скрыт.
- `UIBoxImg()` — `color` (по умолчанию `box_blue.png`) и скрытый `chute.png`.
- `UIBoxShadow()` — `box_shadow.png` со смещением.
- `UIBoxTimer()` — текст таймера (скрыт до приземления).
- `UIRewardText()` — иконка золота + число, начальный масштаб 0.
- `UIButton()` — невидимая кнопка 200×200 поверх ящика, изначально неинтерактивна. Обработчик:
  выключает кнопку, `sendButtonRequest("/ingame/campaign/getAirDrop")`; в ответе сбрасывает
  `airDropWait`, берёт золото через `RewardUtils.getResource`; при `isOk` и найденной награде —
  `holdResource("GoldenCoinsOffer::RESOURCE_GOLDEN_COINS", ...)`, `animationHide()`,
  `animationReward(count)`. Ошибка запроса — только `console.warn`. ГДД:
  [#gdd-collect](game-design/airdrop-gdd.md#gdd-collect).
- `setDropBoxColor(color)` — заменяет спрайт `color` на `atlas/airDrop/box_<color>.png`; строки цвета
  приходят с сервера (`grey`, `green`, `blue`, `purple`, `orange`, `red`). ГДД:
  [#gdd-box-quality](game-design/airdrop-gdd.md#gdd-box-quality).

<a id="m-requests"></a>
#### Опрос и показ ящика

- `onAirDropEvent()` — при `airDropWait` выходит; иначе `sendRequest("/ingame/campaign/sendAirDrop")`.
  Успех: `airDropWait = true`, `setDropBoxColor`, затем `showDropBox` (instant) либо
  `animationPlane` + `animationBox`. Ошибки `count`/`bad luck`/`time` — `Logger.info`. ГДД:
  [#gdd-spawn-chance](game-design/airdrop-gdd.md#gdd-spawn-chance), [#gdd-daily-limit](game-design/airdrop-gdd.md#gdd-daily-limit).
- `showDropBox(data)` — делает ящик видимым, показывает таймер (масштаб 4), включает кнопку, удаляет
  прежний `airDropLife` и создаёт новый `Every` на 1 с: по истечении `airDropDeadTime` удаляет себя и
  вызывает `animationHide`, иначе обновляет текст таймера. ГДД: [#gdd-lifetime](game-design/airdrop-gdd.md#gdd-lifetime).

<a id="m-animations"></a>
#### Анимации

- `animationPlane()` ([#gdd-plane-flight](game-design/airdrop-gdd.md#gdd-plane-flight)) — 4 с, позиция `(-100, 100) → (50, -400)`, видимость на время твина.
- `animationBox(data)` — скрывает ящик и запускает две анимации ниже.
- `animationBoxShadow(box)` ([#gdd-box-drop](game-design/airdrop-gdd.md#gdd-box-drop)) — 6 с, задержка 1 с, позиция `(2500, 1400) → (0, 0)`, масштаб 3 → 1,
  `Easing.outSine`.
- `animationBoxMain(box, data)` ([#gdd-box-drop](game-design/airdrop-gdd.md#gdd-box-drop)) — 5 с, задержка 2 с, позиция `(-500, 4500) → (0, 0)`, масштаб 4 → 1;
  на старте показывает ящик и парашют, по окончании скрывает парашют и вызывает `showDropBox`.
- `animationHide()` — `animationHideBox` + `animationHideShadow` + `animationHideTimer`.
- `animationHideBox()` — `airDropWait = false`, выключает кнопку, сжимает `boxImg` до 0 за 0,5 с.
- `animationHideShadow()`, `animationHideTimer()` — сжатие до 0 за 0,5 с.
- `animationReward(count)` ([#gdd-collect](game-design/airdrop-gdd.md#gdd-collect)) — число в `rewardText`; масштаб `reward` 0 → 15 (0,5 с, задержка 0,5 с),
  затем → 0 (0,5 с, задержка 0,1 с); в конце `FlyIconsAnimation.play(HEADER_GOLDEN_COINS, 5,
  <мировая позиция reward>)` и `releaseHold` в колбэке.

<a id="m-dev"></a>
#### Dev-инструменты

- `UIDev()` — три текстовые кнопки: `airChance` → `devAirChance()`, `airDrop` → `devAirDropEvent()`,
  `airReset` → `/ingame/devTools/airDropReset` (лог в консоль).
- `devAirDropEvent()` — `/ingame/devTools/airDropForce`; успех — как неинстантный ответ (всегда с
  анимацией). `airDropWait` перед запросом не проверяет и не сбрасывает.
- `devAirChance()` — сбрасывает `airDropWait`, `/ingame/devTools/airDropChance`; успех — как
  неинстантный ответ. Ошибки обоих — `console.log`.

Обработка ответа (`airDropWait = true` → цвет → анимации) повторена в трёх методах почти дословно,
отличаются только роут и ветка `airDropInstant`.

<a id="types"></a>
### Типы (`src/types/interfaces.d.ts`)

- `AirDropSendJSON` — `{ airDrop: { airDropInstant: boolean; airDropType: string; airDropDeadTime: number } }`.
- `AirDropGetJSON` — `{ airDropReward: { reward: ItemJSON } }`.

<a id="cls-campaignbattleground"></a>
### `CampaignBattleGround` (airDrop-часть)

Поле `airDrop: AirDrop`; в конструкторе — `new AirDrop(this, this.layout)`, следом идёт `RankedProfile`
(рейтинговый бой, не область airDrop; `campaign-architecture.md`). Других обращений airDrop
нет: `AirDrop` берёт у поля боя только `tweenSystem` и `screen`.

<a id="client-contract"></a>
### Контракт с сервером

Серверная сторона — `/workspace/server/.claude/docs/airdrop-architecture.md#client-contract`.

| Роут | Когда | Ответ / ошибки |
|---|---|---|
| `/ingame/campaign/sendAirDrop` | раз в минуту, если `airDropWait = false` | `payload.airDrop` (`AirDropSendJSON`); ошибки `time`, `count`, `bad luck` |
| `/ingame/campaign/getAirDrop` | нажатие на ящик | `payload.airDropReward` (`AirDropGetJSON`); ошибка `no air drop` (клиент отдельно не обрабатывает) |
| `/ingame/devTools/airDropChance` | dev-кнопка `airChance` | как `sendAirDrop` |
| `/ingame/devTools/airDropForce` | dev-кнопка `airDrop` | как `sendAirDrop`, ящик гарантирован |
| `/ingame/devTools/airDropReset` | dev-кнопка `airReset` | пустой `ok` (сервер сбрасывает только суточный счётчик) |

`airDropDeadTime` — абсолютное серверное время в мс; клиент сравнивает его с `TimeUtils.nowMls()`
(время, синхронизированное с сервером). Сервер добавляет к сроку жизни 5,5 с на клиентскую анимацию.
Строка цвета для жёлтого ящика — `orange` (совпадает с именем файла `box_orange.png`).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Явных комментариев о компромиссах в коде нет. Ниже — наблюдения по коду; расхождения с ГДД помечены
«ГДД».

> **Отложено (решение пользователя, 2026-10-14):** все пункты сейчас не исправляются, ГДД под код не
> правится. При задаче по airDrop — предложить исправление, сверив с актуальным кодом.

1. **Анимации зависят от скорости боя.** Твины идут на `tweenSystem` боя, который обновляется в
   `Battle.update` с множителем `timeScale` (dev-кнопки скорости) и `dt`, ограниченным 50 мс за кадр.
   При ускорении/замедлении боя или просадке FPS меняется длительность пролёта и падения.
2. **ГДД: на земле ящик живёт меньше 5 минут** ([#gdd-lifetime](game-design/airdrop-gdd.md#gdd-lifetime)). От ответа до
   приземления 7 с, сервер закладывает на анимацию 5,5 с: таймер после приземления стартует около 4:58.
3. **ГДД: ящик появляется во время туториала** ([#gdd-spawn-chance](game-design/airdrop-gdd.md#gdd-spawn-chance)). Опрос
   идёт с момента создания `CampaignBattleGround`; сервер в `/sendAirDrop` туториал тоже не проверяет.
4. **ГДД: неудачный сбор не убирает ящик** ([#gdd-collect](game-design/airdrop-gdd.md#gdd-collect)). `catch` только пишет
   в консоль: кнопка остаётся выключенной, ящик лежит до конца таймера. При ошибочном ответе обращение
   к `response.airDropReward.reward` до проверки `isOk` бросит исключение (тоже уходит в `catch`).
   Отказ `sendButtonRequest` из-за другой активной кнопки (`ERR_WS_BUTTON_ALREADY_PRESSED`) ведёт к
   тому же.
5. **ГДД: проверка «раз в минуту» может пропускаться** ([#gdd-spawn-chance](game-design/airdrop-gdd.md#gdd-spawn-chance)).
   Клиент отсчитывает 60 с от отправки, сервер — 60 с от обработки. Если следующий запрос дойдёт
   раньше, сервер ответит `time`, и бросок сдвинется ещё на минуту. В обратную сторону: кулдаун
   сервера живёт только в памяти (server `#tradeoffs` п.1), а клиент шлёт первый запрос сразу при
   создании поля боя — после перезагрузки бросок может пройти раньше, чем через минуту.
6. **ГДД: ящик, забранный после полуночи, засчитывается в прошедшие сутки**
   ([#gdd-daily-limit](game-design/airdrop-gdd.md#gdd-daily-limit)). Серверный `getAirDrop()` увеличивает счётчик без
   суточного сброса; при следующей проверке лимита счётчик обнуляется, и ящик в новых сутках не
   учитывается (server `#tradeoffs` п.3). Клиентской правки не требует.
7. **Первый тик `airDropLife` вызывается в конструкторе `Every`**, до присвоения `this.airDropLife`.
   Если `airDropDeadTime` уже прошёл в момент `showDropBox`, `this.airDropLife.remove()` обращается к
   прежнему (уже удалённому) таймеру или к `undefined` — во втором случае `TypeError`.
8. **Dev-кнопка `airDrop` не проверяет `airDropWait`** и не останавливает `airDropLife` прежнего
   ящика до приземления нового: таймер старого ящика может скрыть новый во время падения.
9. **Общий тег hold** `GoldenCoinsOffer::RESOURCE_GOLDEN_COINS` с `GoldenCoinsOfferPopup`,
   `AchievementLine`, `CollectionAlbumCard`, `CollectionsUSSROperationsSection`
   (`bag-architecture.md#consumers`): одновременные награды золотом снимают удержание друг друга.
10. **Дублирование обработки ответа** в `onAirDropEvent`/`devAirDropEvent`/`devAirChance`.
11. **Баг из ТЗ «Правки 2»** («самолёт пролетает и ничего не сбрасывает, ресет не помогает, после
    перезагрузки ящик на поле»). Исправлен ли он, неизвестно (пользователь, 2026-10-14); по коду
    однозначно не воспроизводится. Кандидаты: п.8, п.1, п.4. `airReset` на сервере не трогает
    активный ящик, поэтому сброс не убирает зависший ящик.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`game-design/airdrop-gdd.md`](game-design/airdrop-gdd.md).

| Раздел ГДД | Где реализовано на клиенте |
|---|---|
| [#gdd-spawn-chance](game-design/airdrop-gdd.md#gdd-spawn-chance) | `onAirDropEvent`, `airDropCheckTimer`, `airDropWait` (шансы считает сервер) |
| [#gdd-daily-limit](game-design/airdrop-gdd.md#gdd-daily-limit) | только сервер; клиент логирует ошибку `count` |
| [#gdd-box-quality](game-design/airdrop-gdd.md#gdd-box-quality) | `setDropBoxColor` (цвет выбирает сервер) |
| [#gdd-reward](game-design/airdrop-gdd.md#gdd-reward) | только сервер; клиент показывает `count` из ответа |
| [#gdd-lifetime](game-design/airdrop-gdd.md#gdd-lifetime) | `showDropBox`, `animationHide` |
| [#gdd-plane-flight](game-design/airdrop-gdd.md#gdd-plane-flight) | `UIPlane`, `animationPlane` |
| [#gdd-box-drop](game-design/airdrop-gdd.md#gdd-box-drop) | `UIBox*`, `animationBox`, `animationBoxShadow`, `animationBoxMain` |
| [#gdd-collect](game-design/airdrop-gdd.md#gdd-collect) | `UIButton`, `animationHideBox`, `animationReward` |

Дублей по смыслу среди функций с бизнес-смыслом нет; три обработчика ответа ([#tradeoffs](#tradeoffs) п.10) выражают одно
правило «показать выпавший ящик», два из них — dev.

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от корня репозитория `client`.

<a id="file-map-direct"></a>
### Файлы прямого влияния

- `src/views/home_screen/campaign/AirDrop.ts` — вся логика и вид airDrop: опрос, анимации, таймер, сбор награды, dev-кнопки.
- `src/types/interfaces.d.ts` — `AirDropSendJSON`, `AirDropGetJSON` (ответы сервера).
- `assets-src/atlas/airDrop/` — атлас области: `plane.png`, `chute.png`, `box_shadow.png`, `box_{grey,green,blue,purple,orange,red}.png`.

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

- `src/views/home_screen/campaign/CampaignBattleGround.ts` — создание `AirDrop` и встраивание в поле боя кампании.
- `src/views/home_screen/HomeScreen.ts` — загрузка пакета ассетов `AirDrop` в `loadAssets`; цикл `battle.update`, двигающий твины airDrop.
- `tools/src/config.yaml` — строка атласа `airDrop` → пакет `AirDrop`.
- `assets/bundles/fullassetmap.wr` — сгенерированная запись пакета `AirDrop`.
- `src/views/battle/ground/BattleGround.ts` — зависимость: `tweenSystem`, `screen`.
- `src/battle/Battle.ts` — зависимость: `update()` обновляет `tweenSystem` с `timeScale`.
- `src/plain/Every.ts` — зависимость: периодический таймер опроса и жизни ящика.
- `src/plain/user/UserBag.ts` — зависимость: `holdResource`/`releaseHold` золота.
- `src/shared/animations/FlyIconsAnimation.ts` — зависимость: полёт иконок золота к шапке.
- `src/plain/RewardUtils.ts` — зависимость: выбор золота из награды.
- `src/plain/globals/WSSocket.ts` — зависимость: `sendRequest`/`sendButtonRequest`, отказ при `errCode`.
- `src/utils/TimeUtils.ts` — зависимость: серверное время и формат таймера.

Сверка полноты: `grep -rniE "airdrop" src assets-src tools/src/config.yaml assets/bundles` даёт
`AirDrop.ts`, `CampaignBattleGround.ts`, `interfaces.d.ts`, `HomeScreen.ts`, атлас, `config.yaml` и
`fullassetmap.wr`.
