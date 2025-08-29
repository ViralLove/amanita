# Техническая реализация онбординга AMANITA

## Обзор архитектуры

Система онбординга AMANITA построена на основе **Finite State Machine (FSM)** с интеграцией **Telegram WebApp** для создания и управления криптографическими кошельками. Архитектура обеспечивает безопасный и удобный процесс регистрации пользователей в закрытой экосистеме.

## Компоненты системы

### 1. FSM (Finite State Machine)

**Файл**: `bot/fsm/onboarding_states.py`

```python
class OnboardingStates(StatesGroup):
    LanguageSelection = State()        # Выбор языка
    OnboardingPathChoice = State()     # Выбор пути онбординга
    InviteInput = State()             # Ввод инвайт-кода
    WebAppConnecting = State()        # Подключение к WebApp
    RestoreAccess = State()           # Восстановление доступа
    Completed = State()               # Завершение онбординга
```

### 2. Обработчики онбординга

**Файл**: `bot/handlers/onboarding_fsm.py`

#### Основные обработчики:

- **`start_onboarding`** - точка входа `/start`
- **`set_language`** - установка языка пользователя
- **`process_invite_choice`** - обработка выбора пути
- **`process_invite_code`** - валидация инвайт-кода
- **`process_restore_access`** - восстановление доступа

#### Поддерживаемые языки:

```python
LANG_KEYBOARD = [
    ["🇷🇺 ru", "🇪🇸 es", "🇬🇧 en", "🇫🇷 fr"],
    ["🇪🇪 et", "🇮🇹 it", "🇵🇹 pt", "🇩🇪 de"],
    ["🇵🇱 pl", "🇫🇮 fi", "🇳🇴 no", "🇸🇪 sv"]
]
```

### 3. WebApp интеграция

**Файл**: `bot/handlers/webapp_common.py`

#### Режимы WebApp:

1. **`create_new`** - создание нового кошелька
2. **`recovery_only`** - восстановление существующего кошелька
3. **`view_seed`** - просмотр seed-фразы
4. **`sign_tx`** - подпись транзакций

#### Параметры URL:

```python
# Создание нового кошелька
webapp_url = f"{WALLET_APP_URL}?mode=create_new&invite_verified=true&source=onboarding&debug=1"

# Восстановление доступа
webapp_url = f"{WALLET_APP_URL}?mode=recovery_only&invite_verified=false&source=onboarding"
```

## Процесс онбординга

### 1. Старт бота (`/start`)

```python
@router.message(F.text == "/start")
async def start_onboarding(message: types.Message, state: FSMContext):
    await state.set_state(OnboardingStates.LanguageSelection)
    await message.answer("Пожалуйста, выберите язык:", reply_markup=get_language_keyboard())
```

**Действие**: Устанавливает состояние `LanguageSelection` и показывает клавиатуру выбора языка.

### 2. Выбор языка

```python
@router.message(OnboardingStates.LanguageSelection, F.text.in_(lang_map.keys()))
async def set_language(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = lang_map[message.text]
    user_settings.set_language(user_id, lang)
    
    await state.set_state(OnboardingStates.OnboardingPathChoice)
    # Показывает приветственное сообщение и выбор пути
```

**Действие**: Сохраняет выбранный язык в `UserSettings` и переводит в состояние `OnboardingPathChoice`.

### 3. Выбор пути онбординга

Пользователю предлагается два варианта:

- **🌱 У меня есть приглашение** - для новых пользователей
- **🔄 Я уже был(а) здесь** - для восстановления доступа

### 4. Ввод инвайт-кода

#### Валидация формата:

```python
if not re.match(r"^AMANITA-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}$", invite_code):
    await message.answer(loc.t("onboarding.invalid_invite"))
    return
```

**Формат**: `AMANITA-XXXX-YYYY` (12 символов, буквы и цифры)

#### Блокчейн валидация:

```python
validation = blockchain.validate_invite_code(invite_code)
if not validation.get("success"):
    await message.answer(loc.t("onboarding.invalid_invite"))
    return
```

**Метод**: `BlockchainService.validate_invite_code()` вызывает смарт-контракт `InviteNFT.validateInviteCode()`

### 5. WebApp интеграция

После успешной валидации инвайта:

1. **Формирование URL** с параметрами режима
2. **Создание кнопки** с `WebAppInfo`
3. **Переход в состояние** `WebAppConnecting`

```python
keyboard = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(
            text=loc.t("onboarding.btn_connect"),
            web_app=WebAppInfo(url=webapp_url)
        )
    ]],
    resize_keyboard=True,
    one_time_keyboard=True
)
```

### 6. Обработка данных WebApp

**Файл**: `bot/handlers/webapp_common.py`

#### Получение данных:

```python
@router.message(F.web_app_data)
async def handle_web_app_data(message: types.Message, state: FSMContext):
    data = json.loads(message.web_app_data.data)
    event = data.get("event")
    wallet_address = data.get("address")
```

#### События WebApp:

- **`created_access`** - создан новый кошелёк
- **`restored_access`** - восстановлен существующий кошелёк
- **`seed_viewed`** - просмотрена seed-фраза
- **`tx_signed`** - подписана транзакция

## Блокчейн интеграция

### 1. Валидация инвайт-кодов

**Контракт**: `InviteNFT.sol`

**Метод**: `validateInviteCode(string memory inviteCode)`

**Проверки**:
- Существование инвайта
- Статус использования
- Срок действия
- Права пользователя

### 2. Активация инвайтов

**Метод**: `AccountService.activate_and_mint_invites()`

**Процесс**:
1. Генерация 12 новых инвайт-кодов
2. Вызов смарт-контракта `activateAndMintInvites`
3. Минтинг новых NFT для пользователя
4. Возврат списка новых кодов

```python
async def activate_and_mint_invites(self, invite_code: str, wallet_address: str) -> List[str]:
    # Генерация новых кодов
    new_invite_codes = [generate_random_code() for _ in range(12)]
    
    # Вызов блокчейн-контракта
    tx_hash = await self.blockchain_service.transact_contract_function(
        "InviteNFT",
        "activateAndMintInvites",
        seller_private_key,
        invite_code,
        wallet_address,
        new_invite_codes,
        0  # expiry
    )
    
    return new_invite_codes
```

## Локализация

### Структура ключей

**Файл**: `bot/templates/ru.json`

```json
{
  "onboarding": {
    "welcome_title": "🍄 Добро пожаловать в экосистему AMANITA.",
    "welcome_description": "Ты попал туда, где натуральная медицина встречает заботу...",
    "btn_have_invite": "🌱 У меня есть приглашение",
    "btn_restore": "🔄 Я уже был(а) здесь",
    "input_invite_label": "🌱 Введи свой код приглашения:",
    "invalid_invite": "⚠️ Что-то не так с кодом...",
    "invite_validated": "🍃 Твой код в порядке. Теперь активируем его.",
    "onboarding_complete": "🍄 Ты подключён(а)."
  }
}
```

### Поддерживаемые языки

- 🇷🇺 Русский (базовый)
- 🇬🇧 English
- 🇪🇸 Español
- 🇫🇷 Français
- 🇪🇪 Eesti
- 🇮🇹 Italiano
- 🇵🇹 Português
- 🇩🇪 Deutsch
- 🇵🇱 Polski
- 🇫🇮 Suomi
- 🇳🇴 Norsk
- 🇸🇪 Svenska

## Безопасность

### 1. Валидация данных

- **Формат инвайт-кода**: Регулярное выражение
- **Блокчейн проверка**: Валидация через смарт-контракт
- **Адрес кошелька**: Проверка формата Ethereum адреса

### 2. FSM защита

- **Состояния**: Строгая последовательность переходов
- **Данные**: Валидация на каждом этапе
- **Таймауты**: Автоматический сброс состояния

### 3. WebApp безопасность

- **HTTPS**: Только защищенные соединения
- **Валидация**: Проверка подписи Telegram
- **Изоляция**: Отдельный контекст для каждого пользователя

## Обработка ошибок

### 1. Валидация инвайта

```python
if not validation.get("success"):
    reason = validation.get("reason")
    logger.error(f"[INVITE] Ошибка валидации: {reason}")
    await message.answer(loc.t("onboarding.invalid_invite"))
    await message.answer(loc.t("onboarding.retry"))
    return
```

### 2. WebApp ошибки

```python
if not wallet_address or not wallet_address.startswith('0x') or len(wallet_address) != 42:
    logger.warning(f"[WEBAPP][WARNING] Неверный формат адреса: {wallet_address}")
    await message.answer(loc.t("onboarding.invalid_address_format"))
    return
```

### 3. Блокчейн ошибки

```python
try:
    tx_hash = await self.blockchain_service.transact_contract_function(...)
except Exception as e:
    logger.error(f"[AccountService] Ошибка транзакции: {e}")
    raise Exception("Транзакция не была отправлена или завершилась с ошибкой")
```

## Мониторинг и логирование

### 1. Структурированные логи

```python
logger.info(f"[ONBOARDING] Установлен язык: {lang} для user_id={user_id}")
logger.info(f"[INVITE] Получен инвайт-код для проверки: {invite_code}")
logger.info(f"[WEBAPP] Получены данные от WebApp для user_id={user_id}")
```

### 2. Метрики

- Время завершения онбординга
- Успешность валидации инвайтов
- Количество ошибок на этапе
- Конверсия WebApp интеграции

## Тестирование

### 1. Unit тесты

**Файл**: `bot/tests/test_onboarding_integration.py`

- Валидация формата инвайт-кодов
- Проверка FSM переходов
- Тестирование локализации

### 2. Интеграционные тесты

- Взаимодействие с блокчейном
- WebApp интеграция
- Полный flow онбординга

### 3. Mock сервисы

```python
@pytest.fixture
def mock_blockchain_service():
    class MockBlockchainService:
        def validate_invite_code(self, invite_code):
            return {"success": True, "reason": ""}
    return MockBlockchainService()
```

## Конфигурация

### Переменные окружения

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token

# WebApp
WALLET_APP_URL=https://localhost:3000/

# Блокчейн
SELLER_PRIVATE_KEY=0x...
AMANITA_REGISTRY_CONTRACT_ADDRESS=0x...
INVITE_NFT_CONTRACT_ADDRESS=0x...
```

### Настройки FSM

```python
# Таймауты состояний
ONBOARDING_TIMEOUT = 300  # 5 минут
LANGUAGE_SELECTION_TIMEOUT = 60  # 1 минута
INVITE_INPUT_TIMEOUT = 120  # 2 минуты
```

## Расширение функциональности

### 1. Новые режимы WebApp

```python
# Добавление нового режима
if event == "new_mode":
    await handle_new_mode(data, state)
```

### 2. Дополнительные языки

```python
# Добавление языка в LANG_KEYBOARD
LANG_KEYBOARD.append(["🇯🇵 ja", "🇰🇷 ko", "🇨🇳 zh"])
lang_map["🇯🇵 ja"] = "ja"
```

### 3. Кастомные валидации

```python
# Расширение валидации инвайта
async def custom_invite_validation(invite_code: str) -> dict:
    # Дополнительная логика
    pass
```

## Заключение

Система онбординга AMANITA представляет собой комплексное решение, объединяющее:

- **FSM** для управления состоянием пользователя
- **WebApp** для криптографических операций
- **Блокчейн** для валидации и активации
- **Локализацию** для многоязычной поддержки
- **Безопасность** на всех уровнях

Архитектура обеспечивает масштабируемость, безопасность и удобство использования, позволяя новым пользователям легко присоединиться к экосистеме AMANITA.
