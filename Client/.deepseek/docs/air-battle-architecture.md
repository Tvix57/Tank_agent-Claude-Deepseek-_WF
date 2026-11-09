# Бой — самолёты и воздушный бой (клиент)

> **auto-create** — документ составлен по существующему коду (код в рамках задачи не менялся),
> 2026-10-15. Запуском не проверялось.
> Сверено с кодом после merge `origin/amnesia/fix` 2026-10-19.
> Общий движок (тик, очередь событий, ГСЧ, детерминизм, контракт) и наземный бой —
> [`battle-architecture.md`](battle-architecture.md). Аэродром (слоты, выбор самолёта) — отдельная
> область, документ готовит аналитик аэродрома.

ГДД: [`game-design/battle-gdd.md`](game-design/battle-gdd.md) (одна копия на client и server; ТЗ — цель, часть правил не
реализована, см. [#tz-gap](#tz-gap)). Классы, слоты и очерёдность взлёта —
[`game-design/aerodrome-gdd.md`](game-design/aerodrome-gdd.md).

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

У каждого бойца до 8 самолётов на позициях 0–7 (данные — с аэродрома). Самолёты по одному
взлетают, после взлёта остаются в воздухе до конца боя и делают две вещи:

- **пулемётный бой** — стреляют по самолётам противника, урон `gunDamage`;
- **бомбы** — у самолётов с `bombType ≠ 0` по перезарядке бомбы бьют по танкам противника, урон
  `bombDamage`: одиночная (случайный танк), по линии (все живые танки случайной непустой линии из
  трёх), массовая (все живые танки).

На бой самолёты не влияют напрямую: победа определяется только танками
([battle-architecture.md#cls-battle](battle-architecture.md#cls-battle)).

Вид состоит из трёх частей:

- **Полоса неба** на поле наземного боя (`BattleGround`, слой `air`) — иконки появившихся самолётов
  в порядке появления, полоса hp, полоса перезарядки бомбы. Нажатие открывает страницу воздушного
  боя.
- **Страница воздушного боя** (`BattleAir`, флеш) — самолёты обеих сторон на своих позициях,
  пулемётные очереди, урон, уничтожение.
- **Окно авиаудара** (`BattleAirstrike`) — по одному на сторону, и на поле боя, и на странице
  воздушного боя: самолёт с бомбами → падение бомб → танк-цель с взрывом.

<a id="flow"></a>
### Ход воздушной части боя

1. **Взлёт** ([#m-takeoff](#m-takeoff)). Боец выбирает самолёт на взлёт, начиная с позиции 7 и до 0 (слоты 1 → 8),
   ставит его «на полосу» (`AirplanePrepareTakeoffEvent`, таймер 5 с), через 5 с даёт разрешение,
   самолёт взлетает (`AirplaneTakeoffEvent`, 1,5 с), затем появляется в бою (`AirplaneSpawnEvent`,
   1 с). Следующий самолёт выводится на полосу не раньше чем через 1 с после взлёта предыдущего:
   примерно один самолёт в 6 с.
2. **Перезарядка** ([#cls-airplanerecharge](#cls-airplanerecharge)). После появления тикают две
   перезарядки: пулемёт и бомба.
3. **Пулемёт** ([#m-gun](#m-gun)). Заряжен и есть цель — `AirplaneAttackEvent` сейчас и
   `AirplaneTakeDamageEvent` через 1 с. Цели нет — пулемёт ждёт 500 мс и проверяет снова.
4. **Бомба** ([#m-bomb](#m-bomb)). Заряжена — выстрел расходуется, по каждой цели
   `AirplaneAttackEvent` через случайные 0–800 мс и `TankTakeDamageEvent` через 5,5 с после него.
5. **Уничтожение**. hp = 0 — `AirplaneDestroyedEvent(unit, rewarded = боец-бот)`; за самолёт бота
   кампания просит награду (`/battleAirplaneReward`, см. [campaign-architecture.md](campaign-architecture.md)).

<a id="references"></a>
## 2. Референсы

- Серверный двойник: `game/src/main/java/com/linkedgames/game/model/battle/units/UnitAirplane.java`,
  `recharge/AirplaneRecharge.java`, `events/airplane/*` — те же константы и таблицы целей. Правки
  логики — парой с сервером, см. [battle-architecture.md#determinism](battle-architecture.md#determinism).
- Анимации из ТЗ (архив `demo_1/Planes_New_06-*`) в коде не найдены; текущие spine —
  `airplane_bullet`, `airplane_shot`, `airplane_damage`, `air_clouds_up/down`.

<a id="patterns"></a>
## 3. Паттерны

Общие паттерны движка — [battle-architecture.md#patterns](battle-architecture.md#patterns). Своё:

- **Поэтапный автомат с `idle`** — как у танка, но с этапами взлёта (`PREPARE_TAKEOFF` →
  `CLEARANCE_TAKEOFF` → `IN_AIR` → `SPAWNED`).
- **Диспетчер взлёта у бойца** — очередь взлёта ведёт `Fighter`.
- **Запоминание цели** — `targetAirplane` держится, пока цель жива.
- **Подписка страницы на эмиттер вида** — `BattleAir` слушает `ground.eventEmitter`;
  при открытии рисует уже появившиеся самолёты из состояния движка.
- **Окно события с флагом `active`** — новый авиаудар не запускает окно, пока идёт предыдущий.

<a id="class-list"></a>
## 4. Список классов

Движок: `UnitAirplane`, `AirplaneRecharge`, события `AirplanePrepareTakeoffEvent`,
`AirplaneTakeoffEvent`, `AirplaneSpawnEvent`, `AirplaneRechargeEvent`, `AirplaneAttackEvent`,
`AirplaneTakeDamageEvent`, `AirplaneDestroyedEvent`, `AirplaneReplacedEvent`; самолётная часть
`Fighter` (взлёт) и `TankTakeDamageEvent.fromAirplane`.

Вид: `BattleAir`, `BattleAirAirplane`, `AnimationAirplaneShot`, `BattleAirstrike`,
`BattleGroundAirplane` (класс внутри называется `CampaignGroundAirplane`), `AnimationAirstrike`,
самолётная часть `BattleGround`.

Перечисления: `AirplaneBombType`, `AirplaneType`, `AirplaneGunType`, `AirplaneArmorType`.

<a id="anchors"></a>
## 5. Навигация (якоря)

- Ход боя: [#flow](#flow); методы: [#m-takeoff](#m-takeoff), [#m-gun](#m-gun),
  [#m-target-airplane](#m-target-airplane), [#m-bomb](#m-bomb).
- Классы: [#cls-unitairplane](#cls-unitairplane), [#cls-airplanerecharge](#cls-airplanerecharge),
  [#cls-airplane-events](#cls-airplane-events), [#cls-fighter-air](#cls-fighter-air),
  [#cls-battleground-air](#cls-battleground-air), [#cls-battlegroundairplane](#cls-battlegroundairplane),
  [#cls-battleair](#cls-battleair), [#cls-battleairairplane](#cls-battleairairplane),
  [#cls-animationairplaneshot](#cls-animationairplaneshot), [#cls-battleairstrike](#cls-battleairstrike),
  [#cls-animationairstrike](#cls-animationairstrike), [#enums](#enums).
- Сверка с ГДД: [#tz-gap](#tz-gap).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Файл | Раздел |
|---|---|---|
| `UnitAirplane` | `src/battle/units/UnitAirplane.ts` | [#cls-unitairplane](#cls-unitairplane) |
| `AirplaneRecharge` | `src/battle/recharge/AirplaneRecharge.ts` | [#cls-airplanerecharge](#cls-airplanerecharge) |
| события `Airplane*` | `src/battle/events/airplane/*.ts` | [#cls-airplane-events](#cls-airplane-events) |
| `Fighter` (взлёт) | `src/battle/Fighter.ts` | [#cls-fighter-air](#cls-fighter-air) |
| `BattleGround` (небо, авиаудар) | `src/views/battle/ground/BattleGround.ts` | [#cls-battleground-air](#cls-battleground-air) |
| `BattleGroundAirplane` | `src/views/battle/ground/BattleGroundAirplane.ts` | [#cls-battlegroundairplane](#cls-battlegroundairplane) |
| `AnimationAirstrike` | `src/views/battle/ground/animations/AnimationAirstrike.ts` | [#cls-animationairstrike](#cls-animationairstrike) |
| `BattleAir` | `src/views/battle/air/BattleAir.ts` | [#cls-battleair](#cls-battleair) |
| `BattleAirAirplane` | `src/views/battle/air/BattleAirAirplane.ts` | [#cls-battleairairplane](#cls-battleairairplane) |
| `AnimationAirplaneShot` | `src/views/battle/air/animations/AnimationAirplaneShot.ts` | [#cls-animationairplaneshot](#cls-animationairplaneshot) |
| `BattleAirstrike` | `src/views/battle/BattleAirstrike.ts` | [#cls-battleairstrike](#cls-battleairstrike) |
| перечисления | `src/plain/airplane/*.ts` | [#enums](#enums) |

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-unitairplane"></a>
### `UnitAirplane` (`src/battle/units/UnitAirplane.ts`)

Самолёт: позиция 0–7, `AirplaneJSON`, hp, `gunRecharge`, `bombRecharge`, запомненная цель
`targetAirplane`, флаги `SPAWNED`/`ALIVE`/`DESTROYED`/`REPLACED`/`PREPARE_TAKEOFF`/`CLEARANCE_TAKEOFF`/
`IN_AIR`, своё время и `idle`.

Константы: `SPAWN_DURATION = 1000`, `TAKEOFF_DURATION = 1500`, `GUN_ATTACK_DURATION = 1000`,
`BOMB_ATTACK_DURATION = 5500` (мс).

- `init()` — только `ALIVE` (в отличие от танка, ГСЧ не трогает).
- `update(dt)` — у появившегося тикают обе перезарядки; при `idle <= time` — `stateHandling()`.
- `stateHandling()` — по порядку, один шаг за вызов: разрешение на взлёт → `IN_AIR`,
  `AirplaneTakeoffEvent`, `idle = +1500`; на земле — ничего; не появился → `SPAWNED`,
  `AirplaneSpawnEvent`, `idle = +1000`; заменён → `AirplaneReplacedEvent`; уничтожен →
  `AirplaneDestroyedEvent(uid, fighter.isBot())` (танк использует `Battle.isRewardedOpponent`, см. [battle-architecture.md#tradeoffs](battle-architecture.md#tradeoffs) Д6); иначе пулемёт ([#m-gun](#m-gun)) и бомба
  ([#m-bomb](#m-bomb)) в одном вызове.
- `takeDamage(damage)` — hp не ниже 0; при 0 сразу снимает `ALIVE` и ставит `DESTROYED` (у танка
  `DESTROYED` ставится позже).
- `prepareTakeoff()` / `clearanceTakeoff()` — флаги этапов взлёта, их ставит `Fighter`.
- `isCombat()` — флаг `IN_AIR` (взлетел, в т. ч. уже сбитый). Используется `Fighter` (выбор самолёта на взлёт, `Fighter.ts:226`); окно аэродрома, которое раньше показывало «в бою», удалено.
- `markAsReplaced()` — как у танка, но **нигде не вызывается**: замены самолёта в бою нет.
- `setRechargeMode(mode)` / `addRechargeTime(time)` — пустые методы.
- Фабрики: `createFromServer(fighter, UnitAirplaneDataJSON)`, `loadFromServer(fighter,
  UnitAirplaneJSON)`.
- Делегаты: `getFighter`, `getPosition`, `getHp`, `setHp`, `getHpMax` (`params.hp`), `getData`,
  `getParams`, `isAlive`, `isDestroyed`, `isReplaced`, `isAvailable`, `isSpawned`,
  `isPrepareTakeoff`, `markAsSpawned`.

<a id="m-gun"></a>
#### Пулемёт: `attackAirplane()`

ГДД: [#gdd-air-combat](game-design/battle-gdd.md#gdd-air-combat).

Цель — `getTargetAirplane()`. Нет цели — `false`, пулемёт уходит в ожидание 500 мс
(`gunRecharge.idle(500)`), выстрел не тратится. Есть — `AirplaneAttackEvent` сейчас,
`AirplaneTakeDamageEvent` через 1000 мс, перезарядка `doShot()`. Промаха нет, урон всегда
`gunDamage` атакующего ([#cls-airplane-events](#cls-airplane-events)).

<a id="m-target-airplane"></a>
#### Выбор цели пулемёта: `getTargetAirplane()`

ГДД: [#gdd-air-target](game-design/battle-gdd.md#gdd-air-target).

1. Запомненная цель жива — она же («не меняет цель до уничтожения»).
2. Кандидаты — живые и появившиеся самолёты противника.
3. Первый приоритет — позиции из `TARGET_AIRPLANE_PRIORY_TABLE_0[моя позиция]`; есть — случайный из
   них через ГСЧ.
4. Второй приоритет — `TARGET_AIRPLANE_PRIORY_TABLE_1`; есть — случайный из них.
5. Иначе — случайный из всех кандидатов.

Таблицы (позиция атакующего → позиции противника):

| Атакующий | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| приоритет 1 | 6, 7 | 6, 7 | 5 | 4 | 5 | 4 | 7 | 6 |
| приоритет 2 | — | — | 7 | 6 | — | 6 | 5 | 4 |

Позиция в коде `p` — это слот ГДД `8 − p`; в номерах слотов таблицы приведены в [#gdd-air-target](game-design/battle-gdd.md#gdd-air-target).

<a id="m-bomb"></a>
#### Бомба: `attackTank()` / `getTargetTanks()`

ГДД: [#gdd-bomb](game-design/battle-gdd.md#gdd-bomb).

Перезарядка бомбы готова → выстрел расходуется всегда, даже если целей нет. Цели по `bombType`:

- `SOLO` (1) — `opponent.getRandomAliveTank()`.
- `LINE` (2) — линии позиций `[0–3]`, `[4–7]`, `[8–11]`; непустые — где на позициях стоит хоть один
  не заменённый танк (живой или нет); случайная из непустых; в ней — живые танки.
- `MASS` (3) — все живые танки позиций 0–11.

Для каждой цели: `randDelay = getRandomInt(0, 800)`, `AirplaneAttackEvent` в `now + randDelay`,
`TankTakeDamageEvent` в `now + 5500 + randDelay`. Урон — `bombDamage` без модификаторов, у цели
снимается `armorLossDurability`
([battle-architecture.md#cls-tanktakedamage](battle-architecture.md#cls-tanktakedamage)). Урон
приходит, даже если самолёт сбит за эти 5,5 с.

<a id="cls-airplanerecharge"></a>
### `AirplaneRecharge` (`src/battle/recharge/AirplaneRecharge.ts`)

ГДД: [#gdd-airplane-params](game-design/battle-gdd.md#gdd-airplane-params) (перезарядка пулемётов).

Копия `TankRecharge` ([battle-architecture.md#cls-tankrecharge](battle-architecture.md#cls-tankrecharge))
с полем `type` (`TYPE_GUN = "gun"`, `TYPE_BOMB = "bomb"`). Отличия:

- из строки параметра берётся только первое число (время перезарядки); пауза между выстрелами 0,
  выстрелов в серии 1 — даже если в строке `R/B/N`;
- `idle(duration)` — перевести в `PREPARE` на `duration` (ожидание цели пулемётом);
- событие `AirplaneRechargeEvent` несёт `type`.

`R = 0` — оружие выключено. На практике у самолётов без бомб `bombRecharge` выключается так же.

<a id="cls-airplane-events"></a>
### События самолётов (`src/battle/events/airplane/*.ts`)

Все в `execute` находят юнит(ы) по uid и кладут в публичные поля для вида.

- `AirplanePrepareTakeoffEvent(unit, takeoffTime)` — самолёт на полосе, `takeoffTime = 5000`
  (таймер на плашке `HomeScreenMilitaryBase`).
- `AirplaneTakeoffEvent(unit)` — взлёт (анимация на плашке `HomeScreenMilitaryBase`).
- `AirplaneSpawnEvent(unit)` — появление в бою; в серверном бое ставит `SPAWNED`.
- `AirplaneRechargeEvent(unit, type, mode, shots, v0, v1)` — начало перезарядки, `v0` — её время.
- `AirplaneAttackEvent(attacker, target)` — выстрел пулемёта (цель — самолёт) или сброс бомбы (цель
  — танк).
- `AirplaneTakeDamageEvent(attacker, target)` — клиентский бой: `damage = gunDamage` атакующего
  (0 при `INFINITY`), `takeDamage`; фиксирует `hp`, `hpMax`. Серверный: применяет пришедший `damage`.
- `AirplaneDestroyedEvent(unit, rewarded)` — уничтожение; `rewarded` — самолёт бота.
- `AirplaneReplacedEvent(unit)` — замена; в клиентской симуляции не возникает.

<a id="cls-fighter-air"></a>
### `Fighter` — взлёт (`src/battle/Fighter.ts`)

<a id="m-takeoff"></a>
ГДД: [aerodrome-gdd.md#gdd-takeoff-order](game-design/aerodrome-gdd.md#gdd-takeoff-order).
Константы: `AVIATION_TAKEOFF_DELAY = 5000`, `AVIATION_POSITIONS = 8`.

- `update(dt)`, начало — если `aviationTakeoffTime` наступил (или 0), первый в списке самолёт с
  `PREPARE_TAKEOFF` получает `clearanceTakeoff()`.
- `update(dt)`, конец — если `aviationTakeoffTime == 0` или прошло больше 1000 мс после него,
  `getNextAirplaneToTakeoff()`; найден — `prepareTakeoff()`, `aviationTakeoffTime = time + 5000`,
  `AirplanePrepareTakeoffEvent`.
- `getNextAirplaneToTakeoff()` — позиции от 7 к 0, первый не заменённый самолёт, который ещё не на
  полосе и не взлетел.

<a id="cls-battleground-air"></a>
### `BattleGround` — небо и авиаудар (`src/views/battle/ground/BattleGround.ts`)

ГДД: [#gdd-sky-block](game-design/battle-gdd.md#gdd-sky-block), [#gdd-event-window](game-design/battle-gdd.md#gdd-event-window).

- `UIAir()` — полоса неба 400×30 по 8 ячеек на сторону, кликабельна (открывает `BattleAir`) только
  после первого появления самолёта.
- `UIBattlefield()` — окна `BattleAirstrike` `airstrike_top` и `airstrike_bottom`, нажатие открывает
  `BattleAir`.
- `onAirplaneSpawnEvent` — иконка в ячейку `pos_<7 − число уже появившихся на этой стороне>`: в
  порядке появления от края, позиция самолёта не учитывается. Логика совпадает с `createAirplane`.
- `onAirplaneDestroyedEvent` — иконка остаётся, поверх — знак уничтожения.
- `onAirplaneReplacedEvent` — удаляет иконку.
- `onAirplaneRechargeEvent` — полоса перезарядки бомбы.
- `onAirplaneAttackEvent` — только цель-танк и не в фоне: окно авиаудара своей стороны
  (`bottom` — самолёт игрока), если оно не активно, и `AnimationAirstrike` на поле.
- `onAirplaneTakeDamageEvent` — полоса hp иконки.
- `onAirplanePrepareTakeoffEvent`, `onAirplaneTakeoffEvent` — пустые (взлёт рисует плашка военной базы на главной).
- `createAirplane(unit)` — иконка для `onNewOpponentEvent`.

<a id="cls-battlegroundairplane"></a>
### `BattleGroundAirplane` (`src/views/battle/ground/BattleGroundAirplane.ts`)

Иконка самолёта в полосе неба: картинка по `type`, полоса hp (цвет по стороне), полоса перезарядки
бомбы (если `bombType ≠ 0`), знак уничтожения. Класс объявлен как `CampaignGroundAirplane`.

- `updateHpBar(current, max)`, `animationMoveOut()` (опускание за 1 с),
  `animationRecharge(event)` (только `type = "bomb"`), `stateDestroy(visible)`.
- Делегаты: `getUid`, `isTopSide`, `isBottomSide`, `view`.

<a id="cls-animationairstrike"></a>
### `AnimationAirstrike` (`src/views/battle/ground/animations/AnimationAirstrike.ts`)

Бомба над танком-целью на поле: появляется через 4500 мс, падает 1000 мс, в 5500 мс — взрыв, потом
удаляется. Тайминги совпадают с `BOMB_ATTACK_DURATION`, но заданы числами в анимации.

<a id="cls-battleair"></a>
### `BattleAir` (`src/views/battle/air/BattleAir.ts`)

ГДД: [#gdd-air-page](game-design/battle-gdd.md#gdd-air-page), [#gdd-air-positions](game-design/battle-gdd.md#gdd-air-positions).

Страница воздушного боя — `FlashLayout` "BattleAirPopup" с тегом `LOWER_FLASH_TAG`.

- `publish(ground)` — грузит spine-пакеты облаков, пуль, попадания, выстрела
  (`SpineBattleAir*`, `SpineBattleAirplane*`) и публикует флеш.
- `onCreate()` — фон, облака, поля `top`/`bottom` по 8 ячеек `pos_N`, свои окна авиаудара; рисует
  уже появившиеся живые самолёты; подписывается на `ground.eventEmitter`: `BATTLE_AIRPLANE_SPAWN`,
  `_DESTROYED`, `_RECHARGE`, `_ATTACK`, `_TAKE_DAMAGE`, `BATTLE_NEW_OPPONENT`, `BATTLE_ENDED`.
- Расположение ячеек: у каждой стороны ближе к противнику позиции 7 и 6, затем 5, 4, 3, 2, в
  глубине 1 и 0 (смещения `topAirplanesPadding`/`bottomAirplanesPadding`).
- `createAirplane(unit)` — `BattleAirAirplane` в ячейку `pos_<позиция самолёта>`.
- `onAirplaneSpawn` / `onAirplaneDestroyed` (падение, звук, убрать из списка) / `onAirplaneRecharge`
  (пулемёт или бомба) / `onAirplaneTakeDamage` (цифра урона, hp).
- `onAirplaneAttack` — цель-самолёт: `AnimationAirplaneShot`; цель-танк: своё окно авиаудара, если
  не активно.
- `onNewOpponent` — пересоздать самолёты стороны `top`.
- `onBattleEnded` — очистить и закрыть страницу.
- Кнопка «назад» есть, только если у экрана нет хедера (`headerFooterShow = false`).

<a id="cls-battleairairplane"></a>
### `BattleAirAirplane` (`src/views/battle/air/BattleAirAirplane.ts`)

Самолёт на странице воздушного боя: спрайт (вид спереди/сзади по стороне), покачивание, полоса hp,
полоски перезарядки пулемёта и бомбы. Нажатие — `AirplaneInfoPopup`.

- `animationMoveOut()` — появление; `animationTakeDamage(value)` — цифра урона;
  `animationRechargeGun(event)` / `animationRechargeBomb(event)`; `stateDestroy` — покачивание и
  падение; `stateFire`; `updateHpBar`; `visibleHpBar`.
- Делегаты: `getUid`, `getGunType`, `getBattlefieldPosition`, `isTopSide`, `isBottomSide`, `view`.

<a id="cls-animationairplaneshot"></a>
### `AnimationAirplaneShot` (`src/views/battle/air/animations/AnimationAirplaneShot.ts`)

Пулемётная очередь: звук по `gunType` (`airplane_attack_gun_<gunType>.mp3`), вспышки у атакующего,
несколько пуль с разбросом ±20 px (`MathUtils.getRandomInt` — только визуал), попадания; удаление
через 2000 мс.

<a id="cls-battleairstrike"></a>
### `BattleAirstrike` (`src/views/battle/BattleAirstrike.ts`)

ГДД: [#gdd-event-window](game-design/battle-gdd.md#gdd-event-window), [#gdd-bomb](game-design/battle-gdd.md#gdd-bomb).

Окно события «Сброс авиабомбы», 115×75, выезжает с края своей стороны.

- `animate(attacker, target)` — `active = true`; кадр 0 (самолёт: ранг, флаг, имя, сила, hp, бомбы
  уходят вниз) → через 3 с кадр 1 (падение бомб) → через 5 с кадр 2 (танк-цель и взрыв) → через 7 с
  окно уезжает, `active = false`. Число бомб: `SOLO` — 1, `LINE` — 4, `MASS` — 12.
- `stop()` — досрочное закрытие.
- `onTankTakeDamage(event)` — подписка на глобальный `GameEvents.emitter` (переизлучает
  `CampaignBattleGround`); должна показывать урон по цели в окне, но не срабатывает — см.
  [#tradeoffs](#tradeoffs) п.1.
- `animationTakeDamage(value)` — цифра урона или «не пробил».
- `setClickCallback(f)`, `isActive`, `view` — делегаты.

<a id="enums"></a>
### Перечисления (`src/plain/airplane/*.ts`)

- `AirplaneBombType`: `NONE = 0`, `SOLO = 1`, `LINE = 2`, `MASS = 3`.
- `AirplaneType` (класс самолёта): `FIGHTER = 0`, `HEAVY_FIGHTER = 1`, `STORMTROOPER = 2`,
  `BOMBER = 3`, `STRATEGIC_BOMBER = 4`. В бою не используется.
- `AirplaneGunType`: `SMALL_CALIBER = 0`, `LARGE_CALIBER = 1`; `AirplaneArmorType`: `LIGHT = 0`,
  `HEAVY = 1`. В расчёте урона не используются.
- Параметры самолёта — `AirplaneParamsJSON` в `bag.d.ts`: `hp`, `armorType`, `gunDamage`, `gunType`,
  `gunRecharge`, `bombDamage`, `bombType`, `bombRecharge`, `bombDelay` (последний нигде не читается).

<a id="tz-gap"></a>
### Сверка с ГДД (2026-10-17)

Нумерация: слот ТЗ N = позиция в коде `8 − N` (позиция 7 — слот 1, позиция 0 — слот 8; решение
пользователя). С этой поправкой совпадают порядок взлёта (слот 1 → 8), формация на странице и класс
по месту. «Как в коде» приняты выбор цели по таблицам ([#gdd-air-target](game-design/battle-gdd.md#gdd-air-target)),
многократный сброс бомбы по перезарядке без задержки `bombDelay` ([#gdd-bomb](game-design/battle-gdd.md#gdd-bomb)) и
по окну события на каждую сторону ([#gdd-event-window](game-design/battle-gdd.md#gdd-event-window)).

Не совпадает с ГДД: правила ТЗ не реализованы, на сервере то же самое
(`/workspace/server/.claude/docs/battle-architecture.md#airplanes`). Все пункты отложены
пользователем 2026-10-17.

| Правило ГДД | Код (клиент и сервер) |
|---|---|
| [#gdd-armor-guns](game-design/battle-gdd.md#gdd-armor-guns) — ±25% по типу пулемёта и брони | `gunType`/`armorType` в урон не входят, урон = `gunDamage` |
| [#gdd-maneuverability](game-design/battle-gdd.md#gdd-maneuverability) — промах по разнице манёвренности | параметра нет, промаха у пулемёта нет |
| [#gdd-airplane-params](game-design/battle-gdd.md#gdd-airplane-params) — время полёта бомбы и два времени взлёта как параметры | константы: бомба 5500 + 0–800 мс, взлёт 5000 / 1500 / 1000 мс |
| [#gdd-bomb](game-design/battle-gdd.md#gdd-bomb) — линия случайно из линий с живыми танками | случайная из линий, где стоит любой не заменённый танк, в т. ч. только уничтоженные |
| [#gdd-sky-block](game-design/battle-gdd.md#gdd-sky-block) — сбитый самолёт пропадает, после всех блок скрыт | иконка остаётся со знаком уничтожения, блок не скрывается |
| [#gdd-air-page](game-design/battle-gdd.md#gdd-air-page) — все выбранные в бой самолёты | только взлетевшие и живые |

Привязка вида бомбы к классу ([#gdd-bomb](game-design/battle-gdd.md#gdd-bomb)) в коде не проверяется: вид задаёт параметр `bombType`
каждого самолёта в данных баланса.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Детерминизм — общий список в
[battle-architecture.md#tradeoffs](battle-architecture.md#tradeoffs) (Д1–Д6); бонус урона сервера
(Д4) касается и пулемётов, и бомб.

1. **Урон в окне авиаудара не показывается.** `BattleAirstrike.onTankTakeDamage`
   (`BattleAirstrike.ts:253`): `if (event.attacker.is(BattleUnit.AIRPLANE)) return;` — условие
   перевёрнуто. Урон от самолёта отбрасывается, а урон от танка сравнивается с uid самолёта и никогда
   не совпадает. Отложено пользователем 2026-10-17.
2. **Перезарядка бомбы рисуется по режиму пулемёта** (`BattleAirAirplane.ts:121, 127, 129`):
   в блоке бомбы проверяется `gunRecharge.getMode()`. Пока оба режима `AUTO`, не проявляется. Отложено пользователем 2026-10-17.
3. **Угол пули считается от цели к цели** (`AnimationAirplaneShot.ts:65`):
   `getAngle(targetAirplanePos, targetAirplanePos)` — угол всегда один, направление от атакующего не
   учитывается. Отложено пользователем 2026-10-17.
4. **Имя класса не совпадает с файлом**: `BattleGroundAirplane.ts:16` объявляет
   `CampaignGroundAirplane`.
5. **Дубль размещения иконки в небе**: `BattleGround.onAirplaneSpawnEvent` (`BattleGround.ts:412`)
   повторяет `createAirplane` (`BattleGround.ts:612`). Одно правило — две функции; оставить
   `createAirplane`. Отложено пользователем 2026-10-17.
6. **Дубль перезарядки**: `AirplaneRecharge` почти копия `TankRecharge`, с теми же мёртвыми
   `addRechargeTime`/`MANUAL @TODO` (`AirplaneRecharge.ts:83–88, 129`); у `UnitAirplane` пустые
   `setRechargeMode`/`addRechargeTime` (`UnitAirplane.ts:83–89`).
7. **Тайминги бомбы продублированы во вью**: 4500/5500 мс в `AnimationAirstrike.ts:42, 44, 52`
   повторяют `UnitAirplane.BOMB_ATTACK_DURATION`; окно `BattleAirstrike` — свои 3/5/7 с.
8. **Мёртвые сущности**: `UnitAirplane.markAsReplaced`, `AirplaneReplacedEvent` и обработчики
   `onAirplaneReplacedEvent` в клиентской симуляции не срабатывают; `AirplaneType`,
   `AirplaneGunType`, `AirplaneArmorType`, `bombDelay` в бою не используются.
9. **Бомба тратится без целей** (`UnitAirplane.ts:203–206`): перезарядка уходит, даже если
   `getTargetTanks()` пуст. Пулемёт в этом случае ждёт (`gunRecharge.idle(500)`).
10. **`LINE` выбирает линию по любым не заменённым танкам**, включая уничтоженные
    (`UnitAirplane.ts:268–282`): может выпасть линия, где живых нет, и удар уйдёт впустую.
11. **`BattleAir.onDestroy` вызывает `layout.destroy()`** и сам же подписан на
    `Layout.EVENT_DESTROYED` (`BattleAir.ts:37, 83`), а кнопка «назад» и `onBattleEnded` вызывают
    `onDestroy` напрямую (`BattleAir.ts:136, 295`). Повторный вход защищён только поведением
    `Layout.destroy` из `src/ee/`.
12. **`BattleAir.onNewOpponent` не проверяет `isSpawned`** (`BattleAir.ts:280`), в отличие от
    `BattleGround.onNewOpponentEvent` (`BattleGround.ts:524`): ещё не взлетевший самолёт противника
    в серверном бою появится на странице.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`game-design/battle-gdd.md`](game-design/battle-gdd.md). Расхождения — [#tz-gap](#tz-gap).

| Место в коде | Правило ГДД |
|---|---|
| `UnitAirplane` — позиции, `BattleAir.UIBattlefield` — формация | [#gdd-air-positions](game-design/battle-gdd.md#gdd-air-positions) |
| `UnitAirplane.attackAirplane`, `AirplaneTakeDamageEvent` | [#gdd-air-combat](game-design/battle-gdd.md#gdd-air-combat), [#gdd-armor-guns](game-design/battle-gdd.md#gdd-armor-guns), [#gdd-maneuverability](game-design/battle-gdd.md#gdd-maneuverability) |
| `UnitAirplane.getTargetAirplane` | [#gdd-air-target](game-design/battle-gdd.md#gdd-air-target) |
| `UnitAirplane.attackTank`, `getTargetTanks`, `TankTakeDamageEvent.fromAirplane` | [#gdd-bomb](game-design/battle-gdd.md#gdd-bomb) |
| `AirplaneRecharge`, константы `UnitAirplane`, `AirplaneParamsJSON` | [#gdd-airplane-params](game-design/battle-gdd.md#gdd-airplane-params) |
| `BattleAirstrike`, окна в `BattleGround`/`BattleAir` | [#gdd-event-window](game-design/battle-gdd.md#gdd-event-window), [#gdd-bomb](game-design/battle-gdd.md#gdd-bomb) (число бомб) |
| `BattleGround.UIAir`, `onAirplane*Event`, `BattleGroundAirplane` | [#gdd-sky-block](game-design/battle-gdd.md#gdd-sky-block) |
| `BattleAir` | [#gdd-air-page](game-design/battle-gdd.md#gdd-air-page) |
| `Fighter.getNextAirplaneToTakeoff`, `Fighter.update` (взлёт) | [aerodrome-gdd.md#gdd-takeoff-order](game-design/aerodrome-gdd.md#gdd-takeoff-order) |
| `AirplaneDestroyedEvent.rewarded` | [campaign-gdd.md#gdd-kill-reward](game-design/campaign-gdd.md#gdd-kill-reward) |
| состав самолётов противника | [campaign-gdd.md#gdd-enemy-airplanes](game-design/campaign-gdd.md#gdd-enemy-airplanes) |

<a id="file-map"></a>
## 10. Карта файлов компонента

Общие файлы движка — [battle-architecture.md#file-map](battle-architecture.md#file-map).

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `src/battle/units/UnitAirplane.ts` | самолёт: взлёт, пулемёт, бомбы, выбор целей |
| `src/battle/recharge/AirplaneRecharge.ts` | перезарядка пулемёта и бомбы |
| `src/battle/events/airplane/*.ts` | 8 событий самолётов, расчёт урона пулемёта |
| `src/battle/Fighter.ts` | очередь взлёта (общий файл с наземным боем) |
| `src/battle/events/tank/TankTakeDamageEvent.ts` | урон бомбы (`fromAirplane`, общий файл) |
| `src/views/battle/ground/BattleGround.ts` | полоса неба, окна авиаудара на поле (общий файл) |
| `src/views/battle/ground/BattleGroundAirplane.ts` | иконка самолёта в небе |
| `src/views/battle/ground/animations/AnimationAirstrike.ts` | бомба над танком на поле |
| `src/views/battle/air/BattleAir.ts` | страница воздушного боя |
| `src/views/battle/air/BattleAirAirplane.ts` | самолёт на странице воздушного боя |
| `src/views/battle/air/animations/AnimationAirplaneShot.ts` | пулемётная очередь |
| `src/views/battle/BattleAirstrike.ts` | окно события «Сброс авиабомбы» |
| `src/plain/airplane/AirplaneBombType.ts` | вид удара бомбой |
| `src/plain/airplane/AirplaneGunType.ts`, `AirplaneArmorType.ts` | типы пулемёта и брони (в бою не используются) |
| `spine/battle/air_clouds_up`, `air_clouds_down`, `airplane_bullet`, `airplane_damage`, `airplane_shot` (пакеты `SpineBattleAir*`/`SpineBattleAirplane*` в `tools/src/config.yaml`) | spine страницы воздушного боя |
| `atlas/battle_screen/airplanes/*`, `atlas/home_screen/air_bg.png`, `atlas/home_screen/support/*` | иконки неба, фон страницы, рамки окна авиаудара |
| `raw/audio/battle/airplane_*` | звуки пулемёта и уничтожения |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `src/views/home_screen/HomeScreenMilitaryBase.ts` | плашка военной базы на главной (новая область fix, не описывается): таймер по `BATTLE_AIRPLANE_PREPARE_TAKEOFF`, анимация взлёта по `BATTLE_AIRPLANE_TAKEOFF`; подключена в `HomeScreen.ts:470` |
| `src/views/home_screen/HomeScreenAerodrome.ts` | прежняя плашка аэродрома: в `HomeScreen` не подключена, файл остался с теми же подписками (ошибки tsc от ссылок на удалённое — состояние кода после merge) |
| `src/views/home_screen/campaign/CampaignBattleGround.ts` | награда за самолёт (`/battleAirplaneReward`), переизлучение `BATTLE_AIRPLANE_*` в `GameEvents.emitter` |
| `src/plain/GameEvents.ts` | `BATTLE_AIRPLANE_*` (строки 63–70) |
| `src/plain/airplane/AirplaneType.ts` | зависимость: класс самолёта (бой не использует) |
| `src/views/home_screen/popups/bag/bag.d.ts` | зависимость: `AirplaneJSON`, `AirplaneParamsJSON` (зона сумки) |
| `src/views/popups/AirplaneInfoPopup.ts` | открывается нажатием на самолёт на странице воздушного боя |
| `src/utils/AirplaneUtils.ts`, `src/presets/RankPresets.ts` | зависимость: пути ассетов самолёта, ранг, текст в окне авиаудара |
