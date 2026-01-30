# Квалификация тестов: ActivityRegistry.UUPS (test-qualification.mdc)

**Правило:** @.cursor/rules/test-qualification.mdc  
**Дата:** 2026-01-29  
**Файлы:** ActivityRegistry.UUPS.comprehensive.test.js, ActivityRegistry.UUPS.smoke.test.js  
**Цель:** Честная проверка на false successes, некорректные утверждения, непокрытые критические пути.

---

## Применённые правила

| ID | Приоритет | Описание |
|----|-----------|----------|
| NO_FALSE_SUCCESSES | P0 | Тесты не должны проходить при сломанной функциональности |
| VALIDATE_REAL_FUNCTIONALITY | P0 | Тесты проверяют реальное поведение, не побочные эффекты |
| NO_UNTESTED_CRITICAL_PATHS | P0 | Все критические пути должны быть покрыты |
| CORRECT_LOGIC | P1 | Утверждения осмысленны, не тавтологии |
| MINIMAL_MOCK_OVERUSE | P2 | Не перегружать моками |

---

## P0 — Результаты проверки

### NO_FALSE_SUCCESSES
- **Проверка:** Тесты не проходят при заведомо сломанной функциональности.
- **Статус:** Критические сценарии (деплой, createActivity, activate/deactivate, upgrade от не-UPGRADER, повторный initialize, pause) проверяют либо успех с конкретными данными, либо явный revert с ожидаемой ошибкой (expectRevertCustom). Ложных успехов по этим путям не выявлено.
- **Замечание:** Один тест принимает любой revert — см. P1 (activate несуществующей).

### VALIDATE_REAL_FUNCTIONALITY
- **Проверка:** Тесты проверяют реальное поведение контракта, а не побочные эффекты.
- **Статус:** createActivity проверяет возврат activityId, запись в getActivitiesByCreator, active=false, событие ActivityCreated. activate/deactivate проверяют изменение active и getPublishedActivityIds. Full State Preservation проверяет состояние после upgrade. Поведение проверяется через вызовы контракта и сравнение с ожидаемыми значениями.
- **Пробел P1:** После setSpiralEngine проверяется только spiralEngine() === newAddr и событие SpiralEngineUpdated; нет теста, что следующий createActivity реально использует новый engine (например, setSpiralEngine на контракт без роли для creator → createActivity ревертит). См. раздел P1.

### NO_UNTESTED_CRITICAL_PATHS
- **Проверка:** Критические пути Logic покрыты тестами.
- **Покрыто:** initialize (адреса, роли, повторный вызов → InvalidInitialization); _authorizeUpgrade (не-UPGRADER → AccessControlUnauthorizedAccount); createActivity (pause, роль, usedInvite, EmptyCID, возврат, событие); getActivity (id==0/999 → ActivityNotFound, структура); activateActivity (только creator, уже active, не creator, событие, published); deactivateActivity (только creator, черновик, не creator, published после deactivate); forceDeactivate (admin снимает чужую); setSpiralEngine (zero address, не admin, при pause); pause/unpause (только admin); getActivitiesByCreator, getPublishedActivityIds; Full State Preservation после upgrade.
- **Пробел P1:** Путь _authorizeUpgrade(newImplementation == address(0)) → revert ZeroAddress не покрыт: нет теста «admin вызывает upgradeToAndCall(ethers.ZeroAddress, "0x") → ZeroAddress». См. P1.

---

## P1 — Замечания и рекомендации

### 1. CORRECT_LOGIC: «activate несуществующей активности ревертит»
- **Сейчас:** Тест ловит любой revert (проверка `msg.includes("revert") || msg.includes("return data")`) и считает успехом.
- **Риск:** При изменении контракта на другую ошибку тест останется зелёным — мы не проверяем конкретную семантику.
- **Рекомендация:** Проверять явно custom error через expectRevertCustom.
- **Уточнение после правки:** Для id 999 модификатор onlyOwnActivity срабатывает раньше проверки в теле функции: activities[999].creator == address(0) != msg.sender → реверт **NotActivityCreator** (не ActivityNotFound). Тест обновлён на expectRevertCustom(..., "NotActivityCreator", activityRegistry).

### 2. NO_UNTESTED_CRITICAL_PATHS: _authorizeUpgrade(ZeroAddress)
- **Путь в Logic:** _authorizeUpgrade(address newImplementation): при newImplementation == address(0) revert ZeroAddress.
- **Сейчас:** Нет теста вызова upgradeToAndCall(ethers.ZeroAddress, "0x") от admin с ожиданием ZeroAddress.
- **Рекомендация:** Добавить тест: admin вызывает upgradeToAndCall(ethers.ZeroAddress, "0x") → expectRevertCustom(..., "ZeroAddress", activityRegistry).
- **Выполнено:** Добавлен тест «upgradeToAndCall(ZeroAddress) от admin ревертит с ZeroAddress».

### 3. VALIDATE_REAL_FUNCTIONALITY: использование SpiralEngine после setSpiralEngine
- **Сейчас:** Проверяются только spiralEngine() === newAddr и SpiralEngineUpdated.
- **Рекомендация (опционально):** Добавить тест: setSpiralEngine(spiral2); на spiral2 для creator не выдан ACTIVITY_CREATOR_ROLE или usedInviteByUser == 0; createActivity от creator ревертит с NotActivatedActivityCreator. Так проверяется, что контракт действительно использует новый engine при создании.
- **Выполнено:** Добавлен тест «P1: после setSpiralEngine createActivity использует новый engine — creator не активирован на spiral2 → NotActivatedActivityCreator».

### 4. CORRECT_LOGIC: неиспользуемый хелпер expectNotReverted
- **Сейчас:** expectNotReverted объявлен в файле, нигде не вызывается.
- **Рекомендация:** Удалить неиспользуемый хелпер или использовать в подходящем тесте (например, expectNotReverted(activityRegistry.connect(admin).unpause()) после pause).
- **Выполнено:** expectNotReverted используется в тесте «pause/unpause только ADMIN_ROLE» для вызова unpause().

---

## P2 — Минимальные замечания

### MINIMAL_MOCK_OVERUSE
- MockSpiralEngine используется для изоляции Logic (проверка onlyActivatedActivityCreator, usedInviteByUser). Альтернатива — реальный SpiralEngine в интеграции; для unit-тестов Logic мок обоснован. Замечаний нет.

---

## Сводная таблица

| Правило | Приоритет | Статус | Действие |
|---------|-----------|--------|----------|
| NO_FALSE_SUCCESSES | P0 | ✅ Критичных ложных успехов нет | — |
| VALIDATE_REAL_FUNCTIONALITY | P0 | ✅ P1 выполнен: тест createActivity после setSpiralEngine добавлен | — |
| NO_UNTESTED_CRITICAL_PATHS | P0 | ✅ P1 выполнен: тест upgradeToAndCall(ZeroAddress) добавлен | — |
| CORRECT_LOGIC | P1 | ✅ activate(999) — expectRevertCustom(NotActivityCreator); expectNotReverted используется | — |
| MINIMAL_MOCK_OVERUSE | P2 | ✅ | — |

---

## Рекомендуемые правки (по приоритету)

1. **P1:** Тест «activate несуществующей» — проверять конкретно ActivityNotFound через expectRevertCustom.
2. **P1:** Добавить тест «upgradeToAndCall(ZeroAddress) от admin ревертит с ZeroAddress».
3. **P1:** Удалить expectNotReverted или использовать в тесте unpause.
4. **P1 (опционально):** Тест: setSpiralEngine(spiral2); creator на spiral2 не активирован → createActivity ревертит с NotActivatedActivityCreator.

После внесения правок 1–3 качество набора тестов по правилу test-qualification будет соответствовать P0 без оговорок; пункт 4 усиливает проверку реального использования SpiralEngine.

---

## Выполненные правки (2026-01-29)

- **P1.1** Выполнено: тест «activate несуществующей» заменён на expectRevertCustom. Фактическая ошибка контракта для id 999 — **NotActivityCreator** (модификатор onlyOwnActivity срабатывает до проверки ActivityNotFound в теле функции), тест ожидает NotActivityCreator.
- **P1.2** Выполнено: добавлен тест «upgradeToAndCall(ZeroAddress) от admin ревертит с ZeroAddress».
- **P1.3** Выполнено: expectNotReverted используется в тесте «pause/unpause только ADMIN_ROLE» для вызова unpause().
- **P1.4 (опц.)** Выполнено по методике run-phase: добавлен тест «P1: после setSpiralEngine createActivity использует новый engine — creator не активирован на spiral2 → NotActivatedActivityCreator».
- Всего **39 тестов** (comprehensive + smoke), все проходят.
