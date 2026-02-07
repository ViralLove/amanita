# Руководство по запуску и деплою Edge Function arweave-upload

**Назначение:** пошаговые инструкции по локальному запуску Supabase, настройке переменных окружения, деплою функции `arweave-upload` и публикации в облачный Supabase.

**Связанные документы:** [arweave-upload-architecture.md](./arweave-upload-architecture.md), [arweave-upload-security.md](./arweave-upload-security.md), [arweave-upload-publish-api.md](./arweave-upload-publish-api.md).

---

## 1. Предварительные требования

- **Supabase CLI** установлен (`brew install supabase/tap/supabase` или [официальная установка](https://supabase.com/docs/guides/cli)).
- **Deno** (для локальной проверки/тестов Edge Function): `brew install deno`.
- Учётная запись Supabase для облачного деплоя.

Проверка:
```bash
supabase --version
deno --version
```

---

## 2. Локальный запуск Supabase

### 2.1 Старт локального стека

Из корня репозитория:

```bash
# Остановить контейнеры (если были запущены ранее)
supabase stop

# Запустить локальный Supabase
supabase start

# Проверить статус и получить URL/ключи
supabase status
```

Ожидаемый вывод содержит:
- **API URL:** `http://127.0.0.1:54321`
- **anon key:** JWT для вызова Edge Functions
- **Studio URL:** `http://127.0.0.1:54323` (управление БД и т.д.)

### 2.2 Остановка

```bash
supabase stop
```

---

## 3. Переменные окружения и секреты

Edge Function `arweave-upload` использует переменные, перечисленные ниже. Локально они задаются через файл `.env`; в облаке — через Supabase Secrets.

### 3.1 Список переменных

| Переменная | Назначение | Обязательна для publish |
|------------|------------|--------------------------|
| `ARWEAVE_PRIVATE_KEY_FILE` | Путь к JSON-файлу с JWK приватного ключа Arweave (оператор) | да (upload-text, upload-file, publish) |
| `UPLOAD_TOKEN_JWT_PUBLIC_KEY` | Публичный ключ Backend для верификации JWT (PEM или JWK JSON) | да (POST /edge/v1/publish) |
| `BACKEND_URL` | Базовый URL Backend API (без завершающего слеша) | да (PUT status, POST callback) |
| `EDGE_TO_BACKEND_SECRET` | Секрет для заголовка `Authorization: Bearer …` при вызовах Backend | да |

Подробнее про ключи и безопасность: [arweave-upload-security.md](./arweave-upload-security.md).

### 3.2 Локальная разработка (.env)

1. В корне проекта создайте или отредактируйте `.env` (файл не коммитить в git).

2. Добавьте переменные. Пример для **локального** запуска функции:

```bash
# Supabase (значения после supabase start можно взять из supabase status)
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0

# Arweave: путь к файлу с JWK оператора (относительно рабочей директории при serve)
ARWEAVE_PRIVATE_KEY_FILE=./supabase/functions/arweave-upload/arweave-wallet.json

# Publish: JWT RS256 и Backend (подставьте свои значения)
UPLOAD_TOKEN_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"
BACKEND_URL=http://localhost:8000
EDGE_TO_BACKEND_SECRET=your-shared-secret-with-backend
```

Для `UPLOAD_TOKEN_JWT_PUBLIC_KEY` можно использовать либо PEM (как выше), либо одну строку JSON JWK (см. [arweave-upload-security.md](./arweave-upload-security.md)).

3. Файл с JWK оператора (`arweave-wallet.json`) должен существовать по указанному пути при вызове `supabase functions serve` (обычно рабочая директория — корень проекта, поэтому путь задаётся от него).

### 3.3 Облако: Supabase Secrets

В облаке переменные задаются как **Secrets** проекта. Так они не попадают в код и доступны только Edge Functions.

1. Линкуйте проект с облачным (см. раздел 4).
2. Установите секреты через CLI:

```bash
# Публичный ключ Backend (PEM — можно в одну строку с \n)
supabase secrets set UPLOAD_TOKEN_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjAN...
-----END PUBLIC KEY-----"

# URL Backend API
supabase secrets set BACKEND_URL="https://api.your-backend.com"

# Секрет для Edge → Backend
supabase secrets set EDGE_TO_BACKEND_SECRET="your-production-secret"
```

Для **приватного ключа Arweave** в облаке: в коде может использоваться `ARWEAVE_PRIVATE_KEY_FILE` (путь к файлу) или `ARWEAVE_PRIVATE_KEY` (JSON-строка JWK). В Supabase Cloud файлов нет — задавайте секрет `ARWEAVE_PRIVATE_KEY` с телом JWK в одну строку: `supabase secrets set ARWEAVE_PRIVATE_KEY='{"kty":"RSA",...}'`. Если функция ожидает только `ARWEAVE_PRIVATE_KEY_FILE`, нужно добавить в коде поддержку чтения ключа из `ARWEAVE_PRIVATE_KEY` (см. README и `utils.ts` в функции).

Проверка заданных секретов (имена, без значений):

```bash
supabase secrets list
```

### 3.4 Уточнения: BACKEND_URL и UPLOAD_TOKEN_JWT_PUBLIC_KEY

**BACKEND_URL — это корень сервера, без пути и без версии.**

В коде Edge к `BACKEND_URL` дописывается путь:  
`PUT ${BACKEND_URL}/v1/uploads/${uploadId}/status` и `POST ${BACKEND_URL}/v1/uploads/callback`.  
То есть в переменную задаётся только **схема + хост + порт**:

- Локально (bot слушает на 8000): `BACKEND_URL=http://localhost:8000` или `http://127.0.0.1:8000`
- Не нужно: `http://localhost:8000/v1` — путь `/v1/uploads/...` добавляется в коде

**UPLOAD_TOKEN_JWT_PUBLIC_KEY — публичный ключ RSA (PEM или JWK) для проверки JWT.**

Edge **только проверяет** подпись токена этим ключом. Токен должен быть **подписан** соответствующим **приватным** ключом (обычно на Backend при выдаче токена). Сейчас в bot есть только моки PUT status и POST callback; эндпоинта «prepare», который выдаёт такой JWT, ещё нет. Чтобы тестировать POST /edge/v1/publish:

1. **Сгенерировать RSA-пару** (например, 2048 bit) и сохранить приватный ключ в безопасном месте.
2. **Публичный ключ** прописать в Edge: в `supabase/.env` (или в корневом `.env` при `supabase functions serve --env-file .env`) как `UPLOAD_TOKEN_JWT_PUBLIC_KEY` — в формате PEM или одной строкой JWK (см. [arweave-upload-security.md](./arweave-upload-security.md)).
3. **Тестовый JWT** подписывать **приватным** ключом: payload должен содержать `exp` (unix timestamp), `upload_id` (UUID), `max_bytes` (число). Алгоритм подписи — RS256. Такой токен можно собрать скриптом (Python/Node) или позже получать с Backend, когда появится prepare.

Пример генерации ключа (OpenSSL, публичный ключ в PEM для вставки в .env):

```bash
openssl genrsa -out private_upload_jwt.pem 2048
openssl rsa -in private_upload_jwt.pem -pubout -out public_upload_jwt.pem
# Содержимое public_upload_jwt.pem (включая -----BEGIN/END-----) — в UPLOAD_TOKEN_JWT_PUBLIC_KEY
```

Приватный ключ не класть в Edge; использовать только для подписи токенов (локально в скрипте или на Backend после реализации prepare).

### 3.5 Режим мока Backend

Когда Backend недоступен или нужны тесты без реальных вызовов PUT status / POST callback, можно включить **режим мока**:

1. **Включение мока** — в env (локально в `.env`, в облаке — Secrets):
   - `BACKEND_USE_MOCK=true` — вызовы к Backend не выполняются; симулируется ответ.
   - `BACKEND_MOCK_PUT_STATUS` и `BACKEND_MOCK_CALLBACK` — коды ответа 200, 404 или 409 (по умолчанию 200).

2. **Переключение на лету** — чтобы в одном деплое проверять разные сценарии (успех / 404 / 409) без смены env, можно задавать симулированный код **заголовками запроса**. Функция учитывает эти заголовки только если «переопределение» разрешено одним из двух способов:

   **Вариант А: разрешить всем запросам**  
   Задайте в Secrets: `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true`. Тогда любой вызов может передать заголовки `X-Backend-Mock-Put-Status` и/или `X-Backend-Mock-Callback` (значения 200, 404, 409), и они будут применены к этому запросу. Секрет не нужен.

   **Вариант Б: разрешить только тем, кто знает секрет**  
   Задайте в Secrets строку, которую знаете только вы (или ваш тестовый скрипт), например:  
   `BACKEND_MOCK_TEST_SECRET=my-staging-secret-xyz`  
   Эту строку **не генерирует** система — вы её **придумываете** и один раз прописываете в Supabase Secrets (или в `.env` при локальном serve). В каждом запросе, где хотите переопределить мок, добавляйте заголовок:  
   `X-Backend-Mock-Secret: my-staging-secret-xyz`  
   (то же значение, что и в `BACKEND_MOCK_TEST_SECRET`). Если значение совпало — заголовки `X-Backend-Mock-Put-Status` и `X-Backend-Mock-Callback` для этого запроса учитываются. Если секрет не передан или не совпал — переопределение по заголовкам игнорируется.

   Итого по секрету: вы **создаёте** его сами (любая строка), **храните** в env/Secrets как `BACKEND_MOCK_TEST_SECRET`, **отправляете** ту же строку в заголовке `X-Backend-Mock-Secret` при вызове функции (curl, Postman, скрипт).

Пример curl к задеплоенной функции (переопределение через секрет):

```bash
# В Supabase Secrets задано: BACKEND_MOCK_TEST_SECRET=my-test-secret
# В запросе передаём тот же секрет и нужный код мока:
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/arweave-upload" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Backend-Mock-Secret: my-test-secret" \
  -H "X-Backend-Mock-Put-Status: 409" \
  -d '{"upload_token":"…","upload_id":"…","signed_data_item":"…","payload_size":0}'
```

Если включён `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true`, заголовок `X-Backend-Mock-Secret` не обязателен — достаточно `X-Backend-Mock-Put-Status` и/или `X-Backend-Mock-Callback`.

Подробнее: [arweave-upload-publish-api.md](./arweave-upload-publish-api.md) (раздел 5 и 5.1).

---

## 4. Локальный запуск Edge Function

Запуск функции в режиме разработки (без деплоя в облако):

```bash
# Из корня проекта; .env — в корне
supabase functions serve arweave-upload --env-file .env
```

Функция будет доступна по адресу вида:
`http://127.0.0.1:54321/functions/v1/arweave-upload`

Проверка здоровья:
```bash
curl -H "Authorization: Bearer YOUR_ANON_KEY" \
  http://127.0.0.1:54321/functions/v1/arweave-upload/health
```

Тест publish — по контракту из [arweave-upload-publish-api.md](./arweave-upload-publish-api.md) (нужен валидный JWT от Backend и подписанный Data Item).

---

## 5. Деплой в облачный Supabase

### 5.1 Логин и линковка проекта

```bash
# Войти в аккаунт Supabase (откроется браузер)
supabase login

# Перейти в каталог с проектом
cd /path/to/Amanita

# Связать локальный проект с облачным (project-ref из Dashboard → Settings → General)
supabase link --project-ref YOUR_PROJECT_REF
```

`YOUR_PROJECT_REF` — идентификатор проекта из URL Dashboard: `https://supabase.com/dashboard/project/YOUR_PROJECT_REF`.

### 5.2 Настройка секретов в облаке

Перед деплоем задайте секреты (раздел 3.3):

```bash
supabase secrets set UPLOAD_TOKEN_JWT_PUBLIC_KEY="..."
supabase secrets set BACKEND_URL="https://..."
supabase secrets set EDGE_TO_BACKEND_SECRET="..."
# и при необходимости ARWEAVE_PRIVATE_KEY / ARWEAVE_PRIVATE_KEY_FILE — по тому, как реализовано в коде
```

### 5.3 Деплой функции

```bash
supabase functions deploy arweave-upload
```

Проверка:
```bash
supabase functions list
supabase functions status arweave-upload
```

URL функции в облаке:
`https://YOUR_PROJECT_REF.supabase.co/functions/v1/arweave-upload`

### 5.4 Логи в облаке

```bash
supabase functions logs arweave-upload --follow
supabase functions logs arweave-upload --since 1h
```

---

## 6. Краткий чеклист

**Локально:**
- [ ] `supabase start`, `supabase status` — стек запущен
- [ ] `.env` создан и заполнен (в т.ч. `ARWEAVE_PRIVATE_KEY_FILE`, `UPLOAD_TOKEN_JWT_PUBLIC_KEY`, `BACKEND_URL`, `EDGE_TO_BACKEND_SECRET`)
- [ ] `supabase functions serve arweave-upload --env-file .env` — функция отвечает на `/health`

**Облако:**
- [ ] `supabase login`, `supabase link --project-ref ...`
- [ ] `supabase secrets set ...` для всех требуемых переменных
- [ ] `supabase functions deploy arweave-upload`
- [ ] Проверка вызова `/health` и при необходимости `/edge/v1/publish` по облачному URL

---

**Версия:** 1.0  
**Дата:** 2026-01-29
