# ArWeave Upload Edge Function

Supabase Edge Function для загрузки файлов и текстовых данных в ArWeave.

## 🚀 Функциональность

- **Upload Text** - загрузка текстовых данных
- **Upload File** - загрузка файлов
- **Publish** - приём подписанного Data Item + JWT, валидация, публикация в Arweave (bundle), callback в Backend
- **Health Check** - проверка состояния функции

## 📋 Endpoints

### Health Check
```bash
GET /health
```

### Upload Text
```bash
POST /upload-text
Content-Type: application/json

{
  "data": "Hello, ArWeave!",
  "contentType": "text/plain"
}
```

### Upload File
```bash
POST /upload-file
Content-Type: multipart/form-data

file: [binary file data]
```

### Publish (signed Data Item → Arweave bundle)
```bash
POST /edge/v1/publish
Content-Type: application/json

{
  "upload_token": "<JWT RS256 от Backend>",
  "upload_id": "<UUID>",
  "signed_data_item": "<base64 Data Item ANS-104>",
  "payload_size": 1234
}
```
Ответ 200: `{ "ack": true, "status": "queued_for_publish" }`. Публикация и callback выполняются асинхронно.

## 🔧 Настройка

### Переменные окружения / Secrets

| Переменная | Описание |
|------------|----------|
| `ARWEAVE_PRIVATE_KEY_FILE` | Путь к JSON-файлу с JWK приватного ключа Arweave (upload-text, upload-file, publish) |
| `UPLOAD_TOKEN_JWT_PUBLIC_KEY` | Публичный ключ Backend для верификации JWT (PEM или JWK JSON); для POST /edge/v1/publish |
| `BACKEND_URL` | URL Backend API; для вызовов PUT status и POST callback |
| `EDGE_TO_BACKEND_SECRET` | Секрет для заголовка `Authorization: Bearer …` при вызовах Backend |

Для локальной разработки и деплоя задавайте через Supabase Secrets или env.

### Локальный запуск
```bash
supabase functions serve arweave-upload
```

### Деплой
```bash
supabase functions deploy arweave-upload
```

## 📊 Ответы

### Успешная загрузка
```json
{
  "success": true,
  "transaction_id": "abc123...",
  "url": "https://arweave.net/abc123..."
}
```

### Ошибка
```json
{
  "success": false,
  "error": "Error message"
}
```

## 🔗 Интеграция с Python

Этот edge function предназначен для интеграции с Python `ArWeaveUploader`:

```python
# Python код будет вызывать эти endpoints
response = await http_client.post("/upload-text", json={"data": "test"})
transaction_id = response.json()["transaction_id"]
``` 