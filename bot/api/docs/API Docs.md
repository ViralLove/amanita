# API Docs: Интеграция загрузки продуктов, медиа и описаний

## Архитектура интеграции

- Все медиа (изображения, файлы) и описания продуктов хранятся в децентрализованном хранилище (IPFS/Arweave).
- API разделяет загрузку файлов/описаний и создание продукта:
  1. Сначала загружаются файлы/описания, получаются их CID.
  2. Затем создаётся или обновляется продукт, где используются только CID.
- Это обеспечивает повторное использование данных, надёжность и масштабируемость.

---

## Быстрый чек-лист интеграции

1. **Загрузите все изображения через `/media/upload`**
   - Для каждого файла получите CID из ответа.
2. **Загрузите описание продукта через `/description/upload`**
   - Получите CID описания из ответа.
3. **Соберите структуру продукта (см. ниже), подставьте все CID**
4. **Вызовите `/products/upload` с массивом продуктов**
5. **Обрабатывайте ответы и ошибки по каждому продукту**

---

## Пример полного потока

### 1. Загрузка изображения
```http
POST /media/upload
Content-Type: multipart/form-data
file: product.jpg
```
**Ответ:**
```json
{ "cid": "QmImg1...", "filename": "product.jpg", "status": "success" }
```

### 2. Загрузка описания
```http
POST /description/upload
Content-Type: application/json
{
  "id": "desc-123",
  "title": "Amanita Powder",
  "scientific_name": "Amanita muscaria",
  "generic_description": "Высушенный порошок мухомора.",
  "dosage_instructions": [
    { "type": "powder", "title": "Старт", "description": "1 г в день" },
    { "type": "tincture", "title": "Микродозинг", "description": "5 капель" }
  ]
}
```
**Ответ:**
```json
{ "cid": "QmDesc...", "status": "success" }
```

### 3. Создание продукта
```http
POST /products/upload
Content-Type: application/json
{
  "products": [
    {
      "id": "123",
      "title": "Amanita Powder",
      "description": { ... },
      "description_cid": "QmDesc...",
      "cover_image": "QmImg1...",
      "gallery": ["QmImg2...", "QmImg3..."],
      "categories": ["mushrooms"],
      "forms": ["powder"],
      "species": "Amanita muscaria",
      "prices": [
        { "price": "19.99", "currency": "USD" },
        { "price": "29.99", "currency": "USD", "weight": "100", "weight_unit": "g" }
      ],
      "attributes": { "sku": "SKU-123", "stock": 10 }
    }
  ]
}
```
**Ответ:**
```json
{
  "results": [
    {
      "id": "123",
      "blockchain_id": "0x...",
      "tx_hash": "0x...",
      "status": "success"
    }
  ]
}
```

---

## Структура продукта (Product)

- **id**: уникальный идентификатор (строка или число)
- **title**: название продукта
- **description**: вложенный объект (см. ниже)
- **description_cid**: CID описания (обязательно)
- **cover_image**: CID обложки (обязательно)
- **gallery**: массив CID дополнительных изображений (опционально)
- **categories**: массив категорий (опционально)
- **forms**: массив форм продукта (опционально)
- **species**: вид продукта (обязательно)
- **prices**: массив цен (см. ниже)
- **attributes**: любые дополнительные поля (sku, stock, tags и др.)

### Пример структуры цен (prices)
```json
"prices": [
  { "price": "19.99", "currency": "USD" },
  { "price": "29.99", "currency": "USD", "weight": "100", "weight_unit": "g" },
  { "price": "39.99", "currency": "EUR", "form": "premium" }
]
```

### Пример структуры описания (description)
```json
"description": {
  "id": "desc-123",
  "title": "Amanita Powder",
  "scientific_name": "Amanita muscaria",
  "generic_description": "Высушенный порошок мухомора.",
  "effects": "Мягкое расслабление",
  "dosage_instructions": [
    { "type": "powder", "title": "Старт", "description": "1 г в день" },
    { "type": "tincture", "title": "Микродозинг", "description": "5 капель" }
  ]
}
```

---

## Ошибки и best practices

- **Обязательные поля**: если отсутствует хотя бы одно обязательное поле (id, title, description, description_cid, cover_image, species, prices), продукт не будет создан, а в ответе будет подробная ошибка.
- **CID**: всегда используйте только CID, полученные через /media/upload и /description/upload.
- **Batch**: можно загружать несколько продуктов за один запрос (массив products).
- **Обновление**: для обновления продукта используйте тот же процесс, просто передайте новый набор данных и CID.
- **Ошибки**: если возникла ошибка по одному продукту, остальные продолжают обрабатываться (batch-режим).
- **Валидация**: API проверяет формат, структуру и обязательные поля, а также корректность CID.
- **Аутентификация**: seller_address определяется автоматически по авторизации, не передавайте его явно.

---

## FAQ

**Q: Можно ли использовать один и тот же CID для нескольких продуктов?**
A: Да, если изображение или описание одинаковы, CID можно переиспользовать.

**Q: Как узнать, что пошло не так?**
A: В ответе по каждому продукту будет поле status: "error" и подробное описание ошибки.

**Q: Можно ли обновлять только часть данных продукта?**
A: Нет, всегда передавайте полную структуру продукта с актуальными CID и всеми обязательными полями.

---

## POST /products/upload

### Описание
Метод предназначен для загрузки (создания/обновления) продуктов из e-commerce систем. Все входящие данные должны быть приведены к структуре серверной модели продукта (Product).

### Структура запроса (JSON)

```json
{
  "products": [
    {
      "id": "string|int",                // Уникальный идентификатор продукта (например, из e-commerce)
      "title": "string",                 // Название продукта (обязательно)
      "description": {                    // Структурированное описание (см. ниже)
        "id": "string",
        "title": "string",
        "scientific_name": "string",
        "generic_description": "string",
        "effects": "string (optional)",
        "shamanic": "string (optional)",
        "warnings": "string (optional)",
        "dosage_instructions": [          // Массив инструкций по дозировке (опционально)
          {
            "type": "string",
            "title": "string",
            "description": "string"
          }
        ]
      },
      "description_cid": "string",      // CID расширенного описания (обязательно)
      "cover_image": "string",           // CID обложки (обязательно)
      "gallery": ["string", ...],        // Массив дополнительных изображений (CID, опционально)
      "categories": ["string", ...],     // Список категорий (опционально)
      "forms": ["string", ...],          // Список форм продукта (опционально)
      "species": "string",               // Вид продукта (обязательно)
      "prices": [                         // Массив цен (обязательно хотя бы одна)
        {
          "price": "string|number",     // Цена (обязательно)
          "currency": "string",         // Валюта (обязательно, например, USD, EUR)
          "weight": "string|number (optional)",
          "weight_unit": "string (optional)",
          "volume": "string|number (optional)",
          "volume_unit": "string (optional)",
          "form": "string (optional)"
        }
      ],
      "attributes": {                     // Любые дополнительные поля (sku, stock, tags и др.)
        "sku": "string (optional)",
        "stock": "int (optional)",
        "tags": ["string", ...],
        // ... любые другие поля
      }
    }
    // ... другие продукты
  ]
}
```

### Пояснения
- Все поля, отмеченные как "обязательно", должны присутствовать для успешной загрузки продукта.
- "attributes" (или "meta") — гибкий словарь для любых дополнительных данных, не входящих в основную структуру Product. Сохраняется без изменений.
- "gallery" — массив CID дополнительных изображений (опционально).
- "description" — вложенный объект, структура соответствует серверной модели Description.
- "prices" — массив, каждая цена может содержать валюту, вес/объем, форму и др.
- seller_address не передаётся, определяется по авторизации.

### Пример минимального продукта
```json
{
  "id": "123",
  "title": "Amanita Powder",
  "description": {
    "id": "desc-123",
    "title": "Amanita Powder",
    "scientific_name": "Amanita muscaria",
    "generic_description": "Высушенный порошок мухомора."
  },
  "description_cid": "Qm...",
  "cover_image": "Qm...",
  "species": "Amanita muscaria",
  "prices": [
    { "price": "19.99", "currency": "USD" }
  ]
}
```

### Пример с дополнительными полями
```json
{
  "id": "456",
  "title": "Blue Lotus Tincture",
  "description": {
    "id": "desc-456",
    "title": "Blue Lotus Tincture",
    "scientific_name": "Nymphaea caerulea",
    "generic_description": "Настойка голубого лотоса."
  },
  "description_cid": "Qm...",
  "cover_image": "Qm...",
  "gallery": ["Qm1...", "Qm2..."],
  "categories": ["flowers", "tincture"],
  "forms": ["tincture"],
  "species": "Nymphaea caerulea",
  "prices": [
    { "price": "29.99", "currency": "USD", "volume": "50", "volume_unit": "ml" }
  ],
  "attributes": {
    "sku": "BLT-001",
    "stock": 15,
    "tags": ["relax", "herbal"]
  }
}
```

### Валидация
- Обязательные поля: id, title, description, description_cid, cover_image, species, prices (с хотя бы одной ценой).
- Все дополнительные поля, не входящие в основную структуру, помещаются в attributes/meta.
- Входящий JSON должен быть приведён к этой структуре до передачи в API.
