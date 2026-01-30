# Ретроспектива по продукту: отработка замечаний P1 (test-qualification)

**Дата:** 2026-01-29  
**Основа:** ActivityRegistry.UUPS.test-qualification-report.md, раздел P1 (строки 41–70)  
**Методика:** docs/methodology/multi-step-phase-execution.md, run-phase  
**Цель:** По каждому замечанию P1 — что задано, что сделано, расхождения, качество, выводы.

---

## P1.1 — CORRECT_LOGIC: «activate несуществующей активности ревертит»

**Задано по плану:**  
Проверять явно custom error через expectRevertCustom вместо try/catch с «любой revert».

**Сделано:**  
Тест «activate несуществующей активности ревертит с NotActivityCreator» реализован через expectRevertCustom(activityRegistry.connect(creator).activateActivity(999), "NotActivityCreator", activityRegistry). Уточнение: для id 999 модификатор onlyOwnActivity срабатывает раньше проверки в теле функции → контракт ревертит **NotActivityCreator**, а не ActivityNotFound.

**Расхождения:** В отчёте рекомендовали ожидать ActivityNotFound; фактическое поведение контракта — NotActivityCreator. Тест приведён в соответствие с реальным порядком проверок.

**Качество:** Семантика проверяется явно; при смене ошибки в контракте тест упадёт.

**Выводы:** P1.1 выполнен; ожидаемая ошибка — NotActivityCreator.

---

## P1.2 — NO_UNTESTED_CRITICAL_PATHS: _authorizeUpgrade(ZeroAddress)

**Задано по плану:**  
Добавить тест: admin вызывает upgradeToAndCall(ethers.ZeroAddress, "0x") → expectRevertCustom(..., "ZeroAddress", activityRegistry).

**Сделано:**  
В блок «Deployment and initialization» добавлен тест «upgradeToAndCall(ZeroAddress) от admin ревертит с ZeroAddress». Вызов activityRegistry.connect(admin).upgradeToAndCall(ethers.ZeroAddress, "0x") обёрнут в expectRevertCustom с "ZeroAddress" и activityRegistry.

**Расхождения:** Нет.

**Качество:** Критический путь _authorizeUpgrade(newImplementation == address(0)) покрыт.

**Выводы:** P1.2 выполнен.

---

## P1.3 — VALIDATE_REAL_FUNCTIONALITY: использование SpiralEngine после setSpiralEngine (опционально)

**Задано по плану:**  
Добавить тест: setSpiralEngine(spiral2); на spiral2 для creator не выдан ACTIVITY_CREATOR_ROLE или usedInviteByUser == 0; createActivity от creator ревертит с NotActivatedActivityCreator.

**Сделано:**  
Решение: выполняем (опциональный шаг). В блок «setSpiralEngine» добавлен тест «P1: после setSpiralEngine createActivity использует новый engine — creator не активирован на spiral2 → NotActivatedActivityCreator». Деплой spiral2 без выдачи ACTIVITY_CREATOR_ROLE и без setUserActivated для creator; setSpiralEngine(spiral2); createActivity(0, "QmAfterSetSpiral") от creator → expectRevertCustom(..., "NotActivatedActivityCreator", activityRegistry).

**Расхождения:** Нет.

**Качество:** Подтверждается, что контракт при createActivity обращается к текущему spiralEngine(), а не к закэшированному адресу.

**Выводы:** P1.3 (опц.) выполнен.

---

## P1.4 — CORRECT_LOGIC: неиспользуемый хелпер expectNotReverted

**Задано по плану:**  
Удалить неиспользуемый хелпер или использовать в подходящем тесте (например, expectNotReverted(activityRegistry.connect(admin).unpause()) после pause).

**Сделано:**  
В тесте «pause/unpause только ADMIN_ROLE» вызов unpause() обёрнут в expectNotReverted(activityRegistry.connect(admin).unpause(), "unpause не должен ревертиться"). Хелпер остаётся в файле и используется.

**Расхождения:** Нет.

**Качество:** Хелпер имеет смысл; явная проверка «unpause не ревертится» улучшает читаемость.

**Выводы:** P1.4 выполнен.

---

## Сводная таблица

| Шаг | Статус   | Расхождения |
|-----|----------|--------------|
| P1.1 | Выполнен | Ожидаемая ошибка NotActivityCreator (не ActivityNotFound) — по контракту |
| P1.2 | Выполнен | Нет |
| P1.3 (опц.) | Выполнен | Нет |
| P1.4 | Выполнен | Нет |

---

## Итоговая проверка

**Команда:**  
`npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js contracts/tests/ActivityRegistry.UUPS.smoke.test.js --no-compile`

**Результат:** 39 passing (comprehensive + smoke).
