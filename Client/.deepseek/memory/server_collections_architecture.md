---
schema: 1
name: server_collections_architecture.md
type: project
title: Указатель на серверную документацию коллекций (CollectionUserComponent, пакет model.collections)
source: .claude/memory/server_collections_architecture.md
claude: |
  name: server-collectionusercomponent
  description: "Указатель на серверную документацию коллекций (CollectionUserComponent, пакет model.collections)"
  metadata:
    node_type: memory
    type: reference
    created: 2026-09-28
    status: finalized
    originSessionId: 637dee09-ab33-4715-8e4d-28a211ede2b8
    modified: 2026-10-07T08:45:29.996Z
---

Документ: `/workspace/server/.claude/docs/collections-architecture.md`. Пакет
`com.linkedgames.game.model.collections` (перенесён из пакета `bag` 2026-10-05), роуты —
`CollectionPage`/`CollectionAlbumPage`/`CollectionExperimentalTankPage`.

Описано: Strategy на двух уровнях (секция/коллекция), персистентность плоскими entry-записями в Mongo
`collections`, ролл дропа, клейм комплекта и отложенный танк (`#pending-tank`), push
`setCompleted`, нотификация, сезон альбомов, dev-tools, TODO и закрытые решения (`#todo`).
Сверен с кодом 2026-10-07 (этап push: collectionUpdated/sectionUpdated/sectionRestarted, слой операций секции, quiet у альбомов, отложенный танк до take/sell, grantReward), открытых TODO нет.

Связи: решения 2026-10-05 — [[server-collections-fix-decisions-2026-10-05]]; клиент —
[[client-collections-profile-component]].
