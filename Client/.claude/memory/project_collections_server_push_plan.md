---
name: project-collections-server-push-plan
description: "План следующего этапа коллекций — события обновления шлёт сервер (операции секции), клиент только слушает; конвертация монет танка после решения; решения пользователя 2026-10-07"
metadata:
  node_type: memory
  type: project
  originSessionId: e0d4376c-204d-4285-addd-a5a301101f6b
  modified: 2026-10-07T04:09:40.504Z
---

**СТАТУС: реализовано 2026-10-07 (сессия 2): сервер и клиент одобрены, fix-review без костылей, доки обеих сторон обновлены и зарегистрированы; не закоммичено, ручная проверка в игре не выполнена.** Строится поверх незакоммиченного этапа событий (решение пользователя). Запускать через полный
пайплайн (integration-lead → сервер → одобрение → клиент → fix-reviewer → доки). Опирается на
незакоммиченный этап событий [[project-collections-events-refactor-plan]] — перед запуском спросить про
его коммит и ручную проверку.

## Решения пользователя 2026-10-07
- Источник событий — сервер. Клиентские `GameEvents.emitter.emit` после запросов удаляются; эмит только
  в `GameEvents.listenServerEvents`. Ответ на запрос управляет лишь UI инициатора (окно, анимация монеты).
- События независимые и точечные: push `collectionUpdated {collectionId}` на каждую затронутую коллекцию
  и `sectionUpdated {section}` на секцию; каждый запускает один точечный запрос
  (`/getCollection`, `/getSectionProgress`). `sectionRefreshed` поглощается (рестарт сезона — операция секции).
- Отправку делает СЕКЦИЯ: слой операций секции (сбор награды и прочие мутации) меняет коллекции, затем
  шлёт события; роуты/компонент не мутируют коллекции напрямую. Аргумент, глушащий события, — в этом
  слое; `collectAllAvailableRewards` вызывает операции с ним (клиент берёт полные данные из ответа,
  `reloadSection`). Первоначальная идея «push в addItem коллекции» отклонена самим пользователем
  (мутации идут не только через addItem).
- Танки (ГДД `#gdd-exp-reward` изменён 2026-10-07, есть запись в журнале):
  - «Получить» с танком → сервер запоминает отложенный танк, монеты НЕ конвертируются (6/6).
  - Окно выбора закрывается только «Выбрать»/«Продажа»; нештатное закрытие = решение не принято,
    при перезаходе полный набор и «Получить» открывает окно с тем же танком.
  - Конвертация монет и `everCompleted` (прогресс X/8) — после решения (take/sell); `nextRankItem`
    переезжает в ответ take/sell (без `collectionInfo`/`sectionInfo`).
  - Награда-золото (повторный сбор) — конвертация сразу при «Получить».
- Поток танка: ответ take/sell → анимация монеты; push 101 → карточка; push 102 (если не дубликат) →
  карточка, независимо от анимации; push секции → шапка.
- Альбомы — та же точечная логика; «Собрать всё» — исключение с полной перерисовкой.

- Убрать `refreshRequestId` (Collection, CollectionsTypeSection) вместе с инкрементом в `reloadSection`:
  ответы по одному сокету приходят в порядке запросов, а push — один на коллекцию за операцию; это
  отменяет пункт «гонки: побеждает последний запрос» из [[project-collections-events-refactor-plan]].

## Решения при запуске (2026-10-07, сессия 2)
- Push: `/events/collections/collectionUpdated {collectionId}`, `/events/collections/sectionUpdated {section}`.
- ОТМЕНА пункта «sectionRefreshed поглощается» (подтверждено явно): отдельный push
  `/events/collections/sectionRestarted {section}` (без collectionIds) при рестарте сезона в refreshState;
  на клиенте подписка/метод в базовой `CollectionsTypeSection`, поведение переопределяет наследник
  (альбомы — только таймер; танки вне сезонов).
- ГДД `#gdd-ops-season` изменён: награды за звёзды при рестарте НЕ сбрасываются (сервер `refreshSection` поправить).
- Глушение событий — параметр `boolean` у операций слоя секции.
- `nextRankItem` в ответе take/sell — полная форма (`collectionInfo`/`sectionInfo` внутри остаются,
  окну `TrainCollectionItemPopup` они нужны); «без collectionInfo/sectionInfo» относилось к самому ответу.
- `/markCollectionItemViewed` шлёт `sectionUpdated` с сервера.
- Ревью сервера (итог после нескольких разворотов): в AlbumsSectionType публичные `takeSectionReward()`/
  `takeCollectionReward(id)` → приватные перегрузки с `boolean quiet` (true = без событий), «Собрать всё» —
  с true; роуты quiet не передают. Остальные операции quiet не имеют. Имена grant* отклонены (глагол — take).
- `sendUpdateEvents(int)` / `sendUpdateEvents(List)` (список только dev-секция), `sendCollectionUpdated(id)`,
  `sendSectionEvents()` (sectionUpdated + notification); `convertSetCoins` сам шлёт collectionUpdated соседней.
- Базовый CollectionSectionType только мутирует (addItem, DEV_*), отправку решает наследник в
  абстрактных `onCollectionUpdated(int)` / `onCollectionsUpdated(List)` (сейчас оба наследника → sendUpdateEvents).
- Дубль take/sell танка с TrainPage.actionAccept/actionRefuse — принятый компромисс (#tradeoffs).
- `selected` оставлен как задел; persistence-слой (*Entry no-arg) не трогать.

## Открыто (было до запуска, закрыто выше)
- Имена push-маршрутов и операций секции; форма глушащего аргумента (Java без значений по умолчанию).
- Что слать при `refreshState` на входе в игру (`User.java:467`).
- Упрощение: секция эмитит `COLLECTION_SECTION_UPDATED` сама себе (CollectionsTypeSection:137-138,
  CollectionsExperimentalTanksSection:147, CollectionsUSSROperationsSection:235) — уходит само в этом этапе.

**Why:** пользователь хочет независимые асинхронные обновления без дублей и без клиентских эмитов.
**How to apply:** при запуске этапа дать это пайплайну как входные решения; код сейчас расходится с
ГДД `#gdd-exp-reward` (конвертация при «Получить», закрытие окна по фону) — это и есть объём этапа.
