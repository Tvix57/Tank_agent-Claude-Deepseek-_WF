<!-- GENERATED из CLAUDE.md. DEEPSEEK-ONLY правила — .deepseek/instructions/project.md, далее .deepseek/instructions/rules.md -->

## Раскладка .deepseek (DeepSeek Harness)

Если Claude Code недоступен, эта же команда работает по раскладке `.deepseek`:

- инструкции проекта — `AGENTS.md` корня репозитория (для dsh) и `CLAUDE.ds.md` (для Claude Code, читается
  из подкаталога);
- агенты, скиллы, документация, память — те же файлы в `.deepseek/agents|skills|docs|memory`;
  карта соответствия — `.deepseek/instructions/bridge.md`;
- спецификация конвертера — `.deepseek/sync/CONVERSION.md`;
- инварианты — `.deepseek/sync/INVARIANTS.md`; регрессия — `python3 .deepseek/scripts/selftest.py`.

Правки вести в `.claude`, затем `python3 .deepseek/scripts/convert.py export`.
