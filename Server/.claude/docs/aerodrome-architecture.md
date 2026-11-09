# Аэродром — `AerodromeUserComponent` (сервер)

> Документ составлен `server-analyst-lead` по коду, 2026-10-15; обновлён 2026-10-17 (ссылки на ГДД,
> решения пользователя); актуализирован 2026-10-19 под merge `origin/amnesia/fix` (призыв и
> радиовышка ушли в военную базу). Подтверждено чтением кода, запуском не проверялось.
> Клиентскую сторону разбирает `client-analyst-lead`; здесь клиент упомянут только для списка роутов.

ГДД: [aerodrome-gdd.md](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md). ГДД описывает
призыв, радиовышку, покупку схем, автопризыв и доступ по уровню кампании, которых в коде аэродрома
больше нет ([#tradeoffs](#tradeoffs) п.1, [#gdd-link](#gdd-link)).

Аэродром теперь хранит только расстановку самолётов по 8 позициям. Призыв самолёта, прогресс
(уровень и опыт) и выбор «принять/продать» выполняет военная база (`MilitaryBaseUserComponent`,
`MilitaryBaseAviationFactory`, `MilitaryBasePage`), эта область в документ не входит; здесь она
только ссылкой. Поезд — [train-architecture.md](train-architecture.md). Воздушный бой в документ не входит.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`AerodromeUserComponent`](#cls-aerodromeusercomponent)
   - [`AerodromeSummonData`](#cls-aerodromesummondata)
   - [`AerodromeBuySchemesData`](#cls-aerodromebuyschemesdata)
   - [`AerodromePage`](#cls-aerodromepage)
   - [`CleanupAerodrome` и миграция](#cls-cleanupaerodrome)
   - [Регистрация и персистентность](#persistence)
   - [Потребители состояния аэродрома](#consumers)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Аэродром держит расстановку самолётов по 8 позициям: для самолётов он выполняет роль, которую для
танков выполняет ангар (`HangarUserComponent`). Самолёты лежат в сумке ([bag-architecture.md](bag-architecture.md)),
компонент хранит `uid` по позициям.

Правила по коду:

- Позиции по типам ([gdd-slots](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-slots), `AirplaneType.TYPE_POSITION`): 0 — стратегический бомбардировщик, 1 —
  бомбардировщик, 2–3 — штурмовики, 4–7 — истребители и тяжёлые истребители.
- Постановка ([`addAirplane`](#m-addairplane)): самолёт встаёт на первую пустую позицию своего типа; если все
  позиции типа заняты, заменяется самый слабый по `getPower` ([`getReplaceableAirplane`](#m-getreplaceableairplane)),
  заменённый удаляется из сумки.
- Цена продажи самолёта — 10 серебра ([`getSilverCoinsReward`](#m-getsilvercoinsreward)).

Откуда приходят самолёты (правила — в документах этих областей):

- Военная база: самолёт производит `MilitaryBaseAviationFactory.generateAirplane` (шансы рангов и
  звёзд — листы `SummonRankChances`/`SummonStarsRankChances`, количество звёзд — [`AerodromeSummonData.getRandomStars`](#cls-aerodromesummondata)),
  принятие и продажу выполняет `MilitaryBasePage` (`/acceptAirplane`, `/refuseAirplane`, `/checkFactory`,
  `/runFactory`; роуты зарегистрированы как `/ingame/military_base` и `/ingame/militaryBase`);
  уровень фабрики растёт по листу `SummonUpgrade` (`SummonUpgradeData`).
- Сборка: награда-самолёт через `addAirplane` ([assembly-architecture.md](assembly-architecture.md)).

Схем самолёта (`ItemId.RESOURCE_AIRPLANE_SCHEME`) код больше не выдаёт и не тратит: стартовый набор
5 схем убран из `TrainUserComponent.initStarter`, роутов покупки и dev-выдачи нет ([#tradeoffs](#tradeoffs) п.2).

Сами самолёты лежат в сумке как `Airplane` ([bag-architecture.md#cls-tank-airplane](bag-architecture.md#cls-tank-airplane)),
балансовые данные моделей — `AirplaneData`
([tank-airplane-data-architecture.md#class-airplanedata](tank-airplane-data-architecture.md#class-airplanedata)).
Запись в кодекс при производстве — [codex-architecture.md#producers](codex-architecture.md#producers).

<a id="references"></a>
## 2. Референсы

Расстановка по позициям (`getReplaceableAirplane`, `addAirplane`, `getEmptyPosition`,
`getCurrentPosition`) — копия `HangarUserComponent` для танков. `AerodromeBuySchemesData` — копия
`TrainBuySchemesData`.

<a id="patterns"></a>
## 3. Паттерны

`UserChildComponent` в документе игрока ([train-architecture.md#patterns](train-architecture.md#patterns)).

Своё у аэродрома:

- **Слоты по ссылке.** Компонент хранит не сами самолёты, а `uid` экземпляров из сумки по
  позициям (`Map<Integer, ObjectId>`); самолёт читается через `BagUserComponent.getAirplane(uid)`.
- **Внутреннее событие изменения состава** — `UserEmitterId.AERODROME_UPDATE` после `addAirplane`;
  слушает `BattlefieldUserComponent` (пересчёт команды). Клиенту не отправляется.

<a id="class-list"></a>
## 4. Список классов

Пакет `com.linkedgames.game.model.aerodrome`: `AerodromeUserComponent` (с вложенным `DBFields`),
`data.AerodromeSummonData`, `data.AerodromeBuySchemesData`.
Страница: `com.linkedgames.game.pages.ws.ingame.AerodromePage` (один роут).
Скрипт: `com.linkedgames.game.scripts.CleanupAerodrome` + миграция `1757403378113_cleanup_aerodrome.json`.
Удалены при merge: `AerodromeUpgradeData`, роуты `/summon`, `/accept`, `/refuse`, `/autoData`,
`/upgradeData`, `/buySchemesData`, `/buySchemes`, dev-роуты `/aerodromeAddLevel`, `/aerodromeRemoveLevel`,
`/aerodromeAddSchemes`, листы `AerodromeUpgrade`/`AerodromeSummon`/`AerodromeSummonStars`.

<a id="anchors"></a>
## 5. Навигация (якоря)

| Якорь | Что там |
|---|---|
| `#cls-aerodromeusercomponent` | поля, методы компонента |
| `#m-addairplane` | постановка самолёта на позицию, замена |
| `#m-getreplaceableairplane` | выбор заменяемого самолёта |
| `#m-getsilvercoinsreward` | цена продажи |
| `#cls-aerodromesummondata` | шансы количества звёзд |
| `#cls-aerodromebuyschemesdata` | наборы схем самолёта (нет вызовов) |
| `#cls-aerodromepage` | роут `/ingame/aerodrome` |
| `#cls-cleanupaerodrome` | скрипт чистки самолётов |
| `#persistence` | регистрация в `User`, ключи БД |
| `#consumers` | кто читает позиции |
| `#client-contract` | JSON ответов, роуты клиента |
| `#tradeoffs` | баги, дубли, компромиссы |

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `AerodromeUserComponent`, `AerodromeUserComponent.DBFields` | [#cls-aerodromeusercomponent](#cls-aerodromeusercomponent), [#persistence](#persistence) |
| `AerodromeSummonData` | [#cls-aerodromesummondata](#cls-aerodromesummondata) |
| `AerodromeBuySchemesData` | [#cls-aerodromebuyschemesdata](#cls-aerodromebuyschemesdata) |
| `AerodromePage` | [#cls-aerodromepage](#cls-aerodromepage) |
| `CleanupAerodrome` | [#cls-cleanupaerodrome](#cls-cleanupaerodrome) |

## 7. Классы и методы

<a id="cls-aerodromeusercomponent"></a>
### `AerodromeUserComponent`

`UserChildComponent`, `APIResponseStd`. ГДД: [gdd-slots](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-slots). Имя компонента `"Aerodrome"`, создаётся лениво в
`User.getAerodromeComponent()`.

Поля: `airplanes` (позиция 0–7 → `uid` самолёта в сумке). Константа `POSITIONS = 8` (private).
Уровня радиовышки, опыта, выпавшего самолёта (`receivedAirplane`) и `ACCESS_CAMPAIGN_LEVEL` в компоненте нет.

<a id="m-getreplaceableairplane"></a>
**`getReplaceableAirplane(Airplane): Airplane`** ([gdd-slots](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-slots)) — самый слабый (`getPower`) самолёт среди позиций
типа нового самолёта. Возвращает `null`, если хотя бы одна позиция типа пуста или её `uid` не найден
в сумке. Зовут `MilitaryBasePage` (`/checkFactory`, `/acceptAirplane`) и `addAirplane`.

<a id="m-addairplane"></a>
**`addAirplane(Airplane)`** ([gdd-slots](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-slots)) — ставит самолёт на позицию.
1. Позиция — первая пустая позиция типа (`getEmptyPosition`).
2. Есть заменяемый — позиция заменяемого, ему `addCount(-1)` (удаление из сумки).
3. Позиция так и не найдена (`-1`) — позиция 0 ([#tradeoffs](#tradeoffs) п.3).
4. `BagUserComponent.add(airplane)`, `uid` из результата пишется в позицию, `changedField("arp")`,
   `emit(AERODROME_UPDATE)`.
Серебро за заменённый самолёт не начисляет — это делает вызывающий. Вызывают `MilitaryBasePage /acceptAirplane`
и `AssemblyUserComponent.takeAirplaneReward`.

<a id="m-getsilvercoinsreward"></a>
**`getSilverCoinsReward(Airplane)`** — цена продажи самолёта: 10 при `airplane != null`, иначе 0;
характеристики не учитывает. Зовут `MilitaryBasePage /acceptAirplane` (за заменённый) и `/refuseAirplane` (за выпавший).

**JSON:**
- `apiResponse()` — `{airplanes: [{position, airplaneUid|null}] ×8}` (поля `radioTower` больше нет).
- `getFullAirplanesJSON()` — `[{position, airplane: Airplane.apiResponse()|null}] ×8`, для профиля.

**`dbMappingBuild(Document)`** — читает только `arp` (ключ-строка позиции → `ObjectId`).

Тривиальные: `getAirplaneUid(position)`, `getCurrentPosition(Airplane)` (позиция по `uid` или −1),
`getEmptyPosition` (private), `dbAirplanesChanged` (private), `getAirplanesJSON` (private),
`modifyReceiver` (пустой).

<a id="cls-aerodromesummondata"></a>
### `AerodromeSummonData`

- `getRandomStars()` — количество звёзд нового самолёта по весам `1→30, 2→25, 3→20, 4→15, 5→10`
  (из 100), от уровня не зависит. Единственный вызов — `MilitaryBaseAviationFactory.generateAirplane`.
- `getAirplaneToSilverCoins(int)` — всегда 10, нигде не вызывается ([#tradeoffs](#tradeoffs) п.6).

<a id="cls-aerodromebuyschemesdata"></a>
### `AerodromeBuySchemesData`

`LIST: ImmutableMap<id, data>` — наборы схем самолёта: `id`, `airplaneSchemes`, `bonus`,
`priceGoldenCoins`; `apiResponse()`. Наборы: 25 за 500, 150 за 3000, 500 за 10000 золота, `bonus` 0.
Вызовов в коде нет: роутов покупки нет ([#tradeoffs](#tradeoffs) п.2).

<a id="cls-aerodromepage"></a>
### `AerodromePage` (`/ingame/aerodrome`)

`AuthorizedUserPage`, регистрация в `WSRouter`. Единственный роут `""` — `{aerodrome: apiResponse()}`.
Роуты призыва, принятия, продажи, автопризыва, окна прокачки и покупки схем удалены; призыв самолётов
теперь в `MilitaryBasePage` (см. [#purpose](#purpose)). Dev-роутов аэродрома в `DevToolsPage` нет.

<a id="cls-cleanupaerodrome"></a>
### `CleanupAerodrome` и миграция

Разовый скрипт (`AbstractScript`), запускается миграцией
`game/src/main/resources/migrations/1757403378113_cleanup_aerodrome.json`. Для каждого игрока с
поддокументом `Aerodrome` удаляет из коллекции `bag` все самолёты (`t == ItemType.AIRPLANE`), чьих
`uid` нет на позициях аэродрома. Читает `AerodromeUserComponent.DBFields.AIRPLANES_FIELD` (поэтому
ключ `public`).

<a id="persistence"></a>
### Регистрация и персистентность

- `User`: поле `aerodrome`, `getAerodromeComponent()`, `modifyReceiver`, загрузка поддокумента
  `Aerodrome` (`User.DBFields.P_AERODROME_FIELD`) в `dbMappingBuild`, если ключ есть.
- `AerodromeUserComponent.DBFields`: `arp` — позиции (`{"0": ObjectId, …}`, пишется целиком при каждом
  изменении). Ключи `l`, `exp`, `rca` закомментированы в `DBFields` и не читаются; у существующих игроков
  они остаются в БД ([#tradeoffs](#tradeoffs) п.4).
- Стартового состояния нет: позиции пусты, пока игрок не примет первый самолёт.

<a id="consumers"></a>
### Потребители состояния аэродрома

- `User.createTeam()` — самолёты позиций 0–7 в команду боя (воздушный бой — отдельный анализ).
- `User.profileOverview` — `getFullAirplanesJSON()` в профиле другого игрока.
- `BattlefieldPage ""` — `aerodrome.apiResponse()`.
- `BattlefieldUserComponent` — слушает `AERODROME_UPDATE`.
- `AssemblyUserComponent.takeAirplaneReward` — ставит самолёт-награду через `addAirplane`.
- `MilitaryBasePage` — `getReplaceableAirplane`, `addAirplane`, `getSilverCoinsReward`.
- `HomePage` больше не отдаёт `radioTower`.

<a id="client-contract"></a>
### Контракт с клиентом

Схемы, серебро и самолёты клиент получает push-ом сумки
([bag-architecture.md#client-contract](bag-architecture.md#client-contract)). По `/ingame/aerodrome`
остался только `""`; клиентские вызовы `/summon`, `/accept`, `/refuse`, `/autoData`, `/upgradeData`,
`/buySchemesData`, `/buySchemes` и поле `radioTower` в ответах серверу неизвестны. Сверку с клиентом
(`AerodromePopup` и др.) делает `integration-lead`.
<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Статусы: баг — исправить; отложено — решение пользователя отложить; решение — так задумано по ГДД;
как в коде — ГДД молчит, поведение не менялось. Приоритет — предложение аналитика.

**Решения пользователя, действующие после merge:**
- 2026-10-16: замена и продажа самолёта в квест продажи не идут ([gdd-summon](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved)); `MilitaryBasePage /acceptAirplane` квеста продажи не даёт.

Решения 2026-10-15 про `/refuse` при свободной позиции и раздельные правила аэродрома и поезда относились
к удалённым роутам и таблицам; их судьба зависит от ответа на вопрос о ГДД.

1. **ГДД расходится с кодом.** Статус: открыто (вопрос пользователю). Призыв, радиовышка
   ([gdd-radio-tower-level](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved)), покупка схем, автопризыв, доступ по уровню кампании
   ([gdd-access](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved)) в аэродроме не реализованы: перенесены в военную базу или удалены.
2. **Схемы самолёта без источника и стока.** Статус: открыто. `RESOURCE_AIRPLANE_SCHEME` нигде не
   выдаётся и не тратится; остатки в сумках игроков лежат без применения. `AerodromeBuySchemesData` без вызовов.
3. **Самолёт любого типа может встать на позицию 0.** Статус: баг, приоритет высокий. `addAirplane`
   (`AerodromeUserComponent.java:61-79`): если все позиции типа заняты, но один `uid` не найден в
   сумке, `getReplaceableAirplane` возвращает `null`, `getEmptyPosition` — `−1`, и самолёт пишется
   на позицию 0 (стратегический бомбардировщик), затирая её. Нарушает [gdd-slots](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-slots). Тот же код в
   `HangarUserComponent.addTank`.
4. **Старые ключи БД `l`, `exp`, `rca` остаются в `Aerodrome`**, миграции удаления нет. Невыданный
   `rca` (выпавший, непринятый самолёт) у игрока не обработан: самолёт и его запись в кодекс остаются
   только в БД. Статус: открыто, приоритет средний (решение пользователя: миграция или оставить).
5. **Переходы состояния собраны в `MilitaryBasePage`** (WF `#no-implicit-order`). Статус: как в коде,
   приоритет средний. «Принять» = серебро + квест `SILVER_COINS_GAINED` + `addAirplane` +
   `clearReceivedAirplane` у слота + `increaseAirplaneFactoryExp` + квест `BETTER_AIRPLANE`
   (`MilitaryBasePage.java:600-657`); «продать» — серебро + квест + очистка слота + опыт фабрики
   (`:659-707`). Метод-переход у владельца — вопрос области военной базы.
6. **Кандидаты на удаление**: `AerodromeSummonData.getAirplaneToSilverCoins` (не вызывается),
   `AerodromeBuySchemesData` целиком, пустой `modifyReceiver`, закомментированные константы в `DBFields`.
   Статус: как в коде, приоритет низкий.
7. **Имя `getSilverCoinsReward(Airplane)`** — цена продажи самолёта, имя говорит о награде. Статус: как в коде,
   приоритет низкий; переименование — отдельный этап. `AerodromeSummonData.getRandomStars` теперь
   относится к производству самолёта на военной базе, но лежит в пакете аэродрома.
8. **`getAirplanes(rank)` без проверки на `null`/пустоту** в `MilitaryBaseAviationFactory.generateAirplane`:
   нет самолётов выпавшего ранга — NPE или `IllegalArgumentException`
   ([tank-airplane-data-architecture.md#tradeoffs](tank-airplane-data-architecture.md#tradeoffs) п.5).
   Статус: баг, приоритет высокий (область военной базы).
9. **Число позиций задано дважды**: `POSITIONS = 8` (private) и литерал `8` в `User.createTeam`
   (`User.java:359`). Статус: как в коде, приоритет низкий.
10. **Результат `BagUserComponent.add` не проверяется** в `addAirplane` после удаления заменяемого —
    [bag-architecture.md#tradeoffs](bag-architecture.md#tradeoffs) п.7. Статус: баг-риск, приоритет низкий.
11. **Кодекс пишется до решения игрока** (`MilitaryBasePage /runFactory`): проданный самолёт тоже попадает
    в кодекс ([codex-architecture.md#producers](codex-architecture.md#producers)). Статус: как в коде, приоритет низкий.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД области — [aerodrome-gdd.md](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md) (после merge не менялся). Правило → реализация:

| Правило ГДД | Где реализовано |
|---|---|
| [gdd-purpose](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-purpose) — назначение, прогресс радиовышки | расстановка — `AerodromeUserComponent`; радиовышки нет, прогресс — уровень фабрики в военной базе |
| [gdd-access](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved) — доступ с 5-го уровня кампании | не реализовано (константа удалена) |
| [gdd-slots](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-slots) — 8 слотов по классам, замена слабейшего, 10 серебра | `addAirplane`, `getReplaceableAirplane`, `getEmptyPosition`, `getSilverCoinsReward`; вызывающий — `MilitaryBasePage /acceptAirplane` |
| [gdd-summon](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved) — призыв за схему, решение игрока | перенесено: `MilitaryBasePage` (без схем, за доллары/золото) |
| [gdd-radio-tower-level](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved) — пороги, перенос опыта, окно улучшения | перенесено: `increaseAirplaneFactoryExp`, лист `SummonUpgrade`; окна улучшения аэродрома нет |
| [gdd-auto-summon](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved) — шансы для автопризыва | не реализовано (`/autoData` удалён) |
| [gdd-buy-schemes](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-base-moved) — наборы схем за золото | не реализовано (`AerodromeBuySchemesData` без вызовов) |
| [gdd-takeoff-order](/workspace/client/.claude/docs/game-design/aerodrome-gdd.md#gdd-takeoff-order) — очерёдность взлёта | вне области (воздушный бой); позиции читает `User.createTeam` |
| [bag-gdd.md#gdd-starter](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-starter) — 5 схем самолёта новому игроку | не реализовано (убрано из `TrainUserComponent.initStarter`) |
| [bag-gdd.md#gdd-vehicles](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-vehicles) — замена удаляет технику насовсем | `addAirplane` (`addCount(-1)`), `CleanupAerodrome` |

<a id="file-map"></a>
## 10. Карта файлов компонента

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/aerodrome/AerodromeUserComponent.java` | компонент: позиции самолётов |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/data/AerodromeSummonData.java` | шансы количества звёзд (зовёт военная база) |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/data/AerodromeBuySchemesData.java` | наборы схем самолёта (без вызовов) |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AerodromePage.java` | роут `/ingame/aerodrome` `""` |
| `game/src/main/java/com/linkedgames/game/scripts/CleanupAerodrome.java` | разовая чистка самолётов вне позиций |
| `game/src/main/resources/migrations/1757403378113_cleanup_aerodrome.json` | миграция, запускающая `CleanupAerodrome` |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | поле и геттер компонента, загрузка `Aerodrome`, `modifyReceiver`, `createTeam`, `profileOverview` |
| `game/src/main/java/com/linkedgames/game/model/user/UserEmitterId.java` | событие `AERODROME_UPDATE` |
| `game/src/main/java/com/linkedgames/game/pages/WSRouter.java` | регистрация `/ingame/aerodrome` и `/ingame/military_base`, `/ingame/militaryBase` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/MilitaryBasePage.java` | призыв, принятие, продажа самолёта (область военной базы, ссылка) |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseAviationFactory.java` | `generateAirplane`, вызывает `AerodromeSummonData.getRandomStars` (область военной базы, ссылка) |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseUserComponent.java` | `increaseAirplaneFactoryExp`, уровень фабрики (ссылка) |
| `game/src/main/java/com/linkedgames/game/model/summon/data/SummonUpgradeData.java` | строка листа `SummonUpgrade` (общий Summon, ссылка) |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BattlefieldPage.java` | `aerodrome` в ответе боевого поля |
| `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldUserComponent.java` | слушает `AERODROME_UPDATE` |
| `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` | `addAirplane` для самолёта-награды сборки |
| `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` | `initStarter` (схемы самолёта убраны) |
| `game/src/main/java/com/linkedgames/game/model/codex/CodexUserComponent.java` | запись произведённого самолёта в кодекс |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestEvent.java` | события `AERODROME_SUMMON`, `BETTER_AIRPLANE` (шлёт `MilitaryBasePage`) |
| `game/src/main/java/com/linkedgames/game/model/hangar/HangarUserComponent.java` | образец расстановки по позициям (копия логики) |
| `game/src/main/java/com/linkedgames/game/model/bag/BagUserComponent.java` | зависимость: хранение самолётов, серебра |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/Airplane.java` | зависимость: `getPower` |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneType.java` | зависимость: `TYPE_POSITION` — позиции по типу |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/data/AirplaneData.java` | зависимость: модели самолётов, `type` |
| `game/src/main/java/com/linkedgames/game/model/bag/utils/ItemAddInfo.java` | зависимость: результат `add` в `addAirplane` |
| `game/src/main/java/com/linkedgames/game/model/item/ItemId.java` | зависимость: `RESOURCE_AIRPLANE_SCHEME` (без использования) |
| `game/src/main/java/com/linkedgames/game/model/item/ItemType.java` | зависимость: `AIRPLANE` в `CleanupAerodrome` |
| `game/src/main/java/com/linkedgames/game/dao/BagDao.java` | зависимость: имя коллекции в `CleanupAerodrome` |
| `game/src/main/java/com/linkedgames/game/model/user/UserChildComponent.java` | зависимость: базовый класс компонента |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AuthorizedUserPage.java` | зависимость: базовый класс страницы |
| `game/src/main/java/com/linkedgames/game/scripts/AbstractScript.java` | зависимость: базовый класс скрипта |
| `commons/src/main/java/com/linkedgames/commons/rnd/RandomJdk.java` | зависимость: количество звёзд |
