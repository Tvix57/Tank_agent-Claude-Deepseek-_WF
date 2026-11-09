# Реестр документации компонентов сервера

Владелец — `server-librarian-lead`: только он правит этот файл (шаги ведения — в его
`.claude/agents/librarians/server-librarian-lead.md`, раздел "Реестр документации"). Остальные агенты
и базовая сессия читают; изменения передают ему. Клиентский аналог —
`/workspace/client/.claude/docs/component-docs-registry.md`.

Колонки:
- **Компонент** — класс `*UserComponent` (пакет `com.linkedgames.game.model.<пакет>`) или область без
  своего компонента.
- **Документация** — путь от `/workspace/server/.claude/docs/`; `—` — документа нет.
- **Статус** — `обычный` (по итогам разработки, в т.ч. документ по коду, написанному в этой задаче по ГДД/ТЗ, или по прямому запросу пользователя), `auto-create` (по сканированию кода, доверять с
  осторожностью), `смешанный` (часть разделов auto-create — какие, указано в шапке документа),
  `частично` (документ покрывает только часть компонента — что именно, в скобках), `нет`.
- **Обновлено** — дата последней правки документа: последняя запись его истории изменений или дата,
  которую назвал отправитель при регистрации. Для `нет` — дата, когда строка внесена.

Доля прочитанных аналитиками файлов кода и список непрочитанных — `source-scan-coverage.md`.

## Компоненты пользователя (`UserChildComponent`)

| Компонент | Пакет | Документация | Статус | Обновлено |
|---|---|---|---|---|
| AchievementUserComponent | achievements | [achievements-architecture.md](achievements-architecture.md) | auto-create | 2026-10-19 |
| AerodromeUserComponent | aerodrome | [aerodrome-architecture.md](aerodrome-architecture.md) | auto-create | 2026-10-19 |
| AssemblyUserComponent | assembly | [assembly-architecture.md](assembly-architecture.md) | auto-create | 2026-10-19 |
| BagUserComponent | bag | [bag-architecture.md](bag-architecture.md) | auto-create | 2026-10-19 |
| BattleUserComponent | battle | [battle-architecture.md](battle-architecture.md) | auto-create | 2026-10-19 |
| BattlefieldUserComponent | battlefield | — | нет | 2026-10-13 |
| CampaignUserComponent | campaign | [campaign-architecture.md](campaign-architecture.md) (основной), [airdrop-architecture.md](airdrop-architecture.md) (airDrop) | auto-create | 2026-10-19 |
| ClanUserComponent | clan (+ service.clan, ClanPage, ClanChatPage, dao.ClanDao, миграция 1774862812051_clans) | — | нет | 2026-10-19 |
| CodexUserComponent | codex | [codex-architecture.md](codex-architecture.md) | auto-create | 2026-10-19 |
| CollectionUserComponent | collections | [collections-architecture.md](collections-architecture.md) | обычный | 2026-10-19 |
| HangarUserComponent | hangar | [hangar-architecture.md](hangar-architecture.md); ГДД: [hangar-gdd.md](/workspace/client/.claude/docs/game-design/hangar-gdd.md) | auto-create | 2026-10-19 |
| IdleUserComponent | idle | — | нет | 2026-10-13 |
| LootboxUserComponent | lootbox (+ bag/lootbox/Lootbox, LootboxSlot, LootboxPage; ветка koba/lootbox) | [lootbox-architecture.md](lootbox-architecture.md); ГДД: [lootbox-gdd.md](/workspace/client/.claude/docs/game-design/lootbox-gdd.md) | обычный | 2026-10-30 |
| MailboxUserComponent | mailbox | [mailbox-architecture.md](mailbox-architecture.md); ГДД: [mailbox-gdd.md](/workspace/client/.claude/docs/game-design/mailbox-gdd.md) | auto-create | 2026-10-19 |
| MilitaryBaseUserComponent | military_base (+ bag/military_base/*, MilitaryBasePage) | [military-base-architecture.md](military-base-architecture.md); ГДД: [military-base-gdd.md](/workspace/client/.claude/docs/game-design/military-base-gdd.md) | auto-create | 2026-10-22 |
| NotificationUserComponent | notifications | — | нет | 2026-10-13 |
| OffersUserComponent | offers | [offers-architecture.md](offers-architecture.md); ГДД: [shop-gdd.md](/workspace/client/.claude/docs/game-design/shop-gdd.md) (область «Магазин и офферы») | auto-create | 2026-10-19 |
| QuestsUserComponent | quests | [quests-architecture.md](quests-architecture.md) | auto-create | 2026-10-27 (+паттерн настраиваемой награды) |
| StateUserComponent | state | — | нет | 2026-10-13 |
| TrainUserComponent | train | [train-architecture.md](train-architecture.md) | auto-create | 2026-10-19 |
| TutorialUserComponent | tutorial | [tutorial-architecture.md](tutorial-architecture.md) | auto-create | 2026-10-19 |

## Области без своего компонента

| Область | Классы | Документация | Статус | Обновлено |
|---|---|---|---|---|
| Балансовые данные танков и самолётов | TankData, AirplaneData | [tank-airplane-data-architecture.md](tank-airplane-data-architecture.md) | auto-create | 2026-10-19 |
| Бой (движок боя танков и самолётов, без Battlefield) | model.battle: Battle, Fighter, units/*, events/*, data/* | [battle-architecture.md](battle-architecture.md) | auto-create | 2026-10-19 |
| Бан-панель и модерация | BanPanelPage, dao.BanPanelDao, model.ban.* (BanType, BanActions, BanHistoryEntry, BanCancelInfo, BanGeneralInfo), ModeratorsChatService, ModeratorsChatPage | [ban-architecture.md](ban-architecture.md); ГДД: [ban-gdd.md](/workspace/client/.claude/docs/game-design/ban-gdd.md) | auto-create | 2026-10-19 |
| Summon (общий призыв танков и самолётов, листы баланса) | model.summon.data.SummonUpgradeData; листы SummonUpgrade, SummonRankChances, SummonStarsRankChances | — (частично: [train-architecture.md](train-architecture.md) §«Таблицы баланса поезда (общий Summon)», [aerodrome-architecture.md](aerodrome-architecture.md)) | частично (только таблицы баланса Summon в доках поезда и аэродрома) | 2026-10-19 |
| PvP рейтинговые бои | service.campaign.RankedChallengeService, RankedChallengeActor, RankedChallengeEntry, RankedChallengeBattleContext, LeagueMeta; dao.RankedChallengeDao, RankedChallengeHistoryDao | — | нет | 2026-10-19 |
| Рейтинг кланов | service.rating.RatingClanService, pages.ws.ingame.RatingPage | — | нет | 2026-10-19 |
| Интеграции площадок (SDK/API: ВК, ОК, Yandex, Overmobile, ЮKassa; авторизация /social) | service.integration.* (IntegrationUtil, SocialPortal, VKUtil, OdnoklassnikiUtil, OvermobileService, YookassaUtil), GatewayPage | [platform-sdk-architecture.md](platform-sdk-architecture.md) (ярлык Yandex; платежи: [offers-architecture.md](offers-architecture.md) §«Платёжные страницы», §«Карта файлов») | частично (только фича ярлыка Yandex — YandexUserComponent; остальной service.integration и GatewayPage не описаны) | 2026-10-26 |
