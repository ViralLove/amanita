# Ретроспектива по продукту: Фаза 4 — Full State Preservation и P1

**Дата:** 2026-01-29  
**Основа:** solution-architecture-task1-activity-registry.md, фаза 4 (шаги 4.1–4.3)  
**Цель:** По каждому шагу — что задано, что сделано, расхождения, качество, выводы.

---

## 4.1 — Full State Preservation тест полный

**Задано по плану:**  
Убедиться, что тест Full State Preservation полный: несколько активностей от разных creator, часть active, часть неактивных; сохранение всех getActivity, getActivitiesByCreator для каждого creator, getPublishedActivityIds; upgrade; сравнение всех полей и массивов; создание новой активности (activityId = _activityIdCounter) и **activate**.

**Сделано:**  
- Тест уже был: несколько активностей от creator и otherCreator, одна активна (id 2), снимки getActivity(1,2,3), getActivitiesByCreator, getPublishedActivityIds, upgrade, сравнение, создание активности 4.  
- Добавлено: после `createActivity(0, "QmAfterUpgrade")` вызов `activateActivity(4)`, проверка `getActivity(4).active === true` и что `getPublishedActivityIds` содержит 4.

**Расхождения:** Нет. Ранее не было явной проверки «и activate» новой активности — дополнено.

**Качество:** Тест покрывает полный сценарий по плану 4.1; порядок величин газа не меняется критично.

**Выводы:** Пункт 4.1 выполнен; единственное изменение — добавление activate(4) и проверки published.

---

## 4.2 — P1 тесты

**Задано по плану:**  
Добавить P1 тесты: вызов createActivity при pause() → revert; несколько активностей у одного creator; getPublishedActivityIds пустой до первой активации.

**Сделано:**  
Все три сценария уже были в comprehensive-тестах (фаза 3 / P1): «при pause() createActivity ревертит», «несколько активностей у одного creator: список id и порядок», «getPublishedActivityIds пустой до первой активации». Изменений в коде не потребовалось; прогон тестов — 4 теста по этим сценариям проходят.

**Расхождения:** Нет. Критерии 4.2 выполнены без доработок.

**Качество:** Тесты явно проверяют revert при pause, список id у одного creator и пустой published до первой активации.

**Выводы:** Пункт 4.2 выполнен за счёт уже существующих P1-тестов.

---

## 4.3 — Метрики газа

**Задано по плану:**  
Запуск с отчётом по газу: REPORT_GAS=true npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js. Зафиксировать порядок величин газа для createActivity, activateActivity, deactivateActivity.

**Сделано:**  
Запущен прогон с REPORT_GAS=true; вывод gas reporter сохранён. Создан документ `phase4-gas-metrics.md`: createActivity Avg 172 955, activateActivity Avg 100 641, deactivateActivity Avg 43 737 (Min/Max где есть — в таблице). Итоговая проверка: 36 тестов comprehensive проходят, газ в разумных пределах.

**Расхождения:** Нет.

**Качество:** Метрики зафиксированы в отдельном файле; порядок величин ~10⁵ gas для основных операций — приемлемо.

**Выводы:** Пункт 4.3 выполнен; артефакт — phase4-gas-metrics.md.

---

## Сводка

| Шаг | Статус   | Расхождения | Проверка        |
|-----|----------|-------------|-----------------|
| 4.1 | Выполнен | Нет         | FSP тест + activate(4) |
| 4.2 | Выполнен | Нет         | P1 тесты уже были       |
| 4.3 | Выполнен | Нет         | phase4-gas-metrics.md   |

**Итоговая проверка:**  
`npx hardhat test contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js contracts/tests/ActivityRegistry.UUPS.smoke.test.js` — **37 passing**. Full State Preservation зелёный; газ в разумных пределах.
