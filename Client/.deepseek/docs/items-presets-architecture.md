# Документация утилиты "ItemsPresets" (стандартная отрисовка предметов-наследников BagItem)

Составлено по прямому запросу пользователя (не auto-create): "Напиши документацию на ItemPresets
клиента" (2026-09-25). Класс лежит в `src/presets/ItemsPresets.ts`.
Сверено с кодом после merge `origin/amnesia/fix` 2026-10-19.

Объём сокращён по тому же принципу, что и у соседних компонентов: вёрстка (точные координаты,
`Layout.Align`, отступы) не расписывается построчно — фиксируется, что метод отрисовывает и кто его
вызывает. Класс не принадлежит одной области (используется квестами, idle-наградами, наградами боя,
профилем/кодексом, коллекциями) — своей подпапки в `src/views/...` и своего domain `*.d.ts` у него нет,
поэтому постоянный агент-аналитик под эту область не создавался (решение `client-analyst-lead`,
организационный вопрос, не требует подтверждения пользователем).

**Разделы:** [1. Описание](#s1) · [2. Референсы](#s2) · [3. Паттерны](#s3) ·
[4. Список классов](#s4) · [6. Оглавление по классам](#s6) · [7. Классы и методы](#s7) ·
[8. Компромиссы и открытые решения](#s8) · [9. Call sites](#s9) ·
[10. Карта файлов](#s10)

## 1. Краткое описание: назначение и бизнес-логика {#s1}

`ItemsPresets` — статический класс-набор пресетов для стандартной отрисовки предметов-наследников
`BagItem` (`ItemJSON`/`BagItemJSON` и их наследники: `ResourceJSON`, `TankJSON`, `AirplaneJSON`;
`CollectionItemJSON` наследует `ItemJSON`, без `uid`). Единая точка входа для любого экрана, которому нужно нарисовать иконку или
карточку предмета, не дублируя логику выбора картинки по типу/id предмета в каждом вызывающем месте.

Два независимых сценария использования:
- **Маленькая иконка предмета** (`createImageLayout` → диспетчер по `itemType`) — используется там, где
  предмет показывается как одна из наград в списке (иконка + количество), например в наградах квеста
  или idle-попапе.
- **Полноценная карточка техники** (`createTankLayout`/`createAirplaneLayout`) — используется там, где
  технику нужно показать крупно, с рангом, уровнем и звёздами (профиль, кодекс).

`createRewardsLayout` объединяет первый сценарий в горизонтальный список "иконка + количество" для
массива наград произвольного состава.

## 2. Использованные референсы {#s2}

Нет — документ составлен по существующему коду, без привязки к конкретной фиче/референсу.

## 3. Использованные паттерны {#s3}

- **Диспетчеризация по `itemType` (generic-свитч)** — `createImageLayout` и `createRewardsLayout`
  выбирают приватный метод отрисовки по `ItemType` (`RESOURCE`/`TANK`/`AIRPLANE`/`COLLECTION_ITEM`).
  Это же решение продублировано (не переиспользовано) в обоих методах — общего приватного диспетчера
  между ними нет, `createRewardsLayout` содержит свою копию `switch`. Добавление нового `ItemType`
  требует правки в обоих местах.
- **Пресет-класс без состояния** — все методы `static`, класс не инстанцируется, поведение полностью
  определяется входными данными (`ItemJSON` и наследники).
- **Фолбэк на пустой `Layout`** — необработанный `itemType`/`id`, а также ещё не реализованные ветки
  (см. раздел 8) не бросают ошибку, а молча возвращают пустой `Layout({width: 25, height: 25})`.

## 4. Полный список классов {#s4}

- `src/presets/ItemsPresets.ts` — `class ItemsPresets` (default export, единственный класс файла).

## 5. Ссылки для навигации {#s5}

См. якоря в оглавлении разделов выше и в п.6 ниже (`#cls-itemspresets`, `#collection-item-todo`).

## 6. Оглавление по классам {#s6}

- [ItemsPresets](#cls-itemspresets)

## 7. Классы и методы {#s7}

### ItemsPresets {#cls-itemspresets}

- **`public static createImageLayout(data: ItemJSON): Layout`** — диспетчер маленькой иконки предмета
  по `data.itemType`: `RESOURCE` → `createImageLowResource`, `TANK` → `createImageTank`, `AIRPLANE` →
  `createImageAirplane`, `COLLECTION_ITEM` → `createImageCollectionItem`. Неизвестный `itemType` →
  пустой `Layout(25×25)`.
- **`private static createImageLowResource(data: ResourceJSON): Layout`** — маленькая иконка ресурса
  для обычных списков наград: по `data.id` (`ItemId`) возвращает `Layout` с одной из четырёх иконок
  (золото, серебро, чертёж танка, чертёж самолёта) из `atlas/ui/icons/`, с разными размерами `Layout`
  и масштабом спрайта под каждую иконку. Неизвестный `id` → пустой `Layout(25×25)`.
- **`private static createImageMediumResource(data: ResourceJSON): Layout`** — тот же выбор по
  `data.id`, но золото и серебро берутся из `atlas/ui/header/`; ветки чертежей в коде помечены `// TODO`
  и пока повторяют иконки `createImageLowResource`. Вызывается только из `createRewardsCustomLayout`.
- **`private static createImageTank(data: TankJSON): Layout`** — **не реализован**: возвращает пустой
  `Layout(25×25)` без содержимого, параметр `data` не используется. См. раздел 8.
- **`private static createImageAirplane(data: AirplaneJSON): Layout`** — **не реализован**: аналогично
  `createImageTank`, пустой `Layout(25×25)`, параметр не используется. См. раздел 8.
- **`private static createImageCollectionItem(data: CollectionItemJSON): Layout`** — **не реализован**:
  пустой `Layout(25×25)`, параметр не используется. Это метод, для которого зафиксировано принятое
  архитектурное решение — см. [раздел 8, TODO](#collection-item-todo).
- **`public static createTankLayout(data: TankJSON): Layout`** — полноценная
  карточка танка (64×50): цветной фон по рангу, спрайт танка (загружается асинхронно поштучно через
  `Creator.spriteAsync`, паттерн — `.claude/docs/asset-packaging.md`), рамка, иконка ранга
  (`RankPresets.SmallRankLayout`), текст уровня, звёзды по количеству `data.stars.count`. При заданном
  `data.titleType` сверху добавляется плашка `atlas/tech_info/headers/prototype.png` с переводом
  `tanks.headers.<titleType>`. Поля
  `TankJSON.level`/`stars` необязательные: блок уровня рисуется только при `data.level !== undefined`,
  звёзды — при `data.stars !== undefined` (сервер не присылает их в превью награды, где они ещё не
  определены). Вызывается там, где технику нужно показать крупной карточкой (профиль, кодекс, превью
  награды `CollectionExperimentalTank.UIRewardItem`).
- **`public static createAirplaneLayout(data: AirplaneJSON): Layout`** — то же самое для самолёта,
  структурно идентично `createTankLayout` (свой набор путей к ассетам `atlas/tech_info/airplanes/...`),
  ЗА ИСКЛЮЧЕНИЕМ отсутствия текста уровня и плашки `titleType`: у `createTankLayout` есть блок `levelLayout` с переводом
  `global.levelWD` + значением `data.level`, у `createAirplaneLayout` такого блока нет — только фон,
  спрайт, ранг, рамка и звёзды.
- **`public static createRewardsLayout(data: ItemJSON[]): Layout`** — горизонтальный список наград:
  для каждого элемента массива строит мини-`Layout` "иконка + количество" (иконка — своя копия
  диспетчера по `itemType`, вызывающая те же приватные `createImage*`-методы напрямую, не через
  `createImageLayout`) и добавляет их подряд в общий `resizable`-контейнер. Используется для рендера
  произвольного набора наград (idle-попап, награды боя).
- **`public static createRewardsCustomLayout(data: ItemJSON[]): Layout`** — вариант
  `createRewardsLayout` для превью награды: такой же горизонтальный контейнер, но иконку рисует только
  для `ItemType.RESOURCE` (через `createImageMediumResource`, у остальных типов — только число), а
  количество выводит со знаком «+». В коде помечен `// TODO add params for big count rewards`.
  Вызывается из `CollectionExperimentalTank.UIRewardItem`, когда награда за комплект — не танк.

## 8. Принятые компромиссы и открытые решения {#s8}

- **Диспетчер продублирован дважды** (`createImageLayout` и внутренний `switch` в
  `createRewardsLayout`) — общего приватного метода-диспетчера нет, оба свитча нужно поддерживать
  синхронно при добавлении нового `ItemType`. Наблюдение по коду, не оценка "хорошо/плохо".
- **`createImageTank`/`createImageAirplane` не реализованы** — оба метода существуют (сигнатура на
  месте, вызываются из диспетчеров), но тела пустые (`Layout(25×25)` без содержимого). Это
  предшествующее состояние кода, не связано с решением по коллекционным предметам ниже — отдельно не
  уточнялось у пользователя, документируется как факт кода на 2026-09-25.
- **Коллекционные предметы: принятое решение, ещё не реализовано** {#collection-item-todo} — по
  прямому указанию пользователя (2026-09-25): для `ItemType.COLLECTION_ITEM` в `ItemsPresets` должны
  появиться аналогичные (по образцу `createTankLayout`/`createAirplaneLayout`) публичные функции
  отрисовки, но **сама реализация отрисовки** (создание спрайта, работа с ассетами коллекционных
  предметов) должна располагаться не в `ItemsPresets`, а в новых статических функциях класса
  `CollectionUtils` (`src/utils/CollectionUtils.ts`, см.
  `.claude/docs/collections-architecture.md#cls-collectionutils`) — `ItemsPresets` в этой схеме только
  вызывает готовую функцию `CollectionUtils`, аналогично тому, как `createTankLayout`/
  `createAirplaneLayout` используют `TankUtils.__asset`/`AirplaneUtils.__asset` для построения пути к
  ассету (но здесь в `CollectionUtils` предполагается вынести именно отрисовку, а не только
  вычисление пути).
  Перенос кода сделает пользователь самостоятельно — на момент документирования (2026-09-25) это НЕ
  реализовано: `createImageCollectionItem` — пустая заглушка (см. раздел 7), новых функций в
  `CollectionUtils` под это ещё нет (текущий состав `CollectionUtils` — `__assetGroupTank`, `button`,
  `buttonStatus`, `dollars`, `panelPreset`, ни одна не рисует коллекционный предмет). Ветки
  `case ItemType.COLLECTION_ITEM` в `createImageLayout`/`createRewardsLayout` уже на месте и
  делегируют в `createImageCollectionItem` — при переносе реализации в `CollectionUtils` эти ветки,
  вероятно, не потребуют изменений (менять нужно будет только тело `createImageCollectionItem`).
  Имя(-а) новой публичной функции(-й) `ItemsPresets`/`CollectionUtils` пользователем не зафиксировано.

## 9. Call sites (кто вызывает ItemsPresets на 2026-09-25) {#s9}

Проверено по коду 2026-10-13 (`grep -rn "ItemsPresets\." src`), 14 вызовов в 7 файлах:

- `src/views/home_screen/HomeScreenQuest.ts:137` — `createImageLayout(this.data.reward)`.
- `src/views/home_screen/popups/idle/IdlePopup.ts:118` — `createRewardsLayout(this.data.rewards)`.
- `src/views/home_screen/popups/profile/ProfileSection.ts:187` — `createTankLayout(...)`.
- `src/views/home_screen/popups/profile/ProfileSection.ts:221` — `createAirplaneLayout(...)`.
- `src/views/home_screen/popups/profile/codex/CodexTanksSection.ts:249,255,259` —
  `createTankLayout(...)` (три ветки: собранный/несобранный/др.).
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts:178,184,186`
  — `UIRewardItem`: `createTankLayout(...)` для полученного танка и для награды-танка (сервер не
  присылает уровень и звёзды), `createRewardsCustomLayout([reward])` для награды другого типа.
- `src/views/home_screen/popups/profile/codex/CodexAirplanesSection.ts:251,257,261` —
  `createAirplaneLayout(...)` (аналогично, три ветки).
- `src/views/battlefield_screen/BattlefieldScreen.ts:475` — `createRewardsLayout(rewards)`.

`createImageCollectionItem` напрямую снаружи класса не вызывается — только внутренне через
`createImageLayout`/`createRewardsLayout` при `itemType === ItemType.COLLECTION_ITEM` (сейчас реального
использования в проде фактически нет: `CollectionAlbum`/`CollectionExperimentalTank`/`TrainCollectionItemPopup`
рисуют фото и монеты коллекции своими методами, не через `ItemsPresets` — см. `collections-architecture.md`
#cls-collectionalbum, #cls-collectionexperimentaltank, #cls-traincollectionitempopup-changes).

## 10. Карта файлов компонента {#s10}

Полнота проверена 2026-10-13: `grep -rln "ItemsPresets" src` — 8 файлов, каждый ниже.

**Файлы прямого влияния**

- `src/presets/ItemsPresets.ts` — сам класс-пресет: иконки предметов, карточки танка/самолёта, списки наград.

**Файлы косвенного влияния**

- `src/plain/items/ItemType.ts` — зависимость: enum типа предмета, по нему диспетчеры выбирают метод отрисовки.
- `src/plain/items/ItemId.ts` — зависимость: id ресурсов, по ним выбирается иконка ресурса.
- `src/presets/RankPresets.ts` — зависимость: иконка ранга на карточках техники (`SmallRankLayout`); после merge `amnesia/fix` таблицы ширин расширены до рангов 1–20, иконка 20 px по высоте.
- `src/utils/TankUtils.ts` — зависимость: имя ассета танка для пути спрайта (`__asset`).
- `src/utils/AirplaneUtils.ts` — зависимость: имя ассета самолёта для пути спрайта (`__asset`).
- `src/views/home_screen/popups/bag/bag.d.ts` — зависимость: входные типы `ItemJSON`/`ResourceJSON`/`TankJSON`/`AirplaneJSON`.
- `src/views/home_screen/popups/profile/collections/collection.d.ts` — зависимость: входной тип `CollectionItemJSON`.
- `src/views/home_screen/HomeScreenQuest.ts` — иконка награды квеста на главном экране (`createImageLayout`).
- `src/views/home_screen/popups/idle/IdlePopup.ts` — список idle-наград (`createRewardsLayout`).
- `src/views/battlefield_screen/BattlefieldScreen.ts` — список наград за бой (`createRewardsLayout`).
- `src/views/home_screen/popups/profile/ProfileSection.ts` — карточки танков и самолётов в профиле (`createTankLayout`/`createAirplaneLayout`).
- `src/views/home_screen/popups/profile/codex/CodexTanksSection.ts` — карточки танков в кодексе (`createTankLayout`).
- `src/views/home_screen/popups/profile/codex/CodexAirplanesSection.ts` — карточки самолётов в кодексе (`createAirplaneLayout`).
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts` — превью награды за комплект: карточка танка (`createTankLayout`) или список наград (`createRewardsCustomLayout`).
