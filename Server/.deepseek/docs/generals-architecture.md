# Генералы и Ставка армии — архитектура сервера

**Статус:** черновик (`server-analyst-generals`, 2026-11-06); полная документация — после разработки.
**ГДД:** `/workspace/client/.deepseek/docs/game-design/generals-gdd.md` (одна копия на обе стороны).
**Клиент:** `/workspace/client/.deepseek/docs/generals-architecture.md`.

**Содержание:** [Назначение](#purpose) · [Паттерны](#patterns) · [Модель данных](#model) ·
[Слоты, навыки и баланс](#slots) · [Бонусы в бою](#bonus) · [Награды лутбокса](#rewards) · [Контракт](#contract) ·
[Решения и компромиссы](#decisions) · [Открытые вопросы](#open) · [Что переиспользовать](#reuse) ·
[Карта файлов](#files)

<a id="purpose"></a>
## 1. Назначение

Генерал как предмет сумки, слоты должностей и ручная замена, выдача генерала и умения из лутбокса, бонусы
урона и прочности технике своей нации и древа. Правила бизнес-логики — только в ГДД; здесь — как это
разложено по коду.

<a id="patterns"></a>
## 2. Паттерны и референсы

- `reward-roll-pattern.md` — реестр наград «один тип на выбор»; раздел 4 прямо описывает генерала и умение.
- `refusal-with-state-pattern.md` — отказ с возвратом актуального состояния.
- `hangar-architecture.md`, `HangarUserComponent.getReplaceableTank/addTank` — образец замены слота.
- `lootbox-architecture.md` — образец `*UserComponent` с ячейками, персистентностью и страницей.

<a id="model"></a>
## 3. Модель данных

```
model/bag/general/General             extends BagItem   генерал-предмет: нация, должность, качество, звёзды, умения
    Stars stars                                         1..5 звёзд, 10 качеств — множитель base-навыков
    GeneralSkill[] skills                               additional-навыки, 0..2: по одному на параметр
model/generals/GeneralsUserComponent  extends UserChildComponent implements APIResponseStd
    Map<Integer, ObjectId> slots                        ключ — slotKey «ordinal должности × 10 + индекс слота»,
                                                        значение — uid генерала в сумке
model/generals/GeneralPosition        enum: 8 должностей: древо + индексы слотов (1 у командной, 0..3 у Штаба)
model/generals/GeneralTree            enum: TANK, AIRPLANE — древо техники
model/generals/GeneralInfluenceParam  enum: DAMAGE, ARMOR — параметр и одновременно слот умения
model/generals/GeneralInfluence       enum: 22 типа влияния (древо + параметр + объект), разбор ячейки баланса
model/generals/GeneralSkillAcquisition enum: BASE, ADDITIONAL — как навык попадает к генералу
model/generals/GeneralSkill           умение генерала: id навыка + звёзды; процент = величина + шаги звёзд
model/generals/data/GeneralData       строка листа Generals
model/generals/data/GeneralSkillData  строка листа GeneralSkills
model/generals/data/GeneralsData      справочник экрана, розыгрыши, validate
model/lootbox/data/GeneralReward      награда «генерал»
model/lootbox/data/AbilityReward      награда «умение»
```

- Качество — существующий `Rank`, звёзды — существующий `Stars`: новых перечислений качества и звёзд не
  заводим. Шансы качества — `GeneralsData.RANK_CHANCES` (заглушка), звёзды выдаёт механизм поезда
  (`rollStars`).
- Отдельного поля слота у генерала нет: он вычисляется из баланса — `General.getSlotIndex()` берёт тип
  техники из влияния base-навыка (`GeneralInfluence.getTankType` / `getAirplaneType`), `General.getSlotKey()`
  отдаёт `GeneralPosition.toSlotKey`.

<a id="slots"></a>
## 4. Слоты, навыки и баланс

Слота касаются три метода у владельца `GeneralsUserComponent`: `place(General)` — поставить генерала из
сумки в слот своей должности (сила не сравнивается, прежний в занятом слоте остаётся в сумке, серебра никто
не получает), `remove(int slotKey)` — снять со слота (генерал остаётся в сумке), `sell(General)` — списать из
сумки и начислить серебро по цене танка.

- Слот определяется должностью генерала и, у Штаба, типом техники; нация не учитывается — в слот встаёт
  любой генерал своей должности (ГДД `gdd-slots`).
- Свободный слот заполняется сразу, без окна сравнения. Занятый — ответ отдаёт `receivedGeneral` и
  `slotGeneral`, решение за игроком: «В слот» (`place`) или «Продать» (`sell`); закрытие окна ничего не
  меняет, выпавший уже лежит в сумке.
- Автопродажи нет: `REPLACE_SILVER` в компоненте отсутствует, серебро начисляется только в `sell`.
- Повтор запроса не выдаёт награду дважды — разыгранный генерал попадает в сумку один раз
  (`#idempotent-ops`).

**Страница.** `GeneralsPage` (`pages/ws/ingame/GeneralsPage.java`), маршрут `/ingame/generals` в `WSRouter`:

| Путь | Что делает | Ответ |
|---|---|---|
| `""` | состав Ставки и инвентарь генералов | `generals`, `inventory` |
| `/info` | справочники экрана: должности со слотами и таблица навыков | `positions`, `skills` |
| `/assign` | поставить генерала по `uid` в слот его должности, без сравнения силы | `generals`, `inventory` |
| `/remove` | снять генерала со слота (`position`, `slot`), генерал остаётся в инвентаре | `generals`, `inventory` |
| `/sell` | продать генерала из инвентаря (`uid`), начислить серебро | `generals`, `inventory`, `sold` |

Отказ любого действия — ошибка с тем же свежим состоянием: клиент перерисовывается по данным сервера
(`refusal-with-state-pattern.md`).

**Навыки и умения.** Строка листа `GeneralSkills` — навык; у генерала он либо **base** (характеристика,
активна сразу, слотов не занимает), либо **additional** (умение, выпадает из сундука). Разделение задаёт
баланс: строка генерала задаёт только base-навыки (`baseSkillIds`), набор additional-навыков ею не ограничен
(ГДД `gdd-abilities`).

- `GeneralsData.getBaseSkills` — навыки из строки генерала; процент base-навыка `General.getBasePercent(...)`
  = величина из баланса × множитель звёзд (таблица `Stars`, шкала 10000 = 1,00).
- `GeneralSkill.getPercent()` = величина навыка + 0,1 % от неё за каждый шаг звёзд; `getSteps()` = (качество −
  1) × 5 + число звёзд, максимум 50.
- `General.getAbility(param)` — занятый слот умения, `General.applyAbility(skill)` — положить умение в слот
  своего параметра: пустой сразу, занятый — сравнивается только навык того же типа влияния, остаётся больший
  по проценту, остальное уходит в серебро. Base-навыки замена не затрагивает.
- `General.getPower()` — сила: сумма процентов base-навыков (по ней сравнивает клиент);
  `getPercent(influence)` — итог по типу влияния (base + additional), `getParamPercent(param)` — итог по
  параметру для своего древа (цифры «+N %» на карточке).
- Создание генерала из баланса — `General.createFromData(...)`.

Лист `GeneralSkills` (`GeneralSkillData`):

| Индекс | Колонка | Значение |
|---|---|---|
| 0 | `Id` | идентификатор навыка |
| 1 | `Type` | ordinal `GeneralSkillAcquisition`: 0 — Base, 1 — Additional |
| 2 | `TypeName` | `Base` / `Additional` (приоритет над `Type`) |
| 3 | `ImpactTechType` | ordinal `GeneralTree`: 0 — TANK |
| 4 | `ImpactTechType` | имя древа `TANK` / `AIRPLANE` (приоритет над ordinal) |
| 5 | `ImpactTechSpecType` | ordinal `TankType` / `AirplaneType`; `-1` — вся техника древа |
| 6 | `ImpactTechSpecTypeName` | название типа техники (`Все`, `Легкий`, …) — не читается |
| 7 | `ImpactType` | ordinal `GeneralInfluenceParam`: 0 — DAMAGE, 1 — ARMOR |
| 8 | `ImpactTypeName` | `DAMAGE_INCREASE` / `ARMOR_INCREASE` (приоритет над ordinal) |
| 9 | `ImpactValue` | величина влияния, %; дробная часть с запятой (`4,0000`) |
| 10 | `SilverPrice` | цена продажи умения, серебро; колонки нет → 10 |
| 11 | `Chance` | вес выпадения умения; колонки нет → 1 (навыки равновероятны) |

`ImpactTechType` — на какую технику действует бонус (древо), `ImpactType` — сам параметр (урон или
прочность); пары 3/4 и 7/8 — ordinal и имя одного параметра, имя приоритетнее. Тип влияния собирается из трёх
колонок — древа (3/4), объекта (5) и параметра (7/8) — `GeneralInfluence.of(...)`. Названия навыка в таблице
нет: подпись собирает клиент из типа влияния и `value`.

Лист `Generals` (`GeneralData`):

| Индекс | Колонка | Значение |
|---|---|---|
| 0 | `id` | идентификатор генерала |
| 1 | `Name` | имя и фамилия |
| 2 | `Rank` | качество: номер 1–10 либо название (`Обычное` … `Высшее`) |
| 3 | `Type` | ordinal `GeneralPosition` |
| 4 | `Type Name` | название должности — не читается |
| 5 | `Country` | ordinal `Country` |
| 6 | `Country Code` | код нации (`USSR`) — не читается |
| 7 | `SkillsId` | не читается: набор additional-навыков строкой не ограничен |
| 8 | `BaseSkills` | base-навыки: характеристики генерала |

- Названия качества в `Rank` (`GeneralData.readRank`) переводятся по порядку строк блока «нация + должность»:
  `Обычное` — I, `Необычное` — II, `Редкое` — III, `Эпическое` — IV, `Легендарное` — V, `Мифическое` — VI,
  `Титаническое` — VII, `Высшее` — VIII. Принимаются только ранги I–X: качеств ровно 10, значение вне шкалы
  останавливает импорт с адресной ошибкой.
- Ячейка навыков: вложенный массив (`["1","2"]`), строка через запятую (`"1,2"`) или в фигурных скобках
  (`"{1,6}"`); пустая — генерал без навыков.
- `GeneralsData.validate()` (из `Globals.preload`) проверяет, что base-навыки строки есть в таблице, имеют тип
  получения Base и древо влияния совпадает с древом должности. Штаб без base-навыка нужного типа (слот не
  вычисляется) — предупреждение в лог, а не остановка: в таблице у всех генералов заглушки `{1,6}`.

**Розыгрыш.** `rollRank()` — качество по `RANK_CHANCES` (заглушка); `rollGeneral(rank)` — генерал этого
качества; `rollAbilitySkill()` — additional-навык по `chance`; `getAbilityCandidates(user, skillData)` —
генералы инвентаря того же древа, что и навык; `hasAdditionalSkills()` — есть ли в таблице additional-навык с
весом (вариант участвует в броске сундука); `rollStars(TrainUserComponent)` — звёзды механизмом поезда.

**Таблица баланса.** Оба листа обязательны, как и остальные: отсутствие листа в `balance.json` валит
`Balance.build` с именем листа (`JSONObject["Generals"] is not a JSONArray`), а отказ таблицы на импорте
приходит с телом ответа Google Sheets, где назван нераспознанный диапазон. Доступ: `getGeneralData(id)`,
`generalIsAvailable(id)`, `getGenerals(rank)`, `getGenerals()`, `getSkillData(id)`, `getSkills()`.

<a id="bonus"></a>
## 5. Бонусы в бою

Множитель применяется в `User.createTeam()`; `TankParams` и `AirplaneParams` не трогаем (решение Пользователя
2026-11-06):

```java
final Tank tankCopy = (Tank) tank.copy();
tankCopy.setUid(tank.getUid());
getGeneralsUserComponent().applyBonus(tankCopy);   // умножает hp и damage копии
team.add(position, tankCopy);
```

- `applyBonus` берёт итоговый процент нации техники и увеличивает копию: танк — `params.damage` и `params.hp`,
  самолёт — `params.gunDamage`, `params.bombDamage` (урон) и `params.hp` (прочность). Оригинал в сумке
  остаётся с базовыми параметрами — ангар показывает базовые.
- Складываются влияния «вся техника древа» и влияния конкретного типа техники; нация генерала должна
  совпадать с нацией техники, танковые должности идут к танкам, авиационные — к авиации (ГДД `gdd-summary`).
- Округление — `Math.round`, как в `TankParams.recalculate`.
- Боты (`createBotTeam`) идут мимо `createTeam`, генералов у них нет — правило их не затрагивает.

<a id="rewards"></a>
## 6. Награды лутбокса

Бросок и выдача разделены: `LootboxReward.roll(User)` возвращает `RolledReward` (предмет либо умение с
генералом), выдача — `addTo(User, RolledReward)`. Результат броска передаётся в выдачу, чтобы отказ на
списании валюты в `speedupAndOpen` не терял награду. `LootboxReward.isAvailable(User)` фильтрует варианты до
броска — `LootboxQualityData.rollRewardType(User)`.

| Класс | `roll(User)` | `addTo(User, RolledReward)` | Особенность |
|---|---|---|---|
| `GeneralReward` | качество по `GeneralsData.rollRank()`, генерал своего качества, звёзды механизмом поезда | `user.addItem`, затем `generals.place`, если слот свободен | ответ `receivedGeneral` + `slotGeneral` (`null` — слот был свободен); занятый слот — окно сравнения у клиента, автоматически ничего не продаётся (`gdd-slots`) |
| `AbilityReward` | любой additional-навык по `chance` → случайный получатель среди генералов инвентаря своего древа → звёзды | `General.applyAbility`; проигравшее умение — в серебро; получателя нет — навык сразу в серебро | `isAvailable` = в листе есть additional-навык с весом: умение выпадает всегда, без подходящего генерала уходит в серебро (`gdd-ability-drop`) |

`AbilityReward.addTo` отдаёт попапу «Было/Стало» одинаковый набор ключей в любом исходе: `sold` (навык продан
без присвоения), `general` (карточка после изменения), `before` (`power`, `damagePercent`, `armorPercent` до),
`ability` (выпавшее умение), `applied` (встало ли выпавшее), `soldSkill` (что ушло в серебро, `null` — потерь
нет) и `silver`. Получателя не нашлось — `general`, `before` и `soldSkill` равны `null`, `sold` = true,
`applied` = false.

- Вариант «генерал» участвует в броске, только когда лист `Generals` заполнен (`isAvailable` = справочник не
  пуст): до заполнения баланса сундуки генералов не выдают.
- Валюта — `ItemId.RESOURCE_SILVER_COINS`: за проданного игроком генерала (`GeneralsUserComponent.sell`) и за
  умение, ушедшее в серебро (`GeneralSkillData.silverPrice`). Замена генерала в слоте серебра не даёт —
  прежний остаётся в сумке (ГДД `gdd-slots`).
- «Призыв» из списка наград — существующий ресурс `ItemId.RESOURCE_TANK_SCHEME` (решение Пользователя
  2026-11-06): отдельного варианта награды под него не нужно, уходит штатным путём ресурса в счётчик схем у
  поезда.
- **Dev-выдача.** `DevToolsPage`: `/generalDrop` выдаёт генерала, `/abilityDrop` — умение; оба используют те же
  классы наград, поэтому повторяют поведение сундука.

<a id="contract"></a>
## 7. Контракт

`ItemType.GENERAL` — новое значение **в конец** enum (ordinal = поле `t` в БД) + регистрация в `ItemFactory`
(`General::new`): без регистрации сохранённый предмет не восстановится. Ответ
`GeneralsUserComponent.apiResponse()` дополняет существующий ответ пользователя; отдельные типы под справочник
должностей и генералов заводятся один раз и переиспользуются страницей и попапами.

- Карточка генерала (`General.apiResponse()`): `uid`, `id`, `generalId`, `name`, `country`, `position`,
  `slot`, `tree`, `rank`, `stars`, `power`, `damagePercent`, `armorPercent`, `baseSkills` (`skillId`,
  `influence`, `percent`) и `skills` — additional-умения (`skillId`, `influence`, `stars`, `steps`, `percent`).
- Справочник `/info` (`GeneralsData.apiResponse()`): `positions` (`ordinal`, `airplane`, `slots`) и `skills`
  (`id`, `acquisition`, `influence`, `value`, `silverPrice`).
- Награды сундука: у ресурса — `itemType`, `id`, `min`, `max`; у генерала — `itemType`, `receivedGeneral`,
  `slotGeneral`; у умения — `ability` (признак варианта в справочнике) и поля `AbilityReward.addTo` выше.

<a id="decisions"></a>
## 8. Решения и компромиссы

Правила бизнес-логики — в ГДД (`gdd-slots`, `gdd-abilities`, `gdd-summary`); здесь только то, что определяет
код.

- Бонусы — множитель в `createTeam()`, `TankParams` и `AirplaneParams` не трогаем.
- Звёзды генералов и умений — временно механизм звёзд танков (10 рангов); отдельный механизм появится позже.
- Генерал и умение — `BagItem` и награды лутбокса; шансы качества, звёзд и умений — заглушки в балансе.
- Вход на страницу генералов — временная dev-кнопка на главном экране.
- Наций в таблице 8, а `Country` в коде содержит 10 значений: лишние в генералах не участвуют.
- Листы `Generals` и `GeneralSkills` обязательные, как остальной баланс: отсутствующий или пустой лист
  останавливает сборку баланса (решение Пользователя 2026-11-09; «необязательных» листов в балансе нет —
  см. `CLAUDE.md`, «Баланс всегда считается верным»).

<a id="open"></a>
## 9. Открытые вопросы

- Числа баланса: величины влияния навыков и формула пересчёта величины в бонус к технике; колонок `SilverPrice`
  и `Chance` в таблице нет, поэтому пока 10 и 1.
- `Rank` в живом листе вне шкалы: в блоке Главкома встречаются 11, 13, 15 и повтор 9, две строки смещены —
  импорт останавливается адресной ошибкой, нужна правка таблицы к рангам I–X.
- У всех генералов base-навыки — заглушки `{1,6}`, поэтому слот Штаба не вычисляется: ждёт реальных
  `BaseSkills` по должностям.
- В листе навыков 88 base-строк, но всего 9 разных типов влияния: 80 строк повторяют «Лёгкий танк, урон» с
  величиной 0, отсутствует «Лёгкий танк, прочность»; у 12 additional-навыков величина 0. Дубли на логику не
  влияют (дублируют вес), ждут чисел баланса.
- Звёзды умения разыгрываются механизмом поезда (10 рангов), а по ГДД у additional-навыка 1–5 звёзд — нужен ли
  отдельный розыгрыш.
- `GeneralPosition.AIR_FORCE_STAFF` имеет 4 слота (0–3), а `AirplaneType` — 5 значений: слот стратегического
  бомбардировщика (ordinal 4) не входит ни в один слот. Нужно решение: пятый слот или общий слот на два типа.

<a id="reuse"></a>
## 10. Что переиспользовать, что не трогать

**Переиспользовать.** `HangarUserComponent.getReplaceableTank/addTank` — образец единого метода-перехода у
владельца (замена слота у генералов ручная, образец не копируется); `LootboxUserComponent` — образец
`*UserComponent` с персистентностью одним `changedField`, `apiResponse` и регистрацией в `User`;
`DropUtils.RollDrop` + `DroppedItem` — бросок (свои циклы не добавлять); готовые `Rank`, `Stars`,
`ItemId.RESOURCE_SILVER_COINS`, `UserEmitterId`.

**Не трогать.** `TankParams` / `AirplaneParams` — бонус применяется снаружи (решение Пользователя); правила
открытия и ускорения сундуков — область лутбоксов; движок боя — только `createTeam` через `applyBonus`.

<a id="files"></a>
## 11. Карта файлов

**Файлы прямого влияния**

| Файл | Роль |
|---|---|
| `model/bag/general/General.java` | предмет сумки: base/additional-навыки, `getPower`, `getPercent`, `applyAbility` |
| `model/generals/GeneralsUserComponent.java` | слоты, `place`, `remove`, `sell`, `applyBonus`, `apiResponse` |
| `model/generals/GeneralPosition.java` | enum должностей: древо и индексы слотов, `toSlotKey`/`bySlotKey` |
| `model/generals/GeneralTree.java` | enum древа: танки / авиация |
| `model/generals/GeneralInfluenceParam.java` | enum параметра и слота умения: урон / прочность |
| `model/generals/GeneralInfluence.java` | 22 типа влияния, разбор ячейки баланса |
| `model/generals/GeneralSkillAcquisition.java` | тип получения навыка: Base / Additional |
| `model/generals/GeneralSkill.java` | умение генерала: id навыка, звёзды, процент |
| `model/generals/data/GeneralData.java` | строка листа `Generals` |
| `model/generals/data/GeneralSkillData.java` | строка листа `GeneralSkills` |
| `model/generals/data/GeneralsData.java` | справочник, розыгрыши, `validate` |
| `model/lootbox/data/GeneralReward.java` | награда «генерал» |
| `model/lootbox/data/AbilityReward.java` | награда «умение» |
| `model/lootbox/data/RolledReward.java` (+`RolledItemReward`, `RolledAbilityReward`) | результат броска награды |
| `pages/ws/ingame/GeneralsPage.java` | страница: состав, инвентарь, установка, снятие, продажа |

**Файлы косвенного влияния**

| Файл | Роль |
|---|---|
| `model/item/ItemType.java` | `GENERAL` в конец enum |
| `model/item/ItemFactory.java` | регистрация `General::new` |
| `balance/Balance.java` | загрузка листов `Generals`/`GeneralSkills` (`optionalArray`), геттеры выборки |
| `balance/BalanceImporter.java` | оба листа в списке импортируемых |
| `Globals.java` | `GeneralsData.validate()` при старте |
| `model/user/User.java` | геттер `getGeneralsUserComponent`, `createTeam` + `applyBonus` |
| `pages/WSRouter.java` | маршрут `/ingame/generals` |
| `pages/ws/ingame/dev/DevToolsPage.java` | dev-выдача генерала (`/generalDrop`) и умения (`/abilityDrop`) |
| `model/lootbox/data/LootboxReward.java` | контракт наград: `roll(User)`, `isAvailable`, `addTo` |
| `model/lootbox/data/LootboxData.java` | регистрация наград и веса (заглушки) |
| `model/lootbox/data/LootboxQualityData.java` | бросок варианта с фильтром доступности |
| `model/lootbox/LootboxUserComponent.java` | открытие сундука: бросок до списания, выдача после |
