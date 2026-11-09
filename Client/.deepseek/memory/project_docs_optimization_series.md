---
schema: 1
name: project_docs_optimization_series.md
type: project
title: Серия оптимизации документов компонентов (с 2026-10-13) — по одному документу, следующий только после одобрения пользователя
source: .claude/memory/project_docs_optimization_series.md
claude: |
  name: project-docs-optimization-series
  description: "Серия оптимизации документов компонентов (с 2026-10-13) — по одному документу, следующий только после одобрения пользователя"
  metadata:
    node_type: memory
    type: project
    originSessionId: 2c59b490-c034-488f-8e86-6a2aa77b2a46
    modified: 2026-10-13T17:48:52.699Z
---

Оптимизация `*-architecture.md` через аналитика области: сверка с кодом, дубли, пересказ ГДД и других
документов, кэш окружения, пустые фразы; затем регистрация у `*-librarian-lead`.

Порядок: коллекции client → server, достижения client → server, сумка client → server, кодекс
client → server, пресеты (items, panels-buttons), server: airdrop, assembly, quests, tutorial,
tank-airplane-data.

**Why:** пользователь хочет проверять результат каждого документа сам и не упираться в лимиты.
**How to apply:** после итогов документа показать результат и ждать явного одобрения; без него следующий
документ не запускать. Связано: [[reference_subagent_concurrency_limit]].

Прогресс на 2026-10-14: готовы коллекции (client, server), достижения (client, server), сумка (client,
server), кодекс client. Перед серверным кодексом пользователь переключился на создание новой
документации (client «Сборка»); к оптимизации вернуться, когда пользователь скажет.
