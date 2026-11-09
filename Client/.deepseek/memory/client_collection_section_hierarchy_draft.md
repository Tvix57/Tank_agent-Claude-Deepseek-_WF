---
schema: 1
name: client_collection_section_hierarchy_draft.md
type: project
title: "Кросс-репо контекст коллекций (client+server, ветка koba/collection): стиль работы пользователя и отклонённые варианты архитектуры, которых нет в документах"
source: .claude/memory/client_collection_section_hierarchy_draft.md
claude: |
  name: client-collection-section-hierarchy-draft
  description: "Кросс-репо контекст коллекций (client+server, ветка koba/collection): стиль работы пользователя и отклонённые варианты архитектуры, которых нет в документах"
  metadata:
    node_type: memory
    type: reference
    category: Коллекции
    originSessionId: af86a59c-955a-4daf-ab5c-7ab911aa2ec4
    modified: 2026-10-05T11:01:48.334Z
---

Механика реализована и работает на обеих сторонах. Источники истины (здесь не дублировать):
- клиент — `/workspace/client/.claude/docs/collections-architecture.md`;
- сервер — `/workspace/server/.claude/docs/collections-architecture.md` (включая TODO/закрытые решения);
- бизнес-логика — `.claude/docs/game-design/collections-gdd.md` (заменяет прежний пересказ ТЗ).

Стиль работы: пользователь двигается **строго по шагам, которые сам указывает** — соседние файлы без
указания не трогать, но если правка ломает компиляцию — чинить, не оставлять сломанным.

## Отклонённые варианты (не предлагать повторно без явного запроса)

- Полиморфное создание `COLLECTION_ITEM` через persisted поле-дискриминатор — различаем по
  `collectionId` → секция; рефлексия запрещена ([[feedback_no_reflection_server]]).
- Generic `CollectionsTypeSection<T>`/`Collection<T>` на клиенте — выбран абстрактный
  `getSectionData()`/`getCollectionData()`.
- Вложенный `CollectionExperimentalTanksJSON.qualities[]` — плоская модель: нация = несколько записей.
- Отдельный `ItemType.EXPERIMENTAL_TANK_COIN_ITEM` и подклассы `CollectionItem` — монета и фото один
  класс навсегда; поведение по виду предметов — в наследниках `Collection`.
- Звёзды/прогресс-бар/light-full сплит для танков и поля `quality`/`rank`/`rewarded`/`coins` в
  отдельном виде — у танков только `items` (+ серверные `rank`/`notified`/`reward`/`tank`…).
- Методы, нужные одному наследнику Strategy, в абстрактном классе (даже default) — правило
  описано в серверном доке `#strategy-sectionlist`; `isComplete`/`hasAvailableReward` живут в
  `Collection`, не делегатами через секцию.
- Пересоздание секций/коллекций на каждый вызов — синглтоны на пользователя.

Связанное: [[feedback_server_db_persistence_boundary]] (свои entry-записи вместо `changedField`),
[[feedback_no_verbose_java_comments]], [[server-collections-fix-decisions-2026-10-05]].
