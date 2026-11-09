# Паттерн: отказ со свежим состоянием

**auto-create** (по коду ветки `koba/lootbox`, 2026-10-27). Паттерн собран из существующих кусков
кода; первый потребитель — лутбоксы (отказ постановки, ускорения и «Открыть»). Код лутбоксов на ветке есть
(`LootboxPage.sendRefusal`), см. [lootbox-architecture.md](lootbox-architecture.md).

ГДД: [lootbox-gdd.md#gdd-claim](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-claim),
подраздел «Нестандартные действия»: «Сервер отказал на постановку, ускорение или „Открыть“: попап
закрывается, окно „Трофеи“ без сообщения перерисовывается по данным сервера»;
[#gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup) — сервер принимает
цену клиента, только если она не ниже текущей; [bag-gdd.md#gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend)
— трата только при достаточном остатке.

<a id="toc"></a>
## Оглавление

[Назначение](#purpose) · [Строительные блоки в коде](#building-blocks) · [Где уже встречается](#usages) ·
[Схема паттерна](#scheme) · [Списание валюты](#spend) · [Находки анализа](#findings) ·
[Открытые решения](#open-decisions) · [Связь с ГДД](#gdd-link) · [Карта файлов](#file-map)

<a id="purpose"></a>
## 1. Назначение

Клиент показывает состояние, которое могло устареть: вторая вкладка уже поставила сундук, таймер
истёк, цена ускорения выросла, серебро потрачено в другом окне. Сервер отказывает и в том же ответе
отдаёт актуальное состояние, чтобы клиент перерисовался без второго запроса и без сообщения игроку.

Push `/events/bag/update` эту задачу не решает: он шлёт только изменённые предметы
([bag `#m-sendchanges`](bag-architecture.md#m-sendchanges)), а при отказе ничего не меняется, и push
не приходит.

<a id="building-blocks"></a>
## 2. Строительные блоки в коде

| Блок | Где | Что даёт паттерну |
|---|---|---|
| `JsonPacket.error()` | `commons/.../server/ws/JsonPacket.java` | Ставит `result = "ERROR"` в payload. Цепочка возвращает тот же пакет, `addToPayload` можно звать до и после. |
| `JsonPacket.addToPayload(key, value)` | там же | Кладёт поле в payload; `null` молча пропускается. |
| `JsonPacket.addError(section, code)` | там же | Кладёт `errSection`/`errCode`, но **не** ставит `result`. Совместим с `error()` в одной цепочке (так делает `User` при отказе авторизации, `User.java:455`). |
| `PageProcessor.createResponse()` | `commons/.../ws/pages/impl/DefaultPageProcessor.java` | Каждый вызов создаёт новый пакет и копирует `globalPayload`. Ответ собирается в одной цепочке и уходит `sendReply()`. |
| `Page.callAction` → `onFail` | `commons/.../ws/pages/Page.java` | Брошенный `APICodeException` превращается в ответ только с `errSection`/`errCode`/`errVars`: ни `result`, ни состояния, `onRouteCallEnd` не вызывается. Поэтому отказ со состоянием отдаётся явным ответом и `return`. |
| `PageProcessor.addToGlobalPayload` / `AuthorizedUserPage.appendHeader` | `game/.../pages/ws/ingame/AuthorizedUserPage.java` | Механизм «добавить поле в любой ответ страницы, включая ошибку». Сейчас мёртвый: `headerResponse` всегда пуст ([находка 3](#findings)). |
| `UserActor.onAfterMessageReceive` → `processDelayedExecution` | `game/.../model/user/UserActor.java` | Push сумки уходит после ответа и на успехе, и на отказе, если что-то в сумке успело измениться. |

<a id="usages"></a>
## 3. Где уже встречается

Отказ с данными в payload есть в двух местах; ни одно не отдаёт полное состояние.

- **`MilitaryBasePage`** — пять одинаковых блоков (`/buyBuilding`, `/upgradeProduction`,
  `/upgradeProductionCapacity`, `/runFactory`, `/upgradeStorage`): не хватает долларов и нет
  `useGoldenCoins` → `error()` + `missingDollars` + `goldenCoinsCost`. Это котировка цены при отказе,
  ближайший аналог «отказ + актуальная цена ускорения»
  ([military-base-architecture.md](military-base-architecture.md), строка 67).
- **`ChatService` / `ModeratorsChatService`** (`subscribe`) — чат не загружен → `error()` + `retryMS`.

Остальные отказы (`TrainPage`, `BanPanelPage`, `ShopPage`, `CampaignPage` и др.) — голый `error()`.
Свежее состояние сейчас приходит только в успешных ответах (туториал, airDrop) и через push сумки.

<a id="scheme"></a>
## 4. Схема паттерна

Черновик, имена условные: окончательные даёт разработка по скиллу `naming`.

1. **Одна функция состояния.** У владельца области один метод, собирающий JSON состояния (для
   лутбоксов — сундуки по качествам, ячейка, таймер, текущая цена ускорения). Его зовут и успешный
   ответ, и отказ, и `/get` окна; отдельной функции «состояние для ошибки» нет (правило
   [`#gdd-function-mapping`](agent-system-workflow.md#gdd-function-mapping)).
2. **Сначала все проверки, потом изменения.** Транзакций нет: если отказать после частичного списания,
   списанное не вернётся, а push уйдёт. Проверки идут до первого `addResource`/`add`.
3. **Отказ — явный ответ и `return`:**
   `createResponse().error().addError(<section>, <code>).addToPayload("<state>", <функция состояния>).sendReply()`.
   Код причины нужен, когда клиент ведёт себя по-разному: «не хватает и золота» → переход в магазин
   ([`#gdd-speedup`](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup)), прочие
   отказы → тихая перерисовка. Нужен ли код всегда — [открытое решение 2](#open-decisions).
4. **Ключ состояния один и тот же** в успехе и отказе, чтобы клиент обрабатывал оба ответа одним
   обработчиком.
5. **Исключения** (`JSONException`, `Throwable`, `APICodeException`) по-прежнему уходят через `onFail`
   без состояния. Что делает клиент в этом случае — [открытое решение 3](#open-decisions).
6. **Повторный запрос** (двойное нажатие, повтор после обрыва сети) — тоже отказ со состоянием:
   сундук уже стоит или уже открыт, ответ показывает это, награда второй раз не выдаётся.

<a id="spend"></a>
## 5. Списание валюты

Отказ «не хватает валюты» и само списание — одна проверка, поэтому паттерн опирается на метод
списания. Его сейчас нет:

- `BagUserComponent.addResource(id, -цена)` не проверяет остаток
  ([bag `#tradeoffs` п.5](bag-architecture.md#tradeoffs)).
- «Проверить `getResourceCount` → `addResource(-цена)`» повторено у вызывающих: `TrainPage`,
  `SettingsPage`, `AssemblyUserComponent`, `ClanPage`, `MilitaryBasePage`
  ([bag `#tradeoffs` п.6](bag-architecture.md#tradeoffs)).
- «Списать всю валюту A, остаток добрать валютой B по курсу с округлением вверх» — в
  `MilitaryBasePage` пять копий (доллары → золото через
  `MilitaryBaseUserComponent.getGoldenCoinsCostForDollarsCost`). Лутбоксам нужно то же правило для
  серебра → золото с фиксированным курсом.
- `APICodeList.throwExceptionNoGoldenCoins` и `ERR_NOT_ENOUGH_GOLDEN_COINS` объявлены, вызовов нет.

Предложение для решения пользователя ([открытое решение 4](#open-decisions)): метод-переход у
владельца сумки «списать, если хватает», который проверяет остаток и списывает за один вызов
([`#no-implicit-order`](agent-system-workflow.md#no-implicit-order)), и поверх него вариант с
доплатой второй валютой. Возврат — признак успеха (или недостающее количество), по нему страница
собирает отказ со состоянием.

<a id="findings"></a>
## 6. Находки анализа

1. **Два вида «ошибки» в ответе.** `error()` ставит `result = "ERROR"`, `addError` и `onFail` —
   только `errSection`/`errCode`. Ответ из исключения не содержит `result`. Какой признак отказа
   читает клиент — вопрос клиентского потребления, сервер его не определяет.
2. **Пять копий блока «доллары → золото»** в `MilitaryBasePage` и повтор проверки остатка у пяти
   вызывающих — одно правило [gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend)
   в нескольких местах. Сведение в метод сумки — [открытое решение 4](#open-decisions); перевод
   военной базы на него — отдельный рефакторинг.
3. **`AuthorizedUserPage.appendHeader` пуст.** Читает `header` из запроса, но ничего не кладёт:
   `headerResponse` создаётся пустым и не заполняется. Через `globalPayload` можно добавлять состояние
   в любой ответ страницы, включая ответ из `onFail`, но механизм сейчас ничего не отдаёт.
4. **`throwExceptionNoGoldenCoins` не используется.** Если отказы лутбоксов пойдут через исключение,
   состояние в ответ не попадёт ([схема, п.5](#scheme)).
5. **Сравнение цены.** По ГДД цена клиента принимается, если она «не ниже» серверной. Когда цена
   состоит из серебра и золота, «не ниже» для пары не определено ([открытое решение 5](#open-decisions)).

<a id="open-decisions"></a>
## 7. Решения

Приняты пользователем (2026-10-27/28, лутбоксы):
1. **Состояние отказа** — только `{lootbox}` (ячейки, таймер); балансы клиент берёт из bag-push.
2. **Код причины** — нет ни у одного отказа; нехватку золота проверяет клиент и ведёт в магазин.
4. **Списание** — проверка и `addResource(-цена)` внутри `LootboxUserComponent.speedupAndOpen`, без
   метода в `BagUserComponent`.
5. **«Не ниже» для пары валют** — `silver + gold × SILVER_PER_GOLD ≥ цена(remaining − 60 с)`, при
   достаточных балансах списывается ровно присланная пара.

Открыто:
3. **Отказ из исключения.** Клиент сам перезапрашивает `/ingame/lootbox`, или сервер добавляет
   состояние и в ответ `onFail` (переопределить `onFail` в странице лутбоксов либо заполнить
   `appendHeader`).

<a id="gdd-link"></a>
## 8. Связь с ГДД

| Правило ГДД | Функция | Покрыто кодом |
|---|---|---|
| [lootbox #gdd-claim](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-claim) — отказ → перерисовка по данным сервера | `LootboxPage.sendRefusal` — `error()` + `{lootbox}` | да |
| [lootbox #gdd-speedup](/workspace/client/.claude/docs/game-design/lootbox-gdd.md#gdd-speedup) — цена клиента не ниже серверной, нехватка золота → магазин | `LootboxUserComponent.speedupAndOpen` | да; решения 2, 5 |
| [bag #gdd-gain-spend](/workspace/client/.claude/docs/game-design/bag-gdd.md#gdd-gain-spend) — минус запрещён | проверки у вызывающих + `addResource(-цена)` | да; решение 4 |

<a id="file-map"></a>
## 9. Карта файлов

Прямое влияние — код лутбоксов (`LootboxPage.sendRefusal`, `LootboxUserComponent`); ниже — файлы, на которые паттерн опирается.

**Файлы косвенного влияния**

| Файл | Роль |
|---|---|
| `commons/src/main/java/com/linkedgames/commons/server/ws/JsonPacket.java` | зависимость: `error`, `addError`, `addToPayload`, `globalPayload` |
| `commons/src/main/java/com/linkedgames/commons/server/ws/pages/Page.java` | зависимость: `callAction`/`onFail` — ответ из исключения без состояния |
| `commons/src/main/java/com/linkedgames/commons/server/ws/pages/impl/DefaultPageProcessor.java` | зависимость: `createResponse`, `addToGlobalPayload` |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AuthorizedUserPage.java` | зависимость: `appendHeader`, [находка 3](#findings) |
| `game/src/main/java/com/linkedgames/game/model/bag/BagUserComponent.java` | зависимость: `addResource`/`getResourceCount`, место метода списания |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/MilitaryBasePage.java` | образец отказа с котировкой цены; дубли доплаты, [находка 2](#findings) |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseUserComponent.java` | образец пересчёта нехватки в золото (`getGoldenCoinsCostForDollarsCost`) |
| `game/src/main/java/com/linkedgames/game/service/chat/ChatService.java` | образец `error()` + `retryMS` |
| `game/src/main/java/com/linkedgames/game/APICodeList.java` | зависимость: коды ошибок, неиспользуемый `throwExceptionNoGoldenCoins` |
| `game/src/main/java/com/linkedgames/game/model/user/UserActor.java` | зависимость: push сумки после ответа |
