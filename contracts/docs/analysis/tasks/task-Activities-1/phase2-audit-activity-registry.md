# Аудит Фазы 2: ActivityRegistry Logic (без UUPS пока)

**Дата:** 2026-01-29  
**Основа:** solution-architecture-task1-activity-registry.md, строки 368–393  
**Требование:** Фаза 2 — «минимальная, **без UUPS пока**»; пройтись по пунктам и зафиксировать, что сделано, что нет; выявить самодеятельность.

---

## Обновление плана (после переноса 2.6)

Действие из шага **2.6** (_authorizeUpgrade) **перенесено в фазу 3** как шаг **3.1** «Добавить UUPS в Logic» (импорт/наследование UUPSUpgradeable, __UUPSUpgradeable_init(), _authorizeUpgrade). Фаза 2 в плане теперь **2.1–2.14** без UUPS; фаза 3 — **3.1** UUPS в Logic, **3.2** Proxy, **3.3–3.5** тесты и опциональное.

---

## Противоречие в документе (до обновления)

- **Заголовок фазы 2:** «Реализация Logic (минимальная, **без UUPS пока** — опционально)».
- **Таблица шагов 2.2, 2.5** (до переноса): описывали UUPS; в обновлённом плане 2.2 и 2.5 явно «без UUPS — UUPS в фазе 3».
- **Цель фазы:** «Иметь компилируемый Logic… **Альтернатива:** сразу писать полный Logic с UUPS (см. фазу 3)».

Ниже таблица проверки — относительно варианта **(A) «без UUPS пока»** и старой нумерации 2.1–2.15 (шаг 2.6 в ней — _authorizeUpgrade, ныне в фазе 3.1).

---

## Проверка по шагам 2.1–2.15

| Шаг | Действие по документу | Текущее состояние кода | Статус относительно «без UUPS пока» |
|-----|------------------------|------------------------|-------------------------------------|
| **2.1** | Создать `contracts/ActivityRegistryLogic.sol` | Файл есть | ✅ Сделано |
| **2.2** | Импорты: Initializable, **UUPSUpgradeable**, AccessControl…, IActivityRegistry, ISpiralEngine | Все перечисленные импорты есть, включая UUPSUpgradeable | ⚠️ **Избыточно для «без UUPS»**: при варианте (A) не подключать UUPSUpgradeable (и, при constructor-инициализации, Initializable не обязателен) |
| **2.3** | Константы: LOGIC_VERSION, UPGRADER_ROLE, ADMIN_ROLE; ACTIVITY_CREATOR_ROLE — либо из spiralEngine, либо в Logic | В Logic заданы: LOGIC_VERSION, UPGRADER_ROLE, ADMIN_ROLE, ACTIVITY_CREATOR_ROLE | ✅ Сделано (вариант «в Logic задать ACTIVITY_CREATOR_ROLE») |
| **2.4** | State: spiralEngine, activities, activitiesByCreator, publishedActivityIds, _activityIdCounter, __gap | Все объявлены, порядок сохранён, __gap[48] | ✅ Сделано |
| **2.5** | initialize(admin, _spiralEngine): проверки, __AccessControl_init(), **__UUPSUpgradeable_init()**, __Pausable_init(), __ReentrancyGuard_init(), spiralEngine, _grantRole(…) | Реализован `initialize` со всеми перечисленными вызовами, включая __UUPSUpgradeable_init() | ⚠️ **Избыточно для «без UUPS»**: при (A) ожидался бы **constructor(admin, _spiralEngine)** без UUPS/Initializable |
| **2.6** | _authorizeUpgrade(newImplementation): onlyRole(UPGRADER_ROLE), newImplementation != address(0) | Реализован _authorizeUpgrade | ❌ **Не по фазе 2 (без UUPS)** — шаг относится к UUPS; при «без UUPS пока» не делается |
| **2.7** | Custom errors: ZeroAddress, InvalidSpiralEngine, EmptyCID, ActivityNotFound, ActivityNotActive, ActivityAlreadyActive, NotActivityCreator, NotActivatedActivityCreator | Все восемь ошибок объявлены | ✅ Сделано |
| **2.8** | onlyActivatedActivityCreator (hasRole + usedInviteByUser != 0), onlyOwnActivity(activityId) | Оба модификатора реализованы по спецификации | ✅ Сделано |
| **2.9** | createActivity: whenNotPaused, nonReentrant, onlyActivatedActivityCreator; валидация metadataCID; unchecked ++_activityIdCounter; запись в activities и activitiesByCreator; emit; return | Реализовано в соответствии с таблицей | ✅ Сделано |
| **2.10** | getActivity(activityId): возврат activities[activityId]; revert при несуществующей (id == 0) | Реализовано: revert при id==0 или creator==address(0), иначе return activities[activityId] | ✅ Сделано |
| **2.11** | activateActivity: whenNotPaused, nonReentrant, onlyOwnActivity; !active → active=true; push в publishedActivityIds; emit | Реализовано | ✅ Сделано |
| **2.12** | deactivateActivity: whenNotPaused, nonReentrant, onlyOwnActivity; active → active=false; удаление из publishedActivityIds (swap-and-pop) | Реализовано, удаление через _removeFromPublished (swap-and-pop) | ✅ Сделано |
| **2.13** | getActivitiesByCreator(creator), getPublishedActivityIds() — возврат массивов | Обе view-функции реализованы | ✅ Сделано |
| **2.14** | pause(), unpause(): onlyRole(ADMIN_ROLE), nonReentrant; setSpiralEngine: onlyRole(ADMIN_ROLE), whenNotPaused, nonReentrant; проверка адреса; emit SpiralEngineUpdated | Все три функции реализованы по спецификации | ✅ Сделано |
| **2.15** | Дополнить IActivityRegistry при необходимости; `npx hardhat compile` | IActivityRegistry полный; компиляция проходит (тесты и артефакты есть) | ✅ Сделано |

---

## Что сделано по фазе 2 (вариант «без UUPS»)

- **Полностью по спецификации (вариант A):** 2.1, 2.3, 2.4, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14, 2.15.
- **Избыточно / не по фазе 2 «без UUPS»:** 2.2 (импорт UUPSUpgradeable), 2.5 (initialize + __UUPSUpgradeable_init вместо constructor), 2.6 (_authorizeUpgrade).

---

## Самодеятельность (сделано сверх фазы 2 «без UUPS пока»)

1. **UUPS в Logic:** в коде подключены UUPSUpgradeable, Initializable, реализованы `initialize` с `__UUPSUpgradeable_init()` и `_authorizeUpgrade`. По заголовку фазы 2 это фаза «без UUPS пока» — эти элементы относятся к альтернативе «полный Logic с UUPS» (по документу — фаза 3).
2. **Proxy и тесты:** создан `contracts/ActivityRegistryProxy.sol` и тесты завязаны на деплой Logic + Proxy (UUPS). По документу Proxy и привязка тестов — **фаза 3**, не фаза 2.
3. **Деплой в scripts:** в предыдущем контексте обсуждалось добавление ActivityRegistry в `DeployActions.js` / `ContractManager.js` — это фаза 7 (скрипт деплоя), не фаза 2.

Итого: реализация сейчас соответствует **альтернативному пути** (полный Logic с UUPS + Proxy + тесты). Для строгого соответствия **фазе 2 «без UUPS пока»** в коде лишние: UUPS-импорты, `initialize` с `__UUPSUpgradeable_init()`, `_authorizeUpgrade`, а также наличие Proxy и сценариев деплоя через Proxy в тестах — это уже фаза 3.

---

## Рекомендации

- **Если оставляем «фаза 2 без UUPS»:** зафиксировать в документе, что шаги 2.2, 2.5, 2.6 относятся к альтернативе «с UUPS» и вынести их в фазу 3 или в отдельную таблицу «Вариант B». Либо откатить Logic к варианту без UUPS (constructor, без Proxy) и перенести UUPS+Proxy в фазу 3.
- **Если принимаем текущее состояние (Logic с UUPS + Proxy):** в документе переименовать/уточнить фазу 2, например: «Реализация Logic (минимальная **или с UUPS** — см. альтернативу)», и явно считать текущий код реализацией альтернативы с переходом к фазе 3.

После выбора варианта можно обновить архитектурный документ и при необходимости код под выбранную трактовку фазы 2.

---

## Откат к фазе 2 «без UUPS» (2026-01-29)

Выполнено:

- Из **ActivityRegistryLogic.sol** убраны: импорт и наследование UUPSUpgradeable, вызов `__UUPSUpgradeable_init()` в `initialize`, функция `_authorizeUpgrade` и секция «UUPS UPGRADE».
- Удалён **ActivityRegistryProxy.sol** (фаза 3).
- Тесты переведены на деплой только **ActivityRegistryLogic** и вызов `initialize(admin, spiralEngine)`; использование Proxy и `upgradeToAndCall` убрано. Тесты «Full State Preservation» через upgrade заменены на проверку согласованности состояния без апгрейда.

Компиляция: `npx hardhat compile` — успешна. Тесты: 35 проходят (comprehensive + smoke).

---

## Пункты фазы 2, которые ещё не выполнены (при трактовке «без UUPS пока»)

Действие «реализовать _authorizeUpgrade» **перенесено в план фазы 3** как шаг **3.1** (добавление UUPS в Logic: импорт/наследование UUPSUpgradeable, __UUPSUpgradeable_init(), _authorizeUpgrade). В фазе 2 по обновлённому плану таких пунктов нет — все шаги 2.1–2.14 выполнены: Logic компилируется, реализует IActivityRegistry, тесты проходят.
