# Архитектура решения: режим мока Backend в Edge Function

**Таск:** task-implement-edge-backend-mock-mode  
**Контекст:** supabase/functions/arweave-upload

---

## Цель

Режим мока Backend управляется env; симулированный ответ (200/404/409) — env или per-request заголовки. Без fetch к Backend при включённом моке.

## Компоненты


| Компонент          | Роль                                                                                                                                                                    |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend-calls.ts` | putStatus / postCallback: проверка BACKEND_USE_MOCK; при моке — источник кода из override-аргумента или env; лог; при 404/409 — лог симуляции (без throw по умолчанию). |
| `index.ts`         | Обработчик publish: при разрешённом override читает X-Backend-Mock-Put-Status, X-Backend-Mock-Callback; передаёт значения в putStatus/postCallback.                     |
| Env / Secrets      | BACKEND_USE_MOCK, BACKEND_MOCK_PUT_STATUS, BACKEND_MOCK_CALLBACK, BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE, BACKEND_MOCK_TEST_SECRET.                                        |


## Источник симулированного кода

1. Если передан аргумент override (number) в putStatus/postCallback — использовать его (per-request).
2. Иначе при моке — env BACKEND_MOCK_PUT_STATUS / BACKEND_MOCK_CALLBACK.
3. Нормализация: допустимы 200, 404, 409; иное или пусто → 200.

## Условие учёта заголовков переопределения

Override по запросу учитывается только если:

- BACKEND_USE_MOCK включён, **и**
- BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true **или** заголовок X-Backend-Mock-Secret совпадает с BACKEND_MOCK_TEST_SECRET.

Иначе заголовки X-Backend-Mock-Put-Status / X-Backend-Mock-Callback игнорируются.

## Фазы реализации

- **Phase 0:** backend-calls.ts — чтение BACKEND_USE_MOCK, опциональный аргумент mockOverride, ветвление мок/реальный fetch, нормализация 200|404|409.
- **Phase 1:** index.ts — чтение заголовков при разрешённом override, передача override в putStatus/postCallback.
- **Phase 2:** Документация (arweave-upload-publish-api.md, arweave-upload-deploy-guide.md).
- **Phase 3:** Прогон тестов, верификация по AC.

