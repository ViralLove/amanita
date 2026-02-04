# CHANGELOG: Task Edge Function publish (user signs, operator pays)

**Таск:** task-implement-arweave-upload-edge-function  
**Дата:** 2026-01-29

---

## Добавлено

### Edge Function arweave-upload

- **Маршрут POST /edge/v1/publish:** приём тела `upload_token`, `upload_id`, `signed_data_item`, `payload_size`; валидация полей; при ошибке — 400 bad_request.
- **Валидация JWT RS256:** модуль `publish/validate-token.ts` — чтение публичного ключа из `UPLOAD_TOKEN_JWT_PUBLIC_KEY` (PEM или JWK), проверка подписи, exp, upload_id, payload_size ≤ max_bytes; при невалидном токене — 401 token_invalid, вызов Backend putStatus failed.
- **Валидация Data Item (ANS-104):** модули `publish/validate-data-item.ts`, `publish/deep-hash.ts` — парсинг base64 Data Item, проверка подписи RSA-PSS (saltLength 32), тег Upload-Id = upload_id; при ошибке — 400 signature_invalid, putStatus failed.
- **Вызовы Backend:** модуль `publish/backend-calls.ts` — `putStatus(uploadId, status, failureCode?)`, `postCallback(uploadId, itemId, bundleTxId, publishedAt)`; заголовок `Authorization: Bearer ${EDGE_TO_BACKEND_SECRET}`.
- **Bundling и публикация:** модуль `publish/bundle-publish.ts` — сборка ANS-104 bundle из одного Data Item, создание Arweave tx, теги Bundle-Format/Bundle-Version, подпись operator JWK (`arweave/compatible.ts` + `crypto/arweave-rsa-pss.ts`), отправка в Arweave; при успехе — postCallback; при ошибке — putStatus failed publish_failed.
- **Оркестрация в index.ts:** после валидации — putStatus queued_for_publish, ответ 200 { ack, status }; публикация и callback — в void async (ответ до завершения публикации).
- **Инфраструктура подписи:** `crypto/arweave-rsa-pss.ts` — signArweaveTransaction (RSA-PSS saltLength 32), transaction ID с префиксом "ar".

### Тесты

- `tests/arweave-rsa-pss.test.ts` — signArweaveTransaction (signature, transactionId начинается с "ar").
- `tests/publish-validate-token.test.ts` — verifyUploadToken: валидный токен, неверный upload_id, payload_size > max_bytes, истёкший токен.
- `tests/publish-validate-data-item.test.ts` — validateDataItem: валидный item с Upload-Id, неверный Upload-Id, невалидный base64.

### Документация и конфигурация

- **README (arweave-upload):** секция env/Secrets (UPLOAD_TOKEN_JWT_PUBLIC_KEY, BACKEND_URL, EDGE_TO_BACKEND_SECRET, ARWEAVE_PRIVATE_KEY_FILE), описание POST /edge/v1/publish.
- **Перманентная зона:** [supabase/docs/arweave-upload-publish-api.md](../../arweave-upload-publish-api.md) — API контракт, вызовы Backend, конфигурация.
- **IDE/TypeScript:** deno_shim.d.ts, deno_global.d.ts, tsconfig.json — резолв URL-импорта и глобала Deno при использовании TypeScript LSP.

---

## Не входит в таск

- Backend: таблица uploads, JWT RS256 выпуск, endpoints status/callback, Finalizer job — таск 3.2 (bot).
- Wallet: подпись Data Item, UI, отправка в Edge — отдельный таск.
- Сводный тест publish-flow.test.ts с моками Backend/Arweave (Phase 4.1) — опционально.
