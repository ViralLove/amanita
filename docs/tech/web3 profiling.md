# Web3: Профилирование и выбор сети для AMANITA

## Описание

Сервис `BlockchainService` и Telegram-бот AMANITA поддерживают гибкий выбор активного профиля блокчейн-сети (mainnet, testnet, localhost) для работы с контрактами. Это позволяет удобно переключаться между средами разработки, тестирования и продакшена.

---

## Как указывать активный профиль

### 1. Через переменную окружения (рекомендуется)

**Локальный запуск:**
```bash
export BLOCKCHAIN_PROFILE=amoy
python bot/main.py
```
или одной строкой:
```bash
BLOCKCHAIN_PROFILE=localhost python bot/main.py
```

**Docker/Docker Compose:**
```dockerfile
ENV BLOCKCHAIN_PROFILE=mainnet
```
или в docker-compose.yml:
```yaml
environment:
  - BLOCKCHAIN_PROFILE=amoy
```

**Через .env файл:**
В файле `bot/.env`:
```
BLOCKCHAIN_PROFILE=amoy
```

> Бот автоматически подхватит профиль при запуске, если используется dotenv.

---

### 2. Программно (в коде)

Можно явно указать профиль при создании сервиса:
```python
from bot.services.blockchain import BlockchainService
service = BlockchainService(profile='localhost')
```

Это удобно для тестов, CLI-утилит, скриптов.

---

### 3. Через параметры запуска (опционально)

Можно добавить обработку аргументов командной строки (например, через argparse):
```bash
python bot/main.py --profile amoy
```
И передавать этот профиль в BlockchainService.

---

## Приоритет выбора профиля
1. Явно переданный параметр в конструктор BlockchainService
2. Переменная окружения `BLOCKCHAIN_PROFILE`
3. Значение по умолчанию: `mainnet`

---

## Пример использования в коде
```python
# Использует профиль из env или mainnet по умолчанию
service = BlockchainService()

# Явно указываем профиль
service = BlockchainService(profile='amoy')
```

---

## Рекомендации
- Для продакшена и CI/CD используйте переменные окружения или .env.
- Для тестов и отладки — можно явно передавать профиль в коде.
- Всегда проверяйте, что выбранный профиль и RPC корректно отображаются в логах при запуске.

---

## Возможные значения профиля
- `mainnet` — основная сеть Polygon
- `amoy` — тестовая сеть Polygon Amoy
- `localhost` — локальная нода Hardhat или Ganache

---

## Пример .env
```
BLOCKCHAIN_PROFILE=amoy
WEB3_PROVIDER=https://rpc-amoy.polygon.technology
```

---

## Важно
- Если профиль не указан, используется mainnet.
- Если переменная окружения `WEB3_PROVIDER` задана, она переопределяет RPC для выбранного профиля.
- Все логи по профилю и RPC выводятся при запуске сервиса.
