# MIGRATION.md — переход Claude Code -> DeepSeek -> обратно

Три режима. Выбор режима — не по вкусу, а по одному вопросу: **может ли код проекта меняться в
DeepSeek?**

| Режим | Когда | Что можно | Что меняется в git |
|---|---|---|---|
| **A. Сторож** | Claude Code работает, `.deepseek` только держится свежим | ничего, только `export`/`drift` | `.deepseek` (при желании — один коммит «снимок») |
| **B. Мост** | Claude Code недоступен, менять нужно только документацию, память, агентов, скиллы | `.deepseek/docs/`, `.deepseek/memory/`, `.deepseek/*` | ветка `<ветка>-deepseek`, затем `import` обратно |
| **C. Замена** | Claude Code недоступен надолго, нужно менять и код | всё, но сборка и проверка — своими командами | отдельная ветка; возврат через merge (см. ниже) |

Почему код — только режим C: конвертер переносит `.claude`-раскладку, а не изменения в `src/`/`game/`.
Если DeepSeek правит код, возврат идёт через `git merge` двух веток, а не через `import`.

## Режим A: держать снимок свежим

```bash
python3 .deepseek/scripts/convert.py export && python3 .deepseek/scripts/convert.py drift
```

- Запускать перед началом и после окончания работы в Claude Code.
- `drift` с кодом 0 — снимок актуален. С кодом 1 — прочитать, что разошлось.
- Ошибка «`.deepseek`-ссылки в `.claude`» — правило писалось сразу в `.deepseek`. Текст надо перенести в
  `.claude` и перезапустить `export` (конвертер `.claude` -> `.deepseek` работающий в обратную сторону не
  «чинит», а дублирует).
- Расписание: шаг можно повесить на хук Claude Code (по желанию пользователя) или делать вручную — это
  одна команда.

## Режим B: Claude Code недоступен, меняется документация и правила {#b}

1. Проверить чистоту и свежесть:
   ```bash
   git status -s                 # должно быть пусто
   python3 .deepseek/scripts/convert.py check
   ```
   `.claude` опережает `.deepseek` («changed/missing») — сначала `export --force`, потом дальше.
2. Ветка:
   ```bash
   git switch -c <текущая-ветка>-deepseek
   ```
   Работать в той же ветке, что была в Claude Code (`lastBranch`), но копией — иначе ветка сломает
   сборку для тех, у кого Claude Code работает.
3. Открыть dsh в корне репозитория, первое сообщение — `.deepseek/instructions/checkpoint.md`.
4. Работать. Правила: `.deepseek/instructions/rules.md`. Документацию писать в `.deepseek/docs/`, память —
   в `.deepseek/memory/` и `.deepseek/agent-memory-local/`, заметки о решениях — `.deepseek/notes/`.
5. Коммиты — обычные, в ветку `<ветка>-deepseek`. Пересобрать репозиторий — стандартными командами
   (`npm run build` на клиенте, `mvn` на сервере из `scripts/build.sh` / `server/scripts`).

## Возврат из режима B {#b-back}

1. Сверить и перенести:
   ```bash
   python3 .deepseek/scripts/convert.py check      # что разошлось
   python3 .deepseek/scripts/convert.py import     # .deepseek -> .claude
   ```
   `import` переносит документы и память, чинит `.deepseek/hooks.json`/`.deepseek/state`, не трогает код и агентов, которые в
   `.claude` уже есть. Конфликты («расхождение, файл оставлен как в .claude») разбираются по одному:
   - документ в `.deepseek` свежее — `import --force` для этого файла или правка руками;
   - в `.claude` новее — удалить `.deepseek`-копию (`export --force` вернёт актуальную).
2. `python3 .deepseek/scripts/convert.py drift` и `git status -s .claude` — в диффе только ожидаемое.
3. Коммит в основную ветку: `git commit -m "docs: перенос из DeepSeek-сессии"`.
4. Пересобрать снимок: `python3 .deepseek/scripts/convert.py export`.
5. Ветку `<ветка>-deepseek` оставить до следующего сезона или удалить после merge — она содержит ту же
   документацию, что уже в основной ветке.

## Режим C: меняется код {#c-merge}

1. Всё из режима B, плюс ветка `<ветка>-deepseek` содержит код.
2. Перед возвратом проверить, что основная ветка собирается (`npm run build` / `mvn test`), и что
   DeepSeek-ветка собирается так же.
3. Возврат — merge **основной ветки в DeepSeek-ветку**, конфликты — в пользу основной:
   ```bash
   git switch <ветка>-deepseek
   git merge origin/<ветка>            # конфликты: код — из основной, документация — по смыслу
   python3 .deepseek/scripts/convert.py import --force   # документация и память DeepSeek -> .claude
   python3 .deepseek/scripts/convert.py export           # обновить снимок после merge
   ```
4. Если основной веткой пользовались в Claude Code — она ушла вперёд по документации: сначала merge
   (п.3), затем `check` и ручное разрешение оставшихся расхождений, только потом merge обратно в основную.
5. Merge в основную — отдельным коммитом-«слиянием работы из DeepSeek», с описанием, что сделано в
   DeepSeek-сессии. Ссылки вида `// См. .claude/docs/...` в коде DeepSeek-ветки нужно привести к `.claude`
   (в DeepSeek-режиме код их не получал, но документация могла ссылаться на `.deepseek`).

## Возврат после аварийной остановки DeepSeek

Если сессия dsh оборвалась посреди работы:

1. `git status -s` — незакоммиченное сохранить (`git add -A && git commit -m "wip: deepseek"` в ветке).
2. `python3 .deepseek/scripts/convert.py check` — какие документы успели измениться.
3. Дальше — как в «Возврат из режима B»: `import`, разбор конфликтов, коммит в основную.
4. Если задача в коде осталась недоделанной — не дописывать её в Claude Code вслепую: сначала прочитать
   `git diff <ветка>-deepseek` и `notes/`, затем продолжить тем же пайплайном.

## Откат

- `import` меняет только `.claude/docs/`, `.claude/memory/`, `settings.local.json`, `session_state.json` и
  память агентов — откат `git checkout -- .claude` возвращает всё.
- `export` меняет только `.deepseek/` (и `AGENTS.md` в корне) — откат `git checkout -- .deepseek AGENTS.md`.
- Совсем удалить контур: `git rm -r .deepseek AGENTS.md CLAUDE.ds.md` (если пользователь решил, что
  страховка больше не нужна).
