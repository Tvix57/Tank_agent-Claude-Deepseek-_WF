---
name: project-agent-model-assignment
description: "Решение 2026-09-29 о моделях (model: во frontmatter) агентов client/server — haiku/sonnet/opus по ролям, разработчики на opus по выбору пользователя"
metadata:
  node_type: memory
  type: project
  originSessionId: 5881e60a-9105-4c91-b276-ed2f0df52045
  modified: 2026-09-29T06:20:45.960Z
---

Раскладка `model:` агентов в `.claude/agents/<команда>/*.md` обоих репозиториев (решение 2026-09-29, вместо `inherit`):
- **haiku** — все библиотекари, кроме `web-librarian`;
- **sonnet у `web-librarian`** — явное решение пользователя 2026-10-08 (подтверждено после напоминания о haiku): нужен отбор внешних источников и оценка плюсов/минусов;
- **sonnet** — аналитики областей (`*-analyst-<область>`), `integration-contract-analyst`, `integration-lead`;
- **opus** — `*-analyst-lead`, `integration-fix-reviewer`, все разработчики (`*-developer-lead`, `*-developer-collections`, `server-developer-db-persistence`);
- fable — никому в frontmatter. Исключение (решение 2026-09-29): первичный анализ НОВОЙ области `*-analyst-lead` базовая сессия вызывает разово с `model: "fable"` в Agent tool; все следующие вызовы лида — на opus из frontmatter. Правило записано в `.claude/docs/agent-system-workflow.md` (шаг 2) и в файлах обоих лидов. Новым специалистам-аналитикам — sonnet.

**Why:** баланс токенов и качества — Opus там, где проектирование/суждение/цена ошибки; Sonnet на частых точечных запросах по готовой документации. Разработчиков предлагали перевести на sonnet, пользователь явно выбрал оставить opus (правила проекта: src/ee/, касты, рефлексия, персистентность — цена переделок).

**How to apply:** новым агентам назначать модель по той же роли; не предлагать снова понижать разработчиков без данных (`token_usage_check.py`, частота возвратов на доработку).
