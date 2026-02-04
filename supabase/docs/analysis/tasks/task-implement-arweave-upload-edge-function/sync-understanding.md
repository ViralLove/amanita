# Синхронизация понимания: Edge, криптография, Deno, существующая функция

**Дата:** 2026-01-29  
**Цель:** зафиксировать общее понимание по трём вопросам перед реализацией.

---

## 1. Edge: как проверяет то, что уходит в Arweave? Криптография, ключи, защита от абьюза

### 1.1 Две отдельные проверки (два слоя)

| Слой | Кто подписывает | Кто проверяет в Edge | Криптография | Где ключ |
|------|------------------|----------------------|--------------|----------|
| **upload_token (JWT)** | Backend (приватный RSA) | Edge (публичный RSA Backend) | JWT **RS256** (RSA signature) | Публичный ключ Backend в Edge: `UPLOAD_TOKEN_JWT_PUBLIC_KEY` (env/Secret). Приватный ключ только в Backend. |
| **Data Item** | Пользователь в Wallet (свой Arweave JWK) | Edge (публичный ключ **из самого Data Item** — поле owner) | **RSA-PSS** (Arweave), saltLength 32, SHA-256 | Edge **не хранит** ключ пользователя. Из Data Item извлекается owner (публичный ключ), им проверяется подпись item. |

**Итог:** Edge хранит только (1) публичный ключ Backend для JWT и (2) приватный ключ оператора для подписи **bundle-транзакции** (оплата). Ключей пользователей в Edge нет.

### 1.2 Что именно проверяет Edge перед публикацией

1. **JWT (upload_token):**
   - Подпись JWT валидна (RS256, публичный ключ Backend).
   - `exp` не истёк.
   - `upload_id` из payload JWT совпадает с `upload_id` из тела запроса.
   - `payload_size` из запроса ≤ `max_bytes` из JWT.
   - При нарушении → ответ `code: token_invalid`, вызов Backend `PUT status failed, failure_code=token_invalid`; в Arweave **ничего не отправляется**.

2. **Data Item (signed_data_item):**
   - Парсинг формата (ANS-104, base64).
   - Подпись Data Item валидна (RSA-PSS, публичный ключ = owner из item).
   - Есть тег `Upload-Id` и его значение = `upload_id` из запроса.
   - При нарушении → ответ `code: signature_invalid`, вызов Backend `PUT status failed, failure_code=signature_invalid`; в Arweave **ничего не отправляется**.

3. **Публикация (оператор платит):**
   - После обеих проверок Edge вызывает Backend `PUT status=queued_for_publish`.
   - Собирает bundle (один item или очередь), создаёт **bundle-транзакцию** Arweave, подписывает её **ключом оператора** (ARWEAVE_PRIVATE_KEY_FILE), отправляет в сеть.
   - Получает `bundle_tx_id`, вызывает Backend `POST /v1/uploads/callback`.
   - При ошибке публикации → Backend `PUT status failed, failure_code=publish_failed`, ответ клиенту `code: publish_failed`.

### 1.3 Механизмы защиты от абьюза бюджета

| Механизм | Где | Как |
|----------|-----|-----|
| **Обязательный upload_token** | Edge | Без валидного JWT запрос отклоняется, публикация не оплачивается. Токен выдаёт только Backend после auth/quota. |
| **exp** | Edge | Токен с истёкшим exp не принимается. |
| **max_bytes** | Edge | payload_size из запроса не должен превышать max_bytes из JWT. |
| **upload_id binding** | Edge | upload_id из JWT должен совпадать с upload_id из запроса и с тегом Upload-Id в Data Item (один токен — один контекст). |
| **Anchor single-use, TTL** | Backend | Backend при prepare выдаёт одноразовый anchor и expires_at; не входит в Edge, но без валидного prepare не будет валидного токена. |
| **Rate limits (uploads/min, bytes/day)** | Backend | Backend не выдаёт бесконечно токены; при превышении лимита новый токен не выдаётся. |
| **Sanity check Data Item** | Edge | Подпись и тег Upload-Id — защита от поддельного/чужого item и привязка к нашему upload_id. |
| **Секреты оператора** | Edge | Operator JWK только в секретах; мониторинг баланса, ротация ключей (по документу Arweave разд. 6). |

---

## 2. Подходит ли текущая версия Deno по либам криптографии?

### 2.1 Версия Deno в проекте

- **Файл:** `supabase/config.toml` → `deno_version = 1`.
- **Факт:** Supabase Edge Runtime использует Deno 1.x (в technical-guidance указана совместимость с Deno v1.45.2).

### 2.2 Что нужно для таска

| Задача | Нужная криптография | Поддержка в Deno |
|--------|----------------------|-------------------|
| Верификация JWT RS256 | RSA verify (публичный ключ Backend) | Web Crypto API: `crypto.subtle.importKey()` + `verify()` с алгоритмом RSASSA-PKCS1-v1_5 или проверка через библиотеку **djwt** (Deno JWT), которая под капотом использует Web Crypto. |
| Проверка подписи Data Item | RSA-PSS verify, saltLength 32 | Web Crypto API: `crypto.subtle.verify({ name: "RSA-PSS", saltLength: 32 }, key, signature, data)`. По [deno-webcrypto-rsassa-pss-analysis.md](../../../functions/arweave-upload/deno-webcrypto-rsassa-pss-analysis.md): **Deno 1.40+ поддерживает RSASSA-PSS с saltLength = 32**. |
| Подпись bundle-транзакции оператором | RSA-PSS sign, saltLength 32 | То же: Web Crypto API `crypto.subtle.sign()`. Реализация в `crypto/arweave-rsa-pss.ts` через Web Crypto — без внешних нативных либ. |

### 2.3 Вывод

- **Текущая версия Deno (1.x, фактически 1.40+ в Supabase) подходит.**  
- Используем **нативный Web Crypto API** для RSASSA-PSS (подпись и проверка Data Item / bundle tx) и для верификации JWT RS256 (либо напрямую через `crypto.subtle`, либо через библиотеку **djwt** для разбора JWT и проверки подписи — djwt совместима с Deno и использует Web Crypto).  
- Дополнительные нативные/Node-специфичные криптобиблиотеки не требуются; внешние зависимости минимизируем (например, только djwt для удобства JWT, если решим не писать парсинг JWT вручную).

---

## 3. Используем уже существующую функцию и её дорабатываем?

**Да.**

- Таск и план реализации предполагают **добавление маршрута** в существующую Edge Function, а не создание новой функции.
- **Файл:** `supabase/functions/arweave-upload/index.ts`.
- **Действие:** добавить ветку по `path.endsWith('/edge/v1/publish')` и `req.method === 'POST'`, внутри — оркестрация: validate token → validate Data Item → PUT Backend status → bundle/publish → POST Backend callback; при ошибках — ответы с `code` и вызов Backend status=failed.
- Существующие маршруты `/health`, `/upload-text`, `/upload-file` **не убираем** и не ломаем; при необходимости позже можно вынести старый поток в отдельный маршрут или оставить как есть.
- Общая конфигурация (CORS, Arweave client, loadArweavePrivateKey) переиспользуется; для publish добавляем чтение `UPLOAD_TOKEN_JWT_PUBLIC_KEY`, `BACKEND_URL`, `EDGE_TO_BACKEND_SECRET` из env/Secrets.

**Итог:** дорабатываем существующую функцию `arweave-upload`, один entrypoint (index.ts), один deploy.

---

## 4. Краткая сводка

| Вопрос | Ответ |
|--------|--------|
| 1. Как Edge проверяет то, что уходит в Arweave? | Два слоя: (1) JWT RS256 — проверка токена публичным ключом Backend (claims: exp, upload_id, max_bytes); (2) Data Item — проверка подписи по owner из item и тега Upload-Id. В Arweave уходит только после обеих проверок; bundle tx подписывает оператор. |
| Криптография и ключи | JWT: RS256, ключ в Edge — публичный Backend. Data Item: RSA-PSS, ключ — из item (owner). Bundle tx: RSA-PSS, ключ в Edge — приватный оператора (ARWEAVE_PRIVATE_KEY_FILE). |
| Защита от абьюза бюджета | Токен обязателен + exp + max_bytes + upload_id; anchor/rate limits на Backend; sanity check подписи и тега Data Item в Edge; оператор только подписывает tx, не данные. |
| 2. Deno подходит? | Да. Deno 1.x (1.40+) поддерживает RSASSA-PSS saltLength 32 и Web Crypto; JWT RS256 — через Web Crypto или djwt. Доп. нативные либы не нужны. |
| 3. Существующая функция? | Да. Дорабатываем `arweave-upload` (index.ts), добавляем маршрут POST /edge/v1/publish; старые маршруты сохраняем. |

Если что-то из этого расходится с твоим пониманием — напиши, скорректирую документ и следующие шаги.
