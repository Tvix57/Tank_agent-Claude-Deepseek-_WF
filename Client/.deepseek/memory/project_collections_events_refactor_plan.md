---
schema: 1
name: project_collections_events_refactor_plan.md
type: project
title: Принятые решения по рефакторингу событий обновления коллекций (замена COLLECTION_EXPERIMENTAL_TANK_UPDATE) — запускать отдельной сессией через полный пайплайн
source: .claude/memory/project_collections_events_refactor_plan.md
claude: |
  name: project-collections-events-refactor-plan
  description: Принятые решения по рефакторингу событий обновления коллекций (замена COLLECTION_EXPERIMENTAL_TANK_UPDATE) — запускать отдельной сессией через полный пайплайн
  metadata:
    node_type: memory
    type: project
    originSessionId: 853a9bb5-3116-45aa-8a99-ea82f5d1a388
    modified: 2026-10-06T15:46:30.801Z
---

**СТАТУС: реализовано 2026-10-06 (сессия 2), сервер+клиент одобрены, доки обеих сторон обновлены; не закоммичено.**

Отдельный этап рефакторинга коллекций (решение пользователя 2026-10-06): запускать в НОВОЙ сессии
через полный пайплайн (librarians → integration-lead → server-developer-lead → одобрение →
client-developer-lead → integration-fix-reviewer → доки аналитиками). Решения ниже приняты
пользователем 2026-10-06 («брать как есть»); первая реализация была откатана из-за смешения с этапом
имён ([[feedback-naming-separate-from-refactor]]), код пишется заново на именах после коммита
переименований (client 05c0a903, server 8d6752e).

## События (client `GameEvents`)
- `COLLECTION_EXPERIMENTAL_TANK_UPDATE` удаляется; вместо него `COLLECTION_UPDATED: EventName<number>`
  (collectionId) и `COLLECTION_SECTION_UPDATED: EventName<number>` (section). Не `COLLECTION_SET_*`
  (`set` = «набор собран»).
- Событие несёт только номер; подписчик сам запрашивает данные и перерисовывает только себя:
  коллекция → `/getCollection` (всем полная форма `fullApiResponse`); секция → новый
  `/ingame/collections/getSectionProgress {section}` (JSON секции без `collections`, сервер:
  `progressApiResponse()` у типа секции, `sectionProgressApiResponse(section)` у компонента).
- Гонки: у подписчика побеждает последний запрос.
- Сбор ранга танков → `COLLECTION_UPDATED(свой)`, `COLLECTION_UPDATED(nextRankItem.collectionInfo.id)`,
  `COLLECTION_SECTION_UPDATED(section)`.

## Клиент
- Подписки в базовых `Collection` (по id → `/getCollection` → `this.data = response`) и
  `CollectionsTypeSection` (по section → `/getSectionProgress` → влить шапку, список не трогать).
  Без кастов к подтипу (через существующие `getCollectionData()`/`getSectionData()`; generic отклонены).
- `CollectionSectionJSON.collections?:` необязательное, наследники переопределяют обязательным.
- Танки: карточки всех наций создаются один раз, смена нации — показ/скрытие; вкладки и прогресс
  шапки — из серверного `countries`.
- Альбомы: плитка становится компонентом-наследником `Collection`; открытый альбом тоже слушает
  событие. Dev-кнопки шлют те же события; `devRequest` проверяет `ResultUtils.isOk`.

## Контракт (breaking, выкатка синхронная)
- `/getSection` танков: + `countries: [{country, completed, total, notified}]` (completed — число
  коллекций нации с `everCompleted`, total — число коллекций нации, notified — any), порядок
  детерминированный (`Country.ALL`).
- `/experimentalTank/getCollectionReward` → `{reward, isRewardPending, nextRankItem}`;
  `/takeReward`, `/sellReward` → `{collectionId, rewards}`; `/markCollectionItemViewed` без изменений
  (клиент шлёт `COLLECTION_SECTION_UPDATED`, локально `notified` не патчит).
- `/album/getCollectionReward` → `{reward}`; `/album/getSectionReward` → `{reward}`;
  `/album/getAllRewardInSection` → `{rewards, collectionIds}` (альбомы, где реально забрана стадия).
- dev коллекций → пустой ok; dev секций → `{collectionIds}` (все коллекции секции).
- Новый push `/events/collections/sectionRefreshed {section, collectionIds}` (все коллекции секции)
  при фактическом рестарте сезона в `CollectionUserComponent.refreshState`.
- Устаревших полей на время выкатки не оставлять.

## Добавлено в этап (решение пользователя 2026-10-06)
- Условие кнопки награды стадии секции на клиенте (`sectionRewardedStage == index && sectionStars >=
  stageStars` в `CollectionsUSSROperationsSection`) дублирует серверное `isSectionStageRewardAvailable` —
  убрать дубль новым признаком в JSON секции (форму поля согласовать в этапе).

## Уточнения после сверки integration-lead (решения пользователя 2026-10-06, сессия 2)
- ГДД `#gdd-ops-rewards` дополнен: стадии строго по порядку, кнопка на плитке альбома, кнопка на
  стадии шкалы секции, «Собрать всё».
- Признак награды стадии секции: `availableSectionStage: number | null` (ближайшая незабранная
  стадия, если звёзд хватает; иначе null). На сервере — одна функция этого правила, ей же проверять
  очередь в `getSectionReward` (сейчас очередь отдельно в Page). Клиент рисует кнопку по полю.
- Альбомы НЕ переводить на такую форму: остаются `hasAvailableReward` + `rewardedStage`.
- `countries`: нации с total=0 пропускать. `countries` в коде сейчас НЕТ.
- `sectionRefreshed` слать и при первом старте сезона (прежний endTime == 0).
- `/album/getAllRewardInSection` — ОТМЕНА пункта спеки: остаётся `{rewards, data}` с подменой
  данных секции (подтверждено явно, с последствиями: исключение из схемы событий, полная перерисовка).
- Summon (TrainPage, dev `/collectionSummon`): клиент после ответа шлёт COLLECTION_UPDATED/SECTION_UPDATED.
- Карточки наций «один раз» (show/hide вместо пересоздания в `showCountry`) — В ЭТОМ этапе.
- Плитка альбома — `CollectionAlbumCard` (наследник `Collection`).

## Клиент: схема обновления и имена (решения пользователя 2026-10-06, сессия 2)
- Эмит — инлайн `GameEvents.emitter.emit(...)`, без хелперов; после summon/dev summon/nextRankItem —
  два инлайн-эмита в каждом месте (summon — в `HomeScreen.OnTrainSummon`/`DevOnTrainCollect`).
- Карточка (база `Collection`): `onCollectionUpdated(id)` → `refreshCollection()` (/getCollection) →
  `this.data` → свой `onCollectionDataUpdated()` перерисовывает только карточку. В секции этого метода нет.
- Секция (база `CollectionsTypeSection`): `onSectionUpdated(section)` → `refreshSectionProgress()`
  (/getSectionProgress) → `updateSectionData` (влить, `collections` сохранить) → `onSectionDataUpdated()`
  — ТОЧЕЧНО, только области секции (прогресс/вкладки наций, шкала/награда секции), не весь экран.
- Полное обновление секции — новый `reloadSection(data)`, как открытие из списка секций; использует
  «Собрать всё» (`{rewards, data}`).
- Танки: слои наций — дочерние `"country" + id`, переключение `visible`; `getCountryProgress(country)`.
- Типы: `CollectionExperimentalTanksCountryJSON`; ответ /getSectionProgress — `CollectionSectionJSON`;
  `CollectionSectionRefreshedJSON`; dev `{collectionIds}` — инлайн-литерал; ответы `{reward}` альбомов — `any`.
- `CollectionAlbumCard` в `collection_type/CollectionAlbumCard.ts`, методы `UITitle/UIButton/UIProgress/UIReward`.

**Why:** решения уже приняты пользователем; без записи потерялись бы со scratchpad сессии.
**How to apply:** при запуске этапа событий — дать спеку пайплайну как входные решения, не
переспрашивать принятое; открытые пункты — через AskUserQuestion. Сведение дублей ГДД и `findRank`
сделаны отдельно 2026-10-06 (см. [[project-collections-refactor-candidates]]).
