# Покрытие кода сканированием (клиент)

Владелец — `client-librarian-lead`. Файл показывает, какая доля файлов кода хотя бы раз прочитана
аналитиком при сканировании, и где лежат непрочитанные. По списку
[непросканированных](#unscanned) ищут код без ярко выраженных признаков отдельной области (нет своей
папки в `src/views/` и domain `*.d.ts`, см. `agent-system-workflow.md#area-sign`): утилиты, модели
`src/plain/`, общие виджеты `src/shared/`, пресеты. Такой код не попадает ни в один документ сам по
себе: аналитики областей читают его только попутно. Серверный аналог —
`/workspace/server/.claude/docs/source-scan-coverage.md`.

**Файл кода** — `src/**/*.ts`, включая `*.d.ts`; без `src/ee/` (движок, не документируем).

**Отметка** — строка в [журнале отметок](#marks): файл прочитан целиком при сканировании области.
Отметки ставятся вручную, по полю `ПРОСКАНИРОВАНО` отправителя при регистрации документа
(`agent-system-workflow.md#scan-coverage`). Упоминание файла в документе отметкой не считается.
Исключение — разовые строки `первичное заполнение` (2026-10-18): файлы из раздела «Файлы прямого
влияния» карт файлов уже существующих `*-architecture.md`.

**Как обновлять** — только скриптом, руками не править генерируемые разделы:

```
python3 /workspace/client/.claude/scripts/scan_coverage.py /workspace/client --mark <пути> --by <агент> --doc <документ>
python3 /workspace/client/.claude/scripts/scan_coverage.py /workspace/client   # только пересчёт
```

`<пути>` — от корня репозитория, уникальный хвост пути или папка. Скрипт печатает итог;
`НЕ РАСПОЗНАНО: …` — эти пути не отмечены, уточнить у отправителя. Отметки на удалённые файлы
скрипт выводит в [#stale-marks](#stale-marks) — удалить их строки из журнала и пересчитать.

<!-- generated:start -->
## Итог {#total}

Пересчитано 2026-10-30: просканировано **181 из 310** файлов кода — **58.4%**.

## По папкам {#by-folder}

Сортировка — от наименее покрытых.

| Папка | Файлов | Просканировано | % |
|---|---|---|---|
| (корень src) | 4 | 0 | 0% |
| plain/globals | 5 | 0 | 0% |
| plain/quests | 1 | 0 | 0% |
| plain/tank | 2 | 0 | 0% |
| shared/flash | 5 | 0 | 0% |
| views | 1 | 0 | 0% |
| views/battlefield_screen | 7 | 0 | 0% |
| views/welcome_screen | 3 | 0 | 0% |
| utils | 12 | 2 | 17% |
| shared | 10 | 2 | 20% |
| shared/animations | 4 | 1 | 25% |
| scenes | 3 | 1 | 33% |
| shared/header | 9 | 3 | 33% |
| types | 6 | 2 | 33% |
| battle/events | 21 | 8 | 38% |
| presets | 7 | 3 | 43% |
| plain/items | 2 | 1 | 50% |
| plain | 15 | 9 | 60% |
| plain/user | 3 | 2 | 67% |
| views/home_screen | 152 | 111 | 73% |
| plain/airplane | 4 | 3 | 75% |
| views/popups | 4 | 3 | 75% |
| battle | 9 | 9 | 100% |
| battle/ranking | 1 | 1 | 100% |
| battle/recharge | 3 | 3 | 100% |
| battle/units | 2 | 2 | 100% |
| plain/military_base | 1 | 1 | 100% |
| shared/footer | 1 | 1 | 100% |
| shared/notifications | 1 | 1 | 100% |
| shared/paginators | 1 | 1 | 100% |
| views/ban_screen | 1 | 1 | 100% |
| views/battle | 9 | 9 | 100% |
| views/tutorial | 1 | 1 | 100% |

## Непросканированные файлы {#unscanned}

### (корень src) (4)

- `src/Const.ts`
- `src/SceneImpl.ts`
- `src/ScreenImpl.ts`
- `src/index.ts`

### plain/globals (5)

- `src/plain/globals/Cookie.ts`
- `src/plain/globals/CookieOptions.ts`
- `src/plain/globals/I18n.ts`
- `src/plain/globals/Scheduler.ts`
- `src/plain/globals/WSSocket.ts`

### plain/quests (1)

- `src/plain/quests/QuestEvent.ts`

### plain/tank (2)

- `src/plain/tank/TankAmmoType.ts`
- `src/plain/tank/TankArmorType.ts`

### shared/flash (5)

- `src/shared/flash/DuplicateConnectionFlash.ts`
- `src/shared/flash/GameFlash.ts`
- `src/shared/flash/LoadingFlash.ts`
- `src/shared/flash/ServerNotificationFlash.ts`
- `src/shared/flash/VersionFlash.ts`

### views (1)

- `src/views/ObjectCreator.ts`

### views/battlefield_screen (7)

- `src/views/battlefield_screen/BattlefieldBattleGround.ts`
- `src/views/battlefield_screen/BattlefieldScreen.ts`
- `src/views/battlefield_screen/BattlefieldSlot.ts`
- `src/views/battlefield_screen/BattlefieldSlotLine.ts`
- `src/views/battlefield_screen/BattlefieldUnitFrame.ts`
- `src/views/battlefield_screen/BattlefieldUnitFrameData.ts`
- `src/views/battlefield_screen/battlefield.d.ts`

### views/welcome_screen (3)

- `src/views/welcome_screen/LoginPopup.ts`
- `src/views/welcome_screen/RecoveryPasswordPopup.ts`
- `src/views/welcome_screen/WelcomeScreen.ts`

### utils (10)

- `src/utils/AirplaneUtils.ts`
- `src/utils/ArrayUtils.ts`
- `src/utils/AsyncResult.ts`
- `src/utils/NumberUtils.ts`
- `src/utils/ResourceCounter.ts`
- `src/utils/ResultUtils.ts`
- `src/utils/SequentialQueue.ts`
- `src/utils/StringUtils.ts`
- `src/utils/TankUtils.ts`
- `src/utils/TimeUtils.ts`

### shared (8)

- `src/shared/AnimatedProgressBar.ts`
- `src/shared/AsyncSprite.ts`
- `src/shared/CheckBox.ts`
- `src/shared/FlashPublisher.ts`
- `src/shared/ListBox.ts`
- `src/shared/MovedSprite.ts`
- `src/shared/Slider.ts`
- `src/shared/TabSelector.ts`

### shared/animations (3)

- `src/shared/animations/AttentionAnimation.ts`
- `src/shared/animations/LevelUpAnimation.ts`
- `src/shared/animations/LightRunAnimation.ts`

### scenes (2)

- `src/scenes/LoadingScene.ts`
- `src/scenes/WelcomeScene.ts`

### shared/header (6)

- `src/shared/header/Header.ts`
- `src/shared/header/HeaderPresets.ts`
- `src/shared/header/IHeaderPreset.ts`
- `src/shared/header/presets/HeaderGoldenCoinsBar.ts`
- `src/shared/header/presets/HeaderProfile.ts`
- `src/shared/header/presets/HeaderSilverCoinsBar.ts`

### types (4)

- `src/types/jloader.d.ts`
- `src/types/packer.d.ts`
- `src/types/pixi-spine.d.ts`
- `src/types/pixi.js.d.ts`

### battle/events (13)

- `src/battle/events/airplane/AirplaneAttackEvent.ts`
- `src/battle/events/airplane/AirplaneDestroyedEvent.ts`
- `src/battle/events/airplane/AirplanePrepareTakeoffEvent.ts`
- `src/battle/events/airplane/AirplaneRechargeEvent.ts`
- `src/battle/events/airplane/AirplaneReplacedEvent.ts`
- `src/battle/events/airplane/AirplaneSpawnEvent.ts`
- `src/battle/events/airplane/AirplaneTakeDamageEvent.ts`
- `src/battle/events/airplane/AirplaneTakeoffEvent.ts`
- `src/battle/events/tank/TankAttackEvent.ts`
- `src/battle/events/tank/TankDestroyedEvent.ts`
- `src/battle/events/tank/TankRechargeEvent.ts`
- `src/battle/events/tank/TankReplacedEvent.ts`
- `src/battle/events/tank/TankSpawnEvent.ts`

### presets (4)

- `src/presets/AirplanePresets.ts`
- `src/presets/InputTextPresets.ts`
- `src/presets/RankPresets.ts`
- `src/presets/TankPresets.ts`

### plain/items (1)

- `src/plain/items/ItemId.ts`

### plain (6)

- `src/plain/Coord.ts`
- `src/plain/EventEmitter.ts`
- `src/plain/LoadAssetPackage.ts`
- `src/plain/Logger.ts`
- `src/plain/Utility.ts`
- `src/plain/Vars.ts`

### plain/user (1)

- `src/plain/user/Sex.ts`

### views/home_screen (41)

- `src/views/home_screen/campaign/RankedProfile.ts`
- `src/views/home_screen/popups/battlefield/BattlefieldPopup.ts`
- `src/views/home_screen/popups/battlefield/BattlefiendState.ts`
- `src/views/home_screen/popups/battlefield/battlefield.d.ts`
- `src/views/home_screen/popups/campaign/CampaignRankedHistory.ts`
- `src/views/home_screen/popups/clan/ClanInfoPopup.ts`
- `src/views/home_screen/popups/clan/ClanPopup.ts`
- `src/views/home_screen/popups/clan/ClanUser.ts`
- `src/views/home_screen/popups/clan/ClanUserProfilePopup.ts`
- `src/views/home_screen/popups/clan/ClanUserRole.ts`
- `src/views/home_screen/popups/clan/ClanUtils.ts`
- `src/views/home_screen/popups/clan/clans.d.ts`
- `src/views/home_screen/popups/idle/idle.d.ts`
- `src/views/home_screen/popups/military_base/MilitaryBaseBackground.ts`
- `src/views/home_screen/popups/military_base/MilitaryBaseBuyBuildingPopup.ts`
- `src/views/home_screen/popups/military_base/MilitaryBaseResourcesPopup.ts`
- `src/views/home_screen/popups/military_base/MilitaryBaseSellResourcePopup.ts`
- `src/views/home_screen/popups/military_base/MilitaryBaseStorageResource.ts`
- `src/views/home_screen/popups/profile/ProfilePopup.ts`
- `src/views/home_screen/popups/profile/ProfileSection.ts`
- `src/views/home_screen/popups/profile/ProfileTabSelector.ts`
- `src/views/home_screen/popups/profile/RewardsSection.ts`
- `src/views/home_screen/popups/profile/SettingsSection.ts`
- `src/views/home_screen/popups/profile/profile.d.ts`
- `src/views/home_screen/popups/rating/RatingAirplanesSection.ts`
- `src/views/home_screen/popups/rating/RatingBattlefieldSection.ts`
- `src/views/home_screen/popups/rating/RatingCampaignRankingSection.ts`
- `src/views/home_screen/popups/rating/RatingCampaignSection.ts`
- `src/views/home_screen/popups/rating/RatingClanSection.ts`
- `src/views/home_screen/popups/rating/RatingPopup.ts`
- `src/views/home_screen/popups/rating/RatingPowerSection.ts`
- `src/views/home_screen/popups/rating/RatingTabSelector.ts`
- `src/views/home_screen/popups/rating/RatingTanksSection.ts`
- `src/views/home_screen/popups/rating/rating.d.ts`
- `src/views/home_screen/popups/settings/ChangeNamePopup.ts`
- `src/views/home_screen/popups/settings/ChangePasswordPopup.ts`
- `src/views/home_screen/popups/settings/ConnectPopup.ts`
- `src/views/home_screen/popups/settings/ExitPopup.ts`
- `src/views/home_screen/popups/settings/HtmlViewPopup.ts`
- `src/views/home_screen/popups/settings/LanguagePopup.ts`
- `src/views/home_screen/popups/settings/NewsPopup.ts`

### plain/airplane (1)

- `src/plain/airplane/AirplaneType.ts`

### views/popups (1)

- `src/views/popups/AirplaneInfoPopup.ts`

## Отметки на несуществующие файлы {#stale-marks}

- `src/utils/CollectionUtils.ts`
- `src/views/home_screen/popups/profile/collections/CollectionSectionPopup.ts`
- `src/views/home_screen/popups/profile/collections/CollectionsListSection.ts`
- `src/views/home_screen/popups/profile/collections/CollectionsSection.ts`
- `src/views/home_screen/popups/profile/collections/CollectionsType.ts`
- `src/views/home_screen/popups/profile/collections/collection.d.ts`
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsExperimentalAirplanesSection.ts`
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsExperimentalTanksSection.ts`
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsTypeSection.ts`
- `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsUSSROperationsSection.ts`
- `src/views/home_screen/popups/profile/collections/collection_type/Collection.ts`
- `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbum.ts`
- `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbumCard.ts`
- `src/views/home_screen/popups/profile/collections/collection_type/collection_album.d.ts`
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts`
- `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/collection_experimental_tank.d.ts`
- `src/views/home_screen/popups/train/TrainCollectionItemPopup.ts`
- `src/views/popups/CollectionCompletePopup.ts`
<!-- generated:end -->

## История замеров {#history}

<!-- history:start -->
- 2026-10-18 — 54.0% (147/272)
- 2026-10-19 — 45.9% (147/320)
- 2026-10-22 — 55.3% (177/320)
- 2026-10-23 — 55.3% (177/320)
- 2026-10-26 — 53.5% (161/301)
- 2026-10-27 — 55.5% (167/301)
- 2026-10-29 — 58.4% (181/310)
- 2026-10-30 — 58.4% (181/310)
<!-- history:end -->

## Журнал отметок {#marks}

<!-- marks:start -->
| Файл | Документ | Кто отметил | Дата |
|---|---|---|---|
| `src/battle/Battle.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/BattleAnalyzer.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/BattleBalance.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/BattleEvent.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/BattleRandom.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/BattleType.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/BattleUnit.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/Fighter.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/IBattleUI.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/BattleEventFactory.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/BattlePlaceEvent.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/BattleResultEvent.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/ChangeOpponentEvent.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/DodgeEvent.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/NewOpponentEvent.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/SlotResultEvent.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/events/tank/TankTakeDamageEvent.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/ranking/Ranking.ts` | battle-architecture.md | client-analyst-battle | 2026-10-19 |
| `src/battle/recharge/AirplaneRecharge.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/recharge/RechargeMode.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/recharge/TankRecharge.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/units/UnitAirplane.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/battle/units/UnitTank.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/plain/Every.ts` | client-ui-patterns.md | client-analyst-lead | 2026-10-27 |
| `src/plain/GameEvents.ts` | hangar-architecture.md | первичное заполнение | 2026-10-18 |
| `src/plain/Globals.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/plain/IntegrationUtils.ts` | platform-sdk-gdd.md | client-analyst-platform-sdk | 2026-10-26 |
| `src/plain/MessageDecoder.ts` | mailbox-architecture.md | client-analyst-mailbox | 2026-10-19 |
| `src/plain/RewardFlightUtils.ts` | reward-flight-utils-architecture.md | client-librarian-lead | 2026-10-30 |
| `src/plain/RewardUtils.ts` | client-ui-patterns.md | client-analyst-lead | 2026-10-27 |
| `src/plain/ScreenRedirector.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/plain/TutorialUtils.ts` | tutorial-architecture.md | client-analyst-tutorial | 2026-10-19 |
| `src/plain/airplane/AirplaneArmorType.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/plain/airplane/AirplaneBombType.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/plain/airplane/AirplaneGunType.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/plain/items/ItemType.ts` | lootbox-gdd.md | client-analyst-lootbox | 2026-10-27 |
| `src/plain/military_base/MilitaryBaseBoostRouter.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/plain/user/User.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/plain/user/UserBag.ts` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `src/presets/ButtonPresets.ts` | panels-buttons-presets-architecture.md | первичное заполнение | 2026-10-18 |
| `src/presets/ItemsPresets.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/presets/PanelsPresets.ts` | panels-buttons-presets-architecture.md | первичное заполнение | 2026-10-18 |
| `src/scenes/InGameScene.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/shared/PresentationFlow.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/shared/Users.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/shared/animations/FlyIconsAnimation.ts` | client-ui-patterns.md | client-analyst-lead | 2026-10-27 |
| `src/shared/footer/Footer.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/shared/header/presets/HeaderAchievementsBar.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/shared/header/presets/HeaderDollarsBar.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/shared/header/presets/HeaderTokensBar.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/shared/notifications/Notifications.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/shared/paginators/AdvancedPaginator.ts` | client-ui-patterns.md | client-analyst-lead | 2026-10-27 |
| `src/types/battle.d.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/types/interfaces.d.ts` | airdrop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/utils/AgreementUtils.ts` | platform-sdk-gdd.md | client-analyst-platform-sdk | 2026-10-26 |
| `src/utils/CollectionUtils.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/utils/PaymentHelper.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/ban_screen/BanScreen.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/battle/BattleAirstrike.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/air/BattleAir.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/air/BattleAirAirplane.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/air/animations/AnimationAirplaneShot.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/ground/BattleGround.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/ground/BattleGroundAirplane.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/ground/BattleGroundTank.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/ground/animations/AnimationAirstrike.ts` | air-battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/battle/ground/animations/AnimationTankShot.ts` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/HomeScreen.ts` | train-architecture.md | client-analyst-lead | 2026-10-23 |
| `src/views/home_screen/HomeScreenAerodrome.ts` | aerodrome-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/HomeScreenAssembly.ts` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/HomeScreenMilitaryBase.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/HomeScreenQuest.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/IdleBtn.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/TrainAutoSummonBtn.ts` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/TrainUpgradeBtn.ts` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/TrainUpgradeProgressBar.ts` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/campaign/AirDrop.ts` | airdrop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/campaign/CampaignBattleEndedData.ts` | campaign-architecture.md | client-analyst-campaign | 2026-10-19 |
| `src/views/home_screen/campaign/CampaignBattleGround.ts` | campaign-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/home.d.ts` | hangar-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/airplane/AirplaneGetPopup.ts` | aerodrome-architecture.md | client-analyst-aerodrome | 2026-10-19 |
| `src/views/home_screen/popups/assembly/AssemblyPopup.ts` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/assembly/assembly.d.ts` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/bag/bag.d.ts` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/banPanel/BanHistoryPanel.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/banPanel/BanPanelPopup.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/banPanel/BanReaskPopup.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/banPanel/BanType.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/banPanel/PlayerInfoPopup.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/banPanel/banPanel.d.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/campaign/CampaignLevelRewardsPopup.ts` | campaign-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/campaign/CampaignPopup.ts` | campaign-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/campaign/campaign.d.ts` | campaign-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/chat/AbstractChatSection.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/chat/ChatMessage.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/chat/ChatPopup.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/chat/ChatSection.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/chat/ClanChatSection.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/chat/GlobalChatSection.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/chat/ModeratorChatSection.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/chat/chat.d.ts` | ban-architecture.md | client-analyst-lead | 2026-10-18 |
| `src/views/home_screen/popups/idle/IdlePopup.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/LootboxReceivedPopup.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/LootboxRewardPopup.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/LootboxIdleSection.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/LootboxSpeedupPopup.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/LootboxStartOpenPopup.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/LootboxState.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/LootboxUtils.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/lootbox/lootbox.d.ts` | lootbox-architecture.md | client-analyst-lootbox | 2026-10-29 |
| `src/views/home_screen/popups/mailbox/MailboxBlacklistSection.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/MailboxDialogsSection.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/MailboxFriendsSection.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/MailboxMessagesSection.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/MailboxPopup.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/MailboxRewardsSection.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/MailboxUtils.ts` | mailbox-architecture.md | client-analyst-mailbox | 2026-10-19 |
| `src/views/home_screen/popups/mailbox/content/MailboxClanInviteMessage.ts` | mailbox-architecture.md | client-analyst-mailbox | 2026-10-19 |
| `src/views/home_screen/popups/mailbox/content/MailboxMessage.ts` | mailbox-architecture.md | client-analyst-mailbox | 2026-10-19 |
| `src/views/home_screen/popups/mailbox/mailbox.d.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/popups/AddToBlacklistPopup.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/popups/AddToFriendsPopup.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/popups/DeleteFromBlacklistPopup.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/mailbox/popups/DeleteFromFriendsPopup.ts` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/military_base/MilitaryBaseAerodromePopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseAviationFactoryInfoPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseAviationFactoryPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseAviationFactorySlot.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseBoost.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseBoostMedium.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseBoostPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseBoostSmall.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseData.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseHeadquartersInfoPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseHeadquartersPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseHeadquartersSummonPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseMissingDollarsPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseNotification.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBasePopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseResource.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseSelectableResource.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseSkipAviationFactoryPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseSkipBuildingPopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseState.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseStoragePopup.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/MilitaryBaseUtils.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/base/MilitaryBaseAerodrome.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/base/MilitaryBaseAviationFactory.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/base/MilitaryBaseHeadquarters.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/base/MilitaryBaseStorage.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/military_base/militaryBase.d.ts` | .claude/docs/military-base-architecture.md | client-analyst-military-base | 2026-10-22 |
| `src/views/home_screen/popups/profile/achievements/AchievementLine.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/AchievementRank.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/AchievementsListSection.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/AchievementsSection.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/achievement.d.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/achievements_type/AchievementsAirplanesHuntSection.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/achievements_type/AchievementsTanksHuntSection.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/achievements_type/AchievementsTypeSection.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/achievements/achievements_type/AchievemetType.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/codex/CodexAirplanesSection.ts` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/codex/CodexListSection.ts` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/codex/CodexSection.ts` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/codex/CodexTabSelector.ts` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/codex/CodexTanksSection.ts` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/CollectionSectionPopup.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/CollectionsListSection.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/CollectionsSection.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/CollectionsType.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection.d.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsExperimentalAirplanesSection.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsExperimentalTanksSection.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsTypeSection.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsUSSROperationsSection.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_type/Collection.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbum.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbumCard.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_type/collection_album.d.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/CollectionExperimentalTank.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/profile/collections/collection_type/collection_experimental_tanks/collection_experimental_tank.d.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/DonateSection.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/Offers.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/OffersSection.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/PaymentMethodsPopup.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/PaymentPopup.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/ShopPopup.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/offers/GoldenCoinsOfferPopup.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/shop/shop.d.ts` | shop-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/tank/TankGetPopup.ts` | hangar-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/train/TrainAutoSummonPopup.ts` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/train/TrainBuySchemesPopup.ts` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/train/TrainCollectionItemPopup.ts` | train-architecture.md | client-analyst-lead | 2026-10-23 |
| `src/views/home_screen/popups/train/TrainUpgradePopup.ts` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/home_screen/popups/train/train.d.ts` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/popups/AchievementCompletePopup.ts` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/popups/CollectionCompletePopup.ts` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/popups/ConfirmPopup.ts` | mailbox-architecture.md | client-analyst-mailbox | 2026-10-19 |
| `src/views/popups/TankInfoPopup.ts` | hangar-architecture.md | первичное заполнение | 2026-10-18 |
| `src/views/tutorial/Tutorial.ts` | tutorial-architecture.md | первичное заполнение | 2026-10-18 |
<!-- marks:end -->
