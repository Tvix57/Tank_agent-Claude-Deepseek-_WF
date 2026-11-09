# checkpoint.md — первое сообщение в сессии DeepSeek

Скопировать целиком в первое сообщение dsh (подставить репозиторий: `client` или `server`).

---

Прочитай целиком, прежде чем что-то делать:

1. `AGENTS.md` в корне — правила проекта (это копия `CLAUDE.md`).
2. `.deepseek/instructions/project.md` — те же правила в терминах `.deepseek`, плюс запрет на правку
   `.claude` в DeepSeek-режиме.
3. `.deepseek/instructions/rules.md` — язык, вопросы, противоречия, память, субагенты.
4. `.deepseek/instructions/contracts.md` — форматы памяти, документации, субагентов и скиллов.
5. `.deepseek/instructions/bridge.md` — карта `.claude` ↔ `.deepseek` (что чем заменяется).
6. `.deepseek/docs/agent-system-workflow.md` — только если задача входит в пайплайн команд.
7. `.deepseek/state/session_state.json` — `lastBranch`; сравни с текущей git-веткой. Ветка другая —
   уточни тип задачи (новая фича / расширение / баг), потом обнови `lastBranch`.

Правила ответа:

- Отвечай по-русски, субагентам тоже передавай требование русского ответа.
- Выбор между вариантами — только пользователю: один вопрос за раз, зависимые — отдельными сообщениями.
- Правки только в рабочем коде (`src/` или `game/`) и в `.deepseek/`. `.claude/` не трогать.
- Документация регистрируется через `.deepseek/agents/librarians/*-librarian-lead.md`, стандарт —
  `.deepseek/docs/agent-system-workflow.md#doc-standard`.
- Перед фиксацией решения сверься с ГДД области и с уже принятыми решениями по этой области.
- Контроль токенов: при входе в пайплайн — `python3 .deepseek/scripts/token_usage_check_dsh.py 3600`,
  разбор ответа — `.deepseek/instructions/rules.md`, раздел «Контроль расхода токенов» (периодичность —
  `schedule` dsh; `CronCreate` здесь нет).

Текущая задача: <описание от пользователя>.
