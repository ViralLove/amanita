# Acceptance Verification: режим мока Backend в Edge Function

**Таск:** task-implement-edge-backend-mock-mode  
**Дата верификации:** 2026-01-29 (обновлено 2026-02-07 после доработки тестов)

---

## Соответствие AC

### Режим мока (P0)

| AC | Статус | Подтверждение |
|----|--------|----------------|
| Введена переменная `BACKEND_USE_MOCK`; `true`/`1` → не выполнять реальный fetch | ✅ | `backend-calls.ts`: `isBackendMockEnabled()` читает BACKEND_USE_MOCK; при true/1 в putStatus/postCallback ветка мока, fetch не вызывается. |
| При моке: putStatus/postCallback не вызывают fetch; логируют вызов и параметры; по умолчанию симуляция успеха | ✅ | Ветка мока: console.log с uploadId, status, (failureCode), simulatedStatus; return без ошибки. |
| При выключенном моке поведение без изменений (BACKEND_URL/EDGE_TO_BACKEND_SECRET → fetch; иначе warn + skip) | ✅ | При `!isBackendMockEnabled()` используется прежняя логика: проверка baseUrl/secret, fetch или warn. |

### Вариативность ответов мока (P0)

| AC | Статус | Подтверждение |
|----|--------|----------------|
| BACKEND_MOCK_PUT_STATUS и BACKEND_MOCK_CALLBACK = 200\|404\|409 (по умолчанию 200) | ✅ | `normalizeMockStatus()`: допустимы 200, 404, 409; иное/пусто → 200. Env читаются в putStatus/postCallback при моке. |
| При 200: лог + return без ошибки | ✅ | Реализовано в обеих функциях. |
| При 404/409: не fetch; логировать симулированный код; опционально throw | ✅ | Лог `[mock] putStatus/postCallback simulated 404|409`; throw не реализован (таск: «на первом шаге достаточно логирования»). |

### Переключение на лету (P0)

| AC | Статус | Подтверждение |
|----|--------|----------------|
| Per-request override через заголовки X-Backend-Mock-Put-Status, X-Backend-Mock-Callback (200\|404\|409) | ✅ | `index.ts`: при allowRequestOverride читаются заголовки, нормализация через normalizeMockStatus, передача в putStatus/postCallback. |
| Учёт заголовков только при моке и (BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true или X-Backend-Mock-Secret === BACKEND_MOCK_TEST_SECRET) | ✅ | allowRequestOverride = mockEnabled && (env ALLOW_REQUEST_OVERRIDE === "true" \|\| header Secret === BACKEND_MOCK_TEST_SECRET). |
| Обработчик publish читает заголовки, нормализует, передаёт в putStatus/postCallback; backend-calls принимает опциональный override | ✅ | requestMockOverride.putStatus/callback передаются во все вызовы; putStatus(..., requestMockOverride.putStatus), postCallback(..., requestMockOverride.callback). |

### Конфигурация и доки (P0)

| AC | Статус | Подтверждение |
|----|--------|----------------|
| publish-api: переменные BACKEND_USE_MOCK, BACKEND_MOCK_*, BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE, BACKEND_MOCK_TEST_SECRET; заголовки X-Backend-Mock-* | ✅ | Разд. 5 и 5.1 в arweave-upload-publish-api.md добавлены. |
| deploy-guide: подпункт «Режим мока Backend», переменные, переключение по env и на лету (заголовки, пример curl) | ✅ | Разд. 3.5 в arweave-upload-deploy-guide.md добавлен. |

### Тесты (P1)

| AC | Статус | Подтверждение |
|----|--------|----------------|
| Существующие тесты publish-flow проходят | ✅ | Запуск `deno test tests/ --allow-env`: **20 тестов** проходят (index.ts вызывает serve только при import.meta.main; при импорте из тестов serve не запускается). |
| При необходимости: сценарий проверки, что при BACKEND_USE_MOCK=true fetch не вызывается | ✅ | backend-mock.test.ts: тест «BACKEND_USE_MOCK=true → putStatus не вызывает fetch»; дополнительно тесты с перехватом лога проверяют simulatedStatus (200/404/409), неверный секрет → env, мок выключен → fetch вызывается. См. test-qualification-report.md. |

---

## Итог

Все критерии P0 и P1 выполнены. Тесты (20 шт.) проходят; доработка по test-improvements-plan.md закрыла пробелы квалификации (перехват лога, проверка секрета, явный тест «мок выключен»).

**Рекомендация:** перед мержем при необходимости выполнить ручную проверку по «Команды проверки» в таске (serve с BACKEND_USE_MOCK=true, вызов publish, проверка логов).
