# Безопасность Edge Function arweave-upload: ключи, шифрование, схема

**Назначение:** постоянный документ с описанием всех криптографических ключей, механизмов проверки и шифрования, а также общей схемы безопасности потока «user signs, operator pays».

**Связанные документы:** [arweave-upload-architecture.md](./arweave-upload-architecture.md), [arweave-upload-deploy-guide.md](./arweave-upload-deploy-guide.md), [arweave-upload-publish-api.md](./arweave-upload-publish-api.md).

---

## 1. Обзор схемы: два слоя проверки

Перед публикацией в Arweave Edge проверяет два независимых слоя:

| Слой | Кто подписывает | Кто проверяет в Edge | Алгоритм | Где хранится ключ проверки/подписи |
|------|------------------|------------------------|----------|-------------------------------------|
| **upload_token (JWT)** | Backend (приватный RSA) | Edge (публичный RSA Backend) | JWT **RS256** | Публичный ключ Backend в Edge: `UPLOAD_TOKEN_JWT_PUBLIC_KEY` (env/Secret). Приватный ключ только в Backend. |
| **Data Item** | Пользователь в Wallet (свой Arweave JWK) | Edge (публичный ключ из поля **owner** Data Item) | **RSA-PSS** (Arweave), saltLength 32, SHA-256 | Edge **не хранит** ключ пользователя. Публичный ключ извлекается из самого Data Item (owner). |

Итог: Edge хранит только (1) публичный ключ Backend для JWT и (2) приватный ключ оператора для подписи **bundle-транзакции** (оплата в Arweave). Ключей пользователей в Edge нет.

---

## 2. Ключи и переменные окружения

### 2.1 Публичный ключ Backend (JWT RS256)

| Параметр | Значение |
|----------|----------|
| **Переменная** | `UPLOAD_TOKEN_JWT_PUBLIC_KEY` |
| **Назначение** | Верификация JWT `upload_token`, который выдаёт Backend перед отправкой Data Item в Edge |
| **Формат** | PEM (`-----BEGIN PUBLIC KEY-----` … `-----END PUBLIC KEY-----`) или JWK (JSON-строка) |
| **Где хранится** | Supabase Secrets (production), локально — в `.env` |
| **Кто владеет приватной парой** | Только Backend. Edge только проверяет подпись, не выпускает токены |

Backend подписывает JWT алгоритмом RS256 (RSA + PKCS#1 v1.5 signature). Edge импортирует публичный ключ через Web Crypto API и проверяет подпись и claims (`exp`, `upload_id`, `max_bytes`).

### 2.2 Секрет Edge → Backend

| Параметр | Значение |
|----------|----------|
| **Переменная** | `EDGE_TO_BACKEND_SECRET` |
| **Назначение** | Авторизация вызовов Edge к Backend: `PUT /v1/uploads/{id}/status`, `POST /v1/uploads/callback` |
| **Использование** | Заголовок `Authorization: Bearer <EDGE_TO_BACKEND_SECRET>` |
| **Где хранится** | Supabase Secrets (production), локально — в `.env` |
| **Владелец** | Общий секрет между Edge и Backend; Backend проверяет заголовок и отклоняет запросы без валидного токена |

Не используется для криптографической подписи данных — только как общий секрет для аутентификации сервис-сервис.

### 2.3 URL Backend

| Параметр | Значение |
|----------|----------|
| **Переменная** | `BACKEND_URL` |
| **Назначение** | Базовый URL Backend API (без завершающего слеша) для сборки URL статуса и callback |
| **Пример** | `https://api.example.com` |

Не секрет, но в production обычно задаётся через Secrets/конфиг.

### 2.4 Приватный ключ оператора Arweave (bundle tx)

| Параметр | Значение |
|----------|----------|
| **Переменные** | `ARWEAVE_PRIVATE_KEY_FILE` (путь к JSON-файлу с JWK) или `ARWEAVE_PRIVATE_KEY` (JSON-строка JWK) |
| **Назначение** | Подпись **bundle-транзакции** Arweave при публикации (оплата за сеть). Данные пользователя уже подписаны в Data Item ключом пользователя; оператор подписывает только саму транзакцию. |
| **Алгоритм** | RSA-PSS (Arweave), saltLength 32, реализация в `crypto/arweave-rsa-pss.ts` (Web Crypto API) |
| **Где хранится** | Локально: файл на диске, путь в `.env`. В облаке: только через Supabase Secrets как `ARWEAVE_PRIVATE_KEY` (JSON-строка) |

Это единственный приватный ключ, хранящийся в Edge. Он не используется для подписи пользовательских данных, только для подписи bundle tx и списания комиссии с кошелька оператора.

---

## 3. Что проверяет Edge перед публикацией

### 3.1 JWT (upload_token)

- Подпись JWT валидна (RS256, публичный ключ из `UPLOAD_TOKEN_JWT_PUBLIC_KEY`).
- `exp` не истёк.
- `upload_id` из payload JWT совпадает с `upload_id` из тела запроса.
- `payload_size` из запроса ≤ `max_bytes` из JWT.

При нарушении: ответ `code: token_invalid`, вызов Backend `PUT status` с `status=failed`, `failure_code=token_invalid`; в Arweave ничего не отправляется.

### 3.2 Data Item (signed_data_item)

- Декодирование base64 и парсинг формата ANS-104 (Data Item).
- Подпись Data Item валидна: RSA-PSS (saltLength 32), публичный ключ = **owner** из item (Edge не хранит ключи пользователей).
- Присутствует тег `Upload-Id`, его значение равно `upload_id` из запроса.

При нарушении: ответ `code: signature_invalid`, вызов Backend `PUT status` с `status=failed`, `failure_code=signature_invalid`; в Arweave ничего не отправляется.

### 3.3 Публикация (оператор платит)

После обеих проверок Edge:

1. Вызывает Backend `PUT status=queued_for_publish`.
2. Собирает bundle (ANS-104) из одного Data Item, создаёт bundle-транзакцию Arweave, подписывает её ключом оператора (`ARWEAVE_PRIVATE_KEY_FILE` / `ARWEAVE_PRIVATE_KEY`), отправляет в сеть.
3. При успехе вызывает Backend `POST /v1/uploads/callback` с `upload_id`, `item_id`, `bundle_tx_id`, `published_at`.
4. При ошибке публикации — Backend `PUT status=failed`, `failure_code=publish_failed`, ответ клиенту `code: publish_failed`.

---

## 4. Защита от злоупотребления бюджетом

| Механизм | Где | Описание |
|----------|-----|----------|
| Обязательный upload_token | Edge | Без валидного JWT запрос отклоняется; токен выдаёт только Backend после auth/quota. |
| exp | Edge | Истёкший токен не принимается. |
| max_bytes | Edge | `payload_size` из запроса не должен превышать `max_bytes` из JWT. |
| upload_id binding | Edge | `upload_id` из JWT должен совпадать с `upload_id` из запроса и с тегом Upload-Id в Data Item (один токен — один контекст). |
| Anchor / TTL (prepare) | Backend | Backend при prepare выдаёт одноразовый anchor и expires_at; без валидного prepare не будет валидного токена. |
| Rate limits | Backend | Ограничения uploads/min, bytes/day — Backend не выдаёт бесконечно токены. |
| Sanity check Data Item | Edge | Подпись и тег Upload-Id защищают от поддельного/чужого item и привязывают к нашему upload_id. |
| Секреты оператора | Edge / Ops | Operator JWK только в секретах; мониторинг баланса, ротация ключей по политике проекта. |

---

## 5. Криптографические алгоритмы (реализация)

| Задача | Алгоритм | Реализация |
|--------|----------|-------------|
| Верификация JWT | RS256 (RSA PKCS#1 v1.5) | Web Crypto API или библиотека djwt в Deno |
| Проверка подписи Data Item | RSA-PSS, saltLength 32, SHA-256 | Web Crypto API `crypto.subtle.verify({ name: "RSA-PSS", saltLength: 32 }, key, signature, data)` |
| Подпись bundle-транзакции оператором | RSA-PSS, saltLength 32 | `crypto/arweave-rsa-pss.ts` (Web Crypto API), используется из `arweave/compatible.ts` |

Deno 1.x (в т.ч. Supabase Edge Runtime) поддерживает RSASSA-PSS с saltLength 32; дополнительные нативные библиотеки не требуются.

---

## 6. Формат данных (контракт безопасности)

- **signed_data_item:** в теле запроса передаётся как **base64-строка** бинарного Data Item (ANS-104). Edge декодирует, парсит, извлекает owner и проверяет подпись и тег Upload-Id.
- **upload_token:** непрозрачная строка JWT; Edge проверяет подпись и claims, не передаёт токен в логи и не хранит.

Логирование: не логировать `signed_data_item`, токены, секреты и приватные ключи; только метаданные (upload_id, статусы, коды ошибок).

---

## 7. Сводка по ключам

| Ключ/секрет | Где хранится | Назначение |
|-------------|--------------|------------|
| Публичный ключ Backend (JWT) | Edge: env/Secret | Верификация upload_token |
| Приватный ключ Backend (JWT) | Только Backend | Выпуск upload_token |
| Ключ пользователя (Data Item) | Только Wallet пользователя | Подпись Data Item; в Edge не хранится, проверка по owner из item |
| EDGE_TO_BACKEND_SECRET | Edge и Backend | Авторизация Edge → Backend |
| Приватный ключ оператора Arweave | Edge: env/Secret (файл или JSON) | Подпись bundle tx, оплата в Arweave |

---

**Версия:** 1.0  
**Дата:** 2026-01-29
