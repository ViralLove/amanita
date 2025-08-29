# Чек-лист развертывания системы смарт-контрактов

## 🚀 Быстрый старт

### 1. Подготовка окружения
- [ ] Установить Node.js (v18+)
- [ ] Установить Python (3.8+)
- [ ] Клонировать проект
- [ ] Создать `.env` файл

### 2. Установка зависимостей
```bash
# Node.js зависимости
npm install

# Python зависимости
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
```bash
# Обязательные
DEPLOYER_PRIVATE_KEY=0x...
SELLER_PRIVATE_KEY=0x...
AMANITA_REGISTRY_CONTRACT_ADDRESS=0x... # Будет заполнен после деплоя

# Опциональные
POLYGON_MAINNET_RPC=https://...
POLYGON_MUMBAI_RPC=https://...
POLYGONSCAN_API_KEY=...
```

## 🔧 Компиляция и деплой

### 4. Компиляция контрактов
```bash
npx hardhat compile
```

### 5. Запуск локальной сети
```bash
# В отдельном терминале
npx hardhat node
```

### 6. Деплой контрактов
```bash
# 1. Деплой реестра
npm run deploy:registry

# 2. Скопировать адрес реестра в .env
# AMANITA_REGISTRY_CONTRACT_ADDRESS=0x...

# 3. Деплой всех контрактов
npm run deploy:all

# 4. Генерация инвайтов
npm run deploy:invites

# 5. Загрузка каталога
npm run deploy:catalog
```

## 🧪 Тестирование

### 7. Запуск тестов
```bash
# Unit-тесты
pytest bot/tests/ -v -m "not integration"

# Интеграционные тесты
pytest bot/tests/ -v -m "integration"

# Все тесты
pytest bot/tests/ -v
```

## 📋 Проверка работоспособности

### 8. Проверка подключения
```python
from bot.services.core.blockchain import BlockchainService

# Создание сервиса
service = BlockchainService()

# Проверка реестра
print(f"Registry address: {service.registry.address}")

# Проверка контрактов
print(f"Contracts: {list(service.contracts.keys())}")
```

### 9. Проверка функций
```python
# Валидация инвайта
result = service.validate_invite_code("AMANITA-TEST-CODE")
print(f"Invite validation: {result}")

# Получение продуктов
products = service.get_all_products()
print(f"Products count: {len(products)}")
```

## 🚨 Устранение неполадок

### Частые проблемы

#### Ошибка подключения к Web3
- [ ] Проверить, запущен ли `npx hardhat node`
- [ ] Проверить RPC_URL в .env
- [ ] Проверить chainId в hardhat.config.js

#### Ошибка загрузки ABI
- [ ] Убедиться, что контракты скомпилированы
- [ ] Проверить путь к artifacts в config.py
- [ ] Проверить структуру папок

#### Ошибка деплоя
- [ ] Проверить баланс аккаунта
- [ ] Проверить приватные ключи
- [ ] Проверить gas limit

## 📚 Следующие шаги

### 10. Разработка
- [ ] Изучить архитектуру контрактов
- [ ] Добавить новые функции в BlockchainService
- [ ] Создать новые тесты

### 11. Production
- [ ] Настроить mainnet RPC
- [ ] Получить API ключи для верификации
- [ ] Настроить мониторинг

### 12. Документация
- [ ] Обновить README.md
- [ ] Добавить примеры использования
- [ ] Создать руководство по API

## 🔗 Полезные ссылки

- [Hardhat Documentation](https://hardhat.org/docs)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)

## 📞 Поддержка

При возникновении проблем:
1. Проверить логи в консоли
2. Изучить существующие тесты
3. Создать issue в репозитории
4. Обратиться к команде разработки
