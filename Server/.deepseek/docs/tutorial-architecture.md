# Туториал — `TutorialUserComponent` (сервер)

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду (код в рамках
> задачи не менялся), 2026-09-28; актуализирован после merge origin/amnesia/fix (2026-10-19). Всё ниже подтверждено чтением кода, запуском не проверялось;
> клиентская сторона (как клиент показывает шаги туториала) не проверялась.

ГДД: отсутствует (создание отложено по решению пользователя 2026-10-13).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
   - [Сценарий по шагам](#flow)
   - [Что меняется в игре, пока туториал включён](#effects)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`TutorialUserComponent`](#cls-tutorialusercomponent)
   - [`TutorialData`](#cls-tutorialdata)
   - [Точки использования](#consumers)
   - [Миграция версии игры и `skip_tutorial`](#migration)
   - [Персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
   - [Открытые вопросы](#open)
9. [Карта файлов компонента](#file-map)
   - [Файлы прямого влияния](#files-direct)
   - [Файлы косвенного влияния](#files-indirect)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Туториал сведён к двум шагам: игрок принимает два танка через `/ingame/train/accept`. Состояние — одно
целое `progress` у игрока:

- `0` — ожидание первого принятия танка (`FIRST_TRAIN`);
- `1` — ожидание второго принятия (`SECOND_TRAIN`);
- `-1` — туториал пройден/пропущен (`isEnabled() == false`).

Новый игрок начинает с `0` (поле отсутствует в БД → значение по умолчанию). Игроки с `gv < 1`
получают `-1` при входе ([`UserGameVersion`](#migration)); ранее существовавшим выставлено `-1` также
миграцией [`skip_tutorial`](#migration).

Компонент пассивен: хранит шаг и умеет только «сдвинуть шаг, если он равен ожидаемому»
([`increase`](#m-increase)) и «выключить» ([`skip`](#m-skip)). Единственный потребитель переходов —
`TrainPage /accept` ([точки использования](#consumers)).

<a id="flow"></a>
### Сценарий по шагам

| `progress` | Ожидание | Кто сдвигает | Результат |
|------------|----------|--------------|-----------|
| 0 | принять первый танк | `TrainPage /accept` | `→ 1` |
| 1 | принять второй танк | `TrainPage /accept` | `→ -1` |

<a id="effects"></a>
### Что меняется в игре, пока туториал включён

Серверных эффектов нет: `isEnabled()` используется только для ключа `tutorial` в `apiResponseFull()`.
Фиксированные танки поезда, туториальная команда бота, принудительная победа в бою, туториальные квесты
и награды удалены.

<a id="references"></a>
## 2. Референсы

Внешних референсов нет. Смежные документы (ссылаться, не дублировать):

- [train-architecture.md](train-architecture.md) — `TrainPage /accept`.
- [quests-architecture.md](quests-architecture.md) — раньше туториальные квесты; описание там может быть
  устаревшим (см. [#open](#open)).

<a id="patterns"></a>
## 3. Паттерны

- **`UserChildComponent`** с ленивым созданием в `User` и точечной персистентностью через
  `changedField` (поддокумент `Tutorial` документа `User`, без `dbToData`).
- **Конечный автомат на int** с защитой от «перепрыгивания»: `increase(step)` срабатывает, только
  если текущий шаг равен ожидаемому; цепочка `increase(A) || increase(B)` в `TrainPage` сработает не
  более одного раза за счёт короткого замыкания.
- **Миграция версии игры**: `UserGameVersion` по полю `gv` у `User` выполняет одноразовые преобразования
  при входе.

<a id="class-list"></a>
## 4. Список классов

Пакет туториала (`game/src/main/java/com/linkedgames/game/model/tutorial/`):

- `TutorialUserComponent` — состояние и переходы.
- `data/TutorialData` — константы шагов.

Потребители: `model/user/User`, `model/user/UserGameVersion`, `model/user/UserActor`,
`pages/ws/ingame/TrainPage`. Миграция —
`game/src/main/resources/migrations/1757495348631_skip_tutorial.json`.

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#flow`, `#effects`, `#references`, `#patterns`, `#class-list`, `#class-nav`,
`#cls-tutorialusercomponent` (`#m-isenabled`, `#m-increase`, `#m-skip`, `#m-dbmappingbuild`,
`#m-apiresponse`), `#cls-tutorialdata`, `#consumers`, `#migration`, `#persistence`, `#client-contract`,
`#tradeoffs`, `#open`, `#file-map` (`#files-direct`, `#files-indirect`).

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|-------|--------|
| `TutorialUserComponent` (+ `DBFields`) | [#cls-tutorialusercomponent](#cls-tutorialusercomponent) |
| `TutorialData` | [#cls-tutorialdata](#cls-tutorialdata) |
| `User`, `UserGameVersion`, `TrainPage` | [#consumers](#consumers), [#migration](#migration) |

## 7. Классы и методы

<a id="cls-tutorialusercomponent"></a>
### `TutorialUserComponent`

`extends UserChildComponent implements APIResponseStd`, имя компонента `"Tutorial"`. Одно поле
`int progress`.

<a id="m-isenabled"></a>
- **`isEnabled()`** — `progress != -1`.

<a id="m-increase"></a>
- **`increase(int step)`** — если `progress != step`, возвращает `false` и ничего не делает. Иначе
  `progress++`; если стало больше `TutorialData.MAX` (1) — `progress = -1` (туториал завершён).
  Сохраняет `changedField("pg", progress)`, возвращает `true`. При выключенном туториале никогда не
  срабатывает (шаги ≥ 0).

<a id="m-skip"></a>
- **`skip()`** — `progress = -1`, `changedField("pg", progress)`. Единственный вызов — из
  `UserGameVersion` ([#migration](#migration)).

<a id="m-dbmappingbuild"></a>
- **`dbMappingBuild(Document)`** — `progress = document.getInteger("pg", 0)`.

<a id="m-apiresponse"></a>
- **`apiResponse()`** — `{ "progress": <int> }` (сырое значение, в т.ч. `-1`).

Тривиальное: конструктор `(User, String)`; `modifyReceiver` — пустой; `DBFields.PROGRESS_FIELD = "pg"`.

<a id="cls-tutorialdata"></a>
### `TutorialData`

Три статические константы: `MAX = 1` (последний шаг), `FIRST_TRAIN = 0`, `SECOND_TRAIN = 1`
(значения `progress`, при которых `/accept` двигает шаг). `TutorialSteps` и все балансовые массивы
(танки поезда/противника, `ENEMY_COUNT`, `TUTORIAL_QUESTS`, `LAST_QUEST_*`) удалены.

<a id="consumers"></a>
### Точки использования

- **`User`** — поле `tutorial`, ленивый `getTutorialUserComponent()` (имя `"Tutorial"`);
  `dbMappingBuild` вызывается, только если в документе есть `Tutorial` (`DBFields.P_TUTORIAL_FIELD`);
  `modifyReceiver` проброшен; в `apiResponseFull()` — ключ `tutorial`, только если туториал включён.
  `UserGameVersion.execute` вызывается при входе, если `gv` не равен текущей версии.
- **`TrainPage` (`/ingame/train/accept`)** — после принятия танка `increase(FIRST_TRAIN) ||
  increase(SECOND_TRAIN)`; при срабатывании — `tutorial` в ответе. `/summon` и `/refuse` туториал не
  трогают.
- Туториальных веток в `TrainUserComponent`, `QuestsUserComponent`, `HomePage`, `CampaignPage`,
  `BattleDataFactory` больше нет (подтверждено `grep`).

<a id="migration"></a>
### Миграция версии игры и `skip_tutorial`

- `UserGameVersion.execute(User)` (вызывается из `User` при входе, если `gv != CURRENT_GAME_VERSION = 1`):
  для `gv < 1` вызывает `TutorialUserComponent.skip()` и затем `changeGameVersion(1)`. Новый игрок
  создаётся в `UserActor` с `gv = 1`, поэтому туториал у него остаётся включённым (`progress = 0`).
- `game/src/main/resources/migrations/1757495348631_skip_tutorial.json` — `updateMany` по `users` с
  пустым фильтром: `$set: {"Tutorial.pg": -1}`. Одноразово выключил туториал существующим игрокам.

<a id="persistence"></a>
### Персистентность

Поддокумент `Tutorial` документа `User`, одно поле `pg` (int). Пишется в `increase` и `skip` через
`changedField`; `dbToData` нет. До первого перехода поле в БД отсутствует и читается как `0`.

<a id="client-contract"></a>
### Контракт с клиентом

Объект `tutorial = { progress: <int> }`. Клиенту уходит:

| Где | Когда |
|-----|-------|
| `account.tutorial` (`User.apiResponseFull()`) | туториал включён |
| `/ingame/train/accept` → `payload.tutorial` | шаг сдвинулся в этом запросе (включая `progress: -1`) |

Выключенный туториал выражается **отсутствием** ключа `tutorial` в `account`; явное `progress: -1`
приходит только в ответе `/accept` в момент завершения. Входящих параметров туториала от клиента нет.
Как клиент обрабатывает эти данные — не проверялось.

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и подозрительные места

Всё — по чтению кода, запуском не проверялось.

1. **Переход шагов опирается на короткое замыкание `||`.** В `/accept` `increase(FIRST_TRAIN) ||
   increase(SECOND_TRAIN)`: если выполнить оба вызова подряд, один запрос провёл бы `0 → 1 → -1`.
   Порядок и `||` в `TrainPage` — единственная защита.
2. **Шаг продвигает любое принятие танка**, а не конкретный танк: туториал = «принять два танка подряд
   в `/accept`» (первое принятие `0 → 1`, второе `1 → -1`). `/refuse` шаг не двигает.
3. **Имена `FIRST_TRAIN` / `SECOND_TRAIN`** описывают шаг как «призыв поезда», а двигает его `/accept`
   (принятие танка), не `/summon`. Возможно, имена не соответствуют смыслу — вопрос про переименование
   см. [#open](#open).
4. **`UserGameVersion` для игроков до версии 1 всегда вызывает `skip()`**, независимо от текущего шага
   (`progress` в БД, в т.ч. `0..1`, обнуляется в `-1`). Миграция `skip_tutorial.json` стала избыточной
   для существовавших игроков: версия 0 (поле `gv` отсутствует) всё равно будет пропущена при входе.
5. **`UserGameVersion.execute` вызывается при каждом входе пока `gv != CURRENT`**, `changeGameVersion`
   пишет `gv` один раз; повторного `skip()` не будет.
6. **Неоднородный контракт «выключен»**: отсутствие ключа `tutorial` в ответе vs. `progress: -1` (см.
   [#client-contract](#client-contract)).
7. **Мёртвый код:** пустой `modifyReceiver`. Клиентская часть (21 шаг, привязка к квестам) могла остаться
   на старом контракте — не проверялась ([#open](#open)).

<a id="open"></a>
### Открытые вопросы

- Серверные туториальные ветки в квестах, бою и поезде (фиксированные танки, команда бота, победа без
  эмуляции, туториальные квесты, шаги до 20) удалены; ГДД туториала нет. Нужна ли какая-то из этих
  механик в новом сценарии, не определено.
- Клиентский контракт (`tutorial.progress` в диапазоне 0..20, `account.tutorial`, ответы `/summon`,
  `/completeQuest`, `/battle`) теперь сужен до значений `0, 1, -1` и ответа `/accept` — сверить с
  `/workspace/client/.claude/docs/tutorial-architecture.md` (`client-analyst-tutorial`, `integration-lead`).
- `quests-architecture.md#tutorial` и `#cls-tutorialdata` описывают удалённые ветки — зона
  `server-analyst-quests`.

<a id="file-map"></a>
## 9. Карта файлов компонента

Пути от корня репозитория `server`. Полнота проверена `grep` по `TutorialUserComponent`, `TutorialData`,
`getTutorialUserComponent`, `P_TUTORIAL_FIELD`, `UserGameVersion`. Туториал военной базы
(`MilitaryBaseUserComponent.tutorialProgress`, `MilitaryBasePage`) — отдельный механизм, в карту не входит.

<a id="files-direct"></a>
### Файлы прямого влияния

- `game/src/main/java/com/linkedgames/game/model/tutorial/TutorialUserComponent.java` — состояние шага, `increase`, `skip`, персистентность, ответ клиенту.
- `game/src/main/java/com/linkedgames/game/model/tutorial/data/TutorialData.java` — константы шагов (`MAX`, `FIRST_TRAIN`, `SECOND_TRAIN`).
- `game/src/main/java/com/linkedgames/game/model/user/UserGameVersion.java` — миграция версии игры 0 → 1: `skip()` туториала.
- `game/src/main/resources/migrations/1757495348631_skip_tutorial.json` — историческая одноразовая миграция: выключение туториала существующим игрокам.

<a id="files-indirect"></a>
### Файлы косвенного влияния

- `game/src/main/java/com/linkedgames/game/model/user/User.java` — владелец компонента, загрузка из БД, ключ `tutorial` в полном ответе, вызов `UserGameVersion.execute`, поле `gv`.
- `game/src/main/java/com/linkedgames/game/model/user/UserActor.java` — новый игрок создаётся с `gv = CURRENT_GAME_VERSION` (миграция пропуска его не касается).
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/TrainPage.java` — переходы шагов в `/accept`.

Итого: 4 файла прямого и 3 косвенного влияния.
