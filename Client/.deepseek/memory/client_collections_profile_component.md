---
schema: 1
name: client_collections_profile_component.md
type: project
title: Указатель на клиентскую документацию 'Коллекции' (Профиль → Коллекции, тост CollectionCompletePopup, окно сравнения награды-танка, нотификатор наград) и её статус доверия
source: .claude/memory/client_collections_profile_component.md
claude: |
  name: client-collections-profile-component
  description: "Указатель на клиентскую документацию 'Коллекции' (Профиль → Коллекции, тост CollectionCompletePopup, окно сравнения награды-танка, нотификатор наград) и её статус доверия"
  metadata:
    node_type: memory
    type: reference
    category: Коллекции
    modified: 2026-10-07T08:44:24.005Z
    originSessionId: d78fd85a-0c8e-4b2a-a1b3-719d93241843
---

Документ: `/workspace/client/.claude/docs/collections-architecture.md` (8-пунктовый стандарт:
описание, референсы, паттерны, классы, оглавление, методы, компромиссы `#s8`).

Статус: базовая структура — auto-create (по коду); фичи «комплект собран» (`#set-completed-feature`),
окно сравнения награды-танка (`#cls-collectionexperimentaltank`), нотификатор (`#reward-notification`) — по итогам
реальной разработки. Весь документ сверен с кодом клиента 2026-10-07 и сервера 2026-10-05, этап "события шлёт сервер" реализован.

История контракта `collectionSetCompleted` (push вместо полей в summon, тост вместо модалки, очередь
попапов убрана) — во врезке `#set-completed-feature`; прежние описания в коде/памяти считать
устаревшими. Серверная сторона — [[server-collectionusercomponent]], общий контекст —
[[client-collection-section-hierarchy-draft]].
