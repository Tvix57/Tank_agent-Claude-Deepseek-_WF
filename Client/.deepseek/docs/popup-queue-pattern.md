# Паттерн последовательного показа попапов (очередь флешей)

Как показать два попапа друг за другом, а не параллельно: второй буферизуется и публикуется только
после уничтожения первого.

> **Статус примера ниже (2026-09-25):** конкретный кейс `HomeScreen`/`TrainCollectionItemPopup`/
> `CollectionSetCompletedPopup`, на котором был написан этот документ, БОЛЬШЕ НЕ ДЕЙСТВУЕТ в коде — по
> явному решению пользователя очередь для `CollectionCompletePopup` (переименован из
> `CollectionSetCompletedPopup`, перенесён в `src/views/popups/`) убрана: поля
> `trainCollectionItemPopupOpen`/`pendingCollectionSetCompleted` и метод
> `onTrainCollectionItemPopupExit()` удалены из `HomeScreen`, попап показывается независимо (см.
> `.claude/docs/collections-architecture.md#cls-headerachievementsbar-set-completed`, `#s8` п.7). Сам приём
> (буфер + `EVENT_DESTROYED`) ниже оставлен как справочный рецепт на случай, если он понадобится для
> другой пары попапов. На 2026-09-25 живого примера полной реализации не было; с 2026-10-29 он есть —
> `LootboxReceivedPopup` (ветка `koba/lootbox`, не закоммичено), см. [#lootbox-example](#lootbox-example).
> Смежная подписка на `EVENT_DESTROYED` в `TankGetPopup` и подобных — только `onExit`, без последовательности показа.

**Содержание:** [Проблема](#problem) · [Решение](#solution) · [Пример](#example) ·
[Когда применять](#when) · [Альтернативы](#alternatives)

## Проблема: FlashOverlay не строит очередь {#problem}

`FlashOverlay.publish()` (`src/ee/scene/flash/FlashOverlay.ts`) вставляет флеш в стек по приоритету
поля `important`, но собственной очереди показов не строит. Без явной синхронизации два одновременно
публикуемых попапа отрисуются параллельно, перекрывая друг друга.

После merge `amnesia/fix` у `FlashOverlay` есть `removeAll(skipTag?)` — закрывает все флеши, кроме
помеченных тегом (так `Footer` переключает вкладки `BattlefieldPopup`/`ClanPopup`/`ShopPopup`). Это
сброс стека, а не очередь: задачу последовательного показа он не решает.

## Решение: буфер + `Layout.EVENT_DESTROYED` {#solution}

1. **`FlashLayout.isParallel`** (`src/ee/scene/flash/FlashLayout.ts`) — может ли флеш показываться
   параллельно другим; у модальных попапов `false`.
2. **`FlashPublisher.publish(flashLayout)`** (`src/shared/FlashPublisher.ts`) — публикация флеша в
   `flashOverlay` активной сцены.
3. **Буфер в компоненте-инициаторе** — хранит данные второго попапа, пока первый открыт.
4. **`Layout.EVENT_DESTROYED`** — событие уничтожения `Layout`; на него первый попап вешает
   `onExit`-колбэк, по которому инициатор публикует второй.

## Пример: HomeScreen (живой вызов `onExit`) {#example}

Буфер и флаг `trainCollectionItemPopupOpen` из `HomeScreen` сняты (см. статус в начале документа), в коде остался
только колбэк выхода. `HomeScreen.onTrainCollectionItemReceived` (`src/views/home_screen/HomeScreen.ts`, ~864–897):

```typescript
private onTrainCollectionItemReceived(item: CollectionTrainJSON) {
    let autoParams = this.autoTrainParams;
    if (autoParams !== undefined && item.sellReward) {
        Globals.bag.releaseHold("TrainCollectionItemPopup::RESOURCE_SILVER_COINS");
        this.clearTrainCart(autoParams);
        return;
    }

    TrainCollectionItemPopup.publish(this, {
        itemInfo: item.itemInfo,
        sellReward: item.sellReward,
        collectionInfo: item.collectionInfo,
        sectionInfo: item.sectionInfo,
        onExit: () => this.clearTrainCart(autoParams)
    });
}
```

Попап вызывает `onExit` из подписки на уничтожение своего лэйаута (конструктор `TrainCollectionItemPopup`,
`src/views/home_screen/popups/train/TrainCollectionItemPopup.ts`) и из `.catch` загрузки ассетов в `publish`:

```typescript
this.layout.on(Layout.EVENT_DESTROYED, () => this.onDestroy());   // onDestroy() → this.data.onExit?.()
```

## Живой пример: LootboxReceivedPopup (буфер + generation) {#lootbox-example}

Файл: `src/views/home_screen/popups/lootbox/LootboxReceivedPopup.ts`. Буфер и флаг — статические поля класса,
а не инициатора: `queue: { screen, quality }[]`, `isShown`, `generation` (`:31-33`).

- `enqueue(screen, quality)` (`:139`): `push` в `queue`; если `!isShown` — `showNext()`.
- `showNext()` (`:146`): `shift()`; пусто — выход. Иначе `isShown = true`, запоминается текущее `generation`,
  добавляется пакет `MilitaryBaseScreen` и через `App.assetPacker.onComplete` (`:154`) создаётся попап и
  публикуется `FlashPublisher.publish(flash.getAsGameFlash())` — но только если `generation` не изменилось.
- Попап публикуется с `setParallel(true)` (`getAsGameFlash`, `:136`), то есть не опирается на
  `FlashLayout.isParallel` из раздела «Решение»: последовательность держит буфер `queue`, а не флаг FlashOverlay.
- `EVENT_DESTROYED` вешается в конструкторе (`:49`) → `onDestroy()` (`:104`): снимает подписку `BAG_UPDATE`,
  `Tweens.removeByTarget`; затем, если `this.generation === LootboxReceivedPopup.generation`, — `isShown = false`
  и `showNext()` (`:111-115`). Попап старой генерации только гасит себя и очередь не трогает.
- `clearQueue()` (`:163`): `queue.length = 0`, `isShown = false`, `generation++`. Вызывается из
  `Globals.logout()` (`src/plain/Globals.ts:104`), так что после выхода ни очередь, ни колбэк `onComplete`,
  зарегистрированный до выхода, не покажут попап.
- Инициатор — `HomeScreenQuest.BtnQuest` (`src/views/home_screen/HomeScreenQuest.ts:170-174`): на каждую
  награду `ItemType.LOOTBOX` вызывает `enqueue`.

Дополнение к рецепту выше: `generation` отсутствует в рецепте «Решение», но без него колбэк `onComplete`,
зарегистрированный до `clearQueue()`, показал бы попап уже в новой сессии.

## Когда применять {#when}

- Два независимых серверных сообщения могут прийти почти одновременно (здесь — ответ
  `/ingame/train/summon` и push `/events/collections/setCompleted`).
- Нужна гарантия, что попапы не отрисуются параллельно.

`src/utils/SequentialQueue.ts` в проекте есть, но нигде не используется (мёртвый код) — приём с
буфером и `EVENT_DESTROYED` проще и явнее при чтении кода.

## Альтернативы {#alternatives}

- **`isParallel = false` у обоих попапов + приоритет `important`** — работает, если попапы заметно
  отличаются по важности, но менее явно.
- **`SequentialQueue`** — более общий подход, лишняя сложность для сценария из двух попапов.
- **Один ответ сервера на оба события** — изменение контракта.

## Примеры в коде

- `LootboxReceivedPopup` (`src/views/home_screen/popups/lootbox/LootboxReceivedPopup.ts`) — полный живой пример буфера,
  `EVENT_DESTROYED` и счётчика `generation` со сбросом в `Globals.logout()`, см. [#lootbox-example](#lootbox-example).
- `HomeScreen` + `TrainCollectionItemPopup` + `CollectionSetCompletedPopup` — была полная реализация очереди,
  **удалена 2026-09-25** вместе с переходом `CollectionSetCompletedPopup` → `CollectionCompletePopup`
  (тост без очереди, см. статус в начале документа). Код примера выше — живой, но буфер в нём уже не используется.
- `TankGetPopup` (`.../popups/tank/TankGetPopup.ts`) — та же подписка на `EVENT_DESTROYED` для другой
  цели; такой же приём есть в попапах `settings/`, `BattlefieldPopup`, `IdlePopup`.
