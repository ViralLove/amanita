# Локальный запуск без Docker и smoke

Запуск сервера и smoke-теста crystalize на машине разработчика (без Docker и без деплоя) для быстрой проверки потока JWT и crystalize.

## 1. Запуск сервера локально

Из корня **arweave-uploader**:

```bash
npm start
```

Сервер подхватывает `.env` из текущей директории (если файл есть). Порт по умолчанию — 3000.

**Обязательно для POST /v1/crystalize:** публичный ключ JWT. Задайте **один** из вариантов в `.env`:

- **Путь к файлу (удобно локально):**
  ```bash
  UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE=../keys/amanita_111444555888555444111_public.pem
  ```
- **Либо значение в переменной:** лучше одна строка с `\n` или многострочно без пустых строк между строками ключа:
  ```bash
  UPLOAD_TOKEN_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIB...\n-----END PUBLIC KEY-----"
  ```

Остальное для минимального crystalize:

- `ARWEAVE_PRIVATE_KEY_FILE` или `ARWEAVE_PRIVATE_KEY` — нужны для старта (можно тестовый JWK).
- `USE_REAL_ARWEAVE=false` — мок публикации (сервер не ходит в Arweave, возвращает 200 с mock `bundle_tx_id`).
- Backend (PUT status, callback) при отсутствии только логирует предупреждение.

## 2. Smoke crystalize против локального сервера

В **втором** терминале, из корня arweave-uploader:

1. В `.env` задать:
   - **Куда стучаться:** `DEPLOYED_URL=http://localhost:3000`
   - **Приватный ключ** (из той же пары, что и публичный на сервере):
     ```bash
     SMOKE_JWT_PRIVATE_KEY_FILE=../keys/amanita_111444555888555444111_private.pem
     ```

2. Запустить smoke:
   ```bash
   ./scripts/smoke-real-crystalize.js
   ```

Скрипт сам читает `.env`, логирует URL, `uploadId`, источник ключа и при 401 выводит подсказку (пара ключей, локальный тест).

## 3. Идентификация сбоя 401 token_invalid

- **В логах сервера** при 401 теперь есть поле **`reason`** в событии `publish.token_invalid`:
  - `no_public_key` — не задан или не прочитан публичный ключ (нет `UPLOAD_TOKEN_JWT_PUBLIC_KEY` / `UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE` или ошибка чтения/парсинга).
  - `token_empty` — токен не передан или пустой.
  - `token_not_three_parts` — не JWT (нет трёх частей через точку).
  - `payload_decode_failed` — не удалось декодировать payload (base64/JSON).
  - `exp_expired` — истёк срок действия токена.
  - `upload_id_mismatch` — `upload_id` в токене не совпадает с телом запроса.
  - `payload_size_exceeded` — размер payload больше `max_bytes` из токена.
  - `signature_invalid` — подпись JWT не совпадает (разные ключи или повреждённый токен).

- **В smoke** в консоль выводится: `url`, `uploadId`, `tokenLength`, `keySource`. При 401 — текст ответа и подсказка про пару ключей и `DEPLOYED_URL=http://localhost:3000`.

Сначала проверяйте локально с `DEPLOYED_URL=http://localhost:3000` и одной парой ключей в `.env` (публичный на сервере, приватный в smoke), затем переносите тест на деплой.

Если сервер с **USE_REAL_ARWEAVE=false** (мок), tx в Arweave не загружается — проверка GET даст 404. Задайте **SMOKE_SKIP_ARWEAVE_VERIFY=1** в `.env` smoke, чтобы пропустить шаг проверки и не падать по ожидаемой 404.
