---
name: reference-subagent-concurrency-limit
description: Лимит 20 одновременных субагентов — массовые задачи аналитикам запускать волнами, регистрацию у библиотекаря синхронно
metadata:
  type: reference
---

В Claude Code лимит одновременных субагентов — 20 (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), вложенные считаются. 2026-10-13: 14 аналитиков параллельно + каждый запустил `*-librarian-lead` в фоне → «Concurrent subagent limit reached», аналитики завершались без вердикта регистрации.

**How to apply:** при массовой задаче по многим документам — волнами так, чтобы (аналитики × 2) ≤ 20; в постановке требовать вызов библиотекаря синхронно (`run_in_background: false`). См. [[reference-subagents-no-ask-user]].
