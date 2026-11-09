---
schema: 1
name: server_codex_deferred_fixes.md
type: project
title: Отложенное исправление CodexUserComponent — дубли записей из-за map.remove(id) в onClean (баг уже в master/проде)
source: .claude/memory/server_codex_deferred_fixes.md
claude: |
  name: server-codex-deferred-fixes
  description: Отложенное исправление CodexUserComponent — дубли записей из-за map.remove(id) в onClean (баг уже в master/проде)
  metadata:
    type: project
---

Найдено 2026-10-05 при анализе коллекций. В `CodexUserComponent.onClean` (`tanksMap.remove(id)` / `airplanesMap.remove(id)`) при замене записи на более сильную из карты удаляется НОВАЯ запись: следующая запись того же танка добавляется без сравнения, в БД копятся дубли, `CodexPage` по `tanksList` отдаёт повторы в `collected`, загрузка дубли не сводит. Баг в master с коммита d3d31c4 — затронуты продовые данные.

Предложенный фикс: условное `remove(id, entry)` + сведение дублей при загрузке (оставить запись с наибольшей `getPower()`, остальные DELETED → удалятся обычным сохранением). Уникальный индекс `{ownerId, t, id}` ставить нельзя, пока в проде есть дубли (оффлайн-игроки не самолечатся).

**Why:** пользователь решил не включать в задачу по коллекциям, но попросил записать.
**How to apply:** при любой новой задаче, затрагивающей кодекс, напомнить и предложить починить. Аналог в коллекциях — [[server-collections-fix-decisions-2026-10-05]].

**Обновление 2026-10-19:** по отчёту server-analyst-codex после merge amnesia/fix `onClean` больше не удаляет запись из карты — проверить, закрыт ли баг дублей кодом fix; сведение уже существующих дублей в проде остаётся. Codex на клиенте показывает ранги 1..20 — неизвестно, отдаёт ли сервер 11–20.
