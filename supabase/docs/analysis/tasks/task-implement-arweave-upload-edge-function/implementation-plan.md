# План реализации: Edge Function publish (user signs, operator pays)

**Таск:** [task-implement-arweave-upload-edge-function.md](../task-implement-arweave-upload-edge-function.md)  
**Дата:** 2026-01-29  
**Источники:** [solution-architecture.md](solution-architecture.md), [decision-points.md](decision-points.md).

**Правило:** не переходить к Этапу 5 (реализация по фазам), пока план не зафиксирован. Код — только по этому плану.

---

## Phase 0: Инфраструктура подписи (arweave-rsa-pss)

| Шаг | Файл | Место/действие | Критерий приёмки |
|-----|------|----------------|------------------|
| 0.1 | `supabase/functions/arweave-upload/crypto/arweave-rsa-pss.ts` | **Создать.** Экспорт: `signArweaveTransaction(privateKey: JsonWebKey, signatureData: Uint8Array): Promise<{ signature: Uint8Array; transactionId: string }>`. Внутри: importKey (RSA-PSS), crypto.subtle.sign({ name: "RSA-PSS", saltLength: 32 }), вычисление transaction ID по Arweave (base64url(sha256(owner \|\| signature))). Вспомогательные: extractOwnerFromJwk, computeTransactionId, base64UrlEncode. Референс: deno-webcrypto-rsassa-pss-analysis.md. | deno check crypto/arweave-rsa-pss.ts проходит; функция возвращает signature и transactionId, начинающийся с "ar". |
| 0.2 | `supabase/functions/arweave-upload/arweave/compatible.ts` | Без изменений (импорт из ../crypto/arweave-rsa-pss.ts уже указан). | deno check index.ts проходит; импорт compatible.ts не падает. |
| 0.3 | (опционально) `supabase/functions/arweave-upload/tests/arweave-rsa-pss.test.ts` | Unit-тест signArweaveTransaction с тестовым JWK и signatureData; проверка формата transactionId. | deno test tests/arweave-rsa-pss.test.ts проходит. |

**DoD Phase 0:** `deno check index.ts` успешен; при вызове upload-text (если есть ключ) или в тесте подпись выполняется.

---

## Phase 1: Маршрут, JWT RS256, Backend status

| Шаг | Файл | Место/действие | Критерий приёмки |
|-----|------|----------------|------------------|
| 1.1 | `supabase/functions/arweave-upload/index.ts` | После блока upload-file, перед 404: добавить ветку `if (path.endsWith('/edge/v1/publish') && req.method === 'POST')`. Внутри: `const body = await req.json()`. Проверка наличия полей: upload_token, upload_id, signed_data_item, payload_size (число). При отсутствии — return 400 JSON { code: '...', message: 'Missing required field' }. Не логировать body.signed_data_item. | POST /edge/v1/publish с пустым или неполным body → 400. |
| 1.2 | `supabase/functions/arweave-upload/publish/validate-token.ts` | **Создать.** Экспорт: `verifyUploadToken(token: string, uploadId: string, payloadSize: number): Promise<{ ok: true } | { ok: false; code: 'token_invalid' }>`. Внутри: чтение UPLOAD_TOKEN_JWT_PUBLIC_KEY из Deno.env; парсинг JWT (ручной или djwt); проверка подписи RS256 (Web Crypto importKey + verify); проверка exp (текущее время < exp); проверка payload JWT.upload_id === uploadId; проверка payloadSize <= JWT.max_bytes. При любой ошибке — { ok: false, code: 'token_invalid' }. | Unit-тест: валидный токен → ok: true; истёкший/неверная подпись/неверный upload_id/oversized → ok: false, code: token_invalid. |
| 1.3 | `supabase/functions/arweave-upload/publish/backend-calls.ts` | **Создать.** Экспорт: `putStatus(uploadId: string, status: string, failureCode?: string): Promise<void>`. Чтение BACKEND_URL, EDGE_TO_BACKEND_SECRET из Deno.env. fetch(BACKEND_URL + '/v1/uploads/' + uploadId + '/status', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + EDGE_TO_BACKEND_SECRET }, body: JSON.stringify(status === 'failed' ? { status, failure_code: failureCode } : { status }) }). Не бросать при сетевой ошибке — залогировать; при необходимости повтор или игнор по решению. | Тест с моком: putStatus вызывается с ожидаемыми аргументами. |
| 1.4 | `supabase/functions/arweave-upload/index.ts` | В ветке /edge/v1/publish: вызов verifyUploadToken(body.upload_token, body.upload_id, body.payload_size). При ok: false — return 401 (или 400) JSON { code: 'token_invalid' }, вызов putStatus(body.upload_id, 'failed', 'token_invalid'). При ok: true — вызов putStatus(body.upload_id, 'queued_for_publish'), return 200 JSON { ack: true, status: 'queued_for_publish' }. | Невалидный токен → 401/400 + code token_invalid + putStatus failed. Валидный токен → 200 + putStatus queued_for_publish. |
| 1.5 | `supabase/functions/arweave-upload/tests/publish-validate-token.test.ts` или в общем publish.test.ts | Тесты validate-token: мок публичного ключа, генерация тестовых JWT (валидный, истёкший, неверный upload_id, oversized). | deno test tests/publish*.test.ts — тесты JWT зелёные. |

**DoD Phase 1:** Роут /edge/v1/publish отвечает; валидный JWT → 200 и putStatus queued_for_publish; невалидный JWT → 4xx и putStatus failed. Backend вызывается с правильным телом и заголовком.

---

## Phase 2: Data Item, signature_invalid

| Шаг | Файл | Место/действие | Критерий приёмки |
|-----|------|----------------|------------------|
| 2.1 | `supabase/functions/arweave-upload/publish/validate-data-item.ts` | **Создать.** Экспорт: `validateDataItem(signedDataItemBase64: string, uploadId: string): Promise<{ ok: true; itemId?: string } | { ok: false; code: 'signature_invalid' }>`. Декодировать base64 → Uint8Array. Парсинг Data Item (ANS-104): минимально извлечь id (item_id), owner (публичный ключ), signature, данные для верификации подписи, теги. Проверка подписи: RSA-PSS verify с saltLength 32 по owner. Поиск тега Upload-Id, сравнение значения с uploadId. При несовпадении или невалидной подписи — { ok: false, code: 'signature_invalid' }. | Unit-тест: валидный item с тегом Upload-Id → ok: true; неверный тег или подпись → ok: false. |
| 2.2 | `supabase/functions/arweave-upload/index.ts` | После успешной проверки JWT: вызов validateDataItem(body.signed_data_item, body.upload_id). При ok: false — return 400 JSON { code: 'signature_invalid' }, putStatus(body.upload_id, 'failed', 'signature_invalid'). При ok: true — сохранить itemId для callback, перейти к следующему шагу (Phase 3). Пока Phase 3 не реализована — после ok: true оставить вызов putStatus queued и return 200 (публикация будет в Phase 3). | Невалидная подпись/тег → 400 signature_invalid + putStatus failed. |
| 2.3 | `supabase/functions/arweave-upload/tests/publish-validate-data-item.test.ts` | Тесты: мок Data Item (base64), валидный парсинг и тег; невалидная подпись; отсутствующий/неверный Upload-Id. | deno test — тесты Data Item зелёные. |

**DoD Phase 2:** После JWT выполняется проверка Data Item; при signature_invalid — 4xx и putStatus failed.

---

## Phase 3: Bundle, публикация, callback

| Шаг | Файл | Место/действие | Критерий приёмки |
|-----|------|----------------|------------------|
| 3.1 | `supabase/functions/arweave-upload/publish/bundle-publish.ts` | **Создать.** Экспорт: `bundleAndPublish(signedDataItemBytes: Uint8Array): Promise<{ bundleTxId: string } | { error: string }>`. Построить bundle (ANS-104) из одного Data Item: при отсутствии API в arweave SDK — минимальный builder по спецификации (заголовок bundle + один data item). Создать Arweave tx с data = bundleBytes; загрузить operator key (loadArweavePrivateKey из index или общий модуль); signTransaction(arweave, tx, operatorKey); arweave.transactions.post(tx). Вернуть bundle_tx_id или { error }. | Успешный путь с тестовым item и ключом → bundle_tx_id; при ошибке сети/Arweave → { error }. |
| 3.2 | `supabase/functions/arweave-upload/publish/backend-calls.ts` | Добавить: `postCallback(uploadId: string, itemId: string | undefined, bundleTxId: string, publishedAt: string): Promise<void>`. fetch(BACKEND_URL + '/v1/uploads/callback', { method: 'POST', headers: те же, body: JSON.stringify({ upload_id: uploadId, item_id: itemId, bundle_tx_id: bundleTxId, published_at: publishedAt }) }). | Тест с моком: postCallback вызывается с ожидаемыми полями. |
| 3.3 | `supabase/functions/arweave-upload/index.ts` | После успешной validateDataItem: декодировать body.signed_data_item в Uint8Array; вызов bundleAndPublish(bytes). При успехе — postCallback(body.upload_id, itemId, result.bundleTxId, new Date().toISOString()), затем putStatus(body.upload_id, 'queued_for_publish') если ещё не вызывали (или вызывали в Phase 1 — тогда порядок: сначала putStatus queued, затем bundleAndPublish, затем postCallback). При ошибке bundleAndPublish — putStatus(body.upload_id, 'failed', 'publish_failed'), return 502/503 JSON { code: 'publish_failed' }. | Успех публикации → postCallback вызван; ошибка публикации → putStatus failed + 4xx publish_failed. |
| 3.4 | Порядок вызовов в index | Уточнить: (1) validate token; (2) validate Data Item; (3) putStatus(queued_for_publish); (4) bundleAndPublish(); (5) при успехе postCallback(); при ошибке (4) putStatus(failed, publish_failed). Ответ 200 отдавать после (3), не дожидаясь (4)–(5) (по контракту «не ждать публикации синхронно»). | Ответ 200 { ack, status } сразу после putStatus queued; публикация и callback — асинхронно (или в том же handler после ответа — уточнить по контракту: «Response (сразу): ack, status» — значит ответ до публикации). |

**DoD Phase 3:** После валидации выполняется bundleAndPublish; при успехе — postCallback; при ошибке — putStatus publish_failed и 4xx. Ответ 200 отдаётся по контракту сразу после приёма (queued_for_publish), публикация может идти после ответа.

---

## Phase 4: Тесты и безопасность

| Шаг | Файл | Место/действие | Критерий приёмки |
|-----|------|----------------|------------------|
| 4.1 | `supabase/functions/arweave-upload/tests/publish-flow.test.ts` | Сводные тесты с моками: (1) невалидный токен → 401/400, код token_invalid, мок Backend получил putStatus failed; (2) невалидный Data Item → 400, код signature_invalid, мок Backend получил putStatus failed; (3) валидный токен + валидный item + мок Arweave успех → 200, мок Backend получил putStatus queued и postCallback; (4) валидный токен + item + мок Arweave ошибка → 502/503, код publish_failed, мок Backend получил putStatus failed. | deno test tests/ — все сценарии зелёные. |
| 4.2 | `index.ts`, модули publish/ | Логи: "[publish] request received", "[publish] token ok" / "token invalid", "[publish] data item ok" / "data item invalid", "[publish] status updated", "[publish] publish ok" / "publish failed", "[publish] callback sent". Не логировать: body.signed_data_item, upload_token, секреты, ключи. | Ручная проверка; в тестах не проверять содержимое логов. |
| 4.3 | `supabase/functions/arweave-upload/README.md` или таск-док | Секция env/Secrets: UPLOAD_TOKEN_JWT_PUBLIC_KEY, BACKEND_URL, EDGE_TO_BACKEND_SECRET, ARWEAVE_PRIVATE_KEY_FILE. | Документация есть. |

**DoD Phase 4:** Все тесты проходят; логирование и конфигурация соответствуют P1.

---

## Проверка после каждой фазы

- **Phase 0:** `deno check index.ts`; при необходимости `deno test tests/arweave-rsa-pss.test.ts`.
- **Phase 1:** `deno test tests/publish*.test.ts` (JWT и маршрут); локально POST /edge/v1/publish с мок-телом.
- **Phase 2:** тесты validate-data-item; интеграция в index.
- **Phase 3:** тесты с моком Arweave и Backend; при наличии ключа — один ручной прогон до Arweave (опционально).
- **Phase 4:** `deno test tests/` — полный прогон.

---

## Итог плана реализации

- Phase 0: 1 новый файл (arweave-rsa-pss.ts), опционально тест.
- Phase 1: index.ts (ветка publish), publish/validate-token.ts, publish/backend-calls.ts, тесты.
- Phase 2: publish/validate-data-item.ts, интеграция в index, тесты.
- Phase 3: publish/bundle-publish.ts, postCallback в backend-calls, интеграция в index, тесты.
- Phase 4: сводные тесты, логирование, README/env-док.

**Следующий шаг:** Этап 5 — реализация по фазам (код по этому плану). Выполнять Phase 0 → 1 → 2 → 3 → 4 по порядку; после каждой фазы — проверка и чекпоинт для оператора.
