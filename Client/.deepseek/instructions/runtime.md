# runtime.md — старт и границы сессии DeepSeek

Практика: как начать сессию dsh и чего в ней ждать. Проверено на dsh из репозитория
`deepseek-ai/deepseek-harness` (developer preview); при обновлении dsh расхождения записывать в
`.deepseek/sync/STATE.md`.

## Старт сессии

1. `git status` чистый, ветка — рабочая (см. `.deepseek/sync/POLICY.md`).
2. `python3 .deepseek/scripts/convert.py export --force` — свежий снимок `.claude`.
3. `python3 .deepseek/scripts/convert.py check` — «changed» быть не должно.
4. `dsh web` из корня репозитория; рабочая папка — этот репозиторий.
5. Первое сообщение в сессии — содержимое `.deepseek/instructions/checkpoint.md` (копируется целиком:
   dsh не читает подкаталожные инструкции автоматически, см. `#hooks`).
6. `python3 .deepseek/scripts/preflight.py --confirm-checkpoint [--mode A|B|C]` — проверяет, что снимок
   свежий, checkpoint отмечен, ветка сверена с `lastBranch`, журнал токенов находится. Блокер — сессию не
   начинать. Смена ветки: тот же вызов с `--task-type new|extend|bug`.

**Честно о checkpoint.** Автоматической подстановки `.deepseek/instructions/checkpoint.md` нет: dsh не
гарантирует чтение инструкций подкаталога и не даёт аналога `CLAUDE.md` в подпапке. Поэтому старт держится
на двух вещах: (1) человек вставляет текст первым сообщением, (2) `preflight.py --confirm-checkpoint`
пишет маркер в `.deepseek/state/session.json`, и без маркера следующий запуск preflight возвращает блокер.
Если dsh обзаведётся своим механизмом подкаталожных инструкций — правило снимается, маркер остаётся
как история.

## Модели и провайдер

- Провайдер DeepSeek, ключ в настройках dsh (`Settings -> Models`). Модели проекта:
  `deepseek-v4-pro` (лиды, аналитики-лиды, разработчики) и `deepseek-flash` (специалисты, библиотекари,
  интеграция без кода).
- Один и тот же запрос на `flash` дешевле и быстрее; для архитектуры и спорных решений — `pro`.
- Соответствие с моделями Claude Code — `.deepseek/instructions/bridge.md#модели`.

## Инструменты и субагенты

- Агент запускается `task` с типом, равным имени файла из `.deepseek/agents/`; инструкции агента —
  в самом файле, повторять их в задаче не нужно.
- Обязательная часть любой задачи субагенту — `.deepseek/instructions/rules.md#subagents` (шаблон, якоря, `ВОПРОСЫ`,
  синхронность, чтение скиллов и личной памяти с диска). Здесь она не повторяется.
- Лимит одновременных субагентов — 20 (как в `.claude`). Библиотекари — синхронно.
- Фоновые задачи и планировщик `schedule` — для длинных операций и напоминаний; синхронный ответ
  субагента они не заменяют.

## Контроль расхода токенов {#tokens}

В Claude Code это `CronCreate` раз в час + `.claude/scripts/token_usage_check.py`. В DeepSeek `CronCreate`
нет, а тот скрипт читает транскрипты Claude Code (`~/.claude/projects/...`), поэтому здесь свой источник —
журнал сессий dsh.

```bash
python3 .deepseek/scripts/token_usage_check_dsh.py 3600                 # автопоиск корня журналов
python3 .deepseek/scripts/token_usage_check_dsh.py 3600 --sessions-root ~/.deepseek/sessions
```

Выход — тот же JSON, что у claude-скрипта (`idle`, `base_session`, `agents`, `flags`, `total`), плюс
`"source": "dsh"` и `log`. Разбор ответа, пороги и что делать при `flags` — `.deepseek/instructions/project.md`, раздел
«Контроль расхода токенов»; формулы — в самом скрипте, здесь не дублируются.

**Данные.** `usage`-события dsh (`TokenUsage`: `inputTokens`, `outputTokens`, `cacheReadTokens`,
`cacheWriteTokens`, `reasoningTokens`), журнал `<root>/<projectKey(cwd)>/<sessionId>/session.jsonl`.

**Что нужно проверить один раз при первом запуске:**
1. **Корень журналов.** У JSONL-бэкенда dsh `root` обязателен и по умолчанию не задаётся. Скрипт смотрит
   `--sessions-root`, затем `DSH_SESSIONS_ROOT` / `DEEPSEEK_SESSIONS_ROOT` / `DSH_HOME`, затем обычные
   места. Если ничего не нашлось — он честно говорит `sessions-root not found`; корень надо взять из
   конфигурации dsh.
2. **Сжатие.** Журнал по умолчанию `session.jsonl.zstd`. Без модуля `zstandard` скрипт отвечает
   `zstd-session-log` и не притворяется, что токенов ноль. Варианты: `pip install zstandard` либо
   `compression: none` в конфигурации бэкенда (тогда журнал — обычный JSONL).
3. **Планировщик.** Вместо `CronCreate` — `schedule` dsh (если доступен) с тем же промптом раз в час.
   Недоступен — ручной запуск в начале и в конце этапа, либо `watch`-цикл:
   `while sleep 3600; do python3 .deepseek/scripts/token_usage_check_dsh.py 3600; done`.
4. **Имя роли агента.** `flags[].agent` — имя из события субагента; если dsh пишет его иначе, чем имя
   файла агента, поправить `agent_name()` в скрипте, а не порог.

Скрипт — не часть работы проекта: правки в нём не требуют `import`, он не конвертируется (лежит только
в `.deepseek/scripts/`).

## Сжатие контекста {#compaction}

- dsh сжимает контекст сам (`compaction`); перед сжатием и после него — краткая фиксация в
  `.deepseek/memory/` и `.deepseek/docs/` (что сделано, где остановились). Хуки `PreCompact` из `.claude` в DeepSeek играют
  ту же роль, но полагаться на них нельзя, пока не проверено.
- После сжатия контекста прочитать `.deepseek/instructions/checkpoint.md` заново: правило «проверь
  актуальность документации перед продолжением» действует и здесь.

## Хуки {#hooks}

`.deepseek/hooks.json` — нейтральный перенос того, что в Claude Code лежало в `.claude/settings.local.json`
(напоминания перед сжатием и после старта). Гарантий, что dsh поддерживает те же события, нет: механизм
хуков в dsh — плагин. Пока поведение не подтверждено:

1. Считать, что напоминания не срабатывают.
2. Вместо них — пункт в `.deepseek/instructions/checkpoint.md` (там продублирован смысл обоих напоминаний).
3. Проверка: `dsh` -> список плагинов -> есть плагин хуков? Есть — сопоставить события
   `session_start`/`pre_compact` и записать результат в `.deepseek/sync/STATE.md`.

## Ограничения, которые надо помнить

- **Инструкции в подкаталогах.** `AGENTS.md` в корне dsh читает; `.deepseek/CLAUDE.ds.md` и `.deepseek/instructions/`
  в подкаталоге — читает не каждое средство, поэтому в первой сессии их читают явно (checkpoint).
- **`AGENTS.md` — генерируемый**: правки в нём теряются при `export` (`.deepseek/instructions/rules.md`, раздел «Что делать
  нельзя»). Политика подтверждений dsh и роли с `web_*` — `.deepseek/instructions/rules.md`, раздел «Инструменты и разрешения».
- **Один и тот же `.deepseek` у двух репозиториев.** Конвертер и скрипты симметричны; правки в одном
  репозитории нужно переносить в другой (`.deepseek/sync/INVARIANTS.md`, пункт про симметрию). Скрипт
  `selftest.py` сверяет копии.
