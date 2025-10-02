# 📊 Анализ: Текущий процесс наполнения каталога vs Новая мультиязычная архитектура

## 🔍 Детальная таблица соответствий

| # | Этап старого процесса | Текущий скрипт | Источник данных | Локализуемое поле | Тип поля | Новый процесс | Куда грузить |
|---|---|---|---|---|---|---|---|
| **1. ИЗОБРАЖЕНИЯ** |
| 1.1 | Загрузка изображений в IPFS | `upload_catalog_images.py` | `bot/catalog/*.{jpg,png}` | - | - | **Без изменений** | Pinata/Arweave → `catalog_images.json` |
| **2. ОПИСАНИЯ КОМПОНЕНТОВ** |
| 2.1 | Загрузка описаний биоединиц | `upload_organic_descriptions.py` | `organic_descriptions.json` | `title` | SIMPLE | **MultilingualDescriptionsUploader** | `ComponentDescription.generic_description` → AmanitaInternational → IPFS |
| 2.2 | | | | `scientific_name` | SIMPLE | | `Description.scientific_name` → AmanitaInternational → IPFS |
| 2.3 | | | | `generic_description` | COMPLEX | | `ComponentDescription.ru` → IPFS, CID → AmanitaInternational |
| 2.4 | | | | `effects` | COMPLEX | | `ComponentDescription.ru` → IPFS, CID → AmanitaInternational |
| 2.5 | | | | `shamanic` | COMPLEX | | `ComponentDescription.ru` → IPFS, CID → AmanitaInternational |
| 2.6 | | | | `warnings` | COMPLEX | | `ComponentDescription.ru` → IPFS, CID → AmanitaInternational |
| 2.7 | | | | `features` | COMPLEX | | `ComponentDescription.ru` → IPFS, CID → AmanitaInternational |
| 2.8 | | | | `dosage_instructions` | COMPLEX | | Вложенный объект, см. ниже |
| 2.8.1 | | | | `dosage_instructions[].type` | SIMPLE | | `DosageInstruction.type` → AmanitaInternational → IPFS |
| 2.8.2 | | | | `dosage_instructions[].title` | COMPLEX | | `DosageInstruction.ru` → IPFS, CID → AmanitaInternational |
| 2.8.3 | | | | `dosage_instructions[].description` | COMPLEX | | `DosageInstruction.ru` → IPFS, CID → AmanitaInternational |
| **3. КАТАЛОГ ПРОДУКТОВ** |
| 3.1 | Конвертация CSV → JSON | `catalog_csv2json.py` | `Iveta_catalog.csv` | `product_name` → `title` | SIMPLE | **MultilingualCatalogConverter** | `Product.title` → AmanitaInternational → IPFS |
| 3.2 | | | | `species` | SIMPLE | | `Product.species` → AmanitaInternational → IPFS |
| 3.3 | | | | `form` → `forms[]` | SIMPLE | | `Product.forms` → AmanitaInternational → IPFS |
| 3.4 | | | | `categories[]` | - | | **Не локализуется** (технические теги) |
| 3.5 | | | | `cover_image_url` | - | | **Не локализуется** (CID изображения) |
| 3.6 | | | | `prices[]` | - | | **Не локализуется** (числовые данные) |
| 3.7 | | | | `business_id` | - | | **Не локализуется** (идентификатор) |
| **4. ПОДГОТОВКА К СМАРТ-КОНТРАКТУ** |
| 4.1 | Создание отдельных JSON для продуктов | `prepare_products_for_registry.py` | `active_catalog.json` | - | - | **MultilingualRegistryPreparer** | Генерация JSON с CID переводов из AmanitaInternational |
| 4.2 | Загрузка JSON в IPFS | | `product_jsons/{id}.json` | - | - | | Загрузка мультиязычных JSON с ссылками на переводы |
| 4.3 | Формирование маппинга для контракта | | → `product_registry_upload_data.json` | - | - | | Без изменений |
| **5. ЗАГРУЗКА В БЛОКЧЕЙН** |
| 5.1 | Загрузка продуктов в ProductRegistry | `catalog_pipeline.py` + `deploy_full.js` (action=4) | `product_registry_upload_data.json` | - | - | **Без изменений** | ProductRegistry контракт |

---

## 📝 Легенда типов полей

### SIMPLE - простое поле (enum/title)
**Структура**: Все языки в одном CID
```json
{
  "ru": "Порошок",
  "en": "Powder",
  "de": "Pulver",
  "fr": "Poudre",
  "es": "Polvo"
}
```
**Ключ в AmanitaInternational**: `class.field` (например, `Product.forms`)

**Примеры**:
- `Product.title` - название продукта
- `Product.species` - биологический вид
- `Product.forms` - форма выпуска (powder, capsules, tea)
- `DosageInstruction.type` - тип дозировки (dried, tincture, extract)

---

### COMPLEX - сложное описательное поле
**Структура**: Каждый язык в отдельном CID
```json
// ComponentDescription.ru в IPFS
{
  "generic_description": "Подробное описание на русском...",
  "effects": "Эффекты на русском...",
  "shamanic": "Шаманская перспектива...",
  "warnings": "Предупреждения...",
  "features": ["Особенность 1", "Особенность 2"]
}

// ComponentDescription.en в IPFS (отдельный CID)
{
  "generic_description": "Detailed description in English...",
  "effects": "Effects in English...",
  "shamanic": "Shamanic perspective...",
  "warnings": "Warnings...",
  "features": ["Feature 1", "Feature 2"]
}
```
**Ключ в AmanitaInternational**: `class.language` (например, `ComponentDescription.ru`)

**Примеры**:
- `ComponentDescription` - описание компонента (все поля разом)
- `DosageInstruction` - инструкции по дозировке (title + description)

---

## 🔄 Сравнение процессов: БЫЛО vs СТАНЕТ

### БЫЛО (старый процесс)
```
1. organic_descriptions.json (RU only)
   ↓ [upload_organic_descriptions.py]
2. IPFS → CID для каждой biounit
   ↓ [organic_cid_mapping.json]
3. Iveta_catalog.csv (RU only)
   ↓ [catalog_csv2json.py]
4. active_catalog.json (RU only)
   ↓ [prepare_products_for_registry.py]
5. IPFS → CID для каждого продукта
   ↓ [product_registry_upload_data.json]
6. ProductRegistry.sol (blockchain)
```

**Проблема**: Все тексты только на русском, нет возможности локализации.

**Пример старого формата**:
```json
{
  "business_id": "amanita_powder",
  "title": "Мухомор красный молотый",
  "species": "Мухомор красный (Amanita muscaria)",
  "forms": ["powder"],
  "organic_components": [{
    "biounit_id": "amanita_muscaria",
    "description_cid": "QmXXX...",  // ← CID с описанием ТОЛЬКО на русском
    "proportion": "100%"
  }]
}
```

---

### СТАНЕТ (новый процесс с локализацией)

```
1. multilingual_components.json (RU + переводы)
   {
     "amanita_muscaria": {
       "translations": {
         "title": {"ru": "Мухомор", "en": "Amanita"},
         "descriptions": {
           "ru": {"generic_description": "...", "effects": "..."},
           "en": {"generic_description": "...", "effects": "..."}
         }
       }
     }
   }
   ↓ [MultilingualDescriptionsUploader]
   
2a. IPFS (SIMPLE fields)
    Product.title → {"ru": "Мухомор", "en": "Amanita", ...} → CID_title_all
    Product.forms → {"ru": "Порошок", "en": "Powder", ...} → CID_forms_all
    ↓
    
2b. IPFS (COMPLEX fields)
    ComponentDescription.ru → {generic_description, effects, ...} → CID_comp_ru
    ComponentDescription.en → {generic_description, effects, ...} → CID_comp_en
    ComponentDescription.de → {generic_description, effects, ...} → CID_comp_de
    ↓
   
3. AmanitaInternational.sol (blockchain)
   simpleFieldCIDs["Product.title"] = CID_title_all
   simpleFieldCIDs["Product.forms"] = CID_forms_all
   complexFieldCIDs["ComponentDescription.ru"] = CID_comp_ru
   complexFieldCIDs["ComponentDescription.en"] = CID_comp_en
   complexFieldCIDs["ComponentDescription.de"] = CID_comp_de
   ↓
   
4. multilingual_catalog.csv (базовая информация)
   ↓ [MultilingualCatalogConverter]
   
5. active_catalog_multilingual.json
   {
     "business_id": "amanita_powder",
     "title_label": "Product.title",  // ← ссылка на AmanitaInternational
     "species_label": "Product.species",
     "forms_label": "Product.forms",
     "organic_components": [{
       "biounit_id": "amanita_muscaria",
       "description_label": "ComponentDescription"  // ← ссылка на AmanitaInternational
     }]
   }
   ↓ [MultilingualRegistryPreparer]
   
6. IPFS → CID для каждого продукта (с лейблами)
   ↓ [product_registry_upload_data.json]
   
7. ProductRegistry.sol (blockchain)
```

**Преимущество нового формата**:
```json
{
  "business_id": "amanita_powder",
  "title_label": "Product.title",  // ← лейбл вместо текста
  "species_label": "Product.species",
  "forms_label": "Product.forms",
  "organic_components": [{
    "biounit_id": "amanita_muscaria",
    "description_label": "ComponentDescription",  // ← лейбл вместо CID
    "proportion": "100%"
  }]
}
```

**Получение данных в боте**:
1. Бот получает `title_label = "Product.title"`
2. Запрашивает `AmanitaInternational.simpleFieldCIDs["Product.title"]` → `CID_title_all`
3. Загружает из IPFS `CID_title_all` → `{"ru": "Мухомор", "en": "Amanita", ...}`
4. Кэширует на всех уровнях
5. Показывает пользователю `translations[user_lang]`

---

## 🆕 Новые компоненты для загрузки

### 1. Структура мультиязычных компонентов

**Новый файл**: `bot/catalog/multilingual_components.json`

```json
{
  "components": {
    "amanita_muscaria": {
      "biounit_id": "amanita_muscaria",
      "translations": {
        "title": {
          "ru": "Мухомор красный",
          "en": "Amanita Muscaria",
          "de": "Roter Fliegenpilz",
          "fr": "Amanite tue-mouches",
          "es": "Amanita muscaria"
        },
        "scientific_name": {
          "ru": "Amanita muscaria",
          "en": "Amanita muscaria",
          "de": "Amanita muscaria",
          "fr": "Amanita muscaria",
          "es": "Amanita muscaria"
        },
        "descriptions": {
          "ru": {
            "generic_description": "Мухомор красный — это известный гриб с ярко-красной шляпкой, покрытой белыми пятнами. Традиционно используется в народной медицине и шаманских практиках на протяжении тысячелетий.",
            "effects": "Традиционно используется для улучшения настроения, снижения тревожности, улучшения сна и повышения общего тонуса организма. Обладает адаптогенными свойствами.",
            "shamanic": "В шаманских практиках используется для достижения изменённых состояний сознания, духовного развития и связи с природными силами. Особенно популярен в сибирских традициях.",
            "warnings": "Не рекомендуется беременным и кормящим женщинам, детям до 18 лет, людям с заболеваниями печени и почек. Перед употреблением проконсультируйтесь со специалистом.",
            "features": [
              "Содержит мусцимол и иботеновую кислоту",
              "Традиционное использование в Сибири",
              "Адаптогенные свойства",
              "Улучшает качество сна"
            ]
          },
          "en": {
            "generic_description": "Amanita muscaria is a well-known mushroom with a bright red cap covered in white spots. Traditionally used in folk medicine and shamanic practices for thousands of years.",
            "effects": "Traditionally used to improve mood, reduce anxiety, improve sleep quality, and increase overall vitality. Has adaptogenic properties.",
            "shamanic": "In shamanic practices, it is used to achieve altered states of consciousness, spiritual development, and connection with natural forces. Especially popular in Siberian traditions.",
            "warnings": "Not recommended for pregnant and breastfeeding women, children under 18, people with liver and kidney diseases. Consult a specialist before use.",
            "features": [
              "Contains muscimol and ibotenic acid",
              "Traditional use in Siberia",
              "Adaptogenic properties",
              "Improves sleep quality"
            ]
          },
          "de": {
            "generic_description": "Der Rote Fliegenpilz ist ein bekannter Pilz mit einem leuchtend roten Hut, der mit weißen Flecken bedeckt ist. Wird seit Jahrtausenden in der Volksmedizin und schamanischen Praktiken verwendet.",
            "effects": "Traditionell zur Verbesserung der Stimmung, Verringerung von Angstzuständen, Verbesserung der Schlafqualität und Steigerung der allgemeinen Vitalität verwendet. Hat adaptogene Eigenschaften.",
            "shamanic": "In schamanischen Praktiken wird er verwendet, um veränderte Bewusstseinszustände zu erreichen, spirituelle Entwicklung und Verbindung mit natürlichen Kräften. Besonders beliebt in sibirischen Traditionen.",
            "warnings": "Nicht empfohlen für schwangere und stillende Frauen, Kinder unter 18 Jahren, Menschen mit Leber- und Nierenerkrankungen. Vor der Anwendung einen Spezialisten konsultieren.",
            "features": [
              "Enthält Muscimol und Ibotensäure",
              "Traditionelle Verwendung in Sibirien",
              "Adaptogene Eigenschaften",
              "Verbessert die Schlafqualität"
            ]
          }
        }
      },
      "dosage_instructions": {
        "dried": {
          "translations": {
            "type": {
              "ru": "Сушёный",
              "en": "Dried",
              "de": "Getrocknet",
              "fr": "Séché",
              "es": "Seco"
            },
            "descriptions": {
              "ru": {
                "title": "Дозировка сушёного мухомора",
                "description": "Начинайте с 0.5-1 грамма сушёных шляпок. Постепенно увеличивайте дозировку в течение нескольких недель, следя за своим самочувствием. Максимальная безопасная дозировка - 5-7 грамм в день."
              },
              "en": {
                "title": "Dried Amanita Dosage",
                "description": "Start with 0.5-1 gram of dried caps. Gradually increase the dosage over several weeks, monitoring your well-being. Maximum safe dosage is 5-7 grams per day."
              },
              "de": {
                "title": "Dosierung von getrocknetem Fliegenpilz",
                "description": "Beginnen Sie mit 0,5-1 Gramm getrockneter Hüte. Erhöhen Sie die Dosierung schrittweise über mehrere Wochen und achten Sie auf Ihr Wohlbefinden. Die maximale sichere Dosierung beträgt 5-7 Gramm pro Tag."
              }
            }
          }
        },
        "tincture": {
          "translations": {
            "type": {
              "ru": "Настойка",
              "en": "Tincture",
              "de": "Tinktur",
              "fr": "Teinture",
              "es": "Tintura"
            },
            "descriptions": {
              "ru": {
                "title": "Дозировка спиртовой настойки",
                "description": "Принимайте 10-20 капель настойки 2-3 раза в день. Можно разводить в воде или чае. Начинайте с минимальной дозировки."
              },
              "en": {
                "title": "Alcohol Tincture Dosage",
                "description": "Take 10-20 drops of tincture 2-3 times a day. Can be diluted in water or tea. Start with the minimum dosage."
              }
            }
          }
        }
      }
    },
    "blue_lotus": {
      "biounit_id": "blue_lotus",
      "translations": {
        "title": {
          "ru": "Голубой лотос",
          "en": "Blue Lotus",
          "de": "Blaue Lotusblume"
        },
        "scientific_name": {
          "ru": "Nymphaea caerulea",
          "en": "Nymphaea caerulea",
          "de": "Nymphaea caerulea"
        },
        "descriptions": {
          "ru": {
            "generic_description": "Голубой лотос — священное растение древнего Египта, известное своими расслабляющими и легкими психоактивными свойствами.",
            "effects": "Оказывает мягкое расслабляющее действие, улучшает настроение, способствует медитации и осознанным сновидениям.",
            "shamanic": "Использовался в древнеегипетских ритуалах для достижения духовного просветления и связи с божественным.",
            "warnings": "Не рекомендуется беременным и кормящим. Может вызывать сонливость.",
            "features": [
              "Традиции древнего Египта",
              "Улучшает качество сна",
              "Способствует осознанным сновидениям"
            ]
          },
          "en": {
            "generic_description": "Blue Lotus is a sacred plant of ancient Egypt, known for its relaxing and mild psychoactive properties.",
            "effects": "Provides gentle relaxation, improves mood, supports meditation and lucid dreaming.",
            "shamanic": "Used in ancient Egyptian rituals to achieve spiritual enlightenment and connection with the divine.",
            "warnings": "Not recommended for pregnant and breastfeeding women. May cause drowsiness.",
            "features": [
              "Ancient Egyptian traditions",
              "Improves sleep quality",
              "Supports lucid dreaming"
            ]
          }
        }
      }
    }
  }
}
```

**Новый скрипт**: `bot/utility/upload_multilingual_components.py`

**Функциональность**:
1. Читает `multilingual_components.json`
2. Для каждого компонента:
   - Извлекает SIMPLE fields (`title`, `scientific_name`, `dosage.type`)
   - Создает JSON для каждого SIMPLE field с всеми языками
   - Загружает в IPFS → получает CID
   - Сохраняет `label → CID` локально
3. Для каждого компонента:
   - Извлекает COMPLEX fields (`descriptions`, `dosage.descriptions`)
   - Для каждого языка создает отдельный JSON со всеми полями класса
   - Загружает в IPFS → получает CID
   - Сохраняет `class.language → CID` локально
4. Сохраняет маппинг в `component_translations_mapping.json`

---

### 2. Структура переводов продуктов

**Новый файл**: `bot/catalog/product_translations.json`

```json
{
  "amanita_powder": {
    "title": {
      "ru": "Мухомор красный молотый",
      "en": "Amanita Muscaria Powder",
      "de": "Roter Fliegenpilz Pulver",
      "fr": "Poudre d'Amanite tue-mouches",
      "es": "Polvo de Amanita muscaria"
    },
    "species": {
      "ru": "Мухомор красный (Amanita muscaria)",
      "en": "Amanita muscaria (Fly Agaric)",
      "de": "Amanita muscaria (Roter Fliegenpilz)",
      "fr": "Amanita muscaria (Amanite tue-mouches)",
      "es": "Amanita muscaria"
    },
    "forms": {
      "powder": {
        "ru": "Порошок",
        "en": "Powder",
        "de": "Pulver",
        "fr": "Poudre",
        "es": "Polvo"
      }
    }
  },
  "blue_lotus_flowers": {
    "title": {
      "ru": "Голубой лотос (цветы)",
      "en": "Blue Lotus Flowers",
      "de": "Blaue Lotusblüten"
    },
    "species": {
      "ru": "Голубой лотос (Nymphaea caerulea)",
      "en": "Blue Lotus (Nymphaea caerulea)",
      "de": "Blauer Lotus (Nymphaea caerulea)"
    },
    "forms": {
      "flower": {
        "ru": "Цветы",
        "en": "Flowers",
        "de": "Blüten"
      }
    }
  }
}
```

**Новый скрипт**: `bot/utility/upload_product_translations.py`

**Функциональность**:
1. Читает `product_translations.json`
2. Для каждого SIMPLE field (`Product.title`, `Product.species`, `Product.forms`):
   - Создает JSON со всеми языками
   - Загружает в IPFS → получает CID
   - Сохраняет `label → CID` локально
3. Сохраняет маппинг в `product_translations_mapping.json`

---

### 3. Модифицированный каталог с лейблами

**Модифицированный скрипт**: `bot/utility/create_multilingual_catalog.py`

**Функциональность**:
1. Читает `Iveta_catalog.csv` (базовая информация о продуктах)
2. Читает `product_translations_mapping.json` (лейблы для SIMPLE fields)
3. Читает `component_translations_mapping.json` (лейблы для компонентов)
4. Создает `active_catalog_multilingual.json`:

```json
[
  {
    "business_id": "amanita_powder",
    "title_label": "Product.title",
    "species_label": "Product.species",
    "forms_label": "Product.forms",
    "categories": ["mushroom", "adaptogen", "shamanic"],
    "cover_image_url": "QmRqMjpkLihEsCSJJS4B3WjwW5ZhGm33PHfVw6MxQuo1ru",
    "organic_components": [
      {
        "biounit_id": "amanita_muscaria",
        "description_label": "ComponentDescription",
        "proportion": "100%"
      }
    ],
    "prices": [
      {
        "weight": "50",
        "weight_unit": "g",
        "price": "20",
        "currency": "EUR"
      },
      {
        "weight": "100",
        "weight_unit": "g",
        "price": "35",
        "currency": "EUR"
      }
    ]
  },
  {
    "business_id": "blue_lotus_flowers",
    "title_label": "Product.title",
    "species_label": "Product.species",
    "forms_label": "Product.forms",
    "categories": ["plant", "mental health", "focus"],
    "cover_image_url": "QmT5RC6Q6MRRF3YoDcXmKamKntXT6oSvxk3G2aLDkPc17T",
    "organic_components": [
      {
        "biounit_id": "blue_lotus",
        "description_label": "ComponentDescription",
        "proportion": "100%"
      }
    ],
    "prices": [
      {
        "weight": "100",
        "weight_unit": "g",
        "price": "30",
        "currency": "EUR"
      }
    ]
  }
]
```

---

### 4. Подготовка к загрузке в ProductRegistry

**Модифицированный скрипт**: `bot/utility/prepare_multilingual_registry.py`

**Функциональность**:
1. Читает `active_catalog_multilingual.json`
2. Для каждого продукта:
   - Создает отдельный JSON файл с лейблами
   - Загружает в IPFS → получает CID
   - Сохраняет маппинг `business_id → CID` в `product_registry_upload_data.json`

**Выходной формат** (`product_registry_upload_data.json`):
```json
[
  {
    "id": "amanita_powder",
    "ipfsCID": "QmNewCID123...",
    "active": true
  },
  {
    "id": "blue_lotus_flowers",
    "ipfsCID": "QmNewCID456...",
    "active": true
  }
]
```

---

## 🎯 Ключевые отличия новой архитектуры

### 1. Разделение данных и переводов

**БЫЛО**:
```json
{
  "title": "Мухомор красный",  // ← захардкожено на русском
  "description": "Описание на русском..."
}
```

**СТАНЕТ**:
```json
{
  "title_label": "Product.title",  // ← ссылка на AmanitaInternational
  "description_label": "ComponentDescription"
}
```

Переводы хранятся отдельно в IPFS и получаются динамически через AmanitaInternational.

---

### 2. Загрузка компонентов

**БЫЛО**:
- `organic_descriptions.json` только на русском
- Загружался целиком для каждой biounit
- Один CID на весь компонент

**СТАНЕТ**:
- `multilingual_components.json` с переводами
- Разделяется на SIMPLE/COMPLEX fields
- SIMPLE fields: 1 CID на поле (все языки)
- COMPLEX fields: 1 CID на класс.язык

---

### 3. Загрузка продуктов

**БЫЛО**:
```
CSV → JSON с текстами → IPFS → CID
```

**СТАНЕТ**:
```
CSV + translations.json → JSON с лейблами → IPFS → CID
```

---

### 4. Получение данных в боте

**БЫЛО**:
1. Загрузить JSON продукта → `title = "Мухомор красный"`
2. Показать пользователю

**СТАНЕТ**:
1. Загрузить JSON продукта → `title_label = "Product.title"`
2. Запросить AmanitaInternational.simpleFieldCIDs["Product.title"] → `CID_all`
3. Загрузить из IPFS `CID_all` → `{"ru": "Мухомор", "en": "Amanita", ...}`
4. Кэшировать (Memory → File → IPFS)
5. Показать пользователю `translations[user_lang]`

---

## 📦 План создания с нуля

### Этап A: Подготовка данных

#### A1. Создание `multilingual_components.json`
**Действия**:
1. Взять текущий `organic_descriptions.json`
2. Для каждого компонента создать структуру с переводами
3. Пометить SIMPLE fields (`title`, `scientific_name`, `dosage.type`)
4. Пометить COMPLEX fields (`descriptions`, `dosage.descriptions`)
5. Добавить переводы на английский (минимум)

**Инструмент**: Ручное редактирование + ИИ для перевода

---

#### A2. Создание `product_translations.json`
**Действия**:
1. Взять текущий `Iveta_catalog.csv`
2. Выделить локализуемые поля (`title`, `species`, `forms`)
3. Создать структуру с переводами
4. Добавить переводы на английский (минимум)

**Инструмент**: Ручное редактирование + ИИ для перевода

---

### Этап B: Загрузка переводов

#### B1. Загрузка SIMPLE fields компонентов в IPFS
**Команда**:
```bash
python3 bot/utility/upload_multilingual_components.py --type=simple
```

**Процесс**:
1. Читает `multilingual_components.json`
2. Для каждого SIMPLE field:
   - Создает JSON со всеми языками
   - Загружает в IPFS → CID
   - Сохраняет `label → CID` в `component_simple_mapping.json`

**Пример вывода**:
```json
{
  "ComponentDescription.title": "QmSimple123...",
  "Description.scientific_name": "QmSimple456...",
  "DosageInstruction.type": "QmSimple789..."
}
```

---

#### B2. Загрузка COMPLEX fields компонентов в IPFS
**Команда**:
```bash
python3 bot/utility/upload_multilingual_components.py --type=complex
```

**Процесс**:
1. Читает `multilingual_components.json`
2. Для каждого языка в `descriptions`:
   - Создает JSON со всеми полями класса
   - Загружает в IPFS → CID
   - Сохраняет `class.language → CID` в `component_complex_mapping.json`

**Пример вывода**:
```json
{
  "ComponentDescription.ru": "QmComplex123...",
  "ComponentDescription.en": "QmComplex456...",
  "ComponentDescription.de": "QmComplex789...",
  "DosageInstruction.ru": "QmDosage123...",
  "DosageInstruction.en": "QmDosage456..."
}
```

---

#### B3. Загрузка SIMPLE fields продуктов в IPFS
**Команда**:
```bash
python3 bot/utility/upload_product_translations.py
```

**Процесс**:
1. Читает `product_translations.json`
2. Для каждого SIMPLE field (`Product.title`, `Product.species`, `Product.forms`):
   - Создает JSON со всеми языками
   - Загружает в IPFS → CID
   - Сохраняет `label → CID` в `product_simple_mapping.json`

**Пример вывода**:
```json
{
  "Product.title": "QmProduct123...",
  "Product.species": "QmProduct456...",
  "Product.forms": "QmProduct789..."
}
```

---

#### B4. Загрузка маппингов в AmanitaInternational
**Команда**:
```bash
npx hardhat run scripts/deploy_full.js --network mumbai --action=6
```

**Процесс**:
1. Читает все маппинги:
   - `component_simple_mapping.json`
   - `component_complex_mapping.json`
   - `product_simple_mapping.json`
2. Для каждого маппинга:
   - Вызывает `AmanitaInternational.setSimpleFieldCID(label, CID)` или
   - Вызывает `AmanitaInternational.setComplexFieldCID(class, language, CID)`
3. Логирует результаты загрузки

**Ожидаемый вывод**:
```
✅ Загружено 15 SIMPLE field маппингов
✅ Загружено 30 COMPLEX field маппингов (5 классов × 6 языков)
✅ Всего: 45 маппингов
```

---

### Этап C: Создание мультиязычного каталога

#### C1. Создание `active_catalog_multilingual.json`
**Команда**:
```bash
python3 bot/utility/create_multilingual_catalog.py
```

**Процесс**:
1. Читает `Iveta_catalog.csv` (базовая информация)
2. Читает `product_simple_mapping.json` (лейблы для продуктов)
3. Читает `component_simple_mapping.json` и `component_complex_mapping.json` (лейблы для компонентов)
4. Для каждого продукта:
   - Заменяет `title` → `title_label = "Product.title"`
   - Заменяет `species` → `species_label = "Product.species"`
   - Заменяет `forms` → `forms_label = "Product.forms"`
   - Заменяет `description_cid` → `description_label = "ComponentDescription"`
5. Сохраняет `active_catalog_multilingual.json`

---

#### C2. Подготовка к загрузке в ProductRegistry
**Команда**:
```bash
python3 bot/utility/prepare_multilingual_registry.py
```

**Процесс**:
1. Читает `active_catalog_multilingual.json`
2. Для каждого продукта:
   - Создает отдельный JSON файл с лейблами
   - Сохраняет в `bot/catalog/product_jsons/{business_id}.json`
   - Загружает в IPFS → получает CID
   - Сохраняет маппинг в `product_registry_upload_data.json`

---

#### C3. Загрузка в ProductRegistry
**Команда**:
```bash
npx hardhat run scripts/deploy_full.js --network mumbai --action=4
```

**Процесс**: Без изменений, работает с обычным `product_registry_upload_data.json`

---

## ✅ Критерии успеха новой архитектуры

### 1. Данные

- ✅ Все SIMPLE fields загружены в IPFS (1 CID на поле со всеми языками)
- ✅ Все COMPLEX fields загружены в IPFS (1 CID на класс.язык)
- ✅ Все маппинги `label → CID` загружены в AmanitaInternational
- ✅ Все продукты содержат лейблы вместо текстов

### 2. Функциональность

- ✅ Бот корректно получает переводы по лейблам через AmanitaInternational
- ✅ Кэширование работает на всех уровнях (Memory → File → IPFS)
- ✅ Fallback стратегия работает (RU → EN → key → placeholder)
- ✅ Добавление нового языка не требует пересборки каталога

### 3. Производительность

- ✅ Время загрузки продукта < 500ms (с кэшем < 50ms)
- ✅ Переводы кэшируются агрессивно на всех уровнях
- ✅ IPFS запросы минимизированы через батчинг

### 4. Масштабируемость

- ✅ Легко добавлять новые языки (создать JSON, загрузить в IPFS, обновить контракт)
- ✅ Легко обновлять переводы (загрузить новый CID, обновить контракт)
- ✅ Возможность краудсорсинга переводов (будущая функциональность)

---

## 🎉 Заключение

Данная архитектура обеспечивает:

1. **Масштабируемость**: Легко добавлять новые языки без пересборки каталога
2. **Эффективность**: Агрессивное кэширование на всех уровнях (Memory → File → IPFS)
3. **Надежность**: 4-уровневая fallback стратегия для отсутствующих переводов
4. **Децентрализация**: Возможность краудсорсинга переводов через модерацию в будущем
5. **Совместимость**: Полная интеграция с существующим пайплайном загрузки каталога

**Готова к реализации!** 🚀

