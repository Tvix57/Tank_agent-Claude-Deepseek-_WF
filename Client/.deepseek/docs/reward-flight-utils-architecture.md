# RewardFlightUtils (client)

ГДД: [lootbox-gdd.md#gdd-claim](game-design/lootbox-gdd.md#gdd-claim) (награда уже в сумке, окно закрыто до ответа — без повторного показа).
Статус: обычный — код написан по ГДД в задаче ветки koba/lootbox, 2026-10-30 (не закоммичено). Формат полный.

**Содержание:** [Назначение](#purpose) · [Классы и файлы задачи](#classes) · [Паттерны](#patterns) · [RewardFlightUtils](#api) · [Жизненный цикл записи](#lifecycle) · [Цели FLY_ICONS](#targets) ·
[Места вызова](#callers) · [Компромиссы](#tradeoffs) · [Карта файлов](#file-map)

## Назначение {#purpose}
Сервер уже выдал награду ресурсами, а в хедере счётчик должен вырасти только при прилёте иконок. Утилита
вешает на ресурсы награды удержание в сумке (`Globals.bag.holdResource`), по команде запускает полёт иконок
к хедеру и снимает удержание по окончании полёта (`releaseHold`). Если окно закрыли до полёта, удержание
снимается само, счётчик не зависает. Паттерн: [client-ui-patterns.md#fly-to-target](client-ui-patterns.md#fly-to-target).
Остальные места клиента (`HomeScreen` поезд, `AchievementLine`, `GoldenCoinsOfferPopup`, `MilitaryBaseStoragePopup`, `TrainBuySchemesPopup`,
`CampaignBattleGround`, `AirDrop`) пишут удержание вручную и утилиту не используют.

## Классы и файлы задачи {#classes}
Создано: `RewardFlightUtils` (`src/plain/RewardFlightUtils.ts`). Изменено: вызывающие `HomeScreenQuest`, `IdlePopup`, `LootboxIdleSection` переведены на утилиту. Класс один, его описание — [RewardFlightUtils](#api).

## Паттерны {#patterns}
[client-ui-patterns.md#fly-to-target](client-ui-patterns.md#fly-to-target) (отправитель `FlyIconsAnimation.play`, подписчик в виджете-цели, связка с `holdResource`/`releaseHold`); [bag-architecture.md](bag-architecture.md) (удержание). Референсов нет.

## RewardFlightUtils {#api}
Правила ГДД: `hold` и `fly` для награды задания — [#gdd-obtain](game-design/lootbox-gdd.md#gdd-obtain); `hold` и `fly` для «ЗАБРАТЬ» и закрытия окна «Трофеи» — [#gdd-trophies-window](game-design/lootbox-gdd.md#gdd-trophies-window); `hold`, `fly` и `cancel` для награды открытого сундука и закрытия окна до ответа — [#gdd-claim](game-design/lootbox-gdd.md#gdd-claim). Сам класс общий: правило выражается вызывающим, утилита обеспечивает «счётчик растёт при прилёте».

Класс только со static-входом; экземпляр (запись полёта) создаётся внутри `hold`. Правило ГДД, которое выражает весь класс, — `#gdd-claim`.
- `hold(rewards: ItemJSON[], owner: Layout): number` — `id = ++lastId`. Из `rewards` берутся только `itemType === RESOURCE` с `id` из таблицы [целей](#targets), количества одного `id` суммируются (`collectCountById`). На каждый `itemId` ставится удержание с тегом `"RewardFlight::" + id + "::" + itemId`. Запись кладётся в private static `flightById` и подписывается на уничтожение `owner`. Если `owner` уже уничтожен (`objVersion() === 0`), удержание и запись не создаются, id возвращается. `rewards` может быть `null`/`undefined`.
- `fly(id, from: PIXI.Point)` — запись удаляется (`remove`), для каждого ресурса `FlyIconsAnimation.play(цель, min(10, count), from, onEnd)`, в `onEnd` — `releaseHold` по тегу. Если сцена уничтожается (`Globals.getScene().isDestroyed`), полёт не запускается, `releaseHold` вызывается сразу: подписчики `FLY_ICONS` к этому моменту отписались и `onEnd` не придёт (решение 2026-11-04, снос экрана при открытом окне награды).
- `cancel(id)` — запись удаляется, `releaseHold` без полёта.
- Правило использования (решение пользователя 2026-10-30): id сначала в именованную переменную, затем `fly`: `let flyId = RewardFlightUtils.hold(rewards, owner);` и `RewardFlightUtils.fly(flyId, from);`. Вложенный вызов `fly(hold(...), from)` не используется.
- Повторный и неизвестный id для `fly` и `cancel` ничего не делают: однократность задаётся удалением записи при первом `fly`/`cancel`, отдельного флага нет.
- Private: конструктор, `fly`/`release` (экземплярные), `cancelAfterDestroy`, `holdTag`, `collectCountById`, static `remove`.
- Id полёта — обычный `number`, как остальные id в проекте (`tickId`, `readyTimerId`); отдельный тип не заводится (решение пользователя 2026-10-30): неизвестный id в `fly`/`cancel` ничего не делает.

## Жизненный цикл записи {#lifecycle}
1. `hold` — запись создана, удержание стоит, на `owner` повешен `Layout.EVENT_DESTROYED` → `onOwnerDestroyed`.
2. Один из выходов, первый побеждает:
   - `fly(id, from)` — запись удалена, подписка снята, иконки летят, удержание снимается в `onEnd` каждой цели;
   - `cancel(id)` — запись удалена, подписка снята, удержание снято сразу;
   - уничтожение `owner` — `cancelAfterDestroy()`.
3. `cancelAfterDestroy()` не отменяет сразу, а ставит `cancel(id)` микрозадачей (`Promise.resolve().then(...)`): она выполнится после всех синхронных обработчиков того же destroy, до следующего кадра. Причина: `fly` из других обработчиков того же destroy (`IdlePopup.releaseResources`, `onExit` у `LootboxRewardPopup`) может идти позже `onOwnerDestroyed`; он успевает удалить запись, и отложенный `cancel` становится no-op. Порядок подписчиков на destroy поэтому не важен. Решение пользователя 2026-10-30 (вместо заглушки `ALWAYS_ALIVE` для `App.tick`).
4. Снятие подписки (`owner.off(Layout.EVENT_DESTROYED, ...)`) делается в `remove` только у живого владельца (`objVersion() !== 0`). У уничтоженного `Layout` подписки уже очищены, а `off` внутри `emit` сдвигает массив обработчиков в `ee/EventEmitter` и может пропустить соседний обработчик.

Идемпотентность: двойной `fly`, `fly` + `cancel`, `cancel` + destroy безопасны (запись одна, удаляется один раз). Удержание не может остаться навсегда, пока у каждой цели есть подписчик с вызовом `onEnd`.

## Цели FLY_ICONS {#targets}
Таблица `TARGET_BY_RESOURCE_ID` (private static). В неё входят только цели с живым подписчиком на `GameEvents.FLY_ICONS`: если подписчика нет, `onEnd` не придёт и удержание не снимется.

| ItemId | Цель (`FlyIconsAnimation`) | Подписчик |
|---|---|---|
| `RESOURCE_SILVER_COINS` | `HEADER_SILVER_COINS` | `HeaderSilverCoinsBar.onFlyIcons`, иконки летят |
| `RESOURCE_GOLDEN_COINS` | `HEADER_GOLDEN_COINS` | `HeaderGoldenCoinsBar.onFlyIcons`, иконки летят |
| `RESOURCE_TANK_SCHEME` | `TRAIN_TANK_SCHEMES` | `HomeScreen.onFlyIcons`, полёт к футеру |
| `RESOURCE_MILITARY_BASE_DOLLARS` | `HEADER_DOLLARS` | `HeaderDollarsBar.onFlyIcons`, иконки летят |
| `RESOURCE_MILITARY_BASE_TOKENS` | `HEADER_TOKENS` | `HeaderTokensBar.onFlyIcons`: сразу `data.onEnd()`, иконок нет |

Доллары и жетоны оставлены по решению пользователя, хотя их бары на главном экране скрыты.

Схемы самолёта (`RESOURCE_AIRPLANE_SCHEME`) исключены: цели в коде нет, а подписчик `HOME_AERODROME_AIRPLANE_SCHEMES` живёт только в неподключённом `HomeScreenAerodrome`. Ресурс не попадает в `countById`, удержание на него утилита не ставит. Ручные места (`CampaignBattleGround` и другие, не перешедшие на утилиту) ставят удержание на схемы самолёта и не снимают; открытая задача — бэклог `.claude/exports/backlog-2026-10-21.md`, «Удержание схем самолёта не снимается».

Новая цель: константа в `FlyIconsAnimation`, подписчик в виджете-цели (образец `HeaderSilverCoinsBar.onFlyIcons`, обязательно с вызовом `onEnd`), строка в таблице.

## Места вызова {#callers}
- `HomeScreenQuest.BtnQuest` — после `/ingame/home/completeQuest`: `let flyId = RewardFlightUtils.hold(response.rewards, this.layout)` и `RewardFlightUtils.fly(flyId, Coord.getWorldPosition(this.layout.container))` (`HomeScreenQuest.ts:170-171`); точка вылета — плашка задания. ГДД: `#gdd-obtain`.
- `IdlePopup` — поле `flyId: number | null`. `requestData()` по ответу `/ingame/home/idle` ставит `hold(this.data.rewards, this.layout)`. `takeRewards(from)` («ЗАБРАТЬ») вызывает `fly(flyId, from)`; `releaseResources()` (`onDestroy`) — `fly(flyId, центр экрана)`, так как `layout` к этому времени уничтожен. Второго полёта после «ЗАБРАТЬ» нет: однократность внутри утилиты. Закрытие окна до ответа удержание не ставит (`owner` мёртв).
- `LootboxIdleSection.showOpenResult` — после проверки «окно живо» `hold(result.rewards, this.layout)`, затем `LootboxRewardPopup.publish({ onExit: () => fly(flyId, центр экрана) })`. Контекст лутбоксов: [lootbox-architecture.md#reward-flight](lootbox-architecture.md#reward-flight).

## Компромиссы {#tradeoffs}
Принятые:
- Круг ресурсов ограничен таблицей целей; остальные ресурсы и предметы награды удержания не получают и в хедере появляются сразу, как только сумка обновится.
- `HEADER_TOKENS` подписан, но иконки не летят: подписчик вызывает `onEnd` в тот же кадр, удержание снимается сразу.
- До 10 иконок на ресурс (`MAX_ICONS`), независимо от количества.
- Статические `lastId` и `flightById` живут до перезагрузки страницы. Запись удаляется по `fly`, `cancel` или уничтожению владельца; дольше всего живёт запись владельца, который жив и не вызвал `fly`/`cancel`.
- Пустой после фильтрации `countById` (например, в награде только лутбоксы) всё равно создаёт запись и подписку на уничтожение владельца: `hold` не различает «нечего удерживать». Эффекта на игру нет — `fly` такую запись удаляет без анимации и без `releaseHold` (обсуждено 2026-11-04, правка не нужна).
- `hold` и `fly` вызываются подряд (`HomeScreenQuest`, `LootboxIdleSection`) — удержание снимается не в `fly`, а по `onEnd` анимации, поэтому счётчик в хедере не дёргается до прилёта иконок. Разрыв между вызовами нужен только `IdlePopup` («ЗАБРАТЬ» позже открытия окна).

## Карта файлов {#file-map}
**Файлы прямого влияния**
- `src/plain/RewardFlightUtils.ts` — утилита.

**Файлы косвенного влияния**
- `src/views/home_screen/HomeScreenQuest.ts` — вызывающий (`BtnQuest`).
- `src/views/home_screen/popups/idle/IdlePopup.ts` — вызывающий (`requestData`, `takeRewards`, `releaseResources`).
- `src/views/home_screen/popups/lootbox/LootboxIdleSection.ts` — вызывающий (`showOpenResult`).
- `src/shared/animations/FlyIconsAnimation.ts` — зависимость: `play`, константы целей.
- `src/shared/header/presets/HeaderSilverCoinsBar.ts`, `HeaderGoldenCoinsBar.ts`, `HeaderDollarsBar.ts`, `HeaderTokensBar.ts` — подписчики целей хедера.
- `src/views/home_screen/HomeScreen.ts` — подписчик `TRAIN_TANK_SCHEMES` (`onFlyIcons`).
- `src/plain/user/UserBag.ts` — зависимость: `holdResource`, `releaseHold` ([bag-architecture.md](bag-architecture.md)).
- `src/plain/Globals.ts` — зависимость: `Globals.bag`.
- `src/views/home_screen/popups/bag/bag.d.ts` — зависимость: тип `ItemJSON`.
- `src/plain/items/ItemId.ts`, `src/plain/items/ItemType.ts` — зависимость: идентификаторы ресурсов и тип `RESOURCE`.
- `src/ee/display/layout/Layout.ts` — зависимость: `Layout.EVENT_DESTROYED`, `objVersion()`.
