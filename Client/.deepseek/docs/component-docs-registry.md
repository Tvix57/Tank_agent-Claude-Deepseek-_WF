# Реестр документации компонентов клиента

Владелец — `client-librarian-lead`: только он правит этот файл (шаги ведения — в его
`.claude/agents/librarians/client-librarian-lead.md`, раздел "Реестр документации"). Остальные агенты
и базовая сессия читают; изменения передают ему. Серверный аналог —
`/workspace/server/.claude/docs/component-docs-registry.md`.

Колонки:
- **Компонент** — экран, попап или подраздел UI (папка в `src/views/`), утилита/пресет.
- **Путь** — папка или файл от `src/`.
- **Документация** — путь от `/workspace/client/.claude/docs/`; `—` — документа нет.
- **Статус** — `обычный` (по итогам разработки, в т.ч. документ по коду, написанному в этой задаче по ГДД/ТЗ, или по прямому запросу пользователя), `auto-create`
  (по сканированию кода, доверять с осторожностью), `смешанный` (часть разделов auto-create — какие,
  указано в шапке документа), `частично` (документ покрывает только часть — что именно, в скобках),
  `нет`.
- **Обновлено** — дата последней правки документа: последняя запись его истории изменений или дата,
  которую назвал отправитель при регистрации. Для `нет` — дата, когда строка внесена.

Паттерны и сквозные механизмы (`popup-queue-pattern.md`, `server-push-events-subscription.md`,
`asset-packaging.md`) в реестр не входят — их ведут `client-librarian-patterns-*`. Баги в областях
без документа — `undocumented-areas-known-bugs.md`.
Доля прочитанных аналитиками файлов кода и список непрочитанных — `source-scan-coverage.md`.

## Экраны и попапы (`src/views/`)

| Компонент | Путь | Документация | Статус | Обновлено |
|---|---|---|---|---|
| Экран бана | views/ban_screen | [ban-architecture.md](ban-architecture.md); ГДД: [ban-gdd.md](game-design/ban-gdd.md) | auto-create | 2026-10-19 |
| Бой (самолёты и воздушный бой) | views/battle/air, views/battle/BattleAirstrike.ts, battle/units/UnitAirplane.ts | [air-battle-architecture.md](air-battle-architecture.md); ГДД: [battle-gdd.md](game-design/battle-gdd.md) | auto-create | 2026-10-19 |
| Экран поля боя | views/battlefield_screen | — | нет | 2026-10-13 |
| Главный экран | views/home_screen | — | нет | 2026-10-13 |
| Квесты (слот на главной) | views/home_screen/HomeScreenQuest.ts | — (клиентского дока нет); ГДД: [quests-gdd.md](game-design/quests-gdd.md) | нет | 2026-10-27 |
| Кампания (карта) | views/home_screen/campaign | [campaign-architecture.md](campaign-architecture.md); ГДД: [campaign-gdd.md](game-design/campaign-gdd.md) | auto-create | 2026-10-19 |
| AirDrop | views/home_screen/campaign | [airdrop-architecture.md](airdrop-architecture.md); ГДД: [airdrop-gdd.md](game-design/airdrop-gdd.md) | auto-create | 2026-10-19 |
| Аэродром | views/home_screen/popups/airplane (AirplaneGetPopup), views/home_screen/HomeScreenAerodrome.ts; окна радиовышки/аэродрома удалены merge-ом (`popups/aerodrome` — нет в дереве) | [aerodrome-architecture.md](aerodrome-architecture.md); ГДД: [aerodrome-gdd.md](game-design/aerodrome-gdd.md) | auto-create | 2026-10-19 |
| Военная база | views/home_screen/popups/military_base, views/home_screen/HomeScreenMilitaryBase.ts, plain/military_base/MilitaryBaseBoostRouter.ts, popups/military_base/militaryBase.d.ts, shared/header/presets/HeaderDollarsBar.ts, HeaderTokensBar.ts | [military-base-architecture.md](military-base-architecture.md); ГДД: [military-base-gdd.md](game-design/military-base-gdd.md) | auto-create | 2026-10-22 |
| Кланы | views/home_screen/popups/clan, views/home_screen/popups/clan/clans.d.ts, views/home_screen/popups/chat/ClanChatSection.ts | — | нет | 2026-10-19 |
| Рейтинг кампании/PvP | views/home_screen/campaign/RankedProfile.ts, views/home_screen/popups/campaign/CampaignRankedHistory.ts, views/home_screen/popups/rating/RatingCampaignRankingSection.ts, views/home_screen/popups/rating/RatingClanSection.ts, battle/ranking/Ranking.ts | — | нет | 2026-10-19 |
| Самолёт | views/home_screen/popups/airplane | — | нет | 2026-10-13 |
| Сборка | views/home_screen/popups/assembly | [assembly-architecture.md](assembly-architecture.md); ГДД: [assembly-gdd.md](game-design/assembly-gdd.md) | auto-create | 2026-10-19 |
| Сумка | views/home_screen/popups/bag | [bag-architecture.md](bag-architecture.md); ГДД: [bag-gdd.md](game-design/bag-gdd.md) | auto-create | 2026-10-19 |
| Бан-панель | views/home_screen/popups/banPanel | [ban-architecture.md](ban-architecture.md); ГДД: [ban-gdd.md](game-design/ban-gdd.md) | auto-create | 2026-10-19 |
| Поле боя (попап) | views/home_screen/popups/battlefield | — | нет | 2026-10-13 |
| Кампания (попапы) | views/home_screen/popups/campaign | [campaign-architecture.md](campaign-architecture.md); ГДД: [campaign-gdd.md](game-design/campaign-gdd.md) | auto-create | 2026-10-19 |
| Чат | views/home_screen/popups/chat | — | нет | 2026-10-13 |
| Idle | views/home_screen/popups/idle | — ; ГДД: [lootbox-gdd.md](game-design/lootbox-gdd.md) (окно «Трофеи», раздел #gdd-trophies-window) | нет | 2026-10-28 |
| Лутбоксы | views/home_screen/popups/lootbox (+ LootboxState.ts — состояние, plain/RewardFlightUtils.ts; окно — views/home_screen/popups/idle; таймер и сброс значка — views/home_screen/IdleBtn.ts) | [lootbox-architecture.md](lootbox-architecture.md); ГДД: [lootbox-gdd.md](game-design/lootbox-gdd.md) | обычный | 2026-10-29 |
| Почта | views/home_screen/popups/mailbox | [mailbox-architecture.md](mailbox-architecture.md); ГДД: [mailbox-gdd.md](game-design/mailbox-gdd.md) | auto-create | 2026-10-19 |
| Профиль | views/home_screen/popups/profile | — | нет | 2026-10-13 |
| Достижения | views/home_screen/popups/profile/achievements | [achievements-architecture.md](achievements-architecture.md); ГДД: [achievements-gdd.md](game-design/achievements-gdd.md) | auto-create | 2026-10-19 |
| Кодекс | views/home_screen/popups/profile/codex | [codex-architecture.md](codex-architecture.md) | auto-create | 2026-10-19 |
| Коллекции | views/home_screen/popups/profile/collections | [collections-architecture.md](collections-architecture.md); ГДД: [collections-gdd.md](game-design/collections-gdd.md) | обычный | 2026-10-23 |
| Рейтинг | views/home_screen/popups/rating | — | нет | 2026-10-13 |
| Настройки | views/home_screen/popups/settings | — | нет | 2026-10-13 |
| Магазин и офферы | views/home_screen/popups/shop, utils/PaymentHelper.ts | [shop-architecture.md](shop-architecture.md); ГДД: [shop-gdd.md](game-design/shop-gdd.md) | auto-create | 2026-10-19 |
| Ангар (танки) | views/home_screen/popups/tank | [hangar-architecture.md](hangar-architecture.md); ГДД: [hangar-gdd.md](game-design/hangar-gdd.md) | auto-create | 2026-10-19 |
| Поезд | views/home_screen/popups/train | [train-architecture.md](train-architecture.md); ГДД: [train-gdd.md](game-design/train-gdd.md) | смешанный | 2026-10-23 |
| Общие попапы | views/popups | — | нет | 2026-10-13 |
| Туториал | views/tutorial | [tutorial-architecture.md](tutorial-architecture.md) — область сведена к остаткам после merge (судьба дока ждёт решения пользователя) | auto-create | 2026-10-19 |
| Приветственный экран | views/welcome_screen | — | нет | 2026-10-13 |

## Утилиты, пресеты, общие элементы UI

| Компонент | Путь | Документация | Статус | Обновлено |
|---|---|---|---|---|
| ItemsPresets | presets/ItemsPresets.ts | [items-presets-architecture.md](items-presets-architecture.md) | частично (разделы про `COLLECTION_ITEM`, `createImageCollectionItem`, `createRewardsCustomLayout` не совпадают с кодом `koba/lootbox`, см. [client-ui-patterns.md#doc-drift](client-ui-patterns.md#doc-drift)) | 2026-10-19 |
| PanelsPresets, ButtonPresets | presets/PanelsPresets.ts, presets/ButtonPresets.ts | [panels-buttons-presets-architecture.md](panels-buttons-presets-architecture.md) | обычный | 2026-10-19 |
| CollectionUtils | utils/CollectionUtils.ts | [collections-architecture.md](collections-architecture.md#cls-collectionutils) | обычный | 2026-10-13 |
| FlyIconsAnimation | shared/animations/FlyIconsAnimation.ts | [client-ui-patterns.md](client-ui-patterns.md#fly-to-target) | auto-create | 2026-10-27 |
| RewardFlightUtils | plain/RewardFlightUtils.ts | [reward-flight-utils-architecture.md](reward-flight-utils-architecture.md) | обычный | 2026-10-30 |
| AdvancedPaginator | shared/paginators/AdvancedPaginator.ts | [client-ui-patterns.md](client-ui-patterns.md#paged-grid) | auto-create | 2026-10-27 |
| RewardUtils | plain/RewardUtils.ts | [client-ui-patterns.md](client-ui-patterns.md#files) (только карта файлов, роль — зависимость) | частично (нет отдельного раздела) | 2026-10-27 |
| Every | plain/Every.ts | [client-ui-patterns.md](client-ui-patterns.md#files) (только карта файлов) | частично (нет отдельного раздела) | 2026-10-27 |
| TimeUtils | utils/TimeUtils.ts | [client-ui-patterns.md](client-ui-patterns.md#files) (только карта файлов, роль — зависимость) | частично (нет отдельного раздела) | 2026-10-27 |
| Бой (движок и наземный) | battle, views/battle/ground | [battle-architecture.md](battle-architecture.md); ГДД: [battle-gdd.md](game-design/battle-gdd.md) | auto-create | 2026-10-19 |
| Шапка (Header) | shared/header | — | нет | 2026-10-13 |
| Подвал (Footer) | shared/footer | — | нет | 2026-10-13 |
| Нотификации | shared/notifications | — | нет | 2026-10-13 |
| Флеши | shared/flash | — | нет | 2026-10-13 |
| Интеграции площадок (SDK, авторизация, Overmobile, Yandex Games) | plain/IntegrationUtils.ts, utils/AgreementUtils.ts | — (косвенно: [shop-architecture.md](shop-architecture.md), раздел PaymentHelper); ГДД: [platform-sdk-gdd.md](game-design/platform-sdk-gdd.md) (архитектуры нет) | нет | 2026-10-26 |
