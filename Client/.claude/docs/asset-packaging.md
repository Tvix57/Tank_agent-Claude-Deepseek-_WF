# Client — паковка ассетов (Asset Packer) — атласы и raw-картинки

Первоисточник по добавлению новых ассетов на клиенте (`CLAUDE.md` содержит только указатель сюда).

**Содержание:** [Async per-id атлас](#async-atlas) · [Обычный атлас](#regular-atlas) ·
[Частые причины "картинка не показалась"](#troubleshooting)

Паковщик — внешний Java-инструмент (`tools/AssetPacker.sh` / `tools/src/Asset-Packer.jar`). Он
ничего не пакует по факту наличия файлов в `assets-src/` — нужна явная запись в
`tools/src/config.yaml`. Без неё `Creator.spriteAsync(...)` будет вечно грузить (или тихо ничего не
показывать) без единой ошибки в консоли, а `Creator.sprite(...)` просто не найдёт текстуру.

Способ консьюминга пакета выбирается ДО правки `config.yaml`:

- **Async per-id пакет** ([раздел 1](#async-atlas), `Creator.spriteAsync`) — каждый id (танк,
  предмет коллекции) грузится ОТДЕЛЬНО и ЛЕНИВО, со спиннером. Пакетов много, имя зависит от id.
- **Обычный (regular) атлас** ([раздел 2](#regular-atlas), `Creator.sprite`) — домен грузится
  ЦЕЛИКОМ и ЗАРАНЕЕ вместе с остальными ассетами экрана/попапа, одним пакетом с фиксированным
  именем, без спиннера на спрайт.

---

## 1. Async per-id атлас (`Creator.spriteAsync`) {#async-atlas}

### Шаги

1. **Разместить исходники** в `assets-src/atlas/<domain>/<id>/*.png` (один id-подпапка =
   один пакет, как `tanks/big/<id>/m.png`). Внутри одной id-папки может лежать несколько
   файлов — все они уедут в один и тот же пакет.

2. **Добавить запись в `tools/src/config.yaml`**, секция `atlasList`:
   ```yaml
   - { path: "<domain>/*", packageName: "<Prefix>_{pathPart:0}" }
   ```
   - `{pathPart:0}` подставляет **имя папки целиком, как оно есть на диске** (никакого
     парсинга/обрезки префиксов). Если папки называются `collection_1`, `collection_2`, ...,
     то `{pathPart:0}` даст `collection_1`, и итоговое имя пакета будет
     `<Prefix>_collection_1` — не пытайся вытащить только цифру, шаблонизатор так не умеет
     (проверено эмпирически). Если домен вложен на 2 уровня id-папок (как
     `collection/collection_items/<collectionId>/<itemId>/*.png`), используй `{pathPart:1}` для
     внутреннего уровня — см. запись `collection/collection_items/*/*` →
     `CollectionItem_{pathPart:1}` в `config.yaml`.
   - Дефолтный размер текстуры-шита — **1024×1024**. Если один фрейм больше (или несколько
     фреймов в сумме не влезают — пакуется несколько картинок в один пакет), паковщик падает
     с ошибкой `width or height can't be equal to zero. Maybe frame size is bigger than
     texture size?`. Добавь `textureWidth`/`textureHeight` (2048×2048 как у
     `home_screen`/`battle_screen`) заранее, если картинки крупные/их много в одной id-папке.

3. **Одна большая одиночная картинка (фон и т.п.), НЕ атлас-фрейм** — не клади её в
   `atlasList`/в общий атлас-домен (упадёт с той же ошибкой размера текстуры, если она
   больше листа). Для таких кладём файл в `assets-src/raw/backgrounds/` и добавляем
   **явную** (не wildcard) запись в `rawList`:
   ```yaml
   - { path: "backgrounds/<file>.png", packageName: "<PackageName>" }
   ```
   Такой пакет не подхватывается через `Creator.spriteAsync` автоматически — либо:
   - грузи его через `Creator.spriteAsync(path, "<PackageName>")` как обычный динамический
     пакет (тогда см. пункт 4), либо
   - если он должен быть доступен сразу через обычный `Creator.sprite(path)` (без спиннера)
     — см. раздел 2 ниже (тот же механизм `addAssetPackage`, что и для обычных атласов).

4. **Только для доменов с per-id пакетами** (как `<Prefix>_{pathPart:0}`) — прописать вызов
   в `src/plain/LoadAssetPackage.ts` **для каждого фактического id**, имя должно **точно**
   совпадать с тем, что даст шаблон из `config.yaml`:
   ```ts
   "<Prefix>_<realFolderName>": () => App.assetPacker.addAssetPackage("<Prefix>_<realFolderName>"),
   ```
   Это то, что связывает `Creator.spriteAsync(path, "<Prefix>_<id>")` с реальной загрузкой
   пакета. Этот файл обычно синхронизируется самим паковщиком, но пока новых записей там
   нет — без ручного добавления `spriteAsync` не найдёт, за что зацепиться.

5. **В коде** — путь и имя пакета должны буквально совпадать с тем, что получилось в шагах
   2 и 4:
   ```ts
   Creator.spriteAsync(
       "atlas/<domain>/<realFolderName>/<file>.png",
       "<Prefix>_<realFolderName>"
   )
   ```

6. **Запустить паковщик**: `cd tools && sh ./AssetPacker.sh` (нужен установленный Java).
   Проверить, что всё реально собралось:
   ```bash
   python3 -c "
   import json
   d = json.load(open('assets/bundles/fullassetmap.wr'))
   print([k for k in d if 'Твой_Prefix' in k])
   "
   ```
   Если список пуст — паковщик не увидел новый путь, значит `config.yaml` не подхватился/
   опечатка в `path`. Реальный `.wr`-бандл лежит в
   `assets/bundles/<первые 2 символа id>/<id>.wr` — можно дополнительно проверить, что файл
   физически существует, а не только упомянут в `fullassetmap.wr`.

7. **Пересобрать/перезапустить клиент**. `fullassetmap.wr` — это file dependency вебпака
   (`WebpackModPlugin`), сборка должна пересобраться сама при его изменении, но если
   dev-server был запущен до перегенерации — сделай `npm start` заново + hard refresh в
   браузере, иначе будет закомпилен старый (несопоставленный) вариант.

---

## 2. Обычный (regular) атлас — грузится сразу пакетом, без спиннера на кадр {#regular-atlas}

Используется, когда набор картинок принадлежит экрану/попапу целиком и должен быть
доступен сразу через `Creator.sprite(path)`/`Creator.texture(path)` — без отдельного
`spriteAsync`+спиннера на каждый элемент. Живые примеры в `config.yaml`: `ui`,
`collection/collections_screen` → `CollectionsScreen`, `collection/collection_albums` →
`CollectionAlbums`, `collection/collection_items/collection_10-17` → `CollectionItemTank_10_17`
(и остальные диапазоны монет) — фиксированное `packageName` без `{pathPart}`-шаблона (в отличие
от per-id доменов раздела 1).

### Шаги

1. **Разместить исходники** в `assets-src/atlas/<domain>/*.png` — обычная плоская папка
   (без per-id подпапок; если понадобится группировка — она чисто файловая, паковщик её не
   использует, ключевое отличие от раздела 1).

2. **Добавить запись в `tools/src/config.yaml`**, секция `atlasList`, БЕЗ `{pathPart}`:
   ```yaml
   - { path: "<domain>", packageName: "<PackageName>" }
   ```
   Те же правила по размеру текстуры-листа (1024×1024 по умолчанию, `textureWidth`/
   `textureHeight` при необходимости), что и в разделе 1, п.2.

3. **Подключить загрузку пакета** — добавь
   `App.assetPacker.addAssetPackage("<PackageName>")` туда, где уже грузятся соседние
   пакеты этого же экрана/попапа ПЕРЕД его открытием. Живой пример:
   `ProfilePopup.loadAssets()` (`src/views/home_screen/popups/profile/ProfilePopup.ts`)
   грузит пачкой `CollectionsScreen`/`CollectionAlbumsBackground`/`CollectionAlbums`/
   `CollectionCoinIcon`/`CollectionItemTank_*` перед
   открытием попапа — по этому же паттерну добавляй новый пакет рядом с существующими
   `addAssetPackage`-вызовами того экрана, которому принадлежит новый домен. `LoadAssetPackage.ts`
   для обычных атласов НЕ трогать — этот файл только для async per-id пакетов раздела 1
   (связывает динамическое имя пакета из `spriteAsync` с `addAssetPackage`; у обычного
   атласа имя пакета уже фиксировано и известно в коде напрямую).

4. **В коде** — после того как пакет загружен (экран/попап открыт), просто:
   ```ts
   Creator.sprite("atlas/<domain>/<file>.png")
   ```
   без второго аргумента (packageName) — не нужен, `Creator.sprite` не занимается async-
   догрузкой.

5. **Запустить паковщик и проверить** — см. раздел 1, п.6-7 (полностью совпадает).

---

## Частые причины "картинка не показалась, ошибок нет" {#troubleshooting}

- Домен не добавлен в `config.yaml` → паковщик его просто не видит (никаких ошибок при этом
  не будет, сборка просто не создаст пакет).
- Имя пакета в `LoadAssetPackage.ts`/в коде не совпадает 1-в-1 с тем, что реально
  сгенерировал шаблон `{pathPart:0}` в `config.yaml` (например забыли префикс исходной
  папки) — актуально только для async per-id пакетов (раздел 1).
- Имя пакета передано в `App.assetPacker.addAssetPackage(...)` НЕ строковым литералом (например
  `addAssetPackage("CollectionItem_" + id)`). `webpack/WebpackModPlugin.js` на этапе сборки
  подменяет имя на реальный id пакета только в литерале `addAssetPackage("...")` — динамическая
  строка уходит как есть, в консоли 404 на `assets/bundles/<2 символа>/<Имя>-<Имя>.wr`, а
  `onComplete` не срабатывает. Для per-id пакетов вызывать через
  `LoadAssetPackage[pkg]()` (`src/plain/LoadAssetPackage.ts` — там литералы), как делает
  `AsyncSprite`.
- Для обычного атласа (раздел 2) — забыли вызвать `addAssetPackage("<PackageName>")` до
  того, как код дошёл до `Creator.sprite(...)` на путь из этого домена; либо вызвали его
  ПОСЛЕ, а не ДО открытия экрана/попапа.
- Одиночная крупная картинка засунута в атлас-домен с маленьким текстур-листом → паковщик
  падает при сборке (это как раз видно в консоли `AssetPacker.sh`, а не в браузере).
- `dist/` — это застывший прод-билд, а не то, что видит dev-server; не ориентируйся на его
  дату при диагностике "не обновилось".
- Отдельный частый баг именно в TypeScript-коде: не путай `resizable + calculateBounds: true`
  на ScrollableArea (внешнем вьюпорте скролла) без `fixedWidth`/`fixedHeight` —
  `calculateBounds` в этом случае переписывает `width`/`height` вьюпорта размером контента,
  и скролл-окно "раздувается" под контент вместо того чтобы оставаться фиксированным. Если
  высота задана литералом (`height: N`), а не через `pheight`, обязательно добавляй
  `fixedHeight`/`fixedWidth` — иначе вьюпорт потеряет фиксированный размер.
