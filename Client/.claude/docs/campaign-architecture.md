# Кампания — бои на главном экране, прогресс и карта регионов (клиент)

> **auto-create** — документ составлен по существующему коду, 2026-10-15; актуализирован после
> merge `origin/amnesia/fix` (2026-10-19). Запуском не проверялось.
> Серверная сторона (`CampaignUserComponent`, `CampaignPage`):
> `/workspace/server/.claude/docs/campaign-architecture.md` (auto-create, 2026-10-15); контракт ниже с ним сверен.
> Ящики с золотом на поле боя описаны в [`airdrop-architecture.md`](airdrop-architecture.md) и здесь
> не повторяются.
> Рейтинговые бои кампании (PvP, `RankedProfile`, `CampaignRankedHistory`, `RankedResultJSON`) пришли с
> merge и отдельно не документированы: здесь только места стыка с кампанией ([#ranked-link](#ranked-link)).

ГДД: [campaign-gdd.md](game-design/campaign-gdd.md) (одна копия на client и server).

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
10. [Карта файлов](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Кампания — бесконечная цепочка автоматических боёв, которые идут фоном на главном экране. Игрок не
управляет боем: его танки из ангара сражаются с противником, сервер выдаёт следующий бой, клиент его
проигрывает и сообщает результат. Победа продвигает игрока на один уровень кампании.

Структура прогресса (константы на сервере, `CampaignUserComponent`):

- **уровень** (`level`) — число пройденных миссий, с нуля;
- **глава** (`chapter`) — 5 миссий; `mission` — номер миссии внутри главы, 0..4;
- **регион** (`region`) — 50 миссий, то есть 10 глав.

Клиент получает все четыре числа в `CampaignJSON` и сам их не вычисляет, кроме карты регионов (см.
[#tradeoffs](#tradeoffs), п.9).

Что видит игрок:

- **Поле боя** на главном экране (`CampaignBattleGround`). Бой идёт постоянно; при открытом окне он
  продолжается в фоновом режиме без анимаций.
- **Награды за уничтожение** вражеского танка: серебро и иногда схема танка или самолёта. Иконки
  летят от подбитого танка в шапку или к поезду/аэродрому.
- **Плашка прогресса** слева на главном экране (`HomeScreen.UICampaignProgress`): «Ур. N» (текущий,
  то есть `level + 1`), шкала из четырёх точек по миссиям главы и иконка золота — награда за главу.
- **Завершение главы**: шкала заполняется целиком, золото летит в шапку.
- **Завершение региона**: открывается карта (`CampaignPopup`) с анимацией — текущая локация
  становится пройденной, на ней появляется флаг, загорается следующая. После десятой локации карта
  сменяется следующей.
- **Карта по клику** на плашку прогресса: 10 локаций, пройденные отмечены флагом, на текущих и
  будущих подписан уровень, к которому локация будет пройдена.
- **Плашка результата** боя (победа/поражение) поверх поля после каждого боя; в рейтинговом бою
  дополняется блоком рейтинга и места ([#ranked-link](#ranked-link)).

Уровень кампании открывает другие функции: аэродром (`Vars.AerodromeAccessCampaignLevel = 5`, константа
в `Vars.ts`; прежний потребитель `HomeScreenAerodrome` после merge не подключён к `HomeScreen`) и
автопризыв поезда (`Vars.AutoSummonAccessLevel`, сравнивается с `campaignLevel` из ответа окна).
Квест типа `CAMPAIGN_LEVEL_UP` показывает прогресс 0/1.

<a id="lifecycle"></a>
### Жизненный цикл боя

ГДД: [#gdd-levels](game-design/campaign-gdd.md#gdd-levels), [#gdd-defeat](game-design/campaign-gdd.md#gdd-defeat), [#gdd-level-transition](game-design/campaign-gdd.md#gdd-level-transition).

1. `HomeScreen` после построения вызывает `startNextBattle()`. Метод сразу вызывает `battleRequest()`:
   запрос `/ingame/campaign/battle`. Ожидания туториала перед запросом больше нет.
2. Ответ `battle` передаётся в `battleGround.battle.create(this.battleGround, battle, Globals.account.id)`,
   бой стартует, `CampaignBattleGround.onBattleStart` эмитит `BATTLE_BEGIN` и, если у противника есть
   лига (рейтинговый бой), показывает его плашку `RankedProfile`.
3. По ходу боя `CampaignBattleGround` переизлучает события боя в глобальный `GameEvents.emitter`
   (`BATTLE_TANK_*`, `BATTLE_AIRPLANE_*`) и при уничтожении врага с флагом `rewarded` запрашивает
   награду.
4. На `BattleResultEvent` клиент шлёт `/ingame/campaign/battleResult` с `win`, посчитанным локальной
   симуляцией. Сервер при `win = true` сам пересимулирует бой и решает, засчитать ли победу. В ответе
   может прийти `rankedResult` (рейтинговый бой).
5. После ответа поле закрывается шторкой (1 с), пересоздаются слои `battlefield`/`air`/`animations`,
   и вызывается `HomeScreen.campaignChapterComplete` (пришли `rewards` и окон нет) либо
   `campaignMissionComplete`. Оба в итоге снова вызывают `startNextBattle()`. Плашку результата
   показывает `HomeScreen.onCampaignBattleEnded` по событию `CAMPAIGN_BATTLE_ENDED`.

<a id="references"></a>
## 2. Референсы

Внешних референсов нет. Ближайшие соседи по коду: `airdrop-architecture.md` (тот же
`CampaignBattleGround`), `tutorial-architecture.md` (стык с туториалом; в ответах `/campaign/battle` и
`/campaign/battleResult` клиент поле `tutorial` больше не читает), `bag-architecture.md` (`holdResource`/`releaseHold`).

<a id="patterns"></a>
## 3. Паттерны

- **Наследование поля боя.** `CampaignBattleGround extends BattleGround`: базовый класс рисует бой,
  наследник переопределяет `on*Event`, вызывает `super` и добавляет кампанийную часть (награды,
  результат, глобальные события).
- **Переизлучение событий боя.** События боя внутри `BattleGround` идут через локальный
  `eventEmitter`; кампания дублирует их в глобальный `GameEvents.emitter`, чтобы на них могли
  подписаться главный экран, военная база и авиаудар. Для плашки результата с рейтингом добавлено
  отдельное событие `CAMPAIGN_BATTLE_ENDED` с данными `CampaignBattleEndedData`.
- **Фоновый режим.** `BattleGround.isBackgroundMode()` истинно, пока открыто хотя бы одно окно
  (счётчик по `FlashOverlay`). В фоне награды начисляются без анимаций, а завершение главы идёт по
  ветке обычной миссии.
- **Удержание ресурса на время анимации.** Ресурс награды сразу удерживается в сумке
  (`Globals.bag.holdResource`), чтобы шапка не показала его раньше, чем долетят иконки; снимается в
  колбэке `FlyIconsAnimation` (`releaseHold`). Подробно — `bag-architecture.md`.
- **Окно с колбэком выхода.** `CampaignPopup` принимает `onExit` и вызывает его на
  `Layout.EVENT_DESTROYED`; так `HomeScreen` продолжает цепочку боёв после анимации региона (общий
  приём — `popup-queue-pattern.md`).
- **Ленивая загрузка ассетов окна.** `CampaignPopup.publish` подгружает пакет `CampaignScreen` перед
  показом (`asset-packaging.md`).

<a id="class-list"></a>
## 4. Список классов

Документ описывает существующий код.

- `CampaignBattleGround` — `src/views/home_screen/campaign/CampaignBattleGround.ts`
- `CampaignPopup` — `src/views/home_screen/popups/campaign/CampaignPopup.ts`
- `CampaignLevelRewardsPopup` — `src/views/home_screen/popups/campaign/CampaignLevelRewardsPopup.ts`
  (нигде не открывается)
- `CampaignBattleEndedData` — `src/views/home_screen/campaign/CampaignBattleEndedData.ts`
  (данные события `CAMPAIGN_BATTLE_ENDED`: `result: BattleResultEvent`, `ranking?: RankedResultJSON`)
- Рейтинговая часть (только упоминание, [#ranked-link](#ranked-link)): `RankedProfile`
  (`src/views/home_screen/campaign/RankedProfile.ts`), `CampaignRankedHistory`
  (`src/views/home_screen/popups/campaign/CampaignRankedHistory.ts`)
- Типы — `src/views/home_screen/popups/campaign/campaign.d.ts`, `CampaignJSON` в
  `src/views/home_screen/home.d.ts`
- Кампанийная часть `HomeScreen` — `src/views/home_screen/HomeScreen.ts`

<a id="anchors"></a>
## 5. Навигация (якоря)

| Якорь | Что там |
|---|---|
| [#lifecycle](#lifecycle) | цикл боя от запроса до следующего боя |
| [#cls-campaignbattleground](#cls-campaignbattleground) | поле боя кампании |
| [#m-cbg-rewards](#m-cbg-rewards) | награды за уничтожение танков и самолётов |
| [#m-cbg-result](#m-cbg-result) | отправка результата боя |
| [#cls-homescreen](#cls-homescreen) | кампанийная часть главного экрана |
| [#m-hs-progress](#m-hs-progress) | плашка прогресса и dev-кнопки |
| [#m-hs-complete](#m-hs-complete) | завершение миссии и главы |
| [#m-hs-battle](#m-hs-battle) | запуск следующего боя |
| [#cls-campaignpopup](#cls-campaignpopup) | карта регионов |
| [#cls-campaignlevelrewardspopup](#cls-campaignlevelrewardspopup) | окно наград уровня (не используется) |
| [#ranked-link](#ranked-link) | связь кампании с рейтинговыми боями |
| [#types](#types) | типы данных |
| [#client-contract](#client-contract) | контракт с сервером |
| [#consumers](#consumers) | кто ещё читает уровень кампании |
| [#tradeoffs](#tradeoffs) | известные проблемы |
| [#file-map](#file-map) | карта файлов |

<a id="class-nav"></a>
## 6. Оглавление по классам

- [`CampaignBattleGround`](#cls-campaignbattleground) — [награды](#m-cbg-rewards),
  [результат боя](#m-cbg-result)
- [`HomeScreen` (кампанийная часть)](#cls-homescreen) — [прогресс](#m-hs-progress),
  [завершение](#m-hs-complete), [бой](#m-hs-battle)
- [`CampaignPopup`](#cls-campaignpopup)
- [`CampaignLevelRewardsPopup`](#cls-campaignlevelrewardspopup)
- [Рейтинговые бои](#ranked-link), [типы](#types), [контракт](#client-contract), [потребители](#consumers)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-campaignbattleground"></a>
### `CampaignBattleGround` (`src/views/home_screen/campaign/CampaignBattleGround.ts`)

Поле боя кампании на главном экране, наследник `BattleGround`. Создаётся один раз в
`HomeScreen` (`layout.add(this.battleGround = new CampaignBattleGround(this))`), живёт вместе с
экраном. Хранит ссылку на `HomeScreen` и экземпляр `AirDrop` (см.
[airdrop-architecture.md#cls-campaignbattleground](airdrop-architecture.md#cls-campaignbattleground)).

- `constructor(screen)` — в dev-режиме добавляет переключатель скорости боя (`UISpeed`), создаёт
  `AirDrop` и скрытую плашку противника `RankedProfile` (слой `opponent`).
- `onBattleStart()` — вызывает `super`, эмитит `BATTLE_BEGIN`; если лига противника не `-1`
  (рейтинговый бой), показывает `RankedProfile` с именем, силой, лигой, рейтингом и местом
  противника.
- `UISpeed()` — dev-кнопки «медленнее/быстрее» с подписью `xN`; вызывают `battle.slowed()`/
  `battle.faster()`, перестраивают себя и `applyTimeScale()`.
- `applyTimeScale()` — проходит по дереву слоёв и выставляет `timeScale` уже запущенным Spine-
  анимациям (у снаряда танка базовый множитель 0.4).
- Переизлучатели в `GameEvents.emitter` (каждый вызывает `super` и эмитит одноимённое событие):
  `onTankSpawnEvent` → `BATTLE_TANK_SPAWN`, `onTankReplacedEvent` → `BATTLE_TANK_REPLACED`,
  `onTankRechargeEvent` → `BATTLE_TANK_RECHARGE`, `onTankAttackEvent` → `BATTLE_TANK_ATTACK`,
  `onTankTakeDamageEvent` → `BATTLE_TANK_TAKE_DAMAGE`, `onAirplanePrepareTakeoffEvent`,
  `onAirplaneTakeoffEvent`, `onAirplaneSpawnEvent`, `onAirplaneReplacedEvent`,
  `onAirplaneRechargeEvent`, `onAirplaneAttackEvent`, `onAirplaneTakeDamageEvent` → соответствующие
  `BATTLE_AIRPLANE_*`; `BATTLE_BEGIN` эмитит `onBattleStart` (см. выше).

<a id="m-cbg-rewards"></a>
#### Награды за уничтожение

ГДД: [#gdd-kill-reward](game-design/campaign-gdd.md#gdd-kill-reward) (за самолёты наград нет).

- `onTankDestroyedEvent(event)` (ГДД [#gdd-kill-reward](game-design/campaign-gdd.md#gdd-kill-reward)) — если `event.rewarded`, шлёт `/ingame/campaign/battleTankReward`
  с `tankId`. Ответ без `rewards` (сервер достиг лимита серебра) ничего не показывает. В фоновом
  режиме анимации нет, ресурсы просто начислены. На экране для каждого ресурса из ответа —
  серебро, схема танка, схема самолёта — ставится удержание с тегом
  `CampaignGround::onTankDestroyedEvent::<ресурс><uid танка>` (uid разводит параллельные награды) и
  запускается `FlyIconsAnimation` от позиции танка к шапке, поезду или аэродрому; в конце
  анимации удержание снимается.
- `onAirplaneDestroyedEvent(event)` — если `event.rewarded`, шлёт `/ingame/campaign/battleAirplaneReward`
  с `airplaneId`. Ответ не используется: сервер ресурсов не выдаёт, запрос нужен для квестов и
  достижений. Затем эмитит `BATTLE_AIRPLANE_DESTROYED`.

<a id="m-cbg-result"></a>
#### Результат боя

ГДД: [#gdd-levels](game-design/campaign-gdd.md#gdd-levels), [#gdd-defeat](game-design/campaign-gdd.md#gdd-defeat), [#gdd-level-transition](game-design/campaign-gdd.md#gdd-level-transition).

- `onBattleResultEvent(event)` — вызывает `super` (очищает списки юнитов), выключает плашку
  противника (`RankedProfile.disable()`), считает `isWin` по
  `event.winnerUid` и шлёт `/ingame/campaign/battleResult` с `win`. При успешном ответе:
  - в dev-режиме сверяет локальную симуляцию с серверной (`BattleAnalyzer.check`);
  - если пришли `rewards`, удерживает золото главы с тегом
    `HomeScreen::campaignChapterComplete::RESOURCE_GOLDEN_COINS` (снимает его `HomeScreen`);
  - отключает интерактивность слоя `air`, проигрывает шторку и в её середине пересоздаёт слои поля
    боя, затем вызывает `homeScreen.campaignChapterComplete(campaign, rewards)` (есть `rewards` и не
    фоновый режим) или `homeScreen.campaignMissionComplete(campaign)`;
  - эмитит глобальный `BATTLE_ENDED` и затем `CAMPAIGN_BATTLE_ENDED` с `{ result: event, ranking:
    response.rankedResult }`.
  При ошибке ответа ничего не происходит, следующий бой не запрашивается ([#tradeoffs](#tradeoffs), п.2).

<a id="cls-homescreen"></a>
### `HomeScreen` — кампанийная часть (`src/views/home_screen/HomeScreen.ts`)

Главный экран владеет состоянием кампании (`this.data.campaign: CampaignJSON` из `HomeScreenJSON`),
полем боя (`battleGround`) и плашкой прогресса. Остальное содержимое экрана к кампании не относится.

<a id="m-hs-progress"></a>
#### Плашка прогресса

ГДД: [#gdd-progress-hud](game-design/campaign-gdd.md#gdd-progress-hud).

- `UICampaignProgress(mission?)` — вертикальная плашка: подпись `homeScreen.campaign.level` с
  `level + 1`, четыре точки шкалы (синих `mission` штук), синяя полоса длиной
  `min(max(0, mission - 1), 4) * 0.25`, иконка золота `icon` (точка старта анимации золота главы).
  Клик открывает `CampaignPopup` с текущим `region`. Параметр `mission` нигде не передаётся.
- Dev-кнопки (только `Globals.isDevTools()`): `+`, `+50`, `-50`, `-` шлют
  `/ingame/devTools/campaignAddLevel` или `/campaignRemoveLevel` с `value`. Все четыре обработчика
  одинаковы: записать `campaign`, эмитить `CAMPAIGN_UPDATE`, пересоздать плашку.

<a id="m-hs-complete"></a>
#### Завершение миссии и главы

ГДД: `campaignMissionComplete` — [#gdd-levels](game-design/campaign-gdd.md#gdd-levels); `campaignChapterComplete` — [#gdd-chapter-reward](game-design/campaign-gdd.md#gdd-chapter-reward), [#gdd-map](game-design/campaign-gdd.md#gdd-map).

- `campaignMissionComplete(data)` — записывает `data.campaign`, эмитит `CAMPAIGN_UPDATE`,
  пересоздаёт плашку, вызывает `processTutorial()` и через 1,5 с `startNextBattle()`.
- `campaignChapterComplete(data, rewards)` — временно ставит `this.data.campaign.mission = 5`, чтобы
  шкала показалась заполненной, и пересоздаёт плашку. Если в `chapterRewards` есть золото,
  запускает полёт пяти иконок от `icon` плашки к шапке и в конце снимает удержание
  `HomeScreen::campaignChapterComplete::RESOURCE_GOLDEN_COINS`. Через 1,5 с:
  - если в `rewards` есть `regionRewards` (сервер шлёт пустой массив как признак смены региона) —
    открывает `CampaignPopup` с `animated: true` и **старым** регионом, а продолжение передаёт в
    `onExit`;
  - иначе сразу выполняет продолжение.
  Продолжение: записать `data`, эмитить `CAMPAIGN_UPDATE`, пересоздать плашку, `processTutorial()`,
  `startNextBattle()`.

<a id="m-hs-battle"></a>
#### Запуск боя и плашка результата

ГДД: `onBattleBegin`, `onBattleEnded` — [#gdd-level-transition](game-design/campaign-gdd.md#gdd-level-transition).

- `startNextBattle()` — тонкая обёртка: сразу вызывает `battleRequest()` (ожидание туториала
  убрано merge'ем; обёртка осталась как точка цепочки, см. [#tradeoffs](#tradeoffs), п.4).
- `battleRequest()` — `/ingame/campaign/battle`; при успехе создаёт бой
  `battleGround.battle.create(this.battleGround, response.battle, Globals.account.id)`. При ошибке
  ответа не повторяет; ошибку промиса только логирует.
- `onBattleBegin()` — плавно убирает плашку результата прошлого боя.
- `onCampaignBattleEnded(data)` — подписан на `CAMPAIGN_BATTLE_ENDED`; показывает плашку
  победы/поражения (`UIBattleResult(isWin, data.ranking)`) по `data.result.winnerUid`, то есть по
  локальному результату. Подписка на `BATTLE_ENDED` и пустой `onBattleEvent` удалены.
- Тик экрана (`App.tick`) вызывает `battleGround.battle.update()`; `onDestroy` — `battle.clear()`.

<a id="cls-campaignpopup"></a>
### `CampaignPopup` (`src/views/home_screen/popups/campaign/CampaignPopup.ts`)

Полноэкранная карта из 10 локаций (одна локация = один регион). Окно с тегом `LOWER_FLASH_TAG`
(главный экран под ним скрывается), без кнопки закрытия и без закрытия по фону; закрывается
переходом через нижнее меню (`Footer` → `flashOverlay.clear()`) или само в конце анимации.

ГДД: [#gdd-map](game-design/campaign-gdd.md#gdd-map), термины — [#gdd-terms](game-design/campaign-gdd.md#gdd-terms) (`getLevel`, анимации смены региона).

Конфиг: `region` (абсолютный номер региона), `animated`, `rewards` (не используется), `onExit`.

- `publish(screen, config)` — грузит пакет ассетов `CampaignScreen`, затем публикует окно.
- `onCreate()` — `regionIndex = region % 10` (номер локации на текущей карте), строит карту; при
  `animated` блокирует экран (`setBlockInteractive(true)`) и запускает `animationRegionComplete`.
- `onDestroy()` — вызывает `onExit`.
- `getLevel(id)` — уровень, к которому будет пройдена локация: `(region - regionIndex) * 50 + id * 50`
  (50 — число миссий в регионе, продублировано с сервера).
- `UIMain()` — фон `map.png`, 10 локаций по фиксированным координатам, границы, стрелки.
- `UILocation(id)` — состояние по `regionIndex - id`: `next` (текущая), `done` (пройдена), флаг
  (пройдена) или иконка-ящик (не пройдена), подпись уровня у текущей и будущих. Кнопка открытия
  `CampaignLevelRewardsPopup` закомментирована.
- `UIArrows()`, `UIArrow2/3/9/12()` — стрелка-указатель к текущей локации (видна только у
  `regionIndex`).
- `animationRegionComplete()` — текущая локация переходит из `next` в `done`, стрелка гаснет; через
  1,5 с гаснет ящик и запускается `animationNoReward()` → `animationNextRegion()`; через 3,5 с
  появляется флаг и гаснет подпись уровня.
- `animationNextRegion()` — подсвечивает следующую локацию и её стрелку и через 2 с снимает
  блокировку экрана и закрывает окно. Если следующая локация за пределами карты, вызывает
  `animationNextMap()`.
- `animationNextMap()` — затемнение, `regionIndex = -1`, перестроение карты (все локации не пройдены),
  затем `animationNextRegion()` для локации 0.
- `animationReward()` — анимация вылета ящика с наградами региона; не вызывается
  ([#tradeoffs](#tradeoffs), п.6).
- `getAsGameFlash()`, `view()` — обвязка окна.

<a id="cls-campaignlevelrewardspopup"></a>
### `CampaignLevelRewardsPopup` (`src/views/home_screen/popups/campaign/CampaignLevelRewardsPopup.ts`)

ГДД: [#gdd-map](game-design/campaign-gdd.md#gdd-map) (по ГДД у окна содержимого нет).

Окно «Награда» для локации: запрашивает `/ingame/campaign/levelRewards` с `level`, показывает
заголовок, крестик и текст `campaignScreen.rewardsInfo`. Полученные `rewards` не отрисовываются
(список наград пуст). Окно нигде не открывается ([#tradeoffs](#tradeoffs), п.6).

- `publish(screen, config)` — запрос, затем показ (параллельное окно, закрытие по фону).
- `requestData()`, `onCreate()`, `onDestroy()` (вызывает `onExit`), `UIMain()`, `UIContent()`,
  `getAsGameFlash()`, `view()`.

<a id="ranked-link"></a>
### Связь с рейтинговыми боями (только упоминание)

Рейтинговые бои (PvP кампании) пришли с merge, их правила и экраны здесь не описаны. Точки стыка:

- `CampaignBattleGround.onBattleStart` показывает плашку противника `RankedProfile`, если
  `opponent.getRanking().getLeagueId() !== -1`; `onBattleResultEvent` её выключает.
- В ответе `/battleResult` приходит `rankedResult?: RankedResultJSON` (`src/types/battle.d.ts`); он
  уходит в `CAMPAIGN_BATTLE_ENDED` и рисуется в `HomeScreen.UIBattleResult` (блок рейтинга и места).
- `CampaignRankedHistoryPopup` (`popups/campaign/CampaignRankedHistory.ts`, запрос
  `/ingame/campaign/rankedHistory`, типы `CampaignRankedHistoryJSON` в `campaign.d.ts`) открывается из
  `RatingCampaignRankingSection`; статус — `/ingame/campaign/rankedHistoryStatus`.

<a id="types"></a>
### Типы

- `CampaignJSON` (`home.d.ts`) — `level`, `region`, `chapter`, `mission`. Приходит в `HomeScreenJSON`,
  в ответах `/battleResult` и dev-роутов.
- `CampaignLevelRewardsJSON` (`campaign.d.ts`) — `chapterRewards: any[]`, `regionRewards: any[]`.
- `CampaignPopupJSON` (`campaign.d.ts`) — пустой, не используется.
- `CampaignRankedHistoryJSON`, `CampaignRankedHistoryEntryJSON` (`campaign.d.ts`) — история рейтинговых
  боёв ([#ranked-link](#ranked-link)).
- `CampaignBattleEndedData` — данные события `CAMPAIGN_BATTLE_ENDED`.
- `GameEvents.CAMPAIGN_UPDATE: EventName<CampaignJSON>` — эмитит только клиент (`HomeScreen`), с
  сервера push не приходит.
- `GameEvents.CAMPAIGN_BATTLE_ENDED: EventName<CampaignBattleEndedData>` — эмитит
  `CampaignBattleGround` после `BATTLE_ENDED`; слушает `HomeScreen`.

<a id="client-contract"></a>
### Контракт с сервером

Роуты `CampaignPage` (`/ingame/campaign/*`); airDrop-роуты — в
[airdrop-architecture.md#client-contract](airdrop-architecture.md#client-contract).

| Роут | Запрос | Ответ | Клиент |
|---|---|---|---|
| `/battle` | — | `battle: BattleDataJSON` (поле `tutorial` клиент не читает) | `HomeScreen.battleRequest` |
| `/battleTankReward` | `tankId` | `rewards?: ItemJSON[]` (серебро, иногда схема); без `rewards`, если лимит серебра | `CampaignBattleGround.onTankDestroyedEvent` |
| `/battleAirplaneReward` | `airplaneId` | пусто | `CampaignBattleGround.onAirplaneDestroyedEvent` |
| `/battleResult` | `win` | `campaign`, `rewards?: { chapterRewards, regionRewards? }`, `rankedResult?: RankedResultJSON`, `battleResult?` (только dev); `tutorial` клиент не читает | `CampaignBattleGround.onBattleResultEvent` |
| `/levelRewards` | `level` | `rewards: { rewards: [] }` — заглушка, `level` игнорируется, ветка ошибки недостижима | `CampaignLevelRewardsPopup` (не открывается) |
| `/ingame/devTools/campaignAddLevel`, `/campaignRemoveLevel` | `value` | `campaign` | dev-кнопки плашки |

Особенности:

- `win = false` сервер принимает как есть и возвращает только `campaign`. `win = true` сервер
  проверяет собственной симуляцией (`completeBattle`), и победу засчитывает только она.
- `rewards` приходит только при смене главы: `chapterRewards` — золото главы; `regionRewards` —
  всегда пустой массив, его наличие означает смену региона.
- В туториале сервер засчитывает победу без симуляции. Клиент ответ `tutorial` в этих роутах больше не
  записывает (проверить с сервером, [#tradeoffs](#tradeoffs), п.15).

<a id="consumers"></a>
### Кто ещё читает уровень кампании

ГДД: пороги доступа по уровню — [#gdd-levels](game-design/campaign-gdd.md#gdd-levels); `ProfileSection` — [#gdd-progress-hud](game-design/campaign-gdd.md#gdd-progress-hud).

- `HomeScreenMilitaryBase` — подписан на `BATTLE_BEGIN`, `BATTLE_ENDED`, `BATTLE_AIRPLANE_PREPARE_TAKEOFF`,
  `BATTLE_AIRPLANE_TAKEOFF` (военная база, новая область merge, не документирована).
- `HomeScreenAerodrome` — старая плашка: доступ `campaign.level >= Vars.AerodromeAccessCampaignLevel`,
  подписки на `CAMPAIGN_UPDATE`, `BATTLE_BEGIN`, `BATTLE_ENDED`, `BATTLE_AIRPLANE_*`; из `HomeScreen` не
  создаётся (используется `HomeScreenMilitaryBase`), файл остался и ссылается на удалённое.
- `BattleAir`, `BattleAirstrike` — события самолётов и урона танкам.
- `TrainAutoSummonPopup` — `campaignLevel` из своего ответа против `Vars.AutoSummonAccessLevel`.
  Автопризыв радиовышки удалён вместе с `RadioTower*`.
- `ProfileSection` — `campaignLevel` в профиле («{0} УР»).
- `HomeScreenQuest` — квест `CAMPAIGN_LEVEL_UP` (прогресс 0/1).
- `RatingCampaignSection`, `RatingCampaignRankingSection` — рейтинг по кампании (`/ingame/rating/campaign`) и рейтинговая таблица.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

1. **Золото главы зависает в удержании при открытом окне.** `CampaignBattleGround.ts:256-261`
   удерживает золото при любом ответе с `rewards`, а снимает удержание только
   `HomeScreen.campaignChapterComplete` (`HomeScreen.ts:1020-1025`). В фоновом режиме
   (`CampaignBattleGround.ts:276-280`) вызывается `campaignMissionComplete`, и `releaseHold` не
   происходит: шапка до перезахода показывает золота меньше, чем есть. Вместе с этим в фоне
   пропускается анимация главы и карта региона. ГДД: [#gdd-chapter-reward](game-design/campaign-gdd.md#gdd-chapter-reward), [#gdd-map](game-design/campaign-gdd.md#gdd-map). ГДД, отложено 2026-10-15.
2. **Цепочка боёв останавливается после ошибки.** Ошибка `/battleResult`
   (`CampaignBattleGround.ts:246-248`) или ошибка `/battle` (`HomeScreen.ts:1236-1242`) не запускают
   повтор: поле боя остаётся пустым до перезахода. ГДД: [#gdd-open](game-design/campaign-gdd.md#gdd-open).
3. **Результат на экране может расходиться с сервером.** `win` считается локально
   (`CampaignBattleGround.ts:240`), и плашка победы (`HomeScreen.onCampaignBattleEnded`) показывается по нему.
   Сервер пересимулирует бой и может засчитать поражение: игрок видит «победу» без продвижения.
   Сверка (`BattleAnalyzer`) есть только в dev-режиме. ГДД: [#gdd-open](game-design/campaign-gdd.md#gdd-open).
4. **`startNextBattle` — пустая обёртка.** После удаления ожидания туториала метод только вызывает
   `battleRequest()` (`HomeScreen.ts:1245-1247`): два имени для одного правила ГДД
   ([#gdd-level-transition](game-design/campaign-gdd.md#gdd-level-transition)). Кандидат на оставление
   одной функции; переименование не делалось. Прежний `setTimeout`-повтор исчез, но вместе с ним
   исчезло и ожидание туториала: проверить с `tutorial-architecture.md`, держит ли туториал бой иначе.
5. **Удержание и снятие в разных классах.** Тег `HomeScreen::campaignChapterComplete::…` ставит
   `CampaignBattleGround`, снимает `HomeScreen`, и корректность зависит от того, какую ветку
   выберет первый (см. п.1). Предложение: метод-переход у одного владельца, который сам удерживает
   и сам снимает (`agent-system-workflow.md#no-implicit-order`). ГДД, отложено 2026-10-15.
6. **Заготовка наград региона и уровня.** `CampaignPopup.animationReward` (`CampaignPopup.ts:345-392`)
   не вызывается, список наград в нём всегда пуст, а спрайт `atlas/campaign_screen/boss/0.png` в
   атласе отсутствует; поле `regionRewards` и `config.rewards` (`CampaignPopup.ts:41`, `:54`) не
   читаются. `CampaignLevelRewardsPopup` целиком не открывается (кнопка закомментирована,
   `CampaignPopup.ts:116-120`) и не рисует полученные награды. Пустой `CampaignPopupJSON`
   (`campaign.d.ts:1-3`). Это заготовка под будущую линейку наград (по ТЗ она позже расширится), кандидатом на удаление не считать (решение пользователя 2026-10-15). ГДД: окна содержимого и награды за регион нет ([#gdd-map](game-design/campaign-gdd.md#gdd-map), [#gdd-chapter-reward](game-design/campaign-gdd.md#gdd-chapter-reward)).
7. **Одно действие в шести копиях.** «Записать `campaign`, эмитить `CAMPAIGN_UPDATE`, пересоздать
   плашку» повторено в четырёх dev-обработчиках (`HomeScreen.ts:352-400`), в
   `campaignMissionComplete` (`:1052-1056`) и в продолжении `campaignChapterComplete` (`:1030-1034`).
   Предложение: один метод `HomeScreen`, обновляющий состояние кампании
   (`agent-system-workflow.md#gdd-function-mapping`, `#no-implicit-order`).
8. **Временная подмена состояния.** `campaignChapterComplete` пишет `this.data.campaign.mission = 5`
   (`HomeScreen.ts:1014`) в общее состояние, чтобы нарисовать полную шкалу; настоящие данные
   записываются только после карты региона. При этом у `UICampaignProgress` есть неиспользуемый
   параметр `mission` ровно для такого случая.
9. **Константы сервера продублированы на клиенте.** 50 миссий в регионе (`CampaignPopup.getLevel`,
   `CampaignPopup.ts:73`), 10 локаций на карте (`:27`), 4 точки шкалы и `mission = 5` для полной
   главы (`HomeScreen.ts:330-338`, `:1014`). Смена баланса на сервере сломает карту и шкалу.
10. **Разные числа уровня в разных местах.** Главный экран показывает `level + 1`
    (`HomeScreen.ts:327`), профиль — `campaignLevel` без прибавки (`ProfileSection.ts:155`). Так и
    задумано: [#gdd-progress-hud](game-design/campaign-gdd.md#gdd-progress-hud).
11. **Блокировка экрана при прерванной анимации карты (не проверено запуском).** Анимированная карта
    ставит `setBlockInteractive(true)` (`CampaignPopup.ts:60`) и снимает её только в конце
    `animationNextRegion` (`:336`). Цепочка идёт на `Tweens.delay(this.layout, …)`; если окно закроют
    раньше (например, `flashOverlay.clear()` из нижнего меню), снятие блокировки может не наступить.
    Последний шаг висит на `Tweens.delay(this, …)` (`:335`) — привязан к объекту окна, а не к слою. ГДД: [#gdd-map](game-design/campaign-gdd.md#gdd-map). ГДД, отложено 2026-10-15.
12. **Мелочи.** Имя слоя окна `"ShopPopup"` (`CampaignPopup.ts:47`) скопировано из магазина;
    `(region % 10) ?? 0` (`:52`) — `??` ни на что не влияет; пустая ветка `if (isBackgroundMode())`
    (`CampaignBattleGround.ts:120-122`); в `Header.ts:150` упоминается несуществующий экран
    `"CampaignScreen"`. Пустой `onBattleEvent` удалён merge'ем.
13. **«Ур. 10001» на последнем уровне.** Сервер хранит пройденные уровни от 0 до 10000, главный экран
    показывает `level + 1` (`HomeScreen.ts:327`), и на последнем уровне выходит «Ур. 10001». ГДД:
    [#gdd-levels](game-design/campaign-gdd.md#gdd-levels). ГДД, отложено 2026-10-15.
14. **Доступ по уровню кампании проверяет только клиент.** Пороги `Vars.AerodromeAccessCampaignLevel`
    и `Vars.AutoSummonAccessLevel` сравниваются на клиенте; сервер уровень не проверяет (стык с
    поездом и аэродромом). Порог аэродрома теперь не используется ни одним подключённым классом. ГДД: [#gdd-levels](game-design/campaign-gdd.md#gdd-levels). ГДД, отложено 2026-10-15.
15. **Туториал в ответах боя (не проверено с сервером).** Клиент перестал читать `tutorial` из
    `/battle` и `/battleResult` (`CampaignBattleGround.ts:243-245`, `HomeScreen.ts:1236`); если сервер
    его ещё присылает, шаг туториала после боя не обновится из этих ответов. Обновление шага идёт
    через `Globals.account.setTutorial` в других запросах (`HomeScreen.ts:762`). Подтверждение у
    `client-analyst-tutorial` и серверной стороны.
16. **Состояние кода после merge.** `HomeScreenAerodrome.ts`, `battlefield.d.ts` и `GameEvents`
    ссылаются на удалённые классы и типы аэродрома: ошибки `tsc` от автора ветки fix, не чинились.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [campaign-gdd.md](game-design/campaign-gdd.md).

| Раздел / класс документа | Якорь ГДД |
|---|---|
| `onTankDestroyedEvent`, `onAirplaneDestroyedEvent` | [#gdd-kill-reward](game-design/campaign-gdd.md#gdd-kill-reward) |
| `onBattleResultEvent`, [#lifecycle](#lifecycle) | [#gdd-levels](game-design/campaign-gdd.md#gdd-levels), [#gdd-defeat](game-design/campaign-gdd.md#gdd-defeat), [#gdd-level-transition](game-design/campaign-gdd.md#gdd-level-transition) |
| `onBattleBegin`, `onBattleEnded` | [#gdd-level-transition](game-design/campaign-gdd.md#gdd-level-transition) |
| `UICampaignProgress` | [#gdd-progress-hud](game-design/campaign-gdd.md#gdd-progress-hud) |
| `campaignMissionComplete` | [#gdd-levels](game-design/campaign-gdd.md#gdd-levels) |
| `campaignChapterComplete` | [#gdd-chapter-reward](game-design/campaign-gdd.md#gdd-chapter-reward), [#gdd-map](game-design/campaign-gdd.md#gdd-map) |
| `CampaignPopup` | [#gdd-map](game-design/campaign-gdd.md#gdd-map), [#gdd-terms](game-design/campaign-gdd.md#gdd-terms) |
| `CampaignLevelRewardsPopup` | [#gdd-map](game-design/campaign-gdd.md#gdd-map) |
| [#consumers](#consumers) | [#gdd-levels](game-design/campaign-gdd.md#gdd-levels), `ProfileSection` — [#gdd-progress-hud](game-design/campaign-gdd.md#gdd-progress-hud) |
| [#ranked-link](#ranked-link), `CampaignBattleEndedData`, `RankedProfile` | в ГДД кампании не описано (см. вопросы) |
| [#tradeoffs](#tradeoffs) п.2, п.3 | [#gdd-open](game-design/campaign-gdd.md#gdd-open) |

<a id="file-map"></a>
## 10. Карта файлов

### Файлы прямого влияния

- `src/views/home_screen/campaign/CampaignBattleGround.ts` — поле боя кампании: награды, результат,
  переизлучение событий боя.
- `src/views/home_screen/popups/campaign/CampaignPopup.ts` — карта регионов и анимация смены региона.
- `src/views/home_screen/popups/campaign/CampaignLevelRewardsPopup.ts` — окно наград уровня (не
  используется).
- `src/views/home_screen/campaign/CampaignBattleEndedData.ts` — данные события `CAMPAIGN_BATTLE_ENDED`.
- `src/views/home_screen/campaign/RankedProfile.ts` — плашка противника в рейтинговом бою (только
  упоминание, [#ranked-link](#ranked-link)).
- `src/views/home_screen/popups/campaign/CampaignRankedHistory.ts` — окно истории рейтинговых боёв
  (только упоминание).
- `src/views/home_screen/popups/campaign/campaign.d.ts` — `CampaignLevelRewardsJSON`, `CampaignPopupJSON`,
  `CampaignRankedHistoryJSON`, `CampaignRankedHistoryEntryJSON`.
- `assets-src/atlas/campaign_screen/` — атлас карты (пакет `CampaignScreen`).
- `assets-src/atlas/home_screen/campaign/` — точки и полосы шкалы прогресса (в пакете `HomeScreen`).

### Файлы косвенного влияния

- `src/views/home_screen/HomeScreen.ts` — владелец состояния кампании: плашка прогресса, dev-кнопки,
  завершение миссии/главы, запуск боя, плашка результата.
- `src/views/home_screen/home.d.ts` — `CampaignJSON`, поле `campaign` в `HomeScreenJSON`.
- `src/views/home_screen/campaign/AirDrop.ts` — airDrop на поле боя кампании
  ([airdrop-architecture.md](airdrop-architecture.md)).
- `src/plain/GameEvents.ts` — события `CAMPAIGN_UPDATE`, `CAMPAIGN_BATTLE_ENDED`, `BATTLE_*`.
- `src/types/battle.d.ts` — `RankedResultJSON` (ответ `/battleResult`).
- `src/views/battle/ground/BattleGround.ts` — зависимость: базовое поле боя, фоновый режим.
- `src/views/home_screen/HomeScreenMilitaryBase.ts` — подписка на события боя (новая область merge).
- `src/views/home_screen/HomeScreenAerodrome.ts` — старая плашка аэродрома, из `HomeScreen` не
  подключена; доступ по уровню и подписки на `CAMPAIGN_UPDATE`/события боя.
- `src/views/battle/air/BattleAir.ts`, `src/views/battle/BattleAirstrike.ts` — подписка на события
  боя.
- `src/plain/Vars.ts` — `AerodromeAccessCampaignLevel`.
- `src/views/home_screen/popups/train/TrainAutoSummonPopup.ts` — доступ к автопризыву по
  `campaignLevel` (`TrainAutoSummonJSON` в `home.d.ts`).
- `src/views/home_screen/popups/profile/ProfileSection.ts`, `profile.d.ts` — уровень в профиле.
- `src/plain/quests/QuestEvent.ts`, `src/views/home_screen/HomeScreenQuest.ts` — квест
  `CAMPAIGN_LEVEL_UP`.
- `src/views/home_screen/popups/rating/RatingCampaignSection.ts`, `RatingCampaignRankingSection.ts`,
  `RatingPopup.ts` — вкладки рейтинга по кампании; вторая открывает `CampaignRankedHistory`.
- `src/plain/user/UserBag.ts` — зависимость: удержание ресурсов наград.
- `src/shared/animations/FlyIconsAnimation.ts`, `src/plain/RewardUtils.ts` — зависимость: полёт
  иконок и разбор наград.
- `src/battle/BattleAnalyzer.ts` — зависимость: dev-сверка симуляции.
- `src/shared/footer/Footer.ts` — закрытие карты через `flashOverlay.clear()`.
- `assets-src/raw/lang/ru/ru.json` — ключи `homeScreen.campaign.level`, `campaignScreen.*`,
  `homeScreen.campaign.rTitle/place/rating`, `homeScreen.ranked.*`, `profileScreen.campaign`.
- `tools/src/config.yaml` — пакет `CampaignScreen`.
