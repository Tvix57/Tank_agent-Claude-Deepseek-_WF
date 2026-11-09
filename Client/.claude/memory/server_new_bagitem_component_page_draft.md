---
name: server-new-bagitem-component-page-draft
description: "ЧЕРНОВИК — шаги для добавления на сервере (/workspace/server) нового наследника BagItem, нового <Name>UserComponent (наследника UserChildComponent) и Page для работы с ним. Не применено, требует практической проверки."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e3cf1d82-4d69-42eb-b774-0305e306cb00
  modified: 2026-09-16T08:30:11.461Z
---

# Статус: черновик, не проверен на практике

Реконструирован 2026-09-16 чтением реального кода сервера (не из "старых web
контекстов" — их не было в доступе), по образцу самой свежей триады
`CollectionItem` / `CollectionUserComponent` / `CollectionPage`
(`/workspace/server/game/src/main/java/com/linkedgames/game/model/collections/`,
`.../pages/ws/ingame/CollectionPage.java`). Прежде чем применять — свериться,
что эти файлы не изменились, и пройти шаги на реальном новом домене, отладив
по ходу.

**Не применять автоматически.** Если в разговоре всплывает задача "добавить
новый тип предмета в сумку" / "новый компонент пользователя" / "новую
ws-страницу" — сообщить пользователю, что есть этот черновик, и предложить
использовать/доработать его, а не проводить эту процедуру как готовую.

## 1. Новый наследник BagItem (`<Name>Item`)

Файл: `model/bag/<domain>/<Name>Item.java`

```java
public class <Name>Item extends BagItem {
    // доп. поля

    public static <Name>Item createNew(<Name>ItemData data, boolean isTemplate) {
        final <Name>Item item = new <Name>Item();
        if (isTemplate) item.setUid(BagItem.EMPTY_UID);
        item.setId(data.id);
        item.setCount(1);
        return item;
    }

    @Override public BagItem copy() { ... } // копировать доп. поля вручную
    @Override public JSONObject apiResponse() { ... } // super + свои поля
    @Override protected boolean isStackable() { return false; }
    @Override public ItemType getItemType() { return ItemType.<NAME>_ITEM; }
    @Override public void dbMappingBuild(Document document) { super...; }
    @Override public Document dbToData() { ... super...; }

    public static class DBFields { ... }
}
```

Обязательные доп. регистрации (без них — тихий провал без ошибок в консоли):

- **`model/item/ItemType.java`** — добавить константу `<NAME>_ITEM` в enum.
- **`model/item/ItemFactory.java`** — добавить
  `.put(ItemType.<NAME>_ITEM, <Name>Item::new)` в `itemFactory`. Без этого
  шага предмет, загружаемый из Mongo (`newFromDocument`), не создаётся —
  `factoryNewItem` вернёт `null` (что происходит дальше по цепочке — не
  проверено, вероятна NPE или тихая потеря предмета; проверить при отладке).
- **`model/bag/BagUserComponent.java`**, методы `add0()`/`onClean()` —
  ОПЦИОНАЛЬНО, только если нужны типизированные списки/мапы и геттеры вида
  `getCollectionItems()` (как для `Resource`/`Tank`/`Airplane`/
  `CollectionItem`). Без этого добавления предмет всё равно попадёт в общий
  `items`, просто не будет типизированного быстрого доступа.

## 2. Новый `<Name>UserComponent extends UserChildComponent`

Файл: `model/<domain>/<Name>UserComponent.java`

```java
public class <Name>UserComponent extends UserChildComponent implements APIResponseStd {
    public <Name>UserComponent(User user, String name) {
        super(user, name); // name = "<Name>" — см. КРИТИЧНО ниже
    }
    ...
    @Override public JSONObject apiResponse() { ... }
    @Override public void dbMappingBuild(Document document) { ... }
    public static class DBFields { ... }
}
```

Регистрация в `model/user/User.java`:

1. Приватное поле `private <Name>UserComponent <name>;`
2. Ленивый геттер:
   ```java
   public <Name>UserComponent get<Name>UserComponent() {
       if (<name> == null) {
           <name> = new <Name>UserComponent(this, "<Name>");
       }
       return <name>;
   }
   ```
3. Константа `DBFields.P_<NAME>_FIELD = "<Name>"` — **строка должна буквально
   совпадать** с componentName, переданным в конструктор компонента (шаг 2,
   `"<Name>"`).
4. В общем `dbMappingBuild(Document document)` User'а:
   ```java
   if (document.containsKey(DBFields.P_<NAME>_FIELD)) {
       get<Name>UserComponent().dbMappingBuild(document.get(DBFields.P_<NAME>_FIELD, Document.class));
   }
   ```

### КРИТИЧНО: механизм сохранения (`Component.java`)

`changedField(fieldName, value)`, вызванный внутри `<Name>UserComponent`,
всплывает к родителю с префиксом `dbSectionName() + "."` — а
`dbSectionName()` по умолчанию равен `componentName`, то есть той самой
строке `"<Name>"` из шага 2.1. Если эта строка не совпадает 1-в-1 с
`P_<NAME>_FIELD` в шаге 3 — данные будут **тихо писаться в Mongo под одним
ключом, а читаться при старте из другого** → после рестарта сервера
изменения бесследно пропадают, ошибок нет. Это прямой аналог гочи из
`config.yaml`/`{pathPart:0}` на клиенте — несовпадение имён без диагностики.

Также прямо в комментариях `Component.java`: **нельзя мешать `changedField`
и `changeThis` в одном компоненте** — либо одно, либо другое для всех полей
компонента, смешивание ломает обновления в Mongo.

Для простых полей, встроенных прямо в документ пользователя,
`changedField(...)` — это всё, что нужно; отдельного шага сохранения не
требуется, всплытие до User'а автоматическое через `FieldsChangerObserver`.

### Если у компонента отдельная Mongo-коллекция дочерних сущностей (со своим `uid`)

Нужно это ТОЛЬКО если, как `CollectionEntry`, дочерние записи хранятся
отдельными документами (не встроены в документ юзера) — тогда по образцу
`CollectionUserComponent`:

- Реализовать `dbFetchChanged()` / `commitDbUpdates()` /
  `dbMappingChildBuild(List<Document>)`.
- **Вручную прописать вызов `commitDbUpdates()`** в
  `model/user/tasks/ActorUpdateTask.java` (~строки 150-165), рядом с уже
  существующими `getBagComponent()` / `getAchievementsUserComponent()` /
  `getCodexUserComponent()` / `getCollectionUserComponent()`. **Без этого
  шага записи живут только в памяти текущей сессии и молча теряются при
  рестарте — никакой ошибки не будет.** Это самое незаметное место во всей
  процедуре, аналог "паковщик не подхватил config.yaml, ошибок нет".

## 3. Новая `<Name>Page extends AuthorizedUserPage`

Файл: `pages/ws/ingame/<Name>Page.java`

```java
public class <Name>Page extends AuthorizedUserPage {
    public <Name>Page() {
        addRoute("", this::actionIndex);
        addRoute("/someAction", this::actionSomeAction);
    }

    private void actionIndex(PageProcessor pageProcessor, User user) {
        pageProcessor.createResponse()
                .setPayload(user.get<Name>UserComponent().apiResponse())
                .ok()
                .sendReply();
    }
}
```

Регистрация в `pages/WSRouter.java`:
```java
addPageRoute("/ingame/<name>", new <Name>Page());
```
Без этого шага страница компилируется без ошибок, но полностью недостижима
с клиента — никакой ошибки на сервере, клиент просто не получит ответ по
этому пути.

## Частые причины "работает в памяти, но не сохраняется"/"недоступно с клиента" без ошибок

- Новый `ItemType` не добавлен в `ItemFactory` → предмет не десериализуется
  из БД при загрузке юзера.
- Имя компонента в конструкторе (`super(user, "<Name>")`) не совпадает с
  `DBFields.P_<NAME>_FIELD`, которым читают документ обратно.
- Компонент с отдельной Mongo-коллекцией не подключён в `ActorUpdateTask` →
  `commitDbUpdates()` никогда не вызывается → изменения теряются на
  рестарте.
- `<Name>Page` не зарегистрирована в `WSRouter.java` → маршрут недостижим.
- Смешаны `changedField` и `changeThis` в одном компоненте → обновления в
  Mongo ломаются (см. явное предупреждение в комментариях `Component.java`).

## Что осталось непроверенным (требует отладки при реальном применении)

- Поведение `factoryNewItem` при отсутствии записи в `ItemFactory` (`null`
  supplier) — куда дальше уходит `null` и не роняет ли что-то по цепочке.
- Нужно ли типизированный домен обязательно добавлять в
  `BagUserComponent.add0()/onClean()`, или можно ограничиться общим списком
  `items` — не проверялось на реальном новом домене, только прочитано по
  аналогии с существующими.
- Полный набор мест, где ещё вручную регистрируются per-domain вещи (по
  аналогии с client-паттерном `LoadAssetPackage.ts` — возможно на сервере
  есть свой список подобных "не синхронизируется само" мест, не найден в
  ходе этого чтения).
