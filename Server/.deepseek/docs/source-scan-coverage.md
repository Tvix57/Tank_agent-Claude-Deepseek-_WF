# Покрытие кода сканированием (сервер)

Владелец — `server-librarian-lead`. Файл показывает, какая доля файлов кода хотя бы раз прочитана
аналитиком при сканировании, и где лежат непрочитанные. По списку
[непросканированных](#unscanned) ищут код без ярко выраженных признаков отдельной области (нет своего
`*UserComponent`, см. `agent-system-workflow.md#area-sign`): сервисы, DAO, страницы, `commons`,
утилиты. Такой код не попадает ни в один документ сам по себе: аналитики областей читают его только
попутно. Клиентский аналог — `/workspace/client/.claude/docs/source-scan-coverage.md`.

**Файл кода** — `*/src/main/java/**/*.java` (модули `game` и `commons`).

**Отметка** — строка в [журнале отметок](#marks): файл прочитан целиком при сканировании области.
Отметки ставятся вручную, по полю `ПРОСКАНИРОВАНО` отправителя при регистрации документа
(`agent-system-workflow.md#scan-coverage`). Упоминание файла в документе отметкой не считается.
Исключение — разовые строки `первичное заполнение` (2026-10-18): файлы из раздела «Файлы прямого
влияния» карт файлов уже существующих `*-architecture.md`.

**Как обновлять** — только скриптом, руками не править генерируемые разделы:

```
python3 /workspace/server/.claude/scripts/scan_coverage.py /workspace/server --mark <пути> --by <агент> --doc <документ>
python3 /workspace/server/.claude/scripts/scan_coverage.py /workspace/server   # только пересчёт
```

`<пути>` — от корня репозитория, уникальный хвост пути (`model/bag/BagItem.java`) или папка. Скрипт
печатает итог; `НЕ РАСПОЗНАНО: …` — эти пути не отмечены, уточнить у отправителя. Отметки на
удалённые файлы скрипт выводит в [#stale-marks](#stale-marks) — удалить их строки из журнала и
пересчитать.

<!-- generated:start -->
## Итог {#total}

Пересчитано 2026-10-30: просканировано **191 из 476** файлов кода — **40.1%**.

## По папкам {#by-folder}

Сортировка — от наименее покрытых.

| Папка | Файлов | Просканировано | % |
|---|---|---|---|
| commons: (корень) | 8 | 0 | 0% |
| commons: actors | 3 | 0 | 0% |
| commons: actors/task | 19 | 0 | 0% |
| commons: annotations | 1 | 0 | 0% |
| commons: blocking | 2 | 0 | 0% |
| commons: comp | 6 | 0 | 0% |
| commons: emitter | 4 | 0 | 0% |
| commons: json | 5 | 0 | 0% |
| commons: reloading | 7 | 0 | 0% |
| commons: rnd | 3 | 0 | 0% |
| commons: server | 1 | 0 | 0% |
| commons: server/http | 8 | 0 | 0% |
| commons: server/ws | 20 | 0 | 0% |
| commons: store | 4 | 0 | 0% |
| commons: store/tech | 2 | 0 | 0% |
| commons: text | 4 | 0 | 0% |
| commons: utils | 4 | 0 | 0% |
| commons: utils/collections | 4 | 0 | 0% |
| commons: utils/enums | 1 | 0 | 0% |
| commons: utils/mongodb | 5 | 0 | 0% |
| commons: utils/resources | 2 | 0 | 0% |
| commons: validation | 3 | 0 | 0% |
| game: (корень) | 3 | 0 | 0% |
| game: balance | 4 | 0 | 0% |
| game: balance/data | 2 | 0 | 0% |
| game: model | 3 | 0 | 0% |
| game: model/admin | 6 | 0 | 0% |
| game: model/analytics | 6 | 0 | 0% |
| game: model/battlefield | 4 | 0 | 0% |
| game: model/clan | 15 | 0 | 0% |
| game: model/idle | 1 | 0 | 0% |
| game: model/messages | 2 | 0 | 0% |
| game: model/notifications | 2 | 0 | 0% |
| game: model/state | 1 | 0 | 0% |
| game: model/team | 2 | 0 | 0% |
| game: pages | 2 | 0 | 0% |
| game: pages/web | 9 | 0 | 0% |
| game: service | 1 | 0 | 0% |
| game: service/admin | 1 | 0 | 0% |
| game: service/analytics | 1 | 0 | 0% |
| game: service/battlefield | 4 | 0 | 0% |
| game: service/campaign | 5 | 0 | 0% |
| game: service/clan | 4 | 0 | 0% |
| game: service/drop | 2 | 0 | 0% |
| game: service/integration | 9 | 0 | 0% |
| game: service/mail | 1 | 0 | 0% |
| game: service/playerlist | 1 | 0 | 0% |
| game: service/rating | 6 | 0 | 0% |
| game: service/server | 2 | 0 | 0% |
| game: service/template | 3 | 0 | 0% |
| game: service/user | 5 | 0 | 0% |
| game: service/ws | 1 | 0 | 0% |
| game: utils/actor | 2 | 0 | 0% |
| game: utils/mongodb | 3 | 0 | 0% |
| game: utils/netty | 4 | 0 | 0% |
| game: utils | 7 | 1 | 14% |
| game: model/user | 18 | 4 | 22% |
| game: dao | 15 | 7 | 47% |
| game: pages/rest | 7 | 4 | 57% |
| game: pages/ws | 35 | 23 | 66% |
| game: scripts | 3 | 2 | 67% |
| game: model/bag | 24 | 17 | 71% |
| game: service/chat | 5 | 4 | 80% |
| game: model/achievements | 10 | 10 | 100% |
| game: model/aerodrome | 3 | 3 | 100% |
| game: model/assembly | 4 | 4 | 100% |
| game: model/ban | 5 | 5 | 100% |
| game: model/battle | 47 | 47 | 100% |
| game: model/campaign | 7 | 7 | 100% |
| game: model/codex | 6 | 6 | 100% |
| game: model/hangar | 1 | 1 | 100% |
| game: model/item | 4 | 4 | 100% |
| game: model/lootbox | 6 | 6 | 100% |
| game: model/mailbox | 3 | 3 | 100% |
| game: model/military_base | 13 | 13 | 100% |
| game: model/offers | 6 | 6 | 100% |
| game: model/payment | 2 | 2 | 100% |
| game: model/quests | 4 | 4 | 100% |
| game: model/summon | 1 | 1 | 100% |
| game: model/train | 3 | 3 | 100% |
| game: model/tutorial | 2 | 2 | 100% |
| game: service/battle | 1 | 1 | 100% |
| game: service/offers | 1 | 1 | 100% |

## Непросканированные файлы {#unscanned}

### commons: (корень) (8)

- `commons/src/main/java/com/linkedgames/commons/APICode.java`
- `commons/src/main/java/com/linkedgames/commons/APICodeException.java`
- `commons/src/main/java/com/linkedgames/commons/APICodeList.java`
- `commons/src/main/java/com/linkedgames/commons/APISection.java`
- `commons/src/main/java/com/linkedgames/commons/DesignException.java`
- `commons/src/main/java/com/linkedgames/commons/Environment.java`
- `commons/src/main/java/com/linkedgames/commons/IApp.java`
- `commons/src/main/java/com/linkedgames/commons/Reason.java`

### commons: actors (3)

- `commons/src/main/java/com/linkedgames/commons/actors/ActorComp.java`
- `commons/src/main/java/com/linkedgames/commons/actors/IActorCompPolicy.java`
- `commons/src/main/java/com/linkedgames/commons/actors/Message.java`

### commons: actors/task (19)

- `commons/src/main/java/com/linkedgames/commons/actors/task/ITaskBuilder.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/ImmutableStore.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/Task.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/TaskMailBox.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/TaskMailBoxOptions.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/TaskOrder.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/TaskProcessor.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/cb/IActionAddTask.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/cb/IActionRunnable.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/cb/IOnReceiveAnswer.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/cb/ITaskAdd.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/cb/ITaskReceiveFail.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/execute/ExecuteInside.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/execute/IActionCustomExecutableInside.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/execute/IActionExecutableInside.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/extend/IExecutableInsideHandler.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/extend/ITaskProcessorOwner.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/responses/TaskFailResponseMessage.java`
- `commons/src/main/java/com/linkedgames/commons/actors/task/responses/TaskResponseMessage.java`

### commons: annotations (1)

- `commons/src/main/java/com/linkedgames/commons/annotations/Nullable.java`

### commons: blocking (2)

- `commons/src/main/java/com/linkedgames/commons/blocking/AwaitableResult.java`
- `commons/src/main/java/com/linkedgames/commons/blocking/BlockingResult.java`

### commons: comp (6)

- `commons/src/main/java/com/linkedgames/commons/comp/APIResponseOpt.java`
- `commons/src/main/java/com/linkedgames/commons/comp/APIResponseStd.java`
- `commons/src/main/java/com/linkedgames/commons/comp/Component.java`
- `commons/src/main/java/com/linkedgames/commons/comp/FieldsChangerObserver.java`
- `commons/src/main/java/com/linkedgames/commons/comp/IComponentPolicy.java`
- `commons/src/main/java/com/linkedgames/commons/comp/IPersistentObject.java`

### commons: emitter (4)

- `commons/src/main/java/com/linkedgames/commons/emitter/EventEmitter.java`
- `commons/src/main/java/com/linkedgames/commons/emitter/IEmitterContext.java`
- `commons/src/main/java/com/linkedgames/commons/emitter/IEventEmitter.java`
- `commons/src/main/java/com/linkedgames/commons/emitter/IListener.java`

### commons: json (5)

- `commons/src/main/java/com/linkedgames/commons/json/JSONArray.java`
- `commons/src/main/java/com/linkedgames/commons/json/JSONException.java`
- `commons/src/main/java/com/linkedgames/commons/json/JSONObject.java`
- `commons/src/main/java/com/linkedgames/commons/json/JSONTokener.java`
- `commons/src/main/java/com/linkedgames/commons/json/JSONWriter.java`

### commons: reloading (7)

- `commons/src/main/java/com/linkedgames/commons/reloading/IChangeListener.java`
- `commons/src/main/java/com/linkedgames/commons/reloading/IDestroyListener.java`
- `commons/src/main/java/com/linkedgames/commons/reloading/IModificationWatcher.java`
- `commons/src/main/java/com/linkedgames/commons/reloading/IReloadingClassLoaderSupplier.java`
- `commons/src/main/java/com/linkedgames/commons/reloading/ModificationWatcher.java`
- `commons/src/main/java/com/linkedgames/commons/reloading/ReloadingClassLoader.java`
- `commons/src/main/java/com/linkedgames/commons/reloading/ReloadingMain.java`

### commons: rnd (3)

- `commons/src/main/java/com/linkedgames/commons/rnd/IRandom.java`
- `commons/src/main/java/com/linkedgames/commons/rnd/RandomJdk.java`
- `commons/src/main/java/com/linkedgames/commons/rnd/ThreadLocalSecureRandom.java`

### commons: server (1)

- `commons/src/main/java/com/linkedgames/commons/server/RouterComponent.java`

### commons: server/http (8)

- `commons/src/main/java/com/linkedgames/commons/server/http/HttpContentType.java`
- `commons/src/main/java/com/linkedgames/commons/server/http/HttpPageProcessor.java`
- `commons/src/main/java/com/linkedgames/commons/server/http/IHttpSession.java`
- `commons/src/main/java/com/linkedgames/commons/server/http/pages/HttpPage.java`
- `commons/src/main/java/com/linkedgames/commons/server/http/pages/HttpRouter.java`
- `commons/src/main/java/com/linkedgames/commons/server/http/pages/HttpRouterAction.java`
- `commons/src/main/java/com/linkedgames/commons/server/http/pages/IHttpRouteArg.java`
- `commons/src/main/java/com/linkedgames/commons/server/http/pages/IHttpRouteSimple.java`

### commons: server/ws (20)

- `commons/src/main/java/com/linkedgames/commons/server/ws/ISession.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/JsonPacket.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/JsonPacketEncoder.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/JsonPacketFactory.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/catalog/AdvancedCatalogPolicy.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/catalog/AdvancedSessionCatalog.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/catalog/CatalogPolicy.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/catalog/ICatalogEncodedMessage.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/catalog/ICatalogMessage.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/catalog/SessionBox.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/catalog/SessionCatalog.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/IRouteArg.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/IRouteSimple.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/Page.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/PageProcessor.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/Router.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/RouterAction.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/UPageRequestId.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/impl/DefaultPageProcessor.java`
- `commons/src/main/java/com/linkedgames/commons/server/ws/pages/impl/PlainPageProcessor.java`

### commons: store (4)

- `commons/src/main/java/com/linkedgames/commons/store/ObjectStore.java`
- `commons/src/main/java/com/linkedgames/commons/store/ObjectStoreSettings.java`
- `commons/src/main/java/com/linkedgames/commons/store/RejectReason.java`
- `commons/src/main/java/com/linkedgames/commons/store/ShutdownShardsTask.java`

### commons: store/tech (2)

- `commons/src/main/java/com/linkedgames/commons/store/tech/ITechnicalMessage.java`
- `commons/src/main/java/com/linkedgames/commons/store/tech/TechnicalShutdownFields.java`

### commons: text (4)

- `commons/src/main/java/com/linkedgames/commons/text/Alphabets.java`
- `commons/src/main/java/com/linkedgames/commons/text/MD5.java`
- `commons/src/main/java/com/linkedgames/commons/text/Profanity.java`
- `commons/src/main/java/com/linkedgames/commons/text/StringUtils.java`

### commons: utils (4)

- `commons/src/main/java/com/linkedgames/commons/utils/DateUtil.java`
- `commons/src/main/java/com/linkedgames/commons/utils/ExceptionUtils.java`
- `commons/src/main/java/com/linkedgames/commons/utils/HttpRequest.java`
- `commons/src/main/java/com/linkedgames/commons/utils/Sleeper.java`

### commons: utils/collections (4)

- `commons/src/main/java/com/linkedgames/commons/utils/collections/ImmutableMixedMap.java`
- `commons/src/main/java/com/linkedgames/commons/utils/collections/MixedMap.java`
- `commons/src/main/java/com/linkedgames/commons/utils/collections/typed/ImmutableMixedStringMap.java`
- `commons/src/main/java/com/linkedgames/commons/utils/collections/typed/MixedStringMap.java`

### commons: utils/enums (1)

- `commons/src/main/java/com/linkedgames/commons/utils/enums/EnumValues.java`

### commons: utils/mongodb (5)

- `commons/src/main/java/com/linkedgames/commons/utils/mongodb/AwaitableSubscriber.java`
- `commons/src/main/java/com/linkedgames/commons/utils/mongodb/FieldUpdater.java`
- `commons/src/main/java/com/linkedgames/commons/utils/mongodb/MultiResultSubscriber.java`
- `commons/src/main/java/com/linkedgames/commons/utils/mongodb/NoJobSubscriber.java`
- `commons/src/main/java/com/linkedgames/commons/utils/mongodb/SingleResultSubscriber.java`

### commons: utils/resources (2)

- `commons/src/main/java/com/linkedgames/commons/utils/resources/Resource.java`
- `commons/src/main/java/com/linkedgames/commons/utils/resources/ResourceFolderScanner.java`

### commons: validation (3)

- `commons/src/main/java/com/linkedgames/commons/validation/IRule.java`
- `commons/src/main/java/com/linkedgames/commons/validation/Rules.java`
- `commons/src/main/java/com/linkedgames/commons/validation/Validation.java`

### game: (корень) (3)

- `game/src/main/java/com/linkedgames/game/APICodeList.java`
- `game/src/main/java/com/linkedgames/game/Globals.java`
- `game/src/main/java/com/linkedgames/game/Main.java`

### game: balance (4)

- `game/src/main/java/com/linkedgames/game/balance/Balance.java`
- `game/src/main/java/com/linkedgames/game/balance/BalanceAggregator.java`
- `game/src/main/java/com/linkedgames/game/balance/BalanceImporter.java`
- `game/src/main/java/com/linkedgames/game/balance/KeyModel.java`

### game: balance/data (2)

- `game/src/main/java/com/linkedgames/game/balance/data/IdIntValueData.java`
- `game/src/main/java/com/linkedgames/game/balance/data/PercentValueData.java`

### game: model (3)

- `game/src/main/java/com/linkedgames/game/model/Country.java`
- `game/src/main/java/com/linkedgames/game/model/Rank.java`
- `game/src/main/java/com/linkedgames/game/model/Stars.java`

### game: model/admin (6)

- `game/src/main/java/com/linkedgames/game/model/admin/AdminRole.java`
- `game/src/main/java/com/linkedgames/game/model/admin/AdminTemplateModel.java`
- `game/src/main/java/com/linkedgames/game/model/admin/AdminUser.java`
- `game/src/main/java/com/linkedgames/game/model/admin/db/DBFieldModel.java`
- `game/src/main/java/com/linkedgames/game/model/admin/paginator/Paginator.java`
- `game/src/main/java/com/linkedgames/game/model/admin/table/SimpleTable.java`

### game: model/analytics (6)

- `game/src/main/java/com/linkedgames/game/model/analytics/Analytics.java`
- `game/src/main/java/com/linkedgames/game/model/analytics/AnalyticsSubjectId.java`
- `game/src/main/java/com/linkedgames/game/model/analytics/AnalyticsType.java`
- `game/src/main/java/com/linkedgames/game/model/analytics/WriteType.java`
- `game/src/main/java/com/linkedgames/game/model/analytics/impl/GoldenCoinsAnalytics.java`
- `game/src/main/java/com/linkedgames/game/model/analytics/impl/OfferAnalytics.java`

### game: model/battlefield (4)

- `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldBattle.java`
- `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldFighter.java`
- `game/src/main/java/com/linkedgames/game/model/battlefield/BattlefieldUserComponent.java`
- `game/src/main/java/com/linkedgames/game/model/battlefield/actions/ActionSlot.java`

### game: model/clan (15)

- `game/src/main/java/com/linkedgames/game/model/clan/Clan.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanActor.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanActorPolicy.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanDataAggregator.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanInvite.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanMessage.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanSignature.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanUser.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanUserComponent.java`
- `game/src/main/java/com/linkedgames/game/model/clan/ClanUserRole.java`
- `game/src/main/java/com/linkedgames/game/model/clan/CreationClanData.java`
- `game/src/main/java/com/linkedgames/game/model/clan/tasks/ActorInitializationTask.java`
- `game/src/main/java/com/linkedgames/game/model/clan/tasks/ActorShutdownTask.java`
- `game/src/main/java/com/linkedgames/game/model/clan/tasks/ActorUpdateTask.java`
- `game/src/main/java/com/linkedgames/game/model/clan/tasks/AnswerWithId.java`

### game: model/idle (1)

- `game/src/main/java/com/linkedgames/game/model/idle/IdleUserComponent.java`

### game: model/messages (2)

- `game/src/main/java/com/linkedgames/game/model/messages/MessageEncoder.java`
- `game/src/main/java/com/linkedgames/game/model/messages/Messengers.java`

### game: model/notifications (2)

- `game/src/main/java/com/linkedgames/game/model/notifications/NotificationId.java`
- `game/src/main/java/com/linkedgames/game/model/notifications/NotificationUserComponent.java`

### game: model/state (1)

- `game/src/main/java/com/linkedgames/game/model/state/StateUserComponent.java`

### game: model/team (2)

- `game/src/main/java/com/linkedgames/game/model/team/Team.java`
- `game/src/main/java/com/linkedgames/game/model/team/TeamMembers.java`

### game: pages (2)

- `game/src/main/java/com/linkedgames/game/pages/HTTPRouter.java`
- `game/src/main/java/com/linkedgames/game/pages/WSRouter.java`

### game: pages/web (9)

- `game/src/main/java/com/linkedgames/game/pages/web/WebPage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/AdminCodePage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/AdminListPage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/AdminMainPage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/AdminUserAnalyticsPage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/AdminUserInfoPage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/SetCookiePage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/extend/AbstractAdminPage.java`
- `game/src/main/java/com/linkedgames/game/pages/web/admin/extend/AuthorizedAdminPage.java`

### game: service (1)

- `game/src/main/java/com/linkedgames/game/service/GlobalTasks.java`

### game: service/admin (1)

- `game/src/main/java/com/linkedgames/game/service/admin/AdminService.java`

### game: service/analytics (1)

- `game/src/main/java/com/linkedgames/game/service/analytics/GameAnalytics.java`

### game: service/battlefield (4)

- `game/src/main/java/com/linkedgames/game/service/battlefield/BattlefieldActor.java`
- `game/src/main/java/com/linkedgames/game/service/battlefield/BattlefieldService.java`
- `game/src/main/java/com/linkedgames/game/service/battlefield/battle/League.java`
- `game/src/main/java/com/linkedgames/game/service/battlefield/battle/Participant.java`

### game: service/campaign (5)

- `game/src/main/java/com/linkedgames/game/service/campaign/LeagueMeta.java`
- `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeActor.java`
- `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeBattleContext.java`
- `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeEntry.java`
- `game/src/main/java/com/linkedgames/game/service/campaign/RankedChallengeService.java`

### game: service/clan (4)

- `game/src/main/java/com/linkedgames/game/service/clan/ClanChatService.java`
- `game/src/main/java/com/linkedgames/game/service/clan/ClanNameService.java`
- `game/src/main/java/com/linkedgames/game/service/clan/ClanService.java`
- `game/src/main/java/com/linkedgames/game/service/clan/ClanStore.java`

### game: service/drop (2)

- `game/src/main/java/com/linkedgames/game/service/drop/DropUtils.java`
- `game/src/main/java/com/linkedgames/game/service/drop/DroppedItem.java`

### game: service/integration (9)

- `game/src/main/java/com/linkedgames/game/service/integration/Currency.java`
- `game/src/main/java/com/linkedgames/game/service/integration/IntegrationUtil.java`
- `game/src/main/java/com/linkedgames/game/service/integration/Region.java`
- `game/src/main/java/com/linkedgames/game/service/integration/SocialPortal.java`
- `game/src/main/java/com/linkedgames/game/service/integration/UserCreationOptions.java`
- `game/src/main/java/com/linkedgames/game/service/integration/odnoklassniki/OdnoklassnikiUtil.java`
- `game/src/main/java/com/linkedgames/game/service/integration/overmobile/OvermobileService.java`
- `game/src/main/java/com/linkedgames/game/service/integration/vk/VKUtil.java`
- `game/src/main/java/com/linkedgames/game/service/integration/yookassa/YookassaUtil.java`

### game: service/mail (1)

- `game/src/main/java/com/linkedgames/game/service/mail/MailService.java`

### game: service/playerlist (1)

- `game/src/main/java/com/linkedgames/game/service/playerlist/PlayerListService.java`

### game: service/rating (6)

- `game/src/main/java/com/linkedgames/game/service/rating/RatingAirplanesService.java`
- `game/src/main/java/com/linkedgames/game/service/rating/RatingBattlefieldService.java`
- `game/src/main/java/com/linkedgames/game/service/rating/RatingCampaignService.java`
- `game/src/main/java/com/linkedgames/game/service/rating/RatingClanService.java`
- `game/src/main/java/com/linkedgames/game/service/rating/RatingPowerService.java`
- `game/src/main/java/com/linkedgames/game/service/rating/RatingTanksService.java`

### game: service/server (2)

- `game/src/main/java/com/linkedgames/game/service/server/ServerInfo.java`
- `game/src/main/java/com/linkedgames/game/service/server/ServerNotification.java`

### game: service/template (3)

- `game/src/main/java/com/linkedgames/game/service/template/TemplateManager.java`
- `game/src/main/java/com/linkedgames/game/service/template/TemplateModel.java`
- `game/src/main/java/com/linkedgames/game/service/template/TemplateURLBuilder.java`

### game: service/user (5)

- `game/src/main/java/com/linkedgames/game/service/user/PasswordTokenService.java`
- `game/src/main/java/com/linkedgames/game/service/user/UserNameService.java`
- `game/src/main/java/com/linkedgames/game/service/user/UserPasswordService.java`
- `game/src/main/java/com/linkedgames/game/service/user/UserService.java`
- `game/src/main/java/com/linkedgames/game/service/user/UserStore.java`

### game: service/ws (1)

- `game/src/main/java/com/linkedgames/game/service/ws/WSStore.java`

### game: utils/actor (2)

- `game/src/main/java/com/linkedgames/game/utils/actor/ActorAwaitMessage.java`
- `game/src/main/java/com/linkedgames/game/utils/actor/ActorUtils.java`

### game: utils/mongodb (3)

- `game/src/main/java/com/linkedgames/game/utils/mongodb/Migration.java`
- `game/src/main/java/com/linkedgames/game/utils/mongodb/MongoDB.java`
- `game/src/main/java/com/linkedgames/game/utils/mongodb/UpdateUtils.java`

### game: utils/netty (4)

- `game/src/main/java/com/linkedgames/game/utils/netty/FileReturner.java`
- `game/src/main/java/com/linkedgames/game/utils/netty/HttpHandler.java`
- `game/src/main/java/com/linkedgames/game/utils/netty/ServerInitializer.java`
- `game/src/main/java/com/linkedgames/game/utils/netty/WebsocketHandler.java`

### game: utils (6)

- `game/src/main/java/com/linkedgames/game/utils/FieldHint.java`
- `game/src/main/java/com/linkedgames/game/utils/Futures.java`
- `game/src/main/java/com/linkedgames/game/utils/HttpAsyncRequest.java`
- `game/src/main/java/com/linkedgames/game/utils/ReloadingClassLoader.java`
- `game/src/main/java/com/linkedgames/game/utils/TextUtils.java`
- `game/src/main/java/com/linkedgames/game/utils/UpgradableValue.java`

### game: model/user (14)

- `game/src/main/java/com/linkedgames/game/model/user/PasswordData.java`
- `game/src/main/java/com/linkedgames/game/model/user/RegData.java`
- `game/src/main/java/com/linkedgames/game/model/user/RouterUserComponent.java`
- `game/src/main/java/com/linkedgames/game/model/user/Sex.java`
- `game/src/main/java/com/linkedgames/game/model/user/User.java`
- `game/src/main/java/com/linkedgames/game/model/user/UserActor.java`
- `game/src/main/java/com/linkedgames/game/model/user/UserActorPolicy.java`
- `game/src/main/java/com/linkedgames/game/model/user/UserEmitterId.java`
- `game/src/main/java/com/linkedgames/game/model/user/data/UserLevelData.java`
- `game/src/main/java/com/linkedgames/game/model/user/events/SEvent.java`
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorInitializationTask.java`
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorShutdownTask.java`
- `game/src/main/java/com/linkedgames/game/model/user/tasks/ActorUpdateTask.java`
- `game/src/main/java/com/linkedgames/game/model/user/tasks/UserSignatureCollectorTask.java`

### game: dao (8)

- `game/src/main/java/com/linkedgames/game/dao/AdminDao.java`
- `game/src/main/java/com/linkedgames/game/dao/BattlefieldDao.java`
- `game/src/main/java/com/linkedgames/game/dao/ClanDao.java`
- `game/src/main/java/com/linkedgames/game/dao/CountersDao.java`
- `game/src/main/java/com/linkedgames/game/dao/GameAnalyticsDao.java`
- `game/src/main/java/com/linkedgames/game/dao/RankedChallengeDao.java`
- `game/src/main/java/com/linkedgames/game/dao/RankedChallengeHistoryDao.java`
- `game/src/main/java/com/linkedgames/game/dao/UserDao.java`

### game: pages/rest (3)

- `game/src/main/java/com/linkedgames/game/pages/rest/pblc/OnlineCounterPage.java`
- `game/src/main/java/com/linkedgames/game/pages/rest/pblc/PublicPage.java`
- `game/src/main/java/com/linkedgames/game/pages/rest/pblc/TestPage.java`

### game: pages/ws (12)

- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BattlefieldPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/ClanChatPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/ClanPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/PlayerListPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/ProfilePage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/RatingPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/SettingsPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/StatePage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/dev/DevToolsPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/pblc/GatewayPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/pblc/PublicPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/pblc/ServerInfoPage.java`

### game: scripts (1)

- `game/src/main/java/com/linkedgames/game/scripts/AbstractScript.java`

### game: model/bag (7)

- `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneArmorType.java`
- `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneBombType.java`
- `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneGunType.java`
- `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneType.java`
- `game/src/main/java/com/linkedgames/game/model/bag/tank/TankAmmoType.java`
- `game/src/main/java/com/linkedgames/game/model/bag/tank/TankArmorType.java`
- `game/src/main/java/com/linkedgames/game/model/bag/tank/TankType.java`

### game: service/chat (1)

- `game/src/main/java/com/linkedgames/game/service/chat/ChatLanguage.java`

## Отметки на несуществующие файлы {#stale-marks}

- `game/src/main/java/com/linkedgames/game/dao/CollectionDao.java`
- `game/src/main/java/com/linkedgames/game/model/collections/CollectionUserComponent.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionList/Collection.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionAlbum.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionExperimentalTank.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionAlbumEntry.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionEntry.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionExperimentalTankEntry.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionItemEntry/CollectionItemEntry.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/AlbumsSectionEntry.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/CollectionSectionEntry.java`
- `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/ExperimentalTanksSectionEntry.java`
- `game/src/main/java/com/linkedgames/game/model/collections/data/CollectionItemData.java`
- `game/src/main/java/com/linkedgames/game/model/collections/data/CollectionsData.java`
- `game/src/main/java/com/linkedgames/game/model/collections/enums/CollectionSection.java`
- `game/src/main/java/com/linkedgames/game/model/collections/itemList/CollectionItem.java`
- `game/src/main/java/com/linkedgames/game/model/collections/sectionList/AlbumsSectionType.java`
- `game/src/main/java/com/linkedgames/game/model/collections/sectionList/CollectionSectionType.java`
- `game/src/main/java/com/linkedgames/game/model/collections/sectionList/ExperimentalTanksSectionType.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionAlbumPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionExperimentalTankPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionPage.java`
- `game/src/main/java/com/linkedgames/game/pages/ws/ingame/YandexPage.java`
- `game/src/main/java/com/linkedgames/game/service/integration/yandex/ShortcutRewardStatus.java`
- `game/src/main/java/com/linkedgames/game/service/integration/yandex/YandexUserComponent.java`
<!-- generated:end -->

## История замеров {#history}

<!-- history:start -->
- 2026-10-18 — 42.7% (186/436)
- 2026-10-19 — 38.6% (186/482)
- 2026-10-22 — 42.1% (203/482)
- 2026-10-26 — 40.1% (185/461)
- 2026-10-27 — 38.2% (182/476)
- 2026-10-28 — 40.1% (191/476)
- 2026-10-30 — 40.1% (191/476)
<!-- history:end -->

## Журнал отметок {#marks}

<!-- marks:start -->
| Файл | Документ | Кто отметил | Дата |
|---|---|---|---|
| `game/src/main/java/com/linkedgames/game/dao/AchievementsDao.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/dao/BagDao.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/dao/BanPanelDao.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/dao/ChatDao.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/dao/CodexDao.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/dao/CollectionDao.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/dao/MailboxDao.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/dao/PaymentDao.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/Achievement.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/AchievementData.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/AchievementEntry.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/AchievementFactory.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/AchievementUserComponent.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/IAchievementContext.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/enums/AchievementRank.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/enums/AchievementType.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyAirplaneAchievement.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/achievements/list/DestroyTankAchievement.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/AerodromeUserComponent.java` | aerodrome-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/data/AerodromeBuySchemesData.java` | aerodrome-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/aerodrome/data/AerodromeSummonData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/assembly/AssemblyUserComponent.java` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblyNeedSchemePartsData.java` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblySchemeParts.java` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/assembly/data/AssemblySchemePartsType.java` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/BagItem.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/BagUserComponent.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/Airplane.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneParams.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/AirplaneUtils.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/airplane/data/AirplaneData.java` | tank-airplane-data-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/lootbox/Lootbox.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-28 |
| `game/src/main/java/com/linkedgames/game/model/bag/military_base/MilitaryBaseAviationFactorySlot.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/bag/military_base/MilitaryBaseBoost.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/bag/military_base/MilitaryBaseBuilding.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/bag/resource/Resource.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/Tank.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankParams.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/TankUtils.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/tank/data/TankData.java` | tank-airplane-data-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/utils/ItemAddInfo.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/bag/utils/ItemEmitInfo.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/ban/BanActions.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/ban/BanCancelInfo.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/ban/BanGeneralInfo.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/ban/BanHistoryEntry.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/ban/BanType.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/Battle.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleActor.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleActorPolicy.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleBalance.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleLocation.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleRandom.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleType.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleUnit.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/BattleUserComponent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/Fighter.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionChangeOpponent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionDodge.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionInfo.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/actions/ActionSubscribe.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/actions/IAction.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleAirplaneData.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleData.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleDataFactory.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleFighterData.java` | battle-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/battle/data/BattleTankData.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/BattlePlaceEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/BattleResultEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/ChangeOpponentEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/DodgeEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/ForceEndEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/NewOpponentEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/SlotResultEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneAttackEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneDestroyedEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplanePrepareTakeoffEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneRechargeEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneReplacedEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneSpawnEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneTakeDamageEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/airplane/AirplaneTakeoffEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankAttackEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankDestroyedEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankRechargeEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankReplacedEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankSpawnEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/events/tank/TankTakeDamageEvent.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/recharge/AirplaneRecharge.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/recharge/RechargeMode.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/recharge/TankRecharge.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitAirplane.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/battle/units/UnitTank.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignBattle.java` | campaign-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignBattleResult.java` | campaign-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignFighter.java` | campaign-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/campaign/CampaignUserComponent.java` | airdrop-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropBox.java` | airdrop-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropBoxType.java` | airdrop-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/campaign/data/AirDropData.java` | airdrop-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/codex/CodexEntry.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/codex/CodexEntryFactory.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/codex/CodexEntryType.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/codex/CodexUserComponent.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/codex/entries/CodexAirplaneEntry.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/codex/entries/CodexTankEntry.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/CollectionUserComponent.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionList/Collection.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionAlbum.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionList/CollectionExperimentalTank.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionAlbumEntry.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionEntry.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionEntry/CollectionExperimentalTankEntry.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/collectionItemEntry/CollectionItemEntry.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/AlbumsSectionEntry.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/CollectionSectionEntry.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/collectionsEntry/sectionEntry/ExperimentalTanksSectionEntry.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/data/CollectionItemData.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/data/CollectionsData.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/enums/CollectionSection.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/itemList/CollectionItem.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/AlbumsSectionType.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/CollectionSectionType.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/collections/sectionList/ExperimentalTanksSectionType.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/hangar/HangarUserComponent.java` | hangar-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/item/Item.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/item/ItemFactory.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/item/ItemId.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/item/ItemType.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/lootbox/LootboxSlot.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-30 |
| `game/src/main/java/com/linkedgames/game/model/lootbox/LootboxUserComponent.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-30 |
| `game/src/main/java/com/linkedgames/game/model/lootbox/data/LootboxData.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-28 |
| `game/src/main/java/com/linkedgames/game/model/lootbox/data/LootboxQualityData.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-28 |
| `game/src/main/java/com/linkedgames/game/model/lootbox/data/LootboxResourceReward.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-28 |
| `game/src/main/java/com/linkedgames/game/model/lootbox/data/LootboxReward.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-28 |
| `game/src/main/java/com/linkedgames/game/model/mailbox/MailboxDialog.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/mailbox/MailboxMessage.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/mailbox/MailboxUserComponent.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseAviationFactory.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseBuildingCapacity.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseBuildingRate.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseHeadquarters.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseStorage.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/MilitaryBaseUserComponent.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/BoostRouter.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/BoostSummonData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/MilitaryBaseAviationFactoryData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/MilitaryBaseBoostData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/MilitaryBaseBuildingData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/MilitaryBaseData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/military_base/data/MilitaryBaseStorageData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/offers/OfferId.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/offers/OfferRewardData.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/offers/OffersUserComponent.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/offers/ProcessPaymentResult.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/offers/list/GoldenCoinsOffer.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/offers/types/Offer.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/payment/PaymentProcessor.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/payment/PaymentRequest.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestEvent.java` | quests-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/quests/QuestsUserComponent.java` | quests-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/quests/data/QuestData.java` | quests-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/quests/data/QuestRewardData.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-28 |
| `game/src/main/java/com/linkedgames/game/model/summon/data/SummonUpgradeData.java` | train-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/train/TrainUserComponent.java` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/train/data/TrainBuySchemesData.java` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/train/data/TrainSummonData.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/model/tutorial/TutorialUserComponent.java` | tutorial-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/tutorial/data/TutorialData.java` | tutorial-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/user/UserChildComponent.java` | platform-sdk-architecture.md | server-analyst-platform-sdk | 2026-10-26 |
| `game/src/main/java/com/linkedgames/game/model/user/UserGameVersion.java` | tutorial-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/model/user/UserRights.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/model/user/UserSignature.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/rest/pblc/OdnoklassnikiPaymentPage.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/rest/pblc/PaymentPage.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/rest/pblc/VKPaymentPage.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/rest/pblc/YookassaPaymentPage.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AccountPage.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AchievementsPage.java` | achievements-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AerodromePage.java` | aerodrome-architecture.md | server-analyst-lead | 2026-10-19 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AssemblyPage.java` | assembly-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/AuthorizedUserPage.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BagPage.java` | bag-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BanPanelPage.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/BattlePage.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CampaignPage.java` | airdrop-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/ChatPage.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CodexPage.java` | codex-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionAlbumPage.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionExperimentalTankPage.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/CollectionPage.java` | collections-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/HomePage.java` | hangar-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/LootboxPage.java` | lootbox-architecture.md | server-analyst-lootbox | 2026-10-30 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/MilitaryBasePage.java` | military-base-architecture.md | server-analyst-lead | 2026-10-22 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/ModeratorsChatPage.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/ShopPage.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/TrainPage.java` | train-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/YandexPage.java` | platform-sdk-architecture.md | server-analyst-platform-sdk | 2026-10-26 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/mailbox/BlacklistPage.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/mailbox/DialogsPage.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/mailbox/FriendsPage.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/mailbox/MailboxPage.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/mailbox/MessagesPage.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/pages/ws/ingame/mailbox/RewardsPage.java` | mailbox-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/scripts/CleanupAerodrome.java` | aerodrome-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/scripts/UserResetQuests.java` | quests-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/service/battle/BattleStore.java` | battle-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/service/chat/ChatMessage.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/service/chat/ChatService.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/service/chat/ModeratorsChatMessage.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/service/chat/ModeratorsChatService.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/service/integration/yandex/ShortcutRewardStatus.java` | platform-sdk-architecture.md | server-analyst-platform-sdk | 2026-10-26 |
| `game/src/main/java/com/linkedgames/game/service/integration/yandex/YandexUserComponent.java` | platform-sdk-architecture.md | server-analyst-platform-sdk | 2026-10-26 |
| `game/src/main/java/com/linkedgames/game/service/offers/OffersService.java` | offers-architecture.md | первичное заполнение | 2026-10-18 |
| `game/src/main/java/com/linkedgames/game/utils/Names.java` | ban-architecture.md | server-analyst-lead | 2026-10-18 |
<!-- marks:end -->
