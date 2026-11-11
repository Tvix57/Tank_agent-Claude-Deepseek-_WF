# checkpoint.md — первое сообщение в сессии DeepSeek

Скопировать целиком в первое сообщение dsh (подставить репозиторий: `client` или `server`).

---

Прочитай целиком, прежде чем что-то делать (правила не пересказаны здесь — только где они лежат):

1. `AGENTS.md` в корне — правила проекта (сгенерированная копия `CLAUDE.md`).
2. `.deepseek/instructions/project.md` — те же правила в терминах `.deepseek`; расхождений с `AGENTS.md`
   быть не может (оба выводятся из `CLAUDE.md`).
3. `.deepseek/instructions/rules.md` — DeepSeek-часть: субагенты, скиллы, память, токены, запреты.
4. `.deepseek/instructions/contracts.md` — форматы памяти, документации, субагентов и скиллов.
5. `.deepseek/instructions/bridge.md` — карта `.claude` ↔ `.deepseek` (что чем заменяется).
6. `.deepseek/docs/agent-system-workflow.md` — только если задача входит в пайплайн команд.
7. `.deepseek/state/session_state.json` — `lastBranch`; что с ним делать (сверка с git-веткой, тип задачи)
   — `.deepseek/instructions/project.md`, раздел «Проверка ветки/сессии при старте».

Остальное — по ссылкам, без повторения текста: язык и вопросы — `.deepseek/instructions/project.md`; передача задачи субагенту,
`ВОПРОСЫ` и синхронность — `.deepseek/instructions/rules.md#subagents`; стандарт документации —
`.deepseek/docs/agent-system-workflow.md#doc-standard`; контроль токенов — `.deepseek/instructions/rules.md`, раздел «Контроль расхода
токенов»; правки только в рабочем коде (`src/` или `game/`) и в `.deepseek/`, `.claude/` не трогать —
`.deepseek/instructions/rules.md`, раздел «Что делать нельзя».

Текущая задача: <описание от пользователя>.
