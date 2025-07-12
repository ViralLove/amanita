# Реализация логирования для AMANITA API

## Выполненные задачи

### 1. Настройка структурированного логирования

**Файлы:**
- `bot/api/main.py` - основная логика логирования
- `bot/api/config.py` - конфигурация через переменные окружения
- `bot/api/README.md` - документация по использованию

**Возможности:**
- ✅ Двойной вывод: консоль (человекочитаемый) + файл (JSON)
- ✅ Автоматическая ротация логов (10MB, 5 файлов)
- ✅ Структурированный JSON формат для production
- ✅ Настраиваемые уровни логирования
- ✅ Extra поля для контекста (endpoint, error, etc.)

### 2. Конфигурация через переменные окружения

```bash
# Основные настройки
AMANITA_API_LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
AMANITA_API_LOG_FILE=logs/amanita_api.log     # Путь к файлу логов
AMANITA_API_LOG_MAX_SIZE=10485760            # 10MB максимальный размер
AMANITA_API_LOG_BACKUP_COUNT=5               # Количество файлов ротации

# Дополнительные настройки API
AMANITA_API_HOST=0.0.0.0                     # Хост для API сервера
AMANITA_API_PORT=8000                        # Порт для API сервера
AMANITA_API_CORS_ORIGINS=*                   # CORS настройки
```

### 3. Интеграция с существующей архитектурой

**В main.py:**
- ✅ Передача параметров логирования в API
- ✅ Использование единого ServiceFactory
- ✅ Параллельный запуск бота и API

**Структура логов:**
```json
{
  "timestamp": "2025-07-12T14:48:05.858961",
  "level": "INFO",
  "logger": "amanita_api",
  "message": "Тест логирования API",
  "module": "main",
  "function": "create_api_app",
  "line": 45,
  "endpoint": "/test",
  "test": true
}
```

### 4. Production-ready возможности

**Мониторинг:**
- ✅ Легкое чтение логов: `tail -f logs/amanita_api.log`
- ✅ Поиск ошибок: `grep '"level":"ERROR"' logs/amanita_api.log`
- ✅ Анализ с jq: `cat logs/amanita_api.log | jq '.level' | sort | uniq -c`

**Интеграция:**
- ✅ ELK Stack (Elasticsearch, Logstash, Kibana)
- ✅ Prometheus + Grafana
- ✅ Datadog, New Relic

**Безопасность:**
- ✅ Нет чувствительной информации в логах
- ✅ Автоматическая ротация предотвращает переполнение
- ✅ JSON формат позволяет фильтрацию

### 5. Тестирование

**Проверено:**
- ✅ Создание файлов логов
- ✅ JSON структурированный формат
- ✅ Extra поля в логах
- ✅ Ротация файлов
- ✅ Конфигурация через переменные окружения

## Следующие шаги

1. **HMAC middleware** - система аутентификации
2. **API ключи** - управление доступом
3. **Rate limiting** - защита от DDoS
4. **Pydantic модели** - валидация данных

## Использование

### Запуск с логированием

```bash
# Обычный запуск (INFO уровень)
python -m bot.main

# DEBUG логирование
export AMANITA_API_LOG_LEVEL=DEBUG
python -m bot.main

# Кастомный файл логов
export AMANITA_API_LOG_FILE=logs/custom_api.log
python -m bot.main
```

### Просмотр логов

```bash
# Текущие логи
tail -f logs/amanita_api.log

# Ошибки
grep '"level":"ERROR"' logs/amanita_api.log

# Конкретный эндпоинт
grep '"endpoint":"/health"' logs/amanita_api.log

# Статистика уровней
cat logs/amanita_api.log | jq -r '.level' | sort | uniq -c
``` 