# Ретроспективный анализ выполнения фазы 3: ActivityRegistry UUPS

**Дата:** 2026-01-29  
**Основа:** solution-architecture-task1-activity-registry.md, фаза 3 (шаги 3.1–3.5)  
**Цель:** По каждому из 5 пунктов — что было задано, что сделано, расхождения, качество, выводы.

---

## 3.1 — Добавить UUPS в Logic

**Задано по плану:**
- Импорт и наследование UUPSUpgradeable.
- В `initialize` добавить вызов `__UUPSUpgradeable_init()`.
- Реализовать `_authorizeUpgrade(address newImplementation)` internal override: `onlyRole(UPGRADER_ROLE)`, проверка `newImplementation != address(0)`, при нуле — `revert ZeroAddress`.
- **Артефакт:** Logic с UUPS, компилируется.

**Сделано:**
- В `ActivityRegistryLogic.sol`: добавлен `import .../UUPSUpgradeable.sol`; контракт наследует `UUPSUpgradeable`; в `initialize` после `__AccessControl_init()` вызывается `__UUPSUpgradeable_init()`; реализована секция «UUPS UPGRADE» с `_authorizeUpgrade(address newImplementation) internal override onlyRole(UPGRADER_ROLE) view { if (newImplementation == address(0)) revert ZeroAddress(); }`.
- Компиляция проходит.

**Расхождения:** Нет. Спецификация выполнена полностью.

**Качество:** Соответствует паттерну OpenZeppelin UUPS; порядок вызовов init корректен; `view` в `_authorizeUpgrade` допустим (модификатор только проверяет роль и адрес).

**Выводы:** Пункт 3.1 выполнен без отклонений. Повторное использование того же паттерна, что в ProductRegistryLogic/SpiralEngineLogic, упростило проверку.

---

## 3.2 — Создать ActivityRegistryProxy.sol

**Задано по плану:**
- Создать `contracts/ActivityRegistryProxy.sol`.
- Наследование ERC1967Proxy.
- Конструктор `(address implementation, bytes memory initData)` с вызовом `ERC1967Proxy(implementation, initData)`.
- **Артефакт:** ActivityRegistryProxy.sol создан.

**Сделано:**
- Файл `contracts/ActivityRegistryProxy.sol` создан.
- Импорт `@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol`.
- Контракт наследует `ERC1967Proxy`; конструктор `constructor(address implementation, bytes memory initData) ERC1967Proxy(implementation, initData) {}`.
- NatSpec: краткое описание, автор, security-contact.

**Расхождения:** Нет. Сигнатура и поведение совпадают с планом.

**Качество:** Минимальный proxy без лишней логики; стиль согласован с ProductRegistryProxy (короче комментариев — достаточно для задачи).

**Выводы:** Пункт 3.2 выполнен. Использование ProductRegistryProxy как образца исключило ошибки в конструкторе.

---

## 3.3 — Компиляция Logic+Proxy, перевод тестов на Proxy+Logic

**Задано по плану:**
- Убедиться, что компилируются ActivityRegistryLogic и ActivityRegistryProxy (в Hardhat config или в тестах).
- Перевести тесты на деплой Proxy + Logic, attach Logic ABI к Proxy.
- Запустить тесты: `npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`.
- **Ожидание:** часть тестов зелёные, часть может падать — затем поправить логику (п. 3.4).

**Сделано:**
- В `ActivityRegistry.UUPS.comprehensive.test.js`: в `beforeEach` добавлен деплой Proxy: кодирование `initialize(admin, spiralEngine)` в initCalldata, `Proxy.deploy(logic.getAddress(), initCalldata)`, `activityRegistry = Logic.attach(await proxy.getAddress())`. Переменная `proxy` введена в scope.
- В `ActivityRegistry.UUPS.smoke.test.js`: тот же сценарий — деплой Logic → initCalldata → деплой Proxy → attach Logic ABI к адресу Proxy.
- Заголовки describe обновлены на «Фаза 3: Proxy + Logic» / «UUPS».
- Первый тест деплоя изменён на «должен задеплоить Proxy и привязать Logic к Proxy» с проверкой адреса Proxy.
- Компиляция Logic и Proxy выполняется (Hardhat собирает оба контракта).
- После перевода тестов все запущенные тесты (35 на тот момент) прошли — падающих не было, т.к. логика уже была проверена на Logic без Proxy в фазе 2.

**Расхождения:** План допускал падение части тестов с последующим исправлением в 3.4. Фактически после перевода на Proxy все тесты сразу стали зелёными — доработка Logic в 3.4 не потребовалась (логика и проверки уже были корректны).

**Качество:** Единый сценарий деплоя в comprehensive и smoke; повторное использование того же initCalldata, что и в других UUPS-тестах проекта.

**Выводы:** Пункт 3.3 выполнен. Отсутствие падающих тестов после перевода — следствие того, что фаза 2 уже покрыла Logic без Proxy; перевод на Proxy лишь сменил точку вызова (адрес Proxy вместо Logic).

---

## 3.4 — Исправить падающие тесты; добавить тесты upgradeToAndCall и Full State Preservation

**Задано по плану:**
- Исправить все падающие тесты: при необходимости доработка Logic (проверки, порядок push в publishedActivityIds, swap-and-pop при deactivate).
- Добавить тест: `upgradeToAndCall` от не-UPGRADER → AccessControlUnauthorizedAccount.
- Добавить тест: Full State Preservation после upgradeToAndCall.
- **Артефакт:** все P0 тесты зелёные.

**Сделано:**
- Падающих тестов не было — исправлений Logic не вносили.
- Добавлен тест «upgradeToAndCall от не-UPGRADER ревертит с AccessControlUnauthorizedAccount»: деплой LogicV2, вызов `activityRegistry.connect(creator).upgradeToAndCall(logicV2.getAddress(), "0x")`, ожидание custom error AccessControlUnauthorizedAccount.
- Добавлен блок describe «Full State Preservation» с тестом «сохраняет состояние при upgradeToAndCall; новая активность после апгрейда»: создание активностей от creator и otherCreator, активация одной, снимок getActivity(1,2,3), getActivitiesByCreator, getPublishedActivityIds; деплой LogicV2, вызов `activityRegistry.connect(admin).upgradeToAndCall(logicV2.getAddress(), "0x")`; сравнение всех полей и массивов после апгрейда; создание новой активности и проверка, что activityId = 4 и списки согласованы.
- Все P0 (и добавленные) тесты зелёные; всего 36 тестов после 3.4.

**Расхождения:** План предполагал возможное исправление падающих тестов — фактически ограничились добавлением двух новых тестов. Полнота Full State Preservation: проверяются getActivity по id, getActivitiesByCreator для обоих creator, getPublishedActivityIds и создание активности после апгрейда — соответствует п. 4.1 (несколько активностей, часть active, сравнение после upgrade, новая активность).

**Качество:** Тест upgradeToAndCall явно проверяет роль (не-UPGRADER не может апгрейдить). Full State Preservation покрывает состояние до/после upgrade и продолжение работы (createActivity после апгрейда).

**Выводы:** Пункт 3.4 выполнен. Дополнительная ценность — два новых теста закрепляют UUPS и сохранение состояния; отсутствие падающих тестов подтверждает качество фазы 2.

---

## 3.5 — forceDeactivate (опционально)

**Задано по плану:**
- Добавить при необходимости `forceDeactivate(activityId)` onlyRole(ADMIN_ROLE).
- Добавить тест: admin снимает с публикации чужую активность.
- **Артефакт:** опционально.

**Сделано:**
- В `IActivityRegistry.sol`: объявлена функция `function forceDeactivate(uint256 activityId) external;` в секции админ-функций.
- В `ActivityRegistryLogic.sol`: реализована `forceDeactivate(uint256 activityId) external onlyRole(ADMIN_ROLE) whenNotPaused nonReentrant`: проверки ActivityNotFound (creator == address(0)), ActivityNotActive; установка `active = false`, вызов `_removeFromPublished(activityId)`, emit ActivityDeactivated(activityId, msg.sender).
- В comprehensive-тестах добавлен тест «admin может forceDeactivate чужую активность»: creator создаёт и активирует активность; проверка, что active и published содержат id; вызов `activityRegistry.connect(admin).forceDeactivate(1)`; проверка, что active = false и getPublishedActivityIds пустой.
- Компиляция и все 37 тестов проходят.

**Расхождения:** План помечает пункт как опциональный («при необходимости»). Реализация добавлена без отдельного решения «нужно/не нужно» — как полезная админ-функция (модерация/принудительное снятие с публикации). Расхождение только в том, что опция реализована полностью, а не отложена.

**Качество:** Поведение совпадает с deactivateActivity (те же проверки и swap-and-pop), отличие только в доступе (ADMIN_ROLE вместо onlyOwnActivity). Событие ActivityDeactivated с initiator = admin — корректно. Интерфейс расширен явно; обратная совместимость для существующих вызывающих не ломается (только добавлена новая функция).

**Выводы:** Пункт 3.5 выполнен в полном объёме (включая интерфейс, Logic и тест). Решение реализовать опциональный пункт повышает пригодность контракта для продакшена (админ может снять чужую активность без передачи прав владельца).

---

## Сводка по фазе 3

| Пункт | Статус   | Расхождения с планом                         | Проверка                |
|-------|----------|-----------------------------------------------|-------------------------|
| 3.1   | Выполнен | Нет                                          | Компиляция, тесты       |
| 3.2   | Выполнен | Нет                                          | Файл есть, компиляция   |
| 3.3   | Выполнен | Падающих тестов не было (план их допускал)    | 35 тестов зелёные       |
| 3.4   | Выполнен | Исправлять было нечего; добавлены 2 теста    | 36 тестов зелёные       |
| 3.5   | Выполнен | Опция реализована полностью, не пропущена    | 37 тестов зелёные       |

**Итоговая проверка по плану:**  
`npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js` — все написанные тесты проходят (37 с учётом smoke). Фаза 3 считается завершённой.

---

## Рекомендации на будущее

1. **Длинные ответы с несколькими TODO:** выносить краткий чеклист в начало или конец (как сделано в этой ретроспективе), чтобы при обрезке лога было видно, что 3.3–3.5 тоже выполнены.
2. **Опциональные пункты (типа 3.5):** в плане явно фиксировать «реализовать» vs «оставить на потом» — чтобы ретроспектива однозначно трактовала «при необходимости».
3. **Full State Preservation:** при появлении новых state-полей в Logic добавлять их в снимок до/после upgrade в тесте, чтобы регрессий не было.
