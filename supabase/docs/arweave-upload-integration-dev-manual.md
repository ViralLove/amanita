# Dev Manual: интеграция Arweave-загрузки (user signs, operator pays)

**Назначение:** пошаговый мануал для интеграции потока «user signs, operator pays» в другой проект. Поток отработан в Amanita (Edge Function `arweave-upload`). Мануал позволяет воспроизвести полную цепочку: Signer app → Edge → Backend → Arweave.

**Архитектура:** отдельно задеплоенное **Signer app** хранит Arweave-ключ и подписывает Data Item; оператор (Edge) платит за публикацию bundle.

**Версия:** 1.1  
**Дата:** 2026-02-04  
**Референс:** `supabase/functions/arweave-upload`, `supabase/docs/arweave-upload-*.md`

*Changelog v1.1:* архитектура изменена: вместо user wallet — отдельно деплоируемый Signer app с ключом.

---

## 1. Обзор и предварительные требования

### 1.1 Что интегрируем

- **Edge Function** (Supabase): приём signed Data Item + JWT, валидация, bundle, публикация в Arweave.
- **Backend**: эндпоинт prepare (выдача JWT), PUT status, POST callback.
- **Signer app** (отдельный сервис): хранит Arweave-ключ (JWK), создаёт signed Data Item (ANS-104) с тегом Upload-Id, вызывает Edge POST /edge/v1/publish.

### 1.2 Предварительные требования

- Supabase проект (локально: `supabase start`)
- Supabase CLI: `brew install supabase/tap/supabase`
- Deno: `brew install deno`
- Backend на любом стеке (Python, Node, Go и т.д.)
- Signer app — отдельно деплоируемое приложение (любой стек)
- Кошелёк Arweave (JWK) для оператора (оплата bundle tx в Edge)

### 1.3 Роли и поток данных

```
Signer app                  Edge Function                    Backend                    Arweave
(отдельный сервис)               |                              |                           |
     |                           |                              |                           |
     | 1. prepare (upload_id)   |                              |                           |
     |----------------------------------------------------------->|                           |
     | 2. JWT (upload_token)    |<-----------------------------------------------------------|
     |<-----------------------------------------------------------|                           |
     | 3. Создаёт Data Item     |                              |                           |
     |    с тегом Upload-Id,    |                              |                           |
     |    подписывает ключом    |                              |                           |
     |    (JWK в Signer app)    |                              |                           |
     |                           |                              |                           |
     | 4. POST /edge/v1/publish |                              |                           |
     |    { upload_token,       |                              |                           |
     |      upload_id,          |                              |                           |
     |      signed_data_item,   |                              |                           |
     |      payload_size }      |                              |                           |
     |------------------------->| 5. validate JWT + Data Item  |                           |
     |                           | 6. PUT status queued ------->|                           |
     |<-------------------------| 7. 200 { ack }               |                           |
     |                           | 8. bundle + sign bundle tx   |                           |
     |                           | 9. post to Arweave --------->|-------------------------->|
     |                           |10. POST callback ----------->|                           |
```

---

## 2. Фаза 1: Edge Function

### 2.1 Копирование файлов

Скопируй из `supabase/functions/arweave-upload/` в свой проект (`supabase/functions/<имя-функции>/`) следующие файлы и папки:

| Путь | Назначение |
|------|------------|
| `index.ts` | Entry, роутинг, publish handler |
| `arweave/` | compatible.ts — подпись транзакций |
| `crypto/` | arweave-rsa-pss.ts — RSA-PSS через Web Crypto |
| `publish/` | validate-token.ts, validate-data-item.ts, deep-hash.ts, backend-calls.ts, bundle-publish.ts |
| `deno_shim.d.ts` | Декларации для IDE (URL-модули) |
| `deno_global.d.ts` | Декларация Deno |
| `deno.json` | imports, compilerOptions |
| `tsconfig.json` | TypeScript config |
| `npm-arweave.d.ts` | Типы для Arweave |

**Структура после копирования:**
```
supabase/functions/<имя-функции>/
├── index.ts
├── arweave/compatible.ts
├── crypto/arweave-rsa-pss.ts
├── publish/
│   ├── validate-token.ts
│   ├── validate-data-item.ts
│   ├── deep-hash.ts
│   ├── backend-calls.ts
│   └── bundle-publish.ts
├── deno_shim.d.ts
├── deno_global.d.ts
├── deno.json
├── tsconfig.json
└── npm-arweave.d.ts
```

### 2.2 Маршрут publish

В `index.ts` условие для publish:

```typescript
if (path.endsWith("/edge/v1/publish") && req.method === "POST") {
```

**URL для вызова publish:**
```
POST https://<project-ref>.supabase.co/functions/v1/<имя-функции>/edge/v1/publish
```

Пример: `POST https://xxx.supabase.co/functions/v1/arweave-upload/edge/v1/publish`

Path в handler приходит как `/functions/v1/<имя-функции>/edge/v1/publish` — условие `path.endsWith("/edge/v1/publish")` выполняется.

### 2.3 Поддержка ARWEAVE_PRIVATE_KEY (облако)

В production Supabase Cloud нет файловой системы. Код `loadArweavePrivateKey()` должен поддерживать чтение из `ARWEAVE_PRIVATE_KEY` (JSON-строка JWK):

```typescript
const loadArweavePrivateKey = async (): Promise<JsonWebKey> => {
  const keyJson = Deno.env.get("ARWEAVE_PRIVATE_KEY");
  if (keyJson) {
    const parsed = JSON.parse(keyJson) as JsonWebKey;
    if (parsed.kty && parsed.e && parsed.n && parsed.d) return parsed;
    throw new Error("ARWEAVE_PRIVATE_KEY invalid JWK");
  }
  const path = Deno.env.get("ARWEAVE_PRIVATE_KEY_FILE");
  if (!path) throw new Error("ARWEAVE_PRIVATE_KEY or ARWEAVE_PRIVATE_KEY_FILE required");
  const raw = await Deno.readTextFile(path);
  return JSON.parse(raw) as JsonWebKey;
};
```

Если в копии только `ARWEAVE_PRIVATE_KEY_FILE` — добавь ветку для `ARWEAVE_PRIVATE_KEY`.

---

## 3. Фаза 2: Backend

### 3.1 Контракты Backend

Backend должен реализовать три элемента:

#### A. Prepare (выдача JWT)

Signer app (или вызывающий его клиент) запрашивает право на upload. Backend возвращает `upload_id` (UUID) и `upload_token` (JWT RS256).

**JWT payload:**
```json
{
  "exp": 1738684800,
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "max_bytes": 1048576
}
```

**Алгоритм подписи:** RS256 (RSA PKCS#1 v1.5, SHA-256). Публичный ключ Backend передаётся в Edge как `UPLOAD_TOKEN_JWT_PUBLIC_KEY` (PEM или JWK).

**Генерация ключей (OpenSSL):**
```bash
openssl genrsa -out private_upload_jwt.pem 2048
openssl rsa -in private_upload_jwt.pem -pubout -out public_upload_jwt.pem
```

#### B. PUT /v1/uploads/{upload_id}/status

Edge вызывает при валидации (успех или ошибка).

**Request:**
- URL: `{BACKEND_URL}/v1/uploads/{upload_id}/status`
- Method: PUT
- Headers: `Authorization: Bearer {EDGE_TO_BACKEND_SECRET}`, `Content-Type: application/json`
- Body (успех): `{ "status": "queued_for_publish" }`
- Body (ошибка): `{ "status": "failed", "failure_code": "token_invalid" | "signature_invalid" | "publish_failed" }`

#### C. POST /v1/uploads/callback

Edge вызывает после успешной публикации в Arweave.

**Request:**
- URL: `{BACKEND_URL}/v1/uploads/callback`
- Method: POST
- Headers: те же
- Body: `{ "upload_id", "item_id", "bundle_tx_id", "published_at" }` (ISO 8601)

### 3.2 Переменные Backend

- Приватный RSA-ключ для подписи JWT (хранить в секретах).
- `EDGE_TO_BACKEND_SECRET` — тот же, что в Edge (общий секрет для проверки Bearer).

---

## 4. Фаза 3: Signer app

**Signer app** — отдельно деплоируемое приложение. Хранит Arweave-ключ (JWK) и отвечает за подпись Data Item. Получает prepare от Backend, создаёт signed Data Item и отправляет его в Edge.

### 4.1 Создание Data Item (ANS-104)

Signer app должен:

1. Собрать payload (данные для публикации).
2. Создать Data Item по ANS-104:
   - Signature type: 1 (RSA)
   - Owner: SPKI публичного ключа Signer app (RSA-2048)
   - Теги: минимум `Upload-Id` = `upload_id` из prepare
   - Data: payload
3. Вычислить deep-hash по спецификации Arweave (см. `publish/deep-hash.ts`).
4. Подписать deep-hash своим ключом (JWK хранится в Signer app): RSA-PSS, saltLength 32, SHA-256.
5. Собрать бинарный Data Item и закодировать в base64.

**Формат Data Item (упрощённо):**
- 2 байта: signature type (1 для RSA)
- 256 байт: signature
- 294 байта: owner (SPKI)
- 1 байт: target present (0)
- 1 байт: anchor present (0)
- 8 байт: num tags (little-endian)
- 8 байт: tag bytes length
- Avro-encoded tags (name, value)
- data

**Тег обязателен:** `Upload-Id` = `upload_id` из JWT. Без него Edge отклонит запрос.

### 4.2 Вызов Edge

```http
POST https://<project-ref>.supabase.co/functions/v1/<имя-функции>/edge/v1/publish
Authorization: Bearer <SUPABASE_ANON_KEY>
Content-Type: application/json

{
  "upload_token": "<JWT от Backend>",
  "upload_id": "<UUID из prepare>",
  "signed_data_item": "<base64 бинарного Data Item>",
  "payload_size": 12345
}
```

`payload_size` — размер payload в байтах. Должен быть ≤ `max_bytes` из JWT.

**Примечание:** Создание Data Item (ANS-104) — нетривиально. Signer app может использовать `arweave` npm-пакет (createDataItem), или `@ardrive/turbo-sdk`, или собственную реализацию по спецификации. Референс deep-hash и формата — `publish/deep-hash.ts`, `publish/validate-data-item.ts`. JWK Signer app хранится в секретах/переменных окружения приложения.

---

## 5. Конфигурация и секреты

### 5.1 Переменные Signer app

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `ARWEAVE_SIGNER_PRIVATE_KEY` | да | JSON-строка JWK для подписи Data Item (хранить в секретах) |
| `BACKEND_URL` | да | URL Backend для prepare |
| `EDGE_PUBLISH_URL` | да | URL Edge: `https://<project>.supabase.co/functions/v1/<имя-функции>/edge/v1/publish` |
| `SUPABASE_ANON_KEY` | да | Для заголовка Authorization при вызове Edge |

### 5.2 Переменные Edge Function

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `UPLOAD_TOKEN_JWT_PUBLIC_KEY` | да | Публичный ключ Backend (PEM или JWK JSON) |
| `BACKEND_URL` | да | URL Backend API без слеша (напр. `https://api.example.com`) |
| `EDGE_TO_BACKEND_SECRET` | да | Bearer для PUT status / POST callback |
| `ARWEAVE_PRIVATE_KEY_FILE` | локально | Путь к JSON с JWK оператора |
| `ARWEAVE_PRIVATE_KEY` | облако | JSON-строка JWK оператора |

### 5.3 Локальная разработка (.env)

**Edge Function** (в корне или в supabase/):
```bash
ARWEAVE_PRIVATE_KEY_FILE=./supabase/functions/arweave-upload/arweave-wallet.json
UPLOAD_TOKEN_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjAN...
-----END PUBLIC KEY-----"
BACKEND_URL=http://localhost:8000
EDGE_TO_BACKEND_SECRET=dev-secret
```

**Signer app** (в своём проекте):
```bash
ARWEAVE_SIGNER_PRIVATE_KEY='{"kty":"RSA","n":"...","e":"AQAB","d":"..."}'
BACKEND_URL=http://localhost:8000
EDGE_PUBLISH_URL=http://127.0.0.1:54321/functions/v1/arweave-upload/edge/v1/publish
SUPABASE_ANON_KEY=...
```

### 5.4 Мок Backend (тесты без реального API)

```
BACKEND_USE_MOCK=true
BACKEND_MOCK_PUT_STATUS=200
BACKEND_MOCK_CALLBACK=200
```

Опционально: `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true` или `BACKEND_MOCK_TEST_SECRET=...` для per-request override через заголовки (см. arweave-upload-publish-api.md).

### 5.5 Облако: Supabase Secrets

```bash
supabase secrets set UPLOAD_TOKEN_JWT_PUBLIC_KEY="..."
supabase secrets set BACKEND_URL="https://api.example.com"
supabase secrets set EDGE_TO_BACKEND_SECRET="..."
supabase secrets set ARWEAVE_PRIVATE_KEY='{"kty":"RSA",...}'
```

---

## 6. Тестирование

### 6.1 Локальный запуск Edge

```bash
supabase start
supabase functions serve <имя-функции> --env-file .env
```

Проверка health:
```bash
curl -H "Authorization: Bearer $(supabase status -o json | jq -r '.ANON_KEY')" \
  http://127.0.0.1:54321/functions/v1/<имя-функции>/health
```

### 6.2 Unit-тесты (Deno)

Скопируй папку `tests/` из arweave-upload. Запуск:

```bash
cd supabase/functions/<имя-функции>
deno test tests/ --allow-env --allow-read
```

### 6.3 E2E с моком Backend

1. `BACKEND_USE_MOCK=true` в .env
2. Сгенерируй тестовый JWT (payload: exp, upload_id, max_bytes), подпиши приватным ключом Backend
3. Создай тестовый Data Item с тегом Upload-Id (можно использовать скрипт или библиотеку arweave/bundle)
4. Вызови POST /edge/v1/publish

### 6.4 Генерация тестового JWT (Node/Python)

**Node (jsonwebtoken):**
```javascript
const jwt = require('jsonwebtoken');
const fs = require('fs');
const key = fs.readFileSync('private_upload_jwt.pem');
const token = jwt.sign(
  { upload_id: 'uuid', max_bytes: 1e6, exp: Math.floor(Date.now()/1000) + 3600 },
  key,
  { algorithm: 'RS256' }
);
```

**Python (PyJWT):**
```python
import jwt
with open('private_upload_jwt.pem') as f:
    key = f.read()
token = jwt.encode(
    {'upload_id': 'uuid', 'max_bytes': 1048576, 'exp': ...},
    key, algorithm='RS256'
)
```

---

## 7. Деплой

### 7.1 Supabase Cloud

```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase secrets set ...
supabase functions deploy <имя-функции>
```

### 7.2 URL функции Edge

`https://YOUR_PROJECT_REF.supabase.co/functions/v1/<имя-функции>`

Publish endpoint: `.../functions/v1/<имя-функции>/edge/v1/publish`

### 7.3 Деплой Signer app

Signer app — самостоятельное приложение. Деплой зависит от стека (Docker, Vercel, Railway, VPS и т.д.). Обязательно:

- JWK (`ARWEAVE_SIGNER_PRIVATE_KEY`) хранить в секретах/переменных окружения, не в коде
- Доступ к Backend (prepare) и к Edge (publish)
- `EDGE_PUBLISH_URL` и `SUPABASE_ANON_KEY` для вызова Edge

---

## 8. Верификация интеграции

### 8.1 Чеклист Edge

- [ ] Файлы скопированы, импорты корректны
- [ ] `ARWEAVE_PRIVATE_KEY` поддержан для облака
- [ ] `deno test tests/` — зелёные
- [ ] Health endpoint отвечает 200

### 8.2 Чеклист Backend

- [ ] Prepare выдаёт JWT с exp, upload_id, max_bytes
- [ ] PUT /v1/uploads/{id}/status принимает Bearer, записывает статус
- [ ] POST /v1/uploads/callback принимает body с upload_id, item_id, bundle_tx_id, published_at

### 8.3 Чеклист Signer app

- [ ] Signer app хранит ARWEAVE_SIGNER_PRIVATE_KEY в секретах
- [ ] Signer app вызывает Backend prepare, получает JWT
- [ ] Signer app создаёт Data Item с Upload-Id и подписывает своим ключом
- [ ] Signer app вызывает Edge POST /edge/v1/publish

### 8.4 Чеклист E2E

- [ ] Signer app создаёт Data Item с Upload-Id
- [ ] POST /edge/v1/publish с валидным JWT и Data Item → 200 { ack, status }
- [ ] Backend получает PUT status queued_for_publish
- [ ] После публикации Backend получает POST callback с bundle_tx_id
- [ ] Транзакция видна в Arweave: `https://arweave.net/{bundle_tx_id}`

---

## 9. Связанные документы (референс Amanita)

| Документ | Содержание |
|----------|------------|
| [arweave-upload-architecture.md](./arweave-upload-architecture.md) | Архитектура, модули, порядок обработки |
| [arweave-upload-security.md](./arweave-upload-security.md) | Ключи, алгоритмы, схема безопасности |
| [arweave-upload-publish-api.md](./arweave-upload-publish-api.md) | API publish, коды ошибок, мок |
| [arweave-upload-deploy-guide.md](./arweave-upload-deploy-guide.md) | Локальный запуск, секреты, деплой |
| [crypto-in-edge-functions-guide.md](./crypto-in-edge-functions-guide.md) | Deno, Web Crypto, IDE, ошибка ts(2307) |

---

## 10. Частые проблемы

| Симптом | Решение |
|--------|---------|
| `token_invalid` | Проверить exp, upload_id, max_bytes в JWT; публичный ключ в Edge совпадает с приватным в Backend |
| `signature_invalid` | Проверить тег Upload-Id в Data Item; подпись RSA-PSS saltLength 32 |
| `publish_failed` | Проверить баланс кошелька оператора; логи Edge |
| ts(2307) на URL-импорте | См. crypto-in-edge-functions-guide.md, раздел 6.0 (Deno extension или deno_shim.d.ts) |
| Backend не получает callback | Проверить BACKEND_URL, EDGE_TO_BACKEND_SECRET; логи Edge `[publish] callback sent` |
