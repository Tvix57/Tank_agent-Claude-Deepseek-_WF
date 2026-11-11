# Tank_agent-Claude-Deepseek-_WF

Папка инструкций агентов для «Танков». Живёт **вне контейнера**: правки не теряются при пересборке и не
расходятся между Claude Code (`.claude`) и DeepSeek Harness (`.deepseek`).

## Раскладка

| Папка | Что внутри |
|---|---|
| `Client/` | `CLAUDE.md` — источник правил; `AGENTS.md` и `.deepseek/instructions/project.md` — генерируются конвертером; `.claude/` — команды, скиллы, документация, память; `.deepseek/` — зеркало для dsh |
| `Server/` | то же для сервера (серверные правила и документация отличаются от клиентских) |
| `tools/link_workspaces.py` | пересоздаёт симлинки рабочих каталогов на эту папку |

## Как подключено

- **Контейнер**: `.devcontainer/docker-compose.yml` монтирует эту папку как `/wf`, `.devcontainer/devcontainer.json`
  задаёт `containerEnv: WF_ROOT=/wf`. В рабочих каталогах `/workspace/client` и `/workspace/server`
  `CLAUDE.md`, `AGENTS.md`, `.claude`, `.deepseek` — симлинки на подпапки `Client` и `Server` этой папки.
- **macOS (хост)**: `export WF_ROOT="<абсолютный путь к этой папке>"` в `~/.zshrc`. Симлинки в
  рабочих каталогах ведут на `/wf/...`, поэтому на хосте они висят — правки идут через контейнер.

Исключения инструкций из гита рабочих каталогов дописывает тот же `tools/link_workspaces.py` — в
локальный `.git/info/exclude` проекта и только для путей, которые гит пока не игнорирует (проверка
через `git check-ignore`). Отслеживаемый `.gitignore` проекта не трогается: репозиторий проекта не
должен знать про инфраструктуру агентов. Плата за это — exclude не коммитится, поэтому после
переклона рабочего каталога скрипт запускают заново (он же пересоздаёт и симлинки).

## Правка правил

1. Общие правила — `CLAUDE.md` в папке инструкций репозитория (`Client/` для клиента, `Server/` для сервера);
   специфика DeepSeek — `.deepseek/instructions/rules.md`.
2. `python3 .deepseek/scripts/convert.py export` (из рабочего каталога проекта) — обновляет `AGENTS.md`,
   `.deepseek/instructions/project.md`, `CLAUDE.ds.md` и зеркало.
3. `python3 .deepseek/scripts/convert.py check` — `changed 0, missing 0`; `python3 .deepseek/scripts/selftest.py`
   — инварианты `.deepseek`.

## Если ссылки потерялись (переклонировали рабочие каталоги)

```bash
python3 tools/link_workspaces.py --workdir <рабочий каталог проекта>
```

(запускать из этой папки инструкций; скрипту нужен путь к рабочему каталогу проекта)

Скрипт идемпотентен: существующие ссылки не трогает, обычные файлы складывает в
`<workdir>/.wf-backup/repo-files-<дата>/` перед заменой, недостающие исключения дописывает в
`.git/info/exclude` проекта.
