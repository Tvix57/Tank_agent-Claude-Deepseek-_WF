# Паттерн: реестр наград «один тип на выбор, количество по качеству»

**auto-create** (по коду ветки `koba/lootbox`, 2026-10-27). Паттерн собран из существующих кусков
кода; сам реестр в коде ещё не существует, первый потребитель — лутбоксы.

ГДД: отсутствует. Исходник ТЗ — `/workspace/client/.claude/docs/game-design/incoming/lootbox-source.md`
(ГДД лутбоксов `lootbox-gdd.md` ещё не создан).

<a id="toc"></a>
## Оглавление

[Назначение](#purpose) · [Строительные блоки в коде](#building-blocks) · [Схема паттерна](#scheme) ·
[Добавление нового типа награды](#new-reward-type) · [Находки анализа](#findings) ·
[Открытые решения](#open-decisions) · [Карта файлов](#file-map)

<a id="purpose"></a>
## 1. Назначение

Источник награды с качеством (лутбокс, в будущем любой сундук) отдаёт за одно открытие ровно один тип
награды. Тип выбирается взвешенным броском из списка, разрешённого для этого качества. Количество
берётся случайно из диапазона `[min, max]`, который тоже зависит от качества. Типом может быть ресурс
(золото, серебро, схемы танка), техника (танк) или будущий предмет (генерал), и новый тип добавляется
без правки самого броска.

Из ТЗ: «Из лутбокса может упасть только один из типов наград за раз»; окно подтверждения показывает
все возможные типы и диапазоны («Золото 20 - 500», «схемы поезда 3 - 15», «Умение», «Генерал»).
Значит, реестр должен уметь отдавать клиенту описание содержимого без броска.

Частичные аналоги в документации: [airdrop `#balance`](airdrop-architecture.md#balance) (качество →
диапазон золота, один тип награды), [assembly `#m-generatereward`](assembly-architecture.md#m-generatereward)
(генерация танка с рангом и звёздами), [collections `#roll-section`](collections-architecture.md#roll-section)
(взвешенный выбор из кандидатов с промахом).

<a id="building-blocks"></a>
## 2. Строительные блоки в коде

| Блок | Где | Что даёт паттерну |
|---|---|---|
| `DropUtils.RollDrop(List<DroppedItem<T>>, maxChance)` | `service/drop` | Обобщённый взвешенный бросок. `maxChance = 0` — шкала равна сумме весов, промаха нет; `maxChance > 0` — сумма весов меньше шкалы даёт `null` (промах). Бросок `nextIntInclusive(1, maxChance)`, веса целые. |
| `DroppedItem<T>` | `service/drop` | Пара «значение + целый вес». `T` может быть чем угодно, в том числе генератором награды. |
| `Item` / `ItemType` / `ItemFactory` | `model/item` | Общая модель предмета (`id`, `count`), сериализация `apiResponse()` `{id, itemType, count}` и `dbToData()`/`newFromDocument` для хранения невыданной награды ([bag `#cls-item`](bag-architecture.md#cls-item)). |
| `Resource.createNew(id, isTemplate)` + `setCount` | `model/bag/resource` | Ресурс любого вида по `ItemId`; количество — `count`. Шаблон (`isTemplate = true`) годится для предпросмотра, в сумку не кладётся как есть ([bag `#cls-resource`](bag-architecture.md#cls-resource)). |
| `Tank.createNew(data, isTemplate)` + `setLevel` + `setStars(rank, count)` + `recalculateParams()` | `model/bag/tank` | Танк заданного ранга и звёзд; так же делают поезд и сборка ([assembly `#m-generatereward`](assembly-architecture.md#m-generatereward), шаги 4–6). |
| `Balance.getTanks(rank)` | `balance` | Кандидаты танков ранга. |
| `User.addItem(item, AnalyticsSubjectId)` | `model/user` | Единая точка выдачи: `BagItem` идёт в `BagUserComponent.add`, с `subjectId` пишется аналитика. Не-`BagItem` молча игнорируется. |
| `OfferRewardData` | `model/offers` | Пример неизменяемого набора наград (`ImmutableList<Item>`) через `Builder`. Сам по себе не выбирает, выдаёт всё. |
| `BoostSummonData.getInfoJSON()` | `model/military_base/data` | Пример отдачи клиенту таблицы шансов без броска (`[{rank, chance}]`). |
| `AirDropBoxType` / `AirDropBox.getReward()` | `model/campaign/data` | Пример «качество → диапазон количества»: `nextIntInclusive(min, max)`. |

Качество: в коде нет отдельного перечисления качества. Роль «качества» играет `Rank` (`I`…`XX`) со
списками `TANK_STARS`, `MILITARY_BASE_BOOSTS` и т.п. по 10 значений; у airDrop — свой `AirDropBoxType`
(6 цветов). Выбор для лутбокса — [открытое решение 2](#open-decisions).

<a id="scheme"></a>
## 3. Схема паттерна

Черновик, имена условные: окончательные даёт разработка по скиллу `naming`.

1. **Реестр** — по одной записи на качество источника. Запись — список вариантов
   `DroppedItem<RewardEntry>`, где вес = шанс типа награды при этом качестве.
2. **`RewardEntry`** — вариант награды одного типа. Знает свой диапазон для качества и умеет:
   - `roll()` — создать конкретный `Item` (ресурс с `count` из `[min, max]`, танк выбранного ранга
     и т.д.);
   - `infoJSON()` — описание для окна предпросмотра (тип, `min`, `max` или только тип, как у «Генерал»
     в ТЗ).
3. **Бросок** — `DropUtils.RollDrop(entries)` с `maxChance = 0`: всегда ровно один тип, промаха нет
   (правило «только один из типов за раз»). Своя функция броска не пишется ([находка 1](#findings)).
4. **Хранение результата** — выпавший `Item` сохраняется у владельца источника через `dbToData()` и
   восстанавливается `ItemFactory.newFromDocument`, как невыданная награда сборки (`rw`) и квестов
   (`REWARD_FIELD`). Когда именно делается бросок — [открытое решение 5](#open-decisions).
5. **Выдача** — `user().addItem(item, AnalyticsSubjectId.<источник>)`, ответ клиенту —
   `item.apiResponse()`. Новый `AnalyticsSubjectId` под источник.

Реестр знает только `Item` и `RewardEntry`. Бросок и выдача от конкретного типа не зависят.

<a id="new-reward-type"></a>
## 4. Добавление нового типа награды

- **Новый ресурс** (например, валюта): константа в `ItemId` и запись ресурсного варианта с этим
  `id` в реестре. Больше ничего не нужно: `Resource` уже стакается и выдаётся через `addItem`.
- **Новая техника или генерал**: новый класс `extends BagItem`, значение в `ItemType` (ordinal = поле
  `t` в БД, добавлять только в конец), регистрация в `ItemFactory`, свой вариант `RewardEntry`,
  который создаёт предмет нужного качества. Генерал обязан быть `BagItem`, иначе `User.addItem`
  его не выдаст ([находка 3](#findings)). Персистентность нового предмета — через
  `server-developer-db-persistence`.
- **Умение генерала** (вне текущей задачи) — тип награды с целью (конкретный генерал), его нельзя
  выдать без генерала. Паттерн это не покрывает: понадобится проверка доступности варианта перед
  броском (отфильтровать варианты, как `rollDropSectionType` фильтрует секции). Решать в задаче
  генералов.

<a id="findings"></a>
## 5. Находки анализа

1. **Взвешенный бросок реализован много раз** (правило `#gdd-function-mapping`: одно правило — одна
   функция). Кроме `DropUtils.RollDrop`, свои циклы накопления веса есть в
   `BoostSummonData.getRandomBoostRank` / `getRandomBoostStarsRank` / `getRandomBoostStarsCount` (три
   одинаковых цикла, шкалы 100 000 и 100), `AirDropData` (`nextPercents`), `AerodromeSummonData`,
   `AssemblyNeedSchemePartsData`, `IdleUserComponent` (шкала 1000),
   `CollectionUserComponent.rollDropSectionType`. Для реестра — только `DropUtils.RollDrop`.
   Сведение остальных к нему — отдельная задача рефакторинга, не в лутбоксах.
2. **Неявный порядок при создании танка.** Вызывающий сам делает `createNew` → `setLevel` →
   `setStars` → `recalculateParams()`. Забытый последний шаг даёт танк с неверными `params`/`power`.
   Вариант танка в реестре повторил бы этот порядок в четвёртом месте (поезд, сборка, коллекции).
   Предложение: метод-переход у владельца (`Tank`), создающий готовый танк с уровнем и звёздами
   ([правило](agent-system-workflow.md#no-implicit-order)). Решение — за пользователем.
3. **`User.addItem` молча пропускает не-`BagItem`.** Награда, которая не `BagItem`, теряется без ошибки.
   Для реестра это значит: любой новый тип награды должен быть `BagItem`, либо в `addItem` нужна явная
   ветка.
4. **Расхождение с документом сумки.** В [bag `#cls-item`](bag-architecture.md#cls-item) у `ItemType`
   указан `COLLECTION_ITEM` 6 и шесть зарегистрированных типов в `ItemFactory`. На ветке
   `koba/lootbox` в `ItemType` шесть значений без `COLLECTION_ITEM` (`RESOURCE`…`MILITARY_BASE_BOOST`), в `ItemFactory` тоже шесть.
   Ordinal нового типа (генерала) зависит от того, какая версия попадёт в master; проверить перед
   добавлением.

<a id="open-decisions"></a>
## 6. Открытые решения (не приняты, вынесены пользователю)

1. **Откуда реестр берёт числа.** Захардкожено в Java-классе `*Data` (как `AirDropData`,
   `BoostSummonData`) или отдельный лист в `balance.json`, разбираемый в `Balance.build` (как
   `SummonRankChances`). ТЗ ссылается на таблицу «Расчеты», которой нет.
2. **Перечисление качества лутбокса.** `Rank.I…X` (как звёзды и бусты) или свой enum с 10 значениями.
3. **Шкала веса.** Сумма весов (`maxChance = 0`, без промаха) или фиксированная шкала
   (100 / 100 000) с проверкой, что сумма равна шкале.
4. **Что значит «количество» для танка и генерала.** Для ресурса это `count`. Для техники в ТЗ
   диапазона нет, есть «качество генерала» и «количество и качество звёзд». Нужно правило: качество
   лутбокса → диапазон ранга / ранг звёзд / число звёзд.
5. **Момент броска.** При получении сундука, при постановке на открытие или при открытии. От этого
   зависит защита от переброса: двойное нажатие «Открыть», две вкладки, обрыв сети между броском и
   выдачей. Бросок, не сохранённый до выдачи, можно перебросить повторным запросом.
6. **«Призывы» в ТЗ** — это `RESOURCE_TANK_SCHEME` (в окне «схемы поезда 3 - 15») или что-то другое.

<a id="file-map"></a>
## 7. Карта файлов

Реестра в коде ещё нет, поэтому прямого влияния пока нет; ниже — файлы, на которые паттерн опирается.

**Файлы косвенного влияния**

| Файл | Роль |
|---|---|
| `game/src/main/java/com/linkedgames/game/service/drop/DropUtils.java` | зависимость: взвешенный бросок |
| `game/src/main/java/com/linkedgames/game/service/drop/DroppedItem.java` | зависимость: пара значение + вес |
| `game/src/main/java/com/linkedgames/game/model/item/Item.java` | зависимость: модель награды, `apiResponse`/`dbToData` |
| `game/src/main/java/com/linkedgames/game/model/item/ItemType.java` | зависимость: тип предмета, ordinal в БД; сюда добавляется генерал |
| `game/src/main/java/com/linkedgames/game/model/item/ItemFactory.java` | зависимость: восстановление сохранённой награды, регистрация нового типа |
| `game/src/main/java/com/linkedgames/game/model/item/ItemId.java` | зависимость: `id` ресурсов |
| `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` | зависимость: награда-ресурс |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/Tank.java` | зависимость: награда-танк, [находка 2](#findings) |
| `game/src/main/java/com/linkedgames/game/model/Rank.java` | зависимость: кандидат на качество |
| `game/src/main/java/com/linkedgames/game/balance/Balance.java` | зависимость: `getTanks(rank)`, место листа реестра при варианте 1 |
| `game/src/main/java/com/linkedgames/game/model/user/User.java` | зависимость: `addItem`, [находка 3](#findings) |
| `game/src/main/java/com/linkedgames/game/model/offers/OfferRewardData.java` | образец неизменяемого набора наград |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/BoostSummonData.java` | образец `getInfoJSON`; дубль броска, [находка 1](#findings) |
| `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropBox.java` | образец «качество → диапазон» |
