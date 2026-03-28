# Подготовка к коммиту: Refactor quantity/unit + WooCommerce Export Enhancements

**Дата:** 2026-01-07  
**Ветка:** (проверить перед коммитом)  
**Методология:** `@docs/methodology/git-commit.md`

---

## Общая статистика

- **Изменено файлов:** 20 файлов (tracked)
- **Новых файлов:** 10 файлов (untracked, для коммита)
  - 6 файлов WooCommerce export (Группа 3)
  - 2 файла документации (Группа 6)
  - 2 файла core services (Группа 3)
- **Основные изменения:** ~1030 добавлений, ~710 удалений
- **Группы изменений:** 6 функциональных групп

**Примечание:** Таски (task-*.md) исключены из коммита документации, оставлены только технические документы и методологии.

---

## Исключённые файлы (НЕ коммитить)

### Автоматически исключены (по категориям):

| Категория | Файлы | Причина |
|-----------|-------|---------|
| `__pycache__/` | 12 файлов | Сгенерированные Python cache |
| `artifacts/` | 12 директорий | Сгенерированные Solidity артефакты |
| `cache/` | 1 директория | Кэш данных |
| `flowers/` | 2 файла | Приватные данные (инвайты) |
| `*.csv` (temp) | 1 файл | Временный файл (`woocommerce_products.fixed.csv`) |

### Временные utility скрипты (НЕ коммитить):

```
bot/utility/analyze_woo_export.py           # Временный анализ
bot/utility/fix_woocommerce_csv_html.py     # Одноразовый фикс
bot/utility/format_product_35_dried.py      # Тестовый скрипт
bot/utility/format_product_35_dried_final.py # Тестовый скрипт
bot/utility/format_product_35_dried_simple.py # Тестовый скрипт
```

### Таски (НЕ коммитить):

```
bot/docs/tasks/task-adapt-woo-id-mapping-for-variations.md
bot/docs/tasks/task-fix-sku-priority-from-mapping.md
bot/docs/tasks/task-implement-woo-export-diff-with-columns-mapping.md
bot/docs/tasks/task-refactor-woocommerce-columns-constants.md
bot/docs/tasks/task-woo-export-prices-missing.md
bot/docs/tasks/task-woo-export-script-enhancement.md
bot/docs/tasks/task-woo-id-business-mapping.md
```

**Причина:** Таски являются временными рабочими документами для планирования и отслеживания задач, не являются частью постоянной документации проекта.

---

## Группа 1: Core Models — PriceInfo quantity/unit refactor

### Файлы

```
bot/model/product.py
bot/api/models/product.py
```

### Что изменено

- **`bot/model/product.py`**: Рефакторинг `PriceInfo` — замена `weight/weight_unit/volume/volume_unit` на унифицированные `quantity/unit`
- **`bot/api/models/product.py`**: Синхронизация API модели с новой структурой

### Цель изменений

Унификация системы измерений в модели цен — вместо отдельных полей для веса и объёма используется единая пара `quantity/unit`.

### Commit message

```bash
git add bot/model/product.py bot/api/models/product.py

git commit -m "refactor(models): unify PriceInfo with quantity/unit instead of weight/volume

- Replace weight/weight_unit/volume/volume_unit with unified quantity/unit
- Add is_quantity_based property for backward compatibility
- Update PriceInfo.from_dict() and to_dict() methods
- Sync API model with new structure

This simplifies price handling and removes redundant fields for weight vs volume."
```

---

## Группа 2: API Converters — quantity/unit support

### Файлы

```
bot/api/converters/price_converter.py
bot/api/converters/product_converter.py
```

### Что изменено

- **`price_converter.py`**: Обновление конвертации цен для работы с `quantity/unit`
- **`product_converter.py`**: Обновление конвертации продуктов

### Цель изменений

Адаптация API конвертеров для работы с новой унифицированной структурой цен.

### Commit message

```bash
git add bot/api/converters/price_converter.py bot/api/converters/product_converter.py

git commit -m "refactor(api): update converters for quantity/unit price structure

- Update PriceConverter for unified quantity/unit fields
- Update ProductConverter for new PriceInfo structure
- Maintain backward compatibility with existing API contracts"
```

---

## Группа 3: WooCommerce Export — Major enhancements

### Файлы

```
bot/services/woocommerce/export.py
bot/services/woocommerce/html_format_adapter.py
bot/utility/export_to_woocommerce.py
bot/utility/generate_woo_id_mapping.py
bot/services/core/__init__.py
bot/services/core/contracts/
```

### Что изменено

- **`export.py`**: 
  - Добавлен класс `WooCommerceColumns` с константами колонок
  - Добавлена функция `_apply_mapping_to_rows()` для применения WooCommerce ID из mapping
  - Добавлена функция `_filter_columns()` для фильтрации колонок
  - Поддержка вариаций (variation ID из mapping)
  - SKU вариаций теперь пустой (как в WooCommerce)
  
- **`html_format_adapter.py`**: Обновление для работы с quantity/unit
  
- **`export_to_woocommerce.py`**: 
  - Добавлены параметры `--columns`, `--reuse-woo-id`, `--mapping`
  - Корректное разрешение путей относительно project_root
  
- **`generate_woo_id_mapping.py`**: 
  - Новый скрипт для генерации mapping из WooCommerce экспорта
  - Поддержка вариаций (variable products)
  - Merge mode для инкрементальных обновлений

### Цель изменений

Расширение функциональности WooCommerce экспорта:
- Diff-экспорт с выбором колонок
- Reuse существующих WooCommerce ID
- Поддержка вариативных продуктов

### Commit message

```bash
git add bot/services/woocommerce/export.py \
        bot/services/woocommerce/html_format_adapter.py \
        bot/utility/export_to_woocommerce.py \
        bot/utility/generate_woo_id_mapping.py \
        bot/services/core/__init__.py \
        bot/services/core/contracts/

git commit -m "feat(woocommerce): enhance export with mapping, columns selection and variations support

Export enhancements:
- Add WooCommerceColumns class with column name constants
- Add _apply_mapping_to_rows() for WooCommerce ID reuse from mapping
- Add _filter_columns() for selective column export
- Support variation ID mapping (mappings_by_variation_id)
- Variations now have empty SKU (matches WooCommerce format)

CLI enhancements:
- Add --columns parameter for selective export
- Add --reuse-woo-id flag for ID reuse from mapping
- Add --mapping parameter for mapping file path
- Fix path resolution relative to project_root

New generate_woo_id_mapping.py script:
- Generate mapping from WooCommerce export CSV
- Support variable products and variations
- Merge mode for incremental updates (--overwrite to replace)

This enables diff exports for updating existing WooCommerce products."
```

---

## Группа 4: Formatters — quantity/unit support

### Файлы

```
bot/handlers/common/formatting/product_formatter.py
bot/handlers/common/formatting/product_formatter_service.py
```

### Что изменено

- Обновление форматирования продуктов для работы с `quantity/unit`
- Адаптация вывода цен в Telegram

### Цель изменений

Синхронизация Telegram форматтеров с новой структурой цен.

### Commit message

```bash
git add bot/handlers/common/formatting/product_formatter.py \
        bot/handlers/common/formatting/product_formatter_service.py

git commit -m "refactor(formatters): update product formatters for quantity/unit structure

- Update price formatting for unified quantity/unit fields
- Maintain backward compatibility with Telegram output format"
```

---

## Группа 5: Tests — Update for new structure

### Файлы

```
bot/tests/conftest.py
bot/tests/mock_formatter_service.py
bot/tests/api/test_converters.py
bot/tests/unit/test_html_format_adapter.py
bot/tests/unit/test_sku_generation.py
bot/tests/validation/test_models_compatibility.py
bot/tests/validation/test_models_integration.py
bot/tests/validation/test_priceinfo_validation.py
bot/tests/validation/test_priceinfo_validation_errors.py
bot/tests/validation/test_product_validation.py
bot/tests/validation/test_validation_result_integration.py
```

### Что изменено

- Обновление тестовых фикстур для `quantity/unit`
- Обновление моков и валидационных тестов
- Адаптация unit тестов для новой структуры

### Цель изменений

Синхронизация тестов с рефакторингом модели цен.

### Commit message

```bash
git add bot/tests/conftest.py \
        bot/tests/mock_formatter_service.py \
        bot/tests/api/test_converters.py \
        bot/tests/unit/test_html_format_adapter.py \
        bot/tests/unit/test_sku_generation.py \
        bot/tests/validation/test_models_compatibility.py \
        bot/tests/validation/test_models_integration.py \
        bot/tests/validation/test_priceinfo_validation.py \
        bot/tests/validation/test_priceinfo_validation_errors.py \
        bot/tests/validation/test_product_validation.py \
        bot/tests/validation/test_validation_result_integration.py

git commit -m "test(bot): update tests for quantity/unit PriceInfo refactor

- Update test fixtures with quantity/unit instead of weight/volume
- Update mock_formatter_service for new structure
- Update validation tests for PriceInfo changes
- Update SKU generation tests
- Update HTML format adapter tests

All tests adapted for unified quantity/unit price structure."
```

---

## Группа 6: Documentation — Technical docs and methodology

### Файлы

```
bot/docs/tech/woocommerce-catalog-workflow.md
docs/methodology/task-complexity-assessment.md
```

### Что изменено

- **`woocommerce-catalog-workflow.md`**: Полная техническая документация по workflow экспорта и маппинга WooCommerce каталога
- **`task-complexity-assessment.md`**: Методология оценки сложности задач (7 критериев, категории XS/S/M/L/XL)

### Цель изменений

Добавление технической документации и методологий для поддержки разработки.

### Commit message

```bash
git add bot/docs/tech/woocommerce-catalog-workflow.md \
        docs/methodology/task-complexity-assessment.md

git commit -m "docs: add WooCommerce catalog workflow guide and task complexity assessment

Technical documentation:
- woocommerce-catalog-workflow.md: Complete guide for WooCommerce mapping and export scripts
  * generate_woo_id_mapping.py usage and parameters
  * export_to_woocommerce.py usage and parameters
  * Merge vs overwrite modes
  * Variable products and variations handling
  * Troubleshooting guide

Methodology:
- task-complexity-assessment.md: Systematic approach to task complexity estimation
  * 7 evaluation criteria (1-10 scale)
  * Size categories (XS/S/M/L/XL) with time estimates
  * Process and templates for consistent assessment"
```

---

## Порядок выполнения коммитов

```bash
# 1. Проверить ветку
git branch --show-current

# 2. Группа 1: Core Models
git add bot/model/product.py bot/api/models/product.py
git commit -m "refactor(models): unify PriceInfo with quantity/unit instead of weight/volume

- Replace weight/weight_unit/volume/volume_unit with unified quantity/unit
- Add is_quantity_based property for backward compatibility
- Update PriceInfo.from_dict() and to_dict() methods
- Sync API model with new structure

This simplifies price handling and removes redundant fields for weight vs volume."

# 3. Группа 2: API Converters
git add bot/api/converters/price_converter.py bot/api/converters/product_converter.py
git commit -m "refactor(api): update converters for quantity/unit price structure

- Update PriceConverter for unified quantity/unit fields
- Update ProductConverter for new PriceInfo structure
- Maintain backward compatibility with existing API contracts"

# 4. Группа 3: WooCommerce Export
git add bot/services/woocommerce/export.py \
        bot/services/woocommerce/html_format_adapter.py \
        bot/utility/export_to_woocommerce.py \
        bot/utility/generate_woo_id_mapping.py \
        bot/services/core/__init__.py \
        bot/services/core/contracts/
git commit -m "feat(woocommerce): enhance export with mapping, columns selection and variations support

Export enhancements:
- Add WooCommerceColumns class with column name constants
- Add _apply_mapping_to_rows() for WooCommerce ID reuse from mapping
- Add _filter_columns() for selective column export
- Support variation ID mapping (mappings_by_variation_id)
- Variations now have empty SKU (matches WooCommerce format)

CLI enhancements:
- Add --columns parameter for selective export
- Add --reuse-woo-id flag for ID reuse from mapping
- Add --mapping parameter for mapping file path
- Fix path resolution relative to project_root

New generate_woo_id_mapping.py script:
- Generate mapping from WooCommerce export CSV
- Support variable products and variations
- Merge mode for incremental updates (--overwrite to replace)

This enables diff exports for updating existing WooCommerce products."

# 5. Группа 4: Formatters
git add bot/handlers/common/formatting/product_formatter.py \
        bot/handlers/common/formatting/product_formatter_service.py
git commit -m "refactor(formatters): update product formatters for quantity/unit structure

- Update price formatting for unified quantity/unit fields
- Maintain backward compatibility with Telegram output format"

# 6. Группа 5: Tests
git add bot/tests/conftest.py \
        bot/tests/mock_formatter_service.py \
        bot/tests/api/test_converters.py \
        bot/tests/unit/test_html_format_adapter.py \
        bot/tests/unit/test_sku_generation.py \
        bot/tests/validation/test_models_compatibility.py \
        bot/tests/validation/test_models_integration.py \
        bot/tests/validation/test_priceinfo_validation.py \
        bot/tests/validation/test_priceinfo_validation_errors.py \
        bot/tests/validation/test_product_validation.py \
        bot/tests/validation/test_validation_result_integration.py
git commit -m "test(bot): update tests for quantity/unit PriceInfo refactor

- Update test fixtures with quantity/unit instead of weight/volume
- Update mock_formatter_service for new structure
- Update validation tests for PriceInfo changes
- Update SKU generation tests
- Update HTML format adapter tests

All tests adapted for unified quantity/unit price structure."

# 7. Группа 6: Documentation
git add bot/docs/tech/woocommerce-catalog-workflow.md \
        docs/methodology/task-complexity-assessment.md
git commit -m "docs: add WooCommerce catalog workflow guide and task complexity assessment

Technical documentation:
- woocommerce-catalog-workflow.md: Complete guide for WooCommerce mapping and export scripts
  * generate_woo_id_mapping.py usage and parameters
  * export_to_woocommerce.py usage and parameters
  * Merge vs overwrite modes
  * Variable products and variations handling
  * Troubleshooting guide

Methodology:
- task-complexity-assessment.md: Systematic approach to task complexity estimation
  * 7 evaluation criteria (1-10 scale)
  * Size categories (XS/S/M/L/XL) with time estimates
  * Process and templates for consistent assessment"

# 8. Проверить статус
git status --short bot/

# 9. Проверить коммиты
git log --oneline -6

# 10. Push (после проверки)
# git push origin <branch-name>
```

---

## Чеклист перед коммитами

- [ ] Проверена текущая ветка (`git branch --show-current`)
- [ ] Исключены файлы из категорий "НЕ коммитить":
  - [ ] `__pycache__/` — исключены
  - [ ] `artifacts/` — исключены
  - [ ] `cache/` — исключены
  - [ ] `flowers/` (invites) — исключены
  - [ ] Временные utility скрипты — исключены
  - [ ] `*.csv` временные файлы — исключены
- [ ] Файлы сгруппированы логически
- [ ] Commit messages на английском языке
- [ ] Commit messages следуют conventional commits format
- [ ] Каждый коммит логически целостный

---

## После коммитов

```bash
# Проверить что все нужные файлы закоммичены
git status --short bot/

# Ожидаемый результат — только исключённые файлы:
# - __pycache__/
# - artifacts/
# - cache/
# - flowers/
# - временные utility скрипты
# - временные CSV файлы
```

