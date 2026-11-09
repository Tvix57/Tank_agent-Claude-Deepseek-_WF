# Подписка на серверные push-события (не request/response)

Три подхода к обработке событий, которые сервер инициирует асинхронно (`/events/X/Y`), в отличие от
классических `request/response`-маршрутов.

**Содержание:** [Маппинг пути](#mapping) · [1. GameEvents — рекомендуемый](#approach-1) ·
[2. State.onRegisterEvents](#approach-2) · [3. Прямая подписка](#approach-3) ·
[Правило отписки](#unsubscribe)

## Маппинг серверного пути → локальное событие {#mapping}

`src/plain/globals/WSSocket.ts`, обработчик `g/ws/onmessage` (~строки 99-104): любое входящее
сообщение с `json.type.substring(0, 7) == "/events"` эмитится как
`App.events.emit("g/ws" + json.type, json.payload)`.

Правило детерминировано: серверный путь `/events/X/Y` → локальное событие `"g/ws/events/X/Y"`.

## Подход 1: централизованный типизированный слой (канонический для проекта) {#approach-1}

**Файл:** `src/plain/GameEvents.ts`, вход — `GameEvents.listenServerEvents()` (вызывается один раз из
`Globals.ts`).

1. В `listenServerEvents()` хендлеры регистрируются на сырые события `App.events.on("g/ws/events/<путь>", handler)`.
2. Хендлер сразу переизлучает данные типизированным локальным событием через `GameEvents.emitter`:
   ```typescript
   App.events.on("g/ws/events/collections/setCompleted", (data) => {
       GameEvents.emitter.emit(GameEvents.COLLECTION_SET_COMPLETED, data);
   });
   ```
3. Компоненты/экраны подписываются на `GameEvents.emitter` в `onCreate` и отписываются в `onDestroy`:
   ```typescript
   GameEvents.emitter.on(GameEvents.COLLECTION_SET_COMPLETED, this.onCollectionSetCompleted, this);
   ```

Преимущества: типизированные имена событий вместо "волшебных строк" путей, единая точка регистрации
всех push-обработчиков, разделение ответственности (`GameEvents` — синхронизация с сервером,
компоненты — локальная логика).

Примечание: `EventName<T>` у части событий объявлен как `EventName<never>` (единообразно с
`ACHIEVEMENTS_EVENT`; `TUTORIAL_EVENT` удалён при merge `amnesia/fix`) — payload при этом реально передаётся, но его форма
зафиксирована только в подписчике, не в типе события.

**Примеры в коде:** `HomeScreen`, `UserBag`, хедер-бары (`HeaderAchievementsBar` и др.).

**Пример: события-триггеры перезапроса (коллекции).** Push несёт только id; хендлер эмитит id, а подписчик
сам перезапрашивает данные у сервера (источник истины — сервер, локальных патчей нет):
```typescript
App.events.on("g/ws/events/collections/collectionUpdated", (data: CollectionUpdatedJSON) => {
    GameEvents.emitter.emit(GameEvents.COLLECTION_UPDATED, data.collectionId);
});
```
Три события коллекций (`collectionUpdated`, `sectionUpdated`, `sectionRestarted`) и их подписчики —
`.claude/docs/collections-architecture.md#cls-gameevents`. Клиент эти события после своих запросов не эмитит:
эмит только из `listenServerEvents()`. Ограничения: push приходит раньше ответа на запрос, порядок push между
собой не гарантирован (`collections-architecture.md#s8`, п.15).

## Подход 2: хук `onRegisterEvents()` у наследников `State` {#approach-2}

`src/ee/plain/State.ts` — `protected onRegisterEvents()` (пустая реализация, переопределяется в
наследниках; вызывается из инициализации `State`). Компонент сам регистрирует свои обработчики на
`App.events`.

- Мотивация — инкапсуляция: логика обработки события живёт рядом с логикой компонента.
- Менее типизирован, чем подход 1 (в коде остаются строки путей).
- В проекте используется в основном для внутреннего состояния, а не для push-событий сервера.
- Уместен, когда событие специфично для одного компонента.

## Подход 3: прямая подписка компонента на сырое событие {#approach-3}

```typescript
this.someLayout.on("g/ws/events/some/path", (payload) => { /* обработка */ });
```

Минусы: нет типизации (ошибка в строке пути всплывёт только в runtime), регистрация обработчиков
рассеяна по коду. **Не рекомендуется** — предпочитать подход 1 или 2.

## Правило отписки {#unsubscribe}

Любая подписка на `App.events`/`GameEvents.emitter` обязана иметь явную отписку в `onDestroy`
компонента — иначе утечка при повторных открытиях экранов/попапов:

```typescript
onCreate()  { GameEvents.emitter.on(GameEvents.SOME_EVENT, this.onEvent, this); }
onDestroy() { GameEvents.emitter.off(GameEvents.SOME_EVENT, this.onEvent, this); }
```
