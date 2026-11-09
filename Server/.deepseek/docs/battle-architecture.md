# Бой — серверный движок боя танков и самолётов (сервер)

ГДД: [battle-gdd.md](/workspace/client/.claude/docs/game-design/battle-gdd.md) — по ТЗ пользователя
(воздушный бой, параметры самолётов). ГДД — цель, код может отставать: расхождения и отложенные
правила — в [#tradeoffs](#tradeoffs) п.17–22. Наземный бой танков в ГДД ещё не описан, его правила
собраны в [#gdd-link](#gdd-link) как кандидаты. Слот аэродрома N из ГДД — позиция `8 − N` в коде
(слот 1 — позиция 7, слот 8 — позиция 0).

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду (код в рамках
> задачи не менялся), 2026-10-15; обновлён 2026-10-17 (ссылки на ГДД, решения пользователя); актуализирован 2026-10-19 после merge `origin/amnesia/fix` (рейтинговый бой кампании, удаление туториального бота). Всё ниже подтверждено чтением кода, запуском не проверялось.
> Клиентский движок `src/battle` не анализировался: его разбирает `client-analyst-lead`, сверка
> детерминизма — через `integration-lead` (точки сверки — [#client-divergence](#client-divergence)).
>
> Смежные документы, которые здесь не пересказываются:
> [campaign-architecture.md](campaign-architecture.md) — кампания как потребитель боя (создание
> `BattleData`, эмуляция в `completeBattle`, награды за юнитов, сложность бота);
> [tank-airplane-data-architecture.md](tank-airplane-data-architecture.md) — откуда берутся параметры
> техники;
> [quests-architecture.md#progress-sources](quests-architecture.md#progress-sources) и
> [achievements-architecture.md#progress-sources](achievements-architecture.md#progress-sources) —
> прогресс за уничтоженных юнитов (начисляется через роуты кампании, не движком).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
   - [Границы области: бой и Battlefield](#scope)
   - [Тик боя и порядок шагов](#tick)
   - [Танки в бою](#tanks)
   - [Самолёты в бою](#airplanes)
   - [Урон](#damage)
   - [Конец боя, места и победитель](#ending)
   - [Детерминизм и пересимуляция кампании](#determinism)
   - [Где сервер может разойтись с клиентом](#client-divergence)
   - [Режим реального времени (Battlefield)](#realtime)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. [Классы и методы](#classes)
8. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Пакет `model.battle` — общий движок автобоя: бойцы (`Fighter`) выставляют до 12 танков и до 8
самолётов, юниты сами перезаряжаются, выбирают цели и наносят урон; бой идёт фиксированными тиками
по 16 мс, всё поведение пишется событиями (`BattleEvent`). Случайность — только из
детерминированного генератора `BattleRandom`, зерно (seed) задаётся при создании боя.

Движок работает в двух режимах:

- **Пересимуляция (кампания).** `CampaignBattle` прогоняется синхронно до конца в обработчике
  `/ingame/campaign/battleResult`; сервер берёт победителя своей симуляции. Рейтинговый бой кампании
  (`RankedChallengeService`) идёт тем же путём: `CampaignUserComponent.createRankedBattle` собирает
  `BattleData` из двух `BattleFighterData`, `completeBattle` прогоняет тот же `CampaignBattle`. Клиент получает те же
  `BattleData` (seed + команды) и проигрывает бой у себя. Как кампания создаёт и вызывает бой —
  [campaign-architecture.md#battle-flow](campaign-architecture.md#battle-flow).
- **Реальное время (Battlefield).** `BattlefieldBattle` живёт в актёре `BattleActor`, тикает по
  реальным часам и рассылает события игрокам по WebSocket; игроки влияют на бой действиями
  (`/ingame/battle/*`). См. [#realtime](#realtime).

<a id="scope"></a>
### Границы области: бой и Battlefield

Battlefield — **отдельная фича** со своим `BattlefieldUserComponent`, страницей
`/ingame/battlefield`, сервисом-актёром `BattlefieldService`/`BattlefieldActor`, лигой `League`,
рейтингом `RatingBattlefieldService` и `BattlefieldDao`. В этот документ она не входит; здесь она
описана только как потребитель движка (наследники `BattlefieldBattle`/`BattlefieldFighter`, что они
переопределяют). Нужен свой документ и, по гарантированному признаку ([area-sign](/workspace/client/.claude/docs/agent-system-workflow.md#area-sign)), свой агент.

Но часть кода пакета `model.battle` фактически обслуживает только Battlefield:
`BattleUserComponent` (id текущего боя игрока), `BattleActor`/`BattleActorPolicy`, `BattleStore`,
`BattlePage` (`/ingame/battle`), действия `actions/*`, режим реального времени в `Battle`. Кампания
их не использует. Они описаны здесь, потому что лежат в пакете движка, а `BattlePage` уже зависит от
battlefield-класса `ActionSlot` (см. [#tradeoffs](#tradeoffs) п.12).

<a id="tick"></a>
### Тик боя и порядок шагов

Один шаг `Battle.update(long dt)` (`Battle.java:253-355`), в кампании всегда `dt = 16`:

1. Первый тик — `init()`: каждому бойцу по порядку `fightersList` назначается противник
   (`initOpponent`: пары 0↔1, 2↔3, …), каждый танк получает случайную задержку появления
   `0..500` мс (`UnitTank.init`, тратит RNG), самолёты — только флаг "жив".
2. Если бой в состоянии `ENDED` — `onEnding()`, флаг `FINISH`, выход (бой закончен).
3. События из очереди, у которых `time <= battle.time`, исполняются **в порядке добавления**;
   исполненные пишутся в лог (`log`), в реальном времени — рассылаются. Исполненные удаляются.
4. Реальное время: `botLogic()` ботов.
5. Действия игроков (`executeAction`) по каждому бойцу.
6. `Fighter.update(dt)` по каждому бойцу в порядке `fightersList` (внутри — танки, затем самолёты в
   порядке позиций).
7. Если `ENDING` — ставится `ENDED`, выход (следующий тик закроет бой).
8. Расстановка мест выбывших, проверка конца боя (выжил ≤1 или вышло время `endTime`) — см.
   [#ending](#ending).
9. `onTick()`, затем `battle.time += dt`.

Событие, созданное на тике, исполняется не раньше следующего тика (шаг 3 уже пройден). Время
событий кратно 16 мс: событие с `time = now + 500` сработает на первом тике, где `battle.time`
достигло этого значения. У каждого юнита и бойца свой счётчик `time`, он растёт вместе с
`battle.time`, поэтому `now` в событиях и внутреннее время юнитов совпадают.

<a id="tanks"></a>
### Танки в бою

ГДД: поле боя — [campaign-gdd.md#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield); правил наземного боя
(выстрел, урон, броня) в [battle-gdd.md](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-purpose) пока нет, они ждут отдельного ТЗ.

- **Позиции** 0..11, три линии по 4 (0–3, 4–7, 8–11). Танк копируется из сумки (`Tank.copy()`), hp
  и прочность брони берутся из `TankParams` (параметры — [tank-airplane-data-architecture.md](tank-airplane-data-architecture.md)).
- **Жизненный цикл** (`UnitTank.stateHandling`): ожидание `idle` → появление (событие
  `TankSpawnEvent`, 1000 мс анимации) → стрельба по готовности перезарядки → при hp ≤ 0 событие
  `TankDestroyedEvent` и вечный простой. Замена (`markAsReplaced`) — только в Battlefield.
- **Перезарядка** (`TankRecharge`, режим `AUTO` в кампании): после выстрела ждёт
  `recharge + 300` мс (300 мс — пауза "снаряд заряжен" для UI), событие `TankRechargeEvent`.
- **Выбор цели** (`UnitTank.getTarget`): таблица приоритетов по своей позиции — танк бьёт "свою
  колонку" противника зеркально (позиция 0 → 3, 7, 11; 1 → 2, 6, 10; 2 → 1, 5, 9; 3 → 0, 4, 8,
  для позиций 4–11 то же по модулю 4). Первый живой из списка; никого — случайный живой танк
  противника (RNG). Танки по самолётам не стреляют.
- **Выстрел** (`attackTank`): промах с шансом 5% (`getRandomInt(1,100) <= 5`, RNG на каждый
  выстрел), событие `TankAttackEvent`; при попадании — `TankTakeDamageEvent` через 500 мс.

<a id="airplanes"></a>
### Самолёты в бою

ГДД: [#gdd-airplane-params](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-airplane-params), [#gdd-air-positions](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-positions),
[#gdd-air-combat](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-combat), [#gdd-air-target](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-target),
[#gdd-bomb](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-bomb), порядок взлёта — [aerodrome-gdd.md#gdd-takeoff-order](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-takeoff-order).

- **Позиции** 0..7 (слот N из ГДД = позиция `8 − N`, [#gdd-air-positions](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-positions)).
  Типы по позициям (`AirplaneType.TYPE_POSITION`): истребители и тяжёлые истребители — 4–7 (слоты
  4–1), штурмовики — 2–3, бомбардировщик — 1, стратегический бомбардировщик — 0 (слот 8).
- **Самолёт не держит бойца в бою** ([#gdd-battle-end](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-battle-end)). "Жив" боец, пока у него есть живой танк (`Fighter.isAlive`,
  `isDestroyed` — только по танкам). Боец без танков проигрывает сразу, даже с самолётами. Но hp
  самолётов входят в `getTotalHp` — сортировку выживших при конце по времени.
- **Очередь взлёта** (`Fighter.update`, `Fighter.java:300-327`): по одному самолёту, позиции от 7
  к 0 (сначала истребители, стратег последним). Выбранный самолёт выводится на полосу
  (`prepareTakeoff`, событие `AirplanePrepareTakeoffEvent`, `takeoffTime = 5000`), через 5000 мс
  получает разрешение (`clearanceTakeoff`), следующий выбирается, когда прошло ещё больше 1000 мс
  после этого момента. Итог: первый взлёт на 5-й секунде, далее примерно каждые 6 секунд
  (5000 + 1000 + до одного тика).
- **Взлёт и появление** (`UnitAirplane.stateHandling`): разрешение → `AirplaneTakeoffEvent`, 1500 мс
  → `AirplaneSpawnEvent`, 1000 мс → бой. Перезарядки тикают только после появления.
- **Пулемёт** (воздух-воздух, `gunRecharge`): цель — только появившиеся живые самолёты противника.
  Цель запоминается до её гибели или смены противника (`resetTarget`). Выбор: приоритет 0 по таблице
  позиции, затем приоритет 1, затем любой живой; внутри группы — случайный (RNG). Нет цели —
  заряженный пулемёт ждёт 500 мс и проверяет снова. Урон через 1000 мс
  (`AirplaneTakeDamageEvent`), броня самолёта и манёвренность не учитываются.
- **Бомбы** (воздух-земля, `bombRecharge`; сброс сразу по перезарядке, отдельной задержки до
  первого сброса нет, "как в коде", решение пользователя 2026-10-17, [#gdd-bomb](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-bomb)): выстрел тратится сразу, даже если целей нет. Тип
  (`AirplaneBombType`): `SOLO` — один случайный живой танк; `LINE` — случайная линия из тех, где
  стоит хоть один танк (включая мёртвые, см. [#tradeoffs](#tradeoffs) п.6), удар по живым в линии;
  `MASS` — все живые танки; `NONE` — бомб нет (перезарядка 0 → оружие выключено). На каждую цель
  своя случайная задержка 0..800 мс (RNG): `AirplaneAttackEvent` через задержку, урон
  `TankTakeDamageEvent` через `5500 + задержка` мс.
- **Гибель** — только от пулемётов истребителей противника. `takeDamage` сразу ставит `DESTROYED`
  (у танка — только при следующем шаге состояния), событие `AirplaneDestroyedEvent` — на ближайшем
  шаге самолёта.
- **Не используются в бою** (отложено, [#tradeoffs](#tradeoffs) п.17) параметры `bombDelay`, `gunType`, `armorType` самолёта
  (`AirplaneParams`), формат перезарядки "N/пауза/выстрелы" (`AirplaneRecharge` читает только первое
  число).

<a id="damage"></a>
### Урон

ГДД: урон по самолётам и бомбы — [#gdd-armor-guns](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-armor-guns),
[#gdd-maneuverability](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-maneuverability), [#gdd-bomb](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-bomb) (броня и манёвренность
пока не реализованы, [#tradeoffs](#tradeoffs) п.17); урона по танкам в ГДД нет.

`TankTakeDamageEvent` (по танку) и `AirplaneTakeDamageEvent` (по самолёту) считаются в момент
исполнения события (через 500–6300 мс после выстрела):

- **Отмена удара.** При создании события запоминается "хэш": счётчик смен противника у атакующего
  бойца и счётчик уворотов у цели. Если к моменту удара он изменился, событие недействительно — урона
  нет, `apiResponse()` возвращает `null`. В кампании действий нет, поэтому отмена не срабатывает.
- **Танк по танку** (`fromTank`): `damage` атакующего × модификатор снаряд/броня
  (`BattleBalance`: AP 0.75/1.25/1.0, HE 1.25/1.0/0.75, HEAT 1.0/0.75/1.25 против
  лёгкой/композитной/тяжёлой). Если прочность брони цели ушла в минус, урон растёт на столько
  процентов. Округление вниз. Если пробитие не больше брони цели — блок с шансом, равным прочности
  брони в процентах (RNG; бросок идёт и по уже мёртвой цели). Затем цель теряет
  `armorLossDurability` прочности (в данных это фактически ordinal снаряда — см.
  [tank-airplane-data-architecture.md#tradeoffs](tank-airplane-data-architecture.md#tradeoffs) п.1).
- **Самолёт по танку** (`fromAirplane`): `bombDamage` без модификаторов и блока; прочность брони
  танка тоже падает.
- **Самолёт по самолёту**: `gunDamage`, без модификаторов.
- Общие множители: бой "бесконечный" (`isInfinity`) — урон 0 (флаг нигде не ставится); бонус урона
  `getDamageBoost()` в процентах — в базовом бою 0, растёт со временем только в Battlefield.

<a id="ending"></a>
### Конец боя, места и победитель

ГДД: [#gdd-battle-end](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-battle-end), поражение в кампании —
[campaign-gdd.md#gdd-defeat](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-defeat).

- Выбывший (все танки уничтожены) получает место `всего − (всего − выжившие_до_тика) − сдвиг`;
  несколько выбывших в одном тике получают разные места по порядку `fightersList`.
- Конец: выжило ≤ 1 бойца или вышло время (`endTime`, только Battlefield, 10 минут). Выжившие
  сортируются по сумме hp танков и самолётов (`FighterComparator`, при равенстве — порядок
  `fightersList`), получают места с 1-го. Победитель — первый выживший; если не выжил никто —
  первый боец в списке (в кампании это игрок, см.
  [campaign-architecture.md#tradeoffs](campaign-architecture.md#tradeoffs) п.5).
- `BattleResultEvent` исполняется на следующем тике (`complete()` → `ENDING`); в этом тике юниты ещё
  обновляются (могут стрелять, на победителя это не влияет), ещё через тик — `onEnding()` и `FINISH`
  (`isEnded()`).
- Принудительный конец (`ForceEndEvent`, `forceEnd`): все живые бойцы, кроме первого живого,
  убиваются уроном 999 999 999.

<a id="determinism"></a>
### Детерминизм и пересимуляция кампании

Сервер не сравнивает лог клиента с собственным: клиент шлёт только `win`. Проигрыш принимается без
симуляции; на заявленную победу сервер прогоняет `CampaignBattle` по тем же `BattleData` и решает
по своему победителю ([campaign-architecture.md#m-actionbattleresult](campaign-architecture.md#m-actionbattleresult)).
Расхождение движков поэтому бьёт по одной стороне: игрок увидел победу, а уровень не вырос.

Что делает серверную симуляцию воспроизводимой:

- **Генератор** `BattleRandom` — xorshift32 (`seed ^= seed << 13; seed ^= seed >>> 17;
  seed ^= seed << 5`) над 32-битным `int`, результат `(seed & 0xffffffff) / 2^32` в `[0,1)`.
  `getRandomInt(min, max)` = `(int)(next() * (max − min + 1)) + min`. Seed — `1..Integer.MAX_VALUE`
  (`BattleData.initSeed`).
- **Фиксированный шаг** 16 мс без реальных часов: `completeBattle` вызывает `update(TICK_TIME)`
  напрямую; `Battle.update()` с `System.currentTimeMillis` используется только актёром Battlefield.
- **Порядок итерации** — списки (`ArrayList`, `TeamMembers` по позициям 0..N), не хэш-таблицы:
  `fighters` (`HashMap`) используется только для поиска по uid.
- **Команды фиксируются до боя.** Случайный выбор модели бота (`RandomJdk`, не seed) происходит в
  `BattleDataFactory` при создании `BattleData`; параметры техники уходят клиенту в
  `tank.params`/`airplane.params` готовыми.

Порядок потребления RNG (любая перестановка на клиенте меняет весь бой):

1. Первый тик: по одному числу на танк (`0..500`), бойцы по порядку, танки по позициям.
2. Каждый тик, бойцы по порядку, внутри — танки, затем самолёты по позициям:
   выстрел танка — бросок промаха `1..100` (если цель есть), перед ним при пустой таблице
   приоритетов — выбор случайного живого танка;
   пулемёт самолёта при поиске новой цели — выбор среди группы;
   бомба — `SOLO`: выбор танка; `LINE`: выбор линии; затем по числу целей — задержки `0..800`.
3. Исполнение событий (до шага 2, в порядке добавления): каждый удар танка по непробиваемой цели —
   бросок блока `1..100`.

<a id="client-divergence"></a>
### Где сервер может разойтись с клиентом

Клиент здесь не проверялся. Ниже — места серверной логики, где расхождение наиболее вероятно; их
нужно сверить с `src/battle` через `integration-lead`.

1. **Округление урона — `float` против `double`.** Сервер считает урон танка в 32-битном `float`
   (`TankTakeDamageEvent.java:71-78`). JavaScript по умолчанию считает в `double`. Проверено
   перебором (урон 1..300, три модификатора, прочность брони −1..−60): 196 комбинаций дают разный
   `floor`, например урон 20, AP по композитной (×1.25), прочность −16: сервер 29, `double` 28.
   Расхождение появляется только после того, как прочность брони цели ушла в минус, то есть в
   длинных боях.
2. **Шаг времени.** Сервер — ровно 16 мс, события срабатывают на границах тиков. Клиент с
   переменным кадром (`requestAnimationFrame`) разойдётся, если логика не идёт фиксированным шагом.
3. **Порядок шагов тика** ([#tick](#tick)): события → действия → бойцы → места → время. Событие,
   созданное в тике, исполняется в следующем.
4. **Паузы и константы:** `+300` мс к перезарядке (`TankRecharge.java:97`,
   `AirplaneRecharge.java:101`), появление 1000, полёт снаряда танка 500, пулемёта 1000, бомбы
   5500 + 0..800, взлёт 5000/1500, пауза между взлётами +1000, ожидание пулемёта 500, промах 5%.
5. **Порядок и условия бросков RNG** ([#determinism](#determinism)), особенно: блок бросается и по
   мёртвой цели; бомба тратит выстрел без целей, но RNG тратит только при выборе; `LINE` выбирает
   линию с мёртвыми танками.
6. **Генератор:** сдвиг `>>>` (беззнаковый), приведение к беззнаковому перед делением, `(int)`
   отбрасывает дробь (для неотрицательных совпадает с `Math.floor`).
7. **Победитель при одновременной гибели** — первый в `fightersList` (игрок); сортировка выживших
   устойчивая.
8. **Танк "мёртв" и "уничтожен" — разные состояния.** `takeDamage` снимает `ALIVE`, `DESTROYED`
   ставится на шаге состояния юнита (`UnitTank.java:174-178`); цели выбираются по `isAlive`, конец
   боя — по `isDestroyed`. У самолёта оба флага ставятся сразу.
9. **Отладка.** В dev-режиме `/battleResult` отдаёт полный лог серверной эмуляции
   (`getBattleResultJSON`), но в записях лога нет времени события
   (`BattleEvent.apiResponse` — только `id` и поля), поэтому сравнить с клиентом по тикам нельзя.

<a id="realtime"></a>
### Режим реального времени (Battlefield)

Кратко, как потребитель движка. `BattlefieldBattle` включает `markAsRealtime()` и
`setDuration(10 мин)`, юниты в режиме `RechargeMode.INSTANT` (стреляют по команде
`fullRecharge`), бонус урона растёт со временем, места и итог уходят в `BattlefieldService`.
`League.startBattle` создаёт `BattleData` типа `BATTLEFIELD`, кладёт бой в `BattleStore`
(актёр `BattleActor`, тик актёра 250 мс, внутри догоняет реальное время шагами по 16 мс) и шлёт
игрокам `NewBattleMessage`; `BattlefieldUserComponent` записывает id боя в `BattleUserComponent` и
шлёт уведомление `battleInfo`. Игрок подписывается (`/ingame/battle/subscribe` → `ActionSubscribe` →
пакет `/events/battle/init`) и шлёт действия `/changeOpponent`, `/dodge`, `/charge`. События
рассылаются только связанным бойцам (`broadcastEvent`).

<a id="references"></a>
## 2. Референсы

Внешних референсов в коде нет. Комментарий `BattleData` фиксирует цель: "на одинаковом seed обе
стороны должны показать одинаковый результат" — клиентский движок `src/battle` является парным
референсом для серверного.

<a id="patterns"></a>
## 3. Паттерны

- **Фиксированный шаг симуляции + аккумулятор** (`Battle.update()`): реальное время копится и
  расходуется шагами по 16 мс.
- **Детерминированный PRNG с seed** (`BattleRandom`, xorshift32) — общий для сервера и клиента.
- **Очередь отложенных событий** (`BattleEvent.setTime`): выстрел и попадание разнесены во времени,
  урон считается при исполнении; события же служат логом и сетевым протоколом.
- **Отмена по версии** (хэш счётчиков уворота/смены противника) вместо удаления событий из очереди.
- **Шаблонный метод**: `Battle.initData/onFighterPlace/onEnding/onTick/getDamageBoost`,
  `Fighter.botLogic/onInFocus/onOutFocus/onChangeOpponent/handleAction` — точки расширения для
  `CampaignBattle`/`BattlefieldBattle`.
- **Конечный автомат перезарядки** (`TankRecharge`/`AirplaneRecharge`: IDLE → RECHARGE → PREPARE →
  CAN_SHOT, DISABLE) с тремя режимами (`RechargeMode`).
- **Битовые флаги состояния** у `Battle`, `UnitTank`, `UnitAirplane`.
- **Актёр на бой** (`BattleActor` в `BattleStore`, Akka) — только для реального времени.

<a id="class-list"></a>
## 4. Список классов

Задача — анализ, классы не создавались и не менялись. Компонент целиком:

- ядро: `Battle`, `Fighter`, `BattleUnit`, `BattleRandom`, `BattleBalance`, `BattleEvent`,
  `BattleType`, `BattleLocation`;
- юниты: `units/UnitTank`, `units/UnitAirplane`;
- перезарядка: `recharge/TankRecharge`, `recharge/AirplaneRecharge`, `recharge/RechargeMode`;
- данные: `data/BattleData`, `data/BattleFighterData`, `data/BattleTankData`,
  `data/BattleAirplaneData`, `data/BattleDataFactory`;
- события: `events/tank/*` (6), `events/airplane/*` (8), `events/*` (7);
- реальное время: `BattleUserComponent`, `BattleActor`, `BattleActorPolicy`, `actions/*` (5),
  `service/battle/BattleStore`, `pages/ws/ingame/BattlePage`.

<a id="anchors"></a>
## 5. Навигация (якоря)

Разделы: [#purpose](#purpose), [#scope](#scope), [#tick](#tick), [#tanks](#tanks),
[#airplanes](#airplanes), [#damage](#damage), [#ending](#ending), [#determinism](#determinism),
[#client-divergence](#client-divergence), [#realtime](#realtime), [#tradeoffs](#tradeoffs),
[#gdd-link](#gdd-link), [#file-map](#file-map). Классы — в [#class-nav](#class-nav), методы с логикой —
`#m-<класс>-<метод>`.

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Якорь |
|---|---|
| `Battle` | [#cls-battle](#cls-battle) |
| `Fighter` | [#cls-fighter](#cls-fighter) |
| `BattleUnit` | [#cls-battleunit](#cls-battleunit) |
| `UnitTank` | [#cls-unittank](#cls-unittank) |
| `UnitAirplane` | [#cls-unitairplane](#cls-unitairplane) |
| `TankRecharge`, `AirplaneRecharge`, `RechargeMode` | [#cls-recharge](#cls-recharge) |
| `BattleRandom` | [#cls-battlerandom](#cls-battlerandom) |
| `BattleBalance` | [#cls-battlebalance](#cls-battlebalance) |
| `BattleEvent` и наследники | [#cls-events](#cls-events) |
| `BattleData`, `BattleFighterData`, `BattleTankData`, `BattleAirplaneData` | [#cls-data](#cls-data) |
| `BattleDataFactory` | [#cls-battledatafactory](#cls-battledatafactory) |
| `BattleUserComponent` | [#cls-battleusercomponent](#cls-battleusercomponent) |
| `BattleActor`, `BattleActorPolicy`, `BattleStore` | [#cls-actor](#cls-actor) |
| `BattlePage`, `actions/*` | [#cls-battlepage](#cls-battlepage) |
| `BattleType`, `BattleLocation` | [#cls-enums](#cls-enums) |

<a id="classes"></a>
## 7. Классы и методы

Пути — от `game/src/main/java/com/linkedgames/game/`. "Правило" — кандидат в раздел будущего ГДД
боя (см. [#gdd-link](#gdd-link)).

<a id="cls-battle"></a>
### `Battle` (`model/battle/Battle.java`, абстрактный)

Состояние боя: бойцы (`fighters` по uid и `fightersList` по порядку), очередь событий, лог, время,
флаги (`STARTED`, `PAUSED` — не используется, `ENDING`, `ENDED`, `INFINITY`, `REALTIME`,
`WAIT_TANKS` — не используется, `FINISH`), seed и генератор, выжившие, победитель. Константы
WS-путей `/events/battle/init|update|event|survivors|result` (`update` и `result` не используются).

- `Battle(BattleData)` — uid, `initSeed(data.seed)`, затем абстрактный `initData(data)`
  (наследник создаёт бойцов и юнитов).
- <a id="m-battle-update"></a>**`update(long dt)`** — один тик, порядок — [#tick](#tick). Правило: ход боя ([#gdd-purpose](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-purpose)); места и конец боя —
  [#gdd-battle-end](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-battle-end).
- <a id="m-battle-update-rt"></a>**`update()`** — реальное время: `dt` от `System.currentTimeMillis`,
  аккумулятор, шаги по `TICK_TIME`.
- <a id="m-battle-initopponent"></a>**`initOpponent(Fighter)`** — стартовый противник: соседний по
  индексу (чётный → следующий, нечётный → предыдущий). Правило: начальная пара. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)).
- <a id="m-battle-getanyopponent"></a>**`getAnyOpponent(Fighter)`** — тонкая обёртка над `initOpponent`
  (комментарий в коде: "полезно для 1vs1"). Вызывается `CampaignUserComponent.completeBattle` и
  `CampaignBattleResult` для проигравшего рейтингового боя. Дубль смысла (правило: начальная пара,
  без RNG и проверки живости) — см. [#tradeoffs](#tradeoffs) п.21.
- <a id="m-battle-getopponent"></a>**`getOpponent(Fighter)`** — новый противник: случайный живой,
  кроме себя и (если живых больше двух) текущего. RNG. Правило: смена противника. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)).
- `getUnit(uid)` — поиск юнита по всем бойцам (сравнение uid по ссылке, см. [#tradeoffs](#tradeoffs)
  п.9).
- <a id="m-battle-getsortedalive"></a>**`getSortedAlive()`** — не уничтоженные бойцы, по убыванию
  `getTotalHp`. Правило: места выживших. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)).
- <a id="m-battle-forceend"></a>**`forceEnd()`** — убить всех живых, кроме первого живого.
- `getRandomInt(min, max)` — целое из `BattleRandom` включительно.
- `getBattleResultJSON()` — `{uid, seed, log, winner}` (dev-ответ кампании);
  `getBattleJSON(fighter)` — `{uid, seed, survivors, fighters: [свой, противник], meta}` для
  `/events/battle/init`; `meta` — плотно упакованный массив всех бойцов (`Fighter.getMetaJSON`).
- `broadcastEvent(event)` (private) — рассылка события живым игрокам: глобальное — всем; иначе
  участникам и тем, чей противник участвует.
- Тривиальные: `assignActor`, `markAsInfinity`, `markAsRealtime`, `setDuration`, `getSeed`,
  `initSeed()`/`initSeed(int)`, `isInfinity`, `isRealtime`, `isEnded`, `getTime`, `complete`,
  `addEvent`, `getFighter`, `addFighter`, `getWinner`, `getDamageBoost` (0).
- Хуки: `onFighterPlace`, `onEnding`, `onTick` — пустые.

<a id="cls-fighter"></a>
### `Fighter` (`model/battle/Fighter.java`)

Участник боя: uid, имя, признак бота (`uid.getTimestamp() == 0`), противник, версия (для уворота),
счётчики `state[DODGE, CHANGE_OPPONENT]`, танки, самолёты, суммарная мощность, время, таймер взлёта,
место, очередь действий, сессии WS (до 5).

- `init(Battle)` — противник через `initOpponent`, `onInFocus`, запоминание версии противника,
  `init()` юнитов.
- <a id="m-fighter-update"></a>**`update(long dt)`** — смена противника, если он сменён вручную,
  увернулся (версия изменилась) или уничтожен, а сам боец жив (`onChangeOpponent`, новый через
  `getOpponent`, `NewOpponentEvent`); уничтоженный боец теряет противника. Без противника — ничего не
  делает. Затем очередь взлёта ([#airplanes](#airplanes)) и `update` всех юнитов. Правило: смена противника, взлёт самолётов ([aerodrome-gdd.md#gdd-takeoff-order](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-takeoff-order)).
- <a id="m-fighter-isalive"></a>**`isAlive()` / `isDestroyed()`** — только по танкам. Правило: поражение бойца ([#gdd-battle-end](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-battle-end)).
- `getTotalHp()` — hp танков и самолётов.
- `getTankByPosition`/`getAirplaneByPosition` — не заменённый юнит на позиции (может быть мёртв).
- `getAliveTanks`, `getRandomAliveTank` (RNG), `getAliveAirplanes` (только появившиеся).
- `changeVersion()` — уворот: версия +1, счётчик `DODGE` +1. `changeOpponent()` — версия
  противника `-1`, счётчик `CHANGE_OPPONENT` +1.
- `kill()` — урон 999 999 999 всем танкам.
- `handleAction(IAction)` — `ActionInfo` (ответ ok), `ActionSubscribe` (сессия + `/events/battle/init`),
  `ActionChangeOpponent`/`ActionDodge` (событие в очередь). `executeAction` разбирает очередь.
- Хуки: `botLogic`, `onInFocus`, `onOutFocus` — пустые; `onChangeOpponent` сбрасывает цели самолётов.
- Тривиальные: геттеры, `setPlace`, `addUnit` (+мощность), `getTank`/`getAirplane` по uid,
  `addAction`, `sendWSEvent`, `getMetaJSON`, `apiResponse`.

<a id="cls-battleunit"></a>
### `BattleUnit` (`model/battle/BattleUnit.java`, абстрактный)

uid и тип (`TANK = 1`, `AIRPLANE = 2`), `is(type)`, абстрактный `getFighter()`, `apiResponse()`
`{uid, type}`.

<a id="cls-unittank"></a>
### `UnitTank` (`model/battle/units/UnitTank.java`)

Танк в бою: позиция, копия `Tank`, hp, прочность брони, перезарядка, флаги
(`SPAWNED`, `ALIVE`, `DESTROYED`, `REPLACED`), время, `idle`, `attackTime`.

- `init()` — `ALIVE` + случайная задержка 0..500 мс (RNG).
- <a id="m-unittank-statehandling"></a>**`stateHandling()`** — появление → замена → уничтожение →
  выстрел, см. [#tanks](#tanks). Правило: жизненный цикл танка. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)).
- <a id="m-unittank-attacktank"></a>**`attackTank()`** — цель, промах 5% (RNG), события атаки и урона
  (+500 мс). Правило: выстрел танка, промах. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)).
- <a id="m-unittank-gettarget"></a>**`getTarget()`** — таблица `TARGET_PRIORY_TABLE`, иначе случайный
  живой. Правило: выбор цели танком. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)).
- `takeDamage(int)` — hp вниз до 0, снимает `ALIVE`.
- `markAsReplaced()` — `DESTROYED` + `REPLACED` (Battlefield).
- Тривиальные: геттеры, `setHp` (не вызывается), `addArmorDurability`, `setRechargeMode`,
  `addRechargeTime` (не вызывается), `fullRecharge`, `isAlive/isDestroyed/isReplaced/isAvailable/
  isAttacks`, `getMetaJSON` `[uid, id, rank, level, starsId]`, `apiResponse`.

<a id="cls-unitairplane"></a>
### `UnitAirplane` (`model/battle/units/UnitAirplane.java`)

Самолёт в бою: позиция, копия `Airplane`, hp, две перезарядки (пулемёт, бомбы), запомненная цель,
флаги (`SPAWNED`, `ALIVE`, `DESTROYED`, `REPLACED`, `PREPARE_TAKEOFF`, `CLEARANCE_TAKEOFF`, `IN_AIR`).

- `init()` — только `ALIVE`.
- `prepareTakeoff()` / `clearanceTakeoff()` — флаги очереди взлёта, ставит `Fighter`.
- <a id="m-unitairplane-statehandling"></a>**`stateHandling()`** — взлёт → (на земле — ничего) →
  появление → замена → уничтожение → пулемёт (нет цели — `idle(500)`) → бомбы. Правило: жизненный цикл самолёта
  ([#gdd-air-combat](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-combat), [#gdd-air-positions](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-positions)).
- <a id="m-unitairplane-attacktank"></a>**`attackTank()`** — бомбы по целям `getTargetTanks()`,
  задержка 0..800 на цель (RNG), урон через 5500 + задержка. Правило: бомбовый удар ([#gdd-bomb](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-bomb)).
- <a id="m-unitairplane-gettargettanks"></a>**`getTargetTanks()`** — `SOLO`/`LINE`/`MASS`, см.
  [#airplanes](#airplanes). Правило: зона поражения бомб ([#gdd-bomb](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-bomb)).
- <a id="m-unitairplane-attackairplane"></a>**`attackAirplane()`** — пулемёт по
  `getTargetAirplane()`, урон через 1000 мс; `false`, если цели нет. Правило: пулемётный бой
  ([#gdd-air-combat](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-combat)).
- <a id="m-unitairplane-gettargetairplane"></a>**`getTargetAirplane()`** — запомненная живая цель,
  иначе приоритет 0 → 1 → любая (RNG внутри группы). Правило: выбор воздушной цели ([#gdd-air-target](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-target)); таблицы
  `TARGET_AIRPLANE_PRIORY_TABLE_0/1` по позициям совпадают с таблицей ГДД по слотам `8 − N`
  (сверено 2026-10-17).
- `takeDamage(int)` — hp вниз до 0, снимает `ALIVE`, сразу ставит `DESTROYED`.
- `resetTarget()` — забыть цель (смена противника).
- Тривиальные: геттеры, `setHp` (не вызывается), `setRechargeMode`, `addRechargeTime` (не
  вызывается), `fullRecharge`, флаговые `is*`, `isAttacks` (`attackTime` никогда не растёт —
  всегда `false`), `markAsReplaced`, `getMetaJSON` `[uid, id, rank, starsId]`, `apiResponse`.

<a id="cls-recharge"></a>
### `TankRecharge`, `AirplaneRecharge`, `RechargeMode` (`model/battle/recharge/`)

Автомат перезарядки одного оружия. Параметры: время перезарядки, пауза между выстрелами, число
выстрелов в обойме. `TankRecharge` понимает строку `"N"` и `"N/пауза/выстрелы"`,
`AirplaneRecharge` — только первое число; фактически оба получают `String.valueOf(int)`, поэтому
обойма всегда из одного выстрела. Перезарядка 0 → `DISABLE`.

- <a id="m-recharge-update"></a>**`update(long dt)`** — `IDLE`: остались выстрелы → `PREPARE` (пауза),
  нет → `RECHARGE` (в `AUTO` — `time + recharge + 300` и событие перезарядки). `RECHARGE` в `AUTO` —
  по времени в `CAN_SHOT`; в `MANUAL`/`INSTANT` — копит добавленное время, при наборе — `CAN_SHOT`,
  событие с процентом (в `INSTANT` без события). `PREPARE` — по времени в `CAN_SHOT`. Правило: скорострельность ([#gdd-airplane-params](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-airplane-params) для самолётов; для
  танков правила в ГДД нет).
- `canShot`, `doShot` (минус выстрел, `IDLE`), `idle(duration)` (только самолёт — отложить готовый
  выстрел), `addRechargeTime`, `fullRecharge`, `setMode`, `apiResponse`.
- `RechargeMode`: `AUTO` (кампания), `MANUAL` (нигде не включается), `INSTANT` (Battlefield).

Два класса — копии одного автомата (см. [#tradeoffs](#tradeoffs) п.10).

<a id="cls-battlerandom"></a>
### `BattleRandom` (`model/battle/BattleRandom.java`)

xorshift32, `next()` в `[0,1)`. Формула — [#determinism](#determinism). Правило: воспроизводимость боя ([#gdd-purpose](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-purpose)).

<a id="cls-battlebalance"></a>
### `BattleBalance` (`model/battle/BattleBalance.java`)

`getTankAmmoDamageModifier(ammo, armor)` — таблица 3×3, см. [#damage](#damage). Значения в коде,
не в `balance.json`. Правило: снаряд против брони. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)).

<a id="cls-events"></a>
### `BattleEvent` и наследники (`model/battle/BattleEvent.java`, `events/**`)

`BattleEvent`: `id` (1–20), время срабатывания, `completed`; `execute()` помечает исполненным;
`getFighter0/1/2()` — кому рассылать; `apiResponse()` `{id, …}` — и лог, и сетевой пакет.

| Событие | id | Что делает при исполнении |
|---|---|---|
| `TankSpawnEvent`, `TankReplacedEvent`, `TankDestroyedEvent` (`rewarded` = боец-бот) | 1, 3, 2 | только находит юнит, для лога/клиента |
| `TankRechargeEvent` (`mode`, `shots`, `v0`, `v1`) | 4 | то же |
| `TankAttackEvent` (`isMiss`) | 5 | то же |
| <a id="m-tanktakedamage"></a>`TankTakeDamageEvent` | 6 | проверка хэша, урон от танка/самолёта, потеря прочности, [#damage](#damage). Правило: урон по танку, блок. ГДД: отсутствует (кандидат, см. [#gdd-link](#gdd-link)). |
| `AirplanePrepareTakeoffEvent` (`takeoffTime`), `AirplaneTakeoffEvent`, `AirplaneSpawnEvent`, `AirplaneDestroyedEvent`, `AirplaneReplacedEvent`, `AirplaneRechargeEvent`, `AirplaneAttackEvent` | 7–13 | только находят юнит |
| <a id="m-airplanetakedamage"></a>`AirplaneTakeDamageEvent` | 14 | проверка хэша, урон пулемёта. Правило: урон по самолёту ([#gdd-air-combat](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-combat)) |
| `DodgeEvent` | 15 | `initiator.changeVersion()` |
| `ChangeOpponentEvent` | 16 | `initiator.changeOpponent()` |
| `NewOpponentEvent` | 17 | только рассылка (персонально) |
| `BattlePlaceEvent` | 18 | не создаётся нигде (код закомментирован) |
| `BattleResultEvent` (`winner`) | 19 | `battle.complete()` |
| `SlotResultEvent` | 20 | Battlefield, слот-машина |
| `ForceEndEvent` | −1 | `battle.forceEnd()`, не рассылается |

У событий урона есть второй конструктор по uid без хэша — не используется.

<a id="cls-data"></a>
### `BattleData`, `BattleFighterData`, `BattleTankData`, `BattleAirplaneData` (`model/battle/data/`)

Входные данные боя: `uid`, `seed`, `type`, бойцы (uid, имя, танки и самолёты с позициями). Все поля
публичные для сервера, `apiResponse()` — тот же набор для клиента:
`{uid, seed, type, fighters: [{uid, name, tanks: [{position, tank}], airplanes: [{position, airplane}], ranking?}]}`;
`ranking = {leagueId, rating, place}` добавляется, только если `leagueId != -1`.
`BattleFighterData.leagueId/rating/place` (по умолчанию -1/0/0) заполняет `setRanking` для рейтингового
боя; движок эти поля не читает. `getPower()` — сумма `getPower()` танков и самолётов бойца,
`BattleData.getFighter(uid)` — поиск `BattleFighterData` по uid (или `null`); оба нужны
`CampaignUserComponent.completeBattle` для рейтингового результата. `initSeed()` — случайный seed `1..MAX_INT`. Правило:
одинаковые данные → одинаковый бой.

<a id="cls-battledatafactory"></a>
### `BattleDataFactory` (`model/battle/data/BattleDataFactory.java`)

Сборка `BattleFighterData` из команды (`Team`) пользователя, данных участника Battlefield или бота.
Бот кампании и рост сложности — [campaign-architecture.md#bot-difficulty](campaign-architecture.md#bot-difficulty).
Туториальной ветки нет: `createFighterBotFromUser` всегда берёт `createBotTeam(campaignLevel)`.

- `createFighterFromUser(User)` — команда `user.createTeam()` (копии танков из ангара и самолётов
  из аэродрома).
- `createFighterFromData(UserSignature, Team)` — Battlefield.
- `createFighterBotFromUser(User)` — бот кампании (uid с нулевым временем → `isBot`).
- `createFighterBot(UserSignature, int)` — **не вызывается нигде** (см. [#tradeoffs](#tradeoffs) п.13).
- `createBotTeam`, `getParam` — см. ссылки выше. Выбор модели — `RandomJdk`,
  не seed боя.

<a id="cls-battleusercomponent"></a>
### `BattleUserComponent` (`model/battle/BattleUserComponent.java`)

Id и место (`BattleLocation`) текущего боя реального времени у пользователя. Ничего не сохраняет в
БД (`changedField` не вызывается; `dbMappingBuild` из `User` читает пустой документ).

- `setBattle(battleId, location)`, `clear()` — ставит/сбрасывает; вызываются только из
  `BattlefieldUserComponent` и всегда вместе с `sendNotification()`.
- <a id="m-battleusercomponent-addaction"></a>**`addAction(IAction)`** — нет боя — молча ничего;
  иначе `ActionMessage` в актёр боя через `BattleStore`.
- `sendNotification()` — уведомление `battleInfo` с `{battleId, location}` или его удаление.
- `apiResponse()`, пустой `modifyReceiver`.

<a id="cls-actor"></a>
### `BattleActor`, `BattleActorPolicy`, `BattleStore`

- `BattleActor` (`model/battle/BattleActor.java`) — актёр одного боя: `CreateBattleMessage` (принять
  бой, второй — игнор), `ActionMessage` (действие бойцу), `StopBattleMessage` (`ForceEndEvent`),
  `onTick` → `battle.update()`. По `ENDED` бой сам переводит актёра в `SHUTDOWN_PREPARE`.
- `BattleActorPolicy` — тик актёра 250 мс.
- `BattleStore` (`service/battle/BattleStore.java`) — `ObjectStore` актёров боёв, 4 шарда, очистка
  раз в 5 минут; останавливается в `Globals` при выключении сервера.

<a id="cls-battlepage"></a>
### `BattlePage`, `actions/*`

`pages/ws/ingame/BattlePage.java`, `/ingame/battle`. Все роуты: нет боя — `error`, иначе действие в
`BattleUserComponent.addAction`, ответ `ok` (кроме `""` — ответ даёт сам бой через `ActionInfo`).

| Роут | Действие |
|---|---|
| `""` | `ActionInfo` |
| `/subscribe` | `ActionSubscribe(session)` |
| `/changeOpponent` | `ActionChangeOpponent` |
| `/dodge` | `ActionDodge` |
| `/charge` | `ActionSlot` (класс из `model/battlefield/actions`) |

`IAction` — маркер; `ActionInfo`, `ActionSubscribe`, `ActionChangeOpponent`, `ActionDodge` —
носители данных.

<a id="cls-enums"></a>
### `BattleType`, `BattleLocation`

- `BattleType` (`DEFAULT`, `BATTLEFIELD`) — уходит клиенту ordinal-ом в `BattleData.apiResponse`,
  сервер по нему не ветвится.
- `BattleLocation` (`NONE`, `BATTLEFIELD`) — где идёт бой реального времени, для уведомления
  `battleInfo`.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и подозрительные места

ГДД боя — цель по ТЗ, код может отставать: правила ГДД, которых в коде нет, не считаются багом, а
отложены пользователем 2026-10-17 (п.17–18). Приоритет и статус — предложение аналитика на
2026-10-17. Статусы: «баг» — исправить, «отложено» — решение пользователя, «integration-lead» —
разберёт `integration-lead`, «наблюдение» — без действий до решения.

| Пункт | Приоритет | Статус |
|---|---|---|
| 1 урон в `float` | высокий | integration-lead (в клиентском документе — Д3) |
| 2 нет сравнения боя с клиентом, лог без времени | средний | integration-lead |
| 3 броня уходит в минус без предела | средний | наблюдение (нужно решение ГДД для наземного боя) |
| 4 пробитие не работает в базовых данных | средний | наблюдение (нужно решение ГДД для наземного боя) |
| 5 самолёты и места при конце по времени | низкий | наблюдение (Battlefield) |
| 6 `LINE` выбирает линию с мёртвыми танками | средний | отложено (п.18) |
| 7 мёртвый формат обоймы | низкий | наблюдение |
| 8 неиспользуемые параметры самолёта | средний | отложено (п.17) |
| 9 сравнение `ObjectId` по ссылке | низкий | наблюдение |
| 10 дубли кода | низкий | наблюдение (рефакторинг по решению) |
| 11 мёртвый код | низкий | наблюдение |
| 12 обратные зависимости от Battlefield | низкий | наблюдение |
| 13 `createFighterBot` не вызывается, неточность в campaign-доке | низкий | баг документации (исправляется в campaign-architecture.md) |
| 14 неявный порядок у `BattleUserComponent` | средний | баг (Battlefield) |
| 15 лог боя растёт без ограничения | средний | наблюдение (Battlefield) |
| 16 `BattleResultEvent` на тик позже | низкий | integration-lead |
| 17 броня, пулемёты, манёвренность, времена как параметры | высокий (по ГДД) | отложено |
| 18 `LINE` только по живым линиям | средний | отложено |
| 19 Д1–Д5 клиентского документа | высокий (Д1, Д3), средний (Д2, Д4, Д5) | integration-lead |
| 20 решения "как в коде" | — | не расхождение |

Явных комментариев о компромиссах в коде нет. Ниже наблюдения по коду. Пункты кампании
(`while(true)` без лимита, ничья в пользу игрока, перебор боёв, награды за юнитов без привязки к
бою) описаны в [campaign-architecture.md#tradeoffs](campaign-architecture.md#tradeoffs) п.1, 4–6 и
здесь не повторяются.

1. **Урон в `float` — главный риск расхождения с клиентом.** `TankTakeDamageEvent.java:71-78`; при
   отрицательной прочности брони `floor` от `float` и от `double` расходится (196 комбинаций в
   переборе, пример — [#client-divergence](#client-divergence) п.1). Нужна сверка с клиентом:
   какая сторона и какой тип считаются эталоном.
2. **Сервер не сравнивает бой с клиентом, а пересчитывает только заявленную победу.** Проигрыш
   принимается на слово, победа — по серверному результату. Расхождение видно игроку как "победил,
   а уровень не вырос" без объяснения (см. также campaign п.7). Лог dev-режима без времени событий
   (`BattleEvent.apiResponse`, `BattleEvent.java:84-89`) — сравнить с клиентом по тикам нельзя.
3. **Прочность брони уходит в минус без предела** (`TankTakeDamageEvent.java:75-77, 96`): каждый
   удар добавляет урону `|прочность|` процентов. В длинных боях урон растёт неограниченно. Плюс
   `armorLossDurability` фактически равен ordinal снаряда (AP — 0, у таких целей прочность не
   падает), см. [tank-airplane-data-architecture.md#tradeoffs](tank-airplane-data-architecture.md#tradeoffs) п.1.
4. **Пробитие в базовых данных не работает.** В `balance.json` у всех 348 танков
   `penetration <= armor` (проверено 2026-10-15), поэтому до роста уровня/звёзд каждый удар танка
   по танку идёт через бросок блока (сейчас 10%). Влияет ли рост параметров — не проверялось.
5. **Самолёты не участвуют в условии поражения**, но их hp входят в сортировку мест при конце по
   времени (`Fighter.java:227-244` против `:260-269`). Соответствие замыслу — вопрос к ГДД.
6. **`LINE`-бомба может выбрать линию только из мёртвых танков** (`UnitAirplane.java:308-320`:
   проверка линии через `getTankByPosition`, который возвращает и мёртвых) — удар уходит впустую.
   Бомба тратит выстрел и без целей (`UnitAirplane.java:233-236`).
7. **Перезарядка в формате обоймы мертва.** `TankParams.recharge` и `AirplaneParams.*Recharge` —
   `int`, разбор `"N/пауза/выстрелы"` (`TankRecharge.java:36-45`) недостижим; при строке из двух
   частей список параметров был бы пуст (падение `get(0)`). `AirplaneRecharge` разбирает только
   первое число.
8. **Неиспользуемые параметры самолёта в бою**: `bombDelay`, `gunType`, `armorType`
   (`AirplaneParams.java:10-17`). Нужно решение ГДД: должны ли они влиять.
9. **Сравнение `ObjectId` по ссылке** (`Battle.java:185, 188`, `Fighter.java:158, 197`). Работает,
   пока uid берутся из тех же объектов; uid, пришедший извне (например, из запроса), не найдётся.
10. **Дубли кода (одно правило — одна функция).** `TankRecharge` и `AirplaneRecharge` — один автомат
    с разницей в разборе строки и `idle()`; `getHash` и `fromAirplane` повторяются в двух событиях
    урона; набор флагов `SPAWNED/ALIVE/DESTROYED/REPLACED` и обвязка `markAsReplaced/is*` — в обоих
    юнитах. Кандидаты на общий класс перезарядки и общую базу юнита.
11. **Мёртвый код**: флаги `PAUSED`, `WAIT_TANKS`; `markAsInfinity` (урон 0 недостижим);
    `EVENT_BATTLE_UPDATE`, `EVENT_BATTLE_RESULT`; `BattlePlaceEvent`; `setHp`,
    `addRechargeTime`, `RechargeMode.MANUAL`; конструкторы событий урона по uid;
    `UnitAirplane.isAttacks/attackTime`; `Battle.initSeed()` без аргумента. Кандидаты на удаление.
12. **Обратные зависимости движка от Battlefield.** `Battle.java:327` берёт
    `BattlefieldBattle.EVENT_BATTLE_SURVIVORS` (константа объявлена в самом `Battle`),
    `BattlePage` импортирует `model.battlefield.actions.ActionSlot` (`BattlePage.java:71`).
13. **`createFighterBot` не вызывается** (`BattleDataFactory.java:42-49`), хотя
    [campaign-architecture.md#cls-battledatafactory](campaign-architecture.md#cls-battledatafactory)
    пишет, что он "вызывается вне кампании" — там неточность.
14. **Неявный порядок вызовов у `BattleUserComponent`.** `BattlefieldUserComponent` вызывает
    `setBattle` + `sendNotification` и `clear` + `sendNotification` парами
    (`BattlefieldUserComponent.java:48-49, 53-54`). Переход "вошёл в бой/вышел из боя" стоит
    сделать методами владельца, которые сами шлют уведомление.
15. **Лог боя растёт без ограничения** (`Battle.java:271`) и в реальном времени тоже, хотя там он
    никому не отдаётся: 10-минутный бой Battlefield держит в памяти все события. Недействительные
    события урона пишутся в лог как `null`.
16. **Один `BattleResultEvent` после конца** исполняется тиком позже, и в этом тике юниты ещё
    стреляют (`Battle.java:297-300`); на победителя не влияет, но клиент, остановивший бой сразу,
    покажет на тик меньше событий.
17. **Правила ГДД, которых нет в коде (отложено пользователем 2026-10-17).** По [battle-gdd.md](/workspace/client/.claude/docs/game-design/battle-gdd.md):
    броня самолёта и тип пулемётов, ±25% урона ([#gdd-armor-guns](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-armor-guns)); манёвренность
    и шанс промаха пулемёта ([#gdd-maneuverability](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-maneuverability)); время взлёта (2 вида) и
    время полёта бомбы как параметры самолёта ([#gdd-airplane-params](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-airplane-params)).
    В коде это константы 5000/1500 (`Fighter.update`, `UnitAirplane.stateHandling`) и 5500
    (`UnitAirplane.attackTank`), а `armorType`, `gunType`, `bombDelay` не читаются (см. п.8).
    Изменение любого из них меняет исход пересимуляции и должно повторяться на клиенте
    ([#determinism](#determinism)).
18. **`LINE`-бомба по живым линиям (отложено 2026-10-17).** ГДД ([#gdd-bomb](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-bomb)) выбирает
    линию только из тех, где есть живые танки; код — любую, где стоит хоть один танк (п.6). Правка
    добавит условие выбора линии и сдвинет последовательность RNG на клиенте.
19. **Детерминизм client↔server Д1–Д5** описан в клиентском
    [battle-architecture.md#tradeoffs](/workspace/client/.claude/docs/battle-architecture.md#tradeoffs)
    (замена танка только на клиенте, ничья, точность урона, бонус урона, туториальные параметры). Здесь
    пересекаются с п.1, 2, 16 и [#client-divergence](#client-divergence). Оставлены без изменений,
    разберёт `integration-lead`.
20. **Решения "как в коде" (не расхождения).** ТЗ предлагает параметр задержки до сброса бомбы, но принято как в коде:
    бомба сбрасывается по своей перезарядке; окно события отдельное у каждой стороны
    ([#gdd-event-window](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-event-window), записи в журнале ГДД 2026-10-17). Слот ТЗ N — позиция
    `8 − N`.

21. **`getAnyOpponent` дублирует `initOpponent`** (после merge). Одно правило под двумя именами;
    `initOpponent` вызывается при инициализации бойца, `getAnyOpponent` — при подведении итога 1vs1.
    Предложение: оставить одну; переименование — решение пользователя.
22. **Рейтинговый бой и детерминизм.** Движок не менялся (шаги тика, RNG, формулы те же), изменения в
    `Battle`/`BattleData`/`BattleFighterData` — только вспомогательные методы и поля рейтинга;
    пересимуляция не затронута. Туториальной ветки бота больше нет: клиентские туториальные параметры
    (Д5 из п.19) серверной стороной не подкрепляются.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД боя: [battle-gdd.md](/workspace/client/.claude/docs/game-design/battle-gdd.md) — по ТЗ, цель. Слот ТЗ N = позиция `8 − N`. Смежные разделы других ГДД:
[campaign-gdd.md#gdd-battlefield](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-battlefield),
[#gdd-enemy-tanks](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-enemy-tanks),
[#gdd-enemy-airplanes](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-enemy-airplanes),
[#gdd-defeat](/workspace/client/.claude/docs/game-design/campaign-gdd.md#gdd-defeat).

Правило ГДД → функция. Строки без ссылки — правила наземного боя, их в ГДД ещё нет (кандидаты):

| Правило | Функция |
|---|---|
| Ход боя, шаг 16 мс, воспроизводимость по seed ([#gdd-purpose](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-purpose)) | `Battle.update`, `BattleRandom` |
| Начальная пара и смена противника | `Battle.initOpponent`, `Battle.getOpponent`, `Fighter.update` |
| Поражение бойца, только танки ([#gdd-battle-end](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-battle-end)) | `Fighter.isAlive/isDestroyed` |
| Места и победитель ([#gdd-battle-end](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-battle-end)) | `Battle.update` (места), `getSortedAlive` |
| Жизненный цикл и появление танка | `UnitTank.init`, `UnitTank.stateHandling` |
| Выбор цели танком | `UnitTank.getTarget` |
| Выстрел танка, промах 5% | `UnitTank.attackTank` |
| Урон по танку, снаряд/броня, блок, износ брони | `TankTakeDamageEvent.fromTank`, `BattleBalance` |
| Скорострельность самолётов ([#gdd-airplane-params](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-airplane-params)); танков — нет в ГДД | `TankRecharge.update`, `AirplaneRecharge.update` |
| Очередь взлёта самолётов ([aerodrome-gdd.md#gdd-takeoff-order](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-takeoff-order)) | `Fighter.update` (взлёт), `UnitAirplane.prepareTakeoff/clearanceTakeoff` |
| Жизненный цикл самолёта ([#gdd-air-combat](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-combat), [#gdd-air-positions](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-positions)) | `UnitAirplane.stateHandling` |
| Выбор воздушной цели ([#gdd-air-target](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-target)) | `UnitAirplane.getTargetAirplane` |
| Пулемёт по самолётам ([#gdd-air-combat](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-air-combat)) | `UnitAirplane.attackAirplane`, `AirplaneTakeDamageEvent` |
| Бомбы SOLO/LINE/MASS ([#gdd-bomb](/workspace/client/.claude/docs/game-design/battle-gdd.md#gdd-bomb)) | `UnitAirplane.getTargetTanks`, `attackTank`, `TankTakeDamageEvent.fromAirplane` |
| Уворот и смена противника игроком (Battlefield) | `DodgeEvent`, `ChangeOpponentEvent`, отмена по хэшу |

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от корня репозитория `/workspace/server`.

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/battle/Battle.java` | бой: тик, события, места, победитель, рассылка |
| `game/src/main/java/com/linkedgames/game/model/battle/Fighter.java` | боец: противник, взлёт самолётов, действия |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleUnit.java` | база юнита |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitTank.java` | танк в бою |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitAirplane.java` | самолёт в бою |
| `game/src/main/java/com/linkedgames/game/model/battle/recharge/TankRecharge.java` | перезарядка танка |
| `game/src/main/java/com/linkedgames/game/model/battle/recharge/AirplaneRecharge.java` | перезарядка пулемёта/бомб |
| `game/src/main/java/com/linkedgames/game/model/battle/recharge/RechargeMode.java` | режимы перезарядки |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleRandom.java` | PRNG xorshift32 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleBalance.java` | модификатор снаряд/броня |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleEvent.java` | база события, id событий |
| `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankAttackEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankDestroyedEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankRechargeEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankReplacedEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankSpawnEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankTakeDamageEvent.java` | события танков |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneAttackEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneDestroyedEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplanePrepareTakeoffEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneRechargeEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneReplacedEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneSpawnEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneTakeDamageEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneTakeoffEvent.java` | события самолётов |
| `game/src/main/java/com/linkedgames/game/model/battle/events/BattlePlaceEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/BattleResultEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/ChangeOpponentEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/DodgeEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/ForceEndEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/NewOpponentEvent.java`, `game/src/main/java/com/linkedgames/game/model/battle/events/SlotResultEvent.java` | общие события |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleData.java` | входные данные боя, seed |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleFighterData.java`, `game/src/main/java/com/linkedgames/game/model/battle/data/BattleTankData.java`, `game/src/main/java/com/linkedgames/game/model/battle/data/BattleAirplaneData.java` | данные бойца и юнитов |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleDataFactory.java` | сборка бойцов и ботов |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleType.java`, `game/src/main/java/com/linkedgames/game/model/battle/BattleLocation.java` | тип боя, место боя |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleUserComponent.java` | текущий бой реального времени у игрока |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleActor.java`, `game/src/main/java/com/linkedgames/game/model/battle/BattleActorPolicy.java` | актёр боя реального времени |
| `game/src/main/java/com/linkedgames/game/model/battle/actions/IAction.java`, `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionInfo.java`, `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionSubscribe.java`, `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionChangeOpponent.java`, `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionDodge.java` | действия игрока |
| `game/src/main/java/com/linkedgames/game/service/battle/BattleStore.java` | хранилище актёров боёв |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BattlePage.java` | роуты `/ingame/battle` |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignBattle.java`, `game/src/main/java/com/linkedgames/game/model/campaign/CampaignFighter.java` | бой кампании (режим `AUTO`) |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` | `createBattle`/`createRankedBattle`/`completeBattle` — пересимуляция |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` | `/battleResult` — победитель эмуляции, dev-лог |
| `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldBattle.java`, `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldFighter.java` | бой реального времени (`INSTANT`, бонус урона, слоты, боты) |
| `game/src/main/java/com/linkedgames/game/model/battlefield/actions/ActionSlot.java` | действие `/charge` |
| `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldUserComponent.java` | ставит/сбрасывает бой в `BattleUserComponent` |
| `game/src/main/java/com/linkedgames/game/service/battlefield/battle/League.java` | создаёт бой Battlefield, `StopBattleMessage` |
| `game/src/main/java/com/linkedgames/game/service/battlefield/BattlefieldActor.java` | приём мест и итога боя |
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | `getBattleUserComponent`, `createTeam`, поле `Battle` в документе |
| `game/src/main/java/com/linkedgames/game/Globals.java` | остановка `BattleStore` |
| `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` | регистрация `/ingame/battle` |
| `game/src/main/java/com/linkedgames/game/model/notifications/NotificationId.java` | `BATTLE_INFO_ID` |
| `game/src/main/java/com/linkedgames/game/model/team/Team.java`, `game/src/main/java/com/linkedgames/game/model/team/TeamMembers.java` | зависимость: команда и порядок позиций |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/Tank.java`, `game/src/main/java/com/linkedgames/game/model/bag/tank/TankParams.java`, `game/src/main/java/com/linkedgames/game/model/bag/tank/TankAmmoType.java`, `game/src/main/java/com/linkedgames/game/model/bag/tank/TankArmorType.java`, `game/src/main/java/com/linkedgames/game/model/bag/tank/TankType.java` | зависимость: параметры танка |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/Airplane.java`, `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneParams.java`, `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneBombType.java`, `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneType.java` | зависимость: параметры самолёта |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignBattleResult.java` | итог боя кампании (обычный/рейтинговый), оболочка над `Battle` |
| `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeActor.java`, `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeService.java`, `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeBattleContext.java` | рейтинговый бой кампании (PvP), потребитель движка; здесь не документируется |
| `game/src/main/resources/balance.json` | листы `Tanks`/`Airplanes` — параметры юнитов |
