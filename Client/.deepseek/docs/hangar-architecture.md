# Ангар (танки) — клиент

> **auto-create** — документ составлен по существующему коду (код в рамках задачи не менялся),
> 2026-10-17; сверено с кодом после merge `origin/amnesia/fix` (2026-10-19, незакоммичен). Запуском не проверялось.
> Серверная сторона: `/workspace/server/.claude/docs/hangar-architecture.md` (тоже auto-create).

ГДД: [`game-design/hangar-gdd.md`](game-design/hangar-gdd.md) (одна копия на client и server).

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

Ангар — команда танков игрока: 12 слотов, 3 ряда по 4 ([#gdd-slots](game-design/hangar-gdd.md#gdd-slots)). Танк из
слота N ангара стоит в слоте N поля боя кампании. В коде слот хранится как `position` = N − 1
(глоссарий, «Слот»). Слоты закреплены за типами танка (задаёт сервер, `TankType.TYPE_POSITION`):

| Слоты (ГДД) | `position` (код) | Тип танка |
|---|---|---|
| 1–4 | 0–3 | тяжёлые |
| 5–8 | 4–7 | средние |
| 9–12 | 8–11 | лёгкие и ПТ (общий ряд) |

Танк попадает в ангар только через три источника: поезд (`/ingame/train/accept`), сборку
(`/ingame/assembly/take`) и экспериментальные танки коллекций (`.../takeReward`). Во всех трёх случаях
сервер сам решает, в какой слот встанет танк: первый свободный слот его ряда, а если все
заняты — место самого слабого по мощности танка ряда ([#gdd-placement](game-design/hangar-gdd.md#gdd-placement)). Заменённый танк удаляется из сумки. Перед
решением игрок видит общее окно сравнения `TankGetPopup`.

Ручной перестановки, снятия танка со слота и запаса танков вне ангара на клиенте нет. Отдельного
окна ангара тоже нет: ангар — блок 4×3 в подвале главного экрана (`HomeScreen.UIHangar`), клик по танку
открывает окно информации `TankInfoPopup`.

<a id="lifecycle"></a>
### Жизненный цикл на клиенте

1. **Загрузка.** `HomeScreen.onPreload` получает `/ingame/home` → `HomeScreenJSON.hangar`
   (`HangarJSON`: массив `TankPositionJSON { position, tankUid | null }`, 12 записей по порядку
   позиций). Сами данные танков берутся из сумки: `Globals.bag.getTank(tankUid)`.
2. **Отрисовка.** `UIHangar` строит сетку из 4 колонок по порядку массива; пустая позиция —
   полупрозрачная заглушка с мощностью 0.
3. **Получение танка.** Источник (поезд, сборка, коллекция) показывает `TankGetPopup` с
   `receivedTank` и `replaceableTank` из ответа сервера. Решение уходит в маршрут источника.
4. **Обновление.** После успешного «взять» источник сам вызывает
   `GameEvents.emitter.emit(GameEvents.HANGAR_UPDATE)`. `HomeScreen.onHangarUpdate` перезапрашивает
   `/ingame/home/hangar`, ставит изменившиеся танки в идущий бой (`battle.replaceTank`) и
   перерисовывает блок ангара.
5. **Следующий бой.** Состав для нового боя кампании собирает сервер (`User.createTeam`) — клиент
   получает его в ответе на запрос боя (см. [campaign-architecture.md](campaign-architecture.md)).

Маршрутов `/ingame/hangar/*` нет. Единственный маршрут ангара — `/ingame/home/hangar` (`HomePage`).

<a id="references"></a>
## 2. Референсы

- Окно сравнения самолётов `AirplaneGetPopup` скопировано с `TankGetPopup`: та же схема кнопок,
  перестановки и анимации мощности ([aerodrome-architecture.md](aerodrome-architecture.md)).
- Серверная расстановка самолётов (`AerodromeUserComponent`) скопирована с `HangarUserComponent`.

<a id="patterns"></a>
## 3. Паттерны

- Окна — `IViewProvider` + `FlashLayout` + `GameFlash` через `FlashPublisher.publish`; статический
  `publish(screen, config)`.
- Решение в окне — колбэки `onAccept`/`onRefuse`/`onClose` в конфиге: окно не знает маршрутов
  источника.
- Обновление после смены состава — локальное клиентское событие `GameEvents.HANGAR_UPDATE` без
  данных и перезапрос (pull). Серверного push-события ангара нет (рекомендованная схема push —
  [server-push-events-subscription.md](server-push-events-subscription.md)).
- Отрисовка танка — общие пресеты `TankPresets` (большая/малая карточка, имя, параметры).

<a id="class-list"></a>
## 4. Список классов

Задача — первичная документация, классы не создавались и не менялись. Компонент целиком:

- `TankGetPopup` — окно сравнения и решения по новому танку.
- `TankInfoPopup` — окно информации о танке.
- `HomeScreen` (ангарная часть) — блок ангара, обработчик `HANGAR_UPDATE`, вызовы `TankGetPopup`.
- `home.d.ts` — `HangarJSON`, `TankPositionJSON`.
- `GameEvents.HANGAR_UPDATE`.

<a id="anchors"></a>
## 5. Навигация (якоря)

| Якорь | Что там |
|---|---|
| `#purpose`, `#lifecycle` | бизнес-логика и жизненный цикл |
| `#cls-tankgetpopup` | окно сравнения, кнопки, перестановка |
| `#cls-tankinfopopup` | окно информации |
| `#cls-homescreen-hangar` | блок ангара и `onHangarUpdate` |
| `#cls-types` | `HangarJSON`, `TankPositionJSON` |
| `#cls-hangar-update` | событие `HANGAR_UPDATE` и кто его шлёт |
| `#contract` | контракт с сервером |
| `#tradeoffs` | находки с номерами строк |
| `#file-map` | карта файлов |

<a id="class-nav"></a>
## 6. Оглавление по классам

- [TankGetPopup](#cls-tankgetpopup)
- [TankInfoPopup](#cls-tankinfopopup)
- [HomeScreen — ангарная часть](#cls-homescreen-hangar)
- [Типы home.d.ts](#cls-types)
- [GameEvents.HANGAR_UPDATE](#cls-hangar-update)
- [Контракт с сервером](#contract)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-tankgetpopup"></a>
### `TankGetPopup` (`src/views/home_screen/popups/tank/TankGetPopup.ts`)

ГДД: [#gdd-compare-window](game-design/hangar-gdd.md#gdd-compare-window).

Окно решения по новому танку. Общее для поезда, сборки и экспериментальных танков коллекций; про
особенности вызовов — [train-architecture.md#cls-tankgetpopup-train](train-architecture.md#cls-tankgetpopup-train),
[assembly-architecture.md](assembly-architecture.md),
[collections-architecture.md#cls-tankgetpopup-bgclose](collections-architecture.md#cls-tankgetpopup-bgclose).

Конфиг `HomeTankGetPopupConfig` (19–27): `receivedTank`, `replaceableTank | null`, `onAccept`,
`onRefuse`, необязательные `bgClose` (по умолчанию закрытие по фону разрешено), `onClose`, `onExit`.
Поле `swapped` (35) — показан ли сейчас новый танк на месте текущего.

**`UITankGet()`** (80–135) — два вида окна:
- `replaceableTank === null` (свободный слот): заголовок «НОВЫЙ ТАНК», большая карточка
  `TankBigLayout`, параметры, одна кнопка.
- есть заменяемый: сверху `top` — «текущий» танк (на позиции), снизу `bottom` — сравниваемый с
  разницей мощности (`TankSmallLayout(data, compared)`), над верхним — пустой слот `animatePower`.
Подпись «ЗАКРЫТЬ» внизу — только если `bgClose !== false`.

**`UIButtons(up, down)`** (145–204; ГДД: [#gdd-compare-window](game-design/hangar-gdd.md#gdd-compare-window) — подсветка, продажа, выбор) — кнопки по паре «верхний/нижний»:
- `up === null` — зелёная «ВЫБРАТЬ» (`accept`): `onAccept()` и закрытие.
- `down.power > up.power` (снизу мощнее) — красная «ПРОДАЖА» слева, зелёная «ВЫБРАТЬ» справа.
- иначе — серая «ВЫБРАТЬ» слева, красная «ПРОДАЖА» справа.
«ВЫБРАТЬ» при заменяемом танке только меняет танки местами (`BtnSwap`), запроса нет. «ПРОДАЖА»
продаёт нижний танк: без перестановки — `onRefuse()` (продать новый), после перестановки —
`onAccept()` (взять новый, продать заменённый). Запрос уходит только по «ПРОДАЖА» или по
единственной «ВЫБРАТЬ».

**`BtnSwap()`** (223–247; ГДД: [#gdd-compare-window](game-design/hangar-gdd.md#gdd-compare-window) — перестановка) — меняет местами карточки `top`/`bottom`, перестраивает кнопки, запускает
`animatePower(разница мощности)`, переключает `swapped`.

**`animatePower(value)`** (206–221) — всплывающее «±N» мощности над верхним танком (зелёное при
росте, красное при падении).

**`processTutorial()`** (249–265) — на шагах туториала `TutorialUtils.FIRST_TRAIN` (0) и
`TutorialUtils.SECOND_TRAIN` (1) указатель на кнопку `accept`, иначе выключает указатель ([tutorial-architecture.md](tutorial-architecture.md)).

**`getAsGameFlash()`** (267–283; ГДД: [#gdd-compare-window](game-design/hangar-gdd.md#gdd-compare-window) — закрытие по фону задаёт источник) — флеш `TankGetPopup`; клик по фону при `bgClose !== false`
закрывает окно и вызывает `onClose` (решение не принимается).

Тривиальные: `onCreate` (47), `onDestroy` → `onExit` (52), `UIMain` (58, анимация появления и
блокировка ввода экрана), `UITank(data, compared)` (137, имя + малая карточка + параметры),
`publish` (285), `view` (290).

<a id="cls-tankinfopopup"></a>
### `TankInfoPopup` (`src/views/popups/TankInfoPopup.ts`)

ГДД: [#gdd-tank-info](game-design/hangar-gdd.md#gdd-tank-info).

Окно только для просмотра: `TankBigLayout` (флаг страны, картинка, «прототип», имя, ранг, тип,
уровень, звёзды, мощность) и `ParamsLayout` (прочность, урон, перезарядка, тип снаряда, тип брони).
Закрывается по фону; флеш параллельный (`setParallel(true)`, 96), то есть открывается поверх других
окон без очереди. Конфиг: `data: TankJSON`, `onExit?`. Вызывают: блок ангара на главной, поле боя
(`BattleGroundTank`), окно Battlefield, профиль, кодекс.

<a id="cls-homescreen-hangar"></a>
### `HomeScreen` — ангарная часть (`src/views/home_screen/HomeScreen.ts`)

ГДД: [#gdd-hangar-view](game-design/hangar-gdd.md#gdd-hangar-view) — `UIHangar`, `UITank`;
[#gdd-battle-replace](game-design/hangar-gdd.md#gdd-battle-replace) — `onHangarUpdate`.

- `onPreload()` (67–79) — `/ingame/home`, `this.data.hangar`.
- `UIFooter()` (411) — блок ангара под именем `hangar` (419).
- **`UIHangar()`** (442–470) — сетка `GRID` из 4 колонок по порядку `data.hangar.tanks`; занятая
  позиция — `UITank(Globals.bag.getTank(uid))` с кнопкой `TankInfoPopup`; пустая — `UITank(null)`.
  Поле `position` не читается — раскладка опирается на порядок массива (см. [#tradeoffs](#tradeoffs) п.4).
- **`UITank(data | null)`** (480–527) — карточка 64×62: цвет ранга, картинка `atlas/tanks/small/<id>/card.png`
  (async-атлас `Tank_<id>`), ранг, рамка, плашка «прототип» при `titleType`, уровень, звёзды,
  мощность. Заглушка пустой позиции — картинка танка 1 с прозрачностью 0.3 и мощность «0».
- **`onHangarUpdate()`** (972–990) — `/ingame/home/hangar` → `data.hangar`; по всем позициям с
  танком в сумке — `battleGround.battle.replaceTank(account.id, position, tank)` (что делает замена в
  бою — [battle-architecture.md](battle-architecture.md), метод `replaceTank`); заменяет блок
  `hangar`. Обновления фона туториала в обработчике больше нет (убрано при merge).
- Подписка/отписка `HANGAR_UPDATE` — 188 / 213.
- Вызовы `TankGetPopup` поездом: `OnTrainSummon` (666, вызов 715), `DevOnTrainCollect` (800, вызов 848, dev); «взять» —
  `OnTrainAccept` (757) с `emit(HANGAR_UPDATE)` (774). Логика поезда —
  [train-architecture.md](train-architecture.md).

<a id="cls-types"></a>
### Типы (`src/views/home_screen/home.d.ts`)

- `HomeScreenJSON.hangar: HangarJSON` (3).
- `HangarJSON { tanks: TankPositionJSON[] }` (25–27).
- `TankPositionJSON { position: number; tankUid: string | null }` (38–41); позиции 0–11 по
  [#gdd-slots](game-design/hangar-gdd.md#gdd-slots).
- Тот же `HangarJSON` приходит в `BattlefieldScreenJSON.hangar` (`battlefield.d.ts:2`).
- `TankJSON` — тип сумки (`popups/bag/bag.d.ts:15`).

<a id="cls-hangar-update"></a>
### `GameEvents.HANGAR_UPDATE` (`src/plain/GameEvents.ts:36`)

Клиентское событие без данных (`EventName<never>`), с сервера не приходит. Слушатель один —
`HomeScreen.onHangarUpdate`. Отправители (каждый вызывает вручную после своего «взять»):

| Где | Строка | После чего |
|---|---|---|
| `HomeScreen.OnTrainAccept` | `HomeScreen.ts:774` | `/ingame/train/accept` |
| `AssemblyPopup.BtnTake` | `AssemblyPopup.ts:280` | `/ingame/assembly/take` |
| `CollectionExperimentalTank.resolvePendingReward` | `CollectionExperimentalTank.ts:253` | `.../takeReward` при `isTake` |

<a id="contract"></a>
### Контракт с сервером

| Маршрут | Где на клиенте | Ответ |
|---|---|---|
| `/ingame/home` | `HomeScreen.onPreload` | `hangar: { tanks: [{ position, tankUid }] }` и другие блоки |
| `/ingame/home/hangar` | `HomeScreen.onHangarUpdate` | `hangar` |
| `/ingame/battlefield` | `BattlefieldPopup` | `hangar` (область Battlefield) |

Сервер (`/workspace/server/game/src/main/java/com/linkedgames/game/`):
- `model/hangar/HangarUserComponent.java` — 12 позиций (`POSITIONS`, 22); `getReplaceableTank`
  (34) — самый слабый танк ряда, `null` если есть свободная ([#gdd-placement](game-design/hangar-gdd.md#gdd-placement)); `addTank` (61) — ставит танк,
  уменьшает счётчик заменённого, шлёт серверное `UserEmitterId.HANGAR_UPDATE` (слушает
  `BattlefieldUserComponent`, клиенту не уходит); `getTanksJSON` (134) — 12 записей по порядку.
- `model/bag/tank/TankType.java:16–21` — `TYPE_POSITION`.
- `pages/ws/ingame/HomePage.java:13` — маршрут `/hangar`.
- `model/user/User.java:328` `createTeam` — состав для боя; `User.java:517` — полный ангар в профиле.

Подробно — серверный документ, `#client-contract`.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Ничего из перечисленного не исправлялось. Номера строк — на состояние кода после merge `origin/amnesia/fix`.

1. **Обновление ангара держится на ручном `emit` у каждого источника (неявный порядок вызовов).**
   После каждого запроса, меняющего состав, вызывающий обязан сам отправить `HANGAR_UPDATE`
   (`HomeScreen.ts:774`, `AssemblyPopup.ts:280`, `CollectionExperimentalTank.ts:253`). Новый источник
   танков, забывший это, оставит главную и идущий бой со старым составом. Сервер уже знает о смене
   (`HangarUserComponent.addTank` шлёт внутреннее `HANGAR_UPDATE`), но клиенту её не передаёт.
   Предложение: push-событие ангара с сервера по схеме
   [server-push-events-subscription.md](server-push-events-subscription.md), тогда отправители не
   нужны. Затрагивает контракт — через `integration-lead`.
2. **`onHangarUpdate` без обработки ошибок** (`HomeScreen.ts:973`): нет `catch` и проверки
   `ResultUtils.isOk`. При ошибке блок ангара и бой молча остаются старыми.
3. **Снято при merge `origin/amnesia/fix`.** Обработчик ангара больше не обновляет фон туториала
   (`updateHomeBackground` убран из `onHangarUpdate`). Номер сохранён, чтобы не ломать ссылки на пункты.
4. **Раскладка по порядку массива, а не по `position`.** `UIHangar` (`HomeScreen.ts:446`) кладёт
   танки в сетку по индексу, `BattlefieldPopup.UITanksBattle` (`BattlefieldPopup.ts:411–418`) ставит
   танк в `pos_<i>` по индексу. Сейчас работает, потому что сервер отдаёт 12 записей строго по
   порядку (`HangarUserComponent.getTanksJSON`, 134–150). При этом `onHangarUpdate` для боя читает
   `position` (`HomeScreen.ts:976`), то есть позицию код определяет двумя разными способами.
5. **Танк в ангаре, которого нет в сумке.** `UIHangar` (`HomeScreen.ts:447–454`) при `uid !== null`
   берёт `Globals.bag.getTank(uid)`, который может вернуть `null` (например, если push сумки пришёл
   позже ответа ангара). Тогда рисуется заглушка, а клик открывает `TankInfoPopup` с `data = null` —
   падение в `TankPresets.TankBigLayout` на `data.country`. То же в `BattlefieldPopup.ts:331–336`.
   Воспроизведение не проверялось.
6. **Три отрисовки одной карточки танка в слоте ангара** (одно правило — одна функция):
   `HomeScreen.UITank` (480–527), `BattlefieldPopup.UITankFrame` (350–392, без плашки «прототип») и
   профиль (`ProfileSection.UITanks`, 202–237: `ItemsPresets.createTankLayout` + своя заглушка). Сетка 4×3 тоже
   продублирована: `HomeScreen.UIHangar` ≈ `BattlefieldPopup.UITanks` (324–348). Предложение — один
   пресет карточки слота и один построитель сетки. Состав карточки задан в
   [#gdd-hangar-view](game-design/hangar-gdd.md#gdd-hangar-view): ему соответствует `HomeScreen.UITank`.
7. **Мёртвый код в `TankGetPopup`.** `replaceableTank ?? receivedTank` (118, 226, 235) — в этих
   ветках `replaceableTank` не `null`, правая часть не срабатывает. Ключ `homeScreen.tankPopup.equip`
   в `ru.json` не используется. `onExit` в конфиг передаёт только сборка, и пустой
   ([assembly-architecture.md](assembly-architecture.md)).
8. **Поля `TankJSON.level`/`stars` необязательны в типе** (`bag.d.ts:20–21`), но
    `HomeScreen.UITank` (509, 514), `BattlefieldPopup.UITankFrame` (373, 378) и `TankPresets`
    читают их без проверки. С `strict: false` компилятор этого не ловит.
9. **Замена танка в идущем бою только на клиенте.** Описано в
    [battle-architecture.md](battle-architecture.md) (Д1 и п.2 известных проблем): сервер считает бой
    по стартовому составу ([#gdd-battle-replace](game-design/hangar-gdd.md#gdd-battle-replace), расхождение отложено).
    Прочность нового танка — текущая прочность заменённого, не выше своего максимума
    (`Fighter.ts:115–117`), как требует ГДД.
10. **Серверные наблюдения (к сведению, анализ сервера не проводился):**
    - `HangarUserComponent.addTank` (`HangarUserComponent.java:70–73`): если в позиции висит `uid`
      танка, которого нет в сумке, новый танк ставится на позицию 0 — в тяжёлый ряд. По
      [#gdd-placement](game-design/hangar-gdd.md#gdd-placement) такой слот должен считаться свободным (без серебра).
      Решение об исправлении принято пользователем 2026-10-17, фикс отложен; клиент правок не требует.
    - Лёгкие и ПТ делят позиции 8–11 и заменяют друг друга — так и задумано
      ([#gdd-placement](game-design/hangar-gdd.md#gdd-placement), решение пользователя 2026-10-17).
11. **Смежное:** `TrainCollectionItemPopup` создаёт флеш с именем `"TankGetPopup"`
    (`TrainCollectionItemPopup.ts:264`) — копипаст; имя флеша сейчас ни на что не влияет. Область поезда.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`game-design/hangar-gdd.md`](game-design/hangar-gdd.md).

| Место в коде | Раздел ГДД |
|---|---|
| позиции 0–11, `HangarJSON`/`TankPositionJSON` | [#gdd-slots](game-design/hangar-gdd.md#gdd-slots) |
| `replaceableTank` в ответах источников (решает сервер) | [#gdd-placement](game-design/hangar-gdd.md#gdd-placement) |
| `TankGetPopup`: `UITankGet`, `UIButtons`, `BtnSwap`, `animatePower` | [#gdd-compare-window](game-design/hangar-gdd.md#gdd-compare-window) |
| `HomeScreen.UIHangar`, `HomeScreen.UITank` | [#gdd-hangar-view](game-design/hangar-gdd.md#gdd-hangar-view) |
| `TankInfoPopup` | [#gdd-tank-info](game-design/hangar-gdd.md#gdd-tank-info) |
| `HomeScreen.onHangarUpdate` → `Battle.replaceTank` | [#gdd-battle-replace](game-design/hangar-gdd.md#gdd-battle-replace) |

Правила источников (цена продажи, очки сборки, закрытие окна по фону, автопризыв) — в ГДД
источников: [train-gdd.md#gdd-decision](game-design/train-gdd.md#gdd-decision),
[assembly-gdd.md#gdd-take](game-design/assembly-gdd.md#gdd-take),
[collections-gdd.md#gdd-exp-reward](game-design/collections-gdd.md#gdd-exp-reward).

Одно правило — одна функция: [#gdd-hangar-view](game-design/hangar-gdd.md#gdd-hangar-view) сейчас выражено тремя
отрисовками карточки и двумя сетками ([#tradeoffs](#tradeoffs) п.6).

<a id="file-map"></a>
## 10. Карта файлов компонента

Полнота проверена `grep` по `TankGetPopup|TankInfoPopup|HangarJSON|TankPositionJSON|HANGAR_UPDATE|/ingame/home/hangar|tankPopup\.`
по `src/` и `ru.json`.

### Файлы прямого влияния

- `src/views/home_screen/popups/tank/TankGetPopup.ts` — окно сравнения и решения по новому танку.
- `src/views/popups/TankInfoPopup.ts` — окно информации о танке.
- `src/views/home_screen/HomeScreen.ts` — блок ангара (`UIHangar`, `UITank`), `onHangarUpdate`,
  подписка на `HANGAR_UPDATE`.
- `src/views/home_screen/home.d.ts` — `HangarJSON`, `TankPositionJSON`, `HomeScreenJSON.hangar`.
- `src/plain/GameEvents.ts` — событие `HANGAR_UPDATE`.

### Файлы косвенного влияния

- `src/presets/TankPresets.ts` — зависимость: карточки и параметры танка; подписи «ТЕКУЩИЙ/НОВЫЙ ТАНК».
- `src/plain/TutorialUtils.ts` — зависимость: `FIRST_TRAIN`/`SECOND_TRAIN`, шаги указателя в `TankGetPopup.processTutorial` ([tutorial-architecture.md](tutorial-architecture.md)).
- `src/utils/TankUtils.ts` — зависимость: формат перезарядки, ассет по id.
- `src/plain/user/UserBag.ts` — зависимость: `getTank(uid)` — данные танка по `tankUid`.
- `src/views/home_screen/popups/bag/bag.d.ts` — зависимость: `TankJSON`, `TankParamsJSON`.
- `src/battle/Battle.ts` — `replaceTank` — постановка танка из ангара в идущий бой.
- `src/battle/Fighter.ts` — `replaceTank(unit)` (90–118): отказ, если танк на позиции уничтожен; новый танк получает прочность заменённого.
- `src/views/home_screen/popups/assembly/AssemblyPopup.ts` — вызывает `TankGetPopup`, шлёт `HANGAR_UPDATE`.
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts`
  — вызывает `TankGetPopup` (`bgClose: false`), шлёт `HANGAR_UPDATE`.
- `src/views/home_screen/popups/battlefield/BattlefieldPopup.ts` — своя копия сетки ангара и позиций в бою.
- `src/views/home_screen/popups/battlefield/battlefield.d.ts` — `BattlefieldScreenJSON.hangar: HangarJSON` (тот же файл ссылается на удалённый при merge `AerodromeJSON` — ошибка tsc от автора fix, не область ангара).
- `src/views/home_screen/popups/profile/ProfileSection.ts` — сетка танков игрока в профиле, `TankInfoPopup`.
- `src/views/home_screen/popups/profile/codex/CodexTanksSection.ts` — открывает `TankInfoPopup`.
- `src/views/battle/ground/BattleGroundTank.ts` — клик по танку в бою открывает `TankInfoPopup`.
- `src/views/home_screen/popups/train/TrainCollectionItemPopup.ts` — зависимость: имя флеша `"TankGetPopup"` (копипаст, [#tradeoffs](#tradeoffs) п.11).
- `assets-src/raw/lang/ru/ru.json` — ключи `homeScreen.tankPopup.*`, `tanks.params.*`.
