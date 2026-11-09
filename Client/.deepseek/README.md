# `.deepseek` — страховка на случай блокировки Claude Code

Каталог живёт рядом с `.claude` и содержит то же самое в терминах DeepSeek Harness (dsh): инструкции
проекта, команды агентов, скиллы, документацию и память. Назначение — если Claude Code недоступен,
продолжить ту же работу в DeepSeek без пересказа контекста, а когда Claude Code вернётся, слить
накопленное обратно без потерь.

Это **временная** страховка: основной источник истины — `.claude`, здесь хранится снимок, а не вторая
жизнь проекта. Пока `.deepseek` не используется в работе, `.claude` остаётся нетронутым.

## Быстрый старт (Claude Code недоступен)

```bash
cd /workspace/<client|server>
python3 .deepseek/scripts/convert.py export --force   # свежий снимок .claude -> .deepseek
python3 .deepseek/scripts/convert.py check            # ноль «changed» — снимок полный
git switch -c <ветка>-deepseek                        # работа в той же ветке (см. sync/POLICY.md)
dsh web                                               # DeepSeek Harness, рабочий каталог — этот репозиторий
```

Первым сообщением в сессии dsh:

> Прочитай `AGENTS.md`, затем `.deepseek/instructions/runtime.md` и `.deepseek/docs/agent-system-workflow.md`.
> Раскладка — `.deepseek`: агенты из `.deepseek/agents/`, скиллы из `.deepseek/skills/`.

Готовое сообщение целиком — `instructions/checkpoint.md`. Дальше порядок тот же, что был в Claude Code:
библиотекари → аналитики → разработчики, «решение всегда за пользователем», документация регистрируется
через лида библиотекарей.

## Пока Claude Code работает

Снимок держится свежим одной командой — до и после сессии:

```bash
python3 .deepseek/scripts/convert.py export && python3 .deepseek/scripts/convert.py drift
```

`drift` ловит отставший снимок, правки `.deepseek` мимо конвертера и протёкшие `.deepseek`-ссылки
в `.claude`. Если правило проекта поменялось — сначала `CLAUDE.md`/`.claude/docs/`, потом `export`;
правка сразу в `.deepseek` живёт до следующего экспорта и теряется.

## Возврат в Claude Code

Пока `.deepseek` только читали, делать нечего. Если в DeepSeek правили документацию или память:

```bash
python3 .deepseek/scripts/convert.py check      # что разошлось
python3 .deepseek/scripts/convert.py import     # домой в .claude/docs и .claude/memory
git diff --stat .claude && git commit -m "docs: перенос изменений из DeepSeek"
```

Пошаговый сценарий с откатом — `sync/MIGRATION.md`. Если DeepSeek-сессия меняла и код —
`sync/MIGRATION.md#c-merge` и `sync/POLICY.md`.

## Состав

| Файл или каталог | Кто пишет |
|---|---|
| `AGENTS.md`, `CLAUDE.ds.md` (в корне репозитория) | конвертер |
| `instructions/` | человек; `instructions/project.md` — конвертер |
| `agents/`, `skills/`, `docs/`, `memory/`, `state/`, `hooks.json` | конвертер |
| `agent-memory-local/`, `notes/` | агенты DeepSeek |
| `sync/` | человек и сессия DeepSeek |
| `scripts/convert.py`, `scripts/selftest.py` | живут только здесь; симметричная копия — в другом репозитории |
| `scripts/token_usage_check_dsh.py`, `scripts/preflight.py` | служебные, только в `.deepseek` (не конвертируются) |

## Скрипты

| Скрипт | Что делает |
|---|---|
| `scripts/convert.py` | конвертация `.claude` ↔ `.deepseek` (`export`, `import`, `check`, `drift`, `status`) |
| `scripts/selftest.py` | 13 инвариантов контура, включая компиляцию скриптов и проверку расчёта токенов |
| `scripts/token_usage_check_dsh.py` | расход токенов по журналу dsh: те же пороги и JSON, что у claude-скрипта |
| `scripts/preflight.py` | старт сессии: свежий снимок, checkpoint, ветка, журнал токенов |

`.deepseek/` и `AGENTS.md` исключены из git через `.git/info/exclude` (как `.claude/` и `CLAUDE.md`):
снимок — локальная страховка, в историю он не попадает. Если снимок нужен переживающим `git clean` или
переезд на другую машину, его нужно закоммитить осознанно, сняв исключение, — это решение владельца
проекта, а не поведение конвертера.

## Документы

- `instructions/bridge.md` — карта соответствия раскладок, инструментов, моделей и команд.
- `instructions/contracts.md` — что DeepSeek соблюдает поверх `AGENTS.md`: память, документация, субагенты, скиллы.
- `instructions/rules.md` — правила для всех сессий (язык, вопросы, противоречия, субагенты); шаблон
  постановки задачи субагенту — `instructions/rules.md#subagents`.
- `instructions/runtime.md` — старт сессии dsh, модели, инструменты, хуки, ограничения.
- `instructions/checkpoint.md` — первое сообщение в сессии.
- `instructions/project.md` — правила проекта в терминах `.deepseek` (генерируется).
- `sync/INVARIANTS.md` — что обязано оставаться верным; проверка `scripts/selftest.py`.
- `sync/CONVERSION.md` — поля, имена, преобразования (спецификация конвертера).
- `sync/MIGRATION.md` — переход Claude Code -> DeepSeek -> обратно, режимы A/B/C.
- `sync/POLICY.md` — источник истины, границы правок, конфликты.
- `sync/HAZARDS.md` — что делает dsh иначе и что из этого необратимо.
- `sync/STATE.md` — журнал переносов (дописывает конвертер).
