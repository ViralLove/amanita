# Task: implement — Edge Function приём signed item + upload_token (user signs, operator pays)

**Рутовый контекст:** только `supabase/`. Контракт с Backend (bot) и референс архитектуры: [Arweave data upload.md](../../../docs/analysis/epics/activities%20crud%20and%20search/Arweave%20data%20upload.md). Эпик: [epic-activities-api-production.md](../../../docs/analysis/epics/activities%20crud%20and%20search/epic-activities-api-production.md) Фаза 3, таск 3.1.

---

## Цель

Реализовать в Supabase Edge Function поток «user signs, operator pays»: endpoint приёма **signed Data Item** и **upload_token** от Wallet; валидация **JWT RS256** (публичный ключ в Edge); sanity check подписи Data Item и тега `Upload-Id`; два вызова в Backend (обновление статуса `queued_for_publish`, callback с `bundle_tx_id`); bundling и публикация в Arweave с оплатой кошельком оператора (operator JWK).

## Почему это важно (риск)

Без рабочей Edge по этой схеме невозможен полный поток Фазы 3 Epic Activities: пользователь подписывает данные в Wallet, оператор оплачивает storage. Текущая реализация Edge (`arweave-upload`) рассчитана на старый поток (Backend шлёт данные, Edge подписывает транзакцию); контракт «user signs, operator pays» и два вызова Backend не реализованы.

## Границы (что НЕ входит)

- Backend: таблица uploads, JWT RS256 выпуск, endpoints status/callback, Finalizer job — таск 3.2 (bot).
- Wallet: подпись Data Item, UI, отправка в Edge — отдельный таск в `wallet/`.
- Realtime: эмит событий по статусам — Backend (и опционально в эпике).

---

## Факты из кода / референсы

### 1) Архитектура «user signs, operator pays» и контракт Edge

- `docs/analysis/epics/activities crud and search/Arweave data upload.md`
  - Разд. 1.3: Edge проверяет `upload_token`, sanity check data item и подписи, bundling/публикация, callback в backend с `bundle_tx_id`.
  - Разд. 4.2: **POST /edge/v1/publish** — request: `upload_token`, `upload_id`, `signed_data_item`, `item_id?`, `payload_size`. Edge валидирует токен (JWT RS256 — разд. 4.2 вариант B), проверяет подпись Data Item и тег `Upload-Id`, ставит backend статус `queued_for_publish`, после публикации вызывает backend callback.
  - Разд. 10 (sequence): Edge → Backend UpdateStatus(queued_for_publish); Edge → Arweave bundle tx (operator signs); Edge → Backend Callback(upload_id, item_id, bundle_tx_id, published_at).

### 2) Текущая Edge Function

- `supabase/functions/arweave-upload/index.ts`
  - Endpoints: `/health` (GET), `/upload-text` (POST), `/upload-file` (POST).
  - `loadArweavePrivateKey()` — загрузка operator JWK из env/file.
  - `signTransaction(arweave, transaction, privateKey)` из `arweave/compatible.ts` — подпись транзакции оператором.
  - Нет endpoint'а приёма signed item + upload_token; нет валидации JWT RS256; нет вызовов Backend (status, callback).

### 3) JWT RS256 в Edge

- `Arweave data upload.md` разд. 4.2: Backend подписывает JWT **приватным** ключом (RSA); Edge проверяет **публичным** ключом. Claims: `upload_id`, `user_id`, `max_bytes`, `exp`. Проверка локальная (без вызова Backend).

### 4) Два вызова Edge → Backend

- `Arweave data upload.md` разд. 10, 11.2: (1) UpdateStatus(upload_id, status=queued_for_publish); (2) Callback с upload_id, item_id, bundle_tx_id, published_at. В эпике зафиксировано: Backend предоставляет `PUT /v1/uploads/{upload_id}/status` и `POST /v1/uploads/callback` (таск 3.2 bot).

### 5) Коды ошибок

- Документ Arweave разд. 10 (alt): TOKEN_INVALID, SIGNATURE_INVALID, PUBLISH_FAILED. Edge при ошибке вызывает Backend UpdateStatus(upload_id, status=failed, reason=token_invalid | signature_invalid | publish_failed).

---

## Gap / Проблема

1. Отсутствует endpoint **POST /edge/v1/publish** (или эквивалент в текущей функции) для приёма `upload_token`, `upload_id`, `signed_data_item`, `item_id?`, `payload_size`.
2. Не реализована валидация **upload_token** по JWT RS256 (публичный ключ в Edge — env/Supabase Secret).
3. Не реализован sanity check **Data Item**: подпись, наличие тега `Upload-Id` = upload_id, payload_size <= max_bytes из токена.
4. Отсутствуют вызовы Backend: **PUT** (status queued_for_publish или failed с reason) и **POST** (callback с bundle_tx_id).
5. Не реализованы: приём уже подписанного Data Item от пользователя, добавление в bundle, подпись **bundle tx** кошельком оператора, отправка в Arweave, получение bundle_tx_id и передача в callback.
6. Ошибки (invalid token, invalid signature, publish failure) не маппятся в коды и не приводят к вызову Backend status=failed.

---

## AC/DoD

_Верификация: [acceptance-verification.md](acceptance-verification.md). Статус по плану: [implementation-plan-status.md](implementation-plan-status.md)._

### Endpoint и контракт (P0)

- [x] Endpoint **POST /edge/v1/publish** (или маршрут в существующей Edge Function): тело запроса — `upload_token`, `upload_id`, `signed_data_item` (serialized), `item_id?`, `payload_size`.
- [x] Response при успешном приёме: `{ ack: true, status: "queued_for_publish" }` (без ожидания публикации в ответе).
- [x] При ошибке валидации: HTTP 4xx, тело с полем `code`: `token_invalid` | `signature_invalid` | `publish_failed` (и при необходимости `message`). _Примечание: при async-публикации ответ клиенту с `publish_failed` не отдаётся (200 уже отдан); Backend получает putStatus failed._

### Валидация upload_token JWT RS256 (P0)

- [x] Публичный ключ Backend (RSA) доступен в Edge (Supabase Secret или env).
- [x] Проверка подписи JWT алгоритмом RS256; проверка `exp`, совпадение `upload_id` из payload с телом запроса, `payload_size <= max_bytes`.
- [x] При невалидном/истёкшем токене: ответ с `code: token_invalid`, вызов Backend **PUT /v1/uploads/{upload_id}/status** с `status=failed`, `failure_code=token_invalid`.

### Sanity check Data Item (P0)

- [x] Парсинг/валидация формата signed_data_item (Data Item: id, raw payload, signature, tags).
- [x] Проверка подписи Data Item (RSA-PSS / совместимо с Arweave).
- [x] Проверка наличия тега `Upload-Id` и совпадения значения с `upload_id` из запроса.
- [x] При невалидной подписи или теге: ответ с `code: signature_invalid`, вызов Backend status=failed, `failure_code=signature_invalid`.

### Вызовы Backend (P0)

- [x] После успешной валидации: вызов Backend **PUT /v1/uploads/{upload_id}/status** с телом `{ "status": "queued_for_publish" }` (авторизация по контракту bot–Edge).
- [x] После успешной публикации в Arweave: вызов Backend **POST /v1/uploads/callback** с телом `{ upload_id, item_id, bundle_tx_id, published_at }`.
- [x] При ошибке публикации (gateway/Arweave): вызов Backend status=failed, `failure_code=publish_failed`; ответ клиенту `code: publish_failed`. _См. примечание выше (async, 200 уже отдан)._

### Bundling и публикация (P0)

- [x] Принятый signed Data Item добавляется в bundle (или публикуется один item — N=1 допустимо по эпику).
- [x] Создание Arweave bundle tx (data = bundle_bytes), подпись **bundle tx** кошельком оператора (operator JWK), отправка в Arweave.
- [x] Получение `bundle_tx_id`, передача в callback Backend.

### Тесты (P0)

- [x] Unit/интеграционные тесты: невалидный/истёкший токен → token_invalid и вызов Backend status failed; невалидная подпись/тег → signature_invalid; успешный путь: status queued_for_publish → публикация → callback с bundle_tx_id. _Покрытие по модулям (validate-token, validate-data-item, arweave-rsa-pss); сводный publish-flow с моками Backend/Arweave — опционально._

### Безопасность и конфигурация (P1)

- [x] Публичный ключ JWT и URL Backend не хардкодятся в коде (Secrets/env).
- [x] Логирование переходов (принят запрос, токен ок, Data Item ок, вызов status, публикация, callback) без логирования payload/секретов.

---

## Документация (перманентная зона)

- **API и контракт publish:** [supabase/docs/arweave-upload-publish-api.md](../../arweave-upload-publish-api.md) — request/response, вызовы Backend, env, порядок обработки.
- **CHANGELOG по таску:** [CHANGELOG-task-arweave-upload-publish.md](CHANGELOG-task-arweave-upload-publish.md) — добавлено/не входит.

---

## Где менять код

| Роль | Файл/место | Действие |
|------|------------|----------|
| Runtime | `supabase/functions/arweave-upload/index.ts` (или новый handler) | Добавить маршрут POST /edge/v1/publish; оркестрация: validate token → validate Data Item → call Backend status → bundle/publish → call Backend callback. |
| Runtime | Новый модуль (например `publish/validate-token.ts`) | Валидация JWT RS256 (публичный ключ из env), проверка claims. |
| Runtime | Новый модуль (например `publish/validate-data-item.ts`) | Парсинг signed_data_item, проверка подписи и тега Upload-Id. |
| Runtime | Модуль вызовов Backend (например `publish/backend-calls.ts`) | PUT .../status, POST .../callback с авторизацией по контракту. |
| Runtime | Существующий или новый код bundling | Добавление signed Data Item в bundle, подпись bundle tx operator JWK (`arweave/compatible.ts` или аналог для bundle), отправка в Arweave. |
| Tests | `supabase/functions/arweave-upload/tests/` | Тесты: token invalid, signature invalid, success path (status + callback), publish_failed. |

---

## План выполнения

1. **Контракт и маршрут** — добавить POST /edge/v1/publish, описать контракт запроса/ответа по Arweave data upload.md.
2. **JWT RS256** — реализовать проверку upload_token (публичный ключ в Edge), обработка token_invalid и вызов Backend status=failed.
3. **Data Item** — парсинг и sanity check подписи и тега Upload-Id; обработка signature_invalid и вызов Backend status=failed.
4. **Backend: status** — вызов PUT /v1/uploads/{upload_id}/status после успешной валидации (и при ошибках с failure_code).
5. **Bundling и публикация** — использование принятого signed item в bundle (или single), подпись bundle tx оператором, отправка в Arweave, получение bundle_tx_id.
6. **Backend: callback** — вызов POST /v1/uploads/callback с upload_id, item_id, bundle_tx_id, published_at; при ошибке публикации — только status=failed, publish_failed.
7. **Тесты** — сценарии token_invalid, signature_invalid, publish_failed, успешный путь; при необходимости моки Backend.

---

## Команды проверки

### После реализации

```bash
# Локальный запуск Edge Function
cd supabase && supabase functions serve arweave-upload

# Проверка endpoint (пример; подставить реальные BACKEND_URL, токен, signed item)
curl -X POST http://localhost:54321/functions/v1/arweave-upload/edge/v1/publish \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"upload_token":"<JWT>","upload_id":"<uuid>","signed_data_item":"<base64>","payload_size":128}'
# Ожидаем: 200, { ack: true, status: "queued_for_publish" } и вызовы Backend (status, затем callback после публикации)
```

### Тесты

```bash
cd supabase/functions/arweave-upload
deno test tests/
# Ожидаем: все тесты проходят, включая сценарии token_invalid, signature_invalid, success, publish_failed
```

---

## Метаданные задачи

| Поле | Значение |
|------|----------|
| **Приоритет** | P0 |
| **Сложность** | L |
| **Оценка времени** | 2–4 дня |
| **Зависимости** | Контракт Backend (таск 3.2 bot): PUT .../status, POST .../callback; формат JWT RS256 и публичный ключ в Edge. Таск 3.2 можно начинать с моков Edge. |
| **Тэги** | supabase, edge-functions, arweave, jwt-rs256, user-signs-operator-pays |
| **Статус** | implemented (верификация по AC: acceptance-verification.md) |

---

## Зависимости

- **Таск 3.2 (bot):** предоставляет endpoints PUT /v1/uploads/{upload_id}/status и POST /v1/uploads/callback; выпускает upload_token JWT RS256 (приватный ключ в Backend). Для разработки Edge допустимы моки Backend.
- **Референс:** [Arweave data upload.md](../../../docs/analysis/epics/activities%20crud%20and%20search/Arweave%20data%20upload.md) — разделы 2 (теги), 4.2 (Edge API, JWT RS256), 10 (sequence), 11.

---

**Версия:** 2.0  
**Дата:** 2026-01-29  
**Предыдущая версия:** таск описывал старый поток (operator signs транзакцию); обновлён под архитектуру «user signs, operator pays» и контракт из Arweave data upload.md и эпика Фаза 3.
