# Интеграционные тесты Upload flow (таск 3.2)

**Постоянная документация:** `bot/docs/tests/data-upload-integration-tests.md`  
**Правило:** @integration-test-build.core.mdc  
**Файлы тестов:** `tests/integration/upload_harness.py`, `tests/integration/test_upload_flow_integration.py`  
**Маркер:** `@pytest.mark.integration`

---

## Что делают тесты (простыми словами)

Тесты проверяют, что **бэкенд и база работают вместе** без моков: реальный Supabase, реальный UploadService, реальные HTTP-запросы к API.

- **Phase 1 (Proof):** «БД жива» — вставили запись в таблицу `uploads`, прочитали; проверили, что UploadService видит эту запись. Нужно только чтобы Supabase был доступен.
- **Phase 2 (Contracts):** «API говорит то, что договорились» — PUT статуса возвращает 200 и `{ "ok": true }`; на неизвестный id — 404; POST callback из неподходящего статуса — 409. Формат ответов и коды ошибок соответствуют контракту с Edge.
- **Phase 3 (Flows):** «Весь путь от А до Б» — создали запись в статусе prepared → отправили PUT «queued» → отправили POST callback с `item_id` и `bundle_tx_id` → в БД запись в статусе `published` с заполненными полями. Плюс проверки: неизвестный id даёт 404; callback без предварительного PUT — 409. Один тест (опционально) идёт с самого начала через `prepare()` — для него нужен JWT-ключ.

Edge Function в этих тестах **не вызывается**: мы только имитируем её вызовы (те же URL, те же тела и Bearer), чтобы проверить бэкенд и БД.

---

## Запуск тестов

Из папки **bot**:

```bash
cd bot
# С реальным Supabase (локальный или test project):
export SUPABASE_URL=...      # см. раздел «Переменные Supabase» ниже
export SUPABASE_SERVICE_ROLE_KEY=...
python3 -m pytest tests/integration/test_upload_flow_integration.py -v -m integration
```

**Важно:** после `-m` обязательно указать имя маркера: **`-m integration`** (иначе pytest выдаст «argument -m: expected one argument»).

Без `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY` все тесты будут пропущены (skip). Если переменные заданы в `bot/.env`, отдельный `export` не нужен — тесты подхватят их через `load_dotenv` в conftest.

**Если тесты падают с «Invalid API key»:** клиент supabase-py ожидает ключ в формате JWT. Локальный `supabase status` отдаёт ключи вида `sb_secret_*`, которые библиотека может не принять. В этом случае задайте `SUPABASE_SERVICE_ROLE_KEY` JWT из облачного Dashboard (Project Settings → API → service_role) или используйте облачный проект для интеграционных тестов.

---

## Запуск Supabase (локально)

Для интеграционных тестов нужен доступный Supabase с таблицей `uploads`. Локальный стек поднимается из **корня репозитория** (Amanita), не из `bot/`.

### Требования

- Установленный **Supabase CLI**: `brew install supabase/tap/supabase` или [официальная установка](https://supabase.com/docs/guides/cli).

Проверка: `supabase --version`

### Старт и остановка

```bash
# Из корня репозитория (Amanita)
cd /path/to/Amanita

# Остановить контейнеры, если были запущены ранее
supabase stop

# Запустить локальный Supabase
supabase start

# Посмотреть статус и URL/ключи
supabase status
```

В выводе `supabase status` будут блоки **APIs** (Project URL), **Database**, **Authentication Keys** и др.

Остановка:

```bash
supabase stop
```

### Переменные Supabase: что куда подставлять

**SUPABASE_URL** — адрес API Supabase (доступ к БД, REST, Auth и т.д.).

- **Локально** всегда один и тот же: `http://127.0.0.1:54321`. Можно один раз прописать в `bot/.env` и не менять при каждом `supabase start`.
- **В облаке** нужно подставить URL вашего проекта. Откуда взять: [Supabase Dashboard](https://supabase.com/dashboard) → ваш проект → **Project Settings** (шестерёнка) → **API** → поле **Project URL** (например `https://xxxxx.supabase.co`). При смене ориентации на облачный Supabase замените в `.env` значение `SUPABASE_URL` на этот URL.

**SUPABASE_SERVICE_ROLE_KEY** — секретный ключ для доступа к Supabase **с правами сервиса** (обход RLS, полный доступ к таблицам).

- **Для чего используется:** авторизация **Backend'а при обращении к Supabase API** (чтение/запись таблиц, в т.ч. `uploads`). Используется в `SupabaseService` (bot) и в интеграционных тестах при подключении к реальной БД. К **Edge Functions** это не относится — их вызывают с **anon-ключом** (Publishable) в заголовке `Authorization: Bearer <anon_key>`.
- **Откуда взять в выводе `supabase status`:** в блоке **🔑 Authentication Keys** два поля — **Publishable** (anon) и **Secret**. В `SUPABASE_SERVICE_ROLE_KEY` подставляйте значение из строки **Secret** (не Publishable). Пример: `sb_secret_******` — целиком, как выведено.

Таблица `uploads` должна существовать: применяется миграция `supabase/migrations/20260129100000_create_uploads_table.sql` при первом применении миграций. Локальный `supabase start` обычно применяет миграции из `supabase/migrations/` автоматически.

---

## Деплой Edge Function arweave-upload

Edge Function `arweave-upload` вызывается извне (Wallet/Backend); для интеграционных тестов upload flow её **запускать не обязательно** — тесты только имитируют вызовы к Backend. Ниже — как поднять функцию локально и задеплоить в облако, когда понадобится.

Полное руководство: [supabase/docs/arweave-upload-deploy-guide.md](../../../supabase/docs/arweave-upload-deploy-guide.md).

### Локальный запуск Edge Function

Из **корня репозитория**:

```bash
cd /path/to/Amanita

# .env в корне с переменными (см. раздел про ключи и контракт ниже)
supabase functions serve arweave-upload --env-file .env
```

Функция будет доступна по адресу:  
`http://127.0.0.1:54321/functions/v1/arweave-upload`

Проверка здоровья:

Подставьте ключ из строки **Publishable** (блок **🔑 Authentication Keys** вывода `supabase status`; не Secret). Локальный Edge Runtime Supabase может требовать заголовок **apikey** в дополнение к **Authorization** (или вместо него):

```bash
# Вариант 1: оба заголовка (если один не срабатывает)
curl -H "Authorization: Bearer sb_publishable_XXXX" \
     -H "apikey: sb_publishable_XXXX" \
  http://127.0.0.1:54321/functions/v1/arweave-upload/health

# Вариант 2: только Authorization
curl -H "Authorization: Bearer sb_publishable_XXXX" \
  http://127.0.0.1:54321/functions/v1/arweave-upload/health
```

Если приходит **«Missing authorization header»**: проверку делает платформа Supabase до вызова вашего кода. Убедитесь, что (1) передаёте значение **Publishable** целиком, (2) попробуйте добавить заголовок **apikey** с тем же значением, (3) локальный стек должен быть запущен: сначала `supabase start`, затем в другом терминале `supabase functions serve arweave-upload --env-file .env`.

### Деплой в облачный Supabase

1. **Логин и линковка проекта**

```bash
supabase login
cd /path/to/Amanita
supabase link --project-ref YOUR_PROJECT_REF
```

`YOUR_PROJECT_REF` — из Dashboard → Settings → General (или из URL: `https://supabase.com/dashboard/project/YOUR_PROJECT_REF`).

2. **Секреты в облаке**

Задать переменные как Secrets (без них функция не сможет вызывать Backend и проверять JWT):

```bash
supabase secrets set UPLOAD_TOKEN_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."
supabase secrets set BACKEND_URL="https://api.your-backend.com"
supabase secrets set EDGE_TO_BACKEND_SECRET="your-production-secret"
# Для публикации в Arweave (если нужна):
# supabase secrets set ARWEAVE_PRIVATE_KEY='{"kty":"RSA",...}'
```

Проверка: `supabase secrets list`

3. **Деплой функции**

```bash
supabase functions deploy arweave-upload
```

Проверка:

```bash
supabase functions list
supabase functions status arweave-upload
```

URL в облаке: `https://YOUR_PROJECT_REF.supabase.co/functions/v1/arweave-upload`

4. **Логи**

```bash
supabase functions logs arweave-upload --follow
supabase functions logs arweave-upload --since 1h
```

---

## Требования к окружению (тесты)

- Таблица `uploads` должна существовать (миграция `supabase/migrations/20260129100000_create_uploads_table.sql`).
- Опционально для полного flow с prepare: `UPLOAD_TOKEN_JWT_PRIVATE_KEY` или `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE` (см. раздел про ключи ниже).

---

## Фазы тестов

| Фаза | Класс | Содержание |
|------|--------|------------|
| Phase 1 | TestUploadIntegrationProof | Proof: insert/get в Supabase, handshake UploadService + DB |
| Phase 2 | TestUploadIntegrationContracts | Контракты API: формат ответов PUT/POST, 404/409 |
| Phase 3 | TestUploadIntegrationFlows | Потоки: happy path (put → callback → published), ошибки 404, опционально prepare→put→callback |

Всего 10 тестов. Edge не вызываем; моки только внешние (finalizer в тестах не запускается).

---

## Требования к Edge Function (контракт Backend ↔ Edge)

Edge Function `arweave-upload` вызывает Backend двумя запросами. Ниже — всё, что нужно для восстановления контекста и настройки Edge.

### Авторизация Edge → Backend

- Заголовок: `Authorization: Bearer <EDGE_TO_BACKEND_SECRET>`.
- Секрет один и тот же в Edge (env/Secret) и в Backend (env `EDGE_TO_BACKEND_SECRET`). Backend сравнивает токен из заголовка с этим значением; при несовпадении — 401.

### 1) PUT /v1/uploads/{upload_id}/status

- **Когда:** после валидации JWT и Data Item (успех) или при любой ошибке (token_invalid, signature_invalid, publish_failed).
- **Тело (успех):** `{ "status": "queued_for_publish" }`.
- **Тело (ошибка):** `{ "status": "failed", "failure_code": "token_invalid" | "signature_invalid" | "publish_failed" }`. При `status: "failed"` поле `failure_code` обязательно.
- **Ответ Backend:** 200 `{ "ok": true }` при успешном обновлении; 404 при неизвестном `upload_id`; 409 при недопустимом переходе статуса.

### 2) POST /v1/uploads/callback

- **Когда:** после успешной публикации в Arweave.
- **Тело:** JSON с полями:
  - `upload_id` (string, UUID)
  - `item_id` (string)
  - `bundle_tx_id` (string)
  - `published_at` (string, ISO 8601)
- **Ответ Backend:** 200 `{ "ok": true }` при успехе; 404 при неизвестном `upload_id`; 409 если текущий статус не `queued_for_publish` (например, callback без предварительного PUT или повторный callback).

### Переменные Edge (для вызовов Backend)

| Переменная | Назначение |
|------------|------------|
| `BACKEND_URL` | Базовый URL Backend API (без завершающего слеша), например `https://api.example.com`. |
| `EDGE_TO_BACKEND_SECRET` | Секрет для заголовка `Authorization: Bearer ...`. Должен совпадать с `EDGE_TO_BACKEND_SECRET` в Backend. |

Подробный контракт и порядок обработки в Edge: [supabase/docs/arweave-upload-publish-api.md](../../../supabase/docs/arweave-upload-publish-api.md).

---

## JWT upload_token: генерация и хранение ключей

Backend подписывает JWT алгоритмом **RS256** (RSA). Edge только **проверяет** подпись с помощью **публичного** ключа; приватный ключ хранится только в Backend.

### Зачем две половинки

- **Приватный ключ (Backend):** подпись JWT при `prepare()`; без него Backend не может выдать валидный `upload_token`.
- **Публичный ключ (Edge):** проверка подписи и claims (`exp`, `upload_id`, `max_bytes`); без него Edge не примет токен.

Одна пара ключей: генерируем один раз, приватный — только в Backend, публичный — в Edge (env/Secret).

### Генерация пары RSA (один раз)

```bash
# Приватный ключ (PEM), 2048 бит
openssl genrsa -out upload_token_private.pem 2048

# Публичный ключ (PEM) из приватного
openssl rsa -in upload_token_private.pem -pubout -out upload_token_public.pem
```

Файлы:
- `upload_token_private.pem` — только Backend, не коммитить, не отдавать в Edge.
- `upload_token_public.pem` — в Edge в переменную `UPLOAD_TOKEN_JWT_PUBLIC_KEY`.

### Хранение в Backend (приватный ключ)

Backend читает ключ при подписании JWT (модуль `services/upload/jwt_upload_token.py`). Поддерживаются два способа:

1. **Переменная окружения `UPLOAD_TOKEN_JWT_PRIVATE_KEY`**  
   Строка PEM целиком. В shell/env переносы строк часто задают как `\n`; код заменяет `\n` на реальный перевод строки.  
   Пример (одна строка):  
   `UPLOAD_TOKEN_JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"`

2. **Файл и переменная `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE`**  
   Путь к файлу с PEM (например, `upload_token_private.pem`). Код читает содержимое из файла. Удобно, когда ключ лежит в секретном томе или отдельном файле, а не в env.

Если не заданы ни переменная, ни валидный файл — при вызове `prepare()` будет выброшено исключение с сообщением о необходимости настроить ключ.

### Хранение в Edge (публичный ключ)

- **Переменная:** `UPLOAD_TOKEN_JWT_PUBLIC_KEY`.
- **Формат:** PEM (`-----BEGIN PUBLIC KEY-----` … `-----END PUBLIC KEY-----`) или одна строка JSON JWK (см. [arweave-upload-security.md](../../../supabase/docs/arweave-upload-security.md)).
- **Где:** Supabase Secrets (production), локально — в `.env`. В Edge хранится только публичный ключ.

### Сводка по переменным

| Где | Переменная | Содержимое |
|-----|------------|------------|
| Backend | `UPLOAD_TOKEN_JWT_PRIVATE_KEY` | PEM приватного ключа (строка, `\n` допустимы) |
| Backend | `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE` | Путь к файлу с PEM приватного ключа |
| Edge | `UPLOAD_TOKEN_JWT_PUBLIC_KEY` | PEM или JWK публичного ключа |

Одна пара ключей — генерируем один раз, приватный только в Backend, публичный только в Edge. Ротация: генерируем новую пару, меняем в Backend и Edge, старые токены перестанут проходить проверку после истечения `exp`.

### Claims JWT (для восстановления контекста)

В токене хранятся: `upload_id`, `user_id`, `max_bytes`, `exp` (timestamp), `iat` (timestamp). Edge проверяет подпись, `exp`, соответствие `upload_id` и что `payload_size` из запроса ≤ `max_bytes`.
