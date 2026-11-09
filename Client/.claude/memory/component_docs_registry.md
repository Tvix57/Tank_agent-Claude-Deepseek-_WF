---
name: component-docs-registry
description: Реестры документации компонентов client и server — .claude/docs/component-docs-registry.md в каждом репозитории, владельцы *-librarian-lead
metadata:
  type: reference
---

Реестры: `/workspace/client/.claude/docs/component-docs-registry.md` (экраны/попапы `src/views/`,
утилиты, пресеты) и `/workspace/server/.claude/docs/component-docs-registry.md` (все `*UserComponent`
и области без компонента) — компонент → ссылка на документ, статус (обычный/auto-create/смешанный/
частично/нет), дата последнего обновления. Ведёт только `client-librarian-lead` / `server-librarian-lead`
соответственно (шаги — в файле агента, раздел "Реестр документации"); просмотр/обновление по запросу
пользователя — через них. Заведены 2026-10-13.
