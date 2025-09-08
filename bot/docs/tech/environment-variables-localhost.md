# 🔧 Переменные окружения для localhost (Development)

## 📋 Существующие переменные

### Блокчейн
```bash
# Блокчейн подключение
WEB3_PROVIDER_URI="http://127.0.0.1:8545"

# Адреса контрактов
AMANITA_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
INVITE_NFT_CONTRACT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
PRODUCT_REGISTRY_CONTRACT_ADDRESS=0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9

# Продавец
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
SELLER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
```

### API
```bash
# API настройки
AMANITA_API_URL="http://localhost:8000"
AMANITA_API_KEY="ak_seller_node_amanita_iveta_launch_september_2025"
AMANITA_API_SECRET=""
AMANITA_API_HMAC_SECRET_KEY=""
```

### Хранилище
```bash
# Тип хранилища
STORAGE_TYPE="pinata"
STORAGE_COMMUNICATION_MODE="sync"

# ArWeave
ARWEAVE_PRIVATE_KEY=

# Pinata
PINATA_API_KEY=
PINATA_API_SECRET=
PINATA_JWT=
PINATA_NEW_API_KEY=
```

### Telegram
```bash
TELEGRAM_BOT_TOKEN=""
```

### Система
```bash
APP_ROOT_DIR="bot"
WALLET_APP_URL="https://0e3d247dd47c.ngrok-free.app"
NODE_ADMIN_PRIVATE_KEY=
```

## 🆕 Новые переменные для DI контейнера

### Логирование
```bash
# Уровень логирования (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL="DEBUG"

# Включить отладочный режим
ENABLE_DEBUG="true"
```

### Блокчейн (дополнительные настройки)
```bash
# Таймаут подключения к блокчейну (секунды)
BLOCKCHAIN_TIMEOUT="60"

# Количество попыток переподключения
BLOCKCHAIN_RETRY_ATTEMPTS="3"
```

### API (дополнительные настройки)
```bash
# Таймаут API запросов (секунды)
API_TIMEOUT="30"

# Включить логирование API запросов
ENABLE_API_LOGGING="true"
```

### Безопасность
```bash
# Включить HMAC валидацию
ENABLE_HMAC_VALIDATION="true"

# Включить rate limiting
ENABLE_RATE_LIMITING="false"
```

### Telegram (дополнительные настройки)
```bash
# URL для webhook (None для polling в development)
TELEGRAM_WEBHOOK_URL=""

# Таймаут polling (секунды)
TELEGRAM_POLLING_TIMEOUT="10"
```

### Кэширование
```bash
# Включить кэширование
ENABLE_CACHING="true"

# TTL кэша (секунды)
CACHE_TTL="300"
```

### Мониторинг
```bash
# Включить метрики
ENABLE_METRICS="true"

# Интервал сбора метрик (секунды)
METRICS_INTERVAL="60"
```

## 📝 Полный .env файл для localhost

```bash
# ===========================================
# AMANITA BOT - LOCALHOST CONFIGURATION
# ===========================================

# Telegram Bot
TELEGRAM_BOT_TOKEN=""

# ===========================================
# БЛОКЧЕЙН КОНФИГУРАЦИЯ
# ===========================================
WEB3_PROVIDER_URI="http://127.0.0.1:8545"
BLOCKCHAIN_TIMEOUT="60"
BLOCKCHAIN_RETRY_ATTEMPTS="3"

# Контракты
AMANITA_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
INVITE_NFT_CONTRACT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
PRODUCT_REGISTRY_CONTRACT_ADDRESS=0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9

# Продавец
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
SELLER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

# ===========================================
# API КОНФИГУРАЦИЯ
# ===========================================
AMANITA_API_URL="http://localhost:8000"
AMANITA_API_KEY="ak_seller_node_amanita_iveta_launch_september_2025"
AMANITA_API_SECRET=""
AMANITA_API_HMAC_SECRET_KEY=""
API_TIMEOUT="30"
ENABLE_API_LOGGING="true"

# ===========================================
# ХРАНИЛИЩЕ
# ===========================================
STORAGE_TYPE="pinata"
STORAGE_COMMUNICATION_MODE="sync"

# ArWeave
ARWEAVE_PRIVATE_KEY=

# Pinata
PINATA_API_KEY=
PINATA_API_SECRET=
PINATA_JWT=
PINATA_NEW_API_KEY=

# ===========================================
# TELEGRAM КОНФИГУРАЦИЯ
# ===========================================
TELEGRAM_WEBHOOK_URL=""
TELEGRAM_POLLING_TIMEOUT="10"

# ===========================================
# СИСТЕМА
# ===========================================
APP_ROOT_DIR="bot"
WALLET_APP_URL="https://0e3d247dd47c.ngrok-free.app"
NODE_ADMIN_PRIVATE_KEY=

# ===========================================
# ОКРУЖЕНИЕ
# ===========================================
# Окружение приложения (development, production, testing)
# Если не указано, используется development
ENVIRONMENT="development"

# ===========================================
# ЛОГИРОВАНИЕ И ОТЛАДКА
# ===========================================
LOG_LEVEL="DEBUG"
ENABLE_DEBUG="true"

# ===========================================
# БЕЗОПАСНОСТЬ
# ===========================================
ENABLE_HMAC_VALIDATION="true"
ENABLE_RATE_LIMITING="false"

# ===========================================
# КЭШИРОВАНИЕ
# ===========================================
ENABLE_CACHING="true"
CACHE_TTL="300"

# ===========================================
# МОНИТОРИНГ
# ===========================================
ENABLE_METRICS="true"
METRICS_INTERVAL="60"
```

## 🔧 Использование в Python коде

### В DI контейнере
```python
from dotenv import load_dotenv
import os

# Загружаем .env файл
load_dotenv()

# Читаем переменные
blockchain_rpc = os.getenv("WEB3_PROVIDER_URI")
storage_type = os.getenv("STORAGE_TYPE")
api_url = os.getenv("AMANITA_API_URL")
log_level = os.getenv("LOG_LEVEL", "INFO")  # с fallback
enable_debug = os.getenv("ENABLE_DEBUG", "false").lower() == "true"
```

### В config.py
```python
# Уже реализовано в существующем config.py
from dotenv import load_dotenv
load_dotenv()

# Переменные автоматически доступны через os.getenv()
```

## 📋 Рекомендации

1. **Безопасность**: Никогда не коммитьте .env файл с реальными секретами
2. **Fallback значения**: Всегда указывайте значения по умолчанию
3. **Типизация**: Используйте правильные типы (bool, int, string)
4. **Документация**: Документируйте каждую переменную
5. **Валидация**: Проверяйте обязательные переменные при старте

## 🚀 Следующие шаги

1. Добавить новые переменные в .env файл
2. Обновить DI контейнер для использования новых переменных
3. Добавить валидацию конфигурации
4. Протестировать все окружения
