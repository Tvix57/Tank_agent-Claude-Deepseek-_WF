---
schema: 1
name: reference_military_base_architecture.md
type: reference
title: Серверный док области «Военная база» (MilitaryBaseUserComponent) — путь, статус auto-create, дата 2026-10-22; открывать при задаче по военной базе/авиазаводу
source: .claude/memory/reference_military_base_architecture.md
claude: |
  name: military-base-architecture
  description: "Серверный док области «Военная база» (MilitaryBaseUserComponent) — путь, статус auto-create, дата 2026-10-22; открывать при задаче по военной базе/авиазаводу"
  metadata:
    node_type: memory
    type: reference
    originSessionId: fd6d858f-99c1-43c3-90d3-ec53e1b9dfc6
    modified: 2026-10-22T06:06:07.767Z
---

Док: `/workspace/server/.claude/docs/military-base-architecture.md` (server).

Статус: auto-create — составлено аналитиками задним числом по результатам сканирования кода, не в процессе разработки. Доверять с осторожностью, перепроверять по актуальному коду.

Дата: 2026-10-22, ветка `koba/collection`, отправитель `server-analyst-lead`. Проверка по стандарту и покрытию пройдена лидом. Запуском не проверялось, только чтение кода.

ГДД: [military-base-gdd.md](/workspace/client/.claude/docs/game-design/military-base-gdd.md) (согласован, зарегистрирован 2026-10-22); открытые противоречия — `#gdd-open`. Клиентский док: `/workspace/client/.claude/docs/military-base-architecture.md`; контракт сверяет `integration-lead`.

Связано: [[aerodrome-deferred-fixes]] (призыв самолёта переехал в военную базу), [[server_collections_deferred_fixes]] (id `MILITARY_BASE_*` в ItemType).

**How to apply:** перед выводами о поведении военной базы сверять с кодом `MilitaryBaseUserComponent`; не считать док истиной без проверки.
