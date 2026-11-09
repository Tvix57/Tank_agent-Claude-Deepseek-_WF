---
name: server-collections-deferred-fixes
description: "Отложенные рефакторы серверных коллекций с условиями запуска — новая альбомная секция, секция эксп. самолётов"
metadata:
  node_type: memory
  type: project
  originSessionId: 764d4a81-c530-49cd-8140-eab6756614a5
  modified: 2026-10-07T07:07:03.177Z
---

Решения пользователя 2026-10-07 (ревью этапа server-push, [[project-collections-server-push-plan]]): сейчас не трогать,
напомнить и предложить рефактор при наступлении условия.

- **Условие: задача на добавление новой секции с альбомами.** `CollectionUserComponent.getAlbumsSectionType(CollectionSection)`
  — аргумент выглядит лишним при одной альбомной секции (USSR_OPERATIONS), а `get*` скрывает возврат null для
  неальбомной секции. Пересмотреть форму (имя `find*`, аргумент, связь с заделом `selected`/`reselect`).
- **Условие: задача на добавление секции экспериментальных самолётов.** `CollectionExperimentalTankPage.getTanksSectionType`
  — приватный прямой каст `getSectionType(EXPERIMENTAL_TANKS)` в Page, несимметрично альбомам. Предложить метод
  компонента (`getExperimentalTanksSectionType()` или общий подход для типизированных секций).

**Why:** пользователь отложил, чтобы не расширять текущий этап.
**How to apply:** при задаче с указанным условием — напомнить и предложить рефактор до реализации.

## ItemType после слияния с amnesia/fix (решение 2026-10-19)
Клиент `koba/collection` слит с `origin/amnesia/fix`: `MILITARY_BASE_BUILDING=3`, `MILITARY_BASE_AVIATION_FACTORY_SLOT=4`, `MILITARY_BASE_BOOST=5`, `COLLECTION_ITEM=6`.
**Why:** обе ветки заняли id 3; военная база уже в fix, коллекции сдвинуты.
Server тоже слит (без коммита, 2026-10-19): `COLLECTION_ITEM` последний в enum (ordinal 6), `getCount()` стал `long` → в `CollectionUserComponent.grantReward` `(int)`-каст для `triggerEvent`.
**How to apply:** Старые документы сумки с `t=3` (коллекционные) теперь будут читаться как `MILITARY_BASE_BUILDING` — продолжение открытого ClassCastException t=3, нужна чистка/миграция, решать с пользователем.
