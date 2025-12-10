# Тесты bot слоя

## 📋 Структура тестов

Тесты организованы в следующую структуру:

```
bot/tests/
├── unit/              # Unit тесты (с моками)
├── integration/       # Integration тесты (с реальными сервисами)
├── e2e/              # End-to-end тесты
└── api/              # API тесты
```

---

## 🎯 Unit тесты (`unit/`)

**Характеристики:**
- Используют моки для всех зависимостей
- Быстрые (не требуют внешних сервисов)
- Изолированные (не зависят от состояния)

**Запуск:**
```bash
# Все unit тесты
pytest bot/tests/unit/ -v -m unit

# Конкретный файл
pytest bot/tests/unit/test_product_registry_service.py -v
```

**Количество файлов:** 26

---

## 🔗 Integration тесты (`integration/`)

**Характеристики:**
- Используют реальные сервисы (блокчейн, Arweave, Pinata)
- Требуют настроенной инфраструктуры (Hardhat node, переменные окружения)
- Медленнее unit тестов

**Требования:**
- Hardhat node запущен на `localhost:8545`
- Контракты задеплоены (Action 1, Action 555, Action 444)
- Переменные окружения настроены (см. `bot/docs/tests/integration-infrastructure.md`)

**Запуск:**
```bash
# Все integration тесты
pytest bot/tests/integration/ -v -m integration

# Конкретный файл
pytest bot/tests/integration/test_product_registry_integration.py -v
```

**Количество файлов:** 15

**📚 Документация:**
- [`bot/docs/tests/integration-infrastructure.md`](../docs/tests/integration-infrastructure.md) - Подробная документация по инфраструктуре

---

## 🏷️ Маркеры тестов

Все тесты должны иметь соответствующие маркеры:

- `@pytest.mark.unit` - для unit тестов
- `@pytest.mark.integration` - для integration тестов

**Пример:**
```python
@pytest.mark.unit
def test_example():
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_example():
    pass
```

---

## 📝 Команды для запуска

### Все тесты
```bash
pytest bot/tests/ -v --tb=short
```

### Только unit тесты
```bash
pytest bot/tests/unit/ -v -m unit
```

### Только integration тесты
```bash
pytest bot/tests/integration/ -v -m integration
```

### С покрытием
```bash
pytest bot/tests/ --cov=bot --cov-report=html
```

---

## 📚 Дополнительная документация

- [`bot/docs/tests/integration-infrastructure.md`](../docs/tests/integration-infrastructure.md) - Инфраструктура интеграционных тестов
- [`bot/docs/tests/registry.md`](../docs/tests/registry.md) - Тестирование ProductRegistryService
- [`bot/docs/tests/overview.md`](../docs/tests/overview.md) - Обзор всех тестов

---

## 🎯 Принципы организации тестов

1. **Четкое разделение:** Unit и integration тесты в разных директориях
2. **Маркеры:** Все тесты должны иметь соответствующие маркеры
3. **Изоляция:** Unit тесты не зависят от внешних сервисов
4. **Реальность:** Integration тесты используют реальные сервисы
5. **Документация:** Каждый тест должен быть понятен без чтения кода

---

**Последнее обновление:** 2025-11-26  
**Рефакторинг:** Тесты разделены на unit/integration структуру

