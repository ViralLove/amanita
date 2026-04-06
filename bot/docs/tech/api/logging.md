# Логирование Bot API

## Где настраивается

- Инициализация при импорте **`bot/api/main.py`**: вызывается **`setup_logging`** из **`bot/utils/logging_setup.py`** для логгера **`amanita_api`**.
- Параметры по умолчанию и env — класс **`APIConfig`** (`bot/api/config.py`); сводная таблица — **[`api.md`](./api.md) §4**.

## Переменные окружения (логи)

| Переменная | Смысл |
|------------|--------|
| `AMANITA_API_LOG_LEVEL` | `DEBUG` / `INFO` / … |
| `AMANITA_API_LOG_FILE` | Путь к файлу (если задан — включается JSON в файл) |
| `AMANITA_API_LOG_MAX_SIZE` | Размер файла до ротации (байты, по умолчанию 10MB) |
| `AMANITA_API_LOG_BACKUP_COUNT` | Число файлов ротации |

Консоль: человекочитаемый формат. Файл: одна строка = один JSON-объект (поля `timestamp`, `level`, `logger`, `message`, `module`, `function`, `line`; плюс extra-поля из записи).

## Просмотр

```bash
tail -f logs/amanita_api.log
grep '"level":"ERROR"' logs/amanita_api.log
```

Не логировать секреты запросов (Bearer, HMAC, токены); при отладке использовать маскирование на стороне клиента.
