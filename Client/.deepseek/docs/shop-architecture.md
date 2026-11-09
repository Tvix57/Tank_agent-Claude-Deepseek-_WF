# Магазин и офферы (клиент)

> **auto-create** — документ составлен по существующему коду, 2026-10-17; актуализирован
> 2026-10-19 после merge origin/amnesia/fix (изменились подвал, шрифты, иконка золота, тег флеша).
> Запуском не проверялось.
> Серверная сторона: `/workspace/server/.claude/docs/offers-architecture.md` (тоже auto-create).

ГДД: [`game-design/shop-gdd.md`](game-design/shop-gdd.md) — черновик по коду: правила не подтверждены, все пункты
в [#gdd-open](game-design/shop-gdd.md#gdd-open).

<a id="toc"></a>
## Оглавление

1. [Назначение и бизнес-логика](#purpose)
2. [Референсы](#references)
3. [Паттерны](#patterns)
4. [Список классов](#class-list)
5. [Навигация (якоря)](#anchors)
6. [Оглавление по классам](#class-nav)
7. [Классы и методы](#classes)
8. [Принятые уязвимости, компромиссы и известные проблемы](#tradeoffs)
9. [Связь с ГДД](#gdd-link)
10. [Карта файлов компонента](#file-map)

<a id="purpose"></a>
## 1. Назначение и бизнес-логика

Магазин — окно на весь экран, которое открывается кнопкой «МАГАЗИН» в подвале. В нём одна вкладка
«ЗОЛОТО»: сетка наборов золотых монет (`ItemId.RESOURCE_GOLDEN_COINS`) за реальные деньги. Наборы,
цены и награды присылает сервер в составе оффера с `id = 1` («набор золотых монет»); других офферов
сервер сейчас не создаёт, клиент других не умеет показывать.

Оффер — серверная сущность с набором пакетов (`bundles`). У каждого пакета есть номер `n`, цена в
рублях `price`, список наград `rewards` и флаг `canTake` — пакет оплачен, но награда ещё не забрана.
Покупка за золото в магазине не происходит: золото тратится в окне покупки схем поезда
(см. [train-architecture.md](train-architecture.md)); оно только берёт у магазина пакет ассетов
`ShopScreen`. Окна покупки схем аэродрома после merge в коде нет.

<a id="lifecycle"></a>
### Путь покупки на клиенте

1. **Открытие** ([#gdd-shop-entry](game-design/shop-gdd.md#gdd-shop-entry)). Кнопка «МАГАЗИН» в `Footer`
   (активна только когда туториал завершён, `tutorial.progress === -1`; повторное нажатие при
   открытом магазине закрывает его: `flashOverlay.removeAll("ShopPopup")`) → `ShopPopup.publish`: запрос `/ingame/shop`, загрузка пакета `ShopScreen`,
   показ окна. Сразу после показа окно проверяет `offers.purchased` (оплаченные и не забранные
   офферы) и рисует вкладку «ЗОЛОТО» (`DonateSection`).
2. **Выбор пакета** ([#gdd-gold-bundles](game-design/shop-gdd.md#gdd-gold-bundles)). Нажатие на карточку → `PaymentHelper.openPaymentWindow(price, offerId, n, name)`.
   Незарегистрированному игроку (`Globals.account.reg = false`) вместо оплаты показывается
   `ConnectPopup` (регистрация); после неё покупка сама не продолжается.
3. **Код товара** — строка `offer_<price>_<offerId>_<n>`. По нему сервер находит оффер, пакет и
   сверяет цену.
4. **Платёжный канал** выбирается по площадке ([#gdd-payment-channels](game-design/shop-gdd.md#gdd-payment-channels)):
   - Одноклассники — `FAPI.UI.showPayment` (сумма = `price`);
   - ВКонтакте — `vkBridge` `VKWebAppShowOrderBox` по коду товара;
   - остальные: есть платёжный модуль Overmobile SDK — `OVMSDK.purchase`; валюта аккаунта RUB —
     окно `PaymentMethodsPopup` (ЮKassa: карты, СБП, SberPay, ЮMoney, чек на email);
   - другая валюта без Overmobile SDK — ничего не происходит ([#tradeoffs](#tradeoffs) п.5).
5. **ЮKassa** ([#gdd-payment-channels](game-design/shop-gdd.md#gdd-payment-channels), [#gdd-receipt](game-design/shop-gdd.md#gdd-receipt)). `PaymentHelper.BtnPaymentYookassa` подгружает виджет ЮKassa, открывает
   `PaymentPopup` и запрашивает у сервера токен `/ingame/shop/yookassaPaymentToken`; виджет
   рисуется в DOM-блок `#yookassa` внутри `PaymentPopup`. Сейчас сервер на этот запрос всегда
   отвечает ошибкой ([#tradeoffs](#tradeoffs) п.7).
6. **Подтверждение оплаты** ([#gdd-purchase-confirm](game-design/shop-gdd.md#gdd-purchase-confirm)) приходит уведомлением аккаунта `purchasedOfferId` (push
   `NotificationJSON` → `User.receiveNotifications`); ни один запрос клиента его не возвращает. По нему `Footer`
   показывает значок на кнопке магазина, а открытый `ShopPopup` запрашивает
   `/ingame/shop/purchased`.
7. **Получение награды** ([#gdd-take-reward](game-design/shop-gdd.md#gdd-take-reward)). Для первого оффера из `purchased` по таблице `Offers.FLASH_LIST`
   открывается окно «ПОЗДРАВЛЯЕМ С ПОКУПКОЙ!» (`GoldenCoinsOffer`) с первым пакетом, у которого
   `canTake = true`. Кнопка «Забрать» → `/ingame/shop/takePurchasedOffer {id, n}`; при успехе
   золото удерживается в сумке (hold), летит иконками в шапку, затем hold снимается. При закрытии
   окна `ShopPopup` снова запрашивает `purchased` и показывает следующий пакет, пока список не
   опустеет. Если магазин закрыт, награда ждёт следующего открытия магазина; до этого виден только
   значок на кнопке.

<a id="references"></a>
## 2. Референсы

Нет. Окна оплаты и получения награды собраны по общей схеме попапов проекта (окно
`PanelsPresets.PNL_WINDOW_STANDARD`, заголовок, анимация появления, `GameFlash`).

<a id="patterns"></a>
## 3. Паттерны

- Попапы через `FlashPublisher.publish(GameFlash)` и очередь флешей —
  [popup-queue-pattern.md](popup-queue-pattern.md). `ShopPopup` помечен `LOWER_FLASH_TAG` и тегом `"ShopPopup"` (по нему `Footer` закрывает магазин; закрывает
  весь экран, главный экран под ним не рисуется); окна оплаты и награды — `setParallel(true)`.
- Hold ресурса на время анимации — [bag-architecture.md](bag-architecture.md) (`holdResource`/
  `releaseHold`).
- Обычный атлас и пакет ассетов `ShopScreen` —
  [asset-packaging.md#regular-atlas](asset-packaging.md#regular-atlas).
- Таблица «id оффера → функция показа окна» (`Offers.FLASH_LIST`) — точка расширения под новые
  офферы.

<a id="class-list"></a>
## 4. Список классов

В задаче классы не создавались и не менялись (auto-create). Классы области:

- `ShopPopup` — окно магазина.
- `DonateSection` — вкладка «ЗОЛОТО».
- `OffersSection` — пустая вкладка офферов (не используется).
- `Offers` — таблица окон получения награды по id оффера.
- `GoldenCoinsOffer` (файл `GoldenCoinsOfferPopup.ts`) — окно получения золота после оплаты.
- `PaymentHelper` — выбор платёжного канала, код товара, цена в валюте площадки.
- `PaymentMethodsPopup` (+ enum `YookassaPids`) — выбор способа оплаты ЮKassa.
- `PaymentPopup` — окно-контейнер виджета ЮKassa.
- Типы `shop.d.ts`: `ShopPopupJSON`, `OffersJSON`, `OfferJSON`, `BundleOfferJSON`, `BundleJSON`.

<a id="anchors"></a>
## 5. Навигация (якоря)

`#purpose`, `#lifecycle`, `#references`, `#patterns`, `#class-list`, `#class-nav`, `#classes`,
`#cls-shoppopup`, `#cls-donatesection`, `#cls-offerssection`, `#cls-offers`,
`#cls-goldencoinsoffer`, `#cls-paymenthelper`, `#cls-paymentmethodspopup`, `#cls-paymentpopup`,
`#cls-types`, `#client-contract`, `#tradeoffs`, `#gdd-link`, `#file-map`.

<a id="class-nav"></a>
## 6. Оглавление по классам

- [ShopPopup](#cls-shoppopup)
- [DonateSection](#cls-donatesection)
- [OffersSection](#cls-offerssection)
- [Offers](#cls-offers)
- [GoldenCoinsOffer](#cls-goldencoinsoffer)
- [PaymentHelper](#cls-paymenthelper)
- [PaymentMethodsPopup](#cls-paymentmethodspopup)
- [PaymentPopup](#cls-paymentpopup)
- [Типы shop.d.ts](#cls-types)
- [Контракт с сервером](#client-contract)

<a id="classes"></a>
## 7. Классы и методы

У методов с бизнес-смыслом указан раздел ГДД. Правила в разделах пока не подтверждены
(черновик по коду), поведение описано по коду. Методы с общим разделом ГДД не дублируют друг
друга ([#gdd-function-mapping](agent-system-workflow.md#gdd-function-mapping)):

- `#gdd-take-reward`: `ShopPopup.checkPurchasedOffers`/`requestPurchasedOffers` выбирают, какое
  окно получения показать и когда показать следующее; `GoldenCoinsOffer.BtnTake` забирает
  конкретный набор.
- `#gdd-price-display`: `PaymentHelper.getConvertedPrice` пересчитывает рубли в валюту аккаунта;
  `getPriceRtb`/`getPriceRtf` выбирают формат и иконку площадки и используют пересчёт как одну из
  веток.
- `#gdd-payment-channels`: `openPaymentWindow` выбирает канал; `BtnPaymentOvermobileSDK`,
  `BtnPaymentYookassa`, `PaymentMethodsPopup.UIPaymentButtons` — оплата в конкретном канале.
- `#gdd-offers`: `Offers.FLASH_LIST` — окно получения по id оффера; `DonateSection.UIMain` — какой
  оффер показан во вкладке.

<a id="cls-shoppopup"></a>
### `ShopPopup` (`src/views/home_screen/popups/shop/ShopPopup.ts`)

Окно магазина. Поле `data: ShopPopupJSON` — ответ `/ingame/shop`, его читает `DonateSection`.
Конфиг `ShopPopupConfig` пустой.

- `static publish(screen, config)` ([#gdd-shop-entry](game-design/shop-gdd.md#gdd-shop-entry)) — `requestData()` → `loadAssets()` → публикация флеша. Ошибка
  запроса не обрабатывается: окно просто не откроется.
- `requestData()` — `/ingame/shop`, сохраняет ответ в `data`.
- `loadAssets()` — пакет `ShopScreen` с индикатором загрузки.
- `onCreate()` — строит окно, вызывает `checkPurchasedOffers()` и `showDonateSection()`,
  подписывается на изменение уведомлений аккаунта (`onNotificationChange`).
- `onDestroy()` — отписка от уведомлений.
- `UIMain()` — фон, `TabSelector` с одной вкладкой `shopScreen.tab3` («ЗОЛОТО»), слот `section`;
  ширина вкладок пересчитывается после каждого обновления раскладки (не шире 150).
- `checkPurchasedOffers()` ([#gdd-take-reward](game-design/shop-gdd.md#gdd-take-reward)) — если `data.offers.purchased` не пуст, берёт первый оффер и вызывает
  его окно из `Offers.FLASH_LIST`; закрытие окна → `requestPurchasedOffers()`. Оффер без записи в
  таблице молча пропускается.
- `requestPurchasedOffers()` ([#gdd-take-reward](game-design/shop-gdd.md#gdd-take-reward)) — `/ingame/shop/purchased`, обновляет `data.offers.purchased` и снова
  вызывает `checkPurchasedOffers()` (цикл до пустого списка).
- `handleUserNotifications()` ([#gdd-purchase-confirm](game-design/shop-gdd.md#gdd-purchase-confirm)) — на любое изменение уведомлений аккаунта: если счётчик
  `purchasedOfferId` больше нуля — `requestPurchasedOffers()` ([#tradeoffs](#tradeoffs) п.1).
- `showDonateSection()` — кладёт `DonateSection` в слот.
- `showOffersSection()` — кладёт пустой `OffersSection`; нигде не вызывается.
- `getAsGameFlash()` — теги `LOWER_FLASH_TAG` и `"ShopPopup"`.
- Своей кнопки закрытия у окна нет; закрывает его `Footer`: кнопка «Домой» (`flashOverlay.clear()`)
  или повторное нажатие «МАГАЗИН» (`flashOverlay.removeAll("ShopPopup")`).

<a id="cls-donatesection"></a>
### `DonateSection` (`src/views/home_screen/popups/shop/DonateSection.ts`)

Вкладка «ЗОЛОТО»: вертикальный скролл шириной 390 с сеткой в 3 колонки.

- `UIMain()` ([#gdd-offers](game-design/shop-gdd.md#gdd-offers)) — берёт `popup.data.offers.list[0]` как `BundleOfferJSON`; если его `id === 1`, рисует
  карточку на каждый пакет ([#tradeoffs](#tradeoffs) п.4).
- `UIDonateGold(id, bundle)` ([#gdd-gold-bundles](game-design/shop-gdd.md#gdd-gold-bundles)) — карточка 130×184:
  - фон по номеру пакета: `n = 1..3` синий, `4` фиолетовый, `5` золотой, остальные (`0`) серый;
  - картинка `atlas/shop_screen/gold/<n>.png` (у `n = 2` сдвиг на 5 px);
  - количество — `rewards[0].count` с иконкой `atlas/ui/header/golden_coins_icon.png`, подарок — `rewards[1].count`, если вторая награда есть
    (`offers.gift`, «{0} В ПОДАРОК»);
  - цена — `PaymentHelper.getPriceRtf(price)`;
  - нажатие — `PaymentHelper.openPaymentWindow(price, id, n, translate("offers.name." + id), screen)`.

<a id="cls-offerssection"></a>
### `OffersSection` (`src/views/home_screen/popups/shop/OffersSection.ts`)

Заготовка вкладки офферов: только фон. Создаётся лишь из неиспользуемого
`ShopPopup.showOffersSection()` — кандидат на удаление ([#tradeoffs](#tradeoffs) п.10).

<a id="cls-offers"></a>
### `Offers` (`src/views/home_screen/popups/shop/Offers.ts`)

`static FLASH_LIST: {[offerId]: (screen, data, onClose) => void}`
([#gdd-offers](game-design/shop-gdd.md#gdd-offers)) — какое окно показать для
оплаченного оффера. Сейчас одна запись: `1` → `GoldenCoinsOffer.publish` с `onExit = onClose`.

<a id="cls-goldencoinsoffer"></a>
### `GoldenCoinsOffer` (`src/views/home_screen/popups/shop/offers/GoldenCoinsOfferPopup.ts`)

Окно «ПОЗДРАВЛЯЕМ С ПОКУПКОЙ!» для оффера золота. Имя класса не совпадает с именем файла
([#tradeoffs](#tradeoffs) п.11).

- Конструктор — выбирает `target`: первый пакет оффера с `canTake = true`.
- `UIContent()` — картинка пакета `gold/<n>.png`, сумма всех `rewards[].count`, кнопка
  `global.take` («Забрать»). Иконка золота — `atlas/ui/header/golden_coins_icon.png`, заголовок кеглем 17.
- `BtnTake()` ([#gdd-take-reward](game-design/shop-gdd.md#gdd-take-reward)) — `sendButtonRequest("/ingame/shop/takePurchasedOffer", {id, n})`. Успех: золото из
  ответа (`RewardUtils.getResource`) удерживается в сумке под тегом
  `GoldenCoinsOffer::RESOURCE_GOLDEN_COINS`, `FlyIconsAnimation.HEADER_GOLDEN_COINS` (5 иконок) из
  центра окна в шапку, по окончании — `releaseHold`; окно закрывается. Ошибка — пустой `catch`
  ([#tradeoffs](#tradeoffs) п.3).
- `onDestroy()` — вызывает `config.onExit` (у `ShopPopup` это повторный запрос `purchased`).
- `getAsGameFlash()` — `bgClick` пустой: закрыть окно можно только кнопкой «Забрать».

<a id="cls-paymenthelper"></a>
### `PaymentHelper` (`src/utils/PaymentHelper.ts`)

Статический помощник оплаты; вызывается из `DonateSection` и `PaymentMethodsPopup`.

- `openPaymentWindow(price, offerId, bundleId, name, screen, registerFirst = true)`
  ([#gdd-payment-channels](game-design/shop-gdd.md#gdd-payment-channels)) — проверка
  регистрации (иначе `ConnectPopup` с пустыми колбэками), код товара, выбор канала по
  `IntegrationUtils.getSocialPortal()` (см. [путь покупки](#lifecycle), п.4). Переменные
  `currency`, `convertedPrice`, `picUrl` вычисляются и не используются.
- `getProductCode(price, offerId, bundleId)` — `"offer_" + price + "_" + offerId + "_" + bundleId`.
- `getConvertedPrice(rubPrice)` ([#gdd-price-display](game-design/shop-gdd.md#gdd-price-display)) — цена × `shopCurrencyRate` с округлением вверх до копейки; при
  курсе < 1 — «красивые» цены: до 0,25 → 0,25; до 1 → x,x9; до 5 → кратно 0,5 минус 0,01; выше —
  кратно 1 минус 0,01.
- `BtnPaymentOvermobileSDK(code)` ([#gdd-payment-channels](game-design/shop-gdd.md#gdd-payment-channels)) — `OVMSDK.purchase(code, account.nid)` с индикатором загрузки; на
  RuStore индикатор снимается принудительно через 10 с. Результат только пишется в консоль.
- `BtnPaymentYookassa(price, code, name, email, screen, pid)`
  ([#gdd-payment-channels](game-design/shop-gdd.md#gdd-payment-channels)) — подгрузка
  `checkout-widget.js` (один раз), `PaymentPopup`, запрос токена, создание
  `YooMoneyCheckoutWidget` (для карт — способы `bank_card` и `mir_pay`, иначе только выбранный),
  рендер в `#yookassa`, по событию `complete` окно закрывается. Ошибка запроса или ответ не `ok` —
  текст `offers.paymentError` в окне; ошибка самого виджета — только скрытие индикатора.
- `getPriceRtb(price, options)` / `getPriceRtf(price, options)`
  ([#gdd-price-display](game-design/shop-gdd.md#gdd-price-display)) — цена для показа: ОК — `<price> OK`;
  ВК — голоса `IntegrationUtils.getVKPrice(price)` (`ceil(price / 7)`); иначе по
  `shopCurrency`: RUB (с иконкой рубля), USD `$x.xx`, EUR `€x,xx`, YAN (Яндекс), HOP (Playhop),
  RUBY (GamePush), прочие — `<цена> <код валюты>`. Шрифт цены — `Const.FONT_HEAVY` (жирная) или
  `Const.FONT_MEDIUM`, кегль по умолчанию 15.

<a id="cls-paymentmethodspopup"></a>
### `PaymentMethodsPopup` (`src/views/home_screen/popups/shop/PaymentMethodsPopup.ts`)

Окно «СПОСОБЫ ОПЛАТЫ» (заголовок кеглем 17, как у `PaymentPopup`; только валюта RUB без Overmobile SDK). Конфиг: `name`, `price`, `code`,
`onExit`, `onSuccess` (`onSuccess` нигде не вызывается).

- Enum `YookassaPids` — `bank_card`, `yoo_money`, `sberbank`, `sbp`, `mir_pay`.
- `UIPaymentButtons()` ([#gdd-payment-channels](game-design/shop-gdd.md#gdd-payment-channels)) — кнопки `ButtonPresets.BTN_PAYMENT`: карты, СБП, SberPay, ЮMoney (кнопка
  мобильного платежа закомментирована). Каждая → `PaymentHelper.BtnPaymentYookassa` с нужным `pid`.
- `UIContent()` — чекбокс «Хочу получать чеки на email адрес» и поле email (длина до
  `Globals.vars.UserEmailMaxLength`). Если у аккаунта уже есть `receiptEmail`, чекбокс включён и
  поле заполнено.
- `getReceiptEmail()` ([#gdd-receipt](game-design/shop-gdd.md#gdd-receipt)) — email, если чекбокс включён, иначе пустая строка. Формат на клиенте не
  проверяется.
- `BtnTestPayment(code)` — только dev-режим (`Globals.isDevTools()`), галочка в заголовке:
  `/ingame/devTools/offer {code}` — сервер проводит оплату без платёжной системы. Ответ
  игнорируется.
- `onDestroy()` — `config.onExit`. Закрыть окно можно только крестиком (`bgClick` пустой).

<a id="cls-paymentpopup"></a>
### `PaymentPopup` (`src/views/home_screen/popups/shop/PaymentPopup.ts`)

Окно «ОПЛАТА» (заголовок кеглем 17) 360×~510 с индикатором загрузки и DOM-блоком `Div` с `id` из конфига (`"yookassa"`),
куда виджет ЮKassa рисует форму. Закрывается крестиком или кликом по фону.

- `static publish(screen, {id})` — возвращает экземпляр, чтобы `PaymentHelper` мог показать ошибку.
- `hideLoading()`, `displayError(text)` — скрыть индикатор / показать текст ошибки.

<a id="cls-types"></a>
### Типы (`src/views/home_screen/popups/shop/shop.d.ts`)

- `ShopPopupJSON { offers: OffersJSON }`
- `OffersJSON { list: OfferJSON[]; purchased: OfferJSON[] }` — все активные офферы / оплаченные и не
  забранные.
- `OfferJSON { id }`; `BundleOfferJSON extends OfferJSON { bundles: BundleJSON[] }`
- `BundleJSON { n, price, canTake, rewards: ItemJSON[] }`

<a id="client-contract"></a>
### Контракт с сервером

| Запрос / событие | Кто шлёт | Payload | Ответ, как использует клиент |
|---|---|---|---|
| `/ingame/shop` | `ShopPopup.requestData` | `{}` | `{offers: {list, purchased}}` → `ShopPopup.data` |
| `/ingame/shop/purchased` | `ShopPopup.requestPurchasedOffers` | `{}` | `{purchased: OfferJSON[]}` |
| `/ingame/shop/takePurchasedOffer` | `GoldenCoinsOffer.BtnTake` | `{id, n}` | `{rewards: ItemJSON[]}`; ошибка — без payload |
| `/ingame/shop/yookassaPaymentToken` | `PaymentHelper.BtnPaymentYookassa` | `{price, name, code, email, pid}` | `{token}` |
| `/ingame/devTools/offer` | `PaymentMethodsPopup.BtnTestPayment` | `{code}` | не читается |
| уведомление `purchasedOfferId` | сервер (push `NotificationJSON`) | `value` = id оффера | `Footer` — значок; `ShopPopup` — запрос `purchased` |

Серверная сторона (для контекста, не правится здесь; подробно —
`/workspace/server/.claude/docs/offers-architecture.md`): `ShopPage`
(`/workspace/server/game/src/main/java/com/linkedgames/game/pages/ws/ingame/ShopPage.java`),
`OffersUserComponent` и `GoldenCoinsOffer` в `model/offers/`. Сервер разбирает код товара
`offer_<price>_<offerId>_<n>` (части 2 и 3), сверяет цену пакета, при оплате добавляет номер пакета
в список оплаченных и ставит уведомление; оффер золота активируется всегда
(`resetOffers`). Пакеты сервера: `n = 0..5`, цены 150 / 450 / 1500 / 3000 / 6000 / 12000 ₽, золото
1500 / 4500 / 15000 / 30000 / 60000 / 120000, подарочной второй награды сейчас нет. Цены совпадают с
ГДД ([#gdd-gold-bundles](game-design/shop-gdd.md#gdd-gold-bundles)).

<a id="tradeoffs"></a>
## 8. Принятые уязвимости, компромиссы и известные проблемы

Пункты найдены анализом кода. Решение пользователя есть только по п.7; остальные ждут решения.

1. **Дубли окна награды.** `ShopPopup.ts:128-132`: `handleUserNotifications` срабатывает на любое
   изменение уведомлений аккаунта (почта, достижения, коллекции), пока счётчик `purchasedOfferId`
   больше нуля, и через `checkPurchasedOffers` (`:97-106`) публикует ещё одно окно
   `GoldenCoinsOffer`, даже если такое уже открыто. Повторное «Забрать» по тому же пакету сервер
   отклонит, а окно останется висеть (п.3).
2. **Падение после закрытия магазина.** `ShopPopup.ts:108-114`: если `ShopPopup` уже уничтожен
   (кнопка «Домой» в `Footer.ts:175` очищает все флеши, в том числе окно награды, и его `onExit`
   вызывает `requestPurchasedOffers`), `WSSocket.sendRequest` для мёртвого `layout` возвращает
   `Promise.resolve()` без ответа, и строка `:110` падает на `response.purchased` (TypeError).
3. **Ошибка «Забрать» молчит, окно не закрыть.** `GoldenCoinsOfferPopup.ts:138-140` — пустой
   `catch`; `:145-147` — пустой `bgClick`, крестика нет. При ошибке игрок остаётся с окном, которое
   не закрывается ничем, кроме кнопки «Домой».
4. **Вкладка «ЗОЛОТО» берёт первый оффер списка.** `DonateSection.ts:60-65`: `list[0]` считается
   оффером золота. Пустой список — падение на `offerData.id`; другой оффер первым (сервер собирает
   список из `HashMap`) — пустая вкладка.
5. **Валюта без канала оплаты.** `PaymentHelper.ts:56-64`: для валют, отличных от RUB, без
   Overmobile SDK нажатие на пакет ничего не делает, хотя цена в этой валюте показывается
   (`:183-205`). `:36-38` — `currency`, `convertedPrice`, `picUrl` вычисляются впустую.
6. **Покупка не продолжается после регистрации.** `PaymentHelper.ts:28-34`: `ConnectPopup` с пустыми
   `onSuccess`/`onExit`; после регистрации игрок должен снова нажать на пакет.
7. **ЮKassa отключена на сервере.** `ShopPage.java:56-61` (сервер): `if (true)` всегда отвечает
   ошибкой на `/yookassaPaymentToken`. На клиенте все четыре кнопки `PaymentMethodsPopup` приводят
   к «Не удалось начать процесс оплаты» (`PaymentHelper.ts:134-159`). Решение пользователя 2026-10-17:
   отложенное исправление; в ГДД — [О10](game-design/shop-gdd.md#gdd-open).
8. **Email для чека.** `PaymentMethodsPopup.ts:223-225`: формат email не проверяется; введённый
   адрес не записывается в `Globals.account.receiptEmail`, при следующем открытии окна подставится
   старое значение.
9. **Значение уведомления — id оффера, а не счётчик.** `Notifications.ts:13-16` читает
   `purchasedOfferId` как число, сервер кладёт туда id оффера (`OffersUserComponent.java:90-91`) или
   `1` при входе (`GoldenCoinsOffer.java:62-64`); работает, пока id > 0. Сервер снимает уведомление
   в начале `takePurchasedOffer` (`OffersUserComponent.java:102`), поэтому при двух оплаченных
   пакетах значок на кнопке магазина пропадает после первого «Забрать», хотя второй пакет ещё не
   забран. Сервер также не шлёт повторный push, если значение не изменилось
   (`offers-architecture.md#tradeoffs` п.5): вторая оплата при горящем значке не доходит до открытого
   магазина ([О13](game-design/shop-gdd.md#gdd-open)).
10. **Неиспользуемый код и ключи.** `OffersSection.ts` целиком и `ShopPopup.showOffersSection`
    (`ShopPopup.ts:116-120`); пустой `ShopPopupConfig` (`:20-22`); `onSuccess` в
    `PaymentMethodsPopupConfig` (`PaymentMethodsPopup.ts:27`); `reject` в `loadAssets`
    (`ShopPopup.ts:135`); ключи `shopScreen.tab0..tab2`, `offers.goldenOffer.*`,
    `offers.price.fs/moco/rbk/telegram` в `ru.json` нигде не читаются. Кандидаты на удаление.
11. **Имена.** Файл `GoldenCoinsOfferPopup.ts`, класс `GoldenCoinsOffer` (совпадает с серверным
    классом оффера). Тег hold `GoldenCoinsOffer::RESOURCE_GOLDEN_COINS` используют ещё
    `AchievementLine`, `CollectionAlbumCard`, `CollectionsUSSROperationsSection`, `AirDrop` — см.
    [bag-architecture.md](bag-architecture.md) (одновременные hold под одним тегом).
12. **Награда только в открытом магазине.** Оплата, подтверждённая при закрытом магазине,
    показывается лишь значком; окно получения откроется при следующем входе в магазин. Вопрос в
    ГДД — [О13](game-design/shop-gdd.md#gdd-open).
13. **Смежное, не эта область.** Кнопка «КУПИТЬ ЗОЛОТО» в `TrainBuySchemesPopup` без обработчика
    (переход в магазин закомментирован, `TrainBuySchemesPopup.ts:108`) — описано в
    [train-architecture.md](train-architecture.md).
14. **Подвал и параллельные окна.** Кнопки подвала `Footer` переработаны после merge (вкладки
    «Дом», «Бой», «Клан», «Магазин»; «Клан» вместо «События», окно клана — зона кланов fix, здесь не
    описывается). Открытое окно военной базы и чата сбрасывают подсветку вкладки
    (`Footer.onFlashActivated`), поэтому подсветка «Магазин» может не соответствовать открытому
    окну; при закрытии `ShopPopup` кнопкой «Домой» активной становится вкладка «Дом».

<a id="gdd-link"></a>
## 9. Связь с ГДД

ГДД: [`game-design/shop-gdd.md`](game-design/shop-gdd.md), статус «черновик, по коду». Пользователь не подтвердил ни
одного правила из кода, поэтому разделы ГДД содержат только тему и ссылки на пункты
[#gdd-open](game-design/shop-gdd.md#gdd-open).

| Раздел ГДД | Где в клиенте | Пункты `#gdd-open` |
|---|---|---|
| [#gdd-shop-entry](game-design/shop-gdd.md#gdd-shop-entry) | `Footer` (кнопка), `ShopPopup.UIMain` | О1 |
| [#gdd-gold-bundles](game-design/shop-gdd.md#gdd-gold-bundles) | `DonateSection.UIDonateGold` | О2, О3 |
| [#gdd-offers](game-design/shop-gdd.md#gdd-offers) | `Offers.FLASH_LIST`, `DonateSection.UIMain` | О4, О5, О6 |
| [#gdd-payment-channels](game-design/shop-gdd.md#gdd-payment-channels) | `PaymentHelper.openPaymentWindow`, `BtnPaymentOvermobileSDK`, `BtnPaymentYookassa`, `PaymentMethodsPopup` | О7, О8, О9, О10 |
| [#gdd-price-display](game-design/shop-gdd.md#gdd-price-display) | `PaymentHelper.getConvertedPrice`, `getPriceRtb` | О11, О12 |
| [#gdd-purchase-confirm](game-design/shop-gdd.md#gdd-purchase-confirm) | `ShopPopup.handleUserNotifications`, `Footer.handleShopNotifications` | О13, О14 |
| [#gdd-take-reward](game-design/shop-gdd.md#gdd-take-reward) | `ShopPopup.checkPurchasedOffers`, `GoldenCoinsOffer.BtnTake` | О15, О16 |
| [#gdd-receipt](game-design/shop-gdd.md#gdd-receipt) | `PaymentMethodsPopup.UIContent`, `getReceiptEmail` | О17 |

<a id="file-map"></a>
## 10. Карта файлов компонента

### Файлы прямого влияния

- `src/views/home_screen/popups/shop/ShopPopup.ts` — окно магазина, офферы к получению.
- `src/views/home_screen/popups/shop/DonateSection.ts` — вкладка «ЗОЛОТО».
- `src/views/home_screen/popups/shop/OffersSection.ts` — пустая вкладка офферов (не используется).
- `src/views/home_screen/popups/shop/Offers.ts` — таблица окон получения по id оффера.
- `src/views/home_screen/popups/shop/offers/GoldenCoinsOfferPopup.ts` — окно получения золота.
- `src/views/home_screen/popups/shop/PaymentMethodsPopup.ts` — способы оплаты ЮKassa, email чека.
- `src/views/home_screen/popups/shop/PaymentPopup.ts` — контейнер виджета ЮKassa.
- `src/views/home_screen/popups/shop/shop.d.ts` — типы ответа магазина.
- `src/utils/PaymentHelper.ts` — платёжные каналы, код товара, отображение цены.
- `assets-src/atlas/shop_screen/` — фоны карточек, картинки пакетов золота `gold/0..5.png`
  (пакет `ShopScreen`).
- `assets-src/atlas/ui/payment/` — кнопки и иконки способов оплаты.
- `assets-src/atlas/ui/icons/payments/` — иконки валют в цене.

### Файлы косвенного влияния

- `src/shared/footer/Footer.ts` — кнопка «МАГАЗИН» (`ShopPopup.publish`, повторное нажатие закрывает
  магазин, блокируется до конца туториала), значок по `purchasedOfferId`, закрытие магазина
  кнопкой «Домой».
- `src/shared/notifications/Notifications.ts` — константа `PURCHASED_OFFER_ID`, чтение счётчика.
- `src/plain/user/User.ts` — `notifications` и подписка на их изменение, `reg`, `receiptEmail`,
  `shopCurrency`, `shopCurrencyRate`, `nid`.
- `src/SceneImpl.ts` — приём push-уведомлений аккаунта (`onReceiveNotification`).
- `src/types/interfaces.d.ts` — зависимость: `NotificationJSON`, `ItemJSON`.
- `src/plain/IntegrationUtils.ts` — зависимость: площадка, валюта, курс, Overmobile SDK, цена в
  голосах ВК.
- `src/views/home_screen/popups/settings/ConnectPopup.ts` — регистрация перед покупкой.
- `src/plain/user/UserBag.ts` — hold/release золота при получении награды.
- `src/shared/animations/FlyIconsAnimation.ts` — полёт золота в шапку.
- `src/plain/RewardUtils.ts`, `src/plain/items/ItemId.ts` — зависимость: поиск золота в наградах.
- `src/presets/ButtonPresets.ts` — `BTN_PAYMENT`, `BTN_GREEN`.
- `src/presets/PanelsPresets.ts`, `src/presets/InputTextPresets.ts`, `src/shared/CheckBox.ts`,
  `src/shared/TabSelector.ts` — зависимость: элементы окон.
- `src/plain/globals/WSSocket.ts` — зависимость: `sendRequest`/`sendButtonRequest` (поведение для
  уничтоженного `layout`, [#tradeoffs](#tradeoffs) п.2).
- `src/views/home_screen/popups/train/TrainBuySchemesPopup.ts` — использует пакет `ShopScreen`, фоны
  `shop_screen/*`, ключи `shopScreen.*`; закомментированный переход в магазин.
- `assets-src/atlas/ui/header/golden_coins_icon.png` — иконка золота в карточках и окне награды.
- `src/views/home_screen/popups/profile/achievements/AchievementLine.ts`,
  `src/views/home_screen/popups/profile/collections/collection_type/CollectionAlbumCard.ts`,
  `src/views/home_screen/popups/profile/collections/collection_section_type/CollectionsUSSROperationsSection.ts`,
  `src/views/home_screen/campaign/AirDrop.ts` — общий тег hold `GoldenCoinsOffer::RESOURCE_GOLDEN_COINS`.
- `src/views/home_screen/popups/campaign/CampaignPopup.ts` — имя флеш-слоя `"ShopPopup"`
  (скопированная строка, к магазину отношения не имеет).
- `tools/src/config.yaml` — пакет `ShopScreen` (`shop_screen`).
- `assets-src/raw/lang/ru/ru.json` — ключи `offers.*`, `shopScreen.*`, `footer.shop`.
- Сервер (контекст контракта): `ShopPage.java`, `model/offers/OffersUserComponent.java`,
  `model/offers/list/GoldenCoinsOffer.java`, `DevToolsPage.java` (`/offer`),
  `model/notifications/NotificationId.java`.
