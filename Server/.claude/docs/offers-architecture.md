# Магазин и офферы (сервер)

ГДД: [`/workspace/client/.claude/docs/game-design/shop-gdd.md`](/workspace/client/.claude/docs/game-design/shop-gdd.md) — черновик по коду от 2026-10-17. Ни одно правило пользователь пока не
подтвердил: все они записаны в [открытые вопросы ГДД](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) (О1–О17), и ссылки `ГДД #gdd-open`
ниже означают «так в коде, требует подтверждения». Таблица «раздел ГДД → реализация» — [§9](#gdd-link).

> **auto-create** — документ составлен `server-analyst-lead` по существующему коду, 2026-10-17. Код в
> рамках задачи не менялся. Доверие пониженное: утверждения подтверждены чтением серверного кода;
> после merge `amnesia/fix` (2026-10-19) актуализированы цены наборов, ссылки на строки и траты золота; клиент просмотрен только в объёме роутов и типов, которые он шлёт и ждёт
> ([контракт](#client-contract)), его поведение не анализировалось.

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
   - [Модель оффера](#offer-model)
   - [Жизненный цикл покупки](#purchase-flow)
   - [Появление, таймеры и лимиты офферов](#lifecycle)
   - [Покупки за золото](#gold-spend)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. Классы и методы
   - [`OffersUserComponent`](#cls-offersusercomponent)
   - [`Offer`](#cls-offer)
   - [`GoldenCoinsOffer`](#cls-goldencoinsoffer)
   - [`OffersService`, `OfferId`, `OfferRewardData`, `ProcessPaymentResult`](#cls-small)
   - [`PaymentProcessor`](#cls-paymentprocessor)
   - [`PaymentRequest`, `PaymentDao`](#cls-paymentrequest)
   - [Платёжные страницы `/pblc/*`](#cls-payment-pages)
   - [`ShopPage`](#cls-shoppage)
   - [Точки в `User`, `AuthorizedUserPage`, `DevToolsPage`](#cls-hooks)
   - [Персистентность](#persistence)
   - [Контракт с клиентом](#client-contract)
8. [Принятые уязвимости, компромиссы и подозрительные места](#tradeoffs)
   - [Отложенные исправления](#deferred)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)
    - [Файлы прямого влияния](#file-map-direct)
    - [Файлы косвенного влияния](#file-map-indirect)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Область продаёт игроку внутриигровое золото (`ItemId.RESOURCE_GOLDEN_COINS`) за реальные деньги.
Единственный оффер в коде — «Набор золота» (`GoldenCoinsOffer`, id `1`): шесть наборов от 150 до
12 000 рублей, от 1 500 до 120 000 золота. Оффер бессрочный и всегда доступен, число покупок не
ограничено.

Покупка проходит в два шага. Платёжная система (ВК, Одноклассники, ЮKassa, партнёрка Overmobile)
присылает на сервер уведомление о платеже; сервер проверяет цену и записывает в оффер «купленный,
но не забранный» набор. Игрок открывает магазин, видит набор с флагом `canTake` и нажимает «Забрать» —
только тогда золото попадает в сумку. Купленные наборы хранятся в профиле без срока.

<a id="offer-model"></a>
### Модель оффера

`OffersUserComponent` держит словарь `offerId → Offer` активных офферов. Абстрактный `Offer` задаёт
общий каркас: срок действия (`expirationTime`: `0` — неактивен, `-1` — бессрочный, иначе момент
истечения в мс), цену и название набора по индексу, проверку цены, реакцию на платёж и выдачу
награды. Конкретный оффер — наследник со своим списком наборов (`OfferRewardData`: цена + список
предметов-шаблонов). Реестр типов — `OffersService` (id → конструктор).

Платёж привязан к офферу через код товара `offer_<цена>_<offerId>_<индекс набора>`. Код формирует
клиент (`PaymentHelper.getProductCode`), платёжная система возвращает его серверу без изменений.

<a id="purchase-flow"></a>
### Жизненный цикл покупки

1. Клиент открывает окно оплаты нужной платёжной системы с кодом товара.
2. Платёжная система вызывает публичный HTTP-роут (`/pblc/vkpayment`, `/pblc/okpayment`,
   `/pblc/yoopayment`, `/pblc/payment`). Страница проверяет подпись и согласованность суммы
   с ценой из кода, затем запускает задачу [`PaymentProcessor`](#cls-paymentprocessor).
3. `PaymentProcessor` находит пользователя, проверяет, не обработан ли уже платёж с той же парой
   `provider + orderId`, и выполняет `User.processPaymentRequest` внутри актора пользователя.
4. `OffersUserComponent.processPaymentRequest` разбирает код, проверяет оффер и цену, добавляет
   индекс набора в `purchasedBundles` оффера и ставит уведомление `purchasedOfferId`.
5. При успехе платёж записывается в коллекцию `payment_requests`; при неуспехе страница отвечает
   платёжной системе ошибкой.
6. Клиент видит уведомление (значок на кнопке магазина), открывает магазин, вызывает
   `/ingame/shop/takePurchasedOffer` — набор снимается из `purchasedBundles`, награда кладётся в
   сумку.

<a id="lifecycle"></a>
### Появление, таймеры и лимиты офферов

- Появление. Перед каждым WS-запросом игрока (`AuthorizedUserPage.onRouteCallStart`) вызывается
  `resetOffers()`. Он убирает истёкшие офферы и активирует «Набор золота», если тот неактивен.
  Других условий появления в коде нет: офферов, которые открываются по уровню, событию или покупке,
  сейчас не существует.
- Таймеры. Каркас поддерживает срок (`expirationTime`, `isExpired`), но единственный оффер
  бессрочный (`start()` ставит `ENDLESS`). Поле `startTime` нигде не задаётся. Истёкший оффер
  снимается только после того, как игрок забрал все купленные наборы.
- Лимиты. Лимита покупок нет: каждый платёж добавляет запись в `purchasedBundles`, повторы одного
  набора хранятся как отдельные записи. `isCompleted()` у «Набора золота» всегда `false`.

<a id="gold-spend"></a>
### Покупки за золото

Своего магазина «за золото» у области нет. Золото тратят другие области, они описаны в своих
документах:

- покупка наборов схем танка — `TrainPage /buySchemes`, [train-architecture.md](train-architecture.md)
  (`TrainBuySchemesData`);
- смена логина — `SettingsPage`, `User.LOGIN_CHANGE_COST = 1000` (области без документа).

Начисление и списание золота в сумке — [bag-architecture.md](bag-architecture.md).

<a id="references"></a>
## 2. Референсы

Не использовались. Документ описывает существующий код.

<a id="patterns"></a>
## 3. Паттерны

- **Шаблонный метод + реестр фабрик.** `Offer` задаёт каркас, наследник реализует наборы;
  `OffersService` создаёт оффер по id через `Supplier`.
- **Идемпотентность платежа** по паре `provider + orderId`: проверка перед начислением и уникальный
  индекс `payment_requests` (миграция `1770013290850_payment_exist_index.json`). Ограничения —
  [#tradeoffs](#tradeoffs), п.1.
- **Многошаговая задача (`Task`)** с выполнением внутри актора пользователя (`ExecuteInside` через
  `UserStore`): начисление не зависит от того, онлайн ли игрок.
- **Предметы-шаблоны** в статических наборах: `Resource.createNew(id, true)`, сумка кладёт личную
  копию (см. [bag-architecture.md](bag-architecture.md)).
- **Персистентность через `changedField`** целым поддокументом `list` при любом изменении.

<a id="class-list"></a>
## 4. Список классов

Задача ничего не создавала и не меняла. Ниже — классы области (полный список файлов —
[карта файлов](#file-map)).

| Класс | Пакет / путь | Роль |
|---|---|---|
| `OffersUserComponent` | `model.offers` | компонент пользователя: активные офферы, приём платежа, выдача награды |
| `Offer` | `model.offers.types` | абстрактный оффер: срок, каркас наборов, сериализация |
| `GoldenCoinsOffer` | `model.offers.list` | «Набор золота»: шесть наборов, купленные наборы |
| `OfferRewardData` | `model.offers` | цена + награды набора |
| `OfferId` | `model.offers` | константы id офферов |
| `ProcessPaymentResult` | `model.offers` | результат обработки платежа |
| `OffersService` | `service.offers` | реестр типов офферов, код товара |
| `PaymentProcessor` | `model.payment` | задача обработки платежа |
| `PaymentRequest` | `model.payment` | запись платежа |
| `PaymentDao` | `dao` | коллекция `payment_requests` |
| `ShopPage` | `pages.ws.ingame` | WS-роуты `/ingame/shop` |
| `VKPaymentPage`, `OdnoklassnikiPaymentPage`, `YookassaPaymentPage`, `PaymentPage` | `pages.rest.pblc` | HTTP-уведомления платёжных систем |

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#offer-model`, `#purchase-flow`, `#lifecycle`, `#gold-spend`, `#references`,
`#patterns`, `#class-list`, `#class-nav`, `#cls-offersusercomponent`, `#cls-offer`,
`#cls-goldencoinsoffer`, `#cls-small`, `#cls-paymentprocessor`, `#cls-paymentrequest`,
`#cls-payment-pages`, `#cls-shoppage`, `#cls-hooks`, `#persistence`, `#client-contract`,
`#tradeoffs`, `#deferred`, `#gdd-link`, `#file-map`, `#file-map-direct`, `#file-map-indirect`.

<a id="class-nav"></a>
## 6. Оглавление по классам

| Класс | Раздел |
|---|---|
| `OffersUserComponent` | [#cls-offersusercomponent](#cls-offersusercomponent) |
| `Offer` | [#cls-offer](#cls-offer) |
| `GoldenCoinsOffer` | [#cls-goldencoinsoffer](#cls-goldencoinsoffer) |
| `OffersService`, `OfferId`, `OfferRewardData`, `ProcessPaymentResult` | [#cls-small](#cls-small) |
| `PaymentProcessor` | [#cls-paymentprocessor](#cls-paymentprocessor) |
| `PaymentRequest`, `PaymentDao` | [#cls-paymentrequest](#cls-paymentrequest) |
| `VKPaymentPage`, `OdnoklassnikiPaymentPage`, `YookassaPaymentPage`, `PaymentPage` | [#cls-payment-pages](#cls-payment-pages) |
| `ShopPage` | [#cls-shoppage](#cls-shoppage) |
| `User`, `AuthorizedUserPage`, `DevToolsPage` (точки подключения) | [#cls-hooks](#cls-hooks) |

## 7. Классы и методы

<a id="cls-offersusercomponent"></a>
### `OffersUserComponent`

`game/src/main/java/com/linkedgames/game/model/offers/OffersUserComponent.java`. Наследник
`UserChildComponent`, создаётся лениво в `User.getOffersUserComponent()` с именем `"Offers"`. Поле
`availableOffersMap: Map<Integer, Offer>`. ГДД: [gdd-offers](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-offers), [gdd-take-reward](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-take-reward); правила в
[#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open).

- **`resetOffers()`** (стр. 35–69) — ГДД [gdd-offers](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-offers), [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О4–О6. Вызывается перед каждым WS-роутом. Деактивирует офферы, у которых
  одновременно `isActive && isExpired && isTaken` (истёк и всё купленное забрано), затем удаляет из
  словаря все неактивные; при изменениях сохраняет список. В конце активирует «Набор золота», если
  он неактивен.
- **`processPaymentRequest(PaymentRequest)`** (стр. 71–99) — ГДД [gdd-purchase-confirm](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-purchase-confirm), [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О13–О14. Id оффера и индекс набора берёт из кода
  (`getOfferIdByCode`, `getOfferNumberByCode`). Успех, только если оффер есть, активен, не
  `isCompleted` и `checkPrice(price, индекс)` вернул `true`. Тогда дописывает в `PaymentRequest`
  `offerId`, `offerNumber`, `purchaseName`, вызывает `offer.onPaymentReceiver`, ставит уведомление
  `purchasedOfferId = offerId` и сохраняет список. Код без префикса `offer` пишет в лог ошибку и
  возвращает неуспех.
- **`takePurchasedOffer(offerId, bundleIndex)`** (стр. 101–116) — ГДД [gdd-take-reward](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-take-reward), [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О13, О15–О16. Сразу снимает уведомление
  `purchasedOfferId`; затем ищет оффер, проверяет, что он не `isTaken`, и вызывает
  `offer.execute(user, bundleIndex)`. Любая неудача — `null` (роут отвечает `error()`).
- **`getPlainPurchaseName(price, code)`** (стр. 168–181) — ГДД [gdd-price-display](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-price-display) (название в окне ВК), [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О11. Название товара для окна подтверждения ВК
  (`get_item`). Те же проверки, что в `processPaymentRequest`; неуспех — `null`; код не офферный —
  пустая строка.
- **`activateOffer(id)`** (стр. 151–159) — ГДД [gdd-offers](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-offers), О4–О5. Создаёт оффер через `OffersService`, вызывает `start()`,
  кладёт в словарь, сохраняет. Неизвестный id игнорируется.
- **`getPurchasedOffersJSON()`** (стр. 189–199) — офферы с незабранными покупками (`!isTaken`).
- **`apiResponse()`** (стр. 201–213) — `{list: [все офферы], purchased: [незабранные]}`.
- **`dbMappingBuild(Document)`** (стр. 215–234) — восстанавливает офферы из поддокумента `list`,
  пропуская нечисловые ключи и неизвестные id; вызывает `offer.restore(user)`.
- Тривиальные: `isOfferActive(id)`, `getOfferIdByCode`, `getOfferNumberByCode` (разбор кода по `_`,
  части 2 и 3), `updateOffersData()` (`changedField("list", ...)`), пустой `modifyReceiver`.

<a id="cls-offer"></a>
### `Offer`

`game/src/main/java/com/linkedgames/game/model/offers/types/Offer.java`. Абстрактный класс,
`IPersistentObject` + `APIResponseStd`. ГДД: [gdd-offers](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-offers) (срок и активность — [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О4, О6).

- Состояние: `id`, `startTime`, `expirationTime` (константа `ENDLESS = -1`).
- `isActive()` — `expirationTime != 0`; `isExpired()` — `expirationTime >= 0` и текущее время не
  меньше `expirationTime` (бессрочный не истекает); `deactivate()` → `clearState()` → `expirationTime = 0`.
- `restore(User)` — хук после загрузки из БД, в базе пустой.
- Абстрактные: `start`, `isCompleted`, `isTaken`, `getPrice(bundle)`, `getName(bundle)`,
  `checkPrice(price, bundle)`, `onPaymentReceiver(PaymentRequest)`, `execute(User, bundle)`,
  `apiResponse`.
- `dbMappingBuild`/`dbToData` — поля `et`, `st`, нули не пишутся.

<a id="cls-goldencoinsoffer"></a>
### `GoldenCoinsOffer`

`game/src/main/java/com/linkedgames/game/model/offers/list/GoldenCoinsOffer.java`. id
`OfferId.GOLDEN_COINS_OFFER = 1`. ГДД: [gdd-gold-bundles](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-gold-bundles), [gdd-offers](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-offers); все числа ниже — «так в коде»,
[#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О2, О4.

Наборы (`BUNDLES`, стр. 27–46), цена в рублях → золото:

| Индекс `n` | Цена | Золото |
|---|---|---|
| 0 | 150 | 1 500 |
| 1 | 450 | 4 500 |
| 2 | 1 500 | 15 000 |
| 3 | 3 000 | 30 000 |
| 4 | 6 000 | 60 000 |
| 5 | 12 000 | 120 000 |

Константа `GOLD_PER_ROUBLE = 10` (стр. 23) используется только в отчёте партнёрке
(`OvermobileService.gameDrivenPayment`); после смены цен на круглые она совпадает со всеми наборами ([#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О14). Комментарий на стр. 25–26 описывает, как добавить бонусное
золото вторым предметом набора; сейчас бонуса нет.

- `purchasedBundles: List<Integer>` — купленные и незабранные индексы, с повторами.
- `start()` — `expirationTime = ENDLESS`. `isCompleted()` — всегда `false`.
- `isTaken()` ([gdd-take-reward](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-take-reward)) — `purchasedBundles.isEmpty()`: «забирать нечего». Имя читается наоборот, см.
  [#tradeoffs](#tradeoffs), п.7.
- `checkPrice(price, n)` — точное совпадение с ценой набора; неизвестный индекс даёт цену `-1`.
- `getName(n)` — `"Набор Золота #" + (n + 1)`.
- `onPaymentReceiver` — добавляет `offerNumber` платежа в `purchasedBundles`.
- `execute(user, n)` ([gdd-take-reward](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-take-reward), О15) — если `n` есть в `purchasedBundles`, удаляет одно вхождение, выдаёт предметы
  набора через `user.addItem` и возвращает `{rewards: [ItemJSON]}`; иначе `null`.
- `restore(user)` ([gdd-purchase-confirm](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-purchase-confirm), О13) — при загрузке профиля с незабранными наборами ставит уведомление
  `purchasedOfferId = 1`.
- `apiResponse()` — `{id, bundles: [{n, price, canTake, rewards}]}`.
- Персистентность — поле `pb` (список индексов), пишется, только если не пуст.

<a id="cls-small"></a>
### `OffersService`, `OfferId`, `OfferRewardData`, `ProcessPaymentResult`

- `OffersService` (`service/offers/OffersService.java`): `offerExists(id)`, `createOffer(id)`
  (неизвестный id → `NullPointerException`, проверку делает вызывающий), `makeCodeOffer(price,
  offerId, n)` — не вызывается нигде, код на деле собирает клиент.
- `OfferId` — `GOLDEN_COINS_OFFER = 1`.
- `OfferRewardData` — неизменяемые `price` и `rewards`, builder.
- `ProcessPaymentResult` — `success` и `offer`; `offer` читает только пустая ветка в
  `User.processPaymentRequest`.

<a id="cls-paymentprocessor"></a>
### `PaymentProcessor`

`game/src/main/java/com/linkedgames/game/model/payment/PaymentProcessor.java`. Восемь перегрузок
`createPaymentProcessorTask` сводятся к приватной (стр. 63–152). ГДД: [gdd-purchase-confirm](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-purchase-confirm), [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О14. Шаги задачи:

1. `findUser` — по `social` или `nid`; не найден → `fail(REASON_USER_NOT_FOUND)`.
2. `findPaymentRequest(provider, orderId)` — запись есть → `duplicate = true`, `success()` без
   повторного начисления.
3. Создаётся `PaymentRequest` (валюта по умолчанию RUB).
4. `paymentExecute` — `User.processPaymentRequest` в акторе пользователя; `false` →
   `fail(REASON_INCORRECT_PAYMENT)`, запись в БД не делается.
5. `insertPaymentRequest`; ошибка вставки только пишется в лог.

`getPriceFromCode(code)` (стр. 154–166) — вторая часть кода по `_`, иначе `0`.

<a id="cls-paymentrequest"></a>
### `PaymentRequest`, `PaymentDao`

- `PaymentRequest` (`model/payment/PaymentRequest.java`) — документ `payment_requests`: `_id`,
  `provider`, `userId`, `orderId`, `price`, `code`, `time`; `convertedPrice` + `currency`, если
  заданы; `offerId`/`offerNumber` (только `> 0`, поэтому набор с индексом 0 сохраняется без
  `offerNumber`), `name`, `extra`. Конструктор из `Document` нигде не используется.
- `PaymentDao` (`dao/PaymentDao.java`) — `findPaymentRequest(provider, orderId)`,
  `insertPaymentRequest`, `findLastPaymentRequestByUserId` (не вызывается). Индексы — уникальный
  `{provider, orderId}` и `{userId}` (миграции в [карте файлов](#file-map-direct)).

<a id="cls-payment-pages"></a>
### Платёжные страницы `/pblc/*`

ГДД: [gdd-payment-channels](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-payment-channels), [gdd-price-display](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-price-display) ([#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О8, О10, О11).
Регистрация — `HTTPRouter` (стр. 28–31). Все страницы считают цену из кода (`getPriceFromCode`) и
отказывают при `price <= 0`.

- **`VKPaymentPage`** (`/pblc/vkpayment`, POST). Подпись MD5 с секретом приложения.
  `get_item`/`get_item_test` — название через `getPlainPurchaseName`, цена в голосах
  `VKUtil.getPriceVoices(price) = ceil(price / 7)`, картинка — общая иконка игры.
  `order_status_change` + `chargeable` — `PaymentProcessor`; для боевого (не `_test`) и
  неповторного платежа — отчёт `OvermobileService.gameDrivenPayment` (выручка `голоса × 7`, прибыль
  `голоса × 3`). Ошибки — коды ВК 1/2/10/11/20/22.
- **`OdnoklassnikiPaymentPage`** (`/pblc/okpayment`, GET). Подпись MD5; `amount` обязан совпасть с
  ценой из кода; отчёт партнёрке (выручка `price × 1.1`, прибыль `price × 0.42`).
- **`YookassaPaymentPage`** (`/pblc/yoopayment`, POST). Доступ только с IP/подсетей ЮKassa; событие
  `payment.succeeded`, пользователь — `metadata.nid`, код — `metadata.code`, сумма `amount.value`
  обязана совпасть с ценой; отчёт партнёрке только для не тестовых платежей. `payment.canceled` —
  просто 200.
- **`PaymentPage`** (`/pblc/payment`, GET) — уведомления партнёрки Overmobile. Для провайдеров
  партнёрки 2.0 (`HUAWEI`, `GOOGLE3`, `APPBAZAR`, `RUSTORE`, `YANDEXPAY`, `BEELINE`, `IFREE2`) с
  `command=pay` начисляет через `PaymentProcessor` (код — `data.productId`; песочница в продакшене
  подтверждается без начисления). Для остальных только отвечает `check`/`pay` без начисления.

<a id="cls-shoppage"></a>
### `ShopPage`

`game/src/main/java/com/linkedgames/game/pages/ws/ingame/ShopPage.java`, `WSRouter` → `/ingame/shop`. ГДД: [gdd-shop-entry](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-shop-entry), [gdd-take-reward](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-take-reward), [gdd-payment-channels](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-payment-channels).

| Роут | Запрос | Ответ |
|---|---|---|
| `""` | — | `{offers: OffersUserComponent.apiResponse()}` |
| `/purchased` | — | `{purchased: [...]}` |
| `/takePurchasedOffer` | `{id, n}` (`getInt`) | `{rewards: [ItemJSON]}` или `error()` |
| `/yookassaPaymentToken` | `{price, name, code, pid, email}` | всегда `error()` — заглушка `if (true)` на стр. 56 |

Код после заглушки (стр. 63–99) проверяет параметры, сверяет цену с кодом и запрашивает токен через
`OvermobileService.getYookassaPaymentToken` с таймаутом 10 с — сейчас недостижим.

<a id="cls-hooks"></a>
### Точки в `User`, `AuthorizedUserPage`, `DevToolsPage`

- `User`: поле `offers` и ленивый `getOffersUserComponent()` (стр. 257–262), `modifyReceiver`
  (стр. 431), загрузка из поля `Offers` (стр. 699–701, константа `P_OFFERS_FIELD` на стр. 760),
  `processPaymentRequest` (стр. 1092–1102) — обёртка над компонентом с пустой веткой «обработка» для
  «Набора золота».
- `AuthorizedUserPage.onRouteCallStart` (стр. 22) — `resetOffers()` перед каждым WS-роутом ([gdd-offers](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-offers)).
- `DevToolsPage` (`/ingame/devTools`, только при `app.devTools=true`):
  - `/offer` (`actionOffer`, стр. 199–232) — `{code}`; при коде из 4 частей создаёт `PaymentRequest`
    с провайдером `test` и вызывает `User.processPaymentRequest` в обход `PaymentProcessor` и
    `payment_requests`. Ответ всегда пустой `ok()`.
  - `/userGoldenCoins` (стр. 63–70) — +5 000 золота, пока у игрока меньше 500 000 000.

<a id="persistence"></a>
### Персистентность

Профиль пользователя, поле `Offers`:

```
Offers: { list: { "<offerId>": { et: <long>, st: <long>?, pb: [<int>, ...]? } } }
```

Весь поддокумент `list` переписывается при каждом изменении (`changedField`). Платежи — отдельная
коллекция `payment_requests` ([`PaymentRequest`](#cls-paymentrequest)). Своей Mongo-коллекции у
`OffersUserComponent` нет.

<a id="client-contract"></a>
### Контракт с клиентом

Сверено по коду клиента точечно (роуты и типы), поведение клиента не анализировалось.

| Сервер | Клиент | Данные |
|---|---|---|
| `/ingame/shop` | `ShopPopup.requestData` (`src/views/home_screen/popups/shop/ShopPopup.ts`) | `ShopPopupJSON { offers: OffersJSON { list: OfferJSON[], purchased: OfferJSON[] } }`, `BundleOfferJSON { bundles: BundleJSON { n, price, canTake, rewards } }` — `shop.d.ts` |
| `/ingame/shop/purchased` | `ShopPopup.requestPurchasedOffers` | `{ purchased: OfferJSON[] }` |
| `/ingame/shop/takePurchasedOffer` | класс `GoldenCoinsOffer`, кнопка «Забрать» (файл `src/views/home_screen/popups/shop/offers/GoldenCoinsOfferPopup.ts`) | запрос `{id, n}`, ответ `{rewards: ItemJSON[]}`; клиент удерживает золото в сумке (`holdResource`) на время анимации |
| `/ingame/shop/yookassaPaymentToken` | `PaymentHelper` (`src/utils/PaymentHelper.ts`) | клиент вызывает, сервер всегда отвечает ошибкой ([#tradeoffs](#tradeoffs), п.4) |
| `/ingame/devTools/offer` | `PaymentMethodsPopup` (`.../shop/PaymentMethodsPopup.ts`) | `{code}` → пустой `ok` |
| push `/events/userNotification` | `Notifications.PURCHASED_OFFER_ID`, `Footer`, `ShopPopup.handleUserNotifications` | `{method: UPDATE, name: "purchasedOfferId", value: offerId}` / `{method: DELETE, name}`; при входе — в `notifications` профиля |
| код товара | `PaymentHelper.getProductCode` | `offer_<цена>_<offerId>_<n>`; на сервере разбирают `PaymentProcessor.getPriceFromCode` и `OffersUserComponent.getOfferIdByCode`/`getOfferNumberByCode` |

Начисление золота в сумку после `/takePurchasedOffer` клиент получает через push сумки
([bag-architecture.md](bag-architecture.md)).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и подозрительные места

Номера строк — на 2026-10-19 (после merge `amnesia/fix`); у `GoldenCoinsOffer` цены наборов изменены, остальной код области не менялся.

1. **Двойное начисление при параллельных уведомлениях об одном платеже.**
   `PaymentProcessor.java:102–112` проверяет `orderId` до начисления, запись делается после него
   (стр. 138–149). Два одновременных уведомления (повтор платёжной системы по таймауту) оба проходят
   проверку и оба начисляют набор; уникальный индекс отклонит вторую вставку, но ошибка только
   пишется в лог (стр. 144–148), награда уже выдана. Та же ситуация при ошибке БД на вставке:
   набор выдан, записи нет, повтор уведомления выдаст его ещё раз.
2. **Начисление живёт в памяти до сохранения профиля.** `processPaymentRequest` меняет
   `purchasedBundles` через `changedField` (`OffersUserComponent.java:92`), а запись в
   `payment_requests` идёт сразу. Падение сервера между ними даёт оплаченный платёж без набора и
   без повторного начисления: платёж помечен обработанным.
3. **Уведомление снимается до проверки и при оставшихся наборах.**
   `OffersUserComponent.java:102` удаляет `purchasedOfferId` в начале `takePurchasedOffer`, даже если
   запрос завершится ошибкой или у игрока остались другие незабранные наборы. Значок магазина
   пропадает до следующего входа (вернёт `GoldenCoinsOffer.restore`, стр. 59–65).
4. **Роут токена ЮKassa отключён.** `ShopPage.java:56–61` — `if (true)` отвечает ошибкой, код ниже
   недостижим; клиент (`PaymentHelper.ts:134`) роут вызывает. Решение пользователя 2026-10-17: в
   [отложенные исправления](#deferred); ГДД [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open), О10.
5. **Повторное уведомление с тем же значением не отправляется.** `NotificationUserComponent.addNotification`
   (стр. 22–24) пропускает значение, равное текущему. После `restore` (значение `1`) новый платёж
   не шлёт push; открытый магазин не узнает о покупке, пока не будет нового запроса.
6. **`/devTools/offer` падает на неизвестном id и нечисловом коде.** `DevToolsPage.java:210–211` —
   `Integer.parseInt` без защиты; `OffersService.createOffer` (`OffersService.java:20`) для неизвестного
   id бросает NPE, проверка `offer == null` на стр. 214 мёртвая. Только dev.
7. **Имя `isTaken` у «Набора золота» значит «забирать нечего».** `GoldenCoinsOffer.java:78–80`.
   `resetOffers` (`OffersUserComponent.java:41`) и `takePurchasedOffer` (стр. 107) читают его именно
   так, но имя легко понять наоборот. Кандидат на переименование (решение — пользователю).
8. **Мёртвый код — кандидаты на удаление:** пустая ветка с приведением типа в
   `User.processPaymentRequest` (`User.java:1095–1098`) и поле `ProcessPaymentResult.offer`, которое
   читает только она; `OffersService.makeCodeOffer` (стр. 23–25); `Offer.startTime` (никто не
   задаёт); `PaymentDao.findLastPaymentRequestByUserId` (стр. 50–61); конструктор
   `PaymentRequest(Document)`.
9. **`getPlainPurchaseName` для не офферного кода возвращает пустую строку.**
   `OffersUserComponent.java:180`: ВК получит товар с пустым названием, а платёж затем отклонится в
   `processPaymentRequest` (стр. 94–96). Сейчас других кодов нет, проявится при новом типе товара.
10. **Цена в разных валютах сравнивается одним числом.** Код хранит цену в рублях; ОК сверяет её с
    `amount` в ОК (1 ОК = 1,1 ₽ по `OdnoklassnikiPaymentPage.java:64`), ВК переводит в голоса с
    округлением вверх (`VKUtil.getPriceVoices`). Реальная цена набора отличается по платформам; что
    так задумано, по коду не видно.
11. **ЮKassa: NPE без `income_amount`.** `YookassaPaymentPage.java:120` читает
    `incomeAmount.optString` до проверки на `null` (стр. 121). Задача упадёт до начисления, ЮKassa
    повторит уведомление.
12. **`resetOffers` на каждом WS-запросе** (`AuthorizedUserPage.java:22`) обходит словарь офферов.
    Сейчас оффер один, затраты малы; при росте числа офферов с таймерами стоит пересмотреть.
13. **Два шага у вызывающего при выдаче.** `takePurchasedOffer` снимает уведомление сам, а
    добавление — в `processPaymentRequest`, восстановление — в `GoldenCoinsOffer.restore`. Правило
    «значок горит, пока есть незабранные наборы» разнесено по трём местам и уже расходится (п.3).
    Кандидат на один метод у компонента, который пересчитывает уведомление по состоянию офферов.

<a id="deferred"></a>
### Отложенные исправления

Ничего из списка не исправлено; приоритет — по влиянию на деньги игрока. Номера — пункты
[#tradeoffs](#tradeoffs).

1. Высокий. Двойная выдача при параллельном повторе уведомления и оплата без набора при сбое (п.1–2);
   ГДД [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) О14.
2. Высокий. ЮKassa отключена: роут токена всегда отвечает ошибкой, клиент показывает способы оплаты
   (п.4). Решение пользователя 2026-10-17: отложено, обсудить с `integration-lead` (прятать или
   включать); ГДД О10.
3. Высокий. NPE в `YookassaPaymentPage` без `income_amount` (п.11).
4. Средний. Уведомление `purchasedOfferId` снимается до проверки и при оставшихся наборах; повторный
   push не уходит; правило разнесено по трём местам (п.3, 5, 13); ГДД О13.
5. Низкий. Валюты ВК и ОК сравниваются одним числом (п.10); ГДД О11.
6. Низкий. `/devTools/offer` падает на неизвестном id (п.6), имя `isTaken` (п.7), мёртвый код (п.8),
   пустое название для не офферного кода (п.9), `resetOffers` на каждом запросе (п.12).

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`shop-gdd.md`](/workspace/client/.claude/docs/game-design/shop-gdd.md) — черновик по коду от 2026-10-17. Правила из кода пользователь не
подтвердил, они вынесены в [#gdd-open](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-open) (О1–О17); таблица показывает, где
реализован каждый раздел.

| Раздел ГДД | Открытые вопросы | Реализация на сервере |
|---|---|---|
| [gdd-purpose](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-purpose) | — | вся область, [#purpose](#purpose) |
| [gdd-shop-entry](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-shop-entry) | О1 | `ShopPage` ([#cls-shoppage](#cls-shoppage)); вкладки и кнопка — клиент |
| [gdd-gold-bundles](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-gold-bundles) | О2, О3 | `GoldenCoinsOffer.BUNDLES` ([#cls-goldencoinsoffer](#cls-goldencoinsoffer)); цвет карточки — клиент |
| [gdd-offers](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-offers) | О4, О5, О6 | `OffersUserComponent.resetOffers`, `activateOffer`, `Offer` ([#lifecycle](#lifecycle), [#cls-offer](#cls-offer)) |
| [gdd-payment-channels](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-payment-channels) | О7–О10 | платёжные страницы, `ShopPage /yookassaPaymentToken` ([#cls-payment-pages](#cls-payment-pages)); регистрация и выбор канала — клиент |
| [gdd-price-display](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-price-display) | О11, О12 | `getPlainPurchaseName`, проверка цены в страницах ВК и ОК; показ цены — клиент |
| [gdd-purchase-confirm](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-purchase-confirm) | О13, О14 | `PaymentProcessor`, `OffersUserComponent.processPaymentRequest`, `GoldenCoinsOffer.restore` ([#purchase-flow](#purchase-flow)) |
| [gdd-take-reward](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-take-reward) | О15, О16 | `OffersUserComponent.takePurchasedOffer`, `GoldenCoinsOffer.execute` и `isTaken` |
| [gdd-receipt](/workspace/client/.claude/docs/game-design/shop-gdd.md#gdd-receipt) | О17 | на сервере нет: чек обрабатывает клиент и ЮKassa |

Одно правило — одна функция: функций с одним смыслом под разными именами не найдено. Исключение —
`User.processPaymentRequest`, тонкая обёртка над `OffersUserComponent.processPaymentRequest`
([#tradeoffs](#tradeoffs), п.8); кандидат на удаление после подтверждения правил.

<a id="file-map"></a>
## 10. Карта файлов компонента

Пути от корня `/workspace/server`; `…/game/` = `game/src/main/java/com/linkedgames/game/`.

<a id="file-map-direct"></a>
### Файлы прямого влияния

| Файл | Роль |
|---|---|
| `…/game/model/offers/OffersUserComponent.java` | компонент: офферы, приём платежа, выдача |
| `…/game/model/offers/types/Offer.java` | абстрактный оффер |
| `…/game/model/offers/list/GoldenCoinsOffer.java` | «Набор золота» |
| `…/game/model/offers/OfferRewardData.java` | цена и награды набора |
| `…/game/model/offers/OfferId.java` | id офферов |
| `…/game/model/offers/ProcessPaymentResult.java` | результат обработки платежа |
| `…/game/service/offers/OffersService.java` | реестр типов офферов |
| `…/game/model/payment/PaymentProcessor.java` | задача обработки платежа |
| `…/game/model/payment/PaymentRequest.java` | запись платежа |
| `…/game/dao/PaymentDao.java` | коллекция `payment_requests` |
| `…/game/pages/ws/ingame/ShopPage.java` | WS-роуты `/ingame/shop` |
| `…/game/pages/rest/pblc/VKPaymentPage.java` | уведомления ВК |
| `…/game/pages/rest/pblc/OdnoklassnikiPaymentPage.java` | уведомления ОК |
| `…/game/pages/rest/pblc/YookassaPaymentPage.java` | уведомления ЮKassa |
| `…/game/pages/rest/pblc/PaymentPage.java` | уведомления партнёрки Overmobile |
| `game/src/main/resources/migrations/1770013290850_payment_exist_index.json` | уникальный индекс `{provider, orderId}` |
| `game/src/main/resources/migrations/1770013464056_payment_user_index.json` | индекс `{userId}` |

<a id="file-map-indirect"></a>
### Файлы косвенного влияния

| Файл | Роль |
|---|---|
| `…/game/model/user/User.java` | создание компонента, загрузка поля `Offers`, `processPaymentRequest` |
| `…/game/pages/ws/ingame/AuthorizedUserPage.java` | `resetOffers()` перед каждым WS-роутом |
| `…/game/pages/ws/ingame/dev/DevToolsPage.java` | dev-роуты `/offer`, `/userGoldenCoins` |
| `…/game/pages/WSRouter.java` | регистрация `/ingame/shop` и `/ingame/devTools` |
| `…/game/pages/HTTPRouter.java` | регистрация `/pblc/*payment` |
| `…/game/service/integration/overmobile/OvermobileService.java` | отчёт партнёрке о платеже, токен ЮKassa; читает `GOLD_PER_ROUBLE` |
| `…/game/model/notifications/NotificationId.java` | зависимость: ключ `purchasedOfferId` |
| `…/game/model/notifications/NotificationUserComponent.java` | зависимость: хранение и push уведомлений |
| `…/game/model/bag/resource/Resource.java`, `…/game/model/item/ItemId.java` | зависимость: золото как предмет-шаблон |
| `…/game/service/integration/vk/VKUtil.java` | зависимость: цена в голосах, секрет ВК |
| `…/game/service/integration/IntegrationUtil.java` | зависимость: подписи, `social`/`provider`, картинка товара |
| `…/game/service/integration/odnoklassniki/OdnoklassnikiUtil.java`, `…/game/service/integration/yookassa/YookassaUtil.java` | зависимость: секрет ОК, IP ЮKassa |
| `…/game/pages/ws/ingame/TrainPage.java`, `…/game/pages/ws/ingame/SettingsPage.java` | траты золота в других областях ([покупки за золото](#gold-spend)) |
