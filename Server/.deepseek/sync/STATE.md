# STATE.md — журнал переносов

Свежесть и направление переносов. Верхнюю часть правят руками, строки под `## Журнал` дописывает
`convert.py`. Расхождение с `drift` — читать последнюю строку и решать по `POLICY.md#конфликты`.

Текущая раскладка: `.claude` основная, `.deepseek` снимок (режим A).

## Правки DeepSeek-сессии 2026-11-06 (проведены через `.claude`, `import` не нужен)

- Субагенты: в `instructions/rules.md#subagents` — обязательный шаблон постановки задачи
  (`АГЕНТ`/`ЗАДАЧА`/`ОБЛАСТЬ`/`ВХОД`/`ВЕРНУТЬ`/`ОБЯЗАТЕЛЬНО`); ссылки на него в `runtime.md#субагенты`,
  `README.md`, `sync/HAZARDS.md`.
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
| 2026-11-06 11:21:14 +0000 | export | снимок .claude -> .deepseek | {"agents": 32, "skills": 1, "docs": 27, "memory": 0} |
| 2026-11-06 11:22:08 +0000 | export | снимок .claude -> .deepseek | {"agents": 32, "skills": 1, "docs": 27, "memory": 0} |
