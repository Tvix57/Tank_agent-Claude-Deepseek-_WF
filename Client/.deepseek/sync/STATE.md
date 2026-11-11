# STATE.md — журнал переносов

Свежесть и направление переносов. Верхнюю часть правят руками, строки под `## Журнал` дописывает
`convert.py`. Расхождение с `drift` — читать последнюю строку и решать по `.deepseek/sync/POLICY.md#конфликты`.

Текущая раскладка: `.claude` основная, `.deepseek` снимок (режим A).

## Дедупликация правил 2026-11-11 (правки в `.deepseek` и `CLAUDE.md`, `import` не нужен)

Общие правила сведены в `CLAUDE.md` клиента — он единственный источник; серверный `CLAUDE.md` держит
ссылки на его разделы и серверные отличия. Из `.deepseek/instructions/*`, `.deepseek/README.md` и
`.deepseek/sync/HAZARDS.md` убраны пересказы правил — вместо них ссылки на разделы `CLAUDE.md`; якоря
`#субагенты`/`#память` заменены на `#subagents`. Дубли в `.claude` (запись памяти про русский язык,
строка «отвечать по-русски» в агентах, отсутствие якоря `#conflict-check`) — осознанная дельта: решение
Пользователя 2026-11-11 оставить `.claude` как есть.

## Правка ссылок 2026-11-11: без переменной WF-папки, от папки инструкций

Ссылки в инструкциях больше не строятся через переменную с корнем WF-папки: они относительные — от папки
инструкций того репозитория, в котором лежит файл (`../client/...` из серверной папки). Файлы
`.deepseek/instructions/*` и `.deepseek/sync/*` приведены к этой же базе. Исключения — места, где пути
перечисляют раскладку дерева, а не адресуют файл: таблица раскладок в `.deepseek/instructions/bridge.md`,
индекс `.deepseek/README.md` и разделы `.deepseek/sync/CONVERSION.md`.

## Правки DeepSeek-сессии 2026-11-06 (проведены через `.claude`, `import` не нужен)

- Субагенты: в `.deepseek/instructions/rules.md#subagents` — обязательный шаблон постановки задачи
  (`АГЕНТ`/`ЗАДАЧА`/`ОБЛАСТЬ`/`ВХОД`/`ВЕРНУТЬ`/`ОБЯЗАТЕЛЬНО`); ссылки на него в `.deepseek/instructions/runtime.md`,
  `.deepseek/README.md`, `.deepseek/sync/HAZARDS.md`.
- Лиды аналитиков (client и server): вызов специалистов и создание нового агента — в терминах dsh
  (`task`, `write`, `edit`, `skill`, `traits`); якоря WF — полным путём; `#conflict-check`, `#resume`,
  `#doc-depth`, `#doc-review` добавлены в WF; `#naming-rules` заменён путём к скиллу `naming`;
  модель — `deepseek-v4-pro`/`deepseek-flash` вместо `fable`/`opus`/`sonnet`; создание ГДД — только
  после согласования структуры с Пользователем; каталог личной памяти создаётся вместе с агентом.
- Ростер: добавлены `client-analyst-generals` и `server-analyst-generals` (правка в `.claude`).
- Специалисты и лиды разработчиков: `Agent tool` → `task`, `Skill`/`Write`/`Edit` → `skill`/`write`/`edit`,
  `subagent_type`/`run_in_background` у библиотекарей → тип агента и синхронный вызов.
- Память: созданы `.deepseek/agent-memory-local/{client,server}-{analyst,developer}-generals/`.
- ГДД `generals-gdd.md`: уточнено, что клиентской архитектуры ещё нет; серверная ссылается на ГДД
  через `.claude`-путь с оговоркой про `.deepseek`-раскладку.

## Осознанная дельта 2026-11-09: генералы остаются в `.deepseek`

Область «Генералы и Ставка армии» заведена в DeepSeek 2026-11-06 и в `.claude` пока **не переносится** —
решение Пользователя 2026-11-09. Потерь при переносе инструкций в папку WF не было: этих файлов в `.claude`
не было изначально.

- Файлы дельты: `.deepseek/agents/analysts/client-analyst-generals.md`, `.deepseek/agents/developers/client-developer-generals.md`,
  `.deepseek/docs/game-design/generals-gdd.md`, `.deepseek/docs/generals-architecture.md`, `agent-memory-local/*-generals/`.
- `import` для них **не запускать**, пока Пользователь не решит иначе: он создаст эти файлы в `.claude`.
- Следствия, которые поломкой не считать: `convert.py check` → `new 2`; `convert.py drift` →
  «снимок отстал: 2»; `preflight.py` пункт 1 (свежесть снимка) → БЛОК на всё время дельты.
- `export --force` дельту не удаляет: снимок только копирует `.claude` → `.deepseek`, лишнее не чистит.
- `.claude/agents/analysts/client-analyst-lead.md` (ро̀стер) ссылается на `client-analyst-generals`,
  которого в `.claude` пока нет: так и задумано, запись опережает агентов (решение Пользователя
  2026-11-09). Ссылку не снимать и висячей ссылкой не считать.

## Журнал

| Когда | Команда | Что | Счётчики |
|---|---|---|---|
| 2026-11-04 03:26:59 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:27:27 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:27:34 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:27:44 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:28:10 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:28:47 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:29:08 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:29:34 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:30:26 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:30:36 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:30:57 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:31:34 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:32:00 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:33:11 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:34:17 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:36:37 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:39:43 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:39:43 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:48:11 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:57:15 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 03:57:42 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 04:13:42 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 04:14:17 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 04:14:30 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-04 04:14:51 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 10:40:41 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 10:40:49 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 10:40:57 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:00:00 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:14:17 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:17:21 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:17:59 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:18:19 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:19:15 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:19:27 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:19:45 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:21:14 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-06 11:22:08 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-09 12:26:06 +0700 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-09 12:26:42 +0700 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-11 05:24:21 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-11 05:29:42 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
| 2026-11-11 05:30:19 +0000 | export | снимок .claude -> .deepseek | {"agents": 31, "skills": 4, "docs": 55, "memory": 65} |
