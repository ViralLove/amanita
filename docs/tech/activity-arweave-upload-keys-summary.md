# Публичный и приватный ключ в потоке загрузки в Arweave (справка и инструкции)

**Назначение:** как организованы ключи, зачем они нужны, как их генерировать и в какие переменные окружения добавлять в архитектуре **Backend (bot) ↔ arweave-uploader (Node.js микросервис) ↔ Arweave**.

**Актуальная архитектура:** вместо Supabase Edge Function используется микросервис **arweave-uploader** (Node.js), т.к. подключение к Arweave в Edge не работало как нужно. Поток: Backend выдаёт JWT `upload_token` и вызывает arweave-uploader; микросервис проверяет JWT, валидирует Data Item, подписывает bundle-транзакцию ключом оператора и отправляет в Arweave.

---

## 1. Два независимых слоя ключей

| Слой | Кто подписывает | Кто проверяет | Где что хранится |
|------|------------------|---------------|-------------------|
| **JWT upload_token** | Backend (приватный RSA) | arweave-uploader (публичный RSA Backend) | Приватный ключ **только в Backend**. В arweave-uploader — только **публичный** (`UPLOAD_TOKEN_JWT_PUBLIC_KEY`). |
| **Data Item** | Пользователь (свой Arweave JWK в Wallet) | arweave-uploader (публичный ключ из поля **owner** Data Item) | Ключей пользователя в микросервисе **нет**; проверка по owner из item. |
| **Bundle-транзакция Arweave** | arweave-uploader (оператор) | Сеть Arweave | В arweave-uploader хранится **приватный ключ оператора** (`ARWEAVE_PRIVATE_KEY` / `ARWEAVE_PRIVATE_KEY_FILE`) — только для подписи bundle tx и оплаты. |

Итог: arweave-uploader хранит (1) **публичный** ключ Backend для JWT, (2) **приватный** ключ оператора Arweave для bundle tx. Ключей пользователей в микросервисе нет.

---

## 2. Подробные инструкции: генерация ключей и переменные окружения

### 2.1 Пара JWT (Backend ↔ arweave-uploader)

Одна RSA-пара: Backend подписывает JWT, arweave-uploader проверяет подпись. Генерируем один раз.

#### Где находиться при генерации

- Можно в **любой** рабочей директории (ключи не привязаны к репо). Удобно: отдельная папка для секретов (например `./keys` в корне репозитория, добавлена в `.gitignore`) или домашний каталог.

#### Шаг 1: Сгенерировать приватный ключ (PEM, 2048 бит)

```bash
# Создать папку для ключей (опционально) и перейти в неё
mkdir -p keys
cd keys

# Приватный ключ (PEM)
openssl genrsa -out upload_token_private.pem 2048
```

**Результат:** файл `upload_token_private.pem`. Не коммитить, не отдавать в arweave-uploader.

#### Шаг 2: Извлечь публичный ключ (PEM)

```bash
# В той же папке (keys или где лежит upload_token_private.pem)
openssl rsa -in upload_token_private.pem -pubout -out upload_token_public.pem
```

**Результат:** файл `upload_token_public.pem`. Его содержимое нужно передать в arweave-uploader.

#### Шаг 3: Переменные окружения — Backend (bot)

Рабочая директория для запуска Backend: **корень проекта bot** (`bot/`).

| Переменная | Что подставить | Обязательность |
|------------|----------------|----------------|
| `UPLOAD_TOKEN_JWT_PRIVATE_KEY` | Строка PEM **приватного** ключа целиком (переносы строк можно как `\n`) | Одна из двух: либо эта переменная, либо файл ниже |
| `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE` | **Путь** к файлу с PEM приватного ключа, например `../keys/upload_token_private.pem` или абсолютный путь | Одна из двух: либо переменная выше, либо эта |

**Пример в `.env` (bot):**

```bash
# Вариант 1: путь к файлу (удобно, если keys/ рядом с bot/)
UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE=../keys/upload_token_private.pem

# Вариант 2: PEM строкой (одна строка с \n)
# UPLOAD_TOKEN_JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
```

Код Backend: `bot/services/upload/jwt_upload_token.py` — читает ключ из env или файла при вызове `sign_upload_token()` (prepare).

#### Шаг 4: Переменные окружения — arweave-uploader

Рабочая директория для запуска микросервиса: **корень проекта arweave-uploader** (`arweave-uploader/`).

| Переменная | Что подставить | Обязательность |
|------------|----------------|----------------|
| `UPLOAD_TOKEN_JWT_PUBLIC_KEY` | Содержимое файла **публичного** ключа (PEM) — целиком, либо одна строка JSON JWK | Обязательна для приёма crystalize (проверка JWT) |

**Как подставить PEM в `.env` (arweave-uploader):**

В `.env` **нельзя** писать PEM с реальными переносами строк: парсеры (dotenv и др.) воспринимают каждую новую строку как новый ключ, в переменную попадёт только первая строка. Нужно **одна строка с `\n`** и значение в кавычках:

```bash
UPLOAD_TOKEN_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIBIjANBg...\n...\n-----END PUBLIC KEY-----"
```

**Пример готовой строки** (подставь свой ключ между заголовком и футером; переносы в PEM заменить на `\n`):

```bash
# Публичный ключ Backend (PEM) — одна строка, кавычки обязательны
UPLOAD_TOKEN_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n<строка1_base64>\n<строка2>\n...\n-----END PUBLIC KEY-----"
```

Собрать из файла в одну строку с `\n` (в папке, где лежит `upload_token_public.pem`):

```bash
# Вывод в одну строку с \n — вставить в .env как значение UPLOAD_TOKEN_JWT_PUBLIC_KEY
awk 'NF {printf "%s\\n", $0}' upload_token_public.pem
# Или вручную: скопировать содержимое файла и заменить каждый перенос строки на \n, затем взять в двойные кавычки.
```

---

### 2.2 Ключ оператора Arweave (только arweave-uploader)

Им микросервис подписывает bundle-транзакцию (оплата в Arweave). Формат: Arweave JWK (RSA, JSON).

#### Где находиться при генерации / сохранении

- Рабочая директория: **корень arweave-uploader** (`arweave-uploader/`) — если сохраняете файл ключа рядом с проектом (например `./arweave-key.json`). Либо любая безопасная папка; путь потом задаётся в env.

#### Как получить Arweave JWK

1. **Официальный кошелёк Arweave** — экспорт ключа в формате JWK (JSON).
2. **Скрипт/утилита** — сгенерировать RSA JWK (n, e, d, p, q, …) в формате, совместимом с Arweave (размер ключа по спецификации Arweave, обычно 4096 или 2048 в зависимости от требований библиотеки). При необходимости можно добавить в `arweave-uploader/scripts/` скрипт генерации; по умолчанию ориентируемся на экспорт из кошелька или документацию Arweave.

Файл сохранить, например, как `arweave-uploader/arweave-key.json` (и добавить в `.gitignore`).

#### Переменные окружения — arweave-uploader

Рабочая директория: **корень arweave-uploader** (`arweave-uploader/`).

| Переменная | Что подставить | Обязательность |
|------------|----------------|----------------|
| `ARWEAVE_PRIVATE_KEY` | JSON-строка JWK целиком (одна строка) | Одна из двух: либо эта, либо файл ниже |
| `ARWEAVE_PRIVATE_KEY_FILE` | **Путь** к файлу с JWK, например `./arweave-key.json` | Одна из двух |

Приоритет: если задан `ARWEAVE_PRIVATE_KEY`, используется он; иначе читается файл из `ARWEAVE_PRIVATE_KEY_FILE`. Если ни одного нет — микросервис не стартует.

**Пример в `.env` (arweave-uploader):**

```bash
# Вариант 1: путь к файлу (файл в корне arweave-uploader)
ARWEAVE_PRIVATE_KEY_FILE=./arweave-key.json

# Вариант 2: JWK одной строкой (не коммитить)
# ARWEAVE_PRIVATE_KEY={"kty":"RSA","n":"...","e":"AQAB","d":"...","p":"...","q":"...","dp":"...","dq":"...","qi":"..."}
```

Дополнительно (опционально): `ARWEAVE_PROTOCOL`, `ARWEAVE_HOST`, `ARWEAVE_PORT` — по умолчанию https, arweave.net, 443.

---

### 2.3 Секрет Backend ↔ arweave-uploader (авторизация вызовов микросервиса к Backend)

arweave-uploader вызывает Backend: `PUT .../status`, `POST .../callback`. Авторизация: общий секрет в заголовке `Authorization: Bearer <secret>`.

| Сервис | Переменная | Что подставить |
|--------|------------|----------------|
| arweave-uploader | `UPLOADER_TO_BACKEND_SECRET` или `EDGE_TO_BACKEND_SECRET` | Общая строка-секрет (задать произвольно, хранить в секретах) |
| arweave-uploader | `BACKEND_URL` | Базовый URL Backend без завершающего слеша, например `https://your-backend.example.com` |
| Backend (bot) | Проверка заголовка `Authorization: Bearer <тот же секрет>` | В коде маршрутов uploads (PUT status, POST callback) — сравнение с тем же значением из env (имя переменной в bot при необходимости уточнить в коде) |

Генерировать секрет не криптографическим ключом, а случайной строкой, например:

```bash
openssl rand -hex 32
```

Значение прописать в `.env` (или в секретах деплоя) и в Backend, и в arweave-uploader.

---

## 3. Сводные таблицы по сервисам

### Backend (bot)

| Переменная | Назначение | Где генерировать / откуда взять |
|------------|------------|----------------------------------|
| `UPLOAD_TOKEN_JWT_PRIVATE_KEY` | PEM приватного ключа RSA (подпись JWT) | Сгенерировать: `openssl genrsa -out upload_token_private.pem 2048` (в любой папке, например `keys/`) |
| `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE` | Путь к файлу с PEM приватного ключа | Указать путь к `upload_token_private.pem` |
| Секрет для приёма callback/status от uploader | По контракту Backend проверяет заголовок | Задать общий секрет с arweave-uploader (см. п. 2.3) |

**В какой папке выполнять команды:** генерация ключей — в любой (например `keys/`); запуск Backend — из **`bot/`**.

---

### arweave-uploader (Node.js микросервис)

| Переменная | Назначение | Где генерировать / откуда взять |
|------------|------------|----------------------------------|
| `UPLOAD_TOKEN_JWT_PUBLIC_KEY` | PEM или JWK публичного ключа Backend (проверка JWT) | Из той же пары: `openssl rsa -in upload_token_private.pem -pubout -out upload_token_public.pem` (в папке с приватным ключом) |
| `ARWEAVE_PRIVATE_KEY` | JWK ключа оператора Arweave (строка JSON) | Кошелёк Arweave или скрипт; не из openssl |
| `ARWEAVE_PRIVATE_KEY_FILE` | Путь к файлу с JWK оператора | Например `./arweave-key.json` в корне arweave-uploader |
| `BACKEND_URL` | Базовый URL Backend | Задать вручную (например `http://localhost:8000` или production URL) |
| `UPLOADER_TO_BACKEND_SECRET` или `EDGE_TO_BACKEND_SECRET` | Секрет для заголовка Authorization при вызовах Backend | Задать общий с Backend (например `openssl rand -hex 32`) |
| `PORT` | Порт HTTP-сервера | По умолчанию 3000; на деплое часто задаёт платформа |

**В какой папке выполнять команды:** запуск и `.env` — из **`arweave-uploader/`**. Генерация JWT-пары — в любой папке (например `keys/`); путь к приватному/публичному файлу в env указывать относительный или абсолютный.

---

## 4. Краткий чеклист «с нуля»

1. **JWT-пара (одна папка, один раз)**  
   - `cd keys` (или любая папка)  
   - `openssl genrsa -out upload_token_private.pem 2048`  
   - `openssl rsa -in upload_token_private.pem -pubout -out upload_token_public.pem`  

2. **Backend (bot)**  
   - В `bot/.env`: `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE` = путь к `upload_token_private.pem` (или вставить PEM в `UPLOAD_TOKEN_JWT_PRIVATE_KEY`).  
   - Задать секрет для callback/status и прописать в bot (если ещё не сделано).  

3. **arweave-uploader**  
   - В `arweave-uploader/.env`: `UPLOAD_TOKEN_JWT_PUBLIC_KEY` = содержимое `upload_token_public.pem`.  
   - `ARWEAVE_PRIVATE_KEY_FILE=./arweave-key.json` (или JWK в `ARWEAVE_PRIVATE_KEY`) — ключ оператора из кошелька/скрипта.  
   - `BACKEND_URL` и `UPLOADER_TO_BACKEND_SECRET` (или `EDGE_TO_BACKEND_SECRET`).  

4. **Проверка**  
   - Запуск Backend из `bot/`, arweave-uploader из `arweave-uploader/`.  
   - Smoke: `arweave-uploader/scripts/smoke-deployed.sh` (при real smoke нужны `SMOKE_REAL=1` и `SMOKE_JWT_PRIVATE_KEY_FILE` или `SMOKE_JWT_PRIVATE_KEY_PEM`; на деплое в `UPLOAD_TOKEN_JWT_PUBLIC_KEY` — публичный ключ от той же пары).  

---

## 5. Связь с общей архитектурой Activity

- Поток «метаданные Activity → Arweave» входит в вертикальную архитектуру (блокчейн → Arweave → Supabase).
- Загрузка в Arweave идёт через Backend (prepare → JWT) и **микросервис arweave-uploader** (проверка JWT + Data Item, подпись bundle tx ключом оператора). Раньше планировалась Supabase Edge Function — заменена на Node.js микросервис из-за проблем с подключением к Arweave в Edge.
- Backend (bot) при вызове uploader может использовать URL Supabase Edge или отдельный URL микросервиса (в зависимости от конфигурации деплоя); настройка URL — в коде/конфиге bot (например `SUPABASE_URL` или отдельная переменная для base URL arweave-uploader).

**Связанные документы:**  
- [arweave-uploader/docs/architecture.md](../../arweave-uploader/docs/architecture.md) — контракт API, env микросервиса.  
- [bot/docs/tests/data-upload-integration-tests.md](../../bot/docs/tests/data-upload-integration-tests.md) — JWT ключи и openssl (раздел «JWT upload_token: генерация и хранение ключей»).  
- [supabase/docs/arweave-upload-security.md](../../supabase/docs/arweave-upload-security.md) — полная схема безопасности (ранее под Edge; логика ключей та же).

---

**Версия:** 2.0  
**Дата:** 2026-01-30  
**Изменения:** архитектура переведена на микросервис arweave-uploader (Node.js); добавлены пошаговые инструкции по генерации ключей, папкам и переменным окружения для Backend и arweave-uploader.
