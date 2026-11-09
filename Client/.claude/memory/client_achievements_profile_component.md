---
name: client-achievements-profile-component
description: "Документация компонента 'Достижения' (Профиль → Достижения): назначение, референсы, паттерны, список классов и методов, принятые компромиссы. auto-create — составлено client-analyst-lead путём анализа существующего кода (не по итогам разработки), доверие ниже, чем к документации по факту реализации."
metadata: 
  node_type: memory
  type: reference
  category: Достижения
  modified: 2026-09-25T07:46:32.514Z
  originSessionId: unknown
---

# Документация компонента "Достижения"

Полный документ лежит в `/workspace/client/.claude/docs/achievements-architecture.md` (8 разделов по
принятому в проекте стандарту: описание, референсы, паттерны, список классов, якоря, оглавление,
описание методов, принятые компромиссы).

Статус: **auto-create** — все разделы 1–8 составлены `client-analyst-lead` путём анализа уже написанного
кода, а не по итогам отчёта разработчиков. Доверять с осторожностью, при использовании сверяться с
актуальным кодом, а не только с документом.

Область: `src/views/home_screen/popups/profile/achievements/**` (включая `achievement.d.ts`,
`AchievementsSection.ts`, `AchievementsListSection.ts`, `AchievementsTypeSection.ts` (абстрактный),
`achievements_type/AchievementsAirplanesHuntSection.ts`, `achievements_type/AchievementsTanksHuntSection.ts`,
`achievements_type/AchievementType.ts`, `AchievementLine.ts`, `AchievementRank.ts`), а также
`src/shared/header/presets/HeaderAchievementsBar.ts` (управление показом тоста) и
`src/views/popups/AchievementCompletePopup.ts` (тост о выполнении достижения).

Объём документа сокращён по явному запросу: вёрстка/расположение UI-элементов не описываются, только
(1) какие данные приходят с сервера и методы их обработки, (2) какие элементы обновляются/пересоздаются,
(3) механизм показа `AchievementCompletePopup`.

**Классы и компоненты:**

- `AchievementsSection` — корневой контейнер вкладки, маршрутизация через `LayoutSlot`
- `AchievementsListSection` — список двух категорий (`tanksHunt`/`airplaneHunt`) с бейджами
- `AchievementsTypeSection` (абстрактный) — экран одной категории со скроллируемым списком
- `AchievementsAirplanesHuntSection` / `AchievementsTanksHuntSection` — наследники
- `AchievementLine` — один пункт списка, отвечает за запрос обновлений и частичное обновление UI
- `HeaderAchievementsBar` — пресет шапки, управляет показом тоста
- `AchievementCompletePopup` — тост поверх экрана, автоскрытие через 5 секунд
- Domain-типы: `AchievementsJSON`, `AchievementJSON`, `AchievementDoneJSON` (в `achievement.d.ts`)

**Использованные паттерны:**

- `PreloadableLayout` (`onPreload`/`onCreate`/`onDestroy`) в `AchievementsTypeSection`
- Подписка на серверные push-события (см. `.claude/docs/server-push-events-subscription.md`); одновременно используются два подхода к одному событию `g/ws/events/achievements/update` — это зафиксированный факт кода
- `LayoutSlot` для переключения между секциями

**Компромиссы:**

- Дублирование подписки на `g/ws/events/achievements/update` (напрямую в `AchievementLine` и через `GameEvents.ACHIEVEMENTS_EVENT` в `HeaderAchievementsBar`)
- Показ `AchievementCompletePopup` не является очередью — несколько тостов накапливаются одновременно, а не показываются по очереди
