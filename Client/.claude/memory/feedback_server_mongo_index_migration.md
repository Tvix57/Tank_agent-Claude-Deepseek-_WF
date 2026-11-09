---
name: feedback-server-mongo-index-migration
description: Server — при новой Mongo-коллекции/новом фильтре запроса сразу создавать JSON-миграцию индекса в том же изменении
metadata:
  node_type: memory
  type: feedback
  originSessionId: fe3dfa05-069a-4d45-b25e-6ff187d5f9f7
  modified: 2026-10-05T09:06:42.876Z
---

При добавлении новой Mongo-коллекции (новый `*Dao`) или нового фильтра запроса на сервере — сразу, в том же изменении, создавать миграцию индекса в `/workspace/server/game/src/main/resources/migrations/<timestamp_мс>_<имя>.json` (минимум `{ownerId: 1}` для документов на сущность).

**Why:** при разработке коллекций `CollectionDao` искал по `ownerId`, а индекс не был создан — пользователь заметил это сам (2026-10-05) и попросил, чтобы файл создавался сразу.
**How to apply:** правило закреплено в `/workspace/server/CLAUDE.md` и в агентах server-developer-db-persistence (раздел «Индексы и миграции» — первоисточник), server-developer-lead, server-developer-collections. Уникальные индексы — только по выбору пользователя (дубли в БД → `Migration` делает `System.exit`). См. [[server-collections-fix-decisions-2026-10-05]].
