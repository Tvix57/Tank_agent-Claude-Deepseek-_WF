# Бой — движок симуляции и наземный бой (клиент)

> **auto-create** — документ составлен по существующему коду (код в рамках задачи не менялся),
> 2026-10-15. Запуском не проверялось. Актуализирован 2026-10-19 под merge `amnesia/fix` (владелец боя,
> `Ranking`, запрет замены в PvP, снятие туториальных подмен из движка).
> Самолёты и воздушный бой вынесены в [`air-battle-architecture.md`](air-battle-architecture.md).
> Серверная сторона — `/workspace/server/.claude/docs/battle-architecture.md` (пакет `model.battle`), контекст
> пересимуляции — `/workspace/server/.claude/docs/campaign-architecture.md#battle-flow`.

ГДД: [`game-design/battle-gdd.md`](game-design/battle-gdd.md) (одна копия на client и server). Правила наземного боя
танков ждут отдельного ТЗ; поле боя кампании —
[`campaign-gdd.md#gdd-battlefield`](game-design/campaign-gdd.md#gdd-battlefield).

**Почему два документа.** Движок (`Battle`, `Fighter`, события, перезарядка) общий для танков и
самолётов и почти не меняется, а ТЗ пользователя 2026-10-15 целиком про самолёты: параметры, выбор
цели, бомбы, окно события. Разработчик воздушной части открывает только
[`air-battle-architecture.md`](air-battle-architecture.md), а сюда приходит за общими механизмами
(тик, события, детерминизм, контракт).

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

Бой — автоматическое сражение двух бойцов (`Fighter`): у каждого до 12 танков на позициях 0–11
(3 ряда по 4) и до 8 самолётов на позициях 0–7. Игрок в бой не вмешивается, кроме замены танка в
слоте ангара во время боя. Танки стреляют по перезарядке, самолёты по очереди взлетают с аэродрома,
бьют пулемётами по самолётам противника и бомбами по его танкам. Бой заканчивается, когда у одного из
бойцов не осталось живых танков.

Движок работает в двух режимах:

- **Клиентская симуляция** (`Battle.create`) — кампания на главном экране. Сервер присылает
  стартовые данные и seed (`/ingame/campaign/battle`), клиент сам считает бой и сообщает
  `win` в `/ingame/campaign/battleResult`. При `win = true` сервер повторяет ту же симуляцию на
  Java по тому же seed и засчитывает победу, только если победил игрок и в его эмуляции. Поэтому
  клиентская и серверная симуляции обязаны совпадать до события — см. [#determinism](#determinism).
- **Серверный бой** (`Battle.load` + `addServerEvent`) — экран «Поле боя» (`BattlefieldScreen`,
  PvP). Логику считает сервер, клиент только применяет пришедшие события к состоянию и рисует их.

Вид наземного боя — `BattleGround`: два поля танков (`top` — противник, `bottom` — игрок), полоса
неба с иконками самолётов над полем и два окна авиаудара. Кампанийная обвязка (награды, отправка
результата, скорость, airDrop) живёт в наследнике `CampaignBattleGround` — см.
[`campaign-architecture.md`](campaign-architecture.md). Подмены параметров и вида танков для
туториала в движке и в виде боя больше нет (убраны при merge `amnesia/fix`); `Battle` и
`BattleGround` не зависят от `TutorialUtils` и `Globals.account.tutorial`. Рейтинговые данные бойца
(`Fighter.ranking`, `Ranking`) относятся к новой области «рейтинг кампании» (PvP) и здесь только
упомянуты.

<a id="lifecycle"></a>
### Жизненный цикл боя (клиентская симуляция)

1. `HomeScreen` получает `battle: BattleDataJSON` и вызывает
   `battleGround.battle.create(battleGround, data, Globals.account.id)` (`HomeScreen.ts:1238`); третий
   аргумент — uid владельца боя (`ownerUid`).
2. `create` создаёт `BattleRandom(seed)`, бойцов (`Fighter.createFromServer`), вызывает `init` у
   каждого бойца в порядке массива: `init` находит противника и инициализирует юниты. Каждый танк
   при `init` берёт из генератора случайную задержку появления 0–500 мс.
3. Если у какого-то бойца нет живых танков, ставится `FLAG_WAIT_TANKS`: бой стоит, пока
   `replaceTank` не поставит танк.
4. `HomeScreen` каждый кадр вызывает `battle.update()` (`HomeScreen.ts:179`). Прошедшее реальное
   время (с учётом `timeScale`, не больше 50 мс за кадр) копится и расходуется фиксированными тиками
   по 16 мс.
5. В каждом тике: выполняются события, чьё время наступило (каждое пишется в `log` и уходит в
   `IBattleUI.onBattleEvent`), затем обновляются бойцы (танки, самолёты, перезарядка), затем
   проверяется победитель. Найден единственный живой боец — в очередь ставится `BattleResultEvent`.
6. На следующем тике `BattleResultEvent` вызывает `battle.complete()`; тик завершается флагом
   `FLAG_ENDED`. События, запланированные на будущее, отбрасываются.
7. `CampaignBattleGround.onBattleResultEvent` отправляет `win` и запускает следующий бой.

<a id="references"></a>
## 2. Референсы

- Серверный движок `game/src/main/java/com/linkedgames/game/model/battle/**` — Java-двойник
  клиентского: те же имена классов, константы (`TICK_TIME = 16`, `SPAWN_DURATION`, таблицы целей),
  тот же xorshift-генератор. Клиент — порт серверного движка; любая правка правил
  боя делается парой.
- Отдельного внешнего референса нет.

<a id="patterns"></a>
## 3. Паттерны

- **Фиксированный шаг симуляции** — `Battle.update` переводит переменный кадр в тики по 16 мс через
  аккумулятор. Только так клиент и сервер проходят одинаковую последовательность состояний.
- **Детерминированный ГСЧ с seed** — `BattleRandom` (xorshift32). Все случайные решения логики идут
  через `Battle.getRandomInt`; `Math.random` в логике запрещён (во вью он есть — только для
  разброса пуль).
- **Очередь отложенных событий** — чужое состояние юниты меняют только через
  `BattleEvent` со временем срабатывания (выстрел сейчас, урон через время полёта снаряда). Событие
  одновременно меняет состояние, пишется в лог и уходит в UI.
- **Двойной режим событий** — у событий урона/появления ветка `isServerSide()`: при серверном бое
  событие применяет пришедшие числа, при клиентском — считает их само.
- **Фабрика событий по id** — `BattleEventFactory` строит событие из JSON сервера.
- **Флаги состояния битовой маской** — у `Battle`, `UnitTank`, `UnitAirplane`.
- **UI через интерфейс** — движок знает только `IBattleUI` (`onBattleStart/End/Event`). `BattleGround`
  реализует его и переизлучает события в свой `eventEmitter` (`GameEvents.BATTLE_*`), на который
  подписан, например, `BattleAir`.
- **Общий `TweenSystem` боя** — анимации вида и смежных областей (airDrop, аэродром) идут на
  `battle.tweenSystem`, который обновляется тем же `dt`, что и бой: скорость и пауза боя
  действуют на анимации.
- **Meta-сводка бойцов** — `FighterMeta` (uid/id/rank/level/stars юнитов) строится при старте и
  дополняется при замене танка; вид берёт из неё имена анимаций для отмены.

<a id="class-list"></a>
## 4. Список классов

Движок (`src/battle/`): `Battle`, `Fighter`, `BattleUnit`, `UnitTank`, `TankRecharge`,
`RechargeMode`, `BattleEvent`, `BattleEventFactory`, события танков (`TankSpawnEvent`,
`TankDestroyedEvent`, `TankReplacedEvent`, `TankRechargeEvent`, `TankAttackEvent`,
`TankTakeDamageEvent`), общие события (`BattleResultEvent`, `NewOpponentEvent`, `DodgeEvent`,
`ChangeOpponentEvent`, `BattlePlaceEvent`, `SlotResultEvent`), `BattleRandom`, `BattleBalance`,
`BattleAnalyzer`, `IBattleUI`, `BattleType`.

Вид (`src/views/battle/ground/`): `BattleGround`, `BattleGroundTank`, `AnimationTankShot`.

Типы: `src/types/battle.d.ts`.

Самолётная часть (`UnitAirplane`, `AirplaneRecharge`, события `Airplane*`, `BattleAir`,
`BattleAirAirplane`, `BattleAirstrike`, `BattleGroundAirplane`, анимации) — в
[`air-battle-architecture.md#class-list`](air-battle-architecture.md#class-list).

<a id="anchors"></a>
## 5. Навигация (якоря)

- Жизненный цикл: [#lifecycle](#lifecycle); детерминизм: [#determinism](#determinism);
  контракт: [#client-contract](#client-contract).
- Классы: [#cls-battle](#cls-battle), [#cls-fighter](#cls-fighter), [#cls-unittank](#cls-unittank),
  [#cls-tankrecharge](#cls-tankrecharge), [#cls-events](#cls-events),
  [#cls-tanktakedamage](#cls-tanktakedamage), [#cls-misc](#cls-misc),
  [#cls-battleground](#cls-battleground), [#cls-battlegroundtank](#cls-battlegroundtank),
  [#cls-animationtankshot](#cls-animationtankshot), [#types](#types).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Файл | Раздел |
|---|---|---|
| `Battle` | `src/battle/Battle.ts` | [#cls-battle](#cls-battle) |
| `Fighter` | `src/battle/Fighter.ts` | [#cls-fighter](#cls-fighter) |
| `UnitTank`, `BattleUnit` | `src/battle/units/UnitTank.ts`, `src/battle/BattleUnit.ts` | [#cls-unittank](#cls-unittank) |
| `TankRecharge`, `RechargeMode` | `src/battle/recharge/` | [#cls-tankrecharge](#cls-tankrecharge) |
| `BattleEvent`, `BattleEventFactory`, события | `src/battle/BattleEvent.ts`, `src/battle/events/**` | [#cls-events](#cls-events) |
| `TankTakeDamageEvent`, `BattleBalance` | `src/battle/events/tank/TankTakeDamageEvent.ts`, `src/battle/BattleBalance.ts` | [#cls-tanktakedamage](#cls-tanktakedamage) |
| `BattleRandom`, `BattleAnalyzer`, `IBattleUI`, `BattleType` | `src/battle/` | [#cls-misc](#cls-misc) |
| `BattleGround` | `src/views/battle/ground/BattleGround.ts` | [#cls-battleground](#cls-battleground) |
| `BattleGroundTank` | `src/views/battle/ground/BattleGroundTank.ts` | [#cls-battlegroundtank](#cls-battlegroundtank) |
| `AnimationTankShot` | `src/views/battle/ground/animations/AnimationTankShot.ts` | [#cls-animationtankshot](#cls-animationtankshot) |
| Типы | `src/types/battle.d.ts` | [#types](#types) |

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-battle"></a>
### `Battle` (`src/battle/Battle.ts`)

Корень симуляции: бойцы, очередь событий, лог, время, флаги, seed. Конструктор принимает внешний
`TweenSystem` (поле `tweenSystem`), чтобы движок не зависел от вида.

Флаги: `STARTED`, `PAUSED` (обработчики фокуса закомментированы — сейчас не ставится), `ENDING`,
`ENDED`, `INFINITY` (урон 0; включение закомментировано), `WAIT_TANKS`, `SERVER_SIDE`.

- `create(ui, data: BattleDataJSON, ownerUid: string)` — клиентская симуляция, см. [#lifecycle](#lifecycle). Если бой
  уже шёл — сначала `clear()`.
- `load(ui, data: BattleJSON)` — серверный бой: бойцы через `Fighter.loadFromServer` с готовым
  состоянием (hp, флаги, перезарядка), meta из плоского массива `data.meta` (`loadMeta`), флаг
  `SERVER_SIDE`. Бойцы в этом режиме не обновляются, состояние меняют только события.
- `clear()` — сбрасывает бойцов, события, лог, meta, флаги, `ownerUid`, вызывает `ui.onBattleEnd()`.
  `accumulatedTime`, `timeScale` и генератор не сбрасываются.
- `update()` — кадр: `dt()` (реальное время × `timeScale`, потолок `DT_THRESHOLD = 50`, при
  `PAUSED` — 0) → `tweenSystem.update(dt)` → тики `_update(16)`.
- `_update(dt)` — тик: события с `time <= this.time` по порядку очереди (выполнить, записать
  `apiResponse()` в лог, отдать в UI, удалить); если не `SERVER_SIDE` — `fighter.update(dt)` по
  порядку массива; `ENDING` → `ENDED` и выход; поиск единственного бойца с `isAlive()` →
  `BattleResultEvent(winner)`; `time += dt`. При `WAIT_TANKS` тик пропускается целиком.
  ГДД: [#gdd-battle-end](game-design/battle-gdd.md#gdd-battle-end), [campaign-gdd.md#gdd-levels](game-design/campaign-gdd.md#gdd-levels) (ничья).
- `replaceTank(uid, position, tank)` — замена танка игрока во время боя (вызывает
  `HomeScreen.onHangarUpdate`, `HomeScreen.ts:983`). Если бойца нет — выход; если противник бойца
  не бот (`!opponent.isBot()`, PvP) — выход, замена в таком бою запрещена. Иначе создаёт
  `UnitTank.createFromData`, передаёт `Fighter.replaceTank`, дописывает meta нового танка, снимает
  `WAIT_TANKS`.
- `isRewardedOpponent(fighter)` — `ownerUid !== null && fighter.getUid() !== ownerUid`: «боец —
  не владелец боя». Используется в `UnitTank.stateHandling` для `TankDestroyedEvent.rewarded`.
  `ownerUid` ставится в `create`, сбрасывается в `null` в `clear()`, в `load` не ставится (серверный
  бой «Поля боя» наград не даёт).
  ГДД: [campaign-gdd.md#gdd-battlefield](game-design/campaign-gdd.md#gdd-battlefield) (замена в
  слоте — правило поезда).
- `getRandomInt(min, max)` — единственный вход в ГСЧ для логики: `floor(next() * (max-min+1)) + min`.
- `initOpponent(needy)` — противник по индексу в массиве бойцов: чётный ↔ следующий, нечётный ↔
  предыдущий.
- `getBattleResult()` — `{uid, seed, log, winner}`; используется только `BattleAnalyzer`.
- `faster()` / `slowed()` — `timeScale` 0…3: шаг 1, ниже 1 — шаг 0.1, округление до сотых
  (кнопки скорости в `CampaignBattleGround`).
- `createMeta()` / `createTankMeta(unit)` / `loadMeta(data)` — сборка `FighterMeta`; `starsId =
  stars.rank * 10 + stars.count`.
- Делегаты одной строкой: `getSeed`, `isInfinity`, `isServerSide`, `isEnded`, `getTime`,
  `getTimeScale`, `complete` (ставит `ENDING`), `addFighter` (с заменой по uid), `deleteFighter`,
  `addEvent`, `addServerEvent` (через фабрику), `getFighters`, `getFighter`, `getUnit` (танк или
  самолёт по uid, включая заменённые), `getTanks`, `getAirplanes`, `getAliveAirplanes`,
  `getFighterMeta`, `getFighterMetaByUnitUid`, `getUnitMeta`.
- `onFocus` / `onBlur` / `onVisibilityChange` / `addListeners` / `removeListeners` — подписки
  закомментированы, пауза по фокусу окна не работает.

<a id="cls-fighter"></a>
### `Fighter` (`src/battle/Fighter.ts`)

Сторона боя: uid, имя, признак бота (uid начинается с `00000000` — ObjectId с нулевым timestamp),
танки, самолёты, противник, рейтинг (`Ranking`), собственное время и таймер взлёта.

- `init(battle)` — сохраняет бой, противника (`battle.initOpponent`), вызывает `init` у всех юнитов.
- `replaceTank(unit)` — ставит новый танк на позицию: если на позиции тот же uid — ничего; если
  стоящий танк уничтожен — замена запрещена (ничего не делает); иначе старый `markAsReplaced()`,
  новый добавляется в конец списка, `init()` (берёт случайную задержку появления), hp нового =
  `min(hp старого, hpMax нового)`. Новый танк появляется заново (событие `TankSpawnEvent`), старый
  выдаёт `TankReplacedEvent`.
- `update(dt)` — взлёт самолётов и обновление юнитов, порядок: разрешение на взлёт → `tanks[i].update`
  → `airplanes[i].update` → выбор следующего самолёта на взлёт. Подробно о взлёте —
  [air-battle-architecture.md#m-takeoff](air-battle-architecture.md#m-takeoff).
- `isAlive()` — есть танк без флага `DESTROYED`. Это условие победы в `Battle._update`.
- `getRandomAliveTank()` — случайный живой танк противника (через ГСЧ боя).
- `getPower()` — сумма `getData().power` всех танков и самолётов бойца (клиентский расчёт, на
  детерминизм не влияет).
- `getRanking()` — `Ranking` (`src/battle/ranking/Ranking.ts`): `leagueId` (−1 — нет рейтинга),
  `rating`, `place`; `set`/`reset`/геттеры. Заполняется из необязательного `data.ranking` в
  `createFromServer` и `loadFromServer`. Потребитель — `CampaignBattleGround` (профиль соперника,
  область рейтинга/PvP кампании, здесь не описывается).
- `createFromServer(data)` — новый боец из `FighterDataJSON`: танки и самолёты из данных сервера
  как есть, затем `ranking`.
- `loadFromServer(data)` — боец с готовым состоянием для серверного боя, затем `ranking`.
- Делегаты: `getUid`, `getName`, `isBot`, `getBattle`, `getOpponent`, `addUnit`, `getTank`,
  `getTankByPosition` (только не заменённые), `getTanks`, `getAliveTanks`, `getAliveTanksCount`,
  `getAirplane`, `getAirplaneByPosition`, `getAirplanes`, `getAliveAirplanes` (живые и появившиеся).

<a id="cls-unittank"></a>
### `UnitTank` (`src/battle/units/UnitTank.ts`), `BattleUnit` (`src/battle/BattleUnit.ts`)

`BattleUnit` — база юнита: uid, тип (`TANK = 1`, `AIRPLANE = 2`), `is(type)`.

`UnitTank` — танк: позиция 0–11, данные `TankJSON`, hp, прочность брони, `recharge: TankRecharge`,
флаги `SPAWNED`/`ALIVE`/`DESTROYED`/`REPLACED`, своё время и `idle` (до какого момента танк занят).

- `init()` — `ALIVE`, `idle += getRandomInt(0, 500)`: танки появляются не одновременно.
- `update(dt)` — у появившегося танка тикает перезарядка; когда `idle <= time` — `stateHandling()`.
- `stateHandling()` — конечный автомат, один шаг за вызов: появление (`TankSpawnEvent`,
  `idle = time + 1000`) → заменён (`TankReplacedEvent`, `idle = ∞`) → уничтожен (флаг `DESTROYED`,
  `TankDestroyedEvent(uid, rewarded = battle.isRewardedOpponent(fighter))`, `idle = ∞`) → выстрел, если
  `recharge.canShot()`.
- `attackTank()` — цель по `getTarget()`; промах с шансом 5% (`getRandomInt(1, 100) <= 5`);
  `TankAttackEvent` сейчас и `TankTakeDamageEvent` через 500 мс, если не промах.
  ГДД: наземный бой ждёт отдельного ТЗ.
- `getTarget()` — `TARGET_PRIORY_TABLE`: для каждой позиции три приоритетные позиции противника
  (та же колонка во всех трёх рядах, зеркально: 0→3,7,11; 1→2,6,10; 2→1,5,9; 3→0,4,8; ряды 2 и 3
  повторяют ряд 1). Первая живая; иначе случайный живой танк противника.
- `takeDamage(damage)` — hp не ниже 0; при 0 снимает `ALIVE`. `DESTROYED` ставится позже, в
  `stateHandling`, когда у танка кончится `idle`.
- `markAsReplaced()` — снимает `ALIVE`, ставит `DESTROYED` и `REPLACED`: заменённый танк остаётся в
  списке невидимым.
- Фабрики: `createFromServer(fighter, UnitTankDataJSON)`, `createFromData(fighter, position, TankJSON)`
  (замена в бою), `loadFromServer(fighter, UnitTankJSON)` (с состоянием).
- Делегаты: `getFighter`, `getPosition`, `getHp`, `setHp`, `getHpMax` (`params.hp`),
  `getArmorDurability`, `addArmorDurability`, `getData`, `getParams`, `isAlive`, `isSpawned`,
  `isDestroyed`, `isReplaced`, `isAvailable` (= не заменён), `markAsSpawned`.

<a id="cls-tankrecharge"></a>
### `TankRecharge` (`src/battle/recharge/TankRecharge.ts`), `RechargeMode`

Перезарядка орудия танка. Параметр `params.recharge` — строка `"R"` или `"R/B/N"`: время
перезарядки, пауза между выстрелами серии, число выстрелов в серии (по умолчанию `R/0/1`). `R = 0` —
оружие выключено (`STATE_DISABLE`).

Состояния: `IDLE` → (`shots > 0`) `PREPARE` (пауза между выстрелами) → `CAN_SHOT`; (`shots = 0`)
`RECHARGE` → `CAN_SHOT` с `shots = N`. При входе в `RECHARGE` в режиме `AUTO` ставится
`rechargeTime = time + R + 300` (300 мс — пауза для показа «заряжено») и событие `TankRechargeEvent`
(`v0 = R`).

- `canShot()` / `doShot()` — проверка и расход выстрела (переход в `IDLE`).
- `getLeftRechargeTime()` — остаток для полосы перезарядки во вью (без учёта 300 мс).
- `setData(json)` — состояние из сервера (серверный бой).
- `getMode` / `setMode` / `getBaseRechargeTime` — делегаты.
- `addRechargeTime(time)` — копит `addedRechargeTime`, который нигде не читается.

`RechargeMode`: `AUTO = 0`, `MANUAL = 1` (ветка `@TODO`), `INSTANT = 2` (в движке не обрабатывается,
вью прячет полосу).

<a id="cls-events"></a>
### `BattleEvent`, `BattleEventFactory`, события (`src/battle/BattleEvent.ts`, `src/battle/events/**`)

`BattleEvent` — id, время срабатывания (`setTime`, по умолчанию 0 — «в ближайший тик»), флаг
`completed`, `execute(battle)`, `apiResponse()` (JSON для лога; время в JSON не пишется).

Id: 1–6 танковые, 7–14 самолётные, 15 `DODGE`, 16 `CHANGE_OPPONENT`, 17 `NEW_OPPONENT`, 18
`BATTLE_PLACE`, 19 `BATTLE_RESULT`, 20 `SLOT_RESULT`.

`BattleEventFactory` — статическая карта `id → buildFromServer`, заполняется при импорте модуля.

Танковые события (кроме урона — [#cls-tanktakedamage](#cls-tanktakedamage)): в `execute` находят
юнит(ы) по uid и кладут в публичные поля для вида.

- `TankSpawnEvent` — в серверном бое ставит юниту `SPAWNED`.
- `TankDestroyedEvent(unit, rewarded)` — `rewarded = true`, если уничтожен танк бойца, не являющегося владельцем боя (по нему
  кампания просит награду).
- `TankReplacedEvent`, `TankRechargeEvent(unit, mode, shots, v0, v1)`, `TankAttackEvent(attacker,
  target, isMiss)` — только данные для вида.

Общие события:

- `BattleResultEvent(winner)` — в клиентском бое вызывает `battle.complete()`.
- `NewOpponentEvent(initiator, opponent)` — только серверный бой: удаляет всех бойцов, кроме
  инициатора, и добавляет нового из `FighterJSON`.
- `DodgeEvent`, `ChangeOpponentEvent`, `BattlePlaceEvent`, `SlotResultEvent` — события «Поля боя»,
  движок только переносит данные; обработка — в `BattlefieldBattleGround`/`BattlefieldScreen`.

<a id="cls-tanktakedamage"></a>
### `TankTakeDamageEvent` (`src/battle/events/tank/TankTakeDamageEvent.ts`), `BattleBalance`

Урон по танку — единственное место расчёта урона танкам (и от танка, и от бомбы самолёта).

- `execute(battle)` — серверный бой: применяет пришедший `damage` и снимает `armorLossDurability`.
  Клиентский: `fromTank` или `fromAirplane` по типу атакующего, затем фиксирует `hp`, `hpMax`,
  `armorDurability` для лога и вида.
- `fromTank` — `damage = params.damage × BattleBalance.getTankAmmoDamageModifier(ammoType, armorType
  цели)`; при отрицательной прочности брони цели урон растёт на `|прочность|`%; `Math.floor`. Если
  `penetration` атакующего не больше `armor` цели — блок с шансом `прочность`%
  (`getRandomInt(1, 100) <= armorDurability`) → урон 0. Затем `takeDamage` и снятие
  `armorLossDurability` (даже при блоке и промахе по уже мёртвой цели).
- `fromAirplane` — `damage = params.bombDamage` атакующего самолёта без модификаторов, снятие
  прочности брони такое же. Подробно о бомбах —
  [air-battle-architecture.md#m-bomb](air-battle-architecture.md#m-bomb).
- `BattleBalance.getTankAmmoDamageModifier(ammo, armor)` — таблица 3×3: бронебойный AP — лёгкая
  0.75 / композитная 1.25 / тяжёлая 1; фугасный HE — 1.25 / 1 / 0.75; кумулятивный HEAT — 1 / 0.75 /
  1.25; иначе 1.

ГДД: урон танков ждёт отдельного ТЗ; урон бомбы — [#gdd-bomb](game-design/battle-gdd.md#gdd-bomb).

<a id="cls-misc"></a>
### `BattleRandom`, `BattleAnalyzer`, `IBattleUI`, `BattleType`

- `BattleRandom` — xorshift32 (`<<13`, `>>>17`, `<<5`), `next()` ∈ [0, 1). Совпадает с
  серверным `BattleRandom.java` бит в бит.
- `BattleAnalyzer.check(client, server)` — dev-сверка: сравнивает длину логов и первую несовпавшую
  запись (± 10 соседних) через `Logger.error`. Вызывается в `CampaignBattleGround`, только если
  сервер прислал `battleResult` (dev-режим сервера).
- `IBattleUI` — `onBattleStart`, `onBattleEnd`, `onBattleEvent(event)`.
- `BattleType` — `DEFAULT = 0`, `BATTLEFIELD = 1`; на клиенте не используется.

<a id="cls-battleground"></a>
### `BattleGround` (`src/views/battle/ground/BattleGround.ts`)

Вид боя и реализация `IBattleUI`. Создаёт собственные `TweenSystem`, `Battle` и `EventEmitter`.
Наследники: `CampaignBattleGround` (главный экран), `BattlefieldBattleGround` («Поле боя»).

Структура `layout`: `battlefield` (поля `top`/`bottom` по 12 ячеек `pos_N` с фиксированными
координатами, окна `airstrike_top`/`airstrike_bottom`), `air` (полоса неба, 8 ячеек на сторону),
`animations`, `curtain`, `result`.

- `onBattleEvent(event)` — диспетчер по id: вызывает `on*Event` и эмитит `GameEvents.BATTLE_*` в
  `this.eventEmitter`. Для `BATTLE_RESULT` эмитит `BATTLE_ENDED`.
- `onTankSpawnEvent` — `createTank` + выезд. `onTankDestroyedEvent` — прячет полосу hp, остов,
  звук. `onTankReplacedEvent` — удаляет вид танка. `onTankRechargeEvent` — полоса перезарядки.
- `onTankAttackEvent` — в фоновом режиме пропускается; иначе анимация пуль у атакующего и
  `AnimationTankShot` в слое `animations` с именем `target_<uid бойца> attacker_<uid бойца>`
  (по имени `clearAnimationsByName` отменяет анимации при смене противника).
- `onTankTakeDamageEvent` — цифра урона (не в фоне), полоса hp и прочности.
- Самолётные обработчики (`onAirplane*Event`) и полоса неба —
  [air-battle-architecture.md#cls-battleground-air](air-battle-architecture.md#cls-battleground-air).
- `onNewOpponentEvent` — пересоздаёт вид всех танков и самолётов стороны `top` по новому бойцу.
- `onBattleResultEvent` — очищает списки видов (сами виды не уничтожает — это делает наследник,
  заменяя слои).
- `setBackgroundMode(value)` — счётчик фонового режима: пока открыт любой флеш
  (`FlashOverlay.EVENT_ON_FLASH_ACTIVATED`), выстрелы и цифры урона не рисуются. Бой идёт.
- `createTank(unit)` — вид танка на `battlefield.<side>.pos_<позиция>`; сторона `bottom`, если uid
  бойца равен `Globals.account.id`.
- Делегаты: `getAnimationsLayout`, `clearAnimationsByName`, `getTopAirstrike`,
  `getBottomAirstrike`, `getTimeScale` (всегда 1, переопределяет наследник), `setAirInteractive`,
  `isBackgroundMode`, `getTank`, `getAirplane`, `view`. `onDodgeEvent`, `onChangeOpponentEvent`,
  `onBattlePlaceEvent` — пустые хуки для наследника.

<a id="cls-battlegroundtank"></a>
### `BattleGroundTank` (`src/views/battle/ground/BattleGroundTank.ts`)

Вид танка (конфиг `BattleGroundTankConfig {topSide}`): модель, полоса hp (длина 30, смещение по y ±25), полоса перезарядки, счётчик выстрелов,
spine-эффекты (выхлоп, дым, огонь, взрыв).

- `UIMain()` — сборка; полоса перезарядки стартует с остатка `recharge.getLeftRechargeTime()`.
- `animationMoveOut(instant?)` — выезд на позицию (1000 мс) и звук появления.
- `animationTakeDamage(value)` — всплывающая цифра урона (0 — «не пробил»), звук.
- `animationRecharge(event)` — полоса перезарядки по `event.value0`.
- `animationBullets()`, `animationManualRecharge(value)`, `updateHpBar`, `updateArmorDurability`,
  `updateBullets`, `visibleHpBar`, `stateExhaust/Smoke/Fire/Destroy` — визуальные состояния.
- Делегаты: `getConfig`, `getBattlefieldPosition`, `getUid`, `getAmmoType`, `getArmorType`,
  `isTopSide`, `isBottomSide`, `view`.

<a id="cls-animationtankshot"></a>
### `AnimationTankShot` (`src/views/battle/ground/animations/AnimationTankShot.ts`)

Анимация выстрела танка по `TankAttackEvent`: звук по типу танка, вспышка, полёт снаряда 500 мс
(совпадает с `UnitTank.ATTACK_DURATION`), попадание. Тип эффекта попадания выбирается по значению
`BattleBalance.getTankAmmoDamageModifier` (1.25 / 1 / 0.75), то есть вью повторно считает
модификатор урона.

<a id="types"></a>
### Типы (`src/types/battle.d.ts`)

- Стартовые данные клиентского боя: `BattleDataJSON {uid, seed, fighters}`, `FighterDataJSON`,
  `UnitTankDataJSON {position, tank}`, `UnitAirplaneDataJSON {position, airplane}`.
- Бойцы получили необязательное поле `ranking {leagueId, rating, place}` (`FighterDataJSON`, `FighterJSON`); `RankedResultJSON {rating, place: {before, after, delta}}` — результат рейтингового боя (потребители — `HomeScreen.UIBattleResult`, `CampaignBattleEndedData`; не область боя).
- Серверный бой с состоянием: `BattleJSON {uid, seed, survivors, fighters, meta}`, `FighterJSON`,
  `UnitTankJSON`, `UnitAirplaneJSON`, `TankRechargeJSON`, `AirplaneRechargeJSON`.
- Лог: `BattleResultJSON {uid, seed, log, winner}`, `BattleEventJSON {id}` и наследники по каждому
  событию.
- Meta: `FighterMeta`, `UnitMeta`, `UnitTankMeta`, `UnitAirplaneMeta`.
- `TankJSON`/`TankParamsJSON`/`AirplaneJSON`/`AirplaneParamsJSON` — в
  `src/views/home_screen/popups/bag/bag.d.ts` (зона сумки).

<a id="client-contract"></a>
### Контракт с сервером

| Направление | Где | Что |
|---|---|---|
| сервер → клиент | `/ingame/campaign/battle` → `HomeScreen` | `battle: BattleDataJSON` (uid, seed, бойцы со стартовым составом) |
| клиент → сервер | `/ingame/campaign/battleResult` | только `win`; лог и seed не отправляются |
| сервер → клиент | ответ `/battleResult` | `battleResult?: BattleResultJSON` — лог серверной эмуляции, только при `app.devTools`; клиент сверяет его `BattleAnalyzer` |
| сервер → клиент | «Поле боя»: `BattleJSON` + поток `BattleEventJSON` | серверный бой, `Battle.load` + `addServerEvent` |

Подробно о роутах кампании — [campaign-architecture.md#client-contract](campaign-architecture.md#client-contract).

<a id="determinism"></a>
### Детерминизм клиентской и серверной симуляции

Сервер засчитывает заявленную клиентом победу, только если его эмуляция по тому же `BattleData` и
seed тоже дала победу игрока. Совпадение держится на одинаковых: шаге тика (16 мс), порядке бойцов
и юнитов в массивах, порядке событий в очереди, порядке и числе обращений к ГСЧ, константах и
формулах. Сверено с сервером точечно и с `/workspace/server/.claude/docs/battle-architecture.md#client-divergence`:

- совпадает: `BattleRandom` (бит в бит), формула `getRandomInt`, `TICK_TIME`, длительности
  появления/атаки/взлёта/бомбы, шанс промаха 5%, случайная задержка появления 0–500, задержка бомбы
  0–800, `+300` к перезарядке, таблица целей танков, порядок взлёта 7→0, порядок шагов тика
  (события → бойцы → `ENDING` → поиск победителя), конец боя по флагу танка `DESTROYED`.

Места, где симуляции расходятся или могут разойтись, — в [#tradeoffs](#tradeoffs), пункты Д1–Д6.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Детерминизм (клиент ↔ сервер):

- **Д1. Замена танка во время боя есть только на клиенте.** `HomeScreen.onHangarUpdate` вызывает
  `battle.replaceTank` (`HomeScreen.ts:983`, `Battle.ts:297`); в серверном движке `replaceTank`
  нет, эмуляция идёт по стартовому составу. Кроме того, `Fighter.replaceTank` → `UnitTank.init`
  (`UnitTank.ts:39`) берёт число из ГСЧ в момент замены, и вся дальнейшая последовательность
  случайных чисел сдвигается. После любой замены в бою клиентский и серверный бои разные: игрок может
  видеть победу, которую сервер не засчитает (и наоборот — клиент не отправит `win: true`). Стык
  клиент↔сервер, нужен `integration-lead`.
- **Д2. Ничья.** Клиент ищет единственного живого бойца (`Battle.ts:416–431`); если последние танки
  обеих сторон уничтожены в одном тике, победителя нет, `BattleResultEvent` не ставится, бой не
  заканчивается. Сервер в этом случае объявляет победителем первого бойца в списке, то есть игрока
  (`/workspace/server/.claude/docs/battle-architecture.md#ending`), что совпадает с ГДД кампании: ничья —
  победа игрока ([campaign-gdd.md#gdd-levels](game-design/campaign-gdd.md#gdd-levels)). Расходится
  клиент.
- **Д3. Точность урона.** Клиент считает в double (`TankTakeDamageEvent.ts:56–61`), сервер — в float
  (`TankTakeDamageEvent.java:71–78`). При отрицательной прочности брони множитель
  `1 + |прочность|/100` в float и double округляется по-разному; на границе целого `Math.floor` даст
  разный урон. Сервер проверил перебором: 196 комбинаций расходятся, например урон 20, AP по
  композитной, прочность −16 — сервер 29, клиент 28.
- **Д4. Бонус урона.** Сервер добавляет `damage * battle.getDamageBoost() / 100` (в т. ч. для бомб и
  пулемётов), на клиенте этого нет. По серверному документу в базовом бою бонус равен 0 и растёт только
  в Battlefield, поэтому на кампанию не влияет, пока это так.
- **Д5. Туториальные параметры — снято.** Подмена параметров танков в туториале убрана из
  `Fighter.createFromServer` и `Battle.replaceTank` (merge `amnesia/fix`). Номер не переиспользуется.
- **Д6. Признак `rewarded` в событии уничтожения.** Клиентский танк считает его как
  `battle.isRewardedOpponent(fighter)` (боец не владелец боя, `UnitTank.ts:149`), сервер — как
  `fighter.isBot()` (`UnitTank.java:176`). В бою с ботом значения совпадают; в бою против игрока
  (`!opponent.isBot()`) клиент пишет `rewarded = true` для танков противника, сервер — `false`.
  Самолёт на клиенте по-прежнему `fighter.isBot()` (`UnitAirplane.ts:189`), то есть правило
  «кто награждается» выражено двумя способами. На исход боя не влияет (поле только в логе и для
  кампании), но `BattleAnalyzer` увидит расхождение логов. Стык клиент↔сервер.

Логика и код:

1. **`Battle.replaceTank` при отказе замены** (`Battle.ts:297–320`): если `Fighter.replaceTank`
   ничего не сделал (на позиции уничтоженный танк или тот же uid), meta нового танка всё равно
   дописывается и `WAIT_TANKS` снимается.
2. **Две проверки «награждаемого»** (`UnitTank.ts:149` — `isRewardedOpponent`, `UnitAirplane.ts:189`
   — `isBot`): одно правило ГДД ([campaign-gdd.md#gdd-kill-reward](game-design/campaign-gdd.md#gdd-kill-reward)),
   два выражения. Решение — вопрос пользователю (см. Д6).
3. **Запрет замены в PvP зашит в движке** (`Battle.replaceTank`, `!opponent.isBot()`) без записи в
   ГДД ангара ([hangar-gdd.md#gdd-battle-replace](game-design/hangar-gdd.md#gdd-battle-replace)).
4. **Мёртвый код перезарядки**: `addRechargeTime`/`addedRechargeTime` нигде не применяются
   (`TankRecharge.ts:84–89`); режим `MANUAL` — `@TODO` (`TankRecharge.ts:124`); `INSTANT` движок не
   обрабатывает. `BattleType` на клиенте не используется. Пауза по потере фокуса закомментирована
   (`Battle.ts:534–545`). Кандидаты на удаление или доработку.
5. **Урон по заменённому/мёртвому танку**: `TankTakeDamageEvent` применяет урон и снимает прочность
   брони у цели без проверки, что она жива и не заменена. Если цель заменили за время полёта
   снаряда, урон уходит невидимому заменённому танку.
6. **`AnimationTankShot` повторно считает модификатор урона** через `BattleBalance` и сравнивает
   float-значения (`case 1.25`). Тип эффекта лучше брать из события.
7. **`clear()` не сбрасывает `accumulatedTime`/`timeScale`**: остаток времени и скорость прошлого
   боя переходят в следующий (на детерминизм не влияет — тики фиксированные).
8. **`BattleGround.onBattleResultEvent` очищает списки, не уничтожая виды** — полагается на то, что
   наследник заменит слои.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`game-design/battle-gdd.md`](game-design/battle-gdd.md). Самолётная часть —
[air-battle-architecture.md#gdd-link](air-battle-architecture.md#gdd-link).

| Место в коде | Правило ГДД |
|---|---|
| `Battle._update` — поиск победителя, `Fighter.isAlive` | [#gdd-battle-end](game-design/battle-gdd.md#gdd-battle-end); ничья — [campaign-gdd.md#gdd-levels](game-design/campaign-gdd.md#gdd-levels), поражение — [campaign-gdd.md#gdd-defeat](game-design/campaign-gdd.md#gdd-defeat) |
| позиции 0–11, 3 ряда по 4, `createTank` | [campaign-gdd.md#gdd-battlefield](game-design/campaign-gdd.md#gdd-battlefield) |
| `Battle.replaceTank`, `Fighter.replaceTank` | [campaign-gdd.md#gdd-battlefield](game-design/campaign-gdd.md#gdd-battlefield) (замена в слоте), [campaign-gdd.md#gdd-train-dependency](game-design/campaign-gdd.md#gdd-train-dependency) |
| `TankDestroyedEvent.rewarded`, `Battle.isRewardedOpponent` | [campaign-gdd.md#gdd-kill-reward](game-design/campaign-gdd.md#gdd-kill-reward) |

Правила наземного боя (промах 5%, таблица целей танков, урон и блок брони, перезарядка, перенос hp
при замене) пока есть только в коде. По решению пользователя они ждут отдельного ТЗ и в ГДД не
вносятся.

<a id="file-map"></a>
## 10. Карта файлов компонента

Самолётные файлы — [air-battle-architecture.md#file-map](air-battle-architecture.md#file-map).

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `src/battle/Battle.ts` | корень симуляции: тик, очередь событий, лог, ГСЧ, замена танка, владелец боя |
| `src/battle/Fighter.ts` | сторона боя: юниты, противник, взлёт самолётов, условие «жив», сила, рейтинг |
| `src/battle/ranking/Ranking.ts` | лига, рейтинг, место бойца (новая область рейтинга/PvP кампании; здесь только данные бойца) |
| `src/battle/BattleUnit.ts` | база юнита |
| `src/battle/units/UnitTank.ts` | танк: автомат состояний, выстрел, выбор цели |
| `src/battle/recharge/TankRecharge.ts` | перезарядка танка |
| `src/battle/recharge/RechargeMode.ts` | режимы перезарядки |
| `src/battle/BattleEvent.ts` | база события, id событий |
| `src/battle/events/BattleEventFactory.ts` | событие из JSON сервера |
| `src/battle/events/tank/*.ts` | 6 событий танков, в т. ч. расчёт урона |
| `src/battle/events/BattleResultEvent.ts`, `NewOpponentEvent.ts`, `DodgeEvent.ts`, `ChangeOpponentEvent.ts`, `BattlePlaceEvent.ts`, `SlotResultEvent.ts` | общие события |
| `src/battle/BattleRandom.ts` | xorshift-ГСЧ по seed |
| `src/battle/BattleBalance.ts` | модификатор урона снаряд × броня |
| `src/battle/BattleAnalyzer.ts` | dev-сверка логов клиента и сервера |
| `src/battle/IBattleUI.ts` | интерфейс вида |
| `src/battle/BattleType.ts` | тип боя (не используется) |
| `src/views/battle/ground/BattleGround.ts` | вид боя, `IBattleUI`, диспетчер событий |
| `src/views/battle/ground/BattleGroundTank.ts` | вид танка |
| `src/views/battle/ground/animations/AnimationTankShot.ts` | анимация выстрела танка |
| `src/types/battle.d.ts` | типы данных боя, лога, meta |
| `assets-src/atlas/battle_screen/` (пакет `BattleScreen`), `spine/battle/tank_*` (пакеты `SpineBattleTank*`) в `tools/src/config.yaml` | ассеты боя |
| `raw/audio/battle/*` | звуки боя |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `src/views/home_screen/HomeScreen.ts` | создаёт бой (`create`), крутит `battle.update()`, замена танка из ангара (`replaceTank`) |
| `src/views/home_screen/campaign/CampaignBattleGround.ts` | наследник `BattleGround` для кампании: награды, `/battleResult`, `BattleAnalyzer`, скорость, переизлучение `BATTLE_*` в `GameEvents.emitter`; показ рейтинга и силы соперника (`Fighter.getRanking/getPower`) — см. [campaign-architecture.md](campaign-architecture.md) |
| `src/views/battlefield_screen/BattlefieldBattleGround.ts`, `BattlefieldScreen.ts` | серверный бой «Поле боя»: `load`, `addServerEvent`, обработка `Dodge`/`ChangeOpponent`/`NewOpponent`/`SlotResult`/`BattlePlace` |
| `src/views/battlefield_screen/BattlefieldSlot.ts`, `BattlefieldSlotLine.ts`, `BattlefieldUnitFrame.ts`, `BattlefieldUnitFrameData.ts` | «Поле боя»: используют юниты и события боя |
| `src/views/ObjectCreator.ts` | регистрация `BattlefieldScreen` |
| `src/views/home_screen/campaign/AirDrop.ts` | анимации airDrop на `battle.tweenSystem` — см. [airdrop-architecture.md](airdrop-architecture.md) |
| `src/plain/GameEvents.ts` | события `BATTLE_*` (строки 52–76) |
| `src/plain/Globals.ts` | зависимость: `account.id` (сторона, `ownerUid` при `create`) |
| `src/plain/tank/TankAmmoType.ts`, `TankArmorType.ts` | зависимость: типы снаряда и брони |
| `src/views/home_screen/popups/bag/bag.d.ts` | зависимость: `TankJSON`, `TankParamsJSON` (зона сумки) |
| `src/plain/Logger.ts` | зависимость: вывод `BattleAnalyzer` |
