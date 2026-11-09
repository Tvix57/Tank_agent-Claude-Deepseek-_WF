---
name: feedback-server-db-persistence-boundary
description: "Server (/workspace/server): при выносе логики из UserChildComponent в Strategy/helper-классы, которые не Component — changedField физически недоступен helper-у; два рабочих пути — raw-accessor делегирование ИЛИ своя entry-персистентность у helper-а (как у коллекций)."
metadata:
  node_type: memory
  type: feedback
  category: Коллекции
  originSessionId: af86a59c-955a-4daf-ab5c-7ab911aa2ec4
  modified: 2026-09-20T12:59:49.907Z
---

# Правило: границы персистентности при рефакторинге в Strategy на сервере

Когда пользователь просит вынести бизнес-логику из `UserChildComponent`
(например, `CollectionUserComponent`) в отдельные Strategy/helper-классы,
которые НЕ являются `Component`/`UserChildComponent` (живут в другом пакете,
как `sectionList/*`, `itemList/*`) — **саму механику персистентности (поля
хранения + запись в БД) вынести туда НЕЛЬЗЯ технически**, только бизнес-логику
поверх неё.

**Почему**: `changedField(String, Object)` определён в
`commons/src/main/java/com/linkedgames/commons/comp/Component.java` как
`protected final` — вызвать его можно только изнутри самого `Component`/его
подкласса. Обычный POJO в другом пакете (даже с публичным полем `owner:
CollectionUserComponent`) физически не может дёрнуть `owner.changedField(...)`
— компилятор не даст (protected + другой пакет). Реальная сборка Mongo
`WriteModel` идёт позже, через `dbFetchChanged()`.

Также: `dbMappingBuild(document)` вызывается РОВНО ОДИН РАЗ — при инициализации
пользователя (`ActorInitializationTask` → `User.dbMappingBuild` →
`getXxxUserComponent().dbMappingBuild(...)`). Сам `UserChildComponent`
(например, `CollectionUserComponent`) — session-long singleton (ленивый
геттер на `User`, кэшируется на всё время сессии Akka-актора), а НЕ
пересоздаётся на каждый запрос.

**Как применять** — раз helper-класс физически не может дёрнуть
`changedField`, есть ДВА рабочих пути (какой брать — решает пользователь,
спросить заранее):
1. **Raw-accessor делегирование**: поля хранения и `changedField` остаются
   на самом `Component`, helper получает только узкие public-геттеры/сеттеры
   одного поля без бизнес-логики, вся формула — в Strategy-классе поверх них.
2. **Собственная персистентность у helper-а**: helper заводит свою запись
   (свой `_id`/`ownerId`, свой `dbFetchChanged()`/`dbMappingBuild`) в общей
   Mongo-коллекции, по тому же паттерну, что уже используют `BagItem`/
   `AchievementEntry`/`CodexEntry` — `Component` тогда просто агрегирует
   вызовы `dbFetchChanged()` у своих helper-ов, сам не хранит ничего из их
   состояния. **Так в итоге и сделано для коллекций** — см.
   [[client-collection-section-hierarchy-draft]] и
   `/workspace/server/.claude/docs/collections-architecture.md`: `Collection`/
   `CollectionSectionType` вообще не вызывают `changedField`, у каждого своя
   entry-запись (`CollectionEntry`/`CollectionSectionEntry`) с локальным
   `markAsDirty()`.

Не пытаться "исправить" это через рефлексию или каст к protected — оба пути
запрещены отдельными правилами ([[feedback_no_reflection_server]], CLAUDE.md
про каст к приватным полям).
