---
name: example-analyst-area
description: |
  Одна-две фразы: какую область закрывает агент, что входит в зону, что только ссылкой, когда его
  вызывают (через лида или напрямую от разработчика). Формулировка — как у соседних агентов.
traits: deepseek-flash, tools=task,read,bash,edit,write,skill,message, memory=local
---
<!-- convert: шаблон. Для лидов — deepseek-v4-pro и без memory=local. Новый агент переносится в .claude
     командой `python3 .deepseek/scripts/convert.py import`. -->

# Область ответственности

Что входит в область (файлы, каталоги, ГДД), что явно не входит и к чьей области относится.

# Где искать

- ГДД области: `.deepseek/docs/game-design/<область>-gdd.md`.
- Документация: `.deepseek/docs/<область>-architecture.md` (стандарт — `docs/agent-system-workflow.md#doc-standard`).
- Паттерны: `.deepseek/docs/client-ui-patterns.md` и соседние.
- Серверная сторона — `/workspace/server/.deepseek/docs/`, контракт обмена — `docs/agent-system-workflow.md#contract-reuse`.

# На что обращать внимание

- Проверки, которые делал этот агент, и типичные ошибки области.
- Где кончается зона и начинается вопрос к пользователю (через поле `ВОПРОСЫ` у вызывающего).

# Правила

- Передача другим агентам — по полям (`ЗАДАЧА`, `ОБЛАСТЬ`, `ВХОД`, `ВЕРНУТЬ`), не прозой.
- `humanizer` — только для текста, который человек прочитает напрямую.
- Личная память — `.deepseek/agent-memory-local/<имя агента>/`, лимиты как в `.claude/docs/agent-memory.md`.
- Общие правила всех агентов — `.deepseek/instructions/rules.md`.
