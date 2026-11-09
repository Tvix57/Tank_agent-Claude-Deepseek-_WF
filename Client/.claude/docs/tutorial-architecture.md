# Туториал — обучение первых минут игры (клиент)

**Статус: остатки** — документ сохранён по решению пользователя 2026-10-19; описывает остатки туториала в коде после merge `origin/amnesia/fix`.

> **auto-create** — документ составлен по существующему коду, актуализирован 2026-10-19 после merge
> `origin/amnesia/fix` (туториал в коде сведён к остаткам, см. [#purpose](#purpose)). Запуском не
> проверялось.
> Серверная сторона: `/workspace/server/.claude/docs/tutorial-architecture.md` (тоже auto-create).

ГДД: отсутствует (создание отложено по решению пользователя 2026-10-13).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
   - [Обработка шагов](#steps)
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

После merge `origin/amnesia/fix` клиентский туториал вырезан почти целиком: удалены типы конфига
(`src/types/tutorial.d.ts`), событие `GameEvents.TUTORIAL_EVENT`, чтение `tutorial` из push
`/events/quest/update`, конфиг шагов `TutorialUtils.DATA`, подмена спрайтов, параметров и фонов танков,
пауза боёв, туториальные фоны и спрайты танков. Остался указатель на два шага и блокировки.

Клиент хранит последний полученный шаг в `Globals.account.tutorial.progress` (`-1` — туториал
выключен). Что делает:

- **Указатель.** Затемняет экран, оставляя «окно» над нужной кнопкой, рисует круг, палец и эффект
  нажатия ([`Tutorial`](#cls-tutorial)). Клики вне окна блокируются.
- **Блокировки.** Пока шаг не `-1`: не открываются окно аэродрома с главной плашки, вкладки футера
  «battlefield», клана и магазина, окно наград за отсутствие (`IdlePopup`) и окно покупки схем при ошибке
  призыва (`TrainBuySchemesPopup`).

Клиент больше не паузит бои по шагу, не подменяет вид и параметры танков и не меняет фон по шагу: бой
кампании запрашивается всегда (`HomeScreen.startNextBattle` → `battleRequest`), параметры берутся из
данных боя как есть. Сценарий шагов (серверный enum `TutorialSteps`, 0..20) — на сервере
(`/workspace/server/.claude/docs/tutorial-architecture.md#flow`); совпадение сервера с урезанным
клиентом не проверялось ([вопросы](#tradeoffs), п.1).

<a id="steps"></a>
### Обработка шагов

Клиент различает только `-1` и шаги 0 и 1. Константы — `TutorialUtils.FIRST_TRAIN = 0`,
`TutorialUtils.SECOND_TRAIN = 1`; обе ветки в коде делают одно и то же.

| Шаг | Что делает клиент |
|---|---|
| 0, 1 | `HomeScreen.processTutorial` — указатель на кнопку поезда (`content.footer.train`, 200×65); клик → `Tutorial.hide()`. `TankGetPopup.processTutorial` и `AirplaneGetPopup.processTutorial` — указатель на «принять» после анимации окна (145×55) |
| любой другой, кроме -1 | `disable()` в `HomeScreen.processTutorial` и в окнах; блокировки из [#purpose](#purpose) действуют |
| -1 | `disable()`, обычный режим |

Как шаг попадает в клиент и кто после этого перерисовывает указатель — [контракт](#client-contract).

<a id="references"></a>
## 2. Референсы

- Серверный сценарий, эффекты на поезд, бой и квесты, контракт —
  `/workspace/server/.claude/docs/tutorial-architecture.md` (`#flow`, `#effects`, `#client-contract`,
  `#tradeoffs`). Туториальные квесты и их награды —
  `/workspace/server/.claude/docs/quests-architecture.md#tutorial`.
- Дроп предмета коллекции вместо танка на `/train/summon` и окно `TrainCollectionItemPopup` —
  `collections-architecture.md`.
- Окно получения самолёта `AirplaneGetPopup` — `aerodrome-architecture.md` (после merge плашка
  аэродрома ссылается на удалённое окно, там же).

<a id="patterns"></a>
## 3. Паттерны

- **Оверлей сцены.** Один экземпляр `Tutorial` на `InGameScene`, слой с `zIndex =
  zidxBlockInteractive - 1` (999) — выше всех окон `FlashOverlay`, хедера и футера. Смена экрана
  (`Scene.EVENT_SCREEN_CHANGED`) выключает оверлей. Экраны и окна получают его через
  `HomeScreen.getTutorial()`.
- **Конечный автомат по шагу без своего состояния.** Каждое место с указателем держит свой
  `processTutorial()` со `switch` по `Globals.account.tutorial.progress`; общего диспетчера нет
  ([#tradeoffs](#tradeoffs), п.4).
- **Перерисовка по смене окон.** `HomeScreen` вызывает `processTutorial` на `onStart` и на
  `FlashOverlay.EVENT_ON_CHANGED`; при открытых окнах он ничего не меняет, указатель окна ставит само
  окно после анимации появления.
- **Событие смены шага.** `User` рассылает `App.events` событие `g/account/tutorial/update`
  (`onTutorialChange`/`offTutorialChange`) при смене `progress` в `build` и при `setTutorial`. Подписан
  только `Footer`.

<a id="class-list"></a>
## 4. Список классов

- `src/views/tutorial/Tutorial.ts` — `Tutorial` (оверлей-указатель) + интерфейс
  `TutorialShowConfig { width?, height?, offsetX?, offsetY? }`.
- `src/plain/TutorialUtils.ts` — `TutorialUtils` (две константы шага, [#cls-tutorialutils](#cls-tutorialutils)).
- `src/types/interfaces.d.ts` — `TutorialJSON { progress }`, поле `UserFullJSON.tutorial`.

Точки встраивания в чужих классах — [#integration](#integration).

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#steps`, `#references`, `#patterns`, `#class-list`, `#class-nav`, `#classes`,
`#cls-tutorial` (`#m-show`, `#m-hide`, `#m-disable`), `#cls-tutorialutils`, `#types`, `#integration`,
`#client-contract`, `#tradeoffs`, `#gdd-link`, `#file-map`.

<a id="class-nav"></a>
## 6. Оглавление по классам

[`Tutorial`](#cls-tutorial) · [`TutorialUtils`](#cls-tutorialutils) · [Типы](#types) ·
[Точки встраивания](#integration) · [Контракт с сервером](#client-contract)

<a id="classes"></a>
## 7. Классы и методы

<a id="cls-tutorial"></a>
### `Tutorial` (`implements IViewProvider`)

Оверлей на весь экран: четыре чёрных прямоугольника (`top`/`bottom`/`left`/`right`, alpha 0.3,
`Button.newBlockClicks`) вокруг прозрачного «окна», круг из четырёх `circle_part.png`, пульсирующий
`click_effect.png` и покачивающийся `finger.png`. Создаётся невидимым. Подписан на
`EVENT_AFTER_REFRESH` слоя сцены (отписка по `EVENT_DESTROYED`) и при ресайзе пересчитывает позицию
окна по цели. Файл в merge не менялся.

<a id="m-show"></a>
- **`show(target, config)`** — ставит окно над `target` (центр — мировая позиция контейнера цели +
  смещение, размер — `width`/`height`, по умолчанию 50×50). Затемнение и круг проявляются за 500 мс с
  задержкой 1 с. Если оверлей был невидим — палец и эффект сразу на месте; если уже был виден
  (в том числе после `hide()`), палец доезжает от прежней позиции за 500 мс, эффект появляется по
  приезде. Сначала вызывает `disable()`, поэтому повторный `show` безопасен.
<a id="m-hide"></a>
- **`hide()`** — прячет затемнение, круг, палец и эффект, но оставляет слой видимым: прямоугольники
  с нулевой прозрачностью продолжают блокировать клики вне прежнего окна. Используется на время
  анимации поезда после клика.
<a id="m-disable"></a>
- **`disable()`** — выключает слой целиком, клики снова проходят.

Внутреннее: `calculatePosition`/`setPosition` — геометрия окна; `onResize` — пересчёт, если цель
жива; `clearTweens` — снятие твинов показа. `view()` — слой.

<a id="cls-tutorialutils"></a>
### `TutorialUtils` (статический)

Две константы `FIRST_TRAIN = 0` и `SECOND_TRAIN = 1`; больше в классе ничего нет (прежние `DATA`,
`getStepData`, `findTutorialData`, `getTutorialTankParams`, `awaitTutorial`, enum `TutorialSteps`
удалены). Имена констант не совпадают со смыслом серверных шагов 0 («призыв поезда») и 1 («получение
танка») — [#tradeoffs](#tradeoffs), п.2.

<a id="types"></a>
### Типы

- `TutorialJSON { progress: number }` (`src/types/interfaces.d.ts`) — объект шага с сервера.
  Прежние `TutorialData`, `TutorialStepData`, `TutorialTankData`, `TutorialTankParams` удалены вместе
  с `tutorial.d.ts`.

<a id="integration"></a>
### Точки встраивания

- **`InGameScene.initComposition`** — создаёт `Tutorial` в отдельном слое над окнами, выключает его
  при смене экрана.
- **`User`** — поле `tutorial: TutorialJSON = { progress: -1 }`; `build(account)` копирует ключ
  `tutorial`, только если он есть в ответе (`ObjectUtils.classBuild`), и при смене `progress` эмитит
  `g/account/tutorial/update`; `setTutorial(tutorial)` пишет шаг и эмитит то же событие;
  `onTutorialChange`/`offTutorialChange` — подписка.
- **`HomeScreen`**:
  - `processTutorial()` — указатель на кнопку поезда на шагах 0 и 1, на `-1` и прочих шагах —
    `disable()`; при открытых окнах выходит, ничего не меняя;
  - `startNextBattle()` — вызывает `battleRequest()` без проверки шага;
  - `OnTrainAccept()` — пишет `tutorial` из `/train/accept` через `setTutorial` и вызывает
    `processTutorial`; после анимации поезда вызывает `processTutorial` ещё раз;
  - `OnTrainSummon()` — при ошибке в туториале не открывает `TrainBuySchemesPopup`; кнопка поезда
    вызывает `Tutorial.hide()`;
  - `campaignMissionComplete`/`campaignChapterComplete` — `processTutorial` после боя;
  - `IdlePopup` открывается только при `-1`.
- **`TankGetPopup`** — `processTutorial` после анимации: указатель на «принять» на шагах 0 и 1.
- **`AirplaneGetPopup`** — то же на шагах 0 и 1 ([#tradeoffs](#tradeoffs), п.3).
- **`HomeScreenAerodrome`** — главная плашка аэродрома открывает окно только при `-1`; после merge файл
  импортирует удалённый `AerodromePopup` (ошибка tsc от автора fix, не исправлялась).
- **`Footer`** — подписан на `onTutorialChange`; пока шаг не `-1`, кнопки «battlefield», клана и
  магазина неинтерактивны (`updateTutorialInteractive`).

Больше туториала нет в `HomeScreenQuest`, `CampaignBattleGround`, `Fighter`, `Battle`, `BattleGround`,
`BattleGroundTank`, `BattlefieldPopup`, `BattlefieldScreen`, `GameEvents`: проверено
`git grep -niE "tutor"` по `src`.

<a id="client-contract"></a>
### Контракт с сервером

Объект `tutorial = { progress }`, своих роутов и входящих параметров у туториала нет. Сервер —
`/workspace/server/.claude/docs/tutorial-architecture.md#client-contract`. Клиент читает шаг из двух
мест:

| Источник | Клиент | Перерисовка указателя |
|---|---|---|
| `account.tutorial` (`/pblc/gateway` и другие ответы с `account`) | `User.build` | нет; эмитится `g/account/tutorial/update`, подписан только `Footer` |
| `/train/accept` → `payload.tutorial` | `HomeScreen.OnTrainAccept` → `setTutorial` | `processTutorial` |

Не читаются: `payload.tutorial` у `/home/completeQuest`, `/campaign/battle`, `/campaign/battleResult`
и `/train/summon`, push `/events/quest/update`. Отсутствие ключа клиент держит как прежнее значение; при
новом входе `Globals.account` создаётся заново с `-1`.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Наблюдения по коду, запуском не проверялись; баг это или задумано, решает пользователь. Реестр
`undocumented-areas-known-bugs.md` записей о туториале не содержит.

1. **Клиент и серверный сценарий не сверены.** Сервер, судя по его документу, ведёт шаги 0..20,
   выдаёт туториальных врагов и держит `-1` только после шага 20. Клиент реагирует на шаги 0 и 1 и не
   делает ничего на шагах 2..20 (указатель на квест и на финал убран, шаг записывается, но указатель
   гаснет), не получает `tutorial` из `/completeQuest`, `/battle`, `/battleResult` и push. Проверка
   серверного кода после merge не входила в задачу — нужна сверка (`integration-lead`).
2. **Имена констант не отражают смысл.** `SECOND_TRAIN = 1` — по серверному сценарию шаг «получение
   танка», а не «второй поезд»; на нём `HomeScreen` показывает указатель на кнопку поезда, хотя окно
   поезда уже открыто, `TankGetPopup` — на «принять». На шаге 1 одновременно срабатывают обе ветки
   (экран и окно), порядок решает `flashOverlay.count()`.
3. **Указатель в окне самолёта.** `AirplaneGetPopup.processTutorial` показывает указатель на
   «принять» на шагах 0 и 1, хотя сценарий самолётов не содержит; копия из `TankGetPopup`.
4. **Правило «туториал включён» записано девятью сравнениями.** `progress === -1` в пяти файлах
   (`HomeScreen`, `HomeScreenAerodrome`, `TankGetPopup`, `AirplaneGetPopup`, `Footer`). Кандидат на одну
   функцию у `User`. Отображение «шаг → указатель» разнесено по трём `processTutorial` (`HomeScreen`,
   `TankGetPopup`, `AirplaneGetPopup`).
5. **Смена шага — два шага у вызывающего.** `User.build` и `User.setTutorial` эмитят событие, но
   `HomeScreen` на него не подписан и после `setTutorial` вызывает `processTutorial` вручную; указатель
   после `build` не перерисовывается вообще (после `/train/summon` ставит указатель `TankGetPopup`).
   Кандидат на подписку `HomeScreen` на `onTutorialChange`
   (`agent-system-workflow.md#no-implicit-order`).
6. **Окно, открытое поверх указателя, не кликается.** Слой туториала (z 999) выше `FlashOverlay`.
   Если окно, не знающее о туториале, открывается, пока оверлей показан или в режиме `hide()`, его
   кнопки вне «окна» указателя закрыты блокирующими прямоугольниками, а `processTutorial` при открытых
   окнах ничего не меняет. Пример: на шаге 0 выпал предмет коллекции (серверный `#tradeoffs`, п.5) —
   после клика по поезду оверлей в режиме `hide()`, открывается `TrainCollectionItemPopup`, шаг не
   сдвинулся. Возможна блокировка игрока.
7. **Остатки паковки.** Записи `TutorialBackground1..5` и `TTank_*` удалены из `tools/src/config.yaml`
   (2026-10-20, ронял `AssetPacker.sh`); в `assets-src/atlas/tanks/tutorial/` остались только `.DS_Store`.

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: отсутствует (создание отложено по решению пользователя 2026-10-13). Правила для будущей связи:

- когда и на что показывается указатель — [`processTutorial`](#integration) в трёх классах;
- что недоступно игроку во время туториала — блокировки в [#integration](#integration).

Сценарий шагов, выдача танков и врагов, награды квестов — серверные правила
(`/workspace/server/.claude/docs/tutorial-architecture.md#flow`, `#effects`).

<a id="file-map"></a>
## 10. Карта файлов компонента

Полнота проверена `git grep -niE "tutor" -- src tools` и по `assets-src`. Движок `src/ee/`, `Const`,
`Globals` не перечислены (в `Globals.ts` упоминаний туториала нет). Не входят: `src/scenes/LoadingScene.ts` и
`src/types/jloader.d.ts` — параметр `isTutorial` внешнего загрузчика, к компоненту не относится.

### Файлы прямого влияния

- `src/views/tutorial/Tutorial.ts` — оверлей-указатель, `show`/`hide`/`disable`.
- `src/plain/TutorialUtils.ts` — две константы шага.
- `assets-src/atlas/ui/finger.png`, `click_effect.png`, `circle_part.png` — спрайты указателя (в общем атласе `UI`).

### Файлы косвенного влияния

- `src/scenes/InGameScene.ts` — создание `Tutorial`, слой над окнами, выключение при смене экрана.
- `src/plain/user/User.ts` — поле `tutorial`, `setTutorial`, событие `g/account/tutorial/update`.
- `src/types/interfaces.d.ts` — `TutorialJSON`, `UserFullJSON.tutorial`.
- `src/views/home_screen/HomeScreen.ts` — `processTutorial`, `getTutorial`, чтение `tutorial` из `/train/accept`, блокировки `IdlePopup`/`TrainBuySchemesPopup`.
- `src/views/home_screen/popups/tank/TankGetPopup.ts` — указатель на «принять».
- `src/views/home_screen/popups/airplane/AirplaneGetPopup.ts` — указатель на «принять».
- `src/views/home_screen/HomeScreenAerodrome.ts` — блокировка главной плашки аэродрома.
- `src/shared/footer/Footer.ts` — блокировка вкладок «battlefield», клана и магазина.
- `tools/src/config.yaml` — записи `TutorialBackground1..5` (файлы удалены, [#tradeoffs](#tradeoffs), п.7).
