# Интеграция WebApp кошелька в Telegram бот

## Описание
Данное руководство описывает интеграцию WebApp кошелька в Telegram бот Amanita. WebApp позволяет пользователям создавать и восстанавливать Ethereum кошельки прямо внутри Telegram.

## Настройка

### 1. Переменные окружения
В файле `.env` проекта должны быть указаны следующие переменные:

```
TELEGRAM_BOT_TOKEN=your_bot_token
WALLET_APP=http://localhost:8080/
```

Для production нужно указать публичный HTTPS URL:

```
WALLET_APP=https://your-domain.com/wallet/
```

### 2. Запуск локального сервера WebApp

Для разработки можно использовать локальный сервер:

```bash
cd webapp
python3 -m http.server 8080
```

### 3. Доступ к WebApp из Telegram бота

WebApp доступен через:

1. Команду `/wallet` - отправляет сообщение с кнопкой для открытия WebApp
2. Основное меню (команда `/menu`) - включает кнопку "🔐 Криптокошелёк" для доступа к WebApp

## Процесс работы

1. Пользователь нажимает на кнопку WebApp
2. Открывается WebApp в окне Telegram
3. Пользователь может:
   - Создать новый кошелёк (сгенерируется случайная сид-фраза)
   - Восстановить существующий кошелёк по сид-фразе
4. Адрес кошелька автоматически отправляется обратно в бот

## Технические детали

### Как WebApp отправляет данные в бот

WebApp использует метод `Telegram.WebApp.sendData()` для отправки адреса кошелька обратно в Telegram бот:

```javascript
// В webapp/main.js
function sendAddressToBot() {
  if (Telegram && Telegram.WebApp && Telegram.WebApp.sendData) {
    Telegram.WebApp.sendData(currentWallet.address);
  }
}
```

### Обработка данных от WebApp в боте

Для полной обработки данных от WebApp нужно реализовать обработчик web_app_data:

```python
@router.message(content_types=types.ContentType.WEB_APP_DATA)
async def handle_web_app_data(message: types.Message):
    """Обрабатывает данные от WebApp кошелька"""
    user_id = message.from_user.id
    wallet_address = message.web_app_data.data
    
    logging.info(f"[WALLET] Получен адрес кошелька от WebApp: {wallet_address}")
    
    # Здесь нужно сохранить адрес кошелька пользователя
    user_settings.set_web3_credentials(user_id, wallet_address, None)
    
    await message.answer(f"Ваш кошелёк успешно подключен!\nАдрес: {wallet_address[:10]}...{wallet_address[-8:]}")
```

## Безопасность

- В текущей MVP-версии приватные ключи хранятся в localStorage браузера
- Для production рекомендуется добавить:
  - Шифрование приватных данных
  - Защиту паролем
  - Дополнительную аутентификацию при восстановлении кошелька

## Дальнейшее развитие

1. Добавить возможность подписывать транзакции напрямую из WebApp
2. Интегрировать балансы и историю транзакций
3. Добавить поддержку разных блокчейнов помимо Ethereum 