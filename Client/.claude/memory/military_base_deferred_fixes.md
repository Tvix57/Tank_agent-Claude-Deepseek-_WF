---
name: military-base-deferred-fixes
description: "Отложенные исправления военной базы (client) — найдены при первичной документации 2026-10-22; напомнить при задаче по военной базе, авиазаводу, аэродрому базы"
metadata:
  node_type: memory
  type: project
  modified: 2026-10-22T06:06:55.183Z
  originSessionId: fd6d858f-99c1-43c3-90d3-ec53e1b9dfc6
---

Решение пользователя 2026-10-22: все баги и расхождения ГДД↔код отложены, ничего не чинить без явной команды. Закрыто сверкой с сервером: потеря бустера при закрытии окна призыва (§8.4) невозможна.
Доки: client `military-base-architecture.md` §8 (`#p-…`), ГДД `game-design/military-base-gdd.md` (расхождения ГДД↔код — в `#gdd-open`, сюда не дублируются).
Пути — от `/workspace/client/src/views/home_screen/popups/military_base/`.

## Баги клиента (отложено пользователем 2026-10-22)
- Деление на 0: `MilitaryBaseStoragePopup.ts:112` — при `maxCapacity = 0` заполненность NaN.
- `/acceptAirplane`, `/refuseAirplane` без проверки `result`: `MilitaryBaseAviationFactoryPopup.ts:342-361` — ответ без `militaryBase` даёт `setMilitaryBaseData(undefined)` (§8.13).
- `bonus.amount` читается без проверки: `MilitaryBaseUtils.ts:45` (сервер заполняет для всех 50 id — риск только при новых id).
- Мёртвое: атласы и пакеты бустеров 51/52 (`Boost_51/52` в `LoadAssetPackage.ts`), `MilitaryBaseStorageJSON.exp` (`militaryBase.d.ts:11`) — удалить.
- Цикл `/tick` при ошибке запроса: `MilitaryBasePopup.ts:128-160`, `catch` шлёт заново каждый тик; плюс рассинхрон часов (`TimeUtils.ts:11-29`), нужен лимит повторов (§8.16).
- `/takeProfit` без проверки ответа: `MilitaryBaseStoragePopup.ts:391+` — `getResource().count` на пустом ответе бросает исключение, его глотает `catch`.
- 19 обработчиков `catch` по области, большинство пустые (например `MilitaryBasePopup.ts:371`, `MilitaryBaseResourcesPopup.ts:840,851`) — ошибки игроку не показываются (§8 п.8).
- Аэродром базы падает, если самолёта нет в сумке: `MilitaryBaseAerodromePopup.ts:120,150` (также в `aerodrome_deferred_fixes.md`); подпись «В БОЮ» не возвращена.
- Таймер взлёта на плашке `HomeScreenMilitaryBase.ts:~41-50` вычитает 1000 мс за тик, а не считает по часам — после фона врёт.
- Неявный порядок (`#no-implicit-order`): пара `setMilitaryBaseData` + `emit(MILITARY_BASE_UPDATED)` повторена в 6 местах (`MilitaryBasePopup.ts:130-132`, `MilitaryBaseHeadquartersPopup.ts:262-264`, `MilitaryBaseAviationFactoryPopup.ts` — запуск/accept/refuse, `MilitaryBaseStoragePopup.ts` — прокачка); нужен один метод у `MilitaryBaseState`. Так же запись `tutorialProgress` вызывающими (`MilitaryBaseBuyBuildingPopup.ts:218-221`, `MilitaryBaseSellResourcePopup.ts:508-511`, `MilitaryBaseResourcesPopup.ts:~905`).

## Визуальные правки, не найденные в коде (документ «Правки», в ГДД не входят)
- 2.9 — боковые затенения остались: `MilitaryBaseBackground.ts:59-60`, `MilitaryBaseAerodromePopup.ts`; должны быть только сверху и снизу.
- 2.4 — цифры в баблах: шрифт 8 px вместо 16 px (обводка есть, `base/MilitaryBaseHeadquarters.ts`).

**How to apply:** при задаче по военной базе напомнить и предложить включить эти пункты; перед исправлением сверить с актуальным кодом.
