---
name: client-asset-packaging-docs
description: "Где искать процедуру паковки клиентских ассетов (async per-id атласы, обычные атласы, raw-картинки, config.yaml, AssetPacker)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3f953276-d14c-4026-a691-02a88960c0ff
  modified: 2026-09-23T06:27:56.623Z
---

Полная процедура добавления/паковки клиентских ассетов — `/workspace/client/.claude/docs/asset-packaging.md`.
Содержит: async per-id атласы (`Creator.spriteAsync` + `config.yaml` + `LoadAssetPackage.ts`),
обычные (regular) атласы (`Creator.sprite` + `addAssetPackage`, без спиннера), raw-картинки,
частые причины "картинка не показалась, ошибок нет".

**Why:** раньше жила внутри `CLAUDE.md`, 2026-09-23 вынесена в отдельный документ по явному
решению пользователя (аналогично тому, как устроена документация по MongoDB-персистентности
на сервере) — `CLAUDE.md` теперь содержит только короткий указатель. `client-librarian-patterns-gamedev`
ссылается на этот документ как на первоисточник (не на `CLAUDE.md`).

**How to apply:** при любой задаче на добавление нового атласа/ассета на клиенте — открывать
этот документ целиком, не пересказывать по памяти. См. также [[feedback_no_git_dependency_tooling_files]]
(`.claude/docs/*.md` не коммитится вместе с игровым кодом как обычный файл проекта — уточни
у пользователя политику коммита, если не ясно).
