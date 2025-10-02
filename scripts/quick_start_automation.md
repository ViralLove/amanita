# 🚀 Amanita Ecosystem Quick Start Automation

## 📋 Обзор
Полностью автоматизированный скрипт для развертывания экосистемы Amanita с нуля на localhost. Скрипт выполняет полный цикл: от запуска инфраструктуры до активации пользователей и запуска Telegram бота.

## 🎯 Архитектура скрипта

### Основные компоненты
1. **Инфраструктурные сервисы**: Hardhat node, Wallet server, ngrok tunnel
2. **Смарт-контракты**: Деплой и регистрация всех контрактов экосистемы
3. **Пользовательская активация**: Минтинг инвайтов и активация селлера
4. **Telegram бот**: Запуск основного интерфейса

### Структура функций

#### 🔧 Системные функции
- `cleanup_and_kill_processes()` - Очистка процессов и файлов
- `check_prerequisites()` - Проверка зависимостей
- `setup_environment()` - Настройка переменных окружения

#### 🌐 Инфраструктурные функции
- `start_hardhat_node()` - Запуск Hardhat node
- `start_wallet_server()` - Запуск wallet сервера
- `start_ngrok_tunnel()` - Создание ngrok туннеля

#### 📦 Контрактные функции
- `deploy_contracts()` - Деплой контрактов (Action 1)
- `extract_contract_addresses()` - Извлечение адресов из логов
- `force_copy_contract_addresses()` - Принудительное копирование адресов

#### 👥 Пользовательские функции
- `mint_invites()` - Минтинг инвайтов (Action 777)
- `select_best_invite()` - Автовыбор лучшего инвайта
- `activate_seller()` - Активация селлера (Action 888)

#### 🤖 Бот функции
- `start_bot()` - Запуск Telegram бота
- `cleanup()` - Очистка при завершении

## 🔄 Детальный процесс выполнения

### Этап 1: Подготовка системы
```bash
# Очистка старых процессов и файлов
cleanup_and_kill_processes()
├── Удаление старых invite файлов
├── Убийство процессов на портах 3000, 8545
└── Очистка ngrok процессов

# Проверка зависимостей
check_prerequisites()
├── Python 3.x
├── ngrok
├── Node.js
└── npm
```

### Этап 2: Запуск инфраструктуры
```bash
# Hardhat node
start_hardhat_node()
├── Проверка существующего процесса
├── Запуск в фоне (PID: $HARDHAT_PID)
├── Ожидание готовности (до 30 сек)
└── Проверка JSON-RPC ответа

# Wallet server
start_wallet_server()
├── Переход в директорию wallet/
├── Запуск HTTP сервера на порту 3000
└── Проверка доступности

# ngrok tunnel
start_ngrok_tunnel()
├── Запуск ngrok http 3000
├── Получение публичного URL через API
└── Обновление WALLET_APP_URL в .env файлах
```

### Этап 3: Настройка окружения
```bash
setup_environment()
├── Создание/обновление .env файлов
├── Установка localhost ключей:
│   ├── DEPLOYER_PRIVATE_KEY
│   ├── SELLER_ADDRESS
│   ├── SELLER_PRIVATE_KEY
│   └── WEB3_PROVIDER_URI
└── Валидация файлов
```

### Этап 4: Деплой контрактов
```bash
deploy_contracts()
├── Выполнение: DEPLOY_ACTION=1 deploy_full.js
├── Извлечение адресов контрактов:
│   ├── MagicRegistry
│   ├── SpiralEngine
│   ├── ProductRegistry
│   ├── SoulboundCore
│   ├── SoulMetadata
│   ├── SoulRecovery
│   ├── SoulIntegration
│   └── SoulIdentity
├── Обработка ошибок "Parameter decoding error"
└── Принудительное копирование адресов в bot/.env
```

### Этап 5: Минтинг инвайтов
```bash
mint_invites()
├── Проверка существующих invite файлов
├── Выполнение: DEPLOY_ACTION=777 deploy_full.js
├── Создание deployer_invites_localhost.txt
├── Обработка ошибок контрактов
└── Продолжение при проблемах с состоянием
```

### Этап 6: Активация селлера
```bash
activate_seller()
├── Проверка существующих seller invites
├── Автовыбор лучшего deployer invite
├── Выполнение: DEPLOY_ACTION=888 deploy_full.js
├── Создание ${SELLER_ADDRESS}_invites.txt
└── Обработка ошибок активации
```

### Этап 7: Запуск бота
```bash
start_bot()
├── Проверка наличия bot/main.py
├── Валидация invite файлов
├── Запуск: python3 bot/main.py
├── Проверка успешного старта
└── Логирование в /tmp/bot_output.log
```

## 🔧 Вспомогательные функции

### Управление переменными окружения
```bash
update_env_var(file, key, value)
├── Очистка форматирования (sed)
├── Удаление дубликатов (awk)
├── Обновление или добавление переменной
└── Создание файла при отсутствии
```

### Извлечение адресов контрактов
```bash
extract_contract_addresses(output)
├── Regex поиск адресов в логах
├── Fallback к существующим .env файлам
├── Обновление всех .env файлов
└── Валидация результатов
```

### Принудительное копирование
```bash
force_copy_contract_addresses()
├── Извлечение всех адресов из root .env
├── Создание временного файла
├── Фильтрация старых адресов
├── Добавление новых адресов
└── Замена bot/.env с проверкой ошибок
```

## 📊 Конфигурация

### Порты и адреса
- **Hardhat node**: 8545
- **Wallet server**: 3000
- **ngrok API**: 4040
- **Default keys**: localhost Hardhat аккаунты

### Переменные окружения
- `DEPLOYER_PRIVATE_KEY`: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
- `SELLER_ADDRESS`: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
- `SELLER_PRIVATE_KEY`: 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
- `WEB3_PROVIDER_URI`: http://localhost:8545

### Файлы и директории
- **Root .env**: `$PROJECT_ROOT/.env`
- **Bot .env**: `$PROJECT_ROOT/bot/.env`
- **Invite files**: `$PROJECT_ROOT/bot/flowers/`
- **Log files**: `/tmp/hardhat_node.log`, `/tmp/ngrok.log`, `/tmp/bot_output.log`

## 🚨 Обработка ошибок

### Известные проблемы

#### 1. **"Parameter decoding error"** - Критическая проблема состояния контрактов

##### 🔍 **Детальный анализ проблемы**

**Описание ошибки:**
```
❌ Контракт не отвечает на name(): Parameter decoding error: Returned values aren't valid, did it run Out of Gas? You might also see this error if you are not using the correct ABI for the contract you are retrieving data from, requesting data from a block number that does not exist, or querying a node which is not fully synced.
```

**Контекст возникновения:**
- Ошибка появляется при попытке взаимодействия с уже задеплоенными контрактами
- Происходит в скрипте `deploy_full.js` при выполнении действий 1, 777, 888
- Возникает при вызове базовых методов контрактов (например, `name()`)

**Техническая суть:**
1. **Проблема ABI**: Контракт задеплоен, но ABI не соответствует реальному коду контракта
2. **Состояние контракта**: Контракт находится в некорректном состоянии после деплоя
3. **Проблемы сети**: Hardhat node не синхронизирован или имеет проблемы с состоянием
4. **Проблемы газа**: Контракт не может выполнить операцию из-за недостатка газа

**Анализ по методологии @analysis.mdc:**

**Корневая причина (Root Cause Analysis):**
- Контракты задеплоены успешно (видны в логах деплоя)
- Адреса контрактов корректны и записываются в `.env`
- Проблема возникает при попытке **чтения состояния** контрактов
- Это указывает на **несоответствие ABI** или **проблемы с компиляцией**

**Влияние на систему:**
- ✅ **Инфраструктура работает**: Hardhat node, wallet server, ngrok
- ✅ **Контракты задеплоены**: Адреса корректны и записаны
- ❌ **Взаимодействие с контрактами невозможно**: Методы не отвечают
- ❌ **Минтинг инвайтов не работает**: Нельзя проверить состояние
- ❌ **Активация селлера не работает**: Нельзя взаимодействовать с SpiralEngine

**Стратегия обработки в скрипте:**
```bash
# Скрипт обрабатывает ошибку gracefully
if echo "$DEPLOY_OUTPUT" | grep -q "Parameter decoding error"; then
    log_warning "Detected parameter decoding error - this might be due to contract state issues"
    log_info "Attempting to continue with existing contracts..."
    
    # Принудительное копирование адресов контрактов
    force_copy_contract_addresses
    
    # Продолжение выполнения
    log_warning "Continuing with deployment process..."
```

**Диагностические шаги:**

1. **Проверка ABI соответствия:**
   ```bash
   # Проверить соответствие ABI и байт-кода
   npx hardhat verify --network localhost <CONTRACT_ADDRESS>
   ```

2. **Проверка состояния контракта:**
   ```bash
   # Прямой вызов через web3
   curl -X POST http://localhost:8545 \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_getCode","params":["<CONTRACT_ADDRESS>","latest"],"id":1}'
   ```

3. **Проверка синхронизации ноды:**
   ```bash
   # Проверить блок номер
   curl -X POST http://localhost:8545 \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
   ```

**Возможные решения:**

1. **Перекомпиляция контрактов:**
   ```bash
   npx hardhat clean
   npx hardhat compile
   ```

2. **Перезапуск Hardhat node:**
   ```bash
   # Очистка состояния ноды
   rm -rf .hardhat/
   npx hardhat node --reset
   ```

3. **Проверка версий зависимостей:**
   ```bash
   # Проверить совместимость версий
   npm list @openzeppelin/contracts
   npm list hardhat
   ```

4. **Обновление ABI в коде:**
   ```bash
   # Обновить ABI файлы
   cp artifacts/contracts/SpiralEngine.sol/SpiralEngine.json bot/artifacts/
   ```

**Рекомендации по предотвращению:**

1. **Валидация деплоя:**
   ```bash
   # Добавить проверку после деплоя
   validate_contract_deployment() {
       local contract_addr="$1"
       local method="$2"
       
       response=$(curl -s -X POST http://localhost:8545 \
         -H "Content-Type: application/json" \
         -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"$contract_addr\",\"data\":\"$method\"},\"latest\"],\"id\":1}")
       
       if echo "$response" | grep -q "error"; then
           log_error "Contract validation failed: $response"
           return 1
       fi
       return 0
   }
   ```

2. **Health check контрактов:**
   ```bash
   # Регулярная проверка состояния контрактов
   check_contract_health() {
       for contract in $CONTRACT_ADDRESSES; do
           if ! validate_contract_deployment "$contract" "0x06fdde03"; then
               log_warning "Contract $contract is not responding"
           fi
       done
   }
   ```

**Влияние на экосистему Amanita:**

**🔗 Цепочка зависимостей:**
```
Parameter Decoding Error → Контракты недоступны → Минтинг инвайтов невозможен → Активация селлера невозможна → Telegram бот не работает → Экосистема не функционирует
```

**📊 Матрица влияния:**
| Компонент | Статус | Влияние | Критичность |
|-----------|--------|---------|-------------|
| Hardhat Node | ✅ Работает | Нет | Низкая |
| Wallet Server | ✅ Работает | Нет | Низкая |
| ngrok Tunnel | ✅ Работает | Нет | Низкая |
| Contract Deployment | ✅ Завершен | Частичное | Средняя |
| Contract Interaction | ❌ Не работает | Критическое | Высокая |
| Invite Minting | ❌ Не работает | Критическое | Высокая |
| Seller Activation | ❌ Не работает | Критическое | Высокая |
| Telegram Bot | ⚠️ Запускается | Ограниченное | Средняя |

**🎯 Практические последствия:**
1. **Для разработчиков**: Невозможно тестировать функциональность инвайтов и активации
2. **Для пользователей**: Telegram бот запускается, но не может взаимодействовать с блокчейном
3. **Для экосистемы**: Нарушена основная логика работы системы приглашений

**Статус проблемы:**
- 🔴 **Критическая**: Блокирует основную функциональность
- 🔄 **Обрабатывается**: Скрипт продолжает работу с ограничениями
- 📊 **Мониторится**: Логируются все случаи возникновения
- 🛠️ **Требует исправления**: Необходимо устранение корневой причины
- ⏰ **Приоритет**: P0 - требует немедленного решения

#### 2. **"already exists/deployed"** - повторные запуски
#### 3. **"invite already used"** - дублирование инвайтов  
#### 4. **"seller already activated"** - повторная активация

### Стратегии восстановления
- Продолжение выполнения при некритичных ошибках
- Принудительное копирование адресов контрактов
- Проверка существующих файлов инвайтов
- Graceful degradation при проблемах с ботом

## 📈 Мониторинг и логирование

### Логирование
- **Цветное логирование**: INFO (синий), SUCCESS (зеленый), WARNING (желтый), ERROR (красный)
- **Детальные логи**: Все операции с временными метками
- **Файлы логов**: Отдельные файлы для каждого сервиса

### Проверки здоровья
- JSON-RPC проверки для Hardhat node
- HTTP проверки для wallet server
- ngrok API проверки для туннеля
- PID проверки для всех процессов

## 🔄 Жизненный цикл

### Инициализация
1. Очистка системы
2. Проверка зависимостей
3. Определение PROJECT_ROOT

### Выполнение
1. Запуск инфраструктуры
2. Настройка окружения
3. Деплой контрактов
4. Активация пользователей
5. Запуск бота

### Завершение
1. Trap для cleanup при выходе
2. Убийство всех фоновых процессов
3. Очистка временных файлов

## 🎯 Результат выполнения

### Успешное завершение
- ✅ Hardhat node работает на 8545
- ✅ Wallet server доступен локально и через ngrok
- ✅ Все контракты зарегистрированы в MagicRegistry
- ✅ Deployer и seller активированы
- ✅ Telegram бот запущен

### Файлы результатов
- **Contract addresses**: В root/.env и bot/.env
- **Invite files**: deployer_invites_localhost.txt, ${SELLER_ADDRESS}_invites.txt
- **ngrok URL**: Обновлен в WALLET_APP_URL
- **Process PIDs**: Для мониторинга и управления

## 🛠️ Использование

### Запуск
```bash
cd /Users/eslinko/Development/Amanita
./scripts/quick_start_automation.sh
```

### Остановка
```bash
# Ctrl+C для graceful shutdown
# Или убийство процессов по PID
```

### Отладка
```bash
# Проверка логов
cat /tmp/hardhat_node.log
cat /tmp/ngrok.log
cat /tmp/bot_output.log

# Проверка процессов
lsof -ti:3000
lsof -ti:8545
pgrep -f "ngrok"
```