# Uploader ↔ Node (bot): авторизация и переменные окружения (референс)

**Версия:** 1.1  
**Статус:** референс по готовой системе  
**Таск:** [task-tests-phase3-full-cycle-real-db-real-arweave-uploader](../analysis/tasks/task-tests-phase3-full-cycle-real-db-real-arweave-uploader.md)

Документ описывает, как устроена авторизация между arweave-uploader и bot (нода) и какие переменные окружения используются. Целевые имена — OWN_AUTH_TOKEN, NODE_*, ARWEAVE_*; старые (EDGE_TO_BACKEND_SECRET, UPLOADER_TO_BACKEND_SECRET, BACKEND_*) в коде не используются.

---

## 1. Правило именования

- У каждого сервиса в своём .env есть **OWN_AUTH_TOKEN** — **свой** токен (для приёма входящих вызовов).
- Токен **другого** сервиса задаётся префиксом по имени того сервиса: в bot — **ARWEAVE_*** (вызовы к uploader), в uploader — **NODE_*** (вызовы к bot). Значения не путать.

---

## 2. Где что реализовано

### 2.1 Bot (приём putStatus / callback)


| Файл                                                     | Реализация                                                                                                                                                                                          |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bot/api/routes/uploads.py`                              | Секрет для проверки Bearer читается только из `OWN_AUTH_TOKEN` (`_get_own_auth_token()`). Входящий заголовок `Authorization: Bearer <token>` сравнивается с этим значением; при несовпадении — 401. |
| `bot/tests/integration/test_upload_floou_integration.py` | Секрет для заголовка тестов — `OWN_AUTH` из `OWN_AUTH_TOKEN` (или `mock-own-auth-token`).                                                                                                           |
| `bot/tests/integration/upload_harness.py`                | Фикстура `upload_integration_own_auth`: выставляет/читает `OWN_AUTH_TOKEN` (то же значение, что проверяет uploads.py).                                                                              |
| `bot/tests/unit/test_upload_flow_api.py`                 | В тестах выставляется `OWN_AUTH_TOKEN` (то же значение, что ожидает uploads.py).                                                                                                                    |
| `bot/tests/api/test_uploads_mock_curl.sh`                | Bearer берётся из `OWN_AUTH_TOKEN` (или `mock-own-auth-token`).                                                                                                                                     |


### 2.2 arweave-uploader (вызовы к ноде)


| Файл                                             | Реализация                                                                                                                                                                     |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `arweave-uploader/dist/publish/backend-calls.js` | URL ноды — только `NODE_URL`. Секрет для Bearer при вызове ноды — только `NODE_AUTH_TOKEN`. Включение мока вызовов к ноде — только `NODE_MOCK` (true/1 → заглушка, без fetch). |
| `arweave-uploader/dist/server.js`                | Флаг мока вызовов к ноде — только `NODE_MOCK` (`isNodeMockEnabled()`).                                                                                                         |
| `arweave-uploader/.env.example`                  | Описаны OWN_AUTH_TOKEN, NODE_URL, NODE_AUTH_TOKEN, NODE_MOCK; явно указано: NODE_AUTH_TOKEN = значение OWN_AUTH_TOKEN в bot.                                                   |


### 2.3 Документация таска

- В папке таска (implementation-plan, decision-points, vision-env-and-exact-solution, env-backend-and-secret) целевые имена — только OWN_AUTH_TOKEN, NODE_*, ARWEAVE_*.

---

## 3. Переменные окружения (сводка)

**bot/.env**


| Переменная          | Назначение                                                                                         |
| ------------------- | -------------------------------------------------------------------------------------------------- |
| OWN_AUTH_TOKEN      | Свой токен bot'а; по нему проверяется Bearer при приёме putStatus/callback от uploader.            |
| ARWEAVE_SERVICE_URL | URL arweave-uploader (для клиента/тестов: POST /v1/crystalize).                                    |
| ARWEAVE_AUTH_TOKEN  | Токен для исходящих вызовов bot → arweave-uploader; то же значение, что OWN_AUTH_TOKEN в uploader. |


**arweave-uploader/.env**


| Переменная      | Назначение                                                                  |
| --------------- | --------------------------------------------------------------------------- |
| OWN_AUTH_TOKEN  | Свой токен uploader'а (при приёме входящих вызовов).                        |
| NODE_AUTH_TOKEN | Токен для вызовов uploader → bot; то же значение, что OWN_AUTH_TOKEN в bot. |
| NODE_URL        | URL ноды (bot), куда uploader шлёт putStatus и postCallback.                |
| NODE_MOCK       | true/1 — не выполнять реальный HTTP к ноде (заглушка).                      |


**Связь (не перепутать):** NODE_AUTH_TOKEN (uploader) = OWN_AUTH_TOKEN (bot). ARWEAVE_AUTH_TOKEN (bot) = OWN_AUTH_TOKEN (uploader).

---

## 4. Проверка по критериям приёмки (AC)

Соответствие таску task-tests-phase3-full-cycle-real-db-real-arweave-uploader и подзадаче «env и авторизация uploader ↔ node».

### 4.1 Секрет и Bearer (env)


| Критерий                                                                                                           | Статус | Как проверено                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Bot читает секрет для Bearer только из OWN_AUTH_TOKEN                                                              | ✅      | Код: uploads.py — `_get_own_auth_token()` → `os.environ.get("OWN_AUTH_TOKEN")`.                                                      |
| Тесты bot (integration + unit) используют OWN_AUTH_TOKEN для заголовка                                             | ✅      | test_upload_floou_integration.py — OWN_AUTH; upload_harness — upload_integration_own_auth; test_upload_flow_api.py — OWN_AUTH_TOKEN. |
| arweave-uploader использует только NODE_URL, NODE_AUTH_TOKEN, NODE_MOCK для вызовов к ноде                         | ✅      | backend-calls.js, server.js — только NODE_*.                                                                                         |
| .env.example uploader документирует OWN_AUTH_TOKEN, NODE_*, NODE_MOCK и связь NODE_AUTH_TOKEN = OWN_AUTH_TOKEN bot | ✅      | arweave-uploader/.env.example — секция «Node (Backend)».                                                                             |
| В целевой документации таска нет EDGE_TO_BACKEND_SECRET, UPLOADER_TO_BACKEND_SECRET, BACKEND_* как основных имён   | ✅      | Grep по папке таска — совпадений нет.                                                                                                |


### 4.2 Прогон тестов


| Проверка                                                               | Результат                                                                                                      |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Unit-тесты upload API (`pytest tests/unit/test_upload_flow_api.py -v`) | 6 passed (OWN_AUTH_TOKEN выставляется в фикстуре).                                                             |
| Интеграционные тесты upload floou                                      | Требуют SUPABASE_URL и ключи; при отсутствии — падение по сети, не по секрету. Логика Bearer — через OWN_AUTH. |
| Скрипт test_uploads_mock_curl.sh                                       | Использует OWN_AUTH_TOKEN; при запуске с поднятым API и OWN_AUTH_TOKEN в env — ожидаемые 200/401/422.          |


### 4.3 Связь с полным AC таска

Полный цикл (prepare → crystalize → putStatus/callback → published) и замена терминологии Edge → uploader описаны в самом таске и в implementation-plan. Данный документ покрывает подмножество AC, относящееся к **env и авторизации** (OWN_AUTH_TOKEN, NODE_*, ARWEAVE_*). Остальные пункты AC (тест полного цикла с real_arweave_uploader, пометка legacy Edge теста, эпик) — в объёме таска и плана по фазам.

---

## 5. Ссылки

- Модель токенов и таблица «ничего не перепутать»: [vision-env-and-exact-solution.md](../analysis/tasks/task-tests-phase3-full-cycle-real-db-real-arweave-uploader/vision-env-and-exact-solution.md).
- Краткая сводка env: [env-backend-and-secret.md](../analysis/tasks/task-tests-phase3-full-cycle-real-db-real-arweave-uploader/env-backend-and-secret.md).
- План по фазам: [implementation-plan-phase3-full-cycle-real-uploader.md](../analysis/tasks/task-tests-phase3-full-cycle-real-db-real-arweave-uploader/implementation-plan-phase3-full-cycle-real-uploader.md).

