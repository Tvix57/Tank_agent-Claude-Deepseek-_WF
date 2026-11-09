---
name: server-collections-fix-decisions-2026-10-05
description: "Решения пользователя по исправлению серверных коллекций (записи предметов, кодекс, сезон, индексы) от 2026-10-05; реализованы и одобрены пользователем, клиент правок не требует"
metadata:
  node_type: memory
  type: project
  originSessionId: fe3dfa05-069a-4d45-b25e-6ff187d5f9f7
  modified: 2026-10-06T06:30:36.321Z
---

Обновление 2026-10-06: имена методов и JSON-ключи коллекций переименованы (`collectionEndTime` → `sectionEndTime`, `currentStage` → `rewardedStage` и др.), `refreshSection()` оставлен по решению ниже; актуальные имена — в серверном `collections-architecture.md` (история изменений). Фраза «контракт не изменился» ниже относится к 2026-10-05.

Реализовано и одобрено пользователем 2026-10-05 (сервер, коммит `edf1878`); контракт с клиентом не изменился (ключи JSON, роуты, формат уведомления те же; `collectionEndTime` — по-прежнему абсолютное время в мс), клиентский код не правился. Пакет перенесён в `com.linkedgames.game.model.collections`; consume→add теперь `removeAllItems` → `updateState`, флаги через `markDeleted()` (см. [[feedback-no-implicit-call-order]]). Решения пользователя 2026-10-05, ветка koba/collection:

1. Записи предметов Collection — вариант Б2: инвариант «1 cid = 1 CollectionItemEntry = 1 документ»; улучшение меняет звёзды той же записи (флаг «изменена»), consume→add снимает DELETED с той же записи, условное remove(cid, entry), сведение дублей при загрузке (лучшие звёзды остаются, прочие DELETED). Переход на BagItem (вариант А) отклонён.
2. Танк коллекции в кодекс — НЕ писать, остаётся правило ГДД (collections-gdd.md: «Запись в кодекс для экспериментального танка не создаётся»). Подтверждено пользователем явно.
3. Сезон альбомов — геттеры (getCollectionTimeLeft, hasAvailableReward, isDropEnabled) без побочных эффектов; отдельный refreshSection()/CollectionUserComponent.refreshState() в AuthorizedUserPage.onRouteCallStart рядом с resetOffers() + при входе (onAuthorizedActiveOnce). Чинит двойную выдачу наград этапов после конца сезона. Уточнение пользователя: сезон ЛИЧНЫЙ — публичная функция refreshSection() (abstract void на CollectionSectionType, рядом abstract boolean isSectionActive()) ставит дедлайн now + 90 дней (сброс наград этапов сохраняется); refreshState в AuthorizedUserPage проверяет время и, если сезон кончился (или не начат), вызывает эту функцию. Позже её же будет вызывать отдельный page выбора секции. isDropEnabled удалён — условие ролла дропа = isSectionActive() (тот же смысл по ГДД). Прежний шаг по 90 дней от эпохи удалён.
4. Миграция индекса {ownerId: 1} для коллекции БД `collections`. Уникальный {ownerId,cid} — не включён.

Codex — не включён в объём, записан в отложенные: [[server-codex-deferred-fixes]].

**Why:** зафиксировать выбор, чтобы не переспрашивать и не противоречить ему в следующих сессиях.
**How to apply:** при реализации/правке этих мест следовать решениям; при попытке изменить — правило проверки на противоречие. См. [[server-collections-architecture]].
