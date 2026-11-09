# bridge.md — карта соответствия `.claude` и `.deepseek`

Одна страница: где что лежит и чем заменяется команда. Спецификация конвертера —
`../sync/CONVERSION.md`, инварианты — `../sync/INVARIANTS.md`.

## Раскладки

| `.claude` (Claude Code) | `.deepseek` (DeepSeek) | Преобразование |
|---|---|---|
| `CLAUDE.md` | `AGENTS.md` (в корне репозитория) | `.claude/` -> `.deepseek/`, `#gdd-x` -> `gdd-x`, `agent-system-workflow.md` -> `.deepseek/docs/...` |
| `CLAUDE.md` | `instructions/project.md` | то же плюс шапка «Источник» и хвост «вернуть к CLAUDE.md» |
| — | `CLAUDE.ds.md` | указатель для Claude Code при чтении из подкаталога |
| `.claude/agents/<g>/<a>.md` | `agents/<g>/<a>.md` | frontmatter `tools`/`model`/`memory` -> `traits` |
| `.claude/agents/<g>/.claude/agent-memory-local/<a>/` | `agent-memory-local/<a>/` | плоская копия без вложенного `.claude` |
| `.claude/skills/<s>/SKILL.md` | `skills/<s>/SKILL.md` | тот же текст, ссылки на `.claude/` -> `.deepseek/` |
| `.claude/skills/<s>/*` | `skills/<s>/*` | файл-в-файл |
| `.claude/docs/*.md` | `docs/*.md` | текст без изменений |
| `.claude/docs/game-design/incoming/*` | — | не переносится (исходники пользователя) |
| `.claude/memory/<name>.md` | `memory/<name>.md` | YAML-заголовок -> `schema/name/type/title/source/updated` |
| `.claude/memory/MEMORY.md` | `memory/MEMORY.md` и `memory/INDEX.md` | ссылки `./../docs/x` -> `.deepseek/docs/x` |
| `.claude/settings.local.json` (`hooks`) | `hooks.json` | `SessionStart` -> `session_start` и т.д. |
| `.claude/session_state.json` | `state/session_state.json` | копия |
| `.claude/scripts/*.py` | `scripts/*.py` | копия (кроме `convert.py`) |
| `.claude/exports/`, `.claude/worktrees/`, `checkpoints/` | — | не переносится (инфраструктура Claude Code) |

## Инструменты

| `.claude` (`tools` агента) | `.deepseek` (`traits`, `tools=`) |
|---|---|
| `Read` | `read` |
| `Bash` | `bash` |
| `Write` | `write` |
| `Edit` | `edit` |
| `Agent` | `task` |
| `Skill` | `skill` |
| `Grep` | `grep` |
| `Glob` | `glob` |
| `WebSearch` | `web_search` |
| `WebFetch` | `web_fetch` |
| `SendMessage` | `message` |
| `memory: local` | `memory=local` |

Инструмента без аналога (например, `AskUserQuestion`, `NotebookEdit`, `TodoWrite`) в `tools` у агентов
проекта нет. Появится — конвертер вынесет его в комментарий `<!-- convert: ... -->` вверху файла агента и
предупредит; молча терять инструмент нельзя.

## Модели

| `.claude` (`model`) | `.deepseek` (первый элемент `traits`) | Обратно (`import`) |
|---|---|---|
| `opus` | `deepseek-v4-pro` | `opus` |
| `sonnet` | `deepseek-flash` | `sonnet` |
| `haiku` | `deepseek-flash` | `sonnet` (haiku в Claude Code нет в тире) |
| `fable` | `deepseek-v4-pro` | `opus` |

Имена моделей — те, что принимает API DeepSeek (`api-docs.deepseek.com`); конкретную модель выбрать в dsh
в разделе Models — одна и та же может отдаваться разной версией. Правило выбора: лиды — `pro`,
специалисты — `flash`; обратное преобразование восстанавливает `opus` только для `pro`, чтобы
экономия на `flash` не расходилась с исходным бюджетом.

## Команды вместо слэш-команд Claude Code

| В Claude Code | В DeepSeek |
|---|---|
| `/agents` (список и вызов агентов) | прочитать `agents/**`, вызвать через `task`, сославшись на файл |
| `/clear`, `/compact` | сжатие контекста dsh (`compaction`), затем прочитать `instructions/checkpoint.md` |
| `CronCreate` / `CronList` / `CronDelete` | планировщик dsh (`schedule`); при отсутствии — ручной чек-лист `instructions/runtime.md#hooks` |
| `AskUserQuestion` | вопрос пользователю в чате (один зависимый вопрос — отдельным сообщением) |
| `Agent tool` (subagent_type) | `task` с типом = имя файла агента |
| `Skill` с `skill: "<имя>"` | чтение `skills/<имя>/SKILL.md` |
| `SendMessage` | `message` |
| хук `SessionStart`/`PreCompact` | `hooks.json`, поддержка проверяется в `instructions/runtime.md#hooks` |
| `memory: local` (агент) | `traits: memory=local` + `.deepseek/agent-memory-local/<агент>/` |
