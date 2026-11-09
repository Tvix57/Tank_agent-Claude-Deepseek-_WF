# CONVERSION.md — спецификация конвертера `.claude` ↔ `.deepseek`

Источник истины для поведения `scripts/convert.py`. Меняется вместе со скриптом; расхождение текста и
кода — баг, его ловит `scripts/selftest.py`.

## Команды

| Команда | Что делает | Когда вызывать |
|---|---|---|
| `export [--force]` | `.claude` -> `.deepseek`, генерируемые файлы целиком | перед сессией dsh; после правки `.claude` |
| `import [--force]` | `.deepseek` -> `.claude`: документы, память, обслуживаемые служебные | после работы в DeepSeek, перед возвратом |
| `check [--strict]` | по каждому файлу `ok/changed/new/missing` | перед переключением режима; в CI с `--strict` |
| `drift [--strict]` | отстал ли снимок, тронуты ли ручные файлы, нет ли `.deepseek`-ссылок в `.claude` | после `export`, как сторож |
| `sync-agents --direction to_dz\|to_claude` | сравнение агентов двух раскладок: чего нет в назначении и где правила расходятся | только по запросу Пользователя |
| `status` | счётчики и состояние синхронизации | для отчёта |

Флаги: `--repo <корень>` (по умолчанию — два уровня выше скрипта), `--force` (писать при совпадении,
перезаписывать конфликты в `import`), `--strict` (код возврата 1 при расхождениях). Код 0 — успех.
Для `sync-agents` — `--direction`, `--apply`, `--yes` (см. ниже).

## Перенос агентов с подтверждением {#sync-agents}

`sync-agents` запускается **только по запросу Пользователя**, никогда автоматически из `export`/`import`.
По умолчанию — пробный прогон, файлы не меняются:

```bash
python3 .deepseek/scripts/convert.py sync-agents --direction to_dz       # .claude -> .deepseek, только план
python3 .deepseek/scripts/convert.py sync-agents --direction to_claude   # .deepseek -> .claude, только план
```

Порядок работы:

1. **Чего нет в папке назначения** — печатается `СОЗДАТЬ`. Файл берётся из источника как основа и
   переводится в правила назначения (`convert_agent_to_dz` / `convert_agent_to_claude`: пути, `model`/
   `traits`, `tools`, `memory`, `cacheTtl`). Создание происходит только с `--apply --yes`.
2. **Файл с таким именем уже есть** — печатается `ОТЛИЧИЯ`: строки правил источника, которых нет в
   назначении (`+`), и строки назначения, которых нет в источнике (`-`). Сравнивается тело без
   frontmatter, после приведения к системе назначения, поэтому разница форматов `traits`/`tools` за
   отличие не считается.
3. **Применение отличий — после одобрения Пользователем.** Без пары `--apply --yes` команда возвращает
   код 2 и ничего не пишет:

   ```bash
   python3 .deepseek/scripts/convert.py sync-agents --direction to_dz --apply --yes
   ```

Итоговая строка: `создать N, с отличиями M, без отличий K`. При `--apply` создаются отсутствующие
агенты; отличия в существующих файлах правятся вручную по одобренному списку, по одному файлу.

## Исключения git

`.deepseek/` и `AGENTS.md` в корне — служебные файлы контура, как `.claude/` и `CLAUDE.md`: их исключают
через `.git/info/exclude` репозитория (не `.gitignore` — это локальная настройка репозитория, а не общий
файл проекта):

```text
# deepseek-runtime (страховочный контур, зеркало .claude)
.deepseek/
AGENTS.md
```

Проверка: `git check-ignore -v .deepseek AGENTS.md` называет эти строки, `git status --porcelain` их не
показывает. Следит за этим `selftest.py` (инвариант 12): строк нет — код 1. Исключения действуют только
в этом рабочем каталоге; при клонировании репозитория в другом месте их нужно добавить заново.

## Что конвертируется

`agents/`, `skills/`, `docs/`, `memory/`, `settings.local.json` (-> `hooks.json`), `session_state.json`
(-> `state/session_state.json`), `scripts/*.py` (копии, кроме конвертера).

Не конвертируется: `checkpoints/`, `worktrees/`, `exports/`, `mailbox/`, `agent-registry.json`,
`first-run`, `assistant-daemon-state.json`, `__pycache__`, `docs/game-design/incoming/`.

## Ручные и генерируемые

Генерируемые несут `<!-- GENERATED` в первых 4000 байт: `AGENTS.md` и `CLAUDE.ds.md` в корне,
`instructions/project.md`, `agents/`, `skills/`, `docs/`, `memory/`, `hooks.json`,
`state/session_state.json`, `scripts/*` (копии). `schema.yml` и строки журнала `sync/STATE.md` пишет
конвертер, заголовка у них нет.

Ручные не перезаписываются никогда: `README.md`, `instructions/{bridge,contracts,rules,runtime,invariants,checkpoint}.md`,
`sync/*.md`, `scripts/convert.py`, `scripts/selftest.py`, `notes/`, `agent-memory-local/`.

Если ручной файл получил заголовок `<!-- GENERATED`, `drift` сообщает о поломке; файл восстанавливается из git.

## Агенты {#agents}

Прямое преобразование (`export`):

```yaml
# .claude/agents/analysts/client-analyst-bag.md  ->  # .deepseek/agents/analysts/client-analyst-bag.md
name: client-analyst-bag                            name: client-analyst-bag
description: |                                      description: |
  ...                                                 ...
tools: Agent, Read, Bash, Edit, Write, Skill, SendMessage
model: sonnet                                       traits: deepseek-flash, tools=task,read,bash,edit,write,skill,message
memory: local
experimental: {cacheTtl: 1h}                        # experimental не переносится: кэш — настройка dsh
```

- `tools` — по таблице `bridge.md#инструменты`; дубликаты убираются; инструмент без аналога попадает в
  комментарий `<!-- convert: ... -->` вверху файла (молча терять нельзя).
- `model` -> первый элемент `traits` по таблице `bridge.md#модели`; неизвестная модель -> `deepseek-flash`.
- `memory: local` -> `memory=local`.
- Тело: `](.../.claude/...)` -> `](.../.deepseek/...)`, `#gdd-x` -> `gdd-x`, `agent-system-workflow.md` ->
  `.deepseek/docs/agent-system-workflow.md`.
- `.claude/agents/**/.claude/agent-memory-local/**` -> `.deepseek/agent-memory-local/**` без вложенного `.claude`.
- Файлы, имя которых начинается с `_` (`agents/_TEMPLATE.md`), конвертер не трогает в обе стороны:
  это шаблоны. Новый агент копируется из шаблона под рабочим именем.

Обратное (`import`) — создаёт в `.claude` агентов, которых там ещё нет (из `.deepseek/agents/**` в
`.claude/agents/**`, `traits` -> `tools`/`model`/`memory`, `pro`->`opus`, `flash`->`sonnet`; `cacheTtl` не
восстанавливается). Существующий `.claude`-агент не перезаписывается (источник — `.claude`; `--force`
снимает запрет). Память агентов (`.deepseek/agent-memory-local/**`) обратно не переносится: для этого
служит `notes/` (см. ниже).

## Скиллы

`SKILL.md` — тот же YAML (`name`, `description`), тело переводится теми же заменами; остальные файлы
скилла копируются байт-в-байт. У сервера `skills/{glossary,naming,writing-for-agents}` — симлинки на
`client`: конвертер их разыменовывает в файлы и обратно не симлинкует.

## Документация

Текст копируется без изменений: относительные ссылки между документами совпадают в обеих раскладках.
Для документов со ссылками на `agent-system-workflow.md` и `#gdd-...` действуют те же замены. Источник
истины — `.claude`; `import` переносит текст в обе стороны, потому что документ может родиться в DeepSeek.

## Память

```yaml
# .claude/memory/feedback_no_verbose_java_comments.md  ->  # .deepseek/memory/feedback_no_verbose_java_comments.md
name: feedback-no-verbose-java-comments                     schema: 1
description: "…"                                            name: feedback_no_verbose_java_comments.md
metadata:                                                   type: feedback
  node_type: memory                                         title: "Правило: …"   # из description до первой точки
  type: feedback                                            category: Общие правила проекта
  category: Общие правила проекта                           source: .claude/memory/feedback_no_verbose_java_comments.md
  originSessionId: …                                        updated: 2026-09-19T05:00:23.711Z
  modified: 2026-09-19T05:00:23.711Z                         <тело без изменений>
```

- `name` = имя файла с `_`: по нему `import` узнаёт файл, который уже был в `.claude`, и не пересобирает его.
- `schema: 1` — маркер формата DeepSeek; файл без него при `import` считается новым и собирается в YAML.
- `MEMORY.md` — индекс переписывается (`./../docs/x` -> `.deepseek/docs/x`, `./x.md` -> `.deepseek/memory/x.md`);
  копия индекса целиком лежит в `memory/INDEX.md` — её читает человек в браузере.
- `import`: файл со `schema: 1` собирается обратно в YAML `.claude` (добавляется `converted-from`, если был
  `source`); расхождение с существующим файлом без `--force` не перезаписывается и попадает в отчёт.

## Заметки и личная память агентов

`.deepseek/notes/<дата>-<тема>.md` — то, что в `.claude` пишется в личную память агента. Формат
(`title`, `agent`, раздел `## Запись`) — `notes/TEMPLATE.txt`. `import` переносит заметку в
`.claude/agents/.claude/agent-memory-local/<agent>/deepseek_<файл>.md` и добавляет строку в `MEMORY.md`
этого агента. Обратного автоматического переноса нет: `.claude`-память агентов остаётся источником,
`import` её не читает.

## Служебное

- `hooks.json`: `{"schema": 1, "events": [{"event": "pre_compact", "matcher": "auto", "type": "command",
  "command": "…"}]}`; обратно — группировка по `matcher` в формат `settings.local.json`.
- `state/session_state.json` — копия; `import` возвращает `lastBranch`.
- `schema.yml` — версия схемы и дата последнего экспорта.
- `sync/STATE.md` — журнал; его дописывают все команды, верхнюю часть правят руками.

## Чего конвертер не делает

- Не переносит `.claude/exports/` (бэклоги, черновики) и `.claude/worktrees/`.
- Не меняет код (`src/`, `game/`) и ссылки на документацию в коде.
- Не разрешает конфликты содержательно: «changed» — сигнал, кому верить; решает человек или агент по
  `POLICY.md#конфликты`.

