# 🛒 WooCommerce Catalog Workflow: Полное руководство

## 📋 Содержание

1. [Обзор рабочего процесса](#обзор-рабочего-процесса)
2. [Генерация WooCommerce ID Mapping](#генерация-woocommerce-id-mapping)
3. [Экспорт каталога в WooCommerce CSV](#экспорт-каталога-в-woocommerce-csv)
4. [Дифф-экспорты (Инкрементальные обновления)](#дифф-экспорты-инкрементальные-обновления)
5. [Работа с Variable Products](#работа-с-variable-products)
6. [Troubleshooting](#troubleshooting)
7. [Примеры сценариев использования](#примеры-сценариев-использования)

---

## Обзор рабочего процесса

### Схема работы

```
┌─────────────────────────────────────────────────────────────────┐
│ БЛОКЧЕЙН (Продукты)                                             │
└───────────────┬─────────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. ПОЛНЫЙ ЭКСПОРТ → WooCommerce CSV (все колонки, без ID)      │
│    python bot/utility/export_to_woocommerce.py                  │
└───────────────┬─────────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────────┐
│ WOOCOMMERCE (Импорт)                                            │
│ → Создаются новые продукты с автоматическими WooCommerce ID    │
└───────────────┬─────────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────────┐
│ WOOCOMMERCE (Экспорт)                                           │
│ Tools → Export → Products                                        │
│ → Скачать CSV с WooCommerce ID + SKU + Meta: business_id       │
└───────────────┬─────────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. ГЕНЕРАЦИЯ MAPPING                                            │
│    python bot/utility/generate_woo_id_mapping.py \              │
│      --input wc-product-export-*.csv                            │
│    → Создаёт woo_id_mapping.json (WooCommerce ID ↔ business_id)│
└───────────────┬─────────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ДИФФ-ЭКСПОРТЫ (Обновления)                                  │
│    python bot/utility/export_to_woocommerce.py \                │
│      --columns "ID,SKU,Regular price" --reuse-woo-id            │
│    → CSV с WooCommerce ID для обновления цен/описаний           │
└─────────────────────────────────────────────────────────────────┘
```

### Основные компоненты

| Компонент | Файл | Назначение |
|-----------|------|-----------|
| **Export Script** | `bot/utility/export_to_woocommerce.py` | Экспорт продуктов из блокчейна в WooCommerce CSV |
| **Mapping Generator** | `bot/utility/generate_woo_id_mapping.py` | Генерация JSON-маппинга WooCommerce ID ↔ business_id |
| **Mapping File** | `data/sellers/{seller}/catalog/woo_id_mapping.json` | JSON с привязкой WooCommerce ID к нашим ID |
| **Export Service** | `bot/services/woocommerce/export.py` | Логика генерации CSV-строк и применения mapping |

---

## Генерация WooCommerce ID Mapping

### Что это?

**Mapping файл** — это JSON, который связывает:
- **WooCommerce ID** (автоматически назначенные при первом импорте)
- **business_id** (наши внутренние ID продуктов)
- **SKU** (уникальный артикул продукта)

Без mapping файла мы не можем обновлять существующие продукты в WooCommerce — каждый экспорт будет создавать **дубликаты**.

### Формат mapping файла v2.0

```json
{
  "version": "2.0",
  "generated_at": "2026-01-07T12:40:21Z",
  "source_file": "wc-product-export-*.csv",
  
  "mappings_by_business_id": {
    "amanita_pantherina_whole": {
      "woo_id": 199,
      "sku": "40_dried",
      "product_type": "variable",
      "blockchain_id": 40,
      "component_ids": 2,
      "form": "dried",
      "variations": [
        {
          "variation_id": 382,
          "attribute_value": "30g",
          "regular_price": "60"
        },
        {
          "variation_id": 383,
          "attribute_value": "50g",
          "regular_price": "100"
        }
      ]
    },
    "simple_product": {
      "woo_id": 100,
      "sku": "10_powder",
      "product_type": "simple",
      "blockchain_id": 10
    }
  },
  
  "mappings_by_sku": {
    "40_dried": {
      "woo_id": 199,
      "business_id": "amanita_pantherina_whole",
      "blockchain_id": 40
    }
  },
  
  "mappings_by_variation_id": {
    "382": {
      "parent_business_id": "amanita_pantherina_whole",
      "parent_woo_id": 199,
      "attribute_value": "30g",
      "regular_price": "60"
    }
  },
  
  "statistics": {
    "total_products": 17,
    "variable_products": 1,
    "simple_products": 16,
    "total_variations": 2,
    "mapped": 17,
    "skipped": 0,
    "duplicates": 0
  }
}
```

### Скрипт: `generate_woo_id_mapping.py`

#### Базовое использование

```bash
# Генерация mapping из WooCommerce экспорта (дефолтная директория: data/sellers/iveta)
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-*.csv
```

#### Все параметры

```bash
python3 bot/utility/generate_woo_id_mapping.py \
  --input <ПУТЬ_К_CSV>                     # WooCommerce export CSV (обязательный)
  --output-dir <ДИРЕКТОРИЯ>                # Где сохранить mapping.json (default: data/sellers/iveta)
  --products-dir <ДИРЕКТОРИЯ>              # Где локальные JSON продуктов (default: data/sellers/iveta/products)
  --verbose                                # Детальное логирование (DEBUG)
  --overwrite                              # Полная перезапись mapping (default: merge)
```

#### Параметры подробно

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `--input` | string | (обязательно) | Путь к CSV-файлу WooCommerce экспорта |
| `--output-dir` | string | `data/sellers/iveta` | Директория для сохранения `catalog/woo_id_mapping.json` |
| `--products-dir` | string | `data/sellers/iveta/products` | Директория с локальными JSON-файлами продуктов (для валидации существования) |
| `--verbose` | flag | false | Включить детальное логирование (DEBUG уровень) |
| `--overwrite` | flag | false | Полная перезапись mapping. **По умолчанию: merge-режим** |

#### Режимы работы

##### 🔄 Merge-режим (по умолчанию)

**Используется:** Когда экспортируешь **только часть каталога** (например, 2-3 продукта для обновления).

**Поведение:**
- Загружает существующий `woo_id_mapping.json`
- Обновляет/добавляет записи для продуктов из нового CSV
- **Сохраняет** продукты, которых нет в новом CSV
- Мержит вариации по `variation_id`

**Пример:**

```bash
# Экспортировали из WooCommerce 2 продукта для обновления
# Mapping будет обновлён только для этих 2 продуктов, остальные 15 останутся
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-partial.csv
```

**Вывод (пример):**

```
======================================================================
РЕЗУЛЬТАТЫ (MERGE MODE)
======================================================================
Всего продуктов: 17
  - Variable продуктов: 1
  - Simple продуктов: 16
Всего вариаций: 5

Merge статистика:
  Обновлено продуктов: 2
  Новых продуктов: 0
  Без изменений: 15
  Обновлено вариаций: 3
  Новых вариаций: 2

Записей по business_id: 17
Записей по SKU: 17
Записей по variation_id: 5

✅ Маппинг сохранён в: data/sellers/iveta/catalog/woo_id_mapping.json
```

##### ⚠️ Overwrite-режим (флаг `--overwrite`)

**Используется:** Когда экспортируешь **весь каталог** заново (полная синхронизация).

**Поведение:**
- **Полностью перезаписывает** `woo_id_mapping.json`
- Удаляет продукты, которых нет в новом CSV
- Используется для "чистого старта"

**Пример:**

```bash
# Полный экспорт всех продуктов из WooCommerce
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-full.csv \
  --overwrite
```

#### Примеры использования

##### 1. Первичная генерация mapping (после первого импорта в WooCommerce)

```bash
# 1. Экспортировать все продукты из WooCommerce (Tools → Export → Products)
# 2. Скачать CSV файл (например, wc-product-export-7-1-2026-*.csv)
# 3. Сгенерировать mapping:

python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-7-1-2026-1767787818987.csv \
  --output-dir data/sellers/iveta
```

##### 2. Обновление mapping после добавления новых продуктов

```bash
# WooCommerce экспорт содержит ТОЛЬКО новые продукты (2-3 шт)
# Merge-режим автоматически добавит их к существующему mapping

python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-new-products.csv
```

##### 3. Обновление вариаций variable продукта

```bash
# Экспортировали из WooCommerce 1 variable продукт с новыми вариациями
# Merge-режим обновит вариации, не трогая другие продукты

python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-updated-variations.csv \
  --verbose  # Детальный лог для проверки merge
```

##### 4. Полная пересинхронизация (редко используется)

```bash
# ВНИМАНИЕ: Удалит все продукты, которых нет в новом CSV!
# Используй только при полном экспорте всего каталога

python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-full.csv \
  --overwrite
```

##### 5. Другой продавец (не iveta)

```bash
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/john/catalog/wc-product-export-*.csv \
  --output-dir data/sellers/john \
  --products-dir data/sellers/john/products
```

#### Валидация и проверки

Скрипт выполняет следующие проверки:

1. **Валидация CSV:**
   - Наличие обязательных колонок: `ID`, `SKU`, `Meta: business_id` (для не-вариаций)
   - Корректность типов данных (ID — число)

2. **Определение типа продукта:**
   - `variable` — родительский продукт с вариациями
   - `variation` — вариация продукта (нет SKU и business_id)
   - `simple` — простой продукт

3. **Связывание вариаций:**
   - Вариации идут **все вместе после всех родителей** в WooCommerce экспорте
   - Скрипт корректно связывает их по количеству и атрибутам

4. **Проверка локальных продуктов:**
   - Валидирует существование локальных JSON-файлов продуктов
   - Логирует, сколько продуктов найдено

#### Что делать, если ошибки?

##### Ошибка: "Отсутствуют обязательные колонки: ID, SKU, Meta: business_id"

**Причина:** CSV-файл не содержит нужных колонок.

**Решение:** При экспорте из WooCommerce включите Custom Meta Fields:
- `Meta: business_id`
- `Meta: blockchain_id`
- `Meta: component_ids`

##### Ошибка: "Не удалось прочитать ни одной валидной строки из CSV"

**Причина:** Все строки в CSV имеют невалидные данные.

**Решение:** Проверьте структуру CSV, убедитесь что:
- ID — числа
- SKU заполнены (для не-вариаций)
- business_id заполнены (для не-вариаций)

##### Предупреждение: "Родитель X: ожидалось N вариаций, найдено M"

**Причина:** Количество вариаций не соответствует списку атрибутов родителя.

**Действие:** Проверьте в WooCommerce, что все вариации присутствуют.

---

## Экспорт каталога в WooCommerce CSV

### Скрипт: `export_to_woocommerce.py`

#### Базовое использование

```bash
# Полный экспорт на русском языке в файл по умолчанию
python3 bot/utility/export_to_woocommerce.py
```

#### Все параметры

```bash
python3 bot/utility/export_to_woocommerce.py \
  --language <ЯЗЫК>                        # Язык локализации (default: ru)
  --output <ПУТЬ>                          # Путь к CSV (default: data/sellers/{seller}/catalog/woocommerce_products.csv)
  --seller-name <ИМЯ>                      # Имя продавца (default: из SELLER_BUSINESS_ID или 'iveta')
  --columns "<КОЛОНКИ>"                    # Список колонок через запятую (default: все)
  --reuse-woo-id                           # Использовать WooCommerce ID из mapping
  --mapping <ПУТЬ>                         # Путь к mapping.json (default: data/sellers/{seller}/catalog/woo_id_mapping.json)
```

#### Параметры подробно

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `--language` | string | `ru` | Язык локализации (`ru`, `en`) |
| `--output` | string | `data/sellers/{seller}/catalog/woocommerce_products.csv` | Путь к выходному CSV |
| `--seller-name` | string | из `SELLER_BUSINESS_ID` или `iveta` | Имя продавца для путей |
| `--columns` | string | `None` (все) | Список колонок через запятую. Пример: `"ID,SKU,Regular price"` |
| `--reuse-woo-id` | flag | false | Добавить колонку `ID` с WooCommerce ID из mapping |
| `--mapping` | string | `data/sellers/{seller}/catalog/woo_id_mapping.json` | Путь к mapping файлу |

#### Режимы работы

##### 🆕 Полный экспорт (первый импорт в WooCommerce)

**Используется:** Когда продукты **еще не загружены** в WooCommerce.

**Поведение:**
- Экспортируются **все колонки**
- **Нет** колонки `ID` (WooCommerce создаст ID автоматически)
- Включены все метаданные (`Meta: business_id`, `Meta: blockchain_id`)

**Пример:**

```bash
python3 bot/utility/export_to_woocommerce.py \
  --language ru \
  --output data/sellers/iveta/catalog/woocommerce_products.csv
```

**Что дальше:**
1. Импортировать CSV в WooCommerce (Tools → Import → Products)
2. Экспортировать из WooCommerce (чтобы получить WooCommerce ID)
3. Сгенерировать mapping файл (см. раздел выше)

##### 🔄 Дифф-экспорт: Обновление цен

**Используется:** Когда нужно обновить **только цены** существующих продуктов.

**Поведение:**
- Экспортируются только колонки: `ID`, `SKU`, `Regular price`
- `ID` берётся из mapping файла
- SKU — для идентификации продукта

**Пример:**

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price" \
  --reuse-woo-id
```

**Что дальше:**
- Импортировать CSV в WooCommerce с опцией **Update existing products**

##### 🔄 Дифф-экспорт: Обновление описаний

**Используется:** Когда нужно обновить **только описания** существующих продуктов.

**Пример:**

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Description,Short description" \
  --reuse-woo-id
```

##### 🔄 Дифф-экспорт: Обновление мета-полей

**Пример:**

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Meta: blockchain_id,Meta: component_ids,Meta: form" \
  --reuse-woo-id
```

#### Примеры использования

##### 1. Первичный экспорт (полный каталог на русском)

```bash
python3 bot/utility/export_to_woocommerce.py \
  --language ru \
  --output data/sellers/iveta/catalog/woocommerce_products.csv
```

**Лог:**

```
🚀 Запуск экспорта продуктов в WooCommerce CSV
📋 Seller name из переменной окружения SELLER_BUSINESS_ID: iveta
📋 Output path по умолчанию: /path/to/data/sellers/iveta/catalog/woocommerce_products.csv
📋 Параметры: language=ru, seller_name=iveta, output=/path/to/data/sellers/iveta/catalog/woocommerce_products.csv
🔧 Инициализация сервисов...
✅ Сервисы инициализированы
📦 Загрузка продуктов из блокчейна...
✅ Загружено продуктов: 17
📝 Генерация CSV файла...
✅ CSV файл создан: /path/to/data/sellers/iveta/catalog/woocommerce_products.csv
✨ Экспорт завершен успешно
```

##### 2. Экспорт на английском языке

```bash
python3 bot/utility/export_to_woocommerce.py \
  --language en \
  --output data/sellers/iveta/catalog/woocommerce_products_en.csv
```

##### 3. Дифф-экспорт: только цены (с reuse ID)

```bash
# Предварительное условие: woo_id_mapping.json существует
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price" \
  --reuse-woo-id
```

**Лог:**

```
...
✅ Mapping-файл загружен: /path/to/data/sellers/iveta/catalog/woo_id_mapping.json
📊 Статистика mapping: всего продуктов 17, сопоставлено 17, записей по business_id 17, записей по SKU 17
📋 Выбранные колонки (3): ID, SKU, Regular price
...
```

**Результат CSV:**

```csv
ID,SKU,Regular price
194,35_dried,25
195,36_dried,30
196,37_dried,35
```

##### 4. Дифф-экспорт: описания + мета-поля

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Description,Short description,Meta: business_id,Meta: blockchain_id" \
  --reuse-woo-id
```

##### 5. Дифф-экспорт с кастомным mapping файлом

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price" \
  --reuse-woo-id \
  --mapping data/sellers/iveta/catalog/woo_id_mapping_backup.json
```

#### Колонки WooCommerce CSV

Скрипт поддерживает следующие стандартные колонки WooCommerce:

| Колонка | Описание |
|---------|----------|
| `ID` | WooCommerce ID (только с `--reuse-woo-id`) |
| `Type` | Тип продукта (`simple`, `variable`, `variation`) |
| `SKU` | Уникальный артикул |
| `Name` | Название продукта |
| `Published` | Статус публикации (1/0) |
| `Description` | Полное описание (HTML) |
| `Short description` | Краткое описание (HTML) |
| `Regular price` | Обычная цена |
| `Categories` | Категории (через `>`) |
| `Tags` | Теги (через `,`) |
| `Images` | URL изображений (через `,`) |
| `Attribute 1 name` | Имя атрибута (для variable) |
| `Attribute 1 value(s)` | Значения атрибута (для variable) |
| `Attribute 1 visible` | Видимость атрибута (1/0) |
| `Attribute 1 global` | Глобальный атрибут (1/0) |
| `Meta: business_id` | Наш внутренний ID |
| `Meta: blockchain_id` | ID в блокчейне |
| `Meta: component_ids` | ID компонентов (через `,`) |
| `Meta: form` | Форма продукта (`dried`, `powder`) |

#### Что делать, если ошибки?

##### Предупреждение: "Mapping-файл не найден. Колонка ID будет добавлена пустой."

**Причина:** Включён `--reuse-woo-id`, но mapping файл не существует.

**Решение:** Сначала сгенерируйте mapping (см. раздел выше).

##### Ошибка: "Mapping-файл имеет невалидную структуру"

**Причина:** JSON-файл повреждён или имеет неправильный формат.

**Решение:** Пересоздайте mapping файл заново.

##### Предупреждение: "Колонка X указана в --columns, но отсутствует в данных"

**Причина:** Вы указали несуществующую колонку.

**Решение:** Проверьте написание колонки (см. таблицу выше).

---

## Дифф-экспорты (Инкрементальные обновления)

### Зачем нужны дифф-экспорты?

**Проблема:** Полный экспорт всех колонок занимает много времени и загружает большие CSV.

**Решение:** Экспортируй только нужные колонки + `ID` для обновления.

### Типичные сценарии

#### 1. Обновление цен

**Use case:** Изменились цены в блокчейне, нужно синхронизировать с WooCommerce.

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price" \
  --reuse-woo-id
```

**Результат:** CSV ~3KB вместо ~500KB (полный экспорт).

#### 2. Обновление описаний

**Use case:** Обновились текстовые описания компонентов.

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Description,Short description" \
  --reuse-woo-id
```

#### 3. Обновление изображений

**Use case:** Обновились URL изображений в блокчейне.

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Images" \
  --reuse-woo-id
```

#### 4. Обновление мета-полей (для интеграций)

**Use case:** Нужно синхронизировать `blockchain_id` или `component_ids`.

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Meta: blockchain_id,Meta: component_ids,Meta: form" \
  --reuse-woo-id
```

### Как работает `--reuse-woo-id`?

1. **Загрузка mapping:** Скрипт читает `woo_id_mapping.json`
2. **Применение ID:** Для каждой строки CSV:
   - Ищет `business_id` продукта в mapping
   - Добавляет `woo_id` в колонку `ID`
3. **Фильтрация колонок:** Оставляет только указанные в `--columns`
4. **Запись CSV:** CSV готов для импорта в WooCommerce (update mode)

### Важно!

- **Всегда** включай `ID` и `SKU` в `--columns` для дифф-экспортов
- WooCommerce использует `ID` для поиска продукта, `SKU` — как fallback
- Без `ID` WooCommerce создаст новые продукты (дубликаты!)

---

## Работа с Variable Products

### Что такое Variable Product?

**Variable Product** в WooCommerce — это продукт с несколькими вариациями (например, разный вес: 30g, 50g, 100g).

**Структура в CSV:**

```csv
ID,Type,SKU,Regular price,Attribute 1 name,Attribute 1 value(s)
199,variable,40_dried,,weight,"30g, 50g, 100g"
382,variation,,,weight,30g
383,variation,,,weight,50g
384,variation,,,weight,100g
```

### Как работает mapping для Variable Products?

**Структура в `woo_id_mapping.json`:**

```json
{
  "mappings_by_business_id": {
    "amanita_pantherina_whole": {
      "woo_id": 199,
      "sku": "40_dried",
      "product_type": "variable",
      "variations": [
        {
          "variation_id": 382,
          "attribute_value": "30g",
          "regular_price": "60"
        },
        {
          "variation_id": 383,
          "attribute_value": "50g",
          "regular_price": "100"
        },
        {
          "variation_id": 384,
          "attribute_value": "100g",
          "regular_price": "150"
        }
      ]
    }
  },
  "mappings_by_variation_id": {
    "382": {
      "parent_business_id": "amanita_pantherina_whole",
      "parent_woo_id": 199,
      "attribute_value": "30g",
      "regular_price": "60"
    }
  }
}
```

### Генерация mapping для Variable Products

```bash
# WooCommerce экспорт содержит variable продукт + его вариации
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-with-variations.csv
```

**Скрипт автоматически:**
1. Определяет тип каждой строки (`variable`, `variation`, `simple`)
2. Связывает вариации с родительским продуктом
3. Создаёт индекс `mappings_by_variation_id`

### Обновление цен для Variable Product

```bash
# Дифф-экспорт: цены для variable продукта и его вариаций
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price,Attribute 1 value(s)" \
  --reuse-woo-id
```

**Результат CSV:**

```csv
ID,SKU,Regular price,Attribute 1 value(s)
199,40_dried,,"30g, 50g, 100g"
382,,60,30g
383,,100,50g
384,,150,100g
```

### Важные особенности

1. **Вариации не имеют SKU и business_id** в WooCommerce экспорте
2. **Вариации идут ВСЕ ВМЕСТЕ после всех родителей** в CSV (не сразу после своего parent)
3. Скрипт `generate_woo_id_mapping.py` корректно связывает их по:
   - Количеству атрибутов родителя
   - Валидации атрибута вариации

---

## Troubleshooting

### Проблема: "Продукты дублируются при каждом импорте"

**Причина:** Не используется `--reuse-woo-id` или mapping файл не существует.

**Решение:**

1. Убедитесь что `woo_id_mapping.json` создан
2. Используйте флаг `--reuse-woo-id` при экспорте

```bash
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price" \
  --reuse-woo-id
```

### Проблема: "Mapping файл устаревший (не все продукты)"

**Причина:** Mapping создан из старого WooCommerce экспорта.

**Решение:**

1. Экспортируйте **все продукты** из WooCommerce
2. Пересоздайте mapping с флагом `--overwrite`

```bash
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-full.csv \
  --overwrite
```

### Проблема: "Вариации не связываются с родительским продуктом"

**Причина:** WooCommerce экспорт не содержит колонку `Type` или атрибуты некорректны.

**Решение:**

1. Убедитесь что WooCommerce экспорт включает:
   - Колонку `Type`
   - Колонки `Attribute 1 name` и `Attribute 1 value(s)`
2. Проверьте логи скрипта (используйте `--verbose`)

```bash
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export.csv \
  --verbose
```

### Проблема: "Цены не обновляются в WooCommerce"

**Причина:** Неправильный формат цены или отсутствует `ID`.

**Решение:**

1. Убедитесь что CSV содержит колонку `ID` с WooCommerce ID
2. Убедитесь что цены — это строки (не числа)
3. При импорте в WooCommerce включите опцию "Update existing products"

### Проблема: "Скрипт падает с ошибкой 'KeyError: ID'"

**Причина:** Используется `--reuse-woo-id`, но mapping файл пустой или некорректный.

**Решение:**

1. Проверьте структуру `woo_id_mapping.json`
2. Пересоздайте mapping файл

---

## Примеры сценариев использования

### Сценарий 1: Первичная загрузка каталога в WooCommerce

**Шаги:**

```bash
# 1. Полный экспорт из блокчейна (без ID)
python3 bot/utility/export_to_woocommerce.py \
  --language ru \
  --output data/sellers/iveta/catalog/woocommerce_products.csv

# 2. Импорт в WooCommerce (Tools → Import → Products)
#    Загружаем woocommerce_products.csv

# 3. Экспорт из WooCommerce (Tools → Export → Products)
#    Включить Custom Meta Fields: business_id, blockchain_id, component_ids
#    Скачиваем wc-product-export-*.csv

# 4. Генерация mapping
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-*.csv

# ✅ Готово! Теперь можно делать дифф-экспорты
```

### Сценарий 2: Обновление цен (еженедельно)

```bash
# 1. Генерация дифф-CSV с новыми ценами
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price" \
  --reuse-woo-id

# 2. Импорт в WooCommerce (Tools → Import → Products)
#    Update existing products: Yes
#    Match by: ID
```

### Сценарий 3: Добавление новых продуктов

```bash
# 1. Полный экспорт (включая новые продукты)
python3 bot/utility/export_to_woocommerce.py \
  --language ru

# 2. Импорт в WooCommerce
#    Update existing products: Yes (обновит старые)
#    Match by: SKU

# 3. Экспорт из WooCommerce (только новых продуктов!)
#    Фильтруем в WooCommerce по дате создания

# 4. Обновление mapping (merge-режим)
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-new.csv

# ✅ Mapping обновлён, старые продукты сохранены
```

### Сценарий 4: Обновление описаний компонентов

```bash
# 1. Обновили описания в блокчейне (component content)
# 2. Генерация дифф-CSV
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Description,Short description" \
  --reuse-woo-id

# 3. Импорт в WooCommerce (Update existing products)
```

### Сценарий 5: Работа с Variable Products

```bash
# 1. Создали variable продукт с вариациями в WooCommerce вручную
# 2. Экспорт из WooCommerce
# 3. Обновление mapping
python3 bot/utility/generate_woo_id_mapping.py \
  --input data/sellers/iveta/catalog/wc-product-export-with-variations.csv

# 4. Теперь можно обновлять цены вариаций:
python3 bot/utility/export_to_woocommerce.py \
  --columns "ID,SKU,Regular price,Attribute 1 value(s)" \
  --reuse-woo-id

# ✅ Вариации корректно обновляются
```

---

## Быстрая справка по командам

### Генерация mapping

```bash
# Первый раз (после первого импорта в WooCommerce)
python3 bot/utility/generate_woo_id_mapping.py --input wc-export.csv

# Обновление (merge-режим)
python3 bot/utility/generate_woo_id_mapping.py --input wc-export-partial.csv

# Полная перезапись
python3 bot/utility/generate_woo_id_mapping.py --input wc-export-full.csv --overwrite

# Детальный лог
python3 bot/utility/generate_woo_id_mapping.py --input wc-export.csv --verbose
```

### Экспорт каталога

```bash
# Полный экспорт (первый раз)
python3 bot/utility/export_to_woocommerce.py

# Дифф-экспорт: цены
python3 bot/utility/export_to_woocommerce.py --columns "ID,SKU,Regular price" --reuse-woo-id

# Дифф-экспорт: описания
python3 bot/utility/export_to_woocommerce.py --columns "ID,SKU,Description,Short description" --reuse-woo-id

# Дифф-экспорт: изображения
python3 bot/utility/export_to_woocommerce.py --columns "ID,SKU,Images" --reuse-woo-id

# Английский язык
python3 bot/utility/export_to_woocommerce.py --language en
```

---

## Полезные ссылки

- [WooCommerce Product CSV Import Schema](https://woocommerce.com/document/product-csv-import-schema/)
- [WooCommerce Variable Products](https://woocommerce.com/document/variable-product/)
- Формат mapping файла: `bot/docs/analysis/tasks/mapping-format-specification.md`

---

**Версия документа:** 1.0  
**Дата:** 2026-01-07  
**Автор:** AI Assistant (на базе реального кода)

