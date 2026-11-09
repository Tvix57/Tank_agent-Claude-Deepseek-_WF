---
name: project-collections-refactor-candidates
description: "Кандидаты этапа рефакторинга структуры коллекций (после этапа имён 2026-10-06) — findRank, миграция notified, COLLECTION_EXPERIMENTAL_TANK_UPDATE, события обновления"
metadata:
  node_type: memory
  type: project
  originSessionId: 853a9bb5-3116-45aa-8a99-ea82f5d1a388
  modified: 2026-10-06T14:43:42.799Z
---

Этап имён коллекций выполнен 2026-10-06 (без коммита). Структурные правки отложены в отдельный этап
по правилу [[feedback-naming-separate-from-refactor]]:

Сделано 2026-10-06 (рефакторинг напрямую, без коммита на момент записи):
- `findRank()` удалён, вызовы → `findExperimentalTankRank()`.
- Правило «стадия пройдена и не выдана» сведено в `isCollectionStageRewardAvailable` /
  `isSectionStageRewardAvailable`; `completed` альбома — серверный, в краткой форме `apiResponse()`.
- Две одинаковые отрисовки шкалы стадий (`CollectionAlbum` и шапка `CollectionsUSSROperationsSection`) —
  ОСТАВЛЕНЫ дубликатом по решению пользователя; не предлагать сведение повторно без запроса.

Осталось:
1. Поле записи `notified` (было `notyfied`) — без Mongo-миграции, тестовая БД очищается; для живой БД
   нужен `$rename notyfied → notified` (пользователь в этап не включил).
2. ~~Этап событий~~ — РЕАЛИЗОВАН 2026-10-06 через полный пайплайн (код обеих сторон не закоммичен
   на момент записи, ручной прогон в игре не делался); решения — [[project-collections-events-refactor-plan]].

**Why:** пользователь разделил переименования и рефакторинг на разные этапы.
**How to apply:** при старте этапа рефакторинга коллекций предложить этот список пользователю на выбор.

**2026-10-13 — работа над коллекциями объявлена пользователем завершённой.** Доки обеих сторон
финально сверены аналитиками, ссылки на доки из кода удалены (client 22, server 85 строк). Незакрытое
(предлагать только при новой задаче по коллекциям): миграция `notified`; ClassCastException при
документе сумки `t = 3` в `BagUserComponent.dbMappingChildBuild` (фильтр или миграция — решает
пользователь).
Мёртвый код `Balance.collectionItemIsAvailable`/`getCollectionItemsId` (server) удалён 2026-10-23.
