# Commerce: медиа, описание, загрузка продуктов

**SSOT по путям и auth:** [`api.md`](./api.md) §2.2–2.4, §3.1 (HMAC на `/media`, `/description`, `/products`).

## Идея

1. Загрузить файлы и описание → получить **CID** (IPFS/Arweave через существующие сервисы бота).
2. Собрать продукт с CID и вызвать **`POST /products/upload`**.
3. Все write-запросы к этим префиксам подписываются **HMAC** (заголовки см. `api.md` §3.1).

## Чек-лист

1. `POST /media/upload` (multipart) → CID каждого файла.
2. `POST /description/upload` (JSON) → CID описания.
3. Собрать тело `products[]` (см. ниже).
4. `POST /products/upload` → разбор `results[]` по каждому товару.

## Пример потока (HTTP)

### 1. Изображение

```http
POST /media/upload
Content-Type: multipart/form-data
```

Ответ (пример): `cid`, `filename`, признак успеха — уточняйте по OpenAPI `/docs`.

### 2. Описание

```json
POST /description/upload
{
  "id": "desc-123",
  "title": "Amanita Powder",
  "scientific_name": "Amanita muscaria",
  "generic_description": "…",
  "dosage_instructions": [
    { "type": "powder", "title": "Старт", "description": "1 г в день" }
  ]
}
```

### 3. Продукт(ы)

```json
POST /products/upload
{
  "products": [
    {
      "id": "123",
      "title": "Amanita Powder",
      "description": { "id": "desc-123", "title": "…", "scientific_name": "…", "generic_description": "…" },
      "description_cid": "<CID из шага 2>",
      "cover_image": "<CID обложки>",
      "gallery": ["<CID>", "…"],
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

Ответ: массив `results` с `id`, `blockchain_id`, `tx_hash`, `status` per product (точные поля — в OpenAPI и коде конвертера).

## Поля продукта (контракт для интегратора)

| Поле | Назначение |
|------|------------|
| `id` | Внешний идентификатор (строка/число) |
| `title` | Название |
| `description` | Вложенный объект описания (как в `/description/upload`) |
| `description_cid` | CID полного описания (**обязателен**) |
| `cover_image` | CID обложки (**обязателен**) |
| `gallery` | Доп. изображения (CID), опционально |
| `categories`, `forms` | Опционально |
| `species` | Обязателен |
| `prices` | Минимум одна цена: `price`, `currency`; опционально вес/объём/форма |
| `attributes` | Произвольные поля (sku, stock, tags) |

**Продавец:** `seller_address` в теле не передаётся — определяется из контекста HMAC / API-ключа (см. код роутов).

## Ошибки и практики

- Batch: ошибка по одному элементу не обязательно отменяет остальные — смотрите `status` per item в ответе.
- Используйте CID только из ответов upload-эндпоинтов.
- Полные коды ошибок и схемы — **`/openapi.json`**, не дублировать здесь.

## FAQ

**Повторное использование CID?** Да, если файл/описание общие.

**Частичное обновление?** Контракт ориентирован на полную структуру продукта; уточняйте в OpenAPI для `PUT /products/{id}`.
