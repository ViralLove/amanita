# AMANITA API - Логирование

## Обзор

API использует структурированное логирование с поддержкой файловой ротации и JSON формата для production окружения.

## Конфигурация

### Переменные окружения

```bash
# Уровень логирования (DEBUG, INFO, WARNING, ERROR)
AMANITA_API_LOG_LEVEL=INFO

# Путь к файлу логов
AMANITA_API_LOG_FILE=logs/amanita_api.log

# Максимальный размер файла логов (в байтах)
AMANITA_API_LOG_MAX_SIZE=10485760  # 10MB

# Количество файлов ротации
AMANITA_API_LOG_BACKUP_COUNT=5
```

### Настройки по умолчанию

- **Уровень логирования**: INFO
- **Файл логов**: `logs/amanita_api.log`
- **Максимальный размер**: 10MB
- **Количество файлов**: 5 (основной + 4 ротации)

## Структура логов

### Консольный вывод (человекочитаемый)
```
2024-01-15 10:30:45 - amanita_api - INFO - Инициализация AMANITA API приложения
2024-01-15 10:30:45 - amanita_api - INFO - Запрос к корневому эндпоинту
```

### Файловый вывод (JSON структурированный)
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

## Ротация логов

Логи автоматически ротируются при достижении максимального размера файла:

- `amanita_api.log` - текущий файл
- `amanita_api.log.1` - предыдущий файл
- `amanita_api.log.2` - пред-предыдущий файл
- и т.д.

Старые файлы автоматически удаляются при превышении лимита.

## Мониторинг в production

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

### Интеграция с системами мониторинга

Логи в JSON формате легко интегрируются с:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Prometheus + Grafana** (через log exporters)
- **Datadog**
- **New Relic**

### Пример конфигурации для ELK

```yaml
# logstash.conf
input {
  file {
    path => "/path/to/logs/amanita_api.log"
    codec => json
    start_position => "beginning"
  }
}

filter {
  date {
    match => [ "timestamp", "ISO8601" ]
    target => "@timestamp"
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "amanita-api-logs-%{+YYYY.MM.dd}"
  }
}
```

## Отладка

### Включение DEBUG логирования

```bash
export AMANITA_API_LOG_LEVEL=DEBUG
python -m bot.main
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

## Безопасность

- Логи не содержат чувствительной информации (пароли, токены)
- Файлы логов имеют ограниченные права доступа
- Ротация предотвращает переполнение диска
- JSON формат позволяет легко фильтровать чувствительные данные

## Производительность

- Асинхронная запись в файлы
- Буферизация для оптимизации I/O
- Ротация не блокирует основное приложение
- Минимальное влияние на производительность API 