# Режим мока Backend в arweave-uploader

Когда микросервис вызывает Backend (PUT status, POST callback), в режиме разработки или тестов Backend может быть не развёрнут. Режим мока позволяет не выполнять реальные HTTP-запросы к Backend, а только логировать вызовы и при необходимости симулировать ответы 200 / 404 / 409.

**Связанный таск:** [task-implement-microservice-backend-mock-mode](analysis/tasks/task-implement-microservice-backend-mock-mode/task-implement-microservice-backend-mock-mode.md).

---

## 1. Включение режима мока

Переменная окружения **`BACKEND_USE_MOCK`**:

- `true` или `1` (без учёта регистра) — вызовы `putStatus` и `postCallback` **не выполняют** реальный `fetch` к Backend; вместо этого логируются параметры и при необходимости симулируется код ответа (200 / 404 / 409).
- Не задана или иное значение — поведение без изменений: при заданных `BACKEND_URL` и секрете выполняется реальный HTTP; при не заданных — предупреждение в лог и пропуск вызова.

Пример:

```bash
BACKEND_USE_MOCK=true node dist/server.js
```

Чтобы **не** мокировать backend и реально дергать bot: не задавайте `BACKEND_USE_MOCK` (или `false`), укажите **`BACKEND_URL`** и **`UPLOADER_TO_BACKEND_SECRET`** или **`EDGE_TO_BACKEND_SECRET`** — см. **[backend-integration.md](./backend-integration.md)**.

---

## 2. Переменные переключения симулированного ответа (env)

Действуют **только при `BACKEND_USE_MOCK=true`**.

| Переменная | Допустимые значения | По умолчанию | Назначение |
|------------|---------------------|--------------|------------|
| **BACKEND_MOCK_PUT_STATUS** | `200`, `404`, `409` | `200` | Симулированный код ответа для вызова PUT …/status. |
| **BACKEND_MOCK_CALLBACK** | `200`, `404`, `409` | `200` | Симулированный код ответа для вызова POST …/callback. |

При значении `200`: в лог пишутся параметры вызова, возврат без ошибки.  
При значении `404` или `409`: в лог дополнительно пишется факт симуляции этого кода (для сценариев «backend вернул 404/409»).

Пример:

```bash
BACKEND_USE_MOCK=true BACKEND_MOCK_PUT_STATUS=404 node dist/server.js
# После вызова publish в логах — симуляция 404 для putStatus.
```

---

## 3. Переключение на лету (заголовки запроса)

При вызове **уже задеплоенного** микросервиса тесты не могут менять env между запросами. Чтобы в разных сценариях проверять то «успех», то «putStatus 404», то «callback 409» без передеплоя, можно задавать симулированный ответ **только для данного запроса** через заголовки.

### 3.1 Условие учёта заголовков

Заголовки переопределения учитываются **только если**:

1. Включён мок: `BACKEND_USE_MOCK=true`, **и**
2. Выполнено одно из:
   - в env задано **`BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true`** (или `1`), **или**
   - в запросе передан заголовок **`X-Backend-Mock-Secret`**, совпадающий со значением **`BACKEND_MOCK_TEST_SECRET`** из env (для тестового/стейджинг окружения).

Иначе заголовки `X-Backend-Mock-Put-Status` и `X-Backend-Mock-Callback` **игнорируются** (без ошибки).

### 3.2 Заголовки переопределения

| Заголовок | Значения | Назначение |
|-----------|----------|------------|
| **X-Backend-Mock-Put-Status** | `200`, `404`, `409` | Симулированный код ответа для PUT status **только для этого запроса**. |
| **X-Backend-Mock-Callback** | `200`, `404`, `409` | Симулированный код ответа для POST callback **только для этого запроса**. |
| **X-Backend-Mock-Secret** | строка | Должен совпадать с `BACKEND_MOCK_TEST_SECRET`, чтобы разрешить учёт двух заголовков выше (если не задано `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE`). |

Нормализация: допустимы только 200, 404, 409; иное или пусто → 200.

### 3.3 Примеры вызова задеплоенного микросервиса

Сценарий «успех» (без заголовков или 200):

```bash
curl -X POST "https://YOUR_SERVICE/v1/crystalize" \
  -H "Content-Type: application/json" \
  -d '{"upload_id":"00000000-0000-0000-0000-000000000001"}'
```

Сценарий «putStatus 404»:

```bash
curl -X POST "https://YOUR_SERVICE/v1/crystalize" \
  -H "Content-Type: application/json" \
  -H "X-Backend-Mock-Put-Status: 404" \
  -d '{"upload_id":"00000000-0000-0000-0000-000000000001"}'
```

Сценарий «callback 409» (при заданном `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true` или валидном `X-Backend-Mock-Secret`):

```bash
curl -X POST "https://YOUR_SERVICE/v1/crystalize" \
  -H "Content-Type: application/json" \
  -H "X-Backend-Mock-Callback: 409" \
  -d '{"upload_id":"00000000-0000-0000-0000-000000000001"}'
```

---

## 4. Сводная таблица переменных окружения

| Переменная | Назначение |
|------------|------------|
| **BACKEND_USE_MOCK** | Включить режим мока (не выполнять реальный fetch к Backend). |
| **BACKEND_MOCK_PUT_STATUS** | Симулированный код для PUT status (200\|404\|409). |
| **BACKEND_MOCK_CALLBACK** | Симулированный код для POST callback (200\|404\|409). |
| **BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE** | Разрешить переопределение по заголовкам запроса (`true`/`1`). |
| **BACKEND_MOCK_TEST_SECRET** | Секрет для заголовка `X-Backend-Mock-Secret` (учёт override только при совпадении). |

---

## 5. Пример переменных окружения

В корне репозитория есть файл **`.env.example`** со всеми переменными (включая режим мока Backend). Скопируйте в `.env` и подставьте значения.

---

## 6. Связанные документы

- [Архитектура микросервиса](architecture.md) — контракт API, маршруты, конфиг.
- [Таск: режим мока Backend](analysis/tasks/task-implement-microservice-backend-mock-mode/task-implement-microservice-backend-mock-mode.md) — постановка и AC/DoD.
