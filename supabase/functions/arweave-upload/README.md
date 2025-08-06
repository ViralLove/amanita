# ArWeave Upload Edge Function

Supabase Edge Function для загрузки файлов и текстовых данных в ArWeave.

## 🚀 Функциональность

- **Upload Text** - загрузка текстовых данных
- **Upload File** - загрузка файлов
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

## 🔧 Настройка

### Переменные окружения
```bash
ARWEAVE_PRIVATE_KEY=your-private-key-here
```

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