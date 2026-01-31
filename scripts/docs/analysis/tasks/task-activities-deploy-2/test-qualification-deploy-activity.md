# Квалификация тестов: task-activities-deploy-2 (деплой ActivityRegistry)

**Дата:** 2026-01-29  
**Вариант:** B (обновление теста action1 + краткая квалификация)  
**Источник:** testing-step-constraints.md, test-qualification.mdc

---

## 1. Изменение набора тестов

- **Файл:** `scripts/tests/unit/actions/DeployActions.test.js`
- **Изменение:** в тесте «должен деплоить все UUPS контракты через deploySingleContract» добавлена проверка  
  `expect(mockContractManager.deploySingleContract.calledWith('ActivityRegistry')).to.be.true`
- **Цель:** зафиксировать, что action1 деплоит ActivityRegistry; при удалении ActivityRegistry из action1 тест покраснеет.

---

## 2. Проверка по test-qualification (P0/P1)

| Правило | Статус | Комментарий |
|---------|--------|-------------|
| NO_FALSE_SUCCESSES (P0) | ✅ | Тест проверяет реальный вызов deploySingleContract('ActivityRegistry'); при отсутствии вызова тест падает. |
| VALIDATE_REAL_FUNCTIONALITY (P0) | ✅ | Проверяется именно то, что action1 вызывает деплой ActivityRegistry — соответствие коду. |
| CORRECT_LOGIC (P1) | ✅ | Утверждение осмысленное: «action1 должен деплоить ActivityRegistry»; не тавтология. |

**Итог:** изменённый тест соответствует критериям test-qualification; ложных успехов нет, логика проверки корректна.

---

## 3. Прогон

- **Команда:** `npm run test:unit -- --grep "DeployActions"`
- **Результат:** тесты DeployActions проходят, в т.ч. «должен деплоить все UUPS контракты через deploySingleContract»; в выводе action1 присутствуют ACTIVITY_REGISTRY_PROXY_ADDRESS и ACTIVITY_REGISTRY_CONTRACT_ADDRESS.

---

**Статус:** Выполнено (вариант B). Перед коммитами — верификация по AC (acceptance-verification-*.md).
