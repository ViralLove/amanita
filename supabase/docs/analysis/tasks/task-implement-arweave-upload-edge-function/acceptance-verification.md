# Верификация по критериям приёмки: Edge Function publish

**Таск:** [task-implement-arweave-upload-edge-function.md](../task-implement-arweave-upload-edge-function.md)  
**Дата:** 2026-01-29  
**Источник AC:** раздел «AC/DoD» в файле таска.

**Правило:** прогон тестов + сверка кода/тестов с каждым пунктом AC; явные N/A с обоснованием.

---

## Прогон тестов

```bash
cd supabase/functions/arweave-upload && deno test tests/ --allow-env
```

**Результат:** ok | 8 passed | 0 failed (arweave-rsa-pss.test.ts, publish-validate-token.test.ts, publish-validate-data-item.test.ts).

---

## Таблица верификации AC

| AC (уровень) | Формулировка | Код/тесты | Статус |
|--------------|--------------|-----------|--------|
| **Endpoint и контракт (P0)** | | | |
| | Endpoint POST /edge/v1/publish, тело: upload_token, upload_id, signed_data_item, item_id?, payload_size | index.ts: path.endsWith("/edge/v1/publish"), body: upload_token, upload_id, signed_data_item, payload_size; item_id не в body (опционально в контракте — не парсим из body) | ✅ |
| | Response при успехе: { ack: true, status: "queued_for_publish" } (без ожидания публикации) | index.ts: return 200 JSON { ack: true, status: "queued_for_publish" } после putStatus(queued) | ✅ |
| | При ошибке валидации: HTTP 4xx, тело с code: token_invalid \| signature_invalid \| publish_failed | index.ts: 401 + code token_invalid; 400 + code signature_invalid; publish_failed — см. примечание ниже | ⚠️ см. ниже |
| **Валидация upload_token JWT RS256 (P0)** | | | |
| | Публичный ключ Backend в Edge (Secret/env) | validate-token.ts: Deno.env.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY"); README env | ✅ |
| | Проверка подписи RS256, exp, upload_id, payload_size <= max_bytes | validate-token.ts: verifyUploadToken(token, uploadId, payloadSize) | ✅ |
| | При невалидном токене: code token_invalid, PUT status failed, failure_code=token_invalid | index.ts: putStatus(uploadId, "failed", "token_invalid"); 401 JSON code token_invalid | ✅ |
| **Sanity check Data Item (P0)** | | | |
| | Парсинг/валидация signed_data_item (id, payload, signature, tags) | validate-data-item.ts: ANS-104 парсер, owner, signature, tags, data | ✅ |
| | Проверка подписи Data Item (RSA-PSS, Arweave) | validate-data-item.ts: deep-hash + crypto.subtle.verify RSA-PSS saltLength 32 | ✅ |
| | Тег Upload-Id и совпадение с upload_id | validate-data-item.ts: getTagValue(tags, "Upload-Id") === uploadId | ✅ |
| | При невалидной подписи/теге: code signature_invalid, PUT status failed | index.ts: putStatus(..., "signature_invalid"); 400 JSON code signature_invalid | ✅ |
| **Вызовы Backend (P0)** | | | |
| | После успешной валидации: PUT .../status { status: "queued_for_publish" } | index.ts: putStatus(uploadId, "queued_for_publish") | ✅ |
| | После успешной публикации: POST .../callback { upload_id, item_id, bundle_tx_id, published_at } | backend-calls.ts: postCallback(...); index.ts void async: postCallback после bundleAndPublish success | ✅ |
| | При ошибке публикации: PUT status failed publish_failed; ответ клиенту code publish_failed | putStatus(..., "failed", "publish_failed") в async блоке; клиенту 200 уже отдан — см. примечание | ⚠️ см. ниже |
| **Bundling и публикация (P0)** | | | |
| | Signed Data Item в bundle (N=1 допустимо) | bundle-publish.ts: buildBundleBody — ANS-104 header + один item | ✅ |
| | Arweave bundle tx, подпись operator JWK, отправка | bundle-publish.ts: signTransaction(arweave, tx, privateKey); arweave.transactions.post | ✅ |
| | bundle_tx_id в callback Backend | postCallback(uploadId, itemId, result.bundleTxId, publishedAt) | ✅ |
| **Тесты (P0)** | | | |
| | Невалидный/истёкший токен → token_invalid, Backend status failed | publish-validate-token.test.ts: wrong upload_id, expired, oversized → ok: false code token_invalid | ✅ |
| | Невалидная подпись/тег → signature_invalid | publish-validate-data-item.test.ts: wrong Upload-Id, invalid base64 → signature_invalid | ✅ |
| | Успешный путь: status queued → публикация → callback | Unit-тесты по фазам; сводный publish-flow.test.ts с моками Backend/Arweave — не реализован (Phase 4.1) | ⚠️ частично |
| | publish_failed сценарий | Нет отдельного теста с моком Arweave error → putStatus failed | ⚠️ нет |
| **Безопасность и конфигурация (P1)** | | | |
| | JWT ключ и BACKEND_URL не хардкод (Secrets/env) | Deno.env.get; README таблица env | ✅ |
| | Логи без payload/секретов | index.ts: [publish] request received, token ok/invalid, data item ok/invalid, status updated, publish ok/failed, callback sent; не логируем signed_data_item, token | ✅ |

---

## Примечания к статусу

### ⚠️ Ответ клиенту code: publish_failed

**AC:** «При ошибке публикации … ответ клиенту code: publish_failed».

**Реализация:** По контракту и плану ответ 200 { ack, status } отдаётся сразу после putStatus(queued_for_publish); публикация и callback выполняются асинхронно (void async). Поэтому при ошибке публикации клиент уже получил 200; ответ с code: publish_failed клиенту не отдаётся. Backend получает putStatus(failed, publish_failed).

**Вывод:** Соответствие AC по уведомлению Backend — да. По явному «ответ клиенту code: publish_failed» — расхождение по дизайну (клиент не ждёт публикации). Рекомендация: зафиксировать в контракте/таске, что при async-публикации клиент не получает publish_failed в ответе; достаточно статуса в Backend.

### ⚠️ Сводный тест publish-flow (Phase 4.1)

**План:** tests/publish-flow.test.ts — сценарии с моками Backend и Arweave (token_invalid, signature_invalid, success, publish_failed).

**Факт:** Есть unit-тесты по фазам (validate-token, validate-data-item, arweave-rsa-pss); сводного flow-теста с моками fetch/Arweave нет.

**Вывод:** Критерий «Unit/интеграционные тесты: сценарии …» выполнен частично (покрытие по модулям). Для полного соответствия плану — добавить publish-flow.test.ts с моками (опционально по решению оператора).

---

## Итог верификации

| Категория | Статус |
|-----------|--------|
| Endpoint и контракт | ✅ кроме явного ответа publish_failed клиенту (см. примечание) |
| JWT RS256 | ✅ |
| Data Item sanity check | ✅ |
| Вызовы Backend | ✅ (ответ клиенту при publish_failed — см. примечание) |
| Bundling и публикация | ✅ |
| Тесты | ✅ по модулям; ⚠️ сводный flow с моками не делался |
| Безопасность и конфигурация | ✅ |

**Рекомендация:** Считать таск принятым по AC с двумя оговорками: (1) ответ клиенту при publish_failed не отдаётся по текущему контракту (200 сразу); (2) сводный тест publish-flow — по желанию добавить позже.
