# Этап 2: Решения до кода (decision-points)

**Таск:** [task-implement-arweave-upload-edge-function.md](../task-implement-arweave-upload-edge-function.md)  
**Дата:** 2026-01-29  
**Цель:** зафиксировать решения перед реализацией; согласование с оператором при необходимости.

---

## 1. JWT RS256 — публичный ключ в Edge

**Вопрос:** откуда Edge берёт публичный ключ Backend для верификации upload_token?

**Варианты:**
- A: Supabase Secret (например `UPLOAD_TOKEN_JWT_PUBLIC_KEY`) — PEM или JWK в виде строки.
- B: Env-переменная с тем же именем (для локальной разработки).

**Решение:** A + B — читать из `Deno.env.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY")`; в production значение задаётся через Supabase Secrets. Формат: PEM (начало с `-----BEGIN PUBLIC KEY-----`) или JWK (JSON string). Реализация должна поддерживать оба формата или только PEM на первом шаге (PEM проще для PyJWT на Backend).

**Статус:** принято по референсу Arweave data upload.md разд. 4.2 (вариант B RS256).

---

## 2. Авторизация Edge → Backend

**Вопрос:** как Edge авторизуется при вызовах PUT .../status и POST .../callback?

**Варианты:**
- A: Заголовок `Authorization: Bearer <secret>`, секрет общий у Backend и Edge (Supabase Secret `EDGE_TO_BACKEND_SECRET`).
- B: Кастомный заголовок `X-Edge-Secret` с тем же секретом.
- C: Подпись запроса (сложнее, отложить).

**Решение:** A — `Authorization: Bearer ${EDGE_TO_BACKEND_SECRET}`. Backend (таск 3.2) проверяет заголовок. Секрет в Edge — Supabase Secret `EDGE_TO_BACKEND_SECRET`; URL Backend — `BACKEND_URL` (env/Secret). Контракт с bot: при реализации таска 3.2 использовать тот же механизм.

**Статус:** принято для MVP; при реализации таска 3.2 (bot) согласовать имя секрета и заголовок.

---

## 3. Формат signed_data_item (serialized)

**Вопрос:** в каком виде Wallet присылает signed_data_item в теле запроса?

**Варианты:**
- A: Base64-строка бинарного Data Item (ANS-104).
- B: JSON-объект с полями (id, signature, tags, payload base64).
- C: Raw binary (тогда Content-Type отдельный, реже для JSON body).

**Решение:** A — принять в теле JSON поле `signed_data_item` как **base64-строку** бинарного Data Item (ANS-104). Edge декодирует base64 → Uint8Array, парсит по спецификации ANS-104 (или Arweave Data Item), проверяет подпись и тег Upload-Id. Если Wallet позже примет другой формат — расширить парсер; контракт с Wallet зафиксировать в Arweave data upload.md или в API-спеке Backend.

**Статус:** принято для MVP. При появлении Wallet-таска — явно согласовать в контракте.

---

## 4. Подпись bundle tx оператором (arweave-rsa-pss vs pss_wasm)

**Вопрос:** чем подписывать bundle-транзакцию Arweave в Edge? Сейчас `arweave/compatible.ts` импортирует `../crypto/arweave-rsa-pss.ts`, файл отсутствует; в `crypto/` есть только `pss_wasm.ts` (пустой) и `pss.wasm`.

**Варианты:**
- A: Реализовать `crypto/arweave-rsa-pss.ts` на Web Crypto API (RSASSA-PSS, saltLength 32) — как в старой постановке таска; compatible.ts продолжит использовать его для подписи транзакций (в т.ч. bundle tx).
- B: Переключить compatible.ts на использование pss_wasm; доработать pss_wasm для подписи Arweave tx.
- C: Использовать Arweave SDK встроенную подпись, если SDK умеет подписывать с переданным JWK (без файла).

**Решение:** A — добавить модуль `crypto/arweave-rsa-pss.ts` с реализацией на Web Crypto API (RSASSA-PSS, saltLength 32, вычисление transaction ID по Arweave). Это разблокирует текущие `/upload-text` и `/upload-file` и даёт единый путь подписи для bundle tx в потоке publish. Файл `pss_wasm.ts` пустой; не полагаться на него в рамках данного таска.

**Статус:** принято; реализация по референсу deno-webcrypto-rsassa-pss-analysis.md и старой постановке таска (Web Crypto API).

---

## 5. Публикация при N=1 (один Data Item)

**Вопрос:** как публиковать один принятый Data Item — как bundle из одного элемента или как одну «обычную» Arweave tx?

**Варианты:**
- A: Собрать ANS-104 bundle из одного Data Item, создать одну Arweave bundle-транзакцию, подписать её оператором, отправить в сеть.
- B: Отправить данные как одну data-транзакцию (без формата bundle), подписанную оператором — тогда это не «bundle», а один tx с payload = данные item (контракт с Arweave может отличаться).

**Решение:** A — для соответствия диаграмме и контракту (bundle_tx_id, «Build bundle_bytes from queued signed data items») использовать формат **bundle (ANS-104)** даже при одном item. Один item = bundle из одного элемента. Arweave SDK (arweave@1.15.7) или отдельная сборка по спецификации ANS-104; при отсутствии готового API в SDK — минимальная сборка bundle bytes по спецификации и создание tx(data=bundle_bytes), подпись через compatible.ts.

**Статус:** принято по референсу Arweave data upload.md разд. 10. При реализации проверить наличие bundle API в arweave npm; при необходимости добавить минимальный bundle builder.

---

## 6. Имена env/Secrets (сводка)

| Имя | Назначение | Где задаётся |
|-----|------------|--------------|
| `UPLOAD_TOKEN_JWT_PUBLIC_KEY` | Публичный ключ Backend (PEM или JWK) для проверки JWT RS256 | Supabase Secrets / env |
| `BACKEND_URL` | Базовый URL Backend для PUT .../status и POST .../callback | Supabase Secrets / env |
| `EDGE_TO_BACKEND_SECRET` | Секрет для заголовка Authorization при вызовах Backend | Supabase Secrets |
| `ARWEAVE_PRIVATE_KEY_FILE` | Путь к файлу с operator JWK (уже используется) | Существует |

**Статус:** принято для реализации.

---

## 7. Итог этапа 2

- Решения 1–6 зафиксированы; при необходимости оператор может скорректировать (формат signed_data_item, имена секретов, выбор A/B для п.4).
- Готовность к Этапу 3: архитектура решения (solution-architecture) с учётом этих решений.

**Следующий шаг:** Этап 3 — solution-architecture (фазы, шаги, артефакты).
