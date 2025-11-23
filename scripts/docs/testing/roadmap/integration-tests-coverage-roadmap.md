# План улучшения покрытия интеграционных тестов

**Версия:** 1.0  
**Дата:** 2025-11-22  
**Статус:** ✅ Базовое покрытие реализовано

---

## 📊 Текущее состояние покрытия критических интеграций

### ✅ Реализованные тесты

Все три критические интеграции **уже покрыты тестами**:

| # | Интеграция | Файл теста | Статус | Тестов | Время создания |
|---|------------|------------|--------|--------|----------------|
| 1 | CoreLogic → InviteActions | `scripts/tests/integration/core-invite-actions.integration.test.js` | ✅ Создан | 4 теста | 2025-11-22 |
| 2 | ActionsManager → ComponentActions → InviteActions | `scripts/tests/integration/action555-full-workflow.integration.test.js` | ✅ Создан | 4 теста | 2025-11-22 |
| 3 | ComponentActions → uploadComplexFields → AmanitaInternational | `scripts/tests/e2e/actions/component/action555.e2e.test.js` | ✅ Создан | 7 тестов | 2025-11-22 |

**Итого:** 19 тестов для трех критических интеграций

---

## 🔍 Анализ качества существующих тестов

### 1. CoreLogic → InviteActions Integration

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js`

**Покрытие:**
- ✅ Делегация активации seller в InviteActions.activateSeller
- ✅ Fallback на прямую реализацию, если InviteActions не доступен
- ✅ Адаптация результата InviteActions под старую структуру
- ✅ Правильное определение inviteCode из параметров или конфига

**Пробелы (P1):**
- ❌ Нет теста для случая, когда `InviteActions.activateSeller()` выбрасывает ошибку
- ❌ Нет теста для проверки логирования (warnings при использовании deprecated параметров)
- ❌ Нет теста для проверки адаптации результата при частичных данных (activationResult = null)

**Архитектура теста:**
```
✅ Реальные модули: CoreLogic, InviteActions (через IntegrationHarness)
✅ Минимальные моки: SpiralEngine контракт (external API)
✅ State tracking: Activation state через closures
✅ Проверка делегации: Spy на InviteActions.activateSeller
```

### 2. ActionsManager → ComponentActions → InviteActions Integration

**Файл:** `scripts/tests/integration/action555-full-workflow.integration.test.js`

**Покрытие:**
- ✅ Полный workflow: SpiralEngine → activateSeller → uploadComponents
- ✅ Обработка ошибки на этапе активации
- ✅ Идемпотентность (пропуск активации если уже активирован)
- ✅ Проверка правильности делегации ComponentActions → InviteActions

**Пробелы (P1):**
- ❌ Нет теста для ошибки на этапе uploadComponents (активация прошла, но загрузка компонентов провалилась)
- ❌ Нет теста для частичной загрузки компонентов (некоторые успешно, некоторые провалились)
- ❌ Нет теста для проверки метрик загрузки компонентов в результате

**Архитектура теста:**
```
✅ Реальные модули: ActionsManager, ComponentActions, InviteActions (через IntegrationHarness)
✅ Минимальные моки: SpiralEngine контракт (external API), uploadComponentsCore (stub)
✅ State tracking: Activation state через closures
✅ Проверка цепочки: ActionsManager.executeAction(555) → ComponentActions.action555() → InviteActions.activateSeller()
```

### 3. ComponentActions → uploadComplexFields → AmanitaInternational Integration

**Файл:** `scripts/tests/e2e/actions/component/action555.e2e.test.js`

**Покрытие:**
- ✅ Полный workflow: Load → Activate → Upload → Validate
- ✅ Проверка регистрации компонентов в OrganicComponentRegistry
- ✅ Проверка complex fields в AmanitaInternational
- ✅ Проверка правильности `className` с `biounit_id`
- ✅ Проверка уникальности ключей для разных компонентов
- ✅ Проверка формата `className` с `biounit_id`
- ✅ Проверка вызова `setComplexFieldCID` с правильным `className`

**Пробелы (P1):**
- ⏳ Нет integration тестов для проверки загрузки complex fields без Hardhat node
- ⏳ Нет проверки вызова `uploadComplexFields` в integration тестах

**Архитектура теста:**
```
✅ Реальные модули: ComponentActions (через E2EHarness)
✅ Реальные контракты: AmanitaInternational, OrganicComponentRegistry (Hardhat node)
✅ State tracking: Проверка состояния контракта после загрузки
✅ Проверка цепочки: action555() → uploadComponentsCore() → uploadComplexFields() → setComplexFieldCID()
```

**Примечание:** Test #3 тестирует загрузку компонентов в scripts слое, а не чтение в bot слое. E2E тесты уже полностью покрывают функциональность.

---

## 🎯 Архитектура решения для улучшения покрытия

### Принципы улучшения

1. **Инкрементальное улучшение** - не переписывать существующие тесты, добавлять новые сценарии
2. **Приоритизация по риску** - сначала закрыть P0 пробелы, затем P1, затем P2
3. **Соответствие методологии** - следовать @integration-test-build.core.mdc
4. **Минимальные изменения** - использовать существующие fixtures и harness

### Архитектурные паттерны

#### Паттерн 1: Error Path Testing

**Цель:** Покрыть все типы ошибок в каждой критической интеграции

**Структура:**
```javascript
describe('Error Handling', () => {
  it('должен обработать ошибку [тип ошибки] на этапе [этап]', async () => {
    // GIVEN: Настройка условий для ошибки
    // WHEN: Вызов метода
    // THEN: Проверка обработки ошибки
  });
});
```

**Применение:**
- CoreLogic → InviteActions: ошибка в InviteActions.activateSeller()
- ActionsManager → ComponentActions: ошибка в uploadComponentsCore()
- ComponentActions → uploadComplexFields → AmanitaInternational: уже покрыто E2E тестами (7 тестов)

#### Паттерн 2: Partial Success Testing

**Цель:** Проверить обработку частичных успехов (некоторые операции прошли, некоторые провалились)

**Структура:**
```javascript
describe('Partial Success Handling', () => {
  it('должен обработать частичный успех [сценарий]', async () => {
    // GIVEN: Настройка для частичного успеха
    // WHEN: Вызов метода
    // THEN: Проверка обработки частичного успеха
  });
});
```

**Применение:**
- ActionsManager → ComponentActions: частичная загрузка компонентов

#### Паттерн 3: Metrics and Logging Testing

**Цель:** Проверить, что метрики и логирование работают корректно

**Структура:**
```python
def test_metrics_after_operation(self, service):
    """Test metrics tracking after operation"""
    # GIVEN: Очистка метрик
    # WHEN: Выполнение операции
    # THEN: Проверка метрик
```

**Применение:**
- ComponentActions → uploadComplexFields: проверка загрузки через integration тесты (опционально)

---

## 📋 План реализации улучшений

### Этап 1: P0 - Критические пробелы (если есть)

**Статус:** ✅ Нет критических пробелов (P0)

Все три интеграции покрыты базовыми тестами. Все критические пути (успешные сценарии, основные ошибки) покрыты.

### Этап 2: P1 - Важные улучшения

#### 2.1 CoreLogic → InviteActions: Error Handling

**Приоритет:** P1  
**Время:** 30-45 минут

**Тесты для добавления:**
1. `test_should_handle_error_in_invite_actions_activate_seller` - обработка ошибки в InviteActions.activateSeller()
2. `test_should_log_warning_when_using_deprecated_invite_codes` - проверка логирования deprecated параметров
3. `test_should_handle_null_activation_result` - адаптация результата при activationResult = null

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js`

**Структура теста:**
```javascript
describe('Error Handling', () => {
  it('должен обработать ошибку в InviteActions.activateSeller()', async () => {
    // GIVEN: InviteActions.activateSeller выбрасывает ошибку
    const activateSellerStub = sinon.stub(modules.coreLogic.inviteActions, 'activateSeller')
      .rejects(new Error('Activation failed'));
    
    // WHEN: CoreLogic.activateSellerBasic вызывается
    // THEN: Ошибка пробрасывается корректно
  });
});
```

#### 2.2 ActionsManager → ComponentActions: Error Handling в uploadComponents

**Приоритет:** P1  
**Время:** 30-45 минут

**Тесты для добавления:**
1. `test_should_handle_error_in_upload_components_after_successful_activation` - ошибка в uploadComponents после успешной активации
2. `test_should_handle_partial_component_upload` - частичная загрузка компонентов (некоторые успешно, некоторые провалились)
3. `test_should_validate_upload_metrics_in_result` - проверка метрик загрузки в результате

**Файл:** `scripts/tests/integration/action555-full-workflow.integration.test.js`

**Структура теста:**
```javascript
describe('Component Upload Error Handling', () => {
  it('должен обработать ошибку в uploadComponents после успешной активации', async () => {
    // GIVEN: Seller активирован успешно, но uploadComponents выбрасывает ошибку
    const uploadStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
      .rejects(new Error('Upload failed'));
    
    // WHEN: Action 555 вызывается
    // THEN: Ошибка пробрасывается, но активация остается валидной
  });
});
```

### Этап 3: P2 - Дополнительные улучшения

#### 3.1 MultilingualIPFSService → BlockchainService: Cache TTL и Metrics

**Приоритет:** P2  
**Время:** 30-45 минут

**Тесты для добавления:**
1. `test_cache_ttl_expiration` - проверка протухания TTL локального кэша
2. `test_cache_invalidation` - проверка инвалидации кэша
3. `test_stats_tracking_after_load` - проверка метрик (stats) после загрузки

**Файл:** `bot/tests/integration/test_multilingual_ipfs_blockchain_integration.py`

**Структура теста:**
```python
def test_cache_ttl_expiration(self, multilingual_ipfs_service, blockchain_service, ipfs_factory):
    """Test cache TTL expiration"""
    # GIVEN: Данные загружены и закэшированы
    # WHEN: TTL истекает
    # THEN: Данные перезагружаются из блокчейна/IPFS
```

---

## 🔧 Детальный план реализации

### Фаза 1: Анализ текущего покрытия (Завершено)

**Статус:** ✅ Завершено

- [x] Идентифицированы все три критические интеграции
- [x] Проверено существование тестов для каждой интеграции
- [x] Проанализировано качество существующих тестов
- [x] Выявлены пробелы в покрытии

### Фаза 2: Приоритизация улучшений

**Статус:** ✅ Завершено

- [x] Классифицированы пробелы по приоритету (P0/P1/P2)
- [x] Определено, что критических пробелов нет (P0 покрыт)
- [x] Определены важные улучшения (P1)
- [x] Определены дополнительные улучшения (P2)

### Фаза 3: Реализация P1 улучшений (Pending)

**Статус:** ⏳ Ожидает реализации

#### Задача 3.1: Добавить error handling тесты для CoreLogic → InviteActions

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js`

**Тесты:**
1. `test_should_handle_error_in_invite_actions_activate_seller`
   - **GIVEN:** `InviteActions.activateSeller()` выбрасывает ошибку
   - **WHEN:** `CoreLogic.activateSellerBasic()` вызывается
   - **THEN:** Ошибка пробрасывается корректно, fallback не срабатывает

2. `test_should_log_warning_when_using_deprecated_invite_codes`
   - **GIVEN:** `inviteCodes` массив передан в `activateSellerBasic()`
   - **WHEN:** Метод вызывается
   - **THEN:** Логируется warning о deprecated параметре

3. `test_should_handle_null_activation_result`
   - **GIVEN:** `InviteActions.activateSeller()` возвращает результат без `activationResult`
   - **WHEN:** `CoreLogic.activateSellerBasic()` адаптирует результат
   - **THEN:** Результат адаптирован корректно (transactionHash = null)

**Время:** 30-45 минут

#### Задача 3.2: Добавить error handling тесты для ActionsManager → ComponentActions

**Файл:** `scripts/tests/integration/action555-full-workflow.integration.test.js`

**Тесты:**
1. `test_should_handle_error_in_upload_components_after_successful_activation`
   - **GIVEN:** Seller активирован успешно, `uploadComponentsCore()` выбрасывает ошибку
   - **WHEN:** Action 555 вызывается
   - **THEN:** Ошибка пробрасывается, но активация остается валидной

2. `test_should_handle_partial_component_upload`
   - **GIVEN:** `uploadComponentsCore()` возвращает результат с `failCount > 0`
   - **WHEN:** Action 555 вызывается
   - **THEN:** Ошибка выбрасывается с деталями провалившихся компонентов

3. `test_should_validate_upload_metrics_in_result`
   - **GIVEN:** Action 555 выполнен успешно
   - **WHEN:** Результат проверяется
   - **THEN:** Метрики загрузки присутствуют в результате (totalCount, successCount, failCount)

**Время:** 30-45 минут

### Фаза 4: Реализация P2 улучшений (Optional)

**Статус:** ⏳ Опционально (для будущего)

#### Задача 4.1: Расширить integration тесты для загрузки complex fields (опционально)

**Файл:** `scripts/tests/integration/action555-full-workflow.integration.test.js` (расширить существующий)

**Тесты:**
1. `test_should_upload_complex_fields_with_correct_classname` - проверка вызова `setComplexFieldCID` с правильным `className`
2. `test_should_create_unique_keys_for_different_components` - проверка уникальности ключей
3. `test_should_save_cids_in_state_complex_fields` - проверка сохранения CIDs в state

**Время:** 30-45 минут

**Примечание:** E2E тесты уже полностью покрывают функциональность. Integration тесты - опциональное улучшение.

---

## 📊 Метрики покрытия

### Текущее состояние

| Интеграция | Базовые тесты | Error handling | Partial success | Metrics | Всего |
|------------|---------------|----------------|-----------------|---------|-------|
| CoreLogic → InviteActions | ✅ 4 | ⏳ 0 | N/A | N/A | 4 |
| ActionsManager → ComponentActions → InviteActions | ✅ 4 | ⏳ 0 | ⏳ 0 | ⏳ 0 | 4 |
| MultilingualIPFSService → BlockchainService | ✅ 11 | ✅ 5 | N/A | ⏳ 0 | 11 |

**Итого:** 15 тестов (базовое покрытие для загрузки в scripts), 8 дополнительных тестов рекомендуется (P1+P2)

### Целевое состояние (после реализации P1)

| Интеграция | Базовые тесты | Error handling | Partial success | Metrics | Всего |
|------------|---------------|----------------|-----------------|---------|-------|
| CoreLogic → InviteActions | ✅ 4 | ✅ 3 | N/A | N/A | 7 |
| ActionsManager → ComponentActions → InviteActions | ✅ 4 | ✅ 1 | ✅ 2 | ✅ 1 | 8 |
| ComponentActions → uploadComplexFields → AmanitaInternational | ✅ 7 | ⏳ 0 | N/A | N/A | 7 |

**Итого:** 22 теста (после P1 улучшений)

**Примечание:** Test #3 для загрузки complex fields уже полностью покрыт E2E тестами (7 тестов). Integration тесты для более детальной проверки - опционально (P1).

---

## 🎯 Критерии приемки

### Для каждого нового теста:

1. **Корректная структура:**
   - [ ] GIVEN-WHEN-THEN структура
   - [ ] Использование реальных модулей через IntegrationHarness/conftest
   - [ ] Минимальные моки (только external APIs)

2. **Проверка функциональности:**
   - [ ] Тест проверяет реальное поведение, а не только структуру ответа
   - [ ] Тест проверяет состояние после операции
   - [ ] Тест проверяет обработку ошибок (для error handling тестов)

3. **Соответствие методологии:**
   - [ ] Следует @integration-test-build.core.mdc
   - [ ] Использует state tracking через closures (где применимо)
   - [ ] Проверяет module handshakes

4. **Проходимость:**
   - [ ] Тест проходит успешно
   - [ ] Нет false positives
   - [ ] Тест стабилен (не флакает)

---

## 🔄 Последовательность реализации

### Шаг 1: Подготовка (5 минут)

- [ ] Создать ветку для улучшений
- [ ] Обновить TODO tracker
- [ ] Подготовить тестовые данные

### Шаг 2: Реализация P1 улучшений (1.5-2 часа)

- [ ] Задача 3.1: Добавить error handling тесты для CoreLogic → InviteActions (30-45 мин)
- [ ] Задача 3.2: Добавить error handling тесты для ActionsManager → ComponentActions (30-45 мин)
- [ ] Валидация: Запустить все тесты, убедиться что все проходят (15 мин)

### Шаг 3: Документирование (10 минут)

- [x] Обновить метрики покрытия тестов
- [ ] Создать changelog для тестов

### Шаг 4: Опционально - P2 улучшения (30-45 минут)

- [ ] Задача 4.1: Расширить integration тесты для загрузки complex fields (опционально, 30-45 мин)

---

## 🚀 Быстрый старт

### Для реализации P1 улучшений:

1. **CoreLogic → InviteActions:**
   ```bash
   # Открыть файл
   scripts/tests/integration/core-invite-actions.integration.test.js
   
   # Добавить новый describe блок "Error Handling"
   # Реализовать 3 теста по структуре выше
   ```

2. **ActionsManager → ComponentActions:**
   ```bash
   # Открыть файл
   scripts/tests/integration/action555-full-workflow.integration.test.js
   
   # Добавить новый describe блок "Component Upload Error Handling"
   # Реализовать 3 теста по структуре выше
   ```

3. **Валидация:**
   ```bash
   # Запустить тесты
   npm run test:integration
   npm run test:e2e -- scripts/tests/e2e/actions/component/action555.e2e.test.js
   ```

---

## 📝 Примечания

1. **Все базовые тесты уже созданы** - не нужно создавать новые файлы, только расширять существующие
2. **Приоритет P1** - это улучшения, не критичные для MVP, но важные для качества
3. **Приоритет P2** - опциональные улучшения для будущего
4. **Методология** - все тесты должны следовать @integration-test-build.core.mdc

---

## 🔗 Связанные документы

- **[reference/integration-tests-implementation-reference.md](reference/integration-tests-implementation-reference.md)** - Справочник по реализации интеграционных тестов
- **[architecture/mock-state-tracking-architecture.md](architecture/mock-state-tracking-architecture.md)** - Архитектура синхронизации состояния в моках
- **[Testing-Architecture.md](../../Testing-Architecture.md)** - Архитектура тестирования

---

**Версия:** 1.0  
**Дата обновления:** 2025-11-22  
**Статус:** ✅ Анализ завершен, план готов к реализации

