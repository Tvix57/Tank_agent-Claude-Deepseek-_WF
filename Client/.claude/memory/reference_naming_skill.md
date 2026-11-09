---
name: reference-naming-skill
description: "Проектные скиллы naming, glossary, writing-for-agents (client+server, одна копия в client, в server симлинки), 2026-10-06"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5bc5a339-d8df-4dc8-a7ec-adc59de5764f
  modified: 2026-10-06T04:13:41.050Z
---

Скилл `/workspace/client/.claude/skills/naming/SKILL.md`; в server подключён симлинком
`/workspace/server/.claude/skills/naming` → client (одна копия, правлю только в client).
Обе папки `.claude/skills/` исключены через `.git/info/exclude` (см. [[feedback-no-git-dependency-tooling-files]]).

Создан по просьбе пользователя вместо сторонних скиллов (naming-analyzer, clean-code), так как они
учат общему стандарту и конфликтуют с правилами проекта (комментарии, `src/ee/`). Если конвенции в
коде заметно изменятся, таблицы в скилле надо пересчитать.

Там же (2026-10-06) — свои адаптации из mattpocock/skills:
- `glossary` (из domain-modeling): глоссарий «термин ГДД ↔ слово в коде» в
  `/workspace/client/.claude/docs/glossary.md`, создаётся лениво; ADR-часть выброшена (решения — в memory/docs).
  Отдельно от ГДД, т.к. README ГДД запрещает имена кода. `naming` ссылается на глоссарий.
- `writing-for-agents`: указатели, две нагрузки, иерархия/раскрытие, ключевые слова, чистка + правила
  проекта для `.claude/*`.
Обе в server — симлинками, как `naming`.
