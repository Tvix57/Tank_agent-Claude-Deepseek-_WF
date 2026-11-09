# Аэродром — самолёты игрока и окно получения самолёта (клиент)

> **auto-create**, 2026-10-15/16 по коду до merge `origin/amnesia/fix`; актуализирован 2026-10-19 по коду
> после merge (в индексе, не закоммичен). Запуском не проверялось.
> Серверная сторона: `/workspace/server/.claude/docs/aerodrome-architecture.md` (`AerodromeUserComponent`,
> `AerodromePage`; готовит `server-analyst-lead`).

ГДД: [aerodrome-gdd.md](game-design/aerodrome-gdd.md) (по ТЗ пользователя 2026-10-15, записан по коду
до merge). После merge большая часть правил ГДД в клиентском коде не реализована, см.
[п.8](#tradeoffs) и [п.9](#gdd-link).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. [Классы и методы](#classes)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Аэродром хранит до восьми самолётов игрока, которые участвуют в бою кампании. Место самолёта выбирает
сервер по классу (`AirplaneType.TYPE_POSITION` на сервере): 0 — стратегический бомбардировщик,
1 — бомбардировщик, 2–3 — штурмовик, 4–7 — истребитель и тяжёлый истребитель. Позиция `p` в коде — слот
`8 − p` в ГДД (решение пользователя 2026-10-15). Новый самолёт встаёт в свободную позицию своего
класса, иначе заменяет самого слабого самолёта своего класса; ручной расстановки нет
([gdd-slots](game-design/aerodrome-gdd.md#gdd-slots)).

После merge от клиента области остались:

- **Окно получения самолёта** (`AirplaneGetPopup`): без замены — «ВЫБРАТЬ»; с заменой — сравнение двух
  самолётов, обмен местами и «ПРОДАЖА» нижнего самолёта. Единственный вызов — окно авиазавода военной
  базы ([п.7](#cls-airplanegetpopup)).
- **Константы и события**: `Vars.AerodromeAccessCampaignLevel` (5), `Vars.AutoSummonAccessLevel` (10, общий
  с поездом), `GameEvents.AERODROME_UPDATE` и `RADIO_TOWER_UPDATE`, поля `access` в `home.d.ts`,
  `FlyIconsAnimation.HOME_AERODROME_AIRPLANE_SCHEMES`. Все они объявлены, но читателей и эмиттеров
  у аэродрома нет (кроме полёта схем, [п.8](#tradeoffs)).
- **Файл `HomeScreenAerodrome.ts`** (бывшая плашка аэродрома) остался в дереве, но не подключён и
  ссылается на удалённые классы ([п.8](#tradeoffs) п.1).

Куда переехала функциональность. Окно аэродрома (стоянки 8 мест, карточки 4×2) теперь —
`MilitaryBaseAerodromePopup`, он открывается с карты военной базы. Призыв самолётов идёт через авиазавод
и штаб военной базы (`/ingame/militaryBase/*`), а не через радиовышку (`/ingame/aerodrome/summon`).
Окно прокачки радиовышки стало `MilitaryBaseAviationFactoryInfoPopup` (переименован
`RadioTowerUpgradePopup`). Это область «Военная база», здесь только ссылки; документа по ней нет.
Автопризыва самолётов, покупки схем самолёта за золото и плашки аэродрома на главном экране в коде
больше нет: плашка `HomeScreen.UIAerodrome` показывает только `HomeScreenMilitaryBase`.

Самолёты в бою (взлёт, воздушный бой, бомбы) — область «Бой» ([air-battle-architecture.md](air-battle-architecture.md)).
Доступ по уровню кампании — [campaign-architecture.md](campaign-architecture.md) (`#tradeoffs` п.14).
Туториал — [tutorial-architecture.md](tutorial-architecture.md). Схемы и самолёты в сумке, hold-ы —
[bag-architecture.md](bag-architecture.md).

<a id="references"></a>
## 2. Референсы

- **Поезд** ([train-architecture.md](train-architecture.md)) — прототип: `TankGetPopup` → `AirplaneGetPopup`
  (та же схема кнопок, обмена и анимации силы). Правила аэродрома свои, копии кода поезда находкой не
  считаются.
- **Военная база** — новая область merge (`src/views/home_screen/popups/military_base/**`), документа нет.

<a id="patterns"></a>
## 3. Паттерны

- **Окно = `IViewProvider` + `FlashLayout` + статический `publish`**: `FlashPublisher.publish(getAsGameFlash())`,
  параллельное окно (`setParallel(true)`), закрытие кликом по фону.
- **Шапка поверх окна**: конструктор `AirplaneGetPopup` зовёт `screen.pushHeaderZIndex(false)`, `onDestroy` —
  `popHeaderZIndex()` (появилось в merge).
- **Hold награды на время анимации**: `holdResource` синхронно в обработчике ответа, `releaseHold` в конце
  полёта иконок ([bag-architecture.md](bag-architecture.md)). Схемы самолёта так держат квесты,
  простой и бой кампании (`HomeScreenQuest`, `IdlePopup`, `CampaignBattleGround`).

<a id="class-list"></a>
## 4. Список классов

Область в коде после merge: `AirplaneGetPopup`, остаток `HomeScreenAerodrome` (не подключён), константы
и события из [п.1](#purpose). Удалены merge-ом: `AerodromePopup`, `RadioTowerFrame`,
`RadioTowerUpgradeInfoBtn` (`RadioTowerUpgradeBtn.ts`), `RadioTowerAutoSummonBtn`,
`RadioTowerAutoSummonPopup`, `AerodromeBuySchemesPopup`, `aerodrome.d.ts`, события
`RADIO_TOWER_START_AUTO_SUMMON`/`RADIO_TOWER_AUTO_SUMMON`/`RADIO_TOWER_STOP_AUTO_SUMMON`, aerodrome-часть
`HomeScreen` (`OnRadioTowerSummon`, `OnAirplaneAccept`/`Refuse`, `run/stopRadioTowerAutoSummon`,
`isRadioTowerAutoSummonTargetAirplane`, поле `autoRadioTower`). `RadioTowerUpgradePopup` переименован в
`military_base/MilitaryBaseAviationFactoryInfoPopup`.

<a id="anchors"></a>
## 5. Навигация (якоря)

- Классы — `#cls-<имя в нижнем регистре>`; метод с логикой — `#m-airplane-get-buttons` (кнопки окна
  получения). `#types` — типы и события, `#client-contract` — контракт с сервером.

<a id="class-nav"></a>
## 6. Оглавление по классам

- [AirplaneGetPopup](#cls-airplanegetpopup) — окно получения самолёта · [кнопки](#m-airplane-get-buttons)
- [HomeScreenAerodrome](#cls-homescreenaerodrome) — остаток плашки, не подключён
- [Типы и события](#types) · [Контракт с сервером](#client-contract)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-airplanegetpopup"></a>
### `AirplaneGetPopup` (`implements IViewProvider`)

ГДД: [gdd-summon](game-design/aerodrome-gdd.md#gdd-base-moved) (окно решения).
Конфиг: `receivedAirplane`, `replaceableAirplane | null`, `onAccept`, `onRefuse`, `onClose?`, `onExit?`.
Единственный вызов — `MilitaryBaseAviationFactoryPopup.BtnGetAirplane` после `/ingame/militaryBase/checkFactory`:
`onAccept` → `/acceptAirplane`, `onRefuse` → `/refuseAirplane`, `onClose` пустой, `onExit` не задаётся.

- `UIAirplaneGet` — без замены: панель «НОВЫЙ САМОЛЁТ» и параметры (высота панели считается по
  `AirplanePresets.ParamsHeight`); с заменой: заменяемый сверху, новый снизу, оба с параметрами
  (`AirplanePresets`).
<a id="m-airplane-get-buttons"></a>
- `UIButtons(up, down)` — без замены одна «ВЫБРАТЬ» → `onAccept`. С заменой «ВЫБРАТЬ» (обмен местами,
  `BtnSwap`) и «ПРОДАЖА»: продаётся нижний самолёт — `onRefuse` до обмена, `onAccept` после. Зелёной
  подсвечивается кнопка, ведущая к более сильному самолёту (если нижний мощнее — красная «ПРОДАЖА» слева,
  зелёная «ВЫБРАТЬ» справа).
- `BtnSwap` — меняет самолёты местами, показывает разницу силы (`animatePower`).
- `getAsGameFlash` — клик по фону закрывает окно и зовёт `onClose` без решения.
- `processTutorial` — указатель на «ВЫБРАТЬ» на шагах `TutorialUtils.FIRST_TRAIN`/`SECOND_TRAIN`
  (константы из merge, у аэродрома своих шагов нет), иначе `disable()`
  ([tutorial-architecture.md](tutorial-architecture.md) `#tradeoffs` п.6).

<a id="cls-homescreenaerodrome"></a>
### `HomeScreenAerodrome.ts` (остаток, не подключён)

Файл не изменён merge-ом и нигде не импортируется (`HomeScreen.UIAerodrome` создаёт только
`HomeScreenMilitaryBase`). Импортирует удалённый `AerodromePopup` и использует удалённый тип
`AerodromeRadioTowerJSON` и события `RADIO_TOWER_*` — не компилируется. Старое описание (таймер
взлёта, замок, полоса уровня, счётчик схем) — в тэге `pre-amnesia-merge`.

<a id="types"></a>
### Типы и события

- `aerodrome.d.ts` удалён; типы `AerodromeJSON`, `AerodromeRadioTowerJSON` нигде не объявлены, но ещё
  упоминаются: `battlefield.d.ts` (`aerodrome: AerodromeJSON`, читает `BattlefieldPopup`, область «Бой»),
  `GameEvents.RADIO_TOWER_UPDATE: EventName<AerodromeRadioTowerJSON>`, `HomeScreenAerodrome.ts`.
- `militaryBase.d.ts`: `AerodromePopupJSON { aerodrome: any }` (ответ `/ingame/aerodrome` для
  `MilitaryBaseAerodromePopup`).
- `home.d.ts`: `HomeScreenJSON.access: AccessJSON` с `aerodrome.level` — клиент не читает;
  `HomeScreenJSON.radioTower` удалён.
- `bag.d.ts`: `AirplaneJSON` (`type` — класс, `rank`, `stars`, `params`, `power`) — область «Сумка».
- `GameEvents`: `AERODROME_UPDATE`, `RADIO_TOWER_UPDATE` — объявлены, эмиттеров и подписчиков нет.
- `Vars`: `AerodromeAccessCampaignLevel = 5` (читателей нет, кроме `HomeScreenAerodrome.ts`),
  `AutoSummonAccessLevel = 10` (читает `TrainAutoSummonPopup`).

<a id="client-contract"></a>
### Контракт с сервером

Из `/ingame/aerodrome/*` клиент шлёт только `/ingame/aerodrome` (`MilitaryBaseAerodromePopup.requestData`,
ответ `aerodrome.airplanes[{position, airplaneUid | null}]`; на сервере `AerodromePage` теперь имеет один
маршрут `""`, остальные убраны). Роуты `summon`, `accept`, `refuse`, `autoData`, `upgradeData`,
`buySchemesData`, `buySchemes`, `devTools/aerodrome*` клиент больше не вызывает. Самолёт после призыва
в авиазаводе проходит через `/ingame/militaryBase/checkFactory`, `/acceptAirplane`, `/refuseAirplane`
(военная база, вне области). Схемы и самолёты в сумке приходят push-ом сумки (`ITEM_*`). Серверные роуты
и баланс — в серверном документе (проверить его актуальность, [п.8](#tradeoffs)).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Наблюдения по коду после merge, запуском не проверялись. Ошибки `tsc` от автора fix (удалённые типы и
классы в `HomeScreenAerodrome.ts`, `battlefield.d.ts`, `GameEvents`) пользователь чинить не просил.
Решения пользователя 2026-10-15/16 по старой реализации (расхождения с ГДД в
радиовышке) утратили предмет вместе с кодом; расхождения с ГДД — в [п.9](#gdd-link).

1. **Мёртвый и несобираемый код.** `HomeScreenAerodrome.ts` не подключён и ссылается на удалённое
   ([#types](#types)); `HomeScreen.ts:54` — неиспользуемый `interface RadioTowerAutoSummonParams`;
   `GameEvents.RADIO_TOWER_UPDATE` с удалённым типом; `AERODROME_UPDATE` без эмиттеров; в
   `ru.json` остались `homeScreen.aerodrome.access`, `homeScreen.takeoffTime` и часть `aerodromeScreen.*`
   (`MilitaryBaseAerodromePopup`, `AirplanePresets` и `AirplaneGetPopup` берут из `aerodromeScreen.airplanePopup.*`).
2. **Hold схем самолёта не снимается.** Квесты, простой и бой кампании ставят `holdResource` на
   `RESOURCE_AIRPLANE_SCHEME` и играют `FlyIconsAnimation.HOME_AERODROME_AIRPLANE_SCHEMES`
   (`HomeScreenQuest.ts:180-181`, `IdlePopup.ts:180,204`, `CampaignBattleGround.ts:142-146`);
   `FlyIconsAnimation.play` только эмитит `FLY_ICONS`, а подписчик с этим именем был лишь в
   `HomeScreenAerodrome.onFlyIcons` (не подключён). Остальные подписчики (`Header*Bar`, `HomeScreen` для
   схем танка) фильтруют по другому имени, `onEnd` не вызывается, `releaseHold` не выполняется
   ([bag-architecture.md#userbag-hold-leak](bag-architecture.md#userbag-hold-leak)). Правка вне области
   (сумка/награды), нужна пользователю.
3. **Закрытие окна получения по фону не принимает решение.** `AirplaneGetPopup` по клику на фон зовёт
   `onClose` (пустой у `MilitaryBaseAviationFactoryPopup`); что должен видеть игрок и остаётся ли самолёт
   в слоте фабрики — правило военной базы, в ГДД аэродрома не описано ([п.9](#gdd-link)).
4. **Автопризыва с продажей при свободной позиции больше нет.** Правило
   [gdd-auto-summon](game-design/aerodrome-gdd.md#gdd-base-moved) о продаже самолёта на свободное место
   в клиенте не выражено ничем; в окне получения при свободной позиции кнопки продажи нет
   ([gdd-summon](game-design/aerodrome-gdd.md#gdd-base-moved)).
5. **Самолёт без данных в сумке роняет `MilitaryBaseAerodromePopup`** (`UIMain`/`UIFooter` берут
   `Globals.bag.getAirplane(uid)` без проверки и читают `data.uid`, `data.id`). Прежний `AerodromePopup`
   имел ту же слабость; окно теперь вне области, учтено здесь ссылкой.
6. **Мёртвые ветки в `AirplaneGetPopup`.** `onExit` в конфиге никто не передаёт; шаги туториала
   `FIRST_TRAIN`/`SECOND_TRAIN` у аэродрома не используются (в военной базе указатель попадёт на кнопку
   только в туториале поезда — кандидат на удаление).
7. **Серверная сторона, возможно, устарела.** `AerodromePage` на сервере уже без маршрутов призыва,
   прокачки, автопризыва и покупки схем; серверный документ нужно сверить (задача `server-analyst-aerodrome`).

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД области — [aerodrome-gdd.md](game-design/aerodrome-gdd.md) (не менялся). Правило → клиентская реализация
после merge:

| Правило ГДД | Где на клиенте после merge | Расхождение |
|---|---|---|
| [gdd-access](game-design/aerodrome-gdd.md#gdd-base-moved) — с 5-го уровня, замок на главном экране | плашки аэродрома нет; `Vars.AerodromeAccessCampaignLevel` не используется | ГДД ↔ код: вопрос 1 |
| [gdd-classes](game-design/aerodrome-gdd.md#gdd-classes) — 5 классов | `AirplaneJSON.type`; иконка класса на стоянке `MilitaryBaseAerodromePopup` | — |
| [gdd-slots](game-design/aerodrome-gdd.md#gdd-slots) — 8 мест, ставит игра | `MilitaryBaseAerodromePopup.UIBase/UIFooter` (вне области); расстановка — сервер | — |
| [gdd-takeoff-order](game-design/aerodrome-gdd.md#gdd-takeoff-order) — подпись «В БОЮ» | в `MilitaryBaseAerodromePopup` подписи «В БОЮ» и подписок на `BATTLE_*` нет | ГДД ↔ код: вопрос 2 |
| [gdd-summon](game-design/aerodrome-gdd.md#gdd-base-moved) — призыв за схему на радиовышке, окно решения | окно решения — `AirplaneGetPopup`; призыв — штаб и авиазавод военной базы, не радиовышка | ГДД ↔ код: вопрос 3 |
| [gdd-radio-tower-level](game-design/aerodrome-gdd.md#gdd-base-moved) — уровни радиовышки | радиовышки в клиенте нет; `MilitaryBaseAviationFactoryInfoPopup` — уровень авиазавода | ГДД ↔ код: вопрос 3 |
| [gdd-auto-summon](game-design/aerodrome-gdd.md#gdd-base-moved) | автопризыва самолётов в клиенте нет | ГДД ↔ код: вопрос 4 |
| [gdd-buy-schemes](game-design/aerodrome-gdd.md#gdd-base-moved) — 3 набора схем за золото | окна покупки схем самолёта нет | ГДД ↔ код: вопрос 5 |

<a id="file-map"></a>
## 10. Карта файлов компонента

<a id="file-map-direct"></a>
### Файлы прямого влияния

- `src/views/home_screen/popups/airplane/AirplaneGetPopup.ts` — окно получения самолёта.
- `src/views/home_screen/HomeScreenAerodrome.ts` — остаток плашки аэродрома, не подключён, не компилируется.
- `assets-src/atlas/aerodrome_screen/` — атлас (пакет `AerodromeScreen`), теперь грузит
  `MilitaryBaseAerodromePopup`; файлы `air`, `level_bar*`, `panel`, `radio`, `summon` удалены merge-ом,
  добавлен `bg_bot.png`.

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

- `src/views/home_screen/popups/military_base/MilitaryBaseAerodromePopup.ts`,
  `base/MilitaryBaseAerodrome.ts`, `MilitaryBasePopup.ts` (кнопка открытия) — новое окно аэродрома
  (область «Военная база», документа нет).
- `src/views/home_screen/popups/military_base/MilitaryBaseAviationFactoryPopup.ts` — единственный
  вызывающий `AirplaneGetPopup`; `MilitaryBaseAviationFactoryInfoPopup.ts` — бывший `RadioTowerUpgradePopup`;
  `militaryBase.d.ts` — `AerodromePopupJSON`.
- `src/views/home_screen/HomeScreen.ts` — `UIAerodrome` (только `HomeScreenMilitaryBase`), неиспользуемый
  `RadioTowerAutoSummonParams`.
- `src/views/home_screen/home.d.ts` — `AccessJSON`/`AerodromeAccessJSON`.
- `src/plain/GameEvents.ts` — `AERODROME_UPDATE`, `RADIO_TOWER_UPDATE`.
- `src/plain/Vars.ts` — `AerodromeAccessCampaignLevel`, `AutoSummonAccessLevel`.
- `src/shared/animations/FlyIconsAnimation.ts` — константа `HOME_AERODROME_AIRPLANE_SCHEMES`.
- `src/views/home_screen/popups/train/TrainAutoSummonPopup.ts` — читает `AutoSummonAccessLevel`.
- `src/views/home_screen/HomeScreenQuest.ts`, `popups/idle/IdlePopup.ts`,
  `campaign/CampaignBattleGround.ts` — полёт и hold схем самолёта.
- `src/views/home_screen/popups/battlefield/BattlefieldPopup.ts`, `battlefield.d.ts` — читают `AerodromeJSON`
  (область «Бой»).
- `src/views/popups/AirplaneInfoPopup.ts` — окно самолёта (общее с боем; в merge добавлен
  `pushHeaderZIndex`/`popHeaderZIndex`).
- `src/presets/AirplanePresets.ts` — вёрстка самолёта и параметров в окне получения.
- `src/views/home_screen/popups/bag/bag.d.ts`, `src/plain/user/UserBag.ts`, `src/plain/items/ItemId.ts` —
  `AirplaneJSON`, `getAirplane`, `RESOURCE_AIRPLANE_SCHEME`.
- `src/plain/TutorialUtils.ts` — `FIRST_TRAIN`/`SECOND_TRAIN` в `AirplaneGetPopup`.
- `src/presets/ItemsPresets.ts` — иконка схемы самолёта в списках наград.
- `assets-src/raw/lang/ru/ru.json` — ключи `aerodromeScreen.*`, `homeScreen.aerodrome.access`,
  `homeScreen.takeoffTime`.
- `tools/src/config.yaml` — пакет `AerodromeScreen`.
