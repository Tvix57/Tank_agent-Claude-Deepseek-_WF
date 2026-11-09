# Генералы и Ставка армии — архитектура сервера

**Статус:** черновик архитектуры (`server-analyst-generals`, 2026-11-06). Полная документация по
стандарту делается после разработки, один раз.
**ГДД:** `/workspace/client/.claude/docs/game-design/generals-gdd.md` (одна копия на обе стороны; в
страховочной раскладке — `/workspace/client/.deepseek/docs/game-design/generals-gdd.md`).

**Содержание:** [Назначение](#purpose) · [Области и агенты](#areas) · [Использованные паттерны](#patterns) ·
[Модель данных](#model) · [Слоты и замена](#slots) · [Бонусы в бою](#bonus) · [Награды лутбокса](#rewards) ·
[Контракт](#contract) · [Решения пользователя](#decisions) · [Открытые вопросы](#open) ·
[Что переиспользовать](#reuse) · [Карта файлов](#files)

<a id="purpose"></a>
## 1. Назначение

Серверная часть фичи «Генералы и Ставка армии»: генерал как предмет сумки, назначение на должности,
автоматическая замена по общему проценту параметров, выдача генерала и умения из лутбокса, бонусы урона
и прочности технике своей нации.

Правила бизнес-логики — только в ГДД; здесь — как это раскладывается по коду.

<a id="areas"></a>
## 2. Затронутые области и агенты

| Область | Агент | Что делает в этой задаче |
|---|---|---|
| Генералы (новая) | `server-analyst-generals` / `server-developer-generals` | вся фича целиком |
| Лутбоксы | `server-analyst-lootbox` / `server-developer-lootbox` | новые виды награды в реестре `LootboxReward` |
| Сумка | `server-analyst-bag` | регистрация нового `ItemType` и `ItemFactory` |
| Ангар | `server-analyst-hangar` | эталон замены слота, править не нужно |
| Бой | `server-analyst-battle` | точка применения бонусов в `User.createTeam()` |

<a id="patterns"></a>
## 3. Использованные паттерны

- `reward-roll-pattern.md` — реестр наград «один тип на выбор»; раздел 4 «Добавление нового типа
  награды» прямо описывает генерала и умение.
- `refusal-with-state-pattern.md` — отказ с возвратом актуального состояния.
- `hangar-architecture.md` + `HangarUserComponent.getReplaceableTank/addTank` — образец замены слота и
  единый метод-переход.
- `lootbox-architecture.md` — образец `*UserComponent` с ячейками, персистентностью и страницей.

<a id="model"></a>
## 4. Модель данных

```
model/bag/general/General          extends BagItem
    int nationOrdinal              нация (Country), фиксирована
    int positionOrdinal            должность (GeneralPosition), фиксирована
    int generalId                  идентификатор записи справочника (имя + качество)
    Stars stars                    1..5 звёзд, 10 качеств
    GeneralAbility[] abilities     0..2 умения

model/generals/GeneralsUserComponent   extends UserChildComponent implements APIResponseStd
    Map<String, ObjectId> slots    ключ — «должность:слот» (у Штаба 4 слота: TT/PT/ST/LT),
                                   значение — uid генерала в сумке

model/generals/GeneralPosition     enum: 8 должностей, у каждой группа (танковая/авиационная),
                                   цель бонуса (прочность / урон / оба) и число слотов
                                   (1 для командных, 4 для Штаба по типам техники)
model/generals/GeneralAbility      умение: тип (связь — урон, логистика — прочность), звёзды
model/generals/data/GeneralData        справочник генерала: нация, должность, имя, качество
model/generals/data/GeneralPositionData бонус и лимит по должности
model/generals/data/GeneralRollData     шансы качества и звёзд по качеству сундука (заглушки)
```

Качество генерала — существующий `Rank`, звёзды — существующий `Stars`: новых перечислений качества и
звёзд не заводим (ГДД `gdd-quality`, `gdd-stars`).

<a id="slots"></a>
## 5. Слоты и замена

Один метод-переход у владельца, по образцу `HangarUserComponent.addTank`:

```java
public boolean assign(General general) {
    if (general == null) return false;
    final String slotKey = general.getSlotKey();   // должность + слот типа техники у Штаба
    final ObjectId currentUid = slots.get(slotKey);
    final General current = currentUid == null ? null : user().getBagComponent().getGeneral(currentUid);
    if (current == null) {
        final ItemAddInfo addInfo = user().getBagComponent().add(general);
        if (!addInfo.success || addInfo.item == null) return false;
        slots.put(slotKey, addInfo.item.getUid());
    } else {
        if (general.getTotalPercent() <= current.getTotalPercent()) {
            current.addCount(-1);
            return true;
        }
        current.addCount(-1);
        user().getBagComponent().addResource(ItemId.SILVER, 10);
        final ItemAddInfo addInfo = user().getBagComponent().add(general);
        if (!addInfo.success || addInfo.item == null) return false;
        slots.put(slotKey, addInfo.item.getUid());
    }
    dbSlotsChanged();
    user().getEventEmitter().emit(UserEmitterId.GENERALS_UPDATE);
    return true;
}
```

Правила, зашитые в этот метод (ссылки — на ГДД):
- замена только по своей должности и слоту типа техники (`gdd-slots`);
- нация кандидата при сравнении не учитывается — в слот встаёт лучший, откуда бы он ни был
  (`gdd-slots`);
- сравнение по общему проценту `getTotalPercent()` = качество + звёзды + умения (`gdd-summary`);
- заменённый генерал уходит, за него 10 серебра по цене танка (`gdd-slots`);
- повтор запроса не выдаёт генерала дважды: состояние слота — в том же методе (правило
  `#idempotent-ops`).

`getTotalPercent()` живёт у `General` — расчёт процента одно правило ГДД, одна функция.

**Страница.** `GeneralsPage` (`pages/ws/ingame/GeneralsPage.java`), маршрут `/ingame/generals` в `WSRouter`:

| Путь | Что делает | Ответ |
|---|---|---|
`""` | текущий состав Ставки и инвентарь генералов | `generals`, `inventory` |
`/info` | справочники экрана: должности со слотами и таблица навыков | `positions`, `skills` |
`/assign` | поставить генерала в слот (по `uid`); при занятом слоте — замена, если `isBetter` | `generals`, `inventory` |
`/remove` | снять генерала со слота (`position`, `slot`) | `generals`, `inventory` |
`/sell` | продать генерала из инвентаря (`uid`), серебро начисляется | `generals`, `inventory`, `sold` |

- Отказ любого действия отдаётся ошибкой с тем же свежим состоянием, клиент перерисовывается по данным
  сервера.
- `assign`, `remove`, `sell` — методы у `GeneralsUserComponent`: смена слота, списание и начисление
  серебра в одном методе у владельца, повтор запроса не выдаёт генерала дважды.

**Навыки.** Навык — отдельная сущность генерала: `GeneralSkill` (id навыка из баланса + звёзды и
качество звёзд), массив `skills` в `General`. Набор навыков генерала задаётся списком `skillIds` в его
строке баланса — генерал не может получить навык, которого нет в его `skillIds`. Процент навыка =
шаги звёзд × `percentPerStar` (шаг — `(ordinal качества − 1) × 5 + число звёзд`). Общий процент
генерала `getTotalPercent()` = качество + звёзды + сумма навыков по типам; по нему работает `isBetter`.
Создание генерала из баланса — `General.createFromData(...)`.

Лист `GeneralSkills` в балансе, `GeneralSkillData`:

| Индекс | Поле | Значение |
|---|---|---|
| 0 | `id` | идентификатор навыка |
| 1 | `name` | название («Рота связи», «Рота логистики») |
| 2 | `type` | ordinal `GeneralSkillType` (0 — урон, 1 — прочность) |
| 3 | `percentPerStar` | процент за шаг |
| 4 | `maxStars` | предел шагов |
| 5 | `silverPrice` | цена при замене навыка, серебро |
| 6 | `chance` | шанс выпадения навыка |

Выпадение навыка — `GeneralsData.rollSkill()` взвешенно по `chance`.

**Шансы.** `GeneralsData` держит мапу «ранг → шанс в процентах» по рангам I–X (сейчас заглушка —
по 10 %). Звёзды генерала (качество и количество) выдаются механизмом поезда:
`GeneralsData.rollStars(TrainUserComponent)` → `TrainUserComponent.rollStarsRank()` /
`rollStarsCount()`, те же методы использует выдача танка из поезда.

**Таблица баланса.** Лист `Generals` рядом с `Tanks`, формат — массив строк по индексам:

| Индекс | Поле | Значение |
|---|---|---|
| 0 | `id` | идентификатор генерала |
| 1 | `name` | имя и фамилия |
| 2 | `country` | ordinal `Country` |
| 3 | `position` | ordinal `GeneralPosition` |
| 4 | `rank` | ordinal `Rank` (качество, I–X) |
| 5 | `damagePercent` | прибавка к урону, % |
| 6 | `durabilityPercent` | прибавка к прочности, % |
| 7 | `skillIds` | массив id навыков этого генерала из листа `GeneralSkills` |

Ячейка `skillIds` принимается в двух видах: вложенный массив (`["1","2"]`) или строка через запятую
(`"1,2"`); пустая ячейка — генерал без навыков. Навыки генерала — только те, что перечислены в его
строке: `GeneralsData.getGeneralSkills(generalData)`. Выпавшее умение выбирается среди них и только если
у генерала ещё нет этого навыка — `GeneralsData.rollGeneralSkill(general)`.

- Загрузка — `GeneralData.build(JSONArray)` по образцу `TankData.build`, через тот же `mapping` в
  `Balance.build`; лист добавлен в `SHEETS` у `BalanceImporter`, поэтому приходит из таблицы вместе с
  остальными.
- Лист читается как **необязательный** (`optionalArray` → `optJSONArray`): пока листа в таблице нет,
  загрузка баланса проходит, `getGenerals()` пуст. Остальные листы остаются обязательными —
  отсутствие `Tanks` по-прежнему ошибка.
- Доступ: `getGeneralData(id)`, `generalIsAvailable(id)`, `getGenerals(rank)`, `getGenerals()`.
  Выбор выпавшего генерала своего качества — `GeneralsData.rollGeneral(rank)`.

<a id="bonus"></a>
## 6. Бонусы в бою

Решение пользователя 2026-11-06: множитель применяется в `User.createTeam()`, `TankParams` и
`AirplaneParams` не трогаем.

```java
public Team createTeam() {
    ...
    final Tank tankCopy = (Tank) tank.copy();
    tankCopy.setUid(tank.getUid());
    getGeneralsUserComponent().applyBonus(tankCopy);   // умножает hp и damage копии
    team.add(position, tankCopy);
}
```

- `applyBonus` берёт итоговый процент нации танка и увеличивает `params.hp` и `params.damage` копии;
  оригинал в сумке остаётся с базовыми параметрами (ангар показывает базовые).
- Боты (`createBotTeam`) идут мимо `createTeam`, генералов у них нет — правило не затрагивает.
- Итог по нации: танковые должности — к танкам, авиационные — к авиации (ГДД `gdd-summary`).
- Округление — `Math.round`, как в `TankParams.recalculate`.

<a id="rewards"></a>
## 7. Награды лутбокса

Две новые реализации `LootboxReward`:

| Класс | `roll()` | `addTo(User, Item)` | Особенность |
|---|---|---|---|
| `GeneralReward` | генерал по шансам качества сундука | `user.getBagComponent()` + `generalsComponent.assign` | качество и звёзды разыгрываются по `GeneralRollData` |
| `AbilityReward` | умение существующему генералу | обновляет умение у генерала в сумке | **вариант фильтруется до броска**: нет генерала — вариант недоступен |

Умение без адресата не выпадает (ГДД `gdd-ability-drop`): список вариантов для броска строится из
генералов игрока, поэтому пустой список — вариант исключается из реестра для этого открытия.

«Призыв» из списка наград — существующий ресурс `ItemId.RESOURCE_TANK_SCHEME` (решение пользователя
2026-11-06): отдельного варианта награды под него заводить не нужно, уходит штатным путём ресурса в
счётчик схем у поезда.

Валюта за заменённое умение и генерала — `ItemId.SILVER` по цене танка.

<a id="contract"></a>
## 8. Контракт

`ItemType.GENERAL` — новое значение **в конец** enum (ordinal = поле `t` в БД) + регистрация в
`ItemFactory` (`General::new`). Без регистрации сохранённый предмет не восстановится.

Ответ `GeneralsUserComponent.apiResponse()` дополняет существующий ответ пользователя; отдельные типы
под справочник должностей и генералов заводятся один раз и переиспользуются страницей и попапами.

<a id="decisions"></a>
## 9. Решения пользователя (2026-11-06)

1. Нации — 8: СССР, Великобритания, Франция, США, Китай, Германия, Италия, Япония. В коде `Country`
   содержит 10 значений — лишние не участвуют в таблице генералов.
2. Должности: **8, все активны сразу** (4 танковых + 4 авиационных). Слотов в дереве Ставки — **11**:
   1 + 1 + 1 + 4 в танковой ветке (4 слота — у Штаба танковых войск, по типу техники) и 4 слота
   Штаба авиационных войск.
3. Слоты: `GeneralsUserComponent`, по одному слоту на должность (у Штаба — 4, по типу техники), замена
   автоматическая. Слот **не привязан к нации**: в него встаёт генерал любой страны.
4. Бонусы: множитель в `User.createTeam()`, `TankParams` не трогаем.
5. Звёзды генералов — временно механизм звёзд как у танков.
6. Генерал и умение — награды лутбокса, наследуют `BagItem`.
7. Шансы качества/звёзд генерала и качества умений — временные заглушки.
8. Вход на страницу генералов — временная dev-кнопка на главном экране.

<a id="open"></a>
## 10. Открытые вопросы

- «Лучшее» умение при автозамене, если сравниваются умения разных типов.
- Пример и уточнение расчёта замены генерала (в исходнике — «написать пример и уточнение»).
- Числа баланса: бонусы по должностям, таблица генералов (560 на тип), шансы.

Закрыто 2026-11-06: «призыв» в списке наград сундука — это схема танка
(`ItemId.RESOURCE_TANK_SCHEME`), отдельного ресурса нет.

<a id="reuse"></a>
## 11. Что переиспользовать, что не трогать

**Переиспользовать**
- `HangarUserComponent.getReplaceableTank/addTank` — образец структуры замены и единого метода-перехода.
- `LootboxUserComponent` — образец `*UserComponent`: персистентность одним `changedField`, `apiResponse`,
  регистрация в `User`.
- `DropUtils.RollDrop` + `DroppedItem` — бросок, свои циклы не добавлять.
- `Rank`, `Stars`, `ItemId.SILVER`, `UserEmitterId` — существующие типы.

**Не трогать**
- `TankParams` / `AirplaneParams` — решение пользователя: бонус снаружи.
- Правила открытия и ускорения сундуков — область лутбоксов.
- Движок боя — только `createTeam` через `applyBonus`.

<a id="files"></a>
## 12. Карта файлов (планируемая)

| Файл | Роль |
|---|---|
| `model/bag/general/General.java` | предмет сумки, `getTotalPercent()` |
| `model/generals/GeneralsUserComponent.java` | слоты, `assign`, `applyBonus`, `apiResponse` |
| `model/generals/GeneralPosition.java` | enum должностей |
| `model/generals/GeneralAbility.java` | умение и его звёзды |
| `model/generals/data/GeneralData.java` | запись листа `Generals` баланса (id, имя, нация, должность, качество, проценты) |
| `model/generals/data/GeneralPositionData.java` | бонус и лимит по должности |
| `model/generals/data/GeneralRollData.java` | шансы (заглушки) |
| `model/lootbox/data/GeneralReward.java` | награда «генерал» |
| `model/lootbox/data/AbilityReward.java` | награда «умение» |
| `model/item/ItemType.java` | `GENERAL` в конец enum |
| `model/item/ItemFactory.java` | регистрация `General::new` |
| `balance/Balance.java` | загрузка листа `Generals`, геттеры выборки |
| `balance/BalanceImporter.java` | лист `Generals` в списке импортируемых |
| `model/user/User.java` | геттер `getGeneralsUserComponent`, `createTeam` + `applyBonus` |
| `model/generals/GeneralSkill.java` | навык генерала: id из баланса + звёзды и качество звёзд |
| `model/generals/GeneralSkillType.java` | тип навыка: урон / прочность |
| `model/generals/data/GeneralSkillData.java` | запись листа `GeneralSkills` |
| `pages/ws/ingame/GeneralsPage.java` | страница: состав, инвентарь, установка, снятие, продажа |
| `pages/WSRouter.java` | маршрут страницы |
| `pages/ws/ingame/dev/DevToolsPage.java` | dev-выдача генерала |
