---
name: aerodrome-deferred-fixes
description: Отложенные исправления аэродрома (client+server) — найдены при первичной документации и сверке с ГДД 2026-10-16; напомнить при задаче по аэродрому
metadata:
  node_type: memory
  type: project
  originSessionId: 966c7a90-69c7-4a91-84d6-754b8f0b19f5
  modified: 2026-10-17T06:22:29.701Z
---

Доки: `/workspace/client/.claude/docs/aerodrome-architecture.md#tradeoffs`,
`/workspace/server/.claude/docs/aerodrome-architecture.md#tradeoffs`; ГДД: `game-design/aerodrome-gdd.md`.
2026-10-16 пользователь решил ничего не чинить сейчас. Главное:
- клиент, приоритет: рамка радиовышки застревает в слое `summon` после закрытия окна самолёта по фону; автопризыв
  не останавливается при закрытии окна решения по фону (у поезда останавливается);
- клиент: покупка схем ищет в награде схемы танка (нет удержания и анимации), «КУПИТЬ ЗОЛОТО» без действия; ответы
  `/accept`/`/refuse` не проверяются на ошибку и обрабатываются дважды (RadioTowerFrame и HomeScreen); любая ошибка
  `/summon` открывает покупку схем (открытый вопрос ГДД); окно падает, если самолёта по `uid` нет в сумке;
  слой `summon` открывает окно во время туториала;
- сервер (нумерация #tradeoffs от 2026-10-17), приоритет: п.1 неизвестный `uid` → самолёт любого класса в позицию 0
  (слот 8), тот же баг в копии HangarUserComponent — по решению 2026-10-17 копии не объединять, чинить в обеих;
  п.10 нет самолётов выпавшего ранга → падение `receiveAirplane`; также п.3 предел «важного уровня» из таблицы поезда,
  п.13 `/buySchemes` без `id` падает, п.12 результат `BagUserComponent.add` не проверяется;
- стык, отложено: доступ с 5-го уровня кампании проверяет только клиент (общий пункт с [[campaign-deferred-fixes]]).
Решения 2026-10-16 «как в коде» (не баги): замена/продажа самолёта не идёт в квест продажи; правый столбец сверху
вниз 4,3,2,1; «(макс ур)» только в окнах; сохранённый ранг с нулевым шансом запускается и не сбрасывается при выходе.
Дубли кода с поездом находкой не считаются: у аэродрома свои правила.

**Why:** документация делалась без задачи на исправление.
**How to apply:** при задаче по аэродрому напомнить и предложить начать с двух клиентских приоритетов и двух
серверных. Перед исправлением сверить с актуальным кодом. Связано: [[project-battle-air-followups]].

## После merge amnesia/fix (2026-10-19, отложено пользователем)
Аэродром сведён к слотам, призыв самолёта переехал в военную базу (авиазавод).
- Вернуть подпись «В БОЮ» в `MilitaryBaseAerodromePopup` (правило порядка взлёта в ГДД оставлено).
- `AirplaneGetPopup` закрывается по фону, `onClose` пустой — по ГДД самолёт ждёт решения игрока.
- `MilitaryBaseAerodromePopup` падает, если самолёта нет в сумке.
- Висящий `holdResource(RESOURCE_AIRPLANE_SCHEME)`: `HomeScreenQuest.ts:180-182`, `IdlePopup.ts:180,204`, `CampaignBattleGround.ts:142-146` — подписчик анимации `HOME_AERODROME_AIRPLANE_SCHEMES` был только в неподключённом `HomeScreenAerodrome`, `releaseHold` не вызывается.
- Мёртвый код/ошибки tsc из fix (оставлены автору): `HomeScreenAerodrome.ts`, `RadioTowerAutoSummonParams`, `GameEvents.RADIO_TOWER_UPDATE`, `battlefield.d.ts` `AerodromeJSON`, `AERODROME_UPDATE`, `Vars.AerodromeAccessCampaignLevel`.
- server: ключи `l/exp/rca` в документе Aerodrome оставлены; `AerodromeBuySchemesData` и `RESOURCE_AIRPLANE_SCHEME` — до решения по военной базе.
