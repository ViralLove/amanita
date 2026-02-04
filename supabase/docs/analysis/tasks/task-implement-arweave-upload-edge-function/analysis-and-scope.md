# Этап 1: Анализ и рамки

**Таск:** [task-implement-arweave-upload-edge-function.md](../task-implement-arweave-upload-edge-function.md)  
**Дата:** 2026-01-29  
**Методика:** @.cursor/commands/run-analysis.md — только факты из кода, без предположений.

---

## 1. Факты из кода (что есть)

### 1.1 Edge Function: index.ts

- **Файл:** `supabase/functions/arweave-upload/index.ts`
- **Роутинг:** `serve()`, `const url = new URL(req.url)`, `const path = url.pathname`; ветвление по `path.endsWith(...)` и `req.method`.
- **Существующие маршруты:**
  - `path === '/' || path.endsWith('/health')` && GET → health check (JSON status, timestamp, arweave).
  - `path.endsWith('/upload-text')` && POST → validateTextUpload(body), uploadText(), возврат transaction_id.
  - `path.endsWith('/upload-file')` && POST → formData, file, uploadFile(), возврат transaction_id.
  - Иначе → 404 "Endpoint not found".
- **CORS:** corsHeaders заданы; OPTIONS возвращает 'ok'.
- **Ошибки:** catch → 500, JSON `{ success: false, error: errorMessage }`.
- **Arweave:** `Arweave.init(...)`, `loadArweavePrivateKey()` из env `ARWEAVE_PRIVATE_KEY_FILE` (файл JWK), `signTransaction(arweave, transaction, privateKey)` из `./arweave/compatible.ts`.

### 1.2 Подпись транзакции: arweave/compatible.ts

- **Файл:** `supabase/functions/arweave-upload/arweave/compatible.ts`
- **Импорт:** `import { signArweaveTransaction } from "../crypto/arweave-rsa-pss.ts";`
- **Функция:** `signTransaction(arweave, transaction, privateKey)` — getSignatureData(), signArweaveTransaction(), устанавливает transaction.signature и transaction.id.
- **Факт:** файл `crypto/arweave-rsa-pss.ts` **отсутствует** в репозитории (в `crypto/` есть только `pss_wasm.ts` и `pss.wasm`). Вызов `/upload-text` или `/upload-file` приведёт к ошибке загрузки модуля при первом обращении.

### 1.3 crypto/

- **Содержимое:** `pss_wasm.ts`, `pss.wasm` — реализация подписи через WebAssembly; нет `arweave-rsa-pss.ts`.

### 1.4 Контракт по таску и Arweave data upload.md

- **Требуется:** POST /edge/v1/publish, тело: `upload_token`, `upload_id`, `signed_data_item`, `item_id?`, `payload_size`.
- **Ответ при успехе:** `{ ack: true, status: "queued_for_publish" }`.
- **При ошибке:** HTTP 4xx, тело с `code`: `token_invalid` | `signature_invalid` | `publish_failed`.
- **Логика:** валидация JWT RS256 (публичный ключ в Edge) → sanity check Data Item (подпись, тег Upload-Id) → PUT Backend status queued_for_publish → bundle/publish → POST Backend callback с bundle_tx_id; при любой ошибке — Backend PUT status failed с failure_code.

---

## 2. Gap (чего нет, что нужно сделать)

| # | Требование таска | Есть в коде | Gap |
|---|------------------|-------------|-----|
| 1 | Endpoint POST /edge/v1/publish | Нет; есть только /health, /upload-text, /upload-file | Добавить ветку по path.endsWith('/edge/v1/publish') && POST. |
| 2 | Валидация upload_token JWT RS256 (публичный ключ в Edge) | Нет | Реализовать модуль проверки JWT RS256 (публичный ключ из env/Secret). |
| 3 | Sanity check Data Item (подпись, тег Upload-Id) | Нет | Реализовать парсинг signed_data_item и проверку подписи и тега. |
| 4 | Вызов Backend PUT /v1/uploads/{id}/status | Нет | Реализовать fetch к BACKEND_URL с авторизацией (контракт bot–Edge). |
| 5 | Вызов Backend POST /v1/uploads/callback | Нет | Реализовать после успешной публикации. |
| 6 | Bundling и публикация (принять signed item, подписать bundle tx оператором, отправить в Arweave) | Есть только uploadText/uploadFile (оператор создаёт и подписывает транзакцию с данными); нет приёма готового Data Item и bundle | Реализовать приём signed_data_item, формирование bundle (или N=1), подпись bundle tx operator JWK, отправка, получение bundle_tx_id. |
| 7 | Ответы с code (token_invalid, signature_invalid, publish_failed) и вызов Backend status=failed при ошибках | Нет; текущие ошибки — 500 с error message | Добавить ответы 4xx с полем code и вызов PUT status с failure_code. |
| 8 | Публичный ключ JWT и BACKEND_URL из env/Secrets | Нет (только ARWEAVE_PRIVATE_KEY_FILE) | Использовать env/Secrets для JWT_PUBLIC_KEY (или аналог), BACKEND_URL, авторизации к Backend. |

**Дополнительно:** зависимость `arweave/compatible.ts` от несуществующего `crypto/arweave-rsa-pss.ts` блокирует текущие upload-text/upload-file. Для нового потока publish нужна подпись **bundle tx** оператором — либо добавить `arweave-rsa-pss.ts`, либо использовать существующий `pss_wasm` для подписи bundle tx (решение вынести в Этап 2).

---

## 3. Рамки (scope) таска

- **Входит:** только `supabase/` — Edge Function: маршрут /edge/v1/publish, JWT RS256, Data Item check, вызовы Backend, bundling/публикация, тесты.
- **Не входит:** Backend (таск 3.2 bot), Wallet (отдельный таск), Realtime (Backend).

---

## 4. Итог этапа 1

- **Факты зафиксированы:** текущий роутинг, наличие/отсутствие модулей, контракт из таска.
- **Gap зафиксирован:** 8 пунктов; отдельно — зависимость compatible.ts от отсутствующего arweave-rsa-pss.ts.
- **Готовность к Этапу 2:** решения (decision-points) — формат signed_data_item, источник публичного ключа для Data Item, использование pss_wasm vs arweave-rsa-pss для подписи bundle tx, авторизация Edge→Backend.

**Следующий шаг:** Этап 2 — решения до кода (decision-points), согласование с оператором.
