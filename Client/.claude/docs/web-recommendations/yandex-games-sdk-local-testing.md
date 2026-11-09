# Яндекс Игры SDK: локальное тестирование

- [Локальный тест SDK через sdk-dev-proxy (prod и dev)](#web-ysdk-dev-proxy)

## Локальный тест SDK через sdk-dev-proxy (prod и dev) {#web-ysdk-dev-proxy}

- **Задача:** проверить ysdk.shortcut.canShowPrompt/showPrompt и другие вызовы SDK локально (http://localhost:8080, webpack) до выкладки.
- **Ключевые слова:** Yandex Games, Яндекс Игры, ysdk, SDK, shortcut, ярлык, canShowPrompt, showPrompt, localhost, sdk-dev-proxy, dev-mode, mocks, game_url, debug-mode, черновик, локальный запуск.
- **Рекомендация:** официальный npm-пакет `@yandex-games/sdk-dev-proxy`, два режима.
  - Dev (моки, без регистрации и черновика): `npx @yandex-games/sdk-dev-proxy -h <адрес локального сервера> --dev-mode=true` (или `-p <папка с игрой>`); игра открывается по `https://localhost`. Мок shortcut задаётся в адресе: `?mocks={"canShowPrompt":true,"isAuthorized":true,"lockedOrientation":"landscape"}`.
  - Prod (реальная платформа, нужен черновик): `npx @yandex-games/sdk-dev-proxy -h <адрес> --app-id=<ID черновика>` либо вручную: открыть игру-черновик на yandex.ru/games и добавить `?game_url=https://localhost` (принимается только домен localhost). Отладка: `&debug-mode=16` или кнопка «Открыть с debug-панелью» в консоли.
  - Параметры пакета: `--host/-h`, `--path/-p`, `--port` (по умолчанию 8080), `--app-id/-i`, `--csp/-c`, `--log/-l`, `--tld`, `--dev-mode`.
- **Плюсы:** dev — без черновика, без CSP-ограничений, вызовы SDK логируются по модулям, `canShowPrompt` управляется моком; prod — настоящий SDK и платформа.
- **Минусы:** в документации локального запуска нет описания, как мок отвечает на `showPrompt` (outcome) и работает ли shortcut в prod-локальном режиме; в prod-режиме нужен черновик и CSP для внешних хостов; про HTTPS/сертификаты для localhost в документе ничего нет (dev и `game_url` указывают `https://localhost`). Документация shortcut: доступность зависит от устройства, правил браузера и ограничений платформы; страница не описывает тестирование и локальный режим.
- **Применимость к проекту:** webpack-сервер на :8080 совпадает с портом по умолчанию — прокси ставится перед ним через `-h`; нужно проверить конфликт портов (прокси тоже 8080 по умолчанию, задать `--port`). Игра грузит `https://sdk.games.s3.yandex.net/sdk.js`; как прокси подменяет загрузку SDK при использовании этого абсолютного URL (вместо относительного `/sdk.js`) в источниках не сказано — проверить на практике. Конфликтов с CLAUDE.md нет. `showPrompt` вызывать из клика пользователя; `canShowPrompt()` возвращает объект с `canShow`.
- **Источники:** https://yandex.ru/dev/games/doc/ru/concepts/local-launch — 2026-10-26; https://yandex.ru/dev/games/doc/ru/sdk/sdk-shortcut — 2026-10-26; https://yandex.ru/dev/games/doc/ru/sdk/sdk-about — 2026-10-26.
- **Статус:** не применялось
