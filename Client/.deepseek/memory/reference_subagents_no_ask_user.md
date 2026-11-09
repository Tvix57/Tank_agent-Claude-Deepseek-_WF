---
schema: 1
name: reference_subagents_no_ask_user.md
type: reference
title: "Субагенты не имеют AskUserQuestion (ограничение Claude Code) — вопросы идут полем ВОПРОСЫ через базовую сессию, правило #ask-relay"
source: .claude/memory/reference_subagents_no_ask_user.md
claude: |
  name: reference-subagents-no-ask-user
  description: Субагенты не имеют AskUserQuestion (ограничение Claude Code) — вопросы идут полем ВОПРОСЫ через базовую сессию, правило #ask-relay
  metadata:
    type: reference
---

Claude Code всегда убирает `AskUserQuestion` из инструментов субагента, `tools` во frontmatter не
помогает (code.claude.com/docs/en/sub-agents, «Available tools»; подтверждено 2026-10-13 и на
практике трижды). 2026-10-13 по решению пользователя закреплено правило
`agent-system-workflow.md#ask-relay` (оба репозитория): агент на развилке ставит паузу и возвращает
поле `ВОПРОСЫ`; базовая сессия спрашивает и продолжает тот же экземпляр через `SendMessage`;
предсказуемые вопросы (ГДД, создание агента) задаёт до запуска. `AskUserQuestion` убран из `tools`
всех агентов.

**How to apply:** после каждого возврата агента проверять поле `ВОПРОСЫ`; при новых агентах —
не добавлять `AskUserQuestion` в `tools`, ссылаться на #ask-relay.
