# Глоссарий проекта

Термины игры и их имена в коде client/server. Правила механик — в ГДД по ссылкам.

## Коллекции

**Качество монеты** — `rank`
Уровень монет и набора экспериментальных танков (1–8), от него зависят звёзды монеты и танк-награда.
ГДД: collections-gdd.md#gdd-exp-quality
_Избегать_: tier, тир
_В коде_: `findExperimentalTankRank` (server), `nextRankItem` / `nextRankCollection` (JSON)

**Дубликат** — `duplicate`
Выпавший предмет коллекции, который у игрока уже есть (монета, фото с не большим числом звёзд);
превращается в серебро. ГДД: collections-gdd.md#gdd-exp-duplicate, #gdd-ops-upgrade
_Избегать_: sell (кроме JSON-ключа `sellReward`)
_В коде_: `addDuplicateReward`, `createDuplicateReward` (server)

**Конец события альбомов** — `sectionEndTime`
Момент окончания личного таймера события секции альбомов. ГДД: collections-gdd.md#gdd-ops-season
_Избегать_: seasonEndTime, collectionEndTime
_В коде_: `AlbumsSectionEntry.sectionEndTime` (server), JSON-ключ `sectionEndTime`

## Поезд

**Схема танка** — `TANK_SCHEME` (`ItemId.RESOURCE_TANK_SCHEME`)
Ресурс сумки, плата за один призыв в поезде. ГДД: train-gdd.md#gdd-scheme, bag-gdd.md#gdd-resources
_Избегать_: жетон призыва (слово пользователя, то же понятие), token
_В коде_: `RESOURCE_TANK_SCHEME` (client, server), JSON-ключ `schemes` в `/ingame/train/buySchemesData`

## Ангар

**Ангар** — `hangar`
Команда танков игрока из 12 слотов; её танки воюют в боях кампании. ГДД: hangar-gdd.md#gdd-purpose
_Избегать_: команда, состав (в значении «ангар»); team (кроме серверной боевой `Team`)
_В коде_: `HangarJSON` (client), `HangarUserComponent` (server), маршрут `/ingame/home/hangar`

**Слот** — `position` (только имя в коде)
Место танка в ангаре и на поле боя или самолёта на аэродроме; слово для игрока и ГДД.
Нумерация: танк — слот N = `position` N−1 (слоты 1–12 ↔ `position` 0–11: тяжёлые 1–4 ↔ 0–3, средние
5–8 ↔ 4–7, лёгкие и ПТ 9–12 ↔ 8–11); самолёт — слот N = `position` 8−N (слот 8, стратегический
бомбардировщик ↔ 0; слоты 1–4, истребители ↔ 7–4). ГДД: hangar-gdd.md#gdd-slots, aerodrome-gdd.md#gdd-slots
_Избегать_: «позиция» в тексте ГДД и для игрока; slot в коде
_В коде_: `TankPositionJSON.position` (client), `TankType.TYPE_POSITION`, `AirplaneType.TYPE_POSITION` (server)

**Ряд** — отдельного имени в коде нет (слоты типа — `TYPE_POSITION`)
Четыре слота одного класса: тяжёлые, средние, лёгкие и ПТ. Класс танка при замене — его ряд.
ГДД: hangar-gdd.md#gdd-slots
_Избегать_: «тип» в значении «ряд» (лёгкие и ПТ — разные типы, но один ряд)
_В коде_: `TankType.TYPE_POSITION` (server)

**Заменяемый танк** — `replaceableTank`
Самый слабый танк ряда, на место которого встанет новый, если в ряду нет свободного слота.
ГДД: hangar-gdd.md#gdd-placement
_В коде_: JSON-ключ `replaceableTank`, `getReplaceableTank` (server)

**Окно сравнения** — `TankGetPopup`
Общее окно решения по новому танку («ВЫБРАТЬ» / «ПРОДАЖА»). ГДД: hangar-gdd.md#gdd-compare-window
_Избегать_: окно получения танка
_В коде_: `TankGetPopup` (client)

## Интеграции

**Ярлык** — `shortcut`
Ярлык игры на экране устройства, который создаёт диалог Яндекс Игр; за него игроку полагается разовая награда.
ГДД: platform-sdk-gdd.md#gdd-reward
_Избегать_: закладка, bookmark, иконка на рабочем столе
_В коде_: `YandexUserComponent.sendShortcutReward` (server), `account.yandexShortcut` (JSON)
