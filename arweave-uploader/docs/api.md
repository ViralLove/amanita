# API Arweave Uploader (внешняя документация)

Документация для сервера ноды (или другого клиента), вызывающего сервис загрузки в Arweave.

**Спецификация OpenAPI 3.0:** [api.openapi.yaml](./api.openapi.yaml) — можно импортировать в Swagger UI, Postman, использовать для кодогенерации.

---

## Базовый URL

- **Production:** `https://amanita-uploader-888.up.railway.app`
- **Локально:** `http://localhost:3000` (порт из `PORT`, по умолчанию 3000)

---

## Эндпоинты

### GET /health

Проверка доступности сервиса. Авторизация не требуется.

**Ответ 200:**
```json
{
  "ok": true,
  "service": "arweave-uploader",
  "version": "0.2.0"
}
```

---

### POST /v1/crystalize

Публикация подписанного Data Item (ANS-104) в Arweave. Тело — JSON.

**Заголовки:** `Content-Type: application/json`  
**Опционально (если на деплое задан RELAY_AUTH_TOKEN):** `Authorization: Bearer <token>`

**Тело запроса:**

| Поле | Тип | Обязательно | Описание |
|------|-----|--------------|----------|
| `upload_id` | string | да | Уникальный идентификатор загрузки. Должен совпадать с `upload_id` в JWT и в теге Data Item. |
| `upload_token` | string | да | JWT RS256. Claims: `upload_id`, `max_bytes`, `exp`. Подписан приватным ключом; публичный ключ пары настроен на uploader. |
| `signed_data_item` | string | да | ANS-104 Data Item в base64url (уже подписан клиентом). Обязателен тег `Upload-Id` = `upload_id`. |
| `payload_size` | number | да | Размер payload в байтах, ≥ 0. Должен быть ≤ `max_bytes` из JWT. |

**Успех 200:**
```json
{
  "ack": true,
  "status": "queued_for_publish",
  "bundle_tx_id": "<43 символа base64url>",
  "arweave_url": "https://arweave.net/<bundle_tx_id>"
}
```

- `bundle_tx_id` — идентификатор bundle-транзакции в Arweave (43 символа, алфавит A–Z, a–z, 0–9, `-`, `_`).
- `arweave_url` — URL для доступа к данным; формируется как `{protocol}://{host}/{bundle_tx_id}` (обычно `https://arweave.net/...`).

**Ошибки:**

| Код | code | Когда |
|-----|------|--------|
| 400 | `invalid_body` | Тело не JSON или не объект. |
| 400 | `missing_field` | Нет или неверный тип одного из полей (`upload_id`, `upload_token`, `signed_data_item`, `payload_size`). |
| 400 | `signature_invalid` | Подпись Data Item или тег Upload-Id не прошли проверку. |
| 401 | `token_invalid` | JWT отсутствует, истёк, неверная подпись, несовпадение `upload_id` или `payload_size` > `max_bytes`. |
| 502 | `publish_failed` | Ошибка при отправке в Arweave (сеть, gateway). |

Тело ошибки всегда в формате:
```json
{
  "code": "<код>",
  "message": "<текст>"
}
```

---

## Режим мока (USE_REAL_ARWEAVE=false)

Если на сервере задано `USE_REAL_ARWEAVE=false`, запрос в Arweave не выполняется. Ответ 200 и формат полей те же; `bundle_tx_id` генерируется случайно (43 символа base64url). Используется для интеграций без реальной сети. Проверка наличия tx по `arweave_url` в этом режиме вернёт 404.

---

## См. также

- [api.openapi.yaml](./api.openapi.yaml) — полная спецификация OpenAPI 3.0.
- [architecture.md](./architecture.md) — внутренняя архитектура и конфиг сервиса.
- [local-run-and-smoke.md](./local-run-and-smoke.md) — локальный запуск и smoke-тест.
