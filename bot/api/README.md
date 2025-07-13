# AMANITA API - Документация

## Обзор

AMANITA API - это REST API для интеграции e-commerce платформ с блокчейн экосистемой AMANITA. API предоставляет интерфейс для работы с товарами, инвайтами, заказами и блокчейн операциями.

## 🚀 Быстрый старт

### Запуск API сервера

```bash
# Из корневой директории проекта
cd bot
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Документация API
open http://localhost:8000/docs
```

## 📋 Доступные эндпоинты

### Публичные эндпоинты
- `GET /` - Корневой эндпоинт
- `GET /health` - Проверка состояния сервиса
- `GET /health/detailed` - Детальная диагностика
- `GET /docs` - Swagger документация
- `GET /redoc` - ReDoc документация

### Аутентифицированные эндпоинты
- `POST /auth-test` - Тест HMAC аутентификации
- `POST /api-keys/` - Создание API ключа
- `GET /api-keys/{client_address}` - Получение ключей клиента
- `DELETE /api-keys/{api_key}` - Отзыв API ключа
- `GET /api-keys/validate/{api_key}` - Валидация ключа

## 🔐 Аутентификация

API использует HMAC аутентификацию для защиты эндпоинтов.

### Переменные окружения для аутентификации

```bash
# API ключи (уже настроены в .env)
AMANITA_API_KEY=ak_22bc74537e53698e
AMANITA_API_SECRET=sk_9160864a1ba617780cce32258248c21d085d8ddb18d3250ff4532925102d1b68

# HMAC настройки
AMANITA_API_HMAC_SECRET_KEY=default-secret-key-change-in-production
AMANITA_API_HMAC_TIMESTAMP_WINDOW=300
AMANITA_API_HMAC_NONCE_CACHE_TTL=600
```

### Форматы API ключей

API поддерживает следующие форматы ключей:
- `ak_` + 16 символов (формат Amanita)
- `sk_` + 64 hex символа (секретный ключ)
- 64 hex символа (традиционный формат)

## 🧪 Тестирование

### Запуск всех тестов API

```bash
# Из директории bot
python3 -m pytest tests/api/ -v
```

### Результаты тестирования

✅ **Все тесты проходят успешно (63/63)**
- HMAC аутентификация работает
- Валидация данных функционирует
- Обработка ошибок корректна
- Health check эндпоинты доступны

### Структура тестов

```
tests/api/
├── test_api_auth.py      # Тесты аутентификации
├── test_data.py          # Тестовые данные
├── test_error_handlers.py # Тесты обработки ошибок
├── test_models.py        # Тесты моделей данных
└── conftest.py           # Конфигурация pytest
```

## 📝 Логирование

### Конфигурация

```bash
# Уровень логирования (DEBUG, INFO, WARNING, ERROR)
AMANITA_API_LOG_LEVEL=DEBUG

# Путь к файлу логов
AMANITA_API_LOG_FILE=logs/amanita_api.log

# Максимальный размер файла логов (в байтах)
AMANITA_API_LOG_MAX_SIZE=10485760  # 10MB

# Количество файлов ротации
AMANITA_API_LOG_BACKUP_COUNT=5
```

### Структура логов

#### Консольный вывод (человекочитаемый)
```
2024-01-15 10:30:45 - amanita_api - INFO - Инициализация AMANITA API приложения
2024-01-15 10:30:45 - amanita_api - INFO - Запрос к корневому эндпоинту
```

#### Файловый вывод (JSON структурированный)
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "amanita_api",
  "message": "Инициализация AMANITA API приложения",
  "module": "main",
  "function": "create_api_app",
  "line": 45,
  "log_level": "INFO",
  "log_file": "logs/amanita_api.log",
  "service_factory_available": true
}
```

## ⚙️ Конфигурация

### Основные настройки

```bash
# Окружение
AMANITA_API_ENVIRONMENT=development

# Сервер
AMANITA_API_HOST=0.0.0.0
AMANITA_API_PORT=8000

# CORS
AMANITA_API_CORS_ORIGINS=*
AMANITA_API_CORS_ALLOW_CREDENTIALS=true

# Безопасность
AMANITA_API_TRUSTED_HOSTS=*
```

### Документация

```bash
# URL документации
AMANITA_API_DOCS_URL=/docs
AMANITA_API_REDOC_URL=/redoc
AMANITA_API_OPENAPI_URL=/openapi.json
```

## 🔗 Интеграция с блокчейном

API интегрирован с локальной Hardhat нодой и смарт-контрактами:

- **AmanitaRegistry**: `0x5FbDB2315678afecb367f032d93F642f64180aa3`
- **InviteNFT**: `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`
- **ProductRegistry**: `0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9`

## 📊 Мониторинг

### Чтение логов

```bash
# Просмотр текущих логов
tail -f logs/amanita_api.log

# Поиск ошибок
grep '"level":"ERROR"' logs/amanita_api.log

# Поиск по конкретному эндпоинту
grep '"endpoint":"/health"' logs/amanita_api.log

# Анализ JSON логов с jq
cat logs/amanita_api.log | jq '.level' | sort | uniq -c
```

### Health Check

```bash
# Базовый health check
curl http://localhost:8000/health

# Детальная диагностика
curl http://localhost:8000/health/detailed
```

## 🚀 Следующие шаги

### Приоритет 1: Расширение функциональности
- [ ] Эндпоинты для работы с блокчейном
- [ ] Интеграция ProductRegistry и InviteNFT сервисов
- [ ] API для управления инвайтами

### Приоритет 2: Интеграционные тесты
- [ ] Тесты с реальными смарт-контрактами
- [ ] End-to-end тесты
- [ ] Тесты производительности

### Приоритет 3: WordPress интеграция
- [ ] API для WooCommerce плагина
- [ ] Синхронизация заказов
- [ ] Управление товарами через API

## 🔧 Отладка

### Включение DEBUG логирования

```bash
export AMANITA_API_LOG_LEVEL=DEBUG
python -m uvicorn api.main:app --reload
```

### Просмотр структуры логов

```bash
# Показать все поля JSON лога
cat logs/amanita_api.log | jq 'keys' | head -1

# Показать уникальные уровни логирования
cat logs/amanita_api.log | jq -r '.level' | sort | uniq

# Показать статистику по модулям
cat logs/amanita_api.log | jq -r '.module' | sort | uniq -c
```

## 🛡️ Безопасность

- HMAC аутентификация для всех защищенных эндпоинтов
- Валидация временных меток (timestamp window)
- Защита от replay атак (nonce cache)
- CORS настройки для веб-клиентов
- Trusted Host middleware
- Логи не содержат чувствительной информации
- Ротация логов предотвращает переполнение диска

## ⚡ Производительность

- Асинхронная обработка запросов (FastAPI)
- Асинхронная запись в файлы логов
- Буферизация для оптимизации I/O
- Ротация логов не блокирует основное приложение
- Минимальное влияние на производительность API 