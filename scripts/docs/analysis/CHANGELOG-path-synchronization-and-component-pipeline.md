# Описание изменений: Синхронизация путей и рефакторинг компонентного pipeline

## Дата изменений
2025-12-25

## Общая статистика
- **Изменено файлов:** 17 файлов
- **Основные изменения:** ~5244 добавлений, ~560 удалений
- **Группы изменений:** 6 функциональных групп

---

## Группа 1: Core Feature - Синхронизация путей в CatalogActions

### Файлы
- `scripts/lib/actions/CatalogActions.js`

### Что изменено

#### Action 42: Unified Arweave Upload
- **До:** Использовал жестко заданный путь `data/sellers/{sellerId}/output/products`
- **После:** Многоуровневая логика поиска путей:
  1. Приоритет 1: Путь из конфига (`config.get('paths.outputPath')`)
  2. Приоритет 2: Поиск в нескольких возможных местах:
     - `data/sellers/{sellerId}/products`
     - `data/sellers/{sellerId}/output/products`
  3. Fallback: Стандартный путь с валидацией существования
- Добавлена валидация существования директории перед использованием
- Добавлено логирование найденных путей

#### Action 43: Contract Registration
- **До:** Не определял пути автоматически, полагался на конфиг/env
- **После:** Автоматическое определение путей на основе Seller ID:
  - Mapping file: поиск в `data/sellers/{sellerId}/product_combined_mapping.json` или `data/sellers/{sellerId}/output/product_combined_mapping.json`
  - Products dir: поиск в `data/sellers/{sellerId}/products` или `data/sellers/{sellerId}/output/products`
- Добавлена валидация существования файлов/директорий с понятными сообщениями об ошибках
- Добавлена инициализация ProductRegistry контракта в context
- Изменена сигнатура вызова `action43_UnifiedContractRegistration`: теперь принимает `context, mappingFile, productsDir` вместо объекта с `contractManager, config, logger`

#### Action 444: Automatic Pipeline
- **До:** Использовал `config.get('catalog.outputDir') || process.env.OUTPUT_DIR || 'data/output'`
- **После:** Использует ту же логику поиска путей, что и Action 42:
  - Поиск существующей директории `products` в нескольких местах
  - Определение `outputDir` как родительской директории найденного `productsDir`
  - Fallback на конфиг/env только если директория не найдена
- Добавлено логирование найденных путей

### Цель изменений
Устранить рассинхронизацию путей между Action 42, Action 43 и Action 444. Обеспечить единообразную логику определения путей к mapping файлам и директориям продуктов во всех actions каталога.

---

## Группа 2: Configuration - Исправления валидатора каталога

### Файлы
- `scripts/validators/validate_catalog_pipeline.js`

### Что изменено

#### Исправление бага с неопределенной переменной
- **До:** Использовалась неопределенная переменная `i` в сообщении об ошибке
- **После:** Используется `productId` из контекста

#### Поиск mapping файла в нескольких местах
- **До:** Искал mapping файл только в `data/sellers/{sellerId}/output/product_combined_mapping.json`
- **После:** Поиск в нескольких местах с выбором самого нового файла:
  - `data/sellers/{sellerId}/output/product_combined_mapping.json` (стандартное место)
  - `data/sellers/{sellerId}/product_combined_mapping.json` (альтернативное место)
- Определение `outputDir` на основе найденного mapping файла

#### Schema-aware валидация продуктов
- **До:** Проверял только legacy схему (`product_id`, `components`)
- **После:** Поддержка обеих схем с автоматическим определением:
  - Новая схема (primary): `business_id`, `organic_components`
  - Legacy схема (fallback): `product_id`, `components`
- Добавлена функция `detectProductSchema()` для определения версии схемы
- Добавлена функция `normalizeProduct()` для нормализации продукта к schema-independent виду
- Валидация required fields теперь schema-aware
- Добавлены предупреждения о legacy схеме

### Цель изменений
Исправить технические проблемы валидатора (баг с переменной, несоответствие путей) и добавить поддержку новой схемы продуктов с обратной совместимостью.

---

## Группа 3: Core Feature - Рефакторинг ComponentActions (Action 555 → Pipeline 51→52→53)

### Файлы
- `scripts/lib/actions/ComponentActions.js`

### Что изменено

#### Action 555: Рефакторинг в композитный pipeline
- **До:** Монолитная функция, выполнявшая активацию seller и загрузку компонентов в одном действии
- **После:** Композитный pipeline, последовательно вызывающий:
  1. Action 51: Активация seller
  2. Action 52: Загрузка компонентов в Arweave
  3. Action 53: Регистрация компонентов в контракте
- Добавлена обработка ошибок на каждом этапе с прерыванием pipeline при ошибке
- Добавлена статистика выполнения каждого этапа
- Добавлено логирование прогресса каждого этапа

#### Action 51: Новая функция активации seller
- Проверка статуса активации ДО требования DEPLOYER_INVITE
- Если seller уже активирован → пропуск активации
- Если seller НЕ активирован → требование DEPLOYER_INVITE и выполнение активации
- Валидация результата через blockchain (проверка `usedInviteByUser` и `hasRole`)

#### Action 52: Новая функция загрузки в Arweave
- Вызов `action52_UnifiedArweaveUpload` из `upload_steps.js`
- Валидация context (arweave client, AmanitaInternational, seller)
- Валидация активации seller (требует Action 51)

#### Action 53: Новая функция регистрации в контракте
- Вызов `action53_UnifiedContractRegistration` из `upload_steps.js`
- Валидация context

### Цель изменений
Разделить монолитную Action 555 на отдельные, переиспользуемые actions (51, 52, 53) для улучшения модульности и возможности независимого выполнения каждого этапа.

---

## Группа 4: Core Feature - Расширение upload_steps.js

### Файлы
- `scripts/lib/upload_steps.js`
- `scripts/lib/product_upload_steps.js`
- `scripts/lib/product_utils.js`

### Что изменено

#### Поддержка USE_EXISTING_CIDS флага
- Добавлена проверка флага `context.useExistingCids` в функциях:
  - `uploadSimpleFields()`: проверка существующих CID для title и dosage_types
  - `uploadComplexFields()`: проверка существующих CID для всех языков
  - `uploadRootMetadata()`: проверка существующего CID для root metadata
- Если CID найдены → пропуск загрузки, возврат существующих CID
- Если CID отсутствуют → fallback на обычную логику загрузки

#### ComponentTracking интеграция
- В `updateRootMetadata()`:
  - Импорт `ComponentTracking`
  - Очистка исходного JSON от тестовых адресов через `tracking.cleanSourceJson()`
  - Обновление tracking-полей через `tracking.updateForCreation()`
- В `registerComponent()`:
  - Обновление `change_history` с blockchain данными (transaction hash, block number)
  - Обновление исходного JSON файла компонента с blockchain данными
  - Обновление финального JSON файла с blockchain данными

#### Новые функции для компонентов
- `action52_UnifiedArweaveUpload()`: Unified Arweave upload для компонентов
  - Валидация context и seller активации
  - Поиск компонентов в директории
  - Загрузка всех компонентов в Arweave
- `action53_UnifiedContractRegistration()`: Unified contract registration для компонентов
  - Регистрация компонентов в OrganicComponentRegistry
  - Обновление tracking-полей с blockchain данными

#### Исправления в проверке шагов
- Изменена проверка завершенности шагов: теперь проверяется `state.arweave` вместо `state`
- Исправлено чтение CID из `state.arweave.root_metadata.cid` вместо `state.root_metadata.cid`

### Цель изменений
Добавить поддержку resume capability (USE_EXISTING_CIDS), интеграцию ComponentTracking для отслеживания изменений компонентов, и новые unified функции для загрузки и регистрации компонентов.

---

## Группа 5: Unit Tests - Обновление тестов для новых функций

### Файлы
- `scripts/tests/unit/actions/ComponentActions.test.js`
- `scripts/tests/unit/actions/CatalogActions.test.js`
- `scripts/tests/unit/lib/upload_steps.test.js`
- `scripts/tests/setup.js`

### Что изменено

#### ComponentActions.test.js
- **До:** Только тесты для `action555()` как монолитной функции
- **После:** Разделение тестов на отдельные describe блоки:
  - `action51() - Seller Activation`: тесты активации seller
  - `action52() - Arweave Upload`: тесты загрузки в Arweave
  - `action53() - Contract Registration`: тесты регистрации в контракте
  - `action555() - Composite Pipeline (51 → 52 → 53)`: тесты композитного pipeline
- Добавлены тесты для проверки статуса активации
- Добавлены тесты для валидации через blockchain

#### upload_steps.test.js
- Добавлены тесты для `updateRootMetadata() - ComponentTracking Integration`
- Добавлены тесты для `action52_UnifiedArweaveUpload()`
- Добавлены тесты для `action52_UnifiedArweaveUpload() - ComponentTracking Integration`
- Добавлены тесты для `action53_UnifiedContractRegistration()`
- Добавлены тесты для `action53_UnifiedContractRegistration() - ComponentTracking Integration`
- Добавлены тесты для `uploadSimpleFields() - USE_EXISTING_CIDS`:
  - Тест пропуска загрузки при наличии существующих CID
  - Тест fallback на загрузку при отсутствии CID
  - Тест fallback при частичном отсутствии CID

#### CatalogActions.test.js
- Обновлены тесты для совместимости с новыми сигнатурами функций

#### setup.js
- Обновлена конфигурация тестов для новых функций

### Цель изменений
Обеспечить покрытие тестами новых функций (Action 51, 52, 53, USE_EXISTING_CIDS, ComponentTracking) и обновить существующие тесты для совместимости с рефакторингом.

---

## Группа 6: Documentation и Configuration

### Файлы
- `scripts/docs/node-launch.txt`
- `scripts/docs/testing/reference/integration-tests-implementation-reference.md`
- `scripts/deployment/README.md`
- `scripts/deployment/variant-a.json`
- `scripts/clean_components_upload.bash`
- `scripts/lib/actions/index.js`

### Что изменено

#### node-launch.txt
- Обновлена документация для новых actions (51, 52, 53, 555)
- Добавлены примеры использования новых функций

#### integration-tests-implementation-reference.md
- Обновлена документация по интеграционным тестам

#### deployment/README.md
- Добавлена документация по deployment процессу

#### deployment/variant-a.json
- Обновлена конфигурация deployment

#### clean_components_upload.bash
- Обновлен скрипт очистки для совместимости с новыми путями

#### lib/actions/index.js
- Обновлен экспорт новых функций

### Цель изменений
Обновить документацию и конфигурационные файлы для отражения изменений в архитектуре и новых функций.

---

## Удаленные файлы

### Файлы
- `scripts/docs/analysis/documentation-sync-issues.md`

### Причина удаления
Временный документ анализа, больше не актуален после исправления проблем синхронизации путей.

---

## Технические детали

### Зависимости между группами
1. **Группа 1** (CatalogActions) должна быть закоммичена первой, так как изменяет сигнатуры функций
2. **Группа 2** (Validator) зависит от путей, определенных в Группе 1
3. **Группа 3** (ComponentActions) может быть закоммичена независимо
4. **Группа 4** (upload_steps) должна быть закоммичена перед Группой 5 (Tests)
5. **Группа 5** (Tests) зависит от всех предыдущих групп
6. **Группа 6** (Documentation) может быть закоммичена последней

### Обратная совместимость
- Все изменения сохраняют обратную совместимость через fallback логику
- Legacy схема продуктов поддерживается в валидаторе
- Старые пути поддерживаются через поиск в нескольких местах

### Риски
- Изменение сигнатуры `action43_UnifiedContractRegistration` может сломать код, который вызывает эту функцию напрямую (не через Action 43)
- Новые функции (Action 51, 52, 53) требуют правильной последовательности выполнения (51 → 52 → 53)

